#!/usr/bin/env python3
"""experiments/train_rc52.py — rc52 REINFORCE trainer.

Algorithm: REINFORCE with running-mean baseline on a softmax-policy over
per-action Q-scores. Linear Q: Q(s,a) = w · φ(s,a), where φ is the shared
17-or-20-dim zoo_features vector.

Per-batch loop:
  1. Play B games with current weights (zoo_rc52_trainer with ε-greedy).
     Half as Red, half as Blue to cancel color bias.
  2. For each game, compute our-side return G:
        G = +score if we were Red, -score if we were Blue
     (positive → we won, negative → they won, zero → tie)
  3. Batch baseline: b = mean(G over games).
  4. For each turn record (s, a), update:
        π(a|s)  = softmax(Q(s,a') for a' ∈ legal)
        ∇log π  = φ(s, a) - Σ_a' π(a'|s) φ(s, a')
        w      += lr · (G - b) · ∇log π
  5. Save weights. Next batch.

Output format matches A1's `final_weights.py` so rc52 can be loaded by
any zoo_reflex_tuned container (submission-compatible).

Usage:
    .venv/bin/python experiments/train_rc52.py \\
        --iters 15 --games-per-iter 10 --epsilon 0.15 --lr 1e-4 \\
        --init-weights experiments/artifacts/phase2_A1_17dim_final_weights.py \\
        --out experiments/artifacts/rc52/final_weights.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PY = REPO_ROOT / ".venv" / "bin" / "python"
SINGLE_GAME = REPO_ROOT / "experiments" / "single_game.py"


FEATURE_KEYS = [
    'f_bias', 'f_successorScore', 'f_distToFood', 'f_distToCapsule',
    'f_numCarrying', 'f_distToHome', 'f_ghostDist1', 'f_ghostDist2',
    'f_inDeadEnd', 'f_stop', 'f_reverse', 'f_numInvaders',
    'f_invaderDist', 'f_onDefense', 'f_patrolDist',
    'f_distToCapsuleDefend', 'f_scaredFlee',
    'f_scaredGhostChase', 'f_returnUrgency', 'f_teammateSpread',
]
NUM_FEATS = len(FEATURE_KEYS)


# ---------------------------------------------------------------------------
# Weights I/O
# ---------------------------------------------------------------------------

def weights_dict_to_vec(w: dict) -> np.ndarray:
    return np.array([float(w.get(k, 0.0)) for k in FEATURE_KEYS], dtype=np.float64)


def vec_to_weights_dict(v: np.ndarray) -> dict:
    return {k: float(v[i]) for i, k in enumerate(FEATURE_KEYS)}


def load_init_weights(path: str | None) -> tuple[np.ndarray, np.ndarray]:
    """Load W_OFF, W_DEF from a final_weights.py-style module.

    Returns (17|20-dim np arrays). If path is None or load fails, both are
    initialized to A1 seed zeros (all ones? no — use tuned SEED_WEIGHTS).
    """
    if path and Path(path).exists():
        try:
            spec = importlib.util.spec_from_file_location("_init_w", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            w_off = getattr(mod, "W_OFF", {})
            w_def = getattr(mod, "W_DEF", {}) or w_off
            return (weights_dict_to_vec(w_off), weights_dict_to_vec(w_def))
        except Exception as exc:
            print(f"[rc52] init weights load failed: {exc}", file=sys.stderr)

    # Fallback: zero init (agent will explore widely).
    return np.zeros(NUM_FEATS), np.zeros(NUM_FEATS)


def save_weights(w_off: np.ndarray, w_def: np.ndarray, out_path: Path,
                 iteration: int, stats: dict):
    """Write a final_weights.py module compatible with A1's format."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        f.write("# rc52 REINFORCE-trained weights (auto-generated).\n")
        f.write(f"# Iteration {iteration}. Stats: {json.dumps(stats)}\n\n")
        f.write("W_OFF = {\n")
        for i, k in enumerate(FEATURE_KEYS):
            f.write(f"    {k!r}: {float(w_off[i])!r},\n")
        f.write("}\n\n")
        f.write("W_DEF = {\n")
        for i, k in enumerate(FEATURE_KEYS):
            f.write(f"    {k!r}: {float(w_def[i])!r},\n")
        f.write("}\n\n")
        f.write("PARAMS = {}\n")


# ---------------------------------------------------------------------------
# Training rollout
# ---------------------------------------------------------------------------

def _write_weights_json(w_off: np.ndarray, w_def: np.ndarray, tmp_path: Path):
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    with tmp_path.open("w") as f:
        json.dump({
            "w_off": vec_to_weights_dict(w_off),
            "w_def": vec_to_weights_dict(w_def),
        }, f)


def _run_one_game(weights_path: Path, log_path: Path, epsilon: float,
                  our_is_red: bool) -> dict:
    """Run one game with RC52 trainer agent (our side) vs baseline."""
    env = os.environ.copy()
    env["RC52_WEIGHTS_PATH"] = str(weights_path)
    env["RC52_LOG_PATH"] = str(log_path)
    env["RC52_EPSILON"] = str(epsilon)

    py = str(VENV_PY) if VENV_PY.exists() else sys.executable
    trainer = "zoo_rc52_trainer"
    if our_is_red:
        cmd = [py, str(SINGLE_GAME), "-r", trainer, "-b", "baseline", "-l",
               "defaultCapture", "-q"]
    else:
        cmd = [py, str(SINGLE_GAME), "-r", "baseline", "-b", trainer, "-l",
               "defaultCapture", "-q"]

    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True,
                              timeout=180.0, cwd=str(REPO_ROOT))
    except subprocess.TimeoutExpired:
        return {"crashed": True, "score": 0}

    if proc.returncode != 0:
        return {"crashed": True, "score": 0, "stderr": proc.stderr[-400:]}

    for ln in proc.stdout.strip().split("\n")[::-1]:
        if ln.startswith("{"):
            try:
                return json.loads(ln)
            except Exception:
                continue
    return {"crashed": True, "score": 0}


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max()
    e = np.exp(z)
    return e / (e.sum() + 1e-12)


def train(args):
    out_path = Path(args.out).resolve()
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Init weights
    w_off, w_def = load_init_weights(args.init_weights)
    print(f"[rc52] init: w_off mean {w_off.mean():.2f}, w_def mean {w_def.mean():.2f}",
          file=sys.stderr)

    tmp_weights = out_dir / "_current_weights.json"
    turn_log = out_dir / "_turns.jsonl"

    # Running mean baseline
    baseline = 0.0
    baseline_decay = 0.9

    total_games = 0
    overall_wins = 0
    t0 = time.time()

    for it in range(args.iters):
        _write_weights_json(w_off, w_def, tmp_weights)
        if turn_log.exists():
            turn_log.unlink()

        # Play batch.
        game_returns = []
        game_colors = []     # "red" or "blue"
        game_turns = []      # list of [records-for-this-game]

        for g in range(args.games_per_iter):
            our_is_red = (g % 2 == 0)
            res = _run_one_game(tmp_weights, turn_log, args.epsilon, our_is_red)
            if res.get("crashed"):
                continue
            score = float(res.get("score", 0.0) or 0.0)
            G = score if our_is_red else -score
            game_returns.append(G)
            game_colors.append("red" if our_is_red else "blue")
            won = (G > 0)
            if won:
                overall_wins += 1
            total_games += 1

        # Read all turn records for this iteration.
        records_by_color = {"red": [], "blue": []}
        try:
            for ln in open(turn_log):
                try:
                    rec = json.loads(ln.strip())
                except Exception:
                    continue
                records_by_color[rec.get("color", "red")].append(rec)
        except Exception:
            pass

        # Partition records by game. We alternate colors even/odd, and only
        # our agent logs — so all records from the even-numbered subprocess
        # are "red", odd are "blue". But subprocesses append sequentially,
        # so we split turns by color and game index modulo alternation.
        # Simpler: assign ALL records from each color a single G value
        # (the AVERAGE of that color's game returns within the batch).
        mean_G_red = (np.mean([G for G, c in zip(game_returns, game_colors) if c == "red"])
                      if any(c == "red" for c in game_colors) else 0.0)
        mean_G_blue = (np.mean([G for G, c in zip(game_returns, game_colors) if c == "blue"])
                       if any(c == "blue" for c in game_colors) else 0.0)

        # Update baseline (running mean of all returns this batch).
        batch_mean = np.mean(game_returns) if game_returns else 0.0
        baseline = baseline_decay * baseline + (1 - baseline_decay) * batch_mean

        # REINFORCE update per record.
        updates_off = np.zeros(NUM_FEATS)
        updates_def = np.zeros(NUM_FEATS)
        n_off_updates = 0
        n_def_updates = 0

        for color, recs in records_by_color.items():
            G = mean_G_red if color == "red" else mean_G_blue
            advantage = G - baseline
            for rec in recs:
                try:
                    feats = np.asarray(rec["feats"], dtype=np.float64)  # [L, 17or20]
                    chosen = int(rec["chosen"])
                    role = rec.get("role", "OFFENSE")
                    if feats.shape[0] == 0 or chosen < 0 or chosen >= feats.shape[0]:
                        continue
                    if feats.shape[1] != NUM_FEATS:
                        continue
                    w = w_off if role == "OFFENSE" else w_def
                    Q = feats @ w                        # [L]
                    pi = _softmax(Q)                     # [L]
                    grad = feats[chosen] - (pi[:, None] * feats).sum(axis=0)  # [17]
                    step = args.lr * advantage * grad
                    if role == "OFFENSE":
                        updates_off += step
                        n_off_updates += 1
                    else:
                        updates_def += step
                        n_def_updates += 1
                except Exception:
                    continue

        # Apply average update (instead of summed — keeps scale stable).
        if n_off_updates > 0:
            w_off += updates_off / n_off_updates
        if n_def_updates > 0:
            w_def += updates_def / n_def_updates

        # Optional L2 clip.
        max_norm = args.w_clip
        for w in (w_off, w_def):
            nrm = np.linalg.norm(w)
            if nrm > max_norm:
                w *= max_norm / nrm

        dt = time.time() - t0
        wins_batch = sum(1 for G in game_returns if G > 0)
        wr_cum = overall_wins / max(1, total_games)
        print(f"[rc52] iter={it+1}/{args.iters} games={len(game_returns)} "
              f"wins_batch={wins_batch}/{len(game_returns) or 0} "
              f"mean_G={batch_mean:.2f} baseline={baseline:.2f} "
              f"cum_wr={wr_cum:.2%} off_upd={n_off_updates} def_upd={n_def_updates} "
              f"|w_off|={np.linalg.norm(w_off):.2f} wall={dt:.0f}s",
              file=sys.stderr, flush=True)

        # Save after every iter so we can resume / HTH mid-train.
        save_weights(w_off, w_def, out_path, it + 1, {
            "iter": it + 1,
            "cum_games": total_games,
            "cum_wr": wr_cum,
            "baseline": float(baseline),
            "batch_mean_G": float(batch_mean),
        })

    print(json.dumps({
        "iters": args.iters, "total_games": total_games,
        "final_wr": overall_wins / max(1, total_games),
        "out": str(out_path),
    }))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="rc52 REINFORCE trainer")
    p.add_argument("--iters", type=int, default=15)
    p.add_argument("--games-per-iter", type=int, default=10)
    p.add_argument("--epsilon", type=float, default=0.15)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--w-clip", type=float, default=500.0)
    p.add_argument("--init-weights", type=str, default="")
    p.add_argument("--out", type=str, required=True)
    args = p.parse_args(argv)
    return train(args)


if __name__ == "__main__":
    sys.exit(main())

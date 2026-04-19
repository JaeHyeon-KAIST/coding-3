#!/usr/bin/env python3
"""experiments/distill_rc22.py — rc22 Policy Distillation pipeline.

Pipeline:
    COLLECT: run N games (rc82 teacher vs baseline, both colors), write
             per-turn (features [L,20], legal [L], chosen) records to JSONL.
    TRAIN  : numpy MLP (20→32→1) Q-score per legal action → softmax → CE
             loss vs teacher's chosen action. SGD + momentum.
    EXPORT : .npz with W1, b1, W2, b2, FEATURE_KEYS.

Subcommands:
    collect  --games N --out artifacts/rc22/data.jsonl
    train    --data  artifacts/rc22/data.jsonl --out artifacts/rc22/weights.npz
    both     --games N --out-dir artifacts/rc22/

All Python calls go through `.venv/bin/python` (or the current interpreter)
and respect CLAUDE.md's no-global-python rule.
"""

from __future__ import annotations

import argparse
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


# Same canonical order used by the collector and the student agent.
FEATURE_KEYS = [
    'f_bias',
    'f_successorScore',
    'f_distToFood',
    'f_distToCapsule',
    'f_numCarrying',
    'f_distToHome',
    'f_ghostDist1',
    'f_ghostDist2',
    'f_inDeadEnd',
    'f_stop',
    'f_reverse',
    'f_numInvaders',
    'f_invaderDist',
    'f_onDefense',
    'f_patrolDist',
    'f_distToCapsuleDefend',
    'f_scaredFlee',
    'f_scaredGhostChase',
    'f_returnUrgency',
    'f_teammateSpread',
]
NUM_FEATS = len(FEATURE_KEYS)
NUM_ACTIONS = 5  # N/S/E/W/Stop


# ---------------------------------------------------------------------------
# COLLECT
# ---------------------------------------------------------------------------

def _run_one_game(log_path: Path, red: str, blue: str, layout: str, seed: int | None,
                  timeout_s: float = 180.0) -> dict:
    """Invoke experiments/single_game.py with RC22_LOG_PATH set.

    Returns parsed JSON from single_game (winner, score, ...).
    """
    env = os.environ.copy()
    env["RC22_LOG_PATH"] = str(log_path)

    py = str(VENV_PY) if VENV_PY.exists() else sys.executable

    cmd = [py, str(SINGLE_GAME), "-r", red, "-b", blue, "-l", layout, "-q"]
    if seed is not None and layout == "RANDOM":
        # single_game forwards -l as-is; matches run_match's seed convention.
        cmd[cmd.index(layout)] = f"RANDOM{seed}"

    try:
        proc = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=timeout_s,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"crashed": True, "crash_reason": "timeout", "red_win": 0, "blue_win": 0}

    if proc.returncode != 0:
        return {"crashed": True, "crash_reason": f"exit={proc.returncode}",
                "stderr": proc.stderr[-400:]}
    # single_game emits one JSON line on stdout.
    for ln in proc.stdout.strip().split("\n")[::-1]:
        ln = ln.strip()
        if ln.startswith("{"):
            try:
                return json.loads(ln)
            except Exception:
                continue
    return {"crashed": True, "crash_reason": "no_json", "stdout_tail": proc.stdout[-400:]}


def cmd_collect(args) -> int:
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    total = args.games
    t0 = time.time()
    wins = 0
    crashes = 0

    for i in range(total):
        # Alternate colors: even i → collector is Red, odd → collector is Blue.
        if i % 2 == 0:
            red, blue = "zoo_distill_collector", "baseline"
            our_win_key = "red_win"
        else:
            red, blue = "baseline", "zoo_distill_collector"
            our_win_key = "blue_win"

        layout = args.layout
        seed = args.seed_base + i if layout == "RANDOM" else None
        res = _run_one_game(out_path, red, blue, layout, seed)

        wins += int(res.get(our_win_key, 0) or 0)
        crashes += int(1 if res.get("crashed") else 0)
        dt = time.time() - t0
        eta = dt / (i + 1) * (total - i - 1)
        print(f"[collect] {i+1}/{total} red={red} blue={blue} "
              f"our_win={res.get(our_win_key, 0)} crashed={res.get('crashed', False)} "
              f"wins={wins} crashes={crashes} wall={dt:.1f}s eta={eta:.1f}s",
              file=sys.stderr, flush=True)

    # Count records
    try:
        n_recs = sum(1 for _ in open(out_path))
    except Exception:
        n_recs = 0
    print(f"[collect] DONE {total} games, {n_recs} turn-records → {out_path}",
          file=sys.stderr)
    print(json.dumps({
        "games": total, "wins": wins, "crashes": crashes,
        "turns": n_recs, "jsonl": str(out_path),
    }))
    return 0


# ---------------------------------------------------------------------------
# TRAIN
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> list:
    """Load all turn records. Returns list of (feats ndarray [L,20], chosen_local_idx, legal list)."""
    data = []
    for ln in open(path):
        ln = ln.strip()
        if not ln:
            continue
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        legal = rec.get("legal", [])
        feats = rec.get("feats", [])
        chosen = rec.get("chosen", -1)
        if not legal or chosen not in legal:
            continue
        if len(feats) != len(legal):
            continue
        x = np.asarray(feats, dtype=np.float64)  # [L, 20]
        if x.ndim != 2 or x.shape[1] != NUM_FEATS:
            continue
        local_idx = legal.index(chosen)  # position within legal list
        data.append((x, local_idx))
    return data


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max()
    e = np.exp(z)
    return e / (e.sum() + 1e-12)


def _normalize_feats(data: list) -> tuple[np.ndarray, np.ndarray]:
    """Compute per-feature mean+std over all (s,a) pairs for input normalization."""
    stacked = np.concatenate([x for x, _ in data], axis=0) if data else np.zeros((0, NUM_FEATS))
    mu = stacked.mean(axis=0) if len(stacked) else np.zeros(NUM_FEATS)
    sd = stacked.std(axis=0)  if len(stacked) else np.ones(NUM_FEATS)
    sd = np.where(sd < 1e-6, 1.0, sd)
    return mu, sd


def cmd_train(args) -> int:
    data_path = Path(args.data).resolve()
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    data = _load_jsonl(data_path)
    N = len(data)
    if N == 0:
        print("[train] no data — abort", file=sys.stderr)
        return 1

    mu, sd = _normalize_feats(data)

    # Normalize once (store normalized arrays back).
    data = [((x - mu) / sd, idx) for (x, idx) in data]

    # MLP shape: 20 → H → 1 (per-action score). Softmax over legal actions.
    H = args.hidden
    rng = np.random.RandomState(args.seed)
    W1 = rng.randn(NUM_FEATS, H).astype(np.float64) * np.sqrt(2.0 / NUM_FEATS)
    b1 = np.zeros(H, dtype=np.float64)
    W2 = rng.randn(H, 1).astype(np.float64) * np.sqrt(2.0 / H)
    b2 = np.zeros(1, dtype=np.float64)

    lr = args.lr
    mom = 0.9
    vW1 = np.zeros_like(W1); vb1 = np.zeros_like(b1)
    vW2 = np.zeros_like(W2); vb2 = np.zeros_like(b2)

    split = int(N * 0.9)
    train_data = data[:split]
    val_data = data[split:]
    print(f"[train] N={N} train={len(train_data)} val={len(val_data)} "
          f"hidden={H} lr={lr} epochs={args.epochs}", file=sys.stderr)

    perm = np.arange(len(train_data))
    for epoch in range(args.epochs):
        rng.shuffle(perm)
        loss_sum = 0.0
        correct = 0
        for i in perm:
            x, y = train_data[i]  # x: [L, 20], y: int
            # Forward
            z1 = x @ W1 + b1  # [L, H]
            h1 = np.maximum(0.0, z1)
            z2 = (h1 @ W2 + b2).reshape(-1)  # [L]
            p = _softmax(z2)
            loss = -np.log(max(p[y], 1e-12))
            loss_sum += loss
            if int(np.argmax(z2)) == y:
                correct += 1

            # Backprop (softmax + CE)
            dz2 = p.copy()
            dz2[y] -= 1.0           # [L]
            dW2 = h1.T @ dz2.reshape(-1, 1)   # [H, 1]
            db2 = dz2.sum(keepdims=True)      # [1]
            dh1 = dz2.reshape(-1, 1) @ W2.T   # [L, H]
            dz1 = dh1.copy()
            dz1[z1 <= 0] = 0.0
            dW1 = x.T @ dz1                   # [20, H]
            db1 = dz1.sum(axis=0)             # [H]

            # Momentum SGD update
            vW1 = mom * vW1 - lr * dW1
            vb1 = mom * vb1 - lr * db1
            vW2 = mom * vW2 - lr * dW2
            vb2 = mom * vb2 - lr * db2
            W1 += vW1; b1 += vb1
            W2 += vW2; b2 += vb2

        tr_acc = correct / max(1, len(train_data))
        tr_loss = loss_sum / max(1, len(train_data))
        va_loss, va_acc = _evaluate(val_data, W1, b1, W2, b2)
        print(f"[train] epoch={epoch+1} loss={tr_loss:.4f} acc={tr_acc:.3f} "
              f"val_loss={va_loss:.4f} val_acc={va_acc:.3f}", file=sys.stderr)

    # Save
    np.savez(
        out_path,
        W1=W1, b1=b1, W2=W2, b2=b2,
        feat_mu=mu, feat_sd=sd,
        feature_keys=np.array(FEATURE_KEYS),
        hidden=H,
    )
    print(f"[train] weights → {out_path}", file=sys.stderr)
    print(json.dumps({
        "n": N, "train_n": len(train_data), "val_n": len(val_data),
        "hidden": H, "epochs": args.epochs, "lr": lr,
        "final_train_acc": tr_acc, "final_val_acc": va_acc,
        "out": str(out_path),
    }))
    return 0


def _evaluate(data, W1, b1, W2, b2) -> tuple[float, float]:
    if not data:
        return 0.0, 0.0
    loss_sum, correct = 0.0, 0
    for x, y in data:
        z1 = x @ W1 + b1
        h1 = np.maximum(0.0, z1)
        z2 = (h1 @ W2 + b2).reshape(-1)
        p = _softmax(z2)
        loss_sum += -np.log(max(p[y], 1e-12))
        if int(np.argmax(z2)) == y:
            correct += 1
    return loss_sum / len(data), correct / len(data)


# ---------------------------------------------------------------------------
# BOTH
# ---------------------------------------------------------------------------

def cmd_both(args) -> int:
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    data_path = out_dir / "data.jsonl"
    wt_path = out_dir / "weights.npz"

    class Bag:
        pass
    a = Bag()
    a.games = args.games
    a.out = str(data_path)
    a.layout = args.layout
    a.seed_base = args.seed_base
    rc = cmd_collect(a)
    if rc != 0:
        return rc

    a = Bag()
    a.data = str(data_path)
    a.out = str(wt_path)
    a.hidden = args.hidden
    a.lr = args.lr
    a.epochs = args.epochs
    a.seed = args.seed
    return cmd_train(a)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="rc22 Policy Distillation pipeline")
    sp = p.add_subparsers(dest="cmd", required=True)

    c = sp.add_parser("collect")
    c.add_argument("--games", type=int, required=True)
    c.add_argument("--out", type=str, required=True)
    c.add_argument("--layout", type=str, default="defaultCapture")
    c.add_argument("--seed-base", type=int, default=2226)
    c.set_defaults(func=cmd_collect)

    t = sp.add_parser("train")
    t.add_argument("--data", type=str, required=True)
    t.add_argument("--out", type=str, required=True)
    t.add_argument("--hidden", type=int, default=32)
    t.add_argument("--lr", type=float, default=1e-3)
    t.add_argument("--epochs", type=int, default=30)
    t.add_argument("--seed", type=int, default=2226)
    t.set_defaults(func=cmd_train)

    b = sp.add_parser("both")
    b.add_argument("--games", type=int, required=True)
    b.add_argument("--out-dir", type=str, required=True)
    b.add_argument("--layout", type=str, default="defaultCapture")
    b.add_argument("--seed-base", type=int, default=2226)
    b.add_argument("--hidden", type=int, default=32)
    b.add_argument("--lr", type=float, default=1e-3)
    b.add_argument("--epochs", type=int, default=30)
    b.add_argument("--seed", type=int, default=2226)
    b.set_defaults(func=cmd_both)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

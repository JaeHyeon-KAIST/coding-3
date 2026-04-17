"""experiments/hth_battery.py — HTH validation of an evolved champion.

Loads a `final_weights.py` style module, writes a tmp genome JSON, then
plays N games per opponent via `run_match.py` under a ProcessPool.
Reports per-opponent win rate + Wilson 95% CI and total crash count.

Designed for the pm18/post-A1 reality check: A1's fitness=1.065 was on the
training pool, not baseline.py. This script actually measures baseline HTH
and diagnoses overfit against a monster-reference opponent.

Usage:
    .venv/bin/python experiments/hth_battery.py \
        --weights experiments/artifacts/final_weights.py \
        --opponents baseline monster_rule_expert zoo_reflex_h1test zoo_minimax_ab_d2 \
        --games-per-opp 200 50 30 30 \
        --layouts defaultCapture RANDOM \
        --workers 16 --out experiments/artifacts/hth_A1.csv
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_match import run_match  # noqa: E402


def wilson_95(wins: int, total: int) -> tuple[float, float, float]:
    """95% Wilson interval for a binomial proportion.

    Returns (point_estimate, lower_bound, upper_bound). Handles n=0 without
    dividing by zero.
    """
    if total == 0:
        return 0.0, 0.0, 1.0
    p = wins / total
    z = 1.96
    denom = 1 + z * z / total
    centre = p + z * z / (2 * total)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return p, (centre - spread) / denom, (centre + spread) / denom


def play_one(opp: str, our_is_red: bool, weights_arg: str, layout: str, seed: int):
    """Run a single match with our champion vs `opp`. Returns a row dict."""
    our_agent = "zoo_reflex_tuned"
    if our_is_red:
        red, blue = our_agent, opp
        red_opts, blue_opts = weights_arg, ""
    else:
        red, blue = opp, our_agent
        red_opts, blue_opts = "", weights_arg
    try:
        result = run_match(
            red=red, blue=blue, layout=layout, seed=seed,
            timeout_s=120.0, red_opts=red_opts, blue_opts=blue_opts,
        )
    except Exception as e:
        result = {"crashed": True, "red_win": 0, "blue_win": 0,
                  "crash_reason": f"wrapper:{type(e).__name__}:{e}"}
    crashed = bool(result.get("crashed", False))
    win = int(result.get("red_win" if our_is_red else "blue_win", 0))
    return {
        "opp": opp,
        "color": "red" if our_is_red else "blue",
        "layout": layout,
        "seed": seed,
        "win": win,
        "crashed": int(crashed),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True,
                    help="Path to final_weights.py (module with W_OFF, W_DEF, PARAMS).")
    ap.add_argument("--opponents", nargs="+", required=True,
                    help="Opponent agent names.")
    ap.add_argument("--games-per-opp", nargs="+", type=int, default=[100],
                    help="Games per opponent. If single value, used for all opps.")
    ap.add_argument("--layouts", nargs="+", default=["defaultCapture", "RANDOM"])
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--master-seed", type=int, default=42)
    ap.add_argument("--out", required=True, help="CSV output path.")
    args = ap.parse_args()

    # Broadcast single games-per-opp value to all opponents.
    if len(args.games_per_opp) == 1:
        args.games_per_opp = args.games_per_opp * len(args.opponents)
    if len(args.games_per_opp) != len(args.opponents):
        raise SystemExit("--games-per-opp must be length 1 or match --opponents length")

    # Load final_weights module
    weights_path = Path(args.weights).resolve()
    spec = importlib.util.spec_from_file_location("final_weights", weights_path)
    fw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fw)
    if not hasattr(fw, "W_OFF") or not hasattr(fw, "W_DEF"):
        raise SystemExit(f"{weights_path} missing W_OFF / W_DEF")
    params = getattr(fw, "PARAMS", {})

    # Write genome JSON for --red-opts / --blue-opts channel.
    # MUST be absolute — capture.py subprocess runs with cwd=minicontest/
    # and the red_opts `weights=<path>` is resolved by zoo_core.load_weights_override
    # relative to that cwd, not the hth_battery cwd. A relative path here silently
    # fails to load (zoo agent falls back to SEED_WEIGHTS → appears as 100% tie
    # against baseline = the pre-evolution zoo_reflex_tuned deadlock signature).
    genome_json = (Path(args.out).parent / ("hth_genome_" + weights_path.stem + ".json")).resolve()
    genome_json.parent.mkdir(parents=True, exist_ok=True)
    with genome_json.open("w") as f:
        json.dump({"w_off": fw.W_OFF, "w_def": fw.W_DEF, "params": params}, f)
    weights_arg = f"weights={genome_json}"
    print(f"[hth] genome JSON: {genome_json}", file=sys.stderr)

    # Build match list — for each opp, N games split across layouts × 2 colors.
    matches = []
    for opp, n_games in zip(args.opponents, args.games_per_opp):
        per_config = max(1, n_games // (len(args.layouts) * 2))
        for li, layout in enumerate(args.layouts):
            for rep in range(per_config):
                seed = args.master_seed + li * 997 + rep
                matches.append((opp, True, weights_arg, layout, seed))
                matches.append((opp, False, weights_arg, layout, seed))
    total = len(matches)
    print(f"[hth] scheduled {total} matches across {len(args.opponents)} opps × "
          f"{len(args.layouts)} layouts × 2 colors, workers={args.workers}",
          file=sys.stderr)

    # Parallel execute
    per_opp = defaultdict(lambda: {"wins": 0, "crashes": 0, "total": 0})
    rows = []
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(play_one, *m) for m in matches]
        for fut in as_completed(futures):
            try:
                row = fut.result()
            except Exception as e:
                print(f"[hth] worker error: {type(e).__name__}: {e}", file=sys.stderr)
                continue
            opp = row["opp"]
            per_opp[opp]["wins"] += row["win"]
            per_opp[opp]["crashes"] += row["crashed"]
            per_opp[opp]["total"] += 1
            rows.append(row)
            done += 1
            if done % max(1, total // 20) == 0:
                print(f"[hth] progress {done}/{total}", file=sys.stderr)

    # Write CSV
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        f.write("opp,color,layout,seed,win,crashed\n")
        for r in rows:
            f.write(f"{r['opp']},{r['color']},{r['layout']},{r['seed']},{r['win']},{r['crashed']}\n")
    print(f"[hth] CSV: {out_path}", file=sys.stderr)

    # Summary (stdout)
    print()
    print(f"HTH Battery — champion weights: {weights_path.name}")
    print(f"{'opponent':<32}  {'wins/total':<12}  {'WR':>7}  {'95% Wilson CI':<22}  {'crash':>6}")
    print("-" * 92)
    for opp in args.opponents:
        stats = per_opp.get(opp, {"wins": 0, "crashes": 0, "total": 0})
        w, n, c = stats["wins"], stats["total"], stats["crashes"]
        p, lo, hi = wilson_95(w, n)
        gate = " PASS" if lo > 0.51 else (" MARGINAL" if p >= 0.51 else " FAIL")
        print(f"{opp:<32}  {w}/{n:<11}  {p:>7.3f}  [{lo:.3f}, {hi:.3f}]   {c:>6}"
              f"{gate if opp == 'baseline' else ''}")


if __name__ == "__main__":
    main()

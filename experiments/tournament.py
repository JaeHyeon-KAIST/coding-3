"""
tournament.py — Parallel round-robin match runner.

Runs an NxN round-robin over a set of agent names. Each pair plays on each
layout across color swaps and seeds. Jobs dispatched via ProcessPoolExecutor
with worker count capped at physical cores (per plan §3.4).

Usage:
    # Round-robin among zoo agents
    python experiments/tournament.py \\
        --agents zoo_reflex_tuned zoo_minimax_ab_d2 zoo_mcts_heuristic baseline \\
        --layouts defaultCapture officeCapture \\
        --seeds 1 42 2025 \\
        --games-per-pair 2 \\
        --workers 8 --pin \\
        --out experiments/artifacts/tournament_results/t_$(date +%s).csv

Key constraints (plan):
- workers <= physical core count (Linux pinning via run_match.py; macOS no-op)
- Common Random Numbers (CRN): each (agent_A, agent_B, layout, seed) plays BOTH
  color assignments — variance-reduction via paired outcomes
- Output CSV schema matches §7.4 (agent, layout, opponent, seed, color, win, ...)
- No subprocess oversubscription: if workers > cpu_count(), capped to cpu_count()
"""

from __future__ import annotations
import argparse
import csv
import json
import multiprocessing
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import permutations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUN_MATCH = REPO_ROOT / "experiments" / "run_match.py"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"


def physical_cores() -> int:
    """Return physical core count (best-effort)."""
    try:
        n = os.cpu_count() or 1
    except Exception:
        n = 1
    return max(1, n - 1)  # leave 1 core for OS/Claude


def dispatch_one(args_tuple):
    """Subprocess-runnable wrapper around run_match CLI (serializable args)."""
    red, blue, layout, seed, pin_core, timeout = args_tuple
    cmd = [
        str(VENV_PYTHON),
        str(RUN_MATCH),
        "--red", red,
        "--blue", blue,
        "--layout", layout,
        "--timeout", str(timeout),
    ]
    if seed is not None:
        cmd += ["--seed", str(seed)]
    if pin_core is not None:
        cmd += ["--pin-core", str(pin_core)]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
    except subprocess.TimeoutExpired:
        return {
            "red": red, "blue": blue, "layout": layout, "seed": seed,
            "winner": None, "score": None, "red_win": 0, "blue_win": 0, "tie": 0,
            "crashed": True, "crash_reason": "outer_timeout",
            "wall_time": timeout + 10,
        }
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception as e:
        return {
            "red": red, "blue": blue, "layout": layout, "seed": seed,
            "winner": None, "score": None, "red_win": 0, "blue_win": 0, "tie": 0,
            "crashed": True, "crash_reason": f"parse_fail:{type(e).__name__}",
            "wall_time": 0.0, "stderr": proc.stderr[-500:] if proc.stderr else "",
        }


def build_jobs(agents, layouts, seeds, games_per_pair, crn_pair_colors=True):
    """
    Build the list of (red, blue, layout, seed, pin_core_slot, timeout) jobs.

    With CRN color-pairing, each (A, B, layout, seed) is played with both
    A=red/B=blue AND A=blue/B=red. This halves the opponent-pool variance
    at the cost of 2x games.
    """
    jobs = []
    for a, b in permutations(agents, 2):
        for layout in layouts:
            for seed in seeds:
                for _rep in range(games_per_pair):
                    jobs.append((a, b, layout, seed, None, 120.0))
    # pin_core is None here; outer scheduler assigns below based on worker index
    return jobs


def run_tournament(agents, layouts, seeds, games_per_pair, workers, pin, out_path, timeout_per_game):
    cpu = physical_cores()
    if workers > cpu:
        print(f"[warn] requested {workers} workers but only {cpu} physical cores; capping.", file=sys.stderr)
        workers = cpu

    jobs = build_jobs(agents, layouts, seeds, games_per_pair)
    # assign pin_core by job index modulo workers (only if pinning requested)
    if pin:
        jobs = [
            (r, b, l, s, i % workers, t)
            for i, (r, b, l, s, _, t) in enumerate(jobs)
        ]
    # unused timeout positional left as 120
    jobs = [(r, b, l, s, pc, timeout_per_game) for (r, b, l, s, pc, _) in jobs]

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(dispatch_one, job): job for job in jobs}
        for i, fut in enumerate(as_completed(futures)):
            try:
                res = fut.result()
            except Exception as e:
                job = futures[fut]
                res = {
                    "red": job[0], "blue": job[1], "layout": job[2], "seed": job[3],
                    "crashed": True, "crash_reason": f"executor_error:{e}",
                    "wall_time": 0.0,
                }
            results.append(res)
            if (i + 1) % 10 == 0:
                elapsed = time.time() - start
                print(f"[{i+1}/{len(jobs)}] elapsed={elapsed:.0f}s", file=sys.stderr)

    # emit CSV
    cols = [
        "red", "blue", "layout", "seed", "winner", "score",
        "red_win", "blue_win", "tie", "crashed", "crash_reason",
        "wall_time", "exit_code",
    ]
    with out_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)

    total = len(results)
    crashed = sum(1 for r in results if r.get("crashed"))
    elapsed = time.time() - start
    print(
        f"[done] {total} matches in {elapsed:.0f}s "
        f"({total / max(elapsed, 1e-9):.2f} games/s); "
        f"crashes: {crashed} ({100 * crashed / max(total, 1):.1f}%); "
        f"csv: {out_path}",
        file=sys.stderr,
    )
    return results, out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", nargs="+", required=True, help="Agent names (as -r/-b in capture.py)")
    ap.add_argument("--layouts", nargs="+", default=["defaultCapture"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[1])
    ap.add_argument("--games-per-pair", type=int, default=1)
    ap.add_argument("--workers", type=int, default=physical_cores())
    ap.add_argument("--pin", action="store_true", help="CPU-pin each worker (Linux only)")
    ap.add_argument("--timeout-per-game", type=float, default=120.0)
    ap.add_argument("--out", default="experiments/artifacts/tournament_results/tournament.csv")
    args = ap.parse_args()

    run_tournament(
        agents=args.agents,
        layouts=args.layouts,
        seeds=args.seeds,
        games_per_pair=args.games_per_pair,
        workers=args.workers,
        pin=args.pin,
        out_path=args.out,
        timeout_per_game=args.timeout_per_game,
    )


if __name__ == "__main__":
    main()

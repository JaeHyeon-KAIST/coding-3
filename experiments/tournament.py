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

# Canonical output column order. Used by both the live writer (run_tournament)
# and the resume-key loader (_load_completed_keys). Keep in sync with the
# schema documented in STRATEGY.md §7.4.
CSV_COLS = [
    "red", "blue", "layout", "seed", "winner", "score",
    "red_win", "blue_win", "tie", "crashed", "crash_reason",
    "wall_time", "exit_code",
]


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


def _load_completed_keys(resume_csv: Path) -> set:
    """Return the set of (red, blue, layout, seed) tuples already recorded in
    resume_csv so run_tournament can skip them.

    - Missing file, empty file, or read error → empty set (run everything).
    - Seed field is normalised to int-or-None to match build_jobs' tuple shape.
    - CSV reader is tolerant of trailing newlines / partial last rows (which
      can happen if a prior run was SIGKILL'd mid-fsync — we accept whatever
      DictReader can parse).
    """
    if not resume_csv.exists() or resume_csv.stat().st_size == 0:
        return set()
    keys = set()
    try:
        with resume_csv.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                seed_raw = row.get("seed", "")
                try:
                    seed = int(seed_raw) if seed_raw not in ("", "None") else None
                except ValueError:
                    seed = None
                keys.add((row.get("red", ""), row.get("blue", ""),
                          row.get("layout", ""), seed))
    except (OSError, csv.Error) as e:
        print(f"[resume] warn: failed reading {resume_csv}: {e}", file=sys.stderr)
        return set()
    return keys


def run_tournament(agents, layouts, seeds, games_per_pair, workers, pin,
                   out_path, timeout_per_game, resume_from=None):
    """Run a round-robin tournament, persisting each result to CSV immediately.

    Resilience contract (pm4 patch):
    - Each completed game is written to `out_path` and fsync'd before the
      next is parsed. A mid-run SIGKILL / power loss preserves every row that
      had returned before the kill.
    - If `out_path` (or `--resume-from`, if given) already exists with rows,
      those (red, blue, layout, seed) combos are skipped — pick-up continues
      in-place via append mode. First-time runs truncate + write header.
    """
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

    # Resume source defaults to out_path; override via --resume-from.
    resume_csv = Path(resume_from) if resume_from else out_path
    completed_keys = _load_completed_keys(resume_csv)
    if completed_keys:
        before = len(jobs)
        jobs = [
            j for j in jobs
            if (j[0], j[1], j[2], j[3]) not in completed_keys
        ]
        print(f"[resume] {len(completed_keys)} completed rows loaded from {resume_csv}; "
              f"skipping {before - len(jobs)}; {len(jobs)} remaining.",
              file=sys.stderr)

    # Write mode: append if out_path already has content (resume in-place),
    # otherwise truncate and write header.
    if out_path.exists() and out_path.stat().st_size > 0:
        mode, write_header = "a", False
    else:
        mode, write_header = "w", True

    start = time.time()
    results = []
    with out_path.open(mode, newline="", buffering=1) as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
            csv_file.flush()
            os.fsync(csv_file.fileno())
            # Also fsync the parent directory so the newly-created file's
            # directory entry survives a hard crash between rows.
            # macOS/Linux: fsync on an O_RDONLY dir fd flushes the inode.
            try:
                dir_fd = os.open(str(out_path.parent), os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except OSError:
                pass  # non-fatal; row data is still in file

        if not jobs:
            print("[tournament] nothing to do; all jobs already in resume CSV.",
                  file=sys.stderr)
            return [], out_path

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
                # Per-row persist: mid-run crash preserves everything up to here.
                writer.writerow(res)
                csv_file.flush()
                os.fsync(csv_file.fileno())
                if (i + 1) % 10 == 0:
                    elapsed = time.time() - start
                    print(f"[{i+1}/{len(jobs)}] elapsed={elapsed:.0f}s", file=sys.stderr)

    total = len(results)
    crashed = sum(1 for r in results if r.get("crashed"))
    elapsed = time.time() - start
    print(
        f"[done] {total} new matches in {elapsed:.0f}s "
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
    ap.add_argument(
        "--resume-from",
        default=None,
        help="Optional path to a prior CSV; (red,blue,layout,seed) combos present "
             "there are skipped. If omitted and --out already exists, --out itself "
             "is used as the resume source and appended to in place.",
    )
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
        resume_from=args.resume_from,
    )


if __name__ == "__main__":
    main()

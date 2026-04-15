"""
run_match.py — Single game subprocess wrapper for tournament evaluation.

Spawns one `capture.py` invocation with:
- Optional CPU pinning (Linux) for reproducible timing during parallel tournament
- Seed-fixed for Common Random Numbers (CRN) pairing
- Structured result parsing from stdout

Called by tournament.py in a ProcessPoolExecutor. Must run fast (<100ms
overhead beyond the game itself) so the pool can saturate physical cores.

Usage:
    python experiments/run_match.py \\
        --red zoo_dummy --blue baseline \\
        --layout defaultCapture --seed 42 \\
        --pin-core 0 --timeout 120

Returns JSON on stdout: {red, blue, layout, seed, winner, score, red_win, blue_win, tie, crashed, wall_time}

CS470 A3 constraints reminder:
- Only numpy + pandas deps allowed (no extras here either)
- Framework owns signal.SIGALRM — this wrapper does not touch it
- Parallel workers ≤ physical cores (enforced by tournament.py, not here)
"""

from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MINICONTEST = REPO_ROOT / "minicontest"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"

# pm14 α-post Option A: we now call a wrapper that imports capture.py's
# runGames directly instead of shelling out to capture.py (whose __main__
# block runs a 4-loop over your_baseline1..3+baseline, inflating wall
# time ~4×). single_game.py skips the 4-loop while leaving capture.py
# untouched. See single_game.py docstring for the full rationale.
SINGLE_GAME = REPO_ROOT / "experiments" / "single_game.py"


def pin_to_core(core: int) -> None:
    """Pin the current process to a single CPU core (Linux only; macOS is no-op)."""
    if hasattr(os, "sched_setaffinity"):
        try:
            os.sched_setaffinity(0, {core})
        except OSError:
            pass  # degrade gracefully; macOS falls through


def run_match(
    red: str,
    blue: str,
    layout: str = "defaultCapture",
    seed: int | None = None,
    timeout_s: float = 120.0,
    pin_core: int | None = None,
    red_opts: str = "",
    blue_opts: str = "",
) -> dict:
    """Run one capture.py match; return structured result.

    Seed policy (CS470 A3 workaround, applied 2026-04-15 pm7):
    - capture.py's ``--fixRandomSeed`` handler hardcodes
      ``random.seed('cs188')`` — a constant — so the seed VALUE we pass
      is dropped on the floor. Passing the flag therefore collapses
      every invocation to an identical PRNG state. pm6 empirical
      confirmation: 200/210 tournament matches tied.
    - Instead we route the seed through the layout axis. When ``layout``
      is the bare string "RANDOM" and ``seed`` is given, the effective
      layout becomes ``f"RANDOM{seed}"`` so capture.py's mazeGenerator
      uses our seed to deterministically pick a layout variant.
    - For named layouts (e.g., "defaultCapture"), the seed has no
      honored injection point, so we omit ``--fixRandomSeed`` entirely.
      capture.py then uses its default (system-clock-seeded) RNG,
      giving real per-invocation variance across repeats. We lose
      bit-for-bit reproducibility in exchange for usable signal in an
      averaged tournament. The tournament's seed field remains a
      repetition index and CSV dedup key.
    """
    if pin_core is not None:
        pin_to_core(pin_core)

    # Translate the tournament's seed into capture.py's one honored
    # seed axis: the RANDOM<N> layout-generator form. Named layouts
    # have no seed injection point; we rely on clock-seeded PRNG there.
    if seed is not None and layout == "RANDOM":
        effective_layout = f"RANDOM{seed}"
    else:
        effective_layout = layout

    cmd = [
        str(VENV_PYTHON),
        str(SINGLE_GAME),
        "-r", red,
        "-b", blue,
        "-l", effective_layout,
        "-n", "1",
        "-q",  # quiet
    ]
    # IMPORTANT: do NOT append --fixRandomSeed. See docstring above.

    # Forward team-specific options (e.g. "weights=/tmp/genome.json") so
    # evolve.py (M5/M6) can inject a custom weight set via the zoo agent's
    # `createTeam(weights=...)` kwarg. Empty strings skipped for
    # backward-compat with callers that pass red_opts="".
    if red_opts:
        cmd += ["--redOpts", red_opts]
    if blue_opts:
        cmd += ["--blueOpts", blue_opts]

    env = os.environ.copy()
    if seed is not None:
        env["PYTHONHASHSEED"] = str(seed)  # dict iteration only; harmless

    start = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(MINICONTEST),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        stdout = proc.stdout
        stderr = proc.stderr
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        return {
            "red": red, "blue": blue, "layout": layout, "seed": seed,
            "winner": None, "score": None, "red_win": 0, "blue_win": 0, "tie": 0,
            "crashed": True, "crash_reason": "subprocess_timeout",
            "wall_time": timeout_s,
        }

    wall = time.time() - start

    # pm14 α-post Option A: single_game.py writes a canonical one-line
    # JSON on stdout: {winner, score, red_win, blue_win, tie, crashed,
    # crash_reason}. The old regex-based parsing against capture.py's
    # human-readable log lines is gone — it only existed because we
    # couldn't modify capture.py, and now we never read capture.py's
    # prints (single_game.py suppresses them through `-q`).
    winner = None
    score: float | None = None
    red_win = blue_win = tie = 0
    crashed = (exit_code != 0)
    crash_reason = f"nonzero_exit:{exit_code}" if crashed else None

    try:
        lines = [ln for ln in stdout.strip().splitlines() if ln.strip()]
        if lines:
            payload = json.loads(lines[-1])
            winner = payload.get("winner")
            score = payload.get("score")
            red_win = int(payload.get("red_win", 0))
            blue_win = int(payload.get("blue_win", 0))
            tie = int(payload.get("tie", 0))
            # single_game.py's self-reported crash (import, parser, or
            # runGames failure) takes precedence over exit_code alone,
            # because the script may exit 0 even after emitting a crash
            # payload.
            sg_crashed = bool(payload.get("crashed", False))
            sg_reason = payload.get("crash_reason")
            if sg_crashed:
                crashed = True
                if sg_reason:
                    crash_reason = sg_reason
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        crashed = True
        crash_reason = f"parse_fail:{type(e).__name__}:{e}"

    return {
        "red": red, "blue": blue, "layout": layout, "seed": seed,
        "winner": winner, "score": score,
        "red_win": red_win, "blue_win": blue_win, "tie": tie,
        "crashed": crashed, "crash_reason": crash_reason,
        "wall_time": round(wall, 3),
        "exit_code": exit_code,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run one capture.py match and emit JSON result.")
    ap.add_argument("--red", required=True, help="Red team name (e.g. zoo_dummy)")
    ap.add_argument("--blue", required=True, help="Blue team name (e.g. baseline)")
    ap.add_argument("--layout", default="defaultCapture")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--pin-core", type=int, default=None)
    ap.add_argument(
        "--red-opts", default="",
        help="Pass-through to capture.py --redOpts (e.g. 'weights=/tmp/g.json')",
    )
    ap.add_argument(
        "--blue-opts", default="",
        help="Pass-through to capture.py --blueOpts",
    )
    args = ap.parse_args()

    result = run_match(
        red=args.red,
        blue=args.blue,
        layout=args.layout,
        seed=args.seed,
        timeout_s=args.timeout,
        pin_core=args.pin_core,
        red_opts=args.red_opts,
        blue_opts=args.blue_opts,
    )
    print(json.dumps(result))
    return 0 if not result["crashed"] else 2


if __name__ == "__main__":
    sys.exit(main())

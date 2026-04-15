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
        "capture.py",
        "-r", red,
        "-b", blue,
        "-l", effective_layout,
        "-n", "1",
        "-q",  # quiet
    ]
    # IMPORTANT: do NOT append --fixRandomSeed. See docstring above.

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

    # Parse capture.py stdout. Typical lines:
    #   "The Red team has returned at least N of the opponents' dots."
    #   "The Blue team has returned at least N of the opponents' dots."
    #   "Time is up.\nTie game!"  OR  "The Red team wins by N points." / "The Blue team wins by N points."
    #   "Average Score: X.X"
    #   "Red Win Rate:  n/m (p)"  "Blue Win Rate:  n/m (p)"
    red_win, blue_win, tie = 0, 0, 0
    winner = None
    score = None
    crashed = False
    crash_reason = None

    if exit_code != 0:
        crashed = True
        crash_reason = f"nonzero_exit:{exit_code}"

    if "Red agent crashed" in stderr or "Red agent crashed" in stdout:
        crashed = True
        crash_reason = "red_crashed"
        blue_win = 1
        winner = "Blue"
    elif "Blue agent crashed" in stderr or "Blue agent crashed" in stdout:
        crashed = True
        crash_reason = "blue_crashed"
        red_win = 1
        winner = "Red"
    elif "The Red team wins" in stdout or "The Red team has returned" in stdout:
        red_win = 1
        winner = "Red"
    elif "The Blue team wins" in stdout or "The Blue team has returned" in stdout:
        blue_win = 1
        winner = "Blue"
    elif "Tie game" in stdout or "Time is up" in stdout:
        tie = 1
        winner = "Tie"

    m = re.search(r"Average Score:\s*(-?[\d.]+)", stdout)
    if m:
        try:
            score = float(m.group(1))
        except ValueError:
            score = None

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
    args = ap.parse_args()

    result = run_match(
        red=args.red,
        blue=args.blue,
        layout=args.layout,
        seed=args.seed,
        timeout_s=args.timeout,
        pin_core=args.pin_core,
    )
    print(json.dumps(result))
    return 0 if not result["crashed"] else 2


if __name__ == "__main__":
    sys.exit(main())

"""experiments/single_game.py — run ONE capture.py game WITHOUT the 4-loop
harness in capture.py's `__main__`.

Background
----------
`capture.py` (immutable per CLAUDE.md) has a `__main__` block that wraps
`runGames` in `for i in range(len(lst))` with
`lst = ['your_baseline1.py','your_baseline2.py','your_baseline3.py','baseline.py']`
to emit the assignment's 4-way comparison `output.csv`. Every shell
invocation `python capture.py -r X -b Y -n 1 -q` therefore plays **four**
games (one per lst entry), even though our evolution pipeline wants one.

Measured consequence (pm13 M4b-4 dry-run): effective per-match wall was
10.5s, 4× higher than the single-game cost inside `runGames` itself. M6
budget re-extrapolated to ~103h vs STRATEGY's 20h target — a 5× overrun
entirely attributable to this hidden 4× amplification.

Fix (pm14 α-post, Option A)
---------------------------
Import `capture.readCommand` + `capture.runGames` directly and call them
from this wrapper. `capture.py`'s `__main__` block never executes under
import, so the 4-loop is skipped while every function capture.py exposes
is reused verbatim. No framework file is modified (CLAUDE.md compliant).

Usage
-----
    python experiments/single_game.py \\
        -r <red_team> -b <blue_team> -l <layout> \\
        [--redOpts 'weights=/tmp/g.json'] [--blueOpts ''] \\
        [-q] [--fixRandomSeed]

Returns one-line JSON on stdout; crash / error paths set
`crashed=True` + `crash_reason=<classified>`.
"""

from __future__ import annotations
import json
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MINICONTEST = REPO_ROOT / "minicontest"


def _emit(payload: dict) -> None:
    """Print a canonical one-line JSON result."""
    print(json.dumps(payload))


def main() -> int:
    # capture.py's `imp.load_source`, `from util import ...`, `from game
    # import ...` all resolve relative to the *current working directory*.
    # run_match.py used to set cwd=MINICONTEST when shelling out; we must
    # do the same here because this wrapper is launched from the repo root.
    os.chdir(str(MINICONTEST))
    sys.path.insert(0, str(MINICONTEST))

    try:
        from capture import readCommand, runGames
    except Exception as e:
        _emit({
            "winner": None, "score": None,
            "red_win": 0, "blue_win": 0, "tie": 0,
            "crashed": True,
            "crash_reason": f"capture_import_failed:{type(e).__name__}:{e}",
        })
        return 2

    # `readCommand(argv, blue_team)` uses blue_team only as the parser
    # default for --blue. A user-supplied -b / --blue will override it.
    # We still look up the argv token so the default equals the final value
    # (keeps readCommand's print line tidy).
    argv = sys.argv[1:]
    blue_team = "baseline"
    for i, tok in enumerate(argv):
        if tok in ("-b", "--blue") and i + 1 < len(argv):
            blue_team = argv[i + 1]
            break

    try:
        options = readCommand(argv, blue_team)
    except SystemExit as e:
        # OptionParser exits on --help or bad args
        _emit({
            "winner": None, "score": None,
            "red_win": 0, "blue_win": 0, "tie": 0,
            "crashed": True,
            "crash_reason": f"readCommand_sysexit:{e}",
        })
        return 3
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        _emit({
            "winner": None, "score": None,
            "red_win": 0, "blue_win": 0, "tie": 0,
            "crashed": True,
            "crash_reason": f"readCommand_failed:{type(e).__name__}:{e}",
        })
        return 3

    # Force a single game regardless of what the user passed for -n. The
    # 4-loop we're skipping is the *outer* loop over lst, but readCommand
    # still builds `numGames` layouts from -n. We trim to 1 here so
    # runGames doesn't run a pointless inner repeat.
    options["numGames"] = 1
    options["layouts"] = options["layouts"][:1]

    try:
        games, avg_score, red_win_rate, red_lose_rate = runGames(**options)
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        _emit({
            "winner": None, "score": None,
            "red_win": 0, "blue_win": 0, "tie": 0,
            "crashed": True,
            "crash_reason": f"runGames_failed:{type(e).__name__}:{e}",
        })
        return 4

    # Decode the one game's outcome. `score > 0` = red wins by that margin,
    # `< 0` = blue. Ties are score == 0. An agent crash inside run
    # surfaces as the opposite team's +N/-N score (CaptureRules handles
    # it internally) so we count it as a normal win/loss, matching the
    # fitness signal in evaluate_genome.
    if games:
        score = games[-1].state.data.score
        if score > 0:
            winner, rw, bw, tie = "Red", 1, 0, 0
        elif score < 0:
            winner, rw, bw, tie = "Blue", 0, 1, 0
        else:
            winner, rw, bw, tie = "Tie", 0, 0, 1
        score_out: float | None = float(score)
    else:
        winner, rw, bw, tie, score_out = None, 0, 0, 0, None

    _emit({
        "winner": winner,
        "score": score_out,
        "red_win": rw,
        "blue_win": bw,
        "tie": tie,
        "crashed": False,
        "crash_reason": None,
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())

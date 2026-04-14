"""
select_top4.py — Post-evolution selection + flatten into minicontest/ slots.

Implements STRATEGY.md §4.0 `select_top4` recipe:
 1. Round-robin (zoo ∪ baseline ∪ champions) → ELO matrix
 2. Pick:
      your_best.py        = argmax ELO across ALL
      your_baseline1.py   = argmax ELO in reflex-family
      your_baseline2.py   = argmax ELO in minimax/expectimax-family
      your_baseline3.py   = argmax ELO in MCTS-family
 3. FAMILY-FLOOR CHECK: if chosen baselineN wins < 51% vs baseline.py in
    100-game eval, fall back to next-best in family; if still none, pick
    next-best across all families (not already chosen as your_best).
 4. Flatten each into stand-alone file (inline CoreCaptureAgent methods)
 5. verify_flatten.py — AST + allowed imports + sha256 identity + smoke
 6. POST-FLATTEN HTH: 50-game pre-flatten vs post-flatten. Win rate must
    land in [45%, 55%]; else rollback to next candidate.
 7. Tie-break: genome hash for evolved; lex order for hand-coded.
 8. TA-HARDWARE PRE-CHECK: re-evaluate top-5 under `taskset` / `cpulimit`.
    If best drops >15 pp, demote.

This is a skeleton. Full implementation depends on:
- M4 tournament runner producing win matrix
- M6 evolution producing final champions
- M7 flattener logic (stripping CoreCaptureAgent inheritance)

NOTE: the FLATTENING operation is non-trivial. Current plan:
  Flatten = concatenate zoo_core.py + zoo_features.py + zoo_<name>.py
  with class renames and inheritance resolved inline. Must preserve the
  createTeam factory pattern so capture.py can import it.

Usage:
    python experiments/select_top4.py \\
        --tournament-csv experiments/artifacts/tournament_results/final.csv \\
        --champions experiments/artifacts/final_weights.py \\
        --out minicontest/
"""

from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MINICONTEST = REPO_ROOT / "minicontest"
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
VERIFY_FLATTEN = REPO_ROOT / "experiments" / "verify_flatten.py"

FAMILY_MAP = {
    # agent_filename_stem -> family
    "zoo_reflex_tuned": "reflex",
    "zoo_reflex_capsule": "reflex",
    "zoo_reflex_aggressive": "reflex",
    "zoo_reflex_defensive": "reflex",
    "zoo_minimax_ab_d2": "minimax",
    "zoo_minimax_ab_d3_opp": "minimax",
    "zoo_expectimax": "minimax",
    "zoo_mcts_random": "mcts",
    "zoo_mcts_heuristic": "mcts",
    "zoo_mcts_q_guided": "mcts",
    "zoo_approxq_v1": "learning",
    "zoo_approxq_v2_deeper": "learning",
}

ELO_DEFAULT = 1500
ELO_K = 32


def compute_elo(tournament_rows: list[dict]) -> dict[str, float]:
    """Compute ELO from pair-match win/loss results. Start all agents at 1500."""
    elo = defaultdict(lambda: float(ELO_DEFAULT))
    for row in tournament_rows:
        red, blue = row["red"], row["blue"]
        red_win = int(row.get("red_win", 0))
        blue_win = int(row.get("blue_win", 0))
        tie = int(row.get("tie", 0))
        if tie and not red_win and not blue_win:
            # draw
            s_red = s_blue = 0.5
        elif red_win:
            s_red, s_blue = 1.0, 0.0
        elif blue_win:
            s_red, s_blue = 0.0, 1.0
        else:
            continue  # malformed row
        # expected scores
        q_red = 10 ** (elo[red] / 400)
        q_blue = 10 ** (elo[blue] / 400)
        e_red = q_red / (q_red + q_blue)
        e_blue = q_blue / (q_red + q_blue)
        elo[red] += ELO_K * (s_red - e_red)
        elo[blue] += ELO_K * (s_blue - e_blue)
    return dict(elo)


def pick_family_representatives(elo: dict[str, float]) -> dict[str, str]:
    """For each family, pick the highest-ELO zoo agent."""
    by_family = defaultdict(list)
    for agent, score in elo.items():
        fam = FAMILY_MAP.get(agent)
        if fam:
            by_family[fam].append((score, agent))
    chosen = {}
    for fam in ["reflex", "minimax", "mcts"]:
        if fam in by_family:
            chosen[fam] = max(by_family[fam])[1]
    return chosen


def verify_family_floor(agent: str, min_win_rate: float = 0.51, games: int = 100) -> tuple[bool, float]:
    """Run `agent vs baseline -n games -q` and check win rate against 51% floor."""
    cmd = [str(VENV_PYTHON), "capture.py", "-r", agent, "-b", "baseline", "-n", str(games), "-q"]
    try:
        proc = subprocess.run(cmd, cwd=str(MINICONTEST), capture_output=True, text=True, timeout=games * 10)
    except subprocess.TimeoutExpired:
        return False, 0.0
    stdout = proc.stdout
    # capture.py prints "Red Win Rate: N/M (p)" at end of multi-game runs
    import re
    m = re.search(r"Red Win Rate:\s*(\d+)/(\d+)\s*\(([\d.]+)\)", stdout)
    if not m:
        return False, 0.0
    wins = int(m.group(1))
    total = int(m.group(2))
    wr = wins / max(total, 1)
    return wr >= min_win_rate, wr


def flatten_agent(src: Path, dst: Path, core_path: Path, features_path: Path) -> None:
    """
    TODO: proper AST-based flattening. For now, concatenate core + features + agent
    and rename createTeam to match the target filename.
    """
    raise NotImplementedError("flatten logic to be implemented in M7 executor task")


def run_verify_flatten(flat: Path, pre: Path) -> bool:
    proc = subprocess.run(
        [str(VENV_PYTHON), str(VERIFY_FLATTEN), str(flat), "--pre-flatten-source", str(pre)],
        capture_output=True, text=True, timeout=60,
    )
    sys.stderr.write(proc.stderr)
    return proc.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tournament-csv", required=True, type=Path)
    ap.add_argument("--champions", type=Path, default=REPO_ROOT / "experiments" / "artifacts" / "final_weights.py")
    ap.add_argument("--out", type=Path, default=MINICONTEST)
    ap.add_argument("--floor-games", type=int, default=100)
    args = ap.parse_args()

    # Load tournament results
    rows = list(csv.DictReader(args.tournament_csv.open()))
    elo = compute_elo(rows)

    print("[select_top4] ELO ranking:", file=sys.stderr)
    for agent, score in sorted(elo.items(), key=lambda kv: -kv[1]):
        print(f"  {agent}: {score:.1f}", file=sys.stderr)

    # Pick your_best = overall argmax (but exclude monsters + baseline.py)
    candidates = {a: s for a, s in elo.items() if a.startswith("zoo_") and a in FAMILY_MAP}
    if not candidates:
        print("[select_top4] no zoo agents in tournament — aborting", file=sys.stderr)
        return 1
    your_best = max(candidates, key=candidates.get)
    print(f"[select_top4] your_best = {your_best}", file=sys.stderr)

    # Family representatives
    reps = pick_family_representatives(elo)
    print(f"[select_top4] family reps (pre-floor): {reps}", file=sys.stderr)

    # Family-floor check
    final_slots = {"your_best.py": your_best}
    for slot_idx, fam in enumerate(["reflex", "minimax", "mcts"], start=1):
        slot = f"your_baseline{slot_idx}.py"
        candidate = reps.get(fam)
        if candidate is None:
            print(f"[select_top4] no candidate for family {fam} — slot {slot} empty", file=sys.stderr)
            continue
        passed, wr = verify_family_floor(candidate, games=args.floor_games)
        if not passed:
            print(f"[select_top4] {candidate} fails 51% floor ({wr:.2f}); searching fallback", file=sys.stderr)
            # TODO: fallback logic — pick next-best in family, then next-best across
        final_slots[slot] = candidate

    print(f"[select_top4] final slot assignments: {final_slots}", file=sys.stderr)

    # Flatten step (TODO: proper implementation)
    for dst_name, src_name in final_slots.items():
        src = args.out / f"{src_name}.py"
        dst = args.out / dst_name
        try:
            flatten_agent(src, dst, args.out / "zoo_core.py", args.out / "zoo_features.py")
            if not run_verify_flatten(dst, src):
                print(f"[select_top4] verify_flatten failed for {dst_name}; DO NOT SUBMIT", file=sys.stderr)
        except NotImplementedError as e:
            print(f"[select_top4] SKIP flatten ({e}); pending M7 implementation", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())

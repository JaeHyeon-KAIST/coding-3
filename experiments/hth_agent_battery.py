"""experiments/hth_agent_battery.py — HTH battery for multiple *named agents*.

Generalises experiments/hth_battery.py from weights-override comparison
(single container agent with different genome JSONs) to direct multi-agent
comparison (any minicontest/{agent}.py modules). Needed for the pm20
D-series family evaluation (zoo_reflex_A1 vs zoo_reflex_A1_D1 vs
zoo_reflex_A1_D3 — different AGENT classes, not just weights).

For each (agent, opponent) pair:
  - Plays N games split across --layouts × 2 colors (to cancel color bias)
  - Distinct seed per (layout, rep) for CRN coverage
  - Aggregates wins from the agent's perspective (red-win when agent is red,
    blue-win when agent is blue)
  - Reports Wilson 95% CI + crash rate

Usage:
    .venv/bin/python experiments/hth_agent_battery.py \\
        --agents zoo_reflex_A1 zoo_reflex_A1_D1 zoo_reflex_A1_D3 \\
        --opponents baseline monster_rule_expert zoo_reflex_h1test \\
        --games-per-pair 40 --layouts defaultCapture RANDOM \\
        --workers 8 --out experiments/artifacts/hth_dseries.csv
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_match import run_match  # noqa: E402


def wilson_95(wins: int, total: int) -> tuple[float, float, float]:
    if total == 0:
        return 0.0, 0.0, 1.0
    p = wins / total
    z = 1.96
    denom = 1 + z * z / total
    centre = p + z * z / (2 * total)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return p, (centre - spread) / denom, (centre + spread) / denom


def play_one(agent: str, opp: str, agent_is_red: bool, layout: str, seed: int):
    if agent_is_red:
        red, blue = agent, opp
    else:
        red, blue = opp, agent
    try:
        result = run_match(
            red=red, blue=blue, layout=layout, seed=seed, timeout_s=120.0,
        )
    except Exception as exc:
        result = {"crashed": True, "red_win": 0, "blue_win": 0,
                  "crash_reason": f"wrapper:{type(exc).__name__}:{exc}"}
    crashed = bool(result.get("crashed", False))
    win = int(result.get("red_win" if agent_is_red else "blue_win", 0))
    return {
        "agent": agent,
        "opp": opp,
        "color": "red" if agent_is_red else "blue",
        "layout": layout,
        "seed": seed,
        "win": win,
        "crashed": int(crashed),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", nargs="+", required=True,
                    help="Agent module stems under minicontest/.")
    ap.add_argument("--opponents", nargs="+", required=True,
                    help="Opponent module stems under minicontest/.")
    ap.add_argument("--games-per-pair", type=int, default=40,
                    help="Games per (agent, opponent) pair. Split across "
                         "len(layouts) * 2 colors.")
    ap.add_argument("--layouts", nargs="+", default=["defaultCapture", "RANDOM"])
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--master-seed", type=int, default=42)
    ap.add_argument("--out", required=True, help="CSV output path.")
    args = ap.parse_args()

    # Build match list.
    matches = []
    per_config = max(1, args.games_per_pair // (len(args.layouts) * 2))
    actual_per_pair = per_config * len(args.layouts) * 2
    for agent in args.agents:
        for opp in args.opponents:
            for li, layout in enumerate(args.layouts):
                for rep in range(per_config):
                    seed = args.master_seed + li * 997 + rep + hash(agent + opp) % 10000
                    matches.append((agent, opp, True, layout, seed))
                    matches.append((agent, opp, False, layout, seed))
    total = len(matches)
    print(f"[hth-agent] scheduled {total} matches "
          f"({len(args.agents)} agents × {len(args.opponents)} opps × "
          f"{len(args.layouts)} layouts × 2 colors × {per_config} reps "
          f"= {actual_per_pair}/pair), workers={args.workers}",
          file=sys.stderr)

    per_pair = defaultdict(lambda: {"wins": 0, "crashes": 0, "total": 0})
    rows = []
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(play_one, *m) for m in matches]
        for fut in as_completed(futures):
            try:
                row = fut.result()
            except Exception as exc:
                print(f"[hth-agent] worker error: {type(exc).__name__}: {exc}",
                      file=sys.stderr)
                continue
            key = (row["agent"], row["opp"])
            per_pair[key]["wins"] += row["win"]
            per_pair[key]["crashes"] += row["crashed"]
            per_pair[key]["total"] += 1
            rows.append(row)
            done += 1
            if done % max(1, total // 10) == 0:
                print(f"[hth-agent] progress {done}/{total}", file=sys.stderr)

    # Write CSV
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        f.write("agent,opp,color,layout,seed,win,crashed\n")
        for r in rows:
            f.write(f"{r['agent']},{r['opp']},{r['color']},{r['layout']},"
                    f"{r['seed']},{r['win']},{r['crashed']}\n")
    print(f"[hth-agent] CSV: {out_path}", file=sys.stderr)

    # Summary table
    print()
    print(f"HTH Agent Battery — agents={args.agents} vs opponents={args.opponents}")
    header = f"{'agent':<28}  {'opponent':<28}  {'W/N':<10}  {'WR':>6}  {'95% Wilson CI':<22}  {'crash':>6}"
    print(header)
    print("-" * len(header))
    for agent in args.agents:
        for opp in args.opponents:
            stats = per_pair.get((agent, opp), {"wins": 0, "crashes": 0, "total": 0})
            w, n, c = stats["wins"], stats["total"], stats["crashes"]
            p, lo, hi = wilson_95(w, n)
            print(f"{agent:<28}  {opp:<28}  {w}/{n:<7}  {p:>6.3f}  "
                  f"[{lo:.3f}, {hi:.3f}]   {c:>6}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

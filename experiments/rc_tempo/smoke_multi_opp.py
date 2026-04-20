#!/usr/bin/env python3
"""Multi-opponent smoke harness for rc-tempo β iteration (pm30).

Default pool covers 11 paradigms so we can spot which defender archetype
β_chase fails against.  Thin wrapper over hth_resumable's primitives.

Usage (Mac sanity):
    .venv/bin/python experiments/rc_tempo/smoke_multi_opp.py \\
        --agent zoo_reflex_rc_tempo_beta \\
        --opponents baseline \\
        --layouts defaultCapture \\
        --games-per-cell 5 --workers 4 \\
        --out /tmp/sanity.csv

Usage (Server full smoke):
    .venv/bin/python experiments/rc_tempo/smoke_multi_opp.py \\
        --agent zoo_reflex_rc_tempo_beta \\
        --variant current \\
        --games-per-cell 15 --workers 16 \\
        --out experiments/artifacts/rc_tempo/smoke_pm30_current.csv
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / 'experiments'))
sys.path.insert(0, str(HERE))

from hth_resumable import (  # noqa: E402
    FIELDS,
    append_row,
    load_completed,
    play_one,
    wilson_95,
)


DEFAULT_OPPONENTS = [
    'baseline',
    'zoo_reflex_rc82',
    'zoo_reflex_rc166',
    'zoo_reflex_rc16',
    'zoo_reflex_rc02',
    'zoo_reflex_rc32',
    'zoo_reflex_rc47',
    'zoo_reflex_h1test',
    'zoo_reflex_h1c',
    'monster_rule_expert',
    'zoo_distill_rc22',
]

DEFAULT_LAYOUTS = ['defaultCapture', 'distantCapture']
DEFAULT_COLORS = ['red', 'blue']


def build_work(agent, opponents, layouts, colors, games_per_cell, master_seed,
               done, metrics_csv):
    work = []
    for opp in opponents:
        for li, layout in enumerate(layouts):
            for ci, color in enumerate(colors):
                for g in range(games_per_cell):
                    seed = master_seed + li * 997 + ci * 53 + g
                    key = (opp, layout, color, seed, g)
                    if key in done:
                        continue
                    work.append((agent, opp, layout, color, seed, g, metrics_csv))
    return work


def summarize(csv_path, agent):
    """Print per-opponent + per-layout WR table with Wilson CI."""
    if not Path(csv_path).exists():
        print("[smoke] no csv to summarize")
        return
    rows = []
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    rows = [r for r in rows if r['agent_a'] == agent]
    # Per (opp, layout)
    agg = {}
    for r in rows:
        k = (r['opp'], r['layout'])
        if k not in agg:
            agg[k] = {'wins': 0, 'total': 0, 'crashes': 0}
        wincol = 'red_win' if r['color'] == 'red' else 'blue_win'
        agg[k]['wins'] += int(r[wincol])
        agg[k]['total'] += 1
        agg[k]['crashes'] += int(r['crashed'])
    # Per opponent aggregated over layouts
    agg_opp = {}
    for (opp, layout), s in agg.items():
        if opp not in agg_opp:
            agg_opp[opp] = {'wins': 0, 'total': 0, 'crashes': 0}
        agg_opp[opp]['wins'] += s['wins']
        agg_opp[opp]['total'] += s['total']
        agg_opp[opp]['crashes'] += s['crashes']
    # Overall
    tot_w = sum(s['wins'] for s in agg_opp.values())
    tot_n = sum(s['total'] for s in agg_opp.values())
    tot_c = sum(s['crashes'] for s in agg_opp.values())

    print()
    print(f"=== SMOKE {agent} ===")
    print(f"{'opp':<26} {'layout':<18} {'w/n':<12} {'WR':>7} {'Wilson 95% CI':<22} {'crash':>6}")
    print('-' * 100)
    for (opp, layout), s in sorted(agg.items()):
        if s['total'] == 0:
            continue
        p, lo, hi = wilson_95(s['wins'], s['total'])
        print(f"{opp:<26} {layout:<18} {s['wins']}/{s['total']:<9}  {p:>7.3f}  "
              f"[{lo:.3f}, {hi:.3f}]   {s['crashes']:>6}")

    print()
    print(f"{'opp':<26} {'TOTAL':<18} {'w/n':<12} {'WR':>7} {'Wilson 95% CI':<22} {'crash':>6}")
    print('-' * 100)
    for opp, s in sorted(agg_opp.items()):
        if s['total'] == 0:
            continue
        p, lo, hi = wilson_95(s['wins'], s['total'])
        print(f"{opp:<26} {'(all layouts)':<18} {s['wins']}/{s['total']:<9}  {p:>7.3f}  "
              f"[{lo:.3f}, {hi:.3f}]   {s['crashes']:>6}")

    if tot_n:
        p, lo, hi = wilson_95(tot_w, tot_n)
        print('-' * 100)
        print(f"{'OVERALL':<26} {'':<18} {tot_w}/{tot_n:<9}  {p:>7.3f}  "
              f"[{lo:.3f}, {hi:.3f}]   {tot_c:>6}")


def summarize_metrics(metrics_csv):
    """If agent wrote per-game metrics, print chase-success stats."""
    if not metrics_csv or not Path(metrics_csv).exists():
        return
    rows = []
    try:
        with open(metrics_csv) as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        print(f"[smoke] metrics csv parse failed: {e}")
        return
    if not rows:
        return
    # Filter by opponent context (opp appears in game_id)
    from collections import defaultdict
    per_opp = defaultdict(lambda: {'n': 0, 'scared': 0, 'tempo_on': 0,
                                    'eat_ticks': [], 'foods_a': 0, 'foods_b': 0})
    for r in rows:
        gid = r.get('game_id', '')
        # game_id pattern: {agent}_{opp}_{layout}_{color}_{seed}_{game_idx}
        parts = gid.split('_')
        opp = 'unknown'
        for i, p in enumerate(parts):
            if p.startswith('baseline') or p.startswith('zoo') or p.startswith('monster'):
                # hit opp — concat until we see a layout
                opp = p
                if i + 1 < len(parts) and (parts[i + 1].startswith('reflex') or
                                            parts[i + 1].startswith('rule') or
                                            parts[i + 1].startswith('distill')):
                    opp = f"{p}_{parts[i + 1]}"
                    if i + 2 < len(parts) and parts[i + 2] in {'rc82', 'rc166', 'rc16',
                                                                'rc02', 'rc32', 'rc47',
                                                                'h1test', 'h1c', 'rc22',
                                                                'expert'}:
                        opp = f"{opp}_{parts[i + 2]}"
                break
        d = per_opp[opp]
        d['n'] += 1
        try:
            if r.get('scared_seen', '').lower() == 'true':
                d['scared'] += 1
            if r.get('tempo_enabled', '').lower() == 'true':
                d['tempo_on'] += 1
            tick = int(r.get('capsule_ate_tick', -1) or -1)
            if tick > 0:
                d['eat_ticks'].append(tick)
            d['foods_a'] += int(r.get('foods_on_scared_a', 0) or 0)
            d['foods_b'] += int(r.get('foods_on_scared_b', 0) or 0)
        except Exception:
            pass

    print()
    print('=== CHASE METRICS ===')
    print(f"{'opp':<36} {'n':>4} {'tempo%':>7} {'scared%':>8} "
          f"{'avg_eat_tick':>13} {'avg_food_A':>11} {'avg_food_B':>11}")
    print('-' * 100)
    for opp, d in sorted(per_opp.items()):
        if d['n'] == 0:
            continue
        tempo_pct = 100 * d['tempo_on'] / d['n']
        scared_pct = 100 * d['scared'] / d['n']
        eat_avg = (sum(d['eat_ticks']) / len(d['eat_ticks'])) if d['eat_ticks'] else -1
        food_a_avg = d['foods_a'] / max(1, d['n'])
        food_b_avg = d['foods_b'] / max(1, d['n'])
        print(f"{opp:<36} {d['n']:>4} {tempo_pct:>6.1f}% {scared_pct:>7.1f}% "
              f"{eat_avg:>13.1f} {food_a_avg:>11.2f} {food_b_avg:>11.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agent', default='zoo_reflex_rc_tempo_beta')
    ap.add_argument('--variant', default='default',
                    help='label for this smoke (appears in metrics csv name)')
    ap.add_argument('--opponents', nargs='+', default=DEFAULT_OPPONENTS)
    ap.add_argument('--layouts', nargs='+', default=DEFAULT_LAYOUTS)
    ap.add_argument('--colors', nargs='+', default=DEFAULT_COLORS)
    ap.add_argument('--games-per-cell', type=int, default=15)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--master-seed', type=int, default=42)
    ap.add_argument('--out', required=True)
    ap.add_argument('--metrics-out', default=None)
    args = ap.parse_args()

    # Derive metrics csv if not set
    if args.metrics_out is None:
        out_path = Path(args.out)
        args.metrics_out = str(out_path.parent / f"metrics_{out_path.stem}.csv")

    done = load_completed(args.out)
    print(f"[smoke] resume: {len(done)} completed rows in {args.out}", file=sys.stderr)

    work = build_work(args.agent, args.opponents, args.layouts, args.colors,
                       args.games_per_cell, args.master_seed, done, args.metrics_out)
    total = len(work)
    if total == 0:
        print("[smoke] nothing to do (all completed)", file=sys.stderr)
    else:
        print(f"[smoke] scheduled {total} games  opp={len(args.opponents)}  "
              f"lay={len(args.layouts)}  col={len(args.colors)}  workers={args.workers}",
               file=sys.stderr)

    t0 = time.time()
    written = 0
    if total:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(play_one, w) for w in work]
            for fut in as_completed(futures):
                try:
                    row = fut.result()
                except Exception as e:
                    print(f"[smoke] worker error: {type(e).__name__}: {e}",
                           file=sys.stderr)
                    continue
                append_row(args.out, row)
                written += 1
                if written % max(1, total // 20) == 0:
                    elapsed = time.time() - t0
                    eta = elapsed / max(1, written) * (total - written)
                    print(f"[smoke] progress {written}/{total}  "
                          f"elapsed={elapsed:.0f}s  ETA={eta:.0f}s",
                           file=sys.stderr)

    summarize(args.out, args.agent)
    summarize_metrics(args.metrics_out)


if __name__ == '__main__':
    main()

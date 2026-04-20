#!/usr/bin/env python3
"""Parallel test of risk map + DP orienteering across all 1-capsule layouts.

Per layout: (a) count-max DP, (b) risk-max DP with default weights.
Diffs which foods are selected; prints ASCII map with route overlay.

Usage:
    .venv/bin/python experiments/rc_tempo/test_risk_dp.py
    .venv/bin/python experiments/rc_tempo/test_risk_dp.py --layout defaultCapture
    .venv/bin/python experiments/rc_tempo/test_risk_dp.py --weights w_de=5.0,w_iso=3.0
"""
import argparse
import glob
import os
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
FIXTURE_DIR = os.path.join(REPO, 'experiments', 'artifacts', 'rc_tempo', 'fixtures')

sys.path.insert(0, HERE)
from risk_score import load_fixture, compute_risk_map, reachable_foods, orienteering_dp, DEFAULT_WEIGHTS


def parse_weights(spec):
    if not spec:
        return None
    out = {}
    for part in spec.split(','):
        k, v = part.split('=')
        out[k.strip()] = float(v)
    return out


def render_map(fixture, count_route, risk_route, team='red'):
    """ASCII map: . space, % wall, o food (unselected), C count-only route food,
    R risk-only route food, B both, $ capsule, | home column."""
    walls = fixture['walls']  # tuple[width][height]
    w, h = fixture['width'], fixture['height']
    foods = set(fixture['red_target_foods'] if team == 'red' else fixture['blue_target_foods'])
    caps = set(fixture['red_target_capsules'] if team == 'red' else fixture['blue_target_capsules'])
    homes = set(fixture['red_home_cells'] if team == 'red' else fixture['blue_home_cells'])
    mid = fixture['midline_x']

    count_cells = set(count_route['food_order'])
    risk_cells = set(risk_route['food_order'])

    # render top-down (y=h-1 at top)
    lines = []
    for y in range(h - 1, -1, -1):
        row = []
        for x in range(w):
            cell = (x, y)
            if walls[x][y]:
                row.append('%')
            elif cell in caps:
                row.append('$')
            elif cell in count_cells and cell in risk_cells:
                row.append('B')
            elif cell in count_cells:
                row.append('C')
            elif cell in risk_cells:
                row.append('R')
            elif cell in foods:
                row.append('.')
            elif cell in homes:
                row.append('|')
            elif x == mid:
                row.append(':')
            else:
                row.append(' ')
        lines.append(''.join(row))
    return '\n'.join(lines)


def run_one(args):
    layout_name, weights = args
    path = os.path.join(FIXTURE_DIR, layout_name)
    fixture = load_fixture(path)
    lay = fixture['layout_name']

    caps = fixture['red_target_capsules']
    if len(caps) != 1:
        return {
            'layout': lay,
            'skipped': f"V0.1 needs exactly 1 red capsule (got {len(caps)})",
        }
    capsule = caps[0]
    foods = fixture['red_target_foods']

    # risk map
    t0 = time.perf_counter()
    risk_scores, components = compute_risk_map(fixture, team='red', weights=weights)
    t_risk = time.perf_counter() - t0

    # reachable filter (budget 40)
    reachable = reachable_foods(fixture, capsule, foods, team='red', budget=40)

    t0 = time.perf_counter()
    count_result = orienteering_dp(fixture, capsule, reachable, team='red', budget=40, objective='count')
    t_count = time.perf_counter() - t0

    t0 = time.perf_counter()
    risk_result = orienteering_dp(fixture, capsule, reachable, team='red', budget=40,
                                   objective='risk', risk_scores=risk_scores)
    t_risk_dp = time.perf_counter() - t0

    # diff food picks
    count_set = set(count_result['food_order'])
    risk_set = set(risk_result['food_order'])
    common = count_set & risk_set
    only_count = count_set - risk_set
    only_risk = risk_set - count_set

    # score summary
    risk_of_count_route = sum(risk_scores.get(f, 0) for f in count_set)
    risk_of_risk_route = sum(risk_scores.get(f, 0) for f in risk_set)

    # Render ASCII (cells)
    render = render_map(fixture, count_result, risk_result, team='red')

    return {
        'layout': lay,
        'n_foods': len(foods),
        'n_reachable': len(reachable),
        'count_n': count_result['n_food'],
        'count_moves': count_result['total_moves'],
        'count_risk_sum': round(risk_of_count_route, 2),
        'risk_n': risk_result['n_food'],
        'risk_moves': risk_result['total_moves'],
        'risk_risk_sum': round(risk_of_risk_route, 2),
        'common': len(common),
        'only_count': len(only_count),
        'only_risk': len(only_risk),
        'only_count_cells': sorted(only_count),
        'only_risk_cells': sorted(only_risk),
        't_risk': round(t_risk, 4),
        't_count_dp': round(t_count, 3),
        't_risk_dp': round(t_risk_dp, 3),
        'render': render,
        'top5_risk': sorted(((f, round(risk_scores[f], 2), components[f])
                             for f in foods), key=lambda x: -x[1])[:5],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layout', default=None, help='single layout to test (with .pkl suffix or without)')
    ap.add_argument('--weights', default=None, help='comma-separated weight overrides, e.g. w_de=5.0,w_iso=3.0')
    ap.add_argument('--render', action='store_true', help='print ASCII map for each layout')
    args = ap.parse_args()

    weights = parse_weights(args.weights)
    print(f"Weights (after overrides): {dict(DEFAULT_WEIGHTS, **(weights or {}))}")

    if args.layout:
        name = args.layout if args.layout.endswith('.pkl') else args.layout + '.pkl'
        paths = [name]
    else:
        paths = sorted(os.path.basename(p) for p in glob.glob(os.path.join(FIXTURE_DIR, '*.pkl')))

    work = [(p, weights) for p in paths]
    t0 = time.perf_counter()
    with Pool(min(12, len(work))) as pool:
        results = pool.map(run_one, work)
    wall = time.perf_counter() - t0

    print(f"\nPool({min(12, len(work))}) wall: {wall:.2f}s")
    print("=" * 120)
    print(f"{'Layout':<22} {'Foods':<6} {'Reach':<6} "
          f"{'Cn':<4} {'Cmv':<4} {'Crsum':<7} "
          f"{'Rn':<4} {'Rmv':<4} {'Rrsum':<7} "
          f"{'∩':<3} {'onlyC':<6} {'onlyR':<6} "
          f"{'t_risk':<7} {'t_Cdp':<7} {'t_Rdp':<7}")
    print("-" * 120)
    for r in results:
        if r.get('skipped'):
            print(f"{r['layout']:<22} SKIP: {r['skipped']}")
            continue
        print(f"{r['layout']:<22} {r['n_foods']:<6} {r['n_reachable']:<6} "
              f"{r['count_n']:<4} {r['count_moves']:<4} {r['count_risk_sum']:<7} "
              f"{r['risk_n']:<4} {r['risk_moves']:<4} {r['risk_risk_sum']:<7} "
              f"{r['common']:<3} {r['only_count']:<6} {r['only_risk']:<6} "
              f"{r['t_risk']:<7} {r['t_count_dp']:<7} {r['t_risk_dp']:<7}")

    # Detailed output per tested layout (if single or --render)
    for r in results:
        if r.get('skipped'):
            continue
        if args.layout or args.render:
            print(f"\n{'=' * 70}\n{r['layout']}\n{'=' * 70}")
            print("Top-5 highest-risk foods (cell, score, components):")
            for f, s, comp in r['top5_risk']:
                print(f"  {f}  risk={s}  de={comp['de']} ap={comp['ap']} "
                      f"dh={comp['dh']} vor_m={comp['vor_margin']} iso={comp['iso']}")
            print(f"\nCount-only picks ({r['only_count']}): {r['only_count_cells']}")
            print(f"Risk-only picks ({r['only_risk']}): {r['only_risk_cells']}")
            print(f"\nASCII map (legend: %=wall $=capsule |=home :=midline "
                  f".=food C=count-only R=risk-only B=both)")
            print(r['render'])


if __name__ == '__main__':
    main()

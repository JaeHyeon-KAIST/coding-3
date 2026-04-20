#!/usr/bin/env python3
"""Aggregate HTH CSV → per-opponent per-layout WR tables + Wilson CI."""
import argparse
import csv
import math
from collections import defaultdict


def wilson(w, n):
    if n == 0:
        return 0, 0, 1
    p = w / n
    z = 1.96
    denom = 1 + z * z / n
    c = p + z * z / (2 * n)
    s = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return p, (c - s) / denom, (c + s) / denom


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csvs', nargs='+', help='one or more HTH CSVs')
    ap.add_argument('--per-color', action='store_true')
    args = ap.parse_args()

    all_rows = []
    for path in args.csvs:
        with open(path) as f:
            all_rows.extend(list(csv.DictReader(f)))

    # Per (agent, opp, layout)
    agg = defaultdict(lambda: {'w': 0, 'n': 0, 'c': 0, 'score_sum': 0})
    for r in all_rows:
        agent = r['agent_a']
        opp = r['opp']
        layout = r['layout']
        color = r['color']
        wincol = 'red_win' if color == 'red' else 'blue_win'
        win = int(r[wincol])
        key = (agent, opp, layout)
        agg[key]['w'] += win
        agg[key]['n'] += 1
        agg[key]['c'] += int(r['crashed'])
        try:
            s = float(r.get('score', 0) or 0)
            if color == 'blue':
                s = -s
            agg[key]['score_sum'] += s
        except Exception:
            pass
        if args.per_color:
            key2 = (agent, opp, layout, color)
            agg[key2]['w'] += win
            agg[key2]['n'] += 1

    # Print per-agent table
    agents = sorted({k[0] for k in agg.keys()})
    for agent in agents:
        print(f"\n=== {agent} ===")
        print(f"{'opponent':<30} {'layout':<18} {'w/n':<10} {'WR':>7} {'Wilson 95%':<22} {'avg_score':>9} {'crash':>6}")
        print('-' * 110)
        keys = sorted(k for k in agg.keys() if len(k) == 3 and k[0] == agent)
        for k in keys:
            s = agg[k]
            p, lo, hi = wilson(s['w'], s['n'])
            avg = s['score_sum'] / max(1, s['n'])
            print(f"{k[1]:<30} {k[2]:<18} {s['w']}/{s['n']:<7}  {p:>7.3f}  [{lo:.3f}, {hi:.3f}]   {avg:>+9.2f} {s['c']:>6}")

        if args.per_color:
            print(f"\n-- per-color --")
            keys4 = sorted(k for k in agg.keys() if len(k) == 4 and k[0] == agent)
            for k in keys4:
                s = agg[k]
                p, lo, hi = wilson(s['w'], s['n'])
                print(f"  {k[1]:<28} {k[2]:<16} {k[3]:<6} {s['w']}/{s['n']:<7}  {p:>7.3f}  [{lo:.3f}, {hi:.3f}]")

        # Overall
        total_w = sum(agg[k]['w'] for k in agg if len(k) == 3 and k[0] == agent)
        total_n = sum(agg[k]['n'] for k in agg if len(k) == 3 and k[0] == agent)
        p, lo, hi = wilson(total_w, total_n)
        print(f"\n  OVERALL: {total_w}/{total_n} = {p:.3f}  [{lo:.3f}, {hi:.3f}]")


if __name__ == '__main__':
    main()

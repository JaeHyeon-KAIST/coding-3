#!/usr/bin/env python3
"""Solo vs Duo feasibility analysis.

For each RANDOM<1..30>, check:
  1. SOLO: Can A alone (B stays defense) deposit ≥ 28 food via cap-1 + cap-2 chain?
  2. DUO (A-both): A eats both caps (A detours cap1→cap2), B pure food.
  3. DUO (A-B-split): A eats cap1, B eats cap2 at right timing. Both harvest food.
  4. DUO (regional): A handles cap1 + local food, B handles cap2 + local food.

Report: SOLO_WIN / DUO_WIN_{mode} / NOT_FEASIBLE for each map.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from collections import deque

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
os.chdir(str(MINICONTEST))
sys.path.insert(0, str(MINICONTEST))

import mazeGenerator as mg
import random as _random


WIN_THRESHOLD = 28  # food deposits needed to likely win
SCARED_BUDGET = 75  # maximum scared window (cap-2 eaten at tick 35 post-cap-1)
CAP2_DEADLINE = 35  # cap-2 must be eaten by this tick post-cap1


def parse_layout(maze_str):
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    walls = [[False]*cols for _ in range(rows)]
    food = []
    capsules = []
    spawns = {}
    for r, line in enumerate(lines):
        y = rows - 1 - r
        for c, ch in enumerate(line):
            if ch == '%':
                walls[r][c] = True
            elif ch == '.':
                food.append((c, y))
            elif ch == 'o':
                capsules.append((c, y))
            elif ch in '1234':
                spawns[ch] = (c, y)
    return walls, food, capsules, spawns, (cols, rows)


def bfs_distances(walls, start, W, H):
    dists = {start: 0}
    q = deque([start])
    while q:
        (x, y) = q.popleft()
        d = dists[(x, y)]
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx, ny = x+dx, y+dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            r = H - 1 - ny
            if walls[r][nx]:
                continue
            if (nx, ny) not in dists:
                dists[(nx, ny)] = d + 1
                q.append((nx, ny))
    return dists


def greedy_harvest(start, end, targets, budget, pairwise):
    """Greedy orienteering: start → as many targets as possible → end, within budget."""
    current = start
    collected = set()
    used = 0
    while True:
        best = None
        best_d = None
        for t in targets:
            if t in collected:
                continue
            d_ct = pairwise.get((current, t))
            d_te = pairwise.get((t, end))
            if d_ct is None or d_te is None:
                continue
            if used + d_ct + d_te > budget:
                continue
            if best_d is None or d_ct < best_d:
                best_d = d_ct
                best = t
        if best is None:
            break
        collected.add(best)
        used += best_d
        current = best
    # Final leg
    d_final = pairwise.get((current, end), 0)
    used += d_final
    return collected, used


def build_pairwise(walls, cells_of_interest, W, H):
    """Pairwise BFS distances between all cells of interest."""
    pairwise = {}
    for c in cells_of_interest:
        d = bfs_distances(walls, c, W, H)
        for other in cells_of_interest:
            if other in d:
                pairwise[(c, other)] = d[other]
    return pairwise


def analyze_map(seed):
    _random.seed(seed)
    maze_str = mg.generateMaze(seed)
    walls, food, capsules, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    blue_side_food = [f for f in food if f[0] >= mid_col]
    blue_side_caps = [c for c in capsules if c[0] >= mid_col]

    if len(blue_side_caps) < 2:
        return None

    a_spawn = spawns['1']
    b_spawn = spawns['3']

    dists_a = bfs_distances(walls, a_spawn, W, H)
    dists_b = bfs_distances(walls, b_spawn, W, H)

    # Best midline entry (blue side col adjacent to midline)
    blue_entry_cells = []
    for r in range(H):
        for c in range(mid_col, mid_col+2):
            if c < W and not walls[r][c]:
                y = H - 1 - r
                blue_entry_cells.append((c, y))

    a_entry = min([e for e in blue_entry_cells if e in dists_a],
                   key=lambda e: dists_a[e], default=None)
    b_entry_candidates = [e for e in blue_entry_cells if e in dists_b]
    # B entry should be distinct from A for spatial split
    b_entry = sorted(b_entry_candidates, key=lambda e: -abs(e[1] - a_entry[1]))[0] \
              if len(b_entry_candidates) > 1 else a_entry

    if a_entry is None:
        return {'seed': seed, 'verdict': 'NOT_FEASIBLE', 'reason': 'no_entry'}

    # Cap assignment: sort by distance from A
    cap_dist_a = sorted(blue_side_caps, key=lambda c: dists_a.get(c, 9999))
    cap1, cap2 = cap_dist_a[0], cap_dist_a[1]  # A naturally prefers cap1

    # Cells of interest for pairwise BFS
    cells_of_interest = list(set([a_entry, b_entry, cap1, cap2] + blue_side_food))
    pairwise = build_pairwise(walls, cells_of_interest, W, H)

    d_entry_cap1 = pairwise.get((a_entry, cap1), 9999)
    d_cap1_cap2 = pairwise.get((cap1, cap2), 9999)

    # Discard if cap1 unreachable
    if d_entry_cap1 > 40:
        return {'seed': seed, 'verdict': 'NOT_FEASIBLE', 'reason': 'cap1_far'}

    results = {}

    # --- Option SOLO: A does both caps, B stays home (defense) ---
    # A: a_entry → cap1 → [food ≤ 35, end at cap2] → cap2 → [food ≤ 40] → home
    # Segment 1: cap1 → food → cap2 within 35
    seg1_food, seg1_used = greedy_harvest(cap1, cap2, blue_side_food, 35, pairwise)
    # Segment 2: cap2 → food → home within 40
    remaining_food = [f for f in blue_side_food if f not in seg1_food]
    seg2_food, seg2_used = greedy_harvest(cap2, a_entry, remaining_food, 40, pairwise)
    solo_total = len(seg1_food) + len(seg2_food)
    results['SOLO'] = {
        'total': solo_total,
        'seg1': len(seg1_food),
        'seg2': len(seg2_food),
        'b_food': 0,
    }

    # --- Option DUO_A_BOTH: A both caps + detour, B pure food ---
    # Same as SOLO for A, B harvests blue side food in parallel
    available_for_b = [f for f in blue_side_food
                       if f not in seg1_food and f not in seg2_food]
    b_food_both, _ = greedy_harvest(b_entry, b_entry, available_for_b, SCARED_BUDGET, pairwise)
    duo_both_total = solo_total + len(b_food_both)
    results['DUO_A_BOTH'] = {
        'total': duo_both_total,
        'seg1': len(seg1_food),
        'seg2': len(seg2_food),
        'b_food': len(b_food_both),
    }

    # --- Option DUO_SPLIT: A handles cap1, B handles cap2 ---
    # A: a_entry → cap1 → free food 75 tick → home (no cap2 detour constraint!)
    a_split_food, _ = greedy_harvest(cap1, a_entry, blue_side_food, SCARED_BUDGET - d_entry_cap1, pairwise)
    # B: b_entry → [food] → cap2 (within 35 post-cap1) → [food] → home
    # B budget: 75 - 0 (B enters at tick 0, needs cap2 by tick 35)
    # Segment B.1: b_entry → food → cap2 within 35
    b_seg1_food, _ = greedy_harvest(b_entry, cap2, blue_side_food,
                                     35, pairwise)
    # Filter out what A took
    avail_split = [f for f in blue_side_food if f not in a_split_food and f not in b_seg1_food]
    # Segment B.2: cap2 → food → home within 40
    b_seg2_food, _ = greedy_harvest(cap2, b_entry, avail_split, 40, pairwise)
    duo_split_total = len(a_split_food) + len(b_seg1_food) + len(b_seg2_food)
    results['DUO_SPLIT'] = {
        'total': duo_split_total,
        'a_food': len(a_split_food),
        'b_seg1': len(b_seg1_food),
        'b_seg2': len(b_seg2_food),
    }

    # --- Best duo option ---
    best_duo = max(['DUO_A_BOTH', 'DUO_SPLIT'], key=lambda k: results[k]['total'])
    best_duo_total = results[best_duo]['total']

    # --- Verdict ---
    if solo_total >= WIN_THRESHOLD:
        verdict = 'SOLO_WIN'
    elif best_duo_total >= WIN_THRESHOLD:
        verdict = f'DUO_WIN_{best_duo}'
    elif best_duo_total >= 20:
        verdict = 'DUO_GOOD'
    elif best_duo_total >= 12:
        verdict = 'DUO_MODEST'
    else:
        verdict = 'NOT_FEASIBLE'

    return {
        'seed': seed,
        'verdict': verdict,
        'solo_total': solo_total,
        'duo_both_total': duo_both_total,
        'duo_split_total': duo_split_total,
        'best_duo': best_duo,
        'd_entry_cap1': d_entry_cap1,
        'd_cap1_cap2': d_cap1_cap2,
        'cap1': cap1,
        'cap2': cap2,
    }


def main():
    print(f"{'seed':>4} | {'verdict':<22} | {'solo':>4} | {'duoBOTH':>7} {'duoSPLIT':>8} | "
          f"d_ent_c1 d_c1_c2 | cap1          cap2")
    print('-' * 110)

    counts = {'SOLO_WIN': 0, 'DUO_WIN_DUO_A_BOTH': 0, 'DUO_WIN_DUO_SPLIT': 0,
              'DUO_GOOD': 0, 'DUO_MODEST': 0, 'NOT_FEASIBLE': 0}
    rows = []

    for seed in range(1, 31):
        try:
            res = analyze_map(seed)
            if res is None or 'total' not in res.get('verdict', ''):
                pass
            if res is None:
                counts['NOT_FEASIBLE'] += 1
                rows.append((seed, 'ERROR', '-', '-', '-', '-', '-', '-', '-'))
                continue
            counts[res['verdict']] = counts.get(res['verdict'], 0) + 1
            rows.append((seed, res['verdict'], res['solo_total'],
                          res['duo_both_total'], res['duo_split_total'],
                          res['d_entry_cap1'], res['d_cap1_cap2'],
                          res['cap1'], res['cap2']))
        except Exception as e:
            counts['NOT_FEASIBLE'] += 1
            rows.append((seed, f'ERROR:{type(e).__name__}', 0, 0, 0, 0, 0, '-', '-'))

    for r in rows:
        seed, verdict, solo, dboth, dsplit, dec1, dc1c2, c1, c2 = r
        print(f"{seed:>4} | {verdict:<22} | {solo:>4} | {dboth:>7} {dsplit:>8} | "
              f"{dec1:>8} {dc1c2:>7} | {str(c1):<13} {str(c2):<13}")

    print('\n=== Summary ===')
    for k, v in counts.items():
        print(f"  {k:<22}: {v:>2}/30")
    print(f"\n  WIN possible (Solo OR Duo): {counts['SOLO_WIN'] + counts['DUO_WIN_DUO_A_BOTH'] + counts['DUO_WIN_DUO_SPLIT']}/30")
    print(f"  SOLO alone suffices        : {counts['SOLO_WIN']}/30")
    print(f"  Need DUO                   : {counts['DUO_WIN_DUO_A_BOTH'] + counts['DUO_WIN_DUO_SPLIT']}/30")


if __name__ == '__main__':
    main()

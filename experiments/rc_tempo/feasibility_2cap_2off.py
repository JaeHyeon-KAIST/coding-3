#!/usr/bin/env python3
"""Feasibility analysis: can 2-offense 2-capsule chain win in scared window?

For each RANDOM<1..30>:
  1. Parse map, extract walls/food/capsules/spawns
  2. BFS distance matrix on opp-side cells
  3. Greedy 2-agent orienteering solver within 75-tick scared budget
  4. Report: (cap1_entry, cap2_entry, est_food_harvested_by_both, verdict)

Criteria for "win-feasible":
  - 2 agents combined can harvest and deposit ≥ 28 food within 75 ticks
  - Cap-1 → deep food → cap-2 → more food → home BEFORE scared expires
  - Budget: ~75 ticks (40 + 35 overlap, timed for max extension)
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from collections import deque
from heapq import heappush, heappop

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
os.chdir(str(MINICONTEST))
sys.path.insert(0, str(MINICONTEST))

import mazeGenerator as mg
import random as _random


def parse_layout(maze_str):
    """Parse layout string into (walls, food, capsules, spawns, dims)."""
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    walls = [[False]*cols for _ in range(rows)]
    food = []
    capsules = []
    spawns = {}
    for r, line in enumerate(lines):
        y = rows - 1 - r  # flip y so (0,0) = bottom-left like Berkeley convention
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
    """BFS distances from start to all reachable cells. start/cells in (x, y) bottom-left."""
    dists = {}
    q = deque([(start, 0)])
    dists[start] = 0
    while q:
        (x, y), d = q.popleft()
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx, ny = x+dx, y+dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            r = H - 1 - ny  # flip back to row index
            if walls[r][nx]:
                continue
            if (nx, ny) not in dists:
                dists[(nx, ny)] = d + 1
                q.append(((nx, ny), d+1))
    return dists


def greedy_orienteering_1agent(dist_matrix, start, targets, budget, must_return_to):
    """Greedy nearest-food orienteering from start, collect as many targets as possible,
    must return to must_return_to within budget total steps.

    dist_matrix: dict (pos1, pos2) -> dist, approximated by symmetric BFS dist.
    Returns: (harvested_count, path, used_budget)
    """
    current = start
    collected = set()
    remaining_budget = budget
    path = [start]

    while True:
        # Find nearest uncollected target that still allows return to must_return_to
        best_t = None
        best_d = None
        for t in targets:
            if t in collected:
                continue
            d_curr_to_t = dist_matrix.get((current, t))
            if d_curr_to_t is None:
                continue
            d_t_to_home = dist_matrix.get((t, must_return_to))
            if d_t_to_home is None:
                continue
            if d_curr_to_t + d_t_to_home > remaining_budget:
                continue
            if best_d is None or d_curr_to_t < best_d:
                best_d = d_curr_to_t
                best_t = t

        if best_t is None:
            break
        collected.add(best_t)
        remaining_budget -= best_d
        path.append(best_t)
        current = best_t

    # Final return
    d_home = dist_matrix.get((current, must_return_to), 0)
    used = budget - remaining_budget + d_home
    path.append(must_return_to)
    return len(collected), path, used


def analyze_map(seed):
    _random.seed(seed)
    maze_str = mg.generateMaze(seed)
    walls, food, capsules, spawns, (W, H) = parse_layout(maze_str)

    mid_col = W // 2

    # Red's offensive = blue side (x >= mid_col)
    blue_side_food = [f for f in food if f[0] >= mid_col]
    blue_side_caps = [c for c in capsules if c[0] >= mid_col]

    # Red A = agent '1' (offensive, lower index on red)
    # Actually looking at layout:  1=red index 0 OFFENSE,  3=red index 2 DEFENSE
    # Red starts at (1, 2) and (1, 1) — bottom left area
    a_spawn = spawns.get('1', (1, 2))
    b_spawn = spawns.get('3', (1, 1))

    # Midline entry points = cells on blue side col = mid_col adjacent to red side
    # Both agents need to cross into blue territory
    # Find reachable midline cells (blue side, just past midline)
    blue_entry_cells = []
    for r in range(H):
        for c in range(mid_col, mid_col+2):
            if c < W and not walls[r][c]:
                y = H - 1 - r
                blue_entry_cells.append((c, y))

    # Compute BFS from a_spawn to everything
    dists_a = bfs_distances(walls, a_spawn, W, H)
    dists_b = bfs_distances(walls, b_spawn, W, H)

    # Find best midline entry (closest to A)
    a_entry = min([e for e in blue_entry_cells if e in dists_a],
                   key=lambda e: dists_a[e], default=None)
    b_entry = min([e for e in blue_entry_cells if e in dists_b and e != a_entry],
                   key=lambda e: dists_b[e], default=a_entry)

    if a_entry is None:
        return None  # map has no reachable blue side from A

    # Sort capsules by distance from A
    cap_dist_a = [(c, dists_a.get(c, 9999)) for c in blue_side_caps]
    cap_dist_a.sort(key=lambda x: x[1])

    if len(cap_dist_a) < 2:
        return None

    cap1 = cap_dist_a[0][0]  # closer cap = cap-1 (A eats first)
    cap2 = cap_dist_a[1][0]
    d_a_to_cap1 = cap_dist_a[0][1]
    d_a_to_cap2 = cap_dist_a[1][1]

    # Pairwise distances on blue side
    blue_cells_of_interest = [cap1, cap2] + blue_side_food + [a_entry, b_entry]
    blue_cells_of_interest = list(set(blue_cells_of_interest))

    # BFS from each cell to compute pairwise
    pairwise = {}
    for c in blue_cells_of_interest:
        d = bfs_distances(walls, c, W, H)
        for other in blue_cells_of_interest:
            if other in d:
                pairwise[(c, other)] = d[other]

    # Cap1 -> cap2 distance
    d_cap1_cap2 = pairwise.get((cap1, cap2), 9999)

    # --- Strategy simulation ---
    # Scared window timing:
    #   T0: A eats cap1 at tick T0
    #   Scared ends: T0 + 40 (normal)
    #   A/B eats cap2 at tick T0 + 35 (optimal timing for max extension)
    #   Scared renewed to T0 + 35 + 40 = T0 + 75
    #   Total effective scared: T0 to T0 + 75 → 75 ticks

    # BUT: both agents need to be HOME by T0 + 75 (before scared expires)
    # Because after scared, defender wakes → ghosts can eat our pacman → we lose carried food

    # Budget allocation:
    # A: cap1 eat at T0 → food collection → ... → back home before T0 + 75
    # B: enters around T0 (maybe a bit later to coordinate cap2 timing)
    #   B's role: eat some food + time cap2 eat at T0+35
    #   Or: A eats cap2 while B does pure food

    # Simplification: assume A handles both cap-1 and cap-2 sequentially
    # A: a_entry → cap1 (d_a_entry_cap1) → food greedy → cap2 (within 35 of cap1) → food → home
    # B: b_entry → food greedy → home

    # We need A to eat cap2 by tick 35 post-cap1
    # So A path: cap1 → food_detour → cap2, with cap1_to_cap2 path length ≤ 35
    # Food collected by A during detour = food on path between cap1 and cap2

    # Rough estimate:
    # A budget after cap1: 75 ticks (until scared end)
    # A must: reach cap2 by tick 35 (35 tick detour)
    # Then continue food collection + return: 40 more ticks

    # --- Run greedy orienteering for A and B ---
    d_entry_cap1 = pairwise.get((a_entry, cap1), 9999)

    if d_entry_cap1 > 30:  # Cap1 too far from entry → can't trigger in time
        return {'seed': seed, 'verdict': 'CAP1_TOO_FAR', 'd_entry_cap1': d_entry_cap1}

    # A segment 1: cap1 → cap2 with food detour (35-tick budget, must end at cap2)
    # We'll approximate by picking food near cap1-cap2 path
    # Budget for A after cap1 = 75
    # Constraint: must be at cap2 by tick 35 (post-cap1)

    # Simplification: check if greedy 35-tick food detour between cap1 and cap2 possible
    # Then remaining 40 ticks for more food + home return

    # Segment A.1: cap1 → [food detour ≤ 35] → cap2
    # Find food with (d(cap1, f) + d(f, cap2)) minimal, insert greedily
    candidate_food = []
    for f in blue_side_food:
        d1 = pairwise.get((cap1, f), 9999)
        d2 = pairwise.get((f, cap2), 9999)
        if d1 + d2 - d_cap1_cap2 <= 35 - d_cap1_cap2:
            # Detour is affordable
            candidate_food.append((f, d1 + d2))
    candidate_food.sort(key=lambda x: x[1])

    a_segment1_food = 0
    budget1 = 35 - d_cap1_cap2  # slack
    # Count how many can fit via greedy insertion
    current_in_seg1 = cap1
    used1 = 0
    collected1 = set()
    while True:
        best_f = None
        best_cost = None
        for f, _ in candidate_food:
            if f in collected1:
                continue
            d_curr_f = pairwise.get((current_in_seg1, f), 9999)
            d_f_cap2 = pairwise.get((f, cap2), 9999)
            if used1 + d_curr_f + d_f_cap2 > 35:
                continue
            if best_cost is None or d_curr_f < best_cost:
                best_cost = d_curr_f
                best_f = f
        if best_f is None:
            break
        collected1.add(best_f)
        used1 += best_cost
        current_in_seg1 = best_f
    a_segment1_food = len(collected1)
    # Final leg from current to cap2 uses remaining
    d_final_cap2 = pairwise.get((current_in_seg1, cap2), 9999)
    used1 += d_final_cap2

    # Segment A.2: cap2 → [food ≤ 40] → home (back to a_entry)
    remaining_budget_a = 75 - 35
    # Greedy from cap2
    current_in_seg2 = cap2
    collected2_a = set()
    used2 = 0
    available_food = [f for f in blue_side_food if f not in collected1]
    while True:
        best_f = None
        best_d = None
        for f in available_food:
            if f in collected2_a:
                continue
            d_curr_f = pairwise.get((current_in_seg2, f), 9999)
            d_f_home = pairwise.get((f, a_entry), 9999)
            if used2 + d_curr_f + d_f_home > remaining_budget_a:
                continue
            if best_d is None or d_curr_f < best_d:
                best_d = d_curr_f
                best_f = f
        if best_f is None:
            break
        collected2_a.add(best_f)
        used2 += best_d
        current_in_seg2 = best_f
    a_segment2_food = len(collected2_a)

    # Segment B: entry → food greedy → home (budget 75, during scared window)
    # B enters at b_entry, budget = 75
    # But B doesn't need to eat capsules — just food harvest
    available_food_b = [f for f in blue_side_food
                        if f not in collected1 and f not in collected2_a]
    harvested_b, _, _ = greedy_orienteering_1agent(
        pairwise, b_entry, available_food_b, 75, b_entry)

    total_food = a_segment1_food + a_segment2_food + harvested_b

    # Verdict
    if total_food >= 28:
        verdict = 'WIN_FEASIBLE'
    elif total_food >= 20:
        verdict = 'GOOD_HARVEST'
    elif total_food >= 12:
        verdict = 'MODEST'
    else:
        verdict = 'WEAK'

    return {
        'seed': seed,
        'verdict': verdict,
        'total_food': total_food,
        'a_seg1_food': a_segment1_food,  # between cap1 and cap2
        'a_seg2_food': a_segment2_food,  # after cap2
        'b_food': harvested_b,
        'd_entry_cap1': d_entry_cap1,
        'd_cap1_cap2': d_cap1_cap2,
        'cap1_pos': cap1,
        'cap2_pos': cap2,
        'a_entry': a_entry,
        'food_on_blue_side': len(blue_side_food),
    }


def main():
    print(f"{'seed':>4} | {'verdict':<15} | {'food':>4} | {'a1':>3} {'a2':>3} {'b':>3} | d_ent_c1 d_c1_c2 | cap1_pos     cap2_pos")
    print('-' * 100)

    verdicts = {'WIN_FEASIBLE': 0, 'GOOD_HARVEST': 0, 'MODEST': 0, 'WEAK': 0,
                 'CAP1_TOO_FAR': 0, 'ERROR': 0}

    for seed in range(1, 31):
        try:
            res = analyze_map(seed)
            if res is None:
                verdicts['ERROR'] += 1
                print(f"{seed:>4} | ERROR")
                continue
            verdicts[res['verdict']] += 1
            if res['verdict'] == 'CAP1_TOO_FAR':
                print(f"{seed:>4} | CAP1_TOO_FAR  | d_ent_c1={res['d_entry_cap1']}")
                continue
            print(f"{seed:>4} | {res['verdict']:<15} | {res['total_food']:>4} | "
                   f"{res['a_seg1_food']:>3} {res['a_seg2_food']:>3} {res['b_food']:>3} | "
                   f"{res['d_entry_cap1']:>8} {res['d_cap1_cap2']:>7} | "
                   f"{str(res['cap1_pos']):>12} {str(res['cap2_pos']):>12}")
        except Exception as e:
            verdicts['ERROR'] += 1
            print(f"{seed:>4} | ERROR: {e}")

    print('\n=== Summary ===')
    for k, v in verdicts.items():
        print(f"  {k:<18}: {v:>2}/30")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""DP orienteering timing test per layout.

Loads each capture layout, extracts capsule/food/walls, computes all-pairs
maze distances, then runs the DP orienteering from each Red-side perspective's
capsule target.

Usage:
    .venv/bin/python experiments/test_orienteering.py
"""
import glob
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MINICONTEST = os.path.join(HERE, '..', 'minicontest')
sys.path.insert(0, MINICONTEST)

import layout
import distanceCalculator


def find_home_cells(walls, midline_x, my_side_is_red):
    """중앙선 바로 우리 쪽에 있는 cells (= home entrance)."""
    cells = []
    width = walls.width
    height = walls.height
    target_x = midline_x - 1 if my_side_is_red else midline_x
    for y in range(height):
        if not walls[target_x][y]:
            cells.append((target_x, y))
    return cells


def reachable_filter(distancer, capsule, foods, home_cells, budget):
    """capsule → f → (nearest home) 가 예산 내인 food만 남김."""
    out = []
    for f in foods:
        cost_to = distancer.getDistance(capsule, f)
        cost_back = min(distancer.getDistance(f, h) for h in home_cells)
        if cost_to + cost_back <= budget:
            out.append(f)
    return out


def orienteering_dp(distancer, capsule, foods, home_cells, budget=40):
    """
    Bitmask DP. State = (last_visited_food_idx_or_-1, eaten_mask).
    dp[state] = min distance from capsule to this state.
    Returns (best_food_count, best_route, total_dist).
    """
    n = len(foods)
    if n == 0:
        nh = min(home_cells, key=lambda h: distancer.getDistance(capsule, h))
        return 0, [capsule, nh], distancer.getDistance(capsule, nh)

    # cache distances
    # dist_cap_to_food[i]
    # dist_food_to_food[i][j]
    # dist_food_to_home[i] = min over home cells
    d_cap = [distancer.getDistance(capsule, foods[i]) for i in range(n)]
    d_ff = [[distancer.getDistance(foods[i], foods[j]) for j in range(n)] for i in range(n)]
    d_fh = [min(distancer.getDistance(foods[i], h) for h in home_cells) for i in range(n)]

    # dp: {(pos, mask): min_dist}. pos = -1 means at capsule.
    INF = 10 ** 9
    dp = {(-1, 0): 0}

    best_count = 0
    best_state = (-1, 0)
    best_total = distancer.getDistance(capsule, min(home_cells,
                                                     key=lambda h: distancer.getDistance(capsule, h)))

    # BFS / forward DP via frontier queue; order doesn't strictly matter if we use min-update.
    from collections import deque
    frontier = deque()
    frontier.append((-1, 0))
    while frontier:
        pos, mask = frontier.popleft()
        cur_dist = dp.get((pos, mask), INF)

        # evaluate "end here" option
        if pos == -1:
            to_home = distancer.getDistance(capsule, min(home_cells,
                                                         key=lambda h: distancer.getDistance(capsule, h)))
        else:
            to_home = d_fh[pos]
        total_if_end = cur_dist + to_home
        food_count = bin(mask).count('1')
        if total_if_end <= budget:
            if food_count > best_count or (food_count == best_count and total_if_end < best_total):
                best_count = food_count
                best_state = (pos, mask)
                best_total = total_if_end

        # expand
        for i in range(n):
            if mask & (1 << i):
                continue
            new_mask = mask | (1 << i)
            if pos == -1:
                step = d_cap[i]
            else:
                step = d_ff[pos][i]
            new_dist = cur_dist + step
            # pruning: must be able to reach home afterwards
            if new_dist + d_fh[i] > budget:
                continue
            key = (i, new_mask)
            if new_dist < dp.get(key, INF):
                dp[key] = new_dist
                frontier.append(key)

    # reconstruct route (not strictly needed for timing but useful)
    # For this test we skip reconstruction, just report counts.
    return best_count, None, best_total


def analyze_layout(layout_file):
    lay = layout.getLayout(layout_file, back=0)
    if lay is None:
        # layout.getLayout expects name w/o path and searches ./layouts/
        fullpath = os.path.join(MINICONTEST, 'layouts', layout_file)
        if not os.path.exists(fullpath):
            return None
        with open(fullpath) as f:
            lines = [line.rstrip() for line in f]
        # Parse manually
        lay = layout.Layout(lines)

    walls = lay.walls
    food_grid = lay.food
    capsules = lay.capsules   # list of (x, y)
    width = walls.width
    height = walls.height
    midline_x = width // 2

    # Red team perspective: foods to eat = Blue side food (x >= midline_x)
    # Capsules Red can eat = capsules on Blue side
    red_target_foods = [(x, y) for x in range(midline_x, width) for y in range(height) if food_grid[x][y]]
    red_target_capsules = [c for c in capsules if c[0] >= midline_x]

    # Red home cells (= midline_x - 1 column, non-wall)
    red_home = [(midline_x - 1, y) for y in range(height) if not walls[midline_x - 1][y]]

    if len(red_target_capsules) != 1:
        return {
            'layout': layout_file,
            'n_foods_total': len(red_target_foods),
            'n_capsules': len(red_target_capsules),
            'skipped': f"V0.1 only supports exactly 1 capsule (this has {len(red_target_capsules)})",
        }

    # Build distancer
    t0 = time.perf_counter()
    d = distanceCalculator.Distancer(lay)
    d.getMazeDistances()
    t_dist = time.perf_counter() - t0

    # Use first capsule
    capsule = red_target_capsules[0]

    # Reachable filter
    t0 = time.perf_counter()
    reachable = reachable_filter(d, capsule, red_target_foods, red_home, budget=40)
    t_filter = time.perf_counter() - t0

    # DP
    t0 = time.perf_counter()
    count, _, total = orienteering_dp(d, capsule, reachable, red_home, budget=40)
    t_dp = time.perf_counter() - t0

    return {
        'layout': layout_file,
        'map_size': f"{width}x{height}",
        'n_foods_total': len(red_target_foods),
        'n_reachable': len(reachable),
        'n_capsules': len(red_target_capsules),
        'n_home_cells': len(red_home),
        'best_food_count': count,
        'best_total_moves': total,
        'budget': 40,
        't_distancer_sec': round(t_dist, 3),
        't_filter_sec': round(t_filter, 4),
        't_dp_sec': round(t_dp, 3),
        't_total_init_sec': round(t_dist + t_filter + t_dp, 3),
    }


def main():
    layouts_dir = os.path.join(MINICONTEST, 'layouts')
    all_layouts = sorted(os.path.basename(p) for p in glob.glob(os.path.join(layouts_dir, '*.lay')))

    print(f"Testing {len(all_layouts)} layouts...", flush=True)
    print("=" * 100, flush=True)
    print(f"{'Layout':<24} {'Size':<8} {'Foods':<6} {'Reach':<6} {'Caps':<5} "
          f"{'Homes':<6} {'Best':<5} {'Moves':<6} "
          f"{'t_dist':<8} {'t_dp':<8} {'t_init':<8}")
    print("-" * 100)

    for lay_name in all_layouts:
        print(f"[start] {lay_name}", flush=True)
        try:
            r = analyze_layout(lay_name)
        except Exception as e:
            print(f"{lay_name}: ERROR {e}")
            continue
        if r is None:
            print(f"{lay_name}: layout not loadable")
            continue
        if r.get('skipped'):
            print(f"{lay_name:<24} {r.get('map_size','?'):<8} "
                  f"{r.get('n_foods_total','?'):<6} -      {r.get('n_capsules',0):<5} "
                  f"-      -     -      "
                  f"-        -        -        ({r['skipped']})")
            continue
        print(f"{r['layout']:<24} {r['map_size']:<8} {r['n_foods_total']:<6} "
              f"{r['n_reachable']:<6} {r['n_capsules']:<5} {r['n_home_cells']:<6} "
              f"{r['best_food_count']:<5} {r['best_total_moves']:<6} "
              f"{r['t_distancer_sec']:<8} {r['t_dp_sec']:<8} {r['t_total_init_sec']:<8}")


if __name__ == '__main__':
    main()

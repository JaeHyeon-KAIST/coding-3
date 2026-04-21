#!/usr/bin/env python3
"""OPTIMAL (offline, no time limit) feasibility analysis for RANDOM<1..30>.

Scenarios tested:
  1. SOLO: A alone eats cap1 + cap2, B stays home. Can A deposit ≥ 28 food?
  2. DUO: both agents offensive. Can they together deposit ≥ 28 food?
     - DUO_A_BOTH: A eats both caps (detour), B pure food harvester
     - DUO_SPLIT:  A eats cap1, B eats cap2 (within 35 ticks after cap1)
     - DUO_A_CAP1_ONLY: A eats cap1, B pure food (no second capsule)
     - etc.

For each, use wide beam search (beam=3000) + simulated annealing refinement
to find near-optimal food harvest.
"""
from __future__ import annotations
import os
import sys
import random
from pathlib import Path
from collections import deque
from heapq import heappush, heappop

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
os.chdir(str(MINICONTEST))
sys.path.insert(0, str(MINICONTEST))

import mazeGenerator as mg

WIN_THRESHOLD = 28
SCARED_MAX_EXTENSION = 79   # 39 (pre-reset opp moves) + 40 (post-reset) = 79 total opp moves of scared
CAP2_DEADLINE = 39          # cap-2 must be eaten by A's 39th move post-cap-1 (opp still scared w/ timer=1)
BEAM_WIDTH = 3000
SA_ITERATIONS = 5000


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


def build_pairwise(walls, cells, W, H):
    pw = {}
    for c in cells:
        d = bfs_distances(walls, c, W, H)
        for o in cells:
            if o in d:
                pw[(c, o)] = d[o]
    return pw


def beam_search_orienteering(start, end, food_list, budget, pairwise, beam=BEAM_WIDTH):
    """Beam search: path start → [subset of food] → end within budget.
    Returns list of (collected_frozenset, cost) sorted by (count desc, cost asc).
    """
    # state: (current_pos, time_used, frozenset of visited food)
    # initial state
    initial = (start, 0, frozenset())
    states = [initial]
    visited_states = {(start, frozenset()): 0}  # dedup by (pos, visited) keep min time
    all_found = []

    depth = 0
    while states and depth < 40:
        depth += 1
        next_states = []
        for (pos, time_used, visited) in states:
            # Try each food not yet visited
            extended = False
            for f in food_list:
                if f in visited:
                    continue
                d_pf = pairwise.get((pos, f))
                d_fe = pairwise.get((f, end))
                if d_pf is None or d_fe is None:
                    continue
                new_time = time_used + d_pf
                if new_time + d_fe > budget:
                    continue
                new_visited = visited | {f}
                key = (f, new_visited)
                if key in visited_states and visited_states[key] <= new_time:
                    continue
                visited_states[key] = new_time
                next_states.append((f, new_time, new_visited))
                extended = True
            # terminal: can also end here
            d_pe = pairwise.get((pos, end))
            if d_pe is not None and time_used + d_pe <= budget:
                all_found.append((visited, time_used + d_pe))
            if not extended:
                pass

        # Keep top `beam` by (food count desc, time_used asc)
        next_states.sort(key=lambda s: (-len(s[2]), s[1]))
        states = next_states[:beam]

    # Final: all_found contains candidate terminals
    # Sort by count desc
    all_found.sort(key=lambda s: (-len(s[0]), s[1]))
    # Dedup by visited_set
    seen = set()
    result = []
    for v, t in all_found:
        if v in seen:
            continue
        seen.add(v)
        result.append((v, t))
    return result


def max_food_solo_two_caps(pairwise, a_entry, cap1, cap2, food_list):
    """SOLO: a_entry → cap1 → [food] → cap2 → [food] → a_entry.
    Returns: max food count, seg1_food_set, seg2_food_set, total_time.
    """
    d_entry_cap1 = pairwise.get((a_entry, cap1), 9999)
    if d_entry_cap1 > 50:  # way too far
        return 0, frozenset(), frozenset(), 9999

    # Segment 1: cap1 → [food] → cap2 within CAP2_DEADLINE
    seg1_options = beam_search_orienteering(
        cap1, cap2, food_list, CAP2_DEADLINE, pairwise, beam=BEAM_WIDTH)

    # Segment 2 budget: remaining scared window (75 - (time up to cap2))
    # But we want max scared extension, so assume cap2 eaten at tick exactly CAP2_DEADLINE
    # Then budget for seg2 = SCARED_MAX_EXTENSION - CAP2_DEADLINE = 40
    seg2_budget = SCARED_MAX_EXTENSION - CAP2_DEADLINE  # 40

    best = (0, frozenset(), frozenset(), 9999)
    # Try top 50 seg1 options
    for seg1_food, seg1_cost in seg1_options[:50]:
        remaining_food = [f for f in food_list if f not in seg1_food]
        seg2_options = beam_search_orienteering(
            cap2, a_entry, remaining_food, seg2_budget, pairwise, beam=BEAM_WIDTH)
        if not seg2_options:
            continue
        best_seg2_food, best_seg2_cost = seg2_options[0]
        total = len(seg1_food) + len(best_seg2_food)
        if total > best[0]:
            total_time = d_entry_cap1 + seg1_cost + best_seg2_cost
            best = (total, seg1_food, best_seg2_food, total_time)
    return best


def max_food_duo_A_both_B_free(pairwise, a_entry, b_entry, cap1, cap2, food_list):
    """DUO_A_BOTH: A does solo two-caps, B free-harvests remaining blue food."""
    a_count, a_seg1, a_seg2, _ = max_food_solo_two_caps(
        pairwise, a_entry, cap1, cap2, food_list)

    b_avail = [f for f in food_list if f not in a_seg1 and f not in a_seg2]
    # B must return to b_entry within SCARED_MAX_EXTENSION budget
    b_options = beam_search_orienteering(
        b_entry, b_entry, b_avail, SCARED_MAX_EXTENSION, pairwise, beam=BEAM_WIDTH)
    b_food = b_options[0][0] if b_options else frozenset()
    return a_count + len(b_food), a_seg1, a_seg2, b_food


def max_food_duo_split(pairwise, a_entry, b_entry, cap1, cap2, food_list):
    """DUO_SPLIT: A eats cap1, B eats cap2 within 35 ticks after A's cap1.

    Timing:
      - A enters at tick 0, reaches cap1 at tick d(a_entry, cap1) = T_cap1
      - B enters at tick 0 too, must reach cap2 by tick T_cap1 + 35
      - After cap2: both agents harvest until tick T_cap2 + 40 = scared end
      - Both must be home at scared end

    For A: a_entry → cap1 → [food_A] → a_entry within SCARED_MAX_EXTENSION
      Budget: SCARED_MAX_EXTENSION - (time up to cap1 post-trigger) = SCARED_MAX_EXTENSION (post-cap1 budget)
      Actually: since scared window is 75 ticks starting from cap1 eating:
      A's post-cap1 budget = SCARED_MAX_EXTENSION = 75

    For B: b_entry → [food_B1] → cap2 → [food_B2] → b_entry
      Constraint: time to cap2 ≤ T_cap1 + CAP2_DEADLINE (in game time)
      If B enters at tick 0 and A eats cap1 at tick T_cap1 = d(a_entry, cap1):
      B must eat cap2 by tick T_cap1 + 35 (game time)
      So B's path b_entry → cap2 ≤ T_cap1 + 35 ticks
      After cap2: remaining budget = (T_cap1 + 75) - (T_cap1 + 35) = 40 ticks
    """
    d_a_c1 = pairwise.get((a_entry, cap1), 9999)
    if d_a_c1 > 50:
        return 0, frozenset(), frozenset(), frozenset()

    T_cap1 = d_a_c1  # game tick when A eats cap1
    # A's post-cap1 harvest budget: 75 ticks (scared window)
    a_food_budget = SCARED_MAX_EXTENSION

    # A: cap1 → [food] → a_entry within a_food_budget
    a_options = beam_search_orienteering(
        cap1, a_entry, food_list, a_food_budget, pairwise, beam=BEAM_WIDTH)
    a_food = a_options[0][0] if a_options else frozenset()

    # Food available to B
    b_avail = [f for f in food_list if f not in a_food]

    # B: b_entry → [food_B1] → cap2 with time constraint (path ≤ T_cap1 + 35)
    #    → [food_B2] → b_entry within remaining 40 ticks
    b_seg1_budget = T_cap1 + CAP2_DEADLINE  # tick game
    seg1_options = beam_search_orienteering(
        b_entry, cap2, b_avail, b_seg1_budget, pairwise, beam=BEAM_WIDTH)

    best_b_total = 0
    best_seg1_food = frozenset()
    best_seg2_food = frozenset()
    for seg1_food, seg1_cost in seg1_options[:30]:
        remaining = [f for f in b_avail if f not in seg1_food]
        seg2_budget = 40  # after cap2 eaten, 40 ticks of scared remains
        seg2_options = beam_search_orienteering(
            cap2, b_entry, remaining, seg2_budget, pairwise, beam=BEAM_WIDTH)
        if not seg2_options:
            continue
        seg2_food, _ = seg2_options[0]
        total = len(seg1_food) + len(seg2_food)
        if total > best_b_total:
            best_b_total = total
            best_seg1_food = seg1_food
            best_seg2_food = seg2_food

    return len(a_food) + best_b_total, a_food, best_seg1_food, best_seg2_food


def max_food_duo_swap(pairwise, a_entry, b_entry, cap1, cap2, food_list):
    """DUO_SWAP: B eats cap1, A eats cap2 (reverse assignment)."""
    return max_food_duo_split(pairwise, b_entry, a_entry, cap1, cap2, food_list)


def analyze_map(seed):
    random.seed(seed)
    maze_str = mg.generateMaze(seed)
    walls, food, capsules, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    blue_side_food = [f for f in food if f[0] >= mid_col]
    blue_side_caps = [c for c in capsules if c[0] >= mid_col]

    if len(blue_side_caps) < 2 or '1' not in spawns or '3' not in spawns:
        return {'seed': seed, 'verdict': 'ERROR'}

    a_spawn = spawns['1']
    b_spawn = spawns['3']
    dists_a = bfs_distances(walls, a_spawn, W, H)
    dists_b = bfs_distances(walls, b_spawn, W, H)

    # Best midline entries
    blue_entry_cells = []
    for r in range(H):
        for c in range(mid_col, mid_col+2):
            if c < W and not walls[r][c]:
                y = H - 1 - r
                blue_entry_cells.append((c, y))

    a_entry = min([e for e in blue_entry_cells if e in dists_a],
                   key=lambda e: dists_a[e], default=None)
    b_entries = [e for e in blue_entry_cells if e in dists_b]
    if len(b_entries) > 1:
        b_entry = sorted(b_entries, key=lambda e: -abs(e[1] - a_entry[1]))[0]
    elif b_entries:
        b_entry = b_entries[0]
    else:
        b_entry = a_entry

    if a_entry is None:
        return {'seed': seed, 'verdict': 'NOT_FEASIBLE'}

    # Cap assignment
    cap_dist_a = sorted(blue_side_caps, key=lambda c: dists_a.get(c, 9999))
    cap1, cap2 = cap_dist_a[0], cap_dist_a[1]

    # Pairwise distances
    cells = list(set([a_entry, b_entry, cap1, cap2] + blue_side_food))
    pairwise = build_pairwise(walls, cells, W, H)

    # --- SOLO ---
    solo_count, solo_seg1, solo_seg2, solo_time = max_food_solo_two_caps(
        pairwise, a_entry, cap1, cap2, blue_side_food)

    # --- DUO_A_BOTH ---
    duo_both, ab_seg1, ab_seg2, ab_b = max_food_duo_A_both_B_free(
        pairwise, a_entry, b_entry, cap1, cap2, blue_side_food)

    # --- DUO_SPLIT (A:cap1, B:cap2) ---
    duo_split, ds_a, ds_b1, ds_b2 = max_food_duo_split(
        pairwise, a_entry, b_entry, cap1, cap2, blue_side_food)

    # --- DUO_SWAP (B:cap1, A:cap2) ---
    duo_swap, _, _, _ = max_food_duo_split(
        pairwise, b_entry, a_entry, cap1, cap2, blue_side_food)

    # Verdict
    if solo_count >= WIN_THRESHOLD:
        verdict = 'SOLO_WIN'
    else:
        best_duo = max(duo_both, duo_split, duo_swap)
        if best_duo >= WIN_THRESHOLD:
            if duo_split == best_duo:
                verdict = 'DUO_SPLIT_WIN'
            elif duo_both == best_duo:
                verdict = 'DUO_A_BOTH_WIN'
            else:
                verdict = 'DUO_SWAP_WIN'
        elif best_duo >= 22:
            verdict = 'DUO_GOOD'
        elif best_duo >= 15:
            verdict = 'DUO_MODEST'
        else:
            verdict = 'NOT_FEASIBLE'

    return {
        'seed': seed,
        'verdict': verdict,
        'solo': solo_count,
        'duo_both': duo_both,
        'duo_split': duo_split,
        'duo_swap': duo_swap,
        'food_total_blue': len(blue_side_food),
    }


def main():
    print(f"{'seed':>4} | {'verdict':<18} | {'SOLO':>4} | {'D_BOTH':>6} {'D_SPLIT':>7} {'D_SWAP':>6} | {'food_blue':>9}")
    print('-' * 75)

    counts = {}
    for seed in range(1, 31):
        print(f"seed {seed} running...", end=' ', flush=True)
        res = analyze_map(seed)
        counts[res['verdict']] = counts.get(res['verdict'], 0) + 1
        food_blue = res.get('food_total_blue', 0)
        solo = res.get('solo', 0)
        dboth = res.get('duo_both', 0)
        dsplit = res.get('duo_split', 0)
        dswap = res.get('duo_swap', 0)
        print(f"\r{seed:>4} | {res['verdict']:<18} | {solo:>4} | {dboth:>6} {dsplit:>7} {dswap:>6} | {food_blue:>9}")

    print('\n=== Summary ===')
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {k:<20}: {v}/30")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Abstract-graph feasibility analyzer — 120 cases (30 seeds × 4 strategies).

Mirrors experiments/rc_tempo/feasibility_4strategies_parallel.py but uses the
abstract graph from abstract_graph.py + beam search from abstract_search.py.

Pm33 design doc (.omc/plans/pm33-abstract-graph-2cap-strategy.md) expects
~19-20 WIN at threshold 28. Compare side-by-side with food-level to detect
abstract-specific regressions.
"""
from __future__ import annotations
import os
import sys
import random
import time
from pathlib import Path
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
RC_TEMPO = REPO / "experiments" / "rc_tempo"

os.chdir(str(MINICONTEST))
if str(MINICONTEST) not in sys.path:
    sys.path.insert(0, str(MINICONTEST))
if str(RC_TEMPO) not in sys.path:
    sys.path.insert(0, str(RC_TEMPO))

import mazeGenerator as mg
from abstract_graph import build_from_maze, full_map_bfs
from abstract_search import beam_search_abstract


WIN_THRESHOLD = 28
SCARED_MAX = 79
CAP2_DEADLINE = 39
BEAM = 500
N_A_PLANS = 3
N_SEG1_PLANS = 3


def solve_split_abstract(graph, cap_A, cap_B, beam=None):
    if beam is None:
        beam = BEAM
    """A eats cap_A alone (budget=79); B eats cap_B via food detour
    (seg1 budget=39 to cap_B, seg2 budget=79-seg1_time to home). A/B food disjoint."""
    entry_xs = graph['entry_xs']
    if not entry_xs:
        return 0

    a_results = beam_search_abstract(graph, cap_A, entry_xs, budget=SCARED_MAX, beam=beam)
    if not a_results:
        return 0

    best = 0
    for a_res in a_results[:N_A_PLANS]:
        a_food = a_res['food']
        a_vx = a_res['visited_xs_mask']
        a_vh = a_res['visited_headers_mask']

        # B seg1: cap_B → any entry_X, budget=39. Edge symmetry: path food count
        # equals entry → cap_B with same visited set. Forbidden = A's food/headers.
        seg1_results = beam_search_abstract(
            graph, cap_B, entry_xs, budget=CAP2_DEADLINE,
            forbidden_xs_mask=a_vx, forbidden_headers_mask=a_vh, beam=beam)
        if not seg1_results:
            continue

        for seg1 in seg1_results[:N_SEG1_PLANS]:
            s1_food = seg1['food']
            s1_time = seg1['time']
            s1_vx = seg1['visited_xs_mask']
            s1_vh = seg1['visited_headers_mask']

            seg2_budget = SCARED_MAX - s1_time
            if seg2_budget <= 0:
                if s1_food + a_food > best:
                    best = s1_food + a_food
                continue

            seg2_results = beam_search_abstract(
                graph, cap_B, entry_xs, budget=seg2_budget,
                forbidden_xs_mask=a_vx | s1_vx,
                forbidden_headers_mask=a_vh | s1_vh, beam=beam)
            s2_food = seg2_results[0]['food'] if seg2_results else 0
            total = a_food + s1_food + s2_food
            if total > best:
                best = total
    return best


def solve_both_abstract(graph, cap_first, cap_second, beam=None):
    if beam is None:
        beam = BEAM
    """A: cap_first → food (seg1, budget=39) → cap_second → food (seg2, budget=79-s1t)
    → home. B: pure food from any entry → any entry (budget=79). Food disjoint."""
    entry_xs = graph['entry_xs']
    if not entry_xs:
        return 0

    seg1_results = beam_search_abstract(
        graph, cap_first, cap_second, budget=CAP2_DEADLINE, beam=beam)
    if not seg1_results:
        return 0

    best = 0
    for seg1 in seg1_results[:N_SEG1_PLANS]:
        s1_food = seg1['food']
        s1_time = seg1['time']
        s1_vx = seg1['visited_xs_mask']
        s1_vh = seg1['visited_headers_mask']

        seg2_budget = SCARED_MAX - s1_time
        if seg2_budget <= 0:
            continue

        seg2_results = beam_search_abstract(
            graph, cap_second, entry_xs, budget=seg2_budget,
            forbidden_xs_mask=s1_vx, forbidden_headers_mask=s1_vh, beam=beam)
        if not seg2_results:
            continue
        s2 = seg2_results[0]
        s2_food = s2['food']
        s2_vx = s2['visited_xs_mask']
        s2_vh = s2['visited_headers_mask']

        # B pure food: multi-source start, multi-sink end
        combined_vx = s1_vx | s2_vx
        combined_vh = s1_vh | s2_vh
        b_results = beam_search_abstract(
            graph, entry_xs, entry_xs, budget=SCARED_MAX,
            forbidden_xs_mask=combined_vx, forbidden_headers_mask=combined_vh,
            beam=beam)
        b_food = b_results[0]['food'] if b_results else 0

        total = s1_food + s2_food + b_food
        if total > best:
            best = total
    return best


def _setup(seed):
    random.seed(seed)
    maze_str = mg.generateMaze(seed)
    graph, walls, spawns = build_from_maze(maze_str)
    spawn_a = spawns['1']
    a_dists = full_map_bfs(walls, spawn_a, graph['W'], graph['H'])
    blue_caps = graph['blue_caps']
    if len(blue_caps) < 2:
        return None
    cap_sorted = sorted(blue_caps, key=lambda c: a_dists.get(c, 9999))
    cap1, cap2 = cap_sorted[0], cap_sorted[1]
    return {'graph': graph, 'cap1': cap1, 'cap2': cap2,
            'd_c12': a_dists.get(cap2, 9999) - a_dists.get(cap1, 9999)}


def worker(args):
    # args = (seed, strat) OR (seed, strat, beam). Beam overrides module-level BEAM.
    if len(args) == 3:
        seed, strat, beam = args
    else:
        seed, strat = args
        beam = BEAM
    ctx = _setup(seed)
    if ctx is None:
        return (seed, strat, 0, 0)
    g = ctx['graph']
    c1, c2 = ctx['cap1'], ctx['cap2']
    if strat == 'S1_CLOSE_SPLIT':
        food = solve_split_abstract(g, c1, c2, beam=beam)
    elif strat == 'S2_CLOSE_BOTH':
        food = solve_both_abstract(g, c1, c2, beam=beam)
    elif strat == 'S3_FAR_SPLIT':
        food = solve_split_abstract(g, c2, c1, beam=beam)
    elif strat == 'S4_FAR_BOTH':
        food = solve_both_abstract(g, c2, c1, beam=beam)
    else:
        food = 0
    return (seed, strat, food, ctx['d_c12'])


def main():
    t0 = time.time()
    tasks = []
    for seed in range(1, 31):
        for strat in ['S1_CLOSE_SPLIT', 'S2_CLOSE_BOTH', 'S3_FAR_SPLIT', 'S4_FAR_BOTH']:
            tasks.append((seed, strat))

    results = {}
    n_cpus = min(8, os.cpu_count() or 4)
    print(f"=== Abstract-graph feasibility analysis ===")
    print(f"    workers={n_cpus}, total_tasks={len(tasks)}, BEAM={BEAM}")

    done = 0
    with ProcessPoolExecutor(max_workers=n_cpus) as ex:
        futs = {ex.submit(worker, t): t for t in tasks}
        for fut in as_completed(futs):
            seed, strat, food, dc = fut.result()
            results.setdefault(seed, {'d_c12': dc})[strat] = food
            done += 1
            print(f"  progress: {done:>3}/{len(tasks)}  [{time.time() - t0:.1f}s]",
                  end='\r', flush=True)

    elapsed = time.time() - t0
    print(f"\n\n=== Results ({elapsed:.1f}s total) ===\n")

    print(f"{'sd':>2} | {'S1':>4} | {'S2':>4} | {'S3':>4} | {'S4':>4} | {'WIN':<20}")
    print('-' * 55)
    win_counts = {'S1_CLOSE_SPLIT': 0, 'S2_CLOSE_BOTH': 0,
                   'S3_FAR_SPLIT': 0, 'S4_FAR_BOTH': 0}
    any_win = 0
    win_seeds = []
    for seed in sorted(results.keys()):
        r = results[seed]
        wins = []
        for k in ['S1_CLOSE_SPLIT', 'S2_CLOSE_BOTH', 'S3_FAR_SPLIT', 'S4_FAR_BOTH']:
            if r.get(k, 0) >= WIN_THRESHOLD:
                wins.append(k.split('_')[0])
                win_counts[k] += 1
        if wins:
            any_win += 1
            win_seeds.append(seed)
        ws = '+'.join(wins) if wins else '-'
        print(f"{seed:>2} | "
              f"{r.get('S1_CLOSE_SPLIT', 0):>4} | {r.get('S2_CLOSE_BOTH', 0):>4} | "
              f"{r.get('S3_FAR_SPLIT', 0):>4} | {r.get('S4_FAR_BOTH', 0):>4} | "
              f"{ws:<20}")

    print('\n=== Summary ===')
    print(f"  ANY strategy WIN (>= {WIN_THRESHOLD}): {any_win}/30  (seeds: {win_seeds})")
    for k, v in win_counts.items():
        print(f"  {k}: {v}/30")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Parallel 4-strategy feasibility: 120 tasks (30 seeds × 4 strategies).

Each (seed, strategy) combination is independent → ProcessPoolExecutor.
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

# MUST do these at import time so workers inherit them
os.chdir(str(MINICONTEST))
if str(MINICONTEST) not in sys.path:
    sys.path.insert(0, str(MINICONTEST))

import mazeGenerator as mg

WIN_THRESHOLD = 28
SCARED_MAX = 79
CAP2_DEADLINE = 39
BEAM = 500


def parse_layout(maze_str):
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    walls = [[False]*cols for _ in range(rows)]
    food, caps, spawns = [], [], {}
    for r, line in enumerate(lines):
        y = rows - 1 - r
        for c, ch in enumerate(line):
            if ch == '%': walls[r][c] = True
            elif ch == '.': food.append((c, y))
            elif ch == 'o': caps.append((c, y))
            elif ch in '1234': spawns[ch] = (c, y)
    return walls, food, caps, spawns, (cols, rows)


def bfs(walls, start, W, H):
    dists = {start: 0}
    q = deque([start])
    while q:
        p = q.popleft()
        x, y = p
        d = dists[p]
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x+dx, y+dy
            if not (0<=nx<W and 0<=ny<H): continue
            r = H-1-ny
            if walls[r][nx]: continue
            if (nx, ny) not in dists:
                dists[(nx, ny)] = d+1
                q.append((nx, ny))
    return dists


def build_pw(walls, cells, W, H):
    pw = {}
    for c in cells:
        d = bfs(walls, c, W, H)
        for o in cells:
            if o in d:
                pw[(c, o)] = d[o]
    return pw


def beam_search(start, end, food_list, budget, pw, beam=BEAM, mid_col=17):
    """Beam search with depth priority: same food count → prefer deeper harvest.
    depth of food f = f[0] - mid_col (x-distance from midline, blue side)
    """
    def depth_sum(vis_set):
        return sum(max(f[0] - mid_col, 0) for f in vis_set)

    init = (start, 0, frozenset())
    states = [init]
    found = []
    for _ in range(40):
        if not states: break
        nxt = []
        seen = {}
        for (pos, t, vis) in states:
            for f in food_list:
                if f in vis: continue
                dpf = pw.get((pos, f))
                dfe = pw.get((f, end))
                if dpf is None or dfe is None: continue
                nt = t + dpf
                if nt + dfe > budget: continue
                new_vis = vis | {f}
                key = (f, new_vis)
                if key in seen and seen[key] <= nt: continue
                seen[key] = nt
                nxt.append((f, nt, new_vis))
            dpe = pw.get((pos, end))
            if dpe is not None and t + dpe <= budget:
                found.append((vis, t + dpe))
        # Priority: (primary) max food count; (secondary) max depth sum; (tertiary) min time
        nxt.sort(key=lambda s: (-len(s[2]), -depth_sum(s[2]), s[1]))
        states = nxt[:beam]
    found.sort(key=lambda s: (-len(s[0]), -depth_sum(s[0]), s[1]))
    seen_sets = set()
    result = []
    for v, t in found:
        if v in seen_sets: continue
        seen_sets.add(v)
        result.append((v, t))
    return result


def _setup(seed):
    """Setup once per seed. Returns map context."""
    random.seed(seed)
    maze_str = mg.generateMaze(seed)
    walls, food, caps, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2
    blue_food = [f for f in food if f[0] >= mid_col]
    blue_caps = [c for c in caps if c[0] >= mid_col]
    a_spawn = spawns['1']
    dists_a = bfs(walls, a_spawn, W, H)
    cap_sorted = sorted(blue_caps, key=lambda c: dists_a.get(c, 9999))
    cap1, cap2 = cap_sorted[0], cap_sorted[1]
    red_edges = []
    for r in range(H):
        c = mid_col - 1
        if c >= 0 and not walls[r][c]:
            y = H - 1 - r
            red_edges.append((c, y))
    cells = list(set([cap1, cap2] + blue_food + red_edges))
    pw = build_pw(walls, cells, W, H)
    return {'cap1': cap1, 'cap2': cap2, 'blue_food': blue_food,
            'red_edges': red_edges, 'pw': pw,
            'd_c1_c2': pw.get((cap1, cap2), 9999)}


def solve_split(ctx, cap_A, cap_B):
    """A eats cap_A alone. B eats cap_B after food detour. Both harvest food."""
    pw = ctx['pw']
    red_edges = ctx['red_edges']
    blue_food = ctx['blue_food']
    best = 0
    a_homes = sorted(red_edges, key=lambda r: pw.get((cap_A, r), 9999))[:3]
    b_homes = sorted(red_edges, key=lambda r: pw.get((cap_B, r), 9999))[:3]
    b_starts = sorted(red_edges, key=lambda r: pw.get((r, cap_B), 9999))[:4]
    for ah in a_homes:
        a_opts = beam_search(cap_A, ah, blue_food, SCARED_MAX, pw)
        if not a_opts: continue
        a_food = a_opts[0][0]
        for bs in b_starts:
            rem = [f for f in blue_food if f not in a_food]
            seg1 = beam_search(bs, cap_B, rem, CAP2_DEADLINE, pw)
            if not seg1: continue
            for s1f, s1c in seg1[:2]:
                avail2 = [f for f in rem if f not in s1f]
                for bh in b_homes:
                    seg2 = beam_search(cap_B, bh, avail2, SCARED_MAX - s1c, pw)
                    if not seg2: continue
                    total = len(a_food) + len(s1f) + len(seg2[0][0])
                    if total > best: best = total
    return best


def solve_both(ctx, cap_first, cap_second):
    """A eats cap_first→food→cap_second→food→home. B pure food harvest."""
    pw = ctx['pw']
    red_edges = ctx['red_edges']
    blue_food = ctx['blue_food']
    best = 0
    a_homes = sorted(red_edges, key=lambda r: pw.get((cap_second, r), 9999))[:3]
    for ah in a_homes:
        seg1 = beam_search(cap_first, cap_second, blue_food, CAP2_DEADLINE, pw)
        if not seg1: continue
        for s1f, s1c in seg1[:3]:
            rem = [f for f in blue_food if f not in s1f]
            seg2 = beam_search(cap_second, ah, rem, SCARED_MAX - s1c, pw)
            if not seg2: continue
            s2f = seg2[0][0]
            a_total = len(s1f) + len(s2f)
            # B: pure food
            b_rem = [f for f in blue_food if f not in s1f and f not in s2f]
            b_best = 0
            for bs in red_edges[:5]:
                for bh in red_edges[:5]:
                    b_opts = beam_search(bs, bh, b_rem, SCARED_MAX, pw)
                    if b_opts and len(b_opts[0][0]) > b_best:
                        b_best = len(b_opts[0][0])
            total = a_total + b_best
            if total > best: best = total
    return best


def worker(args):
    """args = (seed, strategy_name). Returns (seed, strategy_name, food_count)."""
    seed, strat = args
    # Cache ctx per seed? Across processes, no — just recompute.
    ctx = _setup(seed)
    if strat == 'S1_CLOSE_SPLIT':
        food = solve_split(ctx, ctx['cap1'], ctx['cap2'])
    elif strat == 'S2_CLOSE_BOTH':
        food = solve_both(ctx, ctx['cap1'], ctx['cap2'])
    elif strat == 'S3_FAR_SPLIT':
        food = solve_split(ctx, ctx['cap2'], ctx['cap1'])
    elif strat == 'S4_FAR_BOTH':
        food = solve_both(ctx, ctx['cap2'], ctx['cap1'])
    return (seed, strat, food, ctx['d_c1_c2'])


def main():
    t0 = time.time()
    # Build 120 tasks
    tasks = []
    for seed in range(1, 31):
        for strat in ['S1_CLOSE_SPLIT', 'S2_CLOSE_BOTH', 'S3_FAR_SPLIT', 'S4_FAR_BOTH']:
            tasks.append((seed, strat))

    results = {}  # {seed: {strat: food, 'd_c1_c2': ..}}
    n_cpus = min(8, os.cpu_count() or 4)
    print(f"=== Parallel 4-strategy feasibility analysis ===")
    print(f"    workers={n_cpus}, total_tasks={len(tasks)}")

    done = 0
    with ProcessPoolExecutor(max_workers=n_cpus) as ex:
        futs = {ex.submit(worker, t): t for t in tasks}
        for fut in as_completed(futs):
            seed, strat, food, dc = fut.result()
            if seed not in results:
                results[seed] = {'d_c1_c2': dc}
            results[seed][strat] = food
            done += 1
            elapsed = time.time() - t0
            print(f"  progress: {done:>3}/{len(tasks)}  [{elapsed:.1f}s]",
                  end='\r', flush=True)

    elapsed = time.time() - t0
    print(f"\n\n=== Results ({elapsed:.1f}s total) ===\n")

    print(f"{'sd':>2} | {'d_c12':>5} | "
          f"{'S1':>4} | {'S2':>4} | {'S3':>4} | {'S4':>4} | {'WIN':<20}")
    print('-' * 65)
    win_counts = {'S1_CLOSE_SPLIT': 0, 'S2_CLOSE_BOTH': 0,
                   'S3_FAR_SPLIT': 0, 'S4_FAR_BOTH': 0}
    any_win = 0
    for seed in sorted(results.keys()):
        r = results[seed]
        wins = []
        for k in ['S1_CLOSE_SPLIT', 'S2_CLOSE_BOTH', 'S3_FAR_SPLIT', 'S4_FAR_BOTH']:
            if r.get(k, 0) >= WIN_THRESHOLD:
                wins.append(k.split('_')[0])
                win_counts[k] += 1
        if wins: any_win += 1
        ws = '+'.join(wins) if wins else '-'
        print(f"{seed:>2} | {r['d_c1_c2']:>5} | "
              f"{r['S1_CLOSE_SPLIT']:>4} | {r['S2_CLOSE_BOTH']:>4} | "
              f"{r['S3_FAR_SPLIT']:>4} | {r['S4_FAR_BOTH']:>4} | {ws:<20}")

    print('\n=== Summary ===')
    print(f"  ANY strategy WIN (≥28):     {any_win}/30")
    for k, v in win_counts.items():
        print(f"  {k}: {v}/30")
    print()
    print("  Legend:")
    print("    S1 CLOSE_SPLIT = A eats cap1(close), B eats cap2(far)")
    print("    S2 CLOSE_BOTH  = A eats cap1→cap2 (detour), B food only")
    print("    S3 FAR_SPLIT   = A eats cap2(far), B eats cap1(close)")
    print("    S4 FAR_BOTH    = A eats cap2→cap1 (detour), B food only")


if __name__ == '__main__':
    main()

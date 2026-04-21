#!/usr/bin/env python3
"""4-strategy feasibility analysis for RANDOM<1..30>.

Strategies:
  1. CLOSE_SPLIT   — A eats cap1 (close), B eats cap2 (far). Both harvest food.
  2. CLOSE_BOTH    — A eats cap1 (close) then cap2 (far, detour). B pure food.
  3. FAR_SPLIT     — A eats cap2 (far), B eats cap1 (close). Both harvest food.
  4. FAR_BOTH      — A eats cap2 (far) then cap1 (close, detour). B pure food.

Correct initial conditions:
  - A starts AT the capsule it ate (first cap) right after eating
  - B starts on RED side (mid_col-1) at some optimal y, just before crossing
  - Both end on red side (closest red-edge cell)
  - Scared budget: 79 A-moves total, cap-2 by A's 39th move post-cap-1

For each map, report which of the 4 strategies achieve ≥28 food.
"""
from __future__ import annotations
import os
import sys
import random
from pathlib import Path
from collections import deque

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
os.chdir(str(MINICONTEST))
sys.path.insert(0, str(MINICONTEST))

import mazeGenerator as mg

WIN_THRESHOLD = 28
SCARED_MAX = 79
CAP2_DEADLINE = 39
BEAM = 2000


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


def beam(start, end, food, budget, pw, beam=BEAM):
    """Returns list of (collected_frozenset, total_cost)."""
    init = (start, 0, frozenset())
    states = [init]
    found = []
    for _ in range(40):
        if not states: break
        nxt = []
        seen = {}
        for (pos, t, vis) in states:
            for f in food:
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
        nxt.sort(key=lambda s: (-len(s[2]), s[1]))
        states = nxt[:beam]
    found.sort(key=lambda s: (-len(s[0]), s[1]))
    seen_sets = set()
    result = []
    for v, t in found:
        if v in seen_sets: continue
        seen_sets.add(v)
        result.append((v, t))
    return result


def solve_split(pw, cap_A, cap_B, red_edges, blue_food):
    """A eats cap_A alone. B eats cap_B after food detour.

    A: cap_A → food → best red-edge (budget 79)
    B: best red-edge → food → cap_B (within 39) → food → best red-edge (total 79)
    """
    best_total = 0
    # Pick top 3 red-edge candidates for A's home (nearest to cap_A)
    a_home_cands = sorted(red_edges, key=lambda r: pw.get((cap_A, r), 9999))[:3]
    b_home_cands = sorted(red_edges, key=lambda r: pw.get((cap_B, r), 9999))[:3]
    # B start candidates: top 4 red-edges nearest to cap_B (B wants short travel to cap_B)
    b_start_cands = sorted(red_edges, key=lambda r: pw.get((r, cap_B), 9999))[:4]

    for a_home in a_home_cands:
        a_opts = beam(cap_A, a_home, blue_food, SCARED_MAX, pw)
        if not a_opts: continue
        a_food = a_opts[0][0]

        for b_start in b_start_cands:
            remaining = [f for f in blue_food if f not in a_food]
            seg1 = beam(b_start, cap_B, remaining, CAP2_DEADLINE, pw)
            if not seg1: continue
            for seg1_food, seg1_cost in seg1[:2]:
                avail2 = [f for f in remaining if f not in seg1_food]
                for b_home in b_home_cands:
                    seg2 = beam(cap_B, b_home, avail2, SCARED_MAX - seg1_cost, pw)
                    if not seg2: continue
                    seg2_food = seg2[0][0]
                    total = len(a_food) + len(seg1_food) + len(seg2_food)
                    if total > best_total:
                        best_total = total
    return best_total


def solve_both(pw, cap_first, cap_second, red_edges, blue_food):
    """A eats cap_first → food → cap_second (within 39) → food → red-edge. B pure food."""
    best_total = 0
    a_home_cands = sorted(red_edges, key=lambda r: pw.get((cap_second, r), 9999))[:3]

    for a_home in a_home_cands:
        # A seg 1: cap_first → food → cap_second within 39
        seg1 = beam(cap_first, cap_second, blue_food, CAP2_DEADLINE, pw)
        if not seg1: continue
        for seg1_food, seg1_cost in seg1[:3]:
            remaining = [f for f in blue_food if f not in seg1_food]
            # A seg 2: cap_second → food → a_home within (79 - 39 = 40)
            seg2_budget = SCARED_MAX - seg1_cost
            seg2 = beam(cap_second, a_home, remaining, seg2_budget, pw)
            if not seg2: continue
            seg2_food = seg2[0][0]
            a_total = len(seg1_food) + len(seg2_food)

            # B: pure food harvester (A-food already taken)
            b_remaining = [f for f in blue_food if f not in seg1_food and f not in seg2_food]
            # B starts at red-edge, returns to red-edge, budget 79
            b_best = 0
            b_start_cands = sorted(red_edges, key=lambda r: -min(
                [pw.get((r, f), 9999) for f in b_remaining[:5]] if b_remaining else [9999]))[:4]
            for b_s in red_edges[:6]:  # try a subset
                for b_h in red_edges[:6]:
                    b_opts = beam(b_s, b_h, b_remaining, SCARED_MAX, pw)
                    if not b_opts: continue
                    bf = len(b_opts[0][0])
                    if bf > b_best: b_best = bf

            total = a_total + b_best
            if total > best_total:
                best_total = total
    return best_total


def analyze_map(seed):
    random.seed(seed)
    maze_str = mg.generateMaze(seed)
    walls, food, caps, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    blue_food = [f for f in food if f[0] >= mid_col]
    blue_caps = [c for c in caps if c[0] >= mid_col]

    if len(blue_caps) < 2:
        return None

    a_spawn = spawns['1']
    dists_a = bfs(walls, a_spawn, W, H)
    cap_sorted = sorted(blue_caps, key=lambda c: dists_a.get(c, 9999))
    cap1, cap2 = cap_sorted[0], cap_sorted[1]  # cap1=close, cap2=far

    red_edges = []
    for r in range(H):
        c = mid_col - 1
        if c >= 0 and not walls[r][c]:
            y = H - 1 - r
            red_edges.append((c, y))

    cells = list(set([cap1, cap2] + blue_food + red_edges))
    pw = build_pw(walls, cells, W, H)

    # 4 strategies
    s1 = solve_split(pw, cap1, cap2, red_edges, blue_food)  # A:close, B:far
    s2 = solve_both(pw, cap1, cap2, red_edges, blue_food)   # A:close→far, B:food
    s3 = solve_split(pw, cap2, cap1, red_edges, blue_food)  # A:far, B:close
    s4 = solve_both(pw, cap2, cap1, red_edges, blue_food)   # A:far→close, B:food

    return {
        'seed': seed,
        'cap1': cap1, 'cap2': cap2,
        'd_c1_c2': pw.get((cap1, cap2), 9999),
        's1_CLOSE_SPLIT': s1,
        's2_CLOSE_BOTH': s2,
        's3_FAR_SPLIT': s3,
        's4_FAR_BOTH': s4,
    }


def main():
    print(f"{'sd':>2} | {'d_c1c2':>6} | "
          f"{'S1 CLSPL':>8} | {'S2 CLBTH':>8} | {'S3 FRSPL':>8} | {'S4 FRBTH':>8} | "
          f"{'WINS':<20}")
    print('-' * 80)

    win_counts = {'S1': 0, 'S2': 0, 'S3': 0, 'S4': 0}
    any_win_count = 0

    for seed in range(1, 31):
        print(f"  seed {seed} ...", end='\r', flush=True)
        res = analyze_map(seed)
        if res is None: continue
        wins = []
        for key, label in [('s1_CLOSE_SPLIT', 'S1'), ('s2_CLOSE_BOTH', 'S2'),
                            ('s3_FAR_SPLIT', 'S3'), ('s4_FAR_BOTH', 'S4')]:
            if res[key] >= WIN_THRESHOLD:
                wins.append(label)
                win_counts[label] += 1
        if wins: any_win_count += 1
        win_str = '+'.join(wins) if wins else '-'
        print(f"{seed:>2} | {res['d_c1_c2']:>6} | "
              f"{res['s1_CLOSE_SPLIT']:>8} | {res['s2_CLOSE_BOTH']:>8} | "
              f"{res['s3_FAR_SPLIT']:>8} | {res['s4_FAR_BOTH']:>8} | "
              f"{win_str:<20}")

    print('\n=== Summary ===')
    print(f"  ANY strategy WIN (≥28):     {any_win_count}/30")
    for k, v in win_counts.items():
        print(f"  {k} wins: {v}/30")
    print(f"\n  Strategies:")
    print(f"    S1 CLOSE_SPLIT = A eats close (cap1), B eats far (cap2)")
    print(f"    S2 CLOSE_BOTH  = A eats cap1 then cap2 (detour), B food only")
    print(f"    S3 FAR_SPLIT   = A eats far (cap2), B eats close (cap1)")
    print(f"    S4 FAR_BOTH    = A eats cap2 then cap1 (detour), B food only")


if __name__ == '__main__':
    main()

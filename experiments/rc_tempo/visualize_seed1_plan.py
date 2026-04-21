#!/usr/bin/env python3
"""Visualize optimal DUO plan for RANDOM1 (fast, simplified)."""
from __future__ import annotations
import os
import sys
import random
from pathlib import Path
from collections import deque
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
os.chdir(str(MINICONTEST))
sys.path.insert(0, str(MINICONTEST))

import mazeGenerator as mg

SEED = 1
SCARED_MAX = 79
CAP2_DEADLINE = 39
BEAM = 2000
CELL = 24
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_PLAN.png"


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
    parents = {start: None}
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
                parents[(nx, ny)] = p
                q.append((nx, ny))
    return dists, parents


def path_to(parents, end):
    if end not in parents: return None
    p = [end]
    cur = end
    while parents[cur] is not None:
        cur = parents[cur]
        p.append(cur)
    p.reverse()
    return p


def build_pw(walls, cells, W, H):
    pw, pw_paths = {}, {}
    for c in cells:
        d, par = bfs(walls, c, W, H)
        for o in cells:
            if o in d:
                pw[(c, o)] = d[o]
                pw_paths[(c, o)] = path_to(par, o)
    return pw, pw_paths


def beam(start, end, food, budget, pw, beam=BEAM):
    init = (start, 0, frozenset(), ())
    states = [init]
    found = []
    for _ in range(40):
        if not states: break
        nxt = []
        seen = {}
        for (pos, t, vis, order) in states:
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
                nxt.append((f, nt, new_vis, order + (f,)))
            dpe = pw.get((pos, end))
            if dpe is not None and t + dpe <= budget:
                found.append((vis, t + dpe, order))
        nxt.sort(key=lambda s: (-len(s[2]), s[1]))
        states = nxt[:beam]
    found.sort(key=lambda s: (-len(s[0]), s[1]))
    seen_sets = set()
    result = []
    for v, t, o in found:
        if v in seen_sets: continue
        seen_sets.add(v)
        result.append((v, t, o))
    return result


def expand(start, end, order, pw_paths):
    full = [start]
    cur = start
    for wp in order:
        seg = pw_paths.get((cur, wp))
        if seg is None: return None
        full.extend(seg[1:])
        cur = wp
    seg = pw_paths.get((cur, end))
    if seg is None: return None
    full.extend(seg[1:])
    return full


def main():
    print(f"=== RANDOM{SEED} ===")
    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food, caps, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    blue_food = [f for f in food if f[0] >= mid_col]
    blue_caps = [c for c in caps if c[0] >= mid_col]

    a_spawn = spawns['1']
    dists_a, _ = bfs(walls, a_spawn, W, H)
    cap_sorted = sorted(blue_caps, key=lambda c: dists_a.get(c, 9999))
    cap1, cap2 = cap_sorted[0], cap_sorted[1]
    print(f"  cap1={cap1} cap2={cap2}")

    # Red-side midline cells (col=mid_col-1, not wall)
    red_edges = []
    for r in range(H):
        c = mid_col - 1
        if c >= 0 and not walls[r][c]:
            y = H-1-r
            red_edges.append((c, y))
    print(f"  red-edge cells: {len(red_edges)}")

    # pairwise
    cells = list(set([cap1, cap2] + blue_food + red_edges))
    print(f"  computing pairwise {len(cells)} cells...")
    pw, pw_paths = build_pw(walls, cells, W, H)

    # --- DUO_SPLIT: A from cap1 → food → red. B from red → food → cap2 → food → red ---
    # Try a few candidate home points heuristically (closest to cap1 for A, farthest for B)
    a_home_candidates = sorted(red_edges, key=lambda r: pw.get((cap1, r), 9999))[:3]
    b_home_candidates = sorted(red_edges, key=lambda r: pw.get((cap2, r), 9999))[:3]
    b_start_candidates = red_edges  # try all as start

    print(f"  evaluating combos...")
    best = (0, None, None, None, None, None)
    counter = 0
    for a_home in a_home_candidates:
        a_opts = beam(cap1, a_home, blue_food, SCARED_MAX, pw, beam=BEAM)
        if not a_opts: continue
        a_food, a_cost, a_order = a_opts[0]

        for b_start in b_start_candidates[:6]:  # top few
            remaining_food = [f for f in blue_food if f not in a_food]
            seg1_opts = beam(b_start, cap2, remaining_food, CAP2_DEADLINE, pw, beam=BEAM)
            if not seg1_opts: continue
            for seg1_food, seg1_cost, seg1_order in seg1_opts[:3]:
                seg2_food_avail = [f for f in remaining_food if f not in seg1_food]
                seg2_budget = SCARED_MAX - seg1_cost
                for b_home in b_home_candidates:
                    seg2_opts = beam(cap2, b_home, seg2_food_avail, seg2_budget, pw, beam=BEAM)
                    if not seg2_opts: continue
                    seg2_food, seg2_cost, seg2_order = seg2_opts[0]
                    total = len(a_food) + len(seg1_food) + len(seg2_food)
                    counter += 1
                    if total > best[0]:
                        a_path = expand(cap1, a_home, a_order, pw_paths)
                        b_full_order = tuple(list(seg1_order) + [cap2] + list(seg2_order))
                        b_path = expand(b_start, b_home, b_full_order, pw_paths)
                        best = (total, a_path, b_path, set(a_food), set(seg1_food) | set(seg2_food),
                                f"A:cap1→food→{a_home} ({a_cost}m)  B:{b_start}→food→cap2→food→{b_home} ({seg1_cost+seg2_cost}m)")
    print(f"  combos evaluated: {counter}")

    total_food, a_path, b_path, a_food, b_food, label = best
    print(f"\n=== BEST: {total_food} total food ===")
    print(f"  {label}")
    print(f"  A path length: {len(a_path)-1} moves, food: {len(a_food)}")
    print(f"  B path length: {len(b_path)-1} moves, food: {len(b_food)}")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 130
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} optimal DUO plan — 79-move scared window", fill=(20, 20, 20))
    draw.text((10, 23), f"A (red): cap1 {cap1} -> food x{len(a_food)} -> home.  {len(a_path)-1} moves", fill=(180, 30, 30))
    draw.text((10, 41), f"B (blue): home -> food -> cap2 {cap2} -> food -> home.  food x{len(b_food)}  {len(b_path)-1} moves", fill=(30, 30, 180))
    draw.text((10, 59), f"TOTAL FOOD: {total_food} / 30 blue-side  (need 28+ for WIN)", fill=(20, 120, 20))
    draw.text((10, 77), f"Note: red food = A ate, blue food = B ate, yellow = remaining", fill=(80, 80, 80))

    ORIG_Y = 100
    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            x0, y0 = c*CELL, ORIG_Y + r*CELL
            x1, y1 = x0+CELL, y0+CELL
            if ch == '%':
                draw.rectangle([x0,y0,x1,y1], fill=(40,40,60))
            else:
                if c < mid_col:
                    draw.rectangle([x0,y0,x1,y1], fill=(250,240,240))
                else:
                    draw.rectangle([x0,y0,x1,y1], fill=(240,245,255))
                if ch == '.':
                    y = rows-1-r
                    pos = (c, y)
                    cx, cy = x0+CELL//2, y0+CELL//2
                    rd = CELL//6
                    if pos in a_food: color = (220,80,80)
                    elif pos in b_food: color = (80,80,220)
                    else: color = (230,210,80)
                    draw.ellipse([cx-rd, cy-rd, cx+rd, cy+rd], fill=color)
                elif ch == 'o':
                    y = rows-1-r
                    pos = (c, y)
                    cx, cy = x0+CELL//2, y0+CELL//2
                    rd = CELL//2 - 3
                    draw.ellipse([cx-rd, cy-rd, cx+rd, cy+rd], fill=(255,60,200), outline=(80,10,60), width=2)
                    lbl = 'C1' if pos == cap1 else 'C2'
                    draw.text((cx-8, cy-6), lbl, fill=(255,255,255))
                elif ch in '1234':
                    draw.rectangle([x0+3,y0+3,x1-3,y1-3], fill=(100,100,100))
                    draw.text((x0+CELL//4, y0+CELL//8), ch, fill=(255,255,255))

    def px(cell):
        c, y = cell
        r = rows-1-y
        return (c*CELL+CELL//2, ORIG_Y + r*CELL + CELL//2)

    # A path (red arrows, thick)
    for i in range(len(a_path)-1):
        p1, p2 = px(a_path[i]), px(a_path[i+1])
        draw.line([p1, p2], fill=(200,40,40), width=3)
    # A endpoints
    sp = px(a_path[0])
    draw.ellipse([sp[0]-8, sp[1]-8, sp[0]+8, sp[1]+8], outline=(150,10,10), width=3)
    draw.text((sp[0]-5, sp[1]-7), 'A', fill=(150,10,10))
    ep = px(a_path[-1])
    draw.rectangle([ep[0]-7, ep[1]-7, ep[0]+7, ep[1]+7], outline=(150,10,10), width=3)
    draw.text((ep[0]-9, ep[1]-7), 'A*', fill=(150,10,10))

    # B path (blue, thick)
    for i in range(len(b_path)-1):
        p1, p2 = px(b_path[i]), px(b_path[i+1])
        draw.line([p1, p2], fill=(40,80,220), width=3)
    sp = px(b_path[0])
    draw.ellipse([sp[0]-8, sp[1]-8, sp[0]+8, sp[1]+8], outline=(10,30,150), width=3)
    draw.text((sp[0]-5, sp[1]-7), 'B', fill=(10,30,150))
    ep = px(b_path[-1])
    draw.rectangle([ep[0]-7, ep[1]-7, ep[0]+7, ep[1]+7], outline=(10,30,150), width=3)
    draw.text((ep[0]-9, ep[1]-7), 'B*', fill=(10,30,150))

    mx = mid_col * CELL
    draw.line([(mx, ORIG_Y), (mx, ORIG_Y + rows*CELL)], fill=(150,150,150), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == '__main__':
    main()

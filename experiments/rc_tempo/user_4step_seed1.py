#!/usr/bin/env python3
"""User's 4-step algorithm for abstract graph.

Step 1: 포켓 만들기 (leaf pruning)
Step 2: 포켓 헤더 중에 음식 있는 것만 (food_count > 0)
Step 3: "검은색 X" = {main-corridor food} ∪ {pocket mouths with food} ∪ {caps}
Step 4: 서로 직접 연결된 것만 연결
   (= Voronoi-neighbor on main corridor — no other X node between)
"""
from __future__ import annotations
import os
import sys
import random
import time
from pathlib import Path
from collections import deque
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
os.chdir(str(MINICONTEST))
sys.path.insert(0, str(MINICONTEST))

import mazeGenerator as mg

SEED = 1
CELL = 28
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_4STEP.png"


def parse_layout(maze_str):
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    walls = [[False]*cols for _ in range(rows)]
    food_set, cap_set, spawns = set(), set(), {}
    for r, line in enumerate(lines):
        y = rows - 1 - r
        for c, ch in enumerate(line):
            if ch == '%': walls[r][c] = True
            elif ch == '.': food_set.add((c, y))
            elif ch == 'o': cap_set.add((c, y))
            elif ch in '1234': spawns[ch] = (c, y)
    return walls, food_set, cap_set, spawns, (cols, rows)


def build_graph(walls, W, H):
    cells = set()
    for r in range(H):
        for c in range(W):
            if not walls[r][c]:
                y = H - 1 - r
                cells.add((c, y))
    neighbors = {c: [] for c in cells}
    for (x, y) in cells:
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            n = (x+dx, y+dy)
            if n in cells:
                neighbors[(x, y)].append(n)
    return cells, neighbors


def step1_find_pockets(cells, neighbors):
    """Leaf pruning → pocket cells + parent chain."""
    orig_degree = {c: len(neighbors[c]) for c in cells}
    degree = dict(orig_degree)
    pruned = set()
    parent = {}
    leaf_q = deque([c for c in cells if degree[c] == 1])
    while leaf_q:
        v = leaf_q.popleft()
        if v in pruned: continue
        if degree[v] != 1: continue
        active = [n for n in neighbors[v] if n not in pruned]
        if len(active) != 1: continue
        p = active[0]
        parent[v] = p
        pruned.add(v)
        degree[p] -= 1
        if degree[p] == 1:
            leaf_q.append(p)
    return pruned, parent


def step2_get_pocket_mouths_with_food(pruned, parent, main_corridor, food_set):
    """Each tip traces to main corridor; its path cells + attach = 1 sub-branch.
    Return list of (mouth, food_count, cells_in_branch, max_food_depth).
    """
    children = {}
    for c, p in parent.items():
        children.setdefault(p, []).append(c)
    tips = [c for c in pruned if c not in children]

    subs = []
    for tip in tips:
        trace = [tip]
        cur = tip
        attach = None
        while cur in parent:
            nxt = parent[cur]
            if nxt in main_corridor:
                attach = nxt
                break
            trace.append(nxt)
            cur = nxt
        if attach is None: continue
        food_here = [c for c in trace if c in food_set]
        if not food_here: continue  # Step 2: filter empty pockets
        max_fd = 0
        for i, c in enumerate(trace):
            if c in food_set:
                d = len(trace) - i
                if d > max_fd: max_fd = d
        subs.append({
            'attach': attach,
            'cells': trace,
            'food': food_here,
            'max_food_depth': max_fd,
            'visit_cost': 2 * max_fd,
            'food_count': len(food_here),
        })
    return subs


def step3_interest_nodes(sub_branches, main_corridor, food_set, cap_set, mid_col):
    """Build set of 'black X' interest nodes (blue-side only).

    Interest nodes:
      - Main-corridor food cells
      - Pocket mouth cells (where at least 1 sub-branch has food)
      - Cap cells

    Since mouths may have multiple sub-branches, group them: unique positions with
    a list of visit options.
    """
    interest = {}  # cell -> {'type': 'food'/'mouth'/'cap', 'options': list of (cost, food)}

    # Main-corridor food
    for f in food_set:
        if f in main_corridor and f[0] >= mid_col:
            interest[f] = {'type': 'food', 'options': [(0, 1)], 'food_total': 1}

    # Pocket mouths
    mouth_to_options = {}
    for s in sub_branches:
        if s['attach'][0] < mid_col: continue  # blue side only
        mouth_to_options.setdefault(s['attach'], []).append(
            (s['visit_cost'], s['food_count']))
    for m, opts in mouth_to_options.items():
        # Compute food_total = sum of food in all sub-branches (upper bound for visiting all)
        total_food = sum(f for (c, f) in opts)
        interest[m] = {'type': 'mouth', 'options': opts, 'food_total': total_food}

    # Caps
    for c in cap_set:
        if c[0] >= mid_col:
            # May overlap with mouth
            if c in interest:
                interest[c]['type'] = 'cap+mouth'
            else:
                interest[c] = {'type': 'cap', 'options': [(0, 0)], 'food_total': 0}

    return interest


def step4_direct_edges(interest, main_corridor, walls, W, H):
    """Blocked-BFS: for each X, BFS on main corridor until reaching another X.
    Other X nodes act as terminators (stop expansion at them) — so reaching one means
    that one is a direct neighbor with recorded distance.
    """
    interest_set = set(interest.keys())
    edges = {}  # (A, B) -> min distance

    for src in interest_set:
        if src not in main_corridor:
            continue
        visited = {src}
        q = deque([(src, 0)])
        while q:
            p, d = q.popleft()
            # If p is an interest node (other than src), record as neighbor and stop expanding
            if p != src and p in interest_set:
                A, B = tuple(sorted([src, p]))
                if (A, B) not in edges or edges[(A, B)] > d:
                    edges[(A, B)] = d
                continue  # don't expand past another X
            x, y = p
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx, ny = x+dx, y+dy
                if not (0<=nx<W and 0<=ny<H): continue
                r = H-1-ny
                if walls[r][nx]: continue
                n = (nx, ny)
                if n not in main_corridor: continue
                if n in visited: continue
                visited.add(n)
                q.append((n, d+1))
    # No owner map returned (not needed for blocked-BFS), use empty dict
    return edges, {}


def main():
    print(f"=== RANDOM{SEED} — User's 4-step algorithm ===\n")
    t0 = time.time()

    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    cells, neighbors = build_graph(walls, W, H)
    t1 = time.time()
    print(f"[setup] build graph: {(t1-t0)*1000:.2f} ms ({len(cells)} cells)")

    # Step 1: Pockets
    t_s = time.time()
    pruned, parent = step1_find_pockets(cells, neighbors)
    t_e = time.time()
    main_corridor = cells - pruned
    print(f"[STEP 1] 포켓 만들기: {(t_e-t_s)*1000:.2f} ms "
          f"(main: {len(main_corridor)}  pocket cells: {len(pruned)})")

    # Step 2: Keep pockets with food
    t_s = time.time()
    subs = step2_get_pocket_mouths_with_food(pruned, parent, main_corridor, food_set)
    blue_subs = [s for s in subs if s['attach'][0] >= mid_col]
    t_e = time.time()
    print(f"[STEP 2] 포켓 헤더 (음식 있는 것만): {(t_e-t_s)*1000:.2f} ms "
          f"({len(blue_subs)} sub-branches with food, blue side)")
    unique_mouths = set(s['attach'] for s in blue_subs)
    print(f"         unique pocket mouths: {len(unique_mouths)}")
    for m in sorted(unique_mouths):
        opts = [(s['visit_cost'], s['food_count']) for s in blue_subs if s['attach'] == m]
        print(f"         mouth {m}: options = {opts}")

    # Step 3: Interest nodes
    t_s = time.time()
    interest = step3_interest_nodes(blue_subs, main_corridor, food_set, cap_set, mid_col)
    t_e = time.time()
    n_main_food = sum(1 for v in interest.values() if v['type'] == 'food')
    n_mouth = sum(1 for v in interest.values() if 'mouth' in v['type'])
    n_cap = sum(1 for v in interest.values() if 'cap' in v['type'])
    print(f"[STEP 3] 'Black X' 노드: {(t_e-t_s)*1000:.2f} ms "
          f"(total {len(interest)}: {n_main_food} food + {n_mouth} mouth + {n_cap} cap)")

    # Step 4: Direct edges (Voronoi on main corridor)
    t_s = time.time()
    edges, owner = step4_direct_edges(interest, main_corridor, walls, W, H)
    t_e = time.time()
    print(f"[STEP 4] 직접 연결된 것만: {(t_e-t_s)*1000:.2f} ms  ({len(edges)} edges)")

    elapsed = time.time() - t0
    print(f"\n==> TOTAL time: {elapsed*1000:.2f} ms")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 150
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} — User's 4-step algorithm",
              fill=(20, 20, 20))
    draw.text((10, 23), f"[1] 포켓: {len(pruned)} cells  "
              f"[2] 포켓 헤더(음식 있는): {len(unique_mouths)}  "
              f"[3] 'X' 노드: {len(interest)}  "
              f"[4] 직접 edges: {len(edges)}",
              fill=(40, 40, 40))
    draw.text((10, 41), f"Total time: {elapsed*1000:.1f} ms",
              fill=(20, 80, 120))
    draw.text((10, 59), f"X = interest node (food/mouth/cap). "
              f"Green line = directly connected (no other X between).",
              fill=(80, 80, 80))

    ORIG_Y = 90
    import colorsys
    sbr_colors = {}
    for i, s in enumerate(blue_subs):
        h = (i * 0.618033988749895) % 1.0
        rr, gg, bb = colorsys.hsv_to_rgb(h, 0.35, 0.92)
        sbr_colors[id(s)] = (int(rr*255), int(gg*255), int(bb*255))
    cell_to_sbr_color = {}
    for s in blue_subs:
        col = sbr_colors[id(s)]
        for c in s['cells']:
            cell_to_sbr_color[c] = col

    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            x0, y0 = c*CELL, ORIG_Y + r*CELL
            x1, y1 = x0+CELL, y0+CELL
            cell = (c, rows - 1 - r)
            if ch == '%':
                draw.rectangle([x0,y0,x1,y1], fill=(40,40,60))
            else:
                if c < mid_col:
                    bg = (250, 240, 240)
                elif cell in cell_to_sbr_color:
                    bg = cell_to_sbr_color[cell]
                elif cell in main_corridor:
                    bg = (235, 245, 255)
                else:
                    bg = (240, 220, 220)
                draw.rectangle([x0,y0,x1,y1], fill=bg)
                if ch == '.':
                    cx, cy = x0+CELL//2, y0+CELL//2
                    rd = CELL//6
                    if cell in interest and interest[cell]['type'] == 'food':
                        color = (230, 180, 30)
                    else:
                        color = (180, 30, 30)
                    draw.ellipse([cx-rd, cy-rd, cx+rd, cy+rd], fill=color)
                elif ch == 'o':
                    cx, cy = x0+CELL//2, y0+CELL//2
                    rd = CELL//2 - 3
                    draw.ellipse([cx-rd, cy-rd, cx+rd, cy+rd],
                                  fill=(255,60,200), outline=(80,10,60), width=2)
                elif ch in '1234':
                    draw.rectangle([x0+3,y0+3,x1-3,y1-3], fill=(100,100,100))
                    draw.text((x0+CELL//4, y0+CELL//8), ch, fill=(255,255,255))

    def px(cell):
        c, y = cell
        r = rows-1-y
        return (c*CELL+CELL//2, ORIG_Y + r*CELL + CELL//2)

    # Draw direct edges (green, thick)
    for (A, B), w in edges.items():
        p1, p2 = px(A), px(B)
        draw.line([p1, p2], fill=(0, 140, 80), width=3)
        mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
        draw.text((mid[0]-3, mid[1]-5), str(w), fill=(0, 80, 40))

    # Draw 'X' marks for interest nodes
    for pos, info in interest.items():
        cx_, cy_ = px(pos)
        sz = 8
        # Black X
        draw.line([(cx_-sz, cy_-sz), (cx_+sz, cy_+sz)], fill=(0, 0, 0), width=3)
        draw.line([(cx_-sz, cy_+sz), (cx_+sz, cy_-sz)], fill=(0, 0, 0), width=3)

        # Label for mouth / cap
        if 'mouth' in info['type']:
            label = ','.join([f"({f},{c})" for (c, f) in info['options']])
            draw.text((cx_-22, cy_+sz+4), label, fill=(10, 80, 120))
        elif info['type'] == 'cap':
            draw.text((cx_+sz+2, cy_-5), 'C', fill=(150, 10, 80))

    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows*CELL)],
               fill=(120, 120, 120), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Simpler algorithm without red triangles.

1. Pockets (leaf pruning)
2. Filter 0-food pockets
3. Black X = pocket headers + main food + caps
4. Edges: connect A-B ONLY IF blocked-BFS(A, B) == plain-BFS(A, B) on main corridor
   (i.e., direct path doesn't need to detour around other X's)
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
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_DISTCHECK.png"


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


def find_pockets(cells, neighbors):
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


def get_pocket_mouths(pruned, parent, main_corridor, food_set):
    """For each pocket (pruned connected component), compute:
    mouth (main corridor attach), food count, max_food_depth."""
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
        if not food_here: continue
        max_fd = 0
        for i, c in enumerate(trace):
            if c in food_set:
                d = len(trace) - i
                if d > max_fd: max_fd = d
        subs.append({
            'attach': attach, 'cells': trace, 'food': food_here,
            'max_food_depth': max_fd, 'visit_cost': 2*max_fd,
            'food_count': len(food_here),
        })
    return subs


def plain_bfs(walls, start, allowed_cells, W, H):
    """Plain BFS from start, confined to allowed_cells."""
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
            n = (nx, ny)
            if n not in allowed_cells: continue
            if n in dists: continue
            dists[n] = d + 1
            q.append(n)
    return dists


def blocked_bfs_with_terminators(walls, start, allowed_cells, terminators, W, H):
    """BFS from start. Stop at cells in terminators (record + don't expand)."""
    term_dists = {}
    visited = {start}
    q = deque([(start, 0)])
    while q:
        p, d = q.popleft()
        if p != start and p in terminators:
            if p not in term_dists or term_dists[p] > d:
                term_dists[p] = d
            continue
        x, y = p
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x+dx, y+dy
            if not (0<=nx<W and 0<=ny<H): continue
            r = H-1-ny
            if walls[r][nx]: continue
            n = (nx, ny)
            if n not in allowed_cells: continue
            if n in visited: continue
            visited.add(n)
            q.append((n, d+1))
    return term_dists


def build_edges_distcheck(interest, main_corridor, walls, W, H):
    """Add edge (A, B) iff blocked_dist(A, B) == plain_dist(A, B)."""
    interest_cells = set(interest.keys())
    edges = {}
    for src in interest_cells:
        if src not in main_corridor: continue
        plain = plain_bfs(walls, src, main_corridor, W, H)
        blocked = blocked_bfs_with_terminators(
            walls, src, main_corridor, interest_cells, W, H)
        for dst in interest_cells:
            if dst == src: continue
            if dst not in blocked: continue
            if dst not in plain: continue
            if blocked[dst] == plain[dst]:
                A, B = tuple(sorted([src, dst]))
                if (A, B) not in edges or edges[(A, B)] > blocked[dst]:
                    edges[(A, B)] = blocked[dst]
    return edges


def main():
    print(f"=== RANDOM{SEED} — User's simpler algorithm (distance-check only) ===\n")
    t0 = time.time()

    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2
    blue_food = [f for f in food_set if f[0] >= mid_col]
    blue_caps = [c for c in cap_set if c[0] >= mid_col]

    cells, neighbors = build_graph(walls, W, H)
    pruned, parent = find_pockets(cells, neighbors)
    main_corridor = cells - pruned

    subs = get_pocket_mouths(pruned, parent, main_corridor, food_set)
    blue_subs = [s for s in subs if s['attach'][0] >= mid_col]

    # X nodes: blue-side mouths + main food + caps
    interest = {}
    mouth_to_opts = {}
    for s in blue_subs:
        mouth_to_opts.setdefault(s['attach'], []).append(
            (s['visit_cost'], s['food_count']))
    for m, opts in mouth_to_opts.items():
        interest[m] = {'type': 'mouth', 'options': opts,
                       'food_total': sum(f for (c,f) in opts)}

    main_blue_food = [f for f in blue_food if f in main_corridor]
    for f in main_blue_food:
        interest[f] = {'type': 'food', 'options': [(0, 1)], 'food_total': 1}
    for c in blue_caps:
        if c in interest:
            interest[c]['type'] = 'cap+' + interest[c]['type']
        else:
            interest[c] = {'type': 'cap', 'options': [(0, 0)], 'food_total': 0}

    print(f"Interest nodes (X): {len(interest)}")
    print(f"  mouths: {sum(1 for v in interest.values() if 'mouth' in v['type'])}")
    print(f"  main food: {sum(1 for v in interest.values() if v['type'] == 'food')}")
    print(f"  caps: {sum(1 for v in interest.values() if 'cap' in v['type'])}")

    # Build edges using distance-check rule
    t_e = time.time()
    edges = build_edges_distcheck(interest, main_corridor, walls, W, H)
    t_e_end = time.time()
    print(f"\nEdge construction: {(t_e_end - t_e)*1000:.2f} ms")
    print(f"Edges (distance-check rule): {len(edges)}")

    # Compare with blocked-BFS-only (without distance-check)
    blocked_only_edges = {}
    for src in interest:
        if src not in main_corridor: continue
        blocked = blocked_bfs_with_terminators(
            walls, src, main_corridor, set(interest.keys()), W, H)
        for dst, d in blocked.items():
            A, B = tuple(sorted([src, dst]))
            if (A, B) not in blocked_only_edges or blocked_only_edges[(A, B)] > d:
                blocked_only_edges[(A, B)] = d
    print(f"Edges (blocked-BFS only, no distance-check): {len(blocked_only_edges)}")
    print(f"Filtered out (were detours): {len(blocked_only_edges) - len(edges)}")

    total = time.time() - t0
    print(f"\n==> TOTAL time: {total*1000:.2f} ms")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 140
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} — Simpler algorithm (no triangles, distance-check)",
              fill=(20, 20, 20))
    draw.text((10, 23), f"X nodes: {len(interest)}  |  "
              f"Edges (distance-check): {len(edges)}  |  "
              f"(vs blocked-only: {len(blocked_only_edges)})",
              fill=(40, 40, 40))
    draw.text((10, 41), f"Rule: edge A-B added ONLY IF blocked-BFS dist == plain BFS dist",
              fill=(100, 40, 40))
    draw.text((10, 59), f"Total time: {total*1000:.1f} ms",
              fill=(20, 80, 120))

    ORIG_Y = 85

    import colorsys
    sbr_colors = {}
    for i, s in enumerate(blue_subs):
        h = (i * 0.618033988749895) % 1.0
        rr, gg, bb = colorsys.hsv_to_rgb(h, 0.4, 0.92)
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
                    color = (180, 30, 30) if cell in pruned else (230, 180, 30)
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

    # Filtered out edges (in red, thin) — show what was removed by distance-check
    removed = set(blocked_only_edges.keys()) - set(edges.keys())
    for (A, B) in removed:
        p1, p2 = px(A), px(B)
        draw.line([p1, p2], fill=(220, 150, 150), width=1)  # light red, thin

    # Kept edges (green, thick)
    for (A, B), w in edges.items():
        p1, p2 = px(A), px(B)
        draw.line([p1, p2], fill=(0, 140, 80), width=3)
        mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
        draw.text((mid[0]-3, mid[1]-5), str(w), fill=(0, 80, 40))

    # X marks
    for pos in interest:
        cx_, cy_ = px(pos)
        sz = 8
        draw.line([(cx_-sz, cy_-sz), (cx_+sz, cy_+sz)], fill=(0, 0, 0), width=3)
        draw.line([(cx_-sz, cy_+sz), (cx_+sz, cy_-sz)], fill=(0, 0, 0), width=3)
        if 'mouth' in interest[pos]['type']:
            label = ','.join([f"({f},{c})" for (c, f) in interest[pos]['options']])
            draw.text((cx_-22, cy_+sz+4), label, fill=(10, 80, 120))
        elif 'cap' in interest[pos]['type']:
            draw.text((cx_+sz+2, cy_-5), 'C', fill=(150, 10, 80))

    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows*CELL)],
               fill=(120, 120, 120), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == '__main__':
    main()

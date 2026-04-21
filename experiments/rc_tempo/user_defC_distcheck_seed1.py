#!/usr/bin/env python3
"""Definition C (linear pockets) + distance-check edges.

1. Pockets (leaf pruning)
2. Linear segments (each segment = linear chain between endpoints)
3. Keep segments with food
4. X = each linear pocket's START (= entry point of that linear pocket)
   - If start is main corridor → X on main corridor
   - If start is internal junction → X at junction
5. + X for main-corridor food + caps
6. Edges: distance-check rule on (main_corridor ∪ internal_junctions)
   - Edge A-B iff blocked_bfs(A, B) == plain_bfs(A, B)
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
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_DEFC.png"


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


def find_linear_segments(pruned, parent, main_corridor, food_set):
    children = {}
    for c, p in parent.items():
        children.setdefault(p, []).append(c)

    def is_junction(cell):
        return cell in children and len(children[cell]) >= 2

    def is_tip(cell):
        return cell in pruned and cell not in children

    def walk(start, first_child):
        path = [start, first_child]
        cur = first_child
        while True:
            if is_tip(cur) or is_junction(cur):
                return path
            if cur not in children:
                return path
            nx = children[cur][0]
            path.append(nx)
            cur = nx

    segments = []

    def dfs(cell):
        if cell not in children: return
        for ch in children[cell]:
            path = walk(cell, ch)
            food_on = [c for c in path if c in food_set]
            max_fd = 0
            for i, c in enumerate(path):
                if c in food_set and i > max_fd:
                    max_fd = i
            end = path[-1]
            segments.append({
                'cells': path, 'start': cell, 'end': end,
                'length': len(path) - 1,
                'food_cells': food_on, 'food_count': len(food_on),
                'start_type': 'main' if cell in main_corridor else 'junction',
                'end_type': 'tip' if is_tip(end) else 'junction',
                'max_food_depth': max_fd,
            })
            if is_junction(end):
                dfs(end)

    for c in children:
        if c in main_corridor:
            dfs(c)

    return segments


def plain_bfs(walls, start, allowed_cells, W, H):
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


def main():
    print(f"=== RANDOM{SEED} — Definition C + distance-check ===\n")
    t0 = time.time()

    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    cells, neighbors = build_graph(walls, W, H)
    pruned, parent = find_pockets(cells, neighbors)
    main_corridor = cells - pruned

    segments = find_linear_segments(pruned, parent, main_corridor, food_set)
    blue_segs = [s for s in segments if (s['start'][0] >= mid_col or s['end'][0] >= mid_col) and s['food_count'] > 0]

    print(f"Blue linear segments with food: {len(blue_segs)}")
    for i, s in enumerate(blue_segs):
        print(f"  SEG{i+1}: start={s['start']} ({s['start_type']})  "
              f"→ end={s['end']} ({s['end_type']})  "
              f"len={s['length']}  food={s['food_count']}")

    # Internal junctions where live segments start
    internal_junctions = set(s['start'] for s in blue_segs if s['start_type'] == 'junction')
    print(f"Internal junctions used: {len(internal_junctions)}")

    # X positions: each linear segment has an X at its START
    # (multiple segments sharing the same start become multiple X options at that cell)
    x_positions = {}
    for s in blue_segs:
        cell = s['start']
        if cell not in x_positions:
            x_positions[cell] = {'type': 'pocket_start', 'options': [], 'food_total': 0,
                                  'start_type': s['start_type']}
        x_positions[cell]['options'].append({
            'food_count': s['food_count'],
            'visit_cost': s['length'] * 2,
            'end': s['end'],
        })
        x_positions[cell]['food_total'] += s['food_count']

    # Add main food + caps
    blue_food = [f for f in food_set if f[0] >= mid_col]
    for f in blue_food:
        if f in main_corridor:
            x_positions[f] = {'type': 'food', 'options': [{'food_count': 1, 'visit_cost': 0, 'end': f}],
                               'food_total': 1, 'start_type': 'main'}
    blue_caps = [c for c in cap_set if c[0] >= mid_col]
    for c in blue_caps:
        if c in x_positions:
            x_positions[c]['type'] = 'cap+' + x_positions[c]['type']
        else:
            x_positions[c] = {'type': 'cap', 'options': [{'food_count': 0, 'visit_cost': 0, 'end': c}],
                               'food_total': 0, 'start_type': 'main'}

    print(f"\nTotal X positions: {len(x_positions)}")
    on_main = sum(1 for v in x_positions.values() if v['start_type'] == 'main')
    on_junction = sum(1 for v in x_positions.values() if v['start_type'] == 'junction')
    print(f"  on main corridor: {on_main}")
    print(f"  on internal junction: {on_junction}")

    # Build edges: allow propagation through ALL non-wall cells
    # (main corridor + all pruned pocket cells — including foodless trunks that
    #  lead to internal junctions with food)
    allowed_cells = cells

    t_e = time.time()
    edges = {}
    x_cells = set(x_positions.keys())
    for src in x_cells:
        plain = plain_bfs(walls, src, allowed_cells, W, H)
        blocked = blocked_bfs_with_terminators(walls, src, allowed_cells, x_cells, W, H)
        for dst in x_cells:
            if dst == src: continue
            if dst not in blocked or dst not in plain: continue
            if blocked[dst] == plain[dst]:
                A, B = tuple(sorted([src, dst]))
                if (A, B) not in edges or edges[(A, B)] > blocked[dst]:
                    edges[(A, B)] = blocked[dst]
    t_e_end = time.time()
    print(f"\nEdge construction (distance-check): {(t_e_end-t_e)*1000:.2f} ms")
    print(f"Total edges: {len(edges)}")

    total = time.time() - t0
    print(f"\n==> TOTAL time: {total*1000:.2f} ms")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 140
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} — Definition C (linear pockets) + distance-check",
              fill=(20, 20, 20))
    draw.text((10, 23), f"X positions: {len(x_positions)} ({on_main} on main + {on_junction} on junction)  |  "
              f"Edges: {len(edges)}",
              fill=(40, 40, 40))
    draw.text((10, 41), f"Each linear segment = 1 pocket with its own X at the START.",
              fill=(80, 80, 80))
    draw.text((10, 59), f"Total time: {total*1000:.1f} ms",
              fill=(20, 80, 120))

    ORIG_Y = 85

    import colorsys
    seg_colors = {}
    for i, s in enumerate(blue_segs):
        h = (i * 0.618033988749895) % 1.0
        rr, gg, bb = colorsys.hsv_to_rgb(h, 0.4, 0.92)
        seg_colors[id(s)] = (int(rr*255), int(gg*255), int(bb*255))
    cell_to_seg = {}
    for s in blue_segs:
        col = seg_colors[id(s)]
        for c in s['cells'][1:]:
            if c in pruned:
                cell_to_seg[c] = col

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
                elif cell in cell_to_seg:
                    bg = cell_to_seg[cell]
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

    # Draw edges (no weight labels)
    for (A, B), w in edges.items():
        p1, p2 = px(A), px(B)
        draw.line([p1, p2], fill=(0, 140, 80), width=3)

    # Draw X marks — all black (no special color for junction)
    for pos, info in x_positions.items():
        cx_, cy_ = px(pos)
        sz = 8
        col = (0, 0, 0)
        draw.line([(cx_-sz, cy_-sz), (cx_+sz, cy_+sz)], fill=col, width=3)
        draw.line([(cx_-sz, cy_+sz), (cx_+sz, cy_-sz)], fill=col, width=3)

        # Label
        if 'pocket_start' in info['type']:
            labels = [f"({o['food_count']},{o['visit_cost']})" for o in info['options']]
            draw.text((cx_-22, cy_+sz+4), ','.join(labels), fill=(10, 80, 120))

    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows*CELL)],
               fill=(120, 120, 120), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == '__main__':
    main()

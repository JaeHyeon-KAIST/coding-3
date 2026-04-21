#!/usr/bin/env python3
"""Step 1: Pocket detection. Step 2: Full pairwise edges between abstract nodes.

Fixes:
- Sub-branch attach ALWAYS on main corridor (trace through internal branching)
- Full pairwise graph between abstract nodes (pocket mouths + main food + caps)
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
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_FULLPAIR.png"


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
    """Iterative leaf pruning."""
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
    return pruned, parent, orig_degree


def decompose_subbranches_fixed(pruned, parent, main_corridor, food_set):
    """Each tip generates a sub-branch that ALWAYS attaches on main corridor.
    Trace from tip through parent chain until reaching main_corridor.
    """
    # A tip in original is a cell with only one neighbor (degree 1 before pruning)
    # But more safely, use: cell in pruned that is not the parent of any other pruned cell
    children = {}
    for c, p in parent.items():
        children.setdefault(p, []).append(c)
    # Tip = pruned cell with no pruned children
    tips = [c for c in pruned if c not in children]

    subbranches = []
    for tip in tips:
        # Trace from tip to first main corridor cell
        trace = [tip]
        cur = tip
        attach = None
        while cur in parent:
            next_cell = parent[cur]
            if next_cell in main_corridor:
                attach = next_cell
                break
            trace.append(next_cell)
            cur = next_cell
        if attach is None:
            continue  # no main corridor reached (shouldn't happen)

        # Compute depths from attach
        # trace[0] = tip, trace[-1] = closest pruned cell to attach
        # Depth of trace[i] from attach = len(trace) - i
        food_in_branch = [c for c in trace if c in food_set]
        if not food_in_branch:
            continue
        # max_food_depth = max depth of any food cell
        max_food_depth = 0
        for i, c in enumerate(trace):
            if c in food_set:
                depth_from_attach = len(trace) - i  # trace[i] is at depth len-i from attach
                if depth_from_attach > max_food_depth:
                    max_food_depth = depth_from_attach
        subbranches.append({
            'tip': tip,
            'attach': attach,
            'cells': list(trace),
            'food': food_in_branch,
            'depth': len(trace),
            'max_food_depth': max_food_depth,
            'visit_cost': 2 * max_food_depth,
            'food_count': len(food_in_branch),
        })
    return subbranches


def bfs_on_corridor(walls, start, main_corridor, W, H):
    dists = {start: 0}
    parent = {start: None}
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
            if n not in main_corridor: continue
            if n in dists: continue
            dists[n] = d + 1
            parent[n] = p
            q.append(n)
    return dists, parent


def reconstruct_path(parents, end):
    if end not in parents: return None
    path = [end]
    cur = end
    while parents[cur] is not None:
        cur = parents[cur]
        path.append(cur)
    path.reverse()
    return path


def main():
    print(f"=== RANDOM{SEED} — Pocket + Full-Pairwise Abstract Graph ===\n")
    t_total = time.time()

    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2
    blue_food = [f for f in food_set if f[0] >= mid_col]
    blue_caps = [c for c in cap_set if c[0] >= mid_col]

    t0 = time.time()
    cells, neighbors = build_graph(walls, W, H)
    t1 = time.time()
    print(f"[1] Build graph:              {(t1-t0)*1000:.2f} ms  ({len(cells)} cells)")

    t0 = time.time()
    pruned, parent, orig_deg = find_pockets(cells, neighbors)
    t1 = time.time()
    main_corridor = cells - pruned
    blue_main = {c for c in main_corridor if c[0] >= mid_col}
    blue_pruned = {c for c in pruned if c[0] >= mid_col}
    print(f"[2] Leaf pruning:             {(t1-t0)*1000:.2f} ms  "
          f"(blue main: {len(blue_main)}  pruned: {len(blue_pruned)})")

    t0 = time.time()
    subbranches = decompose_subbranches_fixed(blue_pruned, parent, main_corridor, food_set)
    t1 = time.time()
    print(f"[3] Sub-branch decomposition: {(t1-t0)*1000:.2f} ms  ({len(subbranches)} with food)")
    for i, s in enumerate(sorted(subbranches, key=lambda x: (x['attach'], -x['food_count']))):
        print(f"    SB{i+1}: attach={s['attach']}  depth={s['depth']}  "
              f"max_food_depth={s['max_food_depth']}  food={s['food_count']}  "
              f"cost={s['visit_cost']}")

    # Main-corridor blue food
    main_blue_food = [f for f in blue_food if f in blue_main]

    # Unique abstract positions
    sbr_attaches = sorted(set(s['attach'] for s in subbranches))
    abstract_positions = list(set(sbr_attaches + main_blue_food + blue_caps))
    print(f"[4] Abstract positions: {len(abstract_positions)} "
          f"({len(sbr_attaches)} pocket mouths + {len(main_blue_food)} main food + {len(blue_caps)} caps)")

    # Group sub-branches by attach point
    attach_to_sbr = {}
    for s in subbranches:
        attach_to_sbr.setdefault(s['attach'], []).append(s)

    # Full pairwise BFS on main corridor
    t0 = time.time()
    pairwise = {}  # (A, B) -> distance
    pairwise_paths = {}
    pairwise_food = {}  # (A, B) -> list of food cells on shortest path (excluding endpoints)
    for src in abstract_positions:
        dists, par = bfs_on_corridor(walls, src, main_corridor, W, H)
        for dst in abstract_positions:
            if dst == src: continue
            if dst not in dists: continue
            pairwise[(src, dst)] = dists[dst]
            path = reconstruct_path(par, dst)
            pairwise_paths[(src, dst)] = path
            # Food on path (main corridor food between src and dst, excluding endpoints)
            food_on_path = [c for c in path[1:-1] if c in food_set]
            pairwise_food[(src, dst)] = food_on_path
    t1 = time.time()
    print(f"[5] Full pairwise BFS:        {(t1-t0)*1000:.2f} ms  ({len(pairwise)} directed pairs)")

    n_pairs = sum(1 for (a, b) in pairwise if a < b)
    print(f"    Undirected pairs: {n_pairs}")

    total = time.time() - t_total
    print(f"\n==> TOTAL time: {total*1000:.2f} ms")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 160
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} — Pocket + Full-pairwise abstract graph",
              fill=(20, 20, 20))
    draw.text((10, 23), f"Abstract nodes: {len(abstract_positions)}  |  "
              f"Full pairwise edges: {n_pairs}  |  Sub-branches: {len(subbranches)}",
              fill=(40, 40, 40))
    draw.text((10, 41), f"Fix: sub-branch ATTACH always on main corridor "
              f"(trace through internal branching points)",
              fill=(120, 40, 40))
    draw.text((10, 59), f"Total time: {total*1000:.1f} ms  (step 1 + step 2)",
              fill=(20, 80, 120))

    ORIG_Y = 100
    import colorsys
    sbr_colors = {}
    for i, s in enumerate(subbranches):
        h = (i * 0.618033988749895) % 1.0
        rr, gg, bb = colorsys.hsv_to_rgb(h, 0.4, 0.9)
        sbr_colors[id(s)] = (int(rr*255), int(gg*255), int(bb*255))
    cell_to_sbr_color = {}
    for s in subbranches:
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
                elif cell in blue_main:
                    bg = (210, 235, 255)
                else:
                    bg = (240, 220, 220)
                draw.rectangle([x0,y0,x1,y1], fill=bg)
                if ch == '.':
                    cx, cy = x0+CELL//2, y0+CELL//2
                    rd = CELL//6
                    color = (230, 180, 30) if cell in main_blue_food else (180, 30, 30)
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

    # Draw FULL pairwise edges (thin, translucent color)
    drawn = set()
    for (A, B), w in pairwise.items():
        key = tuple(sorted([A, B]))
        if key in drawn: continue
        drawn.add(key)
        p1, p2 = px(A), px(B)
        # Color intensity by weight (shorter edges more visible)
        draw.line([p1, p2], fill=(255, 160, 50), width=1)

    # Abstract node markers
    for pos in abstract_positions:
        cx_, cy_ = px(pos)
        rd = CELL // 3
        if pos in sbr_attaches:
            # Pocket mouth: cyan
            draw.ellipse([cx_-rd, cy_-rd, cx_+rd, cy_+rd],
                          outline=(0, 150, 180), width=3)
            labels = [f"({s['food_count']},{s['visit_cost']})" for s in attach_to_sbr[pos]]
            draw.text((cx_-28, cy_+rd+2), ', '.join(labels), fill=(10, 80, 120))
        elif pos in main_blue_food:
            # Main food: small yellow square
            draw.rectangle([cx_-4, cy_-4, cx_+4, cy_+4], outline=(200, 130, 0), width=2)

    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows*CELL)],
               fill=(120, 120, 120), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == '__main__':
    main()

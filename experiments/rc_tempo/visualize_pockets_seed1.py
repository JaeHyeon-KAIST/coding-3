#!/usr/bin/env python3
"""Pocket detection + visualization for RANDOM1.

Algorithm (iterative leaf pruning):
  1. Build graph of non-wall cells. Each cell's degree = # of non-wall neighbors.
  2. Repeatedly prune cells with degree = 1 (dead-end tips).
     When a cell is pruned, decrement its neighbor's degree. If neighbor becomes
     degree 1, add to queue.
  3. After pruning, remaining cells = main corridor (cycles).
     Pruned cells = pocket cells.
  4. Group pocket cells by MOUTH (main-corridor cell where the pocket attaches).
     Trace each pruned cell toward its parent until reaching a non-pruned cell.
  5. For each pocket (mouth, pocket_cells):
     - Food inside = pocket_cells that have food marker
     - Farthest food from mouth (BFS within pocket)
     - Round-trip cost = 2 × that distance

Visualize:
  - Walls: dark
  - Main corridor cells: light blue tint
  - Pocket cells: red tint (per-pocket different shade)
  - Pocket mouths: cyan circle with (food_count, round_trip) label
  - Food: yellow dots
  - Capsules: magenta
  - Agents: gray boxes
"""
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
CELL = 28
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_POCKETS.png"


def parse_layout(maze_str):
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    walls = [[False]*cols for _ in range(rows)]
    food_set = set()
    cap_set = set()
    spawns = {}
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
    neighbors = {}
    for (x, y) in cells:
        nbs = []
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            n = (x+dx, y+dy)
            if n in cells:
                nbs.append(n)
        neighbors[(x, y)] = nbs
    return cells, neighbors


def find_pockets(cells, neighbors):
    """Iterative leaf pruning. Returns (pocket_groups, main_corridor_cells)."""
    degree = {c: len(neighbors[c]) for c in cells}
    pruned = set()
    parent = {}  # pruned_cell → neighbor it was pruned toward
    leaf_q = deque([c for c in cells if degree[c] == 1])

    while leaf_q:
        v = leaf_q.popleft()
        if v in pruned: continue
        if degree[v] != 1: continue
        # find the ONE remaining neighbor (not pruned)
        active_nbs = [n for n in neighbors[v] if n not in pruned]
        if len(active_nbs) != 1: continue
        p = active_nbs[0]
        parent[v] = p
        pruned.add(v)
        degree[p] -= 1
        if degree[p] == 1:
            leaf_q.append(p)

    main_corridor = cells - pruned

    # Group pruned cells by mouth (first main-corridor cell in parent chain)
    cell_to_mouth = {}
    for cell in pruned:
        cur = cell
        while cur in parent and parent[cur] in pruned:
            cur = parent[cur]
        # parent[cur] should be main corridor
        if cur in parent:
            mouth = parent[cur]
            cell_to_mouth[cell] = mouth

    pocket_groups = {}  # mouth → list of pocket cells
    for cell, mouth in cell_to_mouth.items():
        pocket_groups.setdefault(mouth, []).append(cell)

    return pocket_groups, main_corridor


def bfs_subgraph(neighbors, start, allowed_set):
    """BFS distances starting from `start`, restricted to allowed_set ∪ {start}."""
    dists = {start: 0}
    q = deque([start])
    while q:
        p = q.popleft()
        d = dists[p]
        for n in neighbors[p]:
            if n not in allowed_set and n != start: continue
            if n in dists: continue
            dists[n] = d + 1
            q.append(n)
    return dists


def analyze_pockets(pocket_groups, food_set, neighbors):
    """For each pocket compute (food_count, max_food_dist)."""
    results = []
    for mouth, pocket_cells in pocket_groups.items():
        pocket_set = set(pocket_cells) | {mouth}
        food_in_pocket = [c for c in pocket_cells if c in food_set]
        if not food_in_pocket:
            continue
        # BFS from mouth restricted to pocket
        dists = bfs_subgraph(neighbors, mouth, set(pocket_cells))
        max_food_dist = max(dists.get(f, 0) for f in food_in_pocket)
        results.append({
            'mouth': mouth,
            'cells': pocket_cells,
            'food': food_in_pocket,
            'food_count': len(food_in_pocket),
            'max_food_dist': max_food_dist,
            'round_trip': 2 * max_food_dist,
        })
    return results


def main():
    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    print(f"=== RANDOM{SEED} ===")
    print(f"  map size: {W}×{H}")
    print(f"  total food: {len(food_set)}, capsules: {len(cap_set)}")

    # Analyze BOTH sides, but focus on blue side (opp territory we harvest from)
    # Build graph for entire map
    cells, neighbors = build_graph(walls, W, H)
    pocket_groups, main_corridor = find_pockets(cells, neighbors)

    # Separate pockets by side
    blue_pockets_raw = {m: c for m, c in pocket_groups.items() if m[0] >= mid_col}
    red_pockets_raw = {m: c for m, c in pocket_groups.items() if m[0] < mid_col}

    blue_pocket_info = analyze_pockets(blue_pockets_raw, food_set, neighbors)
    red_pocket_info = analyze_pockets(red_pockets_raw, food_set, neighbors)

    blue_side_food = [f for f in food_set if f[0] >= mid_col]
    blue_pocket_cells_all = set()
    for p in blue_pocket_info:
        blue_pocket_cells_all.update(p['cells'])
    blue_pocket_food = set()
    for p in blue_pocket_info:
        blue_pocket_food.update(p['food'])
    blue_main_food = [f for f in blue_side_food if f not in blue_pocket_food]

    print(f"\n=== Blue side (opp territory, we attack) ===")
    print(f"  food on blue side: {len(blue_side_food)}")
    print(f"  food in pockets:   {len(blue_pocket_food)}")
    print(f"  food on main corridor: {len(blue_main_food)}")
    print(f"  # of pockets w/ food: {len(blue_pocket_info)}")
    print()
    for i, p in enumerate(sorted(blue_pocket_info, key=lambda x: (-x['food_count'], x['round_trip']))):
        print(f"  Pocket {i+1}: mouth={p['mouth']}  food={p['food_count']}  "
              f"max_dist={p['max_food_dist']}  round_trip={p['round_trip']}")

    print(f"\n=== Abstracted node count ===")
    print(f"  Original: {len(blue_side_food)} food nodes")
    print(f"  Abstracted: {len(blue_pocket_info)} pocket nodes + "
          f"{len(blue_main_food)} main-corridor food = "
          f"{len(blue_pocket_info) + len(blue_main_food)} total nodes")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 130
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} pocket decomposition  ({W}×{H}, 30 food blue-side)",
              fill=(20, 20, 20))
    draw.text((10, 23), f"Blue pockets: {len(blue_pocket_info)}  |  "
              f"pocket food: {len(blue_pocket_food)}  |  main corridor food: {len(blue_main_food)}",
              fill=(40, 40, 40))
    draw.text((10, 41), f"Abstract nodes: {len(blue_pocket_info) + len(blue_main_food)} "
              f"(vs {len(blue_side_food)} food cells)",
              fill=(40, 120, 40))
    draw.text((10, 59), f"Red = pocket cell  |  Cyan circle = pocket mouth  |  "
              f"Label: (food count, round-trip cost)",
              fill=(80, 80, 80))

    ORIG_Y = 90
    # Color palettes
    pocket_colors = [(255, 200, 200), (255, 180, 180), (255, 160, 160),
                      (255, 210, 180), (255, 200, 160), (255, 190, 140),
                      (240, 200, 220), (255, 220, 180), (255, 170, 180),
                      (240, 180, 180), (255, 190, 190), (250, 170, 160)]
    mouth_to_color = {}
    for i, p in enumerate(blue_pocket_info):
        mouth_to_color[p['mouth']] = pocket_colors[i % len(pocket_colors)]
    cell_to_pocket_color = {}
    for p in blue_pocket_info:
        col = mouth_to_color[p['mouth']]
        for c in p['cells']:
            cell_to_pocket_color[c] = col

    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            x0, y0 = c*CELL, ORIG_Y + r*CELL
            x1, y1 = x0+CELL, y0+CELL
            cell = (c, rows - 1 - r)
            if ch == '%':
                draw.rectangle([x0,y0,x1,y1], fill=(40,40,60))
            else:
                if c < mid_col:
                    # Red side (ours, don't decompose deeply here)
                    bg = (250, 240, 240)
                else:
                    # Blue side - color by pocket
                    if cell in cell_to_pocket_color:
                        bg = cell_to_pocket_color[cell]
                    else:
                        bg = (200, 230, 255)  # main corridor (light blue)
                draw.rectangle([x0,y0,x1,y1], fill=bg)

                if ch == '.':
                    cx, cy = x0+CELL//2, y0+CELL//2
                    rd = CELL//6
                    if cell in blue_pocket_food:
                        color = (200, 30, 30)  # pocket food (deep)
                    else:
                        color = (230, 210, 80)  # main-corridor food (yellow)
                    draw.ellipse([cx-rd, cy-rd, cx+rd, cy+rd], fill=color)
                elif ch == 'o':
                    cx, cy = x0+CELL//2, y0+CELL//2
                    rd = CELL//2 - 3
                    draw.ellipse([cx-rd, cy-rd, cx+rd, cy+rd],
                                  fill=(255,60,200), outline=(80,10,60), width=2)
                elif ch in '1234':
                    draw.rectangle([x0+3,y0+3,x1-3,y1-3], fill=(100,100,100))
                    draw.text((x0+CELL//4, y0+CELL//8), ch, fill=(255,255,255))

    # Draw pocket mouths (cyan circles with labels)
    for p in blue_pocket_info:
        mx, my = p['mouth']
        r_idx = rows - 1 - my
        cx = mx * CELL + CELL // 2
        cy = ORIG_Y + r_idx * CELL + CELL // 2
        rd = CELL // 3
        draw.ellipse([cx-rd, cy-rd, cx+rd, cy+rd],
                      outline=(0, 150, 180), width=3)
        # Label near mouth (on main corridor side)
        label = f"({p['food_count']},{p['round_trip']})"
        draw.text((cx - 14, cy + rd + 2), label, fill=(10, 80, 120))

    # Midline
    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows*CELL)],
               fill=(120, 120, 120), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == '__main__':
    main()

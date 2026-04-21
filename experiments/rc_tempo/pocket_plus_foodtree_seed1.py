#!/usr/bin/env python3
"""Combined: proper pocket decomposition (sub-branch split) + food-tree.

Step 1: Iterative leaf pruning → identify main corridor vs pockets
Step 2: Within each pocket, identify sub-branches (each linear tip path = 1 node)
Step 3: Abstract nodes = sub-branch mouths + main-corridor food + caps
Step 4: Multi-source BFS on MAIN CORRIDOR only → Voronoi sparse edges between abstract nodes
Step 5: Visualize

Measure time at each step.
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
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_POCKET_PLUS_TREE.png"


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
    """Iterative leaf pruning. Returns (pruned_set, parent_map, orig_degrees)."""
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


def decompose_into_subbranches(pruned, parent, orig_degree, neighbors, food_set, main_corridor):
    """Each sub-branch = linear chain from a dead-end tip to the first cell with orig_degree ≥ 3
    (either another branching cell within pocket or a main-corridor attach point).

    Returns list of sub-branches: each = {
      'tip': position of tip,
      'attach': cell where sub-branch attaches (main corridor or internal branch point),
      'cells': list of cells in sub-branch (tip to just before attach),
      'food': list of food cells in sub-branch,
      'depth': depth from attach to tip,
      'max_food_depth': depth from attach to farthest food,
      'visit_cost': 2 * max_food_depth,
      'food_count': len(food),
    }
    """
    # Tips = cells in pruned with orig_degree == 1
    tips = [c for c in pruned if orig_degree[c] == 1]
    subbranches = []

    for tip in tips:
        # Trace back from tip along pruned cells with orig_degree ≤ 2 until hitting
        # orig_degree ≥ 3 or main corridor.
        trace = [tip]
        cur = tip
        while True:
            # Move toward parent (in pruning chain)
            if cur not in parent:
                break  # reached root of pruning (shouldn't happen for tip)
            next_cell = parent[cur]
            # Is next_cell the attach point?
            # Attach condition: next_cell is on main corridor OR has orig_degree ≥ 3
            if next_cell in main_corridor or orig_degree[next_cell] >= 3:
                # Sub-branch attaches here
                depth = len(trace)  # depth from attach to tip = # cells we traversed
                food_in_branch = [c for c in trace if c in food_set]
                if not food_in_branch:
                    max_food_depth = 0
                else:
                    # max_food_depth = position of farthest food from attach
                    # trace[0] = tip (farthest from attach), trace[-1] = adjacent to attach
                    # depth of trace[i] from attach = depth - i
                    # farthest food = min i where trace[i] in food_set
                    for i, c in enumerate(trace):
                        if c in food_set:
                            # c is at depth (depth - i) from attach (trace[0]=tip at depth `depth`)
                            break
                    max_food_depth = depth - i
                subbranches.append({
                    'tip': tip,
                    'attach': next_cell,
                    'cells': list(trace),
                    'food': food_in_branch,
                    'depth': depth,
                    'max_food_depth': max_food_depth,
                    'visit_cost': 2 * max_food_depth,
                    'food_count': len(food_in_branch),
                })
                break
            else:
                trace.append(next_cell)
                cur = next_cell

    return subbranches


def multi_source_bfs_on_corridor(walls, sources, main_corridor, W, H):
    """Multi-source BFS restricted to main_corridor cells (pockets excluded).
    Sources must be ON or ADJACENT to main_corridor.
    """
    owner = {}
    dist = {}
    q = deque()
    for s in sources:
        if s in main_corridor:
            owner[s] = s
            dist[s] = 0
            q.append(s)
    while q:
        p = q.popleft()
        x, y = p
        d = dist[p]
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x+dx, y+dy
            if not (0<=nx<W and 0<=ny<H): continue
            r = H-1-ny
            if walls[r][nx]: continue
            n = (nx, ny)
            if n not in main_corridor: continue
            if n in owner: continue
            owner[n] = owner[p]
            dist[n] = d + 1
            q.append(n)
    return owner, dist


def build_sparse_graph(owner, dist):
    """Scan for Voronoi boundaries → edges."""
    edges = {}
    for (x, y), ow in owner.items():
        for dx, dy in [(1,0),(0,1)]:
            n = (x+dx, y+dy)
            if n not in owner: continue
            if owner[n] == ow: continue
            A, B = tuple(sorted([ow, owner[n]]))
            w = dist[(x, y)] + 1 + dist[n]
            if (A, B) not in edges or edges[(A, B)] > w:
                edges[(A, B)] = w
    return edges


def main():
    print(f"=== RANDOM{SEED} — Pocket + Food-Tree combined ===\n")
    t_total_start = time.time()

    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2
    blue_food = [f for f in food_set if f[0] >= mid_col]
    blue_caps = [c for c in cap_set if c[0] >= mid_col]

    t0 = time.time()
    cells, neighbors = build_graph(walls, W, H)
    t1 = time.time()
    print(f"[1] Build cell graph:          {(t1-t0)*1000:.2f} ms   ({len(cells)} cells)")

    t0 = time.time()
    pruned, parent, orig_degree = find_pockets(cells, neighbors)
    t1 = time.time()
    main_corridor = cells - pruned
    print(f"[2] Leaf pruning (pockets):    {(t1-t0)*1000:.2f} ms   "
          f"(main: {len(main_corridor)}  pocket: {len(pruned)})")

    # Keep only blue-side pockets
    blue_pruned = {c for c in pruned if c[0] >= mid_col}
    blue_main = {c for c in main_corridor if c[0] >= mid_col}
    print(f"    blue-side main: {len(blue_main)}  pocket cells: {len(blue_pruned)}")

    t0 = time.time()
    subbranches = decompose_into_subbranches(
        blue_pruned, parent, orig_degree, neighbors, food_set, main_corridor)
    t1 = time.time()
    print(f"[3] Decompose sub-branches:    {(t1-t0)*1000:.2f} ms   "
          f"({len(subbranches)} sub-branches)")

    # Filter sub-branches that have food (skip empty ones)
    sbr_with_food = [s for s in subbranches if s['food_count'] > 0]
    print(f"    sub-branches with food: {len(sbr_with_food)}")
    for i, s in enumerate(sorted(sbr_with_food, key=lambda x: (x['attach'], -x['food_count']))):
        print(f"      SB{i+1}: attach={s['attach']}  depth={s['depth']}  "
              f"max_food_depth={s['max_food_depth']}  food={s['food_count']}  "
              f"visit_cost={s['visit_cost']}")

    # Main-corridor food (blue side only)
    main_blue_food = [f for f in blue_food if f in blue_main]
    print(f"    main-corridor food (blue side): {len(main_blue_food)}")

    # Abstract nodes
    # Each sub-branch has an ATTACH point. Multiple sub-branches can attach at same cell.
    # We treat them as SEPARATE nodes (same position, different visit options).
    # For graph purposes, collapse to unique attach points for BFS, but keep sub-branch choice separate.
    abstract_sources = list(set(
        [s['attach'] for s in sbr_with_food] + main_blue_food + blue_caps
    ))
    print(f"[4] Abstract node positions: {len(abstract_sources)}")

    t0 = time.time()
    owner, dist = multi_source_bfs_on_corridor(
        walls, abstract_sources, main_corridor, W, H)
    t1 = time.time()
    print(f"[5] Multi-source BFS on main corridor: {(t1-t0)*1000:.2f} ms")

    t0 = time.time()
    sparse_edges = build_sparse_graph(owner, dist)
    t1 = time.time()
    print(f"[6] Sparse edge construction:  {(t1-t0)*1000:.2f} ms   ({len(sparse_edges)} edges)")

    t_total = time.time() - t_total_start
    print(f"\n==> TOTAL time: {t_total*1000:.2f} ms")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 160
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} — Pocket + Food-Tree combined",
              fill=(20, 20, 20))
    draw.text((10, 23), f"Abstract nodes: {len(abstract_sources)} ("
              f"{len(set(s['attach'] for s in sbr_with_food))} pocket mouths + "
              f"{len(main_blue_food)} main food + {len(blue_caps)} caps)",
              fill=(40, 40, 40))
    draw.text((10, 41), f"Sparse edges on main corridor: {len(sparse_edges)}",
              fill=(40, 120, 40))
    draw.text((10, 59), f"Sub-branches with food: {len(sbr_with_food)} "
              f"(original 30 food → {len(sbr_with_food)} pocket-visits + "
              f"{len(main_blue_food)} main food)",
              fill=(100, 50, 50))
    draw.text((10, 77), f"Total decomposition time: {t_total*1000:.1f} ms",
              fill=(20, 80, 120))

    ORIG_Y = 100
    import colorsys
    sbr_colors = {}
    for i, s in enumerate(sbr_with_food):
        h = (i * 0.618033988749895) % 1.0
        rr, gg, bb = colorsys.hsv_to_rgb(h, 0.4, 0.9)
        sbr_colors[id(s)] = (int(rr*255), int(gg*255), int(bb*255))

    cell_to_sbr_color = {}
    for s in sbr_with_food:
        col = sbr_colors[id(s)]
        for c in s['cells']:
            cell_to_sbr_color[c] = col

    # Main corridor color
    main_color = (210, 235, 255)

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
                    bg = main_color
                else:
                    bg = (240, 220, 220)  # unassigned (foodless pocket)
                draw.rectangle([x0,y0,x1,y1], fill=bg)
                if ch == '.':
                    cx, cy = x0+CELL//2, y0+CELL//2
                    rd = CELL//6
                    if cell in main_blue_food:
                        color = (230, 180, 30)  # main-corridor: yellow-ish
                    else:
                        color = (180, 30, 30)  # pocket: red
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

    # Draw sparse edges
    for (A, B), w in sparse_edges.items():
        p1, p2 = px(A), px(B)
        draw.line([p1, p2], fill=(255, 140, 0), width=2)
        mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
        draw.text((mid[0]-5, mid[1]-5), str(w), fill=(150, 60, 0))

    # Draw sub-branch attach points with labels
    attach_counts = {}
    for s in sbr_with_food:
        a = s['attach']
        attach_counts.setdefault(a, []).append(s)
    for attach_pt, sbr_list in attach_counts.items():
        cx_, cy_ = px(attach_pt)
        rd = CELL // 3
        draw.ellipse([cx_-rd, cy_-rd, cx_+rd, cy_+rd],
                      outline=(0, 150, 180), width=3)
        label = ', '.join([f"({s['food_count']},{s['visit_cost']})" for s in sbr_list])
        draw.text((cx_-28, cy_+rd+2), label, fill=(10, 80, 120))

    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows*CELL)],
               fill=(120, 120, 120), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == '__main__':
    main()

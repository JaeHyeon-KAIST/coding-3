#!/usr/bin/env python3
"""Junction-skeleton abstract graph for RANDOM1.

Nodes = main corridor cells with ≥3 main-corridor neighbors (junctions) +
        map-boundary terminal cells (if needed) +
        sub-branch attach points (pocket mouths) +
        caps.
Edges = main-corridor paths between ADJACENT junctions (or between junction and
        non-junction node embedded in the corridor). No skipping.

Visualization: black X at junctions, green edges between them, markers on edges.
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
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_SKELETON.png"


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
    return pruned, parent, orig_degree


def decompose_subbranches(pruned, parent, main_corridor, food_set):
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
        subs.append({'tip': tip, 'attach': attach, 'cells': trace,
                     'food': food_here, 'depth': len(trace),
                     'max_food_depth': max_fd, 'visit_cost': 2*max_fd,
                     'food_count': len(food_here)})
    return subs


def find_junctions(main_corridor, neighbors):
    """Junctions = main-corridor cells with ≥3 main-corridor neighbors."""
    junctions = set()
    for c in main_corridor:
        main_nbs = [n for n in neighbors[c] if n in main_corridor]
        if len(main_nbs) >= 3:
            junctions.add(c)
    return junctions


def walk_segments(junctions, main_corridor, neighbors, interest_nodes):
    """Walk main-corridor segments between junctions.
    Returns list of segments, each = ordered list of (cell, node_type_or_None).
    node_type: 'junction', 'mouth', 'food', 'cap', or None.
    Also returns edges between adjacent nodes on each segment.
    """
    # A segment is bounded by junctions on both ends.
    # Start from each junction, explore each direction.
    segments = []
    visited_edges = set()  # to avoid duplicate segment walks

    for start_j in junctions:
        for nb in neighbors[start_j]:
            if nb not in main_corridor: continue
            edge_key = tuple(sorted([start_j, nb]))
            if edge_key in visited_edges: continue

            # Walk in this direction until hitting another junction
            segment = [start_j]
            prev = start_j
            cur = nb
            while True:
                segment.append(cur)
                visited_edges.add(tuple(sorted([prev, cur])))
                if cur in junctions:
                    break
                # cur has degree 2 in main corridor, go to the non-prev neighbor
                main_nbs = [n for n in neighbors[cur] if n in main_corridor]
                next_cells = [n for n in main_nbs if n != prev]
                if not next_cells:
                    # Dead-end of main corridor (shouldn't happen normally)
                    break
                prev, cur = cur, next_cells[0]
            segments.append(segment)

    # Now, for each segment, annotate which cells are nodes of interest
    segment_info = []
    for seg in segments:
        nodes_on_seg = []
        for cell in seg:
            types = []
            if cell in junctions: types.append('junction')
            if cell in interest_nodes: types.append(interest_nodes[cell])
            if types:
                nodes_on_seg.append((cell, types))
        segment_info.append({'cells': seg, 'length': len(seg) - 1, 'nodes': nodes_on_seg})

    return segment_info


def main():
    print(f"=== RANDOM{SEED} — Junction skeleton graph ===\n")
    t0 = time.time()

    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2
    blue_food = [f for f in food_set if f[0] >= mid_col]
    blue_caps = [c for c in cap_set if c[0] >= mid_col]

    cells, neighbors = build_graph(walls, W, H)
    pruned, parent, _ = find_pockets(cells, neighbors)
    main_corridor = cells - pruned

    # Blue-side analysis
    subs = decompose_subbranches(pruned, parent, main_corridor, food_set)
    blue_subs = [s for s in subs if s['attach'][0] >= mid_col]
    blue_main = {c for c in main_corridor if c[0] >= mid_col}
    main_blue_food = [f for f in blue_food if f in blue_main]

    # Blue junctions
    blue_junctions = find_junctions(blue_main, {c: [n for n in neighbors[c] if n in blue_main]
                                                  for c in blue_main})
    print(f"Blue main corridor: {len(blue_main)} cells  |  junctions: {len(blue_junctions)}")
    print(f"Main food: {len(main_blue_food)}  |  caps: {len(blue_caps)}  |  sub-branches: {len(blue_subs)}")

    # Build blue_neighbors
    blue_neighbors = {c: [n for n in neighbors[c] if n in blue_main] for c in blue_main}

    # Interest nodes
    interest_nodes = {}  # cell → type
    for m in set(s['attach'] for s in blue_subs):
        interest_nodes[m] = 'mouth'
    for f in main_blue_food:
        interest_nodes[f] = 'food'
    for c in blue_caps:
        interest_nodes[c] = 'cap'

    segments = walk_segments(blue_junctions, blue_main, blue_neighbors, interest_nodes)
    print(f"\nSegments: {len(segments)}")

    # Edges: between adjacent nodes on each segment
    edges = []  # list of (node_a, node_b, weight, cells_in_between)
    for seg in segments:
        nodes = seg['nodes']  # [(cell, types)] ordered along segment
        for i in range(len(nodes)-1):
            a_cell, a_types = nodes[i]
            b_cell, b_types = nodes[i+1]
            # Weight = # of cells between them in segment (= distance)
            idx_a = seg['cells'].index(a_cell)
            idx_b = seg['cells'].index(b_cell)
            w = abs(idx_b - idx_a)
            edges.append((a_cell, b_cell, w))

    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed*1000:.2f} ms")
    print(f"Skeleton edges: {len(edges)}")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 140
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} — Junction-skeleton graph",
              fill=(20, 20, 20))
    draw.text((10, 23), f"Junctions: {len(blue_junctions)}  |  Interest nodes: {len(interest_nodes)}",
              fill=(40, 40, 40))
    draw.text((10, 41), f"Skeleton edges (only between adjacent nodes): {len(edges)}  "
              f"(vs 190 full pairwise)",
              fill=(40, 120, 40))
    draw.text((10, 59), f"Build time: {elapsed*1000:.1f} ms",
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
                elif cell in blue_main:
                    bg = (235, 245, 255)
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

    # Draw skeleton edges (green, thick)
    for (a, b, w) in edges:
        p1, p2 = px(a), px(b)
        draw.line([p1, p2], fill=(0, 140, 80), width=3)
        mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
        draw.text((mid[0]-3, mid[1]-5), str(w), fill=(0, 80, 40))

    # Junctions as black X
    for j in blue_junctions:
        cx_, cy_ = px(j)
        sz = 6
        draw.line([(cx_-sz, cy_-sz), (cx_+sz, cy_+sz)], fill=(0, 0, 0), width=3)
        draw.line([(cx_-sz, cy_+sz), (cx_+sz, cy_-sz)], fill=(0, 0, 0), width=3)

    # Mouths: cyan circles with labels
    attach_to_sbr = {}
    for s in blue_subs:
        attach_to_sbr.setdefault(s['attach'], []).append(s)
    for m, sbs in attach_to_sbr.items():
        cx_, cy_ = px(m)
        rd = CELL // 4
        draw.ellipse([cx_-rd, cy_-rd, cx_+rd, cy_+rd],
                      outline=(0, 150, 180), width=3)
        label = ','.join([f"({s['food_count']},{s['visit_cost']})" for s in sbs])
        draw.text((cx_-22, cy_+rd+2), label, fill=(10, 80, 120))

    # Main food: yellow squares
    for f in main_blue_food:
        cx_, cy_ = px(f)
        draw.rectangle([cx_-4, cy_-4, cx_+4, cy_+4], outline=(200, 130, 0), width=2)

    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows*CELL)],
               fill=(120, 120, 120), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == '__main__':
    main()

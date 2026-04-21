#!/usr/bin/env python3
"""Definition C: Pocket = linear segment (단방향, 분기 없음).

Algorithm:
  1. Leaf pruning identifies pocket cells
  2. Build pocket tree using parent map (from pruning)
  3. Find LINEAR SEGMENTS: maximal chains where interior cells have exactly 1 child (degree-2 in tree)
     - Segment endpoints: main-corridor-adjacent cell, junction (≥2 children), or tip (leaf)
  4. Each linear segment with food = 1 pocket

Visualize: each linear segment in a distinct color with its own mouth.
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
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_LINEAR.png"


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


def find_linear_segments(pruned, parent, main_corridor, food_set):
    """Find linear segments (each = chain of cells with no internal branching).

    Build tree from parent map (pruned cell → parent).
    Children: reverse of parent map.
    Segment: walk from start through degree-2 cells until reaching a junction or tip.

    Returns list of segments, each = {
      'cells': ordered list [start, ..., end],
      'start': endpoint closer to main corridor (or internal junction),
      'end': other endpoint (tip or internal junction),
      'length': len(cells) - 1,
      'food_cells': list of food on segment,
      'food_count': len(food_cells),
      'end_type': 'tip' | 'junction',
      'start_type': 'main' | 'junction',
      'max_food_depth_from_start': max distance from start to any food on segment,
    }
    """
    children = {}
    for c, p in parent.items():
        children.setdefault(p, []).append(c)

    def is_junction(cell):
        return cell in children and len(children[cell]) >= 2

    def is_tip(cell):
        return cell in pruned and cell not in children

    def walk(start, next_cell):
        """Walk: start → next_cell → ... stop at tip or junction."""
        path = [start, next_cell]
        prev, cur = start, next_cell
        while True:
            if is_tip(cur) or is_junction(cur):
                return path
            if cur not in children:
                return path  # shouldn't happen but safe
            # Single child — continue
            next_c = children[cur][0]
            path.append(next_c)
            prev, cur = cur, next_c

    segments = []

    def dfs_segment(start):
        """From start, emit segment for each child, recurse at junctions."""
        if start not in children: return
        for child in children[start]:
            path = walk(start, child)
            end = path[-1]
            food_on = [c for c in path if c in food_set]
            # Compute max_food_depth from start
            max_fd = 0
            for i, c in enumerate(path):
                if c in food_set:
                    if i > max_fd: max_fd = i
            segments.append({
                'cells': path,
                'start': start,
                'end': end,
                'length': len(path) - 1,
                'food_cells': food_on,
                'food_count': len(food_on),
                'start_type': 'main' if start in main_corridor else 'junction',
                'end_type': 'tip' if is_tip(end) else ('junction' if is_junction(end) else 'unknown'),
                'max_food_depth': max_fd,
            })
            if is_junction(end):
                dfs_segment(end)

    # Start from each main-corridor cell that has pruned children
    for c in children:
        if c in main_corridor:
            dfs_segment(c)

    return segments


def main():
    print(f"=== RANDOM{SEED} — Definition C: Linear pockets ===\n")
    t0 = time.time()

    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    cells, neighbors = build_graph(walls, W, H)
    pruned, parent, orig_deg = find_pockets(cells, neighbors)
    main_corridor = cells - pruned

    t_seg = time.time()
    segments = find_linear_segments(pruned, parent, main_corridor, food_set)
    t_seg_end = time.time()

    # Filter blue-side segments
    blue_segments = [s for s in segments if s['start'][0] >= mid_col or s['end'][0] >= mid_col]
    # Filter segments with food
    segs_with_food = [s for s in blue_segments if s['food_count'] > 0]

    print(f"Total pocket cells (both sides): {len(pruned)}")
    print(f"Total linear segments (both sides): {len(segments)}")
    print(f"Blue-side segments: {len(blue_segments)}")
    print(f"Blue-side segments WITH FOOD: {len(segs_with_food)}")
    print(f"\nLinear segment decomposition time: {(t_seg_end - t_seg)*1000:.2f} ms\n")

    for i, s in enumerate(sorted(segs_with_food, key=lambda x: (x['start'], -x['food_count']))):
        print(f"  SEG{i+1}: start={s['start']} ({s['start_type']})  "
              f"end={s['end']} ({s['end_type']})  "
              f"length={s['length']}  food={s['food_count']}  "
              f"max_food_depth={s['max_food_depth']}")

    total = time.time() - t0
    print(f"\n==> TOTAL time: {total*1000:.2f} ms")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 140
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} — Definition C: Linear pockets",
              fill=(20, 20, 20))
    draw.text((10, 23), f"Segments (blue, all): {len(blue_segments)}  |  "
              f"with food: {len(segs_with_food)}",
              fill=(40, 40, 40))
    draw.text((10, 41), f"Each segment = 1 linear pocket. "
              f"Start=main (light blue) or junction (in-pocket red).",
              fill=(80, 80, 80))
    draw.text((10, 59), f"Total time: {total*1000:.1f} ms",
              fill=(20, 80, 120))
    draw.text((10, 77), f"Colors distinguish different linear segments. "
              f"Blue dot = segment start, red triangle = segment end.",
              fill=(100, 100, 100))

    ORIG_Y = 100

    import colorsys
    seg_colors = {}
    for i, s in enumerate(blue_segments):
        h = (i * 0.618033988749895) % 1.0
        rr, gg, bb = colorsys.hsv_to_rgb(h, 0.5, 0.9)
        seg_colors[id(s)] = (int(rr*255), int(gg*255), int(bb*255))

    cell_to_seg = {}
    for s in blue_segments:
        col = seg_colors[id(s)]
        # Color interior cells (skip endpoints, which are shared)
        for c in s['cells'][1:]:  # skip start (endpoint shared)
            if c in pruned:
                cell_to_seg[c] = col

    # Identify junction cells
    children = {}
    for c, p in parent.items():
        children.setdefault(p, []).append(c)
    junction_cells = {c for c in children if len(children[c]) >= 2 and c in pruned}

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
                elif cell in junction_cells:
                    bg = (255, 210, 210)  # junction: light red
                elif cell in main_corridor:
                    bg = (230, 240, 255)
                else:
                    bg = (240, 220, 220)  # foodless pocket
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

    # Draw segment markers
    for s in segs_with_food:
        sp = px(s['start'])
        ep = px(s['end'])
        # Start: blue circle if main, purple if junction
        col_start = (0, 100, 200) if s['start_type'] == 'main' else (150, 50, 150)
        rd = 6
        draw.ellipse([sp[0]-rd, sp[1]-rd, sp[0]+rd, sp[1]+rd],
                      outline=col_start, width=3)
        # End: red triangle if tip, purple circle if junction
        if s['end_type'] == 'tip':
            sz = 6
            draw.polygon([(ep[0]-sz, ep[1]+sz), (ep[0]+sz, ep[1]+sz), (ep[0], ep[1]-sz)],
                          outline=(200, 0, 0), width=2)
        else:
            draw.ellipse([ep[0]-rd, ep[1]-rd, ep[0]+rd, ep[1]+rd],
                          outline=(150, 50, 150), width=3)
        # Label at midpoint: (food, length)
        mid = ((sp[0]+ep[0])//2, (sp[1]+ep[1])//2)
        label = f"({s['food_count']},{s['length']})"
        draw.text((mid[0]-10, mid[1]-5), label, fill=(30, 30, 30))

    # Midline
    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows*CELL)],
               fill=(120, 120, 120), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Final model.

Nodes:
  - X = main corridor cells with food OR cap OR pocket attach (with food pocket)
  - Pocket header = entry into a pocket (ONE per tip). Attached to the X at its attach point.

Rules:
  - A single X can have 0+ pocket headers
  - Edges: X-X only, via distance-check (blocked-BFS == plain-BFS on main corridor)
  - Pocket header connects only to the X at its position (NOT to other pocket headers)

Visualization:
  - X = black X mark
  - Pocket header = RED ARROW from X pointing into the pocket
  - Number at arrowhead = (food_count, visit_cost)
"""
from __future__ import annotations
import os
import sys
import random
import time
import math
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
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_FINAL.png"


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


def get_pocket_headers(pruned, parent, main_corridor, food_set):
    """For each TIP, compute a pocket header: {attach, first_cell, path, food, cost}.
    Path from attach to tip. food_count = food on path. visit_cost = 2*(max_food_depth)."""
    children = {}
    for c, p in parent.items():
        children.setdefault(p, []).append(c)
    tips = [c for c in pruned if c not in children]

    headers = []
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
        food_on = [c for c in trace if c in food_set]
        if not food_on: continue
        # trace is [tip, ..., cell adjacent to attach]
        # depth of tip from attach = len(trace)
        # max_food_depth = max depth of any food cell = len(trace) - min_i_with_food
        max_fd = 0
        for i, c in enumerate(trace):
            if c in food_set:
                d = len(trace) - i
                if d > max_fd: max_fd = d
        # First cell = cell in pocket adjacent to attach = trace[-1]
        first_cell = trace[-1]
        # Direction from attach (X) to first_cell = (dx, dy)
        direction = (first_cell[0] - attach[0], first_cell[1] - attach[1])
        headers.append({
            'attach': attach, 'first_cell': first_cell, 'tip': tip,
            'path': trace, 'food': food_on, 'food_count': len(food_on),
            'max_food_depth': max_fd, 'visit_cost': 2 * max_fd,
            'direction': direction,
        })
    return headers


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
    print(f"=== RANDOM{SEED} — Final model (X + pocket header arrows) ===\n")
    t0 = time.time()

    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    cells, neighbors = build_graph(walls, W, H)
    pruned, parent = find_pockets(cells, neighbors)
    main_corridor = cells - pruned

    headers_all = get_pocket_headers(pruned, parent, main_corridor, food_set)
    blue_headers_raw = [h for h in headers_all if h['attach'][0] >= mid_col]

    # === MERGE: headers sharing (attach, first_cell) share a trunk ===
    # Group by (attach, first_cell)
    groups = {}
    for h in blue_headers_raw:
        key = (h['attach'], h['first_cell'])
        groups.setdefault(key, []).append(h)

    blue_headers = []
    for key, group in groups.items():
        if len(group) == 1:
            blue_headers.append(group[0])
            continue
        # Find junction depth via common prefix of reversed paths
        # path = [tip, ..., first_cell]. Reverse to [first_cell, ..., tip]
        rev_paths = [list(reversed(h['path'])) for h in group]
        i = 0
        while True:
            if i >= min(len(p) for p in rev_paths): break
            ref = rev_paths[0][i]
            if not all(p[i] == ref for p in rev_paths): break
            i += 1
        # Common prefix length = i. Last common cell = rev_paths[0][i-1]
        # Trunk depth from attach to junction = i (i cells in trunk from first_cell to junction inclusive)
        # Wait: depth of first_cell from attach = 1, depth of common cell at index j is j+1 from attach
        # Junction = rev_paths[0][i-1], its depth from attach = i
        junction_depth = i  # = i cells of trunk (from attach to junction)
        # Each header's branch depth from junction = max_food_depth - junction_depth
        combined_food = 0
        combined_branch_cost = 0
        for h in group:
            # Only count if food cells exist beyond junction
            # For simplicity, branch depth = max_food_depth - junction_depth
            branch_depth = max(h['max_food_depth'] - junction_depth, 0)
            combined_branch_cost += 2 * branch_depth
            combined_food += h['food_count']
        combined_cost = 2 * junction_depth + combined_branch_cost
        # Create merged header (same direction since all share first_cell)
        direction = (key[1][0] - key[0][0], key[1][1] - key[0][1])
        merged = {
            'attach': key[0], 'first_cell': key[1],
            'tip': None,  # multiple tips
            'path': [], 'food': [],
            'food_count': combined_food,
            'max_food_depth': max(h['max_food_depth'] for h in group),
            'visit_cost': combined_cost,
            'direction': direction,
            'merged_from': [h['tip'] for h in group],
        }
        blue_headers.append(merged)

    print(f"Pocket headers (blue side, with food): {len(blue_headers)}")
    dir_name = {(0,1):'N', (0,-1):'S', (1,0):'E', (-1,0):'W'}
    for i, h in enumerate(sorted(blue_headers, key=lambda x: (x['attach'], -x['food_count']))):
        d = h['direction']
        dn = dir_name.get(d, str(d))
        mark = ' [MERGED]' if h.get('merged_from') else ''
        print(f"  H{i+1}: X={h['attach']}  food={h['food_count']:2}  cost={h['visit_cost']:2}  "
              f"dir={d} ({dn}){mark}")

    # X positions
    blue_food = [f for f in food_set if f[0] >= mid_col]
    blue_caps = [c for c in cap_set if c[0] >= mid_col]
    x_positions = set()
    for h in blue_headers:
        x_positions.add(h['attach'])
    for f in blue_food:
        if f in main_corridor:
            x_positions.add(f)
    for c in blue_caps:
        x_positions.add(c)

    print(f"\nX positions: {len(x_positions)}")

    # Group headers by attach (same X can have multiple headers)
    x_headers = {}
    for h in blue_headers:
        x_headers.setdefault(h['attach'], []).append(h)

    # Edges: X-X via distance-check on main corridor only
    t_e = time.time()
    edges = {}
    for src in x_positions:
        plain = plain_bfs(walls, src, main_corridor, W, H)
        blocked = blocked_bfs_with_terminators(walls, src, main_corridor, x_positions, W, H)
        for dst in x_positions:
            if dst == src: continue
            if dst not in blocked or dst not in plain: continue
            if blocked[dst] == plain[dst]:
                A, B = tuple(sorted([src, dst]))
                if (A, B) not in edges or edges[(A, B)] > blocked[dst]:
                    edges[(A, B)] = blocked[dst]
    t_e_end = time.time()
    print(f"Edge construction: {(t_e_end - t_e)*1000:.2f} ms")
    print(f"Edges: {len(edges)}")

    total = time.time() - t0
    print(f"\n==> TOTAL: {total*1000:.2f} ms")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 120
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} — X + pocket header model",
              fill=(20, 20, 20))
    draw.text((10, 23), f"X positions: {len(x_positions)}  |  "
              f"Pocket headers: {len(blue_headers)}  |  Edges: {len(edges)}",
              fill=(40, 40, 40))
    draw.text((10, 41), f"Red arrow = pocket header (from X into pocket). "
              f"Number at arrowhead = (food, cost).",
              fill=(80, 80, 80))
    draw.text((10, 59), f"Total time: {total*1000:.1f} ms",
              fill=(20, 80, 120))

    ORIG_Y = 85

    import colorsys
    # Color pocket cells lightly to show pockets
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
                elif cell in pruned:
                    bg = (255, 225, 225)  # light red for pocket cells
                else:
                    bg = (235, 245, 255)
                draw.rectangle([x0,y0,x1,y1], fill=bg)
                if ch == '.':
                    cx, cy = x0+CELL//2, y0+CELL//2
                    rd = CELL//6
                    draw.ellipse([cx-rd, cy-rd, cx+rd, cy+rd], fill=(180, 30, 30))
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

    # Draw edges (green, no labels)
    for (A, B), w in edges.items():
        p1, p2 = px(A), px(B)
        draw.line([p1, p2], fill=(0, 140, 80), width=3)

    # Draw pocket header arrows (red, from X to first_cell)
    def draw_arrow(draw, start_px, end_px, color=(200, 20, 20), width=3, head_size=8):
        draw.line([start_px, end_px], fill=color, width=width)
        dx = end_px[0] - start_px[0]
        dy = end_px[1] - start_px[1]
        length = (dx**2 + dy**2) ** 0.5
        if length == 0: return end_px
        ux, uy = dx/length, dy/length
        # Perpendicular
        px_, py_ = -uy, ux
        # Arrow tip points
        tip1 = (end_px[0] - head_size*ux + head_size*px_*0.6,
                end_px[1] - head_size*uy + head_size*py_*0.6)
        tip2 = (end_px[0] - head_size*ux - head_size*px_*0.6,
                end_px[1] - head_size*uy - head_size*py_*0.6)
        draw.polygon([end_px, tip1, tip2], fill=color)
        return end_px

    for h in blue_headers:
        x_pos = px(h['attach'])
        first = px(h['first_cell'])
        # Extend toward first_cell, use a shorter line for arrow (not all the way to cell center)
        # Arrow tip should be inside the pocket cell
        draw_arrow(draw, x_pos, first, color=(200, 20, 20), width=3, head_size=8)
        # Label at arrow tip
        label = f"({h['food_count']},{h['visit_cost']})"
        lx, ly = first[0], first[1]
        # Offset the label slightly
        draw.text((lx+8, ly-5), label, fill=(120, 10, 10))

    # Draw X marks (black, larger)
    for pos in x_positions:
        cx_, cy_ = px(pos)
        sz = 9
        draw.line([(cx_-sz, cy_-sz), (cx_+sz, cy_+sz)], fill=(0, 0, 0), width=4)
        draw.line([(cx_-sz, cy_+sz), (cx_+sz, cy_-sz)], fill=(0, 0, 0), width=4)

    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows*CELL)],
               fill=(120, 120, 120), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == '__main__':
    main()

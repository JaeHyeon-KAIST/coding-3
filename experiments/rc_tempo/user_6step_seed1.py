#!/usr/bin/env python3
"""User's 6-step algorithm with red triangles (junctions) and detour-filter edges.

1. Pockets (leaf pruning)
2. Exclude 0-food pockets
3. Black X = pocket headers (main-corridor attach) + main-corridor food + caps
4. Red triangle = internal junction inside pocket where ≥2 food-containing segments diverge
5. X-X, X-triangle edges: blocked-BFS (as before, all directly-connected pairs)
6. Triangle-triangle edges: direct connection only if not a detour
   (direct blocked-BFS distance ≤ shortest path via other graph nodes)
"""
from __future__ import annotations
import os
import sys
import random
import time
from pathlib import Path
from collections import deque
import heapq
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
os.chdir(str(MINICONTEST))
sys.path.insert(0, str(MINICONTEST))

import mazeGenerator as mg

SEED = 1
CELL = 28
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_6STEP.png"


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
    """Each linear segment = chain of degree-2 pruned cells between endpoints
    (tip, junction, or main-corridor cell)."""
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

    return segments, children


def filter_pockets_by_food(segments):
    """Step 2: Keep only segments that carry food (directly)
    OR connect upstream to a food-carrying segment (for connectivity)."""
    # For simplicity, keep segments with food. Junction cells will be computed from those.
    return [s for s in segments if s['food_count'] > 0]


def collect_interest_and_triangles(live_segments, main_corridor, food_set, cap_set, mid_col):
    """Step 3 & 4:
    - Black X = main-corridor pocket headers (attach points of live segments whose start is main)
              + main-corridor food + caps
    - Red triangle = internal junctions where ≥2 live segments diverge
    """
    x_nodes = {}  # cell → info
    triangles = {}  # junction cell → info

    # Triangle = internal junction with ≥2 live segments
    junction_counts = {}
    for s in live_segments:
        if s['start_type'] == 'junction':
            junction_counts[s['start']] = junction_counts.get(s['start'], 0) + 1
    for j, cnt in junction_counts.items():
        if cnt >= 2:
            triangles[j] = {'live_segs': [s for s in live_segments if s['start'] == j]}

    # X = pocket headers (on main corridor) for segments starting at main
    for s in live_segments:
        if s['start_type'] == 'main' and s['start'][0] >= mid_col:
            key = s['start']
            if key not in x_nodes:
                x_nodes[key] = {'type': 'mouth', 'options': []}
            x_nodes[key]['options'].append((s['food_count'], s['length']*2))
        # segments starting at junction go inside pocket — don't get an X directly
        # but their junction becomes a triangle (handled above)

    # Main-corridor food (blue side)
    for f in food_set:
        if f in main_corridor and f[0] >= mid_col:
            x_nodes[f] = {'type': 'food', 'options': [(1, 0)]}

    # Caps (blue side)
    for c in cap_set:
        if c[0] >= mid_col:
            if c in x_nodes:
                x_nodes[c]['type'] = 'cap+' + x_nodes[c]['type']
            else:
                x_nodes[c] = {'type': 'cap', 'options': [(0, 0)]}

    return x_nodes, triangles


def blocked_bfs(src, terminators, pass_through, walls, W, H):
    """BFS from src. Stop at any cell in `terminators` (record + don't expand).
    Allowed traversal: cells in `pass_through`.
    Returns {terminator: distance}."""
    terminator_dists = {}
    visited = {src}
    q = deque([(src, 0)])
    while q:
        p, d = q.popleft()
        if p != src and p in terminators:
            if p not in terminator_dists or terminator_dists[p] > d:
                terminator_dists[p] = d
            continue
        x, y = p
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x+dx, y+dy
            if not (0<=nx<W and 0<=ny<H): continue
            r = H-1-ny
            if walls[r][nx]: continue
            n = (nx, ny)
            if n not in pass_through: continue
            if n in visited: continue
            visited.add(n)
            q.append((n, d+1))
    return terminator_dists


def build_edges(x_nodes, triangles, pruned, main_corridor, live_segments, walls, W, H):
    """
    Step 5 & 6:
    - X-X and X-triangle: blocked-BFS from each X (all other nodes = terminators)
      pass_through = main_corridor + pocket cells of live segments
    - Triangle-Triangle: blocked-BFS from each triangle with ONLY X's as terminators
      (so triangles can propagate through other triangles — records distance).
      Then filter: triangle-triangle edge only if direct distance ≤ distance via existing X graph.
    """
    all_node_cells = set(x_nodes.keys()) | set(triangles.keys())
    # Pass-through: main corridor + cells in live segments (including pocket cells)
    live_seg_cells = set()
    for s in live_segments:
        live_seg_cells.update(s['cells'])
    pass_through = main_corridor | live_seg_cells

    edges = {}

    # Phase 1: edges involving X nodes (X-X + X-triangle)
    # From each X, blocked-BFS stopping at ALL other nodes
    x_cells = set(x_nodes.keys())
    tri_cells = set(triangles.keys())

    for src in x_cells:
        terms = all_node_cells - {src}
        result = blocked_bfs(src, terms, pass_through, walls, W, H)
        for dst, d in result.items():
            A, B = tuple(sorted([src, dst]))
            if (A, B) not in edges or edges[(A, B)] > d:
                edges[(A, B)] = d

    # Phase 2: edges triangle-triangle (subject to "not detour" rule)
    # From each triangle, direct blocked-BFS with ONLY X nodes as terminators
    # (other triangles are pass-through), record distance to reaching each other triangle
    # via main corridor.
    # Then filter: direct ≤ via-existing-graph
    candidate_tri_edges = {}
    for src in tri_cells:
        # Blocked by X only; other triangles are pass-through
        terms = x_cells  # only X's terminate
        result = blocked_bfs(src, terms, pass_through, walls, W, H)
        # To get triangle-triangle, do a separate search with triangles as terminators too:
        tri_terms = all_node_cells - {src}
        result_tri = blocked_bfs(src, tri_terms, pass_through, walls, W, H)
        for dst in tri_cells:
            if dst == src: continue
            if dst not in result_tri: continue
            d_direct = result_tri[dst]
            A, B = tuple(sorted([src, dst]))
            if (A, B) not in candidate_tri_edges or candidate_tri_edges[(A, B)] > d_direct:
                candidate_tri_edges[(A, B)] = d_direct

    # Filter: direct distance ≤ via-X-graph distance
    # Compute via-graph distance (Dijkstra on existing edges)
    graph = {}  # node → list of (neighbor, weight)
    for (A, B), w in edges.items():
        graph.setdefault(A, []).append((B, w))
        graph.setdefault(B, []).append((A, w))

    def dijkstra(src):
        dists = {src: 0}
        pq = [(0, src)]
        while pq:
            d, p = heapq.heappop(pq)
            if d > dists.get(p, float('inf')): continue
            for n, w in graph.get(p, []):
                nd = d + w
                if nd < dists.get(n, float('inf')):
                    dists[n] = nd
                    heapq.heappush(pq, (nd, n))
        return dists

    filtered_tri_edges = {}
    for (A, B), d_direct in candidate_tri_edges.items():
        # Compute shortest path A → B in current graph (via X's)
        if A in graph:
            dists_from_A = dijkstra(A)
            d_via = dists_from_A.get(B, float('inf'))
        else:
            d_via = float('inf')
        if d_direct <= d_via:
            filtered_tri_edges[(A, B)] = d_direct

    # Merge
    for e, w in filtered_tri_edges.items():
        edges[e] = w

    return edges, filtered_tri_edges


def main():
    print(f"=== RANDOM{SEED} — User's 6-step algorithm ===\n")
    t0 = time.time()

    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    cells, neighbors = build_graph(walls, W, H)
    pruned, parent, orig_deg = find_pockets(cells, neighbors)
    main_corridor = cells - pruned

    segments, children = find_linear_segments(pruned, parent, main_corridor, food_set)
    live_segments = filter_pockets_by_food(segments)
    blue_live = [s for s in live_segments if s['start'][0] >= mid_col or s['end'][0] >= mid_col]

    print(f"[1] 포켓 (pruned cells): {len(pruned)}")
    print(f"[2] 음식 있는 segments: {len(live_segments)} (total), "
          f"{len(blue_live)} (blue side)")

    x_nodes, triangles = collect_interest_and_triangles(
        blue_live, main_corridor, food_set, cap_set, mid_col)

    print(f"[3] 검은색 X (mouth + food + cap): {len(x_nodes)}")
    print(f"[4] 빨간 세모 (internal junctions with ≥2 live segs): {len(triangles)}")
    for t in triangles:
        segs = [(s['food_count'], s['length']*2, s['end']) for s in triangles[t]['live_segs']]
        print(f"    Triangle {t}: {len(segs)} live segments = {segs}")

    # Step 5 & 6
    edges, tri_edges = build_edges(x_nodes, triangles, pruned, main_corridor,
                                    blue_live, walls, W, H)

    n_total = len(edges)
    n_tri = len(tri_edges)
    n_other = n_total - n_tri
    print(f"[5] X-X + X-triangle edges: {n_other}")
    print(f"[6] Triangle-triangle edges (after detour filter): {n_tri}")

    total = time.time() - t0
    print(f"\n==> TOTAL time: {total*1000:.2f} ms")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 140
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} — 6-step algorithm",
              fill=(20, 20, 20))
    draw.text((10, 23), f"[3] X: {len(x_nodes)}  [4] 세모: {len(triangles)}  "
              f"[5] X-edges: {n_other}  [6] 세모-세모: {n_tri}",
              fill=(40, 40, 40))
    draw.text((10, 41), f"Total time: {total*1000:.1f} ms",
              fill=(20, 80, 120))
    draw.text((10, 59), f"Green = X-X / X-triangle  |  Purple = triangle-triangle (direct, not detour)",
              fill=(80, 80, 80))

    ORIG_Y = 85

    import colorsys
    seg_colors = {}
    for i, s in enumerate(blue_live):
        h = (i * 0.618033988749895) % 1.0
        rr, gg, bb = colorsys.hsv_to_rgb(h, 0.4, 0.92)
        seg_colors[id(s)] = (int(rr*255), int(gg*255), int(bb*255))
    cell_to_seg = {}
    for s in blue_live:
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

    # Draw X-X / X-triangle edges (green)
    for (A, B), w in edges.items():
        if (A, B) in tri_edges: continue  # drawn separately
        p1, p2 = px(A), px(B)
        draw.line([p1, p2], fill=(0, 140, 80), width=3)
        mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
        draw.text((mid[0]-3, mid[1]-5), str(w), fill=(0, 80, 40))

    # Draw triangle-triangle edges (purple arcs conceptually, but straight for simplicity)
    for (A, B), w in tri_edges.items():
        p1, p2 = px(A), px(B)
        draw.line([p1, p2], fill=(180, 60, 180), width=3)
        mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
        draw.text((mid[0]-3, mid[1]-5), str(w), fill=(100, 30, 100))

    # Draw X nodes (black X mark)
    for pos in x_nodes:
        cx_, cy_ = px(pos)
        sz = 8
        draw.line([(cx_-sz, cy_-sz), (cx_+sz, cy_+sz)], fill=(0, 0, 0), width=3)
        draw.line([(cx_-sz, cy_+sz), (cx_+sz, cy_-sz)], fill=(0, 0, 0), width=3)

    # Draw triangles (red triangle marker)
    for pos in triangles:
        cx_, cy_ = px(pos)
        sz = 8
        draw.polygon([(cx_-sz, cy_+sz), (cx_+sz, cy_+sz), (cx_, cy_-sz)],
                      fill=(220, 30, 30), outline=(100, 0, 0), width=2)

    # Midline
    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows*CELL)],
               fill=(120, 120, 120), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Food-to-food sparse graph for RANDOM1. Measure time + visualize.

Algorithm (Voronoi-like):
  1. Multi-source BFS from all food (+capsules) simultaneously.
     Each cell gets (owner_food, dist_to_owner).
  2. Scan boundaries: if cell owned by A is adjacent to cell owned by B (A≠B),
     food A and B are "direct neighbors". Edge weight = dist_A + 1 + dist_B.
  3. Result: sparse graph of food neighbors (no redundant long-range edges).
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
OUT = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images" / f"random_{SEED:02d}_FOODTREE.png"


def parse_layout(maze_str):
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    walls = [[False]*cols for _ in range(rows)]
    food, caps, spawns = [], [], {}
    for r, line in enumerate(lines):
        y = rows - 1 - r
        for c, ch in enumerate(line):
            if ch == '%': walls[r][c] = True
            elif ch == '.': food.append((c, y))
            elif ch == 'o': caps.append((c, y))
            elif ch in '1234': spawns[ch] = (c, y)
    return walls, food, caps, spawns, (cols, rows)


def multi_source_bfs(walls, sources, W, H):
    """Multi-source BFS from all sources simultaneously.
    Returns owner[cell] = source that reached cell first, dist[cell] = BFS dist.
    """
    owner = {}
    dist = {}
    q = deque()
    for s in sources:
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
            if n not in owner:
                owner[n] = owner[p]
                dist[n] = d + 1
                q.append(n)
    return owner, dist


def build_food_neighbor_graph(walls, food_sources, W, H):
    """Returns (edges_dict, owner, dist) where edges_dict[(A, B)] = shortest distance between A and B."""
    owner, dist = multi_source_bfs(walls, food_sources, W, H)

    # Scan all cells for neighbor-pairs with different owners
    edges = {}  # (min(A,B), max(A,B)) → min edge weight
    for (x, y), ow in owner.items():
        for dx, dy in [(1,0),(0,1)]:  # only right + down to avoid dup
            nx, ny = x+dx, y+dy
            n = (nx, ny)
            if n not in owner: continue
            ow_n = owner[n]
            if ow == ow_n: continue
            # Boundary between Voronoi regions
            A, B = tuple(sorted([ow, ow_n]))
            weight = dist[(x, y)] + 1 + dist[n]
            if (A, B) not in edges or edges[(A, B)] > weight:
                edges[(A, B)] = weight
    return edges, owner, dist


def main():
    print(f"=== RANDOM{SEED} food-tree construction ===")
    random.seed(SEED)
    maze_str = mg.generateMaze(SEED)
    walls, food, caps, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    blue_food = [f for f in food if f[0] >= mid_col]
    blue_caps = [c for c in caps if c[0] >= mid_col]
    sources = blue_food + blue_caps
    print(f"  # sources: {len(sources)} ({len(blue_food)} food + {len(blue_caps)} caps, blue side)")

    # Measure time
    t0 = time.time()
    edges, owner, dist = build_food_neighbor_graph(walls, sources, W, H)
    t1 = time.time()
    print(f"  multi-source BFS + boundary scan: {(t1-t0)*1000:.1f} ms")
    print(f"  # sparse edges: {len(edges)}")

    # Compare with full pairwise
    t2 = time.time()
    full_pw = {}
    for s in sources:
        d = {}
        q = deque([s])
        d[s] = 0
        while q:
            p = q.popleft()
            x, y = p
            dd = d[p]
            for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                nx, ny = x+dx, y+dy
                if not (0<=nx<W and 0<=ny<H): continue
                r = H-1-ny
                if walls[r][nx]: continue
                if (nx, ny) not in d:
                    d[(nx, ny)] = dd + 1
                    q.append((nx, ny))
        for o in sources:
            if o in d:
                full_pw[(s, o)] = d[o]
    t3 = time.time()
    n_full = sum(1 for (a,b) in full_pw if a < b)
    print(f"  full pairwise BFS: {(t3-t2)*1000:.1f} ms, # edges: {n_full}")
    print(f"  sparse/full ratio: {len(edges) / n_full * 100:.1f}%")

    # Edge degree distribution
    deg = {s: 0 for s in sources}
    for (A, B) in edges.keys():
        deg[A] += 1
        deg[B] += 1
    deg_values = list(deg.values())
    avg_deg = sum(deg_values) / len(deg_values)
    print(f"  avg node degree: {avg_deg:.1f}   min: {min(deg_values)}   max: {max(deg_values)}")

    # --- Render ---
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 130
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{SEED} food-tree (Voronoi sparse graph)",
              fill=(20, 20, 20))
    draw.text((10, 23), f"Nodes: {len(sources)} (food+caps)  |  Edges: {len(edges)} "
              f"(vs {n_full} full pairwise = {len(edges)/n_full*100:.0f}%)",
              fill=(40, 40, 40))
    draw.text((10, 41), f"Avg degree: {avg_deg:.1f}  |  Construction: {(t1-t0)*1000:.1f} ms",
              fill=(40, 120, 40))
    draw.text((10, 59), f"Colored cells = Voronoi region of owning food. "
              f"Orange lines = food-neighbor edges.",
              fill=(80, 80, 80))

    ORIG_Y = 90

    # Assign colors to each source (Voronoi regions)
    import colorsys
    def source_color(idx, total):
        h = (idx * 0.618033988749895) % 1.0  # golden ratio for good spread
        r, g, b = colorsys.hsv_to_rgb(h, 0.3, 0.95)
        return (int(r*255), int(g*255), int(b*255))

    source_idx = {s: i for i, s in enumerate(sources)}
    source_colors = {s: source_color(i, len(sources)) for i, s in enumerate(sources)}

    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            x0, y0 = c*CELL, ORIG_Y + r*CELL
            x1, y1 = x0+CELL, y0+CELL
            cell = (c, rows - 1 - r)
            if ch == '%':
                draw.rectangle([x0,y0,x1,y1], fill=(40,40,60))
            else:
                if c < mid_col:
                    bg = (250, 240, 240)  # red side: neutral
                else:
                    # Blue side: color by owner
                    if cell in owner:
                        bg = source_colors[owner[cell]]
                    else:
                        bg = (220, 230, 245)
                draw.rectangle([x0,y0,x1,y1], fill=bg)

                if ch == '.':
                    cx, cy = x0+CELL//2, y0+CELL//2
                    rd = CELL//6
                    draw.ellipse([cx-rd, cy-rd, cx+rd, cy+rd], fill=(120, 30, 30))
                elif ch == 'o':
                    cx, cy = x0+CELL//2, y0+CELL//2
                    rd = CELL//2 - 3
                    draw.ellipse([cx-rd, cy-rd, cx+rd, cy+rd],
                                  fill=(255,60,200), outline=(80,10,60), width=2)
                elif ch in '1234':
                    draw.rectangle([x0+3,y0+3,x1-3,y1-3], fill=(100,100,100))
                    draw.text((x0+CELL//4, y0+CELL//8), ch, fill=(255,255,255))

    # Draw edges between food neighbors (orange lines)
    def px(cell):
        c, y = cell
        r = rows-1-y
        return (c*CELL+CELL//2, ORIG_Y + r*CELL + CELL//2)
    for (A, B), weight in edges.items():
        p1, p2 = px(A), px(B)
        draw.line([p1, p2], fill=(255, 140, 0), width=2)
        # Edge weight label at midpoint
        mid = ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)
        draw.text((mid[0]-5, mid[1]-5), str(weight), fill=(150, 60, 0))

    # Midline
    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows*CELL)],
               fill=(120, 120, 120), width=2)

    img.save(OUT)
    print(f"\nSaved: {OUT}")

    # Also show edge list
    print(f"\n=== Sparse edges (top 20 by weight) ===")
    for (A, B), w in sorted(edges.items(), key=lambda x: x[1])[:20]:
        print(f"  {A} -- {B}: weight {w}")


if __name__ == '__main__':
    main()

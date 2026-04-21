#!/usr/bin/env python3
"""Render abstract graph (X + pocket headers + edges) for RANDOM<1..30>.

Uses the CORRECTED abstract_graph module (Y-merge food-union fix, cap-in-pocket
extended_main fix). Output: random_{seed:02d}_FINAL.png.

Companion to feasibility_4strategies_abstract.py.
"""
from __future__ import annotations
import os
import sys
import random
import time
from pathlib import Path
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
RC_TEMPO = REPO / "experiments" / "rc_tempo"
OUT_DIR = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images"

os.chdir(str(MINICONTEST))
sys.path.insert(0, str(MINICONTEST))
sys.path.insert(0, str(RC_TEMPO))

import mazeGenerator as mg
from abstract_graph import (
    parse_layout, build_cell_graph, find_pockets,
    build_pocket_headers_with_cost_table, build_x_edges,
)


CELL = 28


def render(seed, out_path):
    random.seed(seed)
    maze_str = mg.generateMaze(seed)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2

    t0 = time.time()
    cells, neighbors = build_cell_graph(walls, W, H)
    pruned, parent = find_pockets(cells, neighbors)
    main_corridor = cells - pruned

    headers_all = build_pocket_headers_with_cost_table(
        pruned, parent, main_corridor, food_set)
    blue_headers = [h for h in headers_all
                     if h['attach'][0] >= mid_col and h['max_food'] > 0]

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

    # Cap-in-pocket fix: extend main_corridor for edge BFS
    extended_main = set(main_corridor)
    for cap in blue_caps:
        if cap in pruned:
            cur = cap
            extended_main.add(cur)
            while cur in parent:
                p = parent[cur]
                extended_main.add(p)
                if p in main_corridor:
                    break
                cur = p

    edges = build_x_edges(walls, x_positions, extended_main, W, H)
    dt = (time.time() - t0) * 1000

    # Render
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    img_W = cols * CELL + 20
    img_H = rows * CELL + 120
    img = Image.new('RGB', (img_W, img_H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.text((10, 5), f"RANDOM{seed:02d} — X + pocket header model",
              fill=(20, 20, 20))
    draw.text((10, 23),
              f"X positions: {len(x_positions)}  |  "
              f"Pocket headers: {len(blue_headers)}  |  Edges: {len(edges)}",
              fill=(40, 40, 40))
    draw.text((10, 41),
              f"Red arrow = pocket header (from X into pocket). "
              f"Number at arrowhead = (food, cost).",
              fill=(80, 80, 80))
    draw.text((10, 59), f"Total time: {dt:.1f} ms",
              fill=(20, 80, 120))

    ORIG_Y = 85

    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            x0, y0 = c * CELL, ORIG_Y + r * CELL
            x1, y1 = x0 + CELL, y0 + CELL
            cell = (c, rows - 1 - r)
            if ch == '%':
                draw.rectangle([x0, y0, x1, y1], fill=(40, 40, 60))
            else:
                if c < mid_col:
                    bg = (250, 240, 240)
                elif cell in pruned:
                    bg = (255, 225, 225)
                else:
                    bg = (235, 245, 255)
                draw.rectangle([x0, y0, x1, y1], fill=bg)
                if ch == '.':
                    cx, cy = x0 + CELL // 2, y0 + CELL // 2
                    rd = CELL // 6
                    draw.ellipse([cx - rd, cy - rd, cx + rd, cy + rd],
                                  fill=(180, 30, 30))
                elif ch == 'o':
                    cx, cy = x0 + CELL // 2, y0 + CELL // 2
                    rd = CELL // 2 - 3
                    draw.ellipse([cx - rd, cy - rd, cx + rd, cy + rd],
                                  fill=(255, 60, 200), outline=(80, 10, 60), width=2)
                elif ch in '1234':
                    draw.rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3],
                                    fill=(100, 100, 100))
                    draw.text((x0 + CELL // 4, y0 + CELL // 8), ch,
                              fill=(255, 255, 255))

    def px(cell):
        c, y = cell
        r = rows - 1 - y
        return (c * CELL + CELL // 2, ORIG_Y + r * CELL + CELL // 2)

    for (A, B), w in edges.items():
        p1, p2 = px(A), px(B)
        draw.line([p1, p2], fill=(0, 140, 80), width=3)

    def draw_arrow(draw, start_px, end_px, color=(200, 20, 20), width=3, head_size=8):
        draw.line([start_px, end_px], fill=color, width=width)
        dx = end_px[0] - start_px[0]
        dy = end_px[1] - start_px[1]
        length = (dx ** 2 + dy ** 2) ** 0.5
        if length == 0:
            return end_px
        ux, uy = dx / length, dy / length
        perp_x, perp_y = -uy, ux
        tip1 = (end_px[0] - head_size * ux + head_size * perp_x * 0.6,
                end_px[1] - head_size * uy + head_size * perp_y * 0.6)
        tip2 = (end_px[0] - head_size * ux - head_size * perp_x * 0.6,
                end_px[1] - head_size * uy - head_size * perp_y * 0.6)
        draw.polygon([end_px, tip1, tip2], fill=color)
        return end_px

    for h in blue_headers:
        x_pos = px(h['attach'])
        first = px(h['first_cell'])
        draw_arrow(draw, x_pos, first, color=(200, 20, 20), width=3, head_size=8)
        label = f"({h['food_count']},{h['visit_cost']})"
        lx, ly = first[0], first[1]
        draw.text((lx + 8, ly - 5), label, fill=(120, 10, 10))

    for pos in x_positions:
        cx_, cy_ = px(pos)
        sz = 9
        draw.line([(cx_ - sz, cy_ - sz), (cx_ + sz, cy_ + sz)],
                   fill=(0, 0, 0), width=4)
        draw.line([(cx_ - sz, cy_ + sz), (cx_ + sz, cy_ - sz)],
                   fill=(0, 0, 0), width=4)

    mxline = mid_col * CELL
    draw.line([(mxline, ORIG_Y), (mxline, ORIG_Y + rows * CELL)],
               fill=(120, 120, 120), width=2)

    img.save(out_path)
    return {
        'x_count': len(x_positions),
        'headers': len(blue_headers),
        'edges': len(edges),
        'dt_ms': dt,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Rendering RANDOM<1..30> to {OUT_DIR}")
    t0 = time.time()
    for seed in range(1, 31):
        out_path = OUT_DIR / f"random_{seed:02d}_FINAL.png"
        stats = render(seed, out_path)
        print(f"  seed={seed:>2}: X={stats['x_count']:>3}  headers={stats['headers']:>2}  "
              f"edges={stats['edges']:>3}  build={stats['dt_ms']:.1f}ms  -> {out_path.name}")
    print(f"\nTotal wall: {time.time() - t0:.1f}s")


if __name__ == '__main__':
    main()

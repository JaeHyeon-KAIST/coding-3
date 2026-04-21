#!/usr/bin/env python3
"""Render RANDOM<1..30> maps as PNG images for visual inspection."""
from __future__ import annotations
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
OUT_DIR = REPO / "experiments" / "artifacts" / "rc_tempo" / "random_map_images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

os.chdir(str(MINICONTEST))
sys.path.insert(0, str(MINICONTEST))

import mazeGenerator as mg
from PIL import Image, ImageDraw, ImageFont

CELL = 18  # pixel per cell
PAD = 2    # inner padding for dots

COLOR = {
    '%': (40, 40, 60),      # wall — dark navy
    ' ': (230, 230, 235),   # empty — light gray
    '.': (255, 220, 80),    # food — yellow dot
    'o': (255, 60, 200),    # capsule — magenta circle (larger)
    '1': (220, 50, 50),     # red agent 1
    '3': (220, 50, 50),     # red agent 3
    '2': (50, 100, 220),    # blue agent 2
    '4': (50, 100, 220),    # blue agent 4
}
TXT = (30, 30, 30)


def render_map(maze_str: str, title: str) -> Image.Image:
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    title_h = 26
    W = cols * CELL
    H = rows * CELL + title_h
    img = Image.new('RGB', (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Midline
    mid_col = cols // 2

    for r, line in enumerate(lines):
        for c, ch in enumerate(line):
            x0, y0 = c * CELL, title_h + r * CELL
            x1, y1 = x0 + CELL, y0 + CELL
            if ch == '%':
                draw.rectangle([x0, y0, x1, y1], fill=COLOR['%'])
            else:
                # Light tint for left (red) / right (blue) half
                if c < mid_col:
                    draw.rectangle([x0, y0, x1, y1], fill=(250, 240, 240))
                else:
                    draw.rectangle([x0, y0, x1, y1], fill=(240, 245, 255))
                if ch == '.':
                    cx, cy = x0 + CELL // 2, y0 + CELL // 2
                    r_ = CELL // 6
                    draw.ellipse([cx-r_, cy-r_, cx+r_, cy+r_], fill=COLOR['.'])
                elif ch == 'o':
                    cx, cy = x0 + CELL // 2, y0 + CELL // 2
                    r_ = CELL // 2 - PAD
                    draw.ellipse([cx-r_, cy-r_, cx+r_, cy+r_],
                                  fill=COLOR['o'], outline=(80, 10, 60), width=2)
                elif ch in '1234':
                    col = COLOR[ch]
                    draw.rectangle([x0+PAD, y0+PAD, x1-PAD, y1-PAD], fill=col)
                    # Draw digit
                    draw.text((x0 + CELL//4, y0 + CELL//8), ch,
                              fill=(255, 255, 255))

    # Midline indicator
    mx = mid_col * CELL
    draw.line([(mx, title_h), (mx, H)], fill=(200, 200, 200), width=1)

    # Title
    draw.rectangle([0, 0, W, title_h], fill=(250, 250, 250))
    draw.text((8, 5), title, fill=TXT)

    return img


def main():
    import random as _random
    maps = {}
    print("Generating RANDOM<1..30> maps...")
    for seed in range(1, 31):
        _random.seed(seed)
        maze_str = mg.generateMaze(seed)
        maps[seed] = maze_str

    # Save individual PNGs
    print(f"\nSaving individual PNGs to {OUT_DIR}/")
    for seed, ms in maps.items():
        cols = len(ms.split('\n')[0])
        rows = len(ms.split('\n'))
        caps = ms.count('o')
        foods = ms.count('.')
        title = f"RANDOM{seed}   {cols}x{rows}   cap={caps}  food={foods}"
        img = render_map(ms, title)
        img.save(OUT_DIR / f"random_{seed:02d}.png")

    # Create composite grid (5 cols × 6 rows)
    print("\nCreating composite grid (6 rows × 5 cols)...")
    sample_lines = maps[1].split('\n')
    single_W = len(sample_lines[0]) * CELL
    single_H = len(sample_lines) * CELL + 26
    GRID_COLS = 5
    GRID_ROWS = 6
    GAP = 10
    grid_W = GRID_COLS * single_W + (GRID_COLS + 1) * GAP
    grid_H = GRID_ROWS * single_H + (GRID_ROWS + 1) * GAP + 50
    grid = Image.new('RGB', (grid_W, grid_H), (245, 245, 245))
    d = ImageDraw.Draw(grid)
    d.text((10, 15), "RANDOM<1..30> — all 4-capsule 34x18 prison-style procedural mazes",
            fill=(20, 20, 20))

    for i, seed in enumerate(range(1, 31)):
        row, col = i // GRID_COLS, i % GRID_COLS
        img = render_map(maps[seed], f"RANDOM{seed}")
        x = GAP + col * (single_W + GAP)
        y = 50 + GAP + row * (single_H + GAP)
        grid.paste(img, (x, y))

    grid_path = OUT_DIR / "all_random_1_to_30.png"
    grid.save(grid_path)
    print(f"Saved composite: {grid_path}")
    print(f"Individual PNGs: {OUT_DIR}/random_01.png ~ random_30.png")
    print(f"\nView composite: open {grid_path}")


if __name__ == '__main__':
    main()

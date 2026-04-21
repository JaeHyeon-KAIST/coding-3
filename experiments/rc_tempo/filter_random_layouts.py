#!/usr/bin/env python3
"""pm32 layout filter — generate RANDOM<seed> layout list, keep only 1-cap-per-side.

The pm32 plan optimizes the β capsule-chase for 1-capsule-per-side layouts
(it's the prerequisite for `_precompute_team`). RANDOM<seed> layouts can have
0/1/2 capsules per side. This script filters out non-1-cap layouts so T1 and
T2 only run on relevant maps.

Auto-expand pool if yield is below target_count:
    1001-pool_max → +10 → +20 → ...

Usage:
    # Emit the 16 fixed pm32 layouts directly (no RANDOM filtering needed):
    .venv/bin/python experiments/rc_tempo/filter_random_layouts.py \\
        --pm32-fixed --out experiments/rc_tempo/pm32_t1_layouts.txt

    # Legacy RANDOM-seed mode:
    .venv/bin/python experiments/rc_tempo/filter_random_layouts.py \\
        --seed-pool $(seq 1001 1020) --target-count 12 \\
        --out experiments/rc_tempo/pm32_t1_layouts.txt
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / 'minicontest'
sys.path.insert(0, str(MINICONTEST))


def count_capsules_per_side(layout_name):
    """Returns (red_caps, blue_caps) for a layout, or (None, None) on failure.

    RANDOM<seed> layouts are generated via mazeGenerator.randomLayout(seed)
    in the project (capture.py:891-894), NOT via getLayout (which is for
    .lay files only). Fixed layouts (e.g., defaultCapture) use getLayout.
    """
    # capture / layout import requires cwd = minicontest
    cwd_save = os.getcwd()
    try:
        os.chdir(str(MINICONTEST))
        if layout_name.startswith('RANDOM'):
            # Generate maze via project's randomLayout
            try:
                seed = int(layout_name.replace('RANDOM', ''))
            except ValueError:
                return (None, None)
            from mazeGenerator import generateMaze
            from layout import Layout
            try:
                maze_text = generateMaze(seed)
            except Exception as e:
                print(f"[filter] generateMaze({seed}) failed: {e}",
                      file=sys.stderr)
                return (None, None)
            lay = Layout(maze_text.split('\n'))
        else:
            from layout import getLayout
            lay = getLayout(layout_name, 3)
        if lay is None:
            return (None, None)
        # Capsules in layout are global; split by midline x
        walls = lay.walls
        mid = walls.width // 2
        red_caps = 0
        blue_caps = 0
        for cap in lay.capsules:
            if cap[0] < mid:
                red_caps += 1
            else:
                blue_caps += 1
        return (red_caps, blue_caps)
    except Exception as e:
        print(f"[filter] error on {layout_name}: {type(e).__name__}: {e}",
              file=sys.stderr)
        return (None, None)
    finally:
        os.chdir(cwd_save)


PM32_FIXED_LAYOUTS = [
    # 3 original reference layouts (1-cap-per-side confirmed)
    'defaultCapture',
    'distantCapture',
    'strategicCapture',
    # 8 capsule-swap variants (pm32 session, 2026-04-21)
    'defaultCapture_capN',
    'defaultCapture_capS',
    'defaultCapture_capCenter',
    'defaultCapture_capCorner',
    'distantCapture_capN',
    'distantCapture_capCenter',
    'strategicCapture_capN',
    'strategicCapture_capCorner',
    # 5 hand-crafted topologies (pm32 session, 2026-04-21)
    'pm32_corridorCapture',
    'pm32_openCapture',
    'pm32_fortressCapture',
    'pm32_zigzagCapture',
    'pm32_chokeCapture',
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pm32-fixed', action='store_true', default=False,
                     help='Emit the 16 fixed pm32 1-cap layouts directly '
                          '(3 originals + 8 cap-swap variants + 5 hand-crafted). '
                          'Skips all RANDOM-seed filtering. '
                          '--seed-pool is not required when this flag is set.')
    ap.add_argument('--seed-pool', nargs='+', type=int, default=None,
                     help='Initial pool of RANDOM<seed> seeds (not needed with --pm32-fixed)')
    ap.add_argument('--target-count', type=int, default=12,
                     help='Min number of valid 1-cap layouts to return')
    ap.add_argument('--max-pool-size', type=int, default=50,
                     help='Auto-expand pool up to this many seeds total')
    ap.add_argument('--out', type=Path, default=None,
                     help='Output txt path (one layout name per line)')
    ap.add_argument('--include-fixed', action='store_true', default=False,
                     help='Prepend the 4 legacy fixed layouts (defaultCapture etc.) '
                          'when using RANDOM-seed mode')
    args = ap.parse_args()

    # Fast path: emit the fixed pm32 layout list directly
    if args.pm32_fixed:
        final_layouts = list(PM32_FIXED_LAYOUTS)
        print(f"[filter] --pm32-fixed: emitting {len(final_layouts)} fixed layouts")
        for name in final_layouts:
            print(f"  {name}")
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open('w') as f:
                f.write("# pm32 T1/T2 layouts — fixed 1-cap-per-side set\n")
                f.write("# 3 originals + 8 cap-swap variants + 5 hand-crafted\n")
                f.write("# Generated by filter_random_layouts.py --pm32-fixed\n")
                for layout in final_layouts:
                    f.write(layout + '\n')
            print(f"[filter] wrote {len(final_layouts)} layouts to {args.out}")
        else:
            print("\n--- LAYOUT LIST ---")
            for layout in final_layouts:
                print(layout)
        return

    if args.seed_pool is None:
        ap.error("--seed-pool is required when --pm32-fixed is not set")

    seeds = list(args.seed_pool)
    accepted = []
    rejected = {}
    pool_idx = 0

    while len(accepted) < args.target_count and len(seeds) < args.max_pool_size:
        # Process new seeds in current pool
        while pool_idx < len(seeds):
            seed = seeds[pool_idx]
            pool_idx += 1
            name = f"RANDOM{seed}"
            r, b = count_capsules_per_side(name)
            if r is None:
                rejected[name] = 'load_failed'
                continue
            if r == 1 and b == 1:
                accepted.append(name)
                if len(accepted) >= args.target_count:
                    break
            else:
                rejected[name] = f'red_caps={r}, blue_caps={b}'
        # If still short, expand pool by 10
        if len(accepted) < args.target_count and len(seeds) < args.max_pool_size:
            last = seeds[-1]
            print(f"[filter] yield={len(accepted)}/{args.target_count}; "
                  f"expanding pool by 10 (next seed={last+1})", file=sys.stderr)
            seeds.extend(range(last + 1, last + 11))

    print(f"\n[filter] yield: {len(accepted)} valid 1-cap layouts "
          f"out of {pool_idx} examined")
    print(f"[filter] accepted seeds: {[int(n.replace('RANDOM','')) for n in accepted]}")
    if rejected:
        print(f"[filter] rejected: {len(rejected)} layouts")
        for name, reason in sorted(rejected.items())[:10]:
            print(f"  {name}: {reason}")
    # Operator hint when nothing passes — RANDOM mazes use mazeGenerator
    # add_pacman_stuff which always adds capsules in pairs up to max_capsules=4,
    # so RANDOM<seed> layouts always produce 2 caps per side. The plan's
    # 1-cap-only constraint is satisfiable only by the 4 fixed layouts unless
    # mazeGenerator is patched. Use --include-fixed to emit those 4 anyway.
    if len(accepted) == 0 and pool_idx > 0:
        print(f"\n[filter] NOTE: zero RANDOM<seed> layouts satisfy 1-cap-per-side. "
              f"Project's mazeGenerator adds capsules in pairs up to "
              f"max_capsules=4 (mazeGenerator.py:233-241), so RANDOM mazes "
              f"always produce 2 per side. Use --include-fixed to fall back "
              f"to the 4 fixed layouts (defaultCapture/distantCapture/"
              f"strategicCapture/testCapture, of which 3 are 1-cap-per-side).")

    final_layouts = []
    if args.include_fixed:
        final_layouts = ['defaultCapture', 'distantCapture', 'strategicCapture',
                          'testCapture']
    final_layouts.extend(accepted)

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open('w') as f:
            f.write("# pm32 T1/T2 layouts — generated by filter_random_layouts.py\n")
            for layout in final_layouts:
                f.write(layout + '\n')
        print(f"\n[filter] wrote {len(final_layouts)} layouts to {args.out}")
    else:
        print("\n--- LAYOUT LIST ---")
        for layout in final_layouts:
            print(layout)


if __name__ == '__main__':
    main()

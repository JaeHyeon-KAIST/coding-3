#!/usr/bin/env python3
"""Retrograde analysis feasibility test for capsule chase subgame.

Computes V[(me, def, turn)] = ±1 (force win/loss) for all state combos
on a given layout. Reports time taken.

Usage:
    .venv/bin/python experiments/rc_tempo/retrograde_test.py defaultCapture
    .venv/bin/python experiments/rc_tempo/retrograde_test.py distantCapture
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MINICONTEST = REPO / 'minicontest'

sys.path.insert(0, str(MINICONTEST))


def open_cells(walls):
    W, H = walls.width, walls.height
    return [(x, y) for x in range(W) for y in range(H) if not walls[x][y]]


def neighbors_with_stop(walls, cell):
    x, y = cell
    W, H = walls.width, walls.height
    out = [cell]  # STOP (same cell)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < W and 0 <= ny < H and not walls[nx][ny]:
            out.append((nx, ny))
    return out


def retrograde(walls, capsule, restrict_opp_side=True):
    """Compute V[(me, def, turn)] for chase subgame on opp territory.

    turn: 0 = my turn (I choose max), 1 = def turn (def chooses min).
    Value: +1 I win (reach capsule), -1 I lose (def catches me), 0 unresolved.

    Returns dict mapping state tuple to value.
    """
    W, H = walls.width, walls.height
    mid = W // 2
    cells = open_cells(walls)

    if restrict_opp_side:
        # Assume our capsule is on opp side (x >= mid typical for red team)
        cap_x = capsule[0]
        if cap_x >= mid:
            opp_cells = [c for c in cells if c[0] >= mid - 1]  # include midline crossing
        else:
            opp_cells = [c for c in cells if c[0] <= mid]
        cells = opp_cells

    n = len(cells)
    print(f"  Cells in chase region: {n}")

    # Precompute neighbors
    nbrs = {c: neighbors_with_stop(walls, c) for c in cells}
    # Filter to in-region only
    for c in cells:
        nbrs[c] = [n2 for n2 in nbrs[c] if n2 in set(cells)]

    # V[(me, def, turn)] initialization
    V = {}
    # Terminal states:
    # - me == capsule: +1 (I already won)
    # - me == def AND turn == 0 (I'm about to move into def): -1
    # - me == def AND turn == 1 (def just caught me): -1
    for me in cells:
        for d in cells:
            for turn in (0, 1):
                if me == capsule:
                    V[(me, d, turn)] = +1
                elif me == d:
                    V[(me, d, turn)] = -1
                else:
                    V[(me, d, turn)] = 0  # unresolved

    print(f"  Initial states: {len(V)}")
    print(f"  Terminals: +1 = {sum(1 for v in V.values() if v == +1)}, "
          f"-1 = {sum(1 for v in V.values() if v == -1)}")

    # Iterate to convergence
    iteration = 0
    while True:
        iteration += 1
        changes = 0
        for me in cells:
            if me == capsule:
                continue
            for d in cells:
                if me == d:
                    continue
                # Turn 0 (my turn): I pick max over my next moves
                key0 = (me, d, 0)
                if V[key0] == 0:
                    best = -2
                    for me_next in nbrs[me]:
                        # After my move, turn → def's turn
                        # If I move into def cell → I die
                        if me_next == d:
                            v = -1
                        else:
                            v = V[(me_next, d, 1)]
                        if v > best:
                            best = v
                    # Only update if definitively resolved
                    # best == +1 : I can force win
                    # best == -1 : even my best move leads to loss (need all to be ≤ -1)
                    # Correct semantics: max over my actions
                    # If max is +1 (some action leads to my win), V=+1
                    # If max is -1 (all actions lead to my loss), V=-1
                    # If max is 0 (some action leads to unresolved), V stays 0
                    if best != 0:
                        V[key0] = best
                        changes += 1

                # Turn 1 (def's turn): def picks min
                key1 = (me, d, 1)
                if V[key1] == 0:
                    worst = +2
                    for d_next in nbrs[d]:
                        # After def's move, turn → my turn
                        # If def moves onto me cell → I die
                        if d_next == me:
                            v = -1
                        else:
                            v = V[(me, d_next, 0)]
                        if v < worst:
                            worst = v
                    # Semantics: min over def actions
                    # If min is -1 (def can force catching me), V=-1
                    # If min is +1 (even def's best play leaves me winning), V=+1
                    if worst != 0:
                        V[key1] = worst
                        changes += 1

        if changes == 0:
            break
        if iteration % 5 == 0:
            resolved = sum(1 for v in V.values() if v != 0)
            print(f"  Iter {iteration}: {changes} changes, {resolved}/{len(V)} resolved")

    resolved = sum(1 for v in V.values() if v != 0)
    print(f"  Converged at iter {iteration}: {resolved}/{len(V)} resolved "
          f"({100*resolved/len(V):.1f}%)")
    return V, cells


def main():
    layout_name = sys.argv[1] if len(sys.argv) > 1 else 'defaultCapture'
    print(f"=== Retrograde feasibility test on {layout_name} ===\n")

    import os
    os.chdir(str(MINICONTEST))
    from layout import getLayout

    lay = getLayout(layout_name, 3)
    if lay is None:
        print(f"Layout {layout_name} not found")
        return

    walls = lay.walls
    capsules = list(lay.capsules)
    print(f"Layout: {walls.width}x{walls.height}, capsules: {capsules}")

    # Pick one capsule (opp side from red's POV = x >= mid)
    mid = walls.width // 2
    target_caps = [c for c in capsules if c[0] >= mid]
    if not target_caps:
        target_caps = capsules
    capsule = target_caps[0]
    print(f"Target capsule: {capsule}\n")

    # Warm-up: report total open cells
    all_open = open_cells(walls)
    print(f"Total open cells: {len(all_open)}")

    t0 = time.time()
    V, cells = retrograde(walls, capsule, restrict_opp_side=True)
    wall = time.time() - t0

    # Stats
    resolved_plus = sum(1 for v in V.values() if v == +1)
    resolved_minus = sum(1 for v in V.values() if v == -1)
    unresolved = sum(1 for v in V.values() if v == 0)

    print(f"\n=== Results ===")
    print(f"Total wall time: {wall:.2f}s")
    print(f"V = +1 (I can force win): {resolved_plus}")
    print(f"V = -1 (def can force catch): {resolved_minus}")
    print(f"V =  0 (unresolved):         {unresolved}")
    print(f"\n--- Sample queries ---")

    # Query a few interesting states
    mid_y = walls.height // 2
    starting_me = (mid - 1, mid_y)
    # A few plausible def positions
    for d_off in [(2, 0), (5, 0), (10, 0), (15, 0)]:
        d_pos = (capsule[0] + d_off[0], capsule[1] + d_off[1] if 0 <= capsule[1] + d_off[1] < walls.height else capsule[1])
        if d_pos not in cells:
            continue
        key = (starting_me, d_pos, 0)
        v = V.get(key, 'N/A')
        print(f"  V[me={starting_me}, def={d_pos}, my_turn] = {v}")


if __name__ == '__main__':
    main()

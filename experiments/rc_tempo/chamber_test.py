#!/usr/bin/env python3
"""Prototype: chamber-aware abstract graph for seed 2.

Question: does chamber atomization let BEAM=500 find the same optimum that
current implementation needs BEAM=5000 for?

Method:
  1. Build current abstract graph for seed 2.
  2. Find articulation points on blue side → chamber cells.
  3. For each chamber with food, compute cost_table via Held-Karp DP (exact).
  4. Create NEW abstract graph where chamber food cells are replaced with a
     single "chamber header" attached to the articulation point.
  5. Run beam search at BEAM=500, compare to the non-chamber version.
"""
from __future__ import annotations
import os
import sys
import random
import time
import heapq
from collections import deque
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
RC_TEMPO = REPO / "experiments" / "rc_tempo"
os.chdir(str(MINICONTEST))
sys.path.insert(0, str(MINICONTEST))
sys.path.insert(0, str(RC_TEMPO))

import mazeGenerator as mg
from abstract_graph import (
    parse_layout, build_cell_graph, find_pockets,
    build_pocket_headers_with_cost_table, build_x_edges, build_abstract_graph,
    full_map_bfs,
)
from abstract_search import beam_search_abstract


def biconnected_decomp(cells_list, nbrs, start_nodes=None):
    """Tarjan's biconnected components on cell graph.

    Returns (blocks, aps):
      blocks — list of sets (each set is cells in one biconnected component)
      aps    — set of articulation-point cells
    Only explores cells in cells_list (ignores neighbors outside).
    """
    import sys
    sys.setrecursionlimit(20000)

    allowed = set(cells_list)

    def adj(u):
        return [v for v in nbrs[u] if v in allowed]

    disc = {}
    low = {}
    parent = {}
    aps = set()
    blocks = []
    edge_stack = []
    timer = [0]

    def dfs(u, par):
        disc[u] = low[u] = timer[0]
        timer[0] += 1
        children = 0
        parent[u] = par
        for v in adj(u):
            if v not in disc:
                children += 1
                edge_stack.append((u, v))
                dfs(v, u)
                low[u] = min(low[u], low[v])
                if par is None and children > 1:
                    aps.add(u)
                if par is not None and low[v] >= disc[u]:
                    aps.add(u)
                if low[v] >= disc[u]:
                    block = set()
                    while edge_stack:
                        a, b = edge_stack.pop()
                        block.add(a)
                        block.add(b)
                        if (a, b) == (u, v):
                            break
                    blocks.append(block)
            elif v != par and disc[v] < disc[u]:
                edge_stack.append((u, v))
                low[u] = min(low[u], disc[v])

    starts = start_nodes if start_nodes else cells_list
    for u in starts:
        if u in allowed and u not in disc:
            dfs(u, None)
            if edge_stack:
                block = set()
                while edge_stack:
                    a, b = edge_stack.pop()
                    block.add(a)
                    block.add(b)
                blocks.append(block)

    return blocks, aps


def find_chambers(cells, nbrs, mid_col, leaf_pruned):
    """Find chamber leaf-blocks via biconnected decomposition.

    Restricts to main_corridor ∪ leaf_pruned=removed cells. Identifies
    biconnected components of main_corridor; LEAF BLOCKS (blocks with exactly 1
    articulation point) are chambers. Returns (ap, chamber_cells) per chamber.
    Chamber_cells excludes the ap itself (block − {ap}).
    """
    main_corridor = cells - leaf_pruned
    blocks, aps = biconnected_decomp(main_corridor, nbrs)

    chambers = []
    for block in blocks:
        aps_in_block = block & aps
        if len(aps_in_block) != 1:
            continue  # not a leaf block
        ap = next(iter(aps_in_block))
        chamber_cells = block - {ap}
        # Must be on blue side (we only care about blue-side chambers)
        if ap[0] < mid_col:
            continue
        if not all(c[0] >= mid_col for c in chamber_cells):
            # Chamber extends across midline — skip (not a blue-side pocket)
            continue
        if not chamber_cells:
            continue
        chambers.append((ap, chamber_cells))
    return chambers


def chamber_cost_table(chamber_cells, ap, food_set, nbrs):
    """Held-Karp DP: cost_table[k] = min moves to collect k food in chamber,
    start and end at ap.
    """
    full_cells = chamber_cells | {ap}
    food_in_chamber = [c for c in chamber_cells if c in food_set]
    F = len(food_in_chamber)
    food_idx = {f: i for i, f in enumerate(food_in_chamber)}

    # Pairwise BFS within full_cells
    def bfs_restricted(start):
        d = {start: 0}
        q = deque([start])
        while q:
            p = q.popleft()
            for n in nbrs[p]:
                if n not in full_cells or n in d:
                    continue
                d[n] = d[p] + 1
                q.append(n)
        return d

    dist = {c: bfs_restricted(c) for c in full_cells}

    # Dijkstra on (food_mask, current_cell)
    INF = float('inf')
    best = {(0, ap): 0}
    pq = [(0, 0, ap)]
    while pq:
        cost, S, v = heapq.heappop(pq)
        if best.get((S, v), INF) < cost:
            continue
        for vp, d in dist[v].items():
            if vp == v:
                continue
            new_S = S | (1 << food_idx[vp]) if vp in food_idx else S
            new_cost = cost + d
            key = (new_S, vp)
            if new_cost < best.get(key, INF):
                best[key] = new_cost
                heapq.heappush(pq, (new_cost, new_S, vp))

    # cost_table[k] = min over |S|=k of (best[(S, ap)])
    cost_table = [None] * (F + 1)
    cost_table[0] = 0
    for (S, v), c in best.items():
        if v != ap:
            continue
        k = bin(S).count('1')
        if cost_table[k] is None or cost_table[k] > c:
            cost_table[k] = c
    return cost_table, food_in_chamber


def build_chamber_augmented_graph(seed):
    """Build abstract graph WITH chamber headers added + chamber food X's removed."""
    random.seed(seed)
    maze_str = mg.generateMaze(seed)
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    mid_col = W // 2
    cells, nbrs = build_cell_graph(walls, W, H)
    pruned, parent = find_pockets(cells, nbrs)
    main_corridor = cells - pruned

    # Regular leaf-pocket headers
    headers_all = build_pocket_headers_with_cost_table(
        pruned, parent, main_corridor, food_set)
    blue_headers = [h for h in headers_all
                     if h['attach'][0] >= mid_col and h['max_food'] > 0]

    blue_food = [f for f in food_set if f[0] >= mid_col]
    blue_caps = [c for c in cap_set if c[0] >= mid_col]

    # Biconnected decomposition — leaf blocks with single AP are chambers.
    # No overlap: each cell in exactly one block.
    chambers = find_chambers(cells, nbrs, mid_col, pruned)
    print(f'Chambers (leaf biconnected blocks): {len(chambers)}')

    # For each chamber with food, compute cost_table and add as a header
    chamber_food_set = set()  # food cells that will be handled by chamber headers
    for ap, chamber_cells in chambers:
        ct, food_in = chamber_cost_table(chamber_cells, ap, food_set, nbrs)
        if not food_in:
            continue
        chamber_food_set |= set(food_in)
        # Direction: use AP's geometric center of chamber cells
        if chamber_cells:
            avg_x = sum(c[0] for c in chamber_cells) / len(chamber_cells)
            avg_y = sum(c[1] for c in chamber_cells) / len(chamber_cells)
            dx = 1 if avg_x > ap[0] else (-1 if avg_x < ap[0] else 0)
            dy = 1 if avg_y > ap[1] else (-1 if avg_y < ap[1] else 0)
        else:
            dx, dy = 0, 0
        blue_headers.append({
            'attach': ap,
            'first_cell': ap,  # virtual
            'direction': (dx, dy),
            'max_food': len(food_in),
            'food_count': len(food_in),
            'cost_table': ct,
            'visit_cost': ct[len(food_in)] if ct[len(food_in)] is not None else 0,
            'max_food_depth': 0,
            'tips': [],
            'all_cells': list(chamber_cells),
            'chamber': True,
        })
        print(f'  chamber at AP={ap}: {len(chamber_cells)} cells, {len(food_in)} food, cost_table={ct}')

    # Build X positions (excluding chamber food)
    blue_xs = set()
    for h in blue_headers:
        blue_xs.add(h['attach'])
    for f in blue_food:
        if f in chamber_food_set:
            continue  # handled by chamber header
        if f in main_corridor:
            blue_xs.add(f)
    for c in blue_caps:
        blue_xs.add(c)

    # Entry X's (red side)
    entry_xs = set()
    for r in range(H):
        c = mid_col - 1
        if c >= 0 and not walls[r][c]:
            y = H - 1 - r
            cell = (c, y)
            if cell in main_corridor:
                entry_xs.add(cell)

    x_positions = blue_xs | entry_xs
    x_headers = {}
    for h in blue_headers:
        x_headers.setdefault(h['attach'], []).append(h)

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
    # Also extend through chamber cells to reach caps or chamber-X points
    for ap, chamber_cells in chambers:
        extended_main |= chamber_cells

    edges = build_x_edges(walls, x_positions, extended_main, W, H)
    adj = {x: [] for x in x_positions}
    for (a, b), w in edges.items():
        adj[a].append((b, w))
        adj[b].append((a, w))

    x_has_food = {x: (x in food_set) for x in x_positions}

    graph = {
        'x_positions': x_positions, 'blue_xs': blue_xs, 'entry_xs': entry_xs,
        'headers': blue_headers, 'x_headers': x_headers,
        'edges': edges, 'adj': adj, 'main_corridor': main_corridor,
        'blue_caps': blue_caps, 'blue_food': blue_food,
        'x_has_food': x_has_food,
        'mid_col': mid_col, 'W': W, 'H': H,
    }
    return graph, walls, spawns


def test(seed, budget=79):
    print(f'\n=== seed {seed} ===')
    # Baseline: non-chamber graph
    random.seed(seed)
    maze_str = mg.generateMaze(seed)
    from abstract_graph import build_from_maze
    g_base, walls, spawns = build_from_maze(maze_str)
    spawn_a = spawns['1']
    a_dists = full_map_bfs(walls, spawn_a, g_base['W'], g_base['H'])
    cap_sorted = sorted(g_base['blue_caps'], key=lambda c: a_dists.get(c, 9999))
    cap1 = cap_sorted[0]

    print('--- BASELINE (no chamber) ---')
    for beam in (500, 2000, 5000):
        t0 = time.time()
        res = beam_search_abstract(g_base, cap1, g_base['entry_xs'], budget=budget,
                                     beam=beam, max_steps=64)
        dt = (time.time() - t0) * 1000
        best = res[0] if res else {'food': 0, 'time': 0}
        print(f'  BEAM={beam:>4}: food={best["food"]:>2}  time={best["time"]:>3}  wall={dt:.0f}ms')

    print('--- CHAMBER-AUGMENTED ---')
    g_cham, _, _ = build_chamber_augmented_graph(seed)
    for beam in (500, 2000, 5000):
        t0 = time.time()
        res = beam_search_abstract(g_cham, cap1, g_cham['entry_xs'], budget=budget,
                                     beam=beam, max_steps=64)
        dt = (time.time() - t0) * 1000
        best = res[0] if res else {'food': 0, 'time': 0}
        print(f'  BEAM={beam:>4}: food={best["food"]:>2}  time={best["time"]:>3}  wall={dt:.0f}ms')


if __name__ == '__main__':
    for seed in (2, 4, 16):
        test(seed, budget=79)

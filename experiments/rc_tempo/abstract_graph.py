#!/usr/bin/env python3
"""Abstract graph module for 2-cap chain feasibility.

Extracted from user_final_model_seed1.py. No PIL/rendering.

Blue-side abstract graph:
- X positions: pocket attaches ∪ blue food on main corridor ∪ blue caps
  (+ red entry X's at x=mid_col-1 when include_red_entry=True — for entry/exit semantics
   matching the food-level feasibility analyzer which uses red_edges as segment endpoints)
- Pocket headers: one per tip with food, attached to an X
  {attach, first_cell, food_count, visit_cost, direction, max_food_depth}
  Y-shape merge: headers sharing (attach, first_cell) combined with shared-trunk cost
- X-X edges: distance-check rule (blocked_bfs_dist == plain_bfs_dist on main_corridor).

Reusable by feasibility analyzer and (later) β agent.
"""
from __future__ import annotations
from collections import deque


def parse_layout(maze_str):
    lines = maze_str.rstrip('\n').split('\n')
    rows, cols = len(lines), len(lines[0])
    walls = [[False] * cols for _ in range(rows)]
    food_set, cap_set, spawns = set(), set(), {}
    for r, line in enumerate(lines):
        y = rows - 1 - r
        for c, ch in enumerate(line):
            if ch == '%':
                walls[r][c] = True
            elif ch == '.':
                food_set.add((c, y))
            elif ch == 'o':
                cap_set.add((c, y))
            elif ch in '1234':
                spawns[ch] = (c, y)
    return walls, food_set, cap_set, spawns, (cols, rows)


def build_cell_graph(walls, W, H):
    cells = set()
    for r in range(H):
        for c in range(W):
            if not walls[r][c]:
                y = H - 1 - r
                cells.add((c, y))
    neighbors = {c: [] for c in cells}
    for (x, y) in cells:
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            n = (x + dx, y + dy)
            if n in cells:
                neighbors[(x, y)].append(n)
    return cells, neighbors


def find_pockets(cells, neighbors):
    degree = {c: len(neighbors[c]) for c in cells}
    pruned = set()
    parent = {}
    leaf_q = deque([c for c in cells if degree[c] == 1])
    while leaf_q:
        v = leaf_q.popleft()
        if v in pruned:
            continue
        if degree[v] != 1:
            continue
        active = [n for n in neighbors[v] if n not in pruned]
        if len(active) != 1:
            continue
        p = active[0]
        parent[v] = p
        pruned.add(v)
        degree[p] -= 1
        if degree[p] == 1:
            leaf_q.append(p)
    return pruned, parent


def get_pocket_headers(pruned, parent, main_corridor, food_set):
    """One header per tip with food. path = [tip, ..., first_cell]; attach is main corridor.

    Kept for backward compatibility / rendering. For planning use
    build_pocket_headers_with_cost_table instead.
    """
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
        if attach is None:
            continue
        food_on = [c for c in trace if c in food_set]
        if not food_on:
            continue
        max_fd = 0
        for i, c in enumerate(trace):
            if c in food_set:
                d = len(trace) - i
                if d > max_fd:
                    max_fd = d
        first_cell = trace[-1]
        direction = (first_cell[0] - attach[0], first_cell[1] - attach[1])
        headers.append({
            'attach': attach, 'first_cell': first_cell, 'tip': tip,
            'path': trace, 'food_count': len(food_on),
            'max_food_depth': max_fd, 'visit_cost': 2 * max_fd,
            'direction': direction,
        })
    return headers


def _tree_knapsack(children_of, root, food_set):
    """Post-order DP on pocket tree rooted at `root`.

    Returns cost_list where cost_list[k] = min moves to collect exactly k food
    in the subtree rooted at `root`, starting and ending at root.
    cost_list[k] = None if k food is infeasible.
    cost_list[0] = 0 (don't visit any food).

    Edge weight = 1 move per parent-child step (pocket cells are grid-adjacent).
    Round-trip to visit a child subtree = 2 moves for the single edge.
    If a node is in food_set, visiting the node collects its food. "Being at
    the node" requires stepping onto it, so if v is food, the minimum food
    count when landing at v is 1 (cost[v][0] = None).

    Root itself is a special case: if root is food, cost[root][0] = None
    (can't be at root without food). But the CALLER typically treats the
    root (attach X) as already "entered free" from outside — so when
    integrating, use cost[root] as-is and optionally add 1 food if root is
    food. This function doesn't second-guess that; it reports the raw DP.
    """
    def dfs(v):
        v_food = 1 if v in food_set else 0
        if v_food:
            my_cost = [None, 0]
        else:
            my_cost = [0]
        for child in children_of.get(v, []):
            child_cost = dfs(child)
            new_len = len(my_cost) + len(child_cost) - 1
            new_cost = [None] * new_len
            for k1 in range(len(my_cost)):
                if my_cost[k1] is None:
                    continue
                # Option A: don't visit child (keep k1 food, pay 0 extra)
                if new_cost[k1] is None or new_cost[k1] > my_cost[k1]:
                    new_cost[k1] = my_cost[k1]
                # Option B: visit child with k2 food (pay 2 edge + child_cost[k2])
                for k2 in range(len(child_cost)):
                    if child_cost[k2] is None:
                        continue
                    total = k1 + k2
                    if total >= new_len:
                        continue
                    c = my_cost[k1] + 2 + child_cost[k2]
                    if new_cost[total] is None or new_cost[total] > c:
                        new_cost[total] = c
            my_cost = new_cost
        return my_cost

    return dfs(root)


def build_pocket_headers_with_cost_table(pruned, parent, main_corridor, food_set):
    """Group pruned cells by (attach, first_cell), build pocket tree per group,
    run knapsack DP. Returns one header per group with a `cost_table` field.

    Header dict fields:
      attach, first_cell, direction
      max_food: max food collectable in this pocket
      cost_table: list where cost_table[k] = min cost for k food (or None)
      food_count: alias for max_food (legacy)
      visit_cost: alias for cost_table[max_food] (legacy — full pocket visit)
      max_food_depth: legacy rough estimate (largest food depth from attach)
      tips: list of tip cells in this merged pocket
      all_cells: list of all pocket cells in this group
    """
    # Step 1: for each pruned cell, find its (attach, first_cell)
    first_cell_of = {}
    attach_of = {}
    for cell in pruned:
        cur = cell
        trace = [cur]
        attach = None
        first_cell = None
        while cur in parent:
            p = parent[cur]
            if p in main_corridor:
                attach = p
                first_cell = trace[-1]
                break
            trace.append(p)
            cur = p
        if attach is None:
            continue
        attach_of[cell] = attach
        first_cell_of[cell] = first_cell

    # Step 2: group cells by (attach, first_cell)
    groups = {}
    for cell, attach in attach_of.items():
        fc = first_cell_of[cell]
        groups.setdefault((attach, fc), []).append(cell)

    # Step 3: for each group, build tree + run DP
    headers = []
    for (attach, first_cell), cells in groups.items():
        # Build children map from parent (within this group)
        cells_set = set(cells)
        children_of = {attach: [first_cell]}
        for c in cells:
            children_of.setdefault(c, [])
        for c in cells:
            p = parent[c]
            if p == attach:
                continue  # c is first_cell, already child of attach
            if p in cells_set:
                children_of[p].append(c)

        # Run knapsack from attach (attach itself has no food contribution
        # in this view — attach is the X on main corridor; its food is
        # tracked separately via x_has_food).
        cost_list = _tree_knapsack(children_of, attach, food_set)
        max_food = sum(1 for c in cells if c in food_set)

        # Sanity: cost_list[0] should be 0, cost_list[max_food] should be finite.
        # Also filter: any cost_list[k] where k > max_food is invalid.
        trimmed = cost_list[:max_food + 1]

        # Max-depth-of-food (legacy fields)
        max_fd = 0
        for c in cells:
            if c in food_set:
                # Depth = parent chain length to attach
                d = 0
                cur = c
                while cur != attach:
                    d += 1
                    cur = parent[cur]
                if d > max_fd:
                    max_fd = d

        direction = (first_cell[0] - attach[0], first_cell[1] - attach[1])
        full_visit_cost = trimmed[max_food] if max_food > 0 else 0
        headers.append({
            'attach': attach,
            'first_cell': first_cell,
            'direction': direction,
            'max_food': max_food,
            'food_count': max_food,          # legacy alias
            'cost_table': trimmed,           # [0..max_food] — min cost for k food
            'visit_cost': full_visit_cost,   # legacy: full visit
            'max_food_depth': max_fd,        # legacy
            'tips': [c for c in cells if parent.get(c) is None or
                      (c in cells_set and not any(parent.get(other) == c for other in cells_set))],
            'all_cells': list(cells),
        })
    return headers


def merge_y_headers(headers_raw, food_set):
    """Merge headers sharing (attach, first_cell) — they share a trunk.

    Food count = |union(paths) ∩ food_set| to avoid double-counting trunk food
    when multiple branches share it.
    """
    groups = {}
    for h in headers_raw:
        key = (h['attach'], h['first_cell'])
        groups.setdefault(key, []).append(h)

    merged_headers = []
    for key, group in groups.items():
        if len(group) == 1:
            merged_headers.append(group[0])
            continue
        # Common-prefix of reversed paths → trunk depth
        rev_paths = [list(reversed(h['path'])) for h in group]
        i = 0
        while True:
            if i >= min(len(p) for p in rev_paths):
                break
            ref = rev_paths[0][i]
            if not all(p[i] == ref for p in rev_paths):
                break
            i += 1
        junction_depth = i
        combined_branch_cost = 0
        for h in group:
            branch_depth = max(h['max_food_depth'] - junction_depth, 0)
            combined_branch_cost += 2 * branch_depth
        combined_cost = 2 * junction_depth + combined_branch_cost
        # Union of all trace cells → food count
        union_cells = set()
        for h in group:
            union_cells.update(h['path'])
        combined_food = sum(1 for c in union_cells if c in food_set)
        direction = (key[1][0] - key[0][0], key[1][1] - key[0][1])
        merged_headers.append({
            'attach': key[0], 'first_cell': key[1], 'tip': None,
            'path': [], 'food_count': combined_food,
            'max_food_depth': max(h['max_food_depth'] for h in group),
            'visit_cost': combined_cost,
            'direction': direction,
            'merged_from': [h['tip'] for h in group],
        })
    return merged_headers


def plain_bfs(walls, start, allowed_cells, W, H):
    dists = {start: 0}
    q = deque([start])
    while q:
        p = q.popleft()
        x, y = p
        d = dists[p]
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            r = H - 1 - ny
            if walls[r][nx]:
                continue
            n = (nx, ny)
            if n not in allowed_cells:
                continue
            if n in dists:
                continue
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
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            r = H - 1 - ny
            if walls[r][nx]:
                continue
            n = (nx, ny)
            if n not in allowed_cells:
                continue
            if n in visited:
                continue
            visited.add(n)
            q.append((n, d + 1))
    return term_dists


def full_map_bfs(walls, start, W, H):
    """BFS through all non-wall cells. Returns dict[cell -> dist]."""
    dists = {start: 0}
    q = deque([start])
    while q:
        p = q.popleft()
        x, y = p
        d = dists[p]
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            r = H - 1 - ny
            if walls[r][nx]:
                continue
            n = (nx, ny)
            if n in dists:
                continue
            dists[n] = d + 1
            q.append(n)
    return dists


def build_x_edges(walls, x_positions, main_corridor, W, H):
    """X-X edges via distance-check: add iff blocked_dist == plain_dist."""
    edges = {}
    for src in x_positions:
        plain = plain_bfs(walls, src, main_corridor, W, H)
        blocked = blocked_bfs_with_terminators(walls, src, main_corridor, x_positions, W, H)
        for dst in x_positions:
            if dst == src:
                continue
            if dst not in blocked or dst not in plain:
                continue
            if blocked[dst] == plain[dst]:
                A, B = tuple(sorted([src, dst]))
                if (A, B) not in edges or edges[(A, B)] > blocked[dst]:
                    edges[(A, B)] = blocked[dst]
    return edges


def build_abstract_graph(walls, food_set, cap_set, W, H, include_red_entry=True):
    """Build abstract graph for blue-side orienteering.

    Returns dict:
      x_positions:  set of all X cells (blue X's + optional red-entry X's)
      blue_xs:      set of blue-side X's only (food/cap/attach)
      entry_xs:     set of red-entry X's (x=mid_col-1, main_corridor, include_red_entry only)
      headers:      list of (merged) pocket header dicts
      x_headers:    dict[X -> list of headers attached here]
      edges:        dict[(X_a, X_b) sorted -> distance]
      adj:          dict[X -> list of (neighbor_X, weight)]
      main_corridor: set of cells (both sides)
      blue_caps:    list of blue-side capsule cells
      blue_food:    list of blue-side food cells
      x_has_food:   dict[X -> bool] (X is on a blue-side food cell)
      mid_col:      int, map midline x
      W, H:         map dimensions
    """
    mid_col = W // 2
    cells, neighbors = build_cell_graph(walls, W, H)
    pruned, parent = find_pockets(cells, neighbors)
    main_corridor = cells - pruned

    # Use the new cost-table builder (tree-knapsack DP) — partial pocket visits.
    headers_all = build_pocket_headers_with_cost_table(
        pruned, parent, main_corridor, food_set)
    blue_headers = [h for h in headers_all
                     if h['attach'][0] >= mid_col and h['max_food'] > 0]

    blue_food = [f for f in food_set if f[0] >= mid_col]
    blue_caps = [c for c in cap_set if c[0] >= mid_col]

    blue_xs = set()
    for h in blue_headers:
        blue_xs.add(h['attach'])
    for f in blue_food:
        if f in main_corridor:
            blue_xs.add(f)
    for c in blue_caps:
        blue_xs.add(c)

    entry_xs = set()
    if include_red_entry:
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

    # Cap-in-pocket fix: if a cap landed in a pruned pocket cell, it has no
    # neighbors in main_corridor and would be unreachable by distance-check BFS.
    # Extend the allowed-cells set with the cap's pocket trace so the cap can
    # be reached as a waypoint. Note: this may modestly over-count time when
    # both the cap X and an overlapping pocket header are visited, but prevents
    # catastrophic "strategy infeasible" false-negatives.
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
    adj = {x: [] for x in x_positions}
    for (a, b), w in edges.items():
        adj[a].append((b, w))
        adj[b].append((a, w))

    x_has_food = {x: (x in food_set) for x in x_positions}

    return {
        'x_positions': x_positions,
        'blue_xs': blue_xs,
        'entry_xs': entry_xs,
        'headers': blue_headers,
        'x_headers': x_headers,
        'edges': edges,
        'adj': adj,
        'main_corridor': main_corridor,
        'blue_caps': blue_caps,
        'blue_food': blue_food,
        'x_has_food': x_has_food,
        'mid_col': mid_col,
        'W': W, 'H': H,
    }


def build_from_maze(maze_str, include_red_entry=True):
    """One-call builder from a capture.py maze string.

    Returns (graph_dict, walls, spawns). spawns is the {'1','2','3','4' -> (x,y)} dict.
    """
    walls, food_set, cap_set, spawns, (W, H) = parse_layout(maze_str)
    graph = build_abstract_graph(walls, food_set, cap_set, W, H, include_red_entry)
    return graph, walls, spawns


if __name__ == '__main__':
    import os
    import sys
    import random
    import time
    from pathlib import Path

    REPO = Path(__file__).resolve().parent.parent.parent
    MINICONTEST = REPO / "minicontest"
    os.chdir(str(MINICONTEST))
    sys.path.insert(0, str(MINICONTEST))
    import mazeGenerator as mg

    for seed in (1, 2, 3):
        random.seed(seed)
        maze_str = mg.generateMaze(seed)
        t0 = time.time()
        graph, walls, spawns = build_from_maze(maze_str)
        dt = (time.time() - t0) * 1000
        print(f"=== RANDOM{seed:02d} ===  build={dt:.1f} ms")
        print(f"  X total={len(graph['x_positions'])}  blue_xs={len(graph['blue_xs'])}"
              f"  entry_xs={len(graph['entry_xs'])}  headers={len(graph['headers'])}"
              f"  edges={len(graph['edges'])}")
        print(f"  blue_food={len(graph['blue_food'])}  blue_caps={len(graph['blue_caps'])}")

#!/usr/bin/env python3
"""Beam search over the abstract graph from abstract_graph.py.

Performance: all X's / headers stored as bitmask ints. Multi-source Dijkstra
from end_xs provides admissible pruning.

State: (cur_xi, vx_mask, vh_mask, time, food, depth_sum, plan_or_None)

Transitions:
  1. Move to adjacent X via edge: time += w; food +=1 if destination has food.
  2. Visit a header at current X: time += visit_cost; food += food_count.

Priority: (max food, max depth_sum, min time). Depth = max(X.x - mid_col, 0).

Termination: states landing at any X in end_xs are candidates.
"""
from __future__ import annotations
import heapq


def _multi_source_dijkstra(adj_idx, sources):
    dist = {s: 0 for s in sources}
    pq = [(0, s) for s in sources]
    heapq.heapify(pq)
    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, float('inf')):
            continue
        for (v, w) in adj_idx.get(u, []):
            nd = d + w
            if nd < dist.get(v, float('inf')):
                dist[v] = nd
                heapq.heappush(pq, (nd, v))
    return dist


def _is_cell(obj):
    return isinstance(obj, tuple) and len(obj) == 2 and isinstance(obj[0], int)


def get_x_index(graph):
    """Canonical X indexing — must match beam_search_abstract internal ordering."""
    x_list = sorted(graph['x_positions'])
    x_idx = {x: i for i, x in enumerate(x_list)}
    return x_list, x_idx


def beam_search_abstract(graph, start_xs_or_X, end_xs_or_X, budget,
                          forbidden_xs=None, forbidden_headers=None,
                          forbidden_xs_mask=0, forbidden_headers_mask=0,
                          beam=500, max_steps=32, return_plans=False):
    """Max food from any start X to any end X within budget (multi-source, multi-sink).

    Args:
      graph: dict from abstract_graph.build_abstract_graph
      start_xs_or_X: single cell or iterable of start X cells
      end_xs_or_X: single cell or iterable of end X cells
      budget: max time (moves)
      forbidden_xs: iterable of X cells whose food is already eaten (still traversable)
      forbidden_headers: iterable of header indices already visited
      forbidden_xs_mask: alt bitmask representation of forbidden X cells (OR'd with set)
      forbidden_headers_mask: alt bitmask representation of forbidden header indices
      beam: keep top-K states per step
      max_steps: max transitions
      return_plans: if True, include 'plan' in results

    Returns:
      list of dicts sorted best-first:
        {'food', 'time', 'visited_xs_mask', 'visited_headers_mask', 'start_X', 'end_X', optional 'plan'}
    """
    start_set = frozenset([start_xs_or_X]) if _is_cell(start_xs_or_X) else frozenset(start_xs_or_X)
    end_set = frozenset([end_xs_or_X]) if _is_cell(end_xs_or_X) else frozenset(end_xs_or_X)
    if not start_set or not end_set:
        return []
    xs = graph['x_positions']
    if not start_set.issubset(xs) or not end_set.issubset(xs):
        return []

    adj = graph['adj']
    x_has_food = graph['x_has_food']
    headers = graph['headers']
    mid_col = graph['mid_col']

    x_list, x_idx = get_x_index(graph)

    # Combine set + mask forbidden
    fx_mask = int(forbidden_xs_mask)
    for x in (forbidden_xs or []):
        if x in x_idx:
            fx_mask |= 1 << x_idx[x]
    fh_mask = int(forbidden_headers_mask)
    for hi in (forbidden_headers or []):
        fh_mask |= 1 << hi

    x_food_gain = [
        1 if (x_has_food.get(x_list[i], False) and not (fx_mask & (1 << i))) else 0
        for i in range(len(x_list))
    ]
    x_depth = [max(x_list[i][0] - mid_col, 0) for i in range(len(x_list))]

    # Headers index: attach X idx -> list of (hi, cost_table, depth).
    # cost_table is a list where cost_table[k] = min cost for k food, or None.
    # Beam branches into one transition per viable k (≥1, cost not None).
    x_header_list = {}
    for hi, h in enumerate(headers):
        if fh_mask & (1 << hi):
            continue
        xi = x_idx[h['attach']]
        ct = h.get('cost_table')
        if ct is None:
            # Legacy fallback: single (food_count, visit_cost) entry.
            ct = [0, None]
            ct = [None] * (h['food_count'] + 1)
            ct[0] = 0
            ct[h['food_count']] = h['visit_cost']
        x_header_list.setdefault(xi, []).append(
            (hi, ct, x_depth[xi])
        )

    adj_idx = {x_idx[x]: [(x_idx[nb], w) for (nb, w) in lst] for x, lst in adj.items()}

    end_idx_set = {x_idx[e] for e in end_set}
    start_idx_list = [x_idx[s] for s in start_set]

    dist_to_end = _multi_source_dijkstra(adj_idx, end_idx_set)

    # State: (cur_idx, vx_mask, vh_mask, time, food, depth_sum, start_idx, plan)
    states = []
    found = []
    seen_init = {}
    for si in start_idx_list:
        fg = x_food_gain[si]
        vx = 1 << si
        f = fg
        ds = x_depth[si] if fg else 0
        plan = (('start', x_list[si]),) if return_plans else None
        state = (si, vx, 0, 0, f, ds, si, plan)
        key = (si, vx, 0)
        if key in seen_init:
            continue
        seen_init[key] = 0
        states.append(state)
        if si in end_idx_set:
            found.append(state)

    for _ in range(max_steps):
        if not states:
            break
        next_states = []
        seen = {}

        for state in states:
            ci, vx, vh, t, f, ds, si_start, plan = state

            # Option A: visit headers at ci. Each header has a cost_table
            # giving min cost for each food count k. Branch into one transition
            # per viable (k, cost) pair (k >= 1, cost not None). Dedup key
            # includes food to keep Pareto-distinct partial-visit options.
            for (hi, ct, hd) in x_header_list.get(ci, []):
                hbit = 1 << hi
                if vh & hbit:
                    continue
                for k in range(1, len(ct)):
                    hc = ct[k]
                    if hc is None:
                        continue
                    new_t = t + hc
                    if new_t > budget:
                        continue
                    d_end = dist_to_end.get(ci)
                    if d_end is None or new_t + d_end > budget:
                        continue
                    new_f = f + k
                    new_vh = vh | hbit
                    new_ds = ds + hd * k
                    new_plan = (plan + (('header', hi, k),)) if plan is not None else None
                    new_state = (ci, vx, new_vh, new_t, new_f, new_ds, si_start, new_plan)
                    if ci in end_idx_set:
                        found.append(new_state)
                    key = (ci, vx, new_vh, si_start, new_f)
                    prev = seen.get(key)
                    if prev is not None and prev <= new_t:
                        continue
                    seen[key] = new_t
                    next_states.append(new_state)

            # Option B: move to adjacent X. Allow revisit for navigation —
            # food gain only on first visit. This lets A/B traverse loop
            # chambers (where non-tree cycles exist) by walking back through
            # the same neck. Dedup by (ni, new_vx, ...) with seen-time prevents
            # infinite loops.
            for (ni, w) in adj_idx.get(ci, []):
                nbit = 1 << ni
                is_first = not (vx & nbit)
                new_t = t + w
                if new_t > budget:
                    continue
                d_end = dist_to_end.get(ni)
                if d_end is None or new_t + d_end > budget:
                    continue
                fg = x_food_gain[ni] if is_first else 0
                new_f = f + fg
                new_vx = vx | nbit if is_first else vx
                new_ds = ds + (x_depth[ni] if fg else 0)
                new_plan = (plan + (('move', x_list[ni]),)) if plan is not None else None
                new_state = (ni, new_vx, vh, new_t, new_f, new_ds, si_start, new_plan)
                if ni in end_idx_set:
                    found.append(new_state)
                key = (ni, new_vx, vh, si_start, new_f)
                prev = seen.get(key)
                if prev is not None and prev <= new_t:
                    continue
                seen[key] = new_t
                next_states.append(new_state)

        next_states.sort(key=lambda s: (-s[4], -s[5], s[3]))
        states = next_states[:beam]

    found.sort(key=lambda s: (-s[4], -s[5], s[3]))
    seen_keys = set()
    result = []
    for st in found:
        ci, vx, vh, t, f, ds, si_start, plan = st
        key = (f, t, vx, vh, si_start)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        entry = {
            'food': f, 'time': t,
            'visited_xs_mask': vx, 'visited_headers_mask': vh,
            'start_X': x_list[si_start],
            'end_X': x_list[ci],
        }
        if plan is not None:
            entry['plan'] = plan
        result.append(entry)
    return result


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
    sys.path.insert(0, str(REPO / "experiments" / "rc_tempo"))
    import mazeGenerator as mg
    from abstract_graph import build_from_maze, full_map_bfs

    for seed in (1, 2, 3):
        random.seed(seed)
        maze_str = mg.generateMaze(seed)
        graph, walls, spawns = build_from_maze(maze_str)

        entry_xs = graph['entry_xs']
        blue_caps = graph['blue_caps']
        spawn_a = spawns['1']
        a_dists = full_map_bfs(walls, spawn_a, graph['W'], graph['H'])
        cap_sorted = sorted(blue_caps, key=lambda c: a_dists.get(c, 9999))
        cap1, cap2 = cap_sorted[0], cap_sorted[1]

        # Single beam search from cap1 to ANY entry X
        t0 = time.time()
        res = beam_search_abstract(graph, cap1, entry_xs, budget=79, beam=500)
        dt = (time.time() - t0) * 1000
        best = res[0] if res else {'food': 0, 'time': 0, 'end_X': None}
        print(f"RANDOM{seed:02d}  cap1={cap1}  beam → food={best['food']:2}  "
              f"time={best['time']:2}  end_X={best['end_X']}  wall={dt:.1f} ms")

        t0 = time.time()
        res = beam_search_abstract(graph, cap2, entry_xs, budget=79, beam=500)
        dt = (time.time() - t0) * 1000
        best = res[0] if res else {'food': 0, 'time': 0, 'end_X': None}
        print(f"          cap2={cap2}  beam → food={best['food']:2}  "
              f"time={best['time']:2}  end_X={best['end_X']}  wall={dt:.1f} ms")

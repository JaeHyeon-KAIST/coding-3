#!/usr/bin/env python3
"""Pre-extract per-layout fixtures for rc-tempo risk map / DP iteration.

Output: experiments/artifacts/rc_tempo/fixtures/{layout}.pkl — dict of:
    walls (bool grid as tuple of tuples)
    width, height, midline_x
    red_home_cells, blue_home_cells
    red_target_foods, blue_target_foods
    red_target_capsules, blue_target_capsules
    distances: {(cell_a, cell_b): int} all-pairs (both team food+capsule+home cells)
    dead_end_depth: {cell: int}  (0 = on cycle, >=1 = peel depth)
    articulation_points: set[(x,y)]
    food_ap_count_to_home: {food_cell: int}  — APs on shortest path food→nearest_home
    isolated_food: set[(x,y)]  — foods with no other food within 5 maze-cells

Parallel: multiprocessing.Pool over 12 layouts.

Usage:
    .venv/bin/python experiments/rc_tempo/extract_fixtures.py
"""
import glob
import os
import pickle
import sys
import time
from collections import deque
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
MINICONTEST = os.path.join(REPO, 'minicontest')
LAYOUTS_DIR = os.path.join(MINICONTEST, 'layouts')
OUT_DIR = os.path.join(REPO, 'experiments', 'artifacts', 'rc_tempo', 'fixtures')

sys.path.insert(0, MINICONTEST)

ISOLATED_RADIUS = 5


def _neighbors(walls, x, y):
    w, h = walls.width, walls.height
    out = []
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h and not walls[nx][ny]:
            out.append((nx, ny))
    return out


def _walls_to_tuple(walls):
    return tuple(tuple(walls[x][y] for y in range(walls.height)) for x in range(walls.width))


def compute_dead_end_depth(walls, cells, nbrs):
    """Onion-peel. depth[c]=0 means c is on a cycle; >=1 = layers stripped from degree-1."""
    degree = {c: len(nbrs[c]) for c in cells}
    depth = {c: 0 for c in cells}
    queue = deque([c for c in cells if degree[c] == 1])
    removed = set(queue)
    level = 1
    while queue:
        next_q = deque()
        while queue:
            c = queue.popleft()
            depth[c] = level
            for n in nbrs[c]:
                if n in removed:
                    continue
                degree[n] -= 1
                if degree[n] == 1:
                    next_q.append(n)
                    removed.add(n)
        queue = next_q
        level += 1
    return depth


def find_articulation_points(cells, nbrs):
    """Tarjan iterative. Returns set of APs."""
    aps = set()
    disc = {}
    low = {}
    parent = {}
    timer = [0]

    def dfs(root):
        stack = [(root, iter(nbrs[root]), 0)]  # (node, neighbor_iter, children_count)
        disc[root] = low[root] = timer[0]
        timer[0] += 1
        parent[root] = None
        while stack:
            node, it, children = stack[-1]
            advanced = False
            for nb in it:
                if nb not in disc:
                    parent[nb] = node
                    disc[nb] = low[nb] = timer[0]
                    timer[0] += 1
                    stack[-1] = (node, it, children + 1)
                    stack.append((nb, iter(nbrs[nb]), 0))
                    advanced = True
                    break
                elif nb != parent[node]:
                    low[node] = min(low[node], disc[nb])
            if not advanced:
                stack.pop()
                if stack:
                    par = stack[-1][0]
                    low[par] = min(low[par], low[node])
                    # is par AP via node?
                    if parent[par] is not None and low[node] >= disc[par]:
                        aps.add(par)
                else:
                    # node was root
                    final_children = stack[-1][2] if stack else children
                    # actually we popped, so re-examine: root AP if children >= 2
                    if children >= 2:
                        aps.add(node)

    for c in cells:
        if c not in disc:
            dfs(c)
    return aps


def bfs_path(src, dsts_set, nbrs):
    """BFS from src; return (cell_reached_in_dsts, path_list)."""
    visited = {src: None}
    q = deque([src])
    target = None
    while q:
        u = q.popleft()
        if u in dsts_set:
            target = u
            break
        for v in nbrs[u]:
            if v not in visited:
                visited[v] = u
                q.append(v)
    if target is None:
        return None, []
    path = []
    cur = target
    while cur is not None:
        path.append(cur)
        cur = visited[cur]
    path.reverse()
    return target, path


def all_pairs_distances(sources, nbrs):
    """BFS from each source. Returns {(s, t): dist} for t reachable from s."""
    out = {}
    for s in sources:
        dist = {s: 0}
        q = deque([s])
        while q:
            u = q.popleft()
            du = dist[u]
            for v in nbrs[u]:
                if v not in dist:
                    dist[v] = du + 1
                    q.append(v)
        for t, d in dist.items():
            out[(s, t)] = d
    return out


def extract_one(layout_name):
    """Parse one layout file, compute fixture, pickle to OUT_DIR."""
    import layout as layout_module

    t0 = time.perf_counter()
    lay_path = os.path.join(LAYOUTS_DIR, layout_name)
    with open(lay_path) as f:
        lines = [line.rstrip() for line in f if line.rstrip()]
    lay = layout_module.Layout(lines)

    walls = lay.walls
    food_grid = lay.food
    capsules = list(lay.capsules)
    w, h = walls.width, walls.height
    midline_x = w // 2

    # Agent start positions: layout.agentPositions = [(isRed, (x, y)), ...] after sort by index
    # Index mapping: 0=red0, 1=blue1, 2=red2, 3=blue3
    agent_starts = [pos for _, pos in lay.agentPositions]
    red_starts = [pos for i, (_, pos) in enumerate(lay.agentPositions) if i in (0, 2)]
    blue_starts = [pos for i, (_, pos) in enumerate(lay.agentPositions) if i in (1, 3)]

    cells = [(x, y) for x in range(w) for y in range(h) if not walls[x][y]]
    nbrs = {c: _neighbors(walls, c[0], c[1]) for c in cells}

    red_target_foods = [(x, y) for x in range(midline_x, w) for y in range(h) if food_grid[x][y]]
    blue_target_foods = [(x, y) for x in range(midline_x) for y in range(h) if food_grid[x][y]]
    red_target_capsules = [c for c in capsules if c[0] >= midline_x]
    blue_target_capsules = [c for c in capsules if c[0] < midline_x]

    red_home_cells = [(midline_x - 1, y) for y in range(h) if not walls[midline_x - 1][y]]
    blue_home_cells = [(midline_x, y) for y in range(h) if not walls[midline_x][y]]

    # Sources for all-pairs: every food, every home cell, every capsule, every agent start
    sources = (set(red_target_foods) | set(blue_target_foods)
               | set(red_home_cells) | set(blue_home_cells)
               | set(capsules) | set(agent_starts))
    t_setup = time.perf_counter() - t0

    t0 = time.perf_counter()
    distances = all_pairs_distances(sources, nbrs)
    t_dist = time.perf_counter() - t0

    t0 = time.perf_counter()
    dead_end_depth = compute_dead_end_depth(walls, cells, nbrs)
    t_de = time.perf_counter() - t0

    t0 = time.perf_counter()
    articulation_points = find_articulation_points(cells, nbrs)
    t_ap = time.perf_counter() - t0

    # AP count on path to nearest home (per team perspective)
    t0 = time.perf_counter()
    red_home_set = set(red_home_cells)
    blue_home_set = set(blue_home_cells)
    food_ap_count_to_home_red = {}
    for f in red_target_foods:
        _, path = bfs_path(f, red_home_set, nbrs)
        food_ap_count_to_home_red[f] = sum(1 for c in path[1:-1] if c in articulation_points)
    food_ap_count_to_home_blue = {}
    for f in blue_target_foods:
        _, path = bfs_path(f, blue_home_set, nbrs)
        food_ap_count_to_home_blue[f] = sum(1 for c in path[1:-1] if c in articulation_points)
    t_ap_path = time.perf_counter() - t0

    # Isolated food (no other food within ISOLATED_RADIUS maze-cells)
    def isolated_set(foods):
        food_set = set(foods)
        out = set()
        for f in foods:
            others = food_set - {f}
            is_iso = True
            for o in others:
                d = distances.get((f, o))
                if d is not None and d <= ISOLATED_RADIUS:
                    is_iso = False
                    break
            if is_iso:
                out.add(f)
        return out

    red_isolated = isolated_set(red_target_foods)
    blue_isolated = isolated_set(blue_target_foods)

    t_total = time.perf_counter() - t0

    fixture = {
        'layout_name': layout_name,
        'width': w,
        'height': h,
        'midline_x': midline_x,
        'walls': _walls_to_tuple(walls),
        'agent_starts': agent_starts,
        'red_starts': red_starts,
        'blue_starts': blue_starts,
        'red_target_foods': red_target_foods,
        'blue_target_foods': blue_target_foods,
        'red_target_capsules': red_target_capsules,
        'blue_target_capsules': blue_target_capsules,
        'red_home_cells': red_home_cells,
        'blue_home_cells': blue_home_cells,
        'distances': distances,
        'dead_end_depth': dead_end_depth,
        'articulation_points': articulation_points,
        'food_ap_count_to_home_red': food_ap_count_to_home_red,
        'food_ap_count_to_home_blue': food_ap_count_to_home_blue,
        'red_isolated_foods': red_isolated,
        'blue_isolated_foods': blue_isolated,
        'timing': {
            'setup': round(t_setup, 3),
            'distances': round(t_dist, 3),
            'dead_end': round(t_de, 3),
            'articulation': round(t_ap, 3),
            'ap_path': round(t_ap_path, 3),
        },
    }

    out_path = os.path.join(OUT_DIR, layout_name.replace('.lay', '') + '.pkl')
    with open(out_path, 'wb') as f:
        pickle.dump(fixture, f, protocol=pickle.HIGHEST_PROTOCOL)

    return {
        'layout': layout_name,
        'size': f"{w}x{h}",
        'n_cells': len(cells),
        'n_red_food': len(red_target_foods),
        'n_blue_food': len(blue_target_foods),
        'n_red_caps': len(red_target_capsules),
        'n_blue_caps': len(blue_target_capsules),
        'n_ap': len(articulation_points),
        'max_de_depth': max(dead_end_depth.values()) if dead_end_depth else 0,
        'n_red_iso': len(red_isolated),
        't_dist': fixture['timing']['distances'],
        't_ap': fixture['timing']['articulation'],
        't_total_sec': round(sum(fixture['timing'].values()), 3),
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_layouts = sorted(os.path.basename(p) for p in glob.glob(os.path.join(LAYOUTS_DIR, '*.lay')))
    print(f"Extracting {len(all_layouts)} layouts via Pool(12)...", flush=True)

    t0 = time.perf_counter()
    with Pool(12) as pool:
        results = pool.map(extract_one, all_layouts)
    wall = time.perf_counter() - t0

    print(f"\nWall: {wall:.2f}s (sum of per-layout: {sum(r['t_total_sec'] for r in results):.2f}s)")
    print("=" * 120)
    hdr = f"{'Layout':<22} {'Size':<8} {'Cells':<6} {'Rfood':<6} {'Bfood':<6} {'RCap':<5} {'BCap':<5} {'APs':<5} {'MaxDE':<6} {'RIso':<5} {'t_dist':<7} {'t_ap':<7} {'t_tot':<7}"
    print(hdr)
    print("-" * 120)
    for r in results:
        print(f"{r['layout']:<22} {r['size']:<8} {r['n_cells']:<6} "
              f"{r['n_red_food']:<6} {r['n_blue_food']:<6} "
              f"{r['n_red_caps']:<5} {r['n_blue_caps']:<5} "
              f"{r['n_ap']:<5} {r['max_de_depth']:<6} {r['n_red_iso']:<5} "
              f"{r['t_dist']:<7} {r['t_ap']:<7} {r['t_total_sec']:<7}")

    print(f"\nOutput: {OUT_DIR}")


if __name__ == '__main__':
    main()

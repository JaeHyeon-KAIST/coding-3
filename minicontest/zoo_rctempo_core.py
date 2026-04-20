# zoo_rctempo_core.py
# -------------------
# Pure-stdlib topology + orienteering DP core for rc-tempo (β / γ).
#
# Design: all functions accept plain data (walls grid from gameState,
# food/capsule lists, distancer) and return dicts. NO dependencies on
# experiments/* so the file is submission-flatten-ready.
#
# Used by:
#   - minicontest/zoo_reflex_rc_tempo_beta.py (runtime)
#   - minicontest/zoo_reflex_rc_tempo_gamma.py (runtime, Phase 4+)
#   - experiments/rc_tempo/*.py (offline analysis, imports via sys.path hack)

from __future__ import annotations

from collections import deque


# ---------------------------------------------------------------------------
# 1. Topology primitives (dead-end depth, articulation, all-pairs distance)
# ---------------------------------------------------------------------------

def _open_cells(walls):
    w, h = walls.width, walls.height
    return [(x, y) for x in range(w) for y in range(h) if not walls[x][y]]


def _neighbors(walls, cell):
    x, y = cell
    w, h = walls.width, walls.height
    out = []
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < w and 0 <= ny < h and not walls[nx][ny]:
            out.append((nx, ny))
    return out


def compute_dead_end_depth(walls):
    """Onion-peel dead-end depth. depth[c]=0 → on cycle, >=1 → peel level."""
    cells = _open_cells(walls)
    nbrs = {c: _neighbors(walls, c) for c in cells}
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


def find_articulation_points(walls):
    """Tarjan iterative. Returns frozenset of cells that are APs."""
    cells = _open_cells(walls)
    nbrs = {c: _neighbors(walls, c) for c in cells}
    aps = set()
    disc = {}
    low = {}
    parent = {}
    timer = [0]

    for root in cells:
        if root in disc:
            continue
        stack = [(root, iter(nbrs[root]), 0)]
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
                    if parent[par] is not None and low[node] >= disc[par]:
                        aps.add(par)
                else:
                    if children >= 2:
                        aps.add(node)
    return frozenset(aps)


def bfs_distances_from(walls, src, blocked=None):
    """Single-source BFS. Returns {cell: dist}."""
    blocked = blocked or set()
    if src in blocked:
        return {}
    visited = {src: 0}
    q = deque([src])
    while q:
        u = q.popleft()
        for n in _neighbors(walls, u):
            if n in blocked or n in visited:
                continue
            visited[n] = visited[u] + 1
            q.append(n)
    return visited


def bfs_path(walls, src, dsts_set, blocked=None):
    """Multi-target BFS from src. Returns (first_dst_reached, path_list, dist)."""
    blocked = blocked or set()
    if src in blocked:
        return None, [], None
    parent = {src: None}
    q = deque([src])
    target = None
    while q:
        u = q.popleft()
        if u in dsts_set:
            target = u
            break
        for n in _neighbors(walls, u):
            if n in blocked or n in parent:
                continue
            parent[n] = u
            q.append(n)
    if target is None:
        return None, [], None
    path = []
    cur = target
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    path.reverse()
    return target, path, len(path) - 1


# ---------------------------------------------------------------------------
# 2. Capsule approach safety analysis
# ---------------------------------------------------------------------------

def analyze_capsule_safety(walls, capsule, home_cells, aps, depth_limit=15):
    """Returns dict with:
      depth (dist home→capsule), path_aps (AP on shortest path),
      imm_aps (AP adjacent to capsule), chokepoints (AP whose removal disconnects),
      node_conn (1 if chokepoint exists else 2), safe (bool).
    """
    home_set = set(home_cells)
    target, path, depth = bfs_path(walls, capsule, home_set)
    if target is None:
        return {'safe': False, 'depth': None, 'path_aps': [],
                'imm_aps': [], 'chokepoints': [], 'node_conn': 0}
    path_aps = [c for c in path[1:-1] if c in aps]
    imm = []
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        n = (capsule[0] + dx, capsule[1] + dy)
        if 0 <= n[0] < walls.width and 0 <= n[1] < walls.height and not walls[n[0]][n[1]]:
            if n in aps:
                imm.append(n)
    chokepoints = []
    midline_x = walls.width // 2
    enemy_aps = [ap for ap in aps if ap[0] >= midline_x and ap != capsule]
    for ap in enemy_aps:
        _, _, d = bfs_path(walls, capsule, home_set, blocked={ap})
        if d is None:
            chokepoints.append(ap)
    node_conn = 1 if chokepoints else 2
    safe = (node_conn >= 2) and (depth <= depth_limit)
    return {
        'safe': safe, 'depth': depth, 'path_aps': path_aps,
        'imm_aps': imm, 'chokepoints': chokepoints, 'node_conn': node_conn,
        'shortest_path': path,
    }


# ---------------------------------------------------------------------------
# 3. Risk scoring
# ---------------------------------------------------------------------------

DEFAULT_RISK_WEIGHTS = {
    'w_de': 3.0,
    'w_ap': 2.0,
    'w_dh': 0.5,
    'w_vor': 5.0,
    'w_iso': 2.0,
}


def compute_risk_map(walls, foods, home_cells, enemy_home_cells, aps, dead_end_depth,
                     distance_fn, weights=None):
    """risk(f) = w_de*de_depth + w_ap*AP_count_on_path + w_dh*dist_to_home/10
              + w_vor*low_voronoi_flag + w_iso*isolated_flag
    distance_fn(a, b) -> int (provided by caller, typically apsp lookup).
    Returns {food_cell: risk_score}.
    """
    w = dict(DEFAULT_RISK_WEIGHTS)
    if weights:
        w.update(weights)
    food_set = set(foods)
    home_set = set(home_cells)
    en_home_set = set(enemy_home_cells)

    # AP count on shortest path to home (per food)
    ap_counts = {}
    for f in foods:
        _, path, _ = bfs_path(walls, f, home_set)
        ap_counts[f] = sum(1 for c in path[1:-1] if c in aps)

    # Isolated foods: no other food within 5 cells
    isolated = set()
    for f in foods:
        is_iso = True
        for o in food_set:
            if o == f:
                continue
            d = distance_fn(f, o)
            if d is not None and d <= 5:
                is_iso = False
                break
        if is_iso:
            isolated.add(f)

    # Voronoi margin: positive = closer to enemy home
    vor = {}
    for f in foods:
        d_me = min(distance_fn(f, h) for h in home_set) if home_set else 0
        d_en = min(distance_fn(f, h) for h in en_home_set) if en_home_set else 0
        vor[f] = d_me - d_en

    # Dist to home
    dh = {f: min(distance_fn(f, h) for h in home_set) for f in foods}

    scores = {}
    for f in foods:
        de = dead_end_depth.get(f, 0)
        ap = ap_counts[f]
        score = (w['w_de'] * de
                 + w['w_ap'] * ap
                 + w['w_dh'] * (dh[f] / 10.0)
                 + w['w_vor'] * (1 if vor[f] >= 2 else 0)
                 + w['w_iso'] * (1 if f in isolated else 0))
        scores[f] = score
    return scores, {'ap_counts': ap_counts, 'isolated': isolated, 'vor': vor, 'dh': dh}


# ---------------------------------------------------------------------------
# 4. Orienteering DP (weighted bitmask)
# ---------------------------------------------------------------------------

def orienteering_dp(start_cell, foods, home_cells, distance_fn, budget=40,
                     objective='risk', risk_scores=None):
    """Bitmask DP orienteering.

    start_cell: where we begin (capsule for A, midline for B)
    foods: list of candidate food cells
    home_cells: return destinations
    distance_fn: (a, b) -> int
    budget: max total moves
    objective: 'count' (max food count) or 'risk' (max risk sum)
    risk_scores: {food_cell: score} used when objective='risk'

    Returns: {'best_score': ..., 'n_food': ..., 'total_moves': ...,
              'route': [cells], 'food_order': [cells]}.
    """
    n = len(foods)
    INF = 10 ** 9
    if not home_cells:
        return {'best_score': 0, 'n_food': 0, 'total_moves': 0,
                'route': [start_cell], 'food_order': []}
    best_home_from_start = min(home_cells, key=lambda h: distance_fn(start_cell, h))
    base_total = distance_fn(start_cell, best_home_from_start)
    if n == 0:
        return {'best_score': 0, 'n_food': 0, 'total_moves': base_total,
                'route': [start_cell, best_home_from_start], 'food_order': []}

    d_cap = [distance_fn(start_cell, foods[i]) for i in range(n)]
    d_ff = [[distance_fn(foods[i], foods[j]) for j in range(n)] for i in range(n)]
    d_fh = [(min(distance_fn(foods[i], h) for h in home_cells),
             min(home_cells, key=lambda h, i=i: distance_fn(foods[i], h)))
            for i in range(n)]

    if risk_scores is None:
        risk_scores = {f: 1.0 for f in foods}
    risk_arr = [risk_scores.get(foods[i], 0.0) for i in range(n)]

    def score_mask(mask):
        if objective == 'count':
            return bin(mask).count('1')
        total = 0.0
        i = 0
        m = mask
        while m:
            if m & 1:
                total += risk_arr[i]
            m >>= 1
            i += 1
        return total

    dp = {(-1, 0): (0, None)}
    best_score = 0
    best_state = (-1, 0)
    best_total = base_total

    frontier = deque([(-1, 0)])
    while frontier:
        pos, mask = frontier.popleft()
        cur_dist, _ = dp[(pos, mask)]

        if pos == -1:
            to_home_cost = base_total
        else:
            to_home_cost = d_fh[pos][0]
        total_if_end = cur_dist + to_home_cost
        if total_if_end <= budget and mask != 0:
            sc = score_mask(mask)
            if sc > best_score or (sc == best_score and total_if_end < best_total):
                best_score = sc
                best_state = (pos, mask)
                best_total = total_if_end

        for i in range(n):
            if mask & (1 << i):
                continue
            new_mask = mask | (1 << i)
            step = d_cap[i] if pos == -1 else d_ff[pos][i]
            new_dist = cur_dist + step
            if new_dist + d_fh[i][0] > budget:
                continue
            key = (i, new_mask)
            if new_dist < dp.get(key, (INF, None))[0]:
                dp[key] = (new_dist, (pos, mask))
                frontier.append(key)

    food_order = []
    if best_state != (-1, 0):
        cur = best_state
        chain = [cur]
        while True:
            _, par = dp[cur]
            if par is None:
                break
            chain.append(par)
            cur = par
        chain.reverse()
        food_order = [foods[s[0]] for s in chain if s[0] != -1]

    if food_order:
        home_final = min(home_cells, key=lambda h: distance_fn(food_order[-1], h))
        route = [start_cell] + food_order + [home_final]
    else:
        route = [start_cell, best_home_from_start]

    return {
        'best_score': best_score,
        'n_food': len(food_order),
        'total_moves': best_total,
        'route': route,
        'food_order': food_order,
    }


# ---------------------------------------------------------------------------
# 5. Partition + plan precompute
# ---------------------------------------------------------------------------

def partition_y_split(foods, height):
    mid = height / 2
    a = [f for f in foods if f[1] >= mid]
    b = [f for f in foods if f[1] < mid]
    return a, b


def partition_voronoi(foods, a_start, b_start, distance_fn):
    a_f, b_f = [], []
    for f in foods:
        da = distance_fn(a_start, f)
        db = distance_fn(b_start, f)
        if da <= db:
            a_f.append(f)
        else:
            b_f.append(f)
    return a_f, b_f


def pick_b_start(home_cells, b_foods, distance_fn):
    if not b_foods:
        return home_cells[len(home_cells) // 2]
    best, best_cost = home_cells[0], 10 ** 9
    for h in home_cells:
        cost = sum(distance_fn(h, f) for f in b_foods)
        if cost < best_cost:
            best_cost = cost
            best = h
    return best


def entry_orienteering_dp(start_cell, foods, capsule, distance_fn, budget,
                            objective='count'):
    """Entry-phase orienteering: start → capsule, picking up food along the way.

    Unlike the scared-phase DP (which returns to home), entry DP MUST end at capsule.
    Budget limits total path length. Max food count (detour food pickup).

    Returns: same shape as orienteering_dp.
    """
    n = len(foods)
    INF = 10 ** 9
    base_total = distance_fn(start_cell, capsule)
    if n == 0:
        return {'best_score': 0, 'n_food': 0, 'total_moves': base_total,
                'route': [start_cell, capsule], 'food_order': []}

    d_start = [distance_fn(start_cell, foods[i]) for i in range(n)]
    d_ff = [[distance_fn(foods[i], foods[j]) for j in range(n)] for i in range(n)]
    d_fc = [distance_fn(foods[i], capsule) for i in range(n)]

    def score_mask(mask):
        if objective == 'count':
            return bin(mask).count('1')
        return bin(mask).count('1')  # count only for entry

    dp = {(-1, 0): (0, None)}
    best_score = 0
    best_state = (-1, 0)
    best_total = base_total

    frontier = deque([(-1, 0)])
    while frontier:
        pos, mask = frontier.popleft()
        cur_dist, _ = dp[(pos, mask)]
        if pos == -1:
            to_cap = base_total
        else:
            to_cap = d_fc[pos]
        total_if_end = cur_dist + to_cap
        if total_if_end <= budget:
            sc = score_mask(mask)
            if sc > best_score or (sc == best_score and total_if_end < best_total):
                best_score = sc
                best_state = (pos, mask)
                best_total = total_if_end

        for i in range(n):
            if mask & (1 << i):
                continue
            new_mask = mask | (1 << i)
            step = d_start[i] if pos == -1 else d_ff[pos][i]
            new_dist = cur_dist + step
            if new_dist + d_fc[i] > budget:
                continue
            key = (i, new_mask)
            if new_dist < dp.get(key, (INF, None))[0]:
                dp[key] = (new_dist, (pos, mask))
                frontier.append(key)

    food_order = []
    if best_state != (-1, 0):
        cur = best_state
        chain = [cur]
        while True:
            _, par = dp[cur]
            if par is None:
                break
            chain.append(par)
            cur = par
        chain.reverse()
        food_order = [foods[s[0]] for s in chain if s[0] != -1]

    route = [start_cell] + food_order + [capsule]
    return {
        'best_score': best_score,
        'n_food': len(food_order),
        'total_moves': best_total,
        'route': route,
        'food_order': food_order,
    }


def make_plans(walls, foods, home_cells, enemy_home_cells, capsule, aps,
                dead_end_depth, distance_fn, b_budget_bonus=0, weights=None):
    """Precompute top-K (A, B) plan candidates.

    Returns list of dicts with:
      strategy (partition name), b_start, a_foods, b_foods,
      a_res (DP result), b_res, total_food, total_risk.
    """
    risk_scores, _ = compute_risk_map(
        walls, foods, home_cells, enemy_home_cells, aps, dead_end_depth, distance_fn, weights)

    plans = []

    for strat in ('y_split', 'voronoi'):
        # partition
        if strat == 'y_split':
            a_foods, b_foods = partition_y_split(foods, walls.height)
            b_start = pick_b_start(home_cells, b_foods, distance_fn)
        else:
            prelim = pick_b_start(home_cells, foods, distance_fn)
            a_foods, b_foods = partition_voronoi(foods, capsule, prelim, distance_fn)
            b_start = pick_b_start(home_cells, b_foods, distance_fn)
            a_foods, b_foods = partition_voronoi(foods, capsule, b_start, distance_fn)

        a_res = orienteering_dp(capsule, a_foods, home_cells, distance_fn,
                                budget=40, objective='risk', risk_scores=risk_scores)
        b_res = orienteering_dp(b_start, b_foods, home_cells, distance_fn,
                                budget=40 + b_budget_bonus, objective='count', risk_scores=risk_scores)
        plans.append({
            'strategy': strat,
            'b_start': b_start,
            'a_foods': a_foods,
            'b_foods': b_foods,
            'a_res': a_res,
            'b_res': b_res,
            'total_food': a_res['n_food'] + b_res['n_food'],
            'total_risk': a_res['best_score'] + b_res['best_score'],
        })

    # Rank: total_food desc, then total_risk desc, then a_moves asc
    plans.sort(key=lambda p: (-p['total_food'], -p['total_risk'],
                               p['a_res']['total_moves']))
    return plans

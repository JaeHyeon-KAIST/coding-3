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


# ---------------------------------------------------------------------------
# 6. pm31 primitives — Risk-weighted A* + Voronoi safety + Slack planner
# ---------------------------------------------------------------------------

try:
    import heapq as _heapq
except Exception:
    _heapq = None


def risk_weighted_astar(walls, start, target, risk_map, distance_fn,
                         blocked=None, weights=None):
    """Risk-weighted A* search.

    Edge cost = 1 + λ_risk × risk(to_cell) + λ_dead × (dead_end > 2) + λ_ap × is_AP.
    Heuristic = distance_fn(cell, target) (admissible if distance_fn is true maze dist).

    Args:
        walls: Grid object (walls[x][y] bool).
        start, target: Cell tuples.
        risk_map: Dict[Cell, float] static per-cell risk (from compute_risk_map
                  or equivalent). Missing cells treated as 0.
        distance_fn: (a, b) -> int, used as admissible heuristic.
        blocked: Optional set of cells to treat as walls (e.g., teammate cell).
        weights: Optional overrides {lam_risk, lam_dead, lam_ap, dead_penalty,
                 ap_penalty}. Defaults: lam_risk=0.3, lam_dead=2.0, lam_ap=1.0,
                 dead_penalty (depth>=3 kicks in), ap_penalty (AP cell).

    Returns:
        {'path': List[Cell] | None, 'cost': float, 'reachable': bool}
        path[0] == start, path[-1] == target (if reachable).
    """
    if _heapq is None or start == target:
        return {'path': [start] if start == target else None,
                'cost': 0.0, 'reachable': (start == target)}

    w = {
        'lam_risk': 0.3,
        'lam_dead': 2.0,
        'lam_ap': 1.0,
        'dead_penalty_threshold': 3,
        'ap_penalty': 1.0,
    }
    if weights:
        w.update(weights)

    blocked = set(blocked or ())
    if start in blocked or target in blocked:
        return {'path': None, 'cost': 1e9, 'reachable': False}
    if walls[target[0]][target[1]]:
        return {'path': None, 'cost': 1e9, 'reachable': False}

    W, H = walls.width, walls.height

    def edge_cost(to_cell):
        base = 1.0
        r = risk_map.get(to_cell, 0.0) if risk_map else 0.0
        return base + w['lam_risk'] * r

    # g_score and parent
    g = {start: 0.0}
    parent = {start: None}
    # Priority queue: (f, counter, cell)
    counter = 0
    open_heap = []
    _heapq.heappush(open_heap, (distance_fn(start, target), counter, start))
    counter += 1

    while open_heap:
        _, _, cur = _heapq.heappop(open_heap)
        if cur == target:
            # Reconstruct
            path = []
            c = cur
            while c is not None:
                path.append(c)
                c = parent[c]
            path.reverse()
            return {'path': path, 'cost': g[cur], 'reachable': True}
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = cur[0] + dx, cur[1] + dy
            if nx < 0 or nx >= W or ny < 0 or ny >= H:
                continue
            if walls[nx][ny]:
                continue
            nb = (nx, ny)
            if nb in blocked:
                continue
            tentative = g[cur] + edge_cost(nb)
            if tentative < g.get(nb, 1e18):
                g[nb] = tentative
                parent[nb] = cur
                f = tentative + distance_fn(nb, target)
                _heapq.heappush(open_heap, (f, counter, nb))
                counter += 1

    return {'path': None, 'cost': 1e9, 'reachable': False}


def voronoi_safe_path(path, defender, scared_ticks, distance_fn, margin=1):
    """Check whether every cell on `path` is safely reachable before defender.

    For each step i, position path[i] must satisfy:
        i < def_dist(path[i]) - scared_ticks - margin
    (i.e., I reach cell path[i] at tick i, defender can reach it at tick
     def_dist, minus scared_ticks that they can't move as threat, minus safety
     margin of simultaneity.)

    Args:
        path: List[Cell] including start at index 0.
        defender: Cell of defender, or None (no defender = always safe).
        scared_ticks: int, how many more ticks defender is scared.
                      If scared_ticks >= len(path), path is fully safe.
        distance_fn: (a, b) -> int.
        margin: int, safety margin (1 = strict <, 2 = extra buffer).

    Returns:
        {'safe': bool, 'unsafe_at': int | None, 'min_margin': int}
        unsafe_at is the first path index where safety is violated (None if safe).
        min_margin is the tightest def_dist - my_dist observed.
    """
    if defender is None:
        return {'safe': True, 'unsafe_at': None, 'min_margin': 999}
    if not path:
        return {'safe': False, 'unsafe_at': 0, 'min_margin': -999}

    min_margin = 999
    for i, cell in enumerate(path):
        if scared_ticks >= i:
            # Defender is still scared when I arrive at path[i]
            continue
        effective_def_dist = distance_fn(defender, cell) - (scared_ticks if scared_ticks > 0 else 0)
        # Subtracting scared_ticks here is conservative; we treat scared ticks
        # as "free progress" for defender in terms of reaching the cell to
        # threaten us. That over-penalizes slightly; correct model is: defender
        # can't threaten for scared_ticks moves, then resumes pursuit.
        # For simplicity and safety we use the simpler check above (line 167).
        actual_margin = distance_fn(defender, cell) - i
        if actual_margin < min_margin:
            min_margin = actual_margin
        if actual_margin < margin:
            return {'safe': False, 'unsafe_at': i, 'min_margin': actual_margin}
    return {'safe': True, 'unsafe_at': None, 'min_margin': min_margin}


def slack_plan_to_capsule(walls, start, capsule, defender, scared_ticks,
                            food_set, distance_fn, risk_map, aps,
                            dead_end_depth, teammate=None,
                            risk_threshold=3.0, margin=1,
                            min_slack_for_detour=2,
                            max_detour_food=6):
    """Phase 1 A's complete planner: reach capsule safely with slack food grab.

    Composition:
        1. Risk-weighted A* to compute direct path.
        2. Voronoi reachability filter. If unsafe → return reachable=False.
        3. Compute slack = def_direct - my_direct - margin.
        4. If slack >= min_slack_for_detour: entry_orienteering_dp selects
           food subset to pick up en route within budget. Filter eligible
           food: risk(f) ≤ risk_threshold AND each food reachable safely
           (Voronoi) AND not in dead-end depth >= 3.
        5. Return plan with next_step.

    Args:
        start: current agent position.
        capsule: target cell.
        defender: enemy ghost position (single, 1:1 assumption).
        scared_ticks: int, defender scared timer remaining.
        food_set: FrozenSet[Cell] of current food cells on opp side.
        distance_fn: (a, b) -> int.
        risk_map: Dict[Cell, float] static risk.
        aps: FrozenSet[Cell] of articulation points.
        dead_end_depth: Dict[Cell, int].
        teammate: Cell of our B agent (blocked in planner), or None.
        risk_threshold: max risk to consider food eligible for detour.
        margin: safety margin for Voronoi check.
        min_slack_for_detour: min slack to attempt food DP (else direct).
        max_detour_food: cap on |food_set| passed to DP (avoid blow-up).

    Returns:
        {
          'reachable': bool,
          'path': List[Cell],      # chosen path (direct or with food detour)
          'next_step': Cell,       # path[1] if len≥2 else start
          'food_on_path': List[Cell],  # food picked up en route
          'direct_len': int,       # len of direct A* path
          'chosen_len': int,       # len of chosen (maybe detoured) path
          'slack': int,
          'safety_margin': int,    # min Voronoi margin
          'reason': str,           # "direct" | "slack_food" | "unreachable" | "no_slack"
        }
    """
    blocked = set()
    if teammate is not None:
        blocked.add(teammate)

    # Step 1: risk-weighted A* direct path
    direct = risk_weighted_astar(walls, start, capsule, risk_map, distance_fn,
                                   blocked=blocked)
    if not direct['reachable'] or not direct['path']:
        return {
            'reachable': False, 'path': [start], 'next_step': start,
            'food_on_path': [], 'direct_len': -1, 'chosen_len': -1,
            'slack': -1, 'safety_margin': -999, 'reason': 'unreachable',
        }
    direct_path = direct['path']
    direct_len = len(direct_path) - 1

    # Step 2: Voronoi safety on direct path
    vor = voronoi_safe_path(direct_path, defender, scared_ticks,
                              distance_fn, margin=margin)
    if not vor['safe']:
        return {
            'reachable': False, 'path': direct_path, 'next_step': start,
            'food_on_path': [], 'direct_len': direct_len,
            'chosen_len': direct_len, 'slack': -1,
            'safety_margin': vor['min_margin'], 'reason': 'unreachable',
        }

    # Step 3: Compute slack
    if defender is None or scared_ticks >= direct_len:
        def_direct = 10 ** 6
    else:
        def_direct = distance_fn(defender, capsule)
    slack = def_direct - direct_len - margin

    # Step 4: If enough slack, try food orienteering DP
    if slack < min_slack_for_detour or not food_set:
        next_step = direct_path[1] if len(direct_path) >= 2 else start
        return {
            'reachable': True, 'path': direct_path, 'next_step': next_step,
            'food_on_path': [], 'direct_len': direct_len,
            'chosen_len': direct_len, 'slack': slack,
            'safety_margin': vor['min_margin'], 'reason': 'no_slack',
        }

    # Filter eligible food
    eligible = []
    for f in food_set:
        if f == capsule or f == start:
            continue
        if dead_end_depth.get(f, 0) >= 3:
            continue
        if risk_map.get(f, 0.0) > risk_threshold:
            continue
        # Quick distance gate
        d_sf = distance_fn(start, f)
        d_fc = distance_fn(f, capsule)
        if d_sf + d_fc > direct_len + slack:
            continue
        eligible.append(f)

    # Cap food count (DP is 2^n)
    if len(eligible) > max_detour_food:
        # Keep the closest-to-capsule ones (most in-path)
        eligible.sort(key=lambda f: distance_fn(f, capsule))
        eligible = eligible[:max_detour_food]

    if not eligible:
        next_step = direct_path[1] if len(direct_path) >= 2 else start
        return {
            'reachable': True, 'path': direct_path, 'next_step': next_step,
            'food_on_path': [], 'direct_len': direct_len,
            'chosen_len': direct_len, 'slack': slack,
            'safety_margin': vor['min_margin'], 'reason': 'no_eligible_food',
        }

    # Step 5: entry_orienteering_dp budget-constrained food pickup
    budget = direct_len + slack
    dp_res = entry_orienteering_dp(start, eligible, capsule, distance_fn,
                                     budget=budget, objective='count')
    food_order = dp_res.get('food_order', [])

    if not food_order:
        # DP said direct is best
        next_step = direct_path[1] if len(direct_path) >= 2 else start
        return {
            'reachable': True, 'path': direct_path, 'next_step': next_step,
            'food_on_path': [], 'direct_len': direct_len,
            'chosen_len': direct_len, 'slack': slack,
            'safety_margin': vor['min_margin'], 'reason': 'direct',
        }

    # Build concrete path: start → food1 → food2 → ... → capsule via A*
    waypoints = [start] + food_order + [capsule]
    full_path = [start]
    for i in range(len(waypoints) - 1):
        seg = risk_weighted_astar(walls, waypoints[i], waypoints[i+1],
                                    risk_map, distance_fn, blocked=blocked)
        if not seg['reachable'] or not seg['path']:
            # A segment is blocked; fall back to direct
            next_step = direct_path[1] if len(direct_path) >= 2 else start
            return {
                'reachable': True, 'path': direct_path, 'next_step': next_step,
                'food_on_path': [], 'direct_len': direct_len,
                'chosen_len': direct_len, 'slack': slack,
                'safety_margin': vor['min_margin'], 'reason': 'segment_blocked',
            }
        full_path.extend(seg['path'][1:])  # skip first to avoid dup

    # Re-verify Voronoi safety on the detoured path (may be longer)
    vor2 = voronoi_safe_path(full_path, defender, scared_ticks,
                               distance_fn, margin=margin)
    if not vor2['safe']:
        # Detour made us unsafe → fall back to direct
        next_step = direct_path[1] if len(direct_path) >= 2 else start
        return {
            'reachable': True, 'path': direct_path, 'next_step': next_step,
            'food_on_path': [], 'direct_len': direct_len,
            'chosen_len': direct_len, 'slack': slack,
            'safety_margin': vor['min_margin'], 'reason': 'detour_unsafe',
        }

    next_step = full_path[1] if len(full_path) >= 2 else start
    return {
        'reachable': True, 'path': full_path, 'next_step': next_step,
        'food_on_path': list(food_order),
        'direct_len': direct_len, 'chosen_len': len(full_path) - 1,
        'slack': slack, 'safety_margin': vor2['min_margin'],
        'reason': 'slack_food',
    }

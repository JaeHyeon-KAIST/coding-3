#!/usr/bin/env python3
"""Risk scoring + weighted orienteering DP for rc-tempo.

Pure functions — takes fixture dict (from extract_fixtures.py), returns scores.
All weights exposed as kwargs for easy tuning.

Design (pm28):
    risk(f) = w_de * dead_end_depth(f)
            + w_ap * ap_count_on_path_to_home(f)
            + w_dh * (dist_to_home(f) / 10)
            + w_vor * (1 if low_voronoi_margin(f) else 0)
            + w_iso * (1 if isolated_food(f) else 0)
"""
import pickle
from collections import deque

DEFAULT_WEIGHTS = {
    'w_de': 3.0,
    'w_ap': 2.0,
    'w_dh': 0.5,
    'w_vor': 5.0,
    'w_iso': 2.0,
}


def load_fixture(path):
    with open(path, 'rb') as f:
        return pickle.load(f)


def _dist(fixture, a, b):
    return fixture['distances'].get((a, b), fixture['distances'].get((b, a), 10**9))


def dist_to_nearest_home(fixture, cell, team='red'):
    homes = fixture['red_home_cells'] if team == 'red' else fixture['blue_home_cells']
    return min(_dist(fixture, cell, h) for h in homes)


def compute_voronoi_margin(fixture, team='red'):
    """Per-food: margin = dist_to_our_start - dist_to_their_start (approx).
    Negative margin = closer to enemy start = 'their territory' = low_voronoi_margin.
    We use home_cells as start proxies (BFS mean from home set).
    """
    my_homes = fixture['red_home_cells'] if team == 'red' else fixture['blue_home_cells']
    en_homes = fixture['blue_home_cells'] if team == 'red' else fixture['red_home_cells']
    foods = fixture['red_target_foods'] if team == 'red' else fixture['blue_target_foods']
    out = {}
    for f in foods:
        d_me = min(_dist(fixture, f, h) for h in my_homes)
        d_en = min(_dist(fixture, f, h) for h in en_homes)
        out[f] = d_me - d_en  # positive = closer to enemy (deeper in their zone)
    return out


def compute_risk_map(fixture, team='red', weights=None):
    """Returns {food_cell: risk_score}. Higher = more 'worth grabbing during scared'."""
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)

    foods = fixture['red_target_foods'] if team == 'red' else fixture['blue_target_foods']
    ap_counts = (fixture['food_ap_count_to_home_red'] if team == 'red'
                 else fixture['food_ap_count_to_home_blue'])
    isolated = (fixture['red_isolated_foods'] if team == 'red'
                else fixture['blue_isolated_foods'])
    de_depth = fixture['dead_end_depth']

    vor_margin = compute_voronoi_margin(fixture, team)
    # low_voronoi_margin = food is in enemy's 'dominance zone' → risky to grab
    # heuristic: vor_margin > 0 (closer to enemy homes) AND significant
    vor_threshold = 2

    scores = {}
    components = {}
    for f in foods:
        de = de_depth.get(f, 0)
        ap = ap_counts.get(f, 0)
        dh = dist_to_nearest_home(fixture, f, team)
        vor = 1 if vor_margin.get(f, 0) >= vor_threshold else 0
        iso = 1 if f in isolated else 0
        s = w['w_de'] * de + w['w_ap'] * ap + w['w_dh'] * (dh / 10.0) + w['w_vor'] * vor + w['w_iso'] * iso
        scores[f] = s
        components[f] = {
            'de': de, 'ap': ap, 'dh': dh, 'vor_margin': vor_margin.get(f, 0),
            'vor_flag': vor, 'iso': iso, 'score': s,
        }
    return scores, components


def reachable_foods(fixture, capsule, foods, team='red', budget=40):
    """Filter foods where capsule→f→nearest_home ≤ budget."""
    homes = fixture['red_home_cells'] if team == 'red' else fixture['blue_home_cells']
    out = []
    for f in foods:
        to = _dist(fixture, capsule, f)
        back = min(_dist(fixture, f, h) for h in homes)
        if to + back <= budget:
            out.append(f)
    return out


def orienteering_dp(fixture, capsule, foods, team='red', budget=40, objective='count', risk_scores=None):
    """Bitmask DP orienteering.

    objective='count' — max food count (tie-break: min total dist)
    objective='risk' — max risk_sum (tie-break: min total dist)

    Returns: dict with best_score (count or risk_sum), n_food, total_moves, route (list cells).
    """
    homes = fixture['red_home_cells'] if team == 'red' else fixture['blue_home_cells']
    n = len(foods)
    INF = 10**9

    best_home_from_cap = min(homes, key=lambda h: _dist(fixture, capsule, h))
    base_total = _dist(fixture, capsule, best_home_from_cap)

    if n == 0:
        return {
            'best_score': 0.0, 'n_food': 0, 'total_moves': base_total,
            'route': [capsule, best_home_from_cap], 'food_order': [],
        }

    # distance caches
    d_cap = [_dist(fixture, capsule, foods[i]) for i in range(n)]
    d_ff = [[_dist(fixture, foods[i], foods[j]) for j in range(n)] for i in range(n)]
    d_fh = [(min(_dist(fixture, foods[i], h) for h in homes),
             min(homes, key=lambda h, i=i: _dist(fixture, foods[i], h)))
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

    # dp: (pos, mask) -> (min_dist, parent_key, parent_food_idx)
    dp = {(-1, 0): (0, None, None)}

    best_score = 0
    best_state = (-1, 0)
    best_total = base_total

    frontier = deque([(-1, 0)])
    while frontier:
        pos, mask = frontier.popleft()
        cur_dist, _, _ = dp[(pos, mask)]

        if pos == -1:
            to_home_cost = base_total - 0  # dist cap->home
            home_choice = best_home_from_cap
        else:
            to_home_cost, home_choice = d_fh[pos]
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
            if new_dist < dp.get(key, (INF,))[0]:
                dp[key] = (new_dist, (pos, mask), i)
                frontier.append(key)

    # Reconstruct route
    food_order = []
    if best_state != (-1, 0):
        cur = best_state
        chain = [cur]
        while True:
            _, par, _ = dp[cur]
            if par is None:
                break
            chain.append(par)
            cur = par
        chain.reverse()
        food_order = [foods[s[0]] for s in chain if s[0] != -1]

    # Build cell route: capsule → food1 → food2 → ... → home
    if food_order:
        home_final = min(homes, key=lambda h: _dist(fixture, food_order[-1], h))
        route = [capsule] + food_order + [home_final]
    else:
        route = [capsule, best_home_from_cap]

    return {
        'best_score': best_score,
        'n_food': len(food_order),
        'total_moves': best_total,
        'route': route,
        'food_order': food_order,
    }

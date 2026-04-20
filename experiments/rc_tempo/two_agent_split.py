#!/usr/bin/env python3
"""Two-agent zone split + joint DP for scared window.

Scared window = 40 own moves for EACH of Agent A (eats capsule, starts at capsule)
and Agent B (pre-positioned at midline). Both ghosts are scared → no threat.

Strategy:
  1. Partition red-side foods into A_zone / B_zone (3 strategies to compare).
  2. Agent A: weighted DP from capsule through A_zone foods back to home (budget 40).
  3. Agent B: pick best midline home cell as start, weighted DP through B_zone foods
     back to home (budget 40 or slightly less if B starts 1 own-turn later).
  4. Report combined food count, risk sum, routes.

Usage:
    .venv/bin/python experiments/rc_tempo/two_agent_split.py
    .venv/bin/python experiments/rc_tempo/two_agent_split.py --layout strategicCapture --strategy voronoi
    .venv/bin/python experiments/rc_tempo/two_agent_split.py --weights w_iso=0.5 --viz
"""
import argparse
import glob
import os
import sys
import time
from collections import deque
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
FIXTURE_DIR = os.path.join(REPO, 'experiments', 'artifacts', 'rc_tempo', 'fixtures')
VIZ_DIR = os.path.join(REPO, 'experiments', 'artifacts', 'rc_tempo', 'viz_split')

sys.path.insert(0, HERE)
from risk_score import (
    load_fixture, compute_risk_map, orienteering_dp, DEFAULT_WEIGHTS, _dist,
)


STRATEGIES = ['y_split', 'voronoi', 'balanced']


def _reachable_from(fixture, start, foods, team='red', budget=40, include_start_home=False):
    """From start cell (not nec. capsule), foods where start→f→nearest_home ≤ budget."""
    homes = fixture['red_home_cells'] if team == 'red' else fixture['blue_home_cells']
    out = []
    for f in foods:
        to = _dist(fixture, start, f)
        back = min(_dist(fixture, f, h) for h in homes)
        if to + back <= budget:
            out.append(f)
    return out


def _dp_from_start(fixture, start, foods, risk_scores, team='red', budget=40, objective='risk'):
    """DP where 'capsule' slot is actually the agent's starting cell (home or capsule).
    orienteering_dp already uses capsule param as 'start'. We repurpose it."""
    return orienteering_dp(fixture, start, foods, team=team, budget=budget,
                           objective=objective, risk_scores=risk_scores)


def partition_y_split(fixture, foods):
    """Split by horizontal midline. Top (y > mid) → A, bottom → B."""
    h = fixture['height']
    mid_y = h / 2
    a_foods = [f for f in foods if f[1] >= mid_y]
    b_foods = [f for f in foods if f[1] < mid_y]
    return a_foods, b_foods


def partition_voronoi(fixture, foods, a_start, b_start):
    """Each food → nearer of (a_start, b_start)."""
    a_foods, b_foods = [], []
    for f in foods:
        da = _dist(fixture, a_start, f)
        db = _dist(fixture, b_start, f)
        if da <= db:
            a_foods.append(f)
        else:
            b_foods.append(f)
    return a_foods, b_foods


def partition_balanced(fixture, foods, a_start, b_start, risk_scores):
    """Greedy assignment to balance risk totals.
    Sort foods by |da-db| descending (most asymmetric first), assign each to closer agent,
    but break ties toward whichever agent currently has less risk."""
    items = []
    for f in foods:
        da = _dist(fixture, a_start, f)
        db = _dist(fixture, b_start, f)
        items.append((f, da, db, risk_scores.get(f, 0)))
    items.sort(key=lambda x: -abs(x[1] - x[2]))

    a_foods, b_foods = [], []
    a_risk, b_risk = 0.0, 0.0
    for f, da, db, r in items:
        if da < db:
            a_foods.append(f)
            a_risk += r
        elif db < da:
            b_foods.append(f)
            b_risk += r
        else:
            if a_risk <= b_risk:
                a_foods.append(f)
                a_risk += r
            else:
                b_foods.append(f)
                b_risk += r
    return a_foods, b_foods


def pick_b_start(fixture, b_foods, team='red'):
    """Pick the home (midline-1) cell minimizing distance-to-centroid of b_foods.
    Fallback: middle home cell."""
    homes = fixture['red_home_cells'] if team == 'red' else fixture['blue_home_cells']
    if not b_foods:
        return homes[len(homes) // 2]
    # centroid
    cx = sum(f[0] for f in b_foods) / len(b_foods)
    cy = sum(f[1] for f in b_foods) / len(b_foods)
    # Pick home cell with min sum-of-distances to all b_foods
    best = homes[0]
    best_cost = 10 ** 9
    for h in homes:
        cost = sum(_dist(fixture, h, f) for f in b_foods)
        if cost < best_cost:
            best_cost = cost
            best = h
    return best


def run_split(fixture, strategy, risk_scores, budget_a=40, budget_b=40, team='red'):
    caps = fixture['red_target_capsules'] if team == 'red' else fixture['blue_target_capsules']
    foods = fixture['red_target_foods'] if team == 'red' else fixture['blue_target_foods']
    capsule = caps[0]

    if strategy == 'y_split':
        a_foods, b_foods = partition_y_split(fixture, foods)
        b_start = pick_b_start(fixture, b_foods, team=team)
    elif strategy == 'voronoi':
        # bootstrap: pick b_start as centroid home, then partition, then recompute b_start
        prelim_start = pick_b_start(fixture, foods, team=team)
        a_foods, b_foods = partition_voronoi(fixture, foods, capsule, prelim_start)
        b_start = pick_b_start(fixture, b_foods, team=team)
        a_foods, b_foods = partition_voronoi(fixture, foods, capsule, b_start)
    elif strategy == 'balanced':
        prelim_start = pick_b_start(fixture, foods, team=team)
        a_foods, b_foods = partition_balanced(fixture, foods, capsule, prelim_start, risk_scores)
        b_start = pick_b_start(fixture, b_foods, team=team)
    else:
        raise ValueError(f"Unknown strategy {strategy}")

    # Filter reachable within each agent's budget
    a_reach = _reachable_from(fixture, capsule, a_foods, team=team, budget=budget_a)
    b_reach = _reachable_from(fixture, b_start, b_foods, team=team, budget=budget_b)

    t0 = time.perf_counter()
    a_res = _dp_from_start(fixture, capsule, a_reach, risk_scores, team=team, budget=budget_a)
    t_a = time.perf_counter() - t0
    t0 = time.perf_counter()
    b_res = _dp_from_start(fixture, b_start, b_reach, risk_scores, team=team, budget=budget_b)
    t_b = time.perf_counter() - t0

    total_food = a_res['n_food'] + b_res['n_food']
    total_risk = a_res['best_score'] + b_res['best_score']

    return {
        'strategy': strategy,
        'capsule': capsule,
        'b_start': b_start,
        'a_zone_n': len(a_foods),
        'b_zone_n': len(b_foods),
        'a_reach_n': len(a_reach),
        'b_reach_n': len(b_reach),
        'a_res': a_res,
        'b_res': b_res,
        'total_food': total_food,
        'total_risk': round(total_risk, 2),
        'a_foods': a_foods,
        'b_foods': b_foods,
        't_a': round(t_a, 3),
        't_b': round(t_b, 3),
    }


def run_solo_baseline(fixture, risk_scores, budget=40, team='red'):
    """Agent A solo, Agent B does nothing (for comparison)."""
    caps = fixture['red_target_capsules']
    foods = fixture['red_target_foods']
    capsule = caps[0]
    reach = _reachable_from(fixture, capsule, foods, team=team, budget=budget)
    return orienteering_dp(fixture, capsule, reach, team=team, budget=budget,
                           objective='risk', risk_scores=risk_scores)


def render_split_image(fixture, split_result, solo_result, risk_scores, out_path, weights):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle

    walls = fixture['walls']
    w, h = fixture['width'], fixture['height']
    mid = fixture['midline_x']
    foods = fixture['red_target_foods']
    capsule = split_result['capsule']
    b_start = split_result['b_start']

    fig_w = max(9, w * 0.3)
    fig_h = max(5, h * 0.3)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=110)

    for x in range(w):
        for y in range(h):
            if walls[x][y]:
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor='#222', edgecolor='none'))
            else:
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor='#f4f4f4', edgecolor='none'))
    ax.axvline(mid - 0.5, linestyle='--', color='gray', alpha=0.6)
    for y in range(h):
        if not walls[mid - 1][y]:
            ax.add_patch(Rectangle((mid - 1 - 0.5, y - 0.5), 1, 1, facecolor='#d6ecff',
                                   edgecolor='none', alpha=0.8))

    # Food coloring by zone
    a_zone = set(split_result['a_foods'])
    b_zone = set(split_result['b_foods'])
    a_picks = set(split_result['a_res']['food_order'])
    b_picks = set(split_result['b_res']['food_order'])
    for f in foods:
        color = '#cc6677' if f in a_zone else '#77aacc'
        ax.add_patch(Circle(f, 0.32, facecolor=color, edgecolor='black', linewidth=0.4, zorder=5))
        ax.text(f[0], f[1], f"{risk_scores.get(f, 0):.1f}", ha='center', va='center',
                fontsize=5, color='white', zorder=6, fontweight='bold')

    # Mark picks
    for f in a_picks:
        ax.add_patch(Circle(f, 0.46, facecolor='none', edgecolor='#cc0033',
                            linewidth=2, zorder=6))
    for f in b_picks:
        ax.add_patch(Circle(f, 0.46, facecolor='none', edgecolor='#007733',
                            linewidth=2, zorder=6))

    # Capsule + B start
    ax.plot(*capsule, '*', color='magenta', markersize=26, markeredgecolor='black',
            markeredgewidth=1.2, zorder=7)
    ax.plot(*b_start, 'P', color='#00aa55', markersize=15, markeredgecolor='black',
            markeredgewidth=1, zorder=7)

    # Routes
    def draw_route(agent_res, start, color, label):
        if not agent_res['food_order']:
            return
        waypoints = [start] + agent_res['food_order'] + [agent_res['route'][-1]]
        from collections import deque as _dq
        w_, h_ = fixture['width'], fixture['height']
        wall = fixture['walls']
        cells = []
        for i in range(len(waypoints) - 1):
            s, d = waypoints[i], waypoints[i + 1]
            visited = {s: None}
            q = _dq([s])
            while q:
                u = q.popleft()
                if u == d:
                    break
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = u[0] + dx, u[1] + dy
                    if 0 <= nx < w_ and 0 <= ny < h_ and not wall[nx][ny]:
                        if (nx, ny) not in visited:
                            visited[(nx, ny)] = u
                            q.append((nx, ny))
            if d not in visited:
                continue
            path = []
            cur = d
            while cur is not None:
                path.append(cur)
                cur = visited[cur]
            path.reverse()
            if cells:
                cells.extend(path[1:])
            else:
                cells.extend(path)
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        ax.plot(xs, ys, '-', color=color, linewidth=2.3, alpha=0.8, zorder=4, label=label)

    draw_route(split_result['a_res'], capsule, '#cc0033',
               f"A (capsule→home) {split_result['a_res']['n_food']}f "
               f"{split_result['a_res']['total_moves']}m risk={split_result['a_res']['best_score']:.1f}")
    draw_route(split_result['b_res'], b_start, '#007733',
               f"B (midline→home) {split_result['b_res']['n_food']}f "
               f"{split_result['b_res']['total_moves']}m risk={split_result['b_res']['best_score']:.1f}")

    ax.set_xlim(-0.5, w - 0.5)
    ax.set_ylim(-0.5, h - 0.5)
    ax.set_aspect('equal')
    ax.set_xticks(range(0, w, 2))
    ax.set_yticks(range(0, h, 2))
    ax.tick_params(labelsize=6)
    ax.grid(True, alpha=0.15)

    solo_n = solo_result['n_food']
    solo_r = solo_result['best_score']
    title = (f"{fixture['layout_name']}  strategy={split_result['strategy']}  "
             f"w_de={weights.get('w_de', 3)} w_iso={weights.get('w_iso', 2)}\n"
             f"A: {split_result['a_res']['n_food']}f risk={split_result['a_res']['best_score']:.1f} | "
             f"B: {split_result['b_res']['n_food']}f risk={split_result['b_res']['best_score']:.1f} | "
             f"TOTAL: {split_result['total_food']}f risk={split_result['total_risk']}  "
             f"[solo A: {solo_n}f risk={solo_r:.1f}]  Δ={split_result['total_food']-solo_n:+d}f")
    ax.set_title(title, fontsize=9)
    ax.legend(loc='upper left', fontsize=7, framealpha=0.9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=110, bbox_inches='tight')
    plt.close(fig)


def run_one(args):
    pkl, strategy, weights, do_viz, b_bonus = args
    fixture = load_fixture(os.path.join(FIXTURE_DIR, pkl))
    lay = fixture['layout_name']
    caps = fixture['red_target_capsules']
    if len(caps) != 1:
        return {'layout': lay, 'skipped': f"{len(caps)} red caps"}

    risk_scores, _ = compute_risk_map(fixture, team='red', weights=weights)
    solo = run_solo_baseline(fixture, risk_scores)

    results_by_strat = {}
    for s in ([strategy] if strategy != 'all' else STRATEGIES):
        r = run_split(fixture, s, risk_scores, budget_a=40, budget_b=40 + b_bonus)
        results_by_strat[s] = r
        if do_viz:
            out_path = os.path.join(VIZ_DIR, f"{lay.replace('.lay','')}_{s}_bonus{b_bonus}.png")
            render_split_image(fixture, r, solo, risk_scores, out_path,
                               dict(DEFAULT_WEIGHTS, **(weights or {})))

    return {
        'layout': lay,
        'solo_n': solo['n_food'],
        'solo_risk': round(solo['best_score'], 2),
        'by_strat': results_by_strat,
        'b_bonus': b_bonus,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layout', default=None)
    ap.add_argument('--strategy', choices=STRATEGIES + ['all'], default='all')
    ap.add_argument('--weights', default=None)
    ap.add_argument('--viz', action='store_true')
    ap.add_argument('--b-bonus', type=int, default=0, help='extra budget for B (models pre-entry depth)')
    ap.add_argument('--b-bonus-sweep', default=None, help='comma-separated bonuses to sweep, e.g. 0,2,5,10')
    args = ap.parse_args()

    os.makedirs(VIZ_DIR, exist_ok=True)

    weights = None
    if args.weights:
        weights = {}
        for p in args.weights.split(','):
            k, v = p.split('=')
            weights[k.strip()] = float(v)

    if args.layout:
        pkls = [args.layout if args.layout.endswith('.pkl') else args.layout + '.pkl']
    else:
        pkls = sorted(os.path.basename(p) for p in glob.glob(os.path.join(FIXTURE_DIR, '*.pkl')))

    bonuses = [int(b) for b in args.b_bonus_sweep.split(',')] if args.b_bonus_sweep else [args.b_bonus]

    all_results = {}
    for bonus in bonuses:
        work = [(p, args.strategy, weights, args.viz, bonus) for p in pkls]
        t0 = time.perf_counter()
        with Pool(min(12, len(work))) as pool:
            results = pool.map(run_one, work)
        wall = time.perf_counter() - t0
        all_results[bonus] = (wall, results)

    print(f"Weights: {dict(DEFAULT_WEIGHTS, **(weights or {}))}")
    for bonus, (wall, results) in all_results.items():
        print(f"\n{'='*120}\nB_bonus={bonus} (B_budget={40+bonus})   Wall: {wall:.2f}s")
        print("=" * 120)
        for r in results:
            if r.get('skipped'):
                continue
            print(f"\n{r['layout']}  (solo-A: {r['solo_n']}f risk={r['solo_risk']})")
            for s, sr in r['by_strat'].items():
                a = sr['a_res']
                b = sr['b_res']
                print(f"  {s:<10}  zones={sr['a_zone_n']}/{sr['b_zone_n']}  "
                      f"A={a['n_food']}f/{a['total_moves']}m risk={a['best_score']:.1f}  "
                      f"B={b['n_food']}f/{b['total_moves']}m risk={b['best_score']:.1f}  "
                      f"TOTAL={sr['total_food']}f risk={sr['total_risk']}  "
                      f"Δvs.solo={sr['total_food']-r['solo_n']:+d}f  "
                      f"t={sr['t_a']+sr['t_b']:.2f}s")


if __name__ == '__main__':
    main()

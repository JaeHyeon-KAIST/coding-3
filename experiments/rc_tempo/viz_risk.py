#!/usr/bin/env python3
"""Visual risk map + DP routes per layout.

Outputs PNG per 1-capsule layout to experiments/artifacts/rc_tempo/viz/.

Per layout:
  - walls (black), free (light gray)
  - midline (dashed gray), home column (cyan vertical band)
  - capsule ★ magenta
  - foods colored by risk score (viridis heatmap)
  - count-max route: blue line with arrows
  - risk-max route: red line with arrows
  - labels: per-food risk score

Usage:
    .venv/bin/python experiments/rc_tempo/viz_risk.py
    .venv/bin/python experiments/rc_tempo/viz_risk.py --layout defaultCapture
    .venv/bin/python experiments/rc_tempo/viz_risk.py --weights w_de=5.0,w_iso=3.0
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
OUT_DIR = os.path.join(REPO, 'experiments', 'artifacts', 'rc_tempo', 'viz')

sys.path.insert(0, HERE)
from risk_score import (
    load_fixture, compute_risk_map, reachable_foods, orienteering_dp, DEFAULT_WEIGHTS,
)


def bfs_path_cells(fixture, src, dst):
    """Shortest path between two cells on the walls grid."""
    walls = fixture['walls']
    w, h = fixture['width'], fixture['height']
    if src == dst:
        return [src]
    visited = {src: None}
    q = deque([src])
    while q:
        u = q.popleft()
        if u == dst:
            break
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = u[0] + dx, u[1] + dy
            if 0 <= nx < w and 0 <= ny < h and not walls[nx][ny]:
                if (nx, ny) not in visited:
                    visited[(nx, ny)] = u
                    q.append((nx, ny))
    if dst not in visited:
        return []
    path = []
    cur = dst
    while cur is not None:
        path.append(cur)
        cur = visited[cur]
    path.reverse()
    return path


def waypoints_to_path(fixture, waypoints):
    """Chain of cells visited from waypoint[0] through waypoint[n-1]."""
    out = []
    for i in range(len(waypoints) - 1):
        leg = bfs_path_cells(fixture, waypoints[i], waypoints[i + 1])
        if i == 0:
            out.extend(leg)
        else:
            out.extend(leg[1:])
    return out


def parse_weights(spec):
    if not spec:
        return None
    out = {}
    for part in spec.split(','):
        k, v = part.split('=')
        out[k.strip()] = float(v)
    return out


def render_layout(args):
    layout_pkl, weights = args
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    import numpy as np

    fixture = load_fixture(os.path.join(FIXTURE_DIR, layout_pkl))
    lay = fixture['layout_name']
    caps = fixture['red_target_capsules']
    if len(caps) != 1:
        return {'layout': lay, 'skipped': f"{len(caps)} red capsules"}

    capsule = caps[0]
    foods = fixture['red_target_foods']
    walls = fixture['walls']
    w, h = fixture['width'], fixture['height']
    mid = fixture['midline_x']

    risk_scores, components = compute_risk_map(fixture, team='red', weights=weights)
    reachable = reachable_foods(fixture, capsule, foods, team='red', budget=40)
    count_res = orienteering_dp(fixture, capsule, reachable, team='red', budget=40, objective='count')
    risk_res = orienteering_dp(fixture, capsule, reachable, team='red', budget=40,
                                objective='risk', risk_scores=risk_scores)

    # Figure sizing: cells get ~0.3 inch each
    fig_w = max(8, w * 0.28)
    fig_h = max(5, h * 0.28)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=110)

    # Walls
    for x in range(w):
        for y in range(h):
            if walls[x][y]:
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor='#222', edgecolor='none'))
            else:
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor='#f4f4f4', edgecolor='none'))

    # Midline + home columns
    ax.axvline(mid - 0.5, linestyle='--', color='gray', alpha=0.6, linewidth=1)
    for y in range(h):
        if not walls[mid - 1][y]:
            ax.add_patch(Rectangle((mid - 1 - 0.5, y - 0.5), 1, 1, facecolor='#d6ecff',
                                   edgecolor='none', alpha=0.8))

    # Articulation points (subtle highlight)
    aps = fixture['articulation_points']
    for (x, y) in aps:
        if x >= mid:  # only show red-side-relevant APs
            ax.plot(x, y, 'o', color='#ffd966', markersize=4, alpha=0.5, zorder=2)

    # Dead-end depth heatmap on free cells (red-side)
    de_depth = fixture['dead_end_depth']
    max_de = max(de_depth.values()) if de_depth else 1
    for (x, y), d in de_depth.items():
        if d > 0 and x >= mid - 1:
            alpha = min(0.35, d / max_de * 0.4)
            ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor='#ff8888',
                                   edgecolor='none', alpha=alpha, zorder=1))

    # Food risk heatmap
    food_risks = [risk_scores.get(f, 0) for f in foods]
    vmin, vmax = (min(food_risks), max(food_risks)) if food_risks else (0, 1)
    cmap = plt.get_cmap('viridis')
    for f in foods:
        r = risk_scores.get(f, 0)
        norm = (r - vmin) / (vmax - vmin + 1e-9)
        ax.add_patch(Circle(f, 0.32, facecolor=cmap(norm), edgecolor='black',
                            linewidth=0.5, zorder=5))
        ax.text(f[0], f[1], f"{r:.1f}", ha='center', va='center', fontsize=5.5,
                color='white' if norm < 0.55 else 'black', zorder=6, fontweight='bold')

    # Capsule star
    ax.plot(*capsule, '*', color='magenta', markersize=28, markeredgecolor='black',
            markeredgewidth=1.2, zorder=7)

    # Count-max route (blue)
    if count_res['food_order']:
        path = waypoints_to_path(fixture, [capsule] + count_res['food_order']
                                           + [count_res['route'][-1]])
        xs = [c[0] for c in path]
        ys = [c[1] for c in path]
        ax.plot(xs, ys, '-', color='#0066cc', linewidth=2.2, alpha=0.75, zorder=4,
                label=f"count-max: {count_res['n_food']}f/{count_res['total_moves']}m")

    # Risk-max route (red)
    if risk_res['food_order']:
        path = waypoints_to_path(fixture, [capsule] + risk_res['food_order']
                                           + [risk_res['route'][-1]])
        xs = [c[0] for c in path]
        ys = [c[1] for c in path]
        ax.plot(xs, ys, '-', color='#cc0033', linewidth=2.2, alpha=0.75, zorder=4,
                label=f"risk-max: {risk_res['n_food']}f/{risk_res['total_moves']}m risk={risk_res['best_score']:.1f}")

    # Mark picks
    cs_set = set(count_res['food_order'])
    rs_set = set(risk_res['food_order'])
    for f in foods:
        if f in cs_set and f in rs_set:
            ax.add_patch(Circle(f, 0.46, facecolor='none', edgecolor='purple',
                                linewidth=1.8, linestyle='-', zorder=6))
        elif f in cs_set:
            ax.add_patch(Circle(f, 0.46, facecolor='none', edgecolor='#0066cc',
                                linewidth=1.8, linestyle='--', zorder=6))
        elif f in rs_set:
            ax.add_patch(Circle(f, 0.46, facecolor='none', edgecolor='#cc0033',
                                linewidth=1.8, linestyle=':', zorder=6))

    ax.set_xlim(-0.5, w - 0.5)
    ax.set_ylim(-0.5, h - 0.5)
    ax.set_aspect('equal')
    ax.set_xticks(range(0, w, 2))
    ax.set_yticks(range(0, h, 2))
    ax.tick_params(labelsize=6)
    ax.grid(True, alpha=0.15)

    title = (f"{lay}  (w_de={DEFAULT_WEIGHTS['w_de']} w_ap={DEFAULT_WEIGHTS['w_ap']} "
             f"w_dh={DEFAULT_WEIGHTS['w_dh']} w_vor={DEFAULT_WEIGHTS['w_vor']} "
             f"w_iso={DEFAULT_WEIGHTS['w_iso']})\n"
             f"red foods={len(foods)} reachable={len(reachable)} capsule={capsule} | "
             f"count={count_res['n_food']}f risk={count_res['best_score']}  vs  "
             f"risk={risk_res['n_food']}f risk={risk_res['best_score']:.1f}")
    ax.set_title(title, fontsize=9)
    ax.legend(loc='upper left', fontsize=7, framealpha=0.9)

    out_path = os.path.join(OUT_DIR, lay.replace('.lay', '') + '.png')
    fig.tight_layout()
    fig.savefig(out_path, dpi=110, bbox_inches='tight')
    plt.close(fig)

    return {
        'layout': lay,
        'path': out_path,
        'count_n': count_res['n_food'],
        'risk_n': risk_res['n_food'],
        'count_risk': round(count_res['best_score'], 2) if isinstance(count_res['best_score'], (int, float)) else 0,
        'risk_score': round(risk_res['best_score'], 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--layout', default=None)
    ap.add_argument('--weights', default=None)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    weights = parse_weights(args.weights)

    if args.layout:
        name = args.layout if args.layout.endswith('.pkl') else args.layout + '.pkl'
        pkls = [name]
    else:
        pkls = sorted(os.path.basename(p) for p in glob.glob(os.path.join(FIXTURE_DIR, '*.pkl')))

    work = [(p, weights) for p in pkls]
    t0 = time.perf_counter()
    with Pool(min(12, len(work))) as pool:
        results = pool.map(render_layout, work)
    wall = time.perf_counter() - t0

    print(f"Pool({min(12, len(work))}) wall: {wall:.2f}s")
    for r in results:
        if r.get('skipped'):
            print(f"  {r['layout']:<22} SKIP: {r['skipped']}")
        else:
            print(f"  {r['layout']:<22} count={r['count_n']}f  risk={r['risk_n']}f "
                  f"risk_sum={r['risk_score']}  →  {r['path']}")


if __name__ == '__main__':
    main()

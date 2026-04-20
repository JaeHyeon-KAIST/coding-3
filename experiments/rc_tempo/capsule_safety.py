#!/usr/bin/env python3
"""Capsule approach safety analysis — first branch decision for rc-tempo.

Per 1-capsule layout, compute:
  - capsule_depth: min maze-distance from midline (red home column) to capsule
  - path_ap_count: APs on shortest midline→capsule path
  - chokepoint_ap: any SINGLE AP whose removal disconnects midline from capsule
                   (= guaranteed defender camp spot)
  - immediate_ap: AP adjacent to capsule (1 step away)
  - node_connectivity: min # of nodes defender must block to cut all paths (1 or ≥2)

Verdict rule:
  SAFE if node_connectivity ≥ 2 AND capsule_depth ≤ ~15
  UNSAFE otherwise → rc-tempo falls back to rc82

Usage:
    .venv/bin/python experiments/rc_tempo/capsule_safety.py
    .venv/bin/python experiments/rc_tempo/capsule_safety.py --viz
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
VIZ_DIR = os.path.join(REPO, 'experiments', 'artifacts', 'rc_tempo', 'viz_safety')

sys.path.insert(0, HERE)
from risk_score import load_fixture


def bfs_sources_to_target(walls, sources, target, blocked=None):
    """Multi-source BFS. Returns (reachable, dist, parent)."""
    blocked = blocked or set()
    w, h = len(walls), len(walls[0])
    visited = {}
    q = deque()
    for s in sources:
        if s == target:
            return True, 0, {s: None}
        if s in blocked:
            continue
        visited[s] = None
        q.append((s, 0))
    while q:
        u, d = q.popleft()
        if u == target:
            return True, d, visited
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = u[0] + dx, u[1] + dy
            if 0 <= nx < w and 0 <= ny < h and not walls[nx][ny]:
                cell = (nx, ny)
                if cell in blocked or cell in visited:
                    continue
                visited[cell] = u
                q.append((cell, d + 1))
    return target in visited, visited.get(target, None), visited


def reconstruct_path(parent, target):
    path = []
    cur = target
    while cur is not None:
        path.append(cur)
        cur = parent.get(cur)
    path.reverse()
    return path


def analyze_safety(fixture):
    walls = fixture['walls']
    w, h = fixture['width'], fixture['height']
    mid = fixture['midline_x']
    caps = fixture['red_target_capsules']
    if len(caps) != 1:
        return {'layout': fixture['layout_name'], 'skipped': f"{len(caps)} red caps"}
    capsule = caps[0]
    red_homes = fixture['red_home_cells']
    aps = fixture['articulation_points']

    # Shortest midline→capsule
    reach, depth, parent = bfs_sources_to_target(walls, red_homes, capsule)
    path = reconstruct_path(parent, capsule)

    # APs on path (excluding terminal cells - capsule itself, home cells)
    home_set = set(red_homes)
    path_aps = [c for c in path[1:-1] if c in aps]
    path_ap_count = len(path_aps)

    # Immediate AP: AP adjacent (1 step) to capsule
    imm_aps = []
    for (dx, dy) in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        n = (capsule[0] + dx, capsule[1] + dy)
        if 0 <= n[0] < w and 0 <= n[1] < h and not walls[n[0]][n[1]]:
            if n in aps:
                imm_aps.append(n)

    # Single-chokepoint check: for each AP on enemy side (x >= mid), remove it and
    # see if midline→capsule still reachable. If ANY single removal disconnects → chokepoint exists.
    enemy_aps = [ap for ap in aps if ap[0] >= mid and ap != capsule]
    chokepoints = []
    for ap in enemy_aps:
        ok, _, _ = bfs_sources_to_target(walls, red_homes, capsule, blocked={ap})
        if not ok:
            chokepoints.append(ap)

    # Node connectivity (Menger): min number of nodes to remove to disconnect.
    # Equivalent to max-flow with node capacity 1. For our purposes:
    # 1 if any single chokepoint; else ≥ 2 (grid path node-connectivity)
    node_conn = 1 if chokepoints else 2  # approximation; could verify via max-flow for exact

    # Safety verdict
    safe = (node_conn >= 2) and (depth <= 15)

    return {
        'layout': fixture['layout_name'],
        'capsule': capsule,
        'capsule_depth': depth,
        'path_len': len(path),
        'path_ap_count': path_ap_count,
        'path_aps': path_aps,
        'imm_aps': imm_aps,
        'chokepoints': chokepoints,
        'node_conn': node_conn,
        'safe': safe,
        'shortest_path': path,
    }


def render_safety(fixture, result, out_path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle

    walls = fixture['walls']
    w, h = fixture['width'], fixture['height']
    mid = fixture['midline_x']
    foods = set(fixture['red_target_foods'])
    caps = fixture['red_target_capsules']
    capsule = caps[0]
    aps = fixture['articulation_points']
    path = result['shortest_path']
    path_set = set(path)
    chokepoints = set(result['chokepoints'])

    fig_w = max(8, w * 0.3)
    fig_h = max(5, h * 0.3)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=110)

    for x in range(w):
        for y in range(h):
            if walls[x][y]:
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor='#222'))
            else:
                ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor='#f4f4f4'))
    ax.axvline(mid - 0.5, linestyle='--', color='gray', alpha=0.6)
    for y in range(h):
        if not walls[mid - 1][y]:
            ax.add_patch(Rectangle((mid - 1 - 0.5, y - 0.5), 1, 1, facecolor='#d6ecff',
                                   edgecolor='none', alpha=0.8))

    # Foods as small dots
    for f in foods:
        ax.add_patch(Circle(f, 0.22, facecolor='#cc6677', edgecolor='none', zorder=4))

    # Enemy-side APs (gold)
    for ap in aps:
        if ap[0] >= mid:
            ax.plot(ap[0], ap[1], 'o', color='#ffcc00', markersize=6, alpha=0.6, zorder=5)

    # Chokepoints (big red X)
    for cp in chokepoints:
        ax.plot(cp[0], cp[1], 'X', color='red', markersize=16, markeredgecolor='black',
                markeredgewidth=1.3, zorder=8)

    # Shortest path (blue)
    xs = [c[0] for c in path]
    ys = [c[1] for c in path]
    ax.plot(xs, ys, '-', color='#0066cc', linewidth=2.5, alpha=0.75, zorder=6,
            label=f"midline→capsule path ({len(path)-1} moves)")

    # APs ON path (orange circle)
    for ap in result['path_aps']:
        ax.plot(ap[0], ap[1], 'o', color='orange', markersize=12,
                markeredgecolor='black', markeredgewidth=1, zorder=7)

    # Immediate APs (pink triangle)
    for ia in result['imm_aps']:
        ax.plot(ia[0], ia[1], '^', color='deeppink', markersize=14,
                markeredgecolor='black', markeredgewidth=1, zorder=7)

    # Capsule star
    ax.plot(*capsule, '*', color='magenta', markersize=30, markeredgecolor='black',
            markeredgewidth=1.5, zorder=9)

    ax.set_xlim(-0.5, w - 0.5)
    ax.set_ylim(-0.5, h - 0.5)
    ax.set_aspect('equal')
    ax.set_xticks(range(0, w, 2))
    ax.set_yticks(range(0, h, 2))
    ax.tick_params(labelsize=6)
    ax.grid(True, alpha=0.15)

    verdict = "SAFE ✓" if result['safe'] else "UNSAFE ✗ → fallback"
    title = (f"{result['layout']}  capsule={capsule}  depth={result['capsule_depth']}  "
             f"path_APs={result['path_ap_count']}  imm_APs={len(result['imm_aps'])}  "
             f"chokepoints={len(result['chokepoints'])}  node_conn={result['node_conn']}\n"
             f"Legend: blue line=shortest path, gold=APs (enemy side), orange=AP on path, "
             f"pink△=imm-AP, red X=chokepoint     VERDICT: {verdict}")
    ax.set_title(title, fontsize=9)
    ax.legend(loc='upper left', fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=110, bbox_inches='tight')
    plt.close(fig)


def run_one(args):
    pkl, do_viz = args
    fixture = load_fixture(os.path.join(FIXTURE_DIR, pkl))
    lay = fixture['layout_name']
    caps = fixture['red_target_capsules']
    if len(caps) != 1:
        return {'layout': lay, 'skipped': f"{len(caps)} red caps"}
    result = analyze_safety(fixture)
    if do_viz and not result.get('skipped'):
        out = os.path.join(VIZ_DIR, lay.replace('.lay', '') + '.png')
        render_safety(fixture, result, out)
        result['viz'] = out
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--viz', action='store_true')
    ap.add_argument('--layout', default=None)
    args = ap.parse_args()

    os.makedirs(VIZ_DIR, exist_ok=True)

    if args.layout:
        pkls = [args.layout if args.layout.endswith('.pkl') else args.layout + '.pkl']
    else:
        pkls = sorted(os.path.basename(p) for p in glob.glob(os.path.join(FIXTURE_DIR, '*.pkl')))

    work = [(p, args.viz) for p in pkls]
    with Pool(min(12, len(work))) as pool:
        results = pool.map(run_one, work)

    print(f"{'Layout':<24} {'Caps':<5} {'Depth':<6} {'PAP':<4} {'ImmAP':<6} {'Choke':<6} {'Conn':<5} {'SAFE':<5}")
    print("-" * 80)
    for r in results:
        if r.get('skipped'):
            print(f"{r['layout']:<24} SKIP ({r['skipped']})")
            continue
        verdict = "✓" if r['safe'] else "✗"
        print(f"{r['layout']:<24} {'1':<5} {r['capsule_depth']:<6} "
              f"{r['path_ap_count']:<4} {len(r['imm_aps']):<6} "
              f"{len(r['chokepoints']):<6} {r['node_conn']:<5} {verdict}")
    for r in results:
        if not r.get('skipped') and r['chokepoints']:
            print(f"  {r['layout']} chokepoints: {r['chokepoints']}")
        if not r.get('skipped') and r['imm_aps']:
            print(f"  {r['layout']} immediate APs: {r['imm_aps']}")


if __name__ == '__main__':
    main()

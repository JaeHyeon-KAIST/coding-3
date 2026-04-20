#!/usr/bin/env python3
"""Resumable HTH battery for rc-tempo agents.

- Each game result flushed+fsynced to CSV immediately.
- Resume: scans existing CSV for completed (agent_a, opp, layout, color, seed, game_idx)
  keys and skips them.
- Parallel via ProcessPoolExecutor.
- Per-game metrics (if agent supports RCTEMPO_METRICS_CSV) written to a SECOND CSV.

Usage:
    .venv/bin/python experiments/rc_tempo/hth_resumable.py \\
        --agent zoo_reflex_rc_tempo_beta \\
        --opponents baseline zoo_reflex_rc82 zoo_reflex_rc166 monster_rule_expert zoo_reflex_h1test \\
        --layouts defaultCapture distantCapture \\
        --games-per-cell 100 --colors red blue \\
        --workers 12 \\
        --out experiments/artifacts/rc_tempo/hth_beta.csv \\
        --metrics-out experiments/artifacts/rc_tempo/metrics_beta.csv

Resume:
    Re-run the same command. Completed rows detected and skipped.
"""
from __future__ import annotations
import argparse
import csv
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / 'experiments'))
from run_match import run_match  # noqa: E402


FIELDS = ['agent_a', 'opp', 'layout', 'color', 'seed', 'game_idx',
          'winner', 'red_win', 'blue_win', 'tie', 'score',
          'crashed', 'wall_sec']


def wilson_95(w, n):
    if n == 0:
        return 0, 0, 1
    p = w / n
    z = 1.96
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return p, (centre - spread) / denom, (centre + spread) / denom


def load_completed(csv_path):
    """Return set of completed (opp, layout, color, seed, game_idx) tuples."""
    done = set()
    p = Path(csv_path)
    if not p.exists():
        return done
    try:
        with p.open() as f:
            reader = csv.DictReader(f)
            for r in reader:
                try:
                    key = (r['opp'], r['layout'], r['color'],
                            int(r['seed']), int(r['game_idx']))
                    done.add(key)
                except Exception:
                    continue
    except Exception:
        pass
    return done


def append_row(csv_path, row, lock=None):
    """Append one row with flush+fsync. lock is optional (single-process usually safe)."""
    p = Path(csv_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    first_write = not p.exists()
    with p.open('a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if first_write:
            w.writeheader()
        w.writerow({k: row.get(k, '') for k in FIELDS})
        f.flush()
        os.fsync(f.fileno())


def play_one(args):
    agent_a, opp, layout, color, seed, game_idx, metrics_csv = args
    is_red = (color == 'red')
    if is_red:
        red, blue = agent_a, opp
    else:
        red, blue = opp, agent_a

    env_extras = {}
    if metrics_csv:
        env_extras['RCTEMPO_METRICS_CSV'] = metrics_csv
        env_extras['RCTEMPO_LAYOUT'] = layout
        env_extras['RCTEMPO_GAME_ID'] = f"{agent_a}_{opp}_{layout}_{color}_{seed}_{game_idx}"
    # Inject env vars to subprocess via os.environ (run_match spawns subprocess inheriting env)
    for k, v in env_extras.items():
        os.environ[k] = v

    t0 = time.time()
    try:
        result = run_match(red=red, blue=blue, layout=layout, seed=seed,
                            timeout_s=120.0)
    except Exception as e:
        result = {'crashed': True, 'red_win': 0, 'blue_win': 0,
                   'crash_reason': f"wrapper:{type(e).__name__}:{e}",
                   'winner': None, 'score': 0, 'tie': 0}
    wall = time.time() - t0

    winner = result.get('winner')
    rw = int(result.get('red_win', 0) or 0)
    bw = int(result.get('blue_win', 0) or 0)
    tie = int(result.get('tie', 0) or 0)
    score = result.get('score', 0)
    if score is None:
        score = 0
    crashed = int(bool(result.get('crashed', False)))

    return {
        'agent_a': agent_a, 'opp': opp, 'layout': layout,
        'color': color, 'seed': seed, 'game_idx': game_idx,
        'winner': winner or '', 'red_win': rw, 'blue_win': bw, 'tie': tie,
        'score': score, 'crashed': crashed, 'wall_sec': round(wall, 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agent', required=True)
    ap.add_argument('--opponents', nargs='+', required=True)
    ap.add_argument('--layouts', nargs='+', required=True)
    ap.add_argument('--games-per-cell', type=int, default=100,
                    help='games per (opp, layout, color) cell')
    ap.add_argument('--colors', nargs='+', default=['red', 'blue'])
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--master-seed', type=int, default=42)
    ap.add_argument('--out', required=True)
    ap.add_argument('--metrics-out', default=None)
    args = ap.parse_args()

    done = load_completed(args.out)
    print(f"[hth] resume: {len(done)} completed rows in {args.out}", file=sys.stderr)

    work = []
    for opp in args.opponents:
        for li, layout in enumerate(args.layouts):
            for ci, color in enumerate(args.colors):
                for g in range(args.games_per_cell):
                    seed = args.master_seed + li * 997 + ci * 53 + g
                    key = (opp, layout, color, seed, g)
                    if key in done:
                        continue
                    work.append((args.agent, opp, layout, color, seed, g, args.metrics_out))

    total = len(work)
    if total == 0:
        print("[hth] nothing to do (all completed)", file=sys.stderr)
    else:
        print(f"[hth] scheduled {total} games, workers={args.workers}", file=sys.stderr)

    t0 = time.time()
    written = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(play_one, w) for w in work]
        for fut in as_completed(futures):
            try:
                row = fut.result()
            except Exception as e:
                print(f"[hth] worker error: {type(e).__name__}: {e}", file=sys.stderr)
                continue
            append_row(args.out, row)
            written += 1
            if written % max(1, total // 40) == 0:
                elapsed = time.time() - t0
                eta = elapsed / max(1, written) * (total - written)
                print(f"[hth] progress {written}/{total}  elapsed={elapsed:.0f}s  ETA={eta:.0f}s",
                       file=sys.stderr)

    # Summary
    if Path(args.out).exists():
        rows = []
        with open(args.out) as f:
            rows = list(csv.DictReader(f))
        agg = {}
        for r in rows:
            if r['agent_a'] != args.agent:
                continue
            k = (r['opp'], r['layout'])
            if k not in agg:
                agg[k] = {'wins': 0, 'total': 0, 'crashes': 0}
            wincol = 'red_win' if r['color'] == 'red' else 'blue_win'
            agg[k]['wins'] += int(r[wincol])
            agg[k]['total'] += 1
            agg[k]['crashes'] += int(r['crashed'])
        print()
        print(f"HTH {args.agent}")
        print(f"{'opp':<26} {'layout':<18} {'w/n':<10} {'WR':>7} {'Wilson 95% CI':<22} {'crash':>6}")
        print("-" * 100)
        for (opp, layout), s in sorted(agg.items()):
            p, lo, hi = wilson_95(s['wins'], s['total'])
            print(f"{opp:<26} {layout:<18} {s['wins']}/{s['total']:<7}  {p:>7.3f}  "
                  f"[{lo:.3f}, {hi:.3f}]   {s['crashes']:>6}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Phase 1 multi-opp / multi-layout smoke harness using phase1_runner.

Measures β's "can A reach capsule without dying" primitive across a pool
of opponents. Faster than full-game HTH since games exit at A's outcome.

Metrics per cell (opp, layout, color):
    - cap_eaten_rate: fraction of games A ate capsule (success)
    - a_died_rate: fraction A died (failure)
    - timeout_rate: fraction 150 moves elapsed without outcome (ambiguous)
    - avg_moves_to_outcome
    - avg_a_food_on_trip

Usage:
    .venv/bin/python experiments/rc_tempo/phase1_smoke.py \\
        --agent zoo_reflex_rc_tempo_beta_v3a \\
        --opponents baseline zoo_reflex_rc82 zoo_reflex_rc166 \\
        --layouts defaultCapture distantCapture \\
        --games-per-cell 5 --workers 4 --max-moves 300 \\
        --out /tmp/phase1_v3a.csv

Resume: re-run same command. Existing CSV rows (by key) are skipped.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RUNNER = HERE / 'phase1_runner.py'
VENV_PYTHON = REPO / '.venv' / 'bin' / 'python'


FIELDS = [
    'agent', 'opp', 'layout', 'color', 'seed', 'game_idx',
    'outcome', 'moves', 'a_food_eaten', 'a_died_count',
    'capsule_eaten_by_A', 'capsule_eaten_by_anyone', 'capsule_eaten_tick',
    'trigger_tick', 'triggered', 'moves_post_trigger',
    'a_food_post_trigger', 'a_food_pre_trigger',
    'a_died_post_trigger', 'cap_eaten_post_trigger',
    'score', 'crashed', 'wall_sec',
]


DEFAULT_OPPONENTS = [
    'baseline',
    'zoo_reflex_rc82',
    'zoo_reflex_rc166',
    'zoo_reflex_rc16',
    'zoo_reflex_rc02',
    'zoo_reflex_rc32',
    'zoo_reflex_rc47',
    'zoo_reflex_h1test',
    'zoo_reflex_h1c',
    'monster_rule_expert',
    'zoo_distill_rc22',
    'zoo_reflex_rc_tempo_beta',   # β v2d = self-baseline
]

DEFAULT_LAYOUTS = ['defaultCapture', 'distantCapture']
DEFAULT_COLORS = ['red', 'blue']


def play_one(args):
    agent, opp, layout, color, seed, game_idx, max_moves = args
    is_red = (color == 'red')
    red = agent if is_red else opp
    blue = opp if is_red else agent

    cmd = [
        str(VENV_PYTHON), str(RUNNER),
        '-r', red, '-b', blue,
        '-l', layout,
        '--seed', str(seed),
        '--max-moves', str(max_moves),
        '--our-team', color,
    ]
    t0 = time.time()
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                              cwd=str(REPO))
        # Parse last JSON line in stdout
        last_line = None
        for line in res.stdout.strip().splitlines():
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                last_line = line
        if last_line is None:
            data = {'outcome': 'crashed', 'crash_reason': f'no_json_output:rc={res.returncode}'}
        else:
            try:
                data = json.loads(last_line)
            except Exception as e:
                data = {'outcome': 'crashed', 'crash_reason': f'json_parse:{e}'}
    except subprocess.TimeoutExpired:
        data = {'outcome': 'crashed', 'crash_reason': 'subprocess_timeout'}
    except Exception as e:
        data = {'outcome': 'crashed', 'crash_reason': f'subprocess:{type(e).__name__}:{e}'}

    wall = time.time() - t0

    return {
        'agent': agent, 'opp': opp, 'layout': layout, 'color': color,
        'seed': seed, 'game_idx': game_idx,
        'outcome': data.get('outcome', 'unknown'),
        'moves': data.get('moves', 0),
        'a_food_eaten': data.get('a_food_eaten', 0),
        'a_died_count': data.get('a_died_count', 0),
        'capsule_eaten_by_A': int(bool(data.get('capsule_eaten_by_A', False))),
        'capsule_eaten_by_anyone': int(bool(data.get('capsule_eaten_by_anyone', False))),
        'capsule_eaten_tick': data.get('capsule_eaten_tick', -1),
        'trigger_tick': data.get('trigger_tick', -1),
        'triggered': int(bool(data.get('triggered', False))),
        'moves_post_trigger': data.get('moves_post_trigger', -1),
        'a_food_post_trigger': data.get('a_food_post_trigger', 0),
        'a_food_pre_trigger': data.get('a_food_pre_trigger', 0),
        'a_died_post_trigger': int(bool(data.get('a_died_post_trigger', False))),
        'cap_eaten_post_trigger': int(bool(data.get('cap_eaten_post_trigger', False))),
        'score': data.get('score', 0) or 0,
        'crashed': int(bool(data.get('crashed', False))),
        'wall_sec': round(wall, 3),
    }


def load_completed(csv_path):
    done = set()
    p = Path(csv_path)
    if not p.exists():
        return done
    try:
        with p.open() as f:
            reader = csv.DictReader(f)
            for r in reader:
                try:
                    key = (r['agent'], r['opp'], r['layout'], r['color'],
                            int(r['seed']), int(r['game_idx']))
                    done.add(key)
                except Exception:
                    continue
    except Exception:
        pass
    return done


def append_row(csv_path, row):
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


def summarize(csv_path, agent):
    """Summarize post-trigger metrics.

    The core question: AFTER β trigger fires (opp_pacman==1 first observed),
    did A successfully eat capsule / die / collect food?
    Games that never triggered are reported separately as "no_trigger".
    """
    p = Path(csv_path)
    if not p.exists():
        return
    agg = {}
    with p.open() as f:
        for r in csv.DictReader(f):
            if r['agent'] != agent:
                continue
            k = (r['opp'], r['layout'])
            if k not in agg:
                agg[k] = {
                    'n_total': 0, 'n_triggered': 0,
                    'cap_post': 0, 'died_post': 0,
                    'sum_moves_post': 0, 'sum_food_post': 0,
                    'sum_wall': 0.0,
                }
            agg[k]['n_total'] += 1
            agg[k]['sum_wall'] += float(r.get('wall_sec', 0.0))
            triggered = int(r.get('triggered', 0))
            if triggered:
                agg[k]['n_triggered'] += 1
                agg[k]['cap_post'] += int(r.get('cap_eaten_post_trigger', 0))
                agg[k]['died_post'] += int(r.get('a_died_post_trigger', 0))
                mpt = int(r.get('moves_post_trigger', -1))
                if mpt >= 0:
                    agg[k]['sum_moves_post'] += mpt
                agg[k]['sum_food_post'] += int(r.get('a_food_post_trigger', 0))

    print(f"\n[phase1_smoke post-trigger] {agent}")
    hdr = f"{'opp':<26} {'layout':<18} {'n':>4} {'trg':>4} {'cap%':>6} {'die%':>6} {'mov':>5} {'food':>5} {'wall':>6}"
    print(hdr)
    print("-" * len(hdr))
    total = {'n_total': 0, 'n_triggered': 0, 'cap_post': 0, 'died_post': 0,
             'sum_moves_post': 0, 'sum_food_post': 0, 'sum_wall': 0.0}
    for (opp, lay), s in sorted(agg.items()):
        n_total = max(1, s['n_total'])
        n_trg = max(1, s['n_triggered']) if s['n_triggered'] > 0 else 1
        cap_p = s['cap_post'] * 100.0 / n_trg
        die_p = s['died_post'] * 100.0 / n_trg
        mov = s['sum_moves_post'] / n_trg
        food = s['sum_food_post'] / n_trg
        wall = s['sum_wall'] / n_total
        print(f"{opp:<26} {lay:<18} {s['n_total']:>4} {s['n_triggered']:>4} "
              f"{cap_p:>5.1f}% {die_p:>5.1f}% {mov:>5.0f} {food:>5.1f} {wall:>5.2f}s")
        for k in total:
            total[k] += s[k]

    if total['n_total'] > 0:
        n_total = total['n_total']
        n_trg = max(1, total['n_triggered'])
        print("-" * len(hdr))
        print(f"{'TOTAL':<26} {'':<18} {n_total:>4} {total['n_triggered']:>4} "
              f"{total['cap_post']*100.0/n_trg:>5.1f}% {total['died_post']*100.0/n_trg:>5.1f}% "
              f"{total['sum_moves_post']/n_trg:>5.0f} {total['sum_food_post']/n_trg:>5.1f} "
              f"{total['sum_wall']/n_total:>5.2f}s")
        print(f"\n[trigger rate: {total['n_triggered']}/{n_total} = {total['n_triggered']*100.0/n_total:.1f}%]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agent', required=True)
    ap.add_argument('--opponents', nargs='+', default=DEFAULT_OPPONENTS)
    ap.add_argument('--layouts', nargs='+', default=DEFAULT_LAYOUTS)
    ap.add_argument('--colors', nargs='+', default=DEFAULT_COLORS)
    ap.add_argument('--games-per-cell', type=int, default=5)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--master-seed', type=int, default=42)
    ap.add_argument('--max-moves', type=int, default=300)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    done = load_completed(args.out)
    print(f"[phase1_smoke] resume: {len(done)} completed in {args.out}", file=sys.stderr)

    work = []
    for opp in args.opponents:
        for li, layout in enumerate(args.layouts):
            for ci, color in enumerate(args.colors):
                for g in range(args.games_per_cell):
                    seed = args.master_seed + li * 997 + ci * 53 + g
                    key = (args.agent, opp, layout, color, seed, g)
                    if key in done:
                        continue
                    work.append((args.agent, opp, layout, color, seed, g,
                                 args.max_moves))

    total = len(work)
    if total == 0:
        print("[phase1_smoke] nothing to do", file=sys.stderr)
    else:
        print(f"[phase1_smoke] scheduled {total} games, workers={args.workers}",
              file=sys.stderr)

    t0 = time.time()
    written = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(play_one, w) for w in work]
        for fut in as_completed(futures):
            try:
                row = fut.result()
            except Exception as e:
                print(f"[phase1_smoke] worker error: {e}", file=sys.stderr)
                continue
            append_row(args.out, row)
            written += 1
            if written % max(1, total // 20) == 0:
                elapsed = time.time() - t0
                eta = elapsed / max(1, written) * (total - written)
                print(f"[phase1_smoke] {written}/{total}  {elapsed:.0f}s elapsed  ETA {eta:.0f}s",
                      file=sys.stderr)

    summarize(args.out, args.agent)


if __name__ == '__main__':
    main()

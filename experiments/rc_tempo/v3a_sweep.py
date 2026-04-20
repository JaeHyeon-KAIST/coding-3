#!/usr/bin/env python3
"""v3a hyperparameter sweep: run multiple variants, compare post-trigger metrics.

Variants configured via env vars read by zoo_reflex_rc_tempo_beta_v3a:
    V3A_MARGIN          — Voronoi safety margin (0=simultaneous OK, 1=strict, 2=buffer)
    V3A_RISK_THRESHOLD  — max risk for food to be eligible for slack detour
    V3A_SLACK_MIN       — min slack to trigger food DP
    V3A_MAX_FOOD        — cap on food candidates (DP is 2^n)
    V3A_GREEDY_FALLBACK — on unreachable, try greedy 1-step toward capsule
    V3A_TRIGGER_MODE    — "strict" (==1) | "loose" (>=1)
    V3A_STICKY_RADIUS   — sticky commit radius

Usage:
    .venv/bin/python experiments/rc_tempo/v3a_sweep.py \\
        --games-per-cell 5 --workers 6 --max-moves 600 \\
        --out-dir /tmp/v3a_sweep/
"""
from __future__ import annotations
import argparse
import csv
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SMOKE = HERE / 'phase1_smoke.py'
VENV_PYTHON = REPO / '.venv' / 'bin' / 'python'


# Variant definitions: name → env override dict
VARIANTS = {
    # baselines
    'v3a_default': {},  # current defaults: margin=1, rt=3, slack>=2, greedy=off, strict
    'beta_v2d': '__BETA_AGENT__',  # use zoo_reflex_rc_tempo_beta (reference)

    # margin sweep
    'v3a_m0': {'V3A_MARGIN': '0'},
    'v3a_m2': {'V3A_MARGIN': '2'},

    # risk threshold sweep (more food eligible)
    'v3a_rt5': {'V3A_RISK_THRESHOLD': '5'},
    'v3a_rt10': {'V3A_RISK_THRESHOLD': '10'},

    # greedy fallback on unreachable
    'v3a_greedy': {'V3A_GREEDY_FALLBACK': '1'},
    'v3a_m0_greedy': {'V3A_MARGIN': '0', 'V3A_GREEDY_FALLBACK': '1'},

    # loose trigger (opp_pacman >= 1 instead of ==1)
    'v3a_loose': {'V3A_TRIGGER_MODE': 'loose'},
    'v3a_loose_greedy': {'V3A_TRIGGER_MODE': 'loose', 'V3A_GREEDY_FALLBACK': '1'},

    # slack_min=1 (more aggressive slack grab)
    'v3a_slack1': {'V3A_SLACK_MIN': '1', 'V3A_RISK_THRESHOLD': '5'},

    # Combo: best-case of reasonable tuning
    'v3a_combo': {'V3A_MARGIN': '0', 'V3A_GREEDY_FALLBACK': '1',
                   'V3A_RISK_THRESHOLD': '5', 'V3A_SLACK_MIN': '1'},
}


def run_variant(name, env_dict, agent_name, opponents, layouts, colors,
                 games_per_cell, workers, max_moves, out_csv):
    env = os.environ.copy()
    if isinstance(env_dict, dict):
        env.update(env_dict)
    cmd = [
        str(VENV_PYTHON), str(SMOKE),
        '--agent', agent_name,
        '--opponents'] + opponents + [
        '--layouts'] + layouts + [
        '--colors'] + colors + [
        '--games-per-cell', str(games_per_cell),
        '--workers', str(workers),
        '--max-moves', str(max_moves),
        '--out', str(out_csv),
    ]
    t0 = time.time()
    print(f"\n[sweep] ▶ variant={name} (env={env_dict if isinstance(env_dict, dict) else 'n/a'})",
          flush=True)
    result = subprocess.run(cmd, env=env, cwd=str(REPO))
    wall = time.time() - t0
    print(f"[sweep] ✓ variant={name} done in {wall:.1f}s (rc={result.returncode})",
          flush=True)
    return wall


def summarize_sweep(csv_paths):
    """Aggregate post-trigger metrics across all variants."""
    rows = []
    for name, path in csv_paths.items():
        if not path.exists():
            continue
        total = {'n_total': 0, 'n_triggered': 0, 'cap_post': 0,
                 'died_post': 0, 'sum_moves': 0, 'sum_food': 0,
                 'sum_wall': 0.0, 'score_wins': 0}
        with path.open() as f:
            for r in csv.DictReader(f):
                total['n_total'] += 1
                total['sum_wall'] += float(r.get('wall_sec', 0) or 0)
                if int(r.get('triggered', 0)):
                    total['n_triggered'] += 1
                    total['cap_post'] += int(r.get('cap_eaten_post_trigger', 0))
                    total['died_post'] += int(r.get('a_died_post_trigger', 0))
                    mpt = int(r.get('moves_post_trigger', -1))
                    if mpt >= 0:
                        total['sum_moves'] += mpt
                    total['sum_food'] += int(r.get('a_food_post_trigger', 0))
                sc = int(float(r.get('score', 0) or 0))
                col = r.get('color', 'red')
                if (sc > 0 and col == 'red') or (sc < 0 and col == 'blue'):
                    total['score_wins'] += 1
        if total['n_total'] == 0:
            continue
        n_t = total['n_total']
        n_g = max(1, total['n_triggered'])
        rows.append({
            'variant': name,
            'n': n_t,
            'trg%': f"{total['n_triggered']*100.0/n_t:.0f}",
            'cap%': f"{total['cap_post']*100.0/n_g:.1f}",
            'die%': f"{total['died_post']*100.0/n_g:.1f}",
            'mov_post': f"{total['sum_moves']/n_g:.0f}",
            'food_post': f"{total['sum_food']/n_g:.2f}",
            'WR%': f"{total['score_wins']*100.0/n_t:.1f}",
            'wall_s': f"{total['sum_wall']/n_t:.2f}",
        })

    # Score each variant: (cap% + food_per_trig) - die%
    def score(r):
        try:
            cap = float(r['cap%'])
            die = float(r['die%'])
            food = float(r['food_post'])
            return cap - die * 2 + food * 5  # weight: capsule primary, food bonus
        except Exception:
            return -1e9
    rows.sort(key=score, reverse=True)

    # Print table
    print("\n=== v3a Sweep Comparison (post-trigger metrics) ===")
    print(f"{'variant':<22} {'n':>4} {'trg%':>5} {'cap%':>6} {'die%':>6} "
          f"{'mov':>5} {'food':>6} {'WR%':>6} {'wall':>6} {'score':>7}")
    print("-" * 92)
    for r in rows:
        print(f"{r['variant']:<22} {r['n']:>4} {r['trg%']:>5} {r['cap%']:>6} "
              f"{r['die%']:>6} {r['mov_post']:>5} {r['food_post']:>6} "
              f"{r['WR%']:>6} {r['wall_s']:>6} {score(r):>7.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--games-per-cell', type=int, default=5)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--max-moves', type=int, default=600)
    ap.add_argument('--out-dir', type=Path, default=Path('/tmp/v3a_sweep'))
    ap.add_argument('--opponents', nargs='+', default=[
        'baseline', 'zoo_reflex_rc82', 'zoo_reflex_rc166',
        'zoo_reflex_rc32', 'zoo_reflex_rc02', 'monster_rule_expert',
    ])
    ap.add_argument('--layouts', nargs='+', default=['defaultCapture', 'distantCapture'])
    ap.add_argument('--colors', nargs='+', default=['red', 'blue'])
    ap.add_argument('--variants', nargs='+', default=None,
                    help='Subset of variants to run (default: all)')
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    selected = args.variants or list(VARIANTS.keys())
    csv_paths = {}
    total_start = time.time()
    for name in selected:
        if name not in VARIANTS:
            print(f"[sweep] ! unknown variant '{name}', skipping")
            continue
        env_dict = VARIANTS[name]
        if env_dict == '__BETA_AGENT__':
            agent = 'zoo_reflex_rc_tempo_beta'
            env_dict_pass = {}
        else:
            agent = 'zoo_reflex_rc_tempo_beta_v3a'
            env_dict_pass = env_dict
        csv_path = args.out_dir / f"{name}.csv"
        csv_paths[name] = csv_path
        run_variant(name, env_dict_pass, agent,
                     args.opponents, args.layouts, args.colors,
                     args.games_per_cell, args.workers, args.max_moves,
                     csv_path)

    total_wall = time.time() - total_start
    print(f"\n[sweep] All variants done in {total_wall:.0f}s")
    summarize_sweep(csv_paths)


if __name__ == '__main__':
    main()

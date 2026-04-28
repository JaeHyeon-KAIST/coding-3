"""pm46 v2 — Rebuild clean CSV from per-game log files.

Bypasses the bash grep -c "0\\n0" bug in pm46_v2_a_solo_matrix_corrected.sh by
re-parsing each per-game log file in pure Python.

Run on either Mac or sts (just point at logs dir):
    .venv/bin/python experiments/rc_tempo/pm46_v2_rebuild_csv.py \\
        --logs-dir experiments/results/pm46_v2/logs_corrected \\
        --out      experiments/results/pm46_v2/abs_baseline_corrected_clean.csv

Filename pattern: <DEFENDER>_seed<N>.log

CSV columns:
    defender, seed, outcome, first_eat_tick, total_caps_eaten,
    a_died_within_3, a_total_deaths, score, wall_s
"""
from __future__ import annotations
import argparse
import csv
import os
import re
import sys
from pathlib import Path


CAP_EATEN_RE = re.compile(r'\[ABS_CAP_EATEN\] tick=(\d+)')
A_DIED_RE = re.compile(r'\[ABS_A_DIED\] tick=(\d+)')
AVG_SCORE_RE = re.compile(r'Average Score:\s*(-?[\d.]+)')
LOG_NAME_RE = re.compile(r'^(?P<def>.+)_seed(?P<seed>\d+)\.log$')


def classify(eat_ticks, died_ticks, score_present):
    """Classify game outcome from event lists.

    eat_ticks: list of int (timeleft values when caps were eaten — DECREASING)
    died_ticks: list of int (timeleft values when A respawned)
    score_present: bool (Average Score line found → game completed)
    """
    if not score_present:
        return 'timeout', None, False
    if eat_ticks:
        first_eat = max(eat_ticks)  # earliest chronologically (timeleft DECREASES)
        died_within_3 = any(
            (first_eat - dt) <= 3 and (first_eat - dt) >= 0
            for dt in died_ticks
        )
        return ('eat_died' if died_within_3 else 'eat_alive', first_eat, died_within_3)
    if died_ticks:
        return 'no_eat_died', None, False
    return 'no_eat_alive', None, False


def parse_log(path: Path) -> dict | None:
    """Parse a single per-game log into a CSV row dict."""
    m = LOG_NAME_RE.match(path.name)
    if not m:
        return None
    defender = m.group('def')
    seed = int(m.group('seed'))

    eat_ticks = []
    died_ticks = []
    score = None
    score_present = False

    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                m1 = CAP_EATEN_RE.search(line)
                if m1:
                    eat_ticks.append(int(m1.group(1)))
                    continue
                m2 = A_DIED_RE.search(line)
                if m2:
                    died_ticks.append(int(m2.group(1)))
                    continue
                m3 = AVG_SCORE_RE.search(line)
                if m3:
                    try:
                        score = float(m3.group(1))
                    except ValueError:
                        score = None
                    score_present = True
    except OSError:
        return None

    outcome, first_eat, died_within_3 = classify(eat_ticks, died_ticks, score_present)
    return {
        'defender': defender,
        'seed': seed,
        'outcome': outcome,
        'first_eat_tick': first_eat if first_eat is not None else '',
        'total_caps_eaten': len(eat_ticks),
        'a_died_within_3': 'true' if died_within_3 else 'false',
        'a_total_deaths': len(died_ticks),
        'score': score if score is not None else '',
        'wall_s': '',  # not available from logs alone
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--logs-dir', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()

    logs_dir = Path(args.logs_dir)
    if not logs_dir.is_dir():
        print(f'FAIL: not a directory: {logs_dir}', file=sys.stderr)
        sys.exit(1)

    rows = []
    for log_path in sorted(logs_dir.iterdir()):
        if not log_path.is_file() or not log_path.name.endswith('.log'):
            continue
        row = parse_log(log_path)
        if row is not None:
            rows.append(row)

    if not rows:
        print('WARN: no rows parsed', file=sys.stderr)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cols = ['defender', 'seed', 'outcome', 'first_eat_tick', 'total_caps_eaten',
            'a_died_within_3', 'a_total_deaths', 'score', 'wall_s']
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # Summary.
    total = len(rows)
    by_outcome = {}
    by_def = {}
    for r in rows:
        by_outcome[r['outcome']] = by_outcome.get(r['outcome'], 0) + 1
        d = r['defender']
        by_def.setdefault(d, {'eat_alive': 0, 'eat_died': 0, 'no_eat_alive': 0,
                              'no_eat_died': 0, 'timeout': 0, 'total': 0})
        by_def[d][r['outcome']] = by_def[d].get(r['outcome'], 0) + 1
        by_def[d]['total'] += 1

    print(f'Wrote {total} rows -> {out_path}')
    print(f'Aggregate: {dict(sorted(by_outcome.items()))}')
    if total:
        ea = by_outcome.get('eat_alive', 0)
        ed = by_outcome.get('eat_died', 0)
        nd = by_outcome.get('no_eat_died', 0)
        print(f'cap_eat_alive_pct = {100.0 * ea / total:.1f}%')
        print(f'died_pre_eat_pct  = {100.0 * nd / total:.1f}%')
        print(f'eat_died_pct      = {100.0 * ed / total:.1f}%')

    print()
    print('Per-defender breakdown:')
    print(f'{"defender":<32} eat_alive  eat_died  no_eat_alive  no_eat_died  timeout  total')
    for d, c in sorted(by_def.items()):
        print(f'{d:<32} {c.get("eat_alive", 0):>9}  {c.get("eat_died", 0):>8}  '
              f'{c.get("no_eat_alive", 0):>12}  {c.get("no_eat_died", 0):>11}  '
              f'{c.get("timeout", 0):>7}  {c["total"]:>5}')


if __name__ == '__main__':
    main()

"""pm46 v2 — Phase 4 analysis: CAPX vs ABS-baseline per-defender comparison.

Aggregates two CSVs (one ABS-baseline, one CAPX) and emits a comparison table
with per-defender cap_eat_alive % and died_pre_eat % deltas.

Run on either Mac or sts:
    .venv/bin/python experiments/rc_tempo/pm46_v2_compare_capx_vs_abs.py \\
        --abs experiments/results/pm46_v2/abs_baseline_corrected_clean.csv \\
        --capx experiments/results/pm46_v2/capx_tier_screen_m0.csv \\
        --out  experiments/results/pm46_v2/compare_phase4.md

Plan §3.3 acceptance bars (510 games each side):
    aggregate cap_eat_alive ≥ 50%  AND  died_pre_eat ≤ 60%
    ANY defender died_pre_eat ≥ 80% → FAIL (hard rule)
    Strict improvement on ≥ 12 of 17 defenders
"""
from __future__ import annotations
import argparse
import csv
from collections import defaultdict
from pathlib import Path


TIER_A = {
    'baseline', 'monster_rule_expert', 'zoo_minimax_ab_d3_opp',
    'zoo_reflex_defensive', 'zoo_reflex_A1', 'zoo_reflex_A1_D13', 'zoo_belief',
}
TIER_B = {
    'zoo_hybrid_mcts_reflex', 'zoo_minimax_ab_d2', 'zoo_reflex_A1_D1',
    'zoo_reflex_capsule', 'zoo_reflex_rc82',
}
TIER_C = {'zoo_dummy', 'zoo_reflex_aggressive', 'zoo_reflex_tuned'}
TIER_D = {'zoo_reflex_rc_tempo_beta_retro', 'zoo_reflex_rc_tempo_gamma'}

TIER_NAME = {}
for d in TIER_A: TIER_NAME[d] = 'A'
for d in TIER_B: TIER_NAME[d] = 'B'
for d in TIER_C: TIER_NAME[d] = 'C'
for d in TIER_D: TIER_NAME[d] = 'D'


def load_csv(path: Path) -> dict:
    """defender -> {outcome -> count, total}"""
    by_def = defaultdict(lambda: defaultdict(int))
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            d = row['defender']
            o = row['outcome']
            by_def[d][o] += 1
            by_def[d]['__total__'] += 1
    return by_def


def pct(n, total):
    if not total:
        return float('nan')
    return 100.0 * n / total


def fmt_pct(n, total):
    if not total:
        return '   N/A'
    return f'{pct(n, total):5.1f}%'


def aggregate(by_def: dict) -> dict:
    agg = defaultdict(int)
    for c in by_def.values():
        for k, v in c.items():
            agg[k] += v
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--abs', required=True, help='ABS-baseline CSV')
    ap.add_argument('--capx', required=True, help='CAPX CSV')
    ap.add_argument('--out', required=False, help='Markdown output (default stdout only)')
    args = ap.parse_args()

    abs_data = load_csv(Path(args.abs))
    capx_data = load_csv(Path(args.capx))

    all_defs = sorted(set(abs_data.keys()) | set(capx_data.keys()),
                      key=lambda d: (TIER_NAME.get(d, 'Z'), d))

    lines = []
    lines.append('# pm46 v2 Phase 4 — CAPX vs ABS-baseline\n')
    lines.append(f'- ABS:  {args.abs}')
    lines.append(f'- CAPX: {args.capx}\n')

    abs_agg = aggregate(abs_data)
    capx_agg = aggregate(capx_data)
    abs_total = abs_agg['__total__']
    capx_total = capx_agg['__total__']

    lines.append('## Aggregate\n')
    lines.append('| Metric | ABS | CAPX | Δ |')
    lines.append('|---|---:|---:|---:|')
    for outcome in ('eat_alive', 'eat_died', 'no_eat_alive', 'no_eat_died', 'timeout'):
        a = abs_agg[outcome]
        c = capx_agg[outcome]
        a_pct = pct(a, abs_total)
        c_pct = pct(c, capx_total)
        lines.append(f'| {outcome} | {a} ({a_pct:.1f}%) | {c} ({c_pct:.1f}%) | '
                     f'{c_pct - a_pct:+.1f}pp |')
    lines.append(f'| total | {abs_total} | {capx_total} | |\n')

    # Pass bars (plan §3.3).
    abs_eat_alive_pct = pct(abs_agg['eat_alive'], abs_total)
    capx_eat_alive_pct = pct(capx_agg['eat_alive'], capx_total)
    capx_died_pre_eat_pct = pct(capx_agg['no_eat_died'], capx_total)

    lines.append('## Plan §3.3 acceptance bars\n')
    lines.append(f'- aggregate cap_eat_alive ≥ 50%: '
                 f'**{capx_eat_alive_pct:.1f}%** '
                 f'{"PASS" if capx_eat_alive_pct >= 50 else "FAIL"}')
    lines.append(f'- aggregate died_pre_eat ≤ 60%: '
                 f'**{capx_died_pre_eat_pct:.1f}%** '
                 f'{"PASS" if capx_died_pre_eat_pct <= 60 else "FAIL"}')

    # Per-defender hard rule.
    fail_per_def = []
    for d in all_defs:
        c = capx_data.get(d, {})
        tot = c.get('__total__', 0)
        if tot == 0:
            continue
        nd_pct = pct(c.get('no_eat_died', 0), tot)
        if nd_pct >= 80.0:
            fail_per_def.append((d, nd_pct))
    if fail_per_def:
        lines.append('- **PER-DEFENDER HARD RULE FAIL** (died_pre_eat ≥ 80% on any defender):')
        for d, p in fail_per_def:
            lines.append(f'  - {d}: {p:.1f}%')
    else:
        lines.append('- per-defender died_pre_eat ≥ 80%: **PASS** (none)')
    lines.append('')

    # Per-defender comparison table.
    lines.append('## Per-defender breakdown\n')
    lines.append('| Tier | Defender | ABS eat_alive | CAPX eat_alive | Δ | CAPX died_pre_eat |')
    lines.append('|---|---|---:|---:|---:|---:|')
    improved = 0
    regressed = 0
    for d in all_defs:
        tier = TIER_NAME.get(d, '?')
        a = abs_data.get(d, {})
        c = capx_data.get(d, {})
        a_tot = a.get('__total__', 0)
        c_tot = c.get('__total__', 0)
        a_ea = pct(a.get('eat_alive', 0), a_tot)
        c_ea = pct(c.get('eat_alive', 0), c_tot)
        c_nd = pct(c.get('no_eat_died', 0), c_tot)
        delta = c_ea - a_ea if (a_tot and c_tot) else float('nan')
        if a_tot and c_tot:
            if c_ea > a_ea:
                improved += 1
            elif c_ea < a_ea:
                regressed += 1
        lines.append(f'| {tier} | {d} | '
                     f'{a.get("eat_alive", 0)}/{a_tot} ({a_ea:.1f}%) | '
                     f'{c.get("eat_alive", 0)}/{c_tot} ({c_ea:.1f}%) | '
                     f'{delta:+.1f}pp | '
                     f'{c.get("no_eat_died", 0)}/{c_tot} ({c_nd:.1f}%) |')
    lines.append(f'\nImproved: {improved} defenders. Regressed: {regressed}. '
                 f'Strict-improvement gate (≥12 of 17): '
                 f'{"PASS" if improved >= 12 else "FAIL"}')
    lines.append('')

    out = '\n'.join(lines)
    print(out)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(out, encoding='utf-8')
        print(f'\nWrote: {args.out}')


if __name__ == '__main__':
    main()

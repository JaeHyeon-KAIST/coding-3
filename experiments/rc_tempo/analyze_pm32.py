#!/usr/bin/env python3
"""pm32 analysis script — composite-sorted ranking + Pearson r + markdown emit.

REFUSES to sort by WR (per pm32 plan §6.C.1.d MINOR #15) — composite-only
ranking, WR shown as advisory column with footnote.

CLI:
    --t1-dir <path>          T1 sweep dir (optional; for context table)
    --t2-dir <path>          T2 sweep dir (REQUIRED — primary ranking source)
    --f3-dir <path>          F3 HTH sweep dir (optional; for r calibration)
    --baseline <name>        default beta_path4
    --out-md <path>          markdown report
    --dry-run                print to stdout, do not write file

Per Critic-U iter-3: per-opp breakdown columns explicit
   (opp, n, cap%, cap%_ci, die%, die%_ci, wr%, wr%_ci, mean_wall_sec)
Per v2 #75: per-fixed-layout T2 vs F3 row.
"""
from __future__ import annotations
import argparse
import csv
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from composite import (compute_score, wilson_ci_95, pearson_with_ci,
                        spearman_rho)  # noqa: E402

FIXED_LAYOUTS = ['defaultCapture', 'distantCapture', 'strategicCapture',
                  'testCapture']


def aggregate_phase1_csv(csv_path):
    """Aggregate phase1_smoke.FIELDS-format CSV (T1/T2). Returns per-(opp,layout)
    breakdown plus overall."""
    p = Path(csv_path)
    if not p.exists():
        return None
    overall = {'n_total': 0, 'n_triggered': 0, 'cap_post': 0,
                'died_post': 0, 'sum_food': 0, 'score_wins': 0, 'sum_wall': 0.0}
    per_opp = {}
    per_layout = {}
    with p.open() as f:
        for r in csv.DictReader(f):
            overall['n_total'] += 1
            try:
                wall = float(r.get('wall_sec', 0) or 0)
            except Exception:
                wall = 0.0
            overall['sum_wall'] += wall
            try:
                triggered = int(r.get('triggered', 0) or 0)
            except Exception:
                triggered = 0
            try:
                cap_post = int(r.get('cap_eaten_post_trigger', 0) or 0)
                died_post = int(r.get('a_died_post_trigger', 0) or 0)
                food_post = int(r.get('a_food_post_trigger', 0) or 0)
            except Exception:
                cap_post = died_post = food_post = 0
            try:
                sc = int(float(r.get('score', 0) or 0))
                col = r.get('color', 'red')
                wins = int((sc > 0 and col == 'red') or (sc < 0 and col == 'blue'))
            except Exception:
                wins = 0
            opp = r.get('opp', '?')
            lay = r.get('layout', '?')
            for d in (per_opp.setdefault(opp, {'n_total': 0, 'n_triggered': 0,
                                                'cap_post': 0, 'died_post': 0,
                                                'sum_food': 0, 'score_wins': 0,
                                                'sum_wall': 0.0}),
                       per_layout.setdefault(lay, {'n_total': 0, 'n_triggered': 0,
                                                    'cap_post': 0, 'died_post': 0,
                                                    'sum_food': 0, 'score_wins': 0,
                                                    'sum_wall': 0.0}),
                       overall):
                d['n_total'] += 1
                d['sum_wall'] += wall
                d['score_wins'] += wins
                if triggered:
                    d['n_triggered'] += 1
                    d['cap_post'] += cap_post
                    d['died_post'] += died_post
                    d['sum_food'] += food_post
    if overall['n_total'] == 0:
        return None
    return {'overall': overall, 'per_opp': per_opp, 'per_layout': per_layout}


def aggregate_hth_csv(csv_path, agent_name):
    """Aggregate hth_resumable.FIELDS-format CSV (F3). Returns wr_per_(opp,layout)
    plus overall WR. Filters to rows where agent_a == agent_name."""
    p = Path(csv_path)
    if not p.exists():
        return None
    overall = {'n_total': 0, 'wins': 0, 'crashes': 0, 'sum_wall': 0.0}
    per_opp = {}
    per_layout = {}
    per_lay_only = {}  # layout-only WR (combines opps)
    with p.open() as f:
        for r in csv.DictReader(f):
            if r.get('agent_a', '') != agent_name:
                continue
            overall['n_total'] += 1
            try:
                wall = float(r.get('wall_sec', 0) or 0)
            except Exception:
                wall = 0.0
            overall['sum_wall'] += wall
            try:
                crashed = int(r.get('crashed', 0) or 0)
                rw = int(r.get('red_win', 0) or 0)
                bw = int(r.get('blue_win', 0) or 0)
                col = r.get('color', 'red')
            except Exception:
                crashed = rw = bw = 0
                col = 'red'
            overall['crashes'] += crashed
            wins = rw if col == 'red' else bw
            overall['wins'] += wins
            opp = r.get('opp', '?')
            lay = r.get('layout', '?')
            for d in (per_opp.setdefault(opp, {'n_total': 0, 'wins': 0,
                                                'crashes': 0, 'sum_wall': 0.0}),
                       per_layout.setdefault(lay, {'n_total': 0, 'wins': 0,
                                                    'crashes': 0, 'sum_wall': 0.0}),
                       per_lay_only.setdefault(lay, {'n_total': 0, 'wins': 0,
                                                     'crashes': 0, 'sum_wall': 0.0})):
                d['n_total'] += 1
                d['sum_wall'] += wall
                d['wins'] += wins
                d['crashes'] += crashed
    if overall['n_total'] == 0:
        return None
    return {'overall': overall, 'per_opp': per_opp,
            'per_layout': per_layout, 'per_lay_only': per_lay_only}


def _emit_per_opp_breakdown(per_opp, lines):
    """Per-opp breakdown table (Critic-U)."""
    lines.append("")
    lines.append("### Per-opponent breakdown")
    lines.append("")
    lines.append("| opp | n | cap% | cap%_ci | die% | die%_ci | wr% | wr%_ci | mean_wall_sec |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for opp, d in sorted(per_opp.items()):
        n_t = max(1, d['n_triggered'])
        n_w = max(1, d['n_total'])
        cap_lo, cap_hi = wilson_ci_95(d['cap_post'], n_t)
        die_lo, die_hi = wilson_ci_95(d['died_post'], n_t)
        wr_lo, wr_hi = wilson_ci_95(d['score_wins'], n_w)
        mean_wall = d['sum_wall'] / n_w
        lines.append(
            f"| {opp} | {d['n_total']} "
            f"| {d['cap_post']*100.0/n_t:.1f} "
            f"| [{cap_lo*100:.1f},{cap_hi*100:.1f}] "
            f"| {d['died_post']*100.0/n_t:.1f} "
            f"| [{die_lo*100:.1f},{die_hi*100:.1f}] "
            f"| {d['score_wins']*100.0/n_w:.1f} "
            f"| [{wr_lo*100:.1f},{wr_hi*100:.1f}] "
            f"| {mean_wall:.2f} |"
        )


def _ship_verdict(r, r_lo, r_hi, rho):
    """Apply MJ-3 conjunction rule. Returns (verdict, reason)."""
    if math.isnan(r):
        return ('UNUSABLE', 'F3 calibration N too small or invalid (NaN r)')
    if r < 0.5:
        return ('UNUSABLE', f'r={r:.3f} < 0.5; metric does not predict HTH WR')
    diff_disagree = (not math.isnan(rho)) and abs(r - rho) > 0.2
    if diff_disagree:
        return ('PROVISIONAL',
                f'|r - ρ|={abs(r - rho):.3f} > 0.2; rank-correlation '
                f'disagrees with linear')
    if r >= 0.7 and not math.isnan(r_lo) and r_lo > 0.3 and \
            (not math.isnan(rho)) and rho >= 0.7:
        return ('SHIP',
                f'r={r:.3f}, CI lower={r_lo:.3f}, ρ={rho:.3f} all clear')
    if r >= 0.7:
        return ('PROVISIONAL',
                f'r={r:.3f} but CI lower={r_lo:.3f} ≤ 0.3 OR ρ={rho:.3f} < 0.7')
    return ('PROVISIONAL', f'0.5 ≤ r={r:.3f} < 0.7')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--t1-dir', type=Path, default=None)
    ap.add_argument('--t2-dir', type=Path, required=True)
    ap.add_argument('--f3-dir', type=Path, default=None)
    ap.add_argument('--baseline', default='beta_path4')
    ap.add_argument('--out-md', type=Path, default=None)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--sort-by', default='composite',
                     help='Composite-only allowed. WR-sorting is REJECTED.')
    args = ap.parse_args()

    if args.sort_by != 'composite':
        print(f"ERROR: --sort-by '{args.sort_by}' not allowed. pm32 plan "
              f"MINOR #15 forbids WR-sorting. Use composite (default).",
              file=sys.stderr)
        sys.exit(2)

    if not args.t2_dir.exists():
        print(f"ERROR: --t2-dir {args.t2_dir} does not exist", file=sys.stderr)
        sys.exit(2)

    # Aggregate T2
    t2_data = {}
    for csv_path in sorted(args.t2_dir.glob('*.csv')):
        if csv_path.name == 'wall_summary.csv':
            continue
        name = csv_path.stem
        agg = aggregate_phase1_csv(csv_path)
        if agg is not None:
            t2_data[name] = agg

    if not t2_data:
        print(f"ERROR: no T2 CSVs in {args.t2_dir}", file=sys.stderr)
        sys.exit(2)

    # Compute composite per variant
    ranking = []
    for name, agg in t2_data.items():
        score = compute_score(agg['overall'])
        n_t = max(1, agg['overall']['n_triggered'])
        n_w = max(1, agg['overall']['n_total'])
        cap_lo, cap_hi = wilson_ci_95(agg['overall']['cap_post'], n_t)
        die_lo, die_hi = wilson_ci_95(agg['overall']['died_post'], n_t)
        wr_lo, wr_hi = wilson_ci_95(agg['overall']['score_wins'], n_w)
        ranking.append({
            'name': name,
            'score': score,
            'cap_pct': agg['overall']['cap_post'] * 100.0 / n_t,
            'cap_ci': (cap_lo * 100.0, cap_hi * 100.0),
            'die_pct': agg['overall']['died_post'] * 100.0 / n_t,
            'die_ci': (die_lo * 100.0, die_hi * 100.0),
            'wr_pct': agg['overall']['score_wins'] * 100.0 / n_w,
            'wr_ci': (wr_lo * 100.0, wr_hi * 100.0),
            'n': agg['overall']['n_total'],
            'n_triggered': agg['overall']['n_triggered'],
            'agg': agg,
        })

    ranking.sort(key=lambda r: r['score'], reverse=True)

    lines = []
    lines.append(f"# pm32 Analysis — T2 ranking + F3 calibration\n")
    lines.append(f"- T1 dir: {args.t1_dir or '(not provided)'}")
    lines.append(f"- T2 dir: {args.t2_dir}")
    lines.append(f"- F3 dir: {args.f3_dir or '(not provided)'}")
    lines.append(f"- Baseline: `{args.baseline}`")
    lines.append("")
    lines.append("## Headline ranking (composite-sorted)")
    lines.append("")
    lines.append("WR shown as advisory column. **WR is partial-game score at "
                 "cutoff per pm31 lesson; use F3 HTH for game-outcome metric.**")
    lines.append("")
    lines.append("| rank | variant | score | cap% | cap_ci | die% | die_ci | wr% (advisory) | wr_ci | n |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(ranking, 1):
        lines.append(
            f"| {i} | `{r['name']}` | {r['score']:.2f} | "
            f"{r['cap_pct']:.2f} | [{r['cap_ci'][0]:.2f},{r['cap_ci'][1]:.2f}] | "
            f"{r['die_pct']:.2f} | [{r['die_ci'][0]:.2f},{r['die_ci'][1]:.2f}] | "
            f"{r['wr_pct']:.2f} | [{r['wr_ci'][0]:.2f},{r['wr_ci'][1]:.2f}] | "
            f"{r['n']} |"
        )

    # Per-variant per-opp breakdowns (top 5 by composite)
    lines.append("")
    lines.append("## Per-opponent breakdowns (top 5 by composite)")
    for r in ranking[:5]:
        lines.append("")
        lines.append(f"### `{r['name']}`")
        _emit_per_opp_breakdown(r['agg']['per_opp'], lines)

    # F3 HTH calibration
    if args.f3_dir is not None and args.f3_dir.exists():
        f3_data = {}
        for csv_path in sorted(args.f3_dir.glob('*.csv')):
            if csv_path.name == 'wall_summary.csv':
                continue
            name = csv_path.stem
            agg = aggregate_hth_csv(csv_path, name)
            if agg is not None:
                f3_data[name] = agg

        # Pearson + Spearman over variants present in BOTH t2 and f3
        common = sorted(set(t2_data.keys()) & set(f3_data.keys()))
        composite_xs = [next(r['score'] for r in ranking if r['name'] == n)
                         for n in common]
        hth_wr_ys = []
        for n in common:
            d = f3_data[n]['overall']
            hth_wr_ys.append(d['wins'] * 100.0 / max(1, d['n_total']))
        r, r_lo, r_hi = pearson_with_ci(composite_xs, hth_wr_ys)
        rho = spearman_rho(composite_xs, hth_wr_ys)
        verdict, reason = _ship_verdict(r, r_lo, r_hi, rho)

        lines.append("")
        lines.append("## F3 HTH Calibration (Phase 1 composite ↔ HTH WR)")
        lines.append("")
        lines.append(f"- N variants in calibration: **{len(common)}**")
        lines.append(f"- Pearson r: **{r:.3f}** (95% CI: "
                      f"[{r_lo:.3f}, {r_hi:.3f}], approximate via Fisher z; "
                      f"not exact for N<30)")
        lines.append(f"- Spearman ρ: **{rho:.3f}**")
        if not math.isnan(r) and not math.isnan(rho):
            agree_flag = ('INCONSISTENT' if abs(r - rho) > 0.2
                          else 'consistent')
            lines.append(f"- |r - ρ|: {abs(r - rho):.3f} ({agree_flag})")
        lines.append(f"- **Verdict: {verdict}** — {reason}")
        lines.append("")
        lines.append("### Per-variant calibration table")
        lines.append("")
        lines.append("| variant | composite (T2) | HTH WR % (F3) |")
        lines.append("|---|---|---|")
        for n, x, y in zip(common, composite_xs, hth_wr_ys):
            lines.append(f"| `{n}` | {x:.2f} | {y:.2f} |")

        # Per-fixed-layout T2 vs F3 rows (v2 #75)
        lines.append("")
        lines.append("### Per-fixed-layout T2 cap%/wr% vs F3 wr% (top 3 by composite)")
        lines.append("")
        lines.append("| variant | layout | T2 cap% | T2 wr% | F3 wr% |")
        lines.append("|---|---|---|---|---|")
        for r_top in ranking[:3]:
            name = r_top['name']
            for lay in FIXED_LAYOUTS:
                t2_lay = r_top['agg']['per_layout'].get(lay)
                f3_lay = f3_data.get(name, {}).get('per_lay_only', {}).get(lay)
                if t2_lay is None and f3_lay is None:
                    continue
                t2_n_t = max(1, t2_lay['n_triggered']) if t2_lay else 1
                t2_n = max(1, t2_lay['n_total']) if t2_lay else 1
                t2_cap = (t2_lay['cap_post'] * 100.0 / t2_n_t) if t2_lay else float('nan')
                t2_wr = (t2_lay['score_wins'] * 100.0 / t2_n) if t2_lay else float('nan')
                f3_wr = (f3_lay['wins'] * 100.0 /
                          max(1, f3_lay['n_total'])) if f3_lay else float('nan')
                lines.append(f"| `{name}` | {lay} | {t2_cap:.1f} | "
                              f"{t2_wr:.1f} | {f3_wr:.1f} |")
    else:
        lines.append("")
        lines.append("## F3 HTH Calibration")
        lines.append("")
        lines.append("(F3 dir not provided. Calibration deferred to next run.)")
        lines.append(f"- Pearson r: **NaN** (no F3 data)")

    md = "\n".join(lines) + "\n"

    if args.dry_run or args.out_md is None:
        print(md)
        return
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md)
    print(f"Wrote markdown to {args.out_md}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""pm32 T1 → T2 promotion script.

Reads per-variant CSVs from a T1 sweep output dir, applies data-quality
pre-filter, die-ceiling filter, computes composite via composite.compute_score,
sorts, then writes the top-N (with optional buffer + force-includes +
conditional angle stratification) to a text file consumed by T2.

Defaults are LOCKED per pm32 plan §6.C.1.c (MJ-4 + MJ-5):
    --top-n 12 --buffer-pp 2.0 --die-ceiling 2.5 --stratify-angles
    --stratify-tolerance-pp 5.0 --data-quality-check
    --force-include beta_v2d beta_path4 beta_slack3 beta_retro

Operator can override any of these. --dry-run prints the ranking but does NOT
write the output file.

Usage:
    .venv/bin/python experiments/rc_tempo/promote_t1_to_t2.py \\
        --t1-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_t1/ \\
        --out experiments/rc_tempo/pm32_t2_variants.txt
"""
from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from composite import compute_score, wilson_ci_95  # noqa: E402

ANGLE_PREFIXES = ['pm32_p1_', 'pm32_aa_', 'pm32_ac_', 'pm32_rs_']


def aggregate_csv(csv_path):
    """Return dict with n_total, n_triggered, cap_post, died_post, sum_food,
    crashed_count for a single variant's CSV. Returns None if CSV missing/empty.
    """
    p = Path(csv_path)
    if not p.exists():
        return None
    agg = {'n_total': 0, 'n_triggered': 0, 'cap_post': 0,
           'died_post': 0, 'sum_food': 0, 'crashed_count': 0}
    with p.open() as f:
        reader = csv.DictReader(f)
        for r in reader:
            agg['n_total'] += 1
            try:
                if int(r.get('crashed', 0) or 0):
                    agg['crashed_count'] += 1
            except Exception:
                pass
            try:
                if int(r.get('triggered', 0) or 0):
                    agg['n_triggered'] += 1
                    agg['cap_post'] += int(r.get('cap_eaten_post_trigger', 0) or 0)
                    agg['died_post'] += int(r.get('a_died_post_trigger', 0) or 0)
                    agg['sum_food'] += int(r.get('a_food_post_trigger', 0) or 0)
            except Exception:
                pass
    if agg['n_total'] == 0:
        return None
    return agg


def angle_of(name):
    for pref in ANGLE_PREFIXES:
        if name.startswith(pref):
            return pref.rstrip('_')
    return None


def _t1_total_wall_h(t1_dir):
    """Sum wall_sec across all variants in wall_summary.csv (NOT tail -1).

    Returns hours, or None if file missing/empty.
    """
    p = Path(t1_dir) / 'wall_summary.csv'
    if not p.exists():
        return None
    total_sec = 0.0
    n = 0
    try:
        with p.open() as f:
            for r in csv.DictReader(f):
                try:
                    total_sec += float(r.get('wall_sec', 0) or 0)
                    n += 1
                except Exception:
                    pass
    except Exception:
        return None
    if n == 0:
        return None
    return total_sec / 3600.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--t1-dir', type=Path, required=True)
    ap.add_argument('--top-n', type=int, default=12)
    ap.add_argument('--buffer-pp', type=float, default=2.0,
                     help='admit variants within N pp of #top-n composite')
    ap.add_argument('--die-ceiling', type=float, default=2.5,
                     help='reject variants with die%%_upper_wilson > ceiling')
    ap.add_argument('--stratify-angles', action='store_true', default=True,
                     help='conditional ≥1 per angle (default ON)')
    ap.add_argument('--no-stratify-angles', action='store_false',
                     dest='stratify_angles')
    ap.add_argument('--stratify-tolerance-pp', type=float, default=5.0,
                     help="angle's best must be within X pp of #top-N composite")
    ap.add_argument('--data-quality-check', action='store_true', default=True)
    ap.add_argument('--no-data-quality-check', action='store_false',
                     dest='data_quality_check')
    ap.add_argument('--expected-n', type=int, default=1760,
                     help='expected total games per variant (T1: '
                          '11 opp × 16 lay × 2 col × 5g = 1760)')
    ap.add_argument('--force-include', nargs='+',
                     default=['beta_v2d', 'beta_path4', 'beta_slack3', 'beta_retro'])
    ap.add_argument('--out', type=Path, default=None)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    if not args.t1_dir.exists():
        print(f"ERROR: --t1-dir {args.t1_dir} does not exist", file=sys.stderr)
        sys.exit(2)

    # Aggregate per-variant
    csv_files = sorted(args.t1_dir.glob('*.csv'))
    csv_files = [c for c in csv_files if c.name != 'wall_summary.csv']
    aggregates = {}
    for csv_path in csv_files:
        name = csv_path.stem
        agg = aggregate_csv(csv_path)
        if agg is None:
            continue
        aggregates[name] = agg

    if not aggregates:
        print(f"ERROR: no usable variant CSVs in {args.t1_dir}", file=sys.stderr)
        sys.exit(2)

    # Data-quality pre-filter (MJ-5, default ON)
    excluded_dq = {}
    if args.data_quality_check:
        for name in list(aggregates.keys()):
            agg = aggregates[name]
            n = agg['n_total']
            crash_pct = (agg['crashed_count'] * 100.0 / n) if n > 0 else 0.0
            min_n = args.expected_n * 0.8
            reasons = []
            if n < min_n:
                reasons.append(f"n={n} < expected×0.8={min_n:.0f}")
            if crash_pct > 5.0:
                reasons.append(f"crashed%={crash_pct:.1f} > 5%")
            if reasons:
                excluded_dq[name] = '; '.join(reasons)

    # Compute composite + die-ceiling on remaining
    rows = []
    for name, agg in aggregates.items():
        if name in excluded_dq:
            continue
        n_g = max(1, agg['n_triggered'])
        cap_lo, cap_hi = wilson_ci_95(agg['cap_post'], n_g)
        die_lo, die_hi = wilson_ci_95(agg['died_post'], n_g)
        # Convert to percent
        die_hi_pct = die_hi * 100.0
        cap_pct = agg['cap_post'] * 100.0 / n_g
        die_pct = agg['died_post'] * 100.0 / n_g
        score = compute_score(agg)
        rows.append({
            'name': name,
            'score': score,
            'cap_pct': cap_pct,
            'cap_ci_lo_pct': cap_lo * 100.0,
            'cap_ci_hi_pct': cap_hi * 100.0,
            'die_pct': die_pct,
            'die_ci_lo_pct': die_lo * 100.0,
            'die_ci_hi_pct': die_hi_pct,
            'n_triggered': agg['n_triggered'],
            'n_total': agg['n_total'],
            'angle': angle_of(name),
        })

    # Apply die ceiling
    excluded_die = {}
    survivors = []
    for r in rows:
        if r['die_ci_hi_pct'] > args.die_ceiling:
            excluded_die[r['name']] = (
                f"die%_upper_wilson={r['die_ci_hi_pct']:.2f} > ceiling="
                f"{args.die_ceiling}"
            )
        else:
            survivors.append(r)

    survivors.sort(key=lambda r: r['score'], reverse=True)

    # Pick top-N + buffer
    top_score = survivors[args.top_n - 1]['score'] if len(survivors) >= args.top_n else (survivors[-1]['score'] if survivors else 0.0)
    buffer_floor = top_score - args.buffer_pp
    selected = []
    for r in survivors:
        if len(selected) < args.top_n:
            selected.append(r)
        elif r['score'] >= buffer_floor:
            selected.append(r)
        else:
            break
    selected_names = set(r['name'] for r in selected)

    # Force-includes
    forced_include = []
    for name in args.force_include:
        if name in selected_names:
            continue
        if name in aggregates and name not in excluded_dq:
            # Add even if die-ceiling fails — these are forced reference variants
            r = next((x for x in rows if x['name'] == name), None)
            if r is None:
                continue
            forced_include.append(r)
            selected_names.add(name)
        else:
            print(f"WARN: --force-include '{name}' not in T1 dir or excluded "
                  f"by data-quality; skipping", file=sys.stderr)

    # Conditional stratification by angle (MJ-4)
    stratified = []
    skipped_angles = []
    if args.stratify_angles:
        # For each angle, find the angle's BEST variant in survivors
        for pref in ANGLE_PREFIXES:
            angle = pref.rstrip('_')
            angle_best = None
            for r in survivors:
                if r['name'].startswith(pref):
                    if angle_best is None or r['score'] > angle_best['score']:
                        angle_best = r
            if angle_best is None:
                continue
            if angle_best['name'] in selected_names:
                continue
            # Already passed die-ceiling (in survivors). Check tolerance.
            delta = top_score - angle_best['score']
            if delta > args.stratify_tolerance_pp:
                skipped_angles.append(
                    f"STRATIFY SKIPPED for angle {angle}: best="
                    f"{angle_best['name']} score={angle_best['score']:.2f} "
                    f"Δ={delta:.2f}pp > tol={args.stratify_tolerance_pp}"
                )
                continue
            stratified.append(angle_best)
            selected_names.add(angle_best['name'])

    # Combine final list (dedupe preserves selection order)
    final_rows = list(selected)
    for r in forced_include + stratified:
        if r['name'] not in {x['name'] for x in final_rows}:
            final_rows.append(r)

    # Print results
    print(f"\n=== promote_t1_to_t2 — T1 dir: {args.t1_dir} ===")
    t1_wall_h = _t1_total_wall_h(args.t1_dir)
    if t1_wall_h is not None:
        print(f"T1 total wall (sum across all variants): {t1_wall_h:.2f}h")
        print(f"Budget recommendation: --top-n 12 (default) if wall < 3h; "
              f"--top-n 8 if wall >= 3h.")

    if excluded_dq:
        print(f"\n--- EXCLUDED FOR DATA QUALITY ({len(excluded_dq)} variants) ---")
        for name, reason in sorted(excluded_dq.items()):
            # Show "would-be rank if included" for operator override visibility
            tmp_agg = aggregates[name]
            would_be_score = compute_score(tmp_agg) if tmp_agg['n_triggered'] > 0 else float('-inf')
            print(f"  {name}: {reason}  (would-be score={would_be_score:.2f})")

    if excluded_die:
        print(f"\n--- EXCLUDED FOR DIE_CEILING ({len(excluded_die)} variants) ---")
        for name, reason in sorted(excluded_die.items()):
            print(f"  {name}: {reason}")

    print(f"\n--- RANKING (composite score, top {min(20, len(survivors))}) ---")
    print(f"{'rank':>4} {'variant':<28} {'score':>7} {'cap%':>6} {'cap_ci':>14} "
          f"{'die%':>6} {'die_ci':>14} {'n_t':>6} {'n':>6}")
    print("-" * 102)
    for i, r in enumerate(survivors[:20], 1):
        promoted = '✓' if r['name'] in selected_names else ' '
        print(f"{i:>4} {r['name']:<28} {r['score']:>7.2f} {r['cap_pct']:>6.2f} "
              f"[{r['cap_ci_lo_pct']:>5.2f},{r['cap_ci_hi_pct']:>5.2f}] "
              f"{r['die_pct']:>6.2f} [{r['die_ci_lo_pct']:>5.2f},"
              f"{r['die_ci_hi_pct']:>5.2f}] {r['n_triggered']:>6} {r['n_total']:>6} {promoted}")

    if skipped_angles:
        print()
        for line in skipped_angles:
            print(line)

    print(f"\n--- FINAL T2 CANDIDATE LIST ({len(final_rows)} variants) ---")
    for r in final_rows:
        print(f"  {r['name']}  (score={r['score']:.2f}, cap%={r['cap_pct']:.2f}, "
              f"die%={r['die_pct']:.2f})")

    # Write output (unless --dry-run)
    if args.dry_run:
        print("\n--dry-run: NOT writing output file")
        return
    if args.out is None:
        print("\nERROR: --out required (or use --dry-run)", file=sys.stderr)
        sys.exit(2)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('w') as f:
        f.write("# pm32 T2 candidate variants — generated by promote_t1_to_t2.py\n")
        for r in final_rows:
            f.write(r['name'] + '\n')
    print(f"\nWrote {len(final_rows)} variants to {args.out}")


if __name__ == '__main__':
    main()

"""pm32 composite score + statistical helpers — single source of truth.

Used by:
- v3a_sweep.summarize_sweep (refactored to call compute_score)
- promote_t1_to_t2.py
- analyze_pm32.py
- hth_sweep.py post-aggregation

z = 1.96 for Wilson 95% CI to MATCH analyze_hth.py:13 and hth_resumable.py:47
so cross-comparison with prior pm30 HTH analyses is bit-identical. Do not
change without auditing all callers.

Inputs to compute_score:
    agg dict with keys n_triggered, cap_post, died_post, sum_food
    (matches the aggregate shape produced by v3a_sweep.summarize_sweep
    and promote_t1_to_t2 after grouping CSV rows by variant.)
"""
from __future__ import annotations
import math


# Match analyze_hth.py:13 and hth_resumable.py:47 — do not change without
# audit.
Z_975 = 1.96


def compute_score(agg):
    """Composite ranking metric.

    Formula: cap% - 2*die% + 5*(sum_food / max(1, n_triggered))

    Higher is better. cap% (capsule eaten by A post-trigger) is the primary
    upside; die% is the primary downside (weighted 2x because a death in
    Phase 1 also costs flatten-time HTH WR via the rc82 fallback losing
    tempo); food_post is a small bonus for incidental food collection during
    the chase, normalized per triggered game.

    Returns a float; on missing/invalid keys returns 0.0 conservatively.
    """
    n_g = max(1, int(agg.get('n_triggered', 0) or 0))
    cap_pct = 100.0 * float(agg.get('cap_post', 0) or 0) / n_g
    die_pct = 100.0 * float(agg.get('died_post', 0) or 0) / n_g
    food_per_trig = float(agg.get('sum_food', 0) or 0) / n_g
    return cap_pct - 2.0 * die_pct + 5.0 * food_per_trig


def wilson_ci_95(k, n):
    """Wilson 95% CI for binomial proportion. Returns (lower, upper) in [0, 1].

    Pure Python — no scipy (project channel doesn't have it). z = 1.96
    matches analyze_hth.py:13 and hth_resumable.py:47.
    """
    if n is None or n <= 0:
        return (0.0, 0.0)
    p = float(k) / float(n)
    z = Z_975
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    halfwidth = (z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))) / denom
    return (max(0.0, center - halfwidth), min(1.0, center + halfwidth))


def pearson_with_ci(xs, ys):
    """Pearson r + 95% CI via Fisher z back-transform.

    Returns (r, ci_lower, ci_upper). At small N (< ~30) the CI is approximate
    and analyze_pm32.py prints a caveat citing this.

    Returns (NaN, NaN, NaN) when:
      - len(xs) < 4 (Fisher z requires N >= 4)
      - len mismatch
      - either series has zero variance
    """
    if not isinstance(xs, (list, tuple)):
        xs = list(xs)
    if not isinstance(ys, (list, tuple)):
        ys = list(ys)
    n = len(xs)
    if n < 4 or len(ys) != n:
        return (float('nan'), float('nan'), float('nan'))
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / n
    sx = math.sqrt(sum((xs[i] - mx) ** 2 for i in range(n)) / n)
    sy = math.sqrt(sum((ys[i] - my) ** 2 for i in range(n)) / n)
    if sx == 0 or sy == 0:
        return (float('nan'), float('nan'), float('nan'))
    r = cov / (sx * sy)
    # Fisher z back-transform; clamp r away from ±1 to keep log finite.
    r_clamped = max(min(r, 0.999999), -0.999999)
    z = 0.5 * math.log((1.0 + r_clamped) / (1.0 - r_clamped))
    se = 1.0 / math.sqrt(n - 3)
    z_lo, z_hi = z - Z_975 * se, z + Z_975 * se
    r_lo = (math.exp(2.0 * z_lo) - 1.0) / (math.exp(2.0 * z_lo) + 1.0)
    r_hi = (math.exp(2.0 * z_hi) - 1.0) / (math.exp(2.0 * z_hi) + 1.0)
    return (r, r_lo, r_hi)


def spearman_rho(xs, ys):
    """Spearman rank correlation. Returns rho only; standard CI for rank
    correlations isn't widely agreed on with N < 30, and analyze_pm32 only
    consumes the point estimate for the |r - rho| disagreement check (MJ-3).

    Tied ranks: broken by enumeration order (acceptable for continuous-valued
    composite scores; documented in module-level comment).
    """
    if not isinstance(xs, (list, tuple)):
        xs = list(xs)
    if not isinstance(ys, (list, tuple)):
        ys = list(ys)
    n = len(xs)
    if n < 4 or len(ys) != n:
        return float('nan')

    def _ranks(vs):
        # Average-rank tie-breaking would be ideal, but enumeration-order
        # ties are good enough for continuous composite scores where exact
        # equality is rare. Documented for caller awareness.
        sorted_pairs = sorted(enumerate(vs), key=lambda p: p[1])
        ranks = [0.0] * len(vs)
        for rank, (idx, _) in enumerate(sorted_pairs):
            ranks[idx] = float(rank)
        return ranks

    rx = _ranks(xs)
    ry = _ranks(ys)
    return pearson_with_ci(rx, ry)[0]

#!/usr/bin/env python3
"""Generate per-variant CSV fixture files mimicking pm31 S5 phase1 schema.

Run once to populate experiments/rc_tempo/fixtures/ with per-variant CSVs
keyed off VARIANTS (so promote_t1_to_t2 + analyze_pm32 fixture-mode tests
have realistic input).

Values are hand-curated to reproduce pm31 S5's known ranking:
    beta_path4 (cap=55.8%, die=1.7%) > beta_retro (cap=53%, die=2%) >
    beta_v2d (cap=52%, die=2.5%)

All other VARIANTS get noise-around-baseline (cap≈50%, die≈3%) so they're
not Pareto-dominant. Crash% = 0%.
"""
import csv
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from phase1_smoke import FIELDS as PHASE1_FIELDS  # noqa: E402
from v3a_sweep import VARIANTS  # noqa: E402

# Hand-curated per-variant cap/die/food rates (pm31 S5 known ranking).
# (cap_pct, die_pct, food_per_trig)
KNOWN = {
    'beta_v2d':   (52.0, 2.5, 0.00),
    'beta_path4': (55.8, 1.7, 0.10),
    'beta_retro': (53.0, 2.0, 0.05),
    'beta_slack3': (54.5, 2.1, 0.07),
}
# All others: drawn around (cap=49.5, die=3.0, food=0.04) with seeded jitter
DEFAULT = (49.5, 3.0, 0.04)


def make_csv_for_variant(name, n_total=800, trigger_rate=0.65, seed=None):
    """Build n_total rows for a single variant, ~trigger_rate triggered.
    Cap/die rates picked from KNOWN[name] or DEFAULT, applied to triggered rows.

    N is large (800) so Wilson CI half-width is ~3pp at 50% — enough to
    preserve the pm31 S5 known ranking under random sampling.
    Food values use a small Bernoulli with prob food_pp (not normalvariate)
    so that food_per_trig stays close to the configured rate.
    """
    rng = random.Random(seed if seed is not None else hash(name) & 0xFFFFFFFF)
    cap_pct, die_pct, food_pp = KNOWN.get(name, DEFAULT)
    rows = []
    for i in range(n_total):
        triggered = 1 if rng.random() < trigger_rate else 0
        if triggered:
            cap_eaten = 1 if rng.random() < (cap_pct / 100.0) else 0
            died = 1 if rng.random() < (die_pct / 100.0) else 0
            # Bernoulli food (matches integer-valued a_food_post_trigger)
            food_post = 1 if rng.random() < min(0.95, max(0.0, food_pp)) else 0
        else:
            cap_eaten = 0
            died = 0
            food_post = 0
        # Synthesize plausible values for non-metric columns
        opp = ['baseline', 'zoo_reflex_rc82', 'zoo_reflex_rc166',
                'zoo_reflex_rc32', 'monster_rule_expert'][i % 5]
        layout = ['defaultCapture', 'distantCapture',
                   'RANDOM1001', 'RANDOM1002'][(i // 5) % 4]
        color = 'red' if (i % 2 == 0) else 'blue'
        score = rng.randint(-3, 3) if not died else (-2 if color == 'red' else 2)
        wins = int((score > 0 and color == 'red') or (score < 0 and color == 'blue'))
        rows.append({
            'agent': name, 'opp': opp, 'layout': layout, 'color': color,
            'seed': 42 + i, 'game_idx': i,
            'outcome': ('capsule_eaten' if cap_eaten else
                         ('a_died' if died else
                          ('timeout' if triggered else 'no_trigger'))),
            'moves': rng.randint(80, 200),
            'a_food_eaten': rng.randint(0, 5),
            'a_died_count': died,
            'capsule_eaten_by_A': cap_eaten,
            'capsule_eaten_by_anyone': cap_eaten,
            'capsule_eaten_tick': rng.randint(50, 150) if cap_eaten else -1,
            'trigger_tick': rng.randint(20, 80) if triggered else -1,
            'triggered': triggered,
            'moves_post_trigger': rng.randint(20, 100) if triggered else -1,
            'a_food_post_trigger': food_post,
            'a_food_pre_trigger': rng.randint(0, 3),
            'a_died_post_trigger': died,
            'cap_eaten_post_trigger': cap_eaten,
            'score': score,
            'crashed': 0,
            'wall_sec': round(rng.uniform(0.8, 2.2), 2),
        })
    return rows


def main():
    out_dir = HERE
    n_files = 0
    for name in sorted(VARIANTS.keys()):
        rows = make_csv_for_variant(name)
        out_csv = out_dir / f"{name}.csv"
        with out_csv.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=PHASE1_FIELDS)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        n_files += 1
    print(f"[stub] wrote {n_files} per-variant CSV fixtures to {out_dir}")


if __name__ == '__main__':
    main()

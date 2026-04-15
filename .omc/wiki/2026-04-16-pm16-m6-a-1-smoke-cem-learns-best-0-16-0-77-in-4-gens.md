---
title: "2026-04-16 pm16 — M6-a.1 smoke: CEM learns (best 0.16→0.77 in 4 gens)"
tags: ["session-log", "m6-a-1", "cem-trajectory", "evolve.py", "h1test-seed", "elitism", "fitness-ascending"]
created: 2026-04-15T19:34:28.465Z
updated: 2026-04-15T19:34:28.465Z
sources: ["/tmp/m6a1_smoke.log", "experiments/artifacts/2a_gen{000,001,002,003}.json"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-16 pm16 — M6-a.1 smoke: CEM learns (best 0.16→0.77 in 4 gens)

# Session 2026-04-16 pm16 — M6-a.1 smoke: CEM trajectory confirmed

## Focus
Validate that pm15's seeding + elitism fix produces real CEM learning,
not just a non-zero gen-0 snapshot. 4 gens × 20 pop × 12 games/opp × 3
dry-pool opps × defaultCapture, `--init-mean-from h1test`.

## Command
```
evolve.py --phase 2a --n-gens-2a 4 --pop 20 --games-per-opponent-2a 12 \
          --opponents baseline zoo_reflex_h1test zoo_reflex_h1b \
          --layouts defaultCapture \
          --master-seed 900 --init-mean-from h1test
```

## Wall-time profile

| gen | best | mean | elite_mean | snr | stagnation | wall |
|---|---|---|---|---|---|---|
| 0 | 0.160 | 0.009 | 0.025 | 0.47 | 1 | 254.4s |
| 1 | 0.273 | 0.045 | 0.129 | 1.10 | 0 | 262.4s |
| 2 | 0.323 | 0.086 | 0.187 | 1.15 | 0 | 266.1s |
| 3 | **0.774** | 0.171 | 0.380 | 1.10 | 0 | 259.0s |

**Total 17m22s.** best_fitness ascended **4.8×** (0.160 → 0.774). mean_fitness
ascended **19×**. snr cleared STRATEGY §6.3's 1.0 drift-alert threshold
from gen 1 onward. Per-gen wall stable at ~260s (well under the
~360s we'd see at this scale at pm13-era 10.5s/match; pm14 Option A
holds).

## Fitness decoding

`compute_fitness` in Phase 2a (monster_bonus_active=0):

    fitness = pool_win_rate − 0.5·crash_rate − 0.5·stddev_win_rate

With `crash_rate=0` and modest `stddev_win_rate`, fitness 0.774 implies
`pool_win_rate ≈ 0.82` on the 3-opp dry pool — roughly **82% win rate
against baseline / h1test / h1b averaged at 12 games each**. At this
sample size (3 × 12 = 36 games / genome) the 95% CI is ~±0.13
pp, so call it "anywhere between 70 % and 95 %" — still a huge jump
from the seeded genome's own ~0.13 fitness.

## Mean-genome drift from seed

First 5 features, across gens:

| gen | f_bias | f_successorScore | f_distToFood | f_distToCapsule | f_numCarrying |
|---|---|---|---|---|---|
| seed (h1test) | 0 | 100 | 10 | 8 | 5 |
| 0 | -2.1 | 115.1 | 4.9 | 18.2 | 12.2 |
| 1 | 0.6 | 110.6 | 9.2 | 13.0 | 11.6 |
| 2 | -1.1 | 112.6 | 3.2 | 10.6 | 10.5 |
| 3 | **-6.9** | **112.9** | **-0.9** | **8.5** | **-0.6** |

σ decay on those same features: 14.7 → 12.1 → 10.1 → **6.9** (tracking
STRATEGY's 0.9×/gen schedule — actually ~0.83× observed because elite
variance itself shrank).

Interesting: `f_successorScore` settled at ~113 (higher than h1test's
100 — CEM wants MORE food-eating pressure). `f_distToFood` drifted to
≈ 0 (the carrot isn't needed when the stick `f_successorScore` is
strong enough). `f_numCarrying` went from +5 toward 0 (less incentive
to carry stockpile, likely because return-home heuristics dominate).

## Interpretation

The pm15 "fix" works not as a cosmetic seed but as a genuine exploration
enabler:

1. `--init-mean-from h1test` puts the Gaussian centroid in the RIGHT
   neighborhood (+100 magnitude weights the domain needs).
2. `population[0] = mean` (elitism) ensures at least one genome with
   *exactly* h1test weights survives every gen. That genome has
   fitness ≈ 0.13 on this pool, a strict lower bound for best_ever.
3. Gaussian(mean, σ=30) then explores outward; σ decays per gen so
   the search contracts around the elite mean rather than diffusing.
4. CEM picks up the strongest genomes each gen, mean migrates
   toward them — the observed trajectory 0.16 → 0.27 → 0.32 → 0.77.

The sharp jump from 0.32 to 0.77 at gen 3 is a **single strong genome
found** (best > elite_mean × 2). With pop=20 this is plausible noise;
we should NOT read it as "phase 2a will converge at 0.77 everywhere".
What we DO read: the pipeline is bootstrapping real signal, not just
preserving the seed.

## Decisions

1. **pm15 fix validated** — post-fix CEM produces the learning curve
   STRATEGY §6.3 assumed. M6-a row in STATUS updated: v1 ❌ Failed,
   M6-a.1 smoke ✅ PASSED, M6-a.2 (full) ⏳ Unblocked.
2. **Gate for moving to M6-a.2 full: PASSED.**
   - ✅ best_fitness monotonically increasing.
   - ✅ snr ≥ 1.0 for 3 consecutive gens (gens 1-3).
   - ✅ best_ever > h1test seed fitness.
3. **M6-a.2 scope options** for next session:
   - (fast) 2 gens × 40 pop × 264 games × 11-opp pool × 2 layouts,
     ~2h20m wall. Matches pm14 M6-a v1 spec — useful as an
     apples-to-apples before/after comparison.
   - (extended) 5 gens × 40 pop × full spec, ~5-6h wall. Delivers
     the first half of STRATEGY §6.3 Phase 2a (10 gens total).
     Better for champion extraction.
   - User decision pending; "성능 우선" directive from pm-mid
     suggests (extended).

## Next-session priority

Launch M6-a.2 per user decision. Resume from `2a_gen003.json` is an
option too (continue this smoke past 4 gens) but the opponent pool
and layout-RANDOM coverage are intentionally narrow here; best to
start fresh at full spec.

## Artifacts
- `/tmp/m6a1_smoke.log`
- `experiments/artifacts/2a_gen00{0,1,2,3}.json` (gitignored but
  retained in working tree for the M6-a.2 resume option)


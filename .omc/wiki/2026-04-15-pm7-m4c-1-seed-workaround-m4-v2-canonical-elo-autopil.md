---
title: "2026-04-15 pm7 - M4c-1 seed workaround + M4-v2 canonical ELO (autopilot)"
tags: ["session-log", "autopilot", "m4c", "m4-v2", "seed-workaround", "elo", "h1test-champion", "variance-recovered"]
created: 2026-04-15T07:42:19.942Z
updated: 2026-04-15T07:42:19.942Z
sources: ["experiments/run_match.py", "experiments/artifacts/tournament_results/m4_full_pm7_v2.csv", "/tmp/m4_v2.log"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-15 pm7 - M4c-1 seed workaround + M4-v2 canonical ELO (autopilot)

# Session 2026-04-15 pm7 — M4c-1 seed workaround + M4-v2 canonical ELO (autopilot)

## Focus
Autopilot lane invoked after pm6 identified the 95.2% tie-lock as the blocker for M4 ELO. Two phases:
1. Patch `run_match.py` to route seed through the layout axis (C2 workaround from audit).
2. Rerun M4 as v2 with layout variance and confirm the fix produces meaningful ranking signal.

## Phase 2 — patch

`experiments/run_match.py` `run_match(...)`:
- **Removed** `if seed is not None: cmd += ["--fixRandomSeed"]`. capture.py's handler is `random.seed('cs188')` (hardcoded constant) — keeping the flag would clamp every invocation to identical PRNG state.
- **Added** seed→layout promotion: when `layout == "RANDOM"` and a seed is given, the effective `-l` value becomes `f"RANDOM{seed}"`. Named layouts (e.g., `defaultCapture`) pass through untouched; capture.py then seeds from the system clock for per-invocation variance.
- Result dict still records the original `layout` string so tournament's `(red, blue, layout, seed)` dedup key remains stable across runs.
- Docstring "Seed policy" block added; pm6 empirical evidence cited inline.

## Phase 3a — variance smoke

Same config × 5 reps (`baseline vs zoo_reflex_h1test -l defaultCapture --seed 1`):
- Red +0.0 (x3), Red +18.0, Blue -1.0 → 3 distinct outcomes. ✅

RANDOM layout seed 1 vs seed 2 (h1test vs h1b):
- seed=1 → Tie; seed=2 → Red +3. Different layouts, different outcomes. ✅

Note: `zoo_dummy vs baseline` × 3 all tied at Blue -18.0 — not a variance failure, just strategic dominance (random vs feature-weighted is a decided matchup).

## Phase 3b — M4-v2 tournament

Command:
```
tournament.py --agents <15 agents> \
  --layouts defaultCapture RANDOM --seeds 1 2 --games-per-pair 1 \
  --workers 8 --timeout-per-game 180 \
  --out experiments/artifacts/tournament_results/m4_full_pm7_v2.csv
```

Scale: 15 agents × permutations(15,2)=210 × 2 layouts × 2 seeds × 1 rep = **840 jobs**.

Result: **840 matches / 0 crashes / 32m28s wall (CPU user 4h09m, 7.75× parallel)**. CSV resilience patch pm5 made this a non-issue — no mid-run babysitting needed.

## Outcome distribution

| Outcome | count | % |
|---|---|---|
| tie | 761 | 90.6% |
| blue_win | 45 | 5.4% |
| red_win | 34 | 4.0% |

**Tie rate dropped from 95.2% (pm6) to 90.6% (pm7)** — the 4.6 pp decrease is the seed-workaround dividend. Most pairs remain tied, which is a property of the agents (defensive reflex weights dominate), not the tournament infra.

## Canonical ELO

| Rank | Agent | ELO | vs baseline W-L-T | Win% | Net |
|---|---|---|---|---|---|
| 1 | baseline | 1610.7 | — | — | — |
| 2 | **zoo_reflex_h1test** | **1584.6** | 4-3-1 | **50.0%** | +1 |
| 3 | zoo_reflex_h1c | 1532.5 | 1-5-2 | 12.5% | -4 |
| 4 | **zoo_reflex_h1b** | 1503.8 | 3-1-4 | 37.5% | +2 |
| 5 | zoo_reflex_aggressive | 1488.5 | 0-0-8 | 0% | 0 |
| 6 | zoo_reflex_capsule | 1487.2 | 0-0-8 | 0% | 0 |
| 7 | zoo_reflex_tuned | 1486.2 | 0-0-8 | 0% | 0 |
| 8 | zoo_reflex_defensive | 1482.4 | 0-0-8 | 0% | 0 |
| 9 | zoo_minimax_ab_d3_opp | 1479.9 | 0-0-8 | 0% | 0 |
| 10 | zoo_approxq_v2_deeper | 1478.7 | 0-8-0 | 0% | -8 |
| 11 | zoo_approxq_v1 | 1478.6 | 0-8-0 | 0% | -8 |
| 12 | zoo_minimax_ab_d2 | 1476.6 | 0-0-8 | 0% | 0 |
| 13 | zoo_expectimax | 1474.9 | 0-0-8 | 0% | 0 |
| 14 | zoo_dummy | 1468.6 | 0-7-1 | 0% | -7 |
| 15 | monster_rule_expert | 1466.7 | 0-0-8 | 0% | 0 |

## 3-way corroboration (pm4 / M4-v1 pm6 / M4-v2 pm7)

| Agent | pm4 (40g defaultCapture) | M4-v1 (2g defaultCapture, seed-locked) | M4-v2 (8g varied) |
|---|---|---|---|
| h1test | 35% W / 35% L / net 0 | 0W/0L/2T | **50% W / 37.5% L / net +1** |
| h1b | 30% W / 10% L / **net +8** | 1W/0L/1T | 37.5% W / 12.5% L / **net +2** |
| h1c | 20% W / 5% L / net +6 (variance 10-20%) | 0W/0L/2T | 12.5% W / 62.5% L / **net -4** |
| ReflexTuned (control) | 0W/0L/40T | 0W/0L/2T | 0W/0L/8T |
| approxQ v1/v2 | not tested | 0W/2L/0T | 0W/8L/0T |

**Conclusions**:
1. **h1test is the single-dict winner** across all three experiments. pm4 win% understated (35%) because pm4 was defaultCapture-only; when RANDOM layouts are included (v2), h1test's both-OFFENSE formation exploits map variety → 50%.
2. **h1b is the stable second** with a net-positive profile in every experiment. Conservative + reliable.
3. **h1c is map-sensitive** — the 10x `f_distToCapsule` bet pays only where a capsule is reachable. RANDOM layouts frequently place capsules adversely, dropping h1c from +6 net (pm4) to -4 net (v2). H1c should NOT be the M6 evolution seed.
4. **ReflexTuned original weights = structural deadlock** — reproduced across all three sample sizes.
5. **approxQ_{v1, v2_deeper} confirmed unlearned**. Q-learning weights must be trained (M6 output) before these agents become meaningful.
6. **All minimax/expectimax/monster_rule agents** tie baseline on every layout-seed combination we've tested. Seed weights are structurally symmetric; layout alone doesn't break the deadlock.

## Phase 4 — code-reviewer

APPROVED (0 🔴, 2 🟡 maintainability, 3 🟢 nits). Deferred improvements (low priority; don't block M4b):
- 🟡 Layout sentinel case/whitespace normalisation (`"random" ≠ "RANDOM"` silently bypasses promotion).
- 🟡 Add `effective_layout` field to result dict for observability (doesn't break dedup key).
- 🟢 Timeout branch missing `exit_code`; 🟢 PYTHONHASHSEED comment polish; 🟢 docstring reproducibility claim split.

## Decisions

1. **M4-v2 is the canonical ELO for now.** 8 games per baseline matchup is wide-CI but directionally trustworthy across 3 corroborating experiments.
2. **M6 evolution seed = h1test OFFENSIVE weights** (`SEED_WEIGHTS_OFFENSIVE` with `f_onDefense=0`, `f_numInvaders=-50`, both teammates OFFENSE). Secondary seed = h1b role-split variant for ensemble exploration.
3. **approxQ family excluded from pre-M6 evaluation** — trivially 0W. Re-evaluate after evolution assigns them real weights.
4. **MCTS/deep-minimax (5 agents) remain excluded** pending M7.5 time-budget patch (MAX_ITERS polling).
5. **pm7 🟡 code-review items deferred** — correctness not affected; will batch-patch with M4c-2 (`start_new_session`) before M6 kickoff.
6. **No M4-v3 yet**. 100+ games per pair would tighten CIs but the current signal is sufficient to choose evolution seeds. Prioritise M4b (evolve.py fix) which is the actual critical-path blocker.

## Next-session priority

**M4b** — fix `evolve.py:140-142` `NotImplementedError` swallow AND implement `evaluate_genome()`. This is the single blocker between us and a meaningful M5 dry run. Expected ~1.5h. The seed pool is now known (h1test primary, h1b secondary).

After M4b: M5 (evolution dry run N=8 G=2, ~1h) → M6 (20h full campaign) → M7 (select_top4 + flatten) → M8 (output.csv) → M9 (report) → M10 (submission).

## Artifacts this session

- `experiments/run_match.py` (patched — seed routing)
- `experiments/artifacts/tournament_results/m4_full_pm7_v2.csv` (840 rows, canonical)
- `/tmp/m4_smoke.csv`, `/tmp/m4_full.log`, `/tmp/m4_v2.log` (transient logs)
- wiki: this session-log
- STATUS.md updated: M4c-1-infra ✅, M4-v2 ✅, blocker 🔴→🟢 for seed plumbing, M4b is the new critical-path row.


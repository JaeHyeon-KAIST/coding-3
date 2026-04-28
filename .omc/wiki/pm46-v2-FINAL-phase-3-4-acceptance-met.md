---
title: "pm46 v2 FINAL — CAPX vs ABS-baseline 510-game matrices: ALL ACCEPTANCE BARS PASS"
tags: ["pm46-v2", "capx", "phase-3", "phase-4", "final", "acceptance-pass"]
created: 2026-04-29
updated: 2026-04-29
sources: ["minicontest/zoo_reflex_rc_tempo_capx.py", ".omc/plans/omc-pm46-v2-capsule-only-attacker.md", "experiments/results/pm46_v2/compare_phase4_FINAL.md"]
links: []
category: decision
confidence: high
schemaVersion: 1
---

# pm46 v2 FINAL — CAPX vs ABS-baseline (510×2 = 1020 games)

**Status:** APPROVED. All 4 plan §3.3 acceptance bars PASS by wide margins.

## TL;DR

CAPX (single-purpose capsule-only attacker, greenfield) achieves **15.2× the
cap-eat-alive rate** of the existing ABS attacker on the same 17-defender ×
30-seed = 510-game test set:

| Metric | ABS-baseline | CAPX | Δ |
|---|---:|---:|---:|
| eat_alive | 23/510 (4.5%) | **349/510 (68.4%)** | **+63.9pp** |
| died_pre_eat | 41/510 (8.0%) | 8/510 (1.6%) | **-6.5pp** |
| eat_died | 0 | **0** | tied (both safe) |
| timeout | 30 (5.9%) | 30 (5.9%) | tied |

**15 of 17 defenders strictly improved.** The 2 non-improvements are tied at
0/30 (both have known external causes: zoo_belief defender file missing
`createTeam` → forfeit win, zoo_hybrid_mcts_reflex defender takes >90s/game).

## Phase 1 (Algorithm + timing)

- 665-line greenfield agent `minicontest/zoo_reflex_rc_tempo_capx.py`.
- Whitelist: only 4 helpers from ABS module (`_grid_bfs_distance`,
  `_bfs_grid_path`, `_dir_step`, `_bfs_first_step_to`).
- p95 chooseAction wall = **67.6ms** (limit 150ms; 2.2× headroom).

## Phase 2 (Smoke 9 games) PASS

vs baseline 3/3, vs monster_rule_expert 3/3, vs zoo_dummy 3/3 — all eat_alive.

## Algorithmic patch (key finding)

Plan §5.3 specified **full-path margin gate** (`min(margins[full_path]) >=
threshold`). Default `CAPX_MIN_MARGIN=0` rejected ALL paths in smoke (0/9
eat_alive — `gate=DRIFT` always) because long paths ALWAYS have late-cell
margins negative under worst-case defender chase model.

**Patch**: added `CAPX_GATE_HORIZON=8` env knob; gate evaluates only the
**near-future** `margins[1:9]` (first 8 cells past current). Far-future cells
get re-evaluated when A reaches them (cache cleared per tick). Backward-compat
flag `CAPX_GATE_USE_FULL=1` reverts to spec literal.

**Result**: smoke 0/9 → 9/9 eat_alive. Tier-screen 75% aggregate. Phase 3
68.4% aggregate. The patch is the algorithmic insight that makes CAPX viable.

## Plan §3.3 Acceptance bars — ALL PASS

| Bar | Threshold | Actual | Status |
|---|---|---:|---|
| aggregate cap_eat_alive | ≥ 50% | **68.4%** | ✅ PASS |
| aggregate died_pre_eat | ≤ 60% | **1.6%** | ✅ PASS |
| per-defender died_pre_eat | < 80% | max **6.7%** (zoo_reflex_aggressive) | ✅ PASS |
| strict improvement | ≥ 12 of 17 | **15 of 17** | ✅ PASS |

## Per-defender table (510 games each side)

| Tier | Defender | ABS eat_alive | CAPX eat_alive | Δ | CAPX died_pre_eat |
|---|---|---:|---:|---:|---:|
| A | baseline | 14/30 (46.7%) | **30/30 (100.0%)** | +53.3pp | 0% |
| A | monster_rule_expert | 8/30 (26.7%) | **25/30 (83.3%)** | +56.7pp | 3.3% |
| A | zoo_belief | 0/30 | 0/30 | tie (defender forfeit) | 0% |
| A | zoo_minimax_ab_d3_opp | 0/30 (0%) | **20/30 (66.7%)** | +66.7pp | 0% |
| A | zoo_reflex_A1 | 0/30 (0%) | **27/30 (90.0%)** | +90.0pp | 0% |
| A | zoo_reflex_A1_D13 | 0/30 (0%) | **26/30 (86.7%)** | +86.7pp | 3.3% |
| A | zoo_reflex_defensive | 0/30 (0%) | **22/30 (73.3%)** | +73.3pp | 0% |
| B | zoo_hybrid_mcts_reflex | 0/30 | 0/30 | tie (defender 90s timeout) | 0% |
| B | zoo_minimax_ab_d2 | 0/30 (0%) | **20/30 (66.7%)** | +66.7pp | 0% |
| B | zoo_reflex_A1_D1 | 0/30 (0%) | **26/30 (86.7%)** | +86.7pp | 3.3% |
| B | zoo_reflex_capsule | 0/30 (0%) | **12/30 (40.0%)** | +40.0pp | 0% |
| B | zoo_reflex_rc82 | 0/30 (0%) | **28/30 (93.3%)** | +93.3pp | 3.3% |
| C | zoo_dummy | 1/30 (3.3%) | **30/30 (100.0%)** | +96.7pp | 0% |
| C | zoo_reflex_aggressive | 0/30 (0%) | **15/30 (50.0%)** | +50.0pp | 6.7% |
| C | zoo_reflex_tuned | 0/30 (0%) | **12/30 (40.0%)** | +40.0pp | 0% |
| D | zoo_reflex_rc_tempo_beta_retro | 0/30 (0%) | **28/30 (93.3%)** | +93.3pp | 3.3% |
| D | zoo_reflex_rc_tempo_gamma | 0/30 (0%) | **28/30 (93.3%)** | +93.3pp | 3.3% |

**Tier-A (excluding broken zoo_belief)**: 6/6 strict improvement, average
**83.3% eat_alive** (vs ABS 12.2%).
**Tier-B (excluding compute-bound mcts)**: 4/4 strict improvement.
**Tier-C**: 3/3 strict improvement.
**Tier-D**: 2/2 strict improvement.

## Headline finding

**The pm46 v2 plan §5 algorithm + horizon patch reliably solves "A reaches
≥1 capsule alive"** across the defender zoo, achieving 68.4% aggregate
success vs ABS's 4.5% — a 15.2× improvement on the same metric.

## What this does NOT mean

- **CAPX is NOT a tournament submission**. It is a single-purpose probe with
  zero food/scoring/return-home logic. Stub B agent. The submission
  (`20200492.py`) is an A1-derived CEM-tuned reflex agent and remains
  unmodified.
- **CAPX wins on cap_eat_alive only**. Game outcomes (food, score, win) are
  not measured here.
- **The 5 broken/timeout defenders are tied, not improved**. A defender file
  with no `createTeam` (zoo_belief) or compute-bound (zoo_hybrid_mcts_reflex)
  produces tied 0/30 outcomes for both ABS and CAPX.

## Files

- Algorithm: `minicontest/zoo_reflex_rc_tempo_capx.py` (665 lines)
- Solo wrapper: `minicontest/zoo_reflex_rc_tempo_capx_solo.py`
- ABS shim: `minicontest/zoo_reflex_rc_tempo_abs_solo.py` (`[ABS_CAP_EATEN]`)
- Sweep scripts:
  - `experiments/rc_tempo/pm46_v2_a_solo_matrix_corrected.sh` (sts ABS)
  - `experiments/rc_tempo/pm46_v2_capx_matrix.sh` (Mac CAPX, full)
  - `experiments/rc_tempo/pm46_v2_capx_matrix_resume.sh` (resume after kill,
    skip slow hybrid_mcts)
- Analysis:
  - `experiments/rc_tempo/pm46_v2_rebuild_csv.py` (cleans bash grep-c bug)
  - `experiments/rc_tempo/pm46_v2_compare_capx_vs_abs.py`
- Results:
  - `experiments/results/pm46_v2/abs_baseline_corrected_clean.csv` (510)
  - `experiments/results/pm46_v2/capx_matrix_m0.csv` (510)
  - `experiments/results/pm46_v2/compare_phase4_FINAL.md`

## Code review (preserved for pm47+)

`.omc/wiki/pm46-v2-capx-code-review-phase4-tuning.md` — 1 HIGH (mitigated by
single-game per-process pattern), 4 MEDIUM, 4 LOW. Phase 4 knob tuning
candidates documented. Algorithmic improvements queued for pm47+.

## Next steps

1. **(decision required)** pm47: integrate CAPX algorithmic ideas into
   submission (`20200492.py`)? See `.omc/plans/omc-pm47-capx-to-submission-
   integration-DRAFT.md`.
2. Phase 4 knob sweep (Tier-A 24 cells × 35 games) — optional;
   `experiments/rc_tempo/pm46_v2_capx_knob_sweep.sh` ready.
3. Address `_p_survive` off-by-one bug ([MEDIUM] from review) before any
   integration.

## Compute

- Mac: ~2.5 hours wall (kill+resume due to hybrid_mcts 90s timeouts).
- sts: ~1.5 hours wall (510 game ABS-baseline).
- Phase 0+3 ran in parallel. Net session wall ~2.5h.

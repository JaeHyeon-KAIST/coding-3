# pm46 v2 Phase 4 — CAPX vs ABS-baseline

- ABS:  experiments/results/pm46_v2/abs_baseline_corrected_merged.csv
- CAPX: experiments/results/pm46_v2/capx_matrix_m0_merged.csv

## Aggregate

| Metric | ABS | CAPX | Δ |
|---|---:|---:|---:|
| eat_alive | 45 (8.8%) | 403 (79.0%) | +70.2pp |
| eat_died | 0 (0.0%) | 0 (0.0%) | +0.0pp |
| no_eat_alive | 398 (78.0%) | 98 (19.2%) | -58.8pp |
| no_eat_died | 67 (13.1%) | 9 (1.8%) | -11.4pp |
| timeout | 0 (0.0%) | 0 (0.0%) | +0.0pp |
| total | 510 | 510 | |

## Plan §3.3 acceptance bars

- aggregate cap_eat_alive ≥ 50%: **79.0%** PASS
- aggregate died_pre_eat ≤ 60%: **1.8%** PASS
- per-defender died_pre_eat ≥ 80%: **PASS** (none)

## Per-defender breakdown

| Tier | Defender | ABS eat_alive | CAPX eat_alive | Δ | CAPX died_pre_eat |
|---|---|---:|---:|---:|---:|
| A | baseline | 14/30 (46.7%) | 30/30 (100.0%) | +53.3pp | 0/30 (0.0%) |
| A | monster_rule_expert | 8/30 (26.7%) | 25/30 (83.3%) | +56.7pp | 1/30 (3.3%) |
| A | zoo_minimax_ab_d3_opp | 0/30 (0.0%) | 20/30 (66.7%) | +66.7pp | 0/30 (0.0%) |
| A | zoo_reflex_A1 | 0/30 (0.0%) | 27/30 (90.0%) | +90.0pp | 0/30 (0.0%) |
| A | zoo_reflex_A1_D13 | 0/30 (0.0%) | 26/30 (86.7%) | +86.7pp | 1/30 (3.3%) |
| A | zoo_reflex_A1_T5 | 12/30 (40.0%) | 27/30 (90.0%) | +50.0pp | 0/30 (0.0%) |
| A | zoo_reflex_defensive | 0/30 (0.0%) | 22/30 (73.3%) | +73.3pp | 0/30 (0.0%) |
| B | zoo_hybrid_mcts_reflex | 10/30 (33.3%) | 27/30 (90.0%) | +56.7pp | 1/30 (3.3%) |
| B | zoo_minimax_ab_d2 | 0/30 (0.0%) | 20/30 (66.7%) | +66.7pp | 0/30 (0.0%) |
| B | zoo_reflex_A1_D1 | 0/30 (0.0%) | 26/30 (86.7%) | +86.7pp | 1/30 (3.3%) |
| B | zoo_reflex_capsule | 0/30 (0.0%) | 12/30 (40.0%) | +40.0pp | 0/30 (0.0%) |
| B | zoo_reflex_rc82 | 0/30 (0.0%) | 28/30 (93.3%) | +93.3pp | 1/30 (3.3%) |
| C | zoo_dummy | 1/30 (3.3%) | 30/30 (100.0%) | +96.7pp | 0/30 (0.0%) |
| C | zoo_reflex_aggressive | 0/30 (0.0%) | 15/30 (50.0%) | +50.0pp | 2/30 (6.7%) |
| C | zoo_reflex_tuned | 0/30 (0.0%) | 12/30 (40.0%) | +40.0pp | 0/30 (0.0%) |
| D | zoo_reflex_rc_tempo_beta_retro | 0/30 (0.0%) | 28/30 (93.3%) | +93.3pp | 1/30 (3.3%) |
| D | zoo_reflex_rc_tempo_gamma | 0/30 (0.0%) | 28/30 (93.3%) | +93.3pp | 1/30 (3.3%) |

Improved: 17 defenders. Regressed: 0. Strict-improvement gate (≥12 of 17): PASS

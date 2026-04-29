---
title: "pm47 Phase 0.5 — Submission cap-eat-alive vs CAPX (17×10 vs 17×30)"
tags: ["pm47", "submission", "cap-eat", "capx-comparison", "phase-0", "self-similarity"]
created: 2026-04-29
sources:
  - "experiments/results/pm47_phase0/submission_capx_metric_n10.csv"
  - "experiments/results/pm46_v2/capx_matrix_m0_merged.csv"
  - ".omc/specs/deep-interview-pm47-submission-cap-eat-measurement.md"
  - ".omc/research/pm47-decision/synthesis.md"
links:
  - "pm46-v2-FINAL-recovery-17-of-17"
  - "pm46-v2-failure-mode-deep-analysis"
  - "pm46-v2-ccg-improvement-consultation"
category: decision
confidence: high
schemaVersion: 1
---

# pm47 Phase 0.5 — Submission cap-eat-alive vs CAPX

## TL;DR

**`20200492.py` 의 cap-eat-alive 능력은 17 defender 전체에서 CAPX 보다 약함**
(-37pp aggregate, -20pp ~ -53pp per defender). 동시에 submission 은 cap 안
먹어도 51.8% win-rate (Phase 0). 이는 두 가지 의미:

1. **CAPX 의 cap-eat 알고리즘을 submission 에 transfer 가능하면**
   submission 의 cap-eat 능력 대폭 강화 → scared 40-tick window 활용 →
   food return 가능성 증가 → win-rate 추가 향상 가능 (정확한 lift 모름)
2. **단순 transplant 위험**: submission 은 multi-purpose (food/return/
   scoring), CAPX 는 single-purpose. CAPX 의 cap-aggressive 전략을 직접
   transfer 하면 submission 의 food/return loop 가 깨질 수 있음.

## 1. Methodology

- **Wrapper**: `minicontest/submission_capsule_logger.py` — `20200492.py` 의
  `ReflexTunedAgent` 를 importlib 로 load + subclass. registerInitialState
  / chooseAction 모두 super() forward → **submission 행동 100% 동일**
  (verified: bare `20200492.py` 와 같은 score 출력 RANDOM1 baseline +10).
  Cap detection 만 inline 추가 (CAPX 의 `_emit_cap_eaten_if_decremented`
  와 같은 logic), `[SUBM_CAP_EATEN]` / `[SUBM_A_DIED]` 마커 emit.
- **Matrix**: 17 defender (pm46 v2 inventory) × 10 seed = 170 game on sts.
  Wall: 533s ≈ 9분. PYTHONHASHSEED=0 → 결정성 재현.
- **Outcome 분류** (CAPX 와 동일):
  - `eat_alive`: cap 먹음 + 먹는 시점 ±3 tick 안에 죽지 않음
  - `eat_died`: cap 먹음 + 먹은 직후 죽음
  - `died_pre_eat`: cap 못 먹고 죽음
  - `no_eat_alive`: cap 못 먹고 안 죽음 (timeout, oscillation)

## 2. Aggregate (170 game, n=10)

| 지표 | submission | CAPX (n=30, 510 game) | Δ |
|---|---:|---:|---:|
| **eat_alive** | **42.4%** (72/170) | **79.0%** | **-37pp** |
| died_pre_eat | 41.8% (71/170) | 1.8% | **+40pp (24× worse)** |
| no_eat_alive | 15.9% (27/170) | ~17% | similar |
| eat_died | 0% | 0% | tied |

## 3. Per-defender breakdown (모든 17 defender)

| Defender | submission n=10 | CAPX n=30 | Δ pp | submission died_pre_eat |
|---|---:|---:|---:|---:|
| baseline | 5/10 (50%) | 30/30 (**100%**) | **-50** | 5/10 |
| monster_rule_expert | 3/10 (30%) | 25/30 (83%) | **-53** | 6/10 |
| zoo_minimax_ab_d3_opp | 4/10 (40%) | 20/30 (66%) | -26 | 3/10 |
| zoo_reflex_defensive | 4/10 (40%) | 22/30 (73%) | -33 | 2/10 |
| zoo_reflex_A1 | 5/10 (50%) | 27/30 (90%) | -40 | 4/10 |
| zoo_reflex_A1_D13 | 5/10 (50%) | 26/30 (86%) | -36 | 4/10 |
| zoo_reflex_A1_T5 | 5/10 (50%) | 27/30 (90%) | -40 | 4/10 |
| zoo_hybrid_mcts_reflex | 5/10 (50%) | 27/30 (90%) | -40 | 3/10 |
| zoo_minimax_ab_d2 | 4/10 (40%) | 20/30 (66%) | -26 | 3/10 |
| zoo_reflex_A1_D1 | 5/10 (50%) | 26/30 (86%) | -36 | 4/10 |
| zoo_reflex_capsule | 2/10 (20%) | 12/30 (40%) | **-20** | 6/10 |
| zoo_reflex_rc82 | 5/10 (50%) | 28/30 (93%) | -43 | 5/10 |
| zoo_dummy | 6/10 (60%) | 30/30 (100%) | -40 | 0/10 |
| zoo_reflex_aggressive | 2/10 (20%) | 15/30 (50%) | **-30** | 6/10 |
| zoo_reflex_tuned | 2/10 (20%) | 12/30 (40%) | **-20** | 6/10 |
| zoo_reflex_rc_tempo_beta_retro | 5/10 (50%) | 28/30 (93%) | -43 | 5/10 |
| zoo_reflex_rc_tempo_gamma | 5/10 (50%) | 28/30 (93%) | -43 | 5/10 |

**요약**: Submission 이 **17/17 defender 에서 모두 CAPX 보다 cap-eat 약함**.
어떤 defender 에서도 submission 가 CAPX 를 capsule 도달 능력으로 이기지 못함.

## 4. Cross-reference: cap-eat metric vs win-rate metric (Phase 0)

Phase 0 의 **win-rate** 와 Phase 0.5 의 **cap-eat-alive** 비교:

| Defender | Win % (Phase 0, n=10) | Cap-eat-alive % | Pattern |
|---|---:|---:|---|
| zoo_reflex_tuned | **80% W** | 20% eat_alive | **cap 안 먹어도 압승** |
| zoo_reflex_capsule | 70% W | 20% eat_alive | cap 안 먹어도 식량으로 이김 |
| zoo_reflex_aggressive | 60% W | 20% eat_alive | cap 못 먹어도 W |
| zoo_dummy | 80% W | 60% eat_alive | 둘 다 강 (consistent) |
| baseline | 40% W | 50% eat_alive | cap 먹어도 못 이김 (food 약?) |
| **zoo_reflex_A1_D13** | **20% W** | 50% eat_alive | **cap 잘 먹어도 식량 못 이김** |
| zoo_reflex_A1_D1 | 20% W | 50% eat_alive | 같은 패턴 |
| zoo_reflex_A1, A1_T5 | 30% W | 50% eat_alive | 같은 패턴 |

**핵심 패턴 발견**:
- **"Cap 안 먹어도 이김" 군** (capsule, tuned, aggressive): win 70-80%, cap 20%.
  → submission 의 food return 능력만으로 충분.
- **"Cap 먹어도 못 이김" 군** (A1 family): win 20-30%, cap 50%.
  → cap 먹어도 다른 factor (food competition tie? B coordination?) 로 짐.
  Self-similarity paradox 의 진짜 메커니즘 = **food competition stalemate**, not cap-eat lack.
- **baseline 의외**: win 40% but cap 50%. cap 잘 먹는데 식량 경쟁에서 짐.

## 5. Implications for Path 2 (CAPX integration)

### 긍정적 (Path 2 ROI 클 가능성)
- 모든 defender 에서 CAPX 가 cap-eat 우월 → CAPX algorithm 의 transfer
  potential 큼.
- "Cap 잘 먹은 후 scared 40 tick 활용" 메커니즘 미사용 — 활용 시 win-rate
  추가 lift 가능.
- died_pre_eat 24× 차이는 submission 의 risk-aware-ness 부족 = CAPX 의
  defender-aware A* + survival gate 가 직접 cure.

### 부정적 / 위험 (Path 2 ROI 제한 가능)
- A1 family 의 win-rate 약점 (20-30%) 은 cap-eat 가 아님 (50% 임). cap-eat
  fix 가 win-rate 향상 안 함. → **A1 family 의 진짜 약점 = food 경쟁
  메커니즘** (다른 fix 필요).
- Submission 이 이미 cap 안 먹고도 capsule/tuned/aggressive 에 70-80% 이김
  → cap-eat 추가 시 marginal lift 만.
- CAPX 의 cap-aggressive 전략 그대로 transplant 시 submission 의 food return
  loop 깨질 수 있음 (cap 먹은 후 scared window 에서 food 안 먹고 STOP).

### 진짜 ROI 추정 (보수적)
- **capsule/tuned/aggressive**: 이미 70-80% W, 추가 cap-eat 으로 → 80-95% W
  가능 (+10-15pp)
- **A1 family**: cap-eat fix 가 도움 안 됨 (cap 이미 50%, 진짜 약점 = food
  competition). Path 2 가 A1 약점 안 풀음.
- **baseline 등 boundary**: 측정 noise (n=10) 더 필요.

**대안 Path 4 후보 (A1 family 약점 해결)**:
- CEM weight re-evolution against A1 family (다른 fitness function)
- B coordination upgrade (food 분배 효율)
- 새 deposit/return strategy

## 6. Decision tree

다음 액션 선택:

| 옵션 | ROI | 시간 비용 | 위험 |
|---|---|---|---|
| **A) Path 2 narrow integration** | **+10-20pp on capsule/tuned/aggressive (cap-eat lift) → win 80-95%**. A1 family 영향 X. | ~1-2 세션 (CAPX 의 핵심 algorithm 200 LOC submission 에 fold-in) | submission 의 food loop 깨질 위험. ablation knob 필수. |
| B) Path 4 CEM re-evolve | A1 family 약점 직접 cure 가능 (가장 큰 win-rate 향상 잠재) | ~2-3 세션 (CEM evolution 인프라 + fitness function 정의 + 서버 시간) | CEM 가 saturated 일 수도 (이미 A1 가 evolved). |
| C) 둘 다 sequential | 가장 높은 ROI but 가장 큰 시간 | ~3-5 세션 | 시간 부족 가능 |
| D) report 우선 | 60pt 비중 (algorithm 외) 안전 확보 | ~1-2 세션 | 알고리즘 향상 0 |

## 7. Caveats

- **n=10 sample 한계**: per-defender ±28pp 95% CI. boundary defender 는
  n=30 expansion 권고.
- **CAPX 데이터는 n=30** (paired comparison 비대칭). per-defender 직접 비교
  편향 가능.
- **17-defender zoo ≠ tournament 실제 분포** (Claude/Codex advisor 모두
  명시한 limitation). Tournament 에서 baseline 또는 capsule-style 가 주류면
  Path 2 의 ROI 다름.
- **win-rate metric (Phase 0) 와 cap-eat metric (Phase 0.5) 간 상관 관계
  명확하지 않음**. cap-eat 향상이 항상 win-rate 향상은 아님.

## 8. Recommended next session

다음 세션 entry:
1. 사용자 결정: 옵션 A (Path 2 narrow) vs B (Path 4 CEM) vs C (sequential)
   vs D (report).
2. 옵션 A 선택 시: pm47 plan finalize → CAPX 의 어떤 algorithm 부분
   import 할지 specify (defender-aware A*? survival gate? P_survive ranker?).
3. 옵션 B 선택 시: pm48 plan = CEM re-evolution against A1 family +
   fitness function 정의.
4. boundary defender (capsule, tuned, aggressive 의 20%) 만 n=30 으로
   확장하면 추가 정밀도 (5분 sts).

## 9. Files

- 분석 wiki: `.omc/wiki/pm47-submission-cap-eat-comparison.md` (이 파일)
- Submission cap-eat 결과: `experiments/results/pm47_phase0/submission_capx_metric_n10.csv`
- CAPX 결과 (paired): `experiments/results/pm46_v2/capx_matrix_m0_merged.csv`
- Phase 0 win-rate 결과: `experiments/results/pm47_phase0/submission_matrix_n10.csv`
- Wrapper: `minicontest/submission_capsule_logger.py`
- Wrapper script: `experiments/rc_tempo/pm47_phase0_capx_metric_baseline.sh`
- Spec: `.omc/specs/deep-interview-pm47-submission-cap-eat-measurement.md`

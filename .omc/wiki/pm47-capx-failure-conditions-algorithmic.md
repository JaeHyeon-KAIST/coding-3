---
title: "pm47 — CAPX failure conditions + algorithmic improvement hypotheses (no fine-tuning)"
tags: ["pm47", "capx", "failure-conditions", "algorithmic", "no-fine-tuning", "mechanism"]
created: 2026-04-29
sources:
  - "experiments/results/pm46_v2/capx_matrix_m0_merged.csv"
  - "experiments/results/pm46_v2/logs_capx_matrix/"
  - ".omc/wiki/pm46-v2-failure-mode-deep-analysis.md"
  - ".omc/wiki/pm46-v2-FINAL-recovery-17-of-17.md"
links: []
category: debugging
confidence: high
schemaVersion: 1
---

# CAPX failure conditions + algorithmic improvement hypotheses

**사용자 명시 제약**: fine-tuning (knob tweak / threshold sweep) **회피**.
**Conceptual mechanism shift** 만 후보.

## TL;DR

CAPX 510-game matrix 분석:
- **403/510 (79%) eat_alive** — 강력한 baseline
- **107 fails** = **98 stuck** (no_eat_alive) + **9 died_pre_eat** (suicide 거의 안 함, hard-abandon 잘 작동)

Fail seed cluster 분석으로 **3 가지 distinct failure 메커니즘** 식별:

1. **Topology-bound (9 seeds)** — 모든 17 defender 에서 fail. cap 자체가 unreachable 또는 strong-chokepoint.
2. **Reflex-patrol vulnerability (9 seeds)** — capsule/tuned 만 fail. reflex defender 의 cap-region patrol 패턴.
3. **Minimax-specific (1 seed)** — minimax-d3/d2 만 fail. lookahead-based pinning.

각 mechanism 별 **fine-tuning 아닌 algorithmic mechanism shift** 후보 5개 도출.

## 1. 510-game 클러스터 분류

| Tier | Defenders | eat_alive % | 특성 |
|---|---|---|---|
| **Strong** (13 def) | baseline (100%), dummy (100%), rc82/rc_tempo_cousins (93%), A1 family (86-90%), hybrid_mcts (90%), monster (83%) | 80-100% | CAPX 가 거의 항상 cap 도달 |
| **Medium minimax** (3 def) | minimax_ab_d3_opp (66%), minimax_ab_d2 (66%), reflex_defensive (73%) | 66-73% | Lookahead-aware patrol |
| **Weak reflex** (3 def) | capsule (40%), tuned (40%), aggressive (50%) | 40-50% | Reflex chokepoint patrol |

**Aggregate**: 79% eat_alive, 1.8% died_pre_eat (suicide 거의 없음 — hard-abandon
gate 잘 작동), 19% stuck.

## 2. Fail seed overlap 분석

각 defender 의 fail seeds set 의 교집합/차집합:

| Cluster | Seeds | Count | Source defenders |
|---|---|---|---|
| **A — Topology-bound** (모든 defender 에서 fail) | 3, 4, 5, 6, 14, 24, 26, 27, 30 | **9** | All 17 defenders |
| **B — Reflex-patrol-only** (capsule/tuned 에만 추가) | 10, 11, 13, 15, 16, 22, 25, 28, 29 | **9** | capsule, tuned only |
| **C — Minimax-only** | 18 | **1** | minimax_d3, minimax_d2 only |
| **D — Algorithm-fixable** (이전 Phase A 에서 회복됨) | 1, 10 (capsule), 11, 14, 20, 24, 30 (aggressive) | 작음 | S1 fix 로 일부 회복 |

**Interpretation**:
- **A (9 seeds)**: cap 의 위치가 지나치게 모든 path 가 chokepoint 통과. 어떤
  algorithm 으로도 풀기 어려움. **Map topology bound**.
- **B (9 seeds)**: reflex defender 가 cap-region 좁은 corridor 에서 patrol →
  CAPX 의 A* 가 매 tick 다른 path 추천 (defender 위치 변화 따라) → A 진동.
  **Algorithmic improvement target**.
- **C (1 seed)**: minimax 의 lookahead 가 CAPX 의 path 예측 + intercept.
  Single seed = noise 가능, 또는 minimax-specific edge case.

## 3. Failure mechanism 분류 (이전 trace 분석 + 510 game 종합)

### Pattern A — Path bouncing (≈78% of weak-defender fails)

**Symptom**: chosen_target 매 tick 같음 (1 unique target), but A position 진동
(2-3 cells 사이 cycle).

**Mechanism**:
1. Defender 가 매 tick 약간 이동 → `defender_dist_map` 변경
2. A* edge_cost 변경 → A* 가 다른 minimal-cost first step 추천
3. A 가 step 후 다음 tick 에 또 다른 first step 받음 → 이전 cell 로 retreat
4. 1200 tick 동안 같은 cell 진동

**Trigger condition**: defender 가 cap 근처에서 oscillating patrol + corridor
가 좁음 (single-direction A* 가 매 tick 다른 답 가능).

### Pattern B — Target flipping (≈22% of weak-defender fails)

**Symptom**: chosen_target 매 tick 변동 (2 unique targets, 17-41% flip rate).

**Mechanism**:
1. P_survive=0 매 tick (defender 가까이) → ranker floor fallback
2. ranker = distance-only
3. 두 cap 의 BFS dist 가 비슷 + A 의 1-cell 이동만으로 dist tie 가 flip
4. chosen_target 매 tick 변동 → A 진동

**Trigger condition**: 두 cap 이 A 에서 비슷한 거리 + A 가 두 cap 사이
중간 위치 + defender visible.

### Pattern C — True topology bound (≈9 seeds)

**Symptom**: 모든 defender 에서 fail. CAPX 가 어떤 path 도 commit 못 함.

**Mechanism**:
1. Cap 의 위치가 모든 reachable path 에서 chokepoint 통과 필수
2. Defender 가 그 chokepoint 점유 시 cap 도달 불가
3. Pattern A/B 가 함께 발현 (oscillation + 진짜 unreachable)

**Trigger condition**: Cap 이 narrow corridor 끝 + chokepoint 가 single
cell + defender 가 거의 항상 그 cell 점유.

### Pattern D — Suicide (≈9 seeds total, 1.8%)

**Mechanism**: hard-abandon gate (`CAPX_HARD_ABANDON_MARGIN=-1`) 가 일부
edge case 에서 too late 또는 too risky path commit. 거의 발생 안 함 — CAPX
의 가장 작은 fail mode.

## 4. CAPX 가 실패하는 정확한 조건 정리

| 조건 | 결과 |
|---|---|
| Defender 가 cap 근처 patrol + visible | P_survive=0 → ranker degenerate (모든 fail 의 전제) |
| **+ Defender 가 매 tick 약간 이동 (oscillating)** | **Pattern A — A* path first step 매 tick 변경 → A 진동** |
| **+ 두 cap 의 BFS dist 비슷 (ties 가능)** | **Pattern B — chosen_target flip → A 진동** |
| **+ Cap 이 narrow chokepoint 너머** | **Pattern C — 어떤 algorithm 도 풀 수 없음 (topology)** |
| **+ Reflex-based defender (capsule/tuned)** | Pattern A 가 가장 자주 발현 (chokepoint patrol 패턴) |
| **+ Minimax-based defender** | Lookahead 기반 intercept (rare, 1 seed) |
| Defender 가 멀리 또는 invisible | CAPX 가 거의 항상 성공 (strong cluster) |

## 5. Algorithmic improvement hypotheses (fine-tuning 회피)

> **Fine-tuning vs algorithmic 의 정의 (이 wiki 기준)**:
> - Fine-tuning = 기존 knob (CAPX_MIN_MARGIN, sigmoid scale, threshold 등)
>   값 sweep
> - Algorithmic = **기존에 없던 새 mechanism / signal / data structure 도입**

### Tier-1: Conceptual mechanism shift (가장 fine-tuning 안 느낌)

#### Hypothesis 1 — Defender behavior model (frequency map)

**아이디어**: defender 의 last N tick 위치 frequency map 작성 → "이 cell 에서
이전 N tick 동안 K번 나타남" 추적. 일정 cell 이 patrol 거점 → 그 cell 일시
비움 검출 → 그 timing 에 commit.

**왜 fine-tuning 아님**: 새 data structure (frequency map) + 새 decision
signal (patrol-gap detection). 기존 P_survive / margin 과 독립.

**Pattern 영향**: A direct cure (defender 위치 변경 vs path 변경 분리),
B 일부 cure.

**Implementation 추정**: ~30-50 LOC. 새 module-level state 추가.

**Trigger**: 매 tick `_DEFENDER_HISTORY[(d_idx, cell)] += 1` + decay.

#### Hypothesis 2 — True multi-step lookahead (minimax/expectimax depth 2-3)

**아이디어**: 현재 CAPX 는 1-step (gate trigger + path planning). 진짜 lookahead
면 "이 step 후 defender 의 best response 후 my best response..." simulation.
Cycle detection 가능 (Pattern A direct).

**왜 fine-tuning 아님**: 새 algorithm paradigm. CAPX 는 reactive, lookahead 는
planning.

**Pattern 영향**: Pattern A direct cure (cycle 의 다음 step 선택 시 oscillation
회피).

**Implementation 추정**: ~100-200 LOC. expectimax tree 구현. 1s budget 안에서
depth 2-3 가능 (분기 적음).

#### Hypothesis 3 — B agent as distraction (game rule 활용)

**아이디어**: 현재 CAPX 의 B = `StubBAgent` (STOP forever). B 가 다른 cap
방향 또는 다른 corridor 으로 movement → defender 분산. 두 명 vs 두 명 게임
규칙 활용.

**왜 fine-tuning 아님**: 새 agent role + game-mechanic exploitation. CAPX 의
algorithm 안 건드림.

**Pattern 영향**: **Reflex-patrol cluster (B-9 seeds) 직접 cure 가능 가설**:
defender 가 두 명 invader 다 추적 못 함 → A 가 capsule corridor 통과 가능.

**Implementation 추정**: ~50-80 LOC. 새 `DistractionBAgent` class +
solo wrapper 변경. CAPX A 자체는 unchanged.

**위험**: B 가 너무 멀리 가면 defender 가 무시. B 의 정확한 position 결정
algorithm 필요 (예: A 가 가는 cap 와 반대 영역의 cap 향해).

#### Hypothesis 4 — Wait-and-bait (defender frustration)

**아이디어**: A 가 cap-region 진입 시도 → defender 가 cap 근처 patrol 시작 →
A 가 일부러 후퇴 (10-20 tick) → defender 가 cap 떠남 (assume reflex) → A 가
재진입.

**왜 fine-tuning 아님**: 새 strategic loop (advance-retreat-readvance).
현재는 단순 commit-or-abandon.

**Pattern 영향**: Reflex-patrol cluster 일부 cure 가능 (defender 가 invader 안
보면 patrol 떠남 가정).

**위험**: 일부 defender 가 cap 영원히 보호 (commit-once-stay) 시 무한 loop.
Time budget (1200 tick) 낭비.

**Implementation 추정**: ~80-120 LOC. retreat trigger + cap-region re-entry
logic.

### Tier-2: Algorithmic add-on (fine-tuning 의 경계 위)

#### Hypothesis 5 — Position-history oscillation detector + force commit

**아이디어**: A position last 8 ticks 가 같은 2-3 cells cycle 하면 "현재
chosen_target 으로 force-commit" (gate 평가 무시).

**왜 fine-tuning 살짝**: 새 detector + 새 mechanism. 단 gate 무시는
기존 hard-abandon 의 inverse 라 mechanism 비슷.

**Pattern 영향**: Pattern A direct cure.

**Implementation 추정**: ~20 LOC.

#### Hypothesis 6 — Path-cell hysteresis (CCG advisor 권고, 미구현)

**아이디어**: 이전 path 의 first 5 cells 와 80% overlap 하는 새 path 면
"같은 path" 로 간주 → committed_target 이 아니어도 threshold 적용.

**왜 fine-tuning 살짝**: 기존 hysteresis 의 확장. 단 cell-level 이라 새 layer.

**Pattern 영향**: Pattern A direct cure.

**Implementation 추정**: ~15-25 LOC.

#### Hypothesis 7 — Alternative survival signal

**아이디어**: P_survive=0 일 때 fallback 으로 (a) corridor width, (b) escape
route count, (c) chokepoint distance 등 사용. ranker 가 정보 가지게.

**왜 fine-tuning 안 느낌**: 새 signal 도입.

**Pattern 영향**: B (target flipping) cure. Pattern A 도 일부.

**Implementation 추정**: ~50-80 LOC. 새 signal computation.

### Tier-3: Paradigm shift (가장 큰 변화, 위험)

#### Hypothesis 8 — Belief state / imperfect info modeling

현재 capture.py 가 fog-of-war disabled. 그러나 belief state 추가 시 더 robust.
큰 redesign. **NOT recommended for current cycle**.

#### Hypothesis 9 — RL baseline (Q-learning, DQN)

새 paradigm. **NOT recommended** — pm22-pm45 의 CEM evolution 기반 + 시간 부족.

## 6. Recommendation ranking (사용자 결정 회부)

### Tier-1 ranked by ROI / risk:

| Rank | Hypothesis | Pattern fix | LOC | Risk | "fine-tuning 아님" 강도 |
|---|---|---|---|---|---|
| **#1** | **H3 — B as distraction** | **B (9 reflex seeds) 직접** | 50-80 | Medium (B path 결정) | **★★★★★** game-rule exploit |
| **#2** | **H1 — Defender behavior model** | A direct, B 일부 | 30-50 | Low (additive) | ★★★★ 새 data structure |
| **#3** | **H2 — Multi-step lookahead** | A direct | 100-200 | Low-Med (1s budget) | ★★★★★ 새 paradigm |
| #4 | H4 — Wait-and-bait | Reflex 일부 | 80-120 | High (loop 위험) | ★★★ strategic loop |

### Tier-2 (smaller, but still algorithmic):

| Rank | Hypothesis | Pattern fix | LOC | "fine-tuning 아님" 강도 |
|---|---|---|---|---|
| #5 | H5 — Oscillation detector + force commit | A direct | ~20 | ★★ small new mechanism |
| #6 | H6 — Path-cell hysteresis | A direct | ~20 | ★ existing hysteresis 확장 |
| #7 | H7 — Alternative survival signal | B direct | 50-80 | ★★★ 새 signal |

## 7. 사용자 결정 회부 (다음 액션)

이 wiki 는 **분석 + hypothesis 도출만**. 다음 결정:

1. **Tier-1 H3 (B distraction) 실험** — 새 `DistractionBAgent` class +
   solo wrapper 만들기. Reflex-patrol cluster 9 seeds 회복 가능 가설 검증.
   가장 fine-tuning 안 느낌 + game-rule 활용. **추천**.
2. **Tier-1 H1 (Defender behavior model) 실험** — frequency map data structure
   추가. Pattern A 의 매 tick path 변경 자체 흡수.
3. **Tier-1 H2 (Multi-step lookahead) 실험** — 큰 작업, 가장 큰 paradigm shift,
   하지만 가장 generalizable.
4. **여러 Tier-1 sequential** — H3 first (ROI 명확) → 결과 보고 H1/H2 추가.
5. **Tier-2 first (작은 변화)** — H5 oscillation detector (~20 LOC) 빨리 구현,
   결과 보고 큰 결정.
6. **분석 only — 다른 axis 로 (예: pm47 Path 4 = CEM re-evolution)**.

## 8. Caveats

- **Topology-bound 9 seeds 는 어떤 algorithm 으로도 풀 수 없음** (가설). 그
  중 일부 가 algorithm 으로 회복 가능한지 = 미검증.
- **CAPX 자체 개선의 transfer**: 모든 hypothesis 가 CAPX research probe 의
  성능 향상. submission 으로의 transfer 는 별도 plan (pm47 Path 2).
- **Sample size**: per-defender n=30 → 95% CI ±18pp. 회복 가능 seed 가
  noise 인지 확인 필요.
- **"fine-tuning vs algorithmic" 의 경계 모호**: knob 추가도 algorithmic
  가능. 이 wiki 의 ranking 은 보수적 (가장 mechanism shift 큰 것 우선).

## 9. Files

- 이 wiki: `.omc/wiki/pm47-capx-failure-conditions-algorithmic.md`
- 510-game CSV: `experiments/results/pm46_v2/capx_matrix_m0_merged.csv`
- 510-game logs: `experiments/results/pm46_v2/logs_capx_matrix/`
- 이전 deep analysis: `.omc/wiki/pm46-v2-failure-mode-deep-analysis.md`
- CCG advisor 권고 (이전): `.omc/wiki/pm46-v2-ccg-improvement-consultation.md`

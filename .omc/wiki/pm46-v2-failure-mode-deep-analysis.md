---
title: "pm46 v2 CAPX — failure mode deep analysis (post Phase A)"
tags: ["pm46-v2", "capx", "failure-analysis", "oscillation", "ranker-degenerate", "ccg-postmortem"]
created: 2026-04-29
updated: 2026-04-29
sources:
  - "experiments/results/pm46_v2/ccg_phaseA_v1/{baseline,s1,s3,s1s3}.csv"
  - "experiments/results/pm46_v2/ccg_phaseA_v2/{s2,s1s2s3}.csv"
  - "trace logs (in-memory tmp)"
  - ".omc/wiki/pm46-v2-ccg-improvement-consultation.md"
links:
  - "pm46-v2-ccg-improvement-consultation"
  - "pm46-v2-FINAL-recovery-17-of-17"
  - "pm46-v2-capx-code-review-phase4-tuning"
category: debugging
confidence: high
schemaVersion: 1
---

# pm46 v2 CAPX — failure mode deep analysis

**Question**: Phase A 6 variants × 540 games 다 했는데 lift 0~+3pp.
3 advisor (Codex/Gemini/Claude) 추정 (각각 +5-25pp) 가 모두 빗나간
**진짜 이유**? 어떤 game 에서 어떻게 실패하는지 trace 수준에서 추적.

**Bottom line (TL;DR)**:
1. **Capsule/tuned 의 57% (17/30) seeds 는 algorithm-immune topology bound** —
   어떤 fix 도 회복 불가. Algorithmic ceiling 자체가 +3pp 근처.
2. **진짜 fail mode = F2 oscillation, NOT F1 over-rejection** — gate 는 매
   tick TRIGGER 인데도 A 가 cap 못 먹음. 3 advisor 모두 잘못된
   failure mode (F1/F3/F4) 가정해서 fix 가 핀트 어긋남.
3. **Ranker degenerate**: `p_surv=0.00` 매 tick → `CAPX_MIN_PSURVIVE=0.2` floor 항상 발동
   → ranker = distance-only → 두 cap 의 BFS dist 가 비슷 + A 의 작은 이동만으로 target flip → A 자리에서 stuck.
4. **S1 (A\* horizon align) 가 작은 lift 주는 이유**: ranker degenerate 자체를
   풀지 않지만 path 평가 더 stable → target flipping 덜 → 일부 게임에서
   commit 가능.
5. **S2 가 negative 인 이유**: A\* (own-side threat=0) 와 gate (raw threat) 의 view 불일치
   → planning/gating deadlock → 268 tick DRIFT 만 함.

---

## 1. Seed-level consistency 분석 (capsule + tuned)

Capsule 과 tuned 의 fail seeds 가 **모든 variant 에서 100% 동일** —
두 defender 가 사실상 같은 알고리즘.

### 1.1 Topology-bound vs algorithm-sensitive

| Category | Seeds (capsule, 30 total) | Count |
|---|---|---|
| **Topology-bound** (모든 variant fail) | 3, 4, 5, 6, 11, 13, 14, 15, 16, 22, 24, 25, 26, 27, 28, 29, 30 | **17 (57%)** |
| Algorithm-sensitive | 1, 10 | 2 (7%) |
| Always success | 2, 7, 8, 9, 12, 17, 18, 19, 20, 21, 23 | 11 (37%) |

**Implication**: Algorithm 으로 회복 가능한 최대 = 2 seeds = +6.7pp.
실제로 S1 만 **seed 10 회복** (+1 game, +3.3pp). 이게 ceiling.

### 1.2 Per-variant rescue/break vs baseline (capsule)

| Variant | Rescued | Broken | Net |
|---|---|---|---|
| s1 | [10] | — | +1 |
| s3 | — | — | 0 |
| s1s3 | [10] | — | +1 |
| s2 | — | — | 0 |
| s1s2s3 | — | [1] | **−1** |

**S1S2S3 가 baseline 의 success 인 seed 1 을 깨뜨림** (regression). 이는 S1+S2+S3
조합이 가산이 아니라 **negative interference**.

### 1.3 Aggressive 의 패턴 (다름)

| Category | Seeds (aggressive) | Count |
|---|---|---|
| Topology-bound | 2, 3, 5, 6, 13, 16, 22, 25, 26, 28, 29 | 11 (37%) |
| Algorithm-sensitive | 1, 10, 11, 14, 20, 24, 30 | 7 (23%) |

| Variant | Rescued | Broken | Net |
|---|---|---|---|
| s1 | [11, 20, 30] | [1, 24] | +1 |
| s2 | [14] | [1, 10] | −1 |
| s1s3 | [11, 20, 30] | [1, 24] | +1 (s3 효과 0 확인) |
| s1s2s3 | [11, 20] | [1, 10, 24] | −1 (S2 가 S1 의 30 lift 깎음) |

---

## 2. Trace 분석 — 실제 fail mechanism

### 2.1 Seed 10 capsule: baseline FAIL vs s1 SUCCESS

| Variant | trace lines | gate=TRIGGER | gate=DRIFT | caps eaten | deaths | game outcome |
|---|---|---|---|---|---|---|
| baseline | 301 (1200 tick 다 돔) | 296 | 4 | 0 | 0 | timeout, no cap |
| s1 | 96 (cap eat 후 STOP) | 87 | 5 | 2 | 0 | success |

**Critical observation**: baseline 의 296/301 = **98% TRIGGER**. **gate
over-rejection 아님!** 매 tick gate 는 OK 라고 하지만 A 는 cap 못 먹음.

**A 의 oscillation pattern (baseline, ticks 797-769)**:

```
tick 797: a=(12,9)  chosen_tgt=(30,3) act=South
tick 793: a=(12,8)  chosen_tgt=(23,13) act=North   ← target flip!
tick 789: a=(12,9)  chosen_tgt=(23,13) act=North
tick 785: a=(12,10) chosen_tgt=(30,3) act=South    ← target flip!
tick 781: a=(12,9)  chosen_tgt=(30,3) act=South
tick 777: a=(12,8)  chosen_tgt=(23,13) act=North   ← target flip!
tick 773: a=(12,9)  chosen_tgt=(23,13) act=North
tick 769: a=(12,10) chosen_tgt=(30,3) act=South    ← target flip!
```

A 가 column 12 에서 (12,8) ↔ (12,9) ↔ (12,10) 사이 **8-tick cycle 진동**.
chosen target 도 매 tick 변동 (23,13) ↔ (30,3).

**모든 trace line: `p_surv=0.00`**. 즉 P_survive sigmoid 가 weak defender
가까이서 항상 0 → ranker 의 floor fallback (`CAPX_MIN_PSURVIVE=0.2`) 항상
발동 → ranker = pure BFS distance.

### 2.2 Seed 1 capsule: baseline SUCCESS vs s1s2s3 FAIL (S2 가 망침)

| Variant | trig | DRIFT | caps | deaths |
|---|---|---|---|---|
| baseline (success) | 99 | 0 | 2 | 2 |
| s1s2s3 (fail) | 34 | **266** | 0 | 0 |

**S1S2S3 의 deadlock**: gate REJECT 268 ticks. baseline 에선 99 TRIGGER 인 게임이
S1S2S3 에서는 268 DRIFT.

**S2 의 인터페이스 불일치 메커니즘**:
- A\* edge_cost: `if _is_own_side(cell): return 1` → own-side cells threat=0
- → A\* 가 own-side cells 통과하는 path 선호 (낮은 비용)
- 하지만 `_gate.margin_at` 은 raw threat (S2 scope-narrow 에서 own-side mask 빠짐)
- → gate 는 path 의 own-side cells 도 defender 거리로 평가
- → gate 가 path REJECT (own-side 인데 defender 가 가까이 있어서 margin 음수)
- A* 가 끊임없이 이 path 추천하지만 gate 는 끊임없이 REJECT → A drift 만 함
- **A 무한 stuck**

### 2.3 Seed 11 aggressive: baseline FAIL vs s1 SUCCESS

| Variant | trig | DRIFT | caps | deaths |
|---|---|---|---|---|
| baseline | 300 | 0 | 0 | 0 |
| s1 | 87 | 0 | 2 | 1 |

baseline 의 last 3 trace lines (게임 끝)도 동일 oscillation 패턴:
```
tick 12: a=(20,16) tgt=(21,7)  act=West   ← target flip
tick 8:  a=(19,16) tgt=(30,8)  act=East   ← target flip
tick 4:  a=(20,16) tgt=(30,8)  act=East
```
A 가 (19,16) ↔ (20,16) 사이 진동, target 도 (21,7) ↔ (30,8) 변동.

s1 의 success: 한 번 죽긴 했지만 (tick 688) 결국 cap 1개 eat (tick 852),
이후 두번째 cap 도 eat. 즉 **S1 가 oscillation 을 부분적으로 풀어 commit
가능하게 함**.

---

## 3. 진짜 fail mechanism 정리

### 3.1 F2 oscillation, NOT F1 over-rejection

CCG advisor 들의 가정:
- Codex Top #2 / Gemini Top #2: F1 over-rejection (gate 너무 보수적)
- Codex Top #1: F1 + bad fallback drift
- Gemini Top #3 (S3): F3 post-trigger death (suicide)

**실제로**: trace 분석 결과 매 tick TRIGGER. F1 메커니즘 발동 안 함.
**진짜는 F2** — gate 는 OK 인데 ranker 가 target 매 tick 바꿔서 A 자리에 stuck.

### 3.2 Ranker degenerate cascade

```
weak defender (capsule/tuned/aggressive)
  ↓
defender 가 capsule 근처 patrol → BFS dist from defender to A's path = small
  ↓
margin (= d_dist - step_idx) ≤ 0 → P_step_safe(margin) = sigmoid(margin/1.5) ≈ 0
  ↓
P_survive = product of P_step_safe = 0.00 매 tick
  ↓
max(P_survive) < CAPX_MIN_PSURVIVE (0.2) → ranker floor fallback
  ↓
ranker = sorted by bfs_dist (no survival weighting)
  ↓
두 cap 의 BFS dist 가 거의 비슷 → A 가 1-cell 이동하면 dist tie 가 flip
  ↓
chosen_tgt 매 tick 변경 → path 매 tick 변경 → A direction 매 tick 변경
  ↓
A 가 같은 cells 사이 진동 (F2 oscillation)
  ↓
1200 tick 동안 cap 못 먹음 → no_eat_alive
```

### 3.3 왜 S1 만 작은 lift?

S1 (A\* horizon align) 가 path 평가 stability 살짝 개선:
- A* 가 짧은 path (≤ 8 step) 만 평가 → BFS fallback 덜 일어남
- BFS fallback path = 위협 무시 path → ranker 의 P_survive 가 더 잘못된 추정
- S1 으로 A* 가 actual threat-aware path 자주 반환 → ranker 가 두 cap
  사이 비교할 때 신호가 조금 더 안정 (둘 다 0 이지만 A* node-cap overflow 안 됨)

→ **+1 game lift on capsule (seed 10)** + **+3 games on aggressive (seeds 11/20/30)**
→ aggregate +3pp.

### 3.4 왜 S3 효과 0?

`_p_survive` 의 i=0 cell skip 은 P_survive 값이 0 인 시나리오에서 의미 없음:
- 0 × sigmoid(margin_0) = 0
- skip 해도 1 × ∏ remaining = 0 (remaining 들도 0)
- → 모든 게임에서 같은 floor fallback 발동 → 같은 결과

P_survive 가 정보가 있을 때만 (모든 sigmoid > 0.3 등) S3 가 의미. weak
defender 시나리오에서 P_survive 항상 0 → S3 무용지물.

### 3.5 왜 S2 negative?

Scope-narrow S2 의 의도: planning (A\*) + ranker (`_p_survive`) 만 own-side
mask. gate + drift 는 raw threat. **이 비대칭이 deadlock 만듦**:
- A\* 가 "own-side path 추천" (cheap)
- gate 가 "그 path 의 own-side cells 도 raw threat 평가, 위험" → REJECT
- drift fallback 이 "raw threat 따라 안전 cell 로" — own-side 안전 cell 로 drift
- 그러나 cap 향한 progress 없음 → 계속 drift
- 극단적 케이스 (seed 1): 268 tick DRIFT 만 함

S2 의 planning/gating 일관성을 만들려면 둘 다 same own-side mask 사용해야
하는데, 그러면 phase A v1 의 broken 결과 (seed 1 의 7 deaths border-rush)
로 돌아감. **S2 는 어느 scope 로 적용해도 broken**.

---

## 4. Topology-bound 의 본질 (capsule/tuned 17 seeds)

### 4.1 왜 algorithm-immune?

Trace 분석은 algorithm-sensitive (seed 1, 10) 만 했지만, topology-bound 17
seeds 의 패턴은 거의 같을 것으로 추정:
- 두 cap 위치가 A spawn 으로부터 비슷한 BFS dist
- 두 cap 사이 column 영역이 좁음 (쉬운 oscillation 트랩)
- weak defender 가 그 column 패트롤 → P_survive 항상 0
- → ranker degenerate → F2 oscillation → no cap

이걸 풀려면:
- **target hysteresis (현재 committed_target threshold 만 hysteresis;
  ranker 단계에서 target flip 자체는 hysteresis 없음)**
- **oscillation detector** (A position history 기반 stuck 탐지 후 forced
  commit)
- **distance-tie stable 선택** (예: hash-based 또는 첫 결정 sticky)
- **P_survive 대안 신호** (escape route count, choke point 거리)

이 fix 들은 본 wiki 의 scope 가 아님 (분석 only). 그러나 weak defender
에서 algorithm 추가 lift 가능성이 있다면 이 방향임.

### 4.2 왜 capsule 과 tuned 가 100% 동일?

`zoo_reflex_capsule.py` 와 `zoo_reflex_tuned.py` 의 코드 직접 비교 없이도
trace evidence 가 명확함:
- 같은 18 seeds 에서 fail (baseline)
- 같은 12 seeds 에서 success
- eat_tick 도 거의 동일 (e.g., seed 7 capsule 953, tuned 953)

→ 두 defender 의 alpha-beta-pruned reflex 가 cap 근처에서 동일한
defensive policy 를 만들고 있음. 결과 → CAPX 입장에서 같은 problem.
→ 측정 시 effective n=60 (paired), 표본 분산 절반.

### 4.3 Aggressive 는 왜 다름?

Aggressive 는 11 (37%) topology-bound + 7 algorithm-sensitive — capsule
보다 noisy. 추정:
- aggressive defender 가 capsule 보다 stochastic / aggressive movement
- A 의 작은 algorithm 변화가 더 큰 trajectory 변화 일으킴
- ranker 의 distance-tie flip 도 패턴 다름

S2 가 aggressive 에 -1 (seeds 1, 10 break, seed 14 rescue) — 일종의
랜덤 코인 던지기. n=30 의 표본 한계.

---

## 5. CCG advisor postmortem (왜 모두 빗나갔나)

### 5.1 잘못된 baseline assumption

Advisor prompt (`.omc/research/pm46-v2-ccg/CONSULT_PROMPT.md`) 에서 언급한
failure mode taxonomy:
- F1 over-rejection (gate UNSAFE)
- F2 oscillation (UNSAFE↔SAFE flip)
- F3 post-trigger death
- F4 no detour

이 분류는 **이전 ABS attacker 의 failure mode 였음** (`.omc/plans/omc-pm46-v2-capsule-only-attacker.md`
§2.3). CAPX 는 다른 algorithm — 그 4 mode 중 일부만 유전.

**진짜 CAPX 의 fail mode**:
- F2-prime: gate 항상 OK 지만 ranker target flipping → A 자리 진동
- F5 (new): ranker degenerate via P_survive=0 → distance-only → tie-flip
  amplified by A 의 1-cell move

Advisor 들이 F2 본래 의미 (gate UNSAFE↔SAFE flip) 만 알아서 "path-cell
hysteresis" 같은 fix 추천. 그러나 진짜 메커니즘은 ranker 단계의 target
flipping — gate 단계 영향 없음.

### 5.2 P_survive 모델의 정보 손실

Advisor 가 받은 spec 에서 sigmoid scale=1.5 가 있었지만, "weak defender
시나리오에서 P_survive 가 항상 0" 이라는 정보는 없었음. 결과:
- Codex/Gemini 가 "P_survive 미세 조정 (off-by-one fix)" 만 봐서
  ranker degenerate 의 본질 못 봄
- "asymmetric threat mask" 도 P_survive 가 정보 가질 때만 의미 — 0 인
  시나리오에선 unchanged

### 5.3 게임 trace 데이터 부재

Advisor prompt 에 codex_matrix CSV summary 만 줬지 game trace (CAPX_TRACE
출력) 안 줌. trace 보면:
- gate 가 매 tick TRIGGER (F1 아님)
- p_surv=0.00 매 tick (ranker degenerate)
- chosen_tgt 매 tick flip (F2-prime)

이 정보가 advisor 에게 있었으면 다른 fix 추천했을 것.

### 5.4 교훈

1. **CCG 자문 전에 게임 trace 깊이 분석 먼저** — failure mode 가 spec
   가정과 다를 수 있음.
2. **Aggregate metric (eat_alive %) 만 보고 algorithm 추측 안 됨** —
   per-game mechanism 분석 필요.
3. **Algorithm-sensitive seeds 가 작으면 (10% 미만) algorithm tuning 의
   ROI ceiling 도 작음** — Phase A 같은 ablation 으로 사전 측정 가능.

---

## 6. 진짜 fix candidates (분석 결과의 implication, 구현 X)

이 wiki 는 분석 only. 구현은 별도 plan. 그러나 분석 결과가 가리키는
방향:

### 6.1 Target-flipping hysteresis (NOT yet tried)

현재 hysteresis 는 gate threshold 단계 (committed_target == new target →
threshold -2). 그러나 **ranker 가 target 자체 변경하면 hysteresis
무관**. 진짜 fix:
- Ranker 도 last_chosen_tgt 를 sticky 로 (예: same tgt → bonus 1.5×, or
  P_survive 가 새 후보보다 ≥30% 작아야 switch)
- Or: oscillation detector → A position 의 last 8 ticks 가 같은 2-3 cells
  순환이면 force-commit on currently chosen target

### 6.2 Ranker degenerate 보강

P_survive 가 항상 0 일 때 distance-only fallback 대신:
- Fallback 신호로 BFS dist + cap 으로의 corridor width (좁을수록 위험)
  + cap 의 escape route count
- Or: cap 의 home-side mirror cell (own-side staging) 까지 dist 로 ranking

### 6.3 Topology-bound 진단 + skip

17 capsule seeds 가 algorithm-immune. 이걸 detect 하면 (예: 첫 50 tick
trace 에서 oscillation 발견) 게임 일찍 abort 또는 다른 strategy fallback.

이 모두 분석의 implication. 구체적 plan 은 사용자 결정 + 별도 wiki.

---

## 7. 결론

1. **Algorithm-immune ceiling = +3pp** (capsule 1 seed, aggressive 1-3 seeds).
   3 advisor 의 +5-25pp 추정 모두 잘못된 fail mode 가정에서 출발.
2. **진짜 fail mode = F2-prime (ranker target flipping)** + **F5 (P_survive
   degenerate)**. 둘 다 advisor 가 다루지 않음.
3. **S1 만 keep** (가장 작은 LOC + 0 regression + 측정 lift 있음).
4. **S2/S3 효과 측정 0** — default OFF 유지.
5. **S1S2S3 default 시 regression** (seed 1 capsule break) — 절대 default 로 가면 안 됨.
6. **Algorithm 으로 더 큰 lift 원하면** target-flipping hysteresis +
   oscillation detector 방향 — 별도 plan.
7. **"성능 우선" path** = algorithm 더 추가하기보단 submission code
   (`20200492.py`) 의 17-defender 토너먼트 측정 + 약점 진단이 더 큰 ROI.
   CAPX 의 79% 능력은 research probe — submission 적용 separate plan (pm47).

---

## 8. 첨부 데이터

- 6 variants × 90 games CSV: `experiments/results/pm46_v2/ccg_phaseA_v1/*.csv`
  + `experiments/results/pm46_v2/ccg_phaseA_v2/*.csv`
- 게임 logs (각 게임별): `experiments/results/pm46_v2/ccg_phaseA{,_v2}/logs/`
- Trace 분석 (in-memory tmp): seed 10 capsule baseline+s1, seed 1 capsule
  baseline+s1s2s3, seed 11 aggressive baseline+s1

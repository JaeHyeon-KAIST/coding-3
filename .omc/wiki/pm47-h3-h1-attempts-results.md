---
title: "pm47 — H3 (B distraction) + H1 (defender history) Mac smoke results + next-session candidates"
tags: ["pm47", "capx", "h3", "h1", "smoke", "negative", "next-session"]
created: 2026-04-29
sources:
  - "minicontest/zoo_reflex_rc_tempo_capx_distract.py"
  - "minicontest/zoo_reflex_rc_tempo_capx.py (CAPX_USE_DEF_HISTORY env added)"
  - "experiments/results/pm47_h3/h3_smoke.csv"
  - "experiments/results/pm47_h1/h1_smoke.csv"
  - ".omc/wiki/pm47-capx-failure-conditions-algorithmic.md"
links: []
category: debugging
confidence: high
schemaVersion: 1
---

# pm47 — H3 (B distraction) + H1 (defender history) Mac smoke results

## TL;DR

Tier-1 두 hypothesis 둘 다 Mac smoke (5 weak def × 5 seed = 25 game) 에서
**negative** vs CAPX baseline:

| Hypothesis | smoke result | Δ vs CAPX | mechanism diagnosis |
|---|---|---|---|
| H3 (B as distraction) | 12/25 (48%) | **-8pp** | B 가 chokepoint 못 뚫고 자기 영역 oscillating → distract 효과 0 |
| H1 (defender history model) | 10/25 (40%) | **-16pp** | reflex defender 의 recent_visits set 가 거의 모든 cap-region 포함 → threat-skip 거의 무효 |
| (CAPX baseline) | 14/25 (56%) | — | reference |

**사용자 목표 80% 달성 가능성 분석**: CAPX baseline 79% (510 game 기준).
80% 도달은 algorithmic ceiling 으로 marginal — failure-mode wiki 의 "17/30
topology-bound" finding 은 algorithm-immune 한계 강하게 시사.

**다음 세션**: 여러 방향 다 시도 (사용자 명시). 후보 ranked list 아래 §4.

---

## 1. H3 (DistractionBAgent) 구현 + 결과

### Implementation
- `minicontest/zoo_reflex_rc_tempo_capx_distract.py` 작성 (~120 LOC).
- A = `ReflexRCTempoCapxAgent` (unchanged, CAPX baseline 그대로).
- B = `DistractionBAgent`: A 가 안 가는 cap 으로 BFS-walk (A 의 chosen_target
  state 공유 read).
- `createTeam`: A + B (StubB 대신).

### Smoke result (5 def × 5 seed)

| Defender | H3 alive | CAPX baseline (same seeds) | Δ |
|---|---|---|---|
| zoo_reflex_capsule | 0/5 | 1/5 | -1 |
| zoo_reflex_tuned | 0/5 | 1/5 | -1 |
| zoo_reflex_aggressive | 2/5 | 2/5 | 0 |
| zoo_dummy | 5/5 | 5/5 | 0 |
| baseline | 5/5 | 5/5 | 0 |
| **Aggregate** | **12/25** | **14/25** | **-2 (-8pp)** |

### Trace 분석 (capsule seed 1, fail 게임)

`DISTRACT_TRACE=1` 로 1200 tick trace:
- B 의 trajectory: `(1,1) → (11,11) → (6,15) → (1,13) → (1,4) → (12,9) → (6,12) → ...`
- 자기 영역 (Red side, x ≤ 16) 에서만 oscillating
- B 의 target = (23,10) Blue side cap (298/300 tick 동일)
- B 의 dist_to_target: **14 → 17 → 20 → 26 → 29 → 35 → 38 → 44 → 47 → 50** ← **계속 멀어짐**!
- 8 visits each on cells (6,11)-(6,15), (3,15)-(3,16) 등 — **B 도 같은 cells 진동**

### Fail mechanism (H3)
- B 가 cap 향해 가다가 chokepoint 에서 막혀서 자기 영역 진동
- **B 가 invader 자체가 못 됨** (opp side 진입 못 함)
- defender 가 B 추적 안 함 → distract 효과 0
- 오히려 baseline 의 1 win 마저 잃음 (reason: B 가 차지하는 corridor 가
  A 의 path 와 미세하게 conflict 가능)

### Why hypothesis failed
- 가정: "단순 BFS-walk B 가 invader 가 되어 defender 분산"
- 현실: "단순 BFS B 도 chokepoint 통과 못 함" — H3 의 conceptual gap.
- Fix 위해선 **B 도 CAPX-grade 알고리즘** (defender-aware A* + survival gate)
  필요. 그러나 그러면 두 CAPX 같은 fail 패턴 가능 + LOC 큼.

---

## 2. H1 (Defender history model) 구현 + 결과

### Implementation
- `zoo_reflex_rc_tempo_capx.py` 에 env knob `CAPX_USE_DEF_HISTORY=1` 추가
  (default OFF, ablation-friendly).
- `_CAPX_STATE['def_recent_visits'][d_idx]` = `deque(maxlen=20)` of last
  20 ticks visited cells per defender.
- `chooseAction` 매 tick 모든 visible defender 의 position append.
- `_astar_capx.edge_cost` 가 use_def_history=1 시: cell_b 가 모든 defender
  의 def_recent_visits 에 안 포함 → return 1 (no threat).

### Smoke result (5 def × 5 seed, CAPX_USE_DEF_HISTORY=1)

| Defender | H1 alive | CAPX baseline | Δ |
|---|---|---|---|
| zoo_reflex_capsule | 0/5 | 1/5 | -1 |
| zoo_reflex_tuned | 0/5 | 1/5 | -1 |
| zoo_reflex_aggressive | **0/5** | 2/5 | **-2** |
| zoo_dummy | 5/5 | 5/5 | 0 |
| baseline | 5/5 | 5/5 | 0 |
| **Aggregate** | **10/25** | **14/25** | **-4 (-16pp)** |

### Fail mechanism (H1, hypothesized)
- "Reflex defender 가 매 tick 위치 변경 → recent_visits set 매우 빠르게 cap-region
  cells 거의 다 포함" → "threat-skip" 가정이 거의 false → behavior 거의 동일
- 또는 **defender 가 reactive** — invader 가 보이면 즉시 거기 옴 →
  `recent_visits` 가 history 라 미래 visit 무시
- Aggressive 에서 -2 = baseline 의 2 win 도 잃음. recent_visits 가 너무
  permissive → A 가 commit but defender 가 갑자기 옴 → die

### Why hypothesis failed
- 가정: "Defender 가 last 20 tick 안 가본 cell → 가지 않을 것"
- 현실: "Defender 가 invader 보면 reactive 라 어디서도 옴" — history
  prediction 무효
- Fix 위해선: **better defender model** (cycle detection? predicted next
  position?) 또는 **상태 도구화** (어떤 condition 에서 history 의미 있는지)

---

## 3. 두 hypothesis 의 공통 lesson

1. **CAPX 의 algorithmic ceiling 이 진짜 작음** — 우리 hypothesis 들이
   conceptually 다른 방향 (게임 규칙 활용 vs 데이터 모델링) 이지만 둘 다 실패.
2. **Reflex defender 의 chokepoint patrolling 이 algorithm-immune 가설 강화** —
   17/30 topology-bound + 매 hypothesis 가 weak defender 에서 cure 못 함.
3. **smoke n=25 의 한계**: 95% CI ±20pp. -8pp / -16pp 가 진짜인지 noise 인지
   확실치 않음. 단 패턴 (모두 weak defender 에서 worse) 은 noise 보다 signal
   다움.
4. **Mac smoke 가 효과적 filter**: sts dispatch 전에 hypothesis kill — 시간
   효율적.

---

## 4. 다음 세션 candidate list (사용자 명시: 여러 방향 다 시도)

### Algorithm-side (CAPX 자체 개선)

#### Tier-2 (smaller LOC, surgical)

| # | Hypothesis | Idea | LOC | Expected |
|---|---|---|---|---|
| H5 | **Oscillation detector + force commit** | A position last 8 ticks 가 같은 2-3 cells cycle → force commit on chosen target (gate 무시). | ~20 | Pattern A direct cure, +3-5pp 가능 |
| H6 | **Path-cell hysteresis** | 이전 path first 5 cells 와 80% overlap → "same path" → gate threshold -2 적용 (committed_target 아니어도). | ~20 | Pattern A direct cure |
| H7 | **Alternative survival signal** | P_survive=0 일 때 fallback signal: corridor width / escape route count / chokepoint distance. | ~50-80 | Pattern B direct cure |
| H8 | **Forced commit on time-budget exhaustion** | Game tick > 800 인데 cap 못 먹음 → margin threshold -3 (suicide risk). | ~10 | Late-game commit lift |

#### Tier-1 v2 (refined of failed Tier-1)

| # | Hypothesis | Idea | LOC |
|---|---|---|---|
| H3-v2 | **B = mini-CAPX (defender-aware)** | B 도 defender-aware A* + survival gate. CAPX 처럼. | ~150 |
| H1-v2 | **Defender cycle detection** | recent_visits 단순 set 대신 cycle period 추출. defender 가 (a→b→c→a→b→c) 이면 next position 정확 prediction. | ~80 |

#### Tier-3 (paradigm shift, 큰 작업)

| # | Hypothesis | Idea | LOC | Risk |
|---|---|---|---|---|
| H2 | **Multi-step lookahead (minimax depth 2-3)** | 진짜 expectimax tree. Cycle detection 자동. | 100-200 | 1s budget tight |
| H9 | **Topology-bound seeds 별도 분석** | 17 topology-bound seeds 의 cap 위치 visualize → 진짜 unreachable 인지 확인. 일부 가능하면 specific algorithm. | 측정 only | 분석 시간 |

### Submission integration (Path 2 — pm47 plan)

| # | Hypothesis | Idea | LOC | Expected |
|---|---|---|---|---|
| P2-narrow | **CAPX cap-eat algorithm 을 submission 에 fold-in (mode-switch)** | 20200492.py 의 ReflexTunedAgent 안에 cap-mode branch 추가. score < threshold 일 때 CAPX-style cap-eat. | ~200 | submission 의 cap-eat 42% → 60-70% 가능 (CAPX 79% transfer) |

### CEM re-evolution (Path 4 — pm48 plan)

| # | Hypothesis | Idea | Time |
|---|---|---|---|
| P4-A1-rev | **CEM re-evolve against A1 family** | submission win 20-30% on A1_D13/D1 → CEM evolution 으로 A1 family 이기는 weights 진화. fitness function = vs A1 family win rate. | 2-3 sessions, 큰 sts compute |

### Report axis

| # | Item |
|---|---|
| R1 | LaTeX report draft (Methods §3 = pm46 v2 CAPX research probe + failure-mode 분석). 60pt 비중. |
| R2 | Slides 5-10p preparation. |
| R3 | docs/AI_USAGE.md update. |

---

## 5. Recommended sequencing for next session

ROI / time 관점:

**Phase 1 (~30분)**: Tier-2 H5 (oscillation detector). 가장 작은 LOC, 가장
direct (Pattern A 78% 의 fail).

**Phase 2 (~30분)**: Tier-2 H6 (path-cell hysteresis). 같은 Pattern A direct,
다른 mechanism. H5 와 결합 가능.

**Phase 3 (~10분)**: H8 (time-budget forced commit). 게임 끝 가까이 risky
commit.

**Phase 4 (~10분)**: H5+H6+H8 결합 sts dispatch (170 game).

**Phase 5 (decision)**: 결과 보고 다음 path 결정:
- **80% 달성** → P2-narrow (submission integration) 로 ROI maximize
- **80% 미달** → H7 (alternative survival) 또는 H2 (multi-step lookahead)
- **모두 negative** → P2-narrow 또는 R1 (report)

**병행**: H9 (topology-bound seeds visualize) — 17 unsolvable seeds 의
cap/spawn map 시각화. visual 검증으로 "정말 unsolvable" 가설 확정 또는
새 mechanism 발견.

**Long-term (별도 plan, pm48+)**: P4-A1-rev (CEM re-evolution).

---

## 6. Files (이번 세션 산출물)

### Code
- `minicontest/zoo_reflex_rc_tempo_capx_distract.py` — H3 wrapper (~120 LOC)
- `minicontest/zoo_reflex_rc_tempo_capx.py` — H1 env knob 추가 + def_recent_visits state

### Data
- `experiments/results/pm47_h3/h3_smoke.csv` — H3 25 game
- `experiments/results/pm47_h3/logs/` — H3 game logs
- `experiments/results/pm47_h1/h1_smoke.csv` — H1 25 game
- `experiments/results/pm47_h1/logs/` — H1 game logs

### Wiki
- 이 wiki: `.omc/wiki/pm47-h3-h1-attempts-results.md`
- 분석 baseline: `.omc/wiki/pm47-capx-failure-conditions-algorithmic.md`
- 이전 결과: `.omc/wiki/pm47-submission-cap-eat-comparison.md`
- 이전 결과: `.omc/wiki/pm46-v2-failure-mode-deep-analysis.md`

---

## 7. Open question (다음 세션 결정 필요)

1. 80% 가 진짜 hard target 인가? CAPX baseline 79% 이미 가까움. submission
   42% 가 진짜 lift target 일 수도.
2. 17/30 topology-bound 가 진짜 unsolvable? H9 visualization 으로 검증 필요.
3. Tier-2 H5/H6/H8 sequential 시도 후 80% 도달 못 하면 어디로?
   - P2-narrow (submission integration) — 큰 작업, ROI 가장 큼
   - P4-A1-rev (CEM re-evolution) — 더 큰 작업, 별도 plan
   - R1 (report) — 60pt 안전 확보

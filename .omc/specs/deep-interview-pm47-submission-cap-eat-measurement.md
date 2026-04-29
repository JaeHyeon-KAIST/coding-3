# Deep Interview Spec: pm47 Phase 0.5 — Submission cap-eat-alive measurement

## Metadata
- Interview ID: pm47-cap-eat-2026-04-29
- Rounds: 2
- Final Ambiguity Score: 14.5%
- Type: brownfield (CAPX detection logic + 20200492.py 모두 존재)
- Generated: 2026-04-29
- Threshold: 20%
- Status: PASSED

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|---|---|---|---|
| Goal Clarity | 0.90 | 40% | 0.36 |
| Constraint Clarity | 0.80 | 30% | 0.24 |
| Success Criteria | 0.85 | 30% | 0.255 |
| **Total Clarity** | | | **0.855** |
| **Ambiguity** | | | **14.5%** |

## Goal

Submission `20200492.py` 의 **capsule 도달 능력**을 17-defender × N-seed
matrix 로 측정. CAPX 와 동일한 metric (`eat_alive` / `eat_died` /
`died_pre_eat` / `no_eat_alive`) 으로 직접 비교. 결과 데이터를 후속
**다양한 improvement mechanism (CEM weight re-evolution, code edit,
new agent design 등 모두 가능)** 의사 결정 input 으로 사용.

## Constraints

- **Post-cap 행동 (food return, scoring, deposit-28, 1200-tick win
  evaluation) 은 관심 영역 아님** — capsule 도달까지만 측정.
- **Submission 코드 (`20200492.py`) 자체 변경 금지** — wrapper class
  가 import + subclass 만. submission 행동 100% 동일.
- **Mechanism choice 미고정** — measurement 가 모든 후속 mechanism 을
  지원해야 함 (CEM fitness function 으로도, code edit 비교 baseline
  으로도, new agent 비교 reference 로도).
- numpy/pandas only, no multithreading, 1s/turn budget, 1200-tick game cap.
- 17-defender zoo (pm46 v2 inventory) 동일 사용 — CAPX 와 paired
  비교 가능.

## Non-Goals (explicit exclusion)

- Cap 먹은 후 행동 측정 (return, deposit, scared-window food).
- Win/loss/score metric (이미 pm47 Phase 0 에서 17×10 측정 완료).
- CAPX 통합 결정 (이번 측정 결과 본 후 별도 결정).
- Submission 알고리즘 변경 (이번 세션은 측정만).
- 새 attacker design.

## Acceptance Criteria

- [ ] Wrapper class `submission_capsule_logger.py` 작성, `20200492.py`
      의 `ReflexTunedAgent` 를 import + subclass + cap-detection 추가.
- [ ] Wrapper 가 매 tick `prev_caps - current_caps` 검출 → `[SUBM_CAP_EATEN]
      tick=T cap=(x,y) agent_idx=I` print.
- [ ] Wrapper 가 A 의 사망 검출 → `[SUBM_A_DIED] tick=T pos=(x,y)
      agent_idx=I` print (CAPX 의 `_check_a_died` 와 동일 logic).
- [ ] Mac smoke (5 weak defender × 5 seed = 25 game, ~3분) — wrapper
      가 정상 print 확인 + submission 행동이 baseline 과 100% 동일 확인
      (game 결과 score 가 동일).
- [ ] sts dispatch (17 defender × 10 seed = 170 game, ~10분 wall) —
      pm47_phase0_capx_metric_baseline.sh wrapper 사용.
- [ ] Output CSV: per-defender / per-seed / outcome = (eat_alive /
      eat_died / died_pre_eat / no_eat_alive) + first_eat_tick +
      total_caps_eaten + a_died_count.
- [ ] Aggregate 분석 wiki: submission vs CAPX cap-eat-alive 직접 비교
      (per-defender × seed pairing).

## Assumptions Exposed & Resolved

| Assumption | Challenge | Resolution |
|---|---|---|
| 측정만으로 충분한가? | "어떤 결정에 쓸 거?" 질문 | 다양한 mechanism (CEM/code/new agent) 다 지원하게 풍부한 metric. |
| CAPX 의 cap-detection logic 그대로 쓰나? | "어떤 metric?" | 그대로 (`_emit_cap_eaten_if_decremented`). 단 wrapper 가 ABS module import 안 함 (independent). |
| Sample size n=10 충분? | n=10 의 ±28pp variance | 측정 후 boundary defender 만 n=30 확장 (Codex staged 권고와 일관). |
| Wrapper 가 submission 행동 변경하나? | "100% 같음 보장?" | subclass + super() 호출. registerInitialState/chooseAction 모두 forward. cap detection 만 추가. |
| post-cap 측정 필요? | 사용자 명시 | NO. 명확히 out-of-scope. |

## Technical Context (brownfield findings)

- **CAPX 의 cap-detection logic** (`zoo_reflex_rc_tempo_capx.py:435-470`):
  ```python
  prev_caps = set(gameState.getBlueCapsules())  # Red attacker
  on chooseAction entry:
      current_caps = set(gameState.getBlueCapsules())
      eaten = prev_caps - current_caps
      for cap in eaten:
          # proximity check + emit [CAPX_CAP_EATEN]
      prev_caps = current_caps
  ```
- **CAPX 의 death detection** (`_check_a_died`): A 의 position 이
  spawn (1,2) 으로 jump 하면 사망 (respawn).
- **Submission `20200492.py`** (1500 LOC):
  - `ReflexTunedAgent(CoreCaptureAgent)` line 1146
  - `createTeam(firstIndex, secondIndex, isRed, first='ReflexTunedAgent', second='ReflexTunedAgent')` line 1118
  - 두 agent 모두 같은 attacker (offensive 만, no dedicated defender)
- **Wrapper 가 import 할 것** (오직):
  - `20200492.py` 의 `ReflexTunedAgent` (importlib 우회 — 파일이름 숫자 시작)
- **Wrapper 가 import 안 할 것**:
  - `zoo_reflex_rc_tempo_abs` (CAPX 의 import whitelist 와 격리)
  - `zoo_reflex_rc_tempo_capx` (cap-detection logic 은 wrapper 안에서 직접 구현)

## Ontology (Key Entities)

| Entity | Type | Fields | Relationships |
|---|---|---|---|
| **Wrapper** | core | (subclasses ReflexTunedAgent) | wraps Submission, emits Cap-Event |
| Submission (`20200492.py`) | external system | ReflexTunedAgent, createTeam, A1 weights | wrapped by Wrapper |
| Defender (zoo) | external system | 17 instances (capsule, tuned, ...) | opponent of Wrapper |
| Cap-Event | core | `[SUBM_CAP_EATEN]`, `[SUBM_A_DIED]` markers | emitted by Wrapper |
| Outcome | core | eat_alive / eat_died / died_pre_eat / no_eat_alive | derived from Cap-Event sequence |
| Matrix CSV | output | defender, seed, outcome, first_eat_tick, total_caps, a_died | aggregates Outcome per (defender, seed) |

## Ontology Convergence

| Round | Entity Count | New | Changed | Stable | Stability |
|---|---|---|---|---|---|
| 1 | 5 (Wrapper, Submission, Defender, Cap-Event, Outcome) | 5 | - | - | N/A |
| 2 | 6 (+Matrix CSV) | 1 | 0 | 5 | 83% |

Convergence 양호 — round 2 에서 1개만 추가, 나머지 stable.

## Implementation Plan (개요 — 별도 spec 아님)

1. `minicontest/submission_capsule_logger.py` 작성 (~50 LOC)
   - `importlib.util.spec_from_file_location` 으로 `20200492.py` load
   - `ReflexTunedAgent` subclass = `CapsuleLoggerAgent`
   - `registerInitialState` override: super() + init `_prev_caps`, `_spawn`
   - `chooseAction` override: cap detection + death detection + super().chooseAction(gameState)
   - `createTeam` 새로 정의 (두 `CapsuleLoggerAgent`)
2. Mac smoke 1 game (RANDOM1 vs baseline) — `[SUBM_CAP_EATEN]` emit 확인
   + 결과 score = submission baseline 과 동일 확인 (행동 변경 없음 verify)
3. Wrapper script `experiments/rc_tempo/pm47_phase0_capx_metric_baseline.sh`
   - 기존 `pm47_phase0_submission_baseline.sh` fork
   - agent: `submission_capsule_logger`
   - parser: `[SUBM_CAP_EATEN]` + `[SUBM_A_DIED]` count
   - outcome 분류: eat_alive / eat_died / died_pre_eat / no_eat_alive
4. Mac smoke 5 def × 5 seed = 25 game (~3분)
5. sts dispatch 17 × 10 = 170 game (~10분)
6. 분석 wiki: submission vs CAPX cap-eat-alive 직접 비교

## Interview Transcript

<details>
<summary>Full Q&A (2 rounds)</summary>

### Round 1
**Q:** submission 의 cap-eat % 측정 결과 나온 후 다음 어떤 결정 하실 예정?
**A:** "성능을 최대한 높일거야. 필을 죽지 않고 먹는게 중요. 필을 잘 먹도록
학습하자는 거임. 학습이 맞나..?"
**Resolved**: cap_eat_alive 가 핵심 metric, "학습" 은 mechanism 후보 중 하나.
**Ambiguity:** 85% → 25.5%

### Round 2
**Q:** 측정 후 cap-eat 능력 향상 mechanism 어느 마음?
**A:** "어떤 방식이든 상관 없어... 여러 방식다 해서... 최대한 성능 높이는게 목적임"
**Resolved**: mechanism 미고정. metric 풍부히 측정 → 후속 결정에 input.
**Ambiguity:** 25.5% → 14.5%

</details>

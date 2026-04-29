# SESSION_RESUME — 5-minute onboarding for any new Claude or human session

**Last updated:** 2026-04-29 — **pm47 측정 완료 + H3/H1 smoke negative. CAPX baseline 79% / submission 42% cap-eat-alive / submission 51.8% win-rate. Tier-1 (B distraction, defender history) 둘 다 fail. 다음 세션: Tier-2 H5/H6/H8 + H9 topology viz + Path 2 submission integration. 사용자 목표 80%+ eat_alive.**

---

## ⭐⭐⭐ 다음 세션 START HERE — pm47 여러 방향 sequential (2026-04-29)

**사용자 명시 목표**: cap_eat_alive **80%+** (CAPX baseline 79% 초과). 여러
방향 다 시도. 다음 세션에서 sequentially 진행.

**진행 순서 (ROI 기준)**:

### Phase 1 (Algorithm side — Tier-2 surgical, ~30분 each)

1. **H5 — Oscillation detector + force commit** (~20 LOC)
   - A position last 8 ticks 가 같은 2-3 cells cycle 검출 → force commit on
     chosen target (gate 무시)
   - Pattern A 78% 의 fail direct cure 가설
   - env knob: `CAPX_OSC_DETECT=1` (default 0)
   - file: `zoo_reflex_rc_tempo_capx.py` 의 `_choose_action_impl` 안에 추가
   - smoke 5×5 → sts 17×10

2. **H6 — Path-cell hysteresis** (~20 LOC)
   - 이전 path first 5 cells 와 80% overlap 새 path → "same path" → gate
     threshold -2 적용 (committed_target 아니어도)
   - Pattern A 다른 mechanism cure
   - env knob: `CAPX_PATH_HYSTERESIS=1` (default 0)
   - H5 와 결합 가능

3. **H8 — Time-budget forced commit** (~10 LOC)
   - tick > 800 (game 끝 1/3) 인데 cap 못 먹음 → margin threshold -3 (suicide
     risk 일부 허용)
   - Late-game commit lift
   - env knob: `CAPX_LATE_GAME_FORCE=1` (default 0)

4. **결합 sts dispatch** (H5+H6+H8 모두 ON, 17×10, ~10분 sts)

### Phase 2 (Decision tree)

- **80% 달성**: Path 2 (submission integration) 로 ROI maximize
- **80% 미달**: H7 (alternative survival) 또는 H2 (multi-step lookahead)
- **모두 negative**: P2-narrow 또는 LaTeX report

### Phase 3 (병행 분석)

- **H9 — Topology-bound seeds visualization** (측정 only)
  - 17 topology-bound seeds (3,4,5,6,11,13,14,15,22,24,25,26,27,28,29,30 등)
    의 cap 위치 + spawn + walls visualize
  - "정말 unsolvable" 가설 확정 또는 specific algorithm 발견 가능

### Long-term (별도 plan)

- **Path 2 (pm47 narrow integration)**: CAPX cap-eat algorithm 을
  20200492.py 에 fold-in (mode-switch). submission 의 cap-eat 42% → 60-70%
  가능 가설.
- **Path 4 (pm48 CEM re-evolution)**: A1 family 이기는 weights CEM 진화.
  큰 sts compute.

---

## 다음 세션 진입 시 읽기 순서

1. **`.omc/wiki/pm47-h3-h1-attempts-results.md`** ← 가장 최신 (이번 세션 종합)
2. **`.omc/wiki/pm47-capx-failure-conditions-algorithmic.md`** ← Tier 후보 + failure mode
3. **`.omc/wiki/pm47-submission-cap-eat-comparison.md`** ← submission baseline (42% cap-eat-alive)
4. **`.omc/wiki/pm47-submission-cap-eat-comparison.md`** + **`.omc/wiki/pm46-v2-failure-mode-deep-analysis.md`**
5. `minicontest/zoo_reflex_rc_tempo_capx.py` ← 코드 (H1 env knob 이미 추가, ablation-friendly)

---

## (Historical) ⭐⭐ 이전 START HERE — CCG Phase A 결과 회수 + 분석 (2026-04-29)

**Goal**: sts 서버에서 진행 중인 phase A ablation matrix (4 variants × 90 weak-defender games = 360 games, ~3h) 결과 회수 → 분석 → 다음 액션 (S2 scope-narrow 재시도? S1+S3 default → 17×30 full matrix? pm47 통합 시작?).

**상태 (이전 세션 종료 시점)**:
- CCG 자문 완료: Codex + Gemini + Claude lead 종합. S-tier 3 fix 권고.
- 코딩 완료: `minicontest/zoo_reflex_rc_tempo_capx.py` 에 S1/S2/S3 모두 env knob 으로 분리. 합 ~30 LOC.
- **S2 broken** (`CAPX_ASYMMETRIC_THREAT=1` smoke RANDOM1 capsule 0 caps + 7 deaths). **Default OFF**. 원인: `_gate.margin_at` 에서 own-side cell margin=999 → gate 무조건 trigger → border-rush.
- S1+S3 default ON. 4 spot-check 게임 결과: aggressive RANDOM20 suicide → eat_alive (cure ⭐), tuned RANDOM7 1death → 0deaths (개선), 나머지 2 baseline 동일.
- Phase A wrapper: `experiments/rc_tempo/pm46_v2_ccg_phase_a_ablation.sh` (4 variants × 3 weak × 30 seeds = 360 games)
- Server dispatch: ssh jdl_wsl + tmux work 안에서 launch.

**다음 세션 첫 액션**:
1. `ssh jdl_wsl` → `tmux capture-pane -t work -p | tail -50` 로 진척 확인.
2. `ls -la <project>/experiments/results/pm46_v2/ccg_phaseA/*.csv` — 4 csv 모두 있는지.
3. 결과 analysis: 각 variant 별 weak-defender × seed 결과 → eat_alive %, no_eat_died % 비교.
4. **결정 트리**:
   - **S1+S3 가 baseline 대비 명확한 lift** (예: +10pp 이상) → S1+S3 으로 17×30 full matrix 진행 (sts 서버, ~5h) → 17/17 maintain 확인 → pm47 통합 시작.
   - **S1 만 lift, S3 neutral 또는 negative** → S1 default 만 keep, S3 deeper 분석.
   - **둘 다 marginal** (±5pp) → S2 scope-narrow 재시도 (gate margin 빼고 edge_cost+_p_survive 만). 또는 A-tier (Codex Top 1: defender-weighted safest drift) 시도.
   - **S2 별도**: scope-narrow patch 만들고 small smoke 부터 다시.

**핵심 파일** (다음 세션 진입 시):
1. `.omc/wiki/pm46-v2-ccg-improvement-consultation.md` — 권위 wiki. §7.1/§7.2 가 새 implementation 결과.
2. `.omc/research/pm46-v2-ccg/{codex,gemini}-summary.md` — advisor 요약.
3. `.omc/artifacts/ask/{codex,gemini}-capx-improvement-2026-04-29T*.md` — raw 응답.
4. `experiments/rc_tempo/pm46_v2_ccg_phase_a_ablation.sh` — wrapper (sts 에서 돌고 있음).
5. `minicontest/zoo_reflex_rc_tempo_capx.py` — 새 코드 (3 env knob 추가).
6. `experiments/results/pm46_v2/ccg_phaseA/` — 결과 csv 들 (sts 에서 회수).

**Out-of-scope (이전 세션 유지)**:
- 제출 코드 (`20200492.py`, `your_best.py`) 수정 — pm47 별도 결정.
- ABS attacker — 별도 트랙.
- S2 의 wide-scope 적용 — broken 입증, 재시도 시 scope narrowing 필수.

---

## (Historical, 2026-04-29) CCG 자문 + S1+S3 implementation

(위의 다음 세션 START HERE 가 가장 최신. 아래는 컨텍스트 보존.)

CCG 워커 spawn 시도 (oh-my-claudecode:executor team 모드) → **워커 즉시 죽음** (tmux pane %47/%48/%49 사라짐, 원인 미상; 한국어 path 또는 sonnet routing 추정). Plan B 발동: lead 직접 진행:
- omc ask codex / gemini 백그라운드 호출 → 결과 자동 .omc/artifacts/ask/ 저장
- lead 가 직접 weak-defender CSV 분석 (capsule+tuned outcome identical 발견 = effective n=60)
- 종합 wiki 작성

---

## ⭐⭐ (Historical) 이전 START HERE — CCG 외부 자문 (CAPX 알고리즘 개선 여지)

**Goal**: 현재 CAPX 알고리즘 (`zoo_reflex_rc_tempo_capx.py`, 665줄)에 대해 **Claude (executor) + Codex (CLI) + Gemini (CLI) 3 advisor 다 받아서 개선 여지 분석**.

**왜 지금**: pm46 v2 17/17 PERFECT 끝났지만, 일부 defender (zoo_reflex_capsule 40%, zoo_reflex_tuned 40%, zoo_reflex_aggressive 50%) 는 CAPX도 비교적 약함. 또 알고리즘에는 code-reviewer 가 발견한 **1 HIGH (mitigated) + 4 MED + 4 LOW** 이슈도 있음. 외부 visible 자문으로 design refinement 방향 잡기.

**컨텍스트 핸드오프 (이 세션 종료 시점)**:
- Phase 0/1/2/2.5/3/4 + Recovery 완료.
- 모든 코드 + wiki + commit 정리됨.
- ultrawork mode 종료 (state cleared).
- 직전 user 요청: **"지금 로직에 대해서 개선 여지 있는지, /team 을 통해 진행. 클로드 코덱스 제미나이 3개 다 이용"** → 컨텍스트 문제로 다음 세션으로 미룸.

**다음 세션 워크플로우 (사용자 명시)**:
1. `/team` 으로 Claude 에이전트 (executor + analyst) 다중 spawn
2. `codex` CLI 로 OpenAI Codex 자문 받기 (`omc ask codex` 패턴 — `.omc/artifacts/ask/` 에 응답 저장)
3. `gemini` CLI 로 Google Gemini 자문 받기 (`/Users/jaehyeon/.nvm/versions/node/v20.11.0/bin/gemini`)
4. 3 자문 종합 → 개선 후보 ranked list → 사용자에게 결정 회부

**세 advisor 에 동일 prompt 주입 (예시)**:
```
This is the CAPX (Capsule-only experimental Attacker) Pacman agent.
Goal: A reaches >=1 capsule alive. 17 defender × 30 seed = 510 game
matrix shows 79% eat_alive (vs ABS 5%, 17/17 strict improvement).

But 3 defenders are weak: zoo_reflex_capsule (40%), zoo_reflex_tuned
(40%), zoo_reflex_aggressive (50%). Code review found 1 HIGH (mitigated)
+ 4 MED + 4 LOW issues queued.

Algorithm files:
- minicontest/zoo_reflex_rc_tempo_capx.py (665 lines)
- .omc/plans/omc-pm46-v2-capsule-only-attacker.md (full spec, ralplan APPROVED)
- .omc/wiki/pm46-v2-FINAL-recovery-17-of-17.md (final results)
- .omc/wiki/pm46-v2-capx-code-review-phase4-tuning.md (review + tuning grid)

QUESTION: What are the highest-ROI algorithmic improvements? Rank by
expected eat_alive lift on the 3 weak defenders, with the constraint of
no submission code modification (CAPX is research probe).
```

**CCG 종합 후 산출물**: `.omc/wiki/pm46-v2-ccg-improvement-consultation.md` — 3 advisor 응답 요약 + 권고 ranked list + 구현 우선순위.

---

## ⏪ 이전 세션 (2026-04-29) 요약

### Phase 1 — CAPX agent (greenfield, 665줄)
- 4 helper whitelist만 import (no `_ABS_TEAM` 접근).
- p95 chooseAction wall = 67.6ms (limit 150ms; 2.2× headroom).

### 알고리즘 핵심 finding
Plan §5.3 spec 의 full-path margin gate → 너무 엄격해서 default knob 으로 0/9 smoke fail. **`CAPX_GATE_HORIZON=8` 도입** (next 8 cells만 평가, far-future cell은 도달 시 재평가). 이게 CAPX viability 의 핵심 fix.

### Phase 3 + Recovery
- 510-game CAPX matrix (Mac, kill+resume 으로 hybrid_mcts 90s timeout 우회)
- 510-game ABS-baseline (sts, corrected `[ABS_CAP_EATEN]` detector)
- Recovery sweep: zoo_belief (helper module not agent) → zoo_reflex_A1_T5 교체. zoo_hybrid_mcts_reflex → `ZOO_MCTS_MOVE_BUDGET=0.05` env + 240s timeout.

### Phase 4 최종 결과
- aggregate cap_eat_alive: CAPX **79.0%** vs ABS ~5% (+71pp, 15× 개선)
- aggregate died_pre_eat: CAPX **1.8%** vs ABS ~10%
- per-defender died_pre_eat max: 6.7% (limit < 80%)
- **strict improvement: 17/17 PERFECT** (limit ≥ 12)

### Commit chain
- `b315c4a` Phase 0/1/2 evidence
- `e52a03b` doc + partial Phase 4
- `d9d48e8` 15/17 strict (initial complete)
- `1329170` **17/17 PERFECT (recovery final)** ← 최종

### 부수 산출물
- `.omc/plans/omc-pm47-capx-to-submission-integration-DRAFT.md` — pm47 통합 옵션 A/B/C
- `.omc/wiki/pm46-v2-capx-code-review-phase4-tuning.md` — code-reviewer 자문 + Phase 4 24-cell tuning grid
- `experiments/rc_tempo/pm46_v2_capx_knob_sweep.sh` — knob sweep launcher (실행 안 함, 다음 세션 후보)

읽기 순서 (다음 세션 진입 시):
1. **`.omc/wiki/pm46-v2-FINAL-recovery-17-of-17.md`** — 최종 decision wiki (17/17 결과)
2. **`.omc/wiki/pm46-v2-capx-code-review-phase4-tuning.md`** — code review + Phase 4 tuning grid (CCG 자문 baseline)
3. **`minicontest/zoo_reflex_rc_tempo_capx.py`** — CAPX agent (665줄)
4. **`.omc/plans/omc-pm46-v2-capsule-only-attacker.md`** — 알고리즘 spec (§5)
5. **`.omc/plans/omc-pm47-capx-to-submission-integration-DRAFT.md`** — 후속 통합 plan draft
6. **`.omc/artifacts/ask/`** — 과거 codex 자문 logs (참고)

**Out-of-scope (CCG 자문 세션에서도 유지)**:
- 제출 코드 (`20200492.py`, `your_best.py`) 수정 — CAPX는 research probe.
- ABS attacker 코드 변경 — CAPX 와 분리 보존.
- pm47 통합 결정 — CCG 자문 후 별도 세션.

---

## ⭐ NEXT SESSION — START HERE: pm46 v2 CAPX 즉시 실행 (2026-04-29)

**목적 (사용자 명시 reframing)**: 팩맨 게임의 다른 모든 측면 (food harvest, scoring, win condition, scared-window food, return-home, deposit-28) **무시**. 단일 문제만:

> **A 공격 에이전트가 *죽지 않고* capsule 1개라도 도착하는 로직 개발.**

핵심 통찰:
- 수비는 capsule이 우리 전략 핵심인 줄 모름 — 일반 invader patrol 메커니즘.
- 한 path 막혀도 우회 path 로 capsule 도달 가능.
- 기존 ABS의 safety gate (`_a_first_cap_survival_test*` margin check) 가 직선 BFS path만 평가 → 우회 무시 → reject 누적으로 *cap 못 먹는 척*.

**해결 방향**: 새 single-purpose attacker `zoo_reflex_rc_tempo_capx.py` (greenfield). 기존 ABS 코드 수정 X.

### Phase 분할 (plan §6)

| Phase | 위치 | wall | 산출물 |
|---|---|---|---|
| **0 — ABS re-baseline** | sts 서버 (tmux) | 4-5h | `experiments/results/pm46_v2/abs_baseline_corrected.csv` (510 game with corrected `len(getCapsules())` detector) |
| **1 — CAPX prototype** | Mac (병렬, 코드 작성) | 3-4h | `minicontest/zoo_reflex_rc_tempo_capx.py` + solo wrapper |
| **2 — Smoke (3×3)** | Mac | ~5min | smoke csv |
| **2.5 — Tier-screening (17×5)** | Mac 또는 sts | ~45min | screening csv (≥30% gate) |
| **3 — Full matrix (17×30)** | sts (tmux) | 4-5h | `capx_matrix.csv` |
| **4 — Analysis** | Mac | ~30min | 비교 wiki + 결정 |

### 즉시 시작 액션

**Phase 0 setup (sts)**:
1. ABS 코드에 `[ABS_CAP_EATEN]` shim 추가 — `zoo_reflex_rc_tempo_abs_solo.py` 의 ReflexRCTempoAbsAgent wrapper subclass 또는 `_track_a_first_cap_reach` 옆에 detector. ~15 LOC.
2. wrapper script (`pm46_v2_a_solo_matrix.sh`) parser update.
3. git commit + push, ssh jdl_wsl, git pull.
4. `tmux send-keys -t work` 안에서 510 game launch with `2>&1 | tee logs/abs-baseline-$(date +%F-%H%M).log`.

**Phase 1 (Mac, 동시 진행)**:
1. plan §5.1 ~ §5.5 따라 `zoo_reflex_rc_tempo_capx.py` 작성.
2. plan §4.1 G1 import whitelist 만 (`_grid_bfs_distance`, `_bfs_grid_path`, `_dir_step`, `_bfs_first_step_to`).
3. solo wrapper `zoo_reflex_rc_tempo_capx_solo.py` 작성 (StubB + createTeam).
4. Phase 1 AC: p95 chooseAction wall-time < 150ms over 200+ ticks (auto-lower CAPX_ASTAR_NODE_CAP if violated).

### 핵심 algorithm 요약 (plan §5)

- **Defender-aware A\*** (§5.2): edge cost = base + threat_penalty (`defender_dist_map[d][cell]` per-tick precompute, ~7ms × visible def). detour budget `CAPX_DETOUR_BUDGET=4` (hard cap 8). node cap `CAPX_ASTAR_NODE_CAP=2000` with auto-lower fallback.
- **Survival-aware gate** (§5.3): margin threshold relaxed (`CAPX_MIN_MARGIN=0` vs ABS=1), hysteresis (commit 후 margin -2 까지 hold), **hard abandon override** (`CAPX_HARD_ABANDON_MARGIN=-1`: next-3-step margin < -1 면 hysteresis 무시 abandon).
- **Survival-weighted cap rank** (§5.4): `score = -P_survive(astar_path)`; tied → bfs_dist 작은 쪽. **Floor**: max P_survive < `CAPX_MIN_PSURVIVE=0.2` 면 distance-only rank fallback.
- **Cap detect** (§5.1): `prev_caps = set(gameState.getBlueCapsules())` (Red attacker 가정), Red turn 후 decrement → `[CAPX_CAP_EATEN] tick=T cap=(x,y) a_pos=... eater_idx=I` emit.

### Acceptance bars (plan §3.3)

- Aggregate: `cap_eat_alive ≥ 50% AND died_pre_eat ≤ 60%` (510 game).
- **Per-defender override (HARD RULE)**: ANY defender 가 `died_pre_eat ≥ 80%` 면 FAIL regardless of aggregate.
- Per-tier: A ≥30%, B ≥60%, C ≥90%, D ≥50% cap_eat_alive.
- Strict improvement on ≥12 of 17 defenders vs Phase 0 ABS baseline.

### 함수 책임 / 트랙 분리

- omc 영역: 새 `capx*.py` 파일 (greenfield, no ABS 수정). plan §10 명시.
- omx 영역 (`_choose_b_prep_candidate`, `_gate_first_cap_trigger_action`, `_actual_first_cap_trigger_compat`): 안 건드림 (greenfield 라 어차피 access 안 함).
- 제출 코드 (`your_*.py`, `20200492.py`, `myTeam.py`): 안 건드림. CAPX = research probe, not submission.
- `docs/AI_USAGE.md`: discretionary (plan §4.1 G9 — CAPX 비제출).

### Out-of-scope (plan §10)

food harvest, scoring, deposit-28, return-home, scared-window food, cap2-after-cap1 chain, B coordination, opponent classification, retrograde resurrection (pm45 closed), CAPX→submission integration (pm47+ 별도 plan).

---

## (Historical, 2026-04-29) pm46 v1 (mode-commit + B prep) 폐기

**상태**: 폐기. 사용자 의도와 안 맞음.
- v1 plan: ABS_HOME_PRETRIGGER (B prep margin) 도입. R8 회귀 풀 의도.
- v1 Phase 0 trace 결과: PRETRIGGER flag 자체가 dead-code under default `ABS_FIRST_CAP_TRIGGER=1` (omx-pm44 도입). byte-identical trace on R6/R8.
- 추가 진단 (`q-answer.md`): R8 회귀 진짜 원인 = abstract beam ghost-blindness + razor-thin slack. ABS_HOME_PRETRIGGER 안 풀음.
- 사용자 reframing: "ABS chain 무시. A solo capsule 먹기만." → pm46 v2 CAPX 시작.

**관련 wiki**:
- `.omc/wiki/2026-04-29-pm46-phase-0-pretrigger-flag-is-dead-code-regression-hypothesis-.md` — pm46 v1 Phase 0 결과 (classification c).
- `q-answer.md` — sequel 진단 (B prep / safety gate / R8 mechanism).

(구) `.omc/EXPERIMENT_ENV.md` 는 pm45 시점 자료. 여전히 measure metric / emit 메커니즘 / sts 사용법 reference 로 유효하지만 다음 세션 진입 우선순위에서는 빠짐.

---

## ⭐ NEXT SESSION — START HERE: omc-pm46 mode-commit handoff (2026-04-29)

**현재 상태**: pm45 종결. retrograde feature 는 `ABS_USE_RETROGRADE=0` default + dead-code 주석. 다음 세션은 **pre-pill mode commit + B prep** 작업.

**Reframing (사용자 합의 사항)**:
- 현재 코드는 "2-agent 공격이 항상 최적"을 가정하고, 안 맞으면 reactive fallback. 이건 reactive design.
- Game 시작에 **mode commit** ("A+B" vs "A_only"). 한 번 commit 하면 모든 행동 (B prep 포함) 일관.
- `b_start_blocked` 는 post-pill recovery 문제가 아님. **pre-pill 에 mode commit 누락이 진짜 원인**.

**책임 분담**:
- **omc (이 트랙, 시간축 pre-pill)**:
  - `decide_plan_mode()` stub (항상 "A+B" 반환부터)
  - home-side B prep commit (midline 절대 안 넘음, ghost 상태 유지)
  - 미래의 진짜 decision logic (invader threat 등) — Phase 2+
- **omx (omx-pm47, post-pill strategy library)**:
  - A-only strategy 빌더 (B 수비 유지 가정)
  - 기존 S1-S4 (A+B) + 새 A-only 카테고리에 mode 태그
  - 인터페이스: strategy 객체 `mode='A+B'` / `mode='A_only'`

**다음 세션 첫 액션 — Phase 0 (PRETRIGGER 회귀 진단, ~30분, Mac)**:

pm36 era 의 `ABS_PRETRIGGER` 가 RANDOM6 + RANDOM8 (-28 score) 에서 회귀했는데 **원인 trace 안 됨**. 사용자 가설: historical PRETRIGGER 가 midline 넘어서 B 가 Pacman 으로 잡힌 가능성. home-side only 변형은 안전할 수 있음.

```bash
cd minicontest

# PRETRIGGER ON, 회귀 후보 두 seed
ABS_PRETRIGGER=1 ABS_FIRST_CAP_TRACE=1 \
  ../.venv/bin/python capture.py \
  -r zoo_reflex_rc_tempo_abs -b baseline -l RANDOM6 -n 1 -q \
  > /tmp/pm46_phase0_random6_pretrig.log 2>&1

ABS_PRETRIGGER=1 ABS_FIRST_CAP_TRACE=1 \
  ../.venv/bin/python capture.py \
  -r zoo_reflex_rc_tempo_abs -b baseline -l RANDOM8 -n 1 -q \
  > /tmp/pm46_phase0_random8_pretrig.log 2>&1

# OFF baseline 비교
ABS_PRETRIGGER=0 ABS_FIRST_CAP_TRACE=1 \
  ../.venv/bin/python capture.py -r zoo_reflex_rc_tempo_abs -b baseline -l RANDOM6 -n 1 -q \
  > /tmp/pm46_phase0_random6_off.log 2>&1

ABS_PRETRIGGER=0 ABS_FIRST_CAP_TRACE=1 \
  ../.venv/bin/python capture.py -r zoo_reflex_rc_tempo_abs -b baseline -l RANDOM8 -n 1 -q \
  > /tmp/pm46_phase0_random8_off.log 2>&1
```

**Note**: capture.py runs hardcoded 4-baseline loop (line 1054); only Game 1 of each log is canonical. Or substitute `experiments/rc_tempo/pm45_single_game.py` wrapper for clean single-game runs.

Trace 에서 확인:
- B 가 midline 넘었나? 언제?
- B 잡혔나? home-side / enemy-side?
- A 의 cap1 path 영향?
- 점수 timeline (회귀 시점)?

분류:
- (a) B 가 midline 넘어 잡힘 → home-only 변형 안전 → Phase 1 진행
- (b) B 가 home 에서 다른 부작용 (수비 빈자리 등) → home-only 도 unsafe
- (c) 다른 메커니즘 (defender 반응 변화 등)

**Phase 1** (조건부, (a) 확인 시):
- 새 flag: `ABS_HOME_PRETRIGGER` (default 0). pm36 의 `ABS_PRETRIGGER` 와 별개 — 절대 unsafe variant 재활성화 안 함.
- `decide_plan_mode()` stub 추가 (항상 "A+B" 반환, 인터페이스만 확립).
- "A+B" 결정 → B home-side prep 발동:
  - 이동 범위 강제: `x ≤ mid - 1` (적 영역 진입 절대 금지)
  - 타겟: 현 best strategy 의 `b_start`
  - cap1 먹히기 전까지 prep 계속
- 30-seed 검증 vs pm35 era 23W/3T/4L baseline.
- Acceptance: strict improvement on at least one of {wins, mean score, deposited food}, 회귀 없음, `compat=b_start_mismatch` 0 보존.

**Phase 2+** (future, omc-pm47+): omx-pm47 A-only strategy library 완성 대기 → 그 후 진짜 decision logic 구현 → stub 교체.

**함수 책임 충돌** (TRACK_SEPARATION § 6): 다음 함수들은 historical omx (pm44):
- `_choose_b_prep_candidate`
- `_gate_first_cap_trigger_action`
- `_actual_first_cap_trigger_compat`

협업 규칙: 시간축 우선 (pm46 가 omc), omx 에 plan 으로 통보 후 진행. omx-pm47 핸드오프에 인터페이스 (mode 태그) 이미 합의됨.

**Out-of-scope**: omx 영역 (post-pill replanner, A-only strategy builder), 2-def 게릴라 (시간축으로 omc 지만 별도 plan), retrograde 부활 (pm45 종결).

**관련 핵심 infra (pm45 에서 발견, 다음 세션도 사용)**:
- `experiments/rc_tempo/pm45_single_game.py` — capture.runGames() 직접 호출 wrapper. capture.py:1054 의 하드코딩 4-baseline loop 우회. **단일 게임 결정성 필요한 모든 작업에 사용 권장**.
- Mac vs sts agent 결정 다름 (md5 동일에도) — anytime beam CPU 속도 의존성. 동일 환경 안에서만 정량 비교.

---

## (Historical) 2026-04-29 pm45 진단 결과 (closed)

- pm41 retrograde 가 baseline 상대 marginal, **monster_rule_expert (강한 defender) 상대 net negative** 입증.
- sts Phase 0 (4 def × 8 seeds × 2 flag = 64 games): 0/3 strong defenders net non-negative → Phase 4 dead-code direct.
- Architect 의 structural h4 가설 (V table MIN-optimal vs rule-based defender mismatch) 확인.
- 결정 wiki: `.omc/wiki/2026-04-30-pm45-final-decision.md`.

## (Historical) 2026-04-28 pm44 — B-start mismatch handling (omx 책임, complete)

**현재 active 상태**: pm44 완료. `minicontest/zoo_reflex_rc_tempo_abs.py` 에서 scared-start 시점 B 실제 위치가 선택된 ABS strategy 의 `b_start` 가정과 어긋나는 `compat=b_start_mismatch` 문제를 막았다. (pm46 가 이 위에 mode commit 더함.)

---


## 📋 트랙 분리 정책 (2026-04-28)

이 프로젝트는 **`.omc` (Claude) + `.omx` (codex)** 두 트랙 **병렬 active**. 분리 = 각자 자기 surface 에만 글 적고, 코드는 함수 단위 분담.

- **omc 책임 코드**: `_a_first_cap_survival_test*`, `_retrograde_best_action_with_tiebreak`, `_track_a_first_cap_reach`, `_a_cap_test_action`, `_emit_a_cap_test_log` 의 retrograde 필드, `_build_once` 의 V build
- **omx 책임 코드**: `_select_strategy_at_scared_start`, `_choose_b_prep_candidate`, `_gate_first_cap_trigger_action`, `_actual_first_cap_trigger_compat`, post-pill 실행 경로
- **공유**: `_update_abs_postmortem`, `_classify_first_cap_roles`, `_ABS_TEAM` 키 (prefix 로 분리)

- **omc 사용 plan 번호**: pm22~pm35, pm41, **다음 omc-pm45+** 권장
- **omx 사용 plan 번호**: pm36~pm40, pm42~pm44, **다음 omx-pm46+** 권장
- pm41 번호 이미 충돌됨 (omc=retrograde / omx=post-pill). 이후 prefix 강제

- 자세한 정책: **`.omc/TRACK_SEPARATION.md`** (양쪽 surface 에 mirror)
- 2026-04-28 pm44 incident: codex pm44 handoff 가 `.omc/SESSION_RESUME.md` 에 잘못 적혀서 발생. 정책 문서로 재발 방지.

다음 세션은 **이 SESSION_RESUME (omc) 만 권위 source for omc track**. `.omx/SESSION_RESUME.md` 는 codex 자기 트랙 권위 source 로 따로 유지.

---

## (Historical) pm44 handoff block — superseded by omc-pm46 NEXT SESSION above

**상태**: pm44 (omx 작성) 완료. pm45 (omc) 도 종결. 이 블록은 historical reference 로만 보존. 다음 세션 진입점은 위의 "⭐ NEXT SESSION — START HERE: omc-pm46 mode-commit handoff" 블록.

**핵심 변경**:
- pre-trigger movement 를 default로 freeze하지 않음. RANDOM6 회귀가 확인되어 기본 전략에서 제외.
- scared-start 시 선택 strategy 가 `b_start_mismatch` 로 incompatible 하면, 실제 A/B 위치 기준으로 compatible strategy 를 rerank.
- compatible strategy 가 하나도 없으면 invalid ABS plan 을 강행하지 않고 `chosen=None`, `compat=b_start_blocked` 로 막은 뒤 rc82/scared fallback 로 넘김.
- `ABS_RERANK_ON_B_START_MISMATCH=1` 이 기본 ON 경로. `ABS_BLOCK_UNGATED_FIRST_CAP_FALLBACK` 은 존재하지만 default `0`.

**검증 완료**:
- `.venv/bin/python -m py_compile minicontest/zoo_reflex_rc_tempo_abs.py` ✅
- guard sweep: `RANDOM5 6 8 9 11 12 16 21 28`, `ABS_REACH_EXIT=0` 에서 `compat=b_start_mismatch` 0건 ✅
- seed 결과:
  - RANDOM5 `+13`, `b_start_blocked`
  - RANDOM6 `+20`, `ok`
  - RANDOM8 `-28`, `ok`
  - RANDOM9 `+21`, `ok`
  - RANDOM11 `+2`, `no_scared_start`
  - RANDOM12 `+14`, `ok`
  - RANDOM16 `-12`, `no_scared_start`
  - RANDOM21 `+9`, `ok`
  - RANDOM28 `-17`, `ok`

**다음 세션 첫 액션**:
1. `git status` 로 미커밋 변경 확인. 이 repo 는 unrelated dirty file 이 많으므로 절대 revert 하지 말 것.
2. `minicontest/zoo_reflex_rc_tempo_abs.py` 의 pm44 지점부터 읽기:
   - `_select_strategy_at_scared_start`
   - `_choose_b_prep_candidate`
   - `_gate_first_cap_trigger_action`
   - `_actual_first_cap_trigger_compat`
3. pm45는 바로 구현하지 말고, 먼저 `b_start_blocked` 와 `no_scared_start` seeds 를 분리해서 원인 확인:
   - `b_start_blocked`: plan 자체는 trigger 됐지만 실제 B 위치 기준 compatible strategy 없음.
   - `no_scared_start`: scared-window 진입 자체가 기대대로 시작되지 않음.
4. 우선 후보 seeds:
   - `b_start_blocked`: RANDOM5
   - `no_scared_start`: RANDOM11, RANDOM16
   - 점수 회귀/미회복 관찰: RANDOM8, RANDOM28
5. pm45 방향은 "mismatch 재발 방지"를 acceptance gate 로 유지한 채, blocked/no-start 케이스만 개선. pre-trigger freeze default ON 재시도는 RANDOM6 회귀 evidence 때문에 후순위.

**AI usage / 로그**:
- pm44 production edit 는 `docs/AI_USAGE.md` 에 기록 완료.
- session-log wiki: `.omc/wiki/2026-04-28-pm44-b-start-mismatch-handling.md`

---

## Historical pm41 handoff — server n=3 sweep + RANDOM5 regression 추적

**ralplan 상태**: **APPROVE** (3 iter, 2026-04-27). plan §13 (line 499~920) 에 amendment patchset + ADR 통합.

**현재까지 진척** (Mac, 2026-04-27 06:00~08:00):
- ✅ Phase 1 retrograde core 정독
- ✅ Phase 1.5 hard gate (V build <5s/cap, STOP-tie 5/5 재현, tie-break wrapper 10/10 progress)
- ✅ Phase 2 (Amendment A/B/D 통합 — `zoo_reflex_rc_tempo_abs.py`)
- ✅ Phase 3 (Amendment C/E 통합)
- ✅ Phase 4 부분 (Mac 18-seed: **11W/2T/5L** mean -1.39, ★ RANDOM8/21 recovery, ⚠️ RANDOM5 regression)
- ⏸️ Phase 4 server (30-seed × n=3, default flip 통과 게이트)
- ⏸️ Phase 5 (commit + AI_USAGE 등)

**Task 한 줄**: A 에이전트가 1-defender 상대로 "잡히지 않고 cap 먹기"를 retrograde 1v1 minimax tablebase 로 **수학적 보장**까지 끌어올린다 (게이트 a~d 안에서, 그 외는 BFS+margin fallback).

**다음 세션 첫 액션** (서버 또는 Mac):
1. `git status` — 미커밋 변경 확인 (`zoo_reflex_rc_tempo_abs.py` 만 수정됨)
2. RANDOM5 regression 단판 trace: `ABS_USE_RETROGRADE=1 ABS_FIRST_CAP_TRACE=1 ../.venv/bin/python capture.py -r zoo_reflex_rc_tempo_abs -b baseline -l RANDOM5 -n 1 -q 2>&1 | grep "ABS_A_CAP_TEST\|ABS_A_FIRST_CAP_REACH"` — 어느 시점에 retrograde 가 BFS 와 다른 결정?
3. Server jdl_wsl 30-seed × 3 sweep 시작 (STATUS 의 명령어 그대로)
4. n=3 결과 통과시 default flip (`ABS_USE_RETROGRADE` default `'1'`) + commit

**현재 코드 동작**:
- `ABS_USE_RETROGRADE=0` (default) → pm40 BFS+margin (behavior-identical rollback)
- `ABS_USE_RETROGRADE=1` → retrograde V tablebase (게이트 a~d 안에서)
- `ABS_RETRO_BUDGET_S=8.0` (default) → V build budget per cap×total

**Scope**:
- ✅ A 에이전트 단독, 1-defender 케이스, pre-cap (필 먹기 전) 단계만
- ❌ 게릴라 모드, 2-defender 케이스, post-cap plan (필 먹은 후), B 행동 — 전부 후속 plan 으로 분리

**Why**:
- pm40 (현재 default) 의 `_a_first_cap_survival_test` 가 BFS+margin=1 의 약한 검사 → 잡힐 가능성 + timeout 회귀 (RANDOM8: pm38 +29 WIN guard → pm40 timeout LOSS)
- 자산: `zoo_rctempo_core.py:931-1077` 에 retrograde V table 완성품 있음 (pm31 작업, β_retro variant 가 사용)
- V[(me, def, 0)] = +1 ⟺ "잡히지 않고 cap 도달 force-win" 수학적 증명

**Read first (위에서 아래로)**:
1. `.omc/plans/pm41-1def-retrograde-completeness.md` ← 권위 source. 모든 답이 여기 있음
2. 이 SESSION_RESUME.md 의 그 아래 (pm36 까지의 backstory)
3. `.omx/plans/pm40-pre-first-capsule-role-control.md` (codex 가 짠 직전 plan)
4. `minicontest/zoo_rctempo_core.py:931-1077` (build_retrograde_table 본문)
5. `minicontest/zoo_reflex_rc_tempo_abs.py:2456-2548` (교체 대상 함수)

**현재 직접 측정 baseline (pm41 시작 시점, 2026-04-27 04:31)**:
- 30-seed sweep: **24W / 3T / 3L** mean +9.30 (timeout 0점 처리)
- LOSS: **7, 8, 9 — 전부 timeout (1200 move)**
- TIE: 10, 11, 19
- pm41 acceptance = **timeout LOSS 0개, ≥25W, mean ≥+8.0**

**첫 액션 (30분 안)**:
1. `.omc/plans/pm41-1def-retrograde-completeness.md` 끝까지 읽기
2. `zoo_rctempo_core.py:931` retrograde 함수 정독 (signature, return, restrict_opp_side semantics)
3. RANDOM8 (회귀 seed) 단판 trace 로 현재 BFS 분류 확인:
   ```
   cd minicontest && ABS_FIRST_CAP_TRACE=1 ../.venv/bin/python capture.py \
     -r zoo_reflex_rc_tempo_abs -b baseline -l RANDOM8 -n 1 -q 2>&1 \
     | grep "ABS_A_CAP_TEST\|ABS_FIRST_CAP\|ABS_POST"
   ```
4. python REPL 에서 RANDOM8 layout 으로 retrograde V build 시간 + V 사이즈 측정
5. 그 다음 plan 의 Phase 2 (M1 diagnostics-only) 부터 구현

**구현하지 말아야 할 것 (사용자 명시)**:
- post-cap plan (이미 작동, +28점 RANDOM28 evidence 충분)
- 2-defender 케이스 (후속 plan)
- 게릴라 모드 (후속)
- B 에이전트 행동 변경 (후속)

**.omc vs .omx 분기 헷갈리지 말기**:
- `.omc/` = Claude 의 active surface (이 문서)
- `.omx/` = oh-my-codex (codex CLI) 의 active surface (historical reference)
- pm41 의 권위 source 는 `.omc/plans/pm41-...md`

---

## (이전 backstory) 2026-04-26 pm36 handoff — Pocket/food-mask done; next session = trigger-aware capsule chain + return/deposit objective

## NEXT SESSION START HERE — pm36 focus

User stopped here intentionally due to context-window pressure.

**Next problem to solve**: 기존 코드가 "필/capsule을 먹는 것"과 그 이후 scared-window plan을 제대로 연결하지 못함. 다음 세션은 pocket 자체를 더 파기보다, **필을 먹기 전/먹는 순간/먹은 뒤 계획을 어떻게 세울지**부터 잡아야 함.

User clarified the actual objective/constraints:

- Real win condition is **returned/deposited food >= 28**, not only food eaten during scared.
- Plan must connect: cap-1 trigger -> cap-2 before ghosts recover -> harvest -> return home/deposit.
- The second capsule deadline is a hard timing constraint; existing convention is cap2 by about 39 moves, total chained scared budget about 79.
- If a 28-return plan is not reachable, do not maximize easy food count blindly. Prefer hard/deep/expensive food and leave close/easy cleanup food.
- Nuance: because only 28/30 food must be returned, **leaving two deep/hard foods can be legal** when that is the best feasible 28-return subset. The objective should optimize the 28 deposited subset, not always force every deepest food.
- Full food-node search often gives better plans; the problem is runtime. Pocket abstraction is optional if a bounded food-level/hybrid planner can satisfy time.

### Current state from 2026-04-26

- Pocket detection/merge is now usable for planning.
- `RING_OVERLAP_MODE` default changed to `merge`.
- Exact per-food `food_mask` added to abstract beam; A/B can split pocket food without blocking whole header.
- `hard_score` added so if 28-food win is unreachable, planner can prefer hard-to-clean-up-later food.
- Code now has experimental full-food planner flags (`ABS_PLANNER=food`, `ABS_FOOD_BEAM=100`) and pretrigger flags, but they are **not default-safe**.
- Default `ABS_PLANNER=abstract`, pretrigger off: 30-seed n=1 vs baseline = **23W / 3T / 4L**, mean **+4.13**. Losses: seeds 8, 9, 16, 28.
- Food/pretrigger variants recover some losses but regress more seeds overall; keep them experimental until gated by trigger-state checks.
- Visualization `pockets_combo_30.png` now shows merged internal entries as depth labels:
  - `X1` = planner-visible outer entry
  - `X2+` = absorbed sub-pocket entries, visual explanation only
- User is still considering whether visual X should be on `attach` or `first_cell`; **planner should remain attach-based** unless explicitly redesigned.

### Files to read first

1. `.omc/plans/pm35-pocket-detection-status.md` — current truth for pocket/food-mask/hard-score state.
2. `minicontest/zoo_rctempo_gamma_graph.py` and `minicontest/zoo_rctempo_gamma_search.py` — production graph/search copies.
3. `minicontest/zoo_reflex_rc_tempo_abs.py` — in-game strategy builder/executor.
4. `.omc/plans/pm33-abstract-graph-2cap-strategy.md` — original 2-cap scared-window design.

### What "capsule-aware planning" means here

Current abstraction mostly assumes a scared-window segment has already started or starts at a cap. The missing design is the full timing pipeline:

1. **Before cap**: A moves toward selected cap and may collect incidental food.
2. **Trigger moment**: when A eats cap-1, scared timer starts.
3. **B state**: B may have been defending/pre-advancing; at trigger it should switch into its planned role.
4. **Cap-2 extension**: if using 2-cap chain, cap-2 must be eaten within the 39-move deadline.
5. **During scared**: A/B execute coordinated food plan using pocket headers and exact food masks.
6. **After scared / deposit**: agents must return home and deposit; opportunistic food on return may matter.

### Recommended first actions next session

1. Add/inspect trigger-time diagnostics at scared start:
   - trigger agent, A/B positions, carrying counts, remaining capsules, selected strategy, cap2 slack, and whether actual state matches plan assumptions.
2. Add execution gating:
   - only execute ABS scared strategy if the trigger agent and teammate positions are compatible with the plan start cells;
   - otherwise fallback to rc82 instead of forcing an invalid plan.
3. Produce seed-level plan visualization for failure/near-failure seeds showing:
   - A path, B path, cap eaten times, food eaten/returned, food left, hard-score heat, and home return.
   - Start with seeds 8, 9, 16, 28 first, then 4, 7, 14, 17, 18, 22, 24, 25, 27, 30.
4. Inspect `zoo_reflex_rc_tempo_abs.py:_build_strategies()` and decide whether the plan should start from:
   - cap position after cap is eaten, or
   - current in-game positions before cap with a trigger-time model.
5. Add explicit plan fields for timing/deposit:
   - `cap1_time`, `cap2_time`, `scared_budget_used`, `a_entry_time`, `b_entry_time`, return/deposit target, expected returned count.
6. Only after diagnostics/visualization confirm the failure mode, tune hard-score/slack, B coordination, or selective pretrigger.

### Do not forget

- The user’s question for next session is not "pocket detection" anymore.
- The user’s question is: **"필 먹는 거까지 고려해서 계획을 어떻게 세울 것인가?"**
- Do **not** default-enable `ABS_PLANNER=food`, `ABS_PRETRIGGER`, or `ABS_SWAP_TRIGGER` based on isolated seed recoveries. They need 30-seed evidence and trigger-state gating.
- Existing experiments/data are valuable; read before coding.

---

**Previous updated:** 2026-04-25 pm35 — **Euler tour wired + in-game 23/30 WIN baseline (B 협력이 다음 ROI)**

## pm35 TL;DR

pm34 S1에서 plan_to_cells의 'header' action을 skip 처리했던 MVP를 완성. Tree-knapsack DP에 traceback 추가하여 각 k에 대한 Euler tour 셀 시퀀스 미리 계산. Agent가 plan 받을 때 즉시 lookup. **30-seed n=1 sweep 결과 23 WIN / 3 TIE / 4 LOSS = 76.7% WR, mean +4.23**.

### 🎯 pm35 최종 상태

- **23/30 in-game WIN** (vs baseline, n=1) — feasibility 예측 (20/30) 초과
- WIN seeds: 1, 2, 4, 5, 6, 7, 12-15, 17-27, 29, 30
- LOSS seeds: 8, 9, 16, 28 — 모두 plan food<28 (구조적 한계)
- TIE seeds: 3, 10, 11

### 🔬 pm35 핵심 진단

| 회귀 seed | cap1 plan | cap2 plan | 진단 |
|---|---|---|---|
| 8 | 20 | 18 | both<28 → A 단독 부족 |
| 9 | **11** | 22 | cap1 매우 낮음 |
| 16 | cap-in-pocket | - | pm34 known issue |
| 28 | 22 | 24 | both<28 |

**결론**: 현재 ABS = A 단독 1-trip 모델. Feasibility 20/30은 **A+B 협력** 가정. B=rc82 fallback이라 plan food<28 maps에서 cover 못함 → **B 협력 = pm36+ ROI 1순위**.

### 📊 Heatmap (home_dist 분포)

- shallow (≤3): **mean 0.9** per map. 6/30 maps만 ≥2.
- medium (4-7): mean 5.7
- deep (≥8): mean 23.4 (78%)
- "Trip-2 shallow buffer" 전략 **구조적 무효**. 1-trip 28-food가 유일한 win path.

### 🚨 pm36 first action

**Blue 팀 mirror + B 협력 모델**:
1. Blue 팀에서도 ABS 작동 (현재 BLUE=rc82 fallback)
2. B를 plan에 통합: 4-strategy feasibility (S1-S4)에 맞춰 B의 cap/food 분담
   - S1 CLOSE_SPLIT: A→cap_close, B→cap_far + 양쪽 harvest
   - S2 CLOSE_BOTH: A→cap1+cap2 detour, B→food only
   - 게임 시작 시 4 strategies 모두 plan 후 best 선택
3. 30-seed sweep 재측정 → seed 8, 9, 16, 28 회복 확인

### 📂 pm35 production files

- `minicontest/zoo_rctempo_gamma_graph.py` — `_tree_knapsack` traceback 포함
- `minicontest/zoo_reflex_rc_tempo_abs.py` — Euler tour 실행
- `experiments/rc_tempo/home_dist_analysis.py` (new) — heatmap script
- `experiments/artifacts/rc_tempo/home_dist_*.{csv,png,md}` (new)

### 📊 pm35 deferred

- **Saturating objective `min(28, food)`**: 현재 beam이 28 넘어 max 추구. 28 도달 가능한 plan은 path 단순화 가능. ROI 작음.
- **n=10 안정 sweep**: 진행 중 (n=5, ~25min)
- **회귀 seed deep dive**: plan trace 시각화 (현재는 수치만)

---

(Earlier session TL;DRs below — pm34, pm33, pm32, pm31 등 preserved)

## pm34 TL;DR

pm33에서 설계만 했던 abstract graph를 구현하고 food-level (19/30 WIN)과 비교. 초기 13/30 → 여러 버그 수정 거쳐 **최종 20/30 WIN** 도달. **Food-level 수준 초과**.

### 🎯 pm34 최종 상태

- **20/30 WIN** (BEAM=500, 7s wall, 1.3s per map single-thread)
- Food-level 19/30보다 +1 우월
- β agent init 예산 (15s) 여유
- WIN seeds: {1, 3, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 19, 20, 21, 23, 25, 26, 28, 29}
- 미해결: {2, 4, 16} — beam=5000에서 {2} 회복, seed 16은 cap-in-pocket 구조적 한계

### 🔧 pm34 주요 수정/구현

1. **Abstract graph 모듈화** (`experiments/rc_tempo/abstract_graph.py`) — PIL 제거, reusable
2. **Beam search** (`abstract_search.py`) — bitmask + multi-source/sink + Pareto dedup
3. **Tree knapsack DP** — `cost_table[k]` for partial pocket visits (all-or-nothing 제거)
4. **Cap-in-pocket extended_main fix**
5. **X revisit 허용** — chamber/loop neck 재통과 가능
6. **Y-merge food-union 수정** — trunk food 이중 합산 버그 제거
7. **Pareto dedup key** — food를 dedup key에 포함하여 partial-visit 옵션 보존

### 🚨 pm35 first action

β agent 구현 시작:
- `minicontest/zoo_reflex_rc_tempo_gamma.py` 신규 파일 (or β 확장)
- `registerInitialState`:
  - `build_from_maze(game_state.data.layout)` 호출 (~5ms)
  - 4 strategy beam_search_abstract (~1.3s)
  - best plan을 action sequence로 변환
- `chooseAction`:
  - pre-planned action 반환
  - 남는 ms에 beam 확장 (anytime refinement)
- 30-map HTH 측정 vs β v2d 75.65% → target 85-95%

### 📂 pm34 production files (β agent가 import할 것)

- `experiments/rc_tempo/abstract_graph.py` — graph builder
- `experiments/rc_tempo/abstract_search.py` — beam engine
- (나중) `minicontest/zoo_rctempo_core.py` 확장: 위 두 모듈을 agent 환경에 맞게 포팅

### 📊 pm34 beam scale 실측 (per map single-thread)

| BEAM | WIN | per-map wall |
|---|---|---|
| 500 | 20/30 | 1.3s |
| 2000 | 20/30 | 5s |
| 5000 | 21/30 | 13s ⚠️ tight |
| 20000 | 18/30 (non-monotonic regress) | 50s |

### 🧪 pm34 탐구했지만 버려진 것

- **Chamber atomization** via biconnected decomposition — regression (atomic 제약이 beam 유연성 파괴)
- **Priority tweaks** (depth_sum 제거 등) — BEAM=500에서 결과 변화 無
- **Larger beam** (20000) — non-monotonic, regress

교훈: 남은 3 seed gap은 **beam search의 fundamental approximation** 한계. In-game에서 anytime refinement로 회복 기대.

---

(Earlier session TL;DRs below — pm33, pm32, pm31, pm30, pm29 preserved)

**Earlier 2026-04-21 pm33 END** — **major strategic pivot: 2-cap chain + abstract graph design**:

## pm33 TL;DR (big pivot — read carefully)

### 🔄 What changed fundamentally

pm33 planned to build **freeze-checkpoint infra** (pm32 handoff). Within the first hour, we pivoted entirely: "β doesn't need better measurement, it needs a fundamentally stronger strategy."

The rest of the session designed a new strategy: **2-capsule chain + 2-offensive, with abstract-graph-based orienteering planning**.

Freeze-checkpoint work: proven feasible (3 smoke tests PASS — game.state picklable, TEAM-dict restoration works) but **unused** because anytime refinement gives equivalent benefit without freeze infrastructure.

### 🎯 New strategy (designed, NOT implemented)

1. **Target**: `RANDOM<1..30>` layouts (2 capsules per side = 4 total, 34×18 prison-style, deterministic per seed). These are the likely tournament maps per CS470 assignment PDF (p.8).
2. **Core play**: eat cap-1 → 40-tick scared → eat cap-2 within 39 A-moves to extend → total 79-move scared → harvest food with both A and B offensive → aim for 28+ deposits = 1-trip WIN.
3. **Budget math**: scared timer decrements per opp-move. Cap-2 by A's 39th post-cap-1 move → 39 + 40 = 79 opp-moves scared = 79 A-moves budget.

### 📊 Feasibility analysis (120 cases: 30 maps × 4 strategies)

4 scenarios evaluated via food-level beam search:
| # | Code | Strategy |
|---|---|---|
| S1 | CLOSE_SPLIT | A eats cap1 (close), B eats cap2 (far). Both harvest. |
| S2 | CLOSE_BOTH | A eats cap1 → food → cap2 (detour), B pure food. |
| S3 | FAR_SPLIT | A eats cap2, B eats cap1. |
| S4 | FAR_BOTH | A eats cap2 → food → cap1 (detour), B pure food. |

Results (with depth-priority tiebreaker, BEAM=1000 = best quality): **20/30 maps achieve 1-trip WIN (≥ 28 food)**. Remaining 10 get 22-27 food (DOMINATE level).

Single-strategy wins: seeds 13 (S3), 16 (S4), 23 (S2), 29 (S4). All-four wins on 8+ seeds.

### 🏗 Abstract graph (the design we converged to)

See `.omc/plans/pm33-abstract-graph-2cap-strategy.md` for full doc. Summary:

**Nodes**:
- **X positions** (~20 for RANDOM1): main corridor cells with food OR pocket attach OR cap
- **Pocket headers** (~12 for RANDOM1): `{food, cost, direction}` attached to X's
- Merge rule: if 2+ headers share `(attach, first_cell)`, merge into ONE combined header with trunk-sharing cost (e.g., RANDOM1 (30,2): H12 cost 10 + H13 cost 6 → merged cost 12 food 4)

**Edges (X-X only)**:
- Distance-check rule: add iff `blocked_BFS(A, B) == plain_BFS(A, B)` (no detour)
- ~30 edges for RANDOM1 (vs 190 full pairwise)

**Preprocessing time**: ~5ms per map. Exact DP on abstract ≈ 100-400ms (vs food-level beam ~600ms).

### ⏱ Time budgets

| Phase | Budget (single-thread) | Use |
|---|---|---|
| registerInitialState | 15s | ~3s initial plan + 12s refinement |
| Pre-capsule A moves (~20) | 20s | Anytime refinement (~19s spare) |
| Pre-capsule B moves (~20) | 20s | Same |
| Scared phase (79 moves) | 79s | Plan execution (~10ms/move) |

**Effective plan compute**: ~55s. Far more than needed for exact DP on abstract graph.

### 🚨 Critical gap to fix in pm34

**The 120-case analysis uses FOOD-LEVEL graph, NOT the abstract graph we designed.** This is a major inconsistency — β agent will use abstract graph but our feasibility numbers are from food-level.

**First pm34 action**: port analysis to abstract graph. Re-run 120 cases. Verify ~19-20 WIN holds.

### 🎯 pm34 session goals

1. **Port analysis to abstract graph** (exact DP on abstract, verify WIN count)
2. **Implement new β agent** (`zoo_reflex_rc_tempo_gamma.py` or patch existing):
   - registerInitialState: build abstract graph + run 4 strategies × BEAM=500
   - chooseAction: return pre-planned action + anytime refinement
3. **Anytime refinement scheduling**: expand beam or explore alternative strategies during spare ms
4. **Pre-capsule navigation + post-scared return**
5. **30-map HTH validation** (target: 85-95% WR vs pm30 β v2d 75.65%)
6. **Flatten to 20200492.py** (submission)

### 📂 Critical pm33 files (read these in pm34)

- `.omc/plans/pm33-abstract-graph-2cap-strategy.md` — **full design doc (MUST READ)**
- `experiments/rc_tempo/user_final_model_seed1.py` — **FINAL abstract graph implementation** (reference)
- `experiments/rc_tempo/feasibility_4strategies_parallel.py` — 120-case analyzer (food-level — needs porting to abstract)
- `experiments/artifacts/rc_tempo/random_map_images/random_01_FINAL.png` — final abstract graph visualization
- `experiments/artifacts/rc_tempo/random_map_images/all_random_1_to_30.png` — all 30 maps composite

### 🔑 Key constraints to remember

- **Single-threaded only** (CLAUDE.md rule, tournament DQ otherwise)
- **No external deps** (numpy/pandas only; PIL only used for analysis viz, remove from β)
- **Grading maps** assumed `RANDOM<seed>` per assignment PDF. If TA uses Berkeley 1-cap maps → graceful fallback to β v2d behavior.
- **Pocket definition** final = Definition B with Y-shape merge. Internal junctions NOT shown as X's (merged into main corridor attach).

### 💡 User insights (drive implementation, not in analysis)

1. **Pre-capsule food** — A grabs food on way to cap1/cap2 → +3-5 food realistic bonus
2. **Post-scared return food** — on way home → +2-3 food
3. **B pre-advance** — B positioned at midline before cap-1 eaten → B's 79-move budget fully utilized
4. **Multi-trip** — don't need to 1-trip win; 2nd trip viable with re-respawned caps
5. **Anytime refinement** — 15s init + 40s pre-capsule compute = 55s effective

### 🚨 First action in pm34

1. Read this file + `.omc/plans/pm33-abstract-graph-2cap-strategy.md`
2. `open experiments/artifacts/rc_tempo/random_map_images/random_01_FINAL.png` to refresh visual memory of abstract graph
3. Decide: port analysis to abstract first (verify 19-20 WIN) OR jump straight to β agent impl?
   - **Recommended**: port analysis first (~2-4h, catches any abstract-specific bugs)

### Deferred (still not implemented, may or may not need)

- **Freeze-checkpoint infra** (pm32 handoff) — proven feasible, unused. Only build if abstract+anytime proves insufficient.
- **Step E → F3 server sweep** (pm32 plan) — 70-variant sweep. Not needed if new β agent outperforms.

### pm32 committed state (file changes uncommitted but ALL Mac-tested)

**Modified (8)**: zoo_reflex_rc_tempo_beta.py, zoo_reflex_rc_tempo_beta_retro.py, v3a_sweep.py, AI_USAGE.md, open-questions.md, wiki/index.md, wiki/log.md, project-memory.json

**New (18)**:
- 5 modules: composite.py, promote_t1_to_t2.py, analyze_pm32.py, filter_random_layouts.py, hth_sweep.py
- 2 unit tests: test_composite.py, test_env_parsing.py
- Plan: pm32-sweep-plan.md
- 13 layouts: defaultCapture_cap{N,S,Center,Corner}, distantCapture_cap{N,Center}, strategicCapture_cap{N,Corner}, pm32_{corridor,open,fortress,zigzag,choke}Capture
- Smoke variants list, T1 layouts list, fixtures

### 📂 Critical pm32 files

- `.omc/plans/pm32-sweep-plan.md` — full execution plan (1358 lines, 3-iter consensus)
- `experiments/rc_tempo/composite.py` — single source of truth for ranking + Wilson + Pearson + Spearman
- `experiments/rc_tempo/v3a_sweep.py` — extended VARIANTS (70 entries) + new CLI flags (`--variants-file`, `--layouts-file`, `--validate-csv`, `--allow-truncate`)
- `experiments/rc_tempo/hth_sweep.py` — thin orchestrator wrapping existing hth_resumable.py for F3
- `experiments/rc_tempo/pm32_smoke_variants.txt` — 13 variants for Mac smoke (passed)
- `experiments/rc_tempo/pm32_t1_layouts.txt` — 16 layouts for T1
- `minicontest/zoo_reflex_rc_tempo_beta.py` — 3 new env vars + my_home_cells + _maybe_retreat
- `minicontest/layouts/pm32_*Capture.lay` — 5 hand-crafted topology files

### ⚠️ Known issues for pm33

- `mazeGenerator.py` 강제 2-cap (수정 금지, layouts/ 직접 작성으로 우회 함)
- `distantCapture` trigger=0 at max_moves=200 (정상 동작 — 적이 invade 안 하는 layout. 측정 무의미하지만 무해. trigger-rate calibration in pm33 pre-sweep으로 확인하고 결정)
- 채점 환경 Python 버전 모름 — Mac/jdl_wsl/sts 모두 3.9.25로 통일 (server에 맞춤)
- `pm32_ac_retreat` Mac smoke cap%=0 (retreat가 너무 보수적; T2/F3 결과 보고 판단)

### 🆕 Freeze-checkpoint plan (pm33 → pm34)

**pm33** (이번 세션 후 다음): `phase1_runner.py` 확장
- `--save-state-at-trigger <out_pkl>`: trigger 발동 즉시 GameState pickle 후 game 종료
- `--load-state <in_pkl>`: pickle GameState 로드, β agent class swap (registerInitialState 재호출), 시뮬레이션 재개
- Multi-state cache: 1 trigger state per (opp, layout, color, seed) → 70 variants × cached states에서 즉시 chase phase 측정
- 예상 코딩: 4-6h. 위험: pickle 호환성, opponent internal state 정합성

**pm34**: freeze-cache 활용 broader sweep
- 변종 수 100+, layouts 30+, situations (ahead/behind/tied score) 분리
- 기존 wall 5h28m → 예상 1-2h (pre-trigger phase 50-80% 절감)
- AlphaZero식 checkpoint replay 패러다임 (pm34 명시적 implementation)

---

(Earlier session TL;DRs below — pm31, pm30, pm29 등 preserved for reference)

**Earlier — 2026-04-21 pm31 END** — **β_retro + β safety knob sweep (Phase 1 primitive focus)**:
- 🎯 **β_path4 / β_slack3 / β_retro all peak at cap ~55%, die ~1.5-2.1%** (240g × 6-opp × 2-layout × 2-color, max_moves=500, post-trigger).
- 📊 **Phase 1 measurement framework built**: `phase1_runner.py` (early-exit at cap/die), `phase1_smoke.py` (harness), `v3a_sweep.py` (variant framework).
- 🔬 **Retrograde tablebase proven feasible**: defaultCapture 0.77s / distantCapture 1.84s init on pure Python. V table → ±1/0 game-theoretic minimax values.
- 🐛 **β_retro bug fixed (S5)**: retrograde_best_action picked STOP on V=0 draws → A stood still → caught. Fix: greedy-toward-capsule on V=0 commits.
- ❌ **v3a (A*+Voronoi+slack) + v3b (αβ) both Pareto inferior to β safety knobs**.
- 📈 **Best Pareto improvement over β v2d**: β_path4 +4pp cap / -0.4pp die. β_slack3 +2.6pp cap / -0.8pp die (best safety).
- 🧱 **Cap ceiling ~55-56%**: plateau. Higher requires different angle (trigger, pre-position, B coord, retreat planner).

## pm32 TL;DR (NEXT SESSION — READ FIRST)

### 🎯 **Session goal**: Push Phase 1 cap 55% → 70%+ while keeping die ≤ 2%.

### 🚨 First action
1. Read this file + `.omc/wiki/2026-04-21-pm31-*.md` session log (10 min).
2. Inspect S4/S5 CSVs at `experiments/artifacts/rc_tempo/v3_sweep_pm31_{s4,s5}/`.
3. Decide which angle (see below).

### pm32 decision queue (prioritized)

| # | angle | estimated cost | expected cap% gain |
|---|---|---|---|
| A | **Trigger relaxation** (`opp_pacman>=1` + distance gate) | 1-2h | +5-10pp |
| B | **Pre-trigger A positioning** (A to midline early) | 2-3h | +5-8pp |
| C | **Retreat planner** (explicit retreat on chase fail, not rc82 food) | 3-4h | die -40% |
| D | **Monster/distantCapture specific tuning** (per-layout knobs) | 2-3h | +3-5pp in hard opps |
| E | **Agent B pro-active defender disruption** | 4-6h | speculative |
| F | **β_retro + loose trigger combo** (currently untested) | 1h | +2-5pp |

**Recommended first**: F (β_retro loose — cheap, already mostly built) → A (trigger relax) → C (retreat planner if die problematic).

### pm31 core findings (must retain)

1. **β v2d 75.65% WR (pm30 2000g HTH) ≠ cap% 52% (pm31 Phase 1 measurement)**. Different metrics. Never conflate.
2. **Perfect info in minicontest** (fog-of-war disabled in capture.py). Enables retrograde + αβ without belief state.
3. **β safety knobs** (ABORT_DIST, CHASE_SLACK, PATH_ABORT_RATIO) are backward-compat env vars on `zoo_reflex_rc_tempo_beta.py`. **Defaults preserve pm30 behavior exactly.**
4. **retrograde tablebase** in `zoo_rctempo_core.build_retrograde_table` builds in <2s on 32x16 maps. Use for theoretical guarantees.
5. **Phase 1 measurement framework** (`phase1_runner.py` + `phase1_smoke.py` + `v3a_sweep.py`) is production-ready. Extend with new variants by adding to VARIANTS dict.

### pm31 committed state

| Variant | 240g cap% | die% | wall | Notes |
|---|---|---|---|---|
| **β_path4** | **55.8** | **1.7** | 2.2s | Pareto winner (env: BETA_PATH_ABORT_RATIO=4) |
| **β_slack3** | 54.3 | **1.3** | 2.3s | Safety winner (env: BETA_CHASE_SLACK=3) |
| **β_retro** | 55.4 | 2.1 | 3.5s | Retrograde works; bugs fixed in S5 |
| β_v2d (pm30) | 51.7 | 2.1 | 2.3s | pm30 committed baseline (unchanged) |

### 📂 Critical pm31 files

- `.omc/plans/pm31-primitive-spec.md` — full design spec
- `.omc/wiki/2026-04-21-pm31-*.md` — pm31 session log (this session)
- `minicontest/zoo_reflex_rc_tempo_beta.py` — pm30 β with env var knobs (backward compat)
- `minicontest/zoo_reflex_rc_tempo_beta_retro.py` — retrograde agent (pm31)
- `minicontest/zoo_rctempo_core.py` — extended with build_retrograde_table, risk_weighted_astar, ab_capsule_chase, voronoi_safe_path, slack_plan_to_capsule, _neighbors_with_stop
- `experiments/rc_tempo/phase1_runner.py` — Phase 1 early-exit runner
- `experiments/rc_tempo/phase1_smoke.py` — parallel smoke harness
- `experiments/rc_tempo/v3a_sweep.py` — variant sweep framework
- `experiments/rc_tempo/retrograde_test.py` — retrograde feasibility benchmarks
- `experiments/artifacts/rc_tempo/v3_sweep_pm31_s{3,4,5}/` — all CSVs (preserved)

### ⚠️ Known issues / TODOs carry-over

- your_best/baseline{1,2,3}.py still DummyAgent (submission flatten pending)
- UNSAFE layout capsule chase — unchanged from pm30
- DISTANT layout hard (rc82 50%, rc47 30T deadlock) — still structural
- Full-game 1200-move HTH validation for β_path4/β_retro — **NOT done**; needed before flatten
- Monster distantCapture 30-50% die in Phase 1 — specific weakness, no targeted fix

### Quick reference — env vars for variant testing

```bash
# β safety tuning (default = pm30 behavior)
BETA_ABORT_DIST=3           # (default 2)  defender d_me ≤ X → abort
BETA_CHASE_SLACK=3          # (default 1)  def_to_cap+X < me_to_cap → abort
BETA_PATH_ABORT_RATIO=4     # (default 0)  d_me ≤ me_to_cap/R → abort (0=off)

# β_retro
BETA_RETRO_DRAW_MODE=far    # never | far | always (draw commit behavior)
BETA_RETRO_DRAW_MIN_DIST=5  # V=0 commit only if d_cap ≥ X
BETA_RETRO_TRIGGER_MODE=strict  # strict (==1) | loose (≥1)
BETA_RETRO_TRACE=1          # per-tick debug logs

# v3a/v3b (Pareto inferior — mostly superseded)
V3A_VORONOI_MODE=endpoint   # full | endpoint | ap | last_k
V3B_MAX_DEPTH=4             # αβ depth
```

---

(Earlier session TL;DRs below — pm30, pm29, etc. preserved for reference)

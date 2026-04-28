---
title: "pm46 v2 — session 종결 + handoff (CAPX plan APPROVED, Phase 0/1 대기)"
tags: ["pm46", "pm46-v2", "capx", "ralplan", "consensus", "session-log", "handoff"]
created: 2026-04-28T20:48:45.390Z
updated: 2026-04-28T20:48:45.390Z
sources: [".omc/plans/omc-pm46-v2-capsule-only-attacker.md", "q-answer.md", ".omc/wiki/2026-04-29-pm46-v2-step-0-defender-zoo-inventory.md", ".omc/wiki/2026-04-29-pm46-phase-0-pretrigger-flag-is-dead-code-regression-hypothesis-.md", "minicontest/zoo_reflex_rc_tempo_abs_solo.py", "experiments/rc_tempo/pm46_v2_a_solo_matrix.sh", "experiments/results/pm46_v2/a_solo_matrix_smoke.csv"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# pm46 v2 — session 종결 + handoff (CAPX plan APPROVED, Phase 0/1 대기)

---
title: "pm46 v2 — session 종결 + handoff"
category: session-log
date: 2026-04-29
status: CLOSED
tags: [pm46, pm46-v2, capx, ralplan, consensus, handoff]
---

# pm46 v2 — session 종결 + handoff

## Date / Focus
2026-04-29. omc-pm46 v1 폐기 + pm46 v2 (CAPX, capsule-only attacker) plan 작성 + ralplan 3-iter consensus APPROVE.

## Activities (이번 세션)

### 1) pm46 v1 Phase 0 PRETRIGGER 회귀 진단

- 핸드오프 가설: historical `ABS_PRETRIGGER` 가 RANDOM6/8 -28 회귀 원인.
- 4-trace (RANDOM6/8 × ABS_PRETRIGGER on/off, single-game wrapper) 실행 결과: **byte-identical** (timing line 1 만 다름).
- 진단: `ABS_FIRST_CAP_TRIGGER=1` (default, omx-pm44 도입) 가 legacy PRETRIGGER 분기 완전히 덮음. flag 자체가 dead-code.
- 분류 (c) — different mechanism. 사용자 가설 (B midline cross) reject (R8 B at (11,1) home-side).
- Wiki: `2026-04-29-pm46-phase-0-pretrigger-flag-is-dead-code-regression-hypothesis-.md`.

### 2) Q-answer 분석 (R8 razor-edge / B prep / safety gate)

- 사용자 깊은 질문: "scared 40 안에 home 도달 plan 아닌가?"
- 답: plan은 chain 가정 (cap1+cap2 79 tick budget). R8 S4 abstract makespan=77 (slack 2) → actual makespan=79 (slack=0 razor edge, B start_dist=6 늘어남).
- R8 회귀 mechanism: cap1 corridor (x=17~24, y=11) 에 ghost 미리 배치 → scared 동안 path 차단 → cap1 도달 실패 → chain 깨짐 → 단일 scared 안 home 못 감 → ghost active 후 11 food carry 사망.
- ABS_B_PREP_HOME_MARGIN 의미: enemy-side cell 의 frontier_dist > margin 이면 reject. margin=0 = strict home-only. R8 풀 가능성 NO (B 가 어차피 home 에 머물렀음).
- 산출물: `q-answer.md` (repo root, gitignored 가능 — 분석 노트).

### 3) pm46 v2 reframing (사용자 의도)

> "팩맨 게임 다른 측면 무시. A 가 *죽지 않고* cap 1개라도 도착하는 로직 개발."

- 17 defender × 30 seed = 510 게임 측정 행렬 설정.
- pm46 v1 (mode-commit + B prep) 폐기.
- pm46 v2 (CAPX, capsule-only attacker) 시작.

### 4) Defender zoo inventory (Step 0)

- minicontest/ ~190 .py 파일 스캔.
- 17 defender 정선 (Tier-A 7 + B 5 + C 3 + D 2).
- Wiki: `2026-04-29-pm46-v2-step-0-defender-zoo-inventory.md`.

### 5) A solo wrapper (Step 1 부분)

- `minicontest/zoo_reflex_rc_tempo_abs_solo.py` 작성: ReflexRCTempoAbsAgent (lower-index = A) + StubBAgent (higher-index = STOP).
- `experiments/rc_tempo/pm46_v2_a_solo_matrix.sh` matrix wrapper.
- Smoke 9 게임 (3 def × 3 seed) 실행:

| defender | reached | died | none | total |
|---|---|---|---|---|
| baseline | 0 | 3 | 0 | 3 |
| monster_rule_expert | 0 | 3 | 0 | 3 |
| zoo_dummy | 0 | 0 | 3 | 3 |

- 발견: `[ABS_A_FIRST_CAP_REACH]` metric 이 cap1 한정 → "outcome=died" 라도 cap2 먹은 경우 있음 (baseline_seed1: scared started 발동 = cap2 먹음). 진짜 metric = `len(getCapsules())` delta. 측정 metric 재정의 필요.

### 6) ralplan 3-iter consensus

- iter 1: Planner draft (384 lines) → Architect SOUND_WITH_RESERVATIONS (7 patches) → Critic ITERATE (4 추가 = 총 11 P-patches).
- iter 2: Planner revision (581 lines, 11/11 P-patches + survival emphasis) → Architect PASS_TO_CRITIC (3 S-patches) → Critic ITERATE (6 N-patches).
- iter 3: Planner revision (611 lines, 6/6 N-patches) → Architect PASS_TO_CRITIC → **Critic APPROVE**.
- Plan: `.omc/plans/omc-pm46-v2-capsule-only-attacker.md`.

## Observations

- ralplan consensus 가 plan quality 크게 끌어 올림 (특히 metric inconsistency, A* compute budget, survival emphasis 부분).
- Critic 의 P1 (metric correction) 발견이 결정적 — `[ABS] scared started` line 이 ABS class 전용 emit 이라 CAPX 가 emit 못 함. 진짜 ground truth = `getBlueCapsules()` delta.
- Architect S1 (node cap 500 → 2000) 합리적 — K=8 + 4 defender 면 500 노드 자주 초과 → fallback 강제 → P11 detour 무효화 risk.
- Critic N4 (per-defender override hard rule) — 사용자 의도 ("죽지 않고 도착") 정밀 표현. degenerate trade-off (aggregate 통과 but 한 defender 가 80% 자살) 봉쇄.

## Decisions

- pm46 v1 폐기, pm46 v2 (CAPX) 진행.
- CAPX = greenfield (`zoo_reflex_rc_tempo_capx*.py` 새 파일). ABS 본체 안 건드림. 제출 코드 안 건드림. omx 영역 안 건드림. discretionary AI_USAGE.
- 측정 metric = `len(getBlueCapsules())` decrement. ABS-baseline 도 같은 metric 재측정 (Phase 0).
- Phase 0 (sts 서버, 510 game ABS re-baseline) + Phase 1 (Mac, CAPX prototype) 병렬. CLAUDE.md directive ("10+분 compute = sts, Mac = 코딩").

## Open items / Next-session priority

**즉시 (다음 세션 첫 30분)**:
1. ABS 측 cap-eat detector shim 추가 (~15 LOC) — `zoo_reflex_rc_tempo_abs_solo.py` 의 wrapper subclass 또는 별도 module.
2. `pm46_v2_a_solo_matrix.sh` parser update (`[ABS_CAP_EATEN]` 또는 `[CAPX_CAP_EATEN]` 둘 다 지원).
3. git commit + sts 동기화.

**Phase 0 launch (sts background, ~4-5h)**:
4. tmux work 안에서 510 game sweep launch with `2>&1 | tee logs/...`.
5. 진행 상황 capture-pane 으로 모니터.

**Phase 1 (Mac, 병렬 코딩)**:
6. `zoo_reflex_rc_tempo_capx.py` 작성 — plan §5 알고리즘 따라.
7. `zoo_reflex_rc_tempo_capx_solo.py` (Stub B + createTeam).
8. Phase 1 AC: p95 wall-time < 150ms 측정 (200+ ticks Mac timing-gate).
9. Phase 2 smoke (3×3) 검증.

**Phase 2.5 + Phase 3** (Phase 0 결과 + Phase 1 prototype 합쳐 진행):
10. Phase 2.5 tier-screening (17×5=85 game).
11. Phase 3 full matrix (17×30=510 game on sts).

## 핸드오프 파일

- 권위 plan: `.omc/plans/omc-pm46-v2-capsule-only-attacker.md` (611 lines, ralplan APPROVED)
- 진단 노트: `q-answer.md` (repo root)
- inventory: `.omc/wiki/2026-04-29-pm46-v2-step-0-defender-zoo-inventory.md`
- pm46 v1 폐기 배경: `.omc/wiki/2026-04-29-pm46-phase-0-pretrigger-flag-is-dead-code-regression-hypothesis-.md`
- 코드 (이번 세션):
  - `minicontest/zoo_reflex_rc_tempo_abs_solo.py` (Step 1 wrapper)
  - `experiments/rc_tempo/pm46_v2_a_solo_matrix.sh` (matrix script)
  - `experiments/results/pm46_v2/a_solo_matrix_smoke.csv` (smoke 9 game)
- session-log (이 entry): `.omc/wiki/2026-04-29-pm46-v2-session-end-handoff.md`

## Sts 서버 사용 가이드

`.omc/wiki/remote-compute-infra-wsl2-ryzen-7950x-server-jdl-wsl.md` 참고. 핵심:
- `ssh jdl_wsl` (WSL2 Ubuntu, port 2222, root)
- 프로젝트 path: `/root/projects/coding-3` 또는 `~/projects/coding-3`
- venv: `.venv/` (numpy 2.0.2 + pandas 2.3.3, Mac 동일)
- tmux session `work` 영구. 끊어지면: `tmux new-session -d -s work && tmux send-keys -t work 'cd ~/projects/coding-3 && source .venv/bin/activate' Enter`.
- 장시간 run: `2>&1 | tee logs/<name>.log` 필수 (capture-pane 2000-line 버퍼 한계).

## Cross-platform 주의

`.omc/wiki/2026-04-30-pm45-final-decision.md` Cross-platform note: Mac vs sts agent 결정 다름 (md5 동일에도) — anytime beam search CPU-속도 의존성. **동일 환경 안에서만 정량 비교**. Phase 0 baseline (sts) vs Phase 3 CAPX (sts) 같은 환경에서 측정 → 비교 valid.


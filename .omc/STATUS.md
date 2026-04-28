# STATUS — CS470 A3 Pacman Capture-the-Flag

**Last updated:** 2026-04-29 — **pm46 v2 (CAPX) Phase 1 + Phase 2 + Phase 2.5 PASS, Phase 0 + Phase 3 in flight (Mac CAPX 510 + sts ABS 510 동시).**

## ⭐ pm46 v2 status

| Phase | Status | Result |
|---|---|---|
| 1 (CAPX Agent + Wrapper) | ✅ | 665 lines greenfield, py_compile OK |
| 1 timing AC | ✅ | p95=67.6ms (limit 150ms) |
| Algorithmic patch | ✅ | `CAPX_GATE_HORIZON=8` (full-path gate over-restrictive) |
| 2 smoke (3×3) | ✅ | 9/9 eat_alive |
| 2.5 tier-screen (17×5) | ✅ | 64/85 eat_alive (75.3%) |
| Phase 4 partial compare | ✅ | CAPX 75% vs ABS 10% (+65pp) |
| 0 ABS baseline (sts 510) | ⏳ | ~225/510 (44%) |
| 3 CAPX matrix (Mac 510) | ⏳ | ~40/510 (8%) |

Plan §3.3 acceptance bars status:
- aggregate cap_eat_alive ≥ 50%: **75.3%** (tier-screen) ✅
- aggregate died_pre_eat ≤ 60%: **0.0%** ✅
- per-defender died_pre_eat < 80%: **all 0%** ✅
- ≥12 of 17 strict improvement: 6 confirmed, ≥6 more expected after Phase 0 finish.

Latest commit: `b315c4a omc-pm46-v2: CAPX agent + Phase 0/1/2 evidence`.

## (Historical) ⭐ NEXT — pm46 v2 (capsule-only attacker, CAPX) (2026-04-29)

## ⭐ NEXT — pm46 v2 (capsule-only attacker, CAPX) (2026-04-29)

**목적 (사용자 명시)**: 팩맨 게임 다른 측면 (food/scoring/win/return-home) 무시. **A 공격 에이전트가 *죽지 않고* cap 1개라도 도착하는 로직 개발**. 17 defender × 30 seed = 510 게임 행렬 측정.

**Plan**: `.omc/plans/omc-pm46-v2-capsule-only-attacker.md` (611 lines, ralplan APPROVE iter-3, 11 P-patches + 6 N-patches).

**Phase 0 (sts 서버 background, 4-5h)**: ABS-solo 17×30=510 게임 *재측정* with corrected metric (`len(getCapsules())` delta, not `[ABS_A_FIRST_CAP_REACH]` 기존 잘못된 cap1-only). Output → `experiments/results/pm46_v2/abs_baseline_corrected.csv`.

**Phase 1 (Mac, 3-4h coding 병렬)**: 새 CAPX agent `minicontest/zoo_reflex_rc_tempo_capx.py` — survival-weighted A* gate (P_survive sigmoid), defender-aware path with detour budget K=4 (hard cap 8), CAPX_HARD_ABANDON_MARGIN=-1, CAPX_MIN_PSURVIVE=0.2 floor, A* node cap 2000 (auto-lower 2000→1500→1000→500 if Mac p95 > 150ms).

**다음 세션 첫 액션** (오프닝 sequence):
1. `.omc/SESSION_RESUME.md` (이 파일 위) — onboarding
2. `.omc/plans/omc-pm46-v2-capsule-only-attacker.md` — 권위 source, 611줄
3. `q-answer.md` — B prep / safety gate 진단 (root-cause)
4. `.omc/wiki/2026-04-29-pm46-v2-step-0-defender-zoo-inventory.md` — 17 defender 분류
5. `git status` — 미커밋 변경 확인

**즉시 시작 가능**: Phase 0 (sts) + Phase 1 (Mac) 병렬. 3 task 명시 in plan §6.

---

## (Historical) omc-pm46 v1 Phase 0 — PRETRIGGER classification (c) (2026-04-29, SUPERSEDED)

**Result**: 4 단판 trace (RANDOM6/8 × `ABS_PRETRIGGER` on/off) **byte-identical** (line 1 timing noise만 다름). flag toggle 은 agent decision 에 0 영향 — `ABS_FIRST_CAP_TRIGGER=1` (default ON, omx-pm44 도입) 가 `_pre_scared_action` 진입을 완전히 덮어 legacy `ABS_PRETRIGGER` 분기에 도달 불가.

**Classification (c) — different mechanism**:
- (a) "B midline cross" reject — R8 trace 동안 B at (11, 1) → (12, 1), 모두 home-side (mid_x=16).
- (b) "B home에서 부작용" N/A — PRETRIGGER 자체 영향 zero.
- (c) **PRETRIGGER flag is dead under current default**. R6 회귀 = cap topology + 적 수비 강도 (`role_shape=0off_2def` 끝까지 trigger 못 일어남). R8 회귀 = post-trigger A pursuit (return_slack=0 razor edge, omx 영역).

**진단 wiki**: `.omc/wiki/2026-04-29-pm46-phase-0-pretrigger-flag-is-dead-code-regression-hypothesis-.md`
**raw logs**: `/tmp/pm46_phase0_random{6,8}_{off,pretrig}.log` (4개)

**Phase 1 implication**: 핸드오프의 직접 전제 ("PRETRIGGER 안전 변형으로 home-only B prep 도입") 무효 — toggle 할 unsafe variant 가 코드에 존재하지 않음. 현 default 의 `_choose_b_prep_candidate` (omx-pm44) 가 이미 `ABS_B_PREP_HOME_MARGIN=2` 로 home-bias. Phase 1 의 의미 재정의 필요:

- **Reframed Phase 1 GO**: 신규 `ABS_HOME_PRETRIGGER` flag 가 기존 `_choose_b_prep_candidate` 의 margin=0 (strict home) 옵션을 활성화. R6/R8 풀 의도 없고, R5 (b_start_blocked) 등 다른 seed 개선만 acceptance.
- **Pivot 옵션**: R6 (cap routing / mode-commit A_only), R8 (post-trigger pursuit, omx) 별도 진단. Phase 1 deferred.

**Open**: 사용자 결정 — Phase 1 reframed GO / pivot / hybrid.

---

## (Historical) pm45 CLOSED — retrograde feature retire (2026-04-29)

**Disposition**: `ABS_USE_RETROGRADE=0` default kept. Retrograde feature marked dead-code via comment guards on `_a_first_cap_survival_test_retrograde` and `_retrograde_best_action_with_tiebreak`; env var still parseable for research, but no production code path enables it.

**Plan doc**: `.omc/plans/omc-pm45-1def-multi-defender-cap-retention.md` (consensus iter 2 + Critic APPROVE-WITH-PATCHES)
**Final decision wiki**: `.omc/wiki/2026-04-30-pm45-final-decision.md`
**Phase 0 raw**: `experiments/results/pm45/phase0_*.csv` × 4, `phase0_summary.md`

**Phase 0 evidence (sts, 4 def × 8 seeds × 2 flag = 64 games)**:

| Defender | flag=0 caps | flag=1 caps | flag=0 died | flag=1 died | flag=0 score | flag=1 score | Net |
|---|---|---|---|---|---|---|---|
| **monster_rule_expert** (STRONG) | 5 | 1 | 3 | 4 | +14 | −6 | **NEGATIVE** ❌ |
| baseline (weak) | 14 | 9 | 2 | 5 | +13 | +38 | mixed |
| zoo_minimax_ab_d3_opp (STRONG) | 0 | 0 | 0 | 0 | 0 | 0 | UNMEASURABLE |
| zoo_reflex_aggressive (weak) | 0 | 0 | 0 | 0 | 0 | 0 | UNMEASURABLE |

Excluded a-priori: `monster_minimax_d4` (1200 ticks > 90s wall). Excluded by timeout: `monster_mcts_hand` (240s/game).

→ **0/3 STRONG defenders net non-negative** → Phase 4 dead-code direct path (plan §"Phase 4 partial-pass matrix" cell `FAIL × FAIL`).

**Architect h4 confirmed**: V table at `zoo_rctempo_core.py:1024-1036` assumes MIN-optimal defender; rule_expert is rule-based → structural mismatch. Both Mac historical (`pm41_vs_expert.csv`) and sts Phase 0 converge on same direction.

**Key infra discovery (preserved for future)**:

- `capture.py:1054` is hardcoded to iterate `lst = ['your_baseline1.py','your_baseline2.py','your_baseline3.py','baseline.py']` — runs **4 games per invocation** even with `-b override`. `_ABS_TEAM` global state pollutes subsequent games.
- Single-game wrapper `experiments/rc_tempo/pm45_single_game.py` calls `capture.runGames()` directly to bypass this. **Must use this wrapper for any future deterministic single-game work.**
- Mac and sts produce different agent decisions on identical code (md5 verified). Hypothesized cause: CPU-speed-dependent anytime beam search depth within 1-second per-turn budget. Direction (retrograde net negative) is consistent across both, magnitudes differ.

**AI usage**: pm45 retire decision appended to `docs/AI_USAGE.md`.

---

## ⭐ NEXT — omc-pm46 (pre-pill mode commit + B prep)

**Handoff**: `.omc/plans/omc-pm46-handoff-mode-commit-prep.md`
**Companion**: `.omx/plans/omx-pm47-handoff-mode-aware-strategy.md` (symmetric omx side)

**User reframing** (2026-04-29 합의):
- Game 시작에 mode commit ("A+B" vs "A_only").
- Mode 선택되면 모든 행동 일관 (B prep 포함).
- `b_start_blocked` 는 post-pill recovery 문제가 아니라 pre-pill mode commit 누락이 진짜 원인.

**책임 분담**:
- omc (이 트랙, 시간축 우선): `decide_plan_mode()` stub (항상 "A+B" 반환), home-side B prep commit (midline 절대 안 넘음, ghost 상태 유지), 미래 진짜 decision logic은 Phase 2+.
- omx (omx-pm47): A-only strategy library, 기존 S1-S4 + 새 A-only 카테고리에 mode 태그.

**Phase 0 첫 액션** (다음 omc 세션, ~30분 Mac):
- pm36 era `ABS_PRETRIGGER` 가 RANDOM6 / RANDOM8 (-28) 에서 회귀했던 원인 trace.
- 가설: B 가 midline 넘어 잡혔을 가능성 → home-only 변형은 안전할 수 있음.
- 분류 (a) midline cross / (b) home-only도 unsafe / (c) 기타 → Phase 1 implementation 결정.

**함수 책임 충돌** (TRACK_SEPARATION § 6): pm46 작업은 시간축 omc 영역이지만 `_choose_b_prep_candidate`, `_gate_first_cap_trigger_action`, `_actual_first_cap_trigger_compat` 는 historical omx (pm44). 협업 규칙: omx 에 plan 으로 통보 후 진행. omx-pm47 핸드오프에 mode 태그 인터페이스 합의됨.

**Out-of-scope**: omx 영역 (post-pill replanner, A-only strategy builder), 2-def 게릴라 (별도 plan), retrograde 부활 (pm45 종결).

---

## (Historical) pm44 — B-start mismatch handling complete

**Problem fixed**: scared-start 시점 실제 B 위치가 선택된 ABS strategy 의 planned `b_start` 와 달라 `compat=b_start_mismatch` 가 발생했고, invalid ABS scared-window plan 이 실행될 수 있었다.

**Implementation 상태**:
- ✅ `_choose_b_prep_candidate()` 로 projected-reject B prep candidate 선택 경로 추가
- ✅ `_gate_first_cap_trigger_action()` / `_actual_first_cap_trigger_compat()` 로 first-cap trigger 직전 compatibility gate 추가
- ✅ `_select_strategy_at_scared_start()` 에 `b_start_mismatch` rerank/block 경로 추가
- ✅ compatible strategy 가 없으면 `chosen=None`, `compat=b_start_blocked` 로 ABS plan 실행 차단 후 rc82/scared fallback
- ✅ pre-trigger movement freeze 는 default 미채택. RANDOM6 회귀 evidence 때문에 pm44 기본 해결책에서 제외

**Verification**:
- `.venv/bin/python -m py_compile minicontest/zoo_reflex_rc_tempo_abs.py` ✅
- Guard sweep with `ABS_REACH_EXIT=0`: `RANDOM5 6 8 9 11 12 16 21 28` ✅
- Result: `compat=b_start_mismatch` 0건 ✅

| seed | score | final compat/status |
|---|---:|---|
| RANDOM5 | +13 | `b_start_blocked` |
| RANDOM6 | +20 | `ok` |
| RANDOM8 | -28 | `ok` |
| RANDOM9 | +21 | `ok` |
| RANDOM11 | +2 | `no_scared_start` |
| RANDOM12 | +14 | `ok` |
| RANDOM16 | -12 | `no_scared_start` |
| RANDOM21 | +9 | `ok` |
| RANDOM28 | -17 | `ok` |

**Next pm45 focus**:
- Improve `b_start_blocked` and `no_scared_start` without reintroducing `b_start_mismatch`.
- First inspect RANDOM5 (`b_start_blocked`) separately from RANDOM11/RANDOM16 (`no_scared_start`).
- Keep mismatch guard as hard acceptance condition: any pm45 change must preserve zero `compat=b_start_mismatch` on guard sweep.
- Do not default-enable pre-trigger freeze unless RANDOM6 and broader guard sweep recover.

**AI usage**: pm44 production edit has been appended to `docs/AI_USAGE.md`.

---

## Previous pm41 — A 단독 1-defender 완벽 보장 (Retrograde Tablebase)

**Plan doc**: `.omc/plans/pm41-1def-retrograde-completeness.md` (권위 source — 920줄, **§13 ralplan consensus review 필독**)

**ralplan 상태** (2026-04-27): **APPROVE** by Critic after 3 iterations
- iter 1: Planner RALPLAN-DR / Architect ITERATE (4) / Critic ITERATE (7 load-bearing, 3 verified bugs)
- iter 2: Planner amendment patchset / Architect ITERATE (1 real defect: REPL loader)
- iter 3: Planner 3-fix final / **Critic APPROVE** ✅

**Implementation 상태** (Mac, 2026-04-27 phase 2+3 complete):
- ✅ Phase 1 — retrograde core 정독
- ✅ Phase 1.5 hard gate — V build 0.97-3.15s/cap, STOP-tie 5/5 reproduced, wrapper progress 10/10
- ✅ Phase 2 — Amendment A/B/D (`zoo_reflex_rc_tempo_abs.py`: `_ABS_TEAM` +4 fields, `_build_once` V build flag-gated, `_a_first_cap_survival_test` dispatcher rewrite, `_a_first_cap_survival_test_bfs` factor, `_retrograde_best_action_with_tiebreak` helper)
- ✅ Phase 3 — Amendment C/E (`_a_cap_test_action` retrograde_next consume, `_emit_a_cap_test_log` dedup sig + print body extension, `_update_abs_postmortem` REACH emission)
- ⏸️ Phase 4 — Mac partial sweep done (18 seeds), server n=3 sweep pending
- ⏸️ Phase 5 — default flip pending acceptance gate

**Mac 18-seed flag=1 결과** (2026-04-27):
- **11W / 2T / 5L** (mean -1.39)
- ★ Recoveries: RANDOM8 (-28→+7) and RANDOM21 (-18→+9)
- ⚠️ Regression: RANDOM5 (+28→-28) — needs server n=3 to confirm not stochastic
- WIN: 0,1,2,4,6,8,12,13,14,15,21; TIE: 11,16; LOSS: 3,5,7,9,28

**Acceptance gate (plan §13.2 Amendment F) — 미충족, server n=3 필요**:
- W ≥ 25 in EVERY sweep (3 sweeps × 30 seeds)
- timeout LOSS = 0 across all 3
- outcome=died count = 0 across all 3
- mean per-sweep ≥ +8.0
- guard 회귀 없음 (RANDOM5 가 진짜 회귀인지 server 에서 확인)
- init time < 12s (현재 2.5-3s 안전)

**Default flip 보류** — `ABS_USE_RETROGRADE=0` 기본값 유지. Opt-in `ABS_USE_RETROGRADE=1` 만. Acceptance 통과 후 default ON.

**서버 핸드오프 명령**:
```
ssh jdl_wsl
cd ~/coding-3/minicontest
git pull
for r in 1 2 3; do
  for s in $(seq 0 29); do
    timeout 240 ABS_USE_RETROGRADE=1 ../.venv/bin/python capture.py \
      -r zoo_reflex_rc_tempo_abs -b baseline -l RANDOM$s -n 1 -q 2>&1 \
      | grep -E "Average Score|REACH" \
      >> /tmp/pm41_sweep_r$r.log
  done
done
```

**RANDOM5 regression 추적 plan**:
- ABS_FIRST_CAP_TRACE=1 + RANDOM5 단판 → 어디서 retrograde 결정이 BFS 와 갈리는지
- RANDOM5 가 정말 1-defender 케이스인지 (2-defender 라면 TWO_DEF UNSAFE 가 옳음)
- V=+1 이 false-SAFE 인지 (2nd opp 가 visible 안 잡혀서)

**plan §13 amendment 강제 사항** (구현 시 본문 4.2/6.3/7/10 절 대신 §13.2 patchset 적용):
- A: home-side BFS fallback + UNKNOWN_DEF check 위치 수정 (현 본문 dead code 버그)
- B: `_retrograde_best_action_with_tiebreak` 신규 (STOP-wins-tie 방지, BFS-dist 1차 + non-STOP 2차)
- C: `_a_cap_test_action` 가 `retrograde_next` 를 `path[1]` 보다 먼저 consume
- D: V build 자체 flag-gate (현 본문은 flag OFF 시 init 시간 못 살림)
- E: `[ABS_A_FIRST_CAP_REACH]` 신규 emission + dedup sig 확장
- F: n=3 mandatory + timeout=0 headline (현 본문 W≥25 단일 sweep 통계적 noise)
- H: 신규 Phase 1.5 hard gate (`Layout(randomLayout(8).split('\n'))`, `getLayout` 아님)

**실행 경로 (Critic 권고)**: `clear-context` single Claude opus session. Phase 1→5 sequential, Phase 2/3 같은 함수 수정 → team 병렬 X. Phase 4 sweep 만 `run_in_background` 가능.

**Why**:
- pm40 의 `_a_first_cap_survival_test` 는 BFS path + per-step margin=1 의 약한 검사. 사용자 우려 직접: "그냥 BFS 로 가면 잡히는 거 아니야? 무조건 어떤 경우에도 잡히지 않고 필 먹는 게 확실해야 됨"
- 직접 측정한 pm40 결과: **24W/3T/3L LOSS=[7,8,9] 전부 timeout** = "A 가 너무 보수적 reject → cap 안 먹음 → 1200 move 동안 점수 못 쌓음" 회귀
- 특히 8번: pm38 +29 WIN guard → pm40 timeout LOSS

**What**:
- `zoo_rctempo_core.py:931 build_retrograde_table` 활용 — minimax V 1v1 tablebase, 이미 있는 자산 (pm31 β_retro 사용)
- V[(me, def, 0)] = +1 ⟺ "잡히지 않고 cap 도달 force-win" **수학적 증명**
- pm40 의 1-defender 분기를 V lookup 으로 교체

**Scope** (사용자 명시 고정):
- ✅ A only / 1-defender / pre-cap
- ❌ 2-defender / 게릴라 / post-cap / B — 후속 plan (pm42+)

**Acceptance**:
- 30-seed sweep ≥ **25W**, **timeout LOSS = 0**, mean ≥ +8.0
- guard seeds (6, 8, 11, 12, 21, 28) 회귀 없음
- ABS_USE_RETROGRADE=0 rollback intact
- init 시간 < 12s

**현재 직접 측정 baseline (pm41 시작 시점, 2026-04-27 04:31)**:
- 30-seed sweep: 24W / 3T / 3L mean +9.30 (timeout 0점 처리)
- LOSS: 7, 8, 9 (모두 timeout)
- TIE: 10, 11, 19

**.omc vs .omx**: pm37/38/39/40 plan 은 `.omx/plans/` 에 있음 (codex 작업). pm41 부터는 `.omc/plans/` (Claude 세션) 에서 진행. 양쪽 동기화 필요한 시점 도래 — 단 pm41 작업 끝난 뒤 정리.

---

## (이전 진척) 2026-04-26 pm36 — Pocket merge/food-mask/hard-score done; next = trigger-aware capsule chain + return/deposit objective:
- ✅ **Pocket merge cleanup**: `RING_OVERLAP_MODE` default is now `merge`; absorbed tree headers removed after merge; merged pockets include 0-food branches for single-entry topology.
- ✅ **Exact per-food masks**: abstract beam now tracks `food_mask`; cross-agent disjointness uses `forbidden_food_mask`, not whole-header forbids. Ring/merged `_ring_dp()` reconstructs actual food sets. Tree headers exclude `attach` food from pocket-internal alts.
- ✅ **Hard-food fallback**: graph computes `food_hard_scores`; beam returns `hard_score`; if no 28-food win exists, strategy selection can prefer hard-to-clean-up-later food within small count slack.
- ✅ **Visualization update**: `experiments/artifacts/rc_tempo/pocket_viz/pockets_combo_30.png` now labels merged entries by depth:
  - `X1` = planner-visible outer entry
  - `X2+` = absorbed sub-pocket entries, visual explanation only
- 📊 **Clean abstract feasibility**: merge + exact food masks / no attach double-count = **19/30 WIN**, mean food **27.6**.
- 🧪 **Smoke**: `python3 experiments/run_match.py --red zoo_reflex_rc_tempo_abs --blue baseline --layout RANDOM --seed 1 --timeout 120` → no crash, Red win, score 18, wall 2.839s.
- 🎯 **Next session focus**: stop pocket work unless visualization bug appears. Solve **capsule-trigger-aware planning**: how to plan before cap, at cap-eat trigger, B role switch/pre-advance, cap-2 timing, scared-window food plan, and return/deposit.
- 🎯 **User-clarified objective**: plan quality must be judged by **returned/deposited food >= 28**, not eaten-only food. If 28 returned is infeasible, collect hard/deep/expensive food and leave close/easy cleanup food. But because only 28/30 is required, leaving two deep/hard foods can also be legal when that is the best feasible 28-return subset.
- 📊 **Current default in-game baseline after compatibility/fallback fixes**: `ABS_PLANNER=abstract`, pretrigger off = **23W / 3T / 4L**, mean **+4.13** on 30 seeds vs baseline. Losses: 8, 9, 16, 28.
- ⚠️ **Experimental variants are not default-safe**:
  - `ABS_PLANNER=food ABS_FOOD_BEAM=100 ABS_PRETRIGGER=1` = 20W / 4T / 6L, mean +6.73. Recovers some seeds but creates regressions.
  - `ABS_PLANNER=food ABS_FOOD_BEAM=100 ABS_PRETRIGGER=1 ABS_PRETRIGGER_B=0` = 21W / 2T / 7L, mean +4.90. Also regresses overall.
  - Current diagnosis: blocker is trigger-time state mismatch and pretrigger defense/race tradeoff, not pocket representation alone.

### Immediate next-session question

기존 코드가 "필을 먹었다고 가정한 scared-window plan"과 "실제 게임에서 필을 먹으러 가는 과정/먹은 순간"을 잘 연결하지 못함. 다음 세션은 다음을 먼저 설계/시각화:

1. Scared-start diagnostics: trigger agent, A/B positions, carrying counts, remaining capsules, chosen plan, cap2 slack, and assumption-match result.
2. Execution gating: only run ABS scared strategy if actual trigger state matches plan starts; otherwise fallback to rc82.
3. A가 cap-1까지 가는 pre-cap path와 incidental food.
4. cap-1 먹은 tick/time을 scared-window origin으로 삼는 방식.
5. B가 수비/대기 중이다가 trigger 시점에 어디서 시작한다고 모델링할지.
6. cap-2 extension deadline: 39 moves 안에 누가 어떻게 먹는지.
7. A/B path visualization with eaten/returned/left food, home return, and hard-score heat on failure seeds.

---

**Previous updated:** 2026-04-25 pm35 — **Euler tour wired + 30-seed in-game baseline 23/30 WIN (76.7% WR)**:
- ✅ **Tree-knapsack DP에 traceback 추가** (`zoo_rctempo_gamma_graph.py:_tree_knapsack`): cost_list와 함께 cells_list[k] 반환. 각 k에 대한 Euler tour 셀 시퀀스 (attach → 안 → 회수 → attach).
- ✅ **Header에 `cells_table` 필드** 추가 — beam 결정 후 plan_to_cells가 즉시 lookup.
- ✅ **Agent `_plan_to_cells`의 'header' action wiring** (`zoo_reflex_rc_tempo_abs.py`): 이전에 skip → 이제 실제 pocket 진입/회수.
- ✅ **Sanity test 10 maps × 모든 headers × 모든 k**: 0 위반 (cost == cells len, all grid-adjacent, 모든 tour는 attach에서 끝남).
- 📊 **30-seed n=1 sweep (ABS vs baseline)**: 23 WIN / 3 TIE / 4 LOSS = **76.7% WR, mean +4.23**.
  - WIN seeds: 1, 2, 4, 5, 6, 7, 12-15, 17-27, 29, 30 (23개)
  - TIE: 3, 10, 11
  - LOSS: 8 (-18), 9 (-25), 16 (-2), 28 (-20)
- 🔬 **회귀 4 seeds 진단**: plan food < 28 (구조적 한계, 코드 버그 X)
  - 8: cap1 plan 20 / cap2 18 — both < 28
  - 9: cap1 plan **11** / cap2 22 — 매우 낮음
  - 16: cap-in-pocket 구조 (pm34 known issue)
  - 28: cap1 plan 22 / cap2 24 — both < 28
  - 결론: 현재 ABS = **A 단독 모델**. Feasibility 20/30은 **A+B 협력** 가정. B=rc82 fallback이라 plan food<28 maps에서 cover 못함.
- 📊 **Heatmap 분석 (`experiments/artifacts/rc_tempo/home_dist_summary.csv`)**:
  - shallow (home_dist≤3) mean **0.9** per map (range 0-3)
  - medium (4-7) mean 5.7
  - deep (≥8) mean 23.4 (≈78%)
  - 결론: "trip-2 shallow buffer" 전략 구조적 무효 (6/30 maps만 shallow≥2). 1-trip 28-food 가 유일한 합리적 win path.

### pm35 → pm36 handoff

→ **B coordination 시도 결과: NET-NEGATIVE**. Naive BFS-greedy "B during scared = nearest food" 구현 후 6-seed smoke: RANDOM5 +21 → -11 (-32 폭락), RANDOM1 +9 → +24 (+15 gain), 손실 seeds(8/9/16/28) 회복 거의 없음. 가설: rc82가 scared 중 자연스럽게 offensive role-switching 함 (`zoo_reflex_rc82.py:67-76`에서 `isPacman`/`scaredTimer` 검사). 내 naive greedy가 rc82의 heuristic-based offensive보다 약함. **결론: B는 rc82에 위임 유지.**
→ **진짜 lever (LOSS seeds 회복용)**:
  - Beam strengthening (BEAM=2000-5000) — pm34 분석에서 BEAM=5000이 seed 2 회복. 단점: per-map 13s (15s init 예산 압박).
  - Pre-cap food collection (A가 cap1 가는 길에 food 1-3개) — SESSION_RESUME 명시.
  - Smarter B coordination (beam-based plan for B instead of naive greedy).
→ Saturating objective (`min(28, food) + ε*food`) 미구현. 우선순위 낮음.
→ Blue 팀 mirror 미구현. Tournament fairness 위해 필요. 코드 1-2h.
→ n=5 sweep 재가동 중 (~25min, clean code). 종료 후 확정 진단.

### pm35 file changes (uncommitted, smoke-tested)

- `minicontest/zoo_rctempo_gamma_graph.py` — _tree_knapsack returns (cost_list, cells_list); header에 cells_table 추가
- `experiments/rc_tempo/abstract_graph.py` — 위와 byte-identical sync
- `minicontest/zoo_reflex_rc_tempo_abs.py` — _plan_to_cells에 header 처리 wiring
- `experiments/rc_tempo/home_dist_analysis.py` (new) — 30-map BFS home_dist 계산
- `experiments/artifacts/rc_tempo/home_dist_*.{csv,png,md}` (new) — 분석 결과

---

**Earlier 2026-04-22 pm34 END** — **Abstract graph port + feasibility 20/30 WIN (식타 19 초과)**:
- ✅ **Abstract graph 모듈화**: `experiments/rc_tempo/abstract_graph.py`. PIL 제거, 재사용 가능. `build_from_maze` 단일 API.
- ✅ **Abstract beam search** (`experiments/rc_tempo/abstract_search.py`): bitmask vx/vh, multi-source start, multi-sink end, revisit-allowed, **Pareto dedup (food in key)**, **cost_table 기반 k-option 분기**.
- ✅ **Tree knapsack DP for pockets** (`_tree_knapsack` + `build_pocket_headers_with_cost_table`): 각 pocket을 attach root로 재구성, post-order DP로 `cost_table[k]` 계산. Partial pocket visit 모델링. Y-merge overlap 자동 해소.
- ✅ **Cap-in-pocket fix**: `extended_main` 으로 pocket 안 cap에도 edge 연결.
- ✅ **4 strategy solvers** on abstract (`feasibility_4strategies_abstract.py`): solve_split/solve_both + ProcessPoolExecutor 병렬.
- 📊 **120-case 최종: 20/30 WIN** (BEAM=500, 7s wall, 1.3s per map single-thread).
  - Food-level 식타: 19/30 → **abstract +1 초과**
  - 양쪽 동일 WIN: 16 seeds
  - Abstract only WIN: {10, 14, 25, 29} (4 seeds)
  - Food-level only WIN: {2, 4, 16} (3 seeds)
- 🔬 **Beam scale test**: BEAM=500/2000/5000/20000 실험. BEAM=5000에서 21 WIN (seed 2 회복), BEAM=20000 오히려 18로 regress (priority heuristic non-monotonic).
- 🔬 **Chamber/biconnected 프로토타입 실험** (`chamber_test.py`): leaf-block chamber atomization 시도 but **regression** (atomic 제약이 beam 유연성 제거). Biconnected decomposition으로 overlap은 해소했으나 성능 향상 無 → 롤백 (main code는 chamber 없이).
- 🗺 **30 map 시각화** (`render_all_finals.py`): abstract graph 최신 state 반영. `experiments/artifacts/rc_tempo/random_map_images/random_{01..30}_FINAL.png`.
- 🚨 **해결된 버그 2개**:
  1. **Y-merge double-count**: 공통 trunk food가 각 branch에서 중복 합산 → food union 기반으로 수정
  2. **Pareto dedup key**: 이전엔 `(ci, vx, vh, start)`로 food 무시하여 k=1 옵션이 k=2..max를 prune → `(ci, vx, vh, start, food)`로 수정
- ⏱ **β agent init 예산**: BEAM=500 기준 per-map 1.3s → 15s 여유. BEAM=5000 per-map 13s (tight, risky).

### pm34 key artifacts

- `experiments/rc_tempo/abstract_graph.py` — **production module** (used by everything)
- `experiments/rc_tempo/abstract_search.py` — beam search engine
- `experiments/rc_tempo/feasibility_4strategies_abstract.py` — 120-case analyzer, 20/30 WIN
- `experiments/rc_tempo/render_all_finals.py` — 30 map 렌더러
- `experiments/rc_tempo/chamber_test.py` — biconnected chamber 실험 (참고용, regress 확인)
- `experiments/artifacts/rc_tempo/random_map_images/random_{01..30}_FINAL.png` — updated 시각화

### pm34 → pm35 handoff

→ **β agent 구현 시작**. Baseline: BEAM=500 abstract로 initial plan, in-game anytime refinement로 BEAM 점진 확장.
→ Implementation points: `registerInitialState`에서 abstract graph 빌드 (5ms) + 4-strategy beam (1.3s), `chooseAction`에서 pre-planned action + 남은 ms로 beam expand.
→ Seed {2, 4, 16} 3 미해결 WIN은 in-game 성적으로 판단 (abstract가 놓쳐도 실전 WR에선 차이 미미 가능성).

### Known pm34 issues / carry-over

- Seed 16 cap-in-pocket 특수 케이스 미해결 (tree knapsack이 cap 통합 안함)
- Seed 2, 4: beam=500 truncation, beam=5000에선 회복
- Chamber modeling으로 state space 축소 시도했으나 atomic 제약이 regress 유발 → 현재 모델은 chamber 없이 leaf-pocket + main_corridor X만
- `user_best/baseline{1,2,3}.py` still DummyAgent (pm35 flatten 대기)

---

**Earlier 2026-04-21 pm33 END** — **MAJOR STRATEGIC PIVOT: 2-cap chain + abstract graph design (not implemented yet)**:
- 🔄 **Freeze-checkpoint WORK ABANDONED mid-session**. pm32 handoff goal was freeze infra; within 1h we pivoted to a stronger strategy design.
- ✅ **Freeze-checkpoint feasibility PROVEN** via 3 smoke tests: `game.state` picklable, `random.getstate()` + `zoo_core.TEAM.__dict__` restoration works for determinism. Not used — anytime refinement gives equivalent benefit.
- 🆕 **New target strategy (designed, NOT coded)**: 2-cap chain. Eat cap-1 → 40-tick scared → eat cap-2 within 39 A-moves to extend → total 79-move scared window. Both A and B offensive. Goal: **28+ food deposit in 1 trip = WIN**.
- 📊 **Feasibility analysis (120 cases = 30 RANDOM<seed> × 4 strategies)**:
  - S1 CLOSE_SPLIT (A eats cap1, B eats cap2): 10-12/30 WIN
  - S2 CLOSE_BOTH (A detour both, B food): 14-15/30 WIN
  - S3 FAR_SPLIT (A eats cap2, B eats cap1): 14-15/30 WIN
  - S4 FAR_BOTH (A detour both reverse, B food): 13-17/30 WIN
  - **Combined ANY strategy WIN: 18-20/30 (60-67%)** depending on beam width
  - Other 10-12 maps: 22-27 food = DOMINATE level (85-95% expected WR)
- 🏗 **Abstract graph designed** (after ~10 iterations with user):
  - Nodes = X positions (main corridor: food OR pocket attach OR cap)
  - Pocket headers = `{food, cost, direction}` attached to X's
  - Y-shape merge: headers sharing `(attach, first_cell)` merged with trunk-sharing cost
  - Edges = X-X with distance-check rule (blocked == plain BFS dist → no detour)
  - **RANDOM1 example**: 20 X + 12 headers + 30 edges. Preprocessing ~5ms.
- ⏱ **Time budget (single-thread, CLAUDE.md rule)**: 15s init + 40s pre-capsule refinement = **55s effective** — plenty for exact DP on abstract graph (~400ms).
- 🚨 **Critical gap**: 120-case analysis uses FOOD-LEVEL graph. β agent will use ABSTRACT graph. Port required in pm34 before implementation.
- 📋 **NOT done in pm33**: β agent implementation, abstract-graph-based analysis, in-game validation, submission flatten.

### pm33 key artifacts

- `.omc/plans/pm33-abstract-graph-2cap-strategy.md` — **FULL DESIGN DOC** (read first in pm34)
- `experiments/rc_tempo/user_final_model_seed1.py` — **final abstract graph impl** (reference for β coding)
- `experiments/rc_tempo/feasibility_4strategies_parallel.py` — 120-case food-level analyzer
- `experiments/artifacts/rc_tempo/random_map_images/random_01_FINAL.png` — abstract graph viz
- `experiments/artifacts/rc_tempo/random_map_images/all_random_1_to_30.png` — 30-map composite

### pm33 → pm34 handoff

→ `.omc/SESSION_RESUME.md` for 5-min onboarding.
→ `.omc/plans/pm33-abstract-graph-2cap-strategy.md` for full 2-cap design + pm34 steps.

### Key design decisions made this session

1. **Grading map assumption**: `RANDOM<seed>` maps (per assignment PDF p.8). These are always 4-cap (2 per side), 34×18 prison-style.
2. **Capsule budget**: scared timer is per-opp-move. Cap-2 must be eaten by A's 39th post-cap1 move → 79 total opp-moves of scared = 79 A-moves.
3. **"Deep food"** redefinition: far from midline (x - mid_col), NOT pocket-internal depth. Depth priority = break ties by preferring deeper food.
4. **Pocket definition**: after ~5 iterations, settled on Definition B (tip → main corridor trace) with Y-shape merge. Internal junctions NOT separate X's (no red triangle).
5. **Edge rule**: distance-check (blocked == plain BFS). Avoids both over-connection and detour-edges.
6. **Single-threaded**: critical constraint. Multiplied budgets accordingly (55s effective via anytime, not 15s).

---

**Earlier 2026-04-21 pm32 END** — **3-iter ralplan consensus + Mac coding (Step A-C.2) + 16 layouts**:
- 🎯 **Plan v3 APPROVE'd via 3-iteration ralplan**: 1358-line plan at `.omc/plans/pm32-sweep-plan.md`. Architect+Critic both APPROVE. iter-1 11 fixes + iter-2 14 fixes + iter-3 8 operator-tracked.
- ✅ **Mac coding 완료 (Step A through C.2)**: 70 variants in v3a_sweep (P1=5, AA=20, AC=10, RS=5, +30 existing); 3 new env vars in β agent (BETA_TRIGGER_GATE / BETA_TRIGGER_MAX_DIST / BETA_RETREAT_ON_ABORT) with full backward compat; my_home_cells plumbing + _maybe_retreat helper + MJ-7 leak guard.
- 📦 **5 NEW modules created**: `composite.py` (compute_score + Wilson CI + Pearson_with_CI + Spearman_rho), `promote_t1_to_t2.py` (defaults locked: die-ceiling=2.5, stratify-angles, buffer-pp=2.0, data-quality-check), `analyze_pm32.py` (composite-only sort, conjunction ship rule), `filter_random_layouts.py`, `hth_sweep.py` (thin wrapper around existing hth_resumable.py — Architect iter-2 reuse fix).
- 🧪 **25 unit tests PASS**: T-U1 (env parsing), T-U2 (backward compat byte-identical), T-U3 a/b (retro×retreat + no-leak across layouts), T-U4 (composite ranks beta_path4>beta_v2d), T-U5 (Pearson + Spearman 11 cases incl ties + n<4 NaN).
- 🗺️ **16 layouts ready** (1-cap-per-side ALL): 3 originals (defaultCapture, distantCapture, strategicCapture) + 8 capsule-swap variants (default×4, distant×2, strategic×2) + 5 hand-crafted topologies (corridor/open/fortress/zigzag/choke Capture). All verified by capture.py engine load.
- 🐛 **mazeGenerator.py constraint discovered**: `add_pacman_stuff` always inserts capsules in pairs (max=4) → RANDOM<seed> always yields 2-cap maps. Plan's RANDOM-seed pool path infeasible → pivoted to hand-crafted layouts.
- 🐍 **Python parity**: Mac upgraded 3.9.11 → 3.9.25 to match jdl_wsl + sts (numpy 2.0.2, pandas 2.3.3 all identical). md5 of capture.py identical across all 3.
- 🖥️ **Second server `sts` provisioned**: AMD Ryzen 9950X3D (16C/32T, 30GB RAM, RTX 5090 unused), Ubuntu 24.04. uv + .venv 3.9.25 + numpy/pandas + smoke OK. Available for parallel work in pm33+.
- 🟡 **Mac smoke (459s, 13 var × 6 opp × 2 layout × 2 color × 5g × workers=6)**: 13/13 no-crash; **MJ-8 byte-identical pass** (pm32_aa_none_d999 ≡ beta_v2d both 13.3/1.7); top 7 variants tied at score 10.1 (N=10/cell too small to discriminate, expected); ⚠️ **distantCapture trigger=0% at max_moves=200** — opp doesn't invade in 200 moves on bigger maps.
- 🔑 **distantCapture trigger=0 reframed (NOT bug)**: trigger=0 means "opp doesn't attack → we win by score collection, no β chase needed". β variants indistinguishable on such layouts. Decision: keep max_moves=200 (matches "초반 200moves 전략" intent); trigger-rate-low layouts will be pruned in pm33 pre-sweep calibration OR accepted as wasted-but-harmless wall.
- ❄️ **Freeze-checkpoint deferred**: pm33 = build save-state-at-trigger + state-swap harness; pm34 = use it for broader sweep (more variants/maps/situations).
- 📋 **NOT done in pm32**: Step E (git push to servers), Step F1+F2+F3 (server sweep). All deferred to next session.

### pm32 file changes (uncommitted)

8 modified + 18 NEW (5 modules + 13 layouts + plan + fixtures + smoke variants list).

### pm32 → pm33 handoff

→ `.omc/SESSION_RESUME.md` for 5-min onboarding.
→ `.omc/plans/pm32-sweep-plan.md` for full execution plan (Step E onward).
→ `.omc/plans/open-questions.md` for unresolved + freeze-checkpoint pm33+pm34 plan.

---

**Earlier 2026-04-21 pm31 END** — **β Phase 1 primitive measurement + tuning sweep**:
- 🎯 **Phase 1 meas framework built**: `phase1_runner.py` (early-exit cap/die), `phase1_smoke.py` + `v3a_sweep.py`. post-trigger metrics. 31 variants swept (β safety, v3a, v3b, β_retro).
- 📊 **Best cap+die (240g × 6-opp × 2-layout × 2-color, max_moves=500)**:
  - **β_path4** (BETA_PATH_ABORT_RATIO=4): **cap 55.8% / die 1.7%** ⭐ Pareto winner
  - **β_slack3** (BETA_CHASE_SLACK=3): cap 54.3% / **die 1.3%** ⭐ Safety winner
  - **β_retro** (retrograde tablebase, S5 fixed): cap 55.4% / die 2.1%
  - β_v2d (pm30 baseline): cap 51.7% / die 2.1%
- 🔬 **Retrograde tablebase** feasible: defaultCapture 0.77s / distantCapture 1.84s init. Builds minimax V[(me,def,turn)] → ±1/0 under perfect info.
- 🐛 **β_retro S5 fix**: retrograde_best_action returned STOP on V=0 draws → A stuck. Fixed via greedy-toward-capsule on V=0 commits.
- ❌ **v3a (A*+Voronoi+slack) + v3b (αβ) Pareto inferior** (cap 18-44%, die 5-10%).
- 🧱 **Cap ceiling ~55-56% plateau** — next session needs different angle (trigger relax / pre-position / retreat planner / B coord).
- ⚠️ **Full-game 1200-move HTH NOT yet done**; needed before flatten to confirm pm30 75.65% WR baseline preserved/improved.

---

**Earlier 2026-04-20 pm30 END** — **β_chase score-conditional gate (+4.7pp on 660g 11-opp smoke)**:
- 🎯 **v2d accepted**: `_choose_capsule_chase_action` 상단에 `if my_score ≥ 5 pre-capsule: skip chase → rc82 defensive` 게이트 추가
- 📊 **660g 11-opp smoke**: current β 73.2% → v2d 77.9% (+4.7pp) overall. **rc32 +31.7pp 폭발** (Pincer defender 대응), rc02 +6.7pp, baseline +5pp, rc82 +5pp, monster +3.3pp. 무회귀.
- ❌ **v2a (full-path BFS) 기각**: margin=0 -2pp regression, margin=-1 flat. 복합 defender(rc82/rc166) 상대 과도 abort.
- 🏆 **2000g HTH 검증 완료**: 1513/2000 = **75.65%** [0.737, 0.775] — pm29 β 68.6% 대비 **+7.05pp**. Pass criteria ≥68.6% ✓.

### pm30 2000g HTH (β v2d vs pm29 β)

| Opp | pm29 β default | pm30 v2d default | Δ | pm29 distant | pm30 distant | Δ |
|---|---|---|---|---|---|---|
| baseline | 95.0% | 92.5% | -2.5 | 78.0% | 77.0% | -1.0 |
| monster | 66.0% | **81.0%** | **+15.0** 🔥 | 44.5% | **56.0%** | **+11.5** 🔥 |
| rc166 | 50.0% | 50.0% | 0 | 53.5% | **72.5%** | **+19.0** 🔥 |
| rc82 | 71.0% | **77.5%** | +6.5 | 51.5% | 50.0% | -1.5 |
| h1test | 77.0% | **100.0%** | **+23.0** 🔥 | 100.0% | 100.0% | 0 |
| **OVERALL** | **68.6%** | **75.65%** [0.737, 0.775] | **+7.05pp** | | | |

Per-opp all-layout: baseline 84.8%, monster 68.5%, rc166 61.3%, rc82 63.7%, h1test 100%.

- 🔒 **Structural**: rc47 distant = 30T 순수 교착 (0-0 1200-move timeout), rc16 = 50/50 coin flip. chase 로직으로 해결 불가 — Phase 3 DP / Agent B pre-position 차기 타겟.
- 📂 Session log: `.omc/wiki/2026-04-20-pm30-chase-score-conditional-gate-4-7pp.md`

### pm30 smoke table (660g, 11 opponents, 2 layouts, 2 colors)

| Opp | current 73.2% | v2d 77.9% | Δ |
|---|---|---|---|
| baseline | 85.0% | **90.0%** | +5.0 |
| monster_rule_expert | 68.3% | 71.7% | +3.3 |
| zoo_distill_rc22 | 100.0% | 100.0% | 0 |
| zoo_reflex_h1c | 100.0% | 100.0% | 0 |
| zoo_reflex_h1test | 100.0% | 100.0% | 0 |
| zoo_reflex_rc02 | 78.3% | **85.0%** | +6.7 |
| zoo_reflex_rc16 | 50.0% | 50.0% | 0 |
| zoo_reflex_rc166 | 66.7% | 66.7% | 0 |
| zoo_reflex_rc32 | 48.3% | **80.0%** | **+31.7** 🔥 |
| zoo_reflex_rc47 | 50.0% | 50.0% | 0 (30T deadlock distant) |
| zoo_reflex_rc82 | 58.3% | 63.3% | +5.0 |

---

**Earlier 2026-04-20 pm29 END** — rc-tempo V0.1 β 구현 + 2000g HTH 검증 + γ 기각:
- 🏆 **rc-tempo β**: 2000g HTH **68.6% overall**, **71% H2H vs rc82**, **100% vs h1test distant**.
- ✅ **β = rc-tempo V0.1 확정 제출 후보** (submission candidate tier 2, rc166 tier 1).
- ❌ **γ REJECTED**: 0/200 vs rc166 default — entry-DP 예측 가능성 취약점.
- 📊 β vs γ H2H coin flip (101/200).
- 🔧 **Flow**: Mac + Server 병렬 HTH (2000g Mac β + 2000g Server γ), resumable CSV checkpoint.
- 📂 Session log: `.omc/wiki/2026-04-20-pm29-rc-tempo-v01-beta-gamma-hth.md`.

### pm29 full β HTH table (n=200 per cell)

| Opponent | Default WR | Distant WR | avg_score def | avg_score dist |
|---|---|---|---|---|
| baseline | 95.0% [.91, .97] | 78.0% [.72, .83] | +4.66 | +0.89 |
| zoo_reflex_rc82 | **71.0%** [.64, .77] | 51.5% [.45, .58] | +5.71 | +1.72 |
| zoo_reflex_rc166 | 50.0% [.43, .57] | 53.5% [.47, .60] | +4.62 | -1.34 |
| monster_rule_expert | 66.0% [.59, .72] | 44.5% [.38, .51] | +3.04 | +1.87 |
| zoo_reflex_h1test | 77.0% [.71, .82] | **100.0%** [.98, 1.00] | +5.33 | +17.57 |

**OVERALL: 1373/2000 = 68.6%** [0.666, 0.706]

### Submission tier (pm29 확정)

| Tier | Agent | 사용 목적 | 근거 |
|---|---|---|---|
| 1 (primary) | **rc166** | Code 40pt (baseline WR) | 98.5% vs baseline 200g |
| 2 (tournament) | **rc-tempo β** | Extra 30pt (H2H strength) | 71% H2H vs rc82, 100% vs h1test distant |
| fallback | rc82 | Tournament backup | 97% baseline WR, strong composite |

---

**Last updated:** 2026-04-20 pm28 END — **rc-tempo V0.1 설계 완료 (미구현) + Server Order 4 (A4) 분석**:
- 🏁 **rc-tempo V0.1 design lock** — deterministic weighted-orienteering paradigm, capsule-assisted return. 설계만 완료, 구현은 pm29 착수.
- 📐 **핵심 insight (user)**: Scared 40-move 창을 "개수 max" 가 아닌 **"위험 food 우선"** (dead-end, funnel, 고립) weighted DP. 쉬운 food는 Agent B + 후속 trip에서.
- 🔢 **DP 실측 (defaultCapture 0.12s / distantCapture 0.22s / strategicCapture 2.32s)** — 모두 15s init 예산 내.
- 🎯 **Ceiling per trip**: default 7 / distant 9 / strategic 13 food (+Agent B swarm +entry = 12-21 food/trip deposit).
- 🔧 **V0.1 scope lock**: 1-capsule 맵 only (default, distant, strategic). 나머지 rc82 fallback.
- 📄 **Design doc**: `.omc/plans/rc-tempo-design.md` (READ FIRST in pm29).
- 🔄 **Server Order 4 (A4)**: fitness 0.968 peak (A1 1.065 미달), 건강한 수렴 (gen15 peak + 4 gen stagnation). 서버 root unarchived, pm29 cleanup.
- ⚠️ **your_best/baseline{1,2,3}.py 전부 아직 DummyAgent** — M7 flatten_multi 사용해 rc166/rc-tempo 결정 후 populate.

---

**pm27 END:** — **NEW PEAK rc166/rc177 = 98.5% 200g + 11 new Tier 2/3 paradigms + M7 flatten_agent WORKING**:
- 🏆 **rc166** (rc82 if score≥3 else rc16) and **rc177** (rc82 if score≥2 else rc16) both **197/200 = 98.5%** Wilson 95% [0.957, 0.995] → **co-peak** at 200g.
- **rc166 vs rc177 H2H = 100-0-0 Red** → rc166 strictly better despite identical baseline WR. **rc166 primary submission candidate**.
- **rc82 vs rc166 H2H = 29-0-31 Blue** → rc82 dominates direct combat (pm26 finding confirmed, rc82 = tournament candidate).
- **Threshold sweep** (rc160/rc177/rc166/rc178/rc179 = 97.5/98.5/98.5/95/98) → sweet spot at ≥2 / ≥3.
- **11 new Tier 2/3 paradigms** implemented: Tier 2 rc25 (Quiescence 98%), rc37 (Novelty 94%), rc38 (MAP-Elites 87%), rc41 (SARSA 93%), **rc47 Engine αβ 95% 200g [0.910, 0.974]**, rc49 (SIPP-lite 95%). Tier 3 rc58 (Coord-Graph 87%), rc59 (Reward Machines 90%), rc60 (Difference Rewards 90%), rc65 (ToM L2 74%), rc75 (MAML/Reptile 90%).
- **7 drops**: rc26 (too slow), rc35/rc36 (rollout opp-model bug), rc42/rc43 (Double-Q/TD failed), rc67 (stochastic RM+ broken), rc185 (switch continuity issue).
- **M7 flatten_agent WORKING** via `experiments/flatten_multi.py` — recursive dep resolution, strips zoo_* imports keeping stdlib nested imports, injects evolved SEED_WEIGHTS. Parity verified: flat_rc166 98% 100g vs original 98.5%/200g.

---

**pm26 END:** — **SWITCH BREAKTHROUGH: rc160 = 97.5% [0.944, 0.990] NEW PEAK**:
- **🏆 rc160 (`if score >= 1: rc82 else rc16`)** 200g = 195/200 = **97.5%** Wilson [0.944, 0.990]. +0.5pp over rc82 solo (97%).
- **rc159/rc166/rc167** = 99% at 100g (CI overlaps rc160). Simplest 2-way wins.
- **rc152** 4-way (rc82 / rc16 small-lead / A1 / rc52b): 98%.
- **rc148/rc149/rc151/rc156** score/phase variants: 96-97%.
- **Learning-tier** (rc52b 92%, rc46 91%, rc22 88%, rc52 90%) — below switch family.
- **REINFORCE regressed twice** (rc52c aggressive 86%, rc52d conservative 86%) — rc52b is lucky single-run sample.
- **40g "100%" claims CORRECTED (100g authoritative)**: rc82 97%, rc16 92%, rc105 95% — all pm23/pm24 champions are 90-97%, not 100%.
- **Pattern laws** (pm26 distilled): (1) asymmetric direction matters; (2) rc16 must handle tied; (3) threshold flat 1-3; (4) extra slots don't help; (5) chase-agent choice low-impact.
- **Submission candidate**: DUAL TRACK:
  - **rc160** (baseline-optimal, 97.5% 200g) for code 40pt — simplest 2-way switch
  - **rc82** (tournament-optimal, head-to-head 32-11-17 vs rc160) for extra 30pt — composite champion
  - **Head-to-head critical finding (pm26 END)**: rc82 beats rc160 2.9:1. Switch-based rc160 exploits baseline-specific weaknesses; doesn't generalize. Phase 4 round-robin needs rc82.
- Server Order 4 unreachable (SSH timeout).
**Update protocol:** revise this file at end of each session and after each milestone (per `wiki/convention/session-log-protocol`).

## 🚨 pm25 entry point (authoritative)

→ **`.omc/plans/rc-pool.md`** — **80 round-robin candidates 마스터 문서** + pm23/pm24/pm25 변경 로그.
→ **pm25 session log** — `.omc/wiki/2026-04-19-pm25-rc22-policy-distillation-first-tier3-pass.md`.
→ **pm24 session log** — `.omc/wiki/2026-04-19-pm24-mega-sprint-68-rc-8-champions.md`.
→ **pm23 session log** — `.omc/wiki/2026-04-19-pm23-rc02-rc08-tier-1-candidate-sprint.md`.

## pm25 headline (rc22 Tier 3 FIRST pass)

**rc22 Policy Distillation** — numpy MLP (20→32→1, ~2K params) distilled from rc82 teacher.
- **Data**: 100 games rc82 vs baseline → 59,828 (φ(s,a), teacher_action) records. Teacher collected at 96% WR.
- **Training**: 50 epochs, SGD+momentum lr=1e-3, val_acc 90.3% (info-bottleneck ceiling).
- **HTH**: 88/100 = **88%** vs baseline Wilson [0.802, 0.930], 0 crashes. Beats A1 (82.5%).
- **Files**: `experiments/distill_rc22.py`, `minicontest/zoo_distill_collector.py` (teacher+logger), `minicontest/zoo_distill_rc22.py` (student, numpy-only inference).
- **Strategic value**: First architecturally different Phase 4 pool member (neural vs hand-rule) → adds diversity. Demonstrates Tier 3 feasibility.

## pm24 headline (+16 rc total, +14 pass; 3 new 100%-WR)

pm24 Batch A+B+C+D 40-game HTH (20 Red + 20 Blue vs baseline):
| Agent | Red | Blue | Total | WR | Verdict |
|---|---|---|---|---|---|
| **rc82** rc29+rc44 combo | 20/20 | 20/20 | 40/40 | **100%** | 🥇 PASS |
| **rc84** Role-asym rc82 OFF + rc02 DEF | 18/20+2T | 20/20 | 38/40+2T | **95%+** | ✅ PASS |
| **rc86** rc82 + rc48 WHCA* stack | 18/20+1T | 20/20 | 38/40+1T | **95%+** | ✅ PASS |
| **rc21** Layout clustering (weight mult) | 20/20 | 18/20 | 38/40 | **95%** | ✅ PASS |
| **rc81** Role-asym rc16 OFF + rc02 DEF | 17/20+3T | 20/20 | 37/40+3T | **92.5%+** | ✅ PASS |
| **rc29** Search-depth disruption | 20/20 | 17/20 | 37/40 | **92.5%** | ✅ PASS |
| **rc44** State-conditioned stacking | 19/20 | 18/20 | 37/40 | **92.5%** | ✅ PASS |
| **rc83** 5-way multi-champ ensemble | 17/20 | 19/20 | 36/40 | **90%** | ✅ PASS |
| **rc48** WHCA* teammate deconflict | 19/20 | 17/20 | 36/40 | **90%** | ✅ PASS |
| **rc50** Opening book (15-turn) | 18/20 | 18/20 | 36/40 | **90%** | ✅ PASS |
| **rc07** Kamikaze decoy | 20/20 | 16/20 | 36/40 | **90%** | ✅ PASS |
| **rc85** Capsule-timing gate | 17/20 | 18/20+1T | 35/40+1T | **87.5%+** | ✅ PASS |
| **rc31** Kiting / aggro-juggling | 17/20 | 18/20 | 35/40 | **87.5%** | ✅ PASS |
| **rc28** Boids anti-clump | 14/20 | 19/20 | 33/40 | **82.5%** | ✅ PASS (ties A1) |
| **rc30** Particle-filter blinding | 8/20 | 2/20 | 10/40 | **25%** | ❌ DROP |
| **rc34** Pavlovian feinting | 0/20 | 0/20 | 0/40 | **0%** | ❌ DROP |

**pm24 cumulative rc count**: 31 new rc (pm23 = 16 pass + 1 drop rc18; pm24 = 14 pass + 2 drop rc30/34).
**Pool size for Phase 4**: 31 rc + A1/O2/O3/(O4) + D1/D2/D3/D13/T4/T5 = ~38 candidates.
**3 champions at 100% WR**: rc02 (Tarjan AP), rc16 (Voronoi), rc82 (rc29+rc44 combo).

**Insights (pm24)**:
1. **Stochastic top-K injection catastrophic** — rc29 (threat-conditioned REVERSE) passes, rc34 (time-conditioned blind) fails.
2. **Orthogonal overlays compose** — rc82 (rc29+rc44) ties the 100% ceiling. Tactical + strategic layers stack.
3. **Role-asymmetric design viable** — rc84 (rc82+rc02) 95%+, rc90 (rc82+rc32) **97.5%** best asym so far. Pincer defender > AP defender for this composition.
4. **Layout conditioning helps** — rc21 95% with ×1.10/×0.90 class multiplier alone.
5. **Ensemble dilution** — rc83 (5-way vote) 90% < rc82 solo 100%. Voting over weaker members pulls top signal down.
6. **Stacked overlays preserve quality** — rc86 (rc82+rc48) 95%+. Sequential override (apply strongest, then filter) doesn't dilute.
7. **Narrow fire-conditions essential** — rc87 (far-food always-on when safe) 55% and rc89 (dead-end avoid 5-cell) 55%. Overlays that fire too often destroy A1's tuned behavior. Successful overlays (rc02 invader-visible, rc29 herded, rc48 collision) all have tight triggers.
8. **2-ply lookahead modest gain** — rc88 80%, better than A1 82.5%? Actually below. Self-play lookahead without opponent model doesn't always help reflex policies.

## pm23 headline (rc02-rc08 sprint)

## pm23 headline (rc02-rc08 sprint)

40-game HTH (20 Red + 20 Blue vs baseline):
| Agent | Red | Blue | Total | WR | Notes |
|---|---|---|---|---|---|
| **rc02** Tarjan AP | 20/20 | 20/20 | **40/40** | **100%** 🥇 | Beats A1 by ~17.5pp |
| **rc03** Dead-end trap | 20/20 | 18/20 | 38/40 | 95% | — |
| **rc04** Hungarian v2 | 19/20 | 16/20 | 35/40 | 87.5% | v1 failed 0/4, v2 fix shipped |
| **rc05** Prospect-theory | 18/20 | 15/20 | 33/40 | 82.5% | Matches A1 |
| **rc06** Border denial | 15/20 | 15/20 | 30/40 | 75% | — |
| **rc08** Dual-invader lane | 18/20 | 19/20 +1T | 37/40 +T | 92.5%+ | — |
| **rc09** 24-dim features | 20/20 | 17/20 | 37/40 | 92.5% | — |
| **rc11** Border juggling | 18/20 | 17/20 | 35/40 | 87.5% | — |
| **rc15** A1+rc02+D13 ensemble | 18/20 | 20/20 | 38/40 | 95% | — |
| **rc16** Voronoi territory | 20/20 | 20/20 | **40/40** | **100%** 🥇 | Tied with rc02 |
| **rc17** Influence map | 16/20 | 18/20 | 34/40 | 85% | — |
| **rc19** Phase-conditional | 19/20 | 18/20 | 37/40 | 92.5% | — |
| **rc27** Stigmergy | 16/20 | 19/20+1T | 35/40+T | 87.5%+ | — |
| **rc32** Pincer | 19/20 | 20/20 | 39/40 | **97.5%** 🥇 | 3rd highest |
| **rc33** Persona-shift | 18/20 | 17/20 | 35/40 | 87.5% | — |
| **rc45** Weighted ensemble | 20/20 | 17/20+1T | 37/40+T | 92.5%+ | — |
| **rc46** K-centroid classifier | 17/20 | 16/20 | 33/40 | 82.5% | — |
| **O3** (Order 3 HOF) | — | — | — | 78% (HTH) | New HOF wrapper |
| A1 reference (pm20) | | | — | **82.5%** | — |

**Autopilot** cron `fc249310` re-armed for this session. Server Order 3 Phase 2b gen 7 observed (best=0.788), ~13 gens to Order 3 complete, ETA ~12:30 KST 2026-04-19.

## pm21 headline (autopilot gains)

- ✅ Order 2 complete: baseline Wilson LB 0.755 (A1 0.728). Marginal improvement, CI overlap → **A1 kept** as submission; `zoo_reflex_O2.py` added to Phase 4 pool
- ✅ `experiments/make_hof_wrapper.py` + dynamic pool in `launch_orders_34.sh` (HOF auto-detect)
- ✅ Autopilot 30-min cron design + `.omc/plans/autopilot-server-pipeline.md` — rule-based S0→S1→S2, **Phase 4 is manual per user directive**
- 🔄 Order 3 running, ETA ~2026-04-19 09:15 KST; Order 4 auto-launch after (pm22 cron)

## pm20 roadmap pointer (historical)

→ **`wiki decision/pm20-expanded-roadmap-17-tasks-3-axis-development-ccg-enhanced`** for full 17-task plan.

## Headline

40-game reverification with same `-b baseline -n 10` protocol for all candidates. **Prior 10-game judgements were undersampled and partly wrong**. Canonical table (vs `baseline.py`, defaultCapture, 40 games):

| Agent | W | L | T | Win% | Loss% | Tie% | Net |
|---|---|---|---|---|---|---|---|
| `zoo_reflex_tuned` (control) | 0 | 0 | 40 | 0% | 0% | **100%** | 0 |
| `zoo_reflex_h1test` (both-OFFENSE) | 14 | 14 | 12 | **35%** | 35% | 30% | 0 |
| `zoo_reflex_h1b` (role-split, ~~REJECTED~~ RESURRECTED) | 12 | 4 | 24 | 30% | **10%** | 60% | **+8** |
| `zoo_reflex_h1c` (capsule-exploit, new run) | 8 | 2 | 30 | 20% | 5% | 75% | +6 |
| `zoo_reflex_h1c` (pm3 earlier run) | 4 | 4 | 32 | 10% | 10% | 80% | 0 |

Key reversals: (1) **H1b was wrongly rejected** — 40-game sample gives 30% win with 10% loss (lower risk than H1). (2) **H1 still leads on raw win% = grading metric** at 35%, but **cannot clear 51%** (14/40 vs p=0.51: z=-2.07, p≈0.02 → single-dict tuning definitively insufficient for code 40pt). (3) **H1c variance large between runs** (10%→20% across two identical 40-game invocations); 40 games still under-powered for <5%-point CIs. (4) **ReflexTuned 100% tie** confirms original deadlock is structural and reproducible. (5) **`your_baseline1/2/3.py` are DummyAgent (random) copies** — capture.py 4-loop is actually a "vs [random×3, baseline×1]" grading protocol for `output.csv`; before M8 submission we must populate them with our own variants. Next: pivot to **M4 infra patches + M6 evolution** as the only path to 51%.

## Milestone progress (M-series from `.omc/plans/STRATEGY.md` §10)

| # | Milestone | Status | Verification | Commit |
|---|---|---|---|---|
| Plan | Ralplan + Architect/Critic + Scientist/Codex/Gemini consensus | ✅ APPROVED | 6 reviewers | `8c9fe66` |
| M1 | `CoreCaptureAgent` base + dummy smoke | ✅ Done | 10/10 exit 0, 0 crash | `42e8215` |
| M2a | Shared `zoo_features.py` + 4 reflex variants | ✅ Done | 20/20 exit 0, 0 crash, all tied | `372f15f` |
| M2b | 3 minimax variants (d2, d3_opp, expectimax) | ✅ Done | 4/4 exit 0 (partial smoke) | `927b4ce` |
| M2c | 3 MCTS variants (random/heuristic/q_guided) | ✅ Done | 3/3 exit 0 | `9e278b4` |
| M2d | 2 approxQ variants (v1, v2_deeper) | ✅ Done | 6/6 exit 0 | `927b4ce` |
| M3 | 3 hand-tuned monster agents | ✅ Done | 3/3 exit 0 | `9e278b4` |
| **M3-verify** | Smoke for skipped MCTS + monsters | ✅ Done | 7/7 exit 0 | `9e278b4` |
| **H1-verify** | Deadlock-hypothesis validation (zoo_reflex_h1test) | ✅ Done | 3W/2L/5T in 10 games | `a512863` |
| **H1b-verify** | Role-split variant test (zoo_reflex_h1b) | ✅ Done — RESURRECTED | 12W/4L/24T in 40 games (30% W / 10% L, highest net +8) | (uncommitted) |
| **H1c-verify** | Capsule-exploit variant (zoo_reflex_h1c) | ✅ Done — below H1 | 8W/2L/30T in 40 games (20% win, but pm3 run had 10% — variance large) | (uncommitted) |
| **Reverify pm4** | 40-game apples-to-apples for H1/H1b/H1c + ReflexTuned control | ✅ Done | Canonical table in Headline; single-dict saturated | (uncommitted) |
| **M4a-infra** | `tournament.py` CSV-append + fsync + `--resume-from` (autopilot pm5) | ✅ Done | 4/4 QA tests + code-reviewer APPROVED (2 🟡 orthogonal scope-out, 3 🟢 nit) | `4dcbced` |
| **M4-v1** | First tournament run pm6: 15 agents × defaultCapture × seed 1 | ✅ Done (weak signal — superseded by v2) | 210 matches / 0 crashes / 7m10s wall; **95.2% tie** (seed lock) | `4dcbced` |
| **M4c-1-infra** | `run_match.py` drop `--fixRandomSeed` + route seed via `-l RANDOM<seed>` (autopilot pm7) | ✅ Done | variance smoke 5 reps → 3 distinct outcomes; code-reviewer APPROVED (0 🔴 2 🟡 maintainability 3 🟢 nit) | (uncommitted) |
| **M4-v2** | Re-tournament post-M4c-1: 15 agents × (defaultCapture + RANDOM) × seeds 1 2 = 840 games | ✅ Done | 840 matches / 0 crashes / 32m28s wall; **tie 90.6%** (down from 95.2%); h1test 50% vs baseline (ELO 1584, #2 overall); h1b 37.5% (#4); h1c 12.5% (map-sensitive); all minimax/expectimax/monster tie baseline | (uncommitted CSV) |
| **M4b-1-infra** | `evolve.py` fail-fast (remove `NotImplementedError` swallow) | ✅ Done | loud raise verified | `b854f16` |
| **M4b-2-infra** | Weight-override protocol (run_match `--red-opts` + zoo_core loader + zoo_reflex_tuned createTeam) | ✅ Done | 5 unit tests + e2e (override → Red +2 vs baseline; seed-weight → Tie) | `b854f16` |
| **M4b-3-infra** | `evaluate_genome()` full implementation (decode, dump, matches, aggregate, cleanup) | ✅ Done | h1test genome smoke → `{pool_win_rate:0.5, crash_rate:0.0, ...}` | `b854f16` |
| **Pre-α** | Baseline measurement + STRATEGY §6 gap analysis + T1-T4 test plan + parallelization ADR | ✅ Done | 7.74s/match empirical; 4 wiki pages ingested | `6548098` |
| **α-1** | genome-level ProcessPoolExecutor in run_phase (workers=8) | ✅ Done | 8-genome smoke 27.3s (~9× speedup) | `b625dc8` |
| **α-2** | `--resume-from <dir>` checkpoint + forward-compat `best_ever_*` field | ✅ Done | T4 PASS: gen 0 mtime unchanged, gens 1/2 regenerated | `ad56ebe` |
| **α-3** | `--opponents` / `--layouts` CLI → run_phase → evaluate_genome | ✅ Done | 2-opp round-trip smoke 54s | `b625dc8` |
| **α-4** | T1-T4 verification (same-genome equivalence / parallel ranking / crash-robust / resume) | ✅ Done | T1 PASS (90s), T2 PASS (49s), T3 PASS (0.9s), T4 PASS (pm11) | (this commit) |
| **α-5** (optional) | `--time-limit` pass-through for truncated eval (first 3 gens, 600-move) | ❌ PERMANENTLY SKIPPED | pm13 M4b-4 data: gens 0/1/2 wall 760/730/754s (±4%) — "initial gens timeout-dominated" assumption empirically FALSE | — |
| **M4b-4** | M5 dry-run: 3 gens × 8 pop × 24 games/opp × 3 opps × 2 layouts | ✅ Done | 37.4min wall total (per-gen ~750s); per-match 10.5s (Stage 1 was 7.74s, +36% 8-worker contention); gen 1 best=0.101 (signal exists), gens 0/2 all-zero (small-sample noise); stagnation reached 3 | (pm13) |
| **α-post A (4-loop bypass)** | `experiments/single_game.py` wrapper + `run_match.py` refactor to skip `capture.py.__main__`'s 4-loop | ✅ Done | 4.55× per-match speedup (1.70s); T1-T3 all PASS post-A; M6 budget restored to ~23-32h | (pm14) |
| **M6-a v1** (pm14) | Phase 2a smoke v1: zero-init Gaussian → all-zero fitness | ❌ Failed | 2h23m wasted; root cause diagnosed (init_mean=0 cold start) | (pm14) |
| **M6-a.1 smoke** (pm16) | 4 gens × 20 pop × 12 games × 3 dry opps × defaultCapture, `--init-mean-from h1test` + elitism | ✅ **PASSED** | 17m21s; trajectory 0.160→0.273→0.323→**0.774** (4.8×); snr stable 1.1+ (no drift); real CEM learning confirmed | — |
| **M6-a.2** | Full Phase 2a smoke: 2-5 gens × 40 pop × 264 games × 11 opps × 2 layouts | ⏳ Replaced by pm17 6-phase plan (see Phase 2 below) | (pm16 decision deferred) | — |
| **pm17 plan** | 6-phase performance-max pipeline (Phase 1 Mac infra → Phase 2 server evolve queue → Phase 3 Mac hybrid → Phase 4 server tournament → Phase 5 multi-seed validation → Phase 6 submission) | ⏳ Pending — start in NEXT session | full plan in wiki `decision/next-session-execution-plan-performance-max-6-phase-pipeline` | — |
| **Phase 1: B1 features + C4 MCTS calibration** | Mac coding: +3 features (`f_scaredGhostChase`, `f_returnUrgency`, `f_teammateSpread`), MCTS time-budget polling | ✅ Done (pm18) | B1: 20-dim shape check PASS + `zoo_reflex_tuned` smoke 2.1s Tie crashed=false; C4: 3 MCTS files time-polled 0.8s/move, `zoo_mcts_q_guided` smoke 4:43 full 1200-move game Tie crashed=false | `a1b5569` (C4), `379dc74` (B1) |
| **Phase 2: 7-8 candidates evolve queue** | Server sequential: A1 baseline 17-dim (control) → A1/A2/A5 + B1 reflex variants → C1/C3/C4 + B1 paradigm variants. All `--master-seed 42` fixed | **A1 ✅, Order 2 ▶️ running (pm19)** | A1 completed 04:19 pm19 (18.5h wall). Final best_ever_fitness 1.065 at 2b_gen013. HTH battery (340 games, 30s wall) **baseline 158/200=79.0% Wilson[.728,.841] PASS**, monster_rule_expert 46/60=76.7%, zoo_reflex_h1test 37/40=92.5%, zoo_minimax_ab_d2 33/40=82.5%, 0 crashes. **A1 is grading-gate-safe champion.** A1 artifacts archived to `experiments/artifacts/phase2_A1_17dim/`. Order 2 (A1+B1 20-dim, same h1test init, same 11-opp pool, --master-seed 42) launched 11:55 pm19. Expected 18h wall, CEM w/ 20-dim may exceed A1's 1.065 via B1 features or confirm diminishing returns. | A1: `experiments/artifacts/phase2_A1_17dim/final_weights.py` (fitness 1.065); Order 2 log: `logs/phase2_A1_B1_20dim_20260417-1155.log` |
| **A1 HTH validation (pm19)** | 4-opp battery on server via `experiments/hth_battery.py` | ✅ Done | 340 games / 30s / 0 crashes. Baseline WR **79.0%** Wilson LB 0.728 ≫ 0.51 grading threshold; monster/h1test/minimax all ≥76%. M6 §10.6 exit tests: (a) ✓ (fitness 9.5× over gen 0), (c) ✓ (monster_rule_expert 76.7%), (d) marginal (19/30 snr≥1.0). CEM-evolved weights (negative f_onDefense, negative f_numCarrying, capsule-magnet) are NOT an overfit bug — they encode a "1-food-sprint-home" strategy that convincingly beats reflex-heavy opponents including territorial defender. | `714e589` infra; CSV at `experiments/artifacts/phase2_A1_17dim/hth_A1_17dim.csv` |
| **CCG plan review (pm19)** | Codex + Gemini critical review of pm17 plan vs A1 results | ✅ Done | Both advisors independently recommended "validate A1 first, consider dropping Orders 5-8". User re-directed to performance-max given 10-day budget; resumed Phase 2 queue with Orders 2-4 (skip minimax/MCTS/expectimax containers per both advisors' low-ROI judgment). Dead PARAMS strip (Codex recommendation, 41% genome noise) DEFERRED for apples-to-apples comparison with A1. | — |
| **Orders 2-4 diversification flaw (pm19 late)** | pm17 plan's Orders 3/4 are BIT-IDENTICAL to Order 2 as currently configured — _H1B_FEAT_SEED = _H1TEST_FEAT_SEED + same master-seed + same pool → same sampling path | 🔴 pm20 RESOLVE | Fix options: (a) different --master-seed per Order, (b) expand --init-mean-from with "a1" option, (c) HOF pool rotation (create zoo_reflex_A1.py wrapper, Order 3+ includes it as opponent). Combo (a+c) preferred. User's AlphaZero intuition correct — needs implementation. | See SESSION_RESUME.md §"pm20 KEY DECISIONS" |
| **CCG hybrid paradigm analysis (pm19)** | Path 1 (A1 only) vs Path 2 (MCTS+minimax full hybrid) vs Path 3 (MCTS offense + reflex defense) | ⏳ pm20 DECISION | Codex: Path 3 tightly-scoped with hard kill. Gemini: Stick with Path 1, polish report. Convergence: Path 2 drop. Gain expected +1-4pp modest. Claude lean toward Codex given user's performance-max directive. Prereq: M7 flatten A1 first (submission candidate lock). | wiki `decision/pm19-ccg-hybrid-paradigm-analysis-path-1-vs-2-vs-3-mcts-offen` |
| **Phase 3: D-series hybrid** | Mac code-level enhancements applied per champion: D1 role-swap, D2 capsule timing, D3 endgame mode → 4 variants per champion | ⏳ Pending | ~6-8h Mac | — |
| **Phase 4: Round-robin ELO** | 28-40 candidates × 5 layouts × 5 seeds tournament on server | ⏳ Pending | ~2-3h server | — |
| **Phase 5: Top-5 multi-seed final validation** | Server 200-game sweep × 10 seeds + Mac re-validation (cross-platform reproducibility) | ⏳ Pending | ~2-3h | — |
| **Phase 6: M7 flatten + M8 + M9 report + M10 zip** | Mac flatten_agent AST + your_baseline1/2/3 populate + report + packaging | ⏳ Pending | ~6-8h Mac | — |
| **M4c-2-infra** | `run_match.py` `start_new_session=True` + `killpg` on timeout | ⏳ Pending (5min) | — | — |
| M5 | Evolution dry run (N=8, G=2) | ⏳ Pending | ~13min parallel; validates CEM loop end-to-end | — |
| **M6-a** | Phase 2a **smoke** (2 gens × 40 pop, 3-opp dry pool) — Go/No-go check for full 2a | ⏳ Pending | ~1.5h parallel; pass = best_ever > h1test seed fitness | — |
| **M6-b** | Phase 2a **full** (gens 3-10 with resume from M6-a) | ⏳ Pending | ~4h parallel; emit 2a elite mean for 2b init | — |
| **M6-c** | Phase 2b **early** (gens 11-15, split W, monster pool active) | ⏳ Pending | ~2.75h parallel; monster_rule_expert in pool | — |
| **M6-d** | Phase 2b **late** (gens 16-30) + `final_weights.py` emit | ⏳ Pending | ~8.25h parallel; best-ever across both phases | — |
| M7 | select_top4 + flatten + populate slots | ⏳ Pending | — | — |
| M7.5 | Time-budget calibration | ⏳ Pending | — | — |
| M8 | Final `output.csv` for report | ⏳ Pending | ~30min; populate `your_baseline{1,2,3}.py` first | — |
| **M9-a** | Report sections: Intro (8pt) + Methods (20pt) | ⏳ Pending | ~1.5h; ICML template | — |
| **M9-b** | Report Results (20pt) + ablation figures (ELO curves, win-rate tables) | ⏳ Pending | ~1.5h; uses M4-v2 + M6 artifacts | — |
| **M9-c** | Report Conclusion (12pt) + revise pass | ⏳ Pending | ~1h | — |
| M10 | Submission packaging (zip, sha256) | ⏳ Pending | ~15min | — |

**Tier policy (applies to any 1h+ milestone): each sub-tier is an independent resumable unit with a Go/No-go gate at the end. User decides after each gate whether to continue, pause, or pivot. No milestone commits us to more than ~4h of uninterrupted work.**

## Compute dispatch policy (pm17 — remote server provisioned)

| task class | venue | command pattern |
|---|---|---|
| Quick smoke (pop≤4, 1 gen, ≤10 min) | **Mac** | `.venv/bin/python experiments/evolve.py …` |
| Mid tuning (pop 8-16, 2-5 gen) | Either | Mac if convenient |
| **Heavy evolve (pop≥16, ≥5 gen, ≥30 min)** | **Server (jdl_wsl tmux work)** | `ssh jdl_wsl "tmux send-keys -t work '… 2>&1 \| tee logs/<name>.log' Enter"` |
| Large tournament (≥100 matches) | Server | same pattern |
| Result analysis / report writing | **Mac** | inline Claude context |

Server: AMD Ryzen 9 7950X (16 phys / 32 threads), 128 GB RAM, WSL2 Ubuntu, `~/projects/coding-3`. Measured 2.25× faster than Mac M3 Pro on `evolve` `pop=16 workers=16`. Full env doc: wiki `environment/remote-compute-infra-wsl2-ryzen-7950x-server-jdl-wsl`. Dispatch directive in project memory (high priority).

⚠️ **Cross-platform fitness reproducibility imperfect** — same `--master-seed` on Mac vs server can yield different best/mean. Use server for fitness ranking; verify the *final* `your_best.py` win-rate on Mac before submission.

M6 budget on server (Option A bypass + 2.25× server):
- Phase 2a 10 gens × 40 pop × 264 games / 16 workers ≈ **~5 h**
- Phase 2b 20 gens × 40 pop × 224 games / 16 workers ≈ **~5-6 h**
- **M6 total ≈ 10-11 h** — overnight on the server.

## Critical observations / blockers

🟢 **CAPTURE.PY 4-LOOP PROTOCOL — DECODED 2026-04-15 pm4** — `capture.py:1054-1074` loops over `lst=['your_baseline1','your_baseline2','your_baseline3','baseline.py']` to build `output.csv` for the assignment's required comparison report. `your_baseline1/2/3.py` are currently **identical copies of myTeam.py = DummyAgent (random actions)**. So `-n 10 -b baseline` = 40 games all vs baseline.py; bare `-n 10` = 10 vs random ×3 blocks + 10 vs baseline. Before M8 submission, we must populate `your_baseline1/2/3.py` with our own variants (per CLAUDE.md spec) so `output.csv` shows a meaningful 4-way comparison for the report.

🟡 **DEADLOCK — STRUCTURAL, CONFIRMED 2026-04-15 pm4** — `zoo_reflex_tuned.py` (untouched seed weights) produces **0W/0L/40T** vs baseline across a 40-game reverification. The original deadlock claim (0/47 in M1-M3) is exactly reproducible. Weight patches in H1/H1b/H1c break the deadlock (tie% drops from 100% to 30-75%), but none clear 51% win rate.

🔴 **SINGLE-DICT TUNING STATISTICALLY INSUFFICIENT (2026-04-15 pm4)** — H1 14/40 at p=0.51 gives z=-2.07 (p≈0.02). We can reject 51% with 95% confidence for H1 on baseline. H1b (12/40) and H1c (4-8/40) are further below. No pure weight-scaling of `SEED_WEIGHTS_OFFENSIVE` / `SEED_WEIGHTS_DEFENSIVE` will clear grading threshold. Policy-level change required: coordination protocol, role swap, search-based planning, OR **M6 CEM evolution over wider search space**. `evolve.py:140-142` NotImplementedError fix is now ON the critical path.

🟡 **H1b RESURRECTION — pm2 rejection overturned** — The pm2 session concluded H1b "rejected" based on a single 10-game block (1W/2L/7T). 40-game reverification shows 12W/4L/24T (30% W, 10% L, **+8 net** — highest among all diagnostics). H1b has the lowest risk profile (4 losses vs H1's 14). For tournament (diverse opponents), a low-loss / moderate-win variant might rank better than H1's high-variance profile. Keep H1b as a live seed variant for M6.

🔴 **Evolution silent-failure risk (`evolve.py:140-142`)** — `evaluate_genome` raises `NotImplementedError`; the enclosing try/except swallows it into `f=0.0`. A 20h M6 campaign would "complete successfully" and emit `final_weights.py` of random noise. MUST fix before any M5 dry-run. See wiki `debugging/experiments-infrastructure-audit-...`.

🟢 **Seed workaround applied & validated (pm7 autopilot)** — `run_match.py` no longer passes `--fixRandomSeed` (which hardcoded `random.seed('cs188')` in capture.py, dropping the seed VALUE and causing pm6's 95.2% tie lock); seed is now routed through the `-l RANDOM<seed>` layout-generator form. Variance smoke 5 reps produced 3 distinct outcomes. M4-v2 tie rate dropped 95.2% → 90.6% with real cross-layout signal. Code-reviewer APPROVED (0 🔴). Trade-off: named-layout reproducibility lost, but usable ELO restored.

🟢 **M6-a.1 smoke confirms CEM learns (pm16)** — 4 gens × 20 pop × 12 games × 3 dry opps on defaultCapture, `--init-mean-from h1test` + `population[0]=mean` elitism. best_fitness ascended **0.160 → 0.273 → 0.323 → 0.774** (4.8× over gen 0, ~82% win rate against the dry pool at fitness 0.774). snr stable at 1.1+ (STRATEGY §6.3 drift alert threshold cleared every generation). mean_fitness rose 0.009 → 0.171 (population centroid approaching elite region). σ decayed 14.7 → 6.9 on key features (STRATEGY 0.9×/gen schedule holding). Mean_genome shows CEM exploring AWAY from h1test seed — e.g. f_successorScore 100→113, f_bias 0→-6.9, f_distToFood 10→-0.9 — suggesting a *different* local optimum than the seed. Real-scale (M6-a.2 full) run to verify on the 11-opp pool.

🟢 **A1 17-dim full-scale evolution learning confirmed (pm18)** — Order 1 launched on server at 06:37; first 3 gens: best **0.112 → 0.181 → 0.483** (4.3× over gen 0), mean **0.007 → 0.026 → 0.099**, snr **0.61 → 0.91 → 1.10** (gen 2 crossed STRATEGY §6.3 threshold, stagnation_count reset to 0). gen 0 best=0.112 ≈ h1test seed fitness on the harder 11-opp pool (pool_wr ~0.2 minus stddev penalty). gen 2 best=0.483 suggests CEM discovered a ~48% pool-win-rate genome — meaningful learning. Wall **stable at 46.6-48.8 min/gen** (no ProcessPool ramp-up; this IS the per-gen cost). Re-estimation: Phase 2a ≈ 7.8h, Phase 2b ≈ 11h, **total ≈ 18-19h**, finish ETA ~00:40 next day — overnight viable but ~2× wiki's 10h estimate. Pool: `baseline×2 + zoo_reflex_{h1test,h1b,h1c,aggressive,defensive} + zoo_minimax_{ab_d2,ab_d3_opp} + zoo_expectimax + monster_rule_expert` (11 slots, MCTS excluded due to 120s run_match timeout — fixed for Order 2+ once ZOO_MCTS_MOVE_BUDGET override is added).

🟡 **Order 6 blocker — MCTS evolve container needs budget override (pm18)** — C4 set MOVE_BUDGET=0.80s for submission safety, but full 1200-move MCTS game wall ≈ 5 min >> run_match.py's 120s per-game timeout. Every MCTS-container training match would forfeit. Fix: add `ZOO_MCTS_MOVE_BUDGET` env var read at each `_mcts_search` / `_search` call (fallback to `MOVE_BUDGET`). Evolve training can then set `ZOO_MCTS_MOVE_BUDGET=0.1` via `run_match.py env=`, keeping submission behaviour unchanged. ~15 lines patch across 3 files. **Not a blocker for Order 1 (A1 currently running) or Orders 2-5 (reflex/minimax containers) — only Order 6 (C4+B1 MCTS container) is blocked.**

🟢 **M6 budget restored via 4-loop bypass (pm14 Option A)** — `experiments/single_game.py` imports `capture.readCommand` + `capture.runGames` directly and calls them from its own `__main__`; `capture.py`'s `__main__` block (which held the 4-loop) never executes. `capture.py` itself is untouched (CLAUDE.md compliant). Measured impact: **per-match wall 7.74s → 1.70s (4.55× speedup)**, overall T1-T3 wall 140s → 44s (~3.2× at test scale). T1 run A/B produced identical pool_win=0.25 confirming correctness. Re-extrapolated M6: Phase 2a **~8.5-12h**, Phase 2b **~14-20h**, **total ≈ 23-32h** — STRATEGY §6.6's 20h target in reach without scale-down. (D) hybrid is no longer needed; (B) scale-down kept as fallback only. M6-a smoke (Phase 2a, 2 gens × 40 pop, ~45-60min expected) is now cleanly launchable per tier policy.

🟢 **M4-v2 canonical ELO (pm7) — 15 agents × defaultCapture+RANDOM × 2 seeds × 1 rep = 840 games / 0 crashes / 32m28s wall**. Top-3 by ELO (all rankings relative, baseline as reference anchor):
| Agent | ELO | vs baseline (8g) | Win% | Net |
|---|---|---|---|---|
| baseline | 1610.7 | — | — | — |
| **zoo_reflex_h1test** | **1584.6** | 4W/3L/1T | **50%** | +1 |
| zoo_reflex_h1c | 1532.5 | 1W/5L/2T | 12.5% | -4 |
| **zoo_reflex_h1b** | 1503.8 | 3W/1L/4T | 37.5% | +2 |
| (other reflex/minimax/expectimax/monster_rule) | ~1470-1490 | all 0W/0L/8T | 0% | 0 |
| zoo_approxq_{v1,v2_deeper}, zoo_dummy | ~1468-1479 | 0W/{7,8}L | 0% | -7 to -8 |

**3-way corroboration across pm4 (40g on defaultCapture) / M4-v1 (2g deterministic) / M4-v2 (8g varied)**:
- **h1test is the single-dict winner**: pm4 35% → v2 50% (RANDOM layouts amplify 2-OFFENSE formation's attack advantage). Preferred M6 evolution seed.
- **h1b is the robust runner-up**: pm4 30% → v2 37.5%. Consistent profile.
- **h1c is map-sensitive**: pm4 20% on defaultCapture, v2 12.5% when RANDOM layouts rotate capsule position — capsule-exploit fails outside favourable layouts.
- **All minimax/expectimax/monster_rule agents** are 0W/0L/8T vs baseline — tie-deadlock persists across layouts, confirming the structural issue is not layout-specific.
- **approxQ_{v1,v2_deeper} + zoo_dummy** are decisively the weakest (q-learning is UNLEARNED; require M6 evolution to become meaningful).

Artifact: `experiments/artifacts/tournament_results/m4_full_pm7_v2.csv`.

**Statistical caveat**: n=8 vs baseline per agent still wide CI. For 51% grading threshold at 95%: need ~100 games per agent. Either M4-v3 scale-up (same pipeline, more seeds/layouts, ~4h) OR M6 evolution which naturally runs thousands.

🟡 **MCTS/deep-minimax time budget issue (pm6)** — `zoo_mcts_heuristic` (MAX_ITERS=1000, no time polling) timed out 10/10 matches in M4 smoke. Excluded in M4-v1 along with `zoo_mcts_random`, `zoo_mcts_q_guided`, `monster_mcts_hand`, `monster_minimax_d4`. These 5 need MAX_ITERS/ROLLOUT_DEPTH reduction or real-time budget polling — deferred to M7.5 time calibration.

🟢 **Tournament CSV durability — CSV-append + fsync + resume DONE (pm5, autopilot run)** — `tournament.py` now writes each row with `flush()+fsync()` + parent-dir fsync on first-write (hard-crash survival on APFS). Added `_load_completed_keys()` helper + `--resume-from` CLI flag; (red,blue,layout,seed) dedup on resume. Code-reviewer APPROVED (0 🔴, 2 🟡 orthogonal, 3 🟢 nits). 4-test QA: fresh run (2 jobs, 7s, 0 crash), rerun (skip 2, nothing to do), partial skip (seed 1 2 → skip 2 + append 2, single header), regression after dir-fsync add (pass). See wiki session-log `2026-04-15-pm5-tournament-csv-append-resume-patch`. Residual (separate patch): sliding futures window for 85MB memory footprint at M6 scale.

🟡 **Tournament sliding futures window (deferred)** — `tournament.py:128` still eagerly submits all futures upfront; at M6 ~280K jobs this builds ~85MB of Future objects in parent. Not a correctness issue, but a parent-process memory concern. Patch: replace `{pool.submit(...): job for job in jobs}` one-shot dict with a sliding in-flight window of `workers × 4`. ~20 lines.

🟡 **BrokenProcessPool unhandled (deferred)** — single worker segfault still aborts the whole tournament. CSV-append lifeline means restart with `--resume-from` recovers progress, but a recovery loop around `ProcessPoolExecutor` would avoid manual babysitting. Audit wiki M3.

🟡 **Subprocess process-group leakage** — `run_match.py:80` lacks `start_new_session=True`; on TimeoutExpired, grandchildren can orphan. 1-line fix + `os.killpg` on timeout.

🟡 **Submission flatten not yet implemented** — `experiments/select_top4.py` is a skeleton; the `flatten_agent` function raises `NotImplementedError`. Required by M7. Plan has the recipe, but the AST-based concatenation logic needs implementation. Also: `FAMILY_MAP` missing entries for `zoo_dummy`, `zoo_reflex_h1test` (and future h1b/h1c) — silent drop risk during selection.

🟢 **Pre-α complete (2026-04-15 pm9)** — 5-stage preflight before Option α. **Stage 1 baseline**: 1 genome × 72 games sequential = 557s (7.74s/match); sequential extrapolation of M6 full = **186h (~8 days, non-viable)**; 8-way parallel target = 23.2h (≈ STRATEGY §6.6's 20h spec). **Stage 2 STRATEGY §6 gap analysis**: confirmed match (G11 CRN pairing, G3 stddev k=0.5, G8 Phase2→3 transition); scope-in for α (G4 CLI args, G12 ProcessPool, G10 truncated eval optional); scope-out (G1 20-dim claim → doc fix, G5 HALL_OF_FAME, G6 sequential-halving, G7 restart-random, G9 2-elitism — nice-to-have). **Stage 3** T1-T4 test plan (same-genome repeatability, parallel independence, crash isolation, resume integrity) → wiki `pattern/option-test-plan-t1-t4-...`. **Stage 4 ADR**: genome-level ProcessPoolExecutor (workers = min(cores-1, 8)); resume reads existing `{phase}_gen{N}.json` + `best_ever_*` forward-compat fields → wiki `decision/adr-evolve-py-parallelization-...`. **Critical path now**: implement α.

🟡 **Time calibration deferred to M7.5** — `MOVE_BUDGET = 0.80s` is a placeholder. Algorithmic bounds (`MAX_ITERS=1000`, `MAX_DEPTH=3`, `ROLLOUT_DEPTH=20`) are the actual time controllers during dev. Final values come from M7.5 measurement on dev hardware + `taskset/cpulimit` TA simulation.

## Asset inventory

**Source files (`minicontest/`):**
- 1 `zoo_core.py` (CoreCaptureAgent base)
- 1 `zoo_features.py` (17-feature extractor)
- 1 `zoo_dummy.py` (M1 smoke target)
- 4 reflex variants (`zoo_reflex_{tuned,capsule,aggressive,defensive}.py`)
- 3 H1-family diagnostic variants (`zoo_reflex_h1test.py` both-OFFENSE, `zoo_reflex_h1b.py` role-split, `zoo_reflex_h1c.py` capsule-exploit; kept as permanent ablation references)
- 3 minimax variants (`zoo_minimax_{ab_d2,ab_d3_opp}.py`, `zoo_expectimax.py`)
- 3 MCTS variants (`zoo_mcts_{random,heuristic,q_guided}.py`)
- 2 approxQ variants (`zoo_approxq_{v1,v2_deeper}.py`)
- 3 monster agents (`monster_{rule_expert,mcts_hand,minimax_d4}.py`)
- **Total: 21 agents (18 zoo incl. 3 H1-family + 3 monsters)**

**Pipeline scripts (`experiments/`):**
- `run_match.py` — single-game subprocess wrapper (CPU pin support)
- `tournament.py` — `ProcessPoolExecutor` round-robin (CRN pairing)
- `evolve.py` — CEM 2-phase driver (skeleton, depends on weight-override protocol)
- `select_top4.py` — ELO selection + family-floor + flatten (skeleton; flatten unimplemented)
- `verify_flatten.py` — AST + sha256 + import smoke gate

**Documentation:**
- `CLAUDE.md` — project rules (auto-loaded each session)
- `.omc/plans/STRATEGY.md` (746 lines) — full plan, ADR
- `.omc/plans/open-questions.md` (50 lines) — stretch / future items
- `.omc/wiki/` — long-term knowledge base
  - `reference/glossary-cs470-a3-project-terms`
  - `convention/session-log-protocol-multi-session-continuity-discipline`
  - `debugging/m3-smoke-deadlock-0-win-pattern-across-all-tuned-agents`
  - `debugging/experiments-infrastructure-audit-pre-m4-m6`
  - `session-log/session-2026-04-15-m3-smoke-completion-deadlock-observation`
  - `session-log/2026-04-15-pm-h1-deadlock-validation-confirmed`
  - `session-log/2026-04-15-pm2-h1b-rejected-strategic-replanning`
  - `session-log/2026-04-15-pm3-h1c-rejected-capture-py-4-loop-discovery`
  - `session-log/2026-04-15-pm4-40-game-apples-to-apples-reverification-h1b-redem`
- `docs/AI_USAGE.md` — per-milestone code change log (assignment requirement)
- `.omc/notepad.md` — priority context + working memory
- `.omc/STATUS.md` (this file)
- `.omc/SESSION_RESUME.md` — new-session 5-minute onboarding

## Next-session quick start

**STOP and read `.omc/SESSION_RESUME.md` first.** That's the 5-minute onboarding. This STATUS.md is the deeper detail.

If you skipped SESSION_RESUME: the immediate next action is the **M4 infra patch set** — fix `evolve.py:140-142` `NotImplementedError` swallow (ON critical path now that single-dict tuning is statistically rejected), `run_match.py:72` seed plumbing, `tournament.py` CSV-append + sliding futures window. Then M4 tournament pipeline activation. Do NOT run another single-dict H1d variant — pm4 reverification proved single-dict tuning tops out at H1's 35% (statistically below 51% threshold).

## Health summary

| Metric | Value | Health |
|---|---|---|
| Code crashes in 267 smoke games (47 M1-M3 + 10 H1 old + 10 H1b old + 40 H1c pm3 + 40 H1 + 40 H1b + 40 H1c new + 40 ReflexTuned control) | 0 | 🟢 |
| Timeout forfeits | 0 | 🟢 |
| Total agents implemented | 21 (+h1c) | 🟢 |
| Best win rate vs baseline (40-game CI) | **35%** (H1 both-OFFENSE); H1b 30%, H1c 20% (new), ReflexTuned 0% | 🔴 51% threshold statistically rejected → M6 pivot required |
| Best net (W-L) vs baseline | **+8** (H1b — 12W/4L/24T, pm2 rejection overturned) | 🟢 (for tournament) |
| Plan reviewers approving | 6 / 6 | 🟢 |
| Compute budget for M6 (planned) | ~20h | 🟢 |
| Days until submission deadline | TBD (check assignment PDF for due date) | 🟡 |

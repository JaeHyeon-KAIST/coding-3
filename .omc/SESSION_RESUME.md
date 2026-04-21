# SESSION_RESUME — 5-minute onboarding for any new Claude or human session

**Last updated:** 2026-04-22 pm34 END — **Abstract graph 구현 + 20/30 WIN feasibility 검증 완료**

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


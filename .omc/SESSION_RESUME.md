# SESSION_RESUME — 5-minute onboarding for any new Claude or human session

**Last updated:** 2026-04-21 pm32 END — **3-iter ralplan APPROVE + Mac coding done, server sweep DEFERRED to pm33**:
- 🎯 **pm32 plan is execution-ready**: 1358-line consensus plan at `.omc/plans/pm32-sweep-plan.md` (Architect+Critic APPROVE after 3 iterations).
- ✅ **Mac coding 완료 (Step A → C.2)**: 70 v3a_sweep variants (5P1+20AA+10AC+5RS+30 existing); 3 new β env vars (TRIGGER_GATE/TRIGGER_MAX_DIST/RETREAT_ON_ABORT) backward-compat; my_home_cells plumbing + MJ-7 leak guard; 5 new modules (composite, promote_t1_to_t2, analyze_pm32, filter_random_layouts, hth_sweep); 16 1-cap layouts (3 fixed + 8 capsule-swap + 5 hand-crafted topology); 25 unit tests PASS.
- 🟡 **Mac smoke 통과 (~7.6min wall)**: 13/13 no crash; MJ-8 byte-identical (pm32_aa_none_d999 ≡ beta_v2d) ✓; 단 distantCapture trigger=0% at max_moves=200 (적이 invade 안 함 → β chase 불필요 → 측정 무의미하지만 무해).
- 🐍 **Python 3.9.25 parity** Mac/jdl_wsl/sts 모두 일치 (capture.py md5 동일).
- 🖥️ **2nd server sts provisioned**: Ryzen 9950X3D 32T (jdl_wsl 7950X 33T 동급, ~13% 빠름). 둘 다 idle, 활용 옵션 pm33에서 결정.
- 📋 **DEFERRED**: Step E (git push + server pull), Step F1+F2+F3 (server T1 + T2 + HTH calibration). 모든 prereq 끝, **just push and run**.

## pm33 TL;DR (NEXT SESSION — READ FIRST)

### 🎯 Session goals (pm33)
1. **Build freeze-checkpoint infra** (decided pm32 end): `phase1_runner.py`에 `--save-state-at-trigger <pkl>` + `--load-state <pkl>` + state-swap harness. pm34에서 활용.
2. **Execute Step E → F1 → F2 → F3** (pm32 plan §6) — push code to jdl_wsl + sts, server smoke (workers=24, monster pre-check), T1 (1.8h), promote, T2 (1.8h), F3 HTH calibration (~1h). Total ~5h28m server wall.
3. **2nd server (sts) 활용 결정**: Plan A (sts F3-on-4-refs early + F3-on-T2-winners 병행) OR Plan B (T1 50/50 split) OR C (sts standby).

### 🚨 First action
1. Read this file + `.omc/plans/pm32-sweep-plan.md` (pm32 v3 plan — APPROVE'd).
2. `git status` — confirm pm32 uncommitted changes still present.
3. Decide: commit pm32 work + go to Step E? OR commit + build freeze-checkpoint first?
4. If Step E first: `git push` → `ssh jdl_wsl 'cd ~/projects/coding-3 && git pull'` → similarly for sts.

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


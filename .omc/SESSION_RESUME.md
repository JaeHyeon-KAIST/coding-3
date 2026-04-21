# SESSION_RESUME — 5-minute onboarding for any new Claude or human session

**Last updated:** 2026-04-21 pm31 END — **β_retro + β safety knob sweep (Phase 1 primitive focus)**:
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


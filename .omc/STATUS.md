# STATUS — CS470 A3 Pacman Capture-the-Flag

**Last updated:** 2026-04-19 pm26 — **Tier 3 + adaptive rc sprint (+5 rc, +2 lessons)**:
- **rc52b** 92% Wilson [0.850, 0.959] 🥈 NEW LEARNING TIER PEAK — alt-run REINFORCE, +2pp over rc52
- **rc46** 91% [0.838, 0.952] — K-centroid opponent classifier (4-archetype, adaptive multipliers)
- **rc141** 90% [0.826, 0.945] — rc52b OFF + rc82 DEF asym (below rc52b solo)
- **rc142** 91% [0.838, 0.952] — rc46 OFF + rc82 DEF asym (= rc46 solo)
- **rc52c** 86% [0.779, 0.915] — REINFORCE +30 iters from rc52b ckpt with higher lr + lower T → OVERSHOT (train WR ↑, HTH ↓). Lesson: aggressive hypparams don't scale training-WR into HTH-WR.
- **Pattern confirmed**: "learning/classifier OFF + rc82 DEF" ≈ OFF-solo (no boost). 100% peak requires COMPOSITE OFF (rc16/rc32). Sweet-spot hyparams for REINFORCE = low lr + high T.
- Prior: A1 86%, rc22 distill 88%, rc22-v2 85%, rc52 90%, rc82 100% (champion tier 8 at 100%).
- Server Order 4 Phase 2a gen 3/10 running best=0.712, ETA ~24h (unreachable to check — SSH timeout).
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

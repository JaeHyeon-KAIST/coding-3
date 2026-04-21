---
title: "2026-04-21 pm31 - Retrograde analysis + β safety knobs"
tags: ["pm31", "beta-retro", "beta-path4", "beta-slack3", "retrograde", "game-theoretic", "phase1-runner", "sweep-framework"]
created: 2026-04-21T01:06:46.883Z
updated: 2026-04-21T01:06:46.883Z
sources: []
links: []
category: session-log
confidence: medium
schemaVersion: 1
---

# 2026-04-21 pm31 - Retrograde analysis + β safety knobs

# pm31 session log — Retrograde tablebase + β safety knob sweep

**Date**: 2026-04-20 → 2026-04-21 (session-crossing 30+ min)
**Focus**: β v2d Phase 1 capsule chase — reduce die, increase cap. Phase 1-only measurement framework.

## Infrastructure built (major)

### `experiments/rc_tempo/phase1_runner.py`
- Custom in-process game loop (duplicates `Game.run` with early termination)
- Exits on: capsule_eaten_by_A | A_died | max_moves
- **Approach A post-trigger measurement**: trigger_tick = first tick where opp_pacman==1. Metrics: `cap_eaten_post_trigger`, `a_died_post_trigger`, `a_food_post_trigger`, `moves_post_trigger`.
- Per-game wall: ~0.7-1.5s (subprocess overhead dominant)

### `experiments/rc_tempo/phase1_smoke.py`
- ProcessPoolExecutor wrapper around runner
- Multi-opp × layout × color × game matrix
- CSV resumable
- Post-trigger summary table (opp × layout, cap% / die% / food / moves / wall)

### `experiments/rc_tempo/v3a_sweep.py`
- Variant sweep framework with env var knobs
- 31 variants covered: β ref, β safety, v3a (A*+slack), v3b (αβ), β_retro (retrograde)
- Router: `__BETA_AGENT__` (pm30 β), `__BETA__` (β+env), `__V3B__` (αβ), `__RETRO__` (retrograde)

### `experiments/rc_tempo/retrograde_test.py`
- Standalone feasibility test for game-theoretic minimax value tables
- Measured: defaultCapture 0.77s, distantCapture 1.84s — well within 15s init budget

## Agents developed

### v3a (`zoo_reflex_rc_tempo_beta_v3a.py`) — A* + Voronoi + Slack DP
- Risk-weighted A* pathfinding + Voronoi reachability filter + `entry_orienteering_dp` for slack food grab
- Env knobs: V3A_MARGIN, V3A_VORONOI_MODE (full/endpoint/ap/last_k), V3A_RISK_THRESHOLD, V3A_SLACK_MIN, V3A_GREEDY_FALLBACK, V3A_TRIGGER_MODE
- **Result**: cap ~28-42%, significantly below β v2d's 52%. **Pareto inferior**.
- Root cause: full-path Voronoi over-conservative (pm30 S2a failure repeated); slack DP rarely fires because defender typically near capsule → negative slack.

### v3b (`zoo_reflex_rc_tempo_beta_v3b.py`) — αβ minimax
- Iterative-deepening α-β (depth 4-8), move ordering toward capsule, time budget 150ms/move
- Exploits minicontest's perfect-information (fog-of-war disabled)
- **Result**: cap ~22-44%, food 2.2-3.3/game. **Food-biased** — captures less capsule but eats more food.
- Depth tuning (d=4/6/8) gives negligible differences (d=4 sufficient).

### β_retro (`zoo_reflex_rc_tempo_beta_retro.py`) — retrograde tablebase
- `build_retrograde_table` in zoo_rctempo_core: pure-Python fixed-point iteration.
- V[(me_pos, def_pos, turn)] → ±1/0. Built in 0.8-1.8s at init.
- V=+1 guarantees capsule reach regardless of defender (minimax-safe).
- Commit logic: V=+1 OR (V=0 AND d_cap >= DRAW_MIN_DIST). Fallback = β v2d.
- Inherits from ReflexRCTempoBetaAgent (β v2d) so uncommitted chases use β's proven logic.
- **Bug discovered + fixed (S5)**: `retrograde_best_action` returned STOP on V=0 states (all neighbor V values 0, tie broken by first-seen). A stood still → caught by defender. Fix: on V=0 commit, use greedy-toward-capsule (retrograde indifferent on draws).

## Sweep results (240g × 6-opp × 2-layout × 2-color, max_moves=500)

### Top 10 by cap+die (S4 pre-fix, S5 post-fix):

| variant | cap% | die% | food | Notes |
|---|---|---|---|---|
| **beta_path4** | **55.8** | **1.7** | 0.10 | Pareto winner (BETA_PATH_ABORT_RATIO=4) |
| **beta_slack3** | 54.3 | **1.3** | 0.08 | Safety 1위 (BETA_CHASE_SLACK=3) |
| **β_retro (fixed)** | 55.4 | 2.1 | 0.17 | = β_path4-ish, retrograde works |
| beta_v2d | 51.7 | 2.1 | 0.09 | pm30 committed baseline |
| beta_retro_never | 51.7 | 2.1 | 0.09 | V=+1 only commits = β v2d equivalent |
| v3b_d8 | 30.0 | 5.0 | 2.20 | αβ, food-biased |
| v3a_* | 18-42 | 7-10 | 2.6-3.7 | All Pareto inferior |

### β safety knob effects (env vars on zoo_reflex_rc_tempo_beta.py)
- `BETA_ABORT_DIST=2→3`: cap -4pp, die -43% (safety↑)
- `BETA_CHASE_SLACK=1→3`: cap +0-3pp, die -31% (Pareto improvement!)
- `BETA_PATH_ABORT_RATIO=4`: cap +4pp, die -17% (best combination)

## Key decisions / reversals

### Reversal: v3a full-path Voronoi check
**Initial hypothesis**: checking every cell on path is safer than β v2d's endpoint-only check.
**Outcome**: cap dropped from 52% → 28%. **Over-abort** — same failure pattern as pm30 S2a.
**Lesson**: β v2d's endpoint check is near-optimal; full-path variants over-conservative.

### Decision: Phase 1 primary metrics = cap + die (not WR)
**User insight**: WR in Phase 1 smoke is partial-score-at-cutoff, not game outcome. Misleading.
**Resolution**: lock on cap_eaten_by_A_post_trigger + a_died_post_trigger as primary. WR only measured at end via full 1200-move HTH (not done in pm31).

### Reversal: Neural network approach considered then rejected
**Context**: user asked about NN for capsule commitment decisions.
**Reasoning**: 3-5 day engineering cost, numpy-only constraint, training pipeline complexity, risk close to deadline.
**Decision**: retrograde tablebase (6-10h) is theoretically optimal + feasible. No NN needed.

### Insight: minicontest has perfect info (fog-of-war removed)
- `capture.py:278-300` comments out SIGHT_RANGE / SONAR_NOISE
- `getAgentPosition(enemy)` always returns real coords
- **Enables**: retrograde analysis, αβ minimax without belief state, deterministic safety predicates.
- **Disables value of**: particle filter, opponent position estimation.

## Observations

- **Cap ceiling ~55-56%**: β_path4 and β_retro both plateau here. Higher requires different angle (trigger relaxation, pre-trigger positioning, B-agent coord).
- **β safety knob tuning is best ROI**: 3-line env var change (chase_slack=3) gives -31% die. Much cheaper than rewrite.
- **V=0 states are common**: retrograde resolves only 57-71% of state space (+1/-1). The V=0 zone needs heuristic (greedy) for action selection.
- **Per-opp die distribution**:
  - rc02/16/32/82/166 × both layouts: 0-5% die (easy)
  - baseline distantCapture / monster defaultCapture: 15-30% die (hard)
  - monster distantCapture: 50% die (very hard)
  - 10% average masks per-config 0-50% range.

## Open items for pm32

1. **Push cap 55% → 70%+**: current ceiling. Ideas:
   - Trigger relaxation: `opp_pacman >= 1` OR conditional on distance
   - Pre-trigger A positioning: move A toward midline before opp_pacman==1
   - Per-layout-family tuning (distantCapture-specific knobs)
   - Address "rc82 fallback food obsession" problem: A goes deep in opp via rc82 offensive play

2. **Address monster/distant die 30-50% specifically**:
   - What's different? Long-path + defender ambiguity
   - Potential fix: explicit retreat planner when chase fails (not rc82 offensive fallback)

3. **Full-game HTH validation**: before flatten/submit, verify top candidate (β_path4 or β_retro) retains pm30 75.65% WR baseline in 1200-move game.

4. **β_retro `TRIGGER_MODE=loose` not tested** — V=+1 with looser trigger (`opp_pacman>=1`) might unlock more commits.

5. **Agent B coordination**: B is passive mid-line waiter. Could B proactively disrupt defender path to boost A's cap chance?

## Files created/modified (committed)

- `minicontest/zoo_rctempo_core.py` (+build_retrograde_table, +retrograde_best_action, +risk_weighted_astar, +voronoi_safe_path, +slack_plan_to_capsule, +ab_capsule_chase, +_neighbors_with_stop)
- `minicontest/zoo_reflex_rc_tempo_beta.py` (+env var knobs: BETA_ABORT_DIST, BETA_CHASE_SLACK, BETA_PATH_ABORT_RATIO — backward compat when unset)
- `minicontest/zoo_reflex_rc_tempo_beta_v3a.py` (new, 450 lines)
- `minicontest/zoo_reflex_rc_tempo_beta_v3b.py` (new, 470 lines)
- `minicontest/zoo_reflex_rc_tempo_beta_retro.py` (new, 420 lines)
- `experiments/rc_tempo/phase1_runner.py` (new, 270 lines)
- `experiments/rc_tempo/phase1_smoke.py` (new, 260 lines)
- `experiments/rc_tempo/v3a_sweep.py` (new, 230 lines)
- `experiments/rc_tempo/retrograde_test.py` (new, 180 lines)
- `.omc/plans/pm31-primitive-spec.md` (new, 250 lines)

## Commits
- `3722136` pm31 S1: v3a (A*+slack+Voronoi) + Phase 1 sweep harness
- `0f3300e` pm31 S2: v3b αβ minimax + v3a Voronoi mode knobs
- `5116248` pm31 S3: β safety knobs + sweep expansion
- `5071634` pm31 S4: β_retro retrograde-analysis-backed chase
- `b32fa12` pm31 S5: β_retro V=0 commit bug fix

## Next-session priority

See SESSION_RESUME.md pm32 TL;DR.


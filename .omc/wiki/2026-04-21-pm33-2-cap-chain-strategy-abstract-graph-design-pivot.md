---
title: "2026-04-21 pm33 — 2-cap chain strategy + abstract graph design (pivot from freeze-checkpoint)"
tags: ["pm33", "2-cap-strategy", "abstract-graph", "orienteering", "strategy-pivot", "session-log", "feasibility-analysis", "anytime-refinement"]
created: 2026-04-21T14:45:28.026Z
updated: 2026-04-21T14:45:28.026Z
sources: ["experiments/rc_tempo/feasibility_4strategies_parallel.py", "experiments/rc_tempo/user_final_model_seed1.py", ".omc/plans/pm33-abstract-graph-2cap-strategy.md"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-21 pm33 — 2-cap chain strategy + abstract graph design (pivot from freeze-checkpoint)

# pm33 session log (2026-04-21)

## Focus

Originally: build freeze-checkpoint infra (pm32 handoff goal).

Pivoted within 1h after user analysis: "β needs a fundamentally stronger strategy for the 30pt tournament, not better measurement." Rest of 6h session designing **2-cap chain + 2-offensive + abstract-graph orienteering** strategy.

## Activities

### Freeze-checkpoint feasibility (proven, then shelved)

Built 3 smoke tests (`freeze_smoke.py`, `_2.py`, `_3.py`):
- `pickle.dumps(game.state)` round-trips correctly
- Random state restoration (`random.getstate/setstate`) required for deterministic replay
- `zoo_core.TEAM.__dict__` snapshot also required (monster/similar use `TEAM.tick`)
- All 14 test cases PASS (β vs baseline, monster, rc82, rc166, β self-play)

Result: freeze-checkpoint IS structurally feasible. But pivoted to anytime refinement, which provides equivalent benefit without the infrastructure cost.

### Strategy pivot

User insight: RANDOM<seed> layouts (CS470 assignment PDF, p.8) are the likely tournament maps. These always have 4 capsules (2 per side) on 34×18 prison-style grids. Current β (1-cap chase) is a PARTIAL solution.

Full 2-cap chain strategy:
- Eat cap-1 → opp scared (40 opp-moves)
- Before opp's 40th move post-cap1, eat cap-2 → scared timer resets to 40
- Total scared window: 39 (pre-reset) + 40 (post-reset) = **79 opp-moves**
- A budget during scared: 79 A-moves (A and opp interleave 1:1)
- B budget during scared: 79 B-moves
- Goal: 28+ food deposit = 1-trip game WIN

Budget correction: we initially used 75/35 (conservative buffer), corrected to 79/39 (exact per tick math).

### 4-strategy analysis (120 cases: 30 RANDOM seeds × 4 strategies)

| Code | Strategy |
|---|---|
| S1 CLOSE_SPLIT | A eats cap1 (close), B eats cap2 (far), both harvest food |
| S2 CLOSE_BOTH | A eats cap1 → food → cap2 (detour), B pure food |
| S3 FAR_SPLIT | A eats cap2, B eats cap1 |
| S4 FAR_BOTH | A eats cap2 → food → cap1 (detour), B pure food |

Ran with progressive beam widths:
- BEAM=5000 (exhaustive, 295s parallel 8 workers): 18/30 WIN
- BEAM=1000 + depth priority (150s): 20/30 WIN
- BEAM=500 + depth priority (32.5s): 19/30 WIN

Depth priority added during iterations: break ties by preferring food further from midline. Boosted WIN count by 2 (map geometry benefits from scared-window-only reach).

Results (BEAM=1000 final):
- 20/30 maps: 1-trip WIN feasible (≥28 food)
- 10/30 maps: 22-27 food = DOMINATE (85-95% expected WR)
- Single-strategy wins on 4 maps (seeds 13/S3, 16/S4, 23/S2, 29/S4)
- All-four wins on 9 maps (robust: 2, 3, 5, 6, 11, 12, 20, 26, 28)

### Abstract graph design (~10 iterations with user)

Starting concept: reduce food-level graph (30 food, 900 pairs) to a sparser abstract representation for faster orienteering.

Iteration history:
1. **Food-visibility graph** (Voronoi-like, 38 edges) — too sparse, missed connections
2. **Pocket detection via leaf pruning** — identify dead-end regions
3. **Linear segment decomposition** (Definition C) — clean but internal junctions added complexity
4. **Red triangles for "must-pass" nodes** — user's idea, then scrapped (conceptually equivalent to distance-check rule)
5. **Junction skeleton** — keep only branching points as nodes — too abstract
6. **Full pairwise on abstract nodes** — still 190 edges
7. **Distance-check rule** — add edge iff `blocked_BFS == plain_BFS` → SPARSE AND CORRECT
8. **Y-shape merge** — combine headers sharing `(attach, first_cell)` with trunk-sharing cost
9. **Direction field** — each header stores `(food, cost, direction)` for agent execution
10. **FINAL** — X positions on main corridor ONLY + pocket headers with merge + distance-check edges

Final structure for RANDOM1:
- 20 X positions (main corridor: food OR pocket attach OR cap)
- 12 pocket headers (13 raw → 12 after Y-shape merge at (30, 2))
- 30 X-X edges (distance-check filtered)
- Preprocessing: ~5ms

### Key user-driven decisions

1. **"Deep food" = far from midline**, NOT pocket-internal depth. Priority: prefer deep food in scared-window harvest (near-midline food easier to grab anytime).
2. **Internal junction X's REMOVED** — all X's on main corridor only. Y-shape sub-branches merged into single combined option at shared attach.
3. **Pocket headers merged with correct cost** — RANDOM1 (30, 2): H12 (cost 10, food 3) + H13 (cost 6, food 1) → merged (cost 12, food 4, reflecting 2-step trunk × 2 + branches).
4. **Distance-check edges** — cleaner than Voronoi or blocked-BFS-only. Avoids detour artifacts.
5. **Single-thread constraint respected** — per CLAUDE.md, parallel workers only for offline analysis.

### Anytime refinement budget

Single-threaded budgets:
- 15s registerInitialState
- Pre-capsule phase: ~20 moves per agent × 1s = 20s each, × 2 agents = **40s cumulative** during pre-capsule phase
- Scared phase: 79 moves × 1s = 79s (plan execution, not compute)

Effective plan-compute: **55s single-thread**. Plenty for exact DP on abstract graph (~400ms) with room for anytime refinement (widen beam, try alternatives).

## Decisions

1. **Strategy pivot approved**: 2-cap chain replaces pm30-32's 1-cap chase as the target for submission.
2. **Abstract graph is the data structure**: β agent (and future analysis) must use abstract graph, not food-level.
3. **Freeze-checkpoint work shelved**: proven feasible but not needed given anytime refinement.
4. **pm33 → pm34 scope**: design done, implementation next.

## Observations (non-obvious)

- **Depth priority tiebreak** added 2 WIN maps vs no priority. Suggests scared-window efficiency is bottlenecked by choosing right food subset, not just picking most.
- **Y-shape pockets are common**: RANDOM1 has 1 (at (30, 2)). Expect 2-3 per map on average across RANDOM<1..30>. Merge logic is essential for accurate cost.
- **Cap-1 distance and total food correlate loosely**: maps with closer caps (d ≤ 5) favor S2/S4 (BOTH, trunk sharing); maps with far caps (d ≥ 15) favor S3 (FAR_SPLIT, divide territory).
- **Food-level vs abstract graph discrepancy possible**: food-level can skip individual food in a pocket; abstract treats pocket visit as all-or-nothing. Abstract might give slightly LOWER food counts on borderline cases.
- **Anytime refinement plan**: initial fast plan (BEAM=500, 3s), widen beam during pre-capsule phase. After 40s of refinement, effectively exhaustive search.

## Files created

**Feasibility scripts** (food-level analysis):
- `feasibility_2cap_2off.py` — first attempt, greedy
- `feasibility_solo_vs_duo.py` — SOLO vs DUO classifier
- `feasibility_optimal.py` — exhaustive with SCARED_MAX
- `feasibility_4strategies.py` — serial 4-strategy
- `feasibility_4strategies_parallel.py` — **main analyzer** (BEAM=500 + depth priority final)

**Abstract graph iterations** (visual, single-map):
- `food_tree_seed1.py` — Voronoi food-neighbor
- `visualize_pockets_seed1.py` — pocket decomposition
- `pocket_plus_foodtree_seed1.py`, `pocket_fullpairwise_seed1.py`, `junction_skeleton_seed1.py`, `user_4step_seed1.py`, `user_simple_distcheck_seed1.py`, `user_defC_distcheck_seed1.py`, `user_6step_seed1.py`, `linear_pockets_seed1.py` — iterations
- `user_final_model_seed1.py` — **FINAL** (use this in pm34 as reference)

**Freeze-checkpoint smoke tests** (proven, shelved):
- `freeze_smoke.py`, `freeze_smoke2.py`, `freeze_smoke3.py`

**Visualizations**:
- `random_map_images/all_random_1_to_30.png` — composite
- `random_map_images/random_01_FINAL.png` — final abstract graph viz
- `random_map_images/random_01_*.png` — design iteration history

## Open items for pm34

1. Port 120-case analysis from food-level to abstract graph → verify ~19-20 WIN holds
2. Implement new β agent (`zoo_reflex_rc_tempo_gamma.py` or patch):
   - registerInitialState: abstract graph build + 4 strategies × BEAM=500
   - chooseAction: execute plan + anytime refinement
3. Anytime refinement framework (how to schedule incremental compute per turn)
4. Pre-capsule navigation (move to cap target, opportunistic food)
5. Post-scared return (shortest path home)
6. Multi-trip planning (if 1st trip fails to win)
7. 30-map HTH validation (target 85-95% WR vs β v2d's 75.65%)
8. Flatten to 20200492.py for submission
9. Fallback behavior if grading uses 1-cap maps (Berkeley defaults)

## Next-session priority

1. Read `.omc/plans/pm33-abstract-graph-2cap-strategy.md` (full design)
2. `open random_01_FINAL.png` to refresh abstract graph visual
3. Port feasibility analysis to abstract graph first (catch any abstract-specific bugs)
4. THEN implement β agent

## Commits

(none yet for pm33 — will commit at end-of-session after user approval)


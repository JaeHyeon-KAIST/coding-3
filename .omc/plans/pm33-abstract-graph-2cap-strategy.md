# pm33 Design Doc — Abstract Graph + 2-Cap Chain Strategy

**Status**: Design finalized 2026-04-21 pm33 END. Implementation deferred to pm34.

## Session context

pm33 was originally planned to build **freeze-checkpoint infrastructure** (from pm32 end decision). Within the first hour, we pivoted entirely based on user analysis: "our agent doesn't need to be frozen/measured — it needs a fundamentally stronger strategy to win the 30pt tournament."

The rest of the session was spent designing that stronger strategy.

## The core strategic shift

### Old (pm28–pm32): 1-cap chase, reactive
- Opponent crosses midline → β triggers → A chases opponent's 1 capsule
- Eats 1 capsule → 40-tick scared window → harvest some food → return
- Expected WR: 75.65% (pm30 HTH, validated)
- Grading tournament ceiling: ~2nd-tier

### New (pm33 design): **2-cap chain + 2-offensive**
- Game-level insight: tournament maps are almost certainly `RANDOM<seed>` (per CS470 assignment PDF, page 8). These always have **4 capsules (2 per side)** and are always 34×18 prison-style.
- Strategy: eat cap-1 → scared window opens → eat cap-2 within 39 A-moves to extend window → total effective scared = **79 A-moves** (39 pre-reset + 40 post-reset)
- Both agents offensive during scared window. Each has ~75-79 A-moves budget.
- Goal: **deposit 28+ food in one extended scared window = 1-trip game win**
- Feasibility (analysis below): **~20/30 RANDOM seeds achievable**. Remaining 10 seeds get 22-27 food = DOMINATE level.

## Budget math (important, users kept revisiting this)

- `SCARED_TIME = 40` in capture.py. Timer decrements per opp-move (= once per 4 game ticks).
- Cap-1 eaten at tick T0 → opp scared until T0+157 (ticks of game time) if not extended.
- If cap-2 eaten by opp's 39th post-cap-1 move (A's 39th move, tick T0+156), timer resets to 40.
- Opp continues scared for 40 more moves → scared ends opp's 79th move post-cap-1.
- Total opp-moves scared: 39 + 40 = **79** (NOT 80 — 1 overlap at reset instant).
- **A's moves during scared**: 79 (A and opp interleave 1:1 on move-count basis).
- **B's moves during scared**: 79 (same count, offset 2 ticks).

Earlier confusion: we used 75/35 (conservative safety buffer) → corrected to 79/39 in the final analysis.

## 4 scenarios analyzed

Let cap1 = capsule closer to A's spawn (BFS distance), cap2 = farther.

| # | Code | Strategy |
|---|---|---|
| S1 | `CLOSE_SPLIT` | A eats cap1 (close), B eats cap2 (far). Both harvest food. |
| S2 | `CLOSE_BOTH` | A eats cap1 → food detour → cap2. B pure food harvest. |
| S3 | `FAR_SPLIT` | A eats cap2 (far), B eats cap1 (close). Both harvest. |
| S4 | `FAR_BOTH` | A eats cap2 → food detour → cap1. B pure food harvest. |

## Feasibility analysis results

### BEAM=5000 (exhaustive, 295s wall on 8 workers)
| Metric | Value |
|---|---|
| WIN (any strategy ≥ 28) | 18/30 |
| S1 wins | 10/30 |
| S2 wins | 14/30 |
| S3 wins | 15/30 |
| S4 wins | 13/30 |

### BEAM=1000 + depth priority (~150s wall)
| Metric | Value |
|---|---|
| WIN (any strategy ≥ 28) | **20/30** |
| S1 wins | 12/30 |
| S2 wins | 15/30 |
| S3 wins | 14/30 |
| S4 wins | 17/30 |

### BEAM=500 + depth priority (32.5s wall)
| Metric | Value |
|---|---|
| WIN | 19/30 |
| S4 wins | 16/30 |

Notable: BEAM=1000 > BEAM=5000 in WIN count because depth-priority was only added at BEAM=1000 and BEAM=500 runs. Depth priority favors food far from midline (saving scared window for inaccessible food).

### "Deep" definition (clarified twice)
- Not pocket-internal depth
- **Distance from midline on blue side**. `depth(food) = food.x - mid_col`
- Deep food is hard to eat safely without scared window (long exit path)
- Shallow food (near midline) can be eaten cross-midline in any trip

## Abstract graph (THE design we converged to)

### Why abstract
- Food-level graph: 30 food cells, 30×30 = 900 pairwise distances
- Tractable for beam search but slow (~0.7s per strategy with BEAM=500)
- Abstract graph has ~20 nodes (2/3 reduction) and enables exact DP

### Construction (final, see `user_final_model_seed1.py`)

**Step 1: Pocket detection** (iterative leaf pruning)
- Any graph cell with degree 1 gets pruned
- After pruning neighbor's degree, if neighbor is now 1, prune it too
- Result: `pruned` set = all cells in dead-end branches. `main_corridor` = remaining (cells on cycles).

**Step 2: Pocket headers (one per tip with food)**
- For each tip (cell pruned with no pruned children), trace parent chain back to main corridor
- `attach` = main corridor cell where pocket attaches
- `first_cell` = pruned cell adjacent to attach
- `food_count` = food cells on trace
- `visit_cost` = 2 × max_food_depth (round trip to farthest food on this branch)
- `direction` = `(first_cell - attach)` — which way agent should step when entering

**Step 3: Merge Y-shape pockets**
- If 2+ headers share `(attach, first_cell)`, they share a trunk
- Merge into ONE header with:
  - Combined food = sum of headers' food
  - Combined cost = 2 × trunk_depth + sum(2 × branch_depth_from_junction)
  - trunk_depth computed via common-prefix analysis of traces
  - Example: RANDOM1 (30, 2) X had H12 (cost 10, food 3) + H13 (cost 6, food 1) → merged: cost 12, food 4 (trunk 2, branch1 3, branch2 1)

**Step 4: X positions**
- Union of: `{pocket attach cells}` ∪ `{main corridor food cells}` ∪ `{cap cells (on blue side)}`
- Each X is a decision point in orienteering

**Step 5: X-X edges (distance-check rule)**
- For each pair (A, B) of X's:
  - `plain_dist` = shortest path on main corridor (no obstacles)
  - `blocked_dist` = shortest path with other X's as terminators (blocked BFS)
  - Add edge A-B **iff `blocked_dist == plain_dist`**
- Meaning: if direct path A→B happens to pass through another X, it's not a direct edge (implicit via that intermediate X)
- Pocket cells ARE allowed in BFS propagation (to reach internal junctions if any — though none exist in final model with no internal junction X's)

### Final RANDOM1 abstract graph
- 20 X positions (19 on main corridor + 0 on internal junction — we removed internal junction X per user's request)
- 12 pocket headers (13 raw → 12 after Y-shape merge at (30, 2))
- 30 X-X edges (after distance-check filter)
- Preprocessing time: **~5 ms**

### Visual
See `experiments/artifacts/rc_tempo/random_map_images/random_01_FINAL.png`:
- Black X marks at X positions
- Red arrows from X pointing to first_cell (pocket entry direction)
- Green lines between X's (distance-check edges)
- Pink cells = pocket cells
- Light blue = main corridor

## Rejected design iterations (history, for context)

1. **Red triangles for internal junctions** — user initially wanted these as "transit must-pass" markers. Later scrapped in favor of always-on-main-corridor X model.
2. **Voronoi sparse edges** — worked but user wanted more connections. Switched to blocked-BFS, then to distance-check.
3. **Red triangles as "midline crossing gates"** — user's original concept, but they realized it was equivalent to the distance-check rule → simplified.
4. **Full pairwise edges** — too many (190 for RANDOM1). User asked for sparser → Voronoi → blocked-BFS → distance-check.
5. **Pocket = whole connected pruned region** (Definition A) — tied too many decisions together.
6. **Pocket = trace-from-tip-to-main** (Definition B) — overcounted food on shared trunks.
7. **Pocket = linear segment** (Definition C) — conceptually clean (user endorsed), but added internal junction nodes which complicated things. Final: Definition B with Y-shape merge.

## Key user insights (not in analysis, but drive implementation)

1. **Pre-capsule food harvesting** — A can collect food on the way to cap-1. Not in our orienteering budget, free bonus.
2. **Post-scared return food** — on the way home, can grab more food.
3. **B pre-advance** — B can move to midline during pre-trigger phase so B is ready when cap-1 is eaten. Gains effective scared time for B.
4. **Multi-trip game** — don't need to 1-trip win. 2nd trip is viable, possibly with re-triggered scared.
5. **Anytime refinement** — initial plan in 15s `registerInitialState`, refine during each 1s `chooseAction` budget.
   - Pre-capsule phase: ~20 A-moves × 1s = 20s compute + same for B = **40s total extra compute before scared starts**
   - Combined with 15s init = **55s effective budget for planning**
   - Well beyond what offline parallel (BEAM=5000) uses

## Analysis caveats

- **Beam search still used, not exact DP**. The 19-20/30 WIN number might be slightly off from true exact optimum.
- **Food-level graph**, not abstract graph. Abstract might give slightly different (possibly lower) food counts because pocket visits are all-or-nothing whereas food-level can pick individual food.
- **No pre-capsule / post-scared modeling**. Realistic in-game food harvest is probably 3-8 higher than our scared-window-only numbers.
- **No death risk modeling**. Agent might die on the way to capsule (pacman on opp side before scared activates).

## Time budget (online, single-threaded only)

```
Phase                        | Budget | Actual compute use (BEAM=500 plan)
registerInitialState         | 15.0s  | ~3s initial plan + 12s refinement
Pre-capsule phase (~20 moves)| 20s    | ~20 × 990ms = 19.8s refinement
B pre-advance phase          | 20s    | ~19.8s refinement
Scared phase (79 moves)      | 79s    | ~10ms/move decision (plan executed)
```

Effective plan-compute budget: **~55s single-thread** (incl. anytime refinement). Plenty for exact DP on abstract graph (~200-400ms).

## pm34 implementation plan

### Step 1: Switch analysis to abstract graph (verification)
- File: new script (e.g., `feasibility_4strategies_abstract.py`)
- Use `user_final_model_seed1.py`-style abstract graph construction
- Replace food-level beam search with abstract-level DP or beam
- Re-run 120-case analysis → expect similar 19-20 WIN (maybe slightly different)
- Expected speedup: 3-10x

### Step 2: β agent rewrite
- File: new agent (e.g., `minicontest/zoo_reflex_rc_tempo_gamma.py`) or patch existing β
- `registerInitialState`:
  1. Build abstract graph (~5ms)
  2. Compute 4 strategies in parallel via abstract DP with BEAM=500 (~3s)
  3. Pick best plan. Store as sequence of moves.
- `chooseAction`:
  1. Return next action from pre-planned sequence (~10ms)
  2. In remaining budget (~990ms), run refinement on alternative strategies / wider beam
  3. If refined plan better than current → swap

### Step 3: Anytime refinement framework
- Keep current best plan + Pareto-optimal alternatives
- Each `chooseAction`: tighten beam on existing search OR expand alternative scenarios
- Ensure action always deterministic (don't flip-flop mid-execution)

### Step 4: Pre-capsule navigation
- A executes first portion of plan (move toward cap-1 or cap-2)
- On the way, passively eat food (not part of scared-window plan)
- B pre-advances to midline cell near expected entry

### Step 5: Scared phase execution
- Follow pre-computed plan exactly (both A and B)
- Monitor for plan invalidation (e.g., unexpected opponent death, cap re-spawn) — unlikely

### Step 6: Post-scared return
- Both agents head home (shortest path)
- Opportunistic food pickup on the way

### Step 7: 2nd trip setup
- If 1st trip yields 22-27 food (not 1-trip win), plan 2nd trip
- Opponent will have re-spawned caps → another scared opportunity
- Normal β v2d chase logic applies

### Step 8: Validation
- 30-map HTH vs baseline, rc82, monster, etc.
- Target: 85-95% WR (up from 75.65%)
- If successful, `your_best.py` → `20200492.py` → submit

## Files created this session

### Feasibility analysis scripts
- `experiments/rc_tempo/feasibility_2cap_2off.py` — first attempt, food-level greedy
- `experiments/rc_tempo/feasibility_solo_vs_duo.py` — classifier
- `experiments/rc_tempo/feasibility_optimal.py` — wider beam exhaustive
- `experiments/rc_tempo/feasibility_4strategies.py` — serial 4-strategy
- `experiments/rc_tempo/feasibility_4strategies_parallel.py` — **main 120-case analyzer** (BEAM=500 w/ depth priority = final setting)

### Abstract graph design iterations
- `experiments/rc_tempo/food_tree_seed1.py` — Voronoi food-neighbor graph
- `experiments/rc_tempo/visualize_pockets_seed1.py` — initial pocket decomposition
- `experiments/rc_tempo/pocket_plus_foodtree_seed1.py` — combined
- `experiments/rc_tempo/pocket_fullpairwise_seed1.py` — full pairwise
- `experiments/rc_tempo/junction_skeleton_seed1.py` — junction-based
- `experiments/rc_tempo/user_4step_seed1.py` — user's 4-step algorithm
- `experiments/rc_tempo/user_simple_distcheck_seed1.py` — distance-check edges
- `experiments/rc_tempo/user_defC_distcheck_seed1.py` — Definition C attempt
- `experiments/rc_tempo/user_6step_seed1.py` — with red triangles (scrapped)
- `experiments/rc_tempo/linear_pockets_seed1.py` — Definition C linear segments
- `experiments/rc_tempo/user_final_model_seed1.py` — **FINAL ABSTRACT GRAPH** (use this in pm34)

### Visualizations (for reference)
- `experiments/artifacts/rc_tempo/random_map_images/all_random_1_to_30.png` — composite of all RANDOM<1..30>
- `experiments/artifacts/rc_tempo/random_map_images/random_01_*.png` — iterations of abstract graph design
- `experiments/artifacts/rc_tempo/random_map_images/random_01_FINAL.png` — **final abstract graph viz**

### Feasibility feasibility artifacts
- Not yet persisted to CSV. Analysis results are in this doc and SESSION_RESUME.md.

## Freeze-checkpoint status

Originally the pm33 goal. **NOT IMPLEMENTED**. Scope shifted entirely to 2-cap strategy design. Revisit only if needed (unlikely given anytime refinement provides equivalent benefit).

Files created for freeze-checkpoint investigation (proven feasible but unused):
- `experiments/rc_tempo/freeze_smoke.py` — basic pickle round-trip (WORKS)
- `experiments/rc_tempo/freeze_smoke2.py` — β + opponents (mostly WORKS)
- `experiments/rc_tempo/freeze_smoke3.py` — monster with TEAM restore (WORKS)

Key finding: freeze-checkpoint IS structurally feasible (game.state picklable, random state + zoo_core.TEAM dict must be restored). But pivoted away to 2-cap strategy.

## Open questions for pm34

1. **Abstract DP vs Beam search** — is BEAM=500 on abstract close enough to exact, or should we implement proper bitmask DP?
2. **Merge logic edge cases** — what if 3+ headers share same first_cell? (Not in RANDOM1 but might occur)
3. **Anytime refinement scheduling** — greedy increment beam, or explore alternatives systematically?
4. **Pre-capsule path optimization** — which food to pick up on the way? Current plan: just go straight, eat incidentally.
5. **Death risk** — how to handle defender predictably killing A before scared? Simulation-only measurement.
6. **2nd trip planning** — when to abandon 1st-trip WIN pursuit and bank food for 2nd trip.
7. **Submission flattening** — `your_best.py` still DummyAgent. Need to flatten β new agent.

## Critical warnings

- **Single-threaded only** (CLAUDE.md rule, tournament disqualification if violated).
- **No external deps** (numpy/pandas only). Abstract graph work used PIL for visualization — remove from submission code.
- **Grading maps unknown** — assumption is `RANDOM<seed>` based on assignment PDF mention. If TA uses Berkeley fixed maps (1-cap), 2-cap strategy degrades to 1-cap chase (= β v2d behavior). Need graceful fallback.
- **Cap-1 timing is tick-sensitive** — eating cap-2 before cap-1's scared expires requires precise move count. Off-by-one errors kill the plan.

---
title: "pm46 v2 CAPX — code review + Phase 4 tuning candidates"
tags: ["pm46-v2", "capx", "code-review", "phase-4-tuning"]
created: 2026-04-29
updated: 2026-04-29
sources: ["minicontest/zoo_reflex_rc_tempo_capx.py", ".omc/plans/omc-pm46-v2-capsule-only-attacker.md"]
links: []
category: pattern
confidence: high
schemaVersion: 1
---

# pm46 v2 CAPX — code review + Phase 4 tuning candidates

Independent code-reviewer agent (Sonnet) review of CAPX agent. Findings preserved
here for Phase 4 knob sweep + pm47+ algorithmic improvement candidates.

## Severity-rated issues

### [HIGH but mitigated by our test harness] Cross-game module state pollution
`_CAPX_STATE` is module-level, not reset between games in a `-n N` tournament.
`committed_target`, `prev_a_pos`, `astar_cache_tick`, `a_died_emitted` would carry
to the next game with stale coordinates if multiple games shared a Python process.

**Mitigation in current setup**: `pm45_single_game.py -n 1` invocations spawn a
fresh Python process per game (subshell pattern in `pm46_v2_capx_matrix.sh`). No
leakage across the 510-game matrix.

**Risk for future integration**: if CAPX migrates into `your_best.py` for tournament
play (multi-game in a single process), the reset path must be added.
**Fix candidate** (pm47+): clear all keys in `registerInitialState` (game-scoped reset),
keep only `astar_cache` per-tick.

### [MEDIUM] `_p_survive` index off-by-one (`zoo_reflex_rc_tempo_capx.py:243-254`)
`enumerate(path)` starts i=0 for current cell. Margin at i=0 ("can defender reach
A's current cell in 0 steps") is meaningless — A is already there. Biases survival
score downward by ~one sigmoid factor (~0.5×).

**Fix**: `for i, cell in enumerate(path[1:], start=1):` — skip current cell.
Phase 4 candidate.

### [MEDIUM] A* cache: BFS fallback indistinguishable from real A*
On node-cap overflow, the BFS-fallback path is cached with the same key as a real
A* result. Gate evaluates a defender-naive path with the same `_p_survive`
machinery — masks overflow signal in trace.

**Fix**: tag cache entries with origin, emit overflow counter.

### [MEDIUM] `_safest_step_toward` margin uses fixed step_idx=1
`margin_at_cell` subtracts 1 for all next cells. Tie-break by raw BFS dist with no
defender weighting; can pick paths toward closer defenders.

**Fix**: secondary defender-distance tiebreak before BFS dist.

### [LOW] Visible-defender filter excludes scared ghosts entirely
A scared ghost is harmless NOW but lethal once timer expires. Long paths can cross
that boundary.

**Fix**: include scared ghosts but offset their bfs_dist by `scaredTimer`.

### [LOW] Cap-eaten proximity uses Manhattan dist
Manhattan ≤ 1 across thin walls misattributes eater. Tournament-impact only if
CAPX migrates to multi-agent setup.

**Fix**: BFS dist ≤ 1.

### [LOW] Mission-complete returns STOP forever
~600+ ticks of STOP after both caps eaten. 3-STOP forfeit warning rule may apply.

**Fix**: drift toward home or remain at safe cell.

### [LOW] No wall-time circuit breaker
If A* hits 950ms, next tick may push 1100ms (3-violation rule).

**Fix**: adaptive node_cap throttle if last 3 wall_times > 800ms.

## Phase 4 tuning grid (recommended)

| Knob | Default | Candidate values | Hypothesis |
|---|---|---|---|
| `CAPX_GATE_HORIZON` | 8 | **6, 10, 12** | 6 = stricter near-future; 10-12 = give A more lookahead against rc-tempo cousins |
| `CAPX_MIN_MARGIN` | 0 | **-1, 1, 2** | -1 = aggressive on Tier-C; 1-2 = Tier-A safety against eat-then-die |
| `CAPX_DETOUR_BUDGET` | 4 | **2, 6, 8** | 2 = cheap A* on large maps; 6-8 = chokepoint topology |
| `CAPX_HARD_ABANDON_MARGIN` | -1 | **-2, 0, 1** | 0/1 = stricter survival if S2 (eat-then-die ≥80%) on Tier-A |
| `CAPX_SIGMOID_SCALE` | 1.5 | **0.8, 1.0, 2.5** | Sharper = penalize negative margin harder; flatter = ranker degenerates |

**Reviewer's recommended Phase 4 sweep (24 cells, ~3h per cell on Mac)**:
`MIN_MARGIN ∈ {0, 1} × HARD_ABANDON ∈ {-1, 0} × GATE_HORIZON ∈ {6, 8, 10} × SIGMOID ∈ {1.0, 1.5}` — 24 combinations × 35 games (Tier-A 7 def × 5 seeds) per cell.

**Pruning strategy**: Tier-A subset only first; if a cell's Tier-A aggregate ≥ best-so-far + 5pp, expand to Tier-B/C/D. Otherwise drop.

## Algorithmic improvements (pm47+ research candidates)

### 1. Asymmetric threat penalty (territorial defender)
Many zoo defenders (rule_expert, A1_D13) **won't cross the home/border boundary**
unless invader present. Current `edge_cost` charges threat for any defender that
can reach cell B at step i — overly penalizes cells on Blue side.

**Idea**: precompute "defender side" mask (home-side cells); threat = 0 for cells
on opp side unless A is also there (Pacman state). This unlocks ~30% more "safe"
detour paths against territorial defenders. Hypothesis: explains
`monster_rule_expert` blocking CAPX (it patrols home aggressively, so home cells
get full threat).

### 2. Post-eat retreat survival
P3 success = "eat AND survive 3 ticks". Ranker computes P_survive(approach_path)
but ignores P_survive(retreat_path | scared). Add second factor:
`rank_score = P_survive(approach) × P_survive(retreat[:8] | scared=40)`.

Defenders are scared 40 moves post-eat → retreat margins shift by +scaredTimer.
Addresses F3 (post-trigger death) failure mode directly.

### 3. Path-cell hysteresis for noisy defenders
Current hysteresis sticks on `committed_target`. But against random/MCTS noise,
A* recomputes a DIFFERENT path each tick (same target, different cells). Gate
margin flips. Add **path-cell hysteresis**: if ≥80% of new path cells overlap
committed path's first 5 cells, treat as same path → -2 threshold bonus. Doesn't
weaken hard-abandon. Addresses F2 oscillation. Helps CAPX commit faster against
MCTS noise (zoo_hybrid_mcts_reflex 90s timeouts may improve once defender's noise
budget allows quick commits).

## Positive observations from reviewer
- Strict import whitelist (4 helpers from ABS) correctly avoids `_ABS_TEAM`
  side-effect — plan §4.1 G1 P8 honored.
- Per-tick A* cache cleared at tick boundary — N3 contract correct.
- Wall-time tracking ready for adaptive throttling.
- `_emit_trace` clean diagnostic hook with reasonable line cap.
- `_bfs_dist_map` flood-fill is O(W·H) once per defender per tick — well within
  budget.
- `CAPX_GATE_HORIZON` patch is well-motivated and toggleable via
  `CAPX_GATE_USE_FULL=1` for debugging.

## Action items

**For Phase 3 sweep (current)**: no action required. The HIGH issue does not apply
because each game runs in a separate Python process (subshell pattern).

**For Phase 4 tuning sweep**: prioritize `_p_survive` off-by-one fix (5-min code
change, may shift ranker rankings).

**For pm47+ submission integration**: cross-game state reset is required; address
HIGH severity issue.

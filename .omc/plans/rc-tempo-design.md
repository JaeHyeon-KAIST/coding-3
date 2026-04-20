# rc-tempo V0.1 Design Document

**Status:** Design locked 2026-04-20 pm28. Ready for implementation.
**Origin:** User-driven design over pm28 session, heavy back-and-forth.
**Paradigm:** First deterministic orienteering-based agent in rc pool.

---

## 1. Core Idea

**Paradigm shift from existing rc family:**

- Existing rc (rc82, rc166, A1 등): **reactive** — per-turn feature-weight evaluation
- rc-tempo: **precomputed deterministic routing** — full trip plan baked at init (15s budget)

**Key insight chain (user-driven):**

1. Capsule position is static (known at init) → post-capsule behavior precomputable
2. Food position is static + opponents don't eat their own food → food state predictable even after Agent A's entry pickups
3. Scared window (40 moves) is safe — no opponent interference during Phase 3
4. Whole trip (Phase 1 entry + Phase 3 orienteering) pre-bakeable at init

**Strategic insight (user):**
- 40 scared moves should NOT target max food count
- Should target "hard-to-eat foods" (dead-end, funnel, corner) which are normally unreachable
- Agent B cleans up safe food in parallel (swarm join)
- "Easy" foods can be eaten any time; scared is for unique capability

---

## 2. Scope

**V0.1 Supports:**
- Layouts with **exactly 1 Red-eatable capsule** (1 in Blue territory).
  - defaultCapture (32×16) ✅
  - distantCapture (40×16) ✅
  - strategicCapture (44×13) ✅

**V0.1 Fallback (rc82 redirect):**
- Layouts with 0 capsules: alleyCapture, bloxCapture, crowdedCapture, fastCapture, mediumCapture, officeCapture, tinyCapture
- Layouts with 2+ capsules: jumboCapture (v2 — capsule chaining)
- testCapture (1 capsule but tiny/asymmetric)

**Deferred to V2:**
- Capsule chaining (eat 2 capsules with staggered timing to extend scared to ~78 moves)
- jumboCapture / RANDOM layout with 2 Red capsules
- Full safe-route Voronoi tables per defender position
- Scared ghost hunting (dead-end kills)
- Top-3 route variants for anti-determinism

---

## 3. State Machine (Phases)

| Phase | Trigger | Agent A (offense) | Agent B (defense) |
|---|---|---|---|
| **1. Entry** | t=0 | Follow precomputed entry route (start → deep food pickup → near capsule), skip too-deep foods | rc82 defensive patrol |
| **2. Capsule approach** | A within 5 cells of capsule | Final approach to capsule | If swarm-safe: start moving to midline (stays ghost on own side). Else: continue defense |
| **3. Scared window** | A eats capsule (`scaredTimer=40`) | Follow precomputed **risk-weighted orienteering** (max risk sum, home arrival guaranteed) | If pre-positioned: cross midline → opportunistic low-risk cleanup. Else: continue defense |
| **4. Deposit** | A reaches home | → role flip: A becomes defender | If carrying: deposit and either defend or continue attack |
| **5. 2nd cycle** | post-scared | rc82 reactive (capsule gone) | rc82 reactive |

**Phase 3 is the "new" capability. All other phases reuse rc82 logic.**

---

## 4. Precompute (init 15s budget)

All precompute stored in module-level `_TEAM_STATE` dict (shared across both agents).

### 4.1 Map topology (~1s)

- `walls`, `midline_x`, `home_cells` (cells on midline minus 1, non-wall)
- `distancer.getMazeDistances()` — all-pairs BFS
- **Dead-end list**: BFS via degree-1 propagation. For each: `{entry_cell, depth, food_count, cells}`
- **Articulation points** (Tarjan DFS): bottleneck cells; critical for both offense and defense
- **Funnels** (narrow corridors): 1-2 wide passages

### 4.2 Food risk map (~1-2s)

Per-food risk score:
```
risk(f) = 3 * dead_end_depth(f)              # food 안쪽 dead-end 깊음 → 평소 위험
        + 2 * ap_count_on_path_to_home(f)    # 경로에 bottleneck 많음
        + 0.5 * dist_to_nearest_home(f) / 10 # 멀수록 잡힐 확률 ↑
        + 5 * (1 if low_voronoi_margin(f) else 0)  # 수비 우위 구역
        + 2 * (1 if isolated_food(f) else 0) # 외톨이 (다른 food와 > 5 cell)
```

Stored as dict `_TEAM_STATE['food_risk_map'][cell] = score`.

### 4.3 Food assignment to agents

- Split map top/bottom (또는 Voronoi-like based on starting positions)
- `_TEAM_STATE['foods_assigned_to_A']` / `['foods_assigned_to_B']`
- A's foods include "risky" deep foods preferentially
- B's foods are "safe" shallow foods

### 4.4 Entry route (Agent A)

- `start → 2-3 deep food pickups → capsule`
- Skip foods deeper than `max_opp_depth × 0.85` (e.g., depth > 20 on wide maps)
- Greedy nearest with end-at-capsule constraint
- Budget ~25-30 moves

### 4.5 Scared orienteering route (**weighted DP**)

**Problem:**
```
start = capsule
end = one of home_cells
budget = 40 moves
objective = max Σ risk(f) for f ∈ route
constraint = total edge distance ≤ 40
```

**Algorithm:** Bitmask DP
- State: `(pos_idx, eaten_mask)`; `pos_idx` = -1 (capsule) or food index
- `dp[state] = min distance from capsule to this state`
- At each state, check "if end here": total + dist_to_nearest_home ≤ 40
- Track best state by `risk_sum(mask)` (not popcount)
- Reconstruct route via backpointers

**Empirically measured (2026-04-20 pm28):**
| Layout | n_foods_reachable | DP time |
|---|---|---|
| defaultCapture | 20 | 0.01s (pure count max) |
| distantCapture | 21 | 0.04s |
| strategicCapture | 36 | 2.18s |

Weighted version same state space, only evaluation changes. Time bounds identical.

### 4.6 Agent B pre-position trigger

- `swarm_safe_condition(gameState)` = (opponent defender > 8 cells from capsule) AND (opponent attacker not deep in our territory)
- Shared flag `_TEAM_STATE['swarm_safe'] = True` when condition met
- Used to decide if B moves to midline before A eats capsule

---

## 5. Runtime (getAction per turn, ≤0.8s)

**Agent A:**
1. Detect phase via shared state + timer
2. Follow precomputed route for current phase
3. Skip waypoints whose food is already eaten
4. If phase transition: update shared state
5. If danger imminent (pre-capsule): fallback to rc82 escape
6. Post-Phase 4: delegate to rc82 defensive agent

**Agent B:**
1. Default: rc82 defensive patrol
2. If `swarm_safe` + A near capsule: move toward midline (stay own side)
3. If scared window active + pre-positioned: cross midline, greedy pick low-risk foods
4. If `remaining_scared < dist_to_home + 2`: abort, head home
5. Post-scared: rc82 reactive

**Death recovery (simple V0.1):**
- If `_just_respawned(my_pos)` → reset phase to 1, step_idx to 0
- Quick greedy re-plan of entry (0.3s budget)
- If 2+ consecutive deaths → permanent rc82 fallback for rest of game

---

## 6. Shared state (`_TEAM_STATE`)

```python
_TEAM_STATE = {
    # Precomputed at init
    'routes_computed': bool,
    'routes': {
        agent_idx: {
            'entry': [cells],
            'capsule_approach': [cells],
            'scared_plan': [cells],  # weighted DP result
        }
    },
    'food_risk_map': {(x, y): score},
    'foods_assigned_to_A': set,
    'foods_assigned_to_B': set,
    'topology': {
        'dead_ends': [...],
        'articulation': [...],
        'funnels': [...],
        'home_cells': [...],
        'dist_to_home': {...},
    },
    'capsule_target': (x, y),

    # Runtime shared
    'phase': int,  # 1-5
    'swarm_safe': bool,
    'scared_timer_left': int,  # approx
    'capsule_eaten_at_turn': int or None,
    'step_idx': {agent_idx: int},
    'phase_b_role': 'defense' | 'pre_position' | 'join_attack' | 'return',
    'death_count': {agent_idx: int},  # for permanent fallback trigger
}
```

---

## 7. Expected Performance

**DP ceiling per scared trip (measured):**
- defaultCapture: 7 food (weight max, probably 5-6 high-risk foods)
- distantCapture: 9 food (probably 7-8 high-risk)
- strategicCapture: 13 food

**Per-trip total (A + B + entry):**
- defaultCapture: 12-15 food/trip (ceiling)
- distantCapture: 14-17
- strategicCapture: 18-21 (1 trip game-ending possible)

**Expected WR vs baseline:**
- rc82 (97%) vs rc-tempo: comparable or slight upgrade (because same Phase 1 logic, upgraded Phase 3)
- Target: **97-98.5%** on defaultCapture 100g HTH
- Target: **H2H vs rc82 ≥ 50%**

**Lower-bound guarantee:** rc82 fallback means rc-tempo can't lose WR to rc82 on fallback conditions.

---

## 8. Task Breakdown (implementation sequence)

All tasks in TaskCreate. Suggested order:

1. **#1 Skeleton** — `minicontest/zoo_reflex_rc_tempo.py`, createTeam, classes, rc82 delegate import
2. **#10 Fallback** — capsule count check, redirect to rc82 if 0 or 2+
3. **#2 Topology** — walls, home cells, dead-ends (BFS), Tarjan AP, funnels
4. **#13 Risk map** — per-food risk score
5. **#3 Food assignment** — A gets risky, B gets safe; split by topology
6. **#4 Entry route** — start → capsule via deep food pickup
7. **#7 Dead-end whitelist** — conditional entry logic for V0.1 (stretch)
8. **#5 Weighted DP orienteering** — core Phase 3 algorithm
9. **#8 Agent A runtime** — phase machine, route follow, danger detect
10. **#9 Agent B runtime** — pre-position trigger, swarm join, safe cleanup
11. **#11 HTH testing** — 100g on defaultCapture, 50g on distant/strategic
12. **#12 AI_USAGE.md** — record per assignment requirement

**Deferred to V0.2 or V1:**
- **#6 Voronoi safe route table** — per-defender-position safe regions
- Top-3 anti-deterministic route variants
- Capsule chaining (v2)

---

## 9. Design decisions / rationale

| Question | Decision | Rationale |
|---|---|---|
| Algorithm for 40-route | **Bitmask DP** (not heuristic) | Tested 0.12-2.32s; optimal; no hyperparameter tuning |
| Capsule-free maps | **rc82 fallback** (not custom) | Keeps scope tight; rc82 already strong |
| 2+ capsules | **rc82 fallback for V0.1**, v2 adds chaining | Chaining is complex timing; v1 gets value from 3 main maps |
| "Too deep" threshold | **`max_opp_depth × 0.85`** | Map-relative; adapts to any layout |
| Dead recovery | **Simple respawn detect → phase 1 restart + quick replan** | 99% cases simple works; 2-death fallback to rc82 |
| Anti-determinism | **deferred to V0.2** | Start simple, add diversity later |
| Safe routing (Voronoi) | **deferred to V0.2** | V0.1 relies on rc82's reactive ghost avoidance |

---

## 10. Open questions (resolve during impl)

1. **Risk weight constants** — tentative (3, 2, 0.5, 5, 2 in §4.2). Tune by observing which foods DP selects on defaultCapture.
2. **Agent B's cleanup scope** — "safe foods only" vs "any foods not in A's plan". Lean toward latter (more flexible).
3. **Pre-position trigger distance** — A within 5 of capsule. May need adjust after observing.
4. **swarm_safe threshold** — opponent > 8 cells. Verify against actual baseline defender positioning.
5. **Consecutive death threshold** — 2 deaths → permanent rc82. May need 1 or 3.

---

## 11. Testing protocol

**Smoke (post-impl):**
- 10g on defaultCapture vs baseline (sanity check)

**Primary benchmark:**
- **100g HTH vs baseline** on defaultCapture (target ≥ 97%)
- 50g HTH vs baseline on distantCapture, strategicCapture (target ≥ 97%)

**Fallback verification:**
- 30g HTH vs baseline on alleyCapture, jumboCapture (should match rc82 WR)

**H2H (upgrade check):**
- 40g rc-tempo vs rc82 on defaultCapture (target ≥ 50%)
- 40g rc-tempo vs rc166 on defaultCapture

**Output:** CSV in `experiments/artifacts/rc_tempo/hth_*.csv`

---

## 12. Key references

- User design chat: pm28 session (2026-04-20)
- Orienteering test: `experiments/test_orienteering.py`
- Related prior rc: rc82 (composite 97%), rc166 (switch 98.5%)
- Capture.py mechanics confirmed:
  - `SCARED_TIME = 40` (decrements on scared agent's own turn)
  - `DUMP_FOOD_ON_DEATH = True` (carried food respawns at death BFS)
  - `KILL_POINTS = 0` (eating scared opponent = 0 direct score, time waste for them)
  - `MIN_FOOD = 2`, `foodToWin = (TOTAL_FOOD/2) - MIN_FOOD = 18`
  - Capsule team-locked (Red can only eat Blue-territory capsules)

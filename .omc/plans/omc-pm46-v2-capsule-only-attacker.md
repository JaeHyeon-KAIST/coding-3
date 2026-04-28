# omc-pm46-v2: Capsule-Only Single-Purpose Attacker (CAPX)

**Date:** 2026-04-29
**Track:** omc / Claude
**Plan slot:** pm46-v2 (sub-plan of pm46 mode-commit handoff)
**Status:** Iter-3 revision — 6 surgical patches (N1-N6) on top of iter-2. No algorithmic rework. Awaiting Architect/Critic quick re-check.
**Output type:** Greenfield experimental attacker (does NOT modify ABS, does NOT touch submission code)

---

## 0. Iter-2 changelog (Critic patches applied)

- **P1 metric**: ABS's `[ABS] scared started` is class-private; CAPX cannot emit it. Replaced with `len(getCapsules())` decrement detector — same semantic ("any cap consumed by Red"), different emit. ABS-baseline must be RE-MEASURED with the same detector.
- **P2 hard abandon**: §5.3 adds `CAPX_HARD_ABANDON_MARGIN` (default -1) — separates hysteresis (path stability) from suicide prevention.
- **P3 survival-aware acceptance**: User-emphasized goal "필 죽지 않고 도착" — added `died_pre_eat ≤ 60%` aggregate cap, per-defender `died_pre_eat ≤ 80%` cap, primary success = "reach AND survive".
- **P4 Phase 0 ABS re-baseline**: ABS-solo 17×30=510 game re-measured with corrected `prev_caps` detector. Runs in parallel with CAPX Phase 1 (zero serial cost).
- **P5 A* cost**: `defender_dist_map` per-tick precompute; `K_NODES=500` hard cap; fallback to direct BFS on overflow.
- **P6 wrapper fork**: `pm46_v2_capx_matrix.sh` separate; existing `pm46_v2_a_solo_matrix.sh` stays ABS-only.
- **P7 Phase 2.5 tier-screening**: 17×5=85 game gate before 510 sweep.
- **P8 import whitelist**: only 4 helpers from ABS module — never wildcard, never class, never `_build_once`/`_reset_abs_team`.
- **P9 AI_USAGE discretionary**: CAPX is research/non-submission → `docs/AI_USAGE.md` entry optional, not required.
- **P10 pre-mortem**: 3 named scenarios (S1 algorithmic moot / S2 eat-then-die / S3 topology bound).
- **P11 K cap = 8**: monster_rule_expert detour budget capped at 8; topology bound documented if exceeded.

**Survival emphasis**: §3, §5.3, §5.4 all reframed — primary objective = "**A reaches capsule alive**", death-during-approach counts as failure regardless of cap eaten.

## 0.1 Iter-3 changelog (Critic mechanical patches N1-N6)

- **N1 A* node-cap 500 → 2000 + Phase 1 timing gate**: P5+P11 interaction (K=8 may exceed 500 nodes); raised default to 2000 with explicit Phase 1 AC: p95 chooseAction wall-time < 150ms over 200+ ticks on Mac. If exceeded, halt + lower cap before Phase 2.5.
- **N2 `CAPX_MIN_PSURVIVE` floor (default 0.2)**: §5.4 ranker fallback — if max P_survive across candidates < floor, rank by bfs_dist only (closest cap first). New §11 question.
- **N3 Red-only caps + A* result cache**: §5.1/§5.4 use `getBlueCapsules()` (CAPX is Red); A* result cache `_CAPX_STATE['astar_cache'][(a_pos, tick)] = path` — gate AND ranker reuse same A* output (avoid double compute).
- **N4 Per-defender override hard rule**: §3.3 explicit — ANY per-defender `died_pre_eat ≥ 80%` = FAIL regardless of aggregate. No aggregate trade-off.
- **N5 Phase 0 parallelism precision**: "serial cost = 0" → corrected: tmux/nohup background (CPU-bound 4-5h); Phase 1 prototyping is editor-bound; smoke runs (~5 min CPU each) scheduled around Phase 0 idle/post-completion. Net <10% wall-time contention.
- **N6 R11 risk added**: A* p95 wall-time exceeds 200ms under 2000-node cap on Mac → mitigation: N1 timing-gate auto-lowers `CAPX_ASTAR_NODE_CAP`; direct-BFS fallback retains correctness.

---

## 1. Scope (single sentence)

Build a **new experimental attacker agent** (`zoo_reflex_rc_tempo_capx.py`) whose **sole objective** is "**A reaches at least 1 capsule alive** (any of Blue's capsules) per game" against each of the 17-defender zoo, and demonstrate measurable improvement in `(cap_reached AND a_alive_at_eat)` rate over the existing ABS attacker.

**This plan discards** food harvesting, scoring, deposit-28, scared-window food collection, win/lose evaluation, return-home strategy chains, cap2-after-cap1 sequencing, B-agent coordination — NONE of these are part of CAPX's behavior. CAPX is a **single-trigger, single-target probe** with **survival as a co-equal goal**.

---

## 2. Context (key facts driving the design)

### 2.1 User's reframing

The existing ABS agent's `_a_first_cap_survival_test*` survival gate is **overly conservative**. It evaluates only the **direct BFS path** + per-step margin against visible defenders, and rejects any path where any step has margin ≤ `ABS_FIRST_CAP_MARGIN` (default 1). When a defender stands near the direct corridor, the gate emits UNSAFE_TRIGGER and the agent never commits, even though **detour paths exist**.

Defender agents in the zoo are **generic invader-patrol mechanisms** — none of the 17 actively guard capsules. Capsule-eat is a strategic blind-spot we can exploit.

### 2.2 Smoke evidence (pm46 v2 Step 2 partial — 9/9 games)

| Defender | Outcome distribution | Diagnosis |
|---|---|---|
| `baseline` | died 3/3 (tick 280, 359, 520) | A reached cap region but got killed AFTER cap (gate triggered, but no escape plan) |
| `monster_rule_expert` | died 3/3 (tick 148, 195, 300) early | Strong chokepoint defender → gate kept rejecting → A walked into death without commit |
| `zoo_dummy` | none 3/3 (no REACH event at all) | Gate oscillation — random ghost movement flips gate UNSAFE↔SAFE every tick → A oscillates path_len=5 from cap, never commits |

**P1 metric correction (REVISED):** Step 2 wrapper currently parses `[ABS_A_FIRST_CAP_REACH]` (cap1-only). The line `[ABS] scared started` (mentioned in iter-1) is **emitted by `ReflexRCTempoAbsAgent` class only** (lines 2767/2782 in `zoo_reflex_rc_tempo_abs.py`) — CAPX cannot reuse it because CAPX doesn't import the ABS class.

**Ground truth source for both ABS-baseline AND CAPX:** `len(gameState.getBlueCapsules())` decrement on Red turn (Red attackers — only Blue caps are eatable; N3). Each agent emits its own line:
- ABS-baseline: re-measured with `[ABS_CAP_EATEN]` (added via patched ABS-solo wrapper) OR re-parse engine state.
- CAPX: `[CAPX_CAP_EATEN]` line emitted by the new agent.

Different emit strings, **identical semantic** ("Red consumed a cap"). Direct comparison valid.

### 2.3 Failure-mode taxonomy (existing ABS)

1. **F1 — gate over-rejection**: strong defender near direct path → gate UNSAFE on every tick → A never commits → tick 1200 timeout with 0 caps.
2. **F2 — gate oscillation**: random/noisy defender → margin recomputed every tick → SAFE/UNSAFE flip → A oscillates within radius 5–8 of cap → 0 caps.
3. **F3 — post-trigger death**: gate eventually fires SAFE → A walks BFS path → defender intercepts within 2-3 ticks of trigger → death AFTER cap eaten (or just before).
4. **F4 — no detour considered**: gate only evaluates direct BFS path. If direct path is blocked by defender, the existence of an alternate path 2-3 cells longer is not tested.

### 2.4 Constraints (from CLAUDE.md and assignment rules)

- No global Python — `.venv/bin/python` only.
- No multithreading.
- No new dependencies (numpy/pandas only).
- Cannot modify: engine files (`baseline.py`, `capture.py`, `captureAgents.py`, `game.py`, `layout.py`, `distanceCalculator.py`, `graphics*.py`, `keyboardAgents.py`, `mazeGenerator.py`, `textDisplay.py`, `util.py`).
- Must NOT touch submission code (`your_best.py`, `your_baseline*.py`, `20200492.py`, `myTeam.py`).
- Track separation: omc only — must NOT touch `.omx/`.
- Per-turn 1s budget; init 15s; 1200-tick game cap.
- Function ownership: `_choose_b_prep_candidate`, `_gate_first_cap_trigger_action`, `_actual_first_cap_trigger_compat` are pm44 omx-authored. **CAPX is greenfield → no conflict** (we don't reuse these).

---

## 3. Work Objectives — Survival-Aware Success Criteria (P3)

### 3.1 User-emphasized primary criterion

> **"목적은 a 에이전트 *필 죽지 않고 도착*하는 그 에이전트 로직 개발이야."**

CAPX's primary success criterion = **A reaches the capsule AND survives the eat tick**. Degenerate "die-just-after-cap-eat" outcomes do **NOT** count as success. Algorithm and acceptance bars both reflect this.

### 3.2 Success definition (formal)

Per game, success ⇔ ALL of:
1. `[CAPX_CAP_EATEN]` line emitted (cap consumed by Red), AND
2. A's position at the eat tick is on the cap cell (not respawn cell — i.e., A wasn't dying-while-eating), AND
3. A survives ≥ 3 ticks AFTER the eat (proof of "didn't suicide-eat").

If `CAPX_EXIT_ON_EAT=1` is set, only conditions (1)+(2) are checked online; condition (3) (post-eat survival) is checked via `CAPX_EXIT_ON_EAT=0` follow-up runs on borderline defenders.

### 3.3 Quantitative pass bar (REVISED for survival)

| Tier | Defender class | ABS baseline (smoke) | CAPX target — `cap_eat_alive` | CAPX target — `died_pre_eat` cap |
|---|---|---|---|---|
| Tier-A (strong) | monster_rule_expert, zoo_minimax_ab_d3_opp, zoo_reflex_A1, zoo_reflex_A1_D13, zoo_reflex_defensive, zoo_belief, baseline | ~10% | **≥ 30%** | **≤ 80%** |
| Tier-B (medium) | zoo_hybrid_mcts_reflex, zoo_minimax_ab_d2, zoo_reflex_A1_D1, zoo_reflex_capsule, zoo_reflex_rc82 | ~30% | **≥ 60%** | **≤ 60%** |
| Tier-C (weak) | zoo_dummy, zoo_reflex_aggressive, zoo_reflex_tuned | ~20% | **≥ 90%** | **≤ 30%** |
| Tier-D (RC-tempo cousins) | zoo_reflex_rc_tempo_beta_retro, zoo_reflex_rc_tempo_gamma | ~20% | **≥ 50%** | **≤ 70%** |

**Aggregate pass bar (P3 hard rules):**
- `cap_eat_alive ≥ 50%` over 510 games, AND
- `died_pre_eat ≤ 60%` over 510 games, AND
- **No defender** with `died_pre_eat ≥ 80%`, AND
- Strict improvement on `cap_eat_alive` over ABS-baseline on **≥ 12 of 17 defenders** (no regression on more than 2 defenders).

**Per-defender override (N4 — hard rule, NO trade-off):** ANY single per-defender `died_pre_eat ≥ 80%` = FAIL regardless of aggregate. No aggregate-vs-per-defender trade-off allowed against per-defender suicide rate. Rationale: a single defender that turns CAPX into a suicide bot is a structural failure of the survival-aware design, not a tail event to average away.

**Exit conditions:**
- If CAPX cannot beat ABS on Tier-C dummies in Phase 2.5 tier-screening → halt, fundamental design error.
- If aggregate `died_pre_eat > 80%` despite cap_eat success → halt (S2 scenario, see §9 pre-mortem) — agent is suicidal even when "successful".

---

## 4. Guardrails

### 4.1 Must Have

- [G1] **Greenfield file** — `minicontest/zoo_reflex_rc_tempo_capx.py`. Does NOT import or extend `ReflexRCTempoAbsAgent` class. Imports **only** the 4 helpers below from `zoo_reflex_rc_tempo_abs` module:

  ```python
  from zoo_reflex_rc_tempo_abs import (
      _grid_bfs_distance,
      _bfs_grid_path,
      _dir_step,
      _bfs_first_step_to,
  )
  ```

  **Forbidden imports** (P8): wildcard `*`, any class (`ReflexRCTempoAbsAgent`, `StubBAgent`), `_build_once`, `_reset_abs_team`, `_ABS_TEAM`, any `_classify_*`, any `_a_first_cap_*`. If even one of these is imported, the entire `_ABS_TEAM` global init side-effect fires → unsafe.
- [G2] **B-stub wrapper** — `minicontest/zoo_reflex_rc_tempo_capx_solo.py` (mirrors `zoo_reflex_rc_tempo_abs_solo.py` pattern: lower-index = full CAPX, higher-index = `StubBAgent` STOP forever; CAPX defines its OWN StubBAgent — does not import from abs_solo).
- [G3] **Capsule-only success metric (P1 REVISED, N3)** — track `prev_caps = set(gameState.getBlueCapsules())` at start of each chooseAction (CAPX is Red). On entry, if `prev_caps - current_caps` non-empty AND a Red agent's prior action could plausibly have eaten one (proximity check: any Red agent ≤ 1 step from the missing cap on prior tick), emit `[CAPX_CAP_EATEN] tick=T cap=(x,y) a_pos=(x,y) eater_idx=I outcome=eaten`. Continue game (or exit) per env flag `CAPX_EXIT_ON_EAT=1`.
- [G4] **Defender-aware path planner** — replaces ABS's direct-BFS-only approach. See §5.2.
- [G5] **Replaced/relaxed gate with hard abandon override (P2)** — see §5.3.
- [G6] **Trace logging** — `CAPX_TRACE=1` emits per-tick: `tick, a_pos, cap_targets, chosen_target, chosen_path[:5], defenders, gate_decision, p_survive, action`. Default OFF for production runs.
- [G7] **Time budget compliance** — chooseAction must return in <1s. Per-tick precompute: `defender_dist_map` (1 BFS per visible defender, ~7ms total). A* node-expansion cap = **2000 (N1, raised from iter-2's 500 to accommodate K_DETOUR=8 worst case)**. Phase 1 timing gate (see §6 Phase 1 AC) auto-lowers cap if p95 > 150ms.
- [G8] **AI usage logging (P9 — DISCRETIONARY)** — CAPX is research artifact, NOT submission. `docs/AI_USAGE.md` entry is **optional**. If/when CAPX algorithmic ideas migrate into `your_best.py` (separate plan), AI_USAGE entry becomes required.

### 4.2 Must NOT Have

- [N1] No food-harvesting code, no deposit-28, no scared-window food collection, no return-home routing — pure capsule-only.
- [N2] No B-agent coordination — B is stub.
- [N3] No multi-capsule chain (cap1 → cap2). CAPX picks ONE target per tick (re-evaluatable) and goes for it. Once a cap is eaten alive, mission accomplished.
- [N4] No retrograde V table dependency (pm45 closed that branch). Pure online planning.
- [N5] No modifications to `zoo_reflex_rc_tempo_abs.py`, ABS solo wrapper, submission files, or omx-owned files.
- [N6] No new dependencies beyond numpy/pandas. CAPX must run on stock Python 3.9.
- [N7] No new shared `_ABS_TEAM` keys. If CAPX needs cross-tick state, use module-level `_CAPX_STATE` dict on the CAPX module only.

---

## 5. Algorithm Design — Survival-Aware

### 5.1 High-level loop (per tick)

```
chooseAction(gameState):
  a_pos = self position
  caps  = gameState.getBlueCapsules()  # N3: Red attacker → only Blue caps eatable
  emit_cap_eaten_if_decremented(prev_caps, caps)
  prev_caps = caps
  if not caps: return STOP  # already eaten (mission complete)
  defenders = visible enemy ghosts on home/border/opp side

  # Step 0 (P5): per-tick defender-dist precompute (~7ms)
  defender_dist_map = {d: bfs_dists_from(d, walls) for d in defenders}

  # N3: clear A* cache at tick start; ranker + gate share it within this tick.
  _CAPX_STATE['astar_cache'] = {}   # key: (a_pos, tgt) → path

  # Step 1: rank cap targets (survival-weighted with floor fallback, §5.4)
  targets = rank_targets(a_pos, caps, defender_dist_map)

  # Step 2: for each target, compute defender-aware path (cache hit if ranker already computed)
  for tgt in targets:
    path = astar_cached(a_pos, tgt, defender_dist_map, K_DETOUR)
    if path is None: continue
    decision = gate(path, defender_dist_map, committed_target=last_target)
    if decision == TRIGGER:
      last_target = tgt
      return _dir_step(a_pos, path[1], legal)

  # Step 3: hard-abandon path → safest_drift toward least-suicidal cap
  last_target = None
  return safest_step_toward(a_pos, targets[0], defender_dist_map)
```

**N3 A\* result cache:** `_CAPX_STATE['astar_cache']` is a per-tick dict keyed by `(a_pos, tgt)` (since `defender_dist_map` is also per-tick, the key is sufficient). The §5.4 ranker calls `astar_cached` first; the §5.1 Step-2 gate loop reuses the cached path. Cache cleared at the start of each `chooseAction` call. Avoids double A* invocation per tgt within a tick.

### 5.2 Defender-aware A* path planner (P5: bounded compute, replaces F4)

**Algorithm:** A* on the 4-connected walkable grid with cost augmentation.

**Per-tick precompute (P5):**
- For each visible defender `d`, run `bfs_dists_from(d, walls)` once → `defender_dist_map[d][cell]` returns dist in O(1) thereafter.
- ~10 visible defenders max × ~500 cells × constant = ~5-10ms total.

**Edge cost:**
- Edge cost from cell A to cell B (step index `i+1` from path start) = 1 + `threat_penalty(B, i+1, defender_dist_map)`.
- `threat_penalty(cell, step_idx, dist_map)` = sum over defenders d of:
  - +∞ if `dist_map[d][cell] - step_idx ≤ 0` (definite catch — defender can reach cell at/before A)
  - + W2 if margin ∈ [1, 2] (close call) — W2 ≈ 3 (env `CAPX_CLOSE_PENALTY`, default 3)
  - + W3 if margin ∈ [3, 4] (warm) — W3 ≈ 1
  - 0 otherwise

**Bounds:**
- Max path length = `direct_bfs(a_pos, tgt) + K_DETOUR` (env `CAPX_DETOUR_BUDGET`, default 4, **hard cap 8 — P11**).
- Max A* node expansions = **2000 (N1, env `CAPX_ASTAR_NODE_CAP`, default 2000)** — raised from iter-2's 500 because K_DETOUR=8 worst case can expand >500 nodes legitimately. On overflow → fallback to direct BFS path with margin tag, gate decides (P5+N6).
- **Phase 1 timing gate (N1)**: p95 chooseAction wall-time MUST be < 150ms over 200+ ticks on Mac. If exceeded, halt + auto-lower `CAPX_ASTAR_NODE_CAP` (try 1500 → 1000 → 500) before Phase 2.5. Direct-BFS fallback retains correctness at lower cap.

**Output:** list of cells from `a_pos` to `tgt`, OR `None` if no feasible path within budget+node-cap.

### 5.3 Gate policy — Survival-aware soft gate with hard abandon (P2, P3)

**Old gate (ABS):** binary {SAFE, UNSAFE, APPROACH} on direct BFS path with margin ≥ 1.

**New gate (CAPX):** **survival-weighted, hysteresis-aware, with hard abandon override:**

#### 5.3.1 Decision pipeline

```
gate(path, dist_map, committed_target):
  margins = [min(dist_map[d][cell] - i for d in defenders) for i, cell in enumerate(path)]
  next3   = margins[0:3]   # next 3 steps along chosen path
  full    = margins        # whole path

  # 1) Hard abandon override (P2 — suicide prevention)
  if min(next3) < CAPX_HARD_ABANDON_MARGIN:   # default -1
    return ABANDON   # break commitment regardless of hysteresis

  # 2) Hysteresis (path stability — F2 fix)
  if path.target == committed_target:
    threshold = CAPX_MIN_MARGIN - 2          # sticky: -2 from baseline
  else:
    threshold = CAPX_MIN_MARGIN              # default 0

  # 3) Trigger condition
  if min(full) >= threshold:
    return TRIGGER

  # 4) Approach mode (CAPX_APPROACH_MODE=1, default 1)
  if CAPX_APPROACH_MODE and min(full) >= threshold - 1:
    return TRIGGER  # tighter race, but still committed

  return REJECT
```

#### 5.3.2 Knob separation (P2)

- `CAPX_MIN_MARGIN` = baseline trigger threshold (default 0). Tighter races allowed than ABS.
- `CAPX_HARD_ABANDON_MARGIN` = suicide-prevention floor (default -1). Even committed agent abandons if next-3-step min margin drops below this.
- Hysteresis (-2 sticky on committed target) ONLY affects threshold for trigger, NEVER overrides hard abandon.

#### 5.3.3 Survival-weighted survival probability (used in §5.4 ranking)

```
P_survive(path) = product over i of P_step_safe(margin[i])
where P_step_safe(m) = sigmoid((m - 0) / 1.5)  # m=0 → 0.5, m=2 → ~0.79, m=-2 → ~0.21
```

#### 5.3.4 Expected fix mapping

- F1 (over-rejection) → margin threshold relaxed 1 → 0; detour paths considered.
- F2 (oscillation) → hysteresis: once committed, sticky on threshold ONLY (hard abandon still active).
- F3 (post-trigger death) → hard abandon override on next-3 margin < -1.
- F4 (no detour) → A* with detour budget K=4 default (hard cap 8 per P11).

### 5.4 Cap target ranking — Survival-weighted (P3) + N2 floor + N3 cache

**Old (iter-1):** sort by `(bfs_dist, +bfs_dist_to_nearest_defender)`.

**New (iter-3):** sort by `(cap_eat_alive_score, bfs_dist)` with floor fallback:

```
caps = gameState.getBlueCapsules()         # N3
P = {cap: P_survive(astar_cached(a_pos, cap)) for cap in caps}   # N3 cache hit reused by §5.1
if max(P.values(), default=0.0) < CAPX_MIN_PSURVIVE:    # N2: default 0.2
  # Ranker-degenerate fallback: no cap is reachable-alive enough; fall back to closest-cap-first.
  rank = sorted(caps, key=lambda c: bfs_dist(a_pos, c))
else:
  cap_eat_alive_score = lambda c: -P[c]
  rank = sorted(caps, key=lambda c: (cap_eat_alive_score(c), bfs_dist(a_pos, c)))
```

Ranking semantics:
- Default: prefer cap with **higher P_survive**, even if slightly farther. Same P_survive → prefer closer.
- N2 floor fallback: if no cap clears `CAPX_MIN_PSURVIVE` (default 0.2), drop survival-weighting and rank by distance. Rationale: when ALL options are below floor, ranker has no signal — degenerating to "go to nearest cap" is no worse than "go to farthest survival-prob-tied cap".
- A* result cache (N3): `astar_cached` reads/writes `_CAPX_STATE['astar_cache']`. The §5.1 Step-2 gate loop reuses these paths — no recomputation per cap per tick.

If A* fails for both caps → fallback `safest_step_toward(closest_cap)` (drift toward, stay alive).

**Survival emphasis:** "필 죽지 않고 도착" — the ranker explicitly chooses the cap CAPX is most likely to reach alive, NOT the closest cap, EXCEPT when the survival-prob floor (`CAPX_MIN_PSURVIVE`) is unmet for all candidates and ranking by distance becomes the only signal.

### 5.5 B stub

CAPX runs solo via `zoo_reflex_rc_tempo_capx_solo.py` wrapper (mirrors ABS-solo pattern). Lower-index = CAPX. Higher-index = `StubBAgent` (STOP forever). CAPX defines its own StubBAgent class — does not import from `abs_solo`.

---

## 6. Phased Rollout (Task Flow)

### Phase 0 — ABS baseline RE-MEASUREMENT (P4, parallel with Phase 1)

**Trigger:** before any CAPX vs. ABS comparison claim.

**Tasks:**
1. Patch `zoo_reflex_rc_tempo_abs_solo.py` OR add a tiny shim — emit `[ABS_CAP_EATEN] tick=T cap=(x,y)` on `len(getCapsules())` decrement (uses same detector logic as CAPX's; copy-paste 15 lines from CAPX). **OR** use a wrapper script that polls game state from `pm45_single_game.py`.
2. Run 17×30 = 510 games of ABS-solo with corrected detector. Wrapper: `pm46_v2_a_solo_matrix.sh` UNCHANGED in script body, but parses BOTH `[ABS_A_FIRST_CAP_REACH]` AND `[ABS_CAP_EATEN]`.
3. Output: `experiments/results/pm46_v2/abs_baseline_corrected.csv` with `cap_eat`, `a_alive_at_eat`, `cap_eat_alive`, `died_pre_eat` columns.

**Parallelism (N5 — precise):** Phase 0 runs in `tmux` or `nohup` background — CPU-bound, ~4-5h on Mac. Phase 1 prototyping is editor-bound (Claude reading + writing files, light IO). Phase 1 smoke runs (~5 min CPU each) scheduled around Phase 0 idle windows OR deferred to post-Phase-0 completion. Net contention < 10% on Phase 1 wall time. Not "zero serial cost" — but small-constant overhead, dominated by Phase 0's ~4-5h independent of Phase 1 outcomes.

**Acceptance:** 510 games complete; per-defender breakdown computed.

### Phase 1 — CAPX Prototype (1 session, ~3-4 hours)

**Files to create:**
- `minicontest/zoo_reflex_rc_tempo_capx.py` — `ReflexRCTempoCapxAgent(CaptureAgent)` class.
- `minicontest/zoo_reflex_rc_tempo_capx_solo.py` — solo wrapper (CAPX + StubB).

**Acceptance:**
- Prototype runs single game vs. baseline without crashing.
- `[CAPX_CAP_EATEN]` line appears at least once across 3-seed smoke.
- **N1 timing gate**: chooseAction wall time **p95 < 150ms over 200+ ticks** measured on Mac (1-game trace OR 3-game smoke aggregate). If exceeded, halt — auto-lower `CAPX_ASTAR_NODE_CAP` (2000 → 1500 → 1000 → 500) and re-measure. Cannot enter Phase 2.5 with p95 > 150ms.
- Per-tick `defender_dist_map` precompute < 15ms p95.

### Phase 2 — Smoke validation (3 defenders × 3 seeds = 9 games)

**Defenders:** `baseline`, `monster_rule_expert`, `zoo_dummy` (matches Step 2 smoke set).

**Acceptance:**
- vs. `zoo_dummy`: ≥ 2/3 cap_eat_alive (currently 0/3 with ABS).
- vs. `baseline`: ≥ 1/3 cap_eat_alive (currently 0/3 with ABS).
- vs. `monster_rule_expert`: ≥ 1/3 cap_eat_alive OR document why detour A* still fails (chokepoint topology evidence).

### Phase 2.5 — Tier-screening (P7) — 17 defenders × 5 seeds = 85 games (~45 min)

**Trigger:** Phase 2 PASS.

**Acceptance:** aggregate `cap_eat_alive ≥ 30%` across 85 games. If < 30% → halt, tune knobs (`CAPX_MIN_MARGIN`, `K_DETOUR`, `W2`, hysteresis), re-run Phase 2.5. Max 2 tuning iterations before escalating.

**Why this gate exists:** 510-game sweep is 4-6h. 85 game gate (45 min) catches catastrophic regressions before burning the full budget.

### Phase 3 — Wrapper fork + full matrix (P6) — 17 × 30 = 510 games

**Tasks (P6):**
1. Create `experiments/rc_tempo/pm46_v2_capx_matrix.sh` — copy of `pm46_v2_a_solo_matrix.sh` with `-r zoo_reflex_rc_tempo_capx_solo` and parser for `[CAPX_CAP_EATEN]`. Existing `pm46_v2_a_solo_matrix.sh` left UNCHANGED (ABS-only).
2. CSV columns: `defender, seed, outcome, eat_tick, eat_cap, a_pos_at_eat, a_alive_at_eat, ticks_after_eat, wall_s, fail_mode`.
3. Run on Mac, single-thread. Estimated 4-6 hours total.
4. Output: `experiments/results/pm46_v2/capx_matrix.csv`.

### Phase 4 — Analysis + iterate

- Per-defender breakdown: `cap_eat_alive %`, `died_pre_eat %`, regression-vs-ABS-baseline column.
- If §3.3 aggregate pass bars met → APPROVE → wiki entry → merge plan into pm47 (CAPX→submission integration; separate plan).
- If failed → diagnose via §9 pre-mortem scenarios, plan iteration.

---

## 7. Detailed TODOs (per phase)

### Phase 0
0a. Add `[ABS_CAP_EATEN]` emit to ABS-solo via shim (15 LOC). AC: smoke run on baseline RANDOM1 emits the line on cap eat.
0b. Run ABS-baseline 510 game with corrected detector. AC: CSV with all 510 rows; per-defender breakdown computed.

### Phase 1
1. **Create CAPX agent skeleton** — class, registerInitialState (≤15s budget), chooseAction with §5.1 loop. AC: imports OK, no crash on registerInitialState.
2. **Implement defender-aware A*** — see §5.2. Imports per §4.1 G1 whitelist. AC: unit-style smoke — A* finds path on RANDOM1 layout from spawn to nearest cap with detour=4, returns list of cells; A* node-cap=500 honored.
3. **Implement gate policy** — §5.3 with env flags `CAPX_MIN_MARGIN`, `CAPX_HARD_ABANDON_MARGIN`, `CAPX_DETOUR_BUDGET`, `CAPX_ASTAR_NODE_CAP` (default 2000 — N1), `CAPX_CLOSE_PENALTY`, `CAPX_APPROACH_MODE`, `CAPX_MIN_PSURVIVE` (default 0.2 — N2), `CAPX_EXIT_ON_EAT`, `CAPX_TRACE`. AC: 4 unit cases (TRIGGER, hysteresis-sticky, hard-abandon, approach-mode) pass + 1 case for N2 floor fallback (all-caps below floor → distance-only rank).
4. **Implement cap-eat detection** — track `prev_caps` set, on decrease emit `[CAPX_CAP_EATEN]` with `a_alive_at_eat` flag. AC: smoke run shows line on baseline+seed1.
5. **Create solo wrapper** — `zoo_reflex_rc_tempo_capx_solo.py`. AC: capture.py runs `-r zoo_reflex_rc_tempo_capx_solo` without crash.

### Phase 2
6. Run 3×3 smoke. AC: per §6.2 thresholds.

### Phase 2.5
7. Run 17×5 tier-screen. AC: per §6 Phase 2.5 thresholds (≥ 30% aggregate cap_eat_alive).

### Phase 3
8. Create `pm46_v2_capx_matrix.sh` (P6). AC: script runs smoke (3×3) cleanly with new parser.
9. Full 17×30 run. AC: CSV complete, no >5% timeout/error rate.

### Phase 4
10. Analysis script — group_by(defender) aggregates `cap_eat_alive` and `died_pre_eat`. AC: table in plan + wiki entry.

---

## 8. Measurement Protocol

**Defender set:** 17 (per `.omc/wiki/2026-04-29-pm46-v2-step-0-defender-zoo-inventory.md`).

**Seeds:** RANDOM1–RANDOM30 (30 fixed seeds).

**CAPX wrapper command:**
```bash
cd minicontest && timeout 90 env CAPX_EXIT_ON_EAT=1 PYTHONHASHSEED=0 \
  ../.venv/bin/python ../experiments/rc_tempo/pm45_single_game.py \
  -r zoo_reflex_rc_tempo_capx_solo -b $DEF -l RANDOM$SEED -n 1 -q
```

**ABS-baseline wrapper command (Phase 0):**
```bash
cd minicontest && timeout 90 env PYTHONHASHSEED=0 \
  ../.venv/bin/python ../experiments/rc_tempo/pm45_single_game.py \
  -r zoo_reflex_rc_tempo_abs_solo -b $DEF -l RANDOM$SEED -n 1 -q
```

**CSV columns:** `defender, seed, outcome (eat_alive / eat_died / no_eat / timeout), eat_tick, eat_cap, a_pos_at_eat, a_alive_at_eat (bool), ticks_after_eat, wall_s, fail_mode`.

**fail_mode taxonomy:**
- `eat_alive` — success (P3 primary criterion)
- `eat_died` — cap eaten but A died at eat tick or within 3 ticks → **does not count toward primary success**
- `died_pre_eat` — A killed before any cap consumed
- `oscillation_no_commit` — A reached path_len ≤ 5 of a cap but ticks elapsed without eat
- `chokepoint_blocked` — defender held chokepoint, A never approached
- `timeout` — 1200 ticks elapsed, no eat
- `other` — unclassified

**Wall-time budget:** 90s per game timeout. With `CAPX_EXIT_ON_EAT=1`, expected mean ~30s. Total ≈ 4-5 hours.

---

## 9. Risk Register + Pre-mortem

### 9.1 Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| R1: A* with detour=4 still fails on monster_rule_expert chokepoint | Medium | Low (Tier-A bound) | Increase K to 6-8 (hard cap 8 per P11); document if topology fundamentally blocks |
| R2: Hysteresis traps A in losing race (committed → death) | Medium | High (worse than ABS) | **Hard abandon override `CAPX_HARD_ABANDON_MARGIN` (P2)** — if next-3 margin < -1, abandon regardless of hysteresis. Separates path-stability from suicide-prevention. |
| R3: chooseAction wall time blows up on large detour budget | Low | Medium | A* node cap 500 (P5); `defender_dist_map` precompute O(N×cells); fallback to direct BFS on overflow |
| R4: registerInitialState 15s budget exceeded | Very Low | High (forfeit) | No expensive precomputation; just cache walls reference |
| R5: CAPX wins on cap but loses on robustness — submission still uses ABS | Low | Low | This plan does NOT modify submission. CAPX is research artifact. Decision to merge into submission is a separate plan. |
| R6: Cap-eat detection misfires (e.g., scared-window expiry confused with eat) | Low | Medium | `len(getCapsules())` decrement + Red proximity verify; eat marker has `eater_idx` for audit |
| R7: Hidden interaction with `_ABS_TEAM` global on ABS module import | Low | Medium | **Import whitelist (P8)** — only 4 named helpers. Forbidden: classes, `_build_once`, `_reset_abs_team`, wildcard. |
| R8: ABS-baseline metric mismatch makes CAPX comparison invalid | High → resolved | High | **Phase 0 (P4) re-measurement with `[ABS_CAP_EATEN]` detector before any comparison claim.** |
| R9: Survival-weighted ranker prefers far-but-safe → never reaches any cap | Medium | High | Tier-screening Phase 2.5 catches; if hits, add `bfs_dist ≤ N` filter or unweight P_survive in cap-rank |
| R10: P_survive sigmoid scale wrong (too sharp / too flat) | Low | Medium | Phase 2 trace logging exposes; tune in Phase 4 if needed |
| R11 (N6): A* p95 wall-time exceeds 200ms budget on Mac under 2000-node cap | Medium | High (forfeit risk if >1s) | **N1 Phase 1 timing-gate AC**: auto-lower `CAPX_ASTAR_NODE_CAP` (2000→1500→1000→500) until p95 < 150ms; direct-BFS fallback on overflow retains correctness at all caps. |

### 9.2 Pre-mortem (P10) — 3 named failure scenarios

#### Scenario S1 — **Algorithmic moot** (CAPX ≈ ABS ± 5%)

**Symptom:** Phase 3 result: CAPX `cap_eat_alive` within ±5% of ABS-baseline aggregate. No Tier shows clear improvement.

**Diagnosis:** the gate redesign + A* detour didn't actually address the failure modes — defenders' threat is not gate-shaped, it's something else (e.g., spawn distance, cap-near-defender topology, defender-attack-radius).

**Action:** halt Phase 4 iteration. Open `omc-pm46-v3-cap-failure-root-cause.md` plan to investigate WHY the redesign doesn't help. Do NOT try variant tuning — the design is the problem.

#### Scenario S2 — **Eat-then-die** (cap_eat ≥ 50% but died_pre_eat ≥ 80% on Tier-A)

**Symptom:** CAPX gets to caps successfully, but dies on approach or just after. Aggregate `cap_eat ≥ 50%` headline looks good, but `cap_eat_alive` (P3 primary) fails because most "successes" are actually deaths.

**Diagnosis:** survival knobs (`CAPX_HARD_ABANDON_MARGIN`, P_survive sigmoid scale, hysteresis) too permissive. Agent commits to suicide races.

**Action:** Phase 4 knob retune in this order:
1. Tighten `CAPX_HARD_ABANDON_MARGIN` from -1 → 0 (more conservative).
2. Sharpen P_survive sigmoid scale (1.5 → 1.0).
3. Increase `CAPX_MIN_MARGIN` from 0 → 1 (i.e., back to ABS-level).
Re-run Phase 2.5 + Phase 3 with new knobs.

#### Scenario S3 — **Topology bound** (K=8 still 0/30 on monster_rule_expert)

**Symptom:** Even with `K_DETOUR=8` (hard cap, P11), monster_rule_expert defender achieves 0/30 cap_eat. A* finds no feasible path.

**Diagnosis:** RANDOM layout has a single chokepoint, and rule_expert defender holds it deterministically. There is no detour. This is a topology-level barrier, not an algorithmic gap.

**Action:**
1. Document failure with specific RANDOM seeds + chokepoint coordinates in wiki (`debugging/`).
2. Do NOT increase K beyond 8 (compute blows up; topology won't yield).
3. Accept rule_expert as unsolved-by-CAPX; flag for pm47+ (e.g., wait-for-defender-displacement strategy, or accept tournament loss against this defender).
4. Aggregate pass bar still requires Tier-A average ≥ 30%, so 1-2 unsolvable defenders are tolerable.

---

## 10. Out of Scope (explicit)

- Food harvest, scoring, deposit-28.
- Return-home routing.
- Scared-window post-cap food collection.
- cap2-after-cap1 chain.
- B-agent coordination (B is stub).
- Opponent classification / belief tracking.
- Submission file modification (`your_best.py` etc.).
- Tournament-mode (4-baseline loop) integration — uses `pm45_single_game.py` wrapper.
- Mode commit (`decide_plan_mode`) — that's pm46-1 territory (separate plan).
- Retrograde resurrection — pm45 closed.
- CAPX → submission migration — separate plan (pm47+).

---

## 11. Open Questions (deferred to user / Architect)

1. `CAPX_MIN_MARGIN` default — 0 or 1? (Plan: 0; survival emphasis may push to 1 if S2 hits.)
2. `CAPX_DETOUR_BUDGET` default — 4 (default) or 6 (more aggressive)? Hard cap = 8 per P11.
3. `CAPX_HARD_ABANDON_MARGIN` default — -1 (default) or 0 (stricter survival)?
4. `CAPX_EXIT_ON_EAT=1` as default? Saves wall time; lose post-eat survival data — but P3 already counts `eat_died` as failure based on first 3 post-eat ticks (achievable with `=1` if we delay 3 ticks before exit).
5. Phase 0 ABS-baseline re-run — confirm 510-game cost (4-6h Mac) acceptable in parallel with Phase 1 prototyping.
6. Tier-A acceptance bar — `cap_eat_alive ≥ 30%` realistic vs. ABS smoke evidence (~10%)? Or aim higher (≥ 40%)?
7. CAPX → submission integration path — defer to pm47+? Or commit a stub now?
8. **N2 `CAPX_MIN_PSURVIVE` floor 0.2** — retunable in Phase 4 if ranker-degenerate fallback (distance-only) fires too often (no signal from survival weight) or too rarely (floor never breached, defeating the safety net). Phase 4 trace exposes fire count.
9. **N1 `CAPX_ASTAR_NODE_CAP` default 2000** — appropriate for K_DETOUR=8 worst case on Mac? Phase 1 timing gate empirically validates; if 2000 routinely violates 150ms p95, structural redesign of A* (e.g., bidirectional, IDA*) becomes the agenda for pm47+.

(Append to `.omc/plans/open-questions.md` after Architect re-review.)

---

## 12. RALPLAN-DR Summary (iter-3)

### Principles (5)

1. **Single-purpose agent** — CAPX exists for one job: A reaches ≥ 1 capsule **alive**. No food, no scoring, no return-home.
2. **Survival as co-equal goal** — "필 죽지 않고 도착" — death-during-approach = failure. Algorithm and acceptance both reflect this.
3. **Greenfield, not extension** — new file, no modification of ABS or submission. Risk-free experiment. Strict import whitelist (P8).
4. **Online planning over precompute** — no offline tablebase, no retrograde V. Per-tick A* + simple gate, bounded by node-cap **2000 (N1)** + Phase 1 timing-gate auto-lowering. A* result cache (N3) prevents double-compute within a tick.
5. **Soft gate with hysteresis AND hard abandon** — F1/F2 are gate-policy bugs (replace, don't repair); F3 is suicide-prevention (separate knob `CAPX_HARD_ABANDON_MARGIN`).

### Decision Drivers (top 3)

1. **Survival-aware time-to-evidence** — must demonstrate `cap_eat_alive` improvement (NOT just `cap_eat`) within 1 session. Greenfield + survival-weighted A* + Phase 0 parallel re-baseline satisfies; deeper rewrites don't.
2. **No regression risk** — submission code untouched. Even worst-case CAPX failure costs nothing operationally.
3. **Generalization across 17 defenders** — handle weak (dummy oscillation), medium, and strong (rule_expert chokepoint) without per-defender tuning. A* + hysteresis + hard abandon address all four failure modes uniformly.

### Viable Options

#### Option A — **Greenfield CAPX agent with survival-weighted gate** (CHOSEN)

Pros:
- No modification to ABS or submission. Track-separation clean.
- Survival-weighted gate + A* detour cleanly attack F1-F4 + survival co-objective.
- Strict import whitelist (P8) avoids ABS init side-effects.
- Iteration cycle is fast — change CAPX, rerun matrix.
- Phase 0 ABS re-baseline (P4) parallel → zero serial cost.

Cons:
- Code duplication of BFS helpers (~10 LOC if imported, ~100 if copied).
- ABS's positional / classifier code can't be reused — but CAPX doesn't need it.
- Cap-eat detector duplicated in ABS-shim (Phase 0) and CAPX (Phase 1) — ~15 LOC each, same logic.

Invalidation conditions: A* detour fails ALL Tier-A defenders (≤ 5% cap_eat_alive across 7 strong defenders × 30 = 210 games) AND hard abandon doesn't fix the eat-then-die problem on Tier-B/C — would mean topology+threat fundamentally beats the design (S1 + S3 combined).

#### Option B — **Refactor ABS gate in-place** (NOT CHOSEN)

Approach: Modify `_a_first_cap_survival_test_bfs` and `_first_cap_pre_scared_action` to (a) consider detour paths via A*, (b) lower margin threshold, (c) add hysteresis + hard abandon.

Pros:
- All other ABS infrastructure (B coord, food, return-home) keeps working.
- Single-codebase fix.

Cons:
- High blast radius — ABS is 4084 lines, used by submission via `zoo_reflex_rc_tempo_abs_solo` and indirectly. Changes can regress on cap2 chain, B coordination, scoring.
- Function ownership conflict: `_gate_first_cap_trigger_action` is omx-pm44 territory. Modifying requires plan acknowledgement to omx track.
- Cannot easily isolate "capsule-only behavior" for clean measurement — confounded by chain logic.
- Difficult to A/B-test survival emphasis cleanly against ABS — same codebase, hard to compare iter.

Invalidation rationale: This plan's scope is **CAPX as standalone proof of concept**. ABS refactor is appropriate AFTER CAPX validates the algorithmic ideas, as a separate follow-up plan (pm47+).

#### Option C — **Replace gate with retrograde V table extension** (NOT CHOSEN)

Approach: Build retrograde V table for 2-defender (or 1-defender + cap-as-target) and use V == +1 as gate.

Pros:
- Mathematically optimal in chase subgame.
- Already 1-defender retrograde infrastructure exists from pm41.

Cons:
- pm45 explicitly closed retrograde branch — net negative on rule_expert (caps 5→1, deaths 5→11). Reactivating violates pm45 final decision.
- Tablebase build time (15s init budget risk on multi-cap, multi-defender).
- 2-defender state space ~ 30 × 30 × 30 × 40 = 1M states per cap — borderline init budget.
- Optimal-in-subgame ≠ survival-aware: V=+1 is binary, doesn't expose graceful-degradation knobs (P_survive, hard abandon).

Invalidation rationale: pm45 evidence shows retrograde over-commits to optimal-but-fragile lines. CAPX needs robust simple heuristic with survival knobs, not optimal solution.

---

## 13. Confirmation Checklist (for Architect re-review)

- [ ] Algorithm (§5.2 A* + §5.3 survival-aware gate) implementable in single Python file ≤ 700 lines?
- [ ] Wall time per chooseAction (§5.2 P5 precompute + 500-node A* cap) bounded < 200ms p95?
- [ ] Measurement protocol (§8) with corrected detector directly comparable to Phase 0 ABS-baseline?
- [ ] Survival-aware acceptance bars (§3.3) realistic given smoke evidence (§2.2)?
- [ ] Risk register (§9.1) covers regression vs. ABS, init budget, time budget, oscillation, eat-then-die?
- [ ] Pre-mortem (§9.2) S1/S2/S3 actionable on detection?
- [ ] Function ownership (§4.1 G1 P8 whitelist, §10) respects pm44 omx territory + avoids `_ABS_TEAM` side effects?
- [ ] Out-of-scope (§10) explicit and complete?
- [ ] Open questions (§11) decidable by user without further investigation?

---

## 14. Next-step entry point

After Architect re-review APPROVE + user confirmation:
- Execute Phase 0 (ABS re-baseline) + Phase 1 (CAPX prototype) in parallel.
- Or revise per critic feedback before execution.

`/oh-my-claudecode:start-work omc-pm46-v2-capsule-only-attacker`

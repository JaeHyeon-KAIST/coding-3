# CS470 A3 Strategy — Pacman Capture-the-Flag Championship Plan

**Student ID:** 20200492
**Framework:** UC Berkeley CS188 minicontest1 (Capture-the-Flag)
**Submission:** `your_best.py` → rename to `20200492.py`
**Deps:** Python 3.9, `numpy`, `pandas` only (no torch/sklearn/pretrained artifacts)

---

## 0. RALPLAN-DR Summary (reviewer entry point)

### Principles (5)
1. **Robustness ≥ cleverness.** A single crash costs -100 (CRASH_PENALTY) and almost always flips the game. Every search / evaluator must be wrapped in try/except with a legal-action fallback.
2. **Respect the 1s / 3s timer — but calibrate, don't guess.** Framework owns `signal.alarm` — unreusable. During Dev, use algorithmic bounds (`MAX_ITERS`/`MAX_DEPTH`) and trust the framework's 3s SIGALRM. At M7.5 Calibration, measure wall-clock p95/p99 and set final bounds data-driven. Time polling is an escape hatch, not the default. (See §3.3, §3.4.)
3. **Pay training cost, not inference cost.** All expensive tuning offline in `experiments/`; match-time is cheap dot products + bounded search. Weights inlined as Python literals.
4. **Design for the unknown TA opponent, not only for `baseline.py`.** Opponent pool + niching + HALL_OF_FAME prevent overfit.
5. **Methodological contrast is a deliverable.** Three `your_baselineN.py` files are the report's comparison axes (reflex / minimax / MCTS).

### Decision Drivers (top 3)
1. **Robustness to unknown tournament opponents** (non-negotiable; >30% error → 0 pts).
2. **40-pt baseline gate + 30-pt tournament ranking.**
3. **60-pt report with 3 algorithm families + performance curve.**

### Viable Options (3)

**Option A — Pure MCTS champion (single algorithm).**
Pros: (1) published 95-100% vs baseline with heuristic rollout [kkkkkaran wiki]; (2) anytime; (3) simplest architecture.
Cons: (1) still needs hand-crafted rollout policy; (2) weakest report story; (3) Python limits to ~100-500 iters/sec.

**Option B (SELECTED) — Hybrid evolved champion.** MCTS-depth-0 offense + minimax-2 defense + approx-Q eval, weights evolved offline via CEM self-play.
Pros: (1) matches COMP90054 43.4/45 pattern [abhinavcreed13]; (2) algorithmic specialization per side; (3) three sibling baselines give clean ablation.
Cons: (1) larger codebase (mitigated by shared base + try/except discipline); (2) ~10h evolution engineering; (3) role-switching bug surface (mitigated by hysteresis).

**Option C — Approximate Q-learning only.** Pros: O(1) inference. Cons: 30-40% ceiling [kkkkkaran wiki] endangers 40-pt gate; no lookahead.

**Selection:** Option B. A rejected: loses ~20 report pts for no inference gain. C rejected: win-rate ceiling threatens baseline gate.

### Mode: SHORT (default). No `--deliberate`.

---

## 1. Objective & Success Criteria

| Criterion | Threshold | Measurement |
|---|---|---|
| Win rate vs `baseline.py` | **Statistical gate: ≥65%** at n=80 (Wilson lower bound 0.538 > 0.5, distinguishable from random); **Administrative floor: ≥51%** per PDF rubric (noted as NOT statistically detectable at n=80); **Stretch: ≥90%** (Wilson lower bound 0.815, strongly significant) | **Canonical:** §7.1 400-game matrix (8 layouts × 5 opponents × 2 colors × 5 seeds). Gate slice = `opponent=baseline.py` → 80 games. Auxiliary stress matrix (570 games across extended layouts + RANDOM seeds) for generalization audit. **Important:** the 51% PDF-level floor is administrative — passing it means "not trivially worse than random" but does NOT statistically distinguish true skill. Plan for ≥65% minimum in dev/eval for any agent worth submitting |
| Crash / error rate | <5% | Count games with unhandled exception or 3s SIGALRM |
| Avg move time | <0.85s; p99 <0.95s | `time.time()` instrumentation |
| Tie rate | <15% | Push for decisive wins |
| Robustness across pool | ≥65% vs 10+ past-gen champions | Self-play round-robin |
| Reproducibility | Deterministic given seed | Seed-fixed pipeline |
| Report artifacts | 3 algos, 3+ figures, per-layout table | From `output.csv` |
| Submission packaging | `20200492.py` single file, no external state | Section 10 step 10 script |

Stretch: top-5 tournament ranking (30 extra points) → ≥65% vs unknown TA pool.

---

## 1.5 Development vs Submission Scope (critical distinction)

**Submission to TA (hard constraint):** Exactly **1 `.py` file** in the zip — `20200492.py` (renamed from `your_best.py`). The ZIP contents per the assignment PDF are `{id}.py + {id}.pdf + {id}.pptx` — NOT the baseline files.

**Required for local evaluation & report (also filename-mandated by framework):** `minicontest/your_baseline1.py`, `your_baseline2.py`, `your_baseline3.py`. These are used ONLY locally when the student (or TA, for the report table reproduction) runs `python capture.py -r 20200492 -n 10`, which produces `output.csv` with match results of `your_best` vs each of these three + `baseline.py`. The three files stay in `minicontest/` for capture.py's import, but are not included in the submission ZIP.

**Development (no upper bound):** Under `experiments/zoo/` we build ≥10 agent variants as (a) self-play opponents during evolution, (b) evaluation references for ELO, (c) seed genomes for CEM, (d) ablation controls for the report. See Section 4.0.

**Selection → slot-fill:** `experiments/select_top4.py` runs zoo + evolved champions + baseline.py in round-robin, computes ELO, and emits:
- `your_best.py` = overall champion (submitted, renamed)
- `your_baseline1~3.py` = 3 interesting family-representatives (local only, for output.csv richness + Methods section narrative)

`your_baseline1~3` file contents can be swapped freely during development (`cp experiments/zoo/<variant>.py minicontest/your_baselineN.py && rerun capture.py`) to test different comparison narratives before finalizing.

**Rationale:** The larger development pool prevents overfit to `baseline.py`. The three locally-installed "your_baseline*" files give the Results section (20pt) richer comparative material than just `my_best vs baseline` alone. Submitting the one file keeps the TA packaging clean.

---

## 2. Algorithm Assignments per File

| File | Algorithmic family | Rationale | Expected win rate vs baseline |
|---|---|---|---|
| `your_baseline1.py` | Tuned feature-reflex (weighted linear eval) | Fastest to implement; establishes shared feature dict; fixes baseline's 7 exploits directly; report's "reflex" family. | 55-70% |
| `your_baseline2.py` | ID minimax + α-β, opponent-model reduction | Adversarial lookahead; reduction collapses 4-agent tree to 2-agent (closest enemy) → depth 3-4 feasible; report's "search" family. | 70-80% |
| `your_baseline3.py` | MCTS + heuristic rollout (UCT) | Anytime simulation; uses reflex eval as tree-policy prior and rollout policy; report's "simulation" family. | 75-85% |
| `your_best.py` → `20200492.py` | Evolved hybrid: MCTS-depth-0 offense + minimax-2 defense + capsule policy + role switching + bottleneck avoidance. Weights inlined. | Combines MCTS robustness (offense) and minimax sharpness (defense); evolved weights generalize across opponents. | ≥90% target |

---

## 3. Core Agent Architecture (shared by all 4)

All four files inherit from an inlined `CoreCaptureAgent(CaptureAgent)` (single-file constraint forces code duplication).

### 3.1 Shared responsibilities

- **State snapshot** `snapshot(gameState)` → dict of `myPos, myState.isPacman, scaredTimer, numCarrying, foodList, defendFoodList, capsuleList, opponentPositions (fully visible per code inspection), teamPositions, mazeDist`. All algorithms consume this.
- **Distance cache:** relies on framework's process-global `distanceMap` keyed by `layout.walls`; `self.getMazeDistance(a,b)` is O(1) after `registerInitialState` populates it via `self.distancer.getMazeDistances()`.
- **Timer budget:** **deferred to Calibration (M7.5)** — see Section 3.3 phased discipline. During dev, use algorithmic bounds (`MAX_ITERS`, `MAX_DEPTH`, `ROLLOUT_DEPTH`) as int constants; ID/MCTS return best-so-far whenever the bound is reached. Time polling added post-calibration only if wall-clock variance demands it.
- **Crash-proof wrapping (two-layer, timeout-preserving):**
  ```python
  # Framework uses signal.SIGALRM → raises TimeoutFunctionException (util.py:591)
  # We MUST NOT swallow it — framework needs to handle timeout bookkeeping.
  from util import TimeoutFunctionException  # imported at top of each submitted file

  def chooseAction(self, gameState):
      self.turn_start = time.time()
      try:
          action = self._chooseActionImpl(gameState)
          legal = gameState.getLegalActions(self.index)
          if action not in legal:
              action = self._safeFallback(gameState, legal)
          return action
      except TimeoutFunctionException:
          raise  # let framework see it; agent timed out, framework records warning/forfeit
      except Exception:
          try:
              legal = gameState.getLegalActions(self.index)
              fallback = self._safeFallback(gameState, legal)
              if fallback in legal:
                  return fallback
              # fallback was not legal — try a non-STOP legal
              non_stop = [a for a in legal if a != Directions.STOP]
              return random.choice(non_stop) if non_stop else Directions.STOP
          except TimeoutFunctionException:
              raise
          except Exception:
              return Directions.STOP  # absolute last resort (always legal)
  ```

  **Why STOP is ONLY last-resort:** in a tournament, `Directions.STOP` is "almost always a death sentence" (a stationary Pacman gets eaten by chasing ghosts, a stationary ghost lets invaders pass). Prefer `random.choice(legal - {STOP})` when any non-STOP legal action exists. STOP only when the legal action list is empty or retrieving it itself fails.

  `_safeFallback(gameState, legal)` = reflex evaluator from baseline1, ≤5ms, expected not to raise. Takes `legal` so it can pick from within the pre-computed legal set. Even this path's return is re-validated against `legal` before dispatch.

  **Critically:** `TimeoutFunctionException` is explicitly re-raised before the generic `except Exception` catch. Without this, our broad `except Exception` would swallow the framework's own SIGALRM-triggered exception, corrupt the warning counter semantics, and risk the game hanging or mis-scoring. (`util.py:591-593` defines it; `util.py:602` raises it from the handler.)
- **Scared detection:** `gameState.getAgentState(i).scaredTimer > 0`.
- **Bottleneck detection:** precomputed in `registerInitialState` — cell is bottleneck if its enemy-side removal disconnects neighborhood (BFS articulation proxy). Stored as `frozenset`. Simplified from Ford-Fulkerson pattern in [abhinavcreed13].
- **Feature vector:** ~20 features, computed once per `chooseAction`, reused across evaluator calls in search.

### 3.2 Init budget (15s) — crash-proof, APSP-precomputed

**Gemini insight:** the 15s registerInitialState budget is a superpower we barely use. Base plan used ~4s; we should consume 10-12s precomputing structures that make every subsequent `chooseAction` faster.

Shared `CoreCaptureAgent.registerInitialState` wraps **every step** in try/except with graceful degradation. A 15s init crash = forfeit; we must not raise.

```python
def registerInitialState(self, gameState):
    try:
        CaptureAgent.registerInitialState(self, gameState)  # base distancer
    except Exception:
        pass
    try:
        self.start = gameState.getAgentPosition(self.index)
    except Exception:
        self.start = None
    try:
        self.apsp = self._precomputeAPSP(gameState)  # All-Pairs Shortest Path
    except Exception:
        self.apsp = None  # fallback: use self.distancer (slower)
    try:
        self.bottlenecks = self._computeBottlenecks(gameState)
    except Exception:
        self.bottlenecks = frozenset()
    try:
        self.homeFrontier = self._computeHomeFrontier(gameState)
    except Exception:
        self.homeFrontier = []
    try:
        self.deadEnds = self._precomputeDeadEnds(gameState)  # dead-end map
    except Exception:
        self.deadEnds = frozenset()
    try:
        if not hasattr(TEAM, 'initialized') or not TEAM.initialized:
            TEAM.reset(gameState)
    except Exception:
        TEAM.force_reinit()
```

Steps:
1. `self.distancer.getMazeDistances()` (base) — ~1-2s on large layouts.
2. **`self.apsp` — All-Pairs Shortest Path dict `{(pos1,pos2): dist}`** via N-runs BFS. Makes `getMazeDistance` O(1) dict lookup (vs. framework's default which can recompute). Target ~3-5s on largest layouts. Reduces per-move feature-computation jitter.
3. `self.bottlenecks` (BFS articulation) — target <2s.
4. `self.deadEnds` (one-exit cells with depth ≥3) — target <1s. Used by `f_inDeadEnd` feature.
5. `self.homeFrontier` (border-column list) — <100ms.
6. Init `TeamGlobalState` singleton (≤1ms).

Total budgeted init: **10-12s** (vs. 15s cap); **generous buffer**. All steps independently guarded. Crash-proof guarantee: `registerInitialState` returns successfully on any input.

### 3.3 Per-move budget — **phased, data-driven** (not pre-budgeted)

Timing caps are **deferred to the Calibration milestone (M7.5)**, not hard-coded upfront. Guessing `0.70s` without measurement leads to either over-conservative algorithms (wasted headroom) or over-optimistic algorithms (silent warnings). Instead:

| Phase | Time discipline | Rationale |
|---|---|---|
| **Dev (M1–M7)** | **Algorithmic bounds only** — MCTS `MAX_ITERS=1000`, minimax depth cap `MAX_DEPTH=3`, `ROLLOUT_DEPTH=20`. No `time.time()` polling. | Structural bounds are deterministic and easy to reason about. Framework SIGALRM (3s hard forfeit) catches genuine runaway cases during development. Warning counts in game output surface timing issues naturally. |
| **Calibration (M7.5)** | Run each submission candidate through `-n 100 -q` benchmark. Measure **p50, p95, p99 move time** on dev hardware. Then run `taskset -c 0 cpulimit --limit 50` to simulate ~50% TA-server speed. | Empirical calibration: if p99 > 0.85s on dev, reduce `MAX_ITERS` / `MAX_DEPTH` until p99 < 0.80s; if throttled-p99 > 0.95s, tighten further. Set `MOVE_BUDGET` based on this measurement, not a guess. |
| **Submission (M10)** | Shipped caps = measured p95 + small margin, **encoded as algorithmic bounds** (iter/depth ints). Add `time.time()` polling **only if** calibration shows wall-clock variance >20% across 100 games (e.g., GC-heavy layouts). | Simplicity wins: fewer code paths, fewer crash surfaces. Polling is an escape hatch, not the default. |

**Framework-level safety nets (always active, no code required):**
- `signal.alarm(3)` — hard forfeit at 3s per move.
- Warning counter: 3rd >1s warning = game loss.
- Framework's `TimeoutFunction` in `minicontest/util.py:596-622` owns SIGALRM; we do not touch it.

**Do NOT** commit `self.MOVE_BUDGET = 0.70` as a module constant during dev — it's a calibrated-in-M7.5 value.

### 3.4 Compute Budget — Dual Scope (CRITICAL)

Two entirely separate compute budgets. Mixing them is the single biggest design pitfall in this plan.

**Submission-time agent budget (framework-imposed; internal cap = M7.5 calibrated):**
- Framework: **wall-clock ≤ 1s per move warning; 3s → instant forfeit; 2 warnings accumulate, 3rd = loss.** (`minicontest/capture.py:448-455`)
- **Single CPU core assumed.** TA grading server hardware unknown and likely slower than M1/M2 Mac.
- **Internal cap is NOT pre-decided.** During Dev (M1–M7) we rely on **algorithmic bounds** (`MAX_ITERS`, `MAX_DEPTH`, `ROLLOUT_DEPTH`) and the framework's 3s SIGALRM. At M7.5 we measure p95/p99 wall-clock move time across 100 games per candidate (on dev hardware and under `taskset -c 0 cpulimit --limit 50` TA simulation), and set the final `MAX_ITERS`/`MAX_DEPTH` integers such that p99 < 0.80s on dev AND throttled p99 < 1.0s (no warnings in simulated TA environment).
- **`signal.alarm` is owned by the framework** (`minicontest/util.py:589-622`). **Never register our own handler.** If calibration proves time polling is needed, use `time.time()` with amortized checks (every N=100–1000 expansions).
- **TA-simulation commands:** `taskset -c 0 cpulimit --limit 50 .venv/bin/python minicontest/capture.py -r <agent> -b baseline -n 20 -q` (Linux); `sudo renice 19 $$; cpulimit -l 50` or similar on macOS. Acceptance at M7.5: 0 warnings across 20 games.

**Training-time compute budget (soft, our machine):**
- `experiments/tournament.py` uses `multiprocessing.Pool` / `concurrent.futures.ProcessPoolExecutor` for parallel game subprocesses.
- **Parallel-pool size ≤ physical core count.** Oversubscribing (e.g., 16 workers on 8 cores) makes each subprocess's `signal.alarm`-based wall-clock budget shrink in *CPU-time* terms → favors shallow-but-fast agents during training → evolution overfits to "fast" not "strong."
- **Pin each subprocess to a dedicated core** via `os.sched_setaffinity` (Linux) or `taskset -c N` before calling `capture.py`. macOS does not expose per-thread affinity, so on macOS cap workers at `physical_cores - 1` to leave kernel/UI headroom.
- **Optional for pure training (not deployment):** swap wall-clock deadline for an **iteration-count deadline** during self-play — deterministic across oversubscription. Switch back to time-based at deployment.
- **GPU: not used.** Game engine is sequential Python; CPU-bound; GPU transfer overhead dominates. Confirmed via code inspection (no vectorizable tight loops, small dict/tuple state ops).

---

## 4. Per-Algorithm Design

### 4.0 Development Zoo (`experiments/zoo/`, not submitted)

The zoo is the **development population — open-ended, no upper bound**. It is not subject to the 4-file submission cap; `experiments/select_top4.py` picks the four representatives after evolution. All zoo files inherit the shared `CoreCaptureAgent` (Section 3) during development and are flattened into stand-alone modules at submission time.

**Rules of the zoo:**
- **Add agents freely** whenever a new idea surfaces (a novel heuristic, a weird experimental combo, a 2 AM insight). File it in `experiments/zoo/` and it automatically joins the next tournament.
- **No cap** on zoo count. 12, 20, 50 variants — all fine.
- **No cap on baseline count either**: even though only 3 `your_baselineN.py` files are submitted, during development we might have 10+ "baseline-style" reflex variants and 10+ "baseline-style" minimax variants in the zoo. `select_top4.py` chooses which 3 represent the families for the final submission.
- **The only cost** of adding an agent is one extra tournament slot per generation (linear in pool size). As long as the generation wall-clock stays ≤10h, add as many as is useful.
- **During evolution**, each generation additionally spawns N=40 genome-parameterized instances (Phase 2a/2b, §6.3). These are *ephemeral* — not added to the zoo permanently unless promoted to Hall-of-Fame or serialized as `champion_genN.py`.

Initial seed population (start here; grow during development):

| Zoo file | Category | Purpose |
|---|---|---|
| `reflex_tuned.py` | reflex (offense-heavy) | `your_baseline1.py` seed, gen-0 of evolution |
| `reflex_capsule.py` | reflex + capsule module | ablation control for capsule policy |
| `reflex_aggressive.py` | reflex w/ `numCarrying × 5` bias | variety in opponent pool |
| `reflex_defensive.py` | reflex w/ `f_numInvaders × 10` bias | variety in opponent pool |
| `minimax_ab_d2.py` | minimax α-β depth 2, 1-enemy reduction | `your_baseline2.py` seed |
| `minimax_ab_d3_opp.py` | minimax α-β depth 3, 2-enemy reduction | baseline2 stretch |
| `expectimax.py` | expectimax + fixed opponent policy | compare to minimax for report |
| `approxq_v1.py` | approx-Q w/ 10 features, frozen weights | "learning" family representative |
| `approxq_v2_deeper.py` | approx-Q w/ 20 features, richer weight set | ablation |
| `mcts_random.py` | MCTS + random rollout | **control** — known-bad; verifies test plumbing catches regressions |
| `mcts_heuristic.py` | MCTS + reflex-argmax rollout (depth 20) | `your_baseline3.py` seed |
| `mcts_q_guided.py` | MCTS depth-0 + approx-Q leaf eval | `your_best.py` seed |
| `pddl_offense.py` (stretch) | Classical-planner-style offense + reflex defense | search-diversity exploration |
| `bt_hybrid.py` (stretch) | Behavior-tree over MCTS/minimax sub-policies | coordination exploration |
| `champion_genN.py` | serialized evolved champions | Hall-of-Fame pool |

**Representative selection for submission (post-evolution):**
```
experiments/select_top4.py:
  1. Run full round-robin: zoo ∪ {baseline.py} ∪ champions
     (5 layouts × 2 color swaps × 3 seeds = 30 games per pair)
  2. Compute ELO and win-matrix
  3. Pick (with FAMILY-FLOOR clause):
     your_best.py        = argmax ELO across ALL
     your_baseline1.py   = argmax ELO in reflex-family
     your_baseline2.py   = argmax ELO in minimax/expectimax-family
     your_baseline3.py   = argmax ELO in MCTS-family
  4. FAMILY-FLOOR CHECK: for each baselineN, run 100-game eval vs baseline.py.
     If < 51% win rate → select_top4.py logs the failure, then:
       - Fall back to next-best agent in the family (even if lower ELO).
       - If no agent in family reaches 51%, fall back to the next-best
         agent across ALL families that satisfies 51% AND is not already
         selected as your_best. Document the substitution in docs/AI_USAGE.md.
       - Rationale: the 40-pt rubric is per-file win rate, not "family purity."
         Methods section in report acknowledges the substitution honestly.
  5. Flatten each into stand-alone file (inline all CoreCaptureAgent methods)
  6. RUN `experiments/verify_flatten.py <flattened_file>` which checks:
     (a) AST self-containment — file imports only from {captureAgents, util,
         game, random, time, numpy, pandas, sys, os, math, itertools, collections}
         — forbidden import grep returns empty
     (b) No `import torch|sklearn|tensorflow|pickle|requests|urllib`
     (c) sha256 of the extracted `computeFeatures` function body MATCHES
         the sha256 of the pre-flatten zoo source (identity guarantee)
     (d) File parses via `ast.parse()` without SyntaxError
     (e) File runs `python -c 'import <file>'` without ImportError
     Failing any → log and DO NOT proceed.
  7. POST-FLATTEN BEHAVIORAL EQUIVALENCE: run 50 games head-to-head
     between pre-flatten (zoo version) and post-flatten (copied) agent.
     If win rate between them is not [45%, 55%] (i.e. not near-identical),
     flag flatten bug. ROLLBACK: auto-demote to next-ELO candidate in
     same family; re-run steps 5-7. After 3 rollback attempts, escalate
     to human for debug.
  8. Tie-break in ELO: deterministic — by genome hash for evolved agents
     (sha256 of `(W_OFF, W_DEF, PARAMS)` tuple), by filename lex order
     for hand-coded zoo agents.
  9. Write to minicontest/.
```

**`experiments/verify_flatten.py`** is a first-class submission-gate script; spec lives alongside this plan. Also reused at §8.4 step 1 (final submission packaging) — single source of truth.

**TA-hardware robustness pre-check (separate from flatten):** before step 3 finalizes, the top-5 ELO candidates are re-evaluated under a CPU-throttled simulation (`taskset -c 0 cpulimit --limit 50` on Linux; `sudo renice 19` + single-core pin on macOS). If the best-ELO agent's win rate vs. baseline.py drops by >15 percentage points under throttling, it is **demoted** and the next candidate is tested. This guards against agents that only work with fast dev-hardware search depths.

Stretch zoo items (`pddl_offense.py`, `bt_hybrid.py`) are optional; build only if time permits after M6. Skipping them does not block submission.

**Mid-development additions** (expected, not exceptional): during M2–M6 we will invent new variants as we learn what works. Examples that typically emerge:
- `reflex_bottleneck_avoid.py` — reflex with bottleneck penalty cranked up
- `minimax_ab_d2_pincer.py` — minimax that always models the pincer-threat enemy rather than nearest
- `mcts_progressive_widening.py` — MCTS with depth-adaptive exploration
- `approxq_residual.py` — approx-Q with residual features from eval traces
- `champion_gen17_replica.py` — a frozen snapshot of an interesting mid-evolution genome for the HoF pool
- `monster_cheese.py` — an exploiter agent found during eval that beats all current agents, added as a strong reference

Add them. File them. Let them join the tournament. The best floats to top-4.

### 4.1 Tuned Feature-Reflex (`your_baseline1.py`)

**Features (20):**

Offensive: `f_successorScore, f_distToFood, f_distToCapsule, f_numCarrying, f_distToHome, f_ghostDist1, f_ghostDist2, f_inDeadEnd, f_stop, f_reverse`.
Defensive: `f_numInvaders, f_invaderDist, f_onDefense, f_patrolDist, f_distToCapsuleDefend, f_scaredFlee`.
Shared: `f_bias`.

Explicit definitions with numeric guards (prevents `ZeroDivisionError`, inf, NaN — Risk #4):
- `f_distToFood = 1/max(min_dist_to_remaining_food, 1)` (clamp at 1 to protect against on-food case)
- `f_ghostDist* = -1/max(dist, 1)` of two nearest active enemy ghosts; if no active ghost, feature = 0
- `f_inDeadEnd = 1` if successor has only 1 non-back exit AND active ghost within 4
- `f_patrolDist = 1/max(dist, 1)` to rotating patrol anchor among choke points
- `f_scaredFlee` reverses `f_invaderDist` sign when `scaredTimer>0`
- All feature computations wrapped in try/except returning 0 on failure (never raise; never emit inf/NaN).

**Seed weights (gen-0 of evolution):**
```python
WEIGHTS_REFLEX = {
    'f_bias': 0.0, 'f_successorScore': 100.0, 'f_distToFood': 10.0,
    'f_distToCapsule': 8.0, 'f_numCarrying': 5.0, 'f_distToHome': 4.0,
    'f_ghostDist1': -50.0, 'f_ghostDist2': -10.0, 'f_inDeadEnd': -200.0,
    'f_stop': -100.0, 'f_reverse': -2.0,
    'f_numInvaders': -1000.0, 'f_invaderDist': 30.0, 'f_onDefense': 100.0,
    'f_patrolDist': 5.0, 'f_distToCapsuleDefend': -3.0, 'f_scaredFlee': -1.0,
}
```

**Decision:** argmax of `sum(w[f]*features[f])`; tiebreak uniform random with fixed seed.

**Fixes for 7 baseline exploits:** (1) ghost/deadend features; (2) `f_distToHome` when `numCarrying≥threshold`; (3) `f_patrolDist` rotating anchors; (4) large `f_numInvaders` + role-lock when invaders present; (5) capsule features + capsule module; (6) TeamGlobalState; (7) strong `f_stop`/`f_reverse` penalties.

**Known failure modes:** tunnel vision when >2 ghosts pincer (fixed in baseline2/best by lookahead); decision flipping per tick (partially fixed by `f_reverse`).

### 4.2 Minimax + α-β with ID (`your_baseline2.py`)

**Opponent model reduction — honest framing.** A full 4-agent game tree is 5^4=625/ply, infeasible in 0.70s. Two-enemy collapse is the **primary target**:
- **Default (promoted):** 2-enemy minimax with α-β depth 3, both enemies modeled adversarially, aggressive move-ordering pruning. Estimated ~500-1500 nodes/sec in Python → depth 3 reliably on most layouts, depth 4 on small maps.
- **Fallback (if depth 3 misses 0.70s on `jumboCapture`/`distantCapture`):** 1-enemy-closest minimax with other enemy frozen at last-observed position, depth 2-3. **This fallback is not true adversarial minimax**; the frozen-enemy approximation fails on coordinated-pincer opponents (documented failure mode).
- The 1-enemy fallback is chosen dynamically at init time based on measured node-rate during a 200ms probe; persists for the game.

**Reporting note:** In the report's Methods section, we describe this as "2-enemy α-β minimax with aggressive pruning (fallback to 1-enemy frozen on large layouts)." We do **not** claim full 4-agent adversarial optimality.

**Eval:** identical feature vector + weights as Section 4.1.

**ID loop:**
```python
def chooseAction(self, gameState):
    self.turn_start = time.time()
    best_action = self._safeFallback(gameState)
    for depth in range(1, 6):
        if time.time() - self.turn_start > self.MOVE_BUDGET * 0.75:
            break
        try:
            action, val = self._alphaBeta(gameState, depth, -inf, inf, True, self.turn_start)
            if action is not None: best_action = action
        except TimeoutError:
            break
    return best_action
```
Inner α-β polls at every node; raises `TimeoutError` if budget exceeded; partial depth discarded.

**Expected depth:** 2 reliably, 3 on most layouts, 4 on `tinyCapture`/`testCapture`. ~500-2000 nodes/sec.

### 4.3 MCTS with heuristic rollout (`your_baseline3.py`)

**UCT** `c = sqrt(2)` initially (evolvable).

**Node key:** `(myPos, enemyPositions_tuple, foodCount_self_side, capsulesLeft, scaredTimer_enemies)` for transposition (full gameState hashing too expensive).

**Tree policy:** UCB1.

**Rollout policy — two variants, with honest naming for each:**
- `your_baseline3.py` = **MCTS with heuristic rollout** (the real thing): each simulation expands a leaf, performs a `ROLLOUT_DEPTH=20` heuristic rollout (argmax of reflex evaluator at each step), propagates the leaf-derived terminal/heuristic value up the tree. This is genuine Monte Carlo simulation. Random rollouts are rejected per [reporkey wiki].
- `your_best.py` = **UCB-guided leaf-evaluator search** (honest framing of "depth-0 MCTS"). We retain MCTS's tree construction + UCB1 selection, but the "rollout" is a direct call to the feature evaluator. Mathematically this is **not** Monte Carlo sampling — it is best-first tree enumeration with an exploration bonus. We deliberately call it "UCB-guided leaf search" in the report to avoid the semantic overclaim. Pattern matches [abhinavcreed13] which also uses leaf-eval-only in its top-ranked submission.

**Why the split:** Principle 5 (methodological contrast) requires clear family distinctions. `baseline3` = Monte Carlo family; `best.py` = best-first search family with learned leaf eval. This is architecturally cleaner than both being "MCTS."

**Iters/sec:** 100-500 heuristic-rollout; 1000-3000 leaf-eval-only.

**Return:** robust child (highest visit count).

### 4.4 `your_best.py` — Evolved Champion

```
Two agents share TeamGlobalState singleton:
  Agent A (offense): MCTS-depth-0 + evolved W_OFF
                     + capsule policy + bottleneck avoidance in tree prior
  Agent B (defense): depth-2 minimax + evolved W_DEF
                     + invader tracker + patrol anchors
  Role switcher (start of each chooseAction)
```

Design justification:
- **MCTS-depth-0 offense:** width > depth against unpredictable opponents; depth-0 maximizes iters/sec for wide, well-explored tree.
- **Minimax-2 defense:** zero-sum vs ≤2 visible invaders; adversarial depth > exploration. Opponent-model reduction → cheap depth 2-3.
- **Separate `W_OFF`, `W_DEF`:** offense and defense rewards differ; sharing one dict underfits both.
- **Deterministic capsule + role modules:** interpretable for report; only thresholds are evolved.
- **All weights + params Python literals** at top of file.

---

## 5. Team Coordination Layer

### 5.1 Role assignment

`TeamGlobalState.role[agent_index] ∈ {OFFENSE, DEFENSE}`.

Initial: lower-index → OFFENSE, higher → DEFENSE (both read same global → auto-agreement).

Triggers (start of each `chooseAction`):
- `score_lead > PARAMS['role_switch_lead_threshold']` AND no visible invader AND no at-risk food → both OFFENSE.
- **Invader actually in our territory** (stricter than just "visible"; use `isPacman` check on enemy state) AND count ≥ 2 → both DEFENSE.
- Invader in our territory count == 1 AND opponent leading → defender engages, attacker raids.
- Fallback: one of each.

**Hysteresis (context-dependent):**
- Default: trigger must hold 3 consecutive turns before switch (anti-thrash).
- **Tight / losing game** (`score_lead ≤ 0`): hysteresis drops to **2 turns** — a 3-turn lag when invader reaches a 2-food cluster can lose the game before defense activates (invader covers 3 tiles, eats 2-3 food by T+5, `MIN_FOOD=2` gate triggered).
- **Invader already carrying food**: **immediate switch** (no hysteresis) to interception mode. Carrying invader = urgent threat.

### 5.2 Shared module globals

```python
class TeamGlobalState:
    role = {}
    last_seen_enemy = {}
    food_eaten_by_us = []
    capsule_eaten_tick = {}
    switch_counter = 0
    tick = 0
TEAM = TeamGlobalState()
```

Both teammates run in same process (CS188 framework) → module-level state shared without IPC; turns sequential → no concurrency.

### 5.3 Capsule policy (deterministic, thresholds evolved)

- **Don't eat on sight.** Walking past is fine.
- **Eat when:** (a) active enemy within `capsule_ghost_dist_trigger` (default 3) AND no 2-step escape; OR (b) `numCarrying ≥ return_threshold_carrying` AND dist to capsule < dist to home + 2; OR (c) entering precomputed bottleneck with active enemy pursuing.
- **Enemy SCARED_TIME=40:** drop `return_threshold_carrying` to 2; down-weight `f_distToHome` in tree prior.
- **Winning (lead>5) and capsule available:** hold as panic button unless (a) fires.

### 5.4 Endgame mode (last 100 moves)

- Ahead: attacker retreats with food; defender patrols own capsule.
- Behind: both OFFENSE; raise `mcts_c` to 2.5 (gambling).
- Tied: one defender + aggressive attacker with `return_threshold_carrying=1`.

Implemented as PARAMS scaling when `tick > 1100`; no new code paths.

---

## 6. Phase 2 — Evolutionary Self-Play Training Pipeline

All under `experiments/` (NOT submitted). Outputs `W_OFF`, `W_DEF`, `PARAMS` pasted into `your_best.py`.

### 6.1 Genome

| Group | Count |
|---|---|
| `W_OFF` offense weights | 20 (Section 4.1 features), bounded [-1000, 1000] |
| `W_DEF` defense weights | 20, same bounds |
| `PARAMS` hyperparams | ~12: `mcts_c ∈ [0.5, 3.0]`, `rollout_depth ∈ {0, 5, 10, 20}`, `return_threshold_carrying ∈ [2,15]`, `capsule_ghost_dist_trigger ∈ [1,6]`, `role_switch_lead_threshold ∈ [2,20]`, `bottleneck_penalty ∈ [-500, 0]`, `scared_return_threshold ∈ [1,8]`, +5 minor |
| **Total** | **~52 reals + few discretes** |

### 6.2 Algorithm: CEM (ranked against alternatives)

1. **CEM (selected).** Pros: fits ~50-dim continuous with noisy fitness; tolerant of non-smooth objectives; Gaussian resampling = natural exploration. Cons: unimodal assumption (addressed by niching + restarts).
2. (1+λ)-ES. Simpler but slower convergence under noisy ranking.
3. GA. Handles discretes naturally but CEM dominates at 50-dim continuous; kept as fallback.
4. Bayesian optimization. Borderline at 50-dim; we can afford thousands of evals → no edge.

### 6.3 CEM config — two-phase schedule (addresses signal-to-noise at 52 dims)

At N=40 with ~84 games/eval and win-rate ≈ 0.7, elite-selection noise is σ(ŵ) ≈ √(0.7·0.3/84) ≈ 0.05 — comparable to per-genome variance from layout/color/seed, so naive single-phase CEM risks drift rather than learning. We split into:

**Phase 2a (gens 1–10): Dimension-reduced warmup.**
- **Tie W_OFF ≡ W_DEF** (both evolved as single shared 20-dim weight vector) → genome drops to **~32 dims**.
- `N = 40`, `ρ = 0.35` (elite count = 14; raised from 0.25 per Scientist — reduces mean SE by ~18%).
- games/genome = **264** (Phase 2a pool, §6.4). With CRN pairing, effective variance is ~equivalent to 500 IID games.
- σ schedule: start broad (weights σ=30), decay ×0.9/gen, floor σ=2.

**Phase 2b (gens 11–30): Full genome, seeded from 2a elites.**
- Unlock `W_OFF ≠ W_DEF` (full 52 dims). Initialize both to the Phase 2a elite mean; σ=10 for the copy delta.
- `N = 40`, `ρ = 0.35`, games/genome = **224** (Phase 2b pool includes 3 monsters, §6.4).
- Elitism: keep best-ever 2 across both phases.
- Restart: if best-ever stagnates 5 gens → inject 8 random genomes (sampled from Phase 2a elite Gaussian for warm start) + reset σ×2.

**Sanity monitor (per generation):** log `elite_mean_fitness - gen_mean_fitness`; if this ratio to generation-to-generation variance drops below 1.0 for 3 consecutive gens, we are drifting — alert and consider bumping N or games/eval.

**Alternative if Phase 2a doesn't converge (trip-wire):** switch to CMA-ES (still numpy-only implementable) which handles correlated dimensions better than axis-aligned CEM.

### 6.4 Fitness — single canonical formula, phase-aware

Per-genome fitness (used identically in Phase 2a and 2b, mode determined by flags):

```
fitness(g) = pool_win_rate(g)
           - 0.5 · crash_rate(g)
           - k · stddev_win_rate(g)          # risk-sensitive (Gemini)
           + monster_bonus_active · monster_bonus_scale · monster_win_rate(g)

where:
  k = 0.5                                    # StdDev penalty coefficient
  monster_bonus_active = 0 in Phase 2a, 1 in Phase 2b   # Scientist-flagged bug fix
  monster_bonus_scale = 0.15                 # reduced from 0.3 (Scientist)
  pool_win_rate = mean win rate over opponent pool (per-opponent means averaged)
  stddev_win_rate = stddev of per-opponent mean win rates (across diverse opponents)
                    → penalizes high-variance agents that beat some styles but lose to others
  monster_win_rate = mean win rate vs the 3 monster agents (§6.9)
  crash_rate = fraction of games with unhandled exception or timeout-forfeit
```

**Opponent pool (applied in both phases; monsters enter in Phase 2b):**

Phase 2a pool (no monsters): `[baseline.py (2x), reflex_sibling, minimax_sibling, mcts_sibling, reflex_aggressive, reflex_defensive, mcts_q_guided, HALL_OF_FAME_sample_4]` = 11 opponents

Phase 2b pool: above + 3 monsters = 14 opponents

**Sample design:**
- Phase 2a: 3 games/opponent × 4 layouts × 2 color swaps = **264 games/genome** (Scientist-tightened from 150; keeps compute close to original via fewer gens in Phase 2a).
- Phase 2b: 2 games/opponent × 4 layouts × 2 color swaps = **224 games/genome** (was 84; raised for SE < 0.05 over 14 opponents).

**Common Random Numbers (CRN) — variance reduction (Codex):** every (genome, opponent, layout) triple plays **both** colors against the same RNG seed per pair. This pairs correlated outcomes, drastically reducing per-genome variance without more games. Required for the 224-game budget to produce useful SE.

**Sequential halving for elite re-evaluation (Codex):** after initial fitness ranking each gen, the top-⌈N/2⌉ genomes are re-evaluated with an additional 2× games each → top-⌈N/4⌉ get another 2× → until the ρ-th elite's ranking is confidence-bounded (`one_sided_alpha=0.05`). Spends extra budget only where ranking is ambiguous.

Fitness is computed once per generation per genome; results cached under `(gen, genome_hash, opponent_id, layout_id, color, seed)` for reproducibility.

### 6.5 Efficiency & niching

- **Multiprocessing:** `ProcessPoolExecutor(max_workers=N)` where **N ≤ physical_cores** (hard rule — see Section 3.4 for why oversubscription biases evolution toward shallow/fast agents). Default N = `min(physical_cores, 8)`; on macOS cap at `physical_cores - 1` because of no per-thread affinity.
- **CPU pinning:** on Linux each subprocess calls `os.sched_setaffinity(0, {worker_id % cores})` before starting `capture.py`. On macOS skip pinning but hold to the core-count cap.
- **Truncated eval:** first 3 gens use 600-move games; full 1200 afterward.
- **HALL_OF_FAME:** keyed by opponent-style slot (best-vs-baseline, best-vs-aggressive, best-vs-defensive, best-on-RANDOM); 1 role-winner added per gen.
- **Monster opponents:** always included in every generation's opponent set — see Section 6.9.
- **Seed-fixed:** `(generation, genome_id, opponent_id, layout_id, color_swap)` → deterministic given master seed.

### 6.6 Compute budget (revised for Scientist-tightened sample sizes)

- Phase 2a: 264 games × 40 genomes × 10 gens = 105,600 games
- Phase 2b: 224 games × 40 genomes × 20 gens = 179,200 games
- Subtotal: **284,800 games**
- Sequential halving elite re-eval overhead: ~+20% → **341,760 games**
- Wall time @ 8-core pinned, ~20s/game ÷ 8 cores effective ≈ 2.5s each → **~23.7 core-hours**, ~1 day on 8 cores
- Laptop-parallel wall clock: **~20h** (overnight + next day) for main campaign

**With CRN pairing**, effective SE is tighter than naive multiplication suggests (~1.4× effective sample size). Actual decision quality equivalent to ~40-core-hours raw.

If we enable N=2 stretch evolution campaigns (Section 6 Follow-up) compute ~2 days — long weekend.

Halt conditions: ELO stagnation 8 gens OR wall budget exceeded → emit best-ever to `artifacts/final_weights.py`.

**Budget relief valve:** if campaign runs over 36h wall, cut games/genome by 25% (Phase 2b only) and restart final 5 gens. Scientists's sanity monitor triggers an alert if this produces drift.

### 6.7 ELO tracking (report figure)

Cross-opponent ELO updated from round-robin results; curve across generations = required figure.

### 6.8 Output

`experiments/artifacts/final_weights.py` with literal dicts; `experiments/bake_into_best.sh` copies into `your_best.py`.

### 6.9 Monster Reference Agents (evaluation-only, never submitted)

Pure self-play without strong external adversaries collapses into a weak equilibrium: evolved agents beat each other by exploiting gen-specific quirks instead of learning robust play. To provide a stable, high-difficulty adversarial signal every generation, the opponent pool includes **hand-tuned monster agents** whose strengths are fixed and whose quirks are *not* evolved against.

Monsters must be **strategically orthogonal** — not just different algorithms. Each implements a distinct pathological playstyle so evolved agents can't beat them with a single counter-strategy:

| Monster | Algorithm | **Strategic profile (distinct from the others)** | Tuning approach |
|---|---|---|---|
| `monster_rule_expert.py` | Expert system | **Territorial defender** — prioritizes home-side coverage, aggressive patrol, immediate interception on any boundary crossing. Rarely attacks. Exploits opponents' return paths. | Hand-authored rules: exact capsule triggers (distance ≤3, carrying ≥5), invader-count-locked role, per-layout corridor preferences, precomputed dead-end avoidance map |
| `monster_mcts_hand.py` | MCTS | **Aggressive raider** — both agents attack; uses capsule to force through; accepts defensive gaps to maximize food-eaten rate. Exploits opponents that commit to defense. | `C = 1.41`, `rollout_depth = 8`, hand-engineered heuristic rollout + leaf evaluator with 10 carefully weighted features; weights favor food and aggression |
| `monster_minimax_d4.py` | Minimax | **Adaptive exploiter** — observes opponent behavior for first ~50 moves, locks into counter-role (defensive if opponent aggressive, vice versa). Exploits static-strategy agents. | α-β depth 4 with opponent reduction + aggressive pruning + hand-tuned eval weights; **too slow for submission** (~1.5s/move) but fine for training |

Rationale: evolved agents that generalize well should beat *all three* profiles; beating only one indicates overfitting. Training fitness tracks per-monster win rate separately for ablation reporting.

**Monster bonus in fitness:**
```
fitness = win_rate_vs_pool − 0.5·crash_rate
        + monster_bonus × (wins_vs_monsters / total_monster_games)
```
with `monster_bonus = 0.3` (tunable). This keeps selection pressure high even as evolved agents start winning 95%+ against `baseline.py`.

**Co-evolutionary ladder — automated (not manual).** Manual monster refinement is unreliable under deadline pressure. Instead:
- **Automatic replacement rule**: if any monster's win rate against the current-gen champion drops below **30% for 3 consecutive generations**, that monster slot is automatically replaced by a snapshot of the current champion (with `monster_bonus` transferred to the replacement).
- Replaced monsters are archived to `experiments/monsters/archive/` so the report can trace the ladder.
- This turns "monster refinement" into a code-enforced mechanism with no dependency on manual discipline.
- **Statistical note (Scientist):** at our per-gen monster-game count (~12 games/monster), the 3-consecutive-gens rule has false-trigger probability 0.5% and miss-rate 4.3% for 30%-vs-50% detection. Acceptable.
- **Fitness integration:** monster bonus applies ONLY in Phase 2b (flag `monster_bonus_active = 1`); Phase 2a uses pool-only fitness (§6.4). This resolves the §6.4/§6.9 inconsistency flagged by Scientist.

Monsters live in `experiments/monsters/` and are **never copied to `minicontest/`**.

---

## 7. Experimentation & Evaluation Protocol

### 7.1 Matrix

Layouts: default, office, strategic, alley, jumbo, RANDOM[1,42,2025].
Opponents: baseline.py, your_baseline{1,2,3}.py, your_best.py (self-play).
Colors: red + blue swapped.
Seeds: 5/cell.
→ 8 × 5 × 2 × 5 = **400 games per evaluated agent.**

### 7.2 Metrics per game

Win/loss/tie, final score, crashed flag, mean/p95/p99 move time, food eaten, food returned.

### 7.3 Statistics

Win rate with 95% Wilson CI. Aggregate across color/seed → n=10 per (agent, layout, opponent) cell. Full CIs in report.

### 7.4 `output.csv`

Columns: `agent, layout, opponent, seed, color, win, score, tie, crashed, mean_move_time_s, p95_move_time_s, p99_move_time_s, total_food_eaten, food_returned`.

Pandas-only aggregation (dep-constraint compliant).

---

## 8. Report & Submission

### 8.1 Structure (ICML LaTeX, 2+ pages)

| Section | Pages | Points | Content |
|---|---|---|---|
| Intro | 0.25 | 8 | Problem, rules, constraints, contribution |
| Methods | 0.75 | 20 | 3 algo subsections + champion hybrid; pseudocode, rationale. Honest framing for minimax (2-enemy reduction) and `your_best` (UCB-guided leaf search, not full MCTS) |
| Results | 0.75 | 20 | **Ablation-centric narrative** (not just algorithm-bar). Per-layout breakdown; per-opponent-type breakdown; champion ablation (UCB-leaf-search alone vs. +evolved weights vs. +role-switching vs. +capsule policy vs. +bottleneck avoidance). Plus: ELO curve, timing histogram, algorithm-comparison table |
| Conclusion | 0.25 | 12 | Lessons (co-evolutionary ladder worked / didn't; what feature mattered most), limitations (1-enemy-frozen minimax failure modes, CEM signal-to-noise), future work |

### 8.2 Required figures (ablation-forward)

1. **Champion ablation bar** (main narrative figure): UCB-leaf-search baseline vs. + evolved W_OFF/W_DEF vs. + role switching vs. + capsule policy vs. + bottleneck avoidance. Win rate ± 95% Wilson CI. This is the report's load-bearing figure.
2. **Algorithm-comparison grouped bar** (all 4 submitted agents): win rate ± CI per opponent-type cluster (baseline / aggressive / defensive / random). Emphasizes where each family wins differently — avoids the "tall / short / short / short" boring narrative if champion dominates.
3. **ELO-vs-generation curve** with monster-replacement events annotated.
4. **Per-layout win-rate heatmap** (8 layouts × 4 submitted agents).
5. **Move-time histogram** with 0.70s / 1.0s vertical guides.

### 8.3 Writer schedule (parallel with training)

- Baseline1 done → draft Methods §Reflex.
- Baseline2 → §Minimax.
- Baseline3 → §MCTS.
- Evolution running → Intro, Conclusion skeleton, preliminary figures.
- Post-evolution → Methods §Champion + Results + polish.

### 8.4 Packaging (`experiments/package_submission.sh`)

1. AST-parse `your_best.py` (self-contained check).
2. 5-game smoke test on defaultCapture vs baseline → ≥3/5 wins.
3. Copy to `20200492.py`.
4. grep for forbidden imports (`torch|sklearn|tensorflow|pickle`) → empty.
5. sha256 checksum.
6. Bundle per course instructions.

---

## 9. Risk Register

| # | Risk | L | I | Mitigation |
|---|---|---|---|---|
| 1 | **Timeout-induced crash / forfeit** | High w/o mitigation | Catastrophic (-100, repeat → 0 total) | **Calibrated budget from M7.5 artifact** (not hardcoded); Dev uses algorithmic bounds `MAX_ITERS` / `MAX_DEPTH` only. `time.time()` polling ONLY if M7.5 shows >20% wall-clock variance; ID returns partial-depth; **timeout-preserving two-layer** try/except in `chooseAction` (§3.1 — re-raises `TimeoutFunctionException` before generic catch) + full try/except chain in `registerInitialState` (§3.2) + `random.choice(legal - {STOP})` fallback, `STOP` only as absolute last resort; **NEVER register own `signal`** (framework owns SIGALRM via `util.py:589-622`) |
| 2 | **Overfit to baseline.py** | Medium | 95% → 40% vs unknown TA | Opponent pool w/ past champions + variants; niching/HOF; RANDOM layouts in eval |
| 3 | **Evolution stagnates** | Medium | Mediocre weights | σ floor; restart injection every 5 stagnant gens; CEM w/ elitism |
| 4 | **Numeric overflow / inf weights** | Low-Med | NaN → sort fail → potential fallback miss | Clip features [-1e6,1e6]; clip weights [-1000,1000]; guard `1/distance` when None/0 |
| 5 | **Layout distribution shift (TA eval)** | Medium | Hidden layouts underperform | Train + eval on different RANDOM seeds; no layout-specific hardcoding |
| 6 | **Role-switch thrash** | Low | Wasted moves | 3-turn hysteresis (Section 5.1) |
| 7 | **Opp-model reduction gameable** | Low | Rare in tournament | Minimax is fallback not primary; best.py uses MCTS offense |

---

## 10. Milestone Sequence

Every Exit criterion below must be verifiable by a concrete command (`exit_code == 0` or numeric threshold from a logged measurement), not by judgment.

1. **Shared core (Section 3).** Implement `CoreCaptureAgent` base in `experiments/zoo/_core.py`. Fallback, timer (0.70s), two-layer try/except, crash-proof `registerInitialState`, snapshot, bottleneck-BFS, TeamGlobalState. **Exit test:** `cd minicontest && ../.venv/bin/python capture.py -r zoo.dummy -b baseline -l defaultCapture -n 1 -q; echo $?` returns `0` on 10 consecutive runs.
2. **Build Development Zoo (Section 4.0).** Implement all ≥12 zoo agents. **Exit test:** `experiments/smoke_zoo.py` runs 10 games per zoo file vs `baseline.py` on default layout; passes iff: (a) 0 crashes across all; (b) `mcts_random` wins ≤40% (control sanity); (c) top agent per family (reflex/minimax/MCTS) wins ≥60% in at least 50-game extension; logged to `experiments/artifacts/smoke_zoo.csv`.
3. **Monster agents (Section 6.9).** Hand-tune monsters. **Exit test:** `experiments/smoke_monsters.py` runs 50 games: each monster beats `baseline.py` ≥ 85%; each monster beats its gen-0 zoo counterpart ≥55% head-to-head; logged.
4. **Evaluation pipeline (Section 7).** `experiments/tournament.py` + `experiments/run_match.py`. **Exit test:** full round-robin (zoo ∪ baseline ∪ monsters) completes in <2h wall; `taskset -c 0 cpulimit --limit 50` simulation shows 0 timeouts across 20 games (Linux; equivalent on macOS); `output.csv` schema matches §7.4.
5. **Evolution pipeline dry run.** `experiments/evolve.py` CEM (N=8, G=2). **Exit test:** `artifacts/gen0.json` and `artifacts/gen1.json` exist and re-runnable with same seed produces byte-identical output; 0 crashes in 672 games.
6. **Full evolution campaign.** N=40, G=30 (Phase 2a 10 gens at 32 dims + Phase 2b 20 gens at 52 dims). **Exit tests (all must pass):** (a) final-gen best beats gen-0 best ≥15% in 50-game HTH; (b) final-gen best ELO ≥ (mean(gen_0..gen_5 best ELO) + 100 Elo); (c) at least 1 monster beaten ≥60% in 50-game HTH; (d) `(elite_mean_fitness - gen_mean_fitness) / gen_std` > 1.0 for ≥ 20 of 30 gens (drift sanity, §6.3 monitor).
7. **select_top4.py run.** **Exit test:** `verify_flatten.py` passes (steps 6a-e §4.0); post-flatten HTH 50-game test in [45%, 55%] band; family-floor clause verified (each of 4 files wins ≥51% vs baseline.py in 80-game slice). Final 400-game matrix eval (§7.1) shows `your_best.py` ≥90% vs baseline.py, <5% crash.
8. **Generate final `output.csv`** for the four submitted agents. **Exit test:** `output.csv` contains ≥400 rows per submitted agent; all required columns populated; pandas-only aggregation script produces §7.3 Wilson CIs.
9. **Write report** (parallel from M2 onward). **Exit test:** `pdflatex` compiles `report.tex` → 2+ page ICML PDF; contains ≥5 figures per §8.2; per-layout table present; per-section word counts meet rubric implicit expectations.
10. **Submission packaging** (Section 8.4). **Exit test:** `experiments/package_submission.sh` runs clean; output `20200492.zip` SHA256 recorded; unzip + 5-game smoke vs baseline passes (≥3/5 wins); `verify_flatten.py` re-runs clean on extracted `20200492.py`.

Parallelism: M2 (zoo) and M3 (monsters) parallelizable after M1. M4 gates both M5 and M6. M6 runs background during M9. M7 requires M6 complete.

---

## 11. Acceptance / Verification Checklist

- [ ] Every milestone has concrete measurable exit criterion.
- [ ] **Submission agent budget:** `MOVE_BUDGET` value set from M7.5 calibration artifact (NOT a hardcoded constant); ID + (optional) polling; no use of `signal`; per-node polling amortized if used.
- [ ] **Exception handling:** `TimeoutFunctionException` explicitly re-raised in `chooseAction` wrapper before generic `except Exception` catch (§3.1). Verified by grep for `from util import TimeoutFunctionException` in every submitted file.
- [ ] **Fallback strategy:** never return `Directions.STOP` unless legal actions list is empty or getLegalActions itself raises. Default fallback = `random.choice(legal - {STOP})`.
- [ ] **Worst-case slow-CPU simulation** (`taskset -c 0 nice -n 19 ...`) yields 0 timeouts across 20 games per submitted agent.
- [ ] **Training pool parallel N ≤ physical cores**; CPU pinning active on Linux (skipped on macOS with reduced N).
- [ ] **GPU unused** — only numpy/pandas; no torch/sklearn/tensorflow imports.
- [ ] `_safeFallback` never raises; inspected per file.
- [ ] Evolution deterministic given master seed.
- [ ] **Zoo ≥12 variants built** and round-robin-tested before evolution.
- [ ] **Monster agents** (`monster_rule_expert`, `monster_mcts_hand`, `monster_minimax_d4`) present in every generation's opponent set with fitness bonus.
- [ ] Niching/HOF prevents collapse.
- [ ] **`select_top4.py`** produces self-contained flattened files matching the four submission filenames.
- [ ] Report has required tables and ≥3 figures (algorithm bar, ELO curve, per-layout heatmap, move-time histogram).
- [ ] Submission zip exact format; `20200492.py` only; no forbidden imports; grep check passes.
- [ ] Eval matrix covers 8+ layouts, 5 opponents, both colors.
- [ ] `your_best.py` single self-contained file; weights + PARAMS as Python literals only.
- [ ] Feature dict + evaluator logic identical across the 4 submitted agents after flatten.
- [ ] Capsule + role-switch policies deterministic; thresholds evolved.
- [ ] Risk register: timeout/crash = #1 with concrete mitigations.
- [ ] **No global Python usage** — all commands via `.venv/bin/python` or `uv run`.
- [ ] **AI usage log** (`docs/AI_USAGE.md`) updated for every change to submission-target code.

---

## ADR

- **Decision.** Submit hybrid evolved champion `your_best.py` (MCTS-depth-0 offense + minimax-2 defense + deterministic capsule/role modules, weights + hyperparameters evolved by 30-gen CEM self-play with diverse opponent pool). Submit three sibling baselines (reflex/minimax/MCTS) for the report's algorithm comparison.

- **Drivers.** (1) Robustness to unknown TA opponents; (2) 40-pt gate + 30-pt tournament; (3) 60-pt report rewards 3 algorithm families + curve.

- **Alternatives considered.** Option A (pure MCTS) — rejected: weakens report, no inference gain. Option C (approx-Q only) — rejected: 30-40% ceiling endangers 40-pt gate.

- **Why chosen.** Matches top-scoring public submission pattern (COMP90054 43.4/45 [abhinavcreed13]); provides the three algorithm families required by the report; evolution makes weights generalize beyond baseline.py; uses only numpy/pandas.

- **Consequences.** Positive: strong scoring on all three grading axes; shared evaluator reduces code volume. Negative: more crash surfaces (mitigated by shared base + try/except); ~10h compute; opp-model reduction in minimax not theoretically sound (risk #7).

- **Follow-ups.** (1) Post-training round-robin among all 4 submissions to confirm `your_best.py` dominates; if not, debug before baking. (2) Second evolution campaign with trained champion in its own pool (bootstrap self-improvement) if time allows. (3) If error rate on RANDOM layouts >5%, reduce `mcts_budget_s` to 0.7s and re-verify.

# omc-pm47: CAPX → Submission Integration (DRAFT)

**Date:** 2026-04-29 (drafted while pm46 v2 Phase 3 finishing)
**Track:** omc / Claude
**Plan slot:** pm47
**Status:** DRAFT — finalize after pm46 v2 Phase 4 results
**Output type:** Integration of CAPX algorithmic ideas into `your_best.py` / `20200492.py`

---

## 0. Context (from pm46 v2 results)

**CAPX (research probe)** dramatically outperforms ABS attacker on the
"reach capsule alive" goal:
- Aggregate (full data partial): CAPX 80%+ vs ABS 9-10% (+70pp)
- 8+ defenders strict improvement at 30-seed full
- 0% died_pre_eat aggregate
- Algorithmic finding: full-path margin gate too strict; near-future horizon
  (`CAPX_GATE_HORIZON=8`) is the critical patch

**Question for pm47**: Can the submission `20200492.py` (A1-derived CEM-tuned
reflex agent) benefit from CAPX algorithmic ideas WITHOUT regressing on the
broader food/scoring/return-home behavior?

## 1. Scope

This plan integrates **specific CAPX components** into the submission, NOT a
wholesale replacement.

**In-scope**:
- Defender-aware A* path planner (§5.2 of pm46 v2)
- Survival-weighted gate (§5.3 with horizon patch)
- Gate-horizon evaluation (key algorithmic finding)

**Out-of-scope**:
- Wholesale agent replacement (CAPX is pure attacker, not full game)
- Food planning / scoring (already handled by submission)
- B-coordination (CAPX uses StubB)
- 28-food deposit / return-home (already handled)

## 2. Integration approach (3 candidates)

### Option A: Drop-in cap-target evaluator (lowest risk)

**Approach**: Add `CAPX-style cap_eat_alive evaluator` to `your_best.py` as a
secondary feature. The existing reflex action selector picks among legal
moves; we add a feature that scores each move based on:
- Will this move bring A closer to a cap WHILE staying alive?
- Use CAPX's defender-aware A* as a "cap reachability oracle"

**Pros**: Minimal blast radius. Submission keeps its existing behavior plus a
small bias toward survivable cap-eating.
**Cons**: Reflex agent's argmax may still ignore the cap_eat_alive signal if
other features dominate.

### Option B: Two-mode agent (medium risk)

**Approach**: A pre-game classifier decides "easy game" (use submission as-is)
vs "hard game / strong defender" (switch to CAPX for cap-eating phase, then
hand back to submission for food/return-home).

**Pros**: Each defender gets the appropriate algorithm.
**Cons**: Mode-switch adds complexity; classifier must be fast and reliable.

### Option C: CAPX-priors enhancement to existing planner (highest risk)

**Approach**: Inject CAPX's threat-cost edge weighting into the submission's
existing food/path planner. The existing planner already does pathing; we
upgrade its cost model to include defender-aware threat penalty.

**Pros**: Single unified planner. Best long-term architecture.
**Cons**: Requires understanding submission's planner internals; risk of
breaking food-planning behavior.

**Recommended starting point**: Option A. Validate with HTH vs baseline +
zoo-rotation. If marginal, escalate to Option B.

## 3. Acceptance bars

- HTH win rate vs baseline: ≥ 80% (currently 79% per A1 baseline).
- HTH win rate vs zoo (17 def × 30 seed): ≥ 60% mean WR.
- Cap-survival rate: improves on Tier-A defenders (vs current submission
  cap-eat-alive %, measure with an `[ABS_CAP_EATEN]`-style shim).
- Per-turn wall: < 1s p99.
- Init wall: < 15s.

## 4. Phases

### Phase 1: Baseline submission cap-eat measurement
Measure current `20200492.py` cap-eat-alive % across the 17 defenders.
Same shim as pm46 v2 ABS-baseline but applied to submission.

### Phase 2: Option A integration (cap-evaluator add-on)
- Implement defender-aware A* + survival sigmoid in submission.
- Add as a feature in the reflex argmax.
- Run smoke 3×3.

### Phase 3: Validation
- 17×30 = 510 game cap-eat measurement on submission+capx-feature.
- HTH WR vs baseline (n=200, sts).
- Compare to baseline submission.

### Phase 4: Decision
- If Option A meets bars → ship.
- If Option A insufficient on Tier-A → try Option B.
- If still insufficient → STOP, accept submission as-is. CAPX remains research-only.

## 5. Risks

- **R1**: CAPX feature dominates argmax → submission becomes cap-greedy,
  loses on food/scoring. **Mitigation**: feature weight tuning via CEM.
- **R2**: A* compute exceeds 1s budget when paired with existing reflex
  features. **Mitigation**: run A* less frequently (every K ticks, K=3-5).
- **R3**: Cross-game state pollution (HIGH bug from code review) bites us
  in tournament-mode multi-game. **Mitigation**: required reset path in
  `registerInitialState`.

## 6. Dependencies

- pm46 v2 final Phase 4 results (CAPX 510-game CSV, ABS 510-game CSV)
- Code-review fix list (`.omc/wiki/pm46-v2-capx-code-review-phase4-tuning.md`)
- Submission baseline cap-eat measurement (Phase 1 of pm47)

## 7. Out-of-scope for pm47

- pm46 v2 Phase 4 knob sweep (separate path: tunes CAPX itself, not submission)
- omx track work (post-pill replanner, B-coordination)
- Tournament submission packaging (pm48?)

## 8. Open questions

1. Which CAPX knobs to fix vs leave tunable in the integrated version?
2. How to measure "cap-eat-alive" in a multi-game tournament without
   modifying capture.py?
3. Should the integrated agent declare the algorithmic improvements in
   `docs/AI_USAGE.md`?

---
title: "ADR pm19 — Phase 2 scope revision based on A1 validation + CCG consensus"
tags: ["ADR", "pm19", "scope-revision", "CCG", "A1-validated", "Orders-dropped", "Phase-2", "supersedes-pm17"]
created: 2026-04-17T03:49:45.448Z
updated: 2026-04-17T03:49:45.448Z
sources: ["pm17 wiki decision/next-session-execution-plan-performance-max-6-phase-pipeline", "pm19 A1 HTH results (340 games, baseline 79%)", "Codex + Gemini CCG outputs pm19"]
links: []
category: decision
confidence: high
schemaVersion: 1
---

# ADR pm19 — Phase 2 scope revision based on A1 validation + CCG consensus

# ADR pm19 — Phase 2 scope revision after A1 validation

**Supersedes** (partially): wiki `decision/next-session-execution-plan-performance-max-6-phase-pipeline` (pm17 plan).

## Context

pm17 plan (committed `5fd795c`) called for a 6-phase pipeline with Orders 1-8 sequential CEM runs in Phase 2:
- Order 1: A1 (zoo_reflex_tuned, h1test init, 17-dim) ~10h est
- Orders 2-4: A1+B1 / A2+B1 / A5+B1 (same container, different init means, 20-dim)
- Orders 5-7: C1+B1 / C4+B1 / C3+B1 (minimax / MCTS / expectimax containers)
- Order 8 (stretch): A3+B1 (h1c init)

Total pm17 Phase 2 estimate: ~70-100h server at wiki-predicted wall. **Measured reality**: A1 alone took 18.5h (vs estimate ~10h), so full Orders 1-8 pace implies ~140-150h (5-6 days).

pm19 session critical event: **A1 HTH validation showed 79.0% vs baseline.py** (Wilson 95% CI [0.728, 0.841]), comfortably clearing the 51% grading gate.

## Decision

**Keep Orders 2, 3, 4; drop Orders 5, 6, 7; treat Order 8 as stretch-only.**

Revised queue:

| Order | Container | init_mean | dim | Decision |
|---|---|---|---|---|
| 1 A1 | zoo_reflex_tuned | h1test | 17 | ✅ DONE (fitness 1.065, baseline 79%) |
| 2 A1+B1 | zoo_reflex_tuned | h1test | 20 | ▶️ RUN (pm19 launched 11:55) |
| 3 A2+B1 | zoo_reflex_tuned | h1b | 20 | queue next |
| 4 A5+B1 | zoo_reflex_tuned | (h1test⊕h1b)/2 | 20 | queue next |
| ~~5 C1~~ | zoo_minimax_ab_d2 | — | — | ❌ DROP |
| ~~6 C4~~ | zoo_mcts_heuristic | — | — | ❌ DROP |
| ~~7 C3~~ | zoo_expectimax | — | — | ❌ DROP |
| 8 A3+B1 | zoo_reflex_tuned | h1c | 20 | optional stretch |

Total revised: 3 evolutionary runs (~54h) vs pm17's 7 runs (~126h). Net saving ~72h (~3 days).

## Drivers / Evidence

### (1) A1 already satisfies the 40pt grading gate

340-game HTH battery on server (30s wall):
- `baseline.py` 158/200 = 79.0% Wilson CI [0.728, 0.841]
- `monster_rule_expert` 46/60 = 76.7%
- `zoo_reflex_h1test` 37/40 = 92.5%
- `zoo_minimax_ab_d2` 33/40 = 82.5%
- 0 crashes

All four opponent types exceed 50% WR with comfortable margins. Grading gate is protected even without further evolution.

### (2) CCG (Codex + Gemini) independently recommended scope cuts

Both advisors reached "drop paradigm containers (Orders 5-7)" independently:
- **Codex** (technical correctness): "CEM on minimax/expectimax/MCTS containers is unlikely to beat a well-evolved reflex champion in your tournament runtime budget. Your pm7 M4-v2 result (0W/0L/8T vs baseline) already signals weak container ceiling under time limits."
- **Gemini** (alternative-path): "The 40pt code gate is a binary pass/fail... Only pursue [tournament extra credit via more CEM runs] if the 60pt report is already camera-ready."
- **Codex** on MCTS specifically: "Time-budgeted search is machine-dependent (different CPU → different iteration counts)... This increases reproducibility risk... unless MCTS is required for report novelty, abandon MCTS evolution now."

### (3) pm17 plan's wall-time estimate was 1.5× off

pm17 estimated ~10h per Order based on simple `run_match.py` benchmark of 1.3s/match. Actual measured: A1 wall 18.5h (~47 min/gen for 2a, ~34 min/gen for 2b). Probable causes: subprocess spawn overhead per match + layout RANDOM generation + OS scheduling. Compounds the cost/ROI calculus against low-ROI Orders.

### (4) User directive — performance-max with 10-day budget

User explicitly kept Orders 2-4 for potential champion improvement (rather than Gemini's "skip all Orders 2-8" recommendation). Rationale: 10+ day budget can afford 3 additional Orders to explore A1+B1, A2+B1 (h1b alt local optimum), A5+B1 (hybrid init) and pick the best.

## Consequences

### Positive

- **Saves ~72h server compute** (3 days), reclaimed for Phase 3 D-series + Phase 6 report polish.
- **Reduces overfit risk** — fewer CEM runs = less chance of converging on pool-specific weights.
- **Simpler Phase 4 tournament** — 4-8 candidates vs 28-32 candidates, faster round-robin.
- **More time for 60pt report** — report quality compounds (each figure/ablation unlocks point margin).
- **Aligns with CCG blunt advice** without fully abandoning Phase 2 queue.

### Negative

- **Lose paradigm diversity** in final champion pool. If TA tournament selects MCTS-heavy opponents, reflex-only evolved weights may underperform. Counter: A1 HTH vs `zoo_minimax_ab_d2` was 82.5%, suggesting search-based opponents are already manageable.
- **Order 6 (MCTS) submission candidate lost**. `your_best.py` will be reflex-based, not MCTS. Report's algorithm-family comparison narrows to reflex + sibling files.
- **Order 8 (h1c init) deferred**: if Orders 2-4 all underperform A1, h1c init as an alternative-seed hedge is lost without rescheduling.

### Deferred / follow-up

- **Dead PARAMS strip** (Codex's high-impact, low-risk cleanup): deferred because Orders 2-4 must share A1's 32/46-dim genome schema for apples-to-apples comparison. Reconsider if Order 2 underperforms A1 on HTH — dead params could be the culprit.
- **ZOO_MCTS_MOVE_BUDGET env override** (Order 6 blocker fix): NOT IMPLEMENTED. `C4` time polling in submission code (commit `a1b5569`) remains the submission-time behavior (0.8s/move). Training budget separation abandoned.
- **Phase 3 D-series** still scheduled, but designs should use the top-1 champion from Orders 2-4 (not all 4).

## Alternatives considered

**Alternative A — full pm17 plan (7 Orders)**: Rejected. CCG consensus + ROI analysis show Orders 5-7 low yield.

**Alternative B — Gemini's "skip all Orders 2-8" (pivot entirely to report)**: Rejected by user directive. "성능 위주로 무조건" + 10-day budget supports moderate expansion beyond A1.

**Alternative C — add a "patient defender" monster to Order 2-4 pool**: Considered, not implemented. Would require a new `monster_*.py` file + pool change, adding ~2h coding risk. Defer to mid-Orders if A1 monster_rule_expert WR starts dropping in newer Orders.

**Alternative D — dead PARAMS strip NOW (Codex's fix)**: Considered, deferred. Apples-to-apples with A1 matters more than marginal CEM signal boost for a single 18h run. Strip becomes priority if Orders 2-4 stagnate.

## Open questions (reassess after Order 2 HTH)

- Does B1 feature set (20-dim) produce fitness > A1's 1.065?
- If Order 2 ≈ A1: is the 18h diminishing returns? Cut Orders 3-4 too?
- Should Order 3 include dead PARAMS strip, given Order 2 performance?

## Related wiki

- Superseded: `decision/next-session-execution-plan-performance-max-6-phase-pipeline` (pm17)
- Reference: `reference/a1-champion-weights-hth-profile-strategy-interpretation-pm19`
- Runbook: `pattern/server-order-queue-operational-runbook-launch-archive-verify-cyc`
- Session log: `session-log/2026-04-17-pm19-a1-validated-baseline-79-order-2-launched-perfor`


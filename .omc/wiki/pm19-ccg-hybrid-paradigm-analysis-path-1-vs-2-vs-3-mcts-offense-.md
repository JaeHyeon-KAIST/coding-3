---
title: "pm19 CCG hybrid paradigm analysis — Path 1 vs 2 vs 3 + MCTS offense feasibility"
tags: ["ADR", "pm19", "hybrid-paradigm", "CCG", "MCTS-offense", "reflex-defense", "Path-3", "pm20-decision-point"]
created: 2026-04-17T04:25:45.855Z
updated: 2026-04-17T04:25:45.855Z
sources: ["STRATEGY §0 Option B plan", "pm19 A1 HTH 79% baseline", "Codex artifact codex-context-cs470-ai-pacman-capture-the-flag-uc-berkeley-cs188-m-2026-04-17T04-12-57-994Z", "Gemini artifact gemini-context-cs470-ai-pacman-capture-the-flag-university-course-u-2026-04-17T04-10-36-746Z"]
links: []
category: decision
confidence: high
schemaVersion: 1
---

# pm19 CCG hybrid paradigm analysis — Path 1 vs 2 vs 3 + MCTS offense feasibility

# ADR pm19 — Hybrid paradigm analysis (MCTS offense + reflex defense)

**Status**: DEFERRED to pm20 for user decision after Order 2 HTH.

## Question origin

User asked (pm19 session end): original STRATEGY §0 Option B was "MCTS-depth-0 offense + minimax-2 defense + approx-Q eval" — a paradigm-hybrid team. What actually built (A1) is pure-reflex homogeneous team with role-differentiated weights (W_OFF ≠ W_DEF). Is it worth building the original hybrid vision now that A1 is at 79% WR vs baseline?

## Three paths considered

- **Path 1** (status quo): A1 pure reflex. Code gate ✅, 22pt margin.
- **Path 2** (original Option B): MCTS-depth-0 offense + minimax-d2 defense. Full hybrid.
- **Path 3** (pragmatic hybrid): MCTS-q_guided offense + reflex defense (reuse A1's W_DEF). Offense-only evolution.

## CCG verdict — diverged

### Codex: "Path 3 tightly-scoped, hard kill"

- CS188 framework compatible: `createTeam` returns heterogeneous pair OK (capture.py:920).
- Per-agent timers independent: offense 0.8s doesn't steal from defense's 1s.
- Flatten cost medium-high: 1.5-3 engineering-days for robust AST flatten (intra-zoo imports require inlining per verify_flatten allowlist).
- Evolve choice: **Option B** — freeze W_DEF=A1's, evolve offense MCTS only. Current pipeline hardwired to zoo_reflex_tuned; q_guided needs a new override path.
- 120s wall problem: MCTS full-game wall 4m43s >> 120s. Training requires MOVE_BUDGET ≤ 0.1s. Submission 0.8s preserved.
- Reflex saturation: near local optimum, not absolute. Expected hybrid gain **+1 to +4 pp WR**, modest not breakthrough.
- Decision rule: build → smoke (1 game <110s) → A/B 100 games vs A1 → revert if gain <2pp OR timeout >5%.

### Gemini: "Stick with Path 1 + polish report"

- Path 2 = "suicide mission" at 120s wall risk.
- 79% → 85% is vanity — 40pt gate doesn't change.
- TA narrative: "100% polished Simple > 80% polished Complex".
- Pivot framing: "We planned hybrid, found simpler was enough" — academically strong.
- Report carries the 60pt bucket — spend 10 days on that.
- Hybrid execution risk: 60/60 upside but 40/60 downside if implementation flakes.

### Convergence across both

- Path 2 full hybrid: DROP (both agree).
- Offense ≠ Defense as tasks (both agree: offense=pathfinding, defense=interception).
- Modest gain expected (+1-4pp, not dominant).
- MCTS timeout = critical failure mode.
- A1 basic value locked.

## Synthesis — recommended pm20 plan

Given user's directive "performance-max + 10-day budget", Codex's profile fits better:

**Phase A (pm20, 2-3h)**: M7 flatten A1 → `20200492.py`. 5-game smoke. **Lock submission candidate**. Hedge: code gate safe no matter what Path 3 produces.

**Phase B (pm20+pm21, 1-2 days)**: Path 3 build:
1. `minicontest/zoo_hybrid_mcts_reflex.py` (~50 lines): `createTeam → [MCTSQGuidedOffense(i1), ReflexTunedDefenseFromA1(i2)]`
2. MCTS uses `MOVE_BUDGET=0.1s` via env var OR hardcoded lower constant for training
3. **Single-game smoke**: wall <110s + crash=0 required
4. **HTH A/B battery** (reuse `experiments/hth_battery.py`): 100 games vs `baseline.py` + 30 games vs A1 (via zoo_reflex_A1 wrapper — needs creation too)
5. **Kill criteria** (either triggers revert):
   - baseline Wilson LB < 0.75 (A1 had LB 0.728 — basically no improvement)
   - timeout rate > 5%
   - crash rate > 0%
6. If ALL pass: run Order N CEM (offense-only MCTS weights, 18h server, MOVE_BUDGET=0.1)

**Phase C (parallel)**: M9 report Intro/Methods draft. Either experimental outcome enriches the narrative:
- Success: "paradigm-hybrid team empirically beats homogeneous (+Δ pp WR with Wilson CI)"
- Failure: "tested hybrid, observed reflex saturation, here's why simpler wins in this domain"

## Blocking prerequisites (before any Path 3 work)

1. Order 2 HTH must complete — decide whether Order 2 or A1 is the defense-weight source
2. `evolve.py` `--init-mean-from` needs `"a1"` option if we want seed from A1 weights directly (~5 lines)
3. `run_match.py` env-var passthrough for `ZOO_MCTS_MOVE_BUDGET` (~5 lines)
4. `zoo_mcts_q_guided` weight-override loader (currently only zoo_reflex_tuned supports it; ~30 lines mirroring M4b-2 protocol)

Effort estimate total: 4-6h Mac prep + 1-2h smoke iteration + optional 18h server CEM.

## Decision gates in pm20

1. **If Order 2 HTH > A1**: promote Order 2. Consider Path 3 still, but with Order 2 as defense seed.
2. **If Order 2 HTH ≈ A1**: same Path 3 plan, A1 as defense seed.
3. **If Order 2 HTH < A1**: reflex paradigm clearly saturated; Path 3 has stronger "upside justification". Still carry kill criteria.
4. **If user changes mind** (e.g., sees "79% 이미 충분" after more thought): drop Path 3, pivot to report polish.

## Related wiki

- Current champion: `reference/a1-champion-weights-hth-profile-strategy-interpretation-pm19`
- Queue/Phase 2 scope: `decision/adr-pm19-phase-2-scope-revision-based-on-a1-validation-ccg-conse`
- Server ops: `pattern/server-order-queue-operational-runbook-launch-archive-verify-cyc`
- Session: `session-log/2026-04-17-pm19-...`

## Action items (reload in pm20)

- [ ] Read this page at pm20 start
- [ ] Check Order 2 HTH result
- [ ] Confirm user direction (Path 3 go / A1-only / alt)
- [ ] If Path 3: implement zoo_hybrid_mcts_reflex.py + required plumbing
- [ ] Enforce kill criteria; revert if unmet


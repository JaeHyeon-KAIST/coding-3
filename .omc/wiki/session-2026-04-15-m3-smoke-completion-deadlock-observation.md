---
title: "Session 2026-04-15 — M3 smoke completion + deadlock observation"
tags: ["2026-04-15", "m3", "smoke", "deadlock", "session-log"]
created: 2026-04-15T00:20:19.049Z
updated: 2026-04-15T00:20:19.049Z
sources: []
links: []
category: session-log
confidence: medium
schemaVersion: 1
---

# Session 2026-04-15 — M3 smoke completion + deadlock observation

# Session 2026-04-15 — M3 smoke completion + deadlock observation

## Date / Session ID
2026-04-15, session `134a0e0e-26d3-41e8-9be3-8b65c6f8c8b7` (continuation from 2026-04-14)

## Focus (1 sentence)
Complete the M2b/M2c/M3 smoke tests that the previous session paused on, document observations, and bootstrap the multi-session knowledge persistence layer (wiki + protocols).

## Activities
- Ran 7 background smoke tests (1 game each on `defaultCapture` vs `baseline`):
  - `zoo_minimax_ab_d3_opp` — Tie, 31s wall, exit 0
  - `zoo_mcts_random` (control) — Tie, exit 0
  - `zoo_mcts_heuristic` — Tie, exit 0
  - `zoo_mcts_q_guided` — Tie, exit 0
  - `monster_rule_expert` — Tie, exit 0
  - `monster_mcts_hand` — Blue (baseline) won, exit 0
  - `monster_minimax_d4` — Blue (baseline) won, exit 0
- All 7 pass technical M3 exit criterion (no crash, exit 0, no forfeit)
- Updated `docs/AI_USAGE.md` with smoke results (M3-verify entry)
- Committed `9e278b4 M3-verify: complete remaining smoke tests`
- Researched and explained "Auto Dream" feature (24h + 5 session memory consolidation; not in `~/.claude/projects/.../memory/`)
- Bootstrapped `.omc/wiki/` with seed pages (this entry being one of them)

## Observations (non-obvious)

**0-win pattern is universal.** Across 47 smoke games this project:
- All M2 zoo variants (reflex / minimax / MCTS / approxQ — 11 agents)
- All M3 monsters (3 agents)
- → 0 wins, 5 ties (mutual 0-0), 2 baseline-wins (vs monsters)

This is qualitatively different from "weak agents losing." Strong-by-design monsters tie, not lose. Random dummy lost. Tuned agents tie. → mutual scoreless deadlock, not skill gap.

**Hypothesis tree for deadlock:** see wiki `debugging/m3-smoke-deadlock-0-win-pattern-across-all-tuned-agents`. Six numbered hypotheses, primary suspect H1 (SEED_WEIGHTS too defense-heavy).

**Deadlock detection BEFORE M6 is critical.** M6 evolution is ~20h; if the deadlock is structural (not just bad seed weights), evolution can't fix it.

## Decisions

| Decision | Reason | Alternatives considered |
|---|---|---|
| Pause autopilot after M3 (instead of running through M4 immediately) | User-requested pause; also gives time to assess deadlock observation | Continue to M4 directly (rejected — risky to barrel forward without analyzing M3 signal) |
| Bootstrap wiki + session-log discipline NOW (rather than later) | 5+ sessions guaranteed; setup cost trivial vs. compounding context-loss cost | Wait until M6 (rejected — by then, M3 observations would be cold and harder to act on) |
| Add hypothesis H1 → H6 to debugging wiki page even though only H1/H4 are tested-feasible right now | Anti-amnesia: future sessions will see ALL six and can pick up wherever they have time | Only document H1 (rejected — under-documents, future-Claude has to re-derive others) |
| Defer hypothesis testing (H1-H6) until BEFORE M5 dry run | M4 tournament infra will provide richer signal; testing in isolation is wasteful | Test H1 immediately (consider for next session if user wants quick-win) |
| Use STATUS.md + SESSION_RESUME.md (not just wiki) for new-session orientation | Wiki search requires knowing terms; STATUS.md is unconditional first-read | Only wiki (rejected — too much friction for first 30s of new session) |

## Open items / blockers

- **OPEN**: deadlock-hypothesis (wiki `debugging/m3-smoke-deadlock-0-win-pattern-across-all-tuned-agents`). Six hypotheses; H1 + H4 highest priority, validation plan documented. Blocks M6 confidence.
- **OPEN**: M4 tournament pipeline not yet activated. Required for H1/H4 validation richer signal.
- **OPEN**: H1 quick-test (zero out `f_onDefense` in one variant + run 10 games) NOT yet performed. Could be done in <10 min next session for fast signal.
- **OPEN**: WIKI / STATUS files committed but referenced in CLAUDE.md update (this session adds the references).

## Next-session priority

1. **H1 quick validation**: patch one zoo variant with neutralized `f_onDefense`, run 10 games vs baseline. If win rate > 0%, deadlock is just bad seed weights — proceed to M4 confidently. (~15 min)
2. **M4 activation**: run `experiments/tournament.py` with full zoo + monsters on 3 layouts × 2 color swaps × 5 seeds. Generate first ELO table. (~2h)
3. **Pre-M5 sanity check**: review tournament results — does ANY agent pair produce decisive games? If still all ties everywhere, escalate to feature extraction inspection (H2/H3/H5).

## Time spent

~2 hours across resume + smoke + wiki bootstrap.

## Cross-references

- Plan: `.omc/plans/STRATEGY.md` §0 ADR (Option B), §4.1 (seed weights), §10 (milestones)
- Code: `minicontest/zoo_core.py` (CoreCaptureAgent), `minicontest/zoo_features.py` (SEED_WEIGHTS)
- Commit: `9e278b4` M3-verify
- Open issue: wiki `debugging/m3-smoke-deadlock-0-win-pattern-across-all-tuned-agents`
- AI usage: `docs/AI_USAGE.md` (M3-verify entry)


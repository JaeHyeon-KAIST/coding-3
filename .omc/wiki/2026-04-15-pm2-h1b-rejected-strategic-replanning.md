---
title: "2026-04-15 pm2 - H1b rejected + strategic replanning"
tags: ["2026-04-15", "h1b", "rejected", "strategic", "replanning", "session-log"]
created: 2026-04-15T01:22:56.894Z
updated: 2026-04-15T01:22:56.894Z
sources: []
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-15 pm2 - H1b rejected + strategic replanning

# Session 2026-04-15 (pm2) — H1b rejected + strategic replanning

## Date / Session ID
2026-04-15 afternoon, third block of the day (post-H1 morning, post-audit mid-afternoon).

## Focus (1 sentence)
Run the H1b variant (role-split retention + OFFENSIVE-only patch) predicted to resolve H1's -18 decisive losses, analyze the outcome, and reprioritize the experimental roadmap.

## Activities

- Authored `minicontest/zoo_reflex_h1b.py` (~55 lines) inheriting `ReflexTunedAgent`; role-aware `_get_weights()` returns patched OFFENSIVE dict only for OFFENSE role
- Verified weights via import sanity: OFFENSIVE patched (`f_onDefense=0, f_numInvaders=-50`); DEFENSIVE untouched (`f_onDefense=200, f_numInvaders=-2000, f_patrolDist=30`)
- Ran smoke: 10 games vs baseline on defaultCapture in 55s wall — 1W / 2L / 7T
- Documented result in wiki debugging page (Resolution log) with game-by-game + comparison to H1
- Updated STATUS.md with H1b-verify row and re-prioritized next-action guidance
- Escalated two new hypotheses to the top of the follow-up list: H1c (capsule exploit) and H1d (defensive rebalance)

## Observations (non-obvious)

**H1b hypothesis was wrong in direction**. I predicted "defender holds home, -18 routs disappear, ties stay similar or drop". Actual outcome: -18 routs persisted exactly 2/10 (same as H1), and ties INCREASED from 50% to 70%. H1 (both OFFENSE) turns out to be strictly better in win rate terms on this layout.

**DEFENSIVE weights are themselves weak**. `f_patrolDist=30` distracts defender from active invader chase. Baseline's OffensiveReflexAgent enters freely because our defender oscillates between patrol anchor and threat. This means seed-weight tuning of the offensive dict alone is insufficient even if the "split roles" concept is correct.

**"2-OFFENSE formation" has real attacking advantage** over "1+1 split" regardless of weight tuning. Two attackers overwhelm one defender; one attacker vs one defender is reliably stalemated. H1's 30% win rate vs H1b's 10% is partly a formation-level effect, not just weight-level.

**M6 evolution must jointly optimize OFFENSE × DEFENSE weight space + role-switching threshold**, not just tune offensive values. Dimensionality of the useful search space is ~2x what the plan section §6.1 implied.

**Baseline is still un-exploited**. We haven't touched baseline's clear weaknesses (capsule blindness, scaredTimer bug in its defender). H1/H1b both just tune OUR side without targeting THEIR side. The H1c hypothesis is the first one that explicitly exploits baseline.

## Decisions

| Decision | Reason | Alternatives considered |
|---|---|---|
| Keep both `zoo_reflex_h1test.py` AND `zoo_reflex_h1b.py` in the zoo | Ablation references for the report. H1 narrowly beats H1b, but both will appear in M4 tournament for consistent comparison. | Delete H1b (rejected — historical record + future evolution seed diversity) |
| Promote H1c (capsule exploit) to next-priority single-change experiment | Highest ROI: first hypothesis that exploits baseline's actual weakness. 10-minute smoke cost. | H1d first (rejected — DEFENSIVE rebalance is a bigger change, H1c is minimal surgical edit) |
| Defer H2 diagnostic (fallback counter) until after H1c | Tie rate can be re-measured under H1c; if ties drop even without diagnostic, H2 may not matter | Instrument now (rejected — extra code change) |
| DO NOT revert or amend H1 — keep both data points | H1 confirmed deadlock was calibrational; H1b tells us the simple fix isn't enough. Both are data. | (no alternative) |
| Elevate M4 infrastructure patch priority | With multiple hypotheses on the table (H1c, H1d, H2, H1e) we need reliable multi-layout multi-opponent testing. Can't just keep doing defaultCapture smokes. | Push more smokes first (rejected — smoke fatigue; more data per test needed) |

## Open items / blockers

- **OPEN (promoted to top)**: H1c capsule-exploit variant. Not yet authored.
- **OPEN**: `SEED_WEIGHTS_DEFENSIVE` quality. H1b data suggests these are under-tuned. Either H1d or M6 evolution fixes.
- **OPEN (infra, was already tracked)**: M4 tournament patches. Now more urgent because H1c/H1d/H2/H1e need cross-layout comparison.
- **OPEN**: 50% → 70% tie rate jump from H1→H1b unexplained quantitatively. H2 (STOP fallback) still plausible.
- **OPEN (critical, from architect audit)**: `evolve.py:140-142` NotImplementedError swallow; `run_match.py:72` seed bug. See wiki `debugging/experiments-infrastructure-audit-pre-m4-m6`.

## Next-session priority

1. **H1c quick validation** — author `zoo_reflex_h1c.py` with `f_distToCapsule: 8 → 80`, run 10 games vs baseline. Expected: 5W+ if baseline-capsule hypothesis correct. (~15 min)
2. **If H1c works**: activate M4 infrastructure patches (CSV append, seed workaround, process-group isolation, futures window) — ~60 min. Then run M4 tournament across 3 layouts with h1test/h1b/h1c/baseline/monsters.
3. **If H1c fails too**: pivot to H1d (DEFENSIVE rebalance). This is the signal that seed-weight tuning alone will never get us above 30% and we must lean fully on M6 evolution — which means fixing evolve.py's NotImplementedError swallow is now the critical path.

## Time spent

~30 minutes (authoring + smoke + analysis + wiki + plan update).

## Cross-references

- Code: `minicontest/zoo_reflex_h1b.py` (new, ~55 lines); `minicontest/zoo_reflex_h1test.py` (comparison reference)
- wiki debugging: `m3-smoke-deadlock-...` (Resolution log for H1b appended), `experiments-infrastructure-audit-pre-m4-m6` (infra gate)
- Plan: `.omc/plans/STRATEGY.md` §4.1 (seed weights — likely needs amendment), §6.1 (genome dimensions — may underestimate by factor 2)
- Prior session-logs: `session-2026-04-15-m3-smoke-completion-deadlock-observation` → `2026-04-15-pm-h1-deadlock-validation-confirmed` → this one


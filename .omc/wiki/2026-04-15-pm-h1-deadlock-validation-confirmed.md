---
title: "2026-04-15 pm - H1 deadlock validation confirmed"
tags: ["2026-04-15", "h1", "deadlock", "validation", "reflex", "seed-weights"]
created: 2026-04-15T00:48:17.198Z
updated: 2026-04-15T00:48:17.198Z
sources: []
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-15 pm - H1 deadlock validation confirmed

# Session 2026-04-15 (pm) — H1 deadlock hypothesis validation

## Date / Session ID
2026-04-15 (second session of the day, ~09:35-09:50 KST)

## Focus (1 sentence)
Execute the H1 quick-validation left as the #1 next-session priority by the morning session: patch one zoo variant with neutralized `f_onDefense` + `f_numInvaders`, run 10 games vs baseline, confirm or reject H1.

## Activities

- Re-read full multi-session context: `MEMORY.md`, `SESSION_RESUME.md`, `STATUS.md`, `STRATEGY.md` (all 746 lines), `open-questions.md`, wiki (glossary + session-log-protocol + m3-deadlock + prior session-log), `notepad.md`, `docs/AI_USAGE.md`
- Inspected `zoo_features.py` + `zoo_reflex_tuned.py` + `zoo_reflex_aggressive.py` + `zoo_core.py` for the right patch surface
- Verified `capture.py -n N` = exactly N games (line 890 `for i in range(options.numGames)`), NOT 2N as prior notepad note suspected
- Created `minicontest/zoo_reflex_h1test.py` — inherits `ReflexTunedAgent`; overrides `_get_weights()` to always return a patched dict with `f_onDefense=0`, `f_numInvaders=-50`, rest unchanged; bypasses `TEAM.role` so both teammates are OFFENSE
- Import sanity: `.venv/bin/python -c "import zoo_reflex_h1test"` → OK; verified the patched weights via attribute read
- Ran smoke: `../.venv/bin/python capture.py -r zoo_reflex_h1test -b baseline -l defaultCapture -n 10 -q` → 61s wall
- Captured results and wrote resolution log into the debugging wiki page

## Observations (non-obvious)

**Dramatic signal in 10 games.** From 0/47 wins across M1-M3 to **3/10 wins** with one seed-weight patch. The hypothesis that the M3 deadlock was a seed-weight calibration problem — not a structural bug in feature extraction / role logic / APSP — is now the strongly-supported working theory.

**50% tie rate persists** even with both agents fully offensive. This is interesting. It suggests something beyond `f_onDefense` is keeping games scoreless in half the runs. Two plausible explanations:
- Baseline's OffensiveReflexAgent is itself fairly timid; games where nobody commits to a raid naturally end 0-0 at tick 1200
- H2 (STOP fallback over-firing) still has explanatory power for the residual tie rate — worth instrumenting if M4 tournament sees similar pattern on other layouts

**-18 decisive losses** (2/10) reveal the cost of "both agents OFFENSE". With zero defender, baseline's Blue OffensiveReflexAgent walks in and cashes in 18 food unopposed. So H1's test configuration is NOT a viable team strategy — it's a diagnostic. Real agents need 1 OFFENSE + 1 DEFENSE with the rebalanced weights.

**`capture.py -n N` semantic**: exactly N games, NOT 2N. Prior notepad note (2026-04-14) hypothesizing "N×2 with color swap" was wrong. This matters for budget planning: M4/M5/M6 compute estimates are correct as written.

## Decisions

| Decision | Reason | Alternatives considered |
|---|---|---|
| Proceed to M4 tournament activation next | H1 confirmed → deadlock is calibrational, not structural; M6 can safely consume 20h budget | Re-tune SEED_WEIGHTS first then activate M4 (rejected — M4 should show the full pattern across opponents/layouts before we commit to specific weight adjustments) |
| Keep `zoo_reflex_h1test.py` as permanent ablation reference | Future report can cite "we identified and confirmed the seed-weight deadlock via this variant" | Delete after validation (rejected — this is a real experimental artifact; Report Methods section can reference it) |
| Do not re-tune SEED_WEIGHTS_OFFENSIVE yet | CEM evolution can discover right values; manual tuning could bias the genome initial distribution in an unprincipled way | Manually set `f_onDefense=20, f_numInvaders=-200` now (rejected — 30% wins from 0% is enough to proceed; let evolution do the rest) |
| Deprioritize H3/H5/H6 hypotheses | H1's partial explanation + game-played-successfully observation makes APSP/role/color hypotheses low-probability | Test them all preemptively (rejected — wasted effort if M4 reveals different pattern) |

## Open items / blockers

- **PARTIALLY RESOLVED**: deadlock root cause — H1 confirmed as primary driver. See wiki `debugging/m3-smoke-deadlock-...` resolution log.
- **STILL OPEN**: why 50% tie rate persists after H1 patch. Plausible = baseline also timid. Will test via M4 tournament across layouts.
- **STILL OPEN (deferred)**: H2 instrumentation — run only if M4 shows persistent scoreless games.
- **NEXT IMMEDIATE**: M4 tournament pipeline activation.

## Next-session priority

1. **M4 activation** — run `experiments/tournament.py` on full zoo (16 agents incl. h1test) + 3 monsters on 3 layouts × 2 color swaps × 5 seeds. Verify the H1 win pattern generalizes beyond defaultCapture. Generate first ELO table. (~2-3h wall)
2. **Before M5 dry run**: inspect tournament.py output — if tie rate drops below 30% across layouts, H1 sufficient; if it stays at 50%+, escalate H2 instrumentation.
3. **Stretch for same session**: after M4, run the same H1 patch across minimax/MCTS families (`zoo_minimax_h1test`, `zoo_mcts_h1test`) for consistency — inherits ReflexH1TestAgent's weight dict.

## Time spent

~15 minutes (matching morning session's estimate for "H1 quick validation").

## Cross-references

- Code: `minicontest/zoo_reflex_h1test.py` (new, 55 lines), inherits `zoo_reflex_tuned.ReflexTunedAgent`
- Patched file: NONE (non-destructive — new file only, no existing weight changes)
- Debugging wiki: `m3-smoke-deadlock-0-win-pattern-across-all-tuned-agents` (resolution log appended)
- Plan section: `.omc/plans/STRATEGY.md` §4.1 (seed weights — will revisit for M6 init population construction)
- Prior session-log: `session-2026-04-15-m3-smoke-completion-deadlock-observation` (pointed here as next-session priority)


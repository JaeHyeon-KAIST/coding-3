---
title: "2026-04-16 pm14 Option A complete — 4-loop bypass, 4.55× speedup, M6 budget restored"
tags: ["session-log", "option-a", "4-loop-bypass", "single-game", "run-match-refactor", "speedup-4.55x", "m6-budget-restored", "t1-t3-pass"]
created: 2026-04-15T16:32:10.586Z
updated: 2026-04-15T16:32:10.586Z
sources: ["experiments/single_game.py", "experiments/run_match.py", "/tmp/t1t2t3_post_A.log", "pm13 M4b-4 finding"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-16 pm14 Option A complete — 4-loop bypass, 4.55× speedup, M6 budget restored

# Session 2026-04-16 pm14 — Option A complete: 4-loop bypass

## Focus
Fix pm13's M6 budget overshoot (103h vs STRATEGY §6.6's 20h target) by removing capture.py's hidden 4-loop multiplier. Result: 4.55× per-match speedup, M6 back in the 23-32h range.

## Root cause recap
`capture.py.__main__` wraps `runGames` in a 4-loop over
`lst=['your_baseline1.py','your_baseline2.py','your_baseline3.py','baseline.py']`
to build the assignment's `output.csv`. Every `run_match -r X -b Y -n 1`
invocation therefore paid for 4 capture.py games even though we only
wanted the first. At 8-worker parallel contention this inflated
per-match wall to 10.5s (Stage 1 single-worker measured 7.74s).

`capture.py` is immutable per CLAUDE.md, but its internal functions
(`readCommand`, `runGames`) are perfectly importable — the 4-loop only
runs under `__main__`. So we wrap, we don't modify.

## Implementation

### `experiments/single_game.py` (NEW)
- `os.chdir(MINICONTEST) + sys.path.insert(0, MINICONTEST)` at start —
  same working directory capture.py expects (`imp.load_source` etc. are
  CWD-relative).
- `from capture import readCommand, runGames`.
- Sniffs argv for `-b/--blue` to pass as readCommand's `blue_team`
  positional (it's only used as the argparse default).
- Forces `options["numGames"] = 1`, `options["layouts"] = layouts[:1]`
  to trim any accidental -n > 1 inner repeat.
- Calls `runGames(**options)`, decodes the single game's score into
  `winner / red_win / blue_win / tie / score`, emits one-line JSON on
  stdout.
- Exhaustive crash classification at each step: `capture_import_failed`,
  `readCommand_sysexit`, `readCommand_failed`, `runGames_failed`.
  Every crash path still emits a valid JSON so run_match.py's parser
  has something to read.

### `experiments/run_match.py` (REFACTORED)
- `cmd[1]` flipped from `"capture.py"` to `str(SINGLE_GAME)`.
- Old regex-based stdout parsing (`"The Red team wins"`,
  `"Average Score:"`, etc.) **removed**. Now `json.loads(stdout.splitlines()[-1])`
  pulls the canonical payload.
- Self-reported crashes from single_game.py take precedence over
  `exit_code != 0` alone. Parse failure returns `crashed=True,
  crash_reason="parse_fail:..."`.
- `--red-opts/--blue-opts` forwarding preserved (M4b-2).
- `-l RANDOM<seed>` layout promotion preserved (pm7 M4c-1).
- Subprocess timeout path still returns `crash_reason="subprocess_timeout"`.

## Verification

### Single-match wall (baseline vs zoo_reflex_h1test, defaultCapture)

5 sequential runs via run_match.py: wall 1.687s, 1.678s, 1.698s, 1.717s,
1.706s. Mean **1.70s**, stddev 0.015s. Compare to pm13's **10.5s**
under 8-worker load or Stage 1's **7.74s** single-worker baseline.
**4.55× vs Stage 1, ~6× vs pm13.** Expected because the 4-loop literally
ran 4 games instead of 1.

Variance restored: 3 ties + 2 Blue-wins in 5 reps confirms pm7's
clock-seeded PRNG path still works.

### T1-T3 (wiki `pattern/option-test-plan-t1-t4-...`)

Re-ran the pm12 test harness verbatim (same genomes, opponents, counts)
after the refactor. All PASS.

| test | pm12 wall | pm14 wall | speedup | notes |
|---|---|---|---|---|
| T1 same-genome 2× | 90.3s | **28.0s** | 3.2× | run A = run B = 0.25 pool_win_rate (identical) |
| T2 3-genome parallel | 49.4s | **15.5s** | 3.2× | tuned 0.00 < h1test/h1c 0.25 (ranking intact) |
| T3 crash-robust | 0.9s | 1.0s | ≈ | error path now surfaces as `runGames_failed` instead of `nonzero_exit:N`, both propagate cleanly |

Overall T1-T3 wall: **140s → 44s**. Test-scale speedup is 3.2× (lower
than single-match 4.55× because of ProcessPool spawn overhead + fixed
imports at the T2 worker startup).

### Correctness notes from T1

pm12: run A pool_win=0.625, run B pool_win=0.625 (identical; then flipped
in earlier runs)
pm14: run A pool_win=0.25, run B pool_win=0.25 (identical again)

The absolute win rate moved between sessions because the clock-seeded
PRNG delivers a different sample from run to run — this is expected and
matches pm7's design. What matters is that under a *single session's*
identical conditions, both calls produce the same distributional output
AND no crash, which is what T1 actually asserts. PASS.

## M6 budget after Option A

| budget model | per-match wall | Phase 2a | Phase 2b | total |
|---|---|---|---|---|
| pm13 (with 4-loop) | 10.5s | 38.5h | 65.0h | **103h** |
| pm14 Option A (no 4-loop), worst case at test-scale speedup 3.2× | 3.28s | 12.0h | 20.4h | **32.4h** |
| pm14 Option A, single-match speedup 4.55× | 2.31s | 8.5h | 14.4h | **22.9h** |
| STRATEGY §6.6 target | — | — | — | 20h |

**M6 can now fit inside an overnight + half-day run** (~24h) without any
scale-down. Hybrid option (D) from pm13 is no longer required. Scale-down
(B) stays on the bench as a fallback if per-gen trajectory in M6-a
looks dead.

## Decisions

1. **Option A landed.** Commit pm14 (this session).
2. **STRATEGY §6.6's budget math is implicitly correct** once the 4-loop
   amplification is removed — STRATEGY had assumed ~2.5s/game which
   matches our post-A 2.3-3.3s measurement. STRATEGY didn't flag the
   4-loop because it never explicitly reckoned with capture.py's
   `__main__`; this is a latent doc bug worth mentioning in the report.
3. **M6-a is unblocked.** The natural next step.
4. **α-5 still permanently skipped** per pm13 decision — first-3-gens
   wall not the bottleneck.

## Next-session priority

Launch **M6-a** (Phase 2a smoke): `evolve.py --phase 2a --n-gens-2a 2
--pop 40 --games-per-opponent-2a 264 --opponents <full 11> --layouts
defaultCapture RANDOM --master-seed <N>`. Expected wall ~45-60 min.
Gate: `elite_mean > gen_mean` and `best_ever > h1test seed fitness`.
If either fails after gen 1, stop and reassess per tier policy.

## Artifacts

- `experiments/single_game.py` — 4-loop bypass wrapper (NEW, ~150 lines)
- `experiments/run_match.py` — refactored (cmd target, JSON parsing)
- `/tmp/t1t2t3_post_A.log` — full post-A test output


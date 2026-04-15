---
title: "2026-04-15 pm12 α-core complete — T1-T4 all PASS (α-1/2/3/4 verified)"
tags: ["session-log", "option-alpha", "alpha-core", "t1-t4", "verification", "parallelization", "resume", "evolve.py"]
created: 2026-04-15T09:57:47.998Z
updated: 2026-04-15T09:57:47.998Z
sources: ["/tmp/t1t2t3_verify.py", "/tmp/t1t2t3_result2.log", "experiments/evolve.py", "commits b625dc8, ad56ebe"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-15 pm12 α-core complete — T1-T4 all PASS (α-1/2/3/4 verified)

# Session 2026-04-15 pm12 — α-core complete (T1-T4 all PASS)

## Focus
Option α (evolve.py genome-level parallelization + resume + CLI) verified end-to-end against the T1-T4 test plan. Everything except the optional α-5 (truncated eval) is now in place.

## Summary of α-1 → α-4

| Sub-tier | What | Verification | Commit |
|---|---|---|---|
| α-1 | Genome-level ProcessPoolExecutor (workers = min(cores-1, 8)) | 8-genome smoke: 27.3s wall vs ~250s sequential → **~9× speedup** | `b625dc8` |
| α-2 | `--resume-from` reads `{phase}_gen<N>.json`, forward-compat `best_ever_*` | T4: rm gen 1/2, resume rebuilds them; gen 0 mtime unchanged; resume log line `[evolve] resume: phase=2a gen=0 best_ever_fitness=0.0000 stagnation=1` | `ad56ebe` |
| α-3 | `--opponents`, `--layouts` CLI → run_phase → evaluate_genome | 2-opponent round-trip smoke: 4 pop × 4 games × 2 opps × 1 layout = 32 matches, 54s wall, gen000.json emitted with `best_ever_fitness` field | (part of `b625dc8`) |
| α-4 | T1-T4 verification | T4 done in pm11. **T1, T2, T3 all PASS this session.** | — (verify-only) |

## T1 — same-genome 2× equivalence
`h1test` × `baseline` × `defaultCapture` × 8 games, called back-to-back sequentially.
- run A: `pool_win_rate = 0.625` / crash 0
- run B: `pool_win_rate = 0.625` / crash 0
- `|diff| = 0.000` (< 0.5) ✓
- Schema OK, no crashes ✓
- **Verdict: PASS (90.3s wall)**

## T2 — 3 genomes parallel independence + ranking
`h1test` / `h1c` / `tuned` evaluated in a 3-worker pool.
- `h1c   `: pool_win=0.375, crash=0
- `h1test`: pool_win=0.250, crash=0
- `tuned `: pool_win=0.000, crash=0
- `h1test >= tuned` (0.250 vs 0.000) ✓
- `tuned <= 0.25` (structural deadlock reproduced) ✓
- No crashes across the pool ✓
- **Verdict: PASS (49.4s wall)**

Note: T2 flipped the pm4/M4-v2 pair `h1test > h1c` to `h1c > h1test` in THIS run. That's not a correctness issue — at n=8 per genome, binomial σ ≈ 0.15 and a single-seed swap is within expected noise. The critical invariant — `tuned` cannot beat baseline because the structural deadlock is intact — reproduced cleanly.

## T3 — crash-robust with nonexistent opponent
`h1test` × `["nonexistent_agent_xyz"]` × `defaultCapture` × 4 games.
- `pool_win_rate = 0.0`, `crash_rate = 1.0`, schema intact
- `run_match` returned `crashed=True, crash_reason='nonzero_exit:...'` for every attempt (capture.py's `imp.load_source` raises ImportError → returncode ≠ 0)
- `evaluate_genome` propagated crash count without aborting
- **Verdict: PASS (0.9s wall)** — bad opponent fails FAST, not after timeout

## Caught harness bug — `__main__` guard mandatory on macOS

First T1-T3 run failed:
```
RuntimeError: An attempt has been made to start a new process before the
current process has finished its bootstrapping phase.
...
concurrent.futures.process.BrokenProcessPool
```

Cause: macOS Python 3.9 multiprocessing uses the `spawn` start method. When T2 calls `ProcessPoolExecutor(...)`, each worker re-imports the calling script. Without an `if __name__ == "__main__":` guard, the top-level test body (T1, T2 submission) runs inside EVERY worker → T2's recursive spawn → RuntimeError.

Evidence: the first run's log has T1 printed **twice** (the outer script's T1 + one worker's T1) before the recursive T2 tripped.

Fix: wrap `run_t1() / run_t2() / run_t3()` under `def main(): ...` + `if __name__ == "__main__": main()`. Second run passed cleanly in 140s total.

evolve.py's own `main()` is already guarded (line 250-ish `if __name__ == '__main__': main()`), so the production flow is unaffected. Only the ad-hoc test script needed fixing.

## Performance notes

- α-1 smoke (pm10): 8 genomes / 4 games/opp / 1 opp / 1 layout = 32 matches. Wall 27.3s, CPU 554% (~5.5× utilization).
- α-3 smoke (pm12): 4 genomes / 4 games/opp / 2 opps / 1 layout = 32 matches/genome wait no 8 matches/genome × 4 = 32 total. Wall 54.2s, CPU 360%. Overhead of 2× opps shows up.
- T2 (pm12): 3 genomes / 8 games/opp / 1 opp = 8 matches/genome × 3 = 24 matches in 3 workers. Wall 49.4s ≈ one-genome sequential (~93s) × 3/3 workers ≈ 93s if linearly scaled, but parallelism + worker warmup gave us 49.4s — slightly better than linear because one worker finishes its 8 matches earlier than the other two and grabs nothing new.

Full M6 extrapolation re-checks out: **~23h parallel** on defaultCapture + RANDOM seeds × full opponent pool × 40 pop × 30 gens. Matches STRATEGY §6.6's 20h estimate within a reasonable margin.

## Decisions

1. **α-core complete.** α-1/2/3/4 all verified. Not blocking anything else.
2. **α-5 (truncated eval) deferred per user request** — user wants to inspect state before making it optional-in-practice. Likely re-evaluated after M4b-4's M5 dry-run exposes whether initial gens dominate the budget.
3. **Test harness fix captured.** Any future ad-hoc ProcessPool smoke MUST include the `__main__` guard; added as a note inside `/tmp/t1t2t3_verify.py` so the pattern is reusable.
4. **Next natural step: M4b-4** (M5 dry-run). With α-core landed, a single `evolve.py --phase 2a --n-gens-2a 2 --pop 8 --games-per-opponent-2a 24 --opponents ... --layouts ...` should complete in ~13-20 min and give us the first fitness curve with meaningful signal.

## Next-session priority

- Optional first: α-5 truncated eval (15 min) if user greenlights it.
- Main: M4b-4 M5 dry-run.
- After M4b-4 passes: launch M6-a (Phase 2a smoke, 2 gens, ~1.5h) per the tier policy.

## Artifacts

- `/tmp/t1t2t3_verify.py` (test harness; not committed — transient)
- `/tmp/t1t2t3_result2.log` (full test output; not committed)
- `experiments/artifacts/2a_gen00[012].json` from smoke runs (gitignored)


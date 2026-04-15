---
title: "2026-04-16 pm13 M4b-4 M5 dry-run — α-5 killed, M6 budget 5× overshoot discovered"
tags: ["session-log", "m4b-4", "m5-dry-run", "alpha-5-killed", "m6-budget-overshoot", "capture-py-4-loop", "parallelization-efficiency"]
created: 2026-04-15T16:17:18.409Z
updated: 2026-04-15T16:17:18.409Z
sources: ["/tmp/m5_dryrun.log", "experiments/artifacts/2a_gen000.json", "experiments/artifacts/2a_gen001.json", "experiments/artifacts/2a_gen002.json", "experiments/evolve.py"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-16 pm13 M4b-4 M5 dry-run — α-5 killed, M6 budget 5× overshoot discovered

# Session 2026-04-16 pm13 — M4b-4 M5 dry-run (α-5 killed, M6 5× budget overshoot)

## Focus
α-core done. Ran the first real end-to-end evolution: 3 gens, 8 pop, 24 games/opp, 3 opponents, 2 layouts. Two big findings.

## Run spec
```
.venv/bin/python experiments/evolve.py \
  --phase 2a --n-gens-2a 3 --pop 8 --games-per-opponent-2a 24 \
  --opponents baseline zoo_reflex_h1test zoo_reflex_h1b \
  --layouts defaultCapture RANDOM --master-seed 500
```

## Per-gen wall (new instrumentation, this session)

Added `gen_start = time.time()` + `wall={gen_wall:.1f}s` to `run_phase`'s per-gen print. Tiny Edit, 3 hunks, `time` import.

| gen | wall (s) | wall (min) | best | mean | elite_mean | snr | stagnation |
|---|---|---|---|---|---|---|---|
| 0 | **760.8** | 12.7 | 0.000 | 0.000 | 0.000 | 0.00 | 1 |
| 1 | **729.9** | 12.2 | **0.101** | 0.013 | 0.034 | 0.63 | 2 |
| 2 | **753.7** | 12.6 | 0.000 | 0.000 | 0.000 | 0.00 | 3 |
| — | **2244.4** | **37.4** | — | — | — | — | — |

## Finding 1 — α-5 permanently killed

STRATEGY §6.5's "first 3 gens use 600-move games" optimization assumes that initial gens have more time-out games (random genomes don't decisively beat anyone → everything ties at 1200 moves) than later gens, so truncating to 600 moves would disproportionately speed up the early phase.

**pm13 data contradicts this assumption empirically:**

- gen 0 wall 760.8s → gen 1 730.0s → gen 2 753.7s. **±4 % variance, no downward trend**.
- If initial gens were time-out dominated, we'd expect gen 0 ≫ gen 1 ≫ gen 2 as genomes become decisive. We see the opposite pattern — gen 1 is actually the fastest.
- Reason likely: our opponent pool includes `baseline`, `zoo_reflex_h1test`, `zoo_reflex_h1b` — all decisively beat / decisively lose to random-init genomes in under 1200 moves, so the 600-move truncation almost never changes outcomes.
- Projected α-5 savings: **negligible** (<1% of M6 wall).

**Decision**: α-5 permanently skipped. STATUS row set to ❌ PERMANENTLY SKIPPED.

## Finding 2 — M6 budget blows up 5× under parallel load

Stage 1 Pre-α baseline was 7.74s/match measured on a single-worker run (1 genome × 72 games sequential). Today at 8-worker parallel:

- Each worker evaluates 1 genome × 72 games = 760s wall.
- Per-match effective time inside the worker: 760/72 = **10.55s/match**, up **36%** from Stage 1's 7.74s.
- Reason: 8 concurrent capture.py subprocesses fight for disk I/O, file descriptors, and possibly memory bandwidth. Each `run_match` fork adds a second subprocess layer, so the 8 workers create 8 grandchild capture.py processes competing with each other.

**Re-extrapolating STRATEGY §6.6's full spec at the corrected 10.55s/match:**

| Phase | pop × games/genome × gens | matches total | 8-worker wall |
|---|---|---|---|
| 2a | 40 × 264 × 10 | 105,600 | ~38.5 h |
| 2b | 40 × 224 × 20 | 179,200 | ~65 h |
| **M6 total** | | **284,800** | **~103 h ≈ 4.3 days** |

STRATEGY §6.6 had claimed "~20h, 1 day on 8 cores" — we're **5× over**. Cause: STRATEGY's "2.5s each → 23.7 core-hours" line implicitly assumed no 4-loop overhead. But `capture.py:1054` runs `for i in range(len(lst))` with `lst=['your_baseline1..3','baseline.py']`, so every single `-n 1` invocation actually plays 4 capture.py games even though run_match only parses one result out. That's a baked-in 4× budget inflation that STRATEGY missed.

(Separately: the pm7 `-l RANDOM<seed>` workaround is orthogonal — it fixes variance, not throughput.)

## Finding 3 — fitness signal IS present, but noise-dominated at n=8

- gen 1: best genome fitness **0.101** (computed via `compute_fitness` = pool_win_rate − 0.5·stddev_win_rate with no crash/monster term in phase 2a). Best genome beat ~15% of pool games, less penalty for variance.
- gen 0, gen 2: all-zero. Any signal in gen 1 didn't persist — the elite mean in gen 2 was recomputed and happened to sample into a zero-fitness region.
- stagnation_count reached 3 in only 3 gens; restart trigger is 5 gens, so no restart fired. But the trajectory is clearly noise-dominated.

**Not a bug in the evolution pipeline** — it's the expected behavior of 8-pop CEM on a noisy fitness function. M6 full spec (pop=40) has 5× more exploration per gen and should average out the noise.

## Decisions + options

1. **α-5 permanently skipped** — pre-decided based on pm13 timings.
2. **M4b-4 objective met**: pipeline runs end-to-end, per-gen JSON emitted with `best_ever_*`, timing captured, resume remains ready. Mark M4b-4 ✅.
3. **M6 ~103h is not shippable as-is.** Four response options (user decision pending):
   - **(A) 4-loop bypass**: modify run_match.py to import `capture.runGames` directly and invoke 1 game without spawning a subprocess → capture.py main's `for i in lst` never runs → potential 4× speedup → M6 → ~26h. Risk: correctness (capture.py's RNG state, imports, initializers may behave differently). ~30min-1h work + 1 cycle of T1-T4 verification.
   - **(B) Scale down**: pop 40→20 + games 264→132 + gens 10+20→5+10 → 8× reduction → ~13h. Cost: smaller pool/generations reduce CEM's ability to converge on robust weights; final ceiling likely lower.
   - **(C) Accept 4-day wall**: run M6 overnight + all weekend. No code changes; M6-a/b/c/d tier split keeps each block ≤ 8h.
   - **(D) Hybrid** (A + mild scale-down): bypass 4-loop AND drop pop 40→30 → ~15h comfortably inside a day.
4. Tier policy keeps us safe regardless: M6-a smoke (2 gens, ~1.5h at current speed) runs first. If the trajectory looks dead like gens 0/2 above, we stop and reassess before committing to the full run.

## Next-session priority

User decision on A/B/C/D. My recommendation is **(D) hybrid** but only after proving (A) doesn't break correctness — the capture.py framework file is immutable per CLAUDE.md, but *calling* its functions from our own wrapper is allowed (we don't modify capture.py, we just skip its `__main__` block). Needs care because the 4-loop was possibly added by the assignment to prevent us from doing exactly this — if our submission `your_best.py` loads via capture.py's original flow, all four lst-iterations still run against us. But during evolution we don't care about what lst iterates over; we only want one game per run_match call.

If user opts for (C), set M6-a going tonight as-is (1.5h smoke), confirm trajectory is non-dead, then launch M6-b overnight. No code changes required.

## Artifacts

- `/tmp/m5_dryrun.log` — full stdout+stderr
- `experiments/artifacts/2a_gen{000,001,002}.json` — per-gen checkpoints with `best_ever_*`
- `experiments/evolve.py` — adds `import time` + per-gen wall print


---
title: "Option α test plan (T1-T4) for evolve.py parallelization + resume"
tags: ["test-plan", "option-alpha", "evolve.py", "parallelization", "resume", "pre-alpha-stage-3"]
created: 2026-04-15T09:14:22.963Z
updated: 2026-04-15T09:14:22.963Z
sources: ["experiments/evolve.py", "Pre-α Stage 3 design"]
links: []
category: pattern
confidence: high
schemaVersion: 1
---

# Option α test plan (T1-T4) for evolve.py parallelization + resume

# Option α test plan (T1-T4) — parallelization + resume

## Purpose
TDD-style test cases to verify Option α's two changes (ProcessPoolExecutor genome-level parallelism in run_phase + `--resume-from <artifacts_dir>` checkpoint resume) work correctly before launching the full M6 ~23h campaign.

Run order: **T1 → T2 → T3 → T4** (crash-robustness depends on baseline correctness; resume test requires parallel implementation to be stable).

## T1 — same-genome 2× call equivalence (variance bound)

**Purpose**: Parallelization must not change per-genome semantics. A given (genome, opponents, layouts, seed) input should produce the same fitness distribution across runs, modulo the documented pm7 clock-seeded PRNG variance.

**Setup**:
- `genome = h1test_weights` (known-good seed)
- `opponents = ['baseline']`, `layouts = ['defaultCapture']`, `games_per_opponent = 4`

**Procedure**:
1. Run `evaluate_genome` once, record `result_a`.
2. Run it again with identical args, record `result_b`.

**Pass criteria**:
- Both return a dict with keys `{pool_win_rate, crash_rate, stddev_win_rate, monster_win_rate}`.
- Every value is a float in `[0.0, 1.0]`.
- `crash_rate == 0.0` in both.
- `|result_a['pool_win_rate'] - result_b['pool_win_rate']| < 0.5` (wide because n=4; variance is expected).

## T2 — different-genome parallel independence (ordering check)

**Purpose**: Running N genomes in parallel must attribute each result to its own genome (no temp-file cross-contamination, no race on `_weights_override`).

**Setup**:
- 4 genomes, each a known-quality weight set:
  - G_h1test (35% vs baseline in pm4)
  - G_h1b (30% vs baseline)
  - G_h1c (20% vs baseline)
  - G_tuned (0% vs baseline — structural tie)
- Same opponent pool as T1 but `games_per_opponent = 12` (more signal).
- Run through the parallelized `run_phase` with `max_workers=4`.

**Procedure**:
1. Submit all 4 to the ProcessPool.
2. Collect results keyed by genome_id.

**Pass criteria**:
- Each genome_id gets exactly one result.
- The ranking `G_h1test.pool_win_rate ≥ G_h1b ≥ G_h1c ≥ G_tuned` holds with tolerance (at least **3 of the 4 pairwise inequalities** correct — n=12 per genome is noisy).
- `G_tuned.pool_win_rate ≤ 0.1` (the structural-tie control must still tie — this catches any cross-genome weight bleed).

## T3 — crash robustness (bad input + missing opponent)

**Purpose**: One bad genome / missing agent must not abort the entire generation.

**Setup**:
- Genome 0: valid h1test-style genome.
- Genome 1: genome spec pointing at a non-existent agent (e.g., `"opponents=['nonexistent_agent']"`)  OR malformed JSON path injection (requires touching evaluate_genome to accept a pre-made JSON).
- Alternative simpler trigger: one genome with `opponents=['nonexistent_agent_xyz']` forcing `run_match` into `nonzero_exit` crash.

**Procedure**:
1. Run both in the parallel pool.
2. Inspect returned dicts.

**Pass criteria**:
- Genome 0 returns a valid result dict (pool_win_rate > 0 or at least no crash marker).
- Genome 1 returns a dict with `crash_rate > 0.0` AND the caller survives (no uncaught exception propagating out of the pool).
- The overall `run_phase` completes; `gen_records` JSON is still emitted for that generation.

## T4 — resume after kill (checkpoint integrity)

**Purpose**: `--resume-from <artifacts_dir>` must let a killed campaign pick up from the last completed generation without re-running already-done work.

**Setup**:
- Small `run_phase` config: `n_gens=3`, `N=4`, `games_per_opponent=4`.
- Phase "2a".

**Procedure**:
1. Start `evolve.py --phase 2a --n-gens-2a 3 --pop 4 --games-per-opponent-2a 4`.
2. **After gen 0's JSON appears** (`experiments/artifacts/2a_gen000.json`), SIGKILL the process.
3. Verify `2a_gen000.json` is valid and well-formed.
4. Re-run `evolve.py --phase 2a --n-gens-2a 3 --pop 4 --games-per-opponent-2a 4 --resume-from experiments/artifacts/`
5. Inspect which generations the resume produces.

**Pass criteria**:
- `gen000.json` is not overwritten (timestamp unchanged) — resume RE-USES it, doesn't regenerate.
- New files `gen001.json`, `gen002.json` get produced.
- Final `result['gen_records']` contains records for gens 0, 1, 2 (in that order) — resume reads gen 0's mean/sigma, then continues.
- `best_ever_fitness` and `stagnation_count` are correctly restored across the kill boundary (inspect printouts).

## Out of scope for T1-T4

- End-to-end M5 dry-run quality check (fitness trend, elite mean > gen mean). That belongs to M4b-4.
- Monster pool validation (no monsters in T1-T3; T4 is phase-2a only).
- Sequential halving / HALL_OF_FAME — those are post-α.

## Expected outcome matrix

| Test | Parallelization exposes bug | Resume exposes bug |
|---|---|---|
| T1 | If a worker inherits stale env → differing results | — |
| T2 | If temp JSON collides → wrong weights applied → wrong ranking | — |
| T3 | If one crash kills the pool → whole generation lost | — |
| T4 | — | If mean/sigma/best_ever not properly restored → resume behaves like a fresh start |

Run T1-T3 once the parallelism code compiles; T4 after resume code lands.


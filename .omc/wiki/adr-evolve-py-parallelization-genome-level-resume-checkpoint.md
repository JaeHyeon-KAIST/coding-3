---
title: "ADR — evolve.py parallelization (genome-level) + resume checkpoint"
tags: ["adr", "decision", "evolve.py", "parallelization", "resume", "option-alpha", "pre-alpha-stage-4"]
created: 2026-04-15T09:15:10.526Z
updated: 2026-04-15T09:15:10.526Z
sources: ["Pre-α Stage 1 baseline (7.74s/match)", "STRATEGY.md §6.5-6.6", "Pre-α Stage 2 gap analysis"]
links: []
category: decision
confidence: high
schemaVersion: 1
---

# ADR — evolve.py parallelization (genome-level) + resume checkpoint

# ADR — evolve.py parallelization (genome-level) + resume checkpoint

**Date**: 2026-04-15 (Pre-α Stage 4)
**Status**: Decided, implementation in Option α
**Supersedes**: evolve.py's implicit sequential run_phase loop (pm8 M4b-3)
**Driven by**: Pre-α Stage 1 empirical baseline + STRATEGY.md §6.5-6.6 + M6 ~20h budget target

## Context

M4b-3 landed a working but sequential `evaluate_genome` + `run_phase`. Empirical measurement (Stage 1): 72 games/genome costs 557s wall, i.e. **7.74s per run_match** (where each run_match invocation actually plays 4 capture.py games due to the immutable 4-loop, so ~1.94s per game).

Extrapolation to M6 full campaign (STRATEGY §6.6):
- Phase 2a: 264 games × 40 genomes × 10 gens ≈ **62h sequential**
- Phase 2b: 224 games × 40 genomes × 20 gens ≈ **124h sequential**
- Total: **~186h ≈ 8 days sequential** → **non-viable**

STRATEGY §6.6 targets **~20h laptop parallel wall**. That requires roughly **8-9× speedup** on a 12-core Apple Silicon box (leaving 3-4 cores for OS + hooks + terminal).

Additionally, evolve.py currently has no resume capability. A crash 15h into a 23h run loses all progress. STRATEGY §6.6's "Halt conditions" clause presupposes some recovery mechanism.

## Decision

### Decision 1 — Genome-level parallelism (option ii)

Inside `run_phase`, replace the sequential genome loop:

```python
for gid, genome in enumerate(population):
    result = evaluate_genome(gid, genome, phase, ...)
    fitnesses.append(compute_fitness(result, phase))
```

with a ProcessPoolExecutor that evaluates N=40 genomes concurrently, capped at `min(physical_cores - 1, 8)` workers so we leave headroom for the OS and the parent evolve.py process.

```python
from concurrent.futures import ProcessPoolExecutor, as_completed

workers = min(physical_cores() - 1, 8)  # leave 1 for OS + 1 for parent
fitnesses = [None] * len(population)
eval_results = [None] * len(population)
with ProcessPoolExecutor(max_workers=workers) as pool:
    futures = {
        pool.submit(evaluate_genome, gid, genome, phase, opponents, layouts,
                    games_per_opponent, seed_gen + gid): gid
        for gid, genome in enumerate(population)
    }
    for fut in as_completed(futures):
        gid = futures[fut]
        try:
            result = fut.result()
        except Exception as e:
            # Treat a worker-level exception as f=worst, NOT f=0 silently.
            # Log it; a repeated pattern should bubble up the stagnation monitor.
            print(f"[evolve] genome {gid} worker error: {e}", file=sys.stderr)
            result = {"pool_win_rate": 0.0, "crash_rate": 1.0,
                      "stddev_win_rate": 0.0, "monster_win_rate": 0.0}
        eval_results[gid] = result
        fitnesses[gid] = compute_fitness(result, phase)
```

**Rejected alternatives**:

- **(i) Match-level parallelism** (flatten all 11520 matches/gen into one big pool): more implementation complexity (cross-genome result aggregation, temp-JSON sharing), same asymptotic wall time because both approaches are CPU-bound on run_match subprocesses. Future optimization if we find genome-level leaves workers idle at end-of-gen.
- **(iii) Hybrid** (genome-level + internal match parallelism): unclear additional gain since genome-level already saturates cores, and the added complexity would ripple through test cases T1-T3.

### Decision 2 — Resume via existing per-gen JSON (no new format)

evolve.py already emits `artifacts/{phase}_gen{N:03d}.json` with `mean_genome`, `sigma`, `best_fitness`, `snr`, `stagnation_count`. The resume logic is a one-way reader:

```python
def _load_last_checkpoint(phase: str, artifacts_dir: Path):
    """Scan artifacts/ for {phase}_gen*.json; return (last_gen_idx, mean, sigma,
    stagnation_count, best_ever_fitness, best_ever_genome) or None if fresh run.

    best_ever_* is not in the per-gen JSON today (only best_fitness of that gen).
    We ADD a `best_ever_genome` + `best_ever_fitness` field to each gen JSON so
    resume picks up exactly where the killed run left off. This is a forward-
    compatible addition; old gen JSONs without these fields fall back to the
    sampled population max.
    """
```

CLI: `evolve.py --resume-from <artifacts_dir>` reads the highest `{phase}_gen{N}.json`, initializes run_phase with its `mean`, `sigma`, `stagnation_count`, and starts at gen N+1.

**Rejected alternatives**:

- **Append-only single checkpoint file**: adds a second persistence mechanism for no real benefit.
- **SQLite checkpoint DB**: overkill for 30 generations × ~1KB each.

## Consequences

**Positive**:

- M6 total wall time target **~23h** (7.74s/match × 72 matches × (10 gens × 40 genomes + 20 gens × 40 genomes) / 8 parallel ÷ 3600s). Tracks STRATEGY §6.6's 20h target.
- Resume reduces 20h-run risk from catastrophic to graceful (worst case: lose 1 gen = ~30 min).
- Genome-level pool naturally isolates worker crashes — one bad genome doesn't kill the generation.
- Test plan (Stage 3) T1-T4 maps cleanly onto both decisions.

**Negative**:

- Each evaluate_genome call writes/reads a temp JSON per genome (40 × 30 = 1200 tiny files/phase, cleaned up in `finally`). Disk I/O in an SSD-dominant machine is trivial; flagged in case we ever port to a slow filesystem.
- 8 workers × average 69s each means gen boundaries can have up to 30% idle time if one genome is an outlier (e.g., an unlucky layout hits many timeouts). We're OK with that variance — STRATEGY budget has a buffer.
- ProcessPoolExecutor spawn cost (~200ms per worker fork on macOS) × 40 genomes per gen × 30 gens = ~240s total overhead across the campaign. Negligible.

**Neutral**:

- Parallelism lives at run_phase level; evaluate_genome remains a pure function. Tests T1-T3 can exercise each layer independently.

## Open items (post-α)

- Sequential halving (STRATEGY §6.4) — adds ~20% budget efficiency. Implement if Phase 2a results show clear top-few-vs-rest separation that justifies the re-eval cost.
- HALL_OF_FAME pool rotation (STRATEGY §6.5) — helps only if evolved agents drift into pool-specific overfit. Evaluate after M5 dry-run.
- Truncated eval (first 3 gens 600 moves) — potential 2× speedup on the initial 3 gens. Requires run_match.py to accept a `--time-limit` pass-through to capture.py's `-i` flag. ~15 min if we want it; skipped unless M5 dry-run shows the initial gens are budget-dominant.

## Cross-references

- Pre-α Stage 1 baseline numbers: wiki `session-log/2026-04-15-pm8-*` (once ingested by Stage 5)
- Test plan: wiki `pattern/option-alpha-test-plan-t1-t4-for-evolve-py`
- STRATEGY.md §6.5-6.6: parallelism + compute budget spec
- wiki `debugging/experiments-infrastructure-audit-pre-m4-m6`: original C1/C2 audit findings


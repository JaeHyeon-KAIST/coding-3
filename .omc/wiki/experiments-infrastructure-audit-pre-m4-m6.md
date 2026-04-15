---
title: "Experiments infrastructure audit — pre-M4/M6"
tags: ["infrastructure", "audit", "m4", "m5", "m6", "tournament", "evolution", "resilience", "checkpointing", "seed-bug", "open"]
created: 2026-04-15T01:16:10.392Z
updated: 2026-04-15T01:16:10.392Z
sources: []
links: []
category: debugging
confidence: high
schemaVersion: 1
---

# Experiments infrastructure audit — pre-M4/M6

# Experiments infrastructure audit — pre-M4/M6 (2026-04-15 pm)

**Source**: `architect` subagent READ-ONLY audit of `experiments/` pipeline + OS/process layer durability.

**STATUS: audit complete. Five findings open (2 CRITICAL, 3 MEDIUM). One prior concern downgraded to false-alarm.**

## Critical findings

### C1. `evolve.py:140-142` silently swallows `NotImplementedError`

```python
try:
    result = evaluate_genome(...)          # currently raises NotImplementedError
    f = compute_fitness(result, phase)
except NotImplementedError:                # ← swallows
    f = 0.0
    result = {"pool_win_rate": 0.0, ...}
```

**Impact**: a 20h M6 campaign would "complete successfully" with 30 generations of `f=0.0` fitness and emit `final_weights.py` containing **random noise** (just sampled from the initial Gaussian, never selected for fitness). Zero way to detect this failure from the output artifacts alone — the script prints `[evolve] phase=2b gen=N best=0.000 ...` and proceeds.

**Fix**: remove the `except NotImplementedError` branch, or gate it with an explicit `--allow-unimplemented` CLI flag for M5 dry-runs only. Loud fail-fast is required.

### C2. `run_match.py:72` seed value never reaches `capture.py`

```python
# run_match.py:71-72
if seed is not None:
    cmd += ["--fixRandomSeed"]             # ← only flag, seed value dropped

# capture.py:852 (framework, immutable per CLAUDE.md)
if options.fixRandomSeed: random.seed('cs188')   # ← hardcoded constant
```

`PYTHONHASHSEED=str(seed)` is set via env var (`run_match.py:76`) but affects only Python dict iteration order, NOT gameplay randomness. `capture.py` owns all game RNG and seeds it to `'cs188'` regardless.

**Impact**: STRATEGY.md's "5 seeds per cell × 2 color swaps" variance reduction is a **no-op on the seed axis**. CRN pairing is color-swap-only. The tournament matrix collapses on seed dimension — every "seed" is the same PRNG state.

**Workaround (since capture.py is immutable)**: use the `-l RANDOM<seed>` layout generator flag to inject layout diversity, mapping the tournament's `seed` dim onto layout-generation seeds. This gives real variance but requires layout tests to be layout-random rather than fixed.

## Medium findings

### M1. `run_match.py` missing process-group isolation

`subprocess.run(...)` at `run_match.py:80` lacks `start_new_session=True`. On `TimeoutExpired`, only the direct child (python interpreter running `capture.py`) is killed. If the agent is mid-SIGALRM handler or stuck in a C extension, grandchildren can orphan. Workers then carry zombie handles.

**Fix (one-liner)**: add `start_new_session=True` to `subprocess.run`; on `TimeoutExpired`, `os.killpg(os.getpgid(proc.pid), signal.SIGKILL)` as belt-and-braces.

### M2. `select_top4.py:55-69` `FAMILY_MAP` missing entries

Not mapped: `zoo_dummy`, `zoo_reflex_h1test`, and any future `zoo_reflex_h1b.py`, `zoo_reflex_h1c.py`. These will be silently dropped from ELO family selection during M7 flatten. No warning emitted.

**Fix**: add an "unknown_family" bucket + WARN log for unmapped agents.

### M3. `ProcessPoolExecutor` `BrokenProcessPool` unhandled

Python 3.9: if any worker segfaults, the entire pool enters permanent `BrokenProcessPool` state; all subsequent `submit()` raises. `tournament.py:127-139` has no recovery — a single worker crash aborts the whole tournament mid-run.

**Fix**: wrap `submit` calls in `try/except BrokenProcessPool`; on break, shutdown old pool, construct new one, re-enqueue the remaining `remaining_jobs` set.

## False alarm (resolved)

- **`evolve.py` `gen_records` list growth** — 30 generations × ~250 bytes/record = ~8KB. Not a memory concern.
- **subprocess stdout buffer OOM** — current agents don't print-spam. Present risk is bounded at ~2KB/game. Re-assess if future debug-verbose agents are added.

## Tournament.py additional findings (from audit)

- `tournament.py:128` eagerly submits all futures upfront — at M6 scale (~280K jobs) this builds ~85MB of Future + task-tuple objects in parent process. Fix: sliding window of `workers × 4` in-flight.
- `tournament.py:126-139` keeps `results = []` in RAM; CSV written only at `:150`. **Any mid-run failure discards everything**. Fix: CSV-append with `f.flush() + os.fsync()` per row.
- `tournament.py:79` fragile: `json.loads(proc.stdout.strip().splitlines()[-1])` — trailing newlines from numpy warnings / atexit handlers break parsing.

## Patch recipes (summary)

### M4 TODAY (~1h total)
1. `tournament.py` CSV append per row + `--resume-from <csv>` flag
2. `tournament.py` sliding futures window (`workers × 4` in-flight max)
3. `run_match.py` `start_new_session=True` + timeout `killpg`
4. `run_match.py` layout-RANDOM seed workaround (`-l RANDOM<seed>`)
5. Launch in `tmux new -d -s m4 'caffeinate -i .venv/bin/python experiments/tournament.py ...'`

### Before M6 overnight (~3h additional)
6. `evaluate_genome` actual implementation (blocked on weight-override protocol design)
7. Per-genome atomic checkpoint via `os.replace(tmp, final)` on APFS
8. Stop swallowing `NotImplementedError` (loud raise)
9. Persist `stagnation_count` in per-gen record
10. Phase 2a→2b disk handoff (read last `2a_gen*.json` to init Phase 2b if `result_2a is None`)
11. Sidecar watchdog script (~30 lines): alert if `artifacts/` row count stops growing for >10 min

### Durability wrapper (decision)
- M4 (2-3h): `tmux new -d` + `caffeinate -i` sufficient
- M6 (20h): same, plus keep laptop plugged in + lid open; optionally launchd plist for auto-restart on reboot

## Cross-references

- Parent discovery: wiki `debugging/m3-smoke-deadlock-0-win-pattern-across-all-tuned-agents` (H1 confirmed via this pipeline — so the pipeline's correctness matters for every downstream measurement)
- Plan sections: `STRATEGY.md` §3.4 (dual compute budgets), §6.3 (CEM 2-phase), §6.5 (efficiency), §6.6 (compute)
- Code: `experiments/{tournament.py, run_match.py, evolve.py, select_top4.py, verify_flatten.py}`
- Immutable per CLAUDE.md: `capture.py:852` (`random.seed('cs188')` hardcode is why C2 cannot be fixed at framework level)

## Audit author

`architect` subagent (Opus, READ-ONLY, 2026-04-15 pm, ~5min investigation)


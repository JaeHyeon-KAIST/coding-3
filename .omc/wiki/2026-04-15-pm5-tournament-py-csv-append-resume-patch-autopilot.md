---
title: "2026-04-15 pm5 - tournament.py CSV-append + resume patch (autopilot)"
tags: ["session-log", "autopilot", "m4-infra", "tournament.py", "csv-append", "fsync", "resume", "crash-safety", "code-review-approved"]
created: 2026-04-15T05:28:55.635Z
updated: 2026-04-15T05:28:55.635Z
sources: ["experiments/tournament.py", "/tmp/tournament_test_pm5.csv", "/tmp/tournament_test_pm5b.csv", "/tmp/tournament_t2.log"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-15 pm5 - tournament.py CSV-append + resume patch (autopilot)

# Session 2026-04-15 pm5 — tournament.py CSV-append + resume patch (autopilot)

## Focus
User invoked `/autopilot` to execute the pm4 "어차피 해야 할 crash-safety 패치" recommendation. First M4 infra patch: make `experiments/tournament.py` survive mid-run crashes during the planned 20h M6 evolution campaign.

## Scope (committed vs deferred)

**Committed in this patch**:
- Per-row CSV append with `flush() + fsync()` for each completed game.
- Parent directory fsync on first-write path (APFS hard-crash durability).
- `_load_completed_keys(resume_csv)` helper — reads prior CSV, returns `(red, blue, layout, seed)` dedup set with seed normalised to `int|None`.
- `--resume-from <csv>` CLI flag; defaults to `--out` when that path exists (in-place append continuation).
- Module-level `CSV_COLS` constant (replaced duplicated inline column list).

**Deferred** (scope-out; separate wiki-audit items):
- Sliding futures window (85MB at M6 scale) — correctness-neutral, memory concern only.
- `BrokenProcessPool` auto-recovery — a segfault aborts the run, but `--resume-from` allows manual restart, so lifeline exists.
- `evolve.py:140-142` NotImplementedError swallow — separate M4b task.
- `run_match.py:72` seed plumbing workaround — separate M4c task.
- `run_match.py:80` `start_new_session=True` — separate M4c task.
- `select_top4.py` flatten_agent — M7 task.

## Phase 3 QA results (4/4 pass)

| Test | Command | Expected | Observed |
|---|---|---|---|
| T1 --help | `tournament.py --help` | `--resume-from` flag listed | ✅ present, helptext correct |
| T2 fresh | `--agents zoo_dummy baseline --seeds 1` to empty path | CSV 1 header + 2 data rows, 0 crash | ✅ 3 lines, `[done] 2 new matches in 7s` |
| T3 rerun | Same command again | `[resume] skipping 2; 0 remaining`, row count unchanged | ✅ "nothing to do" printed, still 3 lines |
| T4 partial | Same args + `--seeds 1 2` | Skip seed-1 pair, append seed-2 pair, single header | ✅ 5 lines, 1 header, 4 data rows |

Regression after M1 fix (parent-dir fsync add): T2-equivalent reran clean, 3 lines, 0 crash, `2 new matches in 3s`.

## Phase 4 code-reviewer verdict

**APPROVE with nits** — 0 🔴, 2 🟡 (orthogonal to patch scope), 3 🟢 nits.

Code-reviewer confirmed the 6 focus questions:
1. Per-row `flush()+fsync()` sufficient on APFS **after** parent-dir fsync was added (🟡 M1 — which I applied on the same turn).
2. Resume correctness solid; seed normalisation edge cases all handled.
3. Backward compat OK (single caller is `main()`, new kwarg is additive).
4. Empty-header-only file: correct behaviour (no duplicate header emitted).
5. No concurrent writer race (results returned serially from pool).
6. Docstring "Resilience contract" praised; `buffering=1 + flush + fsync` belt-and-suspenders noted as intentional.

Remaining 🟡 findings (deferred to separate patches):
- **M1 parent-dir fsync** ← APPLIED same-turn; confirmed via regression test.
- **M2 BrokenProcessPool handling** — audit finding M3; not in this patch's scope.

🟢 nits skipped intentionally:
- N1 malformed seed logging (low-value noise).
- N2 dead `crn_pair_colors` kwarg (pre-existing, unrelated).
- N3 "reading from X; writing to Y" stderr line (already present via existing `[resume]` + `[done]` output).

## Final file shape

- `CSV_COLS` module constant (13 cols, canonical order matching STRATEGY.md §7.4).
- `_load_completed_keys(resume_csv: Path) -> set` — tolerant of missing/empty/truncated files.
- `run_tournament(..., resume_from=None)` — opens with `"a"` when target has bytes, else `"w"`; per-row `flush+fsync`; parent-dir fsync on first-write.
- `main()` — `--resume-from` flag wired through.

## Invariant the patch now guarantees

> If the process is SIGKILL'd / powered off at any point during run_tournament, every game that had returned from `pool.as_completed` before the kill is persisted to disk (including its directory entry on APFS). Re-running the same command with the same `--out` automatically skips those rows and continues with the remainder.

## Decisions

1. Do **not** commit yet — user's CLAUDE.md rule: commits only when user explicitly asks.
2. M1 fix (parent-dir fsync) applied in-turn, not deferred. The patch now fully earns its "crash-safe" label.
3. Next natural follow-up: M4b (evolve.py NotImplementedError fix + `evaluate_genome` implementation) — the last BLOCKING 🔴 before M5 dry-run. Then M4c (run_match.py).
4. `tournament.py` sliding window + BrokenProcessPool retry stay deferred; re-evaluate before M6 kickoff.

## Next-session priority

M4b — implement `evaluate_genome` and remove the `except NotImplementedError: f=0.0` swallow. This is the single biggest remaining blocker for the M6 evolution campaign (without it, 20h of CPU produces random noise). After M4b, M4c (15 min) + M5 dry-run (~1h) complete the pre-flight. Then M6 20h with confidence that a laptop sleep won't discard the run.


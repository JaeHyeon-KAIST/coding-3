---
title: "2026-04-16 - pm18 Phase 1 B1+C4 done + A1 launched learning confirmed"
tags: ["session-log", "pm18", "phase1", "B1", "C4", "A1", "evolve", "cem-learning", "server"]
created: 2026-04-16T00:06:39.389Z
updated: 2026-04-16T00:06:39.389Z
sources: ["git a1b5569 pm18 C4", "git 379dc74 pm18 B1", "server log logs/phase2_A1_17dim_20260416-0637.log", "experiments/evolve.py FEATURE_NAMES", "minicontest/zoo_features.py SEED_WEIGHTS_OFFENSIVE"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-16 - pm18 Phase 1 B1+C4 done + A1 launched learning confirmed

# 2026-04-16 pm18 — Phase 1 B1+C4 done; A1 Order 1 launched and learning

## Focus

Execute the **first slot** of the pm17 6-phase performance-max pipeline: launch A1 17-dim control evolve on server overnight AND complete Phase 1 Mac coding (B1 features + C4 MCTS time polling) in parallel. User-selected strategy: "A 방식" (server launch + Mac coding concurrently).

## Activities

1. **Read onboarding**: SESSION_RESUME.md, STATUS.md, wiki decision/next-session-execution-plan-performance-max-6-phase-pipeline, wiki environment/remote-compute-infra-wsl2-ryzen-7950x-server-jdl-wsl.
2. **Verified server state**: `jdl_wsl` tmux session `work` alive, HEAD `5fd795c` synced with Mac, `experiments/artifacts/` clean.
3. **Resolved 11-opp pool ambiguity** — STRATEGY §6.4 template includes MCTS-sibling + mcts_q_guided slots, but pm6 finding shows all MCTS agents timeout under run_match's 120s per-game wall. **Designed a pragmatic no-MCTS 11-opp pool** for A1: `baseline×2 + zoo_reflex_{h1test,h1b,h1c,aggressive,defensive} + zoo_minimax_{ab_d2,ab_d3_opp} + zoo_expectimax + monster_rule_expert`.
4. **Launched A1 on server** via `ssh jdl_wsl 'tmux send-keys -t work "..." Enter'` at 06:37 server time. Command: `.venv/bin/python experiments/evolve.py --phase both --master-seed 42 --workers 16 --n-gens-2a 10 --n-gens-2b 20 --pop 40 --rho 0.35 --games-per-opponent-2a 24 --games-per-opponent-2b 16 --init-mean-from h1test --opponents <11 pool> --layouts defaultCapture RANDOM 2>&1 | tee logs/phase2_A1_17dim_20260416-0637.log`. Verified 17 processes (1 parent + 16 ProcessPool workers), log header line emitted.
5. **Set up persistent Monitor** (`ssh jdl_wsl "tail -F .../phase2_A1_17dim_*.log" | grep -E '\[evolve\]|Traceback|Error|BrokenProcessPool|Killed|OOM|CRASH|FAILED|forfeit'`) — delivers gen-completion notifications and error signals automatically.
6. **C4 implemented** in `minicontest/zoo_mcts_{heuristic,random,q_guided}.py`: replaced `for _ in range(MAX_ITERS)` with `while iters < MAX_ITERS and time.time() < deadline` in `_mcts_search` / `_search`. Uses `MOVE_BUDGET = 0.80s` from `zoo_core` (under capture.py's 1s warning threshold). Committed as `a1b5569`.
7. **B1 implemented** in `minicontest/zoo_features.py` + `experiments/evolve.py`: +3 features (`f_scaredGhostChase`, `f_returnUrgency`, `f_teammateSpread`) with non-linear formulas, seed weights = 0.0, `FEATURE_NAMES` + `_H1TEST_FEAT_SEED` extended, Phase 2a/2b genome_dims bumped 29→32 / 46→52. Committed as `379dc74`.
8. **Smokes** on Mac:
   - `zoo_reflex_tuned` (uses B1 features) vs `baseline`: 2.14s, Tie, crashed=false → B1 compute works end-to-end.
   - `zoo_mcts_q_guided` vs `baseline`: 4m43s full 1200-move game, Tie, crashed=false → C4 time polling works without hang.

## Observations

### A1 first 3 gens (server)

| gen | best | mean | snr | wall |
|---|---|---|---|---|
| 0 | 0.112 | 0.007 | 0.61 | 2796.8s |
| 1 | 0.181 | 0.026 | 0.91 | 2895.4s |
| 2 | 0.483 | 0.099 | 1.10 | 2926.9s |

- **CEM learning**: best **4.3× over 3 gens**, mean **14× over 3 gens** — real signal, not stuck.
- **snr crossed 1.0 at gen 2**: gen 0's 0.61 would increment `stagnation_count`; gen 2's 1.10 resets it. STRATEGY §6.3 drift alert threshold cleared.
- **gen 0 best=0.112 ≈ h1test seed fitness** on the 11-opp pool. Matches expectation: h1test historical vs baseline was 35% (pm4) / 50% (pm7 M4-v2), but on a harder 11-opp pool (includes monster_rule_expert + minimax + expectimax), pool win rate drops to ~20-25% and the stddev penalty of 0.5 knocks fitness down to ~0.12.
- **gen 2 best=0.483 ≈ 48% pool win rate** — evolution has found a genome that ~doubles h1test's pool win rate in 2 steps. Strong sign that the 20-dim 17-feat search space has room above h1test.

### Wall time recalibration

- **Measured ~47-48 min/gen**, stable from gen 0 to gen 2 (rules out ProcessPool ramp-up as the cause).
- Wiki `environment/remote-compute-infra-...` estimate was ~30 min/gen (based on simple `run_match.py` benchmark of 1.3s/match × 40 pop × 264 games / 16 workers).
- **Actual ≈ 1.5× slower** — probably subprocess spawn overhead per match + layout RANDOM generation + Mac-compat abstractions. Not investigated further in pm18.
- **Revised total**: Phase 2a 7.8h, Phase 2b ~11h (224 games/genome vs 264, ~34 min/gen), **total ≈ 18-19h**. Started 06:37 → finish ETA ~00:40 next day. Overnight viable but much longer than wiki's 10h.

### Known blocker — Order 6 MCTS evolve container

C4 successfully implements time polling at `MOVE_BUDGET = 0.80s` (submission-safe). But:
- Full 1200-move MCTS game wall = 600 MCTS moves × 0.8s = 480s ≈ 8 min (measured 4m43s on defaultCapture, close enough).
- run_match.py per-game subprocess timeout = 120s.
- **Every MCTS-container training match would forfeit** in evolve pool.

Fix: add `ZOO_MCTS_MOVE_BUDGET` env var read at each `_mcts_search` / `_search` call (fallback to `MOVE_BUDGET`). Evolve training can then set `ZOO_MCTS_MOVE_BUDGET=0.1` via `run_match.py env=`, keeping submission behaviour unchanged. Estimated patch: ~15 lines across 3 files + run_match.py env plumbing.

**Not a blocker for Orders 1-5**: A1 uses reflex container, Orders 2-5 use reflex/minimax. Only Order 6 (C4+B1 MCTS container) needs this. Defer until Order 6 launch time.

## Decisions

1. **Pragmatic 11-opp pool for A1** excludes all MCTS and the MCTS-family monsters (monster_mcts_hand, monster_minimax_d4). Includes `monster_rule_expert` as the one non-timing-out adversarial reference. A2-A8 (post-Order 6 fix) will use the full pool.
2. **`--phase both` for A1** (single invocation runs Phase 2a then Phase 2b with same opponent list). Accepts that Phase 2b monster bonus slot is vacant (monster_bonus_active=1 but monster_win_rate=0 → 0 contribution) — simpler than standalone Phase 2b runs with the current evolve.py CLI.
3. **Commit C4 and B1 as atomic separate commits** (`a1b5569`, `379dc74`) rather than a single combined commit. Lets us roll back independently if one causes issues downstream.
4. **Leave Monitor + server A1 running across session boundary**. Session ends, tmux `work` persists, A1 continues. Next session verifies via `pgrep` + log tail (script in SESSION_RESUME.md).
5. **Skip AI_USAGE.md entry for this session**: per CLAUDE.md rule, only `your_best.py`/`your_baseline1-3.py` direct edits trigger AI_USAGE append. B1 touched `zoo_features.py` and C4 touched `zoo_mcts_*.py` — dev-time files, not submission targets. M7 flatten step will concatenate them into `your_best.py` at submission time, which IS the AI_USAGE trigger moment.

## Open items

- [ ] Next session: verify A1 state (running / finished / crashed) via the SESSION_RESUME.md's verify command.
- [ ] If A1 finished: archive artifacts to `experiments/artifacts/phase2_A1_17dim/`, commit log, launch Order 2 (A1+B1 20-dim, init_mean=h1test, same 11-opp no-MCTS pool).
- [ ] Phase 1 follow-up: `ZOO_MCTS_MOVE_BUDGET` env override patch — 15-line fix before Order 6.
- [ ] Watch gen 3+: if snr drops back below 1.0, stagnation accumulates. Check σ decay holding.
- [ ] Wall-time investigation deferred: gen 0 at 46.6 min vs wiki 30 min. Why 1.5× slower? Candidates: subprocess spawn cost per match, layout RANDOM generation, OS scheduling overhead at 32 threads. Not urgent.

## Next-session priority

1. Read this session log + STATUS.md critical observations.
2. Run A1 state verification (command in SESSION_RESUME.md §Next-session immediate actions).
3. If A1 done: archive + launch Order 2.
4. If A1 mid-run: either wait + do `ZOO_MCTS_MOVE_BUDGET` patch in parallel, OR interrupt + pivot decision.
5. Either way: next action is Order 2 launch OR the Order 6 patch, whichever unblocks the critical path first.


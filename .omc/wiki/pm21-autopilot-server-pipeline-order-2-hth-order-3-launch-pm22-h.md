---
title: "pm21 — autopilot server pipeline + Order 2 HTH + Order 3 launch + pm22 handoff"
tags: ["pm21", "autopilot", "cron", "Order-2-done", "Order-3-launched", "handoff-pm22", "HTH-battery", "Red-Queen-HOF", "A1-kept-champion"]
created: 2026-04-18T05:01:43.351Z
updated: 2026-04-18T05:01:43.351Z
sources: ["pm20 cron autopilot setup commit e160fac", "pm21 Order 2 HTH commit 4b11de1", "pm21 Phase 4 manual policy commit f72238f", "pm21 pm22 handoff doc .omc/plans/pm22-autopilot-resume.md"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# pm21 — autopilot server pipeline + Order 2 HTH + Order 3 launch + pm22 handoff

# pm21 session log — autopilot bootstrap + Order 2 HTH + Order 3 launch + handoff

**Date**: 2026-04-18 (Fri)
**Duration**: ~07:22-13:50 KST (~6.5h incl. long idle during Order 2 Phase 2b tail)
**Focus**: server autopilot orchestration, Order 2 completion handling, Order 3 launch

## Activities

1. **Autopilot orchestrator design** (pm20 carryover):
   - `.omc/plans/autopilot-server-pipeline.md` — decision-tree per stage S0/S1/S2
   - `.omc/state/autopilot-server-pipeline.json` — state file (gitignored)
   - `experiments/launch_orders_34.sh` updated — dynamic HOF pool auto-detect (glob zoo_reflex_O*.py)
   - CronCreate 43b0fdcc @ `7,37 * * * *` recurring (session-only)

2. **Order 2 completion + S1 pipeline** (09:07 cron fired):
   - gen 19 done (best=1.014, best_ever=1.028 at 2b gen 6)
   - HTH battery: baseline 163/200 = **81.5% Wilson [0.755, 0.863]**, monster 73.3%, h1test 85%, minimax 75%. 0 crashes.
   - Rule-based champion decision: Wilson LB 0.755 > A1's 0.728 BUT < 0.80 → **A1 kept** as submission. Order 2 added to Phase 4 pool.
   - Archive: `experiments/artifacts/phase2_A1_B1_20dim/` (server, gitignored)
   - `zoo_reflex_O2.py` generated via `make_hof_wrapper.py` (W_OFF=20, W_DEF=20 — B1 features learned)
   - Mac scp + commit `4b11de1` + push

3. **Order 3 launch** (~09:14 or 13:14 KST — server ambient time):
   - `launch_orders_34.sh 3` — seed=1001, init=h1test, HOF pool `[zoo_reflex_A1, zoo_reflex_O2]`
   - 18 processes healthy, Phase 2a gen 0 started
   - Log: `logs/phase2_A3_diverse_s1001_h1test_20260418-1314.log`

4. **Phase 4 policy revision** (user directive pm21):
   - Phase 4 round-robin tournament is MANUAL — autopilot STOPS at S2, no auto-launch
   - S3 stage deprecated (user controls Phase 4+ pipeline)
   - Commit f72238f

5. **pm22 handoff preparation**:
   - `.omc/plans/pm22-autopilot-resume.md` — 5-step resume doc (state detection, cron re-arm, S1 manual pipeline, hard stops)
   - `.omc/SESSION_RESUME.md` updated — pm22 TL;DR + pointer to handoff
   - `.omc/STATUS.md` updated — pm21 headline + handoff pointer
   - MEMORY.md index + pm22_autopilot_handoff.md entry
   - CronDelete 43b0fdcc (session ending, cron dies anyway — clean)

## Observations

- **Autopilot skill interference**: CronCreate prompt containing keyword "autopilot" kept re-triggering OMC autopilot skill state. Stop hook blocks after each cron wake. Workaround: periodic `state_write(active=false)` + `state_clear(skill-active)`. Noise but not blocking.
- **HTH seed sensitivity**: Order 2 at full 200-game HTH gave 81.5% vs A1's 79%. Both runs consistent enough to say "Order 2 barely exceeds A1". At 40g HTH across earlier pm20 D-series runs, A1 baseline WR swung 65%-85% — **Wilson CI overlap for almost all candidates**. Phase 4 tournament with 5 layouts × 5 seeds will give much tighter separation.
- **HOF pool auto-detect works**: bash glob `minicontest/zoo_reflex_O*.py` correctly expanded to `zoo_reflex_O2` in Order 3's opponent pool. Visible in launch log: `[launch] HOF wrappers in pool: zoo_reflex_A1 zoo_reflex_O2`.
- **WSL shutdown recovery validated**: earlier pm20 end → Apr 18 morning, WSL was shut down (Windows reboot likely). Recovery via `ssh jdl "wsl -d Ubuntu-22.04 -- uptime"` + `git pull` + `tmux new -d` + relaunch with `--resume-from` — Order 2 Phase 2b continued from gen 9 checkpoint. No work lost. This pattern documented in autopilot pipeline safety rails.

## Decisions

- Champion: **A1 stays** — Order 2 marginal (Wilson LB 0.755, CI overlap, not >= 0.80 threshold)
- Phase 4: **manual user kick-off** — remove auto-launch from autopilot plan
- Handoff: **pm22 fresh session** via `.omc/plans/pm22-autopilot-resume.md`
- Cron: **delete at session end** (session-only anyway) — pm22 re-arms

## Open items

- Order 3 running, ETA ~2026-04-19 09:15 KST
- Order 4 auto-launches after Order 3 S1 pipeline — ETA finish ~2026-04-20 05:15 KST
- Phase 4 tournament: user trigger Apr 20 morning
- Phase 5 multi-seed + M7/M8/M9/M10: later sessions

## Next-session priority

**pm22**: Read `.omc/plans/pm22-autopilot-resume.md` FIRST. Re-arm cron. Sit back — autopilot handles Order 3/4 until S2. Come back for Phase 4.

## Related wiki

- `pattern/server-order-queue-operational-runbook-launch-archive-verify-cyc` (operational pattern)
- `decision/pm20-expanded-roadmap-17-tasks-3-axis-development-ccg-enhanced` (pm20 plan)
- `decision/adr-pm19-phase-2-scope-revision-based-on-a1-validation-ccg-conse` (pm19 superseded)


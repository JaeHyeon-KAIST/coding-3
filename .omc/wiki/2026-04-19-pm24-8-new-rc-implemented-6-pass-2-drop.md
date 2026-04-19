---
title: "2026-04-19 - pm24 8 new rc implemented: 6 pass 2 drop"
tags: ["pm24", "rc-batch", "pacman", "batch-A", "batch-B", "rc28", "rc29", "rc30", "rc31", "rc34", "rc44", "rc48", "rc50", "top-k-stochastic-fail"]
created: 2026-04-19T03:19:28.608Z
updated: 2026-04-19T03:19:28.608Z
sources: []
links: []
category: session-log
confidence: medium
schemaVersion: 1
---

# 2026-04-19 - pm24 8 new rc implemented: 6 pass 2 drop

# pm24 — 8 new rc implementation + 40-game HTH battery

**Date**: 2026-04-19 pm24
**Focus**: Implement Tier 1/2 round-robin candidates while server Order 4 runs (18h ETA)
**Duration**: ~2.5h Mac work

## Activities

Server state at pm24 start:
- Order 3 completed at pm23 end, best_ever 0.855. A1 kept as champion (baseline 79%).
- Order 4 launched pm23 autopilot: master-seed=2026, init=a1, HOF pool=A1+O2+O3. 18 evolve processes, Phase 2a gen 0 in progress.
- Autopilot session cron `fc249310` expired → 재생성 안 함 (pm24 이번엔 fully-synchronous Mac 작업만 할 예정).

Mac work: implement 8 new round-robin candidates in 2 batches of 5+3.

### Batch A (5 new rc, launched first)

1. **rc28** Boids swarm cohesion — anti-clump top-K filter when no invader visible and teammates close (maze-dist ≤ 4).
2. **rc29** Search-depth disruption — REVERSE action injection when (a) last 3 actions same direction and (b) ghost at maze-dist ≤ 4 while we're Pacman. Breaks minimax herding pattern.
3. **rc31** Kiting / aggro-juggling — distance-2 hold against single invader, when I'm unscared ghost and teammate not better-positioned.
4. **rc44** Stacking meta-policy — state-class-conditioned weighted vote over (A1, rc02, rc16, rc32). 4 classes: offense_carry / defense_rush / endgame / normal. Per-class hand-tuned weights anchored on pm23 WR.
5. **rc50** Opening book — 15-turn role-conditioned approach target precomputed at init. OFFENSE → food furthest from opp avg home col. DEFENSE → AP closest to our food centroid.

### Batch B (3 new rc, launched after Batch A)

6. **rc30** Particle-filter blinding — randomized top-K selection every 5 turns when we're outside all opponents' 5-cell sight.
7. **rc34** Pavlovian feinting — pick 2nd-best (within A1 tolerance) every 7 turns regardless of context.
8. **rc48** WHCA* / reservation-table — 1-step teammate cell projection; filter my top-K to avoid landing on teammate's projected cell.

All smokes: import OK, 1-game as Red OK. Full 40-game HTH (20 Red + 20 Blue vs baseline) ran in parallel batches of 10.

## Results — 40-game HTH vs baseline

| Agent | Red | Blue | Total | WR | Verdict |
|---|---|---|---|---|---|
| **rc29** Search-depth disruption | 20/20 | 17/20 | 37/40 | **92.5%** | ✅ PASS |
| **rc44** State-conditioned stacking | 19/20 | 18/20 | 37/40 | **92.5%** | ✅ PASS |
| **rc48** WHCA* teammate deconflict | 19/20 | 17/20 | 36/40 | **90%** | ✅ PASS |
| **rc50** Opening book (15-turn) | 18/20 | 18/20 | 36/40 | **90%** | ✅ PASS |
| **rc31** Kiting / aggro-juggling | 17/20 | 18/20 | 35/40 | **87.5%** | ✅ PASS |
| **rc28** Boids anti-clump | 14/20 | 19/20 | 33/40 | **82.5%** | ✅ PASS (ties A1) |
| **rc30** Particle-filter blinding | 8/20 | 2/20 | 10/40 | **25%** | ❌ DROP |
| **rc34** Pavlovian feinting | 0/20 | 0/20 | 0/40 | **0%** | ❌ DROP |

A1 baseline (pm20 reference) = 82.5% WR.

## Observations

- **rc29 and rc44 tie for highest pm24 gain at 92.5%.** rc29 is narrow (fires only when herded), rc44 is broad (state-conditioned vote). Both exceed A1 by +10pp.
- **rc44 stacking meta confirms state-conditioned weighting > flat voting.** rc45 did flat-weighted voting at 92.5% too — parity suggests stacking's ceiling isn't obviously higher without more sophisticated meta-learning. But rc44 would likely outperform rc45 against diverse opponents (different state class distributions).
- **rc50 opening-book is surprising — A1 alone doesn't have myopic opening issues? Or the 15-turn nudge is orthogonal?** 90% vs 82.5% is meaningful. Opening target BFS from init position puts both agents in "better" starting corridors even if they'd get there eventually.
- **rc48 WHCA* coordination helps +7.5pp over A1.** Simple 1-step mate-cell projection (no full MAPF). Suggests A1's reflex has measurable teammate collisions.
- **rc31 kiting modest gain +5pp — distance-2 hold is defensible but timing-sensitive.** A1's f_invaderDist already handles most defense.
- **rc28 Boids ties A1 at 82.5% — anti-clump provides no lift on defaultCapture.** A1's f_teammateSpread (added in pm18 B1) already covers this. Keep anyway for diversity against other opponents in Phase 4.

## Decisions

- **6 rc added to Phase 4 round-robin pool** (rc28/29/31/44/48/50).
- **rc30 and rc34 DROPPED from pool** due to 0% and 25% WR. Files retained for report ablation (stochastic top-K counter-example).
- **Key learning**: random / periodic top-K injection != free lunch. The extra-move latency from picking 2nd-best is negligible, but at critical food-return or ghost-kill moments, sub-optimal choices lose whole games. Contrast rc29 (targeted REVERSE only when threat visible, preserves argmax 95% of turns) which gained +10pp.
- **Implication for future rc**: stochastic overlays must be *threat-conditioned*, never *time-conditioned* only.
- **Not implemented this session**: rc10, rc12-14 (minimax-specific, not applicable to reflex), rc20-27, rc31-50 (≥1-day effort), Tier 3/4 (multi-day).

## Open items

- Server Order 4 still running (ETA ~2026-04-20 ~06:00 KST, 18h wall).
- Phase 4 tournament setup deferred to pm25 (after Order 4 HTH lands).
- M7 flatten_agent AST work deferred (champion identity may change if Order 4 produces stronger weights than A1).

## Next-session priority (pm25)

1. **Server poll**: `ssh jdl_wsl "tmux capture-pane -t work -p -S -30 | tail -20 && pgrep -af evolve.py | wc -l"`.
2. If Order 4 done: archive to `experiments/artifacts/phase2_A4_*`, run HTH battery, compare to A1 (baseline ≥79% Wilson LB > 0.728 required).
3. If Order 4 still running: start Phase 4 round-robin tournament spec on Mac — generate tournament CSV with 23 rc + A1/O2/O3 + D-series (~29 agents, ~840 matches at 2 seeds × defaultCapture+RANDOM).
4. M7 flatten_agent AST implementation for the submission candidate (likely A1 or rc29 or rc44).

## Files touched pm24

**Created** (8 new agent files):
- `minicontest/zoo_reflex_rc28.py`
- `minicontest/zoo_reflex_rc29.py`
- `minicontest/zoo_reflex_rc30.py` (DROP)
- `minicontest/zoo_reflex_rc31.py`
- `minicontest/zoo_reflex_rc34.py` (DROP)
- `minicontest/zoo_reflex_rc44.py`
- `minicontest/zoo_reflex_rc48.py`
- `minicontest/zoo_reflex_rc50.py`

**Updated**:
- `.omc/plans/rc-pool.md` (Batch A + B change log entry)
- `.omc/STATUS.md` (pm24 headline + milestone table)
- `.omc/SESSION_RESUME.md` (pm25 TL;DR)

**Not touched**: submission-target files (`your_best.py`, `your_baseline{1,2,3}.py`) → no `docs/AI_USAGE.md` entry required this session.

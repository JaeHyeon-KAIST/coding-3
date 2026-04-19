---
title: "2026-04-19 pm26 — rc52b + rc46/141/142 adaptive sprint"
tags: ["pm26", "rc52b", "rc46", "rc141", "rc142", "reinforce", "opponent-classifier", "asymmetric", "tier-3"]
created: 2026-04-19T09:25:26.045Z
updated: 2026-04-19T09:25:26.045Z
sources: []
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-19 pm26 — rc52b + rc46/141/142 adaptive sprint

# pm26 session log — rc52b + rc46/141/142 adaptive sprint

**Date**: 2026-04-19
**Focus**: Continue rc pipeline after pm25 Tier 3 sprint. User directive "rc 더 진행해" + "성능 우선으로 알아서 판단해서 진행". 4 new rc shipped, 1 new learning-tier peak.

## Activities

1. **Investigated untracked `experiments/rc52b_final_weights.py`** (stats: iter 30/300g, cum_wr 67.7% vs rc52's 57.3%). Concluded it's an orphan from a prior REINFORCE training run — same spec as rc52 but different stochastic path. Built agent wrapper `zoo_reflex_rc52b.py` and ran 100-game HTH via `hth_battery.py --weights experiments/rc52b_final_weights.py`. Result: **92/100 = 92%** Wilson [0.850, 0.959] — beats rc52 (90%) by 2pp and becomes the new learning-tier peak.

2. **Tested pre-existing `zoo_reflex_rc46.py`** (K-centroid 4-archetype classifier from an earlier session). Protocol: Red 50g + Blue 50g vs baseline. Result: Red 48/50 + Blue 43/50 = **91/100 = 91%** Wilson [0.838, 0.952]. +5pp over A1 solo 86%.

3. **Built `zoo_reflex_rc141.py`** = rc52b OFF + rc82 DEF asymmetric (replicating rc140's pattern with the stronger rc52b variant). Result: 47+43 = **90/100 = 90%** Wilson [0.826, 0.945] — **BELOW** rc52b solo 92%. Confirms rc140's lesson: linear-Q learned offense doesn't stack with rc82 DEF.

4. **Built `zoo_reflex_rc142.py`** = rc46 classifier OFF + rc82 DEF asymmetric. First hybrid of opponent-classifier with composite defense. Result: 48+43 = **91/100 = 91%** — same as rc46 solo. Composite DEF again failed to lift it.

## Observations

- **Pattern confirmed**: "learning/classifier OFF + rc82 DEF" ≈ OFF-solo. The 100% champions (rc82/105/109/116/123/131) require COMPOSITE offenses (rc16 Voronoi / rc32 Pincer). Learning-based linear-Q (rc52/rc52b) and adaptive classifier (rc46) break the multiplicative pattern. Possible cause: rc82 DEF presumes an OFFENSE that maintains A1's decision structure; learned weights shift that structure enough that composite DEF rules don't compose cleanly.
- **REINFORCE training variance ≈ 2pp** (rc52: 90%, rc52b: 92% from different training runs on same spec). A random-seed sweep over training could eke out 1-3pp more on the top end.
- **Classifier + A1 base gives a clean +5pp** (rc46 vs A1 solo) with zero training overhead. Cheap win, valuable for tournament diversity.

## Decisions

- **Keep all 4 new rc for Phase 4 pool**: rc52b (learning peak), rc46 (adaptive), rc141/142 (asymmetric variants). Pool size now ~80 agents.
- **Do NOT upgrade submission candidate**: 100% champions (rc82/105/109/116/123/131) still dominate. pm26 rc all at 90-92%.
- **Phase 4 tournament timing**: still blocked on server Order 4 completion. Server unreachable today (SSH timeout) — retry next session.
- **Pattern abandon**: "learning OFF + rc82 DEF" is dead-end. Future asymmetric rc should pair composites with composites.

## Open items

- Server Order 4 status unknown (SSH timed out). Next session: retry + HTH battery vs baseline if finished.
- rc22-v3 feature extension (34-dim history+AP+phase) not attempted — pm25 found rc22-v2 gave no game-WR lift despite val_acc improvement. Probably diminishing returns.
- rc53 CMA-ES, rc61 AlphaZero-lite, rc70 MuZero-lite still in Tier 3 backlog.

## Next-session priority

1. Retry SSH → server Order 4 status. HTH battery if done.
2. If pool is stable (no new Order 4 champion), run Phase 4 tournament (~75 agents × 5 layouts × 5 seeds) on server.
3. M7 flatten_agent skeleton (AST concatenation) needed before M8 submission.
4. (Stretch) rc22-v3 or rc53 if time permits before Phase 4.

## Files touched

- `minicontest/zoo_reflex_rc52b.py` (new)
- `minicontest/zoo_reflex_rc141.py` (new)
- `minicontest/zoo_reflex_rc142.py` (new)
- `experiments/rc52b_final_weights.py` (track previously-untracked)
- `.omc/plans/rc-pool.md` (+4 pm26 entries)
- `.omc/STATUS.md` (pm26 headline update)

No submission-target files (`your_best.py`, `your_baseline1-3.py`) were edited this session — `docs/AI_USAGE.md` unchanged per convention.


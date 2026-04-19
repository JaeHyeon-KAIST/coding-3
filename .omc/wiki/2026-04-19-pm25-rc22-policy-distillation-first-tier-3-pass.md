---
title: "2026-04-19 pm25 - rc22 Policy Distillation FIRST Tier 3 pass"
tags: ["rc22", "policy-distillation", "pm25", "tier3", "learning-based", "numpy-mlp", "knowledge-distillation", "phase4-pool"]
created: 2026-04-19T07:43:02.446Z
updated: 2026-04-19T07:43:02.446Z
sources: ["experiments/artifacts/rc22/hth_100game.csv", "experiments/artifacts/rc22/weights.npz", "experiments/distill_rc22.py", "minicontest/zoo_distill_collector.py", "minicontest/zoo_distill_rc22.py"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-19 pm25 - rc22 Policy Distillation FIRST Tier 3 pass

# 2026-04-19 pm25 — rc22 Policy Distillation (FIRST Tier 3 learning-based rc)

## Focus

Implement rc22 Policy Distillation as the first learning-based rc. Teacher = rc82 (100% champion from pm24). Student = small numpy MLP satisfying the submission constraint (numpy + pandas only).

## Activities

1. **Designed pipeline** — 3-file split:
   - `experiments/distill_rc22.py` — orchestrator (collect/train/export) with `collect`/`train`/`both` subcommands.
   - `minicontest/zoo_distill_collector.py` — teacher wrapper subclassing `ReflexRC82Agent`, logs per-turn `(legal[], feats[L,20], chosen)` to JSONL via `RC22_LOG_PATH` env var.
   - `minicontest/zoo_distill_rc22.py` — student inference agent, numpy forward pass only, loads weights from `RC22_WEIGHTS` env var or default path.

2. **Architecture decision: per-action Q-scoring with softmax-CE supervision**:
   - Input: φ(s,a) 20-dim per legal action (reuse `zoo_features.extract_features`).
   - MLP: 20 → 32 → 1 scalar. ~2K parameters total.
   - Training: for each turn, forward each legal action, softmax over scores, CE loss with teacher's chosen action index.
   - Inference: argmax over legal Q-scores.

3. **Smoke (20 games, 40 epochs)**:
   - 11,667 records, train_acc 91%, val_acc 91%.
   - HTH 40-game: 19/40 = 47.5% (marginal fail).

4. **Scale-up (100 games, 50 epochs)**:
   - 59,828 records, train_acc 90.9%, val_acc 90.3% (**plateau — information bottleneck**).
   - Teacher WR in collection = 96/100 = 96% (baseline confirmed).

5. **Debugged env var bug**: `RC22_WEIGHTS` with relative path failed because `single_game.py` changes cwd to `minicontest/`. Fix: use absolute path. Exposed by a spurious 0/40 result that looked like total failure but was actually weights never loading → `_safeFallback` (random legal action).

6. **Final 100-game HTH**: **88/100 = 88.0%** Wilson [0.802, 0.930], 0 crashes. Clears 51% grading gate by wide margin (LB 80.2%).

## Observations

1. **Information-bottleneck confirmed**: val_acc plateaus at ~91% regardless of data size (20 vs 100 games). rc82 uses history (3-step REVERSE trigger) + internal state (Tarjan AP graph from rc02 sub-policy, Voronoi territory from rc16, state-class from rc44) that 20-dim φ(s,a) can't recover.

2. **Action-accuracy vs game-WR gap is SMALLER than expected**: 9% action-error compounded over ~300 turns suggested game WR ~55-65%. Observed 88%. Reason: rc22 doesn't need to match teacher every turn — most "errors" are between similarly-valued actions (tie-breaks), and the high-signal moments (ghost-avoidance, food-grab, return-home) are well-captured by the features rc22 does see.

3. **40-game HTH has high variance**: two successive 40-game runs gave 26/40 (65%) and 33/40 (82.5%) on the SAME weights. 100-game was needed for a tight CI. Lesson: **use ≥100 games for authoritative Tier 3 HTH measurement**, not pm23/pm24's 40-game convention (which is fine for hand-rule but not for noisier learning agents).

4. **CPU-only is sufficient**: Earlier question "rc22 is CPU or GPU?" — for a 2K-param MLP on 60K examples, numpy SGD on Mac CPU trains in ~15 seconds. No GPU needed.

5. **Data collection dominated wall time**: 100 games × ~3.4s/game = 340s data collection; 50 epochs × ~0.3s = 15s training. 95% of the pipeline is Pacman game simulation, not ML.

## Decisions

- **rc22 ACCEPTED to Phase 4 pool at 88%.** First architecturally different member (neural vs hand-rule); adds tournament diversity.
- **Default weights**: installed as `experiments/artifacts/rc22/weights.npz` so student agent loads them without env var.
- **No feature extension** for this iteration — 88% is strong enough, and adding history/AP features for another 5-10pp gain costs ~30-45 min engineering. Moving to next rc instead (per "성능 위주" directive = decide by performance, move fast).
- **Do NOT promote rc22 to `your_best.py` submission candidate** — 8 pm24 champions at 100% are still better individually. rc22's value is diversity, not peak.

## Open items

- **AI_USAGE.md logging** — rc22 dev files are not in the submission-target set (your_best/baseline1-3), so strict policy doesn't require logging. But if rc22 is later promoted or flattened into `your_baseline*.py`, the log is needed. DEFERRED until promotion decision.
- **Feature extension** for potential rc22-v2 — add last-3-action one-hot (5-way × 3 = 15 dims) + current-pos AP flag + game phase bucket (4-way) → 34-dim student. Expected lift: val_acc 91% → 94%+, WR 88% → 92%+. Stretch for pm26 if time permits.

## Next-session priority

1. **Order 4 check** — server Phase 2a gen 3 at best=0.712; expect completion ~2026-04-20 evening. If A4 beats A1 (baseline 79%), adds O4 champion to pool.
2. **Choose next Tier 3 rc** — options:
   - rc52 Q-learning v3 (replay buffer + SGD) — 2d, harder but real RL
   - rc46 Opponent-type classifier (counter-policy switch) — 1-2d, novel
   - rc61 AlphaZero-lite — 5d, highest ceiling, highest risk
3. **Or pivot to Phase 4 prep + M7 flatten** — lock 8 pm24 champions + rc22 as submission candidates, prep round-robin tournament infra for when Order 4 finishes.

Recommendation: run Phase 4 prep + M7 flatten in parallel with next Tier 3 rc. Don't chase diminishing returns on distillation (rc22-v2).

---
title: "2026-04-19 pm25 - FULL Tier 3 sprint (4 rc's) + REINFORCE honesty correction"
tags: ["pm25", "tier3", "rc22", "rc52", "rc140", "distillation", "reinforce", "policy-gradient", "temperature-softmax", "debugging", "honest-correction", "learning-based-rc"]
created: 2026-04-19T08:44:39.749Z
updated: 2026-04-19T08:44:39.749Z
sources: ["experiments/train_rc52.py", "experiments/distill_rc22.py", "minicontest/zoo_rc52_trainer.py", "minicontest/zoo_reflex_rc52.py", "minicontest/zoo_distill_rc22.py", "minicontest/zoo_distill_rc22_v2.py", "minicontest/zoo_reflex_rc140.py", "experiments/rc52_final_weights.py", "experiments/artifacts/rc22/hth_100game.csv", "experiments/artifacts/rc52c/hth.csv"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-19 pm25 - FULL Tier 3 sprint (4 rc's) + REINFORCE honesty correction

# 2026-04-19 pm25 — Full Tier 3 sprint + REINFORCE honesty lesson

## Focus

Ship multiple Tier 3 learning-based rc's (first beyond pm24's hand-rule composites). Performance priority, autopilot mode.

## Activities (chronological)

1. **rc22 Policy Distillation v1** (100 games, numpy MLP 20→32→1 from rc82 teacher)
   - Data: 100 games rc82 vs baseline, 59,828 records. Teacher WR 96%.
   - Training: 50 epochs, lr=1e-3. val_acc 90.3%.
   - HTH: **88/100 = 88%** Wilson [0.802, 0.930]. First Tier 3 PASS.
   - Commit: `7dfff1b`.

2. **rc22-v2 Extended-feature distillation** (20 + 15 history + 1 AP + 3 phase = 39 dims)
   - Hypothesis: info-bottleneck at 91% val_acc caused by missing history/state info.
   - Training: 100 games, hidden=48. val_acc 93.7% (+3.4pp).
   - HTH: **85/100 = 85%** Wilson [0.767, 0.907]. Statistically tied with v1.
   - Lesson: **higher action-level accuracy ≠ higher game-WR**. Tighter teacher mimicking can inherit teacher mistakes; slight deviation can regularize. Plateau confirmed.
   - Commit: `ba6f64d`.

3. **rc52 REINFORCE v1 (FIRST attempt, LATER RETRACTED)**
   - Algorithm: linear REINFORCE on 20-dim φ(s,a), π=softmax(Q) over legal.
   - 150 games, lr=1e-4, A1 init.
   - HTH: 95/100 = 95% Wilson [0.888, 0.978] — claimed "NEW CHAMPION TIER".
   - Commit: `fd647a1`.

4. **rc140 rc52-OFF + rc82-DEF asymmetric** (pm24 "X + rc82 DEF = 100%" pattern)
   - HTH: 91/100 = 91% Wilson [0.838, 0.952].
   - Commit: `26a8ed3`.

5. **rc52b retry with 5× lr** (tried to push rc52 higher)
   - 30 iters × 10 games, lr=5e-4.
   - HTH check later — revealed weights BARELY MOVED.

6. **CRITICAL DEBUGGING** (post-rc52b): discovered rc52's weights were identical to A1 within 0.0003 delta. The 95% HTH was A1's actual Mac 100g WR (variance around 86% authoritative A1 Mac baseline).
   - Root causes:
     - A1's confident policy: softmax(Q) near-deterministic → ∇log π(a|s) ≈ 0.
     - Update averaging by per-step count (~2800) → effective lr 3.6×10⁻⁸.

7. **Training-loop fix** — temperature softmax + per-batch normalization:
   - `_softmax(z, T=5.0)` softens policy for gradient (lets gradient flow).
   - `w += updates_sum / num_games` (per-batch Monte Carlo step).
   - `--temperature` CLI flag.

8. **rc52c retrain (30 iters × 10 games, T=5, lr=1e-3)**
   - Weights moved: total delta 0.97, max f_stop -0.47 from A1.
   - HTH: **90/100 = 90%** Wilson [0.826, 0.945]. +4pp over A1's 86% (within CI overlap).
   - Honest: modest lift but NOT a new champion.

9. **Documentation correction** (commit `fd3c5ff`): rc-pool, STATUS, SESSION_RESUME all updated with honest numbers + debug note.

## Observations

1. **Policy gradient needs soft policy for learning signal**. If initialization is already a strong greedy policy, REINFORCE's gradient vanishes. Temperature scaling (T>1) during training is essential.

2. **A1's authoritative Mac 100g WR = 86%** Wilson [0.779, 0.915]. Previously reported 79% was server 340g (pm19 HTH battery). Different venues give different numbers — the pm24 rc-pool's "A1 82.5%" is in the same ballpark.

3. **100-game HTH has ±8-10pp CI width**. Claims like "95%" need context: same weights re-run can easily land 85-95% due to game variance on defaultCapture (not PRNG-seeded). Multiple 100g samples or 500+ game battery needed for decisive comparisons.

4. **Distillation plateau**: rc22 v1 (20-dim, 88%) and v2 (39-dim, 85%) are statistically equivalent. More features improve action-level accuracy (91→94%) but game-WR is bounded by teacher's decision pattern + student architectural limits. Further iteration not worth it.

5. **Composite pattern (pm24 "X + rc82 DEF = 100%") doesn't always generalize**. rc140 (learned rc52 OFF + rc82 DEF) hit 91%, below the hand-rule composites at 100%. Hypothesis: learned weights are already tuned for both roles; separating them creates role mismatch.

## Decisions

- **Keep rc22 (88%), rc22-v2 (85%), rc52 (90%), rc140 (91%)** as Phase 4 pool members — architectural diversity.
- **DO NOT promote any pm25 rc to `your_best.py` submission.** The 8 pm24 composites at 100% remain the submission candidates.
- **Fix learning loop** (temperature + per-batch norm) committed as reference implementation. Future RL-style rc's (rc61 AlphaZero-lite, rc62 Distributional, etc.) can build on this.
- **pm25 lesson documented in wiki** for future self / learners: "REINFORCE on a confident policy requires temperature softening to produce non-zero gradient".

## Open items

- **A1 vs rc52 CI overlap** — 100g each is not decisive. 500g battery would distinguish. Not worth the time (both are ~88% single-agent tier, not champion tier).
- **rc140 retest with properly-trained rc52**. Current rc140 number used A1-rebranded rc52; new rc52 weights have moved ~0.97. Might shift rc140 slightly. Defer.
- **Autopilot mode** remained on throughout this session. Worked well for rapid iteration; the "ship, verify, document, commit, next" loop is reproducible.

## Next-session priority (pm26)

1. **Server Order 4 finish monitoring** (~20h ETA from pm25 end). Phase 2a gen 3/10 best=0.712 trending toward A1's 1.065. Likely minor lift.

2. **Pivot to Phase 4 infrastructure** (M7 flatten + M8 output.csv + round-robin tournament setup). Locking submission 40pt code score is higher EV than more Tier 3 rc's at this point.

3. **Optional stretch** (if time permits):
   - rc62 Distributional RL (research-grade, 3d)
   - rc38 MAP-Elites (quality-diversity, 2d)
   - rc46 Opponent-type classifier (adaptation for tournament, 1-2d)
   - rc52 with aggressive training (higher T, more iters) — might break into mid-90s

4. **NOT worth revisiting**: rc22-v3 (feature engineering) — plateau confirmed.

## Final pm25 summary

- **Commits**: 6 total in pm25 (7dfff1b rc22, ba6f64d rc22-v2, fd647a1 rc52-wrong, 26a8ed3 rc140, fd3c5ff rc52-correction).
- **Files added**: 7 agents + 1 training script + 1 flat weights file.
- **Lines of code**: ~1,500 Python.
- **Training runs**: 5 (20g rc22 smoke, 100g rc22 full, 100g rc22-v2, 150g rc52, 300g rc52c, 300g rc52b).
- **HTH battery runs**: 7 (rc22 40g+100g, rc22-v2 100g, rc52 initial 100g, rc140 100g, A1 100g, rc52c 100g).
- **Autopilot mode**: invoked mid-session for autonomous shipping.
- **Key insight**: REINFORCE needs temperature softening on confident policies.

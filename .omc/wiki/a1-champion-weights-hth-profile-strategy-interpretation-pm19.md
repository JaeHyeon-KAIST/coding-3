---
title: "A1 champion weights HTH profile + strategy interpretation (pm19)"
tags: ["A1", "champion", "weights-analysis", "CEM", "HTH", "pm19", "17-dim", "fitness-1.065", "baseline-79"]
created: 2026-04-17T03:48:37.467Z
updated: 2026-04-17T03:48:37.467Z
sources: ["experiments/artifacts/phase2_A1_17dim/final_weights.py", "hth_A1_17dim.csv", "2b_gen013 best", "Codex+Gemini advisors pm19"]
links: []
category: reference
confidence: high
schemaVersion: 1
---

# A1 champion weights HTH profile + strategy interpretation (pm19)

# A1 champion — weights, HTH profile, and strategy interpretation

## Identity

- **Container**: `zoo_reflex_tuned` (pure reflex agent) with CEM-evolved weight override.
- **Genome dim**: 17 features + 12 PARAMS (PARAMS are dead dims — reflex container ignores them).
- **Provenance**: Phase 2b gen 13 best-ever (fitness 1.065); preserved via elitism into final_weights.py emission.
- **Phase 2a gens**: 10 (shared W_OFF=W_DEF); Phase 2b gens: 20 (split W_OFF ≠ W_DEF).
- **Pool**: `baseline×2 + zoo_reflex_{h1test,h1b,h1c,aggressive,defensive} + zoo_minimax_{ab_d2,ab_d3_opp} + zoo_expectimax + monster_rule_expert` (11-opp, no MCTS due to 120s run_match timeout).
- **Training wall**: 18.5h on Ryzen 7950X (16 workers).

## Evolved W_OFF (offensive role)

```python
W_OFF = {
    'f_bias':                -10.02,   # (seed 0)
    'f_successorScore':      108.97,   # (seed 100)
    'f_distToFood':           34.14,   # (seed 10)  — 3.4× seed, aggressive food-seeking
    'f_distToCapsule':        48.36,   # (seed 8)   — 6× seed, capsule magnet
    'f_numCarrying':         -30.10,   # (seed 5)   — NEGATIVE: disincentive to hoard
    'f_distToHome':           13.85,   # (seed 4)   — 3.5× seed
    'f_ghostDist1':          -28.65,   # (seed -50) — less ghost-fearful
    'f_ghostDist2':          -25.99,   # (seed -10)
    'f_inDeadEnd':           -230.89,  # (seed -200)
    'f_stop':                -143.25,  # (seed -100)
    'f_reverse':              -29.44,  # (seed -2)
    'f_numInvaders':          -61.89,  # (seed -1000) — MUCH weaker defense signal
    'f_invaderDist':          27.36,   # (seed 30)
    'f_onDefense':            -7.79,   # (seed 100)  — NEGATIVE: wants to be offensive
    'f_patrolDist':           11.41,   # (seed 5)
    'f_distToCapsuleDefend':  1.55,    # (seed -3)
    'f_scaredFlee':           5.15,    # (seed -1)   — positive: chases scared ghosts
}
```

## Evolved W_DEF (defensive role)

```python
W_DEF = {
    'f_bias':                 9.25,
    'f_successorScore':      104.99,
    'f_distToFood':           31.76,
    'f_distToCapsule':        36.52,
    'f_numCarrying':         -38.31,   # even more negative than W_OFF
    'f_distToHome':           19.06,
    'f_ghostDist1':          -30.70,
    'f_ghostDist2':          -15.60,
    'f_inDeadEnd':           -222.62,
    'f_stop':                -137.18,
    'f_reverse':              -37.51,
    'f_numInvaders':          -47.23,
    'f_invaderDist':          45.00,
    'f_onDefense':            -12.12,  # NEGATIVE: defender also wants to attack!
    'f_patrolDist':            6.95,
    'f_distToCapsuleDefend':  -9.09,
    'f_scaredFlee':           14.32,   # very positive
}
```

W_DEF is NOT a defensive specialist — it's an offensively-tilted variant of W_OFF with stronger capsule interception (`f_distToCapsuleDefend = -9.09`) and stronger invader pursuit (`f_invaderDist = 45`). Evolution discovered that even the "defensive" teammate should raid.

## HTH profile (pm19 340-game battery, 30s server wall, 0 crashes)

| Opponent | wins/total | WR | Wilson 95% CI | Verdict |
|---|---|---|---|---|
| `baseline.py` | 158/200 | **79.0%** | [0.728, 0.841] | **PASS** (51% grading gate + 22pt margin) |
| `monster_rule_expert` (territorial defender) | 46/60 | 76.7% | [0.646, 0.856] | patient-defender survivable |
| `zoo_reflex_h1test` (CEM seed) | 37/40 | **92.5%** | [0.801, 0.974] | CEM demonstrably improved over seed |
| `zoo_minimax_ab_d2` (search-based opp) | 33/40 | 82.5% | [0.680, 0.913] | search-opp survivable |

Layouts: `defaultCapture + RANDOM` (per-seed layouts). 2 colors each.

## Strategy interpretation — "1-food sprint-home raid"

The evolved weights encode a coherent strategy that both advisors (Codex, Gemini) initially predicted would fail:

1. **Aggressive scavenger**: `f_distToFood = 34` + `f_distToCapsule = 48` drive the agent toward the nearest food/capsule as the dominant signal.
2. **Non-hoarder**: `f_numCarrying = -30` actively penalizes carrying multiple foods. Combined with `f_distToHome = 14`, agent returns home after **1 food** (!), depositing quickly then re-raiding.
3. **No real defender**: both W_OFF and W_DEF have `f_onDefense < 0` and weakened `f_numInvaders` (seed -1000 → -62). Agent rarely stays on home side.
4. **Dead-end avoidance strong**: `f_inDeadEnd = -231` stronger than seed's -200.
5. **Capsule-triggered aggression**: `f_scaredFlee = +5.15` (both roles positive) — when ghosts become scared via our capsule, agent CHASES them (worth points + clears path).

Gemini predicted this would starve against a "patient defender". **It doesn't** — beats `monster_rule_expert` 76.7%. Why?
- `monster_rule_expert` patrols home territory; A1's 1-food strategy means each raid is fast (~20-30 moves), so even if defender intercepts once, A1 re-raids multiple times per 1200-move game.
- Net: A1 scores several foods before defender's intercept count can match.

## Behavioral signature to watch for

On gameplay trace (if recording moves):
- Agent crosses midline → grabs nearest food → immediately reverses direction
- If capsule nearby, agent deviates to capsule regardless of food seeking
- After capsule eaten: agent pursues scared ghost for bonus points
- Teammate behaves similarly (W_DEF also offensively-tilted) → both raiding → food deposit pace high
- Home-side defense is minimal — exposure to slow/occasional invader is acceptable

## Lessons for report (M9)

- **Non-intuitive weights as discovery narrative**: "Why my agent is a pair of greedy raiders instead of one attacker + one defender" → strong Methods + Results story
- **Overfit-prediction failure mode**: 3 independent advisors (Claude, Codex, Gemini) predicted overfit vs patient-defender; HTH disproved. Use as concrete "lesson about intuition vs empirical validation" in Conclusion.
- **f_numCarrying < 0 ablation**: If time permits, a quick 50-game run with that feature forced to 0 (or seed value 5) would show the counterfactual — baseline WR likely drops.

## Caveat — cross-platform unverified

A1 weights were evolved on server; **Mac replay never tested**. STRATEGY §6.5 warns cross-platform reproducibility imperfect. Before final submission, run Mac HTH of flattened `20200492.py` vs `baseline.py` (100+ games) to confirm weights transfer cleanly.


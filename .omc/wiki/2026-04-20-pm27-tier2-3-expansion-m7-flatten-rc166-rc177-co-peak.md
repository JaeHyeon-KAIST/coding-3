---
title: "2026-04-20 pm27 Tier2/3 expansion + M7 flatten + rc166/rc177 co-peak"
tags: ["pm27", "tier2", "tier3", "rc166", "rc177", "rc47", "rc49", "flatten", "M7", "head-to-head", "threshold-sweep"]
created: 2026-04-20T04:46:52.932Z
updated: 2026-04-20T04:46:52.932Z
sources: ["minicontest/zoo_reflex_rc25.py", "minicontest/zoo_reflex_rc47.py", "minicontest/zoo_reflex_rc166.py", "minicontest/zoo_reflex_rc177.py", "experiments/flatten_multi.py"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-20 pm27 Tier2/3 expansion + M7 flatten + rc166/rc177 co-peak

# 2026-04-20 pm27 — Tier 2/3 expansion (11 new paradigms) + rc166/rc177 co-peak 98.5% + M7 flatten working

## Date / Focus
2026-04-20 pm27 (session following pm26 SWITCH breakthrough). Goal: expand Phase 4 round-robin pool via Tier 2/3 paradigms + unblock M7 flatten_agent (pending since pm14).

## Activities

### Phase 1 — Batch I (Switch axis exploration)

Hypothesis tests on axes other than score:

| rc | Switch axis | 100g WR | Verdict |
|---|---|---|---|
| rc168 | my_carry ≥ 6 → rc16 | 97% | ≈ rc160 |
| rc169 | timeleft < 200 → rc32 (endgame pincer) | 97% | ≈ rc160 |
| rc171 | rc160 + rc48 WHCA* overlay | 95% | -2.5pp regression |
| rc159 | 4-way rc82/rc16/A1/rc82 (200g re-val) | 98.0% | CI overlap rc160 |
| rc166 | rc82 if score ≥ 3 else rc16 (200g re-val) | **98.5%** | **NEW PEAK** |

### Phase 2 — Threshold sweep

| rc | Threshold | Game size | WR |
|---|---|---|---|
| rc160 | ≥ 1 | 200g | 97.5% [0.944, 0.990] |
| rc177 | ≥ 2 | 200g | **98.5% [0.957, 0.995]** |
| rc166 | ≥ 3 | 200g | **98.5% [0.957, 0.995]** |
| rc178 | ≥ 4 | 100g | 95% |
| rc179 | ≥ 5 | 100g | 98% |

Sweet spot ≥ 2-3. rc166 vs rc177 tied on point estimate but H2H shows rc166 STRICTLY better.

### Phase 3 — M7 flatten_agent unblock

`experiments/flatten_multi.py` written — recursive dep resolver:
- Parse target agent AST, collect `from zoo_* import ...` recursively
- Topological sort dependencies (deps before dependents)
- Strip ALL top-level imports + any nested `from zoo_* import ...` (but KEEP nested stdlib imports like `import importlib.util` inside function bodies — a critical bug fix)
- Strip `SEED_WEIGHTS_{OFFENSIVE,DEFENSIVE}` from zoo_features.py, inject evolved weights
- Emit compat alias `_base_extract_features = extract_features` for stripped `as`-aliased imports
- Write single-file standalone module with proper createTeam

Verified on rc166 (8-module dep chain: tuned → A1 → rc02/rc16/rc32/rc44 → rc82 → rc166):
- 2205-line output, `ast.parse` OK
- Smoke 4/4 PASS
- 100g HTH: 98/100 (98%) vs original 98.5%/200g → parity confirmed (within CI)

### Phase 4 — Tier 2 paradigms (6 new)

**rc25 Quiescence Search** — αβ d4 + quiescence +2 at volatile positions (ghost/invader within 2-4 cells). First attempt at depth 2 gave 0/4 (tie-deadlock); upping to d4 → 98%. Key: MUST use `_static_eval` (max over self's legal from state) not stale `leaf_eval(state, last_action)`.

**rc37 Novelty Search** — position anti-loop. Maintains deque(12) of visited cells, penalizes candidates landing on recently-visited cells by -8.0 per repeat. Fires UNCONDITIONALLY (vs rc82's rc29 REVERSE which only fires under ghost threat). 94% WR.

**rc38 MAP-Elites inference** — 12-niche archive (pacman, ghost_close, carry_band). Inverse-visit exploration bonus within each niche. 87%.

**rc41 SARSA 4-step** — self-only on-policy rollout using A1 reflex; γ=0.9 discount. No opponent simulation (avoids rc35 bug). 93%.

**rc47 Engine-grade αβ** — IDDFS depths [2,3,4] + history heuristic move ordering + transposition-implicit via pv-first reordering + fail-soft alpha-beta + time polling every 20 nodes. **Critical fix**: leaf eval must use pre-move state + candidate action, NOT post-move state + stale `last_action`. With A1 evolved weights: 99% 100g → 95% 200g authoritative [0.910, 0.974]. First non-composite 95%+.

**rc49 SIPP-lite** — 3-step teammate reservation (extends rc48's 1-step WHCA*). Teammate broadcasts last actions via class-level dict; projects next 3 cells assuming direction-continuation; my candidate actions penalized if they overlap mate's t=0 cell. 95%.

### Phase 5 — Tier 3 paradigms (5 new)

**rc58 Coord-Graph UCT lite** — A1 + pairwise teammate-spreading bonus (reward actions moving away from mate's projected next cell). 87%.

**rc59 Reward Machines** — FSM over 5 game stages (HUNT/COLLECT/RETURN/DEFEND/DESPERATE), multiplicative weight biases per stage. Different from rc19's full weight swap. 90%.

**rc60 Difference Rewards** — Aristocrat utility `D_i = U(me,mate) - U(null,mate)` approximation. Bias toward actions that differentiate from teammate's projected behavior. 90%.

**rc65 ToM L2** — rc82 composite + 2-ply adversarial robustness check over top-K. Opponent assumed to minimize MY utility with perfect info. 74% — adversarial framing too pessimistic, overrides rc82's good moves.

**rc75 MAML/Reptile lite** — layout-family detection at init (wall-density 5×5 around center), apply additive weight offsets for corridor vs open layouts. 90%.

### Phase 6 — Drops (7 total)

| rc | Paradigm | Cause |
|---|---|---|
| rc26 | MCTS-UCB1 bandit | Wall clock too slow (~40 min for 4g smoke at 0.3s budget) |
| rc35 | Rollout PI (feature eval) | Opponent simulation uses `evaluate(self, …)` biased to self's perspective → catastrophic |
| rc36 | Dyna-Q-lite (score delta) | Same rollout opp-model bug as rc35 |
| rc42 | Double-Q pessimistic min | 2/4 smoke — min(W_OFF, W_DEF) too conservative, kills offensive drive |
| rc43 | TD(λ) feature trace | 0/4 smoke — trace bonus overwhelms A1 base |
| rc67 | MCCFR-lite (bucketed RM+) | 0/4 smoke — stochastic sampling picks bad actions |
| rc185 | rc82 if score≥3 else rc47 | 0/4 smoke — paradigm switch breaks agent state continuity |

## Observations

### Critical H2H findings

1. **rc166 > rc177 H2H = 100-0-0 Red** despite IDENTICAL 200g baseline WR (both 98.5%). Every game score = 5 (deterministic outcome). rc166 (≥3 threshold) strictly better than rc177 (≥2 threshold) in head-to-head — interpretation: rc177 switches to rc82 earlier, which loses H2H to rc166's larger rc16-dominated zone.

2. **rc82 > rc166 H2H = 29-0-31 Blue** (0 Red wins). rc82 dominates rc166 in direct combat. **Baseline WR is NOT a tournament proxy**. rc166's switch pattern exploits baseline-specific weaknesses; rc82's pure composite generalizes better.

3. **rc47 vs rc166 = 60/60 Tie**. Engine αβ (search) + rc166 (reflex composite) mutually neutralize → all score=0 ties. Two strong agents find no path to score against each other.

4. **rc25 vs rc166 = 0-60-0 rc166 sweep**. Every game score = -1 (rc166 wins by exactly 1 food). Quiescence search couldn't break through rc166's territorial grip.

### Why Tier 3 ToM-L2 (rc65) regressed vs rc82 base

rc65 took rc82's top-K candidates and selected the one MOST robust to adversarial opponent response. But:
- rc82's action isn't always in top-K by A1 scoring (rc82 uses rc44 state-stacking which differs from pure argmax).
- Adversarial model assumes opponent uses MY evaluator + perfect info → overcautious.
- Real baseline doesn't play adversarially, so rc82's composite already handles the matchup optimally.

### Search paradigm insights

- **Depth matters**: rc25 at depth 2 → 0/4 tie (same as zoo_minimax_ab_d2 with seed weights). Upping to depth 4 → 98%. Shallow minimax tie-deadlocks.
- **Leaf eval semantics**: Must evaluate `(pre-move state, candidate action)` not `(post-move state, stale action)`. Silent bug caused rc47's first smoke to fail (2/4 with score 0-1 ties).
- **A1 evolved weights necessary**: Using `SEED_WEIGHTS_OFFENSIVE` (pre-evolution) at the leaf caused tie-deadlock. Import `_A1_OVERRIDE` from `zoo_reflex_A1` and use its `w_off`/`w_def` dicts.
- **Time budget tension**: 0.2s/turn × 1200 plies = 240s/game per agent. 200g × 2 agents = 133 min CPU. rc47 at 0.8s budget was 4+ hours just for 200g. Submission cap 1s/turn is workable but tight.

## Decisions

1. **rc166 = primary submission candidate** (baseline 40pt). 98.5% 200g cleanly beats 51% threshold.
2. **rc82 = tournament candidate** (if Phase 4 confirms H2H dominance).
3. **Phase 4 tournament** is next priority — pool expanded to ~40+ agents with pm27 additions. Dispatch to server.
4. **M7 unblocked** — `experiments/flatten_multi.py` is the canonical flatten tool; `experiments/flatten.py` stays for single-file cases.
5. Drop rc26/35/36/42/43/67/185 files kept in minicontest/ for audit trail (can be removed later if clutter becomes an issue).

## Open items

- Server Order 4 status unknown since pm26 evening (SSH timeout). Check first in pm28.
- `your_baseline{1,2,3}.py` still DummyAgent. Populate before M8 output.csv generation — candidates: rc47 (engine αβ), rc25 (quiescence), rc166 (switch composite).
- `.omc/plans/rc-pool.md` needs pm27 entries (11 new rc + threshold sweep + 7 drops).
- M9 ICML report skeleton not started.

## Next-session priority

1. Read this session log + `STATUS.md`.
2. Check Order 4 (`ssh jdl_wsl "pgrep -af evolve.py | wc -l"`).
3. Launch Phase 4 round-robin tournament on server with expanded pool (include rc47 + Tier 2/3 additions).
4. Based on Phase 4 ELO: flatten winner to `minicontest/20200492.py` using `experiments/flatten_multi.py`.
5. Populate `your_baseline{1,2,3}.py` with diverse champions for output.csv (M8).
6. Start M9 ICML report (Intro + Methods).


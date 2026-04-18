---
title: "2026-04-19 - pm23 rc02-rc08 Tier 1 candidate sprint"
tags: ["pm23", "rc-pool", "rc02", "rc03", "rc04", "rc05", "rc06", "rc08", "tarjan", "hungarian", "prospect-theory", "hth", "mac-development"]
created: 2026-04-18T19:25:09.150Z
updated: 2026-04-18T19:25:09.150Z
sources: []
links: []
category: session-log
confidence: medium
schemaVersion: 1
---

# 2026-04-19 - pm23 rc02-rc08 Tier 1 candidate sprint

# 2026-04-19 - pm23 rc02-rc08 Tier 1 candidate sprint

## Date
2026-04-19 pm23 (~04:00-05:00 KST)

## Focus
Mac-side implementation of rc02-rc08 Tier 1 hand-rule / assignment-based
overlays on the A1 champion. Goal: populate Phase 4 round-robin pool
with at least 5 new diverse candidates ahead of Phase 4 tournament.

## Activities

1. Verified pm22 server autopilot state (SSH retry after one initial
   timeout). Order 3 Phase 2b gen 7 running, best=0.788, best_ever=0.796
   from gen 6. ~13 gens × 2316s ≈ 8.4h to Order 3 complete. Re-armed
   `7,37 * * * *` cron for pm23 session.

2. Discovered rc01 (D-series) already fully implemented and committed in
   pm20 (commits 4e3baf7 / b3a94d1 / a42f6d0 / b9f0684 / 7e699c5 →
   `zoo_reflex_A1_{D1,D2,D3,D13,T4,T5}.py`). pm20 also ran 40-game HTH
   batteries: D13 is the strongest (92.5% baseline WR on hth_t4 csv).
   Updated rc-pool.md change log to mark rc01 DONE.

3. Implemented 6 new A1 overlay agents:
   - **rc02** `zoo_reflex_rc02.py` — Tarjan's iterative AP DFS + defense
     override that occupies the AP cutting invader from our food.
   - **rc03** `zoo_reflex_rc03.py` — leveraged existing `self.deadEnds`
     chain to build chain→neck mapping; ghost-mode trap at the neck when
     invader is inside the chain.
   - **rc04 v2** `zoo_reflex_rc04.py` — Hungarian-style dogpile breaker.
     v1 applied the override every turn and LOST 0/4 (top-K re-ranking
     too aggressive). v2 fires only when BOTH offense agents share
     greedy-nearest, and only re-ranks within a tight A1-score tolerance
     band. v2 wins 35/40.
   - **rc05** `zoo_reflex_rc05.py` — Prospect-theory `exp(α · carry)` risk
     scaling; amplifies ghost fear + return urgency, damps food greed.
   - **rc06** `zoo_reflex_rc06.py` — Early-game (timeleft > 900) border-
     food priority; re-ranks A1 top-K toward enemy food closest to our
     home frontier.
   - **rc08** `zoo_reflex_rc08.py` — 2×2 min-cost invader assignment;
     intervenes only when greedy-nearest would double-cover one invader.
   - rc07 (kamikaze) deferred — high coordination risk.

4. 40-game HTH smoke (20 Red + 20 Blue) vs baseline:

   | Agent | Red 20 | Blue 20 | Total | WR |
   |---|---|---|---|---|
   | rc02 Tarjan AP | 20/20 | 20/20 | **40/40** | **100%** |
   | rc03 Dead-end trap | 20/20 | 18/20 | 38/40 | 95% |
   | rc04 v2 Hungarian | 19/20 | 16/20 | 35/40 | 87.5% |
   | rc05 Prospect-theory | 18/20 | 15/20 | 33/40 | 82.5% |
   | rc06 Border denial | 15/20 | (pending) | ≥15/40 | ≥ — |
   | rc08 Lane assignment | (pending) | (pending) | — | — |

   A1 champion reference = 82.5% baseline (pm20 hth_t4 Red+Blue mean).
   **rc02 beats A1 by ~17.5pp on baseline.**

5. Committed in two logical chunks:
   - `432a30d` pm23 Mac: rc02-rc08 Tier 1 round-robin candidates (6 files)
   - `16145b5` pm23 docs: rc-pool + pm22/pm23 handoff + HTH results

## Observations

- **rc04 v1 failure pattern** (0/4): applying top-K re-rank on every turn
  overrode A1's correct choice when A1 and the overlay target disagreed.
  Fix was conflict-triggered: only override when a specific dogpile
  condition exists; and within a tolerance band where A1 is near-
  indifferent. Generalized this pattern into rc06 and rc08 as well —
  all three follow the same "conflict-triggered + tolerance-gated" shape.

- **rc02 exceptional performance** suggests baseline has weak AP / chokepoint
  handling on defense. Tarjan APs accurately identify chokes that `zoo_core`
  `_computeBottlenecks` (cut-vertex approximation) could miss, and the
  override cleanly sits on the neck. Will see whether advantage persists
  against stronger opponents (monster_rule_expert, zoo_reflex_h1test) in
  Phase 4. Baseline-specific "cheese" is a real possibility here.

- **rc03's 95% is interesting** because it only engages when an invader
  is physically inside a dead-end chain — most of the game it is a no-op.
  The 2 losses are both Blue-side, suggesting layout-asymmetry (our blue
  dead-ends might be easier to trap than red's, or baseline's defensive
  routing differs by side).

- **rc05 and rc06 lose some Blue games on the -16/-17 pattern** — the
  score swing characteristic of our agent being eaten mid-carry on a
  bad seed. Consistent with known A1 + risk-amp interactions.

- Tarjan's iterative DFS with `[node, nbrs_list, next_index]` stack
  entries works well; rooted at each unvisited cell so multi-component
  mazes (split by a non-wall-but-separator pattern) are handled. APSP
  precompute in zoo_core already guarantees `O(1)` distance lookups
  during the per-turn AP selection, keeping per-turn cost well under 1s.

## Decisions

- **rc02 candidate for submission consideration.** Its 40/40 vs baseline
  is strong enough that if Phase 4 confirms it ≥ A1 on the broader pool,
  rc02 could replace A1 as `your_best.py`. Defer the decision until full
  Phase 4.
- **rc07 (kamikaze) deferred** to later session. Coordination-heavy;
  likely low ROI given the top-K-tolerance overlay pattern doesn't
  obviously apply.
- **Re-ranking overlay pattern canonicalized**: top-K from A1 scoring,
  tolerance band, conflict-triggered override. Use this for all
  assignment-style rcs going forward (rc11 Border Juggling, rc32
  Pincer Maneuver, rc33 Persona-shift, etc.) to avoid rc04 v1-style
  regressions.
- **Order 3/4 server autopilot** still runs via `7,37 * * * *` cron.
  Check at next session start whether Order 3 completed (expect ETA
  ~12:30 KST 2026-04-19).

## Open Items

- rc06 Blue 20 + rc08 Red/Blue 40 pending completion at end of session;
  numbers will be captured in next update.
- Day 2 plan: rc09 (G1 23-dim features — needs new feature extractor,
  slightly more complex), rc10 (G3 role-conditioned input), rc11 (Border
  Juggling), rc15 (F2 Ensemble Voting combining rc02-rc08).
- rc09/rc10 require modifying or forking `zoo_features.py` — must not
  break A1 flattened submission, so forking to `zoo_features_rc09.py`
  is the safe path.
- Phase 4 round-robin tournament can now run with 13+ candidates:
  baseline, A1, O2, D1, D2, D3, D13, T4, T5, rc02, rc03, rc04, rc05,
  rc06, rc08.

## Next-session priority

1. Pull Order 3 results if complete on server; HOF wrap if fitness
   exceeds A1's 1.065 (pm21 auto-detect logic).
2. rc09 / rc11 / rc15 (complete Day 2 targets).
3. Consider promoting rc02 to submission candidate if Phase 4 partial
   confirms baseline-generality of its lead.


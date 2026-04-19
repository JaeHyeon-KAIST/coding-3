---
title: "2026-04-19 - pm24 MEGA sprint 68 rc 8 champions"
tags: ["pm24", "autopilot", "rc-sprint", "100pct-champions", "role-asymmetric", "batch-a-to-q", "pacman"]
created: 2026-04-19T06:39:06.211Z
updated: 2026-04-19T06:39:06.211Z
sources: []
links: []
category: session-log
confidence: medium
schemaVersion: 1
---

# 2026-04-19 - pm24 MEGA sprint 68 rc 8 champions

# pm24 MEGA sprint — 68 round-robin candidates, 8 perfect champions

**Date**: 2026-04-19 pm24
**Duration**: ~5-6h Mac work (autopilot continuous)
**Focus**: Continuous rc implementation + 40-game HTH battery while server Order 4 cooked
**Outcome**: 68 new rc (66 pass + 2 drop), 8 at 100% WR vs baseline

## Batch summary (17 batches A-Q)

| Batch | Count | Theme | Pass / Drop | New 100% |
|---|---|---|---|---|
| A | 5 | Boids/disruption/kite/stacking/opening | 5/0 | — |
| B | 3 | Stochastic overlays | 1/2 | — |
| C | 4 | Kamikaze/layout/asym/combo | 4/0 | rc82 (rc29+rc44) |
| D | 4 | Composite stacks | 4/0 | — |
| E | 4 | Novel axis + role-asym | 4/0 | — |
| F | 4 | Third asym + scared/dense/stack | 4/0 | — |
| G | 4 | Deeper composites | 4/0 | — |
| H | 4 | Adaptive/inverted/quad | 4/0 | — |
| I | 4 | Pairwise champion asym matrix | 4/0 | rc105 (rc16+rc82) |
| J | 4 | rc105 explorations | 4/0 | rc109 (rc16+rc29+rc82) |
| K | 4 | rc109 extensions | 4/0 | — |
| L | 4 | Composites + novel | 4/0 | rc116 (rc109+opening) |
| M | 4 | rc116 extensions + ablation | 4/0 | — |
| N | 4 | Defender-anchored test | 4/0 | rc123 (rc32+rc82) |
| O | 4 | rc82-DEF pattern verification | 4/0 | — |
| P | 4 | rc29-overlay verification | 4/0 | rc131 (rc32+rc29+rc82) |
| Q | 4 | Diversity sweep (final) | 4/0 | — |

**Previous champions (pre-pm24)**: rc02, rc16 (both pm23, 100% solo).

**New champions pm24**: rc82, rc105, rc109, rc116, rc123, rc131.

**Total 8 champions at 100%**: rc02, rc16, rc82, rc105, rc109, rc116, rc123, rc131.

## Key design discoveries

### Pattern 1: Orthogonal overlays compose
rc82 = rc29 REVERSE + rc44 state-conditioned stacking. Both are orthogonal (tactical vs strategic) and compose to 100% vs A1's 79-82.5%.

### Pattern 2: rc16 OFF + rc82 DEF is uniquely strong
Eight 100% teams all include rc82 as DEFENDER. But rc82 DEF alone is NOT sufficient — it only reaches 100% when paired with rc16-family or rc32 OFFENSE. Plain A1/rc09/rc19 OFF + rc82 DEF caps at 87-92.5%.

### Pattern 3: rc29 REVERSE overlay is universal lift
rc16 OFF + rc82 DEF = rc105 100%. Add rc29 → rc109 100%. Add opening book → rc116 100%. Same trick with rc32 OFF: rc123 100%. Add rc29 → rc131 100%.

### Pattern 4: Fire-condition narrowness matters
Wide fire-conditions (rc87 "always-on when safe", rc89 "ghost within 5 cells") get 55% — catastrophic. Narrow (rc02 "invader visible", rc29 "3 same dirs + ghost ≤ 4", rc48 "teammate-cell collision") reach 90-100%.

### Pattern 5: Stochastic injection must be threat-conditioned
rc29 (REVERSE only when herded) at 92.5%. rc34 (every 7 turns regardless) at 0%. Time-conditioning without context = catastrophe.

### Pattern 6: Ensembles have dilution risk
3-champ dense vote (rc94, equal weights over 100% members) = 95%. 5-member ensemble with weaker A1/rc21 (rc83) = 90%. Weight-by-WR (rc102) = 95%. Voting ALWAYS pulls top member down.

### Pattern 7: Sequential stacking preserves strength
rc86 (rc82+rc48 sequential) = 95%+ doesn't dilute. rc101 (quad stack) = 97.5%. Stacked overlays don't hurt the champion whose ceiling they approach.

### Pattern 8: 2-ply lookahead veto hurts champion overlays
rc95 (rc82 + 2-ply veto) = 87.5% — blocks rc82's good 3+ ply disruption moves. rc126 (rc109 + veto) = 92.5%+.

### Pattern 9: Time-adaptive switch is brittle
rc98 (rc02 early → rc82 late): 85%. Discrete strategy switch without smooth blending loses.

## Failed candidates (2 drops)
- **rc30 particle-filter blinding** (random top-K when invisible): 25%. Random wrecks critical food-return / ghost-kill moments.
- **rc34 Pavlovian feinting** (every 7 turns pick 2nd-best): 0%. Same lesson as rc30 — unconditioned randomness catastrophic.

## Weak-but-viable (≤ 75%)
- rc87 far-food prioritization: 55%
- rc89 dead-end avoidance: 55%
- rc92 scared-ghost aggressive: 75%
- rc99 adaptive defender: 72.5% (many ties, too defensive)
- rc06 border denial (pm23): 75%

## Server Order 4 status (during pm24)
- Launched 2026-04-19 11:57 KST: master-seed=2026, init=a1, HOF pool=A1+O2+O3
- By pm24 end: Phase 2a gen 2/30, best 0.597, wall ~60 min/gen
- ETA: ~30h total, finish ~17:00 KST 2026-04-20

## Phase 4 pool (ready for tournament)
- **100%**: rc02, rc16, rc82, rc105, rc109, rc116, rc123, rc131 (8)
- **97.5%**: rc32, rc90, rc97, rc101, rc108, rc111, rc112, rc115, rc120, rc132, rc137 (11)
- **95%+**: rc03, rc15, rc21, rc84, rc86, rc93, rc94, rc96, rc100, rc102, rc103, rc106, rc107, rc114, rc136 (15)
- **90-92.5%+**: rc07, rc08, rc09, rc11, rc19, rc29, rc44, rc45, rc48, rc50, rc81, rc83, rc85, rc91, rc103 (many)
- plus A1, O2, O3, (O4 pending), D1/D2/D3/D13, T4/T5

**Total pool ≈ 75 agents.**

## Next-session priority (pm25)

1. **Server poll** — check Order 4 completion
2. **Phase 4 tournament setup** — `experiments/tournament.py` round-robin ELO on ~75 agents × 2 seeds × defaultCapture+RANDOM
3. **M7 flatten** — pick champion for submission (most likely rc82/rc105/rc109/rc116/rc123/rc131 depending on Phase 4 ELO)
4. **M8-M10** — output.csv + report + zip packaging

## Commits (pm24 MEGA sprint)
- `9573e9d` Batch A+B (rc28/29/30/31/34/44/48/50)
- `dfcd629` Batch C (rc07/21/81/82)
- `179a6e8` Batch D (rc83/84/85/86)
- `ace9393` Batch E (rc87/88/89/90)
- `00e6d8f` Batch F (rc91/92/93/94)
- `6a17451` Batch G (rc95/96/97/98)
- `ca8888a` Batch H (rc99/100/101/102)
- `6d6079b` Batch I (rc103/104/105/106)
- `78b4394` Batch J (rc107/108/109/110)
- `0c0ac5c` Batch K (rc111/112/113/114)
- `ba3c068` Batch L (rc115/116/117/118)
- `d10ed05` Batch M (rc119/120/121/122)
- `88853ba` Batch N (rc123/124/125/126)
- `714317b` Batch O (rc127/128/129/130)
- `b74c4ae` Batch P (rc131/132/133/134)
- `51fb431` Batch Q (rc135/136/137/138, FINAL)

## Files touched (pm24 total)
- 68 new `minicontest/zoo_reflex_rc*.py` files
- `.omc/plans/rc-pool.md` (detailed change log, 17 batch entries)
- `.omc/STATUS.md` (updated 17× with champion tiers)
- `.omc/SESSION_RESUME.md` (pm25 TL;DR)
- wiki session-log entries (2 — this one being final)


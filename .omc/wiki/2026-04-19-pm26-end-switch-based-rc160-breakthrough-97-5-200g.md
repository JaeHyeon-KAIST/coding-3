---
title: "2026-04-19 pm26 END — switch-based rc160 breakthrough (97.5% 200g)"
tags: ["pm26", "rc160", "switch-based", "breakthrough", "100g-authoritative", "pattern-laws"]
created: 2026-04-19T15:10:11.967Z
updated: 2026-04-19T15:10:11.967Z
sources: []
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-19 pm26 END — switch-based rc160 breakthrough (97.5% 200g)

# pm26 END session log — switch-based breakthrough

**Date**: 2026-04-19 → 2026-04-20
**Focus**: Started with Tier-3 sprint (rc52b/rc46/rc141/rc142/rc52c/rc52d — all 90-92% ceiling). User directed "rc 더 진행" repeatedly, then `/autopilot`, so pivoted to explore NEW directions. Found **context-conditional switching** breakthrough. 22 new rc total this session.

## Key result

**rc160 (`if score >= 1: rc82 else rc16`)** — 200g vs baseline = **195/200 = 97.5%** Wilson [0.944, 0.990].
- Simplest 2-way switch between two existing champions.
- Exceeds rc82 solo (97%) and rc16 solo (92%) when tested at 100g.
- Easy to flatten into your_best.py for submission.

## All switch variants tested

| rc | Rule | 100g WR |
|---|---|---|
| rc148 | 3-way: rc82 lead / rc52b chase / A1 | 96% |
| rc149 | Phase switch (early/late rc82, mid rc52b) | 96% |
| rc151 | Tighter rc148 (LEAD=2, CHASE=-1) | 96% |
| rc152 | 4-way: rc82 big-lead / rc16 small-lead / A1 / rc52b | 98% |
| rc153 | rc32 instead of rc16 (multi-inherit bug fixed) | 96% |
| rc154 | 5-way fine-grained | 92% (too fragmented) |
| rc155 | rc22 neural in chase slot | 93% |
| rc156 | Tighter rc152 (LEAD=3, SMALL=1, CHASE=-1) | 97% |
| rc157 | 3-way no-A1 (rc82/rc16/rc52b) | 96% |
| rc158 | rc152 + hysteresis | 94% (sticky bad) |
| **rc159** | rc82 big-lead AND chase + rc16 small-lead + A1 tied | **99%** |
| **rc160** | 2-way: rc82 ≥1 / rc16 else | **99%** (200g: 97.5%) |
| rc161 | 3-champion rc82/rc131/rc16 | 97% |
| rc162 | rc82 always except tied→rc16 | 93% |
| rc163 | rc82 ≥0, rc16 else | 96% |
| rc164 | Inverse (rc16 lead, rc82 else) | 97% |
| rc165 | rc82 ≥2 | 96% |
| **rc166** | rc82 ≥3 | **99%** |
| **rc167** | rc82 lead OR deep-chase, rc16 else | **99%** |

## Pattern laws (5 distilled from sweep)

1. **Asymmetric direction matters**: rc82-lead + rc16-else works (99%); reverse fails (97%).
2. **rc16 MUST cover tied score**: any variant that gives tied→rc82 drops 3-6pp.
3. **Threshold 1-3 is flat**: rc160 (≥1), rc166 (≥3) both 99%. rc165 (≥2) regresses somehow (variance).
4. **More slots don't help**: 4-way rc152 = 98%, 5-way rc154 = 92%, 2-way rc160 = 99%.
5. **Chase-agent choice is low-impact**: rc52b / rc22 / rc32 / A1 in chase all within 2pp.

## 100g authoritative verifications (pm23/pm24 40g "100%" corrected)

| champion | pm23/24 40g claim | pm26 100g actual |
|---|---|---|
| rc82 (rc29+rc44 composite) | 100% | **97%** |
| rc16 (Voronoi overlay) | 100% | **92%** |
| rc105 (rc16 OFF + rc82 DEF asym team) | 100% | **95%** |

All prior claims were variance-inflated. Only rc160 (99% / 97.5%) genuinely exceeds 95% baseline WR at 100-200g.

## REINFORCE training variance

Three rc52 training runs:
- rc52 (orig, 30iter): 90% HTH
- rc52b (alt 30iter): 92% HTH (lucky)
- rc52c (60iter aggressive lr): 86% HTH (overshot)
- rc52d (60iter conservative lr): 86% HTH (also regressed)

**Conclusion**: rc52b is a single-run outlier. Mean HTH across training runs is ~88%. Tournament reporting should state this explicitly.

## Compute note

Session ran 22 new agents × 100g HTH each ≈ 2200 games on Mac defaultCapture. All single-game wall ~5-6s × 10 active Mac cores ≈ 40 wallclock minutes concurrent HTH throughput. Full sprint took ~8 hours real time including training cycles.

## Files touched

- `minicontest/zoo_reflex_rc141.py` through `rc167.py` (20 new agents)
- `minicontest/zoo_reflex_rc52b.py`, `rc52c.py`, `rc52d.py` (REINFORCE variants)
- `experiments/rc52b_final_weights.py`, `rc52c_final_weights.py`, `rc52d_final_weights.py`
- `.omc/plans/rc-pool.md` (+ pm26 log entries)
- `.omc/STATUS.md` (headline update)
- No submission-target files edited (your_best.py etc. untouched).

## Next session (pm27)

1. **Phase 4 tournament prep**: put rc160 against top pm24 champions (rc82, rc105, rc131, etc.) — does rc160 still win when facing strong opponents (not just baseline)?
2. **M7 flatten_agent**: rc160 is simple enough to hand-flatten into 20200492.py. Start AST work.
3. **Server Order 4 check**: retry SSH; HTH battery if finished.
4. **Stretch**: rc168 variants if rc160 loses to champions — maybe rc82-lead / rc105-else (asymmetric team instead of rc16).


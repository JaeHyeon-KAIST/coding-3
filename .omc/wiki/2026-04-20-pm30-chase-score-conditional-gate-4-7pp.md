---
title: "2026-04-20 pm30 β_chase score-conditional gate +4.7pp"
tags: ["pm30", "rc-tempo", "beta", "chase", "score-gate", "smoke", "multi-opp"]
created: 2026-04-20T10:41:24.931Z
updated: 2026-04-20T10:41:24.931Z
sources: ["experiments/artifacts/rc_tempo/smoke_pm30_current.csv", "experiments/artifacts/rc_tempo/smoke_pm30_v2a.csv", "experiments/artifacts/rc_tempo/smoke_pm30_v2a2.csv", "experiments/artifacts/rc_tempo/smoke_pm30_v2d.csv", "minicontest/zoo_reflex_rc_tempo_beta.py"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-20 pm30 β_chase score-conditional gate +4.7pp

# pm30 — β_chase 강화 (SAFE layout / 11 diverse opponents)

**Date**: 2026-04-20
**Focus**: `zoo_reflex_rc_tempo_beta.py` Phase 1 capsule chase 개선
**Scope (user scope-cut)**: SAFE layout 한정, UNSAFE runtime chase 차기 세션

## Activities

1. `experiments/rc_tempo/smoke_multi_opp.py` 신규 — 11-opp × 2 layout × 2 color × 15g = 660g resumable smoke harness. `hth_resumable.py` primitives 재사용.
2. Server 660g smoke 4 variant (current, v2a margin=0, v2a2 margin=-1, v2d score-gate).
3. 최종 2000g HTH 런칭.

## Observations — 660g smoke per-opp WR

| Opp | current | v2a | v2a2 | **v2d** | v2d-current |
|---|---|---|---|---|---|
| baseline | 0.850 | 0.850 | 0.867 | **0.900** | +5.0pp |
| monster_rule_expert | 0.683 | 0.783 | 0.767 | 0.717 | +3.3pp |
| zoo_distill_rc22 | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| zoo_reflex_h1c | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| zoo_reflex_h1test | 1.000 | 1.000 | 1.000 | 1.000 | 0 |
| zoo_reflex_rc02 | 0.783 | 0.800 | 0.750 | **0.850** | +6.7pp |
| zoo_reflex_rc16 | 0.500 | 0.500 | 0.500 | 0.500 | 0 |
| zoo_reflex_rc166 | 0.667 | 0.650 | 0.583 | 0.667 | 0 |
| zoo_reflex_rc32 | 0.483 | 0.317 | 0.550 | **0.800** | **+31.7pp** |
| zoo_reflex_rc47 | 0.500 | 0.500 | 0.500 | 0.500 | 0 |
| zoo_reflex_rc82 | 0.583 | 0.433 | 0.533 | **0.633** | +5.0pp |
| **OVERALL** | **0.732** | 0.712 | 0.732 | **0.779** | **+4.7pp** |

## Decisions

1. **2a (full-path BFS) REJECTED** — margin=0 regressed -2pp; margin=-1 flat. Helps rule-based defenders (monster/rc32 via v2a1) but hurts composite defenders (rc82/rc166). Path-aware check too conservative against non-optimal intercept policies.
2. **2d (score ≥ +5 → chase skip) ACCEPTED** — +4.7pp clean win. Especially strong vs Pincer defender (rc32 +31.7pp). Committed as pm30 final β improvement.
3. **2b (defender prediction), 2c (food pickup) SKIPPED** — 2d already clears plan's pm30 completion criteria (≥68.6% overall ✓; 2000g HTH pending for H2H vs rc166). Further iteration risks regression without more data.

## Structural findings

- **rc47 distant = 30T 순수 교착** (avg_score 0.0) — β와 rc47 both-attack mirror leading to 0-0 tie, capture.py 1200-move timeout. 타입 과제 "tie ≠ win" 규정에서 0% WR 처리. 이번 세션 chase 로직으로 해결 불가.
- **rc16 both layouts = 15W/15L** — Voronoi 어긋남 없는 50/50 pattern. chase 변경과 무관.
- **DISTANT layout 일반적 손실 커지는 추세** — 넓은 맵에서 scared trip return이 defender 공격과 race 상실. Phase 3/4 DP weight 튜닝이 차기 타겟.

## Open items

- UNSAFE layout runtime chase (user scope-cut, 다음 세션)
- Phase 3 DEFAULT_RISK_WEIGHTS 튜닝 (distant 개선 후보)
- Agent B 사전-midline 이동 (2e 후보)
- rc47 distant 교착 해결: scared trip 중 offensive 강화 또는 scared 외 offense 변경

## Next-session priority

1. pm30 2000g HTH 결과 수집 → rc166 default H2H 확인 (합격 기준 ≥55%)
2. β_chase final → `your_best.py` 또는 `20200492.py` flatten 후보 고려
3. DISTANT layout 개선: Phase 3 weight + Agent B pre-position
4. rc47 distant 교착 구조적 해결 방안 수색

## Commits

- `939f6c6` smoke_multi_opp.py 11-opp harness
- `efedba6` S2a v1 full-path BFS margin=1→0 (regressed, reverted)
- `864fc34` S2a v2 margin=-1 (flat, reverted)
- `e304b52` S2d score-gate accepted (+4.7pp)

## Files

- `experiments/rc_tempo/smoke_multi_opp.py` — multi-opp smoke harness (신규)
- `minicontest/zoo_reflex_rc_tempo_beta.py::_choose_capsule_chase_action` — score gate 추가
- `experiments/artifacts/rc_tempo/smoke_pm30_{current,v2a,v2a2,v2d}.csv` — per-variant 660g data
- `experiments/artifacts/rc_tempo/hth_beta_pm30.csv` — 2000g 검증 (진행 중)


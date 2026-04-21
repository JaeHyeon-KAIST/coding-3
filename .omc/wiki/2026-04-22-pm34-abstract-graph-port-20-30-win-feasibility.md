---
title: "2026-04-22 pm34 - abstract graph port + 20/30 WIN feasibility"
tags: ["pm34", "abstract-graph", "beam-search", "tree-knapsack", "pocket-partial-visit", "pareto-dedup", "feasibility", "2-cap-chain"]
created: 2026-04-21T17:47:25.227Z
updated: 2026-04-21T17:47:25.227Z
sources: []
links: []
category: session-log
confidence: medium
schemaVersion: 1
---

# 2026-04-22 pm34 - abstract graph port + 20/30 WIN feasibility

# 2026-04-22 pm34 — abstract graph port + 20/30 WIN feasibility

## Date / Focus

2026-04-22 01:00–02:30 pm34. pm33에서 설계한 abstract graph (X + pocket header + distance-check edges)를 production 모듈로 포팅하고, food-level (19/30 WIN) 대비 정확도 검증.

## Activities

1. **Abstract graph 모듈화** → `experiments/rc_tempo/abstract_graph.py`:
   - `parse_layout`, `build_cell_graph`, `find_pockets`, `build_pocket_headers_with_cost_table`, `build_x_edges`, `build_abstract_graph`, `build_from_maze`
   - PIL 의존성 제거 (production-ready)
2. **Abstract beam search** → `experiments/rc_tempo/abstract_search.py`:
   - Bitmask vx/vh (Python int)
   - Multi-source start + multi-sink end
   - Dijkstra-based `dist_to_end` admissible pruning
   - Revisit 허용 (first-visit food gain)
   - Pareto dedup (food in key)
   - cost_table 기반 k-option 분기 (partial pocket visit)
3. **4 strategy solvers** → `experiments/rc_tempo/feasibility_4strategies_abstract.py`:
   - `solve_split_abstract`, `solve_both_abstract` — ProcessPoolExecutor 병렬
4. **30 map 시각화** → `experiments/rc_tempo/render_all_finals.py`:
   - `random_{01..30}_FINAL.png` 업데이트
5. **Chamber 프로토타입** → `experiments/rc_tempo/chamber_test.py`:
   - Biconnected components via Tarjan's algorithm
   - Leaf-block chamber atomization (articulation-point-based)
   - Result: **regression** (atomic 제약 → beam 유연성 저하). 롤백.

## Observations

### 수정 여정 (13 → 20/30 WIN)

| 단계 | WIN | 주요 변경 |
|---|---|---|
| 1 초기 포팅 | 13/30 | 기본 abstract (여러 버그) |
| 2 Y-merge food-union 수정 | 13 | trunk food 이중 합산 제거 (over-count 교정) |
| 3 Cap-in-pocket extended_main | 16 (+3) | isolated cap 복구 (seeds 4/9/16/24/25) |
| 4 X revisit 허용 | 18 (+2) | chamber/loop neck 재통과 가능 |
| 5 **Tree knapsack DP + Pareto dedup** | **20** (+2) | partial pocket visit, food를 dedup key에 포함 |

### 해결된 주요 버그 2개

1. **Y-merge double-count**:
   - 원인: 공통 trunk food가 각 branch에서 중복 합산 (`combined_food += h['food_count']` 단순 합)
   - 수정: path 셀들의 union ∩ food_set으로 food count 계산
   - 영향: 30/30 seeds 모두 food accounting consistent (header + main = blue_food)

2. **Pareto dedup key 누락**:
   - 원인: dedup key `(ci, vx, vh, start)` — food 무시. Header 방문의 k=1..max 분기 중 **time 제일 짧은 k=1만 유지**되고 k=2..max 전부 버려짐 → partial-visit 옵션 사실상 무효화
   - 수정: `(ci, vx, vh, start, food)` — 다른 food count는 별도 state
   - 영향: 13/30 → 20/30 WIN (가장 큰 single fix)

### Food-level vs Abstract 최종 비교

| 지표 | Abstract (BEAM=500) | Food-level |
|---|---|---|
| WIN count | **20/30** | 19/30 |
| Wall (120 cases, 8 workers) | 7s | 295s |
| Single-thread per case | 335ms | 2.5s |

| Agreement | Seeds |
|---|---|
| Both WIN (16) | 3, 5, 6, 7, 8, 11, 12, 13, 15, 19, 20, 21, 23, 26, 28 (+ 1 dup) |
| Abs only WIN (4) | 10, 14, 25, 29 |
| FL only WIN (3) | 2, 4, 16 |
| Both miss | 9, 17, 18, 22, 24, 27, 30 |

### Beam scale behavior (non-monotonic!)

| BEAM | WIN | per-map wall |
|---|---|---|
| 500 | 20 | 1.3s |
| 2000 | 20 | 5s |
| 5000 | 21 | 13s |
| 20000 | 18 ⚠️ | 50s |

Beam=20000 regress 원인: priority function `(-food, -depth_sum, time)` 의 depth_sum 편향이 거대 beam에서 분산을 악화시킴. 500~5000 sweet spot.

### Chamber atomization 실패 이유

- Biconnected decomposition으로 각 food cell이 정확히 한 block에만 속함 (overlap 없음, correct)
- 하지만 chamber를 "AP 진입 → k food → 같은 AP 퇴장" atomic unit으로 만들면 **beam 유연성 저하** — 기존 모델은 chamber 내부 X를 개별 방문 가능 (revisit-allowed로 neck 재통과)
- 결과: seed 2 BEAM=5000에서 20 → 19로 regress
- 교훈: chamber-like regions은 atomic이 아닌 "cells as X's"로 다루는 게 더 expressive

## Decisions

1. **β agent는 abstract graph 사용** — food-level 초과 + 15s init 여유.
2. **Chamber atomization 불채택** — regression 증명됨. 현재 model은 leaf pockets (tree knapsack) + main_corridor X's.
3. **BEAM=500 production default** — 20/30 WIN, 1.3s per map. Anytime refinement로 남은 1 WIN 잡기가 합리적.
4. **Seed 16 cap-in-pocket 특수 케이스**는 미해결. In-game WR로 판단.

## Open items

- β agent `zoo_reflex_rc_tempo_gamma.py` 구현
- 30-map HTH 측정 (target 85-95% vs β v2d 75.65%)
- `your_best/baseline{1,2,3}.py` flatten (DummyAgent 제거)
- Seed 16/2/4 cap-in-pocket integration into tree knapsack (optional, +1 WIN)

## Next-session priority (pm35)

1. β agent 뼈대 구현:
   - `registerInitialState`: abstract graph build + 4-strategy beam → best plan
   - `chooseAction`: pre-planned action + anytime refinement in remaining ms
2. 30-map HTH vs baseline (smoke) + rc82 (champion)
3. Full 1200-move game validation
4. Submission flatten

## References

- pm33 design doc: `.omc/plans/pm33-abstract-graph-2cap-strategy.md`
- pm34 production files:
  - `experiments/rc_tempo/abstract_graph.py`
  - `experiments/rc_tempo/abstract_search.py`
  - `experiments/rc_tempo/feasibility_4strategies_abstract.py`
  - `experiments/rc_tempo/render_all_finals.py`
- pm34 prototype (참고용, 사용 안함):
  - `experiments/rc_tempo/chamber_test.py`
- 시각화: `experiments/artifacts/rc_tempo/random_map_images/random_{01..30}_FINAL.png`


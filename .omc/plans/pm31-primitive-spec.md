# pm31 Primitive Spec — Safe Reachability + Food Orienteering Planner

**Date**: 2026-04-20 pm31
**Goal**: β_chase V3 — 완전관측 이용한 "안 죽고 capsule 도달 + slack 동안 food 수확" primitive.
**Target**: v2d 77.9% → +3-7pp (v3a), +5-12pp (v3b)

---

## 1. 환경 전제 (minicontest 특화)

**완전관측 확정** (`capture.py:278-300` SIGHT_RANGE/SONAR commented out):
- `getAgentPosition(enemy)` 항상 실제 좌표 리턴
- Particle filter 불필요
- αβ minimax 직접 적용 가능 (perfect-information zero-sum)

**게임 규칙 재확인**:
- 턴당 1초 (3번 warning, 3번 over forfeit)
- Init 15초
- 1200 move 제한
- Capsule eaten → 상대팀 40 move scared
- 승리: opp food 2개 남기기 전 다 먹음 OR 1200 move 후 더 많이 먹은 팀

---

## 2. β 발동 조건 (trigger)

```python
# _chooseActionImpl 상단
opp_pacman_count = sum(
    1 for i in self.getOpponents(gameState)
    if gameState.getAgentState(i).isPacman
)

sticky = (A_committed and dist(A, capsule) <= 5)

if sticky or opp_pacman_count == 1:
    β ON
else:  # 0, 2
    rc82 delegate
```

**Sticky 규칙**: A가 capsule 5칸 이내면 opp_pacman 변화 무시하고 강행.

---

## 3. Planner API

```python
class SafePlanner:
    def __init__(self, walls, precomputed):
        """
        precomputed: {
            'apsp': Dict[(Cell, Cell), int],        # 전-쌍 거리
            'dead_end_depth': Dict[Cell, int],
            'ap_cells': FrozenSet[Cell],            # articulation points
            'risk_map': Dict[Cell, float],          # static per-cell risk
            'home_cells': List[Cell],
            'enemy_home_cells': List[Cell],
        }
        """

    def plan_to_target(
        self,
        start: Cell,
        target: Cell,
        defender: Optional[Cell],        # V1: 단수 (1:1 가정)
        defender_scared_ticks: int,
        teammate: Optional[Cell],
        food_set: FrozenSet[Cell],       # for orienteering
        slack_budget: int = None,        # None이면 자동 계산
    ) -> PlanResult:
        """
        Returns:
            reachable: bool
            path: List[Cell]             # next-step 추출 용
            cost: float
            next_step: Cell
            food_on_path: List[Cell]     # slack 이용한 food grab (선택)
            safety_margin: int           # def_dist - my_dist at worst cell
        """
```

**V1 구현**: A\* risk-weighted + Voronoi 필터 + `entry_orienteering_dp` slack DP
**V2 구현**: αβ depth 6 + TT + iterative deepening, same API signature

---

## 4. V1 알고리즘 (A\* + Slack DP)

### 4.1 Risk-weighted A\*
```
Edge cost = 1 + λ_risk × risk(to_cell)
                + λ_dead × (dead_end_depth ≥ 3 ? penalty : 0)
                + λ_ap × (cell in ap_cells ? penalty : 0)
Heuristic = apsp[(current, target)]  (admissible)
```

### 4.2 Voronoi reachability filter
```python
def is_path_safe(path, defender, scared_ticks):
    if scared_ticks > len(path):
        return True  # defender scared 전체 경로 커버
    for i, cell in enumerate(path):
        my_dist = i
        def_dist = apsp[(defender, cell)] - scared_ticks
        if my_dist >= def_dist:  # margin=1
            return False
    return True
```

### 4.3 Slack food DP (`entry_orienteering_dp` 재사용)
```python
direct_to_cap = apsp[(start, capsule)]
def_intercept = apsp[(defender, capsule)]
slack = def_intercept - direct_to_cap - 1  # margin

if slack >= 2:
    # foods 후보: dist(start, f) + dist(f, cap) ≤ direct + slack
    #           AND 모든 path cell Voronoi-safe
    #           AND risk(f) ≤ τ_risk
    res = entry_orienteering_dp(start, eligible_foods, capsule,
                                 distance_fn, budget=direct + slack,
                                 objective='count')
    return res['route']
else:
    # 직진
    return a_star_path(start, capsule)
```

---

## 5. V2 알고리즘 (αβ Minimax)

### 5.1 상태
```python
State = (my_pos, def_pos, eaten_food_mask, capsule_eaten, scared_ticks, depth)
Actions = 4 moves (N/S/E/W), legal per maze
```

### 5.2 탐색
- Iterative deepening: depth 2 → 4 → 6, 시간 budget 300ms
- Alpha-beta pruning
- Transposition table (state_hash → (value, depth, bound))
- Move ordering: killer moves + history heuristic

### 5.3 Leaf eval
```
if my_pos == target: return TARGET_REWARD + food_collected * FOOD_VALUE
if my_pos == def_pos (and def not scared): return -INF
if depth == limit:
    heuristic = -apsp[(my_pos, target)] * 10
              + food_collected * FOOD_VALUE
              + (def_scared_remain * 0.5)
              - risk_of_cell(my_pos)
```

---

## 6. 죽음 방지 안전장치 (V1+V2 공통)

| # | 위험 | 대응 |
|---|---|---|
| 1 | Dead-end trap | `dead_end_depth ≥ 3` 인 cell은 λ_dead × 5 패널티 |
| 2 | Smart defender | V1: worst-case {static, greedy} 선택 / V2: αβ로 자동 |
| 3 | Scared 만료 | Planner에 `scared_ticks` 인자 추가, 런타임 감쇠 |
| 4 | Simultaneous move | margin=1 (my_dist < def_dist, 엄격 부등) |
| 5 | Teammate 차단 | `teammate` cell을 blocked set에 포함 |
| 6 | Sticky 오용 | `dist(me, capsule) ≤ 5` 만 sticky 허용 |
| 7 | AP chokepoint | `analyze_capsule_safety` `node_conn=1` 이면 init에서 tempo_enabled=False |

---

## 7. 테스트 하네스

`experiments/rc_tempo/test_capsule_scenario.py`

**Layouts** (1-capsule only):
- `defaultCapture` (하드코딩)
- `distantCapture` (하드코딩)
- `strategicCapture` (하드코딩)
- `RANDOM<seed>` × 5 seed (검증 후 1-cap인 것만)

**Opponents** (12):
- baseline
- monster_rule_expert
- zoo_reflex_rc02 / rc16 / rc32 / rc47 / rc82 / rc166
- zoo_reflex_h1test / h1c
- zoo_distill_rc22
- zoo_reflex_rc_tempo_beta (pm30 v2d)

**Metrics per game**:
- `survived`: A 죽은 횟수 (0이면 perfect)
- `capsule_eaten`: A가 capsule 먹었는지
- `food_on_trip`: Phase 1 + Phase 3 동안 수확
- `final_score`, `winner`

---

## 8. 실행 계획

**Mac** (코딩):
1. Spec 리뷰 ✓
2. `zoo_rctempo_core.py` 확장:
   - `safe_reachability_filter(path, defender, scared_ticks, apsp)` 추가
   - `risk_weighted_astar(start, target, blocked, risk_map, apsp)` 추가
   - `compute_apsp_all_pairs(walls)` 추가 (기존 bfs_distances_from 일반화)
3. `zoo_reflex_rc_tempo_beta_v3a.py` 작성:
   - v2d 로직 복사
   - `_choose_capsule_chase_action` 교체: A\* + Voronoi + slack DP
   - `opp_pacman_count` trigger 상단 추가
   - Safety extensions (1-7)
4. `zoo_reflex_rc_tempo_beta_v3b.py` 작성:
   - 동일 구조, `_choose_capsule_chase_action`만 αβ로 교체
5. `experiments/rc_tempo/test_capsule_scenario.py` 작성
6. 10-50g smoke on Mac (crash check)

**Server** (smoke):
1. git push + ssh jdl_wsl pull
2. tmux work 2 panes:
   - pane 0: v3a 1000g × 12-opp × 4-layout
   - pane 1: v3b 1000g × 12-opp × 4-layout
3. Head-to-head v3a vs v3b 200g

**분석**:
- `analyze_hth.py` per-opp Wilson CI
- v2d 77.9% 대비 Δ 계산
- 이긴 쪽 commit + ReflexRCTempoBetaV3Agent로 flatten 후보

---

## 9. Go/No-go 기준

**V1 pass**: v2d 77.9% 대비 **+2pp 이상** (≥79.9%)
**V2 pass**: V1 대비 **+2pp 이상** OR αβ 고유 강점 (rc47 등 smart 상대)
**모두 fail**: v2d 유지, pm32에서 다른 방향 (Q4 DISTANT 튜닝 등)

---

## 10. 예상 소요

- Mac 코딩: 10-15h
- Server smoke: 8-12h (overnight)
- 분석 + 커밋: 1-2h
- **Total: ~1-2 day**

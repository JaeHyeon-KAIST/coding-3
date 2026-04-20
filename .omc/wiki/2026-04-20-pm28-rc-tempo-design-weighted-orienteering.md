---
title: "2026-04-20 pm28 — rc-tempo V0.1 설계 (weighted orienteering)"
category: session-log
tags: [rc-tempo, orienteering, dp, capsule-return, weighted, precompute, pm28, design]
confidence: high
---

# 2026-04-20 pm28 — rc-tempo V0.1 설계 (weighted orienteering)

## Focus

User-driven design of new rc paradigm ("rc-tempo") — first deterministic orienteering agent, capsule-assisted return trip optimization. No code written yet (user preferred design-first approach). All rc design decisions locked in `.omc/plans/rc-tempo-design.md`.

## Activities

1. **Server Order 4 (A4) 분석** — fitness 0.968 peak (A1 1.065 미달), 건강한 수렴. 서버 root에 unarchived.
2. **rc-tempo 아이디어 발전** (user-driven):
   - 초기: capsule-return trip 개념 (capsule을 복귀로 중간에 먹음 → scared 창이 복귀 안전망)
   - 중간: Agent A만으로 vs 2-offense swarm vs asymmetric — 논의 끝에 "조건부 swarm" 결정
   - **User 핵심 insight**: Pre-capsule death는 "restart 가능, 치명적 아님" (food drops nearby, respawn instant)
   - **User 핵심 insight**: 40 scared는 one-way 40 (not round-trip), 왕복 제약 40/2=20 per direction
3. **Phase state machine 확립** (5 phases, Agent A = precomputed orienteering, Agent B = rc82 기본 + swarm join opt)
4. **Map 실측 분석** (`experiments/test_orienteering.py`):
   - defaultCapture (32×16): DP 0.12s, 7 food ceiling, 39 moves
   - distantCapture (40×16): DP 0.22s, 9 food ceiling, 39 moves
   - strategicCapture (44×13): DP 2.32s, 13 food ceiling, 38 moves
   - jumboCapture: 158 foods, 2 capsules → V0.1 fallback rc82 (capsule chaining = V2)
5. **User의 weighted orienteering 제안** (game-changer):
   - DP 목표: max |foods| → max Σ risk(f)
   - 이유: 40 scared는 "평소 위험한 food 전용", 쉬운 food는 Agent B 또는 후속 trip
   - Risk metric: dead-end depth + articulation 경유 수 + home 거리 + Voronoi margin + 고립
6. **V0.1 scope lock**: 1-capsule 맵만 (default, distant, strategic), 나머지 rc82 fallback

## Observations

1. **Phase 3 (scared 창) 은 deterministic** — capsule 도달만 하면 나머지 DP precomputed로 자동 운영. 기존 rc 중 유일한 "plan-based" 계열.
2. **User's risk-weighted insight는 근본적 개선**:
   - 기존 개수 max DP: 쉬운 food 7개 수확 → rc82가 이미 잘 먹는 영역
   - Weighted DP: 어려운 food 5-6개 수확 → rc82 불가 영역 전용 청소
   - **장기 게임 효율 ↑** (이번 trip 적게 먹어도, 다음 trip부터 map 전체가 쉬워짐)
3. **Capsule 메커니즘 재확인**:
   - Scared 감소는 scared agent의 자기 turn에만 (40 scared = 상대의 40 turn = 40 round = 40 of my own turns)
   - Capsule 팀 lock: Red는 Blue 영역 capsule만 eat 가능, 상대가 "뺏어" 먹을 수 없음
   - Food drop on death: 죽은 위치 근처 재배치 (같은 side, BFS)
4. **DP 시간 견적**: weighted 버전도 같은 state space, 시간 변화 無. strategicCapture 2.18s가 경계지만 15s init 예산 여유.

## Decisions

| 결정 | 내용 |
|---|---|
| DP vs heuristic | **DP 사용** (100% 최적, 0 hyperparameter, 모든 scope 맵 15s 내) |
| V0.1 scope | **1 capsule 맵만** (3개), 나머지 rc82 fallback |
| 목적함수 | **risk-weighted sum max** (user insight) |
| Agent B 역할 | 기본 수비 + swarm-safe 시 midline pre-position + scared 창 opportunistic cleanup |
| Pre-position trigger | A within 5 cells of capsule + opponents > 8 cells from capsule |
| "Too deep" skip | `depth > max_opp_depth × 0.85` (map-relative) |
| Dead recovery | Simple: respawn detect → phase 1 restart. 2+ deaths → permanent rc82 fallback |
| V0.2+ deferred | Capsule chaining, Voronoi safe route table, top-3 variants, scared ghost hunt |

## Open items (pm29에서 구현 시 결정)

1. Risk weight 상수 (tentative 3/2/0.5/5/2) — defaultCapture에서 DP 출력 보고 tune
2. Agent B cleanup scope ("safe only" vs "any not in A plan")
3. Dead count threshold (2 or 3 consecutive deaths → fallback)
4. swarm_safe threshold (8 cells vs other)

## Next-session priority

1. **`.omc/plans/rc-tempo-design.md` 정독** → 전체 설계 복원
2. **Server A4 archive** (5분 cleanup)
3. **Task #1 스켈레톤 → Task #12 AI_USAGE** 순차 구현 (1일)
4. **100g HTH vs baseline + H2H vs rc82/rc166**

## Tasks 상태

- Task list (13개) TaskCreate로 저장. 구현 순서: #1 → #10 → #2 → #13 → #3 → #4 → #5 → #8/#9 → #11 → #12
- 미확정 design item은 Task comment에 체크포인트로 추가

## Key references

- **Design doc (critical)**: `.omc/plans/rc-tempo-design.md`
- DP timing test: `experiments/test_orienteering.py`
- Pm27 last session log (이전 맥락): `.omc/wiki/2026-04-20-pm27-tier2-3-expansion-m7-flatten-rc166-rc177-co-peak.md`
- User's insight 연쇄: "capsule 복귀로 중간에 먹음" → "2공 몰빵 위험" → "B pre-position" → "risk-weighted DP"

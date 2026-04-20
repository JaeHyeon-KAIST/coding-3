# pm31 전략회의 kickoff — β_chase 다음 방향

**작성**: 2026-04-20 pm30 END (strategy discussion paused, 다음 세션에서 재개)
**현재 상태**: β v2d 2000g HTH = **75.65%** [0.737, 0.775] (+7.05pp over pm29 β)

---

## 전략회의 핵심 결론 (pm30에서 이미 합의)

### 1. 현재 β_chase 로직 정리 (학습 X, hand-rule)

Phase 1 Agent A `_choose_capsule_chase_action`:
- Init: static safety gate (node_conn ≥ 2 AND depth ≤ 15) 로 tempo on/off
- 매 턴 3개 abort 조건 체크 후 통과하면 **1-step greedy BFS** toward capsule:
  1. **score ≥ +5** (pm30 S2d 추가) → rc82 위임
  2. **defender ≤ 2** from me → rc82 escape
  3. **defender_to_cap + 1 < me_to_cap** → rc82 fallback
- 통과 시: 캡슐 쪽 한 칸.

**학습 요소 전혀 없음. 단순 if문 + distance.**

### 2. 다음 방향 옵션 (유저 선택 대기 중)

| 옵션 | 성능 기대 | 리스크 | 핵심 |
|---|---|---|---|
| A. data-driven rule expansion | +2-5pp | 낮 | Phase 1 결정 로깅 → 패턴 찾아 gate 추가 (2-3h) |
| B. CEM on chase-policy weights | +3-8pp | 중 | numpy-only 학습. 11-opp pool, evolve.py 재사용 (서버 12-15h) |
| C. αβ mini-search (Phase 1 subgame) | **+5-12pp** | 중-상 | 2-agent search. Defender 모델 필요. 구현 1-2d. **rc47 패러다임, unknown tournament opp에 robust** |

**유저 관심**: 성능 peak 높은 건 C. "학습" 의도는 B.

### 3. Defender 모델 핵심 insight (C의 전제)

"greedy 추격" 가정은 **baseline 한 놈에만 맞음**. 실제 우리 opp pool은:
- baseline: greedy 추격 ✓
- rc02: Articulation Point 정지 (static)
- rc16: Voronoi territorial
- rc32: Pincer 협동
- rc82: 상태-조건부 전환
- rc166: score switch
- rc47: near-optimal αβ
- monster: rule tree
- h1test/h1c: 수비 없음

**해결 후보**:
1. Pessimistic reachability (Stage 2a 시도 → 과보수 -2pp)
2. **Observation-based classifier** (rc46 패러다임, 20턴 관찰 → 4분류: pursue/patrol/territorial/search)
3. Multi-hypothesis worst-case

### 4. Opp configuration 분기 (유저 제안, 미구현)

**언제 β chase 로직 발동해야 하는가?** opp_pacman_count 로 판정:

| opp_pacman_count | 의미 | β 행동 |
|---|---|---|
| 0 | 상대 2-defender (둘 다 우리진영 못 들어옴) | **중립 대기** (rc82), capsule chase 비활성. 어차피 상대 score=0이라 간단히 food 1-2 deposit로 승리 |
| **1** | **상대 1-attacker + 1-defender** (가장 흔한 1+1 race) | **β chase 즉시 가동** — 이게 capsule tempo 전략의 핵심 사용처 |
| 2 | 상대 2-attacker (both-OFF, h1test류) | **수비 올인**, chase 비활성. 2-pacman = scared 대상 없음 → capsule 가치 낮음 |

**엣지**:
- 상대가 계속 2-defender 유지 → trigger 안 터짐, rc82 중립 게임 OK
- 2-pacman으로 순간 건너뜀 → 즉시 chase 취소
- 1→0 전환 (attacker 복귀): capsule 가까우면 계속, 멀면 중단

**구현 위치**: `_chooseActionImpl` 상단 분기 (~30줄). pm29 β v2d 로직은 case 1(1+1) 경우에만 발동.

---

## pm31 의사결정 체크리스트

다음 세션 시작 시 아래 순서로 정리:

### [ ] Q1. 다음 메인 방향 선택
- [ ] A (data-rule expansion) 먼저 + 시간 되면 B
- [ ] B (CEM 학습) 단독
- [ ] C (αβ search) 단독
- [ ] **Opp config 분기 먼저** (간단, 1-2h) + 그 후 A/B/C 결정
  - 현재 가장 적합해 보임. β 발동 조건을 1+1로 제한하면 2-def/2-att에서의 낭비 제거. 그 뒤 1+1 내부 chase 로직 개선.

### [ ] Q2. C 선택 시 defender 모델
- [ ] Greedy 추격 (간단, baseline 전용)
- [ ] Pessimistic reachability (과보수, rc82/166 regression 재현 위험)
- [ ] Observation-based 4-classifier (rc46 패러다임, 복잡하지만 robust) — **추천**

### [ ] Q3. UNSAFE layout chase
- pm30 scope-cut (차기 세션). 비안전 capsule도 런타임 판정으로 먹기.
- Opp config 분기와 orthogonal (병행 구현 가능).

### [ ] Q4. DISTANT layout 개선 (pm30 남긴 약점)
- rc82 distant 50%, rc47 distant 30T structural deadlock 등
- Phase 3 DEFAULT_RISK_WEIGHTS 튜닝, Agent B 사전-midline, scared trip 길이 조절 등
- Opp config 분기가 해결하는 측면도 있을 것 (distant에서 상대 2-att였다면 잘못 chase 발동한 사례 있을 수)

---

## pm31 시작 시 필수 체크

```bash
# 1. Context
cat .omc/SESSION_RESUME.md          # pm30 END 요약
cat .omc/plans/pm31-strategy-kickoff.md  # 이 파일

# 2. 현재 β 상태
git log --oneline -5                # f662ce5 pm30 CLOSE 최신
cat minicontest/zoo_reflex_rc_tempo_beta.py | head -50

# 3. 성능 data
# smoke 660g current / v2a / v2a2 / v2d: experiments/artifacts/rc_tempo/smoke_pm30_*.csv
# HTH 2000g v2d: experiments/artifacts/rc_tempo/hth_beta_pm30.csv
```

---

## 약속

**pm31 세션 시작 시 첫 액션**: 이 문서 읽고 유저에게 **Q1~Q4 순서대로 물어서 결정**. 결정 후 구현 진입.

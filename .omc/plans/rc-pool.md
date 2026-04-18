# Round-robin Candidate Pool (rc##)

**Purpose**: Phase 4 라운드로빈 토너먼트에 올릴 후보 다양화. Mac 병렬 개발용 기법 목록.
**Created**: 2026-04-19 pm22 end
**Status at creation**: A1(17dim) champion (baseline 79%, Wilson LB 0.728). Order 3/4 돌아가는 중.

---

## 🎯 명명 규칙

- `rc01` ~ `rc##`: round-robin candidate (이 문서 항목)
- pm은 "session timeline" prefix (pm22 = 22번째 세션). rc는 **작업 항목** prefix.
- 한 rc가 여러 세션에 걸칠 수 있음.

## 📏 제약 (모든 rc 공통)

- **제출**: `numpy + pandas` only. torch/sklearn/tf 등 X.
- **Turn**: 1 sec/turn (3회 초과 warn, 3 sec 초과 forfeit)
- **Init**: 15 sec (`registerInitialState`)
- **Game**: 1200 move max
- **Team**: 4v4 (2 Pacman + 2 Ghost, role-switch 가능)
- **Training compute**: RTX 4090 24GB 서버 (GPU 학습은 OK, 추론은 numpy)
- **수정 금지 파일**: `baseline.py`, `capture.py`, `captureAgents.py`, `game.py`, `layout.py`, `util.py`, `distanceCalculator.py`, `keyboardAgents.py`, `mazeGenerator.py`, `textDisplay.py`, `graphicsDisplay.py`, `captureGraphicsDisplay.py`, `graphicsUtils.py`

---

## 🏆 Tier 1 — 즉시 구현 가능 (no training, 각 < 8h)

| ID | 기법 | 카테고리 | 난이도 | 예상 | 비고 |
|---|---|---|---|---|---|
| **rc01** | D-series hand-rules (D1 role-swap, D2 capsule-timing, D3 endgame, D4 dead-end-guard) | F1 | L | 6h | A1 champion 위에 layer. 확정적. |
| **rc02** | Articulation Point / Bridge / Biconnected 방어 | Gemini#1+Codex | M | 4h | Tarjan algorithm, init 15sec에 전처리 |
| **rc03** | Dead-end Trapping | Gemini#2 | L | 3h | 깊은 dead-end 입구 봉쇄 100% 킬 |
| **rc04** | Hungarian / Min-cost Flow task allocation | Codex | L | 4h | 역할 중복 제거, 음식/patrol 할당 |
| **rc05** | Prospect Theory Risk Adjustment | Gemini#8 | L | 2h | carrying 많을수록 risk aversion 지수증가 |
| **rc06** | Resource Denial (청야 전술) | Gemini#7 | L | 3h | 초반 아군 경계선 음식 선소비 |
| **rc07** | Sacrificial Decoy (카미카제) | Gemini#13 | L | 4h | 한 agent 희생 + 본대 득점 |
| **rc08** | Dynamic Lane Assignment | Gemini#6 | L | 4h | 4v4 zone defense 스왑 |
| **rc09** | G1 추가 Feature (23-dim) | (기존) | L | 3h | f_enemyDistToHome, f_ourCarrierDist, f_capsuleProximity, f_chokePoint |
| **rc10** | G3 Role-conditioned input | (기존) | L | 2h | one-hot (offense/defense) input 추가 |
| **rc11** | Border Juggling (Trojan Horse) | Gemini#3 | L | 3h | 경계선에서 Pacman↔Ghost 전환 |
| **rc12** | Transposition Table (for minimax) | H1 | L | 4h | hash cache, depth+1~2 효과 |
| **rc13** | Iterative Deepening (for minimax) | H2 | L | 3h | 1sec 타임박스 동적 depth |
| **rc14** | Killer Heuristics / Move Ordering | H3 | L | 2h | alpha-beta 효율 2~4배 |
| **rc15** | F2 Ensemble Voting (A1 + O2 + D-variants) | F2 | M | 4h | 1sec 예산 실측 필수 |

---

## 🥈 Tier 2 — 중간 난이도 (some training or tuning, 각 1~2일)

| ID | 기법 | 카테고리 | 난이도 | 예상 | 비고 |
|---|---|---|---|---|---|
| **rc16** | Voronoi 영역 제어 | L1 | M | 1일 | 격자 최단거리 지배 영역 계산 |
| **rc17** | Influence Map (위험/기회 heatmap) | L2 | M | 1일 | 가우시안 blur 확산 |
| **rc18** | History Features (최근 N턴 메모) | L3 | L | 4h | 재귀 없이 메모리 흉내 |
| **rc19** | Mode-based Policy (opening/mid/endgame) | L4 | M | 1일 | game phase 판단 + 다른 weights |
| **rc20** | Flow Field Pathfinding | L5 | M | 1일 | multi-target A* 대체 |
| **rc21** | Layout Clustering (width/corridor/capsule pattern) | L10 | M | 1일 | layout detect + weights swap |
| **rc22** | E1/E2 Policy Distillation (teacher=A1/O2, student=small MLP) | E1 | M | 1.5일 | GPU 학습 → numpy distill |
| **rc23** | A3 Coevolutionary CEM (공격 pop ↔ 수비 pop) | A3 | M | 2일 | 서로 elite 대상 학습 |
| **rc24** | G2 Particle Filter Opponent Belief | G2 | M | 1일 | 보이지 않는 적 추적 |
| **rc25** | Quiescence Search (minimax 확장) | H4 | M | 1일 | horizon effect 완화 |
| **rc26** | MCTS-RAVE / UCB1-Tuned | H5 | M | 1일 | sibling 정보 공유 |
| **rc27** | Stigmergy / Virtual Pheromones | Gemini#11 | M | 1일 | numpy 배열 페로몬 decay |
| **rc28** | Boids-inspired Swarm Cohesion | Gemini#12 | M | 4h | Sep/Align/Cohesion 규칙 |
| **rc29** | Search-Depth Disruption (Stop/back moves) | Gemini#15 | M | 4h | 적 minimax 트리 교란 |
| **rc30** | Particle-Filter Blinding | Gemini#16 | M | 6h | 적 belief 분산 터뜨림 |
| **rc31** | Aggro-Juggling & Kiting | Gemini#4 | M | 1일 | MOBA 탱커 스타일 |
| **rc32** | Pincer Maneuver (다경로 포위) | Gemini#5 | M | 6h | A* 1,2순위 동시 사용 |
| **rc33** | Persona-shifting Agent (Bully/Ghost/Coward) | Gemini#17 | M | 1일 | 상황별 페르소나 전환 |
| **rc34** | Pavlovian Feinting (패턴 오염) | Gemini#10 | M | 1일 | 적 학습 교란 |
| **rc35** | Rollout Policy Iteration (classical) | I1 | M | 1일 | numpy-friendly |
| **rc36** | Dyna-Q (실+모의 경험) | I2 | M | 1.5일 | Q-learning sample efficient |
| **rc37** | Novelty Search (diversity-based selection) | J3 | M | 1.5일 | local optima 탈출 |
| **rc38** | MAP-Elites (Quality Diversity) | J4 | M | 2일 | 특성공간 위 diverse archive |
| **rc39** | Differential Evolution | J2 | L | 1일 | CEM 대안 |
| **rc40** | Bayesian Optimization (GP 기반) | J5 | M | 1.5일 | sample-efficient 탐색 |
| **rc41** | SARSA / Expected SARSA | K1 | M | 1일 | on-policy Q |
| **rc42** | Double Q-learning | K3 | M | 1일 | overestimation bias 제거 |
| **rc43** | TD(λ) with Eligibility Traces | K2 | M | 1.5일 | TD-Gammon 스타일 |
| **rc44** | N1 Stacking (meta-learner) | N1 | M | 1일 | base policies 확률 → 메타 분류 |
| **rc45** | N3 Weighted Voting (learned weights) | N3 | L | 4h | validation 기반 가중치 |
| **rc46** | **Online Opponent Type Classifier** ⭐ | new | M | 1~2일 | 초기 50~100 move 통계 → K-cluster 분류 → counter-policy switch (user 제안) |
| **rc47** | Engine-grade Alpha-Beta Package (PVS+aspiration+LMR+history) | Codex | M | 1.5일 | 기존 minimax 급상승 |
| **rc48** | WHCA* / Reservation-table MAPF | Codex | M | 1일 | cooperative A* + 충돌 방지 |
| **rc49** | SIPP + D* Lite / LPA* incremental replanning | Codex | M | 1.5일 | 시간축 안전구간 + incremental |
| **rc50** | Opening Book / Endgame Table | H6 | L | 6h | 초반 symmetric layout 최선수 사전계산 |

---

## 🥉 Tier 3 — 고난이도 (multi-day, 리스크 있음)

| ID | 기법 | 카테고리 | 난이도 | 예상 | 비고 |
|---|---|---|---|---|---|
| **rc51** | C4 ExIt (MCTS teacher → NN student) | C4 | H | 2일 | self-play + distill loop |
| **rc52** | B1 Q-learning v3 (진짜 학습, replay buffer + SGD) | B1 | M | 2일 | zoo_approxq 살리기 |
| **rc53** | A2 CMA-ES with restarts (IPOP-CMA-ES) | A2 | M | 2일 | covariance + restart |
| **rc54** | J2 NEAT (evolve network topology) | J2 | H | 3일 | numpy 구현 많이 필요 |
| **rc55** | Re-determinizing IS-MCTS | Codex | M | 2일 | information set MCTS |
| **rc56** | POMCP (particle belief + UCT) | Codex | M | 2일 | online POMDP planner |
| **rc57** | Vec-QMDP / QMDP-FIB hybrid | Codex | M | 2일 | belief-space fallback |
| **rc58** | Factored MCTS / Coord-Graph UCT | Codex | H | 3일 | branching factor 감소 |
| **rc59** | Reward Machines / Automata-guided RL | Codex | M | 2일 | FSM 목표 분해 |
| **rc60** | Difference Rewards / Aristocrat Utility | Codex | M | 1.5일 | counterfactual credit assignment |
| **rc61** | C3 AlphaZero-lite (MCTS + policy/value net + self-play) | C3 | H | 5일 | 가장 ambitious, safety net |
| **rc62** | K4 Distributional RL (C51, QR-DQN) | K4 | H | 3일 | 리턴 분포 학습 |
| **rc63** | K5 SAC (entropy-regularized actor-critic) | K5 | H | 3일 | exploration 자동 |
| **rc64** | D3 CTDE MAPPO | D3 | H | 4일 | 4v4 centralized training |
| **rc65** | Recursive Theory of Mind L2 | Gemini#9 | H | 2일 | 적 시뮬 내 실행 |
| **rc66** | Vision-Edge Surfing (거리 6 유지) | Gemini#14 | H | 2일 | 시야 악용 스텔스 |
| **rc67** | MCCFR / Outcome-Sampling CFR | Codex | H | 3일 | 근사 Nash |
| **rc68** | DESPOT-lite | Codex | H | 3일 | sparse belief tree + regularization |
| **rc69** | I-POMDP Lite (opponent intent latent) | Codex | H | 3일 | 의도 타입까지 latent |
| **rc70** | I1 MuZero-lite (world model + MCTS) | I1 | H | 5일 | 가장 복잡, 연구급 |

---

## 📚 Tier 4 — Recent Papers (2023~2026 RL advances)

| ID | 기법 | Paper | 난이도 | 예상 | 비고 |
|---|---|---|---|---|---|
| **rc71** | TAR² (2025) | arxiv.org/abs/2502.04864 | M | 2일 | 시간·agent축 credit redistribution |
| **rc72** | DrS (ICLR 2024) | arxiv.org/abs/2404.16779 | M | 2일 | sparse→dense stage reward |
| **rc73** | ARES (2025) | arxiv.org/abs/2505.10802 | M | 2일 | attention-based dense shaping |
| **rc74** | DIRECT (2023) | arxiv.org/abs/2301.07421 | M | 2일 | discriminator-based surrogate reward |
| **rc75** | E5 Meta-Learning (MAML/Reptile) | classical | H | 3일 | 빠른 layout adaptation |

---

## 🧪 Tier 5 — 압축 / 보조 (결과물 최적화)

| ID | 기법 | 난이도 | 예상 | 비고 |
|---|---|---|---|---|
| **rc76** | M2 Pruning + Quantization | L | 1일 | 학습한 net → int8 compress |
| **rc77** | M3 Ensemble Distillation | M | 1일 | N teacher → 1 student |
| **rc78** | M4 Lottery Ticket Hypothesis | M | 2일 | sub-network 추출 |
| **rc79** | N2 Boosting (AdaBoost) | M | 1일 | 순차적 error fix |
| **rc80** | N4 Gating Network (MoE 완성형) | M | 1.5일 | state-dependent expert select |

---

## 📊 카테고리 요약

| 카테고리 | 개수 | 대표 |
|---|---|---|
| Hand-rule/휴리스틱 | 12 | rc01, rc02, rc03, rc05, rc06, rc07, rc08, rc11 |
| Search 고도화 | 8 | rc12, rc13, rc14, rc25, rc26, rc47, rc48, rc50 |
| Evolution 변종 | 7 | rc23, rc37, rc38, rc39, rc40, rc53, rc54 |
| RL (on-policy/off-policy) | 7 | rc41, rc42, rc43, rc52, rc62, rc63, rc64 |
| Multi-agent coordination | 6 | rc04, rc27, rc28, rc58, rc64 |
| Ensemble/Meta | 5 | rc15, rc44, rc45, rc77, rc80 |
| Distillation/Compression | 5 | rc22, rc51, rc76, rc77, rc78 |
| POMDP/Imperfect-info | 6 | rc24, rc55, rc56, rc57, rc67, rc68, rc69 |
| Feature/Representation | 3 | rc09, rc10, rc18 |
| Opponent modeling | 4 | rc29, rc30, rc34, rc46 |
| Recent papers | 5 | rc71~rc75 |
| Creative/Unconventional | 6 | rc31, rc32, rc33, rc65, rc66 |

---

## 🚦 다음 세션 추천 실행 순서

**Day 1** (즉시): Tier 1 Quick Wins — rc01, rc02, rc03, rc04, rc05
**Day 2**: Tier 1 연속 — rc09, rc10, rc15, rc12, rc13, rc14
**Day 3**: Tier 2 학습 필요한 것 — rc22 (distillation), rc23 (coev), rc46 (opponent classifier ⭐)
**Day 4~5**: Tier 2 나머지 선택 — rc16, rc17, rc19, rc24, rc33
**Day 6~7**: Tier 3 고위험 — rc51, rc52, rc61 중 1~2개
**Day 8**: Phase 4 tournament (모든 rc 다 돌림)
**Day 9**: Phase 5 validation
**Day 10**: Report + zip

### 각 rc 평가 기준 (Go/No-go)

- **vs baseline**: 40게임에서 WR ≥ 30% (심하게 나쁘면 skip)
- **vs A1**: 20게임에서 WR ≥ 30% (일부 패배 OK, 다양성 목적)
- **리소스**: 1sec/turn 통과 (crash-proof)
- **코드 크기**: submission에 넣을 후보는 flatten 가능해야

---

## 🔗 관련 문서

- `.omc/STATUS.md` — 전체 milestone 상태
- `.omc/SESSION_RESUME.md` — 세션 시작용 5분 onboarding
- `.omc/plans/STRATEGY.md` — 원래 마스터 plan
- `.omc/plans/open-questions.md` — 미해결 stretch 질문
- `.omc/plans/autopilot-server-pipeline.md` — 서버 자동화
- `.omc/plans/pm22-autopilot-resume.md` — pm22 handoff (이번 세션 origin)
- `.omc/artifacts/ask/codex-*.md` — Codex advisor raw output (rc71~rc74, rc47~rc49 등)
- `.omc/artifacts/ask/gemini-*.md` — Gemini advisor raw output (rc02~rc08 등)

## 📝 변경 로그

- **2026-04-19 pm22 end**: 80개 후보 수집 완료. CCG advisor 2개 + user 제안 1개 + 기존 50개 통합.
- **2026-04-19 pm23 start**: rc01 (D-series) 이미 pm20에 구현·커밋·smoke PASS 확인.
  - Files: `zoo_reflex_A1_{D1,D2,D3,D13,T4,T5}.py` (commits 4e3baf7 ~ 7e699c5).
  - HTH 결과 (hth_t4_pm20.csv, 40g × 3 opps 각):
    - A1 (control) 82.5% baseline / 87.5% monster / 82.5% h1test
    - **D13 92.5% baseline / 82.5% monster / 97.5% h1test** (BEST candidate)
    - D1 85.0% / 85.0% / 87.5%
    - D2 85.0% / 80.0% / 87.5%
    - D3 75.0% / 82.5% / 82.5%
    - T4 77.5% / 77.5% / 87.5%
    - T5 (hth_t5 csv) 82.5% / 80.0% / 95.0%
  - 모두 30% 임계값 통과 → Phase 4 round-robin pool 전부 포함.
  - rc01 status: **DONE**. rc02 (Articulation Point) 시작.
- **2026-04-19 pm23 mid**: rc02~rc06 Mac 구현·smoke 완료.
  - **rc02** Tarjan AP defense: **40/40 (100%) vs baseline** — best new result this session.
  - **rc03** Dead-end trap: Red 20/20, Blue pending. Smoke 4/4 PASS.
  - **rc04** Hungarian food assignment (conflict-only v2): Red 19/20, Blue pending. Smoke 4/4 PASS. (v1 실패: 0/4. top-K 재랭킹 너무 공격적 → tol-frac + conflict-only 제약 추가 후 v2 PASS).
  - **rc05** Prospect-theory risk scaling: 4-game smoke 3/4. 40-game pending.
  - **rc06** Border food early resource denial: 4-game smoke 3W/1T/0L. 40-game pending.
  - Status: rc02 DONE; rc03, rc04, rc05, rc06 smoke PASS (40-game pending).
- **2026-04-19 pm23 rc2-rc8 40-game HTH results (vs baseline, 20 Red + 20 Blue)**:
  - **rc02** Tarjan AP: **40/40 = 100%** 🥇 (Red 20/20, Blue 20/20).
  - **rc03** Dead-end trap: **38/40 = 95%** (Red 20/20, Blue 18/20).
  - **rc04** Hungarian conflict-only v2: **35/40 = 87.5%** (Red 19/20, Blue 16/20).
  - **rc05** Prospect-theory risk: 40-game pending.
  - **rc06** Border food denial: 40-game pending.
  - **rc07** Kamikaze: SKIPPED pm23 (high-risk; revisit Day 2+).
  - **rc08** Lane assignment dual-invader: 40-game pending.
  - Baseline reference: A1 champion = 82.5% (pm20 hth_t4 Red+Blue). **rc02 > A1 by ~17.5pp**.
  - All implemented candidates pass 30% threshold → Phase 4 round-robin pool 포함.

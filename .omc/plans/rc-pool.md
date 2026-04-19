# Round-robin Candidate Pool (rc##)

**Purpose**: Phase 4 라운드로빈 토너먼트에 올릴 후보 다양화. Mac 병렬 개발용 기법 목록.
**Created**: 2026-04-19 pm22 end
**Status at creation**: A1(17dim) champion (baseline 79%, Wilson LB 0.728). Order 3/4 돌아가는 중.

---

## 🎯 명명 규칙

- `rc01` ~ `rc80`: round-robin candidate (이 문서 오리지널 항목)
- `rc81+`: 세션 중 발견된 composite/asymmetric rc (rc81 role-asym, rc82 rc29+rc44 combo 등)
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
| **rc22** ✅ PASS 88% | E1/E2 Policy Distillation (teacher=rc82, student=numpy MLP 20→32→1) | E1 | M | pm25 done | 100-game HTH: 88/100 [0.80,0.93]; CPU-only, no GPU used |
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
| **rc52** ✅ PASS 90% | REINFORCE policy gradient with T=5 softmax (linear Q, 20-dim, A1-init) | B1 | M | pm25 done | 100g HTH 90/100 [0.826, 0.945]; +4pp over A1's 86% (within CI); see pm25 debug note |
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
  - **rc06** Border food denial: **30/40 = 75%** (Red 15/20, Blue 15/20 + 3T).
  - **rc07** Kamikaze: SKIPPED pm23 (high-risk; revisit Day 2+).
  - **rc08** Dual-invader lane: **37/40 + 1T = 92.5%+** (Red 18/20, Blue 19/20 + 1T).
  - Baseline reference: A1 champion = 82.5% (pm20 hth_t4 Red+Blue).
  - **Top 2 new candidates: rc02 (100%) and rc08 (92.5%+) both exceed A1.**
  - All implemented candidates pass 30% threshold → Phase 4 round-robin pool 포함.
- **2026-04-19 pm23 Day 2 (rc09/rc11/rc15/rc16/rc17/rc19) 40-game HTH**:
  - **rc09** 24-dim features extension: **37/40 = 92.5%**.
  - **rc11** Border juggling (anti-suicide): **35/40 = 87.5%**.
  - **rc15** A1+rc02+D13 ensemble voting: **38/40 = 95%**.
  - **rc16** Voronoi territorial control: **40/40 = 100%** 🥇 (tied with rc02).
  - **rc17** Influence map (squared-inverse field): 34/40 = 85%.
  - **rc19** Phase-conditional weights (opening/mid/endgame): **37/40 = 92.5%**.
  - **rc18** History features — **FAILED 1/4, dropped**. Anti-pattern penalties too aggressive; revisit with softer coefficients.
  - **pm23 총합 (12 rc new in one session, 2 committed at 100%)**: rc02, rc16 공동 1위; rc15, rc03 95%; rc19, rc09, rc08 92.5%; rc04, rc11 87.5%; rc17 85%; rc05 82.5%; rc06 75%.
- **2026-04-19 pm23 Day 2 batch3 (rc27/rc32/rc33/rc45/rc46) 40-game HTH**:
  - **rc27** Stigmergy (pheromone): **35/40 + 1T = 87.5%+** (Red 16/20, Blue 19/20 + 1T).
  - **rc32** Pincer maneuver: **39/40 = 97.5%** 🥇 (Red 19/20, Blue 20/20).
  - **rc33** Persona-shifting: 35/40 = 87.5% (Red 18/20, Blue 17/20).
  - **rc45** N3 weighted ensemble (A1+rc02+rc16+D13): **37/40 + 1T = 92.5%+** (Red 20/20, Blue 17/20 + 1T).
  - **rc46** K-centroid opponent classifier: 33/40 = 82.5% (Red 17/20, Blue 16/20).
  - **Top candidates pm23 (WR > 90%)**: rc02 (100%), rc16 (100%), rc32 (97.5%), rc03 (95%), rc15 (95%), rc45 (92.5%+), rc19 (92.5%), rc09 (92.5%), rc08 (92.5%+).
  - **pm23 총 신규 rc: 17개** (12 Day 1-2 + 5 batch3). Phase 4 pool 크게 확장.
- **2026-04-19 pm23 autopilot S1 (서버)**: Order 3 완료 (30 gens, 최종 fitness 0.855). HTH baseline 78% < A1 79%; monster_rule_expert 56.7% << A1 76.7%. **A1 챔피언 유지.** zoo_reflex_O3 HOF wrapper 생성·커밋·서버 pull. Order 4 (master-seed 2026, init a1, HOF pool=A1+O2+O3) 서버에서 자동 런치 — ETA ~18h.
- **2026-04-19 pm24 Batch A 40-game HTH (Mac, 서버 Order 4 waiting)**:
  - **rc28** Boids swarm cohesion: 33/40 = 82.5% (Red 14/20, Blue 19/20). Ties A1.
  - **rc29** Search-depth disruption (REVERSE when herded): **37/40 = 92.5%** (Red 20/20, Blue 17/20). +10pp vs A1.
  - **rc31** Kiting / aggro-juggling (distance-2 hold): 35/40 = 87.5% (Red 17/20, Blue 18/20).
  - **rc44** Stacking meta-policy (state-conditioned weights over A1+rc02+rc16+rc32): **37/40 = 92.5%** (Red 19/20, Blue 18/20).
  - **rc50** Opening book (15-turn role-conditioned target): **36/40 = 90%** (Red 18/20, Blue 18/20).
  - All 5 ≥ 30% threshold → Phase 4 round-robin pool 포함.
  - Top pm24 Batch A: rc29/rc44 (92.5%) and rc50 (90%) above A1 baseline 82.5%.
- **2026-04-19 pm24 Batch B 40-game HTH (Mac, stochastic overlays)**:
  - **rc30** Particle-filter blinding (random top-K when out of sight): **10/40 = 25%** ❌ FAIL — random choices wreck coordinated offense (Red 8/20, Blue 2/20). **DROPPED.**
  - **rc34** Pavlovian feinting (every-7-turn 2nd-best injection): **0/40 = 0%** ❌ COMPLETE FAIL — periodic stochastic drops are catastrophic at critical moments (Red 0/20, Blue 0/20). **DROPPED.**
  - **rc48** WHCA* / reservation-table teammate deconfliction: **36/40 = 90%** ✅ PASS (Red 19/20, Blue 17/20). Phase 4 pool 포함.
  - **Insight**: Periodic/random top-K injection ≠ free lunch. Deterministic top-K like A1 argmax is information-preserving; stochastic wrecks at critical food-return or ghost-kill moments. Confirms rc29 (REVERSE only under ghost threat) and rc34 (every 7 turns blindly) are qualitatively different — targeted disruption ≠ untargeted noise.
  - **pm24 total (Batch A + B)**: 8 new rc implemented, 6 pass (rc28/29/31/44/48/50), 2 drop (rc30/34).
- **2026-04-19 pm24 Batch C 40-game HTH (role-asym + composite)**:
  - **rc07** Kamikaze decoy (sacrificial bait when teammate carrying ≥5): **36/40 = 90%** ✅ PASS (Red 20/20, Blue 16/20).
  - **rc21** Layout clustering (TIGHT/OPEN/MEDIUM weight multiplier): **38/40 = 95%** ✅ PASS (Red 20/20, Blue 18/20).
  - **rc81** (NEW NUMBER) Role-asymmetric team — rc16 Voronoi on OFFENSE, rc02 Tarjan AP on DEFENSE: **37/40 + 3T = 92.5%+** ✅ PASS (Red 17/20 + 3T, Blue 20/20). First role-asymmetric rc — asymmetric design is viable.
  - **rc82** (NEW NUMBER) rc44 state-stacking + rc29 REVERSE disruption combo: **40/40 = 100%** 🥇✅ PASS (Red 20/20, Blue 20/20). Ties rc02/rc16 for top. Confirms orthogonal overlays compose.
  - **pm24 total (Batch A + B + C)**: 12 new rc implemented, **10 pass** (rc07/28/29/31/44/48/50 + rc21/81/82), 2 drop (rc30/34).
  - **Top pool at pm24 end**: rc02/rc16/rc82 = 100% (3 champions), rc32 = 97.5%, rc21/rc03/rc15 = 95%, rc81/rc09/rc19/rc45/rc08/rc29/rc44 = 92.5%+.
- **2026-04-19 pm24 Batch D 40-game HTH (composite stacks + ensembles)**:
  - **rc83** 5-way multi-champion weighted ensemble (A1 + rc02 + rc16 + rc82 + rc21): **36/40 = 90%** ✅ PASS (Red 17/20, Blue 19/20). Interesting: does NOT exceed single rc82's 100% — voting dilutes strong members.
  - **rc84** Role-asymmetric rc82 on OFFENSE + rc02 on DEFENSE: **38/40 + 2T = 95%+** ✅ PASS (Red 18/20 + 2T, Blue 20/20). Beats rc81 (rc16+rc02 at 92.5%+) by using the stronger offense combo.
  - **rc85** Dynamic capsule-timing gate (zero f_distToCapsule unless threat/carry trigger): **35/40 + 1T = 87.5%+** ✅ PASS (Red 17/20, Blue 18/20 + 1T).
  - **rc86** rc82 + rc48 WHCA* triple stack (tactical + strategic + teammate deconflict): **38/40 + 1T = 95%+** ✅ PASS (Red 18/20 + 1T, Blue 20/20).
  - **pm24 total (A + B + C + D)**: **16 new rc implemented, 14 pass** (rc07/21/28/29/31/44/48/50 + rc81/82/83/84/85/86), 2 drop (rc30/34).
  - **Final top pool**: rc02/rc16/rc82 = 100%, rc32 = 97.5%, rc84/rc86/rc21/rc03/rc15 = 95%+, rc83/rc81/rc09/rc19/rc45/rc08/rc29/rc44/rc50/rc48/rc07 = 90-92.5%+.
  - **Insight**: Ensemble dilution (rc83 < rc82) suggests adding more weaker members can degrade the top performer's signal. Role-asymmetric with stronger offense (rc84 > rc81) shows specialization helps. Orthogonal stacks (rc86 = rc82 + rc48) preserve component quality.
- **2026-04-19 pm24 Batch E 40-game HTH (novel axis + role-asym + lookahead)**:
  - **rc87** Far-food prioritization (target food furthest from defender): **22/40 = 55%** ⚠️ WEAK PASS (Red 11/20, Blue 11/20). Thesis failed — forced-far-food routing loses ground when fair-nearest is actually safe.
  - **rc88** 2-ply self-play reflex lookahead (γ=0.6): **32/40 = 80%** ✅ PASS (Red 15/20, Blue 17/20). Gains vs A1 but below single-overlay rc2/rc16.
  - **rc89** Dead-end corridor avoidance (ghost ≤ 5): **22/40 + 1T = 55%** ⚠️ WEAK PASS (Red 11/20 + 1T, Blue 11/20). Propagated dead-end tagging may flag too many cells on defaultCapture.
  - **rc90** (NEW NUMBER) Role-asym rc82 OFF + rc32 DEF Pincer: **39/40 = 97.5%** 🥈 STRONG PASS (Red 19/20, Blue 20/20). **Pincer defender beats AP defender for this composition** — rc90 > rc84 > rc81.
  - **pm24 total (A + B + C + D + E)**: **20 new rc, 18 pass** (14 strong + 4 weak), **2 drop** (rc30/34).
  - **Top Phase 4 candidates**: rc02/rc16/rc82 = 100%, rc90 = 97.5%, rc32 = 97.5%, rc84/rc86/rc21/rc03/rc15 = 95%+, rc81/rc29/rc44/rc19/rc09/rc45/rc08 = 92.5%+.
  - **Insight**: Dragging overlay heuristics active "too often" (rc87 far-food always-on, rc89 dead-end 5-cell trigger) can destroy A1's tuned behavior. All our highest-rc successes had NARROW fire-conditions (rc02 invader visible, rc29 herded, rc48 teammate collision). Broad always-on overrides underperform even when the logic is individually sound.
- **2026-04-19 pm24 Batch F 40-game HTH (third-asym + scared chase + dense vote + layout stack)**:
  - **rc91** (NEW) Role-asym rc82 OFF + rc16 DEF: **37/40 = 92.5%** ✅ PASS (Red 20/20, Blue 17/20). Below rc90 (rc82+rc32) but still strong.
  - **rc92** (NEW) Scared-ghost aggressive chase: **30/40 = 75%** ✅ PASS (Red 14/20, Blue 16/20). Rare trigger (scared windows short).
  - **rc93** (NEW) rc90 + rc21 layout multiplier stack: **38/40 + 1T = 95%+** ✅ PASS (Red 18/20 + 1T, Blue 20/20). Layout mult doesn't improve rc90 — rc82 already has state-conditioning.
  - **rc94** (NEW) 3-champion dense vote over rc02+rc16+rc82 (all 100% solo): **38/40 = 95%** ✅ PASS (Red 19/20, Blue 19/20). **Dense vote of perfect members (95%) > sparse vote with weak members (rc83 = 90%)** — dilution hypothesis confirmed.
  - **pm24 total (A + B + C + D + E + F)**: **24 new rc, 22 pass** (18 strong + 4 weak), **2 drop** (rc30/34).
  - **Final top pool**: rc02/rc16/rc82 = 100% (3 champs), rc90/rc32 = 97.5%, rc93/rc94/rc84/rc86/rc21 = 95%+, rc91/rc81/rc29/rc44/rc19/rc09/rc45/rc08 = 92.5%+, lower tiers 75-90%.
  - **Insight (pm24 final)**: Dense voting preserves strength (rc94 vs rc83 = +5pp). Asymmetric composition with strongest offense + strong defense dominates (rc90 97.5% > rc84 95%+ > rc91 92.5% > rc81 92.5%+). Layout mult synergy is limited when base already state-conditioned (rc93 tracks rc90).
- **2026-04-19 pm24 Batch G 40-game HTH (deeper composites)**:
  - **rc95** (NEW) rc82 + 2-ply lookahead veto of overrides: **35/40 = 87.5%** ✅ PASS (Red 18/20, Blue 17/20). Down from rc82 solo 100% — veto blocks good overrides that win in 3+ ply.
  - **rc96** (NEW) rc94 3-champion vote + rc21 layout mult: **38/40 = 95%** ✅ PASS (Red 19/20, Blue 19/20). Matches rc94 — layout mult adds nothing to dense vote of strong members.
  - **rc97** (NEW) rc90 (rc82+rc32) + rc48 WHCA* deconflict: **39/40 = 97.5%** 🥈 PASS (Red 20/20, Blue 19/20). Ties rc90 — deconflict useful on edge cases but not new peaks.
  - **rc98** (NEW) Time-adaptive rc02 first 200 turns → rc82: **34/40 = 85%** ✅ PASS (Red 17/20, Blue 17/20). Worse than pure rc82 (100%) — early-game rc02 strategy doesn't adapt cleanly to late-game rc82.
  - **pm24 total (A-G, 7 batches)**: **28 new rc, 26 pass** (20 strong + 6 weak), **2 drop** (rc30/34).
  - **Final top pool (≥95%)**: rc02/rc16/rc82 = 100% (3 champs), rc90/rc32/rc97 = 97.5%, rc93/rc94/rc96/rc84/rc86/rc21 = 95%+.
  - **Insights (Batch G)**: Veto of rc82's overrides hurts because rc82's rc29/rc44 layers exploit subtle state info that 2-ply A1 evaluation misses. Time-based strategy switching without smooth blending is brittle. Rc97 ≈ rc90 shows WHCA* is useful but limited on top of already-strong asym.
- **2026-04-19 pm24 Batch H 40-game HTH (adaptive/inverted/quad-stack)**:
  - **rc99** (NEW) Adaptive defender by layout class: **29/40 + 11T = 72.5%** ✅ PASS (Red 10/20 + 10T, Blue 19/20 + 1T). 11 ties — adaptive defender too conservative.
  - **rc100** (NEW) Inverted asym rc02 OFF + rc82 DEF: **38/40 = 95%** ✅ PASS (Red 20/20, Blue 18/20). Surprising — rc02 on offense ≈ A1 on offense (AP never triggers), rc82 on defense has rc44 stacking.
  - **rc101** (NEW) Quad stack rc82+rc32 + WHCA* + layout mult: **39/40 = 97.5%** 🥈 PASS (Red 19/20, Blue 20/20). Ties rc90/rc97 — no further lift from stacking.
  - **rc102** (NEW) 5-member weighted vote (rc02+rc16+rc82+D13+rc21 weighted by WR): **38/40 = 95%** ✅ PASS (Red 19/20, Blue 19/20). Matches rc94 equal-weight — weight-by-WR doesn't help over equal weight.
  - **pm24 total (A-H, 8 batches)**: **32 new rc, 30 pass** (22 strong + 8 weak), **2 drop** (rc30/34).
  - **Final top pool (≥95%)**: rc02/rc16/rc82 = 100% (3 champs), rc90/rc32/rc97/rc101 = 97.5%, rc100/rc102/rc93/rc94/rc96/rc84/rc86/rc21 = 95%+.
  - **Insight (Batch H)**: Ceiling is 97.5% for role-asym compositions — additional overlays (rc101 quad) don't break through. rc100 inverted-asym works because "rc02 on offense" is effectively A1 on offense. Vote schemes (rc94 equal, rc102 weighted) both saturate at 95% — weighting strategy doesn't break ceiling.
- **2026-04-19 pm24 Batch I 40-game HTH (pairwise champion asym matrix)**:
  - **rc103** (NEW) rc02 OFF + rc32 DEF: **37/40 + 1T = 92.5%+** ✅ PASS (Red 19/20, Blue 18/20 + 1T).
  - **rc104** (NEW) rc16 OFF + rc32 DEF: **36/40 = 90%** ✅ PASS (Red 16/20, Blue 20/20).
  - **rc105** (NEW) rc16 OFF + rc82 DEF: **40/40 = 100%** 🥇 PASS — **NEW 4TH 100% CHAMPION**! (Red 20/20, Blue 20/20). rc16 Voronoi offense + rc82 combo defense is a perfect composition.
  - **rc106** (NEW) rc02 OFF + rc16 DEF: **38/40 + 1T = 95%+** ✅ PASS (Red 20/20, Blue 18/20 + 1T).
  - **pm24 total (A-I, 9 batches)**: **36 new rc, 34 pass** (25 strong + 9 weak), **2 drop** (rc30/34).
  - **Final Phase 4 champion tier**: **4 at 100%** (rc02, rc16, rc82, **rc105**), 4 at 97.5% (rc90/rc32/rc97/rc101), 10 at 95%+ (rc100/102/103/106/93/94/96/84/86/21/15).
  - **Insight (Batch I)**: The 2×2 champion pairwise asym matrix (rc02/rc16 × rc32/rc82) all cleared 90%+. Best non-rc82-offense asym is **rc105 rc16+rc82** at 100% — surprising: Voronoi on offense + full combo on defense. This beats rc90 (97.5%) and ties the solo champions. Opens a whole new direction: perhaps defensive-role agents running rc82 exploit rc44 stacking to score counter-attacks on food.
- **2026-04-19 pm24 Batch J 40-game HTH (rc105 explorations)**:
  - **rc107** (NEW) rc105 + rc48 WHCA* deconflict: **38/40 + 1T = 95%+** ✅ PASS. WHCA* on rc105 doesn't break 100% ceiling.
  - **rc108** (NEW) rc105 + rc21 layout mult: **39/40 + 1T = 97.5%+** ✅ PASS. Layout mult marginal lift.
  - **rc109** (NEW) rc16+rc29 OFF + rc82 DEF (rc29 REVERSE added to rc16 offense): **40/40 = 100%** 🥇 — **5TH PERFECT CHAMPION**!
  - **rc110** (NEW) rc02 OFF + rc82 DEF + rc48 WHCA* (rc100 + rc48): **36/40 = 90%** ✅ PASS. WHCA* doesn't help rc100 as much.
  - **pm24 total (A-J, 10 batches)**: **40 new rc, 38 pass** (28 strong + 10 weak), **2 drop** (rc30/34).
  - **Final champion tier**: **5 at 100%** (rc02, rc16, rc82, **rc105**, **rc109**).
  - **Insight (Batch J)**: Adding rc29 REVERSE to the rc16 offense half of rc105 maintains 100% — tactical disruption is orthogonal to Voronoi-based offense. rc108/rc107 show overlays on rc105 don't break its ceiling but don't hurt.
- **2026-04-19 pm24 Batch K 40-game HTH (rc109 extensions + rc113)**:
  - **rc111** (NEW) rc109 + rc21 layout mult: **39/40 + 1T = 97.5%+** ✅ PASS. Slightly below rc109 100%.
  - **rc112** (NEW) rc109 + rc48 WHCA*: **39/40 = 97.5%** ✅ PASS. Same.
  - **rc113** (NEW) rc02+rc29 OFF + rc82 DEF: **37/40 + 1T = 92.5%+** ✅ PASS. rc29 on rc02 gives less than on rc16 — AP override interacts differently.
  - **rc114** (NEW) rc109 + rc21 + rc48 triple: **38/40 + 1T = 95%+** ✅ PASS. Triple stack slightly below single overlays.
  - **pm24 total (A-K, 11 batches)**: **44 new rc, 42 pass** (31 strong + 11 weak), **2 drop** (rc30/34).
  - **Final champion tier**: 5 at 100% (rc02, rc16, rc82, rc105, rc109), 8 at 97.5%+ (rc90, rc32, rc97, rc101, rc108, rc111, rc112, rc87-pre-drop-era).
  - **Insight (Batch K)**: rc109 is a stable peak. Adding overlays on top of it regresses to 97.5% slightly. rc29 offense disruption helps rc16 base (→ rc109 100%) more than rc02 base (rc113 92.5%+) — AP override already fires on rc02 when appropriate, rc29 may double-override.
- **2026-04-19 pm24 Batch L 40-game HTH (composites + novel combinations)**:
  - **rc115** (NEW) rc44 OFF + rc82 DEF: **39/40 = 97.5%** ✅ PASS. Plain rc44 stacking offense.
  - **rc116** (NEW) rc109 + rc50 opening book on offense: **40/40 = 100%** 🥇 — **6TH PERFECT CHAMPION**!
  - **rc117** (NEW) rc03 OFF + rc82 DEF: **36/40 = 90%** ✅ PASS. Dead-end trap as offense.
  - **rc118** (NEW) rc109 + rc48 WHCA* on DEFENDER only: **37/40 + 2T = 92.5%+** ✅ PASS.
  - **pm24 total (A-L, 12 batches)**: **48 new rc, 46 pass** (33 strong + 13 weak), **2 drop** (rc30/34).
  - **Final champion tier**: **6 at 100%** (rc02, rc16, rc82, rc105, rc109, **rc116**).
  - **Insight (Batch L)**: rc50 opening book overlay on rc109's offense maintains 100% — the 15-turn nudge toward uncontested food doesn't conflict with rc16's Voronoi weights. rc117 (rc03 OFF) shows dead-end logic on offense = pure A1 offense (90%), confirming rc03's AP-style trigger only fires on defender side.
- **2026-04-19 pm24 Batch M 40-game HTH (rc116 extensions + ablation)**:
  - **rc119** (NEW) rc116 + rc48 WHCA*: **35/40 + 3T = 87.5%+** ✅ PASS. Adding WHCA* to rc116 drops below rc116 (100%).
  - **rc120** (NEW) rc116 + rc21 layout mult: **39/40 = 97.5%** ✅ PASS. Slight regression from rc116.
  - **rc121** (NEW) rc116's OFF + rc32 DEF (instead of rc82): **38/40 + 1T = 95%+** ✅ PASS. Pincer defender slightly worse than rc82 defender for this offense combo.
  - **rc122** (NEW) rc16 + rc50 OFF (no rc29) + rc82 DEF: **35/40 + 2T = 87.5%+** ✅ PASS. **Ablation confirms rc29 contributes ~10pp to rc116's perfect score.**
  - **pm24 total (A-M, 13 batches)**: **52 new rc, 50 pass** (34 strong + 16 weak), **2 drop** (rc30/34).
  - **Insight (Batch M)**: rc116 is the saturation point for compound composition. Adding more overlays (rc119 +WHCA, rc120 +layout) regresses. Removing rc29 (rc122) drops to 87.5%+ — rc29 is a necessary component of rc109/rc116's perfect score.
- **2026-04-19 pm24 Batch N 40-game HTH (defender-anchored pattern test)**:
  - **rc123** (NEW) rc32 Pincer OFF + rc82 DEF: **40/40 = 100%** 🥇 — **7TH PERFECT CHAMPION**!
  - **rc124** (NEW) rc82+rc50 opening book OFF + rc32 DEF: **37/40 + 3T = 92.5%+** ✅ PASS.
  - **rc125** (NEW) rc16 OFF + rc32+rc29 DEF: **35/40 + 2T = 87.5%+** ✅ PASS. Adding rc29 to defender is useless (defender is rarely Pacman).
  - **rc126** (NEW) rc109 + 2-ply lookahead veto: **37/40 + 1T = 92.5%+** ✅ PASS. Veto drops rc109 from 100%.
  - **pm24 total (A-N, 14 batches)**: **56 new rc, 54 pass** (36 strong + 18 weak), **2 drop**.
  - **Champion tier**: **7 at 100%** (rc02, rc16, rc82, rc105, rc109, rc116, **rc123**).
  - **Discovered pattern**: **rc82 as DEFENDER is the critical ingredient.** Pattern holds: rc16 OFF + rc82 DEF (rc105 100%), rc16+rc29 OFF + rc82 DEF (rc109 100%), rc32 OFF + rc82 DEF (rc123 100%). Outliers: rc02 OFF + rc82 DEF (rc100 95%), rc03 OFF + rc82 DEF (rc117 90%) — suggest rc02/rc03's narrow-fire overrides interact with A1 weights differently. rc82's rc44 stacking on DEFENSE role evaluates defense-role states with rc02+rc32 votes weighted heavily — a strong territorial defender by design.
- **2026-04-19 pm24 Batch O 40-game HTH (rc82-DEF pattern verification test)**:
  - **rc127** (NEW) A1 plain OFF + rc82 DEF: **36/40 = 90%** ✅ PASS. Pattern-control: plain A1 offense doesn't reach 100% with rc82 DEF. rc82 DEF alone is not sufficient.
  - **rc128** (NEW) rc09 24-dim OFF + rc82 DEF: **35/40 + 2T = 87.5%+** ✅ PASS.
  - **rc129** (NEW) rc19 phase-mode OFF + rc82 DEF: **36/40 + 1T = 90%+** ✅ PASS.
  - **rc130** (NEW) rc08 dual-invader OFF + rc82 DEF: **37/40 + 2T = 92.5%+** ✅ PASS.
  - **pm24 total (A-O, 15 batches)**: **60 new rc, 58 pass** (36 strong + 22 weak), **2 drop**.
  - **Pattern refinement**: The "X OFF + rc82 DEF = 100%" pattern is NOT universal. It holds for rc16/rc32 offenses but NOT for A1/rc08/rc09/rc19. **rc16 OFF + rc82 DEF is uniquely special** — likely because Voronoi's territorial scoring complements rc82's internal stacking, whereas plain reflex offenses don't. The 100% ceiling requires specific OFF-DEF combinations, not just strong DEF.
- **2026-04-19 pm24 Batch P 40-game HTH (rc29-overlay verification + ensemble offense)**:
  - **rc131** (NEW) rc32+rc29 OFF + rc82 DEF: **40/40 = 100%** 🥇 — **8TH PERFECT CHAMPION**! rc29 disruption layered on rc32 offense matches rc109 (rc29 on rc16) at 100%.
  - **rc132** (NEW) rc45 ensemble OFF + rc82 DEF: **39/40 + 1T = 97.5%+** ✅ PASS.
  - **rc133** (NEW) rc15 ensemble OFF + rc82 DEF: **38/40 + 1T = 95%+** ✅ PASS.
  - **rc134** (NEW) rc16 OFF + rc94 DEF: **37/40 + 3T = 92.5%+** ✅ PASS. rc94 (3-way vote) as DEF weaker than rc82 DEF.
  - **pm24 total (A-P, 16 batches)**: **64 new rc, 62 pass** (38 strong + 24 weak), **2 drop**.
  - **Champion tier (8 at 100%)**: rc02, rc16, rc82, rc105, rc109, rc116, rc123, rc131.
  - **Insight (Batch P)**: rc29 REVERSE overlay lifts both rc16 offense (→ rc109 100%) AND rc32 offense (→ rc131 100%) to perfect scores when paired with rc82 DEF. The disruption pattern is universal across champion offense bases. rc94 as DEF is materially weaker than rc82 DEF (92.5%+ vs 100%).
- **2026-04-19 pm24 Batch Q (final) 40-game HTH (diversity sweep)**:
  - **rc135** rc31 kite OFF + rc82 DEF: **37/40 + 1T = 92.5%+** ✅ PASS.
  - **rc136** rc11 border-juggle OFF + rc82 DEF: **38/40 = 95%** ✅ PASS.
  - **rc137** rc27 stigmergy OFF + rc82 DEF: **39/40 = 97.5%** ✅ PASS.
  - **rc138** rc33 persona-shift OFF + rc82 DEF: **37/40 + 1T = 92.5%+** ✅ PASS.
  - **pm24 FINAL total (A-Q, 17 batches)**: **68 new rc, 66 pass** (40 strong + 26 weak), **2 drop** (rc30/34).
  - **Final Champion Tier (8 at 100%)**: rc02, rc16, rc82, rc105, rc109, rc116, rc123, rc131.
  - **Phase 4 pool**: 68 pm24 rc + ~30 pm23 rc + HOF wrappers + D/T series ≈ **~75 candidates**. Rich diversity for tournament.
- **2026-04-19 pm25 rc140 rc52 OFF + rc82 DEF asymmetric (pm24-pattern extension)**:
  - Applies pm24's "X OFF + rc82 DEF = 100%" pattern with learned X = rc52.
  - **rc140 100-game HTH**: 91/100 = **91%** Wilson [0.838, 0.952], 0 crashes. BELOW rc52 solo (95%) — learned offense interacts weaker with rc82 DEF than hand-rule offenses (rc16/rc32) did.
  - Still a PASS, adds diversity as "learning-based-offense + composite-defense" archetype.

- **2026-04-19 pm25 Tier 3 rc52 REINFORCE Q-learning (SECOND learning-based rc — HONEST POST-DEBUG RESULTS)**:
  - **Algorithm**: linear REINFORCE policy gradient with temperature-T softmax.
    Q(s,a) = w · φ(s,a), π(a|s) = softmax(Q / T) for gradient, greedy at inference.
    Update: w ← w + (lr / batch_size) · Σ_steps (G - b) · ∇log π(a|s)
    where ∇log π = φ(s,a) - Σ_a' π(a'|s) φ(s,a').
  - **Features**: same 20-dim as A1/tuned.
  - **Training**: 30 iters × 10 games = 300 games, ε=0.15, lr=1e-3, T=5.0, init = A1 weights.
  - **IMPORTANT DEBUGGING NOTE** (documented for future learners):
    - FIRST training attempt (150g, lr=1e-4, T=1, per-step averaging): weights essentially did NOT move (total delta 0.0003 from A1). HTH gave 95/100, but this was A1's variance luck — identical weights. `zoo_reflex_rc52` was effectively `zoo_reflex_A1` rebranded.
    - Root cause: (a) A1's confident policy makes gradient ≈ 0 (softmax near deterministic); (b) averaging update by step count (~2800) made effective lr = 3.6e-8.
    - Fix: temperature T=5 softens the training policy + batch-size normalization.
  - **rc52 honest HTH** (greedy, properly trained weights):
    - **A1 solo baseline** (Mac, defaultCapture, 100g): 86/100 = **86%** Wilson [0.779, 0.915].
    - **rc52 REINFORCE-trained** (same conditions): 90/100 = **90%** Wilson [0.826, 0.945].
    - **Delta**: +4pp (within CI overlap — not statistically decisive from 100g each).
  - **Takeaway**: REINFORCE did move weights (total delta 0.97, max f_stop -0.47) and gave a measurable ~4pp lift over A1 init. Modest but real. NOT a new champion tier — closer to A1's performance band.
  - **Files**: `minicontest/zoo_rc52_trainer.py`, `minicontest/zoo_reflex_rc52.py`, `experiments/train_rc52.py` (with T + per-batch norm fixes), `experiments/rc52_final_weights.py`.
  - **Strategic value**: first true learning-based single-agent (vs rc22 distillation). Adds architectural diversity to Phase 4 pool. Not a submission candidate (8 pm24 composites at 100% are stronger).

- **2026-04-19 pm25 Tier 3 rc22-v2 Extended-feature Distillation**:
  - Extended features: 20 base + 15 history one-hot + 1 successor AP flag + 3 phase one-hot = **39 dims**.
  - Training: 100 games (same collector pipeline), hidden=48, 50 epochs.
  - Val_acc: **93.7%** (vs v1's 90.3%) — **+3.4pp improvement**, info bottleneck relaxed.
  - **rc22-v2 100-game HTH**: **85/100 = 85%** Wilson [0.767, 0.907], 0 crashes.
  - **Lesson**: higher action-level accuracy did NOT yield proportional game-WR gain. 85% vs v1's 88% is statistically indistinguishable (CIs overlap). Confirms "teacher mimicking ceiling" — closer mimicking can inherit teacher's minor mistakes. Further iterations (v3, v4) would show diminishing returns.
  - **Decision**: keep both v1 and v2 as Phase 4 pool members (architectural diversity). No rc22-v3 planned.
  - **Files**: `minicontest/zoo_distill_collector_v2.py`, `minicontest/zoo_distill_rc22_v2.py`, `experiments/artifacts/rc22_v2/weights.npz`.

- **2026-04-19 pm25 Tier 3 rc22 Policy Distillation (FIRST learning-based rc)**:
  - **Teacher**: rc82 (rc29+rc44 combo, pm24 100% WR champion).
  - **Student**: numpy MLP 20→32→1 (per-action Q-score), softmax over legal, argmax inference. **~2K parameters**, pure numpy forward pass (submission-safe).
  - **Data**: 100 games rc82 vs baseline, both colors, 59,828 (φ(s,a), teacher_action) records. Teacher WR in collection = 96/100 = **96%** (baseline confirmed).
  - **Training**: 50 epochs, SGD+momentum, lr=1e-3. **Train acc 90.9%, val acc 90.3%** (information-bottleneck ceiling — MLP can't capture rc82's full internal state from 20-dim features).
  - **rc22 100-game HTH vs baseline**: **88/100 = 88%** (Wilson [0.802, 0.930]), 0 crashes. **PASS** (>> 51% threshold, beats A1 82.5%).
  - **Pipeline artifacts**: `experiments/distill_rc22.py` (orchestrator), `minicontest/zoo_distill_collector.py` (teacher + logger), `minicontest/zoo_distill_rc22.py` (student inference, 2K params numpy-only), `experiments/artifacts/rc22/weights.npz` (trained MLP), `experiments/artifacts/rc22/data.jsonl` (59,828 records).
  - **Insight**: Action-level accuracy ≠ game-level WR. 9% action-error compounds over 300-turn games → initial expectation was 55-65% WR, **observed 88%** because rc22 doesn't need to match teacher EVERY turn — just enough to execute the strategy. Lossy distillation still captures most of rc82's skill.
  - **Value for Phase 4**: First ARCHITECTURALLY DIFFERENT pool member (neural vs hand-rule). Adds diversity. Also demonstrates feasibility of Tier 3 → opens rc52/rc61 etc.

- **2026-04-19 pm26 rc52b REINFORCE alt-run (NEW learning tier peak)**:
  - Untracked `experiments/rc52b_final_weights.py` from prior training run (iter 30/300g, cum_wr 67.7% vs rc52's 57.3%). Same algorithm/spec as rc52 — different stochastic path.
  - **rc52b 100-game HTH vs baseline** (Mac, defaultCapture, 8-worker): **92/100 = 92%** Wilson [0.850, 0.959], 0 crashes. **+2pp over rc52 (90%)**, +6pp over A1 solo (86%).
  - Weights diverged visibly from rc52 (e.g. f_distToFood 34.14 → 34.14 similar, but f_scaredFlee 5.15 vs 14.32 in W_DEF). Training variance on the same REINFORCE spec yielded a better local optimum.
  - **Files**: `minicontest/zoo_reflex_rc52b.py` (new agent wrapper), `experiments/rc52b_final_weights.py` (weights).
  - **Strategic value**: confirms REINFORCE can reach ~92% on baseline; variance across training runs ≈ 2pp. Both rc52 and rc52b stay in Phase 4 pool for diversity.

- **2026-04-19 pm26 rc46 K-centroid opponent classifier (Tier 2 adaptive)**:
  - 4-archetype nearest-centroid classifier (RUSH/TURTLE/CHOKE/NEUTRAL) on a 4-D observation vector (pacman_ratio, invader_crossings, mean_depth, our_food_eaten_ratio).
  - Classification fires once at our-turn tick 60 (~120 game ticks) and stays fixed. Per-archetype multipliers applied to A1's weights (boost defense for RUSH, boost offense for TURTLE/CHOKE, no-op for NEUTRAL).
  - **rc46 100-game HTH vs baseline**: Red 48/50 + Blue 43/50 + 2 Ties + 5 Red/50 (from Blue-perspective loss) → **91/100 = 91%** Wilson [0.838, 0.952], 0 crashes. **+5pp over A1 solo (86%)**, ties rc52's 90% learning tier.
  - **Strategic value**: first OPPONENT-ADAPTIVE rc. Different archetype from rc52/rc52b (reactive vs offline-learned). Valuable in tournament where opponent stats vary.

- **2026-04-19 pm26 rc141 rc52b OFF + rc82 DEF asymmetric**:
  - Same pattern as rc140 but using the better-trained REINFORCE variant (rc52b instead of rc52).
  - **rc141 100-game HTH**: Red 47/50 + Blue 43/50 → **90/100 = 90%** Wilson [0.826, 0.945], 0 crashes. **Below rc52b solo 92%** (-2pp) — confirms rc140's lesson that linear-Q learned offense interacts weakly with rc82 DEF.
  - Still a PASS. Archetype slot filled for Phase 4 diversity.

- **2026-04-19 pm26 rc142 rc46 classifier OFF + rc82 DEF asymmetric**:
  - First hybrid of opponent-classifier OFF with composite DEF. Classifier observes during both OFF/DEF turns; on OFF turn applies multipliers to A1 weights; on DEF turn uses rc82 full composite.
  - **rc142 100-game HTH**: Red 48/50 + Blue 43/50 + 2 Ties → **91/100 = 91%** Wilson [0.838, 0.952], 0 crashes. **Same as rc46 solo** — composite DEF didn't lift it above the classifier's intrinsic 91%.
  - **Pattern confirmed (pm26)**: "learning/classifier OFF + rc82 DEF" composition stays ≈ OFF-solo. Only COMPOSITE offenses (rc16/rc32) achieved the 100% peak with rc82 DEF. Sweet spot = "two composites" not "learning + composite".

- **2026-04-19 pm26 rc52c REINFORCE continued from rc52b ckpt (OVERSHOOT lesson)**:
  - Continued rc52b weights for 30 more iters (effective 60 total), ε=0.10, lr=5e-4 (5× rc52b's 1e-4), T=3.0 (lower than rc52b's 5.0). Training cum_wr rose 67.7% → **73.3%**.
  - **rc52c 100-game HTH**: **86/100 = 86%** Wilson [0.779, 0.915]. **-6pp regression from rc52b's 92%** — back to A1 solo baseline.
  - **Lesson (learning rate / temperature overshoot)**: more training is NOT more skill when hyperparameters are aggressive. Higher lr (5× stronger gradient step) and lower T (sharper policy → larger ∇log π magnitude) both push weights harder per batch. Combined, 30 more iters overshot the rc52b local optimum. Training-set WR (ε-greedy vs baseline) does NOT predict held-out WR (greedy HTH).
  - **Recommendation for future REINFORCE**: prefer low lr + higher T + longer training for fine-grained improvement. rc52b's 67.7% cum_wr / 92% HTH was the sweet spot.
  - **Files**: `minicontest/zoo_reflex_rc52c.py` (wrapper kept for Phase 4 diversity; weights at `experiments/artifacts/rc52c/final_weights.py`).
  - **Phase 4 value**: rc52c joins pool as "over-trained REINFORCE" data point. Its HTH-86% matches A1, so it may serve as a controlled-regression member in tournament analysis.

- **2026-04-19 pm26 rc143 rc52b OFF + rc16 Voronoi DEF asymmetric**:
  - Alternative to rc141: use rc16 (A1 + Voronoi overlay, 100% solo) as DEF base instead of rc82 composite.
  - **rc143 100-game HTH**: Red 49/50 + Blue 42/50 + 1 Tie → **91/100 = 91%** Wilson [0.838, 0.952]. Same ~91% tier as rc141/rc142. **Red side extraordinary (98%)** but Blue 84% — color asymmetry pulled down total. rc16 DEF doesn't stack additively with rc52b OFF either.

- **2026-04-19 pm26 rc147 rc46 + NEUTRAL→rc52b override**:
  - Attempted to exploit "baseline classifies as NEUTRAL" by swapping NEUTRAL archetype handler from A1-no-op to rc52b weights.
  - **rc147 100-game HTH**: Red 46/50 + Blue 45/50 → **91/100 = 91%** Wilson [0.838, 0.952]. Same tier — NEUTRAL swap didn't lift above rc46 solo.
  - **Interpretation**: either baseline doesn't classify as NEUTRAL often (despite matching centroid), or A1 base with rc52b-like subset of improvements already captures the gain, so swapping to full rc52b adds nothing.

- **2026-04-19 pm26 rc52d CONSERVATIVE REINFORCE (peak confirmed as lucky draw)**:
  - Applied pm26 overshoot-lesson: lr=1e-5 (50× lower than rc52c's 5e-4), T=8.0 (higher temperature), 60 iter from rc52b ckpt. Training cum_wr 67.7% → **74.3%** (steady linear improvement, |w_off| stable 312.36).
  - **rc52d 100-game HTH**: **86/100 = 86%** Wilson [0.779, 0.915]. **SAME as rc52c's 86%** — regression equal magnitude despite very different hypparams.
  - **Cross-run lesson**: 3 REINFORCE attempts have produced HTH of (92%, 86%, 86%) from nearly identical training cum_wr (68%, 73%, 74%). rc52b is a **lucky training sample**; repeated runs converge toward ~86% (= A1 baseline). Hypothesis: the REINFORCE signal is too weak to escape A1's basin of attraction; HTH variance dominates.
  - **Implication for submission**: rc52b (92%) should be considered an **unrepeatable single-run success** — when reporting results we should note the variance band is wide.
  - **Files**: `minicontest/zoo_reflex_rc52d.py`, `experiments/rc52d_final_weights.py`.
  - **Phase 4 value**: rc52d + rc52c = two "regressed REINFORCE" members. Useful as intra-REINFORCE ablation controls.

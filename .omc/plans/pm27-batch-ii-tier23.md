# pm27 Batch II — Tier 2/3 rc plan (user request)

**Created**: 2026-04-20 pm27 (user asked "티어 2,3도 조금 몇개 해봤으면")
**Prerequisite**: Batch I (rc168/169/171 + rc159/166 re-val) 결과 수집 완료
**Budget**: ~2-5 days Mac, depends on pick

## 🎯 선정 원칙

현재 상태:
- baseline WR 97.5% (rc160 200g) — 천장 근접, 한계효용 급감
- 토너먼트 가치 필요 (H2H: rc82 > rc160)
- hand-rule composite 포화 (rc02~rc174 탐색 완료)

**ROI 최고 픽**: 현재 파이프라인과 **직교한 새 패러다임** — 토너먼트 generalization 가치 + 리포트 ablation 축.

## 📌 Batch II 후보 (3개 추천, 전부 하면 ~5d)

### 1. rc24 — Particle Filter Opponent Belief (Tier 2, 1d Mac)

**가설**: 적이 안 보일 때 (noisy distance만 있을 때) Bayesian particle filter로 belief 추적 → 침입자 예측 좌표로 수비 결정. 현재 rc 전부 직접 관측만 쓰는데, 이 축은 정보 비대칭에서 가치가 큼.

**구현 개요**:
- agent당 적 2명 belief (각 N=200 particle)
- move model: random walk on legal cells  
- observation model: noisyDistance likelihood
- resample every turn
- 가장 가능성 높은 cell → defender 할당

**제출**: numpy only, 서브밀리초 per turn 가능.
**파일**: `minicontest/zoo_reflex_rc24.py`
**평가**: 100g vs baseline (belief 안 보이므로 rc02 Tarjan AP와 비슷한 수치 예상), 토너먼트 가치는 opponent 다양할 때 상승.

### 2. rc47 — Engine-grade Alpha-Beta (Tier 2, 1.5d Mac)

**가설**: 기존 `zoo_minimax_ab_d2` 는 단순 αβ. PVS (Principal Variation Search) + aspiration windows + LMR (Late Move Reductions) + history heuristic 풀스택으로 동일 시간에 depth+2 가능. rc88 2-ply self-play (80%)가 한계였는데, 진짜 검색 엔진은 다른 얘기.

**구현 개요**:
- PVS: 첫 move는 full window, 나머지는 null window + re-search
- Aspiration windows: 이전 iteration eval±δ로 초기 window
- LMR: 깊이 3+ 에서 top-2 제외 move는 depth-1
- Move ordering: (1) hash table PV, (2) SEE (material swap), (3) history heuristic (cutoff 빈도)
- Transposition table: Zobrist key, replace-always
- Iterative deepening with 0.8s budget

**제출 가치**: `your_baseline1.py` 후보 (현재 DummyAgent). output.csv 4-way 비교에서 의미있는 다양성.
**파일**: `minicontest/zoo_reflex_rc47.py` + 의존성 reuse (`zoo_features.evaluate` as leaf).
**평가**: 100g vs baseline (αβ 자체는 강력할 거고), 100g vs rc82 (토너먼트 차별화 측정).

### 3. rc51 — ExIt (MCTS→NN Distillation) (Tier 3, ~2d)

**가설**: rc22 distillation 파이프라인이 검증됨 (88% WR). 이를 teacher = MCTS (UCT 500 rollouts), student = 5K param MLP으로 확장. Teacher는 offline 서버 학습 (20 rollouts×100 games), student는 numpy inference.

**구현 개요**:
- Teacher: rc22 teacher collector 패턴 재사용, action selection은 MCTS UCT500
- Student net: 20→64→32→1 (~2.5K params, rc22 2K 대비 약간 더 큼)
- Training: 50K examples, SGD+momentum, 50 epochs
- Evaluation: numpy inference, 1sec/turn 안에 500 examples 가능

**리스크**: MCTS teacher 자체가 느림 (100게임 40-60h). 서버에서.
**파일**: `experiments/distill_rc51.py`, `minicontest/zoo_distill_rc51_collector.py`, `minicontest/zoo_distill_rc51.py`.
**평가**: 100g vs baseline. Ceiling 관찰. rc22는 rc82 teacher였는데 rc51은 MCTS teacher → 더 높은 ceiling 기대.

## 🗂 실행 순서

사용자가 "조금 몇개" 요청이므로 — Batch I 결과 본 후 1-2개 선별 시작:

**옵션 A (최소)**: rc24 + rc47 (Mac 2.5d, 학습 없음)
**옵션 B (추천)**: rc24 + rc47 + rc51 (Mac 2.5d + 서버 48h 병렬, Tier 3 포함)
**옵션 C (stretch)**: A 또는 B + rc61 AlphaZero-lite (5d 서버, 리스크↑)

## 📝 Batch I 끝난 뒤 분기

Batch I 결과 시나리오:
- rc159 또는 rc166이 97.5%+ 유지 → 해당 baseline WR 기반 제출 락 → Batch II 시작
- rc168/169/171 중 누가 99%+ → 새 switch axis 발견, baseline 트랙 확장
- 전부 96% 이하 → rc160 기존 peak 유지, Batch II 진행

## 🔗 관련

- `rc-pool.md` Tier 2/3 섹션 — 원본 카탈로그
- pm25 `rc22` 성공 패턴 (distill 파이프라인 재사용 가능)
- pm19 CCG 자문에서 minimax container "low ROI" 판정 있지만, 그건 _container for evolve_ 얘기였고, engine-grade αβ 는 stand-alone 가치 다름

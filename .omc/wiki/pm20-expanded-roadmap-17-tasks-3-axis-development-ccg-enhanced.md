---
title: "pm20 expanded roadmap — 17 tasks, 3-axis development, CCG-enhanced"
tags: ["ADR", "pm20", "roadmap", "CCG", "17-task-plan", "3-axis", "tournament-30pt", "supersedes-pm19"]
created: 2026-04-17T05:15:24.152Z
updated: 2026-04-17T05:15:24.152Z
sources: ["pm19 ADR wiki decision/adr-pm19-phase-2-scope-revision", "pm19 CCG hybrid paradigm analysis wiki", "pm20 Codex artifact codex-cs470-pacman-capture-the-flag-minicontest-at-kaist-uc-berkel-2026-04-17T05-07-16-420Z.md", "pm20 Gemini artifact gemini-cs470-pacman-capture-the-flag-minicontest-at-kaist-uc-berkel-2026-04-17T05-06-28-648Z.md", "pm20 user directive: 15-day budget (13 effective), tournament 30pt MAX priority, never discard ≥50%-baseline candidates"]
links: []
category: decision
confidence: high
schemaVersion: 1
---

# pm20 expanded roadmap — 17 tasks, 3-axis development, CCG-enhanced

# pm20 expanded roadmap — 17-task plan, 3-axis parallel development

**Supersedes** (extends): wiki `decision/adr-pm19-phase-2-scope-revision-based-on-a1-validation-ccg-conse`.

## Strategic shift (pm20)

User directive: **performance-max + tournament 30pt 우승이 최상위 목표**. 15일 예산 (버퍼 2일 → 13일 가용). 180명 학생이 참가하는 round-robin이기에 **robustness first, peak strength second**. **baseline 50%+ 후보 절대 버리지 않음** — 전부 Phase 4 round-robin 대상.

pm19 → pm20 주요 변화:
- pm19 "Orders 2-4 + D-series + 제한적 Path 3" → pm20 "3축 병렬 (CEM 진화, Rule hybrid, Paradigm hybrid) + CCG 추가 기법 전부"
- Codex + Gemini 둘 다 자문 (2026-04-17 pm20) — particle filter, opponent classifier, endgame lockout, capsule proxy camping, stochasticity 추가

## 3축 개발 구조

### 축 1 — CEM 진화 (서버 jdl_wsl)

| Order | Init | Master-seed | Pool 추가 | 상태 |
|---|---|---|---|---|
| A1 (17-dim) | h1test | 42 | (기본 11) | ✅ 완료 (fitness 1.065, 79% baseline) |
| 2 A1+B1 (20-dim) | h1test | 42 | (기본 11) | ▶️ 실행 중 (ETA ~06:00 내일) |
| 3 | h1test | 1001 | + zoo_reflex_A1 | ⏳ 대기 (Order 2 완료 후) |
| 4 | a1 (NEW) | 2026 | + zoo_reflex_A1, zoo_reflex_O2 (HOF 확장) | ⏳ 대기 |
| 5+ (Specialist) | — | — | specialist 루트 진입 | ⏳ |

각 Order ~18h. A1의 **champion weight vector 다양성** 확보. Red Queen HOF 시스템 (Task #12): 각 Order 끝날 때마다 champion을 zoo_reflex_O{N}.py로 자동 래핑 후 다음 Order pool에 추가 → 모든 새 Order가 모든 이전 champion을 이겨야 함 (AlphaZero-lite, Codex +15-40 ELO).

### 축 2 — Rule-based Hybrid (Mac)

| Task | 내용 | 공수 | CCG 소스 |
|---|---|---|---|
| D1 #5 | Role-swap + arbitration (closest-to-home invader handler, force-defender-if-leading, carrying bank rule) | 2-4h | Codex |
| D2 #6 | Capsule timing + proxy camping + dead-end trap state machine | 4-6h | Codex + Gemini (proxy) |
| D3 #7 | Endgame lockout + score-lead trigger + suicide-teleport | 2-3h | Codex (score-lead) + Gemini (teleport) |

D1/D2/D3은 **mixin 형태** — A1 champion + D-series 조합으로 4 variant per champion 생성 (bare / +D1 / +D1+D2 / +D1+D2+D3).

### 축 3 — Paradigm Hybrid (Mac 코드 + 서버 CEM)

| Task | 내용 | 공수 |
|---|---|---|
| Path 3 #3 | MCTS q_guided offense + ReflexTuned (A1 weights) defense + MCTS + A1 policy prior PUCT (T6 통합) | 4-6h infra, 18h optional CEM |
| T5 #9 | Particle filter opponent tracking (Gemini "unfair advantage") | 6-8h |
| T4 #8 | Online opponent classification (50-tick observation → counter-mode) | 6-10h |
| T7 #10 | Specialist split with role-switch curriculum (Order 5+) | 10-16h + 18h server |
| T8 #11 | Stochasticity layer (final polish on 20200492.py) | 1-2h |

## 17-task 우선순위 + 의존성

### Tier 0 — Hedge (이미 확보)
- ✅ #1 M7 flatten A1 → 20200492.py lock (pm20 완료, 40pt 게이트 보장)

### Tier 1 — Infrastructure (pm20-21, Mac 병렬)
- 🔄 #2 Orders 3/4 diversification (patch + launch script, commit 후 내일 런칭 대기)
- #3 Path 3 hybrid infra (MCTS weight-override + ZOO_MCTS_MOVE_BUDGET env var + zoo_hybrid_mcts_reflex.py + PUCT policy prior)
- #12 Red Queen HOF extension tool (experiments/make_hof_wrapper.py) — 내일 Order 2 끝나면 바로 사용

### Tier 2 — Rule-based hybrids (pm21-22, Mac)
- #5 D1 role-swap + arbitration
- #6 D2 capsule tactics (timing + proxy + trap)
- #7 D3 endgame lockout + score-lead + suicide-teleport

### Tier 3 — Advanced techniques (pm22-25, Mac)
- #8 T4 Online opponent classification
- #9 T5 Particle filter opponent tracking
- #10 T7 Specialist split (Order 5+, 서버 병행)
- #11 T8 Stochasticity layer (최종 폴리시)

### Tier 4 — Selection + submission (pm26-27)
- #13 Phase 4 round-robin tournament (전체 후보 ELO)
- #14 Phase 5 multi-seed top-3 validation
- #15 M8 populate your_baseline1/2/3 + output.csv
- #16 M9 ICML report (Intro+Methods / Results / Conclusion)
- #17 M10 submission zip

## 13일 실행 타임라인

| Day | 서버 | Mac | 체크포인트 |
|---|---|---|---|
| pm20 (today) | Order 2 running | Task #3, #12, D-series 착수 | ✅ pm20 계획 문서화 |
| pm21 | Order 2 완료 → HTH → 결정 → Order 3 launch | D1/D2/D3 완성 smoke | Order 2 HTH 결과 |
| pm22 | Order 3 running | T4 opponent classifier | Order 3 중간 확인 |
| pm23 | Order 3 완료 → HTH → Order 4 launch | T5 particle filter | Order 3 HTH |
| pm24 | Order 4 running | T5 완료 smoke, Path 3 CEM prep | Order 4 중간 |
| pm25 | Order 4 완료 → HTH, Order 5 (specialist) launch | Path 3 hybrid smoke + CEM 준비 | Order 4 HTH |
| pm26 | Order 5 running / Phase 4 tournament | T8 stochasticity, D-series × champion 조합 | Phase 4 ELO |
| pm27 | Phase 5 multi-seed | M9 report Intro/Methods draft | top-3 선정 |
| pm28 | 최종 chosen champion Mac re-validation | M9 Results + figures | 최종 champion |
| pm29 | 버퍼 | M9 Conclusion | 리포트 거의 완료 |
| pm30 | 버퍼 | M10 zip + sha256 + 최종 검증 | 제출 |
| pm31-32 | 버퍼 (+2일) | 긴급 버그 수정 | — |

## 결정 게이트 (각 Order HTH 후)

| 게이트 | Trigger | Action |
|---|---|---|
| G1 | Order 2 HTH > A1 (Wilson LB > 0.80) | Order 2 → new champion, 20200492.py 재flatten |
| G1 | Order 2 HTH ≈ A1 | A1 유지, Order 3 계속 |
| G1 | Order 2 HTH < A1 (LB < 0.70) | B1 feature 롤백 검토, Order 3/4 17-dim으로 |
| G2 | Order 3 HTH > top | 현재 champion 갱신 |
| G3 | Order 4 HTH > top | 현재 champion 갱신 |
| G4 | Path 3 smoke 실패 (wall > 110s 또는 crash) | Path 3 축 중단 |
| G5 | T5 particle filter 검증 5-game smoke 0 crash | 모든 champion에 통합 |
| G6 | Phase 4 top-3 내 variance > 5pp | Phase 5 confidence 우선 재평가 |

## 절대 금지 (Codex 경고)

- ❌ Opponent timing-pressure — 우리 자신 forfeit 리스크
- ❌ 단일 Order 실패로 전체 계획 붕괴 — 각 Order 후 체크포인트
- ❌ Specialist 훈련 without coordination rules — 중복 OFFENSE/DEFENSE 배치 실패 모드
- ❌ TD-lambda Q-learning을 Main 축으로 — 15일로 너무 risky

## Failure mode watchlist (Codex top 3)

1. **Time-budget tail risk** — >1s 스파이크 monitor (3 warnings = forfeit)
2. **Color/layout asymmetry overfit** — always test both colors, multi-layout
3. **Non-transitive matchup holes** — pool 다양성으로 hedge

## Related wiki

- Superseded: `decision/adr-pm19-phase-2-scope-revision-based-on-a1-validation-ccg-conse`
- Champion profile: `reference/a1-champion-weights-hth-profile-strategy-interpretation-pm19`
- Server ops: `pattern/server-order-queue-operational-runbook-launch-archive-verify-cyc`
- CCG advisor artifacts (pm20): `.omc/artifacts/ask/codex-cs470-pacman-capture-the-flag-minicontest-at-kaist-uc-berkel-2026-04-17T05-07-16-420Z.md`, `.omc/artifacts/ask/gemini-cs470-pacman-capture-the-flag-minicontest-at-kaist-uc-berkel-2026-04-17T05-06-28-648Z.md`
- pm19 hybrid paradigm analysis: `decision/pm19-ccg-hybrid-paradigm-analysis-path-1-vs-2-vs-3-mcts-offense-`


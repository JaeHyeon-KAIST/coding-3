---
title: "2026-04-19 - pm22 rc-pool 80 candidates 수집 + autopilot Phase 2b 진행"
tags: ["pm22", "session-log", "rc-pool", "autopilot", "candidate-pool", "ccg", "codex", "gemini", "handoff", "round-robin"]
created: 2026-04-18T18:58:45.666Z
updated: 2026-04-18T18:58:45.666Z
sources: []
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-19 - pm22 rc-pool 80 candidates 수집 + autopilot Phase 2b 진행

# Session pm22 — Candidate Pool Expansion (no code)

## Date / Duration

- 2026-04-18 14:00 KST ~ 2026-04-19 04:30 KST (~14h, mostly autopilot + planning + /branch conversation)

## Focus

**첫째**: autopilot cron으로 Order 3 진행 (서버 자동 orchestration 검증).
**둘째**: round-robin 토너먼트 후보 다양화를 위한 기법 수집/정리. 실제 코드 X.

## Activities

### autopilot 관련
- pm21 session 끝나면서 cron 016b37d5 소멸. pm22 첫 action으로 cron re-arm.
- `7,37 * * * *` 30분 간격 SSH check → stage 판정 → action.
- 총 ~20번 정도 cron wake, S0 유지 (Order 3 진행 중).
- Phase 2a 트래젝토리 (best): 0.314 → 0.383 → 0.444 → 0.452 → 0.533 → 0.628 → 0.644 → 0.716 → 0.634 → 0.668 (best_ever 0.716 at gen 7).
- Phase 2b 시작, gen 0~6 best: 0.744 → 0.751 → 0.725 → 0.762 → 0.781 → 0.784 → 0.796 (best_ever 0.796). 13 gens 남음.
- Phase 2a 2b 전환 시 wall time 급감: 58min/gen → 38min/gen (split W에서 opp pool 줄어서).

### autopilot 운영 팁 (pm22 경험)
- 매 cron wake마다 skill-active state 자동 활성 → stop hook 반복 block. 해결: `state_write(mode=autopilot, active=false) + state_clear(mode=skill-active)` 각 wake 후.
- SSH 가끔 timeout. `-o ConnectTimeout=10`과 재시도로 처리.
- `ssh jdl_wsl "cd ~/projects/coding-3 && ..."` cd 필수 (없으면 home dir 봄).
- Cron `durable=true` 해도 session-only. 새 세션마다 re-arm 필요.

### /branch로 분기: rc-pool 수집
- user가 "GPU도 있고 10+ days도 남았는데 더 다양화하자"고 요청.
- Mac M3 Pro + 서버 RTX 4090 24GB 확인 (Windows 호스트 기준 정상, WSL passthrough 미설정).
- 기존 50개 기법 카테고리별 정리 (진화/RL/search/MARL/supporting/combination/feature/infra).
- CCG invoke: Codex + Gemini 각자 시각에서 15~20개씩 추가 후보.
  - **Codex** (알고리즘 correctness): TAR² DrS ARES DIRECT (최신 RL credit assignment), IS-MCTS MCCFR POMCP DESPOT Vec-QMDP I-POMDP Lite (imperfect-info), Factored MCTS Engine-grade Alpha-Beta WHCA* SIPP Articulation Points Hungarian (search/coord/backend)
  - **Gemini** (creative/unconventional): Articulation Point 방어, Dead-end Trapping, Border Juggling, Aggro-Juggling, Pincer Maneuver, Dynamic Lane Assignment, Resource Denial, Prospect Theory, Recursive ToM L2, Pavlovian Feinting, Stigmergy Pheromones, Boids Swarm, Sacrificial Decoy, Vision-Edge Surfing, Search-Depth Disruption, Particle-Filter Blinding, Persona-shifting Agent
- user 새 제안: "초기 몇 move 상대 관찰 → 스타일 분류 → 맞춤 counter-policy" = **rc46 Online Opponent Type Classifier** (추가).

### 최종 rc-pool 문서화
- `.omc/plans/rc-pool.md` 작성 (194 lines, 80 rc candidates in 5 tiers).
  - Tier 1 (15): 즉시 구현, L 난이도, <8h (rc01 D-series, rc02 articulation, rc12 transposition 등)
  - Tier 2 (35): 중간 난이도, 1~2일 각 (rc22 distillation, rc23 coev, rc46 opponent classifier 등)
  - Tier 3 (20): H 난이도, 2~5일 (rc51 ExIt, rc61 AlphaZero-lite 등)
  - Tier 4 (5): 최신 논문 (rc71~rc75)
  - Tier 5 (5): 압축/보조 (rc76~rc80)
- `.omc/plans/pm23-handoff.md` 작성 (169 lines, session handoff).
- `.omc/STATUS.md`, `.omc/SESSION_RESUME.md` 업데이트 (pm22 → pm23 entry point 변경).
- 메모리 업데이트: `project_cs470_a3.md`, `pm22_autopilot_handoff.md` → "pm23 candidate impl handoff".

## Observations

1. **Phase 2b wall speedup**: gen 당 38min (Phase 2a 58min의 65%). Split W의 opp pool이 적어서 (dry 풀에서 11-opp full pool로 전환 예상했는데 반대). 구체 원인 미조사.
2. **Order 3 best_ever 0.716 (Phase 2a)** > A1 Phase 2a (~0.5). Order 3 Phase 2b에서 A1 최종 1.065 근접 가능성.
3. **CCG advisor 품질**: Codex가 1차 논문 정확히 인용 (TAR²/DrS/ARES arxiv URL). Gemini는 conceptual/creative 강점. 상호 보완.
4. **rc46 (online opponent classifier)** user 직관으로 도출된 아이디어인데 I-POMDP Lite + D4 opponent modeling + DIRECT discriminator 등과 자연스럽게 연결됨. 핵심 후보.

## Decisions

1. **후보 pool을 5 Tier로 층화** (난이도 + 시간 예산): pm23은 Tier 1부터 순차 접근.
2. **`rc##` naming**: pm##는 세션 타임라인, rc##는 작업 항목. 한 rc가 여러 세션 걸칠 수 있음.
3. **pm22는 코드 작성 X**: planning/정리만. 실제 구현은 pm23부터.
4. **Phase 4 tournament 시점**: Order 3/4 + rc 주요 후보 완료 후 user 수동 트리거 (autopilot S2에서 stop 유지).
5. **GPU 활용은 pm23+ 결정**: WSL passthrough 설정 필요, 현재 설정 안 됨. rc22 distillation + rc61 AlphaZero-lite 등 진행 시 필요.

## Open items / 다음 세션 priority

**pm23 first actions**:
1. `.omc/plans/pm23-handoff.md` + `.omc/plans/rc-pool.md` 읽기
2. 서버 상태 체크 (autopilot 자동 S1 정상 수행됐나)
3. Cron re-arm (session-only)
4. rc01 D-series 구현 시작 (Mac)

**Server autopilot 예상 진행 (pm22 → pm23 이행 기간)**:
- Order 3 완료: ~12:30 KST 04-19
- S1 자동 (HTH + archive + O3 wrapper + Order 4 launch): ~5min
- Order 4 완료: ~11:30 KST 04-20
- S2 도달 → autopilot 정지, notification

**미해결**:
- Phase 2b wall time 감소 원인 (opp pool 구성 확인 필요)
- rc46 (opponent classifier) spec 상세화 (다음 세션에서)
- GPU passthrough 설정 (rc22/rc61 필요 시점에)

## Next-session priority (pm23)

1. 서버 Order 3/4 autopilot 검증 (Phase 2b 끝, Order 4 시작)
2. rc01 D-series (D1 role-swap + D2 capsule timing + D3 endgame + D4 dead-end-guard) 최소 1개 완성 + 40게임 smoke pass
3. Tier 1 rc02~rc05 중 2~3개 추가 완성
4. Optional: rc46 opponent classifier spec 상세화


# pm23 Session Handoff — Candidate Pool Implementation

**Origin**: pm22 ended 2026-04-19 ~04:30 KST.
**pm22 main output**: **80 candidates (rc01~rc80)** for round-robin tournament. No code, just planning.
**pm23 goal**: 실제 코드 구현 시작 (Tier 1 rc01~rc15 중심).

---

## 🎯 pm23 First Actions (5 min)

### Step 1 — Read essentials (3 min)

**반드시 읽을 것 (우선순위 순)**:
1. 이 파일
2. `.omc/plans/rc-pool.md` ← **메인 문서, 80 후보 전체 목록**
3. `.omc/STATUS.md` (milestone 상태)
4. `.omc/state/autopilot-server-pipeline.json` (서버 자동화 상태)

### Step 2 — Verify server autopilot (30s)

```bash
ssh -o ConnectTimeout=10 jdl_wsl "cd ~/projects/coding-3 && \
  pgrep -af evolve.py | wc -l; \
  ls experiments/artifacts/final_weights.py 2>/dev/null && echo YES_FINAL || echo NO_FINAL; \
  ls -d experiments/artifacts/phase2_*/ 2>/dev/null | wc -l; \
  tmux capture-pane -t work -p -S -5 | tail -5"
```

### Step 3 — Re-arm cron if session fresh

pm21과 pm22 모두 `durable=true` 해도 session-only로 떨어짐. pm23도 동일.

```
CronCreate(
  cron="7,37 * * * *",
  recurring=true,
  durable=true,
  prompt="Autopilot server pipeline check. Read .omc/plans/autopilot-server-pipeline.md and .omc/state/autopilot-server-pipeline.json. SSH jdl_wsl, identify stage (S0/S1/S2), execute action AUTONOMOUSLY. Update state + PushNotification on transitions. STOP at S2 (Phase 4 manual per user directive)."
)
```

### Step 4 — Start rc01 (D-series)

```bash
# D1 role-swap부터 시작
cat .omc/plans/rc-pool.md  # rc01 spec 참고
# 구현: minicontest/zoo_reflex_d1.py
# A1 champion 베이스 + role-swap logic overlay
```

---

## 🖥️ 서버 상태 (pm22 end 시점)

| 항목 | 값 |
|---|---|
| **Order 3 진행** | Phase 2b gen 6 완료 (best=0.796, best_ever=0.796) |
| **남은 2b gens** | 13 (~8.3h) |
| **Order 3 ETA** | ~12:30 KST 2026-04-19 (~8h 후) |
| **Order 4 ETA** | ~11:30 KST 2026-04-20 (Order 3 끝난 뒤 자동 런치 후 ~22h) |
| **현재 stage** | S0-Order3 |
| **Autopilot cron** | pm22 session이 닫히면 소멸. pm23이 재생성 필요. |
| **champion** | A1 (17dim, baseline 79%, Wilson LB 0.728) |
| **HOF pool** | `zoo_reflex_A1.py`, `zoo_reflex_O2.py` (Mac+server 동기화됨) |
| **HOF 예정 생성** | `zoo_reflex_O3.py` (Order 3 끝나면), `zoo_reflex_O4.py` (Order 4 끝나면) |
| **submission** | `minicontest/20200492.py` = A1 flatten (이미 committed) |

### 기대 Order 3/4 결과 (Phase 2a best_ever=0.716 관찰 기준)

Order 3 Phase 2a best_ever 0.716은 A1 Phase 2a 끝 (~0.5)보다 **43% 우수**.
Phase 2b에서 A1 1.065에 근접 또는 초과 가능성 있음.

**자동 판정**: autopilot이 Order 3 HTH 결과 Wilson LB ≥ 0.80 AND > A1 (0.728)이면 champion 교체.
현재 A1 = 79% ≈ Wilson LB 0.728, 이걸 넘으려면 Order 3가 **baseline ≥ 82%** 정도 필요.

---

## 📋 pm23 구체적 작업 시나리오

### Scenario A: Server autopilot가 문제없이 돌고 있음
- rc01 (D-series) 부터 Mac에서 구현 시작
- 서버는 건드리지 말고 놔둠

### Scenario B: Order 3 끝났지만 autopilot 안 돌아감 (cron 죽음 + pm22 fail)
1. Handoff 문서 (`.omc/plans/autopilot-server-pipeline.md`) Stage S1 절차 수동 실행:
   - HTH battery 돌림
   - Archive
   - zoo_reflex_O3 wrapper 생성
   - Order 4 launch
2. Cron 재생성

### Scenario C: Server crash (WSL dead)
1. `ssh jdl "wsl -d Ubuntu-22.04 -- uptime"`로 깨우기
2. `--resume-from experiments/artifacts/`로 재개

### Scenario D: 사용자가 Order 4 이후 Order 5+ 추가 원함
`.omc/plans/rc-pool.md`와 별개로 추가 Order 설계 (10일 여유 있으니 6~7개 더 가능):
- Order 5: h1b seed, master-seed 3141
- Order 6: MCTS container (pm18 blocker 수정 후)
- Order 7: expectimax container
- Order 8: h1c seed

---

## 🚦 Mac 작업 추천 순서 (pm23~)

**Day 1 (pm23)**: Tier 1 rc01, rc02, rc03, rc04, rc05
**Day 2 (pm24)**: Tier 1 rc09, rc10, rc15, rc12, rc13, rc14
**Day 3~4**: Tier 2 rc22, rc23, rc46 (user 제안 opponent classifier ⭐)
**Day 5~6**: Tier 2 나머지 선택
**Day 7**: Tier 3 고위험 1~2개
**Day 8**: Phase 4 tournament (서버 트리거)
**Day 9**: Phase 5 validation
**Day 10**: Report + zip + 제출

각 rc 완료 시:
1. `minicontest/zoo_*.py` 또는 `minicontest/monster_*.py` 새 파일
2. vs baseline 40게임 smoke test (WR ≥ 30% 확인)
3. 통과 시 git commit + push
4. `docs/AI_USAGE.md` 업데이트 (제출 코드 수정 시)
5. `.omc/plans/rc-pool.md`의 변경 로그에 상태 업데이트 (not started / in progress / done / skipped)

---

## 🔔 주의사항 (pm22 경험)

### pm22 learned anti-patterns
1. **Autopilot skill state 재활성화**: cron prompt의 "autopilot" 키워드가 OMC autopilot skill을 재활성. 해결: 매 cron wake 후 `state_write(mode=autopilot, active=false)` + `state_clear(mode=skill-active)`. Stop hook 걸리면 반복.
2. **SSH 가끔 timeout**: `-o ConnectTimeout=10` 추가 필수. 한 번 실패해도 재시도하면 보통 성공.
3. **ls cwd 의존**: `ssh jdl_wsl "cd ~/projects/coding-3 && ls ..."` 꼭 cd 붙여야 함. 안 붙이면 home dir 봄.

### rc-pool 구현 시 주의
1. **1 sec/turn 제약 엄격**: ensemble (rc15), recursive ToM (rc65), opponent classifier (rc46)는 실측 필수
2. **Submission flatten 고려**: 나중 M7에서 flatten해야 하므로 import 구조 간단하게
3. **CLAUDE.md 금지 사항**:
   - 글로벌 python 사용 X (`.venv/bin/python` 또는 `uv run --python .venv/bin/python`)
   - numpy/pandas 외 라이브러리 X
   - 멀티스레딩 X (submission)
   - framework 파일 수정 X

### 서버와 Mac 동기화
- HOF wrapper (`zoo_reflex_O3.py`, `O4.py`)는 autopilot이 자동 scp + commit
- Mac에서 rc 개발하다가 서버에도 배포하고 싶으면 `git push` → `ssh jdl_wsl "cd ~/projects/coding-3 && git pull"`
- `experiments/artifacts/`는 gitignored, 서버에만 있음

---

## 📊 pm22 최종 Quick Stats

| 지표 | pm22 시작 | pm22 끝 |
|---|---|---|
| Order 3 Phase 2a | 미시작 | **완료** (best_ever 0.716) |
| Order 3 Phase 2b gens | 0 | 7/20 (35%) |
| HOF wrappers | 2 (A1, O2) | 2 (O3는 autopilot이 생성 예정) |
| rc pool | 0 | **80** |
| 문서 신규 | - | rc-pool.md, pm23-handoff.md |
| Autopilot cron id | — | 016b37d5 (pm22 session 종료 시 dies) |

---

## 🎯 pm23 성공 기준

1. ✅ rc-pool.md와 pm23-handoff.md 숙지
2. ✅ 서버 autopilot 재가동 (cron 재생성)
3. ✅ rc01 (D-series) 적어도 D1 완성 + 40게임 smoke 통과
4. Optional: rc02~rc05 중 2~3개 추가 완성
5. Optional: Order 3 autopilot 통해 자동 완료 확인

`rc-pool.md` 변경 로그에 pm23 end 시점의 rc 상태 업데이트 필수.

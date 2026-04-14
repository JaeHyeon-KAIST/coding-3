# Project Notepad

## Priority Context (always loaded at session start)

- **Project**: CS470 A3 — Pacman capture-the-flag contest. Student ID 20200492.
- **Python**: `.venv/bin/python` 만 사용. Global python/pip 절대 금지. numpy+pandas only.
- **Goal**: 토너먼트 승률 극대화 (extra credit 30pt 랭킹 노림).
- **제출 직전**: `.venv/bin/python minicontest/capture.py -r your_best -b baseline -n 10 -q` 로 승률 최종 확인.
- **AI 사용 로그**: 제출 대상 코드 수정할 때마다 `docs/AI_USAGE.md`에 append.
- **수정 금지 파일 리스트는 `.omc/project-memory.json`의 `frozen` 참고.

## Working Memory (auto-pruned after 7 days)

### 2026-04-14 초기 세팅 결과
- venv: `.venv/` Python 3.9.11 / numpy 2.0.2 / pandas 2.3.3
- 게임 엔진 동작 확인됨: `cd minicontest && ../.venv/bin/python capture.py -r <red> -b <blue> -n <N> -q`
- `-n N`을 주면 N판씩 2세트(Red/Blue 스타터 교체) 총 2N 게임이 돌아가는 것처럼 보임 — `capture.py` 소스 확인 필요 시점에 확인
- 기본 상태: `your_best.py`, `your_baseline{1,2,3}.py`, `myTeam.py` 전부 DummyAgent (랜덤 액션). baseline 상대 승률 0%.
- `baseline.py`의 `OffensiveReflexAgent` + `DefensiveReflexAgent` 이 기준선. 이걸 51%+ 이겨야 코드 40pt
- 빠른 배치 실험 시 반드시 `-q` (quiet) 플래그 — 그래픽 뜨면 느림

<!-- 이후 관찰 기록 -->

### 2026-04-14 후반 — Ralplan consensus 확정 + multi-reviewer 통과

- 3-round consensus: Planner → Architect (PROCEED w/ 7 patches) → Critic iter1 (ITERATE, 7 actionable) → patches applied → Critic iter2 (APPROVE)
- 추가 3-way validation: Scientist (2 must-fix), Codex (6 patches), Gemini (3 high-leverage additions — risk-sensitive fitness, APSP init, STOP fallback 개선)
- 모든 MUST-FIX 패치 적용 완료. 최종 플랜: `.omc/plans/STRATEGY.md` 746 lines
- Stretch items는 `.omc/plans/open-questions.md` 50줄에 정리 (online opponent profiling, max-flow bottleneck, numpy MLP, report narrative 개선 등)
- 커밋 `8c9fe66` — plan milestone 확정

### 2026-04-14 후반 — Autopilot Phase 2 M1 시작

- Executor (Opus) 백그라운드 가동: `minicontest/zoo_core.py` (CoreCaptureAgent) + `zoo_dummy.py` + 10회 smoke test
- Path layout 결정: 플랜의 `experiments/zoo/_core.py` 대신 `minicontest/zoo_*.py`로 변경 (capture.py -r 이름 해석 호환)
- `experiments/` 디렉토리 = 평가 파이프라인/진화/분석/제출 스크립트용
- M1 완료 후 M2 (zoo 12+ variants) 바로 진행 예정

## Manual (never pruned)

<!-- 유저가 수동으로 적는 영구 메모 -->

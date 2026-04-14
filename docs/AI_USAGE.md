# AI Usage Log — CS470 Assignment #3 (Student 20200492)

과제 규정: "AI 사용 시 (1) AI 이름, (2) 프롬프트, (3) 사용 부분, (4) 검증 방법을 comprehensive하게 명시."
이 파일은 **제출 대상 코드** (`your_best.py`, `your_baseline1.py`, `your_baseline2.py`, `your_baseline3.py`, 최종 `20200492.py`) 수정 시마다 자동 누적된다. 최종 리포트에 그대로 반영 가능.

## 엔트리 포맷

```
## YYYY-MM-DD HH:MM (Asia/Seoul) — <한 줄 요약>
- **AI**: <모델 이름 + 버전, e.g., Claude Opus 4.6>
- **Prompt**: <유저 요청 핵심 or Claude 쪽에서 내린 지시 요약>
- **수정 부분**: <파일 경로 + 함수/클래스 또는 라인 범위>
- **검증 방법**: <실제 돌린 명령/테스트 + 결과 (승률, 오류, 러닝타임 등)>
- (옵션) **배경/의도**: 한두 줄 더 구체적 설명
```

---

## 2026-04-14 — 프로젝트 초기 세팅 (채점 대상 코드 수정 없음)

- **AI**: Claude Opus 4.6 (1M context)
- **Prompt**: 프로젝트 PDF 읽고 Claude Code/OMC 세팅 (CLAUDE.md, .omc, docs, venv)
- **수정 부분**: 제출 대상 코드(`your_*.py`, `myTeam.py`) **수정 없음** — 프로젝트 메타 파일(`CLAUDE.md`, `.omc/*`, `.gitignore`, `docs/AI_USAGE.md`)만 추가
- **검증 방법**: venv 설치 후 `.venv/bin/python minicontest/capture.py -r baseline -b baseline -n 1 -q` 스모크 실행으로 환경 동작만 확인

_이 엔트리는 **채점 대상 파일을 바꾸지 않음**이라 리포트에 포함 불필요. 이후 실제 에이전트 로직을 수정하는 순간부터 엔트리가 채점 대상이 됨._

---

<!-- 이 아래부터 실제 코드 변경 로그가 쌓임 -->

---

## 2026-04-14 16:15 — M1 구현: CoreCaptureAgent 기반 + 더미 smoke 에이전트

- **AI**: Claude Opus 4.6 (OMC executor 서브에이전트; 메인 orchestrator가 smoke test 보강 실행)
- **Prompt**: STRATEGY.md §3/§4.0/§5 기반으로 `CoreCaptureAgent` 기반 클래스를 `minicontest/zoo_core.py`에 구현. 2-layer crash-proof `chooseAction` (TimeoutFunctionException re-raise + random-non-STOP fallback + STOP 최후 fallback), `registerInitialState` 7단계 개별 try/except 감쌈 + APSP 사전계산, `TeamGlobalState` 싱글턴 정의. 추가로 `zoo_dummy.py`에 랜덤 non-STOP 액션 선택 에이전트 작성. 10회 smoke test로 검증.
- **수정 부분**:
  - `minicontest/zoo_core.py` (신규, 21349 bytes) — `CoreCaptureAgent(CaptureAgent)`, `TeamGlobalState`, APSP/bottleneck/deadEnd/homeFrontier precompute helpers, 2-layer chooseAction wrapper
  - `minicontest/zoo_dummy.py` (신규, 1393 bytes) — `ZooDummyAgent(CoreCaptureAgent)` + `createTeam` factory
- **검증 방법 및 결과**:
  - Import sanity: `.venv/bin/python -c "import zoo_core, zoo_dummy"` → OK
  - 10연속 smoke test: `cd minicontest && for i in 1..10; do ../.venv/bin/python capture.py -r zoo_dummy -b baseline -l defaultCapture -n 1 -q; done`
  - 결과: **10/10 exit code 0**, 0 crashes, 0 timeout warnings. zoo_dummy은 랜덤 move라 baseline에 **0승 7패 3무** (기대대로). CRASH_PENALTY 발동 없음. M1 exit criteria 충족.
- **배경**: 모든 후속 zoo 변종과 submitted agent가 상속할 기반 클래스. 2-layer 예외 처리로 CRASH_PENALTY=100 방지. APSP 사전계산으로 이후 search agent의 distance lookup이 O(1). 제출 대상 파일은 아니지만, select_top4.py가 zoo에서 선정한 에이전트를 `your_best.py` / `your_baseline1~3.py`로 복사/평탄화할 때 이 기반 클래스의 메소드들이 인라인됨.

# CS470 Assignment #3 — Pacman Capture the Flag

KAIST 인공지능개론 (2026 봄학기) 코딩 과제 3. UC Berkeley CS188 기반 **팀 캡처더플래그** 미니 콘테스트.

**학번 / 제출 파일명**: `20200492` → `20200492.py`, `20200492.pdf`, `20200492.pptx`, `20200492.zip`

## 목표 우선순위

1. **승률 극대화 / 토너먼트 랭킹 상위권** (extra credit 30pt 노림)
2. baseline 대비 51%+ 승률로 코드 40pt 확보
3. LaTeX ICML 포맷 리포트 60pt 확보 (Intro 8 / Methods 20 / Results 20 / Conclusion 12)

## 🚫 절대 금지

- **글로벌 Python 사용 금지**. `python`, `python3`, `pip`, `pip3` 단독 호출 금지
  - 모든 Python 실행: `.venv/bin/python ...` 또는 `uv run --python .venv/bin/python ...`
  - 패키지 설치: `uv pip install --python .venv/bin/python <pkg>`
- **numpy / pandas 외 의존성 추가 금지** (채점 환경에 없음 → 0점 리스크)
- **멀티스레딩 사용 금지** (과제 규정, 실격 사유)
- **`baseline.py`, `capture.py`, `captureAgents.py`, `game.py`, `layout.py`, `distanceCalculator.py`, `graphicsDisplay.py`, `captureGraphicsDisplay.py`, `graphicsUtils.py`, `keyboardAgents.py`, `mazeGenerator.py`, `textDisplay.py`, `util.py` 수정 금지**

## ✍️ 수정 가능 파일

| 파일 | 역할 |
|---|---|
| `minicontest/your_best.py` | 최종 제출 (→ `20200492.py`로 rename 후 제출). 승률 극대화 타겟 |
| `minicontest/your_baseline1.py` | 실험용 #1 (예: reflex 고도화) |
| `minicontest/your_baseline2.py` | 실험용 #2 (예: minimax + α-β) |
| `minicontest/your_baseline3.py` | 실험용 #3 (예: MCTS 또는 feature-based q-learning) |
| `minicontest/myTeam.py` | 템플릿 (참고용, 실제 제출은 `your_best.py` 계열) |

## Python 실행 규칙

- Python 버전: **3.9** (채점 환경과 일치)
- venv 위치: `.venv/` (uv 생성)
- 의존성: `numpy`, `pandas` 만

### 자주 쓰는 커맨드

```bash
# 기본 한 판 (baseline vs baseline)
.venv/bin/python minicontest/capture.py -r baseline -b baseline

# 내 best vs baseline
.venv/bin/python minicontest/capture.py -r your_best -b baseline

# 10판 자동 (제출 검증용)
.venv/bin/python minicontest/capture.py -r your_best -b baseline -n 10

# 텍스트 모드 (빠른 배치 실험)
.venv/bin/python minicontest/capture.py -r your_best -b baseline -n 10 -q

# 랜덤 레이아웃 시드 고정
.venv/bin/python minicontest/capture.py -r your_best -b baseline -l RANDOM13
```

**주의**: `capture.py`는 `minicontest/` 안에서 돌려야 import 경로가 맞을 가능성 — 문제 생기면 `cd minicontest && ../.venv/bin/python capture.py ...` 로 변경.

## 🤖 AI 사용 로깅 (필수)

과제 규정: "AI 사용 시 (1) AI 이름 (2) 프롬프트 (3) 사용 부분 (4) 검증 방법을 comprehensive하게 명시"

**Claude는 제출 대상 코드(`your_best.py`, `your_baseline1~3.py`)를 Edit/Write로 터치한 직후 `docs/AI_USAGE.md`에 엔트리를 append해야 한다.** 엔트리 포맷은 해당 파일 상단 템플릿 참고.

## 제약 사항 치트시트

- 턴당 **1초** (3번 초과 warning, 3초 초과 forfeit)
- 초기화 **15초** (`registerInitialState`)
- 게임 **1200 move** 제한
- 적 턴에 계산 불가 — **no multithreading**
- Capsule → 상대팀 40 moves 동안 scared (또는 먹히고 respawn 시 해제)
- 승리 조건: 상대 food 2개 빼고 다 먹음 또는 1200 move 경과 시 더 많이 먹은 팀

## 체크리스트 (제출 직전)

- [ ] `.venv/bin/python minicontest/capture.py -r your_best -b baseline -n 10` 승률 확인
- [ ] `your_best.py` → `20200492.py` rename (또는 복사)
- [ ] LaTeX 리포트 ICML 포맷 2p+ (`icml2021_style/` 템플릿 이용)
- [ ] 발표 슬라이드 5~10p
- [ ] ZIP: `20200492.zip` 안에 `20200492.py`, `20200492.pdf`, `20200492.pptx`
- [ ] `docs/AI_USAGE.md` 내용이 리포트에 반영됐는지

## Q&A TA

Injae Kim (Lead, injae.kim@kaist.ac.kr), 배민성, 이태훈, 윤승민, 서진우

---

## 🧭 Multi-session continuity (장기 5+ 세션 프로젝트)

이 프로젝트는 5 세션 이상 가로질러 진행. 새 세션 시작할 때 다음 순서:

1. **`.omc/SESSION_RESUME.md`** — 5분 onboarding. 무조건 첫 번째 읽기.
2. **`.omc/STATUS.md`** — 마일스톤 진척 + 열린 blocker.
3. `git log --oneline -10` — 최근 진척.
4. 필요 시 wiki 검색: `wiki_query --query "<topic>"` 또는 `wiki_list`.

### 영속 저장소 매트릭스

| 정보 종류 | 어디에 적나 / 어디서 읽나 |
|---|---|
| 프로젝트 규칙·금지사항 | 이 파일 (`CLAUDE.md`) |
| 플랜 / ADR / 마일스톤 | `.omc/plans/STRATEGY.md` |
| 미해결 stretch 질문 | `.omc/plans/open-questions.md` |
| 현재 마일스톤 상태 1줄 요약 | `.omc/STATUS.md` |
| 새 세션 5분 onboarding | `.omc/SESSION_RESUME.md` |
| 결정·디버깅·패턴·세션로그·용어집 (영구) | `.omc/wiki/` (`wiki_query/read/list/ingest`) |
| 단기 working memory (7일 prune) | `.omc/notepad.md` |
| 사용자/프로젝트 영구 메모리 (Auto Dream 정리 대상) | `~/.claude/projects/.../memory/MEMORY.md` |
| 코드 변경 로그 (과제 채점 자료) | `docs/AI_USAGE.md` |
| 외부 advisor 응답 (Codex/Gemini) | `.omc/artifacts/ask/` (gitignored) |

### Session-log discipline (필수)

> `wiki/convention/session-log-protocol-multi-session-continuity-discipline` 참고

- 30분 이상 작업 / 마일스톤 완료 / 비자명한 결정 후 → `wiki_ingest` 로 `category=session-log` 엔트리 추가
- 엔트리 포맷: Date / Focus / Activities / Observations / Decisions / Open items / Next-session priority

### 카테고리 가이드 (`.omc/wiki/`)

- `decision/` — ADR 외 결정. WHY 중심.
- `debugging/` — hypothesis 추적, 재현 노트. STATUS=OPEN/CLOSED.
- `pattern/` — 코드 패턴 (crash-proof, CRN sampling 등).
- `reference/` — 외부 인사이트, baseline 분석, glossary.
- `session-log/` — 매 세션 진척 일지 (`YYYY-MM-DD - <topic>` 슬러그).
- `convention/` — 프로젝트 컨벤션 문서.
- `architecture/` — 고수준 구조 (CoreCaptureAgent, evolution pipeline 등).
- `environment/` — 자주 쓰는 명령, 환경 설정 메모.

### Auto Dream 자동 발동

- 5 세션 + 24h 누적 시 `~/.claude/projects/.../memory/` 자동 정리
- `.omc/wiki/` 는 영향 받지 않음 (수동 영속)

### 종료 시 체크리스트

- [ ] 마일스톤 완료 시 `STATUS.md` 갱신
- [ ] 30분+ 세션 시 `wiki_ingest` session-log 엔트리
- [ ] 제출 대상 코드 수정 시 `docs/AI_USAGE.md` append
- [ ] 새 hypothesis 발견 시 wiki `debugging/` 페이지 추가

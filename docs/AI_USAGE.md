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

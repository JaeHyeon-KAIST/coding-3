# SESSION_RESUME — 5-minute onboarding for any new Claude or human session

**Last updated:** 2026-04-15 (pm — after H1 validation)

This is the **first thing to read** when resuming work on this project. STATUS.md and STRATEGY.md have more detail; this file makes you productive in 5 minutes.

## Step 1 — Read this 30-second TL;DR

This is **CS470 Coding Assignment #3**: Pacman Capture-the-Flag tournament agent for KAIST CS470 (UC Berkeley CS188 framework). Student ID `20200492`. We have a fully reviewed plan (6-way validation: Planner/Architect/Critic + Scientist/Codex/Gemini), 19 agents implemented (16 zoo + 3 monster; includes `zoo_reflex_h1test` diagnostic). **The M3 deadlock has been H1-CONFIRMED as seed-weight bias (NOT structural)** — 3W/2L/5T in 10 games on defaultCapture with `f_onDefense=0`, `f_numInvaders=-50` overrides. M4 tournament activation is the next action.

## Step 2 — Run these commands (~30 sec)

```bash
cd "/Users/jaehyeon/KAIST/26 Spring/인공지능개론/coding 3"
git log --oneline -5         # what was committed recently
ls minicontest/zoo_*.py minicontest/monster_*.py | wc -l   # 19 expected (16 zoo + 3 monsters)
```

## Step 3 — Read these in order (~3 min)

1. **`.omc/STATUS.md`** — milestone progress table + open blockers (1 min)
2. Wiki `session-log/session-2026-04-15-...` — what the last session did (1 min) — read with `wiki_read`
3. Wiki `debugging/m3-smoke-deadlock-...` — the OPEN critical issue (1 min) — read with `wiki_read`

## Step 4 — Know what to do next

Per the 2026-04-15 pm session-log (H1 validation), the **immediate next action** is:

> **M4 activation**: run `experiments/tournament.py` with full zoo (16) + monsters (3) on 3 layouts × 2 color swaps × 5 seeds. Generate first ELO table. Confirms whether H1 win-pattern generalizes beyond defaultCapture. (~2-3h)

If M4 tie rate stays ≥50% on multiple layouts, escalate to H2 instrumentation (STOP fallback over-firing — add a counter to `CoreCaptureAgent._safeFallback` and re-run one layout).

Stretch after M4: replicate H1 patch pattern for `zoo_minimax_h1test` / `zoo_mcts_h1test` for family consistency, then proceed to **M5 dry run (N=8, G=2)**.

## Project rules — must respect

(Already in `CLAUDE.md` which is auto-loaded; restated here for new humans):

1. **Never use global Python.** Always `.venv/bin/python` or `uv run --python .venv/bin/python`.
2. **Only numpy + pandas** — no torch, sklearn, tensorflow, pickle, requests.
3. **No multithreading in submission agent.** Training pipeline can use `multiprocessing.Pool`.
4. **Never modify framework files**: `baseline.py`, `capture.py`, `captureAgents.py`, `game.py`, `layout.py`, `util.py`, `distanceCalculator.py`, `keyboardAgents.py`, `mazeGenerator.py`, `textDisplay.py`, `graphicsDisplay.py`, `captureGraphicsDisplay.py`, `graphicsUtils.py`.
5. **Editable**: only `your_best.py`, `your_baseline1.py`, `your_baseline2.py`, `your_baseline3.py`, `myTeam.py`, plus our `zoo_*.py` and `monster_*.py` development files.
6. **Submission ZIP contains exactly one `.py`**: `20200492.py` (renamed from `your_best.py`). The `your_baseline*.py` files are NOT in the ZIP — they're for `output.csv` generation only.
7. **AI usage logging**: every edit to a submission-target file must append an entry to `docs/AI_USAGE.md` (assignment regulation).
8. **Session-log discipline**: at the end of any > 30-min work session or after a milestone, append a `session-log` wiki entry per `wiki/convention/session-log-protocol-...`.

## Where to find more (no need to read upfront)

| For information about... | Location |
|---|---|
| Full plan (all 11 sections) | `.omc/plans/STRATEGY.md` |
| Open / stretch questions | `.omc/plans/open-questions.md` |
| Detailed milestone status | `.omc/STATUS.md` |
| All decisions / observations / patterns / debugging notes | `.omc/wiki/` (use `wiki_query`) |
| Per-milestone code change log | `docs/AI_USAGE.md` |
| Project-specific terms | wiki `reference/glossary-cs470-a3-project-terms` |
| Working memory (7-day prune) | `.omc/notepad.md` |
| Persistent user context | `~/.claude/projects/.../memory/MEMORY.md` |

## When stuck

- Search prior sessions: `session_search --query "<topic>"` (also includes prior sessions on this project)
- Search wiki: `wiki_query --query "<topic>"`
- Read STRATEGY.md ADR section: `.omc/plans/STRATEGY.md` §0
- Ask user (don't barrel forward on ambiguous decisions)

## When done with this session

1. Summarize what you did + observations + decisions + next actions to `wiki_ingest` with `category=session-log`, `title="YYYY-MM-DD - <topic>"`
2. Update `.omc/STATUS.md` if any milestone state changed
3. Commit any code changes (per user request — don't auto-commit unless instructed)
4. Append to `docs/AI_USAGE.md` if submission-target code was modified

# SESSION_RESUME — 5-minute onboarding for any new Claude or human session

**Last updated:** 2026-04-15 (pm2 — after H1b rejection + strategic replan)

This is the **first thing to read** when resuming work on this project. STATUS.md and STRATEGY.md have more detail; this file makes you productive in 5 minutes.

## Step 1 — Read this 30-second TL;DR

This is **CS470 Coding Assignment #3**: Pacman Capture-the-Flag tournament agent for KAIST CS470 (UC Berkeley CS188 framework). Student ID `20200492`. Plan is 6-way validated; 20 agents implemented (17 zoo + 3 monster; includes H1/H1b diagnostics). **M3 deadlock resolved as seed-weight bias** (H1 confirmed: both-OFFENSE 3W/2L/5T). **H1b role-split rejected** (1W/2L/7T): simple fix insufficient. DEFENSIVE weights themselves weak; formation matters as much as weights. Next: H1c (capsule exploit, highest ROI) → M4 infra patches → M4 tournament.

## Step 2 — Run these commands (~30 sec)

```bash
cd "/Users/jaehyeon/KAIST/26 Spring/인공지능개론/coding 3"
git log --oneline -5         # what was committed recently
ls minicontest/zoo_*.py minicontest/monster_*.py | wc -l   # 20 expected (17 zoo + 3 monsters)
```

## Step 3 — Read these in order (~3 min)

1. **`.omc/STATUS.md`** — milestone progress table + open blockers (1 min)
2. Wiki `session-log/session-2026-04-15-...` — what the last session did (1 min) — read with `wiki_read`
3. Wiki `debugging/m3-smoke-deadlock-...` — the OPEN critical issue (1 min) — read with `wiki_read`

## Step 4 — Know what to do next

Per the 2026-04-15 pm2 session-log (H1b rejected), the **immediate next action** is:

> **H1c quick validation**: author `minicontest/zoo_reflex_h1c.py`. Inherits ReflexTunedAgent; both OFFENSE (H1 formation). Override `f_distToCapsule: 8 → 80` (10x). Goal: exploit baseline's capsule blindness — when we eat capsule, baseline defender scared 40 ticks; baseline weights ignore scared → it self-destructs chasing us. Prediction: 5W+ if hypothesis correct. ~15 min.

If H1c fails too (< H1's 30%): pivot to H1d (DEFENSIVE rebalance: `f_patrolDist 30 → 5`, `f_invaderDist 80 → 400`). This is the signal that ALL single-dict tunings are insufficient, and M6 evolution is the only path — which makes fixing `evolve.py:140-142` NotImplementedError swallow the critical path.

After a successful diagnostic hypothesis: activate **M4 infra patches** (architect audit: CSV append + resume, seed workaround via `-l RANDOM<seed>`, `start_new_session=True`, sliding futures window, tmux+caffeinate launch; ~1h). Then M4 tournament across 3 layouts × all zoo.

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

# SESSION_RESUME — 5-minute onboarding for any new Claude or human session

**Last updated:** 2026-04-15 (pm4 — after 40-game apples-to-apples reverification; single-dict saturated, M4 infra pivot)

This is the **first thing to read** when resuming work on this project. STATUS.md and STRATEGY.md have more detail; this file makes you productive in 5 minutes.

## Step 1 — Read this 30-second TL;DR

**CS470 Coding Assignment #3**: Pacman Capture-the-Flag tournament agent (KAIST, UC Berkeley CS188 framework). Student ID `20200492`. 21 agents implemented (18 zoo incl. 3 H1-family + 3 monsters). 40-game apples-to-apples reverification (pm4) produced the canonical comparison vs `baseline.py` on `defaultCapture`:

| Agent | W / L / T | Win% | Net (W−L) |
|---|---|---|---|
| zoo_reflex_tuned (control) | 0 / 0 / 40 | 0% (100% tie) | 0 |
| zoo_reflex_h1test (both-OFFENSE) | 14 / 14 / 12 | **35%** | 0 |
| zoo_reflex_h1b (role-split, RESURRECTED) | 12 / 4 / 24 | 30% | **+8** |
| zoo_reflex_h1c (capsule-exploit, new) | 8 / 2 / 30 | 20% | +6 |

Key reversals: **pm2's H1b rejection was wrong** — H1b has the best net score (+8) and lowest loss rate (10%). **H1 leads on raw win% (grading metric) at 35%**, but 14/40 vs p=0.51 rejects the 51% threshold at 95% (z=-2.07). **Single-dict tuning is statistically saturated**; M6 CEM evolution is now the only viable path to the 40pt code score. ReflexTuned 100% tie confirms the original deadlock is structural.

## Step 2 — Run these commands (~30 sec)

```bash
cd "/Users/jaehyeon/KAIST/26 Spring/인공지능개론/coding 3"
git log --oneline -5         # what was committed recently
ls minicontest/zoo_*.py minicontest/monster_*.py | wc -l   # 21 expected (18 zoo + 3 monsters)
```

## Step 3 — Read these in order (~3 min)

1. **`.omc/STATUS.md`** — canonical 40-game table + all open blockers (1 min)
2. Wiki `session-log/2026-04-15-pm4-40-game-apples-to-apples-reverification-h1b-redem` — what pm4 concluded (1 min) — read with `wiki_read`
3. Wiki `debugging/experiments-infrastructure-audit-pre-m4-m6` — the two 🔴 blockers that M4 must fix (1 min) — read with `wiki_read`

## Step 4 — Know what to do next

Per pm4 reverification, **do NOT attempt another single-dict variant** (H1d etc.). Single-dict search is statistically exhausted. The immediate critical path:

> **M4 infrastructure patches** (~1h total, all audited in wiki `debugging/experiments-infrastructure-audit-...`):
> 1. **🔴 `evolve.py:140-142`** — fix `NotImplementedError` swallow. Without this, a 20h M6 run emits noise weights while appearing to succeed. Highest ROI; blocks everything.
> 2. **🔴 `run_match.py:72`** — seed plumbing broken; apply `-l RANDOM<seed>` workaround so CRN seed axis becomes real.
> 3. **🟡 `tournament.py`** — CSV-append + fsync per row, sliding futures window (workers×4). ~40 lines. Makes mid-run kill survivable at M6 scale.
> 4. **🟡 `run_match.py:80`** — add `start_new_session=True` + `os.killpg` on timeout. 1-line fix.
> 5. **🟡 `experiments/select_top4.py`** — implement `flatten_agent` AST concatenation (blocks M7).

After infra patches: **M4 tournament activation** — `experiments/tournament.py` across all 21 agents × 3 layouts (defaultCapture, + 2 more) × 5 seeds → first real ELO table. **M5 dry run** (N=8, G=2) on small genome → verify evolution pipeline end-to-end. **M6 full CEM campaign** (~20h).

Also queued (before M8): **populate `your_baseline1/2/3.py`** with our strongest variants (currently all DummyAgent random copies) so `output.csv` produces the required 4-way comparison table for the report.

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

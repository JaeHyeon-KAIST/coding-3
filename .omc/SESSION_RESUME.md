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

**Current state (2026-04-15 pm9)**: M4a, M4b-1/2/3, M4c-1 infrastructure all landed and committed. M4-v1/v2 tournaments produced canonical ELO (h1test 50% vs baseline, h1b best net +8). Pre-α preflight complete: baseline measured at 7.74s/match, ADR written, test plan (T1-T4) ready.

**α-core is DONE as of pm12.** Commits: `b625dc8` (α-1 parallelization), `ad56ebe` (α-2 resume), CLI plumbing folded into α-1, T1-T4 all PASS. α-5 (truncated eval) is the only α sub-tier deferred — user paused before greenlighting it.

**Immediate next action = M4b-4 (M5 dry-run, ~13-20 min parallel wall):** `evolve.py --phase 2a --n-gens-2a 2 --pop 8 --games-per-opponent-2a 24` with the canonical 3-opponent dry-run pool. Check fitness trend, elite selection, gen JSON emit, resume after one mid-gen kill.

**Then M6 — split into 4 resumable tiers** (do NOT treat as a single 23h block). Each tier is independent via `evolve.py --resume-from`; user judges at each gate whether to continue or pivot:

- **M6-a** (~1.5h parallel): Phase 2a smoke, 2 gens × 40 pop. Go/No-go signal = best_ever fitness exceeds h1test seed baseline. If no: diagnose (seed weights wrong? opponent pool too easy? restart with broader σ).
- **M6-b** (~4h parallel): Phase 2a full (gens 3-10), resuming from M6-a's gen 1. Emits `2a_gen009.json` containing the Phase 2b initial mean.
- **M6-c** (~2.75h parallel): Phase 2b early (gens 11-15). Split W + monster_rule_expert in pool. First look at whether split-W gains over shared-W.
- **M6-d** (~8.25h parallel): Phase 2b late (gens 16-30) + final_weights.py emission. Overnight / weekend block.

Launch each tier via `tmux new -d -s m6 'caffeinate -i .venv/bin/python experiments/evolve.py --phase 2a --n-gens-2a N --resume-from ...'`. Watchdog via Monitor tool on `artifacts/{phase}_gen*.json` stall.

**Then M7** (`flatten_agent` AST + select_top4 + family-floor). **M8** (output.csv: populate `your_baseline{1,2,3}.py` first). **M9 — split**:
- **M9-a** (~1.5h): Intro (8pt) + Methods (20pt)
- **M9-b** (~1.5h): Results (20pt) + ablation figures
- **M9-c** (~1h): Conclusion (12pt) + revise

**M10** (~15min): submission packaging.

## Tier policy (project convention)

Every milestone that needs more than ~1h of uninterrupted compute/work is split into resumable sub-tiers with Go/No-go gates. User decides after each gate. No single step commits more than ~4h.

Context for every follow-up session: start by reading this file (top-to-bottom), then `.omc/STATUS.md`, then the wiki pages referenced in the Option α step above.

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

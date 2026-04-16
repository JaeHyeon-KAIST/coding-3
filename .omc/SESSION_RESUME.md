# SESSION_RESUME — 5-minute onboarding for any new Claude or human session

**Last updated:** 2026-04-16 (pm18 — Phase 1 B1+C4 done, committed; A1 17-dim Order 1 ▶️ running on server, gens 0-2 showing CEM learning 0.112→0.483)

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

**Current state (2026-04-16 pm18 end)**: Phase 1 complete and committed. A1 17-dim (Order 1) launched and running on server with real learning signal.

**What's done since pm17**:
- ✅ Phase 1 B1 (20-dim features, commit `379dc74`) — f_scaredGhostChase, f_returnUrgency, f_teammateSpread. seed_weights = 0.0 (evolution discovers magnitudes).
- ✅ Phase 1 C4 (commit `a1b5569`) — MCTS time-budget polling 0.8s/move in zoo_mcts_{heuristic,random,q_guided}.py. Submission-safe under capture.py's 1s warning.
- ✅ A1 17-dim Order 1 launched on server 06:37 with 11-opp no-MCTS pool + `--master-seed 42 --workers 16 --init-mean-from h1test --phase both`.

**A1 in flight, first 3 gens**:
| gen | best | mean | snr | wall |
|---|---|---|---|---|
| 0 | 0.112 | 0.007 | 0.61 | 2796.8s |
| 1 | 0.181 | 0.026 | 0.91 | 2895.4s |
| 2 | 0.483 | 0.099 | 1.10 | 2926.9s |

CEM learning confirmed (best 4.3× over 3 gens, snr cleared 1.0 at gen 2). Wall stable ~47-48 min/gen → ETA finish ~00:40 next day. Per-gen wall is ~2× the wiki estimate, so total ~18-19h vs planned 10h — still within overnight budget.

**Server commits needed**: `git pull origin main` to get `379dc74` + `a1b5569` (pm18 B1+C4). Mac already has them. A1 does NOT need these (it's running 17-dim reflex, not 20-dim or MCTS).

## ⚠️ Next-session immediate actions

Read in order:
1. THIS file
2. `.omc/STATUS.md` (milestone table + Critical observations — look for "A1 17-dim full-scale evolution learning confirmed (pm18)" and "Order 6 blocker")
3. wiki `session-log/2026-04-16-pm18-phase1-b1-c4-done-a1-launched-learning-confirmed` (the pm18 record)
4. **wiki `decision/next-session-execution-plan-performance-max-6-phase-pipeline`** — the FULL pm17 plan (still canonical — Orders 2-8 unchanged)
5. wiki `environment/remote-compute-infra-wsl2-ryzen-7950x-server-jdl-wsl` — server how-to

**FIRST: verify A1 state (A1 was running when pm18 ended):**
```bash
ssh jdl_wsl "tmux capture-pane -t work -p -S -40 | tail -25 && echo --- && pgrep -af evolve.py | head -3 && echo --- && ls experiments/artifacts/2[ab]_gen*.json 2>/dev/null && echo --- && tail -25 logs/phase2_A1_17dim_20260416-0637.log"
```

Three possible outcomes:
- **A1 STILL RUNNING**: `pgrep` shows 17 processes, artifacts has ≥3 `2a_gen*.json` files, log tail shows recent `[evolve] ... gen=N ...` line. → Wait for completion OR checkpoint-resume for Order 2.
- **A1 FINISHED SUCCESSFULLY**: `pgrep` shows nothing, artifacts has `2a_gen000-009.json`, `2b_gen000-019.json`, `final_weights.py`. → Archive to `experiments/artifacts/phase2_A1_17dim/`, commit log, launch Order 2.
- **A1 CRASHED / STUCK**: log ends with Traceback / BrokenProcessPool / OOM, OR pgrep shows 17 procs but log hasn't advanced in 60+ min. → Read the error, decide fix vs restart.

**THEN**: if A1 done, archive artifacts + launch Order 2 (A1+B1 20-dim, init_mean=h1test, same 11-opp pool WITHOUT mcts until Order 6 fix). If A1 still running with good trajectory, leave it and do Phase 1 follow-up (Order 6 `ZOO_MCTS_MOVE_BUDGET` env override patch — see STATUS.md Order 6 blocker row).

## What we're doing (pm17 user decision)

**User has time slack, wants performance-max (code 40pt + tournament extra 30pt). Full 6-phase pipeline.** Fixed `--master-seed=42` for all Phase 2 candidates (apples-to-apples ranking) → Phase 5 multi-seed on top-5 (cross-platform robustness).

Critical path with parallelism:
- **First slot (~10h calendar)**: launch A1 17-dim baseline candidate on server (overnight, control champion) WHILE coding Phase 1 B1+C4 on Mac in parallel.
- **Subsequent slots**: queue server with B1-extended candidates (Order 2-7), Mac handles Phase 3 hybrid coding + Phase 5 validation + Phase 6 flatten/report.

Total budget ~5-7 days, mostly server overnight.

**Dispatch is case-by-case** — NOT "always server". See wiki page for the venue decision matrix.

**FIRST decision in next session**: confirm pm17 6-phase plan still wanted. If yes, launch the parallel first slot (server A1 17-dim + Mac Phase 1 coding). `evolve.py --phase 2a --n-gens-2a 2 --pop 8 --games-per-opponent-2a 24` with the canonical 3-opponent dry-run pool. Check fitness trend, elite selection, gen JSON emit, resume after one mid-gen kill.

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

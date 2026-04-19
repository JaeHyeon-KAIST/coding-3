# SESSION_RESUME — 5-minute onboarding for any new Claude or human session

**Last updated:** 2026-04-19 pm24 end — Order 4 Phase 2a gen 0 launched (ETA ~18h, master-seed=2026, init=a1, HOF pool=A1+O2+O3). pm24 implemented 8 new rc (6 pass, 2 drop).

## pm25 TL;DR (NEXT SESSION)

- **pm24 주요 성과**: 8 new rc implemented + full 40g HTH. 6 pass: rc29/rc44 (92.5%), rc48/rc50 (90%), rc31 (87.5%), rc28 (82.5%). 2 drop: rc30/rc34 (random top-K catastrophic).
- **pm25 할 일**:
  1. `ssh jdl_wsl "tmux capture-pane -t work -p -S -30 | tail -20"` — Order 4 상태 확인.
  2. Order 4 완료 (ETA 2026-04-20 ~06:00 KST) → HTH battery → O4 HOF wrapper 생성 또는 A1 유지.
  3. Phase 4 round-robin tournament 준비 (23 rc + A1/O2/O3/O4 + D-series = ~30 candidates).
  4. M7 flatten 계획 수립 (champion = A1 or best rc46/rc02/rc16/rc29/rc44).
- **서버 상태**: Order 4 running, 18 evolve processes, ETA ~18h.
- **First actions**: `.omc/STATUS.md` pm24 headline → Order 4 server check → Phase 4 plan.

## pm23-24 TL;DR (historical)

- **pm22**: Round-robin 후보 80개 수집 (Codex 18 + Gemini 17 + 기존 50 + user 아이디어). `rc-pool.md` 생성.
- **pm23**: 17 rc implemented in one session (rc02-rc08, rc09/11/15/16/17/19, rc27/32/33/45/46). rc02 + rc16 공동 1위 (100%), rc32 97.5%. rc18 dropped (FAIL).
- **pm24**: 8 more rc (rc28/29/30/31/34/44/48/50). 6 pass, 2 drop. Batch B learned: random top-K injection catastrophic; deterministic top-K safe.

## pm22 TL;DR (historical)

- Autopilot cron으로 Order 3 자동 실행 (Phase 2a 완료, Phase 2b gen 6/20 진행 중)
- 후보군 총 정리 세션 (코드 구현 X)
- CCG advisor (Codex + Gemini) 사용해 추가 후보 35개 수집
- `rc##` naming 도입 (pm은 세션 타임라인, rc는 작업 항목)
- 문서 신규 2개: `rc-pool.md`, `pm23-handoff.md`

## pm20 TL;DR (historical)

3-axis parallel development (CEM evolution + rule-based hybrids + paradigm hybrids) with 17 tasks tracked; CCG added particle filter + opponent classifier + endgame lockout + capsule proxy camping + stochasticity; robustness-first over peak (180-agent tournament); **never discard ≥50% baseline candidates** (all go to Phase 4 round-robin).

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
2. `.omc/STATUS.md` (milestone table — look for "A1 HTH validation (pm19)" and "CCG plan review (pm19)")
3. wiki `session-log/2026-04-17-pm19-a1-validated-order-2-launched-performance-max-pivot` (pm19 record — CCG advisor outputs archived there)
4. (optional) wiki `decision/next-session-execution-plan-performance-max-6-phase-pipeline` — superseded by pm19 scope tweaks; keep only Orders 2-4 queue, drop Orders 5-7 per CCG consensus unless buffer remains

**FIRST: verify Order 2 state** (launched 2026-04-17 11:55, ~18h expected):
```bash
ssh jdl_wsl "tmux capture-pane -t work -p -S -40 | tail -25 && echo --- && pgrep -af evolve.py | wc -l && echo --- && ls experiments/artifacts/2[ab]_gen*.json 2>/dev/null | head -30 && echo --- && tail -25 logs/phase2_A1_B1_20dim_*.log"
```

Three outcomes and actions:
- **RUNNING**: `pgrep` shows ≥17 processes. Wait or work on Phase 3 D-series coding on Mac in parallel.
- **FINISHED**: `pgrep` shows 0, artifacts has 2a_gen000-009 + 2b_gen000-019 + `final_weights.py`. → Archive to `experiments/artifacts/phase2_A1_B1_20dim/`, run HTH battery vs baseline+monster via `experiments/hth_battery.py`, compare to A1's 79% baseline WR. If Order 2 > A1: update champion. Then launch Order 3 (A2+B1 h1b init).
- **CRASHED**: check log for Traceback. Fix, re-archive any partial artifacts, decide restart vs skip.

**Phase 2 queue status (pm19 revised — Orders 5/7 dropped per CCG low-ROI)**:
- A1 (17-dim h1test) ✅ fitness 1.065, baseline 79% PASS
- Order 2 (A1+B1 20-dim h1test init) ▶️ running
- Order 3 (A2+B1 h1b init) — queued after Order 2
- Order 4 (A5+B1 (h1test⊕h1b)/2 hybrid init) — queued after Order 3
- Orders 5/7 (minimax / expectimax containers) — DROPPED (low ROI per Codex + Gemini consensus)
- Order 6 (MCTS container) — DROPPED (MCTS wall >> 120s timeout + machine-dependent time polling)
- Order 8 (h1c init) — stretch IF Orders 2-4 all underwhelm

**Phase 3 D-series coding plan** (Mac, ~10-12h, parallel to server Orders 2-4):
- D1 role-swap: dynamic OFFENSE↔DEFENSE swap on (carrying ≥ threshold → return) + (invaders ≥ 2 → both defensive)
- D2 capsule timing: eat capsule only when (a) ghost_dist ≤ 3 AND carrying ≥ 5, OR (b) opponents ate our capsule
- D3 endgame mode: last 100 moves, leading → defend; behind → all-in rush ignoring ghost penalty
- Dead-end-guard: hardcoded override when in dead-end with ghost ≤ 3 (overrides reflex evaluator)
- Deliverable: 4 variants per champion (bare / +D1 / +D2 / +D1+D2+D3)

## ⚡ pm20 KEY DECISIONS (must resolve before heavy compute)

### Decision 1 — Orders 2-4 are BIT-IDENTICAL as currently configured (pm19 late discovery)

pm17 plan's Orders 3 (h1b init), 4 (hybrid init) would produce IDENTICAL results to Order 2 because:
- `_H1B_FEAT_SEED = list(_H1TEST_FEAT_SEED)` in evolve.py — same vector
- `--master-seed 42` fixed across all → identical Gaussian sampling
- Same 11-opp pool
- Order 4 "hybrid" option NOT implemented in `--init-mean-from` CLI

**Fix options** for real diversification in Orders 3/4:
- (a) Different `--master-seed` per Order (e.g., 1001, 2026) — trivial
- (b) Expand `KNOWN_SEEDS_PHASE_2A` + `--init-mean-from` with `"a1"` option (seed from A1 final_weights)
- (c) HOF pool rotation — create `zoo_reflex_A1.py` wrapper, add to Order 3+ pool so evolution must beat A1 (AlphaZero-lite)

Combo (a+c) recommended: different seeds + HOF pool → genuine champion diversity for Phase 4 ELO meaningfulness.

### Decision 2 — Hybrid paradigm (Path 3) trial?

CCG analysis (wiki `decision/pm19-ccg-hybrid-paradigm-analysis-path-1-vs-2-vs-3-mcts-offen`):
- **Codex**: Path 3 tightly-scoped with hard kill. 1-2 days engineering + 18h CEM.
- **Gemini**: Stick with Path 1, polish report. Overengineering risk.
- **Claude synthesis**: given user's performance-max + 10-day budget, lean Codex. Prep: M7 flatten A1 first to LOCK submission candidate, then attempt Path 3 with clear abort criteria.

**pm20 action**: after Order 2 HTH, decide: (A) Path 3 trial, (B) A1-only polish, (C) other.

**Phase 4 tournament** (post Orders 2-4): round-robin ELO, ~1-2h server wall.

**Phase 5 multi-seed** (server + Mac): top-3 × 200 games × 10 seeds × 4 layouts. ~1h server + 1-2h Mac cross-platform check.

**Phase 6 submission** (Mac, ~15-20h report + misc):
- M7 flatten_agent AST implementation (skeleton at `experiments/select_top4.py`)
- M8 output.csv (auto via capture.py 4-loop)
- M9 ICML 2+ page report with 4+ ablation figures
- M10 package zip with sha256

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

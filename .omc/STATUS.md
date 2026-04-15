# STATUS — CS470 A3 Pacman Capture-the-Flag

**Last updated:** 2026-04-15
**Update protocol:** revise this file at end of each session and after each milestone (per `wiki/convention/session-log-protocol`).

## Headline

Plan validated, infrastructure built, **deadlock observation flagged** before scaling to evolution. Currently paused after M3.

## Milestone progress (M-series from `.omc/plans/STRATEGY.md` §10)

| # | Milestone | Status | Verification | Commit |
|---|---|---|---|---|
| Plan | Ralplan + Architect/Critic + Scientist/Codex/Gemini consensus | ✅ APPROVED | 6 reviewers | `8c9fe66` |
| M1 | `CoreCaptureAgent` base + dummy smoke | ✅ Done | 10/10 exit 0, 0 crash | `42e8215` |
| M2a | Shared `zoo_features.py` + 4 reflex variants | ✅ Done | 20/20 exit 0, 0 crash, all tied | `372f15f` |
| M2b | 3 minimax variants (d2, d3_opp, expectimax) | ✅ Done | 4/4 exit 0 (partial smoke) | `927b4ce` |
| M2c | 3 MCTS variants (random/heuristic/q_guided) | ✅ Done | 3/3 exit 0 | `9e278b4` |
| M2d | 2 approxQ variants (v1, v2_deeper) | ✅ Done | 6/6 exit 0 | `927b4ce` |
| M3 | 3 hand-tuned monster agents | ✅ Done | 3/3 exit 0 | `9e278b4` |
| **M3-verify** | Smoke for skipped MCTS + monsters | ✅ Done | 7/7 exit 0 | `9e278b4` |
| **M4** | Tournament pipeline activation | ⏳ NEXT | — | — |
| M5 | Evolution dry run (N=8, G=2) | ⏳ Pending | — | — |
| M6 | Full evolution campaign (~20h) | ⏳ Pending | — | — |
| M7 | select_top4 + flatten + populate slots | ⏳ Pending | — | — |
| M7.5 | Time-budget calibration | ⏳ Pending | — | — |
| M8 | Final `output.csv` for report | ⏳ Pending | — | — |
| M9 | LaTeX ICML report | ⏳ Pending | — | — |
| M10 | Submission packaging (zip, sha256) | ⏳ Pending | — | — |

## Critical observations / blockers

🔴 **DEADLOCK PATTERN** — across 47 smoke games, 0 wins for any of our 14 tuned agents (5 ties + 2 baseline-wins for monsters). Even hand-tuned monster agents (designed to be strong) tie or lose to baseline. This is qualitatively different from "weak agents losing"; it's mutual scoreless stalemate. Six hypotheses tracked in wiki `debugging/m3-smoke-deadlock-...`. Highest probability: SEED_WEIGHTS too defense-heavy. Must validate before committing to ~20h M6 campaign.

🟡 **Submission flatten not yet implemented** — `experiments/select_top4.py` is a skeleton; the `flatten_agent` function raises `NotImplementedError`. Required by M7. Plan has the recipe, but the AST-based concatenation logic needs implementation.

🟡 **Time calibration deferred to M7.5** — `MOVE_BUDGET = 0.80s` is a placeholder. Algorithmic bounds (`MAX_ITERS=1000`, `MAX_DEPTH=3`, `ROLLOUT_DEPTH=20`) are the actual time controllers during dev. Final values come from M7.5 measurement on dev hardware + `taskset/cpulimit` TA simulation.

## Asset inventory

**Source files (`minicontest/`):**
- 1 `zoo_core.py` (CoreCaptureAgent base)
- 1 `zoo_features.py` (17-feature extractor)
- 1 `zoo_dummy.py` (M1 smoke target)
- 4 reflex variants (`zoo_reflex_{tuned,capsule,aggressive,defensive}.py`)
- 3 minimax variants (`zoo_minimax_{ab_d2,ab_d3_opp}.py`, `zoo_expectimax.py`)
- 3 MCTS variants (`zoo_mcts_{random,heuristic,q_guided}.py`)
- 2 approxQ variants (`zoo_approxq_{v1,v2_deeper}.py`)
- 3 monster agents (`monster_{rule_expert,mcts_hand,minimax_d4}.py`)
- **Total: 18 agents (15 zoo + 3 monsters)**

**Pipeline scripts (`experiments/`):**
- `run_match.py` — single-game subprocess wrapper (CPU pin support)
- `tournament.py` — `ProcessPoolExecutor` round-robin (CRN pairing)
- `evolve.py` — CEM 2-phase driver (skeleton, depends on weight-override protocol)
- `select_top4.py` — ELO selection + family-floor + flatten (skeleton; flatten unimplemented)
- `verify_flatten.py` — AST + sha256 + import smoke gate

**Documentation:**
- `CLAUDE.md` — project rules (auto-loaded each session)
- `.omc/plans/STRATEGY.md` (746 lines) — full plan, ADR
- `.omc/plans/open-questions.md` (50 lines) — stretch / future items
- `.omc/wiki/` — long-term knowledge base (just bootstrapped this session)
  - `reference/glossary-cs470-a3-project-terms`
  - `convention/session-log-protocol-multi-session-continuity-discipline`
  - `debugging/m3-smoke-deadlock-0-win-pattern-across-all-tuned-agents`
  - `session-log/session-2026-04-15-m3-smoke-completion-deadlock-observation`
- `docs/AI_USAGE.md` — per-milestone code change log (assignment requirement)
- `.omc/notepad.md` — priority context + working memory
- `.omc/STATUS.md` (this file)
- `.omc/SESSION_RESUME.md` — new-session 5-minute onboarding

## Next-session quick start

**STOP and read `.omc/SESSION_RESUME.md` first.** That's the 5-minute onboarding. This STATUS.md is the deeper detail.

If you skipped SESSION_RESUME: the immediate next action is **H1 quick validation** (patch one zoo variant with `f_onDefense=0`, run 10 games, see if it scores). Then **M4 tournament activation**.

## Health summary

| Metric | Value | Health |
|---|---|---|
| Code crashes in 47 smoke games | 0 | 🟢 |
| Timeout forfeits | 0 | 🟢 |
| Total agents implemented | 18 | 🟢 |
| Agents that have beaten baseline | 0 | 🔴 (deadlock — see hypothesis) |
| Plan reviewers approving | 6 / 6 | 🟢 |
| Compute budget for M6 (planned) | ~20h | 🟢 |
| Days until submission deadline | TBD (check assignment PDF for due date) | 🟡 |

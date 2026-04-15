---
title: "Glossary — CS470 A3 project terms"
tags: ["glossary", "terminology", "reference", "onboarding"]
created: 2026-04-15T00:13:08.209Z
updated: 2026-04-15T00:13:08.209Z
sources: []
links: []
category: reference
confidence: medium
schemaVersion: 1
---

# Glossary — CS470 A3 project terms

# Glossary — CS470 A3 Pacman Capture-the-Flag

Project-specific terms encountered across plans, code, and discussions. Updated as new vocabulary arises.

## File / Directory Vocabulary

- **`minicontest/`** — UC Berkeley CS188 framework (provided, mostly read-only). Contains `capture.py` (game engine), `baseline.py` (reference opponent), and our zoo/monster source files (`zoo_*.py`, `monster_*.py`).
- **`zoo`** — set of agent variants under development. Lives in `minicontest/zoo_*.py` for `capture.py -r <name>` import compatibility (NOT under `experiments/zoo/` despite the plan's notional layout). Open-ended — add as many as needed.
- **`monster`** — strong reference agents used as evaluation/training opponents only; never submitted. Three orthogonal strategic profiles: territorial defender / aggressive raider / adaptive exploiter.
- **`your_best.py`** — submission slot. Renamed to `{Student_ID}.py` (`20200492.py`) at submit. The ONLY file in the submission ZIP.
- **`your_baseline1~3.py`** — local-only comparison agents. Used by `capture.py -r 20200492 -n 10` to generate `output.csv`. NOT in submission ZIP.
- **`select_top4.py`** — script (not yet implemented; skeleton in `experiments/`) that picks ELO-top zoo agents and copies them into the four submission slots.
- **`experiments/`** — development infrastructure (training pipelines, evaluation, analysis). NOT submitted. Source: tournament.py, evolve.py, run_match.py, select_top4.py, verify_flatten.py.

## Code Components

- **`CoreCaptureAgent`** — shared base class (defined in `zoo_core.py`) for all zoo + monster agents. Provides crash-proof wrappers, APSP cache, TeamGlobalState singleton.
- **`zoo_features.py`** — shared 17-feature extractor module. Used by reflex/minimax/MCTS variants. NOT used by `monster_rule_expert.py` or `zoo_approxq_*.py` (those have their own feature bases for methodological contrast).
- **`TeamGlobalState`** / **`TEAM`** — module-level singleton shared between two teammates (same Python process). Tracks role assignment, last-seen enemies, capsule eaten timestamps.
- **role** — `"OFFENSE"` or `"DEFENSE"` per agent. Stored in `TEAM.role[agent_index]`. Switches based on score lead, invader count, and hysteresis.
- **hysteresis** — N-turn delay before switching role; default 3, drops to 2 when losing, immediate when invader carrying food. Anti-thrash mechanism.
- **`_safeFallback`** — last-resort action selector inside `CoreCaptureAgent`. Returns `random.choice(legal - {STOP})`, falls back to `STOP` only if no legal non-STOP exists. STOP is "almost always death" in tournament play.
- **`MOVE_BUDGET`** — per-move time cap (currently 0.80s pre-calibration; M7.5 will set final value). NOT hardcoded as a constant; algorithmic bounds are primary control.
- **`MAX_ITERS`** / **`MAX_DEPTH`** / **`ROLLOUT_DEPTH`** — algorithmic time controllers (1000 / 3 / 20 default). Used during Dev phase instead of time polling. Updated by M7.5 calibration.

## Algorithm / Search Vocabulary

- **CEM (Cross-Entropy Method)** — evolutionary algorithm we use for weight optimization. Iteratively samples from a Gaussian, selects elites, refits Gaussian to elites. 2-phase schedule: Phase 2a (32 dims, 10 gens) → Phase 2b (52 dims, 20 gens).
- **CMA-ES** — fallback if CEM drifts. Adapts covariance matrix; better for correlated dimensions.
- **(1+λ)-ES** — alternative simple ES; not currently used.
- **N** / **ρ (rho)** / **elite count** — N=40 population, ρ=0.35 elite fraction → 14 elites per generation.
- **σ (sigma)** — Gaussian std dev for CEM sampling. Starts 30, decays ×0.9/gen, floor 2.
- **CRN (Common Random Numbers)** — variance-reduction technique. Each (genome, opponent, layout, seed) plays BOTH color assignments to pair correlated outcomes. Halves opponent-pool variance at 2× game cost.
- **sequential halving** — elite re-evaluation: top-⌈N/2⌉ get extra games, then top-⌈N/4⌉, etc. until ranking confidence-bound. Used after initial fitness computation each gen.
- **fitness function** — `pool_win_rate − 0.5·crash_rate − 0.5·stddev_win_rate + (Phase 2b only) 0.15·monster_win_rate`. Risk-sensitive (StdDev penalty from Gemini suggestion).
- **monster_bonus** — fitness bonus per win against monster opponent. Set to 0.15 (down from 0.3 per Scientist's misalignment concern).
- **HALL_OF_FAME** — past-generation champion archive kept in opponent pool. Prevents overfit to current population.
- **niching** — diversity preservation by sub-population per algorithmic family. Reflex sub-pop, minimax sub-pop, MCTS sub-pop, hybrid sub-pop.
- **restart trigger** — if best-ever stagnates 5 gens, inject 8 random genomes + reset σ×2.
- **stagnation_count** / **drift** — sanity monitor. If `(elite_mean − gen_mean) / gen_std < 1.0` for 3 consecutive gens, evolution is drifting (not learning) — alert.
- **MCTS / UCT / UCB1** — Monte Carlo Tree Search with Upper Confidence Bound for trees. C = sqrt(2) ≈ 1.41 default.
- **Rollout / playout / simulation** — random or heuristic action sequence from a leaf to terminal/depth-limit. Random rollouts FAIL in this domain (per research); heuristic-argmax or no-rollout (depth-0) required.
- **UCB-guided leaf-evaluator search** — honest naming for "MCTS depth-0". UCB1 tree expansion + direct feature-evaluator at leaves (no rollout simulation). Mathematically NOT Monte Carlo.
- **opponent-model reduction** — minimax simplification. Frozen-far-enemy (1-enemy reduction) is the fallback; 2-enemy adversarial is the primary target.

## Engine Constants (from `capture.py`)

- **`SCARED_TIME = 40`** — moves enemies stay scared after we eat capsule.
- **`MIN_FOOD = 2`** — food threshold to trigger win condition.
- **`TOTAL_FOOD = 60`** — typical food count per side. Win = return `(TOTAL_FOOD/2 - MIN_FOOD) = 28` dots.
- **`CRASH_PENALTY = 100`** — score penalty for unhandled exception. Almost always flips game outcome.
- **`KILL_POINTS = 0`** — eating opponent doesn't directly score. Only `dumpFoodFromDeath` (drops carried food back to opponent's side).
- **`getMoveWarningTime = 1s`** — soft warning threshold per move.
- **`getMoveTimeout = 3s`** — hard SIGALRM forfeit threshold per move.
- **`getMaxTimeWarnings = 2`** — 3rd warning = game loss.
- **`SIGALRM`** / **`TimeoutFunctionException`** — framework-owned timeout mechanism (`util.py:589-622`). Agent code MUST NOT register own signal handler. MUST re-raise `TimeoutFunctionException` before generic `except`.

## Map / Layout Vocabulary

- **layout** — Pacman map definition (e.g., `defaultCapture`, `officeCapture`, `jumboCapture`, `RANDOM[seed]`).
- **dividing line** / **midline** — column separating Red and Blue territory. Crossing toggles ghost↔Pacman.
- **homeFrontier** — list of cells on our side adjacent to the dividing column.
- **bottleneck** — cell whose removal disconnects neighborhood (BFS articulation point approximation). Strategic choke.
- **dead-end** / **deadEnd** — corridor cell with one non-back exit and depth ≥ 3.
- **APSP (All-Pairs Shortest Path)** — dict `{(p1, p2): dist}` precomputed in `registerInitialState` for O(1) maze distance lookup. Generous use of 15s init budget (Gemini-flagged).

## Game-State Vocabulary

- **`numCarrying`** — food dots an agent currently carries.
- **`numReturned`** — food dots successfully cashed in (returned to home side).
- **`scaredTimer`** — ticks remaining for an agent to be scared.
- **`isPacman`** — True when agent is in enemy territory (eats food).

## Submission / Grading Vocabulary

- **administrative floor** — ≥51% win rate per PDF rubric. NOT statistically detectable at n=80 (Wilson CI [0.40, 0.62] includes 0.50). Rubric satisfaction only.
- **statistical gate** — ≥65% win rate at n=80 (Wilson lower bound 0.538). Distinguishable from random.
- **stretch** — ≥90% win rate (Wilson lower bound 0.815, strongly significant).
- **family-floor clause** — `select_top4.py` rule: if best-in-family wins <51% vs baseline, fall back to next family or relabel.
- **flatten** — concatenate `zoo_core.py` + `zoo_features.py` + `zoo_<name>.py` into a single self-contained submission file. Strips inheritance and helper imports.
- **verify_flatten** — `experiments/verify_flatten.py` — AST + allowed-imports + forbidden-pattern grep + sha256 identity + import-smoke. Submission gate.
- **output.csv** — table generated by `python capture.py -r 20200492 -n 10`. Contains your_best vs each of your_baseline1~3 + baseline match results. Source for report Results section.

## Milestones (M-series)

- **M1** — `CoreCaptureAgent` base + dummy. ✅ done.
- **M2a/b/c/d** — Build zoo (reflex / minimax / MCTS / approxQ families). ✅ done.
- **M3** — Hand-tuned monster reference agents. ✅ done.
- **M4** — Evaluation pipeline (`tournament.py` activation, full round-robin). ⏳ next.
- **M5** — Evolution pipeline dry run (N=8, G=2). ⏳ pending.
- **M6** — Full evolution campaign (~20h overnight). ⏳ pending.
- **M7** — `select_top4.py` + flatten + populate submission slots. ⏳ pending.
- **M7.5** — Time-budget calibration on TA-simulated hardware. ⏳ pending.
- **M8** — Final `output.csv` for report. ⏳ pending.
- **M9** — LaTeX ICML report. ⏳ pending.
- **M10** — Submission packaging (zip, sha256, smoke). ⏳ pending.

## OMC / Process Vocabulary

- **ralplan** — consensus planning skill: Planner → Architect → Critic loop.
- **autopilot** — full-auto execution from spec → tested code.
- **CCG** — Claude/Codex/Gemini tri-model orchestration via `omc ask`.
- **ADR** — Architecture Decision Record. Section 0 of `STRATEGY.md`.
- **stop hook** — Claude Code background script that fires after each turn. Can block stop and request continuation (e.g., autopilot persistent mode).
- **Auto Dream** — Anthropic's background memory consolidation sub-agent. Triggers after 24h + 5 sessions. Cleans `~/.claude/projects/{id}/memory/`.


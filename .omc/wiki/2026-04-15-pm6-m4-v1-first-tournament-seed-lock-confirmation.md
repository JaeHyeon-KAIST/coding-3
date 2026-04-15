---
title: "2026-04-15 pm6 - M4-v1 first tournament + seed-lock confirmation"
tags: ["session-log", "m4", "tournament", "elo", "seed-lock", "95-percent-tie", "h1b-winner", "mcts-timeout"]
created: 2026-04-15T06:51:07.853Z
updated: 2026-04-15T06:51:07.853Z
sources: ["experiments/artifacts/tournament_results/m4_full_pm6_v1.csv", "/tmp/m4_smoke.csv", "/tmp/m4_full.log", "experiments/tournament.py", "minicontest/zoo_mcts_heuristic.py"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-15 pm6 - M4-v1 first tournament + seed-lock confirmation

# Session 2026-04-15 pm6 — M4-v1 first tournament + seed-lock confirmation

## Focus
First M4 tournament with the pm5 crash-safe `tournament.py`. Intent: produce an ELO table over all 21 agents. Outcome: mixed — pipeline works end-to-end, but seed-deterministic lock collapses 95.2% of matches to ties, so signal is weak. Also surfaced MCTS/deep-minimax timeout issue that we deferred.

## Smoke (30 matches, 6 agents)
Command: `tournament.py --agents baseline h1test h1b h1c mcts_heuristic minimax_ab_d2 --layouts defaultCapture --seeds 1 --games-per-pair 1 --workers 8 --timeout-per-game 120`

- 30 matches in 4m37s wall. **10 crashes — ALL on `zoo_mcts_heuristic` matchups** (all 10 of its permutations).
- Root cause: `zoo_mcts_heuristic` uses `MAX_ITERS=1000` with **no time polling** (per its own header comment: "no time polling — §3.3 Dev phase"). At 1000 MCTS iterations × ~1200 moves × 4 games per `run_match` invocation (capture.py's 4-loop), wall cost exceeds run_match's 120s timeout.
- Mini-ELO on the 20 clean matches: h1test 1528 > h1b 1510 > minimax_ab_d2 1499 > baseline 1487 > h1c 1475. Consistent with pm4 40-game rankings (h1test highest by win%, h1b/h1c also appear).

## Exclusion list for M4-v1
- `zoo_mcts_random`, `zoo_mcts_heuristic`, `zoo_mcts_q_guided` — MAX_ITERS=1000 no time polling
- `monster_mcts_hand` — likely same pattern
- `monster_minimax_d4` — depth-4 minimax likely slow

Deferred to M7.5 time calibration (per STRATEGY.md §6.5).

## M4-v1 (15 agents, 210 matches)
Command: `tournament.py --agents baseline zoo_reflex_{tuned,capsule,aggressive,defensive,h1test,h1b,h1c} zoo_minimax_{ab_d2,ab_d3_opp} zoo_expectimax zoo_approxq_{v1,v2_deeper} zoo_dummy monster_rule_expert --layouts defaultCapture --seeds 1 --games-per-pair 1 --workers 8 --timeout-per-game 180 --out experiments/artifacts/tournament_results/m4_full_pm6_v1.csv`

- **210 matches / 0 crashes / 7m10s wall** (CPU user 52 min, 7.3× parallel).
- **Tie rate: 200/210 = 95.2%.** Only 10 decisive matches.

## Decisive matches (10 total)

| Red | Blue | Winner | Score |
|---|---|---|---|
| baseline | zoo_reflex_h1b | Blue (h1b) | -1.0 |
| baseline | zoo_dummy | Red (baseline) | +18.0 |
| baseline | zoo_approxq_v1 | Red (baseline) | +18.0 |
| baseline | zoo_approxq_v2_deeper | Red (baseline) | +18.0 |
| zoo_reflex_h1test | zoo_reflex_h1c | Red (h1test) | +1.0 |
| zoo_reflex_h1c | zoo_reflex_h1test | Blue (h1test) | -1.0 |
| zoo_approxq_v1 | baseline | Blue (baseline) | -18.0 |
| zoo_approxq_v2_deeper | baseline | Blue (baseline) | -18.0 |
| zoo_dummy | baseline | Blue (baseline) | -18.0 |
| monster_rule_expert | zoo_reflex_h1test | Blue (h1test) | -1.0 |

Observations:
- **zoo_reflex_h1b is the ONLY variant that beat baseline** (1W/0L/1T vs baseline when h1b=Blue). Consistent with pm4 40-game finding (h1b best net +8).
- **zoo_approxq_{v1, v2_deeper} are unlearned** — feature-weight q-learning agents that have never been trained (expected; requires M6 evolution). Both 0W/2L vs baseline.
- **zoo_dummy (random) 0W/2L vs baseline** — sanity check.
- **zoo_reflex_h1test ↔ zoo_reflex_h1c color-swap result** (`Red wins`/`Blue wins` for same pair inverted) — pm4 had h1test 35% and h1c 20% vs baseline, here h1test wins both h1c matchups.
- **Everything else ties** including all minimax variants, expectimax, monster_rule_expert, and all reflex variants vs all others.

## ELO (15 agents, all 210 matches)

| Agent | ELO |
|---|---|
| baseline | 1557.3 |
| zoo_reflex_h1test | 1532.0 |
| zoo_reflex_h1b | 1500.5 |
| zoo_minimax_ab_d3_opp | 1497.7 |
| zoo_expectimax | 1497.5 |
| zoo_reflex_aggressive | 1497.2 |
| zoo_reflex_tuned | 1497.2 |
| zoo_reflex_capsule | 1497.1 |
| zoo_minimax_ab_d2 | 1497.1 |
| zoo_reflex_defensive | 1496.9 |
| monster_rule_expert | 1487.5 |
| zoo_approxq_v2_deeper | 1486.1 |
| zoo_dummy | 1485.8 |
| zoo_approxq_v1 | 1485.6 |
| zoo_reflex_h1c | 1484.6 |

baseline appears "top" because of the 3 easy wins vs unlearned agents. Middle cluster (1497) is a statistical artefact of mutual ties — not a real ranking signal.

## Root cause of the 95.2% tie rate — SEED LOCK (CONFIRMED)

- `run_match.py:71-72` passes `--fixRandomSeed` whenever the tournament hands it a seed value.
- `capture.py:~852` treats `--fixRandomSeed` as a hard `random.seed('cs188')` — a constant, not the tournament's seed value.
- Net effect: every `run_match` subprocess starts with the identical PRNG state. Game outcomes are a deterministic function of (red-team, blue-team, layout). Repeats collapse to the same result.
- Since every agent-pair plays the same match twice (color-swapped), most pairs emit 2 identical ties. The only pairs with non-tie outcomes are those where the underlying strategy-gap is decisive regardless of color.

This was flagged in the wiki audit `experiments-infrastructure-audit-pre-m4-m6` as C2. We now have empirical confirmation: **without M4c-1 seed workaround, running more games, more seeds, or more reps adds NO information**.

## Pipeline wins
- `tournament.py` pm5 crash-safety patch works: per-row CSV append, resume, fsync. 0 crashes in 210 matches (excl. MCTS timeouts in smoke, which were reported correctly as `subprocess_timeout` crash rows).
- compute_elo() from `select_top4.py` runs cleanly on the CSV output.
- 7m10s for 210 matches (8 workers) is well within acceptable overhead; M4-v2 with 3 layouts should run in ~20-25 min.

## Decisions

1. **M4-v1 is a smoke + signal-weak snapshot.** Retain CSV as `m4_full_pm6_v1.csv`. Do not act on these rankings for agent selection.
2. **M4c-1 (`-l RANDOM<seed>` workaround) is now BLOCKING for M4-v2.** Bump priority above M4b.
3. **Exclude MCTS family (3 zoo + 1 monster) + monster_minimax_d4 from all M4 variants** until M7.5 time calibration implements per-turn time polling.
4. **Confirm pm4 empirical result**: zoo_reflex_h1b remains the best current candidate variant — it was the only agent to beat baseline in this deterministic run.
5. **approxQ_{v1, v2_deeper} are confirmed unlearned.** They will only become meaningful after M6 evolution produces weight vectors. Don't include them in pre-M6 comparisons.

## Next-session priority

**M4c-1** (~15-30 min): patch `run_match.py` to translate the tournament's seed into `-l RANDOM<seed>` (replacing `--fixRandomSeed`). Verify via a small smoke that the same (red, blue) pair with 3 different seeds yields 3 different outcomes.

Then **M4-v2**: same 15-agent tournament on 3 RANDOM layouts with 3 seeds (270 jobs × 4 actual games ≈ 20-25 min wall) → first real ELO table.

After that: **M4b** (evolve.py), **M5** (dry run), **M6** (20h).


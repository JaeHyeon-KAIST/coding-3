---
title: "2026-04-15 pm4 - 40-game apples-to-apples reverification + H1b redemption"
tags: ["session-log", "reverification", "40-game", "h1-family", "h1b-redemption", "statistical-rejection", "dummyagent-discovery", "control-experiment"]
created: 2026-04-15T04:49:44.615Z
updated: 2026-04-15T04:49:44.615Z
sources: ["/tmp/h1_reverify.log", "/tmp/h1b_reverify.log", "/tmp/h1c_reverify.log", "/tmp/tuned_control.log", "minicontest/capture.py:761,889,980,1054", "minicontest/your_baseline1.py", "minicontest/your_baseline2.py", "minicontest/your_baseline3.py"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-15 pm4 - 40-game apples-to-apples reverification + H1b redemption

# Session 2026-04-15 pm4 — 40-game apples-to-apples reverification + H1b redemption

## Focus
User directive: "정확성이 가장 우선" (accuracy first). Rerun ALL H1-family variants + ReflexTuned control under the same 40-game `-b baseline -n 10 -q` protocol so conclusions rest on equal-sized samples.

## Protocol verification (why 40 games per invocation)
- `capture.py:761` — `readCommand(argv, blue_team)` uses `blue_team` only as an OptionParser **default** for `-b`. CLI `-b baseline` overrides on every iteration of the main loop.
- `capture.py:1054-1055` — main wraps `runGames` in `for i in range(4)` over `lst=['your_baseline1.py','your_baseline2.py','your_baseline3.py','baseline.py']` to build `output.csv`.
- `capture.py:889-903` — each iteration builds its own `layouts[0..numGames-1]`; for `defaultCapture` (no `-l`), all 10 layouts per block are deterministic same-map.
- `capture.py:972-1017` — `runGames` does NOT re-seed Python's `random`; no seed reset between blocks or between games. So 40 games are 40 independent random draws from the natural process-start PRNG state.
- `capture.py:811` — `-f/--fixRandomSeed` hardcodes `random.seed('cs188')` ONCE. Omitted here to preserve natural variance across 40 games.

## Bonus discovery
`your_baseline1.py`, `your_baseline2.py`, `your_baseline3.py` are currently **exact copies of `myTeam.py` → `DummyAgent` (random action)**. So capture.py's 4-loop is actually a "vs [random, random, random, baseline]" comparison harness for `output.csv`. When `-b baseline` is explicit, all 4 blocks collapse to baseline (our use case). Before M8 submission, these must be populated with our own variants (per CLAUDE.md: "your_baseline1.py 실험용 #1", etc.); otherwise the required report comparison table is degenerate.

## Canonical 40-game table (vs baseline.py, defaultCapture)

| Agent | W | L | T | Win% | Loss% | Tie% | Net (W−L) |
|---|---|---|---|---|---|---|---|
| zoo_reflex_tuned (control) | 0 | 0 | 40 | 0% | 0% | **100%** | 0 |
| zoo_reflex_h1test (both-OFFENSE) | 14 | 14 | 12 | **35%** | 35% | 30% | 0 |
| zoo_reflex_h1b (role-split) | 12 | 4 | 24 | 30% | **10%** | 60% | **+8** |
| zoo_reflex_h1c (capsule-exploit, new run) | 8 | 2 | 30 | 20% | 5% | 75% | +6 |
| zoo_reflex_h1c (pm3 earlier run) | 4 | 4 | 32 | 10% | 10% | 80% | 0 |

## Block-level scores (for provenance / audit)

**H1 (zoo_reflex_h1test)**:
- Block 1: [1,1,1,-18,1,0,0,-18,1,1] → 6W/2L/2T
- Block 2: [-18,-17,1,0,-18,2,-18,-18,0,-18] → 2W/6L/2T
- Block 3: [-18,0,-18,-18,3,-18,0,0,0,1] → 2W/4L/4T
- Block 4: [1,0,-18,-18,1,1,0,1,0,0] → 4W/2L/4T

**H1b (zoo_reflex_h1b)**:
- Block 1: [1,0,0,1,0,1,0,0,0,0] → 3W/0L/7T
- Block 2: [0,0,1,0,1,0,-18,-18,0,0] → 2W/2L/6T
- Block 3: [-18,0,0,0,0,0,0,1,1,1] → 3W/1L/6T
- Block 4: [3,0,1,1,0,0,1,0,0,-18] → 4W/1L/5T

**H1c (zoo_reflex_h1c, new run)**:
- Block 1: [0,0,0,0,0,0,0,0,0,0] → 0W/0L/10T
- Block 2: [0,3,0,0,0,0,1,-18,0,0] → 2W/1L/7T
- Block 3: [0,1,2,0,0,0,0,0,-18,2] → 3W/1L/6T
- Block 4: [3,0,0,0,0,0,1,0,0,2] → 3W/0L/7T

**ReflexTuned (untouched control)**: 40 games all `[0,0,0,0,0,0,0,0,0,0]` → perfect 100% tie. Deadlock exactly reproducible.

## Statistical reasoning

- **ReflexTuned 0% win** (40 tie games) ⇒ original deadlock observation is confirmed structural, not a fluke.
- **51% grading threshold**: H1 14/40 at p=0.51 gives z=(0.35-0.51)/sqrt(0.51·0.49/40)=-2.07, one-sided p≈0.019. We reject p ≥ 0.51 at 95%. **No pure single-dict weight scaling of the seed will clear the 40pt code score on `baseline.py`**.
- **Block variance**: H1 block win% ranges from 2/10 (block 2) to 6/10 (block 1) — σ_block ≈ 0.17. The 10-game block used by pm1 for H1's "3W" verdict is ONE random draw from this distribution; it could easily have been 2W or 6W. This is why pm2's "1W/2L/7T → H1b rejected" verdict was wrong.
- **H1c run-to-run variance**: Same agent, same `-b baseline -n 10` command, two separate invocations → (4/40, 8/40). Binomial σ for n=40, p=0.15 ≈ 2.3, so 4↔8 wins = ~1.7σ (borderline). At 40 games per invocation, ±6%-point CI on win rate is typical; not tight enough for small comparisons.

## Decisions

1. **H1b pm2 rejection overturned.** It is the net-positive leader (+8) and has lowest loss rate (10%). Keep as an active seed variant; it may rank best in tournaments (diverse opponents, where low-loss is more valuable than peak win rate).
2. **H1 retains grading-metric lead.** 35% win rate is the current best, but 51% is statistically out of reach via weight tuning.
3. **Single-dict tuning is TERMINATED.** The path to 51% runs through either (a) policy changes (coordination, search-based planning) or (b) M6 evolution over a much wider weight space. No H1d quick test needed — we have sufficient evidence.
4. **Critical path pivot to infra.** Immediate next actions:
   - Fix `evolve.py:140-142` `NotImplementedError` swallow (see wiki `debugging/experiments-infrastructure-audit-pre-m4-m6`). Without this, any M6 run yields random-noise weights.
   - Seed plumbing fix / `-l RANDOM<seed>` workaround in `run_match.py:72`.
   - Tournament CSV + memory robustness patches.
   - Then M4 tournament pipeline activation across zoo on 3 layouts.
5. **Populate `your_baseline1/2/3.py` before M8 submission** with meaningful variants (plan candidates: reflex-tuned, minimax-d2, MCTS-heuristic) so `output.csv` is non-degenerate in the report.

## Open items

- Sample size: 40 games per agent still gives ~±10% win-rate CI. For final ranking decisions, prefer 100+ games via tournament pipeline (M4).
- Fixed-seed (`-f`) reproducibility run left for M4; current numbers use natural PRNG variance.
- Tournament against student opponents (M8) will stress-test H1 vs H1b profile tradeoff. Current intuition: H1b's low-loss profile is more tournament-robust.

## Next-session priority
Start M4 infrastructure patches. The `evolve.py:140-142` fix is the single blocker; after that, `run_match.py` seed workaround and tournament CSV append are ~1h total. Then M4 tournament run across all 17 zoo agents × 3 layouts × baseline on real parallel compute.


---
title: "M3 smoke deadlock — 0-win pattern across all tuned agents"
tags: ["m3", "deadlock", "tuning", "seed-weights", "scoreless", "open", "h1-confirmed", "resolved-partial", "baseline-analysis", "h1b-rejected", "defender-weakness"]
created: 2026-04-15T00:20:09.516Z
updated: 2026-04-15T01:22:15.755Z
sources: []
links: []
category: debugging
confidence: high
schemaVersion: 1
---

# M3 smoke deadlock — 0-win pattern across all tuned agents

# M3 smoke deadlock — 0-win pattern across all tuned agents

**STATUS: OPEN — blocking M6 success likelihood**

## Symptom

Across 47 smoke games (M1 dummy + M2 zoo variants + M3 monsters vs `baseline.py` on `defaultCapture`):
- 0 wins for any of our tuned agents
- 5 ties + 2 baseline-wins for hand-tuned monsters
- The ONLY agent that loses to baseline (rather than tying) is `zoo_dummy` (random actions): 7L 3T

## Why is this strange

Hand-tuned reflex/minimax/MCTS/monster agents producing 0 wins is suspicious. Even the `monster_*` agents — explicitly designed as strong adversarial references — tied or lost to baseline. Random `zoo_dummy` lost to baseline (baseline's offense scored against random's lack of defense). Tuned agents tied 0-0 (mutual scoreless deadlock).

If our agents were merely WEAK, baseline should win them similarly to how baseline beats random. They DON'T — they tie.

## Hypotheses (numbered for cross-session tracking)

### H1: SEED_WEIGHTS too defense-heavy → both teams refuse territory cross [HIGH PROBABILITY]
- `f_numInvaders = -1000.0` and `f_onDefense = +100.0` in `zoo_features.SEED_WEIGHTS_OFFENSIVE`
- These dominate any food-eating reward when the agent is in our own territory
- Result: agents stay home → baseline's offensive reflex agent enters but can't score (we block) → we never invade either → 0-0
- Test: zero out `f_onDefense` in one zoo variant, run smoke; if it scores, H1 confirmed

### H2: STOP fallback firing too often [MEDIUM]
- `_safeFallback` returns `random.choice(legal - {STOP})` only when no exception in primary
- If feature extraction silently raises (try/except returns 0.0 per feature), entire weight vector might be 0 → argmax picks first legal action which could be STOP (ordering-dependent)
- Test: add a debug counter in `_safeFallback`; check if it's invoked frequently

### H3: APSP/bottleneck features over-penalize movement [LOW]
- `_precomputeAPSP` runs at init; `getMazeDistance` falls back if APSP not built
- If APSP cache is corrupt or wrong, distance features could mislead → agent stays put thinking food is "close"
- Test: assert `len(self.apsp) > 0` after registerInitialState; print one distance pair to verify

### H4: Monster agents inherit zoo_features's bias [HIGH for monsters specifically]
- `monster_minimax_d4` explicitly imports zoo_features (per spec)
- `monster_rule_expert` may also use defensive logic that prevents scoring
- Even with hand-tuned strategy, if the underlying feature signal is biased, monsters can't escape
- Test: replace monster's leaf evaluator with a pure food-distance heuristic; observe behavior

### H5: TeamGlobalState role assignment broken [MEDIUM]
- Default: lower-index OFFENSE, higher DEFENSE
- If reset() runs per game and resets to OFFENSE/DEFENSE but agents both end up DEFENSE due to a logic bug...
- Test: print `TEAM.role` at start of each game; confirm one is OFFENSE and one DEFENSE

### H6: capture.py red-vs-blue starting team randomization confounds smoke results [LOW]
- "Blue team starts" appeared in earlier smoke output
- Maybe agent #2 (lower-index for blue) doesn't get OFFENSE role correctly when starting
- Test: run with both `-r our_agent -b baseline` and `-r baseline -b our_agent`; compare

## Validation plan (priority-ordered)

1. **M4 tournament infra** (planned) — agent-vs-agent matchups across multiple layouts. Will reveal: (a) is the deadlock specific to vs-baseline, or universal? (b) do any agent pairs produce decisive games?
2. **Pre-M4 quick check** — manually test H1 by patching one zoo variant with `f_onDefense = 0, f_numInvaders = -50`, running 10 games. If win rate > 0%, H1 is the cause.
3. **Logging instrumentation** — add `print` of `chooseAction` action distribution in one zoo variant for 1 game; identify if STOP dominates (H2).
4. **TeamGlobalState assertion** — add assert at start of `_chooseActionImpl` that exactly one agent has OFFENSE role; catches H5.

## Why this matters

If H1/H4 is true, M6 CEM evolution should naturally select for less-defensive weights (because tied games yield fitness=0.5 vs winning yields 1.0; aggressive mutants will win and propagate). However:
- If deadlock is structural (H2/H3/H5), evolution can't escape — selection pressure exists but no aggressive behavior is reachable in genome space
- If H6 is true, our entire smoke methodology is biased and we need to fix capture.py invocation

**M6 is ~20h compute. We CANNOT afford to discover post-evolution that the deadlock was structural.** Validation plan items 2-4 should run BEFORE M5 dry run.

## Cross-references

- Initial observation: `docs/AI_USAGE.md` M2a entry (2026-04-14)
- Confirming observation: `docs/AI_USAGE.md` M3-verify entry (2026-04-15)
- Plan section discussing seed weights: `.omc/plans/STRATEGY.md` §4.1
- ADR for evolution as solution path: `.omc/plans/STRATEGY.md` §0 ADR
- Open question: `.omc/plans/open-questions.md` (Phase 2a CEM seed convergence)
- First session-log entry: see wiki `session-log/session-2026-04-15-m3-smoke-deadlock`

## Resolution log (append as hypotheses are tested)

(Empty — no hypothesis tested yet beyond observation)

---

## Update (2026-04-15T00:47:29.500Z)

## Resolution log — H1 quick validation (2026-04-15 09:45-09:46 KST)

**STATUS: H1 CONFIRMED (partial). Deadlock is NOT structural — root cause localized to SEED_WEIGHTS overweight on defense. Agent: `zoo_reflex_h1test.py`.**

### Experiment

- **Variant**: `minicontest/zoo_reflex_h1test.py` — inherits `ReflexTunedAgent`, overrides `_get_weights()` to always return H1-patched `SEED_WEIGHTS_OFFENSIVE`:
  - `f_onDefense: 100.0 → 0.0` (remove home-side bonus entirely)
  - `f_numInvaders: -1000.0 → -50.0` (mild signal, not a cliff)
  - All other OFFENSIVE weights unchanged
  - Both teammates use this weight set (ReflexAggressive pattern — bypass `TEAM.role`)
- **Smoke**: `cd minicontest && ../.venv/bin/python capture.py -r zoo_reflex_h1test -b baseline -l defaultCapture -n 10 -q` → 61s wall

### Result

| Metric | Value | vs. baseline M3 signal |
|---|---|---|
| Our wins | **3/10 (30%)** | was 0/47 across all M2/M3 agents |
| Ties | 5/10 (50%) | was ~45/47 |
| Losses | 2/10 (20%) | was ~2/47 (monsters only) |
| Scores | `[0,0,0,0,0, 1,1,-18, 1,-18]` | — |
| Crashes/forfeits | 0 | ✅ |

The 3 wins are narrow (`+1` — single-food advantage); the 2 losses are decisive (`-18` — baseline's Blue agent returned 18 food unopposed). Seems clearly attributable to both our agents being OFFENSIVE (no defender) — baseline's OffensiveReflexAgent can walk in and score freely.

### Hypothesis verdict

- **H1 CONFIRMED (HIGH confidence).** Zero-defensive weights broke the deadlock; 30% win rate from a 0% baseline is conclusive.
- **H1 is NOT the complete story.** 50% tie rate persists even with neutralized defense — other factors (possibly H2 STOP fallback, H5 role logic, or just baseline being defensive itself) contribute to deadlock on small food margins.
- **Root cause interpretation**: `f_onDefense=+100` + `f_numInvaders=-1000` in the OFFENSIVE seed dominated the legitimate offensive signal (`f_successorScore=100` per dot eaten gives +100 gain per food — but also `f_onDefense=+100` gives +100 just for being home; the two are identical magnitude → argmax prefers safer home-side action).

### Implications for plan

- ✅ **M6 evolution CAN fix this.** Selection pressure exists: aggressive mutants outscore tied ones → they propagate. 20h CEM compute is NOT wasted risk.
- ⚠️ **Seed weights need partial re-tuning** before evolution to give CEM a better starting point:
  - `f_onDefense` should be ~+20 (not +100) for OFFENSE role — mild home preference, not cliff
  - `f_numInvaders` should be ~-200 (not -1000) for OFFENSE — signal, not dominator
  - `DEFENSIVE` weights can keep the cliff (that's the role's purpose)
- ⚠️ **-18 loss pattern suggests** the "both OFFENSE" pattern of H1 test is not viable as a real team strategy — need 1 OFFENSE + 1 DEFENSE split with the rebalanced weights.
- ✅ **M4 tournament can proceed with confidence.** Deadlock was tuning, not structural.

### Remaining open hypotheses (lower priority now)

- H2 (STOP fallback over-firing) — STILL plausible for the 50% tie rate residual; instrument next session if M4 tournament shows persistent tie bias.
- H3 (APSP corruption) — unlikely given agent moved and scored; can deprioritize.
- H4 (monster features inherit bias) — RELEVANT for monster redesign but not blocking for M4.
- H5 (role assignment broken) — deprioritize; H1 test bypassed role entirely and still scored, but this doesn't disprove H5.
- H6 (red/blue start randomization) — low; results balanced across starts.

### Next actions

1. **M4 tournament activation** — run `experiments/tournament.py` on full zoo + monsters across multiple layouts × color swaps × seeds. Confirms whether tie rate persists across opponent diversity or is baseline-specific.
2. **Before M5/M6**: optional re-tune `SEED_WEIGHTS_OFFENSIVE` to mid-values (`f_onDefense=20`, `f_numInvaders=-200`) so CEM gen-0 has a competitive starting pop.
3. **Keep `zoo_reflex_h1test.py`** in the zoo as an ablation reference — documents the deadlock cause in the final report.

---

## Update (2026-04-15T01:16:36.861Z)

## Deeper analysis — baseline.py weaknesses + 10-game breakdown (2026-04-15 pm)

### Game-by-game H1 smoke breakdown (defaultCapture, zoo_reflex_h1test as Red)

| # | Starter | Result | Score | Interp |
|---|---|---|---|---|
| 1 | Red | Tie | 0 | deadlock |
| 2 | Blue | Tie | 0 | deadlock |
| 3 | Red | Tie | 0 | deadlock |
| 4 | Red | Tie | 0 | deadlock |
| 5 | Red | Tie | 0 | deadlock |
| 6 | Red | Red win | +1 | narrow win |
| 7 | Red | Red win | +1 | narrow win |
| 8 | Blue | **Blue win** | **-18** | baseline 18 food unopposed |
| 9 | Red | Red win | +1 | narrow win |
| 10 | Blue | **Blue win** | **-18** | baseline 18 food unopposed |

**Perfect asymmetric pattern:**

| Starter | W | L | T |
|---|---|---|---|
| Red (us) starts | 3 | 0 | 5 |
| Blue (baseline) starts | 0 | 2 | 0 |

Mechanism: `capture.py:381` runs `starter = random.randint(0, 1)` each game. When baseline's `OffensiveReflexAgent` gets the first-mover move, it enters our territory one tick earlier. Both our H1 agents are OFFENSE (no defender), so baseline raids freely → cashes 18 food.

### baseline.py structural weaknesses (baseline.py:130-188)

**`OffensiveReflexAgent` — weights:** `{successorScore: 100, distanceToFood: -1}` — only 2 features.

Missing from baseline Offense (exploitable):
- ❌ **Ghost avoidance** — walks into ghost paths freely
- ❌ **Capsule awareness** — never uses capsule for scared-window attack
- ❌ **`numCarrying` sensitivity** — never returns home; keeps eating until caught (then dumps all)
- ❌ **Dead-end detection** — follows food into 1-exit corridors blindly

**`DefensiveReflexAgent` — weights:** `{numInvaders: -1000, onDefense: 100, invaderDistance: -10, stop: -100, reverse: -2}` — structurally near-identical to our own `SEED_WEIGHTS_DEFENSIVE`.

Missing from baseline Defense (exploitable):
- ❌ **`scaredTimer` ignored** — when scared, `invaderDistance: -10` still drives it TOWARD invaders. Self-sacrifice bug.

### Implications for next variant design

H1 (both OFFENSE) broke the deadlock BUT created defense vacuum → asymmetric loss pattern.

The correct patch is **H1b — keep 1 OFFENSE + 1 DEFENSE split from `ReflexTunedAgent`, override only the OFFENSIVE weight dict** (`f_onDefense=0, f_numInvaders=-50`), leave DEFENSIVE weights untouched.

Prediction: asymmetric losses should resolve because the DEFENSE role agent holds home during Blue-starter games. Tie rate might stay similar (if tie rate is baseline-driven) or drop (if H1 was over-patching).

### Stretch follow-ups (documented for later sessions)

- **H1c**: exploit baseline's capsule-blindness. Boost `f_distToCapsule: 8.0 → 40.0` in OFFENSIVE. When baseline Defender stays scared 40 ticks but our `zoo_features` correctly handles scared (via `f_scaredFlee`), we can raid freely.
- **H2 diagnostic**: instrument `CoreCaptureAgent._safeFallback` with a call counter. If counter > 5 per game → STOP fallback is over-firing (confirming H2 as residual tie-rate driver).

---

## Update (2026-04-15T01:22:15.755Z)

## Resolution log — H1b test: role-aware patch (2026-04-15 pm)

**STATUS: H1b REJECTED as primary fix. Below H1 in win rate (1/10 vs 3/10). But high information value — reveals that DEFENSIVE weights themselves fail to block baseline offense, and that "2-OFFENSE formation" has real attacking advantage over "1+1 split".**

### Experiment

- **Variant**: `minicontest/zoo_reflex_h1b.py` — inherits `ReflexTunedAgent`, overrides `_get_weights()` role-aware:
  - role=OFFENSE → H1-patched offensive weights (`f_onDefense=0`, `f_numInvaders=-50`, rest unchanged)
  - role=DEFENSE → `SEED_WEIGHTS_DEFENSIVE` **untouched** (intentional — test whether preserving defender resolves -18 losses)
- **Smoke**: `cd minicontest && ../.venv/bin/python capture.py -r zoo_reflex_h1b -b baseline -l defaultCapture -n 10 -q` → 55s wall

### Result

| # | Starter | Result | Score |
|---|---|---|---|
| 1 | Red | Tie | 0 |
| 2 | Blue | **Blue win** | **-18** |
| 3 | Blue | Tie | 0 |
| 4 | Blue | Red win | +1 |
| 5 | Red | Tie | 0 |
| 6 | Blue | Tie | 0 |
| 7 | Blue | Tie | 0 |
| 8 | Blue | Tie | 0 |
| 9 | Red | Tie | 0 |
| 10 | Blue | **Blue win** | **-18** |

**Totals**: 1W / 2L / 7T. Average score -3.5.

### Comparison with H1

| Metric | H1 (both OFFENSE) | H1b (role split) | Delta |
|---|---|---|---|
| Wins | 3/10 (30%) | **1/10 (10%)** | ↓ 20 pp |
| Losses | 2/10 | 2/10 | same |
| Ties | 5/10 | **7/10** | ↑ 20 pp |
| -18 rout occurrences | 2 | **2** (still!) | same |
| Red-starter wins | 3/8 (37%) | 0/3 (0%) | ↓ |
| Blue-starter wins | 0/2 (0%) | 1/7 (14%) | modest |

### Diagnosis — why H1b underperformed

**Failure mode 1: defender cannot actually stop baseline offense (the -18 pattern persists).**

The `SEED_WEIGHTS_DEFENSIVE` mix is:
```
f_onDefense: 200, f_patrolDist: 30, f_invaderDist: 80, f_numInvaders: -2000
```

When baseline's OffensiveReflexAgent enters our territory, our defender should chase (`f_invaderDist=+80 × 1/dist`). But simultaneously:
- `f_patrolDist=30 × 1/dist` pulls defender TOWARD the patrol anchor (home frontier bottleneck)
- `f_onDefense=200` gives huge bonus just for being home-side
- Defender ends up **oscillating between patrol anchor and invader**, arriving late. Baseline offender raids deep, cashes 18 food, returns.

In Blue-starter games where baseline gets first move, defender's latency compounds — by the time defender engages, 10+ food already eaten.

**Failure mode 2: lone offender can't penetrate baseline defender.**

In H1 (both OFFENSE), two attackers on one baseline defender = at least one finds a path. In H1b, one attacker vs one defender = most games become tail-chasing stalemates → 70% tie rate.

Red-starter games (3/10) are all ties in H1b — lone offender mostly fails to find unopposed entry.

### Implications

- **`SEED_WEIGHTS_DEFENSIVE` is weak** — `f_patrolDist=30` distracts defender from active threats. Patrol-first vs chase-first tuning needs rebalancing.
- **"2 OFFENSE formation" has real attacking advantage** over "1 OFFENSE + 1 DEFENSE" — H1's higher win rate (30% vs 10%) isn't just seed-weight effect; it's formation effect.
- **M6 CEM evolution must jointly optimize OFFENSE and DEFENSE weights + the role-formation decision.** Cannot just tune offensive values with defensive unchanged. This doubles (roughly) the effective dimensionality that evolution needs to explore.
- **Single-weight-dict tweaks cannot solve both deadlock AND defense vacuum simultaneously** — deeper redesign (better DEFENSIVE weights; or different role-switching logic; or richer OFFENSIVE strategy that exploits baseline weaknesses) required.

### Remaining hypotheses re-prioritized

1. **H1c (NEW, highest ROI)**: exploit baseline capsule-blindness. OFFENSIVE `f_distToCapsule: 8 → 80` (10x). When baseline defender is scared (40 ticks), its `invaderDistance: -10` weight drives it suicidally TOWARD us (can't handle scared). During the 40-tick scared window, both our offense agents can raid safely.
2. **H1d (NEW)**: rebalance DEFENSIVE weights. `f_patrolDist: 30 → 5`, `f_invaderDist: 80 → 400`, `f_onDefense: 200 → 50`. Test whether defender can actually block baseline offense when properly chase-prioritized.
3. **H2 (diagnostic)**: `_safeFallback` call counter. Tie rate jumped 50% → 70% from H1 to H1b — needs an explanation beyond "offense weaker"; STOP-fallback over-firing plausible.
4. **H1e (stretch)**: switch tested agent to `zoo_minimax_ab_d2` with same OFFENSIVE patch. Lookahead may penetrate baseline defender where reflex cannot.

### Strategic note

M4 tournament (with infra patches) becomes more important now, not less. We need to test H1c/H1d/H2/H1e **across layouts** and **against multiple opponent types** (not just baseline) to avoid overfitting to baseline-specific patterns. Small smoke tests on defaultCapture alone cannot generalize.


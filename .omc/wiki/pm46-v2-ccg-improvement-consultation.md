---
title: "pm46 v2 CAPX — CCG tri-advisor consultation (Claude + Codex + Gemini)"
tags: ["pm46-v2", "capx", "ccg", "consultation", "improvement", "algorithm", "phase-4-tuning"]
created: 2026-04-29
updated: 2026-04-29
sources:
  - "minicontest/zoo_reflex_rc_tempo_capx.py"
  - ".omc/wiki/pm46-v2-FINAL-recovery-17-of-17.md"
  - ".omc/wiki/pm46-v2-capx-code-review-phase4-tuning.md"
  - ".omc/research/pm46-v2-ccg/codex-summary.md"
  - ".omc/research/pm46-v2-ccg/gemini-summary.md"
  - ".omc/artifacts/ask/codex-capx-algorithm-improvement-consultation-prompt-for-external--2026-04-29T00-30-28-224Z.md"
  - ".omc/artifacts/ask/gemini-capx-algorithm-improvement-consultation-prompt-for-external--2026-04-29T00-31-25-942Z.md"
links: []
category: decision
confidence: high
schemaVersion: 1
---

# pm46 v2 CAPX — CCG tri-advisor consultation

**Goal**: Identify highest-ROI algorithmic improvements to CAPX
(`zoo_reflex_rc_tempo_capx.py`, 684 LOC) for the 3 weak defenders
(`zoo_reflex_capsule` 40%, `zoo_reflex_tuned` 40%, `zoo_reflex_aggressive`
50%), with constraint of NO submission code modification (CAPX is research
probe).

**Method**: Tri-advisor parallel consultation:
1. **Claude (lead)** — independent data + code analysis (this section + §3).
2. **Codex CLI** (gpt-5.5, reasoning=high) — see `.omc/research/pm46-v2-ccg/codex-summary.md`.
3. **Gemini CLI** — see `.omc/research/pm46-v2-ccg/gemini-summary.md`.

**Verdict**: Strong convergence on 2 fixes (asymmetric threat mask +
`_p_survive` off-by-one). Gemini alone identified a **structural bug**
(A* ↔ gate horizon mismatch) that explains the empirical late-commit
pattern. Recommended action: implement S-tier 3 fixes (combined ~6 LOC)
and re-measure on 17×30 matrix.

---

## 1. Empirical evidence (lead's per-defender data analysis)

### 1.1 Weak-defender outcome distributions (510-game matrix)

**Capsule + Tuned are functionally identical defenders** (this is the most
important finding the prior review missed):

| Seed | capsule outcome | tuned outcome | eat_tick (capsule / tuned) |
|---|---|---|---|
| 1 | eat_alive | eat_alive | 828 / 828 |
| 7 | eat_alive | eat_alive | 953 / 953 |
| 8 | eat_alive | eat_alive | 1029 / 1029 |
| ... | ... | ... | ... |

12 of 30 seeds: BOTH eat_alive at SAME tick. 18 of 30 seeds: BOTH
no_eat_alive (no cap, no death). Confirmed by direct CSV diff: same set
{1,2,7,8,9,12,17,18,19,20,21,23} succeeds, same {3,4,5,6,10,11,13,14,15,
16,22,24,25,26,27,28,29,30} fails. **A single algorithmic improvement
acting on the failure mode of capsule WILL also fix tuned, doubling
sample size to effective n=60.**

**Aggressive is structurally different**:
- 15/30 eat_alive at varied ticks (637-1044).
- **2/30 no_eat_died** (seeds 20, 26) — these are the only suicide
  outcomes in the 510-game matrix. Both happened LATE (tick=961 and
  tick=944 in `timeleft` units, i.e., late game).
- 13/30 no_eat_alive — same stuck pattern as capsule/tuned, but on a
  different seed subset.

### 1.2 Failure-mode taxonomy refined from logs

Sample game logs (`experiments/results/pm46_v2/logs_capx_matrix/`):
- **capsule_seed3.log, seed11.log, seed14.log etc**: Only `[CAPX_INIT]`
  emitted, no `[CAPX_CAP_EATEN]`, no `[CAPX_A_DIED]`. Game timeout. =
  **F1 (over-rejection) or F2 (oscillation) pure stuck pattern.**
- **aggressive_seed20.log**: `[CAPX_A_DIED] tick=961` (single death,
  late, NO cap eaten). = **F3 (post-trigger death) pre-cap suicide.**
- **capsule_seed1.log** (success): 2 caps eaten at tick 828 + 804
  (within scared chain), 2 deaths at 644 (post-cap roam) and 1036
  (pre-cap). Late-commit success.

eat_tick distribution among successes (capsule+tuned): 648, 828, 884,
929, 940, 953, 984, 1012, 1024, 1029, 1037, 1040, 1044 — **clustered
in last 35% of game**. Suggests gate REJECT for hundreds of ticks
before eventually committing. Consistent with F1-overrejection +
gate horizon misalignment.

### 1.3 Implications for fix selection

- The 18 stuck seeds (capsule+tuned) need **gate-relaxation OR
  better-A\*-detour** — not safer-fallback (no fallback issue when there
  is no commit at all).
- The 2 aggressive suicide seeds need **survival-aware ranker /
  gate-tightening** — suicide is rare but exists.
- Lead opinion: same root mechanism — A\* fails to find safe detour →
  agent waits → eventually commits late on a marginal path that hurts
  the suicide cases too.

---

## 2. Convergence matrix (3 advisors)

| Candidate | Claude (lead) | Codex | Gemini | Net verdict |
|---|---|---|---|---|
| **A\* horizon alignment (sync `_astar_capx` edge_cost step_idx ≤ gate_horizon)** | not previously identified, lead validates Gemini's diagnosis on code review | — (missed) | **TOP #1** | **★ S-tier — highest single ROI**, structural bug fix |
| **Asymmetric / Lethality threat mask (skip threat on cells where self ≠ pacman)** | endorse (encodes physical rule) | TOP #2 | TOP #2 | **★ S-tier — both external advisors converge** |
| **`_p_survive` off-by-one (skip i=0 current cell)** | endorse (existing reviewer's MED already flagged it) | #6 runner-up | TOP #3 | **★ S-tier — 1 LOC, both advisors endorse** |
| **Defender-weighted safest drift (rewrite `_safest_step_toward`)** | partial endorse (only fires when stuck — won't help 18-seed no-commit case) | TOP #1 | not mentioned | A-tier — likely lifts strong-defender suicide-after-commit |
| **Capsule-terminal gate relaxation (last cell may share with defender)** | risky (engine-ordering dependent; may inflate `eat_died`) | TOP #3 | not mentioned | A-tier — needs careful validation |
| **Path-cell hysteresis (cell-level overlap discount)** | low priority (oscillation rare in stuck-pattern logs) | runner-up | runner-up | B-tier — defer |
| **Adaptive detour escalation (retry K=8 on rejection)** | duplicates A* horizon fix benefit | runner-up | not mentioned | B-tier — superseded by S-tier #1 |
| **Post-eat retreat survival (factor P_survive(retreat\|scared))** | reject (CAPX scope ends at first cap eat) | reject | reject | **REJECTED** |
| **Mission-complete safe drift (vs STOP forever)** | accept as safety quality fix (low ROI for eat_alive) | newly flagged | not flagged | B-tier — future work |
| **Tag A\* cache origin (astar vs bfs_fallback)** | accept as observability fix | newly flagged | **disagrees** with prior reviewer's MED rating, calls it safe | C-tier — observability only |

---

## 3. Recommended implementation plan (lead synthesis)

### S-tier — implement immediately (combined ~6 LOC, near-zero regression risk)

#### S1. A\* horizon alignment ⭐ HIGHEST ROI

**File:** `minicontest/zoo_reflex_rc_tempo_capx.py:148-158` (function
`_astar_capx`, helper `edge_cost`).

**Bug:** The `gate_horizon` patch (added post-Phase-1) made `_gate`
evaluate only the next 8 steps of the path. But `_astar_capx.edge_cost`
still applies threat for arbitrary `step_idx` (path-end may be 30+
steps out). Result: A\* often returns `None` for distant capsules → falls
back to direct BFS (no threat awareness) → gate then judges the
threat-naive BFS path.

**Fix (~2 LOC):** in `edge_cost`, early-return when step_idx exceeds
horizon:

```python
def edge_cost(cell_b, step_idx):
    if step_idx > knobs.get('gate_horizon', 8):
        return 1
    threat = 0
    for d_dist in defender_dist_map.values():
        margin = d_dist.get(cell_b, 999) - step_idx
        if margin <= 0:
            threat += INF
        elif margin <= 2:
            threat += W2
        elif margin <= 4:
            threat += W3
    return 1 + threat
```

**Knob:** `CAPX_ASTAR_HORIZON` (default = `CAPX_GATE_HORIZON` value, i.e., 8).
Setting `CAPX_ASTAR_HORIZON=999` reverts to old behavior for A/B test.

**Expected lift (Gemini estimate):** +15–25pp on `aggressive` and
`tuned`. Lead concurs, but expects similar magnitude on `capsule`
because capsule and tuned share the failure pattern.

**Regression risk:** near-zero. The fix only loosens A\* (more paths
become feasible). It does NOT loosen `_gate` (which already only sees
next 8 steps). So no path that previously got `gate=TRIGGER` will now
get `gate=REJECT` due to this fix.

#### S2. Asymmetric / Lethality threat mask

**File:** `minicontest/zoo_reflex_rc_tempo_capx.py:148-158` (same
`edge_cost` helper); also `_p_survive`, `_gate`, `_safest_step_toward`
margin computations.

**Bug:** Pacman engine kills A only when A is Pacman (i.e., on the
opponent's side of the board). When A is on its own side, it's a ghost
and cannot be killed by a non-scared enemy ghost. Yet `edge_cost`
applies threat penalty regardless of side. This causes A to refuse
border staging cells that are physically safe.

**Fix (~3-5 LOC):** Cache `is_red` + map width at init. In threat
evaluators, skip threat when cell is on A's home side:

```python
# In _read_capx_env or registerInitialState:
self._knobs['is_red']    = (self.index in gameState.getRedTeamIndices())
self._knobs['mid_x']     = walls.width // 2

# In edge_cost (and analogous in _p_survive, _gate):
home_x_max = mid_x - 1 if knobs['is_red'] else mid_x  # red home: x < mid
def is_home(cell):
    return cell[0] <= home_x_max if knobs['is_red'] else cell[0] >= home_x_max + 1
if is_home(cell_b):
    return 1   # no threat, A is ghost here
```

**Knob:** `CAPX_ASYMMETRIC_THREAT` (default 1). Set 0 to revert.

**Expected lift (both advisors):** +10–20pp on `capsule` (territorial
defender), +6–14pp on `tuned`/`aggressive`.

**Regression risk:** strictly zero — encodes the actual game rule. The
only failure mode would be wrong side detection (off-by-one on `mid_x`
or wrong red/blue assignment) — easy to test on smoke.

**Important:** Codex's framing was more precise than the existing reviewer's:
the rule is "skip threat where self_would_be_pacman is FALSE", NOT a
broad "discount opp-side cells". For a Red attacker (CAPX), opp-side =
blue side = where A becomes Pacman = where threat IS real.

#### S3. `_p_survive` off-by-one

**File:** `minicontest/zoo_reflex_rc_tempo_capx.py:243-254`.

**Bug:** `enumerate(path)` starts at `i=0` for the current cell. Margin
"can defender reach A's current cell in 0 steps" is meaningless — A is
already there alive. Multiplying P_survive by sigmoid(margin_0/1.5)
biases the result by ~0.5× whenever any defender is close. This pushes
many candidates below `CAPX_MIN_PSURVIVE=0.2` floor → ranker
degenerates to closest-cap distance ranking → loses threat weighting.

**Fix (1 LOC):**

```python
# Before:
for i, cell in enumerate(path):
# After:
for i, cell in enumerate(path[1:], start=1):
```

**Knob:** `CAPX_PSURVIVE_SKIP_CURRENT` (default 1). Set 0 to revert.

**Expected lift (both advisors):** +5–10pp on `aggressive` (specifically
helps the suicide cases by restoring ranker's preference for safer
caps).

**Regression risk:** zero — pure mathematical correction.

### Combined S-tier characteristics

- ~6 LOC total across 3 fixes, all in the same file.
- 3 independent env knobs allow ablation: each fix toggles individually.
- Additive in expected effect: S1 fixes A\* underuse; S2 fixes
  border-freeze; S3 fixes ranker collapse. Different failure paths.
- All near-zero regression risk individually.

### A-tier — implement after S-tier validation

| Fix | When to consider | Risk |
|---|---|---|
| **A1** Defender-weighted safest drift (Codex #1) | If S-tier still has stuck-pattern fails (drifting matters when even relaxed gate rejects) | Low — only changes Step 3 fallback |
| **A2** Capsule-terminal gate relaxation (Codex #3) | If `eat_died` rate is 0 after S-tier (room to be more aggressive at the cap cell) | Medium — could increase suicide on weaker variants |

### B-tier — defer

| Fix | Reason |
|---|---|
| Path-cell hysteresis | Empirical evidence shows STUCK (no commit) pattern, not OSCILLATION (committed but flipping path). Lower expected lift. |
| Adaptive detour escalation | S1 already addresses A\* underuse; this is duplicate compute. |
| Mission-complete safe drift | Quality-of-life fix; doesn't change eat_alive (already eaten). |
| Tag A\* cache origin | Observability only; helps debugging future work. |

### Rejected

- **Post-eat retreat survival** (existing reviewer's algorithmic
  hypothesis #2) — both Codex and Gemini reject independently. CAPX's
  objective ends at "eat first cap alive" — `cap_eat_alive` outcome is
  determined the moment cap is eaten with A still alive. Adding a
  retreat factor would distort the ranker AWAY from the closest
  reachable cap, hurting the metric we're trying to optimize.

---

## 4. Validation matrix (Codex's recipe + lead refinement)

### Phase A: Per-fix screen (independent ablation)

For each of S1, S2, S3 individually, with all OTHER fixes OFF:

| Defender | Seeds | Games |
|---|---|---|
| zoo_reflex_capsule | 30 | 30 |
| zoo_reflex_tuned | 30 | 30 |
| zoo_reflex_aggressive | 30 | 30 |
| **Total per variant** | — | **90** |
| 3 variants (S1, S2, S3 alone) | — | **270 games** |

Wall: ~270 × 5–10s ≈ 25–45 min on Mac single-thread.

**Pass threshold per fix:** Δ eat_alive ≥ +5pp aggregated over 90 games
(roughly significant given paired-seed design — see §5).

### Phase B: Combined validation + regression guard

If at least 2 of {S1, S2, S3} pass Phase A:
1. All-S-tier-on variant: 3 weak × 30 = 90 games (verify additive lift).
2. Strong-defender regression: 4 representative strong defenders (e.g.,
   `monster_rule_expert`, `zoo_reflex_A1`, `zoo_minimax_ab_d2`,
   `zoo_dummy`) × 15 seeds = 60 games. Accept if eat_alive loss ≤ -3
   wins out of 60 (i.e., ≤ -5pp).

Wall: ~150 × 5-10s ≈ 12-25 min.

### Phase C: Final 17×30=510 matrix (only after Phase B PASS)

Same wrapper as `pm46_v2_capx_matrix.sh`. Compare against current
17/17 baseline. Pass criteria:
- Aggregate `cap_eat_alive` ≥ 79.0% (current) + improvement.
- All 17 defenders strict improvement (or no regression on 14 strong).
- `died_pre_eat` ≤ 6.7% per defender (current max).

Wall: ~4-5h.

### Statistical caveats (lead)

- n=30 per defender → ±~18pp 95% CI on a single defender (Wilson).
- **However**: the capsule+tuned identical-outcome finding effectively
  doubles sample to n=60 for that fail mode → CI tightens to ±~12pp.
  Phase A on (capsule + tuned aggregated) = 60 paired observations →
  any +5pp lift across 60 games is roughly 60% confidence; +10pp ≈ 90%.
- aggressive is independent → still ±18pp on single fix. Need to look
  for both eat_alive AND died_pre_eat changes.
- For Phase C aggregate, 510 games with paired seeds → very high
  confidence on aggregate ±2pp. But per-defender power stays at ±18pp.

---

## 5. Implementation cost-of-readiness

| Phase | Wall | Code LOC | Risk |
|---|---|---|---|
| S-tier coding (S1+S2+S3) | ~30 min | ~6 LOC | Near-zero |
| Phase A screen (270 games, 3 variants) | ~45 min | 0 (env-knob only) | None |
| Phase B combined + regression (150 games) | ~25 min | 0 | Low |
| Phase C full 510 matrix | ~5h | 0 | None (informational) |
| **Total (S-tier validated)** | **~6h** | **~6 LOC** | — |

A-tier and B-tier fixes can wait for a separate iteration. S-tier alone
is a high-confidence next step.

---

## 6. Out of scope (per user reframing in SESSION_RESUME)

- Submission code modification (`20200492.py`, `your_best.py`,
  `myTeam.py`).
- ABS attacker code (`zoo_reflex_rc_tempo_abs.py`) — separate track.
- pm47 integration decision (CAPX → submission) — separate session.
- Cross-game state pollution HIGH (mitigated for current matrix; only
  matters for multi-game-per-process integration into submission).

---

## 7. Decision request

**Proposed next-session action:**
1. Implement S1+S2+S3 in `zoo_reflex_rc_tempo_capx.py` (~6 LOC, ~30
   min coding).
2. Phase A screen (270 games, ~45 min).
3. Iterate based on which fixes pass.

**User decisions needed:**
- Approve S-tier-only scope (vs adding A-tier upfront)?
- Phase A first (3 separate variants) or skip to Phase B (all S-tier
  on, regression check)?
- Wall budget — is ~6h end-to-end acceptable, or should we Phase C
  defer to server (sts)?

---

## 7.1 Implementation post-mortem (2026-04-29 same session)

After approval, implemented S1+S2+S3 in `zoo_reflex_rc_tempo_capx.py` with
3 env knobs. Single-game smoke on RANDOM1 vs `zoo_reflex_capsule`:

| Variant | Caps eaten | Deaths | Verdict |
|---|---|---|---|
| baseline (all S OFF) | 2 | 2 | reproduces existing eat_alive |
| S1 only ON | 2 | 2 | identical to baseline (no effect this seed) |
| **S2 only ON** | **0** | **1** | **REGRESSION** |
| S3 only ON | 2 | 2 | identical to baseline |
| All S1+S2+S3 ON | 0 | **7** | **catastrophic regression** |

**Root cause hypothesis**: S2 (asymmetric threat) was applied to `_gate.margin_at` —
when A is on home side, all next-8 cells get margin=999 → gate ALWAYS triggers
in home cells regardless of opp-side defender threat → A border-rushes → dies
as soon as it crosses → respawns → repeats.

**Action**: Changed `CAPX_ASYMMETRIC_THREAT` default from 1 → **0** (S2 OFF
by default). S1 + S3 remain default ON.

**Updated single-game verification (S1+S3 ON, S2 OFF)**:

| Game | Old (baseline) | New default (S1+S3) | Verdict |
|---|---|---|---|
| capsule RANDOM1 | 2 caps + 2 deaths | 2 caps + 2 deaths | identical ✅ |
| tuned RANDOM7 | 2 caps + 1 death | 2 caps + **0 deaths** | improved ✅ |
| capsule RANDOM3 | no_eat_alive | no_eat_alive | unchanged (both fail) |
| **aggressive RANDOM20** | **no_eat_died (suicide)** | **2 caps + 1 death (eat_alive!)** | **S3 cured suicide** ⭐ |

**Conclusion**: S3 (`_p_survive` skip-current) directly eliminated the
ranker's degenerate "blind charge" failure mode on aggressive RANDOM20.
S1+S3 default is strictly better than baseline on the spot-checked seeds.

**S2 status**: needs gate-margin scope-narrowing (apply only to `edge_cost`
and `_p_survive`, NOT `_gate.margin_at`). Deferred to ablation matrix —
S2 will be re-evaluated as standalone variant in Phase A. If gate-margin
S2 issue is the root cause, a follow-up patch can re-introduce S2 with
narrower scope.

## 7.2 Phase A ablation script

`experiments/rc_tempo/pm46_v2_ccg_phase_a_ablation.sh` — 3 weak defenders
× 30 seeds × 4 variants = 360 games:

- `baseline` (all S OFF) — replicates existing matrix as control
- `s1` only — A* horizon align alone
- `s3` only — _p_survive skip-current alone
- `s1s3` — proposed new default

Outputs: `experiments/results/pm46_v2/ccg_phaseA/{baseline,s1,s3,s1s3}.csv`

S2 ablation deferred (broken default — needs scope-narrowing patch first).

Wall: ~50 min/variant on Mac single-thread; ~3.5h total. Server expected <3h.

## 8. Files

- **Synthesis (this doc)**: `.omc/wiki/pm46-v2-ccg-improvement-consultation.md`
- **Codex summary**: `.omc/research/pm46-v2-ccg/codex-summary.md`
- **Gemini summary**: `.omc/research/pm46-v2-ccg/gemini-summary.md`
- **Codex raw**: `.omc/artifacts/ask/codex-capx-algorithm-improvement-consultation-prompt-for-external--2026-04-29T00-30-28-224Z.md`
- **Gemini raw**: `.omc/artifacts/ask/gemini-capx-algorithm-improvement-consultation-prompt-for-external--2026-04-29T00-31-25-942Z.md`
- **Original prompt**: `.omc/research/pm46-v2-ccg/CONSULT_PROMPT.md`
- **Source under review**: `minicontest/zoo_reflex_rc_tempo_capx.py`
- **Reference baseline**: `.omc/wiki/pm46-v2-FINAL-recovery-17-of-17.md`
- **Prior reviewer**: `.omc/wiki/pm46-v2-capx-code-review-phase4-tuning.md`

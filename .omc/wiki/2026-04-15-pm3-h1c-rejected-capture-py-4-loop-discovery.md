---
title: "2026-04-15 pm3 - H1c rejected + capture.py 4-loop discovery"
tags: ["session-log", "h1c", "capsule-exploit", "capture.py", "40-game-loop", "single-dict-saturation", "deadlock"]
created: 2026-04-15T02:22:43.924Z
updated: 2026-04-15T02:22:43.924Z
sources: ["minicontest/zoo_reflex_h1c.py", "/tmp/h1c_smoke.log", "minicontest/capture.py:1033-1075"]
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-15 pm3 - H1c rejected + capture.py 4-loop discovery

# Session 2026-04-15 pm3 — H1c rejected + capture.py 4-loop discovery

## Focus
Author H1c (capsule-exploit variant) per SESSION_RESUME.md directive, smoke-test vs baseline, decide next step.

## Activities

1. **Wrote `minicontest/zoo_reflex_h1c.py`**:
   - Inherits `ReflexTunedAgent`, returns H1c-patched weight dict from `_get_weights`
   - Both teammates use the same dict regardless of role (H1 formation)
   - Weight deltas vs `SEED_WEIGHTS_OFFENSIVE`:
     - `f_onDefense`: 100.0 → 0.0 (H1 inheritance)
     - `f_numInvaders`: -1000 → -50 (H1 inheritance)
     - `f_distToCapsule`: 8.0 → **80.0** (new, 10x)

2. **Import smoke** via `.venv/bin/python -c "import zoo_reflex_h1c; ..."`: all overrides correctly applied, `createTeam` constructs both agents.

3. **10-game smoke** via `.venv/bin/python capture.py -r zoo_reflex_h1c -b baseline -n 10 -q`:
   - **Actual behavior**: capture.py ran **40 games** (4 blocks × 10), all with Blue = `baseline.py` (confirmed by `Grep "Loading Team:"`).
   - Root cause: `capture.py:1054` wraps `runGames` in `for i in range(len(lst))` loop where `lst = ['your_baseline1.py','your_baseline2.py','your_baseline3.py','baseline.py']`. When `-b baseline` is CLI-passed, the parser override applies every iteration, so all 4 blocks = baseline.
   - **Results per block** (10 games each): 2W/0L/8T, 2W/1L/7T, 0W/1L/9T, 0W/2L/8T
   - **Aggregate (40 games)**: 4W / 4L / 32T → **10% win rate vs baseline**
   - Three -18 blowout losses (baseline raided unopposed when our H1c teammates got hung up near enemy capsule)

## Observations

- **Tie rate exploded from 50% (H1) to 80% (H1c)**. Signature of a NEW deadlock: `f_distToCapsule=80` dominates `f_distToFood=10` at all distances < 8. Both agents get pulled toward the same single enemy capsule, clustering on the approach and never dispersing to harvest food. Capsule-exploit hypothesis therefore fails on its own terms: even if baseline's defender does ignore `scaredTimer`, we don't eat the capsule often enough to trigger the exploit because both agents block each other.
- **Capture.py 4-loop is an assignment-evaluation protocol**, not a bug. `capture.py:1033-1075` exists to build `output.csv` comparing your_best against all your_baseline variants for grading. Running `capture.py` directly with `-b baseline` gives **40 games** per invocation, not 10. Prior H1 commit message "3W/2L/5T in 10 games" and H1b "1W/2L/7T in 10 games" most likely represent one of the 4 blocks — actual 40-game picture is unknown.
- **Single-dict weight tuning saturated** across 3 variants:
  - H1 both-OFFENSE: 30% (10-game sample, caveat above)
  - H1b role-split: 10% (10-game sample)
  - H1c capsule-exploit: 10% (40-game sample, confident)
  - No single scalar re-weighting of `SEED_WEIGHTS_OFFENSIVE` has reached 51%. Weight-space search is not going to clear 51% — we need either (a) multi-weight co-tuning (M6 evolution) or (b) policy-level changes (coordination protocol, role swapping, etc.)

## Decisions

- H1c REJECTED. Keep file as permanent ablation artefact (now 3 H1-family references: h1test, h1b, h1c).
- STATUS.md updated: H1c-verify row added, 40-game sample noted, 🔴 "single-dict tuning saturated" blocker added.
- **Did NOT auto-proceed to H1d**. Next step is a user decision: (a) H1d DEFENSIVE rebalance quick test, or (b) pivot directly to M4 infra patches + unblock M6 evolution (`evolve.py:140-142` NotImplementedError fix is now blocking).

## Open items

- Prior H1 / H1b 10-game numbers should be re-verified against 40-game aggregation for apples-to-apples comparison. Worth ~5 min of compute.
- `zoo_reflex_h1c.py` is not a submission file → **no** `docs/AI_USAGE.md` append per CLAUDE.md scoping rules.

## Next-session priority

User decision gate: H1d quick test vs M4 infra pivot. If M4 pivot: first task is the `evolve.py:140-142` NotImplementedError swallow fix (wiki `debugging/experiments-infrastructure-audit-pre-m4-m6`).


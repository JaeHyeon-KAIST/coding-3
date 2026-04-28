---
title: "pm46 v2 — Phase 2 smoke 9/9 PASS + gate-horizon algorithmic patch"
tags: ["pm46", "pm46-v2", "capx", "gate-horizon", "phase-2", "smoke"]
created: 2026-04-29
updated: 2026-04-29
sources: ["minicontest/zoo_reflex_rc_tempo_capx.py", ".omc/plans/omc-pm46-v2-capsule-only-attacker.md"]
links: []
category: debugging
confidence: high
schemaVersion: 1
---

# pm46 v2 — Phase 2 smoke + gate-horizon algorithmic patch

**Status**: Phase 1 AC + Phase 2 smoke PASS. Algorithmic patch applied to gate (`CAPX_GATE_HORIZON`).

## Phase 1 timing AC (executor verified)

- p95 chooseAction wall = **67.6ms** (limit 150ms — 2.2x headroom).
- max wall = 127.1ms.
- 0 ticks > 150ms across 232 measured ticks.
- → PASS.

## Issue discovered: full-path gate over-restriction

Plan §5.3 specifies gate uses `min(margins[full_path]) >= threshold` for trigger.
On RANDOM1 baseline:
- A spawn = (1, 2). Caps = [(25, 6), (23, 10)]. Defender at (32, 15) home base.
- Direct BFS dist (1,2)→(25,6) ≈ 30 cells.
- Defender BFS dist to (25, 6) ≈ 17 cells.
- For path step idx 30 at cap, margin = 17 - 30 = **-13**.
- Default `CAPX_MIN_MARGIN=0` → reject. `approach_mode` only allows `≥ -1`. Reject.
- Even `CAPX_MIN_MARGIN=-15` → 1/3 baseline pass (only seed 8 lucky enough).

**Result with full-path gate (CAPX_MIN_MARGIN=-15)**:
| Defender | eat_alive |
|---|---|
| baseline | 1/3 |
| monster_rule_expert | 1/3 |
| zoo_dummy | 1/3 |

**Diagnosis**: full-path margin assumes defender races optimally to far cells of A's plan. Not realistic — real defenders react locally. Far-future cells get re-evaluated when A gets closer (cache cleared per tick).

## Patch: near-future horizon

Added env knob `CAPX_GATE_HORIZON` (default 8). Gate evaluates `margins[1:horizon+1]` instead of `margins[full]`. Backward-compat flag `CAPX_GATE_USE_FULL=1` reverts to spec literal.

**Code change** (`minicontest/zoo_reflex_rc_tempo_capx.py:_gate`):
```python
horizon = max(1, knobs.get('gate_horizon', 8))
if knobs.get('gate_use_full', 0):
    gate_window = margins
else:
    gate_window = margins[1:horizon + 1] if len(margins) > 1 else margins
full_min = min(gate_window) if gate_window else 999
```

**Result with horizon patch (CAPX_MIN_MARGIN=0, default)**:
| Defender | eat_alive | eat_died |
|---|---|---|
| baseline | **3/3** | 0 |
| monster_rule_expert | **3/3** | 0 |
| zoo_dummy | **3/3** | 0 |

**9/9 eat_alive** with default knobs. Phase 2 AC ALL PASS:
- vs zoo_dummy ≥ 2/3 → ✅ 3/3
- vs baseline ≥ 1/3 → ✅ 3/3
- vs monster_rule_expert ≥ 1/3 → ✅ 3/3

A still dies 0-1 times per game (mostly post-eat), but eats both caps before that.

## Phase 2.5 tier-screen (in progress)

CAPX_MIN_MARGIN=0, 17 def × 5 seeds = 85 games on Mac.
Acceptance: aggregate cap_eat_alive ≥ 30%.
Result: TBD (filled once complete).

## Phase 0 ABS-baseline (sts, parallel)

Re-baseline with corrected detector (`[ABS_CAP_EATEN]` + `[ABS_A_DIED]`).
17 × 30 = 510 games. Wrapper script had grep-c bug ("0\n0" multi-line) but
post-process via `pm46_v2_rebuild_csv.py` recovers clean CSV from per-game logs.
Result: TBD.

## Files

- `minicontest/zoo_reflex_rc_tempo_capx.py` — CAPX agent (665 lines).
- `minicontest/zoo_reflex_rc_tempo_capx_solo.py` — solo wrapper.
- `minicontest/zoo_reflex_rc_tempo_abs_solo.py` — ABS-solo wrapper +
  `[ABS_CAP_EATEN]` + `[ABS_A_DIED]` shim.
- `experiments/rc_tempo/pm46_v2_a_solo_matrix_corrected.sh` — sts launcher (BUG: grep-c).
- `experiments/rc_tempo/pm46_v2_capx_smoke.sh` — Phase 2 smoke (3×3).
- `experiments/rc_tempo/pm46_v2_capx_tier_screen.sh` — Phase 2.5 (17×5).
- `experiments/rc_tempo/pm46_v2_rebuild_csv.py` — clean CSV from logs.
- `experiments/rc_tempo/pm46_v2_compare_capx_vs_abs.py` — Phase 4 analysis.

## Open Questions

- `CAPX_GATE_HORIZON=8` default — should it be revisited per defender class?
  Tier-A strong defenders may need shorter horizon (more reactive); Tier-C weak
  defenders may benefit from longer horizon (more committed plans). Phase 4 candidate.
- Is the gate horizon design closer to ABS's reflex behavior than the spec's
  worst-case threat model? Likely yes — simpler and more empirically grounded.

## Next steps

1. Phase 2.5 tier-screen complete → check aggregate ≥ 30%.
2. Phase 0 ABS-baseline complete → rebuild clean CSV.
3. Compare CAPX (Phase 2.5 over 5 seeds) vs ABS-baseline (Phase 0 over 30 seeds)
   per defender. Note: sample-size mismatch reduces statistical power, but the
   direction is the smoke target.
4. If CAPX strictly improves on ≥ 12/17 defenders, plan §3.3 strict-improvement
   gate is met (decision: Phase 3 510-game run on sts vs not).
5. Run Phase 3 (17×30 = 510) on sts in tmux.

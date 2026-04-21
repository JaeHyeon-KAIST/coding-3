---
title: "2026-04-21 pm32 — 3-iter ralplan + Mac coding (Step A-C.2) + 16 layouts + Mac smoke"
tags: ["pm32", "ralplan", "consensus", "mac-coding", "layouts", "smoke", "freeze-checkpoint", "session-log"]
created: 2026-04-21T07:04:06.636Z
updated: 2026-04-21T07:04:06.636Z
sources: []
links: []
category: session-log
confidence: high
schemaVersion: 1
---

# 2026-04-21 pm32 — 3-iter ralplan + Mac coding (Step A-C.2) + 16 layouts + Mac smoke

# 2026-04-21 pm32 — Plan v3 APPROVE + Mac coding done, server sweep deferred

## Date
2026-04-21 (long session, 3-iter ralplan + executor + smoke + docs)

## Focus
Plan β capsule-chase hyperparameter sweep (pm32) + execute Mac coding portion (Step A-C.2 of v3 plan). Server sweep (Step E onward) deferred to pm33.

## Activities

### 3-iteration ralplan consensus on pm32-sweep-plan.md
- **iter-1** (Planner v1, 763 lines): Architect REQUEST CHANGES (7 critical/major); Critic ITERATE (3 CRITICAL incl `red_starts/blue_starts` empty bug + `food_per_trig` column missing + CLI flags absent before use, 8 MAJOR incl wrong-metric pre-mortem missing).
- **iter-2** (Planner v2, 1104 lines): Architect APPROVE WITH NOTES; Critic ITERATE (1 NEW CRITICAL: `hth_resumable.py` already exists — plan was about to build duplicate `hth_runner.py`. Architect-Critic concur. Plus 7 new operator-tracked).
- **iter-3** (Planner v3, 1358 lines): Architect APPROVE WITH NOTES; **Critic APPROVE WITH OPERATOR-TRACKED ITEMS**.
- Steelman residual reduced 100% → 30% (iter-2) → 10% (iter-3 — irreducible small-N noise from N=12 academic project, not planning defect).
- Server hardware reality (32-core jdl_wsl Ryzen 7950X) discovered mid-iter-2 → wall budgets halved → enabled Step F3 HTH calibration to be added without busting 6h budget.

### Mac coding executor sub-agent (Step A through C.2)
~34min wall, 25 unit tests + 6 integration gates all PASS:
- Step A: 70 VARIANTS in v3a_sweep.py (5 pm32_p1_* + 20 pm32_aa_* + 10 pm32_ac_* + 5 pm32_rs_* + 30 existing).
- Step B: BETA_TRIGGER_GATE (none|any|exactly_one) + BETA_TRIGGER_MAX_DIST (with `>0` defensive guard) added to `_choose_capsule_chase_action`.
- Step C: BETA_RETREAT_ON_ABORT + my_home_cells slot in RCTEMPO_TEAM (populated by _precompute_team) + _maybe_retreat helper + 3 abort sites repointed + MJ-7 leak guard.
- Step C.0: composite.py single source of truth (compute_score, wilson_ci_95 z=1.96, pearson_with_ci Fisher z, spearman_rho).
- Step C.1: v3a_sweep.py hardening (`--variants-file`, `--layouts-file`, `--validate-csv` with `--allow-truncate` gate + .bak + crashed=1 protection); promote_t1_to_t2.py + analyze_pm32.py SKELETONS with `--dry-run`; filter_random_layouts.py; **hth_sweep.py** (~50 lines, thin wrapper around existing hth_resumable.py — Architect iter-2 reuse fix).
- Step C.2: CLI verification gate (`--help | grep | wc -l == 4`).
- T-U5 added (Critic-S iter-3): pearson + spearman 11 cases incl perfect ±1, no-corr, ties, n<4 NaN, n=12 numpy-validated reference.

### 16 layouts hand-crafted (sub-agent)
- mazeGenerator.py constraint discovered: `add_pacman_stuff` always adds capsules in pairs (max=4) → RANDOM<seed> yields only 2-cap maps → "1-cap only" hard requirement violated → pivoted to hand-crafted .lay files.
- 3 originals retained (defaultCapture, distantCapture, strategicCapture).
- 8 capsule-swap variants: defaultCapture_cap{N,S,Center,Corner}, distantCapture_cap{N,Center}, strategicCapture_cap{N,Corner}.
- 5 hand-crafted topology: pm32_corridorCapture (24×12), pm32_openCapture (24×12), pm32_fortressCapture (28×14), pm32_zigzagCapture (24×12), pm32_chokeCapture (28×11 odd-H for self-mirror choke gap).
- All 13 new files pass 4 verification gates (border-walls, capsule count == 2, exactly one of {1,2,3,4}, 180° point symmetry, BFS connectivity).
- All 13 layouts loaded successfully by capture.py engine after rename to include "Capture" (engine requires "capture" substring case-insensitive in layout name).

### Mac smoke (Step D)
459s wall, 13 var × 6 opp × 2 layout × 2 color × 5g, workers=6, max_moves=200:
- 13/13 variants no-crash.
- **MJ-8 byte-identical PASS**: pm32_aa_none_d999 (13.3% cap / 1.7% die / 0.02 food / 16.7 WR) ≡ beta_v2d (identical) → backward compat confirmed.
- Top 7 variants tied at composite score 10.1 (expected at N=10/cell — discrimination requires T2's N=30/cell).
- pm32_rs_retro_retreat anomaly (cap 25.0% / die 8.3% — only deviation from baseline) — possible retro+retreat interaction, deferred to T2 confirmation.
- pm32_ac_retreat cap=0.0% — retreat too conservative or small-sample noise.

### distantCapture trigger=0% finding (reframed)
- All 60 distantCapture games at max_moves=200 → 0/60 trigger (opp never invades).
- Initially flagged as bug; reframed via user dialogue: trigger=0 means opp doesn't attack → β chase unneeded → variants indistinguishable on such layouts → β v2d ≡ β_path4 ≡ β_retro all play rc82 base.
- "측정 안 되는 게 정상" — wasted compute but not measurement bug.
- Decision: keep max_moves=200 (matches "초반 200moves 전략" intent). pm33 pre-T1 trigger-rate calibration smoke will identify low-trigger layouts to drop.

### Python parity upgrade
- Mac was 3.9.11; jdl_wsl + sts both 3.9.25.
- Non-destructive swap: `uv venv --python 3.9.25 .venv-new` + numpy/pandas + smoke + `mv .venv .venv-old; mv .venv-new .venv`.
- 25 unit tests re-PASS post-upgrade.
- Now Mac/jdl_wsl/sts identical: Python 3.9.25, numpy 2.0.2, pandas 2.3.3, capture.py md5 `afa813a0...`.

### Second server sts provisioned
- AMD Ryzen 9 9950X3D (16C/32T, ~13% faster than jdl_wsl per PassMark, 3D V-Cache 128MB+ likely better for game-tree workloads).
- 30GB RAM (vs 47GB jdl_wsl), RTX 5090 unused (CPU-bound task), Ubuntu 24.04, Python 3.9.25 via uv.
- Setup: ~3min (uv install + clone + venv + deps + smoke). Currently idle, available for pm33 parallel execution.

## Decisions

### Plan v3 architectural (3-iter consensus)
- max_moves=200 for Phase 1 sweep ("초반 전략" intent).
- workers=24 cap (user limit ≤25; SMT contention 16P×2 means effective ~18.4 cores at 24w).
- 70 variants × 4 angles × 11 opps × 16 layouts × 2 colors. Two-tier T1 (5g/cell) → T2 (30g/cell) → F3 HTH calibration (12 var × 6 opp × 4 layout × 2 col × 30g full-1200-move).
- Conjunction ship rule: `r ≥ 0.7 AND r_95_ci_lower > 0.3 AND ρ ≥ 0.7 AND |r-ρ| ≤ 0.2`. Else PROVISIONAL or UNUSABLE.
- "Clear winner" formal: `cap_lower_wilson(v) > cap_upper_wilson(beta_path4) AND die_upper_wilson(v) ≤ 2.5`.

### Freeze-checkpoint deferred (pm32 → pm33+pm34)
- User's idea: pickle GameState at trigger fire → swap β agent → resume. AlphaZero-style checkpoint replay.
- Cost-benefit for pm32: 3-6h coding vs ~50min wall savings → ROI negative for single-use.
- pm33: build save-state-at-trigger + load-state + state-swap harness.
- pm34: use it for broader sweep (100+ variants, 30+ layouts, situation stratification).

### Server sweep deferred to pm33
- All Step A-C.2 done on Mac. Step E (git push + server pull) is just `git push`.
- Server T1 + T2 + F3 ~5h28m server wall, deferred entirely.

## Observations

- 3-iter ralplan consensus caught 3 production-blocking bugs (red_starts empty, food_per_trig column missing, CLI flags absent) that smoke would have surfaced 2-4h later. Worth the ~30min planning time.
- Architect's iter-2 NEW finding (hth_resumable.py reuse) saved 30-50min Mac coding + critical-path untested code risk.
- mazeGenerator.py 2-cap constraint is a project-wide planning hazard for future "diversify layouts" requests. Hand-crafting is the workaround.
- Cache-friendly workloads on 9950X3D 3D V-Cache may exceed 13% headline speedup on Pacman game-tree exploration.
- distantCapture trigger=0 reframing was a key pedagogical moment — "wasted measurement" became "informative non-measurement" once we identified what β chase actually measures.

## Files created/modified (uncommitted at session end)

- 8 modified: zoo_reflex_rc_tempo_beta.py, zoo_reflex_rc_tempo_beta_retro.py, v3a_sweep.py, AI_USAGE.md, open-questions.md, wiki/index.md, wiki/log.md, project-memory.json
- 18 new: composite.py, promote_t1_to_t2.py, analyze_pm32.py, filter_random_layouts.py, hth_sweep.py, test_composite.py, test_env_parsing.py, pm32_smoke_variants.txt, pm32_t1_layouts.txt, fixtures/, pm32-sweep-plan.md, 13 .lay files

## Open items for pm33

1. **Build freeze-checkpoint infra** (decided pm32 end): `phase1_runner.py` --save-state-at-trigger + --load-state + state-swap. Estimated 4-6h.
2. **Step E → F1 → F2 → F3 server sweep** if not pivoting to freeze infra first.
3. **2nd server (sts) activation strategy**: Plan A (sts F3 parallel) / B (T1 50/50 split) / C (sts standby).
4. **Trigger-rate calibration smoke** before T1 launch: 1var × 16L × 11opp × 2c × 1g ≈ 60s. Drop layouts with trigger rate < 20% to save wasted T1 wall.
5. Address open-questions.md items still unresolved (12 carryover from pm32 plan v3).

## Next-session priority

If user wants fastest result → execute Step E → F1 → F2 → F3 directly (use existing pm32 infra, ~5h28m server wall).
If user wants long-term ROI → build freeze infra in pm33 first, then pm34 broader sweep with cached states.
User indicated pm33 = freeze infra build, pm34 = broader sweep execution.

## Commits

(none yet — pm32 changes uncommitted at session end; will commit at start of pm33 or end of pm32 if user requests)

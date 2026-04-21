# Open Questions

## STRATEGY.md — CS470 A3 Pacman CTF — 2026-04-14

### Original Planner-flagged questions

- [ ] **Opponent-model reduction soundness.** We collapse 4-agent minimax to 1-enemy-closest. Is there a cheap improvement (expectimax over two enemies weighted by distance; or 2-enemy minimax aggressively pruned) within the 0.70s budget? — Why it matters: baseline2 is the report's "search" reference; underperformance weakens the comparison. **STATUS: addressed by §4.2 revision — 2-enemy minimax depth 3 is now the default, 1-enemy frozen is fallback only.**
- [ ] **MCTS node transposition granularity.** Proposed key ignores teammate position and exact food set. Is food-count coarsening acceptable, or does it hurt late-game? — Why it matters: too-coarse keys cause incorrect reuse; too-fine defeat transposition. May need per-layout tuning.
- [ ] **Evolution compute budget vs quality.** N=40 G=30 ≈ 10h. Is 30 generations enough for a 52-dim CEM under noisy fitness (~84 games/eval)? Alternatives: smaller genome (share W_OFF=W_DEF initially), or shorter horizon with more gens. — Why it matters: under-training caps the 40-pt win rate and the ELO curve figure. **STATUS: addressed by §6.3 two-phase schedule (10 gens at 32 dims + 150 games, then 20 gens at 52 dims + 84 games).**
- [ ] **Role-switch hysteresis (3 turns) is hand-set.** Should this be evolved in Phase 2? — Why it matters: potential free performance; complexity cost if wrongly tuned. **PARTIALLY ADDRESSED in §5.1: 2 turns when losing, immediate on food-carrying invader. Still not evolved — may add to PARAMS.**
- [ ] **Bottleneck detection cost in `jumboCapture`.** BFS articulation may approach the 15s init cap. Need to benchmark. Fallback: skip feature in baseline{1,2,3}.py, keep only in your_best.py. — Why it matters: init overrun loses the game before it starts.
- [ ] **Champion pool composition (HALL_OF_FAME).** Draw from final generations only (stronger but narrower), or across all generations (more diverse but weaker)? — Why it matters: affects generalization vs convergence in evolution.
- [ ] **Tie-break policy in evaluator argmax.** Currently random with fixed per-agent seed. Alternative: deterministic preference order (N > E > S > W > Stop). — Why it matters: reproducibility for report; minor play effect.
- [ ] **Report page count.** Rubric says "2+ pages." Stretch to 3-4 with more figures, or keep tight 2 pages? — Why it matters: TA preference unknown; crisp 2-page may outscore padded 4-page.

### Architect-raised follow-ups (added 2026-04-14)

- [ ] **Empirical validation that "UCB-guided leaf search" beats 2-ply minimax with identical leaf eval.** If not, `your_best.py` should switch to minimax. — Why: MCTS-without-simulation is architecturally suspect; HTH test required before baking.
- [ ] **Maximum safe hysteresis lag given MIN_FOOD=2.** Can an invader starting adjacent to a 2-food cluster deterministically win before hysteresis fires? — Why: §5.1 still leaves 2-turn lag in some cases; must measure.
- [ ] **Behavioral-equivalence test between `CoreCaptureAgent`-inherited and flattened champion.** AST self-containment ≠ behavior equivalence. **§4.0 step 7 now enforces 50-game HTH pre/post-flatten with [45%,55%] acceptance window.**
- [ ] **Does the monster co-evolution auto-replacement rule actually trigger under the planned compute budget?** If monsters are replaced before gen 30, report this as a headline result; if not, remove `monster_bonus` from fitness. — Why: unused mechanism distorts selection.
- [ ] **Fraction of evolved-champion moves saturating 0.70s on dev hardware.** If >30%, TA-hardware behavior diverges. — Why: Principle 3 only holds if training and deployment inference distributions match. Addressed partially by §4.0 CPU-throttled pre-check.
- [ ] **CEM drift check.** Measure per-generation `(elite_mean - gen_mean) / gen_std` for 5 consecutive gens. If ratio < 1.0, we're drifting, not training — switch to CMA-ES. **§6.3 sanity monitor added.**
- [ ] **`select_top4.py` tie-breaking.** Deterministic by genome hash for evolved, lex by filename for zoo. **Documented in §4.0 step 8.**
- [ ] **Coordinated-pincer attack failure mode of 1-enemy-frozen fallback** — can a deliberate TA opponent (one threatens food, other cuts home) exploit? — Why: §4.2 fallback still has this weakness; measure in eval matrix.
- [ ] **`_safeFallback` second-order guard sufficiency.** `Directions.STOP` is always legal per game.py Actions, but is there ANY path from `chooseAction` to a crash that bypasses both wrappers? — Why: §3.1 two-layer guard is belt-and-suspenders, but Principle 1 demands zero crash.

### Critic-raised follow-ups

- [ ] (All iteration 1 items patched and verified APPROVED in iteration 2. New follow-ups below.)

### Gemini orthogonal additions (not yet integrated — stretch)

- [ ] **Online Opponent Profiling / Style-Switching** — detect "permanent defender" or "pure rusher" opponents from first ~40 ticks of observed behavior; switch evolved agents into pre-trained counter-style weight sets. Potential +5-10% tournament win rate. Added if time permits post-M7.
- [ ] **Dynamic Bottleneck via Max-Flow** — not just static BFS articulation. During play, weight edges by proximity to active enemies and compute `max_flow(my_pacman → home)`. If flow drops below threshold → force retreat regardless of `numCarrying`. Replaces static `f_inDeadEnd` with live capacity analysis.
- [ ] **numpy MLPs for Non-linear Features** — tiny MLP (e.g., 20→10→1) trained alongside linear weights via CEM. Captures XOR logic like "safe IFF (ghost_scared OR ghost_dist>5) AND (not dead_end)." Since numpy is allowed. Verify inference time fits budget.
- [ ] **Entry-Kill Border Modeling** — verify that minimax models the "Pacman-becomes-ghost-at-midline" transition as a terminal state. Common tournament loss = border camping. §4.2 should explicitly test this in an adversarial unit case.
- [ ] **MIN_FOOD=2 Endgame Suicide-Reset** — when score_lead > 0, only 2 food remain, and agent is trapped, often better to die (respawn home) than stall. Current plan's §5.4 endgame mode doesn't cover this.
- [ ] **Respawn Asymmetry Survival Mode** — when teammate dies and respawns at (1,1), we're effectively 1v2 for ~20 moves. Detect this and shift surviving agent into SURVIVAL (defensive, no raids) until teammate reaches midline. Missing from §5.1 role logic.

### Gemini report narrative enhancements (stretch; not required)

- [ ] **Phase Transition Analysis figure** — plot "Avg Food Carried" vs "Enemy Proximity" for champion vs baselines. Shows champion "bails earlier" than baselines. Richer than win-rate bar chart.
- [ ] **State-Space Value Heatmaps** — visualize evaluator value function across a standard layout. Show champion sees "Corridors of Risk" that simpler agents don't.
- [ ] **Failure Case Autopsy subsection** — identify a specific layout (e.g., `bloxsCapture`) where champion still fails. Academic maturity signal > perfect result.

### Codex sample-design improvements (partially integrated, more stretch)

- [ ] **Sep-CMA-ES as fallback** — if CEM + CRN + sequential halving still shows drift in Phase 2b, switch to separable CMA-ES (numpy-implementable). Trip-wire: §6.3 sanity monitor alerts for 5+ consecutive gens.
- [ ] **Elite re-eval to ~336 games** (Codex recommendation) — beyond sequential halving. If compute budget tight, drop to 224 with CRN (currently set).

## pm32-sweep-plan.md — pm32 Server Sweep — 2026-04-21 (v1 entries below; v2 entries further below)

### Resolved in v2 of the plan
- [x] **RESOLVED — Server `--workers 12` parity** — Server confirmed via SSH as 32 logical CPUs, idle. v2 plan moves to `--workers 24` with 8 cores reserved for OS. Wall budgets recalculated; T1 1.8h not 3h.
- [x] **RESOLVED — `--workers 12` for monster_rule_expert overhead** — Now workers=24 with explicit instruction to drop to workers=16 if wall_summary.csv shows monster outliers. Same mechanism, different threshold.
- [x] **RESOLVED — RANDOM seed pool sufficiency** — `filter_random_layouts.py` now built in Step C.1 with auto-expand pool 1001-1020 → 1001-1030 → 1001-1050 if yield < 12. Operator-visible yield count printed before T1 launch.
- [x] **RESOLVED — Env var naming clash** — Documented inline in BOTH `zoo_reflex_rc_tempo_beta.py` and `zoo_reflex_rc_tempo_beta_retro.py` headers per MINOR #16. Distinct names (BETA_TRIGGER_GATE vs BETA_RETRO_TRIGGER_MODE) with explanatory paragraph.
- [x] **RESOLVED — Wilson 95% CI implementation** — Pure-Python `wilson_ci_95` lives in `experiments/rc_tempo/composite.py` per Step C.1. Single source of truth; unit-tested via T-U4 against fixture stub.
- [x] **RESOLVED — T1→T2 budget overrun rule** — Replaced "auto-cut" with explicit operator gate per MAJOR #10. promote_t1_to_t2.py prints wall and recommends --top-n; operator decides.
- [x] **RESOLVED — Full-game HTH validation post-sweep** — Now in pm32 scope as Step F3 per MAJOR #11. Outputs Pearson r between Phase 1 composite and HTH WR. Decision rule: r ≥ 0.7 → ship; 0.5 ≤ r < 0.7 → provisional (pm33 deeper HTH); r < 0.5 → unusable (escalate to pm33 metric redesign).

### Carried over (still open, partially mitigated)
- [ ] **`max_moves=200` cutoff coverage** — pm31 used `max_moves=500`. v2 keeps 200 to fit budget. Mitigation: Mac smoke (Step D) inspects `moves_post_trigger` mean; bump to 300 if > 100. — Why it matters: under-counted post-trigger games bias cap%/die%.
- [ ] **β_retro V table coverage in loose-trigger crosses** — `BETA_RETRO_TRIGGER_MODE=loose` allows chase when `opp_pacman ≥ 1` (including 2). V table is 1:1 only; loose-retro with 2 defenders degrades to rc82 fallback. — Why it matters: pm32_rs_retro_loose_path4 may be uninformative. Mitigation: T1 summary table called out; F3 includes the variant for HTH check.

### NEW in v2 (status updated by v3)

- [ ] **F3 wall under-estimate risk** — F3 estimate assumes ~5s/game per pm30 measurement, but pm30 used different opponent set. monster_rule_expert + rc47 + rc166 may be slower in HTH (full 1200 moves vs Phase 1 ~150 moves). — Why it matters: F3 budget 1.0-1.2h could blow to 1.5h+, shrinking the 1h server margin. Mitigation: launch F3 with smaller candidate set (8 not 12) if T2 already consumed > 2.5h. **v3 update**: explicitly inlined into §6.F3 wall estimate as "1.4h tail risk" + linked to §8 "realistic margin 7-30min" footnote.
- [x] **RESOLVED in v3 — Pearson r threshold rationale** — Per MJ-3, ship gate is now a CONJUNCTION: `r ≥ 0.7 AND r_95_ci_lower > 0.3 AND ρ ≥ 0.7 AND |r - ρ| ≤ 0.2`. Pearson 95% CI computed via Fisher z back-transform in `composite.pearson_with_ci`; Spearman ρ via `composite.spearman_rho`. Inlined into §4 Scenario 4, §6.F3, §9 ADR.
- [x] **RESOLVED in v3 — `hth_runner.py` is new untested code on critical path** — Per CR-1, F3 now wraps EXISTING `experiments/rc_tempo/hth_resumable.py` (verified contract: argparse 134-144, FIELDS 38-40, fsync 86, run_match call 35, wilson_95 z=1.96 at line 47, timeout_s=120). New code reduced to ~50-line orchestrator `hth_sweep.py` analogous to `v3a_sweep.py:run_variant`. Tested I/O code is reused, not rewritten.
- [ ] **CSV column-set fatal-mismatch may strand operator** — `--validate-csv` exits non-zero on column drift; operator may not know what to do. — Why it matters: silent corruption was the v1 risk; loud corruption is the v2 risk. Mitigation: error message must enumerate the differing columns and suggest remediation (delete file vs migrate schema). **v3 status**: still open — implementation guidance not yet added to `--validate-csv` error path. Tag for executor to address during C.1 implementation.
- [x] **PARTIALLY RESOLVED in v3 — Stub fixture `fixtures/pm31_s5_stub.csv` may not match reality** — Per MJ-6, Step E.0 NOW REQUIRES `experiments/rc_tempo/fixtures/pm31_s5_subset.csv` (REAL pm31 S5 subset) to be scp'd locally and committed before Step E. Step E REQUIRED fixture cross-check ranks beta_path4 > beta_v2d on REAL data. Stub is now only a Mac-only sanity check; real-data check is the production gate.
- [x] **RESOLVED in v3 — Promote stratification may force a weak variant into T2** — Per MJ-4, stratification is now CONDITIONAL by default: `--stratify-angles` only forces an angle's best variant if it clears `--die-ceiling 2.5` AND is within `--stratify-tolerance-pp 5.0` of #top-N composite. Else angle gets no slot. Skipped angles are printed as `STRATIFY SKIPPED for angle <name>: best=<v> Δ=<x>pp > tol`.
- [ ] **Step F3 layout subset (4 fixed only) is narrower than T2** — T2 includes ~16 layouts (4 fixed + ~12 RANDOM); F3 drops the random layouts. — Why it matters: pm32 winner ranked on T2's broad layout set may lose F3 specifically because F3 doesn't sample its strong layouts. Mitigation: F3 results must be checked against T2 per-layout breakdown for the same 4 fixed layouts only. **v3 status**: still open — `analyze_pm32.py` SHOULD emit a per-fixed-layout T2 vs F3 comparison row to make this contrast visible. Tag for executor.
- [ ] **Naming asymmetry header doc not enforceable mechanically** — Future contributors may "consolidate" the two env vars unaware of the rationale. — Why it matters: silent regression of either β default. Mitigation: docs/AI_USAGE.md entry, plus a one-line assertion at registerInitialState that logs `BETA_TRIGGER_GATE` value the first time it is seen as non-default (so contributor sees it in stderr). **v3 status**: still open — header doc is preserved per MINOR #16 but the runtime stderr assertion suggested in v2 is not yet specified for executor.

### NEW in v3

- [ ] **`hth_sweep.py` env-var marker passing** — `hth_resumable.py` accepts `--agent` as a single string, not a variant + env-dict pair. `hth_sweep.py` must reproduce v3a_sweep.py's logic of converting a VARIANTS entry (`{'__BETA__': '1', 'BETA_PATH_ABORT_RATIO': '4'}`) into `--agent zoo_reflex_rc_tempo_beta` + `env=...` for the subprocess. — Why it matters: a transcription error would run the wrong agent under the variant name, polluting F3 results. Mitigation: T-I1 should include 1 sanity HTH game per variant during Mac smoke that asserts the variant's expected env-vars are observable in the agent (e.g., via `BETA_RETRO_TRACE=1` debug log).
- [ ] **`composite.pearson_with_ci` Fisher z back-transform with N=12** — Fisher z assumes bivariate normality; with N=12 the CI is approximate. — Why it matters: a "tight CI" claim might over-promise rigor. Mitigation: in `analyze_pm32.py` markdown output, explicitly cite "approximate via Fisher z; not exact for N<30".
- [ ] **Step E.1 acceptance gates require ground-truth thresholds untested at this hardware** — Median ≤ 1.2s, max ≤ 5s, monster ratio ≤ 2× are educated guesses. — Why it matters: a too-strict gate could falsely halt T1; a too-loose gate could miss real degradation. Mitigation: capture E.1 wall numbers in pm32 session log so pm33 can re-baseline.
- [ ] **MJ-7 RCTEMPO_TEAM.reset() inside _precompute_team interacts with `tempo_enabled` ordering in `registerInitialState`** — `registerInitialState` calls `RCTEMPO_TEAM.reset()` first, then `_precompute_team`, then `RCTEMPO_TEAM.tempo_enabled = ...` based on _precompute_team's effects. Adding ANOTHER `RCTEMPO_TEAM.reset()` inside `_precompute_team` could nuke fields the outer reset already set. — Why it matters: subtle initialization ordering bug. Mitigation: be explicit in implementation — only reset `my_home_cells` and `tempo_enabled` slots, NOT the full state. Verify via T-U3 sub-test (b).
- [ ] **`--data-quality-check` threshold (n < 0.8 × expected, crashed% > 5%) is hand-set** — Same risk as Step E.1 thresholds. — Why it matters: a variant excluded for crashed=8% might still be a valid winner. Mitigation: print BOTH "would-be rank if included" AND "exclusion reason" so operator can override via `--no-data-quality-check`.
- [ ] **Cumulative server wall ≈ 5h28m vs realistic margin 7-30min is tight** — §8 acknowledges this. — Why it matters: even one ambiguous T2 result that warrants a re-run will exceed the 6h budget. Mitigation: pre-decided, defer ambiguity to pm33 not retry inside pm32; document decision in operator log when invoked.

### NEW in pm32 END (2026-04-21)

- [ ] **distantCapture trigger=0% at max_moves=200** — Mac smoke (5g × 6opp × 2L × 2color) showed 0/60 trigger on distantCapture cell. Reframed as "opp doesn't invade → β chase unneeded → variant differences invisible there". Not a bug. — Why it matters: T1 wall on such layouts produces 0 information for β-discrimination. Mitigation: pm33 pre-T1 trigger-rate calibration smoke (1var × 16L × 11opp × 2c × 1g ≈ 60s) → drop layouts with trigger rate < 20% from T1.
- [ ] **mazeGenerator.py forces 2-cap maps** — `add_pacman_stuff` inserts capsules in pairs (max=4); `--seed-pool 1001-1020 → 1050` yields 0 1-cap maps. Layout pool pivoted to hand-crafted .lay files. — Why it matters: future "scale up layout diversity" requests cannot use RANDOM<seed>. Must hand-craft or skip mazeGenerator entirely. Mitigation: 5 hand-crafted topology layouts created in pm32.
- [ ] **Mac smoke pm32_ac_retreat cap=0%** — retreat-on-abort variant produces 0 capsule grabs at N=10/cell. May be too conservative OR small-sample noise. — Why it matters: if T2 confirms cap=0%, retreat-on-abort is a no-go feature. Mitigation: T2 30g/cell + per-opp breakdown will resolve.
- [ ] **Mac smoke pm32_rs_retro_retreat cap=25%/die=8.3%** — only variant deviating from baseline at N=10. Higher cap AND higher die — possibly retreat path interferes with retro chase commit. — Why it matters: retro+retreat stack may have unintended interaction. Mitigation: T2 + per-opp breakdown.
- [ ] **2nd server `sts` activation strategy** — sts (Ryzen 9950X3D 32T, ~13% faster than jdl_wsl) provisioned but not yet integrated into sweep. — Why it matters: doubling server capacity could halve wall OR enable parallel F3-on-refs early. Mitigation: pm33 first action — choose Plan A (sts F3 parallel) / Plan B (T1 50/50 split) / Plan C (sts standby).

### Freeze-checkpoint roadmap (pm33 + pm34)

- [ ] **pm33: Build save-state-at-trigger + load-state + state-swap harness** — `phase1_runner.py --save-state-at-trigger <pkl>` pickles GameState at trigger fire; `--load-state <pkl>` loads it, swaps A's agent class, runs registerInitialState on resumed state, continues game. Cache one trigger state per (opp, layout, color, seed) tuple. Estimated cost: 4-6h coding + spike test for pickle compatibility (GameState may have non-pickle objects: distancer, layout). Risk: silent state corruption, opponent internal state mismatch. — Why this matters: pre-trigger phase is 40-80 moves of identical compute across all variants in same (opp, layout, color, seed). Caching trigger state → measure ONLY chase phase per variant → ~50-80% wall reduction.
- [ ] **pm34: Use freeze-cache for broader sweep** — 100+ variants, 30+ layouts, situation stratification (ahead/behind/tied score). Wall ~1-2h (vs 5h28m without cache). Enables wider exploration without budget pressure.

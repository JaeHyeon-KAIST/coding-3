# pm32 — Server Sweep: β Capsule-Chase Hyperparameter Search (v3 — FINAL)

**Date**: 2026-04-21 pm32
**Author**: Planner (RALPLAN-DR consensus, deliberate mode, **iteration 3 — FINAL**)
**Audience**: Architect + Critic reviewers (final pass), then executor
**Status**: FINAL v3 — addresses Architect iter-2 APPROVE WITH NOTES + Critic iter-2 ITERATE. All CR/MJ/MN items landed.
**Blast radius**: HIGH — this is the project's core early-game strategy validation. A wrong winner from this sweep propagates into the final submitted agent.

---

## ADR Iteration 3 — what changed since v2

All iter-2 CRITICAL/MAJOR/MINOR findings landed. The plan is now executable end-to-end.

- **[CR-1] F3 harness: replace NEW `hth_runner.py` with thin `hth_sweep.py` wrapping existing `hth_resumable.py`.** Verified contract at `experiments/rc_tempo/hth_resumable.py`: argparse 134-144 (`--agent`, `--opponents`, `--layouts`, `--colors`, `--games-per-cell`, `--workers`, `--out`, `--metrics-out`, `--master-seed`); FIELDS 38-40 (winner/red_win/blue_win/tie/score/crashed/wall_sec); per-cell key 65-66; atomic writes 80-86 (flush+fsync); wilson_95 z=1.96 at line 47; calls `run_match` (`experiments/run_match.py` confirmed) with `timeout_s=120`. v2 plan's "Option (b) build hth_runner.py" was wrong — `analyze_hth.py` is the AGGREGATOR; `hth_resumable.py` is the RUNNER and already has the exact contract we need. New `hth_sweep.py` (~50 lines) is just a thin orchestrator analogous to `v3a_sweep.py:run_variant` (lines 100-123) that loops over candidate agents and subprocess-calls `hth_resumable.py`. Saves ~30-50min Mac coding (~100→~50 lines) and eliminates v2 open-question "untested critical-path code" (resolved).
- **[CR-2] Step E.1 NEW — workers=24 server smoke + monster_rule_expert pre-check.** Step E uses workers=8 (parity); T1 uses workers=24 (untested SMT). E.1 inserts between E and F1 with same matrix at workers=24. Acceptance: median wall ≤ 1.2s/game, max ≤ 5s, 0 forfeits, monster_rule_expert mean wall ≤ 2× rest-of-opps median. Halt and reduce workers if any fail. ~10min wall.
- **[MJ-3] r-threshold reconciliation: secondary CI gate + Spearman cross-check.** With N=12 variants, point-estimate Pearson r=0.7 has ~95% CI [0.20, 0.91] (Fisher z-back-transform). Plan now requires `r ≥ 0.7 AND r_95_ci_lower > 0.3` for ship. If lower-bound ≤ 0.3, escalate to PROVISIONAL regardless of point estimate. `analyze_pm32.py` also reports Spearman ρ alongside Pearson r; if `|r - ρ| > 0.2`, flag inconsistency in output. Updated in §4 Scenario 4, §6.F3 decision rule, §6.C.1.d analyze spec, §9 ADR follow-ups.
- **[MJ-4] promote_t1_to_t2.py defaults locked.** `--die-ceiling 2.5`, `--stratify-angles`, `--buffer-pp 2.0`, plus NEW `--stratify-tolerance-pp 5.0` are all DEFAULTS (operator can override). Stratification only forces an angle if its best variant clears `die_ceiling` AND is within `stratify_tolerance_pp` of #top-N composite — prevents diluting T2 budget on a known-weak angle.
- **[MJ-5] `--data-quality-check` ON by default in promote_t1_to_t2.py.** Pre-filter excludes any variant with `n_completed < expected_n × 0.8` OR `crashed% > 5%`. Prints `EXCLUDED FOR DATA QUALITY: <name>: reason` before ranking. F1→F2 checklist mandates operator review of exclusion list.
- **[MJ-6] pm31 S5 fixture cross-check at Step E REQUIRED, not "if exists".** New Step E.0 prerequisite: operator MUST `scp` a real subset (`experiments/rc_tempo/fixtures/pm31_s5_subset.csv`) before pm32 starts; halt with operator instruction otherwise. v2's "if exists" semantics replaced with hard precondition.
- **[MJ-7] `RCTEMPO_TEAM.reset()` invoked at top of `_precompute_team` to defeat module-singleton leak across games.** Sequential games on different layouts in the same subprocess could leak `my_home_cells` from game N into game N+1's `_maybe_retreat`. Fix: reset state FIRST inside `_precompute_team`, then check signature. T-U3 extended with a 2-game-different-layouts subprocess test asserting no stale home_cells leak.
- **[MJ-8] Tighten `pm32_aa_none_d999 ≡ beta_v2d` equivalence test.** v2 acceptance "Wilson CI overlap" was a 25pp bar at N≈40 — useless. v3 requires byte-identical CSV rows after sorting by `(opp, layout, color, seed, game_idx)` modulo `wall_sec`. Deterministic seed → identical outcome required.
- **[MN-9] Inline critical open-question content into plan body.** The r-threshold rationale and the 2× monster wall threshold now appear inline in §4, §6.F3, §6.E.1 — no cross-reference required for ship-gate decisions.
- **[MN-10] composite.py z-value harmonized to z=1.96** to match existing `analyze_hth.py:13` and `hth_resumable.py:47`. Docstring documents the choice. v2's `z=1.959963984540054` replaced.
- **[MN-11] Option ζ added to §3 (rejected).** F3-first calibration on 4 refs before T1/T2 commit. Rejected because cost-of-information ordering is immaterial at 32-core (F3-after costs the same as F3-before), and post-T2 winner needs F3 anyway. Documented for completeness.
- **[workers-confirm] workers=24 confirmed as cap (≤25 ceiling per user direction).** Re-emphasized in §8 footer that 24 is chosen, not 32 (full SMT).
- **[realistic-margin] §8 budget realistic margin 7-30min, not 42min.** Architect's pessimistic test: workers=24 + SMT contention + monster_rule_expert tail produces realistic server margin 7-30min, not 42min. Added as dedicated row + footnote in §8 to prevent operator overconfidence.
- **[hth-rename] All `hth_runner` mentions replaced with `hth_sweep` + "wraps existing hth_resumable.py"** throughout §3, §6.F3, §9, §11, §12.

Anything explicitly NOT changing from v2:
- Two-tier sweep design (Option α) — drivers unchanged.
- Mac smoke (Step D) → server smoke (Step E) → server smoke@workers=24 (NEW Step E.1) → T1 → T2 → F3 → Analysis sequencing.
- 70 variants total (5 P1 + 20 Angle A + 10 Angle C + 5 retro-stack + 30 existing).
- 1-capsule-only constraint and `max_moves=200` cutoff.
- Naming `BETA_TRIGGER_GATE` (`none`/`any`/`exactly_one`) and inline header asymmetry doc.
- All output directories under `experiments/artifacts/rc_tempo/v3_sweep_pm32_*/` (gitignored, on home FS).

---

## ADR Iteration 2 — what changed since v1 (preserved for traceability)

Hardware reality check first: server `jdl_wsl` confirmed via SSH as **AMD Ryzen 9 7950X (16 physical × 2 SMT = 32 logical CPUs), 47 GB RAM, idle (load 0.00)**. v1 wall budgets assumed `--workers 12`; revised to `--workers 24` (8 logical cores reserved for OS + headroom). All wall budgets dropped ~50%, which changes the entire shape of the sweep.

Concrete revisions vs v1:

- **[server-cpu] workers=24, not 12.** Wall budgets recalculated throughout (§8 fully rewritten). T1 ~1.8h, T2 ~1.8h, new F3 HTH ~1.0h. Total server wall ~5.0h (incl. 30min slack), comfortably inside 6h budget with 1h margin.
- **[CRITICAL #1] `_maybe_retreat` home_cells fix.** v1 referenced `RCTEMPO_TEAM.red_starts/blue_starts` which are declared at `zoo_reflex_rc_tempo_beta.py:59-60` but **never populated** (verified by grep). Fix: store `my_home_cells` from `_precompute_team` lines 224/231 onto `RCTEMPO_TEAM.my_home_cells`; `_maybe_retreat` reads that. Step C pseudocode rewritten in §6.C.
- **[CRITICAL #2] composite score uses real fields.** `food_per_trig` was a v1 fiction (no such CSV column). Replaced with `food_post = sum(a_food_post_trigger) / max(1, n_triggered)` — matches existing `v3a_sweep.py:163`. New `experiments/rc_tempo/composite.py` module with `compute_score(aggregates) -> float`, consumed by all three places (`v3a_sweep.summarize_sweep`, `promote_t1_to_t2.py`, `analyze_pm32.py`).
- **[CRITICAL #3] CLI surface verification gate (Step C.2).** Inserted between C.1 and D. Two-minute `--help` grep gate that blocks Step D from launching if `--variants-file`, `--layouts-file`, `--validate-csv`, `--allow-truncate` are not all present.
- **[MAJOR #4] variant count reconciled to 70.** v1 enumerated only ~15 new variants (45 total). Revised Step A enumerates exactly 40 new variants by name (5 P1 + 20 Angle A + 10 Angle C + 5 retro-stack), bringing the dict to 30 + 40 = 70.
- **[MAJOR #5] `pm32_smoke_variants.txt` reconciled** to use only names that exist in revised Step A.
- **[MAJOR #6] `--validate-csv` hardened.** `.bak` before any rewrite; refuses to drop `crashed=1` rows; column-set mismatch is fatal; destructive rewrite gated behind `--allow-truncate`.
- **[MAJOR #7] `BETA_TRIGGER_MAX_DIST > 0` defensive guard** added so `=0` (sentinel for "off") doesn't accidentally nuke the agent.
- **[MAJOR #8] T-U3 retro × retreat interaction test** added — verifies retro variant + `BETA_RETREAT_ON_ABORT=1` differs from retro + retreat OFF on a fixed seed.
- **[MAJOR #9] promote_t1_to_t2.py + analyze_pm32.py SKELETONS built in Step C.1** with `--dry-run` mode and pm31 fixture support. Fixture path reality: `experiments/artifacts/rc_tempo/v3_sweep_pm31_s5/` does **not** exist on Mac (verified `ls`); fixtures live on server. Plan now: skeletons run on a synthetic 3-row CSV stub committed at `experiments/rc_tempo/fixtures/pm31_s5_stub.csv` for Mac unit tests; full pm31 fixture validation runs on server during Step E.
- **[MAJOR #10] T1→T2 budget rule made operator-explicit.** Replaced "auto-mitigation" framing with explicit operator checklist gate (§6.F1→F2). With 32-core budget, the cut is unlikely needed — the math is documented in §8.
- **[MAJOR #11] Step F3 — full-game 1200-move HTH calibration ADDED.** Top T2 winners + 4 refs vs 6 opponents × 4 layouts × 2 colors × 30g, ~1.0h. Outputs Pearson r between Phase 1 composite score and HTH WR. r ≥ 0.7 → ship to flatten; 0.5 ≤ r < 0.7 → provisional, recommend pm33 deeper HTH; r < 0.5 → pm32 result UNUSABLE for flatten, escalate.
- **[MAJOR #12] §8 budget reconciled to 32-core reality.** New 13-row table; explicit Mac coding window 2-3h; server window ~5h; total ~7-8h end-to-end with 1h server margin.
- **[MAJOR #13] Pre-mortem Scenario 4 ADDED — wrong-metric optimization.** Detection = F3 r < 0.5; mitigation = F3 itself; recovery = pm33 extended HTH on top 3.
- **[MAJOR #14] "Clear winner" formalized.** Step F2 acceptance: ∃ variant `v` with `cap%_lower_wilson_95 > beta_path4_upper_wilson_95 ∧ die%_upper_wilson_95 ≤ 2.5`. Else: "no winner; recommend STAY at beta_path4". Lock at §6.F2.
- **[MINOR #15] analyze_pm32.py spec forbids WR-sorted ranking.** Composite-sorted only; WR shown as advisory column with footnote.
- **[MINOR #16] Naming asymmetry documented inline.** New header paragraph in both β files explaining `BETA_TRIGGER_GATE` vs `BETA_RETRO_TRIGGER_MODE` semantics. No rename (would break backward compat).
- **[MINOR #17] Wilson CI per-cell vs per-variant claims annotated** wherever they appear.
- **[MINOR #18] `filter_random_layouts.py` moved into Step C.1 prereq.** Auto-expand pool 1001-1020 → 1001-1030 if <12 valid 1-cap. Operator sees yield count before T1 launch.

Anything explicitly NOT changing:
- Two-tier sweep design (Option α) — drivers unchanged.
- Mac smoke (Step D) → server smoke (Step E) → T1 → T2 sequencing.
- 1-capsule-only constraint and `max_moves=200` cutoff (with open-question that smoke validates < 5% truncation rate).
- Naming `BETA_TRIGGER_GATE` (`none`/`any`/`exactly_one`) chosen over reusing `BETA_TRIGGER_MODE` to avoid the strict/loose semantic clash with β_retro.
- All output directories under `experiments/artifacts/rc_tempo/v3_sweep_pm32_*/` (gitignored, on home FS).

---

## TL;DR

Two-tier sweep + HTH calibration over the β / β_retro capsule-chase agent across **70 variants × ~16 layouts × 11 opponents × 2 colors** at `max_moves=200`, primary metric is composite score `cap% - 2*die% + 5*food_post` with hard die ≤ 2.5%. T1 (broad, 5 g/cell) ranks all variants; T2 (deep, 30 g/cell) confirms top 8-12 with tighter Wilson CIs; **F3 (NEW)** runs full 1200-move HTH on T2 winners + reference variants and reports Pearson r between Phase 1 composite and HTH WR. Goal: push cap from the 55% plateau to 60-70%+ while keeping die ≤ 2%, **and** prove the winner is statistically separable from the current Pareto front (β_path4 / β_slack3 / β_retro). All compute on `jdl_wsl` (32 logical CPUs, idle) with `--workers 24`, in tmux session `work`. Mac coding window ~2-3h (now includes promote/analyze skeletons), server window ~5h with 1h margin against the 6h budget.

---

## 1. Principles (immutable for this sweep)

1. **Backward compatibility on env-var defaults.** Every new env var introduced (Angle A, Angle C) must default to a value that **exactly reproduces pm31-committed behavior** when unset. This is non-negotiable — the same code path serves Phase 1 sweeps AND any future full-game HTH baseline reproduction.
2. **Cap+die is primary; WR is advisory.** Per pm31 lesson (`feedback_phase1_metric_no_wr.md`), the Phase 1 runner's WR is a partial-score-at-cutoff artifact and is misleading. Rank by composite `cap% - 2*die% + 5*food_post`; never by WR alone. Full-game 1200-move WR is now an explicit Step F3 deliverable, NOT a primary ranking metric.
3. **Resumability is mandatory, not optional.** Every CSV write is fsynced; every run loop reads existing CSVs before scheduling work. A `kill -9` on the orchestrator must never lose a single completed game. Destructive CSV rewrites only behind explicit operator opt-in (`--allow-truncate`).
4. **Smoke before sweep, every time.** No T1 launch on server without a Mac smoke pass + a server smoke pass demonstrating environment parity. No T2 launch without T1 results inspected manually. No flatten without F3 HTH calibration.
5. **One Pareto front, not a horse race.** A "winner" is formally defined: ∃ variant `v` with `cap%_lower_wilson_95 > beta_path4_upper_wilson_95` AND `die%_upper_wilson_95 ≤ 2.5%`. Else there is no winner and we stay at `beta_path4`.

---

## 2. Decision Drivers (priority order; trade-off arbitrators)

1. **Statistical reliability at decision time** — when cap%/die% gap is < 3pp, we want N ≥ 800 per variant. Drives the two-tier design (small N for ranking, large N for verification). At 32-core budget, T2 reaches N ≈ 10,560 per variant, yielding Wilson 95% half-width ~1pp on cap%.
2. **Wall-time fits the 6h server budget at workers=24** — total server wall must finish in ~5h with 1h margin. With 32 logical cores: T1 ~1.8h + T2 ~1.8h + F3 ~1.0h + transitions/analysis ~0.4h = ~5.0h. No need to cut variants.
3. **Risk floor: do not regress die%** — even a +5pp cap improvement is rejected if die% > 2.5%. The sweep optimizes for cap subject to a hard die ceiling, not unconstrained max(cap).

---

## 3. Viable Options Considered

### Option α — **Two-tier sweep + HTH calibration (RECOMMENDED, REVISED)**

**Design**: T1 broad (5 g/cell × 70 variants × 11 opp × ~16 layout × 2 colors ≈ 154,000 games at ~1.0s each on server) → eliminate to top 8-12 by composite score → T2 deep (30 g/cell × ~12 variants × same matrix ≈ 158,400 games) for the survivors → **F3 HTH calibration** (30 g/cell × ~12 variants × 6 opp × 4 layouts × 2 colors ≈ 17,280 games × 5s ≈ 1h).

**Pros**:
- Two-stage filter naturally controls noise: T1 rejects obviously dominated variants cheaply; T2 gives publication-grade confidence on candidates.
- F3 HTH calibration directly addresses pm31's headline finding (β v2d 75.65% WR ≠ Phase 1 cap 52%) by measuring the correlation between the Phase 1 metric we're optimizing and the actual game-outcome metric.
- Same harness reused: T1, T2 = `phase1_smoke.py`; F3 = a thin wrapper that runs full games (modify only `--max-moves` cap).
- Resumable at all three stages; kill-9 safe.

**Cons**:
- Three output directories to manage (mitigated by `experiments/artifacts/rc_tempo/v3_sweep_pm32_t{1,2,hth}/`).
- T1 → T2 promotion criteria must be locked BEFORE T1 finishes (or post-hoc cherry-picking). Locked in §6.F1→F2.
- F3 requires a full-game runner, not the early-exit `phase1_runner.py`. **REUSES existing `experiments/rc_tempo/hth_resumable.py`** (verified contract: argparse 134-144, FIELDS 38-40, fsync 86, run_match call 35) via thin new `hth_sweep.py` orchestrator (~50 lines).

**T1 → T2 promotion rule (locked)**: top 8 by composite, plus 4 forced reference variants (`beta_v2d`, `beta_path4`, `beta_slack3`, `beta_retro`), plus conditional stratification floor (≥1 from each of 4 angles, only if angle's best variant clears die_ceiling AND is within `--stratify-tolerance-pp 5.0` of #top-N composite). Up to 12 in T2.

**T2 → F3 promotion rule (locked)**: all variants with `cap%_lower_wilson_95 > beta_v2d_point_estimate AND die%_upper_wilson_95 ≤ 2.5%`, plus 4 reference variants (always included). Cap at 12 to keep F3 within budget.

### Option β — **Single-tier deep (REJECTED)**

**Design**: 15 variants × 30 g/cell × full matrix ≈ 247,500 games — too many to fit, so cut to ~12 variants. Skip ranking phase. Skip F3.

**Cons**: Cuts variant count from 70 → 12, sacrificing exploration breadth. pm31's discovery that `BETA_PATH_ABORT_RATIO=4` was Pareto-best emerged from sweeping 5+ ratio settings — pre-pruning to "the obvious 12" would have missed it. With 32-core budget, breadth is no longer expensive.

**Invalidation**: rejected — exploration breadth is now nearly free, removing the only reason to consider this option.

### Option γ — **Three-tier (T0 micro × T1 broad × T2 deep) (REJECTED)**

**Cons**: T0 with 2 g/cell is too noisy to filter on metric (a 0/2 die is indistinguishable from 0/2 cap). It only catches *crashes*, which Mac smoke (Step D) and server smoke (Step E) already exercise. Adds latency.

**Invalidation**: rejected — T0 is functionally redundant with Steps D + E.

### Option δ — **Single-tier wide-and-shallow only (REJECTED)**

**Cons**: 8 g/cell still gives Wilson 95% half-width ≈ 4.7pp at cap=55% (per-cell N=8). We cannot statistically separate β_path4 (55.8) from a hypothetical winner at 58% with that N. Fails Driver #1.

**Invalidation**: rejected — insufficient N to statistically resolve the question we're explicitly asking.

### Option ε — **Two-tier WITHOUT F3 HTH calibration (REJECTED)**

**Design**: original v1 plan: T1 + T2 only.

**Pros**: simpler; saves 1h server wall.

**Cons**: directly contradicts pm31 lesson that Phase 1 cap% may not predict full-game WR (β v2d: cap 52% in Phase 1, WR 75.65% in HTH — clearly the metrics differ). Without F3 we cannot know whether our pm32 winner will hold up in real games, AND we explicitly defer the question to pm33 — repeating the Phase 1 vs HTH disconnect.

**Invalidation**: rejected — pre-mortem Scenario 4 (wrong-metric optimization) is unmitigated without F3. With 32-core budget, F3 is affordable (1h vs total budget 5h).

### Option ζ — **F3-first calibration on 4 refs BEFORE T1/T2 (REJECTED, NEW)**

**Design**: Run F3 HTH on the 4 reference variants (β_v2d, β_path4, β_slack3, β_retro) FIRST (~20min wall at 32-core, 4 var × 6 opp × 4 lay × 2 col × 30g = 5,760 games × 5s / 24 = ~20min). Use the resulting Phase 1↔HTH correlation to decide whether T1/T2 are even worth running (if r < 0.5 on the 4 refs, no point sweeping).

**Pros**:
- Catches metric disconnect EARLY, before spending 3.5h on T1+T2.
- Cheap insurance (~20min) against a 3.5h misallocation.

**Cons**:
- 4-point Pearson r is statistically meaningless (95% CI is essentially [-1, 1] at N=4). Cannot distinguish r=0.3 from r=0.9 with that sample.
- Even if r is "low" on the 4 refs, T1/T2 might still find a winner whose Phase 1 metric correlates better with HTH than the references do. Calibration on 4 cherry-picked points doesn't generalize.
- With 32-core budget, cost-of-information ordering is immaterial — F3-after costs the same as F3-before; we don't save wall by reordering. The post-T2 winner needs F3 anyway.

**Invalidation**: rejected — small-N Pearson is uninformative; reordering doesn't save wall at 32-core; post-T2 winner needs F3 regardless.

---

## 4. Pre-mortem (REQUIRED, deliberate mode)

### Scenario 1 — Technical failure: variant crash propagates, CSV corruption

**What happens**: A new variant crashes inside one game (e.g., `KeyError` in retrograde lookup with loose trigger). `phase1_smoke.py`'s `subprocess.run` returns non-zero, the parent worker emits `outcome='crashed'` and continues; CSV gets a row with `crashed=1`. Acceptable. The failure mode that worries us is: the **orchestrator** (`v3a_sweep.py`) crashes mid-variant, leaving a partial CSV. Or: a row mid-write is corrupted by SIGKILL, breaking `csv.DictReader` on resume.

**Detection signal**:
- Orchestrator stderr shows traceback before "[sweep] ✓ variant=… done" line.
- Resume run reports `[phase1_smoke] resume: 0 completed` despite a non-empty CSV (DictReader exception swallowed in `load_completed`).
- T1 summary table shows a variant with `n_total << expected` (e.g., 50 instead of 1100).

**Mitigation (preventive)**:
- Wrap each `run_variant` in try/except in `v3a_sweep.py` so one variant's death does not kill the rest of the sweep.
- `--validate-csv` mode (new): walks all CSVs, checks column-set parity (fatal if mismatch), and only drops trailing partial rows IF `--allow-truncate` is also set. Always writes `.bak` first. Refuses to drop rows with `crashed=1`.
- The existing `append_row` already does `f.flush(); os.fsync(f.fileno())` — keep this. Confirm during Step D smoke that crashing the harness mid-row leaves only complete rows behind.

**Recovery path**:
- Per-variant CSVs are independent — if one variant's CSV is unrecoverable, delete just that file and re-run with `--variants <name>`.

### Scenario 2 — Methodological failure: T1 noise picks the wrong T2 candidates

**What happens**: T1 at 5 g/cell × ~22 valid (opp, layout, color) cells per variant = ~110 games per variant; with cap% Wilson half-width ~9pp at N=110, two variants 6pp apart in measured cap% may actually be equal. We then advance the wrong candidates to T2 and spend our deep budget on losers.

**Detection signal**:
- T1 top-12 list contains variants whose composite score is within Wilson CI of variants ranked 13-20.
- T2 results show no clear winner; the "promoted" 8 cluster around the same cap%/die% point as the "non-promoted" 4 reference variants.

**Mitigation (preventive)**:
- **Forced-include 4 reference variants** (`beta_v2d`, `beta_path4`, `beta_slack3`, `beta_retro`) in T2.
- **Promotion buffer**: take top 8 + any variant within 2pp composite-score of #8 (so up to 12 total).
- **Stratify T1 by angle**: ensure ≥1 variant from each of {pm32_p1_combo, pm32_angle_a, pm32_angle_c, pm32_retro_stack} makes it to T2.
- Print T1 ranking table with explicit Wilson 95% CI columns BEFORE the operator picks T2 candidates.

**Recovery path**:
- If T2 inconclusive, declare `beta_path4` the pm32 winner per the formal "no winner" rule.
- If T2 strongly suggests a non-promoted variant might have been a winner (visible in T1 raw data on inspection), re-run T2 with that variant added (~10min for one extra variant at 32-core budget).

### Scenario 3 — External failure: server dies mid-sweep / SSH drop / disk full

**What happens**: After 4h of compute, the server reboots, SSH drops, or disk fills. tmux session `work` survives an SSH drop but not a server reboot.

**Detection signal**:
- `ssh jdl_wsl 'tmux has-session -t work'` returns non-zero.
- `df -h /home` on server shows < 5% free.
- Orchestrator process gone from `ps`.

**Mitigation (preventive)**:
- **All output paths in repo** (`experiments/artifacts/rc_tempo/v3_sweep_pm32_*/`), not `/tmp`.
- **tmux session `work`** with three windows: `t1` (orchestrator), `monitor` (heartbeat tail), `f3` (HTH after T2).
- **Disk-space pre-check** in `v3a_sweep.py`: refuse to start if `shutil.disk_usage(out_dir).free < 1 GiB`. T1+T2 ≈ 150MB; F3 ≈ 200MB; comfortable margin.
- **Heartbeat log**: orchestrator writes to `<out_dir>/heartbeat.log` every 60s.

**Recovery path**:
- After SSH drop: `ssh jdl_wsl tmux a -t work`.
- After server reboot: re-run `v3a_sweep.py` with same args; resume skips done games.
- After disk full: archive completed CSVs to `~/archive/`, free space, resume.

### Scenario 4 — Methodological failure: wrong-metric optimization (NEW)

**What happens**: pm32 winner picked by Phase 1 composite (cap% - 2*die% + 5*food_post) does **not** correlate with full-game 1200-move WR. Specifically: the v2 variant we'd ship to flatten loses HTH against `beta_v2d` despite having higher Phase 1 cap%. This is the pm31 disconnect (β v2d cap 52% vs WR 75.65%) repeating.

**Detection signal**:
- F3 output: Pearson `r(composite, hth_wr) < 0.5` across the F3 candidate set.
- Or qualitative: T2 winner has cap=65% / die=1.5%, but F3 HTH WR drops to 60% (vs `beta_path4` 75%+).

**Mitigation (preventive — including MJ-3 inline rationale)**:
- F3 itself is the primary mitigation — we *measure* the disconnect before flattening.
- F3 candidate list always includes the 4 reference variants so we can compute the regression line, not just the winner's WR.
- `analyze_pm32.py` reports BOTH Pearson r (with 95% CI via Fisher z back-transform) AND Spearman ρ (rank correlation, robust to bounded/nonlinear). With N=12, point-estimate Pearson r=0.7 has ~95% CI [0.20, 0.91] — wide enough that a bare point-estimate ship gate is unsafe. The conjunction in the recovery path enforces (point estimate strong) AND (CI tight) AND (rank correlation agrees).

**Recovery path** (per MJ-3 — secondary CI gate + Spearman cross-check inline):

The Phase 1 composite ↔ HTH WR correlation will be measured at N=12 variants. With N=12 a point-estimate Pearson r=0.7 has 95% CI ≈ [0.20, 0.91] (Fisher z back-transform). A bare point-estimate threshold is therefore insufficient. The decision rule is a CONJUNCTION of (point estimate) AND (CI lower bound) AND (Spearman cross-check):

- **SHIP**: Pearson `r ≥ 0.7` AND `r_95_ci_lower > 0.3` AND Spearman `ρ ≥ 0.7` AND `|r - ρ| ≤ 0.2`. Ship pm32 winner to flatten in pm33.
- **PROVISIONAL**: Pearson r ≥ 0.7 but `r_95_ci_lower ≤ 0.3` (loose CI), OR `0.5 ≤ r < 0.7`, OR `|r - ρ| > 0.2` (rank-correlation disagrees with linear). pm33 priority becomes deeper HTH (200+ games per cell on top 3 candidates); flatten only on top of pm33 winner.
- **UNUSABLE**: Pearson `r < 0.5`. pm32 result UNUSABLE for flatten decision. Stay at `beta_path4` (the pm31 baseline still tested at 75.65% in pm30 HTH). pm33 must redesign the metric.

`analyze_pm32.py` emits BOTH coefficients with CIs, plus a flag if they disagree by > 0.2.

---

## 5. Expanded Test Plan (REQUIRED, deliberate mode)

### 5.1 Unit-level tests (Mac, ~10min, run before Step D)

**T-U1: env var parsing & defaults**
- `BETA_TRIGGER_GATE` defaults to `'none'`, accepts `'any'` / `'exactly_one'`, ignores invalid values silently → `'none'`.
- `BETA_TRIGGER_MAX_DIST` defaults to `999`, accepts integer; non-integer → default. **Defensive guard**: `if trigger_max_dist > 0 and d_to_cap > trigger_max_dist: return None` (so a stale `=0` does not nuke the agent).
- `BETA_RETREAT_ON_ABORT` defaults to `'0'` (rc82 fallback unchanged), accepts `'1'`.
- **Test mechanism**: `experiments/rc_tempo/test_env_parsing.py` (new, ~80 lines). Imports the module, monkey-patches `os.environ`, instantiates the agent in a way that exercises `_choose_capsule_chase_action` decision branches via a mocked `gameState`. If full mocking is too heavy, fall back to integration check via single-game replay (slower but real).
- **Acceptance**: 8 cases pass; 0 unhandled exceptions; "off" sentinel `=0` does not abort.

**T-U2: backward compat reproduction**
- Run a single game (`defaultCapture`, baseline, seed=42, `--max-moves 200`, `--our-team red`) with NO new env vars set.
- Save the resulting CSV row from Mac smoke; compare metric fields against an analogous row from pm31 S5 if available (server only) OR establish a "frozen" Mac reference row at first run and treat it as the regression target.
- **Acceptance**: with no env vars set, the row is byte-identical across two consecutive Mac runs (deterministic given seed). If pm31 S5 fixture is available on server (Step E), additionally compare and require Wilson CI overlap.

**T-U3: retro × retreat-on-abort interaction + module-singleton leak proof (NEW per Architect#7 + Critic-A + MJ-7)**

Two sub-tests, both required:

(a) Same as v2: run two single games — (a1) `BETA_RETREAT_ON_ABORT=0`, (a2) `BETA_RETREAT_ON_ABORT=1`. Same agent (`zoo_reflex_rc_tempo_beta_retro`), same seed, same layout (`distantCapture`, baseline opp), same color. Action stream OR `a_final_pos` must differ between (a1) and (a2) on at least one tick.

**Why retro inherits the retreat path**: `zoo_reflex_rc_tempo_beta_retro.py:271-277` shows that on retro abort, `_chooseActionImpl` falls through to `super()._chooseActionImpl(gameState)` which is β v2d, which calls `_choose_capsule_chase_action` — the function we're adding `_maybe_retreat` to.

(b) NEW MJ-7 — module-singleton no-leak: in a SINGLE subprocess, run game-1 on `defaultCapture` then game-2 on `distantCapture` (different home midline x-coordinates), with `BETA_RETREAT_ON_ABORT=1` for both. After game-2, assert `RCTEMPO_TEAM.my_home_cells` matches game-2's actual midline (NOT game-1's stale value). Implementation: same-process two-game sequence in `test_env_parsing.py`.

**Acceptance**: (a) shows action divergence on the retreat env var. (b) shows `RCTEMPO_TEAM.my_home_cells` after game-2 lies on the game-2 midline x-column, NOT game-1's.

**T-U4: composite score on pm31 fixture stub (NEW per Critic#2)**
- Load `experiments/rc_tempo/fixtures/pm31_s5_stub.csv` (committed, ~30 hand-curated rows representing β_v2d, β_path4, β_retro at known cap/die/food values).
- Compute composite via `experiments.rc_tempo.composite.compute_score`.
- **Acceptance**: ranking has `beta_path4 > beta_retro > beta_v2d` (matches pm31 S5 known result). Score values match a separately maintained reference table within 0.01.

### 5.2 Integration tests (Mac smoke, ~15min, Step D)

**T-I1: every new variant runs to completion on Mac**
- Run `v3a_sweep.py` with `pm32_smoke_variants.txt` (12 variants drawn ONLY from revised Step A's enumerated set).
- ~12 variants × 4 opp × 2 lay × 2 col × 5g = 960 games, ~2-3min wall on Mac at workers=6.
- **Acceptance**: every variant CSV exists; `crashed` column sums to 0 across all rows; trigger rate > 50% on baseline (sanity).

**T-I2: regression — old variants reproduce within Wilson CI**
- Same harness, only `beta_v2d`, `beta_path4`, `beta_retro`. Same seeds.
- Compare cap% and die% to v1's pm31 S5 reference numbers (or fixture stub) with Wilson CI overlap test.
- **Acceptance**: all 3 variants overlap within 95% CI half-width (~9pp at per-cell N=20 ≈ N=20 games per (opp, layout, color) cell after expansion). If overlap fails, halt — backward compat is broken.

### 5.3 E2E parity test (Mac × Server, ~5min wall on server, Step E)

**T-E1: Mac smoke ≡ Server smoke** — outcome columns identical, ≤5% wall_sec deviation. Computed by `scp` server CSVs back, diff against Mac CSVs row-wise.

### 5.4 Observability requirements (build into the sweep, not after)

- **T-O1** heartbeat.log every 60s with elapsed/eta/games_done.
- **T-O2** `wall_summary.csv` per variant: name, wall_sec, games_completed, games_failed, games_per_min.
- **T-O3** `--validate-csv` mode validates column-set parity across all CSVs (fatal mismatch); refuses partial-row deletion without `--allow-truncate`; refuses to drop `crashed=1` rows; writes `.bak` before any rewrite.
- **T-O4** orchestrator stdout: `[t1] {variant}: cap=X.X% die=X.X% food=X.X% N={n} wall={s}s` after each variant; partial ranking table every 10 variants.

### 5.5 Promote/analyze skeleton tests (NEW per Critic-C)

**T-D1: `promote_t1_to_t2.py --dry-run` on fixture**
- Input: `experiments/rc_tempo/fixtures/pm31_s5_stub.csv` plus a synthetic 70-variant fixture extension (auto-generated by stub builder, cap%/die% drawn from a prior).
- Run `promote_t1_to_t2.py --t1-dir <fixture> --top-n 8 --buffer-pp 2.0 --force-include beta_v2d beta_path4 beta_slack3 beta_retro --stratify-angles --dry-run --out /tmp/_t2_smoke.txt`
- **Acceptance**: stdout shows ranking table with `beta_path4` ranked higher than `beta_v2d`; `_t2_smoke.txt` has 8-12 lines including all 4 force-includes.

**T-D2: `analyze_pm32.py --dry-run` on fixture**
- Input: same fixture (treat as both T1 and T2 fake).
- **Acceptance**: stdout shows composite-sorted ranking, with WR column footnoted as "advisory; partial-game score at cutoff"; emits markdown skeleton; emits Pearson r placeholder (NaN if no F3 input).

---

## 6. Step-by-Step Implementation Plan

> File paths assume project root `/Users/jaehyeon/KAIST/26 Spring/인공지능개론/coding 3/`. All paths below are relative.

> **Order**: Steps A-C (coding, Mac), C.1 (resumability + skeletons + filter), C.2 (CLI gate), D (Mac smoke), E (server smoke), F1 (T1), F2 (T2), F3 (HTH), G (analysis).

### Step A — Add P1 + Angle A + Angle C + retro-stack variants to `v3a_sweep.py` VARIANTS

**Changes**: edit `experiments/rc_tempo/v3a_sweep.py` `VARIANTS` dict (currently lines 38-97, ~30 entries).

**Add exactly 40 NEW variants** so the dict has 70 total. Enumerated by angle:

```python
# === pm32 P1: env-combo crosses (5 NEW) ===
'pm32_p1_a3_s2_p4':  {'__BETA__': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '2', 'BETA_PATH_ABORT_RATIO': '4'},
'pm32_p1_a3_s3_p4':  {'__BETA__': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '3', 'BETA_PATH_ABORT_RATIO': '4'},
'pm32_p1_a2_s3_p5':  {'__BETA__': '1', 'BETA_ABORT_DIST': '2', 'BETA_CHASE_SLACK': '3', 'BETA_PATH_ABORT_RATIO': '5'},
'pm32_p1_a3_s2_p3':  {'__BETA__': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '2', 'BETA_PATH_ABORT_RATIO': '3'},
'pm32_p1_a4_s2_p4':  {'__BETA__': '1', 'BETA_ABORT_DIST': '4', 'BETA_CHASE_SLACK': '2', 'BETA_PATH_ABORT_RATIO': '4'},

# === pm32 Angle A: trigger gate × distance gate (20 NEW) ===
# 4 trigger gates × 5 distance caps = 20 cells
'pm32_aa_none_d999':       {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'none',        'BETA_TRIGGER_MAX_DIST': '999'},
'pm32_aa_none_d12':        {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'none',        'BETA_TRIGGER_MAX_DIST': '12'},
'pm32_aa_none_d10':        {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'none',        'BETA_TRIGGER_MAX_DIST': '10'},
'pm32_aa_none_d8':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'none',        'BETA_TRIGGER_MAX_DIST': '8'},
'pm32_aa_none_d6':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'none',        'BETA_TRIGGER_MAX_DIST': '6'},
'pm32_aa_any_d999':        {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '999'},
'pm32_aa_any_d12':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '12'},
'pm32_aa_any_d10':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '10'},
'pm32_aa_any_d8':          {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '8'},
'pm32_aa_any_d6':          {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '6'},
'pm32_aa_one_d999':        {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '999'},
'pm32_aa_one_d12':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '12'},
'pm32_aa_one_d10':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '10'},
'pm32_aa_one_d8':          {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '8'},
'pm32_aa_one_d6':          {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '6'},
# 5 best-known-baseline crosses with the new gate
'pm32_aa_p4_any_d10':      {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '10', 'BETA_PATH_ABORT_RATIO': '4'},
'pm32_aa_p4_one_d10':      {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '10', 'BETA_PATH_ABORT_RATIO': '4'},
'pm32_aa_s3_any_d10':      {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '10', 'BETA_CHASE_SLACK': '3'},
'pm32_aa_s3_one_d10':      {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '10', 'BETA_CHASE_SLACK': '3'},
'pm32_aa_combo_one_d8':    {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '8',  'BETA_PATH_ABORT_RATIO': '4', 'BETA_CHASE_SLACK': '2'},

# === pm32 Angle C: retreat-on-abort × baseline crosses (10 NEW) ===
'pm32_ac_retreat':              {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1'},
'pm32_ac_retreat_path4':        {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_PATH_ABORT_RATIO': '4'},
'pm32_ac_retreat_slack3':       {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_CHASE_SLACK': '3'},
'pm32_ac_retreat_a3':           {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_ABORT_DIST': '3'},
'pm32_ac_retreat_combo_a':      {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '2'},
'pm32_ac_retreat_combo_b':      {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_PATH_ABORT_RATIO': '4', 'BETA_CHASE_SLACK': '2'},
'pm32_ac_retreat_any_d10':      {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '10'},
'pm32_ac_retreat_one_d10':      {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '10'},
'pm32_ac_retreat_one_d8_p4':    {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '8',  'BETA_PATH_ABORT_RATIO': '4'},
'pm32_ac_retreat_safe':         {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '2', 'BETA_PATH_ABORT_RATIO': '6'},

# === pm32 retro-stack: retro × safety-knob crosses (5 NEW) ===
'pm32_rs_retro_path4':          {'__RETRO__': '1', 'BETA_PATH_ABORT_RATIO': '4'},
'pm32_rs_retro_slack3':         {'__RETRO__': '1', 'BETA_CHASE_SLACK': '3'},
'pm32_rs_retro_a3_s2':          {'__RETRO__': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '2'},
'pm32_rs_retro_loose_path4':    {'__RETRO__': '1', 'BETA_RETRO_TRIGGER_MODE': 'loose', 'BETA_PATH_ABORT_RATIO': '4'},
'pm32_rs_retro_retreat':        {'__RETRO__': '1', 'BETA_RETREAT_ON_ABORT': '1'},
```

**Note on `pm32_aa_none_d999`**: this is functionally `beta_v2d` (no gate, infinite distance cap). Keep it explicitly in the sweep as a sanity check that the new code paths preserve baseline behavior — it should land within Wilson CI of `beta_v2d`.

**Verification**:
- `python -c "from experiments.rc_tempo.v3a_sweep import VARIANTS; print(len(VARIANTS))"` from project root prints exactly **70**.
- `python -c "import experiments.rc_tempo.v3a_sweep"` succeeds (no syntax errors).
- Per-angle counts: `grep -c "^    'pm32_p1_" v3a_sweep.py` → 5; `_aa_` → 20; `_ac_` → 10; `_rs_` → 5.

**Rollback**: `git checkout experiments/rc_tempo/v3a_sweep.py`.

**Acceptance**: VARIANTS dict has 70 keys; per-angle counts as above; unit imports succeed.

**Time**: 30min.

---

### Step B — Add Angle A env vars to `zoo_reflex_rc_tempo_beta.py`

**Changes**: edit `minicontest/zoo_reflex_rc_tempo_beta.py` inside `_choose_capsule_chase_action` (lines 312-384).

**New env vars**:
- `BETA_TRIGGER_GATE` — `'none'` (default; current behavior — chase always considered when score < 5 and capsule still up) | `'any'` (only if `opp_pacman_count >= 1`) | `'exactly_one'` (only if `opp_pacman_count == 1`).
- `BETA_TRIGGER_MAX_DIST` — int, default `999` (effectively disabled). When > 0 and `d_to_cap > N`, return `None`.

**Naming asymmetry note (per MINOR #16)**: We add a NEW env var name (`BETA_TRIGGER_GATE`) instead of reusing `BETA_RETRO_TRIGGER_MODE`'s `strict`/`loose` because the semantic is different — for β proper, `'none'` (default) means "no opp_pacman gate at all", while for β_retro, `'strict'` (its default) means "opp_pacman == 1 required". Reusing the same env-var spelling with reversed defaults would silently break either one. We document the asymmetry in a header comment in BOTH files.

**Pseudocode** (insert right after the score-gate at current line 339, before the safety check at line 341):

```python
# pm32 Angle A: trigger gating and distance gate. Defaults preserve pm31 behavior.
# Naming: BETA_TRIGGER_GATE (β proper) is INDEPENDENT of BETA_RETRO_TRIGGER_MODE
# (β_retro only). See header comment for the rationale.
trigger_gate = os.environ.get('BETA_TRIGGER_GATE', 'none')  # none | any | exactly_one
trigger_max_dist = _iv('BETA_TRIGGER_MAX_DIST', 999)

if trigger_gate != 'none':
    try:
        opp_pac = sum(
            1 for opp_idx in self.getOpponents(gameState)
            if getattr(gameState.getAgentState(opp_idx), 'isPacman', False)
        )
    except Exception:
        opp_pac = 0
    if trigger_gate == 'any' and opp_pac < 1:
        return None
    if trigger_gate == 'exactly_one' and opp_pac != 1:
        return None

# Defensive guard (per Architect#5): only enforce the cap when > 0.
# A stale / mistyped =0 must NOT abort all chases.
if trigger_max_dist > 0 and d_to_cap > trigger_max_dist:
    return None
```

**Header comment to add at top of `zoo_reflex_rc_tempo_beta.py`** (right after the existing block at lines 1-22):

```python
# ---------------------------------------------------------------------------
# Naming convention (pm32):
#
#   This file (β proper) uses BETA_TRIGGER_GATE with values:
#     'none'        — chase always considered (default; pm31 behavior)
#     'any'         — chase only if opp_pacman_count >= 1
#     'exactly_one' — chase only if opp_pacman_count == 1
#
#   The sister file zoo_reflex_rc_tempo_beta_retro.py uses
#   BETA_RETRO_TRIGGER_MODE with values 'strict' (default; ==1) | 'loose' (>=1).
#
#   These ARE intentionally different env-var names with different defaults —
#   β v2d (this file) historically had no opp_pacman gate at all; β_retro
#   needs a 1:1 chase subgame for the retrograde V table to be valid. Reusing
#   one var would force one of the two agents to silently regress its
#   committed default. Do not consolidate the two without a behavior audit.
# ---------------------------------------------------------------------------
```

**Verification**:
- T-U1 covers parsing.
- T-U2 (default OFF for both new vars) reproduces β v2d byte-identically.
- `grep "BETA_TRIGGER_GATE\|BETA_TRIGGER_MAX_DIST" minicontest/zoo_reflex_rc_tempo_beta.py` shows exactly the new block.

**Rollback**: `git checkout minicontest/zoo_reflex_rc_tempo_beta.py`.

**`docs/AI_USAGE.md`**: append entry — this file is upstream of `your_best.py` flatten; conservative interpretation per project rule.

**Acceptance**: T-U1 + T-U2 pass.

**Time**: 30min including header docs and unit tests.

---

### Step C — Add Angle C env var to `zoo_reflex_rc_tempo_beta.py` (retreat-on-abort)

**Changes**: edit `minicontest/zoo_reflex_rc_tempo_beta.py`. Four touchpoints: (1) add `my_home_cells` to `RCTEMPO_TEAM` shared state, (2) **`RCTEMPO_TEAM.reset()` invoked at top of `_precompute_team` to defeat module-singleton leak (MJ-7)**, (3) add `_maybe_retreat` helper, (4) replace abort `return None` sites with a retreat-aware return.

**(1) Persist `my_home_cells` to team state** (CRITICAL #1 fix):

In `_RCTempoTeamState.reset()` (current lines 51-73), the `red_starts` / `blue_starts` slots exist but are never written. Replace them with `my_home_cells`:

```python
def reset(self):
    self.initialized = False
    self.game_signature = None
    self.tempo_enabled = False
    self.safety = None
    self.plans = []
    self.top_plan = None
    self.capsule = None
    # pm32: the actual home-side midline cells (was: unused red_starts/blue_starts)
    self.my_home_cells = []
    # Keep the old empty slots for any external code that touched them — but
    # we never populate them and never read them ourselves.
    self.red_starts = []
    self.blue_starts = []
    self.a_index = None
    self.b_index = None
    self.phase = 1
    self.tick = 0
    self.metrics = { ... }
```

In `_precompute_team` (current lines 214-274), at the end of the if/else block where `my_home_cells` is computed (line 224 for red, line 231 for blue), add:

```python
RCTEMPO_TEAM.my_home_cells = list(my_home_cells)
```

**(2) MJ-7 — `RCTEMPO_TEAM.reset()` at top of `_precompute_team` to defeat module-singleton leak**:

The current pattern in `registerInitialState` (lines 182-202) calls `RCTEMPO_TEAM.reset()` BEFORE `_precompute_team`, but only IF `(initialized AND signature mismatches)`. If `_precompute_team` early-returns (e.g., `len(my_capsules) != 1` at line 241 or `safety not safe` at line 254), then on a SUBSEQUENT call with a different layout in the same subprocess, the team state has stale `my_home_cells` from the previous game. Fix: at the start of `_precompute_team`, ALWAYS reset team state slots that this function is responsible for setting:

```python
def _precompute_team(self, gameState):
    # MJ-7: defeat module-singleton leak. Even on early return below, the
    # team's _maybe_retreat helper must NOT read stale my_home_cells from
    # a previous (different layout's) game in the same subprocess.
    RCTEMPO_TEAM.my_home_cells = []
    RCTEMPO_TEAM.tempo_enabled = False
    # ... existing logic continues ...
```

Then `_maybe_retreat` already gates on `if not home_cells: return None`, so an early-return from `_precompute_team` correctly degrades to "rc82 fallback" rather than "use stale home cells from a previous game".

**(3) Add `_maybe_retreat` helper** to the `ReflexRCTempoBetaAgent` class:

```python
def _maybe_retreat(self, gameState, my_pos, distance_fn):
    """pm32 Angle C: when chase aborts and BETA_RETREAT_ON_ABORT=1, take one
    greedy step toward the home midline. Default OFF preserves pm31 behavior
    (return None → rc82 fallback)."""
    if os.environ.get('BETA_RETREAT_ON_ABORT', '0') != '1':
        return None
    home_cells = RCTEMPO_TEAM.my_home_cells
    if not home_cells:
        return None
    home_target = min(home_cells, key=lambda c: distance_fn(my_pos, c))
    legal = gameState.getLegalActions(self.index)
    if not legal:
        return None
    return _next_step_toward(gameState, my_pos, home_target, legal, distance_fn)
```

**(4) Replace abort sites in `_choose_capsule_chase_action`**:

Three current abort sites at lines ~371, ~376, ~379, all `return None`. Each becomes:

```python
return self._maybe_retreat(gameState, my_pos, distance_fn)
```

(Note: helper returns `None` when env var is unset → behavior identical to current.)

**Subtle correctness note**: returning a retreat action MEANS rc82 doesn't get to play this turn. Over many turns this might cost food/defense in some matchups. The whole point is to test whether it nets positive on cap+die. Default is OFF.

**Verification**:
- T-U1 covers `BETA_RETREAT_ON_ABORT` parsing.
- T-U2 (default OFF) reproduces β v2d.
- T-U3 (NEW) verifies retro variant + retreat ON differs from retro + retreat OFF (proves `_maybe_retreat` path is exercised even from retro fallthrough).
- Sanity grep: `grep -A 3 "RCTEMPO_TEAM.my_home_cells" minicontest/zoo_reflex_rc_tempo_beta.py` shows ONE write (in `_precompute_team`) and ONE read (in `_maybe_retreat`).

**Rollback**: `git checkout minicontest/zoo_reflex_rc_tempo_beta.py`.

**`docs/AI_USAGE.md`**: append entry.

**Acceptance**: T-U1 + T-U2 + T-U3 pass.

**Time**: 40min including team-state plumbing + unit test.

---

### Step C.1 — Resumability + observability + skeletons + layout filter

**Changes**: edit `experiments/rc_tempo/v3a_sweep.py` AND create new files.

**(a) v3a_sweep.py additions**:
1. Disk-space pre-check at start of `main()`: `import shutil; assert shutil.disk_usage(args.out_dir).free > 1 * 2**30, "need 1 GiB free"`.
2. Per-variant try/except wrapper around `run_variant`.
3. Heartbeat log writer: `_write_heartbeat(out_dir, msg)` called every 60s in a small thread or between variants.
4. `--validate-csv` mode (CRITICAL — hardened per MAJOR #6):
   - Walks all CSVs in `--out-dir`.
   - Computes column-set; **fatal error + exit non-zero** if any CSV's columns disagree with `phase1_smoke.FIELDS`.
   - Reports trailing partial rows but does **not** delete them unless `--allow-truncate` is set.
   - With `--allow-truncate`: writes `<csv>.bak` first, then drops only trailing rows that fail `csv.DictReader` parsing AND do **not** have `crashed=1` (crashed rows are valuable signal).
5. `--variants-file <path>` reads variant names from text file, one per line.
6. `--layouts-file <path>` reads layout names from text file, one per line.
7. After each variant: append a row to `<out_dir>/wall_summary.csv`: `variant, wall_sec, games_completed, games_failed, games_per_min`.
8. **Replace inline composite score (currently v3a_sweep.py:167-176) with a call to** `experiments.rc_tempo.composite.compute_score(row_aggregates_dict)`.

**(b) New file: `experiments/rc_tempo/composite.py`** (~40 lines):

```python
"""pm32 composite score for ranking variants.

Single source of truth — used by v3a_sweep.summarize_sweep, promote_t1_to_t2.py,
and analyze_pm32.py. Update HERE, not in caller copies.

Inputs: aggregates dict with keys n_total, n_triggered, cap_post, died_post,
        sum_food (sum of a_food_post_trigger across triggered games),
        sum_wall, score_wins.
Outputs: float score (higher = better).
"""
def compute_score(agg: dict) -> float:
    n_g = max(1, agg.get('n_triggered', 0))
    cap_pct  = 100.0 * agg.get('cap_post', 0)  / n_g
    die_pct  = 100.0 * agg.get('died_post', 0) / n_g
    food_pp  = agg.get('sum_food', 0) / n_g  # per triggered game
    return cap_pct - 2.0 * die_pct + 5.0 * food_pp


def wilson_ci_95(k: int, n: int) -> tuple[float, float]:
    """Pure-Python Wilson 95% CI for binomial proportion. (lower, upper) in [0,1].
    No scipy dependency (numpy/pandas only per project constraints).

    z = 1.96 chosen to MATCH existing analyze_hth.py:13 and hth_resumable.py:47
    so any cross-comparison with prior pm30 HTH analyses is bit-identical.
    The 4-decimal-place loss vs 1.959963984540054 is well below per-game noise.
    """
    if n <= 0:
        return (0.0, 1.0)
    z = 1.96  # MATCHES existing project convention; do not change without auditing callers
    p = k / n
    denom = 1.0 + z*z / n
    center = (p + z*z / (2*n)) / denom
    half = (z * (p*(1-p)/n + z*z/(4*n*n)) ** 0.5) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def pearson_with_ci(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    """Pearson r + 95% CI via Fisher z back-transform. Returns (r, ci_lower, ci_upper).
    Used by analyze_pm32.py for Phase 1 composite ↔ HTH WR correlation at N=12."""
    import math
    n = len(xs)
    if n < 4 or n != len(ys):
        return (float('nan'), float('nan'), float('nan'))
    mx = sum(xs) / n
    my = sum(ys) / n
    sx2 = sum((x - mx) ** 2 for x in xs)
    sy2 = sum((y - my) ** 2 for y in ys)
    if sx2 == 0 or sy2 == 0:
        return (float('nan'), float('nan'), float('nan'))
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    r = sxy / (sx2 ** 0.5 * sy2 ** 0.5)
    r_clamped = max(min(r, 0.999999), -0.999999)
    z = 0.5 * math.log((1 + r_clamped) / (1 - r_clamped))  # Fisher z
    se = 1.0 / math.sqrt(n - 3)
    z_lo = z - 1.96 * se
    z_hi = z + 1.96 * se
    r_lo = (math.exp(2 * z_lo) - 1) / (math.exp(2 * z_lo) + 1)
    r_hi = (math.exp(2 * z_hi) - 1) / (math.exp(2 * z_hi) + 1)
    return (r, r_lo, r_hi)


def spearman_rho(xs: list[float], ys: list[float]) -> float:
    """Spearman rank correlation. More robust than Pearson to bounded/nonlinear data.
    analyze_pm32.py emits both; flags if |Pearson - Spearman| > 0.2."""
    n = len(xs)
    if n < 4 or n != len(ys):
        return float('nan')
    def _ranks(vs):
        order = sorted(range(n), key=lambda i: vs[i])
        ranks = [0.0] * n
        for rank_idx, orig_idx in enumerate(order):
            ranks[orig_idx] = rank_idx + 1
        return ranks
    rx = _ranks(xs)
    ry = _ranks(ys)
    return pearson_with_ci(rx, ry)[0]
```

**(c) New file: `experiments/rc_tempo/promote_t1_to_t2.py`** (~150 lines, SKELETON for Step F1→F2 use):

CLI (defaults locked per MJ-4):
```
--t1-dir <path>                   # T1 output dir (read all *.csv)
--top-n <int>                     # default 8
--buffer-pp <float>               # default 2.0; admit variants within N pp of #top-n
--force-include <names>           # variant names to always include
--stratify-angles / --no-stratify-angles
                                  # default ON; ensure ≥1 per angle prefix (pm32_p1, pm32_aa, pm32_ac, pm32_rs)
--stratify-tolerance-pp <float>   # default 5.0; angle's best must be within X pp of #top-N composite
--die-ceiling <float>             # default 2.5; reject any variant with die%_upper_wilson > ceiling
--data-quality-check / --no-dqc   # default ON; exclude variants with n < expected×0.8 OR crashed%>5%
--expected-n <int>                # default 1760 (T1 cell count); used by --data-quality-check
--out <txt path>                  # newline-delimited variant names
--dry-run                         # do not write --out; just print ranking table
```

Logic:
1. **Data-quality pre-filter** (MJ-5, default ON): drop any variant with `n_completed < expected_n × 0.8` OR `crashed% > 5%`. Print `EXCLUDED FOR DATA QUALITY: <name>: n=X expected=Y crashed%=Z` for each.
2. Aggregate per-variant (cap, die, food, n) from each CSV.
3. Compute Wilson 95% CI on cap% and die% via `composite.wilson_ci_95`.
4. Reject any variant with `die%_upper_wilson > die_ceiling` (MJ-4 default 2.5).
5. Compute composite via `composite.compute_score`.
6. Sort descending. Take top-N + buffer + force-includes.
7. **Conditional stratification** (MJ-4): for each angle prefix, only force-include the angle's best variant IF that best clears `die_ceiling` AND its composite is within `stratify_tolerance_pp` (default 5.0) of #top-N composite. Else angle gets no forced slot. Print `STRATIFY SKIPPED for angle <name>: best=<v> Δ=<x>pp > tol` when skipped.
8. Print ranking table with rank, score, cap%, cap%_ci, die%, die%_ci, n, promoted_flag, reason.
9. Print final selected list (and exclusion list) before writing `--out`.

**(d) New file: `experiments/rc_tempo/analyze_pm32.py`** (~180 lines, SKELETON):

CLI:
```
--t1-dir <path>            # optional
--t2-dir <path>            # required
--f3-dir <path>            # optional; HTH outputs (from hth_sweep.py via hth_resumable.py)
--baseline <name>          # default beta_path4
--out-md <path>            # markdown report
--dry-run
```

Logic:
1. Load all CSVs from each directory; aggregate by variant.
2. Compute composite + Wilson CIs via `composite.compute_score` and `composite.wilson_ci_95`.
3. Sort by composite (NEVER by WR — per MINOR #15). WR shown as advisory column with footnote.
4. If `--f3-dir` given: load HTH CSVs (`hth_resumable.py` schema: `agent_a, opp, layout, color, seed, game_idx, winner, red_win, blue_win, tie, score, crashed, wall_sec`), aggregate per-agent HTH WR (= sum(red_win|blue_win matching agent's color) / n) and compute:
   - **Pearson r with 95% CI** via `composite.pearson_with_ci(composite_xs, hth_wr_ys)`.
   - **Spearman ρ** via `composite.spearman_rho(...)` (MJ-3 cross-check).
   - **Disagreement flag** if `|r - ρ| > 0.2`.
5. Emit ASCII Pareto plot (cap% vs die%) + ranking table + per-opponent breakdown.
6. Emit markdown to `--out-md` with:
   - Headline composite ranking.
   - WR advisory column with footnote "WR is partial-game score at cutoff per pm31 lesson; use F3 HTH for game-outcome metric."
   - F3 correlation BLOCK with: Pearson r, Pearson 95% CI, Spearman ρ, agreement flag.
   - **Recommendation**: SHIP iff `(r ≥ 0.7) AND (r_ci_lower > 0.3) AND (ρ ≥ 0.7) AND (|r - ρ| ≤ 0.2)`; PROVISIONAL if r ≥ 0.7 but CI loose, or 0.5 ≤ r < 0.7, or rank-disagreement; UNUSABLE if r < 0.5.

**(e) New file: `experiments/rc_tempo/filter_random_layouts.py`** (~50 lines):

CLI:
```
--seed-pool <list of ints>     # e.g., 1001 1002 ... 1030
--target-count <int>           # min valid 1-cap layouts to return; default 12
--min-pool-size <int>          # default 30 (auto-expand if needed)
--out <txt path>               # newline-delimited layout names like RANDOM1003
```

Logic: for each candidate seed, instantiate via `getLayout('RANDOM<seed>')`, count capsules, accept iff total caps == 2 (1 per side). If fewer than `--target-count` survive, expand pool by 10 (warn operator).

**(f) New file: `experiments/rc_tempo/fixtures/pm31_s5_stub.csv`**:
~30 hand-curated rows mimicking pm31 S5 schema (`phase1_smoke.FIELDS`), with values for `beta_v2d`, `beta_path4`, `beta_retro` chosen to produce the known pm31 ranking under the composite formula. Used by T-U4, T-D1, T-D2.

**Verification**:
- `python experiments/rc_tempo/v3a_sweep.py --help` shows new flags.
- `python experiments/rc_tempo/v3a_sweep.py --validate-csv --out-dir /tmp/empty/` exits cleanly on empty dir.
- `python experiments/rc_tempo/promote_t1_to_t2.py --t1-dir experiments/rc_tempo/fixtures/ --dry-run` produces ranking table (T-D1).
- `python experiments/rc_tempo/analyze_pm32.py --t2-dir experiments/rc_tempo/fixtures/ --dry-run` produces markdown skeleton (T-D2).
- `python experiments/rc_tempo/filter_random_layouts.py --seed-pool 1001 1002 1003 1004 1005 --target-count 3` runs.
- T-U4 passes against the stub.

**Rollback**: `git checkout` plus `git rm` for new files.

**Acceptance**: all 5 verification commands run; T-D1 + T-D2 + T-U4 pass; T-O3 `--validate-csv` operates on at least one existing CSV.

**Time**: 60min (was 40min in v1; +20min for skeletons + composite module + filter + fixture stub).

---

### Step C.2 — CLI surface verification gate (NEW per CRITICAL #3)

**Action**: 2-minute manual gate before Step D.

**Command**:
```bash
.venv/bin/python experiments/rc_tempo/v3a_sweep.py --help \
    | grep -E -- '--(variants-file|layouts-file|validate-csv|allow-truncate)' | wc -l
```

**Acceptance**: output is `4` (all four flags present in `--help`). If `< 4`, halt and patch `v3a_sweep.py` argparse setup before proceeding to Step D.

**Time**: 2min.

---

### Step D — Mac smoke (~15min wall on Mac at workers=6)

**Command**:
```bash
.venv/bin/python experiments/rc_tempo/v3a_sweep.py \
    --variants-file experiments/rc_tempo/pm32_smoke_variants.txt \
    --games-per-cell 5 --workers 6 --max-moves 200 \
    --opponents baseline zoo_reflex_rc82 zoo_reflex_rc166 monster_rule_expert \
    --layouts defaultCapture distantCapture \
    --colors red blue \
    --out-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_macsmoke/
```

**`pm32_smoke_variants.txt`** (12 lines, ALL drawn from revised Step A enumerated set per MAJOR #5):
```
beta_v2d
beta_path4
beta_retro
pm32_p1_a3_s2_p4
pm32_p1_a3_s3_p4
pm32_aa_none_d10
pm32_aa_any_d10
pm32_aa_one_d8
pm32_ac_retreat
pm32_ac_retreat_path4
pm32_rs_retro_path4
pm32_rs_retro_retreat
```

**Expected wall**: 12 × 4 × 2 × 2 × 5 = 960 games × ~1.3s avg on Mac / 6 workers ≈ 3-4min compute + ~10min orchestrator overhead → ~15min total.

**Acceptance**:
- T-I1: every variant CSV exists; `crashed=0` for all rows.
- T-I2: `beta_v2d` cap%/die% within Wilson CI of pm31 reference.
- T-O1: `heartbeat.log` written and updates every 60s.
- Manual: visual inspection of summary table makes sense (no variant at cap=0% or 100%).
- **TIGHTENED (MJ-8)**: `pm32_aa_none_d999` and `beta_v2d` produce **byte-identical CSV rows** after sorting by `(opp, layout, color, seed, game_idx)`, modulo `wall_sec`. Verify via:
  ```bash
  diff <(sort -t, -k2,2 -k3,3 -k4,4 -k5,5n -k6,6n \
          experiments/artifacts/rc_tempo/v3_sweep_pm32_macsmoke/pm32_aa_none_d999.csv \
          | cut -d, -f1-22) \
       <(sort -t, -k2,2 -k3,3 -k4,4 -k5,5n -k6,6n \
          experiments/artifacts/rc_tempo/v3_sweep_pm32_macsmoke/beta_v2d.csv \
          | cut -d, -f1-22)
  ```
  Expected: zero output lines (all metric columns identical because seeds are deterministic and the new code path with `BETA_TRIGGER_GATE='none'` + `BETA_TRIGGER_MAX_DIST=999` must traverse exactly the original control flow). If non-zero, `BETA_TRIGGER_GATE='none'` default has a behavior-altering bug — halt.

**If FAIL**: do not proceed to Step E.

**Time**: 30min including post-run diagnosis budget.

---

### Step E.0 — REQUIRED prerequisite: pm31 S5 fixture present locally (NEW per MJ-6)

**Action**: before proceeding to Step E, operator MUST verify `experiments/rc_tempo/fixtures/pm31_s5_subset.csv` exists locally. If absent:

```bash
# scp from server (idempotent, ~50KB)
scp jdl_wsl:~/work/coding3/experiments/artifacts/rc_tempo/v3_sweep_pm31_s5/beta_v2d.csv \
    experiments/rc_tempo/fixtures/pm31_s5_subset.csv
# Or if pm31 S5 fixture lives at a different server path, locate via:
ssh jdl_wsl "find ~/work/coding3 -name 'beta_v2d.csv' -path '*pm31*' 2>/dev/null | head -3"
```

If the file truly does not exist on the server (i.e., pm31 S5 was on Mac and no longer accessible), HALT with operator message: "pm31 S5 fixture missing — cannot validate composite-formula reproducibility against real data. Re-run pm31 S5 partial reproduction OR document this as a known unmeasured risk in pm32 ADR before proceeding."

**Acceptance**: file exists with > 100 rows AND `csv.DictReader` succeeds.

**Time**: 5min (network) or HALT.

---

### Step E — git push + server pull + server smoke + parity diff

**Pre-push checklist**:
- `git status` shows only intended files.
- `experiments/artifacts/rc_tempo/v3_sweep_pm32_macsmoke/` is gitignored — do NOT commit.
- `experiments/rc_tempo/fixtures/pm31_s5_subset.csv` is committed (small enough; required for T-D1 / T-D2 reproducibility).

**Commands**:
```bash
git add experiments/rc_tempo/v3a_sweep.py \
    experiments/rc_tempo/composite.py \
    experiments/rc_tempo/promote_t1_to_t2.py \
    experiments/rc_tempo/analyze_pm32.py \
    experiments/rc_tempo/filter_random_layouts.py \
    experiments/rc_tempo/fixtures/pm31_s5_stub.csv \
    experiments/rc_tempo/pm32_smoke_variants.txt \
    experiments/rc_tempo/test_env_parsing.py \
    minicontest/zoo_reflex_rc_tempo_beta.py \
    docs/AI_USAGE.md \
    .omc/plans/pm32-sweep-plan.md \
    .omc/plans/open-questions.md
git commit -m "pm32 S1: β trigger gate + retreat + sweep resumability + skeletons"
git push origin main

ssh jdl_wsl
cd ~/work/coding3
git pull origin main

# Server smoke: same command as Mac smoke
tmux new -s work
tmux rename-window smoke
.venv/bin/python experiments/rc_tempo/v3a_sweep.py \
    --variants-file experiments/rc_tempo/pm32_smoke_variants.txt \
    --games-per-cell 5 --workers 8 --max-moves 200 \
    --opponents baseline zoo_reflex_rc82 zoo_reflex_rc166 monster_rule_expert \
    --layouts defaultCapture distantCapture \
    --colors red blue \
    --out-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_serversmoke/
```

(Server smoke uses workers=8, not 24, to validate environment parity at low concurrency before stressing the box at T1.)

**T-E1 parity diff** on Mac:
```bash
scp -r jdl_wsl:~/work/coding3/experiments/artifacts/rc_tempo/v3_sweep_pm32_serversmoke /tmp/server_smoke
diff <(sort /tmp/server_smoke/beta_v2d.csv) \
     <(sort experiments/artifacts/rc_tempo/v3_sweep_pm32_macsmoke/beta_v2d.csv) \
     | head -50
```

**Acceptance**: outcome columns identical, ≤5% wall_sec deviation. If deviation, halt — debug environment parity (numpy version, distancer, RNG handling).

**REQUIRED T-U2 fixture cross-check (per MAJOR #9 v2 + MJ-6 v3 — now hard precondition not optional)**:
```bash
# On server — if pm31 S5 dir present:
.venv/bin/python experiments/rc_tempo/promote_t1_to_t2.py \
    --t1-dir experiments/artifacts/rc_tempo/v3_sweep_pm31_s5/ \
    --top-n 8 --dry-run

# OR, on Mac, against the committed subset fixture:
.venv/bin/python experiments/rc_tempo/promote_t1_to_t2.py \
    --t1-dir experiments/rc_tempo/fixtures/ \
    --top-n 8 --dry-run
```
**Acceptance**: `beta_path4` is ranked above `beta_v2d` in the printed ranking table. If not, halt — composite formula or aggregation has regressed since pm31.

**Time**: 20min wall (commit + push + pull + smoke + parity diff + fixture check).

---

### Step E.1 — Server smoke at workers=24 + monster_rule_expert pre-check (NEW per CR-2)

**Purpose**: Step E ran at `--workers 8` for parity. T1 will run at `--workers 24`. SMT contention behavior at workers=24 is untested. Step E.1 validates 24-worker behavior on the same matrix BEFORE committing 1.8h to T1.

**Command** (in server tmux window `smoke`):
```bash
.venv/bin/python experiments/rc_tempo/v3a_sweep.py \
    --variants-file experiments/rc_tempo/pm32_smoke_variants.txt \
    --games-per-cell 5 --workers 24 --max-moves 200 \
    --opponents baseline zoo_reflex_rc82 zoo_reflex_rc166 monster_rule_expert \
    --layouts defaultCapture distantCapture \
    --colors red blue \
    --out-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_serversmoke24/
```

(Same matrix as Step E; only `--workers` changed from 8 to 24. Resumable per-cell, so this re-runs only if the output dir is empty.)

**Acceptance** (all four hold; halt if any fail):
1. **Median wall ≤ 1.2 s/game** — from `wall_summary.csv`. If exceeded, SMT contention is degrading per-game performance > 20% — drop T1 to `--workers 16` (saves SMT pairing).
2. **Max wall ≤ 5 s/game** — no individual game exceeds 5s. (Indicates a rogue game, not contention.)
3. **Zero forfeits / no >1s turn-warning chain forfeits** — check `crashed=0` AND no `outcome=='timeout'` rows from a forfeit (vs an honest 200-move cap).
4. **`monster_rule_expert` mean wall ≤ 2× rest-of-opponents median** — compute per-opp wall mean from rows where `crashed=0`. If monster mean > 2× the median of {baseline, rc82, rc166}, drop T1 to `--workers 16`.

**Wall budget**: 5min execution + 5min for `wall_summary.csv` inspection + decision = **10min total**.

**Output to operator**:
- One-line summary printed by orchestrator at end: `[E.1] median=X.Xs max=X.Xs forfeits=N monster_ratio=X.X — PASS/FAIL on each gate`.

**Time**: 10min.

---

### Step F1 — Server T1 (broad sweep, ~1.8h at workers=24)

**Layout pre-flight** (per MINOR #18 — operator-visible yield):
```bash
.venv/bin/python experiments/rc_tempo/filter_random_layouts.py \
    --seed-pool $(seq 1001 1020) \
    --target-count 12 \
    --out experiments/rc_tempo/pm32_t1_layouts.txt
# Operator sees: "Found N valid 1-cap layouts. Threshold met / expanding pool."
```

If yield < 12 even at pool 1001-1030, expand to 1001-1050 (operator decision based on output).

**Variant list**:
```bash
.venv/bin/python -c "from experiments.rc_tempo.v3a_sweep import VARIANTS; print('\n'.join(VARIANTS.keys()))" \
    > experiments/rc_tempo/pm32_t1_variants.txt
# Verify count == 70
wc -l experiments/rc_tempo/pm32_t1_variants.txt
```

**T1 command** (in tmux window `t1` of session `work`):
```bash
.venv/bin/python experiments/rc_tempo/v3a_sweep.py \
    --variants-file experiments/rc_tempo/pm32_t1_variants.txt \
    --layouts-file experiments/rc_tempo/pm32_t1_layouts.txt \
    --games-per-cell 5 --workers 24 --max-moves 200 \
    --opponents baseline zoo_reflex_h1test zoo_reflex_h1c zoo_distill_rc22 \
                zoo_reflex_rc02 zoo_reflex_rc16 zoo_reflex_rc32 zoo_reflex_rc47 \
                zoo_reflex_rc82 zoo_reflex_rc166 monster_rule_expert \
    --colors red blue \
    --out-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_t1/
```

**Wall estimate (revised at workers=24)**:
- Per-variant: 11 opp × ~16 layouts (4 fixed + 12 RANDOM) × 2 colors × 5g = 1,760 games.
- Per-variant wall @ 24 workers × 1.0s avg per game = 1,760 / 24 = ~73s.
- Total T1 wall: 70 × 73s = 5,110s ≈ **1.4h**. Add 20% slack for CI overhead, monster_rule_expert latency tail → **~1.8h budget**.

**Monitor pane**:
```bash
tail -F experiments/artifacts/rc_tempo/v3_sweep_pm32_t1/heartbeat.log
```

**Acceptance**:
- All 70 variants completed; `wall_summary.csv` has 70 rows.
- T1 summary table printed; top 20 identified by composite (NEVER WR).
- `crashed%` per variant ≤ 5%.
- Total wall < 2.5h (else operator inspects for runaway variant or reduces workers).

**If FAIL** (orchestrator dies):
- Inspect last heartbeat line.
- Re-run same command — resumability skips done.
- If specific variant consistently crashing, drop from variants file and continue.

**Time**: 1.8h.

---

### Step F1 → F2 transition: operator-explicit T2 candidate selection (per MAJOR #10)

After T1 finishes (heartbeat log shows "all variants done"), operator runs:

```bash
# Inspect TOTAL T1 wall (sum across all variants) to decide --top-n. With 32-core budget, > 3h is unlikely.
# WARNING (Critic-W iter-3): wall_summary.csv has one row per variant — do NOT use `tail -1` (gives last variant's wall only)
awk -F, 'NR>1 {sum+=$2} END {printf "T1 total wall: %.2fh (%d variants)\n", sum/3600, NR-1}' \
    experiments/artifacts/rc_tempo/v3_sweep_pm32_t1/wall_summary.csv

# Generate T2 candidate list with promotion logic
.venv/bin/python experiments/rc_tempo/promote_t1_to_t2.py \
    --t1-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_t1/ \
    --top-n 12 \
    --buffer-pp 2.0 \
    --die-ceiling 2.5 \
    --force-include beta_v2d beta_path4 beta_slack3 beta_retro \
    --stratify-angles \
    --out experiments/rc_tempo/pm32_t2_variants.txt
```

**Operator decision gate** (printed by `promote_t1_to_t2.py`):
> "Total T1 wall = X.Xh. Budget recommendation: --top-n 12 (default) if wall < 3h; --top-n 8 if wall ≥ 3h. Press Enter to accept default; or re-run with explicit --top-n."

**Math justification** (with 32-core budget, top-n=12 is safe):
- T2 wall: 12 × 6 (5g→30g) × 1,760 games × 1s / 24 workers = ~88min ≈ 1.5h. Plus 20% slack → 1.8h. Comfortable inside the remaining budget after T1.

**Time**: 10min (operator inspection + script run).

---

### Step F2 — Server T2 (deep verify, ~1.8h)

**Command** (tmux window `t2`):
```bash
.venv/bin/python experiments/rc_tempo/v3a_sweep.py \
    --variants-file experiments/rc_tempo/pm32_t2_variants.txt \
    --layouts-file experiments/rc_tempo/pm32_t1_layouts.txt \
    --games-per-cell 30 --workers 24 --max-moves 200 \
    --opponents baseline zoo_reflex_h1test zoo_reflex_h1c zoo_distill_rc22 \
                zoo_reflex_rc02 zoo_reflex_rc16 zoo_reflex_rc32 zoo_reflex_rc47 \
                zoo_reflex_rc82 zoo_reflex_rc166 monster_rule_expert \
    --colors red blue \
    --out-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_t2/
```

**Wall**: 12 × 6 × 73s = 5,256s ≈ **1.5h** + 20% slack → **~1.8h budget**.

**Acceptance** (CRITICAL — formalized per MAJOR #14):

A "winner" exists IFF:
- ∃ variant `v` with `cap%_lower_wilson_95(v) > cap%_upper_wilson_95(beta_path4)` AND
- `die%_upper_wilson_95(v) ≤ 2.5`.

If multiple `v` qualify, the winner is the one with highest composite.

If NO `v` qualifies, the verdict is: "no winner detected; recommend STAY at beta_path4 baseline." This is a valid pm32 outcome and is reported as such in §6.G.

**Time**: 1.8h.

---

### Step F3 — Full-game 1200-move HTH calibration via `hth_sweep.py` wrapping existing `hth_resumable.py` (REVISED per CR-1)

**Purpose**: directly measure correlation between Phase 1 composite (the metric we optimized) and full-game WR (the metric that ultimately matters). Mitigates pre-mortem Scenario 4.

**Candidate list**: T2 winner(s) + 4 reference variants. Capped at 12 to keep wall in budget.

**Layout subset**: 4 fixed only (`defaultCapture`, `distantCapture`, `strategicCapture`, `testCapture`). Skip RANDOM seeds — full-game RANDOM noise + 30g is too expensive and pm30 HTH baseline used fixed layouts only (so we keep the comparison apples-to-apples).

**Opponent subset**: 6 opponents (baseline, zoo_reflex_rc82, zoo_reflex_rc166, zoo_reflex_rc32, monster_rule_expert, zoo_distill_rc22).

**Implementation (REVISED CR-1)**: REUSE the existing `experiments/rc_tempo/hth_resumable.py` — verified contract:
- argparse at lines 134-144 (`--agent`, `--opponents`, `--layouts`, `--games-per-cell`, `--colors`, `--workers`, `--master-seed`, `--out`, `--metrics-out`)
- `FIELDS` at lines 38-40: `[agent_a, opp, layout, color, seed, game_idx, winner, red_win, blue_win, tie, score, crashed, wall_sec]`
- per-cell resume key at lines 65-66: `(opp, layout, color, seed, game_idx)`
- atomic CSV writes at lines 80-86: `f.flush(); os.fsync(f.fileno())`
- `wilson_95` at line 47 with `z=1.96` (matches our `composite.py`)
- subprocess `run_match` from `experiments/run_match.py:35` with `timeout_s=120`
- `ProcessPoolExecutor` parallelism

Build only the thin orchestrator `experiments/rc_tempo/hth_sweep.py` (~50 lines), analogous to `v3a_sweep.py:run_variant` (lines 100-123): loops over variants from `--variants-file`, for each variant calls `hth_resumable.py` via subprocess passing the appropriate env-var dict (re-using the `__BETA__` / `__RETRO__` / `__BETA_AGENT__` markers from `v3a_sweep.py:VARIANTS`), aggregates per-variant CSVs into `<out_dir>/<variant>.csv`. Eliminates v2 plan's "build new ~100-line `hth_runner.py`" — saves ~30-50min Mac coding and removes the v2 open-question "untested critical-path code" entirely.

**`hth_sweep.py` CLI** (mirrors `v3a_sweep.py` shape):
```
--variants-file <txt>          # one variant name per line, drawn from VARIANTS
--opponents <list>             # passed through to hth_resumable.py
--layouts <list>               # passed through (NO --layouts-file for F3 — fixed layouts only)
--colors <list>                # default red blue
--games-per-cell <int>         # default 30
--workers <int>                # default 24
--out-dir <path>               # one CSV per variant inside
```

**Command** (tmux window `f3`):
```bash
.venv/bin/python experiments/rc_tempo/hth_sweep.py \
    --variants-file experiments/rc_tempo/pm32_t2_variants.txt \
    --opponents baseline zoo_reflex_rc82 zoo_reflex_rc166 zoo_reflex_rc32 \
                monster_rule_expert zoo_distill_rc22 \
    --layouts defaultCapture distantCapture strategicCapture testCapture \
    --colors red blue \
    --games-per-cell 30 --workers 24 \
    --out-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_hth/
```

**Wall estimate**:
- Cells: 12 var × 6 opp × 4 lay × 2 col × 30g = 17,280 games.
- Per-game: full 1200-move HTH ≈ 4-6 s on server (pm30 measured ~5s).
- Total: 17,280 × 5s / 24 workers = 3,600s ≈ **1.0h**. Plus 20% slack → **~1.2h budget**.
- **Open-question caveat (carried over)**: pm30 measurement used a smaller opponent set; if F3 opponents (esp. monster_rule_expert + rc47 + rc166) average 7s per game instead of 5s, F3 grows to ~1.4h. Mitigation: drop candidate set from 12 → 8 if T2 already consumed > 2.5h.

**Output**:
- Per-variant HTH WR aggregated by `analyze_pm32.py --f3-dir`.
- Reports: Pearson r with 95% CI (Fisher z), Spearman ρ, agreement flag.

**Decision rule** (per Scenario 4 + MJ-3, inlined here for self-contained reading):
- **SHIP**: Pearson `r ≥ 0.7` AND `r_95_ci_lower > 0.3` AND Spearman `ρ ≥ 0.7` AND `|r - ρ| ≤ 0.2`. → flatten pm32 winner in pm33.
- **PROVISIONAL**: any of (`r ≥ 0.7 BUT r_ci_lower ≤ 0.3`), (`0.5 ≤ r < 0.7`), (`|r - ρ| > 0.2`). → pm33 deeper HTH (200+ g/cell on top 3) before flatten.
- **UNUSABLE**: Pearson `r < 0.5`. → stay at `beta_path4`; pm33 must redesign metric.

**Time**: 1.0-1.2h (1.4h tail risk acknowledged).

---

### Step G — Analysis + ADR finalization (~30min, on Mac while server idle or done)

After F3 finishes:
- `scp` server CSVs back under `experiments/artifacts/rc_tempo/v3_sweep_pm32_{t1,t2,hth}/`.
- Run analysis:
```bash
.venv/bin/python experiments/rc_tempo/analyze_pm32.py \
    --t1-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_t1/ \
    --t2-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_t2/ \
    --f3-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_hth/ \
    --baseline beta_path4 \
    --out-md .omc/wiki/2026-04-21-pm32-sweep-results.md
```
- Update §9 ADR with final decision + r value + recommendation.
- Update `STRATEGY.md` if a new winner ships.
- Append session-log entry to `.omc/wiki/`.
- Update `STATUS.md` and `SESSION_RESUME.md` for pm33 handoff.

**Time**: 30min.

---

## 7. Resumability Design (consolidated)

| Failure | Recovery | Data loss |
|---|---|---|
| Orchestrator killed (kill -9, panic) | Re-run same command | 0 — `phase1_smoke.py:load_completed` skips done; in-flight 1-24 games lost. |
| One variant crashes the orchestrator | Re-run; per-variant try/except prevents propagation | 0 |
| SSH session drops | `tmux a -t work` from new SSH | 0 |
| Server reboots | Re-run on boot; resumability skips done | 0-24 games (in-flight). |
| Disk full | Pre-check refuses start; if it fills mid-run, archive and resume | 0 if archive on different FS. |
| CSV mid-row corruption | `--validate-csv --allow-truncate` drops trailing partial row, writes `.bak`, refuses to drop `crashed=1` rows | 1 row max (the trailing partial). |
| CSV column-set drift | `--validate-csv` exits non-zero, fatal, no auto-fix | 0; operator inspects and decides. |
| Variant produces no rows | `wall_summary.csv` shows games_completed=0 — operator notices | 0; re-run that variant. |
| Variant CSV unrecoverable | `rm <var>.csv && python v3a_sweep.py --variants <name>` | All games for that variant. |
| Mac smoke disagrees with server | Halt at Step E; debug parity before T1 | N/A |
| F3 r < 0.5 | Per Scenario 4 decision rule | N/A |

**Key invariants**:
- Per-cell granularity for resume — `(agent, opp, layout, color, seed, game_idx)` is unique.
- Per-variant CSVs are independent files.
- All output paths under `experiments/artifacts/rc_tempo/v3_sweep_pm32_*/` (gitignored, on server home FS).
- `--validate-csv` is idempotent and never destructive without `--allow-truncate`.

---

## 8. Time Budget Breakdown (32-core revised, v3 with F3-via-`hth_sweep` and Step E.0/E.1 inserted)

| # | Phase | Activity | Wall | Cumulative | Where |
|---|---|---|---|---|---|
| 1 | A | v3a_sweep.py: 40 NEW VARIANTS entries | 30m | 0:30 | Mac |
| 2 | B | β agent: BETA_TRIGGER_GATE + BETA_TRIGGER_MAX_DIST + header doc + unit tests | 30m | 1:00 | Mac |
| 3 | C | β agent: my_home_cells plumbing + RCTEMPO_TEAM.reset gate + _maybe_retreat + T-U3 (now 2-game-different-layouts variant) | 45m | 1:45 | Mac |
| 4 | C.1 | composite.py (compute_score + wilson_ci_95@z=1.96 + pearson_with_ci + spearman_rho) + promote SKELETON (defaults locked) + analyze SKELETON (Spearman + agreement flag) + filter_random + fixture stub + **hth_sweep.py thin wrapper (~50 lines, REUSES hth_resumable.py)** | 50m | 2:35 | Mac |
| 5 | C.2 | CLI surface verification gate (manual `--help` check) | 2m | 2:37 | Mac |
| 6 | D | Mac smoke (12 var × 4 opp × 2 lay × 2 col × 5g, workers=6); **MJ-8 byte-identical diff** for `pm32_aa_none_d999 ≡ beta_v2d` | 30m | 3:07 | Mac |
| 7 | E.0 | **NEW (MJ-6)** scp pm31 S5 fixture subset locally; halt-check it exists | 5m | 3:12 | Mac |
| 8 | E | git push + server pull + server smoke (workers=8) + parity diff + **REQUIRED fixture cross-check** | 20m | 3:32 | Mac+Server |
| 9 | E.1 | **NEW (CR-2)** Server smoke at workers=24 + monster_rule_expert wall pre-check | 10m | 3:42 | Server |
| 10 | F1 | Server T1 (70 var × 11 opp × ~16 lay × 2 col × 5g, workers=24) | 1.8h | 5:30 | Server |
| 11 | F1→F2 | Operator inspects wall_summary.csv + reviews `--data-quality-check` exclusions + runs promote_t1_to_t2.py | 10m | 5:40 | Server (operator) |
| 12 | F2 | Server T2 (12 var × same matrix × 30g, workers=24) | 1.8h | 7:28 | Server |
| 13 | F3 | Server HTH via `hth_sweep.py` → `hth_resumable.py` (12 var × 6 opp × 4 lay × 2 col × 30g, full game 1200 moves, workers=24) | 1.0-1.2h | 8:28-8:40 | Server |
| 14 | G | Analysis + writeup + STATUS update | 30m | 8:58-9:10 | Mac |

**Workers cap (per user direction)**: chosen value is `--workers 24`, which is the explicit cap (≤ 25 ceiling). NOT 32 (full SMT) — 8 logical cores reserved for OS + headroom + monster_rule_expert tail latency. Step E.1 validates this empirically before T1.

**Server-only wall** (rows 8+9+10+11+12+13): 0:20 + 0:10 + 1:48 + 0:10 + 1:48 + 1:12 = **5h 28m**, leaves **32min margin** under the 6h server budget.

**Realistic margin (per Architect pessimistic test)**: with workers=24 + SMT contention + monster_rule_expert tail, the realistic margin is **7-30min**, NOT the naïve 32min above. Reasons:
- F3 per-game wall could grow from 5s → 7s on the heavier opponent set (+24min on F3 alone).
- T1's last 1-2 variants tend to bunch in the slowest cell (monster × distantCapture); +5-10min tail.
- Mac↔server `scp` if needed mid-run: +5min.

This means there is **little tolerance for a full T2 re-run**. If T2 produces ambiguous results that warrant a re-run, defer to pm33 rather than retry inside pm32. Operator should plan to cut T2 candidates from 12 → 8 if F1 wall > 2.5h (locked rule, MAJOR #10).

**Mac-only wall** (rows 1-7): **3h 12m**. Can overlap with server idle time during pre-pm32 prep.

**Total end-to-end**: ~9h. Independent Mac and Server windows.

**Pre-decided budget cut** (operator-visible, not auto): if F1 wall > 2.5h, operator chooses `--top-n 8` instead of `--top-n 12` for F2 (saves ~30min). With workers=24 and current estimate, this is unlikely to trigger.

**Time delta vs v2** (CR-1 + CR-2 + MJ-6):
- F3 implementation: -10min (replace ~100-line hth_runner with ~50-line hth_sweep)
- C.1 net: -10min (new composite.py functions absorb the F3 savings; still under v2's 60m → now 50m)
- E.0 prereq: +5min
- E.1 server smoke@24: +10min
- T-U3 extended: +5min
- Net: +0min vs v2; same 9h end-to-end.

---

## 9. ADR (Architectural Decision Record)

**Title**: pm32 server sweep — two-tier hyperparameter search + HTH calibration over β capsule-chase

**Decision**: Adopt Option α (two-tier sweep + F3 HTH calibration) over Options β/γ/δ/ε.

**Decision Drivers**:
1. Statistical reliability: T2 with 30 g/cell × 11 opp × ~16 layout × 2 col = ~10,560 games per variant, gives Wilson 95% CI half-width ~1pp on cap% — sufficient to resolve 3pp differences confidently.
2. Wall-time fits 6h server budget at workers=24 (32-core server confirmed): T1 ~1.8h + T2 ~1.8h + F3 ~1.0-1.2h ≈ 4.6-5.0h, with ~1h margin.
3. Risk floor: variants with `die%_upper_wilson > 2.5%` auto-eliminated in T1 → T2 promotion.
4. (NEW) Phase 1 vs HTH metric disconnect (pm31's β v2d cap 52% vs WR 75.65%) is the headline known risk; F3 directly measures and reports the correlation, allowing principled flatten decision.

**Alternatives Considered**:
- Option β (single-tier deep): cuts variant count 70 → 12, sacrificing exploration breadth. Rejected — with 32-core budget, breadth is nearly free.
- Option γ (three-tier with T0 micro): T0 redundant with Steps D + E. Rejected.
- Option δ (single-tier wide-and-shallow): 8 g/cell statistically insufficient. Rejected.
- Option ε (two-tier WITHOUT F3): leaves Scenario 4 (wrong-metric optimization) unmitigated, repeats pm31 disconnect. Rejected.

**Why Chosen**:
- T1 explores all 4 angles broadly; T2 confirms with publication-grade N; F3 calibrates the metric we optimized against the metric we ultimately ship.
- Reuses `phase1_smoke.py` infrastructure for T1+T2 AND **reuses `hth_resumable.py` for F3** (tested code on critical path); only NEW orchestration code is the thin `hth_sweep.py` (~50 lines). Minimal new bugs.
- Resumable at row, variant, tier granularity; bounded blast radius from any failure.
- Forced-include of pm31 reference variants in T2 + F3 keeps results interpretable as "vs known baseline".
- 32-core hardware reality removes the wall-pressure that drove v1's variant cuts.
- **Conjunction r-threshold (MJ-3)** prevents shipping a winner whose Phase 1↔HTH correlation is weak even if the point estimate is high (small-N risk).

**Consequences**:
- We commit ~5.5h server time on jdl_wsl (within tmux session `work`). Server unavailable for other compute during this window.
- We produce ~350MB of CSV (T1 ~80MB + T2 ~70MB + HTH ~200MB). Gitignored; on server home FS.
- We will know by end of pm32: (a) whether the 55% cap ceiling is breakable in Phase 1, (b) whether any cap-improvement actually translates to HTH WR. Both are valid outcomes.
- 3 new env vars added to β agent (`BETA_TRIGGER_GATE`, `BETA_TRIGGER_MAX_DIST`, `BETA_RETREAT_ON_ABORT`). Plus `RCTEMPO_TEAM.my_home_cells` storage. Backward compat preserved by defaults.
- 1 new env-var name for `composite.py` `compute_score`; centralizes ranking formula across 3 callers.
- 5 new files committed: `composite.py`, `promote_t1_to_t2.py`, `analyze_pm32.py`, `filter_random_layouts.py`, **`hth_sweep.py` (thin orchestrator wrapping existing `hth_resumable.py`)**, plus `fixtures/pm31_s5_stub.csv`, `fixtures/pm31_s5_subset.csv` (real subset, MJ-6), and 2 text variant/layout lists.

**Follow-ups** (pm33 priorities ordered by F3 outcome — MJ-3 conjunction rule):
1. **If F3 r ≥ 0.7 AND r_95_ci_lower > 0.3 AND ρ ≥ 0.7 AND |r - ρ| ≤ 0.2**: flatten pm32 winner into `your_best.py`. Behavioral-equivalence HTH (50g/cell) post-flatten per Architect's earlier directive.
2. **PROVISIONAL** (any single conjunction member fails but Pearson ≥ 0.5): pm33 deeper HTH (200+ g/cell) on top 3 candidates before flatten.
3. **If Pearson r < 0.5**: pm33 redesign Phase 1 metric (e.g., switch to mid-game cap+food+enemy_pacman_killed composite, or reduce to N=50 full-game WR if compute allows).
4. `docs/AI_USAGE.md` entry for β agent edits (Steps B + C).
5. Update `STRATEGY.md` if winner ships.
6. If pm32 fails to break 55% ceiling AND r ≥ 0.5: pm33 pivots to Angle B (pre-trigger A positioning) or Angle E (B-agent coordination) from pm31 decision queue — these are larger structural changes outside env-var sweeps.

---

## 10. Risks Not Yet Addressed (Open Questions)

These items are out of scope for pm32 but tracked. Will append/update `.omc/plans/open-questions.md`.

(See open-questions.md for the canonical list. Items resolved or carried over from v1 are marked there.)

---

## 11. Files Touched (summary)

| Path | Change | Step |
|---|---|---|
| `experiments/rc_tempo/v3a_sweep.py` | +40 VARIANTS entries; +`--validate-csv`/`--allow-truncate`/`--variants-file`/`--layouts-file` flags; +heartbeat; +disk pre-check; +per-variant try/except; +wall_summary.csv; refactor scoring to call `composite.compute_score` | A, C.1 |
| `minicontest/zoo_reflex_rc_tempo_beta.py` | +`BETA_TRIGGER_GATE`, `BETA_TRIGGER_MAX_DIST` (with `>0` guard), `BETA_RETREAT_ON_ABORT` env vars; +`my_home_cells` team-state plumbing; +`_maybe_retreat` helper; +naming-asymmetry header doc | B, C |
| `minicontest/zoo_reflex_rc_tempo_beta_retro.py` | +naming-asymmetry header doc (no logic change) | C |
| `experiments/rc_tempo/composite.py` | NEW — single source of truth for composite score + Wilson CI | C.1 |
| `experiments/rc_tempo/promote_t1_to_t2.py` | NEW — T1 → T2 promotion with stratification + die ceiling + dry-run | C.1, F1→F2 |
| `experiments/rc_tempo/analyze_pm32.py` | NEW — composite-sorted ranking + Pearson r + markdown emit (REFUSES WR sort) | C.1, G |
| `experiments/rc_tempo/filter_random_layouts.py` | NEW — capsule-count filter on RANDOM<seed> layouts with auto-expand | C.1, F1 |
| `experiments/rc_tempo/hth_sweep.py` | NEW (~50 lines) — thin orchestrator wrapping existing `hth_resumable.py`. Loops over T2 winners + 4 refs and subprocess-calls `hth_resumable.py` per variant with the right env-var dict. NO new I/O code (reuses tested fsync/resume from `hth_resumable.py`). | F3 |
| `experiments/rc_tempo/test_env_parsing.py` | NEW — unit tests T-U1, T-U3 | B, C |
| `experiments/rc_tempo/fixtures/pm31_s5_stub.csv` | NEW — ~30-row hand-curated fixture for T-U4, T-D1, T-D2 | C.1 |
| `experiments/rc_tempo/fixtures/pm31_s5_subset.csv` | NEW (MJ-6) — REAL pm31 S5 subset scp'd from server, REQUIRED precondition checked at Step E.0 | E.0 |
| `experiments/rc_tempo/pm32_smoke_variants.txt` | NEW — 12 variants for Mac smoke (only enumerated names) | D |
| `experiments/rc_tempo/pm32_t1_variants.txt` | NEW (auto-generated) — 70 variant names | F1 |
| `experiments/rc_tempo/pm32_t1_layouts.txt` | NEW (auto-generated by filter) — 4 fixed + 12+ RANDOM | F1 |
| `experiments/rc_tempo/pm32_t2_variants.txt` | NEW (auto-generated by promote) — 8-12 promoted + force-included | F2 |
| `experiments/artifacts/rc_tempo/v3_sweep_pm32_macsmoke/` | NEW (gitignored) | D |
| `experiments/artifacts/rc_tempo/v3_sweep_pm32_serversmoke/` | NEW (gitignored) | E |
| `experiments/artifacts/rc_tempo/v3_sweep_pm32_t1/` | NEW (gitignored) | F1 |
| `experiments/artifacts/rc_tempo/v3_sweep_pm32_t2/` | NEW (gitignored) | F2 |
| `experiments/artifacts/rc_tempo/v3_sweep_pm32_hth/` | NEW (gitignored) | F3 |
| `docs/AI_USAGE.md` | +1 entry for β agent edits (B + C) | B, C |
| `.omc/plans/pm32-sweep-plan.md` | THIS FILE (revised v2) | (planner) |
| `.omc/plans/open-questions.md` | UPDATE — mark v1 items resolved, add new ones | (planner) |
| `.omc/wiki/2026-04-21-pm32-sweep-results.md` | NEW (Step G) | G |
| `.omc/STATUS.md` | UPDATE — pm32 outcome | G |
| `.omc/SESSION_RESUME.md` | UPDATE — pm33 handoff | G |

---

## 12. Pre-Sweep Final Checklist (operator runs before T1 launch — REVISED v3)

Pre-Mac-smoke:
- [ ] Step C.2 CLI gate passed (4 flags present in `--help`).
- [ ] T-U1 (env parsing), T-U2 (backward compat), T-U3 (retro × retreat AND 2-game-different-layouts no-leak), T-U4 (composite on stub) all pass.

Mac smoke (Step D):
- [ ] All 12 variants, 0 crashes, β v2d reproduces.
- [ ] `pm32_aa_none_d999` BYTE-IDENTICAL to `beta_v2d` after sort (MJ-8 diff returns zero lines).
- [ ] heartbeat.log writes every 60s.

Pre-server (Step E.0 + Step E):
- [ ] **REQUIRED**: `experiments/rc_tempo/fixtures/pm31_s5_subset.csv` exists locally and is committed.
- [ ] git status clean before push; only intended files staged.
- [ ] Server pull successful; `git log -1` on server matches local HEAD.
- [ ] Server smoke (Step E) at workers=8 clean — outcomes match Mac (T-E1).
- [ ] **REQUIRED** fixture cross-check: `promote_t1_to_t2.py --dry-run` against fixtures/ ranks `beta_path4 > beta_v2d`.

Server smoke at workers=24 (Step E.1, NEW CR-2):
- [ ] median wall ≤ 1.2 s/game.
- [ ] max wall ≤ 5 s/game.
- [ ] zero forfeits.
- [ ] monster_rule_expert mean wall ≤ 2× rest-of-opponents median.
- [ ] If ANY of the four fail → drop T1 to `--workers 16`, document in operator log, redo E.1.

Pre-T1 launch:
- [ ] `pm32_t1_variants.txt` regenerated, has 70 variants.
- [ ] `pm32_t1_layouts.txt` exists, has 4 fixed + ≥ 12 valid RANDOM (operator-visible filter yield acknowledged).
- [ ] `experiments/artifacts/rc_tempo/v3_sweep_pm32_t1/` doesn't exist yet (or is empty).
- [ ] tmux session `work` running; windows `t1`, `monitor`, `t2`, `f3` opened.
- [ ] Disk pre-check passed (≥ 1 GiB free).
- [ ] Heartbeat tail running in window `monitor`.
- [ ] T1 command typed but not yet entered — operator verifies args.
- [ ] Press Enter.

After T1 ends:
- [ ] Inspect `wall_summary.csv`.
- [ ] Run `promote_t1_to_t2.py` (defaults locked: `--die-ceiling 2.5`, `--stratify-angles`, `--buffer-pp 2.0`, `--stratify-tolerance-pp 5.0`, `--data-quality-check`).
- [ ] **Review `EXCLUDED FOR DATA QUALITY` lines BEFORE accepting promote output** (MJ-5).
- [ ] Choose `--top-n` per operator gate: default 12; if F1 wall > 2.5h → 8.
- [ ] Launch T2 in window `t2`.

After T2 ends:
- [ ] Re-run `promote_t1_to_t2.py` against T2 dir to confirm winner per formal rule (`cap_lower_wilson > path4_upper_wilson` AND `die_upper_wilson ≤ 2.5`).
- [ ] Launch F3 in window `f3` with T2 winner + 4 refs via `hth_sweep.py`.

After F3 ends:
- [ ] Run `analyze_pm32.py --t1-dir … --t2-dir … --f3-dir …`.
- [ ] Inspect: Pearson r, Pearson 95% CI, Spearman ρ, agreement flag.
- [ ] Apply MJ-3 decision rule: SHIP iff `(r ≥ 0.7) AND (r_ci_lower > 0.3) AND (ρ ≥ 0.7) AND (|r - ρ| ≤ 0.2)`; PROVISIONAL otherwise; UNUSABLE if r < 0.5.
- [ ] Update `STATUS.md`, `SESSION_RESUME.md`, session-log wiki entry.
- [ ] Update §9 ADR with final r/ρ/CI numbers + ship/provisional/unusable verdict.

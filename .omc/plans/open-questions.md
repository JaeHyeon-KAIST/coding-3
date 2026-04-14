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

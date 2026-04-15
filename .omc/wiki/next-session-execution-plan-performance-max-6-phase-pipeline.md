---
title: "Next-session execution plan — performance-max 6-phase pipeline"
tags: ["plan", "next-session", "performance-max", "6-phase", "candidate-roster", "dispatch-policy", "fixed-seed-then-multiseed"]
created: 2026-04-15T21:23:56.407Z
updated: 2026-04-15T21:23:56.407Z
sources: ["pm17 user decision: 시간 여유, 성능 최우선", "pm16 M6-a.1 PASS", "pm14 Option A 4-loop bypass", "wiki environment/remote-compute-infra-..."]
links: []
category: decision
confidence: high
schemaVersion: 1
---

# Next-session execution plan — performance-max 6-phase pipeline

# Next-session execution plan — performance-max 6-phase

**Decision (pm17 end)**: user has time slack, prioritizes ranking max (extra 30pt + code 40pt). Run the full 6-phase plan, NOT the minimal "M6-both-full only" path.

**Experimental design**: fixed `--master-seed=42` for ALL Phase 2 candidates (apples-to-apples ranking). Then Phase 5 multi-seed validation on top-5 to weed out lucky-seed artifacts. This is the standard "develop with fixed seed → validate with seed sweep" ML pattern.

**Dispatch is case-by-case, NOT "always server"**. See dispatch policy below.

---

## Phase 1 — Pre-evolve infrastructure (Mac, ~6-8h coding)

Critical path: every later evolve runs on top of these.

### B1 — Feature engineering (17 → 20 dim)
Add 3 features to `minicontest/zoo_features.py` extractor + `SEED_WEIGHTS_OFFENSIVE/DEFENSIVE` dicts + `experiments/evolve.py FEATURE_NAMES`:

- `f_scaredGhostChase` — when an enemy ghost has scaredTimer > 0, value = 1/dist(myPos, that ghost). Lets evolution learn to chase scared ghosts (they're worth points and can't kill us). Currently no feature captures this.
- `f_returnUrgency` — `numCarrying × distToHome × time_remaining_factor` (non-linear). Stronger pressure to return when carrying lots near game end. Existing `f_distToHome` is linear-ish; this captures the actual scoring decision.
- `f_teammateSpread` — `1 / max(maze_distance(my_pos, teammate_pos), 1)`. Negative weight → agents disperse and don't dogpile. Currently nothing prevents both teammates from clustering on same food.

Also: bump `KNOWN_SEEDS_PHASE_2A` to 20 features (extend each seed dict with 0.0 for new features so existing seeds remain valid baselines).

### C4 — MCTS time calibration
Modify `minicontest/zoo_mcts_heuristic.py` (and `zoo_mcts_random.py`, `zoo_mcts_q_guided.py` if used):
- Replace `for _ in range(MAX_ITERS)` with time-budget polling: `while time.time() - turn_start < move_budget: do_one_iteration()`.
- Default `move_budget = 0.8s` (stays under capture.py's 1s warning threshold).
- This unblocks MCTS as an evolve container — currently always times out under run_match's 120s subprocess wall (M4-v1 pm6 finding).

### Verification before launching Phase 2
- Smoke `evaluate_genome` with 20-dim vector once — confirm shape + non-zero fitness.
- Smoke `zoo_mcts_heuristic` 1 game vs baseline — confirm no timeout, returns within move_budget.

**Commit per task** (B1 separate from C4) so we can roll back individually.

---

## Phase 2 — Candidate evolve queue (server tmux work, ~70-100h sequential, 3-4 days)

All runs use `--master-seed 42`, full STRATEGY §6.3 spec
(`--n-gens-2a 10 --n-gens-2b 20 --pop 40 --workers 16
 --games-per-opponent-2a 24 --games-per-opponent-2b 16
 --opponents <11-pool> --layouts defaultCapture RANDOM`).

| order | candidate | container | init_mean_from | feature dim | est. wall | rationale |
|---|---|---|---|---|---|---|
| 1 | A1 baseline | zoo_reflex_tuned | h1test | 17 (no B1) | ~10h | control — comparable to pm14 v1 spec, validates infra |
| 2 | A1 + B1 | zoo_reflex_tuned | h1test | **20** | ~12h | extended search space |
| 3 | A2 + B1 | zoo_reflex_tuned | h1b | 20 | ~12h | local-optimum diversity |
| 4 | A5 + B1 | zoo_reflex_tuned | hybrid (h1test⊕h1b)/2 | 20 | ~12h | safe + strong compromise |
| 5 | C1 + B1 | zoo_minimax_ab_d2 | h1test | 20 | ~15h | 2-step lookahead paradigm |
| 6 | C4 + B1 | zoo_mcts_heuristic | h1test | 20 | ~17h | MCTS, biggest ceiling unknown |
| 7 | C3 + B1 | zoo_expectimax | h1test | 20 | ~14h | risk-aware paradigm |
| 8 (stretch) | A3 + B1 | zoo_reflex_tuned | h1c | 20 | ~12h | map-specific re-test |

Output per run: `experiments/artifacts/champion_<id>.py` (we'll add a small post-evolve script that renames `final_weights.py` → labeled candidate file).

**Tier policy STILL applies inside Phase 2**: each candidate is independently launchable + resumable. After each finishes, we can bail / pivot.

---

## Phase 3 — Hybrid layer (Mac, ~6-8h coding + smoke)

Apply 3 code-level enhancements ON TOP OF each champion's evolved weights:

- **D1 role-swap rule**: dynamic OFFENSE↔DEFENSE switch on conditions
  (carrying ≥ N → return; ≥ K invaders detected → both DEFENSE; etc.).
- **D2 capsule timing**: only eat capsule when a) ghost dist ≤ 3 AND we're carrying ≥ 5, OR b) opponents have eaten our capsule recently. Avoids wasting capsule on a bored stroll.
- **D3 endgame mode**: last 100 moves, behavior switches based on score lead — leading → hold + defend, behind → all-in food rush ignoring ghost penalty.

For each Phase 2 champion, produce 4 variants:
  - bare (just the evolved weights),
  - +D1, +D2, +D1+D2+D3 combined.

Total: 7-8 champions × 4 ≈ **28-32 candidates** for Phase 4 ELO.

---

## Phase 4 — Round-robin ELO tournament (server, ~2-3h)

All Phase 3 candidates ∪ {baseline, monster_rule_expert, all our existing zoo agents that ran in pm7 M4-v2} → ~35-40 agents.

`tournament.py` with `--workers 16 --layouts defaultCapture RANDOM officeCapture --seeds 1 42 2025 7777 9999`. Permutations × 5 layouts × 5 seeds ≈ 25K-50K matches. At ~1.3s/match × 16 workers ≈ 30-60 min wall.

`compute_elo` produces global ranking. **Top-5 candidates promoted to Phase 5**.

---

## Phase 5 — Multi-seed final validation (server + Mac, ~2-3h)

For top-5: each plays **200 games vs baseline.py** spread across 10 seeds × 4 layouts × 2 colors. Server runs full sweep (~1h). Then Mac re-runs same matches for top-3 (~1-2h, cross-platform reproducibility check).

Verdicts:
- Server win-rate AND Mac win-rate ≥ 51% on at least 3 seed-variants → pass code 40pt.
- Highest minimum win-rate across 10 seeds = our final pick (robust, not lucky).

---

## Phase 6 — Submission (Mac, ~6-8h)

- M7 flatten: implement `select_top4.flatten_agent` AST concatenation. Output: single `20200492.py`.
- M7.5 time calibration on Mac (capture.py's 1s/turn warning) + TA hardware sim (`taskset -c 0 .venv/bin/python ...` if Linux available).
- Populate `your_baseline1/2/3.py` with our top-3 from Phase 4 (currently random DummyAgent — capture.py needs them for output.csv).
- M8 generate `output.csv` (capture.py 4-loop does this automatically when run from minicontest dir).
- M9 LaTeX report (3-5h): Intro 8 + Methods 20 + Results 20 + Conclusion 12. Required figure: ELO curve over generations + per-monster win rate ablation.
- M10 packaging: 20200492.zip = 20200492.{py,pdf,pptx} + sha256 sanity check.

---

## Total budget

- Mac active work: ~25-35h (Phase 1 + 3 + 5 verify + 6)
- Server background: ~75-105h (Phase 2 main + 4 + 5 sweep)
- Calendar: ~5-7 days at relaxed pace, much of it server-overnight.

---

## Dispatch policy (case-by-case, refined pm17)

| situation | venue | reason |
|---|---|---|
| Phase 1 coding (B1, C4) | **Mac** | iteration speed, debugging, no compute heavy |
| Phase 2 candidate evolve (each ≥10h) | **Server** (tmux work) | 2.25× faster, parallel-safe with our gen-level ProcessPool |
| Phase 1 verification smokes (≤10 min) | **Mac** | inline context for analysis |
| Phase 3 hybrid coding | **Mac** | code work, no compute |
| Phase 3 hybrid smokes (each ~3-5 min) | **Mac** | quick iteration |
| Phase 4 tournament (~1h) | **Server** | 16-thread pool, cleanly fits |
| Phase 5 server sweep | **Server** | speed |
| Phase 5 Mac re-validation | **Mac** | cross-platform reproducibility per project doc |
| Phase 6 flatten + report | **Mac** | code + writing, low compute |

NOT every long-wall task goes to server: Phase 5 Mac validation is the explicit counter-example. Always reason from "what compute is needed" + "what context Claude needs to see live".

---

## Fixed-seed-then-multiseed reasoning (record for next session)

Why not run multi-seed from the start?
- Cost: 7 candidates × 5 seeds × 30 gens × 40 pop × 264 games = absurd (~500h server). Useless redundancy in early gens.
- Fixed seed gives apples-to-apples candidate ranking — all on same noise.
- After ranking narrows to top-5, multi-seed eliminates the lucky-seed-42 artifact: a candidate that wins under seed 42 but flops on seeds 1, 100, 9999 is fragile. Robust top-1 is the candidate that's in top-3 across all seeds.

Cross-platform layer adds independent variance signal: server best ≠ Mac best ≠ TA grader best, all with the same seed. Mac re-validation catches any server-specific weights.

---

## What to do FIRST in next session

1. Read `.omc/SESSION_RESUME.md` (5-min onboarding).
2. Read `.omc/STATUS.md` headline + tier rows.
3. Read THIS wiki page (decision/next-session-execution-plan-...).
4. Verify server alive: `ssh jdl_wsl "tmux list-sessions && cd ~/projects/coding-3 && git log --oneline -2"`. Pull if behind.
5. Decision point: launch A1 17-dim (Order 1, control) on server WHILE writing Phase 1 (B1+C4) on Mac. They run in parallel during the same ~10h slot.

(Do NOT launch all of Phase 2 at once — sequential queue per dispatch policy.)


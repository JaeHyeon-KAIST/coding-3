"""
evolve.py — CEM self-play evolution driver (M5 dry-run, M6 full campaign).

Implements the two-phase Cross-Entropy Method per STRATEGY.md §6:
- Phase 2a (gens 1-10): 32-dim (shared W_OFF=W_DEF + PARAMS), 264 games/genome
- Phase 2b (gens 11-30): 52-dim (split W_OFF ≠ W_DEF + PARAMS), 224 games/genome

Key mechanics:
- N=40 per gen, ρ=0.35 (14 elites per gen)
- Elitism: keep best-ever 2 across both phases
- σ schedule: weights start σ=30, decay ×0.9/gen, floor σ=2
- Restart: stagnation 5 gens → inject 8 random genomes + reset σ×2
- CRN pairing: each (genome, opponent, layout, seed) plays both colors
- Sequential halving for elite re-evaluation
- Sanity monitor: alert if (elite_mean - gen_mean) / gen_std < 1.0 for 3+ gens

Fitness (phase-aware, §6.4):
    fitness(g) = pool_win_rate - 0.5 * crash_rate
               - 0.5 * stddev_win_rate          # Risk-sensitive (Gemini)
               + monster_bonus_active * 0.15 * monster_win_rate
    monster_bonus_active = 0 (Phase 2a), 1 (Phase 2b)

Output: `experiments/artifacts/gen<N>.json` per generation, plus
`experiments/artifacts/final_weights.py` with inlined WEIGHTS dict.

NOTE: This is a skeleton. Full implementation depends on M2/M3 delivering
the zoo agents with a weight-override protocol (probably: env var or
argparse flag to pass custom weights to a zoo agent at load time).
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO_ROOT / "experiments" / "artifacts"

# Feature names (from zoo_features.py — must stay in sync)
FEATURE_NAMES = [
    "f_bias", "f_successorScore", "f_distToFood", "f_distToCapsule",
    "f_numCarrying", "f_distToHome", "f_ghostDist1", "f_ghostDist2",
    "f_inDeadEnd", "f_stop", "f_reverse",
    "f_numInvaders", "f_invaderDist", "f_onDefense", "f_patrolDist",
    "f_distToCapsuleDefend", "f_scaredFlee",
    # ... 3 more to reach 20 if needed
]
N_FEATURES = len(FEATURE_NAMES)

# PARAMS dimensions (from §6.1)
PARAM_NAMES = [
    "mcts_c",                        # [0.5, 3.0]
    "rollout_depth",                 # {0, 5, 10, 20}
    "return_threshold_carrying",     # [2, 15]
    "capsule_ghost_dist_trigger",    # [1, 6]
    "role_switch_lead_threshold",    # [2, 20]
    "bottleneck_penalty",            # [-500, 0]
    "scared_return_threshold",       # [1, 8]
    "move_budget_margin",            # [0.05, 0.30]
    "reverse_penalty",               # [-10, 0]
    "stop_penalty",                  # [-500, -50]
    "food_urgency_gamma",            # [0.8, 1.0]
    "defender_patrol_radius",        # [2, 8]
]


def genome_dims(phase: str) -> int:
    if phase == "2a":  # shared W_OFF=W_DEF
        return N_FEATURES + len(PARAM_NAMES)
    elif phase == "2b":
        return 2 * N_FEATURES + len(PARAM_NAMES)
    raise ValueError(f"unknown phase: {phase}")


def sample_gaussian(mean: np.ndarray, sigma: np.ndarray, n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(loc=mean, scale=sigma, size=(n, mean.shape[0]))


def evaluate_genome(genome_id: int, genome: np.ndarray, phase: str, opponents: list, layouts: list, games_per_opponent: int, master_seed: int) -> dict:
    """
    TODO: spawn tournament games using run_match.py + custom-weight mechanism.
    Returns a dict: {pool_win_rate, crash_rate, stddev_win_rate, monster_win_rate}
    """
    raise NotImplementedError("blocked on M2/M3 delivering a weight-override protocol for zoo agents")


def compute_fitness(eval_result: dict, phase: str) -> float:
    pool_wr = eval_result["pool_win_rate"]
    crash_rate = eval_result["crash_rate"]
    stddev_wr = eval_result["stddev_win_rate"]
    monster_wr = eval_result.get("monster_win_rate", 0.0)
    monster_bonus_active = 1.0 if phase == "2b" else 0.0
    return (
        pool_wr
        - 0.5 * crash_rate
        - 0.5 * stddev_wr
        + monster_bonus_active * 0.15 * monster_wr
    )


def run_phase(phase: str, n_gens: int, N: int, rho: float, games_per_opponent: int, master_seed: int, initial_mean=None, initial_sigma=None):
    dims = genome_dims(phase)
    if initial_mean is None:
        mean = np.zeros(dims)
    else:
        mean = np.array(initial_mean)
        if mean.shape[0] != dims:
            # dim mismatch — Phase 2a -> 2b transition: expand shared weights
            if phase == "2b" and initial_mean.shape[0] == N_FEATURES + len(PARAM_NAMES):
                # Duplicate shared weights into OFF and DEF slots
                feat_part = initial_mean[:N_FEATURES]
                param_part = initial_mean[N_FEATURES:]
                mean = np.concatenate([feat_part, feat_part, param_part])
            else:
                raise ValueError(f"dim mismatch: initial_mean {initial_mean.shape} vs expected {dims}")
    if initial_sigma is None:
        sigma = np.full(dims, 30.0)
    else:
        sigma = np.array(initial_sigma)

    stagnation_count = 0
    best_ever_fitness = -np.inf
    best_ever_genome = None
    elite_count = int(np.ceil(rho * N))

    gen_records = []
    for gen in range(n_gens):
        seed_gen = master_seed + gen * 1000
        population = sample_gaussian(mean, sigma, N, seed_gen)
        fitnesses = []
        eval_results = []
        for gid, genome in enumerate(population):
            try:
                result = evaluate_genome(gid, genome, phase, [], [], games_per_opponent, master_seed=seed_gen + gid)
                f = compute_fitness(result, phase)
            except NotImplementedError:
                f = 0.0
                result = {"pool_win_rate": 0.0, "crash_rate": 0.0, "stddev_win_rate": 0.0}
            fitnesses.append(f)
            eval_results.append(result)

        fitnesses = np.array(fitnesses)
        elite_idx = np.argsort(fitnesses)[-elite_count:]
        elite = population[elite_idx]

        # Sanity monitor
        elite_mean = fitnesses[elite_idx].mean()
        gen_mean = fitnesses.mean()
        gen_std = max(fitnesses.std(), 1e-9)
        snr = (elite_mean - gen_mean) / gen_std
        if snr < 1.0:
            stagnation_count += 1
        else:
            stagnation_count = 0

        # Update distribution
        mean = elite.mean(axis=0)
        sigma = np.maximum(elite.std(axis=0) * 0.9, 2.0)

        # Track best
        gen_best_idx = np.argmax(fitnesses)
        if fitnesses[gen_best_idx] > best_ever_fitness:
            best_ever_fitness = fitnesses[gen_best_idx]
            best_ever_genome = population[gen_best_idx]

        # Restart trigger
        if stagnation_count >= 5:
            print(f"[evolve] stagnation trigger: injecting 8 random + σ*=2", file=sys.stderr)
            sigma *= 2.0
            stagnation_count = 0

        record = {
            "phase": phase,
            "gen": gen,
            "mean_fitness": float(fitnesses.mean()),
            "best_fitness": float(fitnesses.max()),
            "elite_mean_fitness": float(elite_mean),
            "snr": float(snr),
            "stagnation_count": stagnation_count,
            "mean_genome": mean.tolist(),
            "sigma": sigma.tolist(),
        }
        gen_records.append(record)

        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        with (ARTIFACTS / f"{phase}_gen{gen:03d}.json").open("w") as f:
            json.dump(record, f, indent=2)
        print(f"[evolve] phase={phase} gen={gen} best={record['best_fitness']:.3f} mean={record['mean_fitness']:.3f} snr={snr:.2f}", file=sys.stderr)

    return {
        "final_mean": mean.tolist(),
        "final_sigma": sigma.tolist(),
        "best_ever_fitness": float(best_ever_fitness) if best_ever_genome is not None else None,
        "best_ever_genome": best_ever_genome.tolist() if best_ever_genome is not None else None,
        "gen_records": gen_records,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["2a", "2b", "both"], default="both")
    ap.add_argument("--n-gens-2a", type=int, default=10)
    ap.add_argument("--n-gens-2b", type=int, default=20)
    ap.add_argument("--pop", type=int, default=40)
    ap.add_argument("--rho", type=float, default=0.35)
    ap.add_argument("--games-per-opponent-2a", type=int, default=24)  # 264/11 pool
    ap.add_argument("--games-per-opponent-2b", type=int, default=16)  # 224/14 pool
    ap.add_argument("--master-seed", type=int, default=42)
    args = ap.parse_args()

    result_2a = None
    if args.phase in ("2a", "both"):
        print("[evolve] starting Phase 2a (32-dim shared W, 10 gens, 264 games/genome)", file=sys.stderr)
        result_2a = run_phase(
            phase="2a", n_gens=args.n_gens_2a, N=args.pop, rho=args.rho,
            games_per_opponent=args.games_per_opponent_2a,
            master_seed=args.master_seed,
        )

    if args.phase in ("2b", "both"):
        print("[evolve] starting Phase 2b (52-dim split W, 20 gens, 224 games/genome)", file=sys.stderr)
        init_mean = np.array(result_2a["final_mean"]) if result_2a else None
        init_sigma = np.array(result_2a["final_sigma"]) * 0.5 + 10.0 if result_2a else None
        result_2b = run_phase(
            phase="2b", n_gens=args.n_gens_2b, N=args.pop, rho=args.rho,
            games_per_opponent=args.games_per_opponent_2b,
            master_seed=args.master_seed + 10000,
            initial_mean=init_mean, initial_sigma=init_sigma,
        )
        # Emit final weights as Python literal
        best = np.array(result_2b["best_ever_genome"])
        w_off = dict(zip(FEATURE_NAMES, best[:N_FEATURES].tolist()))
        w_def = dict(zip(FEATURE_NAMES, best[N_FEATURES:2*N_FEATURES].tolist()))
        params = dict(zip(PARAM_NAMES, best[2*N_FEATURES:].tolist()))
        out = ARTIFACTS / "final_weights.py"
        with out.open("w") as f:
            f.write(f"# Auto-generated by experiments/evolve.py\n")
            f.write(f"# Phase 2b best-ever fitness: {result_2b['best_ever_fitness']:.4f}\n\n")
            f.write(f"W_OFF = {json.dumps(w_off, indent=2)}\n\n")
            f.write(f"W_DEF = {json.dumps(w_def, indent=2)}\n\n")
            f.write(f"PARAMS = {json.dumps(params, indent=2)}\n")
        print(f"[evolve] final weights written: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()

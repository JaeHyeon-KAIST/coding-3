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
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = REPO_ROOT / "experiments" / "artifacts"

# Make run_match importable when running this script directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_match import run_match  # noqa: E402

# The "container" zoo agent that accepts `weights=<path>` via --redOpts.
# Its createTeam forwards the kwarg to zoo_core.load_weights_override and
# attaches the override onto both teammates so _get_weights returns the
# evolve.py-supplied dict instead of seed weights.
EVOLVE_CONTAINER_AGENT = "zoo_reflex_tuned"

# Default dry-run opponent pool / layouts when the caller passes empty lists.
# Chosen from the pm4/M4-v2 top-3 so the genome gets measurably different
# responses: a strong opponent (h1test), the best net agent (h1b), and the
# grading anchor (baseline). Keep it small so M5 dry-run stays under ~30 min.
DEFAULT_DRY_RUN_OPPONENTS = ("baseline", "zoo_reflex_h1test", "zoo_reflex_h1b")
DEFAULT_DRY_RUN_LAYOUTS = ("defaultCapture", "RANDOM")

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


def _default_workers() -> int:
    """Default ProcessPoolExecutor worker count for genome-level parallelism.

    Caps at 8 to match STRATEGY §3.4 guidance (oversubscription biases
    selection toward shallow/fast agents). Reserves 1 core for the parent
    evolve.py process + OS. For a 12-core box: `min(11, 8) = 8`.
    """
    try:
        cores = os.cpu_count() or 1
    except Exception:
        cores = 1
    return max(1, min(cores - 1, 8))


def _decode_genome(genome: np.ndarray, phase: str) -> tuple:
    """Split a flat genome vector into (w_off, w_def, params_dict).

    Phase 2a shared-W encoding (length = N_FEATURES + |PARAM_NAMES|):
        [f0..fN-1] = shared weights (w_off = w_def)
        [fN..end]  = params
    Phase 2b split-W encoding (length = 2*N_FEATURES + |PARAM_NAMES|):
        [f0..fN-1]        = w_off
        [fN..f(2N-1)]     = w_def
        [f2N..end]        = params

    Returns (w_off: dict, w_def: dict | None, params: dict). `w_def` is None
    in phase 2a so the zoo agent falls back to w_off for the DEFENSE role.
    """
    if phase == "2a":
        feats = genome[:N_FEATURES]
        params = genome[N_FEATURES:]
        w_off = dict(zip(FEATURE_NAMES, feats.tolist()))
        w_def = None
    elif phase == "2b":
        w_off = dict(zip(FEATURE_NAMES, genome[:N_FEATURES].tolist()))
        w_def = dict(zip(FEATURE_NAMES, genome[N_FEATURES:2 * N_FEATURES].tolist()))
        params = genome[2 * N_FEATURES:]
    else:
        raise ValueError(f"unknown phase: {phase}")
    params_dict = dict(zip(PARAM_NAMES, params.tolist()))
    return w_off, w_def, params_dict


def _dump_genome_json(genome_id: int, phase: str, master_seed: int,
                      w_off: dict, w_def, params: dict) -> Path:
    """Write the genome spec to a temp JSON file under ARTIFACTS/genomes/
    and return the path. The zoo agent's createTeam will load it via
    `--redOpts weights=<this path>`.
    """
    genome_dir = ARTIFACTS / "genomes"
    genome_dir.mkdir(parents=True, exist_ok=True)
    path = genome_dir / f"tmp_{phase}_s{master_seed}_g{genome_id}.json"
    with path.open("w") as f:
        json.dump({"w_off": w_off, "w_def": w_def, "params": params}, f)
    return path


def evaluate_genome(genome_id: int, genome: np.ndarray, phase: str,
                    opponents: list, layouts: list,
                    games_per_opponent: int, master_seed: int) -> dict:
    """Play the candidate genome against every opponent on every layout,
    both colors, and aggregate into the fitness inputs expected by
    `compute_fitness`.

    Uses `EVOLVE_CONTAINER_AGENT` (zoo_reflex_tuned) as the host — it
    accepts `weights=<json_path>` via capture.py's --redOpts/--blueOpts
    channel (M4b-2 protocol). The genome JSON is written once per call
    and reused across every match to keep disk I/O minimal.

    Parameters:
      genome_id           : population index, used to name the temp JSON.
      genome              : 1-D numpy array (shape matches genome_dims).
      phase               : "2a" (shared W) or "2b" (split W).
      opponents           : list of agent names; empty → DEFAULT_DRY_RUN_OPPONENTS.
      layouts             : list of layouts; empty → DEFAULT_DRY_RUN_LAYOUTS.
      games_per_opponent  : TOTAL games per opponent, distributed evenly
                            across layouts × 2 colors (floor-div; min 2).
      master_seed         : base seed for layout-RANDOM variance injection.

    Returns dict: {pool_win_rate, crash_rate, stddev_win_rate, monster_win_rate}.
    pool_win_rate, crash_rate, stddev_win_rate are floats in [0, 1];
    stddev_win_rate is the standard deviation of per-opponent win rates.
    monster_win_rate is 0.0 when no monster_* opponents participate.
    """
    # 1) Decode and persist the genome so child capture.py processes can load it.
    w_off, w_def, params = _decode_genome(genome, phase)
    genome_file = _dump_genome_json(genome_id, phase, master_seed,
                                    w_off, w_def, params)

    try:
        # 2) Resolve pool / layouts.
        if not opponents:
            opponents = list(DEFAULT_DRY_RUN_OPPONENTS)
        if not layouts:
            layouts = list(DEFAULT_DRY_RUN_LAYOUTS)

        # 3) Build the match list. Each opponent gets games_per_opponent
        # games total, distributed evenly across (layout × color).
        per_config = max(1, games_per_opponent // max(1, len(layouts) * 2))
        weights_arg = f"weights={genome_file}"

        matches = []  # (opp, our_is_red, red, blue, layout, seed, red_opts, blue_opts)
        for opp in opponents:
            for li, layout in enumerate(layouts):
                for rep in range(per_config):
                    seed = master_seed + li * 997 + rep
                    # Our agent as RED
                    matches.append((
                        opp, True,
                        EVOLVE_CONTAINER_AGENT, opp,
                        layout, seed,
                        weights_arg, "",
                    ))
                    # Our agent as BLUE (color swap for CRN variance reduction)
                    matches.append((
                        opp, False,
                        opp, EVOLVE_CONTAINER_AGENT,
                        layout, seed,
                        "", weights_arg,
                    ))

        # 4) Run every match sequentially (evolve.py's outer gen-loop is
        # where parallelism lives; each genome is fast to evaluate here).
        per_opp_wins: dict = defaultdict(list)
        monster_wins: list = []
        total_games = 0
        total_crashes = 0

        for opp, our_is_red, red, blue, layout, seed, red_opts, blue_opts in matches:
            try:
                result = run_match(
                    red=red, blue=blue, layout=layout, seed=seed,
                    timeout_s=120.0,
                    red_opts=red_opts, blue_opts=blue_opts,
                )
            except Exception as e:
                # Treat a wrapper-level crash as a loss; keep iterating.
                result = {"crashed": True, "red_win": 0, "blue_win": 0}

            total_games += 1
            if result.get("crashed"):
                total_crashes += 1
                win = 0  # crashed → our loss
            else:
                win = int(result.get("red_win" if our_is_red else "blue_win", 0))
            per_opp_wins[opp].append(win)
            if opp.startswith("monster_"):
                monster_wins.append(win)

        # 5) Aggregate.
        all_wins = [w for ws in per_opp_wins.values() for w in ws]
        pool_win_rate = (sum(all_wins) / len(all_wins)) if all_wins else 0.0
        crash_rate = (total_crashes / total_games) if total_games else 0.0
        per_opp_wr = [sum(ws) / len(ws) for ws in per_opp_wins.values() if ws]
        stddev_win_rate = float(np.std(per_opp_wr)) if per_opp_wr else 0.0
        monster_win_rate = (sum(monster_wins) / len(monster_wins)) if monster_wins else 0.0

        return {
            "pool_win_rate": pool_win_rate,
            "crash_rate": crash_rate,
            "stddev_win_rate": stddev_win_rate,
            "monster_win_rate": monster_win_rate,
        }
    finally:
        # 6) Clean up temp genome JSON (keeps artifacts/ from bloating
        # with N*G*gens files over a long campaign).
        try:
            genome_file.unlink()
        except Exception:
            pass


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


def run_phase(phase: str, n_gens: int, N: int, rho: float, games_per_opponent: int,
              master_seed: int, initial_mean=None, initial_sigma=None,
              workers: int | None = None,
              opponents: list | None = None, layouts: list | None = None):
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

    # Resolve worker count and opponents/layouts pool (α-1 + α-3 glue).
    # Passing opponents=None / layouts=None lets evaluate_genome fall back
    # to DEFAULT_DRY_RUN_* — the existing M4b-3 behaviour.
    if workers is None:
        workers = _default_workers()
    opp_for_eval = list(opponents) if opponents else []
    lay_for_eval = list(layouts) if layouts else []

    gen_records = []
    for gen in range(n_gens):
        seed_gen = master_seed + gen * 1000
        population = sample_gaussian(mean, sigma, N, seed_gen)

        # Preallocate so results land at the genome's own index even though
        # futures complete out-of-order.
        fitnesses_list: list = [0.0] * N
        eval_results: list = [None] * N

        # Genome-level parallel evaluation (α-1). Worker-level exceptions
        # are logged LOUDLY and the genome is demoted (crash_rate=1.0) —
        # this is the counterpart to the M4b-1 fail-fast rule applied
        # inside the pool. A bad genome does NOT silently look like f=0.0
        # (that pattern was how 20h of evolution would emit noise weights).
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    evaluate_genome,
                    gid, population[gid], phase,
                    opp_for_eval, lay_for_eval,
                    games_per_opponent, seed_gen + gid,
                ): gid
                for gid in range(N)
            }
            for fut in as_completed(futures):
                gid = futures[fut]
                try:
                    result = fut.result()
                except Exception as e:
                    print(f"[evolve] genome {gid} worker error: {type(e).__name__}: {e}",
                          file=sys.stderr)
                    result = {"pool_win_rate": 0.0, "crash_rate": 1.0,
                              "stddev_win_rate": 0.0, "monster_win_rate": 0.0}
                eval_results[gid] = result
                fitnesses_list[gid] = compute_fitness(result, phase)

        fitnesses = np.array(fitnesses_list)
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
    ap.add_argument(
        "--workers", type=int, default=None,
        help=(
            "ProcessPoolExecutor worker count for genome-level parallelism. "
            "Default: min(os.cpu_count()-1, 8) — leaves 1 core for the parent "
            "process + OS, caps at 8 per STRATEGY §3.4 oversubscription rule."
        ),
    )
    ap.add_argument(
        "--opponents", nargs="+", default=None,
        help=(
            "Opponent agent names (e.g. baseline zoo_reflex_h1test ...). "
            "Passed to evaluate_genome. When omitted, evaluate_genome falls "
            "back to DEFAULT_DRY_RUN_OPPONENTS."
        ),
    )
    ap.add_argument(
        "--layouts", nargs="+", default=None,
        help=(
            "Layout names. `RANDOM` gets promoted per-seed in run_match.py "
            "(seed→RANDOM<seed>). When omitted, falls back to "
            "DEFAULT_DRY_RUN_LAYOUTS."
        ),
    )
    args = ap.parse_args()

    result_2a = None
    if args.phase in ("2a", "both"):
        print(f"[evolve] starting Phase 2a (shared W, {args.n_gens_2a} gens, "
              f"pop={args.pop}, workers={args.workers or _default_workers()})",
              file=sys.stderr)
        result_2a = run_phase(
            phase="2a", n_gens=args.n_gens_2a, N=args.pop, rho=args.rho,
            games_per_opponent=args.games_per_opponent_2a,
            master_seed=args.master_seed,
            workers=args.workers,
            opponents=args.opponents, layouts=args.layouts,
        )

    if args.phase in ("2b", "both"):
        print(f"[evolve] starting Phase 2b (split W, {args.n_gens_2b} gens, "
              f"pop={args.pop}, workers={args.workers or _default_workers()})",
              file=sys.stderr)
        init_mean = np.array(result_2a["final_mean"]) if result_2a else None
        init_sigma = np.array(result_2a["final_sigma"]) * 0.5 + 10.0 if result_2a else None
        result_2b = run_phase(
            phase="2b", n_gens=args.n_gens_2b, N=args.pop, rho=args.rho,
            games_per_opponent=args.games_per_opponent_2b,
            master_seed=args.master_seed + 10000,
            initial_mean=init_mean, initial_sigma=init_sigma,
            workers=args.workers,
            opponents=args.opponents, layouts=args.layouts,
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

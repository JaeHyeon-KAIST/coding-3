#!/usr/bin/env python3
"""Thin orchestrator over hth_resumable.py for pm32 F3 HTH calibration.

Mirrors v3a_sweep.py:run_variant pattern (loops over variants, subprocess
calls hth_resumable.py per variant). Reuses tested I/O code from
hth_resumable.py (atomic writes, resume key, FIELDS, wilson_95).

Depends on hth_resumable.py contract (FIELDS, --agent, --opponents, --workers,
etc.). If hth_resumable.py changes, see pm32 plan §6.F3 for required updates.

Usage:
    .venv/bin/python experiments/rc_tempo/hth_sweep.py \\
        --variants-file experiments/rc_tempo/pm32_t2_variants.txt \\
        --opponents baseline zoo_reflex_rc82 zoo_reflex_rc166 zoo_reflex_rc32 \\
                    monster_rule_expert zoo_distill_rc22 \\
        --layouts defaultCapture distantCapture strategicCapture testCapture \\
        --colors red blue \\
        --games-per-cell 30 --workers 24 \\
        --out-dir experiments/artifacts/rc_tempo/v3_sweep_pm32_hth/
"""
from __future__ import annotations
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
HTH_RESUMABLE = HERE / 'hth_resumable.py'
VENV_PYTHON = REPO / '.venv' / 'bin' / 'python'

# Single source of truth for variant → (agent, env_overrides) dispatch
sys.path.insert(0, str(HERE))
from v3a_sweep import VARIANTS, _resolve_agent_and_env  # noqa: E402


def resolve_agent_and_env(name):
    """Public alias around v3a_sweep._resolve_agent_and_env so callers (and
    the env-var sanity smoke from pm32 plan §6.C.1) don't reach into the
    underscore name."""
    return _resolve_agent_and_env(name)


def run_variant(name, opponents, layouts, colors, games_per_cell, workers,
                 out_dir, master_seed=42):
    agent, env_overrides = resolve_agent_and_env(name)
    env = os.environ.copy()
    env.update(env_overrides)
    out_csv = Path(out_dir) / f"{name}.csv"
    cmd = [
        str(VENV_PYTHON), str(HTH_RESUMABLE),
        '--agent', agent,
        '--opponents'] + opponents + [
        '--layouts'] + layouts + [
        '--colors'] + colors + [
        '--games-per-cell', str(games_per_cell),
        '--workers', str(workers),
        '--master-seed', str(master_seed),
        '--out', str(out_csv),
    ]
    t0 = time.time()
    print(f"[hth_sweep] ▶ variant={name} agent={agent} env_overrides={env_overrides}",
          flush=True)
    result = subprocess.run(cmd, env=env, cwd=str(REPO))
    wall = time.time() - t0
    print(f"[hth_sweep] ✓ variant={name} wall={wall:.1f}s rc={result.returncode}",
          flush=True)
    return wall


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variants-file', type=Path, required=True)
    ap.add_argument('--opponents', nargs='+', required=True)
    ap.add_argument('--layouts', nargs='+', required=True)
    ap.add_argument('--colors', nargs='+', default=['red', 'blue'])
    ap.add_argument('--games-per-cell', type=int, required=True)
    ap.add_argument('--workers', type=int, default=24)
    ap.add_argument('--master-seed', type=int, default=42)
    ap.add_argument('--out-dir', type=Path, required=True)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if not args.variants_file.exists():
        print(f"ERROR: --variants-file {args.variants_file} not found",
              file=sys.stderr)
        sys.exit(2)

    variants = []
    for line in args.variants_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        variants.append(line)

    total_t0 = time.time()
    for name in variants:
        if name not in VARIANTS:
            print(f"[hth_sweep] ! unknown variant '{name}', skipping",
                  flush=True)
            continue
        try:
            run_variant(name, args.opponents, args.layouts, args.colors,
                         args.games_per_cell, args.workers, args.out_dir,
                         master_seed=args.master_seed)
        except Exception as e:
            print(f"[hth_sweep] !! variant '{name}' CRASHED: "
                  f"{type(e).__name__}: {e}", flush=True)
    total = time.time() - total_t0
    print(f"\n[hth_sweep] All variants done in {total:.0f}s", flush=True)


if __name__ == '__main__':
    main()

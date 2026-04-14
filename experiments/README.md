# experiments/ — Development & Evaluation Infrastructure

Not submitted. This directory holds the training/evaluation pipeline that produces the final submitted agent.

## Directory layout

```
experiments/
├── README.md                    # this file
├── tournament.py                # [M4] round-robin runner using ProcessPoolExecutor
├── run_match.py                 # [M4] single game subprocess wrapper with CPU pinning
├── evolve.py                    # [M5/M6] CEM self-play evolution driver
├── select_top4.py               # [M7] post-evolution ranking + flatten to minicontest/
├── verify_flatten.py            # [M7] AST + sha256 + import checks
├── smoke_zoo.py                 # [M2] per-zoo-agent smoke runner
├── smoke_monsters.py            # [M3] per-monster smoke runner
├── package_submission.sh        # [M10] final zip packager
├── monsters/                    # hand-tuned reference opponents (evaluation only)
│   ├── monster_rule_expert.py       # territorial defender
│   ├── monster_mcts_hand.py         # aggressive raider
│   ├── monster_minimax_d4.py        # adaptive exploiter
│   └── archive/                     # replaced monsters (auto-archived by §6.9 trigger)
└── artifacts/                   # gitignored generated outputs
    ├── gen*.json                    # per-generation CEM state
    ├── smoke_zoo.csv                # M2 exit evidence
    ├── smoke_monsters.csv           # M3 exit evidence
    ├── tournament_results/          # M4+ raw match logs
    ├── evolution_log/               # CEM progress, ELO curve data
    └── final_weights.py             # baked weights for your_best.py
```

## Relationship to `minicontest/`

During development, agent **source files** live in `minicontest/` with `zoo_` prefix (e.g., `minicontest/zoo_core.py`, `minicontest/zoo_reflex_tuned.py`). This is required because `capture.py -r <name>` loads `<name>.py` from the current working directory.

At submission time:
1. `experiments/select_top4.py` runs the zoo round-robin
2. Picks representatives per family (reflex / minimax / MCTS / champion)
3. Flattens via `verify_flatten.py` (strips `_core.py` inheritance, inlines helpers)
4. Copies into `minicontest/your_best.py` and `minicontest/your_baseline1~3.py`
5. Only `your_best.py` is renamed and submitted (`{student_id}.py`)

See `.omc/plans/STRATEGY.md` §1.5 and §4.0 for the full scheme.

## Key constraints (from plan)

- Python 3.9, numpy + pandas only
- Training-time parallel workers ≤ physical cores (CPU pinning required)
- Seed-fixed for reproducibility — `(generation, genome_id, opponent_id, layout_id, color_swap)` master seed derived
- Framework SIGALRM owned by `capture.py`; training code must not override
- During training, use Common Random Numbers (CRN): paired red/blue color swap on same seed
- Sequential halving for elite re-evaluation under uncertainty

## Running things

All Python via `.venv/bin/python`:

```bash
# Smoke single zoo agent
cd minicontest && ../.venv/bin/python capture.py -r zoo_dummy -b baseline -n 1 -q

# M2 zoo smoke (runs after M1 complete)
../.venv/bin/python experiments/smoke_zoo.py

# Full tournament (M4+)
../.venv/bin/python experiments/tournament.py --workers 8 --pin

# Evolution campaign (M6)
../.venv/bin/python experiments/evolve.py --config experiments/cem_config.yaml

# Submission selection + flatten (M7)
../.venv/bin/python experiments/select_top4.py
```

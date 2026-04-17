#!/usr/bin/env bash
# launch_orders_34.sh
# --------------------
# Launch Orders 3 or 4 on the server with pm20-designed diversification:
#   Order 3: master-seed=1001, init=h1test, + zoo_reflex_A1 HOF opponent
#   Order 4: master-seed=2026, init=a1    , + zoo_reflex_A1 HOF opponent
#
# Expected wall: ~18h per Order (A1 pm18 pace: 47 min/gen × 10 gens 2a + 34 min/gen × 20 gens 2b).
# Pool size: 12 opponents (pm19's 11 + zoo_reflex_A1 = 12). A1 in pool forces
# CEM to discover weights that beat the pm19 champion, producing meaningfully
# different champions than Order 2 (pure Gaussian noise around same mean).
#
# Prerequisites (run on server):
#   1. Order 2 has finished and its artifacts archived:
#        experiments/artifacts/2a_gen*.json → phase2_A1_B1_20dim/
#        experiments/artifacts/2b_gen*.json → phase2_A1_B1_20dim/
#        experiments/artifacts/final_weights.py → phase2_A1_B1_20dim/
#   2. `git pull origin main` up-to-date with pm20 commits (zoo_reflex_A1.py,
#      evolve.py a1 init option, this script itself).
#   3. Order 2 HTH decision made — if Order 2 > A1, update zoo_reflex_A1 wrapper
#      to point at Order 2 weights (or add zoo_reflex_O2 wrapper) before Order 3
#      launches.
#
# Usage (on server inside tmux work session):
#   cd ~/projects/coding-3
#   bash experiments/launch_orders_34.sh 3    # launches Order 3
#   bash experiments/launch_orders_34.sh 4    # launches Order 4 (after Order 3 done)

set -u -o pipefail

ORDER_NUM="${1:-}"

case "$ORDER_NUM" in
    3)
        MASTER_SEED=1001
        INIT_MEAN=h1test
        TAG="A3_diverse_s1001_h1test"
        ;;
    4)
        MASTER_SEED=2026
        INIT_MEAN=a1
        TAG="A4_diverse_s2026_a1init"
        ;;
    *)
        echo "Usage: $0 <3|4>" >&2
        exit 1
        ;;
esac

# Verify prerequisites before launching (cheap failure).
if [[ ! -f minicontest/zoo_reflex_A1.py ]]; then
    echo "[launch] ERROR: minicontest/zoo_reflex_A1.py missing — git pull?" >&2
    exit 2
fi
if ! .venv/bin/python -c "import sys; sys.path.insert(0,'experiments'); import evolve; assert '$INIT_MEAN' in evolve.KNOWN_SEEDS_PHASE_2A" 2>/dev/null; then
    echo "[launch] ERROR: evolve.py KNOWN_SEEDS_PHASE_2A missing '$INIT_MEAN' — git pull?" >&2
    exit 3
fi

# Previous artifacts present → abort (would be overwritten silently).
if compgen -G "experiments/artifacts/2[ab]_gen*.json" > /dev/null; then
    echo "[launch] ERROR: experiments/artifacts/ still has gen JSONs from a prior run." >&2
    echo "[launch]        Archive them first:" >&2
    echo "[launch]          mkdir -p experiments/artifacts/phase2_<PREV_TAG>/" >&2
    echo "[launch]          mv experiments/artifacts/2a_gen*.json experiments/artifacts/2b_gen*.json \\" >&2
    echo "[launch]             experiments/artifacts/final_weights.py experiments/artifacts/hth_*.csv \\" >&2
    echo "[launch]             experiments/artifacts/phase2_<PREV_TAG>/" >&2
    exit 4
fi

mkdir -p logs

TIMESTAMP="$(date +%Y%m%d-%H%M)"
LOG_PATH="logs/phase2_${TAG}_${TIMESTAMP}.log"

echo "[launch] Order $ORDER_NUM — master-seed=$MASTER_SEED, init=$INIT_MEAN"
echo "[launch] log = $LOG_PATH"
echo "[launch] ETA ≈ 18h"
echo ""

# Auto-detect HOF wrappers (zoo_reflex_O2.py, zoo_reflex_O3.py, ...) in
# minicontest/ — each represents a previously-completed Order's champion.
# Order N+1's opponent pool must include all prior Orders' wrappers so CEM
# evolves against the real champion history (AlphaZero-lite Red Queen).
HOF_WRAPPERS=()
for wrapper in minicontest/zoo_reflex_O*.py; do
    [[ -f "$wrapper" ]] || continue
    stem=$(basename "$wrapper" .py)
    HOF_WRAPPERS+=("$stem")
done

echo "[launch] HOF wrappers in pool: zoo_reflex_A1 ${HOF_WRAPPERS[@]:-(none)}"

.venv/bin/python experiments/evolve.py --phase both \
    --master-seed "$MASTER_SEED" \
    --workers 16 \
    --n-gens-2a 10 \
    --n-gens-2b 20 \
    --pop 40 \
    --rho 0.35 \
    --games-per-opponent-2a 24 \
    --games-per-opponent-2b 16 \
    --init-mean-from "$INIT_MEAN" \
    --opponents \
        baseline baseline \
        zoo_reflex_h1test zoo_reflex_h1b zoo_reflex_h1c \
        zoo_reflex_aggressive zoo_reflex_defensive \
        zoo_reflex_A1 "${HOF_WRAPPERS[@]}" \
        zoo_minimax_ab_d2 zoo_minimax_ab_d3_opp zoo_expectimax \
        monster_rule_expert \
    --layouts defaultCapture RANDOM \
    2>&1 | tee "$LOG_PATH"

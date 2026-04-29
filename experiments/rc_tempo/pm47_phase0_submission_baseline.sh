#!/usr/bin/env bash
# pm47 Phase 0 — submission baseline matrix
#
# Measure 20200492.py (the actual submission) against the 17-defender zoo
# that was used for CAPX/ABS measurement. This is the FIRST broad measurement
# of the submission code (only HTH vs baseline.py was previously known).
#
# Usage:
#   bash experiments/rc_tempo/pm47_phase0_submission_baseline.sh           # default 10 seeds
#   SEEDS_PER_DEF=30 bash experiments/rc_tempo/pm47_phase0_submission_baseline.sh
#   SMOKE=1 bash experiments/rc_tempo/pm47_phase0_submission_baseline.sh   # 5 defender x 10 seed sanity
#
# Output: experiments/results/pm47_phase0/submission_matrix.csv
# Columns: defender,seed,outcome,score,wall_s
# outcome: red_win | blue_win | tie | timeout | error

set -u

cd "$(dirname "$0")/../.." || { echo "FAIL: cannot cd to repo root"; exit 1; }
ROOT="$(pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "FAIL: missing $PY"; exit 1; }

OUT="$ROOT/experiments/results/pm47_phase0"
mkdir -p "$OUT/logs"

# Default: 10 seeds per defender (Codex staged recommendation).
# Override via env: SEEDS_PER_DEF=30 for full Claude-style sweep.
SEEDS_PER_DEF=${SEEDS_PER_DEF:-10}
GAME_TIMEOUT=${GAME_TIMEOUT:-90}

# Defender set (17, same as pm46 v2 CAPX matrix)
ALL_DEFENDERS=(
  baseline
  monster_rule_expert
  zoo_minimax_ab_d3_opp
  zoo_reflex_defensive
  zoo_reflex_A1
  zoo_reflex_A1_D13
  zoo_reflex_A1_T5
  zoo_hybrid_mcts_reflex
  zoo_minimax_ab_d2
  zoo_reflex_A1_D1
  zoo_reflex_capsule
  zoo_reflex_rc82
  zoo_dummy
  zoo_reflex_aggressive
  zoo_reflex_tuned
  zoo_reflex_rc_tempo_beta_retro
  zoo_reflex_rc_tempo_gamma
)

# Smoke mode: 5 weak defenders only
if [ "${SMOKE:-0}" = "1" ]; then
  DEFENDERS=(zoo_dummy zoo_reflex_aggressive zoo_reflex_tuned zoo_reflex_capsule baseline)
  CSV_NAME=submission_smoke.csv
else
  DEFENDERS=("${ALL_DEFENDERS[@]}")
  CSV_NAME=submission_matrix_n${SEEDS_PER_DEF}.csv
fi

CSV="$OUT/$CSV_NAME"
echo "defender,seed,outcome,score,wall_s" > "$CSV"

# hybrid_mcts needs a smaller move budget to fit timeouts (per pm46 recovery wiki)
HYBRID_MCTS_ENV='ZOO_MCTS_MOVE_BUDGET=0.05'

global_t0=$(date +%s)
total_games=$((${#DEFENDERS[@]} * SEEDS_PER_DEF))
done_games=0

echo "=== pm47 phase 0 submission baseline ==="
echo "defenders: ${#DEFENDERS[@]} | seeds: $SEEDS_PER_DEF | total: $total_games"
echo "csv: $CSV"
echo ""

for def in "${DEFENDERS[@]}"; do
  d_t0=$(date +%s)
  d_wins=0
  d_losses=0
  d_ties=0
  for seed in $(seq 1 $SEEDS_PER_DEF); do
    log="$OUT/logs/${def}_seed${seed}.log"
    g_t0=$(date +%s)
    cd "$ROOT/minicontest"

    # Pick env vars for this defender
    if [ "$def" = "zoo_hybrid_mcts_reflex" ]; then
      EXTRA_ENV="$HYBRID_MCTS_ENV"
      EFFECTIVE_TIMEOUT=240
    else
      EXTRA_ENV=""
      EFFECTIVE_TIMEOUT=$GAME_TIMEOUT
    fi

    # shellcheck disable=SC2086
    timeout "$EFFECTIVE_TIMEOUT" env $EXTRA_ENV PYTHONHASHSEED=0 \
      "$PY" "$ROOT/experiments/rc_tempo/pm45_single_game.py" \
      -r 20200492 -b "$def" -l "RANDOM$seed" -n 1 -q \
      > "$log" 2>&1 || true
    cd "$ROOT"
    wall=$(($(date +%s) - g_t0))

    # Parse outcome via Win Rate lines (most reliable across all
    # game-end paths: regular win, 28-dot return, timeout, tie).
    score=$(grep -oE 'Average Score: -?[0-9.]+' "$log" | head -1 | grep -oE '\-?[0-9.]+' | head -1)
    [ -z "$score" ] && score=0
    red_wr=$(grep -oE 'Red Win Rate: +[01]/1' "$log" | head -1 | grep -oE '[01]/1' | head -1 | cut -d/ -f1)
    blue_wr=$(grep -oE 'Blue Win Rate: +[01]/1' "$log" | head -1 | grep -oE '[01]/1' | head -1 | cut -d/ -f1)
    if [ "$red_wr" = "1" ]; then
      outcome=red_win; d_wins=$((d_wins + 1))
    elif [ "$blue_wr" = "1" ]; then
      outcome=blue_win; d_losses=$((d_losses + 1))
    elif [ "$red_wr" = "0" ] && [ "$blue_wr" = "0" ]; then
      outcome=tie; d_ties=$((d_ties + 1))
    else
      outcome=error
    fi

    echo "$def,$seed,$outcome,${score:-0},$wall" >> "$CSV"
    done_games=$((done_games + 1))
  done
  d_wall=$(($(date +%s) - d_t0))
  echo "[$done_games/$total_games] $def: W=$d_wins L=$d_losses T=$d_ties wall=${d_wall}s"
done

echo ""
echo "=== summary ==="
total_w=$(awk -F, 'NR>1 && $3=="red_win"' "$CSV" | wc -l | tr -d ' ')
total_l=$(awk -F, 'NR>1 && $3=="blue_win"' "$CSV" | wc -l | tr -d ' ')
total_t=$(awk -F, 'NR>1 && ($3=="tie"||$3=="timeout")' "$CSV" | wc -l | tr -d ' ')
total_e=$(awk -F, 'NR>1 && $3=="error"' "$CSV" | wc -l | tr -d ' ')
echo "AGGREGATE: W=$total_w L=$total_l T=$total_t err=$total_e total=$total_games"
echo "wall_total=$(($(date +%s) - global_t0))s | csv=$CSV"

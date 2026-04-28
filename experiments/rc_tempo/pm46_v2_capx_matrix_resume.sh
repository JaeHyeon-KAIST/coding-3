#!/usr/bin/env bash
# pm46 v2 Phase 3 RESUME — skip zoo_hybrid_mcts_reflex (90s timeouts wasteful).
#
# Continues CAPX matrix from defender 9 (zoo_minimax_ab_d2) onward.
# APPENDS to existing capx_matrix_m0.csv (does NOT overwrite).
#
# Pre-state required:
#   - capx_matrix_m0.csv has rows for defenders 1-7 (full 30) + hybrid_mcts
#     partial (3 timeouts) = 213 games + header.
#   - Original sweep killed cleanly.

set -u

cd "$(dirname "$0")/../.." || { echo "FAIL: cannot cd to repo root"; exit 1; }
ROOT="$(pwd)"
PY="$ROOT/.venv/bin/python"

OUT_DIR="$ROOT/experiments/results/pm46_v2"
CSV="$OUT_DIR/capx_matrix_m0.csv"
LOG_DIR="$OUT_DIR/logs_capx_matrix"
mkdir -p "$LOG_DIR"

[ -f "$CSV" ] || { echo "FAIL: $CSV not found — abort resume"; exit 1; }

# Resume defenders (skip hybrid_mcts).
DEFENDERS=(
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

SEEDS=()
for i in $(seq 1 30); do SEEDS+=("$i"); done

GAME_TIMEOUT_S=90
TOTAL=$(( ${#DEFENDERS[@]} * ${#SEEDS[@]} ))
COUNTER=0
START_TS=$(date +%s)

echo "=== pm46 v2 CAPX matrix RESUME (skip hybrid_mcts, append to $CSV) ==="
echo "host: $(hostname)  total resume games: $TOTAL"
echo

# Add synthetic timeout entries for hybrid_mcts seeds 4-30 (preserves matrix shape).
echo "Pre-fill: zoo_hybrid_mcts_reflex seeds 4-30 = synthetic timeout (defender slow, 90s+)"
for s in $(seq 4 30); do
  echo "zoo_hybrid_mcts_reflex,$s,timeout,,0,false,0,,90" >> "$CSV"
done

# Now run remaining defenders.
for DEF in "${DEFENDERS[@]}"; do
  for SEED in "${SEEDS[@]}"; do
    COUNTER=$(( COUNTER + 1 ))
    LAY="RANDOM${SEED}"
    LOG="$LOG_DIR/m0_${DEF}_seed${SEED}.log"
    T0=$(date +%s)

    ( cd minicontest && timeout $GAME_TIMEOUT_S env \
        PYTHONHASHSEED=0 \
        CAPX_MIN_MARGIN=0 \
        "$PY" ../experiments/rc_tempo/pm45_single_game.py \
          -r zoo_reflex_rc_tempo_capx_solo -b "$DEF" -l "$LAY" -n 1 -q \
        > "$LOG" 2>&1 ) || true

    WALL=$(( $(date +%s) - T0 ))

    EAT_LINES=$(grep -c '\[CAPX_CAP_EATEN\]' "$LOG" 2>/dev/null)
    EAT_LINES=${EAT_LINES:-0}; EAT_LINES=${EAT_LINES//[!0-9]/}
    [ -z "$EAT_LINES" ] && EAT_LINES=0

    DIED_RAW=$(grep '\[CAPX_A_DIED\]' "$LOG" 2>/dev/null || true)
    if [ -z "$DIED_RAW" ]; then
      A_TOTAL_DEATHS=0
    else
      A_TOTAL_DEATHS=$(printf '%s\n' "$DIED_RAW" | grep -c '\[CAPX_A_DIED\]')
      A_TOTAL_DEATHS=${A_TOTAL_DEATHS:-0}; A_TOTAL_DEATHS=${A_TOTAL_DEATHS//[!0-9]/}
      [ -z "$A_TOTAL_DEATHS" ] && A_TOTAL_DEATHS=0
    fi

    FIRST_HEAD=$(grep '\[CAPX_CAP_EATEN\]' "$LOG" 2>/dev/null | head -1 || true)
    if [ -n "$FIRST_HEAD" ]; then
      FIRST_EAT_TICK=$(echo "$FIRST_HEAD" | sed -n 's/.*tick=\([0-9]*\).*/\1/p')
    else
      FIRST_EAT_TICK=""
    fi

    A_DIED_WITHIN_3="false"
    if [ -n "$FIRST_EAT_TICK" ] && [ -n "$DIED_RAW" ]; then
      while IFS= read -r dline; do
        [ -z "$dline" ] && continue
        DTICK=$(echo "$dline" | sed -n 's/.*tick=\([0-9]*\).*/\1/p')
        if [ -n "$DTICK" ] && [ "$DTICK" -le "$FIRST_EAT_TICK" ] && \
           [ "$((FIRST_EAT_TICK - DTICK))" -le 3 ]; then
          A_DIED_WITHIN_3="true"
          break
        fi
      done <<< "$DIED_RAW"
    fi

    SCORE_LINE=$(grep -E "Average Score" "$LOG" 2>/dev/null | head -1 || true)
    if [ -z "$SCORE_LINE" ]; then
      OUTCOME="timeout"
      SCORE=""
    else
      SCORE=$(echo "$SCORE_LINE" | sed -n 's/.*Score: *\(-*[0-9]*\).*/\1/p')
      [ -z "$SCORE" ] && SCORE=""
      if [ "$EAT_LINES" -gt 0 ] 2>/dev/null; then
        if [ "$A_DIED_WITHIN_3" = "true" ]; then
          OUTCOME="eat_died"
        else
          OUTCOME="eat_alive"
        fi
      else
        if [ "$A_TOTAL_DEATHS" -gt 0 ] 2>/dev/null; then
          OUTCOME="no_eat_died"
        else
          OUTCOME="no_eat_alive"
        fi
      fi
    fi

    echo "$DEF,$SEED,$OUTCOME,$FIRST_EAT_TICK,$EAT_LINES,$A_DIED_WITHIN_3,$A_TOTAL_DEATHS,$SCORE,$WALL" >> "$CSV"

    ELAPSED=$(( $(date +%s) - START_TS ))
    printf "[%3d/%3d] %-32s seed=%2d  outcome=%-12s wall=%2ds elapsed=%4ds\n" \
      "$COUNTER" "$TOTAL" "$DEF" "$SEED" "${OUTCOME:-NA}" "$WALL" "$ELAPSED"
  done
done

ELAPSED=$(( $(date +%s) - START_TS ))
echo
echo "=== resume complete: $TOTAL games in ${ELAPSED}s ==="

#!/usr/bin/env bash
# pm46 v2 CAPX Phase 2 smoke — 3 defenders × 3 seeds = 9 games
#
# Per plan §6 Phase 2:
#   AC: vs zoo_dummy ≥ 2/3 cap_eat_alive
#       vs baseline ≥ 1/3 cap_eat_alive
#       vs monster_rule_expert ≥ 1/3 OR document chokepoint topology
#
# Use:
#   bash experiments/rc_tempo/pm46_v2_capx_smoke.sh [CAPX_MIN_MARGIN_value]
#   default: CAPX_MIN_MARGIN=-15 (permissive — full-path gate too strict at 0)

set -u

cd "$(dirname "$0")/../.." || { echo "FAIL: cannot cd to repo root"; exit 1; }
ROOT="$(pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "FAIL: missing $PY"; exit 1; }

OUT_DIR="$ROOT/experiments/results/pm46_v2"
mkdir -p "$OUT_DIR"

MARGIN="${1:--15}"
CSV="$OUT_DIR/capx_smoke_m${MARGIN}.csv"
LOG_DIR="$OUT_DIR/logs_capx_smoke"
mkdir -p "$LOG_DIR"

DEFENDERS=(baseline monster_rule_expert zoo_dummy)
SEEDS=(1 8 15)

GAME_TIMEOUT_S=90
TOTAL=$(( ${#DEFENDERS[@]} * ${#SEEDS[@]} ))
COUNTER=0
START_TS=$(date +%s)

echo "=== pm46 v2 CAPX smoke (CAPX_MIN_MARGIN=$MARGIN) ==="
echo "host: $(hostname)  python: $($PY --version 2>&1)  total games: $TOTAL"
echo "csv:  $CSV"
echo

echo "defender,seed,outcome,first_eat_tick,total_caps_eaten,a_died_within_3,a_total_deaths,score,wall_s" > "$CSV"

for DEF in "${DEFENDERS[@]}"; do
  for SEED in "${SEEDS[@]}"; do
    COUNTER=$(( COUNTER + 1 ))
    LAY="RANDOM${SEED}"
    LOG="$LOG_DIR/m${MARGIN}_${DEF}_seed${SEED}.log"
    T0=$(date +%s)

    ( cd minicontest && timeout $GAME_TIMEOUT_S env \
        PYTHONHASHSEED=0 \
        CAPX_MIN_MARGIN="$MARGIN" \
        "$PY" ../experiments/rc_tempo/pm45_single_game.py \
          -r zoo_reflex_rc_tempo_capx_solo -b "$DEF" -l "$LAY" -n 1 -q \
        > "$LOG" 2>&1 ) || true

    WALL=$(( $(date +%s) - T0 ))

    # Parse — fixed grep -c handling (avoid 0\n0 bug).
    EAT_LINES=$(grep -c '\[CAPX_CAP_EATEN\]' "$LOG" 2>/dev/null)
    EAT_LINES=${EAT_LINES:-0}
    EAT_LINES=${EAT_LINES//[!0-9]/}

    DIED_LINES_RAW=$(grep '\[CAPX_A_DIED\]' "$LOG" 2>/dev/null || true)
    if [ -z "$DIED_LINES_RAW" ]; then
      A_TOTAL_DEATHS=0
    else
      A_TOTAL_DEATHS=$(printf '%s\n' "$DIED_LINES_RAW" | grep -c '\[CAPX_A_DIED\]')
      A_TOTAL_DEATHS=${A_TOTAL_DEATHS:-0}
    fi

    FIRST_EAT_LINE=$(grep '\[CAPX_CAP_EATEN\]' "$LOG" 2>/dev/null | tail -1 || true)
    if [ -n "$FIRST_EAT_LINE" ]; then
      # Caveat: timeleft counts DOWN, so first emit is HIGHEST tick. We use
      # tail -1 to get the FIRST (chronologically latest emit = oldest cap).
      # Wait actually: first emit chronologically = first in log = head.
      FIRST_EAT_LINE_HEAD=$(grep '\[CAPX_CAP_EATEN\]' "$LOG" 2>/dev/null | head -1 || true)
      FIRST_EAT_TICK=$(echo "$FIRST_EAT_LINE_HEAD" | sed -n 's/.*tick=\([0-9]*\).*/\1/p')
    else
      FIRST_EAT_TICK=""
    fi

    # a_died_within_3: any death tick ≤ first_eat + 3 (timeleft DECREASES so death tick < first_eat tick by ≤3)
    A_DIED_WITHIN_3="false"
    if [ -n "$FIRST_EAT_TICK" ] && [ -n "$DIED_LINES_RAW" ]; then
      while IFS= read -r dline; do
        [ -z "$dline" ] && continue
        DTICK=$(echo "$dline" | sed -n 's/.*tick=\([0-9]*\).*/\1/p')
        if [ -n "$DTICK" ] && [ "$DTICK" -le "$FIRST_EAT_TICK" ] && \
           [ "$((FIRST_EAT_TICK - DTICK))" -le 3 ]; then
          A_DIED_WITHIN_3="true"
          break
        fi
      done <<< "$DIED_LINES_RAW"
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
    printf "[%d/%d] %-22s seed=%2d  outcome=%-12s eats=%-2s deaths=%-2s wall=%2ds total=%4ds\n" \
      "$COUNTER" "$TOTAL" "$DEF" "$SEED" "${OUTCOME:-NA}" "${EAT_LINES:-0}" "${A_TOTAL_DEATHS:-0}" "$WALL" "$ELAPSED"
  done
done

echo
echo "=== smoke summary (CAPX_MIN_MARGIN=$MARGIN) ==="
for DEF in "${DEFENDERS[@]}"; do
  EA=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="eat_alive" {n++} END {print n+0}' "$CSV")
  ED=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="eat_died" {n++} END {print n+0}' "$CSV")
  TOT=$(awk -F, -v d="$DEF" 'NR>1 && $1==d {n++} END {print n+0}' "$CSV")
  printf "  %-22s eat_alive=%d/%d eat_died=%d\n" "$DEF" "$EA" "$TOT" "$ED"
done

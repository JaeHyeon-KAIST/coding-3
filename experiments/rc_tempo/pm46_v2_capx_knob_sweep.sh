#!/usr/bin/env bash
# pm46 v2 Phase 4 — CAPX knob tuning sweep on Tier-A subset.
#
# Per code-reviewer's Phase 4 candidates (.omc/wiki/pm46-v2-capx-code-review-
# phase4-tuning.md):
#   MIN_MARGIN ∈ {0, 1}
#   HARD_ABANDON ∈ {-1, 0}
#   GATE_HORIZON ∈ {6, 8, 10}
#   SIGMOID ∈ {1.0, 1.5}
# = 24 cells × 35 games (Tier-A 7 def × 5 seed) = 840 games per full sweep.
#
# Pruning (-coarse): only 4 cells (extremes) for fast scan.
# Aggressive (-prune): 8 cells (mid + extremes).
# Full: all 24 cells (long).
#
# Use:
#   bash experiments/rc_tempo/pm46_v2_capx_knob_sweep.sh [coarse|prune|full]
#   default: coarse

set -u

cd "$(dirname "$0")/../.." || { echo "FAIL: cannot cd to repo root"; exit 1; }
ROOT="$(pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "FAIL: missing $PY"; exit 1; }

OUT_DIR="$ROOT/experiments/results/pm46_v2"
mkdir -p "$OUT_DIR"

MODE="${1:-coarse}"
CSV="$OUT_DIR/capx_knob_sweep_${MODE}.csv"
LOG_DIR="$OUT_DIR/logs_capx_knob_sweep"
mkdir -p "$LOG_DIR"

# Tier-A subset (excluding broken zoo_belief and timeout zoo_hybrid_mcts_reflex).
DEFENDERS=(
  baseline
  monster_rule_expert
  zoo_minimax_ab_d3_opp
  zoo_reflex_defensive
  zoo_reflex_A1
  zoo_reflex_A1_D13
)
SEEDS=(1 8 15 22 29)

# Knob grids.
case "$MODE" in
  coarse)
    # Only 4 cells: extremes
    GRID=(
      "0 -1 8 1.5"   # default
      "1 0 6 1.0"    # strict near-future
      "0 -1 10 1.5"  # longer horizon
      "0 0 8 1.0"    # tight gate
    )
    ;;
  prune)
    # 8 cells: 2x knob1 × 2x knob2 × 2x knob3
    GRID=(
      "0 -1 6 1.0"
      "0 -1 6 1.5"
      "0 -1 8 1.0"
      "0 -1 8 1.5"
      "0 0 8 1.5"
      "1 -1 8 1.5"
      "1 0 8 1.5"
      "1 0 6 1.0"
    )
    ;;
  full)
    # 24 cells per code-reviewer
    GRID=(
      "0 -1 6 1.0"  "0 -1 6 1.5"
      "0 -1 8 1.0"  "0 -1 8 1.5"
      "0 -1 10 1.0" "0 -1 10 1.5"
      "0 0 6 1.0"   "0 0 6 1.5"
      "0 0 8 1.0"   "0 0 8 1.5"
      "0 0 10 1.0"  "0 0 10 1.5"
      "1 -1 6 1.0"  "1 -1 6 1.5"
      "1 -1 8 1.0"  "1 -1 8 1.5"
      "1 -1 10 1.0" "1 -1 10 1.5"
      "1 0 6 1.0"   "1 0 6 1.5"
      "1 0 8 1.0"   "1 0 8 1.5"
      "1 0 10 1.0"  "1 0 10 1.5"
    )
    ;;
  *)
    echo "FAIL: unknown mode $MODE (use coarse|prune|full)"
    exit 1
    ;;
esac

GAME_TIMEOUT_S=90
TOTAL_PER_CELL=$(( ${#DEFENDERS[@]} * ${#SEEDS[@]} ))
TOTAL_GAMES=$(( ${#GRID[@]} * TOTAL_PER_CELL ))
COUNTER=0
START_TS=$(date +%s)

echo "=== pm46 v2 CAPX knob sweep ($MODE) ==="
echo "host: $(hostname)  total games: $TOTAL_GAMES (${#GRID[@]} cells × $TOTAL_PER_CELL)"
echo "csv:  $CSV"
echo

echo "cell,min_margin,hard_abandon,gate_horizon,sigmoid,defender,seed,outcome,first_eat_tick,total_caps_eaten,a_died_within_3,a_total_deaths,score,wall_s" > "$CSV"

CELL_IDX=0
for CELL in "${GRID[@]}"; do
  CELL_IDX=$(( CELL_IDX + 1 ))
  read -r MIN_MARGIN HARD_ABANDON GATE_HORIZON SIGMOID <<< "$CELL"
  CELL_TAG="m${MIN_MARGIN}_h${HARD_ABANDON}_g${GATE_HORIZON}_s${SIGMOID}"
  echo "[CELL $CELL_IDX/${#GRID[@]}] $CELL_TAG"

  for DEF in "${DEFENDERS[@]}"; do
    for SEED in "${SEEDS[@]}"; do
      COUNTER=$(( COUNTER + 1 ))
      LAY="RANDOM${SEED}"
      LOG="$LOG_DIR/${CELL_TAG}_${DEF}_seed${SEED}.log"
      T0=$(date +%s)

      ( cd minicontest && timeout $GAME_TIMEOUT_S env \
          PYTHONHASHSEED=0 \
          CAPX_MIN_MARGIN="$MIN_MARGIN" \
          CAPX_HARD_ABANDON_MARGIN="$HARD_ABANDON" \
          CAPX_GATE_HORIZON="$GATE_HORIZON" \
          CAPX_SIGMOID_SCALE="$SIGMOID" \
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

      echo "$CELL_TAG,$MIN_MARGIN,$HARD_ABANDON,$GATE_HORIZON,$SIGMOID,$DEF,$SEED,$OUTCOME,$FIRST_EAT_TICK,$EAT_LINES,$A_DIED_WITHIN_3,$A_TOTAL_DEATHS,$SCORE,$WALL" >> "$CSV"

      ELAPSED=$(( $(date +%s) - START_TS ))
      printf "  [%3d/%3d] %-28s seed=%2d  outcome=%-12s wall=%2ds elapsed=%4ds\n" \
        "$COUNTER" "$TOTAL_GAMES" "$DEF" "$SEED" "${OUTCOME:-NA}" "$WALL" "$ELAPSED"
    done
  done
done

ELAPSED=$(( $(date +%s) - START_TS ))
echo
echo "=== knob sweep complete: $TOTAL_GAMES games in ${ELAPSED}s ==="
echo
echo "--- best cells (by aggregate eat_alive) ---"
awk -F, 'NR>1 {tot[$1]++; if ($8=="eat_alive") ea[$1]++} END {for (c in tot) printf "%-30s %d/%d (%.1f%%)\n", c, ea[c]+0, tot[c], (ea[c]+0)/tot[c]*100}' "$CSV" | sort -t'(' -k2 -nr | head -10

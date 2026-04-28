#!/usr/bin/env bash
# pm46 v2 Phase 0 (corrected) — ABS-solo cap-eat matrix
# 17 defenders × 30 RANDOM seeds × 1 game each = 510 games
#
# CORRECTED detector vs pm46_v2_a_solo_matrix.sh:
#   - parses [ABS_CAP_EATEN] (any cap eaten by Red, multi-fire)
#   - parses [ABS_A_DIED] (A respawn tracking)
#   - parses [ABS_A_FIRST_CAP_REACH] (legacy, retained)
#   - sets ABS_REACH_EXIT=0 to keep games running past first cap1 reach,
#     so cap2/multi-cap detection works.
#   - timeout 90s per game.
#
# CSV columns:
#   defender, seed, outcome, first_eat_tick, total_caps_eaten,
#   a_died_within_3, a_total_deaths, score, wall_s
#
#   outcome ∈ {eat_alive, eat_died, no_eat_alive, no_eat_died, timeout}
#     eat_alive    — at least one [ABS_CAP_EATEN] AND no [ABS_A_DIED] within
#                    3 ticks of first eat (P3 primary success)
#     eat_died     — at least one [ABS_CAP_EATEN] AND died within 3 ticks
#     no_eat_alive — no cap eaten, A still alive at end
#     no_eat_died  — no cap eaten, A respawned at least once
#     timeout      — no Average Score line (game timed out)
#
# Run from repo root:
#   bash experiments/rc_tempo/pm46_v2_a_solo_matrix_corrected.sh [--smoke]

set -u

cd "$(dirname "$0")/../.." || { echo "FAIL: cannot cd to repo root"; exit 1; }
ROOT="$(pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "FAIL: missing $PY"; exit 1; }

OUT_DIR="$ROOT/experiments/results/pm46_v2"
mkdir -p "$OUT_DIR"

CSV="$OUT_DIR/abs_baseline_corrected.csv"
LOG_DIR="$OUT_DIR/logs_corrected"
mkdir -p "$LOG_DIR"

DEFENDERS=(
  baseline
  monster_rule_expert
  zoo_minimax_ab_d3_opp
  zoo_reflex_defensive
  zoo_reflex_A1
  zoo_reflex_A1_D13
  zoo_belief
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

SEEDS=()
for i in $(seq 1 30); do SEEDS+=("$i"); done

if [ "${1:-}" = "--smoke" ]; then
  DEFENDERS=(baseline monster_rule_expert zoo_dummy)
  SEEDS=(1 8 15)
  CSV="$OUT_DIR/abs_baseline_corrected_smoke.csv"
  LOG_DIR="$OUT_DIR/logs_corrected_smoke"
  mkdir -p "$LOG_DIR"
  echo "[smoke mode] 3 defenders × 3 seeds = 9 games"
fi

GAME_TIMEOUT_S=90
TOTAL=$(( ${#DEFENDERS[@]} * ${#SEEDS[@]} ))
COUNTER=0
START_TS=$(date +%s)

echo "=== pm46 v2 ABS-solo CORRECTED matrix ==="
echo "host: $(hostname)  python: $($PY --version 2>&1)  total games: $TOTAL"
echo "csv:  $CSV"
echo "logs: $LOG_DIR/"
echo

echo "defender,seed,outcome,first_eat_tick,total_caps_eaten,a_died_within_3,a_total_deaths,score,wall_s" > "$CSV"

for DEF in "${DEFENDERS[@]}"; do
  for SEED in "${SEEDS[@]}"; do
    COUNTER=$(( COUNTER + 1 ))
    LAY="RANDOM${SEED}"
    LOG="$LOG_DIR/${DEF}_seed${SEED}.log"
    T0=$(date +%s)

    ( cd minicontest && timeout $GAME_TIMEOUT_S env \
        PYTHONHASHSEED=0 \
        ABS_REACH_EXIT=0 \
        ABS_FIRST_CAP_TRACE=0 \
        "$PY" ../experiments/rc_tempo/pm45_single_game.py \
          -r zoo_reflex_rc_tempo_abs_solo -b "$DEF" -l "$LAY" -n 1 -q \
        > "$LOG" 2>&1 ) || true

    WALL=$(( $(date +%s) - T0 ))

    # Parse cap-eat events.
    EAT_LINES=$(grep -c '\[ABS_CAP_EATEN\]' "$LOG" 2>/dev/null || echo 0)
    FIRST_EAT_LINE=$(grep '\[ABS_CAP_EATEN\]' "$LOG" 2>/dev/null | head -1 || true)
    if [ -n "$FIRST_EAT_LINE" ]; then
      FIRST_EAT_TICK=$(echo "$FIRST_EAT_LINE" | sed -n 's/.*tick=\([0-9]*\).*/\1/p')
    else
      FIRST_EAT_TICK=""
    fi

    # Parse A respawn events.
    DIED_LINES=$(grep '\[ABS_A_DIED\]' "$LOG" 2>/dev/null || true)
    A_TOTAL_DEATHS=$(echo "$DIED_LINES" | grep -c '\[ABS_A_DIED\]' || echo 0)

    # a_died_within_3: any death tick within 3 of first eat tick.
    A_DIED_WITHIN_3="false"
    if [ -n "$FIRST_EAT_TICK" ] && [ -n "$DIED_LINES" ]; then
      while IFS= read -r dline; do
        [ -z "$dline" ] && continue
        DTICK=$(echo "$dline" | sed -n 's/.*tick=\([0-9]*\).*/\1/p')
        if [ -n "$DTICK" ] && [ "$DTICK" -ge "$FIRST_EAT_TICK" ] && \
           [ "$((DTICK - FIRST_EAT_TICK))" -le 3 ]; then
          A_DIED_WITHIN_3="true"
          break
        fi
      done <<< "$DIED_LINES"
    fi

    # Outcome classification.
    SCORE_LINE=$(grep -E "Average Score|Score:|red team won|blue team won" "$LOG" 2>/dev/null | head -1 || true)
    if [ -z "$SCORE_LINE" ]; then
      OUTCOME="timeout"
      SCORE=""
    else
      SCORE=$(echo "$SCORE_LINE" | sed -n 's/.*Score: *\(-*[0-9]*\).*/\1/p')
      [ -z "$SCORE" ] && SCORE=""
      if [ "$EAT_LINES" -gt 0 ]; then
        if [ "$A_DIED_WITHIN_3" = "true" ]; then
          OUTCOME="eat_died"
        else
          OUTCOME="eat_alive"
        fi
      else
        if [ "$A_TOTAL_DEATHS" -gt 0 ]; then
          OUTCOME="no_eat_died"
        else
          OUTCOME="no_eat_alive"
        fi
      fi
    fi

    echo "$DEF,$SEED,$OUTCOME,$FIRST_EAT_TICK,$EAT_LINES,$A_DIED_WITHIN_3,$A_TOTAL_DEATHS,$SCORE,$WALL" >> "$CSV"

    ELAPSED=$(( $(date +%s) - START_TS ))
    printf "[%3d/%3d] %-32s seed=%2d  outcome=%-12s eats=%-2s deaths=%-2s wall=%2ds  total=%5ds\n" \
      "$COUNTER" "$TOTAL" "$DEF" "$SEED" "${OUTCOME:-NA}" "${EAT_LINES:-0}" "${A_TOTAL_DEATHS:-0}" "$WALL" "$ELAPSED"
  done
done

ELAPSED=$(( $(date +%s) - START_TS ))
echo
echo "=== matrix complete: $TOTAL games in ${ELAPSED}s ==="

# Per-defender summary.
echo
echo "--- summary (cap_eat_alive % over seeds) ---"
echo "defender                          eat_alive  eat_died  no_eat_alive  no_eat_died  timeout  total"
for DEF in "${DEFENDERS[@]}"; do
  EA=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="eat_alive"   {n++} END {print n+0}' "$CSV")
  ED=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="eat_died"    {n++} END {print n+0}' "$CSV")
  NA=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="no_eat_alive"{n++} END {print n+0}' "$CSV")
  ND=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="no_eat_died" {n++} END {print n+0}' "$CSV")
  TO=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="timeout"     {n++} END {print n+0}' "$CSV")
  T=$(awk -F, -v d="$DEF" 'NR>1 && $1==d                       {n++} END {print n+0}' "$CSV")
  printf "%-32s %4d   %4d   %4d   %4d   %4d   %4d\n" "$DEF" "$EA" "$ED" "$NA" "$ND" "$TO" "$T"
done

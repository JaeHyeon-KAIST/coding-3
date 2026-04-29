#!/usr/bin/env bash
# pm46 v2 recovery — 2 invalid defenders re-measured.
#
# Replaces:
#   - zoo_belief (helper module, no createTeam) → zoo_reflex_A1_T5 (Tier-A
#     belief-using agent that actually has createTeam)
#   - zoo_hybrid_mcts_reflex (90s timeout under default 0.8s/turn budget) →
#     same agent BUT with ZOO_MCTS_MOVE_BUDGET=0.05 env var (50ms/turn,
#     well under 1s assignment limit) + 240s game timeout (was 90s)
#
# Output appended to existing CSVs (replaces zoo_belief rows; adds A1_T5 +
# corrected hybrid_mcts rows).

set -u

cd "$(dirname "$0")/../.." || { echo "FAIL: cannot cd to repo root"; exit 1; }
ROOT="$(pwd)"
PY="$ROOT/.venv/bin/python"

OUT_DIR="$ROOT/experiments/results/pm46_v2"
LOG_DIR_BASE="$OUT_DIR/logs_recovery"
mkdir -p "$LOG_DIR_BASE"

CAPX_CSV="$OUT_DIR/capx_recovery.csv"
ABS_CSV="$OUT_DIR/abs_recovery.csv"

echo "defender,seed,outcome,first_eat_tick,total_caps_eaten,a_died_within_3,a_total_deaths,score,wall_s" > "$CAPX_CSV"
echo "defender,seed,outcome,first_eat_tick,total_caps_eaten,a_died_within_3,a_total_deaths,score,wall_s" > "$ABS_CSV"

# 2 measurement sets × 2 agents × 30 seeds = 120 games.
SEEDS=()
for i in $(seq 1 30); do SEEDS+=("$i"); done

DEFENDERS=(zoo_reflex_A1_T5 zoo_hybrid_mcts_reflex)
AGENTS=(capx abs)

run_game() {
  local AGENT_KIND=$1     # capx or abs
  local DEF=$2
  local SEED=$3
  local LAY="RANDOM${SEED}"

  local LOG_DIR="$LOG_DIR_BASE/${AGENT_KIND}"
  mkdir -p "$LOG_DIR"
  local LOG="$LOG_DIR/${DEF}_seed${SEED}.log"

  local AGENT_R EAT_PAT DIED_PAT TIMEOUT_S ENV_EXTRA

  if [ "$AGENT_KIND" = "capx" ]; then
    AGENT_R="zoo_reflex_rc_tempo_capx_solo"
    EAT_PAT='\[CAPX_CAP_EATEN\]'
    DIED_PAT='\[CAPX_A_DIED\]'
    ENV_EXTRA="CAPX_MIN_MARGIN=0"
  else
    AGENT_R="zoo_reflex_rc_tempo_abs_solo"
    EAT_PAT='\[ABS_CAP_EATEN\]'
    DIED_PAT='\[ABS_A_DIED\]'
    ENV_EXTRA="ABS_REACH_EXIT=0 ABS_FIRST_CAP_TRACE=0"
  fi

  if [ "$DEF" = "zoo_hybrid_mcts_reflex" ]; then
    TIMEOUT_S=240
    ENV_EXTRA="$ENV_EXTRA ZOO_MCTS_MOVE_BUDGET=0.05"
  else
    TIMEOUT_S=90
  fi

  local T0=$(date +%s)
  ( cd minicontest && timeout $TIMEOUT_S env PYTHONHASHSEED=0 $ENV_EXTRA \
      "$PY" ../experiments/rc_tempo/pm45_single_game.py \
        -r "$AGENT_R" -b "$DEF" -l "$LAY" -n 1 -q \
      > "$LOG" 2>&1 ) || true
  local WALL=$(( $(date +%s) - T0 ))

  local EAT_LINES
  EAT_LINES=$(grep -c "$EAT_PAT" "$LOG" 2>/dev/null)
  EAT_LINES=${EAT_LINES:-0}; EAT_LINES=${EAT_LINES//[!0-9]/}
  [ -z "$EAT_LINES" ] && EAT_LINES=0

  local DIED_RAW
  DIED_RAW=$(grep "$DIED_PAT" "$LOG" 2>/dev/null || true)
  local A_TOTAL_DEATHS
  if [ -z "$DIED_RAW" ]; then
    A_TOTAL_DEATHS=0
  else
    A_TOTAL_DEATHS=$(printf '%s\n' "$DIED_RAW" | grep -c "$DIED_PAT")
    A_TOTAL_DEATHS=${A_TOTAL_DEATHS:-0}; A_TOTAL_DEATHS=${A_TOTAL_DEATHS//[!0-9]/}
    [ -z "$A_TOTAL_DEATHS" ] && A_TOTAL_DEATHS=0
  fi

  local FIRST_EAT_TICK=""
  local FIRST_HEAD
  FIRST_HEAD=$(grep "$EAT_PAT" "$LOG" 2>/dev/null | head -1 || true)
  if [ -n "$FIRST_HEAD" ]; then
    FIRST_EAT_TICK=$(echo "$FIRST_HEAD" | sed -n 's/.*tick=\([0-9]*\).*/\1/p')
  fi

  local A_DIED_WITHIN_3="false"
  if [ -n "$FIRST_EAT_TICK" ] && [ -n "$DIED_RAW" ]; then
    while IFS= read -r dline; do
      [ -z "$dline" ] && continue
      local DTICK
      DTICK=$(echo "$dline" | sed -n 's/.*tick=\([0-9]*\).*/\1/p')
      if [ -n "$DTICK" ] && [ "$DTICK" -le "$FIRST_EAT_TICK" ] && \
         [ "$((FIRST_EAT_TICK - DTICK))" -le 3 ]; then
        A_DIED_WITHIN_3="true"
        break
      fi
    done <<< "$DIED_RAW"
  fi

  local SCORE_LINE OUTCOME SCORE
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

  local OUT_CSV
  if [ "$AGENT_KIND" = "capx" ]; then
    OUT_CSV="$CAPX_CSV"
  else
    OUT_CSV="$ABS_CSV"
  fi
  echo "$DEF,$SEED,$OUTCOME,$FIRST_EAT_TICK,$EAT_LINES,$A_DIED_WITHIN_3,$A_TOTAL_DEATHS,$SCORE,$WALL" >> "$OUT_CSV"

  printf "[%-4s vs %-22s seed=%2d] outcome=%-12s eats=%-2s deaths=%-2s wall=%3ds\n" \
    "$AGENT_KIND" "$DEF" "$SEED" "${OUTCOME:-NA}" "${EAT_LINES:-0}" "${A_TOTAL_DEATHS:-0}" "$WALL"
}

START_TS=$(date +%s)
TOTAL=0
for AK in "${AGENTS[@]}"; do
  for DEF in "${DEFENDERS[@]}"; do
    for SEED in "${SEEDS[@]}"; do
      run_game "$AK" "$DEF" "$SEED"
      TOTAL=$(( TOTAL + 1 ))
    done
  done
done

ELAPSED=$(( $(date +%s) - START_TS ))
echo
echo "=== recovery complete: $TOTAL games in ${ELAPSED}s ==="
echo
echo "--- summary ---"
for AK in "${AGENTS[@]}"; do
  if [ "$AK" = "capx" ]; then C="$CAPX_CSV"; else C="$ABS_CSV"; fi
  echo "[$AK]"
  for DEF in "${DEFENDERS[@]}"; do
    EA=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="eat_alive" {n++} END {print n+0}' "$C")
    ED=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="eat_died" {n++} END {print n+0}' "$C")
    NA=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="no_eat_alive" {n++} END {print n+0}' "$C")
    ND=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="no_eat_died" {n++} END {print n+0}' "$C")
    TO=$(awk -F, -v d="$DEF" 'NR>1 && $1==d && $3=="timeout" {n++} END {print n+0}' "$C")
    T=$(awk -F, -v d="$DEF" 'NR>1 && $1==d {n++} END {print n+0}' "$C")
    printf "  %-32s ea=%2d ed=%2d na=%2d nd=%2d to=%2d / %d\n" "$DEF" "$EA" "$ED" "$NA" "$ND" "$TO" "$T"
  done
done

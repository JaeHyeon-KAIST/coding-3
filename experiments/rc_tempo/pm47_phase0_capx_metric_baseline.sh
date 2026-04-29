#!/usr/bin/env bash
# pm47 Phase 0.5 — submission cap-eat-alive matrix (CAPX-comparable metric)
#
# Measure 20200492.py via submission_capsule_logger.py wrapper against the
# 17-defender zoo. Captures CAPX-equivalent metric (eat_alive / eat_died /
# died_pre_eat / no_eat_alive) for direct comparison with CAPX results.
#
# Submission behavior is 100% unchanged (verified: identical score with/
# without wrapper). Wrapper only adds [SUBM_CAP_EATEN] / [SUBM_A_DIED]
# print markers.
#
# Usage:
#   bash experiments/rc_tempo/pm47_phase0_capx_metric_baseline.sh           # 17 def x 10 seed
#   SEEDS_PER_DEF=30 bash experiments/rc_tempo/pm47_phase0_capx_metric_baseline.sh
#   SMOKE=1 bash experiments/rc_tempo/pm47_phase0_capx_metric_baseline.sh   # 5 def x 5 seed
#
# Output: experiments/results/pm47_phase0/submission_capx_metric_n{N}.csv
# Columns: defender,seed,outcome,first_eat_tick,total_caps_eaten,a_total_deaths,score,wall_s
# outcome: eat_alive (cap eaten + alive at eat) | eat_died (cap eaten + died <=3 ticks)
#          | died_pre_eat (no cap, A died) | no_eat_alive (no cap, A alive at end)

set -u

cd "$(dirname "$0")/../.." || { echo "FAIL: cannot cd to repo root"; exit 1; }
ROOT="$(pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "FAIL: missing $PY"; exit 1; }

OUT="$ROOT/experiments/results/pm47_phase0"
mkdir -p "$OUT/logs_capx_metric"

SEEDS_PER_DEF=${SEEDS_PER_DEF:-10}
GAME_TIMEOUT=${GAME_TIMEOUT:-90}

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

if [ "${SMOKE:-0}" = "1" ]; then
  DEFENDERS=(zoo_dummy zoo_reflex_aggressive zoo_reflex_tuned zoo_reflex_capsule baseline)
  SEEDS_PER_DEF=${SEEDS_PER_DEF:-5}
  CSV_NAME=submission_capx_metric_smoke.csv
else
  DEFENDERS=("${ALL_DEFENDERS[@]}")
  CSV_NAME=submission_capx_metric_n${SEEDS_PER_DEF}.csv
fi

CSV="$OUT/$CSV_NAME"
echo "defender,seed,outcome,first_eat_tick,total_caps_eaten,a_total_deaths,score,wall_s" > "$CSV"

HYBRID_MCTS_ENV='ZOO_MCTS_MOVE_BUDGET=0.05'

global_t0=$(date +%s)
total_games=$((${#DEFENDERS[@]} * SEEDS_PER_DEF))
done_games=0

echo "=== pm47 phase 0.5 submission cap-eat-alive matrix ==="
echo "defenders: ${#DEFENDERS[@]} | seeds: $SEEDS_PER_DEF | total: $total_games"
echo "csv: $CSV"
echo ""

for def in "${DEFENDERS[@]}"; do
  d_t0=$(date +%s)
  d_alive=0; d_died=0; d_no_eat_died=0; d_no_eat_alive=0
  for seed in $(seq 1 $SEEDS_PER_DEF); do
    log="$OUT/logs_capx_metric/${def}_seed${seed}.log"
    g_t0=$(date +%s)
    cd "$ROOT/minicontest"

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
      -r submission_capsule_logger -b "$def" -l "RANDOM$seed" -n 1 -q \
      > "$log" 2>&1 || true
    cd "$ROOT"
    wall=$(($(date +%s) - g_t0))

    # Parse cap events + deaths
    first_eat_tick=$(grep '\[SUBM_CAP_EATEN\]' "$log" | head -1 \
                     | grep -oE 'tick=[0-9-]+' | head -1 | cut -d= -f2)
    total_caps=$(grep -c '\[SUBM_CAP_EATEN\]' "$log")
    deaths=$(grep -c '\[SUBM_A_DIED\]' "$log")
    score=$(grep -oE 'Average Score: -?[0-9.]+' "$log" | head -1 | grep -oE '\-?[0-9.]+' | head -1)
    [ -z "$score" ] && score=0

    # Outcome classification (CAPX-equivalent semantics)
    # eat_alive: cap eaten + no death in [first_eat_tick-3, first_eat_tick] window
    # eat_died: cap eaten + death within 3 ticks of first eat
    # died_pre_eat: no cap eaten, but A died at least once
    # no_eat_alive: no cap eaten, no death (A oscillated/timeout)
    if [ -n "$first_eat_tick" ]; then
      # check for death in window [first_eat_tick-3, first_eat_tick] (timeleft decreases)
      death_near_eat=0
      while IFS= read -r dline; do
        dt=$(echo "$dline" | grep -oE 'tick=[0-9-]+' | head -1 | cut -d= -f2)
        if [ -n "$dt" ]; then
          # death tick (timeleft) should be in [first_eat_tick-3, first_eat_tick] = died at or just after eat
          # since timeleft decreases: dt < first_eat_tick && dt >= first_eat_tick - 3
          if [ "$dt" -lt "$first_eat_tick" ] && [ "$dt" -ge "$((first_eat_tick - 3))" ]; then
            death_near_eat=1
            break
          fi
        fi
      done < <(grep '\[SUBM_A_DIED\]' "$log")
      if [ "$death_near_eat" = "1" ]; then
        outcome=eat_died; d_died=$((d_died + 1))
      else
        outcome=eat_alive; d_alive=$((d_alive + 1))
      fi
    elif [ "$deaths" -gt 0 ]; then
      outcome=died_pre_eat; d_no_eat_died=$((d_no_eat_died + 1))
    else
      outcome=no_eat_alive; d_no_eat_alive=$((d_no_eat_alive + 1))
    fi

    echo "$def,$seed,$outcome,${first_eat_tick:-},$total_caps,$deaths,$score,$wall" >> "$CSV"
    done_games=$((done_games + 1))
  done
  d_wall=$(($(date +%s) - d_t0))
  echo "[$done_games/$total_games] $def: alive=$d_alive eat_died=$d_died no_eat_died=$d_no_eat_died no_eat_alive=$d_no_eat_alive wall=${d_wall}s"
done

echo ""
echo "=== summary ==="
total_alive=$(awk -F, 'NR>1 && $3=="eat_alive"' "$CSV" | wc -l | tr -d ' ')
total_eat_died=$(awk -F, 'NR>1 && $3=="eat_died"' "$CSV" | wc -l | tr -d ' ')
total_pre_died=$(awk -F, 'NR>1 && $3=="died_pre_eat"' "$CSV" | wc -l | tr -d ' ')
total_no_eat=$(awk -F, 'NR>1 && $3=="no_eat_alive"' "$CSV" | wc -l | tr -d ' ')
echo "AGGREGATE: eat_alive=$total_alive eat_died=$total_eat_died died_pre_eat=$total_pre_died no_eat_alive=$total_no_eat total=$total_games"
echo "wall_total=$(($(date +%s) - global_t0))s | csv=$CSV"

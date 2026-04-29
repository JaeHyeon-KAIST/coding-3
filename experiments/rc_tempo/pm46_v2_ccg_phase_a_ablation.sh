#!/usr/bin/env bash
# pm46 v2 CCG — Phase A ablation matrix
# Tests S1 (A* horizon align) + S3 (_p_survive skip-current) ablation
# on the 3 weak defenders. S2 (asymmetric threat) excluded — smoke
# regression on RANDOM1 capsule (0 caps + 7 deaths). See:
# .omc/wiki/pm46-v2-ccg-improvement-consultation.md
#
# Matrix: 3 weak defenders × 30 seeds × 4 variants = 360 games
# Variants:
#   baseline    — all S-tier OFF (replicates existing capx_matrix_m0)
#   s1          — only A* horizon align ON
#   s3          — only _p_survive skip-current ON
#   s1s3        — both ON (proposed new default)
#
# Wall: ~50min/variant on Mac single-thread; ~3.5h total. Server expected <3h.

set -u

cd "$(dirname "$0")/../.." || { echo "FAIL: cannot cd to repo root"; exit 1; }
ROOT="$(pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "FAIL: missing $PY"; exit 1; }

OUT="$ROOT/experiments/results/pm46_v2/ccg_phaseA"
mkdir -p "$OUT/logs"

DEFENDERS=(zoo_reflex_capsule zoo_reflex_tuned zoo_reflex_aggressive)
SEEDS=$(seq 1 30)

# variant=name | env-vars (space separated)
VARIANTS=(
  "baseline|CAPX_ASTAR_HORIZON=999 CAPX_ASYMMETRIC_THREAT=0 CAPX_PSURVIVE_SKIP_CURRENT=0"
  "s1|CAPX_ASTAR_HORIZON=8 CAPX_ASYMMETRIC_THREAT=0 CAPX_PSURVIVE_SKIP_CURRENT=0"
  "s3|CAPX_ASTAR_HORIZON=999 CAPX_ASYMMETRIC_THREAT=0 CAPX_PSURVIVE_SKIP_CURRENT=1"
  "s1s3|CAPX_ASTAR_HORIZON=8 CAPX_ASYMMETRIC_THREAT=0 CAPX_PSURVIVE_SKIP_CURRENT=1"
)

GAME_TIMEOUT=${GAME_TIMEOUT:-90}

global_t0=$(date +%s)

for entry in "${VARIANTS[@]}"; do
  name="${entry%%|*}"
  envs="${entry#*|}"
  csv="$OUT/${name}.csv"
  echo "defender,seed,outcome,first_eat_tick,total_caps_eaten,a_total_deaths,wall_s" > "$csv"
  v_t0=$(date +%s)
  echo "[$name] starting | env: $envs"

  for def in "${DEFENDERS[@]}"; do
    for seed in $SEEDS; do
      log="$OUT/logs/${name}_${def}_seed${seed}.log"
      g_t0=$(date +%s)
      cd "$ROOT/minicontest"
      # shellcheck disable=SC2086
      timeout "$GAME_TIMEOUT" env $envs CAPX_EXIT_ON_EAT=0 PYTHONHASHSEED=0 \
        "$PY" "$ROOT/experiments/rc_tempo/pm45_single_game.py" \
        -r zoo_reflex_rc_tempo_capx_solo -b "$def" -l "RANDOM$seed" -n 1 -q \
        > "$log" 2>&1 || true
      cd "$ROOT"
      wall=$(($(date +%s) - g_t0))

      eat_tick=$(grep '\[CAPX_CAP_EATEN\]' "$log" | head -1 \
                 | grep -oE 'tick=[0-9]+' | head -1 | cut -d= -f2)
      total=$(grep -c '\[CAPX_CAP_EATEN\]' "$log")
      deaths=$(grep -c '\[CAPX_A_DIED\]' "$log")

      if [ -n "$eat_tick" ]; then
        outcome="eat_alive"
      elif [ "$deaths" -gt 0 ]; then
        outcome="no_eat_died"
      else
        outcome="no_eat_alive"
      fi
      echo "$def,$seed,$outcome,${eat_tick:-},$total,$deaths,$wall" >> "$csv"
    done
  done

  v_wall=$(($(date +%s) - v_t0))
  # quick aggregate
  alive=$(awk -F, 'NR>1 && $3=="eat_alive"' "$csv" | wc -l | tr -d ' ')
  died=$(awk -F, 'NR>1 && $3=="no_eat_died"' "$csv" | wc -l | tr -d ' ')
  total_g=$(awk -F, 'NR>1' "$csv" | wc -l | tr -d ' ')
  echo "[$name] DONE — wall=${v_wall}s | eat_alive=${alive}/${total_g} | no_eat_died=${died}/${total_g}"
done

echo "ALL VARIANTS DONE — total wall=$(($(date +%s) - global_t0))s | csvs in $OUT/"

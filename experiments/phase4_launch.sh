#!/usr/bin/env bash
# phase4_launch.sh — Launch Phase 4 round-robin tournament.
#
# Usage:
#   bash experiments/phase4_launch.sh [seed] [workers]
#
# Defaults: seed=42, workers=16 (server-optimised).
#
# Outputs CSV to experiments/artifacts/phase4_tournament/<timestamp>.csv.
# Expected wall: ~6 min on server (16 workers), ~6-12h on Mac.

set -euo pipefail

SEED=${1:-42}
WORKERS=${2:-16}
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT"

# Parse agent list from phase4_agents.txt (strip comments + blanks).
AGENTS=$(grep -E '^[a-zA-Z0-9_]' experiments/phase4_agents.txt | tr '\n' ' ')
if [ -z "$AGENTS" ]; then
  echo "[phase4] ERROR: no agents parsed from phase4_agents.txt" >&2
  exit 1
fi

N=$(echo "$AGENTS" | wc -w)
OUT_DIR="experiments/artifacts/phase4_tournament"
mkdir -p "$OUT_DIR"
TS=$(date +%Y%m%d-%H%M%S)
OUT="$OUT_DIR/phase4_${TS}.csv"
LOG="logs/phase4_${TS}.log"
mkdir -p logs

echo "[phase4] Launching round-robin: N=$N agents, seed=$SEED, workers=$WORKERS"
echo "[phase4] Output: $OUT"
echo "[phase4] Log: $LOG"
echo ""

.venv/bin/python experiments/tournament.py \
    --agents $AGENTS \
    --layouts defaultCapture \
    --seeds $SEED \
    --games-per-pair 1 \
    --workers "$WORKERS" \
    --out "$OUT" 2>&1 | tee "$LOG"

echo ""
echo "[phase4] Done. CSV: $OUT"
echo "[phase4] Next: run experiments/select_top4.py or manual analysis on CSV."

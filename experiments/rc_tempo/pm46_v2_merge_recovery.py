"""pm46 v2 — merge recovery rows into main CSVs.

For each main CSV (capx_matrix_m0, abs_baseline_corrected_clean):
  1. Remove rows matching defenders being replaced (zoo_belief, zoo_hybrid_mcts_reflex).
  2. Append corresponding recovery rows.
  3. Add zoo_reflex_A1_T5 rows from recovery (replaces zoo_belief in inventory).

Output: *_merged.csv (preserves originals).
"""
from __future__ import annotations
import csv
import sys
from pathlib import Path

ROOT = Path("/Users/jaehyeon/KAIST/26 Spring/인공지능개론/coding 3")
RES = ROOT / "experiments/results/pm46_v2"

CAPX_MAIN = RES / "capx_matrix_m0.csv"
ABS_MAIN = RES / "abs_baseline_corrected_clean.csv"
CAPX_REC = RES / "capx_recovery.csv"
ABS_REC = RES / "abs_recovery.csv"

CAPX_OUT = RES / "capx_matrix_m0_merged.csv"
ABS_OUT = RES / "abs_baseline_corrected_merged.csv"

# Defenders to REPLACE in main with recovery rows.
REPLACE = {"zoo_belief", "zoo_hybrid_mcts_reflex"}

def merge(main_path: Path, rec_path: Path, out_path: Path) -> None:
    rows_main = []
    fieldnames = None
    with open(main_path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        fieldnames = r.fieldnames
        for row in r:
            if row['defender'] in REPLACE:
                continue  # drop
            rows_main.append(row)

    rows_rec = []
    with open(rec_path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            rows_rec.append(row)

    merged = rows_main + rows_rec
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(merged)

    print(f"{main_path.name}: kept {len(rows_main)} from main + {len(rows_rec)} from recovery = {len(merged)} -> {out_path.name}")


merge(CAPX_MAIN, CAPX_REC, CAPX_OUT)
merge(ABS_MAIN, ABS_REC, ABS_OUT)

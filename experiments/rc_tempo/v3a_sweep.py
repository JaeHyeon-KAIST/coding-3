#!/usr/bin/env python3
"""v3a hyperparameter sweep: run multiple variants, compare post-trigger metrics.

Variants configured via env vars read by zoo_reflex_rc_tempo_beta_v3a:
    V3A_MARGIN          — Voronoi safety margin (0=simultaneous OK, 1=strict, 2=buffer)
    V3A_RISK_THRESHOLD  — max risk for food to be eligible for slack detour
    V3A_SLACK_MIN       — min slack to trigger food DP
    V3A_MAX_FOOD        — cap on food candidates (DP is 2^n)
    V3A_GREEDY_FALLBACK — on unreachable, try greedy 1-step toward capsule
    V3A_TRIGGER_MODE    — "strict" (==1) | "loose" (>=1)
    V3A_STICKY_RADIUS   — sticky commit radius

Usage:
    .venv/bin/python experiments/rc_tempo/v3a_sweep.py \\
        --games-per-cell 5 --workers 6 --max-moves 600 \\
        --out-dir /tmp/v3a_sweep/

pm32 hardening (Step C.1):
    --variants-file <txt>     read variant names from file (one per line)
    --layouts-file <txt>      read layout names from file (one per line)
    --validate-csv            walk CSVs in --out-dir, check column-set parity,
                              report partial rows; refuses destructive ops
                              without --allow-truncate
    --allow-truncate          allow --validate-csv to drop trailing partial
                              rows after writing .bak (refuses to drop crashed=1)
    Heartbeat log + per-variant try/except + wall_summary.csv + disk pre-check
    are unconditional.
"""
from __future__ import annotations
import argparse
import csv
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SMOKE = HERE / 'phase1_smoke.py'
VENV_PYTHON = REPO / '.venv' / 'bin' / 'python'

# Composite ranking: single source of truth
sys.path.insert(0, str(HERE))
from composite import compute_score  # noqa: E402

# Field set for --validate-csv (matches phase1_smoke.FIELDS)
from phase1_smoke import FIELDS as PHASE1_FIELDS  # noqa: E402


# Variant definitions: name → env override dict (str agent name tag for v3b)
# Marker '__BETA_AGENT__': use zoo_reflex_rc_tempo_beta (no env vars)
# Marker dict with '__BETA__': use zoo_reflex_rc_tempo_beta WITH env overrides
# Marker dict with '__V3B__': use zoo_reflex_rc_tempo_beta_v3b
# Marker dict with '__RETRO__': use zoo_reflex_rc_tempo_beta_retro
# else: use zoo_reflex_rc_tempo_beta_v3a with given env dict
VARIANTS = {
    # === Reference ===
    'beta_v2d': '__BETA_AGENT__',  # pm30 committed β (endpoint-only Voronoi)

    # === β safety sweep (pm31 S3: reduce distant die) ===
    'beta_abort3':      {'__BETA__': '1', 'BETA_ABORT_DIST': '3'},
    'beta_abort4':      {'__BETA__': '1', 'BETA_ABORT_DIST': '4'},
    'beta_slack2':      {'__BETA__': '1', 'BETA_CHASE_SLACK': '2'},
    'beta_slack3':      {'__BETA__': '1', 'BETA_CHASE_SLACK': '3'},
    'beta_path5':       {'__BETA__': '1', 'BETA_PATH_ABORT_RATIO': '5'},
    'beta_path4':       {'__BETA__': '1', 'BETA_PATH_ABORT_RATIO': '4'},
    'beta_combo_a':     {'__BETA__': '1', 'BETA_ABORT_DIST': '3',
                          'BETA_CHASE_SLACK': '2'},
    'beta_combo_b':     {'__BETA__': '1', 'BETA_ABORT_DIST': '4',
                          'BETA_CHASE_SLACK': '2',
                          'BETA_PATH_ABORT_RATIO': '5'},
    'beta_safe':        {'__BETA__': '1', 'BETA_ABORT_DIST': '3',
                          'BETA_CHASE_SLACK': '2',
                          'BETA_PATH_ABORT_RATIO': '6'},

    # === β_retro (retrograde tablebase) ===
    'beta_retro':         {'__RETRO__': '1'},                           # V+1 + V=0 far
    'beta_retro_never':   {'__RETRO__': '1', 'BETA_RETRO_DRAW_MODE': 'never'},
    'beta_retro_always':  {'__RETRO__': '1', 'BETA_RETRO_DRAW_MODE': 'always'},
    'beta_retro_far3':    {'__RETRO__': '1', 'BETA_RETRO_DRAW_MODE': 'far',
                            'BETA_RETRO_DRAW_MIN_DIST': '3'},
    'beta_retro_far8':    {'__RETRO__': '1', 'BETA_RETRO_DRAW_MODE': 'far',
                            'BETA_RETRO_DRAW_MIN_DIST': '8'},

    # === v3a (A* + Voronoi + Slack DP) ===
    'v3a_default': {},  # margin=1, full-path Voronoi, strict trigger
    'v3a_loose': {'V3A_TRIGGER_MODE': 'loose'},

    # NEW: endpoint-only Voronoi (match β v2d check style)
    'v3a_endpoint': {'V3A_VORONOI_MODE': 'endpoint'},
    'v3a_endpoint_loose': {'V3A_VORONOI_MODE': 'endpoint',
                            'V3A_TRIGGER_MODE': 'loose'},
    'v3a_endpoint_rt10': {'V3A_VORONOI_MODE': 'endpoint',
                           'V3A_RISK_THRESHOLD': '10'},
    'v3a_endpoint_combo': {'V3A_VORONOI_MODE': 'endpoint',
                            'V3A_TRIGGER_MODE': 'loose',
                            'V3A_RISK_THRESHOLD': '10',
                            'V3A_SLACK_MIN': '1'},

    # AP-only Voronoi (check only articulation points + target)
    'v3a_ap': {'V3A_VORONOI_MODE': 'ap'},
    'v3a_ap_loose': {'V3A_VORONOI_MODE': 'ap', 'V3A_TRIGGER_MODE': 'loose'},

    # last_k tail check
    'v3a_lastk': {'V3A_VORONOI_MODE': 'last_k', 'V3A_LAST_K': '5'},

    # === v3b (αβ minimax) ===
    'v3b_default': {'__V3B__': '1'},  # strict trigger, depth=6, budget=0.15
    'v3b_loose': {'__V3B__': '1', 'V3B_TRIGGER_MODE': 'loose'},
    'v3b_d4': {'__V3B__': '1', 'V3B_MAX_DEPTH': '4'},
    'v3b_d8': {'__V3B__': '1', 'V3B_MAX_DEPTH': '8', 'V3B_TIME_BUDGET': '0.3'},
    'v3b_fast': {'__V3B__': '1', 'V3B_MAX_DEPTH': '4', 'V3B_TIME_BUDGET': '0.05'},
    'v3b_loose_d4': {'__V3B__': '1', 'V3B_TRIGGER_MODE': 'loose',
                      'V3B_MAX_DEPTH': '4'},

    # === pm32 P1: env-combo crosses (5 NEW) ===
    'pm32_p1_a3_s2_p4':  {'__BETA__': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '2', 'BETA_PATH_ABORT_RATIO': '4'},
    'pm32_p1_a3_s3_p4':  {'__BETA__': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '3', 'BETA_PATH_ABORT_RATIO': '4'},
    'pm32_p1_a2_s3_p5':  {'__BETA__': '1', 'BETA_ABORT_DIST': '2', 'BETA_CHASE_SLACK': '3', 'BETA_PATH_ABORT_RATIO': '5'},
    'pm32_p1_a3_s2_p3':  {'__BETA__': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '2', 'BETA_PATH_ABORT_RATIO': '3'},
    'pm32_p1_a4_s2_p4':  {'__BETA__': '1', 'BETA_ABORT_DIST': '4', 'BETA_CHASE_SLACK': '2', 'BETA_PATH_ABORT_RATIO': '4'},

    # === pm32 Angle A: trigger gate × distance gate (20 NEW) ===
    # 4 trigger gates × 5 distance caps = 20 cells
    'pm32_aa_none_d999':       {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'none',        'BETA_TRIGGER_MAX_DIST': '999'},
    'pm32_aa_none_d12':        {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'none',        'BETA_TRIGGER_MAX_DIST': '12'},
    'pm32_aa_none_d10':        {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'none',        'BETA_TRIGGER_MAX_DIST': '10'},
    'pm32_aa_none_d8':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'none',        'BETA_TRIGGER_MAX_DIST': '8'},
    'pm32_aa_none_d6':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'none',        'BETA_TRIGGER_MAX_DIST': '6'},
    'pm32_aa_any_d999':        {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '999'},
    'pm32_aa_any_d12':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '12'},
    'pm32_aa_any_d10':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '10'},
    'pm32_aa_any_d8':          {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '8'},
    'pm32_aa_any_d6':          {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '6'},
    'pm32_aa_one_d999':        {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '999'},
    'pm32_aa_one_d12':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '12'},
    'pm32_aa_one_d10':         {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '10'},
    'pm32_aa_one_d8':          {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '8'},
    'pm32_aa_one_d6':          {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '6'},
    # 5 best-known-baseline crosses with the new gate
    'pm32_aa_p4_any_d10':      {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '10', 'BETA_PATH_ABORT_RATIO': '4'},
    'pm32_aa_p4_one_d10':      {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '10', 'BETA_PATH_ABORT_RATIO': '4'},
    'pm32_aa_s3_any_d10':      {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '10', 'BETA_CHASE_SLACK': '3'},
    'pm32_aa_s3_one_d10':      {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '10', 'BETA_CHASE_SLACK': '3'},
    'pm32_aa_combo_one_d8':    {'__BETA__': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '8',  'BETA_PATH_ABORT_RATIO': '4', 'BETA_CHASE_SLACK': '2'},

    # === pm32 Angle C: retreat-on-abort × baseline crosses (10 NEW) ===
    'pm32_ac_retreat':              {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1'},
    'pm32_ac_retreat_path4':        {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_PATH_ABORT_RATIO': '4'},
    'pm32_ac_retreat_slack3':       {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_CHASE_SLACK': '3'},
    'pm32_ac_retreat_a3':           {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_ABORT_DIST': '3'},
    'pm32_ac_retreat_combo_a':      {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '2'},
    'pm32_ac_retreat_combo_b':      {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_PATH_ABORT_RATIO': '4', 'BETA_CHASE_SLACK': '2'},
    'pm32_ac_retreat_any_d10':      {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_TRIGGER_GATE': 'any',         'BETA_TRIGGER_MAX_DIST': '10'},
    'pm32_ac_retreat_one_d10':      {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '10'},
    'pm32_ac_retreat_one_d8_p4':    {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_TRIGGER_GATE': 'exactly_one', 'BETA_TRIGGER_MAX_DIST': '8',  'BETA_PATH_ABORT_RATIO': '4'},
    'pm32_ac_retreat_safe':         {'__BETA__': '1', 'BETA_RETREAT_ON_ABORT': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '2', 'BETA_PATH_ABORT_RATIO': '6'},

    # === pm32 retro-stack: retro × safety-knob crosses (5 NEW) ===
    'pm32_rs_retro_path4':          {'__RETRO__': '1', 'BETA_PATH_ABORT_RATIO': '4'},
    'pm32_rs_retro_slack3':         {'__RETRO__': '1', 'BETA_CHASE_SLACK': '3'},
    'pm32_rs_retro_a3_s2':          {'__RETRO__': '1', 'BETA_ABORT_DIST': '3', 'BETA_CHASE_SLACK': '2'},
    'pm32_rs_retro_loose_path4':    {'__RETRO__': '1', 'BETA_RETRO_TRIGGER_MODE': 'loose', 'BETA_PATH_ABORT_RATIO': '4'},
    'pm32_rs_retro_retreat':        {'__RETRO__': '1', 'BETA_RETREAT_ON_ABORT': '1'},
}


# ---------------------------------------------------------------------------
# Heartbeat (pm32 T-O1)
# ---------------------------------------------------------------------------

class _Heartbeat:
    """Background-thread heartbeat — appends to <out_dir>/heartbeat.log every
    `interval` seconds with current variant + ETA. Stop via .stop()."""

    def __init__(self, out_dir, total_variants, interval=60):
        self.out_dir = Path(out_dir)
        self.total = total_variants
        self.interval = interval
        self.current = 0
        self.current_name = '<starting>'
        self._stop = threading.Event()
        self._t0 = time.time()
        self._thread = None
        self.path = self.out_dir / 'heartbeat.log'

    def update(self, current_idx, current_name):
        self.current = current_idx
        self.current_name = current_name

    def _loop(self):
        while not self._stop.is_set():
            try:
                elapsed = time.time() - self._t0
                done = max(self.current, 1)
                eta = elapsed / done * (self.total - done)
                msg = (
                    f"[heartbeat] {time.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"variant={self.current}/{self.total} ({self.current_name}) "
                    f"elapsed={elapsed:.0f}s eta_remaining={eta:.0f}s\n"
                )
                with self.path.open('a') as f:
                    f.write(msg)
                    f.flush()
            except Exception:
                pass
            self._stop.wait(self.interval)

    def start(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Fire one immediate heartbeat so the file exists for tail -F
        try:
            with self.path.open('a') as f:
                f.write(f"[heartbeat] {time.strftime('%Y-%m-%d %H:%M:%S')} "
                        f"sweep started, total_variants={self.total}\n")
                f.flush()
        except Exception:
            pass
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        try:
            with self.path.open('a') as f:
                f.write(f"[heartbeat] {time.strftime('%Y-%m-%d %H:%M:%S')} "
                        f"sweep ended (variants_done={self.current}/{self.total} "
                        f"wall={time.time() - self._t0:.0f}s)\n")
                f.flush()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# wall_summary.csv (pm32 T-O2)
# ---------------------------------------------------------------------------

WALL_SUMMARY_FIELDS = ['variant', 'wall_sec', 'games_completed',
                        'games_failed', 'games_per_min']


def _append_wall_summary(out_dir, name, wall_sec, csv_path):
    """Append one row per variant to <out_dir>/wall_summary.csv.

    games_completed = total rows in <name>.csv.
    games_failed = rows with crashed=1.
    games_per_min = games_completed / (wall_sec / 60), or 0 if wall<=0.
    """
    p = Path(out_dir) / 'wall_summary.csv'
    completed = 0
    failed = 0
    if csv_path.exists():
        try:
            with csv_path.open() as f:
                for r in csv.DictReader(f):
                    completed += 1
                    try:
                        if int(r.get('crashed', 0) or 0):
                            failed += 1
                    except Exception:
                        pass
        except Exception:
            pass
    gpm = completed / (wall_sec / 60.0) if wall_sec > 0 else 0.0
    first = not p.exists()
    with p.open('a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=WALL_SUMMARY_FIELDS)
        if first:
            w.writeheader()
        w.writerow({
            'variant': name,
            'wall_sec': round(wall_sec, 2),
            'games_completed': completed,
            'games_failed': failed,
            'games_per_min': round(gpm, 2),
        })
        f.flush()


# ---------------------------------------------------------------------------
# --validate-csv (pm32 T-O3)
# ---------------------------------------------------------------------------

def _validate_csvs(out_dir, allow_truncate=False):
    """Walk all *.csv in out_dir, check column-set parity vs phase1_smoke.FIELDS,
    report partial rows. Refuses destructive ops without allow_truncate.
    Refuses to drop crashed=1 rows.

    Returns 0 if everything is clean (or only fixable issues were fixed when
    allow_truncate=True), non-zero if a fatal mismatch is found.
    """
    out_dir = Path(out_dir)
    if not out_dir.exists():
        print(f"[validate] out-dir {out_dir} does not exist (nothing to validate)")
        return 0
    expected = set(PHASE1_FIELDS)
    bad = 0
    for csv_path in sorted(out_dir.glob('*.csv')):
        # Skip wall_summary.csv (different schema)
        if csv_path.name == 'wall_summary.csv':
            continue
        try:
            with csv_path.open() as f:
                reader = csv.reader(f)
                try:
                    header = next(reader)
                except StopIteration:
                    print(f"[validate] {csv_path.name}: empty (no header), SKIP")
                    continue
            actual = set(header)
            missing = expected - actual
            extra = actual - expected
            if missing or extra:
                print(f"[validate] FATAL column-set mismatch in {csv_path.name}:")
                if missing:
                    print(f"  MISSING: {sorted(missing)}")
                if extra:
                    print(f"  EXTRA:   {sorted(extra)}")
                print(f"  Suggestion: delete {csv_path.name} and re-run from "
                      f"scratch (schema migrated), OR migrate the CSV to add "
                      f"missing columns. Fatal — exiting non-zero.")
                bad += 1
                continue
            # Detect partial rows by re-reading via DictReader with strict
            # dialect handling. A truly-partial trailing row will trip the
            # field-count check below.
            partial_count = 0
            crashed_partial = 0
            with csv_path.open() as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                expected_n = len(header)
                rows = list(reader)
            for i, row in enumerate(rows):
                if len(row) != expected_n:
                    partial_count += 1
                    # Try to identify if this looked like a crashed=1 row
                    # before truncation
                    try:
                        crashed_idx = header.index('crashed')
                        if crashed_idx < len(row) and str(row[crashed_idx]) == '1':
                            crashed_partial += 1
                    except (ValueError, IndexError):
                        pass
            if partial_count == 0:
                print(f"[validate] {csv_path.name}: OK ({len(rows)} rows)")
                continue
            print(f"[validate] {csv_path.name}: {partial_count} partial trailing "
                  f"row(s) ({crashed_partial} would-be crashed=1)")
            if not allow_truncate:
                print(f"  --allow-truncate not set; leaving CSV unchanged.")
                continue
            if crashed_partial > 0:
                print(f"  REFUSING to drop partial rows because some have "
                      f"crashed=1 (signal-bearing). Operator must inspect.")
                bad += 1
                continue
            # Safe to truncate: backup, then rewrite without partial rows
            bak = csv_path.with_suffix(csv_path.suffix + '.bak')
            shutil.copy2(csv_path, bak)
            with csv_path.open('w', newline='') as f:
                w = csv.writer(f)
                w.writerow(header)
                for row in rows:
                    if len(row) == expected_n:
                        w.writerow(row)
            print(f"  truncated; .bak written to {bak.name}")
        except Exception as e:
            print(f"[validate] {csv_path.name}: ERROR {type(e).__name__}: {e}")
            bad += 1
    return 0 if bad == 0 else 2


# ---------------------------------------------------------------------------
# Variant dispatch + run
# ---------------------------------------------------------------------------

def _resolve_agent_and_env(name):
    """Map VARIANTS[name] → (agent_module_name, env_overrides_dict).

    Single source of truth for the 4-way marker dispatch. hth_sweep.py imports
    this so the same logic isn't duplicated in two places.
    """
    if name not in VARIANTS:
        raise KeyError(f"unknown variant: {name}")
    env_dict = VARIANTS[name]
    if env_dict == '__BETA_AGENT__':
        return ('zoo_reflex_rc_tempo_beta', {})
    if isinstance(env_dict, dict) and env_dict.get('__BETA__'):
        return ('zoo_reflex_rc_tempo_beta',
                {k: v for k, v in env_dict.items() if k != '__BETA__'})
    if isinstance(env_dict, dict) and env_dict.get('__V3B__'):
        return ('zoo_reflex_rc_tempo_beta_v3b',
                {k: v for k, v in env_dict.items() if k != '__V3B__'})
    if isinstance(env_dict, dict) and env_dict.get('__RETRO__'):
        return ('zoo_reflex_rc_tempo_beta_retro',
                {k: v for k, v in env_dict.items() if k != '__RETRO__'})
    # default: v3a
    return ('zoo_reflex_rc_tempo_beta_v3a',
            env_dict if isinstance(env_dict, dict) else {})


def run_variant(name, env_dict, agent_name, opponents, layouts, colors,
                 games_per_cell, workers, max_moves, out_csv):
    env = os.environ.copy()
    if isinstance(env_dict, dict):
        env.update(env_dict)
    cmd = [
        str(VENV_PYTHON), str(SMOKE),
        '--agent', agent_name,
        '--opponents'] + opponents + [
        '--layouts'] + layouts + [
        '--colors'] + colors + [
        '--games-per-cell', str(games_per_cell),
        '--workers', str(workers),
        '--max-moves', str(max_moves),
        '--out', str(out_csv),
    ]
    t0 = time.time()
    print(f"\n[sweep] ▶ variant={name} (env={env_dict if isinstance(env_dict, dict) else 'n/a'})",
          flush=True)
    result = subprocess.run(cmd, env=env, cwd=str(REPO))
    wall = time.time() - t0
    print(f"[sweep] ✓ variant={name} done in {wall:.1f}s (rc={result.returncode})",
          flush=True)
    return wall


def summarize_sweep(csv_paths):
    """Aggregate post-trigger metrics across all variants.

    Composite scoring delegated to composite.compute_score (single source).
    """
    rows = []
    for name, path in csv_paths.items():
        if not path.exists():
            continue
        total = {'n_total': 0, 'n_triggered': 0, 'cap_post': 0,
                 'died_post': 0, 'sum_moves': 0, 'sum_food': 0,
                 'sum_wall': 0.0, 'score_wins': 0}
        with path.open() as f:
            for r in csv.DictReader(f):
                total['n_total'] += 1
                total['sum_wall'] += float(r.get('wall_sec', 0) or 0)
                if int(r.get('triggered', 0)):
                    total['n_triggered'] += 1
                    total['cap_post'] += int(r.get('cap_eaten_post_trigger', 0))
                    total['died_post'] += int(r.get('a_died_post_trigger', 0))
                    mpt = int(r.get('moves_post_trigger', -1))
                    if mpt >= 0:
                        total['sum_moves'] += mpt
                    total['sum_food'] += int(r.get('a_food_post_trigger', 0))
                sc = int(float(r.get('score', 0) or 0))
                col = r.get('color', 'red')
                if (sc > 0 and col == 'red') or (sc < 0 and col == 'blue'):
                    total['score_wins'] += 1
        if total['n_total'] == 0:
            continue
        n_t = total['n_total']
        n_g = max(1, total['n_triggered'])
        composite = compute_score(total)  # single source of truth
        rows.append({
            'variant': name,
            'n': n_t,
            'trg%': f"{total['n_triggered']*100.0/n_t:.0f}",
            'cap%': f"{total['cap_post']*100.0/n_g:.1f}",
            'die%': f"{total['died_post']*100.0/n_g:.1f}",
            'mov_post': f"{total['sum_moves']/n_g:.0f}",
            'food_post': f"{total['sum_food']/n_g:.2f}",
            'WR%': f"{total['score_wins']*100.0/n_t:.1f}",
            'wall_s': f"{total['sum_wall']/n_t:.2f}",
            '_score': composite,
        })

    rows.sort(key=lambda r: r['_score'], reverse=True)

    # Print table
    print("\n=== v3a Sweep Comparison (post-trigger metrics; sorted by composite) ===")
    print(f"{'variant':<28} {'n':>4} {'trg%':>5} {'cap%':>6} {'die%':>6} "
          f"{'mov':>5} {'food':>6} {'WR%':>6} {'wall':>6} {'score':>7}")
    print("-" * 98)
    for r in rows:
        print(f"{r['variant']:<28} {r['n']:>4} {r['trg%']:>5} {r['cap%']:>6} "
              f"{r['die%']:>6} {r['mov_post']:>5} {r['food_post']:>6} "
              f"{r['WR%']:>6} {r['wall_s']:>6} {r['_score']:>7.1f}")


def _read_lines(path):
    """Read non-empty, non-comment lines from a text file."""
    out = []
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"file not found: {p}")
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--games-per-cell', type=int, default=5)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--max-moves', type=int, default=600)
    ap.add_argument('--out-dir', type=Path, default=Path('/tmp/v3a_sweep'))
    ap.add_argument('--opponents', nargs='+', default=[
        'baseline', 'zoo_reflex_rc82', 'zoo_reflex_rc166',
        'zoo_reflex_rc32', 'zoo_reflex_rc02', 'monster_rule_expert',
    ])
    ap.add_argument('--layouts', nargs='+',
                     default=['defaultCapture', 'distantCapture'])
    ap.add_argument('--colors', nargs='+', default=['red', 'blue'])
    ap.add_argument('--variants', nargs='+', default=None,
                    help='Subset of variants to run (default: all)')
    ap.add_argument('--variants-file', type=Path, default=None,
                    help='Read variant names from text file (one per line, '
                         '# comments allowed)')
    ap.add_argument('--layouts-file', type=Path, default=None,
                    help='Read layout names from text file (overrides --layouts)')
    ap.add_argument('--validate-csv', action='store_true',
                    help='Walk CSVs in --out-dir, check column-set parity, '
                         'report partial rows. Exits when done.')
    ap.add_argument('--allow-truncate', action='store_true',
                    help='With --validate-csv, allow dropping trailing partial '
                         'rows (writes .bak first; refuses if any partial has '
                         'crashed=1).')
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # --validate-csv: standalone mode, exits when done
    if args.validate_csv:
        rc = _validate_csvs(args.out_dir, allow_truncate=args.allow_truncate)
        sys.exit(rc)

    # Disk pre-check (Scenario 3 mitigation)
    try:
        free = shutil.disk_usage(args.out_dir).free
        if free < 1 * (2 ** 30):
            print(f"[sweep] FATAL: only {free / 2**30:.2f} GiB free in "
                  f"{args.out_dir}; need >= 1 GiB. Aborting.")
            sys.exit(3)
        print(f"[sweep] disk pre-check OK: {free / 2**30:.2f} GiB free in {args.out_dir}")
    except Exception as e:
        print(f"[sweep] WARN: disk pre-check failed ({e}); proceeding anyway.")

    # Resolve variant set
    if args.variants_file is not None:
        try:
            selected = _read_lines(args.variants_file)
        except FileNotFoundError as e:
            print(f"[sweep] {e}")
            sys.exit(2)
    elif args.variants is not None:
        selected = args.variants
    else:
        selected = list(VARIANTS.keys())

    # Resolve layouts
    if args.layouts_file is not None:
        try:
            layouts = _read_lines(args.layouts_file)
        except FileNotFoundError as e:
            print(f"[sweep] {e}")
            sys.exit(2)
    else:
        layouts = args.layouts

    # Heartbeat thread (T-O1)
    hb = _Heartbeat(args.out_dir, total_variants=len(selected))
    hb.start()

    csv_paths = {}
    total_start = time.time()
    completed = 0
    try:
        for i, name in enumerate(selected):
            if name not in VARIANTS:
                print(f"[sweep] ! unknown variant '{name}', skipping")
                continue
            hb.update(i + 1, name)
            try:
                agent, env_dict_pass = _resolve_agent_and_env(name)
            except Exception as e:
                print(f"[sweep] ! variant '{name}' resolve failed: {e}; skipping")
                continue
            csv_path = args.out_dir / f"{name}.csv"
            csv_paths[name] = csv_path
            # Per-variant try/except (one variant crash != sweep death)
            try:
                wall = run_variant(
                    name, env_dict_pass, agent,
                    args.opponents, layouts, args.colors,
                    args.games_per_cell, args.workers, args.max_moves,
                    csv_path,
                )
                _append_wall_summary(args.out_dir, name, wall, csv_path)
                completed += 1
            except Exception as e:
                print(f"[sweep] !! variant '{name}' CRASHED: "
                      f"{type(e).__name__}: {e}")
                traceback.print_exc()
                # Still try to log a wall_summary row with what we have
                try:
                    _append_wall_summary(args.out_dir, name, 0.0, csv_path)
                except Exception:
                    pass
    finally:
        hb.stop()

    total_wall = time.time() - total_start
    print(f"\n[sweep] All variants done in {total_wall:.0f}s "
          f"({completed}/{len(selected)} completed)")
    summarize_sweep(csv_paths)


if __name__ == '__main__':
    main()

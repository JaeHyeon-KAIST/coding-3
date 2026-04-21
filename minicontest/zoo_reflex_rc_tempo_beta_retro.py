# zoo_reflex_rc_tempo_beta_retro.py
# ----------------------------------
# rc-tempo β_retro — pm31 S4: Retrograde-analysis-backed capsule chase.
#
# Uses minicontest's perfect-information model + 1:1 chase subgame (triggered
# when opp_pacman_count == 1) to precompute a game-theoretic value table
# V[(me, def, turn)] at init. At runtime, looks up current state:
#
#   V = +1 → commit: following best action guarantees capsule arrival
#            regardless of defender strategy (minimax proved).
#   V = -1 → never: defender can force catch us — don't start.
#   V =  0 → draw/cycle; controlled by BETA_RETRO_DRAW_MODE:
#            'never' — treat as -1 (safety-first, default)
#            'far'   — commit if d(me,cap) >= RETRO_DRAW_MIN_DIST (user suggestion)
#            'always' — treat as +1 (aggressive, not recommended)
#
# Critical differences from β v2d / β_slack3:
#   - "Commit once or don't start" — no mid-chase abort to rc82
#   - No offensive rc82 fallback — if not committed, stays in defensive rc82
#     or waits (no going deep into opp territory)
#   - Guaranteed capsule arrival when V == +1 (modulo 1:1 assumption)
#
# Env knobs:
#   BETA_RETRO_DRAW_MODE   'never' | 'far' | 'always'   (default 'far')
#   BETA_RETRO_DRAW_MIN_DIST  int                       (default 5)
#   BETA_RETRO_TRIGGER_MODE  'strict' (==1) | 'loose' (>=1)  (default 'strict')
#   BETA_RETRO_EMERGENCY_ABORT  d_me threshold for emergency only  (default 1)
#
# ---------------------------------------------------------------------------
# Naming convention (pm32):
#
#   This file (β_retro) uses BETA_RETRO_TRIGGER_MODE with values:
#     'strict' (default; opp_pacman_count == 1 required)
#     'loose'  (opp_pacman_count >= 1)
#
#   The sister file zoo_reflex_rc_tempo_beta.py uses BETA_TRIGGER_GATE with
#   values 'none' (default; no gate) | 'any' (>=1) | 'exactly_one' (==1).
#
#   These ARE intentionally different env-var names with different defaults —
#   β_retro needs a 1:1 chase subgame for the retrograde V table to be valid;
#   β v2d historically had no opp_pacman gate at all. Reusing one var would
#   force one of the two agents to silently regress its committed default.
#   Do not consolidate the two without a behavior audit.
#
#   β_retro inherits β v2d's _choose_capsule_chase_action via the
#   `super()._chooseActionImpl(gameState)` fallthrough path (line ~268). The
#   pm32 BETA_RETREAT_ON_ABORT env var therefore also affects β_retro on
#   chase-abort fallthrough — by design (T-U3 (a) regression test).
# ---------------------------------------------------------------------------

from __future__ import annotations

import os
import sys
import time

from zoo_reflex_rc_tempo_beta import ReflexRCTempoBetaAgent
from game import Directions, Actions
from zoo_rctempo_core import (
    analyze_capsule_safety,
    build_retrograde_table,
    compute_dead_end_depth,
    find_articulation_points,
    retrograde_best_action,
)


class _V3RetroTeamState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.initialized = False
        self.game_signature = None
        self.tempo_enabled = False
        self.capsule = None
        self.a_index = None
        self.b_index = None
        self.phase = 1
        self.tick = 0
        self.V_table = {}
        self.cell_set = frozenset()
        self.metrics = {
            'init_time': 0.0,
            'v_table_size': 0,
            'v_plus_count': 0,
            'v_minus_count': 0,
            'retro_trigger_fires': 0,
            'retro_commits_plus': 0,
            'retro_commits_draw': 0,
            'retro_aborts': 0,
        }


V3_RETRO_TEAM = _V3RetroTeamState()


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return default


def _distance_fn_from_apsp(apsp, distancer_fallback):
    def _dist(a, b):
        if apsp is not None:
            d = apsp.get((a, b))
            if d is not None:
                return d
        try:
            return distancer_fallback.getDistance(a, b)
        except Exception:
            try:
                return abs(a[0] - b[0]) + abs(a[1] - b[1])
            except Exception:
                return 10 ** 9
    return _dist


def _action_toward_cell(gameState, my_pos, next_cell, legal):
    if my_pos == next_cell:
        return Directions.STOP if Directions.STOP in legal else legal[0]
    for a in legal:
        if a == Directions.STOP:
            continue
        vec = Actions.directionToVector(a)
        nx, ny = int(my_pos[0] + vec[0]), int(my_pos[1] + vec[1])
        if (nx, ny) == next_cell:
            return a
    return None


def _detect_phase(agent, gameState):
    try:
        opps = [gameState.getAgentState(i) for i in agent.getOpponents(gameState)]
        any_scared = any(int(getattr(o, 'scaredTimer', 0) or 0) > 0 for o in opps)
        caps = list(agent.getCapsules(gameState))
        if any_scared:
            return 3
        if caps:
            return 1
        return 4
    except Exception:
        return 1


def _opp_pacman_count(agent, gameState):
    try:
        cnt = 0
        for i in agent.getOpponents(gameState):
            st = gameState.getAgentState(i)
            if getattr(st, 'isPacman', False):
                cnt += 1
        return cnt
    except Exception:
        return -1


def _nearest_visible_defender(agent, gameState, my_pos, distance_fn):
    try:
        best_pos = None
        best_dist = 10 ** 9
        best_scared = 0
        for i in agent.getOpponents(gameState):
            st = gameState.getAgentState(i)
            if getattr(st, 'isPacman', False):
                continue
            opp_pos = gameState.getAgentPosition(i)
            if opp_pos is None:
                continue
            opp_pos = (int(opp_pos[0]), int(opp_pos[1]))
            d = distance_fn(my_pos, opp_pos)
            if d < best_dist:
                best_dist = d
                best_pos = opp_pos
                best_scared = int(getattr(st, 'scaredTimer', 0) or 0)
        return best_pos, best_scared
    except Exception:
        return None, 0


class ReflexRCTempoBetaRetroAgent(ReflexRCTempoBetaAgent):

    RCTEMPO_ROLE_A = 'A'
    RCTEMPO_ROLE_B = 'B'

    DRAW_MODE = os.environ.get('BETA_RETRO_DRAW_MODE', 'far')  # never | far | always
    DRAW_MIN_DIST = _env_int('BETA_RETRO_DRAW_MIN_DIST', 5)
    TRIGGER_MODE = os.environ.get('BETA_RETRO_TRIGGER_MODE', 'strict')
    EMERGENCY_ABORT = _env_int('BETA_RETRO_EMERGENCY_ABORT', 1)
    TRACE = _env_int('BETA_RETRO_TRACE', 0)  # 1 = verbose per-tick logs

    def registerInitialState(self, gameState):
        # Let β v2d do its own precompute first (sets up RCTEMPO_TEAM for
        # its chase logic which we use as fallback).
        super().registerInitialState(gameState)
        # Now set up our V3_RETRO_TEAM singleton.
        game_sig = self._compute_game_signature(gameState)
        if V3_RETRO_TEAM.initialized and V3_RETRO_TEAM.game_signature == game_sig:
            return
        V3_RETRO_TEAM.reset()
        V3_RETRO_TEAM.game_signature = game_sig
        t0 = time.time()
        try:
            self._precompute_retrograde(gameState)
        except Exception as exc:
            try:
                print(f"[β_retro] retrograde init failed: {exc}", file=sys.stderr)
            except Exception:
                pass
            V3_RETRO_TEAM.tempo_enabled = False
        V3_RETRO_TEAM.metrics['init_time'] = time.time() - t0
        V3_RETRO_TEAM.initialized = True

    def _compute_game_signature(self, gameState):
        try:
            walls = gameState.getWalls()
            starts = tuple(gameState.getAgentPosition(i)
                            for i in range(gameState.getNumAgents()))
            return (walls.width, walls.height, starts)
        except Exception:
            return id(gameState)

    def _precompute_retrograde(self, gameState):
        walls = gameState.getWalls()
        my_team = list(sorted(self.getTeam(gameState)))

        mid = walls.width // 2
        if self.red:
            my_capsules_getter = gameState.getBlueCapsules
            is_red = True
        else:
            my_capsules_getter = gameState.getRedCapsules
            is_red = False

        my_capsules = list(my_capsules_getter())
        if len(my_capsules) != 1:
            V3_RETRO_TEAM.tempo_enabled = False
            return
        capsule = my_capsules[0]

        # Safety gate via AP analysis (same as β)
        aps = find_articulation_points(walls)
        # No dead-end usage here; retrograde handles all topology implicitly
        if self.red:
            my_home_cells = [(mid - 1, y) for y in range(walls.height)
                              if not walls[mid - 1][y]]
        else:
            my_home_cells = [(mid, y) for y in range(walls.height)
                              if not walls[mid][y]]
        safety = analyze_capsule_safety(walls, capsule, my_home_cells, aps)
        if not safety.get('safe', False):
            V3_RETRO_TEAM.tempo_enabled = False
            return

        # Build retrograde value table
        V = build_retrograde_table(walls, capsule, restrict_opp_side=True,
                                     is_red_team=is_red)

        # Derive cell set (cells present in V)
        cells = set()
        for (me, d, t) in V.keys():
            cells.add(me)
            cells.add(d)

        V3_RETRO_TEAM.V_table = V
        V3_RETRO_TEAM.cell_set = frozenset(cells)
        V3_RETRO_TEAM.capsule = capsule
        V3_RETRO_TEAM.a_index = my_team[0]
        V3_RETRO_TEAM.b_index = my_team[1]
        V3_RETRO_TEAM.tempo_enabled = True

        V3_RETRO_TEAM.metrics['v_table_size'] = len(V)
        V3_RETRO_TEAM.metrics['v_plus_count'] = sum(1 for v in V.values() if v == 1)
        V3_RETRO_TEAM.metrics['v_minus_count'] = sum(1 for v in V.values() if v == -1)

    def _my_role(self):
        if self.index == V3_RETRO_TEAM.a_index:
            return self.RCTEMPO_ROLE_A
        return self.RCTEMPO_ROLE_B

    def _chooseActionImpl(self, gameState):
        V3_RETRO_TEAM.tick += 1

        phase = _detect_phase(self, gameState)
        V3_RETRO_TEAM.phase = phase

        if not V3_RETRO_TEAM.tempo_enabled:
            return super()._chooseActionImpl(gameState)

        # Phase 1 + Agent A: retrograde-backed chase
        if phase == 1 and self._my_role() == 'A':
            action = self._choose_retro_chase_action(gameState)
            if action is not None:
                return action

        # Everyone else (B, Phase 3, fallback): rc82 plays
        return super()._chooseActionImpl(gameState)

    def _choose_retro_chase_action(self, gameState):
        """Phase 1 A: retrograde lookup → commit if V=+1 (or draw+far)."""
        if V3_RETRO_TEAM.capsule is None:
            return None
        my_pos = gameState.getAgentPosition(self.index)
        if my_pos is None:
            return None

        # Score gate
        try:
            raw_score = gameState.getScore()
            my_score = raw_score if self.red else -raw_score
            if my_score >= 5:
                return None
        except Exception:
            pass

        distance_fn = _distance_fn_from_apsp(self.apsp, self.distancer)
        capsule = V3_RETRO_TEAM.capsule
        d_to_cap = distance_fn(my_pos, capsule)

        # Trigger check
        opp_pac = _opp_pacman_count(self, gameState)
        if self.TRIGGER_MODE == 'loose':
            trigger_on = (opp_pac >= 1)
        else:
            trigger_on = (opp_pac == 1)
        if not trigger_on:
            if self.TRACE:
                print(f"[retro t={V3_RETRO_TEAM.tick}] me={my_pos} SKIP opp_pac={opp_pac}", file=sys.stderr)
            return None

        V3_RETRO_TEAM.metrics['retro_trigger_fires'] += 1

        # Nearest defender
        def_pos, def_scared = _nearest_visible_defender(
            self, gameState, my_pos, distance_fn)

        # Scared defender: trivially safe; direct chase
        if def_pos is None or def_scared > 0:
            if self.TRACE:
                print(f"[retro t={V3_RETRO_TEAM.tick}] me={my_pos} def_scared/none → greedy", file=sys.stderr)
            return self._greedy_step_toward(gameState, my_pos, capsule,
                                              distance_fn)

        me_in = my_pos in V3_RETRO_TEAM.cell_set
        def_in = def_pos in V3_RETRO_TEAM.cell_set
        # Check we are in V table region
        if not me_in or not def_in:
            # Not in precomputed region (e.g., I'm on home side). Fall through
            # to rc82 (safe β v2d behavior) — no aggressive greedy chase.
            if self.TRACE:
                print(f"[retro t={V3_RETRO_TEAM.tick}] me={my_pos} def={def_pos} "
                      f"NOT_IN_REGION (me_in={me_in}, def_in={def_in}) → β v2d", file=sys.stderr)
            V3_RETRO_TEAM.metrics['retro_aborts'] += 1
            return None

        # Retrograde value lookup
        V = V3_RETRO_TEAM.V_table
        v_current = V.get((my_pos, def_pos, 0), 0)

        # Decision based on V and DRAW_MODE
        should_commit = False
        reason = ''
        if v_current == +1:
            should_commit = True
            reason = 'V=+1'
            V3_RETRO_TEAM.metrics['retro_commits_plus'] += 1
        elif v_current == 0:
            if self.DRAW_MODE == 'always':
                should_commit = True
                reason = 'V=0 always'
                V3_RETRO_TEAM.metrics['retro_commits_draw'] += 1
            elif self.DRAW_MODE == 'far' and d_to_cap >= self.DRAW_MIN_DIST:
                should_commit = True
                reason = f'V=0 far (d_cap={d_to_cap})'
                V3_RETRO_TEAM.metrics['retro_commits_draw'] += 1
            else:
                reason = f'V=0 near (d_cap={d_to_cap} < {self.DRAW_MIN_DIST}) or never'
        else:
            reason = 'V=-1'
        # v_current == -1 OR draw_mode='never' on 0 → don't commit

        if not should_commit:
            if self.TRACE:
                print(f"[retro t={V3_RETRO_TEAM.tick}] me={my_pos} def={def_pos} "
                      f"d_cap={d_to_cap} ABORT reason={reason} (draw_mode={self.DRAW_MODE})", file=sys.stderr)
            V3_RETRO_TEAM.metrics['retro_aborts'] += 1
            return None

        # Emergency abort: defender adjacent = immediate death
        d_me = distance_fn(my_pos, def_pos)
        if d_me <= self.EMERGENCY_ABORT:
            if self.TRACE:
                print(f"[retro t={V3_RETRO_TEAM.tick}] EMERGENCY_ABORT d_me={d_me}", file=sys.stderr)
            return None

        # Compute best action. For V=+1, retrograde-directed. For V=0 commit,
        # retrograde is indifferent (all draws) — use greedy toward capsule
        # to ensure progress.
        walls = gameState.getWalls()
        if v_current == +1:
            best_next, best_v = retrograde_best_action(
                V, walls, my_pos, def_pos, cell_set=V3_RETRO_TEAM.cell_set)
            # Also ensure retrograde didn't pick STOP on +1 (shouldn't happen,
            # but be defensive — prefer moving closer to capsule on tie)
            if best_next == my_pos:
                # Find any neighbor with V=+1 closer to capsule
                from zoo_rctempo_core import _neighbors_with_stop
                best_d = distance_fn(my_pos, capsule)
                for n in _neighbors_with_stop(walls, my_pos):
                    if n == my_pos or n not in V3_RETRO_TEAM.cell_set:
                        continue
                    if n == def_pos:
                        continue
                    v_n = V.get((n, def_pos, 1), 0)
                    if v_n == +1:
                        d_n = distance_fn(n, capsule)
                        if d_n < best_d:
                            best_d = d_n
                            best_next = n
        else:
            # V=0 draw commit — use greedy toward capsule (heuristic progress)
            best_next = None
            best_v = 0
            legal = gameState.getLegalActions(self.index)
            if legal:
                action = self._greedy_step_toward(gameState, my_pos, capsule,
                                                    distance_fn)
                if action is not None:
                    vec = Actions.directionToVector(action)
                    bx, by = int(my_pos[0] + vec[0]), int(my_pos[1] + vec[1])
                    best_next = (bx, by)

        if self.TRACE:
            print(f"[retro t={V3_RETRO_TEAM.tick}] me={my_pos}→{best_next} "
                  f"def={def_pos} v_cur={v_current} best_v={best_v} COMMIT ({reason})",
                  file=sys.stderr)

        # If best action actually worsens our value (-1), abort
        if best_v == -1:
            V3_RETRO_TEAM.metrics['retro_aborts'] += 1
            return None

        legal = gameState.getLegalActions(self.index)
        if not legal:
            return None
        action = _action_toward_cell(gameState, my_pos, best_next, legal)
        if action is None:
            return self._greedy_step_toward(gameState, my_pos, capsule,
                                              distance_fn)
        return action

    def _greedy_step_toward(self, gameState, my_pos, target, distance_fn):
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return None
        best_action = None
        best_dist = 10 ** 9
        for a in legal:
            if a == Directions.STOP:
                continue
            vec = Actions.directionToVector(a)
            nx, ny = int(my_pos[0] + vec[0]), int(my_pos[1] + vec[1])
            d = distance_fn((nx, ny), target)
            if d < best_dist:
                best_dist = d
                best_action = a
        return best_action or (legal[0] if legal else None)

    def final(self, gameState):
        try:
            super().final(gameState)
        except Exception:
            pass


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRCTempoBetaRetroAgent",
               second="ReflexRCTempoBetaRetroAgent"):
    return [ReflexRCTempoBetaRetroAgent(firstIndex),
            ReflexRCTempoBetaRetroAgent(secondIndex)]

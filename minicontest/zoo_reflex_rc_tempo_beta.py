# zoo_reflex_rc_tempo_beta.py
# ---------------------------
# rc-tempo V0.1 β — deterministic weighted-orienteering scared-window plan
# layered on top of rc82's reactive play.
#
# Design:
#   Phase 1 (pre-capsule):   rc82 plays (has f_distToCapsule bias already)
#   Phase 3 (scared window): follow precomputed 2-agent orienteering plan
#   Phase 4 (post-scared):   rc82 plays
#
# Agent A = lower team index (offense, eats capsule, risk-max DP)
# Agent B = higher team index (defense + scared cleanup via count-max DP)
#
# Safety gate: layouts where static capsule-approach analysis finds a
# single-node chokepoint → tempo_enabled=False → agent behaves as rc82.
#
# Metrics (per agent, written to csv at game end if RCTEMPO_METRICS_CSV env set):
#   phase_reached, reached_capsule, time_to_capsule,
#   foods_on_scared, total_turns, final_score
#
# Shared state:
#   All per-team state stored on a module-level singleton `RCTEMPO_TEAM`
#   so Agent A and B see the same plans / phase / tick.
#
# ---------------------------------------------------------------------------
# Naming convention (pm32):
#
#   This file (β proper) uses BETA_TRIGGER_GATE with values:
#     'none'        — chase always considered (default; pm31 behavior)
#     'any'         — chase only if opp_pacman_count >= 1
#     'exactly_one' — chase only if opp_pacman_count == 1
#
#   The sister file zoo_reflex_rc_tempo_beta_retro.py uses
#   BETA_RETRO_TRIGGER_MODE with values 'strict' (default; ==1) | 'loose' (>=1).
#
#   These ARE intentionally different env-var names with different defaults —
#   β v2d (this file) historically had no opp_pacman gate at all; β_retro
#   needs a 1:1 chase subgame for the retrograde V table to be valid. Reusing
#   one var would force one of the two agents to silently regress its
#   committed default. Do not consolidate the two without a behavior audit.
# ---------------------------------------------------------------------------

from __future__ import annotations

import os
import sys
import time
from collections import deque

from zoo_reflex_rc82 import ReflexRC82Agent
from game import Directions, Actions
from zoo_rctempo_core import (
    DEFAULT_RISK_WEIGHTS,
    analyze_capsule_safety,
    compute_dead_end_depth,
    find_articulation_points,
    make_plans,
)


# ---------------------------------------------------------------------------
# Team shared state
# ---------------------------------------------------------------------------

class _RCTempoTeamState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.initialized = False
        self.game_signature = None  # dedup across games in same process
        self.tempo_enabled = False
        self.safety = None
        self.plans = []  # list of (A, B) plan dicts
        self.top_plan = None
        self.capsule = None
        # pm32 Angle C: actual home-side midline cells, used by _maybe_retreat
        self.my_home_cells = []
        # Legacy slots — never populated; kept for any external code that
        # touched them. _maybe_retreat reads my_home_cells, NOT these.
        self.red_starts = []
        self.blue_starts = []
        self.a_index = None  # global agent index of A
        self.b_index = None
        self.phase = 1
        self.tick = 0
        self.metrics = {
            'init_time': 0.0,
            'scared_seen': False,
            'capsule_ate_tick': None,
            'foods_on_scared_a': 0,
            'foods_on_scared_b': 0,
            'tempo_enabled': False,
            'plans_count': 0,
        }


RCTEMPO_TEAM = _RCTempoTeamState()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _distance_fn_from_apsp(apsp, distancer_fallback):
    """Returns distance function that uses APSP if available, else distancer."""
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


def _bfs_path(walls, start, goal, limit=60):
    """Shortest maze path start→goal. Returns [start, ..., goal] or None.

    limit bounds BFS expansion to avoid wall-time surprises on big maps.
    """
    if start == goal:
        return [start]
    w, h = walls.width, walls.height
    parent = {start: None}
    q = deque([start])
    expanded = 0
    while q and expanded < limit * limit:
        u = q.popleft()
        expanded += 1
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = u[0] + dx, u[1] + dy
            if nx < 0 or nx >= w or ny < 0 or ny >= h:
                continue
            if walls[nx][ny]:
                continue
            v = (nx, ny)
            if v in parent:
                continue
            parent[v] = u
            if v == goal:
                # reconstruct
                path = [v]
                cur = u
                while cur is not None:
                    path.append(cur)
                    cur = parent[cur]
                path.reverse()
                return path
            q.append(v)
    return None


def _next_step_toward(gameState, my_pos, target, legal, distance_fn):
    """Pick legal action that minimizes distance to target. Tie-break by index."""
    if my_pos == target:
        return Directions.STOP if Directions.STOP in legal else legal[0]
    best_action = None
    best_dist = 10 ** 9
    for a in legal:
        if a == Directions.STOP:
            continue
        vec = Actions.directionToVector(a)
        nx, ny = int(my_pos[0] + vec[0]), int(my_pos[1] + vec[1])
        new_pos = (nx, ny)
        d = distance_fn(new_pos, target)
        if d < best_dist:
            best_dist = d
            best_action = a
    if best_action is None:
        return legal[0] if legal else Directions.STOP
    return best_action


def _detect_phase(agent, gameState):
    """Returns 1 (pre-capsule), 3 (scared), 4 (post)."""
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


# ---------------------------------------------------------------------------
# Beta Agent
# ---------------------------------------------------------------------------

class ReflexRCTempoBetaAgent(ReflexRC82Agent):

    RCTEMPO_ROLE_A = 'A'
    RCTEMPO_ROLE_B = 'B'

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        # Initialize per-game team state (once per team)
        game_sig = self._compute_game_signature(gameState)
        if RCTEMPO_TEAM.initialized and RCTEMPO_TEAM.game_signature == game_sig:
            # Already initialized by teammate
            return
        RCTEMPO_TEAM.reset()
        RCTEMPO_TEAM.game_signature = game_sig
        t0 = time.time()
        try:
            self._precompute_team(gameState)
        except Exception as exc:
            try:
                print(f"[rc_tempo_beta] init failed, rc82 fallback: {exc}", file=sys.stderr)
            except Exception:
                pass
            RCTEMPO_TEAM.tempo_enabled = False
        RCTEMPO_TEAM.metrics['init_time'] = time.time() - t0
        RCTEMPO_TEAM.metrics['tempo_enabled'] = RCTEMPO_TEAM.tempo_enabled
        RCTEMPO_TEAM.initialized = True

    def _compute_game_signature(self, gameState):
        """Per-game signature: layout hash + starting positions."""
        try:
            walls = gameState.getWalls()
            starts = tuple(gameState.getAgentPosition(i)
                            for i in range(gameState.getNumAgents()))
            return (walls.width, walls.height, starts)
        except Exception:
            return id(gameState)

    def _precompute_team(self, gameState):
        # pm32 MJ-7: defense-in-depth slot reset for direct-call safety. Even
        # if registerInitialState's reset path is bypassed (or _precompute_team
        # early-returns below), the team's _maybe_retreat helper must NOT read
        # stale my_home_cells from a previous (different layout's) game in the
        # same subprocess.
        RCTEMPO_TEAM.my_home_cells = []
        RCTEMPO_TEAM.tempo_enabled = False
        walls = gameState.getWalls()

        # My team indices
        my_team = list(sorted(self.getTeam(gameState)))
        enemy_team = list(sorted(self.getOpponents(gameState)))

        # Red/blue home cells based on our role
        mid = walls.width // 2
        if self.red:
            my_home_cells = [(mid - 1, y) for y in range(walls.height)
                              if not walls[mid - 1][y]]
            enemy_home_cells = [(mid, y) for y in range(walls.height)
                                 if not walls[mid][y]]
            my_capsules_getter = gameState.getBlueCapsules
            my_foods = list(self.getFood(gameState).asList())
        else:
            my_home_cells = [(mid, y) for y in range(walls.height)
                              if not walls[mid][y]]
            enemy_home_cells = [(mid - 1, y) for y in range(walls.height)
                                 if not walls[mid - 1][y]]
            my_capsules_getter = gameState.getRedCapsules
            my_foods = list(self.getFood(gameState).asList())

        # pm32 Angle C: persist the actual midline cells for _maybe_retreat.
        # Note: this happens BEFORE the 1-capsule gate / safety-gate early
        # returns below, so retreat is available even when tempo is disabled.
        RCTEMPO_TEAM.my_home_cells = list(my_home_cells)

        my_capsules = list(my_capsules_getter())

        # 1-capsule gate
        if len(my_capsules) != 1:
            RCTEMPO_TEAM.tempo_enabled = False
            return
        capsule = my_capsules[0]

        # Topology
        aps = find_articulation_points(walls)
        de_depth = compute_dead_end_depth(walls)

        # Safety gate
        safety = analyze_capsule_safety(walls, capsule, my_home_cells, aps)
        RCTEMPO_TEAM.safety = safety
        if not safety.get('safe', False):
            RCTEMPO_TEAM.tempo_enabled = False
            return

        # Distance function (reuse CoreCaptureAgent APSP if ready)
        distance_fn = _distance_fn_from_apsp(self.apsp, self.distancer)

        # Precompute plans
        plans = make_plans(
            walls, my_foods, my_home_cells, enemy_home_cells,
            capsule, aps, de_depth, distance_fn, b_budget_bonus=3)
        if not plans:
            RCTEMPO_TEAM.tempo_enabled = False
            return

        RCTEMPO_TEAM.plans = plans
        RCTEMPO_TEAM.top_plan = plans[0]
        RCTEMPO_TEAM.capsule = capsule
        RCTEMPO_TEAM.a_index = my_team[0]
        RCTEMPO_TEAM.b_index = my_team[1]
        RCTEMPO_TEAM.tempo_enabled = True
        RCTEMPO_TEAM.metrics['plans_count'] = len(plans)

    def _my_role(self):
        if self.index == RCTEMPO_TEAM.a_index:
            return self.RCTEMPO_ROLE_A
        return self.RCTEMPO_ROLE_B

    def _chooseActionImpl(self, gameState):
        # Update tick
        RCTEMPO_TEAM.tick += 1

        # Phase detection (still computed even if tempo_enabled=False for metrics)
        phase = _detect_phase(self, gameState)
        RCTEMPO_TEAM.phase = phase
        if phase == 3 and not RCTEMPO_TEAM.metrics['scared_seen']:
            RCTEMPO_TEAM.metrics['scared_seen'] = True
            RCTEMPO_TEAM.metrics['capsule_ate_tick'] = RCTEMPO_TEAM.tick

        # Tempo disabled: pure rc82
        if not RCTEMPO_TEAM.tempo_enabled:
            return super()._chooseActionImpl(gameState)

        # Scared window: attempt precomputed plan
        if phase == 3:
            action = self._choose_scared_action(gameState)
            if action is not None:
                self._maybe_log_food(gameState, action)
                return action

        # Phase 1 + Agent A: commit to capsule approach
        if phase == 1 and self._my_role() == 'A':
            action = self._choose_capsule_chase_action(gameState)
            if action is not None:
                return action

        # Pre-capsule / post-scared: rc82 plays naturally
        return super()._chooseActionImpl(gameState)

    def _maybe_retreat(self, gameState, my_pos, distance_fn):
        """pm32 Angle C: when chase aborts and BETA_RETREAT_ON_ABORT=1, take one
        greedy step toward the nearest home midline cell. Default OFF preserves
        pm31 behavior (returns None → rc82 fallback).

        Returns None when:
          - BETA_RETREAT_ON_ABORT != '1' (env not set or set to '0')
          - my_home_cells empty (e.g., team-state reset post-MJ-7 leak guard)
          - no legal actions available
        """
        if os.environ.get('BETA_RETREAT_ON_ABORT', '0') != '1':
            return None
        home_cells = RCTEMPO_TEAM.my_home_cells
        if not home_cells:
            return None
        try:
            home_target = min(home_cells, key=lambda c: distance_fn(my_pos, c))
        except Exception:
            return None
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return None
        # If we're already on a home cell, no need to step
        if my_pos == home_target:
            return None
        return _next_step_toward(gameState, my_pos, home_target, legal,
                                  distance_fn)

    def _choose_capsule_chase_action(self, gameState):
        """Phase 1 A: greedy step toward capsule with pm29 safety + pm30 Stage 2d score gate.

        pm30 decision (2026-04-20): Revert full-path BFS (v2a/v2a2 66g smoke showed
        no overall gain vs pm29; regressions on rc82/rc166 composite defenders
        outweighed monster/rc32 improvements).  Keep pm29's 2-cell early abort +
        defender-closer-to-capsule abort.  Add Stage 2d score-conditional gate.

        Returns action if chase is safe and score-permissive.  Returns None for
        rc82 fallback otherwise.
        """
        if RCTEMPO_TEAM.capsule is None:
            return None
        my_pos = gameState.getAgentPosition(self.index)
        if my_pos is None:
            return None

        # Stage 2d: score-conditional gate.
        # If we're already leading by a wide margin, no need to risk a chase —
        # rc82 handles patrol/defense.  "Lead" is from our team's perspective
        # (red → getScore, blue → −getScore).
        try:
            raw_score = gameState.getScore()
            my_score = raw_score if self.red else -raw_score
            if my_score >= 5:
                return None  # lead secure, defer to rc82
        except Exception:
            pass  # fall through if framework guarantees change

        distance_fn = _distance_fn_from_apsp(self.apsp, self.distancer)
        capsule = RCTEMPO_TEAM.capsule
        d_to_cap = distance_fn(my_pos, capsule)

        legal = gameState.getLegalActions(self.index)
        if not legal:
            return None

        # Defender safety with env-var overridable thresholds (pm31 tuning).
        # Defaults preserve pm30 committed behavior exactly.
        def _iv(name, default):
            try:
                return int(os.environ.get(name, default))
            except Exception:
                return default
        abort_dist = _iv('BETA_ABORT_DIST', 2)                 # d_me <= X → abort
        chase_slack = _iv('BETA_CHASE_SLACK', 1)               # def_to_cap + X < me_to_cap → abort
        path_abort_ratio = _iv('BETA_PATH_ABORT_RATIO', 0)     # abort if d_me <= d_to_cap/R (0=off)

        # pm32 Angle A: trigger gating and distance gate. Defaults preserve pm31
        # behavior (gate='none', dist=999 → no-op). See header doc for the
        # naming-asymmetry rationale vs BETA_RETRO_TRIGGER_MODE.
        trigger_gate = os.environ.get('BETA_TRIGGER_GATE', 'none')
        if trigger_gate not in ('none', 'any', 'exactly_one'):
            trigger_gate = 'none'  # silently ignore garbage
        trigger_max_dist = _iv('BETA_TRIGGER_MAX_DIST', 999)

        if trigger_gate != 'none':
            try:
                opp_pac = sum(
                    1 for opp_idx in self.getOpponents(gameState)
                    if getattr(gameState.getAgentState(opp_idx), 'isPacman', False)
                )
            except Exception:
                opp_pac = 0
            if trigger_gate == 'any' and opp_pac < 1:
                return self._maybe_retreat(gameState, my_pos, distance_fn)
            if trigger_gate == 'exactly_one' and opp_pac != 1:
                return self._maybe_retreat(gameState, my_pos, distance_fn)

        # Defensive guard (pm32): only enforce the cap when > 0. A stale =0
        # must NOT abort all chases.
        if trigger_max_dist > 0 and d_to_cap > trigger_max_dist:
            return self._maybe_retreat(gameState, my_pos, distance_fn)

        try:
            for opp_idx in self.getOpponents(gameState):
                ost = gameState.getAgentState(opp_idx)
                if getattr(ost, 'isPacman', False):
                    continue
                if int(getattr(ost, 'scaredTimer', 0) or 0) > 0:
                    continue
                opp_pos = gameState.getAgentPosition(opp_idx)
                if opp_pos is None:
                    continue
                opp_pos = (int(opp_pos[0]), int(opp_pos[1]))
                d_me = distance_fn(my_pos, opp_pos)
                if d_me <= abort_dist:
                    return self._maybe_retreat(gameState, my_pos, distance_fn)
                if path_abort_ratio > 0:
                    threshold = max(abort_dist, d_to_cap // path_abort_ratio)
                    if d_me <= threshold:
                        return self._maybe_retreat(gameState, my_pos, distance_fn)
                d_opp_cap = distance_fn(opp_pos, capsule)
                if d_opp_cap + chase_slack < d_to_cap:
                    return self._maybe_retreat(gameState, my_pos, distance_fn)
        except Exception:
            return None

        # Greedy step toward capsule
        return _next_step_toward(gameState, my_pos, capsule, legal, distance_fn)

    def _choose_scared_action(self, gameState):
        plan = RCTEMPO_TEAM.top_plan
        if plan is None:
            return None
        role = self._my_role()
        route = plan['a_res']['route'] if role == 'A' else plan['b_res']['route']
        if not route:
            return None

        my_pos = gameState.getAgentPosition(self.index)
        if my_pos is None:
            return None

        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        distance_fn = _distance_fn_from_apsp(self.apsp, self.distancer)
        # B must be pre-positioned: within 5 cells of b_start, else stay defensive (rc82).
        # Otherwise B abandons defense to chase distant food and baseline attacker runs riot.
        if role == 'B':
            b_start = plan.get('b_start')
            if b_start is None or distance_fn(my_pos, b_start) > 5:
                return None  # let rc82 (defense) handle

        # Find next waypoint we haven't reached yet
        next_wp = self._next_unvisited_waypoint(my_pos, route, distance_fn, gameState)
        if next_wp is None:
            return None

        # If ghost (non-scared - could happen during phase transition) within 2, abort
        try:
            opps = [gameState.getAgentState(i) for i in self.getOpponents(gameState)]
            for o in opps:
                if int(getattr(o, 'scaredTimer', 0) or 0) > 0:
                    continue
                if not getattr(o, 'isPacman', False):
                    opp_pos = o.getPosition() if hasattr(o, 'getPosition') else None
                    if opp_pos is not None:
                        d = distance_fn(my_pos, (int(opp_pos[0]), int(opp_pos[1])))
                        if d <= 2:
                            return None  # fallback to rc82
        except Exception:
            pass

        action = _next_step_toward(gameState, my_pos, next_wp, legal, distance_fn)
        return action

    def _next_unvisited_waypoint(self, my_pos, route, distance_fn, gameState):
        """Find the earliest waypoint in route that is still a food we need to eat,
        OR the final home cell if all food eaten."""
        my_foods = set(self.getFood(gameState).asList())
        # route = [capsule_or_bstart, food1, food2, ..., home]
        # Skip the first (start) waypoint; look for first food still in my_foods
        for wp in route[1:-1]:
            if wp in my_foods:
                return wp
        # All foods eaten — head home
        return route[-1]

    def _maybe_log_food(self, gameState, action):
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return
            vec = Actions.directionToVector(action)
            nx, ny = int(my_pos[0] + vec[0]), int(my_pos[1] + vec[1])
            target = (nx, ny)
            foods = set(self.getFood(gameState).asList())
            if target in foods:
                key = 'foods_on_scared_a' if self._my_role() == 'A' else 'foods_on_scared_b'
                RCTEMPO_TEAM.metrics[key] += 1
        except Exception:
            pass

    def final(self, gameState):
        """Write metrics CSV if env var set. Called by framework at end."""
        try:
            super().final(gameState)
        except Exception:
            pass
        try:
            self._maybe_write_metrics(gameState)
        except Exception:
            pass

    def _maybe_write_metrics(self, gameState):
        csv_path = os.environ.get('RCTEMPO_METRICS_CSV')
        if not csv_path:
            return
        if self._my_role() != 'A':
            # only A writes — avoid double-entry
            return
        try:
            score = gameState.getScore()
        except Exception:
            score = 0
        row = {
            'game_id': os.environ.get('RCTEMPO_GAME_ID', '0'),
            'red': self.red,
            'layout': os.environ.get('RCTEMPO_LAYOUT', ''),
            'tempo_enabled': RCTEMPO_TEAM.metrics['tempo_enabled'],
            'plans_count': RCTEMPO_TEAM.metrics['plans_count'],
            'init_time': round(RCTEMPO_TEAM.metrics['init_time'], 3),
            'scared_seen': RCTEMPO_TEAM.metrics['scared_seen'],
            'capsule_ate_tick': RCTEMPO_TEAM.metrics['capsule_ate_tick'] or -1,
            'foods_on_scared_a': RCTEMPO_TEAM.metrics['foods_on_scared_a'],
            'foods_on_scared_b': RCTEMPO_TEAM.metrics['foods_on_scared_b'],
            'total_ticks': RCTEMPO_TEAM.tick,
            'final_score': score,
        }
        try:
            first_write = not os.path.exists(csv_path)
            with open(csv_path, 'a') as f:
                if first_write:
                    f.write(','.join(row.keys()) + '\n')
                f.write(','.join(str(v) for v in row.values()) + '\n')
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
        except Exception:
            pass


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRCTempoBetaAgent", second="ReflexRCTempoBetaAgent"):
    return [ReflexRCTempoBetaAgent(firstIndex), ReflexRCTempoBetaAgent(secondIndex)]

# zoo_reflex_rc_tempo_beta_v3a.py
# --------------------------------
# rc-tempo V3a — pm31 A* + Voronoi + slack food DP planner.
#
# Differences from β v2d (pm30):
#   1. opp_pacman_count trigger — β active ONLY when exactly 1 opp pacman
#      (plus sticky commit if A already within 5 of capsule).
#   2. _choose_capsule_chase_action replaced with risk-weighted A* +
#      full-path Voronoi reachability filter + slack food orienteering DP.
#   3. Death-avoidance safety: dead-end risk weighting, teammate cell
#      exclusion, simultaneous-move margin=1, scared-timer awareness.
#
# Design: identical team-state structure and Phase 3 scared plan as β.
# Only Phase 1 A behavior diverges.

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
    compute_risk_map,
    find_articulation_points,
    make_plans,
    risk_weighted_astar,
    slack_plan_to_capsule,
    voronoi_safe_path,
)


# ---------------------------------------------------------------------------
# Team shared state (same shape as β)
# ---------------------------------------------------------------------------

class _V3TeamState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.initialized = False
        self.game_signature = None
        self.tempo_enabled = False
        self.safety = None
        self.plans = []
        self.top_plan = None
        self.capsule = None
        self.a_index = None
        self.b_index = None
        self.phase = 1
        self.tick = 0
        self.aps = frozenset()
        self.de_depth = {}
        self.risk_map = {}
        self.home_cells = []
        self.enemy_home_cells = []
        self.my_capsules_count_initial = 0
        # Sticky commit tracking
        self.a_committed = False
        self.last_slack_plan = None
        self.metrics = {
            'init_time': 0.0,
            'scared_seen': False,
            'capsule_ate_tick': None,
            'foods_on_scared_a': 0,
            'foods_on_scared_b': 0,
            'tempo_enabled': False,
            'plans_count': 0,
            'v3_trigger_fires': 0,
            'v3_slack_food_grabs': 0,
            'v3_a_deaths': 0,
        }


V3_TEAM = _V3TeamState()


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
    """Given next_cell (adjacent to my_pos), find the legal action that moves there."""
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


def _next_step_toward(gameState, my_pos, target, legal, distance_fn):
    if my_pos == target:
        return Directions.STOP if Directions.STOP in legal else legal[0]
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
    if best_action is None:
        return legal[0] if legal else Directions.STOP
    return best_action


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
    """Count opps currently acting as pacmen (crossed into our territory)."""
    try:
        cnt = 0
        for i in agent.getOpponents(gameState):
            st = gameState.getAgentState(i)
            if getattr(st, 'isPacman', False):
                cnt += 1
        return cnt
    except Exception:
        return -1  # unknown


def _nearest_visible_defender(agent, gameState, my_pos, distance_fn):
    """Return (def_pos, scared_ticks) of nearest visible non-scared-equivalent
    opp ghost. Returns (None, 0) if no visible defender.

    For V1 1:1 assumption: we pick the closest non-pacman opp.
    """
    try:
        best_pos = None
        best_dist = 10 ** 9
        best_scared = 0
        for i in agent.getOpponents(gameState):
            st = gameState.getAgentState(i)
            if getattr(st, 'isPacman', False):
                continue  # pacman, not a defender right now
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


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except Exception:
        return default


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except Exception:
        return default


def _env_bool(name, default):
    v = os.environ.get(name)
    if v is None:
        return default
    return v.lower() in ('1', 'true', 'yes', 'on')


class ReflexRCTempoBetaV3aAgent(ReflexRC82Agent):

    RCTEMPO_ROLE_A = 'A'
    RCTEMPO_ROLE_B = 'B'

    # Tunable knobs (env-var overridable — per-variant sweep)
    STICKY_RADIUS = _env_int('V3A_STICKY_RADIUS', 5)
    VORONOI_MARGIN = _env_int('V3A_MARGIN', 1)
    RISK_THRESHOLD = _env_float('V3A_RISK_THRESHOLD', 3.0)
    MIN_SLACK_FOR_DETOUR = _env_int('V3A_SLACK_MIN', 2)
    MAX_DETOUR_FOOD = _env_int('V3A_MAX_FOOD', 5)
    GREEDY_FALLBACK = _env_bool('V3A_GREEDY_FALLBACK', False)
    TRIGGER_MODE = os.environ.get('V3A_TRIGGER_MODE', 'strict')  # 'strict' (==1) | 'loose' (>=1)

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        game_sig = self._compute_game_signature(gameState)
        if V3_TEAM.initialized and V3_TEAM.game_signature == game_sig:
            return
        V3_TEAM.reset()
        V3_TEAM.game_signature = game_sig
        t0 = time.time()
        try:
            self._precompute_team(gameState)
        except Exception as exc:
            try:
                print(f"[rc_tempo_v3a] init failed, rc82 fallback: {exc}", file=sys.stderr)
            except Exception:
                pass
            V3_TEAM.tempo_enabled = False
        V3_TEAM.metrics['init_time'] = time.time() - t0
        V3_TEAM.metrics['tempo_enabled'] = V3_TEAM.tempo_enabled
        V3_TEAM.initialized = True

    def _compute_game_signature(self, gameState):
        try:
            walls = gameState.getWalls()
            starts = tuple(gameState.getAgentPosition(i)
                            for i in range(gameState.getNumAgents()))
            return (walls.width, walls.height, starts)
        except Exception:
            return id(gameState)

    def _precompute_team(self, gameState):
        walls = gameState.getWalls()
        my_team = list(sorted(self.getTeam(gameState)))

        mid = walls.width // 2
        if self.red:
            my_home_cells = [(mid - 1, y) for y in range(walls.height)
                              if not walls[mid - 1][y]]
            enemy_home_cells = [(mid, y) for y in range(walls.height)
                                 if not walls[mid][y]]
            my_capsules_getter = gameState.getBlueCapsules
        else:
            my_home_cells = [(mid, y) for y in range(walls.height)
                              if not walls[mid][y]]
            enemy_home_cells = [(mid - 1, y) for y in range(walls.height)
                                 if not walls[mid - 1][y]]
            my_capsules_getter = gameState.getRedCapsules

        my_foods = list(self.getFood(gameState).asList())
        my_capsules = list(my_capsules_getter())

        V3_TEAM.my_capsules_count_initial = len(my_capsules)

        # 1-capsule gate (β tempo strategy only targets 1-cap layouts)
        if len(my_capsules) != 1:
            V3_TEAM.tempo_enabled = False
            return
        capsule = my_capsules[0]

        aps = find_articulation_points(walls)
        de_depth = compute_dead_end_depth(walls)

        safety = analyze_capsule_safety(walls, capsule, my_home_cells, aps)
        V3_TEAM.safety = safety
        if not safety.get('safe', False):
            V3_TEAM.tempo_enabled = False
            return

        distance_fn = _distance_fn_from_apsp(self.apsp, self.distancer)

        # Precompute Phase 3 plans (same as β)
        plans = make_plans(
            walls, my_foods, my_home_cells, enemy_home_cells,
            capsule, aps, de_depth, distance_fn, b_budget_bonus=3)
        if not plans:
            V3_TEAM.tempo_enabled = False
            return

        # Precompute static risk map for chase-phase A* edge costs
        risk_map, _ = compute_risk_map(
            walls, my_foods, my_home_cells, enemy_home_cells,
            aps, de_depth, distance_fn)

        V3_TEAM.plans = plans
        V3_TEAM.top_plan = plans[0]
        V3_TEAM.capsule = capsule
        V3_TEAM.aps = aps
        V3_TEAM.de_depth = de_depth
        V3_TEAM.risk_map = risk_map
        V3_TEAM.home_cells = my_home_cells
        V3_TEAM.enemy_home_cells = enemy_home_cells
        V3_TEAM.a_index = my_team[0]
        V3_TEAM.b_index = my_team[1]
        V3_TEAM.tempo_enabled = True
        V3_TEAM.metrics['plans_count'] = len(plans)

    def _my_role(self):
        if self.index == V3_TEAM.a_index:
            return self.RCTEMPO_ROLE_A
        return self.RCTEMPO_ROLE_B

    def _chooseActionImpl(self, gameState):
        V3_TEAM.tick += 1

        phase = _detect_phase(self, gameState)
        V3_TEAM.phase = phase
        if phase == 3 and not V3_TEAM.metrics['scared_seen']:
            V3_TEAM.metrics['scared_seen'] = True
            V3_TEAM.metrics['capsule_ate_tick'] = V3_TEAM.tick

        # Tempo disabled: pure rc82
        if not V3_TEAM.tempo_enabled:
            return super()._chooseActionImpl(gameState)

        # Scared window: precomputed plan (same as β)
        if phase == 3:
            action = self._choose_scared_action(gameState)
            if action is not None:
                self._maybe_log_food(gameState, action)
                return action

        # Phase 1 + Agent A: try v3a chase
        if phase == 1 and self._my_role() == 'A':
            action = self._choose_capsule_chase_action_v3a(gameState)
            if action is not None:
                return action

        # B or fallback: rc82
        return super()._chooseActionImpl(gameState)

    def _choose_capsule_chase_action_v3a(self, gameState):
        """pm31 V3a: risk-weighted A* + Voronoi + slack food DP.

        Trigger: β ON only if opp_pacman_count == 1 OR sticky commit active.
        """
        if V3_TEAM.capsule is None:
            return None
        my_pos = gameState.getAgentPosition(self.index)
        if my_pos is None:
            return None

        # Score-conditional skip (inherited from v2d)
        try:
            raw_score = gameState.getScore()
            my_score = raw_score if self.red else -raw_score
            if my_score >= 5:
                V3_TEAM.a_committed = False
                return None
        except Exception:
            pass

        distance_fn = _distance_fn_from_apsp(self.apsp, self.distancer)
        capsule = V3_TEAM.capsule
        d_to_cap = distance_fn(my_pos, capsule)

        # --- Trigger logic: opp_pacman_count + sticky commit ---
        opp_pac = _opp_pacman_count(self, gameState)
        sticky_active = (V3_TEAM.a_committed and d_to_cap <= self.STICKY_RADIUS)

        if self.TRIGGER_MODE == 'loose':
            trigger_on = (opp_pac >= 1)
        else:
            trigger_on = (opp_pac == 1)

        if trigger_on or sticky_active:
            V3_TEAM.metrics['v3_trigger_fires'] += 1
            # β active — run slack planner
        else:
            # β OFF: reset sticky and fallback to rc82
            V3_TEAM.a_committed = False
            return None

        # --- Defender + teammate info ---
        def_pos, def_scared = _nearest_visible_defender(
            self, gameState, my_pos, distance_fn)

        # Teammate (B) position
        teammate_pos = None
        try:
            if V3_TEAM.b_index is not None:
                tp = gameState.getAgentPosition(V3_TEAM.b_index)
                if tp is not None:
                    teammate_pos = (int(tp[0]), int(tp[1]))
        except Exception:
            pass

        # Food set (opp side, still uneaten)
        try:
            food_set = frozenset(tuple(f) for f in self.getFood(gameState).asList())
        except Exception:
            food_set = frozenset()

        walls = gameState.getWalls()

        # --- Slack planner ---
        try:
            plan = slack_plan_to_capsule(
                walls, my_pos, capsule,
                defender=def_pos, scared_ticks=def_scared,
                food_set=food_set, distance_fn=distance_fn,
                risk_map=V3_TEAM.risk_map,
                aps=V3_TEAM.aps, dead_end_depth=V3_TEAM.de_depth,
                teammate=teammate_pos,
                risk_threshold=self.RISK_THRESHOLD,
                margin=self.VORONOI_MARGIN,
                min_slack_for_detour=self.MIN_SLACK_FOR_DETOUR,
                max_detour_food=self.MAX_DETOUR_FOOD,
            )
        except Exception as e:
            try:
                print(f"[v3a] slack_plan crashed: {e}", file=sys.stderr)
            except Exception:
                pass
            return None  # rc82 fallback

        V3_TEAM.last_slack_plan = plan

        if not plan['reachable']:
            # Unsafe → either rc82 fallback OR best-effort greedy step.
            if self.GREEDY_FALLBACK:
                legal = gameState.getLegalActions(self.index)
                if legal:
                    # Check nearest defender proximity; if within 2, still abort.
                    if def_pos is not None:
                        d_me_def = distance_fn(my_pos, def_pos)
                        if d_me_def <= 2 and def_scared <= 0:
                            V3_TEAM.a_committed = False
                            return None
                    return _next_step_toward(gameState, my_pos, capsule,
                                              legal, distance_fn)
            V3_TEAM.a_committed = False
            return None

        # Mark committed if we're within sticky radius
        if d_to_cap <= self.STICKY_RADIUS:
            V3_TEAM.a_committed = True

        if plan.get('reason') == 'slack_food' and plan.get('food_on_path'):
            V3_TEAM.metrics['v3_slack_food_grabs'] += 1

        # Execute next step
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return None
        next_cell = plan['next_step']
        action = _action_toward_cell(gameState, my_pos, next_cell, legal)
        if action is None:
            # Fall back to greedy
            action = _next_step_toward(gameState, my_pos, capsule, legal,
                                         distance_fn)
        return action

    # --- Phase 3 scared plan + final metrics copied from β ---

    def _choose_scared_action(self, gameState):
        plan = V3_TEAM.top_plan
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

        if role == 'B':
            b_start = plan.get('b_start')
            if b_start is None or distance_fn(my_pos, b_start) > 5:
                return None

        next_wp = self._next_unvisited_waypoint(my_pos, route, distance_fn, gameState)
        if next_wp is None:
            return None

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
                            return None
        except Exception:
            pass

        action = _next_step_toward(gameState, my_pos, next_wp, legal, distance_fn)
        return action

    def _next_unvisited_waypoint(self, my_pos, route, distance_fn, gameState):
        my_foods = set(self.getFood(gameState).asList())
        for wp in route[1:-1]:
            if wp in my_foods:
                return wp
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
                V3_TEAM.metrics[key] += 1
        except Exception:
            pass

    def final(self, gameState):
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
            return
        try:
            score = gameState.getScore()
        except Exception:
            score = 0
        row = {
            'agent': 'v3a',
            'game_id': os.environ.get('RCTEMPO_GAME_ID', '0'),
            'red': self.red,
            'layout': os.environ.get('RCTEMPO_LAYOUT', ''),
            'tempo_enabled': V3_TEAM.metrics['tempo_enabled'],
            'plans_count': V3_TEAM.metrics['plans_count'],
            'init_time': round(V3_TEAM.metrics['init_time'], 3),
            'scared_seen': V3_TEAM.metrics['scared_seen'],
            'capsule_ate_tick': V3_TEAM.metrics['capsule_ate_tick'] or -1,
            'foods_on_scared_a': V3_TEAM.metrics['foods_on_scared_a'],
            'foods_on_scared_b': V3_TEAM.metrics['foods_on_scared_b'],
            'v3_trigger_fires': V3_TEAM.metrics['v3_trigger_fires'],
            'v3_slack_food_grabs': V3_TEAM.metrics['v3_slack_food_grabs'],
            'total_ticks': V3_TEAM.tick,
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
               first="ReflexRCTempoBetaV3aAgent", second="ReflexRCTempoBetaV3aAgent"):
    return [ReflexRCTempoBetaV3aAgent(firstIndex),
            ReflexRCTempoBetaV3aAgent(secondIndex)]

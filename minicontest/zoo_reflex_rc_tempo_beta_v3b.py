# zoo_reflex_rc_tempo_beta_v3b.py
# --------------------------------
# rc-tempo V3b — pm31 αβ minimax capsule chase.
#
# Uses perfect-information zero-sum search (leveraging minicontest's
# removal of fog-of-war — full opponent positions always known).
#
# Me = MAX, defender = MIN. Iterative deepening to depth 6 with
# α-β pruning + move ordering. Time budget 150ms/move default.
#
# Same trigger + scared-plan infrastructure as v3a; only the chase
# decision differs.

from __future__ import annotations

import os
import sys
import time

from zoo_reflex_rc82 import ReflexRC82Agent
from game import Directions, Actions
from zoo_rctempo_core import (
    ab_capsule_chase,
    analyze_capsule_safety,
    compute_dead_end_depth,
    compute_risk_map,
    find_articulation_points,
    make_plans,
)


# Reuse singleton pattern from v3a — but separate team state so they can
# coexist without interference.

class _V3BTeamState:
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
        self.home_cells = []
        self.enemy_home_cells = []
        self.a_committed = False
        self.metrics = {
            'init_time': 0.0,
            'scared_seen': False,
            'capsule_ate_tick': None,
            'foods_on_scared_a': 0,
            'foods_on_scared_b': 0,
            'tempo_enabled': False,
            'v3b_trigger_fires': 0,
            'v3b_ab_depth_sum': 0,
            'v3b_ab_nodes_sum': 0,
            'v3b_ab_calls': 0,
        }


V3B_TEAM = _V3BTeamState()


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


class ReflexRCTempoBetaV3bAgent(ReflexRC82Agent):

    RCTEMPO_ROLE_A = 'A'
    RCTEMPO_ROLE_B = 'B'

    # Tunable knobs
    STICKY_RADIUS = _env_int('V3B_STICKY_RADIUS', 5)
    AB_MAX_DEPTH = _env_int('V3B_MAX_DEPTH', 6)
    AB_TIME_BUDGET = _env_float('V3B_TIME_BUDGET', 0.15)  # seconds per move
    TRIGGER_MODE = os.environ.get('V3B_TRIGGER_MODE', 'strict')  # strict | loose

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        game_sig = self._compute_game_signature(gameState)
        if V3B_TEAM.initialized and V3B_TEAM.game_signature == game_sig:
            return
        V3B_TEAM.reset()
        V3B_TEAM.game_signature = game_sig
        t0 = time.time()
        try:
            self._precompute_team(gameState)
        except Exception as exc:
            try:
                print(f"[rc_tempo_v3b] init failed, rc82 fallback: {exc}", file=sys.stderr)
            except Exception:
                pass
            V3B_TEAM.tempo_enabled = False
        V3B_TEAM.metrics['init_time'] = time.time() - t0
        V3B_TEAM.metrics['tempo_enabled'] = V3B_TEAM.tempo_enabled
        V3B_TEAM.initialized = True

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

        if len(my_capsules) != 1:
            V3B_TEAM.tempo_enabled = False
            return
        capsule = my_capsules[0]

        aps = find_articulation_points(walls)
        de_depth = compute_dead_end_depth(walls)
        safety = analyze_capsule_safety(walls, capsule, my_home_cells, aps)
        V3B_TEAM.safety = safety
        if not safety.get('safe', False):
            V3B_TEAM.tempo_enabled = False
            return

        distance_fn = _distance_fn_from_apsp(self.apsp, self.distancer)
        plans = make_plans(
            walls, my_foods, my_home_cells, enemy_home_cells,
            capsule, aps, de_depth, distance_fn, b_budget_bonus=3)
        if not plans:
            V3B_TEAM.tempo_enabled = False
            return

        V3B_TEAM.plans = plans
        V3B_TEAM.top_plan = plans[0]
        V3B_TEAM.capsule = capsule
        V3B_TEAM.aps = aps
        V3B_TEAM.de_depth = de_depth
        V3B_TEAM.home_cells = my_home_cells
        V3B_TEAM.enemy_home_cells = enemy_home_cells
        V3B_TEAM.a_index = my_team[0]
        V3B_TEAM.b_index = my_team[1]
        V3B_TEAM.tempo_enabled = True

    def _my_role(self):
        if self.index == V3B_TEAM.a_index:
            return self.RCTEMPO_ROLE_A
        return self.RCTEMPO_ROLE_B

    def _chooseActionImpl(self, gameState):
        V3B_TEAM.tick += 1

        phase = _detect_phase(self, gameState)
        V3B_TEAM.phase = phase
        if phase == 3 and not V3B_TEAM.metrics['scared_seen']:
            V3B_TEAM.metrics['scared_seen'] = True
            V3B_TEAM.metrics['capsule_ate_tick'] = V3B_TEAM.tick

        if not V3B_TEAM.tempo_enabled:
            return super()._chooseActionImpl(gameState)

        if phase == 3:
            action = self._choose_scared_action(gameState)
            if action is not None:
                self._maybe_log_food(gameState, action)
                return action

        if phase == 1 and self._my_role() == 'A':
            action = self._choose_capsule_chase_action_v3b(gameState)
            if action is not None:
                return action

        return super()._chooseActionImpl(gameState)

    def _choose_capsule_chase_action_v3b(self, gameState):
        """pm31 V3b: αβ minimax capsule chase."""
        if V3B_TEAM.capsule is None:
            return None
        my_pos = gameState.getAgentPosition(self.index)
        if my_pos is None:
            return None

        try:
            raw_score = gameState.getScore()
            my_score = raw_score if self.red else -raw_score
            if my_score >= 5:
                V3B_TEAM.a_committed = False
                return None
        except Exception:
            pass

        distance_fn = _distance_fn_from_apsp(self.apsp, self.distancer)
        capsule = V3B_TEAM.capsule
        d_to_cap = distance_fn(my_pos, capsule)

        opp_pac = _opp_pacman_count(self, gameState)
        sticky_active = (V3B_TEAM.a_committed and d_to_cap <= self.STICKY_RADIUS)

        if self.TRIGGER_MODE == 'loose':
            trigger_on = (opp_pac >= 1)
        else:
            trigger_on = (opp_pac == 1)

        if trigger_on or sticky_active:
            V3B_TEAM.metrics['v3b_trigger_fires'] += 1
        else:
            V3B_TEAM.a_committed = False
            return None

        def_pos, def_scared = _nearest_visible_defender(
            self, gameState, my_pos, distance_fn)

        legal = gameState.getLegalActions(self.index)
        if not legal:
            return None

        walls = gameState.getWalls()

        try:
            res = ab_capsule_chase(
                walls, my_pos, capsule,
                defender=def_pos, scared_ticks=def_scared,
                distance_fn=distance_fn,
                max_depth=self.AB_MAX_DEPTH,
                time_budget=self.AB_TIME_BUDGET,
                home_cells=V3B_TEAM.home_cells,
            )
        except Exception as e:
            try:
                print(f"[v3b] ab_capsule_chase crashed: {e}", file=sys.stderr)
            except Exception:
                pass
            return None

        V3B_TEAM.metrics['v3b_ab_calls'] += 1
        V3B_TEAM.metrics['v3b_ab_depth_sum'] += res.get('depth_reached', 0)
        V3B_TEAM.metrics['v3b_ab_nodes_sum'] += res.get('nodes', 0)

        next_pos = res.get('best_action_pos')
        if next_pos is None:
            return None

        # Safety gate: if αβ says "stay" (score very negative), fall back to rc82
        score = res.get('score', 0.0)
        if score < -500.0:
            V3B_TEAM.a_committed = False
            return None

        if d_to_cap <= self.STICKY_RADIUS:
            V3B_TEAM.a_committed = True

        action = _action_toward_cell(gameState, my_pos, next_pos, legal)
        if action is None:
            action = _next_step_toward(gameState, my_pos, capsule, legal,
                                         distance_fn)
        return action

    # --- Phase 3 scared + final metrics (copied from v3a/β) ---

    def _choose_scared_action(self, gameState):
        plan = V3B_TEAM.top_plan
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
                V3B_TEAM.metrics[key] += 1
        except Exception:
            pass

    def final(self, gameState):
        try:
            super().final(gameState)
        except Exception:
            pass


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRCTempoBetaV3bAgent", second="ReflexRCTempoBetaV3bAgent"):
    return [ReflexRCTempoBetaV3bAgent(firstIndex),
            ReflexRCTempoBetaV3bAgent(secondIndex)]

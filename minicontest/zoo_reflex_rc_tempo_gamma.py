# zoo_reflex_rc_tempo_gamma.py
# -----------------------------
# rc-tempo V0.1 γ — β + entry-DP layer for opportunistic food pickup on A's
# path from home to capsule. Falls back to β (rc82) when path blocked.
#
# New in γ vs β:
#   - At init: additionally compute entry-DP plan (A's start → capsule,
#     max food pickup within budget = shortest_path + slack).
#   - In phase 1 (pre-capsule): if entry plan exists AND next waypoint has
#     no defender threat within sight, follow entry route. Else β logic.
#
# Safety: waypoint-by-waypoint defender check. If any visible enemy ghost
# within 2 cells of our next waypoint → abort entry plan, revert to rc82.

from __future__ import annotations

import os
import sys
import time

from zoo_reflex_rc_tempo_beta import (
    ReflexRCTempoBetaAgent, RCTEMPO_TEAM, _distance_fn_from_apsp, _detect_phase,
    _next_step_toward,
)
from zoo_rctempo_core import entry_orienteering_dp
from game import Directions, Actions


ENTRY_BUDGET_SLACK = 6  # max extra moves for detour food pickup
ENTRY_DEFENDER_CUTOFF = 3  # cells — if defender ≤ this to next WP, abort


class ReflexRCTempoGammaAgent(ReflexRCTempoBetaAgent):

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        # Additionally compute entry plan (only if tempo_enabled)
        if not RCTEMPO_TEAM.tempo_enabled:
            return
        try:
            self._precompute_entry(gameState)
        except Exception as exc:
            try:
                print(f"[rc_tempo_gamma] entry precompute failed, β fallback: {exc}",
                       file=sys.stderr)
            except Exception:
                pass
            RCTEMPO_TEAM.metrics['entry_plan_ready'] = False

    def _precompute_entry(self, gameState):
        if RCTEMPO_TEAM.capsule is None:
            return
        distance_fn = _distance_fn_from_apsp(self.apsp, self.distancer)

        # A's start position (index = a_index)
        a_idx = RCTEMPO_TEAM.a_index
        a_start = gameState.getAgentPosition(a_idx)
        if a_start is None:
            return

        capsule = RCTEMPO_TEAM.capsule
        foods = list(self.getFood(gameState).asList())
        shortest = distance_fn(a_start, capsule)
        budget = shortest + ENTRY_BUDGET_SLACK
        entry = entry_orienteering_dp(a_start, foods, capsule, distance_fn,
                                       budget=budget, objective='count')
        RCTEMPO_TEAM.entry_plan = entry
        RCTEMPO_TEAM.entry_budget = budget
        RCTEMPO_TEAM.metrics['entry_plan_ready'] = True
        RCTEMPO_TEAM.metrics['entry_plan_foods'] = entry['n_food']
        RCTEMPO_TEAM.metrics['entry_plan_moves'] = entry['total_moves']

    def _chooseActionImpl(self, gameState):
        RCTEMPO_TEAM.tick += 1
        phase = _detect_phase(self, gameState)
        RCTEMPO_TEAM.phase = phase
        if phase == 3 and not RCTEMPO_TEAM.metrics['scared_seen']:
            RCTEMPO_TEAM.metrics['scared_seen'] = True
            RCTEMPO_TEAM.metrics['capsule_ate_tick'] = RCTEMPO_TEAM.tick

        if not RCTEMPO_TEAM.tempo_enabled:
            return super(ReflexRCTempoBetaAgent, self)._chooseActionImpl(gameState)

        # Phase 3: β scared logic
        if phase == 3:
            action = self._choose_scared_action(gameState)
            if action is not None:
                self._maybe_log_food(gameState, action)
                return action

        # Phase 1: try entry plan (A only)
        if phase == 1 and self._my_role() == 'A':
            action = self._choose_entry_action(gameState)
            if action is not None:
                return action

        # Fallback: rc82
        return super(ReflexRCTempoBetaAgent, self)._chooseActionImpl(gameState)

    def _choose_entry_action(self, gameState):
        entry_plan = getattr(RCTEMPO_TEAM, 'entry_plan', None)
        if entry_plan is None or not entry_plan.get('route'):
            return None

        my_pos = gameState.getAgentPosition(self.index)
        if my_pos is None:
            return None

        distance_fn = _distance_fn_from_apsp(self.apsp, self.distancer)

        # Next waypoint: first unvisited food in entry plan, or capsule if all picked
        my_foods = set(self.getFood(gameState).asList())
        capsule = RCTEMPO_TEAM.capsule
        next_wp = capsule
        for wp in entry_plan['food_order']:
            if wp in my_foods:
                next_wp = wp
                break

        # Safety: visible defender within ENTRY_DEFENDER_CUTOFF of next_wp?
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
                d_to_wp = distance_fn(opp_pos, next_wp)
                d_to_me = distance_fn(my_pos, opp_pos)
                if d_to_wp <= ENTRY_DEFENDER_CUTOFF or d_to_me <= 2:
                    return None  # abort, rc82 handles
        except Exception:
            pass

        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        return _next_step_toward(gameState, my_pos, next_wp, legal, distance_fn)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRCTempoGammaAgent", second="ReflexRCTempoGammaAgent"):
    return [ReflexRCTempoGammaAgent(firstIndex), ReflexRCTempoGammaAgent(secondIndex)]

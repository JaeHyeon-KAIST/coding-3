# zoo_reflex_rc122.py
# ------------------
# rc122: rc16 + rc50 opening book OFF (no rc29) + rc82 DEF.
#
# Ablation: rc116 = (rc16+rc29+rc50) OFF + rc82 DEF (100%). rc122
# removes rc29 to test whether REVERSE disruption is necessary for
# the perfect score, or whether rc16+rc50 alone + rc82 DEF is
# sufficient.

from __future__ import annotations

from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc50 import ReflexRC50Agent


class ReflexRC122OffenseAgent(ReflexRC50Agent):
    """rc50 opening book (which inherits ReflexA1Agent → ReflexTunedAgent).
    For rc122 we want the OFFENSE agent to base on rc16 Voronoi. Simplest:
    use rc16 directly with an inline opening-book override similar to rc50."""


# Since rc50 already extends ReflexA1Agent (not rc16), and Python
# MRO doesn't easily mix rc16's voronoi into rc50's opening book,
# we implement rc122 directly via rc16 + inline opening-book logic.


from collections import deque
from zoo_reflex_rc50 import _bfs_distances, RC50_BOOK_TURNS, RC50_TOP_K, RC50_A1_TOL_FRAC
from zoo_reflex_rc02 import _articulation_points
from zoo_core import TEAM
from zoo_features import evaluate
from game import Directions
from util import nearestPoint


class ReflexRC122OffenseAgent(ReflexRC16Agent):
    """rc16 Voronoi + 15-turn opening book (no rc29 reverse)."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc122_turn = 0
        try:
            self._rc122_target = self._compute_opening_target(gameState)
        except Exception:
            self._rc122_target = None

    def _compute_opening_target(self, gameState):
        try:
            role = getattr(self, "role", None) or TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"
        if role != "OFFENSE":
            return None
        walls = gameState.getWalls()
        try:
            my_pos = gameState.getAgentPosition(self.index)
        except Exception:
            my_pos = None
        if my_pos is None:
            return None
        opps = list(self.getOpponents(gameState))
        opp_cols = []
        for opp_idx in opps:
            try:
                p = gameState.getInitialAgentPosition(opp_idx)
                if p is not None:
                    opp_cols.append(p[0])
            except Exception:
                continue
        if not opp_cols:
            return None
        opp_col_mean = sum(opp_cols) / len(opp_cols)
        try:
            food_list = list(self.getFood(gameState).asList())
        except Exception:
            food_list = []
        if not food_list:
            return None
        my_dists = _bfs_distances(walls, my_pos)
        best = None
        best_key = float("-inf")
        for f in food_list:
            d_us = my_dists.get(f, None)
            if d_us is None:
                continue
            contest = abs(f[0] - opp_col_mean)
            key = contest - 0.5 * d_us
            if key > best_key:
                best_key = key
                best = f
        return best

    def _chooseActionImpl(self, gameState):
        self._rc122_turn += 1
        target = getattr(self, "_rc122_target", None)
        if target is None or self._rc122_turn > RC50_BOOK_TURNS:
            return super()._chooseActionImpl(gameState)
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP
            weights = self._get_weights()
            scored = []
            for action in legal:
                try:
                    s = evaluate(self, gameState, action, weights)
                except Exception:
                    s = float("-inf")
                scored.append((s, action))
            scored.sort(key=lambda sa: sa[0], reverse=True)
            if not scored or scored[0][0] == float("-inf"):
                return super()._chooseActionImpl(gameState)
            top_score = scored[0][0]
            tol = max(abs(top_score) * RC50_A1_TOL_FRAC, 1.0)
            K = min(RC50_TOP_K, len(scored))
            candidates = [a for s, a in scored[:K] if s >= top_score - tol]
            if len(candidates) < 2:
                return scored[0][1]
            best_action = candidates[0]
            best_dist = float("inf")
            for action in candidates:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw is None:
                        continue
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                    d = self.getMazeDistance(sp, target)
                    if d < best_dist:
                        best_dist = d
                        best_action = action
                except Exception:
                    continue
            return best_action
        except Exception:
            return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="rc122-offense", second="rc122-defense"):
    return [ReflexRC122OffenseAgent(firstIndex),
            ReflexRC82Agent(secondIndex)]

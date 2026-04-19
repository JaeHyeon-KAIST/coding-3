# zoo_reflex_rc116.py
# ------------------
# rc116: rc109 + rc50 15-turn opening book overlay on OFFENSE.
#
# Adds an opening-book nudge (rc50-style: first 15 turns target
# uncontested food from BFS) to rc109's rc16+rc29 offense agent.
# Defense is unchanged rc82.

from __future__ import annotations

from collections import deque

from zoo_reflex_rc109 import ReflexRC109OffenseAgent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc02 import _articulation_points
from zoo_reflex_rc50 import _bfs_distances
from zoo_core import TEAM
from zoo_features import evaluate
from game import Directions
from util import nearestPoint


RC116_BOOK_TURNS = 15
RC116_TOP_K = 3
RC116_A1_TOL_FRAC = 0.05


class ReflexRC116OffenseAgent(ReflexRC109OffenseAgent):
    """rc109 offense + rc50-style 15-turn opening book nudge."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc116_turn = 0
        try:
            self._rc116_target = self._compute_opening_target(gameState)
        except Exception:
            self._rc116_target = None

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
        self._rc116_turn += 1
        target = getattr(self, "_rc116_target", None)
        if target is None or self._rc116_turn > RC116_BOOK_TURNS:
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
            tol = max(abs(top_score) * RC116_A1_TOL_FRAC, 1.0)
            K = min(RC116_TOP_K, len(scored))
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
               first="rc116-offense", second="rc116-defense"):
    return [ReflexRC116OffenseAgent(firstIndex),
            ReflexRC82Agent(secondIndex)]

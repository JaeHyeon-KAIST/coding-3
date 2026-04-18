# zoo_reflex_rc06.py
# ------------------
# rc06: Border-food resource denial overlay on A1 champion.
#
# Gemini #7 (scorched earth / 청야 전술). Adapted for Pacman CTF:
# in the capture framework you can't eat your own food, but you CAN
# preferentially eat the enemy's border food (the cells on the enemy side
# that sit closest to our home frontier). This achieves two things:
#   (1) fastest risk-adjusted return rate — shortest round-trips while
#       the opponent defender is still positioning;
#   (2) pushes the eatable frontier deeper into enemy territory, so
#       future turns of the game the remaining food is all far from our
#       home — which our defender can more easily contain.
#
# Only active in the early game window (timeleft > RC06_LATE_THRESHOLD)
# and only for OFFENSE role. Uses the same top-K A1 re-rank as rc04 so
# we never override ghost-safety.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions


RC06_TOP_K = 3
RC06_LATE_THRESHOLD = 900      # active while timeleft > this (first ~300 ticks)
RC06_A1_TOL_FRAC = 0.05


class ReflexRC06Agent(ReflexA1Agent):
    """A1 champion + early-game border-food priority overlay."""

    def _border_food_target(self, gameState):
        """Return the enemy food cell closest to our home frontier, or
        None if inactive."""
        try:
            timeleft = int(getattr(gameState.data, "timeleft", 1200) or 1200)
        except Exception:
            timeleft = 1200
        if timeleft <= RC06_LATE_THRESHOLD:
            return None

        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"
        if role != "OFFENSE":
            return None

        try:
            food_list = list(self.getFood(gameState).asList())
            home = list(self.homeFrontier) if self.homeFrontier else []
            if not food_list or not home:
                return None
            return min(
                food_list,
                key=lambda f: min(self.getMazeDistance(f, h) for h in home),
            )
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        try:
            target = self._border_food_target(gameState)
        except Exception:
            target = None
        if target is None:
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
            tol = max(abs(top_score) * RC06_A1_TOL_FRAC, 1.0)
            K = min(RC06_TOP_K, len(scored))
            candidates = [a for s, a in scored[:K]
                          if s >= top_score - tol]
            if len(candidates) < 2:
                return scored[0][1]

            from util import nearestPoint
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
               first="ReflexRC06Agent", second="ReflexRC06Agent"):
    return [ReflexRC06Agent(firstIndex), ReflexRC06Agent(secondIndex)]

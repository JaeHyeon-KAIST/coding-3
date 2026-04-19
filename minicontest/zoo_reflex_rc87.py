# zoo_reflex_rc87.py
# ------------------
# rc87: Far-food prioritization overlay on A1 champion.
#
# A1's f_distToFood pulls Pacman toward the NEAREST food on the enemy
# side. A competent defender that camps the defended food cluster
# will intercept agents trained to prefer nearest food. rc87 flips
# the preference: when we are safe (no ghost threat, not carrying
# much), target the food FURTHEST from the nearest enemy defender.
#
# The chase is routed through A1's top-K with the existing tolerance
# band, so ghost-safety weighting stays intact. The only thing rc87
# changes is the "which top-K candidate to pick" tie-breaker — it
# prefers actions whose successor cell minimizes the distance to the
# "far food" target.
#
# Fire-conditions:
#   (a) we are Pacman on enemy side,
#   (b) carrying < RC87_CARRY_MAX food,
#   (c) no active (non-scared) ghost within RC87_GHOST_NEAR,
#   (d) ≥ 2 remaining enemy foods (otherwise A1's nearest-food
#       behavior is already optimal),
#   (e) at least one enemy defender position is known.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions
from util import nearestPoint


RC87_TOP_K = 3
RC87_A1_TOL_FRAC = 0.05
RC87_CARRY_MAX = 3
RC87_GHOST_NEAR = 4


class ReflexRC87Agent(ReflexA1Agent):
    """A1 champion + far-food tie-breaker when we are safe."""

    def _far_food_target(self, gameState):
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return None
            my_state = gameState.getAgentState(self.index)
            if not getattr(my_state, "isPacman", False):
                return None

            try:
                carrying = int(getattr(my_state, "numCarrying", 0) or 0)
            except Exception:
                carrying = 0
            if carrying >= RC87_CARRY_MAX:
                return None

            # No active ghost within threshold.
            defender_positions = []
            for opp_idx in self.getOpponents(gameState):
                try:
                    ost = gameState.getAgentState(opp_idx)
                    if getattr(ost, "isPacman", False):
                        continue
                    if int(getattr(ost, "scaredTimer", 0) or 0) > 0:
                        continue
                    opp_pos = gameState.getAgentPosition(opp_idx)
                    if opp_pos is None:
                        continue
                    if self.getMazeDistance(my_pos, opp_pos) <= RC87_GHOST_NEAR:
                        return None
                    defender_positions.append(opp_pos)
                except Exception:
                    continue
            if not defender_positions:
                return None

            try:
                food_list = list(self.getFood(gameState).asList())
            except Exception:
                food_list = []
            if len(food_list) < 2:
                return None

            # Pick the food whose nearest-defender distance is LARGEST,
            # tie-break on distance-to-us (shorter preferred).
            best = None
            best_far = -1
            best_close = float("inf")
            for f in food_list:
                try:
                    nearest_def = min(self.getMazeDistance(p, f)
                                      for p in defender_positions)
                    my_d = self.getMazeDistance(my_pos, f)
                except Exception:
                    continue
                if nearest_def > best_far or (
                    nearest_def == best_far and my_d < best_close
                ):
                    best_far = nearest_def
                    best_close = my_d
                    best = f
            return best
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        try:
            target = self._far_food_target(gameState)
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
            tol = max(abs(top_score) * RC87_A1_TOL_FRAC, 1.0)
            K = min(RC87_TOP_K, len(scored))
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
               first="ReflexRC87Agent", second="ReflexRC87Agent"):
    return [ReflexRC87Agent(firstIndex), ReflexRC87Agent(secondIndex)]

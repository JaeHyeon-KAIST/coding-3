# zoo_reflex_rc92.py
# ------------------
# rc92: Scared-ghost aggressive chase overlay on A1 champion.
#
# When an enemy ghost is SCARED (after we eat their capsule), that
# ghost can be eaten on contact for +1 score and forces them to
# respawn. A1's features partially encode this via f_numInvaders and
# f_invaderDist, but those target ghosts-turned-Pacman, not scared
# ghosts-still-on-home.
#
# rc92 explicitly pulls Pacman toward scared enemy defenders when
# the scared timer has meaningful remaining time. This accelerates
# kill-score and briefly removes their defense threat.
#
# Fire-conditions (all):
#   (a) at least one enemy defender is SCARED (scaredTimer > 2),
#   (b) we are Pacman on enemy side,
#   (c) maze distance to the scared ghost ≤ scaredTimer (we can
#       actually reach before timer expires),
#   (d) I am the agent closer to this scared ghost (teammate should
#       continue normal food-gathering if further).
#
# Within top-K with A1 tolerance, pick action that minimizes distance
# to the scared ghost. This eats the ghost then returns to normal
# A1 behavior.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions
from util import nearestPoint


RC92_TOP_K = 3
RC92_A1_TOL_FRAC = 0.05
RC92_SCARED_MIN = 2          # ghost must have more than this timer left


class ReflexRC92Agent(ReflexA1Agent):
    """A1 champion + aggressive scared-ghost chase when reachable."""

    def _scared_chase_target(self, gameState):
        try:
            my_pos = gameState.getAgentPosition(self.index)
            my_state = gameState.getAgentState(self.index)
            if my_pos is None:
                return None
            if not getattr(my_state, "isPacman", False):
                return None

            best = None
            best_d = float("inf")
            for opp_idx in self.getOpponents(gameState):
                try:
                    ost = gameState.getAgentState(opp_idx)
                    if getattr(ost, "isPacman", False):
                        continue  # want enemy defenders (ghosts)
                    scared = int(getattr(ost, "scaredTimer", 0) or 0)
                    if scared <= RC92_SCARED_MIN:
                        continue
                    opp_pos = gameState.getAgentPosition(opp_idx)
                    if opp_pos is None:
                        continue
                    d = self.getMazeDistance(my_pos, opp_pos)
                    if d > scared:
                        continue  # can't reach in time
                    if d < best_d:
                        best_d = d
                        best = opp_pos
                except Exception:
                    continue
            if best is None:
                return None

            # Am I the closer teammate?
            my_team = sorted(list(self.getTeam(gameState)))
            mates = [i for i in my_team if i != self.index]
            if mates:
                try:
                    mate_pos = gameState.getAgentPosition(mates[0])
                    if mate_pos is not None:
                        mate_d = self.getMazeDistance(mate_pos, best)
                        if mate_d < best_d:
                            return None
                except Exception:
                    pass
            return best
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        try:
            target = self._scared_chase_target(gameState)
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
            tol = max(abs(top_score) * RC92_A1_TOL_FRAC, 1.0)
            K = min(RC92_TOP_K, len(scored))
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
               first="ReflexRC92Agent", second="ReflexRC92Agent"):
    return [ReflexRC92Agent(firstIndex), ReflexRC92Agent(secondIndex)]

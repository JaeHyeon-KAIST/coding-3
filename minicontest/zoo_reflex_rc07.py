# zoo_reflex_rc07.py
# ------------------
# rc07: Kamikaze / sacrificial-decoy overlay on A1 champion.
#
# Cooperative score-transfer strategy: when my teammate is carrying
# substantial food on the enemy side AND a ghost is threatening them,
# I charge the ghost to draw aggro. This gives my teammate a safe
# return window. Inspired by Gemini rc-pool #13.
#
# Fire-conditions (all must hold):
#   (a) my teammate is Pacman on enemy side and carrying ≥ 5 food,
#   (b) at least one active (non-scared) ghost is visible and within
#       RC07_GHOST_NEAR of my teammate,
#   (c) I can plausibly reach that ghost (distance < teammate escape),
#   (d) I am NOT myself carrying meaningful food — we don't want to
#       sacrifice my own big score.
#
# Action: among A1's top-K candidate actions (with tolerance), pick
# the one that MINIMIZES distance to the threatening ghost. A1 might
# normally dodge; kamikaze overrides toward the ghost.
#
# Note: decoy survives if it is a ghost on home side (can counter the
# enemy). So "suicide" is really just "get close to take one for the
# team and potentially kill them". Safe when my side.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions
from util import nearestPoint


RC07_TOP_K = 3
RC07_A1_TOL_FRAC = 0.05
RC07_MATE_CARRY_MIN = 5
RC07_GHOST_NEAR = 4           # ghost must be ≤ this cells from teammate
RC07_MY_CARRY_MAX = 2          # I'm not carrying much


class ReflexRC07Agent(ReflexA1Agent):
    """A1 champion + kamikaze-decoy to draw ghost from carrying teammate."""

    def _decoy_target(self, gameState):
        """Return ghost position to charge or None."""
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return None
            my_state = gameState.getAgentState(self.index)
            try:
                my_carry = int(getattr(my_state, "numCarrying", 0) or 0)
            except Exception:
                my_carry = 0
            if my_carry > RC07_MY_CARRY_MAX:
                return None

            my_team = sorted(list(self.getTeam(gameState)))
            mates = [i for i in my_team if i != self.index]
            if not mates:
                return None
            mate = mates[0]
            try:
                mate_state = gameState.getAgentState(mate)
                mate_pos = gameState.getAgentPosition(mate)
            except Exception:
                return None
            if mate_pos is None:
                return None
            if not getattr(mate_state, "isPacman", False):
                return None
            try:
                mate_carry = int(getattr(mate_state, "numCarrying", 0) or 0)
            except Exception:
                mate_carry = 0
            if mate_carry < RC07_MATE_CARRY_MIN:
                return None

            # Find active ghost near teammate.
            best_ghost = None
            best_d_mate = float("inf")
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
                    d_mate = self.getMazeDistance(mate_pos, opp_pos)
                    if d_mate <= RC07_GHOST_NEAR and d_mate < best_d_mate:
                        best_d_mate = d_mate
                        best_ghost = opp_pos
                except Exception:
                    continue
            if best_ghost is None:
                return None

            # I must be able to reach the ghost reasonably fast.
            try:
                my_d = self.getMazeDistance(my_pos, best_ghost)
            except Exception:
                return None
            if my_d > 2 * best_d_mate + 4:
                # Too far to help.
                return None
            return best_ghost
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        try:
            target = self._decoy_target(gameState)
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
            tol = max(abs(top_score) * RC07_A1_TOL_FRAC, 1.0)
            K = min(RC07_TOP_K, len(scored))
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
               first="ReflexRC07Agent", second="ReflexRC07Agent"):
    return [ReflexRC07Agent(firstIndex), ReflexRC07Agent(secondIndex)]

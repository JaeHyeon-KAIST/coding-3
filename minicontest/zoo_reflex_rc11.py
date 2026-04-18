# zoo_reflex_rc11.py
# ------------------
# rc11: Border-juggling overlay on A1 champion (Gemini #3).
#
# Observation: when we stand exactly on the home-side border, we are a
# ghost (not Pacman), and a single step across the midline transforms us
# into a Pacman. A1's argmax treats each frame as a static evaluation and
# doesn't explicitly exploit this tick-level identity switch.
#
# Border juggling uses the switch deliberately:
#   * If I'm on our home frontier cell and a visible enemy is an active
#     non-scared ghost within reach on the enemy side, STOP (stay a ghost
#     on my home side) and wait — we remain invulnerable.
#   * If I'm on our home frontier and a visible invader (enemy Pacman) is
#     within N steps, skip into the enemy side as a Pacman to pull the
#     enemy defender away from the midline — then oscillate back.
#
# In practice we implement the first, safer half: when at the home
# frontier AND an active enemy ghost is within D on the enemy side AND
# we are not already carrying food, prefer STOP / move-back-home over
# stepping into the enemy. This is an anti-suicide safety overlay that
# A1 sometimes violates.
#
# Only overrides when a specific threshold condition is met; otherwise
# falls through to pure A1. Crash-proof.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from game import Directions


RC11_GHOST_THREAT_DIST = 3
RC11_MAX_CARRY_TO_WAIT = 1


class ReflexRC11Agent(ReflexA1Agent):
    """A1 + border-wait safety override."""

    def _at_border_with_ghost_threat(self, gameState):
        """Return True if I'm on a home-frontier cell AND an active ghost
        is within RC11_GHOST_THREAT_DIST on the enemy side AND my
        numCarrying ≤ RC11_MAX_CARRY_TO_WAIT."""
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return False
            frontier = self.homeFrontier if self.homeFrontier else []
            if my_pos not in frontier:
                return False

            st = gameState.getAgentState(self.index)
            carry = int(getattr(st, "numCarrying", 0) or 0)
            if carry > RC11_MAX_CARRY_TO_WAIT:
                return False

            for opp_idx in self.getOpponents(gameState):
                try:
                    opp_pos = gameState.getAgentPosition(opp_idx)
                    if opp_pos is None:
                        continue
                    opp_state = gameState.getAgentState(opp_idx)
                    if getattr(opp_state, "isPacman", False):
                        continue
                    if int(getattr(opp_state, "scaredTimer", 0) or 0) > 0:
                        continue
                    # Ghost must be on enemy side (not our side).
                    walls = gameState.getWalls()
                    mid_x = walls.width // 2
                    if self.red:
                        # Our home is x < mid_x → enemy side is x >= mid_x.
                        if int(opp_pos[0]) < mid_x:
                            continue
                    else:
                        if int(opp_pos[0]) >= mid_x:
                            continue
                    d = self.getMazeDistance(my_pos, opp_pos)
                    if d <= RC11_GHOST_THREAT_DIST:
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def _pick_home_wait_action(self, gameState):
        """Pick action: prefer STOP at frontier, else move toward nearest
        frontier cell (i.e. stay or retreat home)."""
        try:
            from util import nearestPoint
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return None
            my_pos = gameState.getAgentPosition(self.index)
            frontier = self.homeFrontier if self.homeFrontier else []
            if my_pos in frontier and Directions.STOP in legal:
                return Directions.STOP
            if not frontier:
                return None

            best_action = None
            best_dist = float("inf")
            for action in legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw is None:
                        continue
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                    # Reject actions that step into enemy side (we're juggling).
                    # "Enemy side" = opposite of our home side by x coordinate.
                    walls = gameState.getWalls()
                    mid_x = walls.width // 2
                    if self.red and sp[0] >= mid_x:
                        continue
                    if not self.red and sp[0] < mid_x:
                        continue
                    d = min(self.getMazeDistance(sp, h) for h in frontier)
                    if d < best_dist:
                        best_dist = d
                        best_action = action
                except Exception:
                    continue
            return best_action
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        try:
            should_wait = self._at_border_with_ghost_threat(gameState)
        except Exception:
            should_wait = False
        if not should_wait:
            return super()._chooseActionImpl(gameState)

        try:
            action = self._pick_home_wait_action(gameState)
        except Exception:
            action = None
        if action is None:
            return super()._chooseActionImpl(gameState)
        return action


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC11Agent", second="ReflexRC11Agent"):
    return [ReflexRC11Agent(firstIndex), ReflexRC11Agent(secondIndex)]

# zoo_reflex_rc168.py
# -------------------
# rc168: rc82 default, rc16 when my_carry >= 6 (return-home switch).
# Hypothesis: when the agent is already carrying a lot, territorial
# Voronoi (rc16) navigates back home better than rc82's combat-focused
# composite. rc82 handles the offensive accumulation; rc16 handles the
# delivery. Orthogonal to score-based rc160.
#
# Fire condition: ANY teammate (self.index) carry >= 6 → rc16.
# Otherwise rc82.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


RC168_CARRY_THRESHOLD = 6


class ReflexRC168Agent(ReflexRC82Agent):
    """rc82 default, rc16 when my_carry >= 6."""

    def _my_carry(self, gameState):
        try:
            st = gameState.getAgentState(self.index)
            return int(getattr(st, "numCarrying", 0) or 0)
        except Exception:
            return 0

    def _chooseActionImpl(self, gameState):
        carry = self._my_carry(gameState)
        if carry >= RC168_CARRY_THRESHOLD:
            return ReflexRC16Agent._chooseActionImpl(self, gameState)
        return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC168Agent", second="ReflexRC168Agent"):
    return [ReflexRC168Agent(firstIndex), ReflexRC168Agent(secondIndex)]

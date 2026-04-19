# zoo_reflex_rc173.py
# -------------------
# rc173: rc170 variant — on rc82/rc16 disagreement, prefer rc16 when
# tied (score==0). rc170 used score>=1 rc82 else rc16. rc173 tests
# whether pulling the threshold to >=2 helps tied cases.
#
# Slots (disagreement only):
#   score >= 2 : rc82
#   score <= 1 : rc16

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC173Agent(ReflexRC82Agent):
    """Consensus ∧; disagreement prefers rc16 on tied (score <= 1)."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        rc82_action = super()._chooseActionImpl(gameState)
        rc16_action = ReflexRC16Agent._chooseActionImpl(self, gameState)
        if rc82_action == rc16_action:
            return rc82_action
        return rc82_action if self._my_score(gameState) >= 2 else rc16_action


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC173Agent", second="ReflexRC173Agent"):
    return [ReflexRC173Agent(firstIndex), ReflexRC173Agent(secondIndex)]

# zoo_reflex_rc163.py
# -------------------
# rc163: rc82 when leading OR tied, rc16 only when behind.
# Tests whether tied-score use of rc82 (not rc16) loses edge cases.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC163Agent(ReflexRC82Agent):
    """rc82 if score >= 0, rc16 if behind."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        if self._my_score(gameState) >= 0:
            return super()._chooseActionImpl(gameState)
        return ReflexRC16Agent._chooseActionImpl(self, gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC163Agent", second="ReflexRC163Agent"):
    return [ReflexRC163Agent(firstIndex), ReflexRC163Agent(secondIndex)]

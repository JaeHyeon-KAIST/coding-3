# zoo_reflex_rc164.py
# -------------------
# rc164: rc16 when leading, rc82 when tied/behind.
# Inverts rc160's logic to test whether the "leading with rc82" pattern
# is essential or whether rc16 when leading (as in pm24's rc105 OFF slot)
# is equally strong.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC164Agent(ReflexRC82Agent):
    """rc16 if score >= 1, rc82 otherwise."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        if self._my_score(gameState) >= 1:
            return ReflexRC16Agent._chooseActionImpl(self, gameState)
        return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC164Agent", second="ReflexRC164Agent"):
    return [ReflexRC164Agent(firstIndex), ReflexRC164Agent(secondIndex)]

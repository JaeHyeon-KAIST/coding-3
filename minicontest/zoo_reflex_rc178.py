# zoo_reflex_rc178.py
# -------------------
# rc178: rc82 if score >= 4, rc16 otherwise.
# Threshold sweep above rc166 (>=3 = 98.5%).

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC178Agent(ReflexRC82Agent):
    """rc82 if score >= 4, rc16 otherwise."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        if self._my_score(gameState) >= 4:
            return super()._chooseActionImpl(gameState)
        return ReflexRC16Agent._chooseActionImpl(self, gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC178Agent", second="ReflexRC178Agent"):
    return [ReflexRC178Agent(firstIndex), ReflexRC178Agent(secondIndex)]

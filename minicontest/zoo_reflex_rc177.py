# zoo_reflex_rc177.py
# -------------------
# rc177: rc82 if score >= 2, rc16 otherwise.
# Threshold sweep between rc160 (>=1 = 97.5%) and rc166 (>=3 = 98.5%).

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC177Agent(ReflexRC82Agent):
    """rc82 if score >= 2, rc16 otherwise."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        if self._my_score(gameState) >= 2:
            return super()._chooseActionImpl(gameState)
        return ReflexRC16Agent._chooseActionImpl(self, gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC177Agent", second="ReflexRC177Agent"):
    return [ReflexRC177Agent(firstIndex), ReflexRC177Agent(secondIndex)]

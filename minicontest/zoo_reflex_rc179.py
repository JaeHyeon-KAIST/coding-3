# zoo_reflex_rc179.py
# -------------------
# rc179: rc82 if score >= 5, rc16 otherwise.
# Highest threshold in sweep — tests whether rc16 should dominate until
# big lead locked in.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC179Agent(ReflexRC82Agent):
    """rc82 if score >= 5, rc16 otherwise."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        if self._my_score(gameState) >= 5:
            return super()._chooseActionImpl(gameState)
        return ReflexRC16Agent._chooseActionImpl(self, gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC179Agent", second="ReflexRC179Agent"):
    return [ReflexRC179Agent(firstIndex), ReflexRC179Agent(secondIndex)]

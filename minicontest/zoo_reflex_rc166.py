# zoo_reflex_rc166.py
# -------------------
# rc166: rc82 if STRICTLY leading (>= 3 threshold), rc16 otherwise.
# More aggressive rc16-usage — pushes rc82 back to big-lead only.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC166Agent(ReflexRC82Agent):
    """rc82 if score >= 3, rc16 otherwise."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        if self._my_score(gameState) >= 3:
            return super()._chooseActionImpl(gameState)
        return ReflexRC16Agent._chooseActionImpl(self, gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC166Agent", second="ReflexRC166Agent"):
    return [ReflexRC166Agent(firstIndex), ReflexRC166Agent(secondIndex)]

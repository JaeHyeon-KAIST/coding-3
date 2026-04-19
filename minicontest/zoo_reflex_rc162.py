# zoo_reflex_rc162.py
# -------------------
# rc162: minimal switch — rc82 always EXCEPT when exactly tied (use rc16).
# Tests: what happens when we leave rc82 only at the single tied-score
# threshold? If rc160 (rc82 leading else rc16) hits 99%, maybe the rc16
# coverage of "behind" games is doing the work. This isolates.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC162Agent(ReflexRC82Agent):
    """rc82 always except score==0 tied → rc16."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        if self._my_score(gameState) == 0:
            return ReflexRC16Agent._chooseActionImpl(self, gameState)
        return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC162Agent", second="ReflexRC162Agent"):
    return [ReflexRC162Agent(firstIndex), ReflexRC162Agent(secondIndex)]

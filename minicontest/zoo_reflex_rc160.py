# zoo_reflex_rc160.py
# -------------------
# rc160: rc82 ALWAYS when possible, rc16 otherwise.
# Simplified 2-way switch — prove/disprove whether rc82 composite
# dominates all other slots. If rc82 is 100% solo and the switch
# costs ~2pp (rc152 98% vs rc82 solo), then max-rc82-time is the
# winning strategy.
#
# Slots:
#   score >= 1 (leading at all) : rc82
#   otherwise (tied or behind)  : rc16 Voronoi
#
# Testing whether removing rc52b + A1 entirely helps.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC160Agent(ReflexRC82Agent):
    """2-way: rc82 when leading, rc16 when tied/behind."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)
        if score >= 1:
            return super()._chooseActionImpl(gameState)
        return ReflexRC16Agent._chooseActionImpl(self, gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC160Agent", second="ReflexRC160Agent"):
    return [ReflexRC160Agent(firstIndex), ReflexRC160Agent(secondIndex)]

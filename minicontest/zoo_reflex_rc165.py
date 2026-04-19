# zoo_reflex_rc165.py
# -------------------
# rc165: rc160 but rc82 threshold raised to ≥2. rc16 handles 0..1 and ≤-1.
# Tests whether the small-lead range (+1) is better handled by rc16 (not rc82).

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC165Agent(ReflexRC82Agent):
    """rc82 if score >= 2, rc16 otherwise."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        if self._my_score(gameState) >= 2:
            return super()._chooseActionImpl(gameState)
        return ReflexRC16Agent._chooseActionImpl(self, gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC165Agent", second="ReflexRC165Agent"):
    return [ReflexRC165Agent(firstIndex), ReflexRC165Agent(secondIndex)]

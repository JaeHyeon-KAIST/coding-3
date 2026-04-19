# zoo_reflex_rc167.py
# -------------------
# rc167: rc82 at any lead OR deep-chase (≤ -5). rc16 for near-tied bands.
# Experiment — does rc82 in deep chase (when trailing hard) help recovery
# better than rc16 Voronoi?

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC167Agent(ReflexRC82Agent):
    """rc82 if score >= 1 or score <= -5, rc16 otherwise."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)
        if score >= 1 or score <= -5:
            return super()._chooseActionImpl(gameState)
        return ReflexRC16Agent._chooseActionImpl(self, gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC167Agent", second="ReflexRC167Agent"):
    return [ReflexRC167Agent(firstIndex), ReflexRC167Agent(secondIndex)]

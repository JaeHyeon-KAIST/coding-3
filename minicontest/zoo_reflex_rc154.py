# zoo_reflex_rc154.py
# -------------------
# rc154: 5-WAY score-conditioned switch. Extends rc152's 4-way by splitting
# the "near-tied" slot into tied vs. slight-deficit bands.
#
# Bands:
#   score ≥ +5     : rc82 big-lead composite
#   score +2..+4   : rc16 Voronoi small-lead
#   score 0..+1    : rc32 Pincer (aggressive hold)
#   score -2..-1   : A1 balanced
#   score ≤ -3     : rc52b REINFORCE chase

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc32 import ReflexRC32Agent
from zoo_reflex_rc52b import _RC52B_OVERRIDE
from zoo_reflex_A1 import _A1_OVERRIDE


class ReflexRC154Agent(ReflexRC82Agent, ReflexRC32Agent):
    """5-way score-conditioned switch. Multi-inherits rc32 for _pincer_target."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)

        if score >= 5:
            return super()._chooseActionImpl(gameState)
        if score >= 2:
            return ReflexRC16Agent._chooseActionImpl(self, gameState)
        if score >= 0:
            return ReflexRC32Agent._chooseActionImpl(self, gameState)

        saved = getattr(self, "_weights_override", None)
        try:
            if score <= -3 and _RC52B_OVERRIDE.get("w_off"):
                self._weights_override = _RC52B_OVERRIDE
            else:
                if _A1_OVERRIDE.get("w_off"):
                    self._weights_override = _A1_OVERRIDE
            from zoo_reflex_tuned import ReflexTunedAgent
            return ReflexTunedAgent._chooseActionImpl(self, gameState)
        finally:
            self._weights_override = saved


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC154Agent", second="ReflexRC154Agent"):
    return [ReflexRC154Agent(firstIndex), ReflexRC154Agent(secondIndex)]

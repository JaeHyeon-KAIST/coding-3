# zoo_reflex_rc156.py
# -------------------
# rc156: rc152's 4-way switch with tuned thresholds — tighter bands
# to route MORE turns through rc16/rc52b and FEWER through A1.
#
# Thresholds:
#   leading ≥ +3      : rc82 (was +5)
#   leading 1..2      : rc16 (was 1..4)
#   near-tied 0       : A1 only if exactly 0
#   chasing ≤ -1      : rc52b (was -3)
#
# Hypothesis: rc148's tightening failed only because it kept only 3 slots
# and ignored rc16 archetype. With 4 slots AND tighter thresholds,
# coverage shifts from A1 to champion regions.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc52b import _RC52B_OVERRIDE
from zoo_reflex_A1 import _A1_OVERRIDE


class ReflexRC156Agent(ReflexRC82Agent):
    """4-way switch with tighter bands than rc152."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)

        if score >= 3:
            return super()._chooseActionImpl(gameState)
        if score >= 1:
            return ReflexRC16Agent._chooseActionImpl(self, gameState)

        saved = getattr(self, "_weights_override", None)
        try:
            if score <= -1 and _RC52B_OVERRIDE.get("w_off"):
                self._weights_override = _RC52B_OVERRIDE
            else:
                if _A1_OVERRIDE.get("w_off"):
                    self._weights_override = _A1_OVERRIDE
            from zoo_reflex_tuned import ReflexTunedAgent
            return ReflexTunedAgent._chooseActionImpl(self, gameState)
        finally:
            self._weights_override = saved


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC156Agent", second="ReflexRC156Agent"):
    return [ReflexRC156Agent(firstIndex), ReflexRC156Agent(secondIndex)]

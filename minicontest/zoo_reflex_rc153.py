# zoo_reflex_rc153.py
# -------------------
# rc153: 4-way score-conditioned switch like rc152 but uses rc32
# (Pincer composite, 97.5% solo) instead of rc16 in the small-lead slot.
#
# rc152 achieved 98% with rc16 in that slot. Swapping to rc32 tests
# whether different-archetype small-lead-holders behave equivalently.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc32 import ReflexRC32Agent
from zoo_reflex_rc52b import _RC52B_OVERRIDE
from zoo_reflex_A1 import _A1_OVERRIDE


SCORE_BIG_LEAD = 5
SCORE_SMALL_LEAD = 1
SCORE_CHASE = -3


class ReflexRC153Agent(ReflexRC82Agent, ReflexRC32Agent):
    """4-way switch with rc32 Pincer in small-lead slot.

    Multi-inherits rc32 so _pincer_target method is available on self.
    MRO: rc153 → rc82 → ... → rc32 → A1 → tuned → core. rc82's
    _chooseActionImpl still dominates (super() call), but calling
    ReflexRC32Agent._chooseActionImpl explicitly still works.
    """

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)

        if score >= SCORE_BIG_LEAD:
            return super()._chooseActionImpl(gameState)

        if score >= SCORE_SMALL_LEAD:
            return ReflexRC32Agent._chooseActionImpl(self, gameState)

        saved = getattr(self, "_weights_override", None)
        try:
            if score <= SCORE_CHASE and _RC52B_OVERRIDE.get("w_off"):
                self._weights_override = _RC52B_OVERRIDE
            else:
                if _A1_OVERRIDE.get("w_off"):
                    self._weights_override = _A1_OVERRIDE
            from zoo_reflex_tuned import ReflexTunedAgent
            return ReflexTunedAgent._chooseActionImpl(self, gameState)
        finally:
            self._weights_override = saved


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC153Agent", second="ReflexRC153Agent"):
    return [ReflexRC153Agent(firstIndex), ReflexRC153Agent(secondIndex)]

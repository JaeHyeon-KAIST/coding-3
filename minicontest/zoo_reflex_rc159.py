# zoo_reflex_rc159.py
# -------------------
# rc159: rc152 with rc82 composite in BOTH chase and big-lead slots.
# Drops rc52b entirely — hypothesis: rc82 (100% solo) outperforms
# rc52b (92% solo) even when behind.
#
# Slots:
#   ≥ +5 : rc82 (big lead lock)
#   +1..+4 : rc16 Voronoi (small lead)
#   -2..0 : A1 balanced
#   ≤ -3 : rc82 (chase with composite)

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_A1 import _A1_OVERRIDE


class ReflexRC159Agent(ReflexRC82Agent):
    """4-way: rc82/rc16/A1/rc82 — rc82 replaces rc52b in chase."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)
        if score >= 5 or score <= -3:
            # Big lead OR chase → rc82 composite
            return super()._chooseActionImpl(gameState)
        if score >= 1:
            return ReflexRC16Agent._chooseActionImpl(self, gameState)
        # Near-tied → A1
        saved = getattr(self, "_weights_override", None)
        try:
            if _A1_OVERRIDE.get("w_off"):
                self._weights_override = _A1_OVERRIDE
            from zoo_reflex_tuned import ReflexTunedAgent
            return ReflexTunedAgent._chooseActionImpl(self, gameState)
        finally:
            self._weights_override = saved


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC159Agent", second="ReflexRC159Agent"):
    return [ReflexRC159Agent(firstIndex), ReflexRC159Agent(secondIndex)]

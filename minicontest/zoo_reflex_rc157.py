# zoo_reflex_rc157.py
# -------------------
# rc157: rc152 without A1 slot — rc52b covers ALL negative scores.
# Hypothesis: A1 (86% solo) is the weakest member of rc152's 4-way
# switch. Replacing it with rc52b (92%) in the near-tied band should
# lift average. 3-way: big-lead→rc82, small-lead→rc16, otherwise→rc52b.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc52b import _RC52B_OVERRIDE


class ReflexRC157Agent(ReflexRC82Agent):
    """3-way switch: rc82 big-lead, rc16 small-lead, rc52b otherwise."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)
        if score >= 5:
            return super()._chooseActionImpl(gameState)
        if score >= 1:
            return ReflexRC16Agent._chooseActionImpl(self, gameState)
        saved = getattr(self, "_weights_override", None)
        try:
            if _RC52B_OVERRIDE.get("w_off"):
                self._weights_override = _RC52B_OVERRIDE
            from zoo_reflex_tuned import ReflexTunedAgent
            return ReflexTunedAgent._chooseActionImpl(self, gameState)
        finally:
            self._weights_override = saved


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC157Agent", second="ReflexRC157Agent"):
    return [ReflexRC157Agent(firstIndex), ReflexRC157Agent(secondIndex)]

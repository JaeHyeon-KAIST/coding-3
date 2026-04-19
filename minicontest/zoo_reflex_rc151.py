# zoo_reflex_rc151.py
# -------------------
# rc151: tighter thresholds on rc148's score-conditioned switch.
# rc148 used LEAD=+5, CHASE=-3 and hit 96%. Tightening the bands
# should trigger switches earlier, potentially smoothing edge cases
# where rc148 spent too long on A1 in near-tied early game.
#
# Thresholds:
#   leading ≥ +2      : rc82 (100% composite, lock lead earlier)
#   chasing ≤ -1      : rc52b (push offense sooner)
#   otherwise (0, +1) : A1 balanced

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc52b import _RC52B_OVERRIDE
from zoo_reflex_A1 import _A1_OVERRIDE


SCORE_LEAD = 2
SCORE_CHASE = -1


class ReflexRC151Agent(ReflexRC82Agent):
    """Score-conditioned switch with tighter bands than rc148."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)
        if score >= SCORE_LEAD:
            return super()._chooseActionImpl(gameState)
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
               first="ReflexRC151Agent", second="ReflexRC151Agent"):
    return [ReflexRC151Agent(firstIndex), ReflexRC151Agent(secondIndex)]

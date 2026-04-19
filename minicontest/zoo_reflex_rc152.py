# zoo_reflex_rc152.py
# -------------------
# rc152: 4-WAY score-conditioned switch. Adds rc16 (Voronoi champion)
# as the "small lead" slot between rc148's A1 and rc82 bands.
#
# Thresholds (rc148's LEAD=5/CHASE=-3 preserved, rc16 band inserted):
#   leading ≥ +5       : rc82 composite (lock big lead)
#   leading 1..4       : rc16 Voronoi (territorial — rc16 uses A1 base + voronoi overlay)
#   near-tied (-2..0)  : A1 balanced
#   chasing ≤ -3       : rc52b REINFORCE (aggressive offense)
#
# Implementation: subclass ReflexRC82Agent (big-lead branch uses super).
# For rc16 slot, temporarily use an attached rc16 helper agent's logic.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc52b import _RC52B_OVERRIDE
from zoo_reflex_A1 import _A1_OVERRIDE


SCORE_BIG_LEAD = 5
SCORE_SMALL_LEAD = 1
SCORE_CHASE = -3


class ReflexRC152Agent(ReflexRC82Agent):
    """4-way score-conditioned switch: rc82 / rc16 / A1 / rc52b."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)

        if score >= SCORE_BIG_LEAD:
            return super()._chooseActionImpl(gameState)

        if score >= SCORE_SMALL_LEAD:
            # rc16 branch — call ReflexRC16Agent's logic directly on self
            # (self is a ReflexRC82Agent, which inherits ReflexA1Agent —
            # so all attributes rc16 needs are available).
            return ReflexRC16Agent._chooseActionImpl(self, gameState)

        # Near-tied or chasing → weight override
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
               first="ReflexRC152Agent", second="ReflexRC152Agent"):
    return [ReflexRC152Agent(firstIndex), ReflexRC152Agent(secondIndex)]

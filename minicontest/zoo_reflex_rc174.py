# zoo_reflex_rc174.py
# -------------------
# rc174: carry-count switch. rc82 when one of us is carrying ≥ 5 food
# (return-home urgency), rc160-pattern otherwise.
#
# Heuristic: rc82's composite is better at getting home under ghost
# pressure (rc29 REVERSE disrupts, rc44 stacking). rc16's Voronoi can
# be too territorial-focused when we need to cash in.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


CARRY_THRESHOLD = 5


class ReflexRC174Agent(ReflexRC82Agent):
    """rc82 when any teammate carrying ≥5; rc160 pattern else."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _we_carrying(self, gameState):
        team = self.getTeam(gameState)
        return max(
            int(gameState.getAgentState(i).numCarrying or 0) for i in team
        )

    def _chooseActionImpl(self, gameState):
        if self._we_carrying(gameState) >= CARRY_THRESHOLD:
            return super()._chooseActionImpl(gameState)
        if self._my_score(gameState) >= 1:
            return super()._chooseActionImpl(gameState)
        return ReflexRC16Agent._chooseActionImpl(self, gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC174Agent", second="ReflexRC174Agent"):
    return [ReflexRC174Agent(firstIndex), ReflexRC174Agent(secondIndex)]

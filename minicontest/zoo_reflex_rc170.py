# zoo_reflex_rc170.py
# -------------------
# rc170: CONSENSUS rc82 + rc16. Compute both agents' preferred actions;
# if they agree, use that action; if they disagree, fall back to rc160
# rule (rc82 if leading else rc16).
#
# Hypothesis: when both champions agree, the action is near-certain
# to be best. When they disagree, score decides which specialist wins.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent


class ReflexRC170Agent(ReflexRC82Agent):
    """Consensus rc82 ∧ rc16; fallback to score-based rc160."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        rc82_action = super()._chooseActionImpl(gameState)
        rc16_action = ReflexRC16Agent._chooseActionImpl(self, gameState)
        if rc82_action == rc16_action:
            return rc82_action
        # Disagreement → rc160 tie-break
        return rc82_action if self._my_score(gameState) >= 1 else rc16_action


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC170Agent", second="ReflexRC170Agent"):
    return [ReflexRC170Agent(firstIndex), ReflexRC170Agent(secondIndex)]

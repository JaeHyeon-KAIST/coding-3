# zoo_reflex_rc149.py
# -------------------
# rc149: GAME-PHASE switching based on elapsed moves.
#
# Game phases (1200-move total):
#   early   (0-200)      → rc82 composite (exploration + rc29 disruption helps)
#   mid     (200-900)    → rc52b REINFORCE (offense-leaning weights maximize food)
#   endgame (900+)       → rc82 composite (defend/capture late)
#
# Phase counter kept in TEAM shared state (both teammates see same count).

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc52b import _RC52B_OVERRIDE
from zoo_core import TEAM


PHASE_EARLY_END = 200
PHASE_MID_END = 900


class ReflexRC149Agent(ReflexRC82Agent):
    """Phase-conditioned switch between rc82 and rc52b."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        if not hasattr(TEAM, "rc149_turn"):
            TEAM.rc149_turn = 0

    def _chooseActionImpl(self, gameState):
        try:
            TEAM.rc149_turn = getattr(TEAM, "rc149_turn", 0) + 1
            turn = TEAM.rc149_turn
        except Exception:
            turn = 0

        if turn < PHASE_EARLY_END or turn > PHASE_MID_END:
            # Early or late phase → rc82 composite.
            return super()._chooseActionImpl(gameState)

        # Mid-game → rc52b weights via ReflexTunedAgent base.
        saved = getattr(self, "_weights_override", None)
        try:
            if _RC52B_OVERRIDE.get("w_off"):
                self._weights_override = _RC52B_OVERRIDE
            from zoo_reflex_tuned import ReflexTunedAgent
            return ReflexTunedAgent._chooseActionImpl(self, gameState)
        finally:
            self._weights_override = saved


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC149Agent", second="ReflexRC149Agent"):
    return [ReflexRC149Agent(firstIndex), ReflexRC149Agent(secondIndex)]

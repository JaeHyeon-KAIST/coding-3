# zoo_reflex_rc172.py
# -------------------
# rc172: rc160 + endgame guard. rc160 until turn 1000, then rc82-locked
# if leading to preserve the lead. Hypothesis: rc16's territorial push
# is risky in last ~200 moves when keeping the lead matters more than
# gaining more.
#
# Slots:
#   turn < 1000:
#     score >= 1 : rc82
#     score <= 0 : rc16
#   turn >= 1000 (endgame):
#     score >= 1 : rc82 (lock lead)
#     score <= 0 : rc16 (still push to gain)

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_core import TEAM


ENDGAME_TURN = 1000


class ReflexRC172Agent(ReflexRC82Agent):
    """rc160 + endgame awareness (kept lead locks rc82 faster)."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        if not hasattr(TEAM, "rc172_turn"):
            TEAM.rc172_turn = 0

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        try:
            TEAM.rc172_turn = getattr(TEAM, "rc172_turn", 0) + 1
            turn = TEAM.rc172_turn
        except Exception:
            turn = 0

        score = self._my_score(gameState)

        if score >= 1:
            return super()._chooseActionImpl(gameState)

        # score <= 0: normally rc16, but endgame tied with no capture → rc82
        if turn >= ENDGAME_TURN and score == 0:
            return super()._chooseActionImpl(gameState)

        return ReflexRC16Agent._chooseActionImpl(self, gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC172Agent", second="ReflexRC172Agent"):
    return [ReflexRC172Agent(firstIndex), ReflexRC172Agent(secondIndex)]

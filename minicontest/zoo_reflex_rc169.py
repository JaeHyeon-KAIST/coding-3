# zoo_reflex_rc169.py
# -------------------
# rc169: rc82 default, rc32 pincer when timeleft < 200 (endgame kill).
# Hypothesis: in the last ~50 turns of a close game, aggressive pincer
# kills of the opponent's carrier close out the win faster than rc82's
# balanced state-stacking. Orthogonal axis: time-phase, not score.
#
# Fire: timeleft < 200 (last 200 plies = ~50 team-turns) → rc32.
# Otherwise rc82.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc32 import ReflexRC32Agent


RC169_ENDGAME_TIMELEFT = 200


class ReflexRC169Agent(ReflexRC82Agent):
    """rc82 default, rc32 pincer in last ~200 plies."""

    def _timeleft(self, gameState):
        try:
            return int(getattr(gameState.data, "timeleft", 1200) or 1200)
        except Exception:
            return 1200

    def _chooseActionImpl(self, gameState):
        if self._timeleft(gameState) < RC169_ENDGAME_TIMELEFT:
            return ReflexRC32Agent._chooseActionImpl(self, gameState)
        return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC169Agent", second="ReflexRC169Agent"):
    return [ReflexRC169Agent(firstIndex), ReflexRC169Agent(secondIndex)]

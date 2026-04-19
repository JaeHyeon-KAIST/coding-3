# zoo_reflex_rc98.py
# ------------------
# rc98: Time-adaptive champion switch — rc02 for first RC98_SWITCH
# turns, then rc82 afterward.
#
# Hypothesis: early game is dominated by positional/defensive play
# (rc02 Tarjan AP excels at holding choke points while food is
# dense), while late game needs offensive pressure to break ties
# or close the gap (rc82 combo excels at both-side tactical play).
#
# Switch turn per agent (each agent has its own turn counter since
# both behave independently in createTeam). After RC98_SWITCH turns,
# the agent delegates to rc82's chooseAction rather than rc02's.

from __future__ import annotations

from collections import deque

from zoo_reflex_A1 import ReflexA1Agent
from zoo_reflex_rc02 import ReflexRC02Agent, _articulation_points
from zoo_reflex_rc82 import ReflexRC82Agent
from game import Directions


RC98_SWITCH = 200    # switch from rc02 to rc82 after this many of our turns


class ReflexRC98Agent(ReflexA1Agent):
    """Time-adaptive: rc02 early, rc82 late."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self.tarjan_aps = _articulation_points(gameState.getWalls())
        except Exception:
            self.tarjan_aps = frozenset()
        try:
            self._rc82_hist = deque(maxlen=4)
        except Exception:
            pass
        self._rc44_turn = 0
        self._rc98_turn = 0

    def _chooseActionImpl(self, gameState):
        self._rc98_turn += 1
        try:
            if self._rc98_turn <= RC98_SWITCH:
                return ReflexRC02Agent._chooseActionImpl(self, gameState)
            return ReflexRC82Agent._chooseActionImpl(self, gameState)
        except Exception:
            return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC98Agent", second="ReflexRC98Agent"):
    return [ReflexRC98Agent(firstIndex), ReflexRC98Agent(secondIndex)]

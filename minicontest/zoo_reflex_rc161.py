# zoo_reflex_rc161.py
# -------------------
# rc161: 3-champion score switch. All slots use 100% composite champions.
#
# Slots:
#   score ≥ +1 (leading any amount) : rc82 (rc29+rc44 composite)
#   score == 0 (tied exactly)       : rc131 (rc32 Pincer + rc82 DEF)
#   score ≤ -1 (behind)             : rc16 (Voronoi)
#
# All three are 100%-tier solos. Hypothesis: no dilution — all champions
# agree on good moves; their differences matter only in disagreement
# zones, where switching picks the state-best choice.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent
import importlib
_rc131_mod = importlib.import_module("zoo_reflex_rc131")
_RC131_CLASSES = [c for c in dir(_rc131_mod) if c.startswith("ReflexRC131")]


class ReflexRC161Agent(ReflexRC82Agent):
    """3-champion score switch. No weight-mix slots."""

    def __init__(self, index, timeForComputing=0.1):
        super().__init__(index, timeForComputing=timeForComputing)
        self._rc131_helper = None

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            team = _rc131_mod.createTeam(self.index, self.index, self.red)
            self._rc131_helper = team[0]
            self._rc131_helper.registerInitialState(gameState)
        except Exception:
            self._rc131_helper = None

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)
        if score >= 1:
            return super()._chooseActionImpl(gameState)
        if score == 0 and self._rc131_helper is not None:
            try:
                return self._rc131_helper.chooseAction(gameState)
            except Exception:
                pass
        return ReflexRC16Agent._chooseActionImpl(self, gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC161Agent", second="ReflexRC161Agent"):
    return [ReflexRC161Agent(firstIndex), ReflexRC161Agent(secondIndex)]

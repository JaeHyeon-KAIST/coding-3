# zoo_reflex_rc155.py
# -------------------
# rc155: rc152's 4-way score switch but with rc22 (neural distill) in the
# CHASE slot instead of rc52b. rc22 is MLP-distilled from rc82 teacher,
# reaching 88% solo — architecturally different from linear-Q rc52b.
# Hypothesis: when chasing, neural policy's teacher-mimicking behavior
# may find recovery paths that linear-Q doesn't see.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_A1 import _A1_OVERRIDE

import importlib
_distill_mod = importlib.import_module("zoo_distill_rc22")


SCORE_BIG_LEAD = 5
SCORE_SMALL_LEAD = 1
SCORE_CHASE = -3


class ReflexRC155Agent(ReflexRC82Agent):
    """4-way score switch: rc82/rc16/A1/rc22(chase)."""

    def __init__(self, index, timeForComputing=0.1):
        super().__init__(index, timeForComputing=timeForComputing)
        self._rc22_helper = None

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        # Lazily instantiate rc22 helper for CHASE slot.
        try:
            self._rc22_helper = _distill_mod.createTeam(
                self.index, self.index, self.red)[0]
            self._rc22_helper.registerInitialState(gameState)
        except Exception:
            self._rc22_helper = None

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)

        if score >= SCORE_BIG_LEAD:
            return super()._chooseActionImpl(gameState)

        if score >= SCORE_SMALL_LEAD:
            return ReflexRC16Agent._chooseActionImpl(self, gameState)

        if score <= SCORE_CHASE and self._rc22_helper is not None:
            try:
                return self._rc22_helper.chooseAction(gameState)
            except Exception:
                pass  # fall through to A1

        # Near-tied or rc22 failed → A1 balanced
        saved = getattr(self, "_weights_override", None)
        try:
            if _A1_OVERRIDE.get("w_off"):
                self._weights_override = _A1_OVERRIDE
            from zoo_reflex_tuned import ReflexTunedAgent
            return ReflexTunedAgent._chooseActionImpl(self, gameState)
        finally:
            self._weights_override = saved


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC155Agent", second="ReflexRC155Agent"):
    return [ReflexRC155Agent(firstIndex), ReflexRC155Agent(secondIndex)]

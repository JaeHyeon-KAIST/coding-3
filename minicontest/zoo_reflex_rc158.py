# zoo_reflex_rc158.py
# -------------------
# rc158: rc152 with HYSTERESIS — once we enter big-lead territory
# (rc82 slot), stay there until the lead drops below SAFE_EXIT.
# Prevents flip-flopping between rc82 and rc16 when score oscillates
# around the threshold.
#
# State stored in TEAM.rc158_locked_rc82 (shared across teammates).

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc52b import _RC52B_OVERRIDE
from zoo_reflex_A1 import _A1_OVERRIDE
from zoo_core import TEAM


LOCK_ENTRY = 5      # enter rc82 lock when score reaches +5
LOCK_EXIT = 2       # release lock only when score drops below +2
SMALL_LEAD = 1
CHASE = -3


class ReflexRC158Agent(ReflexRC82Agent):
    """rc152 with rc82 hysteresis to stabilise big-lead switching."""

    def _my_score(self, gameState):
        s = gameState.getScore()
        return s if self.red else -s

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        TEAM.rc158_locked_rc82 = False

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)
        locked = getattr(TEAM, "rc158_locked_rc82", False)
        if locked and score < LOCK_EXIT:
            TEAM.rc158_locked_rc82 = False
            locked = False
        if not locked and score >= LOCK_ENTRY:
            TEAM.rc158_locked_rc82 = True
            locked = True
        if locked:
            return super()._chooseActionImpl(gameState)

        if score >= SMALL_LEAD:
            return ReflexRC16Agent._chooseActionImpl(self, gameState)

        saved = getattr(self, "_weights_override", None)
        try:
            if score <= CHASE and _RC52B_OVERRIDE.get("w_off"):
                self._weights_override = _RC52B_OVERRIDE
            else:
                if _A1_OVERRIDE.get("w_off"):
                    self._weights_override = _A1_OVERRIDE
            from zoo_reflex_tuned import ReflexTunedAgent
            return ReflexTunedAgent._chooseActionImpl(self, gameState)
        finally:
            self._weights_override = saved


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC158Agent", second="ReflexRC158Agent"):
    return [ReflexRC158Agent(firstIndex), ReflexRC158Agent(secondIndex)]

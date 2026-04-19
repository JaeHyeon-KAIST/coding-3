# zoo_reflex_rc141.py
# -------------------
# rc141: ROLE-ASYMMETRIC — rc52b (alt REINFORCE, 92% solo) on OFFENSE,
# rc82 (100% composite) on DEFENSE.
#
# Same archetype as rc140 but using the better-trained REINFORCE variant.
# rc52b beats rc52 by 2pp solo (92 vs 90); if the asymmetric bonus scales,
# rc141 target is 93-95% (vs rc140's 91%).

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc52b import _RC52B_OVERRIDE
from zoo_core import TEAM


class ReflexRC141Agent(ReflexRC82Agent):
    """rc52b for offense, rc82 full composite for defense."""

    def __init__(self, index, timeForComputing=0.1):
        super().__init__(index, timeForComputing=timeForComputing)
        self._rc52b_override = _RC52B_OVERRIDE

    def _chooseActionImpl(self, gameState):
        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"

        if role == "OFFENSE":
            saved = getattr(self, "_weights_override", None)
            try:
                if self._rc52b_override.get("w_off"):
                    self._weights_override = self._rc52b_override
                from zoo_reflex_tuned import ReflexTunedAgent
                return ReflexTunedAgent._chooseActionImpl(self, gameState)
            except Exception:
                pass
            finally:
                self._weights_override = saved

        return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC141Agent", second="ReflexRC141Agent"):
    return [ReflexRC141Agent(firstIndex), ReflexRC141Agent(secondIndex)]

# zoo_reflex_rc143.py
# -------------------
# rc143: ROLE-ASYMMETRIC — rc52b (REINFORCE, 92% solo) on OFFENSE,
# rc16 (Voronoi A1, 100% solo) on DEFENSE.
#
# Alternative to rc141 (which used rc82 DEF and got 90%, below rc52b solo).
# Hypothesis: rc82 DEF is composite & A1-assuming; rc16 DEF is A1-compatible
# with only a Voronoi feature overlay. A learned-offense + A1-compatible-DEF
# combo may preserve the rc52b OFF skill better than rc141 did.

from __future__ import annotations

from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc52b import _RC52B_OVERRIDE
from zoo_core import TEAM


class ReflexRC143Agent(ReflexRC16Agent):
    """rc52b OFFENSE + rc16 Voronoi DEFENSE."""

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
               first="ReflexRC143Agent", second="ReflexRC143Agent"):
    return [ReflexRC143Agent(firstIndex), ReflexRC143Agent(secondIndex)]

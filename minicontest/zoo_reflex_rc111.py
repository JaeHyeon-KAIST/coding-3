# zoo_reflex_rc111.py
# ------------------
# rc111: rc109 (rc16+rc29 OFF + rc82 DEF) + rc21 layout multiplier.
#
# Adds layout-class weight scaling to the 5th 100% champion.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc109 import ReflexRC109OffenseAgent
from zoo_reflex_rc21 import _layout_class, RC21_MULT_TABLE


class _RC111LayoutMixin:
    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self._rc111_class = _layout_class(gameState.getWalls())
        except Exception:
            self._rc111_class = "MEDIUM"

    def _get_weights(self):
        try:
            base = super()._get_weights()
        except Exception:
            return {}
        if not base:
            return base
        try:
            cls = getattr(self, "_rc111_class", "MEDIUM")
            role = TEAM.role.get(self.index, "OFFENSE")
            mult = RC21_MULT_TABLE.get(cls, {}).get(role, 1.0)
            if mult == 1.0:
                return base
            return {k: (v * mult) for k, v in base.items()}
        except Exception:
            return base


class ReflexRC111OffenseAgent(_RC111LayoutMixin, ReflexRC109OffenseAgent):
    pass


class ReflexRC111DefenseAgent(_RC111LayoutMixin, ReflexRC82Agent):
    pass


def createTeam(firstIndex, secondIndex, isRed,
               first="rc111-offense", second="rc111-defense"):
    return [ReflexRC111OffenseAgent(firstIndex),
            ReflexRC111DefenseAgent(secondIndex)]

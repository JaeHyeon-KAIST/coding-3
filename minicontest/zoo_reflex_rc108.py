# zoo_reflex_rc108.py
# ------------------
# rc108: rc105 (rc16 OFF + rc82 DEF) + rc21 layout multiplier.
#
# Stacks layout-class weight scaling (×1.10/×0.90) on top of the
# rc105 composition. Tests whether layout conditioning adds lift
# to an already-perfect baseline or saturates.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc21 import _layout_class, RC21_MULT_TABLE


class _RC108LayoutMixin:
    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self._rc108_class = _layout_class(gameState.getWalls())
        except Exception:
            self._rc108_class = "MEDIUM"

    def _get_weights(self):
        try:
            base = super()._get_weights()
        except Exception:
            return {}
        if not base:
            return base
        try:
            cls = getattr(self, "_rc108_class", "MEDIUM")
            role = TEAM.role.get(self.index, "OFFENSE")
            mult = RC21_MULT_TABLE.get(cls, {}).get(role, 1.0)
            if mult == 1.0:
                return base
            return {k: (v * mult) for k, v in base.items()}
        except Exception:
            return base


class ReflexRC108OffenseAgent(_RC108LayoutMixin, ReflexRC16Agent):
    pass


class ReflexRC108DefenseAgent(_RC108LayoutMixin, ReflexRC82Agent):
    pass


def createTeam(firstIndex, secondIndex, isRed,
               first="rc108-offense", second="rc108-defense"):
    return [ReflexRC108OffenseAgent(firstIndex),
            ReflexRC108DefenseAgent(secondIndex)]

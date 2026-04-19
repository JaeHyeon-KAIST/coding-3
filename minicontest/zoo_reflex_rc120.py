# zoo_reflex_rc120.py
# ------------------
# rc120: rc116 (6th champion) + rc21 layout multiplier.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc116 import ReflexRC116OffenseAgent
from zoo_reflex_rc21 import _layout_class, RC21_MULT_TABLE


class _RC120LayoutMixin:
    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self._rc120_class = _layout_class(gameState.getWalls())
        except Exception:
            self._rc120_class = "MEDIUM"

    def _get_weights(self):
        try:
            base = super()._get_weights()
        except Exception:
            return {}
        if not base:
            return base
        try:
            cls = getattr(self, "_rc120_class", "MEDIUM")
            role = TEAM.role.get(self.index, "OFFENSE")
            mult = RC21_MULT_TABLE.get(cls, {}).get(role, 1.0)
            if mult == 1.0:
                return base
            return {k: (v * mult) for k, v in base.items()}
        except Exception:
            return base


class ReflexRC120OffenseAgent(_RC120LayoutMixin, ReflexRC116OffenseAgent):
    pass


class ReflexRC120DefenseAgent(_RC120LayoutMixin, ReflexRC82Agent):
    pass


def createTeam(firstIndex, secondIndex, isRed,
               first="rc120-offense", second="rc120-defense"):
    return [ReflexRC120OffenseAgent(firstIndex),
            ReflexRC120DefenseAgent(secondIndex)]

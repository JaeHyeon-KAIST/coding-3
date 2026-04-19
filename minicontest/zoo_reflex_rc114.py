# zoo_reflex_rc114.py
# ------------------
# rc114: rc109 + rc21 layout mult + rc48 WHCA* (triple-layer on 5th champ).
#
# Stacks all three known-good orthogonal layers on rc109:
#   rc109: rc16+rc29 OFF + rc82 DEF (100% base)
#   + rc21: layout-class weight multiplier
#   + rc48: 1-step teammate cell deconflict
#
# Tests whether full three-layer stacking on a champion composition
# holds at 100% or degrades.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc109 import ReflexRC109OffenseAgent
from zoo_reflex_rc97 import _RC97DeconflictMixin
from zoo_reflex_rc21 import _layout_class, RC21_MULT_TABLE


class _RC114LayoutMixin:
    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self._rc114_class = _layout_class(gameState.getWalls())
        except Exception:
            self._rc114_class = "MEDIUM"

    def _get_weights(self):
        try:
            base = super()._get_weights()
        except Exception:
            return {}
        if not base:
            return base
        try:
            cls = getattr(self, "_rc114_class", "MEDIUM")
            role = TEAM.role.get(self.index, "OFFENSE")
            mult = RC21_MULT_TABLE.get(cls, {}).get(role, 1.0)
            if mult == 1.0:
                return base
            return {k: (v * mult) for k, v in base.items()}
        except Exception:
            return base


class ReflexRC114OffenseAgent(_RC97DeconflictMixin, _RC114LayoutMixin,
                              ReflexRC109OffenseAgent):
    pass


class ReflexRC114DefenseAgent(_RC97DeconflictMixin, _RC114LayoutMixin,
                              ReflexRC82Agent):
    pass


def createTeam(firstIndex, secondIndex, isRed,
               first="rc114-offense", second="rc114-defense"):
    return [ReflexRC114OffenseAgent(firstIndex),
            ReflexRC114DefenseAgent(secondIndex)]

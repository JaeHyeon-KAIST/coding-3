# zoo_reflex_rc93.py
# ------------------
# rc93: rc90 (rc82 OFF + rc32 DEF) + rc21 layout multiplier stack.
#
# rc90 reached 97.5% — strongest asymmetric. rc21 adds a
# layout-class-conditioned weight multiplier (×1.10/×0.90 per
# class). The two are orthogonal: rc90 chooses WHICH agent class
# plays each role; rc21 scales the features those classes use.
#
# Implementation: subclass both rc82 and rc32 with an rc21-style
# _get_weights override that applies the layout multiplier on top of
# whatever weights the base class returns.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc32 import ReflexRC32Agent
from zoo_reflex_rc21 import _layout_class, RC21_MULT_TABLE


class _LayoutAwareMixin:
    """Mixin that applies rc21 layout-class multiplier on _get_weights."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self._rc93_class = _layout_class(gameState.getWalls())
        except Exception:
            self._rc93_class = "MEDIUM"

    def _get_weights(self):
        try:
            base = super()._get_weights()
        except Exception:
            return {}
        if not base:
            return base
        try:
            cls = getattr(self, "_rc93_class", "MEDIUM")
            role = TEAM.role.get(self.index, "OFFENSE")
            mult = RC21_MULT_TABLE.get(cls, {}).get(role, 1.0)
            if mult == 1.0:
                return base
            return {k: (v * mult) for k, v in base.items()}
        except Exception:
            return base


class ReflexRC93OffenseAgent(_LayoutAwareMixin, ReflexRC82Agent):
    """rc82 combo on OFFENSE with rc21 layout multiplier."""


class ReflexRC93DefenseAgent(_LayoutAwareMixin, ReflexRC32Agent):
    """rc32 pincer on DEFENSE with rc21 layout multiplier."""


def createTeam(firstIndex, secondIndex, isRed,
               first="rc93-offense", second="rc93-defense"):
    return [ReflexRC93OffenseAgent(firstIndex),
            ReflexRC93DefenseAgent(secondIndex)]

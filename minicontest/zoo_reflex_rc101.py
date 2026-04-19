# zoo_reflex_rc101.py
# ------------------
# rc101: Quad-stack on the rc90 skeleton — rc82 OFF + rc32 DEF +
# rc48 WHCA* deconflict + rc21 layout multiplier.
#
# Layering all four known-good orthogonal axes:
#   1. Role-asymmetric (rc82 OFF / rc32 DEF) — rc90 at 97.5%
#   2. Teammate deconflict (rc48) — rc97 at 97.5%
#   3. Layout-class weight multiplier (rc21) — rc93 at 95%+
#
# Combined via mixins: each role-specialized agent wraps its rc82
# or rc32 base with both _RC97DeconflictMixin (WHCA*) and an
# rc21-style layout multiplier on _get_weights.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc32 import ReflexRC32Agent
from zoo_reflex_rc97 import _RC97DeconflictMixin
from zoo_reflex_rc21 import _layout_class, RC21_MULT_TABLE


class _LayoutMultMixin:
    """Applies rc21 layout-class multiplier on _get_weights."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self._rc101_class = _layout_class(gameState.getWalls())
        except Exception:
            self._rc101_class = "MEDIUM"

    def _get_weights(self):
        try:
            base = super()._get_weights()
        except Exception:
            return {}
        if not base:
            return base
        try:
            cls = getattr(self, "_rc101_class", "MEDIUM")
            role = TEAM.role.get(self.index, "OFFENSE")
            mult = RC21_MULT_TABLE.get(cls, {}).get(role, 1.0)
            if mult == 1.0:
                return base
            return {k: (v * mult) for k, v in base.items()}
        except Exception:
            return base


class ReflexRC101OffenseAgent(_RC97DeconflictMixin, _LayoutMultMixin, ReflexRC82Agent):
    """rc82 OFF + WHCA* + layout mult."""


class ReflexRC101DefenseAgent(_RC97DeconflictMixin, _LayoutMultMixin, ReflexRC32Agent):
    """rc32 DEF + WHCA* + layout mult."""


def createTeam(firstIndex, secondIndex, isRed,
               first="rc101-offense", second="rc101-defense"):
    return [ReflexRC101OffenseAgent(firstIndex),
            ReflexRC101DefenseAgent(secondIndex)]

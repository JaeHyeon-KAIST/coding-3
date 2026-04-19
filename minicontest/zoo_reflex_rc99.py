# zoo_reflex_rc99.py
# ------------------
# rc99: Layout-adaptive asymmetric team.
#
# rc90 uses rc32 Pincer as defender (97.5%). rc91 uses rc16 Voronoi
# as defender (92.5%). The choice of defender likely depends on
# maze geometry — rc32's pincer exploits corridor structure while
# rc16's territorial pressure works better in open maps. rc99
# picks defender class based on rc21's layout class at init:
#
#   TIGHT   : rc32 Pincer (corridors = pincer opportunities)
#   OPEN    : rc16 Voronoi (territory matters more)
#   MEDIUM  : rc02 Tarjan AP (balanced default)
#
# OFFENSE is always rc82 (our best-offense single agent).

from __future__ import annotations

from zoo_reflex_rc02 import ReflexRC02Agent
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc32 import ReflexRC32Agent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc21 import _layout_class


def createTeam(firstIndex, secondIndex, isRed,
               first="Adaptive", second="Adaptive"):
    """rc82 OFF + layout-adaptive DEF (rc32/rc16/rc02)."""
    # We need the layout; but createTeam has no gameState. Defender
    # class selection happens at registerInitialState (deferred). A
    # simple approach: initialize DEFENSE as rc02Agent and swap
    # internally based on layout. Cleaner: use a thin wrapper that
    # dispatches on first chooseAction.
    return [ReflexRC82Agent(firstIndex),
            _AdaptiveDefender(secondIndex)]


class _AdaptiveDefender(ReflexRC02Agent):
    """Defender that swaps its base class behavior by layout at init."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            cls = _layout_class(gameState.getWalls())
        except Exception:
            cls = "MEDIUM"
        self._rc99_def_class = cls

    def _chooseActionImpl(self, gameState):
        cls = getattr(self, "_rc99_def_class", "MEDIUM")
        try:
            if cls == "TIGHT":
                return ReflexRC32Agent._chooseActionImpl(self, gameState)
            elif cls == "OPEN":
                return ReflexRC16Agent._chooseActionImpl(self, gameState)
            else:
                return ReflexRC02Agent._chooseActionImpl(self, gameState)
        except Exception:
            return super()._chooseActionImpl(gameState)

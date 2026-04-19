# zoo_reflex_rc107.py
# ------------------
# rc107: rc105 (rc16 OFF + rc82 DEF) + rc48 WHCA* teammate deconflict.
#
# rc105 reached 100% in Batch I. rc48 overlay (90% solo) adds a
# 1-step teammate-cell projection filter. Both agents get the
# WHCA* deconflict mixin on top of their base (rc16 or rc82).

from __future__ import annotations

from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc97 import _RC97DeconflictMixin


class ReflexRC107OffenseAgent(_RC97DeconflictMixin, ReflexRC16Agent):
    """rc16 Voronoi on OFFENSE + WHCA* deconflict."""


class ReflexRC107DefenseAgent(_RC97DeconflictMixin, ReflexRC82Agent):
    """rc82 combo on DEFENSE + WHCA* deconflict."""


def createTeam(firstIndex, secondIndex, isRed,
               first="rc107-offense", second="rc107-defense"):
    return [ReflexRC107OffenseAgent(firstIndex),
            ReflexRC107DefenseAgent(secondIndex)]

# zoo_reflex_rc118.py
# ------------------
# rc118: rc109 with rc48 WHCA* on DEFENDER only (asymmetric overlay).
#
# rc109 = rc16+rc29 OFF + rc82 DEF. rc112 put rc48 on both sides.
# rc118 applies rc48 only to the defender — offense stays as rc109's
# compound rc16+rc29, defender gets rc82+rc48. Tests whether split
# deconfliction (one agent respecting teammate cell, the other not)
# is better or worse than mutual.

from __future__ import annotations

from zoo_reflex_rc109 import ReflexRC109OffenseAgent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc97 import _RC97DeconflictMixin


class ReflexRC118DefenseAgent(_RC97DeconflictMixin, ReflexRC82Agent):
    """rc82 DEF + WHCA* deconflict."""


def createTeam(firstIndex, secondIndex, isRed,
               first="rc118-offense", second="rc118-defense"):
    return [ReflexRC109OffenseAgent(firstIndex),
            ReflexRC118DefenseAgent(secondIndex)]

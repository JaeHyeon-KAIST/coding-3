# zoo_reflex_rc112.py
# ------------------
# rc112: rc109 (rc16+rc29 OFF + rc82 DEF) + rc48 WHCA* deconflict.
#
# Adds teammate-cell projection filter to the 5th 100% champion.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc109 import ReflexRC109OffenseAgent
from zoo_reflex_rc97 import _RC97DeconflictMixin


class ReflexRC112OffenseAgent(_RC97DeconflictMixin, ReflexRC109OffenseAgent):
    pass


class ReflexRC112DefenseAgent(_RC97DeconflictMixin, ReflexRC82Agent):
    pass


def createTeam(firstIndex, secondIndex, isRed,
               first="rc112-offense", second="rc112-defense"):
    return [ReflexRC112OffenseAgent(firstIndex),
            ReflexRC112DefenseAgent(secondIndex)]

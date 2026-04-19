# zoo_reflex_rc119.py
# ------------------
# rc119: rc116 (6th champion) + rc48 WHCA* deconflict.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc116 import ReflexRC116OffenseAgent
from zoo_reflex_rc97 import _RC97DeconflictMixin


class ReflexRC119OffenseAgent(_RC97DeconflictMixin, ReflexRC116OffenseAgent):
    pass


class ReflexRC119DefenseAgent(_RC97DeconflictMixin, ReflexRC82Agent):
    pass


def createTeam(firstIndex, secondIndex, isRed,
               first="rc119-offense", second="rc119-defense"):
    return [ReflexRC119OffenseAgent(firstIndex),
            ReflexRC119DefenseAgent(secondIndex)]

# zoo_reflex_rc110.py
# ------------------
# rc110: rc100 (rc02 OFF + rc82 DEF) + rc48 WHCA* deconflict.
#
# rc100 reached 95% (inverted asym — rc02 on offense effectively
# collapses to A1). Adding rc48 coordination may lift it. Tests
# whether WHCA* overlay gives the same +2.5pp that rc97 showed
# over rc90.

from __future__ import annotations

from zoo_reflex_rc02 import ReflexRC02Agent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc97 import _RC97DeconflictMixin


class ReflexRC110OffenseAgent(_RC97DeconflictMixin, ReflexRC02Agent):
    """rc02 on OFFENSE + WHCA* deconflict."""


class ReflexRC110DefenseAgent(_RC97DeconflictMixin, ReflexRC82Agent):
    """rc82 on DEFENSE + WHCA* deconflict."""


def createTeam(firstIndex, secondIndex, isRed,
               first="rc110-offense", second="rc110-defense"):
    return [ReflexRC110OffenseAgent(firstIndex),
            ReflexRC110DefenseAgent(secondIndex)]

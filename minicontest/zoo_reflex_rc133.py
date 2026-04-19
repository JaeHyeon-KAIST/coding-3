# zoo_reflex_rc133.py
# ------------------
# rc133: rc15 ensemble OFF + rc82 DEF.

from __future__ import annotations

from zoo_reflex_rc15 import ReflexRC15Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc133-offense", second="rc133-defense"):
    return [ReflexRC15Agent(firstIndex), ReflexRC82Agent(secondIndex)]

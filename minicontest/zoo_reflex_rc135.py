# zoo_reflex_rc135.py
# ------------------
# rc135: rc31 kiting OFF + rc82 DEF.

from __future__ import annotations

from zoo_reflex_rc31 import ReflexRC31Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc135-offense", second="rc135-defense"):
    return [ReflexRC31Agent(firstIndex), ReflexRC82Agent(secondIndex)]

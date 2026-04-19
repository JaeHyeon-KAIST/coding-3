# zoo_reflex_rc137.py
# ------------------
# rc137: rc27 stigmergy OFF + rc82 DEF.

from __future__ import annotations

from zoo_reflex_rc27 import ReflexRC27Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc137-offense", second="rc137-defense"):
    return [ReflexRC27Agent(firstIndex), ReflexRC82Agent(secondIndex)]

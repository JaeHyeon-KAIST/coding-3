# zoo_reflex_rc132.py
# ------------------
# rc132: rc45 weighted-ensemble OFF + rc82 DEF.

from __future__ import annotations

from zoo_reflex_rc45 import ReflexRC45Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc132-offense", second="rc132-defense"):
    return [ReflexRC45Agent(firstIndex), ReflexRC82Agent(secondIndex)]

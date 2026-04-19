# zoo_reflex_rc130.py
# ------------------
# rc130: rc08 (dual-invader lane) OFF + rc82 DEF.

from __future__ import annotations

from zoo_reflex_rc08 import ReflexRC08Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc130-offense", second="rc130-defense"):
    return [ReflexRC08Agent(firstIndex), ReflexRC82Agent(secondIndex)]

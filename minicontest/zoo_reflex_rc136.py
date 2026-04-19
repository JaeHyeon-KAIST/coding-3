# zoo_reflex_rc136.py
# ------------------
# rc136: rc11 border juggling OFF + rc82 DEF.

from __future__ import annotations

from zoo_reflex_rc11 import ReflexRC11Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc136-offense", second="rc136-defense"):
    return [ReflexRC11Agent(firstIndex), ReflexRC82Agent(secondIndex)]

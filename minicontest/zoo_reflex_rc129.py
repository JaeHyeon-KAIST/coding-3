# zoo_reflex_rc129.py
# ------------------
# rc129: rc19 (phase-mode) OFF + rc82 DEF.

from __future__ import annotations

from zoo_reflex_rc19 import ReflexRC19Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc129-offense", second="rc129-defense"):
    return [ReflexRC19Agent(firstIndex), ReflexRC82Agent(secondIndex)]

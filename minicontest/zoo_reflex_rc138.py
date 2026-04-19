# zoo_reflex_rc138.py
# ------------------
# rc138: rc33 persona-shift OFF + rc82 DEF.

from __future__ import annotations

from zoo_reflex_rc33 import ReflexRC33Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc138-offense", second="rc138-defense"):
    return [ReflexRC33Agent(firstIndex), ReflexRC82Agent(secondIndex)]

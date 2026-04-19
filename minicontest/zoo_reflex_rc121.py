# zoo_reflex_rc121.py
# ------------------
# rc121: rc109's OFF (rc16+rc29+rc50 via rc116-style) + rc32 DEF.
#
# Replaces rc82 defender (rc44 stacking + rc29) with rc32 Pincer.
# Tests whether the simpler rc32 defender matches rc82's defense
# when paired with the rc116-style compound offense.

from __future__ import annotations

from zoo_reflex_rc32 import ReflexRC32Agent
from zoo_reflex_rc116 import ReflexRC116OffenseAgent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc121-offense", second="rc121-defense"):
    return [ReflexRC116OffenseAgent(firstIndex),
            ReflexRC32Agent(secondIndex)]

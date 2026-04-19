# zoo_reflex_rc134.py
# ------------------
# rc134: rc16 OFF + rc94 (3-champ dense vote) DEF.
#
# Tests whether rc94 dense vote as DEFENSE (instead of rc82) with
# rc16 Voronoi as OFFENSE can reach 100%. rc94 solo = 95%, rc16
# solo = 100%, so combining a weaker defender with a stronger
# offense may still reach the ceiling if rc94's vote includes rc82
# contribution.

from __future__ import annotations

from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc94 import ReflexRC94Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc134-offense", second="rc134-defense"):
    return [ReflexRC16Agent(firstIndex), ReflexRC94Agent(secondIndex)]

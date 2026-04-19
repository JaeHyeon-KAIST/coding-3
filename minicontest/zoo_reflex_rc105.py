# zoo_reflex_rc105.py
# ------------------
# rc105: Asymmetric rc16 OFF + rc82 DEF.
#
# Swapped-roles counterpart to rc91 (rc82 OFF + rc16 DEF). rc91 was
# 92.5%. rc105 tests whether rc82's rc44 stacking works on defense
# while rc16's Voronoi handles offense. Voronoi on offense includes
# a territorial-control push for food spread.

from __future__ import annotations

from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="Asymmetric", second="Asymmetric"):
    return [ReflexRC16Agent(firstIndex), ReflexRC82Agent(secondIndex)]

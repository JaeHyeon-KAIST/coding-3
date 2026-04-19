# zoo_reflex_rc106.py
# ------------------
# rc106: Asymmetric rc02 OFF + rc16 DEF.
#
# Both agents are 100%-WR champions. rc02 Tarjan AP effectively
# collapses to A1 on offense (its trigger requires "invader visible
# on our side"). rc16 Voronoi on defense pushes territorial control
# via our defended food ownership.
#
# Completes the 2×2 champion asym matrix along with:
#   rc90: rc82 OFF + rc32 DEF
#   rc91: rc82 OFF + rc16 DEF
#   rc100: rc02 OFF + rc82 DEF
#   rc103: rc02 OFF + rc32 DEF
#   rc104: rc16 OFF + rc32 DEF
#   rc105: rc16 OFF + rc82 DEF

from __future__ import annotations

from zoo_reflex_rc02 import ReflexRC02Agent
from zoo_reflex_rc16 import ReflexRC16Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="Asymmetric", second="Asymmetric"):
    return [ReflexRC02Agent(firstIndex), ReflexRC16Agent(secondIndex)]

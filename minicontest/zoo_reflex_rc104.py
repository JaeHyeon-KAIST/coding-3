# zoo_reflex_rc104.py
# ------------------
# rc104: Asymmetric rc16 OFF + rc32 DEF.
#
# Combines two 100%/97.5% solo champions in their most natural
# roles: rc16 Voronoi pressure on offense, rc32 Pincer on defense.
# rc16's territorial feature adds a push toward our side's food
# control while attacking. Compared to rc81 (rc16 OFF + rc02 DEF,
# 92.5%), rc104 swaps to rc32 Pincer defender.

from __future__ import annotations

from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc32 import ReflexRC32Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="Asymmetric", second="Asymmetric"):
    return [ReflexRC16Agent(firstIndex), ReflexRC32Agent(secondIndex)]

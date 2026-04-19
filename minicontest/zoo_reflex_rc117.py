# zoo_reflex_rc117.py
# ------------------
# rc117: rc03 (dead-end trap) OFF + rc82 DEF.
#
# rc03 dead-end trap scored 95% solo. It's a defense-specialized
# agent (tags dead-end cells and closes them off against invaders).
# As OFFENSE, the dead-end tag would only affect... wait, actually
# rc03 uses dead-end cells on OUR side to trap invaders. On enemy
# side (as Pacman) the dead-end logic doesn't activate. So rc03 as
# OFFENSE = A1 as OFFENSE on enemy side.
#
# Pairs rc03 OFF with rc82 DEF — tests a conceptually defensive agent
# doing offense. Likely mirrors rc100's result (rc02 OFF + rc82 DEF
# = 95%).

from __future__ import annotations

from zoo_reflex_rc03 import ReflexRC03Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc117-offense", second="rc117-defense"):
    return [ReflexRC03Agent(firstIndex), ReflexRC82Agent(secondIndex)]

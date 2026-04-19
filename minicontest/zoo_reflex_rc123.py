# zoo_reflex_rc123.py
# ------------------
# rc123: rc32 Pincer OFF + rc82 DEF.
#
# rc32 is primarily defensive (pincer maneuver vs single invader).
# Used as OFFENSE agent, its pincer trigger rarely fires on enemy
# side. Likely behaves as pure A1 on offense — similar to rc100
# (rc02 OFF + rc82 DEF = 95%).

from __future__ import annotations

from zoo_reflex_rc32 import ReflexRC32Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc123-offense", second="rc123-defense"):
    return [ReflexRC32Agent(firstIndex), ReflexRC82Agent(secondIndex)]

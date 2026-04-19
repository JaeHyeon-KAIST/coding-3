# zoo_reflex_rc115.py
# ------------------
# rc115: rc44 OFF + rc82 DEF asymmetric.
#
# rc44 is state-conditioned stacking (voting over A1/rc02/rc16/rc32
# by game phase). Used as offense agent paired with rc82 (which
# itself uses rc44 internally) on defense. This tests whether
# plain rc44 offense (without rc82's rc29 reverse overlay) behaves
# differently in the asymmetric role from the rc109 variant.

from __future__ import annotations

from zoo_reflex_rc44 import ReflexRC44Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc115-offense", second="rc115-defense"):
    return [ReflexRC44Agent(firstIndex), ReflexRC82Agent(secondIndex)]

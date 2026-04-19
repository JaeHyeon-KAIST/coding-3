# zoo_reflex_rc103.py
# ------------------
# rc103: Asymmetric rc02 OFF + rc32 DEF.
#
# Both rc02 and rc32 are near-100% solo. As with rc100 (rc02 OFF +
# rc82 DEF), rc02-as-OFFENSE largely behaves like A1 because the
# Tarjan AP override only fires against invaders on our side. rc32
# Pincer handles single invaders on defense.
#
# Compared to rc90 (rc82 OFF + rc32 DEF): rc103 gives up rc82's
# rc29/rc44 offense layers. Should be slightly weaker, quantifies
# the marginal value of rc82-over-A1 on offense.

from __future__ import annotations

from zoo_reflex_rc02 import ReflexRC02Agent
from zoo_reflex_rc32 import ReflexRC32Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="Asymmetric", second="Asymmetric"):
    return [ReflexRC02Agent(firstIndex), ReflexRC32Agent(secondIndex)]

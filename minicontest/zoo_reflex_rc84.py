# zoo_reflex_rc84.py
# ------------------
# rc84: Role-asymmetric team — rc82 combo on OFFENSE, rc02 Tarjan AP
# on DEFENSE.
#
# rc81 did (rc16 OFF + rc02 DEF) at 92.5%+. rc84 swaps rc16 → rc82
# for offense because rc82 adds the threat-conditioned REVERSE
# disruption (rc29) AND state-conditioned stacking (rc44) on top of
# A1, giving a richer offensive policy than rc16's single Voronoi
# overlay.
#
# Both components are 100% WR in solo runs, so the combination
# should at minimum match each — and potentially exceed if their
# failure modes differ (they are qualitatively different overlays).

from __future__ import annotations

from zoo_reflex_rc02 import ReflexRC02Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="Asymmetric", second="Asymmetric"):
    """firstIndex → OFFENSE via rc82 combo, secondIndex → DEFENSE via rc02."""
    return [ReflexRC82Agent(firstIndex), ReflexRC02Agent(secondIndex)]

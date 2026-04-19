# zoo_reflex_rc90.py
# ------------------
# rc90: Role-asymmetric team — rc82 combo on OFFENSE, rc32 Pincer on
# DEFENSE.
#
# pm24 tried rc81 (rc16 OFF + rc02 DEF, 92.5%+), rc84 (rc82 OFF +
# rc02 DEF, 95%+). rc90 swaps the defender: rc32 (97.5% solo)
# replaces rc02 (100% solo) because rc32's pincer maneuver may be
# more effective against a single invader — which is the common
# case in defaultCapture.
#
# If the defender hypothesis holds, rc90 should match rc84 closely;
# if rc32's 2.5pp deficit matters, rc90 may trail slightly. Either
# way, a distinct asymmetric composition for Phase 4 diversity.

from __future__ import annotations

from zoo_reflex_rc32 import ReflexRC32Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="Asymmetric", second="Asymmetric"):
    """firstIndex → OFFENSE via rc82, secondIndex → DEFENSE via rc32."""
    return [ReflexRC82Agent(firstIndex), ReflexRC32Agent(secondIndex)]

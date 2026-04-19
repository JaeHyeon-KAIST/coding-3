# zoo_reflex_rc91.py
# ------------------
# rc91: Role-asymmetric team — rc82 combo on OFFENSE, rc16 Voronoi
# on DEFENSE.
#
# Third asymmetric variant. We've tried:
#   rc81: rc16 OFF + rc02 DEF → 92.5%+
#   rc84: rc82 OFF + rc02 DEF → 95%+
#   rc90: rc82 OFF + rc32 DEF → 97.5%
#
# rc91 is rc82 OFF + rc16 DEF — rc16 has a territorial-control signal
# that may trade off vs rc32's single-invader pincer. Voronoi is
# stronger when multiple invaders present (dual-coverage territorial
# pressure) while pincer is stronger for single invader. Complementary
# to rc90 for Phase 4 diversity.

from __future__ import annotations

from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="Asymmetric", second="Asymmetric"):
    """firstIndex → OFFENSE via rc82, secondIndex → DEFENSE via rc16."""
    return [ReflexRC82Agent(firstIndex), ReflexRC16Agent(secondIndex)]

# zoo_reflex_rc81.py
# ------------------
# rc81: Role-asymmetric team — rc16 Voronoi on OFFENSE, rc02 Tarjan AP
# on DEFENSE.
#
# All prior rc's (including rc45 ensemble) use the SAME agent class
# for both team members. But our two 100%-WR pm23 candidates specialize:
#   - rc02 Tarjan AP is a pure-defense overlay (fires on invader visible).
#   - rc16 Voronoi is a territorial-control overlay (offense + defense
#     balance favored by rc16's f_voronoiScore weight).
#
# Since zoo_core.TEAM.role assigns lower-index → OFFENSE and higher-
# index → DEFENSE, we can build a team where:
#   - firstIndex agent = ReflexRC16Agent (OFFENSE role)
#   - secondIndex agent = ReflexRC02Agent (DEFENSE role)
#
# Each agent class handles its role naturally — rc16 adds Voronoi
# territory pressure while attacking, rc02 locks choke points while
# defending. Combined coverage may exceed either solo's 100%.

from __future__ import annotations

from zoo_reflex_rc02 import ReflexRC02Agent
from zoo_reflex_rc16 import ReflexRC16Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="Asymmetric", second="Asymmetric"):
    """firstIndex → OFFENSE via rc16, secondIndex → DEFENSE via rc02."""
    return [ReflexRC16Agent(firstIndex), ReflexRC02Agent(secondIndex)]

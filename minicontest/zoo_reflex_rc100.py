# zoo_reflex_rc100.py
# ------------------
# rc100: Inverted role-asymmetric — rc02 Tarjan AP on OFFENSE,
# rc82 combo on DEFENSE.
#
# Counterintuitive test. rc90 established rc82 OFF + rc32 DEF =
# 97.5%. rc100 inverts the pairing: maybe rc82's state-conditioned
# stacking (with rc29 disruption) works on defense too, and rc02's
# Tarjan AP is applicable when offense agent "blockades" on enemy
# side near their food?
#
# In practice:
#   - OFFENSE rc02: its Tarjan AP override only fires on "visible
#     invader on our side" — which never happens during offense.
#     So rc02 OFF behaves as pure A1 on offense (since override
#     never triggers).
#   - DEFENSE rc82: its rc29 reverse fires when herded by ghost,
#     but we're a defender (ghost) so enemy Pacman doesn't herd us.
#     rc44 stacking still applies.
#
# So rc100 is effectively A1 OFF + rc44-stacking DEF. Likely worse
# than rc90 (rc82 OFF + rc32 DEF), but quantifies the loss.

from __future__ import annotations

from zoo_reflex_rc02 import ReflexRC02Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="Inverted", second="Inverted"):
    """firstIndex → OFFENSE via rc02, secondIndex → DEFENSE via rc82."""
    return [ReflexRC02Agent(firstIndex), ReflexRC82Agent(secondIndex)]

# zoo_reflex_defensive.py
# -----------------------
# Inherits ReflexTunedAgent but both teammates use DEFENSIVE weights with
# f_numInvaders weight amplified × 10.

from __future__ import annotations

from zoo_reflex_tuned import ReflexTunedAgent
from zoo_features import SEED_WEIGHTS_DEFENSIVE
from game import Directions


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexDefensiveAgent', second='ReflexDefensiveAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# Build the defensive weight variant once at module load.
_WEIGHTS_DEFENSIVE = dict(SEED_WEIGHTS_DEFENSIVE)
_WEIGHTS_DEFENSIVE['f_numInvaders'] = SEED_WEIGHTS_DEFENSIVE['f_numInvaders'] * 10.0


class ReflexDefensiveAgent(ReflexTunedAgent):
    """Both agents defend; amplified invader penalty."""

    def _get_weights(self):
        # Always defensive — ignore TEAM.role.
        return _WEIGHTS_DEFENSIVE

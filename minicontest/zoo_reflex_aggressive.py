# zoo_reflex_aggressive.py
# ------------------------
# Inherits ReflexTunedAgent but always uses OFFENSIVE weights with:
#   - f_numCarrying weight × 5 (inflated — values pellets highly)
#   - f_distToHome weight × 0.2 (deflated — doesn't prioritize returning)
#
# Both teammates are pure attackers (always OFFENSE weights regardless of TEAM.role).

from __future__ import annotations

from zoo_reflex_tuned import ReflexTunedAgent
from zoo_features import SEED_WEIGHTS_OFFENSIVE, _ACTION_PREFERENCE, evaluate
from game import Directions


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexAggressiveAgent', second='ReflexAggressiveAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# Build the aggressive weight variant once at module load.
_WEIGHTS_AGGRESSIVE = dict(SEED_WEIGHTS_OFFENSIVE)
_WEIGHTS_AGGRESSIVE['f_numCarrying'] = SEED_WEIGHTS_OFFENSIVE['f_numCarrying'] * 5.0
_WEIGHTS_AGGRESSIVE['f_distToHome'] = SEED_WEIGHTS_OFFENSIVE['f_distToHome'] * 0.2


class ReflexAggressiveAgent(ReflexTunedAgent):
    """Both agents attack; inflated carrying value, deflated return-home drive."""

    def _get_weights(self):
        # Always aggressive offense — ignore TEAM.role.
        return _WEIGHTS_AGGRESSIVE

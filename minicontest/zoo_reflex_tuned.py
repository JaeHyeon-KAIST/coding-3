# zoo_reflex_tuned.py
# -------------------
# Tuned feature-reflex team agent. Seed for your_baseline1.py.
# Both teammates inherit CoreCaptureAgent; role (OFFENSE/DEFENSE) is assigned
# by TeamGlobalState.role[], defaulting to lower-index=OFFENSE,
# higher-index=DEFENSE.
#
# Decision rule: argmax over legal actions using role-appropriate weights.
# Tiebreak: deterministic preference order [North, East, South, West, Stop].

from __future__ import annotations

from zoo_core import CoreCaptureAgent, TEAM
from zoo_features import (
    extract_features, evaluate,
    SEED_WEIGHTS_OFFENSIVE, SEED_WEIGHTS_DEFENSIVE,
    _ACTION_PREFERENCE,
)
from game import Directions


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexTunedAgent', second='ReflexTunedAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


class ReflexTunedAgent(CoreCaptureAgent):
    """Tuned reflex agent with 20 features and role-based weight selection."""

    def _get_weights(self):
        """Return the weight dict appropriate for this agent's current role."""
        try:
            role = TEAM.role.get(self.index, 'OFFENSE')
        except Exception:
            role = 'OFFENSE'
        if role == 'DEFENSE':
            return SEED_WEIGHTS_DEFENSIVE
        return SEED_WEIGHTS_OFFENSIVE

    def _chooseActionImpl(self, gameState):
        """Argmax over legal actions using role-appropriate weights.

        Tiebreak: deterministic preference [North, East, South, West, Stop].
        """
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        weights = self._get_weights()

        best_score = float('-inf')
        best_action = None

        # Evaluate in preference order so first tie-preferred action wins.
        ordered = sorted(legal, key=lambda a: _ACTION_PREFERENCE.index(a)
                         if a in _ACTION_PREFERENCE else len(_ACTION_PREFERENCE))

        for action in ordered:
            try:
                score = evaluate(self, gameState, action, weights)
            except Exception:
                score = float('-inf')
            if score > best_score:
                best_score = score
                best_action = action

        if best_action is None or best_action not in legal:
            # Fallback: prefer non-STOP
            non_stop = [a for a in legal if a != Directions.STOP]
            return non_stop[0] if non_stop else Directions.STOP

        return best_action

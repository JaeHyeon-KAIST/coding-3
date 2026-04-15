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
               first='ReflexTunedAgent', second='ReflexTunedAgent',
               weights=None):
    """Construct the two teammate agents.

    Extra kwarg (M4b-2, pm8):
      weights — optional path to a JSON weights file (or a dict). When
                provided (passed via capture.py's `--redOpts weights=...`),
                the spec is loaded via zoo_core.load_weights_override and
                attached to each agent as `_weights_override`. The agent's
                `_get_weights()` then returns the override instead of the
                module-level seed weights. Used by evolve.py (M5/M6) to
                inject candidate genomes at runtime. Never raises — a bad
                `weights` path silently falls back to seed weights.
    """
    agents = [eval(first)(firstIndex), eval(second)(secondIndex)]
    if weights:
        try:
            from zoo_core import load_weights_override
            override = load_weights_override(weights)
            # Only attach if non-empty — keeps the agent's fallback clean.
            if override.get('w_off') or override.get('w_def'):
                for a in agents:
                    a._weights_override = override
        except Exception:
            pass  # crash-proof: fall back to seed weights on any failure
    return agents


class ReflexTunedAgent(CoreCaptureAgent):
    """Tuned reflex agent with 20 features and role-based weight selection.

    If `self._weights_override` is attached (see createTeam `weights` kwarg),
    `_get_weights()` returns the override instead of the module-level seed.
    This is the runtime hook used by evolve.py to evaluate CEM candidates.
    """

    def _get_weights(self):
        """Return the weight dict appropriate for this agent's current role.

        Priority: runtime override > role-split seed weights.
        Override schema (from zoo_core.load_weights_override):
          {'w_off': {...}, 'w_def': {...} | None, 'params': {...}}
        If w_def is None (Phase 2a shared-W), DEFENSE role also uses w_off.
        """
        try:
            role = TEAM.role.get(self.index, 'OFFENSE')
        except Exception:
            role = 'OFFENSE'
        override = getattr(self, '_weights_override', None)
        if override:
            if role == 'DEFENSE' and override.get('w_def'):
                return override['w_def']
            if override.get('w_off'):
                return override['w_off']
            # override attached but empty — fall through to seed
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

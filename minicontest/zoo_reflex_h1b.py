# zoo_reflex_h1b.py
# -----------------
# H1b: role-aware variant of the H1 deadlock-hypothesis test.
# See wiki debugging/m3-smoke-deadlock-0-win-pattern-across-all-tuned-agents.
#
# Keeps the 1 OFFENSE + 1 DEFENSE split from ReflexTunedAgent
# (TEAM.role-driven: lower-index agent = OFFENSE, higher-index = DEFENSE).
# Overrides ONLY the OFFENSIVE weight dict:
#   f_onDefense   : +100.0 -> 0.0     (home-side bonus removed)
#   f_numInvaders : -1000  -> -50     (mild invader signal, not dominator)
# DEFENSIVE weights untouched so the home-defender role still holds territory.
#
# Rationale: H1 (both agents OFFENSE) confirmed that SEED_WEIGHTS_OFFENSIVE
# bias was the deadlock driver (3W/2L/5T vs 0W/0L/10T for older variants).
# BUT the "both OFFENSE" configuration eliminated the defender, causing
# 2/10 games to be -18 routs on Blue-starter games where baseline's
# OffensiveReflexAgent raided unopposed. H1b preserves the defender
# while still addressing the over-defensive OFFENSIVE seed.
#
# Prediction: ties similar or reduced; decisive -18 losses eliminated;
# overall win rate >= H1's 30% (ideally 40-60%).
#
# Diagnostic variant, not a submission candidate.

from __future__ import annotations

from zoo_reflex_tuned import ReflexTunedAgent
from zoo_core import TEAM
from zoo_features import SEED_WEIGHTS_OFFENSIVE, SEED_WEIGHTS_DEFENSIVE


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexH1bAgent', second='ReflexH1bAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# Build patched OFFENSIVE weight variant once at module load.
_WEIGHTS_OFFENSIVE_H1B = dict(SEED_WEIGHTS_OFFENSIVE)
_WEIGHTS_OFFENSIVE_H1B['f_onDefense'] = 0.0
_WEIGHTS_OFFENSIVE_H1B['f_numInvaders'] = -50.0


class ReflexH1bAgent(ReflexTunedAgent):
    """Role-aware H1 patch variant.

    OFFENSE role  -> H1-patched offensive weights (no home-side bonus,
                     mild invader signal).
    DEFENSE role  -> SEED_WEIGHTS_DEFENSIVE untouched (strong home defense,
                     invader-chasing, patrol).
    """

    def _get_weights(self):
        try:
            role = TEAM.role.get(self.index, 'OFFENSE')
        except Exception:
            role = 'OFFENSE'
        if role == 'DEFENSE':
            return SEED_WEIGHTS_DEFENSIVE
        return _WEIGHTS_OFFENSIVE_H1B

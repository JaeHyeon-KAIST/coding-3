# zoo_reflex_h1test.py
# --------------------
# H1 hypothesis validation variant (wiki: debugging/m3-smoke-deadlock-...).
#
# Hypothesis H1: SEED_WEIGHTS_OFFENSIVE is too defense-heavy. The terms
#   f_numInvaders = -1000.0    # (|val| = 1000 any time enemy Pacman visible on our side)
#   f_onDefense   = +100.0     # (+100 any time our successor is NOT a Pacman = home side)
# jointly dominate the offensive gain signal (f_successorScore=100 per dot,
# f_distToFood=10/dist), so argmax prefers "stay on our side" over "invade".
#
# This variant overrides the OFFENSIVE weights with:
#   f_onDefense   = 0.0        # remove home-side bonus entirely
#   f_numInvaders = -50.0      # keep a mild invader-aware signal, not a cliff
# All other weights unchanged.
#
# Both teammates use the overridden OFFENSIVE weights regardless of TEAM.role
# (ReflexAggressive pattern) so that BOTH attempt invasion. This is the
# fastest way to confirm whether SEED_WEIGHTS are the deadlock cause.
#
# If win rate > 0% vs baseline over 10 games on defaultCapture, H1 confirmed:
# seed weights need re-tuning before M6 evolution (evolution cannot escape
# structural biases; it can only retune values).
# If still 0W 10T/L, H1 rejected → escalate to H2 (STOP fallback firing),
# H3 (APSP corruption), H5 (role assignment bug).
#
# NOT a submission file. Evaluation-only.

from __future__ import annotations

from zoo_reflex_tuned import ReflexTunedAgent
from zoo_features import SEED_WEIGHTS_OFFENSIVE


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexH1TestAgent', second='ReflexH1TestAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# Build the H1-test weight variant once at module load.
_WEIGHTS_H1_TEST = dict(SEED_WEIGHTS_OFFENSIVE)
_WEIGHTS_H1_TEST['f_onDefense'] = 0.0
_WEIGHTS_H1_TEST['f_numInvaders'] = -50.0


class ReflexH1TestAgent(ReflexTunedAgent):
    """Weak-defense variant of ReflexTunedAgent for H1 hypothesis testing.

    Both teammates use the H1-test OFFENSIVE weights regardless of role,
    so BOTH attempt territory crossings. If the deadlock was just seed-weight
    bias, this agent should score.
    """

    def _get_weights(self):
        return _WEIGHTS_H1_TEST

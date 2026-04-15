# zoo_reflex_h1c.py
# -----------------
# H1c: capsule-exploit variant of the H1 deadlock-hypothesis test.
# See wiki session-log/2026-04-15-pm2-h1b-rejected-strategic-replanning.
#
# Builds on H1 (both-OFFENSE formation, 3W/2L/5T vs baseline on defaultCapture)
# by aggressively prioritising capsule acquisition. The hypothesis is that
# baseline.py's defensive agent uses a feature set that IGNORES its own
# scaredTimer — so once we eat an enemy capsule, baseline's defender will
# continue to "chase" us (with its weights dominated by invaderDist) and
# effectively self-destruct for ~40 ticks, during which our raiders can
# harvest food unopposed.
#
# Weight overrides (all applied to SEED_WEIGHTS_OFFENSIVE; BOTH teammates
# use this dict regardless of role, same formation as H1):
#   f_onDefense     : +100.0 -> 0.0     (remove home-side bonus — H1 inheritance)
#   f_numInvaders   : -1000  -> -50     (mild invader signal — H1 inheritance)
#   f_distToCapsule :    8.0 -> 80.0    (10x, NEW — strong capsule pull)
#
# f_distToCapsule = 1 / max(min_cap_dist, 1), so with weight 80:
#   dist 1  -> +80         (dominates f_distToFood@10 = +10)
#   dist 5  -> +16
#   dist 10 -> +8          (still matches f_distToFood@1, so nearby food
#                           still gets sampled when capsule is far)
#
# Prediction: >= 5W in 10 games vs baseline on defaultCapture. If confirmed,
# the path forward is (a) promote the "both-OFFENSE + capsule-hungry"
# pattern into an M4 contender variant, and (b) proceed with M4 infra
# patches + tournament. If rejected (win rate <= H1's 30%), pivot to H1d
# (DEFENSIVE rebalance: f_patrolDist 30->5, f_invaderDist 80->400) and
# ultimately concede that single-dict tuning caps out, making M6 evolution
# the only path — which requires the `evolve.py:140-142` NotImplementedError
# fix described in wiki debugging/experiments-infrastructure-audit-...
#
# NOT a submission file. Evaluation-only.

from __future__ import annotations

from zoo_reflex_tuned import ReflexTunedAgent
from zoo_features import SEED_WEIGHTS_OFFENSIVE


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexH1cAgent', second='ReflexH1cAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# Build the H1c weight variant once at module load.
# Inherits H1's both-OFFENSE formation patches, plus the 10x capsule pull.
_WEIGHTS_H1C = dict(SEED_WEIGHTS_OFFENSIVE)
_WEIGHTS_H1C['f_onDefense'] = 0.0       # H1 inheritance
_WEIGHTS_H1C['f_numInvaders'] = -50.0   # H1 inheritance
_WEIGHTS_H1C['f_distToCapsule'] = 80.0  # NEW — capsule-exploit pull


class ReflexH1cAgent(ReflexTunedAgent):
    """Capsule-exploit variant of ReflexTunedAgent for H1c hypothesis testing.

    Both teammates use the H1c OFFENSIVE weights regardless of role
    (same formation as H1), so BOTH attempt invasion and BOTH are strongly
    attracted to the enemy capsule. Once the capsule is eaten, baseline's
    defender (oblivious to its own scaredTimer) should self-destruct.
    """

    def _get_weights(self):
        return _WEIGHTS_H1C

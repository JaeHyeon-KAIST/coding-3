# zoo_reflex_rc42.py
# ------------------
# rc42: Double Q-learning inference-style (minimum-of-two evaluators).
#
# In Double Q, each update uses one Q-estimator to select and the OTHER
# to evaluate → removes overestimation bias. At inference time we can
# approximate by taking the MINIMUM of two evaluators (conservative
# — pessimistic estimate of action value).
#
# Here: W_OFF and W_DEF are both 17-feature evolved weight vectors. For
# each candidate action, compute scores under both and use min. This
# hedges against one set "hallucinating" value that the other disagrees
# with. Cheap (~2× evaluate cost per action).
#
# Tier 2 (K3 Double Q-learning in rc-pool.md).

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent, _A1_OVERRIDE
from zoo_features import (
    evaluate, SEED_WEIGHTS_OFFENSIVE, SEED_WEIGHTS_DEFENSIVE,
    _ACTION_PREFERENCE,
)
from zoo_core import TEAM
from game import Directions


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC42Agent", second="ReflexRC42Agent"):
    return [ReflexRC42Agent(firstIndex), ReflexRC42Agent(secondIndex)]


class ReflexRC42Agent(ReflexA1Agent):
    """Double-Q minimum of W_OFF and W_DEF evaluators."""

    def _chooseActionImpl(self, gameState):
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            w_off = (_A1_OVERRIDE.get("w_off") or SEED_WEIGHTS_OFFENSIVE)
            w_def = (_A1_OVERRIDE.get("w_def") or SEED_WEIGHTS_DEFENSIVE)

            try:
                ordered = sorted(
                    legal,
                    key=lambda a: (_ACTION_PREFERENCE.index(a)
                                   if a in _ACTION_PREFERENCE
                                   else len(_ACTION_PREFERENCE)),
                )
            except Exception:
                ordered = list(legal)

            best = float("-inf")
            best_a = None
            for a in ordered:
                try:
                    s1 = evaluate(self, gameState, a, w_off)
                    s2 = evaluate(self, gameState, a, w_def)
                except Exception:
                    continue
                # Use MIN as pessimistic estimate (Double-Q style).
                score = min(s1, s2)
                if score > best:
                    best = score
                    best_a = a

            if best_a is None or best_a not in legal:
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            return best_a
        except Exception:
            try:
                return super()._chooseActionImpl(gameState)
            except Exception:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP

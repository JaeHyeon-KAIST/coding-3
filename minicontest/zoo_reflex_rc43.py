# zoo_reflex_rc43.py
# ------------------
# rc43: TD(λ) eligibility-trace feature smoother (inference-only).
#
# TD(λ) maintains eligibility traces e_k(t) = γλ·e_k(t-1) + f_k(s_t).
# During training, updates propagate via Σ w_k · e_k. At inference time
# (no training, just A1's evolved weights), we use the trace as a
# MOMENTUM signal: actions whose features align with recently-taken
# actions' features get a small bonus. This rewards consistency.
#
# Concretely:
#   1. Maintain per-feature trace dict updated every turn.
#   2. At chooseAction, for each candidate action compute:
#        score = A1_score(a) + α · Σ w_k · e_k · f_k(s,a)
#      where α is a small mixing coefficient.
#   3. Pick argmax.
#
# The bonus is positive for actions that continue "in the same strategic
# direction" as the recent trajectory, negative for reversals on
# positive-weight features. Counteracts reflex-oscillation.
#
# Tier 2 (K2 TD(λ) in rc-pool.md).

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import (
    evaluate, extract_features, _ACTION_PREFERENCE,
)
from zoo_core import TEAM
from game import Directions


RC43_LAMBDA = 0.85
RC43_GAMMA = 0.95
RC43_ALPHA_MIX = 0.10  # small blend weight; avoid overwhelming A1


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC43Agent", second="ReflexRC43Agent"):
    return [ReflexRC43Agent(firstIndex), ReflexRC43Agent(secondIndex)]


class ReflexRC43Agent(ReflexA1Agent):
    """A1 + TD(λ)-style feature-trace momentum bonus."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc43_trace = {}  # feature name -> accumulated trace value

    def _decay_trace(self):
        decay = RC43_GAMMA * RC43_LAMBDA
        for k in list(self._rc43_trace.keys()):
            v = self._rc43_trace[k] * decay
            if abs(v) < 1e-6:
                del self._rc43_trace[k]
            else:
                self._rc43_trace[k] = v

    def _update_trace(self, feats):
        # Accumulate features into trace.
        for k, v in feats.items():
            self._rc43_trace[k] = self._rc43_trace.get(k, 0.0) + float(v)

    def _momentum_score(self, feats, weights):
        """Σ w_k · e_k · f_k — scaled version of feature*trace."""
        bonus = 0.0
        for k, v in feats.items():
            w = weights.get(k, 0.0)
            tr = self._rc43_trace.get(k, 0.0)
            bonus += w * tr * float(v)
        return bonus

    def _chooseActionImpl(self, gameState):
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            weights = self._get_weights()
            self._decay_trace()

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
            best_feats = None
            for a in ordered:
                try:
                    base = evaluate(self, gameState, a, weights)
                    feats = extract_features(self, gameState, a)
                    bonus = self._momentum_score(feats, weights)
                except Exception:
                    continue
                score = base + RC43_ALPHA_MIX * bonus
                if score > best:
                    best = score
                    best_a = a
                    best_feats = feats

            if best_a is None or best_a not in legal:
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP

            # Update trace with the chosen action's features.
            if best_feats is not None:
                self._update_trace(best_feats)
            return best_a
        except Exception:
            try:
                return super()._chooseActionImpl(gameState)
            except Exception:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP

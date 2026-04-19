# zoo_reflex_rc34.py
# ------------------
# rc34: Pavlovian feinting / pattern-pollution overlay on A1 champion.
#
# Goal: inject controlled deterministic deviation from argmax so that
# opponents that model our policy (minimax, MCTS priors, anyone caching
# "what would Pacman do") cannot rely on greedy-best prediction.
#
# Scheme: every RC34_PERIOD turns, pick the SECOND-best action from
# A1's top-K instead of the argmax — provided it is still within A1's
# tolerance band (so we never sacrifice safety). Otherwise fall through
# to A1. Between feints, act as pure A1.
#
# Difference from rc29 (which reverses direction under a ghost threat):
#   - rc29 is *reactive* — triggered by adversarial proximity.
#   - rc34 is *proactive* — periodic regardless of threat. This
#     deliberately trains-out any opponent policy that built a prior
#     on our deterministic argmax.
#
# Safety: feint only when second-best exists AND is within A1 tolerance.
# The agent becomes stochastic only in a well-bounded sub-optimal band.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions


RC34_PERIOD = 7
RC34_TOP_K = 3
RC34_A1_TOL_FRAC = 0.05


class ReflexRC34Agent(ReflexA1Agent):
    """A1 champion + periodic second-best feint for pattern-pollution."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc34_turn = 0

    def _chooseActionImpl(self, gameState):
        self._rc34_turn += 1

        # Not a feint turn: pure A1.
        if self._rc34_turn % RC34_PERIOD != 0:
            return super()._chooseActionImpl(gameState)

        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        try:
            weights = self._get_weights()
            scored = []
            for action in legal:
                try:
                    s = evaluate(self, gameState, action, weights)
                except Exception:
                    s = float("-inf")
                scored.append((s, action))
            scored.sort(key=lambda sa: sa[0], reverse=True)
            if not scored or scored[0][0] == float("-inf"):
                return super()._chooseActionImpl(gameState)

            top_score = scored[0][0]
            tol = max(abs(top_score) * RC34_A1_TOL_FRAC, 1.0)
            K = min(RC34_TOP_K, len(scored))
            candidates = [a for s, a in scored[:K] if s >= top_score - tol]
            if len(candidates) < 2:
                return scored[0][1]
            return candidates[1]
        except Exception:
            return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC34Agent", second="ReflexRC34Agent"):
    return [ReflexRC34Agent(firstIndex), ReflexRC34Agent(secondIndex)]

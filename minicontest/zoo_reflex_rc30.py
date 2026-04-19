# zoo_reflex_rc30.py
# ------------------
# rc30: Particle-filter blinding overlay on A1 champion.
#
# Some opponents (including our own zoo_belief.py) use a particle
# filter to track us when we're outside their 5-cell sight radius. The
# filter converges on our position when we act deterministically —
# every turn they can eliminate particles incompatible with our
# predicted move. If we act randomly when out of sight, their particle
# distribution stays diffuse, giving us a position-privacy advantage.
#
# rc30 injects randomized top-K selection only when:
#   (a) we are currently NOT visible to any opponent (distance > 5 to
#       all enemies AND their known positions vs our position),
#   (b) every RC30_PERIOD turns — periodic blinding, not every turn
#       (we still want A1-quality paths most of the time).
#
# Random selection is weighted by A1 score so we still lean toward the
# best action; lower-scored options in the top-K get a small chance.
#
# Difference from rc29 (reactive reverse) and rc34 (periodic feint):
#   - rc29: fires when ghost is close.
#   - rc34: fires every N turns regardless of visibility.
#   - rc30: fires periodically AND only when out of sight — exploits
#     the asymmetric information the framework gives us.

from __future__ import annotations

import random

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions


RC30_TOP_K = 3
RC30_A1_TOL_FRAC = 0.05
RC30_PERIOD = 5        # blind every N turns
RC30_VISIBILITY = 5    # sight radius from Capture-the-Flag rules


class ReflexRC30Agent(ReflexA1Agent):
    """A1 champion + randomized top-K when out of opponent sight."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc30_turn = 0
        # Seed RNG deterministically per game to aid reproducibility.
        try:
            self._rc30_rng = random.Random(
                hash(("rc30", int(self.index))) & 0xFFFFFFFF
            )
        except Exception:
            self._rc30_rng = random.Random()

    def _invisible_to_opponents(self, gameState):
        """True iff no opponent has us within their 5-cell sight."""
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return False
            for opp_idx in self.getOpponents(gameState):
                try:
                    opp_pos = gameState.getAgentPosition(opp_idx)
                    if opp_pos is None:
                        # Opp not visible to US → likely we are also not to them
                        continue
                    if self.getMazeDistance(my_pos, opp_pos) <= RC30_VISIBILITY:
                        return False
                except Exception:
                    continue
            return True
        except Exception:
            return False

    def _chooseActionImpl(self, gameState):
        self._rc30_turn += 1
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        # Only blind on period turns AND when invisible.
        if self._rc30_turn % RC30_PERIOD != 0:
            return super()._chooseActionImpl(gameState)
        try:
            if not self._invisible_to_opponents(gameState):
                return super()._chooseActionImpl(gameState)
        except Exception:
            return super()._chooseActionImpl(gameState)

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
            tol = max(abs(top_score) * RC30_A1_TOL_FRAC, 1.0)
            K = min(RC30_TOP_K, len(scored))
            candidates = [(s, a) for s, a in scored[:K]
                          if s >= top_score - tol]
            if len(candidates) < 2:
                return scored[0][1]

            # Softmax-like weighting favoring top score but sometimes
            # picking 2nd or 3rd.
            #
            # Simple scheme: pick from candidates uniformly. Randomized
            # enough to scatter particle-filter belief while staying
            # in-bounds.
            idx = self._rc30_rng.randrange(len(candidates))
            return candidates[idx][1]
        except Exception:
            return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC30Agent", second="ReflexRC30Agent"):
    return [ReflexRC30Agent(firstIndex), ReflexRC30Agent(secondIndex)]

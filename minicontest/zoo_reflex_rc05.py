# zoo_reflex_rc05.py
# ------------------
# rc05: Prospect-theory risk adjustment overlay on A1 champion.
#
# Kahneman/Tversky prospect theory: loss aversion is non-linear and grows
# steeply as you have more to lose. Applied to Pacman: the more food a
# carrier holds, the more punitive "dying" becomes (you lose everything
# on respawn), so risk aversion should increase super-linearly with
# current numCarrying, not linearly as A1's evolved weights do.
#
# A1 already has `f_returnUrgency = numCarrying² × (1/home_dist) × time`,
# which is quadratic. rc05 goes one step further: the entire action
# weighting is rescaled by `exp(alpha · carry)`, amplifying ghost fear,
# dead-end aversion, and return-home pressure, while damping food
# attraction. This is Gemini's prospect-theory framing (§8).
#
# Implementation note: `_get_weights` has no direct access to gameState,
# so `_chooseActionImpl` caches the current `numCarrying` before calling
# super, and `_get_weights` reads from the cache. Both offense and
# defense roles use the same adjustment (defenders rarely carry, so the
# adjustment is no-op for them most of the time).

from __future__ import annotations

import math

from zoo_reflex_A1 import ReflexA1Agent


# Growth rate — tuned so carry=5 ≈ 2.7×, carry=10 ≈ 7.4×, carry=15 ≈ 20×.
RC05_ALPHA = 0.20
# Food-attraction damping uses half the carry exponent (reduce greed).
RC05_FOOD_DAMP_FRAC = 0.5
# Clamp the risk multiplier to keep weight magnitudes numerically sane.
RC05_MAX_RISK_MULT = 12.0


class ReflexRC05Agent(ReflexA1Agent):
    """A1 champion + prospect-theory risk scaling by numCarrying."""

    def _chooseActionImpl(self, gameState):
        # Cache current carrying for _get_weights (called inside super()).
        try:
            st = gameState.getAgentState(self.index)
            self._rc05_carry = int(getattr(st, "numCarrying", 0) or 0)
        except Exception:
            self._rc05_carry = 0
        return super()._chooseActionImpl(gameState)

    def _get_weights(self):
        base = super()._get_weights()
        try:
            carry = int(getattr(self, "_rc05_carry", 0) or 0)
        except Exception:
            carry = 0
        if carry <= 0:
            return base

        try:
            risk = min(math.exp(RC05_ALPHA * carry), RC05_MAX_RISK_MULT)
            food_damp = min(
                math.exp(RC05_ALPHA * carry * RC05_FOOD_DAMP_FRAC),
                RC05_MAX_RISK_MULT,
            )
        except Exception:
            return base

        adj = dict(base)

        # Amplify ghost fear. f_ghostDist1/2 are stored as negative values
        # in A1's weights — multiplying by risk (positive) preserves sign
        # and increases magnitude, which is what we want (more avoidance).
        for k in ("f_ghostDist1", "f_ghostDist2", "f_inDeadEnd"):
            if k in adj:
                adj[k] = adj[k] * risk

        # Amplify return-home pressure.
        for k in ("f_distToHome", "f_returnUrgency"):
            if k in adj:
                adj[k] = adj[k] * risk

        # Damp food / successor-score greed so we don't keep pushing into
        # danger once we already hold food.
        for k in ("f_distToFood", "f_successorScore", "f_distToCapsule"):
            if k in adj:
                adj[k] = adj[k] / max(food_damp, 1.0)

        return adj


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC05Agent", second="ReflexRC05Agent"):
    return [ReflexRC05Agent(firstIndex), ReflexRC05Agent(secondIndex)]

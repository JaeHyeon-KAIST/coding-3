# zoo_reflex_rc95.py
# ------------------
# rc95: rc82 (rc29 disruption + rc44 stacking) + rc88 2-ply lookahead.
#
# rc82 reached 100% solo. rc88 (2-ply self-play lookahead) reached
# only 80% solo — below A1 82.5%, suggesting the lookahead on its
# own is marginal. But layered atop rc82's already-strong policy,
# the lookahead might distinguish between same-scored top-K actions
# that differ in 2-turn horizon.
#
# Strategy:
#   1. Run rc82's normal selection → produces chosen action.
#   2. If rc82 chose the A1-argmax (no disruption/stacking kicked
#      in), keep it.
#   3. If rc82 chose non-argmax (disruption or stacking overrode),
#      use 2-ply lookahead to verify the override has better
#      2-horizon value than A1 argmax. If not, revert to argmax.
#
# This "lookahead veto" prevents rc82's overrides from making
# short-sighted choices that lose in 2 turns.

from __future__ import annotations

import time

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions


RC95_GAMMA = 0.6
RC95_TIME_BUDGET_WARN = 0.80


def _two_ply_value(agent, gameState, action, weights, gamma):
    try:
        s1 = evaluate(agent, gameState, action, weights)
    except Exception:
        return float("-inf")
    if s1 == float("-inf"):
        return s1
    try:
        succ = gameState.generateSuccessor(agent.index, action)
        legal2 = succ.getLegalActions(agent.index)
        if not legal2:
            return s1
        best_s2 = float("-inf")
        for a2 in legal2:
            try:
                s2 = evaluate(agent, succ, a2, weights)
            except Exception:
                s2 = float("-inf")
            if s2 > best_s2:
                best_s2 = s2
        return s1 + gamma * (best_s2 if best_s2 != float("-inf") else 0)
    except Exception:
        return s1


class ReflexRC95Agent(ReflexRC82Agent):
    """rc82 combo + 2-ply lookahead veto of non-argmax overrides."""

    def _chooseActionImpl(self, gameState):
        t0 = time.time()
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        # Run rc82 normally.
        try:
            rc82_choice = super()._chooseActionImpl(gameState)
        except Exception:
            return super()._chooseActionImpl(gameState)

        # Compute A1 1-ply argmax separately for comparison.
        try:
            weights = self._get_weights()
            scored_1ply = {}
            for action in legal:
                try:
                    s = evaluate(self, gameState, action, weights)
                except Exception:
                    s = float("-inf")
                scored_1ply[action] = s
            a1_argmax = max(scored_1ply.items(), key=lambda kv: kv[1])[0]
            if rc82_choice == a1_argmax:
                return rc82_choice

            # Lookahead veto: require rc82 override to exceed A1 argmax
            # at 2-ply horizon.
            v_rc82 = _two_ply_value(self, gameState, rc82_choice, weights, RC95_GAMMA)
            v_a1 = _two_ply_value(self, gameState, a1_argmax, weights, RC95_GAMMA)
            if v_rc82 >= v_a1 - 1e-6:
                return rc82_choice
            # Revert to A1 argmax if override would be worse 2-ply.
            return a1_argmax
        except Exception:
            return rc82_choice
        finally:
            dt = time.time() - t0
            if dt > RC95_TIME_BUDGET_WARN:
                try:
                    print(f"[rc95] warn: turn took {dt:.3f}s")
                except Exception:
                    pass


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC95Agent", second="ReflexRC95Agent"):
    return [ReflexRC95Agent(firstIndex), ReflexRC95Agent(secondIndex)]

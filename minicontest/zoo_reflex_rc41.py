# zoo_reflex_rc41.py
# ------------------
# rc41: SARSA n-step lookahead (self-only on-policy return).
#
# n-step SARSA: Q(s,a) ≈ r_1 + γ·r_2 + γ²·r_3 + ... + γⁿ·Q(s_n, a_n)
# At inference time with A1 reflex as the on-policy π:
#   1. Apply candidate action a from current state.
#   2. For k=1..n-1, apply A1 reflex argmax for SELF only
#      (opponent held in current position → no adversarial sim).
#   3. Return = γⁿ · evaluate(s_n, A1_argmax, weights)
#   4. Pick action with highest return.
#
# Distinct from rc47 (αβ minimax, opponent modeled), rc35 (full-game
# rollout, all agents), rc36 (score-delta reward). rc41's self-only
# on-policy trajectory should avoid rc35's "opponent uses my evaluator"
# bug.
#
# Tier 2 (K1 SARSA family).

from __future__ import annotations

import time

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate, _ACTION_PREFERENCE
from zoo_core import TEAM
from game import Directions


RC41_N_STEPS = 4
RC41_GAMMA = 0.9
RC41_TIME_BUDGET = 0.15


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC41Agent", second="ReflexRC41Agent"):
    return [ReflexRC41Agent(firstIndex), ReflexRC41Agent(secondIndex)]


class ReflexRC41Agent(ReflexA1Agent):
    """A1 + n-step on-policy SARSA return."""

    def _reflex_pick_self(self, state, weights):
        try:
            legal = state.getLegalActions(self.index)
        except Exception:
            return None
        if not legal:
            return None
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
        best_a = ordered[0]
        for a in ordered:
            try:
                v = evaluate(self, state, a, weights)
            except Exception:
                continue
            if v > best:
                best = v
                best_a = a
        return best_a

    def _n_step_return(self, state, weights, deadline):
        """Apply self-only reflex rollout for n-1 more steps, return
        γⁿ × best-next-action utility at terminal."""
        s = state
        gamma_pow = 1.0
        for step in range(RC41_N_STEPS - 1):
            if time.time() >= deadline:
                break
            a = self._reflex_pick_self(s, weights)
            if a is None:
                break
            try:
                s = s.generateSuccessor(self.index, a)
            except Exception:
                break
            gamma_pow *= RC41_GAMMA
        # Best self-action at terminal state.
        try:
            legal = s.getLegalActions(self.index)
        except Exception:
            return 0.0
        if not legal:
            return 0.0
        best = float("-inf")
        for a in legal:
            try:
                v = evaluate(self, s, a, weights)
            except Exception:
                continue
            if v > best:
                best = v
        if best == float("-inf"):
            return 0.0
        return gamma_pow * best

    def _chooseActionImpl(self, gameState):
        try:
            deadline = time.time() + RC41_TIME_BUDGET
            weights = self._get_weights()
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            try:
                ordered = sorted(
                    legal,
                    key=lambda a: (_ACTION_PREFERENCE.index(a)
                                   if a in _ACTION_PREFERENCE
                                   else len(_ACTION_PREFERENCE)),
                )
            except Exception:
                ordered = list(legal)

            best_score = float("-inf")
            best_a = None
            for a in ordered:
                if time.time() >= deadline:
                    break
                try:
                    base = evaluate(self, gameState, a, weights)
                    succ = gameState.generateSuccessor(self.index, a)
                except Exception:
                    continue
                future = self._n_step_return(succ, weights, deadline)
                score = base + RC41_GAMMA * future
                if score > best_score:
                    best_score = score
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

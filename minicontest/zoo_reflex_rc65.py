# zoo_reflex_rc65.py
# ------------------
# rc65: Recursive Theory of Mind L2 — rc82 composite + 2-ply adversarial
# robustness check.
#
# Standard ToM: agent models opponent as a reflex agent (L0). ToM L1:
# agent assumes opponent models me (modeling them). ToM L2: I pick an
# action that's robust even if opponent best-responds using my own
# evaluator (they know what I value and try to deny it).
#
# Implementation (reflex-level, 2-ply minimax over rc82's top-K):
#   1. rc82 produces its composite action (rc44 state-stacking + rc29
#      REVERSE disruption). Call it `rc82_action`.
#   2. Build top-K candidates at the A1 level within tolerance band.
#   3. For each candidate `a_me`, simulate:
#        - I take `a_me` -> succ_me
#        - Closer enemy takes their argmax with MY evaluator negated
#          (adversarial with perfect info) -> succ_adv
#        - Score `a_me` = max over my legal actions at succ_adv of
#          evaluate(self, succ_adv, a, weights)  (i.e. my best next
#          move after adversarial response)
#   4. If rc82's action SURVIVES the adversarial response better than
#      any alternative, keep it; else swap to the robust alternative.
#
# Tier 3 (category: Creative / Recursive opponent modeling).

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_features import evaluate, _ACTION_PREFERENCE
from game import Directions


RC65_TOP_K = 3
RC65_A1_TOL_FRAC = 0.05


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC65Agent", second="ReflexRC65Agent"):
    return [ReflexRC65Agent(firstIndex), ReflexRC65Agent(secondIndex)]


class ReflexRC65Agent(ReflexRC82Agent):
    """rc82 + 2-ply adversarial robustness check."""

    def _closer_enemy(self, gameState):
        try:
            opponents = self.getOpponents(gameState)
            if not opponents:
                return None
            my_pos = gameState.getAgentPosition(self.index)
            best, best_d = None, 99999
            for idx in opponents:
                p = gameState.getAgentPosition(idx)
                if p is None or my_pos is None:
                    continue
                d = self.getMazeDistance(my_pos, p)
                if d < best_d:
                    best_d, best = d, idx
            return best
        except Exception:
            return None

    def _static_eval(self, gameState, weights):
        """Best self-action utility at the given state."""
        try:
            legal = gameState.getLegalActions(self.index)
        except Exception:
            return 0.0
        if not legal:
            return 0.0
        best = float("-inf")
        for a in legal:
            try:
                v = evaluate(self, gameState, a, weights)
            except Exception:
                continue
            if v > best:
                best = v
        return best if best != float("-inf") else 0.0

    def _adversarial_response_value(self, succ_me, enemy_idx, weights):
        """Assume enemy picks action that MINIMIZES my best next-turn
        utility. Return the minimax value after enemy's response."""
        try:
            legal = succ_me.getLegalActions(enemy_idx)
        except Exception:
            return self._static_eval(succ_me, weights)
        if not legal:
            return self._static_eval(succ_me, weights)
        worst = float("inf")
        for b in legal:
            try:
                succ_adv = succ_me.generateSuccessor(enemy_idx, b)
            except Exception:
                continue
            v = self._static_eval(succ_adv, weights)
            if v < worst:
                worst = v
        return worst if worst != float("inf") else self._static_eval(succ_me, weights)

    def _chooseActionImpl(self, gameState):
        try:
            # Start from rc82's composite choice (inherits rc44+rc29).
            rc82_action = super()._chooseActionImpl(gameState)

            legal = gameState.getLegalActions(self.index)
            if not legal or len(legal) <= 1:
                return rc82_action

            weights = self._get_weights()
            enemy_idx = self._closer_enemy(gameState)
            if enemy_idx is None:
                return rc82_action

            # Build A1 top-K candidates.
            scored = []
            for action in legal:
                try:
                    s = evaluate(self, gameState, action, weights)
                except Exception:
                    s = float("-inf")
                scored.append((s, action))
            scored.sort(key=lambda sa: sa[0], reverse=True)
            if not scored or scored[0][0] == float("-inf"):
                return rc82_action

            top = scored[0][0]
            tol = max(abs(top) * RC65_A1_TOL_FRAC, 1.0)
            K = min(RC65_TOP_K, len(scored))
            candidates = [a for s, a in scored[:K] if s >= top - tol]

            # Always include rc82's action (may be outside top-K).
            if rc82_action in legal and rc82_action not in candidates:
                candidates.append(rc82_action)

            # Adversarial robustness scoring for each candidate.
            best_a = rc82_action
            best_score = float("-inf")
            for a in candidates:
                try:
                    succ_me = gameState.generateSuccessor(self.index, a)
                except Exception:
                    continue
                robust_val = self._adversarial_response_value(
                    succ_me, enemy_idx, weights)
                # Bonus: if this matches rc82's choice, small tie-break.
                bonus = 0.5 if a == rc82_action else 0.0
                score = robust_val + bonus
                if score > best_score:
                    best_score = score
                    best_a = a

            if best_a in legal:
                self._record(best_a)
                return best_a
            return rc82_action
        except Exception:
            try:
                return super()._chooseActionImpl(gameState)
            except Exception:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP

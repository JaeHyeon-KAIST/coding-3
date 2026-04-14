# zoo_minimax_ab_d2.py
# --------------------
# 2-agent minimax with alpha-beta pruning, depth 2.
# Opponent modelling: only the closer-of-two enemies is modelled adversarially;
# the farther enemy is frozen at its current (possibly invisible) position.
# When no enemy positions are observable, collapses to self-only max over
# the leaf evaluator.
#
# Ply structure (depth 2, 2-agent tree):
#   max (self) -> min (closer enemy) -> leaf evaluate
#
# Leaf evaluator: zoo_features.evaluate with OFFENSIVE weights when role=OFFENSE,
# DEFENSIVE weights when role=DEFENSE.
#
# Time discipline: depth bound only (MAX_DEPTH=2). No signal / time polling.

from __future__ import annotations

import random

from zoo_core import CoreCaptureAgent, TEAM, Directions, MAX_DEPTH
from zoo_features import (
    evaluate,
    SEED_WEIGHTS_OFFENSIVE,
    SEED_WEIGHTS_DEFENSIVE,
)

# Override: this file always uses depth 2.
_D2 = 2

_NEG_INF = float('-inf')
_POS_INF = float('inf')


def createTeam(firstIndex, secondIndex, isRed,
               first='MinimaxD2Agent', second='MinimaxD2Agent'):
    return [MinimaxD2Agent(firstIndex), MinimaxD2Agent(secondIndex)]


class MinimaxD2Agent(CoreCaptureAgent):
    """Minimax with alpha-beta pruning at depth 2, 1-enemy reduction."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _weights(self):
        try:
            role = TEAM.role.get(self.index, 'OFFENSE')
        except Exception:
            role = 'OFFENSE'
        return SEED_WEIGHTS_DEFENSIVE if role == 'DEFENSE' else SEED_WEIGHTS_OFFENSIVE

    def _closer_enemy(self, gameState):
        """Return (closer_idx, closer_pos, farther_idx, farther_pos).

        Positions that are None mean the enemy is not currently visible.
        If both positions are None, returns (None, None, None, None).
        """
        try:
            opponents = self.getOpponents(gameState)
            if not opponents:
                return None, None, None, None

            my_pos = gameState.getAgentPosition(self.index)

            pairs = []
            for idx in opponents:
                pos = gameState.getAgentPosition(idx)
                pairs.append((idx, pos))

            # Sort by maze distance; None positions pushed to end.
            def dist_key(pair):
                _, pos = pair
                if pos is None or my_pos is None:
                    return 9999
                return self.getMazeDistance(my_pos, pos)

            pairs.sort(key=dist_key)

            if len(pairs) == 1:
                return pairs[0][0], pairs[0][1], None, None
            return pairs[0][0], pairs[0][1], pairs[1][0], pairs[1][1]
        except Exception:
            return None, None, None, None

    def _leaf_eval(self, gameState, action, weights):
        """Evaluate (gameState, action) from self's perspective."""
        try:
            return evaluate(self, gameState, action, weights)
        except Exception:
            return _NEG_INF

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _alphabeta(self, gameState, depth, alpha, beta,
                   is_max_node, agent_idx, weights,
                   enemy_idx, last_action):
        """Alpha-beta search.

        is_max_node=True  -> self (maximiser)
        is_max_node=False -> enemy agent_idx (minimiser)

        last_action is the action taken by self to reach the current state
        (needed for the leaf evaluator which takes (state, action)).
        depth counts down; leaf reached at depth == 0.
        """
        if depth == 0:
            # Evaluate from the maximiser's perspective.
            return self._leaf_eval(gameState, last_action, weights)

        if is_max_node:
            # --- MAX node (self) ---
            try:
                legal = gameState.getLegalActions(self.index)
            except Exception:
                return self._leaf_eval(gameState, last_action, weights)

            if not legal:
                return self._leaf_eval(gameState, last_action, weights)

            best = _NEG_INF
            for action in legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    continue

                if enemy_idx is not None:
                    # Hand off to minimiser.
                    val = self._alphabeta(succ, depth - 1, alpha, beta,
                                         False, enemy_idx, weights,
                                         enemy_idx, action)
                else:
                    # No visible enemy — evaluate leaf directly.
                    val = self._leaf_eval(succ, action, weights)

                if val > best:
                    best = val
                alpha = max(alpha, best)
                if alpha >= beta:
                    break  # beta cut-off
            return best

        else:
            # --- MIN node (enemy) ---
            try:
                legal = gameState.getLegalActions(agent_idx)
            except Exception:
                # Enemy action space unknown — treat as leaf.
                return self._leaf_eval(gameState, last_action, weights)

            if not legal:
                return self._leaf_eval(gameState, last_action, weights)

            worst = _POS_INF
            for action in legal:
                try:
                    succ = gameState.generateSuccessor(agent_idx, action)
                except Exception:
                    continue

                # After enemy moves, it's back to self (depth already
                # decremented coming into this node, but we call leaf at
                # depth-1-which-is-0 from parent). For depth 2 the
                # leaf follows immediately after the MIN node.
                val = self._leaf_eval(succ, last_action, weights)

                if val < worst:
                    worst = val
                beta = min(beta, worst)
                if alpha >= beta:
                    break  # alpha cut-off
            return worst

    # ------------------------------------------------------------------
    # _chooseActionImpl
    # ------------------------------------------------------------------

    def _chooseActionImpl(self, gameState):
        try:
            weights = self._weights()
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return self._safeFallback(gameState, legal)

            enemy_idx, enemy_pos, _, _ = self._closer_enemy(gameState)

            best_action = None
            best_val = _NEG_INF
            alpha = _NEG_INF
            beta = _POS_INF

            for action in legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    continue

                if enemy_idx is not None:
                    # depth starts at _D2; we already expanded the root (self),
                    # so pass depth=_D2-1 to the MIN node.
                    val = self._alphabeta(succ, _D2 - 1, alpha, beta,
                                         False, enemy_idx, weights,
                                         enemy_idx, action)
                else:
                    # All enemies invisible — collapse to self-only max.
                    val = self._leaf_eval(succ, action, weights)

                if val > best_val:
                    best_val = val
                    best_action = action
                alpha = max(alpha, best_val)

            if best_action is None or best_action not in legal:
                return self._safeFallback(gameState, legal)
            return best_action

        except Exception:
            return self._safeFallback(gameState, gameState.getLegalActions(self.index))

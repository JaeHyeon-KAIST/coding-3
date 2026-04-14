# zoo_expectimax.py
# -----------------
# Expectimax: self node = max; opponent nodes = expectation over uniform
# distribution of legal moves.
#
# Depth 2, 1 closer-enemy (others frozen at current position).
# Ply structure:
#   max (self) -> chance (closer_enemy, uniform) -> leaf evaluate
#
# When no enemy is visible, collapses to self-only max.
#
# Leaf evaluator: zoo_features.evaluate with role-appropriate weights.
# Time discipline: depth bound only (depth=2). No signal / time polling.

from __future__ import annotations

import random

from zoo_core import CoreCaptureAgent, TEAM, Directions
from zoo_features import (
    evaluate,
    SEED_WEIGHTS_OFFENSIVE,
    SEED_WEIGHTS_DEFENSIVE,
)

_DEPTH = 2
_NEG_INF = float('-inf')


def createTeam(firstIndex, secondIndex, isRed,
               first='ExpectimaxAgent', second='ExpectimaxAgent'):
    return [ExpectimaxAgent(firstIndex), ExpectimaxAgent(secondIndex)]


class ExpectimaxAgent(CoreCaptureAgent):
    """Expectimax depth-2 agent; opponent node uses uniform expectation."""

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
        """Return (closer_idx, closer_pos) — None pair if no visible enemy."""
        try:
            opponents = self.getOpponents(gameState)
            if not opponents:
                return None, None
            my_pos = gameState.getAgentPosition(self.index)

            def dist_key(pair):
                _, pos = pair
                if pos is None or my_pos is None:
                    return 9999
                return self.getMazeDistance(my_pos, pos)

            pairs = [(idx, gameState.getAgentPosition(idx)) for idx in opponents]
            pairs.sort(key=dist_key)
            return pairs[0]
        except Exception:
            return None, None

    def _leaf_eval(self, gameState, action, weights):
        try:
            return evaluate(self, gameState, action, weights)
        except Exception:
            return _NEG_INF

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _expectimax(self, gameState, depth, is_max_node,
                    agent_idx, weights, self_action):
        """Expectimax search.

        is_max_node=True  -> self (maximiser)
        is_max_node=False -> enemy chance node (uniform expectation)
        depth counts down; leaf at depth == 0.
        self_action: the action self took at root (for leaf evaluator).
        """
        if depth == 0:
            return self._leaf_eval(gameState, self_action, weights)

        if is_max_node:
            try:
                legal = gameState.getLegalActions(self.index)
            except Exception:
                return self._leaf_eval(gameState, self_action, weights)

            if not legal:
                return self._leaf_eval(gameState, self_action, weights)

            best = _NEG_INF
            for action in legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    continue

                if agent_idx is not None:
                    val = self._expectimax(succ, depth - 1, False,
                                          agent_idx, weights, action)
                else:
                    val = self._leaf_eval(succ, action, weights)

                if val > best:
                    best = val
            return best

        else:
            # Chance node: uniform expectation over enemy's legal moves.
            try:
                legal = gameState.getLegalActions(agent_idx)
            except Exception:
                return self._leaf_eval(gameState, self_action, weights)

            if not legal:
                return self._leaf_eval(gameState, self_action, weights)

            total = 0.0
            count = 0
            prob = 1.0 / len(legal)
            for action in legal:
                try:
                    succ = gameState.generateSuccessor(agent_idx, action)
                except Exception:
                    continue
                val = self._leaf_eval(succ, self_action, weights)
                total += val * prob
                count += 1

            if count == 0:
                return self._leaf_eval(gameState, self_action, weights)
            # Re-normalise in case some successors raised.
            return total * (len(legal) / max(count, 1))

    # ------------------------------------------------------------------
    # _chooseActionImpl
    # ------------------------------------------------------------------

    def _chooseActionImpl(self, gameState):
        try:
            weights = self._weights()
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return self._safeFallback(gameState, legal)

            enemy_idx, enemy_pos = self._closer_enemy(gameState)

            # If enemy is invisible, treat as no enemy.
            if enemy_pos is None:
                enemy_idx = None

            best_action = None
            best_val = _NEG_INF

            for action in legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    continue

                if enemy_idx is not None:
                    # depth = _DEPTH - 1 after root expansion.
                    val = self._expectimax(succ, _DEPTH - 1, False,
                                          enemy_idx, weights, action)
                else:
                    val = self._leaf_eval(succ, action, weights)

                if val > best_val:
                    best_val = val
                    best_action = action

            if best_action is None or best_action not in legal:
                return self._safeFallback(gameState, legal)
            return best_action

        except Exception:
            return self._safeFallback(gameState, gameState.getLegalActions(self.index))

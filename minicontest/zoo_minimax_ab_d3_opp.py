# zoo_minimax_ab_d3_opp.py
# ------------------------
# 2-enemy minimax with alpha-beta pruning at depth 3.
# Both enemies are modelled adversarially (NOT frozen).
#
# Ply sequence per full-depth tree:
#   [self(max)] -> [closer_enemy(min)] -> [teammate_approx(static skip)]
#               -> [farther_enemy(min)] -> leaf
#
# "teammate_approx(static skip)" means the teammate's turn is NOT expanded;
# the teammate is treated as stationary (current position frozen) for the
# purposes of this search. This reduces the branching factor substantially
# while still modelling both opponents adversarially.
#
# Move ordering heuristic: for MAX nodes actions are sorted descending by
# leaf evaluator score; for MIN nodes ascending. This improves alpha-beta
# pruning efficiency.
#
# Leaf evaluator: zoo_features.evaluate with role-appropriate weights.
#
# Time discipline: depth bound only (depth=3). No signal / time polling.

from __future__ import annotations

import random

from zoo_core import CoreCaptureAgent, TEAM, Directions
from zoo_features import (
    evaluate,
    SEED_WEIGHTS_OFFENSIVE,
    SEED_WEIGHTS_DEFENSIVE,
)

_DEPTH = 3
_NEG_INF = float('-inf')
_POS_INF = float('inf')


def createTeam(firstIndex, secondIndex, isRed,
               first='MinimaxD3OppAgent', second='MinimaxD3OppAgent'):
    return [MinimaxD3OppAgent(firstIndex), MinimaxD3OppAgent(secondIndex)]


class MinimaxD3OppAgent(CoreCaptureAgent):
    """Depth-3 minimax with alpha-beta; both enemies adversarially modelled."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _weights(self):
        try:
            role = TEAM.role.get(self.index, 'OFFENSE')
        except Exception:
            role = 'OFFENSE'
        return SEED_WEIGHTS_DEFENSIVE if role == 'DEFENSE' else SEED_WEIGHTS_OFFENSIVE

    def _sorted_enemies(self, gameState):
        """Return list of (idx, pos) sorted by maze distance to self (closer first).

        Positions may be None if enemy is invisible.
        """
        try:
            opponents = self.getOpponents(gameState)
            my_pos = gameState.getAgentPosition(self.index)

            def dist_key(pair):
                _, pos = pair
                if pos is None or my_pos is None:
                    return 9999
                return self.getMazeDistance(my_pos, pos)

            pairs = [(idx, gameState.getAgentPosition(idx)) for idx in opponents]
            pairs.sort(key=dist_key)
            return pairs
        except Exception:
            return []

    def _leaf_eval(self, gameState, self_action, weights):
        try:
            return evaluate(self, gameState, self_action, weights)
        except Exception:
            return _NEG_INF

    def _order_actions_max(self, gameState, agent_idx, actions, self_action, weights):
        """Sort actions descending by quick leaf eval (helps alpha-beta for MAX)."""
        try:
            scored = []
            for a in actions:
                try:
                    succ = gameState.generateSuccessor(agent_idx, a)
                    v = evaluate(self, succ, self_action, weights)
                except Exception:
                    v = 0.0
                scored.append((v, a))
            scored.sort(key=lambda x: -x[0])
            return [a for _, a in scored]
        except Exception:
            return actions

    def _order_actions_min(self, gameState, agent_idx, actions, self_action, weights):
        """Sort actions ascending by quick leaf eval (helps alpha-beta for MIN)."""
        try:
            scored = []
            for a in actions:
                try:
                    succ = gameState.generateSuccessor(agent_idx, a)
                    v = evaluate(self, succ, self_action, weights)
                except Exception:
                    v = 0.0
                scored.append((v, a))
            scored.sort(key=lambda x: x[0])
            return [a for _, a in scored]
        except Exception:
            return actions

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _search(self, gameState, depth, alpha, beta,
                ply_agents, ply_idx, weights, self_action):
        """Generic alpha-beta search over a ply_agents sequence.

        ply_agents: list of (agent_idx, is_max) tuples defining the ply order.
        ply_idx:    current position in ply_agents.
        self_action: the action taken by self at root (for leaf evaluator).
        depth:      remaining plies to expand.
        """
        if depth == 0 or ply_idx >= len(ply_agents):
            return self._leaf_eval(gameState, self_action, weights)

        agent_idx, is_max = ply_agents[ply_idx]

        try:
            legal = gameState.getLegalActions(agent_idx)
        except Exception:
            return self._leaf_eval(gameState, self_action, weights)

        if not legal:
            return self._leaf_eval(gameState, self_action, weights)

        # Move ordering for better pruning.
        if is_max:
            legal = self._order_actions_max(gameState, agent_idx, legal, self_action, weights)
        else:
            legal = self._order_actions_min(gameState, agent_idx, legal, self_action, weights)

        if is_max:
            best = _NEG_INF
            for action in legal:
                try:
                    succ = gameState.generateSuccessor(agent_idx, action)
                except Exception:
                    continue
                # For max node (self), propagate the chosen action as self_action.
                sa = action if agent_idx == self.index else self_action
                val = self._search(succ, depth - 1, alpha, beta,
                                   ply_agents, ply_idx + 1, weights, sa)
                if val > best:
                    best = val
                alpha = max(alpha, best)
                if alpha >= beta:
                    break
            return best
        else:
            worst = _POS_INF
            for action in legal:
                try:
                    succ = gameState.generateSuccessor(agent_idx, action)
                except Exception:
                    continue
                val = self._search(succ, depth - 1, alpha, beta,
                                   ply_agents, ply_idx + 1, weights, self_action)
                if val < worst:
                    worst = val
                beta = min(beta, worst)
                if alpha >= beta:
                    break
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

            enemies = self._sorted_enemies(gameState)
            visible_enemies = [(idx, pos) for idx, pos in enemies if pos is not None]

            if not visible_enemies:
                # All enemies invisible — collapse to self-only max (leaf eval).
                best_action = None
                best_val = _NEG_INF
                for action in legal:
                    try:
                        succ = gameState.generateSuccessor(self.index, action)
                        val = evaluate(self, succ, action, weights)
                    except Exception:
                        val = _NEG_INF
                    if val > best_val:
                        best_val = val
                        best_action = action
                if best_action is None or best_action not in legal:
                    return self._safeFallback(gameState, legal)
                return best_action

            # Build ply sequence:
            # ply 0: self (max) — expanded at root loop below
            # ply 1: closer_enemy (min)
            # ply 2: farther_enemy (min)  [if 2 visible enemies]
            # Teammate is skipped (static approximation).
            ply_agents = []
            for idx, _ in visible_enemies[:2]:
                ply_agents.append((idx, False))  # MIN node

            # Move ordering for root (self = MAX).
            ordered_legal = self._order_actions_max(
                gameState, self.index, legal, None, weights)

            best_action = None
            best_val = _NEG_INF
            alpha = _NEG_INF
            beta = _POS_INF

            for action in ordered_legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    continue

                # depth = _DEPTH - 1 because we already expanded root.
                val = self._search(succ, _DEPTH - 1, alpha, beta,
                                   ply_agents, 0, weights, action)

                if val > best_val:
                    best_val = val
                    best_action = action
                alpha = max(alpha, best_val)

            if best_action is None or best_action not in legal:
                return self._safeFallback(gameState, legal)
            return best_action

        except Exception:
            return self._safeFallback(gameState, gameState.getLegalActions(self.index))

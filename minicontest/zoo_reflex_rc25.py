# zoo_reflex_rc25.py
# ------------------
# rc25: Quiescence Search on top of d2 minimax.
#
# Standard alpha-beta truncates at the horizon even when the position is
# tactically VOLATILE — e.g. a ghost or invader is within capture range
# and a single extra ply would reveal a kill. Quiescence search extends
# the horizon by a bounded quiescence depth whenever the position is
# "noisy" (volatile features present).
#
# Volatility predicate (conservative):
#   - any visible enemy within maze-distance 2 of self, OR
#   - self is Pacman and any ghost is within 4 cells, OR
#   - self is ghost and any invader is within 4 cells.
#
# Quiescence depth capped at +2 to keep worst-case branching bounded.
#
# Leaf evaluator: A1 evolved weights via `_weights()` helper (same
# pattern as rc47). Single closer-enemy opponent model.
#
# Tier 2 (H4 Quiescence Search in rc-pool.md).

from __future__ import annotations

import time

from zoo_core import CoreCaptureAgent, TEAM, Directions
from zoo_features import (
    evaluate,
    SEED_WEIGHTS_OFFENSIVE,
    SEED_WEIGHTS_DEFENSIVE,
)
from zoo_reflex_A1 import _A1_OVERRIDE


RC25_TIME_BUDGET = 0.30
RC25_BASE_DEPTH = 4
RC25_QUIESCENCE_MAX = 2
RC25_VOLATILE_GHOST_DIST = 4
RC25_VOLATILE_INVADER_DIST = 4

_NEG_INF = float("-inf")
_POS_INF = float("inf")


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC25Agent", second="ReflexRC25Agent"):
    return [ReflexRC25Agent(firstIndex), ReflexRC25Agent(secondIndex)]


class ReflexRC25Agent(CoreCaptureAgent):
    """Quiescence-extended alpha-beta, depth 2 + up to 2 quiescence."""

    def _weights(self):
        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"
        if _A1_OVERRIDE.get("w_off") and _A1_OVERRIDE.get("w_def"):
            return _A1_OVERRIDE["w_def"] if role == "DEFENSE" else _A1_OVERRIDE["w_off"]
        return SEED_WEIGHTS_DEFENSIVE if role == "DEFENSE" else SEED_WEIGHTS_OFFENSIVE

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

    def _is_volatile(self, gameState):
        """Decide if the position warrants quiescence extension."""
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return False
            my_state = gameState.getAgentState(self.index)
            im_pacman = getattr(my_state, "isPacman", False)
            for opp in self.getOpponents(gameState):
                p = gameState.getAgentPosition(opp)
                if p is None:
                    continue
                d = self.getMazeDistance(my_pos, p)
                if d <= 2:
                    return True
                ost = gameState.getAgentState(opp)
                opp_is_pacman = getattr(ost, "isPacman", False)
                if im_pacman and not opp_is_pacman and d <= RC25_VOLATILE_GHOST_DIST:
                    return True
                if (not im_pacman) and opp_is_pacman and d <= RC25_VOLATILE_INVADER_DIST:
                    return True
            return False
        except Exception:
            return False

    def _leaf_eval(self, gameState, action, weights):
        try:
            return evaluate(self, gameState, action, weights)
        except Exception:
            return _NEG_INF

    def _static_eval(self, gameState, weights):
        try:
            legal = gameState.getLegalActions(self.index)
        except Exception:
            return 0.0
        if not legal:
            return 0.0
        best = _NEG_INF
        for a in legal:
            try:
                v = evaluate(self, gameState, a, weights)
            except Exception:
                continue
            if v > best:
                best = v
        return best if best != _NEG_INF else 0.0

    def _ab(self, gameState, depth, alpha, beta,
            is_max, enemy_idx, weights, deadline, q_budget):
        """Alpha-beta with quiescence.

        q_budget: remaining quiescence plies we can borrow to extend the
        horizon at volatile leaves. Each extension decrements q_budget.
        """
        if time.time() >= deadline:
            return self._static_eval(gameState, weights)

        if depth <= 0:
            # Quiescence check — extend if volatile AND budget remains.
            if q_budget > 0 and self._is_volatile(gameState):
                return self._ab(gameState, 1, alpha, beta,
                                is_max, enemy_idx, weights, deadline,
                                q_budget - 1)
            return self._static_eval(gameState, weights)

        if is_max:
            try:
                legal = gameState.getLegalActions(self.index)
            except Exception:
                return self._static_eval(gameState, weights)
            if not legal:
                return self._static_eval(gameState, weights)

            best = _NEG_INF
            for action in legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    continue
                if enemy_idx is not None and depth > 1:
                    val = self._ab(succ, depth - 1, alpha, beta,
                                   False, enemy_idx, weights, deadline, q_budget)
                else:
                    val = self._leaf_eval(gameState, action, weights)
                if val > best:
                    best = val
                if best > alpha:
                    alpha = best
                if alpha >= beta:
                    break
            return best

        try:
            legal = gameState.getLegalActions(enemy_idx)
        except Exception:
            return self._static_eval(gameState, weights)
        if not legal:
            return self._static_eval(gameState, weights)
        worst = _POS_INF
        for action in legal:
            try:
                succ = gameState.generateSuccessor(enemy_idx, action)
            except Exception:
                continue
            val = self._ab(succ, depth - 1, alpha, beta,
                           True, enemy_idx, weights, deadline, q_budget)
            if val < worst:
                worst = val
            if worst < beta:
                beta = worst
            if alpha >= beta:
                break
        return worst

    def _chooseActionImpl(self, gameState):
        try:
            deadline = time.time() + RC25_TIME_BUDGET
            weights = self._weights()
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            enemy_idx = self._closer_enemy(gameState)
            alpha, beta = _NEG_INF, _POS_INF
            best_action = None
            best_val = _NEG_INF

            for action in legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    continue
                if enemy_idx is not None and RC25_BASE_DEPTH > 1:
                    val = self._ab(succ, RC25_BASE_DEPTH - 1, alpha, beta,
                                   False, enemy_idx, weights, deadline,
                                   RC25_QUIESCENCE_MAX)
                else:
                    val = self._leaf_eval(gameState, action, weights)
                if val > best_val:
                    best_val = val
                    best_action = action
                if best_val > alpha:
                    alpha = best_val

            if best_action is None or best_action not in legal:
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            return best_action
        except Exception:
            try:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            except Exception:
                return Directions.STOP

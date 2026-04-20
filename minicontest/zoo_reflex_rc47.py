# zoo_reflex_rc47.py
# ------------------
# rc47: Engine-grade alpha-beta with iterative-deepening, history
# heuristic move ordering, and a small transposition cache.
#
# Paradigm departure from our reflex-based rc family. Uses the same
# `zoo_features.evaluate` as the leaf evaluator (so it inherits A1's
# learned weights via `zoo_reflex_tuned`) but reaches depth 4-6 at
# 0.8s budget thanks to:
#
#   - IDDFS (iterative deepening depth-first search): search to depth
#     2, 4, 6 sequentially, stopping when budget exceeded. Previous
#     iteration's best move is tried first in next iteration.
#   - History heuristic: per-action counters incremented on cutoffs,
#     decayed between iterations. Orders sibling moves by descending
#     history score.
#   - Alpha-beta pruning with fail-soft convention.
#   - Time polling at every MIN node to abort cleanly before forfeit.
#
# Single closer-enemy minimax reduction (same as zoo_minimax_ab_d2).
#
# This agent is a candidate for your_baseline1.py in the assignment's
# 4-loop output.csv comparison, providing a search-based paradigm
# contrast to our A1/rc82 reflex champions.

from __future__ import annotations

import time
from collections import defaultdict

from zoo_core import CoreCaptureAgent, TEAM, Directions
from zoo_features import (
    evaluate,
    SEED_WEIGHTS_OFFENSIVE,
    SEED_WEIGHTS_DEFENSIVE,
)
from zoo_reflex_A1 import _A1_OVERRIDE


_NEG_INF = float("-inf")
_POS_INF = float("inf")

# Time budget per chooseAction (seconds). Submission cap is 1.0s; we
# leave slack for overhead. When budget exceeded mid-search, we abort
# and return the best action from the last COMPLETED depth.
RC47_TIME_BUDGET = 0.20

# Iterative-deepening target depths. We always finish depth 2 (cheap
# safety net) then attempt deeper levels until budget exceeded.
RC47_DEPTHS = [2, 3, 4]

# How often (in node count) to poll the wall clock. 20 keeps overhead
# low (<1%) while still detecting overruns within ~5ms.
RC47_POLL_EVERY = 20

# History-heuristic decay factor between iterations. 0.5 forgets half
# of the previous iteration's weight each time so recent information
# dominates without discarding it completely.
RC47_HIST_DECAY = 0.5


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC47Agent", second="ReflexRC47Agent"):
    return [ReflexRC47Agent(firstIndex), ReflexRC47Agent(secondIndex)]


class ReflexRC47Agent(CoreCaptureAgent):
    """Engine-grade alpha-beta: IDDFS + history heuristic + TT."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        # Per-agent history scores: dict[action_str -> float]
        self._history = defaultdict(float)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _weights(self):
        """Prefer A1-evolved weights (CEM-learned, baseline-breaking);
        fall back to seed if A1 override is empty."""
        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"
        if _A1_OVERRIDE.get("w_off") and _A1_OVERRIDE.get("w_def"):
            if role == "DEFENSE":
                return _A1_OVERRIDE["w_def"]
            return _A1_OVERRIDE["w_off"]
        return SEED_WEIGHTS_DEFENSIVE if role == "DEFENSE" else SEED_WEIGHTS_OFFENSIVE

    def _closer_enemy(self, gameState):
        """Return closer enemy (idx, pos) or (None, None)."""
        try:
            opponents = self.getOpponents(gameState)
            if not opponents:
                return None, None
            my_pos = gameState.getAgentPosition(self.index)
            best = None
            best_d = 99999
            for idx in opponents:
                p = gameState.getAgentPosition(idx)
                if p is None or my_pos is None:
                    continue
                d = self.getMazeDistance(my_pos, p)
                if d < best_d:
                    best_d = d
                    best = (idx, p)
            return best if best is not None else (None, None)
        except Exception:
            return None, None

    def _leaf_eval(self, gameState, action, weights):
        """Evaluate a (state, self-pre-move-action) pair. Used only when
        the tree is evaluated BEFORE self applies `action`."""
        try:
            return evaluate(self, gameState, action, weights)
        except Exception:
            return _NEG_INF

    def _static_eval(self, gameState, weights):
        """State-only eval: best self-move utility at this state.
        Used at true leaves (post-enemy-move states) where we don't
        want to reuse a stale action reference."""
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

    def _order_actions(self, actions, pv_first=None):
        """Order moves by (pv_first, history score descending, string)."""
        def key(a):
            is_pv = 0 if a == pv_first else 1
            hscore = -self._history.get(a, 0.0)
            return (is_pv, hscore, str(a))
        return sorted(actions, key=key)

    # ------------------------------------------------------------------
    # Alpha-beta with time-abort
    # ------------------------------------------------------------------

    def _ab(self, gameState, depth, alpha, beta,
            is_max, enemy_idx, weights,
            deadline, poll_counter):
        """Alpha-beta. Returns (value, timed_out).

        Convention: `gameState` is the PRE-move state for the agent at this
        node (self if is_max, enemy if not). Leaves use `_static_eval`
        which picks best self-move from here — works for both MAX and
        post-MIN states because self is always the evaluator."""
        # Time check
        poll_counter[0] += 1
        if poll_counter[0] % RC47_POLL_EVERY == 0:
            if time.time() >= deadline:
                return self._static_eval(gameState, weights), True

        if depth == 0:
            return self._static_eval(gameState, weights), False

        if is_max:
            try:
                legal = gameState.getLegalActions(self.index)
            except Exception:
                return self._static_eval(gameState, weights), False
            if not legal:
                return self._static_eval(gameState, weights), False

            ordered = self._order_actions(legal)
            best = _NEG_INF
            for action in ordered:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    continue
                if enemy_idx is not None and depth > 1:
                    # Hand to MIN with enemy to move at `succ`.
                    val, to = self._ab(succ, depth - 1, alpha, beta,
                                       False, enemy_idx, weights,
                                       deadline, poll_counter)
                else:
                    # Direct leaf evaluation of (pre-move-state, action).
                    val = self._leaf_eval(gameState, action, weights)
                    to = False
                if to:
                    return best, True
                if val > best:
                    best = val
                if best > alpha:
                    alpha = best
                if alpha >= beta:
                    self._history[action] += (depth * depth)
                    break
            return best, False

        # MIN node (enemy to move at gameState)
        try:
            legal = gameState.getLegalActions(enemy_idx)
        except Exception:
            return self._static_eval(gameState, weights), False
        if not legal:
            return self._static_eval(gameState, weights), False

        worst = _POS_INF
        for action in legal:
            try:
                succ = gameState.generateSuccessor(enemy_idx, action)
            except Exception:
                continue
            # After enemy moves, self is to move at `succ`.
            val, to = self._ab(succ, depth - 1, alpha, beta,
                               True, enemy_idx, weights,
                               deadline, poll_counter)
            if to:
                return worst, True
            if val < worst:
                worst = val
            if worst < beta:
                beta = worst
            if alpha >= beta:
                break
        return worst, False

    # ------------------------------------------------------------------
    # Root search: IDDFS
    # ------------------------------------------------------------------

    def _iterative_deepening(self, gameState, weights, enemy_idx, deadline):
        """Run IDDFS up to RC47_DEPTHS or until deadline. Returns best action."""
        root_legal = list(gameState.getLegalActions(self.index))
        if not root_legal:
            return None

        # Decay history between calls (persistent across turns).
        for a in list(self._history.keys()):
            self._history[a] *= RC47_HIST_DECAY

        pv_action = None
        best_action = None

        for depth in RC47_DEPTHS:
            if time.time() >= deadline:
                break

            ordered = self._order_actions(root_legal, pv_first=pv_action)
            local_best = _NEG_INF
            local_action = None
            alpha = _NEG_INF
            beta = _POS_INF
            poll_counter = [0]
            aborted = False

            for action in ordered:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    continue
                if enemy_idx is not None and depth > 1:
                    val, to = self._ab(succ, depth - 1, alpha, beta,
                                       False, enemy_idx, weights,
                                       deadline, poll_counter)
                else:
                    val = self._leaf_eval(gameState, action, weights)
                    to = False
                if to:
                    aborted = True
                    break
                if val > local_best:
                    local_best = val
                    local_action = action
                if local_best > alpha:
                    alpha = local_best

            if not aborted and local_action is not None:
                best_action = local_action
                pv_action = local_action
            else:
                # Depth incomplete — keep last completed depth's best.
                break

        return best_action if best_action is not None else root_legal[0]

    # ------------------------------------------------------------------
    # _chooseActionImpl
    # ------------------------------------------------------------------

    def _chooseActionImpl(self, gameState):
        try:
            deadline = time.time() + RC47_TIME_BUDGET
            weights = self._weights()
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            enemy_idx, _ = self._closer_enemy(gameState)
            best = self._iterative_deepening(gameState, weights, enemy_idx, deadline)
            if best is None or best not in legal:
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            return best
        except Exception:
            try:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            except Exception:
                return Directions.STOP

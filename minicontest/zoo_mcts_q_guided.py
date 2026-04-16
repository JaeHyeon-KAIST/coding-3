# zoo_mcts_q_guided.py
# --------------------
# UCB-guided leaf-evaluator search (honest naming per plan §4.4).
#
# This is best-first tree enumeration with UCB1 exploration bonus.
# Unlike traditional MCTS, no Monte-Carlo rollout simulation occurs —
# leaves are directly evaluated by zoo_features.evaluate().
# Honest naming per plan §4.4.
#
# Algorithmically: MCTS-depth-0. The tree is grown via UCB1 tree policy
# (same as zoo_mcts_random and zoo_mcts_heuristic), but when a leaf is
# selected, instead of performing a Monte Carlo rollout, we directly call
# zoo_features.evaluate() on the leaf state. This collapses the simulate
# step to a single O(1) evaluator call, yielding ~10x more iterations per
# second than heuristic rollout (§4.3 iters/sec comparison: 100-500 heuristic
# vs. 1000-3000 leaf-eval-only).
#
# Tree policy : UCB1 with C = sqrt(2)
# Leaf eval   : zoo_features.evaluate() (direct, no rollout)
# Iterations  : MAX_ITERS=1000 hard cap (no time polling — §3.3 Dev phase)
# Return      : robust child (highest visit count)
#
# Candidate for your_best.py seed (plan §4.4 "MCTS-depth-0 offense").

from __future__ import annotations

import math
import random
import time

from zoo_core import CoreCaptureAgent, TEAM, Directions, MAX_ITERS, ROLLOUT_DEPTH, MOVE_BUDGET
from zoo_features import (
    extract_features,
    evaluate,
    SEED_WEIGHTS_OFFENSIVE,
    SEED_WEIGHTS_DEFENSIVE,
)

# UCB1 exploration constant.
_UCB_C = math.sqrt(2)


# ---------------------------------------------------------------------------
# createTeam factory
# ---------------------------------------------------------------------------

def createTeam(firstIndex, secondIndex, isRed,
               first='MCTSQGuidedAgent', second='MCTSQGuidedAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# ---------------------------------------------------------------------------
# MCTSNode
# ---------------------------------------------------------------------------

class _MCTSNode:
    """Single tree node for UCB-guided leaf search."""

    __slots__ = ('visits', 'total_value', 'children', 'parent', 'action',
                 'untried_actions', 'state_hash')

    def __init__(self, state_hash, action, parent, untried_actions):
        self.visits = 0
        self.total_value = 0.0
        self.children = {}
        self.parent = parent
        self.action = action
        self.untried_actions = list(untried_actions)
        self.state_hash = state_hash

    def ucb1(self, parent_visits):
        if self.visits == 0:
            return float('inf')
        exploit = self.total_value / self.visits
        explore = _UCB_C * math.sqrt(math.log(parent_visits) / self.visits)
        return exploit + explore

    def best_child_ucb(self):
        best_score = float('-inf')
        best_child = None
        for child in self.children.values():
            score = child.ucb1(self.visits)
            if score > best_score:
                best_score = score
                best_child = child
        return best_child

    def robust_child(self):
        if not self.children:
            return None
        return max(self.children.values(), key=lambda c: c.visits)


# ---------------------------------------------------------------------------
# State hash helper
# ---------------------------------------------------------------------------

def _state_hash(agent, gameState):
    """Coarse-grained transposition key.

    Key = (myPos, sorted_enemy_positions_tuple, food_count_to_eat,
           capsule_count, max_scared_timer)
    """
    try:
        my_pos = gameState.getAgentPosition(agent.index)
        my_pos = (int(my_pos[0]), int(my_pos[1])) if my_pos else None
    except Exception:
        my_pos = None

    try:
        enemy_positions = []
        for idx in agent.getOpponents(gameState):
            pos = gameState.getAgentPosition(idx)
            if pos is not None:
                enemy_positions.append((int(pos[0]), int(pos[1])))
        enemy_positions_tuple = tuple(sorted(enemy_positions))
    except Exception:
        enemy_positions_tuple = ()

    try:
        food_count = len(agent.getFood(gameState).asList())
    except Exception:
        food_count = 0

    try:
        capsule_count = len(agent.getCapsules(gameState))
    except Exception:
        capsule_count = 0

    try:
        max_scared = max(
            (int(gameState.getAgentState(i).scaredTimer or 0)
             for i in agent.getOpponents(gameState)),
            default=0,
        )
    except Exception:
        max_scared = 0

    return (my_pos, enemy_positions_tuple, food_count, capsule_count, max_scared)


# ---------------------------------------------------------------------------
# MCTSQGuidedAgent
# ---------------------------------------------------------------------------

class MCTSQGuidedAgent(CoreCaptureAgent):
    """UCB-guided leaf-evaluator search (MCTS-depth-0).

    This is best-first tree enumeration with UCB1 exploration bonus.
    Unlike traditional MCTS, no Monte-Carlo rollout simulation occurs —
    leaves are directly evaluated by zoo_features.evaluate().
    Honest naming per plan §4.4.

    Key difference from zoo_mcts_heuristic.py:
    - heuristic: tree policy + ROLLOUT_DEPTH=20 simulate steps + backprop
    - q_guided:  tree policy + direct evaluate() call + backprop
                 (zero simulate steps; the "rollout" is a single O(1) call)

    Expected characteristics:
    - ~10x more iterations per second vs heuristic rollout
    - Wider, shallower effective search vs. heuristic's deeper simulation
    - Performance depends entirely on evaluate() quality (no stochastic averaging)
    - Best suited for offense role where leaf Q-value accurately predicts outcome
    """

    def _get_weights(self):
        try:
            role = TEAM.role.get(self.index, 'OFFENSE')
        except Exception:
            role = 'OFFENSE'
        return SEED_WEIGHTS_DEFENSIVE if role == 'DEFENSE' else SEED_WEIGHTS_OFFENSIVE

    # ----- Search internals -------------------------------------------------

    def _make_node(self, gameState, action, parent):
        try:
            sh = _state_hash(self, gameState)
            legal = gameState.getLegalActions(self.index)
            non_stop = [a for a in legal if a != Directions.STOP]
            stop_actions = [a for a in legal if a == Directions.STOP]
            ordered = non_stop + stop_actions
        except Exception:
            sh = None
            ordered = [Directions.STOP]
        return _MCTSNode(sh, action, parent, ordered)

    def _tree_policy(self, node, gameState):
        """UCB1-based selection and expansion. Returns (leaf_node, leaf_state).

        Identical tree policy to zoo_mcts_random and zoo_mcts_heuristic —
        the only difference is that the returned leaf is directly evaluated
        rather than being used as a rollout start point.
        """
        cur_node = node
        cur_state = gameState

        while True:
            try:
                legal = cur_state.getLegalActions(self.index)
            except Exception:
                break
            if not legal:
                break

            if cur_node.untried_actions:
                action = cur_node.untried_actions.pop(0)
                try:
                    next_state = cur_state.generateSuccessor(self.index, action)
                except Exception:
                    return cur_node, cur_state
                child = self._make_node(next_state, action, cur_node)
                cur_node.children[action] = child
                return child, next_state
            else:
                if not cur_node.children:
                    break
                best = cur_node.best_child_ucb()
                if best is None:
                    break
                try:
                    cur_state = cur_state.generateSuccessor(self.index, best.action)
                except Exception:
                    break
                cur_node = best

        return cur_node, cur_state

    def _leaf_evaluate(self, gameState):
        """Direct leaf evaluation — NO rollout.

        This is the core distinction from traditional MCTS: instead of
        simulating ROLLOUT_DEPTH random or heuristic steps and returning
        the terminal value, we evaluate the leaf state directly using
        zoo_features.evaluate(). The action used for feature extraction is
        STOP (representing 'value of being in this state').

        Returns float.
        """
        try:
            weights = self._get_weights()
            return evaluate(self, gameState, Directions.STOP, weights)
        except Exception:
            return 0.0

    def _backpropagate(self, node, value):
        cur = node
        while cur is not None:
            cur.visits += 1
            cur.total_value += value
            cur = cur.parent

    def _search(self, gameState):
        """Run UCB-guided leaf search until MOVE_BUDGET deadline or MAX_ITERS.

        C4 time-budget polling (pm18): leaf-eval-only, so each iter is
        ~10× faster than heuristic rollout. Typical iter count at 0.8s
        budget ≈ 500-1000 (often saturating MAX_ITERS on simple maps).
        """
        turn_start = time.time()
        deadline = turn_start + MOVE_BUDGET
        root = self._make_node(gameState, None, None)
        root.visits = 1

        iters = 0
        while iters < MAX_ITERS and time.time() < deadline:
            # 1. Tree policy (selection + expansion)
            leaf, leaf_state = self._tree_policy(root, gameState)
            # 2. Leaf evaluation (direct — no rollout)
            value = self._leaf_evaluate(leaf_state)
            # 3. Backpropagation
            self._backpropagate(leaf, value)
            iters += 1

        # Return robust child (highest visit count).
        robust = root.robust_child()
        if robust is not None:
            return robust.action

        # Fallback: static evaluate among legal actions.
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP
        weights = self._get_weights()
        return max(legal, key=lambda a: evaluate(self, gameState, a, weights),
                   default=Directions.STOP)

    # ----- CoreCaptureAgent interface ---------------------------------------

    def _chooseActionImpl(self, gameState):
        try:
            action = self._search(gameState)
            legal = gameState.getLegalActions(self.index)
            if action in legal:
                return action
        except Exception:
            pass
        try:
            legal = gameState.getLegalActions(self.index)
            weights = self._get_weights()
            best = max(legal, key=lambda a: evaluate(self, gameState, a, weights),
                       default=Directions.STOP)
            if best in legal:
                return best
        except Exception:
            pass
        return Directions.STOP

# zoo_mcts_random.py
# ------------------
# MCTS control agent with random rollout policy.
# Role: CONTROL — known-weak; validates test plumbing and serves as a lower bound
# for MCTS-family comparison (plan §4.0 row 10, §4.3).
#
# Tree policy : UCB1 with C = sqrt(2)
# Rollout policy: uniform random legal action at each step (ROLLOUT_DEPTH=20)
# Rollout reward: terminal score if game ended, else zoo_features.evaluate()
# Iterations    : MAX_ITERS=1000 hard cap (no time polling — §3.3 Dev phase)
# Return        : robust child (highest visit count)
#
# Import note: this module is discovered by capture.py's `-r zoo_mcts_random`
# mechanism (imports zoo_mcts_random.py from CWD). All zoo dependencies
# (zoo_core, zoo_features) must be present in the same directory.

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

# UCB1 exploration constant (sqrt(2) is the canonical Kocsis-Szepesvari value).
_UCB_C = math.sqrt(2)


# ---------------------------------------------------------------------------
# createTeam factory — required by capture.py
# ---------------------------------------------------------------------------

def createTeam(firstIndex, secondIndex, isRed,
               first='MCTSRandomAgent', second='MCTSRandomAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# ---------------------------------------------------------------------------
# MCTSNode — lightweight dict-based node
# ---------------------------------------------------------------------------

class _MCTSNode:
    """Single tree node.

    Fields
    ------
    visits      : int — number of times this node has been visited
    total_value : float — cumulative rollout value propagated through this node
    children    : dict[action -> _MCTSNode]
    parent      : _MCTSNode or None
    action      : str — action that led from parent to this node (None for root)
    """

    __slots__ = ('visits', 'total_value', 'children', 'parent', 'action',
                 'untried_actions', 'state_hash')

    def __init__(self, state_hash, action, parent, untried_actions):
        self.visits = 0
        self.total_value = 0.0
        self.children = {}          # action -> _MCTSNode
        self.parent = parent
        self.action = action        # edge label from parent
        self.untried_actions = list(untried_actions)
        self.state_hash = state_hash

    def ucb1(self, parent_visits):
        """UCB1 score. Returns +inf for unvisited nodes (force exploration)."""
        if self.visits == 0:
            return float('inf')
        exploit = self.total_value / self.visits
        explore = _UCB_C * math.sqrt(math.log(parent_visits) / self.visits)
        return exploit + explore

    def best_child_ucb(self):
        """Return child with highest UCB1 score."""
        best_score = float('-inf')
        best_child = None
        for child in self.children.values():
            score = child.ucb1(self.visits)
            if score > best_score:
                best_score = score
                best_child = child
        return best_child

    def robust_child(self):
        """Return child with highest visit count (standard MCTS return policy)."""
        if not self.children:
            return None
        return max(self.children.values(), key=lambda c: c.visits)


# ---------------------------------------------------------------------------
# State hashing helper
# ---------------------------------------------------------------------------

def _state_hash(agent, gameState):
    """Coarse-grained transposition key for speed.

    Key = (myPos, sorted_enemy_positions_tuple, food_count_to_eat,
           capsule_count, max_scared_timer)

    We hash only observable state to avoid the full gameState object cost.
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
# MCTSRandomAgent
# ---------------------------------------------------------------------------

class MCTSRandomAgent(CoreCaptureAgent):
    """MCTS with random rollout policy.

    This is the CONTROL variant — intentionally weak because uniform-random
    rollouts give near-zero signal in most game states. Its expected poor
    performance vs. baseline confirms that the test plumbing works and that
    any improvement seen in the heuristic/q-guided variants is due to the
    rollout quality, not infrastructure differences.
    """

    def _get_weights(self):
        """Role-appropriate weight dict."""
        try:
            role = TEAM.role.get(self.index, 'OFFENSE')
        except Exception:
            role = 'OFFENSE'
        return SEED_WEIGHTS_DEFENSIVE if role == 'DEFENSE' else SEED_WEIGHTS_OFFENSIVE

    # ----- MCTS internals ---------------------------------------------------

    def _make_node(self, gameState, action, parent):
        """Create a new tree node for the given gameState."""
        try:
            sh = _state_hash(self, gameState)
            legal = gameState.getLegalActions(self.index)
            # Prefer non-STOP actions first for ordering.
            non_stop = [a for a in legal if a != Directions.STOP]
            stop_actions = [a for a in legal if a == Directions.STOP]
            ordered = non_stop + stop_actions
        except Exception:
            sh = None
            ordered = [Directions.STOP]
        return _MCTSNode(sh, action, parent, ordered)

    def _tree_policy(self, node, gameState):
        """Select/expand a leaf node using UCB1.

        Returns (leaf_node, leaf_gameState).
        Expands one untried action per call (standard UCT).
        """
        cur_node = node
        cur_state = gameState

        while True:
            # Terminal check — if generateSuccessor would always fail, stop.
            try:
                legal = cur_state.getLegalActions(self.index)
            except Exception:
                break
            if not legal:
                break

            if cur_node.untried_actions:
                # Expand: pick one untried action.
                action = cur_node.untried_actions.pop(0)
                try:
                    next_state = cur_state.generateSuccessor(self.index, action)
                except Exception:
                    # If successor fails, just return current node.
                    return cur_node, cur_state
                child = self._make_node(next_state, action, cur_node)
                cur_node.children[action] = child
                return child, next_state
            else:
                if not cur_node.children:
                    break
                # All children tried — descend by UCB1.
                best = cur_node.best_child_ucb()
                if best is None:
                    break
                try:
                    cur_state = cur_state.generateSuccessor(self.index, best.action)
                except Exception:
                    break
                cur_node = best

        return cur_node, cur_state

    def _rollout(self, gameState):
        """Random rollout from gameState up to ROLLOUT_DEPTH steps.

        At each step, choose a uniformly random legal action for self.index.
        Returns a float reward (evaluate() at terminal state or after depth steps).
        """
        try:
            state = gameState
            weights = self._get_weights()
            for _ in range(ROLLOUT_DEPTH):
                try:
                    legal = state.getLegalActions(self.index)
                except Exception:
                    break
                if not legal:
                    break
                action = random.choice(legal)
                try:
                    state = state.generateSuccessor(self.index, action)
                except Exception:
                    break
            # Evaluate final state: use evaluate() on STOP action as a proxy
            # for the state value (STOP means "stay here and be evaluated").
            try:
                return evaluate(self, state, Directions.STOP, weights)
            except Exception:
                return 0.0
        except Exception:
            return 0.0

    def _backpropagate(self, node, value):
        """Propagate value up to root."""
        cur = node
        while cur is not None:
            cur.visits += 1
            cur.total_value += value
            cur = cur.parent

    def _mcts_search(self, gameState):
        """Run MCTS until MOVE_BUDGET wall-clock deadline or MAX_ITERS cap.

        C4 time-budget polling (pm18): see zoo_mcts_heuristic.py docstring
        for rationale. Random rollouts are cheaper per step than the
        heuristic variant, so the iter count at 0.8s budget is usually
        higher (~50-100).
        """
        turn_start = time.time()
        deadline = turn_start + MOVE_BUDGET
        root = self._make_node(gameState, None, None)
        # Root must be visited once before UCB1 is meaningful.
        root.visits = 1

        iters = 0
        while iters < MAX_ITERS and time.time() < deadline:
            # 1. Tree policy (selection + expansion)
            leaf, leaf_state = self._tree_policy(root, gameState)
            # 2. Rollout
            value = self._rollout(leaf_state)
            # 3. Backpropagation
            self._backpropagate(leaf, value)
            iters += 1

        # Return action of robust child (most visited).
        robust = root.robust_child()
        if robust is not None:
            return robust.action

        # Fallback: best static evaluate among legal actions.
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP
        weights = self._get_weights()
        best_action = max(
            legal,
            key=lambda a: evaluate(self, gameState, a, weights),
            default=Directions.STOP,
        )
        return best_action

    # ----- CoreCaptureAgent interface ---------------------------------------

    def _chooseActionImpl(self, gameState):
        try:
            action = self._mcts_search(gameState)
            legal = gameState.getLegalActions(self.index)
            if action in legal:
                return action
        except Exception:
            pass
        # Fallback: static evaluate
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

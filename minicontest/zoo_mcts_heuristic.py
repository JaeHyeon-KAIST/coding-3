# zoo_mcts_heuristic.py
# ---------------------
# MCTS with greedy heuristic rollout policy.
# Role: Primary MCTS agent (plan §4.3 "MCTS with heuristic rollout").
# This is the "real" MCTS — using reflex evaluator argmax as the rollout
# policy gives genuine Monte Carlo signal (unlike random rollout in
# zoo_mcts_random.py, which is the control/lower-bound).
#
# Tree policy  : UCB1 with C = sqrt(2)
# Rollout policy: argmax of zoo_features.evaluate() at each step (greedy heuristic)
#                 with ROLLOUT_DEPTH=20 and early-stop on food-return or death
# Iterations   : MAX_ITERS=1000 hard cap (no time polling — §3.3 Dev phase)
# Return       : robust child (highest visit count)
#
# Expected performance: substantially better than zoo_mcts_random.py.
# Candidate for your_baseline3.py seed (plan §4.0, §4.3).

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
               first='MCTSHeuristicAgent', second='MCTSHeuristicAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# ---------------------------------------------------------------------------
# MCTSNode
# ---------------------------------------------------------------------------

class _MCTSNode:
    """Single tree node for MCTS."""

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
# MCTSHeuristicAgent
# ---------------------------------------------------------------------------

class MCTSHeuristicAgent(CoreCaptureAgent):
    """MCTS with greedy heuristic rollout.

    The rollout policy selects argmax of zoo_features.evaluate() at each step.
    This is genuine Monte Carlo simulation (unlike zoo_mcts_q_guided which has
    no rollout at all). The heuristic rollout gives substantially better signal
    than random rollout, making this agent a strong MCTS representative.

    Early-stop conditions during rollout:
    - Food carried drops to 0 (food returned home) — positive terminal signal
    - Agent is eaten (position resets to start) — negative terminal signal
    Both are detected via numCarrying and position snap.
    """

    def _get_weights(self):
        try:
            role = TEAM.role.get(self.index, 'OFFENSE')
        except Exception:
            role = 'OFFENSE'
        return SEED_WEIGHTS_DEFENSIVE if role == 'DEFENSE' else SEED_WEIGHTS_OFFENSIVE

    # ----- MCTS internals ---------------------------------------------------

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
        """UCB1-based selection and expansion. Returns (leaf_node, leaf_state)."""
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

    def _rollout(self, gameState):
        """Greedy heuristic rollout: argmax evaluate() at each step.

        Runs up to ROLLOUT_DEPTH steps. Early-stops on:
        - numCarrying drop to 0 after being > 0 (food returned)
        - position reset to start position (eaten)
        Returns float reward.
        """
        try:
            state = gameState
            weights = self._get_weights()

            # Track initial carrying count and position for early-stop detection.
            try:
                prev_carrying = int(
                    state.getAgentState(self.index).numCarrying or 0)
            except Exception:
                prev_carrying = 0
            try:
                prev_pos = state.getAgentPosition(self.index)
            except Exception:
                prev_pos = None

            for _ in range(ROLLOUT_DEPTH):
                try:
                    legal = state.getLegalActions(self.index)
                except Exception:
                    break
                if not legal:
                    break

                # Greedy: pick action maximizing evaluate().
                try:
                    non_stop = [a for a in legal if a != Directions.STOP]
                    candidates = non_stop if non_stop else legal
                    action = max(
                        candidates,
                        key=lambda a: evaluate(self, state, a, weights),
                    )
                except Exception:
                    action = random.choice(legal)

                try:
                    next_state = state.generateSuccessor(self.index, action)
                except Exception:
                    break

                # Early-stop: food returned (carrying dropped to 0 from > 0).
                try:
                    new_carrying = int(
                        next_state.getAgentState(self.index).numCarrying or 0)
                    if prev_carrying > 0 and new_carrying == 0:
                        # Food returned — positive signal; evaluate terminal.
                        try:
                            return evaluate(self, next_state, Directions.STOP, weights)
                        except Exception:
                            return 0.0
                    prev_carrying = new_carrying
                except Exception:
                    pass

                # Early-stop: death (position jumps to start).
                try:
                    new_pos = next_state.getAgentPosition(self.index)
                    if (prev_pos is not None and new_pos is not None
                            and self.start is not None
                            and new_pos == self.start
                            and prev_pos != self.start):
                        # Likely eaten — negative terminal.
                        try:
                            return evaluate(self, next_state, Directions.STOP, weights)
                        except Exception:
                            return 0.0
                    prev_pos = new_pos
                except Exception:
                    pass

                state = next_state

            # Evaluate final state.
            try:
                return evaluate(self, state, Directions.STOP, weights)
            except Exception:
                return 0.0
        except Exception:
            return 0.0

    def _backpropagate(self, node, value):
        cur = node
        while cur is not None:
            cur.visits += 1
            cur.total_value += value
            cur = cur.parent

    def _mcts_search(self, gameState):
        """Run MCTS until MOVE_BUDGET wall-clock deadline or MAX_ITERS cap.

        C4 time-budget polling (pm18): check `time.time() < deadline` before
        each iter. MOVE_BUDGET (0.80s per zoo_core) stays under capture.py's
        1s warning threshold. MAX_ITERS retained as a hard cap against
        clock misbehavior. Typical iter count at 0.8s budget ≈ 30-50
        (heuristic rollout is ~20 steps per iter).
        """
        turn_start = time.time()
        deadline = turn_start + MOVE_BUDGET
        root = self._make_node(gameState, None, None)
        root.visits = 1

        iters = 0
        while iters < MAX_ITERS and time.time() < deadline:
            leaf, leaf_state = self._tree_policy(root, gameState)
            value = self._rollout(leaf_state)
            self._backpropagate(leaf, value)
            iters += 1

        robust = root.robust_child()
        if robust is not None:
            return robust.action

        # Fallback: static evaluate.
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP
        weights = self._get_weights()
        return max(legal, key=lambda a: evaluate(self, gameState, a, weights),
                   default=Directions.STOP)

    # ----- CoreCaptureAgent interface ---------------------------------------

    def _chooseActionImpl(self, gameState):
        try:
            action = self._mcts_search(gameState)
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

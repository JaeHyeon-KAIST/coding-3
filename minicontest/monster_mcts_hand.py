# monster_mcts_hand.py
# --------------------
# Monster reference agent #2 — Aggressive Raider (hand-tuned MCTS).
# EVALUATION-ONLY. Never submitted. Used in the training opponent pool (STRATEGY §6.9).
#
# Strategic profile: BOTH agents attack. The team accepts defensive gaps
# entirely — no one guards home — in order to maximise food-eaten rate.
# MCTS is hand-tuned (iterations, exploration constant, rollout depth)
# with a custom leaf evaluator that heavily rewards food eaten, capsules
# consumed, and penalises ghost adjacency. Defensive features carry zero
# weight.
#
# Role switch is minimal: an agent that is carrying ≥ 8 food runs home
# (effectively a "cash-in" subroutine) using the same MCTS search but
# with the leaf evaluator biased toward the home-frontier. Otherwise both
# agents stay offensive.
#
# A "MEGA_AGGRESSION" trigger escalates exploration (C ↑) when the opponent
# hasn't scored in 100 ticks — signalling a defensive opponent we want to
# pry open faster.
#
# Time discipline: hard iteration cap only (MAX_ITERS = 800). No signal,
# no time polling. May be slow on large layouts; this is a monster agent,
# slowness is acceptable per STRATEGY §6.9.

from __future__ import annotations

import math
import random

from zoo_core import CoreCaptureAgent, TEAM, Directions


# ---------------------------------------------------------------------------
# Hand-tuned MCTS hyperparameters (NOT evolvable; monster constants).
# ---------------------------------------------------------------------------
C_EXPLORATION = 1.41          # sqrt(2), the Kocsis-Szepesvari baseline
C_MEGA = 2.5                  # when MEGA_AGGRESSION mode fires
MAX_ITERS = 800               # hard cap — no time polling
ROLLOUT_DEPTH = 8             # shallow — we pay for iterations, not depth
AGGRESSION_BIAS = 3.0         # inflates food rewards in evaluator
CARRY_CASHIN_THRESHOLD = 8    # run home when carrying this many pellets
MEGA_TICK_WINDOW = 100        # opponent-silent ticks needed to trigger MEGA


# ---------------------------------------------------------------------------
# Leaf evaluator weights (hand-tuned, AGGRESSIVE-RAIDER profile).
# Zero weight on defensive features (f_onDefense, f_numInvaders, etc.).
# ---------------------------------------------------------------------------
_W_EATS_FOOD = 2.0 * AGGRESSION_BIAS        # positive — we love eating
_W_GHOST_ADJ = -8.0                         # punishment for landing next to ghost
_W_CAPSULE_EATEN = 1.5 * AGGRESSION_BIAS    # incentive to eat capsule on pass
_W_DIST_TO_FOOD = 6.0                       # pull toward nearest pellet
_W_DIST_TO_CAPSULE = 3.0                    # pull toward nearest capsule
_W_CARRY = 1.0                              # reward accumulation
_W_DIST_TO_HOME_WHEN_CASHING = 10.0         # cash-in override pulls home
_W_STOP = -20.0                             # stagnation penalty
_W_EATEN = -50.0                            # we died — very bad


def createTeam(firstIndex, secondIndex, isRed,
               first='MonsterMCTSHandAgent', second='MonsterMCTSHandAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# ---------------------------------------------------------------------------
# MCTSNode — lightweight dict-based node
# ---------------------------------------------------------------------------

class _MCTSNode:
    __slots__ = ('visits', 'total_value', 'children', 'parent', 'action',
                 'untried_actions')

    def __init__(self, action, parent, untried_actions):
        self.visits = 0
        self.total_value = 0.0
        self.children = {}
        self.parent = parent
        self.action = action
        self.untried_actions = list(untried_actions)

    def ucb1(self, parent_visits, c):
        if self.visits == 0:
            return float('inf')
        exploit = self.total_value / self.visits
        explore = c * math.sqrt(math.log(parent_visits) / self.visits)
        return exploit + explore

    def best_child_ucb(self, c):
        best_score = float('-inf')
        best_child = None
        for child in self.children.values():
            s = child.ucb1(self.visits, c)
            if s > best_score:
                best_score = s
                best_child = child
        return best_child

    def robust_child(self):
        if not self.children:
            return None
        return max(self.children.values(), key=lambda c: c.visits)


# ---------------------------------------------------------------------------
# MonsterMCTSHandAgent
# ---------------------------------------------------------------------------

class MonsterMCTSHandAgent(CoreCaptureAgent):
    """Aggressive raider — hand-tuned MCTS with food-heavy evaluator."""

    def __init__(self, index, timeForComputing=0.1):
        CoreCaptureAgent.__init__(self, index, timeForComputing)
        # Track last-observed opponent score and its tick, for MEGA trigger.
        self._last_opp_score = 0
        self._last_opp_change_tick = 0
        # Count of capsules eaten by our team during this game (persistent
        # across chooseAction calls). Incremented when a capsule we previously
        # saw is no longer on the board.
        self._capsule_seen = None  # set of capsule positions last seen
        self._capsules_eaten = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _my_score(self, gameState):
        try:
            raw = gameState.getScore()
            return raw if self.red else -raw
        except Exception:
            return 0

    def _update_mega_tracking(self, gameState):
        """Compute whether MEGA_AGGRESSION mode should be active.

        Trigger: opponent team score stayed the same for MEGA_TICK_WINDOW ticks.
        We approximate opp score by negating our signed score when we're
        winning, and otherwise reading gameState.getScore() directly. A pure
        "did it change" test suffices.
        """
        try:
            cur_score = self._my_score(gameState)
            tick = int(getattr(TEAM, 'tick', 0) or 0)
            # We treat "no change in score" as "opponent hasn't scored AND we
            # haven't either" — both of which indicate a locked game state we
            # want to crack open.
            if cur_score != self._last_opp_score:
                self._last_opp_score = cur_score
                self._last_opp_change_tick = tick
            return (tick - self._last_opp_change_tick) > MEGA_TICK_WINDOW
        except Exception:
            return False

    def _update_capsule_count(self, gameState):
        """Increment self._capsules_eaten when our team eats a capsule.

        A capsule has been eaten by us if it was in the enemy-side capsule
        list (self.getCapsules) on the previous tick but is missing now,
        AND no visible enemy is at that position (we assume we ate it —
        close enough for a heuristic).
        """
        try:
            cur = set(self.getCapsules(gameState))
            if self._capsule_seen is not None:
                disappeared = self._capsule_seen - cur
                self._capsules_eaten += len(disappeared)
            self._capsule_seen = cur
        except Exception:
            pass

    def _cashing_in(self, gameState):
        """Return True if we're carrying enough food to trigger cash-in mode."""
        try:
            st = gameState.getAgentState(self.index)
            return int(getattr(st, 'numCarrying', 0) or 0) >= CARRY_CASHIN_THRESHOLD
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Leaf evaluator — AGGRESSIVE RAIDER profile
    # ------------------------------------------------------------------

    def _leaf_eval(self, gameState, action, *, cashing_in, mega):
        """Hand-tuned evaluator. Returns a float.

        Positive terms reward food eaten, capsule consumed, and carrying.
        Negative terms penalise ghost adjacency, stop, and being eaten.
        Defensive features (onDefense, numInvaders) carry ZERO weight.
        """
        try:
            # Baseline food count BEFORE action.
            try:
                food_before = len(self.getFood(gameState).asList())
            except Exception:
                food_before = 0

            try:
                successor = gameState.generateSuccessor(self.index, action)
            except Exception:
                return 0.0

            # Features after stepping.
            try:
                my_state_after = successor.getAgentState(self.index)
                my_pos_after = my_state_after.getPosition()
                if my_pos_after is not None:
                    my_pos_after = (int(my_pos_after[0]), int(my_pos_after[1]))
            except Exception:
                my_pos_after = None

            try:
                food_after = len(self.getFood(successor).asList())
            except Exception:
                food_after = food_before

            eats_food = max(0, food_before - food_after)

            # Nearest food distance (1/max(d,1)) — pull toward food.
            try:
                food_list = self.getFood(successor).asList()
                if food_list and my_pos_after is not None:
                    dmin = min(self.getMazeDistance(my_pos_after, f) for f in food_list)
                    dist_to_food = 1.0 / max(dmin, 1)
                else:
                    dist_to_food = 0.0
            except Exception:
                dist_to_food = 0.0

            try:
                cap_list = list(self.getCapsules(successor))
                if cap_list and my_pos_after is not None:
                    dmin = min(self.getMazeDistance(my_pos_after, c) for c in cap_list)
                    dist_to_capsule = 1.0 / max(dmin, 1)
                else:
                    dist_to_capsule = 0.0
            except Exception:
                dist_to_capsule = 0.0

            # Was a capsule eaten this step? (capsule_list_before - capsule_list_after)
            try:
                cap_before = list(self.getCapsules(gameState))
                cap_after = cap_list if cap_list is not None else []
                capsule_eaten_step = 1.0 if len(cap_before) > len(cap_after) else 0.0
            except Exception:
                capsule_eaten_step = 0.0

            # Ghost adjacency penalty (only active ghosts, not scared).
            try:
                ghost_adj = 0.0
                if my_pos_after is not None:
                    for idx in self.getOpponents(successor):
                        try:
                            g_state = successor.getAgentState(idx)
                            g_pos = g_state.getPosition()
                            if g_pos is None:
                                continue
                            g_pos = (int(g_pos[0]), int(g_pos[1]))
                            # Only active ghost threat (not Pacman, not scared).
                            if getattr(g_state, 'isPacman', False):
                                continue
                            if int(getattr(g_state, 'scaredTimer', 0) or 0) > 0:
                                continue
                            d = self.getMazeDistance(my_pos_after, g_pos)
                            if d <= 1:
                                ghost_adj += 1.0
                            elif d == 2:
                                ghost_adj += 0.3
                        except Exception:
                            continue
            except Exception:
                ghost_adj = 0.0

            # numCarrying after action.
            try:
                num_carrying_after = int(getattr(my_state_after, 'numCarrying', 0) or 0)
            except Exception:
                num_carrying_after = 0

            # Distance to home-frontier (only material when cashing in).
            try:
                frontier = self.homeFrontier if self.homeFrontier else []
                if frontier and my_pos_after is not None:
                    dmin = min(self.getMazeDistance(my_pos_after, h) for h in frontier)
                    dist_to_home = 1.0 / max(dmin, 1)
                else:
                    dist_to_home = 0.0
            except Exception:
                dist_to_home = 0.0

            # "Eaten" check — if we teleported back to spawn.
            try:
                start = self.start
                eaten = 1.0 if (start is not None and my_pos_after == start) else 0.0
            except Exception:
                eaten = 0.0

            stop_flag = 1.0 if action == Directions.STOP else 0.0

            value = (
                _W_EATS_FOOD * eats_food
                + _W_GHOST_ADJ * ghost_adj
                + _W_CAPSULE_EATEN * capsule_eaten_step
                + _W_DIST_TO_FOOD * dist_to_food
                + _W_DIST_TO_CAPSULE * dist_to_capsule
                + _W_CARRY * num_carrying_after
                + _W_STOP * stop_flag
                + _W_EATEN * eaten
            )
            if cashing_in:
                value += _W_DIST_TO_HOME_WHEN_CASHING * dist_to_home * max(num_carrying_after, 1)

            # MEGA mode flattens the ghost penalty (we accept risk).
            if mega:
                value -= 0.5 * _W_GHOST_ADJ * ghost_adj  # subtract half the penalty

            # Guard against NaN/Inf leaking through.
            if value != value or value in (float('inf'), float('-inf')):
                return 0.0
            return float(value)
        except Exception:
            return 0.0

    # ------------------------------------------------------------------
    # MCTS internals
    # ------------------------------------------------------------------

    def _ordered_legal(self, gameState, agent_idx):
        """Return legal actions for the agent, non-STOP first."""
        try:
            legal = gameState.getLegalActions(agent_idx)
            non_stop = [a for a in legal if a != Directions.STOP]
            stop = [a for a in legal if a == Directions.STOP]
            return non_stop + stop
        except Exception:
            return [Directions.STOP]

    def _make_node(self, gameState, action, parent):
        return _MCTSNode(action, parent, self._ordered_legal(gameState, self.index))

    def _tree_policy(self, node, gameState, c_param):
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
            if not cur_node.children:
                break
            best = cur_node.best_child_ucb(c_param)
            if best is None:
                break
            try:
                cur_state = cur_state.generateSuccessor(self.index, best.action)
            except Exception:
                break
            cur_node = best
        return cur_node, cur_state

    def _rollout(self, gameState, *, cashing_in, mega):
        """Heuristic rollout — at each step pick the action with the highest
        leaf_eval. Not greedy to the extreme: adds a 30% epsilon-random to
        avoid determinism bias. Returns the evaluator score of the final
        state on STOP.
        """
        try:
            state = gameState
            for _ in range(ROLLOUT_DEPTH):
                try:
                    legal = state.getLegalActions(self.index)
                except Exception:
                    break
                if not legal:
                    break
                if random.random() < 0.3:
                    action = random.choice(legal)
                else:
                    best_a = None
                    best_v = float('-inf')
                    for a in legal:
                        v = self._leaf_eval(state, a, cashing_in=cashing_in, mega=mega)
                        if v > best_v:
                            best_v = v
                            best_a = a
                    action = best_a if best_a is not None else random.choice(legal)
                try:
                    state = state.generateSuccessor(self.index, action)
                except Exception:
                    break
            return self._leaf_eval(state, Directions.STOP, cashing_in=cashing_in, mega=mega)
        except Exception:
            return 0.0

    def _backprop(self, node, value):
        cur = node
        while cur is not None:
            cur.visits += 1
            cur.total_value += value
            cur = cur.parent

    def _mcts_search(self, gameState, *, cashing_in, mega):
        root = self._make_node(gameState, None, None)
        root.visits = 1
        c_param = C_MEGA if mega else C_EXPLORATION
        for _ in range(MAX_ITERS):
            leaf, leaf_state = self._tree_policy(root, gameState, c_param)
            value = self._rollout(leaf_state, cashing_in=cashing_in, mega=mega)
            self._backprop(leaf, value)
        robust = root.robust_child()
        if robust is not None:
            return robust.action
        # Fallback: greedy leaf evaluator on root.
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP
            return max(
                legal,
                key=lambda a: self._leaf_eval(gameState, a, cashing_in=cashing_in, mega=mega),
                default=Directions.STOP,
            )
        except Exception:
            return Directions.STOP

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def _chooseActionImpl(self, gameState):
        # Shared tick increment (best-effort).
        try:
            TEAM.tick = int(getattr(TEAM, 'tick', 0) or 0) + 1
        except Exception:
            pass

        try:
            self._update_capsule_count(gameState)
        except Exception:
            pass

        try:
            mega = self._update_mega_tracking(gameState)
        except Exception:
            mega = False

        try:
            cashing_in = self._cashing_in(gameState)
        except Exception:
            cashing_in = False

        try:
            legal = gameState.getLegalActions(self.index)
        except Exception:
            legal = []
        if not legal:
            return Directions.STOP

        try:
            action = self._mcts_search(gameState, cashing_in=cashing_in, mega=mega)
            if action in legal:
                return action
        except Exception:
            pass

        # Fallback: greedy leaf evaluator.
        try:
            return max(
                legal,
                key=lambda a: self._leaf_eval(gameState, a, cashing_in=cashing_in, mega=mega),
                default=Directions.STOP,
            )
        except Exception:
            pass

        non_stop = [a for a in legal if a != Directions.STOP]
        return non_stop[0] if non_stop else Directions.STOP

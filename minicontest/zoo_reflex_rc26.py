# zoo_reflex_rc26.py
# ------------------
# rc26: Flat MCTS bandit (UCB1) with A1-reflex rollouts.
#
# Simpler than full tree MCTS — treats each legal root action as an arm
# in a multi-armed bandit, pulls arms according to UCB1, and estimates
# each arm's value by short A1-reflex rollouts.
#
# Different from rc47 (minimax αβ) and rc35 (pure rollout):
#   - UCB1 bandit selection concentrates samples on promising actions
#   - Rollouts use A1 reflex argmax for BOTH teams (self-play estimate)
#   - Rollout depth short (~6) to keep per-turn budget tight
#
# Tier 2 (H5 MCTS-RAVE family, simplified without tree / RAVE).

from __future__ import annotations

import math
import time
import random as _random

from zoo_core import CoreCaptureAgent, TEAM, Directions
from zoo_features import (
    evaluate,
    SEED_WEIGHTS_OFFENSIVE,
    SEED_WEIGHTS_DEFENSIVE,
    _ACTION_PREFERENCE,
)
from zoo_reflex_A1 import _A1_OVERRIDE


RC26_TIME_BUDGET = 0.30
RC26_ROLLOUT_DEPTH = 6
RC26_UCB_C = 1.414
RC26_MAX_PULLS = 150


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC26Agent", second="ReflexRC26Agent"):
    return [ReflexRC26Agent(firstIndex), ReflexRC26Agent(secondIndex)]


class ReflexRC26Agent(CoreCaptureAgent):
    """Flat MCTS bandit with A1-reflex rollouts."""

    def _weights(self):
        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"
        if _A1_OVERRIDE.get("w_off") and _A1_OVERRIDE.get("w_def"):
            return _A1_OVERRIDE["w_def"] if role == "DEFENSE" else _A1_OVERRIDE["w_off"]
        return SEED_WEIGHTS_DEFENSIVE if role == "DEFENSE" else SEED_WEIGHTS_OFFENSIVE

    def _reflex_pick(self, state, agent_idx, weights):
        """Deterministic A1 reflex argmax for any agent."""
        try:
            legal = state.getLegalActions(agent_idx)
        except Exception:
            return None
        if not legal:
            return None
        try:
            ordered = sorted(
                legal,
                key=lambda a: (_ACTION_PREFERENCE.index(a)
                               if a in _ACTION_PREFERENCE
                               else len(_ACTION_PREFERENCE)),
            )
        except Exception:
            ordered = list(legal)
        best = float("-inf")
        best_a = ordered[0]
        for a in ordered:
            try:
                v = evaluate(self, state, a, weights)
            except Exception:
                continue
            if v > best:
                best = v
                best_a = a
        return best_a

    def _rollout(self, state, depth, agent_order, weights, deadline):
        """Simulate `depth` plies using reflex argmax for all agents."""
        s = state
        for step in range(depth):
            if time.time() >= deadline:
                break
            idx = agent_order[step % len(agent_order)]
            a = self._reflex_pick(s, idx, weights)
            if a is None:
                break
            try:
                s = s.generateSuccessor(idx, a)
            except Exception:
                break
        # Terminal state eval = best self-move utility.
        try:
            legal = s.getLegalActions(self.index)
        except Exception:
            return 0.0
        if not legal:
            return 0.0
        best = float("-inf")
        for a in legal:
            try:
                v = evaluate(self, s, a, weights)
            except Exception:
                continue
            if v > best:
                best = v
        return best if best != float("-inf") else 0.0

    def _chooseActionImpl(self, gameState):
        try:
            deadline = time.time() + RC26_TIME_BUDGET
            weights = self._weights()
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP
            if len(legal) == 1:
                return legal[0]

            my_team = sorted(list(self.getTeam(gameState)))
            opps = sorted(list(self.getOpponents(gameState)))
            mate = next((i for i in my_team if i != self.index), self.index)
            opp_first = opps[0] if opps else self.index
            opp_second = opps[1] if len(opps) > 1 else opp_first
            agent_order = [opp_first, mate, opp_second, self.index]

            # Stats: action -> [N, total_reward]
            stats = {a: [0, 0.0] for a in legal}
            pulls = 0

            while time.time() < deadline and pulls < RC26_MAX_PULLS:
                total_N = sum(s[0] for s in stats.values())
                # UCB1 selection
                if total_N == 0:
                    action = legal[0]
                else:
                    best_ucb = float("-inf")
                    action = legal[0]
                    for a in legal:
                        n, w = stats[a]
                        if n == 0:
                            ucb = float("inf")
                        else:
                            mean = w / n
                            ucb = mean + RC26_UCB_C * math.sqrt(
                                math.log(total_N) / n)
                        if ucb > best_ucb:
                            best_ucb = ucb
                            action = a

                # Simulate from succ after our chosen action.
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    stats[action][0] += 1
                    pulls += 1
                    continue
                val = self._rollout(succ, RC26_ROLLOUT_DEPTH,
                                    agent_order, weights, deadline)
                stats[action][0] += 1
                stats[action][1] += val
                pulls += 1

            # Return action with highest mean (ignore unpulled arms).
            best_mean = float("-inf")
            best_a = legal[0]
            try:
                ordered = sorted(
                    legal,
                    key=lambda a: (_ACTION_PREFERENCE.index(a)
                                   if a in _ACTION_PREFERENCE
                                   else len(_ACTION_PREFERENCE)),
                )
            except Exception:
                ordered = list(legal)
            for a in ordered:
                n, w = stats[a]
                if n == 0:
                    continue
                mean = w / n
                if mean > best_mean:
                    best_mean = mean
                    best_a = a
            return best_a if best_a in legal else legal[0]
        except Exception:
            try:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            except Exception:
                return Directions.STOP

# zoo_reflex_rc36.py
# ------------------
# rc36: Dyna-Q-lite (inference-only rollouts using game-score delta).
#
# Different from rc35 (feature-eval rollout, FAILED) and rc26 (UCB1
# bandit). rc36 rolls out each legal action using A1 reflex argmax for
# ALL agents (self + teammate + 2 opponents), then scores by the ACTUAL
# game-score delta (state.getScore() final − initial) rather than the
# linear feature evaluator.
#
# The score-delta reward is more faithful to the actual game objective
# (food eaten − food lost) and less vulnerable to evaluator exploit
# than the feature-linear score.
#
# Tier 2 (I2 Dyna-Q in rc-pool.md; no actual Q-table learning, just the
# model-based rollout idea).

from __future__ import annotations

import time

from zoo_core import CoreCaptureAgent, TEAM, Directions
from zoo_features import (
    evaluate,
    SEED_WEIGHTS_OFFENSIVE,
    SEED_WEIGHTS_DEFENSIVE,
    _ACTION_PREFERENCE,
)
from zoo_reflex_A1 import _A1_OVERRIDE


RC36_TIME_BUDGET = 0.30
RC36_ROLLOUT_DEPTH = 12
RC36_K = 3


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC36Agent", second="ReflexRC36Agent"):
    return [ReflexRC36Agent(firstIndex), ReflexRC36Agent(secondIndex)]


class ReflexRC36Agent(CoreCaptureAgent):
    """Score-delta rollout policy iteration."""

    def _weights(self):
        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"
        if _A1_OVERRIDE.get("w_off") and _A1_OVERRIDE.get("w_def"):
            return _A1_OVERRIDE["w_def"] if role == "DEFENSE" else _A1_OVERRIDE["w_off"]
        return SEED_WEIGHTS_DEFENSIVE if role == "DEFENSE" else SEED_WEIGHTS_OFFENSIVE

    def _reflex_pick(self, state, agent_idx, weights):
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

    def _my_score(self, state):
        try:
            s = state.getScore()
            return s if self.red else -s
        except Exception:
            return 0

    def _rollout_delta(self, state, depth, agent_order, weights, deadline):
        """Return score-delta after `depth` plies of reflex self-play."""
        s_start = self._my_score(state)
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
        return float(self._my_score(s) - s_start)

    def _chooseActionImpl(self, gameState):
        try:
            deadline = time.time() + RC36_TIME_BUDGET
            weights = self._weights()
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            my_team = sorted(list(self.getTeam(gameState)))
            opps = sorted(list(self.getOpponents(gameState)))
            mate = next((i for i in my_team if i != self.index), self.index)
            opp_first = opps[0] if opps else self.index
            opp_second = opps[1] if len(opps) > 1 else opp_first
            agent_order = [opp_first, mate, opp_second, self.index]

            # Fallback: A1 reflex scores for tie-breaking.
            a1_scores = {}
            for a in legal:
                try:
                    a1_scores[a] = evaluate(self, gameState, a, weights)
                except Exception:
                    a1_scores[a] = float("-inf")

            best_delta = float("-inf")
            best_action = None
            for action in legal:
                if time.time() >= deadline:
                    break
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    continue
                total = 0.0
                count = 0
                for k in range(RC36_K):
                    if time.time() >= deadline:
                        break
                    d = self._rollout_delta(succ, RC36_ROLLOUT_DEPTH,
                                            agent_order, weights, deadline)
                    total += d
                    count += 1
                if count == 0:
                    continue
                mean_delta = total / count
                # Combine with A1 score (small weight) for tie-break & safety.
                combined = mean_delta * 100.0 + a1_scores.get(action, 0.0)
                if combined > best_delta:
                    best_delta = combined
                    best_action = action

            if best_action is None:
                # Fall back to A1 argmax
                best_action = max(legal, key=lambda a: a1_scores.get(a, float("-inf")))
            if best_action not in legal:
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

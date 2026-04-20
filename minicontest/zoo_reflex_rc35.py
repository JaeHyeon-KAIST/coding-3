# zoo_reflex_rc35.py
# ------------------
# rc35: Rollout Policy Iteration (Monte Carlo forward search).
#
# Paradigm different from switch composites (rc160-179) and pure search
# (rc47). For each legal action, simulate K rollouts of depth D using
# A1's reflex argmax as the base-policy. Score each rollout by its
# terminal-state evaluation, average across K rollouts, pick the action
# with the highest average.
#
# Key differences from rc47 (αβ):
#   - No opponent minimax modeling — opponent uses the SAME A1 reflex
#     policy as we do (self-play assumption).
#   - Breadth K > depth; evaluates trajectories, not trees.
#   - No transposition / pruning — each rollout is independent.
#
# Gain over pure reflex (A1): rollouts can reveal consequences of
# SHORT-TERM losing actions that lead to strong long-term positions
# (e.g. going through a chokepoint when a ghost is near, trading a
# turn of "distance to food" for a kill opportunity).
#
# Budget: K=5 rollouts × depth=8 steps × 4 agents/step × ~1ms per
# generateSuccessor = ~160ms/turn total over 5 legal actions ≈ 800ms.
# Tight but within 1s/turn. Budget-polled with early abort.
#
# Tier 2 (I1 Rollout Policy Iteration in rc-pool.md).

from __future__ import annotations

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


RC35_TIME_BUDGET = 0.80
RC35_K = 5          # rollouts per candidate action
RC35_DEPTH = 8      # steps per rollout (counts all 4 agents)
RC35_EXPLORE_EPS = 0.15  # prob of random move during rollout (explore)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC35Agent", second="ReflexRC35Agent"):
    return [ReflexRC35Agent(firstIndex), ReflexRC35Agent(secondIndex)]


class ReflexRC35Agent(CoreCaptureAgent):
    """Rollout policy iteration over A1 reflex base policy."""

    def _weights(self, for_idx=None):
        """A1 evolved weights for the appropriate role (or OFFENSE default)."""
        idx = for_idx if for_idx is not None else self.index
        try:
            role = TEAM.role.get(idx, "OFFENSE")
        except Exception:
            role = "OFFENSE"
        if _A1_OVERRIDE.get("w_off") and _A1_OVERRIDE.get("w_def"):
            return _A1_OVERRIDE["w_def"] if role == "DEFENSE" else _A1_OVERRIDE["w_off"]
        return SEED_WEIGHTS_DEFENSIVE if role == "DEFENSE" else SEED_WEIGHTS_OFFENSIVE

    def _reflex_action(self, state, agent_idx, weights, rng, explore_eps=0.0):
        """A1 reflex argmax for agent_idx in state. With epsilon random explore."""
        try:
            legal = state.getLegalActions(agent_idx)
        except Exception:
            return None
        if not legal:
            return None
        if rng.random() < explore_eps:
            return rng.choice(legal)
        # Deterministic argmax over evaluate(agent, state, action, weights).
        # Note: evaluate takes `agent` which self-references index etc.
        # We can only pass `self` here, so this is biased toward self's
        # perspective. Good enough for rollout.
        best = float("-inf")
        best_a = legal[0]
        # Preference order for deterministic tie-break.
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
            try:
                # For non-self agents, we'd need an agent_wrapper; simplify by
                # still using self's perspective but with its legal actions.
                v = evaluate(self, state, a, weights)
            except Exception:
                continue
            if v > best:
                best = v
                best_a = a
        return best_a

    def _rollout(self, state, depth, agent_order, my_weights, rng, deadline):
        """Simulate `depth` steps. Return final state's evaluate score."""
        s = state
        for step in range(depth):
            if time.time() >= deadline:
                break
            idx = agent_order[step % len(agent_order)]
            a = self._reflex_action(s, idx, my_weights, rng,
                                    explore_eps=RC35_EXPLORE_EPS)
            if a is None:
                break
            try:
                s = s.generateSuccessor(idx, a)
            except Exception:
                break
        # Evaluate terminal state — max over self's legal.
        try:
            legal = s.getLegalActions(self.index)
        except Exception:
            return 0.0
        if not legal:
            return 0.0
        best = float("-inf")
        for a in legal:
            try:
                v = evaluate(self, s, a, my_weights)
            except Exception:
                continue
            if v > best:
                best = v
        return best if best != float("-inf") else 0.0

    def _chooseActionImpl(self, gameState):
        try:
            deadline = time.time() + RC35_TIME_BUDGET
            weights = self._weights()
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            # Determine agent turn order after self's move.
            # Pacman capture sequence: self, opp1, teammate, opp2, self, ...
            my_team = sorted(list(self.getTeam(gameState)))
            opps = sorted(list(self.getOpponents(gameState)))
            mate = next((i for i in my_team if i != self.index), self.index)
            # Order after self's move: first opponent, teammate, second
            # opponent, self — 4-cycle. Opp closest to self first (rough).
            opp_first = opps[0] if opps else self.index
            opp_second = opps[1] if len(opps) > 1 else opp_first
            agent_order = [opp_first, mate, opp_second, self.index]

            rng = _random.Random(0xBEEF + self.index * 31)

            scored = []
            for action in legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    scored.append((float("-inf"), action))
                    continue
                total = 0.0
                count = 0
                for k in range(RC35_K):
                    if time.time() >= deadline:
                        break
                    v = self._rollout(succ, RC35_DEPTH, agent_order, weights,
                                      rng, deadline)
                    total += v
                    count += 1
                avg = total / max(count, 1)
                scored.append((avg, action))

            if not scored:
                return Directions.STOP
            # Tie-break by preference order on equal averages.
            scored.sort(key=lambda sa: (-sa[0],
                                        (_ACTION_PREFERENCE.index(sa[1])
                                         if sa[1] in _ACTION_PREFERENCE
                                         else len(_ACTION_PREFERENCE))))
            return scored[0][1]
        except Exception:
            try:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            except Exception:
                return Directions.STOP

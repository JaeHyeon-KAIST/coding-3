# zoo_reflex_rc126.py
# ------------------
# rc126: rc109 + rc88 2-ply lookahead on OFFENSE.
#
# rc109 = rc16+rc29 OFF + rc82 DEF (100%). rc88 (2-ply self-play
# lookahead) scored 80% solo. Combined: rc109 offense wraps its
# chosen action in a 2-ply value veto — if the chosen action has
# WORSE 2-ply value than A1's argmax, fall back to argmax. Tests
# whether lookahead veto finally lifts rc109 above 100% (by
# rejecting bad REVERSE choices) or degrades it.

from __future__ import annotations

import time

from zoo_reflex_rc109 import ReflexRC109OffenseAgent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_features import evaluate
from game import Directions


RC126_GAMMA = 0.6
RC126_TIME_BUDGET_WARN = 0.80


def _two_ply_value(agent, gameState, action, weights, gamma):
    try:
        s1 = evaluate(agent, gameState, action, weights)
    except Exception:
        return float("-inf")
    if s1 == float("-inf"):
        return s1
    try:
        succ = gameState.generateSuccessor(agent.index, action)
        legal2 = succ.getLegalActions(agent.index)
        if not legal2:
            return s1
        best_s2 = float("-inf")
        for a2 in legal2:
            try:
                s2 = evaluate(agent, succ, a2, weights)
            except Exception:
                s2 = float("-inf")
            if s2 > best_s2:
                best_s2 = s2
        return s1 + gamma * (best_s2 if best_s2 != float("-inf") else 0)
    except Exception:
        return s1


class ReflexRC126OffenseAgent(ReflexRC109OffenseAgent):
    """rc109 offense + 2-ply lookahead veto."""

    def _chooseActionImpl(self, gameState):
        t0 = time.time()
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP
        try:
            rc109_choice = super()._chooseActionImpl(gameState)
        except Exception:
            return super()._chooseActionImpl(gameState)
        try:
            weights = self._get_weights()
            scored_1ply = {}
            for action in legal:
                try:
                    s = evaluate(self, gameState, action, weights)
                except Exception:
                    s = float("-inf")
                scored_1ply[action] = s
            a1_argmax = max(scored_1ply.items(), key=lambda kv: kv[1])[0]
            if rc109_choice == a1_argmax:
                return rc109_choice
            v_109 = _two_ply_value(self, gameState, rc109_choice, weights, RC126_GAMMA)
            v_a1 = _two_ply_value(self, gameState, a1_argmax, weights, RC126_GAMMA)
            if v_109 >= v_a1 - 1e-6:
                return rc109_choice
            return a1_argmax
        except Exception:
            return rc109_choice
        finally:
            dt = time.time() - t0
            if dt > RC126_TIME_BUDGET_WARN:
                try:
                    print(f"[rc126] warn: turn took {dt:.3f}s")
                except Exception:
                    pass


def createTeam(firstIndex, secondIndex, isRed,
               first="rc126-offense", second="rc126-defense"):
    return [ReflexRC126OffenseAgent(firstIndex),
            ReflexRC82Agent(secondIndex)]

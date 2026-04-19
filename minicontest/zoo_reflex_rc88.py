# zoo_reflex_rc88.py
# ------------------
# rc88: 2-ply reflex lookahead overlay on A1 champion.
#
# A1's argmax is pure 1-ply (score each legal action's successor
# state, pick argmax). rc88 adds a 2-ply horizon:
#   - For each legal action a1, simulate successor state.
#   - In successor, score each legal action a2 with A1's weights.
#   - Value(a1) = A1_score(a1) + γ · max_{a2} A1_score(a2)
#   - Pick argmax over Value(a1).
#
# γ = RC88_GAMMA (0.6 — discount so 2-ply signal doesn't overwhelm
# 1-ply). The 2-ply max is a *self-play* lookahead — we don't model
# the opponent's move. Still helps: it distinguishes "this action
# has a great successor that's a dead-end" (low 2-ply) from "this
# action has a great successor that opens further options" (high
# 2-ply).
#
# Cost: ~5 legal × ~5 legal = ~25 A1 evaluations per turn. Measured
# ~40-80 ms on defaultCapture — comfortably under 1 sec. No
# parallelization.

from __future__ import annotations

import time

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions


RC88_GAMMA = 0.6
RC88_TIME_BUDGET_WARN = 0.80


class ReflexRC88Agent(ReflexA1Agent):
    """A1 champion + 2-ply self-play lookahead argmax."""

    def _chooseActionImpl(self, gameState):
        t0 = time.time()
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        try:
            weights = self._get_weights()

            scored_1ply = {}
            for action in legal:
                try:
                    s = evaluate(self, gameState, action, weights)
                except Exception:
                    s = float("-inf")
                scored_1ply[action] = s
            best_1 = max(scored_1ply.values()) if scored_1ply else None
            if best_1 is None or best_1 == float("-inf"):
                return super()._chooseActionImpl(gameState)

            # 2-ply lookahead for each 1-ply action.
            combined = {}
            for a1 in legal:
                s1 = scored_1ply[a1]
                if s1 == float("-inf"):
                    combined[a1] = float("-inf")
                    continue
                try:
                    succ = gameState.generateSuccessor(self.index, a1)
                    legal2 = succ.getLegalActions(self.index)
                    if not legal2:
                        combined[a1] = s1
                        continue
                    best_s2 = float("-inf")
                    for a2 in legal2:
                        try:
                            s2 = evaluate(self, succ, a2, weights)
                        except Exception:
                            s2 = float("-inf")
                        if s2 > best_s2:
                            best_s2 = s2
                    combined[a1] = s1 + RC88_GAMMA * (best_s2 if
                                                       best_s2 != float("-inf") else 0)
                except Exception:
                    combined[a1] = s1

            chosen = max(combined.items(), key=lambda kv: kv[1])[0]
        except Exception:
            return super()._chooseActionImpl(gameState)

        dt = time.time() - t0
        if dt > RC88_TIME_BUDGET_WARN:
            try:
                print(f"[rc88] warn: turn took {dt:.3f}s")
            except Exception:
                pass
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC88Agent", second="ReflexRC88Agent"):
    return [ReflexRC88Agent(firstIndex), ReflexRC88Agent(secondIndex)]

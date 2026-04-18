# zoo_reflex_rc15.py
# ------------------
# rc15: F2 ensemble voting over A1 + rc02 + D13.
#
# Motivation: the Phase 4 round-robin currently has 6-8 candidates that each
# beat baseline 75-100%. Their error modes likely differ — rc02's AP
# defense works for articulation cuts, D13 uses role-swap + endgame rules,
# A1 is pure-CEM. If we VOTE among three complementary agents on the same
# turn, errors of any one agent get dominated by the other two, and the
# ensemble's expected WR should exceed each individual (classic bagging
# intuition applied at the action level).
#
# Design:
#   For each turn, compute three candidate actions:
#     - action_A1: pure A1 argmax (`ReflexA1Agent._chooseActionImpl`)
#     - action_RC02: A1 + Tarjan AP defense override
#     - action_D13: A1 + D1 role-swap + D3 endgame rules
#   Majority vote. Ties broken by rc02 preference (strongest single member
#   at 100% vs baseline) then A1 then D13.
#
# Budget: three lightweight argmax evaluations on the same state. Each
# inner _chooseActionImpl is ~15-50ms (A1 argmax over ≤5 legal actions
# using a 20-dim feature-sum). Total well under the 1-sec / turn budget;
# we log warnings if we ever exceed 700ms.
#
# Any failure in any member falls through — if all three fail, pure A1.

from __future__ import annotations

import time
from collections import Counter

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent

# Import overlay classes — only needed at instantiate-time.
from zoo_reflex_rc02 import ReflexRC02Agent, _articulation_points
from zoo_reflex_A1_D13 import ReflexA1D13Agent
from game import Directions


RC15_TIME_BUDGET_WARN = 0.70   # seconds


class ReflexRC15Agent(ReflexA1Agent):
    """A1 + rc02 + D13 ensemble via majority vote."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        # Precompute Tarjan APs for the rc02 branch.
        try:
            walls = gameState.getWalls()
            self.tarjan_aps = _articulation_points(walls)
        except Exception:
            self.tarjan_aps = frozenset()

    def _action_a1(self, gameState):
        """Pure A1 argmax (skips any overlays)."""
        try:
            return ReflexA1Agent._chooseActionImpl(self, gameState)
        except Exception:
            return None

    def _action_rc02(self, gameState):
        """A1 + Tarjan AP defense override."""
        try:
            return ReflexRC02Agent._chooseActionImpl(self, gameState)
        except Exception:
            return None

    def _action_d13(self, gameState):
        """A1 + D1 role-swap + D3 endgame (full D13 rules)."""
        try:
            return ReflexA1D13Agent._chooseActionImpl(self, gameState)
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        t0 = time.time()

        a_a1 = self._action_a1(gameState)
        a_rc02 = self._action_rc02(gameState)
        a_d13 = self._action_d13(gameState)

        legal = gameState.getLegalActions(self.index)
        votes = [a for a in (a_a1, a_rc02, a_d13) if a is not None and a in legal]

        if not votes:
            # All members failed — absolute fallback.
            return Directions.STOP if Directions.STOP in legal else (
                legal[0] if legal else Directions.STOP
            )

        counts = Counter(votes)
        top_count = max(counts.values())
        top_actions = [a for a, c in counts.items() if c == top_count]

        if len(top_actions) == 1:
            chosen = top_actions[0]
        else:
            # Tie-break: rc02 > a1 > d13.
            if a_rc02 is not None and a_rc02 in top_actions:
                chosen = a_rc02
            elif a_a1 is not None and a_a1 in top_actions:
                chosen = a_a1
            elif a_d13 is not None and a_d13 in top_actions:
                chosen = a_d13
            else:
                chosen = top_actions[0]

        dt = time.time() - t0
        if dt > RC15_TIME_BUDGET_WARN:
            # Log but never raise — framework will warn via its own timer.
            try:
                print(
                    f"[rc15] warn: turn took {dt:.3f}s (>{RC15_TIME_BUDGET_WARN}s budget)"
                )
            except Exception:
                pass

        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC15Agent", second="ReflexRC15Agent"):
    return [ReflexRC15Agent(firstIndex), ReflexRC15Agent(secondIndex)]

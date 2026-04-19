# zoo_reflex_rc45.py
# ------------------
# rc45: N3 weighted ensemble voting across top-3 single-candidate agents.
#
# rc15 used simple majority among A1 + rc02 + D13. rc45 upgrades by:
#   (a) Including rc16 Voronoi (also 100% vs baseline on 40-game smoke).
#   (b) Using validation-WR-weighted votes rather than equal votes. An
#       action with more "total validation weight" behind it wins.
#   (c) Tie-breaking by summed weights, not by hardcoded ordering.
#
# Weighting scheme (from pm23 40-game WR vs baseline):
#   A1       → 0.825
#   rc02     → 1.00
#   rc16     → 1.00
#   D13      → 0.925  (pm20's hth_t4 result, best D-series)
#
# Each member "votes" for its chosen legal action, contributing its
# weight to that action's tally. Winning action = argmax of tallies.
#
# Member instances reuse our registerInitialState setup: rc02 needs
# tarjan_aps (computed here), and D13 inherits A1 but doesn't need extra
# precompute. rc16 requires Voronoi feature eval inline.
#
# Budget: up to 4 lightweight A1-style argmaxes per turn. Measured
# ~25-40ms / turn on defaultCapture — well under 1 sec.

from __future__ import annotations

import time
from collections import defaultdict

from zoo_reflex_A1 import ReflexA1Agent
from zoo_reflex_rc02 import ReflexRC02Agent, _articulation_points
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_A1_D13 import ReflexA1D13Agent
from game import Directions


# Weights ≈ empirical 40-game baseline WR.
RC45_WEIGHTS = {
    "a1":   0.825,
    "rc02": 1.000,
    "rc16": 1.000,
    "d13":  0.925,
}

RC45_TIME_BUDGET_WARN = 0.80


class ReflexRC45Agent(ReflexA1Agent):
    """A1 + rc02 + rc16 + D13 weighted ensemble."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self.tarjan_aps = _articulation_points(gameState.getWalls())
        except Exception:
            self.tarjan_aps = frozenset()

    def _vote_a1(self, gameState):
        try:
            return ReflexA1Agent._chooseActionImpl(self, gameState)
        except Exception:
            return None

    def _vote_rc02(self, gameState):
        try:
            return ReflexRC02Agent._chooseActionImpl(self, gameState)
        except Exception:
            return None

    def _vote_rc16(self, gameState):
        try:
            return ReflexRC16Agent._chooseActionImpl(self, gameState)
        except Exception:
            return None

    def _vote_d13(self, gameState):
        try:
            return ReflexA1D13Agent._chooseActionImpl(self, gameState)
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        t0 = time.time()
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        votes = {
            "a1":   self._vote_a1(gameState),
            "rc02": self._vote_rc02(gameState),
            "rc16": self._vote_rc16(gameState),
            "d13":  self._vote_d13(gameState),
        }

        tallies = defaultdict(float)
        for name, act in votes.items():
            if act is None or act not in legal:
                continue
            tallies[act] += RC45_WEIGHTS[name]

        if not tallies:
            return Directions.STOP if Directions.STOP in legal else (
                legal[0] if legal else Directions.STOP
            )

        chosen = max(tallies.items(), key=lambda kv: kv[1])[0]

        dt = time.time() - t0
        if dt > RC45_TIME_BUDGET_WARN:
            try:
                print(f"[rc45] warn: turn took {dt:.3f}s")
            except Exception:
                pass
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC45Agent", second="ReflexRC45Agent"):
    return [ReflexRC45Agent(firstIndex), ReflexRC45Agent(secondIndex)]

# zoo_reflex_rc94.py
# ------------------
# rc94: Dense 3-champion vote over rc02 + rc16 + rc82 (all 100% solo).
#
# rc83 did a 5-way ensemble (A1 + rc02 + rc16 + rc82 + rc21) and
# reached only 90% — hypothesis was "ensemble dilution". rc94 tests
# that hypothesis by voting over ONLY the 100%-WR members, removing
# the weaker A1 and rc21 votes that might have pulled the signal
# down in rc83.
#
# If ensemble dilution hypothesis holds, rc94 should exceed rc83's
# 90% — ideally approaching the 100% ceiling of its components.
# If voting 3 perfect members still underperforms solo, the
# dilution mechanism is deeper (maybe they disagree on the same
# ambiguous state in different ways, and tie-breaking corrupts).

from __future__ import annotations

import time
from collections import defaultdict

from zoo_reflex_A1 import ReflexA1Agent
from zoo_reflex_rc02 import ReflexRC02Agent, _articulation_points
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc82 import ReflexRC82Agent
from game import Directions


RC94_WEIGHTS = {
    "rc02": 1.0,
    "rc16": 1.0,
    "rc82": 1.0,
}

RC94_TIME_BUDGET_WARN = 0.80


class ReflexRC94Agent(ReflexA1Agent):
    """3-way equal-weight vote over rc02 + rc16 + rc82 (all 100%)."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self.tarjan_aps = _articulation_points(gameState.getWalls())
        except Exception:
            self.tarjan_aps = frozenset()
        try:
            from collections import deque
            self._rc82_hist = deque(maxlen=4)
        except Exception:
            pass
        self._rc44_turn = 0

    def _chooseActionImpl(self, gameState):
        t0 = time.time()
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        def _safe_vote(fn):
            try:
                v = fn(self, gameState)
                if v in legal:
                    return v
                return None
            except Exception:
                return None

        votes = {
            "rc02": _safe_vote(ReflexRC02Agent._chooseActionImpl),
            "rc16": _safe_vote(ReflexRC16Agent._chooseActionImpl),
            "rc82": _safe_vote(ReflexRC82Agent._chooseActionImpl),
        }

        tallies = defaultdict(float)
        for name, act in votes.items():
            if act is None:
                continue
            tallies[act] += RC94_WEIGHTS.get(name, 0.0)

        if not tallies:
            return Directions.STOP if Directions.STOP in legal else legal[0]

        # Tie-break: prefer rc82's action (highest-complexity overlay).
        max_tally = max(tallies.values())
        tied = [a for a, t in tallies.items() if t == max_tally]
        if len(tied) == 1:
            chosen = tied[0]
        elif votes.get("rc82") in tied:
            chosen = votes["rc82"]
        elif votes.get("rc02") in tied:
            chosen = votes["rc02"]
        else:
            chosen = tied[0]

        dt = time.time() - t0
        if dt > RC94_TIME_BUDGET_WARN:
            try:
                print(f"[rc94] warn: turn took {dt:.3f}s")
            except Exception:
                pass
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC94Agent", second="ReflexRC94Agent"):
    return [ReflexRC94Agent(firstIndex), ReflexRC94Agent(secondIndex)]

# zoo_reflex_rc102.py
# ------------------
# rc102: rc82 + rc45 weighted-ensemble voting sibling.
#
# rc45 is a 4-member weighted vote (A1 + rc02 + rc16 + D13 — the
# pre-rc82 ensemble). rc102 adds rc82 as a 5th member but uses the
# EMPIRICAL per-member WR as weight (like rc45), NOT equal (like
# rc94). This differs from rc83 because we use pm24's actual WRs
# and DROP A1 (redundant given rc82 inherits A1):
#
#   rc02  → 1.000
#   rc16  → 1.000
#   rc82  → 1.000
#   D13   → 0.925
#   rc21  → 0.950
#
# Strongest members get highest weight. Tie-break: rc82 (highest
# complexity). Test: does weighted vote do better than equal vote
# (rc94, 95%)?

from __future__ import annotations

import time
from collections import defaultdict, deque

from zoo_reflex_A1 import ReflexA1Agent
from zoo_reflex_rc02 import ReflexRC02Agent, _articulation_points
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc21 import ReflexRC21Agent
from zoo_reflex_A1_D13 import ReflexA1D13Agent
from game import Directions


RC102_WEIGHTS = {
    "rc02": 1.000,
    "rc16": 1.000,
    "rc82": 1.000,
    "d13":  0.925,
    "rc21": 0.950,
}

RC102_TIME_BUDGET_WARN = 0.80


class ReflexRC102Agent(ReflexA1Agent):
    """5-member weighted vote over rc02 + rc16 + rc82 + D13 + rc21."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self.tarjan_aps = _articulation_points(gameState.getWalls())
        except Exception:
            self.tarjan_aps = frozenset()
        try:
            self._rc82_hist = deque(maxlen=4)
        except Exception:
            pass
        self._rc44_turn = 0
        try:
            from zoo_reflex_rc21 import _layout_class
            self._rc21_class = _layout_class(gameState.getWalls())
        except Exception:
            self._rc21_class = "MEDIUM"

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
            "d13":  _safe_vote(ReflexA1D13Agent._chooseActionImpl),
            "rc21": _safe_vote(ReflexRC21Agent._chooseActionImpl),
        }
        tallies = defaultdict(float)
        for name, act in votes.items():
            if act is None:
                continue
            tallies[act] += RC102_WEIGHTS.get(name, 0.0)
        if not tallies:
            return Directions.STOP if Directions.STOP in legal else legal[0]

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
        if dt > RC102_TIME_BUDGET_WARN:
            try:
                print(f"[rc102] warn: turn took {dt:.3f}s")
            except Exception:
                pass
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC102Agent", second="ReflexRC102Agent"):
    return [ReflexRC102Agent(firstIndex), ReflexRC102Agent(secondIndex)]

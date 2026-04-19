# zoo_reflex_rc96.py
# ------------------
# rc96: rc94 (3-champion dense vote) + rc21 layout multiplier.
#
# rc94 is a dense equal-weight vote over rc02 + rc16 + rc82 (all
# 100% solo), reaching 95%. rc21 added a simple layout-class-based
# weight multiplier and got 95%. Stacking: the members of rc94
# each use rc21-multiplied weights.
#
# Since rc02 and rc16 both inherit from ReflexA1Agent, they share
# the _get_weights plumbing. By subclassing them with the
# _LayoutAwareMixin-style override, each vote is cast using
# layout-adjusted weights. rc82 already has state-conditioning
# inside rc44, so the layout multiplier stacks on its internal
# evaluations as well (since rc82's rc44 evaluates its members
# which all use A1's _get_weights).

from __future__ import annotations

import time
from collections import defaultdict

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from zoo_reflex_rc02 import ReflexRC02Agent, _articulation_points
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc21 import _layout_class, RC21_MULT_TABLE
from game import Directions


RC96_WEIGHTS = {"rc02": 1.0, "rc16": 1.0, "rc82": 1.0}
RC96_TIME_BUDGET_WARN = 0.80


class ReflexRC96Agent(ReflexA1Agent):
    """rc94 3-way vote + rc21 layout multiplier applied underneath."""

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
        try:
            self._rc96_class = _layout_class(gameState.getWalls())
        except Exception:
            self._rc96_class = "MEDIUM"

    def _get_weights(self):
        try:
            base = super()._get_weights()
        except Exception:
            return {}
        if not base:
            return base
        try:
            cls = getattr(self, "_rc96_class", "MEDIUM")
            role = TEAM.role.get(self.index, "OFFENSE")
            mult = RC21_MULT_TABLE.get(cls, {}).get(role, 1.0)
            if mult == 1.0:
                return base
            return {k: (v * mult) for k, v in base.items()}
        except Exception:
            return base

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
            tallies[act] += RC96_WEIGHTS.get(name, 0.0)
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
        if dt > RC96_TIME_BUDGET_WARN:
            try:
                print(f"[rc96] warn: turn took {dt:.3f}s")
            except Exception:
                pass
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC96Agent", second="ReflexRC96Agent"):
    return [ReflexRC96Agent(firstIndex), ReflexRC96Agent(secondIndex)]

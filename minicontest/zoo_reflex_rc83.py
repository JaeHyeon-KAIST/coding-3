# zoo_reflex_rc83.py
# ------------------
# rc83: 5-way multi-champion weighted ensemble.
#
# rc45 ensembled 4 members (A1 + rc02 + rc16 + D13). rc83 expands to
# 5 members using the best winners discovered through pm23/pm24:
#
#   A1   (0.825 baseline WR) — submission-grade reflex champion
#   rc02 (1.000) — Tarjan articulation-point defense
#   rc16 (1.000) — Voronoi territorial control
#   rc82 (1.000) — rc29+rc44 combo (tactical disruption + state stacking)
#   rc21 (0.950) — layout-class weight multiplier
#
# Each member casts its argmax. Winning action = argmax over
# sum_{member} weight_member * 1[member.vote == action]. Weights ≈
# empirical 40-game WR vs baseline; members failing (returning None
# or not-legal) contribute zero.
#
# Time budget: 5 argmax evaluations per turn. On defaultCapture each
# base is ~5-10ms, totalling ~30-50ms — well under 1 sec.

from __future__ import annotations

import time
from collections import defaultdict

from zoo_reflex_A1 import ReflexA1Agent
from zoo_reflex_rc02 import ReflexRC02Agent, _articulation_points
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc21 import ReflexRC21Agent
from game import Directions


RC83_WEIGHTS = {
    "a1":   0.825,
    "rc02": 1.000,
    "rc16": 1.000,
    "rc82": 1.000,
    "rc21": 0.950,
}

RC83_TIME_BUDGET_WARN = 0.80


class ReflexRC83Agent(ReflexA1Agent):
    """5-way weighted ensemble over A1 + rc02 + rc16 + rc82 + rc21."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self.tarjan_aps = _articulation_points(gameState.getWalls())
        except Exception:
            self.tarjan_aps = frozenset()
        # rc82 needs its own turn counter and history; inherit via MRO.
        try:
            from collections import deque
            self._rc82_hist = deque(maxlen=4)
        except Exception:
            pass
        self._rc44_turn = 0
        # rc21 layout class.
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
            "a1":   _safe_vote(ReflexA1Agent._chooseActionImpl),
            "rc02": _safe_vote(ReflexRC02Agent._chooseActionImpl),
            "rc16": _safe_vote(ReflexRC16Agent._chooseActionImpl),
            "rc82": _safe_vote(ReflexRC82Agent._chooseActionImpl),
            "rc21": _safe_vote(ReflexRC21Agent._chooseActionImpl),
        }

        tallies = defaultdict(float)
        for name, act in votes.items():
            if act is None:
                continue
            tallies[act] += RC83_WEIGHTS.get(name, 0.0)

        if not tallies:
            return Directions.STOP if Directions.STOP in legal else legal[0]

        chosen = max(tallies.items(), key=lambda kv: kv[1])[0]

        dt = time.time() - t0
        if dt > RC83_TIME_BUDGET_WARN:
            try:
                print(f"[rc83] warn: turn took {dt:.3f}s")
            except Exception:
                pass
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC83Agent", second="ReflexRC83Agent"):
    return [ReflexRC83Agent(firstIndex), ReflexRC83Agent(secondIndex)]

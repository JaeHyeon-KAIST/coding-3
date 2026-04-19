# zoo_reflex_rc109.py
# ------------------
# rc109: rc105 with rc29 REVERSE disruption layered on rc16 OFFENSE.
#
# rc105 = rc16 OFF + rc82 DEF. rc82 already has rc29 REVERSE layer
# built in. rc109 adds the same rc29 REVERSE layer to the rc16
# offense agent, creating symmetric tactical disruption.
#
# Implementation: subclass rc16 with the same history-tracked
# REVERSE injection as rc29 does on A1.

from __future__ import annotations

from collections import deque

from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_features import evaluate
from game import Directions, Actions


RC109_HIST_LEN = 4
RC109_SAME_DIR_MIN = 3
RC109_GHOST_TRIGGER = 4
RC109_TOP_K = 3
RC109_A1_TOL_FRAC = 0.05


def _reverse_of(action):
    try:
        if action is None or action == Directions.STOP:
            return None
        return Actions.reverseDirection(action)
    except Exception:
        return None


class ReflexRC109OffenseAgent(ReflexRC16Agent):
    """rc16 Voronoi + rc29-style REVERSE when herded by ghost."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc109_hist = deque(maxlen=RC109_HIST_LEN)

    def _should_reverse(self, gameState, legal):
        try:
            if not hasattr(self, "_rc109_hist"):
                self._rc109_hist = deque(maxlen=RC109_HIST_LEN)
            hist = list(self._rc109_hist)
            if len(hist) < RC109_SAME_DIR_MIN:
                return None
            last = hist[-RC109_SAME_DIR_MIN:]
            if any(a == Directions.STOP or a is None for a in last):
                return None
            if not all(a == last[0] for a in last):
                return None

            my_pos = gameState.getAgentPosition(self.index)
            my_state = gameState.getAgentState(self.index)
            if my_pos is None or not getattr(my_state, "isPacman", False):
                return None

            for opp_idx in self.getOpponents(gameState):
                try:
                    ost = gameState.getAgentState(opp_idx)
                    if getattr(ost, "isPacman", False):
                        continue
                    if int(getattr(ost, "scaredTimer", 0) or 0) > 0:
                        continue
                    opp_pos = gameState.getAgentPosition(opp_idx)
                    if opp_pos is None:
                        continue
                    d = self.getMazeDistance(my_pos, opp_pos)
                    if d <= RC109_GHOST_TRIGGER:
                        rev = _reverse_of(last[0])
                        if rev in legal:
                            return rev
                except Exception:
                    continue
            return None
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP
        try:
            base = super()._chooseActionImpl(gameState)
        except Exception:
            base = Directions.STOP

        try:
            disrupt = self._should_reverse(gameState, legal)
            chosen = base
            if disrupt is not None and disrupt in legal:
                weights = self._get_weights()
                scored = []
                for action in legal:
                    try:
                        s = evaluate(self, gameState, action, weights)
                    except Exception:
                        s = float("-inf")
                    scored.append((s, action))
                scored.sort(key=lambda sa: sa[0], reverse=True)
                top_score = scored[0][0]
                tol = max(abs(top_score) * RC109_A1_TOL_FRAC, 1.0)
                K = min(RC109_TOP_K, len(scored))
                candset = set(a for s, a in scored[:K] if s >= top_score - tol)
                if disrupt in candset:
                    chosen = disrupt
        except Exception:
            chosen = base

        try:
            if not hasattr(self, "_rc109_hist"):
                self._rc109_hist = deque(maxlen=RC109_HIST_LEN)
            self._rc109_hist.append(chosen)
        except Exception:
            pass
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="rc109-offense", second="rc109-defense"):
    """rc16+rc29 on OFFENSE, rc82 on DEFENSE."""
    return [ReflexRC109OffenseAgent(firstIndex),
            ReflexRC82Agent(secondIndex)]

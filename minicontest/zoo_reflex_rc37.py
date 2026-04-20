# zoo_reflex_rc37.py
# ------------------
# rc37: Novelty Search (anti-loop via position history).
#
# Reflex agents can get trapped in oscillation when two or more actions
# score identically and tie-break flips deterministically. rc37 adds a
# novelty bonus: actions leading to RECENTLY-VISITED cells are
# penalized by -α per repeat count in the last N-step history.
#
# Different from existing anti-loop logic (rc82's rc29 REVERSE under
# ghost threat): rc37 fires UNCONDITIONALLY whenever an action
# duplicates recent behavior, regardless of ghost presence.
#
# Tier 2 (J3 Novelty Search in rc-pool.md — simplified to inference-time
# position memory).

from __future__ import annotations

from collections import deque

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate, _ACTION_PREFERENCE
from game import Directions
from util import nearestPoint


RC37_HISTORY_LEN = 12
RC37_NOVELTY_PENALTY = 8.0  # per-repeat penalty on evaluate score


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC37Agent", second="ReflexRC37Agent"):
    return [ReflexRC37Agent(firstIndex), ReflexRC37Agent(secondIndex)]


class ReflexRC37Agent(ReflexA1Agent):
    """A1 + novelty bonus anti-loop."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc37_hist = deque(maxlen=RC37_HISTORY_LEN)

    def _successor_cell(self, gameState, action):
        try:
            succ = gameState.generateSuccessor(self.index, action)
            raw = succ.getAgentState(self.index).getPosition()
            if raw is None:
                return None
            sp = nearestPoint(raw)
            return (int(sp[0]), int(sp[1]))
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            weights = self._get_weights()

            try:
                ordered = sorted(
                    legal,
                    key=lambda a: (_ACTION_PREFERENCE.index(a)
                                   if a in _ACTION_PREFERENCE
                                   else len(_ACTION_PREFERENCE)),
                )
            except Exception:
                ordered = list(legal)

            best_score = float("-inf")
            best_action = None
            best_cell = None
            for action in ordered:
                try:
                    base = evaluate(self, gameState, action, weights)
                except Exception:
                    base = float("-inf")
                cell = self._successor_cell(gameState, action)
                repeats = 0
                if cell is not None and self._rc37_hist:
                    repeats = sum(1 for c in self._rc37_hist if c == cell)
                score = base - (RC37_NOVELTY_PENALTY * repeats)
                if score > best_score:
                    best_score = score
                    best_action = action
                    best_cell = cell

            if best_action is None or best_action not in legal:
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP

            if best_cell is not None:
                self._rc37_hist.append(best_cell)
            return best_action
        except Exception:
            try:
                return super()._chooseActionImpl(gameState)
            except Exception:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP

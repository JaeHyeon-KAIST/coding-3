# zoo_reflex_rc38.py
# ------------------
# rc38: MAP-Elites-lite inference-time diversity archive.
#
# MAP-Elites maintains an archive of DIFFERENT niche behaviors to
# prevent premature convergence. At inference time, we approximate:
# maintain a small archive of (state_bucket, action) pairs; for a new
# decision, pick the action that would occupy an under-represented
# niche, breaking ties by A1 argmax.
#
# State bucket: (my_is_pacman, ghost_close, carry_band∈{0,1-2,3+})
# → 2·2·3 = 12 niches. Each niche stores a visit count per action.
# The "exploration bonus" is inverse-proportional to visits.
#
# Tier 2 (J4 MAP-Elites).

from __future__ import annotations

from collections import defaultdict

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate, _ACTION_PREFERENCE
from zoo_core import TEAM
from game import Directions


RC38_EXPLORE_BONUS = 2.0  # score bonus inversely proportional to visits


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC38Agent", second="ReflexRC38Agent"):
    return [ReflexRC38Agent(firstIndex), ReflexRC38Agent(secondIndex)]


class ReflexRC38Agent(ReflexA1Agent):
    """A1 + MAP-Elites-style niche exploration bonus."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        # niche -> {action: visits}
        self._rc38_archive = defaultdict(lambda: defaultdict(int))

    def _niche(self, gameState):
        try:
            my_pos = gameState.getAgentPosition(self.index)
            my_state = gameState.getAgentState(self.index)
            is_pacman = 1 if getattr(my_state, "isPacman", False) else 0
            carry = int(getattr(my_state, "numCarrying", 0) or 0)
            carry_band = 0 if carry == 0 else (1 if carry <= 2 else 2)
            ghost_close = 0
            for opp in self.getOpponents(gameState):
                p = gameState.getAgentPosition(opp)
                if p is None or my_pos is None:
                    continue
                if self.getMazeDistance(my_pos, p) <= 4:
                    ghost_close = 1
                    break
            return (is_pacman, ghost_close, carry_band)
        except Exception:
            return (0, 0, 0)

    def _chooseActionImpl(self, gameState):
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            weights = self._get_weights()
            niche = self._niche(gameState)
            visits = self._rc38_archive[niche]

            try:
                ordered = sorted(
                    legal,
                    key=lambda a: (_ACTION_PREFERENCE.index(a)
                                   if a in _ACTION_PREFERENCE
                                   else len(_ACTION_PREFERENCE)),
                )
            except Exception:
                ordered = list(legal)

            best = float("-inf")
            best_a = None
            for a in ordered:
                try:
                    base = evaluate(self, gameState, a, weights)
                except Exception:
                    base = float("-inf")
                n = visits.get(a, 0)
                bonus = RC38_EXPLORE_BONUS / (1.0 + n)
                score = base + bonus
                if score > best:
                    best = score
                    best_a = a

            if best_a is None or best_a not in legal:
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            visits[best_a] += 1
            return best_a
        except Exception:
            try:
                return super()._chooseActionImpl(gameState)
            except Exception:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP

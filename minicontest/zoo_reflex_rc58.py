# zoo_reflex_rc58.py
# ------------------
# rc58: Factored Coord-Graph UCT lite (teammate spreading bonus).
#
# In multi-agent MCTS (coordination graphs), pairwise terms Q_ij(s, a_i,
# a_j) capture teammate dependencies that decompose poorly under pure
# individual Q_i. At inference time we approximate: estimate teammate's
# expected action (their A1 argmax), compute their projected position,
# then add a "spreading" bonus to MY action proportional to the
# post-action maze-distance between the two of us.
#
# Rationale: two Pacman agents clustering together is wasteful — one
# can't eat food the other is next to. Spreading bonus pushes agents
# apart to cover more ground, a coordination insight that the
# individual A1 evaluator doesn't capture.
#
# Tier 3 (H category: Factored MCTS / Coord-Graph UCT).

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate, _ACTION_PREFERENCE
from zoo_core import TEAM
from game import Directions
from util import nearestPoint


RC58_COORD_WEIGHT = 3.0  # bonus scaling; tune: too high → agents fly apart
RC58_MAX_BONUS = 15.0  # cap to prevent total score domination


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC58Agent", second="ReflexRC58Agent"):
    return [ReflexRC58Agent(firstIndex), ReflexRC58Agent(secondIndex)]


class ReflexRC58Agent(ReflexA1Agent):
    """A1 + pairwise teammate-spreading coordination bonus."""

    def _teammate_idx(self, gameState):
        try:
            team = sorted(list(self.getTeam(gameState)))
            mates = [i for i in team if i != self.index]
            return mates[0] if mates else None
        except Exception:
            return None

    def _project_teammate_cell(self, gameState, mate_idx):
        """Teammate's expected next cell = their A1 argmax successor."""
        try:
            mate_legal = gameState.getLegalActions(mate_idx)
        except Exception:
            return None
        if not mate_legal:
            return None
        weights = self._get_weights()
        best = float("-inf")
        best_a = None
        for a in mate_legal:
            try:
                s = evaluate(self, gameState, a, weights)
            except Exception:
                continue
            if s > best:
                best = s
                best_a = a
        if best_a is None:
            return None
        try:
            succ = gameState.generateSuccessor(mate_idx, best_a)
            raw = succ.getAgentState(mate_idx).getPosition()
            if raw is None:
                return gameState.getAgentPosition(mate_idx)
            sp = nearestPoint(raw)
            return (int(sp[0]), int(sp[1]))
        except Exception:
            return gameState.getAgentPosition(mate_idx)

    def _my_next_cell(self, gameState, action):
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
            mate_idx = self._teammate_idx(gameState)
            mate_cell = (self._project_teammate_cell(gameState, mate_idx)
                         if mate_idx is not None else None)

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
                bonus = 0.0
                if mate_cell is not None:
                    my_cell = self._my_next_cell(gameState, a)
                    if my_cell is not None:
                        try:
                            d = self.getMazeDistance(my_cell, mate_cell)
                            bonus = min(RC58_COORD_WEIGHT * d, RC58_MAX_BONUS)
                        except Exception:
                            bonus = 0.0
                score = base + bonus
                if score > best:
                    best = score
                    best_a = a

            if best_a is None or best_a not in legal:
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            return best_a
        except Exception:
            try:
                return super()._chooseActionImpl(gameState)
            except Exception:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP

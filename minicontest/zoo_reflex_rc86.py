# zoo_reflex_rc86.py
# ------------------
# rc86: rc82 (rc29 disruption + rc44 stacking) + rc48 (WHCA* teammate
# deconfliction) triple stack.
#
# rc82 is a tactical+strategic overlay over A1 (both 100% solo).
# rc48 is a 1-step teammate-collision filter (90% solo).
# They operate on orthogonal axes — rc82 picks WHAT action; rc48
# picks WHICH of the top-K candidates avoids the teammate's
# projected cell.
#
# Stacking logic:
#   1. rc82 runs its state-conditioned vote + REVERSE disruption →
#      produces a chosen action.
#   2. If rc48's reservation check says chosen action lands on
#      teammate's projected cell, swap to the highest-WR alternative
#      within A1's top-K that does NOT land there.
#   3. If no safe alternative, defer to rc82's choice (cannot do
#      better).

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_features import evaluate
from game import Directions, Actions
from util import nearestPoint


RC86_TOP_K = 4
RC86_A1_TOL_FRAC = 0.05

_RC86_LAST_ACTION: dict = {}


class ReflexRC86Agent(ReflexRC82Agent):
    """rc82 combo + 1-step teammate deconfliction."""

    def _teammate_projected_cell(self, gameState):
        try:
            my_team = sorted(list(self.getTeam(gameState)))
            mates = [i for i in my_team if i != self.index]
            if not mates:
                return None
            mate = mates[0]
            mate_pos = gameState.getAgentPosition(mate)
            if mate_pos is None:
                return None
            last_act = _RC86_LAST_ACTION.get(mate)
            if last_act is None or last_act == Directions.STOP:
                return mate_pos
            dx, dy = Actions.directionToVector(last_act)
            nx, ny = int(mate_pos[0] + dx), int(mate_pos[1] + dy)
            walls = gameState.getWalls()
            if 0 <= nx < walls.width and 0 <= ny < walls.height:
                if walls[nx][ny]:
                    return mate_pos
                return (nx, ny)
            return mate_pos
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)
        if not legal:
            chosen = Directions.STOP
            _RC86_LAST_ACTION[self.index] = chosen
            return chosen

        # Run rc82 first (which itself inherits rc44 + rc29).
        try:
            rc82_choice = super()._chooseActionImpl(gameState)
        except Exception:
            rc82_choice = Directions.STOP

        mate_cell = self._teammate_projected_cell(gameState)
        if mate_cell is None:
            _RC86_LAST_ACTION[self.index] = rc82_choice
            return rc82_choice

        # Would rc82's choice land on mate?
        try:
            succ = gameState.generateSuccessor(self.index, rc82_choice)
            raw = succ.getAgentState(self.index).getPosition()
            if raw is None:
                _RC86_LAST_ACTION[self.index] = rc82_choice
                return rc82_choice
            sp = nearestPoint(raw)
            sp = (int(sp[0]), int(sp[1]))
            if sp != mate_cell:
                # rc82's choice is safe; commit.
                _RC86_LAST_ACTION[self.index] = rc82_choice
                return rc82_choice
        except Exception:
            _RC86_LAST_ACTION[self.index] = rc82_choice
            return rc82_choice

        # rc82's choice collides — search A1 top-K for alternate.
        try:
            weights = self._get_weights()
            scored = []
            for action in legal:
                try:
                    s = evaluate(self, gameState, action, weights)
                except Exception:
                    s = float("-inf")
                scored.append((s, action))
            scored.sort(key=lambda sa: sa[0], reverse=True)
            if not scored or scored[0][0] == float("-inf"):
                _RC86_LAST_ACTION[self.index] = rc82_choice
                return rc82_choice

            top_score = scored[0][0]
            tol = max(abs(top_score) * RC86_A1_TOL_FRAC, 1.0)
            K = min(RC86_TOP_K, len(scored))
            for s, a in scored[:K]:
                if s < top_score - tol:
                    break
                if a == rc82_choice:
                    continue
                try:
                    succ = gameState.generateSuccessor(self.index, a)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw is None:
                        continue
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                    if sp != mate_cell:
                        _RC86_LAST_ACTION[self.index] = a
                        return a
                except Exception:
                    continue
        except Exception:
            pass

        # No alternative found — commit rc82's choice.
        _RC86_LAST_ACTION[self.index] = rc82_choice
        return rc82_choice


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC86Agent", second="ReflexRC86Agent"):
    return [ReflexRC86Agent(firstIndex), ReflexRC86Agent(secondIndex)]

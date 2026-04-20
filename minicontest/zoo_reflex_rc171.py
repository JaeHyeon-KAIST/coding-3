# zoo_reflex_rc171.py
# -------------------
# rc171: rc160 (score-switch rc82/rc16) + rc48 WHCA* teammate
# deconfliction overlay. rc86 showed rc82+rc48 = 95%+ (pm24); this
# tests whether the same stacking principle boosts rc160 (97.5% 200g
# solo).
#
# Stacking logic mirrors rc86:
#   1. rc160 picks chosen action (score-dependent rc82 or rc16).
#   2. If chosen action would land on teammate's projected cell,
#      search A1's top-K for an alternate that avoids collision.
#   3. If no alternate, commit rc160's choice.

from __future__ import annotations

from zoo_reflex_rc160 import ReflexRC160Agent
from zoo_features import evaluate
from game import Directions, Actions
from util import nearestPoint


RC171_TOP_K = 4
RC171_A1_TOL_FRAC = 0.05

_RC171_LAST_ACTION: dict = {}


class ReflexRC171Agent(ReflexRC160Agent):
    """rc160 score-switch + 1-step teammate deconfliction."""

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
            last_act = _RC171_LAST_ACTION.get(mate)
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
            _RC171_LAST_ACTION[self.index] = chosen
            return chosen

        # Run rc160 (score-switch → rc82 or rc16).
        try:
            rc160_choice = super()._chooseActionImpl(gameState)
        except Exception:
            rc160_choice = Directions.STOP

        mate_cell = self._teammate_projected_cell(gameState)
        if mate_cell is None:
            _RC171_LAST_ACTION[self.index] = rc160_choice
            return rc160_choice

        # Would rc160's choice land on mate?
        try:
            succ = gameState.generateSuccessor(self.index, rc160_choice)
            raw = succ.getAgentState(self.index).getPosition()
            if raw is None:
                _RC171_LAST_ACTION[self.index] = rc160_choice
                return rc160_choice
            sp = nearestPoint(raw)
            sp = (int(sp[0]), int(sp[1]))
            if sp != mate_cell:
                _RC171_LAST_ACTION[self.index] = rc160_choice
                return rc160_choice
        except Exception:
            _RC171_LAST_ACTION[self.index] = rc160_choice
            return rc160_choice

        # rc160 collides — try A1 top-K alternate.
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
                _RC171_LAST_ACTION[self.index] = rc160_choice
                return rc160_choice

            top_score = scored[0][0]
            tol = max(abs(top_score) * RC171_A1_TOL_FRAC, 1.0)
            K = min(RC171_TOP_K, len(scored))
            for s, a in scored[:K]:
                if s < top_score - tol:
                    break
                if a == rc160_choice:
                    continue
                try:
                    succ = gameState.generateSuccessor(self.index, a)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw is None:
                        continue
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                    if sp != mate_cell:
                        _RC171_LAST_ACTION[self.index] = a
                        return a
                except Exception:
                    continue
        except Exception:
            pass

        _RC171_LAST_ACTION[self.index] = rc160_choice
        return rc160_choice


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC171Agent", second="ReflexRC171Agent"):
    return [ReflexRC171Agent(firstIndex), ReflexRC171Agent(secondIndex)]

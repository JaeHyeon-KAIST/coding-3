# zoo_reflex_rc97.py
# ------------------
# rc97: rc90 (rc82 OFF + rc32 DEF role-asymmetric) + rc48 WHCA*
# teammate-deconfliction overlay.
#
# rc90 is our strongest asymmetric composition (97.5%). rc48 adds
# a 1-step reservation table to avoid teammate cell collisions
# (90% solo). Stacked: each role-specialized agent wraps its
# rc82/rc32 choice with an rc48-style collision filter.
#
# Implementation: subclass ReflexRC82Agent and ReflexRC32Agent with
# a mixin that performs the teammate-cell check post-hoc on the
# base class's chosen action.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc32 import ReflexRC32Agent
from zoo_features import evaluate
from game import Directions, Actions
from util import nearestPoint


RC97_TOP_K = 4
RC97_A1_TOL_FRAC = 0.05

_RC97_LAST_ACTION: dict = {}


class _RC97DeconflictMixin:
    """Mixin: wrap base class choice with 1-step teammate cell filter."""

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
            last_act = _RC97_LAST_ACTION.get(mate)
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
            _RC97_LAST_ACTION[self.index] = chosen
            return chosen

        try:
            base_choice = super()._chooseActionImpl(gameState)
        except Exception:
            base_choice = Directions.STOP

        mate_cell = self._teammate_projected_cell(gameState)
        if mate_cell is None:
            _RC97_LAST_ACTION[self.index] = base_choice
            return base_choice

        # Would base collide?
        try:
            succ = gameState.generateSuccessor(self.index, base_choice)
            raw = succ.getAgentState(self.index).getPosition()
            if raw is None:
                _RC97_LAST_ACTION[self.index] = base_choice
                return base_choice
            sp = nearestPoint(raw)
            sp = (int(sp[0]), int(sp[1]))
            if sp != mate_cell:
                _RC97_LAST_ACTION[self.index] = base_choice
                return base_choice
        except Exception:
            _RC97_LAST_ACTION[self.index] = base_choice
            return base_choice

        # Search top-K alternates.
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
                _RC97_LAST_ACTION[self.index] = base_choice
                return base_choice
            top_score = scored[0][0]
            tol = max(abs(top_score) * RC97_A1_TOL_FRAC, 1.0)
            K = min(RC97_TOP_K, len(scored))
            for s, a in scored[:K]:
                if s < top_score - tol:
                    break
                if a == base_choice:
                    continue
                try:
                    succ = gameState.generateSuccessor(self.index, a)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw is None:
                        continue
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                    if sp != mate_cell:
                        _RC97_LAST_ACTION[self.index] = a
                        return a
                except Exception:
                    continue
        except Exception:
            pass
        _RC97_LAST_ACTION[self.index] = base_choice
        return base_choice


class ReflexRC97OffenseAgent(_RC97DeconflictMixin, ReflexRC82Agent):
    """rc82 on OFFENSE + WHCA* deconflict."""


class ReflexRC97DefenseAgent(_RC97DeconflictMixin, ReflexRC32Agent):
    """rc32 on DEFENSE + WHCA* deconflict."""


def createTeam(firstIndex, secondIndex, isRed,
               first="rc97-offense", second="rc97-defense"):
    return [ReflexRC97OffenseAgent(firstIndex),
            ReflexRC97DefenseAgent(secondIndex)]

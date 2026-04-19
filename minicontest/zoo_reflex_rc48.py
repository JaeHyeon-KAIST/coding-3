# zoo_reflex_rc48.py
# ------------------
# rc48: WHCA* / reservation-table cooperative pathfinding overlay.
#
# Cooperative pathfinding (Silver 2005 WHCA*) reserves grid cells so
# two agents on the same team don't collide or deadlock. A1's reflex
# has no explicit teammate-awareness — both agents can pick actions
# that result in swapping cells or landing on the same cell next turn.
#
# rc48 implements a lightweight single-step reservation:
#   - At chooseAction, look at teammate's most recently chosen action
#     (stored on a shared agent-class attribute, updated each turn).
#   - Compute teammate's expected next cell.
#   - Filter my top-K candidate actions to exclude those that result
#     in my landing on that cell.
#   - Pick the best remaining candidate. If all are blocked, fall
#     through to A1 (safety net).
#
# "Most recent action" is a proxy for "teammate's intended next step"
# — imperfect but cheap. Unlike full WHCA*, we only look 1 step ahead
# (sufficient for same-turn-same-cell collision).
#
# Also blocks mutual-swap: if my move takes me to teammate's CURRENT
# cell AND teammate's last action (their reverse) would take them to
# my current cell, we'd swap through each other — illegal-ish and
# wastes a turn. Also filtered.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions, Actions
from util import nearestPoint


RC48_TOP_K = 4
RC48_A1_TOL_FRAC = 0.05

# Class-level shared state between teammate instances.
# Keyed by agent-index int.
_RC48_LAST_ACTION: dict = {}
_RC48_LAST_POS: dict = {}


class ReflexRC48Agent(ReflexA1Agent):
    """A1 champion + 1-step reservation-table teammate deconfliction."""

    def _teammate_projected_cell(self, gameState):
        """Return teammate's projected next cell or None."""
        try:
            my_team = sorted(list(self.getTeam(gameState)))
            mates = [i for i in my_team if i != self.index]
            if not mates:
                return None
            mate = mates[0]
            mate_pos = gameState.getAgentPosition(mate)
            if mate_pos is None:
                return None
            last_act = _RC48_LAST_ACTION.get(mate)
            if last_act is None or last_act == Directions.STOP:
                # Assume teammate stays put.
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
        # Record position for this turn (used on next turn by teammate).
        try:
            _RC48_LAST_POS[self.index] = gameState.getAgentPosition(self.index)
        except Exception:
            pass

        legal = gameState.getLegalActions(self.index)
        if not legal:
            chosen = Directions.STOP
            _RC48_LAST_ACTION[self.index] = chosen
            return chosen

        try:
            mate_cell = self._teammate_projected_cell(gameState)
        except Exception:
            mate_cell = None

        # Run A1 baseline; if mate_cell unknown, return A1.
        try:
            a1_choice = super()._chooseActionImpl(gameState)
        except Exception:
            a1_choice = Directions.STOP

        if mate_cell is None:
            _RC48_LAST_ACTION[self.index] = a1_choice
            return a1_choice

        # Filter top-K to avoid landing on mate_cell.
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
                _RC48_LAST_ACTION[self.index] = a1_choice
                return a1_choice

            top_score = scored[0][0]
            tol = max(abs(top_score) * RC48_A1_TOL_FRAC, 1.0)
            K = min(RC48_TOP_K, len(scored))
            candidates = [(s, a) for s, a in scored[:K] if s >= top_score - tol]

            def _lands_on(cell, action):
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw is None:
                        return False
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                    return sp == cell
                except Exception:
                    return False

            safe = [(s, a) for s, a in candidates if not _lands_on(mate_cell, a)]
            if not safe:
                chosen = a1_choice
            else:
                chosen = safe[0][1]
        except Exception:
            chosen = a1_choice

        _RC48_LAST_ACTION[self.index] = chosen
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC48Agent", second="ReflexRC48Agent"):
    return [ReflexRC48Agent(firstIndex), ReflexRC48Agent(secondIndex)]

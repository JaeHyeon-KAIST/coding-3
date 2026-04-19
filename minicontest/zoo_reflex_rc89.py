# zoo_reflex_rc89.py
# ------------------
# rc89: Dead-end avoidance overlay on A1 champion (Pacman side).
#
# A1's f_distToFood can lead Pacman into a food-holding dead-end
# even when a ghost is patrolling nearby. Once inside, there's no
# escape — the ghost blocks the single corridor exit. rc89 filters
# A1's top-K candidate actions to exclude any action that moves us
# INTO a dead-end cell when a non-scared ghost is within
# RC89_GHOST_TRIGGER cells.
#
# A "dead-end cell" is precomputed at init: any open cell with
# degree ≤ 1 in the 4-connected graph, extended along the single
# corridor until a branching point.
#
# Fire-conditions:
#   (a) I'm Pacman on enemy side,
#   (b) active ghost visible within RC89_GHOST_TRIGGER,
#   (c) A1's top candidate would lead into a flagged dead-end cell.
#
# If all top-K candidates are dead-ends (trapped already), defer
# to A1 — nothing better we can do.

from __future__ import annotations

from collections import deque

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions, Actions
from util import nearestPoint


RC89_TOP_K = 3
RC89_A1_TOL_FRAC = 0.05
RC89_GHOST_TRIGGER = 5


def _dead_end_cells(walls):
    """Return frozenset of cells in a dead-end corridor.
    A cell is a dead-end cell iff it has degree ≤ 1, OR its only
    non-dead-end neighbor is already dead-end-tagged (corridor
    extension).
    """
    try:
        W, H = walls.width, walls.height
    except Exception:
        return frozenset()

    def neighbors(p):
        x, y = p
        out = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not walls[nx][ny]:
                out.append((nx, ny))
        return out

    dead_ends = set()
    for x in range(W):
        for y in range(H):
            if walls[x][y]:
                continue
            if len(neighbors((x, y))) <= 1:
                dead_ends.add((x, y))

    # Propagate: a cell whose only non-dead-end neighbor count drops
    # to 1 also becomes dead-end. Iterate until fixpoint.
    changed = True
    while changed:
        changed = False
        for x in range(W):
            for y in range(H):
                if walls[x][y] or (x, y) in dead_ends:
                    continue
                nbrs = neighbors((x, y))
                non_de = [n for n in nbrs if n not in dead_ends]
                if len(non_de) <= 1:
                    dead_ends.add((x, y))
                    changed = True
    return frozenset(dead_ends)


class ReflexRC89Agent(ReflexA1Agent):
    """A1 champion + dead-end avoidance when ghost is close."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self._rc89_dead = _dead_end_cells(gameState.getWalls())
        except Exception:
            self._rc89_dead = frozenset()

    def _ghost_close(self, gameState):
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return False
            my_state = gameState.getAgentState(self.index)
            if not getattr(my_state, "isPacman", False):
                return False
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
                    if d <= RC89_GHOST_TRIGGER:
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def _chooseActionImpl(self, gameState):
        if not self._rc89_dead or not self._ghost_close(gameState):
            return super()._chooseActionImpl(gameState)

        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

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
                return super()._chooseActionImpl(gameState)

            top_score = scored[0][0]
            tol = max(abs(top_score) * RC89_A1_TOL_FRAC, 1.0)
            K = min(RC89_TOP_K, len(scored))
            candidates = [(s, a) for s, a in scored[:K] if s >= top_score - tol]
            if not candidates:
                return scored[0][1]

            # Prefer candidates whose successor cell is NOT a dead-end.
            non_dead = []
            for s, a in candidates:
                try:
                    succ = gameState.generateSuccessor(self.index, a)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw is None:
                        continue
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                    if sp not in self._rc89_dead:
                        non_dead.append((s, a))
                except Exception:
                    continue
            if non_dead:
                # Pick highest-scored non-dead-end.
                non_dead.sort(key=lambda sa: sa[0], reverse=True)
                return non_dead[0][1]
            # All dead-ends; defer to A1 (already trapped — no improvement).
            return scored[0][1]
        except Exception:
            return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC89Agent", second="ReflexRC89Agent"):
    return [ReflexRC89Agent(firstIndex), ReflexRC89Agent(secondIndex)]

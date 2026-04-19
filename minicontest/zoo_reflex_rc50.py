# zoo_reflex_rc50.py
# ------------------
# rc50: Opening-book overlay on A1 champion.
#
# Idea: the opening ~20 moves determine the agent's initial positioning
# on the maze. A1's reflex weights drive this through f_distToFood /
# f_onDefense, but without lookahead A1 can commit to a suboptimal
# food target (e.g. the nearest food in maze-distance is actually
# camped by the opposing defender).
#
# rc50 precomputes two strategic "approach targets" at init (well
# inside the 15s budget):
#   - offense_target: the food furthest from opponents' average home
#     column, i.e. the food whose capture is LEAST contested.
#   - defense_target: the articulation point closest to our food
#     cluster's centroid — the choke to hold.
#
# For the first RC50_BOOK_TURNS turns:
#   - OFFENSE agents are nudged toward offense_target (via top-K).
#   - DEFENSE agents are nudged toward defense_target.
#
# After the book expires, fall fully through to A1 forever.
#
# This addresses A1's "myopic opening" failure where it eats the
# nearest food first, then has to cross enemy defender lines to reach
# any subsequent food.

from __future__ import annotations

from collections import deque

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from zoo_reflex_rc02 import _articulation_points
from zoo_features import evaluate
from game import Directions
from util import nearestPoint


RC50_BOOK_TURNS = 15
RC50_TOP_K = 3
RC50_A1_TOL_FRAC = 0.05


def _bfs_distances(walls, start):
    """BFS from start over 4-connected non-wall cells.
    Returns dict cell -> int distance."""
    try:
        W, H = walls.width, walls.height
    except Exception:
        return {}
    if walls[start[0]][start[1]]:
        return {}
    dist = {start: 0}
    q = deque([start])
    while q:
        x, y = q.popleft()
        d = dist[(x, y)]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not walls[nx][ny]:
                if (nx, ny) not in dist:
                    dist[(nx, ny)] = d + 1
                    q.append((nx, ny))
    return dist


class ReflexRC50Agent(ReflexA1Agent):
    """A1 champion + 15-turn opening book with role-conditioned targets."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc50_turn = 0
        try:
            self._rc50_opening_target = self._compute_opening_target(gameState)
        except Exception:
            self._rc50_opening_target = None

    def _compute_opening_target(self, gameState):
        """Pick a single (cell) target based on our role.
        OFFENSE → best-uncontested food. DEFENSE → choke AP near food centroid."""
        try:
            role = getattr(self, "role", None) or TEAM.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"

        walls = gameState.getWalls()
        try:
            my_pos = gameState.getAgentPosition(self.index)
        except Exception:
            my_pos = None
        if my_pos is None:
            return None

        # Opponents' avg home column — approximate as the mean of their
        # init positions (available at register-time).
        opps = list(self.getOpponents(gameState))
        opp_cols = []
        for opp_idx in opps:
            try:
                p = gameState.getInitialAgentPosition(opp_idx)
                if p is not None:
                    opp_cols.append(p[0])
            except Exception:
                continue
        if not opp_cols:
            return None
        opp_col_mean = sum(opp_cols) / len(opp_cols)

        if role == "OFFENSE":
            # Find food on enemy side; pick the one furthest from
            # opp mean column (most uncontested on the *lateral* axis).
            try:
                food_list = list(self.getFood(gameState).asList())
            except Exception:
                food_list = []
            if not food_list:
                return None
            my_dists = _bfs_distances(walls, my_pos)
            best = None
            best_key = -1
            for f in food_list:
                lateral = abs(f[1] - _mean(opp_cols if False else [0]))  # unused now
                # Use (lateral distance from opp row-centroid) as tie-break.
                # Primary: maze-distance to us (closer is better).
                d_us = my_dists.get(f, None)
                if d_us is None:
                    continue
                # Score: prefer food with small d_us AND large horizontal
                # distance from opp home column (less contested).
                contest = abs(f[0] - opp_col_mean)
                key = contest - 0.5 * d_us
                if key > best_key:
                    best_key = key
                    best = f
            return best
        else:
            # DEFENSE: pick articulation point that lies closest to our
            # defended food's centroid.
            try:
                defended = list(self.getFoodYouAreDefending(gameState).asList())
            except Exception:
                defended = []
            if not defended:
                return None
            cx = sum(f[0] for f in defended) / len(defended)
            cy = sum(f[1] for f in defended) / len(defended)
            centroid = (int(round(cx)), int(round(cy)))
            aps = _articulation_points(walls)
            if not aps:
                return centroid
            # Prefer APs that are reasonably close to us AND the centroid.
            best = None
            best_score = float("inf")
            my_dists = _bfs_distances(walls, my_pos)
            for ap in aps:
                try:
                    d_mine = my_dists.get(ap, 9999)
                    d_cent = abs(ap[0] - centroid[0]) + abs(ap[1] - centroid[1])
                    score = d_mine + 1.5 * d_cent
                    if score < best_score:
                        best_score = score
                        best = ap
                except Exception:
                    continue
            return best or centroid

    def _chooseActionImpl(self, gameState):
        self._rc50_turn += 1
        target = getattr(self, "_rc50_opening_target", None)
        if target is None or self._rc50_turn > RC50_BOOK_TURNS:
            return super()._chooseActionImpl(gameState)

        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP
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
            tol = max(abs(top_score) * RC50_A1_TOL_FRAC, 1.0)
            K = min(RC50_TOP_K, len(scored))
            candidates = [a for s, a in scored[:K] if s >= top_score - tol]
            if len(candidates) < 2:
                return scored[0][1]

            best_action = candidates[0]
            best_dist = float("inf")
            for action in candidates:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw is None:
                        continue
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                    d = self.getMazeDistance(sp, target)
                    if d < best_dist:
                        best_dist = d
                        best_action = action
                except Exception:
                    continue
            return best_action
        except Exception:
            return super()._chooseActionImpl(gameState)


def _mean(xs):
    return sum(xs) / max(len(xs), 1)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC50Agent", second="ReflexRC50Agent"):
    return [ReflexRC50Agent(firstIndex), ReflexRC50Agent(secondIndex)]

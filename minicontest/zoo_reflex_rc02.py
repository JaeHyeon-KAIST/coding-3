# zoo_reflex_rc02.py
# ------------------
# rc02: Tarjan articulation-point defense overlay on A1 champion.
#
# zoo_core already computes an approximate "bottleneck" set by a cut-vertex
# remove-BFS heuristic. rc02 replaces/augments that with a proper
# **Tarjan iterative DFS** over the maze graph, computed once at
# registerInitialState (safely inside the 15s budget).
#
# Defense override engages only when:
#   (a) role = DEFENSE (from TEAM.role, same as A1),
#   (b) at least one visible invader (enemy Pacman on our side), and
#   (c) a useful articulation point exists that (i) lies on a roughly-
#       shortest path between the invader and our defended food, and
#       (ii) we can reach before the invader does.
#
# When engaged, the agent walks toward that AP. If already on it, the
# agent STOPs — holding the cut and preventing the invader from crossing.
#
# Everything else is pure ReflexA1Agent behavior. Any failure in the AP
# layer falls through to A1's argmax (crash-proof contract).
#
# Rationale (CCG: Gemini #1 + Codex):
#   Baseline and most student agents rely on shortest-path heuristics that
#   route through predictable maze bottlenecks. A defender that correctly
#   identifies the cut vertex between invader and food can shut down
#   food-eating even against fast 1-food-sprint strategies that A1's
#   reactive patrol weight misses.
#
# Expected uplift vs A1: +3 to +10pp on baseline (A1 ≈82% on this layout),
# larger against aggressive mono-offense opponents. Smoke-verifiable vs
# baseline; Phase 4 round-robin pool candidate.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from game import Directions


# Heuristic thresholds — chosen conservatively; tune after HTH if needed.
RC02_PATH_DETOUR_MAX = 3       # AP considered "on path" if extra distance ≤ this
RC02_RACE_MARGIN = 0            # must reach AP strictly before invader (≤ 0 margin)
RC02_CUT_SCORE_MIN = 0.05       # skip APs with minimal food-coverage gain


def _articulation_points(walls):
    """Tarjan's iterative DFS over the 4-connected maze graph.
    Returns frozenset of articulation-point cells.

    Iterative to avoid Python recursion limits on large layouts. Handles
    multiple connected components (each BFS/DFS seed checked).
    Complexity: O(V + E) for V open cells.
    """
    try:
        width, height = walls.width, walls.height
    except Exception:
        return frozenset()

    def neighbors(p):
        x, y = p
        out = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and not walls[nx][ny]:
                out.append((nx, ny))
        return out

    # Collect open cells.
    opens = []
    for x in range(width):
        for y in range(height):
            if not walls[x][y]:
                opens.append((x, y))
    if not opens:
        return frozenset()

    disc = {}     # discovery time
    low = {}      # lowlink
    parent = {}   # parent in DFS tree
    aps = set()
    timer = [0]

    for start in opens:
        if start in disc:
            continue

        parent[start] = None
        disc[start] = low[start] = timer[0]
        timer[0] += 1
        # Stack entries: [node, neighbors_list, next_index]
        stack = [[start, neighbors(start), 0]]
        root_children = 0

        while stack:
            u, nbs, i = stack[-1]
            if i < len(nbs):
                stack[-1][2] = i + 1
                v = nbs[i]
                if v == parent[u]:
                    continue
                if v in disc:
                    # Back-edge — update lowlink.
                    if disc[v] < low[u]:
                        low[u] = disc[v]
                else:
                    parent[v] = u
                    disc[v] = low[v] = timer[0]
                    timer[0] += 1
                    if u == start:
                        root_children += 1
                    stack.append([v, neighbors(v), 0])
            else:
                # Finished processing u — propagate lowlink to parent.
                stack.pop()
                if stack:
                    p = stack[-1][0]
                    if low[u] < low[p]:
                        low[p] = low[u]
                    # Non-root AP check.
                    if parent[p] is not None and low[u] >= disc[p]:
                        aps.add(p)

        # Root AP check: only AP if >= 2 DFS-tree children.
        if root_children > 1:
            aps.add(start)

    return frozenset(aps)


class ReflexRC02Agent(ReflexA1Agent):
    """A1 champion + Tarjan AP defense override."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            walls = gameState.getWalls()
            self.tarjan_aps = _articulation_points(walls)
        except Exception:
            self.tarjan_aps = frozenset()

    # ---------------- AP selection ------------------------------------

    def _find_blocking_ap(self, gameState, snap):
        """Identify AP that cuts invader from our food. Returns cell or None."""
        try:
            my_pos = snap.get("myPos")
            if my_pos is None or not self.tarjan_aps:
                return None

            # Find the nearest visible invader.
            invader_pos = None
            invader_dist = float("inf")
            for opp_idx, opp_pos in (snap.get("opponentPositions") or {}).items():
                if opp_pos is None:
                    continue
                try:
                    opp_state = gameState.getAgentState(opp_idx)
                    if not getattr(opp_state, "isPacman", False):
                        continue
                    d = self.getMazeDistance(my_pos, opp_pos)
                    if d < invader_dist:
                        invader_dist = d
                        invader_pos = opp_pos
                except Exception:
                    continue
            if invader_pos is None:
                return None

            try:
                defend_food = self.getFoodYouAreDefending(gameState).asList()
            except Exception:
                defend_food = []
            if not defend_food:
                return None

            # Direct invader → nearest-food distance (reference).
            d_inv_food_min = min(
                self.getMazeDistance(invader_pos, f) for f in defend_food
            )

            best_ap = None
            best_score = float("-inf")
            for ap in self.tarjan_aps:
                try:
                    d_inv_ap = self.getMazeDistance(invader_pos, ap)
                    d_ap_food_min = min(
                        self.getMazeDistance(ap, f) for f in defend_food
                    )
                    # "On-path" check via triangle-inequality slack.
                    detour = (d_inv_ap + d_ap_food_min) - d_inv_food_min
                    if detour > RC02_PATH_DETOUR_MAX:
                        continue
                    # Must reach the AP before invader.
                    d_me_ap = self.getMazeDistance(my_pos, ap)
                    if d_me_ap > d_inv_ap + RC02_RACE_MARGIN:
                        continue
                    # Cut score: food this AP plausibly blocks, weighted by
                    # proximity (threat-weighted coverage).
                    cut = 0.0
                    for f in defend_food:
                        d_inv_f = self.getMazeDistance(invader_pos, f)
                        d_via_ap = d_inv_ap + self.getMazeDistance(ap, f)
                        if d_via_ap <= d_inv_f + RC02_PATH_DETOUR_MAX:
                            cut += 1.0 / max(d_inv_f, 1)
                    if cut < RC02_CUT_SCORE_MIN:
                        continue
                    # Prefer high cut-score and nearby APs.
                    score = cut - 0.05 * d_me_ap
                    if score > best_score:
                        best_score = score
                        best_ap = ap
                except Exception:
                    continue
            return best_ap
        except Exception:
            return None

    # ---------------- action computation ------------------------------

    def _move_toward_or_hold(self, gameState, target):
        """Return legal action moving toward `target`, or STOP if already
        on it (preferred). None if no useful action found."""
        try:
            from util import nearestPoint
            my_pos = gameState.getAgentPosition(self.index)
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return None
            if my_pos == target:
                if Directions.STOP in legal:
                    return Directions.STOP
                # Otherwise fall through to "best adjacent" pick.

            best_action = None
            best_dist = float("inf")
            for action in legal:
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
            return None

    # ---------------- main override ------------------------------------

    def _chooseActionImpl(self, gameState):
        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"
        if role != "DEFENSE":
            return super()._chooseActionImpl(gameState)

        try:
            snap = self.snapshot(gameState)
        except Exception:
            return super()._chooseActionImpl(gameState)

        try:
            target = self._find_blocking_ap(gameState, snap)
        except Exception:
            target = None
        if target is None:
            return super()._chooseActionImpl(gameState)

        try:
            action = self._move_toward_or_hold(gameState, target)
        except Exception:
            action = None
        if action is None:
            return super()._chooseActionImpl(gameState)
        return action


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC02Agent", second="ReflexRC02Agent"):
    return [ReflexRC02Agent(firstIndex), ReflexRC02Agent(secondIndex)]

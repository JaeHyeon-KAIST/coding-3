# zoo_reflex_rc03.py
# ------------------
# rc03: Dead-end trap defense overlay on A1 champion.
#
# zoo_core already precomputes `self.deadEnds` — a frozenset of all cells
# that sit on a length ≥ 3 single-exit corridor. rc03 builds on top of that
# by also computing the chain-to-neck mapping: for each dead-end cell, the
# single "neck" cell that connects the chain to the rest of the maze.
#
# Trap logic (engages when non-scared, on home side):
#   If any visible enemy Pacman is currently inside one of our dead-end
#   chains AND we can reach the chain's neck before they can, move toward
#   that neck (or STOP if already there). Since a dead-end has only one
#   exit, sealing the neck guarantees the invader cannot escape without
#   crossing us — a free kill on contact.
#
# Rationale (Gemini #2): opposing Pacmen routinely route through dead-ends
# (e.g. isolated food clusters). Baseline and naive agents don't leverage
# the graph structure to guarantee captures. rc03 converts a purely
# structural observation into a 100%-kill opportunity.
#
# Why a separate agent (not merged into rc02 AP defense): dead-end traps
# and AP cuts fire on different sub-structures and at different thresholds.
# Keeping them separate gives Phase 4 tournament measurement of each layer
# independently before composing.
#
# Any failure in the trap layer falls through to A1 argmax (crash-proof).

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from game import Directions


class ReflexRC03Agent(ReflexA1Agent):
    """A1 champion + dead-end neck trap."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self.dead_end_neck = self._build_dead_end_necks(gameState)
        except Exception:
            self.dead_end_neck = {}

    # ---------------- precompute ---------------------------------------

    def _build_dead_end_necks(self, gameState):
        """For every cell c in self.deadEnds, return necks[c] = neck cell
        (the single junction-side exit of c's dead-end chain). Returns
        dict[(x,y)] -> (x,y). Empty on failure."""
        try:
            de_set = self.deadEnds if self.deadEnds else frozenset()
            if not de_set:
                return {}
            walls = gameState.getWalls()
            W, H = walls.width, walls.height

            def nbrs(p):
                x, y = p
                out = []
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and not walls[nx][ny]:
                        out.append((nx, ny))
                return out

            necks = {}
            seen = set()
            for start in de_set:
                if start in seen:
                    continue
                # BFS across dead-end cells to build one chain component.
                frontier = [start]
                comp = {start}
                seen.add(start)
                while frontier:
                    nxt = []
                    for c in frontier:
                        for n in nbrs(c):
                            if n in de_set and n not in seen:
                                seen.add(n)
                                comp.add(n)
                                nxt.append(n)
                    frontier = nxt
                # Collect the chain's neighbors that lie OUTSIDE the chain —
                # those are candidate neck cells (usually exactly one).
                neck_candidates = set()
                for c in comp:
                    for n in nbrs(c):
                        if n not in de_set:
                            neck_candidates.add(n)
                if not neck_candidates:
                    continue  # Orphan component (no neck) — skip.
                # If there are multiple candidates (e.g. branched chains that
                # our dead-end heuristic missed), any one of them works as a
                # partial seal. Pick deterministically.
                neck = min(neck_candidates)
                for c in comp:
                    necks[c] = neck
            return necks
        except Exception:
            return {}

    # ---------------- trap selection -----------------------------------

    def _find_trap_target(self, gameState, snap):
        """Return neck cell to occupy, or None if no trap available."""
        try:
            my_pos = snap.get("myPos")
            if my_pos is None or not self.dead_end_neck:
                return None
            # Must be non-Pacman (i.e. a ghost on our side) and not scared
            # to execute the kill.
            if snap.get("isPacman"):
                return None
            if int(snap.get("scaredTimer", 0) or 0) > 0:
                return None

            best_neck = None
            best_margin = float("-inf")
            for opp_idx, opp_pos in (snap.get("opponentPositions") or {}).items():
                if opp_pos is None:
                    continue
                try:
                    opp_state = gameState.getAgentState(opp_idx)
                    if not getattr(opp_state, "isPacman", False):
                        continue
                    opp_int = (int(opp_pos[0]), int(opp_pos[1]))
                    neck = self.dead_end_neck.get(opp_int)
                    if neck is None:
                        continue
                    d_me = self.getMazeDistance(my_pos, neck)
                    d_inv = self.getMazeDistance(opp_int, neck)
                    # We must reach the neck no later than the invader.
                    margin = d_inv - d_me
                    if margin < 0:
                        continue
                    # Prefer the trap with the largest time margin (safer).
                    if margin > best_margin:
                        best_margin = margin
                        best_neck = neck
                except Exception:
                    continue
            return best_neck
        except Exception:
            return None

    # ---------------- action computation -------------------------------

    def _move_toward_or_hold(self, gameState, target):
        """Return a legal action moving toward `target`. STOP if already
        on it. None if nothing helpful can be computed."""
        try:
            from util import nearestPoint
            my_pos = gameState.getAgentPosition(self.index)
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return None
            if my_pos == target and Directions.STOP in legal:
                return Directions.STOP

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
            snap = self.snapshot(gameState)
        except Exception:
            return super()._chooseActionImpl(gameState)

        try:
            target = self._find_trap_target(gameState, snap)
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
               first="ReflexRC03Agent", second="ReflexRC03Agent"):
    return [ReflexRC03Agent(firstIndex), ReflexRC03Agent(secondIndex)]

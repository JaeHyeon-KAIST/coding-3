# zoo_reflex_rc28.py
# ------------------
# rc28: Boids-style swarm cohesion overlay on A1 champion.
#
# Team-coordination heuristic borrowed from flocking rules:
#   - Separation: don't cluster on the same square as our teammate.
#   - Alignment: when both on home territory patrolling, prefer to face
#     opposite directions so we cover different approaches.
#   - Cohesion: when both on offense far from home, keep within a
#     "support radius" so either of us can bail the other out.
#
# rc28 implements a simplified version: when no invader is visible and
# we're both on home side, a softer "anti-clump" pressure nudges us to
# the top-K A1 action that maximizes distance to teammate. Prevents the
# common A1 failure mode where both defenders converge on the same
# patrol cell (f_invaderDist aligns them).
#
# Fire-conditions (all must hold):
#   (a) no visible invader (f_invaderDist signal absent),
#   (b) both our agents are in known positions,
#   (c) teammate distance ≤ RC28_CLUMP_DIST,
#   (d) multiple near-tied legal actions exist in A1's top-K.
#
# Within top-K with A1 tolerance, pick the action that MAXIMIZES maze
# distance from the teammate's current cell. Falls through to A1 on any
# exception or when no overlap.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions
from util import nearestPoint


RC28_TOP_K = 3
RC28_A1_TOL_FRAC = 0.05
RC28_CLUMP_DIST = 4   # only intervene when teammates are within this maze distance


class ReflexRC28Agent(ReflexA1Agent):
    """A1 champion + Boids-style anti-clumping separation overlay."""

    def _boids_should_fire(self, gameState):
        """Return teammate_pos iff overlay should engage, else None."""
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return None

            # No visible invaders.
            for opp_idx in self.getOpponents(gameState):
                try:
                    opp_state = gameState.getAgentState(opp_idx)
                    if getattr(opp_state, "isPacman", False):
                        opp_pos = gameState.getAgentPosition(opp_idx)
                        if opp_pos is not None:
                            return None
                except Exception:
                    continue

            # Teammate position known + close.
            my_team = sorted(list(self.getTeam(gameState)))
            mates = [i for i in my_team if i != self.index]
            if not mates:
                return None
            try:
                mate_pos = gameState.getAgentPosition(mates[0])
            except Exception:
                mate_pos = None
            if mate_pos is None:
                return None

            try:
                d = self.getMazeDistance(my_pos, mate_pos)
            except Exception:
                return None
            if d > RC28_CLUMP_DIST:
                return None

            # Both on home side (ghost mode).
            try:
                my_state = gameState.getAgentState(self.index)
                if getattr(my_state, "isPacman", False):
                    return None
                mate_state = gameState.getAgentState(mates[0])
                if getattr(mate_state, "isPacman", False):
                    return None
            except Exception:
                return None

            return mate_pos
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        try:
            mate_pos = self._boids_should_fire(gameState)
        except Exception:
            mate_pos = None
        if mate_pos is None:
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
            tol = max(abs(top_score) * RC28_A1_TOL_FRAC, 1.0)
            K = min(RC28_TOP_K, len(scored))
            candidates = [a for s, a in scored[:K] if s >= top_score - tol]
            if len(candidates) < 2:
                return scored[0][1]

            # Pick candidate that MAXIMIZES distance to teammate.
            best_action = candidates[0]
            best_sep = -1
            for action in candidates:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw is None:
                        continue
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                    d = self.getMazeDistance(sp, mate_pos)
                    if d > best_sep:
                        best_sep = d
                        best_action = action
                except Exception:
                    continue
            return best_action
        except Exception:
            return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC28Agent", second="ReflexRC28Agent"):
    return [ReflexRC28Agent(firstIndex), ReflexRC28Agent(secondIndex)]

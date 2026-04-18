# zoo_reflex_rc08.py
# ------------------
# rc08: Dynamic lane / invader assignment overlay on A1 champion.
#
# Problem: when both enemy Pacmen invade simultaneously, A1's f_invaderDist
# pulls each of our defenders toward the NEAREST invader — which can be
# the SAME invader. One enemy gets double-covered, the other walks free.
#
# Solution (Gemini #6 variant): 2-agent, 2-invader min-cost assignment.
# Each of our agents is paired with one invader so total chase distance
# is minimized. The assigned defender is nudged (within A1's top-K) toward
# its paired invader.
#
# Engages only when:
#   (a) at least 2 visible invaders — single-invader case is trivially
#       handled by A1's existing invader-chase weight,
#   (b) both our agents have a known position,
#   (c) a non-trivial swap exists (i.e. the greedy-nearest assignment
#       would double-cover one invader).
#
# Like rc04 and rc06, the override is restricted to A1's top-K actions
# with a tolerance band, so ghost-safety and patrol semantics remain
# exactly as A1 trained them.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions


RC08_TOP_K = 3
RC08_A1_TOL_FRAC = 0.05


class ReflexRC08Agent(ReflexA1Agent):
    """A1 champion + invader-lane dual-coverage overlay."""

    def _lane_assignment_target(self, gameState):
        """Return the invader position I should chase iff (a) 2+ invaders
        are visible, (b) both our agents have positions, and (c) the min-
        cost assignment swaps away from the greedy-nearest duplicate."""
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return None

            my_team = sorted(list(self.getTeam(gameState)))
            teammates = [i for i in my_team if i != self.index]
            if not teammates:
                return None
            mate = teammates[0]
            try:
                mate_pos = gameState.getAgentPosition(mate)
            except Exception:
                mate_pos = None
            if mate_pos is None:
                return None

            invaders = []
            for opp_idx in self.getOpponents(gameState):
                try:
                    p = gameState.getAgentPosition(opp_idx)
                    if p is None:
                        continue
                    st = gameState.getAgentState(opp_idx)
                    if getattr(st, "isPacman", False):
                        invaders.append(p)
                except Exception:
                    continue
            if len(invaders) < 2:
                return None

            # 2 agents × 2 invaders: only 2 assignments possible.
            a_inv, b_inv = invaders[0], invaders[1]
            c_me_a = self.getMazeDistance(my_pos, a_inv)
            c_me_b = self.getMazeDistance(my_pos, b_inv)
            c_mate_a = self.getMazeDistance(mate_pos, a_inv)
            c_mate_b = self.getMazeDistance(mate_pos, b_inv)

            opt1 = c_me_a + c_mate_b
            opt2 = c_me_b + c_mate_a
            if opt1 <= opt2:
                my_target = a_inv
                # Greedy (both chase nearest): check whether both agents
                # would have chosen the SAME invader under greedy-nearest.
                greedy_me = a_inv if c_me_a <= c_me_b else b_inv
                greedy_mate = a_inv if c_mate_a <= c_mate_b else b_inv
                if greedy_me == greedy_mate:
                    # Duplicate chase — intervene.
                    return my_target
                # No duplication: A1 already handles via f_invaderDist.
                return None
            else:
                my_target = b_inv
                greedy_me = a_inv if c_me_a <= c_me_b else b_inv
                greedy_mate = a_inv if c_mate_a <= c_mate_b else b_inv
                if greedy_me == greedy_mate:
                    return my_target
                return None
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        try:
            target = self._lane_assignment_target(gameState)
        except Exception:
            target = None
        if target is None:
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
            tol = max(abs(top_score) * RC08_A1_TOL_FRAC, 1.0)
            K = min(RC08_TOP_K, len(scored))
            candidates = [a for s, a in scored[:K]
                          if s >= top_score - tol]
            if len(candidates) < 2:
                return scored[0][1]

            from util import nearestPoint
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


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC08Agent", second="ReflexRC08Agent"):
    return [ReflexRC08Agent(firstIndex), ReflexRC08Agent(secondIndex)]

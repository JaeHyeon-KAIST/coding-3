# zoo_reflex_rc04.py
# ------------------
# rc04: Hungarian-style task allocation overlay on A1 champion.
#
# Problem: the two offense Pacmen can converge on the same food cluster
# ("dogpiling"), halving effective food-eating throughput. A1's evolved
# `f_teammateSpread` weight nudges dispersion softly, but it still breaks
# down when both agents prefer the same greedy-nearest target.
#
# Solution (Codex, conflict-only): detect the dogpile case (both offense
# agents share greedy-nearest food). Only when the conflict actually
# exists, the FARTHER agent is reassigned to its 2nd-nearest food. Within
# A1's top-K actions (so we never override ghost-safety), the farther
# agent is nudged toward its new assignment. If no conflict exists, A1 is
# untouched — its evolved weights already handle coverage.
#
# Why only conflict-triggered: an earlier draft applied the override on
# every turn and destroyed performance by re-ranking A1's legitimate best
# action when the assignment disagreed with it. The rule of thumb is:
# A1 knows the safe action; only use the assignment to break dogpiles.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions


RC04_TOP_K = 3            # only re-rank within A1's K best actions
RC04_A1_TOL_FRAC = 0.05   # override only if A1 top gap < 5% of |top_score|


class ReflexRC04Agent(ReflexA1Agent):
    """A1 champion + dogpile-breaking food assignment overlay."""

    def _conflict_override_target(self, gameState):
        """Return a target food iff (a) my teammate and I share greedy-
        nearest food and (b) I am the farther of the two. Else None."""
        try:
            my_team = sorted(list(self.getTeam(gameState)))
            offense = []
            for idx in my_team:
                try:
                    role = TEAM.role.get(idx, "OFFENSE")
                except Exception:
                    role = "OFFENSE"
                if role == "OFFENSE":
                    offense.append(idx)
            if len(offense) < 2 or self.index not in offense:
                return None

            food_list = list(self.getFood(gameState).asList())
            if len(food_list) < 2:
                return None

            mate = [i for i in offense if i != self.index][0]
            try:
                my_pos = gameState.getAgentPosition(self.index)
                mate_pos = gameState.getAgentPosition(mate)
            except Exception:
                return None
            if my_pos is None or mate_pos is None:
                return None

            my_near = min(food_list,
                          key=lambda f: self.getMazeDistance(my_pos, f))
            mate_near = min(food_list,
                            key=lambda f: self.getMazeDistance(mate_pos, f))
            if my_near != mate_near:
                return None  # no conflict, no override

            d_me = self.getMazeDistance(my_pos, my_near)
            d_mate = self.getMazeDistance(mate_pos, mate_near)
            # Tie-break by agent index for determinism.
            if (d_me, self.index) <= (d_mate, mate):
                return None  # I keep the primary target; teammate re-routes

            # I am farther — pick my 2nd-nearest food.
            ranked = sorted(food_list,
                            key=lambda f: self.getMazeDistance(my_pos, f))
            if len(ranked) < 2:
                return None
            return ranked[1]
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        # Only intervene in OFFENSE role.
        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"
        if role != "OFFENSE":
            return super()._chooseActionImpl(gameState)

        try:
            target = self._conflict_override_target(gameState)
        except Exception:
            target = None
        if target is None:
            return super()._chooseActionImpl(gameState)

        # Score legal actions with A1's weights. Only re-rank if the top-K
        # are close to each other (A1 is "near-indifferent").
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

            if not scored:
                return super()._chooseActionImpl(gameState)

            top_score = scored[0][0]
            # If A1 top-1 is -inf, fall back.
            if top_score == float("-inf"):
                return super()._chooseActionImpl(gameState)

            tol = max(abs(top_score) * RC04_A1_TOL_FRAC, 1.0)
            K = min(RC04_TOP_K, len(scored))
            candidates = [a for s, a in scored[:K]
                          if s >= top_score - tol]
            if len(candidates) < 2:
                # A1 has a clear winner — do not override.
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
               first="ReflexRC04Agent", second="ReflexRC04Agent"):
    return [ReflexRC04Agent(firstIndex), ReflexRC04Agent(secondIndex)]

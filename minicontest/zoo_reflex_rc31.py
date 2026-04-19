# zoo_reflex_rc31.py
# ------------------
# rc31: Aggro-juggling / kiting overlay on A1 champion.
#
# "Kiting" in MOBA / tower-defense terms: a defender who has a small
# speed advantage oscillates 1 step toward / 1 step away from an
# attacker, baiting the attacker to commit forward moves while the
# defender keeps distance and chains attacks.
#
# Applied to Capture-the-Flag:
#   - When we are a non-scared ghost,
#   - and exactly one visible invader is at maze distance d ∈ [2,3],
#   - and our teammate is NOT already between the invader and their home
#     (we don't want to hand-off — we want to juggle),
#   - then we deliberately hold distance 2 rather than closing to 1.
#
# The kiting step is the top-K A1 action whose resulting cell has maze
# distance EXACTLY 2 from the invader (or the closest value to 2). If
# no such candidate exists, we fall through to A1's choice.
#
# Why this helps: A1's f_invaderDist pulls us toward distance 0, which
# is a kill state — but also invites swap-suicide from the invader's
# teammate. Kite-distance-2 keeps us positioned to kill on their move
# forward while avoiding self-sacrifice.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions
from util import nearestPoint


RC31_TOP_K = 3
RC31_A1_TOL_FRAC = 0.05
RC31_KITE_DIST = 2          # ideal maze distance to invader while kiting
RC31_ENGAGE_MIN = 2
RC31_ENGAGE_MAX = 3


class ReflexRC31Agent(ReflexA1Agent):
    """A1 champion + kite-distance-2 aggro-juggling against single invader."""

    def _kite_target_invader(self, gameState):
        """Return invader position to juggle iff overlay should fire, else None."""
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return None
            my_state = gameState.getAgentState(self.index)
            # Must be non-scared ghost.
            if getattr(my_state, "isPacman", False):
                return None
            if int(getattr(my_state, "scaredTimer", 0) or 0) > 0:
                return None

            # Exactly one visible invader.
            invaders = []
            for opp_idx in self.getOpponents(gameState):
                try:
                    ost = gameState.getAgentState(opp_idx)
                    if not getattr(ost, "isPacman", False):
                        continue
                    p = gameState.getAgentPosition(opp_idx)
                    if p is None:
                        continue
                    invaders.append(p)
                except Exception:
                    continue
            if len(invaders) != 1:
                return None
            inv_pos = invaders[0]

            # Engagement range.
            d = self.getMazeDistance(my_pos, inv_pos)
            if d < RC31_ENGAGE_MIN or d > RC31_ENGAGE_MAX:
                return None

            # Teammate NOT already between invader and home.
            my_team = sorted(list(self.getTeam(gameState)))
            mates = [i for i in my_team if i != self.index]
            if mates:
                try:
                    mate_pos = gameState.getAgentPosition(mates[0])
                except Exception:
                    mate_pos = None
                if mate_pos is not None:
                    # Crude: if teammate is closer to invader than us AND
                    # teammate is between us and invader, they can handle it.
                    try:
                        mate_d = self.getMazeDistance(mate_pos, inv_pos)
                        if mate_d < d:
                            return None
                    except Exception:
                        pass

            return inv_pos
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        try:
            inv_pos = self._kite_target_invader(gameState)
        except Exception:
            inv_pos = None
        if inv_pos is None:
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
            tol = max(abs(top_score) * RC31_A1_TOL_FRAC, 1.0)
            K = min(RC31_TOP_K, len(scored))
            candidates = [a for s, a in scored[:K] if s >= top_score - tol]
            if len(candidates) < 2:
                return scored[0][1]

            # Pick action whose successor-distance to invader is CLOSEST TO 2.
            best_action = candidates[0]
            best_gap = float("inf")
            for action in candidates:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw is None:
                        continue
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                    d = self.getMazeDistance(sp, inv_pos)
                    gap = abs(d - RC31_KITE_DIST)
                    if gap < best_gap:
                        best_gap = gap
                        best_action = action
                except Exception:
                    continue
            return best_action
        except Exception:
            return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC31Agent", second="ReflexRC31Agent"):
    return [ReflexRC31Agent(firstIndex), ReflexRC31Agent(secondIndex)]

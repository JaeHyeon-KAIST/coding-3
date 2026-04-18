# zoo_reflex_rc17.py
# ------------------
# rc17: Influence-map overlay on A1 champion.
#
# Idea: every threat and opportunity on the board radiates a decaying
# field. Food and capsules radiate POSITIVE influence; active enemy
# ghosts radiate NEGATIVE influence. Our agent prefers successors that
# sit on high net-influence cells — a smoother signal than hand-picking
# "nearest food" or "nearest ghost" individually, which is what A1's
# `f_distToFood` and `f_ghostDist1` do as scalar distances.
#
# Computational approximation: instead of Gaussian-blurring the full
# W×H grid per turn (O(W·H·sources) — too slow), we evaluate the
# influence directly at each candidate successor position. That shrinks
# it to O(actions · sources) ≈ 5 × 30 ≈ 150 ops per turn. Safely
# under the 1-sec budget.
#
# Influence formula at position p:
#   +w_food     · Σ_f 1/(d(p,f)+1)²
#   +w_capsule  · Σ_c 1/(d(p,c)+1)²
#   -w_ghost    · Σ_g 1/(d(p,g)+1)²   (g = active non-scared enemy ghost)
#   +w_scared   · Σ_s 1/(d(p,s)+1)²   (s = scared enemy ghost — kill bonus)
#
# The squared inverse gives a steeper field than A1's 1/dist, amplifying
# near-field pulls (where tactical decisions matter) and damping far-
# field contributions (which A1's successor-score already handles).
#
# Added as a single new feature `f_influenceMap` with hand-tuned
# positive weight. A1's 20 evolved weights stay exactly as-is.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import extract_features as _base_extract_features
from game import Directions


# Influence components.
RC17_W_FOOD = 1.0
RC17_W_CAPSULE = 1.5
RC17_W_GHOST = 3.0   # negative weight (sign applied at aggregation)
RC17_W_SCARED = 2.0

# Feature weight (added on top of weighted sum of A1 features).
RC17_F_WEIGHT = 20.0


def _influence_at(agent, pos, successor):
    """Signed influence at `pos` from food, capsules, and enemy ghosts.
    Squared-inverse falloff. Errors → 0.0."""
    try:
        total = 0.0

        # Food pulls.
        try:
            foods = list(agent.getFood(successor).asList())
            for f in foods:
                d = agent.getMazeDistance(pos, f)
                total += RC17_W_FOOD / ((d + 1) * (d + 1))
        except Exception:
            pass

        # Capsule pulls (stronger per-source than food).
        try:
            caps = list(agent.getCapsules(successor))
            for c in caps:
                d = agent.getMazeDistance(pos, c)
                total += RC17_W_CAPSULE / ((d + 1) * (d + 1))
        except Exception:
            pass

        # Active enemy ghosts — repel.
        # Scared enemy ghosts — attract (kill bonus).
        for opp_idx in agent.getOpponents(successor):
            try:
                opp_pos = successor.getAgentPosition(opp_idx)
                if opp_pos is None:
                    continue
                opp_state = successor.getAgentState(opp_idx)
                if getattr(opp_state, "isPacman", False):
                    continue
                scared = int(getattr(opp_state, "scaredTimer", 0) or 0)
                d = agent.getMazeDistance(pos, opp_pos)
                if scared > 0:
                    total += RC17_W_SCARED / ((d + 1) * (d + 1))
                else:
                    total -= RC17_W_GHOST / ((d + 1) * (d + 1))
            except Exception:
                continue

        return float(total)
    except Exception:
        return 0.0


class ReflexRC17Agent(ReflexA1Agent):
    """A1 champion + influence-map successor evaluation."""

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        weights = self._get_weights()
        try:
            from zoo_features import _ACTION_PREFERENCE
            ordered = sorted(
                legal,
                key=lambda a: (_ACTION_PREFERENCE.index(a)
                               if a in _ACTION_PREFERENCE
                               else len(_ACTION_PREFERENCE)),
            )
        except Exception:
            ordered = list(legal)

        best_score = float("-inf")
        best_action = None
        for action in ordered:
            try:
                feats = _base_extract_features(self, gameState, action)
                try:
                    from util import nearestPoint
                    succ = gameState.generateSuccessor(self.index, action)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw != nearestPoint(raw):
                        succ = succ.generateSuccessor(self.index, action)
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                except Exception:
                    succ = gameState
                    sp = None
                inf = _influence_at(self, sp, succ) if sp is not None else 0.0
                score = sum(weights.get(k, 0.0) * v for k, v in feats.items())
                score += RC17_F_WEIGHT * inf
            except Exception:
                score = float("-inf")
            if score > best_score:
                best_score = score
                best_action = action

        if best_action is None or best_action not in legal:
            non_stop = [a for a in legal if a != Directions.STOP]
            return non_stop[0] if non_stop else Directions.STOP
        return best_action


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC17Agent", second="ReflexRC17Agent"):
    return [ReflexRC17Agent(firstIndex), ReflexRC17Agent(secondIndex)]

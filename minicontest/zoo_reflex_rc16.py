# zoo_reflex_rc16.py
# ------------------
# rc16: Voronoi territorial-control overlay on A1 champion.
#
# Voronoi diagram on the maze graph: for each cell, the "owner" is
# whichever team has the closest agent (by maze-distance). We compute
# our net territorial balance per turn and encode it as a single signed
# feature, added on top of A1's 20 evolved features.
#
# Two net scores are computed:
#   - food_voronoi: (our-owned food cells − enemy-owned) / total food
#   - free_voronoi: (our-owned empty cells − enemy-owned) / total open cells
#
# These are collapsed into one feature `f_voronoiScore` = food_voronoi +
# 0.2 · free_voronoi. Food ownership dominates (food is what actually
# scores). The 0.2 weight on empty territory is a secondary incentive
# to maintain positional advantage even when food distribution is
# balanced.
#
# Computation cost: O(cells) at init for APSP is already precomputed in
# zoo_core. Per-turn we just iterate over food and empty cells and ask
# our O(1) `getMazeDistance`. Typical `< 5ms`/turn on default layouts.
#
# Hand-tuned weight = 30 on the feature, comparable to A1's mid-range
# weights (|w|≈25-40). Evolves positive → agent prefers moves that
# expand our territory.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import extract_features as _base_extract_features
from game import Directions


RC16_F_WEIGHT = 30.0  # applied to f_voronoiScore for both OFF and DEF
RC16_FREE_WEIGHT = 0.2  # relative weight of empty cells in the combined score


def _compute_voronoi_feature(agent, successor):
    """Return the signed Voronoi score for the given successor state.
    Value ∈ roughly [-1.2, +1.2]. Errors → 0.0."""
    try:
        my_team = list(agent.getTeam(successor))
        opp_team = list(agent.getOpponents(successor))
        my_positions = []
        for idx in my_team:
            try:
                p = successor.getAgentPosition(idx)
                if p is not None:
                    my_positions.append(p)
            except Exception:
                continue
        opp_positions = []
        for idx in opp_team:
            try:
                p = successor.getAgentPosition(idx)
                if p is not None:
                    opp_positions.append(p)
            except Exception:
                continue
        if not my_positions or not opp_positions:
            return 0.0

        # Food ownership.
        food_list = list(agent.getFood(successor).asList())
        defend_food = list(agent.getFoodYouAreDefending(successor).asList())
        all_food = food_list + defend_food
        if all_food:
            ours = 0
            theirs = 0
            for f in all_food:
                d_us = min(agent.getMazeDistance(p, f) for p in my_positions)
                d_them = min(agent.getMazeDistance(p, f) for p in opp_positions)
                if d_us < d_them:
                    ours += 1
                elif d_them < d_us:
                    theirs += 1
            food_vor = (ours - theirs) / max(len(all_food), 1)
        else:
            food_vor = 0.0

        # Empty-cell ownership — sample a stride to avoid O(H·W) per turn.
        walls = successor.getWalls()
        W, H = walls.width, walls.height
        stride = 2  # sample every 2nd cell in each axis; plenty for signal
        ours_e = 0
        theirs_e = 0
        for x in range(0, W, stride):
            for y in range(0, H, stride):
                if walls[x][y]:
                    continue
                cell = (x, y)
                d_us = min(agent.getMazeDistance(p, cell) for p in my_positions)
                d_them = min(agent.getMazeDistance(p, cell) for p in opp_positions)
                if d_us < d_them:
                    ours_e += 1
                elif d_them < d_us:
                    theirs_e += 1
        total = ours_e + theirs_e + 1
        free_vor = (ours_e - theirs_e) / total

        return float(food_vor + RC16_FREE_WEIGHT * free_vor)
    except Exception:
        return 0.0


class ReflexRC16Agent(ReflexA1Agent):
    """A1 champion + Voronoi territorial score feature."""

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        weights = self._get_weights()

        best_score = float("-inf")
        best_action = None
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

        for action in ordered:
            try:
                feats = _base_extract_features(self, gameState, action)
                # Compute successor for Voronoi (mirroring extract_features).
                try:
                    from util import nearestPoint
                    succ = gameState.generateSuccessor(self.index, action)
                    pos = succ.getAgentState(self.index).getPosition()
                    if pos != nearestPoint(pos):
                        succ = succ.generateSuccessor(self.index, action)
                except Exception:
                    succ = gameState
                vor = _compute_voronoi_feature(self, succ)
                feats["f_voronoiScore"] = vor
                score = sum(weights.get(k, 0.0) * v for k, v in feats.items())
                score += RC16_F_WEIGHT * vor
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
               first="ReflexRC16Agent", second="ReflexRC16Agent"):
    return [ReflexRC16Agent(firstIndex), ReflexRC16Agent(secondIndex)]

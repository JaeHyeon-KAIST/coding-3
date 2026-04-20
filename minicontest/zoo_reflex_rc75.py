# zoo_reflex_rc75.py
# ------------------
# rc75: Meta-Learning layout adaptation (MAML/Reptile-lite inference).
#
# MAML learns a base policy that adapts quickly to new tasks with few
# gradient steps. At inference time with no training, we approximate:
# detect the current "layout family" (open vs corridor) and apply a
# small ADDITIVE weight adjustment pre-trained for that family.
#
# Layout detection (cheap):
#   - corridor_score = # wall-cells in a 5x5 neighborhood around center
#   - High corridor → mass movement restricted, prefer chokepoint plays
#   - Low corridor → open → prefer fast collection / territorial Voronoi
#
# Weight adjustments (small, hand-tuned additive offsets, analogous to
# one Reptile inner-loop step):
#   corridor: +5 on f_onDefense, -5 on f_distToFood (be more patient
#              holding position; don't rush through chokes).
#   open:     +3 on f_distToFood, -3 on f_patrolDist (aggressive fan-out).
#
# Tier 3 (rc75 Meta-Learning family).

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate, _ACTION_PREFERENCE
from zoo_core import TEAM
from game import Directions


RC75_CORRIDOR_ADJ = {
    "f_onDefense": 5.0,
    "f_distToFood": -5.0,
    "f_patrolDist": 3.0,
}
RC75_OPEN_ADJ = {
    "f_distToFood": 3.0,
    "f_patrolDist": -3.0,
    "f_successorScore": 2.0,
}


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC75Agent", second="ReflexRC75Agent"):
    return [ReflexRC75Agent(firstIndex), ReflexRC75Agent(secondIndex)]


class ReflexRC75Agent(ReflexA1Agent):
    """A1 + layout-family adaptive additive weight adjustment."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc75_family = self._detect_family(gameState)

    def _detect_family(self, gameState):
        try:
            walls = gameState.getWalls()
            W, H = walls.width, walls.height
            cx, cy = W // 2, H // 2
            # Count walls in 5x5 around center.
            wall_count = 0
            total = 0
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    x = cx + dx
                    y = cy + dy
                    if 0 <= x < W and 0 <= y < H:
                        total += 1
                        if walls[x][y]:
                            wall_count += 1
            if total == 0:
                return "open"
            ratio = wall_count / total
            return "corridor" if ratio >= 0.35 else "open"
        except Exception:
            return "open"

    def _adjusted_weights(self, base):
        adj_table = (RC75_CORRIDOR_ADJ if self._rc75_family == "corridor"
                     else RC75_OPEN_ADJ)
        out = dict(base)
        for k, delta in adj_table.items():
            if k in out:
                out[k] = out[k] + delta
        return out

    def _chooseActionImpl(self, gameState):
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            base = self._get_weights()
            weights = self._adjusted_weights(base)

            try:
                ordered = sorted(
                    legal,
                    key=lambda a: (_ACTION_PREFERENCE.index(a)
                                   if a in _ACTION_PREFERENCE
                                   else len(_ACTION_PREFERENCE)),
                )
            except Exception:
                ordered = list(legal)

            best = float("-inf")
            best_a = None
            for a in ordered:
                try:
                    s = evaluate(self, gameState, a, weights)
                except Exception:
                    continue
                if s > best:
                    best = s
                    best_a = a

            if best_a is None or best_a not in legal:
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            return best_a
        except Exception:
            try:
                return super()._chooseActionImpl(gameState)
            except Exception:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP

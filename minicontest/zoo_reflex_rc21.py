# zoo_reflex_rc21.py
# ------------------
# rc21: Layout-clustering weight-swap overlay on A1 champion.
#
# Different maze layouts reward different strategies:
#   - Narrow/corridor-heavy: defense dominates (chokes work, food
#     clustered, short paths), reward defensive weight boost.
#   - Open/wide layouts: offense dominates (hard to defend, many
#     access points), reward offensive weight boost.
#
# At registerInitialState (15s budget), rc21 computes 3 layout
# metrics:
#   - open_ratio = #open-cells / #total-cells (density of non-walls)
#   - avg_degree = mean 4-neighbor openness per open cell
#   - dead_end_ratio = fraction of open cells with degree ≤ 1
#
# Classify into:
#   TIGHT   : avg_degree < 2.3 OR dead_end_ratio > 0.2
#   OPEN    : avg_degree > 2.6 AND dead_end_ratio < 0.1
#   MEDIUM  : otherwise
#
# Per-class weight-multiplier vector scales A1's loaded W_OFF / W_DEF
# at _get_weights time:
#   TIGHT   : DEFENSE ×1.15 (boost),  OFFENSE ×0.90 (dampen)
#   OPEN    : DEFENSE ×0.90,         OFFENSE ×1.10
#   MEDIUM  : no change (×1.00 both)
#
# The multiplier is applied uniformly across all weights (not
# per-feature) to stay conservative. Falls through to A1 semantics
# for all control flow.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_core import TEAM
from game import Directions


RC21_MULT_TABLE = {
    "TIGHT":  {"OFFENSE": 0.90, "DEFENSE": 1.15},
    "OPEN":   {"OFFENSE": 1.10, "DEFENSE": 0.90},
    "MEDIUM": {"OFFENSE": 1.00, "DEFENSE": 1.00},
}


def _layout_class(walls):
    try:
        W, H = walls.width, walls.height
    except Exception:
        return "MEDIUM"
    total = W * H
    if total <= 0:
        return "MEDIUM"
    open_cells = []
    for x in range(W):
        for y in range(H):
            if not walls[x][y]:
                open_cells.append((x, y))
    n_open = len(open_cells)
    if n_open == 0:
        return "MEDIUM"
    deg_sum = 0
    dead_ends = 0
    for (x, y) in open_cells:
        deg = 0
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not walls[nx][ny]:
                deg += 1
        deg_sum += deg
        if deg <= 1:
            dead_ends += 1
    avg_degree = deg_sum / n_open
    dead_end_ratio = dead_ends / n_open
    if avg_degree < 2.3 or dead_end_ratio > 0.2:
        return "TIGHT"
    if avg_degree > 2.6 and dead_end_ratio < 0.1:
        return "OPEN"
    return "MEDIUM"


class ReflexRC21Agent(ReflexA1Agent):
    """A1 champion + layout-class-conditioned weight multiplier."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self._rc21_class = _layout_class(gameState.getWalls())
        except Exception:
            self._rc21_class = "MEDIUM"

    def _get_weights(self):
        try:
            base = super()._get_weights()
        except Exception:
            return {}
        if not base:
            return base
        try:
            cls = getattr(self, "_rc21_class", "MEDIUM")
            role = TEAM.role.get(self.index, "OFFENSE")
            mult = RC21_MULT_TABLE.get(cls, {}).get(role, 1.0)
            if mult == 1.0:
                return base
            return {k: (v * mult) for k, v in base.items()}
        except Exception:
            return base


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC21Agent", second="ReflexRC21Agent"):
    return [ReflexRC21Agent(firstIndex), ReflexRC21Agent(secondIndex)]

# zoo_belief.py
# -------------
# Particle-filter-lite opponent belief tracker (pm20 T5, per Gemini
# "unfair advantage" recommendation).
#
# Maintains a 2D numpy belief distribution per enemy agent. Updates via
# (a) delta collapse when the enemy is directly observable
# (getAgentPosition returns a position) or (b) uniform 5-action random-walk
# diffusion when the enemy is out of sight (getAgentPosition returns None).
#
# Contest 2 caveat: SIGHT_RANGE + SONAR_NOISE_RANGE are commented out in
# capture.py, so enemies MAY always be visible in this assignment. In that
# case the tracker collapses to a trivial identity: belief = delta at the
# true position every tick, no diffusion ever. The tracker still runs but
# introduces negligible overhead (O(w*h) per update ~ 0.5ms on default map).
#
# Design principles:
#   - Pure numpy (no scipy, no sklearn — per assignment rules)
#   - Walls as valid-cell mask; belief mass routed only through open cells
#   - Motion model: uniform-5 (stay + 4 directions). Destination must be a
#     valid cell; disallowed directions pool into "stay" for mass conservation
#   - Renormalize each update to guard against numerical drift
#
# Reusable across agents: both teammates import the same TEAM.t5_tracker.

from __future__ import annotations

import numpy as np


class OpponentBeliefTracker:
    """Belief distribution over enemy positions."""

    def __init__(self, walls, enemy_indices):
        self.w, self.h = walls.width, walls.height
        # Valid-cell mask: True where not a wall
        self.valid = np.zeros((self.w, self.h), dtype=bool)
        for x in range(self.w):
            for y in range(self.h):
                if not walls[x][y]:
                    self.valid[x, y] = True
        n_valid = int(self.valid.sum())
        uniform = self.valid.astype(float) / max(n_valid, 1)
        self.beliefs = {idx: uniform.copy() for idx in enemy_indices}
        self.tick = 0

    def observe(self, enemy_idx, pos):
        """Update enemy_idx's belief given an observation. `pos` is (x, y) or None."""
        if enemy_idx not in self.beliefs:
            # Unknown enemy — initialize uniform
            n_valid = int(self.valid.sum())
            self.beliefs[enemy_idx] = self.valid.astype(float) / max(n_valid, 1)

        if pos is not None:
            try:
                x, y = int(pos[0]), int(pos[1])
            except Exception:
                return
            if 0 <= x < self.w and 0 <= y < self.h and self.valid[x, y]:
                b = np.zeros((self.w, self.h))
                b[x, y] = 1.0
                self.beliefs[enemy_idx] = b
                return
        # Not observed -> diffuse
        self.beliefs[enemy_idx] = self._diffuse(self.beliefs[enemy_idx])

    def _diffuse(self, b: np.ndarray) -> np.ndarray:
        """Uniform-5 random-walk propagation.

        For each cell, its belief mass spreads evenly into {stay, up, down,
        left, right} neighbors. Mass heading into a wall gets redirected to
        "stay" so total probability is conserved.
        """
        # Precompute the 5 directions' shifts. `np.roll` wraps around the
        # grid — we mask with self.valid to zero out wall cells and recover
        # mass that should have stayed in place.
        shares = 5.0
        incoming = np.zeros_like(b)
        per_cell_out = b / shares

        # "stay" contribution
        incoming += per_cell_out

        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            shifted = np.roll(per_cell_out, (dx, dy), axis=(0, 1))
            # Zero out wrap-around edges by masking out invalid destinations
            # and cells whose SOURCE would have been off-grid.
            # np.roll wraps, so we need to explicitly clear the wrapped-in strip.
            if dx == 1:   # moved right: column 0 got wrapped from last col
                shifted[0, :] = 0.0
            elif dx == -1:
                shifted[-1, :] = 0.0
            if dy == 1:
                shifted[:, 0] = 0.0
            elif dy == -1:
                shifted[:, -1] = 0.0
            # Mass arriving at wall cells bounces back to the source
            illegal_mass = shifted * (~self.valid)
            shifted = shifted * self.valid
            incoming += shifted
            # Bounce-back: shift illegal_mass back to its origin
            if np.any(illegal_mass):
                back = np.roll(illegal_mass, (-dx, -dy), axis=(0, 1))
                incoming += back

        # Renormalize; if mass collapsed (all cells invalid somehow), reset uniform
        s = incoming.sum()
        if s > 1e-9:
            incoming /= s
        else:
            n_valid = int(self.valid.sum())
            incoming = self.valid.astype(float) / max(n_valid, 1)
        return incoming

    def map_position(self, enemy_idx) -> tuple[int, int] | None:
        """Argmax (ML) position under the belief. Returns (x, y) or None."""
        b = self.beliefs.get(enemy_idx)
        if b is None:
            return None
        idx_flat = int(b.argmax())
        x = idx_flat // self.h
        y = idx_flat % self.h
        return (x, y)

    def expected_distance(self, enemy_idx, from_pos) -> float:
        """E[manhattan_dist(from_pos, enemy_pos)] under belief. O(w*h) vectorized."""
        b = self.beliefs.get(enemy_idx)
        if b is None:
            return 999.0
        try:
            fx, fy = int(from_pos[0]), int(from_pos[1])
        except Exception:
            return 999.0
        xs = np.arange(self.w).reshape(-1, 1)
        ys = np.arange(self.h).reshape(1, -1)
        dist = np.abs(xs - fx) + np.abs(ys - fy)
        return float((b * dist).sum())

    def peak_mass(self, enemy_idx) -> float:
        """Maximum belief mass on any single cell — proxy for tracker confidence.
        1.0 means localized to one cell (just observed or collapsed), <1 means
        diffused. Used to decide whether to act on the belief."""
        b = self.beliefs.get(enemy_idx)
        if b is None:
            return 0.0
        return float(b.max())

# zoo_reflex_rc85.py
# ------------------
# rc85: Dynamic capsule-timing specialist on A1 champion.
#
# A1's f_distToCapsule is always-on — it pulls Pacman toward capsules
# regardless of context. This is wasteful when we're safe (no ghost
# threat, not carrying much) — capsule gets consumed "for nothing".
#
# rc85 suppresses the capsule attraction (effectively zeroes
# f_distToCapsule) UNLESS a high-value firing condition holds:
#
#   (a) we are Pacman with a non-scared ghost at maze-dist ≤ 3 AND
#       a capsule is within 2x that ghost distance — the capsule
#       will save us,
#   (b) we are Pacman carrying ≥ 5 food AND a non-scared ghost is
#       closer than our nearest home cell — capsule removes threat,
#   (c) opponents have already been using their capsule (we can't
#       keep holding; spending it ourselves is strictly better than
#       leaving it).
#
# Implementation: override _get_weights to return a modified dict
# with f_distToCapsule = 0 when no trigger fires. Scoped to OFFENSE
# role only (DEFENSE already uses different weights).

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from game import Directions


RC85_GHOST_NEAR = 3
RC85_CARRY_HIGH = 5


class ReflexRC85Agent(ReflexA1Agent):
    """A1 champion + capsule-timing gate on OFFENSE role."""

    def _should_keep_capsule_weight(self, gameState):
        """True iff context justifies active capsule attraction."""
        try:
            my_pos = gameState.getAgentPosition(self.index)
            my_state = gameState.getAgentState(self.index)
            if my_pos is None:
                return False
            # Only gate while Pacman (on enemy side).
            if not getattr(my_state, "isPacman", False):
                return False

            try:
                carrying = int(getattr(my_state, "numCarrying", 0) or 0)
            except Exception:
                carrying = 0

            # Active ghost near us?
            ghost_near = False
            min_ghost_d = float("inf")
            for opp_idx in self.getOpponents(gameState):
                try:
                    ost = gameState.getAgentState(opp_idx)
                    if getattr(ost, "isPacman", False):
                        continue
                    if int(getattr(ost, "scaredTimer", 0) or 0) > 0:
                        continue
                    opp_pos = gameState.getAgentPosition(opp_idx)
                    if opp_pos is None:
                        continue
                    d = self.getMazeDistance(my_pos, opp_pos)
                    min_ghost_d = min(min_ghost_d, d)
                    if d <= RC85_GHOST_NEAR:
                        ghost_near = True
                except Exception:
                    continue

            # Fire (a): ghost ≤ 3 and capsule within reach.
            if ghost_near:
                try:
                    caps = self.getCapsules(gameState)
                    if caps:
                        for c in caps:
                            dc = self.getMazeDistance(my_pos, c)
                            if dc <= 2 * min_ghost_d:
                                return True
                except Exception:
                    pass

            # Fire (b): carrying ≥ 5 and ghost closer than home.
            if carrying >= RC85_CARRY_HIGH and min_ghost_d < float("inf"):
                try:
                    walls = gameState.getWalls()
                    half = walls.width // 2
                    is_red = self.red
                    home_col = half - 1 if is_red else half
                    home_dist = abs(my_pos[0] - home_col)
                    if min_ghost_d < home_dist:
                        return True
                except Exception:
                    pass

            # Fire (c): our capsule count decreased vs start — opponents
            # ate our capsule. Use theirs in retaliation if still
            # available. Approximation: if enemy capsules still exist
            # and our side's scared timer ran out ever, we didn't
            # benefit → take theirs.
            try:
                defended_caps = self.getCapsulesYouAreDefending(gameState)
                initial = getattr(self, "_rc85_init_defended", None)
                if initial is not None and len(defended_caps) < initial:
                    return True
            except Exception:
                pass

            return False
        except Exception:
            return True  # safer default: keep capsule weight on

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self._rc85_init_defended = len(self.getCapsulesYouAreDefending(gameState))
        except Exception:
            self._rc85_init_defended = None

    def _get_weights(self):
        try:
            base = super()._get_weights()
        except Exception:
            return {}
        if not base:
            return base
        role = TEAM.role.get(self.index, "OFFENSE")
        if role != "OFFENSE":
            return base
        # Without context, we can't easily access gameState here — so
        # we rely on _chooseActionImpl to cache a "should_keep" flag
        # each turn and gate the capsule weight via that.
        keep = getattr(self, "_rc85_keep_capsule", True)
        if keep:
            return base
        gated = dict(base)
        gated["f_distToCapsule"] = 0.0
        return gated

    def _chooseActionImpl(self, gameState):
        try:
            self._rc85_keep_capsule = self._should_keep_capsule_weight(gameState)
        except Exception:
            self._rc85_keep_capsule = True
        return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC85Agent", second="ReflexRC85Agent"):
    return [ReflexRC85Agent(firstIndex), ReflexRC85Agent(secondIndex)]

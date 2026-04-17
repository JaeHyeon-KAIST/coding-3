# zoo_reflex_A1_D13.py
# --------------------
# A1 champion weights + combined D1 role-swap + D3 endgame/lockout/teleport.
#
# Priority chain (first fire wins):
#   P0  D3 suicide-teleport        (action override, skips role logic entirely)
#   P1  D3 endgame-lead            (timeleft<100 + score>=1 -> DEFENSE)
#   P2  D3 endgame-behind          (timeleft<100 + score<0  -> OFFENSE)
#   P3  D3 mid-lockout             (timeleft<400 + lead>=2  -> lower-idx DEFENSE)
#   P4  D1 force-return            (carrying>=5 -> DEFENSE)
#   P5  D1 dual-defense            (invaders>=2 -> DEFENSE)
#   P6  D1 nearest-invader-handler (single invader + I'm closer -> DEFENSE)
#   P7  D1 safe-bank               (carrying>=3 + enemy unseen -> DEFENSE)
#   P8  fallback                   (base TEAM.role from CEM joint tuning)
#
# Rationale for D3-first ordering: D3 rules are time-pressured (endgame,
# lockout) and must override D1's strategic rules. E.g. "score=2 and
# timeleft=300 and carrying=8" should trigger D3 mid-lockout defender lock
# (D3 P3), NOT D1 force-return alone (which might leave no defender when
# teammate is also mid-mission). Suicide-teleport (P0) is an action override
# and sits outside the role chain entirely.
#
# Produced by composing D1 + D3's role-compute methods as unbound calls, so
# we get one class with both rule sets without multiple inheritance diamond
# issues. Both source modules remain independent.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from zoo_reflex_A1_D1 import ReflexA1D1Agent
from zoo_reflex_A1_D3 import ReflexA1D3Agent


class ReflexA1D13Agent(ReflexA1Agent):
    """A1 weights + D1 rules + D3 rules (priority-chained)."""

    def _compute_d13_role(self, gameState, base_role: str) -> str:
        """Try D3 rules first; fall through to D1 if D3 does not engage."""
        # D3 role compute — returns base_role unchanged if none of R1/R2/R3 fired.
        d3_role = ReflexA1D3Agent._compute_d3_role(self, gameState, base_role)
        if d3_role != base_role:
            return d3_role
        # D1 role compute — returns base_role unchanged if none of R1/R2/R4/R5 fired.
        return ReflexA1D1Agent._compute_d1_role(self, gameState, base_role)

    def _chooseActionImpl(self, gameState):
        # P0: D3 suicide-teleport (action override).
        try:
            teleport = ReflexA1D3Agent._check_suicide_teleport(self, gameState)
            if teleport is not None:
                return teleport
        except Exception:
            pass  # Failure here must never block normal play.

        # Role-override chain (P1-P7), falling through to base role (P8).
        try:
            original = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            return super()._chooseActionImpl(gameState)

        try:
            d13_role = self._compute_d13_role(gameState, original)
            TEAM.role[self.index] = d13_role
            try:
                return super()._chooseActionImpl(gameState)
            finally:
                TEAM.role[self.index] = original
        except Exception:
            try:
                TEAM.role[self.index] = original
            except Exception:
                pass
            return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexA1D13Agent", second="ReflexA1D13Agent"):
    return [ReflexA1D13Agent(firstIndex), ReflexA1D13Agent(secondIndex)]

# zoo_reflex_A1_D1.py
# -------------------
# A1 champion weights + D1 role-swap & arbitration rules (pm20, Codex-advised).
#
# D1 is the first rule-based hybrid layer in the pm20 plan. It wraps
# ReflexA1Agent (which pins A1's evolved weights via load_weights_override)
# and adds deterministic role-override rules on top of the CEM-learned
# evaluator.
#
# Rule priority (first matching rule wins):
#   R1 force-return   carrying >= 5              -> DEFENSE (home-bound weights)
#   R2 dual-defense   invaders >= 2              -> DEFENSE
#   R3 endgame-lock   lead>=1 & timeleft<200     -> lower-idx agent permanent DEFENSE
#   R4 nearest-handler 1 invader & I'm closer    -> DEFENSE (I handle invader)
#   R5 safe-bank      carrying>=3 & enemy unseen -> DEFENSE (bank conservatively)
#   R0 fallback                                  -> base TEAM.role (CEM joint-tuned)
#
# Role switching is done by temporarily mutating TEAM.role[self.index] for this
# turn only (then restoring in finally). Turns are sequential in CS188 so no
# cross-agent race.
#
# Expected uplift (Codex): +12 to +30 Elo over bare A1 if arbitration works as
# designed. Smoke-verifiable vs baseline (should match or exceed A1's 79%).

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent

# Rule thresholds (hardcoded; A1's evolved PARAMS dict is noise since the
# zoo_reflex_tuned container doesn't consume PARAMS during CEM training).
D1_RETURN_THRESHOLD = 5       # R1: carrying >= this -> force return
D1_INVADER_MULTI_THRESHOLD = 2  # R2: invaders >= this -> dual defense
D1_ENDGAME_TIMELEFT = 200     # R3: timeleft < this AND lead -> permanent defender
D1_LEAD_THRESHOLD = 1         # R3: score_lead >= this
D1_BANK_THRESHOLD = 3         # R5: carrying >= this AND enemy unseen -> bank


class ReflexA1D1Agent(ReflexA1Agent):
    """A1 champion weights + D1 deterministic role-override rules."""

    def _compute_d1_role(self, gameState, base_role: str) -> str:
        """Apply D1 rules in priority order. Returns 'OFFENSE' or 'DEFENSE'.
        Never raises — any failure falls back to base_role.
        """
        try:
            snap = self.snapshot(gameState)
        except Exception:
            return base_role

        try:
            numCarrying = int(snap.get("numCarrying", 0) or 0)
        except Exception:
            numCarrying = 0

        # R1: Force return if carrying enough food.
        if numCarrying >= D1_RETURN_THRESHOLD:
            return "DEFENSE"

        # Count visible invaders (opponent pacmen on our side).
        invader_count = 0
        opp_positions = snap.get("opponentPositions", {}) or {}
        any_enemy_visible = False
        for opp_idx, opp_pos in opp_positions.items():
            if opp_pos is not None:
                any_enemy_visible = True
            try:
                opp_state = gameState.getAgentState(opp_idx)
                if opp_pos is not None and getattr(opp_state, "isPacman", False):
                    invader_count += 1
            except Exception:
                continue

        # R2: Dual defense when multiple invaders.
        if invader_count >= D1_INVADER_MULTI_THRESHOLD:
            return "DEFENSE"

        # R3: Endgame permanent-defender lock.
        try:
            score = int(self.getScore(gameState))
            timeleft = int(getattr(gameState.data, "timeleft", 1200) or 1200)
            if score >= D1_LEAD_THRESHOLD and timeleft < D1_ENDGAME_TIMELEFT:
                my_team = sorted(list(self.getTeam(gameState)))
                # Lower-index teammate becomes the permanent defender; the
                # higher-index one may continue offense to press the score.
                if my_team and self.index == my_team[0]:
                    return "DEFENSE"
        except Exception:
            pass

        # R4: Single invader — closest-to-home teammate handles it.
        if invader_count == 1 and base_role == "OFFENSE":
            try:
                home = list(self.homeFrontier) if self.homeFrontier else []
                my_pos = gameState.getAgentPosition(self.index)
                teammates = [i for i in self.getTeam(gameState) if i != self.index]
                if home and my_pos and teammates:
                    tm_idx = teammates[0]
                    tm_pos = gameState.getAgentPosition(tm_idx)
                    my_home = min(self.getMazeDistance(my_pos, h) for h in home)
                    if tm_pos is not None:
                        tm_home = min(self.getMazeDistance(tm_pos, h) for h in home)
                    else:
                        tm_home = 999
                    if my_home < tm_home:
                        return "DEFENSE"
            except Exception:
                pass

        # R5: Safe-bank — moderate carrying + no visible enemy → conservative return.
        if numCarrying >= D1_BANK_THRESHOLD and not any_enemy_visible:
            return "DEFENSE"

        # R0 fallback.
        return base_role

    def _chooseActionImpl(self, gameState):
        """Override TEAM.role[self.index] for this turn, then call the A1
        (ReflexTunedAgent) argmax. Restore role in finally so teammate sees
        the original joint-tuned role assignment.
        """
        try:
            original = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            return super()._chooseActionImpl(gameState)

        try:
            d1_role = self._compute_d1_role(gameState, original)
            TEAM.role[self.index] = d1_role
            try:
                return super()._chooseActionImpl(gameState)
            finally:
                TEAM.role[self.index] = original
        except Exception:
            # If D1 logic itself raises, fall back to pure A1 behavior.
            try:
                TEAM.role[self.index] = original
            except Exception:
                pass
            return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexA1D1Agent", second="ReflexA1D1Agent"):
    return [ReflexA1D1Agent(firstIndex), ReflexA1D1Agent(secondIndex)]

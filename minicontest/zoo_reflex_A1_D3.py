# zoo_reflex_A1_D3.py
# -------------------
# A1 champion weights + D3 endgame / score-lead / suicide-teleport rules.
# pm20 Codex ROI #2 (score-lead lockout with safe triggers): +10 to +30 Elo
# conditional; Gemini priority #4 (endgame lockout): +2h implementation.
#
# Priority chain (first match wins):
#   R1 endgame-lead    timeleft<100 AND score>=1        -> both DEFENSE (seal win)
#   R2 endgame-behind  timeleft<100 AND score<0         -> both OFFENSE (desperation)
#   R3 mid-lead-lock   timeleft<400 AND score_lead>=2   -> lower-idx DEFENSE
#   R4 suicide-teleport dist_to_home>20 AND invader>=1
#                      AND carrying<=1                  -> legal action minimizing
#                                                          dist to nearest active
#                                                          enemy ghost (respawn)
#   R0 fallback                                         -> base A1 behavior
#
# R1/R2 are turn-terminal score-seal mechanics; R3 is the "don't throw the lead"
# safety net; R4 is a niche tactic (Gemini) that converts dead-far-from-home
# Pacman into an instant home respawn to cover a defensive emergency. R4 is
# disabled when we carry >1 food (we'd lose points), not when score is close.
#
# D3 does NOT include D1 rules — compose via zoo_reflex_A1_D1D3.py later.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent

D3_ENDGAME_TIMELEFT = 100      # R1/R2 final-push window (in moves)
D3_MID_LOCKOUT_TIMELEFT = 400  # R3 start of mid-lockout
D3_MID_LOCKOUT_LEAD = 2        # R3 score lead required to engage mid-lockout
D3_TELEPORT_HOME_DIST = 20     # R4 "dead-far" threshold
D3_TELEPORT_MAX_CARRYING = 1   # R4 must be carrying <= this (don't lose points)


class ReflexA1D3Agent(ReflexA1Agent):
    """A1 champion weights + D3 endgame / lockout / teleport rules."""

    # ---------------- role overrides (R1 / R2 / R3) ----------------

    def _compute_d3_role(self, gameState, base_role: str) -> str:
        try:
            score = int(self.getScore(gameState))
        except Exception:
            score = 0
        try:
            timeleft = int(getattr(gameState.data, "timeleft", 1200) or 1200)
        except Exception:
            timeleft = 1200

        try:
            my_team = sorted(list(self.getTeam(gameState)))
            is_lower_idx = bool(my_team) and self.index == my_team[0]
        except Exception:
            is_lower_idx = False

        # R1: endgame + leading -> both DEFENSE (lock the lead)
        if timeleft < D3_ENDGAME_TIMELEFT and score >= 1:
            return "DEFENSE"

        # R2: endgame + behind -> both OFFENSE (desperation; accept risk)
        if timeleft < D3_ENDGAME_TIMELEFT and score < 0:
            return "OFFENSE"

        # R3: mid-game big-lead lockout -> lower-idx defender, higher-idx keeps pressing
        if timeleft < D3_MID_LOCKOUT_TIMELEFT and score >= D3_MID_LOCKOUT_LEAD:
            if is_lower_idx:
                return "DEFENSE"

        return base_role

    # ---------------- action override (R4) -------------------------

    def _check_suicide_teleport(self, gameState):
        """If R4 trigger fires, return a legal action that minimizes distance
        to the nearest active enemy ghost (leading to respawn at home). Else
        return None and let the evaluator pick.
        """
        try:
            snap = self.snapshot(gameState)
        except Exception:
            return None

        my_pos = snap.get("myPos")
        if my_pos is None:
            return None

        try:
            numCarrying = int(snap.get("numCarrying", 0) or 0)
        except Exception:
            numCarrying = 0
        if numCarrying > D3_TELEPORT_MAX_CARRYING:
            return None

        # Check home distance — must be "dead far" to justify suicide cost.
        try:
            home = list(self.homeFrontier) if self.homeFrontier else []
            if not home:
                return None
            my_home_dist = min(self.getMazeDistance(my_pos, h) for h in home)
            if my_home_dist < D3_TELEPORT_HOME_DIST:
                return None
        except Exception:
            return None

        # Need at least one invader on our side.
        invader_count = 0
        opp_positions = snap.get("opponentPositions") or {}
        for opp_idx, opp_pos in opp_positions.items():
            if opp_pos is None:
                continue
            try:
                opp_state = gameState.getAgentState(opp_idx)
                if getattr(opp_state, "isPacman", False):
                    invader_count += 1
            except Exception:
                continue
        if invader_count < 1:
            return None

        # Nearest active (non-scared) enemy ghost we can see.
        ghost_positions = []
        for opp_idx, opp_pos in opp_positions.items():
            if opp_pos is None:
                continue
            try:
                opp_state = gameState.getAgentState(opp_idx)
                if getattr(opp_state, "isPacman", False):
                    continue
                if int(getattr(opp_state, "scaredTimer", 0) or 0) > 0:
                    continue
                ghost_positions.append(opp_pos)
            except Exception:
                continue
        if not ghost_positions:
            return None  # no visible active ghost -> skip (can't target)

        # Argmin: legal action whose successor position minimizes distance
        # to the nearest ghost.
        try:
            from util import nearestPoint
        except Exception:
            return None

        legal = gameState.getLegalActions(self.index)
        if not legal:
            return None

        best_action = None
        best_dist = float("inf")
        for action in legal:
            try:
                succ = gameState.generateSuccessor(self.index, action)
                succ_pos_raw = succ.getAgentState(self.index).getPosition()
                if succ_pos_raw is None:
                    continue
                succ_pos = nearestPoint(succ_pos_raw)
                dist = min(self.getMazeDistance(succ_pos, g) for g in ghost_positions)
                if dist < best_dist:
                    best_dist = dist
                    best_action = action
            except Exception:
                continue

        return best_action

    # ---------------- main override --------------------------------

    def _chooseActionImpl(self, gameState):
        # R4 (action override) fires before role override.
        try:
            teleport = self._check_suicide_teleport(gameState)
            if teleport is not None:
                return teleport
        except Exception:
            pass  # R4 failure never blocks normal flow

        # R1 / R2 / R3 via TEAM.role swap.
        try:
            original = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            return super()._chooseActionImpl(gameState)

        try:
            d3_role = self._compute_d3_role(gameState, original)
            TEAM.role[self.index] = d3_role
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
               first="ReflexA1D3Agent", second="ReflexA1D3Agent"):
    return [ReflexA1D3Agent(firstIndex), ReflexA1D3Agent(secondIndex)]

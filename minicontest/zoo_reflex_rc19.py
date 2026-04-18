# zoo_reflex_rc19.py
# ------------------
# rc19: Game-phase-conditional weight switching on A1 champion.
#
# A1 was CEM-evolved to a single weight vector that averages across the
# entire 1200-move episode. Three distinct phases of play exist, however:
#
#   OPENING  (timeleft > 900): no food eaten yet, no information on
#                              opponent's style. Low-risk harvesting is
#                              optimal: push into enemy territory but
#                              hold on close-quarters decisions.
#   MID      (400 < tl ≤ 900): normal play. A1's evolved behavior is a
#                              good default here — use it unchanged.
#   ENDGAME  (tl ≤ 400):       score-aware. If leading (score ≥ 1):
#                              damp offense, amplify defense — protect
#                              the win. If tied/behind: amplify offense,
#                              dampen ghost fear — take the risk.
#
# Implementation: `_get_weights()` delegates to the A1 base, then
# multiplies specific feature weights by phase-dependent multipliers.
# No new features introduced; no structural change to the evaluator.
# Multipliers are conservative (0.5–2.0) so we never stray more than
# one order of magnitude from A1's evolved balance.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent


PHASE_OPENING_START = 900
PHASE_ENDGAME_START = 400

# Multipliers per phase. Each dict maps feature name → scale applied to A1 w.
_PHASE_OPENING = {
    # Encourage borderland food over deep raids.
    "f_distToHome": 1.3,
    "f_distToFood": 1.2,
    # Slightly more cautious vs ghosts (we have time to wait).
    "f_ghostDist1": 1.3,
    "f_ghostDist2": 1.3,
}

_PHASE_ENDGAME_LEAD = {
    # Protect the lead: amplify defense, damp offense.
    "f_distToFood": 0.5,
    "f_successorScore": 0.6,
    "f_distToCapsule": 0.7,
    "f_invaderDist": 1.5,
    "f_numInvaders": 1.5,
    "f_patrolDist": 1.5,
    "f_ghostDist1": 1.5,
    "f_ghostDist2": 1.5,
    "f_returnUrgency": 1.4,
}

_PHASE_ENDGAME_BEHIND = {
    # All-in: amplify offense, damp ghost fear (accept risk).
    "f_distToFood": 1.8,
    "f_successorScore": 1.5,
    "f_distToCapsule": 1.5,
    "f_ghostDist1": 0.6,
    "f_ghostDist2": 0.6,
    "f_inDeadEnd": 0.6,
    "f_returnUrgency": 0.8,
}


def _phase_of(timeleft: int, score: int) -> str:
    if timeleft > PHASE_OPENING_START:
        return "opening"
    if timeleft > PHASE_ENDGAME_START:
        return "mid"
    return "endgame_lead" if score >= 1 else "endgame_behind"


class ReflexRC19Agent(ReflexA1Agent):
    """A1 champion + phase-conditional weight scaling."""

    def _chooseActionImpl(self, gameState):
        # Cache phase so _get_weights can read it without gameState.
        try:
            timeleft = int(getattr(gameState.data, "timeleft", 1200) or 1200)
        except Exception:
            timeleft = 1200
        try:
            score = int(self.getScore(gameState))
        except Exception:
            score = 0
        self._rc19_phase = _phase_of(timeleft, score)
        return super()._chooseActionImpl(gameState)

    def _get_weights(self):
        base = super()._get_weights()
        phase = getattr(self, "_rc19_phase", "mid")
        if phase == "mid":
            return base
        if phase == "opening":
            mult = _PHASE_OPENING
        elif phase == "endgame_lead":
            mult = _PHASE_ENDGAME_LEAD
        elif phase == "endgame_behind":
            mult = _PHASE_ENDGAME_BEHIND
        else:
            return base
        adj = dict(base)
        for k, m in mult.items():
            if k in adj:
                adj[k] = adj[k] * m
        return adj


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC19Agent", second="ReflexRC19Agent"):
    return [ReflexRC19Agent(firstIndex), ReflexRC19Agent(secondIndex)]

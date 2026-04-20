# zoo_reflex_rc59.py
# ------------------
# rc59: Reward Machines / Automata-guided policy.
#
# Explicit FSM over game "stages" with stage-specific WEIGHT SCALINGS
# applied on top of A1's evolved weights. Different from rc19
# (phase-conditional) which swaps weight VECTORS — rc59 keeps A1's
# base vector and multiplies specific features per stage to bias
# decision-making toward the active stage's objective.
#
# FSM states:
#   HUNT       — my carry == 0 AND timeleft > 800 (opening/exploration)
#                → boost f_distToFood, f_distToCapsule; nothing else changed.
#   COLLECT    — my carry 1-5 (picking up food)
#                → boost f_numCarrying (negative → more negative, return bias),
#                   boost f_ghostDist1 (safer).
#   RETURN     — my carry >= 6 (must deliver)
#                → heavily boost f_distToHome (positive → stronger pull home),
#                   reduce f_distToFood (don't chase more).
#   DEFEND     — score >= 3 AND timeleft < 600 (locking in lead)
#                → boost f_onDefense, f_invaderDist, f_patrolDist.
#   DESPERATE  — score <= -3 AND timeleft < 400 (last-ditch)
#                → boost f_distToFood heavily, reduce ghost penalty.
#
# Tier 3 (category: Multi-agent coordination / Reward shaping).

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent, _A1_OVERRIDE
from zoo_features import evaluate, SEED_WEIGHTS_OFFENSIVE, SEED_WEIGHTS_DEFENSIVE, _ACTION_PREFERENCE
from zoo_core import TEAM
from game import Directions


# Per-stage multiplicative biases on specific features.
RC59_STAGE_BIAS = {
    "HUNT": {
        "f_distToFood": 1.25,
        "f_distToCapsule": 1.20,
    },
    "COLLECT": {
        "f_numCarrying": 1.15,
        "f_ghostDist1": 1.15,
        "f_ghostDist2": 1.10,
    },
    "RETURN": {
        "f_distToHome": 1.60,
        "f_distToFood": 0.60,
        "f_ghostDist1": 1.25,
    },
    "DEFEND": {
        "f_onDefense": 1.40,
        "f_invaderDist": 1.30,
        "f_patrolDist": 1.25,
    },
    "DESPERATE": {
        "f_distToFood": 1.50,
        "f_ghostDist1": 0.70,
        "f_ghostDist2": 0.70,
    },
}


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC59Agent", second="ReflexRC59Agent"):
    return [ReflexRC59Agent(firstIndex), ReflexRC59Agent(secondIndex)]


class ReflexRC59Agent(ReflexA1Agent):
    """A1 + stage-FSM weight biasing."""

    def _my_score(self, gameState):
        try:
            s = gameState.getScore()
            return s if self.red else -s
        except Exception:
            return 0

    def _current_stage(self, gameState):
        try:
            st = gameState.getAgentState(self.index)
            carry = int(getattr(st, "numCarrying", 0) or 0)
        except Exception:
            carry = 0
        try:
            timeleft = int(getattr(gameState.data, "timeleft", 1200) or 1200)
        except Exception:
            timeleft = 1200
        score = self._my_score(gameState)

        # Stage precedence: DEFEND / DESPERATE override carry-based states
        # in late game; otherwise carry-based.
        if score >= 3 and timeleft < 600:
            return "DEFEND"
        if score <= -3 and timeleft < 400:
            return "DESPERATE"
        if carry >= 6:
            return "RETURN"
        if carry >= 1:
            return "COLLECT"
        if timeleft > 800:
            return "HUNT"
        return "COLLECT"  # default middle-game

    def _biased_weights(self, base_weights, stage):
        bias = RC59_STAGE_BIAS.get(stage)
        if not bias:
            return dict(base_weights)
        out = dict(base_weights)
        for k, mult in bias.items():
            if k in out:
                out[k] = out[k] * mult
        return out

    def _chooseActionImpl(self, gameState):
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            base = self._get_weights()
            stage = self._current_stage(gameState)
            weights = self._biased_weights(base, stage)

            best = float("-inf")
            best_a = None
            try:
                ordered = sorted(
                    legal,
                    key=lambda a: (_ACTION_PREFERENCE.index(a)
                                   if a in _ACTION_PREFERENCE
                                   else len(_ACTION_PREFERENCE)),
                )
            except Exception:
                ordered = list(legal)
            for a in ordered:
                try:
                    v = evaluate(self, gameState, a, weights)
                except Exception:
                    continue
                if v > best:
                    best = v
                    best_a = a

            if best_a is None or best_a not in legal:
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            return best_a
        except Exception:
            try:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            except Exception:
                return Directions.STOP

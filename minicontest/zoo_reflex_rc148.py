# zoo_reflex_rc148.py
# -------------------
# rc148: SCORE-CONDITIONED policy switching.
#
# At each turn, read current game score (from Red's perspective; flipped
# for Blue). Switch among three champions:
#   - leading by ≥ +5 : rc82 (100% conservative composite — maintain lead)
#   - trailing by ≥ -3 or tied : rc52b (92% aggressive REINFORCE — push offense)
#   - otherwise (early-game or near-equal) : A1 base (86% balanced)
#
# Heuristic basis: score-conditioned agents in classical adversarial search
# literature (e.g. Berliner 1970) choose risk-aversion vs. risk-seeking
# based on advantage. rc82 composite dominates vs baseline so gives the
# safest "stay ahead" choice; rc52b's learned-offense weights push food-
# eating aggressiveness when behind.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc52b import _RC52B_OVERRIDE
from zoo_reflex_A1 import _A1_OVERRIDE
from zoo_core import TEAM


SCORE_LEAD = 5      # ≥ → rc82
SCORE_CHASE = -3    # ≤ → rc52b


class ReflexRC148Agent(ReflexRC82Agent):
    """Score-conditioned switch among rc82/rc52b/A1."""

    def _my_score(self, gameState):
        # Positive means Red leads. Flip for Blue so "+ is good for us".
        s = gameState.getScore()
        return s if self.red else -s

    def _chooseActionImpl(self, gameState):
        score = self._my_score(gameState)

        if score >= SCORE_LEAD:
            # Leading comfortably → rc82 composite (super()).
            return super()._chooseActionImpl(gameState)

        # Behind or near-tied → swap weights and use base tuned logic.
        saved = getattr(self, "_weights_override", None)
        try:
            if score <= SCORE_CHASE and _RC52B_OVERRIDE.get("w_off"):
                self._weights_override = _RC52B_OVERRIDE
            else:
                # Early-game or slight lead → A1 balanced.
                if _A1_OVERRIDE.get("w_off"):
                    self._weights_override = _A1_OVERRIDE
            from zoo_reflex_tuned import ReflexTunedAgent
            return ReflexTunedAgent._chooseActionImpl(self, gameState)
        finally:
            self._weights_override = saved


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC148Agent", second="ReflexRC148Agent"):
    return [ReflexRC148Agent(firstIndex), ReflexRC148Agent(secondIndex)]

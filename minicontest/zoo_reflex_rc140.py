# zoo_reflex_rc140.py
# -------------------
# rc140: ROLE-ASYMMETRIC — rc52 (REINFORCE) on OFFENSE, rc82 (100% composite) on DEFENSE.
#
# Pattern learned from pm24 Batches I-P:
#   rc16 + rc82-def = rc105 (100%)
#   rc16+rc29 + rc82-def = rc109 (100%)
#   rc32 + rc82-def = rc123 (100%)
#   rc32+rc29 + rc82-def = rc131 (100%)
# → "strong OFF + rc82 DEF" is consistently the top archetype.
#
# rc140 extends this: use rc52 (REINFORCE learned, 95% solo WR) on OFFENSE.
# Hypothesis: learned linear-Q offense may be more flexible than rc16 Voronoi
# or rc32 Pincer, giving a fresh 100% champion with a neural-learned component.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc52 import ReflexRC52Agent, _RC52_OVERRIDE
from zoo_core import TEAM


class ReflexRC140Agent(ReflexRC82Agent):
    """rc52 for offense, rc82 full composite for defense."""

    def __init__(self, index, timeForComputing=0.1):
        super().__init__(index, timeForComputing=timeForComputing)
        # Store rc52's learned weights so the OFFENSE branch can use them.
        self._rc52_override = _RC52_OVERRIDE

    def _chooseActionImpl(self, gameState):
        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"

        if role == "OFFENSE":
            # Temporarily attach rc52 weights as override, delegate to
            # ReflexRC52Agent's logic (inherits from tuned).
            #
            # We construct on-the-fly: set self._weights_override, then call
            # the tuned agent's _chooseActionImpl (which honours override via
            # _get_weights). This re-uses all the rc82/rc44 precompute state
            # already loaded into `self`.
            saved = getattr(self, "_weights_override", None)
            try:
                if self._rc52_override.get("w_off"):
                    self._weights_override = self._rc52_override
                # Jump to tuned's _chooseActionImpl through the MRO —
                # ReflexTunedAgent is an ancestor (via A1 → tuned).
                from zoo_reflex_tuned import ReflexTunedAgent
                action = ReflexTunedAgent._chooseActionImpl(self, gameState)
                return action
            except Exception:
                pass
            finally:
                self._weights_override = saved

        # DEFENSE role → full rc82 composite (rc44 stacking + rc29 REVERSE).
        return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC140Agent", second="ReflexRC140Agent"):
    return [ReflexRC140Agent(firstIndex), ReflexRC140Agent(secondIndex)]

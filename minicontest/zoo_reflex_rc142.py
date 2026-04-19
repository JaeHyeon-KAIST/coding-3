# zoo_reflex_rc142.py
# -------------------
# rc142: ROLE-ASYMMETRIC — rc46 (K-centroid opponent classifier, A1 + counter
# multipliers) on OFFENSE, rc82 (100% composite rc44+rc29 stack) on DEFENSE.
#
# Hypothesis: rc46 solo reached 91% by adapting A1 to the opponent archetype.
# rc141 (rc52b OFF + rc82 DEF) gave 90% — LESS than rc52b solo 92%. Pattern
# learned: "X OFF + rc82 DEF" sweet spot holds for COMPOSITE offenses (rc16,
# rc32 → 100%) but not for learned linear-Q. rc46's adaptive multiplier
# approach is a hybrid: still reflex-based (no MLP), but opponent-aware.
# If the "offense must stay composite-friendly" rule holds, rc142 could hit
# 95%+ because rc46's multipliers on top of rc82 DEF preserve policy structure.

from __future__ import annotations

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_reflex_rc46 import _observe, _classify, _COUNTER, ARCH_NEUTRAL
from zoo_core import TEAM


class ReflexRC142Agent(ReflexRC82Agent):
    """rc46 classifier on OFFENSE, rc82 composite on DEFENSE."""

    def _chooseActionImpl(self, gameState):
        try:
            _observe(self, gameState)
            _classify(self, gameState)
        except Exception:
            pass

        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"

        if role == "OFFENSE":
            from zoo_reflex_tuned import ReflexTunedAgent
            return ReflexTunedAgent._chooseActionImpl(self, gameState)

        return super()._chooseActionImpl(gameState)

    def _get_weights(self):
        base = super()._get_weights()
        try:
            if not getattr(TEAM, "rc46_classified", False):
                return base
            role = TEAM.role.get(self.index, "OFFENSE")
            if role != "OFFENSE":
                return base  # DEFENSE uses rc82 unaltered
            arch = getattr(TEAM, "rc46_arch", ARCH_NEUTRAL)
            mult = _COUNTER.get(arch, {})
            if not mult:
                return base
            adj = dict(base)
            for k, m in mult.items():
                if k in adj:
                    adj[k] = adj[k] * m
            return adj
        except Exception:
            return base


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC142Agent", second="ReflexRC142Agent"):
    return [ReflexRC142Agent(firstIndex), ReflexRC142Agent(secondIndex)]

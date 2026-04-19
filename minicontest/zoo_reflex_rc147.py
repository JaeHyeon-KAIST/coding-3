# zoo_reflex_rc147.py
# -------------------
# rc147: rc46 classifier but NEUTRAL archetype uses rc52b weights
# (92% solo) instead of A1 (86% solo). Other archetypes keep A1 base
# + counter multipliers.
#
# Rationale: baseline's ≈ 0.40 invader-presence maps to NEUTRAL centroid.
# Most games classify NEUTRAL, which rc46 treats as "no-op on A1". If we
# swap that to rc52b weights, the majority-case game uses the stronger
# learned policy. Non-NEUTRAL cases (RUSH/TURTLE/CHOKE) keep A1+counter
# since rc52b wasn't trained to counter those extremes.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent, _A1_OVERRIDE
from zoo_reflex_rc52b import _RC52B_OVERRIDE
from zoo_reflex_rc46 import (
    _observe, _classify, _COUNTER,
    ARCH_NEUTRAL, ARCH_RUSH, ARCH_TURTLE, ARCH_CHOKE,
)
from zoo_core import TEAM


class ReflexRC147Agent(ReflexA1Agent):
    """rc46 classifier + NEUTRAL uses rc52b; others use A1+multiplier."""

    def _chooseActionImpl(self, gameState):
        try:
            _observe(self, gameState)
            _classify(self, gameState)
        except Exception:
            pass

        saved = getattr(self, "_weights_override", None)
        try:
            arch = getattr(TEAM, "rc46_arch", ARCH_NEUTRAL)
            classified = getattr(TEAM, "rc46_classified", False)
            if classified and arch == ARCH_NEUTRAL and _RC52B_OVERRIDE.get("w_off"):
                # Swap to rc52b weights for the majority-case baseline archetype.
                self._weights_override = _RC52B_OVERRIDE
            from zoo_reflex_tuned import ReflexTunedAgent
            return ReflexTunedAgent._chooseActionImpl(self, gameState)
        finally:
            self._weights_override = saved

    def _get_weights(self):
        # Only called when we have non-NEUTRAL archetype (since NEUTRAL
        # branch sets override and jumps to tuned). Apply rc46 multipliers
        # on A1 base.
        base = super()._get_weights()
        try:
            if not getattr(TEAM, "rc46_classified", False):
                return base
            arch = getattr(TEAM, "rc46_arch", ARCH_NEUTRAL)
            if arch == ARCH_NEUTRAL:
                return base  # shouldn't hit here normally
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
               first="ReflexRC147Agent", second="ReflexRC147Agent"):
    return [ReflexRC147Agent(firstIndex), ReflexRC147Agent(secondIndex)]

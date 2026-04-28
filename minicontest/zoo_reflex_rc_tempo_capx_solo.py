"""pm46 v2 — CAPX solo wrapper.

Red team composition (mirror of zoo_reflex_rc_tempo_abs_solo.py pattern):
    lower-index agent  = ReflexRCTempoCapxAgent (capsule-only attacker)
    higher-index agent = StubBAgent (STOP forever)

Rationale:
    pm46 v2 CAPX = single-purpose attacker probe. Goal = "A reaches at least
    1 capsule alive" against each of 17 defender zoo entries. B is stubbed
    so that B coordination cannot confound the survival signal.

CAPX defines its OWN StubBAgent (no import from abs_solo) per plan §5.5.

Use:
    cd minicontest
    ../.venv/bin/python ../experiments/rc_tempo/pm45_single_game.py \\
        -r zoo_reflex_rc_tempo_capx_solo -b baseline -l RANDOM1 -n 1 -q
"""
from __future__ import annotations

from captureAgents import CaptureAgent
from game import Directions
from zoo_reflex_rc_tempo_capx import ReflexRCTempoCapxAgent


class StubBAgent(CaptureAgent):
    """Minimal stub — STOP every turn at spawn position."""

    def registerInitialState(self, gameState):
        CaptureAgent.registerInitialState(self, gameState)

    def chooseAction(self, gameState):
        legal = gameState.getLegalActions(self.index)
        if Directions.STOP in legal:
            return Directions.STOP
        return legal[0] if legal else Directions.STOP


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexRCTempoCapxAgent', second='StubBAgent'):
    """Lower-index → full CAPX agent. Higher-index → stub B."""
    if firstIndex < secondIndex:
        return [ReflexRCTempoCapxAgent(firstIndex), StubBAgent(secondIndex)]
    return [StubBAgent(firstIndex), ReflexRCTempoCapxAgent(secondIndex)]

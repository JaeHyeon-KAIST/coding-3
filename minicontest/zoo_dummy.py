# zoo_dummy.py
# ------------
# Minimal smoke-test agent that inherits from `CoreCaptureAgent`. Used at
# M1 to confirm the shared base does not crash, that the framework's
# `-r zoo_dummy` import + `createTeam` path works, and that the timeout-
# preserving wrap in CoreCaptureAgent does not interfere with normal play.
#
# This agent picks a random non-STOP legal action each turn (or STOP if
# the only legal action is STOP). It is intentionally weak — its sole
# purpose is to verify the M1 plumbing.

from __future__ import annotations

import random

from game import Directions

from zoo_core import CoreCaptureAgent


def createTeam(firstIndex, secondIndex, isRed,
               first="ZooDummyAgent", second="ZooDummyAgent"):
    """Standard team factory matching the protocol in baseline.createTeam.

    Both agents are ZooDummyAgent — for M1 we only need to prove the base
    class wires up correctly. M2+ will replace this with real strategies.
    """
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


class ZooDummyAgent(CoreCaptureAgent):
    """Random non-STOP action selector. Smoke-test only."""

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)
        non_stop = [a for a in legal if a != Directions.STOP]
        if non_stop:
            return random.choice(non_stop)
        return Directions.STOP

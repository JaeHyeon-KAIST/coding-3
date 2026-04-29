"""
zoo_reflex_rc_tempo_capx_distract.py
------------------------------------
H3 (B as distraction) variant of CAPX.

A = ReflexRCTempoCapxAgent (unchanged — same as CAPX baseline)
B = DistractionBAgent — heads to a cap that A is NOT chasing, to split
    defender attention. If only one cap remains, both head to it.

Hypothesis (per pm47-capx-failure-conditions-algorithmic.md, H3):
- Reflex defenders patrol cap-region narrow corridors → CAPX A gets
  stuck in oscillation (Pattern A). With B also approaching a cap from
  a different direction, the two ghosts must each chase one invader →
  per-invader threat density drops → A's cap reach probability increases.

Spec: pm47 H3 experiment (no fine-tuning, game-rule exploit).

Usage:
    capture.py -r zoo_reflex_rc_tempo_capx_distract -b <defender>
"""

from __future__ import annotations

import os
from collections import deque

from captureAgents import CaptureAgent
from game import Directions, Actions

# Import CAPX A unchanged. Sharing module-level state for A→B target signaling.
from zoo_reflex_rc_tempo_capx import (
    ReflexRCTempoCapxAgent,
    _CAPX_STATE,
    _bfs_dist_map,
)


class DistractionBAgent(CaptureAgent):
    """
    B agent that picks a cap A is NOT chasing and BFS-walks toward it.

    Reads `_CAPX_STATE['committed_target']` (set by A in chooseAction) and
    targets a different cap. If A has no committed target yet, picks the
    cap farthest from B (different region from A's likely target).

    No survival gate — B is willing to "sacrifice" itself to draw a ghost.
    """

    def registerInitialState(self, gameState):
        CaptureAgent.registerInitialState(self, gameState)
        self._walls = gameState.getWalls()
        self._W = self._walls.width
        self._H = self._walls.height
        self._is_red = (self.index in gameState.getRedTeamIndices())
        print(f'[DISTRACT_INIT] idx={self.index} red={self._is_red}')

    def chooseAction(self, gameState):
        try:
            tick = gameState.data.timeleft
        except Exception:
            tick = -1

        if self._is_red:
            caps = gameState.getBlueCapsules()
        else:
            caps = gameState.getRedCapsules()

        my_pos = gameState.getAgentState(self.index).getPosition()
        if my_pos is None:
            if int(os.environ.get('DISTRACT_TRACE', '0')):
                print(f'[DISTRACT_TRACE] tick={tick} pos=None act=STOP')
            return Directions.STOP
        my_pos = (int(my_pos[0]), int(my_pos[1]))

        if not caps:
            if int(os.environ.get('DISTRACT_TRACE', '0')):
                print(f'[DISTRACT_TRACE] tick={tick} pos={my_pos} caps=0 act=STOP')
            return Directions.STOP

        a_target = _CAPX_STATE.get('committed_target') or _CAPX_STATE.get('last_target')

        if a_target is not None:
            other_caps = [c for c in caps if c != a_target]
        else:
            other_caps = caps
        if not other_caps:
            other_caps = caps

        my_dist = _bfs_dist_map(my_pos, self._walls)
        reachable = [c for c in other_caps if my_dist.get(c) is not None]
        if not reachable:
            if int(os.environ.get('DISTRACT_TRACE', '0')):
                print(f'[DISTRACT_TRACE] tick={tick} pos={my_pos} no_reach act=STOP')
            return Directions.STOP

        target = max(reachable, key=lambda c: my_dist.get(c, 0))
        target_dist = _bfs_dist_map(target, self._walls)
        legal = gameState.getLegalActions(self.index)

        best_action = Directions.STOP
        best_d = 9999
        for action in legal:
            if action == Directions.STOP:
                continue
            dx, dy = Actions.directionToVector(action)
            nx, ny = int(my_pos[0] + dx), int(my_pos[1] + dy)
            if not (0 <= nx < self._W and 0 <= ny < self._H):
                continue
            if self._walls[nx][ny]:
                continue
            d = target_dist.get((nx, ny), 9999)
            if d < best_d:
                best_d = d
                best_action = action

        if int(os.environ.get('DISTRACT_TRACE', '0')):
            print(f'[DISTRACT_TRACE] tick={tick} pos={my_pos} a_tgt={a_target} '
                  f'b_tgt={target} dist_to_b_tgt={best_d} act={best_action}')
        return best_action


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexRCTempoCapxAgent',
               second='DistractionBAgent'):
    return [
        ReflexRCTempoCapxAgent(firstIndex),
        DistractionBAgent(secondIndex),
    ]

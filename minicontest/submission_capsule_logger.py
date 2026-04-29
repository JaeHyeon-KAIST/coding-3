"""
submission_capsule_logger.py
----------------------------
Wrapper around 20200492.py's ReflexTunedAgent that adds capsule-eat and
death detection markers (matches CAPX [CAPX_CAP_EATEN]/[CAPX_A_DIED]
semantics for direct comparison).

Submission behavior is 100% unchanged — the wrapper subclasses the
agent and only adds print statements before delegating to super().

Usage:
    capture.py -r submission_capsule_logger -b <defender> -l RANDOM<N>

Spec: .omc/specs/deep-interview-pm47-submission-cap-eat-measurement.md
"""

from __future__ import annotations

import os
import importlib.util

# Load 20200492.py via importlib (file name starts with digit, can't be
# imported normally). Avoid touching the submission code.
_SUBMISSION_PATH = os.path.join(os.path.dirname(__file__), '20200492.py')
_spec = importlib.util.spec_from_file_location('submission_orig', _SUBMISSION_PATH)
_submission = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_submission)

ReflexTunedAgent = _submission.ReflexTunedAgent


# Module-level state shared across both Red agents (cap detection runs
# on every chooseAction; only emit eat event once per cap consumption).
_LOGGER_STATE: dict = {
    'prev_caps': None,         # set of cap positions on previous tick
    'a_died_emitted': set(),   # tick set where [SUBM_A_DIED] emitted
}


class CapsuleLoggerAgent(ReflexTunedAgent):
    """
    Subclass that emits [SUBM_CAP_EATEN] / [SUBM_A_DIED] markers
    without modifying the underlying agent's decision logic. All
    chooseAction returns delegate to super() unchanged.
    """

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            raw_spawn = gameState.getAgentState(self.index).getPosition()
            self._spawn = (int(raw_spawn[0]), int(raw_spawn[1])) if raw_spawn else None
        except Exception:
            self._spawn = None
        self._is_red = (self.index in gameState.getRedTeamIndices())
        self._prev_a_pos = None
        if _LOGGER_STATE['prev_caps'] is None:
            _LOGGER_STATE['prev_caps'] = set()
        print(f'[SUBM_INIT] idx={self.index} red={self._is_red} spawn={self._spawn}')

    def chooseAction(self, gameState):
        try:
            tick = gameState.data.timeleft
        except Exception:
            tick = -1

        if self._is_red:
            current_caps = set(gameState.getBlueCapsules())
        else:
            current_caps = set(gameState.getRedCapsules())

        prev_caps = _LOGGER_STATE.get('prev_caps') or set()
        eaten = prev_caps - current_caps
        if eaten:
            try:
                a_pos = gameState.getAgentState(self.index).getPosition()
                a_pos = (int(a_pos[0]), int(a_pos[1])) if a_pos else None
            except Exception:
                a_pos = None
            for cap in eaten:
                eater_idx = self._proximity_eater(gameState, cap)
                print(
                    f'[SUBM_CAP_EATEN] tick={tick} cap={cap} a_pos={a_pos}'
                    f' eater_idx={eater_idx} outcome=eaten'
                )
        _LOGGER_STATE['prev_caps'] = set(current_caps)

        # Death detection (A respawned at spawn cell with > 1 Manhattan jump)
        try:
            raw = gameState.getAgentState(self.index).getPosition()
            a_pos_now = (int(raw[0]), int(raw[1])) if raw else None
        except Exception:
            a_pos_now = None
        if (self._spawn is not None and a_pos_now is not None
                and self._prev_a_pos is not None
                and a_pos_now == self._spawn
                and self._prev_a_pos != self._spawn):
            dist = abs(a_pos_now[0] - self._prev_a_pos[0]) + abs(a_pos_now[1] - self._prev_a_pos[1])
            if dist > 1 and tick not in _LOGGER_STATE['a_died_emitted']:
                _LOGGER_STATE['a_died_emitted'].add(tick)
                print(f'[SUBM_A_DIED] tick={tick} pos={a_pos_now} agent_idx={self.index}')
        self._prev_a_pos = a_pos_now

        # 100% unchanged behavior — delegate to ReflexTunedAgent
        return super().chooseAction(gameState)

    def _proximity_eater(self, gameState, cap):
        """Find which Red agent is within Manhattan dist 1 of eaten cap."""
        try:
            red_indices = gameState.getRedTeamIndices()
            for ri in red_indices:
                rpos = gameState.getAgentPosition(ri)
                if rpos is None:
                    continue
                rpos = (int(rpos[0]), int(rpos[1]))
                if abs(rpos[0] - cap[0]) + abs(rpos[1] - cap[1]) <= 1:
                    return ri
        except Exception:
            pass
        return None


def createTeam(firstIndex, secondIndex, isRed,
               first='CapsuleLoggerAgent', second='CapsuleLoggerAgent',
               weights=None):
    """
    Two CapsuleLoggerAgent agents (each subclasses ReflexTunedAgent).
    `weights` kwarg accepted for compatibility with submission's
    createTeam signature but unused here (loaded from default A1 file).
    """
    return [
        CapsuleLoggerAgent(firstIndex),
        CapsuleLoggerAgent(secondIndex),
    ]

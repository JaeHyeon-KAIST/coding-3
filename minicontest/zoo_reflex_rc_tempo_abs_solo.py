"""pm46 v2 — A solo wrapper agent.

Red team composition:
    lower-index agent  = _CapEatTrackingABS (full A agent + cap-eat detector)
    higher-index agent = StubBAgent (STOP every turn, stays at spawn)

Rationale:
    pm46 v2 1단계 = A solo cap survival 실측. B 가 plan 에 협조하지 않는
    상태에서 A 단독으로 cap chain (cap1 → cap2 → home) 실행 가능한가?

`zoo_reflex_rc_tempo_abs.py:1045` 에서 `a_agent_index = min(team)` 으로 결정.
Lower-index 에 full ReflexRCTempoAbsAgent 두면 자동으로 A 역할 부여.
StubBAgent 는 ReflexRCTempoAbsAgent 가 아니므로 _b_plan_action 호출 X —
B 자리는 capture.py 가 보기엔 정상 agent 이지만 실질적으로 무력화.

pm46 v2 corrected detector (P1 patch):
    Existing `[ABS_A_FIRST_CAP_REACH]` is cap1-only AND fires once per game.
    Phase 0 re-baseline needs ANY cap-eat detection (`len(getBlueCapsules())`
    decrement on Red turn) + A respawn tracking → emit `[ABS_CAP_EATEN]` and
    `[ABS_A_DIED]` per occurrence. Both metrics coexist (REACH still fires
    so legacy script keeps working).

Use:
    cd minicontest
    ABS_REACH_EXIT=0 \\
        ../.venv/bin/python ../experiments/rc_tempo/pm45_single_game.py \\
        -r zoo_reflex_rc_tempo_abs_solo -b baseline -l RANDOM1 -n 1 -q
"""
from __future__ import annotations

import os
import sys

from captureAgents import CaptureAgent
from game import Directions
from zoo_reflex_rc_tempo_abs import ReflexRCTempoAbsAgent


# Module-level shim state. Reset by capture.py per-game when the module is
# re-imported; if not, stale state still produces correct deltas because we
# initialize on first chooseAction.
_SOLO_STATE = {
    'prev_caps': None,
    'prev_a_pos': None,
    'a_idx': None,
    'first_eat_tick': None,
    'a_died_within_3': False,
    'cap_eat_count': 0,
}


def _reset_solo_state():
    _SOLO_STATE['prev_caps'] = None
    _SOLO_STATE['prev_a_pos'] = None
    _SOLO_STATE['a_idx'] = None
    _SOLO_STATE['first_eat_tick'] = None
    _SOLO_STATE['a_died_within_3'] = False
    _SOLO_STATE['cap_eat_count'] = 0


class _CapEatTrackingABS(ReflexRCTempoAbsAgent):
    """ReflexRCTempoAbsAgent + per-tick cap-eat / A-respawn detector shim.

    Emits to stderr:
        [ABS_CAP_EATEN] tick=T cap=(x,y) a_pos=(x,y) eater_idx=I outcome=eaten
        [ABS_A_DIED] tick=T agent=I prev_pos=(x,y)
        [ABS_EAT_OUTCOME] first_eat_tick=T total_caps_eaten=N a_died_within_3=B
            (emitted at game end via _update_abs_postmortem hook indirectly;
             we ALSO emit on first detection of >3 ticks past first eat without death)
    """

    def chooseAction(self, gameState):
        try:
            self._emit_cap_eat_track(gameState)
        except Exception:
            pass
        return super().chooseAction(gameState)

    def _emit_cap_eat_track(self, gameState):
        try:
            is_red = self.index in gameState.getRedTeamIndices()
        except Exception:
            is_red = True
        try:
            caps_now = set(
                gameState.getBlueCapsules() if is_red
                else gameState.getRedCapsules()
            )
        except Exception:
            caps_now = set()

        try:
            timeleft = int(getattr(gameState.data, 'timeleft', 1200))
        except Exception:
            timeleft = 1200
        elapsed = max(0, 1200 - timeleft)

        try:
            a_pos_raw = gameState.getAgentPosition(self.index)
            a_pos = (int(a_pos_raw[0]), int(a_pos_raw[1])) if a_pos_raw else None
        except Exception:
            a_pos = None

        # First call of the game for this agent index: seed state.
        if _SOLO_STATE['prev_caps'] is None:
            _SOLO_STATE['prev_caps'] = caps_now
            _SOLO_STATE['prev_a_pos'] = a_pos
            _SOLO_STATE['a_idx'] = self.index
            return

        prev_caps = _SOLO_STATE['prev_caps']
        eaten = prev_caps - caps_now
        if eaten:
            for cap in eaten:
                print(
                    f'[ABS_CAP_EATEN] tick={elapsed} cap={cap} '
                    f'a_pos={a_pos} eater_idx={self.index} outcome=eaten',
                    file=sys.stderr,
                )
            sys.stderr.flush()
            _SOLO_STATE['cap_eat_count'] += len(eaten)
            if _SOLO_STATE['first_eat_tick'] is None:
                _SOLO_STATE['first_eat_tick'] = elapsed

        # A respawn detection (death-aware survival metric).
        try:
            spawn_raw = gameState.getAgentState(self.index).start.pos
            spawn = (int(spawn_raw[0]), int(spawn_raw[1])) if spawn_raw else None
        except Exception:
            spawn = None
        prev_pos = _SOLO_STATE['prev_a_pos']
        if (spawn is not None and prev_pos is not None and a_pos is not None
                and a_pos == spawn and prev_pos != spawn):
            print(
                f'[ABS_A_DIED] tick={elapsed} agent={self.index} '
                f'prev_pos={prev_pos}',
                file=sys.stderr,
            )
            sys.stderr.flush()
            first_eat = _SOLO_STATE['first_eat_tick']
            if first_eat is not None and (elapsed - first_eat) <= 3:
                _SOLO_STATE['a_died_within_3'] = True

        _SOLO_STATE['prev_caps'] = caps_now
        _SOLO_STATE['prev_a_pos'] = a_pos


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
               first='_CapEatTrackingABS', second='StubBAgent'):
    """Lower-index → full A agent (with cap-eat shim). Higher-index → stub B."""
    # Reset module-level shim state at team construction — capture.py creates
    # one team per game, so this gives us a clean start per game.
    _reset_solo_state()
    if firstIndex < secondIndex:
        return [_CapEatTrackingABS(firstIndex), StubBAgent(secondIndex)]
    return [StubBAgent(firstIndex), _CapEatTrackingABS(secondIndex)]


# Backward-compatibility alias for any caller that imports the old class name.
# (zoo_reflex_rc_tempo_abs_solo previously exposed only StubBAgent + createTeam.)
ReflexRCTempoAbsAgent_solo = _CapEatTrackingABS

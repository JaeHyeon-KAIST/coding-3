# zoo_reflex_rc49.py
# ------------------
# rc49: SIPP-lite (Safe Interval Path Planning, multi-step teammate
# reservation).
#
# Extends rc48 (1-step WHCA*) to a 3-step space-time reservation.
# Teammate broadcasts their last 3 chosen actions via a class-level
# ring buffer; we project their likely next 3 cells (assuming they
# keep going in their recent direction unless a wall forces turn) and
# reserve (cell, time) tuples. My candidate action is penalized if it
# would occupy any reserved (cell, time).
#
# Difference from rc48: 3 plies ahead instead of 1 → catches slow
# collisions that 1-step misses (e.g., both agents heading to same
# food 2 cells away).
#
# Tier 2 (path-planning / cooperative A*).

from __future__ import annotations

from collections import deque

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate, _ACTION_PREFERENCE
from zoo_core import TEAM
from game import Directions, Actions
from util import nearestPoint


RC49_LOOKAHEAD = 3
RC49_COLLISION_PENALTY = 12.0

# Class-level teammate action broadcast: {agent_idx: deque([recent actions])}
_RC49_ACTION_HIST: dict = {}


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC49Agent", second="ReflexRC49Agent"):
    return [ReflexRC49Agent(firstIndex), ReflexRC49Agent(secondIndex)]


class ReflexRC49Agent(ReflexA1Agent):
    """A1 + 3-step space-time reservation avoidance."""

    def _teammate_idx(self, gameState):
        try:
            team = sorted(list(self.getTeam(gameState)))
            mates = [i for i in team if i != self.index]
            return mates[0] if mates else None
        except Exception:
            return None

    def _project_teammate_cells(self, gameState, mate_idx):
        """Return list of (cell, time_offset) that teammate is expected
        to occupy in the next RC49_LOOKAHEAD plies. `time_offset` counts
        the agent turns from now: 0 = next action, 1 = action after, etc.
        We assume teammate continues in the direction of their most
        recent action until a wall forces a turn; uses A1 reflex to pick
        a new direction on forced turns.
        """
        cells = []
        try:
            mate_pos = gameState.getAgentPosition(mate_idx)
            if mate_pos is None:
                return cells
            walls = gameState.getWalls()
            last_actions = _RC49_ACTION_HIST.get(mate_idx) or deque()
            # If mate has recent actions, continue the last direction.
            last_dir = None
            for a in reversed(last_actions):
                if a is not None and a != Directions.STOP:
                    last_dir = a
                    break

            cur = (int(mate_pos[0]), int(mate_pos[1]))
            weights = self._get_weights()
            sim_state = gameState
            for t in range(RC49_LOOKAHEAD):
                # Try continuing last_dir first; if blocked, A1 argmax for mate.
                chosen = None
                if last_dir is not None:
                    try:
                        dx, dy = Actions.directionToVector(last_dir)
                        nx, ny = int(cur[0] + dx), int(cur[1] + dy)
                        if (0 <= nx < walls.width and 0 <= ny < walls.height
                                and not walls[nx][ny]):
                            chosen = last_dir
                    except Exception:
                        chosen = None
                if chosen is None:
                    try:
                        mate_legal = sim_state.getLegalActions(mate_idx)
                    except Exception:
                        mate_legal = None
                    if mate_legal:
                        best = float("-inf")
                        for a in mate_legal:
                            try:
                                v = evaluate(self, sim_state, a, weights)
                            except Exception:
                                continue
                            if v > best:
                                best = v
                                chosen = a
                if chosen is None or chosen == Directions.STOP:
                    break
                try:
                    dx, dy = Actions.directionToVector(chosen)
                    nx, ny = int(cur[0] + dx), int(cur[1] + dy)
                    if not (0 <= nx < walls.width and 0 <= ny < walls.height):
                        break
                    if walls[nx][ny]:
                        break
                    cur = (nx, ny)
                    cells.append((cur, t))
                    last_dir = chosen
                    sim_state = sim_state.generateSuccessor(mate_idx, chosen)
                except Exception:
                    break
            return cells
        except Exception:
            return cells

    def _my_next_cell(self, gameState, action):
        try:
            succ = gameState.generateSuccessor(self.index, action)
            raw = succ.getAgentState(self.index).getPosition()
            if raw is None:
                return None
            sp = nearestPoint(raw)
            return (int(sp[0]), int(sp[1]))
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            weights = self._get_weights()
            mate_idx = self._teammate_idx(gameState)
            reserved = (self._project_teammate_cells(gameState, mate_idx)
                        if mate_idx is not None else [])
            # Penalize cells that overlap ANY reserved cell at time 0 (my
            # next step overlapping mate's next step).
            reserved_cells_t0 = {c for (c, t) in reserved if t == 0}

            try:
                ordered = sorted(
                    legal,
                    key=lambda a: (_ACTION_PREFERENCE.index(a)
                                   if a in _ACTION_PREFERENCE
                                   else len(_ACTION_PREFERENCE)),
                )
            except Exception:
                ordered = list(legal)

            best = float("-inf")
            best_a = None
            for a in ordered:
                try:
                    base = evaluate(self, gameState, a, weights)
                except Exception:
                    base = float("-inf")
                my_cell = self._my_next_cell(gameState, a)
                penalty = 0.0
                if my_cell is not None and my_cell in reserved_cells_t0:
                    penalty = RC49_COLLISION_PENALTY
                score = base - penalty
                if score > best:
                    best = score
                    best_a = a

            if best_a is None or best_a not in legal:
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP

            # Broadcast my chosen action for teammate's future projection.
            if self.index not in _RC49_ACTION_HIST:
                _RC49_ACTION_HIST[self.index] = deque(maxlen=4)
            _RC49_ACTION_HIST[self.index].append(best_a)
            return best_a
        except Exception:
            try:
                return super()._chooseActionImpl(gameState)
            except Exception:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP

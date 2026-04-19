# zoo_reflex_rc27.py
# ------------------
# rc27: Stigmergy / virtual-pheromone overlay on A1 champion.
#
# Insects coordinate by leaving pheromones on paths they travel. The maze
# equivalent: our team leaves a decaying "visit marker" on each cell we
# step through. When choosing the next action, we prefer cells with LOW
# pheromone concentration (un-trodden) — this yields natural dispersion
# AND anti-oscillation without the rc18-style hard penalties that blew
# up in smoke (rc18 dropped for aggression).
#
# A global pheromone grid is maintained on the TEAM singleton, decayed
# each turn by a multiplicative factor and incremented at each agent's
# current position. All sensor access is defensive — on any failure the
# agent falls through to pure A1 behavior.
#
# The pheromone is added as a single new feature `f_pheromone` with a
# NEGATIVE weight: higher pheromone at successor position → lower score.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import extract_features as _base_extract_features
from game import Directions


RC27_DECAY = 0.92           # per-tick multiplicative decay
RC27_DEPOSIT = 1.0          # amount added at agent's current cell
RC27_F_WEIGHT = -8.0        # negative: pheromone = bad (already visited)


def _ensure_pher_state(gameState):
    """Initialize TEAM.rc27_phero grid if not present. Shape = (W, H)."""
    try:
        if hasattr(TEAM, "rc27_phero") and TEAM.rc27_phero is not None:
            return
        walls = gameState.getWalls()
        W, H = walls.width, walls.height
        # 2D list of floats; O(W·H) memory (≈32·16 = 512 cells on defaults).
        TEAM.rc27_phero = [[0.0 for _ in range(H)] for _ in range(W)]
        TEAM.rc27_last_tick = -1
    except Exception:
        pass


def _advance_phero_if_new_tick(agent, gameState):
    """Decay + deposit once per game tick (shared across our 2 agents)."""
    try:
        _ensure_pher_state(gameState)
        if TEAM.rc27_phero is None:
            return
        timeleft = int(getattr(gameState.data, "timeleft", 1200) or 1200)
        tick = 1200 - timeleft
        if tick <= TEAM.rc27_last_tick:
            return
        TEAM.rc27_last_tick = tick

        # Decay globally.
        phero = TEAM.rc27_phero
        W = len(phero)
        if W > 0:
            H = len(phero[0])
            for x in range(W):
                row = phero[x]
                for y in range(H):
                    row[y] *= RC27_DECAY

        # Deposit at each of our current positions.
        for idx in agent.getTeam(gameState):
            try:
                p = gameState.getAgentPosition(idx)
                if p is None:
                    continue
                x, y = int(p[0]), int(p[1])
                if 0 <= x < W and 0 <= y < H:
                    phero[x][y] += RC27_DEPOSIT
            except Exception:
                continue
    except Exception:
        pass


class ReflexRC27Agent(ReflexA1Agent):
    """A1 champion + team pheromone-avoidance overlay."""

    def _chooseActionImpl(self, gameState):
        _advance_phero_if_new_tick(self, gameState)
        weights = self._get_weights()
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        try:
            from zoo_features import _ACTION_PREFERENCE
            ordered = sorted(
                legal,
                key=lambda a: (_ACTION_PREFERENCE.index(a)
                               if a in _ACTION_PREFERENCE
                               else len(_ACTION_PREFERENCE)),
            )
        except Exception:
            ordered = list(legal)

        best_score = float("-inf")
        best_action = None
        phero = getattr(TEAM, "rc27_phero", None)
        for action in ordered:
            try:
                feats = _base_extract_features(self, gameState, action)
                score = sum(weights.get(k, 0.0) * v for k, v in feats.items())
                # Successor-position pheromone lookup.
                if phero is not None:
                    try:
                        from util import nearestPoint
                        succ = gameState.generateSuccessor(self.index, action)
                        raw = succ.getAgentState(self.index).getPosition()
                        if raw is not None:
                            sp = nearestPoint(raw)
                            sx, sy = int(sp[0]), int(sp[1])
                            if 0 <= sx < len(phero) and 0 <= sy < len(phero[0]):
                                score += RC27_F_WEIGHT * phero[sx][sy]
                    except Exception:
                        pass
            except Exception:
                score = float("-inf")
            if score > best_score:
                best_score = score
                best_action = action

        if best_action is None or best_action not in legal:
            non_stop = [a for a in legal if a != Directions.STOP]
            return non_stop[0] if non_stop else Directions.STOP
        return best_action


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC27Agent", second="ReflexRC27Agent"):
    return [ReflexRC27Agent(firstIndex), ReflexRC27Agent(secondIndex)]

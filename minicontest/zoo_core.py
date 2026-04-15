# zoo_core.py
# -----------
# Shared base agent for the dev "zoo". Concretely the equivalent of the
# `experiments/zoo/_core.py` module described in STRATEGY.md, but located
# inside `minicontest/` so that capture.py's `-r {name}` import mechanism
# (which imports `{name}.py` from CWD) can discover both `zoo_core` itself
# and any concrete `zoo_<variant>.py` agent that inherits from it.
#
# Submission-time flattening (M9) inlines this file's classes/methods into
# the per-file `your_*.py` artifacts so the final submission satisfies the
# single-file constraint. During development, every zoo agent imports
# CoreCaptureAgent and TEAM from here.
#
# This module is NOT one of the "do-not-modify" framework files, but it
# does NOT modify any of them either.

from __future__ import annotations

import random
import time
from collections import deque

from captureAgents import CaptureAgent
from game import Directions
from util import TimeoutFunctionException

# ---------------------------------------------------------------------------
# Module-level constants (PRE-CALIBRATION values)
# ---------------------------------------------------------------------------
# pre-calibration value; will be updated by M7.5 artifact. Algorithmic bounds
# (MAX_ITERS/MAX_DEPTH) are the primary time controller during M1-M7.
MOVE_BUDGET = 0.80

# pre-calibration value; will be updated by M7.5 artifact. Algorithmic bounds
# (MAX_ITERS/MAX_DEPTH) are the primary time controller during M1-M7.
MAX_ITERS = 1000
# pre-calibration value; will be updated by M7.5 artifact. Algorithmic bounds
# (MAX_ITERS/MAX_DEPTH) are the primary time controller during M1-M7.
MAX_DEPTH = 3
# pre-calibration value; will be updated by M7.5 artifact. Algorithmic bounds
# (MAX_ITERS/MAX_DEPTH) are the primary time controller during M1-M7.
ROLLOUT_DEPTH = 20

# Layout-size guard for bottleneck precomputation: skip if too many open cells.
_BOTTLENECK_MAX_CELLS = 500

# APSP timing thresholds (seconds). Soft warn only — never raise.
_APSP_WARN_SEC = 8.0


# ---------------------------------------------------------------------------
# TeamGlobalState — module-level singleton shared between teammates.
# Both teammates run inside the same process (CS188 framework, no IPC), and
# turns are sequential, so the same Python object is observable from both
# `chooseAction` calls without any synchronization.
# ---------------------------------------------------------------------------
class TeamGlobalState:
    """Mutable shared state for the two teammate agents.

    All mutations happen during sequential `chooseAction` calls — there is
    never concurrent access (CS188 framework owns the turn loop). All public
    methods MUST be exception-safe; callers cannot afford a crash in the
    coordination layer.
    """

    def __init__(self):
        self.initialized = False
        # agent_index -> "OFFENSE" | "DEFENSE"
        self.role = {}
        # agent_index -> (x, y, tick)
        self.last_seen_enemy = {}
        # list of (food_pos, tick) for food eaten by us
        self.food_eaten_by_us = []
        # capsule_pos -> tick when eaten
        self.capsule_eaten_tick = {}
        # agent_index -> int counter for hysteresis
        self.switch_counter = {}
        # global tick counter (incremented by either teammate)
        self.tick = 0

    def reset(self, gameState):
        """Idempotent reset — initialize role assignment exactly once per game.

        Default role assignment: lower-index agent → OFFENSE,
        higher-index agent → DEFENSE. Both teammates read the same dict
        so the two agents auto-agree without any messaging.
        """
        if self.initialized:
            return
        try:
            # Determine which side we are on by looking at the first agent
            # whose `red` field happens to be queryable. We do not depend on
            # `self` here — the singleton has no agent context — so we use
            # the gameState directly.
            red_indices = list(gameState.getRedTeamIndices())
            blue_indices = list(gameState.getBlueTeamIndices())
            for indices in (red_indices, blue_indices):
                if not indices:
                    continue
                sorted_idx = sorted(indices)
                # lower-index agents OFFENSE, higher DEFENSE
                for rank, idx in enumerate(sorted_idx):
                    self.role[idx] = "OFFENSE" if rank == 0 else "DEFENSE"
                    self.switch_counter[idx] = 0
                    self.last_seen_enemy[idx] = None
            self.tick = 0
            self.food_eaten_by_us = []
            self.capsule_eaten_tick = {}
            self.initialized = True
        except Exception:
            # Defensive — if anything goes wrong building defaults, at least
            # mark initialized so we do not keep retrying. Subclass code is
            # expected to fall back to its own role logic if `role` is empty.
            self.initialized = True

    def force_reinit(self):
        """Hard reset — wipe all state. Called from registerInitialState's
        fallback path when `reset()` itself raised."""
        self.__init__()


# Module-level singleton — shared across both teammate agents because they
# import the same `zoo_core` module.
TEAM = TeamGlobalState()


# ---------------------------------------------------------------------------
# Weight-override protocol (M4b-2, 2026-04-15 pm8)
# ---------------------------------------------------------------------------
# During CEM evolution (evolve.py M5/M6), each candidate genome encodes a
# fresh (w_off, w_def, params) set that must be injected into a zoo agent
# at runtime. We piggyback on capture.py's existing `--redOpts` / `--blueOpts`
# channel: the tournament passes `weights=<json_path>` as an agent arg; the
# agent's `createTeam(...)` forwards that to this loader, and the agent's
# `_get_weights()` returns the loaded dict instead of the seed weights.
#
# JSON schema:
#     { "w_off": {feature_name: weight, ...},
#       "w_def": {feature_name: weight, ...} | null,
#       "params": {param_name: value, ...} }
#
# Phase 2a of evolution uses a shared W (w_def == null → agents fall back to
# w_off for both OFFENSE and DEFENSE roles). Phase 2b splits W_OFF ≠ W_DEF
# and supplies both.
def load_weights_override(spec):
    """Load a weight override from a JSON-file path or from a pre-parsed dict.

    Returns a dict with the canonical keys `w_off`, `w_def`, `params`. Keys
    missing in the source are filled with a safe default (`{}` or `None`).
    Never raises: on ANY failure (bad path, malformed JSON, wrong type) we
    return an empty override so the agent cleanly falls back to seed weights.
    The 15s registerInitialState budget cannot afford a crash here.
    """
    import json
    empty = {"w_off": {}, "w_def": None, "params": {}}
    try:
        if isinstance(spec, dict):
            data = spec
        else:
            with open(spec) as f:
                data = json.load(f)
        if not isinstance(data, dict):
            return empty
        w_off_raw = data.get("w_off") or {}
        w_def_raw = data.get("w_def")
        params_raw = data.get("params") or {}
        return {
            "w_off": dict(w_off_raw) if isinstance(w_off_raw, dict) else {},
            "w_def": (dict(w_def_raw) if isinstance(w_def_raw, dict) else None),
            "params": dict(params_raw) if isinstance(params_raw, dict) else {},
        }
    except Exception:
        return empty


# ---------------------------------------------------------------------------
# CoreCaptureAgent — shared base for every zoo agent.
# ---------------------------------------------------------------------------
class CoreCaptureAgent(CaptureAgent):
    """Crash-proof base agent.

    Subclasses MUST override `_chooseActionImpl(gameState)`. Everything else
    (timing, state snapshot, distance lookups, fallback) is provided here.

    Hard guarantees:
      * `registerInitialState` never raises (every step independently
        guarded). A 15s init crash would forfeit the game.
      * `chooseAction` never raises EXCEPT for `TimeoutFunctionException`,
        which we deliberately re-raise so the framework's SIGALRM
        bookkeeping (warning counter, forfeit) stays correct.
      * `_safeFallback` never raises.
    """

    # ----- init -------------------------------------------------------------

    def __init__(self, index, timeForComputing=0.1):
        # Call CaptureAgent.__init__ (sets self.index, self.distancer=None,
        # observationHistory=[], etc.). Mirrors the baseline pattern.
        CaptureAgent.__init__(self, index, timeForComputing)

        # Per-agent state populated in registerInitialState. Each has a safe
        # default in case its precompute step raises.
        self.start = None
        self.apsp = None  # dict[(pos1, pos2)] -> int, or None → fallback to distancer
        self.bottlenecks = frozenset()
        self.deadEnds = frozenset()
        self.homeFrontier = []
        self.turn_start = 0.0

    # ----- registerInitialState (15s budget; crash-proof) -------------------

    def registerInitialState(self, gameState):
        """Heavy precompute, every step independently guarded.

        Steps (order matters for fallbacks):
          1. CaptureAgent.registerInitialState — populates self.distancer.
          2. self.start (agent spawn).
          3. APSP dict — O(1) maze-distance lookups.
          4. Bottlenecks (frozenset of articulation cells).
          5. Dead-ends (frozenset).
          6. Home-frontier (list of border cells on our side).
          7. TEAM singleton reset.
        """
        # 1) Base distancer + standard CaptureAgent setup.
        try:
            CaptureAgent.registerInitialState(self, gameState)
        except Exception:
            pass

        # 2) Spawn point.
        try:
            self.start = gameState.getAgentPosition(self.index)
        except Exception:
            self.start = None

        # 3) APSP — O(N^2) memory but worth it for O(1) per-move lookups.
        try:
            self.apsp = self._precomputeAPSP(gameState)
        except Exception:
            self.apsp = None

        # 4) Bottlenecks — articulation-point approximation (cheap BFS).
        try:
            self.bottlenecks = self._computeBottlenecks(gameState)
        except Exception:
            self.bottlenecks = frozenset()

        # 5) Dead-ends — single-exit cells with depth >= 3 from any junction.
        try:
            self.deadEnds = self._precomputeDeadEnds(gameState)
        except Exception:
            self.deadEnds = frozenset()

        # 6) Home-frontier — cells on our side adjacent to the divider.
        try:
            self.homeFrontier = self._computeHomeFrontier(gameState)
        except Exception:
            self.homeFrontier = []

        # 7) Team singleton — idempotent; safe to call from both teammates.
        try:
            TEAM.reset(gameState)
        except Exception:
            try:
                TEAM.force_reinit()
            except Exception:
                pass

        # NEVER raise from here.

    # ----- chooseAction (timeout-preserving two-layer wrap) ----------------

    def chooseAction(self, gameState):
        """Crash-proof entry point. Returns a legal action or STOP.

        TimeoutFunctionException is the framework's SIGALRM signal — we MUST
        re-raise it so the framework's warning counter and forfeit logic
        work correctly.
        """
        self.turn_start = time.time()
        try:
            action = self._chooseActionImpl(gameState)
            legal = gameState.getLegalActions(self.index)
            if action not in legal:
                action = self._safeFallback(gameState, legal)
            return action
        except TimeoutFunctionException:
            raise  # CRITICAL: let framework see it
        except Exception:
            try:
                legal = gameState.getLegalActions(self.index)
                fallback = self._safeFallback(gameState, legal)
                if fallback in legal:
                    return fallback
                non_stop = [a for a in legal if a != Directions.STOP]
                return random.choice(non_stop) if non_stop else Directions.STOP
            except TimeoutFunctionException:
                raise
            except Exception:
                return Directions.STOP

    def _chooseActionImpl(self, gameState):
        """Subclasses MUST override. Returns a legal action."""
        raise NotImplementedError(
            "CoreCaptureAgent subclasses must implement _chooseActionImpl"
        )

    def _safeFallback(self, gameState, legal):
        """Pick a non-STOP legal action, else STOP. NEVER raises."""
        try:
            if not legal:
                return Directions.STOP
            non_stop = [a for a in legal if a != Directions.STOP]
            if non_stop:
                return random.choice(non_stop)
            return Directions.STOP
        except Exception:
            return Directions.STOP

    # ----- helpers ----------------------------------------------------------

    def snapshot(self, gameState):
        """Compute a per-turn dict of common features. Computed once per
        chooseAction so search-evaluators can read a stable snapshot.

        All field accesses are guarded; missing data degrades to a sensible
        default rather than raising.
        """
        snap = {
            "myPos": None,
            "myState": None,
            "isPacman": False,
            "scaredTimer": 0,
            "numCarrying": 0,
            "foodList": [],
            "defendFoodList": [],
            "capsuleList": [],
            "opponentPositions": {},  # idx -> (x, y) or None
            "teamPositions": {},      # idx -> (x, y) or None
            "walls": None,
        }
        try:
            myState = gameState.getAgentState(self.index)
            snap["myState"] = myState
            try:
                pos = myState.getPosition()
                if pos is not None:
                    snap["myPos"] = (int(pos[0]), int(pos[1]))
            except Exception:
                snap["myPos"] = None
            snap["isPacman"] = bool(getattr(myState, "isPacman", False))
            snap["scaredTimer"] = int(getattr(myState, "scaredTimer", 0) or 0)
            snap["numCarrying"] = int(getattr(myState, "numCarrying", 0) or 0)
        except Exception:
            pass

        try:
            snap["foodList"] = self.getFood(gameState).asList()
        except Exception:
            snap["foodList"] = []

        try:
            snap["defendFoodList"] = self.getFoodYouAreDefending(gameState).asList()
        except Exception:
            snap["defendFoodList"] = []

        try:
            snap["capsuleList"] = list(self.getCapsules(gameState))
        except Exception:
            snap["capsuleList"] = []

        try:
            for idx in self.getOpponents(gameState):
                try:
                    snap["opponentPositions"][idx] = gameState.getAgentPosition(idx)
                except Exception:
                    snap["opponentPositions"][idx] = None
        except Exception:
            pass

        try:
            for idx in self.getTeam(gameState):
                try:
                    snap["teamPositions"][idx] = gameState.getAgentPosition(idx)
                except Exception:
                    snap["teamPositions"][idx] = None
        except Exception:
            pass

        try:
            snap["walls"] = gameState.getWalls()  # reference, not copy
        except Exception:
            snap["walls"] = None

        return snap

    def getMazeDistance(self, pos1, pos2):
        """O(1) APSP lookup if available, else fall back to base distancer."""
        try:
            if self.apsp is not None:
                d = self.apsp.get((pos1, pos2))
                if d is not None:
                    return d
        except Exception:
            pass
        try:
            return self.distancer.getDistance(pos1, pos2)
        except Exception:
            # Last-resort manhattan, mostly so callers do not crash on
            # unreachable / odd positions.
            try:
                return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
            except Exception:
                return 0

    # ----- precompute -------------------------------------------------------

    def _precomputeAPSP(self, gameState):
        """All-Pairs Shortest Path via N independent BFS runs from every
        non-wall cell. Returns dict[(pos1, pos2)] -> int.

        Symmetric — we only BFS from each source once and rely on the
        unweighted-graph property `d(a,b) == d(b,a)`.
        """
        walls = gameState.getWalls()
        width, height = walls.width, walls.height

        # Open cells (non-wall).
        cells = []
        for x in range(width):
            for y in range(height):
                if not walls[x][y]:
                    cells.append((x, y))

        apsp = {}
        t0 = time.time()
        for src in cells:
            # BFS
            visited = {src: 0}
            queue = deque([src])
            while queue:
                cx, cy = queue.popleft()
                d = visited[(cx, cy)]
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if nx < 0 or ny < 0 or nx >= width or ny >= height:
                        continue
                    if walls[nx][ny]:
                        continue
                    if (nx, ny) in visited:
                        continue
                    visited[(nx, ny)] = d + 1
                    queue.append((nx, ny))
            for dst, d in visited.items():
                apsp[(src, dst)] = d

        elapsed = time.time() - t0
        if elapsed > _APSP_WARN_SEC:
            # Soft warning only — never raise from precompute.
            try:
                print(
                    "[zoo_core] WARNING: APSP precompute took %.2fs "
                    "(>%.1fs threshold) on %dx%d layout (%d open cells)"
                    % (elapsed, _APSP_WARN_SEC, width, height, len(cells))
                )
            except Exception:
                pass
        return apsp

    def _computeBottlenecks(self, gameState):
        """Articulation-point approximation: a non-wall cell is a
        "bottleneck" if removing it disconnects its 4-neighbors.

        We only check cells with >= 2 non-wall neighbors. For each such
        cell, run BFS from one neighbor with the cell itself blocked, and
        verify all other non-wall neighbors are reachable.

        Skipped on layouts with too many cells (cost guard).
        """
        walls = gameState.getWalls()
        width, height = walls.width, walls.height

        open_cells = []
        for x in range(width):
            for y in range(height):
                if not walls[x][y]:
                    open_cells.append((x, y))

        if len(open_cells) > _BOTTLENECK_MAX_CELLS:
            return frozenset()

        bottlenecks = set()
        for cx, cy in open_cells:
            neighbors = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height and not walls[nx][ny]:
                    neighbors.append((nx, ny))
            if len(neighbors) < 2:
                continue
            # BFS from neighbors[0] with (cx, cy) blocked.
            blocked = (cx, cy)
            src = neighbors[0]
            seen = {src}
            queue = deque([src])
            while queue:
                ux, uy = queue.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    vx, vy = ux + dx, uy + dy
                    if vx < 0 or vy < 0 or vx >= width or vy >= height:
                        continue
                    if walls[vx][vy]:
                        continue
                    if (vx, vy) == blocked:
                        continue
                    if (vx, vy) in seen:
                        continue
                    seen.add((vx, vy))
                    queue.append((vx, vy))
            # If any other neighbor is unreachable, (cx, cy) is a bottleneck.
            for n in neighbors[1:]:
                if n not in seen:
                    bottlenecks.add((cx, cy))
                    break
        return frozenset(bottlenecks)

    def _precomputeDeadEnds(self, gameState):
        """Cells with exactly one non-wall neighbor (true dead-ends), then
        extend backward along single-exit corridors as long as the corridor
        depth from the original tip is >= 3. Returns frozenset of all such
        cells (the tip and the corridor it sits in).

        Heuristic: the plan calls for "one non-wall neighbor and depth >= 3
        from nearest junction." We approximate by collecting any cell that
        sits on a length->=3 dead-end stub.
        """
        walls = gameState.getWalls()
        width, height = walls.width, walls.height

        def neighbors(p):
            x, y = p
            out = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and not walls[nx][ny]:
                    out.append((nx, ny))
            return out

        # Find tips (cells with exactly one open neighbor).
        tips = []
        for x in range(width):
            for y in range(height):
                if walls[x][y]:
                    continue
                if len(neighbors((x, y))) == 1:
                    tips.append((x, y))

        dead_cells = set()
        for tip in tips:
            chain = [tip]
            prev = None
            cur = tip
            # Walk inward through degree-2 corridor cells.
            while True:
                nbrs = [n for n in neighbors(cur) if n != prev]
                if len(nbrs) != 1:
                    break
                nxt = nbrs[0]
                # Stop when we reach a junction (degree >= 3 looking outward
                # from the corridor side). A junction is a cell with >= 3
                # open neighbors total.
                if len(neighbors(nxt)) >= 3:
                    break
                prev, cur = cur, nxt
                chain.append(cur)
            if len(chain) >= 3:
                dead_cells.update(chain)
        return frozenset(dead_cells)

    def _computeHomeFrontier(self, gameState):
        """List of cells on our side of the dividing column that are
        adjacent to the dividing column itself (the cells we patrol /
        retreat through)."""
        walls = gameState.getWalls()
        width, height = walls.width, walls.height
        # Dividing column convention from capture.py:
        #   isRed pos: pos.x < width / 2
        # so red side cells are x in [0, width//2 - 1]; the home-frontier
        # column for red is width//2 - 1, for blue it is width // 2.
        if self.red:
            frontier_x = width // 2 - 1
        else:
            frontier_x = width // 2
        if frontier_x < 0 or frontier_x >= width:
            return []
        cells = []
        for y in range(height):
            if not walls[frontier_x][y]:
                cells.append((frontier_x, y))
        return cells

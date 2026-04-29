from __future__ import annotations

# zoo_reflex_rc_tempo_capx.py
# ----------------------------
# omc-pm46-v2: Capsule-Only Attacker eXperimental (CAPX)
#
# Sole objective: A reaches at least 1 capsule ALIVE.
# No food, no scoring, no deposit, no return-home, no B-coord.
#
# Import whitelist (HARD RULE — only these 4 helpers from ABS module):
#   _grid_bfs_distance, _bfs_grid_path, _dir_step, _bfs_first_step_to
# Any class/wildcard/global from ABS triggers _ABS_TEAM init side-effect -> FORBIDDEN.

import os
import sys
import time
import math
import heapq
from collections import deque

from captureAgents import CaptureAgent
from game import Directions, Actions

from zoo_reflex_rc_tempo_abs import (
    _grid_bfs_distance,
    _bfs_grid_path,
    _dir_step,
    _bfs_first_step_to,
)

# ---------------------------------------------------------------------------
# Module-level state — only _CAPX_STATE, never _ABS_TEAM
# ---------------------------------------------------------------------------

_CAPX_STATE: dict = {
    'astar_cache': {},         # (a_pos, tgt) -> path  (cleared per tick)
    'astar_cache_tick': -1,
    'last_target': None,
    'committed_target': None,
    'prev_caps': None,         # set of cap positions on previous tick
    'prev_blue_caps_seen': None,
    'prev_a_pos': None,        # for respawn / death detection
    'a_died_emitted': set(),   # tick set where [CAPX_A_DIED] emitted
    'wall_times': [],          # recent chooseAction wall times (ms)
    'tick_counter': 0,
    # H1: defender behavior model — per-defender deque of last K=20 visited cells
    'def_recent_visits': {},   # {d_idx: deque[cell, ...]} — see chooseAction
    'def_recent_window': 20,   # rolling window size
}

# ---------------------------------------------------------------------------
# Env-knob reader (called once in registerInitialState)
# ---------------------------------------------------------------------------

def _read_capx_env() -> dict:
    def _int(name, default):
        try:
            return int(os.environ.get(name, default))
        except Exception:
            return default

    def _float(name, default):
        try:
            return float(os.environ.get(name, default))
        except Exception:
            return default

    return {
        'min_margin':           _int('CAPX_MIN_MARGIN', 0),
        'hard_abandon_margin':  _int('CAPX_HARD_ABANDON_MARGIN', -1),
        'detour_budget':        min(_int('CAPX_DETOUR_BUDGET', 4), 8),
        'astar_node_cap':       _int('CAPX_ASTAR_NODE_CAP', 2000),
        'close_penalty':        _int('CAPX_CLOSE_PENALTY', 3),
        'warm_penalty':         _int('CAPX_WARM_PENALTY', 1),
        'approach_mode':        _int('CAPX_APPROACH_MODE', 1),
        'min_psurvive':         _float('CAPX_MIN_PSURVIVE', 0.2),
        'exit_on_eat':          _int('CAPX_EXIT_ON_EAT', 0),
        'trace':                _int('CAPX_TRACE', 0),
        'sigmoid_scale':        _float('CAPX_SIGMOID_SCALE', 1.5),
        # Patch (post-Phase-1 design fix): gate evaluates near-future horizon
        # instead of full path. Full-path margin always negative for long
        # paths (defender races worst-case to far cells), causing universal
        # REJECT. Near-horizon (default 8 steps) reflects what the agent can
        # actually react to; far-future cells get re-evaluated when the
        # agent gets closer (cache cleared per tick).
        'gate_horizon':         _int('CAPX_GATE_HORIZON', 8),
        'gate_use_full':        _int('CAPX_GATE_USE_FULL', 0),
        # CCG S1: A* edge_cost ignores threat for cells beyond this step horizon
        # (sync with gate_horizon by default — fixes A*↔gate inconsistency).
        # Set high (e.g. 999) to revert to old full-path-pessimistic A*.
        'astar_horizon':        _int('CAPX_ASTAR_HORIZON', _int('CAPX_GATE_HORIZON', 8)),
        # CCG S2 (scope-narrow v2 — post Phase A): own-side safe mask now
        # applies ONLY to A* planning (edge_cost) and ranker (_p_survive),
        # NOT to gate.margin_at or _safest_step_toward (those need actual
        # adversary distance to avoid border-rush). Default ON after redesign.
        'asymmetric_threat':    _int('CAPX_ASYMMETRIC_THREAT', 1),
        # H1 (pm47): defender behavior model. When ON, A* edge_cost only
        # applies threat to cells the defender has actually visited in the
        # last K=20 ticks. Cells the defender never patrols → threat=0
        # (defender unlikely to suddenly be there). Reads
        # _CAPX_STATE['def_recent_visits'] populated each tick by chooseAction.
        # Default OFF; algorithmic ablation per pm47 H1 hypothesis.
        'use_def_history':      _int('CAPX_USE_DEF_HISTORY', 0),
        # CCG S3: _p_survive enumerates path[1:] (skip current cell where A is
        # already alive). 0 reverts to old enumerate(path) including i=0.
        'psurvive_skip_current': _int('CAPX_PSURVIVE_SKIP_CURRENT', 1),
    }

# ---------------------------------------------------------------------------
# BFS flood-fill: build dist map from a single source across walkable grid
# ---------------------------------------------------------------------------

def _bfs_dist_map(src: tuple, walls) -> dict:
    """BFS from src, returns {cell: dist} for all reachable cells."""
    W, H = walls.width, walls.height
    dist = {src: 0}
    q = deque([src])
    while q:
        x, y = q.popleft()
        d = dist[(x, y)]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and not walls[nx][ny]:
                n = (nx, ny)
                if n not in dist:
                    dist[n] = d + 1
                    q.append(n)
    return dist

# ---------------------------------------------------------------------------
# CCG S2: home-side mask helper. A is non-killable while a ghost on its own
# side. `knobs` must carry 'is_red' (bool) and 'mid_x' (int = walls.width//2)
# from registerInitialState. Returns True if `cell` is on attacker's home side.
# ---------------------------------------------------------------------------

def _is_own_side(cell: tuple, knobs: dict) -> bool:
    if not knobs.get('asymmetric_threat', 1):
        return False  # disabled — treat all cells as opp side (full threat)
    mid = knobs.get('mid_x')
    if mid is None:
        return False
    if knobs.get('is_red', True):
        return cell[0] < mid
    return cell[0] >= mid

# ---------------------------------------------------------------------------
# Defender-aware A* path planner (§5.2)
# ---------------------------------------------------------------------------

def _astar_capx(
    start: tuple,
    target: tuple,
    walls,
    defender_dist_map: dict,
    knobs: dict,
) -> list | None:
    """
    A* from start to target on walkable grid with defender threat costs.
    Returns list of cells [start, ..., target] or None if infeasible/overflow.
    Respects:
      - max path length = direct_bfs_dist + detour_budget (hard cap 8)
      - max node expansions = astar_node_cap
    On overflow -> returns None (caller uses direct BFS fallback).
    """
    if start == target:
        return [start]

    direct_dist = _grid_bfs_distance(start, target, walls)
    if direct_dist is None:
        return None

    K = knobs['detour_budget']
    W2 = knobs['close_penalty']
    W3 = knobs['warm_penalty']
    node_cap = knobs['astar_node_cap']
    max_path_len = direct_dist + K

    INF = 1_000_000

    # heuristic: BFS distance to target (admissible since edge cost >= 1)
    def h(cell):
        d = _grid_bfs_distance(cell, target, walls)
        return d if d is not None else INF

    # edge cost from cell A -> cell B at step index step_idx
    astar_horizon = knobs.get('astar_horizon', 8)
    use_def_history = knobs.get('use_def_history', 0)
    # H1: per-defender recently-visited cells (last K=20 ticks). Populated
    # by chooseAction. When use_def_history=1, threat applies only if
    # the candidate cell has been in some defender's recent patrol.
    if use_def_history:
        _def_recent = _CAPX_STATE.get('def_recent_visits', {})
    def edge_cost(cell_b, step_idx):
        # CCG S1: ignore threat for cells beyond near-future horizon. Aligns
        # with `_gate`, which already only inspects margins[1:gate_horizon+1].
        # Without this, A* assumes omniscient defenders perfectly intercept
        # cells 20+ steps out — drives most paths to None → BFS fallback.
        if step_idx > astar_horizon:
            return 1
        # CCG S2: own-side cells are non-lethal (A is ghost). Skip threat.
        if _is_own_side(cell_b, knobs):
            return 1
        # H1: defender behavior model. If no defender has recently visited
        # this cell, treat as non-threat (defender unlikely to suddenly
        # appear here). Bypasses Pattern A oscillation by smoothing
        # tick-to-tick defender position changes into rolling history.
        if use_def_history:
            any_recent = False
            for d_idx in defender_dist_map.keys():
                if cell_b in _def_recent.get(d_idx, ()):
                    any_recent = True
                    break
            if not any_recent:
                return 1
        threat = 0
        for d_dist in defender_dist_map.values():
            margin = d_dist.get(cell_b, 999) - step_idx
            if margin <= 0:
                threat += INF
            elif margin <= 2:
                threat += W2
            elif margin <= 4:
                threat += W3
        return 1 + threat

    W, H = walls.width, walls.height

    # heapq: (f, counter, cell)
    counter = 0
    g = {start: 0}
    step_at = {start: 0}  # track step index for each cell in best path
    came_from = {start: None}
    pq = [(h(start), counter, start)]
    expanded = 0

    while pq:
        f, _, cell = heapq.heappop(pq)

        if cell == target:
            # reconstruct path
            path = []
            cur = target
            while cur is not None:
                path.append(cur)
                cur = came_from[cur]
            return list(reversed(path))

        expanded += 1
        if expanded > node_cap:
            return None  # overflow -> caller uses BFS fallback

        g_cur = g[cell]
        step_cur = step_at[cell]

        x, y = cell
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            if walls[nx][ny]:
                continue
            nb = (nx, ny)
            step_nb = step_cur + 1
            # length budget pruning
            if step_nb > max_path_len:
                continue
            ec = edge_cost(nb, step_nb)
            g_nb = g_cur + ec
            if nb not in g or g_nb < g[nb]:
                g[nb] = g_nb
                step_at[nb] = step_nb
                came_from[nb] = cell
                counter += 1
                heapq.heappush(pq, (g_nb + h(nb), counter, nb))

    return None  # target unreachable within budget

# ---------------------------------------------------------------------------
# Cached A* (per-tick cache shared between ranker and gate loop)
# ---------------------------------------------------------------------------

def _astar_cached(
    a_pos: tuple,
    tgt: tuple,
    walls,
    defender_dist_map: dict,
    knobs: dict,
) -> list | None:
    cache = _CAPX_STATE['astar_cache']
    key = (a_pos, tgt)
    if key in cache:
        return cache[key]

    path = _astar_capx(a_pos, tgt, walls, defender_dist_map, knobs)
    if path is None:
        # fallback: direct BFS path
        path = _bfs_grid_path(a_pos, tgt, walls) or None
    cache[key] = path
    return path

# ---------------------------------------------------------------------------
# Survival probability (§5.3.3 / §5.4)
# ---------------------------------------------------------------------------

def _p_step_safe(margin: float, scale: float) -> float:
    """Sigmoid survival probability for a single step margin."""
    return 1.0 / (1.0 + math.exp(-(margin - 0) / scale))

def _p_survive(path: list, defender_dist_map: dict, scale: float, knobs: dict | None = None) -> float:
    """Product of per-step survival probabilities along path.

    CCG S2: own-side cells contribute P=1 (non-lethal).
    CCG S3: when knobs['psurvive_skip_current']=1 (default), skip i=0 cell
    where A is already alive (avoids ~0.5x bias collapsing ranker).
    """
    if not defender_dist_map:
        return 1.0
    p = 1.0
    skip_current = bool(knobs.get('psurvive_skip_current', 1)) if knobs else True
    iterable = enumerate(path[1:], start=1) if skip_current else enumerate(path)
    for i, cell in iterable:
        if knobs is not None and _is_own_side(cell, knobs):
            continue  # CCG S2: own-side = non-lethal
        m = min(
            (d_dist.get(cell, 999) - i for d_dist in defender_dist_map.values()),
            default=999,
        )
        p *= _p_step_safe(m, scale)
    return p

# ---------------------------------------------------------------------------
# Target ranker (§5.4)
# ---------------------------------------------------------------------------

def _rank_targets(
    a_pos: tuple,
    caps: list,
    walls,
    defender_dist_map: dict,
    knobs: dict,
) -> list:
    """
    Rank caps by survival probability (descending), then bfs distance (ascending).
    Floor fallback: if max P_survive < min_psurvive, rank by bfs_dist only.
    """
    if not caps:
        return []

    min_psurvive = knobs['min_psurvive']
    scale = knobs['sigmoid_scale']

    p_map = {}
    for c in caps:
        path = _astar_cached(a_pos, c, walls, defender_dist_map, knobs)
        if path:
            p_map[c] = _p_survive(path, defender_dist_map, scale, knobs)
        else:
            p_map[c] = 0.0

    max_p = max(p_map.values()) if p_map else 0.0

    def bfs_dist_or_inf(c):
        d = _grid_bfs_distance(a_pos, c, walls)
        return d if d is not None else 9999

    if max_p < min_psurvive:
        # floor fallback: distance-only ranking
        return sorted(caps, key=bfs_dist_or_inf)

    return sorted(caps, key=lambda c: (-p_map[c], bfs_dist_or_inf(c)))

# ---------------------------------------------------------------------------
# Gate policy (§5.3)
# ---------------------------------------------------------------------------

def _gate(
    path: list,
    defender_dist_map: dict,
    committed_target,
    knobs: dict,
) -> str:
    """
    Returns 'TRIGGER', 'ABANDON', or 'REJECT'.
    """
    if not path or len(path) < 1:
        return 'REJECT'

    # compute margin at each path cell (index i = step from current)
    # S2 scope-narrow (post-Phase-A): own-side mask was removed here. Reason:
    # When all next-8 cells are own-side, gate trivially triggers regardless
    # of the cells beyond horizon — A border-rushes into opp-side death.
    # Margin must reflect ACTUAL adversary distance even on own side.
    # S2 still applies in _astar_capx.edge_cost + _p_survive (planning/ranking
    # use the physical-rule shortcut, gate/drift use raw threat).
    def margin_at(i, cell):
        if not defender_dist_map:
            return 999
        return min(
            (d_dist.get(cell, 999) - i for d_dist in defender_dist_map.values()),
            default=999,
        )

    margins = [margin_at(i, cell) for i, cell in enumerate(path)]

    # next 3 steps after current position (indices 1..3) — for hard abandon.
    next3 = margins[1:4] if len(margins) > 1 else margins
    next3_min = min(next3) if next3 else 999

    # Near-future horizon for trigger: margin at the cells the agent will
    # occupy in the next `gate_horizon` ticks. Full-path margin assumed an
    # omniscient defender chasing to the FAR end of the path — too pessimistic
    # for typical Pacman where defenders react locally. Use full path only
    # when CAPX_GATE_USE_FULL=1 (fall back to spec literal).
    horizon = max(1, knobs.get('gate_horizon', 8))
    if knobs.get('gate_use_full', 0):
        gate_window = margins
    else:
        gate_window = margins[1:horizon + 1] if len(margins) > 1 else margins
    full_min = min(gate_window) if gate_window else 999

    hard_abandon = knobs['hard_abandon_margin']
    min_margin = knobs['min_margin']
    approach_mode = knobs['approach_mode']

    # 1) Hard abandon override (P2 — suicide prevention)
    if next3_min < hard_abandon:
        return 'ABANDON'

    # 2) Hysteresis threshold
    target = path[-1] if path else None
    if target is not None and target == committed_target:
        threshold = min_margin - 2
    else:
        threshold = min_margin

    # 3) Trigger condition
    if full_min >= threshold:
        return 'TRIGGER'

    # 4) Approach mode
    if approach_mode and full_min >= threshold - 1:
        return 'TRIGGER'

    return 'REJECT'

# ---------------------------------------------------------------------------
# Safest step toward target (Step 3 fallback drift, §5.1)
# ---------------------------------------------------------------------------

def _safest_step_toward(
    a_pos: tuple,
    target: tuple,
    defender_dist_map: dict,
    walls,
    legal: list,
    knobs: dict | None = None,
) -> str:
    """
    For each legal next cell, pick action maximizing min-defender-margin,
    breaking ties by minimizing BFS distance to target.
    CCG S2: own-side cells get max margin (non-lethal).
    """
    W, H = walls.width, walls.height

    def next_cell(action):
        dx, dy = Actions.directionToVector(action)
        return (int(a_pos[0] + dx), int(a_pos[1] + dy))

    # S2 scope-narrow: drift fallback must see actual threat — own-side mask
    # would let A drift into a border-rush; same broken pattern as gate.
    def margin_at_cell(cell):
        if not defender_dist_map:
            return 999
        return min(
            (d_dist.get(cell, 999) - 1 for d_dist in defender_dist_map.values()),
            default=999,
        )

    best_action = Directions.STOP
    best_margin = -9999
    best_dist = 9999

    for action in legal:
        if action == Directions.STOP:
            continue
        nc = next_cell(action)
        if walls[nc[0]][nc[1]]:
            continue
        m = margin_at_cell(nc)
        d = _grid_bfs_distance(nc, target, walls)
        d = d if d is not None else 9999
        if (m > best_margin) or (m == best_margin and d < best_dist):
            best_margin = m
            best_dist = d
            best_action = action

    return best_action

# ---------------------------------------------------------------------------
# Visible defender extraction
# ---------------------------------------------------------------------------

def _visible_defenders(agent, gameState) -> list:
    """
    Returns [(opp_idx, (x, y)), ...] for visible, non-scared ghost opponents.
    """
    defs = []
    for opp_idx in agent.getOpponents(gameState):
        s = gameState.getAgentState(opp_idx)
        if s.isPacman:
            continue
        if s.scaredTimer and s.scaredTimer > 0:
            continue
        pos = s.getPosition()
        if pos is None:
            continue
        defs.append((opp_idx, (int(pos[0]), int(pos[1]))))
    return defs

# ---------------------------------------------------------------------------
# Cap-eat detection (§5.1 G3 / N3)
# ---------------------------------------------------------------------------

def _emit_cap_eaten_if_decremented(
    agent,
    gameState,
    prev_caps: set,
    current_caps: list,
    a_pos: tuple,
    tick: int,
) -> None:
    """
    If cap set shrank, check Red agent proximity and emit [CAPX_CAP_EATEN].
    """
    current_set = set(current_caps)
    eaten = prev_caps - current_set
    if not eaten:
        return

    # Find which Red agent (if any) was near the missing cap
    red_indices = gameState.getRedTeamIndices()
    for cap in eaten:
        eater_idx = None
        for ri in red_indices:
            rpos = gameState.getAgentPosition(ri)
            if rpos is None:
                continue
            rpos = (int(rpos[0]), int(rpos[1]))
            # proximity check: within 1 BFS step
            if abs(rpos[0] - cap[0]) + abs(rpos[1] - cap[1]) <= 1:
                eater_idx = ri
                break
        print(
            f'[CAPX_CAP_EATEN] tick={tick} cap={cap} a_pos={a_pos}'
            f' eater_idx={eater_idx} outcome=eaten'
        )

# ---------------------------------------------------------------------------
# Respawn / death detection
# ---------------------------------------------------------------------------

def _check_a_died(agent, a_pos: tuple, prev_a_pos, tick: int) -> None:
    """
    Detect if A respawned (current==spawn AND prev was different AND distance jumped > 1).
    """
    spawn = agent._spawn
    if spawn is None or prev_a_pos is None:
        return
    if a_pos != spawn:
        return
    if prev_a_pos == spawn:
        return
    dist = abs(a_pos[0] - prev_a_pos[0]) + abs(a_pos[1] - prev_a_pos[1])
    if dist <= 1:
        return
    if tick not in _CAPX_STATE['a_died_emitted']:
        _CAPX_STATE['a_died_emitted'].add(tick)
        print(f'[CAPX_A_DIED] tick={tick} pos={a_pos}')

# ---------------------------------------------------------------------------
# Main agent class
# ---------------------------------------------------------------------------

class ReflexRCTempoCapxAgent(CaptureAgent):
    """
    CAPX: Capsule-Only experimental attacker.
    Sole objective: reach at least 1 capsule alive.
    Uses defender-aware A* + survival-weighted ranker + soft gate w/ hard abandon.
    """

    def registerInitialState(self, gameState):
        CaptureAgent.registerInitialState(self, gameState)

        self._walls = gameState.getWalls()
        self._W = self._walls.width
        self._H = self._walls.height

        raw_spawn = gameState.getAgentState(self.index).getPosition()
        self._spawn = (int(raw_spawn[0]), int(raw_spawn[1])) if raw_spawn else None

        self._knobs = _read_capx_env()

        self._is_red = (self.index in gameState.getRedTeamIndices())

        # CCG S2: bake side info into knobs so all helpers (edge_cost,
        # _p_survive, _gate margin, _safest_step_toward) can compute
        # _is_own_side(cell, knobs). Red home: x < mid_x. Blue home: x >= mid_x.
        self._knobs['is_red'] = self._is_red
        self._knobs['mid_x']  = self._W // 2

        # Init module-level state on first agent registration
        if _CAPX_STATE['prev_caps'] is None:
            _CAPX_STATE['prev_caps'] = set()
            _CAPX_STATE['prev_blue_caps_seen'] = set()

        print(
            f'[CAPX_INIT] idx={self.index} red={self._is_red}'
            f' W={self._W} H={self._H}'
            f' caps={len(gameState.getBlueCapsules() if self._is_red else gameState.getRedCapsules())}'
        )

    def chooseAction(self, gameState):
        t0 = time.perf_counter()
        action = self._choose_action_impl(gameState)
        wall_ms = (time.perf_counter() - t0) * 1000
        _CAPX_STATE['wall_times'].append(wall_ms)
        if self._knobs['trace']:
            # trace is emitted inside _choose_action_impl via _emit_trace stub
            pass
        return action

    def _choose_action_impl(self, gameState) -> str:
        knobs = self._knobs
        walls = self._walls

        # Tick proxy: use timeleft if available, else counter
        try:
            tick = gameState.data.timeleft
        except Exception:
            _CAPX_STATE['tick_counter'] += 1
            tick = _CAPX_STATE['tick_counter']

        # Current agent position
        raw_pos = gameState.getAgentState(self.index).getPosition()
        if raw_pos is None:
            return Directions.STOP
        a_pos = (int(raw_pos[0]), int(raw_pos[1]))

        # Death detection
        prev_a_pos = _CAPX_STATE['prev_a_pos']
        _check_a_died(self, a_pos, prev_a_pos, tick)
        _CAPX_STATE['prev_a_pos'] = a_pos

        # Capsule tracking (CAPX is Red -> eats Blue caps)
        if self._is_red:
            current_caps = gameState.getBlueCapsules()
        else:
            current_caps = gameState.getRedCapsules()

        prev_caps = _CAPX_STATE['prev_caps']
        if prev_caps is None:
            prev_caps = set()

        # Emit eat event if set shrank
        _emit_cap_eaten_if_decremented(
            self, gameState, prev_caps, current_caps, a_pos, tick
        )
        _CAPX_STATE['prev_caps'] = set(current_caps)

        legal = gameState.getLegalActions(self.index)

        # Mission complete (no caps remain)
        if not current_caps:
            return Directions.STOP

        # Clear A* cache at tick start (N3)
        if _CAPX_STATE['astar_cache_tick'] != tick:
            _CAPX_STATE['astar_cache'] = {}
            _CAPX_STATE['astar_cache_tick'] = tick

        # Build per-tick defender distance maps
        raw_defs = _visible_defenders(self, gameState)
        defender_dist_map: dict = {}
        for d_idx, d_pos in raw_defs:
            defender_dist_map[d_idx] = _bfs_dist_map(d_pos, walls)

        # H1: roll defender visit history (for use_def_history-aware edge_cost)
        if knobs.get('use_def_history', 0):
            from collections import deque as _deque
            recent = _CAPX_STATE.setdefault('def_recent_visits', {})
            window = _CAPX_STATE.get('def_recent_window', 20)
            for d_idx, d_pos in raw_defs:
                dq = recent.get(d_idx)
                if dq is None or not isinstance(dq, _deque):
                    dq = _deque(maxlen=window)
                    recent[d_idx] = dq
                dq.append(d_pos)

        # Step 1: rank cap targets by survival probability
        targets = _rank_targets(a_pos, list(current_caps), walls, defender_dist_map, knobs)

        committed = _CAPX_STATE['committed_target']
        chosen_tgt = None
        chosen_path = None
        chosen_gate = 'NONE'
        chosen_p = 0.0

        # Step 2: try each ranked target through gate
        for tgt in targets:
            path = _astar_cached(a_pos, tgt, walls, defender_dist_map, knobs)
            if not path or len(path) < 2:
                continue
            decision = _gate(path, defender_dist_map, committed, knobs)
            if decision == 'TRIGGER':
                chosen_tgt = tgt
                chosen_path = path
                chosen_gate = 'TRIGGER'
                if defender_dist_map:
                    chosen_p = _p_survive(path, defender_dist_map, knobs['sigmoid_scale'], knobs)
                else:
                    chosen_p = 1.0
                _CAPX_STATE['committed_target'] = tgt
                step = path[1]
                d = _dir_step(a_pos, step, legal)
                action = d if d is not None else Directions.STOP
                if knobs['trace']:
                    self._emit_trace(
                        gameState, tick, a_pos, current_caps, targets,
                        tgt, path, defender_dist_map, chosen_p, 'TRIGGER', action,
                        _CAPX_STATE['wall_times'][-1] if _CAPX_STATE['wall_times'] else 0.0,
                    )
                return action

        # Step 3: hard abandon / drift toward safest reachable target
        _CAPX_STATE['committed_target'] = None
        fallback_tgt = targets[0] if targets else a_pos
        action = _safest_step_toward(a_pos, fallback_tgt, defender_dist_map, walls, legal, knobs)

        if knobs['trace']:
            self._emit_trace(
                gameState, tick, a_pos, current_caps, targets,
                fallback_tgt, None, defender_dist_map, 0.0, 'DRIFT', action,
                _CAPX_STATE['wall_times'][-1] if _CAPX_STATE['wall_times'] else 0.0,
            )
        return action

    def _emit_trace(
        self,
        gameState, tick, a_pos, caps, tgts,
        chosen_tgt, path, defender_dist_map, p_surv, gate, act, wall_ms,
    ) -> None:
        path_len = len(path) if path else 0
        n_defs = len(defender_dist_map)
        tgt_list = list(tgts)[:4]  # cap to avoid huge lines
        print(
            f'[CAPX_TRACE] tick={tick} a={a_pos} caps={len(list(caps))}'
            f' tgts={tgt_list} chosen_tgt={chosen_tgt}'
            f' path_len={path_len} defs={n_defs}'
            f' p_surv={p_surv:.2f} gate={gate} act={act} wall_ms={wall_ms:.1f}'
        )


# ---------------------------------------------------------------------------
# Stub B agent (for solo wrapper — defined here, not imported from abs_solo)
# ---------------------------------------------------------------------------

class StubBAgent(CaptureAgent):
    """Does nothing — allows CAPX to run solo via the solo wrapper."""

    def registerInitialState(self, gameState):
        CaptureAgent.registerInitialState(self, gameState)

    def chooseAction(self, gameState):
        return Directions.STOP


# ---------------------------------------------------------------------------
# createTeam entry point (used by capture.py -r zoo_reflex_rc_tempo_capx)
# ---------------------------------------------------------------------------

def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexRCTempoCapxAgent',
               second='StubBAgent'):
    return [
        ReflexRCTempoCapxAgent(firstIndex),
        StubBAgent(secondIndex),
    ]

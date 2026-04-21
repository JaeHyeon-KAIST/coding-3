# zoo_reflex_rc_tempo_abs.py
# --------------------------
# rc-tempo V0.3 ABS — pm34 abstract-graph + beam-search 2-cap chain planner.
#
# SKELETON stage (pm34 END, pm35 fleshes out):
#   - registerInitialState: build abstract graph + A-alone beam plan (S1)
#   - chooseAction: delegates to rc82 (fallback). Plan execution wired in pm35.
#   - Verified: capture.py can invoke without crash. Build wall logged.
#
# Deps:
#   minicontest/zoo_rctempo_gamma_graph.py (abstract graph builder)
#   minicontest/zoo_rctempo_gamma_search.py (beam search engine)
#
# Naming: "γ" (gamma) name already used by pm29 entry-DP layer (REJECTED).
# This file uses "ABS" to avoid confusion.

from __future__ import annotations

import sys
import time
from collections import deque

from zoo_reflex_rc82 import ReflexRC82Agent
from game import Directions, Actions


_ABS_TEAM = {
    'built': False,
    'graph': None,
    'walls': None,         # walls grid for path reconstruction
    'plan_A': None,
    'plan_A_cells': None,  # cell-level path for A
    'plan_A_index': 0,     # next cell in plan_A_cells to move TO
    'cap1': None,
    'cap2': None,
    'stats': None,
    'note': None,
    'scared_started': False,
    'a_agent_index': None,
}


def _bfs_path(walls, start, goal, allowed_cells, W, H):
    """BFS shortest path from start to goal within allowed_cells. Returns list
    of cells INCLUDING start and goal. Empty list if unreachable."""
    if start == goal:
        return [start]
    parent = {start: None}
    q = deque([start])
    while q:
        p = q.popleft()
        if p == goal:
            path = [p]
            while parent[path[-1]] is not None:
                path.append(parent[path[-1]])
            return list(reversed(path))
        x, y = p
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < W and 0 <= ny < H):
                continue
            r = H - 1 - ny
            if walls[r][nx]:
                continue
            n = (nx, ny)
            if n not in allowed_cells:
                continue
            if n in parent:
                continue
            parent[n] = p
            q.append(n)
    return []


def _plan_to_cells(plan, walls, allowed_cells, W, H):
    """Convert abstract plan tuple to cell sequence.

    plan = (('start', X0), ('move', X1), ('header', hi, k) | ..., ...)
    Only 'move' actions produce cells. 'header' actions are skipped in MVP
    (pocket visits not yet wired). 'start' sets initial position.
    """
    cells = []
    cur = None
    for action in plan:
        kind = action[0]
        if kind == 'start':
            cur = action[1]
            cells.append(cur)
        elif kind == 'move':
            target = action[1]
            if cur is None:
                cur = target
                cells.append(cur)
                continue
            path = _bfs_path(walls, cur, target, allowed_cells, W, H)
            if not path:
                break
            cells.extend(path[1:])  # skip cur (already last)
            cur = target
        elif kind == 'header':
            # TODO: pocket Euler tour. For MVP skip (costs food, but we keep
            # moving through main). Fall back to rc82 may catch nearby pocket
            # food opportunistically.
            continue
    return cells


def _layout_to_maze_str(layout, gameState):
    """Convert Layout + GameState to ascii maze string compatible with
    build_from_maze. '%' wall, '.' food, 'o' capsule, digits for agent spawns."""
    walls = layout.walls
    food = gameState.getBlueFood() if hasattr(gameState, 'getBlueFood') else layout.food
    # Union of blue + red food if needed; for now use full initial food grid
    food_all = layout.food
    W = walls.width
    H = walls.height
    caps = set(layout.capsules)
    # AgentPositions: list of (isPacman, (x, y))
    agent_spawns = {}
    for i, (is_pac, pos) in enumerate(layout.agentPositions):
        agent_spawns[pos] = str(i + 1)

    rows = []
    for r in range(H):
        y = H - 1 - r
        row = []
        for c in range(W):
            if walls[c][y]:
                row.append('%')
            elif (c, y) in caps:
                row.append('o')
            elif food_all[c][y]:
                row.append('.')
            elif (c, y) in agent_spawns:
                row.append(agent_spawns[(c, y)])
            else:
                row.append(' ')
        rows.append(''.join(row))
    return '\n'.join(rows)


def _build_once(gameState, self_agent):
    if _ABS_TEAM['built']:
        return
    _ABS_TEAM['built'] = True
    t0 = time.time()
    try:
        from zoo_rctempo_gamma_graph import build_from_maze, full_map_bfs
        from zoo_rctempo_gamma_search import beam_search_abstract
    except Exception as e:
        _ABS_TEAM['note'] = f'import failed: {e}'
        try:
            print(f'[ABS] import failed: {e}', file=sys.stderr)
        except Exception:
            pass
        return

    layout = gameState.data.layout
    try:
        maze_str = _layout_to_maze_str(layout, gameState)
        graph, walls, spawns = build_from_maze(maze_str)
    except Exception as e:
        _ABS_TEAM['note'] = f'graph build failed: {e}'
        try:
            print(f'[ABS] graph build failed: {e}', file=sys.stderr)
        except Exception:
            pass
        return

    _ABS_TEAM['graph'] = graph
    build_wall = (time.time() - t0) * 1000

    # Abstract graph's `blue_caps` = right-half caps = what RED team eats.
    # So RED team uses graph as-is. BLUE team needs mirror (pm35 TODO).
    if not self_agent.red:
        _ABS_TEAM['note'] = 'blue team — mirror not yet implemented (pm35)'
        try:
            print(f'[ABS] build={build_wall:.1f}ms  '
                  f'X={len(graph["x_positions"])} headers={len(graph["headers"])} '
                  f'edges={len(graph["edges"])} (blue team — fallback only)',
                  file=sys.stderr)
        except Exception:
            pass
        return

    # Identify A agent and cap1/cap2
    team = self_agent.getTeam(gameState)
    a_idx = min(team)
    a_spawn = gameState.getAgentPosition(a_idx)
    if a_spawn is None:
        _ABS_TEAM['note'] = 'A spawn missing'
        return

    a_dists = full_map_bfs(walls, a_spawn, graph['W'], graph['H'])
    blue_caps = graph['blue_caps']
    if len(blue_caps) < 2:
        _ABS_TEAM['note'] = f'only {len(blue_caps)} blue caps — not 2-cap map'
        try:
            print(f'[ABS] {_ABS_TEAM["note"]} — fallback only', file=sys.stderr)
        except Exception:
            pass
        return
    cap_sorted = sorted(blue_caps, key=lambda c: a_dists.get(c, 9999))
    cap1, cap2 = cap_sorted[0], cap_sorted[1]

    # Compute A's plan from EACH cap (rc82 might eat either one first).
    # At scared start, select matching plan by A's actual position.
    t_beam = time.time()
    plans_by_cap = {}
    for start_cap in (cap1, cap2):
        results = beam_search_abstract(
            graph, start_cap, graph['entry_xs'], budget=79,
            beam=500, max_steps=48, return_plans=True)
        if results:
            plans_by_cap[start_cap] = results[0]
    beam_wall = (time.time() - t_beam) * 1000

    _ABS_TEAM['cap1'] = cap1
    _ABS_TEAM['cap2'] = cap2
    _ABS_TEAM['walls'] = walls
    _ABS_TEAM['a_agent_index'] = a_idx

    # Convert both plans to cell sequences
    main_corridor = graph['main_corridor']
    extended_main = set(main_corridor)
    _ABS_TEAM['plans_by_cap'] = {}
    for cap_pos, plan in plans_by_cap.items():
        cells = _plan_to_cells(plan['plan'], walls, extended_main,
                                graph['W'], graph['H'])
        _ABS_TEAM['plans_by_cap'][cap_pos] = {
            'plan': plan,
            'cells': cells,
            'food': plan['food'],
            'time': plan['time'],
        }

    stats = {
        'build_ms': build_wall,
        'beam_ms': beam_wall,
        'cap1': cap1, 'cap2': cap2,
        'xs': len(graph['x_positions']),
        'headers': len(graph['headers']),
        'edges': len(graph['edges']),
        'cap1_food': plans_by_cap.get(cap1, {}).get('food'),
        'cap2_food': plans_by_cap.get(cap2, {}).get('food'),
    }
    _ABS_TEAM['stats'] = stats

    try:
        print(f'[ABS] build={build_wall:.1f}ms  beam={beam_wall:.1f}ms  '
              f'X={stats["xs"]} headers={stats["headers"]} edges={stats["edges"]}  '
              f'cap1={cap1} (food={stats.get("cap1_food", "?")})  '
              f'cap2={cap2} (food={stats.get("cap2_food", "?")})',
              file=sys.stderr)
    except Exception:
        pass


class ReflexRCTempoAbsAgent(ReflexRC82Agent):
    """Abstract-graph 2-cap planner agent (pm34 skeleton).

    Builds plan at init, logs stats, delegates actions to rc82. pm35 wires
    plan → action conversion in chooseAction.
    """

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            _build_once(gameState, self)
        except Exception as e:
            try:
                print(f'[ABS] registerInitialState error: {e}', file=sys.stderr)
            except Exception:
                pass

    def chooseAction(self, gameState):
        # Only A agent executes plan. B agent uses rc82.
        a_idx = _ABS_TEAM.get('a_agent_index')
        if a_idx is None or self.index != a_idx:
            return super().chooseAction(gameState)
        if not _ABS_TEAM.get('plans_by_cap'):
            return super().chooseAction(gameState)

        # Detect scared: any opponent's scaredTimer > 0
        scared_active = False
        try:
            for opp_idx in self.getOpponents(gameState):
                st = gameState.getAgentState(opp_idx)
                if getattr(st, 'scaredTimer', 0) > 0:
                    scared_active = True
                    break
        except Exception:
            pass

        if not scared_active:
            return super().chooseAction(gameState)

        my_pos = gameState.getAgentPosition(self.index)
        if my_pos is None:
            return super().chooseAction(gameState)

        # On first scared tick: select plan whose start cell matches our pos.
        if not _ABS_TEAM.get('scared_started'):
            _ABS_TEAM['scared_started'] = True
            plans = _ABS_TEAM['plans_by_cap']
            selected = None
            for cap_pos, p in plans.items():
                if cap_pos == my_pos:
                    selected = p
                    break
            if selected is None:
                # Closest cap match
                def md(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
                best_d = 9999
                for cap_pos, p in plans.items():
                    d = md(cap_pos, my_pos)
                    if d < best_d:
                        best_d = d
                        selected = p
            _ABS_TEAM['active_plan'] = selected
            _ABS_TEAM['active_plan_index'] = 0
            try:
                print(f'[ABS] scared started — A at {my_pos}, plan food={selected["food"] if selected else "?"}',
                      file=sys.stderr)
            except Exception:
                pass

        active = _ABS_TEAM.get('active_plan')
        if active is None:
            return super().chooseAction(gameState)
        cells = active['cells']
        idx = _ABS_TEAM['active_plan_index']

        target_cell = None
        for look_ahead in range(idx, min(idx + 3, len(cells))):
            if cells[look_ahead] == my_pos:
                if look_ahead + 1 < len(cells):
                    target_cell = cells[look_ahead + 1]
                    _ABS_TEAM['active_plan_index'] = look_ahead + 1
                break

        if target_cell is None:
            return super().chooseAction(gameState)

        # Compute direction from my_pos to target_cell
        dx = target_cell[0] - my_pos[0]
        dy = target_cell[1] - my_pos[1]
        desired = None
        if dx == 1 and dy == 0:
            desired = Directions.EAST
        elif dx == -1 and dy == 0:
            desired = Directions.WEST
        elif dx == 0 and dy == 1:
            desired = Directions.NORTH
        elif dx == 0 and dy == -1:
            desired = Directions.SOUTH

        legal = gameState.getLegalActions(self.index)
        if desired in legal:
            return desired
        # Desired not legal (something happened). Fallback.
        return super().chooseAction(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexRCTempoAbsAgent', second='ReflexRCTempoAbsAgent'):
    return [ReflexRCTempoAbsAgent(firstIndex), ReflexRCTempoAbsAgent(secondIndex)]

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

from zoo_reflex_rc82 import ReflexRC82Agent
from game import Directions, Actions


_ABS_TEAM = {
    'built': False,
    'graph': None,
    'plan_A': None,
    'stats': None,
    'note': None,
}


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

    # Only BLUE team supported in skeleton (graph is blue-side perspective).
    if self_agent.red:
        _ABS_TEAM['note'] = 'red team — skeleton only supports blue'
        try:
            print(f'[ABS] build={build_wall:.1f}ms  '
                  f'X={len(graph["x_positions"])} headers={len(graph["headers"])} '
                  f'edges={len(graph["edges"])} (red team — fallback only)',
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

    # Plan S1: A eats cap1, beam from cap1 to any entry X, budget=79
    t_beam = time.time()
    a_results = beam_search_abstract(
        graph, cap1, graph['entry_xs'], budget=79, beam=500, max_steps=48,
        return_plans=True)
    beam_wall = (time.time() - t_beam) * 1000

    stats = {
        'build_ms': build_wall,
        'beam_ms': beam_wall,
        'cap1': cap1, 'cap2': cap2,
        'xs': len(graph['x_positions']),
        'headers': len(graph['headers']),
        'edges': len(graph['edges']),
    }
    if a_results:
        best = a_results[0]
        _ABS_TEAM['plan_A'] = best
        stats['a_food'] = best['food']
        stats['a_time'] = best['time']
    _ABS_TEAM['stats'] = stats

    try:
        print(f'[ABS] build={build_wall:.1f}ms  beam={beam_wall:.1f}ms  '
              f'X={stats["xs"]} headers={stats["headers"]} edges={stats["edges"]}  '
              f'cap1={cap1} cap2={cap2}  '
              f'A_plan food={stats.get("a_food", "?")} time={stats.get("a_time", "?")}',
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
        # Skeleton: rc82 fallback. pm35 will execute plan during scared window.
        return super().chooseAction(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexRCTempoAbsAgent', second='ReflexRCTempoAbsAgent'):
    return [ReflexRCTempoAbsAgent(firstIndex), ReflexRCTempoAbsAgent(secondIndex)]

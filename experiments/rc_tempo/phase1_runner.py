#!/usr/bin/env python3
"""Phase 1 outcome runner — early-terminate capture game when β resolves.

Exits as soon as:
    - Our "A" agent (offensive, lower team index) eats the capsule, OR
    - Our A dies (teleported to start), OR
    - max_moves reached (timeout).

This is ~5-10× faster than running full 1200-move games when we only want
to measure β's "can A safely reach capsule?" primitive.

Usage:
    .venv/bin/python experiments/rc_tempo/phase1_runner.py \\
        -r zoo_reflex_rc_tempo_beta_v3a -b baseline \\
        -l defaultCapture --seed 42 --max-moves 200

Returns one-line JSON to stdout with keys:
    outcome: "capsule_eaten" | "a_died" | "timeout" | "crashed"
    moves: int — moves played
    a_food_eaten: int — food A ate before outcome
    a_final_pos, capsule_final_pos, winner (optional), wall_sec
"""
from __future__ import annotations
import json
import os
import sys
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"


def _emit(payload: dict) -> None:
    print(json.dumps(payload))


def _a_index_on_team(team_indices):
    """A is the lower-indexed teammate."""
    return sorted(team_indices)[0]


def _opponent_indices(state, our_team):
    if our_team == 'red':
        return state.getBlueTeamIndices()
    return state.getRedTeamIndices()


def run_phase1_game(red_team, blue_team, layout_name, seed,
                    max_moves=200, our_team='red',
                    mute=True, catch_exceptions=True):
    """Run a capture game with early termination on A's Phase 1 outcome.

    Returns: dict with keys outcome, moves, a_food_eaten, ...
    """
    os.chdir(str(MINICONTEST))
    if str(MINICONTEST) not in sys.path:
        sys.path.insert(0, str(MINICONTEST))

    # Seed for layout generation (RANDOM<seed>)
    import random as _random
    _random.seed(seed)

    from capture import CaptureRules, loadAgents
    from layout import getLayout
    import textDisplay

    lay = getLayout(layout_name, 3)
    if lay is None:
        return {'outcome': 'crashed', 'crash_reason': f'layout_not_found:{layout_name}',
                'moves': 0, 'a_food_eaten': 0, 'wall_sec': 0.0}

    # Load agents
    try:
        red_agents = loadAgents(True, red_team, False, {})
        blue_agents = loadAgents(False, blue_team, False, {})
    except Exception as e:
        return {'outcome': 'crashed',
                'crash_reason': f'agent_load_failed:{type(e).__name__}:{e}',
                'moves': 0, 'a_food_eaten': 0, 'wall_sec': 0.0}

    # Interleave agents by index: 0=red[0], 1=blue[0], 2=red[1], 3=blue[1]
    agents = [red_agents[0], blue_agents[0], red_agents[1], blue_agents[1]]

    display = textDisplay.NullGraphics()
    rules = CaptureRules()
    rules.quiet = True
    game = rules.newGame(lay, agents, display, length=1200, muteAgents=mute,
                          catchExceptions=catch_exceptions)

    # Determine our A's global index. IMPORTANT: we must re-invoke the
    # accessors on *game.state* each tick (it changes), not keep a bound
    # method on the initial state.
    state = game.state
    if our_team == 'red':
        my_team_idx = state.getRedTeamIndices()
        cap_list_getter = lambda: game.state.getBlueCapsules()
        food_getter = lambda st: st.getBlueFood()
    else:
        my_team_idx = state.getBlueTeamIndices()
        cap_list_getter = lambda: game.state.getRedCapsules()
        food_getter = lambda st: st.getRedFood()
    a_idx = _a_index_on_team(my_team_idx)

    # A's starting position (for death detection)
    a_start = state.getAgentPosition(a_idx)

    # Initial capsule count + positions
    initial_capsules = set(tuple(c) for c in cap_list_getter())
    initial_food = food_getter(state).asList()
    initial_food_count = len(initial_food)

    t0 = time.time()
    outcome = 'timeout'
    a_food_eaten = 0
    a_died_count = 0
    capsule_eaten_by_A = False
    capsule_eaten_by_anyone = False
    capsule_eaten_tick = -1
    crashed = False
    crash_reason = None

    # Post-trigger measurement: trigger = first tick where exactly 1 opp is pacman
    trigger_tick = -1          # -1 = never triggered
    a_food_pre_trigger = 0
    a_food_post_trigger = 0
    a_died_post_trigger = False
    cap_eaten_post_trigger = False

    # Initialize display + run agent.registerInitialState (copied from Game.run)
    try:
        game.display.initialize(game.state.data)
    except Exception:
        pass

    # Register initial state
    for i, agent in enumerate(agents):
        if agent is None:
            return {'outcome': 'crashed', 'crash_reason': f'agent_null:{i}',
                    'moves': 0, 'a_food_eaten': 0, 'wall_sec': time.time() - t0}
        if hasattr(agent, 'registerInitialState'):
            try:
                agent.registerInitialState(game.state.deepCopy())
            except Exception as e:
                return {'outcome': 'crashed',
                        'crash_reason': f'registerInitialState:idx={i}:{type(e).__name__}:{e}',
                        'moves': 0, 'a_food_eaten': 0, 'wall_sec': time.time() - t0}

    # Main loop — simplified from Game.run
    agent_index = 0
    moves = 0
    from game import GameStateData  # noqa: F401 (ensure import)

    prev_a_pos = a_start
    prev_capsules = set(initial_capsules)
    prev_food = set(initial_food)

    while moves < max_moves and not game.gameOver:
        agent = agents[agent_index]
        obs_state = game.state.deepCopy()
        try:
            if hasattr(agent, 'observationFunction'):
                obs = agent.observationFunction(obs_state)
            else:
                obs = obs_state
        except Exception as e:
            crashed = True
            crash_reason = f'obs:idx={agent_index}:{type(e).__name__}:{e}'
            outcome = 'crashed'
            break

        try:
            action = agent.getAction(obs)
        except Exception as e:
            crashed = True
            crash_reason = f'getAction:idx={agent_index}:{type(e).__name__}:{e}'
            outcome = 'crashed'
            break

        # Apply action (matches Game.run behavior)
        game.moveHistory.append((agent_index, action))
        try:
            game.state = game.state.generateSuccessor(agent_index, action)
        except Exception as e:
            crashed = True
            crash_reason = f'successor:idx={agent_index}:{type(e).__name__}:{e}'
            outcome = 'crashed'
            break

        try:
            game.display.update(game.state.data)
        except Exception:
            pass
        try:
            game.rules.process(game.state, game)
        except Exception:
            pass

        # Trigger detection: check opp_pacman_count AFTER this move
        if trigger_tick < 0:
            opp_pac_count = 0
            for opp_i in _opponent_indices(game.state, our_team):
                try:
                    st = game.state.getAgentState(opp_i)
                    if getattr(st, 'isPacman', False):
                        opp_pac_count += 1
                except Exception:
                    pass
            if opp_pac_count == 1:
                trigger_tick = moves  # will be incremented below

        # Outcome check after this move
        cur_capsules = set(tuple(c) for c in cap_list_getter())
        cur_food = set(food_getter(game.state).asList())

        # Global capsule eaten tracking (independent of who moved)
        eaten_caps = prev_capsules - cur_capsules
        if eaten_caps and not capsule_eaten_by_anyone:
            capsule_eaten_by_anyone = True
            capsule_eaten_tick = moves

        triggered_now = (trigger_tick >= 0)

        if agent_index == a_idx:
            # A just moved — check its state
            cur_a_pos = game.state.getAgentPosition(a_idx)

            # Capsule eaten by A check
            if eaten_caps and cur_a_pos in eaten_caps:
                capsule_eaten_by_A = True
                if triggered_now:
                    cap_eaten_post_trigger = True
                outcome = 'capsule_eaten'
                moves += 1
                break
            # Food A ate (for metric)
            eaten_food = prev_food - cur_food
            if eaten_food and cur_a_pos in eaten_food:
                a_food_eaten += 1
                if triggered_now:
                    a_food_post_trigger += 1
                else:
                    a_food_pre_trigger += 1

            # Death check
            was_pacman = _is_pacman_pos(prev_a_pos, state.getWalls(),
                                          our_team == 'red')
            if was_pacman and cur_a_pos == a_start and prev_a_pos != a_start:
                a_died_count += 1
                if triggered_now:
                    a_died_post_trigger = True
                outcome = 'a_died'
                moves += 1
                break

            prev_a_pos = cur_a_pos

        prev_capsules = cur_capsules
        prev_food = cur_food

        agent_index = (agent_index + 1) % len(agents)
        moves += 1

        # Detect game over
        if game.state.isOver():
            game.gameOver = True
            # Determine reason: game ended naturally
            if outcome == 'timeout':
                outcome = 'game_over'
            break

    # Call agent.final() so metric-writing agents can emit their CSVs.
    for i, agent in enumerate(agents):
        if hasattr(agent, 'final'):
            try:
                agent.final(game.state.deepCopy())
            except Exception:
                pass

    wall = time.time() - t0

    return {
        'outcome': outcome,
        'moves': moves,
        'a_food_eaten': a_food_eaten,
        'a_died_count': a_died_count,
        'capsule_eaten_by_A': capsule_eaten_by_A,
        'capsule_eaten_by_anyone': capsule_eaten_by_anyone,
        'capsule_eaten_tick': capsule_eaten_tick,
        'trigger_tick': trigger_tick,
        'triggered': trigger_tick >= 0,
        'moves_post_trigger': (moves - trigger_tick) if trigger_tick >= 0 else -1,
        'a_food_post_trigger': a_food_post_trigger,
        'a_food_pre_trigger': a_food_pre_trigger,
        'a_died_post_trigger': a_died_post_trigger,
        'cap_eaten_post_trigger': cap_eaten_post_trigger,
        'a_final_pos': list(game.state.getAgentPosition(a_idx)) if not crashed else None,
        'crashed': crashed,
        'crash_reason': crash_reason,
        'wall_sec': round(wall, 3),
        'score': game.state.getScore() if not crashed else None,
    }


def _is_pacman_pos(pos, walls, is_red_team):
    """Heuristic: is the position on opp territory (i.e., A is pacman there)?"""
    if pos is None:
        return False
    mid = walls.width // 2
    if is_red_team:
        return pos[0] >= mid  # red's opp side = right half
    else:
        return pos[0] < mid


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('-r', '--red', required=True)
    ap.add_argument('-b', '--blue', required=True)
    ap.add_argument('-l', '--layout', default='defaultCapture')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--max-moves', type=int, default=200)
    ap.add_argument('--our-team', choices=['red', 'blue'], default='red')
    args = ap.parse_args()

    try:
        result = run_phase1_game(
            red_team=args.red,
            blue_team=args.blue,
            layout_name=args.layout,
            seed=args.seed,
            max_moves=args.max_moves,
            our_team=args.our_team,
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        result = {'outcome': 'crashed',
                  'crash_reason': f'toplevel:{type(e).__name__}:{e}',
                  'moves': 0, 'a_food_eaten': 0, 'wall_sec': 0.0}
    _emit(result)


if __name__ == '__main__':
    main()

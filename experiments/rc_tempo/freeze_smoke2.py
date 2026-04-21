#!/usr/bin/env python3
"""freeze_smoke2.py — extended tests with β + stateful opponents.

Tests:
 5. β vs baseline, approach (a): registerInitialState(mid_state) on load.
 6. β vs baseline, approach (b): registerInitialState(initial_state) → overwrite state.
 7. β vs monster_rule_expert, approach (b).
 8. β vs zoo_reflex_rc82, approach (b).
 9. β vs zoo_reflex_rc_tempo_beta (self-play), approach (b).
10. Cross-variant swap: run 50 with β_v2d → load → swap in β with BETA_PATH_ABORT_RATIO=4 → run 50 → vs fresh β_path4 full run (expect DIFFERENT hash — but both should run without crash).

Approach (b) = the one we want architecturally: call registerInitialState
with the ORIGINAL initial state so β precomputes plans correctly, then
overwrite game.state with the saved mid-game state.
"""
from __future__ import annotations
import hashlib
import os
import pickle
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
os.chdir(str(MINICONTEST))
if str(MINICONTEST) not in sys.path:
    sys.path.insert(0, str(MINICONTEST))

from capture import CaptureRules, loadAgents
from layout import getLayout
import textDisplay


def make_game(red_name, blue_name, layout_name='defaultCapture', seed=42,
              register=True):
    random.seed(seed)
    lay = getLayout(layout_name, 3)
    assert lay is not None
    red_agents = loadAgents(True, red_name, False, {})
    blue_agents = loadAgents(False, blue_name, False, {})
    agents = [red_agents[0], blue_agents[0], red_agents[1], blue_agents[1]]
    display = textDisplay.NullGraphics()
    rules = CaptureRules()
    rules.quiet = True
    game = rules.newGame(lay, agents, display, length=1200,
                          muteAgents=True, catchExceptions=True)
    if register:
        for a in agents:
            if hasattr(a, 'registerInitialState'):
                a.registerInitialState(game.state.deepCopy())
    return game, agents


def run_ticks(game, agents, n_ticks, start_agent=0, start_moves=0):
    agent_index = start_agent
    moves = start_moves
    end = start_moves + n_ticks
    while moves < end and not game.gameOver:
        agent = agents[agent_index]
        obs_state = game.state.deepCopy()
        try:
            obs = agent.observationFunction(obs_state) if hasattr(agent, 'observationFunction') else obs_state
        except Exception:
            obs = obs_state
        try:
            action = agent.getAction(obs)
        except Exception as e:
            print(f'  ❌ agent{agent_index} ({type(agent).__name__}) crashed: {e}')
            return agent_index, moves, False
        game.moveHistory.append((agent_index, action))
        game.state = game.state.generateSuccessor(agent_index, action)
        try:
            game.rules.process(game.state, game)
        except Exception:
            pass
        agent_index = (agent_index + 1) % len(agents)
        moves += 1
        if game.state.isOver():
            game.gameOver = True
            break
    return agent_index, moves, True


def state_hash(state):
    return hashlib.sha256(pickle.dumps(state)).hexdigest()[:12]


def mode_A(red, blue, layout, seed, total):
    game, agents = make_game(red, blue, layout, seed)
    _, _, ok = run_ticks(game, agents, total)
    if not ok:
        return None
    return state_hash(game.state)


def mode_B_approach_b(red, blue, layout, seed, split, total):
    """Approach (b): save mid-state, fresh game, registerInitialState(initial),
    overwrite game.state with mid_state, restore random, resume."""
    # Phase B.1: run split ticks in disposable game
    game, agents = make_game(red, blue, layout, seed)
    # Capture initial state AFTER registerInitialState
    initial_state_blob = pickle.dumps(game.state)
    _, _, ok = run_ticks(game, agents, split)
    if not ok:
        return None
    mid_state_blob = pickle.dumps(game.state)
    saved_random = random.getstate()

    # Phase B.2: fresh game, fresh agents, registerInitialState with INITIAL state
    random.seed(seed)  # reset random so make_game random is same as Mode A
    lay = getLayout(layout, 3)
    red_agents = loadAgents(True, red, False, {})
    blue_agents = loadAgents(False, blue, False, {})
    agents2 = [red_agents[0], blue_agents[0], red_agents[1], blue_agents[1]]
    display = textDisplay.NullGraphics()
    rules = CaptureRules()
    rules.quiet = True
    game2 = rules.newGame(lay, agents2, display, length=1200,
                           muteAgents=True, catchExceptions=True)
    # registerInitialState with ORIGINAL state (not mid_state)
    initial_state_restored = pickle.loads(initial_state_blob)
    for a in agents2:
        if hasattr(a, 'registerInitialState'):
            a.registerInitialState(initial_state_restored)
    # Overwrite game.state with mid-game state
    game2.state = pickle.loads(mid_state_blob)
    # Restore random state captured at split
    random.setstate(saved_random)
    next_agent_idx = split % 4
    _, _, ok = run_ticks(game2, agents2, total - split,
                          start_agent=next_agent_idx, start_moves=split)
    if not ok:
        return None
    return state_hash(game2.state)


def mode_B_approach_a(red, blue, layout, seed, split, total):
    """Approach (a): registerInitialState(MID_STATE) on load."""
    game, agents = make_game(red, blue, layout, seed)
    _, _, ok = run_ticks(game, agents, split)
    if not ok:
        return None
    mid_state_blob = pickle.dumps(game.state)
    saved_random = random.getstate()

    random.seed(seed)
    lay = getLayout(layout, 3)
    red_agents = loadAgents(True, red, False, {})
    blue_agents = loadAgents(False, blue, False, {})
    agents2 = [red_agents[0], blue_agents[0], red_agents[1], blue_agents[1]]
    display = textDisplay.NullGraphics()
    rules = CaptureRules()
    rules.quiet = True
    game2 = rules.newGame(lay, agents2, display, length=1200,
                           muteAgents=True, catchExceptions=True)
    # registerInitialState with MID state (incorrect but let's see what happens)
    mid_state_for_register = pickle.loads(mid_state_blob)
    for a in agents2:
        if hasattr(a, 'registerInitialState'):
            a.registerInitialState(mid_state_for_register)
    game2.state = pickle.loads(mid_state_blob)
    random.setstate(saved_random)
    next_agent_idx = split % 4
    _, _, ok = run_ticks(game2, agents2, total - split,
                          start_agent=next_agent_idx, start_moves=split)
    if not ok:
        return None
    return state_hash(game2.state)


def run_test(name, red, blue, layout='defaultCapture', seed=42,
             split=50, total=100, approach='b'):
    print(f'\n=== {name} ===')
    print(f'  red={red} blue={blue} layout={layout} seed={seed} split={split}/{total} approach={approach}')
    hA = mode_A(red, blue, layout, seed, total)
    if hA is None:
        print(f'  ❌ Mode A crashed')
        return False
    mode_B = mode_B_approach_b if approach == 'b' else mode_B_approach_a
    hB = mode_B(red, blue, layout, seed, split, total)
    if hB is None:
        print(f'  ❌ Mode B crashed')
        return False
    match = hA == hB
    print(f'  A={hA} | B={hB} | {"✓ MATCH" if match else "❌ MISMATCH"}')
    return match


if __name__ == '__main__':
    results = {}
    results['t5 β vs baseline approach(a)'] = run_test(
        't5 β vs baseline approach(a) — registerInit(mid_state)',
        'zoo_reflex_rc_tempo_beta', 'baseline', approach='a')
    results['t6 β vs baseline approach(b)'] = run_test(
        't6 β vs baseline approach(b) — registerInit(initial_state)',
        'zoo_reflex_rc_tempo_beta', 'baseline', approach='b')
    results['t7 β vs monster_rule_expert'] = run_test(
        't7 β vs monster_rule_expert',
        'zoo_reflex_rc_tempo_beta', 'monster_rule_expert', approach='b')
    results['t8 β vs rc82'] = run_test(
        't8 β vs zoo_reflex_rc82',
        'zoo_reflex_rc_tempo_beta', 'zoo_reflex_rc82', approach='b')
    results['t9 β vs rc166'] = run_test(
        't9 β vs zoo_reflex_rc166',
        'zoo_reflex_rc_tempo_beta', 'zoo_reflex_rc166', approach='b')
    results['t10 β vs β (self)'] = run_test(
        't10 β vs β self-play',
        'zoo_reflex_rc_tempo_beta', 'zoo_reflex_rc_tempo_beta', approach='b')
    results['t11 β vs baseline distantCapture'] = run_test(
        't11 β vs baseline distantCapture',
        'zoo_reflex_rc_tempo_beta', 'baseline',
        layout='distantCapture', seed=7, split=80, total=150, approach='b')

    print('\n=== Summary ===')
    for k, v in results.items():
        print(f'  {k}: {"✓ PASS" if v else "❌ FAIL"}')

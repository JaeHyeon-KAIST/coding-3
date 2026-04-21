#!/usr/bin/env python3
"""freeze_smoke.py — does pickle(game.state) give deterministic replay?

Test 1: Pickle GameState → unpickle → state equal?
Test 2: Mode A (run 100 ticks) vs Mode B (run 50 → pickle state → fresh game → unpickle state → run 50 more) → same final state?
Test 3: Same as Test 2, but also save/restore random.getstate().

Run:
    .venv/bin/python experiments/rc_tempo/freeze_smoke.py
"""
from __future__ import annotations
import os
import pickle
import random
import sys
import hashlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
MINICONTEST = REPO / "minicontest"
os.chdir(str(MINICONTEST))
if str(MINICONTEST) not in sys.path:
    sys.path.insert(0, str(MINICONTEST))

from capture import CaptureRules, loadAgents
from layout import getLayout
import textDisplay


def make_game(red_name='baseline', blue_name='baseline',
              layout_name='defaultCapture', seed=42):
    random.seed(seed)
    lay = getLayout(layout_name, 3)
    assert lay is not None, f"layout {layout_name} not found"
    red_agents = loadAgents(True, red_name, False, {})
    blue_agents = loadAgents(False, blue_name, False, {})
    agents = [red_agents[0], blue_agents[0], red_agents[1], blue_agents[1]]
    display = textDisplay.NullGraphics()
    rules = CaptureRules()
    rules.quiet = True
    game = rules.newGame(lay, agents, display, length=1200,
                          muteAgents=True, catchExceptions=True)
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
        except Exception as e:
            print(f'obs failed idx={agent_index}: {e}')
            raise
        try:
            action = agent.getAction(obs)
        except Exception as e:
            print(f'getAction failed idx={agent_index}: {e}')
            raise
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
    return agent_index, moves


def state_hash(state):
    return hashlib.sha256(pickle.dumps(state)).hexdigest()[:12]


def state_summary(state):
    pos = [state.getAgentPosition(i) for i in range(state.getNumAgents())]
    score = state.getScore()
    red_food = state.getRedFood().count()
    blue_food = state.getBlueFood().count()
    red_cap = len(state.getRedCapsules())
    blue_cap = len(state.getBlueCapsules())
    return {
        'pos': pos,
        'score': score,
        'red_food': red_food,
        'blue_food': blue_food,
        'red_cap': red_cap,
        'blue_cap': blue_cap,
        'hash': state_hash(state),
    }


def test1_pickle_roundtrip():
    print('\n=== Test 1: pickle roundtrip ===')
    game, agents = make_game(seed=42)
    run_ticks(game, agents, 50)
    try:
        blob = pickle.dumps(game.state)
        print(f'  pickle OK, size={len(blob)} bytes')
    except Exception as e:
        print(f'  ❌ pickle FAILED: {e}')
        return False
    try:
        restored = pickle.loads(blob)
    except Exception as e:
        print(f'  ❌ unpickle FAILED: {e}')
        return False
    h1 = state_hash(game.state)
    h2 = state_hash(restored)
    match = h1 == h2
    print(f'  original hash: {h1}')
    print(f'  restored hash: {h2}')
    print(f'  match: {"✓" if match else "❌"}')
    return match


def test2_replay_without_random_restore():
    print('\n=== Test 2: A(100) vs B(50→save→new game→load→50) — NO random state restore ===')
    # Mode A
    gameA, agentsA = make_game(seed=42)
    run_ticks(gameA, agentsA, 100)
    sumA = state_summary(gameA.state)
    print(f'  A final: score={sumA["score"]}, pos={sumA["pos"]}, hash={sumA["hash"]}')

    # Mode B
    gameB, agentsB = make_game(seed=42)
    _, moves_b = run_ticks(gameB, agentsB, 50)
    sumB_50 = state_summary(gameB.state)
    print(f'  B@50: score={sumB_50["score"]}, pos={sumB_50["pos"]}, hash={sumB_50["hash"]}')
    saved_blob = pickle.dumps(gameB.state)

    # Fresh game, load state, continue
    gameB2, agentsB2 = make_game(seed=42)  # resets random!
    gameB2.state = pickle.loads(saved_blob)
    # Our A has team index 0, so agents move in order 0,1,2,3,0,1,2,3,...
    # After 50 moves, next agent_index = 50 % 4 = 2
    next_agent_idx = 50 % 4
    run_ticks(gameB2, agentsB2, 50, start_agent=next_agent_idx, start_moves=50)
    sumB = state_summary(gameB2.state)
    print(f'  B final: score={sumB["score"]}, pos={sumB["pos"]}, hash={sumB["hash"]}')

    match = sumA['hash'] == sumB['hash']
    print(f'  match: {"✓" if match else "❌"}')
    return match


def test3_replay_with_random_restore():
    print('\n=== Test 3: same as Test 2, but WITH random.getstate()/setstate() ===')
    gameA, agentsA = make_game(seed=42)
    run_ticks(gameA, agentsA, 100)
    sumA = state_summary(gameA.state)
    print(f'  A final: hash={sumA["hash"]}')

    gameB, agentsB = make_game(seed=42)
    run_ticks(gameB, agentsB, 50)
    saved_blob = pickle.dumps(gameB.state)
    saved_random = random.getstate()

    gameB2, agentsB2 = make_game(seed=42)  # random reset
    gameB2.state = pickle.loads(saved_blob)
    random.setstate(saved_random)  # restore random state
    next_agent_idx = 50 % 4
    run_ticks(gameB2, agentsB2, 50, start_agent=next_agent_idx, start_moves=50)
    sumB = state_summary(gameB2.state)
    print(f'  B final: hash={sumB["hash"]}')

    match = sumA['hash'] == sumB['hash']
    print(f'  match: {"✓" if match else "❌"}')
    return match


def test4_replay_reuse_agents():
    """Does keeping the SAME agent instances (no re-registerInitialState) help?"""
    print('\n=== Test 4: reuse SAME agent instances, random restore ===')
    gameA, agentsA = make_game(seed=42)
    run_ticks(gameA, agentsA, 100)
    sumA = state_summary(gameA.state)
    print(f'  A final: hash={sumA["hash"]}')

    gameB, agentsB = make_game(seed=42)
    run_ticks(gameB, agentsB, 50)
    saved_blob = pickle.dumps(gameB.state)
    saved_random = random.getstate()

    # Reuse the SAME game+agents; overwrite state and random.
    gameB.state = pickle.loads(saved_blob)
    random.setstate(saved_random)
    next_agent_idx = 50 % 4
    run_ticks(gameB, agentsB, 50, start_agent=next_agent_idx, start_moves=50)
    sumB = state_summary(gameB.state)
    print(f'  B final: hash={sumB["hash"]}')
    match = sumA['hash'] == sumB['hash']
    print(f'  match: {"✓" if match else "❌"}')
    return match


if __name__ == '__main__':
    print(f'cwd: {os.getcwd()}')
    results = {}
    results['test1_pickle'] = test1_pickle_roundtrip()
    results['test2_no_rand_restore'] = test2_replay_without_random_restore()
    results['test3_with_rand_restore'] = test3_replay_with_random_restore()
    results['test4_reuse_agents'] = test4_replay_reuse_agents()
    print('\n=== Summary ===')
    for k, v in results.items():
        print(f'  {k}: {"✓ PASS" if v else "❌ FAIL"}')

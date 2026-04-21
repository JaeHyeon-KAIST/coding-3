#!/usr/bin/env python3
"""freeze_smoke3.py — confirm freeze works for monster by also saving TEAM.

Module-level singletons that must be saved/restored:
 * zoo_core.TEAM  — shared by all CoreCaptureAgent descendants; monster's
                    anchor rotation reads TEAM.tick.
 * zoo_reflex_rc_tempo_beta.RCTEMPO_TEAM — β's own team state (re-built
   fresh on load via registerInitialState(initial_state)).

Test 12: β vs monster_rule_expert WITH TEAM state save/restore.
Test 13: β vs monster, different layout + seed.
Test 14: β vs monster_mcts_hand (also reads TEAM.tick).
"""
from __future__ import annotations
import copy
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


def snapshot_modstate():
    """Deep-copy snapshot of all module-level team singletons we know about."""
    out = {}
    import zoo_core
    out['zoo_core.TEAM'] = copy.deepcopy(zoo_core.TEAM.__dict__)
    # Optional: also capture RCTEMPO_TEAM etc., but these are typically
    # rebuilt by registerInitialState(initial_state). We only restore if
    # the agent is being loaded fresh WITHOUT re-registering.
    try:
        import zoo_reflex_rc_tempo_beta as _beta
        out['zoo_reflex_rc_tempo_beta.RCTEMPO_TEAM'] = copy.deepcopy(_beta.RCTEMPO_TEAM.__dict__)
    except Exception:
        pass
    return out


def restore_modstate(snap):
    import zoo_core
    if 'zoo_core.TEAM' in snap:
        zoo_core.TEAM.__dict__.update(copy.deepcopy(snap['zoo_core.TEAM']))
    # NOTE: we do NOT restore RCTEMPO_TEAM because we want the freshly loaded
    # β variant to have its own precomputed plans via registerInitialState.


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
    import zoo_core
    zoo_core.TEAM.force_reinit()  # reset TEAM across test cases
    game, agents = make_game(red, blue, layout, seed)
    _, _, ok = run_ticks(game, agents, total)
    if not ok:
        return None
    return state_hash(game.state)


def mode_B_with_modstate(red, blue, layout, seed, split, total):
    """Save+restore zoo_core.TEAM + random + game.state.
    Use approach (b): registerInitialState(initial_state), overwrite state."""
    import zoo_core
    zoo_core.TEAM.force_reinit()
    game, agents = make_game(red, blue, layout, seed)
    initial_state_blob = pickle.dumps(game.state)
    _, _, ok = run_ticks(game, agents, split)
    if not ok:
        return None
    mid_state_blob = pickle.dumps(game.state)
    saved_random = random.getstate()
    saved_modstate = snapshot_modstate()

    # Fresh game
    zoo_core.TEAM.force_reinit()  # pretend fresh process
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
    initial_state_restored = pickle.loads(initial_state_blob)
    for a in agents2:
        if hasattr(a, 'registerInitialState'):
            a.registerInitialState(initial_state_restored)

    # Overwrite game.state + restore random + restore TEAM
    game2.state = pickle.loads(mid_state_blob)
    random.setstate(saved_random)
    restore_modstate(saved_modstate)

    next_agent_idx = split % 4
    _, _, ok = run_ticks(game2, agents2, total - split,
                          start_agent=next_agent_idx, start_moves=split)
    if not ok:
        return None
    return state_hash(game2.state)


def run_test(name, red, blue, layout='defaultCapture', seed=42,
             split=50, total=100):
    print(f'\n=== {name} ===')
    print(f'  red={red} blue={blue} layout={layout} seed={seed} split={split}/{total}')
    hA = mode_A(red, blue, layout, seed, total)
    if hA is None:
        print(f'  ❌ Mode A crashed')
        return False
    hB = mode_B_with_modstate(red, blue, layout, seed, split, total)
    if hB is None:
        print(f'  ❌ Mode B crashed')
        return False
    match = hA == hB
    print(f'  A={hA} | B={hB} | {"✓ MATCH" if match else "❌ MISMATCH"}')
    return match


if __name__ == '__main__':
    results = {}
    results['t12 β vs monster (with TEAM restore)'] = run_test(
        't12 β vs monster_rule_expert — WITH zoo_core.TEAM restore',
        'zoo_reflex_rc_tempo_beta', 'monster_rule_expert')
    results['t13 β vs monster distantCapture'] = run_test(
        't13 β vs monster distantCapture seed=7',
        'zoo_reflex_rc_tempo_beta', 'monster_rule_expert',
        layout='distantCapture', seed=7, split=80, total=150)
    results['t14 β vs monster_mcts_hand'] = run_test(
        't14 β vs monster_mcts_hand',
        'zoo_reflex_rc_tempo_beta', 'monster_mcts_hand',
        split=60, total=120)

    print('\n=== Summary ===')
    for k, v in results.items():
        print(f'  {k}: {"✓ PASS" if v else "❌ FAIL"}')

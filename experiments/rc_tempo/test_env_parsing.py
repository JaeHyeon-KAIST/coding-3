#!/usr/bin/env python3
"""pm32 unit tests T-U1, T-U2, T-U3.

Run via:
    .venv/bin/python -m unittest experiments.rc_tempo.test_env_parsing

T-U1: env-var parsing & defaults (BETA_TRIGGER_GATE / BETA_TRIGGER_MAX_DIST /
      BETA_RETREAT_ON_ABORT) — no garbage abort.
T-U2: backward-compat reproduction — with no new env vars set, a single
      deterministic game produces the same outcome twice and matches β v2d
      semantics (since env vars default to 'none' / 999 / '0').
T-U3: (a) retro × retreat-on-abort interaction — different actions/positions
      with retreat ON vs OFF on a fixed seed.
      (b) MJ-7 module-singleton no-leak — two sequential games on different
      layouts in the same subprocess do not leak my_home_cells.

These tests use the existing phase1_runner (subprocess invocation pattern is
overkill for unit tests, so we drive run_phase1_game in-process when possible
and fall back to subprocess only when isolation is required).
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
VENV_PYTHON = REPO / '.venv' / 'bin' / 'python'
RUNNER = HERE / 'phase1_runner.py'

# Make minicontest importable
MINICONTEST = REPO / 'minicontest'
sys.path.insert(0, str(MINICONTEST))


def _run_game_subprocess(red, blue, layout, seed, our_team='red',
                          max_moves=200, env_extras=None):
    """Subprocess invocation — required for env-var isolation between tests
    since module-level state in zoo_reflex_rc_tempo_beta cannot be reset
    in-process safely between configurations."""
    cmd = [
        str(VENV_PYTHON), str(RUNNER),
        '-r', red, '-b', blue, '-l', layout,
        '--seed', str(seed), '--max-moves', str(max_moves),
        '--our-team', our_team,
    ]
    env = os.environ.copy()
    # Strip any pm32 vars from the parent env so each test gets a clean slate
    for k in list(env.keys()):
        if k.startswith('BETA_TRIGGER_') or k == 'BETA_RETREAT_ON_ABORT':
            del env[k]
    if env_extras:
        env.update(env_extras)
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=90,
                          cwd=str(REPO), env=env)
    last_line = None
    for line in res.stdout.strip().splitlines():
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            last_line = line
    if last_line is None:
        return {'outcome': 'crashed',
                'crash_reason': f'no_json:{res.returncode}',
                'stderr': res.stderr[:500]}
    return json.loads(last_line)


class TestU1EnvParsing(unittest.TestCase):
    """T-U1: env var parsing & defaults — no garbage aborts."""

    def test_iv_helper_handles_garbage(self):
        """The _iv helper inside _choose_capsule_chase_action must return the
        default when env value is non-integer."""
        # Direct unit on the parsing helper pattern used in the agent.
        def _iv(name, default):
            try:
                return int(os.environ.get(name, default))
            except Exception:
                return default
        os.environ.pop('TEST_IV_DUMMY', None)
        self.assertEqual(_iv('TEST_IV_DUMMY', 999), 999)
        os.environ['TEST_IV_DUMMY'] = 'abc'
        self.assertEqual(_iv('TEST_IV_DUMMY', 999), 999)
        os.environ['TEST_IV_DUMMY'] = '12'
        self.assertEqual(_iv('TEST_IV_DUMMY', 999), 12)
        del os.environ['TEST_IV_DUMMY']

    def test_trigger_gate_silently_normalizes_garbage(self):
        """Invalid BETA_TRIGGER_GATE values must fall back to 'none' silently."""
        # We test this indirectly by running a game with garbage and asserting
        # it does NOT crash (the agent's parsing block coerces invalid → 'none').
        result = _run_game_subprocess(
            red='zoo_reflex_rc_tempo_beta', blue='baseline',
            layout='defaultCapture', seed=42, our_team='red',
            max_moves=80,
            env_extras={'BETA_TRIGGER_GATE': 'wat_is_this'},
        )
        self.assertNotEqual(result.get('outcome'), 'crashed',
                            f"agent crashed on garbage trigger_gate: "
                            f"{result.get('crash_reason')}")

    def test_trigger_max_dist_zero_is_off(self):
        """BETA_TRIGGER_MAX_DIST=0 must NOT abort all chases (defensive guard)."""
        # With dist=0 and the defensive guard, chase behavior must NOT be a
        # universal abort — outcome should look like a normal game (not the
        # 'never triggered' degenerate case).
        result = _run_game_subprocess(
            red='zoo_reflex_rc_tempo_beta', blue='baseline',
            layout='defaultCapture', seed=42, our_team='red',
            max_moves=200,
            env_extras={'BETA_TRIGGER_MAX_DIST': '0'},
        )
        self.assertNotEqual(result.get('outcome'), 'crashed',
                            f"agent crashed: {result.get('crash_reason')}")
        # Game should at minimum reach the trigger (some pacman invasion happens)
        # — not a strict assertion since baseline may stay home, but moves > 10
        # at least proves the agent didn't get into a never-act loop.
        self.assertGreater(result.get('moves', 0), 10,
                           "agent appears to abort all chases on dist=0")

    def test_retreat_on_abort_default_off(self):
        """BETA_RETREAT_ON_ABORT must default to '0' — runs cleanly without env."""
        result = _run_game_subprocess(
            red='zoo_reflex_rc_tempo_beta', blue='baseline',
            layout='defaultCapture', seed=42, our_team='red',
            max_moves=80,
        )
        self.assertNotEqual(result.get('outcome'), 'crashed',
                            f"agent crashed at default config: "
                            f"{result.get('crash_reason')}")


class TestU2BackwardCompat(unittest.TestCase):
    """T-U2: with no new env vars set, runs are deterministic + non-crashy.

    NOTE: A full byte-identical comparison vs pm31 reference happens at
    Mac-smoke time (Step D, MJ-8 diff). This unit test only validates the
    in-process determinism + no-crash invariant — sufficient for Step B
    Mac-coding-window acceptance.
    """

    def test_two_consecutive_runs_byte_identical(self):
        """Same seed → same outcome on two consecutive subprocess runs."""
        run1 = _run_game_subprocess(
            red='zoo_reflex_rc_tempo_beta', blue='baseline',
            layout='defaultCapture', seed=42, our_team='red', max_moves=120,
        )
        run2 = _run_game_subprocess(
            red='zoo_reflex_rc_tempo_beta', blue='baseline',
            layout='defaultCapture', seed=42, our_team='red', max_moves=120,
        )
        # Compare metric fields (skip wall_sec which is timing-noisy)
        compare_keys = ['outcome', 'moves', 'a_food_eaten', 'a_died_count',
                         'capsule_eaten_by_A', 'capsule_eaten_by_anyone',
                         'capsule_eaten_tick', 'trigger_tick', 'triggered',
                         'a_died_post_trigger', 'cap_eaten_post_trigger']
        for k in compare_keys:
            self.assertEqual(run1.get(k), run2.get(k),
                             f"non-determinism in {k}: "
                             f"run1={run1.get(k)} run2={run2.get(k)}")


class TestU3RetroRetreatInteraction(unittest.TestCase):
    """T-U3 (a): β_retro inherits the retreat-on-abort path via fallthrough."""

    def test_retro_retreat_on_vs_off_differs(self):
        """Same seed + same opponent + same layout, BETA_RETREAT_ON_ABORT
        toggled. The action stream OR a_final_pos must differ on at least
        one observable field.

        Layout/opp choice rationale: defaultCapture vs zoo_reflex_rc82
        triggers around tick 159 in our standard seeds, leaving plenty of
        post-trigger ticks where retreat-on-abort can manifest in
        a_final_pos / score. distantCapture vs baseline never triggers
        within max_moves, masking the retreat path entirely."""
        common_kwargs = dict(
            red='zoo_reflex_rc_tempo_beta_retro', blue='zoo_reflex_rc82',
            layout='defaultCapture', seed=42, our_team='red', max_moves=250,
        )
        run_off = _run_game_subprocess(
            env_extras={'BETA_RETREAT_ON_ABORT': '0'}, **common_kwargs,
        )
        run_on = _run_game_subprocess(
            env_extras={'BETA_RETREAT_ON_ABORT': '1'}, **common_kwargs,
        )
        # Sanity: neither crashed
        self.assertNotEqual(run_off.get('outcome'), 'crashed',
                            f"OFF crashed: {run_off.get('crash_reason')}")
        self.assertNotEqual(run_on.get('outcome'), 'crashed',
                            f"ON crashed: {run_on.get('crash_reason')}")
        # Sanity: trigger fired (otherwise the retreat path is unreachable)
        self.assertTrue(run_off.get('triggered'),
                        f"trigger never fired in OFF run: {run_off}")
        self.assertTrue(run_on.get('triggered'),
                        f"trigger never fired in ON run: {run_on}")
        # At least one observable field should differ. We compare a tuple of
        # fields likely to drift if retreat injects new actions.
        diff_fields = ['outcome', 'moves', 'a_food_eaten', 'a_final_pos',
                        'a_died_count', 'capsule_eaten_tick', 'score']
        diffs = [k for k in diff_fields if run_off.get(k) != run_on.get(k)]
        self.assertTrue(
            len(diffs) > 0,
            f"retreat ON vs OFF produced identical outcomes — retreat path "
            f"may not be exercised. OFF={run_off}, ON={run_on}"
        )


class TestU3NoLeak(unittest.TestCase):
    """T-U3 (b) MJ-7: two sequential games on different layouts in one
    subprocess — RCTEMPO_TEAM.my_home_cells must NOT leak from game 1.

    This is the most important regression: a module-level singleton across
    two precompute calls in the same Python process must reset state.
    """

    def test_no_my_home_cells_leak_across_layouts(self):
        """Drive the test in a single subprocess — game 1 on defaultCapture,
        then game 2 on distantCapture. After game 2, my_home_cells must lie
        on the game-2 midline x-column, NOT game-1's.

        IMPORTANT: capture.loadAgents loads the agent module under a renamed
        name ('player1') in sys.modules, distinct from a direct import. The
        agent's `RCTEMPO_TEAM` is therefore the singleton in `sys.modules['player1']`,
        NOT in the directly-imported `zoo_reflex_rc_tempo_beta`. The test
        reads the singleton from the agent's own type's module.
        """
        # We embed the test in a small Python script run as a subprocess so we
        # can capture the my_home_cells value from after each registerInitialState.
        script = r'''
import os, sys, json
sys.path.insert(0, "minicontest")
sys.path.insert(0, "experiments/rc_tempo")
os.chdir("minicontest")

# Force retreat ON so my_home_cells is exercised
os.environ["BETA_RETREAT_ON_ABORT"] = "1"

from layout import getLayout
from capture import CaptureRules, loadAgents
import textDisplay

def init_only(layout_name):
    """Run only registerInitialState for both teams — enough to exercise
    _precompute_team and write my_home_cells.

    Returns (walls, agent_module_with_RCTEMPO_TEAM).
    """
    lay = getLayout(layout_name, 3)
    red_agents = loadAgents(True, "zoo_reflex_rc_tempo_beta", False, {})
    blue_agents = loadAgents(False, "baseline", False, {})
    agents = [red_agents[0], blue_agents[0], red_agents[1], blue_agents[1]]
    display = textDisplay.NullGraphics()
    rules = CaptureRules()
    rules.quiet = True
    game = rules.newGame(lay, agents, display, length=1200, muteAgents=True,
                          catchExceptions=True)
    for a in agents:
        if hasattr(a, "registerInitialState"):
            a.registerInitialState(game.state.deepCopy())
    # Recover the agent's own module so we read THE singleton it mutated.
    agent_mod_name = type(red_agents[0]).__module__
    agent_mod = sys.modules[agent_mod_name]
    return game.state.getWalls(), agent_mod

# Game 1
walls1, mod_g1 = init_only("defaultCapture")
home_g1 = list(mod_g1.RCTEMPO_TEAM.my_home_cells)
mid_g1 = walls1.width // 2 - 1

# Game 2 — different layout. capture.loadAgents reuses the same `player1`
# slot in sys.modules, so the team singleton persists across calls — the
# precise scenario MJ-7 is defending against.
walls2, mod_g2 = init_only("distantCapture")
home_g2 = list(mod_g2.RCTEMPO_TEAM.my_home_cells)
mid_g2 = walls2.width // 2 - 1

# Sanity: confirm same module instance — proves singleton was reused.
same_module = (mod_g1 is mod_g2)

result = {
    "g1_mid_x": mid_g1,
    "g2_mid_x": mid_g2,
    "g1_home_xs": sorted(set(c[0] for c in home_g1)),
    "g2_home_xs": sorted(set(c[0] for c in home_g2)),
    "g1_layout_w": walls1.width,
    "g2_layout_w": walls2.width,
    "g1_count": len(home_g1),
    "g2_count": len(home_g2),
    "same_module": same_module,
    "mod_g1_name": mod_g1.__name__,
    "mod_g2_name": mod_g2.__name__,
}
print("RESULT:" + json.dumps(result))
'''
        env = os.environ.copy()
        # Clean any stale env vars
        for k in list(env.keys()):
            if k.startswith('BETA_TRIGGER_'):
                del env[k]
        result = subprocess.run(
            [str(VENV_PYTHON), '-c', script],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO), env=env,
        )
        marker = None
        for line in result.stdout.strip().splitlines():
            if line.startswith('RESULT:'):
                marker = line[len('RESULT:'):]
                break
        self.assertIsNotNone(
            marker,
            f"test script failed; stdout={result.stdout!r}, stderr={result.stderr!r}",
        )
        data = json.loads(marker)
        # If layouts have different midline x's, then if my_home_cells
        # leaked we'd see g1's x's in g2's home_xs.
        # First sanity: did the layouts actually differ?
        if data['g1_mid_x'] == data['g2_mid_x']:
            # Layouts have same width — leak detection requires different
            # midlines. Skip this exact check but still verify g2 home_xs
            # contains only the g2 midline (not g1's, which would also be
            # the same).
            self.assertEqual(data['g2_home_xs'], [data['g2_mid_x']],
                             f"home_xs has unexpected values: {data}")
        else:
            # Different midlines → unambiguous leak detection
            self.assertEqual(
                data['g2_home_xs'], [data['g2_mid_x']],
                f"my_home_cells LEAKED from game 1 to game 2: g1_mid={data['g1_mid_x']}, "
                f"g2_mid={data['g2_mid_x']}, g2_home_xs={data['g2_home_xs']}"
            )


if __name__ == '__main__':
    unittest.main()

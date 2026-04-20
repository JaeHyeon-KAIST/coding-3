#!/usr/bin/env python3
"""Slow-motion capture.py launcher. Patches PacmanGraphics frameTime before running.

Usage:
  CAPTURE_FRAME_TIME=0.3 .venv/bin/python experiments/play_slow.py \
      -r zoo_reflex_rc166 -b baseline -l defaultCapture -n 1

Default frameTime = 0.3s per move.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MINICONTEST = os.path.join(HERE, '..', 'minicontest')
sys.path.insert(0, MINICONTEST)
os.chdir(MINICONTEST)

import captureGraphicsDisplay

_FRAME_TIME = float(os.environ.get('CAPTURE_FRAME_TIME', '0.3'))

_orig_init = captureGraphicsDisplay.PacmanGraphics.__init__


def _patched_init(self, redTeam, blueTeam, zoom=1.0, frameTime=0.0, capture=False):
    _orig_init(self, redTeam, blueTeam, zoom, _FRAME_TIME, capture)


captureGraphicsDisplay.PacmanGraphics.__init__ = _patched_init

import capture  # noqa: E402

options = capture.readCommand(sys.argv[1:], 'baseline')
capture.runGames(**options)

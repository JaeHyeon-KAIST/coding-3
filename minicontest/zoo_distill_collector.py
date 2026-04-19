# zoo_distill_collector.py
# ------------------------
# rc22 Policy Distillation — data collection agent.
#
# Subclasses ReflexRC82Agent (teacher). On each turn, logs to a JSONL file:
#   { "legal":    [action_idx, ...],          # indices of legal actions
#     "feats":    [[20 floats], ...],          # φ(s, a) per legal action
#     "chosen":   action_idx,                  # teacher's choice (from rc82)
#     "agent":    self.index,
#     "turn":     monotonic turn counter }
#
# The student is a small MLP trained to mimic rc82's action over the same
# feature space. Log path comes from env var `RC22_LOG_PATH`; missing env →
# no logging (agent behaves as vanilla rc82).
#
# NOT a submission file — exists only for training data collection.

from __future__ import annotations

import json
import os
from pathlib import Path

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_features import extract_features
from game import Directions


# Canonical feature order — must match training/inference scripts exactly.
FEATURE_KEYS = [
    'f_bias',
    'f_successorScore',
    'f_distToFood',
    'f_distToCapsule',
    'f_numCarrying',
    'f_distToHome',
    'f_ghostDist1',
    'f_ghostDist2',
    'f_inDeadEnd',
    'f_stop',
    'f_reverse',
    'f_numInvaders',
    'f_invaderDist',
    'f_onDefense',
    'f_patrolDist',
    'f_distToCapsuleDefend',
    'f_scaredFlee',
    'f_scaredGhostChase',
    'f_returnUrgency',
    'f_teammateSpread',
]

ACTION_TO_IDX = {
    Directions.NORTH: 0,
    Directions.SOUTH: 1,
    Directions.EAST:  2,
    Directions.WEST:  3,
    Directions.STOP:  4,
}


class DistillCollectorAgent(ReflexRC82Agent):
    """rc82 teacher + per-turn (feat, action) logger."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc22_turn_counter = 0
        self._rc22_log_path = os.environ.get("RC22_LOG_PATH", "")

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)

        # Compute features for every legal action BEFORE the teacher picks —
        # otherwise rc82's internal history would differ.
        feats_per_action = []
        legal_idxs = []
        for a in legal:
            try:
                f = extract_features(self, gameState, a)
                vec = [f.get(k, 0.0) for k in FEATURE_KEYS]
            except Exception:
                vec = [0.0] * len(FEATURE_KEYS)
            feats_per_action.append(vec)
            legal_idxs.append(ACTION_TO_IDX.get(a, 4))  # STOP fallback

        # Run teacher.
        chosen = super()._chooseActionImpl(gameState)
        chosen_idx = ACTION_TO_IDX.get(chosen, 4)

        # Log (best-effort — any exception here must not break play).
        try:
            if self._rc22_log_path:
                rec = {
                    "legal": legal_idxs,
                    "feats": feats_per_action,
                    "chosen": chosen_idx,
                    "agent": int(self.index),
                    "turn": int(self._rc22_turn_counter),
                }
                # Append one JSON line per turn — robust to concurrent processes.
                with open(self._rc22_log_path, "a") as fh:
                    fh.write(json.dumps(rec) + "\n")
        except Exception:
            pass

        self._rc22_turn_counter += 1
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="DistillCollectorAgent", second="DistillCollectorAgent"):
    return [DistillCollectorAgent(firstIndex), DistillCollectorAgent(secondIndex)]

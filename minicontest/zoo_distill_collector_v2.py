# zoo_distill_collector_v2.py
# ---------------------------
# rc22-v2 Policy Distillation — EXTENDED feature collector.
#
# Feature vector (39 dims per legal action):
#   - 20 base features from zoo_features.extract_features(agent, state, action)
#     (depends on action — successor-state features already vary by action)
#   - 15 history one-hot:  last-3 own actions × 5 directions (N/S/E/W/Stop)
#     (state-level — same for each action at a given turn; lets student learn
#      rc82's REVERSE-disruption trigger that depends on history)
#   - 1  successor articulation-point flag (depends on action — whether the
#     successor position is in self.bottlenecks)
#   - 3  phase one-hot (state-level: early/mid/endgame per rc44's convention
#     turn thresholds 75 and 225)
#
# Logs to `RC22_LOG_PATH` env var (same JSONL format as v1, different width).

from __future__ import annotations

import json
import os
from collections import deque

from zoo_reflex_rc82 import ReflexRC82Agent
from zoo_features import extract_features
from game import Directions


FEATURE_KEYS_V1 = [
    'f_bias', 'f_successorScore', 'f_distToFood', 'f_distToCapsule',
    'f_numCarrying', 'f_distToHome', 'f_ghostDist1', 'f_ghostDist2',
    'f_inDeadEnd', 'f_stop', 'f_reverse', 'f_numInvaders',
    'f_invaderDist', 'f_onDefense', 'f_patrolDist',
    'f_distToCapsuleDefend', 'f_scaredFlee',
    'f_scaredGhostChase', 'f_returnUrgency', 'f_teammateSpread',
]
HIST_KEYS = [
    f'f_hist{i}_act{j}' for i in (1, 2, 3) for j in (0, 1, 2, 3, 4)
]  # 15 dims: hist1_actN, hist1_actS, ..., hist3_actStop
EXTRA_KEYS = ['f_succAP', 'f_phaseEarly', 'f_phaseMid', 'f_phaseEnd']
FEATURE_KEYS_V2 = FEATURE_KEYS_V1 + HIST_KEYS + EXTRA_KEYS  # 39 dims

ACTION_TO_IDX = {
    Directions.NORTH: 0,
    Directions.SOUTH: 1,
    Directions.EAST:  2,
    Directions.WEST:  3,
    Directions.STOP:  4,
}


def _compute_v2_features(agent, gameState, action):
    """Compute 39-dim per-action feature vector.

    Returns a list[float] of length 39 in FEATURE_KEYS_V2 order.
    Never raises — returns zeros on failure.
    """
    try:
        base = extract_features(agent, gameState, action)
        vec = [float(base.get(k, 0.0)) for k in FEATURE_KEYS_V1]
    except Exception:
        vec = [0.0] * len(FEATURE_KEYS_V1)

    # ----- history one-hot (15 dims) --------------------------------------
    hist = getattr(agent, '_hist_v2', None)
    # hist stores the agent's last own actions: hist[-1] = most recent.
    # Layout in feature vector: hist1 = most recent, hist2 = second-most, hist3 = third-most.
    hist_actions = [Directions.STOP, Directions.STOP, Directions.STOP]
    if hist is not None:
        hist_list = list(hist)  # oldest-first
        # map into positions: hist1 = hist_list[-1], hist2 = hist_list[-2], hist3 = hist_list[-3]
        for i in range(1, 4):
            if len(hist_list) >= i:
                hist_actions[i - 1] = hist_list[-i]
    hist_vec = [0.0] * 15
    for i, a in enumerate(hist_actions):
        j = ACTION_TO_IDX.get(a, 4)
        hist_vec[i * 5 + j] = 1.0
    vec.extend(hist_vec)

    # ----- successor AP flag (1 dim) --------------------------------------
    succ_ap = 0.0
    try:
        successor = gameState.generateSuccessor(agent.index, action)
        pos = successor.getAgentState(agent.index).getPosition()
        if pos is not None:
            try:
                bottlenecks = agent.bottlenecks or frozenset()
                spos = (int(pos[0]), int(pos[1]))
                succ_ap = 1.0 if spos in bottlenecks else 0.0
            except Exception:
                succ_ap = 0.0
    except Exception:
        succ_ap = 0.0
    vec.append(succ_ap)

    # ----- phase one-hot (3 dims) -----------------------------------------
    turn = int(getattr(agent, '_turn_counter_v2', 0))
    phase = [0.0, 0.0, 0.0]
    if turn < 75:
        phase[0] = 1.0
    elif turn <= 225:
        phase[1] = 1.0
    else:
        phase[2] = 1.0
    vec.extend(phase)

    return vec


class DistillCollectorV2Agent(ReflexRC82Agent):
    """rc82 teacher + 39-dim feature logger (history + AP + phase)."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._hist_v2 = deque(maxlen=3)
        self._turn_counter_v2 = 0
        self._rc22_log_path = os.environ.get("RC22_LOG_PATH", "")

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)

        # Build extended features per legal action BEFORE teacher picks —
        # history reflects the state up to (not including) this turn's action.
        feats_per_action = []
        legal_idxs = []
        for a in legal:
            vec = _compute_v2_features(self, gameState, a)
            feats_per_action.append(vec)
            legal_idxs.append(ACTION_TO_IDX.get(a, 4))

        # Run teacher.
        chosen = super()._chooseActionImpl(gameState)
        chosen_idx = ACTION_TO_IDX.get(chosen, 4)

        # Log.
        try:
            if self._rc22_log_path:
                rec = {
                    "legal": legal_idxs,
                    "feats": feats_per_action,
                    "chosen": chosen_idx,
                    "agent": int(self.index),
                    "turn": int(self._turn_counter_v2),
                }
                with open(self._rc22_log_path, "a") as fh:
                    fh.write(json.dumps(rec) + "\n")
        except Exception:
            pass

        # Update history (our OWN action only) and turn counter.
        try:
            self._hist_v2.append(chosen)
        except Exception:
            pass
        self._turn_counter_v2 += 1
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="DistillCollectorV2Agent", second="DistillCollectorV2Agent"):
    return [DistillCollectorV2Agent(firstIndex), DistillCollectorV2Agent(secondIndex)]

# zoo_distill_rc22_v2.py
# ----------------------
# rc22-v2 Policy Distillation STUDENT (39-dim extended features).
#
# Extends rc22-v1 (20-dim) with:
#   - 15 history one-hot (last 3 OWN actions × 5 directions)
#   - 1 successor articulation-point flag
#   - 3 phase one-hot (early / mid / endgame turn buckets)
# = 39-dim per-action feature vector.
#
# Inference: same as v1 — MLP 39→H→1 per-action Q-score, argmax pick.
# Submission-safe: numpy forward pass only.

from __future__ import annotations

import os
from collections import deque
from pathlib import Path

import numpy as np

from zoo_core import CoreCaptureAgent
from zoo_features import extract_features
from game import Directions


_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_WEIGHTS = _REPO_ROOT / "experiments" / "artifacts" / "rc22_v2" / "weights.npz"


FEATURE_KEYS_V1 = [
    'f_bias', 'f_successorScore', 'f_distToFood', 'f_distToCapsule',
    'f_numCarrying', 'f_distToHome', 'f_ghostDist1', 'f_ghostDist2',
    'f_inDeadEnd', 'f_stop', 'f_reverse', 'f_numInvaders',
    'f_invaderDist', 'f_onDefense', 'f_patrolDist',
    'f_distToCapsuleDefend', 'f_scaredFlee',
    'f_scaredGhostChase', 'f_returnUrgency', 'f_teammateSpread',
]
NUM_V1 = len(FEATURE_KEYS_V1)
NUM_V2 = 39

ACTION_TO_IDX = {
    Directions.NORTH: 0,
    Directions.SOUTH: 1,
    Directions.EAST:  2,
    Directions.WEST:  3,
    Directions.STOP:  4,
}


def _compute_v2_features(agent, gameState, action):
    """39-dim feature vector. MUST match zoo_distill_collector_v2's layout.

    Returns list[float] of length 39 or [0.0]*39 on failure. Reads:
        agent._hist_v2         — deque of recent own actions (maxlen 3)
        agent._turn_counter_v2 — int, own turn index
        agent.bottlenecks      — frozenset of AP cells (from zoo_core)
    """
    try:
        base = extract_features(agent, gameState, action)
        vec = [float(base.get(k, 0.0)) for k in FEATURE_KEYS_V1]
    except Exception:
        vec = [0.0] * NUM_V1

    # history (15 dims)
    hist_actions = [Directions.STOP, Directions.STOP, Directions.STOP]
    try:
        hist = getattr(agent, '_hist_v2', None)
        if hist is not None:
            hist_list = list(hist)
            for i in range(1, 4):
                if len(hist_list) >= i:
                    hist_actions[i - 1] = hist_list[-i]
    except Exception:
        pass
    hist_vec = [0.0] * 15
    for i, a in enumerate(hist_actions):
        j = ACTION_TO_IDX.get(a, 4)
        hist_vec[i * 5 + j] = 1.0
    vec.extend(hist_vec)

    # successor AP flag (1 dim)
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
                pass
    except Exception:
        pass
    vec.append(succ_ap)

    # phase one-hot (3 dims)
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


def _load_weights():
    path_str = os.environ.get("RC22_V2_WEIGHTS", str(_DEFAULT_WEIGHTS))
    path = Path(path_str)
    if not path.exists():
        return None
    try:
        data = np.load(path, allow_pickle=True)
        return {
            "W1": np.asarray(data["W1"], dtype=np.float64),
            "b1": np.asarray(data["b1"], dtype=np.float64),
            "W2": np.asarray(data["W2"], dtype=np.float64),
            "b2": np.asarray(data["b2"], dtype=np.float64),
            "mu": np.asarray(data["feat_mu"], dtype=np.float64),
            "sd": np.asarray(data["feat_sd"], dtype=np.float64),
        }
    except Exception:
        return None


_WEIGHTS = _load_weights()


class DistillRC22V2Agent(CoreCaptureAgent):
    """39-dim-input MLP student distilled from rc82."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._hist_v2 = deque(maxlen=3)
        self._turn_counter_v2 = 0
        self._weights = _WEIGHTS

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        w = self._weights
        if w is None:
            action = self._safeFallback(gameState, legal)
            self._record(action)
            return action

        # Build per-action feature matrix (39-dim).
        try:
            feats = [_compute_v2_features(self, gameState, a) for a in legal]
            X = np.asarray(feats, dtype=np.float64)
        except Exception:
            action = self._safeFallback(gameState, legal)
            self._record(action)
            return action

        try:
            Xn = (X - w["mu"]) / w["sd"]
            h = np.maximum(0.0, Xn @ w["W1"] + w["b1"])
            q = (h @ w["W2"] + w["b2"]).reshape(-1)
            best = int(np.argmax(q))
            if 0 <= best < len(legal):
                action = legal[best]
                self._record(action)
                return action
        except Exception:
            pass

        action = self._safeFallback(gameState, legal)
        self._record(action)
        return action

    def _record(self, action):
        try:
            self._hist_v2.append(action)
        except Exception:
            pass
        self._turn_counter_v2 += 1


def createTeam(firstIndex, secondIndex, isRed,
               first="DistillRC22V2Agent", second="DistillRC22V2Agent"):
    return [DistillRC22V2Agent(firstIndex), DistillRC22V2Agent(secondIndex)]

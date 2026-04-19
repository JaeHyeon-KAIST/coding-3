# zoo_distill_rc22.py
# --------------------
# rc22 — Policy Distillation STUDENT agent.
#
# Teacher: rc82 (rc29+rc44 combo, 100% vs baseline in pm24).
# Student: numpy MLP (20 → H → 1) scoring per legal action; argmax picks move.
#
# Architecture (Q-style scoring with softmax-CE supervision):
#     For each legal action a, let φ(s, a) be the standard 20-dim feature
#     vector from zoo_features. The student computes
#         h   = relu(W1 · ((φ − μ) / σ) + b1)
#         q   = W2 · h + b2
#         π(a|s) ∝ exp(q)
#     and picks argmax_a q (greedy). W1, b1, W2, b2 + (μ, σ) are loaded from
#     `experiments/artifacts/rc22/weights.npz`.
#
# Submission constraint (numpy + pandas only) satisfied: inference uses
# numpy matmul + relu only.

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from zoo_core import CoreCaptureAgent
from zoo_features import extract_features
from game import Directions


_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_WEIGHTS = _REPO_ROOT / "experiments" / "artifacts" / "rc22" / "weights.npz"


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
NUM_FEATS = len(FEATURE_KEYS)


def _load_weights():
    """Load trained weights. Returns dict or None on failure."""
    path_str = os.environ.get("RC22_WEIGHTS", str(_DEFAULT_WEIGHTS))
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


# Module-level singleton — loaded once per process.
_WEIGHTS = _load_weights()


class DistillRC22Agent(CoreCaptureAgent):
    """MLP-scoring student distilled from rc82."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._weights = _WEIGHTS  # may be None → falls back to preference order

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        w = self._weights
        if w is None:
            # Graceful fallback when weights file is missing: pick a non-STOP
            # legal action (inherited _safeFallback behaviour).
            return self._safeFallback(gameState, legal)

        # Build per-action feature matrix.
        try:
            feats = []
            for a in legal:
                f = extract_features(self, gameState, a)
                feats.append([f.get(k, 0.0) for k in FEATURE_KEYS])
            X = np.asarray(feats, dtype=np.float64)  # [L, 20]
        except Exception:
            return self._safeFallback(gameState, legal)

        # Normalize.
        try:
            Xn = (X - w["mu"]) / w["sd"]
        except Exception:
            Xn = X

        # Forward pass.
        try:
            h = np.maximum(0.0, Xn @ w["W1"] + w["b1"])   # [L, H]
            q = (h @ w["W2"] + w["b2"]).reshape(-1)        # [L]
            best = int(np.argmax(q))
            if 0 <= best < len(legal):
                return legal[best]
        except Exception:
            pass

        return self._safeFallback(gameState, legal)


def createTeam(firstIndex, secondIndex, isRed,
               first="DistillRC22Agent", second="DistillRC22Agent"):
    return [DistillRC22Agent(firstIndex), DistillRC22Agent(secondIndex)]

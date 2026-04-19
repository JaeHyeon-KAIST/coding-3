# zoo_rc52_trainer.py
# --------------------
# rc52 Q-learning (REINFORCE) — TRAINING AGENT.
#
# Runs with env vars:
#   RC52_WEIGHTS_PATH — JSON file with current weights {"w_off": {...}, "w_def": {...}}
#   RC52_LOG_PATH     — JSONL output path, one record per turn
#   RC52_EPSILON      — exploration rate (default 0.10)
#
# Per turn logs:
#   {"color": "red"|"blue", "agent": idx, "role": "OFFENSE"|"DEFENSE",
#    "feats": [[17 or 20 floats] per legal action],
#    "legal_count": L,
#    "chosen": local_action_idx,
#    "turn": global_turn_counter}
#
# Not a submission agent. Used only by experiments/train_rc52.py.

from __future__ import annotations

import json
import os
import random
from pathlib import Path

from zoo_reflex_tuned import ReflexTunedAgent
from zoo_features import extract_features
from zoo_core import TEAM
from game import Directions


FEATURE_KEYS = [
    'f_bias', 'f_successorScore', 'f_distToFood', 'f_distToCapsule',
    'f_numCarrying', 'f_distToHome', 'f_ghostDist1', 'f_ghostDist2',
    'f_inDeadEnd', 'f_stop', 'f_reverse', 'f_numInvaders',
    'f_invaderDist', 'f_onDefense', 'f_patrolDist',
    'f_distToCapsuleDefend', 'f_scaredFlee',
    'f_scaredGhostChase', 'f_returnUrgency', 'f_teammateSpread',
]


def _load_rc52_weights():
    """Load {"w_off": {...}, "w_def": {...}} from RC52_WEIGHTS_PATH.

    Never raises — returns empty dicts on failure so agent falls back to
    whatever ReflexTunedAgent._get_weights does (seed weights).
    """
    path_str = os.environ.get("RC52_WEIGHTS_PATH", "")
    empty = {"w_off": {}, "w_def": {}}
    if not path_str:
        return empty
    try:
        with open(path_str) as f:
            data = json.load(f)
        w_off = data.get("w_off", {}) or {}
        w_def = data.get("w_def", {}) or {}
        return {"w_off": dict(w_off), "w_def": dict(w_def)}
    except Exception:
        return empty


class RC52TrainerAgent(ReflexTunedAgent):
    """ε-greedy action selection + per-turn feature/action logger."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc52_weights = _load_rc52_weights()
        self._rc52_epsilon = float(os.environ.get("RC52_EPSILON", "0.10") or 0.10)
        self._rc52_log_path = os.environ.get("RC52_LOG_PATH", "")
        self._rc52_turn = 0
        # Attach override so ReflexTunedAgent's evaluate picks up rc52 weights.
        if self._rc52_weights.get("w_off") or self._rc52_weights.get("w_def"):
            self._weights_override = {
                "w_off": self._rc52_weights["w_off"],
                "w_def": self._rc52_weights["w_def"] or None,
                "params": {},
            }

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        # Compute per-legal-action features.
        feats_per_action = []
        for a in legal:
            try:
                f = extract_features(self, gameState, a)
                vec = [float(f.get(k, 0.0)) for k in FEATURE_KEYS]
            except Exception:
                vec = [0.0] * len(FEATURE_KEYS)
            feats_per_action.append(vec)

        # Compute Q using current weights (matches ReflexTunedAgent's evaluate).
        role = "OFFENSE"
        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            pass
        w = self._get_weights()  # ReflexTunedAgent method — role-aware

        scores = []
        for vec in feats_per_action:
            s = 0.0
            for k, key in enumerate(FEATURE_KEYS):
                s += float(w.get(key, 0.0)) * vec[k]
            scores.append(s)

        # ε-greedy pick.
        if random.random() < self._rc52_epsilon:
            chosen_local = random.randrange(len(legal))
        else:
            # argmax, stable tiebreak → first-max index
            best = scores[0]
            chosen_local = 0
            for i in range(1, len(scores)):
                if scores[i] > best:
                    best = scores[i]
                    chosen_local = i

        chosen = legal[chosen_local]

        # Log turn.
        try:
            if self._rc52_log_path:
                color = "red" if getattr(self, "red", False) else "blue"
                rec = {
                    "color": color,
                    "agent": int(self.index),
                    "role": role,
                    "feats": feats_per_action,
                    "legal_count": len(legal),
                    "chosen": int(chosen_local),
                    "turn": int(self._rc52_turn),
                }
                with open(self._rc52_log_path, "a") as fh:
                    fh.write(json.dumps(rec) + "\n")
        except Exception:
            pass

        self._rc52_turn += 1
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="RC52TrainerAgent", second="RC52TrainerAgent"):
    return [RC52TrainerAgent(firstIndex), RC52TrainerAgent(secondIndex)]

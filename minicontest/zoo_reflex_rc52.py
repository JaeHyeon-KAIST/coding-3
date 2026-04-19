# zoo_reflex_rc52.py
# -------------------
# rc52: ReflexTunedAgent pinned to REINFORCE-trained weights.
#
# Mirror of zoo_reflex_A1.py pattern — pure reflex/linear Q with weights
# learned by `experiments/train_rc52.py` (policy gradient / REINFORCE) rather
# than CEM (A1). Different learning signal, same architecture.
#
# Submission-compatible (just another weight dict; zoo_reflex_tuned handles it).

from __future__ import annotations

from pathlib import Path

from zoo_reflex_tuned import ReflexTunedAgent


_REPO_ROOT = Path(__file__).resolve().parent.parent
_RC52_WEIGHT_PATHS = [
    # Preferred: gitignored training-output location.
    _REPO_ROOT / "experiments" / "artifacts" / "rc52" / "final_weights.py",
    # Flat copy checked into the repo (used in fresh clones / submission).
    _REPO_ROOT / "experiments" / "rc52_final_weights.py",
]


def _load_rc52_override():
    """Load rc52's W_OFF/W_DEF into load_weights_override format. Never raises."""
    import importlib.util
    import sys
    for path in _RC52_WEIGHT_PATHS:
        if not path.exists():
            continue
        try:
            spec = importlib.util.spec_from_file_location("_rc52_weights", str(path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            w_off = dict(getattr(mod, "W_OFF", {}))
            w_def_raw = dict(getattr(mod, "W_DEF", {}))
            w_def = w_def_raw or None
            return {
                "w_off": w_off,
                "w_def": w_def,
                "params": dict(getattr(mod, "PARAMS", {})),
            }
        except Exception as exc:
            try:
                print(f"[zoo_reflex_rc52] warn: load failed from {path}: {exc}",
                      file=sys.stderr)
            except Exception:
                pass
            continue
    try:
        print("[zoo_reflex_rc52] warn: no rc52 weights file found; fallback to seed",
              file=sys.stderr)
    except Exception:
        pass
    return {"w_off": {}, "w_def": None, "params": {}}


_RC52_OVERRIDE = _load_rc52_override()


class ReflexRC52Agent(ReflexTunedAgent):
    """ReflexTunedAgent pinned to rc52's REINFORCE-learned weights."""

    def __init__(self, index, timeForComputing=0.1):
        super().__init__(index, timeForComputing=timeForComputing)
        if _RC52_OVERRIDE.get("w_off"):
            self._weights_override = _RC52_OVERRIDE


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC52Agent", second="ReflexRC52Agent"):
    return [ReflexRC52Agent(firstIndex), ReflexRC52Agent(secondIndex)]

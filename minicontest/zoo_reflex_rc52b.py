# zoo_reflex_rc52b.py
# --------------------
# rc52b: REINFORCE-trained variant from an alternate training run
# (iter 30, cum_wr 67.7% vs rc52's 57.3%). Same architecture as rc52.

from __future__ import annotations

from pathlib import Path

from zoo_reflex_tuned import ReflexTunedAgent


_REPO_ROOT = Path(__file__).resolve().parent.parent
_RC52B_WEIGHT_PATHS = [
    _REPO_ROOT / "experiments" / "artifacts" / "rc52b" / "final_weights.py",
    _REPO_ROOT / "experiments" / "rc52b_final_weights.py",
]


def _load_rc52b_override():
    import importlib.util
    import sys
    for path in _RC52B_WEIGHT_PATHS:
        if not path.exists():
            continue
        try:
            spec = importlib.util.spec_from_file_location("_rc52b_weights", str(path))
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
                print(f"[zoo_reflex_rc52b] warn: load failed from {path}: {exc}",
                      file=sys.stderr)
            except Exception:
                pass
            continue
    return {"w_off": {}, "w_def": None, "params": {}}


_RC52B_OVERRIDE = _load_rc52b_override()


class ReflexRC52bAgent(ReflexTunedAgent):
    """ReflexTunedAgent pinned to rc52b's REINFORCE-learned weights."""

    def __init__(self, index, timeForComputing=0.1):
        super().__init__(index, timeForComputing=timeForComputing)
        if _RC52B_OVERRIDE.get("w_off"):
            self._weights_override = _RC52B_OVERRIDE


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC52bAgent", second="ReflexRC52bAgent"):
    return [ReflexRC52bAgent(firstIndex), ReflexRC52bAgent(secondIndex)]

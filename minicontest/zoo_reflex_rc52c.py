# zoo_reflex_rc52c.py
# --------------------
# rc52c: REINFORCE continued from rc52b checkpoint for 30 more iters
# (total 60, per-iter 10 games) with ε=0.10, lr=5e-4, T=3.0.
# Training cum_wr 73.3% vs rc52b's 67.7%.

from __future__ import annotations

from pathlib import Path

from zoo_reflex_tuned import ReflexTunedAgent


_REPO_ROOT = Path(__file__).resolve().parent.parent
_RC52C_WEIGHT_PATHS = [
    _REPO_ROOT / "experiments" / "artifacts" / "rc52c" / "final_weights.py",
    _REPO_ROOT / "experiments" / "rc52c_final_weights.py",
]


def _load_rc52c_override():
    import importlib.util
    import sys
    for path in _RC52C_WEIGHT_PATHS:
        if not path.exists():
            continue
        try:
            spec = importlib.util.spec_from_file_location("_rc52c_weights", str(path))
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
                print(f"[zoo_reflex_rc52c] warn: load failed from {path}: {exc}",
                      file=sys.stderr)
            except Exception:
                pass
            continue
    return {"w_off": {}, "w_def": None, "params": {}}


_RC52C_OVERRIDE = _load_rc52c_override()


class ReflexRC52cAgent(ReflexTunedAgent):
    """ReflexTunedAgent pinned to rc52c's continued-REINFORCE weights."""

    def __init__(self, index, timeForComputing=0.1):
        super().__init__(index, timeForComputing=timeForComputing)
        if _RC52C_OVERRIDE.get("w_off"):
            self._weights_override = _RC52C_OVERRIDE


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC52cAgent", second="ReflexRC52cAgent"):
    return [ReflexRC52cAgent(firstIndex), ReflexRC52cAgent(secondIndex)]

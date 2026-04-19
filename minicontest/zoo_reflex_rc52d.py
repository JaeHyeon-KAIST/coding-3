# zoo_reflex_rc52d.py
# --------------------
# rc52d: REINFORCE 60 more iters from rc52b checkpoint with CONSERVATIVE
# hypparams (lr=1e-5, T=8.0) — applies pm26's lesson that aggressive
# hypparams (rc52c: lr=5e-4, T=3) overshoot the local optimum. Training
# cum_wr 67.7% → 74.3% over 60 iter with stable weight norm 312.36.

from __future__ import annotations

from pathlib import Path

from zoo_reflex_tuned import ReflexTunedAgent


_REPO_ROOT = Path(__file__).resolve().parent.parent
_RC52D_WEIGHT_PATHS = [
    _REPO_ROOT / "experiments" / "artifacts" / "rc52d" / "final_weights.py",
    _REPO_ROOT / "experiments" / "rc52d_final_weights.py",
]


def _load_rc52d_override():
    import importlib.util
    import sys
    for path in _RC52D_WEIGHT_PATHS:
        if not path.exists():
            continue
        try:
            spec = importlib.util.spec_from_file_location("_rc52d_weights", str(path))
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
                print(f"[zoo_reflex_rc52d] warn: load failed from {path}: {exc}",
                      file=sys.stderr)
            except Exception:
                pass
            continue
    return {"w_off": {}, "w_def": None, "params": {}}


_RC52D_OVERRIDE = _load_rc52d_override()


class ReflexRC52dAgent(ReflexTunedAgent):
    """ReflexTunedAgent pinned to rc52d's conservative-REINFORCE weights."""

    def __init__(self, index, timeForComputing=0.1):
        super().__init__(index, timeForComputing=timeForComputing)
        if _RC52D_OVERRIDE.get("w_off"):
            self._weights_override = _RC52D_OVERRIDE


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC52dAgent", second="ReflexRC52dAgent"):
    return [ReflexRC52dAgent(firstIndex), ReflexRC52dAgent(secondIndex)]

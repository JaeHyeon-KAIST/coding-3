# zoo_reflex_A1.py
# -----------------
# Opponent-pool wrapper: ReflexTunedAgent with A1 champion weights pinned.
# Added to Orders 3/4 CEM pool so new populations must beat A1 — not just
# the static seed weights — giving genuine AlphaZero-lite HOF rotation.
#
# Never appears in a submission; minicontest-only training opponent.
# pm19's 340-game HTH battery validated A1 at 79.0% baseline WR
# (Wilson [0.728, 0.841]) — a stronger-than-baseline adversary.

from __future__ import annotations

from pathlib import Path

from zoo_reflex_tuned import ReflexTunedAgent

_REPO_ROOT = Path(__file__).resolve().parent.parent

# A1 weights live in one of two layouts:
#   server: experiments/artifacts/phase2_A1_17dim/final_weights.py (full archive)
#   mac:    experiments/artifacts/phase2_A1_17dim_final_weights.py (flat copy)
# Try server path first (canonical archive), fall back to Mac flat file.
_A1_WEIGHT_PATHS = [
    _REPO_ROOT / "experiments" / "artifacts" / "phase2_A1_17dim" / "final_weights.py",
    _REPO_ROOT / "experiments" / "artifacts" / "phase2_A1_17dim_final_weights.py",
]


def _load_a1_override():
    """Load A1 W_OFF / W_DEF into a load_weights_override-compatible dict.
    Never raises — missing / malformed weights file → empty override →
    ReflexTunedAgent._get_weights falls back to seed weights (zoo_reflex_tuned
    semantics). Logged on stderr for easier diagnostics."""
    import importlib.util
    import sys
    for path in _A1_WEIGHT_PATHS:
        if not path.exists():
            continue
        try:
            spec = importlib.util.spec_from_file_location("_a1_weights", str(path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            w_off = dict(getattr(mod, "W_OFF", {}))
            w_def_raw = dict(getattr(mod, "W_DEF", {}))
            # Empty dict → treat as 2a shared-W (None); non-empty → 2b split-W.
            w_def = w_def_raw or None
            return {
                "w_off": w_off,
                "w_def": w_def,
                "params": dict(getattr(mod, "PARAMS", {})),
            }
        except Exception as exc:
            try:
                print(f"[zoo_reflex_A1] warn: load failed from {path}: {exc}",
                      file=sys.stderr)
            except Exception:
                pass
            continue
    try:
        print("[zoo_reflex_A1] warn: no A1 weights file found; falling back "
              "to seed weights (this agent will behave as zoo_reflex_tuned)",
              file=sys.stderr)
    except Exception:
        pass
    return {"w_off": {}, "w_def": None, "params": {}}


_A1_OVERRIDE = _load_a1_override()


class ReflexA1Agent(ReflexTunedAgent):
    """ReflexTunedAgent pinned to A1's evolved weights at construction.

    `_weights_override` is set from module-level _A1_OVERRIDE (loaded once
    on import). ReflexTunedAgent._get_weights already honours the override:
      role=OFFENSE → override['w_off'],
      role=DEFENSE → override['w_def'] if non-None else fall-through.
    """

    def __init__(self, index, timeForComputing=0.1):
        super().__init__(index, timeForComputing=timeForComputing)
        if _A1_OVERRIDE.get("w_off"):
            self._weights_override = _A1_OVERRIDE


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexA1Agent', second='ReflexA1Agent'):
    return [ReflexA1Agent(firstIndex), ReflexA1Agent(secondIndex)]

"""
experiments/flatten.py — Flatten a zoo_reflex_* variant + zoo_core + zoo_features
+ evolve.py final_weights into a single-file submission module.

Pipeline:
  (a) Parse zoo_core.py, zoo_features.py, zoo_<agent>.py.
  (b) Strip top-level imports from each body (framework imports emitted once
      in the merged header; internal `from zoo_core import ...` /
      `from zoo_features import ...` dropped outright).
  (c) Strip SEED_WEIGHTS_OFFENSIVE / SEED_WEIGHTS_DEFENSIVE assignments from
      zoo_features.py body; inject W_OFF / W_DEF parsed from evolve.py's
      final_weights.py (rebinds the same module-level names so the evaluator
      sees evolved weights with zero downstream changes).
  (d) Concatenate: header → features (without SEED_WEIGHTS) → A1 SEED_WEIGHTS →
      core → agent. Dependency order: features symbols (_clip, extract_features,
      evaluate, _ACTION_PREFERENCE) before core (CoreCaptureAgent references
      none of them at class-body definition time), core before agent subclass.

Notes:
  - A1 weights (17 keys) pass through the 20-key feature extractor via
    `weights.get(f, 0.0)` — the 3 B1 features (f_scaredGhostChase,
    f_returnUrgency, f_teammateSpread) resolve to weight 0, exactly matching
    A1's pre-B1 training environment.
  - PARAMS (12 keys in final_weights.py) is NOT consumed by ReflexTunedAgent's
    `evaluate()` and is dropped from the submission.

Usage:
    .venv/bin/python experiments/flatten.py \\
        --agent zoo_reflex_tuned \\
        --weights experiments/artifacts/phase2_A1_17dim_final_weights.py \\
        --out minicontest/20200492.py
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MINICONTEST = REPO_ROOT / "minicontest"


def load_weights(path: Path) -> tuple[dict, dict]:
    """Execute the evolve.py-emitted weights file in a sandbox namespace and
    pull W_OFF / W_DEF out of the module globals.
    """
    spec = importlib.util.spec_from_file_location("weights_src", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "W_OFF") or not hasattr(mod, "W_DEF"):
        raise ValueError(f"{path} missing W_OFF or W_DEF globals")
    return dict(mod.W_OFF), dict(mod.W_DEF)


def format_weight_dict(name: str, d: dict) -> str:
    """Render a weights dict with deterministic key ordering."""
    lines = [f"{name} = {{"]
    for k in sorted(d.keys()):
        lines.append(f"    {k!r}: {d[k]!r},")
    lines.append("}")
    return "\n".join(lines)


def strip_top_imports(source: str) -> str:
    """Remove ALL top-level `import ...` and `from ... import ...` statements.
    The merged header re-emits the full dedup'd import list.
    """
    tree = ast.parse(source)
    lines_to_strip: set[int] = set()
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for lineno in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                lines_to_strip.add(lineno)
    lines = source.split("\n")
    kept = [line for i, line in enumerate(lines, start=1) if i not in lines_to_strip]
    return "\n".join(kept)


# Internal zoo modules — imports of these must be stripped at any nesting
# level (function bodies, class bodies, conditional blocks). After flatten
# their symbols live in the merged module's global namespace.
INTERNAL_MODULES = {"zoo_core", "zoo_features"}


def strip_internal_imports_deep(source: str) -> str:
    """AST-walk the whole tree and strip every `from zoo_core ...` /
    `from zoo_features ...` line — including inline imports inside
    function/class bodies that `strip_top_imports` leaves behind.
    """
    tree = ast.parse(source)
    lines_to_strip: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod_root = (node.module or "").split(".")[0]
            if mod_root in INTERNAL_MODULES:
                for lineno in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                    lines_to_strip.add(lineno)
    lines = source.split("\n")
    kept = [line for i, line in enumerate(lines, start=1) if i not in lines_to_strip]
    return "\n".join(kept)


def _derive_agent_class(agent_source: str, agent_name: str) -> str:
    """Walk agent source AST to find `createTeam`'s `first` kwarg default —
    the string that `eval()` would have resolved to the teammate class. This
    avoids hardcoding a per-agent mapping and works for any zoo_reflex_*
    variant whose createTeam follows the shared template.
    """
    tree = ast.parse(agent_source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "createTeam":
            args = node.args
            defaults = args.defaults  # aligned to end of args.args
            total_args = len(args.args)
            first_default_idx = total_args - len(defaults)
            for pos, arg in enumerate(args.args):
                if arg.arg == "first" and pos >= first_default_idx:
                    default_node = defaults[pos - first_default_idx]
                    if isinstance(default_node, ast.Constant) and isinstance(default_node.value, str):
                        return default_node.value
    raise ValueError(
        f"could not derive agent class from {agent_name} — `createTeam(first=...)`"
        " default not found"
    )


def rewrite_createTeam_eval(source: str, agent_class: str) -> str:
    """Submission: `createTeam` must not use `eval(first)(...)` (forbidden
    pattern per verify_flatten, and pointless once the class name is locked).
    Replace the line that constructs the two teammates with direct-class
    instantiation. A1 always yields the same class for both slots.
    """
    needle = "agents = [eval(first)(firstIndex), eval(second)(secondIndex)]"
    replacement = (
        f"agents = [{agent_class}(firstIndex), {agent_class}(secondIndex)]"
    )
    if needle not in source:
        raise ValueError(
            "expected `eval(first)(firstIndex)` createTeam pattern not found in source"
        )
    return source.replace(needle, replacement, 1)


def strip_seed_weights(features_source: str) -> str:
    """Remove SEED_WEIGHTS_OFFENSIVE / SEED_WEIGHTS_DEFENSIVE assignments."""
    tree = ast.parse(features_source)
    lines_to_strip: set[int] = set()
    targets_to_strip = {"SEED_WEIGHTS_OFFENSIVE", "SEED_WEIGHTS_DEFENSIVE"}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id in targets_to_strip:
                    start = node.lineno
                    end = node.end_lineno or node.lineno
                    for lineno in range(start, end + 1):
                        lines_to_strip.add(lineno)
    lines = features_source.split("\n")
    kept = [line for i, line in enumerate(lines, start=1) if i not in lines_to_strip]
    return "\n".join(kept)


HEADER_TEMPLATE = '''# {outname} — CS470 A3 Pacman Capture-the-Flag submission
#
# Flattened from {agent_name}.py + zoo_core.py + zoo_features.py + A1 evolved weights.
# A1 provenance: CEM Phase 2a/2b, best-ever fitness 1.0652 (pm19). HTH vs
# baseline.py 158/200 = 79.0%, Wilson 95% CI [0.728, 0.841]. See
# experiments/artifacts/phase2_A1_17dim/ for genomes + HTH CSVs.
#
# Generated by experiments/flatten.py. Do not hand-edit.

from __future__ import annotations

import json
import math
import random
import time
from collections import deque

from captureAgents import CaptureAgent
from game import Directions
from util import TimeoutFunctionException, nearestPoint
'''


def flatten(
    agent_name: str,
    weights_path: Path,
    out_path: Path,
    minicontest: Path = MINICONTEST,
) -> None:
    core_src = (minicontest / "zoo_core.py").read_text()
    features_src = (minicontest / "zoo_features.py").read_text()
    agent_src = (minicontest / f"{agent_name}.py").read_text()

    w_off, w_def = load_weights(weights_path)

    features_body = strip_top_imports(strip_seed_weights(features_src))
    core_body = strip_top_imports(core_src)
    agent_body = strip_top_imports(agent_src)

    # Class name we want both teammate slots to resolve to post-flatten. For
    # zoo_reflex_tuned → ReflexTunedAgent; follow the CamelCase convention.
    agent_class = _derive_agent_class(agent_body, agent_name)
    agent_body = strip_internal_imports_deep(agent_body)
    agent_body = rewrite_createTeam_eval(agent_body, agent_class)

    seed_weights_block = (
        "# ===== A1 evolved weights (Phase 2b best-ever fitness 1.0652) =====\n"
        + format_weight_dict("SEED_WEIGHTS_OFFENSIVE", w_off)
        + "\n\n"
        + format_weight_dict("SEED_WEIGHTS_DEFENSIVE", w_def)
        + "\n"
    )

    parts = [
        HEADER_TEMPLATE.format(outname=out_path.name, agent_name=agent_name),
        "\n# ===== zoo_features.py (20-dim feature extractor) =====\n",
        features_body,
        "\n",
        seed_weights_block,
        "\n# ===== zoo_core.py (CoreCaptureAgent, TEAM, weight-override loader) =====\n",
        core_body,
        "\n# ===== " + agent_name + ".py (ReflexTunedAgent + createTeam) =====\n",
        agent_body,
    ]

    result = "".join(parts)
    out_path.write_text(result)
    n_lines = result.count("\n") + 1
    print(f"[flatten] wrote {out_path} ({n_lines} lines)")

    ast.parse(result)
    print("[flatten] ast.parse OK")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="zoo_reflex_tuned",
                    help="Source agent module name (stem) under minicontest/")
    ap.add_argument("--weights", type=Path, required=True,
                    help="evolve.py-emitted final_weights.py file")
    ap.add_argument("--out", type=Path, required=True,
                    help="Output single-file submission module")
    ap.add_argument("--minicontest", type=Path, default=MINICONTEST)
    args = ap.parse_args()

    flatten(args.agent, args.weights, args.out, minicontest=args.minicontest)
    return 0


if __name__ == "__main__":
    sys.exit(main())

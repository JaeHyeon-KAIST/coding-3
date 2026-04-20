"""experiments/flatten_multi.py — Recursive flatten for multi-file rc agents.

Extends experiments/flatten.py to handle agents whose dependency graph
includes multiple zoo_reflex_* files (e.g., rc177 → rc82 → rc44 → {A1,
rc02, rc16, rc32}).

Pipeline:
  (a) Parse target agent. Extract all `from zoo_* import ...` references
      via AST walk.
  (b) Recurse into each dependency, collecting the full set of zoo_*
      modules needed.
  (c) Topologically sort modules (dependencies before dependents).
  (d) Strip top + deep-nested `from zoo_* import ...` lines from every
      module's source.
  (e) Strip SEED_WEIGHTS_{OFFENSIVE,DEFENSIVE} from zoo_features.py and
      replace with evolved W_OFF/W_DEF from the weights file.
  (f) Concatenate: header → features → A1 weight block → core → each
      agent module in topological order → rewrite createTeam to
      direct-class form.

Usage:
    .venv/bin/python experiments/flatten_multi.py \\
        --agent zoo_reflex_rc177 \\
        --weights experiments/artifacts/phase2_A1_17dim/final_weights.py \\
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

# Framework / stdlib — never flattened in.
_FRAMEWORK_MODULES = {
    "capture", "captureAgents", "game", "layout", "util",
    "distanceCalculator", "graphicsDisplay", "captureGraphicsDisplay",
    "graphicsUtils", "keyboardAgents", "mazeGenerator", "textDisplay",
    "baseline",
}
# Python stdlib modules referenced across zoo_*.
_STDLIB_MODULES = {
    "__future__", "json", "math", "random", "time", "collections",
    "os", "sys", "re", "typing", "functools", "itertools",
    "dataclasses", "numpy",
}


def _collect_zoo_imports(source: str) -> set[str]:
    """Return the set of `zoo_*` module roots imported anywhere in source."""
    tree = ast.parse(source)
    deps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = (node.module or "")
            root = mod.split(".")[0]
            if root.startswith("zoo_"):
                deps.add(mod)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root.startswith("zoo_"):
                    deps.add(alias.name)
    return deps


def _resolve_dependencies(target: str, minicontest: Path) -> list[str]:
    """BFS from `target`; return topologically ordered list (deps first)."""
    visited: set[str] = set()
    order: list[str] = []

    def dfs(mod: str):
        if mod in visited:
            return
        visited.add(mod)
        path = minicontest / f"{mod}.py"
        if not path.exists():
            # Framework or missing — skip (shouldn't happen for zoo_*).
            return
        src = path.read_text()
        for dep in _collect_zoo_imports(src):
            # Only recurse into zoo_* files that actually exist.
            if (minicontest / f"{dep}.py").exists() and dep != mod:
                dfs(dep)
        order.append(mod)

    dfs(target)
    return order


def load_weights(path: Path) -> tuple[dict, dict]:
    spec = importlib.util.spec_from_file_location("weights_src", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "W_OFF") or not hasattr(mod, "W_DEF"):
        raise ValueError(f"{path} missing W_OFF or W_DEF globals")
    return dict(mod.W_OFF), dict(mod.W_DEF)


def format_weight_dict(name: str, d: dict) -> str:
    lines = [f"{name} = {{"]
    for k in sorted(d.keys()):
        lines.append(f"    {k!r}: {d[k]!r},")
    lines.append("}")
    return "\n".join(lines)


def strip_all_imports(source: str) -> str:
    """Strip ALL *top-level* imports + any nested `from zoo_* import ...`.
    Keep nested stdlib imports (e.g. `import importlib.util` inside
    function bodies) — those are runtime-required.
    The merged header re-emits the framework + common stdlib imports."""
    tree = ast.parse(source)
    lines_to_strip: set[int] = set()

    # 1) Top-level imports — strip all (header re-emits needed ones).
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for lineno in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                lines_to_strip.add(lineno)

    # 2) Nested imports (inside function/class bodies) — strip ONLY zoo_*.
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod_root = (node.module or "").split(".")[0]
            if mod_root.startswith("zoo_"):
                for lineno in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                    lines_to_strip.add(lineno)
        elif isinstance(node, ast.Import):
            # Strip any `import zoo_*` (rare but safe).
            if all(a.name.split(".")[0].startswith("zoo_") for a in node.names):
                for lineno in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                    lines_to_strip.add(lineno)

    lines = source.split("\n")
    kept = [line for i, line in enumerate(lines, start=1) if i not in lines_to_strip]
    return "\n".join(kept)


def strip_seed_weights(features_source: str) -> str:
    """Remove SEED_WEIGHTS_OFFENSIVE / SEED_WEIGHTS_DEFENSIVE assignments."""
    tree = ast.parse(features_source)
    lines_to_strip: set[int] = set()
    targets = {"SEED_WEIGHTS_OFFENSIVE", "SEED_WEIGHTS_DEFENSIVE"}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id in targets:
                    start = node.lineno
                    end = node.end_lineno or node.lineno
                    for lineno in range(start, end + 1):
                        lines_to_strip.add(lineno)
    lines = features_source.split("\n")
    kept = [line for i, line in enumerate(lines, start=1) if i not in lines_to_strip]
    return "\n".join(kept)


def _derive_agent_class(agent_source: str) -> str:
    tree = ast.parse(agent_source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "createTeam":
            args = node.args
            defaults = args.defaults
            total_args = len(args.args)
            first_default_idx = total_args - len(defaults)
            for pos, arg in enumerate(args.args):
                if arg.arg == "first" and pos >= first_default_idx:
                    dflt = defaults[pos - first_default_idx]
                    if isinstance(dflt, ast.Constant) and isinstance(dflt.value, str):
                        return dflt.value
    raise ValueError("createTeam(first=...) default not found")


def _remove_createTeam(source: str) -> str:
    """Strip the createTeam function from a non-root agent source (we only
    want the LAST agent's createTeam in the flattened output).
    """
    tree = ast.parse(source)
    lines_to_strip: set[int] = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "createTeam":
            for lineno in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                lines_to_strip.add(lineno)
    # Also strip decorators attached to this function (none expected here).
    lines = source.split("\n")
    kept = [line for i, line in enumerate(lines, start=1) if i not in lines_to_strip]
    return "\n".join(kept)


HEADER_TEMPLATE = '''# {outname} — CS470 A3 Pacman Capture-the-Flag submission
#
# Flattened from {agent_name} + dependency tree:
#   {dep_tree}
# + zoo_core + zoo_features + A1 evolved weights.
#
# A1 provenance: CEM Phase 2a/2b, best-ever fitness 1.0652 (pm19).
# HTH vs baseline.py 158/200 = 79.0%, Wilson 95% CI [0.728, 0.841].
#
# Generated by experiments/flatten_multi.py. Do not hand-edit.

from __future__ import annotations

import json
import math
import random
import sys as _sys
import time
from collections import defaultdict, deque
from pathlib import Path

import numpy as np

from captureAgents import CaptureAgent
from game import Directions, Actions
from util import TimeoutFunctionException, nearestPoint
'''


def flatten_multi(
    agent_name: str,
    weights_path: Path,
    out_path: Path,
    minicontest: Path = MINICONTEST,
) -> None:
    # Resolve full dependency tree (topological).
    deps = _resolve_dependencies(agent_name, minicontest)
    # Remove the framework internals zoo_core / zoo_features from the agent
    # dep list — they are concatenated in a fixed position (before A1
    # subclass chain).
    agent_modules = [m for m in deps if m not in {"zoo_core", "zoo_features", "zoo_belief"}]

    if agent_name not in agent_modules:
        agent_modules.append(agent_name)

    # Read canonical support files.
    core_src = (minicontest / "zoo_core.py").read_text()
    features_src = (minicontest / "zoo_features.py").read_text()

    # A1 evolved weights.
    w_off, w_def = load_weights(weights_path)

    features_body = strip_all_imports(strip_seed_weights(features_src))
    core_body = strip_all_imports(core_src)

    # Agent body: concatenate each in topo order. The LAST one keeps its
    # createTeam; previous ones have it stripped.
    agent_blocks: list[str] = []
    root_class: str | None = None
    for i, mod in enumerate(agent_modules):
        src = (minicontest / f"{mod}.py").read_text()
        body = strip_all_imports(src)
        if mod == agent_name:
            root_class = _derive_agent_class(src)
        else:
            body = _remove_createTeam(body)
        agent_blocks.append(f"\n# ===== {mod}.py =====\n{body}\n")

    if root_class is None:
        raise RuntimeError(f"root_class not derived for {agent_name}")

    seed_weights_block = (
        "# ===== A1 evolved weights (Phase 2b best-ever fitness 1.0652) =====\n"
        + format_weight_dict("SEED_WEIGHTS_OFFENSIVE", w_off)
        + "\n\n"
        + format_weight_dict("SEED_WEIGHTS_DEFENSIVE", w_def)
        + "\n\n"
        + "# Compatibility aliases for stripped `as`-aliased imports.\n"
        + "_base_extract_features = extract_features\n"
        + "_base_evaluate = evaluate\n"
        + "_A1_OVERRIDE_BASE = None  # placeholder; rewritten by zoo_reflex_A1 below\n"
        + "\n"
    )

    dep_tree = " → ".join(agent_modules)
    parts = [
        HEADER_TEMPLATE.format(
            outname=out_path.name,
            agent_name=agent_name,
            dep_tree=dep_tree,
        ),
        "\n# ===== zoo_features.py (20-dim feature extractor) =====\n",
        features_body,
        "\n",
        seed_weights_block,
        "\n# ===== zoo_core.py (CoreCaptureAgent, TEAM, weight-override loader) =====\n",
        core_body,
    ] + agent_blocks

    result = "".join(parts)
    out_path.write_text(result)
    n_lines = result.count("\n") + 1
    print(f"[flatten_multi] wrote {out_path} ({n_lines} lines)")
    print(f"[flatten_multi] dep chain: {dep_tree}")
    print(f"[flatten_multi] root class: {root_class}")

    ast.parse(result)
    print("[flatten_multi] ast.parse OK")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True,
                    help="Source agent module name (e.g., zoo_reflex_rc177)")
    ap.add_argument("--weights", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--minicontest", type=Path, default=MINICONTEST)
    args = ap.parse_args()

    flatten_multi(args.agent, args.weights, args.out, minicontest=args.minicontest)
    return 0


if __name__ == "__main__":
    sys.exit(main())

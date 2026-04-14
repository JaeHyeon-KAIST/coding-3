"""
verify_flatten.py — Submission file integrity verifier (plan §4.0 step 6).

Runs 5 checks on a flattened submission-candidate .py file:
  (a) Imports restricted to the allow-list (no torch/sklearn/pickle/etc.)
  (b) Forbidden-import grep returns empty
  (c) sha256 of the extracted `computeFeatures` function body matches
      the pre-flatten source (identity guarantee)
  (d) File parses via ast.parse() without SyntaxError
  (e) File import-smokes without ImportError

Usage:
    python experiments/verify_flatten.py minicontest/your_best.py \\
        --pre-flatten-source minicontest/zoo_champion.py

If --pre-flatten-source is omitted, check (c) is skipped.

Exit codes:
  0 = all checks pass
  1 = any check fails; details emitted on stderr

Invariant: this script must never crash — it's the last line of defense
before submission packaging. Wraps every check in try/except.
"""

from __future__ import annotations
import argparse
import ast
import hashlib
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"

ALLOWED_IMPORTS = {
    # stdlib always ok
    "random", "time", "math", "sys", "os", "re", "json", "csv",
    "itertools", "collections", "functools", "heapq", "copy",
    "io", "string", "bisect",
    # framework modules (shared by capture.py at runtime)
    "captureAgents", "util", "game", "distanceCalculator", "keyboardAgents",
    # deps per assignment rules
    "numpy", "pandas",
    # typing helpers
    "typing",
    # imports from same-dir (allowed since all are in minicontest/)
}

FORBIDDEN_PATTERNS = [
    r"\bimport\s+(torch|tensorflow|sklearn|scikit_learn|pickle|cloudpickle|joblib|dill)\b",
    r"\bfrom\s+(torch|tensorflow|sklearn|scikit_learn|pickle|cloudpickle|joblib|dill)\b",
    r"\bimport\s+(requests|urllib|http|socket)\b",  # network
    r"\b__import__\s*\(",  # dynamic import
    r"\beval\s*\(",  # eval
    r"\bexec\s*\(",  # exec
    r"\bopen\s*\(.*(['\"]w['\"]|['\"]a['\"])",  # file write at import time
    r"\bsignal\.(signal|alarm|setitimer)\b",  # framework owns SIGALRM
]


def check_ast_parse(path: Path) -> tuple[bool, str]:
    try:
        source = path.read_text()
        ast.parse(source)
        return True, "ast.parse OK"
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    except Exception as e:
        return False, f"read/parse failure: {e}"


def check_allowed_imports(path: Path) -> tuple[bool, str]:
    try:
        tree = ast.parse(path.read_text())
    except Exception as e:
        return False, f"ast.parse fail in import check: {e}"
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    bad.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            if mod and mod not in ALLOWED_IMPORTS:
                bad.append(f"from {node.module} import ...")
    if bad:
        return False, f"disallowed imports: {bad}"
    return True, f"all imports ok"


def check_forbidden_patterns(path: Path) -> tuple[bool, str]:
    try:
        src = path.read_text()
    except Exception as e:
        return False, f"read fail: {e}"
    hits = []
    for pat in FORBIDDEN_PATTERNS:
        for m in re.finditer(pat, src):
            # skip matches inside strings/comments (heuristic)
            line_start = src.rfind("\n", 0, m.start()) + 1
            line = src[line_start : src.find("\n", m.end())]
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            hits.append((pat, stripped[:80]))
    if hits:
        return False, f"forbidden patterns: {hits}"
    return True, "no forbidden patterns"


def extract_function_body_hash(path: Path, func_name: str = "computeFeatures") -> str | None:
    """Return sha256 hex of the source text of the named function."""
    try:
        src = path.read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
                body = ast.unparse(node)
                return hashlib.sha256(body.encode()).hexdigest()
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == func_name:
                        body = ast.unparse(item)
                        return hashlib.sha256(body.encode()).hexdigest()
    except Exception:
        return None
    return None


def check_identity(flattened: Path, pre_flatten: Path, func_name: str = "computeFeatures") -> tuple[bool, str]:
    h1 = extract_function_body_hash(flattened, func_name)
    h2 = extract_function_body_hash(pre_flatten, func_name)
    if h1 is None and h2 is None:
        return True, f"(no {func_name} in either file — skipped)"
    if h1 is None or h2 is None:
        return False, f"{func_name} missing in one file: flattened={h1}, pre={h2}"
    if h1 == h2:
        return True, f"{func_name} body hash matches: {h1[:12]}..."
    return False, f"{func_name} body hash MISMATCH: flat={h1[:12]}... pre={h2[:12]}..."


def check_import_smoke(path: Path) -> tuple[bool, str]:
    # run `python -c 'import <module>'` where module = stem of the file
    # CWD must be the file's parent so imports resolve as they would at game time
    module_name = path.stem
    try:
        proc = subprocess.run(
            [str(VENV_PYTHON), "-c", f"import {module_name}"],
            cwd=str(path.parent),
            capture_output=True,
            text=True,
            timeout=15.0,
        )
        if proc.returncode == 0:
            return True, "import smoke OK"
        return False, f"import failed (exit {proc.returncode}): {proc.stderr[:300]}"
    except subprocess.TimeoutExpired:
        return False, "import smoke timed out"
    except Exception as e:
        return False, f"import smoke exception: {e}"


def run_all_checks(flattened: Path, pre_flatten: Path | None) -> tuple[bool, list[tuple[str, bool, str]]]:
    results = []

    ok, msg = check_ast_parse(flattened)
    results.append(("ast.parse", ok, msg))

    ok, msg = check_allowed_imports(flattened)
    results.append(("allowed_imports", ok, msg))

    ok, msg = check_forbidden_patterns(flattened)
    results.append(("forbidden_patterns", ok, msg))

    if pre_flatten is not None:
        ok, msg = check_identity(flattened, pre_flatten)
        results.append(("identity", ok, msg))
    else:
        results.append(("identity", True, "(skipped; no --pre-flatten-source)"))

    ok, msg = check_import_smoke(flattened)
    results.append(("import_smoke", ok, msg))

    all_pass = all(r[1] for r in results)
    return all_pass, results


def main():
    ap = argparse.ArgumentParser(description="Verify a flattened submission .py file.")
    ap.add_argument("target", type=Path, help="Flattened file to check")
    ap.add_argument("--pre-flatten-source", type=Path, default=None,
                    help="Optional: original source file to check body-hash identity against")
    ap.add_argument("--func-name", default="computeFeatures",
                    help="Function name to hash-verify (default: computeFeatures)")
    args = ap.parse_args()

    if not args.target.exists():
        print(f"[verify_flatten] target does not exist: {args.target}", file=sys.stderr)
        return 1

    all_pass, results = run_all_checks(args.target, args.pre_flatten_source)
    for name, ok, msg in results:
        mark = "✓" if ok else "✗"
        print(f"[verify_flatten] {mark} {name}: {msg}", file=sys.stderr)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())

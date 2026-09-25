"""Import/reference census for the 1yzd0 readiness inventory.

PREDICATE (stated so it can be re-derived):
  Universe U = every top-level ``*.py`` directly in
  .wavefoundry/framework/scripts/ (module name = stem) plus the package
  ``wave_lint_lib`` (treated as one module; its submodules are listed too).
  Scanned corpus C = every ``*.py`` file anywhere under
  .wavefoundry/framework/ (scripts, tests, benchmarks, wave_lint_lib, seeds,
  install) except __pycache__.
  For each file f in C and each module m in U we record a reference when the
  AST of f contains:
    import      : ``import m`` / ``import m as x`` / ``from m import ...``
                  (also ``m.sub``); scope = top (module body, incl. nested
                  try/if at module level) or local (inside a def/class)
    call:<fn>   : a Call whose first positional arg is the str constant m
                  (captures importlib.import_module, _load_script, load_module
                  helpers, spec_from_file_location name args, etc.)
    str         : any other str Constant exactly equal to m (purge sets,
                  SOURCE_FILES, patch targets like "server_impl.X" are
                  matched by the prefix rule below)
    dotted      : a str Constant starting with "m." whose remainder is an
                  identifier path (mock.patch("server_impl.foo") targets)
    path        : a str Constant (or JoinedStr literal part) containing
                  "m.py" as a path component
  Non-Python files under .wavefoundry/framework (excluding index/, __pycache__)
  are scanned with a regex for the literal "m.py" basename.
Outputs JSON to stdout.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

REPO = Path("/Users/coryhacking/Developer/wavefoundry")
FW = REPO / ".wavefoundry/framework"
SCRIPTS = FW / "scripts"

universe = sorted(p.stem for p in SCRIPTS.glob("*.py"))
universe.append("wave_lint_lib")
U = set(universe)
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def rel(p: Path) -> str:
    return str(p.relative_to(REPO))


def scan_py(path: Path):
    refs = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception as exc:  # noqa: BLE001
        return [{"error": repr(exc)}]
    # parent scope map
    scope_of = {}

    def walk(node, scope):
        for child in ast.iter_child_nodes(node):
            s = scope
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                s = "local"
            scope_of[id(child)] = s
            walk(child, s)

    walk(tree, "top")
    consumed = set()
    for node in ast.walk(tree):
        scope = scope_of.get(id(node), "top")
        if isinstance(node, ast.Import):
            for a in node.names:
                head = a.name.split(".")[0]
                if head in U:
                    refs.append({"mod": head, "kind": "import", "scope": scope, "line": node.lineno, "text": f"import {a.name}"})
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                head = node.module.split(".")[0]
                if head in U:
                    names = ",".join(a.name for a in node.names)
                    refs.append({"mod": head, "kind": "import", "scope": scope, "line": node.lineno, "text": f"from {node.module} import {names[:120]}"})
        elif isinstance(node, ast.Call) and node.args:
            a0 = node.args[0]
            if isinstance(a0, ast.Constant) and isinstance(a0.value, str) and a0.value in U:
                fn = ast.unparse(node.func)
                refs.append({"mod": a0.value, "kind": f"call:{fn}", "scope": scope, "line": node.lineno, "text": ast.unparse(node)[:160]})
                consumed.add(id(a0))
    for node in ast.walk(tree):
        if id(node) in consumed:
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value
            scope = scope_of.get(id(node), "top")
            if v in U:
                refs.append({"mod": v, "kind": "str", "scope": scope, "line": getattr(node, "lineno", 0), "text": repr(v)})
                continue
            head = v.split(".")[0]
            if head in U and "." in v and IDENT.match(v) and not v.endswith(".py"):
                refs.append({"mod": head, "kind": "dotted", "scope": scope, "line": getattr(node, "lineno", 0), "text": repr(v)[:120]})
            for m in U:
                if re.search(r"(^|[\\/\s\"'`(])" + re.escape(m) + r"\.py\b", v) or v == f"{m}.py":
                    refs.append({"mod": m, "kind": "path", "scope": scope, "line": getattr(node, "lineno", 0), "text": repr(v)[:160]})
    return refs


results = {"universe": universe, "py": {}, "nonpy": {}}
for p in sorted(FW.rglob("*.py")):
    if "__pycache__" in p.parts or "index" in p.relative_to(FW).parts[:1]:
        continue
    r = scan_py(p)
    if r:
        results["py"][rel(p)] = r

pat = {m: re.compile(r"(?<![A-Za-z0-9_])" + re.escape(m) + r"\.py\b") for m in U}
for p in sorted(FW.rglob("*")):
    if not p.is_file() or p.suffix in {".py", ".pyc", ".zip", ".onnx", ".bin", ".sqlite", ".png"}:
        continue
    parts = p.relative_to(FW).parts
    if "__pycache__" in parts or parts[0] in {"index"}:
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except Exception:
        continue
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for m, rx in pat.items():
            if rx.search(line):
                hits.append({"mod": m, "line": i, "text": line.strip()[:160]})
    if hits:
        results["nonpy"][rel(p)] = hits

json.dump(results, sys.stdout, indent=1)

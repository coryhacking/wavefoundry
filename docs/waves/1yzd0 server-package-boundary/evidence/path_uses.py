"""Path / identity census inside the moved set (1yzd0 readiness, section A3).

PREDICATE: for each module M in MOVED, walk its AST and report every
  * Name/Attribute ``__file__`` (incl. ``X.__file__``)
  * Name ``__name__`` / Attribute ``__module__`` / ``__spec__``
  * Attribute ``sys.modules`` / ``_sys.modules``
  * Name ``SCRIPTS_DIR`` or Attribute ``*.SCRIPTS_DIR``
  * Calls to spec_from_file_location / import_module / find_spec / runpy.*
  * str Constant ending in ".py" (script path literal: subprocess argv, file reads)
  * ``parents[N]`` subscripts and ``.parent.parent`` chains
with the enclosing function (qualified) and line. Docstrings are skipped.
"""
import ast
import sys
from pathlib import Path

SCRIPTS = Path("/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts")
MOVED = ["server_impl", "mcp_tool_registry", "codenav_handlers", "graph_handlers", "techdocs_handlers",
         "memory_handlers", "index_handlers", "upgrade_handlers", "edit_gate_handlers", "dashboard_handlers",
         "docs_handlers", "context_efficiency_handlers"]


def docstring_ids(tree):
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                ids.add(id(body[0].value))
    return ids


for m in MOVED:
    src = (SCRIPTS / f"{m}.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    skip = docstring_ids(tree)
    encl = {}

    def walk(node, name):
        for ch in ast.iter_child_nodes(node):
            n = name
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                n = f"{name}.{ch.name}" if name != "<module>" else ch.name
            encl[id(ch)] = n
            walk(ch, n)

    walk(tree, "<module>")
    rows = []
    for node in ast.walk(tree):
        where = encl.get(id(node), "<module>")
        line = getattr(node, "lineno", 0)
        kind = None
        if isinstance(node, ast.Name) and node.id in ("__file__", "__name__", "SCRIPTS_DIR"):
            kind = node.id
        elif isinstance(node, ast.Attribute) and node.attr in ("__file__", "__module__", "__spec__", "SCRIPTS_DIR"):
            kind = f"{ast.unparse(node)}"
        elif isinstance(node, ast.Attribute) and node.attr == "modules" and isinstance(node.value, ast.Name) and node.value.id in ("sys", "_sys"):
            kind = "sys.modules"
        elif isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            if any(k in fn for k in ("spec_from_file_location", "import_module", "find_spec", "runpy")):
                kind = f"call {ast.unparse(node)[:110]}"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            v = node.value
            if v.endswith(".py") and len(v) < 90 and "\n" not in v:
                kind = f"py-literal {v!r}"
        elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "parents":
            kind = f"parents {ast.unparse(node)[:80]}"
        elif isinstance(node, ast.Attribute) and node.attr == "parent" and isinstance(node.value, ast.Attribute) and node.value.attr == "parent":
            kind = f"parent.parent {ast.unparse(node)[:80]}"
        if kind:
            rows.append((line, where, kind))
    print(f"### {m}.py ({len(rows)})")
    for line, where, kind in sorted(set(rows)):
        print(f"  {line:6} {where:55} {kind}")

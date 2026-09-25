"""Mechanical first pass + declared overrides for the A1 module classification.

Inputs: scan.json (see scan_imports.py predicate).
Mechanical facts per module m (top-level scripts/*.py plus the wave_lint_lib package):
  main      : AST has ``if __name__ == "__main__"``
  importers : production files (scripts/*.py, wave_lint_lib/*) that reference m by
              import / call-with-name / str / path (self-references excluded)
  imp_kinds : which reference kinds occur
  server_only: every production importer is in MOVED ∪ {server}
Class assignment rule (in order):
  1. m in MOVED                       -> moved
  2. m in DECLARATIONS                -> downstream declaration (Req 2 names these)
  3. main guard present               -> executable/CLI entry point
  4. otherwise                        -> retained shared substrate
  'borderline' is flagged when a non-moved module is server_only (all its production
  importers are moved modules) — those need an explicit reason to stay.
"""
import ast
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = Path("/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts")
SP = ".wavefoundry/framework/scripts/"
d = json.load(open(HERE / "scan.json"))
MOVED = {"server_impl", "mcp_tool_registry", "codenav_handlers", "graph_handlers", "techdocs_handlers",
         "memory_handlers", "index_handlers", "upgrade_handlers", "edit_gate_handlers", "dashboard_handlers",
         "docs_handlers", "context_efficiency_handlers"}
DECLARATIONS = {"mcp_tool_extensions", "mcp_tool_roster", "record_paths"}


def stem(f):
    r = f[len(SP):]
    return "wave_lint_lib" if r.startswith("wave_lint_lib/") else Path(r).stem


def is_prod(f):
    r = f[len(SP):] if f.startswith(SP) else None
    return r is not None and (("/" not in r) or r.startswith("wave_lint_lib/"))


importers = defaultdict(set)
kinds = defaultdict(set)
for f, refs in d["py"].items():
    if not is_prod(f):
        continue
    for r in refs:
        if r["mod"] == stem(f):
            continue
        importers[r["mod"]].add(stem(f))
        kinds[r["mod"]].add(r["kind"].split(":")[0])


def has_main(m):
    p = SCRIPTS / f"{m}.py"
    if not p.exists():
        return (SCRIPTS / "wave_lint_lib" / "__main__.py").exists()
    t = ast.parse(p.read_text(encoding="utf-8"))
    for n in t.body:
        if isinstance(n, ast.If) and "__main__" in ast.unparse(n.test):
            return True
    return False


rows = []
for m in d["universe"]:
    imp = sorted(importers.get(m, ()))
    server_only = bool(imp) and set(imp) <= (MOVED | {"server"})
    if m in MOVED:
        cls = "moved"
    elif m in DECLARATIONS:
        cls = "downstream declaration"
    elif has_main(m):
        cls = "executable/CLI entry point"
    else:
        cls = "retained shared substrate"
    rows.append({"module": m, "class": cls, "main": has_main(m), "server_only": server_only and m not in MOVED,
                 "importers": imp, "kinds": sorted(kinds.get(m, ()))})
json.dump(rows, open(HERE / "classification.json", "w"), indent=1)
from collections import Counter
print(Counter(r["class"] for r in rows))
for r in rows:
    flag = " [BORDERLINE: server-only importers]" if r["server_only"] else ""
    print(f"{r['class']:28} {r['module']:34} main={int(r['main'])} importers={','.join(r['importers'])} kinds={','.join(r['kinds'])}{flag}")

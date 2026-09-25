"""Module-level mutable state census for the moved set (1yzd0 A4).

PREDICATE: for each moved module, report
  (1) every name rebound inside a function via a ``global`` statement
      (rebinding state: a flat alias that copied the value would go stale), and
  (2) every module-level assignment whose value is a mutable container
      literal/constructor (dict/list/set literal or comprehension, or a call to
      dict/list/set/defaultdict/OrderedDict/deque/Lock/RLock/Event/Condition/
      WeakValueDictionary/WeakKeyDictionary/ContextVar).
Also reports, for server_impl, which of those names are re-exported FROM a
handler module (``from X_handlers import NAME``) - shared-object re-exports.
"""
import ast
from pathlib import Path

SCRIPTS = Path("/Users/coryhacking/Developer/wavefoundry/.wavefoundry/framework/scripts")
MOVED = ["server_impl", "mcp_tool_registry", "codenav_handlers", "graph_handlers", "techdocs_handlers",
         "memory_handlers", "index_handlers", "upgrade_handlers", "edit_gate_handlers", "dashboard_handlers",
         "docs_handlers", "context_efficiency_handlers"]
CTORS = {"dict", "list", "set", "defaultdict", "OrderedDict", "deque", "Lock", "RLock", "Event", "Condition",
         "WeakValueDictionary", "WeakKeyDictionary", "ContextVar", "Semaphore", "BoundedSemaphore"}

reexports = {}
for m in MOVED:
    tree = ast.parse((SCRIPTS / f"{m}.py").read_text(encoding="utf-8"))
    globals_rebound = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Global):
            globals_rebound.update(node.names)
    mutables = []
    for node in tree.body:
        targets, value = [], None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        for t in targets:
            if not isinstance(t, ast.Name):
                continue
            mut = isinstance(value, (ast.Dict, ast.List, ast.Set, ast.DictComp, ast.ListComp, ast.SetComp))
            if isinstance(value, ast.Call):
                fn = value.func
                name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
                mut = name in CTORS
            if mut:
                mutables.append((node.lineno, t.id))
    if m == "server_impl":
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module and node.module in MOVED:
                for a in node.names:
                    reexports[a.name] = node.module
    print(f"### {m}: global-rebound={len(globals_rebound)} mutable-module-containers={len(mutables)}")
    print("   rebound via `global`: " + ", ".join(sorted(globals_rebound)))
    print("   mutable containers: " + ", ".join(f"{n}@{l}" for l, n in mutables))

print("\n### server_impl names re-exported from moved handler modules that are mutable containers or global-rebound in the owner:")
for m in MOVED:
    if m == "server_impl":
        continue
    tree = ast.parse((SCRIPTS / f"{m}.py").read_text(encoding="utf-8"))
    rebound = {n for node in ast.walk(tree) if isinstance(node, ast.Global) for n in node.names}
    mut = set()
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and getattr(node, "value", None) is not None:
            v = node.value
            tg = node.targets if isinstance(node, ast.Assign) else [node.target]
            ism = isinstance(v, (ast.Dict, ast.List, ast.Set, ast.DictComp, ast.ListComp, ast.SetComp)) or (
                isinstance(v, ast.Call) and (getattr(v.func, "attr", None) or getattr(v.func, "id", "")) in CTORS)
            if ism:
                mut.update(t.id for t in tg if isinstance(t, ast.Name))
    hits = [n for n, owner in reexports.items() if owner == m and (n in mut or n in rebound)]
    if hits:
        print(f"   {m}: " + ", ".join(f"{n}{'(REBOUND)' if n in rebound else '(shared-mutable)'}" for n in sorted(hits)))

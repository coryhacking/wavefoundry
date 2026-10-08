"""Executable extraction boundaries for 1y044; scanners include negative controls."""
from __future__ import annotations

import ast
from contextlib import ExitStack
import dataclasses
import importlib
import io
from pathlib import Path
import sys
import tempfile
import tokenize
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from framework_files import source_path  # wf_server-aware source locations (wave 1yzd0)
MODULES = ("lifecycle_gate_support", "lifecycle_gates", "sensor_runner")
FIELDS = {"root", "wave_md", "wave_text", "mode", "lint_result", "phase"}
MARKERS = ("events.jsonl", "## Review Evidence", "## Review Signoff Evidence",
           "## Prepare Review Evidence")


def _source(name):
    return source_path(name).read_text(encoding="utf-8")


def _name(node):
    return ast.unparse(node)


def _definitions(tree):
    result = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            result.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            result.update(n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name))
    return result


def _facade_errors(source):
    tree = ast.parse(source)
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                  and n.body and isinstance(n.body[0], ast.Expr)
                  and isinstance(n.body[0].value, ast.Constant)
                  and isinstance(n.body[0].value.value, str)}
    errors = []
    ledger_names = {"EVENTS_FILENAME"}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            ledger_names.update(a.asname or a.name for a in n.names if a.name == "EVENTS_FILENAME")
    # Resolve straightforward local aliases so constructing a path through a
    # facade constant is no less visible than spelling the filename literally.
    def ledger(n):
        return (isinstance(n, ast.Name) and n.id in ledger_names
                or isinstance(n, ast.Attribute) and n.attr == "EVENTS_FILENAME"
                or isinstance(n, ast.Constant) and n.value == "events.jsonl")
    for _ in range(len(list(ast.walk(tree)))):
        prior = set(ledger_names)
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and ledger(n.value):
                ledger_names.update(t.id for t in n.targets if isinstance(t, ast.Name))
        if prior == ledger_names:
            break
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings:
            if any(marker in n.value for marker in MARKERS):
                errors.append((n.lineno, "literal evidence carrier"))
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div) and ledger(n.right):
            errors.append((n.lineno, "ledger path construction"))
        if isinstance(n, ast.Call) and n.args and ledger(n.args[-1]):
            if _name(n.func).split(".")[-1] in {"joinpath", "join", "Path", "open"}:
                errors.append((n.lineno, "ledger path/read call"))
    return errors


def _import_errors(source, module):
    errors = []
    tree = ast.parse(source)
    support_aliases = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.Import)
                       for a in n.names if a.name == "lifecycle_gate_support"}
    # Wave 1yd99: resolve aliases established by assignment as well as by import,
    # so binding the support module to a local name and reading a helper off it is
    # caught the same as a from-import.  The fixpoint form is the one the facade
    # scanner already uses for ledger names, a few lines above.
    for _ in range(len(list(ast.walk(tree)))):
        prior = set(support_aliases)
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Name) and n.value.id in support_aliases:
                support_aliases.update(x.id for x in n.targets if isinstance(x, ast.Name))
        if prior == support_aliases:
            break
    for n in ast.walk(tree):
        if module == "lifecycle_gates" and isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            value = n.value
            if isinstance(value, ast.Attribute) and _name(value.value) in support_aliases:
                errors.append((n.lineno, "aliased support helper"))
        if isinstance(n, ast.Import):
            imported = [a.name.split(".")[0] for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            imported = [(n.module or "").split(".")[0]]
        else:
            continue
        forbidden = {"server_impl"}
        if module == "lifecycle_gate_support":
            forbidden |= {"lifecycle_gates", "sensor_runner"}
        if set(imported) & forbidden:
            errors.append((n.lineno, "reverse import"))
        if module == "lifecycle_gates" and isinstance(n, ast.ImportFrom) and n.module == "lifecycle_gate_support":
            errors.append((n.lineno, "bound support helper"))
    return errors


def _context_errors(source, fields):
    tree = ast.parse(source)
    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    units = set()
    for n in tree.body:
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            if any(isinstance(t, ast.Name) and t.id.endswith("_GATES") for t in targets):
                units.update(e.id for e in n.value.elts if isinstance(e, ast.Name))
    errors = []
    readers = {f: set() for f in fields}
    def carries_context(node, ctx):
        if isinstance(node, ast.Name):
            return node.id == ctx
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return any(carries_context(item, ctx) for item in node.elts)
        if isinstance(node, ast.Dict):
            return any(carries_context(item, ctx) for item in [*node.keys, *node.values])
        if isinstance(node, ast.IfExp):
            return carries_context(node.body, ctx) or carries_context(node.orelse, ctx)
        if isinstance(node, ast.BoolOp):
            return any(carries_context(item, ctx) for item in node.values)
        return False

    def walk_function(unit, fn, ctx, seen):
        key = (fn.name, ctx)
        if key in seen:
            return
        seen.add(key)
        for n in ast.walk(fn):
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == ctx:
                if n.attr not in fields:
                    errors.append((unit, "unknown context field", n.attr))
                elif isinstance(n.ctx, ast.Load):
                    readers[n.attr].add(unit)
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                value = n.value
                if carries_context(value, ctx):
                    errors.append((unit, "context alias"))
            if isinstance(n, ast.Call):
                if isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == ctx:
                    errors.append((unit, "callable context field"))
                if _name(n.func).split(".")[-1] in {"getattr", "vars", "asdict"} and any(isinstance(a, ast.Name) and a.id == ctx for a in [*n.args, *(kw.value for kw in n.keywords)]):
                    errors.append((unit, "dynamic context access"))
                if isinstance(n.func, ast.Name) and n.func.id in funcs:
                    callee = funcs[n.func.id]
                    params = callee.args.posonlyargs + callee.args.args
                    for param, arg in zip(params, n.args):
                        if isinstance(arg, ast.Name) and arg.id == ctx:
                            walk_function(unit, callee, param.arg, seen)
                    for kw in n.keywords:
                        if isinstance(kw.value, ast.Name) and kw.value.id == ctx:
                            walk_function(unit, callee, kw.arg, seen)
    for unit in units:
        if unit not in funcs:
            errors.append((unit, "not module function"))
            continue
        fn = funcs[unit]
        walk_function(unit, fn, (fn.args.posonlyargs + fn.args.args)[0].arg, set())
    errors.extend((field, "fewer than two distinct readers", sorted(users))
                  for field, users in readers.items() if len(users) < 2)
    if not units:
        errors.append(("no units",))
    return errors


def _purge_entries(source):
    candidates = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Set)
                  and any(isinstance(e, ast.Constant) and e.value == "record_paths" for e in n.elts)]
    if len(candidates) != 1:
        raise AssertionError("Expected exactly one purge literal containing record_paths")
    return [e.value for e in candidates[0].elts if isinstance(e, ast.Constant)]


def _alias_table(source):
    """Flat names in the server_impl ``_FLAT_ALIASES`` table (wave 1yzd0)."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_FLAT_ALIASES"
                                                for t in node.targets):
            return {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
    raise AssertionError("Expected a module-level _FLAT_ALIASES table")


def _retired_table(source):
    """Flat names in the server_impl ``_RETIRED_FLAT_NAMES`` table (wave 1yxyw)."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_RETIRED_FLAT_NAMES"
                                                for t in node.targets):
            return {n.value for n in ast.walk(node.value) if isinstance(n, ast.Constant)
                    and isinstance(n.value, str)}
    raise AssertionError("Expected a module-level _RETIRED_FLAT_NAMES table")


def _purge_covered(source):
    """Names the reload purge evicts: the retained literal plus every moved
    module except server_impl, whose flat and package keys are derived from
    the alias table and the retired-name table."""
    return (set(_purge_entries(source)) | (_alias_table(source) - {"server_impl"})
            | _retired_table(source))


def _evaluated_purge_keys(source):
    """Evaluate the ``_FLAT_ALIASES`` and ``_RETIRED_FLAT_NAMES`` tables and
    ``_PACKAGE_PURGE_KEYS`` from the source alone, without importing
    server_impl: a purge that evicts the module being reloaded crashes the
    import, so it must fail here instead."""
    wanted = [node for node in ast.parse(source).body
              if isinstance(node, ast.Assign)
              and any(isinstance(t, ast.Name)
                      and t.id in {"_FLAT_ALIASES", "_RETIRED_FLAT_NAMES", "_PACKAGE_PURGE_KEYS"}
                      for t in node.targets)]
    namespace = {}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), "<purge keys>", "exec"), namespace)
    return namespace["_PACKAGE_PURGE_KEYS"]


def _package_modules():
    """Moved modules by flat name, from the package files on disk, independent
    of both the purge literal and the alias table."""
    return {p.stem for p in (SCRIPTS / "wf_server").glob("*.py") if p.name != "__init__.py"}


def _direct_local_imports(source):
    """Independent census of module-body framework imports, not the purge list.

    A flat sibling counts by its own name and a ``wf_server`` package module by
    its flat name (wave 1yzd0: ``from wf_server.x import``, ``import
    wf_server.x as x``). Deliberately bounded to module-body imports; lazy and
    transitive imports have different loading paths and are not covered here.
    """
    names = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules = [node.module]
            if node.module == "wf_server":
                modules += ["wf_server." + alias.name for alias in node.names]
        else:
            continue
        for module in modules:
            parts = module.split(".")
            if parts[0] == "wf_server":
                if len(parts) > 1 and (SCRIPTS / "wf_server" / (parts[1] + ".py")).is_file():
                    names.add(parts[1])
            elif (SCRIPTS / (parts[0] + ".py")).is_file():
                names.add(parts[0])
    return names


# Retain the existing process-bootstrap boundary, independently of the purge
# list. server.py is not reloaded: it retains repo_root and setup_readiness,
# activates venv_bootstrap at launch, and setup_readiness retains subprocess_util.
# server.py also configures bytecode_cache at launch (change 1zyv1); its
# configure() decides once per process, so a reload must not replace it.
# Changing these dependencies still requires a process restart.
_RELOAD_BOOTSTRAP_EXCLUSIONS = {
    "repo_root", "setup_readiness", "venv_bootstrap", "subprocess_util", "bytecode_cache",
}


# Wave 1zxnz (1zx02): flat script modules that a module wf_reload_mcp evicts or
# reloads imports, but that the reload leaves loaded. Each reason says why a
# stale copy is acceptable until the host restarts. Reducing this list is a
# follow-up; the guard below keeps it from growing silently.
_RELOAD_RETAINED_FLAT_MODULES = {
    "accel_embedder": "process-wide accelerated embedder cache, loaded lazily by the index runtime",
    "bytecode_cache": "runner bootstrap (_RELOAD_BOOTSTRAP_EXCLUSIONS)",
    "cli_stdio": "stable stdio reconfigure helper, imported lazily",
    "dashboard_lib": "dashboard process coordination; flock-style locks only, read lazily",
    "graph_snapshot": "process-wide graph snapshot cache, read lazily",
    "index_compatibility": "pins the loaded index runtime; a reload deliberately does not replace it",
    "index_state_store": "index store bound to the loaded index runtime, read lazily",
    "install_log_lib": "stable install-log reader API, imported lazily",
    "lifecycle_id": "stable lifecycle id helpers; tool paths reach it through the script cache",
    "machine_authority": "stable scanner path predicate used by the secrets validators",
    "process_info": "process-wide psutil loader, deliberately left loaded",
    "provider_policy": "stable execution-provider selection, imported lazily",
    "render_agent_surfaces": "stable renderer API, imported lazily at call time",
    "repo_root": "runner bootstrap (_RELOAD_BOOTSTRAP_EXCLUSIONS)",
    "scanner_skips": "scanner skip records; flock-style locks only",
    "setup_index": "setup entry point, imported lazily for its CA ladder and checks",
    "setup_readiness": "runner bootstrap (_RELOAD_BOOTSTRAP_EXCLUSIONS)",
    "sqlite_runtime": "process-wide SQLite binding, which must not change inside one process",
    "subprocess_util": "runner bootstrap (_RELOAD_BOOTSTRAP_EXCLUSIONS)",
    "techdocs_audit_lib": "stable audit API, imported lazily at call time",
    "tree_sitter_cache": "process-wide parser cache, imported lazily",
    "upgrade_lib": "stable upgrade-lock helpers, imported lazily",
    "upgrade_wavefoundry": "upgrade runner, imported lazily; an upgrade ends with a restart or reload",
    "venv_bootstrap": "runner bootstrap (_RELOAD_BOOTSTRAP_EXCLUSIONS)",
}

# Wave 1zxnz (1zx02): module-level ``from runtime_lock import NAME`` bindings in
# modules the reload leaves loaded. Exception classes keep their identity
# across the in-place reload; any other bound name keeps old code until
# restart and must be listed here with the reason that is acceptable.
_RUNTIME_LOCK_STALE_BINDINGS = {
    ("dashboard_lib", "RuntimeFileLock"): "flock-style dashboard locks only; old code is consistent until restart",
    ("dashboard_lib", "write_json_in_place"): "metadata rewrite helper; old code is consistent until restart",
    ("scanner_skips", "RuntimeFileLock"): "flock-style scanner lock only; old code is consistent until restart",
}


def _in_place_reloaded(source):
    """Names in server_impl's ``_IN_PLACE_RELOAD_MODULES`` tuple (wave 1zxnz)."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_IN_PLACE_RELOAD_MODULES"
                                                for t in node.targets):
            return {n.value for n in ast.walk(node.value) if isinstance(n, ast.Constant)
                    and isinstance(n.value, str)}
    raise AssertionError("Expected a module-level _IN_PLACE_RELOAD_MODULES tuple")


def _flat_stems():
    from framework_files import framework_source_files

    return {p.stem for p in framework_source_files(include_aliases=True) if p.parent == SCRIPTS}


def _evicted_flat_names(server_source):
    """Flat names the reload evicts or reloads: the purge literal, every
    package module by its flat key, and server_impl itself."""
    package_keys = {key for key in _evaluated_purge_keys(server_source) if "." not in key}
    return set(_purge_entries(server_source)) | package_keys | {"server_impl"}


def _evicted_module_sources(server_source, overrides=None):
    """``{label: source}`` for every module the reload evicts or reloads:
    purge-literal flat modules, every ``wave_lint_lib`` module, and every
    ``wf_server`` package module including server_impl."""
    overrides = overrides or {}
    stems = _flat_stems()
    labels = {name: name for name in _purge_entries(server_source) if name in stems}
    for path in sorted((SCRIPTS / "wave_lint_lib").rglob("*.py")):
        rel = path.relative_to(SCRIPTS).as_posix()
        labels[rel] = rel
    for path in sorted((SCRIPTS / "wf_server").glob("*.py")):
        rel = path.relative_to(SCRIPTS).as_posix()
        labels[rel] = rel
    result = {label: source_path(name).read_text(encoding="utf-8") for label, name in labels.items()}
    result["wf_server/server_impl.py"] = server_source
    result.update(overrides)
    return result


def _flat_imports_anywhere(source, stems):
    """Top-level names of flat script modules imported anywhere in ``source``
    (module level and inside functions)."""
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules = [node.module]
        else:
            continue
        found.update(m.split(".")[0] for m in modules if m.split(".")[0] in stems)
    return found


def _reload_closure_problems(server_source, retained, overrides=None):
    """Problems with the reload closure (wave 1zxnz, 1zx02): an evicted or
    reloaded module importing a flat module that is neither evicted, reloaded
    in place, nor allow-listed; and allow-list entries that are evicted or
    that no evicted module imports any more."""
    stems = _flat_stems()
    evicted = _evicted_flat_names(server_source)
    in_place = _in_place_reloaded(server_source)
    imported = set()
    for source in _evicted_module_sources(server_source, overrides).values():
        imported |= _flat_imports_anywhere(source, stems)
    problems = [f"not reloaded: {name}" for name in sorted(imported - evicted - in_place - set(retained))]
    problems += [f"allow-listed but evicted: {name}" for name in sorted(set(retained) & (evicted | in_place))]
    problems += [f"allow-listed but not imported: {name}" for name in sorted(set(retained) - imported)]
    return problems


def _module_level_nodes(tree):
    """Nodes that run at import time: everything outside function bodies."""
    stack = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


def _runtime_lock_binding_problems(server_source, stale_bindings, overrides=None):
    """Module-level ``from runtime_lock import NAME`` in a flat module the
    reload leaves loaded, where NAME is neither a ``runtime_lock`` exception
    class nor listed in ``stale_bindings``; plus stale map entries."""
    import runtime_lock

    overrides = overrides or {}
    evicted = _evicted_flat_names(server_source) | _in_place_reloaded(server_source)
    bindings = set()
    for stem in sorted(_flat_stems() - evicted):
        source = overrides.get(stem, None)
        if source is None:
            source = _source(stem)
        for node in _module_level_nodes(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and node.module == "runtime_lock" and not node.level:
                bindings.update((stem, alias.name) for alias in node.names)

    def is_exception_class(name):
        value = getattr(runtime_lock, name, None)
        return isinstance(value, type) and issubclass(value, BaseException)

    problems = [f"stale binding: {module}.{name}" for module, name in sorted(bindings)
                if not is_exception_class(name) and (module, name) not in stale_bindings]
    problems += [f"listed but not bound: {module}.{name}" for module, name in sorted(set(stale_bindings) - bindings)]
    return problems


def _patch_census(source, moved):
    tree = ast.parse(source)
    aliases = set()
    owners = set(MODULES)
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            aliases.update(a.asname or a.name for a in n.names if a.name == "server_impl")
            owners.update(a.asname or a.name for a in n.names if a.name in MODULES)
        if isinstance(n, ast.ImportFrom):
            aliases.update(a.asname or a.name for a in n.names if a.name == "server_impl")
            owners.update(a.asname or a.name for a in n.names if a.name in MODULES)
        if isinstance(n, ast.Assign):
            v = n.value
            if (isinstance(v, ast.Call) and _name(v.func).split(".")[-1] in {"load_server", "load_independent_server"}
                    or isinstance(v, ast.Subscript) and _name(v.value) == "sys.modules"
                    and isinstance(v.slice, ast.Constant) and v.slice.value == "server_impl"):
                aliases.update(_name(t) for t in n.targets)
    comments = {t.start[0]: t.string for t in tokenize.generate_tokens(io.StringIO(source).readline)
                if t.type == tokenize.COMMENT}
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    sites = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Attribute) or n.func.attr != "object" or len(n.args) < 2:
            continue
        target = n.args[1]
        if not isinstance(target, ast.Constant) or target.value not in moved:
            continue
        # Include the owning modules as well as server aliases: moved patches
        # must retain this runtime obligation after their target is repointed.
        owner = _name(n.args[0])
        if owner not in aliases | owners and not any(part in owner for part in MODULES):
            continue
        enclosing = [fn for fn in functions if fn.lineno <= n.lineno <= fn.end_lineno]
        fn = min(enclosing, key=lambda f: f.end_lineno - f.lineno) if enclosing else tree
        bound = None
        for w in ast.walk(fn):
            if isinstance(w, (ast.With, ast.AsyncWith)):
                for item in w.items:
                    if item.context_expr is n and item.optional_vars is not None:
                        bound = _name(item.optional_vars)
        # A visible comment must explain why this path intentionally never calls
        # its stub; merely spelling the marker does not establish a justification.
        nearby = " ".join(comments.get(i, "") for i in range(n.lineno - 2, n.end_lineno + 1))
        marker = "inert-by-design:"
        justified = marker in nearby and len(nearby.split(marker, 1)[1].strip()) >= 12
        called = False
        if bound:
            for x in ast.walk(fn):
                if not isinstance(x, ast.Call):
                    continue
                if isinstance(x.func, ast.Attribute) and _name(x.func.value) == bound and x.func.attr in {
                        "assert_called", "assert_called_once", "assert_called_with", "assert_called_once_with", "assert_any_call"}:
                    called = True
                if _name(x.func).endswith("assertTrue") and any(_name(a) == bound + ".called" for a in x.args):
                    called = True
                if _name(x.func).endswith("assertGreater") and x.args and _name(x.args[0]) == bound + ".call_count":
                    called = True
        sites.append((target.value, n.lineno, bound, called or justified, justified))
    return aliases, sites


class LifecycleGateStructureTests(unittest.TestCase):
    def test_facade_only_and_known_bad_carriers(self):
        for module in MODULES:
            self.assertEqual(_facade_errors(_source(module)), [], module)
        for marker in MARKERS:
            with self.subTest(marker=marker):
                self.assertTrue(_facade_errors("x = " + repr("prefix " + marker)))
                self.assertFalse(_facade_errors(repr(marker)))  # module docstring
        for bad in ("p = root / review_evidence.EVENTS_FILENAME",
                    "p = arbitrary.joinpath(review_evidence.EVENTS_FILENAME)",
                    "name = review_evidence.EVENTS_FILENAME\np = root / name\np.read_text()",
                    "from review_evidence import EVENTS_FILENAME as filename\nopen(Path(filename))"):
            self.assertTrue(_facade_errors(bad), bad)

    def test_import_direction_and_known_bad_imports(self):
        for module in MODULES:
            self.assertEqual(_import_errors(_source(module), module), [], module)
            for statement in ("import server_impl", "from server_impl import _diagnostic"):
                for source in (statement, "def f():\n    " + statement):
                    self.assertTrue(_import_errors(source, module))
        self.assertTrue(_import_errors("from lifecycle_gate_support import helper", "lifecycle_gates"))
        self.assertTrue(_import_errors("import lifecycle_gate_support as support\nhelper = support._diagnostic", "lifecycle_gates"))
        # 1yd99 AC-1: a module rebind by assignment escaped the import-only alias
        # set, so a moved helper could be bound through a local name with every
        # landed check green.  Both one-hop and chained rebinds are now caught.
        self.assertTrue(_import_errors(
            "import lifecycle_gate_support\nsupport = lifecycle_gate_support\nhelper = support._diagnostic",
            "lifecycle_gates"))
        self.assertTrue(_import_errors(
            "import lifecycle_gate_support\nfirst = lifecycle_gate_support\nsecond = first\nhelper = second._diagnostic",
            "lifecycle_gates"))
        # The positive corpus must stay green: an unrelated local rebind is not a
        # support alias, and neither is a same-named local in another module.
        self.assertEqual(_import_errors(
            "import lifecycle_gate_support\nsupport = object()\nhelper = support.anything", "lifecycle_gates"), [])
        for sibling in ("lifecycle_gates", "sensor_runner"):
            self.assertTrue(_import_errors("def f():\n    import " + sibling, "lifecycle_gate_support"))

    def test_context_contract_and_known_bad_access(self):
        gates = importlib.import_module("lifecycle_gates")
        fields = {f.name for f in dataclasses.fields(gates.GateContext)}
        self.assertEqual(fields, FIELDS)
        self.assertEqual(_context_errors(_source("lifecycle_gates"), fields), [])
        good = "def a(ctx):\n    return ctx.root\ndef b(ctx):\n    return helper(ctx)\ndef helper(value):\n    return value.root\nTEST_GATES = (a, b)\n"
        self.assertEqual(_context_errors(good, {"root"}), [])
        self.assertEqual(_context_errors(good.replace("return ctx.root", "data = {'root': ctx.root}\n    return ctx.root"), {"root"}), [])
        for bad in ("alias = ctx", "alias = {'context': ctx}", "getattr(ctx, 'root')", "vars(ctx)",
                    "dataclasses.asdict(ctx)", "ctx.root()", "ctx.unlisted"):
            mutated = good.replace("return ctx.root", bad + "\n    return ctx.root")
            self.assertTrue(_context_errors(mutated, {"root"}), bad)
        # Repeating the same unit in another tuple must not supply a second reader.
        self.assertTrue(_context_errors("def a(ctx):\n    return ctx.root\nA_GATES=(a,)\nB_GATES=(a,)", {"root"}))

    def test_patch_census_has_nonvacuous_runtime_obligations(self):
        moved = set().union(*(_definitions(ast.parse(_source(m))) for m in MODULES))
        self.assertTrue({"_diagnostic", "_review_evidence_diagnostics"}.issubset(moved))
        aliases, sites, invalid = set(), [], []
        for path in sorted((SCRIPTS / "tests").glob("test_*.py")):
            if path == Path(__file__):
                continue
            found_aliases, found_sites = _patch_census(path.read_text(encoding="utf-8"), moved)
            aliases.update(found_aliases)
            sites.extend(found_sites)
            invalid.extend((path.name, *site) for site in found_sites if not site[3])
        self.assertTrue({"srv", "self.srv", "server_impl"}.issubset(aliases), aliases)
        self.assertTrue({"_required_wave_council_signoffs", "_collect_silent_unchecked_items_for_close",
                         "_review_evidence_diagnostics"}.issubset({s[0] for s in sites}), sites)
        self.assertEqual(invalid, [], "Bind and assert a called mock, or explain its inert-by-design path")
        self.assertEqual(_patch_census("x = 1", moved)[0], set())
        sample = "def test():\n    srv = load_server()\n    with patch.object(srv, '_diagnostic') as stub:\n        pass\n"
        self.assertFalse(_patch_census(sample, moved)[1][0][3])
        self.assertTrue(_patch_census(sample + "    stub.assert_called_once()\n", moved)[1][0][3])
        justified = sample.replace("    with", "    # inert-by-design: this early return never reaches the diagnostic producer\n    with")
        self.assertTrue(_patch_census(justified, moved)[1][0][3])
        for spelling, expected in (("srv=load_independent_server()", "srv"),
                                   ("self.srv=load_server()", "self.srv"),
                                   ("import server_impl", "server_impl"),
                                   ("srv=sys.modules['server_impl']", "srv")):
            self.assertIn(expected, _patch_census(spelling, moved)[0])
        aliased = sample.replace("srv = load_server()", "import lifecycle_gates as gates").replace("patch.object(srv,", "patch.object(gates,")
        self.assertFalse(_patch_census(aliased, moved)[1][0][3])

    def test_reload_picks_up_every_added_module(self):
        from server_tools_support import _make_repo, load_server, load_thin_runner
        package = _package_modules() - {"server_impl"}
        names = (_direct_local_imports(_source("server_impl")) - _RELOAD_BOOTSTRAP_EXCLUSIONS) | package
        self.assertTrue(set(MODULES) <= names and {"graph_handlers", "mcp_tool_registry"} <= names, names)
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_repo(Path(tmp))
            load_server()
            runner = load_thin_runner()
            try:
                runner.build_server(root)
                for name in names:
                    stub = types.ModuleType(name)
                    stub.stale_gate_marker = True
                    sys.modules[name] = stub
                    if name in package:
                        sys.modules["wf_server." + name] = stub
                try:
                    response = runner.perform_mcp_reload()
                except Exception as exc:  # a purge gap leaves a stub and the reload raises
                    self.fail(f"reload raised {type(exc).__name__}: {exc}")
                self.assertEqual(response["status"], "ok", response)
                retired = _retired_table(_source("server_impl"))
                self.assertTrue(retired and retired <= package, retired)
                for name in names:
                    module = sys.modules["wf_server." + name] if name in package else sys.modules[name]
                    self.assertFalse(hasattr(module, "stale_gate_marker"), name)
                    self.assertEqual(Path(module.__file__).resolve(), source_path(name).resolve())
                    if name in retired:
                        # Wave 1yxyw: the stale flat key an older host held is
                        # evicted and never re-registered.
                        self.assertNotIn(name, sys.modules, name)
                    elif name in package:
                        self.assertIs(sys.modules[name], module, name)
            finally:
                runner._get_handler().close()

    def test_reload_purge_covers_direct_sibling_imports(self):
        source = _source("server_impl")
        imports = _direct_local_imports(source)
        self.assertTrue(_RELOAD_BOOTSTRAP_EXCLUSIONS.issubset(imports))
        reloadable = imports - _RELOAD_BOOTSTRAP_EXCLUSIONS
        self.assertIn("index_source_guard", reloadable)
        self.assertIn("graph_handlers", reloadable)  # package imports are counted (wave 1yzd0)
        self.assertEqual(reloadable - _purge_covered(source), set())
        # Every package module but server_impl is purged, derived from the files
        # on disk rather than from the table the purge itself reads.
        self.assertEqual(_package_modules() - {"server_impl"} - _purge_covered(source), set())
        purge_keys = _evaluated_purge_keys(source)
        for name in _package_modules() - {"server_impl"}:
            self.assertTrue({name, "wf_server." + name} <= purge_keys, name)
        self.assertFalse({"server_impl", "wf_server.server_impl", "wf_server"} & purge_keys)
        dropped = source.replace('"graph_handlers", ', '', 1)
        self.assertNotEqual(dropped, source)
        self.assertNotIn("graph_handlers", _retired_table(dropped))
        self.assertEqual(_package_modules() - {"server_impl"} - _purge_covered(dropped), {"graph_handlers"})
        # The old purge-derived test silently lost coverage when an entry was
        # omitted. Derive expected modules from imports even for this mutant.
        omitted = source.replace('            "index_source_guard",\n', '')
        self.assertNotEqual(omitted, source)
        self.assertEqual(
            (_direct_local_imports(omitted) - _RELOAD_BOOTSTRAP_EXCLUSIONS)
            - _purge_covered(omitted), {"index_source_guard"})

    def test_reload_refreshes_imported_siblings_and_source_guard_callable(self):
        from server_tools_support import _make_repo, load_server, load_thin_runner
        names = _direct_local_imports(_source("server_impl")) - _RELOAD_BOOTSTRAP_EXCLUSIONS
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as patches:
            root = _make_repo(Path(tmp))
            impl = load_server()
            runner = load_thin_runner()
            try:
                runner.build_server(root)
                # Package modules are keyed by their package name: a retired
                # flat alias no longer exists (wave 1yxyw).
                package = _package_modules()
                key = {name: "wf_server." + name if name in package else name for name in names}
                old_modules = {name: sys.modules[key[name]] for name in names}
                for module in old_modules.values():
                    patches.enter_context(patch.object(module, "stale_reload_marker", True, create=True))
                stale_guard = lambda *args, **kwargs: "stale-source-guard"
                patches.enter_context(patch.object(impl.index_source_guard, "index_source_guard", stale_guard))
                try:
                    response = runner.perform_mcp_reload()
                except Exception as exc:
                    self.fail(f"reload raised {type(exc).__name__}: {exc}")
                self.assertEqual(response["status"], "ok", response)
                for name, old_module in old_modules.items():
                    fresh = sys.modules[key[name]]
                    self.assertIsNot(fresh, old_module, name)
                    self.assertFalse(hasattr(fresh, "stale_reload_marker"), name)
                    self.assertEqual(Path(fresh.__file__).resolve(), source_path(name).resolve())
                guard = runner.server_impl.index_source_guard.index_source_guard
                self.assertIsNot(guard, stale_guard)
                with guard(root, wait=False):
                    self.assertTrue((root / ".wavefoundry/locks/index-source-mutation.lock").is_file())
            finally:
                runner._get_handler().close()

    def test_sensor_gate_is_last_in_the_close_hard_gates(self):
        """1yd98 AC-5: the intra-tuple position the precondition depends on.

        `1y0bd` Requirement 5 stated this position in prose; nothing pinned it.
        The close orchestrator computes the blocking keyword after iterating
        `CLOSE_HARD_GATES[:-1]`, so a reorder would hand the keyword to a
        different gate and withhold nothing, with every other test green.
        """
        import lifecycle_gates

        def position_holds():
            # Reads the module attribute itself, so `patch.object` below is
            # load-bearing.  Taking the tuple as a parameter and passing the
            # patched attribute in was behaviourally identical to passing the
            # local rotation, which proved nothing about any tuple in use.
            return lifecycle_gates.CLOSE_HARD_GATES[-1] is lifecycle_gates.required_sensors_gate

        self.assertTrue(position_holds())
        # Known-bad: re-run the same oracle with the module's own tuple reordered.
        rotated = (lifecycle_gates.CLOSE_HARD_GATES[-1],) + lifecycle_gates.CLOSE_HARD_GATES[:-1]
        with patch.object(lifecycle_gates, "CLOSE_HARD_GATES", rotated):
            self.assertFalse(position_holds(),
                             "the oracle must redden on a reordered tuple")

    def test_blocking_predicate_has_exactly_one_implementation(self):
        """1yd98 AC-11: no second spelling of the advisory-aware predicate.

        The scan rejects any comparison in the blocking direction over a
        diagnostics collection, not only the spelling the extracted helper uses,
        so a respelled copy at the close orchestrator does not escape.  The close
        envelope's `advisory_diagnostics` selection compares in the opposite
        direction for a different purpose and is out of scope.
        """
        import lifecycle_gates

        def _advisory_get(node):
            # Call form `x.get("advisory")` and subscript form `x["advisory"]`.
            if isinstance(node, ast.Subscript):
                key = node.slice
                return isinstance(key, ast.Constant) and key.value == "advisory"
            return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get" and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and node.args[0].value == "advisory")

        def blocking_comparisons(source):
            tree = ast.parse(source)
            found = []
            for node in ast.walk(tree):
                # A blocking-direction test over an advisory key, in any spelling.
                # Matching only `is not True` let a respelled copy escape, which a
                # delivery mutation proved; `not x.get("advisory")` and
                # `x.get("advisory") != True` are the same predicate.
                if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                    operand = node.operand
                    # `not x.get("advisory")` and `not x.get("advisory") is True`.
                    if _advisory_get(operand):
                        found.append(ast.unparse(node))
                    elif (isinstance(operand, ast.Compare) and len(operand.ops) == 1
                          and isinstance(operand.ops[0], (ast.Is, ast.Eq))
                          and isinstance(operand.comparators[0], ast.Constant)
                          and operand.comparators[0].value is True
                          and _advisory_get(operand.left)):
                        found.append(ast.unparse(node))
                    continue
                if not isinstance(node, ast.Compare) or len(node.ops) != 1:
                    continue
                if not isinstance(node.ops[0], (ast.IsNot, ast.NotEq)):
                    continue
                comparator = node.comparators[0]
                if not (isinstance(comparator, ast.Constant) and comparator.value is True):
                    continue
                if not _advisory_get(node.left):
                    continue
                found.append(ast.unparse(node))
            return found

        gate_source = _source("lifecycle_gates")
        self.assertEqual(len(blocking_comparisons(gate_source)), 1, "the helper is the only implementation")
        server_source = source_path("server_impl.py").read_text(encoding="utf-8")
        self.assertEqual(blocking_comparisons(server_source), [],
                         "server_impl must call lifecycle_gates.has_blocking_diagnostics")
        self.assertIn("d.get('advisory') is True", ast.unparse(ast.parse(server_source)),
                      "the opposite-direction advisory selection stays")
        # Known-bads: the pinned spelling and two respellings of the same predicate.
        for spelling in ('any(x.get("advisory") is not True for x in diagnostics)',
                         'any(not x.get("advisory") for x in diagnostics)',
                         'any(x.get("advisory") != True for x in diagnostics)',
                         'any(not x.get("advisory") is True for x in diagnostics)',
                         'any(x["advisory"] is not True for x in diagnostics)'):
            with self.subTest(respelling=spelling):
                mutated = server_source.replace(
                    "if lifecycle_gates.has_blocking_diagnostics(diagnostics):",
                    f"if {spelling}:", 1)
                self.assertEqual(len(blocking_comparisons(mutated)), 1,
                                 "known-bad: a reintroduced copy is seen in any spelling")

    def test_statements_this_change_leaves_alone_survive(self):
        """1yd98 AC-10: three statements deliberately outside the amendment set.

        Their absence from that set is a scoping decision, so it is asserted
        rather than inferred.  Each expected string is transcribed from the
        pre-change tree, so this pins what stood before the amendment pass
        rather than whatever the pass produced.
        """
        repo = SCRIPTS.parents[2]
        surface = (repo / "docs/specs/mcp-tool-surface.md").read_text(encoding="utf-8")
        # Stays true: Requirement 3 leaves the prepare call site passing no keyword.
        self.assertIn(
            "reached required sensors run in `ready`/`create`, while dry-run reports "
            "`would_run` without execution.", surface)
        # Pinned independently by a docs-constants lint row; this change must not move it.
        self.assertIn("configured_gates outcomes: `would_run/passed/failed/invalid`", surface)
        prior = (repo / "docs/waves/1y0h0 typed-phase-gates"
                 / "1y0bd-enh config-declared-phase-gates.md").read_text(encoding="utf-8")
        # 1y0bd AC-9's provenance-only invariant: not a member, not cited, unchanged.
        self.assertIn("- [x] AC-9: `sensor_runner` is a member of the purge-set literal", prior)
        self.assertIn("so layering row (a) is mechanically verified for every module it names.", prior)


class ReloadClosureGuardTests(unittest.TestCase):
    """Wave 1zxnz (1zx02) AC-10: what a reload re-imports never imports a
    flat module the reload leaves stale, unless the allow-list says why."""

    def setUp(self):
        self.source = _source("server_impl")

    def test_the_tree_passes_with_the_starting_lists(self):
        self.assertEqual(_in_place_reloaded(self.source), {"runtime_lock"})
        self.assertEqual(_reload_closure_problems(self.source, _RELOAD_RETAINED_FLAT_MODULES), [])
        self.assertEqual(_runtime_lock_binding_problems(self.source, _RUNTIME_LOCK_STALE_BINDINGS), [])
        self.assertEqual(len(_RELOAD_RETAINED_FLAT_MODULES), 24)  # 1zyv1 adds bytecode_cache (runner bootstrap)
        self.assertNotIn("runtime_lock", _RELOAD_RETAINED_FLAT_MODULES)
        self.assertTrue(_RELOAD_BOOTSTRAP_EXCLUSIONS <= set(_RELOAD_RETAINED_FLAT_MODULES))
        self.assertTrue(all(reason.strip() for reason in _RELOAD_RETAINED_FLAT_MODULES.values()))

    def test_an_unlisted_stale_import_is_reported_by_name(self):
        evicted = _evicted_flat_names(self.source) | _in_place_reloaded(self.source)
        candidates = sorted(_flat_stems() - evicted - set(_RELOAD_RETAINED_FLAT_MODULES))
        self.assertTrue(candidates)
        stale = candidates[0]
        lifecycle_lock = _source("lifecycle_lock")
        mutated = {"lifecycle_lock": lifecycle_lock + f"\n\ndef _probe():\n    import {stale}\n"}
        self.assertEqual(
            _reload_closure_problems(self.source, _RELOAD_RETAINED_FLAT_MODULES, mutated),
            [f"not reloaded: {stale}"],
        )

    def test_removing_the_in_place_reload_reports_runtime_lock(self):
        mutated = self.source.replace('_IN_PLACE_RELOAD_MODULES = ("runtime_lock",)',
                                      "_IN_PLACE_RELOAD_MODULES = ()", 1)
        self.assertNotEqual(mutated, self.source)
        self.assertEqual(_reload_closure_problems(mutated, _RELOAD_RETAINED_FLAT_MODULES),
                         ["not reloaded: runtime_lock"])

    def test_allow_list_entries_must_be_retained_and_imported(self):
        evicted = dict(_RELOAD_RETAINED_FLAT_MODULES, lifecycle_lock="evicted, so wrong here")
        self.assertEqual(_reload_closure_problems(self.source, evicted),
                         ["allow-listed but evicted: lifecycle_lock"])
        in_place = dict(_RELOAD_RETAINED_FLAT_MODULES, runtime_lock="reloaded in place, so wrong here")
        self.assertEqual(_reload_closure_problems(self.source, in_place),
                         ["allow-listed but evicted: runtime_lock"])
        evicted_names = _evicted_flat_names(self.source) | _in_place_reloaded(self.source)
        unused = sorted(_flat_stems() - evicted_names - set(_RELOAD_RETAINED_FLAT_MODULES))[0]
        extra = dict(_RELOAD_RETAINED_FLAT_MODULES, **{unused: "no evicted module imports it"})
        self.assertEqual(_reload_closure_problems(self.source, extra),
                         [f"allow-listed but not imported: {unused}"])

    def test_a_new_module_level_runtime_lock_binding_is_reported(self):
        target = "process_info"
        self.assertNotIn(target, _evicted_flat_names(self.source))
        mutated = {target: _source(target) + "\nfrom runtime_lock import RuntimeFileLock\n"}
        self.assertEqual(
            _runtime_lock_binding_problems(self.source, _RUNTIME_LOCK_STALE_BINDINGS, mutated),
            [f"stale binding: {target}.RuntimeFileLock"],
        )
        # Exception classes keep their identity across the reload; a
        # function-local import runs against the reloaded module.
        exceptions = {target: _source(target) + "\nfrom runtime_lock import RuntimeLockBusy\n"}
        self.assertEqual(
            _runtime_lock_binding_problems(self.source, _RUNTIME_LOCK_STALE_BINDINGS, exceptions), [])
        local = {target: _source(target) + "\ndef _probe():\n    from runtime_lock import RuntimeFileLock\n"}
        self.assertEqual(
            _runtime_lock_binding_problems(self.source, _RUNTIME_LOCK_STALE_BINDINGS, local), [])
        dropped = {key: value for key, value in _RUNTIME_LOCK_STALE_BINDINGS.items()
                   if key != ("scanner_skips", "RuntimeFileLock")}
        self.assertEqual(_runtime_lock_binding_problems(self.source, dropped),
                         ["stale binding: scanner_skips.RuntimeFileLock"])


if __name__ == "__main__":
    unittest.main()

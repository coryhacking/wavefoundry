"""Wave 1yzd0: the ``wf_server`` package boundary.

Twelve server-owned modules live in ``scripts/wf_server/``. Each keeps a flat
file whose whole body replaces itself in ``sys.modules`` with the package
module, so the flat names stay the public import surface while there is one
module object per implementation. These tests pin the layout, the aliases,
module identity, scripts-root resolution, the upgrade constraint older runners
impose, and the two test censuses that keep a test from reading or enumerating
an alias as if it were the implementation.
"""
from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from framework_files import PACKAGE_DIR, framework_source_files, package_module_names, source_path
from server_tools_support import load_server

MOVED = frozenset({
    "server_impl", "mcp_tool_registry", "codenav_handlers", "graph_handlers", "techdocs_handlers",
    "memory_handlers", "index_handlers", "upgrade_handlers", "edit_gate_handlers",
    "dashboard_handlers", "docs_handlers", "context_efficiency_handlers",
})
ALIAS_BODY = 'import importlib\nimport sys\n\nsys.modules[__name__] = importlib.import_module("wf_server.{name}")\n'
RETAINED_DECLARATIONS = ("mcp_tool_extensions.py", "mcp_tool_roster.py", "record_paths.py", "server.py")


def _run(code: str) -> dict:
    """Run ``code`` in a fresh interpreter with the scripts root on sys.path."""
    result = subprocess.run(
        [sys.executable, "-B", "-c", code, str(SCRIPTS)],
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr[-4000:])
    return json.loads(result.stdout.strip().splitlines()[-1])


class PackageStructureTests(unittest.TestCase):
    def test_package_holds_exactly_the_inventoried_modules(self):
        self.assertEqual({p.name for p in PACKAGE_DIR.glob("*.py")}, {n + ".py" for n in MOVED} | {"__init__.py"})
        self.assertEqual(package_module_names(), MOVED)
        self.assertEqual([p.name for p in PACKAGE_DIR.iterdir() if p.is_dir() and p.name != "__pycache__"], [])
        # The initializer is never reloaded, so it stays empty (import-free).
        self.assertEqual((PACKAGE_DIR / "__init__.py").read_bytes(), b"")

    def test_flat_aliases_have_the_exact_pinned_bytes(self):
        # A downstream merge that restores a full flat file must fail here.
        for name in sorted(MOVED):
            with self.subTest(module=name):
                self.assertEqual((SCRIPTS / f"{name}.py").read_bytes(), ALIAS_BODY.format(name=name).encode())

    def test_alias_and_evaluator_tables_match_the_inventory(self):
        import retrieval_eval
        server = load_server()
        self.assertEqual(server._FLAT_ALIASES, {name: f"wf_server.{name}" for name in MOVED})
        self.assertEqual(retrieval_eval.SERVER_PACKAGE_DIR, "wf_server")
        self.assertEqual(retrieval_eval.SERVER_PACKAGE_MODULES, frozenset(n + ".py" for n in MOVED))

    def test_declarations_and_entry_point_stay_flat(self):
        for name in RETAINED_DECLARATIONS:
            with self.subTest(file=name):
                self.assertTrue((SCRIPTS / name).is_file())
                self.assertFalse((PACKAGE_DIR / name).exists())
                self.assertNotIn("sys.modules[__name__] = importlib.import_module", (SCRIPTS / name).read_text())
        self.assertFalse((SCRIPTS / "server").exists(), "no server/ package may shadow server.py")

    def test_setup_identity_adds_only_the_package_implementation(self):
        import setup_readiness
        self.assertEqual([n for n in setup_readiness.SOURCE_FILES if "/" in n], ["wf_server/server_impl.py"])
        self.assertIn("server_impl.py", setup_readiness.SOURCE_FILES)
        identity = setup_readiness.capture_loaded_identity()
        self.assertEqual(identity["sources"]["wf_server/server_impl.py"],
                         hashlib.sha256((PACKAGE_DIR / "server_impl.py").read_bytes()).hexdigest())

    def test_package_name_is_reserved_for_extension_modules(self):
        import mcp_tool_extensions
        self.assertIn("wf_server", mcp_tool_extensions.RESERVED_MODULE_NAMES)


class ModuleIdentityTests(unittest.TestCase):
    def test_flat_and_package_names_are_one_module_object(self):
        observed = _run(
            "import json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            # A consumer without the runner imports a handler first (memory_cli does).
            "import memory_handlers\n"
            "import server_impl\n"
            f"names = {sorted(MOVED)!r}\n"
            # Registered by server_impl itself, before any other flat import.
            "eager = {n: sys.modules.get(n) is sys.modules.get('wf_server.' + n) is not None for n in names}\n"
            "print(json.dumps({\n"
            "    'eager': eager,\n"
            "    'same': {n: __import__(n) is sys.modules['wf_server.' + n] for n in names},\n"
            "    'module_names': sorted({sys.modules[n].__name__ for n in names}),\n"
            "    'package_dir_on_path': any(p.rstrip('/\\\\').endswith('wf_server') for p in sys.path),\n"
            "    'scripts_dir': str(server_impl.SCRIPTS_DIR),\n"
            "}))\n"
        )
        self.assertEqual(observed["eager"], {name: True for name in MOVED})
        self.assertEqual(observed["same"], {name: True for name in MOVED})
        self.assertEqual(observed["module_names"], sorted("wf_server." + name for name in MOVED))
        self.assertFalse(observed["package_dir_on_path"])
        self.assertEqual(Path(observed["scripts_dir"]).resolve(), SCRIPTS.resolve())

    def test_declaration_consumers_import_without_mcp(self):
        observed = _run(
            "import json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "sys.modules['mcp'] = None  # any MCP import now raises\n"
            "import mcp_tool_extensions, mcp_tool_roster, record_paths, wf_server\n"
            "print(json.dumps(sorted(k for k in vars(wf_server) if not k.startswith('__'))))\n"
        )
        self.assertEqual(observed, [], "the package initializer imports nothing")

    def test_a_private_name_load_never_registers_the_aliases(self):
        # Eager registration is guarded on the canonical module name, so a
        # private spec load of the package file (a test's second instance)
        # leaves the flat handler keys to the canonical load.
        observed = _run(
            "import importlib.util, json, sys\n"
            "sys.path.insert(0, sys.argv[1])\n"
            "import server_impl\n"
            "canonical = sys.modules['wf_server.server_impl']\n"
            "spec = importlib.util.spec_from_file_location('server_impl_private', "
            "sys.argv[1] + '/wf_server/server_impl.py')\n"
            "private = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(private)\n"
            "print(json.dumps({\n"
            "    'server_impl_is_canonical': sys.modules['server_impl'] is canonical,\n"
            "    'handler_alias_registered': 'graph_handlers' in sys.modules,\n"
            "    'private_has_handlers': hasattr(private, 'wf_graph_report_response'),\n"
            "}))\n"
        )
        self.assertEqual(observed, {"server_impl_is_canonical": True, "handler_alias_registered": False,
                                    "private_has_handlers": True})


class HollowLoaderTests(unittest.TestCase):
    """A file loader of a moved flat file executes the alias, which replaces
    ``sys.modules[name]`` and leaves the loaded object empty. The repaired
    test loaders must hand back the real module."""

    def test_repaired_loaders_return_the_package_module(self):
        import test_graph_snapshot_readers
        import test_memory_records
        for loader in (test_graph_snapshot_readers._load, test_memory_records._load):
            with self.subTest(loader=loader.__module__):
                module = loader("server_impl")
                self.assertEqual(module.__name__, "wf_server.server_impl")
                self.assertTrue(hasattr(module, "wf_graph_report_response"))
        independent = test_memory_records.load_independent_server()
        self.assertEqual(independent.__name__, "server_impl_proc2")
        self.assertTrue(hasattr(independent, "_MEMORY_RECORDS_CACHE"))


class ScriptsRootTests(unittest.TestCase):
    """Each silent degradation the readiness inventory found: moved as-is, these
    read files beside the package and fall back without an error."""

    def setUp(self):
        self.srv = load_server()

    def test_scripts_root_is_not_the_package_directory(self):
        self.assertEqual(self.srv.SCRIPTS_DIR.resolve(), SCRIPTS.resolve())
        self.assertNotIn(str(PACKAGE_DIR), sys.path)

    def test_version_and_chunker_version_resolve(self):
        version = (SCRIPTS.parent / "VERSION").read_text(encoding="utf-8").strip()
        self.assertTrue(version)
        self.assertEqual(self.srv.SERVER_IMPL_VERSION, version)
        self.assertEqual(self.srv._read_framework_pack_version(), version)
        import chunker
        self.assertEqual(self.srv._read_chunker_version(), chunker.CHUNKER_VERSION)

    def test_default_template_reads_the_install_asset(self):
        expected = (SCRIPTS.parent / "install" / "plan-template.md").read_text(encoding="utf-8")
        try:
            template = self.srv._default_template(None)
        except RuntimeError as exc:  # the install asset was looked up beside the package
            self.fail(str(exc))
        self.assertEqual(template, expected)

    def test_load_script_and_upgrade_sentinel_read_retained_scripts(self):
        module = self.srv._load_script("graph_cluster")
        self.assertEqual(Path(module.__file__).resolve(), (SCRIPTS / "graph_cluster.py").resolve())
        import upgrade_handlers
        sentinel = upgrade_handlers._upgrade_summary_sentinel()
        upgrade = sys.modules["upgrade_wavefoundry"]
        self.assertEqual(Path(upgrade.__file__).resolve(), (SCRIPTS / "upgrade_wavefoundry.py").resolve())
        self.assertEqual(sentinel, upgrade.WAVE_UPGRADE_SUMMARY_SENTINEL)

    def test_harness_coherence_sees_runner_and_implementation_tools(self):
        # wf_reload_mcp is defined only in server.py; wf_graph_report only in the
        # package implementation. Reading the flat alias drops the second.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seeds = root / ".wavefoundry" / "framework" / "seeds"
            seeds.mkdir(parents=True)
            (seeds / "900-probe.prompt.md").write_text(
                "Use wf_reload_mcp, then wf_graph_report; never wf_probe_not_a_tool.\n", encoding="utf-8")
            findings = self.srv._audit_harness_coherence(root)["findings"]
        stale = {f["detail"].split("'")[1] for f in findings if f["type"] == "stale_tool_reference"}
        self.assertEqual(stale, {"wf_probe_not_a_tool"})


class OldRunnerCompatibilityTests(unittest.TestCase):
    """Installed 1.25/1.26 runners validate a new pack with these same functions;
    they count only flat modules, so mandatory upgrade modules import flat names."""

    def _pack_names(self, files):
        return {".wavefoundry/framework/scripts/" + p.relative_to(SCRIPTS).as_posix() for p in files}

    def test_mandatory_modules_pass_the_real_validation(self):
        import upgrade_protocol
        available = upgrade_protocol._pack_module_names(
            self._pack_names(framework_source_files(include_aliases=True)))
        self.assertTrue({"server_impl", "dashboard_handlers"} <= available)
        for module in upgrade_protocol.MANDATORY_FEATURE_MODULES:
            with self.subTest(module=module):
                tree = ast.parse((SCRIPTS / module).read_text(encoding="utf-8"))
                upgrade_protocol._validate_imports(tree, module, available)

    def test_package_imports_and_missing_aliases_are_refused(self):
        import upgrade_protocol
        with_aliases = upgrade_protocol._pack_module_names(
            self._pack_names(framework_source_files(include_aliases=True)))
        for statement in ("import wf_server.server_impl", "from wf_server import server_impl",
                          "def f():\n    from wf_server.dashboard_handlers import x"):
            with self.subTest(statement=statement), self.assertRaises(upgrade_protocol.UpgradeProtocolError):
                upgrade_protocol._validate_imports(ast.parse(statement), "upgrade_wavefoundry.py", with_aliases)
        without_aliases = upgrade_protocol._pack_module_names(self._pack_names(framework_source_files()))
        with self.assertRaises(upgrade_protocol.UpgradeProtocolError):
            upgrade_protocol._validate_imports(ast.parse("def f():\n    import server_impl"),
                                               "upgrade_wavefoundry.py", without_aliases)


# ------------------------------------------------------------------ censuses
_SCRIPTS_ROOT_NAMES = {"SCRIPTS", "SCRIPTS_ROOT", "SCRIPTS_DIR", "SCRIPTS_PATH", "self.SCRIPTS"}
# ``<owner>.__file__`` names the package file when the owner is a loaded moved
# module (the test seams bind server_impl to these names).
_PACKAGE_MODULE_OWNERS = {"srv", "self.srv", "server_impl", "impl", "self.impl", "self.server_impl"}
_OPEN_MODULES = {"tokenize", "io", "codecs"}
_CENSUS_EXEMPT = {"framework_files.py", "test_server_package.py"}


def _is_scripts_root(node: ast.AST) -> bool:
    text = ast.unparse(node)
    # In tests/<file>.py, ``Path(__file__)...parents[1]`` is the scripts root.
    return text in _SCRIPTS_ROOT_NAMES or text.endswith("parents[1]")


def _matches_flat_file(pattern: object) -> bool:
    return isinstance(pattern, str) and fnmatch.fnmatch("server_impl.py", pattern)


def _flat_glob_sites(source: str) -> list[str]:
    """Flat enumerations of the scripts root that would list the alias files:
    a non-recursive ``glob`` whose pattern matches a moved flat file,
    ``iterdir``, ``os.listdir``/``os.scandir``, or ``glob.glob`` over it."""
    sites = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "glob" and _is_scripts_root(func.value):
            if node.args and isinstance(node.args[0], ast.Constant) and _matches_flat_file(node.args[0].value):
                sites.append(ast.unparse(node))
        elif isinstance(func, ast.Attribute) and func.attr == "iterdir" and _is_scripts_root(func.value):
            sites.append(ast.unparse(node))
        elif (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
              and (func.value.id, func.attr) in {("os", "listdir"), ("os", "scandir"), ("glob", "glob"),
                                                 ("glob", "iglob")}
              and node.args and any(_is_scripts_root(n) for n in ast.walk(node.args[0]))):
            sites.append(ast.unparse(node))
    return sites


def _is_flat_moved(value: object) -> bool:
    if not isinstance(value, str) or "wf_server" in value:
        return False
    return any(value == f"{n}.py" or value.endswith(f"/{n}.py") for n in MOVED)


def _assignments(tree: ast.AST) -> dict[str, list[ast.AST]]:
    """Every value assigned to each simple name, for one level of indirection."""
    values: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values.setdefault(target.id, []).append(node.value)
    return values


def _read_target_problem(target: ast.AST) -> bool:
    if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {"source_path", "shipped_path"}
           for n in ast.walk(target)):
        return False
    # Package-relative forms read the implementation: a path spelled through
    # the package directory, or one derived from a loaded moved module's own
    # ``__file__``. The flat runner ``server.__file__`` is not exempt.
    if any(isinstance(n, ast.Constant) and n.value == "wf_server" for n in ast.walk(target)):
        return False
    if any(isinstance(n, ast.Attribute) and n.attr == "__file__" and ast.unparse(n.value) in _PACKAGE_MODULE_OWNERS
           for n in ast.walk(target)):
        return False
    if any(isinstance(n, ast.Constant) and _is_flat_moved(n.value) for n in ast.walk(target)):
        return True
    for n in ast.walk(target):
        if (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div) and _is_scripts_root(n.left)
                and not isinstance(n.right, ast.Constant)):
            return True
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "joinpath"
                and _is_scripts_root(n.func.value) and any(not isinstance(a, ast.Constant) for a in n.args)):
            return True
    return False


def _source_read_sites(source: str) -> list[str]:
    """Reads of a moved module's flat file, or computed scripts-root reads that
    bypass ``source_path``. A read is ``.read_text()``, ``.read_bytes()``,
    ``.open(...)``, ``open(...)``/``tokenize.open(...)``/``io.open(...)`` or an
    archive ``.read(<member>)``; a simple name used as the target is resolved
    through its assignments."""
    tree = ast.parse(source)
    assigned = _assignments(tree)
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Attribute) and func.attr == "open" and isinstance(func.value, ast.Name)
                and func.value.id in _OPEN_MODULES and node.args):
            target = node.args[0]
        elif isinstance(func, ast.Attribute) and func.attr in {"read_text", "read_bytes", "open"}:
            target = func.value
        elif isinstance(func, ast.Name) and func.id == "open" and node.args:
            target = node.args[0]
        elif isinstance(func, ast.Attribute) and func.attr == "read" and node.args:
            target = node.args[0]
        else:
            continue
        candidates = [target]
        if isinstance(target, ast.Name):
            candidates += assigned.get(target.id, [])
        if any(_read_target_problem(c) for c in candidates):
            sites.append(ast.unparse(target))
    return sites


def _hollow_loader_sites(source: str) -> list[str]:
    """File loaders that execute a spec for a computed module path and return
    the executed object: given a moved flat name they return the object the
    alias left empty. Return ``sys.modules[name]`` instead."""
    sites = []
    for fn in ast.walk(ast.parse(source)):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        computed = any(
            isinstance(n, ast.Call) and ast.unparse(n.func).endswith("spec_from_file_location") and len(n.args) >= 2
            and not isinstance(n.args[1], ast.Constant) and _is_scripts_root_path(n.args[1])
            for n in ast.walk(fn))
        executed = {ast.unparse(n.args[0]) for n in ast.walk(fn)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "exec_module" and n.args}
        returned = {ast.unparse(n.value) for n in ast.walk(fn) if isinstance(n, ast.Return) and n.value is not None}
        if computed and executed & returned:
            sites.append(fn.name)
    return sites


def _is_scripts_root_path(node: ast.AST) -> bool:
    """``<scripts root> / <non-constant>``: a path that can name any module."""
    return (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and _is_scripts_root(node.left)
            and not isinstance(node.right, ast.Constant))


def _test_sources():
    for path in sorted((SCRIPTS / "tests").glob("*.py")):
        if path.name not in _CENSUS_EXEMPT:
            yield path.name, path.read_text(encoding="utf-8")


class TestCensusTests(unittest.TestCase):
    def test_no_flat_enumeration_of_the_scripts_root_outside_the_helper(self):
        found = {name: sites for name, source in _test_sources() if (sites := _flat_glob_sites(source))}
        self.assertEqual(found, {}, "enumerate framework files through framework_files.framework_source_files")
        for bad in ('paths = SCRIPTS_ROOT.glob("*.py")', 'paths = sorted(SCRIPTS.glob("*_impl.py"))',
                    'paths = SCRIPTS.iterdir()', 'names = os.listdir(SCRIPTS)', 'names = os.scandir(SCRIPTS_ROOT)',
                    'paths = glob.glob(str(SCRIPTS / "*.py"))', 'paths = SCRIPTS_PATH.glob("*.py")',
                    'paths = Path(__file__).resolve().parents[1].glob("*.py")'):
            with self.subTest(bad=bad):
                self.assertTrue(_flat_glob_sites(bad))
        for good in ('paths = SCRIPTS.glob("test_*.py")', 'paths = (SCRIPTS / "wave_lint_lib").glob("*.py")',
                     'paths = SCRIPTS.rglob("*.py")', 'paths = (SCRIPTS / "wf_server").iterdir()',
                     'names = os.listdir(tmp)'):
            with self.subTest(good=good):
                self.assertFalse(_flat_glob_sites(good))

    def test_no_source_read_of_a_moved_flat_path(self):
        found = {name: sites for name, source in _test_sources() if (sites := _source_read_sites(source))}
        self.assertEqual(found, {}, "read moved-module sources through framework_files.source_path")
        for bad in ('(SCRIPTS_ROOT / "server_impl.py").read_text()',
                    'SCRIPTS_ROOT.joinpath("index_handlers.py").read_text()',
                    'SCRIPTS.joinpath(name).read_text()',
                    'SCRIPTS.joinpath(f"{n}.py").read_text()',
                    'open(SCRIPTS / "graph_handlers.py")',
                    'tokenize.open(SCRIPTS / "server_impl.py")',
                    'zf.read(".wavefoundry/framework/scripts/server_impl.py")',
                    '(SCRIPTS / name).read_text()',
                    '(self.SCRIPTS / f"{name}.py").read_bytes()',
                    'p = SCRIPTS / "server_impl.py"\np.read_text()',
                    '(Path(__file__).parents[1] / name).read_text()',
                    'Path(server.__file__).with_name("server_impl.py").read_text()'):
            with self.subTest(bad=bad):
                self.assertTrue(_source_read_sites(bad))
        for good in ('source_path("server_impl.py").read_text()',
                     'Path(self.srv.__file__).with_name("index_handlers.py").read_text()',
                     '(ROOT / "scripts" / "wf_server" / "server_impl.py").read_text()',
                     '(SCRIPTS / "wf_server" / "server_impl.py").read_text()',
                     'zf.read(".wavefoundry/framework/scripts/wf_server/server_impl.py")',
                     '(SCRIPTS / "chunker.py").read_text()',
                     'p = source_path(name)\np.read_text()',
                     'shipped_path(name).read_text()',
                     '(tmp / "server_impl.py").write_text("x")'):
            with self.subTest(good=good):
                self.assertFalse(_source_read_sites(good))

    def test_no_file_loader_returns_a_hollow_module(self):
        found = {name: sites for name, source in _test_sources() if (sites := _hollow_loader_sites(source))}
        self.assertEqual(found, {}, "a computed-name file loader returns sys.modules[name]")
        bad = ("def _load(name):\n    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')\n"
               "    mod = importlib.util.module_from_spec(spec)\n    spec.loader.exec_module(mod)\n    return mod\n")
        self.assertEqual(_hollow_loader_sites(bad), ["_load"])
        self.assertEqual(_hollow_loader_sites(bad.replace("return mod", "return sys.modules[name]")), [])
        fixed_path = bad.replace("SCRIPTS / f'{name}.py'", "SCRIPTS / 'chunker.py'")
        self.assertEqual(_hollow_loader_sites(fixed_path), [])

    def test_helpers_resolve_the_implementation(self):
        self.assertEqual(source_path("server_impl.py"), PACKAGE_DIR / "server_impl.py")
        self.assertEqual(source_path("graph_handlers"), PACKAGE_DIR / "graph_handlers.py")
        self.assertEqual(source_path("chunker.py"), SCRIPTS / "chunker.py")
        self.assertEqual(source_path("chunker"), SCRIPTS / "chunker.py")
        self.assertEqual(source_path("VERSION"), SCRIPTS / "VERSION")
        self.assertEqual(source_path("benchmarks/model_swap_code_queries.json"),
                         SCRIPTS / "benchmarks" / "model_swap_code_queries.json")
        files = framework_source_files()
        self.assertIn(PACKAGE_DIR / "server_impl.py", files)
        self.assertNotIn(SCRIPTS / "server_impl.py", files)
        self.assertIn(SCRIPTS / "server_impl.py", framework_source_files(include_aliases=True))


class PackagePathDisciplineTests(unittest.TestCase):
    """Moved as-is, a lookup beside ``__file__`` resolves inside the package."""

    def test_only_the_scripts_root_and_the_carve_out_read_file_locations(self):
        for path in sorted(PACKAGE_DIR.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            with self.subTest(module=path.name):
                owners = [ast.unparse(n.value) for n in ast.walk(tree)
                          if isinstance(n, ast.Attribute) and n.attr == "__file__" and isinstance(n.value, ast.Name)]
                self.assertNotIn("server_impl", owners, "use server_impl.SCRIPTS_DIR, not server_impl.__file__")
                allowed = []
                if path.name == "server_impl.py":
                    for node in tree.body:
                        if isinstance(node, ast.Assign) and any(
                                isinstance(t, ast.Name) and t.id == "SCRIPTS_DIR" for t in node.targets):
                            allowed.append(node)
                        if isinstance(node, ast.FunctionDef) and node.name == "_audit_harness_coherence":
                            allowed.append(node)
                    self.assertEqual(len(allowed), 2)
                inside = {id(n) for a in allowed for n in ast.walk(a)}
                stray = [n.lineno for n in ast.walk(tree)
                         if isinstance(n, ast.Name) and n.id == "__file__" and id(n) not in inside]
                self.assertEqual(stray, [], "resolve retained scripts through SCRIPTS_DIR")


class FlatAliasIntegrityTests(unittest.TestCase):
    def _scratch_import(self, mutate) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            scratch = Path(tmp) / "scripts copy"
            import shutil
            shutil.copytree(SCRIPTS, scratch, ignore=shutil.ignore_patterns("tests", "__pycache__", "index"))
            mutate(scratch)
            return subprocess.run(
                [sys.executable, "-B", "-c", "import sys; sys.path.insert(0, sys.argv[1]); import server_impl",
                 str(scratch)], capture_output=True, text=True, timeout=180)

    def test_a_restored_full_flat_copy_is_refused_loudly(self):
        # A fork merge that kept a full pre-package flat file would run a second
        # implementation beside the package and break in-place reload.
        result = self._scratch_import(lambda d: (d / "graph_handlers.py").write_text(
            "def wf_graph_report_response(*a, **k):\n    return {}\n", encoding="utf-8"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("graph_handlers.py is not the three-line alias to wf_server.graph_handlers", result.stderr)

    def test_crlf_checkouts_of_the_alias_are_accepted(self):
        def to_crlf(d):
            path = d / "server_impl.py"
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        result = self._scratch_import(to_crlf)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])

    def test_extension_declarations_cannot_take_a_package_module_name(self):
        import mcp_tool_extensions
        server = load_server()
        self.assertTrue(set(server._FLAT_ALIASES) | {"wf_server"} <= mcp_tool_extensions.RESERVED_MODULE_NAMES)
        from unittest.mock import patch
        with patch.object(mcp_tool_extensions, "EXTENSION_MODULES", ("graph_handlers",)):
            problems = mcp_tool_extensions.declaration_problems(core_tools=(), runner_tools=())
        self.assertTrue(any("graph_handlers" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()

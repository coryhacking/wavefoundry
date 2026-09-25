"""Waves 1yzd0 and 1yxyw: the ``wf_server`` package boundary.

Twelve server-owned modules live in ``scripts/wf_server/``. ``server_impl`` and
``dashboard_handlers`` keep a flat file whose whole body replaces itself in
``sys.modules`` with the package module, because installed 1.25/1.26 upgrade
runners resolve the upgrade-mandatory modules' imports against flat stems. The
other ten are reached only as ``wf_server.<name>``. These tests pin the layout,
the two aliases, module identity, the retired-name warning, scripts-root
resolution, the upgrade constraint older runners impose, and the censuses that
keep code from reading an alias as the implementation or naming a retired
module by its flat name.
"""
from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import re
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
RETAINED = frozenset({"server_impl", "dashboard_handlers"})
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
        for name in sorted(RETAINED):
            with self.subTest(module=name):
                self.assertEqual((SCRIPTS / f"{name}.py").read_bytes(), ALIAS_BODY.format(name=name).encode())
        for name in sorted(MOVED - RETAINED):
            with self.subTest(retired=name):
                self.assertFalse((SCRIPTS / f"{name}.py").exists(), "wave 1yxyw retired this flat alias")

    def test_alias_and_evaluator_tables_match_the_inventory(self):
        import mcp_tool_extensions
        import retrieval_eval
        import upgrade_extensions
        server = load_server()
        self.assertEqual(server._FLAT_ALIASES, {name: f"wf_server.{name}" for name in RETAINED})
        self.assertEqual(server._RETIRED_FLAT_NAMES, MOVED - RETAINED)
        self.assertEqual(set(upgrade_extensions.RETIRED_FLAT_SERVER_MODULES), server._RETIRED_FLAT_NAMES)
        self.assertEqual(len(upgrade_extensions.RETIRED_FLAT_SERVER_MODULES), len(server._RETIRED_FLAT_NAMES))
        self.assertTrue(server._RETIRED_FLAT_NAMES.isdisjoint(server._FLAT_ALIASES))
        self.assertEqual(mcp_tool_extensions.RESERVED_MODULE_NAMES
                         & (set(server._FLAT_ALIASES) | server._RETIRED_FLAT_NAMES | {"wf_server"}),
                         set(server._FLAT_ALIASES) | server._RETIRED_FLAT_NAMES | {"wf_server"})
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
            "import wf_server.memory_handlers\n"
            "import server_impl\n"
            f"names = {sorted(RETAINED)!r}\n"
            f"retired = {sorted(MOVED - RETAINED)!r}\n"
            # Registered by server_impl itself, before any other flat import.
            "eager = {n: sys.modules.get(n) is sys.modules.get('wf_server.' + n) is not None for n in names}\n"
            "def flat_import_fails(n):\n"
            "    try:\n"
            "        __import__(n)\n"
            "    except ModuleNotFoundError:\n"
            "        return True\n"
            "    return False\n"
            "print(json.dumps({\n"
            "    'eager': eager,\n"
            "    'same': {n: __import__(n) is sys.modules['wf_server.' + n] for n in names},\n"
            "    'retired_absent': {n: n not in sys.modules and flat_import_fails(n) for n in retired},\n"
            "    'module_names': sorted({sys.modules[n].__name__ for n in names}),\n"
            "    'package_dir_on_path': any(p.rstrip('/\\\\').endswith('wf_server') for p in sys.path),\n"
            "    'scripts_dir': str(server_impl.SCRIPTS_DIR),\n"
            "}))\n"
        )
        self.assertEqual(observed["eager"], {name: True for name in RETAINED})
        self.assertEqual(observed["same"], {name: True for name in RETAINED})
        self.assertEqual(observed["retired_absent"], {name: True for name in MOVED - RETAINED})
        self.assertEqual(observed["module_names"], sorted("wf_server." + name for name in RETAINED))
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
            "    'handler_alias_registered': 'dashboard_handlers' in sys.modules,\n"
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
        import wf_server.upgrade_handlers as upgrade_handlers
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


# Wave 1yxyw: the ten moved modules whose flat aliases are retired. Only
# ``server_impl`` and ``dashboard_handlers`` keep a flat name, because installed
# 1.25/1.26 upgrade runners resolve the mandatory modules' imports against flat
# stems.
RETIRED = MOVED - {"server_impl", "dashboard_handlers"}
# Evicted by the reload purge; ``from wf_server import <name>`` reads the stale
# attribute the never-evicted parent package keeps, so it is refused outside
# the package. ``server_impl`` is never evicted.
_EVICTED = MOVED - {"server_impl"}
_RETIRED_TOKEN = re.compile(
    r"(?<![\w./])(?<!\bas )(?:" + "|".join(sorted(RETIRED)) + r")(?!\w)(?!\.py\b)")
# Assignments and test functions that must name the retired modules by their
# flat names: the reserved extension names, the upgrade hook's own copy
# (upgrade-mandatory modules cannot import wf_server), the evaluator's logical
# keys, and the tests that pin the reload purge of the retired flat keys.
_RETIRED_NAME_TABLES = {
    "mcp_tool_extensions.py": {"RESERVED_MODULE_NAMES"},
    "upgrade_extensions.py": {"RETIRED_FLAT_SERVER_MODULES"},
    "retrieval_eval.py": {"SERVER_PACKAGE_MODULES"},
    "tests/test_mcp_tool_registry.py": {"test_registry_module_is_in_purge_set_and_imported_at_module_top"},
    "tests/test_lifecycle_gates_structure.py": {"test_reload_picks_up_every_added_module",
                                                "test_reload_purge_covers_direct_sibling_imports"},
}
# The census's own home pins those tables and holds the known-bad controls.
_RETIRED_CENSUS_EXEMPT = {"test_server_package.py"}


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (isinstance(body, list) and body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str)):
            ids.add(id(body[0].value))
    return ids


def _retired_flat_name_sites(source: str, tables: set[str] = frozenset()) -> list[str]:
    """Sites outside ``wf_server/`` that name a retired module by its flat name.

    The predicate (change 1yxwn-ref): an import statement, or a string constant
    (an ``import_module``/``__import__`` argument, ``sys.modules`` key,
    ``patch`` target, or code embedded in a subprocess script) whose module
    token is a retired name or starts with ``<name>.``; plus ``from wf_server
    import <evicted module>``. File names (``<name>.py``) and docstrings are not
    module tokens. Assignments and functions named in ``tables`` are allowlisted.
    """
    tree = ast.parse(source)
    skipped = _docstring_ids(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id in tables for t in targets):
                skipped |= {id(n) for n in ast.walk(node)}
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in tables:
            skipped |= {id(n) for n in ast.walk(node)}
    sites = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            sites += [f"{node.lineno}: import {a.name}" for a in node.names if a.name.split(".")[0] in RETIRED]
        elif isinstance(node, ast.ImportFrom) and not node.level:
            if (node.module or "").split(".")[0] in RETIRED:
                sites.append(f"{node.lineno}: from {node.module} import")
            elif node.module == "wf_server":
                sites += [f"{node.lineno}: from wf_server import {a.name}"
                          for a in node.names if a.name in _EVICTED]
        elif (isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skipped
                and _RETIRED_TOKEN.search(node.value)):
            sites.append(f"{node.lineno}: {node.value[:60]!r}")
    return sites


def _retired_census_sources():
    for path in sorted(SCRIPTS.rglob("*.py")):
        relative = path.relative_to(SCRIPTS)
        if relative.parts[0] in {"wf_server", "index"} or "__pycache__" in relative.parts:
            continue
        if path.name in _RETIRED_CENSUS_EXEMPT:
            continue
        yield relative.as_posix(), path.read_text(encoding="utf-8")


class RetiredFlatNameCensusTests(unittest.TestCase):
    def test_no_module_outside_the_package_uses_a_retired_flat_name(self):
        found = {}
        for relpath, source in _retired_census_sources():
            sites = _retired_flat_name_sites(source, _RETIRED_NAME_TABLES.get(relpath, set()))
            if sites:
                found[relpath] = sites
        self.assertEqual(found, {}, "name the retired modules as wf_server.<name>")

    def test_the_census_detects_every_form(self):
        for bad in ("import memory_handlers", "import graph_handlers as g",
                    "def f():\n    from index_handlers import _x",
                    "from wf_server import index_handlers", "from wf_server import dashboard_handlers",
                    "importlib.import_module('codenav_handlers')", "__import__('techdocs_handlers')",
                    "patch('index_handlers._resolve')", "sys.modules['mcp_tool_registry']",
                    "'graph_handlers' in sys.modules", "code = 'import docs_handlers\\n'",
                    "RESERVED_MODULE_NAMES = {'memory_handlers'}",
                    # The hook's allowlisted table does not cover the rest of its module.
                    "RETIRED_FLAT_SERVER_MODULES = ('memory_handlers',)\nimport upgrade_handlers"):
            with self.subTest(bad=bad):
                self.assertTrue(_retired_flat_name_sites(bad, {"RETIRED_FLAT_SERVER_MODULES"}))
        for good in ("import wf_server.memory_handlers as memory_handlers",
                     "from wf_server.index_handlers import _x", "from wf_server import server_impl",
                     "importlib.import_module('wf_server.codenav_handlers')",
                     "patch('wf_server.index_handlers._resolve')", "p = 'wf_server/graph_handlers.py'",
                     "source_path('graph_handlers.py')", "import server_impl, dashboard_handlers",
                     "def f():\n    '''Moved from index_handlers.'''",
                     "code = 'import wf_server.docs_handlers as docs_handlers\\n'",
                     "RETIRED_FLAT_SERVER_MODULES = ('memory_handlers',)"):
            with self.subTest(good=good):
                self.assertEqual(_retired_flat_name_sites(good, {"RETIRED_FLAT_SERVER_MODULES"}), [])
        # An allowlisted test function covers its own strings, never a sibling
        # function or an import statement inside it.
        pinned = "def test_pin():\n    keys = {'graph_handlers'}\n"
        self.assertEqual(_retired_flat_name_sites(pinned, {"test_pin"}), [])
        self.assertTrue(_retired_flat_name_sites(pinned + "def other():\n    patch('index_handlers._x')\n",
                                                 {"test_pin"}))
        self.assertTrue(_retired_flat_name_sites("def test_pin():\n    import graph_handlers\n", {"test_pin"}))


class SwallowedImportTests(unittest.TestCase):
    def test_turn_end_projection_hook_reaches_the_package_module(self):
        # project_context_efficiency swallows every exception (a turn-end hook
        # must never fail the host), so a broken import would pass silently.
        # The recorded call proves the import resolved.
        from unittest.mock import patch
        import project_context_efficiency
        import wf_server.context_efficiency_handlers as handlers
        with tempfile.TemporaryDirectory() as tmp, patch.object(
                handlers, "project_pending_context_efficiency_root") as projected:
            self.assertEqual(project_context_efficiency.main(["--root", tmp]), 0)
        projected.assert_called_once_with(Path(tmp).resolve(), automatic=True)


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
        # A fork merge that kept a full pre-package copy of a RETAINED flat file
        # would run a second implementation beside the package and break reload.
        result = self._scratch_import(lambda d: (d / "dashboard_handlers.py").write_text(
            "def wf_start_dashboard_response(*a, **k):\n    return {}\n", encoding="utf-8"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dashboard_handlers.py is not the three-line alias to wf_server.dashboard_handlers",
                      result.stderr)

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


_LEFTOVER_DRIVER = r'''
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tests"))
from server_tools_support import _make_repo, load_server, load_thin_runner
with tempfile.TemporaryDirectory() as tmp:
    root = _make_repo(Path(tmp))
    load_server()
    runner = load_thin_runner()
    runner.build_server(root)
    try:
        impl = runner.server_impl
        info = impl.wf_server_info_response(root)
        codes = [d["code"] for d in info["diagnostics"]]
        messages = [d["message"] for d in info["diagnostics"] if d["code"] == "retired_flat_module_leftover"]
        stale = None
        if "graph_handlers" in sys.argv[1:]:
            import graph_handlers  # an unmigrated extension's flat import
            stale = graph_handlers is not sys.modules["wf_server.graph_handlers"]
        print(json.dumps({"status": info["status"], "codes": codes, "messages": messages,
                          "leftovers": impl.retired_flat_leftovers(), "stale_binding": stale}))
    finally:
        runner._get_handler().close()
'''


class RetiredFlatLeftoverWarningTests(unittest.TestCase):
    """Wave 1yxyw: the upgrade's MANIFEST-diff prune deletes the retired flat
    files; one that remains is reported by the server, never refused."""

    def _serve(self, *leftovers: str) -> tuple[dict, str]:
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            scratch = Path(tmp) / "scripts copy"
            shutil.copytree(SCRIPTS, scratch, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "index"))
            for name in leftovers:
                # A full flat implementation copy, as an unproven prune leaves it.
                shutil.copy2(PACKAGE_DIR / f"{name}.py", scratch / f"{name}.py")
            result = subprocess.run(
                [sys.executable, "-B", "-c", _LEFTOVER_DRIVER, *leftovers], cwd=scratch,
                env={**__import__("os").environ, "PYTHONPATH": str(scratch), "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True, text=True, timeout=300)
            self.assertEqual(result.returncode, 0, result.stderr[-4000:])
            return json.loads(result.stdout.strip().splitlines()[-1]), result.stderr

    def test_a_leftover_is_warned_in_server_info_and_stderr_and_the_server_serves(self):
        observed, stderr = self._serve("graph_handlers", "memory_handlers")
        self.assertEqual(observed["status"], "ok")
        self.assertEqual(observed["leftovers"], ["graph_handlers.py", "memory_handlers.py"])
        self.assertEqual(observed["codes"].count("retired_flat_module_leftover"), 1)
        for text in (observed["messages"][0], stderr):
            with self.subTest(channel="info" if text is not stderr else "stderr"):
                self.assertIn("graph_handlers.py, memory_handlers.py", text)
                self.assertIn("Delete them", text)
        # The stated consequence: an unmigrated flat import binds to the stale copy.
        self.assertTrue(observed["stale_binding"])

    def test_no_leftover_means_no_warning(self):
        observed, stderr = self._serve()
        self.assertEqual(observed["leftovers"], [])
        self.assertNotIn("retired_flat_module_leftover", observed["codes"])
        self.assertNotIn("retired flat server module", stderr)

    def test_the_upgrade_hook_reports_and_never_raises_or_deletes(self):
        import contextlib
        import io
        import types
        import upgrade_extensions
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scripts = root / ".wavefoundry" / "framework" / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "index_handlers.py").write_text("# leftover\n", encoding="utf-8")
            (scripts / "dashboard_handlers.py").write_text("# retained\n", encoding="utf-8")
            ctx = types.SimpleNamespace(root=root)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                upgrade_extensions.post_pruning(ctx)
            self.assertIn("index_handlers.py", out.getvalue())
            self.assertNotIn("dashboard_handlers.py", out.getvalue())
            self.assertIn("Delete them", out.getvalue())
            self.assertTrue((scripts / "index_handlers.py").is_file(), "the hook never deletes")
            (scripts / "index_handlers.py").unlink()
            quiet = io.StringIO()
            with contextlib.redirect_stdout(quiet):
                upgrade_extensions.post_pruning(ctx)
            self.assertEqual(quiet.getvalue(), "")
            # An unreadable scripts directory is logged, never raised.
            from unittest.mock import patch
            broken = io.StringIO()
            with patch.object(Path, "is_file", side_effect=PermissionError("denied")), \
                    contextlib.redirect_stdout(broken):
                try:
                    upgrade_extensions.post_pruning(ctx)
                except Exception as exc:  # an old runner turns this into exit 3
                    self.fail(f"post_pruning raised {type(exc).__name__}: {exc}")
            self.assertIn("could not check", broken.getvalue())


if __name__ == "__main__":
    unittest.main()

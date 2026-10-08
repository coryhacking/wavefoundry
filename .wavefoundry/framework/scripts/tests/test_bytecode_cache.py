"""Project-local bytecode cache (wave 200xy, change 1zyv1).

AC-1: entry processes over a scratch install cache imported framework modules under
``<root>/.wavefoundry/cache/pycache`` and create no ``__pycache__`` under the
framework directory. AC-2: a rendered hook body does the same. AC-3: a census derived
from the tree pins the entry and library forms. AC-4: the opt-out, the layout rule and
the linked-cache refusal. AC-5: the version flush. AC-6, AC-17: the test runner's
prefix, warm-up and child rules. AC-7: the close-gate borrow. AC-8: exclusions.
AC-12: no exported prefix. AC-13: the server reload writes no bytecode. AC-16: the
upgrade runner members run without ``bytecode_cache``.

Subprocess children run with ``PYTHONDONTWRITEBYTECODE`` and any inherited
``PYTHONPYCACHEPREFIX`` removed, so a child started by a test worker never writes
into the real project cache before its own configuration runs.
"""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import types
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import bytecode_cache  # noqa: E402

POSIX_ONLY = unittest.skipIf(os.name == "nt", "symlink fixtures need POSIX symlink rights")
_PREFIX_ENV = "PYTHONPYCACHEPREFIX"


def _child_env(**extra: str) -> dict:
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONDONTWRITEBYTECODE", _PREFIX_ENV)}
    env["WAVEFOUNDRY_SUPPRESS_DASHBOARD_BROWSER"] = "1"
    env["PYTHONUTF8"] = "1"
    env.update(extra)
    return env


def _ignore_copy(directory: str, names: list[str]) -> set[str]:
    rel = Path(directory).resolve().relative_to(SCRIPTS.resolve())
    skipped = {"__pycache__"}
    if not rel.parts:
        skipped |= {"tests", "benchmarks"}
    return {name for name in names if name in skipped or name.endswith(".pyc")}


def _scratch_install(root: Path, version: str = "9.9.9+test\n") -> Path:
    """A scratch install laid out as ``<root>/.wavefoundry/framework/scripts``."""
    scripts = root / ".wavefoundry" / "framework" / "scripts"
    shutil.copytree(SCRIPTS, scripts, ignore=_ignore_copy)
    (scripts.parent / "VERSION").write_text(version, encoding="utf-8")
    (root / "docs").mkdir(exist_ok=True)
    return scripts


def _pycache_dirs(base: Path) -> list[Path]:
    return sorted(p for p in base.rglob("__pycache__"))


def _mirror(prefix: Path, directory: Path) -> Path:
    return bytecode_cache.mirror_dir(prefix, directory)


def _cached_module_names(prefix: Path, scripts: Path) -> set[str]:
    mirror = _mirror(prefix, scripts)
    if not mirror.is_dir():
        return set()
    return {p.name.split(".")[0] for p in mirror.glob("*.pyc")}


def _run(argv: list[str], *, cwd: Path, env: dict | None = None, timeout: float = 240) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=str(cwd), env=env or _child_env(), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout,
                          stdin=subprocess.DEVNULL)


class _ScratchCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.scripts = _scratch_install(self.root)
        self.cache_root = self.root / ".wavefoundry" / "cache"
        self.prefix = self.cache_root / "pycache"

    def assert_no_in_tree_bytecode(self):
        self.assertEqual(_pycache_dirs(self.root / ".wavefoundry" / "framework"), [])


# ---------------------------------------------------------------------------
# AC-1, AC-2: entry processes and a rendered hook cache under the prefix only
# ---------------------------------------------------------------------------


class EntryProcessCacheTests(_ScratchCase):
    def _assert_cached(self, *modules: str):
        cached = _cached_module_names(self.prefix, self.scripts)
        for name in modules:
            self.assertIn(name, cached, sorted(cached))
        self.assert_no_in_tree_bytecode()
        self.assertEqual((self.prefix / bytecode_cache.STAMP_NAME).read_text(encoding="utf-8"), "9.9.9+test\n")

    def test_docs_lint_caches_under_the_prefix(self):
        _run([sys.executable, str(self.scripts / "docs_lint.py")], cwd=self.root)
        self._assert_cached("venv_bootstrap", "cli_stdio")

    def test_wf_cli_docs_lint_caches_under_the_prefix(self):
        _run([sys.executable, str(self.scripts / "wf_cli.py"), "docs-lint"], cwd=self.root)
        self._assert_cached("venv_bootstrap", "cli_stdio", "runtime_advisory")

    def test_server_dry_run_caches_under_the_prefix(self):
        _run([sys.executable, str(self.scripts / "server.py"), "--dry-run", "--root", str(self.root)], cwd=self.root)
        self._assert_cached("repo_root", "setup_readiness")

    def test_framework_c_children_cache_under_the_prefix(self):
        # The production -c programs, run from the scratch install: the CoreML probe
        # prelude (cwd = scripts) and the upgrade graph-builder probe.
        def constant(module: str, name: str) -> str:
            tree = ast.parse((self.scripts / module).read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == name:
                    return ast.literal_eval(node.value)
            raise AssertionError(f"{module} has no {name}")
        prelude = constant("accel_embedder.py", "_COREML_STATIC_PROBE_PRELUDE")
        done = _run([sys.executable, "-c", prelude + "import accel_embedder\n"], cwd=self.scripts)
        self.assertEqual(done.returncode, 0, done.stderr)
        probe = constant("upgrade_wavefoundry.py", "_GRAPH_BUILDER_PROBE")
        done = _run([sys.executable, "-c", probe, str(self.scripts), str(self.root)], cwd=self.root)
        self.assertEqual(done.returncode, 0, done.stderr)
        self._assert_cached("venv_bootstrap", "accel_embedder", "graph_indexer")


class HookBootstrapCacheTests(_ScratchCase):
    def test_a_rendered_hook_caches_venv_bootstrap_and_writes_nothing_beside_sources(self):
        import render_platform_surfaces as rps

        hooks = self.root / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        body = hooks / "probe-hook.py"
        body.write_text(rps.compose_script("print('hook ran')"), encoding="utf-8")
        done = _run([sys.executable, str(body)], cwd=self.root)
        self.assertIn("hook ran", done.stdout, done.stderr)
        self.assertEqual(_pycache_dirs(self.scripts), [])
        self.assertIn("venv_bootstrap", _cached_module_names(self.prefix, self.scripts))

    def test_the_bootstrap_sets_the_flag_before_importing_bytecode_cache(self):
        import render_platform_surfaces as rps

        text = rps.HOOK_BOOTSTRAP
        flag = text.index("_wf_sys.dont_write_bytecode = True")
        self.assertLess(flag, text.index("import bytecode_cache"))
        self.assertLess(text.index("_wf_bytecode_cache.configure()"), text.index("import venv_bootstrap"))


# ---------------------------------------------------------------------------
# AC-3: census derived from the tree
# ---------------------------------------------------------------------------

# Members of the release upgrade zipapp and the standalone bridge copy: they set
# the flag before their imports and never import bytecode_cache unguarded.
UPGRADE_RUNNER_MEMBERS = frozenset({"upgrade_bundle.py", "upgrade_bridge_bootstrap.py"})
# The test runner keeps its import-time flag and configures in main() only
# (the close gate borrows it in-process).
RUNNER = "run_tests.py"
# Entries whose source bytes are pinned elsewhere, each with the reason. Only
# these stay unconverted; their documented invocation passes ``-B``.
PINNED_SOURCE_ENTRIES = {
    "graph_quality_eval.py": (
        "its own source digest is the evaluator identity recorded in the shipped "
        "graph-quality report pair (tests/test_graph_quality_eval.py); the documented "
        "command runs it with python -B"
    ),
}


def _is_flag_assign(node: ast.AST) -> bool:
    return (isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Attribute)
            and node.targets[0].attr == "dont_write_bytecode"
            and isinstance(node.targets[0].value, ast.Name) and node.targets[0].value.id == "sys"
            and isinstance(node.value, ast.Constant) and node.value.value is True)


def _test_names(test: ast.AST) -> str:
    return ast.unparse(test)


def _module_flag_sites(tree: ast.Module) -> "list[tuple[int, str | None]]":
    """Module-scope flag assignments: (line, guarding if-test text or None)."""
    sites: list[tuple[int, str | None]] = []
    for node in tree.body:
        if _is_flag_assign(node):
            sites.append((node.lineno, None))
        elif isinstance(node, ast.If):
            for child in node.body:
                if _is_flag_assign(child):
                    sites.append((child.lineno, _test_names(node.test)))
    return sites


def _bytecode_cache_imports(tree: ast.Module) -> "list[tuple[int, bool]]":
    """Every ``import bytecode_cache``: (line, inside a try that catches ImportError)."""
    found: list[tuple[int, bool]] = []
    guarded_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and any(
            h.type is not None and "ImportError" in ast.unparse(h.type) for h in node.handlers
        ):
            for inner in node.body:
                for sub in ast.walk(inner):
                    guarded_lines.add(getattr(sub, "lineno", -1))
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        if "bytecode_cache" in names:
            found.append((node.lineno, node.lineno in guarded_lines))
    return found


def _calls_configure(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "configure" and ast.unparse(node.func.value).endswith("bytecode_cache")):
            return True
    return False


def _has_main_block(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.If) and "__name__" in ast.unparse(node.test) and "__main__" in ast.unparse(node.test):
            return True
    return False


def _argv_named_scripts(tree: ast.Module) -> set[str]:
    """Script basenames named directly in an interpreter-led argv list."""
    named: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.List) and node.elts:
            head = ast.unparse(node.elts[0])
            if "executable" not in head and "python" not in head.lower():
                continue
            for element in node.elts[1:3]:
                for sub in ast.walk(element):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value.endswith(".py"):
                        named.add(Path(sub.value).name)
    return named


# ``-c`` programs. A ``python -c`` child is an entry with no file of its own, so the
# census reads the program text: when it imports a framework module (or imports
# dynamically through ``importlib.import_module``) it must run with ``-B`` or set
# ``sys.dont_write_bytecode = True`` before that first import, and a program that
# imports ``bytecode_cache`` must call ``configure()``. A ``-m`` launch must name a
# framework module that is itself an entry.
#
# Limits (documented, not checked): a program text the census cannot resolve to
# string constants (a Name bound outside the file, a call result) is reported, so it
# fails closed; an argv whose script path is a variable (``[sys.executable,
# str(path)]``) is not followed, so such a script is covered only when it is also an
# entry by its own ``__main__`` block (every framework script launched that way is);
# argv lists assembled incrementally (``cmd.append("-c")``) are not seen.
_FLAG_RE = re.compile(r"sys\.dont_write_bytecode\s*=\s*True")
_IMPORT_RE = re.compile(r"^[ \t]*(?:import[ \t]+([\w., \t]+)|from[ \t]+([\w.]+)[ \t]+import)", re.M)


def _framework_module_names(scripts_root: Path) -> set[str]:
    names = {p.stem for p in scripts_root.glob("*.py")}
    names |= {p.parent.name for p in scripts_root.glob("*/__init__.py")}
    return names - {"tests", "__future__"}


def _interpreter_argv(node: ast.AST) -> bool:
    if not isinstance(node, (ast.List, ast.Tuple)) or len(node.elts) < 2:
        return False
    head = node.elts[0]
    if isinstance(head, ast.Constant):
        return isinstance(head.value, str) and "python" in head.value.lower()
    return not isinstance(head, ast.Starred)


def _resolve_text(node: ast.AST, scopes: "list[ast.AST]") -> "str | None":
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _resolve_text(node.left, scopes), _resolve_text(node.right, scopes)
        return None if left is None or right is None else left + right
    if isinstance(node, ast.Name):
        for scope in scopes:  # innermost function first, then the module
            for sub in ast.walk(scope):
                if (isinstance(sub, ast.Assign) and len(sub.targets) == 1
                        and isinstance(sub.targets[0], ast.Name) and sub.targets[0].id == node.id):
                    text = _resolve_text(sub.value, scopes[-1:])
                    if text is not None:
                        return text
    return None


def _first_framework_import(program: str, framework: set[str]) -> "int | None":
    positions = []
    for match in _IMPORT_RE.finditer(program):
        targets = match.group(1) or match.group(2) or ""
        for target in targets.split(","):
            words = target.strip().split()
            if words and words[0].split(".")[0] in framework:
                positions.append(match.start())
    dynamic = program.find("import_module(")
    if dynamic >= 0:
        positions.append(dynamic)
    return min(positions) if positions else None


def c_program_sites(rel: str, tree: ast.Module, framework: set[str],
                    entries: set[str]) -> "tuple[list[str], list[str]]":
    """(problems, descriptions) for every interpreter ``-c`` and ``-m`` launch in ``tree``."""
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    problems: list[str] = []
    sites: list[str] = []
    for node in ast.walk(tree):
        if not _interpreter_argv(node):
            continue
        consts = [e.value if isinstance(e, ast.Constant) else None for e in node.elts]
        if "-m" in consts:
            index = consts.index("-m")
            module = consts[index + 1] if index + 1 < len(consts) else None
            if isinstance(module, str) and module.split(".")[0] in framework:
                if not any(Path(e).stem == module.split(".")[0] for e in entries):
                    problems.append(f"{rel}:{node.lineno}: -m {module} is not a framework entry")
        if "-c" not in consts:
            continue
        index = consts.index("-c")
        if index + 1 >= len(node.elts):
            continue
        scopes: list[ast.AST] = []
        cursor = parents.get(node)
        while cursor is not None:
            if isinstance(cursor, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scopes.append(cursor)
            cursor = parents.get(cursor)
        scopes.append(tree)
        program = _resolve_text(node.elts[index + 1], scopes)
        minus_b = "-B" in consts
        if program is None:
            sites.append(f"{rel}:{node.lineno}: unresolved{' -B' if minus_b else ''}")
            if not minus_b:
                problems.append(f"{rel}:{node.lineno}: -c program text is unresolved and the argv has no -B")
            continue
        program = program.replace(";", "\n")  # one statement per line, same offsets
        first = _first_framework_import(program, framework)
        flag = _FLAG_RE.search(program)
        guard = "-B" if minus_b else ("flag" if flag and first is not None and flag.start() < first else "none")
        sites.append(f"{rel}:{node.lineno}: {'framework' if first is not None else 'stdlib'} import, guard {guard}")
        if first is not None and guard == "none":
            problems.append(f"{rel}:{node.lineno}: -c program imports a framework module with no -B "
                            "and no bytecode flag before that import")
        if "bytecode_cache" in program and "configure(" not in program:
            problems.append(f"{rel}:{node.lineno}: -c program imports bytecode_cache but never calls configure()")
    return problems, sites


def census_problems(scripts_root: Path) -> "tuple[list[str], set[str]]":
    """(problems, entry set) for every non-test script under ``scripts_root``."""
    files: dict[str, ast.Module] = {}
    for path in sorted(scripts_root.rglob("*.py")):
        rel = path.relative_to(scripts_root)
        if "tests" in rel.parts[:-1] or "__pycache__" in rel.parts:
            continue
        if rel.as_posix() == "bytecode_cache.py":
            continue
        files[rel.as_posix()] = ast.parse(path.read_text(encoding="utf-8"))
    named: set[str] = set()
    for tree in files.values():
        named |= _argv_named_scripts(tree)
    by_name: dict[str, list[str]] = {}
    for rel in files:
        by_name.setdefault(Path(rel).name, []).append(rel)
    entries = {rel for rel, tree in files.items() if _has_main_block(tree)}
    problems: list[str] = []
    for name in sorted(named):
        for rel in by_name.get(name, []):
            if rel not in entries:
                problems.append(f"{rel}: named in a framework argv but has no __main__ entry")
            entries.add(rel)
    for rel, tree in sorted(files.items()):
        sites = _module_flag_sites(tree)
        imports = _bytecode_cache_imports(tree)
        base = Path(rel).name
        if rel in PINNED_SOURCE_ENTRIES:
            if sites or imports:
                problems.append(f"{rel}: listed as pinned but now carries bytecode code; drop the exemption")
            continue
        if rel in entries:
            if base in UPGRADE_RUNNER_MEMBERS:
                if not any(test is None for _line, test in sites):
                    problems.append(f"{rel}: an upgrade runner member must set the flag unconditionally")
                first_import = min((n.lineno for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
                                    and not (isinstance(n, ast.ImportFrom) and n.module == "__future__")
                                    and not (isinstance(n, ast.Import) and [a.name for a in n.names] == ["sys"])),
                                   default=10**9)
                if sites and min(line for line, _t in sites) > first_import:
                    problems.append(f"{rel}: the flag must come before the member's imports")
                if any(not guarded for _line, guarded in imports):
                    problems.append(f"{rel}: imports bytecode_cache without an ImportError guard")
                continue
            if not sites:
                problems.append(f"{rel}: entry sets no bytecode flag before importing bytecode_cache")
                continue
            if not imports:
                problems.append(f"{rel}: entry never imports bytecode_cache")
                continue
            if min(line for line, _t in sites) > min(line for line, _g in imports):
                problems.append(f"{rel}: entry imports bytecode_cache before setting the flag")
            if not _calls_configure(tree):
                problems.append(f"{rel}: entry never calls bytecode_cache.configure()")
            for line, test in sites:
                if base == RUNNER and test is None:
                    continue
                if test is None or "__main__" not in test or "pycache_prefix" not in test:
                    problems.append(f"{rel}:{line}: entry flag is not the guarded entry form")
        else:
            for line, test in sites:
                if test is None or "pycache_prefix" not in test:
                    problems.append(f"{rel}:{line}: library flag without the no-prefix guard")
    framework = _framework_module_names(scripts_root)
    for rel, tree in sorted(files.items()):
        problems += c_program_sites(rel, tree, framework, entries)[0]
    return problems, entries


def c_program_census(scripts_root: Path) -> "list[str]":
    """One description per interpreter ``-c`` launch in the non-test scripts."""
    _problems, entries = census_problems(scripts_root)
    framework = _framework_module_names(scripts_root)
    sites: list[str] = []
    for path in sorted(scripts_root.rglob("*.py")):
        rel = path.relative_to(scripts_root)
        if "tests" in rel.parts[:-1] or "__pycache__" in rel.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        sites += c_program_sites(rel.as_posix(), tree, framework, entries)[1]
    return sites


class CallSiteCensusTests(unittest.TestCase):
    def test_every_entry_and_library_site_follows_the_rule(self):
        problems, entries = census_problems(SCRIPTS)
        self.assertEqual(problems, [])
        self.assertTrue(all(reason.strip() for reason in PINNED_SOURCE_ENTRIES.values()))
        self.assertTrue(set(PINNED_SOURCE_ENTRIES) <= entries)
        # The census predicate is derived, so pin that it still finds the known shape.
        for rel in ("docs_lint.py", "wf_cli.py", "server.py", "dashboard_server.py", RUNNER,
                    "wf_server/server_impl.py", "upgrade_bundle.py", "upgrade_bridge_bootstrap.py"):
            self.assertIn(rel, entries)
        self.assertGreaterEqual(len(entries), 44)

    def _fixture(self, files: dict[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            for rel, text in files.items():
                path = Path(tmp) / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(textwrap.dedent(text), encoding="utf-8")
            return census_problems(Path(tmp))[0]

    def test_a_bare_library_assignment_is_reported(self):
        problems = self._fixture({"lib.py": "import sys\nsys.dont_write_bytecode = True\n"})
        self.assertEqual(len(problems), 1)
        self.assertIn("lib.py:2: library flag without the no-prefix guard", problems[0])

    def test_a_main_script_without_configure_is_reported(self):
        problems = self._fixture({"tool.py": """\
            import sys
            if __name__ == "__main__" or sys.pycache_prefix is None:
                sys.dont_write_bytecode = True
            import bytecode_cache
            if __name__ == "__main__":
                print("no configure")
            """})
        self.assertEqual(problems, ["tool.py: entry never calls bytecode_cache.configure()"])

    def test_a_main_script_with_no_flag_is_reported(self):
        problems = self._fixture({"tool.py": 'if __name__ == "__main__":\n    pass\n'})
        self.assertEqual(problems, ["tool.py: entry sets no bytecode flag before importing bytecode_cache"])

    def test_an_import_before_the_flag_is_reported(self):
        problems = self._fixture({"tool.py": """\
            import sys
            import bytecode_cache
            if __name__ == "__main__" or sys.pycache_prefix is None:
                sys.dont_write_bytecode = True
            if __name__ == "__main__":
                bytecode_cache.configure()
            """})
        self.assertEqual(problems, ["tool.py: entry imports bytecode_cache before setting the flag"])

    def test_an_argv_named_script_without_a_main_entry_is_reported(self):
        problems = self._fixture({
            "spawner.py": "import sys\ncmd = [sys.executable, 'worker.py']\n",
            "worker.py": "x = 1\n",
        })
        self.assertIn("worker.py: named in a framework argv but has no __main__ entry", problems)

    def test_an_upgrade_member_importing_bytecode_cache_unguarded_is_reported(self):
        problems = self._fixture({"upgrade_bundle.py": """\
            import sys
            sys.dont_write_bytecode = True
            import bytecode_cache
            if __name__ == "__main__":
                pass
            """})
        self.assertEqual(problems, ["upgrade_bundle.py: imports bytecode_cache without an ImportError guard"])

    def test_every_c_program_that_imports_the_framework_is_guarded(self):
        sites = c_program_census(SCRIPTS)
        # The predicate is derived, so pin that it still sees the known launches.
        framework_sites = {s.split(":")[0] for s in sites if ": framework import" in s}
        self.assertTrue({"accel_embedder.py", "upgrade_wavefoundry.py", "setup_index.py",
                         "upgrade_protocol.py"} <= framework_sites, sites)
        self.assertFalse([s for s in sites if ": framework import, guard none" in s], sites)

    def test_an_unguarded_c_program_importing_the_framework_is_reported(self):
        problems = self._fixture({
            "spawner.py": "import sys\nCODE = 'import sys\\nimport helper\\n'\n"
                          "cmd = [sys.executable, '-c', CODE]\n",
            "helper.py": "x = 1\n",
        })
        self.assertEqual(problems, ["spawner.py:3: -c program imports a framework module with no -B "
                                    "and no bytecode flag before that import"])

    def test_a_flag_after_the_framework_import_is_reported(self):
        problems = self._fixture({
            "spawner.py": "import sys\n"
                          "def go(python):\n"
                          "    code = 'import helper; import sys; sys.dont_write_bytecode = True'\n"
                          "    return [python, '-c', code]\n",
            "helper.py": "x = 1\n",
        })
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("spawner.py:4: -c program imports a framework module", problems[0])

    def test_minus_b_or_a_leading_flag_satisfies_the_c_census(self):
        problems = self._fixture({
            "spawner.py": "import sys\n"
                          "A = [sys.executable, '-B', '-c', 'import helper']\n"
                          "B = [sys.executable, '-c', 'import sys\\nsys.dont_write_bytecode = True\\n"
                          "import bytecode_cache\\nbytecode_cache.configure()\\nimport helper']\n"
                          "C = [sys.executable, '-c', 'import json; print(1)']\n"
                          "D = ['git', '-c', 'user.name=x', 'commit']\n",
            "helper.py": "x = 1\n",
        })
        self.assertEqual(problems, [])

    def test_a_c_program_with_unresolved_text_and_no_minus_b_is_reported(self):
        problems = self._fixture({"spawner.py": "import sys\ncmd = [sys.executable, '-c', make()]\n"})
        self.assertEqual(problems, ["spawner.py:2: -c program text is unresolved and the argv has no -B"])

    def test_a_minus_m_launch_of_a_non_entry_framework_module_is_reported(self):
        problems = self._fixture({
            "spawner.py": "import sys\ncmd = [sys.executable, '-m', 'helper']\n",
            "helper.py": "x = 1\n",
        })
        self.assertEqual(problems, ["spawner.py:2: -m helper is not a framework entry"])


# ---------------------------------------------------------------------------
# AC-4: opt-out, layout rule, linked-cache refusal
# ---------------------------------------------------------------------------

_PROBE = """\
import json, sys
sys.path.insert(0, sys.argv[1])
sys.dont_write_bytecode = True
import bytecode_cache
result = bytecode_cache.configure()
out = {"result": result, "prefix": sys.pycache_prefix, "dont_write": sys.dont_write_bytecode,
       "env": __import__("os").environ.get("PYTHONPYCACHEPREFIX")}
if len(sys.argv) > 2:
    import probe_mod
    out["mark"] = probe_mod.MARK
print(json.dumps(out))
"""


def _probe(scripts: Path, *flags: str, env: dict | None = None, module: bool = False) -> dict:
    argv = [sys.executable, *flags, "-c", _PROBE, str(scripts)] + (["probe"] if module else [])
    done = _run(argv, cwd=scripts, env=env)
    if done.returncode != 0:
        raise AssertionError(done.stderr)
    return json.loads(done.stdout.strip().splitlines()[-1])


def _all_files(base: Path) -> set[str]:
    return {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file() or p.is_symlink()}


class OptOutAndRefusalTests(_ScratchCase):
    def test_writes_disabled_by_flag_or_environment_write_nothing(self):
        before = _all_files(self.root)
        for flags, env in ((("-B",), None), ((), _child_env(PYTHONDONTWRITEBYTECODE="1"))):
            _run([sys.executable, *flags, str(self.scripts / "docs_lint.py")], cwd=self.root, env=env)
            self.assertEqual(_all_files(self.root), before)
            self.assertFalse(self.cache_root.exists())

    def test_a_read_only_process_uses_the_derived_prefix_for_reads(self):
        state = _probe(self.scripts, "-B")
        self.assertEqual(state["prefix"], str(self.prefix))
        self.assertTrue(state["dont_write"])
        self.assertFalse(self.cache_root.exists())

    def test_a_scripts_directory_outside_the_layout_gets_no_prefix(self):
        other = self.root / "elsewhere" / "scripts"
        shutil.copytree(self.scripts, other)
        state = _probe(other)
        self.assertEqual((state["result"], state["prefix"], state["dont_write"]), (None, None, True))
        self.assertFalse((self.root / "elsewhere" / "cache").exists())
        self.assertEqual(_pycache_dirs(other), [])

    def _plant_behind(self, target_prefix: Path) -> None:
        """A source ``probe_mod`` and a valid ``.pyc`` of different code at its mirror."""
        source = self.scripts / "probe_mod.py"
        source.write_text('MARK = "real"\n', encoding="utf-8")
        planted_src = self.root / "planted" / "probe_mod.py"
        planted_src.parent.mkdir()
        planted_src.write_text('MARK = "PLNT"\n', encoding="utf-8")
        st = source.stat()
        os.utime(planted_src, ns=(st.st_atime_ns, st.st_mtime_ns))
        cfile = _mirror(target_prefix, self.scripts) / f"probe_mod.{sys.implementation.cache_tag}.pyc"
        cfile.parent.mkdir(parents=True, exist_ok=True)
        py_compile.compile(str(planted_src), cfile=str(cfile), doraise=True)

    def test_the_plant_is_executed_without_the_refusal(self):
        # The fixture is live: with a real (unlinked) cache directory, the planted
        # bytecode is what runs.
        self._plant_behind(self.prefix)
        state = _probe(self.scripts, "-B", module=True)
        self.assertEqual(state["mark"], "PLNT")

    @POSIX_ONLY
    def test_a_symlinked_cache_root_or_pycache_is_refused(self):
        for linked in ("root", "pycache"):
            with self.subTest(linked=linked):
                target = self.root / f"target-{linked}"
                target.mkdir()
                shutil.rmtree(self.cache_root, ignore_errors=True)
                if linked == "root":
                    self.cache_root.symlink_to(target, target_is_directory=True)
                else:
                    self.cache_root.mkdir()
                    self.prefix.symlink_to(target, target_is_directory=True)
                _run([sys.executable, str(self.scripts / "docs_lint.py")], cwd=self.root)
                self.assertEqual(list(target.rglob("*")), [])
                state = _probe(self.scripts)
                self.assertEqual((state["result"], state["prefix"], state["dont_write"]), (None, None, True))
                self.assert_no_in_tree_bytecode()
                if self.cache_root.is_symlink():
                    self.cache_root.unlink()
                else:
                    shutil.rmtree(self.cache_root)

    @POSIX_ONLY
    def test_a_read_only_process_reads_nothing_through_a_linked_cache(self):
        target = self.root / "target"
        target.mkdir()
        self.cache_root.mkdir()
        self.prefix.symlink_to(target, target_is_directory=True)
        self._plant_behind(self.prefix)  # written through the link, into the target
        env = _child_env(**{_PREFIX_ENV: str(self.prefix)})
        state = _probe(self.scripts, "-B", env=env, module=True)
        self.assertIsNone(state["prefix"])
        self.assertEqual(state["mark"], "real")

    def test_a_reparse_point_attribute_is_refused(self):
        real_lstat = os.lstat
        cache_root = self.cache_root

        def fake_lstat(path, *args, **kwargs):
            st = real_lstat(path, *args, **kwargs)
            if os.path.abspath(path) == str(cache_root):
                return types.SimpleNamespace(st_mode=st.st_mode, st_file_attributes=0x400)
            return st

        self.cache_root.mkdir()
        self.assertFalse(bytecode_cache.is_linked(self.cache_root))
        saved = (sys.pycache_prefix, sys.dont_write_bytecode)
        try:
            sys.pycache_prefix = str(self.prefix)
            with mock.patch.object(bytecode_cache.os, "lstat", side_effect=fake_lstat):
                self.assertTrue(bytecode_cache.is_linked(self.cache_root))
                result = bytecode_cache._configure(runner=True, read_only=False, scripts_dir=self.scripts)
                after = (sys.pycache_prefix, sys.dont_write_bytecode)
        finally:
            sys.pycache_prefix, sys.dont_write_bytecode = saved
        self.assertIsNone(result)
        self.assertEqual(after, (None, True))
        self.assertFalse(self.prefix.exists())


# ---------------------------------------------------------------------------
# AC-5: version flush
# ---------------------------------------------------------------------------


class VersionFlushTests(_ScratchCase):
    def _stale_source(self) -> None:
        source = self.scripts / "probe_mod.py"
        source.write_text('MARK = "old"\n', encoding="utf-8")
        self.assertEqual(_probe(self.scripts, module=True)["mark"], "old")
        st = source.stat()
        source.write_text('MARK = "new"\n', encoding="utf-8")
        os.utime(source, ns=(st.st_atime_ns, st.st_mtime_ns))

    def test_without_a_version_change_the_stale_bytecode_runs(self):
        self._stale_source()
        self.assertEqual(_probe(self.scripts, module=True)["mark"], "old")

    def test_a_version_change_flushes_and_restamps(self):
        self._stale_source()
        (self.scripts.parent / "VERSION").write_text("9.9.10+next\n", encoding="utf-8")
        self.assertEqual(_probe(self.scripts, module=True)["mark"], "new")
        self.assertEqual((self.prefix / bytecode_cache.STAMP_NAME).read_text(encoding="utf-8"), "9.9.10+next\n")
        self.assertEqual([p.name for p in self.cache_root.iterdir()], ["pycache"])

    @POSIX_ONLY
    def test_a_symlink_inside_the_cache_is_unlinked_and_its_target_kept(self):
        _probe(self.scripts)
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep", encoding="utf-8")
        (self.prefix / "Users").mkdir(exist_ok=True)
        (self.prefix / "Users" / "escape").symlink_to(outside, target_is_directory=True)
        (self.prefix / "escape-file").symlink_to(outside / "keep.txt")
        (self.scripts.parent / "VERSION").write_text("9.9.11\n", encoding="utf-8")
        _probe(self.scripts)
        self.assertEqual((outside / "keep.txt").read_text(encoding="utf-8"), "keep")
        self.assertFalse((self.prefix / "Users" / "escape").exists())
        self.assertFalse(os.path.lexists(self.prefix / "escape-file"))

    def test_a_failed_flush_rename_leaves_caching_off(self):
        _probe(self.scripts)
        (self.scripts.parent / "VERSION").write_text("9.9.12\n", encoding="utf-8")
        with mock.patch.object(bytecode_cache.os, "rename", side_effect=PermissionError("held")):
            ok = bytecode_cache._flush_if_stale(self.cache_root, self.prefix, self.scripts.parent / "VERSION")
        self.assertFalse(ok)


# ---------------------------------------------------------------------------
# AC-6, AC-17: the test runner
# ---------------------------------------------------------------------------


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_tests_bytecode_subject", SCRIPTS / "run_tests.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RunnerPrefixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rt = _load_runner()

    def setUp(self):
        self.saved = self.rt._BYTECODE_PREFIX
        self.addCleanup(setattr, self.rt, "_BYTECODE_PREFIX", self.saved)

    def _worker_call(self, prefix):
        self.rt._BYTECODE_PREFIX = prefix
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["cmd"], seen["env"] = cmd, kwargs["env"]
            return subprocess.CompletedProcess(cmd, 0, "", "Ran 1 test in 0.001s\n\nOK\n")

        with mock.patch.object(self.rt.subprocess, "run", side_effect=fake_run), \
                mock.patch.dict(os.environ, {_PREFIX_ENV: "/inherited/elsewhere"}):
            self.rt._run_file(Path("test_x.py"))
        return seen

    def test_workers_receive_the_active_prefix_and_stay_read_only(self):
        seen = self._worker_call("/repo/.wavefoundry/cache/pycache")
        self.assertEqual(seen["env"][_PREFIX_ENV], "/repo/.wavefoundry/cache/pycache")
        self.assertEqual(seen["env"]["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertIn("-B", seen["cmd"])

    def test_workers_get_no_prefix_when_none_is_active(self):
        seen = self._worker_call(None)
        self.assertNotIn(_PREFIX_ENV, seen["env"])
        self.assertIn("-B", seen["cmd"])

    def test_the_profile_child_receives_the_active_prefix(self):
        self.rt._BYTECODE_PREFIX = "/p"
        self.assertEqual(self.rt._child_runner_env({})[_PREFIX_ENV], "/p")
        self.rt._BYTECODE_PREFIX = None
        with mock.patch.dict(os.environ, {_PREFIX_ENV: "/inherited"}):
            self.assertNotIn(_PREFIX_ENV, self.rt._child_runner_env({}))

    def test_the_warm_up_is_routed_through_tree_kill_and_writes(self):
        calls = []

        def spy(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return subprocess.CompletedProcess(cmd, 0)

        with mock.patch.object(self.rt, "_run_tree_kill", side_effect=spy), \
                mock.patch.dict(os.environ, {"PYTHONDONTWRITEBYTECODE": "1", "PYTHON": sys.executable}), \
                contextlib.redirect_stdout(io.StringIO()):
            self.rt._warm_bytecode_cache("/p")
        self.assertTrue(calls)
        for cmd, kwargs in calls:
            self.assertNotIn("-B", cmd)
            self.assertNotIn("PYTHONDONTWRITEBYTECODE", kwargs["env"])
            self.assertEqual(kwargs["env"][_PREFIX_ENV], "/p")
            self.assertIn("timeout", kwargs)
            self.assertEqual(cmd[-2:], [str(self.rt._SCRIPT_DIR), "1"])

    def _main_with(self, configured):
        with mock.patch.object(self.rt, "_configure_bytecode_cache", return_value=configured), \
                mock.patch.object(self.rt, "_warm_bytecode_cache") as warm, \
                mock.patch.object(self.rt, "_remove_bytecode_temp_mirrors") as prune, \
                mock.patch.object(self.rt, "_main", return_value=0), \
                mock.patch.object(sys, "argv", ["run_tests.py"]):
            self.assertEqual(self.rt.main(), 0)
        return warm, prune

    def test_a_top_level_run_warms_and_prunes_the_temp_mirrors(self):
        warm, prune = self._main_with(("/p", True))
        warm.assert_called_once_with("/p")
        prune.assert_called_once_with("/p")

    def test_a_child_run_neither_warms_nor_prunes(self):
        warm, prune = self._main_with(("/p", False))
        warm.assert_not_called()
        prune.assert_not_called()

    def test_a_refused_cache_neither_warms_nor_passes_a_prefix(self):
        warm, prune = self._main_with((None, True))
        warm.assert_not_called()
        prune.assert_not_called()
        self.assertIsNone(self.rt._BYTECODE_PREFIX)

    def test_an_inherited_prefix_marks_a_child(self):
        with mock.patch.object(bytecode_cache, "configure", return_value="/inh") as configure, \
                mock.patch.dict(os.environ, {_PREFIX_ENV: "/inh"}):
            self.assertEqual(self.rt._configure_bytecode_cache(), ("/inh", False))
        configure.assert_called_once_with(read_only=True)
        env = {k: v for k, v in os.environ.items() if k != _PREFIX_ENV}
        with mock.patch.object(bytecode_cache, "configure", return_value="/top") as configure, \
                mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(self.rt._configure_bytecode_cache(), ("/top", True))
        configure.assert_called_once_with(runner=True)


class TempMirrorTests(unittest.TestCase):
    def test_both_temp_spellings_are_removed_and_links_are_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "pycache"
            given = tempfile.gettempdir()
            resolved = os.path.realpath(given)
            for spelling in {given, resolved}:
                mirror = bytecode_cache.mirror_dir(prefix, spelling)
                (mirror / "scratch").mkdir(parents=True, exist_ok=True)
                (mirror / "scratch" / "x.cpython-314.pyc").write_bytes(b"x")
            keep = prefix / "Users" / "kept.pyc"
            keep.parent.mkdir(parents=True, exist_ok=True)
            keep.write_bytes(b"k")
            bytecode_cache.remove_temp_mirrors(prefix)
            for spelling in {given, resolved}:
                self.assertFalse(bytecode_cache.mirror_dir(prefix, spelling).exists())
            self.assertTrue(keep.exists())

    @POSIX_ONLY
    def test_a_link_on_the_way_to_a_mirror_is_unlinked_not_descended(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "pycache"
            outside = Path(tmp) / "outside"
            (outside / "deep").mkdir(parents=True)
            (outside / "deep" / "keep.txt").write_text("keep", encoding="utf-8")
            first = bytecode_cache.mirror_dir(prefix, tempfile.gettempdir()).relative_to(prefix).parts[0]
            prefix.mkdir()
            (prefix / first).symlink_to(outside, target_is_directory=True)
            bytecode_cache.remove_temp_mirrors(prefix)
            self.assertFalse(os.path.lexists(prefix / first))
            self.assertEqual((outside / "deep" / "keep.txt").read_text(encoding="utf-8"), "keep")

    def test_a_mirror_never_leaves_the_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "pycache"
            prefix.mkdir()
            self.assertFalse(bytecode_cache.remove_mirror(prefix, os.sep))


_RUNNER_DRIVER = """\
import importlib.util, json, sys
scripts = sys.argv[1]
sys.path.insert(0, scripts)
spec = importlib.util.spec_from_file_location("run_tests", scripts + "/run_tests.py")
rt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rt)
rt._BYTECODE_WARM_INSTALLATION = False
rt._wait_for_index_build = lambda: None
rt._probe_index_build_lock = lambda: (False, None)
rt.repo_state_snapshot = lambda repo_root=None: {}
pruned = []
real_prune = rt._remove_bytecode_temp_mirrors
rt._remove_bytecode_temp_mirrors = lambda prefix: (pruned.append(prefix), real_prune(prefix))
sys.argv = ["run_tests.py", "--file", "test_probe.py"]
rc = rt.main()
print(json.dumps({"rc": rc, "prefix": rt._BYTECODE_PREFIX, "pruned": pruned}))
"""

_PROBE_TEST = """\
import importlib.util, json, os, pathlib, unittest
class T(unittest.TestCase):
    def test_env(self):
        here = pathlib.Path(__file__).resolve()
        lint = here.parent.parent / "docs_lint.py"
        cached = importlib.util.cache_from_source(str(lint))
        here.with_name("worker-env.json").write_text(json.dumps({
            "prefix": os.environ.get("PYTHONPYCACHEPREFIX", "<none>"),
            "warmed": os.path.exists(cached),
        }), encoding="utf-8")
"""


class RunnerTopLevelAndChildTests(_ScratchCase):
    def setUp(self):
        super().setUp()
        tests = self.scripts / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_probe.py").write_text(_PROBE_TEST, encoding="utf-8")

    def _drive(self, env: dict) -> dict:
        done = _run([sys.executable, "-B", "-c", _RUNNER_DRIVER, str(self.scripts)], cwd=self.scripts, env=env,
                    timeout=300)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return json.loads(done.stdout.strip().splitlines()[-1])

    def test_a_top_level_minus_b_run_flushes_warms_and_passes_the_prefix(self):
        self.prefix.mkdir(parents=True)
        (self.prefix / bytecode_cache.STAMP_NAME).write_text("old-version\n", encoding="utf-8")
        (self.prefix / "stale-marker").write_text("x", encoding="utf-8")
        result = self._drive(_child_env())
        self.assertEqual(result["prefix"], str(self.prefix))
        self.assertEqual(result["pruned"], [str(self.prefix)])
        self.assertFalse((self.prefix / "stale-marker").exists())
        self.assertEqual((self.prefix / bytecode_cache.STAMP_NAME).read_text(encoding="utf-8"), "9.9.9+test\n")
        # docs_lint is written by the warm-up (the runner never imports it); the
        # worker sees it before the run's temp-mirror cleanup removes this scratch
        # tree's mirror (the scratch install lives in the temporary directory).
        worker = json.loads((self.scripts / "tests" / "worker-env.json").read_text(encoding="utf-8"))
        self.assertEqual(worker, {"prefix": str(self.prefix), "warmed": True})
        self.assert_no_in_tree_bytecode()

    def test_a_runner_with_an_inherited_prefix_neither_flushes_nor_warms(self):
        parent = self.root / "parent-cache"
        parent.mkdir()
        self.prefix.mkdir(parents=True)
        (self.prefix / bytecode_cache.STAMP_NAME).write_text("old-version\n", encoding="utf-8")
        result = self._drive(_child_env(**{_PREFIX_ENV: str(parent), "PYTHONDONTWRITEBYTECODE": "1"}))
        self.assertEqual(result["prefix"], str(parent))
        self.assertEqual(result["pruned"], [])
        self.assertEqual((self.prefix / bytecode_cache.STAMP_NAME).read_text(encoding="utf-8"), "old-version\n")
        self.assertEqual(_cached_module_names(self.prefix, self.scripts), set())
        self.assertEqual(list(parent.rglob("*")), [])
        worker = json.loads((self.scripts / "tests" / "worker-env.json").read_text(encoding="utf-8"))
        self.assertEqual(worker, {"prefix": str(parent), "warmed": False})

    def test_a_child_creates_no_cache_in_its_own_tree(self):
        parent = self.root / "parent-cache"
        parent.mkdir()
        self._drive(_child_env(**{_PREFIX_ENV: str(parent), "PYTHONDONTWRITEBYTECODE": "1"}))
        self.assertFalse(self.cache_root.exists())


# ---------------------------------------------------------------------------
# AC-7: the close-gate borrow
# ---------------------------------------------------------------------------

_BORROW = """\
import json, os, sys
sys.path.insert(0, sys.argv[1])
sys.pycache_prefix = sys.argv[2]
sys.dont_write_bytecode = False
import lifecycle_gate_support as lgs
before = (sys.pycache_prefix, sys.dont_write_bytecode, os.environ.get("PYTHONPYCACHEPREFIX"))
module = lgs._load_framework_test_runner(__import__("pathlib").Path(sys.argv[1]) / "run_tests.py")
after = (sys.pycache_prefix, sys.dont_write_bytecode, os.environ.get("PYTHONPYCACHEPREFIX"))
print(json.dumps({"loaded": module is not None, "before": before, "after": after}))
"""


class CloseGateBorrowTests(unittest.TestCase):
    def test_borrowing_the_runner_changes_no_bytecode_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            done = _run([sys.executable, "-c", _BORROW, str(SCRIPTS), tmp], cwd=Path(tmp))
            self.assertEqual(done.returncode, 0, done.stderr)
            state = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertTrue(state["loaded"])
        self.assertEqual(state["before"], state["after"])
        self.assertEqual(state["after"][2], None)


# ---------------------------------------------------------------------------
# AC-8: exclusions
# ---------------------------------------------------------------------------


class CacheExclusionTests(unittest.TestCase):
    CACHE_FILES = (".wavefoundry/cache/pycache/Users/x/a.cpython-314.pyc",
                   ".wavefoundry/cache/pycache/framework-version.stamp",
                   ".wavefoundry/cache/pycache/Users/x/notes.md")

    def _root(self, tmp: str) -> Path:
        root = Path(tmp).resolve()
        (root / "docs").mkdir()
        (root / "docs" / "a.md").write_text("# A\n", encoding="utf-8")
        for rel in self.CACHE_FILES:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"x")
        return root

    @staticmethod
    def _cached(paths, root: Path) -> list[str]:
        rels = [Path(p).relative_to(root).as_posix() if Path(p).is_absolute() else str(p) for p in paths]
        return [rel for rel in rels if rel.startswith(".wavefoundry/cache")]

    def test_the_rendered_gitignore_block_ignores_the_cache(self):
        import render_platform_surfaces as rps
        self.assertIn(".wavefoundry/cache/", rps._GITIGNORE_BLOCK)

    def test_machine_authority_and_the_index_walk_skip_the_cache(self):
        import indexer
        import machine_authority
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            for rel in self.CACHE_FILES:
                self.assertTrue(machine_authority.is_machine_authority_path(rel, root), rel)
            self.assertEqual(self._cached(indexer.walk_repo(root), root), [])

    def test_the_secrets_file_set_skips_the_cache_with_and_without_git(self):
        import render_platform_surfaces as rps
        from wave_lint_lib import secrets_validators
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            self.assertEqual(self._cached(secrets_validators._get_all_files(root), root), [])
        if shutil.which("git") is None:
            self.skipTest("git unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            (root / ".gitignore").write_text("\n".join(rps._GITIGNORE_BLOCK) + "\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            files = secrets_validators._get_all_files(root)
            self.assertIn("docs/a.md", [Path(p).relative_to(root).as_posix() for p in files])
            self.assertEqual(self._cached(files, root), [])

    def test_the_reconcile_scan_skips_the_cache(self):
        import reconcile_scan
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            rels = [rel for _path, rel in reconcile_scan._iter_scannable_files(root)]
            self.assertIn("docs/a.md", rels)
            self.assertEqual([rel for rel in rels if rel.startswith(".wavefoundry/cache")], [])

    def test_the_pack_and_the_receipt_hash_never_see_the_cache(self):
        import build_pack
        rt = _load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            framework = root / ".wavefoundry" / "framework"
            (framework / "scripts").mkdir(parents=True)
            (framework / "scripts" / "tool.py").write_text("x = 1\n", encoding="utf-8")
            with mock.patch.object(rt, "_FRAMEWORK_DIR", framework):
                with_cache = rt._hash_inputs()
                shutil.rmtree(root / ".wavefoundry" / "cache")
                without_cache = rt._hash_inputs()
            self.assertEqual(with_cache, without_cache)
            arcnames = [arc for _path, arc in build_pack.collect_files(framework)]
            self.assertFalse([a for a in arcnames if "cache" in a or a.endswith(".pyc")])


# ---------------------------------------------------------------------------
# AC-12: the prefix is never exported
# ---------------------------------------------------------------------------

_EXPORT = """\
import json, os, sys
sys.path.insert(0, sys.argv[1])
sys.dont_write_bytecode = True
import bytecode_cache
had = "PYTHONPYCACHEPREFIX" in os.environ
prefix = bytecode_cache.configure()
import sensor_runner
result = sensor_runner.run_sensor(sys.argv[2], {"name": "env", "command": [sys.executable, "-c",
    "import os; print('PREFIX=' + os.environ.get('PYTHONPYCACHEPREFIX', '<none>'))"]}, timeout_seconds=60)
print(json.dumps({"had": had, "has": "PYTHONPYCACHEPREFIX" in os.environ, "prefix": prefix,
                  "sensor": result["output_summary"]}))
"""


class NoExportedPrefixTests(_ScratchCase):
    def test_configure_exports_nothing_and_a_sensor_child_gets_no_prefix(self):
        done = _run([sys.executable, "-c", _EXPORT, str(self.scripts), str(self.root)], cwd=self.root)
        self.assertEqual(done.returncode, 0, done.stderr)
        state = json.loads(done.stdout.strip().splitlines()[-1])
        self.assertEqual(state["prefix"], str(self.prefix))
        self.assertFalse(state["had"])
        self.assertFalse(state["has"])
        self.assertIn("PREFIX=<none>", state["sensor"])


# ---------------------------------------------------------------------------
# AC-13: the server reload writes no bytecode and still records identity
# ---------------------------------------------------------------------------


class ReloadWritesNoBytecodeTests(unittest.TestCase):
    def setUp(self):
        import copy
        import setup_readiness
        from server_tools_support import _make_repo, load_server, load_thin_runner

        load_server()
        self.runner = load_thin_runner()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name) / "repo")
        saved = (self.runner._handler, self.runner._root, self.runner._mcp, self.runner._SETUP_LOADED_IDENTITY)

        def restore():
            (self.runner._handler, self.runner._root, self.runner._mcp,
             self.runner._SETUP_LOADED_IDENTITY) = saved
            import server_impl as impl
            impl._SETUP_LOADED_IDENTITY = saved[3]

        self.addCleanup(restore)
        self.setup_readiness = setup_readiness
        self.launch = copy.deepcopy(setup_readiness.capture_loaded_identity())
        self.runner._SETUP_LOADED_IDENTITY = copy.deepcopy(self.launch)
        try:
            self.runner.build_server(self.root)
        except ImportError:
            self.skipTest("mcp package not installed")

    def test_a_reload_with_writes_on_and_a_prefix_set_writes_no_pyc(self):
        import copy
        prefix = Path(self.tmp.name) / "pycache"
        disk = copy.deepcopy(self.launch)
        disk["sources"]["wf_server/server_impl.py"] = "new-impl"
        saved = (sys.pycache_prefix, sys.dont_write_bytecode)
        try:
            sys.pycache_prefix = str(prefix)
            sys.dont_write_bytecode = False
            with mock.patch.object(self.setup_readiness, "capture_loaded_identity", return_value=disk):
                result = self.runner.perform_mcp_reload()
            flag_after = sys.dont_write_bytecode
        finally:
            sys.pycache_prefix, sys.dont_write_bytecode = saved
        self.assertEqual(result["status"], "ok", result)
        self.assertFalse(flag_after)
        self.assertEqual([p.name for p in prefix.rglob("server_impl*.pyc")], [])
        self.assertEqual(self.runner._SETUP_LOADED_IDENTITY["sources"]["wf_server/server_impl.py"], "new-impl")


# ---------------------------------------------------------------------------
# AC-16: upgrade runner members run without bytecode_cache
# ---------------------------------------------------------------------------


class UpgradeRunnerMemberTests(unittest.TestCase):
    """The built zipapp is exercised by tests/test_upgrade_protocol.py
    (``build_pack.build_upgrade_bundle`` then ``upgrade_bundle.run``)."""

    def test_the_standalone_bridge_runs_with_no_bytecode_cache_beside_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / "upgrade_bridge_bootstrap.py"
            shutil.copy2(SCRIPTS / "upgrade_bridge_bootstrap.py", copied)
            done = _run([sys.executable, str(copied), "--help"], cwd=Path(tmp))
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(_pycache_dirs(Path(tmp)), [])


if __name__ == "__main__":
    unittest.main()

"""Timed helpers that start children end their whole tree (wave 1z8tr, change 1z8qm).

AC-1: the routed sites call ``run_with_tree_kill`` (a spy drives two of them;
an AST census keyed by file, enclosing function and callee pins the rest), and
every other timed call outside ``tests/`` is classified with a reason, so a new
timed call fails here until someone decides it.
AC-2: a setup install step and an upgrade convention hook that start a
long-lived grandchild and exceed their timeout leave no grandchild running.
AC-3: the sliced wait returns the same output (more than a pipe buffer), keeps
the caller's timeout, and a large input to a slow reader completes (inputs are
not sliced).
AC-4: a ``KeyboardInterrupt`` raised in the parent during the sliced wait ends
the child group, including through a setup install step.
AC-5: ``setup_index`` against a ``subprocess_util`` without the helper falls
back to ``isolated_run``.

Wave 1z8ox (change 1z8ow) widens the census: calls through
``index_state_store._run_git`` and each module's ``_run_tree_kill`` resolver are
counted, a timed call to an unnamed callee fails it, and only the named
exclusions remain. It adds a spy per resolver, a routed git site whose timeout
ends a fake git's descendant, the reap guard in ``_kill_process_tree``, and the
fallback of a routed module without the helper. Its delivery repair (DEL-F2)
adds ``check_output``, ``check_call`` and ``call`` to the counted callees, routes
``run_tests.repo_state_snapshot``'s git listing, and adds a binding census: a
process runner bound to a name outside the named resolvers fails it.
"""
from __future__ import annotations

import _thread
import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import subprocess_util  # noqa: E402

POSIX_ONLY = unittest.skipIf(os.name == "nt", "process-group checks use POSIX pids and signals")

# ---------------------------------------------------------------------------
# AC-1: classification of every timed subprocess call outside tests/
# ---------------------------------------------------------------------------

CALLEES = frozenset({"run", "isolated_run", "run_with_tree_kill", "communicate", "wait", "_run_install_step",
                     "_mcp_subprocess_run", "_run_git", "_run_tree_kill",
                     "check_output", "check_call", "call"})

# Named resolvers (wave 1z8ox, change 1z8ow): each routed module looks the helper
# up at call time in ONE module-level function, so the census can count its
# sites by name. index_state_store._run_git is the store's resolver.
RESOLVER_MODULES = (
    "accel_embedder", "dashboard_lib", "docs_gardener", "graph_indexer", "graph_quality_eval",
    "indexer", "operator_identity", "provider_policy", "render_platform_surfaces", "retrieval_eval",
    "run_secrets_scan", "run_tests", "scan_secrets", "sqlite_storage_migration", "upgrade_protocol", "server_impl",
)

# Calls that end their whole process tree on timeout.
ROUTED = {
    # server_impl._mcp_subprocess_run forwards its timeout to run_with_tree_kill (wave 1z822).
    ("wf_server/docs_handlers.py", "run_garden", "_mcp_subprocess_run"): 1,
    ("wf_server/docs_handlers.py", "run_sync_surfaces", "_mcp_subprocess_run"): 1,
    ("wf_server/docs_handlers.py", "wf_scan_secrets_response", "_mcp_subprocess_run"): 1,
    ("wf_server/index_handlers.py", "_index_is_up_to_date", "_mcp_subprocess_run"): 1,
    ("wf_server/server_impl.py", "_audit_commit_governance", "_mcp_subprocess_run"): 1,
    ("wf_server/server_impl.py", "_audit_harnessability", "_mcp_subprocess_run"): 1,
    ("wf_server/server_impl.py", "run_validate", "_mcp_subprocess_run"): 1,
    ("wf_server/server_impl.py", "run_validate_changed", "_mcp_subprocess_run"): 1,
    ("sensor_runner.py", "run_sensor", "run_with_tree_kill"): 1,
    ("setup_index.py", "_bootstrap_uv", "_run_install_step"): 1,
    ("setup_index.py", "_bootstrap_venv", "_run_install_step"): 1,
    ("setup_index.py", "_install_deps", "_run_install_step"): 1,
    ("techdocs_audit_lib.py", "run_techdocs_audit", "run_with_tree_kill"): 1,
    ("upgrade_wavefoundry.py", "_delegated_summary_payload", "run_with_tree_kill"): 1,
    ("upgrade_wavefoundry.py", "_read_installed_graph_builder_version", "run_with_tree_kill"): 1,
    ("upgrade_wavefoundry.py", "_run_hook", "run_with_tree_kill"): 1,
    # index_state_store._run_git resolves the helper and keeps the sanitized git env (wave 1z8ox).
    ("commit_provenance.py", "_git", "_run_git"): 1,
    ("index_state_store.py", "_batch_git_blobs", "_run_git"): 1,
    ("index_state_store.py", "_collect_git_freshness", "_run_git"): 1,
    ("index_state_store.py", "_collect_git_history", "_run_git"): 1,
    ("index_state_store.py", "_gardener_only_pairs", "_run_git"): 1,
    ("index_state_store.py", "_git_authority", "_run_git"): 2,
    ("index_state_store.py", "_git_head", "_run_git"): 1,
    ("techdocs_audit_lib.py", "_baseline_text", "_run_git"): 1,
    # _git_strip_vars cannot call _run_git (it would recurse), so it binds the
    # call-time resolution to a local named after the helper; pinned by a spy.
    ("index_state_store.py", "_git_strip_vars", "run_with_tree_kill"): 1,
    # Per-module _run_tree_kill resolvers (wave 1z8ox).
    ("accel_embedder.py", "_coreml_static_probe_passes", "_run_tree_kill"): 1,
    ("dashboard_lib.py", "_windows_process_cmdlines", "_run_tree_kill"): 1,
    ("dashboard_lib.py", "collect_git_stats.run", "_run_tree_kill"): 1,
    ("dashboard_lib.py", "collect_git_stats.run_raw", "_run_tree_kill"): 1,
    ("dashboard_lib.py", "get_file_diff._run", "_run_tree_kill"): 1,
    ("dashboard_lib.py", "list_git_changed_files.run", "_run_tree_kill"): 1,
    ("docs_gardener.py", "collect_changed_markdown_paths", "_run_tree_kill"): 1,
    ("graph_indexer.py", "_gitignored_paths", "_run_tree_kill"): 1,
    ("graph_quality_eval.py", "_git_value", "_run_tree_kill"): 1,
    ("graph_indexer.py", "_physical_perf_core_count", "_run_tree_kill"): 1,
    ("indexer.py", "_process_cmdline", "_run_tree_kill"): 1,
    ("operator_identity.py", "resolve_operator", "_run_tree_kill"): 1,
    ("provider_policy.py", "_ldconfig_lib_paths", "_run_tree_kill"): 1,
    ("provider_policy.py", "nvidia_gpu_present", "_run_tree_kill"): 1,
    ("render_platform_surfaces.py", "tracked_runtime_diagnostics.git", "_run_tree_kill"): 1,
    ("retrieval_eval.py", "_git_output", "_run_tree_kill"): 1,
    ("run_tests.py", "repo_state_snapshot", "_run_tree_kill"): 1,
    ("run_secrets_scan.py", "_physical_perf_core_count", "_run_tree_kill"): 1,
    ("scan_secrets.py", "_physical_perf_core_count", "_run_tree_kill"): 1,
    ("sqlite_storage_migration.py", "_process_cwds", "_run_tree_kill"): 1,
    ("sqlite_storage_migration.py", "discover_hosts", "_run_tree_kill"): 2,
    ("upgrade_protocol.py", "_validate_mandatory_imports_in_subprocess", "_run_tree_kill"): 1,
    ("wf_server/server_impl.py", "_predict_incremental_full_fallback", "_run_tree_kill"): 1,
    ("wf_server/server_impl.py", "_wave_code_footprint", "_run_tree_kill"): 1,
}

# Timed calls that stay as they are, each with the reason. Only these (wave 1z8ox).
EXCLUDED = {
    ("dashboard_server.py", "_watch_loop", "wait"): (1, "threading.Event.wait, not a subprocess"),
    ("run_tests.py", "_run_file", "run"): (1, "waits run in worker threads; a new session would stop Ctrl-C ending the suite"),
    ("setup_index.py", "_run_indexer", "wait"): (1, "Popen background build with its own lifecycle"),
    ("setup_index.py", "_terminate_and_reap", "wait"): (2, "Popen background build with its own lifecycle"),
    ("subprocess_util.py", "_communicate_sliced", "communicate"): (2, "the helper's own wait"),
    ("subprocess_util.py", "_kill_process_tree", "isolated_run"): (1, "taskkill inside the helper"),
    ("subprocess_util.py", "run_with_tree_kill", "communicate"): (1, "the helper's own post-kill drain"),
    ("subprocess_util.py", "run_with_tree_kill", "wait"): (1, "the helper's own reap after an interrupt kill"),
    ("venv_bootstrap.py", "_probe_interpreter", "run"): (
        1, "venv_bootstrap is stdlib-only (test_venv_bootstrap.StdlibOnlyTests); the "
           "python -I -S -B -c probe starts no descendants"),
}

# The census key for a timed call whose callee is not a plain name or attribute,
# such as an inline ``(getattr(...) or ...)(..., timeout=...)``.
UNNAMED = "<unnamed>"


def timed_call_census(scripts_root: Path) -> Counter:
    """(file, enclosing function, callee) -> count of calls passing ``timeout=``.

    Predicate: a call that passes a literal ``timeout=`` keyword and whose
    callee name is in ``CALLEES``, or whose callee has no name at all (an
    inline ``(getattr(...) or ...)(...)`` call-time resolution), counted under
    ``UNNAMED`` so the classification test fails on it. Known limits: a timeout forwarded through
    ``**kwargs`` is not seen (``server_impl._mcp_subprocess_run`` forwards to
    ``run_with_tree_kill`` that way, so its callers are counted instead), and
    calls inside rendered hook bodies (template strings in
    ``render_platform_surfaces``) are not code here and are out of scope.
    """
    found: Counter = Counter()
    for path in sorted(scripts_root.rglob("*.py")):
        rel = path.relative_to(scripts_root)
        if "tests" in rel.parts[:-1] or "__pycache__" in rel.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        stack: list[str] = []

        class _Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):  # noqa: N802
                stack.append(node.name)
                self.generic_visit(node)
                stack.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Call(self, node):  # noqa: N802
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                timed = any(k.arg == "timeout" for k in node.keywords)
                if timed and (name in CALLEES or not name):
                    found[(rel.as_posix(), ".".join(stack) or "<module>", name or UNNAMED)] += 1
                self.generic_visit(node)

        _Visitor().visit(tree)
    return found


# Functions allowed to bind a process runner to a name (DEL-F2 of wave 1z8ox):
# a runner held in a local and called under another name escapes the timed-call
# census above, so only the named resolvers may do it.
BINDING_ALLOWED = frozenset(
    {(("wf_server/" if name == "server_impl" else "") + name + ".py", "_run_tree_kill")
     for name in RESOLVER_MODULES}
    | {
        ("index_state_store.py", "_run_git"),
        ("index_state_store.py", "_git_strip_vars"),
        # setup_index's resolver predates the per-module name; it is the only
        # caller of the helper there and is pinned by RoutingSpyTests.
        ("setup_index.py", "_run_install_step"),
    }
)

_RUNNER_ATTRS = {
    ("subprocess_util", "isolated_run"), ("subprocess_util", "run_with_tree_kill"),
    ("subprocess", "run"), ("subprocess", "Popen"),
    ("subprocess", "check_output"), ("subprocess", "check_call"), ("subprocess", "call"),
}


def _references_runner(value: ast.AST) -> bool:
    """True when ``value`` refers to a process runner as a value, not by calling it.

    ``subprocess.run(...)`` (the runner is the callee) is a call, not a binding;
    ``subprocess_util.isolated_run`` or ``getattr(subprocess_util, ...)`` used as
    a value is a binding.
    """
    callees = {id(node.func) for node in ast.walk(value) if isinstance(node, ast.Call)}
    for node in ast.walk(value):
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and (node.value.id, node.attr) in _RUNNER_ATTRS and id(node) not in callees):
            return True
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "getattr"
                and node.args and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "subprocess_util"):
            return True
    return False


def runner_binding_census(scripts_root: Path) -> Counter:
    """(file, enclosing function) -> count of Assign/AnnAssign/NamedExpr nodes
    whose value refers to a process runner (see ``_references_runner``).

    Known limits: an import alias (``from subprocess_util import isolated_run as r``),
    a module alias (``import subprocess_util as su; r = su.isolated_run``) and a
    default argument (``def f(r=subprocess.run)``) are not seen; none exists in
    the tree today."""
    found: Counter = Counter()
    for path in sorted(scripts_root.rglob("*.py")):
        rel = path.relative_to(scripts_root)
        if "tests" in rel.parts[:-1] or "__pycache__" in rel.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        stack: list[str] = []

        class _Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):  # noqa: N802
                stack.append(node.name)
                self.generic_visit(node)
                stack.pop()

            visit_AsyncFunctionDef = visit_FunctionDef

            def _check(self, node):
                if node.value is not None and _references_runner(node.value):
                    found[(rel.as_posix(), ".".join(stack) or "<module>")] += 1
                self.generic_visit(node)

            visit_Assign = visit_AnnAssign = visit_NamedExpr = _check

        _Visitor().visit(tree)
    return found


class ClassificationTests(unittest.TestCase):
    def test_every_timed_call_is_routed_or_classified(self) -> None:
        expected = dict(ROUTED)
        expected.update({key: count for key, (count, _reason) in EXCLUDED.items()})
        self.assertEqual(dict(timed_call_census(SCRIPTS_ROOT)), expected)

    def test_every_exclusion_has_a_reason(self) -> None:
        for key, (_count, reason) in EXCLUDED.items():
            self.assertTrue(reason.strip(), key)
        self.assertFalse(set(ROUTED) & set(EXCLUDED))

    def test_census_sees_a_planted_unclassified_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tiny.py").write_text(
                "import subprocess\n"
                "def build():\n"
                "    subprocess.run(['make'], timeout=5)\n",
                encoding="utf-8",
            )
            self.assertEqual(dict(timed_call_census(Path(tmp))), {("tiny.py", "build", "run"): 1})

    def test_census_flags_a_timed_call_to_an_unnamed_callee(self) -> None:
        # An inline call-time resolution has no callee name for the census to
        # classify, so it is reported under UNNAMED and fails the table check.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tiny.py").write_text(
                "import subprocess_util\n"
                "def probe():\n"
                "    (getattr(subprocess_util, 'run_with_tree_kill', None)\n"
                "     or subprocess_util.isolated_run)(['git', 'status'], timeout=1)\n",
                encoding="utf-8",
            )
            self.assertEqual(dict(timed_call_census(Path(tmp))), {("tiny.py", "probe", UNNAMED): 1})
        self.assertNotIn(UNNAMED, {callee for _file, _fn, callee in timed_call_census(SCRIPTS_ROOT)})

    def test_census_sees_a_planted_timed_check_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tiny.py").write_text(
                "import subprocess\n"
                "def probe():\n"
                "    return subprocess.check_output(['git', 'status'], timeout=5)\n",
                encoding="utf-8",
            )
            census = dict(timed_call_census(Path(tmp)))
        self.assertEqual(census, {("tiny.py", "probe", "check_output"): 1})
        expected = dict(ROUTED)
        expected.update({key: count for key, (count, _reason) in EXCLUDED.items()})
        self.assertNotEqual({**dict(timed_call_census(SCRIPTS_ROOT)), **census}, expected)

    def test_runners_are_bound_to_names_only_in_the_resolvers(self) -> None:
        census = runner_binding_census(SCRIPTS_ROOT)
        self.assertEqual(set(census) - BINDING_ALLOWED, set())

    def test_binding_census_sees_a_planted_runner_alias(self) -> None:
        # A runner bound to a local and called under another name dodges the
        # timed-call census (``runner`` is not in CALLEES); the binding census
        # catches it.
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tiny.py").write_text(
                "import subprocess_util\n"
                "def probe():\n"
                "    runner = subprocess_util.isolated_run\n"
                "    return runner(['git', 'status'], timeout=5)\n",
                encoding="utf-8",
            )
            self.assertEqual(dict(timed_call_census(Path(tmp))), {})
            census = runner_binding_census(Path(tmp))
        self.assertEqual(dict(census), {("tiny.py", "probe"): 1})
        self.assertEqual(set(census) - BINDING_ALLOWED, {("tiny.py", "probe")})

    def test_binding_census_sees_planted_aliases_of_every_subprocess_api(self) -> None:
        # Each subprocess runner API bound to a local and called under another
        # name dodges the timed-call census; the binding census catches each.
        for api in ("run", "Popen", "check_output", "check_call", "call"):
            with self.subTest(api=api), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "tiny.py").write_text(
                    "import subprocess\n"
                    "def probe():\n"
                    f"    runner = subprocess.{api}\n"
                    "    return runner(['git', 'status'], timeout=5)\n",
                    encoding="utf-8",
                )
                self.assertEqual(dict(timed_call_census(Path(tmp))), {})
                self.assertEqual(dict(runner_binding_census(Path(tmp))), {("tiny.py", "probe"): 1})

    def test_binding_census_ignores_direct_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tiny.py").write_text(
                "import subprocess, subprocess_util\n"
                "def probe():\n"
                "    result = subprocess.run(['git'])\n"
                "    other = subprocess_util.isolated_run(['git'])\n"
                "    return result, other\n",
                encoding="utf-8",
            )
            self.assertEqual(dict(runner_binding_census(Path(tmp))), {})

    def test_resolver_sites_are_in_the_resolver_modules(self) -> None:
        resolver_files = {
            file for (file, _fn, callee) in ROUTED if callee == "_run_tree_kill"
        }
        expected = {
            ("wf_server/" if name == "server_impl" else "") + name + ".py" for name in RESOLVER_MODULES
        }
        self.assertEqual(resolver_files, expected)


def _load_setup_index():
    spec = importlib.util.spec_from_file_location("setup_index_tree_kill", SCRIPTS_ROOT / "setup_index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_resolver_module(name: str):
    if name == "server_impl":
        tests_dir = str(Path(__file__).resolve().parent)
        if tests_dir not in sys.path:
            sys.path.insert(0, tests_dir)
        import server_tools_support

        return server_tools_support.load_server()
    return importlib.import_module(name)


class RoutingSpyTests(unittest.TestCase):
    def test_setup_install_step_calls_the_helper(self) -> None:
        setup_index = _load_setup_index()
        done = subprocess.CompletedProcess(["x"], 0)
        with mock.patch.object(subprocess_util, "run_with_tree_kill", return_value=done) as helper, \
                mock.patch.object(subprocess_util, "isolated_run") as plain:
            self.assertIs(setup_index._run_install_step(["x"], check=False, timeout=7), done)
        helper.assert_called_once_with(["x"], check=False, timeout=7)
        plain.assert_not_called()

    def test_setup_falls_back_without_the_helper(self) -> None:
        # AC-5: a 1.27.0 runner's subprocess_util has no run_with_tree_kill.
        setup_index = _load_setup_index()
        done = subprocess.CompletedProcess(["x"], 0)
        old = types.SimpleNamespace(isolated_run=mock.Mock(return_value=done))
        with mock.patch.object(setup_index, "subprocess_util", old):
            self.assertIs(setup_index._run_install_step(["x"], timeout=3), done)
        old.isolated_run.assert_called_once_with(["x"], timeout=3)

    def test_techdocs_worker_calls_the_helper_with_its_input(self) -> None:
        import techdocs_audit_lib

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(subprocess_util, "run_with_tree_kill",
                                  side_effect=subprocess.TimeoutExpired(["w"], 1)) as helper:
            techdocs_audit_lib.run_techdocs_audit(Path(tmp), timeout_seconds=1)
        helper.assert_called_once()
        self.assertIn('"repo_root"', helper.call_args.kwargs["input"])

    def test_each_module_resolver_calls_the_helper(self) -> None:
        done = subprocess.CompletedProcess(["x"], 0)
        for name in RESOLVER_MODULES:
            with self.subTest(module=name):
                module = _load_resolver_module(name)
                with mock.patch.object(subprocess_util, "run_with_tree_kill", return_value=done) as helper, \
                        mock.patch.object(subprocess_util, "isolated_run") as plain:
                    self.assertIs(module._run_tree_kill(["x"], check=False, timeout=7), done)
                helper.assert_called_once_with(["x"], check=False, timeout=7)
                plain.assert_not_called()

    def test_store_run_git_calls_the_helper_with_the_sanitized_env(self) -> None:
        import index_state_store as iss

        done = subprocess.CompletedProcess(["git"], 0)
        with mock.patch.object(iss, "_git_strip_vars_cache", frozenset({"GIT_DIR"})), \
                mock.patch.dict(os.environ, {"GIT_DIR": "/decoy"}), \
                mock.patch.object(subprocess_util, "run_with_tree_kill", return_value=done) as helper, \
                mock.patch.object(subprocess_util, "isolated_run") as plain:
            self.assertIs(iss._run_git(["git", "status"], capture_output=True, timeout=7), done)
        helper.assert_called_once()
        self.assertEqual(helper.call_args.args, (["git", "status"],))
        self.assertEqual(helper.call_args.kwargs["timeout"], 7)
        self.assertNotIn("GIT_DIR", helper.call_args.kwargs["env"])
        self.assertEqual(helper.call_args.kwargs["env"]["LC_ALL"], "C")
        plain.assert_not_called()

    def test_store_git_strip_vars_calls_the_helper(self) -> None:
        import index_state_store as iss

        done = subprocess.CompletedProcess(["git"], 0, stdout="GIT_EXAMPLE_VAR\n")
        with mock.patch.object(iss, "_git_strip_vars_cache", None), \
                mock.patch.object(subprocess_util, "run_with_tree_kill", return_value=done) as helper, \
                mock.patch.object(subprocess_util, "isolated_run") as plain:
            self.assertIn("GIT_EXAMPLE_VAR", iss._git_strip_vars())
        helper.assert_called_once()
        self.assertEqual(helper.call_args.args, (["git", "rev-parse", "--local-env-vars"],))
        self.assertEqual(helper.call_args.kwargs["timeout"], 10)
        plain.assert_not_called()

    def test_graph_quality_git_value_calls_the_helper_with_its_timeout(self) -> None:
        # Wave 1za2y (1za2x): the evaluator's provenance probe ends its tree on timeout.
        import graph_quality_eval

        done = subprocess.CompletedProcess(["git"], 0, stdout="abc\n")
        with mock.patch.object(subprocess_util, "run_with_tree_kill", return_value=done) as helper, \
                mock.patch.object(subprocess_util, "isolated_run") as plain:
            self.assertEqual(graph_quality_eval._git_value(Path("."), "rev-parse", "HEAD"), "abc")
        helper.assert_called_once()
        self.assertEqual(helper.call_args.args, (["git", "rev-parse", "HEAD"],))
        self.assertEqual(helper.call_args.kwargs["timeout"], 30)
        plain.assert_not_called()

    def test_graph_quality_git_value_falls_back_without_the_helper(self) -> None:
        # The baseline production's subprocess_util predates run_with_tree_kill.
        import graph_quality_eval

        old = types.SimpleNamespace(isolated_run=mock.Mock(
            return_value=subprocess.CompletedProcess(["git"], 0, stdout="abc\n")))
        with mock.patch.dict(sys.modules, {"subprocess_util": old}):
            self.assertEqual(graph_quality_eval._git_value(Path("."), "rev-parse", "HEAD"), "abc")
        old.isolated_run.assert_called_once()
        self.assertEqual(old.isolated_run.call_args.kwargs["timeout"], 30)

    def test_routed_module_falls_back_without_the_helper(self) -> None:
        # AC-5 (wave 1z8ox): an upgrade runner's older subprocess_util has no
        # run_with_tree_kill; a routed site falls back to isolated_run.
        import provider_policy

        old = types.SimpleNamespace(isolated_run=mock.Mock(
            return_value=subprocess.CompletedProcess(["nvidia-smi"], 0, stdout="GPU 0: Example\n")))
        with mock.patch.object(provider_policy, "subprocess_util", old), \
                mock.patch.object(provider_policy.shutil, "which", return_value="nvidia-smi"):
            self.assertTrue(provider_policy.nvidia_gpu_present())
        old.isolated_run.assert_called_once_with(
            ["nvidia-smi", "-L"], capture_output=True, text=True, timeout=3, check=False)


# ---------------------------------------------------------------------------
# AC-2 and AC-4: real process trees
# ---------------------------------------------------------------------------

def _grandchild_script(pid_file: Path) -> list[str]:
    """A child that starts a long-lived grandchild, records its pid, and sleeps."""
    code = (
        "import subprocess, sys, time\n"
        "g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"open({str(pid_file)!r}, 'w').write(str(g.pid))\n"
        "time.sleep(60)\n"
    )
    return [sys.executable, "-c", code]


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class _TreeCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.pid_file = Path(self._tmp.name) / "grandchild.pid"

    def tearDown(self) -> None:
        # Never leak a sleeper if an assertion failed.
        try:
            os.kill(int(self.pid_file.read_text()), 9)
        except (OSError, ValueError):
            pass
        self._tmp.cleanup()

    def _grandchild_pid(self) -> int:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            try:
                return int(self.pid_file.read_text())
            except (OSError, ValueError):
                time.sleep(0.05)
        self.fail("grandchild never recorded its pid")

    def assertGone(self, pid: int) -> None:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and _alive(pid):
            time.sleep(0.05)
        self.assertFalse(_alive(pid), f"grandchild {pid} survived")


@POSIX_ONLY
class GrandchildTests(_TreeCase):
    def test_setup_install_step_timeout_ends_the_tree(self) -> None:
        setup_index = _load_setup_index()
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            setup_index._run_install_step(_grandchild_script(self.pid_file), check=False, timeout=1.5)
        self.assertEqual(caught.exception.timeout, 1.5)
        self.assertGone(self._grandchild_pid())

    def test_convention_hook_timeout_ends_the_tree_and_aborts(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "upgrade_wavefoundry_tree_kill", SCRIPTS_ROOT / "upgrade_wavefoundry.py")
        upgrade = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(upgrade)
        root = Path(self._tmp.name) / "repo"
        hooks = root / ".wavefoundry" / "hooks"
        hooks.mkdir(parents=True)
        hook = hooks / "post-docs-gate"
        hook.write_text(f"#!/bin/sh\nsleep 60 &\necho $! > '{self.pid_file}'\nsleep 60\n", encoding="utf-8")
        hook.chmod(0o755)
        ctx = upgrade.UpgradeContext(root=root, from_version="a", to_version="b", zip_path=None, yes=True)
        with mock.patch.object(upgrade, "_HOOK_TIMEOUT_S", 1.5), self.assertRaises(SystemExit) as caught:
            upgrade._run_hook("post_docs_gate", ctx, None)
        self.assertEqual(caught.exception.code, 3)
        self.assertGone(self._grandchild_pid())

    def test_parent_interrupt_ends_the_tree_through_a_setup_install_step(self) -> None:
        # AC-4: the interrupt is delivered to the main thread during the sliced wait.
        setup_index = _load_setup_index()
        timer = threading.Timer(1.0, _thread.interrupt_main)
        timer.start()
        try:
            with self.assertRaises(KeyboardInterrupt):
                setup_index._run_install_step(_grandchild_script(self.pid_file), check=False, timeout=30)
        finally:
            timer.cancel()
        self.assertGone(self._grandchild_pid())


@POSIX_ONLY
class RoutedGitSiteTests(_TreeCase):
    """Wave 1z8ox (change 1z8ow) AC-2: a routed git site ends git's descendants on timeout.

    Runs without the tree-kill test shim: the real helper, a real process tree.
    """

    def test_gitignored_paths_timeout_ends_the_fake_gits_descendant(self) -> None:
        import graph_indexer

        bin_dir = Path(self._tmp.name) / "bin"
        bin_dir.mkdir()
        fake_git = bin_dir / "git"
        fake_git.write_text(
            f"#!/bin/sh\nsleep 60 &\necho $! > '{self.pid_file}'\nsleep 60\n", encoding="utf-8")
        fake_git.chmod(0o755)
        path = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        started = time.monotonic()
        with mock.patch.dict(os.environ, {"PATH": path}), \
                mock.patch.object(graph_indexer, "_GITIGNORED_PATHS_TIMEOUT_S", 1.5):
            self.assertEqual(graph_indexer._gitignored_paths(Path(self._tmp.name)), frozenset())
        self.assertLess(time.monotonic() - started, 20)
        self.assertGone(self._grandchild_pid())


class ReapGuardTests(unittest.TestCase):
    """Wave 1z8ox AC-3: a child the helper already reaped never has its old group id signalled."""

    def _process(self, returncode):
        return types.SimpleNamespace(pid=424242, returncode=returncode, kill=mock.Mock())

    def test_reaped_child_is_not_group_signalled(self) -> None:
        process = self._process(0)
        with mock.patch.object(subprocess_util.os, "killpg", create=True) as killpg:
            subprocess_util._kill_process_tree(process)
        killpg.assert_not_called()
        process.kill.assert_called_once()

    @POSIX_ONLY
    def test_unreaped_child_is_group_signalled(self) -> None:
        import signal

        process = self._process(None)
        with mock.patch.object(subprocess_util.os, "killpg") as killpg:
            subprocess_util._kill_process_tree(process)
        killpg.assert_called_once_with(424242, signal.SIGKILL)

    def test_windows_branch_follows_the_same_rule(self) -> None:
        fake_os = types.SimpleNamespace(name="nt")
        for returncode, calls in ((0, 0), (None, 1)):
            with self.subTest(returncode=returncode), \
                    mock.patch.object(subprocess_util, "os", fake_os), \
                    mock.patch.object(subprocess_util, "isolated_run") as taskkill:
                subprocess_util._kill_process_tree(self._process(returncode))
            self.assertEqual(taskkill.call_count, calls)
            if calls:
                self.assertEqual(taskkill.call_args.args[0][:3], ["taskkill", "/PID", "424242"])


@POSIX_ONLY
class ExitedUnreapedChildTests(_TreeCase):
    """Wave 1z8ox AC-3b: a child that exited but is unreaped, while a descendant
    holds its output pipe, still has its group signalled on timeout. A guard that
    calls ``poll()`` first would reap the child, skip the kill and leak the descendant."""

    def test_exited_child_with_a_descendant_holding_the_pipe_ends_the_group(self) -> None:
        code = (
            "import subprocess, sys\n"
            "g = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
            f"open({str(self.pid_file)!r}, 'w').write(str(g.pid))\n"
        )
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess_util.run_with_tree_kill(
                [sys.executable, "-c", code], capture_output=True, text=True, timeout=1.5)
        self.assertGone(self._grandchild_pid())


# ---------------------------------------------------------------------------
# AC-3: slicing preserves output, timeout and input
# ---------------------------------------------------------------------------

class SlicedWaitTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.object(subprocess_util, "_TREE_KILL_WAIT_SLICE_SECONDS", 0.05)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _python(self, code: str) -> list[str]:
        return [sys.executable, "-c", code]

    def test_waits_in_slices(self) -> None:
        seen: list[float | None] = []
        real = subprocess.Popen.communicate

        def spy(process, input=None, timeout=None):
            seen.append(timeout)
            return real(process, input, timeout)

        with mock.patch.object(subprocess.Popen, "communicate", spy):
            subprocess_util.run_with_tree_kill(self._python("import time; time.sleep(0.4)"), timeout=10)
        self.assertGreater(len(seen), 2)
        self.assertTrue(all(t is not None and t <= 0.05 for t in seen), seen)

    def test_output_larger_than_a_pipe_buffer_is_whole(self) -> None:
        size = 1_000_000
        result = subprocess_util.run_with_tree_kill(
            self._python(f"import sys, time; time.sleep(0.3); sys.stdout.write('x' * {size})"),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout), size)

    def test_no_timeout_still_completes(self) -> None:
        result = subprocess_util.run_with_tree_kill(
            self._python("import time; time.sleep(0.3); print('done')"), capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "done")

    def test_timeout_is_the_callers(self) -> None:
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired) as caught:
            subprocess_util.run_with_tree_kill(self._python("import time; time.sleep(30)"), timeout=0.6)
        elapsed = time.monotonic() - started
        self.assertEqual(caught.exception.timeout, 0.6)
        self.assertGreaterEqual(elapsed, 0.55)
        self.assertLess(elapsed, 10)

    def test_large_input_to_a_slow_reader_completes(self) -> None:
        size = 5_000_000
        result = subprocess_util.run_with_tree_kill(
            self._python("import sys, time; time.sleep(0.5); print(len(sys.stdin.read()))"),
            input="y" * size, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.stdout.strip(), str(size))


if __name__ == "__main__":
    unittest.main()

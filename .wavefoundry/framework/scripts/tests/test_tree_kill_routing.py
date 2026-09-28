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
                     "_mcp_subprocess_run"})

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
}

# Timed calls that stay as they are, each with the reason.
_GIT = "single git command, no descendants"
_PROBE = "single-program probe, no descendants"
EXCLUDED = {
    ("accel_embedder.py", "_coreml_static_probe_passes", "isolated_run"): (1, "one Python process loading a model; no children"),
    ("dashboard_lib.py", "_windows_process_cmdlines", "isolated_run"): (1, "PowerShell process query"),
    ("dashboard_lib.py", "collect_git_stats.run", "isolated_run"): (1, _GIT),
    ("dashboard_lib.py", "collect_git_stats.run_raw", "isolated_run"): (1, _GIT),
    ("dashboard_lib.py", "get_file_diff._run", "isolated_run"): (1, _GIT),
    ("dashboard_lib.py", "list_git_changed_files.run", "isolated_run"): (1, _GIT),
    ("dashboard_server.py", "_watch_loop", "wait"): (1, "threading.Event.wait, not a subprocess"),
    ("docs_gardener.py", "collect_changed_markdown_paths", "isolated_run"): (1, _GIT),
    ("graph_indexer.py", "_gitignored_paths", "isolated_run"): (1, _GIT),
    ("graph_indexer.py", "_physical_perf_core_count", "isolated_run"): (1, "sysctl " + _PROBE),
    ("graph_quality_eval.py", "_git_value", "isolated_run"): (1, _GIT),
    ("index_state_store.py", "_git_strip_vars", "isolated_run"): (1, _GIT),
    ("indexer.py", "_process_cmdline", "isolated_run"): (1, "PowerShell process query"),
    ("operator_identity.py", "resolve_operator", "run"): (1, _GIT),
    ("provider_policy.py", "_ldconfig_lib_paths", "isolated_run"): (1, "ldconfig " + _PROBE),
    ("provider_policy.py", "nvidia_gpu_present", "isolated_run"): (1, "nvidia-smi " + _PROBE),
    ("render_platform_surfaces.py", "tracked_runtime_diagnostics.git", "isolated_run"): (1, _GIT),
    ("retrieval_eval.py", "_git_output", "isolated_run"): (1, _GIT),
    ("run_secrets_scan.py", "_physical_perf_core_count", "isolated_run"): (1, "sysctl " + _PROBE),
    ("run_tests.py", "_run_file", "run"): (1, "waits run in worker threads; a new session would stop Ctrl-C ending the suite"),
    ("scan_secrets.py", "_physical_perf_core_count", "isolated_run"): (1, "sysctl " + _PROBE),
    ("setup_index.py", "_run_indexer", "wait"): (1, "Popen background build with its own lifecycle"),
    ("setup_index.py", "_terminate_and_reap", "wait"): (2, "Popen background build with its own lifecycle"),
    ("sqlite_storage_migration.py", "_process_cwds", "isolated_run"): (1, "lsof " + _PROBE),
    ("sqlite_storage_migration.py", "discover_hosts", "isolated_run"): (2, "ps or PowerShell process query"),
    ("subprocess_util.py", "_communicate_sliced", "communicate"): (2, "the helper's own wait"),
    ("subprocess_util.py", "_kill_process_tree", "isolated_run"): (1, "taskkill inside the helper"),
    ("subprocess_util.py", "run_with_tree_kill", "communicate"): (1, "the helper's own post-kill drain"),
    ("subprocess_util.py", "run_with_tree_kill", "wait"): (1, "the helper's own reap after an interrupt kill"),
    ("upgrade_protocol.py", "_validate_mandatory_imports_in_subprocess", "run"): (1, "isolated interpreter import probe"),
    ("venv_bootstrap.py", "_probe_interpreter", "run"): (1, "interpreter version probe"),
    ("wf_server/server_impl.py", "_predict_incremental_full_fallback", "isolated_run"): (1, _GIT),
    ("wf_server/server_impl.py", "_wave_code_footprint", "isolated_run"): (1, _GIT),
}


def timed_call_census(scripts_root: Path) -> Counter:
    """(file, enclosing function, callee) -> count of calls passing ``timeout=``.

    Predicate: a call whose callee name is in ``CALLEES`` and that passes a
    literal ``timeout=`` keyword. Known limits: a timeout forwarded through
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
                if name in CALLEES and any(k.arg == "timeout" for k in node.keywords):
                    found[(rel.as_posix(), ".".join(stack) or "<module>", name)] += 1
                self.generic_visit(node)

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


def _load_setup_index():
    spec = importlib.util.spec_from_file_location("setup_index_tree_kill", SCRIPTS_ROOT / "setup_index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

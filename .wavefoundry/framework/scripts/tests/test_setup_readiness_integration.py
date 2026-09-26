"""Public setup/startup boundaries and the shared monitor assessment contract."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.dont_write_bytecode = True
import runtime_advisory


def expected_notice():
    advisory = runtime_advisory.python_runtime_advisory()
    if advisory is not None:
        # Isolated Python can report the resolved Homebrew executable rather
        # than the parent's symlink spelling; provenance belongs to the child.
        advisory["executable"] = subprocess.check_output(
            [sys.executable, "-I", "-S", "-c", "import sys; print(sys.executable)"], text=True,
        ).strip()
    return runtime_advisory.format_advisory(advisory) + "\n" if advisory is not None else ""


def result(status="ready", *, blocked=False, signature=None):
    return {
        "schema_version": 1, "status": status, "signature": signature or {},
        "reasons": [], "actions": [], "startup_blocked": blocked,
        "limitations": [], "timings_ms": {},
    }


class PublicBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.scripts = self.root / ".wavefoundry/framework/scripts"
        self.scripts.mkdir(parents=True)
        for name in ("wf_cli.py", "setup_wavefoundry.py", "server.py", "repo_root.py", "cli_stdio.py", "subprocess_util.py", "runtime_advisory.py"):
            shutil.copy2(SCRIPTS / name, self.scripts / name)
        (self.scripts / "venv_bootstrap.py").write_text(
            "def activate_tool_venv(**kwargs):\n    raise AssertionError('ACTIVATION TRIPWIRE')\n"
            "def tool_venv_python():\n    raise AssertionError('VENV TRIPWIRE')\n"
        )
        (self.scripts / "server_impl.py").write_text("raise AssertionError('HEAVY IMPORT TRIPWIRE')\n")
        (self.scripts / "setup_readiness.py").write_text(
            "import json, os\n"
            "def capture_loaded_identity(): return {'launch': 'test'}\n"
            "def assess_setup(root, **kwargs):\n"
            "    return {'schema_version': 1, 'status': 'action_required', 'root': str(root), "
            "'startup_blocked': os.environ.get('TEST_BLOCKED') == '1', 'actions': [], 'reasons': []}\n"
            "def format_text(result): return json.dumps(result)\n"
            "def exit_code(result): return {'ready': 0, 'action_required': 1, 'indeterminate': 2}[result['status']]\n"
            "def write_setup_stamp(root): raise AssertionError('STAMP TRIPWIRE')\n"
        )

    def invoke(self, name, *args, blocked=False):
        env = dict(os.environ, TEST_BLOCKED="1" if blocked else "0")
        return subprocess.run(
            [sys.executable, "-I", "-S", str(self.scripts / name), *args],
            capture_output=True, text=True, timeout=15, stdin=subprocess.DEVNULL, env=env,
        )

    def test_dispatcher_check_precedes_activation_and_writes_nothing(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        target = self.root / "target with spaces"
        target.mkdir()
        completed = self.invoke("wf_cli.py", "setup", "--check", "--json", "--root", str(target))
        self.assertEqual(completed.returncode, 1, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["root"], str(target))
        self.assertEqual(payload["status"], "action_required")
        self.assertEqual(completed.stderr, expected_notice())
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_check_rejects_repair_flags_before_activation(self):
        for flag in ("--deps-only", "--rebuild", "--check-gpu", "--background-code", "--roo", "--check=true"):
            with self.subTest(flag=flag):
                completed = self.invoke("wf_cli.py", "setup", "--check", flag)
                self.assertEqual(completed.returncode, 2, completed.stderr)
                self.assertNotIn("TRIPWIRE", completed.stderr)
                self.assertEqual(completed.stdout, "")

    def test_startup_blocked_status_precedes_activation_and_heavy_imports(self):
        completed = self.invoke("server.py", "--root", str(self.root), blocked=True)
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertEqual(completed.stdout, "")
        notice = expected_notice()
        self.assertTrue(completed.stderr.startswith(notice))
        self.assertEqual(json.loads(completed.stderr[len(notice):])["root"], str(self.root))

    def test_startup_advisory_does_not_disable_non_index_startup(self):
        completed = self.invoke("server.py", "--root", str(self.root))
        self.assertIn("ACTIVATION TRIPWIRE", completed.stderr)
        self.assertIn('"action_required"', completed.stderr)
        self.assertEqual(completed.stdout, "")

    def test_known_bad_activation_before_check_is_detected(self):
        path = self.scripts / "setup_wavefoundry.py"
        path.write_text(path.read_text().replace(
            "import venv_bootstrap  # the single venv resolver (wave 1p7pl)",
            "import venv_bootstrap\nvenv_bootstrap.activate_tool_venv()",
        ))
        completed = self.invoke("wf_cli.py", "setup", "--check", "--json")
        self.assertIn("ACTIVATION TRIPWIRE", completed.stderr)
        self.assertEqual(completed.stdout, "")

    def test_real_venv_pth_is_not_executed_by_check(self):
        shutil.copy2(SCRIPTS / "venv_bootstrap.py", self.scripts / "venv_bootstrap.py")
        venv = self.root / "venv"
        executable = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        executable.parent.mkdir(parents=True)
        executable.touch()
        site = venv / ("Lib/site-packages" if os.name == "nt" else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
        site.mkdir(parents=True)
        marker = self.root / "pth-executed"
        (site / "poison.pth").write_text(f"import pathlib; pathlib.Path({str(marker)!r}).touch()\n")
        (venv / "pyvenv.cfg").write_text(f"version = {sys.version_info.major}.{sys.version_info.minor}.0\n")
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv)}):
            completed = self.invoke("wf_cli.py", "setup", "--check", "--json")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertFalse(marker.exists())
        self.assertEqual(list(self.root.rglob("__pycache__")), [])


class SharedAssessmentTests(unittest.TestCase):
    def test_real_dispatcher_assessor_missing_environment_preserves_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            scripts = root / ".wavefoundry/framework/scripts"
            shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
            venv = root / "empty-venv"
            site = venv / ("Lib/site-packages" if os.name == "nt" else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages")
            site.mkdir(parents=True)
            marker = root / "pth-executed"
            (site / "poison.pth").write_text(f"import pathlib; pathlib.Path({str(marker)!r}).touch()\n")
            (root / "docs").mkdir()
            (root / "docs/workflow-config.json").write_text("{}")

            def census():
                return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in root.rglob("*") if p.is_file()}

            before = census()
            driver = (
                "import runpy,sys\n"
                "def audit(event,args):\n"
                "    if event in ('socket.connect','socket.getaddrinfo'): raise AssertionError('network')\n"
                "sys.addaudithook(audit)\n"
                "try: runpy.run_path(sys.argv[1],run_name='__main__')\n"
                "except SystemExit:\n"
                "    assert not {'fastembed','onnxruntime','server_impl','setup_index'} & set(sys.modules)\n"
                "    raise\n"
            )
            # run_path leaves sys.argv[1:] intact; the dispatcher sees setup as
            # its first argument after the script path is removed here.
            driver = driver.replace("try: runpy.run_path(sys.argv[1],run_name='__main__')", "script=sys.argv.pop(1)\ntry: runpy.run_path(script,run_name='__main__')")
            completed = subprocess.run(
                [sys.executable, "-I", "-S", "-c", driver, str(scripts / "wf_cli.py"),
                 "setup", "--check", "--json", "--root", str(root)],
                capture_output=True, text=True, timeout=15, stdin=subprocess.DEVNULL,
                env=dict(os.environ, WAVEFOUNDRY_TOOL_VENV=str(venv)),
            )
            self.assertEqual(completed.returncode, 1, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "action_required")
            self.assertTrue(payload["startup_blocked"])
            self.assertEqual(completed.stderr, expected_notice())
            self.assertEqual(before, census())
            self.assertFalse(marker.exists())
            startup = subprocess.run(
                [sys.executable, "-I", "-S", "-c", driver, str(scripts / "server.py"),
                 "--root", str(root)],
                capture_output=True, text=True, timeout=15, stdin=subprocess.DEVNULL,
                env=dict(os.environ, WAVEFOUNDRY_TOOL_VENV=str(venv)),
            )
            self.assertEqual(startup.returncode, 1, startup.stderr)
            self.assertEqual(startup.stdout, "")
            self.assertIn("action_required", startup.stderr)
            self.assertEqual(before, census())

    def test_existing_monitor_tick_observes_setup_without_triggering_setup(self):
        import server_impl
        from unittest.mock import Mock

        handler = server_impl.ImplHandler.__new__(server_impl.ImplHandler)
        handler.root = Path.cwd()
        handler.assess_setup = Mock(return_value=result("action_required"))
        stop = Mock()
        stop.wait.side_effect = [False, True]
        thread = Mock()
        with patch.object(server_impl, "_read_monitor_config", return_value={"enabled": True}), \
             patch.object(server_impl.threading, "Event", return_value=stop), \
             patch.object(server_impl.threading, "Thread", return_value=thread) as constructor, \
             patch.object(server_impl, "_maybe_refresh_if_stale") as refresh:
            handler._start_staleness_monitor()
            constructor.call_args.kwargs["target"]()
        handler.assess_setup.assert_called_once_with()
        # The existing incremental refresher receives no assessment result or
        # repair action; its independent source-change behavior is unchanged.
        self.assertEqual(refresh.call_args.args, (handler.root,))
        self.assertEqual(set(refresh.call_args.kwargs), {"observer"})
        constructor.assert_called_once()

    def test_registered_health_returns_shared_assessment_before_monitor_snapshot(self):
        import server_impl
        from unittest.mock import Mock

        tools = {}

        class Registry:
            def tool(self, *args, **kwargs):
                def register(function):
                    tools[function.__name__] = function
                    return function
                return register

            def resource(self, *args, **kwargs):
                return lambda function: function

        handler = Mock()
        assessment = result("indeterminate")
        with patch.object(sys, "version_info", (3, 12, 9)):
            assessment["advisories"] = [runtime_advisory.python_runtime_advisory()]
        handler.assess_setup.return_value = assessment
        calls = []
        handler.assess_setup.side_effect = lambda **kwargs: calls.append("assessment") or assessment
        handler.background_monitor_status.side_effect = lambda: calls.append("snapshot") or {"setup_readiness": assessment}
        with patch.object(server_impl, "index_health_response", return_value={"status": "ok", "data": {}}):
            server_impl.register_mcp_surface(Registry(), lambda: handler)
            response = tools["index_health"]()
        self.assertEqual(calls, ["assessment", "snapshot"])
        self.assertEqual(response["data"]["setup_readiness"], assessment)
        self.assertEqual(response["data"]["setup_readiness"]["advisories"][0]["actual_version"], "3.12.9")

    def test_explicit_main_argv_not_import_time_sys_argv_controls_check(self):
        import setup_readiness
        import setup_wavefoundry
        with patch.object(sys, "argv", ["unrelated", "--deps-only"]), \
             patch.object(setup_wavefoundry.venv_bootstrap, "activate_tool_venv", side_effect=AssertionError("activation")), \
             patch.object(setup_readiness, "assess_setup", return_value=result("indeterminate")) as assess, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(setup_wavefoundry.main(["--check", "--json"]), 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "indeterminate")
        assess.assert_called_once_with(Path.cwd().resolve())

    def test_monitor_cache_invalidation_coalescing_and_clear(self):
        import server_impl
        import setup_readiness
        handler = server_impl.ImplHandler.__new__(server_impl.ImplHandler)
        handler.root = Path.cwd()
        handler._setup_assessment_lock = threading.Lock()
        handler._setup_loaded_identity = {"launch": "original"}
        handler._setup_assessment_result = None
        handler._setup_assessment_signature = None
        handler._setup_notice_signature = None
        with patch.object(setup_readiness, "assessment_signature", return_value={"v": 1}) as signature, \
             patch.object(setup_readiness, "assess_setup", return_value=result("action_required")) as assess, \
             patch.object(setup_readiness, "format_text", return_value="setup status"), \
             contextlib.redirect_stderr(io.StringIO()) as stderr:
            handler.assess_setup()
            handler.assess_setup()
            self.assertEqual(assess.call_count, 1)
            self.assertEqual(stderr.getvalue().count("setup status"), 1)
            signature.return_value = {"v": 2}
            handler.assess_setup()
            self.assertEqual(assess.call_count, 2)
            self.assertEqual(stderr.getvalue().count("setup status"), 1)
            assess.return_value = result()
            handler.assess_setup(force=True)
            self.assertIsNone(handler._setup_notice_signature)
            assess.return_value = result("action_required")
            handler.assess_setup(force=True)
            self.assertEqual(stderr.getvalue().count("setup status"), 2)
            self.assertEqual(assess.call_args.kwargs["loaded_identity"], {"launch": "original"})
            assess.return_value = result("indeterminate")
            handler.assess_setup(force=True)
            count = assess.call_count
            handler.assess_setup()
            self.assertEqual(assess.call_count, count + 1, "transient unknown must retry without an input edit")
            notices = stderr.getvalue().count("setup status")
            assess.return_value = {**result("indeterminate"), "reasons": [{"code": "busy", "message": "busy"}]}
            handler.assess_setup()
            self.assertEqual(stderr.getvalue().count("setup status"), notices + 1)



class SetupNoticeWrapperTests(unittest.TestCase):
    """Wave 1z2mc: tool responses tell the agent once when setup needs the operator."""

    def setUp(self):
        import server_impl
        self.impl = server_impl
        self.handler = types.SimpleNamespace(_setup_assessment_result=None)

    def _wrap(self, **fns):
        tools = {name: types.SimpleNamespace(fn=fn) for name, fn in fns.items()}
        mcp = types.SimpleNamespace(_tool_manager=types.SimpleNamespace(_tools=tools))
        self.impl._wrap_setup_notice(mcp, lambda: self.handler)
        return tools

    @staticmethod
    def _needs(status="action_required", *, actions=None, code="dependencies_missing"):
        return {
            **result(status),
            "reasons": [{"code": code, "message": "fastembed is missing"}],
            "actions": [{"kind": "setup", "argv": ["wf", "setup"]}] if actions is None else actions,
        }

    @staticmethod
    def _codes(response):
        return [d["code"] for d in response.get("diagnostics") or []]

    def test_notice_once_per_result_and_again_for_a_new_result_or_handler(self):
        tools = self._wrap(code_read=lambda: {"status": "ok", "diagnostics": []})
        self.handler._setup_assessment_result = self._needs()
        first = tools["code_read"].fn()
        self.assertEqual(self._codes(first), ["setup_not_ready"])
        message = first["diagnostics"][0]["message"]
        self.assertIn("dependencies_missing", message)
        self.assertIn("wf setup", message)
        self.assertIn("ask before running", message)
        self.assertLessEqual(len(message), self.impl._SETUP_NOTICE_MAX_CHARS)
        self.assertEqual(self._codes(tools["code_read"].fn()), [])
        self.handler._setup_assessment_result = self._needs(code="index_missing")
        self.assertEqual(self._codes(tools["code_read"].fn()), ["setup_not_ready"])
        # A new handler (as after a reload) has not told the agent yet.
        self.handler = types.SimpleNamespace(_setup_assessment_result=self._needs(code="index_missing"))
        self.assertEqual(self._codes(tools["code_read"].fn()), ["setup_not_ready"])

    def test_many_long_reasons_keep_the_command_and_the_ask_first_text(self):
        many = {**self._needs(), "reasons": [
            {"code": f"reason_{index}", "message": "x" * 150} for index in range(7)]}
        message = self.impl.setup_not_ready_diagnostic(many)["message"]
        self.assertLessEqual(len(message), self.impl._SETUP_NOTICE_MAX_CHARS)
        self.assertIn("Recommended: wf setup", message)
        self.assertTrue(message.endswith("ask before running any command."), message)

    def test_a_failed_notice_does_not_consume_the_result(self):
        tools = self._wrap(code_read=lambda: {"status": "ok", "diagnostics": []})
        self.handler._setup_assessment_result = self._needs()
        with patch.object(self.impl, "setup_not_ready_diagnostic", side_effect=ValueError("bad")):
            self.assertEqual(self._codes(tools["code_read"].fn()), [])
        self.assertEqual(self._codes(tools["code_read"].fn()), ["setup_not_ready"])

    def test_only_results_with_an_action_notify(self):
        tools = self._wrap(code_read=lambda: {"status": "ok", "diagnostics": []})
        for quiet in (result("ready"), {**result("indeterminate"), "reasons": [
                {"code": "observation_failed", "message": "index publication is in progress"}]}):
            with self.subTest(status=quiet["status"]):
                self.handler = types.SimpleNamespace(_setup_assessment_result=quiet)
                self.assertEqual(self._codes(tools["code_read"].fn()), [])
        # The post-upgrade restart assesses indeterminate but carries an action.
        self.handler = types.SimpleNamespace(_setup_assessment_result=self._needs(
            "indeterminate", actions=[{"kind": "restart", "argv": []}], code="loaded_code_stale"))
        response = tools["code_read"].fn()
        self.assertEqual(self._codes(response), ["setup_not_ready"])
        self.assertIn("Restart", response["diagnostics"][0]["message"])
        self.assertNotIn("..", response["diagnostics"][0]["message"])

    def test_skips_runner_async_and_index_health_tools_and_never_nests(self):
        async def wf_reload_mcp():
            return {}

        async def some_async():
            return {}

        def index_health():
            return {"status": "ok", "diagnostics": []}

        def code_read():
            return {"status": "ok", "diagnostics": []}

        tools = self._wrap(wf_reload_mcp=wf_reload_mcp, some_async=some_async,
                           index_health=index_health, code_read=code_read)
        self.assertIs(tools["wf_reload_mcp"].fn, wf_reload_mcp)
        self.assertIs(tools["some_async"].fn, some_async)
        self.assertIs(tools["index_health"].fn, index_health)
        wrapped = tools["code_read"].fn
        mcp = types.SimpleNamespace(_tool_manager=types.SimpleNamespace(_tools=tools))
        self.impl._wrap_setup_notice(mcp, lambda: self.handler)  # as on a reload
        self.assertIs(tools["code_read"].fn, wrapped)

    def test_never_changes_the_call_outcome(self):
        original = {"status": "ok", "diagnostics": [{"code": "existing"}]}
        tools = self._wrap(
            code_read=lambda: original,
            code_text=lambda: "plain text",
            code_odd=lambda: {"status": "ok", "diagnostics": "not a list"},
        )
        self.handler._setup_assessment_result = self._needs()
        response = tools["code_read"].fn()
        self.assertEqual(self._codes(response), ["existing", "setup_not_ready"])
        self.assertEqual(original["diagnostics"], [{"code": "existing"}])  # not mutated
        self.assertEqual(tools["code_text"].fn(), "plain text")
        self.assertEqual(tools["code_odd"].fn()["diagnostics"], "not a list")
        # A handler without setup state, or one that cannot be reached, is harmless.
        self.handler = types.SimpleNamespace()
        self.assertEqual(self._codes(tools["code_read"].fn()), ["existing"])
        broken = self._wrap(code_read=lambda: {"status": "ok"})
        with patch.object(self, "handler", None):
            self.assertEqual(broken["code_read"].fn(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()

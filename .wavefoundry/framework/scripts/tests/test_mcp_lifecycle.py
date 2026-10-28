"""Owned MCP lifecycle regressions; subprocesses use a disposable local framework."""
from __future__ import annotations

import asyncio
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

from server_tools_support import SCRIPTS_ROOT, _make_repo, load_server, load_thin_runner


def isolated_env():
    env = os.environ.copy()
    env.pop("PYTHONPYCACHEPREFIX", None)
    env.update(WAVEFOUNDRY_NO_STARTUP_INSTALL="1",
               WAVEFOUNDRY_DISABLE_BYTECODE_CACHE="1",
               PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1",
               TRANSFORMERS_OFFLINE="1")
    return env


class StdioChild:
    """A single owned child and JSON-lines MCP transport, with bounded reap."""

    def __init__(self, root, command):
        self.root = root
        self.stderr = open(root / "child.stderr", "w+b")
        self.child = subprocess.Popen(
            command, cwd=root, env=isolated_env(), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=self.stderr, close_fds=True,
        )
        self.messages = queue.Queue()
        self.ident = 0
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        for line in iter(self.child.stdout.readline, b""):
            try:
                self.messages.put(json.loads(line))
            except Exception:
                self.messages.put({"invalid_stdout": line.decode(errors="replace")})
        self.messages.put({"eof": True})

    def send(self, payload):
        self.child.stdin.write((json.dumps(payload) + "\n").encode())
        self.child.stdin.flush()

    def begin(self, method, params):
        self.ident += 1
        self.send({"jsonrpc": "2.0", "id": self.ident, "method": method, "params": params})
        return self.ident

    def response(self, ident, timeout=30):
        deadline = time.monotonic() + timeout
        while True:
            item = self.messages.get(timeout=max(.01, deadline - time.monotonic()))
            if "invalid_stdout" in item:
                raise AssertionError(f"Non-protocol stdout: {item}")
            if item.get("eof"):
                raise AssertionError("MCP exited before replying: " + self.logs())
            if item.get("id") == ident:
                if "error" in item:
                    raise AssertionError(item["error"])
                return item["result"]

    def initialize(self):
        from mcp.types import LATEST_PROTOCOL_VERSION
        result = self.response(self.begin("initialize", {
            "protocolVersion": LATEST_PROTOCOL_VERSION, "capabilities": {},
            "clientInfo": {"name": "owned-lifecycle-test", "version": "1"},
        }))
        if result["protocolVersion"] != LATEST_PROTOCOL_VERSION:
            raise AssertionError(result)
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def tool(self, name):
        result = self.response(self.begin("tools/call", {"name": name, "arguments": {}}))
        if result.get("isError"):
            raise AssertionError(result)
        value = result.get("structuredContent")
        if value is None:
            value = json.loads(next(c["text"] for c in result["content"] if c["type"] == "text"))
        if value.get("status") == "error":
            raise AssertionError(value)
        return value.get("data", value)

    def logs(self):
        self.stderr.flush()
        self.stderr.seek(0)
        return self.stderr.read().decode(errors="replace")

    def expect_exit(self, timeout=10):
        try:
            code = self.child.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise AssertionError("Owned MCP child did not exit after EOF") from exc
        if code != 0:
            raise AssertionError(f"MCP exit {code}: {self.logs()}")
        self.reader.join(timeout=2)
        if self.reader.is_alive():
            raise AssertionError("MCP stdout reader did not finish")
        while not self.messages.empty():
            item = self.messages.get_nowait()
            if "invalid_stdout" in item:
                raise AssertionError(f"Non-protocol stdout: {item}")

    def close(self):
        # Never enumerate, signal, or stop another process or inference service.
        if self.child.poll() is None:
            self.child.terminate()
            try:
                self.child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.child.kill()
                self.child.wait(timeout=3)
        if not self.child.stdin.closed:
            self.child.stdin.close()
        self.reader.join(timeout=2)
        self.child.stdout.close()
        self.stderr.close()


class McpStdioLifecycleTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="wf-mcp-lifecycle-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        framework = self.root / ".wavefoundry/framework"
        scripts = framework / "scripts"
        shutil.copytree(SCRIPTS_ROOT, scripts,
                        ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
        shutil.copy2(SCRIPTS_ROOT.parent / "VERSION", framework / "VERSION")
        profile = scripts / "inference_profile.py"
        before = profile.read_text(encoding="utf-8")
        self.assertIn('PROVIDER = "tensorwell"', before)
        profile.write_text(before.replace('PROVIDER = "tensorwell"', 'PROVIDER = "local"'), encoding="utf-8")
        (self.root / "docs").mkdir()
        (self.root / "docs/workflow-config.json").write_text(json.dumps({
            "indexing": {"monitor": {"enabled": True, "interval_seconds": 600}},
        }), encoding="utf-8")
        # Real server/build_server/stdio, with two fixture-only tools. No model call.
        wrapper = self.root / "serve_fixture.py"
        wrapper.write_text('''import asyncio
import json
from pathlib import Path
import sys
import threading
sys.path.insert(0, str(Path(__file__).parent / ".wavefoundry/framework/scripts"))
import server
root = Path(__file__).parent.resolve()
mcp = server.build_server(root)
@mcp.tool()
async def wf_fixture_finite_work():
    (root / "work-entered").write_text("entered")
    await asyncio.sleep(.4)
    (root / "work-finished").write_text("finished")
    return {"finished": True}
@mcp.tool()
def wf_fixture_threads():
    return {"monitors": sorted(t.name for t in threading.enumerate() if t.name.startswith("wavefoundry-"))}
server._RELOAD_SURVIVOR_TOOLS = server._RELOAD_SURVIVOR_TOOLS | {"wf_fixture_finite_work", "wf_fixture_threads"}
mcp.run(transport="stdio")
''', encoding="utf-8")
        self.peer = StdioChild(self.root, [sys.executable, "-B", str(wrapper)])
        self.addCleanup(self.peer.close)

    def assert_identity(self, info):
        identity = info["process"]
        self.assertEqual(identity["pid"], self.peer.child.pid)
        self.assertEqual(identity["parent_pid"], os.getpid())
        self.assertEqual(Path(identity["repo_root"]), self.root)
        self.assertGreaterEqual(identity["uptime_seconds"], 0)
        return identity

    def test_stdio_reloads_keep_identity_uptime_workers_and_exit_on_idle_eof(self):
        import psutil
        self.peer.initialize()
        initial = self.assert_identity(self.peer.tool("wf_server_info"))
        workers = self.peer.tool("wf_fixture_threads")["monitors"]
        self.assertEqual(workers.count("wavefoundry-index-monitor"), 1)
        self.assertEqual(workers.count("wavefoundry-ce-projection-monitor"), 1)
        process = psutil.Process(self.peer.child.pid)
        worker_count = process.num_threads()
        for _ in range(3):
            data = self.peer.tool("wf_reload_mcp")
            current = self.assert_identity(data)
            self.assertGreaterEqual(current["uptime_seconds"], initial["uptime_seconds"])
            self.assertEqual(data["reload"], {
                "mode": "in_process", "process_restarted": False,
                "message": "Implementation reloaded; process unchanged.",
            })
            self.assertIn("runner_stale", data)
            self.assertIn("impl_matches_disk", data)
            # A later reload can restore a table stripped by an earlier failed
            # registration. Verify the public surface after EACH transition.
            self.assertGreater(data["tools_reregistered"], 0)
            healthy = self.assert_identity(self.peer.tool("wf_server_info"))
            self.assertGreaterEqual(healthy["uptime_seconds"], current["uptime_seconds"])
            self.assertEqual(process.num_threads(), worker_count)
            initial = current
        self.assert_identity(self.peer.tool("wf_server_info"))
        self.peer.child.stdin.close()
        self.peer.expect_exit()
        self.assertFalse(list((self.root / ".wavefoundry/framework").rglob("__pycache__")))

    def test_stdio_eof_during_entered_finite_work_exits_and_reaps(self):
        self.peer.initialize()
        self.assert_identity(self.peer.tool("wf_server_info"))
        self.peer.begin("tools/call", {"name": "wf_fixture_finite_work", "arguments": {}})
        deadline = time.monotonic() + 10
        while not (self.root / "work-entered").exists():
            self.assertLess(time.monotonic(), deadline, "finite work never entered")
            self.assertIsNone(self.peer.child.poll(), self.peer.logs())
            time.sleep(.01)
        self.assertFalse((self.root / "work-finished").exists(), "work completed before EOF")
        self.peer.child.stdin.close()
        self.peer.expect_exit()

    def test_exit_oracle_rejects_retained_input_and_nonexiting_owned_child(self):
        self.peer.initialize()
        with self.assertRaisesRegex(AssertionError, "did not exit"):
            self.peer.expect_exit(timeout=.15)  # Known bad: input remains open.
        self.peer.child.stdin.close()
        self.peer.expect_exit()
        script = self.root / "nonexiting.py"
        script.write_text("import sys, time\nsys.stdin.read()\ntime.sleep(60)\n", encoding="utf-8")
        bad = StdioChild(self.root, [sys.executable, "-B", str(script)])
        try:
            bad.child.stdin.close()
            with self.assertRaisesRegex(AssertionError, "did not exit"):
                bad.expect_exit(timeout=.15)
        finally:
            bad.close()
        self.assertIsNotNone(bad.child.returncode)


class HandlerCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.impl = load_server()

    def handler(self):
        handler = self.impl.ImplHandler.__new__(self.impl.ImplHandler)
        handler.index = types.SimpleNamespace()
        handler.telemetry = Mock()
        handler.cache = Mock()
        handler._monitor_stop = handler._monitor_thread = None
        handler._ce_projection_stop = handler._ce_projection_thread = None
        return handler

    def test_real_monitor_timeout_retains_reference_reports_and_retries(self):
        for stop_attr, thread_attr, resource in (
            ("_monitor_stop", "_monitor_thread", "index_monitor"),
            ("_ce_projection_stop", "_ce_projection_thread", "ce_projection_monitor"),
        ):
            with self.subTest(resource=resource):
                handler = self.handler()
                released = threading.Event()
                thread = threading.Thread(target=released.wait, daemon=True)
                stop = threading.Event()
                setattr(handler, stop_attr, stop)
                setattr(handler, thread_attr, thread)
                thread.start()
                try:
                    started = time.monotonic()
                    result = handler.close()
                    self.assertLess(time.monotonic() - started, 3)
                    self.assertFalse(result["complete"])
                    self.assertIn({"resource": resource, "reason": "TimeoutError"}, result["warnings"])
                    self.assertIs(getattr(handler, thread_attr), thread)
                    self.assertIs(getattr(handler, stop_attr), stop)
                    self.assertTrue(stop.is_set())
                    handler.telemetry.close.assert_called_once()
                    handler.cache.invalidate.assert_called_once()
                finally:
                    released.set()
                    thread.join(timeout=2)
                self.assertFalse(thread.is_alive())
                self.assertEqual(handler.close(), {"complete": True, "warnings": []})
                self.assertIsNone(getattr(handler, thread_attr))
                self.assertIsNone(getattr(handler, stop_attr))
                self.assertEqual(handler.close(), {"complete": True, "warnings": []})

    def test_independent_cleanup_continues_after_failure(self):
        handler = self.handler()
        handler.telemetry.close.side_effect = OSError("fixture failure")
        handler.index._loaded = True
        result = handler.close()
        self.assertFalse(result["complete"])
        self.assertEqual(result["warnings"], [{"resource": "telemetry", "reason": "OSError"}])
        handler.cache.invalidate.assert_called_once()
        self.assertFalse(handler.index._loaded)
        handler.telemetry.close.side_effect = None
        self.assertTrue(handler.close()["complete"])


class RunnerCleanupTests(unittest.TestCase):
    def setUp(self):
        self.impl = load_server()
        self.runner = load_thin_runner()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = _make_repo(Path(tmp.name))
        self.addCleanup(self._close_handler)

    def _close_handler(self):
        if self.runner._handler is not None:
            self.runner._handler.close()

    def test_lifespan_closes_current_after_real_reload_for_normal_error_and_cancellation(self):
        for failure in (None, RuntimeError("serving failed"), asyncio.CancelledError("cancelled")):
            with self.subTest(failure=type(failure).__name__):
                # Actual reload evicts this module; patch the currently imported
                # provider each time so no subcase starts an inference service.
                provider = importlib.import_module("inference_provider")
                with patch.object(provider, "start_background") as provider_start:
                    mcp = self.runner.build_server(self.root)
                    startup = self.runner._get_handler()
                    with patch.object(startup, "close", wraps=startup.close) as old_close:
                        async def exercise():
                            async with mcp._mcp_server.lifespan(mcp._mcp_server):
                                result = self.runner.perform_mcp_reload()
                                self.assertEqual(result["status"], "ok", result)
                                current = self.runner._get_handler()
                                self.assertIsNot(current, startup)
                                current.close = Mock(wraps=current.close)
                                if failure is not None:
                                    raise failure
                        if failure is None:
                            asyncio.run(exercise())
                        else:
                            with self.assertRaises(type(failure)) as caught:
                                asyncio.run(exercise())
                            self.assertIs(caught.exception, failure)
                        old_close.assert_called_once()
                        self.runner._get_handler().close.assert_called_once()
                        provider_start.assert_called_once_with(self.root)

    def test_lifespan_cleanup_failure_stays_on_stderr_and_preserves_body_error(self):
        import inference_provider
        for cleanup in ({"complete": False, "warnings": [{"resource": "index_monitor", "reason": "TimeoutError"}]},
                        OSError("close failed")):
            for body_error in (RuntimeError("original serving error"), asyncio.CancelledError("cancelled")):
                with self.subTest(cleanup=cleanup, error=type(body_error).__name__):
                    with patch.object(inference_provider, "start_background"):
                        mcp = self.runner.build_server(self.root)
                        handler = self.runner._get_handler()
                        async def exercise():
                            async with mcp._mcp_server.lifespan(mcp._mcp_server):
                                raise body_error
                        output, errors = io.StringIO(), io.StringIO()
                        side = {"side_effect": cleanup} if isinstance(cleanup, Exception) else {"return_value": cleanup}
                        with patch.object(handler, "close", **side) as close, contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                            with self.assertRaises(type(body_error)) as caught:
                                asyncio.run(exercise())
                        self.assertIs(caught.exception, body_error)
                        close.assert_called_once()
                        self.assertEqual(output.getvalue(), "")
                        self.assertTrue(errors.getvalue(), "shutdown failure must be observable")
                        if isinstance(cleanup, dict):
                            self.assertIn("index_monitor", errors.getvalue())
                        handler.close()

    def test_reload_refuses_incomplete_or_raised_cleanup_before_module_or_handler_replacement(self):
        handler = Mock(root=self.root)
        handler.prepare_reload.return_value = {"complete": True, "warnings": []}
        self.runner._set_handler(handler)
        for cleanup in ({"complete": False, "warnings": [{"resource": "index_monitor", "reason": "TimeoutError"}]},
                        TimeoutError("still running")):
            with self.subTest(cleanup=cleanup):
                handler.close.reset_mock(side_effect=True)
                if isinstance(cleanup, Exception):
                    handler.close.side_effect = cleanup
                else:
                    handler.close.return_value = cleanup
                with patch.object(self.runner.importlib, "reload") as reload_module, patch.object(self.impl, "build_handler") as build:
                    result = self.runner.perform_mcp_reload()
                    self.assertEqual(result["status"], "error")
                    self.assertEqual(result["data"]["reload"]["phase"], "cleanup")
                    self.assertFalse(result["data"]["reload"]["handler_preserved"])
                    diagnostics = result["diagnostics"]
                    expected = "handler_close_warning" if isinstance(cleanup, Exception) else "handler_cleanup_incomplete"
                    self.assertIn(expected, {d["code"] for d in diagnostics})
                    if isinstance(cleanup, dict):
                        self.assertIn("index_monitor", json.dumps(diagnostics))
                    reload_module.assert_not_called()
                    build.assert_not_called()
                    self.assertIs(self.runner._get_handler(), handler)
        # Retry may proceed when cleanup finally succeeds; the refused handler was retained.
        handler.close.side_effect = None
        handler.close.return_value = {"complete": True, "warnings": []}
        with patch.object(self.runner.importlib, "reload", return_value=self.impl) as reload_module, patch.object(self.impl, "build_handler", return_value=handler) as build, patch.object(self.runner, "_refresh_mcp_tool_surface", return_value=(0, [], [], [], [])):
            result = self.runner.perform_mcp_reload()
            self.assertEqual(result["status"], "ok", result)
            reload_module.assert_called_once()
            build.assert_called_once_with(self.root)

    def test_registered_preparation_refusal_preserves_workers_resources_and_resumes(self):
        for blocked in ("index_monitor", "ce_projection_monitor"):
            with self.subTest(blocked=blocked):
                entered, release = threading.Event(), threading.Event()
                progress = {name: threading.Event() for name in ("index_monitor", "ce_projection_monitor")}
                calls = dict.fromkeys(progress, 0)

                def callback(name):
                    calls[name] += 1
                    if name == blocked and calls[name] == 1:
                        entered.set()
                        release.wait(10)
                    progress[name].set()
                    return {"reason": "fixture", "triggered": False}

                with patch.object(self.impl, "_read_monitor_config", return_value={"enabled": True, "interval_seconds": .01}), \
                     patch.object(self.impl, "_read_ce_projection_config", return_value={"interval_seconds": .01, "quiet_period_seconds": 120}), \
                     patch.object(self.impl.ImplHandler, "assess_setup", return_value={"status": "ready"}), \
                     patch.object(self.impl, "_maybe_refresh_if_stale", side_effect=lambda *a, **k: callback("index_monitor")), \
                     patch.object(self.impl, "_maybe_project_context_efficiency", side_effect=lambda *a, **k: callback("ce_projection_monitor")):
                    mcp = self.runner.build_server(self.root)
                    handler = self.runner._get_handler()
                    threads = (handler._monitor_thread, handler._ce_projection_thread)
                    stops = (handler._monitor_stop, handler._ce_projection_stop)
                    sentinel = object()
                    handler.index._docs_vector_layer = sentinel
                    try:
                        self.assertTrue(entered.wait(2), "actual callback never entered")
                        with patch.object(handler, "close", wraps=handler.close) as close, \
                             patch.object(handler.telemetry, "close", wraps=handler.telemetry.close) as telemetry_close, \
                             patch.object(handler.cache, "invalidate", wraps=handler.cache.invalidate) as invalidate:
                            started = time.monotonic()
                            _, result = asyncio.run(mcp.call_tool("wf_reload_mcp", {}))
                            self.assertLess(time.monotonic() - started, 4)
                            self.assertEqual(result["status"], "error", result)
                            self.assertEqual(result["data"]["reload"]["phase"], "prepare")
                            self.assertTrue(result["data"]["reload"]["handler_preserved"])
                            self.assertIn(blocked, json.dumps(result["diagnostics"]))
                            self.assertIs(self.runner._get_handler(), handler)
                            self.assertEqual((handler._monitor_thread, handler._ce_projection_thread), threads)
                            self.assertTrue(all(t.is_alive() for t in threads))
                            self.assertFalse(any(s.is_set() for s in stops))
                            self.assertIs(handler.index._docs_vector_layer, sentinel)
                            self.assertFalse(handler._monitors_paused)
                            close.assert_not_called()
                            telemetry_close.assert_not_called()
                            invalidate.assert_not_called()
                            for event in progress.values():
                                event.clear()
                            release.set()
                            self.assertTrue(all(event.wait(2) for event in progress.values()), "ordinary callbacks did not resume")
                            # A further callback from the formerly blocked worker proves
                            # scheduling resumed, not only completion of its old callback.
                            progress[blocked].clear()
                            self.assertTrue(progress[blocked].wait(2))
                            self.assertGreaterEqual(calls[blocked], 2)
                            _, retry = asyncio.run(mcp.call_tool("wf_reload_mcp", {}))
                            self.assertEqual(retry["status"], "ok", retry)
                            self.assertGreater(retry["data"]["tools_reregistered"], 0)
                            _, info = asyncio.run(mcp.call_tool("wf_server_info", {}))
                            self.assertEqual(info["data"]["process"]["pid"], os.getpid())
                            self.assertIsNot(self.runner._get_handler(), handler)
                            self.assertTrue(all(not t.is_alive() for t in threads))
                    finally:
                        release.set()
                        handler.close()
                        self._close_handler()

    def test_preparation_exception_resumes_without_cleanup(self):
        mcp = self.runner.build_server(self.root)
        handler = self.runner._get_handler()
        with patch.object(handler._monitor_condition, "wait_for", side_effect=RuntimeError("fixture wait failed")), \
             patch.object(handler, "close", wraps=handler.close) as close:
            _, result = asyncio.run(mcp.call_tool("wf_reload_mcp", {}))
            self.assertEqual(result["status"], "error", result)
            self.assertEqual(result["data"]["reload"]["phase"], "prepare")
            self.assertFalse(handler._monitors_paused)
            close.assert_not_called()

    def test_pause_blocks_ready_callback_entry_and_shutdown_stops_paused_workers(self):
        # Both real loops reach the interval boundary before preparation. Release
        # that boundary only after preparation succeeds: neither callback may enter.
        ready = [threading.Event(), threading.Event()]
        proceed = threading.Event()
        real_event = threading.Event
        stops = []

        class ControlledStop:
            def __init__(self, i):
                self.event = real_event()
                self.i = i
                self.checked = real_event()

            def wait(self, timeout):
                ready[self.i].set()
                proceed.wait(3)
                if self.checked.is_set():
                    return self.event.wait(timeout)
                self.checked.set()
                return False

            def set(self):
                self.event.set()

        def make_stop():
            stop = ControlledStop(len(stops))
            stops.append(stop)
            return stop

        # Use a real handler, then replace its stopped loops with controlled ticks.
        self.runner.build_server(self.root)
        handler = self.runner._get_handler()
        handler._stop_staleness_monitor()
        handler._stop_ce_projection_monitor()
        with patch.object(self.impl, "_read_monitor_config", return_value={"enabled": True, "interval_seconds": .01}), \
             patch.object(self.impl, "_read_ce_projection_config", return_value={"interval_seconds": .01}), \
             patch.object(handler, "assess_setup") as assess, \
             patch.object(self.impl, "_maybe_refresh_if_stale") as refresh, \
             patch.object(self.impl, "_maybe_project_context_efficiency") as project:
            # Keep Thread's internal Event real while controlling only the two
            # monitor stop Events created by the start methods.
            real_thread = threading.Thread
            def thread_factory(**kwargs):
                with patch.object(threading, "Event", real_event):
                    return real_thread(**kwargs)
            try:
                with patch.object(threading, "Event", side_effect=make_stop), \
                     patch.object(threading, "Thread", side_effect=thread_factory):
                    handler._start_staleness_monitor()
                    handler._start_ce_projection_monitor()
                self.assertTrue(all(e.wait(2) for e in ready))
                self.assertTrue(handler.prepare_reload()["complete"])
                proceed.set()
                self.assertTrue(all(s.checked.wait(2) for s in stops))
                self.assertTrue(handler.close()["complete"])
                assess.assert_not_called()
                refresh.assert_not_called()
                project.assert_not_called()
            finally:
                proceed.set()
                handler.close()


if __name__ == "__main__":
    unittest.main()

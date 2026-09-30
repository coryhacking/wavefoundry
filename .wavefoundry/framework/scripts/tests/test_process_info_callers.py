"""Callers of process_info (ADR 1z9df, wave 1zc7n).

Liveness is reporting only: the OS locks decide. Without psutil every
liveness wrapper reads "not running", so builds and refreshes proceed to the
lock, and dashboard stop keeps the metadata file (the dashboard's lock
carrier) unless its lock is provably free.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import process_info  # noqa: E402
from server_tools_support import _make_repo, load_server  # noqa: E402


def _refuse():
    raise process_info.ProcessInfoUnavailable("fixture: psutil blocked; run `wf setup`")


def _unavailable():
    return patch.object(process_info, "_load", side_effect=_refuse)


def _idle_child(*args: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)", *args],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


class _Repo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True)
        self.srv = load_server()
        import wf_server.index_handlers as index_handlers
        from wf_server import server_impl
        self.h = index_handlers
        self.impl = server_impl

    def child(self, *args):
        proc = _idle_child(*args)
        self.addCleanup(lambda: (proc.kill(), proc.wait()))
        return proc

    def write_state(self, pid, started_at):
        path = self.h._index_build_state_path(self.root, "project")
        path.write_text(json.dumps({"pid": pid, "started_at": started_at, "mode": "update"}), encoding="utf-8")
        return path


class PidReuseTests(_Repo):
    def test_a_process_started_after_the_recorded_start_is_not_the_build(self):
        proc = self.child()
        time.sleep(0.2)
        self.write_state(proc.pid, time.time() - 100)
        self.assertFalse(self.h._index_build_active(self.root, "project"))
        status = self.h.index_build_status_response(self.root)
        self.assertNotEqual(status["data"].get("state"), "running")

    def test_the_recorded_process_is_still_the_build(self):
        proc = self.child()
        self.write_state(proc.pid, time.time())
        self.assertTrue(self.h._index_build_active(self.root, "project"))
        status = self.h.index_build_status_response(self.root)
        self.assertEqual(status["data"].get("state"), "running")
        self.assertEqual(status["data"].get("source"), "foreground")


class UnavailablePsutilBuildPathTests(_Repo):
    def test_index_build_asks_the_lock_first(self):
        proc = self.child()
        state_path = self.write_state(proc.pid, time.time() - 100)
        log_path = self.h._index_build_log_path(self.root, "project")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("running build output\n", encoding="utf-8")
        state_before = state_path.read_text(encoding="utf-8")
        idx = self.impl._indexer_module()
        with _unavailable():
            with idx._index_build_lock(self.index_dir):
                result = self.h.run_index_rebuild(self.root, content="docs")
            self.assertTrue(result["already_running"], result)
            self.assertEqual(log_path.read_text(encoding="utf-8"), "running build output\n")
            self.assertEqual(state_path.read_text(encoding="utf-8"), state_before)
            # Lock free: liveness reads not running, so a build may proceed to the lock.
            self.assertFalse(self.h._index_build_active(self.root, "project"))

    def test_hook_coalesce_and_refresh_reach_the_lock(self):
        proc = self.child("indexer.py", "--root", str(self.root))
        idx = self.impl._indexer_module()
        (self.index_dir / idx.INDEX_BUILD_LOCK_NAME).write_text(
            json.dumps({"pid": proc.pid, "started_at": time.time()}), encoding="utf-8"
        )
        state_path = self.h._background_refresh_state_path(self.root, "project")
        state_path.write_text(json.dumps({"pid": proc.pid, "started_at": time.time() - 100}), encoding="utf-8")
        self.assertTrue(idx.should_coalesce_hook_reindex(self.index_dir))
        with _unavailable():
            self.assertFalse(idx.should_coalesce_hook_reindex(self.index_dir))
            self.assertFalse(self.h._background_refresh_active(state_path))

    def test_monitor_starts_a_refresh_when_psutil_is_unavailable(self):
        with _unavailable(), \
                patch.object(self.impl, "_check_index_writer_current"), \
                patch.object(self.impl, "_index_inputs_stale", return_value=True), \
                patch.object(self.impl, "_start_background_index_refresh", return_value=True) as start:
            self.impl._maybe_refresh_if_stale(self.root)
        start.assert_called_once()

    def test_status_health_and_server_info_report_unavailable_with_wf_setup(self):
        from unittest.mock import MagicMock

        with _unavailable():
            status = self.h.index_build_status_response(self.root)
            index = MagicMock()
            index.root = self.root
            index.docs_health.return_value = {
                "semantic_ready": True, "stale_layers": [], "missing_layers": [], "has_any_index": True,
                "compatible_chunks": True, "readiness_overview": "ready", "project": {"readiness": "current"},
            }
            health = self.h.index_health_response(index)
            info = self.impl.wf_server_info_response(self.root)
        for resp in (status, health, info):
            diags = [d for d in resp.get("diagnostics", []) if d["code"] == "process_info_unavailable"]
            self.assertEqual(len(diags), 1, resp.get("diagnostics"))
            self.assertIn("wf setup", diags[0]["message"])
        self.assertFalse(info["data"]["process_info"]["available"])
        ok = self.impl.wf_server_info_response(self.root)
        self.assertTrue(ok["data"]["process_info"]["available"])
        self.assertNotIn("process_info_unavailable", [d["code"] for d in ok.get("diagnostics", [])])


class DashboardCarrierTests(_Repo):
    def setUp(self):
        super().setUp()
        import dashboard_lib
        import wf_server.dashboard_handlers as dashboard_handlers
        self.dl = dashboard_lib
        self.dh = dashboard_handlers
        self.meta = dashboard_lib.dashboard_metadata_path(self.root)
        self.meta.parent.mkdir(parents=True, exist_ok=True)

    def hold_dashboard_lock(self):
        script = (
            "import sys, time; sys.path.insert(0, sys.argv[1]); import dashboard_lib;"
            "from pathlib import Path\n"
            "with dashboard_lib.dashboard_server_lock(Path(sys.argv[2])):\n"
            "    print('held', flush=True); time.sleep(60)\n"
        )
        holder = subprocess.Popen([sys.executable, "-B", "-c", script, str(SCRIPTS), str(self.root)],
                                  stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)
        self.addCleanup(lambda: (holder.kill(), holder.wait()))
        self.assertEqual(holder.stdout.readline().strip(), "held")
        return holder

    def assert_kept(self, resp, before=None):
        data = resp["data"]
        self.assertIs(data.get("stopped"), False)
        self.assertIs(data.get("already_stopped"), False)
        self.assertTrue(self.meta.exists())
        if before is not None:
            self.assertEqual(self.meta.read_text(encoding="utf-8"), before)
        codes = [d["code"] for d in resp.get("diagnostics", [])]
        self.assertIn("dashboard_lock_unverified", codes)

    def test_held_lock_keeps_the_carrier_and_restart_refuses(self):
        self.hold_dashboard_lock()
        with _unavailable(), patch.object(self.dh, "_dashboard_cmdline_pids", return_value=[]):
            self.assert_kept(self.dh.wf_stop_dashboard_response(self.root))
            with patch.object(self.dh, "wf_start_dashboard_response") as start:
                restart = self.dh.wf_restart_dashboard_response(self.root)
            start.assert_not_called()
        self.assertIs(restart["data"].get("restarted"), False)

    def test_unknown_lock_state_keeps_the_carrier_on_both_branches(self):
        import runtime_lock

        before = json.dumps({"pid": 0, "url": "http://127.0.0.1:1"})
        self.meta.write_text(before, encoding="utf-8")
        refuse = patch.object(runtime_lock.RuntimeFileLock, "acquire",
                              side_effect=runtime_lock.RuntimeLockError(5, "io error"))
        with refuse, patch.object(self.dh, "_dashboard_cmdline_pids", return_value=[]):
            self.assert_kept(self.dh.wf_stop_dashboard_response(self.root), before)
        proc = self.child()
        with refuse, patch.object(self.dh, "_dashboard_cmdline_pids", return_value=[proc.pid]):
            self.assert_kept(self.dh.wf_stop_dashboard_response(self.root), before)

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "read-only carrier needs POSIX and a non-root user")
    def test_read_only_live_carrier_is_kept(self):
        self.hold_dashboard_lock()
        self.meta.chmod(0o444)
        self.addCleanup(self.meta.chmod, 0o644)
        probe = self.dh._clear_dashboard_metadata(self.meta)
        self.assertIsNone(probe.held)
        with _unavailable(), patch.object(self.dh, "_dashboard_cmdline_pids", return_value=[]):
            self.assert_kept(self.dh.wf_stop_dashboard_response(self.root))

    def test_free_lock_clears_the_metadata_and_keeps_the_carrier(self):
        # Review DEL-DASHBOARD-CARRIER-RACE: the carrier is never deleted, so a
        # dashboard that locked it can never be left holding a deleted inode.
        self.meta.write_text(json.dumps({"pid": 0, "url": "http://127.0.0.1:1"}), encoding="utf-8")
        inode = self.meta.stat().st_ino
        with patch.object(self.dh, "_dashboard_cmdline_pids", return_value=[]):
            resp = self.dh.wf_stop_dashboard_response(self.root)
        self.assertIs(resp["data"].get("already_stopped"), True)
        self.assertIs(resp["data"].get("metadata_cleared"), True)
        self.assertEqual(self.meta.stat().st_ino, inode)
        self.assertEqual(self.dl.read_dashboard_metadata(self.root), {})

    def test_after_stop_branch_keeps_the_carrier_inode(self):
        self.meta.write_text(json.dumps({"pid": 0}), encoding="utf-8")
        inode = self.meta.stat().st_ino
        proc = self.child()
        with patch.object(self.dh, "_dashboard_cmdline_pids", return_value=[proc.pid]):
            resp = self.dh.wf_stop_dashboard_response(self.root)
        self.assertIs(resp["data"].get("stopped"), True, resp)
        self.assertEqual(self.meta.stat().st_ino, inode)
        self.assertEqual(self.dl.read_dashboard_metadata(self.root), {})

    def test_a_dashboard_cannot_lock_the_carrier_while_stop_clears_it(self):
        # The interleaving the review reproduced: a dashboard acquiring the
        # lock during cleanup. Stop holds the lock while it writes, so the
        # concurrent holder is refused, and afterwards exactly one holder wins.
        import runtime_lock

        self.meta.write_text(json.dumps({"pid": 0}), encoding="utf-8")
        attempts = []
        real_write = runtime_lock.RuntimeFileLock.write_metadata
        probe_script = (
            "import sys; sys.path.insert(0, sys.argv[1]); import dashboard_lib\n"
            "from pathlib import Path\n"
            "try:\n"
            "    with dashboard_lib.dashboard_server_lock(Path(sys.argv[2])):\n"
            "        print('acquired')\n"
            "except dashboard_lib.DashboardLockBusy:\n"
            "    print('busy')\n"
        )

        def contend(lock_self, payload):
            out = subprocess.run([sys.executable, "-B", "-c", probe_script, str(SCRIPTS), str(self.root)],
                                 capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
            attempts.append(out.stdout.strip())
            return real_write(lock_self, payload)

        with patch.object(runtime_lock.RuntimeFileLock, "write_metadata", contend), \
                patch.object(self.dh, "_dashboard_cmdline_pids", return_value=[]):
            resp = self.dh.wf_stop_dashboard_response(self.root)
        self.assertEqual(attempts, ["busy"])
        self.assertIs(resp["data"].get("already_stopped"), True)
        self.hold_dashboard_lock()
        second = subprocess.run([sys.executable, "-B", "-c", probe_script, str(SCRIPTS), str(self.root)],
                                capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
        self.assertEqual(second.stdout.strip(), "busy")


@unittest.skipIf(os.name == "nt", "POSIX signals")
class TerminateTests(unittest.TestCase):
    def setUp(self):
        load_server()
        import wf_server.dashboard_handlers as dashboard_handlers
        self.dh = dashboard_handlers

    def test_a_zombie_child_is_reaped_before_it_reads_as_stopped(self):
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        deadline = time.time() + 10
        while process_info.is_zombie(child.pid) is not True and time.time() < deadline:
            time.sleep(0.05)
        self.assertTrue(self.dh._terminate_dashboard_pid(child.pid))
        with self.assertRaises(ChildProcessError):
            os.waitpid(child.pid, os.WNOHANG)
        child.returncode = 0

    def test_sigkill_still_escalates_without_psutil(self):
        child = subprocess.Popen(
            [sys.executable, "-c",
             "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print('ready', flush=True); time.sleep(60)"],
            stdout=subprocess.PIPE, text=True,
        )
        self.addCleanup(lambda: child.poll() is None and (child.kill(), child.wait()))
        self.assertEqual(child.stdout.readline().strip(), "ready")
        started = time.monotonic()
        with _unavailable():
            self.assertTrue(self.dh._terminate_dashboard_pid(child.pid))
        # SIGTERM was ignored, so success needed the SIGKILL after the 5 s wait;
        # the helper reaped the child itself, so Popen cannot see the signal.
        self.assertGreaterEqual(time.monotonic() - started, 4.5)
        with self.assertRaises(ProcessLookupError):
            os.kill(child.pid, 0)
        child.returncode = -signal.SIGKILL


class UpgradeLibTimeoutTests(unittest.TestCase):
    def test_a_timed_out_tasklist_counts_as_running(self):
        import upgrade_lib

        with patch.object(upgrade_lib.os, "name", "nt"), \
                patch.object(upgrade_lib, "_run_tree_kill",
                             side_effect=subprocess.TimeoutExpired(["tasklist"], 10)) as run:
            self.assertTrue(upgrade_lib._pid_is_running(4321))
        self.assertEqual(run.call_args.kwargs["timeout"], 10)


class NoSpawnOnStatusTests(_Repo):
    def test_index_build_status_spawns_no_process_query(self):
        proc = self.child()
        self.write_state(proc.pid, time.time())
        (self.index_dir / "background-build.pid").write_text(str(proc.pid), encoding="utf-8")
        import subprocess_util

        spawned: list[str] = []

        def spy(original):
            def wrapper(cmd, *args, **kwargs):
                spawned.append(str(cmd[0]) if isinstance(cmd, (list, tuple)) and cmd else str(cmd))
                return original(cmd, *args, **kwargs)
            return wrapper

        calls = []
        real_pid_state = process_info.pid_state

        def counting(pid):
            calls.append(pid)
            return real_pid_state(pid)

        with patch.object(subprocess, "run", spy(subprocess.run)), \
                patch.object(subprocess, "Popen", spy(subprocess.Popen)), \
                patch.object(subprocess_util, "isolated_run", spy(subprocess_util.isolated_run)), \
                patch.object(subprocess_util, "run_with_tree_kill", spy(subprocess_util.run_with_tree_kill)), \
                patch.object(process_info, "pid_state", side_effect=counting):
            self.h.index_build_status_response(self.root)
        self.assertGreaterEqual(len(calls), 1)
        queries = {"ps", "tasklist", "powershell", "lsof"}
        self.assertFalse([c for c in spawned if Path(c).name.lower().split(".")[0] in queries], spawned)


if __name__ == "__main__":
    unittest.main()

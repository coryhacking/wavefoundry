"""In-process index build lock holds (wave 1za2y, change 1z9yb).

POSIX record locks are released when the holding process closes ANY descriptor
of the locked file, so a status check inside the server must never open the
lock file while the server itself holds it. The oracle here is a second
process that tries to take the lock byte with a raw ``lockf``: it must fail for
as long as the hold lasts.
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from server_tools_support import _make_repo, load_server  # noqa: E402

_PROBE = textwrap.dedent(
    """
    import fcntl, os, sys
    fd = os.open(sys.argv[1], os.O_RDWR)
    try:
        os.lseek(fd, int(sys.argv[2]), os.SEEK_SET)
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, int(sys.argv[2]))
    except OSError:
        print("held")
    else:
        print("free")
    """
)


@unittest.skipIf(os.name == "nt", "POSIX record-lock release semantics")
class InProcessHoldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True)
        self.srv = load_server()
        import wf_server.index_handlers as index_handlers
        from wf_server import server_impl
        self.handlers = index_handlers
        self.server_impl = server_impl
        self.idx = server_impl._indexer_module()
        self.lock_path = self.index_dir / self.idx.INDEX_BUILD_LOCK_NAME

    def other_process_sees(self) -> str:
        out = subprocess.run(
            [sys.executable, "-B", "-c", _PROBE, str(self.lock_path), str(self.idx.INDEX_BUILD_LOCK_SENTINEL)],
            capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL,
        )
        return out.stdout.strip()

    def assert_status_reports_own_hold(self):
        status = self.handlers.index_build_status_response(self.root, layer="project")
        lock = status["data"]["lock"]
        self.assertTrue(lock["held"], lock)
        self.assertEqual(lock["owner_pid"], os.getpid())
        self.assertEqual(self.other_process_sees(), "held")

    def test_fts_rebuild_hold_survives_status_and_monitor(self):
        seen = {}

        def observe(index_dir):
            self.assertEqual(self.other_process_sees(), "held")
            self.assert_status_reports_own_hold()
            # The quiet-period monitor, driven to its lock-metadata read.
            with patch.object(self.server_impl, "_check_index_writer_current"), \
                    patch.object(self.server_impl, "_index_inputs_stale", return_value=True), \
                    patch.object(self.server_impl, "_background_refresh_active", return_value=False), \
                    patch.object(self.server_impl, "_start_background_index_refresh", return_value=False) as start:
                self.server_impl._maybe_refresh_if_stale(self.root)
            seen["monitor_reached_start"] = start.called
            self.assertEqual(self.other_process_sees(), "held")
            seen["observed"] = True
            return {}

        with patch.object(self.idx, "rebuild_derived_chunk_state", side_effect=observe):
            self.handlers.run_index_rebuild(self.root, content="fts")
        self.assertTrue(seen.get("observed"))
        self.assertTrue(seen.get("monitor_reached_start"), "monitor did not reach its metadata read")
        self.assertEqual(self.other_process_sees(), "free")

    def test_index_optimize_hold_survives_status(self):
        seen = {}

        class Store:
            def read_build_state(inner_self, index_dir):
                self.assert_status_reports_own_hold()
                seen["observed"] = True
                return None

        (self.index_dir / self.idx.vector_store.FILENAME).write_bytes(b"")
        with patch.object(self.idx, "_get_index_state_store", return_value=Store()):
            result = self.idx.optimize_index_tables(self.index_dir)
        self.assertIn("error", result)
        self.assertTrue(seen.get("observed"))
        self.assertEqual(self.other_process_sees(), "free")

    def test_second_in_process_acquire_refuses_and_keeps_the_first(self):
        with self.idx._index_build_lock(self.index_dir):
            with patch("builtins.open", side_effect=AssertionError("lock file opened")), \
                    patch.object(self.idx.os, "open", side_effect=AssertionError("lock file opened")):
                with self.assertRaises(self.idx.IndexBuildAlreadyRunning) as raised:
                    with self.idx._index_build_lock(self.index_dir):
                        self.fail("second acquire entered")
            self.assertIn("lock.held", str(raised.exception))
            self.assertEqual(self.other_process_sees(), "held")
        self.assertEqual(self.other_process_sees(), "free")

    def test_a_reader_thread_during_acquire_cannot_release_the_lock(self):
        # Delivery repair: a reader on another thread (the quiet-period
        # monitor) that opened the file between the OS acquire and the
        # registration would release the lock. Start one inside that window.
        import threading

        import runtime_lock

        real_acquire = runtime_lock.RuntimeFileLock.acquire
        seen = {}

        def reader():
            seen["held"] = self.idx._index_build_lock_held(self.index_dir)
            seen["meta"] = self.idx.read_index_build_lock_metadata(self.lock_path)

        def acquire_then_race(lock_self, *args, **kwargs):
            out = real_acquire(lock_self, *args, **kwargs)
            thread = threading.Thread(target=reader)
            thread.start()
            thread.join(0.3)  # an unguarded reader finishes inside the window
            seen["thread"] = thread
            return out

        with patch.object(runtime_lock.RuntimeFileLock, "acquire", acquire_then_race):
            with self.idx._index_build_lock(self.index_dir):
                seen["thread"].join(10)
                self.assertEqual(self.other_process_sees(), "held")
                self.assertEqual(seen["held"], (True, os.getpid()))
                self.assertEqual(seen["meta"]["pid"], os.getpid())
        self.assertEqual(self.other_process_sees(), "free")

    def test_reload_during_a_hold_keeps_it(self):
        with self.idx._index_build_lock(self.index_dir):
            # What wf_reload_mcp does: drop the script cache, reload server_impl.
            self.server_impl._script_cache.clear()
            reloaded = importlib.reload(self.server_impl)
            import wf_server.index_handlers as index_handlers
            fresh_idx = reloaded._load_script("indexer")
            real_open = os.open

            def guarded_open(path, *args, **kwargs):
                if os.fspath(path) == str(self.lock_path):
                    raise AssertionError("lock file opened during a hold")
                return real_open(path, *args, **kwargs)

            with patch.object(os, "open", side_effect=guarded_open):
                lock = index_handlers._index_build_lock_info(self.root)
                self.assertTrue(fresh_idx._index_build_lock_held(self.index_dir)[0])
            self.assertTrue(lock["held"], lock)
            self.assertEqual(lock["owner_pid"], os.getpid())
            self.assertEqual(self.other_process_sees(), "held")
        self.assertEqual(self.other_process_sees(), "free")

    def test_a_refused_acquire_never_replaces_a_held_carrier(self):
        # Delivery repair DEL-F3: a contender that read stale-looking metadata
        # used to unlink the carrier before its own acquire was refused; a
        # third process then locked a fresh file while the first build still
        # held the old inode. Hold the lock from another process on a file
        # whose metadata names a dead pid.
        import json
        import time

        self.lock_path.write_text(json.dumps({"pid": 99999999, "started_at": 0.0}), encoding="utf-8")
        holder = subprocess.Popen(
            [sys.executable, "-B", "-c", textwrap.dedent(
                """
                import fcntl, os, sys, time
                fd = os.open(sys.argv[1], os.O_RDWR)
                os.lseek(fd, int(sys.argv[2]), os.SEEK_SET)
                fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, int(sys.argv[2]))
                print("locked", flush=True)
                time.sleep(60)
                """
            ), str(self.lock_path), str(self.idx.INDEX_BUILD_LOCK_SENTINEL)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        self.addCleanup(lambda: (holder.kill(), holder.wait(timeout=10)))
        self.assertEqual(holder.stdout.readline().strip(), "locked")
        self.assertEqual(self.other_process_sees(), "held")
        inode = self.lock_path.stat().st_ino

        with self.assertRaises(self.idx.IndexBuildAlreadyRunning):
            with self.idx._index_build_lock(self.index_dir):
                self.fail("acquired a lock another process holds")

        self.assertTrue(self.lock_path.exists())
        self.assertEqual(self.lock_path.stat().st_ino, inode)
        self.assertEqual(self.other_process_sees(), "held")

    def test_a_contender_paused_after_classifying_stale_keeps_the_hold(self):
        # DEL-F3 interleaving from the independent review: the contender reads
        # dead-pid metadata, pauses, another thread acquires, the contender
        # resumes and is refused. External exclusion must hold throughout.
        import json
        import threading

        self.lock_path.write_text(json.dumps({"pid": 99999999, "started_at": 0.0}), encoding="utf-8")
        ready, resume, seen = threading.Event(), threading.Event(), {}
        real = self.idx.classify_index_build_lock_owner

        def classify(meta):
            result = real(meta)
            if threading.current_thread().name == "contender":
                ready.set()
                self.assertTrue(resume.wait(10))
            return result

        def contender():
            try:
                with self.idx._index_build_lock(self.index_dir):
                    seen["entered"] = True
            except self.idx.IndexBuildAlreadyRunning:
                seen["refused"] = True

        with patch.object(self.idx, "classify_index_build_lock_owner", classify):
            thread = threading.Thread(target=contender, name="contender")
            thread.start()
            self.assertTrue(ready.wait(10))
            with self.idx._index_build_lock(self.index_dir):
                self.assertEqual(self.other_process_sees(), "held")
                resume.set()
                thread.join(10)
                self.assertTrue(self.lock_path.exists())
                self.assertEqual(self.other_process_sees(), "held")
        self.assertEqual(seen, {"refused": True})
        self.assertEqual(self.other_process_sees(), "free")

    def test_conflict_message_names_lock_held(self):
        message = self.idx.format_index_build_lock_conflict(self.index_dir)
        self.assertIn("lock.held", message)
        self.assertNotIn("inherited", message)
        self.assertNotIn("appears stale", message)


class BackgroundStateNoteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        (self.root / ".wavefoundry" / "index").mkdir(parents=True)
        load_server()
        import wf_server.index_handlers as index_handlers
        self.handlers = index_handlers

    def status_with_lock(self, held):
        with patch.object(self.handlers, "_background_build_status", return_value="running"), \
                patch.object(self.handlers, "_index_build_lock_info", return_value={"held": held}):
            return self.handlers.index_build_status_response(self.root, layer="project")["data"]

    def test_running_background_without_the_lock_carries_a_note(self):
        data = self.status_with_lock(False)
        self.assertEqual(data["state"], "running")
        self.assertEqual(data["source"], "background")
        self.assertIn("lock.held is authoritative", data["state_note"])

    def test_running_background_holding_the_lock_has_no_note(self):
        self.assertNotIn("state_note", self.status_with_lock(True))


if __name__ == "__main__":
    unittest.main()

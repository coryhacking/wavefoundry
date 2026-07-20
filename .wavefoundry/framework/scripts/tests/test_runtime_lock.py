"""Executable contracts for the shared dedicated runtime-lock engine."""
from __future__ import annotations

import json
import errno
import ast
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import runtime_lock as rl  # noqa: E402
import context_efficiency as ce  # noqa: E402
import dashboard_lib  # noqa: E402
import indexer  # noqa: E402
import review_evidence  # noqa: E402


class RuntimeFileLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_creator_lazily_creates_missing_parent_and_carrier_persists(self) -> None:
        path = self.root / ".wavefoundry" / "locks" / "nested" / "worker.lock"
        self.assertFalse(path.parent.exists())
        with rl.RuntimeFileLock(path):
            self.assertTrue(path.is_file())
        self.assertTrue(path.is_file())

    def test_nonblocking_contention_is_typed_and_probe_is_three_state(self) -> None:
        path = self.root / "locks" / "contended.lock"
        first = rl.RuntimeFileLock(path).acquire()
        try:
            with self.assertRaises(rl.RuntimeLockBusy):
                rl.RuntimeFileLock(path).acquire()
            self.assertEqual(rl.probe_runtime_lock(path), rl.RuntimeLockProbe(True))
        finally:
            first.release()
        self.assertEqual(rl.probe_runtime_lock(path), rl.RuntimeLockProbe(False))

    def test_metadata_rewrite_keeps_inode_and_valid_json(self) -> None:
        path = self.root / "locks" / "metadata.lock"
        lock = rl.RuntimeFileLock(path, offset=1 << 20).acquire()
        try:
            lock.write_metadata({"pid": 1, "phase": "start"})
            inode = path.stat().st_ino
            rl.write_json_in_place(path, {"pid": 1, "phase": "ready"})
            self.assertEqual(path.stat().st_ino, inode)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"pid": 1, "phase": "ready"},
            )
        finally:
            lock.release()

    def test_open_failure_is_not_misreported_as_busy_or_unlocked(self) -> None:
        blocker = self.root / "not-a-directory"
        blocker.write_text("x", encoding="utf-8")
        path = blocker / "child.lock"
        with self.assertRaises(rl.RuntimeLockError):
            rl.RuntimeFileLock(path).acquire()
        probe = rl.probe_runtime_lock(path, create=True)
        self.assertIsNone(probe.held)
        self.assertTrue(probe.error)

    def test_windows_byte_zero_is_initialized_and_sentinel_is_preserved(self) -> None:
        calls: list[tuple[int, int, int]] = []
        fake = types.SimpleNamespace(
            LK_NBLCK=10,
            LK_LOCK=11,
            LK_UNLCK=12,
            locking=lambda fd, mode, length: calls.append((mode, length, fd)),
        )
        zero_path = self.root / "locks" / "zero.lock"
        sentinel_path = self.root / "locks" / "sentinel.lock"
        with patch.object(rl.os, "name", "nt"), patch.dict(
            sys.modules, {"msvcrt": fake}
        ):
            with rl.RuntimeFileLock(zero_path):
                pass
            with rl.RuntimeFileLock(sentinel_path, offset=1 << 30):
                pass
        self.assertEqual(zero_path.read_bytes()[:1], b"\0")
        self.assertEqual(sentinel_path.stat().st_size, 0)
        self.assertEqual([mode for mode, _length, _fd in calls], [10, 12, 10, 12])

    def test_windows_non_contention_error_is_not_misreported_as_busy(self) -> None:
        def fail(_fd, _mode, _length):
            raise OSError(errno.EIO, "device failure")

        fake = types.SimpleNamespace(
            LK_NBLCK=10,
            LK_LOCK=11,
            LK_UNLCK=12,
            locking=fail,
        )
        path = self.root / "locks" / "broken.lock"
        with patch.object(rl.os, "name", "nt"), patch.dict(
            sys.modules, {"msvcrt": fake}
        ):
            with self.assertRaises(rl.RuntimeLockError) as raised:
                rl.RuntimeFileLock(path).acquire()
        self.assertNotIsInstance(raised.exception, rl.RuntimeLockBusy)

    @unittest.skipIf(os.name == "nt", "POSIX release-failure fixture")
    def test_probe_reports_release_failure_as_unknown(self) -> None:
        import fcntl

        path = self.root / "locks" / "probe.lock"
        with patch.object(
            fcntl,
            "flock",
            side_effect=(None, OSError(errno.EIO, "unlock failed")),
        ):
            probe = rl.probe_runtime_lock(path, create=True)
        self.assertIsNone(probe.held)
        self.assertIn("unlock failed", probe.error or "")

    def test_resource_wrappers_create_only_canonical_paths_from_absent_directory(self) -> None:
        locks = self.root / ".wavefoundry" / "locks"
        self.assertFalse(locks.exists())

        with dashboard_lib.dashboard_start_lock(self.root):
            pass
        with dashboard_lib.dashboard_server_lock(self.root):
            pass
        with review_evidence._adoption_write_lock(self.root):
            pass
        producer = ce.producer_lease_path(self.root, "producer")
        handle, acquired = ce._try_lock_lease(producer, create=True)
        self.assertTrue(acquired)
        ce._unlock_lease(handle)

        self.assertEqual(
            dashboard_lib.dashboard_lock_path(
                self.root, dashboard_lib.DASHBOARD_START_LOCK_NAME
            ),
            locks / "dashboard-start.lock",
        )
        self.assertEqual(
            dashboard_lib.dashboard_metadata_path(self.root),
            locks / "dashboard-server.lock",
        )
        self.assertEqual(
            self.root / review_evidence.ADOPTION_LOCK_REL,
            locks / "review-evidence-adoptions.lock",
        )
        self.assertEqual(producer, locks / "producers" / "producer.lock")
        self.assertEqual(
            self.root / ".wavefoundry" / "index" / indexer.INDEX_BUILD_LOCK_NAME,
            self.root / ".wavefoundry" / "index" / "index-build.lock",
        )

    def test_runtime_lock_mechanics_have_one_steady_state_authority(self) -> None:
        consumers = (
            "dashboard_lib.py",
            "context_efficiency.py",
            "review_evidence.py",
        )
        for name in consumers:
            source = (SCRIPTS_DIR / name).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imported = {
                alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            }
            self.assertTrue(
                "runtime_lock" in source,
                f"{name} must delegate lock mechanics to runtime_lock",
            )
            self.assertTrue(
                {"fcntl", "msvcrt"}.isdisjoint(imported),
                f"{name} reintroduced raw platform lock mechanics",
            )

        # The indexer's F_GETLK holder-PID query is deliberate resource policy,
        # not duplicated acquire/release machinery.
        index_source = (SCRIPTS_DIR / "indexer.py").read_text(encoding="utf-8")
        self.assertEqual(index_source.count("import fcntl"), 1)
        self.assertIn("fcntl.F_GETLK", index_source)
        self.assertIn("RuntimeFileLock", index_source)

    def test_steady_state_sources_do_not_reference_pre_cutover_paths(self) -> None:
        old_paths = (
            ".wavefoundry/review-evidence-adoptions.lock",
            ".wavefoundry/dashboard-start.lock",
            ".wavefoundry/dashboard-server.lock",
            ".wavefoundry/logs/context-efficiency-producers",
        )
        for name in (
            "dashboard_lib.py",
            "context_efficiency.py",
            "review_evidence.py",
            "server_impl.py",
            "indexer.py",
        ):
            source = (SCRIPTS_DIR / name).read_text(encoding="utf-8")
            for old_path in old_paths:
                self.assertNotIn(old_path, source, f"{name}: {old_path}")


if __name__ == "__main__":
    unittest.main()

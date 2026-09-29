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
from framework_files import source_path  # wf_server-aware source locations (wave 1yzd0)

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

    @unittest.skipUnless(hasattr(os, "symlink") and os.name != "nt", "POSIX symlink fixture")
    def test_symlinked_carriers_are_refused_and_their_targets_untouched(self) -> None:
        # Wave 1z822: a committed symlink at a lock path must never redirect a write.
        victim = self.root / "victim.txt"
        victim.write_bytes(b"keep me\n")
        locks = self.root / "locks"
        locks.mkdir()
        linked = locks / "linked.lock"
        linked.symlink_to(victim)
        with self.assertRaises(rl.RuntimeLockError) as caught:
            rl.RuntimeFileLock(linked).acquire()
        self.assertIn("symlink", str(caught.exception))
        self.assertIn(str(linked), str(caught.exception))
        with self.assertRaises(rl.RuntimeLockError):
            rl.write_json_in_place(linked, {"pid": 1})
        self.assertEqual(victim.read_bytes(), b"keep me\n")
        dangling = locks / "dangling.lock"
        missing = self.root / "created-through-link.txt"
        dangling.symlink_to(missing)
        with self.assertRaises(rl.RuntimeLockError):
            rl.write_json_in_place(dangling, {"pid": 1})
        with self.assertRaises(rl.RuntimeLockError):
            rl.RuntimeFileLock(dangling).acquire()
        self.assertFalse(missing.exists())
        # Ordinary and missing carriers behave as before.
        fresh = locks / "fresh.json"
        rl.write_json_in_place(fresh, {"pid": 2})
        self.assertEqual(json.loads(fresh.read_text(encoding="utf-8")), {"pid": 2})
        with rl.RuntimeFileLock(locks / "fresh.lock"):
            pass

    def test_windows_branch_refuses_only_links_and_junctions(self) -> None:
        ordinary = self.root / "ordinary.lock"
        ordinary.write_bytes(b"")
        tags = {"symlink.lock": 0xA000000C, "junction.lock": 0xA0000003,
                "onedrive.lock": 0x9000001A, "dedup.lock": 0x80000013}
        for name in tags:
            (self.root / name).write_bytes(b"")
        real_lstat = os.lstat

        def fake_lstat(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            # Python 3.11 cannot build a WindowsPath under a patched os.name.
            tag = tags.get(os.path.basename(os.fspath(path)))
            if tag is not None:
                return types.SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400, st_reparse_tag=tag)
            return info

        with patch.object(rl.os, "name", "nt"), patch.object(rl.os, "lstat", side_effect=fake_lstat):
            for refused in ("symlink.lock", "junction.lock"):
                with self.subTest(refused=refused), self.assertRaises(OSError):
                    rl._open_carrier(self.root / refused, "a+b")
            # Cloud-file placeholders and deduplicated files are reparse points but not links.
            for allowed in ("onedrive.lock", "dedup.lock"):
                rl._open_carrier(self.root / allowed, "a+b").close()
            rl._open_carrier(ordinary, "a+b").close()
            rl._open_carrier(self.root / "new.lock", "r+b").close()
        self.assertTrue((self.root / "new.lock").exists())

    @unittest.skipUnless(hasattr(os, "symlink") and os.name != "nt", "POSIX symlink fixture")
    def test_symlinked_lock_directories_are_refused_and_nothing_is_created_outside(self) -> None:
        # Wave 1z8ot (1z8oq): makedirs followed a committed directory link, so
        # every lock and metadata rewrite landed outside the repository.
        both = (("locks", "x.lock"), ("locks", "sub", "x.lock"))
        cases = {
            "locks-link": ((".wavefoundry", "locks"), both),
            "state-link": ((".wavefoundry",), both),
            "nested-link": ((".wavefoundry", "locks", "sub"), both[1:]),
        }
        for label, (linked_parts, rels) in cases.items():
            with self.subTest(label=label):
                repo = self.root / label / "repo"
                outside = self.root / label / "outside"
                outside.mkdir(parents=True)
                link = repo.joinpath(*linked_parts)
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(outside, target_is_directory=True)
                for rel in rels:
                    path = repo.joinpath(".wavefoundry", *rel)
                    with self.assertRaises(rl.RuntimeLockError) as caught:
                        rl.RuntimeFileLock(path).acquire()
                    self.assertIn("replace it with a real directory", str(caught.exception))
                    with self.assertRaises(rl.RuntimeLockError):
                        rl.write_json_in_place(path, {"pid": 1})
                    self.assertIsNone(rl.probe_runtime_lock(path, create=True).held)
                self.assertEqual(list(outside.iterdir()), [])

        # A dangling directory link is refused without creating its target.
        repo = self.root / "dangling" / "repo"
        (repo / ".wavefoundry").mkdir(parents=True)
        missing = self.root / "dangling" / "missing-dir"
        (repo / ".wavefoundry" / "locks").symlink_to(missing, target_is_directory=True)
        with self.assertRaises(rl.RuntimeLockError):
            rl.RuntimeFileLock(repo / ".wavefoundry" / "locks" / "x.lock").acquire()
        with self.assertRaises(rl.RuntimeLockError):
            rl.write_json_in_place(repo / ".wavefoundry" / "locks" / "x.lock", {"pid": 1})
        self.assertFalse(os.path.lexists(missing))

    @unittest.skipIf(os.name == "nt", "POSIX dir_fd fixture")
    def test_concurrent_create_spurious_enoent_is_retried(self) -> None:
        # macOS returns ENOENT to the loser of two concurrent O_CREAT openat
        # calls; a bounded retry finds the file, and a persistent ENOENT fails.
        real_open = os.open
        failures = {"left": 1}

        def flaky_open(path, flags, *args, **kwargs):
            if kwargs.get("dir_fd") is not None and flags & os.O_CREAT and failures["left"]:
                failures["left"] -= 1
                raise FileNotFoundError(errno.ENOENT, "spurious", path)
            return real_open(path, flags, *args, **kwargs)

        path = self.root / ".wavefoundry" / "locks" / "raced.lock"
        with patch.object(rl.os, "open", side_effect=flaky_open):
            with rl.RuntimeFileLock(path):
                pass
            self.assertEqual(failures["left"], 0)
            failures["left"] = rl._OPEN_AT_ATTEMPTS
            with self.assertRaises(rl.RuntimeLockError):
                rl.RuntimeFileLock(self.root / ".wavefoundry" / "locks" / "gone.lock").acquire()

    def test_full_path_open_without_boundary_retries_spurious_enoent(self) -> None:
        # Delivery finding DEL-F2: the spurious ENOENT was reproduced only with
        # openat(dir_fd); a lock path with no .wavefoundry component (opened by
        # full path) retries it defensively, and this pins that it does.
        real_open = os.open
        failures = {"left": 1}
        seen: list[bool] = []

        def flaky_open(path, flags, *args, **kwargs):
            if flags & os.O_CREAT and failures["left"]:
                seen.append(kwargs.get("dir_fd") is None)
                failures["left"] -= 1
                raise FileNotFoundError(errno.ENOENT, "spurious", path)
            return real_open(path, flags, *args, **kwargs)

        path = self.root / "scratch" / "no-boundary.lock"
        with patch.object(rl.os, "open", side_effect=flaky_open):
            with rl.RuntimeFileLock(path):
                pass
            self.assertEqual(seen, [True])
            self.assertTrue(path.is_file())
            rl.write_json_in_place(self.root / "scratch" / "meta.json", {"pid": 1})
            failures["left"] = rl._OPEN_AT_ATTEMPTS
            with self.assertRaises(rl.RuntimeLockError):
                rl.RuntimeFileLock(self.root / "scratch" / "gone.lock").acquire()
        self.assertTrue((self.root / "scratch" / "meta.json").is_file())

    def test_parent_component_below_boundary_is_refused_with_accurate_message(self) -> None:
        path = Path(os.path.join(os.fspath(self.root), ".wavefoundry", "locks", "..", "x.lock"))
        with self.assertRaises(rl.RuntimeLockError) as caught:
            rl.RuntimeFileLock(path).acquire()
        self.assertIn("contains a .. component below .wavefoundry", str(caught.exception))
        self.assertNotIn("leaves .wavefoundry", str(caught.exception))

    @unittest.skipUnless(hasattr(os, "symlink") and os.name != "nt", "POSIX symlink fixture")
    def test_links_above_the_boundary_and_paths_without_it_are_unchanged(self) -> None:
        real = self.root / "real-checkout"
        real.mkdir()
        checkout = self.root / "linked-checkout"
        checkout.symlink_to(real, target_is_directory=True)
        # The repository root above .wavefoundry may be a link; .wavefoundry is
        # created when missing and used.
        path = checkout / ".wavefoundry" / "locks" / "nested" / "worker.lock"
        with rl.RuntimeFileLock(path) as lock:
            lock.write_metadata({"pid": 1})
        rl.write_json_in_place(path, {"pid": 2})
        self.assertTrue((real / ".wavefoundry").is_dir())
        self.assertEqual(
            json.loads((real / ".wavefoundry/locks/nested/worker.lock").read_text(encoding="utf-8")),
            {"pid": 2},
        )
        # With no .wavefoundry component only the final component is checked.
        scratch = self.root / "scratch-target"
        scratch.mkdir()
        (self.root / "scratch").symlink_to(scratch, target_is_directory=True)
        with rl.RuntimeFileLock(self.root / "scratch" / "tmp.lock"):
            pass
        rl.write_json_in_place(self.root / "scratch" / "tmp.json", {"pid": 3})
        self.assertTrue((scratch / "tmp.lock").is_file())
        self.assertTrue((scratch / "tmp.json").is_file())

    def test_windows_branch_refuses_junctioned_directories_only(self) -> None:
        # Wave 1z8ot (1z8oq): Windows has no openat, so each directory under
        # .wavefoundry is checked with lstat before it is created or opened.
        tags = {"junction-dir": 0xA0000003, "symlink-dir": 0xA000000C,
                "onedrive-dir": 0x9000001A}
        state = self.root / ".wavefoundry"
        for name in tags:
            (state / name).mkdir(parents=True)
        real_lstat = os.lstat

        def fake_lstat(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            tag = tags.get(os.path.basename(os.fspath(path)))
            if tag is not None:
                return types.SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400, st_reparse_tag=tag)
            return info

        with patch.object(rl.os, "name", "nt"), patch.object(rl.os, "lstat", side_effect=fake_lstat):
            for refused in ("junction-dir", "symlink-dir"):
                with self.subTest(refused=refused):
                    with self.assertRaises(rl.RuntimeLockError) as caught:
                        rl.RuntimeFileLock(state / refused / "sub" / "x.lock").acquire()
                    self.assertIn(refused, str(caught.exception))
                    self.assertFalse((state / refused / "sub").exists())
                    with self.assertRaises(rl.RuntimeLockError):
                        rl.write_json_in_place(state / refused / "x.lock", {"pid": 1})
                    self.assertEqual(list((state / refused).iterdir()), [])
            # A OneDrive directory is a reparse point but not a name surrogate.
            rl._open_lock_carrier(state / "onedrive-dir" / "sub" / "x.lock", "a+b").close()
            rl.write_json_in_place(state / "onedrive-dir" / "meta.json", {"pid": 1})
        self.assertTrue((state / "onedrive-dir" / "sub" / "x.lock").is_file())
        self.assertTrue((state / "onedrive-dir" / "meta.json").is_file())

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

    def _held_then_free(self, busy_attempts: int):
        calls: list[tuple[int, int]] = []

        def locking(fd, mode, length):
            calls.append((mode, fd))
            if mode == 10 and sum(1 for m, _ in calls if m == 10) <= busy_attempts:
                raise OSError(errno.EACCES, "locked by another process")

        return calls, types.SimpleNamespace(LK_NBLCK=10, LK_LOCK=11, LK_UNLCK=12, locking=locking)

    def test_windows_blocking_lock_waits_past_ten_seconds_of_contention(self) -> None:
        # Wave 1z2m8: LK_LOCK gave up after ten one-second tries; POSIX waits.
        calls, fake = self._held_then_free(busy_attempts=250)
        path = self.root / "locks" / "busy.lock"
        with patch.object(rl.os, "name", "nt"), patch.dict(sys.modules, {"msvcrt": fake}), \
             patch.object(rl.time, "sleep") as sleep:
            with rl.RuntimeFileLock(path, blocking=True):
                pass
        modes = [mode for mode, _fd in calls]
        self.assertNotIn(11, modes)  # never LK_LOCK
        self.assertEqual(modes.count(10), 251)
        self.assertEqual(sleep.call_count, 250)
        self.assertGreater(sleep.call_count * rl._WINDOWS_LOCK_POLL_SECONDS, 10)

    def test_windows_non_blocking_lock_still_fails_at_once(self) -> None:
        calls, fake = self._held_then_free(busy_attempts=5)
        path = self.root / "locks" / "busy.lock"
        with patch.object(rl.os, "name", "nt"), patch.dict(sys.modules, {"msvcrt": fake}), \
             patch.object(rl.time, "sleep") as sleep:
            with self.assertRaises(rl.RuntimeLockBusy):
                rl.RuntimeFileLock(path).acquire()
        self.assertEqual([mode for mode, _fd in calls], [10])
        sleep.assert_not_called()

    def test_windows_blocking_lock_does_not_retry_a_real_error(self) -> None:
        def fail(_fd, _mode, _length):
            raise OSError(errno.EIO, "device failure")

        fake = types.SimpleNamespace(LK_NBLCK=10, LK_LOCK=11, LK_UNLCK=12, locking=fail)
        path = self.root / "locks" / "broken.lock"
        with patch.object(rl.os, "name", "nt"), patch.dict(sys.modules, {"msvcrt": fake}), \
             patch.object(rl.time, "sleep") as sleep:
            with self.assertRaises(rl.RuntimeLockError) as raised:
                rl.RuntimeFileLock(path, blocking=True).acquire()
        self.assertNotIsInstance(raised.exception, rl.RuntimeLockBusy)
        sleep.assert_not_called()

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
        with review_evidence.project_state_publication_lock(self.root):
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
            self.root / review_evidence.PROJECT_STATE_PUBLICATION_LOCK_REL,
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
            source = source_path(name).read_text(encoding="utf-8")
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
            source = source_path(name).read_text(encoding="utf-8")
            for old_path in old_paths:
                self.assertNotIn(old_path, source, f"{name}: {old_path}")


if __name__ == "__main__":
    unittest.main()

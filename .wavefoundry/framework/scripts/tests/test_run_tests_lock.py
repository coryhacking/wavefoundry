"""Tests for the run-lock helpers in run_tests.py (wave 1p9j0, F16).

The run lock must be portable to native Windows, where ``fcntl`` does not exist.
These tests simulate a Windows host by patching ``os.name`` to ``"nt"`` and
injecting a stub ``msvcrt`` into ``sys.modules``, so the Windows locking path is
exercised without a real Windows host. The POSIX mutual-exclusion behavior (the
"already running" busy diagnostic) is verified directly on the host it runs on.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parent.parent

# Load run_tests as a module (it is a script, not a package member).
_spec = importlib.util.spec_from_file_location("run_tests", SCRIPTS_DIR / "run_tests.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
run_tests = _mod


class _StubMsvcrt:
    """Minimal stand-in for the ``msvcrt`` module used by the Windows lock path.

    Records every ``locking`` call and never raises, simulating a successful
    non-blocking acquire/release. Attribute values are arbitrary sentinels — the
    lock helpers reference them by attribute name (``LK_NBLCK`` / ``LK_UNLCK``).
    """

    LK_NBLCK = 2
    LK_UNLCK = 0

    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int]] = []

    def locking(self, fileno: int, mode: int, nbytes: int) -> None:
        self.calls.append((fileno, mode, nbytes))


class RunLockWindowsPathTests(unittest.TestCase):
    """The lock helpers select the Windows ``msvcrt`` path under a simulated nt host."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_lock_file = run_tests._LOCK_FILE
        run_tests._LOCK_FILE = self.tmp / "test-run.lock"

    def tearDown(self) -> None:
        run_tests._LOCK_FILE = self._orig_lock_file
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_acquire_uses_msvcrt_on_windows(self):
        """_acquire_run_lock imports msvcrt (no ImportError) and locks the sentinel byte."""
        stub = _StubMsvcrt()
        with patch.dict(sys.modules, {"msvcrt": stub}), \
                patch.object(run_tests.os, "name", "nt"):
            lock_file, diag = run_tests._acquire_run_lock()
        self.assertIsNone(diag)
        self.assertIsNotNone(lock_file)
        try:
            # Exactly the non-blocking acquire on a single sentinel byte.
            self.assertEqual(len(stub.calls), 1)
            _fileno, mode, nbytes = stub.calls[0]
            self.assertEqual(mode, stub.LK_NBLCK)
            self.assertEqual(nbytes, 1)
        finally:
            lock_file.close()

    def test_release_uses_msvcrt_on_windows(self):
        """_release_run_lock unlocks the sentinel byte via msvcrt without ImportError."""
        stub = _StubMsvcrt()
        with patch.dict(sys.modules, {"msvcrt": stub}), \
                patch.object(run_tests.os, "name", "nt"):
            lock_file, diag = run_tests._acquire_run_lock()
            self.assertIsNone(diag)
            run_tests._release_run_lock(lock_file)
        modes = [mode for _fileno, mode, _nbytes in stub.calls]
        self.assertIn(stub.LK_NBLCK, modes)  # acquire
        self.assertIn(stub.LK_UNLCK, modes)  # release

    def test_windows_acquire_release_roundtrip_no_import_error(self):
        """A full acquire→release cycle on a simulated nt host raises no ImportError."""
        stub = _StubMsvcrt()
        with patch.dict(sys.modules, {"msvcrt": stub}), \
                patch.object(run_tests.os, "name", "nt"):
            try:
                lock_file, diag = run_tests._acquire_run_lock()
                self.assertIsNone(diag)
                run_tests._release_run_lock(lock_file)
            except ImportError as exc:  # pragma: no cover - regression guard for fcntl import
                self.fail(f"Windows lock path raised ImportError: {exc}")

    def test_windows_busy_lock_reports_already_running(self):
        """A contended msvcrt lock (OSError from locking) maps to the busy diagnostic."""

        class _BusyMsvcrt(_StubMsvcrt):
            def locking(self, fileno: int, mode: int, nbytes: int) -> None:
                super().locking(fileno, mode, nbytes)
                raise OSError(36, "Resource deadlock avoided")

        stub = _BusyMsvcrt()
        with patch.dict(sys.modules, {"msvcrt": stub}), \
                patch.object(run_tests.os, "name", "nt"):
            lock_file, busy = run_tests._acquire_run_lock()
        self.assertIsNone(lock_file)
        self.assertIsNotNone(busy)
        self.assertIn("already running", busy)


class RunFileEncodingTests(unittest.TestCase):
    """_run_file pins UTF-8 on the worker capture and the child env (wave 1p9j0, F13)."""

    def test_run_file_capture_and_child_env_are_utf8(self):
        recorded = {}

        def fake_run(cmd, **kwargs):
            recorded.update(kwargs)

            class _R:
                stdout = "Ran 3 tests in 0.001s\nOK\n"
                stderr = ""
                returncode = 0

            return _R()

        # Scrub ambient UTF-8 vars so the assertions bind the utf8_child_env call itself, not a
        # host shell that happens to export them (delta-review advisory).
        scrubbed = {k: v for k, v in os.environ.items()
                    if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
        with patch.dict(os.environ, scrubbed, clear=True), \
                patch.object(run_tests.subprocess, "run", side_effect=fake_run):
            name, rc, output, count = run_tests._run_file(Path("test_example.py"))
        self.assertEqual(rc, 0)
        self.assertEqual(count, 3)
        self.assertEqual(recorded.get("encoding"), "utf-8")
        self.assertEqual(recorded.get("errors"), "replace")
        env = recorded.get("env") or {}
        self.assertEqual(env.get("PYTHONUTF8"), "1")
        # An inherited PYTHONIOENCODING=cp1252 would win over PYTHONUTF8 in the child;
        # utf8_child_env overrides it unconditionally.
        self.assertEqual(env.get("PYTHONIOENCODING"), "utf-8")


@unittest.skipIf(os.name == "nt", "POSIX fcntl mutual-exclusion path")
class RunLockPosixMutualExclusionTests(unittest.TestCase):
    """On POSIX, a second concurrent acquire returns the busy diagnostic (unchanged)."""

    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_lock_file = run_tests._LOCK_FILE
        run_tests._LOCK_FILE = self.tmp / "test-run.lock"

    def tearDown(self) -> None:
        run_tests._LOCK_FILE = self._orig_lock_file
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_second_acquire_reports_busy(self):
        first, diag = run_tests._acquire_run_lock()
        self.assertIsNone(diag)
        self.assertIsNotNone(first)
        try:
            second, busy = run_tests._acquire_run_lock()
            self.assertIsNone(second)
            self.assertIsNotNone(busy)
            self.assertIn("already running", busy)
        finally:
            run_tests._release_run_lock(first)


if __name__ == "__main__":
    unittest.main()


class SuiteIndexerExclusionTests(unittest.TestCase):
    """Wave 1t72b (1t727): mutual exclusion between the suite and the project
    index build, both directions, bounded, never lost."""

    def setUp(self) -> None:
        self._orig_wait = run_tests._INDEX_BUILD_WAIT_SECONDS
        self._orig_poll = run_tests._INDEX_BUILD_POLL_SECONDS
        self._orig_probe = run_tests._INDEX_BUILD_PROBE

    def tearDown(self) -> None:
        run_tests._INDEX_BUILD_WAIT_SECONDS = self._orig_wait
        run_tests._INDEX_BUILD_POLL_SECONDS = self._orig_poll
        run_tests._INDEX_BUILD_PROBE = self._orig_probe

    def test_suite_waits_for_running_build_then_proceeds(self):
        states = iter([(True, 4242), (True, 4242), (False, None)])
        run_tests._INDEX_BUILD_PROBE = lambda index_dir: next(states)
        run_tests._INDEX_BUILD_POLL_SECONDS = 0.01
        self.assertIsNone(run_tests._wait_for_index_build())

    def test_suite_times_out_with_holder_naming_diagnostic(self):
        run_tests._INDEX_BUILD_PROBE = lambda index_dir: (True, 4242)
        run_tests._INDEX_BUILD_WAIT_SECONDS = 0.05
        run_tests._INDEX_BUILD_POLL_SECONDS = 0.01
        message = run_tests._wait_for_index_build()
        self.assertIsNotNone(message)
        self.assertIn("4242", message)
        self.assertIn("index-build.lock", message)

    def test_probe_failure_never_blocks_the_runner(self):
        def broken(index_dir):
            raise RuntimeError("probe exploded")
        run_tests._INDEX_BUILD_PROBE = broken
        self.assertIsNone(run_tests._wait_for_index_build())
        run_tests._INDEX_BUILD_PROBE = lambda index_dir: (None, None)
        self.assertIsNone(run_tests._wait_for_index_build(),
                          "undetermined lock state must not block")


class IndexerDeferralTests(unittest.TestCase):
    """Wave 1t72b (1t727, revised): a build requested during a test run defers
    without being lost and WITHOUT holding the build lock while waiting."""

    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location(
            "indexer_for_deferral", SCRIPTS_DIR / "indexer.py"
        )
        cls.indexer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.indexer)

    def setUp(self) -> None:
        self._orig_wait = self.indexer._TEST_RUN_WAIT_SECONDS
        self._orig_poll = self.indexer._TEST_RUN_POLL_SECONDS
        self._orig_probe = self.indexer._TEST_RUN_PROBE

    def tearDown(self) -> None:
        self.indexer._TEST_RUN_WAIT_SECONDS = self._orig_wait
        self.indexer._TEST_RUN_POLL_SECONDS = self._orig_poll
        self.indexer._TEST_RUN_PROBE = self._orig_probe

    def _build_lock_free(self, index_dir):
        from runtime_lock import RuntimeFileLock, RuntimeLockBusy
        lock_path = index_dir / self.indexer.INDEX_BUILD_LOCK_NAME
        if not lock_path.exists():
            return True
        probe = RuntimeFileLock(
            lock_path, blocking=False,
            offset=self.indexer.INDEX_BUILD_LOCK_SENTINEL, style="record",
        )
        try:
            probe.acquire()
        except RuntimeLockBusy:
            return False
        probe.release()
        return True

    def test_build_defers_unlocked_until_test_lock_releases(self):
        """Held test lock: the build releases its lock, waits unlocked, then
        re-acquires and proceeds once the suite finishes."""
        idx = self.indexer
        states = iter([True, False, False])  # atomic check: held once, then free
        free_during_wait: list[bool] = []
        with tempfile.TemporaryDirectory() as tmp:
            index_dir = Path(tmp) / ".wavefoundry" / "index"
            index_dir.mkdir(parents=True)

            def probe(path):
                held = next(states)
                if held:
                    pass
                return held

            orig_wait = idx._wait_for_test_run_release
            def instrumented_wait(d):
                # While the build waits for the suite, the BUILD LOCK must be
                # free — a deferring build must never present as running.
                free_during_wait.append(self._build_lock_free(index_dir))
                return orig_wait(d)

            idx._TEST_RUN_PROBE = probe
            idx._TEST_RUN_POLL_SECONDS = 0.01
            idx._TEST_RUN_WAIT_SECONDS = 0.05
            idx._wait_for_test_run_release = instrumented_wait
            try:
                with idx._index_build_lock(index_dir):
                    pass
            finally:
                idx._wait_for_test_run_release = orig_wait
        self.assertEqual(free_during_wait, [True],
                         "the build lock is FREE while deferring to the suite")

    def test_final_cycle_proceeds_never_cancelled(self):
        idx = self.indexer
        idx._TEST_RUN_PROBE = lambda path: True  # suite never finishes
        idx._TEST_RUN_POLL_SECONDS = 0.01
        idx._TEST_RUN_WAIT_SECONDS = 0.02
        with tempfile.TemporaryDirectory() as tmp:
            index_dir = Path(tmp) / ".wavefoundry" / "index"
            index_dir.mkdir(parents=True)
            entered = []
            with idx._index_build_lock(index_dir):
                entered.append(True)
        self.assertEqual(entered, [True], "bounded cycles, then the build runs")

    def test_probe_failure_or_missing_lock_proceeds_immediately(self):
        idx = self.indexer
        def broken(path):
            raise RuntimeError("probe exploded")
        idx._TEST_RUN_PROBE = broken
        with tempfile.TemporaryDirectory() as tmp:
            index_dir = Path(tmp) / ".wavefoundry" / "index"
            index_dir.mkdir(parents=True)
            self.assertFalse(idx._test_run_lock_held(index_dir))
        idx._TEST_RUN_PROBE = lambda path: None
        with tempfile.TemporaryDirectory() as tmp:
            index_dir = Path(tmp) / ".wavefoundry" / "index"
            index_dir.mkdir(parents=True)
            self.assertFalse(idx._test_run_lock_held(index_dir),
                             "undetermined resolves to not-held")


class ExclusionInterleavingTests(unittest.TestCase):
    """Wave 1t72b (1t727 TOCTOU repair): the suite yields after acquiring its
    lock when a build slipped in; the build defers while HOLDING its lock."""

    def setUp(self) -> None:
        self._orig_probe = run_tests._INDEX_BUILD_PROBE

    def tearDown(self) -> None:
        run_tests._INDEX_BUILD_PROBE = self._orig_probe

    def test_probe_helper_reports_held_state(self):
        run_tests._INDEX_BUILD_PROBE = lambda index_dir: (True, 777)
        held, holder = run_tests._probe_index_build_lock()
        self.assertTrue(held)
        self.assertEqual(holder, 777)
        run_tests._INDEX_BUILD_PROBE = lambda index_dir: (None, None)
        held, _ = run_tests._probe_index_build_lock()
        self.assertFalse(held, "undetermined resolves to not-held")

    def test_suite_yield_source_discipline(self):
        """The main start sequence re-probes AFTER acquiring the run lock and
        releases + re-waits when a build holds — pinned at source level so the
        check-then-act ordering cannot silently return."""
        source = (SCRIPTS_DIR / "run_tests.py").read_text(encoding="utf-8")
        wait_pos = source.index("build_wait_error = _wait_for_index_build()")
        acquire_pos = source.index(
            "lock_file, lock_error = _acquire_run_lock()", wait_pos
        )
        reprobe_pos = source.index(
            "held, _holder = _probe_index_build_lock()", acquire_pos
        )
        release_pos = source.index("_release_run_lock(lock_file)", reprobe_pos)
        self.assertTrue(wait_pos < acquire_pos < reprobe_pos < release_pos)
        self.assertIn("for _yield_cycle in range(3):", source)


class IndexerDeferralOrderingTests(unittest.TestCase):
    """Wave 1t72b (1t727 TOCTOU repair): deferral happens while HOLDING the
    build lock — atomic with ownership, so the suite's post-acquire re-probe
    always observes it."""

    @classmethod
    def setUpClass(cls) -> None:
        spec = importlib.util.spec_from_file_location(
            "indexer_for_ordering", SCRIPTS_DIR / "indexer.py"
        )
        cls.indexer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.indexer)

    def test_deferral_ordering_is_post_acquire(self):
        """The test-lock check sits AFTER lock.acquire() (atomic with
        ownership) and the wait sits AFTER lock.release() (never wait while
        holding). Source-ordering assertions: fcntl record locks never
        conflict within one process, so a same-process probe cannot observe
        held-ness — ordering is pinned at source level alongside the behavior
        tests above."""
        source = (SCRIPTS_DIR / "indexer.py").read_text(encoding="utf-8")
        fn_start = source.index("def _index_build_lock(")
        acquire_pos = source.index("lock.acquire()", fn_start)
        check_pos = source.index("_test_run_lock_held(", fn_start)
        release_pos = source.index("lock.release()", check_pos)
        wait_pos = source.index("_wait_for_test_run_release(index_dir)", release_pos)
        self.assertTrue(
            acquire_pos < check_pos < release_pos < wait_pos,
            "acquire < atomic check < release < unlocked wait",
        )
        head = source[fn_start:acquire_pos]
        self.assertNotIn("_test_run_lock_held", head)

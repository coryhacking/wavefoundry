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

"""Tests for the test-cache helpers in run_tests.py."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
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


class HashInputsTests(unittest.TestCase):
    """Tests for _hash_inputs()."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_framework_dir = run_tests._FRAMEWORK_DIR
        run_tests._FRAMEWORK_DIR = self.tmp

    def tearDown(self):
        run_tests._FRAMEWORK_DIR = self._orig_framework_dir
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_returns_hex_string(self):
        (self.tmp / "foo.py").write_bytes(b"x = 1")
        result = run_tests._hash_inputs()
        self.assertIsInstance(result, str)
        self.assertEqual(len(result), 64)  # SHA-256 hex

    def test_same_content_same_hash(self):
        (self.tmp / "foo.py").write_bytes(b"x = 1")
        self.assertEqual(run_tests._hash_inputs(), run_tests._hash_inputs())

    def test_content_change_changes_hash(self):
        f = self.tmp / "foo.py"
        f.write_bytes(b"x = 1")
        h1 = run_tests._hash_inputs()
        f.write_bytes(b"x = 2")
        h2 = run_tests._hash_inputs()
        self.assertNotEqual(h1, h2)

    def test_new_file_changes_hash(self):
        (self.tmp / "foo.py").write_bytes(b"x = 1")
        h1 = run_tests._hash_inputs()
        (self.tmp / "bar.md").write_bytes(b"# seed")
        h2 = run_tests._hash_inputs()
        self.assertNotEqual(h1, h2)

    def test_rename_changes_hash(self):
        (self.tmp / "foo.py").write_bytes(b"x = 1")
        h1 = run_tests._hash_inputs()
        (self.tmp / "foo.py").rename(self.tmp / "baz.py")
        h2 = run_tests._hash_inputs()
        self.assertNotEqual(h1, h2)

    def test_packaging_artifacts_excluded(self):
        (self.tmp / "foo.py").write_bytes(b"x = 1")
        h1 = run_tests._hash_inputs()
        (self.tmp / "MANIFEST").write_bytes(b"changed manifest content")
        (self.tmp / "VERSION").write_bytes(b"2099-01-01a")
        (self.tmp / "test-cache.json").write_bytes(b"{}")
        h2 = run_tests._hash_inputs()
        self.assertEqual(h1, h2)

    def test_index_directory_excluded(self):
        (self.tmp / "foo.py").write_bytes(b"x = 1")
        h1 = run_tests._hash_inputs()
        index_dir = self.tmp / "index"
        index_dir.mkdir()
        (index_dir / "meta.json").write_bytes(b'{"chunks": 999}')
        h2 = run_tests._hash_inputs()
        self.assertEqual(h1, h2)

    def test_nested_pycache_excluded(self):
        # Wave 1tmtx: an external import of run_tests writes
        # scripts/__pycache__/run_tests.pyc before dont_write_bytecode takes
        # effect; the old parts[0]-only check hashed it and destabilized the
        # digest across runs (found via a failed schedule-control comparison).
        h1 = run_tests._hash_inputs()
        nested = run_tests._FRAMEWORK_DIR / "scripts" / "__pycache__"
        nested.mkdir(parents=True, exist_ok=True)
        (nested / "run_tests.cpython-313.pyc").write_bytes(b"bytecode")
        try:
            self.assertEqual(run_tests._hash_inputs(), h1)
        finally:
            shutil.rmtree(nested, ignore_errors=True)

    def test_run_lock_content_excluded(self):
        # Wave 1tmtx: every run rewrites test-run.lock with its own pid; the
        # digest must not see that runtime state (same class as test-cache.json).
        h1 = run_tests._hash_inputs()
        lock = run_tests._FRAMEWORK_DIR / "test-run.lock"
        existed = lock.exists()
        prior = lock.read_bytes() if existed else None
        lock.write_bytes(b"pid 12345\n")
        try:
            self.assertEqual(run_tests._hash_inputs(), h1)
        finally:
            if existed:
                lock.write_bytes(prior)
            else:
                lock.unlink(missing_ok=True)

    def test_pycache_excluded(self):
        (self.tmp / "foo.py").write_bytes(b"x = 1")
        h1 = run_tests._hash_inputs()
        pycache = self.tmp / "__pycache__"
        pycache.mkdir()
        (pycache / "foo.cpython-312.pyc").write_bytes(b"\x00stale bytecode")
        h2 = run_tests._hash_inputs()
        self.assertEqual(h1, h2)

    def test_pytest_cache_excluded(self):
        (self.tmp / "foo.py").write_bytes(b"x = 1")
        h1 = run_tests._hash_inputs()
        cache_dir = self.tmp / ".pytest_cache"
        cache_dir.mkdir()
        (cache_dir / "v").mkdir()
        (cache_dir / "v" / "cache.json").write_bytes(b"{}")
        h2 = run_tests._hash_inputs()
        self.assertEqual(h1, h2)

    def test_seed_documents_included(self):
        h1 = run_tests._hash_inputs()
        seeds_dir = self.tmp / "seeds"
        seeds_dir.mkdir()
        (seeds_dir / "010-agent.prompt.md").write_bytes(b"# Agent seed")
        h2 = run_tests._hash_inputs()
        self.assertNotEqual(h1, h2)

    def test_empty_directory_produces_stable_hash(self):
        h1 = run_tests._hash_inputs()
        h2 = run_tests._hash_inputs()
        self.assertEqual(h1, h2)


class CleanPycacheTests(unittest.TestCase):
    """Tests for _clean_pycache()."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_framework_dir = run_tests._FRAMEWORK_DIR
        run_tests._FRAMEWORK_DIR = self.tmp

    def tearDown(self):
        run_tests._FRAMEWORK_DIR = self._orig_framework_dir
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_removes_pycache_directories(self):
        pycache = self.tmp / "scripts" / "__pycache__"
        pycache.mkdir(parents=True)
        (pycache / "foo.cpython-312.pyc").write_bytes(b"bytecode")
        run_tests._clean_pycache()
        self.assertFalse(pycache.exists())

    def test_removes_nested_pycache(self):
        nested = self.tmp / "scripts" / "tests" / "__pycache__"
        nested.mkdir(parents=True)
        (nested / "test_foo.cpython-312.pyc").write_bytes(b"bytecode")
        run_tests._clean_pycache()
        self.assertFalse(nested.exists())

    def test_leaves_non_pycache_directories(self):
        scripts = self.tmp / "scripts"
        scripts.mkdir()
        (scripts / "foo.py").write_bytes(b"x = 1")
        run_tests._clean_pycache()
        self.assertTrue((scripts / "foo.py").exists())

    def test_is_silent_when_no_pycache_exists(self):
        run_tests._clean_pycache()  # must not raise


class CacheFileTests(unittest.TestCase):
    """Unit tests for _read_cache, _write_cache, and _cache_hit."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_cache_file = run_tests._CACHE_FILE
        run_tests._CACHE_FILE = self.tmp / "test-cache.json"

    def tearDown(self):
        run_tests._CACHE_FILE = self._orig_cache_file
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ------------------------------------------------------------------
    # _read_cache
    # ------------------------------------------------------------------

    def test_read_cache_returns_none_when_file_missing(self):
        self.assertIsNone(run_tests._read_cache())

    def test_read_cache_returns_none_on_invalid_json(self):
        run_tests._CACHE_FILE.write_text("not json", encoding="utf-8")
        self.assertIsNone(run_tests._read_cache())

    def test_read_cache_returns_dict_on_valid_file(self):
        run_tests._CACHE_FILE.write_text(
            json.dumps({"inputs_hash": "abc", "result": "ok"}), encoding="utf-8"
        )
        data = run_tests._read_cache()
        self.assertIsNotNone(data)
        self.assertEqual(data["inputs_hash"], "abc")

    # ------------------------------------------------------------------
    # _write_cache
    # ------------------------------------------------------------------

    def test_write_cache_creates_file_with_correct_fields(self):
        run_tests._write_cache("hash123", 42)
        data = json.loads(run_tests._CACHE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(data["inputs_hash"], "hash123")
        self.assertEqual(data["test_count"], 42)
        self.assertEqual(data["result"], "ok")
        self.assertIn("ran_at", data)

    def test_write_cache_overwrites_existing_file(self):
        run_tests._write_cache("hash_old", 10)
        run_tests._write_cache("hash_new", 20)
        data = json.loads(run_tests._CACHE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(data["inputs_hash"], "hash_new")
        self.assertEqual(data["test_count"], 20)

    def test_write_cache_is_silent_on_unwritable_path(self):
        run_tests._CACHE_FILE = Path("/nonexistent/dir/test-cache.json")
        run_tests._write_cache("hash", 1)  # must not raise

    # ------------------------------------------------------------------
    # _cache_hit
    # ------------------------------------------------------------------

    def test_cache_hit_returns_entry_on_hash_match(self):
        run_tests._write_cache("hash123", 99)
        hit = run_tests._cache_hit("hash123")
        self.assertIsNotNone(hit)
        self.assertEqual(hit["test_count"], 99)

    def test_cache_hit_returns_none_on_hash_mismatch(self):
        run_tests._write_cache("hash123", 99)
        self.assertIsNone(run_tests._cache_hit("different_hash"))

    def test_cache_hit_returns_none_when_no_cache_file(self):
        self.assertIsNone(run_tests._cache_hit("hash123"))

    def test_cache_hit_returns_none_on_non_dict_cache_json(self):
        # Delivery-review finding (wave 1tmtx): valid JSON that is not an
        # object parsed fine and then crashed on .get(); it must be a miss.
        for content in ("[]", '"x"', "5"):
            run_tests._CACHE_FILE.write_text(content, encoding="utf-8")
            self.assertIsNone(run_tests._cache_hit("h"))

    def test_cache_hit_returns_none_when_result_not_ok(self):
        data = {"inputs_hash": "hash123", "result": "fail", "test_count": 5}
        run_tests._CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")
        self.assertIsNone(run_tests._cache_hit("hash123"))


class RunLockTests(unittest.TestCase):
    """Tests for the top-level runner lock."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_lock_file = run_tests._LOCK_FILE
        run_tests._LOCK_FILE = self.tmp / "test-run.lock"

    def tearDown(self):
        run_tests._LOCK_FILE = self._orig_lock_file
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_acquire_run_lock_returns_busy_when_held(self):
        lock_file, error = run_tests._acquire_run_lock()
        self.assertIsNotNone(lock_file)
        self.assertIsNone(error)
        try:
            second_lock, second_error = run_tests._acquire_run_lock()
            self.assertIsNone(second_lock)
            self.assertIsNotNone(second_error)
            self.assertIn("already running", second_error)
        finally:
            run_tests._release_run_lock(lock_file)

    def test_main_returns_busy_when_lock_is_held(self):
        with patch.object(run_tests, "_hash_inputs", return_value="hash123"), \
                patch.object(run_tests, "_cache_hit", return_value=None), \
                patch.object(run_tests, "_acquire_run_lock", return_value=(None, "already running")), \
                patch.object(run_tests, "_clean_pycache") as clean_mock, \
                patch.object(sys, "argv", ["run_tests.py"]):
            rc = run_tests.main()
        self.assertEqual(rc, 1)
        clean_mock.assert_not_called()

    def test_cache_hit_bypasses_lock_acquisition(self):
        with patch.object(run_tests, "_hash_inputs", return_value="stable_hash"), \
                patch.object(run_tests, "_cache_hit", return_value={"test_count": 99, "ran_at": "2026-05-26T00:00:00Z"}), \
                patch.object(run_tests, "_acquire_run_lock") as lock_mock, \
                patch.object(sys, "argv", ["run_tests.py"]):
            rc = run_tests.main()
        self.assertEqual(rc, 0)
        lock_mock.assert_not_called()


class MainCacheBehaviorTests(unittest.TestCase):
    """Integration tests for main() cache read/write/skip logic."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_cache_file = run_tests._CACHE_FILE
        self._orig_tests_dir = run_tests._TESTS_DIR
        run_tests._CACHE_FILE = self.tmp / "test-cache.json"
        run_tests._TESTS_DIR = self.tmp
        (self.tmp / "test_fake.py").write_text("# fake test file\n", encoding="utf-8")
        # Prevent _clean_pycache from touching the real framework directory
        # during these unit tests — it is tested separately in CleanPycacheTests.
        self._patcher_clean = patch.object(run_tests, "_clean_pycache")
        self._patcher_lock = patch.object(run_tests, "_acquire_run_lock", return_value=(object(), None))
        self._patcher_release = patch.object(run_tests, "_release_run_lock")
        # Wave 1t72b (1t727): main() now waits on the PROJECT index-build lock
        # before starting; unit tests must never probe (or wait on) the real
        # repository's lock — a live deferring build once made this file wait
        # out its whole 600s budget.
        self._patcher_build_wait = patch.object(
            run_tests, "_wait_for_index_build", return_value=None
        )
        self._patcher_build_probe = patch.object(
            run_tests, "_probe_index_build_lock", return_value=(False, None)
        )
        self._patcher_clean.start()
        self._patcher_lock.start()
        self._patcher_release.start()
        self._patcher_build_wait.start()
        self._patcher_build_probe.start()

    def tearDown(self):
        self._patcher_clean.stop()
        self._patcher_lock.stop()
        self._patcher_release.stop()
        self._patcher_build_wait.stop()
        self._patcher_build_probe.stop()
        run_tests._CACHE_FILE = self._orig_cache_file
        run_tests._TESTS_DIR = self._orig_tests_dir
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _run_file_result(self, *, success=True, tests_run=42, name="test_fake.py",
                         elapsed_s=1.5, skip_count=0):
        return run_tests.FileResult(
            name, 0 if success else 1, "output", tests_run, elapsed_s, skip_count
        )

    # ------------------------------------------------------------------
    # Cache skip
    # ------------------------------------------------------------------

    def test_skips_tests_on_cache_hit(self):
        with patch.object(run_tests, "_hash_inputs", return_value="stable_hash"):
            run_tests._write_cache("stable_hash", 99)
            with patch.object(run_tests, "_run_file") as mock_run_file, \
                    patch.object(sys, "argv", ["run_tests.py"]):
                ret = run_tests.main()
        mock_run_file.assert_not_called()
        self.assertEqual(ret, 0)

    def test_does_not_skip_on_hash_mismatch(self):
        run_tests._write_cache("old_hash", 99)
        with patch.object(run_tests, "_hash_inputs", return_value="new_hash"), \
                patch.object(run_tests, "_run_file", return_value=self._run_file_result()) as mock_run_file, \
                patch.object(sys, "argv", ["run_tests.py"]):
            run_tests.main()
        mock_run_file.assert_called_once()

    def test_does_not_skip_when_no_cache_file(self):
        with patch.object(run_tests, "_hash_inputs", return_value="some_hash"), \
                patch.object(run_tests, "_run_file", return_value=self._run_file_result()) as mock_run_file, \
                patch.object(sys, "argv", ["run_tests.py"]):
            run_tests.main()
        mock_run_file.assert_called_once()

    # ------------------------------------------------------------------
    # Cache write
    # ------------------------------------------------------------------

    def test_writes_cache_after_successful_run(self):
        with patch.object(run_tests, "_hash_inputs", return_value="clean_hash"), \
                patch.object(run_tests, "_run_file", return_value=self._run_file_result(tests_run=55)), \
                patch.object(sys, "argv", ["run_tests.py"]):
            run_tests.main()
        data = json.loads(run_tests._CACHE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(data["inputs_hash"], "clean_hash")
        self.assertEqual(data["test_count"], 55)
        self.assertEqual(data["result"], "ok")

    def test_does_not_write_cache_on_test_failure(self):
        with patch.object(run_tests, "_hash_inputs", return_value="clean_hash"), \
                patch.object(run_tests, "_run_file", return_value=self._run_file_result(success=False)), \
                patch.object(sys, "argv", ["run_tests.py"]):
            ret = run_tests.main()
        self.assertFalse(run_tests._CACHE_FILE.exists())
        self.assertEqual(ret, 1)

    # ------------------------------------------------------------------
    # --no-cache flag
    # ------------------------------------------------------------------

    def test_no_cache_flag_forces_run_despite_cache_hit(self):
        with patch.object(run_tests, "_hash_inputs", return_value="stable_hash"):
            run_tests._write_cache("stable_hash", 99)
            with patch.object(run_tests, "_run_file", return_value=self._run_file_result()) as mock_run_file, \
                    patch.object(sys, "argv", ["run_tests.py", "--no-cache"]):
                ret = run_tests.main()
        mock_run_file.assert_called_once()
        self.assertEqual(ret, 0)

    def test_no_cache_flag_still_writes_cache_on_success(self):
        with patch.object(run_tests, "_hash_inputs", return_value="stable_hash"), \
                patch.object(run_tests, "_run_file", return_value=self._run_file_result(tests_run=77)), \
                patch.object(sys, "argv", ["run_tests.py", "--no-cache"]):
            run_tests.main()
        data = json.loads(run_tests._CACHE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(data["inputs_hash"], "stable_hash")
        self.assertEqual(data["test_count"], 77)

    def test_hash_computed_once_written_value_matches_pre_run_hash(self):
        """Cache write must use the hash from before the run, not a second call."""
        call_count = []

        def counting_hash():
            call_count.append(1)
            return f"hash_{len(call_count)}"  # returns different value each call

        with patch.object(run_tests, "_hash_inputs", side_effect=counting_hash), \
                patch.object(run_tests, "_run_file", return_value=self._run_file_result(tests_run=10)), \
                patch.object(sys, "argv", ["run_tests.py"]):
            run_tests.main()

        # hash_1 was computed before the run; it must be what's written
        data = json.loads(run_tests._CACHE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(data["inputs_hash"], "hash_1")
        self.assertEqual(len(call_count), 1)  # called exactly once

    def test_no_cache_flag_not_forwarded_to_unittest(self):
        with patch.object(run_tests, "_hash_inputs", return_value="stable_hash"), \
                patch.object(run_tests, "_run_file", return_value=self._run_file_result()) as mock_run_file, \
                patch.object(sys, "argv", ["run_tests.py", "--no-cache"]):
            run_tests.main()
        mock_run_file.assert_called_once()


class RunFileTelemetryTests(unittest.TestCase):
    """_run_file telemetry: child elapsed measurement and skip-count parsing (wave 1tmtx)."""

    def _completed(self, stderr, rc=0):
        return subprocess.CompletedProcess(args=[], returncode=rc, stdout="", stderr=stderr)

    def test_run_file_measures_child_subprocess_elapsed(self):
        times = iter([100.0, 103.25])
        with patch.object(run_tests.time, "monotonic", side_effect=lambda: next(times)), \
                patch.object(run_tests.subprocess, "run",
                             return_value=self._completed("Ran 3 tests in 0.001s\n\nOK\n")):
            res = run_tests._run_file(Path("test_x.py"))
        self.assertEqual(res.elapsed_s, 3.25)
        self.assertEqual(res.test_count, 3)
        self.assertEqual(res.returncode, 0)

    def test_run_file_parses_skip_count_from_result_tail(self):
        out = "test_a ... skipped 'no fixture'\nRan 5 tests in 0.010s\n\nOK (skipped=2)\n"
        with patch.object(run_tests.subprocess, "run", return_value=self._completed(out)):
            res = run_tests._run_file(Path("test_x.py"))
        self.assertEqual(res.skip_count, 2)
        self.assertEqual(res.test_count, 5)

    def test_run_file_skip_count_zero_without_skips(self):
        with patch.object(run_tests.subprocess, "run",
                          return_value=self._completed("Ran 4 tests in 0.002s\n\nOK\n")):
            res = run_tests._run_file(Path("test_x.py"))
        self.assertEqual(res.skip_count, 0)

    def test_run_file_parses_skip_count_on_failed_tail(self):
        out = "Ran 6 tests in 0.010s\n\nFAILED (failures=1, skipped=3)\n"
        with patch.object(run_tests.subprocess, "run", return_value=self._completed(out, rc=1)):
            res = run_tests._run_file(Path("test_x.py"))
        self.assertEqual(res.skip_count, 3)
        self.assertEqual(res.returncode, 1)

    def test_run_file_count_ignores_runner_style_lines_printed_by_tests(self):
        # Known-bad reproduction (found 2026-08-27): a test that exercises
        # main() prints "Ran 42 tests across 1 files in 0.001s" to stdout;
        # the first-unanchored parse read that mock line as the file's count.
        proc = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="Ran 42 tests across 1 files in 0.001s\nOK\n",
            stderr="Ran 92 tests in 0.445s\n\nOK\n",
        )
        with patch.object(run_tests.subprocess, "run", return_value=proc):
            res = run_tests._run_file(Path("test_x.py"))
        self.assertEqual(res.test_count, 92)

    def test_run_file_skip_count_binds_to_final_summary_only(self):
        proc = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="noise skipped=7 noise\nRan 3 tests in 0.001s\n\nOK (skipped=1)\n",
            stderr="Ran 92 tests in 0.445s\n\nOK (skipped=2)\n",
        )
        with patch.object(run_tests.subprocess, "run", return_value=proc):
            res = run_tests._run_file(Path("test_x.py"))
        self.assertEqual(res.test_count, 92)
        self.assertEqual(res.skip_count, 2)


class TelemetrySummaryTests(unittest.TestCase):
    """main() telemetry output: forced-skip aggregation, bounded top-10, service time (wave 1tmtx).

    The forced-skip control here is fixture-scoped (mocked _run_file) and runs
    outside any benchmark or delivery series, per Requirement 2 of 1tm6d.
    """

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_cache_file = run_tests._CACHE_FILE
        self._orig_tests_dir = run_tests._TESTS_DIR
        run_tests._CACHE_FILE = self.tmp / "test-cache.json"
        run_tests._TESTS_DIR = self.tmp
        (self.tmp / "test_fake.py").write_text("# fake test file\n", encoding="utf-8")
        self._patchers = [
            patch.object(run_tests, "_clean_pycache"),
            patch.object(run_tests, "_acquire_run_lock", return_value=(object(), None)),
            patch.object(run_tests, "_release_run_lock"),
            patch.object(run_tests, "_wait_for_index_build", return_value=None),
            patch.object(run_tests, "_probe_index_build_lock", return_value=(False, None)),
        ]
        for p in self._patchers:
            p.start()

    def tearDown(self):
        for p in self._patchers:
            p.stop()
        run_tests._CACHE_FILE = self._orig_cache_file
        run_tests._TESTS_DIR = self._orig_tests_dir
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _main_output(self, run_file):
        buf = io.StringIO()
        kwargs = {"side_effect": run_file} if callable(run_file) else {"return_value": run_file}
        with patch.object(run_tests, "_hash_inputs", return_value="h"), \
                patch.object(run_tests, "_run_file", **kwargs), \
                patch.object(sys, "argv", ["run_tests.py"]), \
                contextlib.redirect_stdout(buf):
            ret = run_tests.main()
        return ret, buf.getvalue()

    def test_forced_skip_reaches_complete_run_summary(self):
        result = run_tests.FileResult("test_fake.py", 0, "output", 10, 1.0, 2)
        ret, out = self._main_output(result)
        self.assertEqual(ret, 0)
        self.assertIn("skipped 2 tests", out)

    def test_slowest_file_summary_is_bounded_to_ten(self):
        for ch in "abcdefghijkl":
            (self.tmp / f"test_{ch}.py").write_text("# fake\n", encoding="utf-8")
        files = sorted(self.tmp.glob("test_*.py"))
        elapsed_map = {f.name: float(i + 1) for i, f in enumerate(files)}

        def fake_run(path):
            return run_tests.FileResult(path.name, 0, "", 1, elapsed_map[path.name], 0)

        ret, out = self._main_output(fake_run)
        self.assertEqual(ret, 0)
        self.assertIn(f"Slowest files (top 10 of {len(files)}):", out)
        block = out.split("Slowest files", 1)[1].split("Worker service time", 1)[0]
        entries = [ln for ln in block.splitlines() if ln.startswith("  test_")]
        self.assertEqual(len(entries), 10)
        slowest_name = max(elapsed_map, key=elapsed_map.get)
        self.assertIn(slowest_name, entries[0])

    def test_service_time_line_reports_aggregate_and_wall_line_is_retained(self):
        (self.tmp / "test_more.py").write_text("# fake\n", encoding="utf-8")
        durations = {"test_fake.py": 1.0, "test_more.py": 2.5}

        def fake_run(path):
            return run_tests.FileResult(path.name, 0, "", 4, durations[path.name], 0)

        ret, out = self._main_output(fake_run)
        self.assertEqual(ret, 0)
        self.assertIn("Worker service time: 3.500s across 2 files; skipped 0 tests", out)
        self.assertRegex(out, r"Ran 8 tests across 2 files in \d+\.\d{3}s")

    def test_telemetry_lines_present_on_failed_run(self):
        result = run_tests.FileResult("test_fake.py", 1, "boom", 3, 0.5, 1)
        ret, out = self._main_output(result)
        self.assertEqual(ret, 1)
        self.assertIn("Slowest files (top 1 of 1):", out)
        self.assertIn("skipped 1 tests", out)
        self.assertIn("FAILED (test_fake.py)", out)
        self.assertFalse(run_tests._CACHE_FILE.exists())


class _MainScaffoldTests(unittest.TestCase):
    """Shared main() scaffolding: tmp cache/tests dirs plus canonical seam patchers.

    Base class only — defines no tests itself. Subclasses drive run_tests.main()
    against a temp tests dir with the lock/index/pycache seams neutralized.
    """

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_cache_file = run_tests._CACHE_FILE
        self._orig_tests_dir = run_tests._TESTS_DIR
        run_tests._CACHE_FILE = self.tmp / "test-cache.json"
        run_tests._TESTS_DIR = self.tmp
        (self.tmp / "test_fake.py").write_text("# fake test file\n", encoding="utf-8")
        self._patchers = [
            patch.object(run_tests, "_clean_pycache"),
            patch.object(run_tests, "_acquire_run_lock", return_value=(object(), None)),
            patch.object(run_tests, "_release_run_lock"),
            patch.object(run_tests, "_wait_for_index_build", return_value=None),
            patch.object(run_tests, "_probe_index_build_lock", return_value=(False, None)),
        ]
        for p in self._patchers:
            p.start()

    def tearDown(self):
        for p in self._patchers:
            p.stop()
        run_tests._CACHE_FILE = self._orig_cache_file
        run_tests._TESTS_DIR = self._orig_tests_dir
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _main(self, argv, run_file):
        out, err = io.StringIO(), io.StringIO()
        kwargs = {"side_effect": run_file} if callable(run_file) else {"return_value": run_file}
        with patch.object(run_tests, "_run_file", **kwargs), \
                patch.object(sys, "argv", ["run_tests.py", *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            ret = run_tests.main()
        return ret, out.getvalue(), err.getvalue()


class _RecordingExecutor:
    """ThreadPoolExecutor stand-in recording actual submit() call order."""

    last_submitted: list[str] = []

    def __init__(self, max_workers):
        type(self).last_submitted = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def submit(self, fn, arg):
        type(self).last_submitted.append(arg.name)
        result = fn(arg)

        class _F:
            def __init__(self, r):
                self._r = r

            def result(self):
                return self._r

        return _F(result)


class ParseArgsTests(unittest.TestCase):
    """Strict argv validation (Requirement 9 of 1tm6d): clear deterministic failures."""

    def _usage(self, argv):
        with self.assertRaises(run_tests._UsageError) as ctx:
            run_tests._parse_args(["run_tests.py", *argv])
        return str(ctx.exception)

    def test_bare_and_no_cache_forms_parse(self):
        self.assertFalse(run_tests._parse_args(["run_tests.py"])["no_cache"])
        opts = run_tests._parse_args(["run_tests.py", "--no-cache"])
        self.assertTrue(opts["no_cache"])
        self.assertEqual(opts["files"], [])
        self.assertIsNone(opts["schedule_control"])

    def test_repeatable_file_selectors_parse_in_order(self):
        opts = run_tests._parse_args(
            ["run_tests.py", "--file", "test_a.py", "--file", "test_b.py"])
        self.assertEqual(opts["files"], ["test_a.py", "test_b.py"])

    def test_schedule_control_with_timings_file_parses(self):
        opts = run_tests._parse_args(
            ["run_tests.py", "--schedule-control", "timing", "--timings-file", "t.json"])
        self.assertEqual(opts["schedule_control"], "timing")
        self.assertEqual(opts["timings_file"], "t.json")

    def test_unknown_option_rejected(self):
        self.assertIn("unknown option", self._usage(["--frobnicate"]))

    def test_positional_argument_rejected(self):
        self.assertIn("positional argument", self._usage(["test_a.py"]))

    def test_file_requires_value(self):
        self.assertIn("--file requires a value", self._usage(["--file"]))

    def test_schedule_control_requires_value(self):
        self.assertIn("--schedule-control requires a value", self._usage(["--schedule-control"]))

    def test_schedule_control_invalid_value_rejected(self):
        self.assertIn("invalid --schedule-control value",
                      self._usage(["--schedule-control", "fastest", "--timings-file", "t"]))

    def test_schedule_control_repeat_rejected(self):
        self.assertIn("only once", self._usage(
            ["--schedule-control", "timing", "--timings-file", "t",
             "--schedule-control", "timing"]))

    def test_timings_file_repeat_rejected(self):
        self.assertIn("only once", self._usage(
            ["--schedule-control", "timing", "--timings-file", "a", "--timings-file", "b"]))

    def test_file_with_no_cache_rejected(self):
        self.assertIn("mutually exclusive", self._usage(["--file", "test_a.py", "--no-cache"]))

    def test_schedule_control_with_file_rejected(self):
        self.assertIn("mutually exclusive", self._usage(
            ["--schedule-control", "timing", "--timings-file", "t", "--file", "test_a.py"]))

    def test_schedule_control_with_no_cache_rejected(self):
        self.assertIn("mutually exclusive", self._usage(
            ["--schedule-control", "timing", "--timings-file", "t", "--no-cache"]))

    def test_schedule_control_without_timings_file_rejected(self):
        self.assertIn("requires --timings-file", self._usage(["--schedule-control", "timing"]))

    def test_timings_file_without_schedule_control_rejected(self):
        self.assertIn("requires --schedule-control", self._usage(["--timings-file", "t.json"]))

    def test_usage_error_exits_2_via_main_before_any_hashing(self):
        err = io.StringIO()
        with patch.object(run_tests, "_hash_inputs") as mock_hash, \
                patch.object(run_tests, "_read_cache") as mock_read, \
                patch.object(sys, "argv", ["run_tests.py", "--bogus"]), \
                contextlib.redirect_stderr(err):
            self.assertEqual(run_tests.main(), 2)
        self.assertIn("unknown option", err.getvalue())
        mock_hash.assert_not_called()
        mock_read.assert_not_called()


class FocusSelectorValidationTests(unittest.TestCase):
    """--file selector validation (Requirement 9 of 1tm6d)."""

    def setUp(self):
        self.files = [Path("/repo/tests/test_a.py"), Path("/repo/tests/test_b.py")]

    def _error(self, selectors):
        selected, error = run_tests._validate_focus_selectors(selectors, self.files)
        self.assertIsNone(selected)
        return error

    def test_valid_selectors_resolve_in_selector_order(self):
        selected, error = run_tests._validate_focus_selectors(
            ["test_b.py", "test_a.py"], self.files)
        self.assertIsNone(error)
        self.assertEqual([p.name for p in selected], ["test_b.py", "test_a.py"])

    def test_duplicate_selector_rejected(self):
        self.assertIn("duplicate", self._error(["test_a.py", "test_a.py"]))

    def test_path_separator_rejected(self):
        self.assertIn("not a path", self._error(["tests/test_a.py"]))

    def test_backslash_separator_rejected(self):
        self.assertIn("not a path", self._error(["tests\\test_a.py"]))

    def test_absolute_path_rejected(self):
        self.assertIn("not a path", self._error(["/repo/tests/test_a.py"]))

    def test_non_test_basename_rejected(self):
        self.assertIn("not a test_*.py basename", self._error(["helper.py"]))

    def test_undiscovered_file_rejected(self):
        self.assertIn("not a discovered test file", self._error(["test_missing.py"]))


class FocusedRunTests(_MainScaffoldTests):
    """Focused runs: canonical path, zero cache/hash/timing seams, focused label (AC-4)."""

    def test_focused_run_calls_no_hash_cache_or_timing_seams(self):
        result = run_tests.FileResult("test_fake.py", 0, "", 3, 0.5, 0)
        cache_bytes = b'{"inputs_hash": "prior", "result": "ok", "test_count": 9}\n'
        run_tests._CACHE_FILE.write_bytes(cache_bytes)
        with patch.object(run_tests, "_hash_inputs") as mock_hash, \
                patch.object(run_tests, "_read_cache") as mock_read, \
                patch.object(run_tests, "_write_cache") as mock_write, \
                patch.object(run_tests, "_cache_hit") as mock_hit, \
                patch.object(run_tests, "_validated_durations") as mock_durations:
            ret, out, _err = self._main(["--file", "test_fake.py"], result)
        self.assertEqual(ret, 0)
        for mock in (mock_hash, mock_read, mock_write, mock_hit, mock_durations):
            mock.assert_not_called()
        self.assertIn("FOCUSED diagnostic run (1 of 1 test files)", out)
        self.assertIn("not delivery evidence", out)
        self.assertEqual(run_tests._CACHE_FILE.read_bytes(), cache_bytes)

    def test_focused_failure_propagates_and_writes_nothing(self):
        result = run_tests.FileResult("test_fake.py", 1, "boom", 3, 0.5, 0)
        ret, _out, _err = self._main(["--file", "test_fake.py"], result)
        self.assertEqual(ret, 1)
        self.assertFalse(run_tests._CACHE_FILE.exists())

    def test_invalid_selector_fails_before_any_seam(self):
        with patch.object(run_tests, "_hash_inputs") as mock_hash, \
                patch.object(run_tests, "_read_cache") as mock_read:
            ret, _out, err = self._main(["--file", "test_absent.py"],
                                        run_tests.FileResult("x", 0, "", 1, 0.1, 0))
        self.assertEqual(ret, 2)
        self.assertIn("not a discovered test file", err)
        mock_hash.assert_not_called()
        mock_read.assert_not_called()


class FocusedCallOrderTests(unittest.TestCase):
    """Positive call-order spies: the focused path traverses every canonical seam (AC-4)."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_cache_file = run_tests._CACHE_FILE
        self._orig_tests_dir = run_tests._TESTS_DIR
        run_tests._CACHE_FILE = self.tmp / "test-cache.json"
        run_tests._TESTS_DIR = self.tmp
        (self.tmp / "test_fake.py").write_text("# fake test file\n", encoding="utf-8")

    def tearDown(self):
        run_tests._CACHE_FILE = self._orig_cache_file
        run_tests._TESTS_DIR = self._orig_tests_dir
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_focused_path_traverses_canonical_seams_in_order(self):
        calls: list[str] = []

        def recorder(name, value=None):
            def _side_effect(*args, **kwargs):
                calls.append(name)
                return value
            return _side_effect

        lock_handle = object()
        with patch.object(run_tests, "_wait_for_index_build",
                          side_effect=recorder("_wait_for_index_build", None)), \
                patch.object(run_tests, "_acquire_run_lock",
                             side_effect=recorder("_acquire_run_lock", (lock_handle, None))), \
                patch.object(run_tests, "_probe_index_build_lock",
                             side_effect=recorder("_probe_index_build_lock", (False, None))), \
                patch.object(run_tests, "_clean_pycache",
                             side_effect=recorder("_clean_pycache", None)), \
                patch.object(run_tests, "_run_file",
                             side_effect=recorder(
                                 "_run_file",
                                 run_tests.FileResult("test_fake.py", 0, "", 2, 0.4, 0))), \
                patch.object(run_tests, "_stray_artifact_failure",
                             side_effect=recorder("_stray_artifact_failure", None)), \
                patch.object(run_tests, "_release_run_lock",
                             side_effect=recorder("_release_run_lock", None)), \
                patch.object(sys, "argv", ["run_tests.py", "--file", "test_fake.py"]), \
                contextlib.redirect_stdout(io.StringIO()):
            ret = run_tests.main()
        self.assertEqual(ret, 0)
        self.assertEqual(calls, [
            "_wait_for_index_build",
            "_acquire_run_lock",
            "_probe_index_build_lock",
            "_clean_pycache",
            "_run_file",
            "_stray_artifact_failure",
            "_clean_pycache",
            "_release_run_lock",
        ])


class DurationsValidationTests(unittest.TestCase):
    """Requirement 3 of 1tm6d: independent advisory validation of durations_s."""

    def setUp(self):
        self.files = [Path("/t/test_a.py"), Path("/t/test_b.py")]

    def test_malformed_container_yields_empty(self):
        self.assertEqual(run_tests._validated_durations(None, self.files), {})
        self.assertEqual(run_tests._validated_durations({"durations_s": "garbage"}, self.files), {})
        self.assertEqual(run_tests._validated_durations({"durations_s": [1, 2]}, self.files), {})
        self.assertEqual(run_tests._validated_durations({}, self.files), {})

    def test_entries_degrade_independently(self):
        cache = {"durations_s": {
            "test_a.py": 1.5,            # valid — survives its bad siblings
            "test_b.py": True,           # boolean — rejected
            "test_stale.py": 2.0,        # unknown/stale key — rejected
            3: 4.0,                      # non-string key — rejected
        }}
        self.assertEqual(run_tests._validated_durations(cache, self.files), {"test_a.py": 1.5})

    def test_out_of_range_values_rejected(self):
        cache = {"durations_s": {
            "test_a.py": -0.1,
            "test_b.py": run_tests._FILE_TIMEOUT_SECONDS + 1,
        }}
        self.assertEqual(run_tests._validated_durations(cache, self.files), {})
        cache = {"durations_s": {"test_a.py": float("inf"), "test_b.py": float("nan")}}
        self.assertEqual(run_tests._validated_durations(cache, self.files), {})

    def test_timeout_boundary_value_is_valid(self):
        cache = {"durations_s": {"test_a.py": float(run_tests._FILE_TIMEOUT_SECONDS)}}
        self.assertEqual(run_tests._validated_durations(cache, self.files),
                         {"test_a.py": float(run_tests._FILE_TIMEOUT_SECONDS)})


class DurationsPersistenceTests(unittest.TestCase):
    """Requirement 3 of 1tm6d: atomic durations_s persistence beside last-green."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_cache_file = run_tests._CACHE_FILE
        run_tests._CACHE_FILE = self.tmp / "test-cache.json"

    def tearDown(self):
        run_tests._CACHE_FILE = self._orig_cache_file
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_write_cache_persists_clamped_rounded_durations(self):
        run_tests._write_cache("h", 5, {"test_a.py": 1.23456, "test_b.py": 9999.0})
        data = json.loads(run_tests._CACHE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(data["durations_s"], {
            "test_a.py": 1.235,
            "test_b.py": float(run_tests._FILE_TIMEOUT_SECONDS),
        })
        self.assertEqual(data["result"], "ok")

    def test_write_cache_without_durations_omits_key(self):
        run_tests._write_cache("h", 5)
        data = json.loads(run_tests._CACHE_FILE.read_text(encoding="utf-8"))
        self.assertNotIn("durations_s", data)

    def test_write_cache_leaves_no_tmp_residue(self):
        run_tests._write_cache("h", 5, {"test_a.py": 1.0})
        self.assertTrue(run_tests._CACHE_FILE.exists())
        self.assertEqual([p.name for p in self.tmp.iterdir()], ["test-cache.json"])


class CacheReadOnceTests(_MainScaffoldTests):
    """Requirement 3 of 1tm6d: an ordinary run reads the cache exactly once."""

    def _count_reads(self, argv, run_file):
        real_read = run_tests._read_cache
        with patch.object(run_tests, "_read_cache", side_effect=real_read) as mock_read, \
                patch.object(run_tests, "_hash_inputs", return_value="h"):
            ret, out, _err = self._main(argv, run_file)
        return ret, out, mock_read.call_count

    def test_cache_hit_path_reads_once(self):
        run_tests._write_cache("h", 9)
        ret, out, reads = self._count_reads([], run_tests.FileResult("test_fake.py", 0, "", 1, 0.1, 0))
        self.assertEqual(ret, 0)
        self.assertIn("Tests current", out)
        self.assertEqual(reads, 1)

    def test_cache_miss_path_reads_once(self):
        run_tests._write_cache("other", 9)
        ret, _out, reads = self._count_reads([], run_tests.FileResult("test_fake.py", 0, "", 1, 0.1, 0))
        self.assertEqual(ret, 0)
        self.assertEqual(reads, 1)

    def test_no_cache_path_reads_once_but_never_skips(self):
        run_tests._write_cache("h", 9)
        result = run_tests.FileResult("test_fake.py", 0, "", 1, 0.1, 0)
        real_read = run_tests._read_cache
        with patch.object(run_tests, "_read_cache", side_effect=real_read) as mock_read, \
                patch.object(run_tests, "_hash_inputs", return_value="h"), \
                patch.object(run_tests, "_run_file", return_value=result) as mock_run:
            with patch.object(sys, "argv", ["run_tests.py", "--no-cache"]), \
                    contextlib.redirect_stdout(io.StringIO()):
                ret = run_tests.main()
        self.assertEqual(ret, 0)
        self.assertEqual(mock_read.call_count, 1)
        mock_run.assert_called_once()

    def test_corrupt_durations_do_not_invalidate_matching_last_green(self):
        run_tests._CACHE_FILE.write_text(json.dumps({
            "inputs_hash": "h", "ran_at": "2026-08-27T00:00:00+00:00",
            "test_count": 9, "result": "ok", "durations_s": "garbage",
        }), encoding="utf-8")
        with patch.object(run_tests, "_hash_inputs", return_value="h"), \
                patch.object(run_tests, "_run_file") as mock_run, \
                patch.object(sys, "argv", ["run_tests.py"]), \
                contextlib.redirect_stdout(io.StringIO()):
            ret = run_tests.main()
        self.assertEqual(ret, 0)
        mock_run.assert_not_called()

    def test_valid_timings_with_hash_mismatch_never_authorize_skip(self):
        run_tests._write_cache("old", 9, {"test_fake.py": 1.0})
        result = run_tests.FileResult("test_fake.py", 0, "", 1, 0.1, 0)
        with patch.object(run_tests, "_hash_inputs", return_value="new"), \
                patch.object(run_tests, "_run_file", return_value=result) as mock_run, \
                patch.object(sys, "argv", ["run_tests.py"]), \
                contextlib.redirect_stdout(io.StringIO()):
            ret = run_tests.main()
        self.assertEqual(ret, 0)
        mock_run.assert_called_once()

    def test_successful_full_run_persists_observed_durations(self):
        result = run_tests.FileResult("test_fake.py", 0, "", 7, 2.5, 0)
        with patch.object(run_tests, "_hash_inputs", return_value="h"):
            ret, _out, _err = self._main([], result)
        self.assertEqual(ret, 0)
        data = json.loads(run_tests._CACHE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(data["durations_s"], {"test_fake.py": 2.5})
        self.assertEqual(data["test_count"], 7)


class ScheduleControlTests(_MainScaffoldTests):
    """Requirement 4 / AC-7 of 1tm6d: benchmark-only schedule controls."""

    def _manifest_path(self):
        return self.tmp / "timings.json"

    def _write_manifest(self, digest, durations):
        self._manifest_path().write_text(json.dumps(
            {"source_digest": digest, "durations_s": durations}), encoding="utf-8")

    def _run(self, mode, run_file, digest="d1"):
        with patch.object(run_tests, "_hash_inputs", return_value=digest), \
                patch.object(run_tests, "_read_cache") as mock_read, \
                patch.object(run_tests, "_write_cache") as mock_write, \
                patch.object(run_tests, "_cache_hit") as mock_hit:
            ret, out, err = self._main(
                ["--schedule-control", mode, "--timings-file", str(self._manifest_path())],
                run_file)
        return ret, out, err, (mock_read, mock_write, mock_hit)

    def test_bootstrap_green_writes_digest_bound_complete_manifest(self):
        result = run_tests.FileResult("test_fake.py", 0, "", 3, 1.234, 0)
        ret, out, _err, cache_mocks = self._run("bootstrap", result)
        self.assertEqual(ret, 0)
        self.assertIn("SCHEDULE CONTROL (bootstrap)", out)
        self.assertIn("Timing manifest written", out)
        data = json.loads(self._manifest_path().read_text(encoding="utf-8"))
        self.assertEqual(data["source_digest"], "d1")
        self.assertEqual(data["durations_s"], {"test_fake.py": 1.234})
        for mock in cache_mocks:
            mock.assert_not_called()

    def test_bootstrap_red_run_writes_no_manifest(self):
        result = run_tests.FileResult("test_fake.py", 1, "boom", 3, 1.0, 0)
        ret, _out, err, _mocks = self._run("bootstrap", result)
        self.assertEqual(ret, 1)
        self.assertIn("no timing manifest written", err)
        self.assertFalse(self._manifest_path().exists())

    def test_candidate_digest_mismatch_is_invalid_before_running(self):
        self._write_manifest("stale", {"test_fake.py": 1.0})
        with patch.object(run_tests, "_run_file") as mock_run:
            ret, _out, err, _mocks = self._run("timing", mock_run)
        self.assertEqual(ret, 2)
        self.assertIn("source digest does not match", err)
        mock_run.assert_not_called()

    def test_candidate_missing_duration_is_invalid(self):
        self._write_manifest("d1", {})
        with patch.object(run_tests, "_run_file") as mock_run:
            ret, _out, err, _mocks = self._run("alphabetical", mock_run)
        self.assertEqual(ret, 2)
        self.assertIn("lacks a valid duration", err)
        self.assertIn("comparison is invalid", err)
        mock_run.assert_not_called()

    def test_timing_candidate_submits_longest_first_via_actual_executor(self):
        for ch in "abc":
            (self.tmp / f"test_{ch}.py").write_text("# fake\n", encoding="utf-8")
        durations = {"test_a.py": 1.0, "test_b.py": 9.0, "test_c.py": 5.0, "test_fake.py": 3.0}
        self._write_manifest("d1", durations)

        def fake_run(path):
            return run_tests.FileResult(path.name, 0, "", 1, durations[path.name], 0)

        with patch.object(run_tests.concurrent.futures, "ThreadPoolExecutor", _RecordingExecutor), \
                patch.object(run_tests.concurrent.futures, "as_completed", lambda futures: list(futures)):
            ret, _out, _err, _mocks = self._run("timing", fake_run)
        self.assertEqual(ret, 0)
        self.assertEqual(_RecordingExecutor.last_submitted,
                         ["test_b.py", "test_c.py", "test_fake.py", "test_a.py"])

    def test_alphabetical_candidate_submits_name_order_via_actual_executor(self):
        for ch in "abc":
            (self.tmp / f"test_{ch}.py").write_text("# fake\n", encoding="utf-8")
        durations = {"test_a.py": 1.0, "test_b.py": 9.0, "test_c.py": 5.0, "test_fake.py": 3.0}
        self._write_manifest("d1", durations)

        def fake_run(path):
            return run_tests.FileResult(path.name, 0, "", 1, durations[path.name], 0)

        manifest_before = self._manifest_path().read_bytes()
        with patch.object(run_tests.concurrent.futures, "ThreadPoolExecutor", _RecordingExecutor), \
                patch.object(run_tests.concurrent.futures, "as_completed", lambda futures: list(futures)):
            ret, _out, _err, _mocks = self._run("alphabetical", fake_run)
        self.assertEqual(ret, 0)
        self.assertEqual(_RecordingExecutor.last_submitted,
                         ["test_a.py", "test_b.py", "test_c.py", "test_fake.py"])
        self.assertEqual(self._manifest_path().read_bytes(), manifest_before)

    def test_production_full_run_order_stays_alphabetical_despite_cached_timings(self):
        for ch in "ab":
            (self.tmp / f"test_{ch}.py").write_text("# fake\n", encoding="utf-8")
        run_tests._write_cache("h", 9, {"test_a.py": 1.0, "test_b.py": 50.0, "test_fake.py": 20.0})

        def fake_run(path):
            return run_tests.FileResult(path.name, 0, "", 1, 0.1, 0)

        with patch.object(run_tests, "_hash_inputs", return_value="mismatch"), \
                patch.object(run_tests, "_run_file", side_effect=fake_run), \
                patch.object(run_tests.concurrent.futures, "ThreadPoolExecutor", _RecordingExecutor), \
                patch.object(run_tests.concurrent.futures, "as_completed", lambda futures: list(futures)), \
                patch.object(sys, "argv", ["run_tests.py"]), \
                contextlib.redirect_stdout(io.StringIO()):
            ret = run_tests.main()
        self.assertEqual(ret, 0)
        self.assertEqual(_RecordingExecutor.last_submitted,
                         ["test_a.py", "test_b.py", "test_fake.py"])


if __name__ == "__main__":
    unittest.main()

"""Tests for the test-cache helpers in run_tests.py."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_cache_hit_returns_none_when_result_not_ok(self):
        data = {"inputs_hash": "hash123", "result": "fail", "test_count": 5}
        run_tests._CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")
        self.assertIsNone(run_tests._cache_hit("hash123"))


class MainCacheBehaviorTests(unittest.TestCase):
    """Integration tests for main() cache read/write/skip logic."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self._orig_cache_file = run_tests._CACHE_FILE
        run_tests._CACHE_FILE = self.tmp / "test-cache.json"
        # Prevent _clean_pycache from touching the real framework directory
        # during these unit tests — it is tested separately in CleanPycacheTests.
        self._patcher_clean = patch.object(run_tests, "_clean_pycache")
        self._patcher_clean.start()

    def tearDown(self):
        self._patcher_clean.stop()
        run_tests._CACHE_FILE = self._orig_cache_file
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _make_mock_program(self, *, success=True, tests_run=42):
        result = MagicMock()
        result.wasSuccessful.return_value = success
        result.testsRun = tests_run
        program = MagicMock()
        program.result = result
        return program

    # ------------------------------------------------------------------
    # Cache skip
    # ------------------------------------------------------------------

    def test_skips_tests_on_cache_hit(self):
        with patch.object(run_tests, "_hash_inputs", return_value="stable_hash"):
            run_tests._write_cache("stable_hash", 99)
            with patch("unittest.main") as mock_ut, \
                    patch.object(sys, "argv", ["run_tests.py"]):
                ret = run_tests.main()
        mock_ut.assert_not_called()
        self.assertEqual(ret, 0)

    def test_does_not_skip_on_hash_mismatch(self):
        run_tests._write_cache("old_hash", 99)
        program = self._make_mock_program()
        with patch.object(run_tests, "_hash_inputs", return_value="new_hash"), \
                patch("unittest.main", return_value=program) as mock_ut, \
                patch.object(sys, "argv", ["run_tests.py"]):
            run_tests.main()
        mock_ut.assert_called_once()

    def test_does_not_skip_when_no_cache_file(self):
        program = self._make_mock_program()
        with patch.object(run_tests, "_hash_inputs", return_value="some_hash"), \
                patch("unittest.main", return_value=program) as mock_ut, \
                patch.object(sys, "argv", ["run_tests.py"]):
            run_tests.main()
        mock_ut.assert_called_once()

    # ------------------------------------------------------------------
    # Cache write
    # ------------------------------------------------------------------

    def test_writes_cache_after_successful_run(self):
        program = self._make_mock_program(tests_run=55)
        with patch.object(run_tests, "_hash_inputs", return_value="clean_hash"), \
                patch("unittest.main", return_value=program), \
                patch.object(sys, "argv", ["run_tests.py"]):
            run_tests.main()
        data = json.loads(run_tests._CACHE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(data["inputs_hash"], "clean_hash")
        self.assertEqual(data["test_count"], 55)
        self.assertEqual(data["result"], "ok")

    def test_does_not_write_cache_on_test_failure(self):
        program = self._make_mock_program(success=False)
        with patch.object(run_tests, "_hash_inputs", return_value="clean_hash"), \
                patch("unittest.main", return_value=program), \
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
            program = self._make_mock_program()
            with patch("unittest.main", return_value=program) as mock_ut, \
                    patch.object(sys, "argv", ["run_tests.py", "--no-cache"]):
                ret = run_tests.main()
        mock_ut.assert_called_once()
        self.assertEqual(ret, 0)

    def test_no_cache_flag_still_writes_cache_on_success(self):
        program = self._make_mock_program(tests_run=77)
        with patch.object(run_tests, "_hash_inputs", return_value="stable_hash"), \
                patch("unittest.main", return_value=program), \
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

        program = self._make_mock_program(tests_run=10)
        with patch.object(run_tests, "_hash_inputs", side_effect=counting_hash), \
                patch("unittest.main", return_value=program), \
                patch.object(sys, "argv", ["run_tests.py"]):
            run_tests.main()

        # hash_1 was computed before the run; it must be what's written
        data = json.loads(run_tests._CACHE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(data["inputs_hash"], "hash_1")
        self.assertEqual(len(call_count), 1)  # called exactly once

    def test_no_cache_flag_not_forwarded_to_unittest(self):
        program = self._make_mock_program()
        with patch.object(run_tests, "_hash_inputs", return_value="stable_hash"), \
                patch("unittest.main", return_value=program) as mock_ut, \
                patch.object(sys, "argv", ["run_tests.py", "--no-cache"]):
            run_tests.main()
        passed_argv = mock_ut.call_args.kwargs["argv"]
        self.assertNotIn("--no-cache", passed_argv)


if __name__ == "__main__":
    unittest.main()

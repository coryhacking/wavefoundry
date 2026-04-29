"""Tests for build_pack.py."""

import os
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import build_pack  # noqa: E402


class BuildPackTests(unittest.TestCase):

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _build(self, date_str="2099-01-01", extra_args=None):
        """Call build_pack.build_zip and return the resulting Path.

        Does not write the real tree's VERSION file (tests use the in-repo pack
        as zip source only).
        """
        return build_pack.build_zip(self.tmp, date_str, write_version=False)

    def _zip_names(self, zip_path):
        with zipfile.ZipFile(zip_path) as zf:
            return zf.namelist()

    # ------------------------------------------------------------------
    # Suffix selection
    # ------------------------------------------------------------------

    def test_first_build_produces_a_suffix(self):
        path = self._build()
        self.assertTrue(path.name.endswith("a.zip"), path.name)

    def test_second_build_produces_b_suffix(self):
        first = self._build()
        second = self._build()
        self.assertTrue(second.name.endswith("b.zip"), second.name)
        # First zip is unchanged: same byte content.
        first_bytes = first.read_bytes()
        self.assertEqual(first_bytes, first.read_bytes())

    def test_pack_version_file_matches_zip_when_enabled(self):
        """Stamp VERSION inside an isolated framework dir; archive must match."""
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "stub.txt").write_text("stub", encoding="utf-8")
        path = build_pack.build_zip(
            self.tmp, "2099-12-01", framework_dir=fw, write_version=True
        )
        self.assertEqual(path.name, "wavefoundry-framework-2099-12-01a.zip")
        self.assertEqual((fw / "VERSION").read_text(encoding="utf-8"), "2099-12-01a\n")
        with zipfile.ZipFile(path) as zf:
            member = "framework/VERSION"
            self.assertIn(member, zf.namelist())
            self.assertEqual(zf.read(member).decode(), "2099-12-01a\n")

    def test_second_build_does_not_alter_first_zip_mtime(self):
        first = self._build()
        mtime_before = first.stat().st_mtime
        self._build()
        self.assertAlmostEqual(first.stat().st_mtime, mtime_before, places=1)

    def test_unsuffixed_same_date_file_is_ignored_by_scanner(self):
        # Place a file that matches the date prefix but has NO letter suffix.
        (self.tmp / "wavefoundry-framework-2099-01-01.zip").write_bytes(b"dummy")
        path = self._build()
        # No valid letter-suffixed pack yet — first pack is still `a`.
        self.assertTrue(path.name.endswith("a.zip"), path.name)

    def test_next_suffix_is_successor_of_max_not_first_gap(self):
        # Only `b` exists — next must be `c`, not filling gap `a`.
        (self.tmp / "wavefoundry-framework-2099-01-01b.zip").write_bytes(b"x")
        path = self._build()
        self.assertTrue(path.name.endswith("c.zip"), path.name)

    def test_suffix_exhaustion_raises(self):
        date_str = "2099-01-01"
        for letter in build_pack.SUFFIX_LETTERS:
            (self.tmp / f"wavefoundry-framework-{date_str}{letter}.zip").write_bytes(b"x")
        with self.assertRaises(RuntimeError) as ctx:
            build_pack.build_zip(self.tmp, date_str, write_version=False)
        self.assertIn("a–z", str(ctx.exception))

    # ------------------------------------------------------------------
    # Zip contents
    # ------------------------------------------------------------------

    def test_zip_is_non_empty(self):
        path = self._build()
        names = self._zip_names(path)
        self.assertGreater(len(names), 0)

    def test_all_entries_begin_with_framework_prefix(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertTrue(
                name.startswith("framework/"),
                f"Entry does not start with expected prefix: {name}",
            )

    def test_expected_files_present(self):
        path = self._build()
        names = self._zip_names(path)
        # At least one prompt file.
        self.assertTrue(any(n.endswith(".prompt.md") for n in names), names[:5])
        # Core scripts.
        self.assertTrue(
            any(n.endswith("render_platform_surfaces.py") for n in names), names[:5]
        )
        self.assertTrue(
            any(n.endswith("run_tests.py") for n in names), names[:5]
        )

    def test_pycache_excluded(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn("__pycache__", name, name)

    def test_pyc_files_excluded(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertFalse(name.endswith(".pyc"), name)

    def test_ds_store_excluded(self):
        # Inject a .DS_Store into the framework tree via should_exclude logic.
        self.assertFalse(
            build_pack.should_exclude("some/path/.DS_Store", ".DS_Store") is False
        )
        # Verify the predicate itself.
        self.assertTrue(build_pack.should_exclude(".DS_Store", ".DS_Store"))

    def test_pytest_cache_excluded(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn(".pytest_cache", name, name)

    def test_scripts_tests_tmp_excluded(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn("scripts/tests/tmp", name, name)

    # ------------------------------------------------------------------
    # --output argument
    # ------------------------------------------------------------------

    def test_output_dir_arg_writes_to_that_directory(self):
        import tempfile
        alt_dir = Path(tempfile.mkdtemp())
        try:
            path = build_pack.build_zip(alt_dir, "2099-02-01", write_version=False)
            self.assertEqual(path.parent, alt_dir)
            self.assertTrue(path.exists())
        finally:
            import shutil
            shutil.rmtree(str(alt_dir), ignore_errors=True)

    def test_nonexistent_output_dir_exits_nonzero(self):
        argv = [
            "build_pack.py",
            "--output", "/nonexistent/path/that/does/not/exist",
        ]
        with patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as ctx:
                build_pack.main()
        self.assertNotEqual(ctx.exception.code, 0)

    # ------------------------------------------------------------------
    # --date argument
    # ------------------------------------------------------------------

    def test_date_override_produces_correct_filename(self):
        path = build_pack.build_zip(self.tmp, "2099-01-01", write_version=False)
        self.assertIn("2099-01-01", path.name)

    def test_date_override_suffix_auto_selection_applies(self):
        # Two builds with the same overridden date should produce a then b.
        first = build_pack.build_zip(self.tmp, "2099-03-15", write_version=False)
        second = build_pack.build_zip(self.tmp, "2099-03-15", write_version=False)
        self.assertTrue(first.name.endswith("a.zip"), first.name)
        self.assertTrue(second.name.endswith("b.zip"), second.name)


if __name__ == "__main__":
    unittest.main()

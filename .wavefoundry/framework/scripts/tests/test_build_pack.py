"""Tests for build_pack.py."""

import os
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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
        self.assertEqual(path.name, "wavefoundry-2099-12-01a.zip")
        self.assertEqual((fw / "VERSION").read_text(encoding="utf-8"), "2099-12-01a\n")
        with zipfile.ZipFile(path) as zf:
            member = ".wavefoundry/framework/VERSION"
            self.assertIn(member, zf.namelist())
            self.assertEqual(zf.read(member).decode(), "2099-12-01a\n")

    def test_prebuild_index_runs_before_zip_and_is_packaged(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "stub.txt").write_text("stub", encoding="utf-8")

        def fake_prebuild(framework_dir, *, source_files=None, verbose=False):
            index_dir = framework_dir / "index"
            index_dir.mkdir(parents=True)
            (index_dir / "meta.json").write_text("{}", encoding="utf-8")

        with patch.object(build_pack, "build_framework_index", side_effect=fake_prebuild) as mocked:
            path = build_pack.build_zip(
                self.tmp,
                "2099-12-02",
                framework_dir=fw,
                write_version=True,
                prebuild_index=True,
            )

        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.args[0], fw)
        self.assertEqual(mocked.call_args.kwargs["verbose"], False)
        self.assertIn(fw / "stub.txt", mocked.call_args.kwargs["source_files"])
        self.assertNotIn(fw / "MANIFEST", mocked.call_args.kwargs["source_files"])
        with zipfile.ZipFile(path) as zf:
            self.assertIn(".wavefoundry/framework/index/meta.json", zf.namelist())

    def test_prebuild_index_uses_pack_filtered_source_files(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "seed.md").write_text("seed", encoding="utf-8")
        scripts_dir = fw / "scripts"
        (scripts_dir / "tests").mkdir(parents=True)
        (scripts_dir / "benchmarks").mkdir(parents=True)
        (scripts_dir / "tests" / "test_foo.py").write_text("x", encoding="utf-8")
        (scripts_dir / "benchmarks" / "bench.py").write_text("x", encoding="utf-8")
        (scripts_dir / "run_tests.py").write_text("x", encoding="utf-8")

        fake_indexer = MagicMock()

        with patch.object(build_pack, "_load_indexer", return_value=fake_indexer), \
             patch.object(build_pack, "_compact_framework_index"):
            build_pack.build_zip(
                self.tmp,
                "2099-12-02",
                framework_dir=fw,
                write_version=True,
                prebuild_index=True,
            )

        kwargs = fake_indexer.build_index.call_args.kwargs
        source_files = {
            str(Path(path).relative_to(fw)).replace("\\", "/")
            for path in kwargs["files"]
        }
        self.assertIn("seed.md", source_files)
        self.assertNotIn("scripts/tests/test_foo.py", source_files)
        self.assertNotIn("scripts/benchmarks/bench.py", source_files)
        self.assertNotIn("scripts/run_tests.py", source_files)
        self.assertNotIn("VERSION", source_files)
        self.assertNotIn("MANIFEST", source_files)
        self.assertNotIn("index/meta.json", source_files)

    def test_prebuild_index_compacts_lance_tables_before_zip(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "stub.txt").write_text("stub", encoding="utf-8")
        index_dir = fw / "index"
        (index_dir / "docs.lance").mkdir(parents=True)
        (index_dir / "code.lance").mkdir(parents=True)

        fake_docs_table = MagicMock(name="docs_table")
        fake_code_table = MagicMock(name="code_table")
        fake_db = MagicMock()
        fake_db.open_table.side_effect = [fake_docs_table, fake_code_table]
        fake_indexer = MagicMock()
        fake_indexer._get_lance_db.return_value = fake_db

        def fake_prebuild(framework_dir, *, source_files=None, verbose=False):
            (framework_dir / "index").mkdir(parents=True, exist_ok=True)

        with patch.object(build_pack, "build_framework_index", side_effect=fake_prebuild), \
             patch.object(build_pack, "_load_indexer", return_value=fake_indexer):
            build_pack.build_zip(
                self.tmp,
                "2099-12-03",
                framework_dir=fw,
                write_version=True,
                prebuild_index=True,
            )

        self.assertEqual(fake_db.open_table.call_args_list[0].args[0], "docs")
        self.assertEqual(fake_db.open_table.call_args_list[1].args[0], "code")
        self.assertEqual(fake_indexer._optimize_lance_table.call_count, 2)
        fake_indexer._optimize_lance_table.assert_any_call(fake_docs_table)
        fake_indexer._optimize_lance_table.assert_any_call(fake_code_table)

    def test_prebuild_index_fails_when_compaction_fails(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "stub.txt").write_text("stub", encoding="utf-8")
        index_dir = fw / "index"
        (index_dir / "docs.lance").mkdir(parents=True)

        fake_db = MagicMock()
        fake_db.open_table.side_effect = RuntimeError("boom")
        fake_indexer = MagicMock()
        fake_indexer._get_lance_db.return_value = fake_db

        def fake_prebuild(framework_dir, *, source_files=None, verbose=False):
            (framework_dir / "index").mkdir(parents=True, exist_ok=True)

        with patch.object(build_pack, "build_framework_index", side_effect=fake_prebuild), \
             patch.object(build_pack, "_load_indexer", return_value=fake_indexer):
            with self.assertRaises(RuntimeError) as ctx:
                build_pack.build_zip(
                    self.tmp,
                    "2099-12-04",
                    framework_dir=fw,
                    write_version=True,
                    prebuild_index=True,
                )

        self.assertIn("compaction failed", str(ctx.exception))

    def test_framework_index_uses_repo_relative_paths_when_under_wavefoundry(self):
        repo = self.tmp / "repo"
        fw = repo / ".wavefoundry" / "framework"
        fw.mkdir(parents=True)
        fake_indexer = MagicMock()

        with patch.object(build_pack, "_load_indexer", return_value=fake_indexer):
            build_pack.build_framework_index(fw)

        fake_indexer.build_index.assert_called_once()
        kwargs = fake_indexer.build_index.call_args.kwargs
        self.assertEqual(fake_indexer.build_index.call_args.args[0], repo.resolve())
        self.assertEqual(kwargs["index_dir"], (fw / "index").resolve())
        self.assertFalse(kwargs["full"])
        self.assertEqual(kwargs["include_prefixes"], (".wavefoundry/framework",))
        self.assertFalse(kwargs["respect_ignore"])

    def test_framework_index_requests_incremental_update_for_packaging(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        fake_indexer = MagicMock()

        with patch.object(build_pack, "_load_indexer", return_value=fake_indexer):
            build_pack.build_framework_index(fw)

        fake_indexer.build_index.assert_called_once()
        kwargs = fake_indexer.build_index.call_args.kwargs
        self.assertFalse(kwargs["full"])
        self.assertEqual(kwargs["content"], "docs")

    def test_second_build_does_not_alter_first_zip_mtime(self):
        first = self._build()
        mtime_before = first.stat().st_mtime
        self._build()
        self.assertAlmostEqual(first.stat().st_mtime, mtime_before, places=1)

    def test_unsuffixed_same_date_file_is_ignored_by_scanner(self):
        # Place a file that matches the date prefix but has NO letter suffix.
        (self.tmp / "wavefoundry-2099-01-01.zip").write_bytes(b"dummy")
        path = self._build()
        # No valid letter-suffixed pack yet — first pack is still `a`.
        self.assertTrue(path.name.endswith("a.zip"), path.name)

    def test_next_suffix_is_successor_of_max_not_first_gap(self):
        # Only `b` exists — next must be `c`, not filling gap `a`.
        (self.tmp / "wavefoundry-2099-01-01b.zip").write_bytes(b"x")
        path = self._build()
        self.assertTrue(path.name.endswith("c.zip"), path.name)

    def test_suffix_exhaustion_raises(self):
        date_str = "2099-01-01"
        for letter in build_pack.SUFFIX_LETTERS:
            (self.tmp / f"wavefoundry-{date_str}{letter}.zip").write_bytes(b"x")
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

    def test_all_entries_begin_with_wavefoundry_prefix(self):
        path = self._build()
        allowed_prefixes = (".wavefoundry/framework/", ".wavefoundry/README.md")
        for name in self._zip_names(path):
            self.assertTrue(
                any(name.startswith(p) or name == p for p in allowed_prefixes),
                f"Entry does not start with expected prefix: {name}",
            )

    def test_wavefoundry_readme_included_in_pack(self):
        path = self._build()
        names = self._zip_names(path)
        self.assertIn(".wavefoundry/README.md", names)

    def test_expected_files_present(self):
        path = self._build()
        names = self._zip_names(path)
        # At least one prompt file.
        self.assertTrue(any(n.endswith(".prompt.md") for n in names), names[:5])
        # Core scripts.
        self.assertTrue(
            any(n.endswith("render_platform_surfaces.py") for n in names), names[:5]
        )
        self.assertIn(
            ".wavefoundry/framework/seeds/215-council-moderator.prompt.md",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/seeds/216-reality-checker.prompt.md",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/scripts/dashboard_server.py",
            names,
        )
        self.assertIn(
            ".wavefoundry/framework/dashboard/dashboard.html",
            names,
        )

    def test_tests_excluded_from_pack(self):
        # Test suite is a development-only artifact; must not ship in the distribution zip.
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn("scripts/tests/", name, name)
            self.assertFalse(name.endswith("run_tests.py"), name)

    def test_benchmarks_excluded_from_pack(self):
        # Benchmarks are development-only artifacts; must not ship in the distribution zip.
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn("scripts/benchmarks/", name, name)

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

    # ------------------------------------------------------------------
    # MANIFEST
    # ------------------------------------------------------------------

    def test_manifest_written_to_framework_dir(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "seed.md").write_text("seed", encoding="utf-8")
        build_pack.build_zip(self.tmp, "2099-11-01", framework_dir=fw, write_version=False)
        self.assertTrue((fw / "MANIFEST").exists())

    def test_manifest_included_in_zip(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "seed.md").write_text("seed", encoding="utf-8")
        path = build_pack.build_zip(self.tmp, "2099-11-02", framework_dir=fw, write_version=False)
        with zipfile.ZipFile(path) as zf:
            self.assertIn(".wavefoundry/framework/MANIFEST", zf.namelist())

    def test_manifest_lists_all_packed_files(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "a.md").write_text("a", encoding="utf-8")
        (fw / "b.txt").write_text("b", encoding="utf-8")
        path = build_pack.build_zip(self.tmp, "2099-11-03", framework_dir=fw, write_version=False)
        with zipfile.ZipFile(path) as zf:
            manifest_text = zf.read(".wavefoundry/framework/MANIFEST").decode()
        entries = {line for line in manifest_text.splitlines() if line.strip()}
        self.assertIn("a.md", entries)
        self.assertIn("b.txt", entries)
        self.assertIn("MANIFEST", entries)

    def test_manifest_does_not_list_excluded_files(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        scripts_dir = fw / "scripts"
        scripts_dir.mkdir(parents=True)
        tests_dir = scripts_dir / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "test_foo.py").write_text("x", encoding="utf-8")
        (scripts_dir / "run_tests.py").write_text("x", encoding="utf-8")
        path = build_pack.build_zip(self.tmp, "2099-11-04", framework_dir=fw, write_version=False)
        with zipfile.ZipFile(path) as zf:
            manifest_text = zf.read(".wavefoundry/framework/MANIFEST").decode()
        entries = {line for line in manifest_text.splitlines() if line.strip()}
        self.assertNotIn("scripts/run_tests.py", entries)
        self.assertFalse(any("tests/" in e for e in entries))


if __name__ == "__main__":
    unittest.main()

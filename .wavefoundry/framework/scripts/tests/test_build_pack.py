"""Tests for build_pack.py."""

import json
import os
import sys
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import build_pack  # noqa: E402

FAKE_PREFIX = "2tm5"
FAKE_VERSION = "1.0.0"


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

    def _build(self, version=FAKE_VERSION, build_prefix=FAKE_PREFIX, extra_args=None):
        """Call build_pack.build_zip and return the resulting Path."""
        return build_pack.build_zip(self.tmp, version, build_prefix, write_version=False, update_manifest=False)

    def _zip_names(self, zip_path):
        with zipfile.ZipFile(zip_path) as zf:
            return zf.namelist()

    # ------------------------------------------------------------------
    # Filename format
    # ------------------------------------------------------------------

    def test_zip_filename_uses_semver_format(self):
        """Zip filename must be wavefoundry-MAJOR.MINOR.PATCH.<build>.zip."""
        path = self._build(version="1.0.0", build_prefix="2abc")
        self.assertEqual(path.name, "wavefoundry-1.0.0.2abc.zip")

    def test_build_suffix_uses_rightmost_four_characters(self):
        self.assertEqual(build_pack._build_suffix("12tm5"), "2tm5")
        self.assertEqual(build_pack._build_suffix("abcd"), "abcd")

    def test_pack_version_file_uses_plus_build_separator(self):
        """VERSION file uses MAJOR.MINOR.PATCH+<build> with '+' separator."""
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "stub.txt").write_text("stub", encoding="utf-8")
        path = build_pack.build_zip(
            self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=True, update_manifest=False
        )
        self.assertEqual(path.name, "wavefoundry-1.0.0.2tm5.zip")
        self.assertEqual((fw / "VERSION").read_text(encoding="utf-8"), "1.0.0+2tm5\n")
        with zipfile.ZipFile(path) as zf:
            member = ".wavefoundry/framework/VERSION"
            self.assertIn(member, zf.namelist())
            self.assertEqual(zf.read(member).decode(), "1.0.0+2tm5\n")

    def test_multi_digit_minor_version_in_filename(self):
        """1.10.0 must produce the correct filename (not confused with 1.1.0)."""
        path = self._build(version="1.10.0", build_prefix="2xyz")
        self.assertEqual(path.name, "wavefoundry-1.10.0.2xyz.zip")

    # ------------------------------------------------------------------
    # write_pack_version
    # ------------------------------------------------------------------

    def test_write_pack_version_stamps_plus_format(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        build_pack.write_pack_version(fw, "1.0.0", "2tm5")
        self.assertEqual((fw / "VERSION").read_text(encoding="utf-8"), "1.0.0+2tm5\n")

    # ------------------------------------------------------------------
    # Prebuild index
    # ------------------------------------------------------------------

    def test_prebuild_index_runs_before_zip_and_is_packaged(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "stub.txt").write_text("stub", encoding="utf-8")

        def fake_prebuild(framework_dir, *, source_files=None, verbose=False):
            index_dir = framework_dir / "index"
            index_dir.mkdir(parents=True)
            (index_dir / "meta.json").write_text("{}", encoding="utf-8")

        with patch.object(build_pack, "build_framework_index", side_effect=fake_prebuild) as mocked, \
             patch.object(build_pack, "_compact_framework_index") as compact_mock:
            path = build_pack.build_zip(
                self.tmp,
                "1.0.0",
                "12tm5",
                framework_dir=fw,
                write_version=True,
                update_manifest=False,
                prebuild_index=True,
            )

        mocked.assert_called_once()
        compact_mock.assert_called_once_with(fw, verbose=False)
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
                "1.0.0",
                "12tm5",
                framework_dir=fw,
                write_version=True,
                update_manifest=False,
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
                "1.0.0",
                "12tm5",
                framework_dir=fw,
                write_version=True,
                update_manifest=False,
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
                    "1.0.0",
                    "12tm5",
                    framework_dir=fw,
                    write_version=True,
                    update_manifest=False,
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

    # ------------------------------------------------------------------
    # Zip contents
    # ------------------------------------------------------------------

    def test_zip_is_non_empty(self):
        path = self._build()
        names = self._zip_names(path)
        self.assertGreater(len(names), 0)

    def test_all_entries_begin_with_wavefoundry_prefix(self):
        path = self._build()
        allowed_prefixes = (
            ".wavefoundry/framework/",
            ".wavefoundry/README.md",
            ".wavefoundry/CHANGELOG.md",
        )
        for name in self._zip_names(path):
            self.assertTrue(
                any(name.startswith(p) or name == p for p in allowed_prefixes),
                f"Entry does not start with expected prefix: {name}",
            )

    def test_wavefoundry_readme_included_in_pack(self):
        path = self._build()
        names = self._zip_names(path)
        self.assertIn(".wavefoundry/README.md", names)

    def test_wavefoundry_changelog_included_in_pack(self):
        path = self._build()
        names = self._zip_names(path)
        self.assertIn(".wavefoundry/CHANGELOG.md", names)

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
            ".wavefoundry/framework/seeds/215-wave-council.prompt.md",
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
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn("scripts/tests/", name, name)
            self.assertFalse(name.endswith("run_tests.py"), name)

    def test_benchmarks_excluded_from_pack(self):
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
        self.assertFalse(
            build_pack.should_exclude("some/path/.DS_Store", ".DS_Store") is False
        )
        self.assertTrue(build_pack.should_exclude(".DS_Store", ".DS_Store"))

    def test_pytest_cache_excluded(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn(".pytest_cache", name, name)

    def test_scripts_tests_tmp_excluded(self):
        path = self._build()
        for name in self._zip_names(path):
            self.assertNotIn("scripts/tests/tmp", name, name)

    def test_transient_artifact_extensions_excluded(self):
        """Regression for 130o2: transient artifacts (.lock, .log, editor backups) must not ship."""
        for ext in build_pack.TRANSIENT_ARTIFACT_EXTENSIONS:
            self.assertTrue(
                build_pack.should_exclude(f"some/path/file{ext}", f"file{ext}"),
                f"should_exclude must reject *{ext} files",
            )
            self.assertTrue(
                build_pack.should_exclude(f"file{ext}", f"file{ext}"),
                f"should_exclude must reject root-level *{ext} files",
            )

    def test_lock_and_log_files_not_in_pack(self):
        """End-to-end: a framework tree with lock/log files produces a pack without them."""
        fw = self.tmp / "fw-with-transients"
        fw.mkdir(parents=True)
        (fw / "scripts").mkdir()
        (fw / "scripts" / "tool.py").write_text("def t(): pass\n", encoding="utf-8")
        (fw / "test-run.lock").write_text("pid\n", encoding="utf-8")
        (fw / "index").mkdir()
        (fw / "index" / "index-build.lock").write_text("pid\n", encoding="utf-8")
        (fw / "index" / "index-build.log").write_text("log line\n", encoding="utf-8")
        (fw / "stray.bak").write_text("editor backup\n", encoding="utf-8")
        (fw / "stray.tmp").write_text("temp\n", encoding="utf-8")

        path = build_pack.build_zip(
            self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False
        )
        names = self._zip_names(path)
        for name in names:
            self.assertFalse(name.endswith(".lock"), f"lock file leaked: {name}")
            self.assertFalse(name.endswith(".log"), f"log file leaked: {name}")
            self.assertFalse(name.endswith(".bak"), f"backup file leaked: {name}")
            self.assertFalse(name.endswith(".tmp"), f"tmp file leaked: {name}")
        # Regular source files still pack
        self.assertTrue(any(n.endswith("scripts/tool.py") for n in names))

    # ------------------------------------------------------------------
    # --output argument
    # ------------------------------------------------------------------

    def test_output_dir_arg_writes_to_that_directory(self):
        import tempfile
        alt_dir = Path(tempfile.mkdtemp())
        try:
            path = build_pack.build_zip(alt_dir, "1.0.0", "2abc", write_version=False, update_manifest=False)
            self.assertEqual(path.parent, alt_dir)
            self.assertTrue(path.exists())
        finally:
            import shutil
            shutil.rmtree(str(alt_dir), ignore_errors=True)

    def test_nonexistent_output_dir_exits_nonzero(self):
        argv = [
            "build_pack.py",
            "--version", "1.0.0",
            "--output", "/nonexistent/path/that/does/not/exist",
        ]
        with patch.object(sys, "argv", argv), patch.object(build_pack, "_reexec_with_venv_if_needed"):
            with self.assertRaises(SystemExit) as ctx:
                build_pack.main()
        self.assertNotEqual(ctx.exception.code, 0)

    def test_version_flag_is_required(self):
        """main() exits non-zero when --version is omitted."""
        argv = ["build_pack.py", "--output", str(self.tmp)]
        with patch.object(sys, "argv", argv), patch.object(build_pack, "_reexec_with_venv_if_needed"):
            with self.assertRaises(SystemExit) as ctx:
                build_pack.main()
        self.assertNotEqual(ctx.exception.code, 0)

    def test_invalid_version_format_exits_nonzero(self):
        """main() rejects version strings that are not MAJOR.MINOR.PATCH."""
        argv = [
            "build_pack.py",
            "--version", "2026-05-20a",
            "--output", str(self.tmp),
        ]
        with patch.object(sys, "argv", argv), patch.object(build_pack, "_reexec_with_venv_if_needed"):
            with self.assertRaises(SystemExit) as ctx:
                build_pack.main()
        self.assertNotEqual(ctx.exception.code, 0)

    def test_pre_v1_versions_exit_nonzero(self):
        argv = [
            "build_pack.py",
            "--version", "0.8.0",
            "--output", str(self.tmp),
        ]
        with patch.object(sys, "argv", argv), patch.object(build_pack, "_reexec_with_venv_if_needed"):
            with self.assertRaises(SystemExit) as ctx:
                build_pack.main()
        self.assertNotEqual(ctx.exception.code, 0)

    # ------------------------------------------------------------------
    # MANIFEST
    # ------------------------------------------------------------------

    def test_manifest_deleted_from_framework_dir_after_zip(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "seed.md").write_text("seed", encoding="utf-8")
        build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False)
        self.assertFalse((fw / "MANIFEST").exists(), "MANIFEST should be deleted after packaging")

    def test_manifest_included_in_zip(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "seed.md").write_text("seed", encoding="utf-8")
        path = build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False)
        with zipfile.ZipFile(path) as zf:
            self.assertIn(".wavefoundry/framework/MANIFEST", zf.namelist())

    def test_manifest_lists_all_packed_files(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "a.md").write_text("a", encoding="utf-8")
        (fw / "b.txt").write_text("b", encoding="utf-8")
        path = build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False)
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
        path = build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False)
        with zipfile.ZipFile(path) as zf:
            manifest_text = zf.read(".wavefoundry/framework/MANIFEST").decode()
        entries = {line for line in manifest_text.splitlines() if line.strip()}
        self.assertNotIn("scripts/run_tests.py", entries)
        self.assertFalse(any("tests/" in e for e in entries))

class ManifestRevisionTests(unittest.TestCase):
    """Tests for update_manifest_revision()."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        (self.tmp / "docs" / "prompts").mkdir(parents=True)
        self.manifest_path = self.tmp / "docs" / "prompts" / "prompt-surface-manifest.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_manifest(self, data: dict) -> None:
        self.manifest_path.write_text(json.dumps(data), encoding="utf-8")

    def _read_manifest(self) -> dict:
        import json
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def test_writes_revision_to_manifest(self):
        self._write_manifest({"framework_revision": "1.0.0+2tm5", "other": "val"})
        build_pack.update_manifest_revision(self.tmp, "1.0.0+2xyz")
        self.assertEqual(self._read_manifest()["framework_revision"], "1.0.0+2xyz")

    def test_preserves_other_manifest_fields(self):
        self._write_manifest({"framework_revision": "1.0.0+2tm5", "other": "val"})
        build_pack.update_manifest_revision(self.tmp, "1.0.0+2xyz")
        self.assertEqual(self._read_manifest()["other"], "val")

    def test_adds_field_when_missing(self):
        self._write_manifest({"other_key": "value"})
        build_pack.update_manifest_revision(self.tmp, "1.0.0+2xyz")
        self.assertEqual(self._read_manifest()["framework_revision"], "1.0.0+2xyz")

    def test_warns_when_manifest_missing(self):
        import io
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            build_pack.update_manifest_revision(self.tmp, "1.0.0+2xyz")
        self.assertIn("warning", captured.getvalue())

    def test_manifest_not_found_does_not_raise(self):
        build_pack.update_manifest_revision(self.tmp, "1.0.0+2xyz")

    def test_build_zip_stamps_manifest_before_zip_is_written(self):
        fw = self.tmp / ".wavefoundry" / "framework"
        fw.mkdir(parents=True)
        (self.tmp / "docs" / "prompts").mkdir(parents=True, exist_ok=True)
        manifest_path = self.tmp / "docs" / "prompts" / "prompt-surface-manifest.json"
        self._write_manifest({"framework_revision": "1.0.0+2tm5"})
        (fw / "stub.txt").write_text("stub", encoding="utf-8")
        build_pack.build_zip(self.tmp, "1.0.0", "2xyz", framework_dir=fw, write_version=False, update_manifest=True)
        import json
        recorded = json.loads(manifest_path.read_text(encoding="utf-8"))["framework_revision"]
        self.assertEqual(recorded, "1.0.0+2xyz")


class DocsGateTests(unittest.TestCase):
    """Tests for check_docs_gate()."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self.bin_dir = self.tmp / ".wavefoundry" / "bin"
        self.bin_dir.mkdir(parents=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _make_script(self, name: str, exit_code: int) -> None:
        import stat
        script = self.bin_dir / name
        script.write_text(f"#!/bin/sh\nexit {exit_code}\n", encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def test_passes_when_both_commands_succeed(self):
        self._make_script("docs-gardener", 0)
        self._make_script("docs-lint", 0)
        build_pack.check_docs_gate(self.tmp)

    def test_fails_when_docs_gardener_fails(self):
        self._make_script("docs-gardener", 1)
        self._make_script("docs-lint", 0)
        with self.assertRaises(SystemExit) as ctx:
            build_pack.check_docs_gate(self.tmp)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_fails_when_docs_lint_fails(self):
        self._make_script("docs-gardener", 0)
        self._make_script("docs-lint", 1)
        with self.assertRaises(SystemExit) as ctx:
            build_pack.check_docs_gate(self.tmp)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_fails_when_docs_gardener_not_found(self):
        with self.assertRaises(SystemExit) as ctx:
            build_pack.check_docs_gate(self.tmp)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_fails_when_docs_lint_not_found(self):
        self._make_script("docs-gardener", 0)
        with self.assertRaises(SystemExit) as ctx:
            build_pack.check_docs_gate(self.tmp)
        self.assertNotEqual(ctx.exception.code, 0)

    def test_error_message_names_the_failing_command(self):
        import io
        self._make_script("docs-gardener", 0)
        self._make_script("docs-lint", 1)
        captured = io.StringIO()
        with patch("sys.stderr", captured):
            with self.assertRaises(SystemExit):
                build_pack.check_docs_gate(self.tmp)
        self.assertIn("docs-lint", captured.getvalue())


if __name__ == "__main__":
    unittest.main()

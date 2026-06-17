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
        return build_pack.build_zip(self.tmp, version, build_prefix, write_version=False, update_manifest=False, inject_install_templates=False)

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
            self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=True, update_manifest=False, inject_install_templates=False
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
    # Framework index removal (1p4ww)
    # ------------------------------------------------------------------

    def test_build_zip_does_not_ship_framework_index(self):
        # 1p4ww: the framework index is no longer built or shipped — the pack carries
        # framework SOURCE only (seeds/README fold into each project's docs index).
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "seeds").mkdir()
        (fw / "seeds" / "010-install.prompt.md").write_text("seed", encoding="utf-8")
        path = build_pack.build_zip(
            self.tmp,
            "1.0.0",
            "12tm5",
            framework_dir=fw,
            write_version=True,
            update_manifest=False,
            inject_install_templates=False,
        )
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        self.assertFalse(any(".lance" in name for name in names))
        self.assertFalse(any("/framework/index/" in name for name in names))
        self.assertTrue(any(name.endswith("seeds/010-install.prompt.md") for name in names))

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
            # Top-level visible marker files (see build_pack template
            # injection). macOS Finder hides `.wavefoundry/` by default,
            # so these give consumers visible landing files at the root.
            # Replaced INSTALL.md in wave 1p35d (1p35f).
            "install-wavefoundry.md",
            "wavefoundry-install-log.md",
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
            self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False, inject_install_templates=False
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
            path = build_pack.build_zip(alt_dir, "1.0.0", "2abc", write_version=False, update_manifest=False, inject_install_templates=False)
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
        build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False, inject_install_templates=False)
        self.assertFalse((fw / "MANIFEST").exists(), "MANIFEST should be deleted after packaging")

    def test_manifest_included_in_zip(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "seed.md").write_text("seed", encoding="utf-8")
        path = build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False, inject_install_templates=False)
        with zipfile.ZipFile(path) as zf:
            self.assertIn(".wavefoundry/framework/MANIFEST", zf.namelist())

    def test_manifest_lists_all_packed_files(self):
        fw = self.tmp / "mini-fw"
        fw.mkdir(parents=True)
        (fw / "a.md").write_text("a", encoding="utf-8")
        (fw / "b.txt").write_text("b", encoding="utf-8")
        path = build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False, inject_install_templates=False)
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
        path = build_pack.build_zip(self.tmp, "1.0.0", "2tm5", framework_dir=fw, write_version=False, update_manifest=False, inject_install_templates=False)
        with zipfile.ZipFile(path) as zf:
            manifest_text = zf.read(".wavefoundry/framework/MANIFEST").decode()
        entries = {line for line in manifest_text.splitlines() if line.strip()}
        self.assertNotIn("scripts/run_tests.py", entries)
        self.assertFalse(any("tests/" in e for e in entries))

    def test_lint_exclusions_doc_ships_in_pack(self):
        """Wave 1p3b9 (1p3b5): the operator-visible `lint-exclusions.md`
        reference doc lives under `.wavefoundry/framework/docs/` so it ships
        in every release pack. Consumers running `Upgrade wave framework`
        receive the doc; enterprise security review reads it locally.
        Regression guard against accidental relocation outside the pack tree."""
        fw = self.tmp / "mini-fw-with-docs"
        fw.mkdir(parents=True)
        docs_dir = fw / "docs"
        docs_dir.mkdir(parents=True)
        (docs_dir / "lint-exclusions.md").write_text(
            "# docs-lint Exclusions\n\nTest content.\n", encoding="utf-8"
        )
        path = build_pack.build_zip(
            self.tmp, "1.0.0", "2tm5", framework_dir=fw,
            write_version=False, update_manifest=False, inject_install_templates=False,
        )
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        self.assertIn(".wavefoundry/framework/docs/lint-exclusions.md", names)


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
        build_pack.build_zip(self.tmp, "1.0.0", "2xyz", framework_dir=fw, write_version=False, update_manifest=True, inject_install_templates=False)
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


# ---------------------------------------------------------------------------
# Release orchestration helpers (wave 1p347 / change 1p349)
# ---------------------------------------------------------------------------


class ChangelogSectionExtractionTests(unittest.TestCase):
    """Tests for _extract_changelog_section()."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        self.changelog = self.tmp / "CHANGELOG.md"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write(self, text):
        self.changelog.write_text(text, encoding="utf-8")

    def test_extracts_named_section_body_only(self):
        """Heading is excluded; body is returned verbatim."""
        self._write(
            "# Changelog\n\n"
            "## [1.4.0] - 2026-06-03\n\n"
            "### Fixed\n\n- alpha\n- beta\n\n"
            "## [1.3.32] - 2026-05-01\n\n"
            "- previous\n"
        )
        body = build_pack._extract_changelog_section(self.changelog, "1.4.0")
        self.assertIn("### Fixed", body)
        self.assertIn("- alpha", body)
        self.assertNotIn("## [1.4.0]", body)
        self.assertNotIn("## [1.3.32]", body)

    def test_returns_empty_when_section_missing(self):
        """Section absent → empty string (caller refuses the release)."""
        self._write("# Changelog\n\n## [1.3.32]\n\n- previous\n")
        body = build_pack._extract_changelog_section(self.changelog, "1.4.0")
        self.assertEqual(body.strip(), "")

    def test_returns_empty_when_file_absent(self):
        """Missing CHANGELOG → empty string (caller refuses the release)."""
        body = build_pack._extract_changelog_section(
            self.tmp / "missing.md", "1.4.0"
        )
        self.assertEqual(body, "")

    def test_section_at_end_of_file_extracted(self):
        """No subsequent `## [` heading → section runs to EOF."""
        self._write("# Changelog\n\n## [1.4.0]\n\n- only\n")
        body = build_pack._extract_changelog_section(self.changelog, "1.4.0")
        self.assertIn("- only", body)


class ReleaseNotesInstallPrependTests(unittest.TestCase):
    """Wave 1p35d (1p35p): release notes carry an `## Install` block at the
    top so an agent or operator landing on the GitHub Releases page sees the
    zip-at-root → shortcut-phrase flow alongside the download link. Source of
    truth lives at `.wavefoundry/framework/install/install-block.md`."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)
        (self.tmp / build_pack.RELEASE_NOTES_INSTALL_BLOCK_REL.parent).mkdir(
            parents=True, exist_ok=True
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write_block(self, content: str) -> None:
        (self.tmp / build_pack.RELEASE_NOTES_INSTALL_BLOCK_REL).write_text(
            content, encoding="utf-8"
        )

    def test_shipped_block_has_install_and_upgrade_sections(self):
        # The shipped release-notes header must carry BOTH a fresh-install path AND an
        # upgrade path (an existing consumer needs "Upgrade wave framework", not Install).
        repo_root = Path(build_pack.__file__).resolve().parents[3]
        block = (repo_root / build_pack.RELEASE_NOTES_INSTALL_BLOCK_REL).read_text(encoding="utf-8")
        self.assertIn("## Install", block)
        self.assertIn("## Upgrade", block)
        self.assertIn("Upgrade wave framework", block)
        # Install precedes Upgrade in document order.
        self.assertLess(block.index("## Install"), block.index("## Upgrade"))

    def test_upgrade_block_flows_into_assembled_notes(self):
        # The upgrade block reaches the assembled release notes, above the changelog body.
        self._write_block("## Install\n\nfresh.\n\n## Upgrade\n\nUpgrade wave framework\n\n---\n\n")
        notes = build_pack._assemble_release_notes(self.tmp, "### Changed\n\n- thing\n")
        self.assertIn("## Upgrade", notes)
        self.assertIn("Upgrade wave framework", notes)
        self.assertLess(notes.index("## Upgrade"), notes.index("### Changed"))

    def test_install_block_is_prepended_to_changelog_body(self):
        self._write_block("## Install\n\nDrop the zip.\n\n---\n\n")
        notes = build_pack._assemble_release_notes(
            self.tmp, "### Changed\n\n- thing\n"
        )
        self.assertTrue(notes.startswith("## Install"))
        self.assertIn("Drop the zip.", notes)
        # Changelog body still present after the block.
        self.assertIn("### Changed", notes)
        self.assertIn("- thing", notes)
        # Install block precedes the changelog body in document order.
        self.assertLess(notes.index("## Install"), notes.index("### Changed"))

    def test_block_missing_falls_through_to_changelog_only(self):
        """No install block on disk → notes are the CHANGELOG body alone."""
        notes = build_pack._assemble_release_notes(
            self.tmp, "### Changed\n\n- thing\n"
        )
        self.assertEqual(notes, "### Changed\n\n- thing\n")

    def test_empty_block_file_falls_through(self):
        """An on-disk-but-empty block file is treated as no block."""
        self._write_block("")
        notes = build_pack._assemble_release_notes(self.tmp, "### Changed\n- x\n")
        self.assertEqual(notes, "### Changed\n- x\n")

    def test_block_includes_shortcut_phrase_and_supported_hosts(self):
        """The shipped install block at the repo source-of-truth path names the
        canonical shortcut phrase and the supported agent-host list. Regression
        guard against future drift — if the block evolves, this asserts the
        agent-facing affordances stay present."""
        repo_block = (
            Path(__file__).resolve().parents[2]
            / "install" / "install-block.md"
        )
        self.assertTrue(repo_block.is_file(), f"missing {repo_block}")
        text = repo_block.read_text(encoding="utf-8")
        self.assertIn("Install Wavefoundry", text)
        for host in ("Claude Code", "Cursor", "Codex"):
            self.assertIn(host, text)


class ReleasePreflightTests(unittest.TestCase):
    """Tests for pre-flight gate refusals."""

    def _mock_run(self, return_codes_and_outputs):
        """Patch subprocess.run to return a sequence of mocked CompletedProcess objs."""
        class _CP:
            def __init__(self, rc, out="", err=""):
                self.returncode = rc
                self.stdout = out
                self.stderr = err
        results = iter(_CP(rc, out, err) for rc, out, err in return_codes_and_outputs)
        def _next(*args, **kwargs):
            return next(results)
        return _next

    def test_working_tree_dirty_refuses(self):
        runner = self._mock_run([(0, " M foo.py\n", "")])
        with patch("build_pack.subprocess.run", runner):
            with self.assertRaises(RuntimeError) as ctx:
                build_pack._check_git_working_tree_clean(Path("/tmp"))
        self.assertIn("working tree", str(ctx.exception).lower())

    def test_working_tree_clean_passes(self):
        runner = self._mock_run([(0, "", "")])
        with patch("build_pack.subprocess.run", runner):
            build_pack._check_git_working_tree_clean(Path("/tmp"))  # no exception

    def test_non_main_branch_refuses(self):
        runner = self._mock_run([(0, "feature-branch\n", "")])
        with patch("build_pack.subprocess.run", runner):
            with self.assertRaises(RuntimeError) as ctx:
                build_pack._check_on_main_branch(Path("/tmp"))
        self.assertIn("feature-branch", str(ctx.exception))
        self.assertIn("main", str(ctx.exception))

    def test_main_branch_passes(self):
        runner = self._mock_run([(0, "main\n", "")])
        with patch("build_pack.subprocess.run", runner):
            build_pack._check_on_main_branch(Path("/tmp"))

    def test_local_tag_exists_refuses(self):
        """rev-parse rc=0 means the tag exists locally."""
        runner = self._mock_run([(0, "abc123\n", "")])
        with patch("build_pack.subprocess.run", runner):
            with self.assertRaises(RuntimeError) as ctx:
                build_pack._check_tag_does_not_exist(Path("/tmp"), "v1.4.0")
        self.assertIn("local tag", str(ctx.exception))

    def test_remote_tag_exists_refuses(self):
        runner = self._mock_run([
            (1, "", "fatal: not a ref"),               # local: missing
            (0, "abc123\trefs/tags/v1.4.0\n", ""),     # remote: present
        ])
        with patch("build_pack.subprocess.run", runner):
            with self.assertRaises(RuntimeError) as ctx:
                build_pack._check_tag_does_not_exist(Path("/tmp"), "v1.4.0")
        self.assertIn("remote tag", str(ctx.exception))

    def test_tag_absent_locally_and_remotely_passes(self):
        runner = self._mock_run([
            (1, "", "fatal: not a ref"),  # local: missing
            (0, "", ""),                  # remote: empty stdout
        ])
        with patch("build_pack.subprocess.run", runner):
            build_pack._check_tag_does_not_exist(Path("/tmp"), "v1.4.0")

    def test_gh_unauthenticated_refuses(self):
        runner = self._mock_run([(1, "", "not logged in")])
        with patch("build_pack.subprocess.run", runner):
            with self.assertRaises(RuntimeError) as ctx:
                build_pack._check_gh_authenticated()
        self.assertIn("gh auth", str(ctx.exception).lower())

    def test_gh_authenticated_passes(self):
        runner = self._mock_run([(0, "Logged in", "")])
        with patch("build_pack.subprocess.run", runner):
            build_pack._check_gh_authenticated()


class TagMessageDerivationTests(unittest.TestCase):
    """Tests for _derive_tag_message()."""

    def _mock_run(self, rc, stdout):
        class _CP:
            def __init__(self, r, o):
                self.returncode = r
                self.stdout = o
                self.stderr = ""
        def _runner(*args, **kwargs):
            return _CP(rc, stdout)
        return _runner

    def test_close_wave_subject_used_verbatim(self):
        runner = self._mock_run(0, "Close wave 1p337 and ship 1.3.32 → 1.4.0\n")
        with patch("build_pack.subprocess.run", runner):
            msg = build_pack._derive_tag_message(Path("/tmp"), "1.4.0")
        self.assertEqual(msg, "Close wave 1p337 and ship 1.3.32 → 1.4.0")

    def test_ascii_arrow_close_wave_subject_recognized(self):
        runner = self._mock_run(0, "Close wave 1p347 and ship 1.4.0 -> 1.4.1\n")
        with patch("build_pack.subprocess.run", runner):
            msg = build_pack._derive_tag_message(Path("/tmp"), "1.4.1")
        self.assertEqual(msg, "Close wave 1p347 and ship 1.4.0 -> 1.4.1")

    def test_non_close_subject_falls_back_to_default(self):
        runner = self._mock_run(0, "chore: tweak gitignore\n")
        with patch("build_pack.subprocess.run", runner):
            msg = build_pack._derive_tag_message(Path("/tmp"), "1.4.1")
        self.assertEqual(msg, "Release v1.4.1")

    def test_git_failure_falls_back_to_default(self):
        runner = self._mock_run(1, "")
        with patch("build_pack.subprocess.run", runner):
            msg = build_pack._derive_tag_message(Path("/tmp"), "1.4.1")
        self.assertEqual(msg, "Release v1.4.1")


# ---------------------------------------------------------------------------
# Release orchestration ordering (wave 1p5l4): the build stamp must be committed
# BEFORE tagging, so the tag lands on the stamp commit (matching the v1.4/v1.5
# convention), and main must be pushed so origin reflects the tagged commit.
# ---------------------------------------------------------------------------


class ReleaseOrchestrationOrderingTests(unittest.TestCase):
    """`_run_release_orchestration` commits the stamp, then tags, then pushes main + tag."""

    def _repo_with_version(self, stamp="1.6.0+ptest"):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        vfile = root / build_pack.FRAMEWORK_REL / "VERSION"
        vfile.parent.mkdir(parents=True, exist_ok=True)
        vfile.write_text(stamp + "\n", encoding="utf-8")
        return root

    class _Recorder:
        """Records argv of each subprocess.run and returns success for all."""
        def __init__(self):
            self.calls = []

        def __call__(self, argv, **kwargs):
            self.calls.append(list(argv))

            class _CP:
                def __init__(self, rc, out="", err=""):
                    self.returncode = rc
                    self.stdout = out
                    self.stderr = err

            # `git diff --cached --quiet` → rc=1 means there ARE staged changes
            # (the stamp), so the commit step proceeds.
            if argv[:3] == ["git", "diff", "--cached"]:
                return _CP(1)
            # `git log -1 --format=%s` (tag-message derivation): non-close subject.
            if argv[:2] == ["git", "log"]:
                return _CP(0, "Close wave 1p5dk and ship 1.5.1 -> 1.6.0\n")
            return _CP(0, "ok")

    def _verbs(self, calls):
        """Reduce recorded argv lists to comparable verb tuples."""
        verbs = []
        for c in calls:
            if c[:2] == ["git", "commit"]:
                verbs.append("commit")
            elif c[:2] == ["git", "tag"]:
                verbs.append("tag")
            elif c[:1] == ["git"] and "push" in c and "HEAD:main" in c:
                verbs.append("push-main")
            elif c[:1] == ["git"] and "push" in c and any(x == "v1.6.0" for x in c):
                verbs.append("push-tag")
            elif c[:2] == ["gh", "release"]:
                verbs.append("gh-release")
        return verbs

    def test_commit_precedes_tag_and_main_is_pushed(self):
        root = self._repo_with_version()
        rec = self._Recorder()
        with patch("build_pack.subprocess.run", rec):
            build_pack._run_release_orchestration(
                root, "1.6.0", Path("/tmp/wavefoundry-1.6.0.ptest.zip"),
                "notes", dry_run=False,
            )
        verbs = self._verbs(rec.calls)
        # The exact release-action sequence.
        self.assertEqual(verbs, ["commit", "tag", "push-main", "push-tag", "gh-release"])
        # And specifically: the stamp commit lands before the tag.
        self.assertLess(verbs.index("commit"), verbs.index("tag"))

    def test_commit_message_carries_the_version_stamp(self):
        root = self._repo_with_version("1.6.0+ptest")
        rec = self._Recorder()
        with patch("build_pack.subprocess.run", rec):
            build_pack._run_release_orchestration(
                root, "1.6.0", Path("/tmp/x.zip"), "notes", dry_run=False,
            )
        commit_call = next(c for c in rec.calls if c[:2] == ["git", "commit"])
        self.assertIn("Bump VERSION to 1.6.0+ptest after release", commit_call)

    def test_dry_run_takes_no_side_effects_and_shows_commit_before_tag(self):
        import io, contextlib
        root = self._repo_with_version()
        rec = self._Recorder()
        buf = io.StringIO()
        with patch("build_pack.subprocess.run", rec), contextlib.redirect_stderr(buf):
            build_pack._run_release_orchestration(
                root, "1.6.0", Path("/tmp/x.zip"), "notes", dry_run=True,
            )
        # No git/gh side-effects beyond the tag-message git-log lookup.
        side_effects = [c for c in rec.calls if c[:2] in (["git", "commit"], ["git", "tag"], ["gh", "release"])]
        self.assertEqual(side_effects, [], "dry-run must not commit/tag/release")
        out = buf.getvalue()
        self.assertLess(out.index("git commit"), out.index(f"git tag -a v1.6.0"))
        self.assertIn("git push origin HEAD:main", out)


# ---------------------------------------------------------------------------
# Install-log / install-entry-doc templates (wave 1p35d / change 1p35f)
# ---------------------------------------------------------------------------


class InstallTemplateInjectionTests(unittest.TestCase):
    """Tests for `install-wavefoundry.md` and `wavefoundry-install-log.md` at zip root."""

    def setUp(self):
        import tempfile
        self._tmp = tempfile.mkdtemp()
        self.tmp = Path(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _build(self, version="1.0.0", build_prefix="2tm5"):
        return build_pack.build_zip(
            self.tmp, version, build_prefix,
            write_version=False, update_manifest=False,
        )

    def _zip_names(self, zip_path):
        with zipfile.ZipFile(zip_path) as zf:
            return zf.namelist()

    def _zip_read(self, zip_path, arcname):
        with zipfile.ZipFile(zip_path) as zf:
            return zf.read(arcname).decode("utf-8")

    def test_install_wavefoundry_md_at_zip_root(self):
        """AC-7: install-wavefoundry.md ships at the zip root, not under .wavefoundry/."""
        zp = self._build()
        names = self._zip_names(zp)
        self.assertIn("install-wavefoundry.md", names)
        self.assertNotIn(".wavefoundry/install-wavefoundry.md", names)

    def test_install_log_template_ships_in_framework_tree(self):
        """AC-6: install-log.template.md ships inside the framework tree (not at zip root).

        The agent copies it to .wavefoundry/install-log.md on first install;
        the live log is never in the zip (preserved across upgrades).
        """
        zp = self._build()
        names = self._zip_names(zp)
        self.assertIn(".wavefoundry/framework/install/install-log.template.md", names)
        # Live log MUST NOT be in the zip — that's the operator-preserved instance.
        self.assertNotIn("install-log.md", names)
        self.assertNotIn(".wavefoundry/install-log.md", names)

    def test_install_md_no_longer_present(self):
        """AC-8: INSTALL.md is removed; not aliased."""
        zp = self._build()
        names = self._zip_names(zp)
        self.assertNotIn("INSTALL.md", names)

    def test_install_wavefoundry_md_has_version_substituted(self):
        """AC-7: {{version}} placeholder is substituted with the build version."""
        zp = self._build(version="1.5.0")
        body = self._zip_read(zp, "install-wavefoundry.md")
        self.assertIn("1.5.0", body)
        self.assertNotIn("{{version}}", body)

    def test_install_log_template_preserves_generated_at_placeholder(self):
        """The {{generated_at}} placeholder is NOT substituted at packaging time.

        Substitution happens when the agent copies the template to
        .wavefoundry/install-log.md on first install; build_pack ships
        the template verbatim.
        """
        zp = self._build()
        body = self._zip_read(zp, ".wavefoundry/framework/install/install-log.template.md")
        self.assertIn("{{generated_at}}", body)

    def test_install_log_template_contains_phase_1_and_phase_2(self):
        """AC-4 + AC-5: template has both phase headings and the boundary marker."""
        zp = self._build()
        body = self._zip_read(zp, ".wavefoundry/framework/install/install-log.template.md")
        self.assertIn("Phase 1", body)
        self.assertIn("Phase 2", body)
        # Restart marker between phases (Phase 1 last row mentions restart agent).
        self.assertIn("restart", body.lower())

    def test_install_log_template_phase_2_starts_with_wave_install_audit(self):
        """AC-5: first Phase 2 row is a wave_install_audit call."""
        zp = self._build()
        body = self._zip_read(zp, ".wavefoundry/framework/install/install-log.template.md")
        phase_2_section = body.split("Phase 2", 1)[1]  # everything after the heading
        head = phase_2_section[:1200]
        self.assertIn("wave_install_audit", head)

    def test_install_wavefoundry_md_explains_template_to_log_copy(self):
        """The entry doc instructs the agent to copy template -> .wavefoundry/install-log.md."""
        zp = self._build()
        body = self._zip_read(zp, "install-wavefoundry.md")
        self.assertIn(".wavefoundry/install-log.md", body)
        self.assertIn("install-log.template.md", body)


class ReadmeVersionBadgeStampTests(unittest.TestCase):
    """Wave 1p5s1: _stamp_readme_version_badge rewrites the static version badge."""

    def _repo(self, readme_text):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "README.md").write_text(readme_text, encoding="utf-8")
        return root

    _BADGE = "[![Version](https://img.shields.io/badge/version-1.0.0-purple)](url)\n"
    _OTHER = (
        "[![MCP](https://img.shields.io/badge/MCP-local_server-0a7ea4)](m)\n"
        "[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](L)\n"
    )

    def test_rewrites_version(self):
        root = self._repo(self._BADGE + self._OTHER)
        self.assertTrue(build_pack._stamp_readme_version_badge(root, "1.6.3"))
        text = (root / "README.md").read_text()
        self.assertIn("badge/version-1.6.3-purple", text)
        self.assertNotIn("version-1.0.0-purple", text)
        # other badges untouched
        self.assertIn("badge/MCP-local_server-0a7ea4", text)
        self.assertIn("badge/License-Apache_2.0-blue.svg", text)

    def test_idempotent(self):
        root = self._repo(self._BADGE)
        build_pack._stamp_readme_version_badge(root, "1.6.3")
        # second call: already at 1.6.3 → no change
        self.assertFalse(build_pack._stamp_readme_version_badge(root, "1.6.3"))

    def test_noop_when_no_badge(self):
        root = self._repo("# Project\n\nNo version badge here.\n")
        self.assertFalse(build_pack._stamp_readme_version_badge(root, "1.6.3"))

    def test_noop_when_readme_absent(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.assertFalse(build_pack._stamp_readme_version_badge(Path(tmp), "1.6.3"))


if __name__ == "__main__":
    unittest.main()

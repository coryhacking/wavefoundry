"""Tests for check_version.py — semver comparison and _to_version helper."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import check_version


class ToVersionTests(unittest.TestCase):
    """Tests for _to_version()."""

    def test_semver_string_parsed_correctly(self):
        v = check_version._to_version("1.0.0")
        self.assertEqual(v, (1, 0, 0))

    def test_semver_with_build_metadata_stripped(self):
        v = check_version._to_version("1.0.0+12tm5")
        # Build metadata stripped — same precedence as 1.0.0.
        self.assertEqual(v, (1, 0, 0))

    def test_date_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_version._to_version("2026-05-20i")

    def test_unknown_format_raises_value_error(self):
        with self.assertRaises((ValueError, Exception)):
            check_version._to_version("not-a-version")

    def test_plain_zero_string_is_valid_semver(self):
        v = check_version._to_version("0.0.0")
        self.assertEqual(v, (0, 0, 0))

    def test_multi_digit_minor_parsed(self):
        v = check_version._to_version("1.10.0")
        self.assertEqual(v, (1, 10, 0))


class ReadInstalledRevisionTests(unittest.TestCase):
    """Wave 1p44p — installed-revision resolver: prompt-surface-manifest.json →
    framework/VERSION fallback; never json.loads the (path-list) MANIFEST."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def test_reads_framework_revision_from_manifest(self):  # AC-1 / AC-2 / AC-9a
        self._write("docs/prompts/prompt-surface-manifest.json",
                    json.dumps({"framework_revision": "1.6.0+abc"}))
        self.assertEqual(check_version._read_installed_revision(self.root), "1.6.0+abc")

    def test_falls_back_to_version_file(self):  # AC-3 / AC-9b
        self._write(".wavefoundry/framework/VERSION", "1.5.0+def\n")
        self.assertEqual(check_version._read_installed_revision(self.root), "1.5.0+def")

    def test_manifest_wins_over_version(self):
        self._write("docs/prompts/prompt-surface-manifest.json",
                    json.dumps({"framework_revision": "1.6.0+abc"}))
        self._write(".wavefoundry/framework/VERSION", "1.5.0+def\n")
        self.assertEqual(check_version._read_installed_revision(self.root), "1.6.0+abc")

    def test_both_absent_returns_none(self):  # AC-3
        self.assertIsNone(check_version._read_installed_revision(self.root))

    def test_path_list_manifest_not_parsed_as_json(self):  # AC-1 regression
        # A legacy newline-delimited MANIFEST must NOT be read as JSON (the old bug).
        self._write(".wavefoundry/framework/MANIFEST", "path/one\npath/two\n")
        self._write(".wavefoundry/framework/VERSION", "1.5.0\n")
        self.assertEqual(check_version._read_installed_revision(self.root), "1.5.0")

    def test_downgrade_guard_now_classifies_downgrade(self):  # AC-4
        # Resolver returns a real revision (not the old always-None), so the
        # upgrade guard's `if from_version` precondition holds and the comparison
        # classifies a genuine downgrade.
        self._write("docs/prompts/prompt-surface-manifest.json",
                    json.dumps({"framework_revision": "1.6.0"}))
        installed = check_version._read_installed_revision(self.root)
        self.assertEqual(installed, "1.6.0")
        self.assertEqual(check_version.compare_versions("1.5.0", installed), "downgrade")


class CompareVersionsTests(unittest.TestCase):
    """Tests for compare_versions()."""

    def test_semver_upgrade(self):
        self.assertEqual(check_version.compare_versions("1.2.0", "1.0.0"), "upgrade")

    def test_semver_downgrade(self):
        self.assertEqual(check_version.compare_versions("1.0.0", "1.2.0"), "downgrade")

    def test_semver_same(self):
        self.assertEqual(check_version.compare_versions("1.0.0", "1.0.0"), "same")

    def test_multi_digit_minor_correct_ordering(self):
        """1.10.0 > 1.9.0 — must not use lexicographic comparison."""
        self.assertEqual(check_version.compare_versions("1.10.0", "1.9.0"), "upgrade")
        self.assertEqual(check_version.compare_versions("1.9.0", "1.10.0"), "downgrade")

    def test_date_string_in_compare_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_version.compare_versions("1.0.0", "2026-05-20i")

    def test_semver_with_build_metadata_same_precedence(self):
        """Build metadata does not affect version precedence."""
        self.assertEqual(check_version.compare_versions("1.0.0+12tm5", "1.0.0+12abc"), "same")
        self.assertEqual(check_version.compare_versions("1.0.0+12tm5", "1.0.0"), "same")


if __name__ == "__main__":
    unittest.main()

"""Tests for check_version.py — semver comparison and _to_version helper."""
from __future__ import annotations

import importlib.util
import sys
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

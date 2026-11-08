#!/usr/bin/env python3
"""A suggested allowlist entry excludes exactly its own path (wave 22u26, change 22qr7).

The entry ends in RE2's ``\\z`` (end of text). ``$`` also matches before a trailing newline in
Python ``re``. Python 3.14 reads ``\\z`` natively; older interpreters reject it, so the Python path
matcher retries an uncompilable pattern through the RE2 translation rule patterns already use.
"""
from __future__ import annotations

import re
import sys
import tomllib
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import scanner_skips
from wave_lint_lib import expr_filter


def _scanner():
    # Another module in the same process may reload the scanner package; use the live one.
    from wave_lint_lib import secrets_validators
    return sys.modules[secrets_validators.__name__]


def _pattern(rel: str) -> str:
    return tomllib.loads("paths = [" + scanner_skips.allowlist_entry(rel) + "]\n")["paths"][0]


def _pre_314_re():
    """``re`` as Python 3.11 to 3.13 behave on ``\\z``: a bad escape."""
    def compile(pattern, flags=0):
        if re.search(r"(?<!\\)(?:\\\\)*\\z", pattern):
            raise re.error("bad escape \\z")
        return re.compile(pattern, flags)

    def search(pattern, string, flags=0):
        return compile(pattern, flags).search(string)
    return types.SimpleNamespace(compile=compile, error=re.error, search=search)


PATHS = ("x", "data dir/many-matches.txt", "a+b/[c].py")


class AllowlistEntryAnchorTests(unittest.TestCase):
    def test_the_entry_ends_in_the_re2_end_of_text_anchor(self):
        for rel in PATHS:
            with self.subTest(rel=rel):
                pattern = _pattern(rel)
                self.assertEqual(pattern, "^" + re.escape(rel) + "\\z")
        self.assertEqual(scanner_skips.allowlist_entry("x"), "'^x\\z'")

    def _assert_exact(self, matches):
        for rel in PATHS:
            with self.subTest(rel=rel):
                pattern = _pattern(rel)
                self.assertTrue(matches(rel, pattern))
                for other in (rel + "\n", rel + "x", "a" + rel, rel[:-1]):
                    self.assertFalse(matches(other, pattern), repr(other))

    def test_the_python_matcher_is_exact(self):
        scanner = _scanner()
        self._assert_exact(lambda rel, pattern: scanner._path_matches_allowlist(rel, [pattern]))

    def test_the_python_matcher_is_exact_through_the_re2_fallback(self):
        # Forces the re.error path an interpreter before 3.14 takes, on any interpreter.
        scanner = _scanner()
        with patch.object(scanner, "re", _pre_314_re()):
            with self.assertRaises(re.error):
                scanner.re.compile("^x\\z")
            with self.assertRaises(re.error):
                scanner.re.search("^x\\z", "x")
            self._assert_exact(lambda rel, pattern: scanner._path_matches_allowlist(rel, [pattern]))

    def test_the_upstream_matcher_is_exact(self):
        self._assert_exact(lambda rel, pattern: bool(expr_filter.compile_regex(pattern).search(rel)))

    def test_an_existing_dollar_entry_keeps_its_behaviour(self):
        # Not rewritten: a hand-written `$` entry still matches before a trailing newline in Python.
        scanner = _scanner()
        self.assertTrue(scanner._path_matches_allowlist("x", ["^x$"]))
        self.assertTrue(scanner._path_matches_allowlist("x\n", ["^x$"]))

    def test_an_uncompilable_pattern_is_still_skipped(self):
        scanner = _scanner()
        self.assertFalse(scanner._path_matches_allowlist("x", ["(unclosed", "^y\\z"]))
        self.assertTrue(scanner._path_matches_allowlist("y", ["(unclosed", "^y\\z"]))


if __name__ == "__main__":
    unittest.main()

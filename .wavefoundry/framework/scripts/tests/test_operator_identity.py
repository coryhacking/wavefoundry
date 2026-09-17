"""Resolver contract tests with real temporary configuration and bounded failures."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import operator_identity as subject


class OperatorIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.map_path = self.root / "docs" / "contributors.json"
        self.map_path.parent.mkdir()
        self.write_map({"alice": {"name": "Alice Example", "emails": ["alice@example.test"]}})

    def write_map(self, entries):
        self.map_path.write_text(json.dumps(entries), encoding="utf-8")

    def git_result(self, stdout="alice@example.test\n", returncode=0):
        return subprocess.CompletedProcess([], returncode, stdout, "")

    def test_missing_map_is_silent_and_never_calls_git(self):
        self.map_path.unlink()
        with patch.object(subject.subprocess, "run") as run:
            self.assertEqual(subject.resolve_operator(self.root), (None, "no_contributors_file"))
        run.assert_not_called()

    def test_explicit_handle_wins_and_unknown_or_blank_never_falls_back(self):
        with patch.object(subject.subprocess, "run") as run:
            self.assertEqual(subject.resolve_operator(self.root, "alice"), ({"handle": "alice", "source": "explicit"}, ""))
            for handle in ("bob", "", " "):
                operator, reason = subject.resolve_operator(self.root, handle)
                self.assertIsNone(operator)
                self.assertIn("explicit", reason)
        run.assert_not_called()

    def test_invalid_map_shapes_never_reach_git(self):
        entry = {"name": "Alice", "emails": ["alice@example.test"]}
        malformed = [[], None, {"": entry}, {" ": entry}, {"alice": None},
                     {"alice": {}}, {"alice": {**entry, "name": " "}},
                     {"alice": {**entry, "name": 7}},
                     {"alice": {**entry, "emails": "alice@example.test"}},
                     {"alice": {**entry, "emails": []}},
                     {"alice": {**entry, "emails": [None]}},
                     {"alice": {**entry, "emails": [" "]}}]
        with patch.object(subject.subprocess, "run") as run:
            for entries in malformed:
                with self.subTest(entries=entries):
                    self.write_map(entries)
                    operator, reason = subject.resolve_operator(self.root, "alice")
                    self.assertIsNone(operator)
                    self.assertIn("invalid shape", reason)
        run.assert_not_called()

    def test_read_and_decode_failures_are_distinct_from_absence(self):
        for raw in (b"{", b"\xff"):
            with self.subTest(raw=raw):
                self.map_path.write_bytes(raw)
                operator, reason = subject.resolve_operator(self.root)
                self.assertIsNone(operator)
                self.assertNotEqual(reason, "no_contributors_file")
        with patch.object(Path, "read_text", side_effect=PermissionError("private detail")):
            self.assertEqual(subject.resolve_operator(self.root), (None, "contributors file could not be read"))

    def test_git_failures_and_unset_email_return_reason_without_private_output(self):
        failures = [FileNotFoundError("private detail"), subprocess.TimeoutExpired("git", 10),
                    UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")]
        for error in failures:
            with self.subTest(error=error), patch.object(subject.subprocess, "run", side_effect=error):
                self.assertEqual(subject.resolve_operator(self.root), (None, "git user.email lookup failed"))
        for result in (self.git_result(returncode=128), self.git_result(returncode=1), self.git_result(" \n")):
            with self.subTest(result=result), patch.object(subject.subprocess, "run", return_value=result):
                operator, reason = subject.resolve_operator(self.root)
                self.assertIsNone(operator)
                self.assertTrue(reason)

    def test_normalized_duplicate_email_is_one_handle_but_two_handles_are_ambiguous(self):
        entry = {"name": "Alice", "emails": [" alice@EXAMPLE.test ", "ALICE@example.test"]}
        self.write_map({"alice": entry})
        with patch.object(subject.subprocess, "run", return_value=self.git_result(" Alice@Example.Test \n")):
            self.assertEqual(subject.resolve_operator(self.root), ({"handle": "alice", "source": "git_email"}, ""))
            self.write_map({"alice": entry, "bob": entry})
            operator, reason = subject.resolve_operator(self.root)
            self.assertIsNone(operator)
            self.assertIn("multiple", reason)

    def test_unmapped_email_and_empty_map_are_unresolved(self):
        with patch.object(subject.subprocess, "run", return_value=self.git_result("unknown@example.test")):
            for entries in ({"alice": {"name": "Alice", "emails": ["alice@example.test"]}}, {}):
                self.write_map(entries)
                operator, reason = subject.resolve_operator(self.root)
                self.assertIsNone(operator)
                self.assertIn("not in", reason)

    def test_git_call_is_bounded_read_only_and_sanitizes_target_overrides(self):
        with patch.dict(os.environ, {"GIT_DIR": "/decoy", "GIT_WORK_TREE": "/decoy", "GIT_CONFIG_COUNT": "1"}), patch.object(subject.subprocess, "run", return_value=self.git_result()) as run:
            subject.resolve_operator(self.root)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["git", "-C", str(self.root), "config", "user.email"])
        self.assertEqual(run.call_args.kwargs["timeout"], 10)
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["creationflags"], getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_CONFIG_COUNT"):
            self.assertNotIn(key, run.call_args.kwargs["env"])

    def test_real_git_uses_target_config_and_does_not_cache(self):
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_CONFIG", "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS"):
            env.pop(key, None)
        with patch.dict(os.environ, env, clear=True):
            subprocess.run(["git", "-C", str(self.root), "init", "-q"], check=True, capture_output=True, timeout=10)
            subprocess.run(["git", "-C", str(self.root), "config", "user.email", " ALICE@example.test "], check=True, capture_output=True, timeout=10)
            with patch.dict(os.environ, {"GIT_DIR": str(self.root / "missing"), "GIT_WORK_TREE": str(self.root / "missing")}):
                self.assertEqual(subject.resolve_operator(self.root), ({"handle": "alice", "source": "git_email"}, ""))
            self.write_map({"changed": {"name": "Changed", "emails": ["alice@example.test"]}})
            self.assertEqual(subject.resolve_operator(self.root), ({"handle": "changed", "source": "git_email"}, ""))
            subprocess.run(["git", "-C", str(self.root), "config", "--unset", "user.email"], check=True, capture_output=True, timeout=10)
            self.assertEqual(subject.resolve_operator(self.root), (None, "git user.email is unset"))


if __name__ == "__main__":
    unittest.main()

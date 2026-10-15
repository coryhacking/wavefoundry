"""Resolver contract tests with real temporary configuration and bounded failures."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import operator_identity as subject


# Wave 1z8ox (change 1z8ow): the timed sites these tests fake now call
# run_with_tree_kill; route it back through isolated_run so the existing fakes
# still intercept (each test asserts its fake was called).
_TREE_KILL_SHIM = None


def setUpModule():
    global _TREE_KILL_SHIM
    tests_dir = str(Path(__file__).resolve().parent)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    from tree_kill_support import ModuleShim

    _TREE_KILL_SHIM = ModuleShim()
    _TREE_KILL_SHIM.start()


def tearDownModule():
    if _TREE_KILL_SHIM is not None:
        _TREE_KILL_SHIM.stop()


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

    def test_local_handle_needs_no_hosting_identity_and_does_not_publish_email(self):
        self.write_map({"release-owner": {"name": "Owner", "emails": ["owner@offline.test"]}})
        with patch.object(subject, "_run_tree_kill", return_value=self.git_result("owner@offline.test")) as run:
            identity, reason = subject.resolve_operator(self.root)
        self.assertEqual(reason, "")
        self.assertEqual(identity, {"handle": "release-owner", "source": "git_email"})
        self.assertNotIn("owner@offline.test", json.dumps(identity))
        self.assertEqual(run.call_args.args[0][-2:], ["config", "user.email"])
        with patch.object(subject, "_run_tree_kill", side_effect=AssertionError("offline explicit identity must not invoke Git")):
            self.assertEqual(subject.resolve_operator(self.root, "release-owner"),
                             ({"handle": "release-owner", "source": "explicit"}, ""))

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
            with self.subTest(error=error), patch.object(subject.subprocess, "run", side_effect=error) as run:
                self.assertEqual(subject.resolve_operator(self.root), (None, "git user.email lookup failed"))
                run.assert_called_once()
        for result in (self.git_result(returncode=128), self.git_result(returncode=1), self.git_result(" \n")):
            with self.subTest(result=result), patch.object(subject.subprocess, "run", return_value=result) as run:
                operator, reason = subject.resolve_operator(self.root)
                self.assertIsNone(operator)
                self.assertTrue(reason)
                run.assert_called_once()

    def test_normalized_duplicate_email_is_one_handle_but_two_handles_are_ambiguous(self):
        entry = {"name": "Alice", "emails": [" alice@EXAMPLE.test ", "ALICE@example.test"]}
        self.write_map({"alice": entry})
        with patch.object(subject.subprocess, "run", return_value=self.git_result(" Alice@Example.Test \n")) as run:
            self.assertEqual(subject.resolve_operator(self.root), ({"handle": "alice", "source": "git_email"}, ""))
            self.write_map({"alice": entry, "bob": entry})
            operator, reason = subject.resolve_operator(self.root)
            self.assertIsNone(operator)
            self.assertIn("multiple", reason)
        self.assertEqual(run.call_count, 2)

    def test_unmapped_email_and_empty_map_are_unresolved(self):
        with patch.object(subject.subprocess, "run", return_value=self.git_result("unknown@example.test")) as run:
            for entries in ({"alice": {"name": "Alice", "emails": ["alice@example.test"]}}, {}):
                self.write_map(entries)
                operator, reason = subject.resolve_operator(self.root)
                self.assertIsNone(operator)
                self.assertIn("not in", reason)
        self.assertEqual(run.call_count, 2)

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



class LocalUserIdentityTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "POSIX account API")
    def test_effective_account_ignores_environment_and_real_uid(self):
        import pwd
        with patch.dict(os.environ, {"USER": "decoy", "LOGNAME": "other", "USERNAME": "wrong"}), \
                patch.object(os, "geteuid", return_value=321) as effective, \
                patch.object(os, "getuid", side_effect=AssertionError("real uid")), \
                patch.object(pwd, "getpwuid", return_value=types.SimpleNamespace(pw_name="local-person")) as lookup, \
                patch.object(subject.subprocess, "run", side_effect=AssertionError("shell identity")):
            self.assertEqual(subject.resolve_local_user(),
                             ({"name": "local-person", "source": "local_os_account"}, ""))
        effective.assert_called_once_with()
        lookup.assert_called_once_with(321)

    def test_windows_native_api_has_fixed_buffer_and_no_retry(self):
        import ctypes
        from ctypes import wintypes
        from unittest.mock import Mock

        def native(buffer, size):
            self.assertEqual(len(buffer), 257)
            self.assertEqual(size._obj.value, 257)
            buffer.value = "native-person"
            size._obj.value = len(buffer.value) + 1
            return 1

        api = Mock(side_effect=native)
        with patch.object(ctypes, "WinDLL", create=True, return_value=types.SimpleNamespace(GetUserNameW=api)) as dll, \
                patch.object(os, "name", "nt"), patch.dict(os.environ, {"USERNAME": "decoy"}):
            self.assertEqual(subject.resolve_local_user(),
                             ({"name": "native-person", "source": "local_os_account"}, ""))
        dll.assert_called_once_with("advapi32", use_last_error=True)
        api.assert_called_once()
        self.assertEqual(api.argtypes, [wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)])
        self.assertEqual(api.restype, wintypes.BOOL)
        for result_size, succeeded in ((9999999, 0), (9999999, 1), (0, 1), (1, 1)):
            def failure(buffer, size):
                size._obj.value = result_size
                return succeeded
            api = Mock(side_effect=failure)
            with self.subTest(size=result_size, succeeded=succeeded), \
                    patch.object(ctypes, "WinDLL", create=True, return_value=types.SimpleNamespace(GetUserNameW=api)), \
                    patch.object(os, "name", "nt"):
                self.assertEqual(subject.resolve_local_user(), (None, "local account lookup is unavailable"))
            api.assert_called_once()

    def test_unavailable_and_unsafe_accounts_return_literal_bounded_reasons(self):
        for error in (OSError("private/path"), ValueError("private account"), ImportError("private module")):
            with self.subTest(error=error), patch.object(os, "name", "nt"), \
                    patch.object(subject, "_windows_local_user_name", side_effect=error):
                self.assertEqual(subject.resolve_local_user(), (None, "local account lookup is unavailable"))
        invalid = (None, 7, "", " ", " trailing ", "x" * 257,
                   "a\n", "a\x00b", "a\u202eb", "a\u200bb", "a\ud800", "a\u2028b", "a\u2029b")
        for name in invalid:
            with self.subTest(name=name), patch.object(os, "name", "nt"), \
                    patch.object(subject, "_windows_local_user_name", return_value=name):
                self.assertEqual(subject.resolve_local_user(),
                                 (None, "local account name is unsafe or exceeds the attribution limit"))
        with patch.object(os, "name", "unsupported"):
            self.assertEqual(subject.resolve_local_user(), (None, "local account lookup is unavailable"))

    def test_exact_safe_name_is_preserved_and_bound_is_inclusive(self):
        for name in ("x" * 256, "Jos\u0065\u0301", "a[link](x)|<b>*_&"):
            with self.subTest(name=name), patch.object(os, "name", "nt"), \
                    patch.object(subject, "_windows_local_user_name", return_value=name):
                self.assertEqual(subject.resolve_local_user(),
                                 ({"name": name, "source": "local_os_account"}, ""))

if __name__ == "__main__":
    unittest.main()

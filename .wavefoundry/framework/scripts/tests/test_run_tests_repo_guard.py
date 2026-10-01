"""Wave 1z8ox (1z8ov): the standing repository-state guard in run_tests.py.

Every test here builds its own temporary git repository and points the runner
at it, so nothing touches the live checkout. The mutant cases run a REAL
worker subprocess through ``_run_file``: a scratch test file that writes into
the fixture repository, exactly as an offending suite test would.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import unittest.mock
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location("run_tests_repo_guard_subject", SCRIPTS_DIR / "run_tests.py")
run_tests = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_tests)


def setUpModule() -> None:  # noqa: N802 (unittest name)
    """These tests drive full runs of a stubbed runner, which refuse while
    WAVEFOUNDRY_TEST_PROFILE is set (change 1zima); a profile run sets it for
    the whole copy, so it is unset here for the module and restored after."""
    import os
    from record_layout_support import TEST_PROFILE_ENV

    environ = patch.dict(os.environ)
    environ.start()
    unittest.addModuleCleanup(environ.stop)
    os.environ.pop(TEST_PROFILE_ENV, None)

_MUTANT_TEMPLATE = '''\
import os
import unittest
from pathlib import Path


class Mutant(unittest.TestCase):
    def test_mutates(self):
        action = os.environ["RG_ACTION"]
        target = Path(os.environ["RG_TARGET"])
        if action == "write":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("mutated by a test\\n", encoding="utf-8")
        elif action == "content":
            target.write_bytes(os.environ["RG_CONTENT"].encode("utf-8"))
        elif action == "delete":
            target.unlink()
        elif action == "none":
            pass


if __name__ == "__main__":
    unittest.main()
'''


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True)


class RepoGuardTestBase(unittest.TestCase):
    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("git is not available")
        self._tmp = tempfile.mkdtemp(prefix="rt-repo-guard-")
        self.tmp = Path(self._tmp)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        (self.repo / ".gitignore").write_text(
            "ignored/\n.wavefoundry/guard-overrides.json\n"
            ".wavefoundry/framework/test-cache.json\n.wavefoundry/framework/test-run.lock\n",
            encoding="utf-8",
        )
        (self.repo / "tracked.txt").write_text("original\n", encoding="utf-8")
        (self.repo / ".wavefoundry").mkdir()
        (self.repo / ".wavefoundry" / "guard-overrides.json").write_text("{}\n", encoding="utf-8")
        _git(self.repo, "add", ".gitignore", "tracked.txt")
        # An untracked, non-ignored file that exists before the run.
        (self.repo / "untracked-before.txt").write_text("present\n", encoding="utf-8")
        self.tests_dir = self.tmp / "tests"
        self.tests_dir.mkdir()
        (self.tests_dir / "test_mutant.py").write_text(_MUTANT_TEMPLATE, encoding="utf-8")
        self.cache_file = self.tmp / "test-cache.json"
        self._saved = {
            "_REPO_ROOT": run_tests._REPO_ROOT,
            "_TESTS_DIR": run_tests._TESTS_DIR,
            "_CACHE_FILE": run_tests._CACHE_FILE,
        }
        run_tests._REPO_ROOT = self.repo
        run_tests._TESTS_DIR = self.tests_dir
        run_tests._CACHE_FILE = self.cache_file
        self._patchers = [
            patch.object(run_tests, "_clean_pycache"),
            patch.object(run_tests, "_acquire_run_lock", return_value=(object(), None)),
            patch.object(run_tests, "_release_run_lock"),
            patch.object(run_tests, "_wait_for_index_build", return_value=None),
            patch.object(run_tests, "_probe_index_build_lock", return_value=(False, None)),
            # The nested scripts/.wavefoundry check is covered elsewhere.
            patch.object(run_tests, "stray_artifact_paths", return_value=[]),
        ]
        for p in self._patchers:
            p.start()

    def tearDown(self):
        for p in self._patchers:
            p.stop()
        for name, value in self._saved.items():
            setattr(run_tests, name, value)
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _main(self, argv, action, target, content=None):
        out, err = io.StringIO(), io.StringIO()
        env = {"RG_ACTION": action, "RG_TARGET": str(target)}
        if content is not None:
            env["RG_CONTENT"] = content
        with patch.dict(os.environ, env), \
                patch.object(sys, "argv", ["run_tests.py", *argv]), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            ret = run_tests.main()
        return ret, out.getvalue(), err.getvalue()


class RepoStateSnapshotTests(RepoGuardTestBase):
    def test_snapshot_covers_tracked_untracked_and_the_gate_file(self):
        snap = run_tests.repo_state_snapshot(self.repo)
        self.assertIn("tracked.txt", snap)
        self.assertIn(".gitignore", snap)
        self.assertIn("untracked-before.txt", snap)
        self.assertIn(".wavefoundry/guard-overrides.json", snap)

    def test_snapshot_leaves_out_ignored_paths_and_the_runner_receipt_and_lock(self):
        (self.repo / "ignored").mkdir()
        (self.repo / "ignored" / "log.txt").write_text("x\n", encoding="utf-8")
        framework = self.repo / ".wavefoundry" / "framework"
        framework.mkdir()
        (framework / "test-cache.json").write_text("{}\n", encoding="utf-8")
        (framework / "test-run.lock").write_text("1\n", encoding="utf-8")
        snap = run_tests.repo_state_snapshot(self.repo)
        self.assertNotIn("ignored/log.txt", snap)
        self.assertNotIn(".wavefoundry/framework/test-cache.json", snap)
        self.assertNotIn(".wavefoundry/framework/test-run.lock", snap)

    def test_missing_gate_file_is_recorded_so_its_creation_is_a_change(self):
        (self.repo / ".wavefoundry" / "guard-overrides.json").unlink()
        before = run_tests.repo_state_snapshot(self.repo)
        self.assertIsNone(before[".wavefoundry/guard-overrides.json"])
        (self.repo / ".wavefoundry" / "guard-overrides.json").write_text("{}\n", encoding="utf-8")
        after = run_tests.repo_state_snapshot(self.repo)
        self.assertEqual(
            run_tests._repo_state_changes(before, after),
            [".wavefoundry/guard-overrides.json"],
        )

    def test_non_git_root_returns_none(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        # GIT_CEILING_DIRECTORIES stops discovery climbing into a parent checkout.
        with patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(self.tmp)}):
            self.assertIsNone(run_tests.repo_state_snapshot(plain))


class RepoGuardMutantTests(RepoGuardTestBase):
    """AC-3: a scratch mutant that changes repository state fails the run."""

    def _assert_guard_failed(self, ret, out, err, rel):
        self.assertEqual(ret, 1, out + err)
        self.assertIn("REPOSITORY CHANGED DURING THE TEST RUN", err)
        self.assertIn(rel, err)
        self.assertIn("concurrent edit by an operator or agent", err)
        self.assertIn("edit gate", err)
        self.assertFalse(self.cache_file.exists(), "a failed guard must write no receipt")

    def test_full_run_fails_when_a_test_modifies_a_tracked_file(self):
        ret, out, err = self._main(["--no-cache"], "write", self.repo / "tracked.txt")
        self._assert_guard_failed(ret, out, err, "tracked.txt")

    def test_full_run_fails_when_a_test_creates_a_non_ignored_file(self):
        ret, out, err = self._main(["--no-cache"], "write", self.repo / "docs" / "new.md")
        self._assert_guard_failed(ret, out, err, "docs/new.md")

    def test_full_run_fails_when_a_test_deletes_a_tracked_file(self):
        ret, out, err = self._main(["--no-cache"], "delete", self.repo / "tracked.txt")
        self._assert_guard_failed(ret, out, err, "tracked.txt")

    def test_full_run_fails_when_a_test_changes_the_gate_file(self):
        gate = self.repo / ".wavefoundry" / "guard-overrides.json"
        ret, out, err = self._main(["--no-cache"], "write", gate)
        self._assert_guard_failed(ret, out, err, ".wavefoundry/guard-overrides.json")

    def test_focused_run_fails_the_same_way(self):
        ret, out, err = self._main(["--file", "test_mutant.py"], "write", self.repo / "tracked.txt")
        self._assert_guard_failed(ret, out, err, "tracked.txt")

    def test_schedule_control_bootstrap_fails_and_writes_no_manifest(self):
        manifest = self.tmp / "timings.json"
        ret, out, err = self._main(
            ["--schedule-control", "bootstrap", "--timings-file", str(manifest)],
            "write", self.repo / "tracked.txt",
        )
        self._assert_guard_failed(ret, out, err, "tracked.txt")
        self.assertFalse(manifest.exists())

    def test_ignored_writes_do_not_trip_the_standing_guard(self):
        ret, out, err = self._main(["--no-cache"], "write", self.repo / "ignored" / "runtime.log")
        self.assertEqual(ret, 0, out + err)
        self.assertNotIn("REPOSITORY CHANGED", err)
        data = json.loads(self.cache_file.read_text(encoding="utf-8"))
        self.assertEqual(data["result"], "ok")

    def test_clean_run_passes_and_writes_the_receipt(self):
        ret, out, err = self._main(["--no-cache"], "none", self.repo / "unused")
        self.assertEqual(ret, 0, out + err)
        self.assertTrue(self.cache_file.exists())

    def test_non_git_root_skips_the_guard_with_a_stated_message(self):
        with patch.object(run_tests, "repo_state_snapshot", return_value=None):
            ret, out, err = self._main(["--no-cache"], "write", self.repo / "tracked.txt")
        self.assertEqual(ret, 0, out + err)
        self.assertIn("repository-state guard is skipped", out)


def _projected_record(body: str, stages: dict | None = None, generation: int = 0) -> str:
    """A wave record as the framework's own projection writes it (real producers)."""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import context_efficiency
    import exploration_avoided

    snapshot = context_efficiency.empty_checkpoint("1abcd")
    snapshot["generation"] = generation
    if stages:
        snapshot["stages"] = stages
        snapshot["measurement_status"] = "healthy"
    text = context_efficiency.replace_checkpoint_block(body, snapshot)
    with tempfile.TemporaryDirectory() as scratch:
        return exploration_avoided.replace_checkpoint_block(text, Path(scratch), "1abcd")


_RECORD_BODY = (
    "# Wave 1abcd\n\nStatus: implementing\n\n## Review Status\n\n"
    "<!-- wave:review-status begin -->\n| Lane | State |\n| --- | --- |\n| qa | open |\n"
    "<!-- wave:review-status end -->\n\n## Notes\n\nBody text.\n"
)
_STAGES = {"implement": {"calls": 3, "estimated_tokens_saved": 1200}}


class WaveRecordProjectionTests(RepoGuardTestBase):
    """DEL-F1: the framework's own context-efficiency projection of the open
    wave record during a run is tolerated; any other wave-record edit is not."""

    def setUp(self):
        super().setUp()
        # A live record in the configured layout and vocabulary (the shipped
        # profile, or a profile's); the projection writes only live records.
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        import record_paths
        import vocabulary_profile

        self.record_rel = f"{record_paths.WAVES_ROOT}/1abcd example/{vocabulary_profile.RECORD_FILENAME}"
        self.record = self.repo / self.record_rel
        self.record.parent.mkdir(parents=True)
        self.before_text = _projected_record(_RECORD_BODY)
        self.record.write_bytes(self.before_text.encode("utf-8"))
        _git(self.repo, "add", self.record_rel)

    def _assert_passed(self, ret, out, err):
        self.assertEqual(ret, 0, out + err)
        self.assertNotIn("REPOSITORY CHANGED", err)
        data = json.loads(self.cache_file.read_text(encoding="utf-8"))
        self.assertEqual(data["result"], "ok")

    def _assert_failed_naming_record(self, ret, out, err):
        self.assertEqual(ret, 1, out + err)
        self.assertIn("REPOSITORY CHANGED DURING THE TEST RUN", err)
        self.assertIn(self.record_rel, err)
        self.assertFalse(self.cache_file.exists())

    def test_projection_only_rewrite_passes_and_writes_the_receipt(self):
        after = _projected_record(_RECORD_BODY, _STAGES, generation=7)
        self.assertNotEqual(after, self.before_text)
        ret, out, err = self._main(["--no-cache"], "content", self.record, after)
        self._assert_passed(ret, out, err)

    def test_projection_appending_its_blocks_to_a_record_without_them_passes(self):
        self.record.write_bytes(_RECORD_BODY.encode("utf-8"))
        after = _projected_record(_RECORD_BODY, _STAGES, generation=1)
        ret, out, err = self._main(["--no-cache"], "content", self.record, after)
        self._assert_passed(ret, out, err)

    def test_dropping_the_tolerance_fails_the_projection_only_run(self):
        # Mutant control: without the projection tolerance the same rewrite fails.
        after = _projected_record(_RECORD_BODY, _STAGES, generation=7)
        with patch.object(run_tests, "_projection_only_change", return_value=False):
            ret, out, err = self._main(["--no-cache"], "content", self.record, after)
        self._assert_failed_naming_record(ret, out, err)

    def test_edit_outside_the_projected_regions_fails(self):
        after = self.before_text.replace("Body text.", "Body text, edited.")
        ret, out, err = self._main(["--no-cache"], "content", self.record, after)
        self._assert_failed_naming_record(ret, out, err)

    def test_edit_inside_a_non_projected_region_fails(self):
        after = self.before_text.replace("| qa | open |", "| qa | approved |")
        ret, out, err = self._main(["--no-cache"], "content", self.record, after)
        self._assert_failed_naming_record(ret, out, err)

    def test_projection_plus_a_body_edit_fails(self):
        after = _projected_record(_RECORD_BODY.replace("Body text.", "Changed."), _STAGES, generation=7)
        ret, out, err = self._main(["--no-cache"], "content", self.record, after)
        self._assert_failed_naming_record(ret, out, err)

    def test_projected_markers_match_the_owning_modules(self):
        if str(SCRIPTS_DIR) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_DIR))
        import context_efficiency
        import exploration_avoided

        self.assertEqual(run_tests._PROJECTED_WAVE_REGIONS, (
            ("## Context Efficiency", context_efficiency.CONTEXT_EFFICIENCY_MARKER_BEGIN,
             context_efficiency.CONTEXT_EFFICIENCY_MARKER_END),
            ("## Estimated Exploration Avoided", exploration_avoided.MARKER_BEGIN,
             exploration_avoided.MARKER_END),
        ))
        self.assertEqual(dict(run_tests._LEGACY_PROJECTION_MARKERS),
                         context_efficiency._LEGACY_CONTEXT_EFFICIENCY_MARKERS)
        rendered = context_efficiency.render_checkpoint_block(context_efficiency.empty_checkpoint("x"))
        self.assertTrue(rendered.startswith("## Context Efficiency\n"))

    def test_without_the_layout_modules_no_file_is_a_wave_record(self):
        # No guessed default layout: the projection tolerance is off and the
        # record is compared like any other file (strict).
        from unittest import mock

        for missing in ("record_paths", "vocabulary_profile"):
            with self.subTest(missing=missing), mock.patch.dict(sys.modules, {missing: None}):
                self.assertIsNone(run_tests._wave_record_matcher(self.repo))
                snap = run_tests.repo_state_snapshot(self.repo)
                self.assertEqual(len(snap[self.record_rel]), 2)
        self.assertFalse(run_tests._is_wave_record(self.record_rel, None))

    def test_wave_record_matcher_follows_the_layout_modules(self):
        import record_paths
        import vocabulary_profile

        prefix, name = run_tests._wave_record_matcher(self.repo)
        self.assertEqual(prefix, record_paths.unvalidated_record_roots(self.repo).waves_rel + "/")
        self.assertEqual(name, vocabulary_profile.RECORD_FILENAME)
        snap = run_tests.repo_state_snapshot(self.repo)
        self.assertEqual(len(snap[self.record_rel]), 3)
        self.assertEqual(len(snap["tracked.txt"]), 2)


class GuardOverridesHashTests(RepoGuardTestBase):
    """The edit-gate file is compared by content hash, not size and mtime."""

    def test_same_size_same_mtime_content_change_is_a_change(self):
        gate = self.repo / ".wavefoundry" / "guard-overrides.json"
        gate.write_text('{"a": 1}\n', encoding="utf-8")
        st = gate.stat()
        before = run_tests.repo_state_snapshot(self.repo)
        gate.write_text('{"b": 2}\n', encoding="utf-8")
        os.utime(gate, ns=(st.st_atime_ns, st.st_mtime_ns))
        after = run_tests.repo_state_snapshot(self.repo)
        self.assertEqual(run_tests._repo_state_changes(before, after),
                         [".wavefoundry/guard-overrides.json"])

    def test_rewrite_with_identical_content_is_not_a_change(self):
        gate = self.repo / ".wavefoundry" / "guard-overrides.json"
        before = run_tests.repo_state_snapshot(self.repo)
        gate.write_text("{}\n", encoding="utf-8")
        os.utime(gate, ns=(1, 1))
        after = run_tests.repo_state_snapshot(self.repo)
        self.assertEqual(run_tests._repo_state_changes(before, after), [])


class GitListingTimeoutTests(RepoGuardTestBase):
    """DEL-F2: the guard's git listing is timed and ends its process tree."""

    def test_listing_goes_through_the_resolver_with_a_timeout_and_no_stdin(self):
        real = run_tests._run_tree_kill
        calls = []

        def spy(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return real(cmd, **kwargs)

        with patch.object(run_tests, "_run_tree_kill", side_effect=spy):
            self.assertIsNotNone(run_tests.repo_state_snapshot(self.repo))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0][:2], ["git", "ls-files"])
        self.assertEqual(calls[0][1]["timeout"], 60)
        self.assertIs(calls[0][1]["stdin"], subprocess.DEVNULL)

    def test_resolver_falls_back_without_the_helper(self):
        done = subprocess.CompletedProcess(["x"], 0)
        import types

        old = types.SimpleNamespace(isolated_run=unittest.mock.Mock(return_value=done))
        with patch.object(run_tests, "subprocess_util", old):
            self.assertIs(run_tests._run_tree_kill(["x"], timeout=3), done)
        old.isolated_run.assert_called_once_with(["x"], timeout=3)

    def test_without_any_runner_the_guard_is_skipped_with_a_stated_message(self):
        import types

        with patch.object(run_tests, "subprocess_util", types.SimpleNamespace()):
            self.assertIsNone(run_tests.repo_state_snapshot(self.repo))
        self.assertIn("no process runner", run_tests._repo_state_unavailable_reason)

    def test_before_snapshot_timeout_skips_the_guard_with_a_stated_message(self):
        timeout = subprocess.TimeoutExpired(["git"], 60)
        with patch.object(run_tests, "_run_tree_kill", side_effect=timeout):
            ret, out, err = self._main(["--no-cache"], "write", self.repo / "tracked.txt")
        self.assertEqual(ret, 0, out + err)
        self.assertIn("did not finish within 60s", out)
        self.assertIn("repository-state guard is skipped", out)

    def test_after_snapshot_timeout_fails_the_run_with_a_stated_reason(self):
        before = run_tests.repo_state_snapshot(self.repo)
        with patch.object(run_tests, "_run_tree_kill", side_effect=subprocess.TimeoutExpired(["git"], 60)):
            message = run_tests._stray_artifact_failure([], before, self.repo)
        self.assertIsNotNone(message)
        self.assertIn("REPOSITORY STATE NOT VERIFIED", message)
        self.assertIn("did not finish within 60s", message)


class RunFileBytecodeEnvTests(unittest.TestCase):
    def test_worker_env_sets_pythondontwritebytecode(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["env"] = kwargs["env"]
            return subprocess.CompletedProcess(cmd, 0, "", "Ran 1 test in 0.001s\n\nOK\n")

        with patch.object(run_tests.subprocess, "run", side_effect=fake_run), \
                patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
            run_tests._run_file(Path("test_x.py"))
        self.assertEqual(captured["env"].get("PYTHONDONTWRITEBYTECODE"), "1")


if __name__ == "__main__":
    unittest.main()

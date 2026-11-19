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
import threading
import time
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
import time
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
        elif action == "wait":
            Path(os.environ["RG_READY"]).touch()
            deadline = time.monotonic() + 15
            while not Path(os.environ["RG_RELEASE"]).exists():
                if time.monotonic() > deadline: raise RuntimeError("publisher did not release worker")
                time.sleep(0.01)
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
            "ignored/\n.wavefoundry/locks/\n.wavefoundry/guard-overrides.json\n"
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
            "_FRAMEWORK_DIR": run_tests._FRAMEWORK_DIR,
            "_TESTS_DIR": run_tests._TESTS_DIR,
            "_CACHE_FILE": run_tests._CACHE_FILE,
        }
        run_tests._REPO_ROOT = self.repo
        run_tests._FRAMEWORK_DIR = self.repo / ".wavefoundry/framework"
        run_tests._FRAMEWORK_DIR.mkdir()
        (run_tests._FRAMEWORK_DIR / "source.py").write_text("old = 1\n")
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


    def _external_main(self, argv, publication):
        ready, release = self.tmp / "ready", self.tmp / "release"
        ready.unlink(missing_ok=True)
        release.unlink(missing_ok=True)
        failures = []
        def publish():
            try:
                deadline = time.monotonic() + 15
                while not ready.exists():
                    if time.monotonic() > deadline:
                        raise RuntimeError("worker did not reach publication barrier")
                    time.sleep(0.01)
                publication()
            except BaseException as exc:
                failures.append(exc)
            finally:
                release.touch()
        thread = threading.Thread(target=publish)
        with patch.dict(os.environ, RG_READY=str(ready), RG_RELEASE=str(release)):
            thread.start()
            result = self._main(argv, "wait", self.repo / "unused")
            thread.join(20)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures, [], repr(failures))
        return result


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
        framework.mkdir(exist_ok=True)
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


class WaveWorkObservationTests(RepoGuardTestBase):
    def test_scratch_writes_do_not_change_source_observation_or_input_hash(self):
        work = self.repo / ".wavefoundry/work/21luh/tests/probe.py"
        work.parent.mkdir(parents=True)
        work.write_text("before = 1\n", encoding="utf-8")
        # Even a mistakenly tracked scratch file remains runtime state. Do not
        # untrack it automatically; genuine source paths must still be observed.
        _git(self.repo, "add", str(work.relative_to(self.repo)))
        before = run_tests.repo_state_snapshot(self.repo)
        digest = run_tests._hash_inputs()
        work.write_text("after = 200\n", encoding="utf-8")
        after = run_tests.repo_state_snapshot(self.repo)
        self.assertNotIn(work.relative_to(self.repo).as_posix(), after)
        self.assertEqual(run_tests._repo_state_changes(before, after), [])
        self.assertEqual(run_tests._hash_inputs(), digest)
        source = run_tests._FRAMEWORK_DIR / "source.py"
        source.write_text("new = 222\n", encoding="utf-8")
        changed = run_tests.repo_state_snapshot(self.repo)
        self.assertIn(".wavefoundry/framework/source.py",
                      run_tests._repo_state_changes(after, changed))
        self.assertNotEqual(run_tests._hash_inputs(), digest)


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
        # Change 23nqu: re-based outside docs/, where a created file still
        # refuses the run (the in-worker guard now refuses a write under docs/).
        ret, out, err = self._main(["--no-cache"], "write", self.repo / "src" / "new.py")
        self._assert_guard_failed(ret, out, err, "src/new.py")

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

    def _main(self, argv, action, target, content=None):
        if action == "content":
            return self._external_main(argv, lambda: target.write_text(content, encoding="utf-8"))
        return super()._main(argv, action, target, content)

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


class CanonicalBookkeepingTests(RepoGuardTestBase):
    """Run the real worker while a separate coordinator publishes canonical state."""

    def setUp(self):
        super().setUp()
        import review_evidence
        import record_paths
        import vocabulary_profile
        self.evidence = review_evidence
        self.wave = self.repo / record_paths.WAVES_ROOT / '1abcd example' / vocabulary_profile.RECORD_FILENAME
        self.wave.parent.mkdir(parents=True)
        self.ledger = self.wave.with_name('events.jsonl')
        self.ledger.write_bytes(b'')
        self.wave.write_text(self._render(
            '# Wave 1abcd\n\nStatus: implementing\n'
            + review_evidence.REVIEW_EVIDENCE_SOURCE_DECLARATION
            + '\n\n## Objective\n\nPreserve material intent.\n\n## Review Evidence\n\n'
            + review_evidence.empty_external_finding_synthesis_section()
            + '\n## Progress Log\n\nInitial progress.\n', []))
        self.change = self.wave.with_name('1abce-bug example.md')
        self.change.write_text(f'# Example\n\n{vocabulary_profile.MEMBER_ID_LABEL}: `1abce-bug example`\n'
                               f'{vocabulary_profile.MEMBER_STATUS_LABEL}: implementing\n'
                               '\n## Acceptance Criteria\n\n- [ ] AC-1: Preserve the label.\n'
                               '\n## Progress Log\n\nInitial progress.\n'
                               '\n## Session Handoff\n\nSubstantive restriction.\n')

    def _render(self, text, rows):
        e = self.evidence
        text = e.render_review_evidence_projection(text, rows)
        return e.render_review_status_projection(text, rows, e.required_review_status_keys(self.repo, text, rows))

    def _publish(self):
        e = self.evidence
        old, errors = e.parse_review_event_bytes(self.ledger.read_bytes())
        self.assertEqual(errors, ())
        rows, errors = e.build_compact_review_event(old, {
            'event': 'run', 'actor': 'council-chair', 'context_id': 'bookkeeping',
            'run_kind': 'initial_delivery', 'cycle': 0})
        self.assertEqual(errors, ())
        all_rows = [*old, *rows]
        approval, errors = e.build_compact_review_event(all_rows, {
            'event': 'approval', 'actor': 'qa-reviewer', 'context_id': 'independent-approval',
            'signoff_key': 'qa-reviewer', 'approval_phase': 'delivery',
            'fresh_context': True, 'independent': True, 'observed': 'checked current controls',
            'artifact_or_test_id': 'test:canonical-bookkeeping',
            'integrity_checks': {
                'test_ran_without_unintended_skip': True, 'public_path_reached': True,
                'boundary_values_realistic': True, 'assertions_non_vacuous': True,
                'known_bad_detected': True, 'known_bad_detection_method': 'classifier mutant rejected'}})
        self.assertEqual(errors, ())
        all_rows.extend(approval)
        with e.project_state_publication_lock(self.repo):
            self.ledger.write_bytes(e.canonical_review_events_bytes(all_rows))
            self.wave.write_text(self._render(self.wave.read_text().replace('Initial progress.', 'Recorded progress.'), all_rows))
            self.change.write_text(self.change.read_text().replace('[ ] AC-1', '[x] AC-1').replace('Initial progress.', 'Recorded progress.'))

    def _assert_rejected(self, publish):
        ret, out, err = self._external_main(['--no-cache'], publish)
        self.assertEqual(ret, 1, out + err)
        self.assertFalse(self.cache_file.exists(), out + err)
        self.assertIn('CHANGED', err)

    def test_external_canonical_bookkeeping_passes_and_next_run_reuses_receipt(self):
        with patch.object(run_tests, '_run_file', wraps=run_tests._run_file) as workers:
            ret, out, err = self._external_main(['--no-cache'], self._publish)
            self.assertEqual(ret, 0, out + err)
            receipt = json.loads(self.cache_file.read_text())
            self.assertEqual(receipt['result'], 'ok')
            self.assertEqual(receipt['inputs_hash'], run_tests._hash_inputs())
            ret, out, err = self._main([], 'none', self.change)
            self.assertEqual(ret, 0, out + err)
            self.assertEqual(workers.call_count, 1, out + err)

    def test_disabling_classifier_is_detected_by_external_publisher_control(self):
        with patch.object(run_tests, '_bookkeeping_changes', return_value=set()):
            self._assert_rejected(self._publish)

    def test_material_change_carriers_fail(self):
        before = self.change.read_text()
        # Change 23q1h: a deferral with a canonical `*Status: ...*` note is
        # bookkeeping now (the pair was `[ ] AC-1` -> `[~] AC-1`); a deferral
        # whose reason is in another form changes criterion text and stays material.
        for old, new in [('Preserve the label.', 'Alter the label.'),
                         ('[ ] AC-1: Preserve the label.', '[~] AC-1: Preserve the label. *dropped*'),
                         ('Substantive restriction.', 'A changed restriction.')]:
            with self.subTest(material=new):
                self.change.write_text(before)
                self._assert_rejected(lambda: self.change.write_text(before.replace(old, new)))

    def test_a_canonical_deferral_is_bookkeeping(self):
        """Change 23q1h: deferring a criterion with a canonical note leaves the
        review-policy digest, so the runner tolerates it like a tick."""
        before = self.change.read_text()
        deferred = before.replace('[ ] AC-1: Preserve the label.', '[~] AC-1: Preserve the label. *Status: dropped*')
        self.assertNotEqual(deferred, before)
        ret, out, err = self._external_main(['--no-cache'], lambda: self.change.write_text(deferred))
        self.assertEqual(ret, 0, out + err)

    def test_source_change_with_same_size_and_restored_mtime_fails_final_hash(self):
        source = run_tests._FRAMEWORK_DIR / 'source.py'
        st = source.stat()
        def publish():
            source.write_text('new = 1\n')
            os.utime(source, ns=(st.st_atime_ns, st.st_mtime_ns))
        ret, out, err = self._external_main(['--no-cache'], publish)
        self.assertEqual(ret, 1, out + err)
        self.assertIn('INPUTS CHANGED', err)
        self.assertFalse(self.cache_file.exists())

    def test_corrupt_history_and_forged_views_fail(self):
        self._publish()
        baseline_ledger, baseline_wave = self.ledger.read_bytes(), self.wave.read_text()
        variants = {
            'malformed': lambda: self.ledger.write_bytes(baseline_ledger + b'not-json\n'),
            'truncated': lambda: self.ledger.write_bytes(b''),
            'rewritten': lambda: self.ledger.write_bytes(baseline_ledger.replace(b'bookkeeping', b'other-state')),
            'forged_view': lambda: self.wave.write_text(baseline_wave.replace('no current executed approval', 'forged current approval')),
            # negative-fixture: malformed source declaration must deny the bookkeeping exemption.
            'false_declaration': lambda: self.wave.write_text(baseline_wave.replace('review-evidence-source: events.jsonl', 'review-evidence-source: `events.jsonl`')),
        }
        for name, publish in variants.items():
            with self.subTest(change=name):
                self.ledger.write_bytes(baseline_ledger)
                self.wave.write_text(baseline_wave)
                self._assert_rejected(publish)

    def test_busy_publication_observation_fails_without_receipt(self):
        e = self.evidence
        with patch.object(e, 'project_state_publication_lock', side_effect=e.ProjectPublicationUnavailable('busy')):
            ret, out, err = self._main(['--no-cache'], 'none', self.wave)
        self.assertEqual(ret, 1, out + err)
        self.assertIn('NOT VERIFIED', err)
        self.assertFalse(self.cache_file.exists())

    def test_valid_policy_receipt_append_is_material(self):
        import review_policy
        receipt, appended = review_policy.build_policy_receipt({
            'schema_version': 1, 'evaluator_version': 7,
            'policy_input_digest': 'changed-policy', 'delivery_mode': 'targeted',
            'primer_depth': 'standard', 'council_seats': ['red-team'],
            'requested_lanes': [], 'required_lanes': [],
            'delivery_council_required': False}, None)
        self.assertTrue(appended)
        self.assertEqual(self.evidence.validate_review_evidence_records([receipt]), ())
        def publish():
            with self.evidence.project_state_publication_lock(self.repo):
                self.ledger.write_bytes(self.evidence.canonical_review_events_bytes([receipt]))
                self.wave.write_text(self._render(self.wave.read_text(), [receipt]))
        self._assert_rejected(publish)

    def test_unregistered_or_new_ledger_does_not_gain_an_exemption(self):
        # Change 23nqu: re-based on paths that still refuse. An unregistered
        # ledger inside the folder of the wave open at the start, and one
        # outside docs/; docs/events.jsonl itself is now tolerated.
        for other in (self.wave.parent / 'nested' / 'events.jsonl', self.repo / 'other' / 'events.jsonl'):
            with self.subTest(path=other.relative_to(self.repo).as_posix()):
                other.parent.mkdir(exist_ok=True)
                self._assert_rejected(lambda: other.write_text('{}\n'))
                other.unlink()

    def test_missing_worker_marker_mutant_reaches_and_changes_valid_progress(self):
        import test_worker_guard
        before = self.change.read_text()
        after = before.replace('Initial progress.', 'Leaked worker progress.')
        ret, out, err = self._main(['--no-cache'], 'content', self.change, after)
        self.assertEqual(ret, 1, out + err)
        self.assertEqual(self.change.read_text(), before)
        self.assertFalse(self.cache_file.exists())
        # Mutate the actual worker-environment boundary; mutating a copied
        # helper could silently exercise the already-loaded outer module.
        with patch.object(test_worker_guard, 'worker_environment', side_effect=lambda env, *_: env):
            ret, out, err = self._main(['--no-cache'], 'content', self.change, after)
        self.assertEqual(ret, 0, out + err)
        self.assertEqual(self.change.read_text(), after)
        self.assertTrue(self.cache_file.exists(), 'the negative control must expose the missing prevention')

    def test_open_wave_bookkeeping_is_not_listed_as_tolerated(self):
        # Change 23nqu, AC-5: on a wave open at the start, a Progress Log edit,
        # an append-only ledger write without a new receipt and a telemetry-only
        # record change are not changes and are not listed as tolerated.
        import context_efficiency

        def publish():
            self._publish()
            snapshot = context_efficiency.empty_checkpoint("1abcd")
            snapshot["generation"] = 3
            self.wave.write_text(context_efficiency.replace_checkpoint_block(self.wave.read_text(), snapshot))
        ret, out, err = self._external_main(['--no-cache'], publish)
        self.assertEqual(ret, 0, out + err)
        self.assertIn('Recorded progress.', self.change.read_text())
        self.assertIn('wave:context-efficiency begin', self.wave.read_text())
        self.assertNotIn('TOLERATED', out + err)
        self.assertNotIn('tolerated_changes', json.loads(self.cache_file.read_text()))

    def test_policy_receipt_in_open_wave_is_refused_not_tolerated(self):
        # Change 23nqu, AC-2.3: the folder of a wave open at the start refuses.
        import review_policy
        receipt, _ = review_policy.build_policy_receipt({
            'schema_version': 1, 'evaluator_version': 7,
            'policy_input_digest': 'changed-policy', 'delivery_mode': 'targeted',
            'primer_depth': 'standard', 'council_seats': ['red-team'],
            'requested_lanes': [], 'required_lanes': [],
            'delivery_council_required': False}, None)
        def publish():
            with self.evidence.project_state_publication_lock(self.repo):
                self.ledger.write_bytes(self.evidence.canonical_review_events_bytes([receipt]))
                self.wave.write_text(self._render(self.wave.read_text(), [receipt]))
        ret, out, err = self._external_main(['--no-cache'], publish)
        self.assertEqual(ret, 1, out + err)
        self.assertIn('REPOSITORY CHANGED DURING THE TEST RUN', err)
        self.assertIn(self.ledger.relative_to(self.repo).as_posix(), err)
        self.assertNotIn('AND TOLERATED', out)
        self.assertFalse(self.cache_file.exists())

    def test_regular_file_replaced_by_symlink_is_not_bookkeeping(self):
        fixture = self.tmp / 'replacement.md'
        fixture.write_bytes(self.change.read_bytes())
        def publish():
            self.change.unlink()
            self.change.symlink_to(fixture)
        self._assert_rejected(publish)


class ProtectedWorkerTests(RepoGuardTestBase):
    def setUp(self):
        super().setUp()
        import record_paths
        self.protected = self.repo / record_paths.WAVES_ROOT / '1abcd example' / 'events.jsonl'
        self.protected.parent.mkdir(parents=True)
        self.protected.write_text('protected\n')
        self.scratch = self.tmp / 'scratch'
        self.scratch.mkdir()

    def _worker(self, code, *, reporting=False, import_time=False):
        header = 'import os, sys, subprocess, shutil, unittest\nfrom pathlib import Path\n'
        body = code if import_time else 'class Control(unittest.TestCase):\n    def test_operation(self):\n' + ''.join('        ' + line + '\n' for line in code.splitlines())
        (self.tests_dir / 'test_mutant.py').write_text(header + body + '\n')
        with patch.object(run_tests, '_QUALIFICATION_REQUESTED', reporting):
            return run_tests._run_file(self.tests_dir / 'test_mutant.py')

    def test_ordinary_and_reporting_workers_refuse_before_import_or_test_write(self):
        before = self.protected.read_bytes()
        for reporting in (False, True):
            for import_time in (False, True):
                with self.subTest(reporting=reporting, import_time=import_time):
                    result = self._worker(f'Path({str(self.protected)!r}).write_text("bad")', reporting=reporting, import_time=import_time)
                    self.assertNotEqual(result.returncode, 0, result.output)
                    self.assertIn('PermissionError', result.output)
                    self.assertEqual(self.protected.read_bytes(), before)

    def test_supported_write_routes_refuse_and_fixture_writes_succeed(self):
        p, scratch = repr(str(self.protected)), repr(str(self.scratch))
        alias = self.scratch / 'linked'
        alias.symlink_to(self.protected.parent, target_is_directory=True)
        operations = [f'Path({p}).write_text("bad")',
                      f'os.open({p}, os.O_WRONLY | os.O_APPEND)',
                      f'Path({p}).unlink()',
                      f'os.chdir(str(Path({p}).parent)); Path("events.jsonl").write_text("bad")',
                      f'Path({str(alias / "events.jsonl")!r}).write_text("bad")',
                      f'os.rename(str(Path({p}).parent), {str(self.scratch / "moved")!r})',
                      f'shutil.rmtree(str(Path({p}).parent))',
                      f'Path({scratch}, "replace").write_text("bad"); os.replace(str(Path({scratch}, "replace")), {p})',
                      f'fd = os.open(str(Path({p}).parent), os.O_RDONLY); os.chdir({scratch}); os.open("events.jsonl", os.O_WRONLY, dir_fd=fd)']
        for code in operations:
            with self.subTest(code=code):
                result = self._worker(code)
                self.assertNotEqual(result.returncode, 0, result.output)
                self.assertIn('PermissionError', result.output)
                self.assertEqual(self.protected.read_text(), 'protected\n')
        result = self._worker(f'fd = os.open({scratch}, os.O_RDONLY)\nos.chdir(str(Path({p}).parent))\nfd2 = os.open("new.txt", os.O_WRONLY | os.O_CREAT, 0o600, dir_fd=fd)\nos.write(fd2, b"fixture")\nos.close(fd2)\nos.close(fd)\nPath({scratch}, "nested").mkdir()\nPath({scratch}, "nested", "data").write_text("fixture")\nshutil.rmtree(Path({scratch}, "nested"))')
        self.assertEqual(result.returncode, 0, result.output)
        self.assertEqual((self.scratch / 'new.txt').read_bytes(), b'fixture')

    def test_exec_and_fork_descendants_refuse_but_isolated_raw_write_limit_is_explicit(self):
        child = f'from pathlib import Path; Path({str(self.protected)!r}).write_text("bad")'
        result = self._worker(f'child = subprocess.run([sys.executable, "-B", "-c", {child!r}], capture_output=True, text=True)\nself.assertNotEqual(child.returncode, 0, child.stdout + child.stderr)\nself.assertIn("PermissionError", child.stderr)')
        self.assertEqual(result.returncode, 0, result.output)
        if hasattr(os, 'fork'):
            result = self._worker(f'pid = os.fork()\nif pid == 0:\n    try: exec({child!r})\n    except PermissionError: os._exit(0)\n    os._exit(1)\nself.assertEqual(os.waitpid(pid, 0)[1], 0)')
            self.assertEqual(result.returncode, 0, result.output)
        self.assertEqual(self.protected.read_text(), 'protected\n')
        # -I drops the inherited site hook. This admitted raw route is not an
        # authentication boundary; unclassified bytes still fail the parent
        # when they land in a wave open at the start of the run (change 23nqu
        # re-based this on an open wave: the folder had no record before).
        import vocabulary_profile
        (self.protected.parent / vocabulary_profile.RECORD_FILENAME).write_text('# Wave\n\nStatus: implementing\n')
        raw = ('import subprocess, sys, unittest\nclass Control(unittest.TestCase):\n    def test_raw(self):\n'
               '        subprocess.run([sys.executable, "-I", "-B", "-c", {!r}], check=True)\n')
        (self.tests_dir / 'test_mutant.py').write_text(raw.format(child))
        ret, out, err = self._main(['--no-cache'], 'none', self.protected)
        self.assertEqual(ret, 1, out + err)
        self.assertIn('REPOSITORY CHANGED', err)
        self.assertEqual(self.protected.read_text(), 'bad')
        self.assertFalse(self.cache_file.exists())
        # The stated limit: the same raw route writing elsewhere under docs/
        # is no longer caught; it is tolerated and listed.
        note = self.repo / 'docs' / 'notes.md'
        note.write_text('before\n')
        (self.tests_dir / 'test_mutant.py').write_text(raw.format(
            f'from pathlib import Path; Path({str(note)!r}).write_text("bad")'))
        ret, out, err = self._main(['--no-cache'], 'none', note)
        self.assertEqual(ret, 0, out + err)
        self.assertEqual(note.read_text(), 'bad')
        self.assertIn('FILES CHANGED DURING THE TEST RUN AND TOLERATED', out)
        self.assertIn('docs/notes.md', out)

    def test_documentation_root_write_refuses_and_record_roots_only_control_allows_it(self):
        # Change 23nqu, AC-3: the fixture repository's docs/ outside the waves
        # and plans roots is protected; the reverse control drops it again.
        import test_worker_guard
        target = self.repo / 'docs' / 'agents' / 'session-handoff.md'
        code = f'p = Path({str(target)!r})\np.parent.mkdir(parents=True, exist_ok=True)\np.write_text("written by a test")'
        result = self._worker(code)
        self.assertNotEqual(result.returncode, 0, result.output)
        self.assertIn('PermissionError', result.output)
        self.assertIn('test worker cannot mutate protected record path', result.output)
        self.assertFalse(target.exists())
        real = test_worker_guard.worker_environment
        def record_roots_only(env, root, dirs):
            self.assertIn('docs', dirs)
            return real(env, root, tuple(d for d in dirs if d != 'docs'))
        with patch.object(test_worker_guard, 'worker_environment', side_effect=record_roots_only):
            result = self._worker(code)
        self.assertEqual(result.returncode, 0, result.output)
        self.assertEqual(target.read_text(), 'written by a test')

    def test_existing_directory_creation_under_documentation_root_is_still_allowed(self):
        # Change 23nqu: the exist_ok allowance is kept for the new root.
        # The directories exist before the worker runs (created here, outside
        # it); a profile may move the waves root, so docs/agents is used.
        docs = self.repo / 'docs'
        (docs / 'agents').mkdir(parents=True, exist_ok=True)
        result = self._worker(f'Path({str(docs)!r}).mkdir(parents=True, exist_ok=True)\n'
                              f'os.makedirs({str(docs / "agents")!r}, exist_ok=True)')
        self.assertEqual(result.returncode, 0, result.output)

    def test_descriptor_protection_uses_host_primitive_when_tests_mock_fcntl(self):
        code = (f'from unittest.mock import patch\n'
                f'outside = os.open({str(self.scratch)!r}, os.O_RDONLY)\n'
                f'inside = os.open({str(self.protected.parent)!r}, os.O_RDONLY)\n'
                'try:\n'
                '    with patch.dict(sys.modules, {"fcntl": object()}):\n'
                '        fd = os.open("scratch.txt", os.O_WRONLY | os.O_CREAT, 0o600, dir_fd=outside)\n'
                '        os.write(fd, b"allowed")\n'
                '        os.close(fd)\n'
                '        with self.assertRaises(PermissionError):\n'
                '            os.open("events.jsonl", os.O_WRONLY, dir_fd=inside)\n'
                'finally:\n'
                '    os.close(outside)\n'
                '    os.close(inside)')
        result = self._worker(code)
        self.assertEqual(result.returncode, 0, result.output)
        self.assertEqual((self.scratch / 'scratch.txt').read_bytes(), b'allowed')
        self.assertEqual(self.protected.read_text(), 'protected\n')

    def test_nested_real_runner_preserves_outer_protection_and_allows_its_fixture(self):
        inner = self.tmp / 'inner'
        inner.mkdir()
        inner_tests = inner / 'tests'
        inner_tests.mkdir()
        child = inner_tests / 'test_inner.py'
        child.write_text('import unittest\nfrom pathlib import Path\nclass Inner(unittest.TestCase):\n'
                         '    def test_leak(self):\n        Path(' + repr(str(self.protected)) + ').write_text("bad")\n')
        code = (f'import run_tests\nrun_tests._REPO_ROOT = Path({str(inner)!r})\n'
                f'run_tests._TESTS_DIR = Path({str(inner_tests)!r})\n'
                f'result = run_tests._run_file(Path({str(child)!r}))\n'
                'self.assertNotEqual(result.returncode, 0, result.output)\n'
                'self.assertIn("PermissionError", result.output)')
        result = self._worker(code)
        self.assertEqual(result.returncode, 0, result.output)
        self.assertEqual(self.protected.read_text(), 'protected\n')
        child.write_text(child.read_text().replace(str(self.protected), str(inner / 'fixture.txt')))
        result = self._worker(code.replace('self.assertNotEqual(result.returncode, 0, result.output)',
                                          'self.assertEqual(result.returncode, 0, result.output)').replace(
                                              'self.assertIn("PermissionError", result.output)',
                                              'self.assertIn("Ran 1 test", result.output)'))
        self.assertEqual(result.returncode, 0, result.output)
        self.assertEqual((inner / 'fixture.txt').read_text(), 'bad')


_POLICY_PATHS = ("docs/workflow-config.json", "docs/repo-profile.json", "docs/contributors.json",
                 "docs/scan-rules.toml", "docs/reconcile-dispositions.json")


class DocumentationToleranceBase(RepoGuardTestBase):
    """Change 23nqu fixture: a wave open at the start, a planned wave, plans,
    the session handoff, recorded data and the five policy files."""

    def setUp(self):
        super().setUp()
        import record_paths
        import vocabulary_profile
        self.record_name = vocabulary_profile.RECORD_FILENAME
        self.waves = self.repo / record_paths.WAVES_ROOT
        self.plans = self.repo / record_paths.PLANS_ROOT
        # A wave open at the start, in the framework's own projected form.
        self.open_record = self._wave('1aaaa open', _projected_record(_RECORD_BODY))
        self.open_spec = self.open_record.with_name('1aaab-enh open-spec.md')
        self.open_spec.write_text('# Open spec\n\n## Requirements\n\nOriginal body.\n')
        self.planned_record = self._wave('1bbbb planned', '# Wave 1bbbb\n\nStatus: planned\n')
        self.planned_spec = self.planned_record.with_name('1bbbc-enh planned-spec.md')
        self.planned_spec.write_text(self.open_spec.read_text())
        self.handoff = self.repo / 'docs/agents/session-handoff.md'
        self.handoff.parent.mkdir(parents=True)
        self.handoff.write_text('# Handoff\n\nBefore.\n')
        self.data = self.repo / 'docs/data/recorded.json'
        self.data.parent.mkdir(parents=True)
        self.data.write_text('{"a": 1}\n')
        self.plans.mkdir(parents=True)
        for rel in _POLICY_PATHS:
            (self.repo / rel).write_text('{}\n')

    def _wave(self, folder, text):
        record = self.waves / folder / self.record_name
        record.parent.mkdir(parents=True)
        record.write_text(text)
        return record

    def rel(self, path):
        return path.relative_to(self.repo).as_posix()

    def tolerated(self, out):
        heading = 'FILES CHANGED DURING THE TEST RUN AND TOLERATED'
        if heading not in out:
            return []
        block = out.split(heading, 1)[1].split('\n', 1)[1]
        return [line.strip() for line in block.splitlines() if line.startswith('  ')]

    def assert_refused(self, ret, out, err, *rels):
        self.assertEqual(ret, 1, out + err)
        self.assertIn('REPOSITORY CHANGED DURING THE TEST RUN', err)
        self.assertIn('concurrent edit by an operator or agent', err)
        self.assertIn('edit gate', err)
        for rel in rels:
            self.assertIn('\n  ' + rel + '\n', err + '\n')
            self.assertNotIn(rel, self.tolerated(out))
        self.assertFalse(self.cache_file.exists(), out + err)

    def planning(self):
        """Plan new work during the run: the 23lxd replay."""
        kept = self.plans / '1cccc-enh kept-plan.md'
        moved = self.plans / '1cccd-enh moved-plan.md'
        kept.write_text('# Kept\n')
        moved.write_text('# Moved\n')
        wave = self._wave('1ccce new', '# Wave 1ccce\n\nStatus: planned\n')
        wave.with_name('events.jsonl').write_text('')
        moved.rename(wave.with_name(moved.name))
        self.handoff.write_text('# Handoff\n\nAfter.\n')
        self.data.write_text('{"a": 2}\n')
        # Telemetry-only writes on the wave open at the start.
        self.open_record.write_text(_projected_record(_RECORD_BODY, _STAGES, generation=9))
        return sorted([self.rel(kept), self.rel(wave), self.rel(wave.with_name('events.jsonl')),
                       self.rel(wave.with_name(moved.name)), self.rel(self.handoff), self.rel(self.data)])

class DocumentationToleranceTests(DocumentationToleranceBase):
    """Change 23nqu: changes under docs/ during a run are tolerated and listed,
    except in a wave open at the start of the run and in the policy files."""

    def test_planning_during_a_full_run_is_tolerated_listed_and_receipted(self):
        expected = []
        ret, out, err = self._external_main(['--no-cache'], lambda: expected.extend(self.planning()))
        self.assertEqual(ret, 0, out + err)
        self.assertNotIn('REPOSITORY CHANGED', err)
        self.assertEqual(self.tolerated(out), expected)
        self.assertNotIn(self.rel(self.open_record), out)
        receipt = json.loads(self.cache_file.read_text())
        self.assertEqual(receipt['result'], 'ok')
        self.assertEqual(receipt['tolerated_changes'], {'paths': expected, 'count': len(expected), 'truncated': False})

    def test_planning_during_a_focused_run_is_tolerated_and_listed(self):
        expected = []
        ret, out, err = self._external_main(['--file', 'test_mutant.py'], lambda: expected.extend(self.planning()))
        self.assertEqual(ret, 0, out + err)
        self.assertEqual(self.tolerated(out), expected)
        self.assertFalse(self.cache_file.exists(), 'a focused run never writes the receipt')

    def test_each_case_that_affects_the_work_under_test_still_refuses(self):
        source = run_tests._FRAMEWORK_DIR / 'source.py'
        gate = self.repo / run_tests._GUARD_OVERRIDES_REL
        outside = self.repo / 'src' / 'module.py'
        outside.parent.mkdir()
        cases = [('framework file', source, 'changed = 1\n'),
                 ('edit-gate file', gate, '{"framework_edit_allowed": {"enabled": true}}\n'),
                 ('outside docs', outside, 'x = 1\n')]
        cases += [(rel, self.repo / rel, '{"changed": true}\n') for rel in _POLICY_PATHS]
        for name, path, text in cases:
            with self.subTest(case=name):
                original = path.read_bytes() if path.exists() else None
                ret, out, err = self._external_main(['--no-cache'], lambda: path.write_text(text))
                self.assert_refused(ret, out, err, self.rel(path))
                if original is None:
                    path.unlink()
                else:
                    path.write_bytes(original)

    def test_open_wave_spec_edit_refuses_while_the_same_planned_wave_edit_is_tolerated(self):
        def publish():
            for spec in (self.open_spec, self.planned_spec):
                spec.write_text(spec.read_text().replace('Original body.', 'Changed body.'))
        ret, out, err = self._external_main(['--no-cache'], publish)
        self.assert_refused(ret, out, err, self.rel(self.open_spec))
        self.assertEqual(self.tolerated(out), [self.rel(self.planned_spec)])

    def test_closing_a_wave_open_at_the_start_refuses(self):
        for status in ('closed', 'paused'):
            with self.subTest(status=status):
                text = self.open_record.read_text()
                ret, out, err = self._external_main(['--no-cache'], lambda: self.open_record.write_text(
                    text.replace('Status: implementing', f'Status: {status}')))
                self.assert_refused(ret, out, err, self.rel(self.open_record))
                self.open_record.write_text(text)

    def test_admitting_a_spec_to_a_wave_open_at_the_start_refuses(self):
        plan = self.plans / '1dddd-enh admitted.md'
        plan.write_text('# Admitted\n')
        ret, out, err = self._external_main(['--no-cache'], lambda: plan.rename(self.open_record.with_name(plan.name)))
        self.assert_refused(ret, out, err, self.rel(self.open_record.with_name(plan.name)))
        self.assertEqual(self.tolerated(out), [self.rel(plan)])

    def test_a_wave_opened_during_the_run_does_not_join_the_refused_set(self):
        def publish():
            self.planned_record.write_text('# Wave 1bbbb\n\nStatus: active\n')
            self.planned_spec.write_text('# Planned spec\n\nRewritten.\n')
        ret, out, err = self._external_main(['--no-cache'], publish)
        self.assertEqual(ret, 0, out + err)
        self.assertEqual(self.tolerated(out), sorted([self.rel(self.planned_record), self.rel(self.planned_spec)]))

    def test_receipt_list_is_bounded_with_a_count_and_truncation_flag(self):
        def publish():
            for name in ('c', 'a', 'b'):
                (self.repo / 'docs' / f'{name}.md').write_text(name)
        with patch.object(run_tests, '_TOLERATED_RECEIPT_MAX_PATHS', 2):
            ret, out, err = self._external_main(['--no-cache'], publish)
        self.assertEqual(ret, 0, out + err)
        self.assertEqual(json.loads(self.cache_file.read_text())['tolerated_changes'],
                         {'paths': ['docs/a.md', 'docs/b.md'], 'count': 3, 'truncated': True})

    def test_receipt_with_and_without_the_field_are_both_proven_by_the_close_gate(self):
        import lifecycle_gate_support
        import lifecycle_gates
        receipts = {}
        ret, out, err = self._main(['--no-cache'], 'none', self.repo / 'unused')
        self.assertEqual(ret, 0, out + err)
        receipts['absent'] = self.cache_file.read_text()
        self.cache_file.unlink()
        ret, out, err = self._external_main(['--no-cache'], lambda: self.handoff.write_text('changed\n'))
        self.assertEqual(ret, 0, out + err)
        receipts['present'] = self.cache_file.read_text()
        self.assertNotIn('tolerated_changes', json.loads(receipts['absent']))
        self.assertEqual(json.loads(receipts['present'])['tolerated_changes']['paths'], [self.rel(self.handoff)])
        for name, text in receipts.items():
            with self.subTest(receipt=name):
                gate_root = self.tmp / f'gate-{name}'
                runner = gate_root / lifecycle_gate_support._FRAMEWORK_TEST_RUNNER_REL
                runner.parent.mkdir(parents=True)
                runner.with_name('test-cache.json').write_text(text)
                # The real reader protocol over this run's own receipt bytes.
                runner.write_text('import json\nfrom pathlib import Path\n'
                                  f'def _hash_inputs(): return {json.loads(text)["inputs_hash"]!r}\n'
                                  "def _read_cache(): return json.loads(Path(__file__).with_name('test-cache.json').read_text())\n")
                self.assertEqual(lifecycle_gates._framework_test_receipt_status(gate_root)['state'], 'proven')

    def test_nested_layout_renamed_record_and_archive_root_are_classified(self):
        import record_paths
        import vocabulary_profile
        nested_open = self.waves / 'group' / '1eeee nested' / 'set.md'
        nested_planned = self.waves / 'group' / '1eeef nested-planned' / 'set.md'
        archived = self.repo / 'docs/archive/1ffff old' / 'set.md'
        for record, status in ((nested_open, 'active'), (nested_planned, 'planned'), (archived, 'closed')):
            record.parent.mkdir(parents=True)
            record.write_text(f'# Wave\n\nStatus: {status}\n')
            record.with_name('notes.md').write_text('before\n')
        # Records named by the renamed vocabulary only; the shipped name is now
        # an ordinary document, so the old open record no longer counts.
        with patch.object(record_paths, 'NESTED', True), \
                patch.object(record_paths, 'ARCHIVE_ROOT', 'docs/archive'), \
                patch.object(vocabulary_profile, 'RECORD_FILENAME', 'set.md'):
            def publish():
                for record in (nested_open, nested_planned, archived):
                    record.with_name('notes.md').write_text('after\n')
            ret, out, err = self._external_main(['--no-cache'], publish)
        self.assert_refused(ret, out, err, self.rel(nested_open.with_name('notes.md')))
        self.assertEqual(self.tolerated(out), sorted([self.rel(nested_planned.with_name('notes.md')),
                                                      self.rel(archived.with_name('notes.md'))]))

    def test_policy_paths_match_their_producers(self):
        import reconcile_scan
        from wave_lint_lib import constants
        self.assertEqual(run_tests._POLICY_FILES, frozenset(_POLICY_PATHS))
        self.assertEqual(reconcile_scan.WORKFLOW_CONFIG_REL, 'docs/workflow-config.json')
        self.assertEqual(reconcile_scan.DISPOSITIONS_REL, 'docs/reconcile-dispositions.json')
        self.assertEqual(constants.SCAN_RULES_PROJECT_PATH, 'docs/scan-rules.toml')
        # No constant exists for these two; pin the producers' own spelling.
        self.assertIn('(Path(root) / "docs" / "contributors.json")',
                      (SCRIPTS_DIR / 'operator_identity.py').read_text(encoding='utf-8'))
        self.assertIn('root / "docs/repo-profile.json"', (SCRIPTS_DIR / 'project_stats.py').read_text(encoding='utf-8'))
        self.assertEqual(run_tests._DOCS_ROOT_REL + '/', 'docs/')
        # Generated output stays tolerated.
        self.assertNotIn('docs/scan-findings.json', run_tests._POLICY_FILES)


class DocumentationToleranceFailsClosedTests(DocumentationToleranceBase):
    """Change 23nqu, AC-4: an undeterminable open-wave set tolerates nothing."""

    def _refuses_the_handoff(self):
        ret, out, err = self._external_main(['--no-cache'], lambda: self.handoff.write_text('changed\n'))
        self.assert_refused(ret, out, err, self.rel(self.handoff))
        self.assertIn('Documentation tolerance is off for this run', err)
        self.assertEqual(self.tolerated(out), [])

    def test_unreadable_layout_refuses_through_the_classifier(self):
        # The worker launch fails every file when the layout itself is
        # invalid, so a full run cannot isolate this branch. Drive the end-of-
        # run comparison on real snapshots instead, with the control first.
        before = run_tests.repo_state_snapshot(self.repo)
        self.assertTrue(before.layout_known)
        self.handoff.write_text('changed\n')
        self.assertIsNone(run_tests._stray_artifact_failure([], before, self.repo))
        self.assertEqual(run_tests._LAST_TOLERATED_CHANGES, [self.rel(self.handoff)])
        self.handoff.write_text('# Handoff\n\nBefore.\n')
        with patch.object(run_tests, '_record_layout', return_value=None):
            before = run_tests.repo_state_snapshot(self.repo)
        self.assertFalse(before.layout_known)
        self.handoff.write_text('changed again\n')
        message = run_tests._stray_artifact_failure([], before, self.repo)
        self.assertIsNotNone(message)
        self.assertIn(self.rel(self.handoff), message)
        self.assertIn('the record layout could not be read', message)
        self.assertEqual(run_tests._LAST_TOLERATED_CHANGES, [])

    def test_unreadable_matcher_refuses_a_full_run(self):
        with patch.object(run_tests, '_wave_record_matcher', return_value=None):
            self._refuses_the_handoff()

    def test_unparseable_status_refuses_a_full_run(self):
        good = self.planned_record.read_bytes()
        variants = {'unknown value': b'# Wave\n\nStatus: someday\n',
                    'no status line': b'# Wave\n\nNo status here.\n',
                    'two status lines': b'# Wave\n\nStatus: planned\nStatus: planned\n',
                    'not utf-8': b'# Wave\n\nStatus: planned\n\xff\xfe\n'}
        for name, data in variants.items():
            with self.subTest(variant=name):
                self.planned_record.write_bytes(data)
                self._refuses_the_handoff()
                self.handoff.write_text('# Handoff\n\nBefore.\n')
        self.planned_record.write_bytes(good)
        # Spaces and backticks around a known status are accepted.
        self.planned_record.write_text('# Wave\n\nStatus: ` planned `\n')
        ret, out, err = self._external_main(['--no-cache'], lambda: self.handoff.write_text('changed\n'))
        self.assertEqual(ret, 0, out + err)

    def test_unreadable_or_linked_record_refuses_a_full_run(self):
        # The same branch: a record with no captured bytes.
        linked = self.tmp / 'linked-record.md'
        linked.write_bytes(self.planned_record.read_bytes())
        self.planned_record.unlink()
        self.planned_record.symlink_to(linked)
        with self.subTest(case='link'):
            self._refuses_the_handoff()
        self.planned_record.unlink()
        self.planned_record.write_bytes(linked.read_bytes())
        self.handoff.write_text('# Handoff\n\nBefore.\n')
        if os.name == 'nt' or os.geteuid() == 0:
            return
        self.planned_record.chmod(0)
        try:
            with self.subTest(case='unreadable'):
                self._refuses_the_handoff()
        finally:
            self.planned_record.chmod(0o644)


class RenamedBookkeepingProfileTests(unittest.TestCase):
    def test_renamed_member_label_runs_real_publication_and_reuses_receipt(self):
        import re
        from record_layout_support import (
            SHIPPED_DEFAULTS, apply_profile, copy_scripts_tree,
            shipped_default_profile, with_vocabulary,
        )
        with tempfile.TemporaryDirectory(prefix='wf-bookkeeping-profile-') as tmp:
            scripts = copy_scripts_tree(Path(tmp) / '.wavefoundry/framework')
            target = scripts / 'tests' / Path(__file__).name
            shutil.copy2(__file__, target)
            profile = with_vocabulary(shipped_default_profile(),
                                      MEMBER_ID_LABEL='Item (key)', MEMBER_STATUS_LABEL='Item State')
            apply_profile(scripts, profile, modules=('vocabulary_profile',), python=sys.executable)
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
            env.pop('PYTHONPYCACHEPREFIX', None)
            command = [sys.executable, '-B', str(target),
                       'CanonicalBookkeepingTests.test_external_canonical_bookkeeping_passes_and_next_run_reuses_receipt']
            passed = subprocess.run(command, cwd=scripts, env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
            self.assertIn('Ran 1 test', passed.stderr)
            # Known bad: pin the classifier's escaped field label back to the
            # shipped vocabulary in this disposable profile, then rerun the
            # same real-worker oracle. The renamed carrier must be rejected.
            vocabulary = scripts / 'vocabulary_profile.py'
            source = vocabulary.read_text()
            old = 'MEMBER_ID_LABEL_RE = re.escape(MEMBER_ID_LABEL)'
            fixed = re.escape(SHIPPED_DEFAULTS['vocabulary_profile']['MEMBER_ID_LABEL'])
            self.assertEqual(source.count(old), 1)
            vocabulary.write_text(source.replace(old, f'MEMBER_ID_LABEL_RE = {fixed!r}'))
            rejected = subprocess.run(command, cwd=scripts, env=env, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(rejected.returncode, 0, rejected.stdout + rejected.stderr)
            self.assertIn('REPOSITORY CHANGED DURING THE TEST RUN', rejected.stdout + rejected.stderr)


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

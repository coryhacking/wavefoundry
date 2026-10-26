"""Prospective recovery exercises the real worker and public runner entry point."""
from __future__ import annotations

import copy
import datetime
import json
import os
import sys
import unittest
import threading
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import qualification_report as qualification
from tests import test_run_tests_repo_guard as guard
from tests.record_layout_support import RecordTreeBuilder

run_tests = guard.run_tests
REAL_ACQUIRE = run_tests._acquire_run_lock
REAL_RELEASE = run_tests._release_run_lock


def setUpModule():
    guard.setUpModule()


class ReconciliationCLITests(guard.RepoGuardTestBase):
    def setUp(self):
        super().setUp()
        self.enterContext(patch.object(run_tests, "_configure_bytecode_cache", return_value=(None, False)))
        self.enterContext(patch.object(run_tests, "_warm_bytecode_cache"))
        self.env = self.enterContext(patch.dict(os.environ))
        os.environ.pop("WAVEFOUNDRY_TEST_PROFILE", None)
        self.previous_cwd = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, self.previous_cwd)
        with (self.repo / ".gitignore").open("a") as stream:
            stream.write(".wavefoundry/cache/\n")
        self.gate = self.repo / run_tests._GUARD_OVERRIDES_REL
        self.gate.write_text(json.dumps({"framework_edit_allowed": {"enabled": True}, "other": {"count": 1}}))
        self.doc = self.repo / "docs/prompts/review-wave.prompt.md"
        self.doc.parent.mkdir(parents=True)
        self.doc.write_text("1. One\n3. Two\n4. Three\n")
        self.note = "Operator reviewed the exact displayed numbering correction as editorial."

    def close_and_edit(self):
        self.gate.write_text(json.dumps({"framework_edit_allowed": {"enabled": False}, "other": {"count": 1}}))
        self.doc.write_text("1. One\n2. Two\n3. Three\n")

    def refused(self, publish=None):
        code, out, err = self._external_main(["--no-cache"], publish or self.close_and_edit)
        self.assertEqual(code, 1, out + err)
        reports = sorted((self.repo / ".wavefoundry/cache/qualification").glob("refused-*.json"))
        self.assertEqual(len(reports), 1, out + err)
        self.path = reports[0].relative_to(self.repo).as_posix()
        self.original_bytes = reports[0].read_bytes()
        self.original = json.loads(self.original_bytes)
        return self.original

    def cli(self, *args):
        # Reconciliation must not launch workers or warm bytecode even on refusals.
        with patch.object(run_tests, "_run_file", side_effect=AssertionError("worker launched")), \
                patch.object(run_tests, "_warm_bytecode_cache", side_effect=AssertionError("warming started")):
            code, out, err = self._main(list(args), "none", self.doc)
        return code, json.loads(out) if out.startswith("{") else out, err

    def inspect(self):
        code, result, err = self.cli("--reconcile", self.path)
        self.assertEqual(code, 0, str(result) + err)
        self.assertTrue(result["eligible"])
        return result

    def accept(self, token):
        return self.cli("--reconcile", self.path, "--accept", token, "--operator-reviewed", self.note)

    def rewrite_original(self, mutate):
        # Deliberately corrupt a disposable report; production never rewrites it.
        value = copy.deepcopy(self.original)
        mutate(value)
        qualification.write_report(self.repo, self.path, value)

    def assert_refused(self, token=None):
        before = self.cache_file.read_bytes() if self.cache_file.exists() else None
        code, result, err = (self.accept(token) if token else self.cli("--reconcile", self.path))
        self.assertEqual(code, 1, str(result) + err)
        self.assertFalse(result["eligible"])
        self.assertEqual(self.cache_file.read_bytes() if self.cache_file.exists() else None, before)
        return result["reason"]

    def test_complete_guard_only_run_accepts_and_reuses_with_original_identity(self):
        original = self.refused()
        self.assertTrue(original["complete"])
        self.assertEqual(original["returncode"], 1)
        self.assertEqual(original["workers"][0]["returncode"], 0)
        inspection = self.inspect()
        self.assertEqual(set(inspection["differences"]), {run_tests._GUARD_OVERRIDES_REL, self.doc.relative_to(self.repo).as_posix()})
        self.assertIn("-3. Two", inspection["differences"][self.doc.relative_to(self.repo).as_posix()]["diff"])
        code, accepted, err = self.accept(inspection["token"])
        self.assertEqual(code, 0, str(accepted) + err)
        receipt = json.loads(self.cache_file.read_text())
        detail = qualification.read_report(self.repo, qualification.LAST_DEFAULT)
        self.assertEqual(receipt["run_id"], original["run_id"])
        self.assertEqual(receipt["ran_at"], original["ran_at"])
        self.assertEqual(detail["run_id"], original["run_id"])
        self.assertEqual(detail["reconciliation"], receipt["reconciliation"])
        self.assertEqual((self.repo / self.path).read_bytes(), self.original_bytes)
        exported = ".wavefoundry/cache/qualification/reused.json"
        with patch.object(run_tests, "_run_file", side_effect=AssertionError("cache ran workers")):
            code, out, err = self._main(["--qualification-report", exported], "none", self.doc)
        self.assertEqual(code, 0, out + err)
        reused = qualification.read_report(self.repo, exported)
        self.assertEqual(reused["reconciliation"], receipt["reconciliation"])
        self.assertEqual(reused["run_id"], original["run_id"])

    def test_identical_acceptance_retry_has_one_authority_and_stable_bytes(self):
        self.refused()
        token = self.inspect()["token"]
        self.assertEqual(self.accept(token)[0], 0)
        receipt = self.cache_file.read_bytes()
        detail = (self.repo / qualification.LAST_DEFAULT).read_bytes()
        first = self.accept(token)
        self.assertEqual(first[0], 0, str(first))
        self.assertEqual(self.cache_file.read_bytes(), receipt)
        self.assertEqual((self.repo / qualification.LAST_DEFAULT).read_bytes(), detail)
        self.assertEqual(len(list((self.repo / ".wavefoundry/cache/qualification").glob("accepted-*"))), 1)

    def test_partial_publication_retry_recovers_without_workers(self):
        self.refused()
        token = self.inspect()["token"]
        with patch.object(run_tests, "_write_cache"):
            self.assertIn("publication incomplete", self.assert_refused(token))
        self.assertTrue((self.repo / qualification.LAST_DEFAULT).exists())
        self.assertEqual(self.accept(token)[0], 0)

    def test_partial_detail_publication_retry_recovers(self):
        self.refused()
        token = self.inspect()["token"]
        real_write = qualification.write_report
        def interrupt(root, path, report, **kwargs):
            if path == qualification.LAST_DEFAULT:
                raise OSError("disposable interruption")
            return real_write(root, path, report, **kwargs)
        with patch.object(qualification, "write_report", side_effect=interrupt):
            self.assertIn("interruption", self.assert_refused(token))
        self.assertEqual(self.accept(token)[0], 0)

    def test_newer_unrelated_receipt_is_preserved(self):
        self.refused()
        token = self.inspect()["token"]
        self.cache_file.write_text(json.dumps({"result": "ok", "inputs_hash": "newer",
            "ran_at": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat()}))
        self.assertIn("newer", self.assert_refused(token))

    def test_newer_unrelated_detail_is_preserved(self):
        self.refused()
        token = self.inspect()["token"]
        newer = dict(self.original, returncode=0)
        newer.pop("recovery")
        newer["ran_at"] = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat()
        newer["run_id"] = "f" * 32
        qualification.validate(newer)
        qualification.write_report(self.repo, qualification.LAST_DEFAULT, newer)
        detail = self.repo / qualification.LAST_DEFAULT
        before = detail.read_bytes()
        self.assertIn("unrelated detail", self.assert_refused(token))
        self.assertEqual(detail.read_bytes(), before)

    def test_edit_after_inspection_even_with_restored_mtime_refuses(self):
        self.refused()
        token = self.inspect()["token"]
        st = self.doc.stat()
        self.doc.write_text(self.doc.read_text().replace("Two", "Six"))
        os.utime(self.doc, ns=(st.st_atime_ns, st.st_mtime_ns))
        self.assertIn("content changed", self.assert_refused())
        self.assertIn("content changed", self.assert_refused(token))

    def test_binary_input_edit_after_inspection_refuses(self):
        binary = self.repo / "opaque.bin"
        binary.write_bytes(b"\x00\xff\x00")
        self.refused()
        token = self.inspect()["token"]
        st = binary.stat()
        binary.write_bytes(b"\x00\xfe\x00")
        os.utime(binary, ns=(st.st_atime_ns, st.st_mtime_ns))
        self.assertIn("content changed", self.assert_refused(token))

    def test_current_framework_edit_and_in_run_framework_edit_refuse(self):
        self.refused()
        token = self.inspect()["token"]
        source = self.repo / ".wavefoundry/framework/source.py"
        source.write_text("new = 2\n")
        self.assertIn("framework inputs", self.assert_refused(token))
        source.write_text("old = 1\n")
        value = copy.deepcopy(self.original)
        value["recovery"]["framework_after"] = "f" * 64
        qualification.write_report(self.repo, self.path, value)
        self.assertIn("framework inputs", self.assert_refused(token))

    def test_failed_or_incomplete_workers_never_qualify(self):
        self.refused()
        self.inspect()  # The immediately adjacent unmodified report is eligible.
        mutations = [
            lambda v: v["workers"][0].update(returncode=1),
            lambda v: v["workers"][0].update(terminal=False),
            lambda v: v.update(complete=False),
            lambda v: v.update(workers=[], observed_workers=[]),
            lambda v: v.update(scope={"kind": "diagnostic", "discovered_workers": v["expected_workers"]}),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.rewrite_original(mutate)
                self.assert_refused()

    def test_strays_unverified_and_missing_evidence_refuse(self):
        self.refused()
        self.inspect()
        mutations = [
            lambda v: v["recovery"].update(strays=["state.db"]),
            lambda v: v["recovery"].update(unverified="unavailable"),
            lambda v: v.pop("recovery"),
            lambda v: v["recovery"]["changes"][self.doc.relative_to(self.repo).as_posix()].pop("before"),
            lambda v: v["recovery"].pop("before"),
            lambda v: v["recovery"].update(changes={}),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                self.rewrite_original(mutate)
                self.assert_refused()

    def test_open_gate_and_unknown_gate_change_refuse(self):
        self.gate.write_text(json.dumps({"framework_edit_allowed": {"enabled": False}, "other": {"count": 1}}))
        def opening():
            self.close_and_edit()
            self.gate.write_text(json.dumps({"framework_edit_allowed": {"enabled": True}, "other": {"count": 1}}))
        self.refused(opening)
        self.assertIn("gate change", self.assert_refused())

    def test_gate_closure_plus_numeric_to_boolean_configuration_change_refuses(self):
        def publish():
            self.close_and_edit()
            self.gate.write_text(json.dumps({"framework_edit_allowed": {"enabled": False}, "other": {"count": True}}))
        self.refused(publish)
        self.assertIn("gate change", self.assert_refused())

    def test_unknown_content_alongside_editorial_and_gate_closure_refuses(self):
        def publish():
            self.close_and_edit()
            (self.repo / "tracked.txt").write_text("unexplained code/config content\n")
        self.refused(publish)
        self.assertIn("before/after", self.assert_refused())

    def test_new_or_deleted_document_refuses(self):
        def publish():
            self.close_and_edit()
            (self.doc.parent / "new.md").write_text("new documentation")
        self.refused(publish)
        self.assertIn("added/deleted", self.assert_refused())

    def test_symlink_document_refuses(self):
        target = self.repo / "target.md"
        target.write_text("unrelated text")
        def publish():
            self.close_and_edit()
            self.doc.unlink()
            self.doc.symlink_to(target)
        self.refused(publish)
        self.assertIn("linked", self.assert_refused())

    def test_authority_carrier_changes_are_not_editorial(self):
        change = RecordTreeBuilder(self.repo).plan("1abce-bug example")
        change.write_text(change.read_text() + "\n## Requirements\n\nOriginal substantive behavior.\n")
        def publish():
            self.close_and_edit()
            change.write_text(change.read_text().replace("Original", "Different"))
        self.refused(publish)
        self.assertIn("authority", self.assert_refused())

    def test_mixed_existing_canonical_bookkeeping_keeps_classifier_tolerance(self):
        change = RecordTreeBuilder(self.repo).plan("1abce-bug example")
        change.write_text(change.read_text() + "\n## Progress Log\n\nInitial progress.\n")
        def publish():
            self.close_and_edit()
            change.write_text(change.read_text().replace("Initial progress.", "Recorded progress."))
        self.refused(publish)
        token = self.inspect()["token"]
        with patch.object(run_tests, "_bookkeeping_changes", return_value=set()):
            self.assertIn("existing classifiers", self.assert_refused(token))
        self.assertEqual(self.accept(token)[0], 0)

    def test_optional_capture_failure_does_not_fail_ordinary_green_or_issue_recovery(self):
        with patch.object(run_tests, "_capture_reconciliation", side_effect=lambda snapshot: setattr(snapshot, "capture_error", "cap")):
            code, out, err = self._main(["--no-cache"], "none", self.doc)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(json.loads(self.cache_file.read_text())["result"], "ok")
        self.assertEqual(list((self.repo / ".wavefoundry/cache/qualification").glob("refused-*")), [])

    def test_uncaptured_changed_document_and_persisted_report_cap_refuse(self):
        with patch.object(run_tests, "_RECONCILIATION_DOC_BYTES", 8):
            self.refused()
        self.assertIn("before/after", self.assert_refused())

    def test_token_and_operator_attestation_are_required(self):
        self.refused()
        token = self.inspect()["token"]
        self.assertIn("token", self.assert_refused("0" * 64))
        code, _, _ = self.cli("--reconcile", self.path, "--accept", token)
        self.assertEqual(code, 2)
        self.note = " "
        self.assertIn("attestation", self.assert_refused(token))

    def test_immutable_original_refuses_replacement_and_identical_write_is_noop(self):
        self.refused()
        qualification.write_report(self.repo, self.path, self.original, immutable=True)
        changed = dict(self.original, returncode=0)
        with self.assertRaisesRegex(ValueError, "immutable"):
            qualification.write_report(self.repo, self.path, changed, immutable=True)
        self.assertEqual((self.repo / self.path).read_bytes(), self.original_bytes)

    def test_publication_lock_serializes_normal_success_with_acceptance(self):
        self.refused()
        token = self.inspect()["token"]
        report = copy.deepcopy(self.original)
        report.pop("recovery")
        report["returncode"] = 0
        result = run_tests.FileResult("test_mutant.py", 0, "", 1, 0.1, 0)
        entered, release = threading.Event(), threading.Event()
        outcome = []
        real_write = run_tests._write_cache
        def publish(*args, **kwargs):
            if threading.current_thread() is worker:
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("publication barrier was not released")
            return real_write(*args, **kwargs)
        def normal_publication():
            outcome.append(run_tests._publish_default_success(report, report["identity"]["source_hash"], [result]))
        with patch.object(run_tests, "_LOCK_FILE", self.repo / ".wavefoundry/framework/test-run.lock"), \
                patch.object(run_tests, "_acquire_run_lock", REAL_ACQUIRE), \
                patch.object(run_tests, "_release_run_lock", REAL_RELEASE), \
                patch.object(run_tests, "_write_cache", side_effect=publish):
            worker = threading.Thread(target=normal_publication)
            worker.start()
            try:
                self.assertTrue(entered.wait(5), "normal publisher never reached receipt write")
                self.assertIn("already running", self.assert_refused(token))
            finally:
                release.set()
                worker.join(5)
            self.assertFalse(worker.is_alive())
        self.assertEqual(outcome, [0])
        self.assertIn("newer", self.assert_refused(token))

    def test_persisted_report_bound_leaves_existing_receipt_unchanged(self):
        self.cache_file.write_text('{"result":"old"}')
        before = self.cache_file.read_bytes()
        with patch.object(qualification, "MAX_BYTES", 64):
            code, out, err = self._external_main(["--no-cache"], self.close_and_edit)
        self.assertEqual(code, 1, out + err)
        self.assertIn("byte bound", err)
        self.assertEqual(self.cache_file.read_bytes(), before)
        self.assertEqual(list((self.repo / ".wavefoundry/cache/qualification").glob("refused-*")), [])

    def test_genuine_failed_worker_with_guard_changes_is_not_reconciled(self):
        worker = self.tests_dir / "test_mutant.py"
        worker.write_text(worker.read_text().replace('        elif action == "none":',
            '            self.fail("genuine worker failure")\n        elif action == "none":'))
        original = self.refused()
        self.assertEqual(original["workers"][0]["returncode"], 1)
        self.assertIn("terminal worker", self.assert_refused())


if __name__ == "__main__":
    unittest.main()

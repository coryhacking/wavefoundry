"""23n00: an unaffected readiness lane need not invent a negative control."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import review_evidence as subject
from test_review_evidence import integrity_checks
import test_review_evidence as evidence_tests
import test_server_tools_lifecycle as lifecycle_tests

RATIONALE = "Not applicable: inspected toolchain metadata and unchanged lockfile; no surface in this reviewer lane is affected."


class ReadinessKnownBadTests(unittest.TestCase):
    def event(self, **overrides):
        event = dict(event="approval", signoff_key="security-reviewer", actor="security-reviewer",
                     context_id="readiness-na", approval_phase="readiness", policy_receipt_id="receipt-test",
                     fresh_context=True, independent=True, observed="inspected unchanged security scope",
                     artifact_or_test_id=self.id(), integrity_checks=integrity_checks(
                         known_bad_detected=None, known_bad_detection_method=RATIONALE))
        event.update(overrides)
        return event

    def build(self, event):
        return subject.build_compact_review_event([], event)

    def test_explicit_null_round_trip_and_other_checks_are_true(self):
        rows, errors = self.build(self.event())
        self.assertEqual(errors, ())
        self.assertIsNone(rows[0]["known_bad_detected"])
        self.assertEqual(rows[0]["known_bad_detection_method"], RATIONALE)
        self.assertEqual(subject._validate_evidence_shape(rows[0], 0), [])
        for field in set(subject.INTEGRITY_CHECK_BOOLEAN_FIELDS) - {"known_bad_detected"}:
            self.assertIs(rows[0][field], True)

    def test_write_and_read_boundary_matrix(self):
        good, errors = self.build(self.event())
        self.assertFalse(errors)
        for key, actor, phase in (
            ("security-reviewer", "security-reviewer", "delivery"),
            ("council-readiness", subject.COUNCIL_ACTOR, "readiness"),
            ("council-delivery", subject.COUNCIL_ACTOR, "delivery"),
            ("wave-council-readiness", subject.COUNCIL_ACTOR, "readiness"),
            ("security-reviewer", "qa-reviewer", "readiness"),
            ("operator-signoff", "security-reviewer", "readiness"),
            ("council-chair", "council-chair", "readiness"),
            ("operator", "operator", "readiness"),
            ("operator-signoff", "operator-signoff", "readiness"),
            ("", "", "readiness"),
            ("wave-council-custom", "wave-council-custom", "readiness"),
        ):
            with self.subTest(key=key, actor=actor, phase=phase):
                extra = {"intent_fit": "establishes"} if subject.requires_intent_fit(key) else {}
                _, errors = self.build(self.event(signoff_key=key, actor=actor, approval_phase=phase, **extra))
                self.assertTrue(any("null (not applicable)" in e for e in errors), errors)
                record = copy.deepcopy(good[0])
                record.update(claim_id="approval:" + key, approval_phase=phase)
                record["verification_context"]["actor"] = actor
                self.assertTrue(any("`known_bad_detected` must be boolean: null (not applicable)" in e for e in subject._validate_evidence_shape(record, 0)))
        record = copy.deepcopy(good[0])
        record.pop("approval_phase")
        self.assertEqual(subject.approval_record_phase(record), "delivery")
        self.assertTrue(any("`known_bad_detected` must be boolean: null (not applicable)" in e for e in subject._validate_evidence_shape(record, 0)))
        record = copy.deepcopy(good[0])
        record.update(claim_kind="finding", required_for_approval=False)
        self.assertTrue(any("`known_bad_detected` must be boolean: null (not applicable)" in e for e in subject._validate_evidence_shape(record, 0)))
        finding = evidence_tests.ReviewEvidenceStateMachineTests._compact_integrity_finding_event(
            self, integrity_checks=integrity_checks(known_bad_detected=None))
        _, errors = self.build(finding)
        self.assertTrue(any("null (not applicable)" in e for e in errors), errors)

    def test_false_missing_and_other_null_checks_remain_refused(self):
        good, _ = self.build(self.event())
        for field in subject.INTEGRITY_CHECK_BOOLEAN_FIELDS:
            for value in (False, None):
                if field == "known_bad_detected" and value is None:
                    continue
                with self.subTest(field=field, value=value):
                    checks = dict(self.event()["integrity_checks"], **{field: value})
                    _, errors = self.build(self.event(integrity_checks=checks))
                    self.assertTrue(errors)
                    record = dict(good[0], **{field: value})
                    # Pin the executed-evidence guard independently of the type guard.
                    self.assertTrue(any("false evidence-integrity" in e for e in subject._validate_evidence_shape(record, 0)))
        checks = dict(self.event()["integrity_checks"])
        checks.pop("known_bad_detected")
        _, errors = self.build(self.event(integrity_checks=checks))
        self.assertTrue(any("missing fields: known_bad_detected" in e for e in errors), errors)
        record = dict(good[0]); record.pop("known_bad_detected")
        self.assertTrue(subject._validate_evidence_shape(record, 0))
        for reason in (None, "", "   "):
            checks = dict(self.event()["integrity_checks"], known_bad_detection_method=reason)
            _, errors = self.build(self.event(integrity_checks=checks))
            self.assertTrue(any("known_bad_detection_method" in e for e in errors), errors)
            self.assertTrue(any("known_bad_detection_method" in e for e in subject._validate_evidence_shape(
                dict(good[0], known_bad_detection_method=reason), 0)))

    def test_rationale_and_null_are_part_of_retry_identity(self):
        digest = subject.review_event_request_digest
        event = self.event()
        self.assertNotEqual(digest(event), digest(self.event(integrity_checks=integrity_checks())))
        checks = dict(event["integrity_checks"], known_bad_detection_method="Different inspected scope")
        self.assertNotEqual(digest(event), digest(self.event(integrity_checks=checks)))
        missing = dict(event["integrity_checks"]); missing.pop("known_bad_detected")
        self.assertNotEqual(digest(event), digest(self.event(integrity_checks=missing)))

    def test_schema_and_refusal_explain_applicability(self):
        schema = subject.review_action_input_schema()["integrity_checks"]
        self.assertIn("specialist-readiness-with-scope-rationale", schema["known_bad_detected"]["null_allowed_for"])
        for field in set(subject.INTEGRITY_CHECK_BOOLEAN_FIELDS) - {"known_bad_detected"}:
            self.assertEqual(schema[field]["null_allowed_for"], ["operator-signoff"])
        _, errors = self.build(self.event(integrity_checks=integrity_checks(known_bad_detected=False)))
        message = " ".join(errors)
        for phrase in ("refuted plan claim", "omitted known census site", "invalid review input", "inspected scope", "Never change false to true"):
            self.assertIn(phrase, message)


class ServedReadinessKnownBadTests(unittest.TestCase):
    """Use the existing registered-tool fixture, without inheriting its test cases."""
    setUp = lifecycle_tests.ReceiptSnapshotPublicIntegrationTests.setUp
    call = lifecycle_tests.ReceiptSnapshotPublicIntegrationTests.call
    ok = lifecycle_tests.ReceiptSnapshotPublicIntegrationTests.ok
    body = lifecycle_tests.ReceiptSnapshotPublicIntegrationTests.body
    prepare = lifecycle_tests.ReceiptSnapshotPublicIntegrationTests.prepare
    records = lifecycle_tests.ReceiptSnapshotPublicIntegrationTests.records
    receipt = lifecycle_tests.ReceiptSnapshotPublicIntegrationTests.receipt
    approve = lifecycle_tests.ReceiptSnapshotPublicIntegrationTests.approve

    def test_registered_write_read_retry_and_prepare_consume_null(self):
        args = dict(wave_id=self.wave_id, event="approval", actor="code-reviewer",
                    context_id="unaffected-code-scope", signoff_key="code-reviewer",
                    approval_phase="readiness", fresh_context=True, independent=True, mode="create",
                    evidence={"observed": "Toolchain metadata only; no code surface affected", "artifact_or_test_id": self.id()},
                    integrity_checks=integrity_checks(known_bad_detected=None, known_bad_detection_method=RATIONALE))
        self.ok(self.call("wf_review_event", **args))
        before = self.wave_md.with_name("events.jsonl").read_bytes()
        self.ok(self.call("wf_review_event", **args))
        self.assertEqual(before, self.wave_md.with_name("events.jsonl").read_bytes())
        record = next(r for r in self.records() if r.get("verification_context", {}).get("context_id") == args["context_id"])
        self.assertIsNone(record["known_bad_detected"])
        self.assertEqual(record["known_bad_detection_method"], RATIONALE)
        text = self.wave_md.read_text()
        readiness = next(line for line in text.splitlines() if line.startswith("| code-reviewer | readiness |"))
        self.assertIn("known-bad control not applicable", readiness.split("|")[4])
        self.assertIn(RATIONALE, readiness.split("|")[4])
        self.assertFalse(any(line.startswith("Readiness ") for line in text.splitlines()))
        response = self.prepare()
        self.assertEqual(response["status"], "ok", response)
        self.assertTrue(response["data"]["readied"])
        self.assertEqual(response["data"]["pending_readiness_lanes"], [])
        # Different evidence under the same identity is refused, never rewritten.
        changed = copy.deepcopy(args)
        changed["integrity_checks"]["known_bad_detection_method"] = "Changed reason"
        response = self.call("wf_review_event", **changed)
        self.assertEqual(response["status"], "error", response)


if __name__ == "__main__":
    unittest.main()

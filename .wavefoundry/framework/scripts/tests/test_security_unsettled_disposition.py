#!/usr/bin/env python3
"""An unsettled security candidate stays open until settled (wave 22upa, change 22ubf).

A real finding whose ``attacker_reachability`` or ``authority_delta`` is ``unverified``
derives ``security_unsettled``: it stays ``pending``, holds ``operator-signoff`` withheld and
is named by Review and Close until fresh evidence settles it or the operator closes it.
Every write here goes through the served ``wf_review_event`` handler; ledgers are read back
through the docs-lint wave validator.
"""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import review_evidence as subject
import vocabulary_profile
from server_tools_support import SCRIPTS_ROOT, load_server
from test_intent_fit_approvals import IntentFitWritePathTests
from test_lifecycle_golden import _APPROVAL_INTEGRITY, _stub_garden, _stub_validate
from wave_lint_lib import wave_validators

REPO_ROOT = SCRIPTS_ROOT.parents[2]
SEED_209 = SCRIPTS_ROOT.parent / "seeds" / "209-agent-harness-core.prompt.md"
ACTOR = subject.COUNCIL_ACTOR
DELIVERY = subject.COUNCIL_DELIVERY_SIGNOFF_KEY
READINESS = subject.COUNCIL_READINESS_SIGNOFF_KEY
FINDING = "sec-candidate"
TRIGGER = "promote if a public caller can reach the parser"
WAIVER = {
    "waiver_id": "waiver-sec-1",
    "waiver_scope": "this candidate only",
    "waiver_reason": "Reachability cannot be settled before release.",
    "waiver_risk": "An unverified parser path may be reachable.",
}

# One unsettled security candidate: a real finding needing no action whose attacker
# reachability is unknown.
UNSETTLED = {
    "validation_status": "real", "scope_relation": "admitted", "contract_relevance": "none",
    "authority_domain": "confidentiality", "authority_delta": "low", "observable_impact": "low",
    "containment": "preventive", "fix_risk": "higher", "optional_value": "none",
    "repair_safety": "unverified", "benefit_vs_fix_risk": "unverified",
    "rejection_basis": "insufficient_evidence", "introduced_or_worsened_by_wave": False,
    "supported_reachability": "unverified", "attacker_reachability": "unverified",
    "repair_scope_bounded": "unverified",
}


def judgment(**changes: object) -> dict:
    return {**UNSETTLED, **changes}


def finding_evidence(**extra: object) -> dict:
    fields = subject.REVIEW_FINDING_REQUIRED_EVIDENCE_FIELDS
    evidence = {field: f"fixture {field}" for field in fields}
    evidence.update(known_bad_detection_method="fixture known-bad", **extra)
    return evidence


def record_disposition(record: dict) -> tuple[str, str]:
    return record["disposition"], record["repair_execution_state"]


class _ServedLedger(unittest.TestCase):
    CONFIG = IntentFitWritePathTests.CONFIG
    _readied = IntentFitWritePathTests._readied
    _event = IntentFitWritePathTests._event
    _approve = IntentFitWritePathTests._approve
    _ledger = IntentFitWritePathTests._ledger

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        for name, value in (("run_validate", _stub_validate), ("run_garden", _stub_garden),
                            ("_run_post_write_lint", lambda *a, **k: {"mode": "stubbed"})):
            patcher = patch.object(self.srv, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    # -- writers ----------------------------------------------------------

    def _finding(self, root, wave_id, *, run_kind, cycle, actor, context, judgment_value,
                 trigger=TRIGGER, fresh=True, finding_id=FINDING, mode="create", **lanes):
        extra = {"promotion_trigger": trigger} if trigger else {}
        return self.srv.wf_review_event_response(
            root, wave_id, "finding", actor, context, mode=mode, finding_id=finding_id,
            run_kind=run_kind, cycle=cycle, judgment=judgment_value,
            evidence=finding_evidence(**extra),
            source_lanes=lanes.get("source_lanes", ["code-reviewer"]),
            blocking_required_lanes=lanes.get("blocking_required_lanes", []),
            approval_recheck_lanes=lanes.get("approval_recheck_lanes", []),
            fresh_context=fresh, independent=fresh, integrity_checks=dict(_APPROVAL_INTEGRITY))

    def _operator_close(self, root, wave_id, *, cycle, actor="operator", waiver=WAIVER,
                        mode="create", context="operator-close", **kwargs):
        evidence = {"observed": "operator closes the candidate by name",
                    "artifact_or_test_id": "operator decision"}
        if waiver is not None:
            evidence["waiver"] = dict(waiver)
        return self.srv.wf_review_event_response(
            root, wave_id, "finding", actor, context, mode=mode, finding_id=FINDING,
            run_kind="reverification", cycle=cycle, evidence=evidence, **kwargs)

    def _head(self, wave_md, finding_id=FINDING):
        return subject.current_synthesis_heads(self._ledger(wave_md))[finding_id]

    def _assert_ok(self, response):
        self.assertEqual(response["status"], "ok", response)

    def _assert_refused(self, response, wave_md, needle):
        before = subject.review_event_path(wave_md).read_bytes()
        self.assertEqual(response["status"], "error", response)
        message = " ".join(d.get("message", "") for d in response["diagnostics"])
        self.assertIn(needle, message)
        self.assertEqual(subject.review_event_path(wave_md).read_bytes(), before)

    # -- wave states ------------------------------------------------------

    def _readiness_wave(self, name):
        root, wave_md, wave_id = self._readied(name)
        self._assert_ok(self._event(root, wave_id, "run", ACTOR, "readiness-run",
                                    {"observed": "run", "artifact_or_test_id": "run"},
                                    mode="create", run_kind="readiness"))
        return root, wave_md, wave_id

    def _delivered(self, name):
        """Every required signoff approved, operator-signoff included, current receipt."""
        root, wave_md, wave_id = self._readied(name, status="active",
                                               approvals=(READINESS, "code-reviewer"))
        evidence = {"observed": "delivery fixture", "artifact_or_test_id": "test:22ubf"}
        self._assert_ok(self._event(root, wave_id, "run", ACTOR, "delivery-run", evidence,
                                    mode="create", run_kind="initial_delivery"))
        self._assert_ok(self._approve(root, wave_id, "code-reviewer", "delivery", evidence,
                                      actor="code-reviewer"))
        self._assert_ok(self._approve(root, wave_id, DELIVERY, "delivery",
                                      {**evidence, "intent_fit": "establishes"}))
        self._approve_operator(root, wave_id, "operator-approval")
        label = vocabulary_profile.MEMBER_STATUS_LABEL
        for doc in wave_md.parent.glob("*.md"):
            text = doc.read_text(encoding="utf-8")
            doc.write_text(text.replace(f"{label}: `planned`", f"{label}: `complete`", 1),
                           encoding="utf-8")
        return root, wave_md, wave_id

    def _approve_operator(self, root, wave_id, context):
        self._assert_ok(self.srv.wf_review_event_response(
            root, wave_id, "approval", "operator", context, mode="create",
            signoff_key="operator-signoff", approval_phase="delivery",
            evidence={"observed": "operator approves", "artifact_or_test_id": "operator"}))

    def _unsettled(self, name):
        root, wave_md, wave_id = self._delivered(name)
        self._assert_ok(self._finding(root, wave_id, run_kind="initial_delivery", cycle=0,
                                      actor="code-reviewer", context="sec-initial",
                                      judgment_value=judgment()))
        return root, wave_md, wave_id

    # -- readers ----------------------------------------------------------

    def _close_dry_run(self, root, wave_id):
        with patch.object(self.srv, "_framework_test_receipt_diagnostic", lambda *a, **k: None,
                          create=True), \
             patch.object(self.srv, "_auto_populate_memory_for_wave", lambda *a, **k: None), \
             patch.object(self.srv, "_maybe_optimize_index_on_close", lambda *a, **k: None):
            return self.srv.wf_close_wave_response(root, wave_id, mode="dry_run")

    def _review(self, root, wave_id):
        return self.srv.wf_review_wave_response(root, wave_id, phase="implementation")

    @staticmethod
    def _codes(response):
        return [d["code"] for d in response.get("diagnostics", [])]

    def _rows(self, wave_md):
        records = self._ledger(wave_md)
        keys = subject.review_status_signoff_keys(
            records, ("operator-signoff", "code-reviewer", DELIVERY, READINESS))
        return {row["signoff_key"]: row for row in subject.review_status_rows(records, keys)}

    def _assert_lints(self, root):
        failures = [f for f in wave_validators.check_wave_docs(root) if "review evidence" in f]
        self.assertEqual(failures, [])


class DerivationTests(_ServedLedger):
    """AC-1 and AC-4: the trigger is the facts, through the served tool."""

    CASES = {
        "reach-insufficient": judgment(),
        "reach-categorical": judgment(rejection_basis="categorical"),
        "reach-disproportionate": judgment(rejection_basis="disproportionate_repair"),
        "delta-insufficient": judgment(attacker_reachability=False, authority_delta="unverified"),
    }
    UNCHANGED = {
        "correctness": judgment(attacker_reachability=False, authority_delta="none",
                                observable_impact="unverified"),
        "shown-unreachable": judgment(rejection_basis="unsupported_reachability",
                                      supported_reachability=False),
        "integrity-domain": judgment(attacker_reachability=False, authority_delta="none",
                                     authority_domain="integrity"),
    }

    def test_an_unknown_security_factor_derives_security_unsettled_whatever_the_basis(self):
        root, wave_md, wave_id = self._readiness_wave("derive")
        for finding_id, value in self.CASES.items():
            with self.subTest(finding_id=finding_id):
                trigger = None if value["rejection_basis"] == "categorical" else TRIGGER
                self._assert_ok(self._finding(root, wave_id, run_kind="readiness", cycle=0,
                                              actor="code-reviewer", context=f"ctx-{finding_id}",
                                              judgment_value=value, trigger=trigger,
                                              finding_id=finding_id))
                head = self._head(wave_md, finding_id)
                self.assertEqual(record_disposition(head), ("security_unsettled", "pending"))
                self.assertFalse(head["blocking"])
                self.assertEqual(head["review_depth"], "focused")

    def test_correctness_unknowns_and_settled_factors_derive_as_before(self):
        root, wave_md, wave_id = self._readiness_wave("unchanged")
        for finding_id, value in self.UNCHANGED.items():
            with self.subTest(finding_id=finding_id):
                self._assert_ok(self._finding(root, wave_id, run_kind="readiness", cycle=0,
                                              actor="code-reviewer", context=f"ctx-{finding_id}",
                                              judgment_value=value, finding_id=finding_id))
                self.assertEqual(record_disposition(self._head(wave_md, finding_id)),
                                 ("dont_do_later", "not_required"))

    def test_action_required_keeps_precedence(self):
        self.assertEqual(subject.derive_disposition(judgment(contract_relevance="required_ac",
                                                             rejection_basis="none")), "do_now")

    def test_the_new_branch_sits_after_do_now_and_before_maybe_later(self):
        maybe = judgment(attacker_reachability=False, authority_delta="none", optional_value="positive",
                         repair_scope_bounded=True, repair_safety="safe", benefit_vs_fix_risk="greater",
                         rejection_basis="none")
        self.assertEqual(subject.derive_disposition(maybe), "maybe_later")
        self.assertEqual(subject.derive_disposition({**maybe, "attacker_reachability": "unverified"}),
                         "security_unsettled")


class HoldsSignoffTests(_ServedLedger):
    """AC-2: it holds operator-signoff withheld, and only that."""

    def test_an_unsettled_candidate_withholds_operator_signoff_and_blocks_close(self):
        root, wave_md, wave_id = self._delivered("hold")
        before_rows = self._rows(wave_md)
        self.assertEqual(before_rows["operator-signoff"]["state"], "approved")
        before = self._close_dry_run(root, wave_id)
        self.assertNotIn("unsettled_security_candidate", self._codes(before))
        self.assertEqual(before["status"], "dry_run", before)

        self._assert_ok(self._finding(root, wave_id, run_kind="initial_delivery", cycle=0,
                                      actor="code-reviewer", context="sec-initial",
                                      judgment_value=judgment()))
        rows = self._rows(wave_md)
        operator = rows["operator-signoff"]
        self.assertEqual(operator["state"], "withheld")
        self.assertIn(FINDING, operator["why"])
        self.assertIn(TRIGGER, operator["why"])
        self.assertEqual(operator["next_action"], subject.UNSETTLED_SECURITY_NEXT_ACTION)
        self.assertNotRegex(operator["next_action"], r"wf_|record ")
        for key, row in before_rows.items():
            if key != "operator-signoff":
                self.assertEqual(rows[key], row, key)
        projection = subject.review_authority_projection(
            self._ledger(wave_md), list(rows), approval_phase="delivery")
        self.assertNotIn("approval:operator-signoff",
                         [action["action_id"] for action in projection["next_actions"]])
        after = self._close_dry_run(root, wave_id)
        self.assertEqual(after["status"], "error", after)
        unsettled = [d for d in after["diagnostics"] if d["code"] == "unsettled_security_candidate"]
        self.assertEqual(len(unsettled), 1, after)
        self.assertIn(FINDING, unsettled[0]["message"])
        self.assertIn("unsettled_security_candidate", self._codes(self._review(root, wave_id)))

    def test_close_change_refuses_while_one_is_open(self):
        root, wave_md, wave_id = self._unsettled("close-change")
        change_id = next(p.stem for p in wave_md.parent.glob("*.md") if p != wave_md)
        response = self.srv.wf_close_change_response(root, wave_id, change_id, mode="dry_run")
        self.assertIn("unsettled_security_candidate", self._codes(response), response)


class SettlingTests(_ServedLedger):
    """AC-3: each settling path makes the wave closable; the refusals hold."""

    def _repair_start(self, root, wave_id, cycle=1):
        self._assert_ok(self._finding(root, wave_id, run_kind="repair_start", cycle=cycle,
                                      actor="implementer", context=f"repair-{cycle}",
                                      judgment_value=judgment()))

    def _reverify(self, root, wave_id, value, *, context, cycle=1, trigger=None, fresh=True,
                  actor="qa-reviewer"):
        return self._finding(root, wave_id, run_kind="reverification", cycle=cycle, actor=actor,
                             context=context, judgment_value=value, trigger=trigger, fresh=fresh)

    def _assert_closable(self, root, wave_id):
        response = self._close_dry_run(root, wave_id)
        self.assertEqual(response["status"], "dry_run", response)
        self.assertNotIn("unsettled_security_candidate", self._codes(response))
        self._assert_lints(root)
        return response

    def test_a_not_issue_reverification_settles_it(self):
        root, wave_md, wave_id = self._unsettled("not-issue")
        self._repair_start(root, wave_id)
        self._assert_ok(self._reverify(root, wave_id, judgment(validation_status="invalid"),
                                       context="reverify-not-issue"))
        self.assertEqual(record_disposition(self._head(wave_md)), ("not_issue", "not_required"))
        self._assert_closable(root, wave_id)

    def test_a_dont_do_later_reverification_on_settled_factors_settles_it(self):
        root, wave_md, wave_id = self._unsettled("dont-do-later")
        self._repair_start(root, wave_id)
        settled = judgment(attacker_reachability=False, authority_delta="none",
                           supported_reachability=False, rejection_basis="categorical")
        self._assert_ok(self._reverify(root, wave_id, settled, context="reverify-ddl"))
        self.assertEqual(record_disposition(self._head(wave_md)), ("dont_do_later", "not_required"))
        self._assert_closable(root, wave_id)

    def test_a_do_now_reverification_follows_the_normal_repair_chain(self):
        root, wave_md, wave_id = self._unsettled("do-now")
        self._repair_start(root, wave_id)
        do_now = judgment(attacker_reachability=True, authority_delta="material",
                          supported_reachability=True, containment="none", rejection_basis="none")
        self._assert_ok(self._reverify(root, wave_id, do_now, context="reverify-do-now"))
        self.assertEqual(record_disposition(self._head(wave_md)), ("do_now", "pending"))
        self.assertEqual(self._close_dry_run(root, wave_id)["status"], "error")
        self._assert_ok(self._reverify(root, wave_id, do_now, context="reverify-repaired",
                                       actor="code-reviewer"))
        self.assertEqual(record_disposition(self._head(wave_md)), ("do_now", "completed"))
        # The repair stales the approvals that predate it; fresh approvals restore them.
        evidence = {"observed": "re-approved after repair", "artifact_or_test_id": "test:22ubf"}
        self._assert_ok(self._approve(root, wave_id, "code-reviewer", "delivery", evidence,
                                      actor="code-reviewer", context="code-reviewer-again"))
        self._assert_ok(self._approve(root, wave_id, DELIVERY, "delivery",
                                      {**evidence, "intent_fit": "establishes"},
                                      context="council-again"))
        self._approve_operator(root, wave_id, "operator-again")
        self._assert_closable(root, wave_id)

    def test_the_operator_close_settles_it_with_attribution(self):
        root, wave_md, wave_id = self._unsettled("operator-close")
        (root / "docs" / "contributors.json").write_text(json.dumps(
            {"op-handle": {"name": "Operator", "emails": ["op@example.invalid"]}}), encoding="utf-8")
        self._assert_ok(self._operator_close(root, wave_id, cycle=1, operator_handle="op-handle"))
        head = self._head(wave_md)
        self.assertEqual(record_disposition(head), ("security_unsettled", "operator_waived"))
        self.assertEqual(head["decision_authority"], "operator")
        self.assertEqual(head["promotion_trigger"], TRIGGER)
        for field, value in WAIVER.items():
            self.assertEqual(head[field], value)
        records = self._ledger(wave_md)
        evidence = next(r for r in records if r.get("evidence_record_id") == head["evidence_record_id"])
        context = evidence["verification_context"]
        self.assertEqual(context["actor"], "operator")
        self.assertEqual(context["operator"], {"handle": "op-handle", "source": "explicit"})
        self.assertIsNone(evidence["known_bad_detected"])
        response = self._assert_closable(root, wave_id)
        waived = [d for d in response["diagnostics"] if d["code"] == "security_candidate_waived"]
        self.assertEqual(len(waived), 1, response)
        self.assertTrue(waived[0]["advisory"])
        self.assertIn(WAIVER["waiver_reason"], waived[0]["message"])
        self.assertIn("op-handle", waived[0]["message"])

    def test_a_still_unsettled_reverification_stays_pending_then_the_operator_closes_that_cycle(self):
        root, wave_md, wave_id = self._unsettled("still-unsettled")
        self._repair_start(root, wave_id)
        self._assert_ok(self._reverify(root, wave_id, judgment(), context="reverify-unknown",
                                       trigger=TRIGGER))
        self.assertEqual(record_disposition(self._head(wave_md)), ("security_unsettled", "pending"))
        self.assertEqual(self._rows(wave_md)["operator-signoff"]["state"], "withheld")
        wrong_cycle = self._operator_close(root, wave_id, cycle=2, mode="dry_run")
        self._assert_refused(wrong_cycle, wave_md, "cycle 1")
        self._assert_ok(self._operator_close(root, wave_id, cycle=1))
        self.assertEqual(subject._guided_repair_cycle(self._ledger(wave_md)), 2)
        # Another finding's repair cycle then opens at cycle 2, and the ledger lints.
        other = judgment(contract_relevance="required_ac", rejection_basis="none",
                         attacker_reachability=False, authority_delta="none")
        self._assert_ok(self._finding(root, wave_id, run_kind="initial_delivery", cycle=0,
                                      actor="code-reviewer", context="other-initial",
                                      judgment_value=other, trigger=None, finding_id="other"))
        self._assert_ok(self._finding(root, wave_id, run_kind="repair_start", cycle=2,
                                      actor="implementer", context="other-repair",
                                      judgment_value=other, trigger=None, finding_id="other"))
        self._assert_lints(root)

    def test_the_refusals(self):
        root, wave_md, wave_id = self._unsettled("refusals")
        self._repair_start(root, wave_id)
        stale = self._reverify(root, wave_id, judgment(validation_status="invalid"),
                               context="reverify-stale", fresh=False)
        self._assert_refused(stale, wave_md, "fresh_context=true")
        self._assert_refused(self._operator_close(root, wave_id, cycle=1, actor="qa-reviewer"),
                             wave_md, "requires actor `operator`")
        partial = {key: value for key, value in WAIVER.items() if key != "waiver_risk"}
        self._assert_refused(self._operator_close(root, wave_id, cycle=1, waiver=partial),
                             wave_md, "waiver_risk")
        self._assert_refused(self._operator_close(root, wave_id, cycle=1, waiver=None),
                             wave_md, "requires a `waiver` object")
        # On a head that is not security_unsettled.
        other = judgment(attacker_reachability=False, authority_delta="none",
                         rejection_basis="categorical")
        self._assert_ok(self._finding(root, wave_id, run_kind="initial_delivery", cycle=0,
                                      actor="code-reviewer", context="settled-initial",
                                      judgment_value=other, trigger=None, finding_id="settled"))
        response = self.srv.wf_review_event_response(
            root, wave_id, "finding", "operator", "operator-settled", mode="create",
            finding_id="settled", run_kind="reverification", cycle=1,
            evidence={"observed": "x", "artifact_or_test_id": "y", "waiver": dict(WAIVER)})
        self._assert_refused(response, wave_md, "applies only to a current security_unsettled head")

    def test_a_hand_written_operator_waived_head_without_operator_evidence_fails(self):
        root, wave_md, wave_id = self._unsettled("hand-written")
        records = list(self._ledger(wave_md))
        head = dict(subject.current_synthesis_heads(records)[FINDING])
        head.update(repair_execution_state="operator_waived", decision_authority="operator", **WAIVER)
        records[records.index(subject.current_synthesis_heads(records)[FINDING])] = head
        errors = subject.validate_review_evidence_records(records)
        self.assertTrue(any("requires linked evidence whose verification_context.actor is `operator`"
                            in error for error in errors), errors)


class CompatibilityTests(_ServedLedger):
    """AC-5: existing ledgers keep validating; closed waves are not re-derived."""

    def test_every_repository_ledger_lints_and_every_summary_line_re_renders(self):
        failures = [f for f in wave_validators.check_wave_docs(REPO_ROOT) if "review evidence" in f]
        self.assertEqual(failures, [])
        for ledger in sorted(REPO_ROOT.glob(f"docs/**/{subject.EVENTS_FILENAME}")):
            rows, errors = subject.parse_review_event_bytes(ledger.read_bytes())
            self.assertEqual(errors, (), ledger)
            line = subject.review_evidence_summary_line(rows)
            self.assertNotIn("security_unsettled", line, ledger)
            wave_text = (ledger.parent / vocabulary_profile.RECORD_FILENAME).read_text(encoding="utf-8")
            if "Machine review state" in wave_text:
                self.assertIn(line, wave_text, ledger)

    def test_the_summary_line_appends_the_fifth_count_only_when_non_zero(self):
        head = {"record_type": "finding_synthesis", "finding_id": "x", "disposition": "security_unsettled"}
        self.assertTrue(subject.review_evidence_summary_line([head]).endswith(", security_unsettled 1"))
        self.assertEqual(subject.review_evidence_summary_line([]),
                         "Machine review state — 0 findings; current: do_now 0, maybe_later 0, "
                         "dont_do_later 0, not_issue 0")

    def _old_rule_records(self, name):
        """A wave holding a `dont_do_later` head written before the rule existed."""
        root, wave_md, wave_id = self._unsettled(name)
        records = [dict(r) for r in self._ledger(wave_md)]
        for record in records:
            if record.get("record_type") == "finding_synthesis" and record["finding_id"] == FINDING:
                record.update(disposition="dont_do_later", repair_execution_state="not_required",
                              review_depth="none")
        return root, wave_md, wave_id, records

    def _write_ledger(self, root, wave_md, records):
        subject.review_event_path(wave_md).write_bytes(subject.canonical_review_events_bytes(records))
        text = wave_md.read_text(encoding="utf-8")
        text = subject.render_review_evidence_projection(text, records)
        if not re.search(r"(?mi)^Status:\s*closed\s*$", text):
            text = subject.render_review_status_projection(
                text, records, subject.required_review_status_keys(root, text, records))
        wave_md.write_text(text, encoding="utf-8")

    def _close_record(self, wave_md):
        text = wave_md.read_text(encoding="utf-8")
        wave_md.write_text(re.sub(r"(?m)^Status: \w+", "Status: closed", text, count=1), encoding="utf-8")

    def test_a_closed_wave_keeps_its_recorded_dispositions(self):
        root, wave_md, _wave_id, records = self._old_rule_records("closed-old")
        self._close_record(wave_md)
        self._write_ledger(root, wave_md, records)
        self.assertEqual(subject.validate_review_evidence_records(records, closed=True), ())
        self._assert_lints(root)
        import dashboard_lib
        state = dashboard_lib._review_evidence_dashboard_state(root, wave_md, wave_md.read_text("utf-8"))
        self.assertEqual(state["integrity"], "ok", state)

    def _maybe_later_head(self, name):
        """A served `maybe_later` head, returned with the ledger records for hand edits."""
        root, wave_md, wave_id = self._delivered(name)
        maybe = judgment(optional_value="positive", repair_scope_bounded=True, repair_safety="safe",
                         benefit_vs_fix_risk="greater", rejection_basis="none",
                         attacker_reachability=False)
        self._assert_ok(self._finding(root, wave_id, run_kind="initial_delivery", cycle=0,
                                      actor="code-reviewer", context="maybe-initial",
                                      judgment_value=maybe, trigger=None))
        records = [dict(r) for r in self._ledger(wave_md)]
        head = subject.current_synthesis_heads(records)[FINDING]
        self.assertEqual(record_disposition(head), ("maybe_later", "pending"))
        return root, wave_md, wave_id, records, head

    def _list_errors(self, root, wave_id):
        response = self.srv.wf_review_event_response(root, wave_id, "list", "coordinator", "list")
        return [d for d in response["diagnostics"] if d["code"] == "review_evidence_invalid"]

    def test_without_the_closed_flag_a_recorded_disposition_is_re_derived(self):
        # Known-bad for the closed flag: a stored disposition the current rules no longer
        # derive (here `optional_value` no longer supports `maybe_later`, as a later rule
        # change would leave it) stays valid as written only in a closed wave.
        root, wave_md, wave_id, records, head = self._maybe_later_head("closed-flag")
        head["optional_value"] = "none"
        self._close_record(wave_md)
        self._write_ledger(root, wave_md, records)
        self.assertEqual(subject.validate_review_evidence_records(records, closed=True), ())
        self._assert_lints(root)
        import dashboard_lib
        state = dashboard_lib._review_evidence_dashboard_state(root, wave_md, wave_md.read_text("utf-8"))
        self.assertEqual(state["integrity"], "ok", state)
        # The server read paths (list, wave resource, projection) judge it the same way.
        self.assertEqual(self._list_errors(root, wave_id), [])
        validation = self.srv._validate_review_evidence_as_recorded(wave_md, wave_md.read_text("utf-8"))
        self.assertEqual(validation.errors, ())
        errors = subject.validate_review_evidence_records(records)
        self.assertTrue(any("disposition must be derived as `dont_do_later`" in e for e in errors), errors)

    def test_the_read_paths_fall_back_when_the_loaded_validator_has_no_closed_flag(self):
        root, wave_md, _wave_id, records, head = self._maybe_later_head("reload-window")
        self._close_record(wave_md)
        self._write_ledger(root, wave_md, records)
        calls = []

        def old_validator(path, *, closure=False, wave_text=None):
            calls.append(path)
            return subject.validate_external_review_evidence(path)

        with patch.object(self.srv, "validate_external_review_evidence", old_validator):
            self.srv._validate_review_evidence_as_recorded(wave_md)
        self.assertEqual(calls, [wave_md])

    def test_an_open_wave_accepts_a_pre_rule_maybe_later_and_keeps_writing(self):
        # Before 22ubf this record derived `maybe_later`; it now derives
        # `security_unsettled`. An open wave accepts it as written, reports the advisory
        # naming its recorded disposition, and later writes still succeed.
        root, wave_md, wave_id, records, head = self._maybe_later_head("open-maybe")
        for record in records:
            if record.get("record_type") == "finding_synthesis" and record["finding_id"] == FINDING:
                record["attacker_reachability"] = "unverified"
        self.assertEqual(subject.derive_disposition(head), subject.SECURITY_UNSETTLED)
        self._write_ledger(root, wave_md, records)
        self.assertEqual(subject.validate_review_evidence_records(records), ())
        self._assert_lints(root)
        self.assertEqual(self._list_errors(root, wave_id), [])
        self._assert_ok(self._finding(root, wave_id, run_kind="initial_delivery", cycle=0,
                                      actor="code-reviewer", context="later-write",
                                      finding_id="later-finding",
                                      judgment_value=judgment(attacker_reachability=False,
                                                              supported_reachability=False,
                                                              rejection_basis="categorical"),
                                      trigger=None))
        response = self._close_dry_run(root, wave_id)
        self.assertNotIn("review_evidence_invalid", self._codes(response), response)
        advisories = [d for d in response["diagnostics"] if d["code"] == "security_candidate_predates_rule"]
        self.assertEqual(len(advisories), 1, response)
        self.assertIn("`maybe_later`", advisories[0]["message"])

    def test_a_closed_wave_with_a_waived_head_and_superseded_unsettled_record_validates(self):
        root, wave_md, wave_id = self._unsettled("closed-waived")
        self._assert_ok(self._operator_close(root, wave_id, cycle=1))
        records = self._ledger(wave_md)
        self.assertEqual(subject.validate_review_evidence_records(records, closed=True), ())
        self.assertEqual(subject.validate_review_evidence_records(records), ())

    def test_an_open_wave_accepts_a_pre_rule_head_with_one_advisory(self):
        root, wave_md, wave_id, records = self._old_rule_records("open-old")
        self._write_ledger(root, wave_md, records)
        self.assertEqual(subject.validate_review_evidence_records(records), ())
        self._assert_lints(root)
        self.assertEqual(self._rows(wave_md)["operator-signoff"]["state"], "approved")
        response = self._close_dry_run(root, wave_id)
        advisories = [d for d in response["diagnostics"] if d["code"] == "security_candidate_predates_rule"]
        self.assertEqual(len(advisories), 1, response)
        self.assertTrue(advisories[0]["advisory"])
        self.assertIn(TRIGGER, advisories[0]["message"])
        self.assertEqual(response["status"], "dry_run", response)


class SurfaceCensusTests(unittest.TestCase):
    """AC-6: every surface naming three of the four older dispositions names the fifth."""

    OLD = ("do_now", "maybe_later", "dont_do_later", "not_issue")
    ROOTS = (".wavefoundry/framework", "docs/specs", "docs/contributing", "docs/agents", "docs/prompts")
    SUFFIXES = {".md", ".py", ".json"}
    # Requirement 8: these surfaces must each be found by the census.
    REQUIRED = (
        ".wavefoundry/framework/seeds/209-agent-harness-core.prompt.md",
        ".wavefoundry/framework/install/lifecycle-prompts/review-wave.prompt.md",
        "docs/contributing/review-and-evals.md",
        "docs/specs/mcp-tool-surface.md",
        "docs/agents/qa-reviewer.md",
        "docs/agents/specialists/council-chair.md",
        ".wavefoundry/framework/scripts/review_evidence.py",
    )
    REQUIRED_SEEDS = ("007", "211", "212", "215", "217", "221", "225", "236", "237", "239")

    def _census(self):
        found = []
        for base in self.ROOTS:
            for path in sorted((REPO_ROOT / base).rglob("*")):
                rel = path.relative_to(REPO_ROOT).as_posix()
                if (not path.is_file() or path.suffix not in self.SUFFIXES
                        or "/tests/" in f"/{rel}" or "__pycache__" in rel):
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if sum(name in text for name in self.OLD) >= 3:
                    found.append((rel, text))
        return found

    def test_every_census_surface_names_security_unsettled(self):
        found = self._census()
        missing = [rel for rel, text in found if "security_unsettled" not in text]
        self.assertEqual(missing, [])
        # Every requirement-8 surface names the fifth disposition, whether or not it
        # names three of the four older ones.
        for rel in self.REQUIRED:
            self.assertIn("security_unsettled", (REPO_ROOT / rel).read_text(encoding="utf-8"), rel)
        for number in self.REQUIRED_SEEDS:
            [seed] = sorted((REPO_ROOT / ".wavefoundry/framework/seeds").glob(f"{number}-*.md"))
            self.assertIn("security_unsettled", seed.read_text(encoding="utf-8"), seed.name)

    def test_the_operator_close_explicit_instruction_rule_is_stated(self):
        rule = "explicit instruction in the current request"
        seed = " ".join(SEED_209.read_text(encoding="utf-8").split())
        self.assertIn(rule, seed)
        schema = subject.review_action_input_schema()["evidence"]["finding"]["conditional_fields"]
        self.assertIn(rule, schema["waiver"]["meaning"])
        source = (SCRIPTS_ROOT / "wf_server" / "server_impl.py").read_text(encoding="utf-8")
        handler = source[source.index("    def wf_review_event("):]
        handler = " ".join(handler[:handler.index('"""', handler.index('"""') + 3)].split())
        self.assertIn(rule, handler)


if __name__ == "__main__":
    unittest.main()

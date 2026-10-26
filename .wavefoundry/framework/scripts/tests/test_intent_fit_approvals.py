"""Wave 21j63 (change 21kk5): council approvals carry the intent verdict.

AC-1 and AC-3 run the registered write path (``wf_review_event_response``),
AC-2 the ledger validator, AC-4 the surfaces a caller reads before writing,
and AC-8 the Review and Close evaluators.
"""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import lifecycle_gate_support
import record_paths
import review_evidence as subject
import vocabulary_profile
from server_tools_support import load_server
from test_lifecycle_golden import (
    _APPROVAL_INTEGRITY,
    _WAVE_REVIEW_CONFIG,
    _build_one,
    _make_repo,
    _stub_garden,
    _stub_validate,
    _write_config,
    capture,
    seed_state,
)
from test_review_evidence import executable_evidence

READINESS = subject.COUNCIL_READINESS_SIGNOFF_KEY
DELIVERY = subject.COUNCIL_DELIVERY_SIGNOFF_KEY
OLD_READINESS = subject.legacy_signoff_key_spellings(READINESS)[0]
CUSTOM_COUNCIL_KEY = subject._LEGACY_COUNCIL_KEY_PREFIX + "x"
ACTOR = subject.COUNCIL_ACTOR
ADVISORY = "delivery_intent_not_established"
REPO_ROOT = Path(__file__).resolve().parents[4]


def _evidence(**extra: object) -> dict[str, object]:
    return {"observed": "intent fixture", "artifact_or_test_id": "test:intent-fit", **extra}


class IntentFitWritePathTests(unittest.TestCase):
    CONFIG = {**_WAVE_REVIEW_CONFIG, "wave_review": {"enabled": True, "delivery_mode": "universal"}}

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

    def _event(self, root, wave_id, event, actor, context_id, evidence, **kwargs):
        return self.srv.wf_review_event_response(
            root, wave_id, event, actor, context_id,
            fresh_context=True, independent=True, evidence=evidence,
            integrity_checks=dict(_APPROVAL_INTEGRITY), **kwargs)

    def _approve(self, root, wave_id, key, phase, evidence, *, actor=ACTOR, mode="create", context=None):
        return self._event(root, wave_id, "approval", actor, context or f"{key}-{phase}-{mode}",
                           evidence, mode=mode, signoff_key=key, approval_phase=phase)

    def _readied(self, name, *, status="planned", approvals=()):
        root = _make_repo(self.base / name)
        _write_config(root, self.CONFIG)
        wave_md, wave_id = _build_one(self.srv, root, name, status=status)
        label = vocabulary_profile.MEMBER_STATUS_LABEL
        doc = next(path for path in wave_md.parent.glob("*.md") if path != wave_md)
        title, rest = doc.read_text(encoding="utf-8").split("\n", 1)
        doc.write_text(f"{title}\n\n{label}: `planned`\n{rest}", encoding="utf-8")
        seed_state(self.srv, root, wave_id, approvals)
        return root, wave_md, wave_id

    def _with_readiness_run(self, name):
        root, wave_md, wave_id = self._readied(name)
        run = self._event(root, wave_id, "run", ACTOR, "readiness-run", _evidence(),
                          mode="create", run_kind="readiness")
        self.assertEqual(run["status"], "ok", run)
        return root, wave_md, wave_id

    def _assert_refused(self, response, wave_md, before, needle):
        self.assertEqual(response["status"], "error", response)
        message = " ".join(d["message"] for d in response["diagnostics"])
        self.assertIn(needle, message)
        self.assertEqual(subject.review_event_path(wave_md).read_bytes(), before)

    def _ledger(self, wave_md):
        records, errors = subject.read_review_event_ledger(wave_md)
        self.assertEqual(errors, ())
        return records

    # AC-1 ---------------------------------------------------------------

    def test_readiness_council_approval_requires_an_approvable_intent_verdict(self):
        root, wave_md, wave_id = self._with_readiness_run("readiness")
        before = subject.review_event_path(wave_md).read_bytes()
        for key in (READINESS, OLD_READINESS):
            with self.subTest(key=key):
                missing = self._approve(root, wave_id, key, "readiness", _evidence(),
                                        context=f"missing-{key}")
                self._assert_refused(missing, wave_md, before, "requires evidence `intent_fit`")
        not_established = self._approve(root, wave_id, READINESS, "readiness",
                                        _evidence(intent_fit="does_not"), context="does-not")
        self._assert_refused(not_established, wave_md, before, "record a finding instead")
        for key in (READINESS, OLD_READINESS):
            with self.subTest(key=key):
                accepted = self._approve(root, wave_id, key, "readiness",
                                         _evidence(intent_fit="partially"), context=f"partially-{key}")
                self.assertEqual(accepted["status"], "ok", accepted)
        approvals = [r for r in self._ledger(wave_md) if r.get("claim_kind") == "approval"]
        self.assertEqual([r.get("intent_fit") for r in approvals], ["partially", "partially"])
        self.assertEqual({r["claim_id"] for r in approvals}, {f"approval:{READINESS}"})

    def test_delivery_council_approval_accepts_does_not_but_never_a_missing_verdict(self):
        root, wave_md, wave_id = self._readied("delivery", status="active",
                                               approvals=(READINESS, "code-reviewer"))
        run = self._event(root, wave_id, "run", ACTOR, "delivery-run", _evidence(),
                          mode="create", run_kind="initial_delivery")
        self.assertEqual(run["status"], "ok", run)
        before = subject.review_event_path(wave_md).read_bytes()
        missing = self._approve(root, wave_id, DELIVERY, "delivery", _evidence(), context="missing")
        self._assert_refused(missing, wave_md, before, "requires evidence `intent_fit`")
        partial = self._approve(root, wave_id, DELIVERY, "delivery",
                                _evidence(intent_fit="partially"), context="partially")
        self.assertEqual(partial["status"], "ok", partial)
        rows = subject._approval_rows(self._ledger(wave_md), approval_phase="delivery")
        self.assertEqual(rows[f"approval:{DELIVERY}"][1]["intent_fit"], "partially")
        accepted = self._approve(root, wave_id, DELIVERY, "delivery",
                                 _evidence(intent_fit="does_not"), context="does-not")
        self.assertEqual(accepted["status"], "ok", accepted)
        rows = subject._approval_rows(self._ledger(wave_md), approval_phase="delivery")
        self.assertEqual(rows[f"approval:{DELIVERY}"][1]["intent_fit"], "does_not")

    def test_retry_of_an_approval_recorded_before_the_verdict_existed_still_replays(self):
        root, wave_md, wave_id = self._with_readiness_run("replay")
        # The record shape written before the verdict existed: no field.
        builder = sys.modules[self.srv.build_identified_review_event.__module__]
        with patch.object(builder, "requires_intent_fit", lambda key: False):
            old = self._approve(root, wave_id, READINESS, "readiness", _evidence(), context="old")
        self.assertEqual(old["status"], "ok", old)
        before = subject.review_event_path(wave_md).read_bytes()
        retry = self._approve(root, wave_id, READINESS, "readiness", _evidence(), context="old")
        self.assertEqual(retry["status"], "ok", retry)
        self.assertTrue(retry["data"]["replayed"])
        self.assertEqual(subject.review_event_path(wave_md).read_bytes(), before)

    # AC-3 ---------------------------------------------------------------

    def test_other_approvals_need_no_verdict_and_refuse_one(self):
        root, wave_md, wave_id = self._with_readiness_run("others")
        cases = (("code-reviewer", "code-reviewer", "readiness"),
                 (CUSTOM_COUNCIL_KEY, ACTOR, "readiness"))
        for key, actor, phase in cases:
            with self.subTest(key=key):
                before = subject.review_event_path(wave_md).read_bytes()
                carrying = self._approve(root, wave_id, key, phase, _evidence(intent_fit="establishes"),
                                         actor=actor, context=f"carry-{key}")
                self._assert_refused(carrying, wave_md, before, "recorded only on council-readiness")
                plain = self._approve(root, wave_id, key, phase, _evidence(), actor=actor,
                                      context=f"plain-{key}")
                self.assertEqual(plain["status"], "ok", plain)
        active_root, active_md, active_id = self._readied("operator", status="active",
                                                          approvals=(READINESS, "code-reviewer"))
        before = subject.review_event_path(active_md).read_bytes()
        operator = self.srv.wf_review_event_response(
            active_root, active_id, "approval", "operator", "operator-carry", mode="create",
            signoff_key="operator-signoff", approval_phase="delivery",
            evidence=_evidence(intent_fit="establishes"), integrity_checks=dict(_APPROVAL_INTEGRITY))
        self._assert_refused(operator, active_md, before, "recorded only on council-readiness")

    # AC-4 ---------------------------------------------------------------

    def test_callers_see_the_verdict_before_writing(self):
        by_phase = {phase: list(values) for phase, values in subject.INTENT_FIT_VALUES_BY_PHASE.items()}
        council = subject.review_action_input_schema()["evidence"]["council_approval"]
        self.assertEqual(council["intent_fit"]["allowed_values_by_phase"], by_phase)
        self.assertIn("intent_fit", council["required_fields"])
        self.assertEqual(sorted(council["signoff_keys"]), sorted(subject.COUNCIL_SIGNOFF_KEYS))

        template = lifecycle_gate_support._prepare_council_verdict_template(None, typed=True)
        self.assertIn("'intent_fit': <" + "|".join(by_phase["readiness"]) + ">", template)
        self.assertIn("`intent_fit`", lifecycle_gate_support._prepare_council_instructions(None, typed=True))

        root, _wave_md, wave_id = self._with_readiness_run("actions")
        actions = self.srv.wf_review_wave_response(root, wave_id, phase="prepare")["data"]["review_actions"]
        by_id = {action["action_id"]: action for action in actions["next_actions"]}
        council_action = by_id[f"approval:{READINESS}"]
        self.assertEqual(council_action["blocking_constraint"]["required_evidence"]["intent_fit"],
                         by_phase["readiness"])
        self.assertIsNone(by_id["approval:code-reviewer"]["blocking_constraint"])

        source = (REPO_ROOT / ".wavefoundry/framework/scripts/wf_server/server_impl.py").read_text(encoding="utf-8")
        handler = next(node for node in ast.walk(ast.parse(source))
                       if isinstance(node, ast.FunctionDef) and node.name == "wf_review_event"
                       and any(getattr(d, "attr", None) == "tool"
                               for d in (getattr(x, "func", x) for x in node.decorator_list)))
        description = " ".join(ast.get_docstring(handler).split())
        self.assertIn("``evidence.intent_fit``", description)
        for value in subject.INTENT_FIT_VALUES:
            self.assertIn(f"``{value}``", description)

    # AC-8 ---------------------------------------------------------------

    def _delivered(self, name, verdict, *, operator=True):
        root, wave_md, wave_id = self._readied(name, status="active", approvals=(READINESS, "code-reviewer"))
        self.assertEqual(self._event(root, wave_id, "run", ACTOR, "delivery-run", _evidence(),
                                     mode="create", run_kind="initial_delivery")["status"], "ok")
        approvals = [("code-reviewer", "code-reviewer", _evidence()),
                     (DELIVERY, ACTOR, _evidence(intent_fit=verdict))]
        for key, actor, evidence in approvals:
            response = self._approve(root, wave_id, key, "delivery", evidence, actor=actor)
            self.assertEqual(response["status"], "ok", response)
        if operator:
            response = self.srv.wf_review_event_response(
                root, wave_id, "approval", "operator", "operator", mode="create",
                signoff_key="operator-signoff", approval_phase="delivery",
                evidence=_evidence(), integrity_checks=dict(_APPROVAL_INTEGRITY))
            self.assertEqual(response["status"], "ok", response)
        label = vocabulary_profile.MEMBER_STATUS_LABEL
        for doc in wave_md.parent.glob("*.md"):
            text = doc.read_text(encoding="utf-8")
            doc.write_text(text.replace(f"{label}: `planned`", f"{label}: `complete`", 1), encoding="utf-8")
        return root, wave_md, wave_id

    def _captured(self, root, wave_id):
        with patch.object(self.srv, "_framework_test_receipt_diagnostic", lambda *a, **k: None, create=True):
            return capture(self.srv, root, wave_id)

    def test_a_not_established_delivery_is_shown_and_never_blocks(self):
        root, _wave_md, wave_id = self._delivered("shown", "does_not")
        captured = self._captured(root, wave_id)
        for route in ("review:implementation", "close:dry_run"):
            with self.subTest(route=route):
                advisories = [d for d in captured[route]["diagnostics"] if d["code"] == ADVISORY]
                self.assertEqual(len(advisories), 1, captured[route])
                self.assertTrue(advisories[0]["advisory"])
        self.assertEqual(captured["close:create"]["status"], "ok", captured["close:create"])
        self.assertIn(ADVISORY, [d["code"] for d in captured["close:create"]["diagnostics"]])

    def test_a_council_delivery_approval_that_is_not_current_shows_nothing(self):
        root, _wave_md, wave_id = self._delivered("stale", "does_not")
        authority_cls = self.srv.lifecycle_gates.review_evidence.ReviewAuthority
        original = authority_cls.signoff_current

        def stale_council(authority, key, *args, **kwargs):
            if key == DELIVERY:
                return False
            return original(authority, key, *args, **kwargs)

        with patch.object(authority_cls, "signoff_current", stale_council):
            captured = self._captured(root, wave_id)
        for route in ("review:implementation", "close:dry_run"):
            with self.subTest(route=route):
                self.assertNotIn(ADVISORY, [d["code"] for d in captured[route]["diagnostics"]])

    def test_other_verdicts_show_nothing(self):
        root, _wave_md, wave_id = self._delivered("quiet", "partially")
        captured = self._captured(root, wave_id)
        for route in ("review:implementation", "close:dry_run", "close:create"):
            with self.subTest(route=route):
                self.assertNotIn(ADVISORY, [d["code"] for d in captured[route]["diagnostics"]])

    def test_operator_signoff_remedy_names_the_outcome_it_accepts(self):
        root, _wave_md, wave_id = self._delivered("remedy", "does_not", operator=False)
        review = self._captured(root, wave_id)["review:implementation"]
        missing = [d for d in review["diagnostics"] if d["code"] == "missing_operator_signoff"]
        self.assertEqual(len(missing), 1, review)
        self.assertIn("signing off accepts that outcome", missing[0]["message"])


class IntentFitLedgerTests(unittest.TestCase):
    """AC-2: optional on read, consistent with the write rules when present."""

    @staticmethod
    def _intent_errors(record):
        return [e for e in subject._validate_evidence_shape(record, 0) if "intent_fit" in e]

    @staticmethod
    def _approval(key, phase, actor=ACTOR, **extra):
        return executable_evidence(
            f"approval-{key}-{phase}", f"approval:{key}", claim_kind="approval", actor=actor,
            required_for_approval=True, approval_phase=phase, **extra)

    def test_every_repository_ledger_still_validates(self):
        ledgers = sorted((REPO_ROOT / record_paths.WAVES_ROOT).glob(f"**/{subject.EVENTS_FILENAME}"))
        self.assertGreater(len(ledgers), 100)
        for path in ledgers:
            with self.subTest(ledger=path.parent.name):
                records, parse_errors = subject.parse_review_event_bytes(path.read_bytes())
                self.assertEqual(parse_errors, ())
                self.assertEqual(subject.validate_review_evidence_records(records), ())

    def test_present_values_follow_the_write_rules(self):
        cases = (
            (self._approval(READINESS, "readiness"), False),
            (self._approval(READINESS, "readiness", intent_fit="partially"), False),
            (self._approval(OLD_READINESS, "readiness", intent_fit="does_not"), True),
            (self._approval(DELIVERY, "delivery", intent_fit="does_not"), False),
            (self._approval(DELIVERY, "delivery", intent_fit="bogus"), True),
            (self._approval("code-reviewer", "delivery", actor="code-reviewer", intent_fit="establishes"), True),
            (executable_evidence("finding-1", "F-1", intent_fit="establishes"), True),
        )
        for record, rejected in cases:
            with self.subTest(claim=record["claim_id"], value=record.get("intent_fit")):
                self.assertEqual(bool(self._intent_errors(record)), rejected, self._intent_errors(record))


if __name__ == "__main__":
    unittest.main()

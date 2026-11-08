#!/usr/bin/env python3
"""An accepted finding's ``promotion_trigger`` is discoverable and round-trips (wave 22u26, change 22r95).

The validator requires ``promotion_trigger`` for three rejection bases and refuses it for every
other. A review event carries it in ``evidence``. These tests hold the tool description, the guided
input schema, seed 209 and the tool-surface spec to the validator's own set, and record an accepted
finding through the served ``wf_review_event`` using only the fields the guided schema lists.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from server_tools_support import SCRIPTS_ROOT, _make_repo, integrity_checks, load_server, load_thin_runner
import review_evidence
import test_server_tools_lifecycle as fixtures

REPO_ROOT = SCRIPTS_ROOT.parents[2]
SEED_209 = SCRIPTS_ROOT.parent / "seeds" / "209-agent-harness-core.prompt.md"
SPEC = REPO_ROOT / "docs" / "specs" / "mcp-tool-surface.md"
FIELD = "promotion_trigger"


class PromotionTriggerContractTests(unittest.TestCase):
    """AC-2: every public surface names the field and the validator's exact basis set."""

    def setUp(self):
        self.bases = review_evidence.PROMOTION_TRIGGER_REJECTION_BASES
        self.refused = review_evidence.REJECTION_BASES - self.bases - {"none"}

    def test_the_bases_are_a_proper_subset_and_categorical_is_refused(self):
        self.assertTrue(self.bases < review_evidence.REJECTION_BASES)
        self.assertIn("categorical", self.refused)

    def test_the_guided_schema_lists_the_field_with_the_validator_set(self):
        schema = review_evidence.review_action_input_schema()
        entry = schema["evidence"]["finding"]["conditional_fields"][FIELD]
        self.assertEqual(entry["required_when"]["rejection_basis"], sorted(self.bases))
        self.assertIs(entry["refused_otherwise"], True)

    def _assert_names_rule(self, text: str, surface: str) -> None:
        self.assertIn(FIELD, text, surface)
        for basis in sorted(self.bases):
            self.assertIn(basis, text, f"{surface} omits {basis}")
        self.assertRegex(text, r"refused for any other basis|not valid for any other rejection basis", surface)

    def test_the_served_description_names_the_field_and_bases(self):
        load_server()
        with tempfile.TemporaryDirectory() as tmp:
            mcp = load_thin_runner().build_server(_make_repo(Path(tmp)))
            description = mcp._tool_manager._tools["wf_review_event"].description
        self._assert_names_rule(" ".join(description.split()), "wf_review_event description")
        self.assertIn("``promotion_trigger`` when it applies", description)

    def test_seed_209_and_the_spec_state_the_validator_rule(self):
        seed = " ".join(SEED_209.read_text(encoding="utf-8").split())
        self._assert_names_rule(seed, "seed 209")
        self.assertNotIn("optional for `categorical`", seed)
        spec = " ".join(SPEC.read_text(encoding="utf-8").split())
        self._assert_names_rule(spec, "mcp-tool-surface spec")
        self.assertIn("PROMOTION_TRIGGER_REJECTION_BASES", spec)


class PromotionTriggerRoundTripTests(unittest.TestCase):
    """AC-1 (regression guard) and AC-4: through the served tool, built from the guided schema."""

    _write_config = fixtures.WaveCouncilPolicyTests._write_config
    _prepared_wave_with_change = fixtures.WaveCouncilPolicyTests._prepared_wave_with_change
    _record_readiness_approval = fixtures.WaveCouncilPolicyTests._record_readiness_approval
    _run_prepare = fixtures.WaveCouncilPolicyTests._run_prepare
    LINT_OK = fixtures.WaveCouncilPolicyTests.LINT_OK
    GARDEN_OK = fixtures.WaveCouncilPolicyTests.GARDEN_OK

    def setUp(self):
        self.srv = load_server()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = _make_repo(Path(self.temp.name))
        self._write_config()
        self.wave_id, self.wave_md, _change = self._prepared_wave_with_change("promotion-trigger")
        mcp = load_thin_runner().build_server(self.root)
        self.tool = mcp._tool_manager._tools["wf_review_event"].fn
        self.schema = review_evidence.review_action_input_schema()

    def _judgment(self, basis: str) -> dict:
        # One allowed value per listed judgment field; the classification of an accepted risk.
        chosen = {
            "validation_status": "real", "scope_relation": "admitted", "contract_relevance": "none",
            "authority_domain": "none", "authority_delta": "none", "observable_impact": "low",
            "containment": "preventive", "fix_risk": "higher", "optional_value": "positive",
            "repair_safety": "safe", "benefit_vs_fix_risk": "less", "rejection_basis": basis,
            "introduced_or_worsened_by_wave": False, "supported_reachability": False,
            "attacker_reachability": False, "repair_scope_bounded": True,
        }
        listed = self.schema["judgment"]
        self.assertEqual(set(chosen), set(listed))
        for field, value in chosen.items():
            self.assertIn(value, listed[field]["allowed_values"], field)
        return chosen

    def _evidence(self, **extra) -> dict:
        fields = self.schema["evidence"]["finding"]["required_fields"]
        evidence = {field: f"fixture {field}" for field in fields}
        evidence.update(known_bad_detection_method="fixture known-bad", **extra)
        return evidence

    def _record(self, finding_id: str, basis: str, **extra) -> dict:
        return self.tool(
            wave_id=self.wave_id, event="finding", mode="create", actor="code-reviewer",
            context_id="ctx-" + finding_id, finding_id=finding_id, run_kind="readiness", cycle=0,
            source_lanes=["code-reviewer"], blocking_required_lanes=[], approval_recheck_lanes=[],
            judgment=self._judgment(basis), evidence=self._evidence(**extra),
            fresh_context=True, independent=True, integrity_checks=integrity_checks())

    def _head(self, finding_id: str) -> dict:
        records, errors = review_evidence.read_review_event_ledger(self.wave_md)
        self.assertEqual(errors, ())
        heads = [r for r in records if r.get("record_type") == "finding_synthesis" and r.get("finding_id") == finding_id]
        self.assertEqual(len(heads), 1, heads)
        return heads[0]

    @staticmethod
    def _messages(result: dict) -> str:
        return " ".join(d.get("message", "") for d in result.get("diagnostics", []))

    def test_an_accepted_finding_records_terminal_with_its_trigger(self):
        result = self._record("accepted-risk", "disproportionate_repair",
                              promotion_trigger="promote if the repair cost falls")
        self.assertEqual(result["status"], "ok", result)
        head = self._head("accepted-risk")
        self.assertEqual((head["disposition"], head["repair_execution_state"], head[FIELD]),
                         ("dont_do_later", "not_required", "promote if the repair cost falls"))
        self.assertFalse(head["blocking"])

    def test_a_trigger_requiring_basis_without_a_trigger_is_refused(self):
        result = self._record("no-trigger", "insufficient_evidence")
        self.assertEqual(result["status"], "error", result)
        self.assertIn("selected rejection_basis requires promotion_trigger", self._messages(result))

    def test_categorical_with_a_trigger_is_refused(self):
        result = self._record("categorical-trigger", "categorical", promotion_trigger="should be refused")
        self.assertEqual(result["status"], "error", result)
        self.assertIn("promotion_trigger is not valid for rejection basis `categorical`", self._messages(result))


if __name__ == "__main__":
    unittest.main()

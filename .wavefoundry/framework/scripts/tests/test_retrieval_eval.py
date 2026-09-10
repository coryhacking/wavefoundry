from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shutil
import statistics
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import retrieval_eval as subject


CLASSES = (
    "architecture_review_intent",
    "known_symbol_navigational",
    "constant_value_lookup",
    "exact_identifier_lexical",
    "error_string_lookup",
    "enumeration",
    "direct_low_information_artifact",
    "abstention",
    "agentic_fix_localization",
)


def _fixture(case_id: str, case_class: str, split: str, *, tools=("code_ask",),
             abstention: bool = False, query_form: str | None = None,
             evidence_role: str = "regression_only",
             authorship_class: str = "qa_local",
             consultation_status: str = "unknown",
             mechanism_exposure: str = "unknown") -> dict:
    omitted = set(subject.TOOLS) - set(tools)
    row = {
        # Wave 1wscp: evidence authority is mandatory on every fixture.  The
        # default here is deliberately NON-gain-eligible so a test must opt in
        # explicitly to assert an improvement claim.
        "evidence_role": evidence_role,
        "authorship_class": authorship_class,
        "consultation_status": consultation_status,
        "mechanism_exposure": mechanism_exposure,
        "id": case_id,
        "class": case_class,
        "split": split,
        "query": f"absent topic {case_id}" if abstention else f"find needle {case_id}",
        "expected_question_type": "explanatory",
        "applicable_tools": list(tools),
        "excluded_tools": {tool: "outside this tool's public contract" for tool in omitted},
        "relevance": [] if abstention else [{
            "path": "target.py",
            "grade": 2,
            "anchor": {"type": "content", "value": "needle"},
        }],
        "provenance": {"change": "local-change"},
        "rationale": "human-verified current implementation target",
        "abstention_expected": abstention,
    }
    if query_form is not None:
        row["query_form"] = query_form
    return row


def _valid_payload() -> dict:
    fixtures = []
    counter = 0
    for case_class in CLASSES[:-1]:
        for split in subject.SPLITS:
            counter += 1
            fixtures.append(_fixture(
                f"case-{counter}", case_class, split,
                tools=(subject.TOOLS[counter % len(subject.TOOLS)],),
                abstention=case_class == "abstention",
            ))
    for split in subject.SPLITS:
        for number in range(5):
            counter += 1
            fixtures.append(_fixture(
                f"agentic-{split}-{number}", "agentic_fix_localization", split,
                tools=(subject.TOOLS[counter % len(subject.TOOLS)],),
                query_form="symptom_only" if number < 3 else "contextual",
            ))
    return {"schema": subject.FIXTURE_SCHEMA, "fixtures": fixtures}


class EvidenceAuthorityTests(unittest.TestCase):
    """Wave 1wscp AC-2: gain eligibility is DERIVED, and a fixture cannot
    assert independence by label while contradicting it in the same object."""

    def _load(self, payload):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "target.py").write_text("needle\n", encoding="utf-8")
            path = root / "fixtures.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subject.load_fixture_corpus(path, root=root)

    def _reject(self, payload):
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            self._load(payload)
        return caught.exception

    def test_the_only_independent_combination_is_gain_eligible(self):
        payload = _valid_payload()
        payload["fixtures"][0].update(subject.GAIN_ELIGIBLE_COMBINATION)
        loaded = self._load(payload)
        self.assertTrue(loaded["fixtures"][0]["gain_eligible"])
        # Everything else in the same corpus stays ineligible.
        self.assertEqual(
            1, sum(1 for f in loaded["fixtures"] if f["gain_eligible"]))

    def test_false_independence_is_rejected_on_each_field_separately(self):
        # Each of the three supporting fields, mutated alone, must fail.  A
        # single combined mutant would pass if only one field were checked.
        for field, bad in (
            ("authorship_class", "implementer"),
            ("consultation_status", "consulted"),
            ("mechanism_exposure", "exposed"),
        ):
            with self.subTest(field=field):
                payload = _valid_payload()
                payload["fixtures"][0].update(subject.GAIN_ELIGIBLE_COMBINATION)
                payload["fixtures"][0][field] = bad
                error = self._reject(payload)
                self.assertEqual("invalid_fixture", error.code)
                self.assertIn(field, str(error))

    def test_a_fixture_cannot_declare_its_own_eligibility(self):
        payload = _valid_payload()
        payload["fixtures"][0]["gain_eligible"] = True
        self.assertEqual("invalid_fixture", self._reject(payload).code)

    def test_each_authority_field_is_mandatory_and_vocabulary_checked(self):
        for field in subject.EVIDENCE_FIELD_VOCABULARIES:
            with self.subTest(field=field, case="missing"):
                payload = _valid_payload()
                payload["fixtures"][0].pop(field)
                self.assertEqual("invalid_fixture", self._reject(payload).code)
            with self.subTest(field=field, case="unknown value"):
                payload = _valid_payload()
                payload["fixtures"][0][field] = "not-a-real-value"
                self.assertEqual("invalid_fixture", self._reject(payload).code)

    def test_derivation_ignores_the_role_label_alone(self):
        # The label by itself never confers eligibility; the derivation reads
        # all four fields.  This pins the "sole authority" contract directly.
        self.assertFalse(subject.derive_gain_eligibility(
            {"evidence_role": "independent_holdout"}))
        self.assertTrue(subject.derive_gain_eligibility(
            dict(subject.GAIN_ELIGIBLE_COMBINATION)))
        for field in subject.GAIN_ELIGIBLE_COMBINATION:
            with self.subTest(field=field):
                weakened = dict(subject.GAIN_ELIGIBLE_COMBINATION)
                weakened[field] = "unknown"
                self.assertFalse(subject.derive_gain_eligibility(weakened))

    def test_a_gain_claim_on_ineligible_evidence_is_refused_at_load(self):
        # A floor is a non-regression assertion any evidence may carry; a
        # minimum_improvement asserts the system got BETTER and needs
        # independent evidence.  Same rule, same target, opposite verdicts.
        def gate(improvement):
            payload = _valid_payload()
            rule = {"scope": "fixture", "target": "case-4", "tool": "code_ask",
                    "metric": "mrr_at_10", "floor": 1.0}
            if improvement is not None:
                rule["minimum_improvement"] = improvement
            payload["quality_gate"] = {"critical_floors": [rule]}
            return payload

        # Floor alone on ineligible (default, historical-style) evidence: fine.
        self._load(gate(None))

        # The same rule with a gain claim attached: refused, naming the case.
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            self._load(gate(0.1))
        self.assertEqual("invalid_fixture", caught.exception.code)
        self.assertIn("case-4", str(caught.exception))
        self.assertIn("minimum_improvement", str(caught.exception))

        # Make that one case genuinely independent and the claim is allowed.
        payload = gate(0.1)
        for fixture in payload["fixtures"]:
            if fixture["id"] == "case-4":
                fixture.update(subject.GAIN_ELIGIBLE_COMBINATION)
        self.assertEqual(
            0.1,
            self._load(payload)["quality_gate"]["critical_floors"][0]["minimum_improvement"])

    def test_the_standing_corpus_claims_no_independent_evidence(self):
        # The shipped 1seaw corpus was authored by the implementing agent
        # during the wave that built the classifier it measures, so no case in
        # it may support an improvement claim.  If this ever flips, someone has
        # relabelled historical evidence as independent.
        root = Path(__file__).resolve().parents[3].parent
        corpus_path = root / "docs" / "evals" / "retrieval-quality-golden.json"
        if not corpus_path.is_file():  # packaged distributions ship no corpus
            self.skipTest("standing corpus is not present in this tree")
        # Deliberately no ``root=``: relevance-path existence is a different
        # contract (covered by the stale-corpus tests) and requiring the whole
        # source tree here would make this assertion unrunnable in the scratch
        # copies used for mutation checks.
        loaded = subject.load_fixture_corpus(corpus_path)
        self.assertEqual(35, len(loaded["fixtures"]))
        self.assertEqual(
            [], [f["id"] for f in loaded["fixtures"] if f["gain_eligible"]])
        self.assertEqual(
            {"historical"}, {f["authorship_class"] for f in loaded["fixtures"]})


def _receipt(fixture_id="f1", tool="code_ask", metric="recall_at_10",
             verdict="confirmed_retrieval_miss", **over) -> dict:
    row = {
        "fixture_id": fixture_id, "tool": tool, "metric": metric,
        "run_id": "run-abc", "inspected_path": "target.py",
        "anchor": {"type": "content", "value": "needle"},
        "observed": "replayed the public path; target absent from the returned set",
        "verdict": verdict, "rationale": "grounded in the replayed response",
    }
    row.update(over)
    return row


class CarrierContaminationTests(unittest.TestCase):
    """Wave 1wscp AC-4: the evaluation apparatus must not occupy result slots
    that belong to the product, and must never be the source of an apparent
    gain."""

    EXPECTED = [".wavefoundry/framework/scripts/indexer.py"]

    def test_only_the_apparatus_counts_as_a_carrier(self):
        self.assertIsNone(subject.classify_carrier(
            ".wavefoundry/framework/scripts/indexer.py"))
        self.assertIsNone(subject.classify_carrier("docs/architecture/search.md"))
        for path, kind in (
            ("docs/evals/retrieval-quality-golden.json", "fixture_source"),
            ("docs/reports/retrieval-quality-post.json", "generated_report"),
            (".wavefoundry/framework/scripts/retrieval_eval.py", "evaluator_source"),
            ("docs/waves/1abc thing/wave.md", "wave_record"),
            ("docs/waves/1abc thing/events.jsonl", "review_commentary"),
        ):
            with self.subTest(path=path):
                self.assertEqual(kind, subject.classify_carrier(path))
        # A fixture living under a wave directory is still a fixture: the most
        # specific rule wins, so ordering is load-bearing.
        self.assertEqual("fixture_source",
                         subject.classify_carrier("docs/evals/nested/case.json"))

    def test_a_carrier_above_the_expected_target_displaced_it(self):
        rows = subject.carrier_rows(
            ["docs/waves/1abc thing/wave.md"] + self.EXPECTED,
            self.EXPECTED)
        self.assertEqual(1, len(rows))
        self.assertEqual("displaced_expected", rows[0]["effect"])
        self.assertEqual(1, rows[0]["rank"])
        self.assertEqual("wave_record", rows[0]["carrier_kind"])
        self.assertTrue(subject.carrier_contamination_violations(rows))

    def test_a_carrier_below_the_expected_target_is_neutral(self):
        rows = subject.carrier_rows(
            self.EXPECTED + ["docs/waves/1abc thing/wave.md"],
            self.EXPECTED,
            approved=["docs/waves/1abc thing/wave.md"])
        self.assertEqual("none", rows[0]["effect"])
        self.assertEqual("approved", rows[0]["approval_state"])
        self.assertEqual([], subject.carrier_contamination_violations(rows))

    def test_a_carrier_standing_in_for_a_missing_target_supplied_the_gain(self):
        # The expected path never appeared; whatever the case scored came from
        # the apparatus.  This is the self-match shape AC-4 names.
        rows = subject.carrier_rows(
            ["docs/evals/retrieval-quality-golden.json"], self.EXPECTED)
        self.assertEqual("supplied_gain", rows[0]["effect"])
        violations = subject.carrier_contamination_violations(rows)
        self.assertEqual(["carrier_supplied_gain"], [v["kind"] for v in violations])

    def test_an_unapproved_carrier_is_a_violation_even_when_neutral(self):
        rows = subject.carrier_rows(
            self.EXPECTED + ["docs/reports/retrieval-quality-post.json"],
            self.EXPECTED)
        self.assertEqual("none", rows[0]["effect"])
        self.assertEqual(["unapproved_carrier_present"],
                         [v["kind"] for v in subject.carrier_contamination_violations(rows)])

    def test_a_clean_holdout_reports_no_carriers_at_all(self):
        rows = subject.carrier_rows(
            self.EXPECTED + [".wavefoundry/framework/scripts/server_impl.py"],
            self.EXPECTED)
        self.assertEqual([], rows)
        self.assertEqual([], subject.carrier_contamination_violations(rows))

    def test_only_the_top_k_slots_are_examined(self):
        padding = [f".wavefoundry/framework/scripts/mod{i}.py" for i in range(subject.RECALL_K)]
        rows = subject.carrier_rows(
            padding + ["docs/evals/retrieval-quality-golden.json"], self.EXPECTED)
        self.assertEqual([], rows)


class AdjudicationReceiptTests(unittest.TestCase):
    """Wave 1wscp AC-3: a zero is not automatically a ranking defect, and the
    receipt that says which kind of failure it is must be per-(fixture, tool,
    metric) and grounded in a replayed public response."""

    def _load(self, payload):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "adjudications.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subject.load_adjudication_manifest(path)

    def _reject(self, payload):
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            self._load(payload)
        return caught.exception

    def _manifest(self, *rows):
        return {"schema": subject.ADJUDICATION_SCHEMA, "adjudications": list(rows)}

    def test_a_valid_receipt_round_trips_keyed_by_the_exact_triple(self):
        loaded = self._load(self._manifest(_receipt()))
        self.assertEqual(
            [("f1", "code_ask", "recall_at_10")], list(loaded))

    def test_every_required_field_is_mandatory(self):
        for field in ("fixture_id", "tool", "metric", "run_id",
                      "inspected_path", "anchor", "observed", "verdict", "rationale"):
            with self.subTest(field=field):
                row = _receipt()
                row.pop(field)
                self.assertEqual(
                    "invalid_adjudication", self._reject(self._manifest(row)).code)

    def test_a_blank_rationale_or_observation_is_refused(self):
        for field in ("rationale", "observed", "inspected_path"):
            with self.subTest(field=field):
                self.assertEqual(
                    "invalid_adjudication",
                    self._reject(self._manifest(_receipt(**{field: "   "}))).code)

    def test_the_verdict_and_anchor_are_vocabulary_checked(self):
        self.assertEqual("invalid_adjudication",
                         self._reject(self._manifest(_receipt(verdict="looks_fine"))).code)
        self.assertEqual("invalid_adjudication",
                         self._reject(self._manifest(
                             _receipt(anchor={"type": "vibes", "value": "x"}))).code)

    def test_one_receipt_per_triple(self):
        self.assertEqual(
            "invalid_adjudication",
            self._reject(self._manifest(_receipt(), _receipt())).code)
        # The same fixture and tool at a DIFFERENT metric is a distinct receipt.
        both = self._load(self._manifest(
            _receipt(), _receipt(metric="ndcg_at_10")))
        self.assertEqual(2, len(both))

    def test_a_seeded_wrong_section_case_is_adjudicated_as_an_oracle_miss(self):
        # AC-3's second named case: the oracle pointed at the wrong section, so
        # the zero indicts the label rather than the ranking.  The verdict must
        # be expressible and must survive validation with a section anchor.
        loaded = self._load(self._manifest(_receipt(
            fixture_id="seeded-wrong-section", metric="ndcg_at_10",
            verdict="oracle_anchor_miss",
            anchor={"type": "section", "value": "Guru > Retrieval Loop"},
            observed="replayed the response; the returned chunk is the correct "
                     "document under a different heading than the anchor names",
            rationale="the anchor names a heading the target content does not "
                      "live under, so the miss is an oracle defect")))
        self.assertEqual(
            "oracle_anchor_miss",
            loaded[("seeded-wrong-section", "code_ask", "ndcg_at_10")]["verdict"])

    def test_gaps_names_every_unadjudicated_zero_and_ignores_scored_cases(self):
        report = {"cases": [
            {"fixture_id": "f1", "tool": "code_ask", "applicable": True,
             "recall_at_10": 0.0, "ndcg_at_10": 1.0},
            {"fixture_id": "f2", "tool": "code_lexical", "applicable": True,
             "recall_at_10": 0.0, "mrr_at_10": 0.0},
            # Not applicable: never demands a receipt.
            {"fixture_id": "f3", "tool": "code_ask", "applicable": False,
             "recall_at_10": 0.0},
        ]}
        self.assertEqual(
            [("f1", "code_ask", "recall_at_10"),
             ("f2", "code_lexical", "mrr_at_10"),
             ("f2", "code_lexical", "recall_at_10")],
            subject.adjudication_gaps(report, {}))
        # Covering one triple removes exactly that triple.
        covered = subject.adjudication_gaps(
            report, {("f1", "code_ask", "recall_at_10"): _receipt()})
        self.assertNotIn(("f1", "code_ask", "recall_at_10"), covered)
        self.assertEqual(2, len(covered))

    def test_the_shipped_manifest_cannot_enter_the_retrieval_corpus(self):
        # The manifest quotes fixture queries and target paths verbatim, so an
        # indexed copy would let the evaluator answer its own questions.  This
        # was a live defect: the framework's own contamination guard refused
        # the file until it was added to .aiignore beside the golden corpus.
        import indexer as indexer_module
        root = Path(__file__).resolve().parents[3].parent
        manifest = root / "docs" / "evals" / "retrieval-adjudications.json"
        if not manifest.is_file():
            self.skipTest("adjudication manifest is not present in this tree")
        subject.assert_eval_artifacts_excluded(root, [manifest], indexer_module)

    def test_the_shipped_manifest_adjudicates_the_real_constant_value_cases(self):
        root = Path(__file__).resolve().parents[3].parent
        manifest_path = root / "docs" / "evals" / "retrieval-adjudications.json"
        if not manifest_path.is_file():
            self.skipTest("adjudication manifest is not present in this tree")
        loaded = subject.load_adjudication_manifest(manifest_path)
        # Both constant-value cases: retrieval succeeded, routing did not.
        for fixture_id in ("constant-value-calibration-reranker",
                           "constant-value-holdout-int8-revision"):
            with self.subTest(fixture_id=fixture_id):
                receipt = loaded[(fixture_id, "code_ask", "question_type_accuracy")]
                self.assertEqual("classifier_contract_mismatch", receipt["verdict"])
        # The lexical zeros on the same fixture are a real miss, not a mismatch.
        self.assertEqual(
            "confirmed_retrieval_miss",
            loaded[("constant-value-calibration-reranker",
                    "code_lexical", "recall_at_10")]["verdict"])


class FixtureSchemaTests(unittest.TestCase):
    def test_accepts_frozen_schema_and_tagged_anchor_union(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "target.py").write_text("needle\n", encoding="utf-8")
            fixture_path = root / "fixtures.json"
            fixture_path.write_text(json.dumps(_valid_payload()), encoding="utf-8")
            loaded = subject.load_fixture_corpus(fixture_path, root=root)
        self.assertEqual(subject.FIXTURE_SCHEMA, loaded["schema"])
        self.assertEqual(26, len(loaded["fixtures"]))

    def test_rejects_unknown_or_malformed_anchor_shape(self):
        payload = _valid_payload()
        payload["fixtures"][0]["relevance"][0]["anchor"] = {
            "type": "line_span", "start": 9, "end": 3,
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixtures.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.load_fixture_corpus(path)
        self.assertEqual("invalid_fixture", caught.exception.code)

    def test_rejects_missing_exclusion_reason_and_query_cap(self):
        payload = _valid_payload()
        payload["fixtures"][0]["excluded_tools"].pop(next(iter(payload["fixtures"][0]["excluded_tools"])))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixtures.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.load_fixture_corpus(path)
        self.assertEqual("invalid_fixture", caught.exception.code)

        payload = _valid_payload()
        payload["fixtures"][0]["query"] = "é" * 257
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixtures.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.load_fixture_corpus(path)
        self.assertEqual("query_cap_exceeded", caught.exception.code)

    def test_stale_relevance_path_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "fixtures.json"
            path.write_text(json.dumps(_valid_payload()), encoding="utf-8")
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.load_fixture_corpus(path, root=root)
        self.assertEqual("stale_corpus", caught.exception.code)

    def test_accepts_explicit_critical_floor_contract(self):
        payload = _valid_payload()
        # Wave 1wscp: a gain claim needs independently eligible evidence, so
        # the targeted case must carry the full independent combination.
        for fixture in payload["fixtures"]:
            if fixture["id"] == "case-4":
                fixture.update(subject.GAIN_ELIGIBLE_COMBINATION)
        payload["quality_gate"] = {"critical_floors": [{
            "scope": "fixture", "target": "case-4",
            "tool": "code_ask", "metric": "mrr_at_10", "floor": 1.0,
            "minimum_improvement": 0.1,
        }]}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixtures.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = subject.load_fixture_corpus(path)
        self.assertEqual(payload["quality_gate"], loaded["quality_gate"])

    def test_fixture_floor_rejects_aggregate_only_agentic_mrr_metric(self):
        payload = _valid_payload()
        payload["quality_gate"] = {"critical_floors": [{
            "scope": "fixture", "target": "case-4", "tool": "code_ask",
            "metric": "agentic_mrr_at_10", "floor": 1.0,
        }]}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixtures.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.load_fixture_corpus(path)
        self.assertEqual("invalid_fixture", caught.exception.code)

    def test_relevance_tools_must_cover_each_applicable_public_path(self):
        payload = _valid_payload()
        fixture = payload["fixtures"][0]
        fixture["applicable_tools"] = ["code_ask", "docs_search"]
        fixture["excluded_tools"] = {
            "code_search": "not applicable", "code_lexical": "not applicable",
        }
        fixture["relevance"][0]["tools"] = ["code_ask"]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fixtures.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.load_fixture_corpus(path)
        self.assertEqual("invalid_fixture", caught.exception.code)


class SelfContaminationTests(unittest.TestCase):
    def setUp(self):
        self.indexer = SimpleNamespace(
            SOURCE_CODE_EXTENSIONS={".json", ".py"},
            DOCS_TEXT_EXTENSIONS={".txt"},
            DOCS_EXTENSIONLESS_NAMES=set(),
            CODE_EXTENSIONLESS_NAMES=set(),
            _load_ignore_patterns=lambda root: [
                line.strip() for line in (root / ".aiignore").read_text().splitlines()
                if line.strip()
            ],
            _matches_ignore=lambda rel, patterns: rel in patterns,
        )

    def test_rejects_index_eligible_unignored_fixture_or_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".aiignore").write_text("safe.json\n", encoding="utf-8")
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.assert_eval_artifacts_excluded(root, [root / "unsafe.json"], self.indexer)
        self.assertEqual("self_contaminating_artifact", caught.exception.code)

    def test_accepts_ignored_or_outside_root_artifacts(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            (root / ".aiignore").write_text("safe.json\n", encoding="utf-8")
            subject.assert_eval_artifacts_excluded(
                root, [root / "safe.json", Path(outside) / "report.json"], self.indexer,
            )


class ScoringTests(unittest.TestCase):
    def test_path_normalization_preserves_leading_dot_directories(self):
        self.assertEqual(".wavefoundry/framework/scripts/server_impl.py",
                         subject._normal_path("./.wavefoundry/framework/scripts/server_impl.py"))

    def test_shared_file_requires_anchor_and_line_spans_overlap(self):
        fixture = _fixture("one", "known_symbol_navigational", "holdout")
        response = {"status": "ok", "data": {"citations": [
            {"path": "target.py", "excerpt": "unrelated content", "lines": [1, 4]},
            {"path": "target.py", "excerpt": "contains needle here", "lines": [20, 30]},
        ]}}
        score = subject.score_response("code_ask", fixture, response)
        self.assertEqual(2, score["first_relevant_rank"])
        self.assertEqual(1.0, score["recall_at_10"])
        self.assertEqual(0.5, score["mrr_at_10"])
        self.assertEqual("excerpt", score["normalized_ranks"][1]["matched_field"])
        self.assertEqual("needle", score["normalized_ranks"][1]["matched_evidence"])

        fixture["relevance"][0]["anchor"] = {"type": "line_span", "start": 25, "end": 28}
        score = subject.score_response("code_ask", fixture, response)
        self.assertEqual(2, score["first_relevant_rank"])

    def test_nearest_rank_p95(self):
        self.assertEqual(10.0, subject._nearest_rank_p95(list(range(1, 11))))

    def test_symbol_anchor_requires_declaration_span_not_same_file_mention(self):
        expected = {"path": "target.py", "grade": 1.0,
                    "anchor": {"type": "symbol", "value": "main"}}
        declarations = {"target.py::main": {"start_line": 40, "end_line": 55,
                                            "kind": "function", "resolver": "code_outline"}}
        known_bad = (
            # exact same-file call-site mention outside the declaration
            {"path": "target.py", "kind": "code", "lines": [80, 92],
             "excerpt": "    result = main()"},
            # comment mention in a neighbouring chunk
            {"path": "target.py", "kind": "code", "lines": [10, 20],
             "excerpt": "# see main for the entry point\ndef helper():"},
            # whole-file summary spanning every declaration
            {"path": "target.py", "kind": "code-summary", "lines": [1, 200],
             "excerpt": "main helper"},
            # the retired field-name shortcut carries no span
            {"path": "target.py", "kind": "code", "symbol": "main", "excerpt": "def main():"},
            # adjacent chunk ending on the line before the declaration
            {"path": "target.py", "kind": "code", "lines": [30, 39], "excerpt": "def before():"},
        )
        for wrong in known_bad:
            with self.subTest(result=wrong):
                self.assertFalse(subject._anchor_matches(wrong, expected, declarations))
        declaration_evidence = (
            # decorated declaration chunk starting above the outline's def line
            {"path": "target.py", "kind": "code", "lines": [38, 55],
             "excerpt": "@decorated\ndef main():"},
            # a split sub-window inside the declaration body
            {"path": "target.py", "kind": "code", "lines": [48, 55], "excerpt": "    return value"},
        )
        for right in declaration_evidence:
            with self.subTest(result=right):
                evidence = subject._anchor_match_evidence(right, expected, declarations)
                self.assertEqual("lines", evidence["field"])
                self.assertEqual(list(right["lines"]), evidence["evidence"])

    def test_unresolved_symbol_anchor_is_invalid_not_a_miss(self):
        expected = {"path": "target.py", "grade": 1.0,
                    "anchor": {"type": "symbol", "value": "main"}}
        result = {"path": "target.py", "kind": "code", "lines": [40, 55], "excerpt": "def main():"}
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject._anchor_matches(result, expected, {})
        self.assertEqual("unresolved_symbol_anchor", caught.exception.code)
        with self.assertRaises(subject.EvaluationInvalid):
            subject._anchor_matches(result, expected, None)

    def test_section_anchor_requires_heading_identity_not_mention(self):
        expected = {"path": "report.md", "grade": 1.0,
                    "anchor": {"type": "section", "value": "Rationale"}}
        self.assertFalse(subject._anchor_matches(
            {"path": "report.md", "section": "Report > Decision",
             "excerpt": "The Rationale section explains this."}, expected,
        ))
        self.assertTrue(subject._anchor_matches(
            {"path": "report.md", "section": "Report > Rationale (part 1/2)",
             "excerpt": "Decision details."}, expected,
        ))

    def test_code_ask_abstention_requires_declared_no_match_or_all_weak(self):
        """Cycle-2 review (QA-SEAT-2): a low band alone is not an abstention when the
        response still presents non-weak citations without the no-match gap."""
        fixture = _fixture("absent", "abstention", "holdout", abstention=True)

        def response(citations, gaps):
            return {"status": "ok", "data": {"citations": citations, "gaps": gaps,
                                             "confidence": "low"}}

        strong = [{"path": "other.py", "excerpt": "x", "lines": [1, 2], "score": 0.3}]
        weak = [{"path": "other.py", "excerpt": "x", "lines": [1, 2], "score": 0.01, "weak": True}]
        self.assertFalse(subject.score_response("code_ask", fixture, response(strong, []))["abstention_correct"])
        self.assertTrue(subject.score_response("code_ask", fixture, response(
            strong, ["no confident match — all retrieval scores are below the relevance floor"]))["abstention_correct"])
        self.assertTrue(subject.score_response("code_ask", fixture, response(weak, []))["abstention_correct"])
        self.assertTrue(subject.score_response("code_ask", fixture, response([], []))["abstention_correct"])
        medium = {"status": "ok", "data": {"citations": [], "gaps": [], "confidence": "medium"}}
        self.assertFalse(subject.score_response("code_ask", fixture, medium)["abstention_correct"])

    def test_section_anchor_falls_back_to_baked_breadcrumb_without_section_field(self):
        expected = {"path": "report.md", "grade": 1.0,
                    "anchor": {"type": "section", "value": "Rationale"}}
        # code_ask citations and code_lexical rows carry no section field; the chunker's
        # first-line breadcrumb is the same section path.
        evidence = subject._anchor_match_evidence(
            {"path": "report.md", "kind": "doc",
             "excerpt": "Report > Rationale (part 2/2)\n\nDecision details."}, expected,
        )
        self.assertEqual({"field": "breadcrumb", "evidence": "Rationale"}, evidence)
        self.assertTrue(subject._anchor_matches(
            {"path": "report.md", "kind": "doc", "text": "Report > Rationale\n\nbody"}, expected,
        ))
        known_bad = (
            # mention in the body, not the breadcrumb
            {"path": "report.md", "kind": "doc",
             "excerpt": "Report > Decision\n\nThe Rationale section explains this."},
            # a summary chunk's first line is the title, never a section path
            {"path": "report.md", "kind": "doc-summary",
             "excerpt": "Rationale\nOwner: Engineering\nSections: Rationale"},
            # an explicit section field wins over the excerpt even when it disagrees
            {"path": "report.md", "kind": "doc", "section": "Report > Decision",
             "excerpt": "Report > Rationale\n\nbody"},
            {"path": "report.md", "kind": "doc", "excerpt": ""},
        )
        for wrong in known_bad:
            with self.subTest(result=wrong):
                self.assertFalse(subject._anchor_matches(wrong, expected))

    def test_content_anchor_uses_explicit_boundaries(self):
        expected = {"path": "target.py", "grade": 1.0,
                    "anchor": {"type": "content", "value": "main"}}
        self.assertFalse(subject._anchor_matches(
            {"path": "target.py", "excerpt": "domain_value = 1"}, expected,
        ))
        self.assertTrue(subject._anchor_matches(
            {"path": "target.py", "excerpt": "def main():"}, expected,
        ))

    def test_per_tool_relevance_removes_unreachable_cross_layer_denominator(self):
        fixture = _fixture("mixed", "direct_ignore_manifest", "holdout",
                           tools=("code_search", "docs_search"))
        fixture["relevance"] = [
            {"path": "source.py", "grade": 3, "anchor": {"type": "symbol", "value": "main"},
             "tools": ["code_search"]},
            {"path": "guide.md", "grade": 2, "anchor": {"type": "section", "value": "Usage"},
             "tools": ["docs_search"]},
        ]
        response = {"status": "ok", "data": {"results": [
            {"path": "source.py", "kind": "code", "lines": [3, 9], "excerpt": "def main():"},
        ]}}
        declarations = {"source.py::main": {"start_line": 3, "end_line": 9,
                                            "kind": "function", "resolver": "code_outline"}}
        score = subject.score_response("code_search", fixture, response, declarations)
        self.assertEqual(1.0, score["recall_at_10"])


class DeclarationResolutionTests(unittest.TestCase):
    class OutlineServer:
        def __init__(self, symbols, constants):
            self.symbols = symbols
            self.constants = constants
            self.calls: list[tuple] = []

        def code_outline_response(self, root, path):
            self.calls.append(("code_outline", path))
            return {"status": "ok", "data": {"file": path, "parser_used": "python_ast",
                                             "symbols": self.symbols.get(path, [])}}

        def code_constants_response(self, root, symbols, glob=""):
            self.calls.append(("code_constants", tuple(symbols)))
            return {"status": "ok", "data": {"results": self.constants}}

    def _corpus(self, *targets):
        fixture = _fixture("one", "known_symbol_navigational", "holdout")
        fixture["relevance"] = [
            {"path": path, "grade": 3, "anchor": {"type": "symbol", "value": symbol}}
            for path, symbol in targets
        ]
        return {"schema": subject.FIXTURE_SCHEMA, "fixtures": [fixture]}

    def test_resolves_through_public_outline_then_constants_and_records_spans(self):
        server = self.OutlineServer(
            {"pkg/mod.py": [
                {"name": "run", "kind": "function", "start_line": 10, "end_line": 30},
                {"name": "Other", "kind": "class", "start_line": 40, "end_line": 80},
            ]},
            [{"name": "INT8_REVISION_2", "file": "./pkg/mod.py", "line": 4, "kind": "scalar"},
             {"name": "INT8_REVISION_2", "file": "pkg/elsewhere.py", "line": 9, "kind": "scalar"}],
        )
        resolved = subject.resolve_symbol_anchors(
            self._corpus(("pkg/mod.py", "run"), ("pkg/mod.py", "INT8_REVISION_2")), server, Path("."),
        )
        self.assertEqual({"start_line": 10, "end_line": 30, "kind": "function",
                          "resolver": "code_outline"}, resolved["pkg/mod.py::run"])
        self.assertEqual({"start_line": 4, "end_line": 4, "kind": "constant",
                          "resolver": "code_constants"}, resolved["pkg/mod.py::INT8_REVISION_2"])
        self.assertIn(("code_constants", ("INT8_REVISION_2",)), server.calls)

    def test_unresolved_or_ambiguous_symbol_anchor_invalidates_the_run(self):
        ambiguous = self.OutlineServer(
            {"pkg/mod.py": [
                {"name": "run", "kind": "method", "start_line": 10, "end_line": 12},
                {"name": "run", "kind": "method", "start_line": 20, "end_line": 22},
            ]}, [],
        )
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.resolve_symbol_anchors(self._corpus(("pkg/mod.py", "run")), ambiguous, Path("."))
        self.assertEqual("ambiguous_symbol_anchor", caught.exception.code)
        missing = self.OutlineServer({"pkg/mod.py": [
            {"name": "run", "kind": "function", "start_line": 10, "end_line": None},
        ]}, [])
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.resolve_symbol_anchors(self._corpus(("pkg/mod.py", "run")), missing, Path("."))
        self.assertEqual("unresolved_symbol_anchor", caught.exception.code)


class TimeoutTests(unittest.TestCase):
    def test_timeout_is_invalid_execution(self):
        def slow():
            time.sleep(0.05)
            return {}

        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject._run_with_timeout(slow, 0.001, "slow")
        self.assertEqual("call_timeout", caught.exception.code)


WARM_SAMPLE_PAIRS = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "retrieval_eval"
     / "warm_sample_pairs.json").read_text(encoding="utf-8")
)["pairs"]


class BaselineComparisonTests(unittest.TestCase):
    def _report(self, generation: int, p95: float, response_bytes: int,
                *, floor: float | None = None, median: float | None = None,
                sample_count: int = 36) -> dict:
        # Wave 1wur7 (1wuuh): the comparison now reads the whole warm
        # distribution.  The defaults keep the floor and median proportional to
        # the p95 so a pair built with only ``p95`` still has one jitter value.
        floor_ms = p95 * 0.5 if floor is None else floor
        median_ms = p95 * 0.75 if median is None else median
        aggregate = {
            "case_count": 1, "recall_at_10": 1.0, "ndcg_at_10": 1.0,
            "agentic_mrr_at_10": 1.0, "abstention_accuracy": 1.0,
            "question_type_accuracy": 1.0,
        }
        report = {
            "schema": subject.REPORT_SCHEMA,
            "fixture_schema": subject.FIXTURE_SCHEMA,
            "fixture_digest": "same",
            "index_identity": {"repository_root": "/repo", "index_directory": "/repo/.wavefoundry/index",
                               "repository_device": 1, "repository_inode": 1,
                               "state_store": "/repo/.wavefoundry/index/index-state.sqlite",
                               "state_store_device": 1, "state_store_inode": 2},
            "generation": {"start": generation, "end": generation,
                           "start_attempt_id": f"attempt-{generation}",
                           "end_attempt_id": f"attempt-{generation}",
                           "start_status": "complete", "end_status": "complete",
                           "start_token": [f"attempt-{generation}", "complete", generation],
                           "end_token": [f"attempt-{generation}", "complete", generation]},
            "evaluator_identity": {"source_sha256": "evaluator", "report_schema": subject.REPORT_SCHEMA,
                                   "fixture_schema": subject.FIXTURE_SCHEMA},
            "production_identity": {"scripts_directory": "/repo/scripts",
                                    "modules": {"server_impl.py": "a"}, "digest": "production",
                                    "versions": {"chunker": "1", "walker": "1", "graph_builder": "1"}},
            "environment": {
                "python": "3.13", "platform": "test", "machine": "arm64", "processor": "test",
                "models": {"docs": "d", "code": "c", "reranker": "r"},
                "indexed_model_versions": {"docs": "d", "code": "c"},
                "execution_providers": ["CPUExecutionProvider"], "reranker_provider": "cpu",
                "packages": {"fastembed": "1", "lancedb": "1", "onnxruntime": "1"},
                "offline": True,
                "retrieval_toggles": {name: False for name in subject.RETRIEVAL_TOGGLE_ENVS},
                "production_tuning": {name: default
                                      for name, _module, default in subject.PRODUCTION_TUNING_ENVS},
            },
            "metrics": {"by_tool": {tool: {
                "by_split": {"holdout": dict(aggregate)},
                "by_split_and_class": {"holdout": {"class-a": dict(aggregate)}},
            }
                                     for tool in subject.TOOLS}},
            "performance": {"tools": {tool: {
                "warm_p95_ms": p95, "warm_floor_ms": floor_ms,
                "warm_median_ms": median_ms, "sample_count": sample_count,
                "max_response_bytes": response_bytes,
            } for tool in subject.TOOLS}},
            "cases": [{
                "fixture_id": "fixture-a", "class": "class-a", "split": "holdout",
                "tool": "code_ask", "applicable": True, "recall_at_10": 1.0,
                "ndcg_at_10": 1.0, "mrr_at_10": 1.0,
                "abstention_correct": None, "question_type_correct": True,
            }],
        }
        report["run_id"] = subject._compute_run_id(report)
        return report

    def test_same_generation_computes_exact_jitter(self):
        baseline = self._report(8, 100.0, 1000)
        current = self._report(8, 110.0, 1200)
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual([], violations)
        self.assertAlmostEqual(0.1, current["performance"]["tools"]["code_ask"]["jitter_ratio"])
        self.assertEqual(0.3, current["performance"]["tools"]["code_ask"]["permitted_relative_regression"])
        self.assertEqual("same_generation_pair", current["comparison"]["comparison_kind"])
        self.assertTrue(current["comparison"]["same_production_identity"])

    def test_same_generation_production_change_is_a_receipt_not_a_jitter_pair(self):
        baseline = self._report(8, 100.0, 1000)
        current = self._report(8, 110.0, 1200)
        current["production_identity"]["digest"] = "repaired-production"
        current["production_identity"]["modules"]["server_impl.py"] = "b"
        # Wave 1wuju (1wujt): a baseline without pair-derived jitter used to be
        # refused here; it is now accepted at the 25% floor, and the receipt says
        # so rather than pretending a jitter pair was measured.
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual([], violations)
        perf = current["performance"]["tools"]["code_ask"]
        self.assertEqual("single_run_floor", perf["jitter_source"])
        self.assertIsNone(perf["jitter_ratio"])
        self.assertEqual(0.25, perf["permitted_relative_regression"])
        self.assertNotIn("jitter_components", perf)
        current = self._report(8, 110.0, 1200)
        current["production_identity"]["digest"] = "repaired-production"
        current["production_identity"]["modules"]["server_impl.py"] = "b"
        for tool in subject.TOOLS:
            baseline["performance"]["tools"][tool]["jitter_ratio"] = 0.02
        baseline["run_id"] = subject._compute_run_id(baseline)
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual([], violations)
        perf = current["performance"]["tools"]["code_ask"]
        self.assertEqual(0.02, perf["jitter_ratio"])
        self.assertEqual("baseline_same_generation_pair", perf["jitter_source"])
        comparison = current["comparison"]
        self.assertEqual("production_change_same_generation", comparison["comparison_kind"])
        self.assertTrue(comparison["same_generation"])
        self.assertFalse(comparison["same_production_identity"])
        self.assertEqual("production", comparison["baseline_production_digest"])
        self.assertEqual("repaired-production", comparison["current_production_digest"])

    def test_cross_generation_reports_latency_to_operator_review_and_keeps_size_hard(self):
        # Wave 1wur7 (1wuuh Requirement 4, AC-4): a cross-generation comparison
        # inherits the BASELINE pair's jitter, so the latency clause cannot police
        # the current machine as a hard violation.  It is reported and routed to
        # operator review; asserted POSITIVELY rather than by deleting the old
        # hard-violation assertion.
        baseline = self._report(8, 100.0, 1000)
        for tool in subject.TOOLS:
            baseline["performance"]["tools"][tool]["jitter_ratio"] = 0.01
        baseline["run_id"] = subject._compute_run_id(baseline)
        current = self._report(9, 140.0, 10000)
        current["operator_review_reasons"] = []
        reasons = current["operator_review_reasons"]
        violations, operator_reviews = subject.apply_baseline_comparison(current, baseline)
        kinds = {row["kind"] for row in violations}
        self.assertNotIn("latency_regression", kinds)
        self.assertIn("response_size_regression", kinds)
        latency = [row for row in operator_reviews if row["kind"] == "latency_regression"]
        self.assertEqual(sorted(subject.TOOLS), sorted(row["tool"] for row in latency))
        for row in latency:
            self.assertEqual("operator_review", row["enforcement"])
            self.assertEqual(140.0, row["current_ms"])
            self.assertEqual(125.0, row["threshold_ms"])
        self.assertEqual("operator_review",
                         current["performance"]["tools"]["code_ask"]["latency_enforcement"])
        self.assertEqual(
            [row["kind"] for row in latency],
            [row["kind"] for row in current["comparison"]["operator_review_reasons"]
             if row["kind"] == "latency_regression"])
        # The reasons must reach the SAME list object the verdict reads.
        self.assertIs(reasons, current["operator_review_reasons"])
        self.assertIn("latency_regression",
                      {row["kind"] for row in current["operator_review_reasons"]})

    def test_same_generation_latency_routes_to_operator_review_not_a_hard_fail(self):
        # Wave 1wur7, delivery review CODE-DEL-3: both arms share one production
        # identity on one frozen generation, so a p95 difference is jitter by
        # construction -- there is no change to attribute a regression to. The
        # clause is reported and routed, never raised as a hard violation and
        # never dropped. The floor and median are held equal so the pair is quiet
        # by the promotability rule and only the tail moved.
        baseline = self._report(8, 100.0, 1000, floor=50.0, median=75.0)
        current = self._report(8, 140.0, 1000, floor=50.0, median=75.0)
        current["operator_review_reasons"] = []
        violations, operator_reviews = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual("same_generation_pair", current["comparison"]["comparison_kind"])
        self.assertNotIn("latency_regression", {row["kind"] for row in violations})
        latency = [row for row in operator_reviews if row["kind"] == "latency_regression"]
        self.assertEqual(sorted(subject.TOOLS), sorted(row["tool"] for row in latency))
        for row in latency:
            self.assertEqual("operator_review", row["enforcement"])
            self.assertIn("jitter rather than a regression", row["reason"])
        self.assertIn("latency_regression",
                      {row["kind"] for row in current["operator_review_reasons"]})
        self.assertEqual("operator_review",
                         current["performance"]["tools"]["code_ask"]["latency_enforcement"])

    def test_contended_baseline_is_reported_as_an_inherited_jitter_source(self):
        # Wave 1wur7, delivery review ARCH-DEL-6 made `pair_contended` READ at the
        # one seam where a contended pair becomes the band. The operator decision
        # at close made latency advisory for every kind, so a contended baseline is
        # now REPORTED per tool on both inheriting kinds rather than refused.
        baseline = self._report(8, 100.0, 1000)
        for tool in subject.TOOLS:
            baseline["performance"]["tools"][tool]["jitter_ratio"] = 0.30
            baseline["performance"]["tools"][tool]["pair_contended"] = True
        baseline["run_id"] = subject._compute_run_id(baseline)
        current = self._report(9, 100.0, 1000)
        _, operator_reviews = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual("cross_generation", current["comparison"]["comparison_kind"])
        reported = [row for row in operator_reviews
                    if row["kind"] == "inherited_contended_baseline"]
        self.assertEqual(sorted(subject.TOOLS), sorted(row["tool"] for row in reported))
        for row in reported:
            self.assertEqual(0.30, row["baseline_jitter_ratio"])
            self.assertIn("quiet same-generation pair", row["recovery"])
        for tool in subject.TOOLS:
            self.assertTrue(current["performance"]["tools"][tool]["baseline_pair_contended"])
        production_change = self._report(8, 100.0, 1000)
        production_change["production_identity"]["digest"] = "repaired-production"
        production_change["production_identity"]["modules"]["server_impl.py"] = "b"
        _, operator_reviews = subject.apply_baseline_comparison(production_change, baseline)
        self.assertEqual("production_change_same_generation",
                         production_change["comparison"]["comparison_kind"])
        self.assertEqual(sorted(subject.TOOLS),
                         sorted(row["tool"] for row in operator_reviews
                                if row["kind"] == "inherited_contended_baseline"))
        # A quiet baseline on the same shape reports nothing, on both kinds.
        for tool in subject.TOOLS:
            baseline["performance"]["tools"][tool]["pair_contended"] = False
        baseline["run_id"] = subject._compute_run_id(baseline)
        quiet = self._report(9, 100.0, 1000)
        _, quiet_reviews = subject.apply_baseline_comparison(quiet, baseline)
        self.assertEqual([], [row for row in quiet_reviews
                              if row["kind"] == "inherited_contended_baseline"])
        self.assertNotIn("baseline_pair_contended",
                         quiet["performance"]["tools"][subject.TOOLS[0]])
        accepted_change = self._report(8, 100.0, 1000)
        accepted_change["production_identity"]["digest"] = "repaired-production"
        accepted_change["production_identity"]["modules"]["server_impl.py"] = "b"
        _, quiet_reviews = subject.apply_baseline_comparison(accepted_change, baseline)
        self.assertEqual([], [row for row in quiet_reviews
                              if row["kind"] == "inherited_contended_baseline"])

    def test_baseline_predating_the_full_distribution_fields_is_refused_with_recovery(self):
        # Wave 1wur7, delivery review QA-DEL-5: the migration case Requirement 1
        # names had no test, and without the typed guard an untyped TypeError
        # escaped instead of the operator-facing recovery message.
        baseline = self._report(8, 100.0, 1000)
        for tool in subject.TOOLS:
            baseline["performance"]["tools"][tool].pop("warm_floor_ms")
            baseline["performance"]["tools"][tool].pop("warm_median_ms")
        baseline["run_id"] = subject._compute_run_id(baseline)
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.apply_baseline_comparison(self._report(8, 100.0, 1000), baseline)
        self.assertEqual("invalid_baseline", caught.exception.code)
        self.assertIn("warm_floor_ms/warm_median_ms", caught.exception.message)
        self.assertIn("re-baseline with the current evaluator", caught.exception.message)

    def test_production_change_same_generation_latency_is_advisory(self):
        # Operator decision at wave 1wur7 close: latency is advisory for EVERY
        # comparison kind, including the one where a production change is the sole
        # difference between the arms. The clause is still computed and reported.
        baseline = self._report(8, 100.0, 1000)
        for tool in subject.TOOLS:
            baseline["performance"]["tools"][tool]["jitter_ratio"] = 0.01
        baseline["run_id"] = subject._compute_run_id(baseline)
        current = self._report(8, 140.0, 1000, floor=50.0, median=75.0)
        current["production_identity"]["digest"] = "repaired-production"
        current["production_identity"]["modules"]["server_impl.py"] = "b"
        violations, operator_reviews = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual("production_change_same_generation",
                         current["comparison"]["comparison_kind"])
        self.assertNotIn("latency_regression", {row["kind"] for row in violations})
        latency = [row for row in operator_reviews if row["kind"] == "latency_regression"]
        self.assertEqual(sorted(subject.TOOLS), sorted(row["tool"] for row in latency))
        for row in latency:
            self.assertEqual("operator_review", row["enforcement"])
            self.assertIn("advisory", row["reason"])
        for tool in subject.TOOLS:
            self.assertEqual("operator_review",
                             current["performance"]["tools"][tool]["latency_enforcement"])

    def test_single_run_baseline_is_accepted_at_the_floor(self):
        # Wave 1wuju (1wujt AC-1, AC-2): a receipt with no pair-derived jitter is
        # a baseline at the existing 25% floor on both inheriting kinds; contention
        # is recorded as not judged, and no within-run ratio is computed.
        baseline = self._report(8, 100.0, 1000)
        for tool in subject.TOOLS:
            baseline["performance"]["tools"][tool].pop("jitter_ratio", None)
        baseline["run_id"] = subject._compute_run_id(baseline)
        for kind in ("cross_generation", "production_change_same_generation"):
            with self.subTest(kind=kind):
                generation = 9 if kind == "cross_generation" else 8
                current = self._report(generation, 140.0, 1000, floor=50.0, median=75.0)
                if kind == "production_change_same_generation":
                    current["production_identity"]["digest"] = "repaired-production"
                    current["production_identity"]["modules"]["server_impl.py"] = "b"
                violations, operator_reviews = subject.apply_baseline_comparison(current, baseline)
                self.assertEqual(kind, current["comparison"]["comparison_kind"])
                self.assertNotIn("latency_regression", {row["kind"] for row in violations})
                for tool in subject.TOOLS:
                    perf = current["performance"]["tools"][tool]
                    self.assertEqual(0.25, perf["permitted_relative_regression"])
                    self.assertEqual("single_run_floor", perf["jitter_source"])
                    self.assertIsNone(perf["jitter_ratio"])
                    self.assertIsNone(perf["pair_contended"])
                    self.assertIs(False, perf["contention_judged"])
                    self.assertIn("no reference level", perf["contention_reason"])
                    self.assertNotIn("within_run_jitter_ratio", perf)
                # 40% over the 25% floor: computed and reported, advisory.
                self.assertEqual(sorted(subject.TOOLS),
                                 sorted(row["tool"] for row in operator_reviews
                                        if row["kind"] == "latency_regression"))

    def test_a_boolean_jitter_ratio_is_not_a_reference_level(self):
        # Delivery review CODE-DEL-2 / QA-DEL-1: the pair branch takes numeric
        # jitter only; a boolean `true` would otherwise read as 1.0 and widen the
        # band to 300%. It falls to the single-run floor instead.
        baseline = self._report(8, 100.0, 1000)
        for tool in subject.TOOLS:
            baseline["performance"]["tools"][tool]["jitter_ratio"] = True
        baseline["run_id"] = subject._compute_run_id(baseline)
        current = self._report(9, 140.0, 1000, floor=50.0, median=75.0)
        subject.apply_baseline_comparison(current, baseline)
        for tool in subject.TOOLS:
            perf = current["performance"]["tools"][tool]
            self.assertEqual("single_run_floor", perf["jitter_source"])
            self.assertEqual(0.25, perf["permitted_relative_regression"])
            self.assertIsNone(perf["jitter_ratio"])

    def test_the_disclosure_tool_mirrors_the_single_run_floor(self):
        # Delivery review ARCH-DEL-2: the data-level comparison tool reproduces
        # the signed evaluator's arithmetic, so a single-run baseline (the default
        # since 1wuju) takes the 0.25 floor there too instead of a skipped entry.
        import importlib.util
        path = Path(subject.__file__).resolve().parent / "benchmarks" / "compare_retrieval_receipts.py"
        spec = importlib.util.spec_from_file_location("compare_retrieval_receipts_under_test", path)
        tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool)
        baseline = self._report(8, 100.0, 1000)
        current = self._report(8, 110.0, 1000)
        for report in (baseline, current):
            for name in subject.TOOLS:
                by_split = report["metrics"]["by_tool"][name]["by_split"]
                by_split["calibration"] = dict(by_split["holdout"])
                report["performance"]["tools"][name].pop("jitter_ratio", None)
        violations, _floors, performance, _deltas = tool.compare(baseline, current)
        self.assertEqual([], [row for row in violations if row["kind"] == "latency_regression"], violations)
        for name in subject.TOOLS:
            self.assertEqual("single_run_floor", performance[name]["jitter_source"], performance[name])
            self.assertEqual(0.25, performance[name]["permitted_relative_regression"])
            self.assertIsNone(performance[name]["baseline_jitter_ratio"])
            self.assertEqual(125.0, performance[name]["warm_p95_threshold_ms"])

    def test_incompatible_store_attempt_or_runtime_invalidates_baseline(self):
        mutations = (
            lambda report: report["index_identity"].update(state_store_inode=99),
            lambda report: report["generation"].update(start_attempt_id="other", end_attempt_id="other"),
            lambda report: report["environment"].update(execution_providers=["CoreMLExecutionProvider"]),
            lambda report: report["environment"]["models"].update(reranker="other"),
            lambda report: report.pop("production_identity"),
            lambda report: report["production_identity"].pop("digest"),
            lambda report: report["environment"]["retrieval_toggles"].update(
                WAVEFOUNDRY_DISABLE_LEXICAL_FUSION=True),
            lambda report: report["environment"].pop("retrieval_toggles"),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                baseline = self._report(8, 100.0, 1000)
                current = self._report(8, 100.0, 1000)
                mutation(current)
                with self.assertRaises(subject.EvaluationInvalid) as caught:
                    subject.apply_baseline_comparison(current, baseline)
                self.assertEqual("invalid_baseline", caught.exception.code)

    def test_holdout_class_regression_is_not_masked_by_aggregate(self):
        baseline = self._report(8, 100.0, 1000)
        current = self._report(8, 100.0, 1000)
        for report in (baseline, current):
            for tool in subject.TOOLS:
                classes = report["metrics"]["by_tool"][tool]["by_split_and_class"]["holdout"]
                classes["class-b"] = dict(classes["class-a"])
                report["metrics"]["by_tool"][tool]["by_split"]["holdout"]["recall_at_10"] = 0.5
        current["metrics"]["by_tool"]["code_ask"]["by_split_and_class"]["holdout"] \
            ["class-a"]["recall_at_10"] = 0.0
        baseline["metrics"]["by_tool"]["code_ask"]["by_split_and_class"]["holdout"] \
            ["class-a"]["recall_at_10"] = 0.5
        baseline["run_id"] = subject._compute_run_id(baseline)
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        self.assertTrue(any(
            row.get("scope") == "class" and row.get("class") == "class-a" and
            row.get("metric") == "recall_at_10"
            for row in violations
        ))

    def test_critical_floor_and_targeted_improvement_reject_permanent_zero(self):
        baseline = self._report(8, 100.0, 1000)
        current = self._report(8, 100.0, 1000)
        for report in (baseline, current):
            report["cases"][0]["recall_at_10"] = 0.0
            report["metrics"]["by_tool"]["code_ask"]["by_split_and_class"]["holdout"] \
                ["class-a"]["recall_at_10"] = 0.0
        baseline["run_id"] = subject._compute_run_id(baseline)
        current["quality_gate"] = {"critical_floors": [
            {"scope": "fixture", "target": "fixture-a", "tool": "code_ask",
             "metric": "recall_at_10", "floor": 0.5},
            {"scope": "class", "target": "class-a", "tool": "code_ask",
             "metric": "recall_at_10", "floor": 0.0, "minimum_improvement": 0.1},
        ]}
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        self.assertIn("critical_quality_floor", {row["kind"] for row in violations})
        self.assertIn("targeted_improvement_unmet", {row["kind"] for row in violations})

    def test_fixture_rank_one_floor_reads_case_mrr_directly(self):
        report = self._report(8, 100.0, 1000)
        rule = {"scope": "fixture", "target": "fixture-a", "tool": "code_ask",
                "metric": "mrr_at_10", "floor": 1.0}
        self.assertEqual(1.0, subject._scope_metric(report, rule))
        report["cases"][0]["mrr_at_10"] = 0.5
        report["quality_gate"] = {"critical_floors": [rule]}
        violations = subject._quality_gate_violations(report, None)
        self.assertEqual("critical_quality_floor", violations[0]["kind"])


class EnvironmentSnapshotTests(unittest.TestCase):
    @staticmethod
    def _index_with_embedder(embedder):
        return SimpleNamespace(
            _meta={"project": {"model_versions": {"docs": "fake", "code": "fake"}}},
            _embedders={"fake-model": embedder},
            _reranker=None,
        )

    @staticmethod
    def _indexer():
        return SimpleNamespace(DOCS_MODEL="docs", CODE_MODEL="code", RERANKER_MODEL="reranker")

    def test_resolves_fastembed_nested_onnx_session_provider(self):
        session = SimpleNamespace(get_providers=lambda: ["CPUExecutionProvider"])
        fastembed = SimpleNamespace(model=SimpleNamespace(model=session))
        environment = subject._environment_snapshot(
            self._index_with_embedder(fastembed), self._indexer(),
        )
        self.assertEqual(["CPUExecutionProvider"], environment["execution_providers"])

    def test_providerless_fastembed_shape_is_invalid(self):
        providerless = SimpleNamespace(model=SimpleNamespace(model=SimpleNamespace()))
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject._environment_snapshot(
                self._index_with_embedder(providerless), self._indexer(),
            )
        self.assertEqual("execution_provider_unknown", caught.exception.code)


class MainCliTests(unittest.TestCase):
    @staticmethod
    def _indexer():
        return SimpleNamespace(
            SOURCE_CODE_EXTENSIONS={".json", ".py"},
            DOCS_TEXT_EXTENSIONS={".txt"},
            DOCS_EXTENSIONLESS_NAMES=set(),
            CODE_EXTENSIONLESS_NAMES=set(),
            _load_ignore_patterns=lambda root: [
                line.strip() for line in (root / ".aiignore").read_text().splitlines()
                if line.strip()
            ],
            # Wave 1wpig: the repository's real rule is a GLOB
            # (``docs/reports/retrieval-quality-*.json``), and the publish
            # temporary is only covered because of it.  An exact-membership fake
            # would let a temporary that the real ignore rule covers read as
            # self-contaminating, and would hide the case where it does not.
            _matches_ignore=lambda rel, patterns: any(
                fnmatch.fnmatch(rel, pattern) for pattern in patterns),
        )

    #: Confined report names used by these CLI tests. ``retrieval-quality-``
    #: prefixed direct children of ``<root>/docs/reports``, per 1wpaj R8.
    BASELINE_REL = "docs/reports/retrieval-quality-baseline-input.json"
    OUT_REL = "docs/reports/retrieval-quality-report.json"
    REPORTS_GLOB = "docs/reports/retrieval-quality-*.json"

    @classmethod
    def _tree(cls, root: Path, ignored: tuple[str, ...]):
        (root / ".aiignore").write_text("\n".join(ignored) + "\n", encoding="utf-8")
        (root / "docs" / "reports").mkdir(parents=True, exist_ok=True)
        fixtures = root / "fixtures.json"
        baseline = root / cls.BASELINE_REL
        out = root / cls.OUT_REL
        fixtures.write_text("{}", encoding="utf-8")
        baseline.write_text("{}", encoding="utf-8")
        return fixtures, baseline, out

    def test_exit_zero_for_baseline_and_pass_and_report_bytes_are_deterministic(self):
        for verdict, with_baseline in (("baseline", False), ("pass", True)):
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                fixtures, baseline, out = self._tree(
                    root, ("fixtures.json", self.REPORTS_GLOB),
                )
                report = {
                    "verdict": verdict, "schema": subject.REPORT_SCHEMA,
                    "payload": {"z": 2, "a": 1},
                }
                # An existing destination is NEVER overwritten, so byte
                # determinism is proved across two declared destinations rather
                # than by republishing over one.
                second_out = out.parent / "retrieval-quality-report-2.json"
                argv = ["--root", str(root), "--fixtures", str(fixtures), "--out", str(out)]
                if with_baseline:
                    argv.extend(("--baseline", str(baseline)))
                with patch.dict(sys.modules, {"indexer": self._indexer()}):
                    with patch.object(subject, "run_evaluation", return_value=report):
                        with patch("builtins.print"):
                            self.assertEqual(0, subject.main(argv))
                            first = out.read_bytes()
                            argv[argv.index(str(out))] = str(second_out)
                            self.assertEqual(0, subject.main(argv))
                            second = second_out.read_bytes()
                self.assertEqual(subject._stable_json_bytes(report, pretty=True), first)
                self.assertEqual(first, second)
                # The publish temporary never survives its own invocation.
                self.assertEqual(
                    [], [name for name in os.listdir(out.parent)
                         if subject._REPORT_TEMP_RE.match(name)])

    def test_exit_one_for_fail_and_operator_review_required(self):
        for verdict in ("fail", "operator_review_required"):
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                fixtures, baseline, out = self._tree(
                    root, ("fixtures.json", self.REPORTS_GLOB),
                )
                argv = [
                    "--root", str(root), "--fixtures", str(fixtures), "--out", str(out),
                    "--baseline", str(baseline),
                ]
                with patch.dict(sys.modules, {"indexer": self._indexer()}):
                    with patch.object(subject, "run_evaluation", return_value={
                        "schema": subject.REPORT_SCHEMA, "verdict": verdict,
                    }):
                        with patch("builtins.print"):
                            self.assertEqual(1, subject.main(argv))

    def test_exit_two_invalid_writes_stable_machine_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixtures, _, out = self._tree(root, ("fixtures.json", self.REPORTS_GLOB))
            reason = subject.EvaluationInvalid("broken_fixture", "fixture is invalid")
            with patch.dict(sys.modules, {"indexer": self._indexer()}):
                with patch.object(subject, "run_evaluation", side_effect=reason):
                    with patch("builtins.print"):
                        self.assertEqual(2, subject.main([
                            "--root", str(root), "--fixtures", str(fixtures), "--out", str(out),
                        ]))
            expected = subject._minimal_invalid_report(reason)
            self.assertEqual(subject._stable_json_bytes(expected, pretty=True), out.read_bytes())

    def test_fixture_output_and_baseline_must_be_excluded_before_execution(self):
        cases = (
            ("fixtures.json", False),
            (self.OUT_REL, False),
            (self.BASELINE_REL, True),
        )
        all_patterns = ("fixtures.json", self.OUT_REL, self.BASELINE_REL)
        for unignored, include_baseline in cases:
            with self.subTest(unignored=unignored), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                ignored = tuple(name for name in all_patterns if name != unignored)
                fixtures, baseline, out = self._tree(root, ignored)
                argv = ["--root", str(root), "--fixtures", str(fixtures), "--out", str(out)]
                if include_baseline:
                    argv.extend(("--baseline", str(baseline)))
                with patch.dict(sys.modules, {"indexer": self._indexer()}):
                    with patch.object(subject, "run_evaluation") as run:
                        with patch("builtins.print"):
                            self.assertEqual(2, subject.main(argv))
                run.assert_not_called()
                self.assertFalse(out.exists(), "self-contaminating preflight must not write output")


class FullRunnerTests(unittest.TestCase):
    class FakeStateStore:
        def __init__(self, *, drift_after: int | None = None):
            self.reads = 0
            self.drift_after = drift_after

        @staticmethod
        def state_store_path(index_dir: Path) -> Path:
            return index_dir / "index-state.sqlite"

        def read_build_state(self, _index_dir: Path):
            self.reads += 1
            generation = 2 if self.drift_after is not None and self.reads >= self.drift_after else 1
            return {"attempt_id": f"attempt-{generation}", "status": "complete",
                    "generation": generation, "started_at": None, "completed_at": None}

        @staticmethod
        def registry_chunk_count(_index_dir: Path, _table: str) -> int:
            return 12

    class FakeIndex:
        def __init__(self, root: Path):
            self.root = root
            self._meta = {"project": {"model_versions": {"docs": "fake", "code": "fake"}}}
            session = SimpleNamespace(get_providers=lambda: ["CPUExecutionProvider"])
            self._embedders = {"fake-model": SimpleNamespace(model=SimpleNamespace(model=session))}
            self._reranker = None

        @staticmethod
        def docs_health():
            return {
                "semantic_ready": True,
                "readiness_overview": "ready",
                "stale_layers": [],
                "missing_layers": [],
            }

    class FakeServer:
        class SemanticModelUnavailableOfflineError(RuntimeError):
            pass

        WaveIndex = None

        @staticmethod
        def _response(index, query, tool):
            if "wavefoundry-retrieval-eval-" in str(index.root):
                return {"status": "ok", "data": {
                    "search_mode": "lexical_fallback", "fallback_reason": "model_unavailable",
                    "citations" if tool == "code_ask" else "results": [], "confidence": "low",
                }}
            absent = query.startswith("absent topic")
            key = "citations" if tool == "code_ask" else "results"
            data = {
                key: [] if absent else [{"path": "target.py", "excerpt": "needle", "lines": [1, 1]}],
                "question_type": "explanatory", "confidence": "low" if absent else "high",
                "search_mode": "hybrid", "fallback_reason": None,
            }
            return {"status": "ok", "data": data, "diagnostics": [], "next_tools": []}

        @classmethod
        def code_ask_response(cls, index, root, question, rerank="agent", epoch_state=None):
            return cls._response(index, question, "code_ask")

        @classmethod
        def code_search_response(cls, index, query, limit=10, epoch_state=None):
            return cls._response(index, query, "code_search")

        @classmethod
        def docs_search_response(cls, index, query, limit=10, epoch_state=None):
            return cls._response(index, query, "docs_search")

        @staticmethod
        def code_lexical_response(root, query="", limit=10):
            absent = query.startswith("absent topic")
            return {"status": "ok", "data": {
                "results": [] if absent else [{"path": "target.py", "text": "needle", "lines": [1, 1]}]
            }}

    def _tree(self, root: Path):
        index_dir = root / ".wavefoundry" / "index"
        import index_state_store as native_state
        store = native_state.IndexStateStore(index_dir)
        try:
            store.ensure_current()
        finally:
            store.close()
        native_state.write_build_bookkeeping(index_dir, {"content": ["docs", "code"]})
        (root / "target.py").write_text("needle\n", encoding="utf-8")
        scripts = root / "scripts"
        scripts.mkdir()
        for name in subject.PRODUCTION_RETRIEVAL_MODULES:
            (scripts / name).write_text(f"# fake {name}\n", encoding="utf-8")
        (scripts / "chunker.py").write_text('CHUNKER_VERSION = "7"\n', encoding="utf-8")
        fixture_path = root / "fixtures.json"
        fixture_path.write_text(json.dumps(_valid_payload()), encoding="utf-8")
        return fixture_path

    def _modules(self, state_store, root: Path | None = None):
        server = self.FakeServer()
        server.WaveIndex = self.FakeIndex
        if root is not None:
            server.__file__ = str(root / "scripts" / "server_impl.py")
        indexer = SimpleNamespace(DOCS_MODEL="docs-model", CODE_MODEL="code-model",
                                  RERANKER_MODEL="reranker-model")
        return server, state_store, indexer

    def setUp(self):
        # The framework test runner pins retrieval kill switches (for example
        # WAVEFOUNDRY_DISABLE_RERANKER) for hermetic runs; the receipt records the
        # EFFECTIVE state, so these runner tests start from every switch cleared.
        self._env = patch.dict(os.environ, {name: "" for name in subject.RETRIEVAL_TOGGLE_ENVS})
        self._env.start()
        self.addCleanup(self._env.stop)

    def test_monitor_free_runner_emits_v1_report_and_degraded_probe(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixtures = self._tree(root)
            modules = self._modules(self.FakeStateStore(), root)
            ticks = iter(range(1_700_000_000, 1_700_100_000))
            report = subject.run_evaluation(root, fixtures, server=modules[0],
                                            state_store=modules[1], indexer=modules[2],
                                            wall_clock=lambda: float(next(ticks)))
            expected_identity = subject._production_identity(root / "scripts")
        self.assertEqual(subject.REPORT_SCHEMA, report["schema"])
        self.assertEqual("baseline", report["verdict"])
        self.assertTrue(report["degraded_mode_probe"]["passed"])
        self.assertTrue(report["degraded_mode_probe"]["disposable_store"])
        self.assertEqual(1, report["generation"]["start"])
        self.assertEqual(3, report["performance"]["protocol"]["measured_repetitions_per_applicable_pair"])
        self.assertEqual({**expected_identity, "end_digest_verified": True},
                         report["production_identity"])
        self.assertEqual(64, len(report["production_identity"]["digest"]))
        self.assertEqual({"chunker": "7", "walker": None, "graph_builder": None,
                          "cluster_builder": None},
                         report["production_identity"]["versions"])
        self.assertEqual("2023-11-14T22:13:20Z", report["run_time"]["started_at"])
        self.assertEqual("2023-11-14T22:13:21Z", report["run_time"]["finished_at"])
        self.assertEqual(1.0, report["run_time"]["duration_seconds"])
        self.assertEqual({}, report["anchor_resolution"])

    def _run(self, payload=None):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixtures = self._tree(root)
            if payload is not None:
                fixtures.write_text(json.dumps(payload), encoding="utf-8")
            modules = self._modules(self.FakeStateStore(), root)
            return subject.run_evaluation(root, fixtures, server=modules[0],
                                          state_store=modules[1], indexer=modules[2])

    def test_receipt_carries_the_warm_distribution_beside_the_p95(self):
        # Wave 1wur7 (1wuuh Requirement 1): the comparison reads the floor and
        # median off the performance block, so they travel in the receipt and the
        # comparison never has to reach back into ``cases[].repetitions[]``.
        report = self._run()
        protocol = report["performance"]["protocol"]
        self.assertEqual(subject.PAIR_JITTER_THRESHOLD, protocol["pair_jitter_threshold"])
        self.assertEqual(subject.MIN_WARM_SAMPLES, protocol["minimum_warm_samples"])
        # QA-DEL-3: an ordering assertion alone let `warm_floor_ms` be recorded as
        # the median. The oracle is the run's own recorded samples.
        samples: dict[str, list[float]] = {}
        for case in report["cases"]:
            for repetition in case.get("repetitions") or []:
                samples.setdefault(case["tool"], []).append(float(repetition["elapsed_ms"]))
        for tool in subject.TOOLS:
            with self.subTest(tool=tool):
                perf = report["performance"]["tools"][tool]
                recorded = samples[tool]
                self.assertEqual(len(recorded), perf["sample_count"])
                self.assertAlmostEqual(min(recorded), perf["warm_floor_ms"], places=5)
                self.assertAlmostEqual(statistics.median(recorded), perf["warm_median_ms"],
                                       places=5)
                self.assertLess(perf["warm_floor_ms"], perf["warm_median_ms"],
                                "a real floor is strictly below the median on this corpus")
                self.assertLessEqual(perf["warm_median_ms"], perf["warm_p95_ms"])
                self.assertEqual(subject.MIN_WARM_SAMPLES, perf["minimum_warm_samples"])
                self.assertFalse(perf["small_sample_estimate"])
        self.assertEqual("baseline", report["verdict"])
        self.assertEqual([], report["operator_review_reasons"])

    def test_small_sample_p95_is_labelled_and_routed_but_nine_samples_are_not(self):
        # Wave 1wur7 (1wuuh AC-3).  ``docs_search`` carries exactly three
        # applicable fixtures against the frozen corpus, so it sits permanently at
        # 3 * MEASURED_REPETITIONS = 9 warm samples.  The declared minimum is
        # pinned AT that standing count: nine is labelled as a maximum-not-tail
        # estimate but is NOT escalated, because escalating a value the corpus
        # makes permanent would put a clean ``pass`` out of reach forever.  A tool
        # BELOW the minimum is labelled and routed to operator review.
        payload = _valid_payload()
        quota, used = {"code_lexical": 2, "docs_search": 3}, {"code_lexical": 0, "docs_search": 0}
        for row in payload["fixtures"]:
            tool = row["applicable_tools"][0]
            if tool in quota and used[tool] < quota[tool]:
                used[tool] += 1
                continue
            if tool in quota:
                row["applicable_tools"] = ["code_ask"]
                row["excluded_tools"] = {name: "outside this tool's public contract"
                                         for name in subject.TOOLS if name != "code_ask"}
        report = self._run(payload)
        tools = report["performance"]["tools"]
        self.assertEqual(9, tools["docs_search"]["sample_count"])
        # QA-DEL-12: the Decision Log's contract is "pinned AT the standing count,
        # not above it", so the derivation is asserted, not just the interval.
        self.assertEqual(3 * subject.MEASURED_REPETITIONS, subject.MIN_WARM_SAMPLES)
        self.assertEqual(tools["docs_search"]["sample_count"], subject.MIN_WARM_SAMPLES)
        self.assertFalse(tools["docs_search"]["small_sample_estimate"])
        self.assertTrue(tools["docs_search"]["p95_is_maximum"],
                        "nine samples make nearest-rank p95 the maximum; the receipt says so")
        self.assertEqual(6, tools["code_lexical"]["sample_count"])
        self.assertTrue(tools["code_lexical"]["small_sample_estimate"])
        self.assertEqual([{"kind": "small_sample_warm_p95", "tool": "code_lexical",
                           "sample_count": 6,
                           "minimum_warm_samples": subject.MIN_WARM_SAMPLES}],
                         report["operator_review_reasons"])
        self.assertEqual("operator_review_required", report["verdict"])

    def test_comparison_runs_end_to_end_and_a_contended_baseline_is_reported(self):
        # QA-DEL-13: the comparison path was only ever exercised by calling
        # `apply_baseline_comparison` directly; nothing drove `run_evaluation`
        # with a baseline and read the resulting verdict off a real receipt.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixtures = self._tree(root)
            modules = self._modules(self.FakeStateStore(), root)
            baseline_path = root / "baseline.json"
            first = subject.run_evaluation(root, fixtures, server=modules[0],
                                           state_store=modules[1], indexer=modules[2])
            self.assertEqual("baseline", first["verdict"])
            subject.write_report(baseline_path, first)
            second = subject.run_evaluation(root, fixtures, baseline_path=baseline_path,
                                            server=modules[0], state_store=modules[1],
                                            indexer=modules[2])
            self.assertEqual("same_generation_pair", second["comparison"]["comparison_kind"])
            self.assertIn(second["verdict"], {"pass", "operator_review_required"})
            # A later generation inherits the recorded pair's jitter, and a pair
            # recorded under load is REPORTED as that band (operator decision at the
            # wave 1wur7 close; ARCH-DEL-6 made the flag read), end to end.
            pair_path = root / "pair.json"
            # The fake corpus runs in microseconds, so its own floor/median jitter
            # is genuinely contended. Normalise the flag to False for the accepted
            # arm so the two arms differ only in the property under test.
            quiet_pair = json.loads(json.dumps(second))
            for tool in subject.TOOLS:
                quiet_pair["performance"]["tools"][tool]["pair_contended"] = False
            quiet_pair["run_id"] = subject._compute_run_id(quiet_pair)
            subject.write_report(pair_path, quiet_pair)
            next_generation = self.FakeStateStore()
            next_generation.read_build_state = lambda _dir: {  # type: ignore[method-assign]
                "attempt_id": "attempt-2", "status": "complete", "generation": 2,
                "started_at": None, "completed_at": None}
            third = subject.run_evaluation(root, fixtures, baseline_path=pair_path,
                                           server=modules[0], state_store=next_generation,
                                           indexer=modules[2])
            self.assertEqual("cross_generation", third["comparison"]["comparison_kind"])
            contended = json.loads(pair_path.read_text(encoding="utf-8"))
            for tool in subject.TOOLS:
                contended["performance"]["tools"][tool]["pair_contended"] = True
            contended["run_id"] = subject._compute_run_id(contended)
            subject.write_report(pair_path, contended)
            fourth = subject.run_evaluation(root, fixtures, baseline_path=pair_path,
                                            server=modules[0], state_store=next_generation,
                                            indexer=modules[2])
            self.assertEqual("operator_review_required", fourth["verdict"])
            self.assertEqual(sorted(subject.TOOLS),
                             sorted(row["tool"] for row in fourth["operator_review_reasons"]
                                    if row["kind"] == "inherited_contended_baseline"))

    def test_active_retrieval_toggle_requires_operator_review_and_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixtures = self._tree(root)
            modules = self._modules(self.FakeStateStore(), root)
            with patch.dict(os.environ, {"WAVEFOUNDRY_DISABLE_LEXICAL_FUSION": "1"}):
                report = subject.run_evaluation(root, fixtures, server=modules[0],
                                                state_store=modules[1], indexer=modules[2])
        self.assertTrue(report["environment"]["retrieval_toggles"]["WAVEFOUNDRY_DISABLE_LEXICAL_FUSION"])
        self.assertFalse(report["environment"]["retrieval_toggles"]["WAVEFOUNDRY_DISABLE_RERANKER"])
        self.assertEqual("operator_review_required", report["verdict"])
        self.assertIn({"kind": "retrieval_toggle_active",
                       "toggles": ["WAVEFOUNDRY_DISABLE_LEXICAL_FUSION"]},
                      report["operator_review_reasons"])

    def test_production_module_edit_during_run_invalidates_the_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixtures = self._tree(root)
            modules = self._modules(self.FakeStateStore(), root)
            original = subject._production_identity
            calls = []

            def drifting(scripts_dir, repo_root=None):
                calls.append(1)
                if len(calls) == 2:
                    (scripts_dir / "server_impl.py").write_text("# edited mid-run\n", encoding="utf-8")
                return original(scripts_dir, repo_root)

            with patch.object(subject, "_production_identity", side_effect=drifting):
                with self.assertRaises(subject.EvaluationInvalid) as caught:
                    subject.run_evaluation(root, fixtures, server=modules[0],
                                           state_store=modules[1], indexer=modules[2])
        self.assertEqual("production_drift", caught.exception.code)

    def test_git_binding_discloses_head_match_and_dirty_worktree(self):
        import subprocess as sp
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scripts = root / "wf-scripts"
            scripts.mkdir()
            env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
                   "HOME": temp, "PATH": os.environ.get("PATH", "")}
            prefix = subject.PRODUCTION_MODULE_PREFIX
            (root / prefix).mkdir(parents=True)
            for name in subject.PRODUCTION_RETRIEVAL_MODULES:
                (root / prefix / name).write_text(f"# {name} v1\n", encoding="utf-8")
                (scripts / name).write_text(f"# {name} v1\n", encoding="utf-8")
            for args in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "base"]):
                sp.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)
            identity = subject._production_identity(scripts, root)
            self.assertEqual(40, len(identity["git"]["head"]))
            self.assertTrue(all(identity["git"]["matches_head"].values()))
            self.assertFalse(identity["git"]["worktree_dirty"])
            # A scratch copy of an OLD server_impl against a dirty tree is disclosed as such.
            (root / prefix / "server_impl.py").write_text("# server_impl v2\n", encoding="utf-8")
            identity = subject._production_identity(scripts, root)
            self.assertTrue(identity["git"]["matches_head"]["server_impl.py"],
                            "the served copy still equals HEAD even though the tree moved on")
            self.assertTrue(identity["git"]["worktree_dirty"])
            served_current = subject._production_identity(root / prefix, root)
            self.assertFalse(served_current["git"]["matches_head"]["server_impl.py"])
            # Reverification RV-4: the blob is compared as raw bytes, so a CRLF module
            # that equals HEAD byte-for-byte is not reported as a mismatch.
            crlf = b"# chunker v1\r\nCHUNKER_VERSION = \"7\"\r\n"
            (root / prefix / "chunker.py").write_bytes(crlf)
            (scripts / "chunker.py").write_bytes(crlf)
            for args in (["add", "."], ["commit", "-q", "-m", "crlf"]):
                sp.run(["git", "-C", str(root), *args], check=True, env=env, capture_output=True)
            identity = subject._production_identity(scripts, root)
            self.assertTrue(identity["git"]["matches_head"]["chunker.py"])
        self.assertEqual({"head": None, "matches_head": {}, "worktree_dirty": None},
                         subject._git_binding(None, {}))

    def test_runner_without_identifiable_production_modules_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixtures = self._tree(root)
            modules = self._modules(self.FakeStateStore())
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.run_evaluation(root, fixtures, server=modules[0],
                                       state_store=modules[1], indexer=modules[2])
            self.assertEqual("production_unidentifiable", caught.exception.code)
            (root / "scripts" / "server_impl.py").unlink()
            modules = self._modules(self.FakeStateStore(), root)
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.run_evaluation(root, fixtures, server=modules[0],
                                       state_store=modules[1], indexer=modules[2])
            self.assertEqual("production_unreadable", caught.exception.code)

    def test_evaluation_index_blocks_known_bad_background_prewarm_sentinel(self):
        calls = []

        class ProductionIndex:
            def __init__(self, root):
                self.root = root

            def _start_background_model_downloads(self):
                calls.append("known-bad-background-start")

            def _start_background_model_downloads_after_startup(self):
                self._start_background_model_downloads()

            def search_docs(self):
                self._start_background_model_downloads_after_startup()

        ProductionIndex(Path(".")).search_docs()
        self.assertEqual(["known-bad-background-start"], calls)
        calls.clear()
        evaluation_index = subject._new_evaluation_index(
            SimpleNamespace(WaveIndex=ProductionIndex), Path("."),
        )
        evaluation_index.search_docs()
        evaluation_index._start_background_model_downloads()
        self.assertEqual([], calls)

    def test_generation_change_invalidates_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixtures = self._tree(root)
            modules = self._modules(self.FakeStateStore(drift_after=3), root)
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.run_evaluation(root, fixtures, server=modules[0],
                                       state_store=modules[1], indexer=modules[2])
        self.assertEqual("generation_drift", caught.exception.code)


class RecordedWarmSamplePairTests(unittest.TestCase):
    """Wave 1wur7 (1wuuh AC-1, AC-2): the jitter estimator judged against DATA.

    The oracle is the raw warm-sample arrays recorded by the real producer and
    committed under ``fixtures/retrieval_eval/warm_sample_pairs.json``, never a
    hand-written percentage chosen to match an answer.  Replay is legitimate
    after this change because the comparator compares report to report and never
    checks either side against the running module's identity.
    """

    def _pair(self, pair_name: str):
        arms = WARM_SAMPLE_PAIRS[pair_name]
        builder = BaselineComparisonTests()
        baseline = builder._report(8, 100.0, 1000)
        current = builder._report(8, 100.0, 1000)
        for report, arm in ((baseline, "arm_a"), (current, "arm_b")):
            for tool in subject.TOOLS:
                samples = arms[arm][tool]
                report["performance"]["tools"][tool].update({
                    "sample_count": len(samples),
                    "warm_p95_ms": subject._nearest_rank_p95(samples),
                    "warm_floor_ms": subject._sample_floor(samples),
                    "warm_median_ms": subject._sample_median(samples),
                })
        baseline["run_id"] = subject._compute_run_id(baseline)
        current["operator_review_reasons"] = []
        return baseline, current

    @staticmethod
    def _nearest_rank(ordered):
        """Nearest-rank p95, restated here so the oracle is independent."""
        import math as _math
        return ordered[max(1, _math.ceil(0.95 * len(ordered))) - 1]

    @classmethod
    def _independent_jitter(cls, arm_a, arm_b, statistic):
        """Recompute one paired statistic without reusing the evaluator's helpers."""
        left, right = statistic(sorted(arm_a)), statistic(sorted(arm_b))
        return abs(left - right) / min(left, right)

    def test_contended_pair_is_refused_and_names_every_over_threshold_tool(self):
        baseline, current = self._pair("contended_1wpif")
        _, operator_reviews = subject.apply_baseline_comparison(current, baseline)
        contended = [row for row in operator_reviews
                     if row["kind"] == "contended_baseline_pair"]
        self.assertEqual(sorted(subject.TOOLS), sorted(row["tool"] for row in contended),
                         "every over-threshold tool is named, not one")
        for row in contended:
            self.assertEqual(subject.PAIR_JITTER_THRESHOLD, row["threshold_ratio"])
            self.assertGreater(max(row["floor_jitter_ratio"], row["median_jitter_ratio"]),
                               subject.PAIR_JITTER_THRESHOLD)
        for tool in subject.TOOLS:
            self.assertTrue(current["performance"]["tools"][tool]["pair_contended"])
        # The reasons reach the same list object the verdict reads.
        self.assertEqual({"contended_baseline_pair"},
                         {row["kind"] for row in current["operator_review_reasons"]
                          if row["kind"] == "contended_baseline_pair"})

    def test_a_recorded_pair_is_preferred_over_the_single_run_floor(self):
        # Wave 1wuju (1wujt AC-2): when the baseline carries pair-derived jitter
        # the band comes from it, not from the floor; pinned on the recorded
        # quiet pair rather than on a hand-written ratio.
        baseline, current = self._pair("quiet_1seaw_baseline")
        subject.apply_baseline_comparison(current, baseline)
        current["run_id"] = subject._compute_run_id(current)
        later = BaselineComparisonTests()._report(9, 100.0, 1000)
        subject.apply_baseline_comparison(later, current)
        for tool in subject.TOOLS:
            perf = later["performance"]["tools"][tool]
            recorded = current["performance"]["tools"][tool]["jitter_ratio"]
            self.assertEqual("baseline_same_generation_pair", perf["jitter_source"])
            self.assertEqual(recorded, perf["jitter_ratio"])
            self.assertEqual(round(max(0.25, 3.0 * recorded), 8),
                             perf["permitted_relative_regression"])
            self.assertNotIn("contention_judged", perf)

    def test_quiet_pairs_of_the_same_fixtures_are_promotable(self):
        for pair_name in ("quiet_1seaw_baseline", "quiet_before_1seas"):
            with self.subTest(pair=pair_name):
                baseline, current = self._pair(pair_name)
                _, operator_reviews = subject.apply_baseline_comparison(current, baseline)
                self.assertEqual([], [row for row in operator_reviews
                                      if row["kind"] == "contended_baseline_pair"])
                for tool in subject.TOOLS:
                    self.assertFalse(current["performance"]["tools"][tool]["pair_contended"])

    def test_tail_noise_alone_does_not_make_a_quiet_pair_contended(self):
        # ``before-1seas`` code_lexical carries 10.70% p95 jitter against a 0.74%
        # floor.  That is why the promotability rule reads the floor and median.
        arms = WARM_SAMPLE_PAIRS["quiet_before_1seas"]
        a, b = arms["arm_a"]["code_lexical"], arms["arm_b"]["code_lexical"]
        p95_jitter = self._independent_jitter(a, b, self._nearest_rank)
        floor_jitter = self._independent_jitter(a, b, lambda v: v[0])
        self.assertGreater(p95_jitter, subject.PAIR_JITTER_THRESHOLD)
        self.assertLess(floor_jitter, subject.PAIR_JITTER_THRESHOLD)
        baseline, current = self._pair("quiet_before_1seas")
        subject.apply_baseline_comparison(current, baseline)
        perf = current["performance"]["tools"]["code_lexical"]
        self.assertFalse(perf["pair_contended"])
        self.assertAlmostEqual(p95_jitter, perf["jitter_components"]["p95"], places=6)

    def test_full_distribution_jitter_reproduces_the_understated_p95_estimate(self):
        import statistics as _statistics

        arms = WARM_SAMPLE_PAIRS["contended_1wpif"]
        a, b = arms["arm_a"]["code_search"], arms["arm_b"]["code_search"]
        expected_floor = self._independent_jitter(a, b, lambda v: v[0])
        expected_median = self._independent_jitter(a, b, _statistics.median)
        expected_p95 = self._independent_jitter(a, b, self._nearest_rank)
        baseline, current = self._pair("contended_1wpif")
        subject.apply_baseline_comparison(current, baseline)
        components = current["performance"]["tools"]["code_search"]["jitter_components"]
        self.assertAlmostEqual(expected_floor, components["floor"], places=6)
        self.assertAlmostEqual(expected_median, components["median"], places=6)
        self.assertAlmostEqual(expected_p95, components["p95"], places=6)
        # The reported pair jitter is the stable-statistic maximum, and the
        # p95-only estimator this change replaces understated it several-fold.
        self.assertAlmostEqual(max(expected_floor, expected_median),
                               current["performance"]["tools"]["code_search"]["jitter_ratio"],
                               places=6)
        self.assertGreater(max(expected_floor, expected_median), 4.0 * expected_p95)
        # QA-DEL-4: AC-2 names these magnitudes, so they are asserted rather than
        # left to move with the fixture. A synthetic replacement of the arrays
        # now fails here instead of passing silently.
        self.assertAlmostEqual(0.1179, expected_floor, places=3)
        self.assertAlmostEqual(0.1810, expected_median, places=3)
        self.assertAlmostEqual(0.0256, expected_p95, places=3)

    def test_pair_jitter_takes_the_floor_when_the_floor_dominates(self):
        # QA-DEL-6: `code_search`'s median exceeds its floor, so asserting only
        # that tool left a median-only estimator alive. Contended `code_ask` is
        # the tool where the FLOOR dominates (25.03% vs 11.27%), which is the
        # half of Requirement 1 the change exists to introduce.
        import statistics as _statistics

        arms = WARM_SAMPLE_PAIRS["contended_1wpif"]
        a, b = arms["arm_a"]["code_ask"], arms["arm_b"]["code_ask"]
        expected_floor = self._independent_jitter(a, b, lambda v: v[0])
        expected_median = self._independent_jitter(a, b, _statistics.median)
        self.assertGreater(expected_floor, expected_median,
                           "code_ask is the floor-dominant tool in this pair")
        baseline, current = self._pair("contended_1wpif")
        subject.apply_baseline_comparison(current, baseline)
        perf = current["performance"]["tools"]["code_ask"]
        self.assertAlmostEqual(expected_floor, perf["jitter_ratio"], places=6)
        self.assertAlmostEqual(0.2503, expected_floor, places=3)


class IndexIdentityBindingTests(unittest.TestCase):
    """Wave 1wur7 (1wtpl): index identity is compared per comparison kind."""

    def _reports(self, baseline_generation: int, current_generation: int):
        builder = BaselineComparisonTests()
        baseline = builder._report(baseline_generation, 100.0, 1000)
        for tool in subject.TOOLS:
            baseline["performance"]["tools"][tool]["jitter_ratio"] = 0.01
        baseline["run_id"] = subject._compute_run_id(baseline)
        return baseline, builder._report(current_generation, 100.0, 1000)

    def test_cross_generation_pair_differing_only_in_store_inode_is_not_refused(self):
        # AC-1.  The identity shape is the one wave 1wpif recorded: the state
        # store file was recreated by a controlled rebuild (inode 634552732 ->
        # 635682939) while every other binding matched.  Those values are the
        # fixture's provenance, not a machine-specific contract.
        baseline, current = self._reports(8, 9)
        baseline["index_identity"]["state_store_inode"] = 634552732
        baseline["run_id"] = subject._compute_run_id(baseline)
        current["index_identity"]["state_store_inode"] = 635682939
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual("cross_generation", current["comparison"]["comparison_kind"])
        self.assertEqual([], violations)

    def test_cross_generation_still_refuses_a_different_repository_or_index(self):
        for key, value in (("repository_root", "/other"), ("repository_inode", 999),
                           ("repository_device", 999), ("index_directory", "/other/index"),
                           ("state_store", "/other/index/index-state.sqlite")):
            with self.subTest(key=key):
                baseline, current = self._reports(8, 9)
                current["index_identity"][key] = value
                with self.assertRaises(subject.EvaluationInvalid) as caught:
                    subject.apply_baseline_comparison(current, baseline)
                self.assertEqual("invalid_baseline", caught.exception.code)
                self.assertIn(key, caught.exception.message)

    def test_same_generation_pair_still_requires_one_physical_store(self):
        # AC-2, the built-in known-bad: the loosening must not reach the kind
        # where "one frozen physical store" is what makes jitter meaningful.
        for key in ("state_store_inode", "state_store_device"):
            with self.subTest(key=key):
                baseline, current = self._reports(8, 8)
                current["index_identity"][key] = 99
                with self.assertRaises(subject.EvaluationInvalid) as caught:
                    subject.apply_baseline_comparison(current, baseline)
                self.assertEqual("invalid_baseline", caught.exception.code)
                self.assertIn(key, caught.exception.message)

    def test_identity_contract_covers_every_field_the_recorder_emits(self):
        # Splitting the comparison into named keys would let a field added to
        # `_index_identity` later go silently uncompared. The contract tuple is
        # the single source of truth, so a new field must join it or fail here.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            index_dir = root / ".wavefoundry" / "index"
            index_dir.mkdir(parents=True)
            store = index_dir / "index-state.sqlite"
            store.write_bytes(b"")
            state_store = SimpleNamespace(state_store_path=lambda _dir: store)
            emitted = subject._index_identity(root, index_dir, state_store)
        self.assertEqual(set(subject.SAME_GENERATION_INDEX_IDENTITY_KEYS), set(emitted))
        self.assertTrue(
            set(subject.CROSS_GENERATION_INDEX_IDENTITY_KEYS)
            < set(subject.SAME_GENERATION_INDEX_IDENTITY_KEYS))
        self.assertEqual(
            {"state_store_device", "state_store_inode"},
            set(subject.SAME_GENERATION_INDEX_IDENTITY_KEYS)
            - set(subject.CROSS_GENERATION_INDEX_IDENTITY_KEYS))

    def test_epoch_is_validated_before_the_index_identity_comparison(self):
        # Requirement 5: the reordering changes which invalid_baseline message a
        # doubly incompatible report returns first.  Pinned, not discovered.
        baseline, current = self._reports(8, 8)
        current["index_identity"]["state_store_inode"] = 99
        current["generation"].update(start_status="running")
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.apply_baseline_comparison(current, baseline)
        self.assertIn("build status is not complete", caught.exception.message)
        self.assertNotIn("state_store_inode", caught.exception.message)


class ClusterProductionIdentityTests(unittest.TestCase):
    """Wave 1wpig (1wpaj Requirement 8): cluster module/version drift MOVES
    production identity.

    The clusters artifact carries the communities and the betweenness ranking
    that ``wf_graph_report`` serves, so a change there changes what the measured
    public paths return.  Before this change a cluster-only edit produced two
    reports with an identical ``production_identity.digest``, which is exactly
    the "before/after receipt" claim the digest exists to make.
    """

    def _scripts(self, root: Path) -> Path:
        scripts = root / "scripts"
        scripts.mkdir()
        for name in subject.PRODUCTION_RETRIEVAL_MODULES:
            (scripts / name).write_text(f"# fake {name}\n", encoding="utf-8")
        (scripts / "graph_cluster.py").write_text(
            'CLUSTER_BUILDER_VERSION = "12"  # trailing prose\n', encoding="utf-8")
        return scripts

    def test_cluster_module_is_part_of_the_production_module_set(self):
        self.assertIn("graph_cluster.py", subject.PRODUCTION_RETRIEVAL_MODULES)
        self.assertEqual(("graph_cluster.py", "CLUSTER_BUILDER_VERSION"),
                         subject.PRODUCTION_VERSION_CONSTANTS["cluster_builder"])

    def test_cluster_module_edit_moves_the_production_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            scripts = self._scripts(Path(temp))
            before = subject._production_identity(scripts)
            (scripts / "graph_cluster.py").write_text(
                'CLUSTER_BUILDER_VERSION = "12"  # trailing prose, edited\n', encoding="utf-8")
            after = subject._production_identity(scripts)
        self.assertNotEqual(before["digest"], after["digest"])
        self.assertIn("graph_cluster.py", before["modules"])

    def test_cluster_version_bump_is_reported_in_the_version_block(self):
        with tempfile.TemporaryDirectory() as temp:
            scripts = self._scripts(Path(temp))
            self.assertEqual("12", subject._production_identity(scripts)["versions"]["cluster_builder"])
            (scripts / "graph_cluster.py").write_text(
                'CLUSTER_BUILDER_VERSION = "13"\n', encoding="utf-8")
            self.assertEqual("13", subject._production_identity(scripts)["versions"]["cluster_builder"])

    def test_shipped_cluster_module_exposes_a_readable_builder_version(self):
        # The constant is read off the SHIPPED module, not a fixture: a rename or
        # a switch to a non-string literal would silently return None.
        scripts = SCRIPTS
        self.assertIsNotNone(
            subject._module_constant(scripts / "graph_cluster.py", "CLUSTER_BUILDER_VERSION"),
            "CLUSTER_BUILDER_VERSION must stay a readable string literal")


class ProductionTuningEnvironmentTests(unittest.TestCase):
    """Wave 1wpig (1wpaj Requirement 8): eleven named tuning variables recorded as
    VALUES, in a compared key of their own, resolved identically every run."""

    EXPECTED = (
        "WAVEFOUNDRY_GRAPH_BETWEENNESS_TOP_N",
        "WAVEFOUNDRY_GRAPH_BETWEENNESS_EXACT_MAX_NODES",
        "WAVEFOUNDRY_GRAPH_BETWEENNESS_CUTOFF_MAX_NODES",
        "WAVEFOUNDRY_GRAPH_BETWEENNESS_CUTOFF",
        "WAVEFOUNDRY_MAX_TS_PARSE_BYTES",
        "WAVEFOUNDRY_MAX_LINE_SCAN_BYTES",
        "WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD",
        "WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS",
        "WAVEFOUNDRY_GRAPH_PARALLEL_BACKEND",
        "WAVEFOUNDRY_GRAPH_PARALLEL_START_METHOD",
        # Wave 1wpaj delivery review: the second variable the indexer
        # assigns during every build, and a chunk-set change.
        "WAVEFOUNDRY_SPEC_CHUNKING",
    )

    def test_exactly_the_declared_variables(self):
        self.assertEqual(list(self.EXPECTED),
                         [name for name, _module, _default in subject.PRODUCTION_TUNING_ENVS])

    def test_values_not_presence(self):
        # The toggle set would snapshot two different centrality settings
        # identically, because it records a boolean.
        low = subject._production_tuning({"WAVEFOUNDRY_GRAPH_BETWEENNESS_TOP_N": "50"})
        high = subject._production_tuning({"WAVEFOUNDRY_GRAPH_BETWEENNESS_TOP_N": "400"})
        self.assertEqual("50", low["WAVEFOUNDRY_GRAPH_BETWEENNESS_TOP_N"])
        self.assertEqual("400", high["WAVEFOUNDRY_GRAPH_BETWEENNESS_TOP_N"])
        self.assertNotEqual(low, high)
        # The toggle-set encoding, applied to the same two settings, collapses.
        self.assertEqual(bool("50"), bool("400"),
                         "presence-as-boolean cannot separate two different values")

    def test_never_joins_the_retrieval_toggle_set(self):
        # An entry in the toggle set routes any invocation where it is SET to
        # operator review, and ``indexer`` assigns WAVEFOUNDRY_MAX_TS_PARSE_BYTES
        # during every build, so the required verdict would be unreachable.
        # The runner itself pins some kill switches for hermetic runs, so the
        # oracle is that setting all eleven tuning variables CHANGES NOTHING about
        # the toggle snapshot -- not that the snapshot is all-false.
        self.assertEqual(set(), set(self.EXPECTED) & set(subject.RETRIEVAL_TOGGLE_ENVS))
        before = subject._retrieval_toggles()
        with patch.dict(os.environ, {name: "1" for name in self.EXPECTED}):
            self.assertEqual(before, subject._retrieval_toggles())

    def test_resolution_falls_back_to_the_module_default(self):
        resolved = subject._production_tuning({})
        for name, _module, default in subject.PRODUCTION_TUNING_ENVS:
            self.assertEqual(default, resolved[name])
        # An empty value is unset, matching the ``or DEFAULT`` production form.
        self.assertEqual("2000000",
                         subject._production_tuning({"WAVEFOUNDRY_MAX_TS_PARSE_BYTES": ""})
                         ["WAVEFOUNDRY_MAX_TS_PARSE_BYTES"])

    def test_a_build_assignment_after_import_cannot_move_the_snapshot(self):
        # ``indexer`` writes WAVEFOUNDRY_MAX_TS_PARSE_BYTES into os.environ while
        # building.  Reading it back would give two invocations of the same
        # evaluator different snapshots and fail the hard equality gate.
        before = subject._production_tuning()
        with patch.dict(os.environ, {"WAVEFOUNDRY_MAX_TS_PARSE_BYTES": "777",
                                     "WAVEFOUNDRY_GRAPH_BETWEENNESS_TOP_N": "777"}):
            self.assertEqual(before, subject._production_tuning())

    def test_declared_defaults_match_the_owning_module_source(self):
        # Drift pin: the defaults are DECLARED in the evaluator (seven of the eleven
        # live inline in an ``os.environ.get`` call rather than in a named
        # constant), so the oracle is the owning module's own source text.
        patterns = {
            "WAVEFOUNDRY_GRAPH_BETWEENNESS_TOP_N":
                r'os\.environ\.get\("WAVEFOUNDRY_GRAPH_BETWEENNESS_TOP_N",\s*"(\d+)"\)',
            "WAVEFOUNDRY_GRAPH_BETWEENNESS_EXACT_MAX_NODES":
                r'os\.environ\.get\("WAVEFOUNDRY_GRAPH_BETWEENNESS_EXACT_MAX_NODES",\s*"(\d+)"\)',
            "WAVEFOUNDRY_GRAPH_BETWEENNESS_CUTOFF_MAX_NODES":
                r'os\.environ\.get\("WAVEFOUNDRY_GRAPH_BETWEENNESS_CUTOFF_MAX_NODES",\s*"(\d+)"\)',
            "WAVEFOUNDRY_GRAPH_BETWEENNESS_CUTOFF":
                r'os\.environ\.get\("WAVEFOUNDRY_GRAPH_BETWEENNESS_CUTOFF",\s*"(\d+)"\)',
            "WAVEFOUNDRY_MAX_TS_PARSE_BYTES":
                r"MAX_TREESITTER_PARSE_BYTES_DEFAULT\s*=\s*([\d_]+)",
            "WAVEFOUNDRY_MAX_LINE_SCAN_BYTES":
                r"_LINE_SCAN_MAX_BYTES_DEFAULT\s*=\s*([\d_]+)",
            "WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD":
                r'os\.environ\.get\("WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD",\s*"(\d+)"\)',
            "WAVEFOUNDRY_GRAPH_PARALLEL_BACKEND":
                r'"WAVEFOUNDRY_GRAPH_PARALLEL_BACKEND",\s*"([a-z]+)"',
            "WAVEFOUNDRY_GRAPH_PARALLEL_START_METHOD":
                r'os\.environ\.get\("WAVEFOUNDRY_GRAPH_PARALLEL_START_METHOD",\s*"([a-z]+)"\)',
        }
        sources: dict[str, str] = {}
        for name, module, default in subject.PRODUCTION_TUNING_ENVS:
            with self.subTest(variable=name):
                if name == "WAVEFOUNDRY_SPEC_CHUNKING":
                    # The module default is a boolean constant, not a string
                    # literal inside the env read, so the declared default is
                    # None and the oracle is that constant's presence.
                    self.assertIsNone(default)
                    self.assertIn(
                        "SPEC_CHUNKING_DEFAULT_ON",
                        sources.setdefault(module, (SCRIPTS / module).read_text(encoding="utf-8")))
                    continue
                if name == "WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS":
                    # No module default: unset means "auto-scale by file count".
                    self.assertIsNone(default)
                    self.assertIn(
                        '"WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS" in os.environ',
                        sources.setdefault(module, (SCRIPTS / module).read_text(encoding="utf-8")))
                    continue
                text = sources.setdefault(module, (SCRIPTS / module).read_text(encoding="utf-8"))
                found = re.search(patterns[name], text)
                self.assertIsNotNone(found, f"{name} default not found in {module}")
                self.assertEqual(default, found.group(1).replace("_", ""))

    def test_a_tuning_difference_refuses_the_comparison(self):
        builder = BaselineComparisonTests()
        baseline = builder._report(8, 100.0, 1000)
        current = builder._report(8, 100.0, 1000)
        current["environment"]["production_tuning"] = dict(
            current["environment"]["production_tuning"],
            WAVEFOUNDRY_GRAPH_BETWEENNESS_TOP_N="9",
        )
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.apply_baseline_comparison(current, baseline)
        self.assertEqual("invalid_baseline", caught.exception.code)
        self.assertIn("production_tuning", caught.exception.message)

    def test_a_report_missing_the_key_entirely_is_refused(self):
        builder = BaselineComparisonTests()
        baseline = builder._report(8, 100.0, 1000)
        current = builder._report(8, 100.0, 1000)
        current["environment"].pop("production_tuning")
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.apply_baseline_comparison(current, baseline)
        self.assertEqual("invalid_baseline", caught.exception.code)


class FixtureLevelComparisonTests(unittest.TestCase):
    """Wave 1wpig (1wpaj Requirement 8): one row per applicable holdout
    ``(fixture_id, tool)`` key, compared on every gate metric."""

    def _pair(self, rows):
        builder = BaselineComparisonTests()
        baseline = builder._report(8, 100.0, 1000)
        current = builder._report(8, 100.0, 1000)
        baseline["cases"] = [dict(row) for row in rows["baseline"]]
        current["cases"] = [dict(row) for row in rows["current"]]
        baseline["run_id"] = subject._compute_run_id(baseline)
        return current, baseline

    @staticmethod
    def _row(fixture_id, tool="code_ask", **overrides):
        row = {"fixture_id": fixture_id, "class": "class-a", "split": "holdout",
               "tool": tool, "applicable": True, "recall_at_10": 1.0,
               "ndcg_at_10": 1.0, "mrr_at_10": 1.0,
               "abstention_correct": None, "question_type_correct": True}
        row.update(overrides)
        return row

    def test_a_masked_per_fixture_regression_the_aggregate_cannot_see(self):
        # Two fixtures, one down and one up by the same amount: the holdout
        # aggregate and the holdout class metric are BYTE-IDENTICAL on both
        # sides, and only the per-fixture oracle can see the loss.
        current, baseline = self._pair({
            "baseline": [self._row("fixture-a", recall_at_10=1.0),
                         self._row("fixture-b", recall_at_10=0.0)],
            "current": [self._row("fixture-a", recall_at_10=0.0),
                        self._row("fixture-b", recall_at_10=1.0)],
        })
        self.assertEqual(
            baseline["metrics"], current["metrics"],
            "the aggregate arms must be identical or this proves nothing")
        self.assertEqual([], subject._quality_comparison(current, baseline),
                         "the aggregate comparison misses it by construction")
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        regressions = [row for row in violations if row["kind"] == "fixture_quality_regression"]
        self.assertEqual(1, len(regressions))
        self.assertEqual(("fixture-a", "recall_at_10", 1.0, 0.0),
                         (regressions[0]["fixture_id"], regressions[0]["metric"],
                          regressions[0]["baseline"], regressions[0]["current"]))

    def test_gate_metric_names_are_mapped_onto_the_case_row_fields(self):
        # Reading ``abstention_accuracy``/``question_type_accuracy`` straight off
        # a case row returns null on BOTH sides, and the null-vs-null skip would
        # silently disable two of the five metrics.
        self.assertEqual({"abstention_accuracy": "abstention_correct",
                          "question_type_accuracy": "question_type_correct"},
                         subject.FIXTURE_CASE_METRIC_KEYS)
        current, baseline = self._pair({
            "baseline": [self._row("fixture-a", abstention_correct=True)],
            "current": [self._row("fixture-a", abstention_correct=False)],
        })
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual(
            ["abstention_accuracy"],
            [row["metric"] for row in violations if row["kind"] == "fixture_quality_regression"])
        current, baseline = self._pair({
            "baseline": [self._row("fixture-a", question_type_correct=True)],
            "current": [self._row("fixture-a", question_type_correct=False)],
        })
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual(
            ["question_type_accuracy"],
            [row["metric"] for row in violations if row["kind"] == "fixture_quality_regression"])

    def test_null_semantics_are_asymmetric(self):
        # baseline value vs current null -> FAILURE.
        current, baseline = self._pair({
            "baseline": [self._row("fixture-a", abstention_correct=True)],
            "current": [self._row("fixture-a", abstention_correct=None)],
        })
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual(
            ["abstention_accuracy"],
            [row["metric"] for row in violations if row["kind"] == "fixture_quality_regression"])
        # current value vs baseline null -> REPORTED, never a failure and never
        # an operator-review reason (a signal APPEARING is not a regression).
        current, baseline = self._pair({
            "baseline": [self._row("fixture-a", abstention_correct=None)],
            "current": [self._row("fixture-a", abstention_correct=True)],
        })
        violations, operator_reviews = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual([], [row for row in violations
                              if row["kind"] == "fixture_quality_regression"])
        reported = current["comparison"]["fixture_comparison"]["reported"]
        self.assertEqual(["abstention_accuracy"], [row["metric"] for row in reported])
        self.assertEqual([], [row for row in operator_reviews
                              if row.get("kind") == "fixture_metric_appeared"])
        # null vs null -> SKIP: neither a violation nor a report.
        current, baseline = self._pair({
            "baseline": [self._row("fixture-a", abstention_correct=None)],
            "current": [self._row("fixture-a", abstention_correct=None)],
        })
        subject.apply_baseline_comparison(current, baseline)
        self.assertEqual([], current["comparison"]["fixture_comparison"]["reported"])
        self.assertEqual([], current["comparison"]["fixture_comparison"]["violations"])

    def test_duplicate_rows_for_one_key_are_refused(self):
        current, baseline = self._pair({
            "baseline": [self._row("fixture-a")],
            "current": [self._row("fixture-a"), self._row("fixture-a")],
        })
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.apply_baseline_comparison(current, baseline)
        self.assertEqual("invalid_baseline", caught.exception.code)
        self.assertIn("more than one applicable holdout row", caught.exception.message)

    def test_key_sets_must_be_identical_in_both_directions(self):
        for missing_side, expected in (("current", "current report is missing"),
                                       ("baseline", "baseline is missing")):
            with self.subTest(missing_side=missing_side):
                rows = {"baseline": [self._row("fixture-a"), self._row("fixture-b")],
                        "current": [self._row("fixture-a"), self._row("fixture-b")]}
                rows[missing_side] = [self._row("fixture-a")]
                current, baseline = self._pair(rows)
                with self.assertRaises(subject.EvaluationInvalid) as caught:
                    subject.apply_baseline_comparison(current, baseline)
                self.assertEqual("invalid_baseline", caught.exception.code)
                self.assertIn(expected, caught.exception.message)

    def test_inapplicable_and_calibration_rows_are_outside_the_oracle(self):
        rows = {
            "baseline": [self._row("fixture-a"),
                         self._row("fixture-c", split="calibration", recall_at_10=1.0),
                         {"fixture_id": "fixture-d", "tool": "code_ask", "split": "holdout",
                          "applicable": False, "exclusion_reason": "out of contract"}],
            "current": [self._row("fixture-a"),
                        self._row("fixture-c", split="calibration", recall_at_10=0.0),
                        {"fixture_id": "fixture-d", "tool": "code_ask", "split": "holdout",
                         "applicable": False, "exclusion_reason": "out of contract"}],
        }
        current, baseline = self._pair(rows)
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        self.assertEqual([], [row for row in violations
                              if row["kind"] == "fixture_quality_regression"])
        self.assertEqual(1, current["comparison"]["fixture_comparison"]["compared_keys"])

    def test_the_same_fixture_on_two_tools_is_two_keys(self):
        current, baseline = self._pair({
            "baseline": [self._row("fixture-a", tool="code_ask"),
                         self._row("fixture-a", tool="code_search")],
            "current": [self._row("fixture-a", tool="code_ask"),
                        self._row("fixture-a", tool="code_search", recall_at_10=0.5)],
        })
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        regressions = [row for row in violations if row["kind"] == "fixture_quality_regression"]
        self.assertEqual([("fixture-a", "code_search")],
                         [(row["fixture_id"], row["tool"]) for row in regressions])
        self.assertEqual(2, current["comparison"]["fixture_comparison"]["compared_keys"])


class ConfinedReportIOTests(unittest.TestCase):
    """Wave 1wpig (1wpaj Requirement 8): confined baseline/output paths, a
    single no-follow baseline handle, and atomic link publish."""

    def setUp(self):
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)
        self.root = Path(self._temp.name)
        self.reports = self.root / "docs" / "reports"
        self.reports.mkdir(parents=True)

    def _dest(self, name="retrieval-quality-out.json") -> Path:
        return self.reports / name

    @staticmethod
    def _can_symlink(target: Path, link: Path) -> bool:
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            return False
        return True

    # -- confinement ------------------------------------------------------
    def test_path_escape_is_refused(self):
        cases = {
            "outside the root": Path(self._temp.name).parent / "retrieval-quality-x.json",
            "outside the report directory": self.root / "retrieval-quality-x.json",
            "not a direct child": self.reports / "nested" / "retrieval-quality-x.json",
            "traversal out of the report directory":
                self.reports / ".." / ".." / "retrieval-quality-x.json",
            "wrong basename prefix": self.reports / "report.json",
        }
        for label, candidate in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(subject.EvaluationInvalid) as caught:
                    subject.confined_report_path(self.root, candidate, role="output")
                self.assertEqual("report_path_unconfined", caught.exception.code)

    def test_a_traversal_that_lands_back_inside_is_accepted(self):
        # ``docs/reports/nested/../retrieval-quality-x.json`` normalizes INTO the
        # report directory; the rule is the resolved parent, not the spelling.
        (self.reports / "nested").mkdir()
        resolved = subject.confined_report_path(
            self.root, self.reports / "nested" / ".." / "retrieval-quality-x.json",
            role="output")
        self.assertEqual(self._dest("retrieval-quality-x.json").resolve(), resolved)

    def test_symlinked_report_directory_is_refused(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        shutil.rmtree(self.reports)
        if not self._can_symlink(elsewhere, self.reports):
            self.skipTest("symlink creation is unavailable on this platform")
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.confined_report_path(self.root, self._dest(), role="output")
        self.assertEqual("report_path_unconfined", caught.exception.code)
        self.assertIn("symlink", caught.exception.message)

    def test_symlinked_final_component_is_refused(self):
        target = self.root / "elsewhere.json"
        target.write_text("{}", encoding="utf-8")
        if not self._can_symlink(target, self._dest()):
            self.skipTest("symlink creation is unavailable on this platform")
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.confined_report_path(self.root, self._dest(), role="output")
        self.assertEqual("report_path_unconfined", caught.exception.code)
        self.assertIn("symlink", caught.exception.message)

    def test_non_regular_file_is_refused(self):
        directory = self._dest("retrieval-quality-dir.json")
        directory.mkdir()
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.confined_report_path(self.root, directory, role="baseline")
        self.assertEqual("report_path_unconfined", caught.exception.code)
        self.assertIn("not a regular file", caught.exception.message)

    def test_parent_directories_are_never_created(self):
        missing = self.root / "other" / "reports" / "retrieval-quality-x.json"
        with self.assertRaises(subject.EvaluationInvalid):
            subject.confined_report_path(self.root, missing, role="output")
        self.assertFalse((self.root / "other").exists())

    def test_protected_closed_1seaw_receipts_can_be_read_but_never_written(self):
        self.assertEqual(3, len(subject.PROTECTED_REPORT_PATHS))
        for relative in subject.PROTECTED_REPORT_PATHS:
            with self.subTest(protected=relative):
                path = self.root / relative
                path.write_text("{}", encoding="utf-8")
                with self.assertRaises(subject.EvaluationInvalid) as caught:
                    subject.confined_report_path(self.root, path, role="output")
                self.assertEqual("report_path_protected", caught.exception.code)
                # Still a legitimate INPUT.
                self.assertEqual(path.resolve(),
                                 subject.confined_report_path(self.root, path, role="baseline"))

    def test_a_publish_temporary_name_cannot_be_a_declared_destination(self):
        temporary = subject._publish_temporary(self._dest())
        self.assertTrue(temporary.name.startswith(subject.REPORT_BASENAME_PREFIX))
        self.assertTrue(subject._REPORT_TEMP_RE.match(temporary.name))
        subject.confined_report_path(self.root, temporary, role="temporary")
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.confined_report_path(self.root, temporary, role="output")
        self.assertEqual("report_path_unconfined", caught.exception.code)
        self.assertIn("reserved for publish temporaries", caught.exception.message)

    # -- single-handle baseline read --------------------------------------
    def test_baseline_bytes_are_hashed_exactly_as_parsed(self):
        path = self._dest("retrieval-quality-baseline-input.json")
        payload = b'{"schema": "x", "value": 1}\n'
        path.write_bytes(payload)
        read_bytes, parsed = subject.read_baseline_bytes(path)
        self.assertEqual(payload, read_bytes)
        self.assertEqual({"schema": "x", "value": 1}, parsed)

    def test_hard_link_alias_is_rejected_from_the_descriptor_link_count(self):
        path = self._dest("retrieval-quality-baseline-input.json")
        path.write_text('{"a": 1}', encoding="utf-8")
        alias = self._dest("retrieval-quality-alias.json")
        try:
            os.link(path, alias)
        except (OSError, NotImplementedError):
            self.skipTest("hard links are unavailable on this platform")
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.read_baseline_bytes(path)
        self.assertEqual("invalid_baseline", caught.exception.code)
        self.assertIn("hard-link alias", caught.exception.message)

    def test_a_symlinked_baseline_is_not_followed(self):
        target = self.root / "elsewhere.json"
        target.write_text('{"a": 1}', encoding="utf-8")
        link = self._dest("retrieval-quality-link.json")
        if not self._can_symlink(target, link):
            self.skipTest("symlink creation is unavailable on this platform")
        if not subject._NO_FOLLOW:
            self.skipTest("O_NOFOLLOW is unavailable on this platform")
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.read_baseline_bytes(link)
        self.assertEqual("invalid_baseline", caught.exception.code)

    def test_a_non_regular_baseline_is_refused(self):
        directory = self._dest("retrieval-quality-dir.json")
        directory.mkdir()
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.read_baseline_bytes(directory)
        self.assertEqual("invalid_baseline", caught.exception.code)

    def test_a_baseline_replaced_between_validation_and_read_is_refused(self):
        path = self._dest("retrieval-quality-baseline-input.json")
        path.write_text('{"a": 1}', encoding="utf-8")
        replacement = self._dest("retrieval-quality-replacement.json")
        replacement.write_text('{"a": 2}', encoding="utf-8")
        real_stat = os.stat

        def replaced(target, *args, **kwargs):
            # The window this closes: the descriptor is held, and the NAME is
            # re-pointed at a different inode before the bytes are read.
            if Path(target) == path:
                os.replace(replacement, path)
            return real_stat(target, *args, **kwargs)

        with patch.object(subject.os, "stat", side_effect=replaced):
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.read_baseline_bytes(path)
        self.assertEqual("invalid_baseline", caught.exception.code)
        self.assertIn("replaced between validation and read", caught.exception.message)

    # -- atomic publish ----------------------------------------------------
    def test_publish_writes_the_report_and_leaves_no_temporary(self):
        destination = self._dest()
        receipt = subject.publish_report(self.root, destination, {"verdict": "baseline"})
        self.assertEqual(subject._stable_json_bytes({"verdict": "baseline"}, pretty=True),
                         destination.read_bytes())
        self.assertEqual(receipt["content_sha256"],
                         hashlib.sha256(destination.read_bytes()).hexdigest())
        self.assertFalse(receipt["recovered_leftover_temporary"])
        self.assertEqual(1, os.lstat(destination).st_nlink)
        self.assertEqual([], [name for name in os.listdir(self.reports)
                              if subject._REPORT_TEMP_RE.match(name)])

    def test_an_existing_destination_is_never_overwritten(self):
        destination = self._dest()
        destination.write_bytes(b"original\n")
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.publish_report(self.root, destination, {"verdict": "baseline"})
        self.assertEqual("report_destination_exists", caught.exception.code)
        self.assertEqual(b"original\n", destination.read_bytes())

    def test_the_temporary_satisfies_the_prefix_rule_and_the_exclusion_assertion(self):
        seen: list[str] = []

        def recording_matches(rel, patterns):
            seen.append(rel)
            return True

        indexer = SimpleNamespace(
            SOURCE_CODE_EXTENSIONS={".json"}, DOCS_TEXT_EXTENSIONS=set(),
            DOCS_EXTENSIONLESS_NAMES=set(), CODE_EXTENSIONLESS_NAMES=set(),
            _load_ignore_patterns=lambda root: ["docs/reports/retrieval-quality-*.json"],
            _matches_ignore=recording_matches,
        )
        destination = self._dest()
        subject.publish_report(self.root, destination, {"verdict": "baseline"},
                               indexer=indexer)
        self.assertIn("docs/reports/retrieval-quality-out.json", seen)
        temporaries = [rel for rel in seen if subject._REPORT_TEMP_RE.match(Path(rel).name)]
        self.assertEqual(1, len(temporaries),
                         "the publish temporary is covered by the pre-create assertion")
        for rel in seen:
            self.assertTrue(Path(rel).name.startswith(subject.REPORT_BASENAME_PREFIX))

    def test_an_unprefixed_temporary_name_is_refused_before_anything_is_created(self):
        destination = self._dest()
        with patch.object(subject, "_publish_temporary",
                          return_value=self.reports / "scratch.json"):
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.publish_report(self.root, destination, {"verdict": "baseline"})
        self.assertEqual("report_path_unconfined", caught.exception.code)
        self.assertFalse(destination.exists())
        self.assertFalse((self.reports / "scratch.json").exists())

    def test_a_leftover_temporary_aliasing_the_destination_is_recovered(self):
        # The interrupt window: os.link ran, the unlink did not.  The recovery
        # unlinks the TEMPORARY, never the destination.
        destination = self._dest()
        report = {"verdict": "baseline"}
        payload = subject._stable_json_bytes(report, pretty=True)
        leftover = subject._publish_temporary(destination)
        leftover.write_bytes(payload)
        try:
            os.link(leftover, destination)
        except (OSError, NotImplementedError):
            self.skipTest("hard links are unavailable on this platform")
        destination_inode = os.lstat(destination).st_ino
        receipt = subject.publish_report(self.root, destination, report)
        self.assertTrue(receipt["recovered_leftover_temporary"])
        self.assertFalse(leftover.exists(), "the temporary is what gets unlinked")
        self.assertTrue(destination.exists(), "the destination is never unlinked")
        self.assertEqual(destination_inode, os.lstat(destination).st_ino)
        self.assertEqual(1, os.lstat(destination).st_nlink)
        self.assertEqual(payload, destination.read_bytes())

    def test_a_leftover_alias_with_different_content_is_refused_and_nothing_is_unlinked(self):
        destination = self._dest()
        leftover = subject._publish_temporary(destination)
        leftover.write_bytes(b"someone elses report\n")
        try:
            os.link(leftover, destination)
        except (OSError, NotImplementedError):
            self.skipTest("hard links are unavailable on this platform")
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.publish_report(self.root, destination, {"verdict": "baseline"})
        self.assertEqual("report_destination_exists", caught.exception.code)
        self.assertTrue(destination.exists())
        self.assertTrue(leftover.exists())
        self.assertEqual(b"someone elses report\n", destination.read_bytes())

    def test_an_unrecoverable_extra_link_fails_the_publish_verification(self):
        # A second link that is NOT a publish temporary: the destination is left
        # exactly as it is and the publish is reported unverified.
        destination = self._dest()
        alias = self._dest("retrieval-quality-someone-elses-name.json")
        payload = subject._stable_json_bytes({"verdict": "baseline"}, pretty=True)
        destination.write_bytes(payload)
        try:
            os.link(destination, alias)
        except (OSError, NotImplementedError):
            self.skipTest("hard links are unavailable on this platform")
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.publish_report(self.root, destination, {"verdict": "baseline"})
        self.assertEqual("report_destination_exists", caught.exception.code)
        self.assertTrue(destination.exists())
        self.assertTrue(alias.exists())

    def test_an_interrupted_unlink_is_recovered_by_the_publish_verification(self):
        # The other half of the interrupt window: os.link ran, the finally-unlink
        # did not.  The destination is left with two links and the verification
        # must recover it -- by unlinking the TEMPORARY, never the destination.
        destination = self._dest()
        report = {"verdict": "baseline"}
        real_unlink = os.unlink
        skipped: list[Path] = []

        def skip_the_first_temporary_unlink(target, *args, **kwargs):
            if not skipped and subject._REPORT_TEMP_RE.match(Path(target).name):
                skipped.append(Path(target))
                return
            return real_unlink(target, *args, **kwargs)

        with patch.object(subject.os, "unlink", side_effect=skip_the_first_temporary_unlink):
            receipt = subject.publish_report(self.root, destination, report)
        self.assertEqual(1, len(skipped), "the interrupt must have been simulated")
        self.assertTrue(receipt["recovered_leftover_temporary"])
        self.assertFalse(skipped[0].exists(), "the leftover temporary is unlinked")
        self.assertTrue(destination.exists(), "the destination is never unlinked")
        self.assertEqual(1, os.lstat(destination).st_nlink)
        self.assertEqual(subject._stable_json_bytes(report, pretty=True),
                         destination.read_bytes())

    def test_a_failed_link_removes_the_temporary(self):
        destination = self._dest()
        with patch.object(subject.os, "link", side_effect=OSError("nope")):
            with self.assertRaises(subject.EvaluationInvalid) as caught:
                subject.publish_report(self.root, destination, {"verdict": "baseline"})
        self.assertEqual("report_publish_failed", caught.exception.code)
        self.assertFalse(destination.exists())
        self.assertEqual([], [name for name in os.listdir(self.reports)
                              if subject._REPORT_TEMP_RE.match(name)])


if __name__ == "__main__":
    unittest.main()


class CheckpointBudgetTests(unittest.TestCase):
    """Wave 1wscp AC-10 / requirement 10: the nine-invocation sequence, the
    per-invocation and cumulative ceilings, and fail-closed exhaustion."""

    def setUp(self):
        self.mod = subject

    def _entry(self, slot, seconds=10.0, report_bytes=1000, public_calls=35):
        return {"slot": slot, "seconds": seconds,
                "report_bytes": report_bytes, "public_calls": public_calls}

    def test_the_sequence_is_exactly_the_nine_named_slots(self):
        self.assertEqual(9, len(self.mod.CHECKPOINT_SLOTS))
        self.assertEqual(9, self.mod.MAX_CHECKPOINT_INVOCATIONS)
        self.assertEqual(
            ("baseline_a", "baseline_b", "post_confidence_routing",
             "post_lexical", "ann_candidate_1", "ann_candidate_2",
             "ann_candidate_3", "post_graph_final", "replay"),
            self.mod.CHECKPOINT_SLOTS)

    def test_at_most_three_ann_candidate_slots_exist(self):
        ann = [s for s in self.mod.CHECKPOINT_SLOTS if s.startswith("ann_candidate")]
        self.assertEqual(3, len(ann))

    def test_the_declared_ceilings_are_the_requirement_ten_values(self):
        self.assertEqual(10_800, self.mod.CHECKPOINT_SEQUENCE_SECONDS)
        self.assertEqual(9 * 1024 * 1024, self.mod.CHECKPOINT_SEQUENCE_BYTES)
        self.assertEqual(7_020, self.mod.CHECKPOINT_SEQUENCE_PUBLIC_CALLS)
        self.assertEqual(1_200, self.mod.CHECKPOINT_INVOCATION_SECONDS)
        self.assertEqual(1024 * 1024, self.mod.CHECKPOINT_INVOCATION_BYTES)
        self.assertEqual(780, self.mod.CHECKPOINT_INVOCATION_PUBLIC_CALLS)

    def test_an_unknown_slot_is_refused(self):
        with self.assertRaises(self.mod.CheckpointBudgetExhausted) as ctx:
            self.mod.authorize_checkpoint([], "post_everything")
        self.assertEqual("unknown_checkpoint_slot", ctx.exception.code)

    def test_a_slot_cannot_be_used_twice(self):
        entries = [self._entry("baseline_a")]
        with self.assertRaises(self.mod.CheckpointBudgetExhausted) as ctx:
            self.mod.authorize_checkpoint(entries, "baseline_a")
        self.assertEqual("checkpoint_slot_already_used", ctx.exception.code)

    def test_a_tenth_invocation_fails_closed(self):
        entries = [self._entry(s) for s in self.mod.CHECKPOINT_SLOTS]
        with self.assertRaises(self.mod.CheckpointBudgetExhausted) as ctx:
            self.mod.authorize_checkpoint(entries, "replay")
        # The slot check fires first; both are exhaustion, and both fail closed.
        self.assertIn(ctx.exception.code,
                      {"checkpoint_slot_already_used",
                       "checkpoint_invocations_exhausted"})

    def test_the_invocation_count_guard_is_reachable_and_pinned(self):
        # Delivery review (QA-DEL-3): the test above accepts EITHER code, and
        # with a well-formed ledger the slot-reuse check always fires first, so
        # deleting the count guard entirely left it green. That made
        # `checkpoint_invocations_exhausted` unpinned while AC-10's note
        # claimed every refusal was covered.
        #
        # A ledger CAN legitimately hold repeats of one slot (a failed attempt
        # is retained against the slot it was attempting), so drive the count
        # guard with nine entries on one slot and then request a FRESH slot --
        # the reuse check cannot fire, and only the count guard stands.
        entries = [self._entry("baseline_a") for _ in range(9)]
        with self.assertRaises(self.mod.CheckpointBudgetExhausted) as ctx:
            self.mod.authorize_checkpoint(entries, "post_graph_final")
        self.assertEqual("checkpoint_invocations_exhausted", ctx.exception.code)

    def test_the_per_invocation_ceilings_are_enforced(self):
        for kwargs, code in (
            ({"seconds": 1201}, "checkpoint_invocation_seconds_exceeded"),
            ({"report_bytes": 1024 * 1024 + 1}, "checkpoint_invocation_bytes_exceeded"),
            ({"public_calls": 781}, "checkpoint_invocation_calls_exceeded"),
        ):
            with self.subTest(limit=code):
                with self.assertRaises(self.mod.CheckpointBudgetExhausted) as ctx:
                    self.mod.authorize_checkpoint([], "baseline_a", **kwargs)
                self.assertEqual(code, ctx.exception.code)

    def test_the_cumulative_ceilings_are_enforced(self):
        # Eight prior runs, each just inside its own ceiling, leave less than a
        # full invocation of sequence budget.
        entries = [self._entry(s, seconds=1200, report_bytes=1024 * 1024,
                               public_calls=780)
                   for s in self.mod.CHECKPOINT_SLOTS[:8]]
        state = self.mod.checkpoint_budget_state(entries)
        self.assertEqual(1200, state["seconds_remaining"])
        with self.assertRaises(self.mod.CheckpointBudgetExhausted) as ctx:
            self.mod.authorize_checkpoint(entries, "replay", seconds=1200,
                                          report_bytes=1024 * 1024 + 1)
        self.assertEqual("checkpoint_invocation_bytes_exceeded", ctx.exception.code)
        # 8 MiB spent of 9 MiB: a full 1 MiB report still fits exactly.
        ok = self.mod.authorize_checkpoint(entries, "replay", seconds=1200,
                                           report_bytes=1024 * 1024,
                                           public_calls=780)
        self.assertTrue(ok["authorized"])

    def test_failed_attempts_consume_budget(self):
        # Not counting them would make the ceiling evadable by discarding
        # unfavourable runs.
        entries = [self._entry("baseline_a", seconds=900),
                   self._entry("baseline_b", seconds=900)]
        state = self.mod.checkpoint_budget_state(entries)
        self.assertEqual(1800.0, state["seconds"])
        self.assertEqual(2, state["invocations"])
        self.assertEqual(7, state["invocations_remaining"])

    def test_the_state_reports_which_slots_remain(self):
        state = self.mod.checkpoint_budget_state([self._entry("baseline_a")])
        self.assertEqual(["baseline_a"], state["slots_used"])
        self.assertNotIn("baseline_a", state["slots_available"])
        self.assertIn("post_graph_final", state["slots_available"])

    def test_a_missing_ledger_reads_as_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                [], self.mod.load_checkpoint_ledger(Path(tmp) / "absent.jsonl"))

    def test_a_corrupt_ledger_fails_closed_rather_than_reading_as_empty(self):
        # An unreadable ledger must never look like "no budget consumed".
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            path.write_text('{"slot": "baseline_a"}\nnot json\n')
            with self.assertRaises(self.mod.CheckpointBudgetExhausted) as ctx:
                self.mod.load_checkpoint_ledger(path)
            self.assertEqual("checkpoint_ledger_unreadable", ctx.exception.code)

    def test_a_valid_ledger_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            path.write_text("\n".join(
                json.dumps(self._entry(s)) for s in ("baseline_a", "baseline_b")) + "\n")
            entries = self.mod.load_checkpoint_ledger(path)
            self.assertEqual(2, len(entries))
            self.assertEqual("baseline_a", entries[0]["slot"])


class CheckpointLedgerKindTests(unittest.TestCase):
    """Wave 1wpie delivery reverification (finding A): a failed attempt must
    not occupy a slot, and the SHIPPED ledger must replay legally.

    The previous version counted every row as an invocation and put every
    row's slot in `slots_used`, so replaying the real ledger reported 15
    invocations against a ceiling of 9, listed duplicate slots, and refused
    the run the wave's own evidence rests on. A budget gate that rejects its
    own history is not enforcing anything."""

    LEDGER = (Path(__file__).resolve().parents[3].parent
              / "docs" / "evals" / "checkpoint-ledger.jsonl")

    def setUp(self):
        self.mod = subject

    def test_a_failed_attempt_does_not_occupy_its_slot(self):
        entries = [
            {"slot": "baseline_a", "kind": "failed_attempt", "seconds": 60.0,
             "report_bytes": 215, "public_calls": 0},
            {"slot": "baseline_a", "kind": "published", "seconds": 300.0,
             "report_bytes": 1000, "public_calls": 165},
        ]
        state = self.mod.checkpoint_budget_state(entries)
        self.assertEqual(1, state["invocations"])
        self.assertEqual(1, state["failed_attempts"])
        self.assertEqual(["baseline_a"], state["slots_used"])

    def test_a_failed_attempt_still_consumes_the_resource_budget(self):
        # The other half: retries are allowed, free retries are not.
        entries = [{"slot": "baseline_a", "kind": "failed_attempt",
                    "seconds": 900.0, "report_bytes": 500, "public_calls": 40}]
        state = self.mod.checkpoint_budget_state(entries)
        self.assertEqual(0, state["invocations"])
        self.assertEqual(900.0, state["seconds"])
        self.assertEqual(40, state["public_calls"])

    def test_a_retry_after_a_failed_attempt_is_authorized(self):
        entries = [{"slot": "post_graph_final", "kind": "failed_attempt",
                    "seconds": 60.0, "report_bytes": 215, "public_calls": 0}]
        ok = self.mod.authorize_checkpoint(entries, "post_graph_final",
                                           seconds=300.0, report_bytes=600000,
                                           public_calls=165)
        self.assertTrue(ok["authorized"])

    def test_a_row_without_an_explicit_kind_counts_as_published(self):
        # Conservative default: a pre-distinction ledger must not silently
        # free slots.
        state = self.mod.checkpoint_budget_state([{"slot": "baseline_a"}])
        self.assertEqual(1, state["invocations"])
        self.assertEqual(["baseline_a"], state["slots_used"])

    def test_the_shipped_ledger_replays_legally(self):
        # The regression that motivated this class: the real on-disk ledger
        # must satisfy the gate that claims to enforce it.
        if not self.LEDGER.is_file():
            self.skipTest("no checkpoint ledger in this tree")
        entries = self.mod.load_checkpoint_ledger(self.LEDGER)
        if not entries:
            self.skipTest("checkpoint ledger is empty")
        state = self.mod.checkpoint_budget_state(entries)
        self.assertLessEqual(state["invocations"],
                             self.mod.MAX_CHECKPOINT_INVOCATIONS,
                             "the shipped ledger exceeds its own ceiling")
        self.assertEqual(len(state["slots_used"]), len(set(state["slots_used"])),
                         f"a slot is occupied twice: {state['slots_used']}")
        for key in ("seconds", "report_bytes", "public_calls"):
            with self.subTest(cap=key):
                self.assertGreaterEqual(state[f"{key}_remaining"], 0,
                                        f"the shipped ledger exceeds the {key} cap")

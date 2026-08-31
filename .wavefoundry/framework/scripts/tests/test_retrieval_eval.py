from __future__ import annotations

import json
import os
import sqlite3
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
             abstention: bool = False, query_form: str | None = None) -> dict:
    omitted = set(subject.TOOLS) - set(tools)
    row = {
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


class BaselineComparisonTests(unittest.TestCase):
    def _report(self, generation: int, p95: float, response_bytes: int) -> dict:
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
            },
            "metrics": {"by_tool": {tool: {
                "by_split": {"holdout": dict(aggregate)},
                "by_split_and_class": {"holdout": {"class-a": dict(aggregate)}},
            }
                                     for tool in subject.TOOLS}},
            "performance": {"tools": {tool: {
                "warm_p95_ms": p95, "max_response_bytes": response_bytes,
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
        with self.assertRaises(subject.EvaluationInvalid) as caught:
            subject.apply_baseline_comparison(current, baseline)
        self.assertEqual("invalid_baseline", caught.exception.code)
        self.assertIn("jitter", caught.exception.message)
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

    def test_cross_generation_requires_prior_jitter_and_detects_regression(self):
        baseline = self._report(8, 100.0, 1000)
        for tool in subject.TOOLS:
            baseline["performance"]["tools"][tool]["jitter_ratio"] = 0.01
        baseline["run_id"] = subject._compute_run_id(baseline)
        current = self._report(9, 140.0, 10000)
        violations, _ = subject.apply_baseline_comparison(current, baseline)
        kinds = {row["kind"] for row in violations}
        self.assertIn("latency_regression", kinds)
        self.assertIn("response_size_regression", kinds)

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
            _matches_ignore=lambda rel, patterns: rel in patterns,
        )

    @staticmethod
    def _tree(root: Path, ignored: tuple[str, ...]):
        (root / ".aiignore").write_text("\n".join(ignored) + "\n", encoding="utf-8")
        fixtures = root / "fixtures.json"
        baseline = root / "baseline.json"
        out = root / "report.json"
        fixtures.write_text("{}", encoding="utf-8")
        baseline.write_text("{}", encoding="utf-8")
        return fixtures, baseline, out

    def test_exit_zero_for_baseline_and_pass_and_report_bytes_are_deterministic(self):
        for verdict, with_baseline in (("baseline", False), ("pass", True)):
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                fixtures, baseline, out = self._tree(
                    root, ("fixtures.json", "baseline.json", "report.json"),
                )
                report = {
                    "verdict": verdict, "schema": subject.REPORT_SCHEMA,
                    "payload": {"z": 2, "a": 1},
                }
                argv = ["--root", str(root), "--fixtures", str(fixtures), "--out", str(out)]
                if with_baseline:
                    argv.extend(("--baseline", str(baseline)))
                with patch.dict(sys.modules, {"indexer": self._indexer()}):
                    with patch.object(subject, "run_evaluation", return_value=report):
                        with patch("builtins.print"):
                            self.assertEqual(0, subject.main(argv))
                            first = out.read_bytes()
                            self.assertEqual(0, subject.main(argv))
                            second = out.read_bytes()
                self.assertEqual(subject._stable_json_bytes(report, pretty=True), first)
                self.assertEqual(first, second)

    def test_exit_one_for_fail_and_operator_review_required(self):
        for verdict in ("fail", "operator_review_required"):
            with self.subTest(verdict=verdict), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                fixtures, baseline, out = self._tree(
                    root, ("fixtures.json", "baseline.json", "report.json"),
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
            fixtures, _, out = self._tree(root, ("fixtures.json", "report.json"))
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
            ("report.json", False),
            ("baseline.json", True),
        )
        for unignored, include_baseline in cases:
            with self.subTest(unignored=unignored), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                ignored = tuple(
                    name for name in ("fixtures.json", "report.json", "baseline.json")
                    if name != unignored
                )
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
        (index_dir / "docs.lance").mkdir(parents=True)
        (index_dir / "code.lance").mkdir()
        sqlite3.connect(index_dir / "index-state.sqlite").close()
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
        self.assertEqual({"chunker": "7", "walker": None, "graph_builder": None},
                         report["production_identity"]["versions"])
        self.assertEqual("2023-11-14T22:13:20Z", report["run_time"]["started_at"])
        self.assertEqual("2023-11-14T22:13:21Z", report["run_time"]["finished_at"])
        self.assertEqual(1.0, report["run_time"]["duration_seconds"])
        self.assertEqual({}, report["anchor_resolution"])

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


if __name__ == "__main__":
    unittest.main()

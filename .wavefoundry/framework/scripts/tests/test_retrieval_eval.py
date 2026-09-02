from __future__ import annotations

import json
import os
import sqlite3
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


if __name__ == "__main__":
    unittest.main()

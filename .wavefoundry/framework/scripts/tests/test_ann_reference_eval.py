"""Tests for the exact-vs-ANN reference measurement (wave `1wsc8`)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ann_reference_eval as subject  # noqa: E402
import indexer  # noqa: E402
import retrieval_eval  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3].parent
CORPUS = REPO_ROOT / "docs" / "evals" / "ann-reference-golden.json"


class _FakeBuilder:
    """Records the query shape and whether the vector index was bypassed."""

    def __init__(self, rows, log):
        self._rows = rows
        self._log = log
        self.bypassed = False

    def metric(self, name):
        self._log.append(("metric", name))
        return self

    def limit(self, n):
        self._log.append(("limit", n))
        return self

    def where(self, clause, prefilter=False):
        self._log.append(("where", clause, prefilter))
        return self

    def bypass_vector_index(self):
        self.bypassed = True
        self._log.append(("bypass",))
        return self

    def to_list(self):
        return list(self._rows)


class _FakeBuilderWithoutBypass(_FakeBuilder):
    """A LanceDB build that cannot do exact search at all."""
    bypass_vector_index = None


class _FakeTable:
    def __init__(self, rows, log, builder_cls=_FakeBuilder):
        self._rows = rows
        self._log = log
        self._builder_cls = builder_cls
        self.last_builder = None

    def search(self, vector):
        self._log.append(("search", len(vector)))
        self.last_builder = self._builder_cls(self._rows, self._log)
        return self.last_builder


def _rows(*ids):
    return [{"id": i} for i in ids]


class ExactSeamTests(unittest.TestCase):
    """AC-1: the exact reference must PROVE it bypassed the index."""

    def test_exact_search_invokes_bypass_and_ann_search_does_not(self):
        log = []
        table = _FakeTable(_rows("a", "b"), log)
        subject.exact_search(table, [0.1, 0.2], 10)
        self.assertTrue(table.last_builder.bypassed)
        self.assertIn(("bypass",), log)

        log.clear()
        table = _FakeTable(_rows("a", "b"), log)
        subject.ann_search(table, [0.1, 0.2], 10)
        self.assertFalse(table.last_builder.bypassed)
        self.assertNotIn(("bypass",), log)

    def test_a_build_without_the_seam_refuses_rather_than_serving_ann(self):
        # The mutant AC-1 names: a build that silently serves ANN while the
        # caller believes it is exact.  It must fail closed, not return rows.
        table = _FakeTable(_rows("a"), [], builder_cls=_FakeBuilderWithoutBypass)
        with self.assertRaises(subject.AnnEvaluationInvalid) as caught:
            subject.exact_search(table, [0.1], 10)
        self.assertEqual("exact_mode_unavailable", caught.exception.code)

    def test_both_sides_issue_the_identical_query_shape(self):
        # An "exact" reference that differed in metric, limit or filter would
        # measure that difference instead of the index.
        exact_log, ann_log = [], []
        subject.exact_search(_FakeTable(_rows("a"), exact_log), [0.1], 25,
                             where="kind = 'code'")
        subject.ann_search(_FakeTable(_rows("a"), ann_log), [0.1], 25,
                           where="kind = 'code'")
        self.assertEqual([e for e in exact_log if e[0] != "bypass"], ann_log)
        self.assertIn(("limit", 25), ann_log)
        self.assertIn(("where", "kind = 'code'", True), ann_log)


class OverlapTests(unittest.TestCase):
    def test_full_and_zero_agreement(self):
        self.assertEqual(1.0, subject.overlap_at_k(["a", "b"], ["b", "a"], 2))
        self.assertEqual(0.0, subject.overlap_at_k(["a", "b"], ["c", "d"], 2))

    def test_an_injected_omission_shows_as_partial_overlap(self):
        # AC-2: dropping one exact hit from the ANN side must be visible.
        self.assertEqual(0.5, subject.overlap_at_k(["a", "b"], ["a", "z"], 2))

    def test_overlap_is_measured_against_the_exact_top_k_only(self):
        self.assertEqual(1.0, subject.overlap_at_k(["a"], ["a", "b", "c"], 1))

    def test_repeated_exact_queries_return_identical_normalized_ids(self):
        # AC-2 first half: the exact side must be reproducible before any
        # candidate is judged against it.
        table = _FakeTable(_rows("b", "a", "c"), [])
        first = subject.normalized_ids(subject.exact_search(table, [0.1], 10))
        second = subject.normalized_ids(subject.exact_search(table, [0.1], 10))
        self.assertEqual(first, second)
        # Order-preserving, not sorted: re-ordering would hide a rank change.
        self.assertEqual(["b", "a", "c"], first)

    def test_an_injected_omission_lands_in_its_own_slice_and_no_other(self):
        # AC-2 second half: the omission must be attributable to the exact
        # (layer, query, filter, k) slice, not smeared across the report.
        exact = {"code-q1": ["a", "b"], "code-q2": ["c", "d"], "docs-q3": ["e", "f"]}
        ann = dict(exact)
        ann["code-q2"] = ["c", "zz"]          # one hit dropped, here only
        slices = {
            subject.slice_key("code", "q1", "none", 2): subject.overlap_at_k(
                exact["code-q1"], ann["code-q1"], 2),
            subject.slice_key("code", "q2", "none", 2): subject.overlap_at_k(
                exact["code-q2"], ann["code-q2"], 2),
            subject.slice_key("docs", "q3", "none", 2): subject.overlap_at_k(
                exact["docs-q3"], ann["docs-q3"], 2),
        }
        degraded = [key for key, value in slices.items() if value < 1.0]
        self.assertEqual([subject.slice_key("code", "q2", "none", 2)], degraded)
        self.assertEqual(0.5, slices[subject.slice_key("code", "q2", "none", 2)])

    def test_macro_mean_weights_every_slice_equally(self):
        slices = {("code", "q1", "none", 10): 1.0,
                  ("code", "q2", "none", 10): 1.0,
                  ("docs", "q3", "none", 10): 0.0}
        self.assertAlmostEqual(2 / 3, subject.macro_mean_overlap(slices))


class CertificationTests(unittest.TestCase):
    """AC-3 and AC-4: fail closed, and never let an aggregate hide a slice."""

    BASE = {("code", "q1", "none", 10): 0.90,
            ("code", "q2", "none", 10): 0.90,
            ("docs", "q3", "none", 10): 0.90}

    def test_a_clear_quality_gain_certifies(self):
        candidate = {k: 0.95 for k in self.BASE}
        verdict = subject.certification_verdict(self.BASE, candidate, k=10)
        self.assertTrue(verdict["certified"], verdict["reasons"])

    def test_an_aggregate_gain_hiding_a_slice_loss_is_rejected(self):
        candidate = dict.fromkeys(self.BASE, 1.0)
        # One slice loses far more than 1/K while the mean still improves.
        candidate[("docs", "q3", "none", 10)] = 0.60
        verdict = subject.certification_verdict(self.BASE, candidate, k=10)
        self.assertFalse(verdict["certified"])
        self.assertTrue(any("1/K" in r for r in verdict["reasons"]))

    def test_a_missing_slice_is_a_rejection_not_a_skip(self):
        candidate = {k: 0.99 for k in list(self.BASE)[:2]}
        verdict = subject.certification_verdict(self.BASE, candidate, k=10)
        self.assertFalse(verdict["certified"])
        self.assertTrue(any("slice sets differ" in r for r in verdict["reasons"]))

    def test_quality_neutral_needs_a_real_latency_gain(self):
        candidate = dict(self.BASE)
        # Neutral quality, latency barely better: rejected.
        verdict = subject.certification_verdict(
            self.BASE, candidate, k=10, default_p95_ms=100.0, candidate_p95_ms=95.0)
        self.assertFalse(verdict["certified"])
        # Neutral quality, latency clearly better: certified.
        verdict = subject.certification_verdict(
            self.BASE, candidate, k=10, default_p95_ms=100.0, candidate_p95_ms=85.0)
        self.assertTrue(verdict["certified"], verdict["reasons"])

    def test_quality_neutral_without_a_paired_measurement_is_rejected(self):
        verdict = subject.certification_verdict(self.BASE, dict(self.BASE), k=10)
        self.assertFalse(verdict["certified"])
        self.assertTrue(any("no paired p95" in r for r in verdict["reasons"]))

    def test_a_small_gain_below_the_threshold_is_rejected(self):
        candidate = {k: v + 0.01 for k, v in self.BASE.items()}
        verdict = subject.certification_verdict(self.BASE, candidate, k=10)
        self.assertFalse(verdict["certified"])


class CorpusTests(unittest.TestCase):
    def _reject(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corpus.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(subject.AnnEvaluationInvalid) as caught:
                subject.load_corpus(path)
        return caught.exception

    def test_the_shipped_corpus_loads_and_stays_inside_the_case_ceiling(self):
        if not CORPUS.is_file():
            self.skipTest("ANN corpus is not present in this tree")
        corpus = subject.load_corpus(CORPUS)
        self.assertLessEqual(len(corpus["cases"]), subject.MAX_TOTAL_CASES)
        # Both layers and both depths are represented, or the macro mean would
        # be dominated by whichever layer happened to have more slices.
        self.assertEqual({"code", "docs"}, {c["layer"] for c in corpus["cases"]})
        self.assertEqual({10, 50}, {c["k"] for c in corpus["cases"]})

    def test_the_shipped_corpus_is_excluded_from_the_retrieval_index(self):
        if not CORPUS.is_file():
            self.skipTest("ANN corpus is not present in this tree")
        retrieval_eval.assert_eval_artifacts_excluded(REPO_ROOT, [CORPUS], indexer)

    def test_duplicate_slice_keys_are_refused(self):
        case = {"id": "x", "layer": "code", "query_text": "q",
                "filter_shape": "none", "k": 10, "rationale": "r"}
        self.assertEqual("invalid_corpus", self._reject(
            {"schema": subject.FIXTURE_SCHEMA, "cases": [case, dict(case)]}).code)

    def test_the_total_case_ceiling_is_enforced(self):
        cases = [{"id": f"x{i}", "layer": "code", "query_text": "q",
                  "filter_shape": "none", "k": 10, "rationale": "r"}
                 for i in range(subject.MAX_TOTAL_CASES + 1)]
        self.assertEqual("case_cap_exceeded", self._reject(
            {"schema": subject.FIXTURE_SCHEMA, "cases": cases}).code)


REPORT = REPO_ROOT / "docs" / "reports" / "ann-reference-post-1wsc8.json"


class ReportIdentityTests(unittest.TestCase):
    """Wave 1wsc8 AC-5 and AC-7: the report is a receipt, not a label. Every
    Requirement 3 field is bound, and altering any of them is detected."""

    def _report(self):
        if not REPORT.is_file():
            self.skipTest("ANN report is not present in this tree")
        return json.loads(REPORT.read_text(encoding="utf-8"))

    def test_the_shipped_report_binds_every_required_identity(self):
        problems = subject.verify_report_identity(self._report())
        self.assertEqual([], problems)

    def test_a_missing_binding_is_reported_rather_than_tolerated(self):
        for field in subject.REQUIRED_IDENTITY_FIELDS:
            with self.subTest(field=field):
                report = self._report()
                report[field] = None
                problems = subject.verify_report_identity(report)
                self.assertTrue(any(field in p for p in problems), problems)

    def test_a_tampered_identity_breaks_the_content_digest(self):
        # AC-5's "detect a deliberately altered table/index/build identity".
        for field, forged in (("lance_table_version", 999999),
                              ("build_epoch", 1),
                              ("build_attempt", "forged-attempt"),
                              ("production_identity", "0" * 64)):
            with self.subTest(field=field):
                report = self._report()
                report[field] = forged
                problems = subject.verify_report_identity(report)
                self.assertTrue(
                    any("content_sha256" in p for p in problems),
                    f"altering {field} must break the receipt: {problems}")

    def test_every_slice_carries_its_query_filter_k_and_both_id_lists(self):
        report = self._report()
        self.assertEqual(5, len(report["slices"]))
        for row in report["slices"]:
            for field in subject.REQUIRED_SLICE_FIELDS:
                self.assertIn(field, row)
            self.assertTrue(row["exact_ids"], "an empty exact side scores nothing")

    def test_the_report_states_it_cannot_support_a_gain_claim(self):
        # AC-7: evidence tier, canonical role, consulted status, and the
        # explicit refusal all ride in the artifact.
        authority = self._report()["evidence_authority"]
        self.assertEqual("standing_regression", authority["evidence_tier"])
        self.assertEqual("regression_only", authority["evidence_role"])
        self.assertTrue(authority["consulted_holdout"])
        self.assertFalse(authority["supports_gain_claim"])

    def test_the_report_records_both_rejections_beside_the_certification(self):
        # An aggregate "one candidate certified" would hide that two others
        # were refused and why; the report must carry all three verdicts.
        candidates = self._report()["candidates"]
        self.assertEqual({"nprobes_20", "nprobes_50", "refine_2"}, set(candidates))
        self.assertTrue(candidates["refine_2"]["certified"])
        for name in ("nprobes_20", "nprobes_50"):
            with self.subTest(candidate=name):
                self.assertFalse(candidates[name]["certified"])
                self.assertTrue(candidates[name]["reasons"],
                                "a rejection must say why")

    def test_the_run_stayed_inside_the_declared_ceilings(self):
        report = self._report()
        total_cases = len(report["slices"]) * (1 + len(report["candidates"]))
        self.assertLessEqual(total_cases, subject.MAX_TOTAL_CASES)
        self.assertLessEqual(len(report["candidates"]),
                             subject.MAX_CANDIDATE_CONFIGURATIONS)


class BoundsTests(unittest.TestCase):
    def test_requirement_nine_numbers_are_pinned_as_literals(self):
        # Pin the contract values, not the constants against themselves.
        self.assertEqual(3, subject.MAX_CANDIDATE_CONFIGURATIONS)
        self.assertEqual(64, subject.MAX_TOTAL_CASES)
        self.assertEqual(1, subject.WARMUP_REPETITIONS)
        self.assertEqual(3, subject.MEASURED_REPETITIONS)
        self.assertEqual(15.0, subject.EXACT_QUERY_TIMEOUT_SECONDS)
        self.assertEqual(180.0, subject.TOTAL_CERTIFICATION_TIMEOUT_SECONDS)

    def test_requirement_four_thresholds_are_pinned_as_literals(self):
        self.assertEqual(0.02, subject.MINIMUM_MEAN_OVERLAP_GAIN)
        self.assertEqual(0.005, subject.QUALITY_NEUTRAL_BAND)
        self.assertEqual(0.10, subject.MINIMUM_LATENCY_GAIN_RATIO)


if __name__ == "__main__":
    unittest.main()

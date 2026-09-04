"""Tests for the bounded lexical-ranking component evaluator (wave `1wpid`)."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import indexer  # noqa: E402
import lexical_ranking_eval as subject  # noqa: E402
import retrieval_eval  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[3].parent
CALIBRATION = REPO_ROOT / "docs" / "evals" / "lexical-ranking-calibration.json"
REGRESSION = REPO_ROOT / "docs" / "evals" / "lexical-ranking-regression.json"


def _minimal_payload(role: str = "calibration") -> dict:
    return {
        "schema": subject.FIXTURE_SCHEMA,
        "evidence_role": role,
        "rows": {"code": [{"id": "r1", "path": "a.py", "text": "widget handler"}]},
        "cases": [{
            "id": "c1", "query": "widget", "table": "code",
            "relevant_ids": ["r1"], "rationale": "declaration target",
        }],
    }


class CorpusSchemaTests(unittest.TestCase):
    def _load(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corpus.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return subject.load_corpus(path)

    def _reject(self, payload):
        with self.assertRaises(subject.LexicalEvaluationInvalid) as caught:
            self._load(payload)
        return caught.exception

    def test_a_minimal_corpus_round_trips(self):
        loaded = self._load(_minimal_payload())
        self.assertEqual("calibration", loaded["evidence_role"])
        self.assertEqual(1, len(loaded["cases"]))

    def test_the_row_cap_is_enforced_per_table(self):
        payload = _minimal_payload()
        payload["rows"]["code"] = [
            {"id": f"r{i}", "path": f"{i}.py", "text": "widget"}
            for i in range(subject.MAX_ROWS_PER_TABLE + 1)
        ]
        payload["cases"][0]["relevant_ids"] = ["r0"]
        self.assertEqual("corpus_cap_exceeded", self._reject(payload).code)

    def test_a_case_cannot_name_a_row_the_corpus_lacks(self):
        payload = _minimal_payload()
        payload["cases"][0]["relevant_ids"] = ["absent-row"]
        self.assertEqual("invalid_corpus", self._reject(payload).code)

    def test_the_evidence_role_is_vocabulary_checked(self):
        self.assertEqual("invalid_corpus",
                         self._reject(_minimal_payload(role="whatever")).code)


class LeakScanTests(unittest.TestCase):
    def test_a_regression_query_reused_as_calibration_is_a_leak(self):
        regression = _minimal_payload("regression_only")
        calibration = _minimal_payload("calibration")
        calibration["cases"][0]["query"] = regression["cases"][0]["query"]
        leaks = subject.leak_scan(regression, calibration)
        self.assertEqual(["calibration_corpus"], [leak["where"] for leak in leaks])

    def test_a_regression_query_appearing_in_implementation_source_is_a_leak(self):
        regression = _minimal_payload("regression_only")
        regression["cases"][0]["query"] = "a very distinctive held out phrase"
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test_impl.py"
            source.write_text(
                'assert search("a very distinctive held out phrase")\n', encoding="utf-8")
            leaks = subject.leak_scan(
                regression, _minimal_payload("calibration"), [source])
        self.assertEqual(["implementation_source"], [leak["where"] for leak in leaks])

    def test_disjoint_corpora_report_no_leak(self):
        regression = _minimal_payload("regression_only")
        regression["cases"][0]["query"] = "held out phrase nothing else uses"
        self.assertEqual(
            [], subject.leak_scan(regression, _minimal_payload("calibration")))


class ScoringTests(unittest.TestCase):
    def test_rank_one_scores_perfectly_and_absence_scores_zero(self):
        self.assertEqual(
            {"recall_at_10": 1.0, "mrr_at_10": 1.0, "ndcg_at_10": 1.0},
            subject.score_case(["a", "b"], ["a"]))
        self.assertEqual(
            {"recall_at_10": 0.0, "mrr_at_10": 0.0, "ndcg_at_10": 0.0},
            subject.score_case(["b", "c"], ["a"]))

    def test_reciprocal_rank_follows_position(self):
        self.assertEqual(0.5, subject.score_case(["x", "a"], ["a"])["mrr_at_10"])

    def test_results_past_k_do_not_count(self):
        returned = [f"pad{i}" for i in range(subject.RECALL_K)] + ["a"]
        self.assertEqual(0.0, subject.score_case(returned, ["a"])["recall_at_10"])


class ShippedCorpusProbeTests(unittest.TestCase):
    """AC-7: the runner must DETECT both known-bad states, reject a leak, and
    stay inside the fixed corpus and runtime bounds."""

    @classmethod
    def setUpClass(cls):
        if not (CALIBRATION.is_file() and REGRESSION.is_file()):
            raise unittest.SkipTest("lexical corpora are not present in this tree")
        cls.calibration = subject.load_corpus(CALIBRATION)
        cls.regression = subject.load_corpus(REGRESSION)

    def test_both_corpora_are_excluded_from_the_retrieval_index(self):
        # A corpus that can be retrieved would let the evaluator answer its own
        # questions.  Same contamination class the adjudication manifest hit.
        retrieval_eval.assert_eval_artifacts_excluded(
            REPO_ROOT, [CALIBRATION, REGRESSION], indexer)

    def test_the_shipped_corpora_do_not_leak_into_each_other(self):
        self.assertEqual([], subject.leak_scan(self.regression, self.calibration))

    def test_the_tail_identifier_now_survives_the_cap_and_is_retrieved(self):
        # This assertion was written inverted, against the pre-change code: the
        # identifier did NOT survive and the case scored Recall@10 of 0.0.  The
        # 1wpid token-selection mechanism flipped it, and the flip is the
        # evidence AC-1 asks for.  The cap itself is unchanged, which is the
        # safety property the repair had to preserve.
        probe = subject.tail_token_probe(Path("."), identifier="CALIBRATION_TAIL_SYMBOL")
        self.assertTrue(probe["identifier_survived"])
        self.assertTrue(probe["within_cap"])
        self.assertEqual(indexer_max_tokens(), probe["match_terms"])

        with tempfile.TemporaryDirectory() as tmp:
            index_dir = Path(tmp) / "idx"
            subject.build_disposable_store(index_dir, self.calibration["rows"])
            case = next(c for c in self.calibration["cases"]
                        if c["id"] == "cal-tail-identifier")
            measured = subject.measure_case(index_dir, case)
        self.assertEqual(1.0, measured["recall_at_10"])
        self.assertEqual(1.0, measured["ndcg_at_10"])

    def test_the_held_back_regression_corpus_also_recovers_its_tail_identifier(self):
        # Delivery non-regression evidence on the protected artifact, whose
        # filler vocabulary is disjoint from calibration so a mechanism fitted
        # to the calibration filler words would not pass here.  This is
        # regression_only evidence and supports no improvement claim.
        with tempfile.TemporaryDirectory() as tmp:
            index_dir = Path(tmp) / "idx"
            subject.build_disposable_store(index_dir, self.regression["rows"])
            case = next(c for c in self.regression["cases"]
                        if c["id"] == "reg-tail-identifier")
            measured = subject.measure_case(index_dir, case)
        self.assertEqual(1.0, measured["recall_at_10"])

    def test_rank_fusion_holds_the_order_that_raw_bm25_reversed(self):
        # The repaired contract, measured on both frozen corpora.  Under raw
        # bm25 the same growth reversed these rows; under reciprocal-rank
        # fusion neither row's rank within its own table moves, so the merged
        # order cannot move either.
        import index_state_store as store

        def fused(index_dir, case):
            per = {}
            for table in ("docs", "code"):
                rows = store.fts_search(index_dir, table, case["query"], limit=10)
                rows.sort(key=lambda h: h.get("bm25", 0.0))
                per[table] = rows
            tracked = set(case["relevant_ids"])
            return [r["id"] for r in store.fuse_lexical_tables(per) if r["id"] in tracked]

        for corpus, case_id in ((self.calibration, "cal-cross-table-order"),
                                (self.regression, "reg-cross-table-order")):
            case = next(c for c in corpus["cases"] if c["id"] == case_id)
            with self.subTest(case=case_id), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                base = root / "base"
                subject.build_disposable_store(base, corpus["rows"])
                before = fused(base, case)

                grown = {t: list(r) for t, r in corpus["rows"].items()}
                grown["docs"] = grown["docs"] + [
                    {"id": f"filler-{i}", "path": f"filler/{i}.md",
                     "text": "unrelated padding prose"} for i in range(32)]
                grown_dir = root / "grown"
                subject.build_disposable_store(grown_dir, grown)
                after = fused(grown_dir, case)

                self.assertEqual(2, len(before), before)
                self.assertEqual(before, after)

    def test_raw_bm25_still_demonstrates_the_defect_the_fusion_repairs(self):
        case = next(c for c in self.calibration["cases"]
                    if c["id"] == "cal-cross-table-order")
        with tempfile.TemporaryDirectory() as tmp:
            counter = [0]

            def factory(tag):
                counter[0] += 1
                return Path(tmp) / f"probe-{tag}-{counter[0]}"

            # Without growth both rows are returned in code-first order.
            index_dir = Path(tmp) / "base-order"
            subject.build_disposable_store(index_dir, self.calibration["rows"])
            baseline = subject.measure_case(index_dir, case)
            self.assertEqual(1.0, baseline["recall_at_10"])

            probe = subject.corpus_growth_probe(
                factory, self.calibration["rows"], case, filler_rows=32)
        # Neither row's content changed, yet their order did.
        self.assertTrue(probe["order_reversed"])
        self.assertEqual(sorted(probe["order_before"]), sorted(probe["order_after"]))
        self.assertNotEqual(probe["order_before"], probe["order_after"])

    def test_the_whole_calibration_pass_stays_inside_the_runtime_budget(self):
        started = time.perf_counter()
        with tempfile.TemporaryDirectory() as tmp:
            index_dir = Path(tmp) / "idx"
            subject.build_disposable_store(index_dir, self.calibration["rows"])
            for case in self.calibration["cases"]:
                subject.measure_case(index_dir, case)
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, subject.RUNNER_BUDGET_SECONDS)

    def test_every_case_is_measured_with_exactly_three_repetitions(self):
        calls = []
        real = subject._search

        def counting(index_dir, table, query, limit):
            calls.append(query)
            return real(index_dir, table, query, limit)

        case = self.calibration["cases"][0]
        with tempfile.TemporaryDirectory() as tmp:
            index_dir = Path(tmp) / "idx"
            subject.build_disposable_store(index_dir, self.calibration["rows"])
            subject._search = counting
            try:
                subject.measure_case(index_dir, case)
            finally:
                subject._search = real
        # Requirement 9 fixes these numbers: one untimed warm-up plus EXACTLY
        # three measured repetitions.  Pin the literals, not the constants --
        # comparing a constant to itself passes for any value and pins nothing.
        self.assertEqual(1, subject.WARMUP_REPETITIONS)
        self.assertEqual(3, subject.MEASURED_REPETITIONS)
        self.assertEqual(4, len(calls))

    def test_the_corpora_stay_inside_the_row_cap(self):
        for corpus, name in ((self.calibration, "calibration"), (self.regression, "regression")):
            for table, rows in corpus["rows"].items():
                with self.subTest(corpus=name, table=table):
                    self.assertLessEqual(len(rows), subject.MAX_ROWS_PER_TABLE)


def indexer_max_tokens() -> int:
    import index_state_store
    return index_state_store.FTS_QUERY_MAX_TOKENS


if __name__ == "__main__":
    unittest.main()

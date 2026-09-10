"""Reject event-evaluation false positives without running model inference."""
import copy
import unittest

from sqlite_event_eval import FILES, compare_reports, response_classification, validate_markers


class EventOracleTests(unittest.TestCase):
    def test_each_layer_requires_both_sentinels_and_exact_revision(self):
        for reader, paths in ((0, FILES[:2]), (1, FILES[2:])):
            good = {path: ["revision_epoch_2"] for path in paths}
            validate_markers(good, reader, "2")
            for bad in ({paths[0]: good[paths[0]]}, {},
                        {paths[0]: good[paths[0]], paths[1]: ["revision_epoch_1"]}):
                with self.assertRaises(RuntimeError):
                    validate_markers(bad, reader, "2")
            with self.assertRaises(RuntimeError):
                validate_markers(good, reader, None)
            validate_markers({}, reader, None)

    def test_status_errors_are_not_all_expected_epoch_refusals(self):
        self.assertEqual(response_classification("error", None, ["index_not_ready"]), "epoch_refusal")
        self.assertEqual(response_classification("error", None, ["query_failed"]), "unexpected_error")
        self.assertEqual(response_classification("ok", "live_fallback", []), "degraded")
        self.assertEqual(response_classification("ok", "semantic", []), "indexed")

    def test_paired_gate_rejects_missing_coverage_errors_and_regression(self):
        report = {
            "status": "measured", "requested_cycles": 10,
            "cycles": [{"coverage": {"before": True, "during": True, "after": True},
                        "reader_errors": []} for _ in range(20)],
            "reader_count": 4, "queries_per_reader_per_phase": 10,
            "schedule_seconds": list(range(0, 30, 3)), "monitor": {"quiet_period_seconds": 5},
            "provider_request": "cpu", "models": {"docs": "same-model"},
            "observed_models": {"embedders": {"same-model": {"session_providers": ["CPUExecutionProvider"], "input_shapes": [[1, 512]]}},
                                "reranker": {"session_providers": ["CPUExecutionProvider"], "input_shapes": [[1, 512]]}},
            "initial_inventory": {"docs": {"id": "same-text"}},
            "attempted": 800, "unavailable": 100, "errors": 0,
            "unexpected_error_responses": 0, "accepted_mixed": 0,
            "event_to_searchable": {"p95_ms": 1000},
        }
        report["final_observed_models"] = copy.deepcopy(report["observed_models"])
        self.assertTrue(compare_reports(report, copy.deepcopy(report))["passed"])
        for key, value in (("unavailable", 101), ("unexpected_error_responses", 1),
                           ("attempted", 799), ("event_to_searchable", {"p95_ms": 1101}),
                           ("provider_request", "coreml"), ("final_observed_models", {})):
            candidate = copy.deepcopy(report)
            candidate[key] = value
            self.assertFalse(compare_reports(report, candidate)["passed"], key)
        candidate = copy.deepcopy(report)
        candidate["cycles"][0]["coverage"]["during"] = False
        self.assertFalse(compare_reports(report, candidate)["passed"])


if __name__ == "__main__":
    unittest.main()

"""Tests for the memory-retrieval policy and candidate evaluation.

The fusion candidate stays measurement-only unless its explicit adoption gate
passes; these tests pin the expanded policy corpus, privacy boundary, and
deterministic candidate controls.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
import inspect
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "tests"))
# Wave 1tgws: the eval engine ships as a framework module; the golden fixture
# it reads for the hermetic pass stays here as test scaffolding.
import memory_eval as evalh  # noqa: E402
from perf_budget_policy import assert_operation_within_budget  # noqa: E402


class MemoryEvalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        (self.root / "docs" / "agents").mkdir(parents=True)

    def test_fixture_covers_expanded_policy_categories(self):
        report = evalh.run(self.root)
        cats = {c["category"] for c in report["cases"]}
        self.assertEqual(
            cats,
            {
                "exact_target", "paraphrase", "no_index", "decay",
                "supersession", "archive_pointer", "archive_history",
                "old_authoritative", "new_low_confidence", "adaptive_cadence",
                "fragile_reverification",
            },
        )

    def test_all_policy_invariants_pass(self):
        report = evalh.run(self.root)
        ov = report["overall"]
        self.assertEqual(ov["invariants_total"], 11)
        self.assertEqual(ov["invariants_passed"], ov["invariants_total"],
                         [c for c in report["cases"] if not c["invariant_pass"]])
        self.assertEqual(
            ov["candidate_invariants_passed"],
            ov["invariants_total"],
            [c for c in report["cases"] if not c["candidate_invariant_pass"]],
        )

    def test_recall_and_mrr_reported_per_case(self):
        report = evalh.run(self.root)
        for c in report["cases"]:
            self.assertIn("recall_at_k", c)
            self.assertIn("mrr", c)
            self.assertGreaterEqual(c["recall_at_k"], 0.0)

    def test_recorded_baseline_and_candidate_controls_are_complete(self):
        report = evalh.run(self.root)
        comp = report["comparison"]
        self.assertEqual(
            set(comp),
            {"baseline", "candidate", "semantic_only", "lexical_only"},
        )
        for metrics in comp.values():
            self.assertEqual(set(metrics), {"recall_at_k", "mrr"})
        self.assertEqual(comp["baseline"]["recall_at_k"], 1.0)
        self.assertFalse(report["adoption_gate"]["adopt"])
        self.assertIn(
            "curated corpus pass unavailable",
            report["adoption_gate"]["reasons"],
        )
        self.assertFalse(report["adoption_gate"]["product_path_changed"])

    def test_failed_gate_leaves_no_product_fusion_branch(self):
        import server_impl

        body = inspect.getsource(server_impl.memory_search_response)
        self.assertNotIn("lexical_bm25_order", body)
        self.assertNotIn("reciprocal_rank_fusion", body)
        self.assertNotIn("enable_memory_fusion", body.lower())

    def test_hermetic_reproducible(self):
        # Two independent runs over freshly-built corpora yield the same report.
        first = evalh.run(self.root)
        with tempfile.TemporaryDirectory() as tmp2:
            root2 = Path(tmp2) / "repo"
            (root2 / "docs" / "agents").mkdir(parents=True)
            second = evalh.run(root2)
        self.assertEqual(first["overall"], second["overall"])
        self.assertEqual(first["comparison"], second["comparison"])
        self.assertEqual(first["fixture_fingerprint"], second["fixture_fingerprint"])

    def test_rrf_is_deterministic_and_uses_positive_match_union(self):
        first = evalh.reciprocal_rank_fusion(
            [["mem-b", "mem-a"], ["mem-a", "mem-c"]]
        )
        second = evalh.reciprocal_rank_fusion(
            [["mem-b", "mem-a"], ["mem-a", "mem-c"]]
        )
        self.assertEqual(first, second)
        self.assertEqual(first, ["mem-a", "mem-b", "mem-c"])

    def test_engine_ships_and_hermetic_fixture_is_test_scaffolding(self):
        """Wave 1tgws: the engine packages; the golden fixture does not."""
        import build_pack

        def rel(path):
            return str(path.relative_to(_SCRIPTS.parent)).replace("\\", "/")

        engine = Path(evalh.__file__).resolve()
        self.assertEqual(engine.parent, _SCRIPTS,
                         "the eval engine must live in shippable framework source")
        self.assertFalse(
            build_pack.should_exclude(rel(engine), engine.name),
            "build_pack must include the relocated eval engine",
        )
        # The hermetic fixture is test scaffolding under the excluded tests dir.
        fixture = evalh._FIXTURE_PATH
        self.assertTrue(
            build_pack.should_exclude(rel(fixture), fixture.name),
            "the golden fixture stays test-only",
        )

    def test_curated_pass_never_rebinds_the_shared_commit_times_global(self):
        """Wave 1tis8 blocking P2: overlapping evals corrupted adaptive freshness.

        ``run_curated`` used to swap ``index_state_store.file_commit_times``
        for a frozen-subset lambda and restore it in a ``finally``. In the
        long-lived MCP server two overlapping ``wf_memory_eval`` calls restore
        OUT OF ORDER, permanently leaving one call's lambda installed, and
        unrelated concurrent readers observe the replacement meanwhile.

        This drives the REAL ``run_curated`` path (the MCP-exposed one where
        the corruption occurred), forces genuine overlap with a barrier,
        propagates worker failures through futures, and probes a path that is
        deliberately NOT one of the sampled records' targets — under the old
        behaviour that lookup returned ``{}``.
        """
        import concurrent.futures
        import threading
        import server_impl as srv

        # Structural: no eval entry point may assign the shared global.
        for fn in (evalh.run, evalh.run_curated):
            self.assertNotIn(
                "file_commit_times =", inspect.getsource(fn),
                f"{fn.__name__} must not rebind the shared commit-times global",
            )

        evalh.run(self.root)  # real corpus + seeded fixture histories
        # Seed one extra path that no memory record targets, so it can never be
        # part of run_curated's frozen subset. A leftover frozen lambda would
        # answer {} for it; the real store answers with its rows.
        unrelated = "docs/agents/memory/zz-unrelated-probe.md"
        histories = {
            path: [int(ts) for ts in values]
            for path, values in evalh.load_fixture().get("commit_times", {}).items()
        }
        histories[unrelated] = [1_700_000_000, 1_700_086_400]
        evalh._seed_commit_history(srv, self.root, histories)

        index_store = srv._load_script("index_state_store")
        original = index_store.file_commit_times
        index_dir = self.root / ".wavefoundry" / "index"

        class _DeterministicIndex:
            """Stand-in for the semantic index so the curated pass runs."""

            def __init__(self, root):
                self.root = root

            def _ensure_loaded(self):
                return None

            def search_docs(self, query, top_n=20):
                return ([], False)

        real_index = srv.WaveIndex
        srv.WaveIndex = _DeterministicIndex
        self.addCleanup(setattr, srv, "WaveIndex", real_index)

        barrier = threading.Barrier(2)
        samples: list[bool] = []
        stop = threading.Event()

        def watch():
            while not stop.is_set():
                samples.append(index_store.file_commit_times is original)
                time.sleep(0.0005)

        def one():
            barrier.wait(timeout=60)  # force the two passes to genuinely overlap
            return evalh.run_curated(self.root)

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(one) for _ in range(2)]
                # .result() re-raises anything a worker raised: a crashed
                # worker fails this test instead of passing silently.
                reports = [f.result(timeout=180) for f in futures]
        finally:
            stop.set()
            watcher.join(timeout=5)

        for report in reports:
            self.assertTrue(
                report["available"],
                f"curated pass must do real work: {report.get('unavailable_reason')}",
            )
            self.assertGreater(report["sample_size"], 0)
            self.assertIn("metrics", report)

        self.assertTrue(samples, "watcher must have sampled the global")
        self.assertTrue(
            all(samples),
            "a concurrent reader observed a replaced file_commit_times global",
        )
        self.assertIs(
            index_store.file_commit_times, original,
            "overlapping curated passes left a frozen-subset lambda installed",
        )
        probe = index_store.file_commit_times(index_dir, [unrelated])
        self.assertTrue(
            probe.get(unrelated),
            "an unrelated path must still resolve after concurrent curated "
            "passes (a leftover frozen subset answered {} here)",
        )

    def test_frozen_histories_reach_ranking_without_global_mutation(self):
        """The explicit override is what actually feeds adaptive decay."""
        import server_impl as srv

        evalh.run(self.root)
        mem = srv._memory_mod()
        records = mem.load_memory_records(
            self.root, statuses=list(mem.DEFAULT_SURFACED_STATUSES)
        )
        # Only churn-decayed kinds derive a commit-cadence half-life; protected
        # kinds and fragile_file deliberately do not, so anchor on a tactical
        # record and compare its derived half-life with and without histories.
        tactical = [
            record for record in records
            if record.get("kind") in mem.CHURN_DECAYED_KINDS
            and [ref for ref in (record.get("target_refs") or [])
                 if not ref.startswith(("symbol:", "community:"))]
        ]
        self.assertTrue(tactical, "corpus should carry a churn-decayed record")
        record = tactical[0]
        target = next(
            ref for ref in record["target_refs"]
            if not ref.startswith(("symbol:", "community:"))
        )

        def halving_for(override):
            ranked = srv._memory_ranked(
                self.root, [record], commit_times_override=override
            )
            return ranked[0][1].get("halving_commits")

        # No history -> the documented static default.
        self.assertEqual(halving_for({}), mem.CHURN_DECAY_HALVING_COMMITS)
        # A dense daily cadence passed EXPLICITLY -> clamped adaptive maximum.
        daily = list(range(1_700_000_000, 1_700_000_000 + 40 * 86400, 86400))
        self.assertEqual(
            halving_for({target: daily}),
            mem.ADAPTIVE_CHURN_MAX_HALVING_COMMITS,
            "explicit frozen histories must reach adaptive cadence derivation",
        )

    def test_memory_eval_tool_reports_aggregate_only(self):
        """The MCP envelope carries metrics/counts/fingerprint, never records."""
        import server_impl as srv

        report = srv.wf_memory_eval_response(self.root)
        self.assertEqual(report["status"], "ok")
        data = report["data"]
        self.assertIn("available", data)
        self.assertIn("fingerprint", data)
        self.assertIn("counts_by_kind", data)

        # Structural privacy check: walk the envelope and assert no key that
        # would carry per-record content appears anywhere. Substring matching
        # would false-trip on legitimate prose (an unavailable_reason naming
        # "records"), so inspect keys, not the serialized blob.
        forbidden = {"memory_id", "summary", "records", "target_refs", "body"}
        def walk(node, path="data"):
            if isinstance(node, dict):
                for key, value in node.items():
                    self.assertNotIn(
                        key, forbidden,
                        f"per-record key {key!r} leaked at {path}",
                    )
                    walk(value, f"{path}.{key}")
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    walk(value, f"{path}[{i}]")
        walk(data)

        if not data["available"]:
            self.assertEqual(
                [d["code"] for d in report["diagnostics"]],
                ["curated_pass_unavailable"],
                "an unavailable pass is an explicit diagnostic, not a failure",
            )
            self.assertIn(
                data["unavailable_reason"],
                report["diagnostics"][0]["message"],
                "the diagnostic must carry the engine's actual reason",
            )

    def test_empty_relevance_union_yields_zero_candidates(self):
        import server_impl as srv

        evalh.run(self.root)  # build the frozen corpus
        mem = srv._memory_mod()
        records = mem.load_memory_records(
            self.root, statuses=list(mem.DEFAULT_SURFACED_STATUSES)
        )
        self.assertTrue(records, "corpus should surface records to be a real test")

        # Query path: an empty relevance union means neither the lexical nor the
        # semantic stream matched, so the positive-match-union contract admits
        # zero candidates regardless of how many records are surfaced.
        self.assertEqual(evalh._policy_order(srv, self.root, records, []), [])

        # Baseline/prefiltered path: an already-filtered candidate list is
        # ordered by policy alone; an empty order does not restrict it.
        prefiltered = evalh._policy_order(
            srv, self.root, records, [], prefiltered=True
        )
        self.assertEqual(
            set(prefiltered), {r["memory_id"] for r in records}
        )

        # Integration: a query that matches nothing (no lexical tokens present,
        # no semantic index) yields zero on the candidate and both controls.
        case = {"query": "zzzznomatchtoken", "no_index": True}
        controls = evalh._candidate_and_controls(
            srv, self.root, case, records_override=records
        )
        self.assertEqual(controls["candidate"], [])
        self.assertEqual(controls["lexical_only"], [])
        self.assertEqual(controls["semantic_only"], [])

    def test_curated_unavailable_report_is_aggregate_only(self):
        report = evalh.run_curated(self.root)
        self.assertFalse(report["available"])
        self.assertIn("fingerprint", report)
        self.assertIn("counts_by_kind", report)
        self.assertNotIn("memory_id", report)
        self.assertNotIn("summary", report)
        self.assertNotIn("records", report)

    def test_lexical_evaluation_has_registered_contention_safe_budget(self):
        records = [
            {
                "memory_id": f"mem-{index}",
                "summary": f"cache refresh policy token {index}",
                "title": "memory",
                "evidence_refs": ["evidence"],
                "target_refs": [f"src/{index}.py"],
                "keywords": ["refresh"],
            }
            for index in range(1000)
        ]
        started = time.perf_counter()
        ranked = evalh.lexical_bm25_order(records, "cache refresh policy")
        elapsed = time.perf_counter() - started
        self.assertEqual(len(ranked), 1000)
        assert_operation_within_budget(
            self, "1000-record memory lexical evaluation", elapsed
        )


if __name__ == "__main__":
    unittest.main()

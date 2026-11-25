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
import copy
import hashlib
import sqlite3
import struct
from unittest.mock import patch
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "tests"))
# Wave 1tgws: the eval engine ships as a framework module; the golden fixture
# it reads for the hermetic pass stays here as test scaffolding.
import memory_eval as evalh  # noqa: E402
from perf_budget_policy import assert_operation_within_budget  # noqa: E402



def _null_read_snapshot(testcase):
    """Wave 248lb fixture rule: a mock index with no store reads through a null
    snapshot. Patches the module instance the handlers load, not the public
    import; production code never makes the snapshot optional."""
    import contextlib
    import wf_server.server_impl as server_impl
    patcher = patch.object(server_impl._load_script("sqlite_vector_store"), "read_snapshot",
                           lambda index_dir: contextlib.nullcontext())
    patcher.start()
    testcase.addCleanup(patcher.stop)

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
                "supersession", "archive_register_entry", "archive_history",
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
            ov["invariants_total"] - 1,
            [c for c in report["cases"] if not c["candidate_invariant_pass"]],
        )
        self.assertEqual(
            [c["category"] for c in report["cases"] if not c["candidate_invariant_pass"]],
            ["paraphrase"],  # legacy confidence-first control is deliberately superseded
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

    def test_unselected_fusion_controls_are_not_product_variants(self):
        import server_impl

        body = inspect.getsource(server_impl._memory_query_records)
        self.assertIn("reciprocal_rank_fusion", body)
        self.assertNotIn("fusion_rankings", body)
        self.assertNotIn("score_fusion", body)
        self.assertNotIn("weighted025", body)

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
                self.index_dir = root / ".wavefoundry" / "index"
                self._docs_vector_layer = "docs"
                self._meta = {"project": {}}

            def _ensure_loaded(self):
                return None

            def _memory_query_vector(self, query):
                return query

            def _memory_dense_scores(self, query, paths, *, expected_hashes):
                return {"scores": {path: 1.0 for path in paths}, "complete": True,
                        "source_current": True}

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
            self.assertGreater(report["sanity_floor"]["sample_size"], 0)
            self.assertIn("metrics", report["sanity_floor"])

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

    def test_available_memory_eval_preserves_repository_files(self):
        from wf_server import server_impl as srv

        evalh.run(self.root)  # Populate historical records before measuring the read.
        # The hermetic run above reads through the real snapshot; only the
        # storeless _StubIndex([]) below needs the null snapshot.
        _null_read_snapshot(self)
        def snapshot():
            return {p.relative_to(self.root): p.read_bytes()
                    for p in self.root.rglob("*") if p.is_file()}

        before = snapshot()
        with patch.object(srv, "WaveIndex", return_value=evalh._StubIndex([])):
            result = srv.wf_memory_eval_response(self.root)
        self.assertEqual(result["status"], "ok", result)
        self.assertTrue(result["data"]["available"], result["data"])
        self.assertEqual(snapshot(), before)

    def test_memory_eval_tool_reports_aggregate_only(self):
        """The MCP envelope carries metrics/counts/fingerprint, never records."""
        import server_impl as srv

        # Change 246to: a real corpus, so the id check below is not vacuous.
        mem = srv._memory_mod()
        golden = evalh.load_fixture()["records"]
        evalh.build_corpus(self.root, golden, mem)
        report = srv.wf_memory_eval_response(self.root)
        self.assertEqual(report["status"], "ok")
        data = report["data"]
        self.assertIn("available", data)
        self.assertIn("query_set", data)
        self.assertIn("counts_by_kind", data)
        self.assertEqual(data["maintenance_signals"]["active_records"],
                         len(mem.load_memory_records(self.root, statuses=["active"])))
        # No memory id string appears anywhere in the envelope (an id list
        # such as `coverage_gap_ids` fails here).
        blob = json.dumps(report)
        for record in golden:
            self.assertNotIn(record["memory_id"], blob)

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
        self.assertIn("query_set", report)
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


class QualificationTests(unittest.TestCase):
    def test_scoped_sql_groups_before_limit_and_preserves_database(self):
        import sqlite_vector_store as store

        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "fixture.sqlite"
            conn = sqlite3.connect(database)
            conn.executescript("CREATE TABLE chunks_docs(id INTEGER PRIMARY KEY,path TEXT);"
                               "CREATE TABLE vectors_docs(chunk_id INTEGER PRIMARY KEY,embedding BLOB);")
            second = "docs/agents/memory/quote'--.md"
            paths = ["docs/agents/memory/first.md", second]
            for i in range(31):
                path = paths[0] if i < 29 else second if i == 29 else "docs/unrelated.md"
                distance = 0.1 if i < 29 else 0.2 if i == 29 else 0.0
                conn.execute("INSERT INTO chunks_docs VALUES(?,?)", (i, path))
                conn.execute("INSERT INTO vectors_docs VALUES(?,?)", (i, struct.pack("<f", distance)))
            conn.commit()
            conn.close()
            original = hashlib.sha256(database.read_bytes()).digest()

            def readonly(_):
                db = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
                # Real SQL traversal and grouping; deterministic distance kernel
                # isolates query shape. Native sqlite-vec is qualified separately.
                db.create_function("vec_distance_cosine", 2, lambda blob, query: struct.unpack("<f", blob)[0])
                return db

            with patch.object(store, "_open", side_effect=readonly):
                report = store.dense_path_scores(Path(tmp), "docs", [1.0] * store.DIMENSIONS, paths, limit=2)
                self.assertEqual(list(report["scores"]), paths)
                self.assertTrue(report["complete"])
                self.assertEqual(report["eligible_chunks"], 30)
                self.assertEqual(report["covered_paths"], 2)
                missing = store.dense_path_scores(Path(tmp), "docs", [1.0] * store.DIMENSIONS, paths + ["missing"])
                self.assertFalse(missing["complete"])
                self.assertEqual(missing["requested_paths"], 3)
            self.assertEqual(hashlib.sha256(database.read_bytes()).digest(), original)

    def test_curated_diagnostic_is_nonqualifying_and_query_failures_do_not_leak(self):
        import server_impl as srv

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = {"memory_id": "private-record-unique", "kind": "successful_pattern",
                      "status": "active", "summary": "private-query-unique", "target_refs": ["private/path"],
                      "evidence_refs": [], "confidence": .8}
            class BrokenIndex:
                def __init__(self, root):
                    self.index_dir = root / ".wavefoundry" / "index"
                    self._docs_vector_layer = "docs"
                    self._meta = {"project": {}}
                def _ensure_loaded(self):
                    pass
                def _memory_query_vector(self, query):
                    return query
                def _memory_dense_scores(self, *args, **kwargs):
                    raise RuntimeError("private-query-unique private-record-unique")
            with patch.object(srv._memory_mod(), "load_memory_records", return_value=[record]), patch.object(srv, "WaveIndex", BrokenIndex):
                report = srv.wf_memory_eval_response(root)
            data = report["data"]
            self.assertFalse(data["available"])
            self.assertFalse(data["qualifying"])
            self.assertFalse(data["adoption_gate"]["adopt"])
            serialized = json.dumps(report)
            for secret in ("private-record-unique", "private-query-unique", "private/path"):
                self.assertNotIn(secret, serialized)

    def test_curated_code_only_index_is_unavailable_not_empty_semantic_success(self):
        import server_impl as srv
        _null_read_snapshot(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = {"memory_id": "memory-a", "kind": "successful_pattern",
                      "status": "active", "summary": "cache policy", "target_refs": ["src/cache.py"],
                      "evidence_refs": [], "confidence": .8}
            index = object.__new__(srv.WaveIndex)
            index.index_dir = root / ".wavefoundry" / "index"
            index._loaded = False
            index._loaded_meta_signature = {}
            index._index_meta_signature = lambda directory: ("complete", 1)
            index._open_vector_layer = lambda layer, kind: "code" if kind == "code" else None
            # Execute the real loader: a complete code-only index is valid for
            # code search, but cannot supply memory's docs-vector measurement.
            index._ensure_loaded()
            self.assertTrue(index._loaded)
            self.assertIsNone(index._docs_vector_layer)
            self.assertEqual(index._code_vector_layer, "code")
            # The product docs path returns no hits with no table. A stand-in
            # avoids embedding an irrelevant query if this guard is mutated.
            index.search_docs = lambda *args, **kwargs: ([], False)
            with patch.object(srv._memory_mod(), "load_memory_records", return_value=[record]), patch.object(srv, "WaveIndex", return_value=index):
                response = srv.wf_memory_eval_response(root)
            report = response["data"]
            self.assertFalse(report["available"])
            self.assertEqual(report["unavailable_reason"], "semantic docs layer unavailable")
            self.assertNotIn("metrics", report)
            self.assertFalse(report["adoption_gate"]["adopt"])

    def test_fusion_caps_each_channel_and_handles_negative_cosine(self):
        dense = {f"dense-{i:02d}": -i / 100 for i in range(25)}
        lexical = {f"lex-{i:02d}": 30 - i for i in range(25)}
        result = evalh.fusion_rankings(dense, lexical)
        eligible = set(sorted(dense)[:20]) | set(sorted(lexical)[:20])
        self.assertEqual(len(result["semantic"]), 20)
        self.assertEqual(len(result["lexical"]), 20)
        for ranking in result.values():
            self.assertLessEqual(len(ranking), 20)
            self.assertEqual(len(ranking), len(set(ranking)))
            self.assertLessEqual(set(ranking), eligible)
        self.assertEqual(result, evalh.fusion_rankings(dict(reversed(list(dense.items()))), lexical))
        for cap in (0, 21, True):
            with self.assertRaises(ValueError):
                evalh.fusion_rankings(dense, lexical, cap)
        with self.assertRaises(ValueError):
            evalh.fusion_rankings({"bad": float("nan")}, {})

    def test_score_normalization_is_capped_and_constant_channels_are_ties(self):
        result = evalh.fusion_rankings({"a": 0.9, "b": 0.8, "outlier": -100}, {}, 2)
        self.assertEqual(result["score_fusion"], ["a", "b"])
        self.assertEqual(evalh.fusion_rankings({"b": -0.5, "a": -0.5}, {})["rrf"], ["a", "b"])
        self.assertTrue(all(not v for v in evalh.fusion_rankings({}, {"zero": 0}).values()))

    def test_injection_requires_explicit_overlap_eligibility(self):
        dense, lexical = {"a": 0.8, "b": 0.7}, {"strong": 4, "weak": 1}
        self.assertEqual(evalh.fusion_rankings(dense, lexical)["injection"], ["a", "b"])
        self.assertEqual(evalh.fusion_rankings(dense, lexical, injection_eligible={"weak"})["injection"], ["a", "b"])
        self.assertEqual(evalh.fusion_rankings(dense, lexical, injection_eligible={"strong"})["injection"], ["a", "strong", "b"])

    def test_bm25_preserves_register_identities_and_rejects_body_duplicates(self):
        rows = [{"memory_id": mid, "summary": "cache policy", "path": "shared-manifest.md"}
                for mid in ("archive-a", "archive-b")]
        self.assertEqual(list(evalh.lexical_bm25_scores(rows, "cache")), ["archive-a", "archive-b"])
        with self.assertRaises(ValueError):
            evalh.lexical_bm25_scores(rows + rows[:1], "cache")

    def test_metrics_keep_negatives_empty_answers_and_unjudged_distinct(self):
        rows = [
            {"relevant_ids": ["a"], "rankings": {"v": []}, "candidate_ids": ["a"]},
            {"relevant_ids": ["b"], "irrelevant_ids": ["wrong"],
             "rankings": {"v": ["wrong", "b", "unknown", "b"]}, "candidate_ids": ["b"]},
            {"relevant_ids": [], "rankings": {"v": ["uncertain"]}},
            {"relevant_ids": [], "rankings": {"v": []}},
        ]
        metrics = evalh.quality_metrics(rows, "v")
        self.assertEqual(metrics["recall_at_3"], 0.5)
        self.assertEqual(metrics["mrr"], 0.25)
        self.assertEqual(metrics["candidate_recall"], 1)
        self.assertEqual(metrics["answerable_misses"], 1)
        self.assertEqual(metrics["no_match_false_positives"], 1)
        self.assertEqual(metrics["judged_irrelevant_results"], 1)
        self.assertEqual(metrics["unjudged_results"], 2)
        self.assertNotIn("unknown", json.dumps(metrics))
        rows[-1]["available"] = {"v": False}
        unavailable = evalh.quality_metrics(rows, "v")
        self.assertFalse(unavailable["available"])
        self.assertIsNone(unavailable["recall_at_3"])
        self.assertFalse(evalh.quality_metrics([], "v")["available"])

    def _manifest(self):
        corpus = {"records": [{"memory_id": "a"}], "archive_register": []}
        cases = [{"id": f"q-{i}", "split": "holdout", "query": f"independent question {i}",
                  "relevant_ids": ["a"] if i < 16 else [],
                  "irrelevant_ids": [] if i < 16 else ["a"], "unjudged_ids": []}
                 for i in range(24)]
        queries = {"reviewer": "qa", "cases": cases,
                   "development_cases": [{"query": "development question"}]}
        parameters = {"channel_cap": 20, "result_cap": 20, "rrf_k": 60,
                      "score_semantic_weight": .75, "normalization": "bounded-channel-minmax",
                      "relevance_text": "title-action-summary", "relevance_threshold": -4.0,
                      "qualification_cap": 20}
        manifest = {"schema_version": 1, "reviewer": "qa", "ranker_author": "impl",
                    "split_protocol": "independent queries before scoring", "parameters": parameters,
                    "gates": {"recall3_gain": .05, "latency_reduction": .20, "warm_p95_ms": 500},
                    "corpus_fingerprint": evalh.qualification_fingerprint(corpus),
                    "queries_fingerprint": evalh.qualification_fingerprint(queries),
                    "parameters_fingerprint": evalh.qualification_fingerprint(parameters)}
        return corpus, queries, manifest

    def test_manifest_pins_complete_inputs_and_reviewer_split(self):
        corpus, queries, manifest = self._manifest()
        self.assertTrue(evalh.validate_qualification_manifest(corpus, queries, manifest)["valid"])
        for kind in ("query", "corpus", "parameters", "author", "overlap", "labels"):
            c, q, m = copy.deepcopy((corpus, queries, manifest))
            if kind == "query":
                q["cases"][0]["query"] = "edited after freeze"
            elif kind == "corpus":
                c["records"][0]["summary"] = "edited"
            elif kind == "parameters":
                m["parameters"]["rrf_k"] = 61
            elif kind == "author":
                m["ranker_author"] = "qa"
            elif kind == "overlap":
                q["cases"][0]["query"] = "Development Question"
                m["queries_fingerprint"] = evalh.qualification_fingerprint(q)
            else:
                q["cases"][0]["irrelevant_ids"] = ["a"]
                m["queries_fingerprint"] = evalh.qualification_fingerprint(q)
            with self.subTest(kind=kind):
                self.assertFalse(evalh.validate_qualification_manifest(c, q, m)["valid"])

    def test_manifest_requires_explicit_judgments_and_rejects_malformed_corpus(self):
        corpus, queries, manifest = self._manifest()
        for value in (None, [7], {"a": {}}, [{"memory_id": ["a"]}]):
            with self.subTest(corpus=value):
                c = dict(corpus, records=value)
                m = dict(manifest, corpus_fingerprint=evalh.qualification_fingerprint(c))
                self.assertFalse(evalh.validate_qualification_manifest(c, queries, m)["valid"])
        for label_change in ({}, {"relevant_ids": None}, {"irrelevant_ids": "a"},
                             {"unjudged_ids": [{}]}, {"irrelevant_ids": []}):
            q = copy.deepcopy(queries)
            case = q["cases"][-1]
            if not label_change:
                for key in ("relevant_ids", "irrelevant_ids", "unjudged_ids"):
                    case.pop(key)
            else:
                case.update(label_change)
            m = dict(manifest, queries_fingerprint=evalh.qualification_fingerprint(q))
            with self.subTest(labels=label_change):
                self.assertFalse(evalh.validate_qualification_manifest(corpus, q, m)["valid"])

    def test_adoption_rejects_missing_evidence_regressions_and_timing_shortcuts(self):
        baseline = {"available": True, "queries": 24, "answerable_queries": 16,
                    "no_match_queries": 8, "recall_at_3": .8, "recall_at_10": 1.,
                    "mrr": .9, "answerable_misses": 0, "no_match_false_positives": 2}
        candidate = dict(baseline, recall_at_3=.9)
        latencies = {"baseline_p95_ms": 100, "candidate_p95_ms": 95,
                     "baseline_warm_calls": 100, "candidate_warm_calls": 100}
        validity = dict.fromkeys(("manifest_valid", "independent_labels", "holdout_untouched",
                                  "coverage_complete", "policy_approved", "performance_complete"), True)
        self.assertTrue(evalh.qualification_adoption(baseline, candidate, latencies, validity)["adopt"])
        for key in validity:
            self.assertFalse(evalh.qualification_adoption(baseline, candidate, latencies, dict(validity, **{key: False}))["adopt"])
        for change in ({"mrr": .8}, {"answerable_misses": 1}, {"no_match_false_positives": 3},
                       {"available": False}, {"recall_at_10": float("nan")}, {"queries": 23}):
            self.assertFalse(evalh.qualification_adoption(baseline, dict(candidate, **change), latencies, validity)["adopt"])
        for change in ({"candidate_warm_calls": 99}, {"candidate_p95_ms": 101},
                       {"candidate_p95_ms": float("inf")}, {"baseline_p95_ms": 0}):
            self.assertFalse(evalh.qualification_adoption(baseline, candidate, dict(latencies, **change), validity)["adopt"])
        self.assertFalse(evalh.qualification_adoption(baseline, baseline, latencies, validity)["adopt"])
        self.assertTrue(evalh.qualification_adoption(baseline, baseline, dict(latencies, candidate_p95_ms=80), validity)["adopt"])

        # Matching populations and a speed win cannot rescue impossible counts.
        for change in ({"queries": -24, "answerable_queries": -16, "no_match_queries": -8},
                       {"queries": True, "answerable_queries": True, "no_match_queries": True},
                       {"queries": 24, "answerable_queries": 30, "no_match_queries": 8},
                       {"queries": 23, "answerable_queries": 15, "no_match_queries": 8},
                       {"queries": 24, "answerable_queries": 17, "no_match_queries": 7},
                       {"answerable_misses": 17}, {"no_match_false_positives": 9}):
            with self.subTest(populations=change):
                self.assertFalse(evalh.qualification_adoption(
                    dict(baseline, **change), dict(candidate, **change),
                    dict(latencies, candidate_p95_ms=80), validity,
                )["adopt"])


# --- Wave 245na (change 245sp): situation-language queries and baselines ----

_R1_SUMMARY = ("After an upgrade restart the MCP server so newly installed package code "
               "loads; the old process keeps stale modules imported.")
_FIXTURE_RECORDS = [
    {"memory_id": "r1", "kind": "environment_gotcha", "confidence": 0.8, "status": "active",
     "summary": _R1_SUMMARY, "evidence": ["1abcd-bug upgrade-stale-modules"],
     "targets": ["src/setup.py"], "created": "2026-07-10"},
    {"memory_id": "r2", "kind": "decision", "confidence": 0.8, "status": "active",
     "summary": "Ledger writes go through the single event writer with an fsync fence.",
     "evidence": ["1abce-enh ledger-writer"], "targets": ["src/ledger.py"], "created": "2026-07-10"},
    {"memory_id": "r3", "kind": "failed_attempt", "confidence": 0.8, "status": "active",
     "summary": "Patching the chunker regex for nested braces broke string literal spans.",
     "evidence": ["1abcf-bug chunker-braces"], "targets": ["src/chunker.py"], "created": "2026-07-10"},
    {"memory_id": "r4", "kind": "fragile_file", "confidence": 0.8, "status": "active",
     "summary": "The dashboard renderer caches templates per process; edits need a restart.",
     "evidence": ["1abcg-bug dashboard-cache"], "targets": ["src/dashboard.py"], "created": "2026-07-10"},
    {"memory_id": "r5", "kind": "successful_pattern", "confidence": 0.8, "status": "active",
     "summary": "Pin release notes to the owning release section, never the latest one.",
     "evidence": ["1abch-doc release-notes"], "targets": ["CHANGELOG.md"], "created": "2026-07-10"},
    {"memory_id": "r9", "kind": "failed_attempt", "confidence": 0.6, "status": "superseded",
     "superseded_by": "r2", "archive": True,
     "summary": "Legacy ledger lockfile ritual before every write.",
     "evidence": ["1abci-bug ledger-lockfile"], "targets": ["src/ledgerlock.py"], "created": "2024-01-01"},
]


def _case(cid, case_type, source, relevant=(), stale=(), query=None, terms=("zzzz",)):
    return {"id": cid, "query": query or f"situation text for {cid} with distinct words",
            "case_type": case_type, "source_id": source, "relevant_ids": list(relevant),
            "stale_ids": list(stale), "grep_terms": list(terms), "author": "fixture author"}


def _ac1_cases():
    return [
        _case("q-001", "answerable", "r1", ["r1"]),
        _case("q-002", "answerable", "r2", ["r2"]),
        _case("q-003", "answerable", "r4", ["r4"]),
        _case("q-004", "null", "q-004"),
        _case("q-005", "null", "q-005"),
        _case("q-006", "stale", "r2", ["r2"], ["r9"]),
    ]


_AC1_SHOWN = [["r1", "r2"], ["r3", "r2"], ["r1"], [], ["r5"], ["r9", "r2"]]
_AC1_CORPUS = ["r1", "r2", "r3", "r4", "r5", "r9"]


def _pairs(rows):
    return [(list(row), list(row)) for row in rows]


def _vec(text):
    out = [0.0] * 16
    for token in str(text).lower().split():
        out[int(hashlib.sha256(token.encode()).hexdigest()[:4], 16) % 16] += 1.0
    out[0] += 0.01
    return out


class _VecEmbedder:
    def embed(self, texts):
        return [_vec(text) for text in texts]


class _ArmIndex:
    """Stand-in index: production's dense call shape, recorded; no model."""

    def __init__(self, root, order=(), *, source_current=True, complete=True):
        self.root = root
        self.index_dir = root / ".wavefoundry" / "index"
        self._docs_vector_layer = "docs"
        self._meta = {"project": {}}
        self.order = list(order)
        self.source_current = source_current
        self.complete = complete
        self.dense_calls = []
        self.search_docs_calls = 0

    def _ensure_loaded(self):
        return None

    def search_docs(self, *args, **kwargs):
        self.search_docs_calls += 1
        return ([], False)

    def _memory_query_vector(self, query):
        return query

    def _memory_dense_scores(self, query, paths, *, expected_hashes):
        self.dense_calls.append((query, sorted(paths), dict(expected_hashes)))
        if not self.source_current:
            return {"scores": {}, "complete": False, "source_current": False}
        ranks = {mid: i for i, mid in enumerate(self.order)}
        return {"scores": {p: 1.0 / (1 + ranks[Path(p).stem]) for p in paths
                           if Path(p).stem in ranks},
                "complete": self.complete, "source_current": True}

    def _indexer_constant(self, name):
        return "stub-docs-model"

    def _get_embedder(self, model):
        return _VecEmbedder()

    def _embed_query(self, text, model):
        return _vec(text)

    def _get_memory_reranker(self):
        return None


def _stub_freeze_embedder(high=()):
    """Queries in ``high`` embed identically to their summaries (cosine 1)."""
    def queries(texts):
        return [[1.0, 0.0] if text in high else [0.0, 1.0] for text in texts]

    def documents(texts):
        return [[1.0, 0.0] for _ in texts]
    return ("stub-docs-model", queries, documents)


class SituationQueryEvalTests(unittest.TestCase):
    def setUp(self):
        import server_impl as srv
        import wf_server.memory_handlers as memory_handlers
        self.srv = srv
        self.mh = memory_handlers
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "evals").mkdir(parents=True)
        evalh.build_corpus(self.root, _FIXTURE_RECORDS, srv._memory_mod())

    def write_set(self, cases, *, freeze=True, high=()):
        (self.root / evalh.QUERY_SET_PATH).write_text(
            json.dumps({"schema_version": 1, "cases": cases}, indent=2), encoding="utf-8")
        if freeze:
            return evalh.freeze_query_set(self.root, embedder=_stub_freeze_embedder(high))
        return None

    def production_stub(self, shown_by_query, *, fallback=None, raises=None):
        real = self.mh.memory_search_response
        calls = []

        def stub(root, query="", index=None, limit=10, **kwargs):
            if not query:
                return real(root, query=query, index=index, limit=limit, **kwargs)
            calls.append({"query": query, "index": index, "limit": limit})
            if raises is not None:
                raise raises
            reason = (fallback or {}).get(query)
            return {"data": {"records": [{"memory_id": mid} for mid in shown_by_query.get(query, [])],
                             "retrieval": {"qualification": "unavailable" if reason else "model_relevance",
                                           "fallback_reason": reason}}}
        return stub, calls

    # AC-1 -----------------------------------------------------------------
    def test_ac1_metrics_and_fixed_baselines(self):
        for key in ("r1", "r2", "r4", "q-004", "q-005"):
            self.assertEqual(evalh.split_for(key), "heldout", key)
        cases = _ac1_cases()
        scored = evalh.score_arms(cases, {
            "scored": _pairs(_AC1_SHOWN),
            "full_context": _pairs([_AC1_CORPUS] * 6),
            "no_memory": _pairs([[]] * 6),
        }, ordered_arms=("scored", "full_context", "no_memory"))
        held = scored["metrics"]["heldout"]
        self.assertEqual(scored["split_counts"]["dev"]["cases"], 0)
        row = held["scored"]
        self.assertEqual([row[k] for k in evalh.METRIC_KEYS], [0.75, 0.5, 0.4286, 0.5, 1.0])
        full = held["full_context"]
        self.assertEqual([full["recall_all"], full["mrr"], full["precision_shown"],
                          full["false_show_rate"], full["stale_shown_rate"], full["mean_shown"]],
                         [1.0, 0.5625, 0.1667, 1.0, 1.0, 6.0])
        self.assertNotIn("recall_at_5", full)
        empty = held["no_memory"]
        self.assertEqual([empty[k] for k in evalh.METRIC_KEYS], [0.0, 0.0, None, 0.0, 0.0])

        texts = {"r1": "lockfile then LOCKFILE", "r2": "ledger", "r3": "one lockfile", "r9": ""}
        self.assertEqual(evalh.grep_order(texts, ["lockfile"]), ["r1", "r3"])
        grep_case = dict(cases[3], grep_terms=["lockfile"])
        matched = evalh.grep_order(texts, grep_case["grep_terms"])
        only = evalh.score_arms([grep_case], {"grep": [(matched, matched)]},
                                ordered_arms=("grep",))
        self.assertEqual(only["metrics"]["heldout"]["grep"]["false_show_rate"], 1.0)

    # AC-2 -----------------------------------------------------------------
    def test_ac2_cluster_bootstrap_is_pinned(self):
        cases = _ac1_cases()
        outcomes = {"scored": _pairs(_AC1_SHOWN)}
        first = evalh.score_arms(cases, outcomes, ordered_arms=("scored",))
        second = evalh.score_arms(cases, outcomes, ordered_arms=("scored",))
        self.assertEqual(first, second)
        low, high = first["metrics"]["heldout"]["scored"]["intervals"]["mrr"]
        self.assertLess(low, 0.5)
        self.assertLess(0.5, high)

        perfect = [_case(f"p-{i}", "answerable", f"src-{i}", [f"m{i}"]) for i in range(8)]
        perfect_rows = _pairs([[f"m{i}"] for i in range(8)])
        result = evalh.score_arms(perfect, {"a": perfect_rows}, ordered_arms=("a",))
        for split, counts in result["split_counts"].items():
            if counts["cases"]:
                self.assertEqual(result["metrics"][split]["a"]["intervals"]["mrr"], [1.0, 1.0])

        key_a = next(k for k in (f"k{i}" for i in range(100)) if evalh.split_for(k) == "heldout")
        key_n = next(k for k in (f"n{i}" for i in range(100)) if evalh.split_for(k) == "heldout")
        mixed = [_case("x-1", "answerable", key_a, ["m"]), _case(key_n, "null", key_n)]
        result = evalh.score_arms(mixed, {"a": _pairs([["m"], []])}, ordered_arms=("a",))
        self.assertGreater(result["metrics"]["heldout"]["a"]["undefined_resamples"]["recall_at_5"], 0)

    # AC-3 -----------------------------------------------------------------
    def test_ac3_sequence_leakage_filter(self):
        _null_read_snapshot(self)  # storeless stub index
        copy_case = _case("a-1", "answerable", "r1", ["r1"], query=_R1_SUMMARY)
        honest = _case("a-2", "answerable", "r1", ["r1"],
                       query="setup reports the package installed but the new API import fails after upgrade")
        self.write_set([copy_case, honest])
        stub, calls = self.production_stub({})
        with patch.object(self.mh, "memory_search_response", stub):
            report = evalh.run_curated(self.root, index=_ArmIndex(self.root, ["r1"]))
        self.assertTrue(report["available"], report.get("unavailable_reason"))
        self.assertEqual(report["query_set"]["leakage_rejected"], 1)
        self.assertEqual(report["query_set"]["scored"], 1)
        self.assertEqual([c["query"] for c in calls], [honest["query"]])

    # AC-4 -----------------------------------------------------------------
    def test_ac4_freeze_binds_the_scored_set(self):
        _null_read_snapshot(self)  # storeless stub index
        cases = [_case("a-1", "answerable", "r1", ["r1"], query="restart after upgrade please"),
                 _case("a-2", "answerable", "r2", ["r2"], query="ledger writes are slow"),
                 _case("n-1", "null", "n-1")]
        lock = self.write_set(cases, high={"ledger writes are slow"})
        self.assertEqual(lock["cosine_rejected"], ["a-2"])
        self.assertEqual(lock["cosine_threshold"], 0.95)
        self.assertEqual(lock["sequence_ratio_threshold"], 0.9)
        self.assertEqual(lock["docs_model"], "stub-docs-model")
        stub, calls = self.production_stub({})
        with patch.object(self.mh, "memory_search_response", stub):
            report = evalh.run_curated(self.root, index=_ArmIndex(self.root, ["r1"]))
        self.assertTrue(report["available"], report.get("unavailable_reason"))
        self.assertEqual(report["query_set"]["cosine_rejected"], 1)
        self.assertNotIn("ledger writes are slow", [c["query"] for c in calls])

        path = self.root / evalh.QUERY_SET_PATH
        original = path.read_text(encoding="utf-8")
        path.write_bytes(original.replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual(evalh.load_query_set(self.root)["sha256"], lock["query_set_sha256"])
        path.write_text(original.replace("restart after upgrade please", "restart now"), encoding="utf-8")
        report = evalh.run_curated(self.root, index=_ArmIndex(self.root))
        self.assertFalse(report["available"])
        self.assertEqual(report["unavailable_reason"], "query_set_hash_mismatch")
        self.assertNotIn("metrics", report)

        lock_path = self.root / evalh.QUERY_SET_LOCK_PATH
        lock_path.unlink()
        path.write_text(original, encoding="utf-8")
        with patch.object(evalh, "_default_freeze_embedder", side_effect=RuntimeError("no model")):
            import io
            import contextlib
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = evalh.main(["--freeze-query-set", str(self.root)])
        self.assertEqual(code, 2)
        self.assertIn("freeze requires the docs embedding model", err.getvalue())
        self.assertFalse(lock_path.exists())

        broken = [dict(cases[0])]
        del broken[0]["grep_terms"]
        self.write_set(broken, freeze=False)
        report = evalh.run_curated(self.root, index=_ArmIndex(self.root))
        self.assertEqual(report["unavailable_reason"], "query_set_invalid")
        for case_type in ("null", "stale"):
            bad = [_case("c-1", case_type, "c-1" if case_type == "null" else "r2",
                         [] if case_type == "null" else ["r2"],
                         ["r9"] if case_type == "stale" else [])]
            del bad[0]["grep_terms"]
            self.assertEqual(evalh.validate_query_set({"cases": bad}), (None, "query_set_invalid"))

    # AC-5 -----------------------------------------------------------------
    def test_ac5_split_keeps_each_record_together(self):
        _null_read_snapshot(self)  # storeless stub index
        for key in ("q-001", "q-002", "n-005"):
            self.assertEqual(evalh.split_for(key), "heldout", key)
        self.assertEqual(evalh.split_for("r3"), "dev")
        self.assertEqual(evalh.split_for("n-001"), "dev")
        cases = [dict(_case("q-001", "answerable", "r3", ["r3"]), split="heldout"),
                 dict(_case("q-002", "answerable", "r3", ["r3"]), split="heldout"),
                 _case("n-001", "null", "n-001"), _case("n-005", "null", "n-005")]
        result = evalh.score_arms(cases, {"a": _pairs([["r3"], [], [], []])}, ordered_arms=("a",))
        self.assertEqual(result["split_counts"]["dev"]["answerable"], 2)
        self.assertEqual(result["split_counts"]["dev"]["null"], 1)
        self.assertEqual(result["split_counts"]["heldout"]["null"], 1)
        self.assertEqual(result["split_counts"]["heldout"]["answerable"], 0)
        self.assertEqual(set(result["metrics"]), {"heldout", "dev"})
        self.write_set([_case("a-1", "answerable", "r1", ["r1"], query="restart after upgrade")])
        stub, _calls = self.production_stub({})
        with patch.object(self.mh, "memory_search_response", stub):
            report = evalh.run_curated(self.root, index=_ArmIndex(self.root))
        self.assertEqual(set(report["metrics"]), {"heldout", "dev"})
        self.assertEqual(report["headline_split"], "heldout")

    # AC-6 -----------------------------------------------------------------
    def test_ac6_production_arm_runs_the_production_path_with_the_shared_index(self):
        _null_read_snapshot(self)  # storeless stub index
        cases = [_case(f"a-{i}", "answerable", "r1", ["r1"], query=f"upgrade restart problem number {i}")
                 for i in range(4)]
        self.write_set(cases)
        index = _ArmIndex(self.root, ["r1"])
        stub, calls = self.production_stub({c["query"]: ["r1"] for c in cases})
        with patch.object(self.mh, "memory_search_response", stub):
            report = evalh.run_curated(self.root, index=index)
        self.assertTrue(report["production_measured"])
        self.assertEqual(len(calls), 4)
        self.assertEqual([c["query"] for c in calls], [c["query"] for c in cases])
        for call in calls:
            self.assertIs(call["index"], index)
            self.assertEqual(call["limit"], self.mh.MEMORY_QUERY_CHECK_CAP)

        from declaration_support import RecordingFastMCP
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        sentinel = object()
        telemetry = MagicMock()
        telemetry.focus = SimpleNamespace(wave_id="", stage="general")
        telemetry.record_workflow.return_value = {}
        handler = SimpleNamespace(root=self.root, cache=None, telemetry=telemetry, index=sentinel)
        surface = RecordingFastMCP()
        self.srv.register_mcp_surface(surface, lambda: handler)
        seen = []
        engine = self.srv._load_script("memory_eval")
        with patch.object(engine, "run_curated",
                          side_effect=lambda root, **kw: seen.append(kw.get("index")) or {"available": False}):
            surface._tool_manager._tools["wf_memory_eval"].fn()
        self.assertEqual(len(seen), 1)
        self.assertIs(seen[0], sentinel)

        built = []

        class _Recorder(_ArmIndex):
            def __init__(self, root):
                built.append(root)
                super().__init__(root)
        with patch.object(self.srv, "WaveIndex", _Recorder), \
                patch.object(self.mh, "memory_search_response", stub):
            evalh.run_curated(self.root, index=None)
        self.assertEqual(built, [self.root])

    # AC-7 -----------------------------------------------------------------
    def test_ac7_fallen_back_production_arm_is_not_measured(self):
        _null_read_snapshot(self)  # storeless stub index
        cases = [_case(f"a-{i}", "answerable", "r1", ["r1"], query=f"upgrade restart problem number {i}")
                 for i in range(4)]
        self.write_set(cases)
        stub, _calls = self.production_stub(
            {}, fallback={cases[2]["query"]: "memory_vector_coverage_incomplete"})
        with patch.object(self.mh, "memory_search_response", stub):
            report = evalh.run_curated(self.root, index=_ArmIndex(self.root, ["r1"]))
        self.assertTrue(report["available"])
        for split in report["metrics"].values():
            self.assertNotIn("production", split)
        for order in report["arm_order"].values():
            self.assertNotIn("production", order)
        self.assertFalse(report["production_measured"])
        self.assertEqual(report["production_unavailable_reason"], "production_path_fell_back")
        self.assertEqual(report["production_retrieval"], {
            "model_screened_probes": 3, "fallback_probes": 1,
            "fallback_reasons": {"memory_vector_coverage_incomplete": 1}})

    # AC-8 -----------------------------------------------------------------
    def test_ac8_arms_share_production_corpus_and_dense_stream(self):
        _null_read_snapshot(self)  # storeless stub index
        query = "editing src ledgerlock py before a legacy write"
        self.write_set([_case("a-1", "answerable", "r2", ["r2"], query=query, terms=["ledgerlock"])])
        index = _ArmIndex(self.root, ["r2", "r1"])
        stub, _calls = self.production_stub({query: ["r2"]})
        with patch.object(self.mh, "memory_search_response", stub):
            report = evalh.run_curated(self.root, index=index)
        self.assertTrue(report["available"], report.get("unavailable_reason"))
        self.assertEqual(index.search_docs_calls, 0)
        arm_calls = [call for call in index.dense_calls if call[0] == query]
        self.assertEqual(len(arm_calls), 1)
        production_index = _ArmIndex(self.root, ["r2", "r1"])
        self.mh.memory_search_response(self.root, query=query, index=production_index, limit=5)
        production_calls = [call for call in production_index.dense_calls if call[0] == query]
        self.assertEqual(production_calls, arm_calls)

        mem = self.srv._memory_mod()
        corpus = (mem.load_memory_records(self.root, statuses=list(mem.DEFAULT_SURFACED_STATUSES))
                  + mem.load_archive_register_entries(self.root))
        self.assertIn("r9", [r["memory_id"] for r in corpus])
        texts = evalh._corpus_texts(self.root, corpus)
        self.assertEqual(evalh.grep_order(texts, ["ledgerlock"]), ["r9"])
        self.assertIn("r9", evalh.lexical_bm25_order(corpus, query)[:5])
        held = report["metrics"][evalh.split_for("r2")]
        self.assertEqual(held["full_context"]["mean_shown"], len(corpus))
        # The register entry r9 is the only item naming ledgerlock, so grep's
        # shown set holds it and its precision against relevant r2 is 0.
        self.assertEqual(held["grep"]["precision_shown"], 0.0)
        self.assertEqual(held["grep"]["mean_shown"], 1.0)

    def test_dense_arms_on_a_stale_index_are_not_measured(self):
        _null_read_snapshot(self)  # storeless stub index
        self.write_set([_case("a-1", "answerable", "r1", ["r1"], query="restart after upgrade")])
        stub, _calls = self.production_stub({})
        with patch.object(self.mh, "memory_search_response", stub):
            report = evalh.run_curated(self.root, index=_ArmIndex(self.root, source_current=False))
        self.assertFalse(report["dense_measured"])
        self.assertEqual(report["dense_unavailable_reason"], "memory_source_state_stale")
        for split in report["metrics"].values():
            self.assertNotIn("dense_only", split)
            self.assertNotIn("hybrid_no_rerank", split)

    def test_dense_ties_use_production_sort_order(self):
        class _Tied:
            def _memory_query_vector(self, query):
                return query

            def _memory_dense_scores(self, query, paths, *, expected_hashes):
                return {"scores": {"docs/agents/memory/zz.md": 0.5, "docs/agents/memory/aa.md": 0.5},
                        "complete": True, "source_current": True}
        body = {"docs/agents/memory/zz.md": "b-mem", "docs/agents/memory/aa.md": "c-mem"}
        stream, _ = evalh.dense_stream(_Tied(), "q", body, {})
        self.assertEqual(stream, ["b-mem", "c-mem"])

    # AC-9 -----------------------------------------------------------------
    def test_ac9_bounded_experimental_row_measures_relevance(self):
        import server_impl as srv
        records = [{"memory_id": "probe", "kind": "successful_pattern", "confidence": 0.6,
                    "status": "active", "summary": "zeta alpha zeta alpha zeta alpha",
                    "evidence": ["1abcd-bug probe"], "targets": ["src/probe.py"], "created": "2026-07-10"}]
        records += [{"memory_id": f"filler-{i}", "kind": "successful_pattern", "confidence": 0.3,
                     "status": "active", "summary": f"zeta alpha zeta filler words {i}",
                     "evidence": ["1abcd-bug filler"], "targets": [f"src/f{i}.py"], "created": "2026-07-10"}
                    for i in range(4)]
        records += [{"memory_id": f"decoy-{i}", "kind": "successful_pattern", "confidence": 0.95,
                     "status": "active",
                     "summary": f"zeta among many other unrelated decoy words padding text here {i}",
                     "evidence": ["1abcd-bug decoy"], "targets": [f"src/d{i}.py"], "created": "2026-07-10"}
                    for i in range(5)]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "docs" / "agents").mkdir(parents=True)
            mem = srv._memory_mod()
            evalh.build_corpus(root, records, mem)
            loaded = mem.load_memory_records(root, statuses=list(mem.DEFAULT_SURFACED_STATUSES))
            query = "zeta alpha"
            lexical = evalh.lexical_bm25_order(loaded, query)
            self.assertEqual(lexical[0], "probe")
            self.assertTrue(all(mid.startswith("filler") for mid in lexical[1:5]), lexical)
            self.assertTrue(all(mid.startswith("decoy") for mid in lexical[5:]), lexical)
            bounded = evalh._candidate_and_controls(
                srv, root, {"query": query}, semantic_order=[], records_override=loaded,
                commit_times={}, bounded=True)
            self.assertEqual(bounded["candidate"][0], "probe")
            self.assertEqual(bounded["lexical_only"][0], "probe")
            unbounded = evalh._candidate_and_controls(
                srv, root, {"query": query}, semantic_order=[], records_override=loaded,
                commit_times={})
            self.assertGreaterEqual(unbounded["lexical_only"].index("probe"), 4)
            self.assertGreaterEqual(unbounded["candidate"].index("probe"), 4)

    # AC-10 ----------------------------------------------------------------
    def test_ac10_index_signals_separate_stale_from_missing_and_need_no_model(self):
        import sqlite_vector_store as store

        def raising(*args, **kwargs):
            raise AssertionError("coverage must not embed")

        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "fixture.sqlite"
            paths = [f"docs/agents/memory/m{i}.md" for i in range(4)]
            hashes = {path: hashlib.sha256(path.encode()).hexdigest() for path in paths}

            def build(chunked, state):
                if database.exists():
                    database.unlink()
                conn = sqlite3.connect(database)
                conn.executescript(
                    "CREATE TABLE chunks_docs(id INTEGER PRIMARY KEY,path TEXT);"
                    "CREATE TABLE vectors_docs(chunk_id INTEGER PRIMARY KEY,embedding BLOB);"
                    "CREATE TABLE layer_path_state(layer TEXT,path TEXT,hash TEXT);")
                for i, path in enumerate(chunked):
                    conn.execute("INSERT INTO chunks_docs VALUES(?,?)", (i, path))
                    conn.execute("INSERT INTO vectors_docs VALUES(?,?)", (i, b"\0"))
                # A chunk with no vector never counts as covered.
                conn.execute("INSERT INTO chunks_docs VALUES(?,?)", (99, "docs/agents/memory/novec.md"))
                for path, digest in state.items():
                    conn.execute("INSERT INTO layer_path_state VALUES('docs',?,?)", (path, digest))
                conn.commit()
                conn.close()

            def readonly(_):
                return sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)

            with patch.object(store, "_open", side_effect=readonly), \
                    patch.object(store, "pack_vector", side_effect=raising):
                build(paths, hashes)
                self.assertEqual(store.memory_vector_coverage(Path(tmp), "docs", hashes), {
                    "requested_paths": 4, "covered_paths": 4, "stale_paths": 0, "missing_paths": 0})
                changed = dict(hashes, **{paths[0]: "0" * 64})
                self.assertEqual(store.memory_vector_coverage(Path(tmp), "docs", changed), {
                    "requested_paths": 4, "covered_paths": 3, "stale_paths": 1, "missing_paths": 0})
                build(paths[1:], hashes)
                self.assertEqual(store.memory_vector_coverage(Path(tmp), "docs", hashes), {
                    "requested_paths": 4, "covered_paths": 3, "stale_paths": 0, "missing_paths": 1})
                # Vector-backed chunks with no published state row are stale,
                # never covered; a code-layer row for the same path is ignored.
                build(paths, {path: digest for path, digest in hashes.items() if path != paths[0]})
                conn = sqlite3.connect(database)
                conn.execute("INSERT INTO layer_path_state VALUES('code',?,?)", (paths[0], hashes[paths[0]]))
                conn.commit()
                conn.close()
                self.assertEqual(store.memory_vector_coverage(Path(tmp), "docs", hashes), {
                    "requested_paths": 4, "covered_paths": 3, "stale_paths": 1, "missing_paths": 0})
                novec = {"docs/agents/memory/novec.md": "0" * 64}
                self.assertEqual(store.memory_vector_coverage(Path(tmp), "docs", novec)["missing_paths"], 1)

        import server_impl as srv
        shared = [{"memory_id": f"t-{i:02d}", "kind": "fragile_file", "confidence": 0.8,
                   "status": "active", "summary": f"shared target note {i}",
                   "evidence": ["1abcd-bug shared"], "targets": ["src/shared.py"], "created": "2026-07-10"}
                  for i in range(21)]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "docs" / "agents").mkdir(parents=True)
            mem = srv._memory_mod()
            evalh.build_corpus(root, shared, mem)
            loaded = mem.load_memory_records(root, statuses=list(mem.DEFAULT_SURFACED_STATUSES))
            self.assertEqual(evalh.target_retrievable(root, loaded, None, mem), {
                "records_with_file_targets": 21, "retrievable": 21, "crowded_past_search_cap": 1})

    # AC-11 ----------------------------------------------------------------
    def test_ac11_abstaining_arm_cannot_read_as_better_than_bm25(self):
        keys = [k for k in (f"h{i}" for i in range(200)) if evalh.split_for(k) == "heldout"][:10]
        cases = [_case(f"c-{i}", "answerable", key, [key]) for i, key in enumerate(keys)]
        production = [[keys[0]]] + [[] for _ in keys[1:]]
        bm25 = [[key, "x1", "x2", "x3", "x4"] if i < 6 else ["x1", "x2", "x3", "x4", "x5"]
                for i, key in enumerate(keys)]
        result = evalh.score_arms(cases, {"production": _pairs(production), "bm25_only": _pairs(bm25)})
        held = result["metrics"]["heldout"]
        self.assertEqual(held["production"]["recall_at_5"], 0.1)
        self.assertEqual(held["production"]["precision_shown"], 1.0)
        self.assertEqual(held["bm25_only"]["recall_at_5"], 0.6)
        self.assertEqual(held["bm25_only"]["precision_shown"], 0.12)
        order = result["arm_order"]["heldout"]
        self.assertLess(order.index("bm25_only"), order.index("production"))
        self.assertEqual(held["production"]["flags"], ["recall_below_bm25"])
        self.assertEqual(held["bm25_only"]["flags"], [])

        self.write_set([_case("a-1", "answerable", "r1", ["r1"], query="restart after upgrade")])
        stub, _calls = self.production_stub({})
        with patch.object(self.mh, "memory_search_response", stub):
            report = evalh.run_curated(self.root, index=_ArmIndex(self.root, ["r1"]))

        def keys_of(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    yield key
                    yield from keys_of(value)
            elif isinstance(node, list):
                for value in node:
                    yield from keys_of(value)
        for key in keys_of(report):
            self.assertNotIn("beats", key)
            self.assertNotIn("pause", key)
            if key != "adoption_gate":
                self.assertNotIn("gate", key)

    # AC-12 ----------------------------------------------------------------
    def test_ac12_labels_sanity_floor_and_privacy(self):
        _null_read_snapshot(self)  # storeless stub index
        cases = [_case("priv-case-a", "answerable", "r1", ["r1"], query="private query alpha restart"),
                 _case("priv-case-b", "null", "priv-case-b", query="private query beta unrelated")]
        self.write_set(cases)
        stub, _calls = self.production_stub({"private query alpha restart": ["r1"]})
        with patch.object(self.mh, "memory_search_response", stub):
            response = self.srv.wf_memory_eval_response(self.root, index=_ArmIndex(self.root, ["r1"]))
        data = response["data"]
        self.assertTrue(data["available"], data.get("unavailable_reason"))
        self.assertEqual({key: data[key] for key in (
            "production_variant", "experimental_variant", "baseline_variant",
            "headline_variant", "headline_split")}, {
            "production_variant": "memory_search_hybrid_rrf",
            "experimental_variant": "policy_ordered_rrf_shortlist5",
            "baseline_variant": "legacy_policy_ordering",
            "headline_variant": "production", "headline_split": "heldout"})
        self.assertEqual(data["sanity_floor"]["label"], "self_summary_sanity_floor")
        self.assertIs(data["sanity_floor"]["headline"], False)
        self.assertNotIn("memory_rrf_summary5", Path(evalh.__file__).read_text(encoding="utf-8"))
        self.assertNotIn("memory_rrf_summary5", json.dumps(response))
        forbidden = {"memory_id", "summary", "records", "target_refs", "body", "query", "case_id"}
        secrets = {c["query"] for c in cases} | {c["id"] for c in cases} | {
            r["summary"] for r in _FIXTURE_RECORDS}

        def walk(node, path="data"):
            if isinstance(node, dict):
                for key, value in node.items():
                    self.assertNotIn(key, forbidden, f"{key!r} leaked at {path}")
                    walk(value, f"{path}.{key}")
            elif isinstance(node, list):
                for i, value in enumerate(node):
                    walk(value, f"{path}[{i}]")
            elif isinstance(node, str):
                self.assertNotIn(node, secrets, f"value leaked at {path}")
        walk(data)

        leaky, _ = self.production_stub({}, raises=RuntimeError(_R1_SUMMARY))
        with patch.object(self.mh, "memory_search_response", leaky):
            response = self.srv.wf_memory_eval_response(self.root, index=_ArmIndex(self.root, ["r1"]))
        self.assertFalse(response["data"]["available"])
        self.assertEqual(response["data"]["unavailable_reason"],
                         "production query measurement unavailable")
        self.assertNotIn(_R1_SUMMARY, json.dumps(response))

    def test_absent_query_set_computes_only_the_sanity_floor(self):
        _null_read_snapshot(self)  # storeless stub index
        report = evalh.run_curated(self.root, index=_ArmIndex(self.root, ["r1"]))
        self.assertEqual(report["query_set"]["reason"], "query_set_absent")
        self.assertFalse(report["query_set"]["available"])
        self.assertNotIn("metrics", report)
        self.assertIn("sanity_floor", report)
        # Requirement 1: an absent set is not an unavailable report; the
        # sanity floor alone decides top-level availability.
        self.assertTrue(report["sanity_floor"]["available"])
        self.assertTrue(report["available"])
        self.assertNotIn("unavailable_reason", report)
        self.assertFalse(report["production_measured"])
        self.assertEqual(report["production_unavailable_reason"], "query_set_unavailable")

    # Delivery repair (wave 245na, cycle 2) ------------------------------
    def test_bootstrap_pools_cases_across_unequal_clusters(self):
        """Requirement 9.2: a resample pools every case of the drawn clusters."""
        # Cluster 0 holds 2 cases (both hit), cluster 1 holds 1 case (miss).
        clusters = [(2.0, 2), (0.0, 1)]
        boot = evalh._bootstrap(clusters, [[0, 1]] * 100)
        self.assertEqual(boot["interval"], [0.6667, 0.6667])  # 2 / 3, not 2 / 2
        boot = evalh._bootstrap(clusters, [[0, 0]] * 100)
        self.assertEqual(boot["interval"], [1.0, 1.0])  # 4 / 4, not 4 / 2
        key_a = next(k for k in (f"pa{i}" for i in range(200)) if evalh.split_for(k) == "heldout")
        key_b = next(k for k in (f"pb{i}" for i in range(200)) if evalh.split_for(k) == "heldout")
        cases = [_case("c-1", "answerable", key_a, ["m"]), _case("c-2", "answerable", key_a, ["m"]),
                 _case("c-3", "answerable", key_b, ["m"])]
        result = evalh.score_arms(cases, {"a": _pairs([["m"], ["m"], []])}, ordered_arms=("a",))
        row = result["metrics"]["heldout"]["a"]
        self.assertEqual(row["recall_at_5"], 0.6667)
        self.assertEqual(row["intervals"]["recall_at_5"], [0.0, 1.0])

    def test_curated_pass_wires_the_bounded_experimental_rows(self):
        _null_read_snapshot(self)  # storeless stub index
        self.write_set([_case("a-1", "answerable", "r1", ["r1"], query="restart after upgrade")])
        stub, _calls = self.production_stub({})
        real = evalh._candidate_and_controls
        seen = []

        def spy(*args, **kwargs):
            seen.append(kwargs.get("bounded", False))
            return real(*args, **kwargs)
        with patch.object(self.mh, "memory_search_response", stub), \
                patch.object(evalh, "_candidate_and_controls", side_effect=spy):
            report = evalh.run_curated(self.root, index=_ArmIndex(self.root, ["r1"]))
        self.assertTrue(report["sanity_floor"]["available"])
        self.assertTrue(seen)
        self.assertTrue(all(seen), seen)

    def test_dense_stream_reports_incomplete_coverage(self):
        _null_read_snapshot(self)  # storeless stub index
        index = _ArmIndex(self.root, ["r1"], complete=False)
        body, hashes = self.srv._memory_mod().memory_body_paths(self.root, [
            r for r in self.srv._memory_mod().load_memory_records(
                self.root, statuses=["active"])])
        self.assertEqual(evalh.dense_stream(index, "q", body, hashes),
                         (None, "memory_vector_coverage_incomplete"))
        self.write_set([_case("a-1", "answerable", "r1", ["r1"], query="restart after upgrade")])
        stub, _calls = self.production_stub({})
        with patch.object(self.mh, "memory_search_response", stub):
            report = evalh.run_curated(self.root, index=_ArmIndex(self.root, ["r1"], complete=False))
        self.assertFalse(report["dense_measured"])
        self.assertEqual(report["dense_unavailable_reason"], "memory_vector_coverage_incomplete")

    def test_dense_only_scores_follow_the_dense_stream(self):
        _null_read_snapshot(self)  # storeless stub index
        query = "restart after upgrade please"
        self.write_set([_case("a-1", "answerable", "r1", ["r1"], query=query)])
        stub, _calls = self.production_stub({})
        with patch.object(self.mh, "memory_search_response", stub):
            report = evalh.run_curated(self.root, index=_ArmIndex(self.root, ["r2", "r1"]))
        row = report["metrics"][evalh.split_for("r1")]["dense_only"]
        self.assertEqual(row["recall_at_5"], 1.0)
        self.assertEqual(row["mrr"], 0.5)
        self.assertEqual(row["mean_shown"], 2.0)
        self.assertEqual(row["precision_shown"], 0.5)

    def test_hybrid_caps_the_lexical_stream_like_production(self):
        _null_read_snapshot(self)  # storeless stub index
        import server_impl as srv
        records = [{"memory_id": f"lex-{i:02d}", "kind": "successful_pattern", "confidence": 0.8,
                    "status": "active", "summary": f"zeta zeta zeta note {i}",
                    "evidence": ["1abcd-bug lex"], "targets": [f"src/l{i}.py"], "created": "2026-07-10"}
                   for i in range(20)]
        records += [{"memory_id": f"sem-{i}", "kind": "successful_pattern", "confidence": 0.8,
                     "status": "active", "summary": f"unrelated semantic neighbour {i}",
                     "evidence": ["1abcd-bug sem"], "targets": [f"src/s{i}.py"], "created": "2026-07-10"}
                    for i in range(5)]
        records.append({"memory_id": "probe", "kind": "successful_pattern", "confidence": 0.8,
                        "status": "active",
                        "summary": "zeta appears once among many other longer padding words here today",
                        "evidence": ["1abcd-bug probe"], "targets": ["src/probe.py"], "created": "2026-07-10"})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "docs" / "evals").mkdir(parents=True)
            mem = srv._memory_mod()
            evalh.build_corpus(root, records, mem)
            loaded = mem.load_memory_records(root, statuses=list(mem.DEFAULT_SURFACED_STATUSES))
            lexical = evalh.lexical_bm25_order(loaded, "zeta")
            self.assertEqual(lexical.index("probe"), 20)
            (root / evalh.QUERY_SET_PATH).write_text(json.dumps({"cases": [
                _case("a-1", "answerable", "probe", ["probe"], query="zeta")]}), encoding="utf-8")
            evalh.freeze_query_set(root, embedder=_stub_freeze_embedder())
            stub, _calls = self.production_stub({})
            order = [f"sem-{i}" for i in range(5)] + ["probe"]
            with patch.object(self.mh, "memory_search_response", stub):
                report = evalh.run_curated(root, index=_ArmIndex(root, order))
        row = report["metrics"][evalh.split_for("probe")]["hybrid_no_rerank"]
        # Capped at MEMORY_SEARCH_CAP the probe's lexical rank 21 adds nothing,
        # so it stays at semantic rank 6, outside the top 5.
        self.assertEqual(row["recall_at_5"], 0.0)

    def test_embedded_text_preferred_rule(self):
        heldout = {"dense_only": {"recall_at_5": 0.5}, "dense_summary_only": {"recall_at_5": 0.5},
                   "dense_compact": {"recall_at_5": 0.4}}
        chars = {"dense_only": 900.0, "dense_summary_only": 120.0, "dense_compact": 300.0}
        self.assertEqual(evalh.embedded_text_preferred(heldout, chars), "dense_summary_only")
        heldout["dense_compact"]["recall_at_5"] = 0.6
        self.assertEqual(evalh.embedded_text_preferred(heldout, chars), "dense_compact")

    # AC-14 ----------------------------------------------------------------
    def test_ac14_hermetic_run_is_unchanged(self):
        """Sorted-JSON digest of run() on the golden fixture, captured from the
        scripts before wave 245na; the curated changes must not move it.
        Recaptured for change 246to, which changes the golden fixture's
        churn histories and cadence case (with its fast-record control) and stops
        churn attenuation."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "docs" / "agents").mkdir(parents=True)
            report = evalh.run(root)
        payload = {key: report[key] for key in (
            "overall", "comparison", "adoption_gate", "fixture_fingerprint", "cases")}
        digest = hashlib.sha256(
            (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")).hexdigest()
        self.assertEqual(
            digest, "63fca38440bf731333c30b770138cc78cf40c28302c2f5eeafb81b40417b807c")



# ---------------------------------------------------------------------------
# Change 246to (wave 249ar): maintenance signals, the uncoverable-record
# helper and versioned query sets.
# ---------------------------------------------------------------------------


class _NoModelIndex(_ArmIndex):
    """An index whose semantic layer cannot load (no model)."""

    def _ensure_loaded(self):
        raise RuntimeError("embedding model unavailable")


class MaintenanceSignalTests(unittest.TestCase):
    def setUp(self):
        import server_impl as srv
        self.srv = srv
        self.mem = srv._memory_mod()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        (self.root / "docs" / "agents").mkdir(parents=True)
        (self.root / "docs" / "evals").mkdir(parents=True)
        _null_read_snapshot(self)

    def _write(self, memory_id, target, *, status="active", lines=(), **fields):
        content = self.mem.render_memory_record(
            memory_id=memory_id, kind="failed_attempt", summary=f"Lesson about {memory_id} handling.",
            evidence=["1abcd"], targets=[target], title=f"Lesson {memory_id}",
            confidence=0.8, status=status, date="2026-11-01", **fields)
        if lines:
            content = content.replace("Updated: 2026-11-01\n",
                                      "Updated: 2026-11-01\n" + "".join(f"{l}\n" for l in lines))
        return self.mem.write_memory_record(self.root, content, memory_id)

    def _file(self, rel):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value = 1\n", encoding="utf-8")

    def _freeze(self, cases, version=1):
        set_rel, _lock = evalh.query_set_paths(version)
        (self.root / set_rel).write_text(
            json.dumps({"schema_version": 1, "cases": cases}, indent=2), encoding="utf-8")
        return evalh.freeze_query_set(self.root, embedder=_stub_freeze_embedder(), version=version)

    def _seed(self, histories):
        index_store = self.srv._load_script("index_state_store")
        store = index_store.IndexStateStore(self.root / ".wavefoundry" / "index")
        try:
            store.apply_freshness(
                rows={p: {"commit_count": len(ts), "source": "test"} for p, ts in histories.items()},
                commits=[(p, f"{i:040x}", ts) for p, times in histories.items()
                         for i, ts in enumerate(times)],
                fingerprint="test", paths_hash="test")
        finally:
            store.close()

    # AC-8 ---------------------------------------------------------------
    def test_ac8_signals_are_counts_only_and_need_no_model(self):
        for rel in ("pkg/b.py", "c.py", "d.py"):
            self._file(rel)
        self._write("m-unres", "gone.py")
        self._write("m-bare", "b.py")
        self._write("m-churn", "c.py")
        self._write("m-clean", "d.py", lines=("Checked at: 2026-11-01T10:00:00Z",
                                              "Check note: checked d.py", "Check flags: none"))
        for memory_id in ("m-old-a", "m-old-b"):
            self._write(memory_id, "d.py", status="stale", lines=(
                "Checked at: 2026-11-02T10:00:00Z", "Check note: churned",
                "Check flags: target_churn"))
            self.mem.archive_memory_record(self.root, memory_id, reason="retired after a check")
        start = 1793534400  # 2026-11-02T12:00:00Z
        self._seed({"c.py": [start + i * 7 * 86400 for i in range(12)]})
        cases = [_case(f"a-{i}", "answerable", source, [source],
                       query=f"distinct situation wording number {i} for {source}")
                 for i, source in enumerate(("m-unres", "m-unres", "m-bare", "m-bare", "m-churn"))]
        self._freeze(cases + [_case("n-1", "null", "n-1")])
        expected = {
            "active_records": 4, "unresolved_target_records": 1,
            "unresolved_target_fraction": 0.25, "not_canonical_target_records": 1,
            "churn_flagged_records": 1, "coverage_gap_records": 2,
            "uncoverable_records": 4,
            "check_outcomes": {"flagged": {"active": 0, "retired": 2},
                               "unflagged": {"active": 1, "retired": 0}},
        }
        signals = evalh.maintenance_signals(self.root, evalh.load_query_set(self.root))
        self.assertEqual(signals, expected)
        report = evalh.run_curated(self.root, index=_NoModelIndex(self.root))
        self.assertFalse(report["available"])
        self.assertEqual(report["maintenance_signals"], expected)
        envelope = self.srv.wf_memory_eval_response(self.root, index=_NoModelIndex(self.root))
        self.assertEqual(envelope["data"]["maintenance_signals"], expected)
        blob = json.dumps(envelope)
        for memory_id in ("m-unres", "m-bare", "m-churn", "m-clean", "m-old-a", "m-old-b"):
            self.assertNotIn(memory_id, blob)
        for rel in evalh.query_set_paths(1):
            (self.root / rel).unlink()
        self.assertIsNone(evalh.maintenance_signals(
            self.root, evalh.load_query_set(self.root))["coverage_gap_records"])

    # AC-14 --------------------------------------------------------------
    def test_ac14_uncoverable_records_are_reproducible_and_kept_out(self):
        rationale = {"validation_rationale": "The lesson applies when editing the loader."}
        delta = {"action_delta": "Run the loader test before editing."}
        for memory_id, fields in (("u1", rationale), ("u2", {}), ("u3", {}),
                                  ("u4", delta), ("u5", rationale)):
            self._file(f"src/{memory_id}.py")
            self._write(memory_id, f"src/{memory_id}.py", **fields)
        counts = {"u1": 1, "u2": 3, "u3": 0, "u4": 2, "u5": 2}
        cases = [_case(f"a-{source}-{i}", "answerable", source, [source],
                       query=f"case {i} wording that describes the {source} situation")
                 for source, count in counts.items() for i in range(count)]
        self._freeze(cases)
        state = evalh.load_query_set(self.root)
        expected = [{"memory_id": "u1", "reasons": ["coverage_gap"]},
                    {"memory_id": "u2", "reasons": ["no_rationale"]},
                    {"memory_id": "u3", "reasons": ["coverage_gap", "no_rationale"]}]
        # Known bad: a coverage-gap-only rule returns u1 and u3 and misses u2.
        self.assertEqual(evalh.uncoverable_records(self.root, state), expected)
        self.assertEqual(evalh.uncoverable_records(self.root, state), expected)
        import io
        import contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = evalh.main(["--uncoverable-records", str(self.root)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue()), expected)
        self.assertEqual(evalh.maintenance_signals(self.root, state)["uncoverable_records"], 3)
        envelope = self.srv.wf_memory_eval_response(self.root, index=_NoModelIndex(self.root))
        self.assertEqual(envelope["data"]["maintenance_signals"]["uncoverable_records"], 3)
        blob = json.dumps(envelope)
        for memory_id in counts:
            self.assertNotIn(f'"{memory_id}"', blob)
        self.assertEqual(evalh.uncoverable_records(self.root, None),
                         [{"memory_id": "u2", "reasons": ["no_rationale"]},
                          {"memory_id": "u3", "reasons": ["no_rationale"]}])


class GoldenCadenceInvariantTests(unittest.TestCase):
    """Delivery fix (qa 1): the cadence case also requires the fast record unflagged."""

    def test_fast_record_must_stay_unflagged(self):
        case = next(c for c in evalh.load_fixture()["cases"] if c["category"] == "adaptive_cadence")
        self.assertEqual(case.get("invariant_falsy_id"), "mem-cadence-fast")
        good = {"data": {"records": [
            {"memory_id": "mem-cadence-fast", "needs_reverification": False},
            {"memory_id": "mem-cadence-slow", "needs_reverification": True}]}}
        self.assertTrue(evalh._invariant_pass(case, good))
        # Known bad: a fixed halving of 5 flags both records.
        both = {"data": {"records": [
            {"memory_id": "mem-cadence-fast", "needs_reverification": True},
            {"memory_id": "mem-cadence-slow", "needs_reverification": True}]}}
        self.assertFalse(evalh._invariant_pass(case, both))
        missing = {"data": {"records": [
            {"memory_id": "mem-cadence-slow", "needs_reverification": True}]}}
        self.assertFalse(evalh._invariant_pass(case, missing))


class VersionedQuerySetTests(unittest.TestCase):
    """AC-9: a versioned freeze leaves the version 1 baseline intact."""

    setUp = SituationQueryEvalTests.setUp
    production_stub = SituationQueryEvalTests.production_stub

    def _v1(self):
        cases = [_case("a-0001", "answerable", "r1", ["r1"], query="restart after upgrade please"),
                 _case("a-0002", "answerable", "r2", ["r2"], query="ledger writes look slow today"),
                 _case("n-0001", "null", "n-0001")]
        (self.root / evalh.QUERY_SET_PATH).write_text(
            json.dumps({"schema_version": 1, "cases": cases}, indent=2), encoding="utf-8")
        evalh.freeze_query_set(self.root, embedder=_stub_freeze_embedder())
        v2 = [cases[0], cases[2],
              _case("a-9001", "answerable", "r3", ["r3"], query="nested braces broke the spans")]
        set_rel, _ = evalh.query_set_paths(2)
        (self.root / set_rel).write_text(
            json.dumps({"schema_version": 1, "cases": v2}, indent=2), encoding="utf-8")

    def _freeze_cli(self, version):
        import io
        import contextlib
        err = io.StringIO()
        with patch.object(evalh, "_default_freeze_embedder",
                          return_value=_stub_freeze_embedder()), contextlib.redirect_stderr(err), \
                contextlib.redirect_stdout(io.StringIO()):
            code = evalh.main(["--freeze-query-set", str(self.root),
                               "--query-set-version", str(version)])
        return code, err.getvalue()

    def _run(self, **kwargs):
        stub, _calls = self.production_stub({})
        with patch.object(self.mh, "memory_search_response", stub):
            return evalh.run_curated(self.root, index=_ArmIndex(self.root, ["r1"]), **kwargs)

    def test_ac9_versioned_freeze_and_selection(self):
        _null_read_snapshot(self)
        self.assertEqual(evalh.query_set_paths(2), (
            Path("docs/evals/memory-query-set.v2.json"),
            Path("docs/evals/memory-query-set.v2.lock.json")))
        self._v1()
        v1_bytes = {rel: (self.root / rel).read_bytes() for rel in evalh.query_set_paths(1)}
        code, _err = self._freeze_cli(2)
        self.assertEqual(code, 0)
        v1_lock = json.loads(v1_bytes[evalh.QUERY_SET_LOCK_PATH])
        lock = json.loads((self.root / evalh.query_set_paths(2)[1]).read_text(encoding="utf-8"))
        self.assertEqual({key: lock[key] for key in (
            "version", "parent_version", "parent_query_set_sha256",
            "added_case_ids", "removed_case_ids")}, {
            "version": 2, "parent_version": 1,
            "parent_query_set_sha256": v1_lock["query_set_sha256"],
            "added_case_ids": ["a-9001"], "removed_case_ids": ["a-0002"]})
        self.assertEqual({rel: (self.root / rel).read_bytes() for rel in v1_bytes}, v1_bytes)

        default = self._run()
        self.assertTrue(default["available"], default.get("unavailable_reason"))
        self.assertEqual(default["query_set"]["version"], 2)
        self.assertEqual(default["query_set"]["sha256"], lock["query_set_sha256"])
        pinned = self._run(query_set_version=1)
        self.assertEqual(pinned["query_set"]["version"], 1)
        self.assertEqual(pinned["query_set"]["sha256"], v1_lock["query_set_sha256"])

        (self.root / evalh.query_set_paths(2)[1]).unlink()
        v1_path = self.root / evalh.QUERY_SET_PATH
        v1_path.write_text(v1_path.read_text(encoding="utf-8").replace(
            "restart after upgrade please", "restart after the upgrade"), encoding="utf-8")
        code, err = self._freeze_cli(2)
        self.assertEqual(code, 2)
        self.assertIn("parent query set does not match its lock", err)
        self.assertFalse((self.root / evalh.query_set_paths(2)[1]).exists())

    def test_ac9_no_versioned_file_is_unchanged(self):
        _null_read_snapshot(self)
        self._v1()
        (self.root / evalh.query_set_paths(2)[0]).unlink()
        report = self._run()
        self.assertTrue(report["available"], report.get("unavailable_reason"))
        self.assertEqual(report["query_set"]["version"], 1)
        self.assertIn("metrics", report)
        self.assertNotIn("version", json.loads(
            (self.root / evalh.QUERY_SET_LOCK_PATH).read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()

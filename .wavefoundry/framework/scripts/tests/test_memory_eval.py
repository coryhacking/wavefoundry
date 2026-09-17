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
                self._docs_vector_layer = "docs"

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
                    self._docs_vector_layer = "docs"
                def _ensure_loaded(self):
                    pass
                def search_docs(self, *args, **kwargs):
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


if __name__ == "__main__":
    unittest.main()

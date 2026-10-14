"""Real Wavefoundry entry points with isolated, qualified service fixtures."""
from __future__ import annotations
import asyncio
import contextlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
import tensorwell_client as tc
import test_tensorwell_client as fixtures
import server_tools_support as support

_REGISTERED_RELOAD_DRIVER = r"""
import asyncio, json, os, sys, threading
from pathlib import Path
scripts, root = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(scripts))
import server
import tensorwell_client as tc
started, release = threading.Event(), threading.Event()
calls = []
def pending(root):
    calls.append(str(root))
    started.set()
    release.wait(5)
tc._startup = pending
tc._policy_reason = lambda: None
mcp = server.build_server(root)
async def run():
    async with mcp._mcp_server.lifespan(mcp._mcp_server):
        assert await asyncio.to_thread(started.wait, 2)
        worker, lock, probe, status = tc._startup_worker, tc._lock, tc._probe_lock, tc._status
        generation = tc._generation
        tc._pair, tc._cache_until, tc._backoff_until = object(), 1e20, 1e20
        source_path = scripts / 'tensorwell_client.py'
        source = source_path.read_text()
        old_pin = tc.EMBEDDING_IDENTITY
        new_pin = 'sha256:' + '9' * 64
        source = source.replace('EMBEDDING_IDENTITY = "' + old_pin + '"',
                                'EMBEDDING_IDENTITY = "' + new_pin + '"', 1)
        source_path.write_text(source + '\nRELOAD_PROBE = "fresh source"\n')
        content, result = await mcp.call_tool('wf_reload_mcp', {})
        if result is None:
            result = json.loads(next(item.text for item in content if item.type == 'text'))
        assert result['status'] == 'ok', result
        assert tc.RELOAD_PROBE == 'fresh source'
        assert tc.EMBEDDING_IDENTITY == new_pin
        assert tc._generation == generation + 1
        assert tc._pair is None and tc._cache_until == 0 and tc._backoff_until == 0
        assert tc._lock is lock and tc._probe_lock is probe and tc._status is status
        assert tc._startup_scheduled and tc._startup_worker is worker and worker.is_alive()
        # A mutant resetting the once flag must remain a synthetic worker,
        # never an attempt to run the real service after code is refreshed.
        tc._startup = pending
        tc._policy_reason = lambda: None
        tc.start_background(root)
        assert tc._startup_worker is worker and len(calls) == 1
        release.set()
        worker.join(2)
        assert not worker.is_alive()
        assert 'wf_server_info' in [tool.name for tool in await mcp.list_tools()]
try:
    asyncio.run(run())
finally:
    release.set()
print(json.dumps({'registered_reload': 'ok', 'fresh_source_and_pin': True,
                  'retained_worker_and_locks': True, 'starts': len(calls)}))
"""


class MemoryQualityOracleTests(unittest.TestCase):
    def test_quality_gate_rejects_losses_false_matches_precision_loss_and_unjudged_returns(self):
        from oracle.tensorwell_memory_parity import evaluate_quality
        # Small synthetic labels exercise the oracle independently of any
        # checkout's historical wave corpus or native model availability.
        cases = [
            {"id": "answer", "candidate_ids": ["direct", "adjacent", "unknown"],
             "relevant_ids": ["direct"], "labels": {"direct": "direct_support", "adjacent": "adjacent_context"},
             "historical_scores": [-3., -5., -6.]},
            {"id": "negative", "candidate_ids": ["irrelevant"], "relevant_ids": [],
             "labels": {"irrelevant": "irrelevant"}, "historical_scores": [-8.]},
        ]
        baseline = {c["id"]: c["historical_scores"] for c in cases}
        self.assertTrue(evaluate_quality(cases, baseline, baseline)["pass"])
        for answer, negative, failed_field in (
            ([-5., -5., -6.], [-8.], "useful_support_losses"),
            ([-3., -5., -6.], [-4.], "negative_case_returns"),
            ([-3., -4., -6.], [-8.], "non_regression"),
            ([-3., -5., -4.], [-8.], "unjudged_returns"),
        ):
            with self.subTest(failure=failed_field):
                result = evaluate_quality(cases, baseline, {"answer": answer, "negative": negative})
                self.assertFalse(result["pass"])
                if failed_field == "non_regression":
                    self.assertFalse(result[failed_field]["direct_support_precision"])
                else:
                    self.assertTrue(result[failed_field])
        for malformed in ([True, -5., -6.], [float("nan"), -5., -6.], [], ["-3", -5., -6.]):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                evaluate_quality(cases, baseline, {"answer": malformed, "negative": [-8.]})


@unittest.skipIf(os.name == "nt", "Private POSIX service fixtures; native Windows service use remains unsupported")
class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ClientTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.enterContext(patch.dict(os.environ, {"ORT_DISABLE_TELEMETRY": "1", "HF_HUB_OFFLINE": "1"}))
        import accel_embedder
        for name in ("StaticShapeEmbedder", "StaticShapeReranker"):
            self.enterContext(patch.object(accel_embedder, name,
                              side_effect=AssertionError("native model forbidden in service fixture")))
        import indexer
        self.indexer = indexer
        self.srv = support.load_server()
        self.fixture.fake_ready()

    def bare_index(self, versions=None):
        obj = self.srv.WaveIndex.__new__(self.srv.WaveIndex)
        obj._meta = {"project": {"model_versions": versions or {"docs": "model@full", "code": "model@full"}}}
        obj._embedders = {}
        obj._reranker = None
        obj._reranker_lock = threading.Lock()
        obj.root = self.fixture.home
        obj._indexer_module = lambda: self.indexer
        obj._indexer_constant = lambda key: getattr(self.indexer, key)
        return obj

    def memory_index(self, count=7):
        from test_memory_records import _MemoryCase
        memory = _MemoryCase()
        memory.setUp()
        self.addCleanup(memory.doCleanups)
        paths = [memory._add(f"mem-{i}", "review_finding") for i in range(count)]
        obj = self.bare_index()
        obj.root = memory.root
        obj._ensure_loaded = lambda: None
        obj._docs_vector_layer = "docs"
        # Only vector storage is synthetic: real eligibility, RRF, getter,
        # adapter, score validation and public response consume these candidates.
        scores = {path.relative_to(memory.root).as_posix(): 1 - i / 100
                  for i, path in enumerate(paths)}
        obj._memory_candidate_scores = lambda *args, **kwargs: {"complete": True, "scores": scores}
        return obj

    def test_all_query_models_use_service_without_local_construction(self):
        import accel_embedder
        obj = self.memory_index()
        obj._memory_reranker_failed_model = self.indexer.RERANKER_MODEL
        obj._memory_reranker = SimpleNamespace(provider="CPUExecutionProvider",
                                               model_name=self.indexer.RERANKER_MODEL)
        obj._reranker_disabled = True
        with contextlib.ExitStack() as stack:
            constructors = [stack.enter_context(patch.object(accel_embedder, name,
                            side_effect=AssertionError("local model construction")))
                            for name in ("StaticShapeEmbedder", "StaticShapeReranker",
                                         "make_embedder", "make_reranker")]
            constructors.append(stack.enter_context(patch.object(
                self.indexer, "_text_embedding_cached_first",
                side_effect=AssertionError("local embedding construction"))))
            self.assertEqual(obj._embed_query("raw query", self.indexer.DOCS_MODEL).shape, (384,))
            self.assertEqual(obj._get_reranker().rerank("raw", ["a", "b"]), [-2.5, -1.5])
            response = self.srv.memory_search_response(obj.root, query="semantic-only", index=obj, limit=20)
            self.assertEqual(response["data"]["retrieval"]["qualification"], "model_relevance")
            self.assertEqual([r["memory_id"] for r in response["data"]["records"]],
                             [f"mem-{i}" for i in range(5)])
            self.assertEqual(self.fixture.requests[-1][1]["documents"],
                             [f"Lesson from mem-{i}." for i in range(5)])
            for constructor in constructors:
                constructor.assert_not_called()

    def test_memory_service_scores_preserve_cutoff_order_cap_and_no_refill(self):
        obj = self.memory_index()
        def scores(path, body):
            if path == "/v1/rerank":
                return {"instance_id": fixtures.INSTANCE, "model": fixtures.descriptor("reranking"),
                        "data": [{"index": i, "score": score} for i, score in enumerate(
                            [-4.0, -4.0001, -3.9999, -10.0, -5.0])]}
        self.fixture.reply = scores
        response = self.srv.memory_search_response(obj.root, query="semantic-only", index=obj, limit=20)
        self.assertEqual([r["memory_id"] for r in response["data"]["records"]], ["mem-0", "mem-2"])
        self.assertEqual(response["data"]["retrieval"]["checked_candidates"], 5)
        self.assertFalse(response["data"]["retrieval"]["support_verified"])
        self.assertEqual(self.fixture.requests[-1][1]["documents"],
                         [f"Lesson from mem-{i}." for i in range(5)])

    def test_memory_service_late_failure_discards_partial_scores_without_local_retry(self):
        import accel_embedder
        obj = self.memory_index()
        requests = []
        def late_failure(path, body):
            if path == "/v1/rerank":
                requests.append(body)
                if len(requests) == 2:
                    return {"instance_id": fixtures.INSTANCE, "model": fixtures.descriptor("reranking"),
                            "data": []}
        self.fixture.reply = late_failure
        with patch.object(tc, "MAX_ITEMS", 1), patch.object(accel_embedder, "StaticShapeReranker",
                side_effect=AssertionError("local retry")) as local:
            response = self.srv.memory_search_response(obj.root, query="semantic-only", index=obj)
        self.assertEqual(len(requests), 2)
        self.assertEqual(response["data"]["records"], [])
        self.assertEqual(response["data"]["retrieval"]["qualification"], "unavailable")
        self.assertEqual(response["data"]["retrieval"]["method"], "lexical_policy")
        self.assertEqual(response["data"]["retrieval"]["checked_candidates"], 0)
        self.assertIn("memory_query_fallback", [d["code"] for d in response["diagnostics"]])
        local.assert_not_called()

    def test_memory_disable_and_unavailable_service_preserve_cpu_cache(self):
        import accel_embedder
        obj = self.bare_index()
        for value in ("1", "true", "YES", " on "):
            with self.subTest(disable=value), patch.dict(os.environ, {"WAVEFOUNDRY_DISABLE_RERANKER": value}), \
                 patch.object(tc, "select_reranker") as select, \
                 patch.object(accel_embedder, "StaticShapeReranker") as local:
                self.assertIsNone(obj._get_memory_reranker())
                select.assert_not_called()
                local.assert_not_called()
        cpu = SimpleNamespace(provider="CPUExecutionProvider", model_name=self.indexer.RERANKER_MODEL)
        for policy in ({"WAVEFOUNDRY_DISABLE_TENSORWELL": "1"}, {"WAVEFOUNDRY_EMBED_PROVIDER": "cpu"}):
            with self.subTest(policy=policy), patch.dict(os.environ, policy), \
                 patch.object(tc, "_discovery") as discovery, \
                 patch.object(accel_embedder, "StaticShapeReranker", return_value=cpu) as local:
                obj = self.bare_index()
                self.assertIs(obj._get_memory_reranker(), cpu)
                self.assertIs(obj._get_memory_reranker(), cpu)
                local.assert_called_once_with(self.indexer.RERANKER_MODEL, ["CPUExecutionProvider"])
                discovery.assert_not_called()
        for unavailable in ("absent", "incompatible"):
            with self.subTest(unavailable=unavailable):
                obj = self.bare_index()
                tc._pair, tc._cache_until, tc._backoff_until = None, 0, 0
                if unavailable == "absent":
                    (self.fixture.state / "endpoint.json").unlink()
                else:
                    self.fixture.endpoint()
                    self.fixture.models = []
                with patch.object(accel_embedder, "StaticShapeReranker", return_value=cpu) as local:
                    self.assertIs(obj._get_memory_reranker(), cpu)
                    self.assertIs(obj._get_memory_reranker(), cpu)
                    local.assert_called_once()

    def test_small_build_resident_before_local_provider_or_cache(self):
        with patch.object(self.indexer, "_predicted_precision_class", return_value="full"), \
             patch.object(self.indexer, "_onnx_providers", side_effect=AssertionError("local provider selection")), \
             patch.object(self.indexer, "_EMBEDDER_CACHE", {self.indexer.DOCS_MODEL: object()}):
            embedder = self.indexer._get_embedder(self.indexer.DOCS_MODEL, n_chunks=1)
            vectors = self.indexer._embed_texts(embedder, ["small raw document"])
        self.assertEqual(vectors.shape, (1, 384))
        request = self.fixture.requests[-1][1]
        self.assertEqual(request["role"], "document")
        self.assertEqual(request["input"], ["small raw document"])

    def test_registered_query_raw_prefix_precision_and_rerank(self):
        obj = self.bare_index()
        obj._embedders[self.indexer.DOCS_MODEL] = object()
        obj._reranker_disabled = True  # a prior local failure does not hide ready service
        prefix = self.indexer.query_embedding_prefix(self.indexer.DOCS_MODEL)
        text = prefix + "this prefix is user input"
        vector = obj._embed_query(text, self.indexer.DOCS_MODEL)
        self.assertEqual(vector.shape, (384,))
        self.assertEqual(self.fixture.requests[-1][1]["input"], [text])
        self.assertEqual(self.fixture.requests[-1][1]["role"], "query")
        self.assertEqual(obj._get_reranker().rerank("raw", ["a", "b"]), [-2.5, -1.5])
        with patch.dict(os.environ, {"WAVEFOUNDRY_DISABLE_RERANKER": "1"}):
            self.assertIsNone(obj._get_reranker())
        for versions in ({"docs": "model@int8", "code": "model@int8"},
                         {"docs": "model@int8", "code": "model@full"}):
            obj = self.bare_index(versions)
            sentinel = object()
            obj._embedders[self.indexer.DOCS_MODEL] = sentinel
            with patch.object(tc, "select_embedder", wraps=tc.select_embedder) as select:
                self.assertIs(obj._get_embedder(self.indexer.DOCS_MODEL), sentinel)
                if len(set(versions.values())) > 1: select.assert_not_called()
                else: self.assertEqual(select.call_args.args[1], "int8")

    def test_selected_query_failure_explicit_no_local_retry(self):
        obj = self.bare_index()
        local = object()
        obj._embedders[self.indexer.DOCS_MODEL] = local
        adapter = tc.select_embedder(self.indexer.DOCS_MODEL)
        with patch.object(obj, "_get_embedder", return_value=adapter), \
             patch.object(tc, "_http", side_effect=RuntimeError("raw hidden error")):
            with self.assertRaises(self.srv.SemanticModelUnavailableOfflineError) as caught:
                obj._embed_query("private input", self.indexer.DOCS_MODEL)
        self.assertNotIn("private input", str(caught.exception))
        self.assertNotIn("raw hidden", str(caught.exception))
        self.assertIs(obj._embedders[self.indexer.DOCS_MODEL], local)

    def test_float32_representability_in_actual_query_build_and_rerank(self):
        import numpy as np
        for value in (1.0, tc.FLOAT32_MAX, -tc.FLOAT32_MAX, 1e100, -1e100):
            with self.subTest(value=value):
                tc._pair, tc._cache_until, tc._backoff_until = None, 0, 0
                self.fixture.reply = None
                embedder = tc.select_embedder(self.indexer.DOCS_MODEL)
                reranker = tc.select_reranker(self.indexer.RERANKER_MODEL)
                def response(path, body):
                    embedding = path == "/v1/embeddings"
                    return {"instance_id": fixtures.INSTANCE,
                            "model": fixtures.descriptor("embedding" if embedding else "reranking"),
                            "data": [{"index": 0, "embedding": [value] + [0.] * 383} if embedding
                                     else {"index": 0, "score": value}]}
                self.fixture.reply = response
                obj = self.bare_index()
                with patch.object(obj, "_get_embedder", return_value=embedder):
                    if abs(value) > tc.FLOAT32_MAX:
                        with self.assertRaises(self.srv.SemanticModelUnavailableOfflineError):
                            obj._embed_query("raw", self.indexer.DOCS_MODEL)
                        with self.assertRaises(tc.TensorwellUnavailable):
                            self.indexer._embed_texts(embedder, ["raw"])
                        with self.assertRaises(tc.TensorwellUnavailable): reranker.rerank("q", ["raw"])
                    else:
                        self.assertTrue(np.isfinite(obj._embed_query("raw", self.indexer.DOCS_MODEL)).all())
                        self.assertTrue(np.isfinite(self.indexer._embed_texts(embedder, ["raw"])).all())
                        self.assertTrue(np.isfinite(np.asarray(reranker.rerank("q", ["raw"]), dtype=np.float32)).all())

    def test_setup_and_optional_downloads_avoid_native_construction(self):
        import setup_index
        import accel_embedder
        with patch.object(accel_embedder, "make_embedder", side_effect=AssertionError("local embedding")), \
             patch.object(accel_embedder, "make_reranker", side_effect=AssertionError("local reranking")), \
             patch.object(setup_index.provider_policy, "select_embedding_providers", side_effect=AssertionError("probe")):
            self.assertEqual(setup_index._prewarm_gpu_accel([self.indexer.DOCS_MODEL]), [])
        obj = self.bare_index()
        obj._model_downloads_started = False
        with patch.dict(os.environ, {"HF_HUB_OFFLINE": "0"}), \
             patch.object(self.srv, "_ensure_model_cached", side_effect=AssertionError("optional download")) as ensure, \
             patch("threading.Thread") as worker:
            worker.side_effect = lambda **kwargs: type("Worker", (), {"start": lambda self: kwargs["target"]()})()
            obj._start_background_model_downloads()
            ensure.assert_not_called()

    def test_failed_incremental_build_preserves_published_vectors_and_file_meta(self):
        import test_indexer as ix_tests
        import index_state_store
        import sqlite_vector_store
        root = self.fixture.home / "repo"
        root.mkdir()
        ix_tests._make_repo(root, {"docs/guide.md": "# Guide\n\nOriginal synthetic text.\n"})
        with patch.object(self.indexer, "_get_embedder", return_value=ix_tests._make_embedder_mock()), \
             patch.object(self.indexer, "_predicted_precision_class", return_value="full"):
            initial = self.indexer.build_index(root, full=True, content="docs", verbose=False)
        self.assertFalse(initial.get("failed"), initial)
        index_dir = root / self.indexer.INDEX_DIR_NAME
        before_rows = sqlite_vector_store.payload_rows(index_dir, "docs")
        before_meta = index_state_store.export_meta_snapshot(index_dir)
        import sqlite_runtime
        def vector_bytes():
            with sqlite_runtime.connect(index_dir / "index.sqlite", read_only=True) as connection:
                return list(connection.execute("SELECT chunk_id,embedding FROM vectors_docs ORDER BY chunk_id"))
        before_vectors = vector_bytes()
        self.assertTrue(before_vectors)
        (root / "docs/guide.md").write_text("# Guide\n\n" + "".join(
            f"## Synthetic section {i}\n\nChanged content {i} café 🌊 " + (f"words {i} " * 60) + "\n\n"
            for i in range(6)))
        requests = []
        def late_failure(path, body):
            if path == "/v1/embeddings":
                requests.append(body)
                if len(requests) == 2:
                    return {"instance_id": fixtures.INSTANCE, "model": fixtures.descriptor("embedding"), "data": []}
        self.fixture.reply = late_failure
        with patch.object(tc, "MAX_ITEMS", 1), \
             patch.object(self.indexer, "_predicted_precision_class", return_value="full"), \
             patch.object(self.indexer, "_onnx_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.indexer, "_text_embedding_cached_first", side_effect=AssertionError("local retry")), \
             patch.object(self.indexer.accel_embedder, "make_embedder", side_effect=AssertionError("native retry")):
            try:
                result = self.indexer.build_index(root, content="docs", verbose=False)
            except tc.TensorwellUnavailable:
                result = {"failed": True}
        self.assertTrue(result.get("failed"), result)
        self.assertEqual(len(requests), 2)
        self.assertEqual(len(requests[0]["input"]), 1)
        self.assertEqual(sqlite_vector_store.payload_rows(index_dir, "docs"), before_rows)
        self.assertEqual(vector_bytes(), before_vectors)
        after_meta = index_state_store.export_meta_snapshot(index_dir)
        self.assertEqual(after_meta["file_meta"], before_meta["file_meta"])
        self.assertEqual(after_meta["model_versions"], before_meta["model_versions"])

    def test_actual_fastmcp_lifespan_build_reload_and_status(self):
        runner = support.load_thin_runner()
        with patch.object(tc, "start_background") as start:
            mcp = runner.build_server(self.fixture.home)
            start.assert_not_called()
            async def serving():
                async with mcp._mcp_server.lifespan(mcp._mcp_server):
                    self.assertEqual(start.call_count, 1)
                    tools = await mcp.list_tools()
                    self.assertIn("wf_server_info", [tool.name for tool in tools])
                    result = runner.perform_mcp_reload(notify="defer")
                    self.assertEqual(result.get("status"), "ok", result)
                    self.assertEqual(start.call_count, 1)
            asyncio.run(serving())
            self.assertEqual(start.call_count, 1)
        with patch.object(tc, "_discovery", side_effect=AssertionError("status I/O")):
            result = runner.server_impl.wf_server_info_response(self.fixture.home)
        self.assertIn("tensorwell", result["data"])

    def test_registered_reload_refreshes_client_preserves_pending_start(self):
        scratch = self.fixture.home / "scratch-scripts"
        shutil.copytree(SCRIPTS_ROOT, scratch,
                        ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
        root = self.fixture.home / "reload-root"
        root.mkdir()
        result = subprocess.run([sys.executable, "-B", "-c", _REGISTERED_RELOAD_DRIVER, str(scratch), str(root)],
                                cwd=self.fixture.home, env=dict(os.environ, PYTHONPATH=str(scratch)),
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr[-6000:])
        report = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(report, {"registered_reload": "ok", "fresh_source_and_pin": True,
                                  "retained_worker_and_locks": True, "starts": 1})


if __name__ == "__main__":
    unittest.main()

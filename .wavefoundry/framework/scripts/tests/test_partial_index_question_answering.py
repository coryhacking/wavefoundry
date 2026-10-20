"""Questions keep answering from an unfinished index (wave 215sy, change 213yb).

The registered ``code_ask``, ``code_search`` and ``docs_search`` tools serve the
compatible rows already stored in the SQLite index while the build epoch is
``building`` (running or interrupted), always with an incomplete-coverage
warning, and read those rows from ONE read snapshot so a publication commit
during the read is never combined with older rows. Every case drives the tools
through FastMCP's ``call_tool`` against a store written by the real producer.
"""
from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from server_tools_support import _make_repo, load_server  # noqa: E402

import sqlite_runtime as runtime  # noqa: E402

FIXTURE = {
    "docs/references/guide.md": "# Guide\n\nThe partial_guide_token explains retrieval.\n",
    "docs/plain.md": "# Plain\n\nAn ordinary document about indexing.\n",
    "src/app.py": "def app_handler():\n    return 'app_handler old generation'\n",
    "src/util.py": "def util_helper():\n    return 'util_helper value'\n",
}
COVERAGE_CODE = "index_coverage_incomplete"


def setUpModule():
    load_server()


def _load_indexer():
    spec = importlib.util.spec_from_file_location("indexer", SCRIPTS_ROOT / "indexer.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["indexer"] = mod
    spec.loader.exec_module(mod)
    return mod


def _embedder(gate=None):
    import numpy as np

    def fake_embed(texts, batch_size=256):
        if gate is not None:
            gate()
        for text in list(texts):
            vector = np.zeros(384, dtype=np.float32)
            vector[0] = 1
            vector[1] = (len(text) % 13) / 13
            yield vector

    mock = MagicMock()
    mock.embed.side_effect = fake_embed
    return mock


def _codes(response):
    return [d.get("code") for d in response.get("diagnostics", [])]


@unittest.skipIf(runtime.apsw is None, "qualified APSW runtime unavailable")
class _Case(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.bi = _load_indexer()
        import index_state_store
        self.iss = index_state_store
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"
        _make_repo(self.root, FIXTURE)
        self.srv._fts_invalidate_serving_state()
        self.addCleanup(self.srv._fts_invalidate_serving_state)
        self.srv._FRESHNESS_CACHE.clear()
        self.addCleanup(self.srv._FRESHNESS_CACHE.clear)
        import numpy as np
        self.index = self.srv.WaveIndex(self.root)
        self.index._embed_query = lambda q, model: np.array([1.0] + [0.0] * 383, dtype=np.float32)
        self.index._get_reranker = lambda: None
        handler = SimpleNamespace(
            root=self.root, index=self.index, background_monitor_status=lambda: {},
            assess_setup=lambda *, force=False: {
                "schema_version": 1, "status": "ready", "startup_blocked": False,
                "signature": "fixture", "reasons": [], "actions": [],
                "limitations": [], "timings_ms": {},
            },
        )
        from mcp.server.fastmcp import FastMCP
        self.mcp = FastMCP("partial-index")
        self.srv.register_mcp_surface(self.mcp, lambda: handler)

    def build(self, *, interrupt=False, gate=None, on_finalize=None, **kwargs):
        """Run the real producer; ``interrupt`` leaves the epoch building."""
        real_finalize = self.iss.finalize_build_epoch

        def finalize(index_dir, attempt):
            if on_finalize is not None:
                on_finalize()
            return False if interrupt else real_finalize(index_dir, attempt)

        with patch.object(self.bi, "_get_embedder", return_value=_embedder(gate)), \
                patch.object(self.iss, "finalize_build_epoch", side_effect=finalize), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return self.bi.build_index(self.root, content="all", verbose=False, **kwargs)

    def call(self, name, **arguments):
        result = asyncio.run(self.mcp.call_tool(name, arguments))
        if isinstance(result, tuple):
            structured = result[1]
            if isinstance(structured, dict):
                return structured.get("result", structured)
            result = result[0]
        if isinstance(result, dict):
            return result
        return json.loads(result[0].text)

    def state(self):
        return self.iss.read_build_state(self.index_dir)

    def finalize_open_attempt(self):
        state = self.state()
        self.assertEqual(state["status"], "building")
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, state["attempt_id"]))

    def assert_partial(self, response, *, mode=None):
        data = response["data"]
        coverage = data["index_coverage"]
        self.assertFalse(coverage["complete"])
        self.assertFalse(coverage["absence_is_proof"])
        self.assertEqual(coverage["build_status"], "building")
        self.assertIn(coverage["build_state"], ("building", "interrupted", "unknown"))
        self.assertEqual(coverage["search_mode"], data.get("search_mode"))
        if mode is not None:
            self.assertEqual(data["search_mode"], mode)
        message = coverage["message"]
        for phrase in ("incomplete", "needs updating", "Verify current source", "not proof of absence"):
            self.assertIn(phrase, message)
        self.assertIn(COVERAGE_CODE, _codes(response))

    def assert_healthy(self, response):
        self.assertNotIn("index_coverage", response["data"])
        self.assertNotIn(COVERAGE_CODE, _codes(response))
        self.assertIsNone(response["data"]["fallback_reason"])


class PartialFirstBuildTests(_Case):
    """AC-1/AC-2: an interrupted first build answers from its stored rows."""

    def setUp(self):
        super().setUp()
        self.build(interrupt=True, full=True)
        state = self.state()
        self.assertEqual((state["status"], state["generation"]), ("building", 0))

    def test_registered_tools_answer_with_incomplete_coverage(self):
        code = self.call("code_search", query="app_handler", graph=False)
        self.assertEqual(code["status"], "ok", code)
        self.assertIn("src/app.py", [r["path"] for r in code["data"]["results"]])
        self.assert_partial(code, mode="hybrid")
        self.assertEqual(code["data"]["index_coverage"]["build_state"], "interrupted")
        self.assertEqual(code["data"]["index_coverage"]["source"], "stored_rows")
        self.assertEqual(code["data"]["index_coverage"]["generation"], 0)

        docs = self.call("docs_search", query="partial_guide_token")
        self.assertEqual(docs["status"], "ok", docs)
        self.assertIn("docs/references/guide.md", [r["path"] for r in docs["data"]["results"]])
        self.assert_partial(docs, mode="semantic")

        ask = self.call("code_ask", question="where is app_handler defined?")
        self.assertEqual(ask["status"], "ok", ask)
        self.assertTrue(ask["data"]["citations"])
        self.assert_partial(ask)
        self.assertNotEqual(ask["data"]["index_freshness"], "current")
        self.assertTrue(any("needs updating" in gap for gap in ask["data"]["gaps"]))

    def test_zero_matches_still_warn(self):
        docs = self.call("docs_search", query="anything", kind="seed")
        self.assertEqual(docs["status"], "ok", docs)
        self.assertEqual(docs["data"]["results"], [])
        self.assert_partial(docs)
        code = self.call("code_search", query="app_handler", language="rust", graph=False)
        self.assertEqual(code["data"]["results"], [])
        self.assert_partial(code)

    def test_model_unavailable_serves_stored_fts_rows(self):
        def offline(*_args, **_kwargs):
            raise self.srv.SemanticModelUnavailableOfflineError("offline")
        self.index._embed_query = offline
        code = self.call("code_search", query="app_handler", graph=False)
        self.assertEqual(code["status"], "ok", code)
        self.assertEqual(code["data"]["fallback_reason"], "model_unavailable")
        self.assertIn("src/app.py", [r["path"] for r in code["data"]["results"]])
        self.assert_partial(code, mode="lexical_fallback")
        docs = self.call("docs_search", query="partial_guide_token")
        self.assertIn("docs/references/guide.md", [r["path"] for r in docs["data"]["results"]])
        self.assert_partial(docs, mode="lexical_fallback")

    def test_completion_returns_to_the_healthy_path(self):
        partial = self.call("code_search", query="app_handler", graph=False)
        self.assert_partial(partial)
        self.assertTrue(self.index._partial)
        self.finalize_open_attempt()
        healthy = self.call("code_search", query="app_handler", graph=False)
        self.assertEqual(healthy["status"], "ok", healthy)
        self.assert_healthy(healthy)
        self.assertFalse(self.index._partial)
        self.assertEqual([r["path"] for r in healthy["data"]["results"]],
                         [r["path"] for r in partial["data"]["results"]])
        for tool, args in (("docs_search", {"query": "partial_guide_token"}),
                           ("code_ask", {"question": "where is app_handler defined?"})):
            response = self.call(tool, **args)
            self.assertEqual(response["status"], "ok", response)
            self.assert_healthy(response)

    def test_queries_write_nothing(self):
        def snapshot():
            files = {p.name: p.read_bytes() for p in self.index_dir.iterdir()
                     if p.is_file() and not p.name.endswith("-shm")}
            return files, self.state()
        before = snapshot()
        self.call("code_search", query="app_handler", graph=False)
        self.call("docs_search", query="partial_guide_token")
        self.call("code_ask", question="where is app_handler defined?")
        self.assertEqual(snapshot(), before)
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir), "a query never completes an epoch")

    def test_damaged_fts_never_schedules_indexing_work(self):
        conn = runtime.connect(self.iss.state_store_path(self.index_dir))
        try:
            with conn:
                conn.execute("INSERT INTO fts_code(fts_code) VALUES('delete-all')")
        finally:
            conn.close()
        with patch.object(self.srv, "_start_background_index_refresh", return_value=True) as refresh:
            code = self.call("code_search", query="app_handler", graph=False)
            ask = self.call("code_ask", question="where is app_handler defined?")
        self.assertEqual(code["status"], "ok", code)
        self.assert_partial(code)
        self.assert_partial(ask)
        refresh.assert_not_called()

    def test_missing_model_identity_makes_the_layer_unusable(self):
        conn = runtime.connect(self.iss.state_store_path(self.index_dir))
        try:
            with conn:
                conn.execute("UPDATE build_layer_meta SET value='{}' WHERE key='model_versions'")
        finally:
            conn.close()
        code = self.call("code_search", query="app_handler", graph=False)
        self.assertEqual(code["status"], "error", code)
        self.assertEqual(code["data"]["fallback_reason"], "index_not_ready")
        self.assertEqual(code["data"]["results"], [])
        ask = self.call("code_ask", question="where is app_handler defined?")
        self.assertEqual(ask["data"]["citations"], [])
        self.assertEqual(ask["data"]["fallback_reason"], "index_not_ready")
        docs = self.call("docs_search", query="partial_guide_token")
        self.assertEqual(docs["data"]["search_mode"], "live_fallback")
        self.assertEqual(docs["data"]["index_coverage"]["source"], "live_filesystem")


class UnavailableStorageTests(_Case):
    """AC-3: absent, unusable, corrupt and incompatible storage stay errors."""

    def test_no_usable_rows_is_an_error(self):
        self.iss.begin_build_epoch(self.index_dir, "empty")
        code = self.call("code_search", query="app_handler", graph=False)
        self.assertEqual(code["status"], "error", code)
        self.assertEqual(code["data"]["fallback_reason"], "index_not_ready")
        self.assertEqual(code["data"]["index_coverage"]["source"], "none")
        # code_ask types unavailability in its ordinary envelope: no citations,
        # a typed reason and the infrastructure-failure diagnostic.
        ask = self.call("code_ask", question="where is app_handler defined?")
        self.assertEqual(ask["data"]["citations"], [])
        self.assertEqual(ask["data"]["fallback_reason"], "index_not_ready")
        self.assertIn("search_infrastructure_failure", _codes(ask))
        self.assertEqual(ask["data"]["index_coverage"]["source"], "none")

    def test_absent_store_keeps_its_refusal(self):
        response = self.call("code_search", query="app_handler", graph=False)
        self.assertEqual(response["status"], "error")
        self.assertNotIn("index_coverage", response["data"])

    def test_incompatible_and_corrupt_storage_are_typed_errors(self):
        self.build(interrupt=True, full=True)
        path = self.iss.state_store_path(self.index_dir)
        conn = runtime.connect(path)
        try:
            with conn:
                conn.execute("UPDATE build_layer_meta SET value='99' WHERE key='walker_version'")
        finally:
            conn.close()
        response = self.call("code_search", query="app_handler", graph=False)
        self.assertEqual(response["status"], "error", response)
        self.assertEqual(_codes(response)[0], "index_version_newer")
        self.assertEqual(response["data"]["results"], [])

    def test_corrupt_storage_is_an_explicit_error(self):
        self.build(interrupt=True, full=True)
        with patch.object(self.srv._load_script("sqlite_vector_store"), "read_snapshot",
                          side_effect=runtime.apsw.CorruptError("database disk image is malformed")):
            response = self.call("code_search", query="app_handler", graph=False)
        self.assertEqual(response["status"], "error", response)
        self.assertEqual(response["data"]["fallback_reason"], "query_failed")
        self.assertIn("unreadable", response["diagnostics"][0]["message"])
        self.assertNotIn("no_results", _codes(response))


class HealthyPathTests(_Case):
    """AC-2/AC-4: a complete epoch is served exactly as before, with no warning."""

    def test_complete_build_carries_no_coverage_warning(self):
        self.build(full=True)
        self.assertIsNotNone(self.iss.build_epoch_token(self.index_dir))
        for tool, args in (("code_search", {"query": "app_handler", "graph": False}),
                           ("docs_search", {"query": "partial_guide_token"}),
                           ("code_ask", {"question": "where is app_handler defined?"})):
            response = self.call(tool, **args)
            self.assertEqual(response["status"], "ok", response)
            self.assert_healthy(response)
        self.assertFalse(self.index._partial)
        self.assertFalse(self.srv._load_script("sqlite_vector_store").snapshot_active(self.index_dir))


class PublicationTransitionTests(_Case):
    """AC-3: a publication commit during a degraded read is never combined."""

    def test_publication_between_dense_and_lexical_reads_is_not_combined(self):
        self.build(full=True)
        (self.root / "src" / "fresh.ts").write_text(
            "export function freshHandler() {\n  return 'app_handler fresh_token';\n}\n", encoding="utf-8")
        embedding = threading.Event()
        release = threading.Event()
        published = threading.Event()

        def gate():
            if not embedding.is_set():
                embedding.set()
                release.wait(30)

        failure = []

        def run_build():
            try:
                self.build(interrupt=True, gate=gate, on_finalize=published.set)
            except BaseException as exc:  # noqa: BLE001 - reported below
                failure.append(exc)
                published.set()

        worker = threading.Thread(target=run_build, daemon=True)
        worker.start()
        self.assertTrue(embedding.wait(30), "the build never reached embedding")
        before = self.state()
        self.assertEqual(before["status"], "building")
        # Warm the epoch-keyed caches (stored language vocabulary, loaded
        # index) on the older rows before the publication commits.
        warm = self.call("code_search", query="app_handler", language="typescript", graph=False)
        self.assertEqual(warm["data"]["results"], [])
        self.assert_partial(warm)

        vectors = self.srv._load_script("sqlite_vector_store")
        real_dense = vectors.dense_rows
        straddled = []

        def dense_then_publish(*args, **kwargs):
            rows = real_dense(*args, **kwargs)
            if not straddled:
                straddled.append(True)
                release.set()
                self.assertTrue(published.wait(60), "publication never committed")
            return rows

        with patch.object(vectors, "dense_rows", side_effect=dense_then_publish):
            during = self.call("code_search", query="app_handler fresh_token", graph=False)
        worker.join(60)
        self.assertFalse(failure, failure)
        self.assertTrue(straddled)
        after_state = self.state()
        # The epoch token is unchanged across the publication commit.
        self.assertEqual((after_state["attempt_id"], after_state["status"], after_state["generation"]),
                         (before["attempt_id"], before["status"], before["generation"]))
        self.assertEqual(during["status"], "ok", during)
        self.assert_partial(during)
        self.assertNotIn("src/fresh.ts", [r["path"] for r in during["data"]["results"]],
                         "rows of the new publication were combined with older dense rows")
        # The next read sees the committed generation: no cached handle or
        # verdict from the earlier read is reused.
        after = self.call("code_search", query="app_handler fresh_token", graph=False)
        self.assert_partial(after)
        self.assertIn("src/fresh.ts", [r["path"] for r in after["data"]["results"]])
        typed = self.call("code_search", query="app_handler", language="typescript", graph=False)
        self.assertEqual({r["path"] for r in typed["data"]["results"]}, {"src/fresh.ts"},
                         "a language vocabulary cached before the publication commit was reused")

    def test_publication_between_two_dense_reads_is_not_combined(self):
        """RT-DEL-1: code_ask reads docs vectors, then code vectors. A real
        publication committed between those two dense reads must not reach
        the second one; both come from the generation the call started on."""
        self.build(full=True)
        (self.root / "src" / "fresh.ts").write_text(
            "export function freshHandler() {\n  return 'app_handler fresh_token';\n}\n", encoding="utf-8")
        embedding = threading.Event()
        release = threading.Event()
        published = threading.Event()

        def gate():
            if not embedding.is_set():
                embedding.set()
                release.wait(30)

        failure = []

        def run_build():
            try:
                self.build(interrupt=True, gate=gate, on_finalize=published.set)
            except BaseException as exc:  # noqa: BLE001 - reported below
                failure.append(exc)
                published.set()

        worker = threading.Thread(target=run_build, daemon=True)
        worker.start()
        self.assertTrue(embedding.wait(30), "the build never reached embedding")
        self.assertEqual(self.state()["status"], "building")

        vectors = self.srv._load_script("sqlite_vector_store")
        real_dense = vectors.dense_rows
        reads = []

        def publish_after_first_dense(index_dir, layer, *args, **kwargs):
            rows = real_dense(index_dir, layer, *args, **kwargs)
            reads.append((layer, [r.get("path") for r in rows]))
            if len(reads) == 1:
                release.set()
                self.assertTrue(published.wait(60), "publication never committed")
            return rows

        with patch.object(vectors, "dense_rows", side_effect=publish_after_first_dense):
            during = self.call("code_ask", question="where is app_handler fresh_token defined?")
        worker.join(60)
        self.assertFalse(failure, failure)
        self.assertGreaterEqual(len(reads), 2, reads)
        self.assertEqual(reads[0][0], "docs")
        self.assertIn("code", [layer for layer, _ in reads[1:]])
        for layer, paths in reads[1:]:
            self.assertNotIn("src/fresh.ts", paths,
                             f"the later {layer} dense read saw the newer publication")
        self.assertEqual(during["status"], "ok", during)
        self.assert_partial(during)
        self.assertNotIn("src/fresh.ts", [c["path"] for c in during["data"]["citations"]])
        # Control: the next call reads the committed generation's vectors.
        later = []

        def record(index_dir, layer, *args, **kwargs):
            rows = real_dense(index_dir, layer, *args, **kwargs)
            later.append((layer, [r.get("path") for r in rows]))
            return rows

        with patch.object(vectors, "dense_rows", side_effect=record):
            self.call("code_ask", question="where is app_handler fresh_token defined?")
        self.assertIn("src/fresh.ts", [p for layer, paths in later if layer == "code" for p in paths])


if __name__ == "__main__":
    unittest.main()

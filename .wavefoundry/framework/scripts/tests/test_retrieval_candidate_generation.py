#!/usr/bin/env python3
"""Wave 1wpif (1wpah): retrieval candidate generation honors filters BEFORE
the bounded top-k, refills per-file caps inside a frozen ceiling with typed
diagnostics and exact accounting, and runs Lance ANN at the documented
library defaults (the inert tuning constants are retired).

Every fixture reflects the system: real Lance tables in temp dirs with a
controlled cosine order (chunk i sits at rank i+1 for the fixed query
vector), a real sqlite FTS5 store seeded through the canonical reconcile
path with a controlled BM25 order (short rows outrank long rows), and the
public response functions with only the embedder and reranker stubbed.
"""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import inspect
import io
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from server_tools_support import _make_repo, _write_sqlite_index, load_server

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
QUERY_VEC = np.array([1.0] + [0.0] * 383, dtype=np.float32)
LONG_TAIL = "alpha_handler " + "filler " * 24  # a longer document: BM25 ranks it after the short ones


def _unit(angle_deg: float) -> list[float]:
    """A unit vector whose cosine to QUERY_VEC falls monotonically with the angle."""
    a = np.deg2rad(angle_deg)
    return [float(np.cos(a)), float(np.sin(a))] + [0.0] * 382


def _chunk(i: int, path: str, language: str = "python", text: str = "alpha_handler", kind: str = "code") -> dict:
    return {
        "id": f"c{i}", "path": path, "kind": kind, "language": language,
        "lines": [i * 10 + 1, i * 10 + 5], "section": "", "tags": "",
        "chunk_hash": f"h{i}", "text": text,
    }


def _doc(i: int, path: str, text: str) -> dict:
    return {
        "id": f"d{i}", "path": path, "kind": "doc", "language": "",
        "lines": [i * 10 + 1, i * 10 + 5], "section": f"Section {i}", "tags": "",
        "chunk_hash": f"dh{i}", "text": text,
    }


def _load_iss():
    spec = importlib.util.spec_from_file_location(
        "_iss_candidate_generation", SCRIPTS_ROOT / "index_state_store.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@contextlib.contextmanager
def _quiet():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


class _CandidateFixture(unittest.TestCase):
    """Real Lance tables + a real FTS5 store with controlled rank orders."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.iss = _load_iss()
        indexer = self.srv._load_script("indexer")
        self.model = indexer.DOCS_MODEL
        self.srv._DEGRADED_LOG_STATE.clear()
        self.srv._fts_invalidate_serving_state()
        self.addCleanup(self.srv._DEGRADED_LOG_STATE.clear)
        self.addCleanup(self.srv._fts_invalidate_serving_state)

    def _build(self, code_chunks: list[dict], docs_chunks: "list[dict] | None" = None):
        """Chunks are given in RANK order for QUERY_VEC (index 0 = rank 1);
        the same rows seed the FTS tables through the canonical reconcile."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        code_vectors = [_unit(0.5 * i) for i in range(len(code_chunks))]
        docs_vectors = [_unit(0.5 * i) for i in range(len(docs_chunks or []))]
        _write_sqlite_index(
            self.index_dir,
            docs_chunks=docs_chunks if docs_chunks else None,
            docs_vectors=docs_vectors if docs_chunks else None,
            code_chunks=code_chunks,
            code_vectors=code_vectors,
            model=self.model,
        )
        content = ["code"] + (["docs"] if docs_chunks else [])
        with _quiet():
            self.iss.reconcile_chunk_index(
                self.index_dir, "code", {c["id"] for c in code_chunks}, lambda: [dict(c) for c in code_chunks])
            if docs_chunks:
                self.iss.reconcile_chunk_index(
                    self.index_dir, "docs", {c["id"] for c in docs_chunks}, lambda: [dict(c) for c in docs_chunks])
        self.iss.write_build_bookkeeping(self.index_dir, {
            "model_versions": {name: self.model for name in content},
            "content": content, "file_hashes": {},
        })
        attempt = self.iss.begin_build_epoch(self.index_dir, "fixture-fts")
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, attempt))
        self.epoch = self.iss.build_epoch_state_token(self.index_dir)
        self.assertEqual(self.epoch[1], "complete")
        idx = self.srv.WaveIndex(self.root)
        idx._start_background_model_downloads_after_startup = lambda: None
        idx._embed_query = lambda q, model: QUERY_VEC.copy()
        idx._ensure_loaded()
        return idx

    @staticmethod
    def _spy_lance(idx) -> list[dict]:
        calls: list[dict] = []
        original = idx._vector_search

        def spy(table, qvec, top_n, where=None, layer="project"):
            calls.append({"top_n": top_n, "where": where})
            return original(table, qvec, top_n, where=where, layer=layer)

        idx._vector_search = spy
        return calls

    def _offline_index(self):
        index = MagicMock()
        index.root = self.root
        index.search_code.side_effect = self.srv.SemanticModelUnavailableOfflineError("offline")
        index.search_docs.side_effect = self.srv.SemanticModelUnavailableOfflineError("offline")
        index.search_combined.side_effect = self.srv.SemanticModelUnavailableOfflineError("offline")
        return index

    @staticmethod
    def _codes(resp: dict) -> list:
        return [d.get("code") for d in resp.get("diagnostics", [])]


# ---------------------------------------------------------------------------
# Requirement 1 / AC-1 / AC-3: shared predicates and the rank-31 fixture
# ---------------------------------------------------------------------------


class LanguagePredicateTests(unittest.TestCase):
    """The shared allowlist resolution behind both substrates (SEC-4)."""

    def setUp(self):
        self.srv = load_server()

    def test_category_and_names_resolve_through_the_allowlist(self):
        web = self.srv._LANG_CATEGORIES["web"]
        self.assertEqual(self.srv._language_filter_names("web"), (web, True))
        for value in ("typescript", "tsx", ".tsx", "TypeScript"):
            self.assertEqual(self.srv._language_filter_names(value), (frozenset({"typescript"}), True), value)
        # The chunker's stored-language vocabulary is allowlisted too.
        self.assertEqual(self.srv._language_filter_names("terraform"), (frozenset({"terraform"}), True))
        self.assertEqual(self.srv._language_filter_names(".mts"), (frozenset({"typescript"}), True))
        self.assertIsNone(self.srv._language_filter_names(""))
        self.assertIsNone(self.srv._language_filter_names(None))

    def test_unknown_values_never_enter_a_predicate(self):
        hostile = "python' OR 1=1 --"
        names, pushdown = self.srv._language_filter_names(hostile)
        self.assertEqual(names, frozenset({hostile}))
        self.assertFalse(pushdown)
        self.assertIsNone(self.srv._language_where_clause(names))
        self.assertEqual(self.srv._language_filter_names("proto"), (frozenset({"proto"}), False))
        self.assertEqual(self.srv._language_where_clause({"python"}), "language = 'python'")
        self.assertEqual(
            self.srv._language_where_clause(self.srv._LANG_CATEGORIES["web"]),
            "language IN ('css', 'html', 'javascript', 'scss', 'typescript')",
        )
        for name in self.srv._canonical_language_vocabulary():
            self.assertRegex(name, r"^[a-z][a-z0-9]{0,31}$")

    def test_search_code_pushes_the_same_set_into_lance_and_fts(self):
        srv = self.srv
        index = srv.WaveIndex.__new__(srv.WaveIndex)
        index._vector_available = {("project", "code")}
        captured: dict = {}

        def lance(table, qvec, top_n, where=None, layer="project"):
            captured["where"] = where
            captured["top_n"] = top_n
            return []

        def fts(table_name, query, top_n, kind=None, tags=None, layer="project", languages=None):
            captured["languages"] = languages
            return []

        with patch.object(index, "_ensure_loaded"), \
                patch.object(index, "_start_background_model_downloads_after_startup"), \
                patch.object(index, "_embed_query", return_value=None), \
                patch.object(index, "_indexer_constant", return_value="model"), \
                patch.object(index, "_open_vector_layer", return_value=object()), \
                patch.object(index, "_vector_search", side_effect=lance), \
                patch.object(index, "_fts5_lexical_search", side_effect=fts), \
                patch.object(index, "_get_reranker", return_value=None):
            index.search_code("q", language="web", top_n=7, kind="code")
            self.assertEqual(captured["where"], "kind = 'code' AND language IN ('css', 'html', 'javascript', 'scss', 'typescript')")
            self.assertEqual(captured["languages"], ["css", "html", "javascript", "scss", "typescript"])
            self.assertEqual(captured["top_n"], max(7 * 4, srv.VECTOR_TOP_K), "a pushed-down language keeps its former single window")
            captured.clear()
            index.search_code("q", language="python' OR 1=1 --", top_n=7)
            self.assertIsNone(captured["where"], "a non-allowlisted value is never echoed into the predicate")
            self.assertIsNone(captured["languages"])


class RankThirtyOneLanguageTests(_CandidateFixture):
    """AC-1: a selected-language candidate below 30 higher-ranked other-language
    rows stays retrievable on the healthy semantic path and the lexical fallback."""

    def _rank_32_fixture(self):
        chunks = [_chunk(i, f"src/py{i}.py") for i in range(31)]
        chunks.append(_chunk(31, "web/app.ts", language="typescript", text=LONG_TAIL))
        return self._build(chunks)

    def test_fixture_places_the_typescript_row_past_both_windows(self):
        idx = self._rank_32_fixture()
        table = idx._open_vector_layer("project", "code")
        dense_window = idx._vector_search(table, QUERY_VEC, 31)
        self.assertEqual({r["language"] for r in dense_window}, {"python"})
        self.assertEqual(idx._vector_search(table, QUERY_VEC, 32)[-1]["path"], "web/app.ts")
        lexical_window = self.iss.fts_search(self.index_dir, "code", "alpha_handler", limit=31)
        self.assertEqual(len(lexical_window), 31)
        self.assertEqual({r["language"] for r in lexical_window}, {"python"})

    def test_healthy_semantic_search_returns_the_rank_32_typescript_row(self):
        idx = self._rank_32_fixture()
        calls = self._spy_lance(idx)
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_search_response(idx, "alpha_handler", language="typescript", epoch_state=self.epoch)
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["data"]["search_mode"], "hybrid")
        self.assertEqual([r["path"] for r in resp["data"]["results"]], ["web/app.ts"])
        self.assertEqual(resp["data"]["language_extensions"], ["ts", "tsx"])
        self.assertEqual(len(calls), 1)
        self.assertIn("language = 'typescript'", calls[0]["where"])
        accounting = resp["data"]["retrieval_accounting"]
        self.assertEqual(accounting["sources"]["code_dense"], {"queries": 1, "examined_rows": 1, "windows": [30]})
        self.assertEqual(accounting["sources"]["code_lexical"], {"queries": 1, "examined_rows": 1, "windows": [30]})
        self.assertNotIn("fill", resp["data"], "a pushed-down language needs no refill")

    def test_category_filter_returns_the_rank_32_typescript_row(self):
        idx = self._rank_32_fixture()
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_search_response(idx, "alpha_handler", language="web", epoch_state=self.epoch)
        self.assertEqual([r["path"] for r in resp["data"]["results"]], ["web/app.ts"])
        self.assertEqual(resp["data"]["language_resolved"], sorted(self.srv._LANG_CATEGORIES["web"]))

    def test_lexical_fallback_returns_the_rank_32_typescript_row(self):
        self._rank_32_fixture()
        with patch.object(self.srv, "_fts_probed_fetch", wraps=self.srv._fts_probed_fetch) as fetch:
            resp = self.srv.code_search_response(
                self._offline_index(), "alpha_handler", language="typescript", epoch_state=self.epoch)
        self.assertEqual(resp["data"]["search_mode"], "lexical_fallback")
        self.assertEqual([r["path"] for r in resp["data"]["results"]], ["web/app.ts"])
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(fetch.call_args.kwargs.get("languages"), ["typescript"])
        self.assertEqual(resp["data"]["retrieval_accounting"]["sources"], {
            "code_lexical": {"queries": 1, "examined_rows": 1, "windows": [7]},
        })

    def test_non_allowlisted_language_is_served_by_the_bounded_refill(self):
        chunks = [_chunk(i, f"src/py{i}.py") for i in range(31)]
        chunks.append(_chunk(31, "api/schema.proto", language="proto", text=LONG_TAIL))
        idx = self._build(chunks)
        calls = self._spy_lance(idx)
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_search_response(idx, "alpha_handler", language="proto", limit=5, epoch_state=self.epoch)
        self.assertEqual([r["path"] for r in resp["data"]["results"]], ["api/schema.proto"])
        self.assertTrue(all(c["where"] is None for c in calls), "the raw value never reaches the predicate")
        self.assertEqual([c["top_n"] for c in calls], [30, 60])
        fill = resp["data"]["fill"]
        self.assertEqual(fill["reason"], self.srv.FILL_REASON_EXHAUSTED)
        self.assertEqual(fill["constraints"]["language_pushdown"], False)
        self.assertEqual(fill["rounds"], 2)


# ---------------------------------------------------------------------------
# Requirements 2 / 3, AC-2: per-file fill, hostile skew, typed outcomes
# ---------------------------------------------------------------------------


class PerFileFillTests(_CandidateFixture):
    """AC-2: limit=5,max_per_file=1 fills five files when five files match."""

    def test_limit_5_max_per_file_1_returns_five_files(self):
        chunks = [_chunk(i, "src/big.py", text="unrelated body") for i in range(31)]
        chunks += [_chunk(31 + j, f"src/other{j}.py", text="unrelated body") for j in range(4)]
        idx = self._build(chunks)
        calls = self._spy_lance(idx)
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_search_response(idx, "alpha_handler", limit=5, max_per_file=1, epoch_state=self.epoch)
        paths = [r["path"] for r in resp["data"]["results"]]
        self.assertEqual(len(paths), 5)
        self.assertEqual(len(set(paths)), 5)
        self.assertEqual(paths[0], "src/big.py", "the highest-ranked chunk per file is retained")
        self.assertEqual([c["top_n"] for c in calls], [30, 60])
        fill = resp["data"]["fill"]
        self.assertEqual(fill["requested"], 5)
        self.assertEqual(fill["returned"], 5)
        self.assertEqual(fill["rounds"], 2)
        self.assertEqual(fill["windows"], [30, 60])
        self.assertIsNone(fill["reason"])
        self.assertEqual(fill["constraints"]["max_per_file"], 1)
        accounting = resp["data"]["retrieval_accounting"]
        self.assertEqual(accounting["sources"]["code_dense"], {"queries": 2, "examined_rows": 35, "windows": [30, 60]})
        # The lexical source returned fewer rows than its window on round one
        # (no token matches) and is exhausted: it is not queried again.
        self.assertEqual(accounting["sources"]["code_lexical"], {"queries": 1, "examined_rows": 0, "windows": [30]})
        self.assertEqual(accounting["substrate_queries"], 3)
        self.assertEqual(accounting["examined_rows"], 35)
        self.assertEqual(accounting["ceiling"], {
            "sources": ["code_dense", "code_lexical"], "queries_per_source": 4, "rows_per_source": 240,
            "substrate_queries": 8, "examined_rows": 480,
        })
        self.assertEqual(accounting["windows"], [30, 60, 120, 240])
        self.assertEqual(self._codes(resp), [])

    def test_no_per_file_cap_means_no_refill_and_the_former_single_window(self):
        chunks = [_chunk(i, f"src/f{i}.py", text="unrelated body") for i in range(40)]
        idx = self._build(chunks)
        calls = self._spy_lance(idx)
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_search_response(idx, "alpha_handler", limit=5, epoch_state=self.epoch)
        self.assertEqual(len(resp["data"]["results"]), 5)
        self.assertEqual([c["top_n"] for c in calls], [self.srv.VECTOR_TOP_K])
        self.assertNotIn("fill", resp["data"])
        self.assertEqual(resp["data"]["retrieval_accounting"]["substrate_queries"], 2)


class HostileSkewTests(_CandidateFixture):
    """AC-2 / Requirement 3: termination at the frozen ceiling with exact
    accounting, and a distinct reason when the substrate is exhausted."""

    def test_ceiling_exit_is_typed_terminates_and_accounts_exactly(self):
        chunks = [_chunk(i, "src/big.py", text="unrelated body") for i in range(250)]
        chunks += [_chunk(250 + j, f"src/other{j}.py", text="unrelated body") for j in range(4)]
        idx = self._build(chunks)
        calls = self._spy_lance(idx)
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_search_response(idx, "alpha_handler", limit=5, max_per_file=1, epoch_state=self.epoch)
        self.assertEqual(resp["status"], "ok")
        self.assertEqual([r["path"] for r in resp["data"]["results"]], ["src/big.py"])
        self.assertEqual([c["top_n"] for c in calls], [30, 60, 120, 240], "four monotonic windows, then stop")
        fill = resp["data"]["fill"]
        self.assertEqual(fill["reason"], self.srv.FILL_REASON_CEILING)
        self.assertEqual(fill["rounds"], 4)
        self.assertEqual(fill["windows"], [30, 60, 120, 240])
        self.assertEqual(fill["returned"], 1)
        accounting = resp["data"]["retrieval_accounting"]
        self.assertEqual(accounting["sources"]["code_dense"], {"queries": 4, "examined_rows": 240, "windows": [30, 60, 120, 240]})
        self.assertEqual(accounting["sources"]["code_lexical"], {"queries": 1, "examined_rows": 0, "windows": [30]})
        self.assertEqual(accounting["substrate_queries"], 5)
        self.assertEqual(accounting["examined_rows"], 240)
        self.assertLessEqual(accounting["substrate_queries"], accounting["ceiling"]["substrate_queries"])
        self.assertLessEqual(accounting["examined_rows"], accounting["ceiling"]["examined_rows"])
        for entry in accounting["sources"].values():
            self.assertLessEqual(entry["queries"], self.srv.REFILL_MAX_QUERIES_PER_SOURCE)
            self.assertLessEqual(entry["examined_rows"], self.srv.REFILL_MAX_ROWS_PER_SOURCE)
        codes = self._codes(resp)
        self.assertIn(self.srv.FILL_REASON_CEILING, codes)
        self.assertNotIn(self.srv.FILL_REASON_EXHAUSTED, codes)
        ceiling_diag = next(d for d in resp["diagnostics"] if d["code"] == self.srv.FILL_REASON_CEILING)
        self.assertIn("4 rounds", ceiling_diag["message"])
        self.assertIn("240", ceiling_diag["message"])
        self.assertEqual(ceiling_diag["recovery_tools"], ["code_keyword", "code_pattern"])
        # Informational, like every other retrieval diagnostic: the envelope
        # stays ok and the 1uugg lifecycle advisory tag is not borrowed.
        self.assertNotIn("advisory", ceiling_diag)

    def test_substrate_exhaustion_is_a_distinct_reason(self):
        chunks = [_chunk(i, "src/big.py", text="unrelated body") for i in range(10)]
        chunks += [_chunk(10 + j, "src/small.py", text="unrelated body") for j in range(2)]
        idx = self._build(chunks)
        calls = self._spy_lance(idx)
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_search_response(idx, "alpha_handler", limit=5, max_per_file=1, epoch_state=self.epoch)
        self.assertEqual(sorted(r["path"] for r in resp["data"]["results"]), ["src/big.py", "src/small.py"])
        self.assertEqual([c["top_n"] for c in calls], [30])
        fill = resp["data"]["fill"]
        self.assertEqual(fill["reason"], self.srv.FILL_REASON_EXHAUSTED)
        self.assertEqual(fill["rounds"], 1)
        self.assertEqual(resp["data"]["retrieval_accounting"]["sources"]["code_dense"],
                         {"queries": 1, "examined_rows": 12, "windows": [30]})
        codes = self._codes(resp)
        self.assertIn(self.srv.FILL_REASON_EXHAUSTED, codes)
        self.assertNotIn(self.srv.FILL_REASON_CEILING, codes)

    def test_reranker_input_window_is_unchanged_by_refill(self):
        """PERF-RDY-4: refill feeds the per-file selection, never the cross-encoder cap."""
        chunks = [_chunk(i, "src/big.py", text="unrelated body") for i in range(25)]
        chunks += [_chunk(25 + j, f"src/single{j}.py", text="unrelated body") for j in range(40)]
        idx = self._build(chunks)
        calls = self._spy_lance(idx)
        seen: list[int] = []
        reranker = MagicMock()

        def rerank(query, docs):
            seen.append(len(docs))
            return [float(i) for i in range(len(docs))]

        reranker.rerank.side_effect = rerank
        with patch.object(idx, "_get_reranker", return_value=reranker):
            resp = self.srv.code_search_response(idx, "alpha_handler", limit=7, max_per_file=1, epoch_state=self.epoch)
        self.assertEqual([c["top_n"] for c in calls], [30, 60], "round two examined 60 rows (36 files)")
        self.assertEqual(len(resp["data"]["results"]), 7)
        self.assertTrue(resp["data"]["reranked"])
        former_window = max(7 * 4, self.srv.VECTOR_TOP_K)
        self.assertEqual(seen, [former_window], "the cross-encoder saw exactly the pre-1wpah window")


class DegradedFtsRefillTests(_CandidateFixture):
    """The lexical fallback carries the same pushdown and refill contract."""

    def test_lexical_fallback_fills_five_files_within_two_windows(self):
        chunks = [_chunk(i, "src/big.py") for i in range(31)]
        chunks += [_chunk(31 + j, f"src/other{j}.py", text=LONG_TAIL) for j in range(4)]
        self._build(chunks)
        with patch.object(self.srv, "_fts_probed_fetch", wraps=self.srv._fts_probed_fetch) as fetch:
            resp = self.srv.code_search_response(
                self._offline_index(), "alpha_handler", limit=5, max_per_file=1, epoch_state=self.epoch)
        self.assertEqual(resp["data"]["search_mode"], "lexical_fallback")
        paths = [r["path"] for r in resp["data"]["results"]]
        self.assertEqual(len(paths), 5)
        self.assertEqual(len(set(paths)), 5)
        self.assertEqual([c.args[3] for c in fetch.call_args_list], [30, 60])
        fill = resp["data"]["fill"]
        self.assertEqual((fill["rounds"], fill["reason"], fill["returned"]), (2, None, 5))
        self.assertEqual(resp["data"]["retrieval_accounting"]["sources"]["code_lexical"],
                         {"queries": 2, "examined_rows": 35, "windows": [30, 60]})

    def test_lexical_fallback_ceiling_is_typed_and_terminates(self):
        chunks = [_chunk(i, "src/big.py") for i in range(250)]
        chunks += [_chunk(250 + j, f"src/other{j}.py", text=LONG_TAIL) for j in range(4)]
        self._build(chunks)
        with patch.object(self.srv, "_fts_probed_fetch", wraps=self.srv._fts_probed_fetch) as fetch:
            resp = self.srv.code_search_response(
                self._offline_index(), "alpha_handler", limit=5, max_per_file=1, epoch_state=self.epoch)
        self.assertEqual([r["path"] for r in resp["data"]["results"]], ["src/big.py"])
        self.assertEqual([c.args[3] for c in fetch.call_args_list], [30, 60, 120, 240])
        self.assertEqual(resp["data"]["fill"]["reason"], self.srv.FILL_REASON_CEILING)
        self.assertIn(self.srv.FILL_REASON_CEILING, self._codes(resp))
        self.assertEqual(resp["data"]["retrieval_accounting"]["sources"], {
            "code_lexical": {"queries": 4, "examined_rows": 240, "windows": [30, 60, 120, 240]},
        })

    def test_lexical_fallback_exhaustion_is_distinct(self):
        chunks = [_chunk(i, "src/big.py") for i in range(10)] + [_chunk(10, "src/small.py")]
        self._build(chunks)
        resp = self.srv.code_search_response(
            self._offline_index(), "alpha_handler", limit=5, max_per_file=1, epoch_state=self.epoch)
        self.assertEqual(resp["data"]["fill"]["reason"], self.srv.FILL_REASON_EXHAUSTED)
        self.assertIn(self.srv.FILL_REASON_EXHAUSTED, self._codes(resp))
        self.assertEqual(len(resp["data"]["results"]), 2)

    def test_degraded_serve_without_constraints_is_one_query_per_table(self):
        self._build([_chunk(i, f"src/f{i}.py") for i in range(5)],
                    docs_chunks=[_doc(i, f"docs/d{i}.md", "alpha_handler guide") for i in range(3)])
        with patch.object(self.srv, "_fts_probed_fetch", wraps=self.srv._fts_probed_fetch) as fetch:
            serve = self.srv._fts_degraded_serve(self.root, ("docs", "code"), "alpha_handler", 7)
        self.assertTrue(serve["available"])
        self.assertEqual(fetch.call_count, 1)
        self.assertNotIn("fill", serve)
        self.assertEqual(len(serve["results"]), 7)


# ---------------------------------------------------------------------------
# AC-2 aggregate: code_ask against the stated public-call formula
# ---------------------------------------------------------------------------


class CodeAskAggregateAccountingTests(_CandidateFixture):
    """The multi-source public-call aggregate: 16 / 960 over the four fused
    sources, the assessment expansion inside those budgets, and the keyword
    pass as a fifth source (20 / 1200) when it fires."""

    def _corpus(self):
        code = [_chunk(i, f"src/billing{i}.py", text=f"def billing_handler_{i}(): pass  # billing handler") for i in range(5)]
        docs = [_doc(i, f"docs/billing{i}.md", f"The billing handler guide {i}: where the billing handler lives") for i in range(5)]
        return self._build(code, docs_chunks=docs)

    def _lexical_rows(self, table: str, question: str) -> int:
        return len(self.iss.fts_search(self.index_dir, table, question, limit=self.srv.LEXICAL_TOP_K))

    def test_navigational_call_accounts_four_sources_under_the_16_960_ceiling(self):
        idx = self._corpus()
        question = "where is the billing handler"
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_ask_response(idx, self.root, question, epoch_state=self.epoch)
        data = resp["data"]
        self.assertEqual(data["question_type"], "navigational")
        self.assertEqual(data["search_mode"], "hybrid")
        self.assertGreaterEqual(len(data["citations"]), 2, "the keyword pass must stay suppressed")
        accounting = data["retrieval_accounting"]
        self.assertEqual(sorted(accounting["sources"]), ["code_dense", "code_lexical", "docs_dense", "docs_lexical"])
        self.assertNotIn(self.srv.KEYWORD_SUBSTRATE_SOURCE, accounting["sources"])
        lex_docs = self._lexical_rows("docs", question)
        lex_code = self._lexical_rows("code", question)
        self.assertGreater(lex_docs + lex_code, 0, "the fixture must exercise the lexical half")
        self.assertEqual(accounting["sources"], {
            "code_dense": {"queries": 1, "examined_rows": 5, "windows": [self.srv.VECTOR_TOP_K]},
            "code_lexical": {"queries": 1, "examined_rows": lex_code, "windows": [self.srv.LEXICAL_TOP_K]},
            "docs_dense": {"queries": 1, "examined_rows": 5, "windows": [self.srv.VECTOR_TOP_K]},
            "docs_lexical": {"queries": 1, "examined_rows": lex_docs, "windows": [self.srv.LEXICAL_TOP_K]},
        })
        self.assertEqual(accounting["substrate_queries"], 4)
        self.assertEqual(accounting["examined_rows"], 10 + lex_docs + lex_code)
        self.assertEqual(accounting["ceiling"], {
            "sources": ["docs_dense", "code_dense", "docs_lexical", "code_lexical"],
            "queries_per_source": 4, "rows_per_source": 240,
            "substrate_queries": 16, "examined_rows": 960,
        })
        # The aggregate identity: the public-call numbers are the per-source sums.
        self.assertEqual(accounting["substrate_queries"], sum(s["queries"] for s in accounting["sources"].values()))
        self.assertEqual(accounting["examined_rows"], sum(s["examined_rows"] for s in accounting["sources"].values()))

    def test_assessment_expansion_counts_inside_the_per_source_budgets(self):
        idx = self._corpus()
        question = "what are the gaps and weaknesses in the billing handler"
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_ask_response(idx, self.root, question, epoch_state=self.epoch)
        data = resp["data"]
        self.assertEqual(data["question_type"], "assessment")
        accounting = data["retrieval_accounting"]
        sources = accounting["sources"]
        top_k = self.srv.VECTOR_TOP_K_EXPLANATORY
        self.assertEqual(sources["docs_dense"]["queries"], 2, "one main plus one derived docs vector query")
        self.assertEqual(sources["docs_dense"]["windows"], [top_k, top_k])
        self.assertEqual(sources["docs_dense"]["examined_rows"], 10, "two distinct query texts over five docs rows")
        self.assertEqual(sources["code_dense"], {"queries": 1, "examined_rows": 5, "windows": [top_k]})
        self.assertEqual(sources["docs_lexical"]["queries"], 2, "the derived lexical pass hits both tables")
        self.assertEqual(sources["code_lexical"]["queries"], 2)
        self.assertEqual(accounting["substrate_queries"], 7)
        self.assertEqual(accounting["ceiling"]["substrate_queries"], 16)
        self.assertEqual(accounting["ceiling"]["examined_rows"], 960)
        for entry in sources.values():
            self.assertLessEqual(entry["queries"], self.srv.REFILL_MAX_QUERIES_PER_SOURCE)
            self.assertLessEqual(entry["examined_rows"], self.srv.REFILL_MAX_ROWS_PER_SOURCE)
        self.assertLessEqual(accounting["examined_rows"], 960)

    def test_keyword_pass_is_accounted_as_a_fifth_source(self):
        idx = self._build([_chunk(0, "src/billing.py", text="def billing_handler(): pass")])
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_ask_response(idx, self.root, "where is the billing handler", epoch_state=self.epoch)
        accounting = resp["data"]["retrieval_accounting"]
        self.assertIn(self.srv.KEYWORD_SUBSTRATE_SOURCE, accounting["sources"])
        keyword = accounting["sources"][self.srv.KEYWORD_SUBSTRATE_SOURCE]
        self.assertEqual(keyword["queries"], 1)
        self.assertEqual(keyword["windows"], [self.srv.KEYWORD_PASS_WINDOW])
        self.assertEqual(accounting["ceiling"]["sources"],
                         ["docs_dense", "code_dense", "docs_lexical", "code_lexical", "keyword"])
        self.assertEqual(accounting["ceiling"]["substrate_queries"], 20)
        self.assertEqual(accounting["ceiling"]["examined_rows"], 1200)
        self.assertLessEqual(accounting["substrate_queries"], 20)

    def test_degraded_code_ask_accounts_only_the_lexical_pass(self):
        self._corpus()
        resp = self.srv.code_ask_response(self._offline_index(), self.root, "where is the billing handler",
                                          epoch_state=self.epoch)
        self.assertEqual(resp["data"]["search_mode"], "lexical_fallback")
        accounting = resp["data"]["retrieval_accounting"]
        self.assertEqual(sorted(accounting["sources"]), ["code_lexical", "docs_lexical"])
        self.assertEqual(accounting["substrate_queries"], 2)
        self.assertEqual(accounting["ceiling"]["substrate_queries"], 16)


class AccountingLedgerTests(unittest.TestCase):
    """The ledger's counting rules and the window sequence."""

    def setUp(self):
        self.srv = load_server()

    def test_nested_windows_count_queries_but_examine_the_largest_prefix(self):
        srv = self.srv
        with srv._ledger_scope() as ledger:
            srv._ledger_record("code_dense", "q", 30, 30)
            srv._ledger_record("code_dense", "q", 60, 45)
            srv._ledger_record("code_dense", "derived", 50, 10)
            srv._ledger_record("docs_lexical", "q", 20, 3)
            summary = srv._ledger_summary(srv.CODE_ASK_SUBSTRATE_SOURCES, ledger)
        self.assertEqual(summary["sources"]["code_dense"], {"queries": 3, "examined_rows": 55, "windows": [30, 60, 50]})
        self.assertEqual(summary["substrate_queries"], 4)
        self.assertEqual(summary["examined_rows"], 58)
        self.assertEqual(summary["ceiling"]["substrate_queries"], 16)
        self.assertIsNone(srv._RETRIEVAL_LEDGER.get(), "the scope resets the ledger")
        srv._ledger_record("code_dense", "q", 30, 30)  # outside any scope: a no-op
        self.assertIsNone(srv._RETRIEVAL_LEDGER.get())

    def test_extra_fired_source_extends_the_ceiling(self):
        srv = self.srv
        with srv._ledger_scope() as ledger:
            srv._ledger_record(srv.KEYWORD_SUBSTRATE_SOURCE, "tok", 50, 2)
            summary = srv._ledger_summary(srv.CODE_ASK_SUBSTRATE_SOURCES, ledger)
        self.assertEqual(summary["ceiling"]["sources"][-1], "keyword")
        self.assertEqual((summary["ceiling"]["substrate_queries"], summary["ceiling"]["examined_rows"]), (20, 1200))
        empty = srv._ledger_summary(srv.CODE_SEARCH_SUBSTRATE_SOURCES, None)
        self.assertEqual((empty["substrate_queries"], empty["examined_rows"]), (0, 0))
        self.assertEqual((empty["ceiling"]["substrate_queries"], empty["ceiling"]["examined_rows"]), (8, 480))

    def test_window_sequence_and_frozen_constants(self):
        srv = self.srv
        self.assertEqual(srv.REFILL_WINDOWS, (30, 60, 120, 240))
        self.assertEqual(srv.REFILL_MAX_QUERIES_PER_SOURCE, 4)
        self.assertEqual(srv.REFILL_MAX_ROWS_PER_SOURCE, 240)
        self.assertEqual(srv._refill_windows(5), (30, 60, 120, 240))
        self.assertEqual(srv._refill_windows(30), (30, 60, 120, 240))
        self.assertEqual(srv._refill_windows(100), (120, 240))
        self.assertEqual(srv._refill_windows(300), (300,))
        self.assertEqual(srv.FILL_REASON_CEILING, "bounded_ceiling_reached")
        self.assertEqual(srv.FILL_REASON_EXHAUSTED, "substrate_exhausted")

    def test_keyword_pass_window_matches_code_keyword_default(self):
        default = inspect.signature(self.srv.code_keyword_response).parameters["limit"].default
        self.assertEqual(self.srv.KEYWORD_PASS_WINDOW, default)


# ---------------------------------------------------------------------------
# Requirements 4 / 5, AC-4 / AC-5: the query builder runs at library defaults
# ---------------------------------------------------------------------------


class CandidateMergeIdentityTests(_CandidateFixture):
    """Delivery repair RED-DEL-2 / CODE-DEL-1: every substrate join keys by
    chunk id, so two DISTINCT chunks that share a path and line range are
    joined and attributed separately.

    Live store at the time of review: 433 docs and 17 code groups of distinct
    chunks sharing coordinates. The legacy ``(path, tuple(lines))`` key was
    last-wins, so a lexical hit on one twin was recorded against whichever
    twin the dense pass happened to add last.
    """

    def _twins(self):
        """Two chunks at ``src/x.py`` lines [10, 12]: the lexical twin ranks
        FIRST in dense order and its coordinate double ranks LAST, the shape
        under which last-wins misattributes."""
        lexical_twin = {
            "id": "c_g", "path": "src/x.py", "kind": "code", "language": "python",
            "lines": [10, 12], "section": "", "tags": "", "chunk_hash": "hg",
            "text": "def g():\n    return omega_token",
        }
        coordinate_double = dict(
            lexical_twin, id="c_f", chunk_hash="hf",
            text="def f():\n    return alpha_token",
        )
        filler = [_chunk(i, "src/f%d.py" % i, text="alpha_token filler") for i in range(1, 6)]
        return self._build([lexical_twin] + filler + [coordinate_double])

    @staticmethod
    def _twin_citations(resp):
        return [c for c in resp["data"]["citations"] if c["path"] == "src/x.py"]

    def _ask(self, idx):
        with patch.object(idx, "_get_reranker", return_value=None):
            return self.srv.code_ask_response(
                idx, self.root, "where is omega_token", epoch_state=self.epoch,
            )

    def test_lexical_hit_is_attributed_to_its_own_chunk(self):
        idx = self._twins()
        resp = self._ask(idx)
        self.assertEqual(resp["data"]["search_mode"], "hybrid")
        twins = self._twin_citations(resp)
        self.assertEqual(len(twins), 2, "both coordinate twins survive selection")
        omega = [c for c in twins if "omega_token" in c["excerpt"]]
        alpha = [c for c in twins if "alpha_token" in c["excerpt"]]
        self.assertEqual((len(omega), len(alpha)), (1, 1), twins)
        self.assertIn("lexical", omega[0]["sources"], omega[0])
        self.assertNotIn("lexical", alpha[0]["sources"], alpha[0])

    def test_the_legacy_coordinate_key_misattributes_the_same_fixture(self):
        """Non-vacuity: restore the pre-repair key and the lexical label
        lands on the wrong twin."""
        srv = self.srv
        legacy = lambda c: (c.get("path", ""), tuple(c.get("lines") or []))
        idx = self._twins()
        with patch.object(srv, "_candidate_merge_key", side_effect=legacy):
            resp = self._ask(idx)
        twins = self._twin_citations(resp)
        alpha = [c for c in twins if "alpha_token" in c["excerpt"]]
        self.assertTrue(alpha)
        self.assertIn("lexical", alpha[0]["sources"],
                      "the legacy key must reproduce the misattribution")

    def test_refill_windows_never_exceed_the_ceiling_for_any_reachable_request(self):
        """Wave 1wpif, SEC-RV1-2: `_refill_windows` grants a single oversized
        window above the last `REFILL_WINDOWS` entry, exceeding
        `REFILL_MAX_ROWS_PER_SOURCE`. That is a FROZEN admitted contract
        (pinned by `test_window_sequence_and_frozen_constants`) and it is
        unreachable: no public MCP entry can pass a value above the ceiling. A
        clamp was tried and reverted rather than change a pinned design inside
        a delivery review; the disposition is routed to `1wpih`.

        Cycle-3 (SEC-RV2-2): the first version of this test hardcoded the
        clamp values, so its own docstring's promise -- that raising a clamp
        would fail it -- was false, and the reverification lane proved it by
        raising the lexical clamp tenfold with the test still green. The
        clamps are now READ FROM PRODUCTION, so the promise holds.
        """
        srv = self.srv
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        def clamp_of(func_name):
            """The literal ceiling in `min(int(limit), N)` inside a response.

            Wave 1wpif cycle-4 (SEC-RV3-3): the first version returned the
            FIRST `min(x, int)` in walk order, so an unrelated `min` added
            earlier in the function silently repointed the pin -- the
            reverification lane demonstrated it with a decoy that left the
            test green while the real clamp was raised above the ceiling. Bind
            to the clamp that actually reads `limit`, and require it to be
            unique so a second one cannot be picked arbitrarily.
            """
            fn = next(
                (n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef) and n.name == func_name),
                None,
            )
            self.assertIsNotNone(fn, f"{func_name} not found")
            found = []
            for call in ast.walk(fn):
                if not (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Name)
                        and call.func.id == "min"
                        and len(call.args) == 2
                        and isinstance(call.args[1], ast.Constant)
                        and isinstance(call.args[1].value, int)):
                    continue
                # The first argument must read the caller's `limit`.
                names = {n.id for n in ast.walk(call.args[0]) if isinstance(n, ast.Name)}
                if "limit" in names:
                    found.append(call.args[1].value)
            self.assertEqual(
                len(found), 1,
                f"{func_name} must contain exactly one min(<reads limit>, N) "
                f"clamp for this pin to bind unambiguously; found {found}",
            )
            return found[0]

        def code_ask_top_n():
            """The largest literal `top_n` code_ask hands to search_combined.

            Read from every `search_combined` call in the code_ask body,
            nested helpers included, so adding a second call with a larger
            window cannot slip past this test.
            """
            fn = next(
                (n for n in ast.walk(tree)
                 if isinstance(n, ast.FunctionDef)
                 and n.name == "_code_ask_response_body"),
                None,
            )
            self.assertIsNotNone(fn, "_code_ask_response_body not found")
            found = []
            for call in ast.walk(fn):
                if not isinstance(call, ast.Call):
                    continue
                name = getattr(call.func, "attr", None) or getattr(call.func, "id", None)
                if name != "search_combined":
                    continue
                for kw in call.keywords:
                    if (kw.arg == "top_n"
                            and isinstance(kw.value, ast.Constant)
                            and isinstance(kw.value.value, int)):
                        found.append(kw.value.value)
            self.assertTrue(found, "no literal top_n on a search_combined call in code_ask")
            return max(found)

        # Every clamp is read from the shipped source, not restated here.
        reachable = {
            "code_search": clamp_of("code_search_response"),
            "docs_search": clamp_of("docs_search_response"),
            "code_lexical": srv.CODE_LEXICAL_MAX_LIMIT,
            "code_ask": code_ask_top_n(),
        }
        for tool, ceiling in reachable.items():
            with self.subTest(tool=tool, clamp=ceiling):
                self.assertLessEqual(
                    ceiling, srv.REFILL_MAX_ROWS_PER_SOURCE,
                    f"{tool} now clamps above the per-source ceiling; the "
                    f"oversized-window fallback is no longer unreachable and "
                    f"SEC-RV1-2 must be reopened",
                )
            for top_n in (-5, 0, 1, max(1, ceiling - 1), ceiling):
                windows = srv._refill_windows(top_n)
                with self.subTest(tool=tool, top_n=top_n):
                    self.assertTrue(windows)
                    self.assertLessEqual(
                        max(windows), srv.REFILL_MAX_ROWS_PER_SOURCE,
                        f"{tool} limit {top_n} produced a window above the ceiling",
                    )
                    self.assertEqual(list(windows), sorted(windows))

    def test_every_merge_seam_keys_on_the_candidate_identity(self):
        """Wave 1wpif, CODE-RV1-1: RED-DEL-2 converted FOUR merge seams to
        `_candidate_merge_key`, but only the hybrid fusion seam was pinned --
        reverting either of the other three individually left the whole suite
        green, so three quarters of the claimed repair could regress unseen.

        Cycle-3 (CODE-RV2-1) replaced a source-text pin with this AST one. The
        reverification lane defeated the text version twice: an extra pair of
        parentheses (`tuple((c.get("lines") or ()))`) slipped past its regex
        while being semantically identical, and two dead helper calls restored
        its expected count. It also scanned 24,183 lines spanning 493
        functions rather than `search_combined`'s body, so the count could be
        satisfied from anywhere in half the file.

        Parsing closes both of those specific holes: the region is now exactly
        the function, and a parenthesised expression parses to the same tree as
        an unparenthesised one.

        Cycle-4 (CODE-RV3-1) narrows this docstring, which previously claimed
        that "spelling tricks cannot hide the legacy key". That claim is FALSE
        and the reverification lane proved it: a helper defined OUTSIDE
        `search_combined`, reading `c["lines"]` by subscript rather than
        `.get("lines")`, was wired into three seams with all eight helper calls
        left in place; the count stayed 8, the legacy list stayed empty, and
        2,025 tests across the affected modules passed while the legacy key
        executed ten times. Other bypasses remain open: `operator.itemgetter`,
        a comprehension key, and star-unpacking with no `tuple` node.

        What this pin actually buys is detection of an ACCIDENTAL revert in
        the two spellings a careless edit produces. The durable instrument is
        behavioural: one fixture per seam, like the hybrid-fusion seam's
        `test_the_legacy_coordinate_key_misattributes_the_same_fixture`, which
        no source-shape trick can satisfy. That work is recorded as a
        follow-up rather than claimed here.
        """
        source = (SCRIPTS_ROOT / "server_impl.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        fn = next(
            (n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and n.name == "search_combined"),
            None,
        )
        self.assertIsNotNone(fn, "search_combined not found in server_impl.py")

        merge_calls = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "_candidate_merge_key"
        ]
        self.assertEqual(
            len(merge_calls), 8,
            "the four merge seams contribute eight _candidate_merge_key calls "
            "inside search_combined; a change here means a seam was added, "
            "removed, or reverted",
        )

        def reaches_lines_get(node):
            """True when the subtree reads the `lines` key off a mapping."""
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "get"
                        and sub.args
                        and isinstance(sub.args[0], ast.Constant)
                        and sub.args[0].value == "lines"):
                    return True
            return False

        legacy = [
            n.lineno for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "tuple"
            and reaches_lines_get(n)
        ]
        self.assertEqual(
            legacy, [],
            "a merge seam reverted to the legacy (path, lines) coordinate key",
        )

    def test_merge_key_falls_back_to_the_canonical_shape_without_an_id(self):
        srv = self.srv
        with_id = {"id": "c1", "path": "src/x.py", "lines": [10, 12]}
        no_id = {"path": "src/x.py", "lines": [10, 12]}
        self.assertEqual(srv._candidate_merge_key(with_id), ("id", "c1"))
        self.assertEqual(srv._candidate_merge_key(no_id), ("loc", "src/x.py", (10, 12)))
        self.assertNotEqual(srv._candidate_merge_key(with_id), srv._candidate_merge_key(no_id))
        # Same id, different coordinates: still one identity.
        self.assertEqual(
            srv._candidate_merge_key({"id": "c1", "path": "src/x.py", "lines": [1, 2]}),
            srv._candidate_merge_key(with_id),
        )


class UnknownLanguageFilterTests(_CandidateFixture):
    """Delivery repair PERF-DEL-4: a language value no stored row carries
    exits before the first substrate query with the honest reason, instead of
    walking four windows on both sources (8 queries / 480 examined rows) and
    reporting ``bounded_ceiling_reached`` ("eligible rows may remain")."""

    def _python_corpus(self):
        return self._build([_chunk(i, "src/py%d.py" % i) for i in range(31)])

    def test_language_outside_the_stored_vocabulary_walks_no_window(self):
        idx = self._python_corpus()
        calls = self._spy_lance(idx)
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_search_response(
                idx, "alpha_handler", language="zzz", limit=5, epoch_state=self.epoch,
            )
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["data"]["results"], [])
        self.assertEqual(calls, [], "no dense window is walked")
        fill = resp["data"]["fill"]
        self.assertEqual((fill["rounds"], fill["windows"]), (0, []))
        self.assertEqual(fill["reason"], self.srv.FILL_REASON_EXHAUSTED)
        self.assertEqual(resp["data"]["retrieval_accounting"]["substrate_queries"], 0)
        codes = self._codes(resp)
        self.assertIn(self.srv.FILL_REASON_EXHAUSTED, codes)
        self.assertNotIn(self.srv.FILL_REASON_CEILING, codes)
        message = next(d["message"] for d in resp["diagnostics"]
                       if d["code"] == self.srv.FILL_REASON_EXHAUSTED)
        self.assertIn("no indexed row carries language", message)
        self.assertIn("zzz", message)

    def test_a_stored_language_still_serves_and_still_refills(self):
        """The guard is data-driven, not name-driven: a non-allowlisted value
        that rows DO carry keeps the bounded refill."""
        chunks = [_chunk(i, "src/py%d.py" % i) for i in range(31)]
        chunks.append(_chunk(31, "api/schema.proto", language="proto", text=LONG_TAIL))
        idx = self._build(chunks)
        calls = self._spy_lance(idx)
        with patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_search_response(
                idx, "alpha_handler", language="proto", limit=5, epoch_state=self.epoch,
            )
        self.assertEqual([r["path"] for r in resp["data"]["results"]], ["api/schema.proto"])
        self.assertEqual([c["top_n"] for c in calls], [30, 60])

    def test_an_unreadable_vocabulary_is_unknown_and_keeps_the_walk(self):
        """None means UNKNOWN, never empty: an unreadable store must not be
        read as proof that a language has no rows."""
        idx = self._python_corpus()
        calls = self._spy_lance(idx)
        iss = self.srv._load_script("index_state_store")
        self.srv._fts_invalidate_serving_state()
        with patch.object(iss, "stored_language_vocabulary", return_value=None), \
                patch.object(idx, "_get_reranker", return_value=None):
            resp = self.srv.code_search_response(
                idx, "alpha_handler", language="zzz", limit=5, epoch_state=self.epoch,
            )
        self.assertEqual(resp["data"]["results"], [])
        # The pre-repair behavior: windows are still walked (this 31-row
        # corpus exhausts both sources at the second window), so the outcome
        # comes from substrate rounds, not from the stored vocabulary.
        self.assertEqual([c["top_n"] for c in calls], [30, 60])
        fill = resp["data"]["fill"]
        self.assertEqual(fill["rounds"], 2)
        self.assertEqual(fill["windows"], [30, 60])
        self.assertEqual(fill["reason"], self.srv.FILL_REASON_EXHAUSTED)

    def test_the_hostile_value_still_never_enters_a_predicate(self):
        idx = self._python_corpus()
        calls = self._spy_lance(idx)
        with patch.object(idx, "_get_reranker", return_value=None):
            self.srv.code_search_response(
                idx, "alpha_handler", language="python' OR 1=1 --", limit=5,
                epoch_state=self.epoch,
            )
        self.assertTrue(all(c["where"] is None for c in calls), calls)

class ColdEpochHybridCostTests(_CandidateFixture):
    """Delivery repair PERF-DEL-3 at the public tools: the FIRST hybrid
    ``code_search`` / ``code_ask`` in a build-state epoch performs no
    ``probe_state_store`` structural quick_check and no coverage scan, while
    ``code_lexical`` — the tool that reports coverage — still gets it."""

    def _corpus(self):
        # The bare token (compound identifiers are indivisible in FTS5).
        code = [_chunk(i, "src/handler%d.py" % i) for i in range(4)]
        docs = [_doc(i, "docs/guide%d.md" % i, "The alpha_handler guide %d" % i) for i in range(4)]
        return self._build(code, docs_chunks=docs)

    def test_first_hybrid_call_in_an_epoch_runs_no_state_probe(self):
        idx = self._corpus()
        iss = self.srv._load_script("index_state_store")
        self.srv._fts_invalidate_serving_state()
        with patch.object(iss, "probe_state_store", wraps=iss.probe_state_store) as probe, \
                patch.object(self.srv, "_state_store_health_summary",
                             wraps=self.srv._state_store_health_summary) as health, \
                patch.object(self.srv, "_chunk_index_coverage",
                             wraps=self.srv._chunk_index_coverage) as coverage, \
                patch.object(idx, "_get_reranker", return_value=None):
            search = self.srv.code_search_response(idx, "alpha_handler", epoch_state=self.epoch)
            self.assertEqual(search["status"], "ok")
            self.assertTrue(search["data"]["results"])
            ask = self.srv.code_ask_response(idx, self.root, "where is alpha_handler",
                                             epoch_state=self.epoch)
            self.assertEqual(ask["data"]["search_mode"], "hybrid")
        probe.assert_not_called()
        health.assert_not_called()
        coverage.assert_not_called()

    def test_code_lexical_on_the_same_cold_epoch_still_reports_coverage(self):
        self._corpus()
        iss = self.srv._load_script("index_state_store")
        self.srv._fts_invalidate_serving_state()
        with patch.object(iss, "probe_state_store", wraps=iss.probe_state_store) as probe:
            resp = self.srv.code_lexical_response(self.root, "alpha_handler", table="code")
        self.assertEqual(resp["status"], "ok")
        self.assertTrue(resp["data"]["results"])
        self.assertIn("code", resp["data"]["coverage"])
        self.assertTrue(resp["data"]["coverage"]["code"]["covered"])
        probe.assert_not_called()


class SQLiteQueryShapeTests(unittest.TestCase):
    """Exact SQLite search replaces all ANN tuning; native behavior is exercised above."""
    def setUp(self):
        self.srv = load_server()

    def test_ann_tuning_calls_and_constants_are_absent(self):
        for name in ("server_impl.py", "indexer.py"):
            tree = ast.parse((SCRIPTS_ROOT / name).read_text(encoding="utf-8"))
            methods = {"nprobes", "minimum_nprobes", "maximum_nprobes", "refine_factor", "ef"}
            self.assertFalse([node for node in ast.walk(tree)
                              if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                              and node.func.attr in methods], name)
        self.assertFalse(hasattr(self.srv, "ANN_REFINE_FACTOR"))

    def test_the_retirement_note_is_not_absorbed_into_the_reranker_chunk(self):
        """Delivery repair RED-DEL-3: the retirement note above sat directly on
        the ``RERANKER_MODEL`` declaration, so the chunker absorbed it into
        that constant's chunk (584 -> 1,274 chars, and the calibration query's
        rank for it moved 1 -> 7). The note now lives above the LanceDB
        constants it talks about, and the RERANKER_MODEL chunk is again the
        declaration plus its own comment."""
        chunker = self.srv._load_script("chunker")
        source = (SCRIPTS_ROOT / "indexer.py").read_text(encoding="utf-8")
        chunks = [c for c in chunker.chunk_file(source, "indexer.py")
                  if "RERANKER_MODEL =" in c.text]
        self.assertEqual(len(chunks), 1, [c.id for c in chunks])
        chunk = chunks[0]
        self.assertIn("cross-encoder reranker", chunk.text)
        self.assertNotIn("LANCEDB_NPROBES", chunk.text)
        self.assertNotIn("LANCEDB_INDEX_THRESHOLD", chunk.text)
        self.assertLess(len(chunk.text), 900, len(chunk.text))
        # Retired Lance tuning has no role in the SQLite implementation.


if __name__ == "__main__":
    unittest.main()

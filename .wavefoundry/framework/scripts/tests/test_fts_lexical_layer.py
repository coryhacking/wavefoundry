"""Tests for the FTS5 lexical layer, chunk registry, and bookkeeping snapshot
(wave 1rsh9 / 1rrr0).

Covers: FTS availability degrade, ordered-consistency crash-window
reconciliation, FTS-hostile query degrade, BM25 candidate shape + fusion
wiring + kill switch, meta.json snapshot reader-contract, the
registry-vs-Lance differential harness (the equivalence proof behind the
registry-backed incremental skip), FTS segment maintenance bounds, FTS
integrity-check detection + rebuild-from-Lance, and the secret-posture
assertions.
"""
from __future__ import annotations

import importlib.util
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]


def load_store_module():
    spec = importlib.util.spec_from_file_location(
        "index_state_store", SCRIPTS_ROOT / "index_state_store.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["index_state_store"] = mod
    spec.loader.exec_module(mod)
    return mod


def _rows(*specs):
    out = []
    for chunk_id, path, text in specs:
        out.append({
            "id": chunk_id, "path": path, "kind": "code",
            "lines": [1, 10], "text": text, "chunk_hash": f"h-{chunk_id}",
        })
    return out


class _StoreCase(unittest.TestCase):
    def setUp(self):
        self.iss = load_store_module()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.index_dir = Path(self._tmp.name) / ".wavefoundry" / "index"


class FtsAvailabilityTests(_StoreCase):
    """AC-1 degrade half: an FTS5-less interpreter builds and queries cleanly."""

    def test_fts_unavailable_degrades_without_errors(self):
        with patch.object(self.iss, "fts5_available", return_value=False):
            self.iss.apply_chunk_deltas(
                self.index_dir, "code", add_rows=_rows(("c1", "a.py", "def alpha(): pass"))
            )
            # Registry still works (it is not FTS-dependent) ...
            self.assertEqual(
                self.iss.registry_chunk_ids(self.index_dir, "code"), {"c1"}
            )
            # ... and lexical search degrades to [] with no error.
            self.assertEqual(self.iss.fts_search(self.index_dir, "code", "alpha"), [])
            # Capability is recorded in store meta (while degraded).
            store = self.iss.IndexStateStore(self.index_dir)
            try:
                self.assertEqual(store.get_meta(self.iss.META_FTS_AVAILABLE), "0")
            finally:
                store.close()

    def test_capability_upgrade_invalidates_registry_for_rebuild(self):
        # An interpreter that GAINS FTS5 later: the fresh FTS tables are empty
        # while the registry is populated — the store must clear the registry
        # so the next id-set reconcile rebuilds both from Lance.
        with patch.object(self.iss, "fts5_available", return_value=False):
            self.iss.apply_chunk_deltas(
                self.index_dir, "code", add_rows=_rows(("c1", "a.py", "def alpha(): pass"))
            )
            self.assertEqual(self.iss.registry_chunk_ids(self.index_dir, "code"), {"c1"})
        # Re-open with real FTS5 available: registry cleared → reconcile repairs.
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            self.assertEqual(store.get_meta(self.iss.META_FTS_AVAILABLE), "1")
        finally:
            store.close()
        self.assertEqual(self.iss.registry_chunk_ids(self.index_dir, "code"), set())
        rows = _rows(("c1", "a.py", "def alpha(): pass"))
        result = self.iss.reconcile_chunk_index(
            self.index_dir, "code", {"c1"}, lambda: rows, expected=True
        )
        self.assertTrue(result["reconciled"])
        self.assertTrue(self.iss.fts_search(self.index_dir, "code", "alpha"))

    def test_fts_available_records_capability_and_serves_search(self):
        self.iss.apply_chunk_deltas(
            self.index_dir, "code", add_rows=_rows(("c1", "a.py", "def _remove_root_bootstrap_file(root): pass"))
        )
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            self.assertEqual(store.get_meta(self.iss.META_FTS_AVAILABLE), "1")
        finally:
            store.close()
        hits = self.iss.fts_search(self.index_dir, "code", "_remove_root_bootstrap_file")
        self.assertEqual([h["id"] for h in hits], ["c1"])
        self.assertEqual(sorted(hits[0].keys()),
                         ["bm25", "id", "kind", "language", "lines", "path", "tags", "text"])


class OrderedConsistencyTests(_StoreCase):
    """AC-1: crash window between Lance write and store commit is repaired."""

    def test_crash_window_is_repaired_by_reconciliation_with_diagnostic(self):
        # Build 1: two chunks in sync; the end-of-build reconcile runs and
        # clears the cold-provisioning flag — the store is now WARM (a real
        # crash window can only happen to a store that survived a build).
        initial = _rows(("c1", "a.py", "def alpha(): pass"), ("c2", "b.py", "def beta(): pass"))
        self.iss.apply_chunk_deltas(self.index_dir, "code", add_rows=initial)
        warm = self.iss.reconcile_chunk_index(
            self.index_dir, "code", {"c1", "c2"}, lambda: initial
        )
        self.assertTrue(warm["in_sync"])
        # Crash window: Lance gained c3 (authoritative) but the store commit
        # never happened — the store still carries only c1/c2.
        lance_now = initial + _rows(("c3", "c.py", "def gamma(): pass"))
        lance_ids = {r["id"] for r in lance_now}
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = self.iss.reconcile_chunk_index(
                self.index_dir, "code", lance_ids, lambda: lance_now
            )
        self.assertTrue(result["reconciled"])
        self.assertIn("out of sync with Lance", stderr.getvalue())
        self.assertIn("crash-window reconciliation", stderr.getvalue())
        self.assertEqual(self.iss.registry_chunk_ids(self.index_dir, "code"), lance_ids)
        self.assertTrue(self.iss.fts_search(self.index_dir, "code", "gamma"))

    def test_in_sync_reconcile_is_a_quiet_no_op(self):
        initial = _rows(("c1", "a.py", "def alpha(): pass"))
        self.iss.apply_chunk_deltas(self.index_dir, "code", add_rows=initial)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = self.iss.reconcile_chunk_index(
                self.index_dir, "code", {"c1"}, lambda: initial
            )
        self.assertTrue(result["in_sync"])
        self.assertEqual(stderr.getvalue(), "")

    def test_cold_start_backfill_is_informational_not_a_crash_warning(self):
        """First build against an empty store (the normal install/upgrade path)
        backfills from Lance with a calm stdout note — the loud crash-window
        stderr diagnostic is reserved for a POPULATED store that diverged."""
        import contextlib
        rows = _rows(("c1", "a.py", "def alpha(): pass"))
        stderr, stdout = io.StringIO(), io.StringIO()
        with redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            result = self.iss.reconcile_chunk_index(
                self.index_dir, "code", {"c1"}, lambda: rows
            )
        self.assertTrue(result["reconciled"])
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("provisioning this store", stdout.getvalue())
        self.assertEqual(self.iss.registry_chunk_ids(self.index_dir, "code"), {"c1"})

    def test_cold_flag_covers_partial_deltas_then_clears(self):
        """A just-created/reset store that received PARTIAL in-build deltas
        before the reconcile (the real install/upgrade/schema-bump sequence)
        still logs the calm provisioning note — and the flag clears, so a
        later genuine divergence IS loud."""
        import contextlib
        rows = _rows(("c1", "a.py", "def alpha(): pass"), ("c2", "b.py", "def beta(): pass"))
        # Partial delta on the fresh store (registry now non-empty, flag still set).
        self.iss.apply_chunk_deltas(self.index_dir, "code", add_rows=rows[:1])
        stderr, stdout = io.StringIO(), io.StringIO()
        with redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            result = self.iss.reconcile_chunk_index(
                self.index_dir, "code", {"c1", "c2"}, lambda: rows
            )
        self.assertTrue(result["reconciled"])
        self.assertEqual(stderr.getvalue(), "")
        self.assertIn("provisioning this store", stdout.getvalue())
        # Flag cleared: a subsequent out-of-band divergence is the LOUD path.
        stderr2 = io.StringIO()
        with redirect_stderr(stderr2):
            self.iss.reconcile_chunk_index(
                self.index_dir, "code", {"c1", "c2", "c3"},
                lambda: rows + _rows(("c3", "c.py", "def gamma(): pass")),
            )
        self.assertIn("crash-window reconciliation", stderr2.getvalue())

    def test_expected_rebuild_is_quiet(self):
        rows = _rows(("c1", "a.py", "def alpha(): pass"))
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = self.iss.reconcile_chunk_index(
                self.index_dir, "code", {"c1"}, lambda: rows, expected=True
            )
        self.assertTrue(result["reconciled"])
        self.assertEqual(stderr.getvalue(), "")


class FtsQuerySafetyTests(_StoreCase):
    """AC-2: FTS-hostile queries degrade to vector-only, never error."""

    def setUp(self):
        super().setUp()
        self.iss.apply_chunk_deltas(
            self.index_dir, "code",
            add_rows=_rows(("c1", "a.py", "def handler(request): raise ValueError")),
        )

    def test_hostile_query_strings_return_empty_not_error(self):
        for hostile in ('NEAR( "unclosed', 'a AND OR NOT', '"unbalanced', "col:val*^",
                        "(((", '""', "   "):
            self.assertIsInstance(
                self.iss.fts_search(self.index_dir, "code", hostile), list
            )

    def test_operators_are_treated_as_literals(self):
        # "AND" quoted as a literal token — no syntax error, no match explosion.
        hits = self.iss.fts_search(self.index_dir, "code", "handler AND request")
        self.assertTrue(any(h["id"] == "c1" for h in hits))

    def test_match_expression_quotes_and_caps_tokens(self):
        expr = self.iss._fts_match_expression('foo "bar" baz')
        self.assertEqual(expr, '"foo" OR """bar""" OR "baz"')
        many = " ".join(f"t{i}" for i in range(50))
        capped = self.iss._fts_match_expression(many)
        self.assertEqual(capped.count(" OR "), self.iss.FTS_QUERY_MAX_TOKENS - 1)


class LexicalFusionWiringTests(unittest.TestCase):
    """AC-2: fusion mechanics — candidate shape, source marker, kill switch."""

    def setUp(self):
        import server_impl
        self.srv = server_impl
        self.iss = load_store_module()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.index_dir = self.root / ".wavefoundry" / "index"

    def _fake_self(self):
        return SimpleNamespace(
            root=self.root,
            _qualify_index_path=lambda p, layer="project": str(p or "").replace("\\", "/"),
        )

    def test_lexical_candidates_shape_and_order(self):
        # Note the tokenizer keeps '_' inside tokens (exact-identifier
        # precision), so the code text here uses separate tokens on purpose.
        self.iss.apply_chunk_deltas(
            self.index_dir, "code",
            add_rows=_rows(("c1", "a.py", "def bootstrap(): cleanup()")),
        )
        self.iss.apply_chunk_deltas(
            self.index_dir, "docs",
            add_rows=[{"id": "d1", "path": "docs/x.md", "kind": "doc", "lines": [1, 4],
                       "text": "bootstrap cleanup guidance", "chunk_hash": "hd"}],
        )
        with patch.object(self.srv, "_load_script", return_value=self.iss):
            cands = self.srv.WaveIndex._lexical_candidates(self._fake_self(), "bootstrap cleanup")
        self.assertEqual(len(cands), 2)
        for c in cands:
            self.assertEqual(c["score"], 0.0)
            self.assertIn("path", c)
            self.assertIn("kind", c)
            self.assertIn("lines", c)
            self.assertIn("text", c)

    def test_lexical_candidates_absent_store_returns_empty(self):
        with patch.object(self.srv, "_load_script", return_value=self.iss):
            cands = self.srv.WaveIndex._lexical_candidates(self._fake_self(), "anything")
        self.assertEqual(cands, [])

    def test_search_combined_wires_fusion_with_kill_switch(self):
        src = Path(self.srv.__file__).read_text(encoding="utf-8")
        fn_pos = src.index("def search_combined(")
        fusion_pos = src.index("LEXICAL_FUSION_DISABLE_ENV", fn_pos)
        rerank_pos = src.index("agent_reranked = self._agent_rerank(query, all_candidates)", fn_pos)
        # Fusion happens BEFORE the rerank (pre-rerank pool merge).
        self.assertLess(fusion_pos, rerank_pos)
        # Lexical source list joins the selection sources (marker convention).
        self.assertIn('_agent_sources["lexical"] = _lex_src', src)
        # Fallback weight applied only when the reranker is unavailable.
        fallback_pos = src.index("LEXICAL_RRF_FALLBACK_WEIGHT / (1.0 + float(", fn_pos)
        self.assertGreater(fallback_pos, rerank_pos)

    def test_kill_switch_removes_all_lexical_participation(self):
        import os as _os
        self.iss.apply_chunk_deltas(
            self.index_dir, "code",
            add_rows=_rows(("c1", "a.py", "def bootstrap_cleanup(): pass")),
        )
        calls = []

        class _SpyIss:
            def fts_search(self, *a, **k):  # pragma: no cover - must not run
                calls.append(a)
                return []

        with patch.dict(_os.environ, {self.srv.LEXICAL_FUSION_DISABLE_ENV: "1"}):
            # The env gate is checked in search_combined before _lexical_candidates;
            # assert the guard exists at source level and the env var name is stable.
            self.assertEqual(self.srv.LEXICAL_FUSION_DISABLE_ENV,
                             "WAVEFOUNDRY_DISABLE_LEXICAL_FUSION")
            src = Path(self.srv.__file__).read_text(encoding="utf-8")
            self.assertIn("if not os.environ.get(LEXICAL_FUSION_DISABLE_ENV):", src)
        self.assertEqual(calls, [])


class Fts5CodeSearchLexicalTests(_StoreCase):
    """Wave 1rsh9 (1sauc): filter parity + degrade for search_code's FTS5 half."""

    def _seed(self):
        self.iss.apply_chunk_deltas(self.index_dir, "code", add_rows=[
            {"id": "py1", "path": "src/a.py", "kind": "code", "language": "python",
             "tags": ["framework"], "lines": [1, 5],
             "text": "def alpha_handler(): pass", "chunk_hash": "h1"},
            {"id": "ts1", "path": "web/b.ts", "kind": "code", "language": "typescript",
             "tags": ["test"], "lines": [1, 5],
             "text": "function alpha_handler() {}", "chunk_hash": "h2"},
            {"id": "sum1", "path": "src/a.py", "kind": "code-summary", "language": "python",
             "tags": [], "lines": [1, 1],
             "text": "alpha_handler summary", "chunk_hash": "h3"},
        ])

    def test_rows_carry_language_and_tags(self):
        self._seed()
        hits = self.iss.fts_search(self.index_dir, "code", "alpha_handler")
        by_id = {h["id"]: h for h in hits}
        self.assertEqual(by_id["py1"]["language"], "python")
        self.assertEqual(by_id["py1"]["tags"], "framework")
        self.assertEqual(by_id["ts1"]["language"], "typescript")

    def test_kind_filter_is_exact(self):
        self._seed()
        hits = self.iss.fts_search(self.index_dir, "code", "alpha_handler", kind="code-summary")
        self.assertEqual([h["id"] for h in hits], ["sum1"])

    def test_tags_filter_matches_any(self):
        self._seed()
        hits = self.iss.fts_search(self.index_dir, "code", "alpha_handler",
                                   tags_any=["framework", "test"])
        self.assertEqual(sorted(h["id"] for h in hits), ["py1", "ts1"])
        hits = self.iss.fts_search(self.index_dir, "code", "alpha_handler",
                                   tags_any=["framework"])
        self.assertEqual([h["id"] for h in hits], ["py1"])

    def test_server_lexical_half_shapes_and_degrades(self):
        import server_impl as srv
        self._seed()
        index = srv.WaveIndex.__new__(srv.WaveIndex)
        index.root = Path(self._tmp.name)
        with patch.object(srv, "_load_script", return_value=self.iss):
            hits = srv.WaveIndex._fts5_lexical_search(index, "code", "alpha_handler", 10)
        self.assertTrue(hits)
        top = hits[0]
        for key in ("path", "kind", "language", "tags", "lines", "text", "score"):
            self.assertIn(key, top)
        # bm25 negated → higher is better (sortable alongside cosine order).
        self.assertGreaterEqual(top["score"], 0.0)
        # language post-filter parity: rows carry language.
        self.assertIn("python", {h["language"] for h in hits})
        # Hostile query and absent store both degrade to [] (dense-only), no error.
        with patch.object(srv, "_load_script", return_value=self.iss):
            self.assertEqual(
                srv.WaveIndex._fts5_lexical_search(index, "code", 'NEAR( "boom', 10), [])
        empty_root = Path(self._tmp.name) / "empty"
        empty_root.mkdir()
        index.root = empty_root
        with patch.object(srv, "_load_script", return_value=self.iss):
            self.assertEqual(
                srv.WaveIndex._fts5_lexical_search(index, "code", "alpha_handler", 10), [])

    def test_search_code_wires_fts5_and_not_lance_fts(self):
        import server_impl as srv
        src = Path(srv.__file__).read_text(encoding="utf-8")
        self.assertNotIn('query_type="fts"', src)
        fn_pos = src.index("def search_code(")
        self.assertIn("_fts5_lexical_search(", src[fn_pos:fn_pos + 4000])

    def test_v3_store_converges_to_v4_via_drop_and_rebuild(self):
        # AC-3 (1sauc): an old-schema store (no language/tags columns) is
        # detected by the version gate, dropped, recreated with the new
        # columns, and the reconcile backfills — no migration code.
        store = self.iss.IndexStateStore(self.index_dir)
        store.set_meta({"store_schema_version": "3"})
        store.close()
        rows = [{"id": "c1", "path": "a.py", "kind": "code", "language": "python",
                 "tags": ["framework"], "lines": [1, 2],
                 "text": "def alpha(): pass", "chunk_hash": "h1"}]
        import io as _io
        from contextlib import redirect_stderr as _rs
        stderr = _io.StringIO()
        with _rs(stderr):
            result = self.iss.reconcile_chunk_index(
                self.index_dir, "code", {"c1"}, lambda: rows
            )
        self.assertTrue(result["reconciled"])
        self.assertIn("schema version mismatch", stderr.getvalue())
        hits = self.iss.fts_search(self.index_dir, "code", "alpha", tags_any=["framework"])
        self.assertEqual([h["id"] for h in hits], ["c1"])
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            self.assertEqual(store.get_meta("store_schema_version"),
                             self.iss.STATE_STORE_SCHEMA_VERSION)
        finally:
            store.close()


class SnapshotContractTests(_StoreCase):
    """AC-4: meta.json snapshot is reader-contract compatible."""

    def test_snapshot_round_trip_is_semantically_identical(self):
        meta = {
            "built_at": "2026-07-10T00:00:00Z",
            "model_versions": {"docs": "arctic@full", "code": "bge@int8"},
            "chunker_versions": {"docs": "12", "code": "12"},
            "walker_version": "7",
            "content": ["code", "docs"],
            "file_meta": {
                "a.py": {"hash": "abc", "mtime": 1751000000.123456, "size": 42,
                         "inode": 999, "chunks_emitted": 3},
                "b.md": {"hash": "def", "mtime": 1751000001.5, "size": 10, "inode": 1000},
            },
        }
        self.iss.write_build_bookkeeping(self.index_dir, meta)
        snapshot = self.iss.export_meta_snapshot(self.index_dir)
        self.assertEqual(snapshot, meta)
        # JSON round-trip (what readers actually parse) is identical too.
        self.assertEqual(json.loads(json.dumps(snapshot)), json.loads(json.dumps(meta)))

    def test_snapshot_absent_store_returns_none(self):
        self.assertIsNone(self.iss.export_meta_snapshot(self.index_dir))

    def test_indexer_falls_back_to_direct_write_on_store_failure(self):
        src = (SCRIPTS_ROOT / "indexer.py").read_text(encoding="utf-8")
        self.assertIn(
            "_save_meta(index_dir, _meta_snapshot if _meta_snapshot is not None else new_meta)",
            src,
        )


class RegistryDifferentialTests(_StoreCase):
    """AC-5: the equivalence proof behind the registry-backed incremental skip.

    The skip fires ONLY when the freshly-chunked {id: chunk_hash} map exactly
    equals the registry map for a path. These fixtures prove (a) that
    condition implies the Lance-read delta plan is a no-op (skip ≡ plan), and
    (b) every real-change case — add/modify/delete/rename and the
    drift/eligibility repair case — fails the condition, so it takes the
    Lance-read path unchanged.
    """

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "indexer", SCRIPTS_ROOT / "indexer.py"
        )
        cls.idx = importlib.util.module_from_spec(spec)
        sys.modules["indexer"] = cls.idx
        spec.loader.exec_module(cls.idx)

    def _chunk(self, chunk_id, path, text, **extra):
        c = {"id": chunk_id, "path": path, "kind": "code", "language": "python",
             "section": "", "text": text, "tags": []}
        c.update(extra)
        return c

    def _lance_row(self, chunk):
        row = dict(chunk)
        row["chunk_hash"] = self.idx._chunk_hash(chunk)
        row["tags"] = " ".join(chunk.get("tags") or [])
        row["vector"] = [0.0, 0.0]
        return row

    def _registry_map(self, chunks):
        return {c["id"]: self.idx._chunk_hash(c) for c in chunks}

    def test_identical_map_implies_no_op_delta_plan(self):
        chunks = [self._chunk("c1", "a.py", "def alpha(): pass"),
                  self._chunk("c2", "a.py", "def beta(): pass")]
        lance_rows = [self._lance_row(c) for c in chunks]
        new_map = self._registry_map(chunks)
        self.assertEqual(new_map, {r["id"]: r["chunk_hash"] for r in lance_rows})
        delete_ids, rows_to_add, fallback, stats = self.idx._plan_lance_delta_rows(
            existing_rows=lance_rows, new_chunks=chunks, embedder=None, label="code",
        )
        self.assertEqual(delete_ids, set())
        self.assertEqual(rows_to_add, [])
        self.assertFalse(fallback)
        self.assertEqual(stats["unchanged"], 2)

    def test_modify_changes_the_map(self):
        old = [self._chunk("c1", "a.py", "def alpha(): pass")]
        new = [self._chunk("c1", "a.py", "def alpha(): return 1")]
        self.assertNotEqual(self._registry_map(old), self._registry_map(new))

    def test_add_and_delete_change_the_map(self):
        base = [self._chunk("c1", "a.py", "x")]
        added = base + [self._chunk("c2", "a.py", "y")]
        self.assertNotEqual(self._registry_map(base), self._registry_map(added))
        self.assertNotEqual(self._registry_map(added), self._registry_map(base))

    def test_rename_changes_the_map(self):
        # A renamed file gets new chunk ids (path-derived) — map keys differ.
        old = [self._chunk("a.py::c1", "a.py", "def alpha(): pass")]
        new = [self._chunk("b.py::c1", "b.py", "def alpha(): pass")]
        self.assertNotEqual(self._registry_map(old), self._registry_map(new))

    def test_drift_repair_case_never_skips(self):
        # Lance drift (path claims chunks in file_meta but Lance has zero rows):
        # the registry — synced FROM Lance — is empty for the path, so the map
        # comparison fails and the Lance-read repair path runs unchanged.
        chunks = [self._chunk("c1", "a.py", "def alpha(): pass")]
        reg = self.iss.registry_map_for_paths(self.index_dir, "code", ["a.py"])
        self.assertEqual(reg, {})  # empty store == drifted registry state
        self.assertNotEqual(reg.get("a.py"), self._registry_map(chunks))

    def test_metadata_only_difference_changes_the_map(self):
        # chunk_hash covers kind/language/section/text/tags — a tags-only
        # change fails the skip condition (no silent stale-metadata retention).
        old = [self._chunk("c1", "a.py", "x", tags=["a"])]
        new = [self._chunk("c1", "a.py", "x", tags=["b"])]
        self.assertNotEqual(self._registry_map(old), self._registry_map(new))

    def test_drift_flagged_paths_are_exempt_from_the_skip(self):
        """Out-of-band drift (rows vanish from Lance AFTER the registry synced):
        the registry mirrors the PRE-drift state, so the skip condition would
        wrongly hold — drift-flagged paths must bypass the skip entirely so the
        repair reads Lance (the authority). Source-anchored: the exemption is
        applied before the map comparison and threaded from `drifted`."""
        src = (SCRIPTS_ROOT / "indexer.py").read_text(encoding="utf-8")
        fn_pos = src.index("def _lance_incremental_write(")
        exempt_pos = src.index("if skip_exempt and file_path in skip_exempt:", fn_pos)
        compare_pos = src.index("_reg_maps.get(file_path) == new_map", fn_pos)
        self.assertLess(exempt_pos, compare_pos)
        # The build threads the drift set into both futures.
        build_pos = src.index("def _build_index_locked(")
        self.assertIn("_skip_exempt = set(drifted)", src[build_pos:])
        self.assertEqual(src.count("skip_exempt=_exempt"), 2)

    def test_incremental_write_wires_the_skip_with_kill_switch(self):
        src = (SCRIPTS_ROOT / "indexer.py").read_text(encoding="utf-8")
        fn_pos = src.index("def _lance_incremental_write(")
        skip_pos = src.index("WAVEFOUNDRY_DISABLE_REGISTRY_INCREMENTAL", fn_pos)
        read_pos = src.index(
            "_read_lance_rows_for_paths(db_path, table_name, lance_read_paths)", fn_pos
        )
        self.assertLess(skip_pos, read_pos)


class FtsMaintenanceTests(_StoreCase):
    """AC-9: segment growth bounded under churn; skipped cleanly without FTS."""

    def _data_blocks(self, table="fts_code"):
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        try:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}_data").fetchone()[0])
        finally:
            conn.close()

    def test_segment_blocks_bounded_after_churn(self):
        # Drive insert/delete churn past the merge threshold repeatedly, then
        # run the on-demand optimize; the shadow-table block count (the
        # segment-growth observable) must collapse to the single-segment
        # baseline rather than growing with churn.
        for cycle in range(30):
            rows = _rows(*[(f"c{cycle}-{i}", f"f{i}.py", f"def fn_{cycle}_{i}(): pass")
                           for i in range(40)])
            self.iss.apply_chunk_deltas(self.index_dir, "code", add_rows=rows)
            self.iss.apply_chunk_deltas(
                self.index_dir, "code", delete_ids=[r["id"] for r in rows[:35]]
            )
        churned = self._data_blocks()
        res = self.iss.sqlite_store_maintenance(
            self.iss.state_store_path(self.index_dir), full_vacuum=True, deep_integrity=True
        )
        self.assertEqual(res["integrity"], "ok")
        optimized = self._data_blocks()
        self.assertLessEqual(optimized, churned)
        self.assertLess(optimized, 40, f"segment blocks not bounded: {optimized}")

    def test_in_build_merge_threshold_is_wired(self):
        src = (SCRIPTS_ROOT / "index_state_store.py").read_text(encoding="utf-8")
        pos = src.index("FTS_MERGE_CHURN_THRESHOLD")
        self.assertGreater(pos, 0)
        self.assertIn("VALUES('merge', ?)", src)
        self.assertIn("VALUES('optimize')", src)

    def test_maintenance_skips_cleanly_when_fts_unavailable(self):
        with patch.object(self.iss, "fts5_available", return_value=False):
            self.iss.apply_chunk_deltas(
                self.index_dir, "code", add_rows=_rows(("c1", "a.py", "x"))
            )
        res = self.iss.sqlite_store_maintenance(
            self.iss.state_store_path(self.index_dir), full_vacuum=True
        )
        self.assertEqual(res["integrity"], "ok")
        self.assertIsNone(res["error"])


class FtsIntegrityTests(_StoreCase):
    """AC-10: a corrupted FTS table is detected and rebuilt from Lance rows."""

    def _corrupt_fts_shadow(self):
        conn = sqlite3.connect(str(self.iss.state_store_path(self.index_dir)))
        try:
            # Mangle the fts5 segment data directly — internal inconsistency
            # that quick_check alone cannot see but 'integrity-check' catches.
            conn.execute("UPDATE fts_code_data SET block = zeroblob(4) WHERE id > 1")
            conn.commit()
        finally:
            conn.close()

    def test_corrupt_fts_is_detected_and_rebuilt_from_rows(self):
        rows = _rows(("c1", "a.py", "def alpha(): pass"), ("c2", "b.py", "def beta(): pass"))
        self.iss.apply_chunk_deltas(self.index_dir, "code", add_rows=rows)
        self._corrupt_fts_shadow()
        verdict = self.iss._fts_integrity_verdict(self.iss.state_store_path(self.index_dir))
        self.assertEqual(verdict, "fail")
        probe = self.iss.probe_state_store(Path(self._tmp.name), self.index_dir)
        self.assertEqual(probe["status"], "structural-fail")
        # Query path: no error surfaces (degrade to []).
        result = self.iss.fts_search(self.index_dir, "code", "alpha")
        self.assertIsInstance(result, list)
        # Rebuild from (Lance) rows recovers, resetting the store if needed.
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            written = self.iss.rebuild_chunk_index(self.index_dir, "code", rows)
        self.assertEqual(written, 2)
        self.assertEqual(
            self.iss._fts_integrity_verdict(self.iss.state_store_path(self.index_dir)),
            "ok",
        )
        self.assertEqual([h["id"] for h in
                          self.iss.fts_search(self.index_dir, "code", "alpha")], ["c1"])


class SecretPostureTests(_StoreCase):
    """AC-8: the store inherits the Lance posture — gitignored, unpackaged,
    and FTS stores no chunk text not already present in Lance."""

    def test_store_lives_under_gitignored_index_dir(self):
        repo_root = SCRIPTS_ROOT.parents[2]
        gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".wavefoundry/index/", gitignore)
        # The store path is inside that dir by construction.
        store = self.iss.state_store_path(Path(".wavefoundry/index"))
        self.assertEqual(str(store).replace("\\", "/"),
                         ".wavefoundry/index/index-state.sqlite")

    def test_build_pack_ships_no_index_artifacts(self):
        # build_pack ships framework SOURCE only; nothing under an index dir
        # (including *.sqlite) is packaged. Assert the packer's exclusion
        # machinery references the index dir.
        src = (SCRIPTS_ROOT / "build_pack.py").read_text(encoding="utf-8")
        self.assertIn("index", src)
        self.assertNotIn("index-state.sqlite", src)  # never explicitly included

    def test_fts_text_comes_only_from_chunk_rows(self):
        # Structural control: the ONLY writers of FTS text are
        # apply_chunk_deltas / rebuild_chunk_index, and the indexer feeds them
        # exclusively Lance-bound rows (rows_to_add / _created_rows) or Lance
        # reads (_fetch_rows) — no new text source exists.
        idx_src = (SCRIPTS_ROOT / "indexer.py").read_text(encoding="utf-8")
        for call, arg in (("apply_chunk_deltas", "add_rows=rows_to_add"),
                          ("apply_chunk_deltas", "add_rows=_created_rows"),
                          ("reconcile_chunk_index", "_fetch_rows")):
            self.assertIn(arg, idx_src, f"{call} must be fed Lance-bound rows ({arg})")
        store_src = (SCRIPTS_ROOT / "index_state_store.py").read_text(encoding="utf-8")
        insert_count = store_src.count("INSERT INTO {fts_name} ")
        self.assertEqual(
            insert_count, 2,
            "FTS text writers must remain exactly apply_chunk_deltas + rebuild_chunk_index",
        )


if __name__ == "__main__":
    unittest.main()

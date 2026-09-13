"""FTS reconciliation honesty and probed public serving (wave 1wpif / 1wpag).

Covers the keyed FTS payload digest (publication-boundary computation,
O(delta) maintenance, never re-blessing prior corruption), the reconcile
in-sync gate (liveness + row/shadow parity + digest before the early
return, healing through the ordinary rebuild, the per-epoch heal marker),
the zero-change build probe, and the server's shared probed-serving
chokepoint: typed ``query_failed`` for the lexical-only tool, typed
``lexical_undercoverage`` for the hybrid tools, healthy-zero controls,
bounded path-sanitized detail strings, at-most-once heal scheduling, the
same-epoch re-damage suppression, the health surface, and the AC-8 warmed
read measured through a sqlite trace hook plus store-seam spies.

Every fault is injected into a REAL store built by the canonical producers
(``reconcile_chunk_index`` / ``apply_chunk_deltas`` + a finalized build
epoch) with direct sqlite mutations; no detector-shaped synthetics.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from server_tools_support import _make_repo, load_server

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]


def _load_store_module(name: str = "index_state_store"):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_ROOT / "index_state_store.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _code_rows() -> list[dict]:
    return [
        {"id": "c1", "path": "src/alpha.py", "kind": "code", "language": "python",
         "lines": [1, 5], "section": "", "tags": "", "chunk_hash": "h1",
         "text": "def alpha_handler(): pass"},
        {"id": "c2", "path": "src/beta.ts", "kind": "code", "language": "typescript",
         "lines": [1, 5], "section": "", "tags": "", "chunk_hash": "h2",
         "text": "function alpha_handler() {}"},
        {"id": "c3", "path": "src/alpha.py", "kind": "code", "language": "python",
         "lines": [6, 9], "section": "", "tags": "", "chunk_hash": "h3",
         "text": "def alpha_handler_two(): pass"},
    ]


def _docs_rows() -> list[dict]:
    return [
        {"id": "d1", "path": "docs/guide.md", "kind": "doc", "language": "",
         "lines": [1, 4], "section": "Intro", "tags": "reference", "chunk_hash": "h4",
         "text": "alpha_handler guide entry"},
        {"id": "d2", "path": "docs/other.md", "kind": "doc", "language": "",
         "lines": [1, 4], "section": "Other", "tags": "journal", "chunk_hash": "h5",
         "text": "alpha_handler journal entry"},
    ]


@contextlib.contextmanager
def _quiet():
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        yield


class _StoreFixture(unittest.TestCase):
    """A real store published by the canonical producer (reconcile from
    Lance-shaped rows), one temp root per test."""

    def setUp(self):
        self.iss = _load_store_module()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = _make_repo(Path(self._tmp.name))
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True)
        self.code_rows = _code_rows()
        self.docs_rows = _docs_rows()
        with _quiet():
            self.iss.reconcile_chunk_index(
                self.index_dir, "code", {r["id"] for r in self.code_rows}, lambda: self.code_rows)
            self.iss.reconcile_chunk_index(
                self.index_dir, "docs", {r["id"] for r in self.docs_rows}, lambda: self.docs_rows)

    def _store_path(self) -> Path:
        return self.iss.state_store_path(self.index_dir)

    def _sql(self, *statements: str) -> None:
        conn = self.iss.sqlite_runtime.connect(self._store_path())
        try:
            with conn:
                for stmt in statements:
                    conn.execute(stmt)
        finally:
            conn.close()

    def _reconcile(self, table: str = "code"):
        rows = self.code_rows if table == "code" else self.docs_rows
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            result = self.iss.reconcile_chunk_index(
                self.index_dir, table, {r["id"] for r in rows}, lambda: rows)
        return result, err.getvalue(), out.getvalue()

    def _publish_epoch(self, scope: str = "fixture") -> str:
        import index_compatibility
        self.iss.write_build_bookkeeping(self.index_dir, {
            "content": ["docs", "code"],
            "walker_version": str(index_compatibility.SUPPORTED["walker_version"]),
            "chunker_versions": {layer: str(index_compatibility.SUPPORTED["chunker_version"])
                                 for layer in ("docs", "code")},
            "model_versions": {layer: "fixture-model" for layer in ("docs", "code")},
        })
        attempt = self.iss.begin_build_epoch(self.index_dir, scope)
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, attempt))
        return attempt

    def _digests(self, table: str = "code") -> tuple:
        conn = self.iss.open_read_only(self.index_dir)
        try:
            recorded = self.iss._fts_recorded_digest(conn, table)
            current = self.iss._fts_table_digest(conn, self.iss.FTS_TABLES[table])
        finally:
            conn.close()
        return recorded, current


class FtsPayloadDigestTests(_StoreFixture):
    """Req 1 / amendment A3: the keyed payload digest contract."""

    def test_readonly_native_posting_probe_checks_unicode_and_token_positions(self):
        row = {"id": "unicode", "path": "unicode.md", "text": "Café naïve Ångström 東京 alpha_beta alpha beta alpha"}
        self.iss.apply_chunk_deltas(self.index_dir, "docs", add_rows=[row])
        real_open = self.iss.open_read_only
        opened = []
        def readonly(index_dir):
            conn = real_open(index_dir)
            if conn is not None:
                opened.append(conn.readonly("main"))
            return conn
        before = self._store_path().read_bytes()
        with patch.object(self.iss, "open_read_only", side_effect=readonly):
            self.assertTrue(self.iss.fts_state_verdict(self.index_dir, "docs")["ok"])
        self.assertTrue(opened and all(opened))
        self.assertEqual(self._store_path().read_bytes(), before)
        # Same token multiset and count, different positions in the inverted
        # index; external-content SELECT still returns the original text.
        self._sql("UPDATE fts_docs SET text='Café naïve Ångström 東京 alpha_beta beta alpha alpha' WHERE chunk_id='unicode'")
        verdict = self.iss.fts_state_verdict(self.index_dir, "docs")
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["reason"], "digest_mismatch")

    def test_rebuild_records_digest_equal_to_full_recompute(self):
        recorded, current = self._digests()
        self.assertIsNotNone(recorded)
        self.assertEqual(recorded, current)
        verdict = self.iss.fts_state_verdict(self.index_dir, "code")
        self.assertTrue(verdict["ok"], verdict)
        self.assertEqual(verdict["digest"], "ok")
        self.assertTrue(verdict["live"])
        self.assertEqual((verdict["fts_rows"], verdict["registry_rows"]), (3, 3))

    def test_row_digest_is_order_independent_and_coercion_stable(self):
        rows = self.code_rows
        forward = self.iss._fts_digest_of_rows(rows)
        backward = self.iss._fts_digest_of_rows(list(reversed(rows)))
        self.assertEqual(forward, backward)
        # A sqlite-shaped row (strings for line bounds, None for an empty
        # field) digests identically to the dict the writer bound.
        from_dict = self.iss._fts_payload_row_digest(*self.iss._fts_row_tuple(rows[0]))
        from_row = self.iss._fts_payload_row_digest(
            "c1", "src/alpha.py", "code", "python", None, "1", "5", "def alpha_handler(): pass")
        self.assertEqual(from_dict, from_row)
        # Any served field participates: a text change flips the digest.
        changed = dict(rows[0], text="def alpha_handler(): return 1")
        self.assertNotEqual(from_dict, self.iss._fts_payload_row_digest(*self.iss._fts_row_tuple(changed)))

    def test_incremental_delta_maintenance_matches_full_recompute(self):
        replaced = dict(self.code_rows[0], text="def alpha_handler(): return 42", chunk_hash="h1b")
        added = {"id": "c4", "path": "src/gamma.py", "kind": "code", "language": "python",
                 "lines": [1, 3], "section": "", "tags": "", "chunk_hash": "h9",
                 "text": "def gamma_handler(): pass"}
        # Replace-by-id, delete-by-id, delete-by-path, and a plain add in one delta.
        self.iss.apply_chunk_deltas(
            self.index_dir, "code",
            delete_ids=["c3"], delete_paths=["src/beta.ts"], add_rows=[replaced, added],
        )
        recorded, current = self._digests()
        self.assertEqual(recorded, current)
        verdict = self.iss.fts_state_verdict(self.index_dir, "code")
        self.assertTrue(verdict["ok"], verdict)
        self.assertEqual(verdict["digest"], "ok")
        self.assertEqual([h["id"] for h in self.iss.fts_search(self.index_dir, "code", "gamma_handler")], ["c4"])
        # The large-delta branch (one linear scan filtered in Python) is exact too.
        bulk = [
            {"id": f"b{i}", "path": f"bulk/{i % 7}.py", "kind": "code", "language": "python",
             "lines": [1, 2], "section": "", "tags": "", "chunk_hash": f"hb{i}",
             "text": f"def bulk_fn_{i}(): pass"}
            for i in range(self.iss._FTS_DIGEST_SELECT_BATCH + 50)
        ]
        self.iss.apply_chunk_deltas(self.index_dir, "code", add_rows=bulk)
        self.iss.apply_chunk_deltas(
            self.index_dir, "code",
            delete_ids=[r["id"] for r in bulk[: self.iss._FTS_DIGEST_SELECT_BATCH]],
            delete_paths=["bulk/3.py"],
        )
        recorded, current = self._digests()
        self.assertEqual(recorded, current)

    def test_delta_never_reblesses_prior_corruption(self):
        # Equal-count substitution BEFORE a later incremental delta: the XOR
        # maintenance removes the corrupt payload's digest, not the published
        # one, so the mismatch survives the delta (a full recompute at the
        # delta seam would have blessed the corruption).
        self._sql("UPDATE fts_code SET text = 'def tampered_symbol(): pass' WHERE chunk_id = 'c1'")
        self.iss.apply_chunk_deltas(
            self.index_dir, "code",
            add_rows=[{"id": "c9", "path": "src/nine.py", "kind": "code", "language": "python",
                       "lines": [1, 2], "section": "", "tags": "", "chunk_hash": "h99",
                       "text": "def nine_handler(): pass"}],
        )
        verdict = self.iss.fts_state_verdict(self.index_dir, "code")
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["reason"], "digest_mismatch")

    def test_unrecorded_digest_bootstraps_at_in_sync_reconcile(self):
        # A store fed only by deltas (pre-digest shape) is honest, not damaged,
        # and the lock owner records the digest at the next in-sync reconcile.
        other = self.root / ".wavefoundry" / "index2"
        rows = self.code_rows
        self.iss.apply_chunk_deltas(other, "code", add_rows=rows)
        store = self.iss.IndexStateStore(other)
        store.delete_meta([self.iss.META_FTS_PAYLOAD_DIGEST_PREFIX + "code"])
        store.close()
        verdict = self.iss.fts_state_verdict(other, "code")
        self.assertTrue(verdict["ok"], verdict)
        self.assertEqual(verdict["digest"], "unrecorded")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            result = self.iss.reconcile_chunk_index(other, "code", {r["id"] for r in rows}, lambda: rows)
        self.assertTrue(result["in_sync"])
        self.assertEqual(result["fts_verified"], "ok")
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(self.iss.fts_state_verdict(other, "code")["digest"], "ok")
        self.assertTrue(self.iss.fts_recorded_integrity(other, "code")["digest_recorded"])

    def test_unqualified_runtime_cannot_open_or_rewrite_canonical(self):
        with patch.object(self.iss.sqlite_runtime, "connect", side_effect=self.iss.sqlite_runtime.RuntimeUnavailable("unqualified runtime")):
            with self.assertRaises(self.iss.sqlite_runtime.RuntimeUnavailable):
                self.iss.apply_chunk_deltas(self.index_dir, "code", add_rows=self.code_rows)
        self.assertTrue(self.iss.fts_state_verdict(self.index_dir, "code")["ok"])

    def test_strict_fetch_raises_on_table_damage_default_swallows(self):
        self._sql("DROP TABLE fts_code")
        self.assertEqual(self.iss.fts_search(self.index_dir, "code", "alpha_handler"), [])
        with self.assertRaises(self.iss.sqlite_runtime.Error):
            self.iss.fts_search(self.index_dir, "code", "alpha_handler", strict=True)
        # Query-shaped FTS5 errors stay a zero-hit even in strict mode.
        with patch.object(self.iss, "_fts_match_expression", return_value='NEAR("unclosed'):
            self.assertEqual(self.iss.fts_search(self.index_dir, "docs", "x", strict=True), [])


class ReconcileHonestyTests(_StoreFixture):
    """AC-1 / AC-2 / AC-5 at the reconcile boundary: every fault in the
    battery is detected by the ORDINARY reconcile (registry ids in sync) and
    healed from the authoritative rows, with the heal marker written."""

    def _assert_healed(self, result: dict, err: str, reason: str) -> None:
        self.assertTrue(result["reconciled"], result)
        self.assertEqual(result.get("fts_repaired"), reason, result)
        self.assertIn("FTS heal", err)
        self.assertIn(reason, err)
        after = self.iss.fts_state_verdict(self.index_dir, "code")
        self.assertTrue(after["ok"], after)
        self.assertEqual(after["digest"], "ok")
        self.assertEqual([h["id"] for h in self.iss.fts_search(self.index_dir, "code", "alpha_handler_two")], ["c3"])

    def test_dropped_table_is_detected_and_rebuilt(self):
        self._sql("DROP TABLE fts_code")
        result, err, _ = self._reconcile()
        self._assert_healed(result, err, "probe_failed")

    def test_emptied_table_beside_registry_is_detected_and_rebuilt(self):
        self._sql("DELETE FROM fts_code")
        result, err, _ = self._reconcile()
        self._assert_healed(result, err, "probe_failed")

    def test_truncated_table_is_detected_and_rebuilt(self):
        self._sql("DELETE FROM fts_code WHERE rowid IN (SELECT rowid FROM fts_code LIMIT 1)")
        result, err, _ = self._reconcile()
        self._assert_healed(result, err, "probe_failed")

    def test_corrupt_shadow_row_is_detected_and_rebuilt(self):
        self._sql("DELETE FROM fts_code_docsize WHERE rowid IN (SELECT rowid FROM fts_code_docsize LIMIT 1)")
        result, err, _ = self._reconcile()
        self._assert_healed(result, err, "probe_failed")

    def test_equal_count_substitution_is_detected_and_rebuilt(self):
        self._sql("UPDATE fts_code SET text = 'def tampered_symbol(): pass' WHERE chunk_id = 'c1'")
        # Every count is preserved: the pre-1wpag probe reads this as live.
        self.assertTrue(self.iss.fts_probe(self.index_dir, "code"))
        self.assertEqual([h["id"] for h in self.iss.fts_search(self.index_dir, "code", "tampered_symbol")], ["c1"])
        result, err, _ = self._reconcile()
        self._assert_healed(result, err, "digest_mismatch")
        self.assertEqual(self.iss.fts_search(self.index_dir, "code", "tampered_symbol"), [])
        self.assertIn("c1", [h["id"] for h in self.iss.fts_search(self.index_dir, "code", "alpha_handler")])

    def test_fts_ahead_orphan_row_is_detected_and_rebuilt(self):
        self._sql(
            "INSERT INTO fts_code (chunk_id, path, kind, language, tags, start_line, end_line, text) "
            "VALUES ('orphan', 'src/orphan.py', 'code', 'python', '', 1, 2, 'def orphan_symbol(): pass')"
        )
        before = self.iss.fts_state_verdict(self.index_dir, "code")
        self.assertEqual((before["fts_rows"], before["registry_rows"]), (3, 3))
        result, err, _ = self._reconcile()
        self._assert_healed(result, err, "probe_failed")
        self.assertEqual(self.iss.fts_search(self.index_dir, "code", "orphan_symbol"), [])

    def test_healthy_control_is_quiet_and_not_rebuilt(self):
        result, err, out = self._reconcile()
        self.assertTrue(result["in_sync"])
        self.assertFalse(result["reconciled"])
        self.assertEqual(result["fts_verified"], "ok")
        self.assertNotIn("fts_repaired", result)
        self.assertEqual((err, out), ("", ""))

    def test_cold_open_control_is_provisioning_not_damage(self):
        other = self.root / ".wavefoundry" / "index-cold"
        rows = self.code_rows
        err, out = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
            result = self.iss.reconcile_chunk_index(other, "code", {r["id"] for r in rows}, lambda: rows)
        self.assertTrue(result["reconciled"])
        self.assertNotIn("fts_repaired", result)
        self.assertIn("provisioning this store", out.getvalue())
        self.assertEqual(err.getvalue(), "")
        self.assertTrue(self.iss.fts_state_verdict(other, "code")["ok"])

    def test_heal_marker_names_the_healing_attempt(self):
        attempt = self._publish_epoch()
        self.assertIsNone(self.iss.fts_recorded_integrity(self.index_dir, "code")["heal_attempt"])
        self._sql("UPDATE fts_code SET text = 'def tampered_symbol(): pass' WHERE chunk_id = 'c2'")
        result, err, _ = self._reconcile()
        self._assert_healed(result, err, "digest_mismatch")
        self.assertEqual(result["fts_heal_attempt"], attempt)
        self.assertEqual(self.iss.fts_recorded_integrity(self.index_dir, "code")["heal_attempt"], attempt)
        self.assertEqual(self.iss.fts_state_verdict(self.index_dir, "code")["heal_attempt"], attempt)
        # An ordinary (non-damage) reconcile never writes the marker.
        self.assertIsNone(self.iss.fts_recorded_integrity(self.index_dir, "docs")["heal_attempt"])

    def test_interrupted_publication_heals_under_the_open_attempt(self):
        self._publish_epoch()
        attempt = self.iss.begin_build_epoch(self.index_dir, "interrupted")  # never finalized
        self._sql("DELETE FROM fts_code")
        result, err, _ = self._reconcile()
        self._assert_healed(result, err, "probe_failed")
        self.assertEqual(result["fts_heal_attempt"], attempt)
        self.assertEqual(self.iss.build_epoch_state_token(self.index_dir)[1], "building")


class ZeroChangeHealProbeTests(unittest.TestCase):
    """Req 2: the zero-change build path's probe consults the FTS verdict so
    an idle repo heals FTS-only damage through the ordinary reconcile."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location("indexer", SCRIPTS_ROOT / "indexer.py")
        self.bi = importlib.util.module_from_spec(spec)
        sys.modules["indexer"] = self.bi
        spec.loader.exec_module(self.bi)
        self.iss = _load_store_module()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.index_dir = Path(self._tmp.name) / ".wavefoundry" / "index"
        rows = [
            {"id": f"c{i}", "path": f"f{i}.py", "kind": "code", "language": "python",
             "lines": [1, 5], "section": "", "text": f"def fn_{i}(): pass",
             "chunk_hash": f"h{i}", "vector": [1.0] + [0.0] * 383}
            for i in range(24)
        ]
        self.iss.apply_chunk_deltas(self.index_dir, "code", add_rows=rows)
        with _quiet():
            self.bi._sync_chunk_derived_state(self.index_dir)

    def _sql(self, stmt: str) -> None:
        conn = self.iss.sqlite_runtime.connect(self.iss.state_store_path(self.index_dir))
        try:
            with conn:
                conn.execute(stmt)
        finally:
            conn.close()

    def test_equal_count_substitution_routes_the_idle_build_to_the_reconcile(self):
        self.assertFalse(self.bi._chunk_index_needs_heal(self.index_dir))
        self._sql("UPDATE fts_code SET text = 'def tampered_symbol(): pass' WHERE chunk_id = 'c7'")
        self.assertTrue(self.bi._chunk_index_needs_heal(self.index_dir))
        with _quiet():
            stats = self.bi._sync_chunk_derived_state(self.index_dir)
        self.assertTrue(stats["code"]["fts_repaired"])
        self.assertEqual(stats["code"]["fts_reason"], "digest_mismatch")
        self.assertFalse(self.bi._chunk_index_needs_heal(self.index_dir))
        self.assertEqual(self.iss.fts_search(self.index_dir, "code", "tampered_symbol"), [])
        self.assertTrue(self.iss.fts_search(self.index_dir, "code", "fn_7"))

    def test_dropped_table_routes_the_idle_build_to_the_reconcile(self):
        self._sql("DROP TABLE fts_code")
        self.assertTrue(self.bi._chunk_index_needs_heal(self.index_dir))
        with _quiet():
            stats = self.bi._sync_chunk_derived_state(self.index_dir)
        self.assertTrue(stats["code"]["fts_repaired"])
        self.assertEqual(stats["code"]["fts_reason"], "probe_failed")
        self.assertFalse(self.bi._chunk_index_needs_heal(self.index_dir))


class ProbedServingTests(unittest.TestCase):
    """AC-3 / AC-4 / AC-5 / AC-7 / AC-8 at the public tools: one probed
    chokepoint, typed failures, healthy-zero controls, bounded detail,
    scheduling authority, the same-epoch heal marker, health, and the O(1)
    warmed read."""

    def setUp(self):
        self.srv = load_server()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True)
        self.iss = _load_store_module("_iss_query_honesty")
        self.code_rows = _code_rows()
        self.docs_rows = _docs_rows()
        # These public-tool controls represent a healthy unified index, which
        # requires a vector for every canonical row as well as intact FTS.
        for row in self.code_rows + self.docs_rows:
            row["vector"] = [1.0] + [0.0] * 383
        with _quiet():
            self.iss.reconcile_chunk_index(
                self.index_dir, "code", {r["id"] for r in self.code_rows}, lambda: self.code_rows)
            self.iss.reconcile_chunk_index(
                self.index_dir, "docs", {r["id"] for r in self.docs_rows}, lambda: self.docs_rows)
        import index_compatibility
        self.iss.write_build_bookkeeping(self.index_dir, {
            "content": ["docs", "code"],
            "walker_version": str(index_compatibility.SUPPORTED["walker_version"]),
            "chunker_versions": {layer: str(index_compatibility.SUPPORTED["chunker_version"])
                                 for layer in ("docs", "code")},
            "model_versions": {layer: "fixture-model" for layer in ("docs", "code")},
        })
        attempt = self.iss.begin_build_epoch(self.index_dir, "fixture")
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, attempt))
        self.COMPLETE = self.iss.build_epoch_state_token(self.index_dir)
        self.srv._DEGRADED_LOG_STATE.clear()
        self.srv._fts_invalidate_serving_state()
        self.addCleanup(self.srv._DEGRADED_LOG_STATE.clear)
        self.addCleanup(self.srv._fts_invalidate_serving_state)

    # --- helpers ---

    def _sql(self, *statements: str) -> None:
        conn = self.iss.sqlite_runtime.connect(self.iss.state_store_path(self.index_dir))
        try:
            with conn:
                for stmt in statements:
                    conn.execute(stmt)
        finally:
            conn.close()

    def _lexical(self, query: str, **kw) -> dict:
        return self.srv.code_lexical_response(self.root, query, **kw)

    def _server_iss(self):
        mod = self.srv._load_script("index_state_store")
        self.assertIs(mod, self.srv._load_script("index_state_store"),
                      "the seam spy needs a cached module object")
        return mod

    def _heal_build(self, scope: str) -> str:
        """The scheduled heal as the build path performs it: a fresh attempt,
        the ordinary reconcile under it, finalize (the only generation advance)."""
        attempt = self.iss.begin_build_epoch(self.index_dir, scope)
        with _quiet():
            self.iss.reconcile_chunk_index(
                self.index_dir, "code", {r["id"] for r in self.code_rows}, lambda: self.code_rows)
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, attempt))
        return attempt

    def _semantic_code_hit(self) -> dict:
        return {"id": "c1", "path": "src/alpha.py", "kind": "code", "language": "python",
                "source": "code", "lines": [1, 5], "text": "def alpha_handler(): pass", "score": 0.9}

    @staticmethod
    def _codes(resp: dict) -> list:
        return [d.get("code") for d in resp.get("diagnostics", [])]

    # --- AC-3 / AC-7: the lexical-only tool ---

    def test_code_lexical_dropped_table_is_typed_query_failed(self):
        self._sql("DROP TABLE fts_code")
        resp = self._lexical("alpha_handler")
        self.assertEqual(resp["status"], "error")
        data = resp["data"]
        self.assertEqual(data["failure_reason"], "query_failed")
        self.assertEqual(data["results"], [])
        self.assertEqual(data["result_count"], 0)
        self.assertNotIn("note", data)  # never the healthy zero-hit explanation
        self.assertIn("query_failed", self._codes(resp))
        self.assertNotIn("chunk_index_undercovered", self._codes(resp))
        self.assertEqual(data["damaged_tables"], ["code"])
        self.assertIn("probe_failed", data["detail"])
        # The intact docs table still serves a lexical-only docs query.
        docs = self._lexical("alpha_handler", table="docs")
        self.assertEqual(docs["status"], "ok")
        self.assertEqual({r["id"] for r in docs["data"]["results"]}, {"d1", "d2"})

    def test_code_lexical_equal_count_substitution_is_typed_at_the_probe_boundary(self):
        self._sql("UPDATE fts_code SET text = 'def tampered_symbol(): pass' WHERE chunk_id = 'c1'")
        resp = self._lexical("tampered_symbol", table="code")
        self.assertEqual(resp["status"], "error")
        self.assertEqual(resp["data"]["failure_reason"], "query_failed")
        self.assertIn("digest_mismatch", resp["data"]["detail"])

    def test_code_lexical_healthy_zero_and_healthy_hits_keep_their_contract(self):
        zero = self._lexical("zz_definitely_absent_zz")
        self.assertEqual(zero["status"], "ok")
        self.assertEqual(zero["data"]["result_count"], 0)
        self.assertIn("compound identifiers", zero["data"]["note"])
        self.assertEqual(zero.get("diagnostics", []), [])
        self.assertNotIn("failure_reason", zero["data"])
        hits = self._lexical("alpha_handler")
        self.assertEqual(hits["status"], "ok")
        self.assertGreaterEqual(hits["data"]["result_count"], 3)
        for field in ("id", "path", "kind", "language", "lines", "text", "text_truncated", "bm25", "table"):
            self.assertIn(field, hits["data"]["results"][0])
        self.assertNotIn("failure_reason", hits["data"])

    def test_cold_open_without_a_store_keeps_the_not_built_contract(self):
        fresh = _make_repo(Path(tempfile.mkdtemp(dir=self.tmp.name)))
        resp = self.srv.code_lexical_response(fresh, "anything")
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(resp["data"]["results"], [])
        self.assertIn("lexical_layer_unavailable", self._codes(resp))
        index = MagicMock()
        index.root = fresh
        index.search_code.side_effect = self.srv.SemanticModelUnavailableOfflineError("offline")
        search = self.srv.code_search_response(index, "alpha_handler", epoch_state=None)
        self.assertEqual(search["status"], "error")
        self.assertEqual(search["data"]["fallback_reason"], "store_absent")

    def test_interrupted_publication_refuses_then_recovers(self):
        attempt = self.iss.begin_build_epoch(self.index_dir, "interrupted")
        building = self.iss.build_epoch_state_token(self.index_dir)
        self.assertEqual(building[1], "building")
        index = MagicMock()
        index.root = self.root
        index.search_code.side_effect = self.srv.SemanticModelUnavailableOfflineError("offline")
        refused = self.srv.code_search_response(index, "alpha_handler", epoch_state=building)
        self.assertEqual(refused["status"], "error")
        self.assertEqual(refused["data"]["fallback_reason"], "index_not_ready")
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, attempt))
        served = self.srv.code_search_response(
            index, "alpha_handler", epoch_state=self.iss.build_epoch_state_token(self.index_dir))
        self.assertEqual(served["status"], "ok")
        self.assertEqual(served["data"]["search_mode"], "lexical_fallback")
        self.assertTrue(served["data"]["results"])

    # --- AC-7: hybrid tools keep semantic results + typed undercoverage ---

    def test_hybrid_code_search_keeps_semantic_results_and_flags_undercoverage(self):
        self._sql("DROP TABLE fts_code")
        index = MagicMock()
        index.root = self.root
        index.search_code.return_value = ([self._semantic_code_hit()], True)
        resp = self.srv.code_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        self.assertEqual(resp["status"], "ok")
        self.assertEqual(len(resp["data"]["results"]), 1)
        self.assertEqual(resp["data"]["search_mode"], "hybrid")
        self.assertIsNone(resp["data"]["fallback_reason"])
        codes = self._codes(resp)
        self.assertIn("lexical_undercoverage", codes)
        self.assertNotIn("lexical_fallback_failed", codes)
        self.assertNotIn("no_results", codes)

    def test_hybrid_code_ask_keeps_citations_and_flags_undercoverage(self):
        self._sql("DROP TABLE fts_docs")
        index = MagicMock()
        index.root = self.root
        index.search_combined.return_value = ([self._semantic_code_hit()], True, 0, 5, [], [], "none", None)
        index._layer_health = MagicMock()
        resp = self.srv.code_ask_response(index, self.root, "what does alpha_handler do?", epoch_state=self.COMPLETE)
        self.assertEqual(resp["status"], "ok")
        data = resp["data"]
        self.assertTrue(data["citations"])
        self.assertEqual(data["search_mode"], "hybrid")
        self.assertIsNone(data["fallback_reason"])
        self.assertIn("lexical_undercoverage", self._codes(resp))
        self.assertTrue(any("lexical undercoverage" in g for g in data["gaps"]), data["gaps"])
        self.assertIn("Based on indexed sources", data["answer"])

    def test_hybrid_healthy_controls_carry_no_undercoverage(self):
        index = MagicMock()
        index.root = self.root
        index.search_code.return_value = ([], True)
        zero = self.srv.code_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        self.assertEqual(zero["status"], "ok")
        self.assertIn("no_results", self._codes(zero))
        self.assertNotIn("lexical_undercoverage", self._codes(zero))
        index.search_code.return_value = ([self._semantic_code_hit()], True)
        hits = self.srv.code_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        self.assertNotIn("lexical_undercoverage", self._codes(hits))
        ask = MagicMock()
        ask.root = self.root
        ask.search_combined.return_value = ([self._semantic_code_hit()], True, 0, 5, [], [], "none", None)
        ask._layer_health = MagicMock()
        resp = self.srv.code_ask_response(ask, self.root, "alpha_handler?", epoch_state=self.COMPLETE)
        self.assertNotIn("lexical_undercoverage", self._codes(resp))
        self.assertFalse(any("lexical undercoverage" in g for g in resp["data"]["gaps"]))

    def test_fusion_kill_switch_suppresses_the_hybrid_diagnostic(self):
        self._sql("DROP TABLE fts_code")
        index = MagicMock()
        index.root = self.root
        index.search_code.return_value = ([self._semantic_code_hit()], True)
        with patch.dict(os.environ, {self.srv.LEXICAL_FUSION_DISABLE_ENV: "1"}):
            resp = self.srv.code_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
        self.assertNotIn("lexical_undercoverage", self._codes(resp))

    # --- AC-3: one shared chokepoint ---

    def test_every_public_fts_path_serves_through_the_chokepoint(self):
        src = Path(self.srv.__file__).read_text(encoding="utf-8")
        self.assertEqual(src.count("iss.fts_search("), 1,
                         "the chokepoint must be the only fts_search caller in server_impl")
        chokepoint = src.index("def _fts_probed_fetch(")
        call = src.index("iss.fts_search(")
        next_top_level_def = src.index("\ndef ", chokepoint + 10)
        self.assertLess(chokepoint, call)
        self.assertLess(call, next_top_level_def, "the one fts_search call lives inside the chokepoint")
        import inspect
        for method in (self.srv.WaveIndex._fts5_lexical_search, self.srv.WaveIndex._lexical_candidates):
            self.assertIn("_fts_probed_fetch(", inspect.getsource(method))
        self.assertIn("_fts_probed_fetch(", inspect.getsource(self.srv._fts_degraded_serve))
        self.assertIn("_fts_probed_fetch(", inspect.getsource(self.srv.code_lexical_response))
        # Behavioral: the degraded fallbacks of all three search tools and the
        # lexical tool each pass through the chokepoint exactly once.
        offline = self.srv.SemanticModelUnavailableOfflineError("offline")
        index = MagicMock()
        index.root = self.root
        index.search_code.side_effect = offline
        index.search_docs.side_effect = offline
        index.search_combined.side_effect = offline
        index._layer_health = MagicMock()
        with patch.object(self.srv, "_fts_probed_fetch", wraps=self.srv._fts_probed_fetch) as fetch:
            self.srv.docs_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
            self.assertEqual(fetch.call_count, 1)
            self.srv.code_search_response(index, "alpha_handler", epoch_state=self.COMPLETE)
            self.assertEqual(fetch.call_count, 2)
            self.srv.code_ask_response(index, self.root, "alpha_handler?", epoch_state=self.COMPLETE)
            self.assertEqual(fetch.call_count, 3)
            self._lexical("alpha_handler")
            self.assertEqual(fetch.call_count, 4)

    # --- A7: bounded, path-sanitized detail ---

    def test_failure_detail_is_bounded_and_repo_relative(self):
        iss_srv = self._server_iss()
        noisy = RuntimeError(
            f"disk exploded at {self.root}/.wavefoundry/index/index.sqlite " + "x" * 2000)
        with patch.object(iss_srv, "fts_search", side_effect=noisy):
            resp = self._lexical("alpha_handler", table="code")
            serve = self.srv._fts_degraded_serve(self.root, ("code",), "alpha_handler", 5)
        self.assertEqual(resp["status"], "error")
        for detail in (resp["data"]["detail"], serve["detail"]):
            self.assertLessEqual(len(detail), self.srv._FTS_DETAIL_CAP)
            self.assertNotIn(str(self.root), detail)
            self.assertIn(".wavefoundry/index/index.sqlite", detail)
        self.assertEqual(serve["failure_reason"], "query_failed")
        self.assertFalse(serve["available"])

    def test_failure_detail_strips_every_root_spelling_including_repr_doubled(self):
        """Wave 1wpif delivery review, SEC-RV1-1: a Windows OSError renders its
        filename through repr, which DOUBLES every backslash. The sanitizer
        matched only the single-separator spellings, so the doubled form
        survived the later backslash-to-slash normalization and left an
        absolute root in a public error string, regressing the 1uu9z
        no-path-leak contract. Pinned at string level so it holds on any
        platform, the way `_strip_root_forms` (wave 1wybs) pins the same class.
        """
        win_root = Path(r"C:\Users\op\repo")
        cases = {
            "posix": f"[Errno 2] No such file: '{self.root}/.wavefoundry/index/s.sqlite'",
            "win_single": r"[Errno 2] No such file: 'C:\Users\op\repo\.wavefoundry\index\s.sqlite'",
            "win_repr_doubled":
                "[Errno 2] No such file: 'C:\\\\Users\\\\op\\\\repo\\\\.wavefoundry\\\\index\\\\s.sqlite'",
            "win_forward_slash":
                "[Errno 2] No such file: 'C:/Users/op/repo/.wavefoundry/index/s.sqlite'",
            "win_mixed":
                "[Errno 2] No such file: 'C:/Users/op\\repo\\.wavefoundry\\index\\s.sqlite'",
            "win_lowercased":
                r"[Errno 2] No such file: 'c:\users\op\repo\.wavefoundry\index\s.sqlite'",
        }
        for name, text in cases.items():
            root = self.root if name == "posix" else win_root
            detail = self.srv._bounded_failure_detail(root, text)
            # The oracle must be separator-blind. A first version of this
            # test asserted the literal "Users/op/repo" and PASSED against a
            # mutant with the repair reverted, because the leak comes out as
            # "C://Users//op//repo//..." -- doubled separators the literal
            # never matched. Collapse every separator run on both sides so
            # the assertion sees the leaked root in any spelling.
            flat_root = re.sub(r"[\\/]+", "/", str(root)).rstrip("/").casefold()
            flat_detail = re.sub(r"[\\/]+", "/", detail).casefold()
            with self.subTest(spelling=name):
                self.assertNotIn(flat_root, flat_detail, detail)
                self.assertIn("index", detail, detail)
                self.assertLessEqual(len(detail), self.srv._FTS_DETAIL_CAP)

    def test_failure_detail_does_not_mangle_a_sibling_of_the_root(self):
        """Wave 1wpif cycle-4, SEC-RV3-1: making the root matcher separator-
        and case-insensitive introduced an OVER-match. With no boundary after
        the last segment, a root that is a string prefix of a sibling
        directory matched inside it, so on a machine where this framework sits
        beside a target repository `.../wavefoundry-target/x` came out as
        `-target/x` -- a path that exists nowhere and reads as if it were
        inside this repository. Over-matching is as much a defect as
        under-matching, and no assertion caught it, because asserting only
        that the root is ABSENT is satisfied by a mangled result.
        """
        root = Path("/Users/op/Developer/wavefoundry")
        siblings = {
            "suffixed": "[Errno 2] No such file: '/Users/op/Developer/wavefoundry-target/.wavefoundry/index/s.sqlite'",
            "appended": "database is locked at /Users/op/Developer/wavefoundryX/docs/plan.md",
        }
        for name, text in siblings.items():
            detail = self.srv._bounded_failure_detail(root, text)
            with self.subTest(sibling=name):
                # The sibling's own directory name must survive intact.
                self.assertIn("wavefoundry-target" if name == "suffixed" else "wavefoundryX",
                              detail, detail)
        # The real root is still stripped, so the boundary did not disable it.
        real = self.srv._bounded_failure_detail(
            root, "[Errno 2] No such file: '/Users/op/Developer/wavefoundry/.wavefoundry/index/s.sqlite'")
        self.assertNotIn("Developer/wavefoundry/", real, real)
        self.assertIn(".wavefoundry/index/s.sqlite", real, real)

    def test_failure_detail_strips_the_home_directory_in_every_spelling(self):
        """Wave 1wpif cycle-4, SEC-RV3-2: the docstring promises that neither
        the root prefix NOR the home directory leaves the process, but the
        home branch was a literal, case-sensitive replace sitting one line
        below the repaired root branch. It leaked the real home directory in
        exactly the three spellings the root branch had just been fixed for,
        and the trailing separator normalization turned those misses back into
        readable absolute paths. Nothing constrained the home branch at all.
        """
        win_home = Path(r"C:\Users\op")
        cases = {
            "single": r"[Errno 2] No such file: 'C:\Users\op\elsewhere\notes.txt'",
            "repr_doubled": "[Errno 2] No such file: 'C:\\\\Users\\\\op\\\\elsewhere\\\\notes.txt'",
            "forward_slash": "[Errno 2] No such file: 'C:/Users/op/elsewhere/notes.txt'",
            "lowercased": r"[Errno 2] No such file: 'c:\users\op\elsewhere\notes.txt'",
        }
        with patch.object(self.srv.Path, "home", staticmethod(lambda: win_home)):
            for name, text in cases.items():
                detail = self.srv._bounded_failure_detail(Path("/no-such-root"), text)
                flat = re.sub(r"[\\/]+", "/", detail).casefold()
                with self.subTest(spelling=name):
                    self.assertNotIn("users/op", flat, detail)
                    self.assertIn("elsewhere", detail, detail)

        # Wave 1wpif cycle-5 (SEC-RV4-1): the longest-first ordering of the
        # prefixes was justified in a comment and pinned by nothing -- sorting
        # shortest-first, or not sorting at all, left all 41 tests in this
        # module green. It is materially live: a repository nested under the
        # home directory is the ordinary layout, and the wrong order strips the
        # home prefix first, so the detail degrades from repo-relative to
        # home-relative and discloses where the repository sits. Pin it.
        posix_home = Path("/Users/op")
        nested_root = Path("/Users/op/Developer/wavefoundry")
        with patch.object(self.srv.Path, "home", staticmethod(lambda: posix_home)):
            nested = self.srv._bounded_failure_detail(
                nested_root,
                "[Errno 2] No such file: '/Users/op/Developer/wavefoundry/.wavefoundry/index/s.sqlite'")
            self.assertNotIn("Developer/wavefoundry", nested, nested)
            self.assertIn(".wavefoundry/index/s.sqlite", nested, nested)
            # A path under home but OUTSIDE the repository still reads as
            # home-relative, so the ordering did not simply swallow everything.
            outside = self.srv._bounded_failure_detail(
                nested_root, "[Errno 2] No such file: '/Users/op/Documents/notes.txt'")
            self.assertIn("~/Documents/notes.txt", outside, outside)

        # The case above is satisfied by insertion order alone (the root is
        # appended before the home directory), so it kills a shortest-first
        # sort but not a no-sort. Discriminate the ORDERING itself with a
        # layout where insertion order is unfavourable: a home directory that
        # is LONGER than the root. Longest-first must still strip the longer
        # prefix, which is the property the code's comment claims.
        long_home = Path("/Users/op/Developer")
        short_root = Path("/Users/op")
        with patch.object(self.srv.Path, "home", staticmethod(lambda: long_home)):
            ordered = self.srv._bounded_failure_detail(
                short_root, "[Errno 2] No such file: '/Users/op/Developer/notes.txt'")
            self.assertIn("~/notes.txt", ordered, ordered)
            self.assertNotIn("Developer", ordered, ordered)

    # --- AC-8 / Req 7: probes, scheduling, marker, warmed reads ---

    def test_serving_error_probes_once_types_failure_and_schedules_at_most_once(self):
        iss_srv = self._server_iss()
        self.assertEqual(self._lexical("alpha_handler", table="code")["status"], "ok")  # warm
        self._sql("DROP TABLE fts_code")  # same epoch, cache warm: the first read is a SERVING error
        probes = []
        real_verdict = iss_srv.fts_state_verdict

        def spy_verdict(*a, **k):
            probes.append(a[1])
            return real_verdict(*a, **k)

        with patch.object(iss_srv, "fts_state_verdict", side_effect=spy_verdict), \
                patch.object(self.srv, "_start_background_index_refresh", return_value=True) as refresh:
            for _ in range(3):
                resp = self._lexical("alpha_handler", table="code")
                self.assertEqual(resp["status"], "error")
                self.assertEqual(resp["data"]["failure_reason"], "query_failed")
        self.assertEqual(probes, ["code"], "exactly one bounded re-probe after the serving error")
        self.assertEqual(refresh.call_count, 1, "healing is requested at most once per table per epoch")
        refresh.assert_called_with(self.root, "project")
        fetch = self.srv._fts_probed_fetch(self.root, ("code",), "alpha_handler", 5)
        self.assertEqual(fetch["heal"]["code"]["suppressed"], "already_requested")

    def test_query_path_performs_no_store_writes(self):
        self._sql("DROP TABLE fts_code")
        store = self.iss.state_store_path(self.index_dir)
        before = (store.stat().st_mtime_ns, store.read_bytes())
        with patch.object(self.srv, "_start_background_index_refresh", return_value=False):
            for _ in range(2):
                self.assertEqual(self._lexical("alpha_handler", table="code")["status"], "error")
            self.srv._fts_degraded_serve(self.root, ("code",), "alpha_handler", 5)
        self.assertEqual((store.stat().st_mtime_ns, store.read_bytes()), before,
                         "a damaged read must neither heal nor write a marker")
        self.assertIsNone(self.iss.fts_recorded_integrity(self.index_dir, "code")["heal_attempt"])

    def test_heal_marker_suppresses_a_second_heal_within_the_same_epoch(self):
        with patch.object(self.srv, "_start_background_index_refresh", return_value=True) as refresh:
            # Damage -> typed failure -> exactly one heal request.
            self._sql("DROP TABLE fts_code")
            self.assertEqual(self._lexical("alpha_handler", table="code")["status"], "error")
            self.assertEqual(refresh.call_count, 1)
            # The scheduled heal runs as the build path does: new attempt,
            # ordinary reconcile (marker = that attempt), finalize.
            healed_attempt = self._heal_build("heal-1")
            self.assertEqual(self.iss.fts_recorded_integrity(self.index_dir, "code")["heal_attempt"], healed_attempt)
            self.assertEqual(self.iss.build_epoch_state_token(self.index_dir)[0], healed_attempt)
            healthy = self._lexical("alpha_handler", table="code")
            self.assertEqual(healthy["status"], "ok")
            self.assertTrue(healthy["data"]["results"])
            # Re-damage WITHIN the healed epoch: typed failure persists, no
            # second heal request (marker == published attempt), no writes.
            self._sql("DROP TABLE fts_code")
            for _ in range(2):
                again = self._lexical("alpha_handler", table="code")
                self.assertEqual(again["status"], "error")
                self.assertEqual(again["data"]["failure_reason"], "query_failed")
            self.assertEqual(refresh.call_count, 1)
            fetch = self.srv._fts_probed_fetch(self.root, ("code",), "alpha_handler", 5)
            self.assertEqual(fetch["heal"]["code"]["suppressed"], "already_healed_this_epoch")
            self.assertEqual(self.iss.fts_recorded_integrity(self.index_dir, "code")["heal_attempt"], healed_attempt)
            # The NEXT epoch (a real build) heals again and serving recovers.
            next_attempt = self._heal_build("heal-2")
            self.assertNotEqual(next_attempt, healed_attempt)
            self.assertEqual(self.iss.fts_recorded_integrity(self.index_dir, "code")["heal_attempt"], next_attempt)
            recovered = self._lexical("alpha_handler", table="code")
            self.assertEqual(recovered["status"], "ok")
            self.assertTrue(recovered["data"]["results"])

    def test_substitution_after_a_warmed_read_is_detected_at_the_next_epoch_transition(self):
        # AC-2 pin: detection happens at the next probe boundary, never on a
        # warmed healthy read. A count-preserving substitution keeps the MATCH
        # path alive, so the warmed read serves; the epoch transition re-probes.
        self.assertEqual(self._lexical("alpha_handler", table="code")["status"], "ok")
        self._sql("UPDATE fts_code SET text = 'def tampered_symbol(): pass' WHERE chunk_id = 'c1'")
        warmed = self._lexical("tampered_symbol", table="code")
        self.assertEqual(warmed["status"], "ok")
        attempt = self.iss.begin_build_epoch(self.index_dir, "transition")
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, attempt))
        with patch.object(self.srv, "_start_background_index_refresh", return_value=True):
            boundary = self._lexical("tampered_symbol", table="code")
        self.assertEqual(boundary["status"], "error")
        self.assertIn("digest_mismatch", boundary["data"]["detail"])

    def test_warmed_healthy_read_runs_no_counts_no_health_scan_no_probe(self):
        """AC-8 (PERF-RDY-3 / QA-RDY-3): measured through a sqlite trace hook
        (``set_trace_callback`` on every read-only connection the store opens)
        plus store-seam spies on ``fts_state_verdict`` and
        ``_state_store_health_summary``, asserted on ``code_lexical``."""
        iss_srv = self._server_iss()
        probes = []
        real_verdict = iss_srv.fts_state_verdict

        def spy_verdict(*a, **k):
            probes.append(a[1])
            return real_verdict(*a, **k)

        statements: list[str] = []
        real_open = iss_srv.open_read_only

        def spy_open(index_dir):
            conn = real_open(index_dir)
            if conn is not None:
                conn.set_exec_trace(lambda cursor, sql, bindings: (statements.append(sql), True)[1])
            return conn

        with patch.object(iss_srv, "fts_state_verdict", side_effect=spy_verdict):
            warm = self._lexical("alpha_handler")
            self.assertEqual(warm["status"], "ok")
            self.assertTrue(warm["data"]["results"])
            warm_probes = len(probes)
            self.assertGreaterEqual(warm_probes, 1, "the first read in an epoch probes once per table")
            with patch.object(iss_srv, "open_read_only", side_effect=spy_open), \
                    patch.object(self.srv, "_state_store_health_summary",
                                 wraps=self.srv._state_store_health_summary) as health:
                for query, table in (("alpha_handler", "both"), ("alpha_handler", "code"), ("zz_absent_zz", "docs")):
                    resp = self._lexical(query, table=table)
                    self.assertEqual(resp["status"], "ok")
        self.assertEqual(len(probes), warm_probes, "a warmed read never re-probes")
        health.assert_not_called()
        self.assertTrue(statements, "the trace hook must observe the serving query")
        self.assertTrue(any("MATCH" in s.upper() for s in statements))
        offenders = [
            s for s in statements
            if re.search(r"count\s*\(", s, re.IGNORECASE)
            or "quick_check" in s.lower()
            or "integrity_check" in s.lower()
            or (re.search(r"\bfrom\s+fts_", s, re.IGNORECASE) and "MATCH" not in s.upper())
        ]
        self.assertEqual(offenders, [])

    # --- PERF-DEL-3 (delivery repair): coverage costs no second probe ---

    def test_coverage_is_computed_without_the_probing_health_summary(self):
        """``code_lexical`` still reports coverage, and computing it no longer
        routes through ``_state_store_health_summary`` -> ``probe_state_store``
        (the structural quick_check, 674 ms on the real store) AFTER
        ``fts_state_verdict`` established liveness, parity and the keyed digest
        for the same epoch."""
        iss_srv = self._server_iss()
        self.srv._fts_invalidate_serving_state()
        with patch.object(self.srv, "_state_store_health_summary",
                          wraps=self.srv._state_store_health_summary) as health, \
                patch.object(iss_srv, "probe_state_store",
                             wraps=iss_srv.probe_state_store) as probe:
            resp = self._lexical("alpha_handler", table="code")
        self.assertEqual(resp["status"], "ok")
        self.assertIn("code", resp["data"]["coverage"])
        self.assertIn("registry_rows", resp["data"]["coverage"]["code"])
        health.assert_not_called()
        probe.assert_not_called()

    def test_the_hybrid_halves_request_no_coverage_at_the_chokepoint(self):
        """The two hybrid halves (``_fts5_lexical_search``,
        ``_lexical_candidates``) never read ``coverage``, so they call the
        chokepoint with ``include_coverage=False`` and the first hybrid read in
        an epoch computes none at all; the lexical tool and the degraded
        fallbacks, which report it, keep the default."""
        index = self.srv.WaveIndex(self.root)
        requested: list = []
        real_fetch = self.srv._fts_probed_fetch

        def spy(*args, **kwargs):
            requested.append(kwargs.get("include_coverage", True))
            return real_fetch(*args, **kwargs)

        self.srv._fts_invalidate_serving_state()
        with patch.object(self.srv, "_fts_probed_fetch", side_effect=spy), \
                patch.object(self.srv, "_chunk_index_coverage",
                             wraps=self.srv._chunk_index_coverage) as coverage:
            self.assertTrue(index._fts5_lexical_search("code", "alpha_handler", 5))
            self.assertTrue(index._lexical_candidates("alpha_handler"))
            self.assertEqual(requested, [False, False])
            coverage.assert_not_called()
            serve = self.srv._fts_degraded_serve(self.root, ("code",), "alpha_handler", 5)
            self.assertTrue(serve["available"])
            self.assertEqual(requested[-1], True, "the degraded fallback still reports coverage")
            self.assertIn("code", serve["coverage"])
            self.assertEqual(coverage.call_count, 1)

    # --- AC-5: health ---

    def test_health_exposes_parity_and_the_epoch_cached_verdict(self):
        summary = self.srv._state_store_health_summary(self.root)
        code = summary["fts"]["code"]
        self.assertTrue(code["ok"])
        self.assertTrue(code["live"])
        self.assertEqual((code["fts_rows"], code["registry_rows"]), (3, 3))
        self.assertEqual(code["digest"], "ok")
        self.assertTrue(code["digest_recorded"])
        self.assertIsNone(code["heal_attempt"])
        self.assertEqual(code["epoch"], list(self.COMPLETE))
        # Damage + the next epoch transition (the probe boundary): the verdict
        # the serving side uses is the one health reports.
        self._sql("INSERT INTO fts_code (chunk_id, path, kind, language, tags, start_line, end_line, text) "
                  "VALUES ('orphan', 'src/o.py', 'code', 'python', '', 1, 2, 'orphan_symbol')")
        attempt = self.iss.begin_build_epoch(self.index_dir, "transition")
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, attempt))
        with patch.object(self.srv, "_start_background_index_refresh", return_value=True):
            damaged = self.srv._state_store_health_summary(self.root)["fts"]["code"]
            self.assertFalse(damaged["ok"])
            self.assertEqual(damaged["reason"], "probe_failed")
            self.assertEqual((damaged["fts_rows"], damaged["registry_rows"]), (3, 3))
            index = MagicMock()
            index.root = self.root
            index.docs_health.return_value = {
                "missing_layers": [], "stale_layers": [], "readiness_overview": "ready", "semantic_ready": True,
            }
            resp = self.srv.index_health_response(index)
        self.assertEqual(resp["status"], "ok")
        self.assertIn("fts_integrity_failed", self._codes(resp))
        self.assertEqual(resp["data"]["state_store"]["fts"]["code"]["reason"], "probe_failed")
        self.assertEqual(resp["data"]["state_store"]["fts"]["docs"]["ok"], True)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

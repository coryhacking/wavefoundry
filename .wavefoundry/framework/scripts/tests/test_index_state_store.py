"""Tests for the semantic-index SQLite state store (wave 1rsh9 / 1rq4h).

Covers the substrate contract (WAL/versioning/recovery), the freshness/
attribution resident schema and its 1ro43/1p8gy consumption contracts, the
build write path (zero-change skip, unchanged-Lance-rows guarantee),
concurrency, maintenance (WAL bounded, reclaim), and the two-layer integrity
probe (structural + stale-fingerprint).
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing, redirect_stderr
from unittest import mock
from pathlib import Path
from unittest import mock

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
STORE_PATH = SCRIPTS_ROOT / "index_state_store.py"


def load_store_module():
    spec = importlib.util.spec_from_file_location("index_state_store", STORE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["index_state_store"] = mod
    spec.loader.exec_module(mod)
    return mod


def _init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)


def _commit_all(root: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", message], check=True)


class _TempRepoCase(unittest.TestCase):
    def setUp(self):
        self.iss = load_store_module()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir()
        self.index_dir = self.root / ".wavefoundry" / "index"


class _FlakyConn:
    """Delegating sqlite connection proxy that raises once on a marked SQL.

    Wave 1wpif delivery review: injecting at the connection is the only way to
    reproduce a lock or IO error at a specific statement without a second
    process, and the error class is exactly what the repair classifies on.
    """

    def __init__(self, real, marker, exc, times=1):
        self._real = real
        self._marker = marker
        self._exc = exc
        self._left = times

    def execute(self, sql, *args, **kwargs):
        if self._marker in sql and self._left > 0:
            self._left -= 1
            raise self._exc
        return self._real.execute(sql, *args, **kwargs)

    def executemany(self, sql, *args, **kwargs):
        # The registry insert is an executemany; intercepting only `execute`
        # silently misses it and the injected error never fires.
        if self._marker in sql and self._left > 0:
            self._left -= 1
            raise self._exc
        return self._real.executemany(sql, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._real, name)

    # `with conn:` is a type-level lookup, so __getattr__ never sees it.
    def __enter__(self):
        return self._real.__enter__()

    def __exit__(self, *exc_info):
        return self._real.__exit__(*exc_info)


class AuxiliaryLikeTests(_TempRepoCase):
    def test_drift_prefixes_preserve_ascii_case_wildcards_and_bound_quotes(self):
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            entries = {path: {"drifted": True, "commits_since": 5}
                       for path in ("DOCS/REPORTS/old.md", "docs/reports/old.md",
                                    "docs/reports-extra/keep.md", "docs/Guide.md",
                                    "DOCS/RÉPORTS/nonascii.md", "DOCS/REPO'T/quote.md")}
            store.upsert_doc_drift(entries)
            result = self.iss.drift_worklist(self.index_dir)
            self.assertEqual(result["flagged_count"], 4)
            self.assertEqual({e["path"] for e in result["entries"]},
                             set(entries) - {"DOCS/REPORTS/old.md", "docs/reports/old.md"})
            with mock.patch.object(self.iss, "DRIFT_EXEMPT_PREFIXES", ("docs/repo_t/",)):
                result = self.iss.drift_worklist(self.index_dir)
                self.assertNotIn("DOCS/REPO'T/quote.md", {e["path"] for e in result["entries"]})
            with mock.patch.object(self.iss, "DRIFT_EXEMPT_PREFIXES", ("docs/repo't/",)):
                result = self.iss.drift_worklist(self.index_dir)
                self.assertEqual(result["flagged_count"], 5)
                self.assertNotIn("DOCS/REPO'T/quote.md", {e["path"] for e in result["entries"]})
        finally:
            store.close()


class StoreSubstrateTests(_TempRepoCase):
    """WAL/versioning contract and non-destructive recovery boundaries."""

    def test_creation_sets_wal_busy_timeout_schema_version_and_auto_vacuum(self):
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            conn = store._conn
            self.assertEqual(
                str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower(), "wal"
            )
            self.assertGreaterEqual(int(conn.execute("PRAGMA busy_timeout").fetchone()[0]), 5000)
            # auto_vacuum=INCREMENTAL is 2 (AC-8 creation half)
            self.assertEqual(int(conn.execute("PRAGMA auto_vacuum").fetchone()[0]), 2)
            self.assertEqual(
                store.get_meta("store_schema_version"), self.iss.STATE_STORE_SCHEMA_VERSION
            )
        finally:
            store.close()

    def test_reopen_current_version_performs_no_schema_churn(self):
        store = self.iss.IndexStateStore(self.index_dir)
        store.set_meta({"sentinel": "survives"})
        self.assertTrue(store.ensure_current())
        store.close()
        store2 = self.iss.IndexStateStore(self.index_dir)
        try:
            self.assertTrue(store2.ensure_current())
            self.assertEqual(store2.get_meta("sentinel"), "survives")
        finally:
            store2.close()

    def test_unknown_schema_version_preserves_store_and_refuses(self):
        store = self.iss.IndexStateStore(self.index_dir)
        store.apply_freshness(rows={"a.py": {"last_modified": 1, "churn_score": 0.5,
                                            "commit_count": 5, "source": "git"}})
        store.set_meta({"store_schema_version": "999"})
        with self.assertRaises(self.iss.sqlite_runtime.StorageRecoveryRequired):
            store.ensure_current()
        self.assertEqual(store.get_meta("store_schema_version"), "999")
        self.assertEqual(store._conn.execute("SELECT COUNT(*) FROM file_freshness").fetchone()[0], 1)
        store.close()
        before = self.iss.state_store_path(self.index_dir).read_bytes()
        with self.assertRaises(self.iss.sqlite_runtime.StorageRecoveryRequired):
            self.iss.IndexStateStore(self.index_dir)
        self.assertEqual(self.iss.state_store_path(self.index_dir).read_bytes(), before)

    def test_corrupted_store_is_preserved_and_refused(self):
        self.iss.IndexStateStore(self.index_dir).close()
        path = self.iss.state_store_path(self.index_dir)
        corrupt = b"this is not a sqlite database" * 64
        path.write_bytes(corrupt)
        with self.assertRaises(self.iss.sqlite_runtime.Error):
            self.iss.IndexStateStore(self.index_dir)
        self.assertEqual(path.read_bytes(), corrupt)

    def test_locked_open_is_not_treated_as_corruption(self):
        holder = self.iss.IndexStateStore(self.index_dir)
        path = self.iss.state_store_path(self.index_dir)
        inode = path.stat().st_ino
        holder._conn.execute("BEGIN IMMEDIATE")
        holder._conn.execute("INSERT OR REPLACE INTO meta VALUES ('hold','1')")
        real_connect = self.iss.sqlite_runtime.connect
        def bounded_connect(*args, **kwargs):
            conn = real_connect(*args, **kwargs)
            conn.set_busy_timeout(10)
            return conn
        try:
            with mock.patch.object(self.iss.sqlite_runtime, "connect", side_effect=bounded_connect):
                with self.assertRaises(self.iss.sqlite_runtime.Error):
                    self.iss.IndexStateStore(self.index_dir)
        finally:
            holder._conn.execute("ROLLBACK")
            holder.close()
        self.assertEqual(path.stat().st_ino, inode)
        self.iss.IndexStateStore(self.index_dir).close()

    def test_meta_read_lock_error_never_resets_the_store(self):
        """Wave 1wpif delivery review, ARCH-RV1-1: `meta_all` swallowed every
        sqlite error into `{}`, so `versions_current()` reported False against
        a perfectly current store and `ensure_current()` dropped every
        resident table. A wait/IO error must PROPAGATE; only a genuinely
        absent table is an honest empty reading."""
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            flaky = _FlakyConn(store._conn, "FROM meta",
                               self.iss.sqlite_runtime.apsw.BusyError("database is locked"))
            store._conn = flaky
            with mock.patch.object(
                store, "reset", side_effect=AssertionError("reset must not run")
            ):
                with self.assertRaises(self.iss.sqlite_runtime.apsw.BusyError):
                    store.ensure_current()
            # The deferral is durable, not stderr-only.
            self.assertIn(
                "meta read deferred, store preserved",
                self.iss.store_log_path(self.index_dir).read_text(encoding="utf-8"),
            )
            # An absent meta table reads as empty, but cannot authorize erasing
            # the canonical database; ensure_current still refuses below.
            store._conn = flaky._real
            store._conn.execute("DROP TABLE meta")
            self.assertEqual(store.meta_all(), {})
            self.assertFalse(store.versions_current())
            with self.assertRaises(self.iss.sqlite_runtime.StorageRecoveryRequired):
                store.ensure_current()
        finally:
            store.close()

    def test_rebuild_transaction_failure_preserves_rows_and_fence(self):
        rows = [{"id": "a", "path": "a.py", "text": "alpha", "lines": [1,3]}]
        self.iss.rebuild_chunk_index(self.index_dir, "code", rows)
        store = self.iss.IndexStateStore(self.index_dir)
        store.set_meta({"in-flight-fence": "1"})
        store._conn.execute("CREATE TRIGGER fail_registry BEFORE INSERT ON chunk_registry "
                            "BEGIN SELECT RAISE(ABORT,'injected write failure'); END")
        store.close()
        with self.assertRaises(self.iss.sqlite_runtime.Error):
            self.iss.rebuild_chunk_index(self.index_dir, "code", [{"id": "b", "path": "b.py", "text": "beta"}])
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            self.assertEqual(store.get_meta("in-flight-fence"), "1")
            self.assertEqual(store._conn.execute("SELECT chunk_id FROM chunks_code").fetchall(), [("a",)])
            self.assertEqual(store._conn.execute("SELECT chunk_id FROM chunk_registry").fetchall(), [("a",)])
        finally:
            store.close()

    def test_rebuild_refuses_stale_canonical_column_shape_without_reset(self):
        store = self.iss.IndexStateStore(self.index_dir)
        store.set_meta({"preserved-witness": "1"})
        store._conn.execute("ALTER TABLE chunk_registry RENAME COLUMN chunk_hash TO obsolete_hash")
        store.close()
        with self.assertRaises(self.iss.sqlite_runtime.Error):
            self.iss.rebuild_chunk_index(self.index_dir, "code", [{"id": "a", "path": "a.py", "text": "alpha"}])
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            self.assertEqual(store.get_meta("preserved-witness"), "1")
            self.assertEqual(store._conn.execute("SELECT count(*) FROM chunks_code").fetchone(), (0,))
        finally:
            store.close()

    def test_derived_rebuild_preserves_canonical_vector_and_build_fence(self):
        row = {"id": "a", "path": "a.py", "text": "alpha", "lines": [3,7],
               "vector": [1.0] + [0.0] * 383}
        self.iss.apply_chunk_deltas(self.index_dir, "code", add_rows=[row])
        store = self.iss.IndexStateStore(self.index_dir)
        store.set_meta({"preserved-witness": "1"})
        before = store._conn.execute("SELECT embedding FROM vectors_code").fetchone()
        store._conn.execute("DELETE FROM chunk_registry")
        store._conn.execute("INSERT INTO fts_code(fts_code) VALUES('delete-all')")
        store.close()
        self.iss.rebuild_chunk_index(self.index_dir, "code", [])
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            self.assertEqual(store.get_meta("preserved-witness"), "1")
            self.assertEqual(store._conn.execute("SELECT embedding FROM vectors_code").fetchone(), before)
            self.assertEqual(store._conn.execute("SELECT chunk_id FROM chunk_registry").fetchall(), [("a",)])
            self.assertEqual(store._conn.execute("SELECT count(*) FROM fts_code WHERE fts_code MATCH 'alpha'").fetchone(), (1,))
            self.assertEqual(self.iss._fts_recorded_digest(store._conn,"code"), self.iss._fts_table_digest(store._conn,"fts_code"))
        finally:
            store.close()

    def test_store_absence_is_not_an_error_for_readers(self):
        # No store built: every read primitive degrades to None/empty (AC-2).
        self.assertIsNone(self.iss.freshness_for_path(self.index_dir, "a.py"))
        self.assertEqual(self.iss.wave_attribution_for_path(self.index_dir, "a.py"), [])
        self.assertIsNone(self.iss.doc_drift_for_path(self.index_dir, "b.md"))
        probe = self.iss.probe_state_store(self.root, self.index_dir)
        self.assertEqual(probe["status"], "absent")


class FreshnessContractTests(_TempRepoCase):
    """AC-3: the 1ro43/1p8gy consumption contracts, fixture-covered."""

    def _build(self, paths):
        return self.iss.update_freshness_from_build(self.root, self.index_dir, paths)

    def test_git_repo_populates_last_modified_churn_and_commits(self):
        _init_git_repo(self.root)
        (self.root / "a.py").write_text("x=1\n")
        (self.root / "b.md").write_text("# b\n")
        _commit_all(self.root, "c1")
        (self.root / "a.py").write_text("x=2\n")
        _commit_all(self.root, "c2")
        summary = self._build(["a.py", "b.md"])
        self.assertEqual(summary["written"], 2)
        fresh = self.iss.freshness_for_path(self.index_dir, "a.py")
        self.assertIsNotNone(fresh)
        self.assertEqual(sorted(fresh.keys()), ["age_days", "churn_score", "commits_since"])
        self.assertEqual(fresh["commits_since"], 2)
        self.assertGreater(fresh["churn_score"], 0.0)
        self.assertAlmostEqual(fresh["age_days"], 0.0, delta=1.0)
        self.assertEqual(self.iss.freshness_for_path(self.index_dir, "b.md")["commits_since"], 1)

    def test_since_ts_filters_commit_count(self):
        _init_git_repo(self.root)
        (self.root / "a.py").write_text("x=1\n")
        _commit_all(self.root, "c1")
        self._build(["a.py"])
        future = int(time.time()) + 3600
        fresh = self.iss.freshness_for_path(self.index_dir, "a.py", since_ts=future)
        self.assertEqual(fresh["commits_since"], 0)
        past = int(time.time()) - 3600
        fresh = self.iss.freshness_for_path(self.index_dir, "a.py", since_ts=past)
        self.assertEqual(fresh["commits_since"], 1)

    def test_non_git_root_falls_back_to_mtime_without_errors(self):
        (self.root / "plain.txt").write_text("hello\n")
        summary = self._build(["plain.txt"])
        self.assertEqual(summary["written"], 1)
        self.assertNotIn("error", summary)
        fresh = self.iss.freshness_for_path(self.index_dir, "plain.txt")
        self.assertEqual(fresh["commits_since"], 0)
        self.assertEqual(fresh["churn_score"], 0.0)
        self.assertIsNotNone(fresh["age_days"])
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            source = store._conn.execute(
                "SELECT source FROM file_freshness WHERE path='plain.txt'"
            ).fetchone()[0]
        finally:
            store.close()
        self.assertEqual(source, "mtime")

    def test_wave_attribution_and_doc_drift_are_resolvable_per_doc(self):
        store = self.iss.IndexStateStore(self.index_dir)
        store.replace_wave_attribution(
            landings=[("1abcd", "deadbeef", 1700000000)],
            change_files=[("1abcd", "src/a.py"), ("1abcd", "docs/x.md")],
        )
        store.upsert_doc_drift({
            "docs/x.md": {"drifted": True, "drift_refs": ["src/a.py"],
                          "commits_since": 7, "anchor_kind": "verification"},
            "docs/waves/old/wave.md": {"historical": True, "waves_behind": 3},
        })
        store.close()
        attribution = self.iss.wave_attribution_for_path(self.index_dir, "src/a.py")
        self.assertEqual(attribution, [{"wave_id": "1abcd", "commit_sha": "deadbeef",
                                        "landed_at": 1700000000}])
        drift = self.iss.doc_drift_for_path(self.index_dir, "docs/x.md")
        self.assertEqual(drift["drifted"], True)
        self.assertEqual(drift["drift_refs"], ["src/a.py"])
        self.assertEqual(drift["commits_since"], 7)
        self.assertEqual(drift["anchor_kind"], "verification")
        historical = self.iss.doc_drift_for_path(self.index_dir, "docs/waves/old/wave.md")
        self.assertTrue(historical["historical"])
        self.assertEqual(historical["waves_behind"], 3)


class BuildIntegrationTests(_TempRepoCase):
    """AC-4 (zero-change skip + Lance untouched), AC-5 (concurrent read)."""

    def test_zero_change_build_skips_the_write(self):
        _init_git_repo(self.root)
        (self.root / "a.py").write_text("x=1\n")
        _commit_all(self.root, "c1")
        first = self.iss.update_freshness_from_build(self.root, self.index_dir, ["a.py"])
        self.assertFalse(first["skipped"])
        second = self.iss.update_freshness_from_build(self.root, self.index_dir, ["a.py"])
        self.assertTrue(second["skipped"])
        # A new commit invalidates the fingerprint → rewrite.
        (self.root / "a.py").write_text("x=2\n")
        _commit_all(self.root, "c2")
        third = self.iss.update_freshness_from_build(self.root, self.index_dir, ["a.py"])
        self.assertFalse(third["skipped"])

    def test_path_set_change_invalidates_the_skip(self):
        _init_git_repo(self.root)
        (self.root / "a.py").write_text("x=1\n")
        _commit_all(self.root, "c1")
        self.iss.update_freshness_from_build(self.root, self.index_dir, ["a.py"])
        (self.root / "new.txt").write_text("n\n")
        result = self.iss.update_freshness_from_build(
            self.root, self.index_dir, ["a.py", "new.txt"]
        )
        self.assertFalse(result["skipped"])
        self.assertEqual(result["written"], 2)

    def test_freshness_refresh_touches_no_lance_artifacts(self):
        """Differential guarantee (AC-4): the store write path never opens or
        mutates anything under the Lance table directories."""
        _init_git_repo(self.root)
        (self.root / "a.py").write_text("x=1\n")
        _commit_all(self.root, "c1")
        # Fake Lance table dirs with sentinel content + recorded stats.
        lance_docs = self.index_dir / "docs.lance"
        lance_docs.mkdir(parents=True)
        sentinel = lance_docs / "data.lance"
        sentinel.write_bytes(b"lance-bytes")
        before = {p: (p.stat().st_mtime_ns, p.stat().st_size)
                  for p in lance_docs.rglob("*")}
        self.iss.update_freshness_from_build(self.root, self.index_dir, ["a.py"])
        # Force a full (non-skip) rewrite too.
        (self.root / "a.py").write_text("x=2\n")
        _commit_all(self.root, "c2")
        self.iss.update_freshness_from_build(self.root, self.index_dir, ["a.py"])
        after = {p: (p.stat().st_mtime_ns, p.stat().st_size)
                 for p in lance_docs.rglob("*")}
        self.assertEqual(before, after)

    def test_reader_during_in_progress_transaction_sees_consistent_snapshot(self):
        """AC-5: WAL snapshot isolation — a reader mid-write-transaction sees the
        previous committed state, never an exception."""
        _init_git_repo(self.root)
        (self.root / "a.py").write_text("x=1\n")
        _commit_all(self.root, "c1")
        self.iss.update_freshness_from_build(self.root, self.index_dir, ["a.py"])
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            store._conn.execute("BEGIN IMMEDIATE")
            store._conn.execute("DELETE FROM file_freshness")
            store._conn.execute(
                "INSERT INTO file_freshness (path, last_modified, churn_score, "
                "commit_count, source, updated_at) VALUES ('mid.txn', 1, 0.9, 9, 'git', 1)"
            )
            # Uncommitted: the read-only connection must still see the old row.
            fresh = self.iss.freshness_for_path(self.index_dir, "a.py")
            self.assertIsNotNone(fresh)
            self.assertIsNone(self.iss.freshness_for_path(self.index_dir, "mid.txn"))
            store._conn.execute("ROLLBACK")
        finally:
            store.close()

    def test_update_never_raises_on_unwritable_index_dir(self):
        # Derived-only sidecar state must never fail a build (write path is
        # fail-safe: reports the error in the summary instead of raising).
        bad_dir = self.root / "not-a-dir"
        bad_dir.write_text("file blocks mkdir")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            summary = self.iss.update_freshness_from_build(
                self.root, bad_dir / "index", ["a.py"]
            )
        self.assertIn("error", summary)


class MaintenanceTests(_TempRepoCase):
    """AC-8: WAL bounded after builds; AC-9: reclaim across stores."""

    def test_wal_is_truncated_after_repeated_builds(self):
        _init_git_repo(self.root)
        wal = Path(str(self.iss.state_store_path(self.index_dir)) + "-wal")
        for i in range(3):
            (self.root / "a.py").write_text(f"x={i}\n")
            _commit_all(self.root, f"c{i}")
            self.iss.update_freshness_from_build(self.root, self.index_dir, ["a.py"])
            size = wal.stat().st_size if wal.exists() else 0
            self.assertEqual(size, 0, f"WAL not truncated after build {i}: {size} bytes")

    def test_optimize_state_stores_reclaims_delete_churned_store(self):
        store = self.iss.IndexStateStore(self.index_dir)
        big_rows = {
            f"path/{i}.py": {"last_modified": i, "churn_score": 0.1,
                             "commit_count": 1, "source": "git"}
            for i in range(5000)
        }
        store.apply_freshness(rows=big_rows)
        # Churn: replace with a tiny row set (mass delete).
        store.apply_freshness(rows={"one.py": {"last_modified": 1, "churn_score": 0.0,
                                               "commit_count": 0, "source": "git"}})
        store.close()
        results = self.iss.optimize_state_stores(self.index_dir, full_vacuum=True)
        res = results["index-state"]
        self.assertTrue(res["present"])
        self.assertEqual(res["integrity"], "ok")
        self.assertGreater(res["reclaimed_bytes"], 0)
        self.assertLess(res["size_after_bytes"], res["size_before_bytes"])

    def test_incremental_reclaim_drains_cursor_and_respects_page_bound(self):
        path = self.iss.state_store_path(self.index_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = self.iss.sqlite_runtime.connect(path)
        conn.execute("CREATE TABLE churn(id INTEGER PRIMARY KEY,payload BLOB)")
        with conn:
            conn.execute("WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<6000) "
                         "INSERT INTO churn SELECT x,zeroblob(4096) FROM n")
        with conn:
            conn.execute("DELETE FROM churn")
        before = conn.execute("PRAGMA freelist_count").fetchone()[0]
        self.assertGreater(before, self.iss.INCREMENTAL_VACUUM_PAGES)
        # Negative control reproduces the previous implementation: execute
        # alone only frees one page even though the requested limit is 5000.
        cursor = conn.execute(f"PRAGMA incremental_vacuum({self.iss.INCREMENTAL_VACUUM_PAGES})")
        cursor.close()
        after_control = conn.execute("PRAGMA freelist_count").fetchone()[0]
        self.assertEqual(before - after_control, 1)
        conn.close()
        result = self.iss.sqlite_store_maintenance(path, full_vacuum=False)
        self.assertIsNone(result["error"])
        conn = self.iss.sqlite_runtime.connect(path, read_only=True)
        after = conn.execute("PRAGMA freelist_count").fetchone()[0]
        conn.close()
        self.assertEqual(after_control - after, self.iss.INCREMENTAL_VACUUM_PAGES)
        self.assertGreater(after, 0)
        self.assertGreater(result["reclaimed_bytes"], 4096)

    def test_passive_checkpoint_reports_frames_pinned_by_reader(self):
        path = self.iss.state_store_path(self.index_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        writer = self.iss.sqlite_runtime.connect(path)
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("CREATE TABLE checkpoint_fixture(id INTEGER PRIMARY KEY,payload BLOB)")
        with writer:
            writer.execute("INSERT INTO checkpoint_fixture VALUES(1,zeroblob(4096))")
        reader = self.iss.sqlite_runtime.connect(path, read_only=True)
        try:
            reader.execute("BEGIN")
            self.assertEqual(reader.execute("SELECT count(*) FROM checkpoint_fixture").fetchone(), (1,))
            with writer:
                writer.execute("INSERT INTO checkpoint_fixture VALUES(2,zeroblob(4096))")
            result = self.iss.sqlite_store_maintenance(path, full_vacuum=False)
            checkpoint = result["checkpoint"]
            self.assertIsNone(result["error"])
            self.assertEqual(checkpoint["mode"], "PASSIVE")
            self.assertFalse(checkpoint["busy"])
            self.assertFalse(checkpoint["complete"])
            self.assertGreater(checkpoint["remaining_frames"], 0)
            self.assertEqual(reader.execute("SELECT count(*) FROM checkpoint_fixture").fetchone(), (1,))
        finally:
            reader.close()
            writer.close()

    def test_optimize_state_stores_reports_absent_stores_without_error(self):
        results = self.iss.optimize_state_stores(self.index_dir)
        self.assertFalse(results["index-state"]["present"])
        self.assertFalse(results["graph-state"]["present"])
        self.assertIsNone(results["index-state"]["error"])

    def test_optimize_covers_the_graph_state_store_file(self):
        """The unified verb reaches the graph store's sqlite file (on-demand
        maintenance only — no graph_indexer code is involved)."""
        graph_store = self.index_dir / self.iss.GRAPH_STATE_STORE_RELPATH
        graph_store.parent.mkdir(parents=True)
        conn = sqlite3.connect(str(graph_store))
        conn.execute("CREATE TABLE files (path TEXT PRIMARY KEY, record BLOB)")
        conn.executemany("INSERT INTO files VALUES (?, ?)",
                         [(f"f{i}", b"x" * 512) for i in range(2000)])
        conn.commit()
        conn.execute("DELETE FROM files")
        conn.commit()
        conn.close()
        results = self.iss.optimize_state_stores(self.index_dir, full_vacuum=True)
        res = results["graph-state"]
        self.assertTrue(res["present"])
        self.assertEqual(res["integrity"], "ok")
        self.assertGreater(res["reclaimed_bytes"], 0)

    def test_graph_state_store_relpath_matches_graph_indexer(self):
        """Wiring lock: the duplicated relative path stays in sync with
        graph_indexer's GRAPH_DIRNAME/GRAPH_STORE_FILENAMES constants."""
        src = (SCRIPTS_ROOT / "graph_indexer.py").read_text(encoding="utf-8")
        # GRAPH_DIRNAME = "graph"; GRAPH_STORE_FILENAMES["project"] = "project-graph-state.sqlite"
        dirname, filename = self.iss.GRAPH_STATE_STORE_RELPATH.split("/", 1)
        self.assertIn(f'GRAPH_DIRNAME = "{dirname}"', src)
        self.assertIn(f'"{filename}"', src)


class GraphVacuumMigrationTests(_TempRepoCase):
    def _graph(self, mode="NONE"):
        path = self.index_dir / self.iss.GRAPH_STATE_STORE_RELPATH
        path.parent.mkdir(parents=True)
        conn = sqlite3.connect(path)
        conn.execute(f"PRAGMA auto_vacuum={mode}")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE files(path TEXT PRIMARY KEY,source_hash TEXT,record BLOB)")
        conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT)")
        conn.execute("CREATE TABLE blobs(key TEXT PRIMARY KEY,value BLOB)")
        conn.execute("INSERT INTO meta VALUES('builder_version','keep-version')")
        conn.execute("INSERT INTO blobs VALUES('merge_state',x'001122')")
        conn.executemany("INSERT INTO files VALUES(?,?,?)",
                         [(f"p/{i}", f"hash-{i}", b"x" * 4096) for i in range(6000)])
        conn.commit()
        conn.execute("DELETE FROM files WHERE path != 'p/0'")
        conn.commit()
        conn.close()
        return path

    def _assert_preserved(self, path, mode):
        with closing(sqlite3.connect(path)) as conn:
            self.assertEqual(conn.execute("PRAGMA auto_vacuum").fetchone()[0], mode)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone(), ("ok",))
            self.assertEqual(conn.execute("SELECT * FROM files").fetchall(),
                             [("p/0", "hash-0", b"x" * 4096)])
            self.assertEqual(conn.execute("SELECT * FROM meta").fetchall(),
                             [("builder_version", "keep-version")])
            self.assertEqual(conn.execute("SELECT * FROM blobs").fetchall(),
                             [("merge_state", b"\x00\x11\x22")])

    def test_legacy_none_converts_once_and_later_reclaims_with_page_bound(self):
        path = self._graph()
        # Negative control: bounded incremental vacuum cannot reclaim a NONE store.
        with closing(sqlite3.connect(path)) as conn:
            before = conn.execute("PRAGMA freelist_count").fetchone()[0]
            self.assertGreater(before, self.iss.INCREMENTAL_VACUUM_PAGES)
            list(conn.execute("PRAGMA incremental_vacuum(5000)"))
            self.assertEqual(conn.execute("PRAGMA freelist_count").fetchone()[0], before)
        generic = self.iss.sqlite_store_maintenance(path)
        self.assertFalse(generic["auto_vacuum_migrated"])
        self.assertEqual(generic["auto_vacuum_after"], 0)
        first = self.iss.optimize_state_stores(self.index_dir, full_vacuum=False)["graph-state"]
        self.assertTrue(first["maintenance_complete"], first)
        self.assertTrue(first["auto_vacuum_migrated"])
        self.assertEqual((first["auto_vacuum_before"], first["auto_vacuum_after"]), (0, 2))
        self.assertEqual(first["vacuum_mode"], "graph_migration")
        self.assertGreater(first["reclaimed_bytes"], 4096)
        self._assert_preserved(path, 2)
        with closing(sqlite3.connect(path)) as conn:
            conn.executemany("INSERT INTO files VALUES(?,?,?)",
                             [(f"p/{i}", "h", b"x" * 4096) for i in range(1, 6000)])
            conn.commit()
            conn.execute("DELETE FROM files WHERE path != 'p/0'")
            conn.commit()
            before = conn.execute("PRAGMA freelist_count").fetchone()[0]
        second = self.iss.optimize_state_stores(self.index_dir, full_vacuum=False)["graph-state"]
        self.assertTrue(second["maintenance_complete"], second)
        self.assertFalse(second["auto_vacuum_migrated"])
        self.assertEqual(second["vacuum_mode"], "incremental")
        with closing(sqlite3.connect(path)) as conn:
            after = conn.execute("PRAGMA freelist_count").fetchone()[0]
        self.assertEqual(before - after, self.iss.INCREMENTAL_VACUUM_PAGES)
        self.assertGreater(after, 0)  # A second full VACUUM would empty the freelist.
        self._assert_preserved(path, 2)

    def test_full_mode_converts_without_full_vacuum(self):
        path = self._graph("FULL")
        real_connect = sqlite3.connect
        def refuse_full_vacuum(*args, **kwargs):
            return _FlakyConn(real_connect(*args, **kwargs), "VACUUM",
                              sqlite3.OperationalError("unexpected full VACUUM"))
        with mock.patch.object(self.iss.sqlite3, "connect", side_effect=refuse_full_vacuum):
            result = self.iss.optimize_state_stores(self.index_dir, full_vacuum=False)["graph-state"]
        self.assertTrue(result["maintenance_complete"], result)
        self.assertTrue(result["auto_vacuum_migrated"])
        self.assertEqual(result["vacuum_mode"], "incremental")
        self._assert_preserved(path, 2)

    def test_failed_vacuum_preserves_original_store_and_reports_retryable_stage(self):
        path = self._graph()
        real_connect = sqlite3.connect
        def fail_vacuum(*args, **kwargs):
            return _FlakyConn(real_connect(*args, **kwargs), "VACUUM",
                              sqlite3.OperationalError("disk I/O error"))
        with mock.patch.object(self.iss.sqlite3, "connect", side_effect=fail_vacuum):
            result = self.iss.optimize_state_stores(self.index_dir, full_vacuum=False)["graph-state"]
        self.assertFalse(result["maintenance_complete"])
        self.assertFalse(result["auto_vacuum_migrated"])
        self.assertEqual(result["error_stage"], "graph_vacuum_migration")
        self.assertEqual(result["error"], "disk I/O error")
        self.assertEqual(result["integrity"], "ok")
        self._assert_preserved(path, 0)
        retry = self.iss.optimize_state_stores(self.index_dir, full_vacuum=False)["graph-state"]
        self.assertTrue(retry["maintenance_complete"], retry)
        self._assert_preserved(path, 2)

    def test_generic_maintenance_does_not_convert_unowned_database(self):
        graph = self._graph()
        source = graph
        for path in (graph.with_name("other.sqlite"), graph.parent.with_name("unowned") / graph.name):
            with self.subTest(path=path):
                path.parent.mkdir(parents=True, exist_ok=True)
                source.rename(path)
                source = path
                result = self.iss.sqlite_store_maintenance(path, migrate_graph_vacuum=True)
                self.assertTrue(result["maintenance_complete"], result)
                self.assertFalse(result["auto_vacuum_migrated"])
                self.assertEqual(result["vacuum_mode"], "none")
                self._assert_preserved(path, 0)

    def test_concurrent_writer_refuses_conversion_without_damaging_store(self):
        path = self._graph()
        real_connect = sqlite3.connect
        class NoWait(_FlakyConn):
            def execute(self, sql, *args, **kwargs):
                if sql == "PRAGMA busy_timeout=10000":
                    sql = "PRAGMA busy_timeout=0"
                return self._real.execute(sql, *args, **kwargs)
        def no_wait(*args, **kwargs):
            return NoWait(real_connect(*args, **kwargs), "unused", None)
        with closing(real_connect(path)) as writer:
            writer.execute("BEGIN IMMEDIATE")
            try:
                with mock.patch.object(self.iss.sqlite3, "connect", side_effect=no_wait):
                    result = self.iss.optimize_state_stores(self.index_dir, full_vacuum=False)["graph-state"]
                self.assertFalse(result["maintenance_complete"])
                self.assertFalse(result["auto_vacuum_migrated"])
                self.assertIn("locked", result["error"])
                self.assertEqual(result["error_stage"], "graph_vacuum_migration")
                self.assertEqual(result["integrity"], "ok")
            finally:
                writer.rollback()
        self._assert_preserved(path, 0)

    def test_wal_reader_snapshot_survives_conversion_and_pinned_checkpoint_is_reported(self):
        path = self._graph()
        with closing(sqlite3.connect(path)) as writer, closing(sqlite3.connect(path)) as reader:
            writer.execute("PRAGMA wal_autocheckpoint=0")
            reader.execute("BEGIN")
            self.assertEqual(reader.execute("SELECT count(*) FROM files").fetchone(), (1,))
            writer.execute("INSERT INTO files VALUES('temporary','hash',zeroblob(4096))")
            writer.commit()
            writer.execute("DELETE FROM files WHERE path='temporary'")
            writer.commit()
            result = self.iss.optimize_state_stores(self.index_dir, full_vacuum=False)["graph-state"]
            self.assertTrue(result["maintenance_complete"], result)
            self.assertTrue(result["auto_vacuum_migrated"])
            self.assertGreater(result["checkpoint"]["remaining_frames"], 0)
            self.assertFalse(result["checkpoint"]["complete"])
            self.assertEqual(reader.execute("SELECT count(*) FROM files").fetchone(), (1,))
            reader.rollback()
        self._assert_preserved(path, 2)

    def test_integrity_failure_stops_before_conversion(self):
        path = self._graph()
        real_connect = sqlite3.connect
        traced = []
        class BadCheck(_FlakyConn):
            def execute(self, sql, *args, **kwargs):
                traced.append(sql)
                if sql == "PRAGMA integrity_check":
                    return self._real.execute("SELECT 'broken page'")
                return self._real.execute(sql, *args, **kwargs)
        def fail_integrity(*args, **kwargs):
            return BadCheck(real_connect(*args, **kwargs), "unused", None)
        with mock.patch.object(self.iss.sqlite3, "connect", side_effect=fail_integrity):
            result = self.iss.optimize_state_stores(self.index_dir, full_vacuum=False)["graph-state"]
        self.assertFalse(result["maintenance_complete"])
        self.assertEqual(result["integrity"], "structural-fail")
        self.assertEqual(result["error_stage"], "integrity_check")
        self.assertFalse(any("vacuum" in sql.lower() for sql in traced))
        self._assert_preserved(path, 0)


def _corrupt_sqlite_file(path: Path) -> None:
    """Byte-corrupt a sqlite file so ``quick_check`` fails structurally.

    Cells grow from the END of each page, so XOR-ing the tail of every page
    mangles real b-tree content (corrupting mid-page bytes can land in free
    space, which quick_check legitimately ignores). The 100-byte header is
    left intact so the file still opens as a database.
    """
    data = bytearray(path.read_bytes())
    page = 4096
    for start in range(0, len(data), page):
        end = min(start + page, len(data))
        for i in range(max(start + page - 512, 128), end):
            data[i] ^= 0xFF
    for suffix in ("-wal", "-shm"):
        try:
            os.unlink(f"{path}{suffix}")
        except OSError:
            pass
    path.write_bytes(bytes(data))


class IntegrityProbeTests(_TempRepoCase):
    """AC-10: two-layer probe — structural and stale-fingerprint — plus recovery."""

    def _built_store(self):
        _init_git_repo(self.root)
        (self.root / "a.py").write_text("x=1\n")
        _commit_all(self.root, "c1")
        self.iss.update_freshness_from_build(self.root, self.index_dir, ["a.py"])

    def test_clean_store_probes_ok(self):
        self._built_store()
        probe = self.iss.probe_state_store(self.root, self.index_dir)
        self.assertEqual(probe["status"], "ok")
        self.assertEqual(probe["schema_version"], self.iss.STATE_STORE_SCHEMA_VERSION)
        deep = self.iss.probe_state_store(self.root, self.index_dir, deep=True)
        self.assertEqual(deep["status"], "ok")
        self.assertEqual(deep["detail"], "integrity_check")

    def test_byte_corrupt_store_reports_structural_fail_and_preserves(self):
        self._built_store()
        path = self.iss.state_store_path(self.index_dir)
        _corrupt_sqlite_file(path)
        before = path.read_bytes()
        self.assertEqual(self.iss.probe_state_store(self.root, self.index_dir)["status"], "structural-fail")
        with redirect_stderr(io.StringIO()):
            summary = self.iss.update_freshness_from_build(self.root,self.index_dir,["a.py"])
        self.assertEqual(summary["written"], 0)
        self.assertEqual(path.read_bytes(), before)

    def test_stale_fingerprint_is_detected_without_structural_error(self):
        self._built_store()
        # Advance HEAD after the store was written: structurally sound, logically stale.
        (self.root / "a.py").write_text("x=2\n")
        _commit_all(self.root, "c2")
        probe = self.iss.probe_state_store(self.root, self.index_dir)
        self.assertEqual(probe["status"], "stale-fingerprint")
        # The next build refreshes it back to ok.
        self.iss.update_freshness_from_build(self.root, self.index_dir, ["a.py"])
        self.assertEqual(
            self.iss.probe_state_store(self.root, self.index_dir)["status"], "ok"
        )

    def test_maintenance_pass_reports_structural_fail_on_corrupt_store(self):
        self._built_store()
        path = self.iss.state_store_path(self.index_dir)
        _corrupt_sqlite_file(path)
        res = self.iss.sqlite_store_maintenance(path, deep_integrity=True)
        self.assertEqual(res["integrity"], "structural-fail")


class IndexerWiringTests(unittest.TestCase):
    """Source-assertion wiring locks: the build path calls the store update."""

    def test_build_index_locked_wires_store_flow_after_meta_build(self):
        """1sed6 build-end order: bookkeeping write (sole state authority; no
        meta.json write) → stranded-row reap → chunk-index reconcile →
        freshness update → attempt-ID-matched epoch finalize → legacy
        meta.json removal (all inside the build lock; the reap precedes the
        reconcile so FTS/registry never retain reaped content between
        builds, and the legacy JSON disappears only after a verified
        complete epoch)."""
        src = (SCRIPTS_ROOT / "indexer.py").read_text(encoding="utf-8")
        transaction_pos = src.index("# One native writer transaction publishes")
        bookkeeping_pos = src.index("write_build_bookkeeping_locked(conn,new_meta)", transaction_pos)
        commit_pos = src.index('conn.execute("COMMIT")', bookkeeping_pos)
        reconcile_pos = src.index("_sync_chunk_derived_state(", commit_pos)
        update_pos = src.index("update_freshness_from_build(", reconcile_pos)
        finalize_pos = src.index("finalize_build_epoch(index_dir, _build_attempt)", update_pos)
        legacy_pos = src.index("_remove_legacy_meta_json(index_dir)", finalize_pos)
        self.assertGreater(legacy_pos, finalize_pos)
        self.assertNotIn("def _save_meta(", src)
        loader_pos = src.index("def _get_index_state_store()")
        self.assertGreater(loader_pos, 0)

    def test_setup_optimize_after_build_uses_one_unified_store_pass(self):
        import setup_index
        spec = importlib.util.spec_from_file_location("_indexer_maintenance_fixture", SCRIPTS_ROOT / "indexer.py")
        indexer = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = indexer
        spec.loader.exec_module(indexer)
        iss = load_store_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index_dir = root / ".wavefoundry/index"
            attempt = iss.begin_build_epoch(index_dir, "fixture")
            self.assertTrue(iss.finalize_build_epoch(index_dir, attempt))
            graph = index_dir / iss.GRAPH_STATE_STORE_RELPATH
            graph.parent.mkdir(parents=True)
            conn = iss.sqlite_runtime.connect(graph)
            conn.execute("CREATE TABLE files(path TEXT PRIMARY KEY)")
            conn.close()
            with mock.patch.object(setup_index, "_load_indexer_module", return_value=indexer), \
                 mock.patch.object(indexer, "_get_index_state_store", return_value=iss), \
                 mock.patch.object(iss, "sqlite_store_maintenance", wraps=iss.sqlite_store_maintenance) as maintenance:
                setup_index._optimize_after_build(root)
            self.assertCountEqual([call.args[0] for call in maintenance.call_args_list],
                                  [iss.state_store_path(index_dir), graph])
            self.assertTrue(all(call.kwargs["full_vacuum"] is False for call in maintenance.call_args_list))
            self.assertEqual(iss.read_build_state(index_dir)["status"], "complete")


class BuildEpochTests(_TempRepoCase):
    """1sed6: the build-epoch state machine — FULL-durable pre-mutation fence,
    attempt-ID compare-and-set finalization, fail-closed reader token."""

    def setUp(self):
        super().setUp()
        self.iss = load_store_module()
        self.index_dir = self.root / ".wavefoundry" / "index"
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def test_absent_store_fails_closed(self):
        self.assertIsNone(self.iss.read_build_state(self.index_dir))
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_fresh_store_is_uninitialized_and_not_ready(self):
        self.iss.write_build_bookkeeping(self.index_dir, {"built_at": "x"})
        state = self.iss.read_build_state(self.index_dir)
        self.assertEqual(state["status"], "uninitialized")
        self.assertEqual(state["generation"], 0)
        # Bookkeeping alone never publishes readiness (fail closed).
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_begin_marks_building_and_token_stays_none(self):
        attempt = self.iss.begin_build_epoch(self.index_dir, "code:test")
        state = self.iss.read_build_state(self.index_dir)
        self.assertEqual(state["status"], "building")
        self.assertEqual(state["attempt_id"], attempt)
        self.assertEqual(state["scope"], "code:test")
        self.assertIsNotNone(state["started_at"])
        self.assertIsNone(state["completed_at"])
        # An in-flight (or crashed) build is never a servable epoch.
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_finalize_cas_advances_generation_exactly_once(self):
        attempt = self.iss.begin_build_epoch(self.index_dir, "all")
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, attempt))
        state = self.iss.read_build_state(self.index_dir)
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["generation"], 1)
        self.assertIsNotNone(state["completed_at"])
        self.assertEqual(
            self.iss.build_epoch_token(self.index_dir), (attempt, 1)
        )
        # Re-presenting the same attempt after completion is a CAS miss —
        # only a `building` row for this attempt can complete.
        self.assertFalse(self.iss.finalize_build_epoch(self.index_dir, attempt))
        self.assertEqual(self.iss.read_build_state(self.index_dir)["generation"], 1)

    def test_wrong_attempt_never_publishes(self):
        self.iss.begin_build_epoch(self.index_dir, "docs")
        self.assertFalse(self.iss.finalize_build_epoch(self.index_dir, "not-the-attempt"))
        state = self.iss.read_build_state(self.index_dir)
        self.assertEqual(state["status"], "building")
        self.assertEqual(state["generation"], 0)
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))

    def test_superseded_attempt_loses_the_cas(self):
        first = self.iss.begin_build_epoch(self.index_dir, "code")
        second = self.iss.begin_build_epoch(self.index_dir, "code")
        # The superseded build must not publish over the newer fence.
        self.assertFalse(self.iss.finalize_build_epoch(self.index_dir, first))
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, second))
        self.assertEqual(
            self.iss.build_epoch_token(self.index_dir), (second, 1)
        )

    def _write_checkpoint(self, payload: dict) -> None:
        checkpoint = self.root / ".wavefoundry" / "upgrade-in-progress.json"
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        checkpoint.write_text(json.dumps(payload), encoding="utf-8")

    def test_value_bound_publisher_grant_admits_phase4_child_at_any_phase(self):
        """1u44m red-first (AC-1): a non-owner Phase 4 child holding the
        value-bound publisher grant is ADMITTED at ``begin_build_epoch`` and
        completes the epoch, with the checkpoint's ``current_phase`` held
        constant across both field values, so the pass cannot be attributed
        to the phase. Owner disjunct defeated via ``"pid": -1``; the staged
        receipt env var is cleared so the presence-bound disjunct cannot
        vacuously admit."""
        token = "grant-token-1u44m"
        for phase in ("awaiting_memory_validation", "index_update"):
            with self.subTest(phase=phase):
                phase_root = self.root / phase.replace("_", "-")
                index_dir = phase_root / ".wavefoundry" / "index"
                checkpoint = (
                    phase_root / ".wavefoundry" / "upgrade-in-progress.json"
                )
                checkpoint.parent.mkdir(parents=True, exist_ok=True)
                checkpoint.write_text(
                    json.dumps(
                        {
                            "current_phase": phase,
                            "pid": -1,
                            "publisher_grant": token,
                            "memory_backfill_pending": 0,
                        }
                    ),
                    encoding="utf-8",
                )
                # Geometry guard: the store derives the repo root as
                # index_dir.parent.parent, so the checkpoint above is the one
                # the guard reads. Prove it: without the grant this refuses.
                with mock.patch.dict(os.environ, {}, clear=False):
                    os.environ.pop(
                        "WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT", None
                    )
                    os.environ.pop(
                        "WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN", None
                    )
                    with self.assertRaisesRegex(
                        RuntimeError, "upgrade_in_progress"
                    ):
                        self.iss.begin_build_epoch(index_dir, "docs")
                with mock.patch.dict(os.environ, {}, clear=False):
                    os.environ.pop(
                        "WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT", None
                    )
                    os.environ.pop("WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID", None)
                    os.environ["WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"] = token
                    attempt = self.iss.begin_build_epoch(index_dir, "docs")
                    self.assertTrue(
                        self.iss.finalize_build_epoch(index_dir, attempt)
                    )
                state = self.iss.read_build_state(index_dir)
                self.assertEqual(state["status"], "complete")
                self.assertEqual(state["generation"], 1)

    def test_publisher_grant_is_value_bound_not_presence_bound(self):
        """A mismatched or unrecorded token never admits: the grant must MATCH
        the checkpoint's recorded ``publisher_grant`` (a stale copy leaked into
        the detached background child dies with this checkpoint)."""
        self._write_checkpoint(
            {
                "current_phase": "index_update",
                "pid": -1,
                "publisher_grant": "the-real-token",
                "memory_backfill_pending": 0,
            }
        )
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT", None)
            os.environ.pop("WAVEFOUNDRY_MEMORY_BACKFILL_RUN_ID", None)
            os.environ["WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"] = "a-stale-token"
            with self.assertRaisesRegex(RuntimeError, "upgrade_in_progress"):
                self.iss.begin_build_epoch(self.index_dir, "docs")
        # A token in the environment with NO recorded grant in the checkpoint
        # is refused too (presence alone must never admit).
        self._write_checkpoint({"current_phase": "index_update", "pid": -1})
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT", None)
            os.environ["WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN"] = "any-token"
            with self.assertRaisesRegex(RuntimeError, "upgrade_in_progress"):
                self.iss.begin_build_epoch(self.index_dir, "docs")

    def test_ungranted_non_owner_stays_refused_at_both_phases(self):
        """Negative control: with no grant env var and the receipt env var
        cleared, a non-owner is refused regardless of ``current_phase`` (the
        pre-1u44m field baseline, preserved for callers without status)."""
        for phase in ("awaiting_memory_validation", "index_update"):
            with self.subTest(phase=phase):
                self._write_checkpoint(
                    {
                        "current_phase": phase,
                        "pid": -1,
                        "memory_backfill_pending": 0,
                    }
                )
                with mock.patch.dict(os.environ, {}, clear=False):
                    os.environ.pop(
                        "WAVEFOUNDRY_UPGRADE_PARENT_FINALIZE_RECEIPT", None
                    )
                    os.environ.pop(
                        "WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN", None
                    )
                    with self.assertRaisesRegex(
                        RuntimeError, "upgrade_in_progress"
                    ):
                        self.iss.begin_build_epoch(self.index_dir, "docs")

    def test_parent_staged_receipt_keeps_strict_shape_attempt_and_generation(self):
        import memory_backfill

        attempt = self.iss.begin_build_epoch(self.index_dir, "all")
        receipt = {
            "index_dir": str(self.index_dir.resolve()),
            "attempt_id": attempt,
            "expected_generation": 1,
            "memory_backfill_run_id": "run-1",
        }
        for mutation in (
            {**receipt, "unexpected": True},
            {**receipt, "attempt_id": "other-attempt"},
            {**receipt, "expected_generation": 2},
            {**receipt, "memory_backfill_run_id": "other-run"},
        ):
            with self.subTest(mutation=mutation):
                self.assertFalse(
                    self.iss.finalize_staged_build_epoch(
                        self.index_dir, mutation, "run-1"
                    )
                )
                self.assertEqual(
                    self.iss.read_build_state(self.index_dir)["status"],
                    "building",
                )

        with mock.patch.object(
            memory_backfill, "record_publication_success", return_value=True
        ) as record:
            self.assertTrue(
                self.iss.finalize_staged_build_epoch(
                    self.index_dir, receipt, "run-1"
                )
            )
        record.assert_called_once_with(self.root, "run-1", attempt)
        self.assertFalse(
            self.iss.finalize_staged_build_epoch(
                self.index_dir, receipt, "run-1"
            )
        )

    def test_token_changes_across_generations(self):
        a1 = self.iss.begin_build_epoch(self.index_dir, "all")
        self.iss.finalize_build_epoch(self.index_dir, a1)
        tok1 = self.iss.build_epoch_token(self.index_dir)
        a2 = self.iss.begin_build_epoch(self.index_dir, "all")
        # Seqlock window: token vanishes while building...
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        self.iss.finalize_build_epoch(self.index_dir, a2)
        tok2 = self.iss.build_epoch_token(self.index_dir)
        # ...and never repeats after completion.
        self.assertNotEqual(tok1, tok2)
        self.assertEqual(tok2[1], tok1[1] + 1)

    def test_bookkeeping_and_reconcile_never_advance_generation(self):
        attempt = self.iss.begin_build_epoch(self.index_dir, "all")
        self.iss.finalize_build_epoch(self.index_dir, attempt)
        before = self.iss.read_build_state(self.index_dir)["generation"]
        self.iss.write_build_bookkeeping(self.index_dir, {"built_at": "y", "file_meta": {}})
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            self.iss.reconcile_chunk_index(self.index_dir, "code", set(), lambda: [])
        self.assertEqual(
            self.iss.read_build_state(self.index_dir)["generation"], before,
            "only finalize_build_epoch may advance the generation",
        )

    def test_interrupted_build_survives_process_restart_as_not_ready(self):
        """Crash simulation: fence committed, process dies before finalize —
        a FRESH module load (new connections) still sees building/None."""
        self.iss.begin_build_epoch(self.index_dir, "code:crashed")
        fresh = load_store_module()
        state = fresh.read_build_state(self.index_dir)
        self.assertEqual(state["status"], "building")
        self.assertIsNone(fresh.build_epoch_token(self.index_dir))

    def test_read_build_summary_is_bounded(self):
        """Review fix: the dashboard/status read returns scalars + file COUNT,
        never per-file rows."""
        self.iss.write_build_bookkeeping(self.index_dir, {
            "built_at": "2026-07-12T00:00:00Z",
            "model_versions": {"docs": "m@full"},
            "chunker_versions": {"docs": "31"},
            "walker_version": "6",
            "content": ["docs"],
            "file_meta": {f"f{i}.md": {"hash": "h", "mtime": 1.0, "size": 1, "inode": i}
                          for i in range(50)},
        })
        summary = self.iss.read_build_summary(self.index_dir)
        self.assertEqual(summary["file_count"], 50)
        self.assertEqual(summary["built_at"], "2026-07-12T00:00:00Z")
        self.assertEqual(summary["model_versions"], {"docs": "m@full"})
        self.assertNotIn("file_meta", summary)
        self.assertIsNone(self.iss.read_build_summary(self.index_dir / "nope"))

    def test_boundary_commits_are_full_durable(self):
        """Structural durability pin: both safety-critical boundary commits
        (fence + CAS) go through the dedicated FULL-synchronous connection;
        the store's ordinary NORMAL posture is unchanged elsewhere."""
        src = STORE_PATH.read_text(encoding="utf-8")
        helper = src.index("def _full_durable_connection(")
        conn = self.iss._full_durable_connection(self.index_dir)
        try:
            self.assertEqual(conn.execute("PRAGMA synchronous").fetchone(), (2,))
        finally:
            conn.close()
        begin = src.index("def begin_build_epoch(")
        self.assertIn("_full_durable_connection(", src[begin:src.index("def finalize_build_epoch(")])
        fin = src.index("def finalize_build_epoch(")
        self.assertIn("_full_durable_connection(", src[fin:src.index("def read_build_state(")])


class ChunkIdCollisionCensusTests(_TempRepoCase):
    """1wngv (wave 1wpif) AC-1/AC-5/AC-9: same-ID/distinct-content census.

    The detector consumes the SAME materialized rows the derived rebuild
    already consumes (the store's `chunk_sync_raw`/`unique` counters and the
    reconcile-time row fetch are the existing O(total chunks) source); the
    synthetic growing corpus proves SCALING only, never defines the detector.
    AC-5's collision is injected at the store-row layer because the fixed
    chunker can no longer emit one.
    """

    def _rows(self):
        # Injected same-ID/distinct-content pair plus a clean row and a
        # same-ID/SAME-content churn duplicate (NOT a collision).
        return [
            {"id": "a.py#x", "path": "a.py", "kind": "code", "language": "python",
             "lines": [1, 3], "text": "alpha", "chunk_hash": "h1"},
            {"id": "a.py#x", "path": "a.py", "kind": "code", "language": "python",
             "lines": [5, 7], "text": "beta", "chunk_hash": "h2"},
            {"id": "a.py#y", "path": "a.py", "kind": "code", "language": "python",
             "lines": [9, 11], "text": "gamma", "chunk_hash": "h3"},
            {"id": "a.py#y", "path": "a.py", "kind": "code", "language": "python",
             "lines": [9, 11], "text": "gamma", "chunk_hash": "h3"},
        ]

    def test_census_detects_distinct_content_and_skips_churn_duplicates(self):
        census = self.iss.chunk_id_collision_census(self._rows())
        self.assertEqual(census["rows_visited"], 4)
        self.assertEqual(census["collision_count"], 1)
        self.assertEqual(census["collision_ids"], ["a.py#x"])

    def test_census_row_visits_scale_linearly(self):
        # AC-9 countable: doubling the corpus doubles row visits exactly
        # (one visit per row; keyed state, no nested passes).
        def corpus(n):
            return [{"id": f"f{i % 50}.py#s{i}", "chunk_hash": f"h{i}"} for i in range(n)]
        small = self.iss.chunk_id_collision_census(corpus(400))
        large = self.iss.chunk_id_collision_census(corpus(800))
        self.assertEqual(small["rows_visited"], 400)
        self.assertEqual(large["rows_visited"], 800)

    def test_hashless_rows_cannot_prove_distinct_content(self):
        rows = [{"id": "a#x", "chunk_hash": ""}, {"id": "a#x", "chunk_hash": "h1"}]
        self.assertEqual(self.iss.chunk_id_collision_census(rows)["collision_count"], 0)

    def test_rebuild_records_census_and_reconcile_warns(self):
        # AC-5: injected store-row collision → recorded meta, reconcile
        # result carries it, and an explicit warning reaches stderr.
        rows = self._rows()
        import contextlib
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), contextlib.redirect_stdout(out):
            result = self.iss.reconcile_chunk_index(
                self.index_dir, "code", {r["id"] for r in rows},
                lambda: list(rows), raw_rows=len(rows),
            )
        self.assertTrue(result["reconciled"])
        self.assertEqual(result.get("id_collisions"), 1)
        self.assertEqual(result.get("id_collision_sample"), ["a.py#x"])
        self.assertIn("chunk-id collision census", err.getvalue())
        count, sample = self.iss.chunk_id_collision_counts(self.index_dir, "code")
        self.assertEqual((count, sample), (1, ["a.py#x"]))
        # The in-sync fast path re-reports the persisted census: an in-sync
        # id SET cannot clear a collision the id set is blind to.
        with redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            second = self.iss.reconcile_chunk_index(
                self.index_dir, "code", {r["id"] for r in rows},
                lambda: list(rows), raw_rows=len(rows),
            )
        self.assertTrue(second["in_sync"])
        self.assertEqual(second.get("id_collisions"), 1)

    def test_clean_rebuild_records_zero_census(self):
        rows = [r for r in self._rows() if r["chunk_hash"] == "h3"][:1]
        self.iss.rebuild_chunk_index(self.index_dir, "code", rows)
        count, sample = self.iss.chunk_id_collision_counts(self.index_dir, "code")
        self.assertEqual((count, sample), (0, []))

    def test_census_consumes_the_materialized_rebuild_rows(self):
        # AC-9 countable: the detector runs over exactly the rows the rebuild
        # materialized (one visit each) — never a second repository pass —
        # and touching a chunker or embedder module would blow up loudly.
        rows = self._rows()

        class _Sentinel:
            def __getattr__(self, name):
                raise AssertionError(f"census must not touch {name!r}")

        with mock.patch.object(
            self.iss, "chunk_id_collision_census",
            wraps=self.iss.chunk_id_collision_census,
        ) as spy:
            with mock.patch.dict(
                sys.modules,
                {"chunker": _Sentinel(), "accel_embedder": _Sentinel()},
            ):
                self.iss.rebuild_chunk_index(self.index_dir, "code", list(rows))
        spy.assert_called_once()
        seen = spy.call_args[0][0]
        self.assertEqual(seen, rows)
        self.assertEqual(spy.call_args[0].__len__(), 1)

    def test_census_overhead_within_advisory_bound(self):
        """AC-9 advisory wall-clock bound. Protocol (declared BEFORE
        measurement): paired same-process runs of ``rebuild_chunk_index``
        over identical synthetic rows into fresh temp stores, census active
        versus census patched to a constant no-op, interleaved, three
        measured repetitions each, MEDIAN compared; bound 10%. The countable
        assertions above are the primary oracle — this measurement is
        advisory evidence and the generous bound reflects that."""
        import statistics
        rows = [
            {"id": f"src/f{i % 100}.py::sym{i}", "path": f"src/f{i % 100}.py",
             "kind": "code", "language": "python", "lines": [i, i + 2],
             "text": f"def sym{i}(): return {i}", "chunk_hash": f"h{i}"}
            for i in range(2000)
        ]
        noop = {"rows_visited": 0, "collision_count": 0, "collision_ids": []}

        def run_once(patched: bool) -> float:
            with tempfile.TemporaryDirectory() as td:
                target = Path(td)
                if patched:
                    ctx = mock.patch.object(
                        self.iss, "chunk_id_collision_census", return_value=noop
                    )
                else:
                    ctx = mock.patch.object(
                        self.iss, "chunk_id_collision_census",
                        wraps=self.iss.chunk_id_collision_census,
                    )
                with ctx:
                    t0 = time.perf_counter()
                    self.iss.rebuild_chunk_index(target, "code", list(rows))
                    return time.perf_counter() - t0

        run_once(True); run_once(False)  # warm both paths
        with_census, without_census = [], []
        for _ in range(3):
            without_census.append(run_once(True))
            with_census.append(run_once(False))
        ratio = statistics.median(with_census) / statistics.median(without_census)
        self.assertLessEqual(
            ratio, 1.10,
            f"census overhead {ratio:.3f} exceeds the 10% advisory bound "
            f"(with={with_census}, without={without_census})",
        )


class LexicalStatisticsTests(_TempRepoCase):
    """Published FTS aggregates and the strictly bounded dashboard reader."""

    def setUp(self):
        super().setUp()
        if not self.iss.fts5_available():
            self.skipTest("SQLite FTS5 unavailable")

    def row(self, id, text):
        return {"id": id, "path": "unindexed_path", "tags": "unindexed_tag",
                "kind": "unindexed_kind", "language": "unindexed_language", "text": text}

    def populate(self):
        attempt = self.iss.begin_build_epoch(self.index_dir, "all")
        self.iss.rebuild_chunk_index(self.index_dir, "docs", [
            self.row("d1", "alpha alpha beta keep_together"), self.row("d2", "beta gamma")])
        self.iss.rebuild_chunk_index(self.index_dir, "code", [self.row("c1", "alpha delta")])
        self.assertTrue(self.iss.finalize_build_epoch(self.index_dir, attempt))
        return attempt

    def assert_no_counts(self, payload, status=None):
        if status:
            self.assertEqual(payload["status"], status)
        for key in ("entries", "term_occurrences", "distinct_terms"):
            self.assertNotIn(key, payload)

    def cache(self):
        conn = self.iss.open_read_only(self.index_dir)
        try:
            return json.loads(self.iss.IndexStateStore._get_meta(conn, self.iss.META_LEXICAL_STATISTICS))
        finally:
            conn.close()

    def put_cache(self, value):
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            store.set_meta({self.iss.META_LEXICAL_STATISTICS: json.dumps(value)})
        finally:
            store.close()

    def test_overlap_repetitions_underscore_and_unindexed_fields(self):
        self.populate()
        payload = self.iss.lexical_statistics(self.index_dir)
        self.assertEqual(payload, {"status": "ready", "engine": "SQLite FTS5", "ranking": "BM25",
            "tokenizer": "unicode61 tokenchars '_'", "entries": 3, "term_occurrences": 8, "distinct_terms": 5})

    def test_empty_one_table_and_tokenless_entries(self):
        attempt = self.iss.begin_build_epoch(self.index_dir, "all")
        self.iss.finalize_build_epoch(self.index_dir, attempt)
        self.assert_no_counts(self.iss.lexical_statistics(self.index_dir), "not_built")
        self.assertEqual(self.iss.lexical_statistics(self.index_dir)["reason"], "empty_corpus")
        for content, expected in (("alpha alpha", (2, 1)), ("", (0, 0))):
            attempt = self.iss.begin_build_epoch(self.index_dir, "docs")
            self.iss.apply_chunk_deltas(self.index_dir, "docs", add_rows=[self.row("one", content)])
            self.iss.finalize_build_epoch(self.index_dir, attempt)
            payload = self.iss.lexical_statistics(self.index_dir)
            self.assertEqual(payload["entries"], 1)
            self.assertEqual((payload["term_occurrences"], payload["distinct_terms"]), expected)

    def test_replacement_delete_and_rebuild_invalidate_atomically(self):
        self.populate()
        self.iss.apply_chunk_deltas(self.index_dir, "docs", add_rows=[self.row("d1", "zeta")], delete_ids=["d2"])
        self.assert_no_counts(self.iss.lexical_statistics(self.index_dir))
        attempt = self.iss.begin_build_epoch(self.index_dir, "docs")
        self.iss.finalize_build_epoch(self.index_dir, attempt)
        payload = self.iss.lexical_statistics(self.index_dir)
        self.assertEqual((payload["entries"], payload["term_occurrences"], payload["distinct_terms"]), (2, 3, 3))
        self.iss.rebuild_chunk_index(self.index_dir, "code", [])
        self.assert_no_counts(self.iss.lexical_statistics(self.index_dir))

    def test_absent_legacy_disabled_and_capability_transition(self):
        self.assert_no_counts(self.iss.lexical_statistics(self.index_dir), "not_built")
        self.assertFalse(self.index_dir.exists())
        self.populate()
        store = self.iss.IndexStateStore(self.index_dir)
        store.delete_meta([self.iss.META_LEXICAL_STATISTICS])
        store.close()
        self.assertEqual(self.iss.lexical_statistics(self.index_dir)["reason"], "statistics_not_built")
        with mock.patch.object(self.iss, "fts5_available", return_value=False):
            self.assert_no_counts(self.iss.lexical_statistics(self.index_dir), "unavailable")
        self.assert_no_counts(self.iss.lexical_statistics(self.index_dir), "not_built")
        store = self.iss.IndexStateStore(self.index_dir)
        self.assertIsNone(store.get_meta(self.iss.META_LEXICAL_STATISTICS))
        store.close()

    def test_in_progress_stale_and_malformed_cache(self):
        self.populate()
        valid = self.cache()
        for key, bad_values in {"entries": [True, -1, 1.5, "3"], "term_occurrences": [False, -1, 2.5],
                                "distinct_terms": [True, -1, 99], "version": [True, 99],
                                "generation": [False, -1, 1.5], "attempt_id": [None, ""]}.items():
            for bad in bad_values:
                with self.subTest(key=key, bad=bad):
                    self.put_cache(dict(valid, **{key: bad}))
                    self.assert_no_counts(self.iss.lexical_statistics(self.index_dir), "unavailable")
        self.put_cache(dict(valid, generation=valid["generation"] + 1))
        self.assertEqual(self.iss.lexical_statistics(self.index_dir)["reason"], "statistics_stale")
        self.put_cache(dict(valid, attempt_id="other"))
        self.assertEqual(self.iss.lexical_statistics(self.index_dir)["reason"], "statistics_stale")
        self.put_cache(valid)
        self.iss.begin_build_epoch(self.index_dir, "all")
        self.assert_no_counts(self.iss.lexical_statistics(self.index_dir), "updating")

    def finish(self, attempt, staged):
        if not staged:
            return self.iss.finalize_build_epoch(self.index_dir, attempt)
        receipt = {"index_dir": str(self.index_dir.resolve()), "attempt_id": attempt,
                   "expected_generation": self.iss.read_build_state(self.index_dir)["generation"] + 1,
                   "memory_backfill_run_id": "test-run"}
        with mock.patch("memory_backfill.record_publication_success"):
            return self.iss.finalize_staged_build_epoch(self.index_dir, receipt, "test-run")

    def test_both_finalizers_reuse_unchanged_cache_and_reject_cas_miss(self):
        self.populate()
        for staged in (False, True):
            attempt = self.iss.begin_build_epoch(self.index_dir, "graph")
            with mock.patch.object(self.iss, "_aggregate_lexical_statistics", side_effect=AssertionError("unexpected vocabulary scan")):
                self.assertFalse(self.finish("wrong-attempt", staged))
                self.assertTrue(self.finish(attempt, staged))
            payload = self.iss.lexical_statistics(self.index_dir)
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(self.cache()["attempt_id"], attempt)

    def test_both_finalizers_isolate_statistics_error_without_reset(self):
        self.populate()
        for staged in (False, True):
            attempt = self.iss.begin_build_epoch(self.index_dir, "docs")
            self.iss.apply_chunk_deltas(self.index_dir, "docs", add_rows=[self.row("new", "zeta")])
            with mock.patch.object(self.iss, "_aggregate_lexical_statistics", side_effect=self.iss.sqlite_runtime.apsw.BusyError("database is locked")), \
                 mock.patch.object(self.iss.IndexStateStore, "reset", side_effect=AssertionError("unexpected reset")):
                self.assertTrue(self.finish(attempt, staged))
            self.assertEqual(self.iss.read_build_state(self.index_dir)["status"], "complete")
            self.assert_no_counts(self.iss.lexical_statistics(self.index_dir))
            self.assertEqual(self.iss.registry_chunk_count(self.index_dir, "docs"), 3)

    def test_snapshot_reads_only_metadata_and_build_state(self):
        self.populate()
        queries = []
        real_open = self.iss.open_read_only
        def traced(index_dir):
            conn = real_open(index_dir)
            conn.set_exec_trace(lambda cursor, sql, bindings: (queries.append(sql), True)[1])
            return conn
        with mock.patch.object(self.iss, "open_read_only", side_effect=traced), \
             mock.patch.object(self.iss, "_aggregate_lexical_statistics", side_effect=AssertionError("reader scanned")), \
             mock.patch.object(self.iss, "fts_probe", side_effect=AssertionError("reader probed")):
            self.assertEqual(self.iss.lexical_statistics(self.index_dir)["status"], "ready")
        self.assertEqual(queries[0], "BEGIN")
        self.assertTrue(all(sql == "BEGIN" or sql.startswith("SELECT") for sql in queries), queries)
        self.assertFalse(any("fts_docs" in sql or "fts_code" in sql or "vocab" in sql for sql in queries), queries)

    def test_staged_parent_computes_new_cache_and_unavailable_reader_preserves_it(self):
        attempt = self.iss.begin_build_epoch(self.index_dir, "docs")
        self.iss.rebuild_chunk_index(self.index_dir, "docs", [self.row("d", "hello hello")])
        self.assertTrue(self.finish(attempt, True))
        self.assertEqual(self.iss.lexical_statistics(self.index_dir)["term_occurrences"], 2)
        with mock.patch.object(self.iss, "fts5_available", return_value=False):
            self.assert_no_counts(self.iss.lexical_statistics(self.index_dir), "unavailable")
        # Runtime capability failure refuses readers; it cannot erase a valid
        # canonical database or its published metadata.
        self.assertEqual(self.iss.lexical_statistics(self.index_dir)["term_occurrences"], 2)

    def test_delta_rollback_restores_matching_cache(self):
        self.populate()
        before = self.cache()
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            store._conn.execute("CREATE TEMP TRIGGER fail_docs BEFORE INSERT ON chunks_docs "
                                "WHEN NEW.chunk_id='new' BEGIN SELECT RAISE(ABORT,'injected IO failure'); END")
            with self.assertRaises(self.iss.sqlite_runtime.Error):
                self.iss._apply_chunk_deltas_locked(store, "docs", add_rows=[self.row("new", "zeta")])
        finally:
            store.close()
        self.assertEqual(self.cache(), before)
        self.assertEqual(self.iss.lexical_statistics(self.index_dir)["entries"], 3)

    def test_unreadable_store_and_invalid_json_do_not_fabricate_metrics(self):
        self.populate()
        with mock.patch.object(self.iss, "open_read_only", return_value=None):
            self.assertEqual(self.iss.lexical_statistics(self.index_dir)["reason"], "store_unreadable")
        store = self.iss.IndexStateStore(self.index_dir)
        store.set_meta({self.iss.META_LEXICAL_STATISTICS: "{"})
        store.close()
        self.assert_no_counts(self.iss.lexical_statistics(self.index_dir), "unavailable")

    def test_current_runtime_without_fts_cannot_advertise_published_cache(self):
        self.populate()
        self.assertEqual(self.iss.lexical_statistics(self.index_dir)["status"], "ready")
        with mock.patch.object(self.iss, "fts5_available", return_value=False), \
             mock.patch.object(self.iss, "open_read_only", side_effect=AssertionError("capability rejection needs no store read")):
            payload = self.iss.lexical_statistics(self.index_dir)
        self.assertEqual(payload["reason"], "fts_disabled")
        self.assert_no_counts(payload, "unavailable")

    def test_statistics_write_error_does_not_undo_publication(self):
        self.populate()
        attempt = self.iss.begin_build_epoch(self.index_dir, "graph")
        real_connect = self.iss._full_durable_connection
        def failing(index_dir):
            return _FlakyConn(real_connect(index_dir), "INSERT INTO meta (key, value) VALUES (?, ?)",
                              self.iss.sqlite_runtime.apsw.IOError("injected cache write failure"))
        with mock.patch.object(self.iss, "_full_durable_connection", side_effect=failing):
            self.assertTrue(self.finish(attempt, False))
        self.assertEqual(self.iss.read_build_state(self.index_dir)["status"], "complete")
        self.assertEqual(self.iss.lexical_statistics(self.index_dir)["reason"], "statistics_stale")


if __name__ == "__main__":
    unittest.main()

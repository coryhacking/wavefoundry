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
from contextlib import redirect_stderr
from pathlib import Path

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


class StoreSubstrateTests(_TempRepoCase):
    """AC-1, AC-2: WAL/versioning contract and drop-and-rebuild recovery."""

    def test_creation_sets_wal_busy_timeout_schema_version_and_auto_vacuum(self):
        store = self.iss.IndexStateStore(self.index_dir)
        try:
            conn = store._conn
            self.assertEqual(
                str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower(), "wal"
            )
            self.assertGreaterEqual(int(conn.execute("PRAGMA busy_timeout").fetchone()[0]), 10000)
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

    def test_unknown_schema_version_resets_store_with_diagnostic(self):
        store = self.iss.IndexStateStore(self.index_dir)
        store.apply_freshness(rows={"a.py": {"last_modified": 1, "churn_score": 0.5,
                                             "commit_count": 5, "source": "git"}})
        store.set_meta({"store_schema_version": "999"})
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            self.assertFalse(store.ensure_current())
        self.assertIn("schema version mismatch", stderr.getvalue())
        self.assertEqual(store.get_meta("store_schema_version"),
                         self.iss.STATE_STORE_SCHEMA_VERSION)
        rows = store._conn.execute("SELECT COUNT(*) FROM file_freshness").fetchone()[0]
        self.assertEqual(rows, 0)
        store.close()

    def test_corrupted_store_is_dropped_and_rebuilt_loudly(self):
        store = self.iss.IndexStateStore(self.index_dir)
        store.close()
        path = self.iss.state_store_path(self.index_dir)
        path.write_bytes(b"this is not a sqlite database" * 64)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            store2 = self.iss.IndexStateStore(self.index_dir)
        try:
            self.assertIn("resetting store", stderr.getvalue())
            self.assertEqual(store2.get_meta("store_schema_version"),
                             self.iss.STATE_STORE_SCHEMA_VERSION)
        finally:
            store2.close()

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
            store._conn.rollback()
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

    def test_byte_corrupt_store_reports_structural_fail_and_rebuilds(self):
        self._built_store()
        _corrupt_sqlite_file(self.iss.state_store_path(self.index_dir))
        probe = self.iss.probe_state_store(self.root, self.index_dir)
        self.assertEqual(probe["status"], "structural-fail")
        # Recovery: the next build-time open drops and rebuilds (derived-only).
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            summary = self.iss.update_freshness_from_build(
                self.root, self.index_dir, ["a.py"]
            )
        self.assertEqual(summary["written"], 1)
        self.assertEqual(
            self.iss.probe_state_store(self.root, self.index_dir)["status"], "ok"
        )

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
        """Build-end order: bookkeeping write → snapshot export → _save_meta →
        stranded-row reap → chunk-index reconcile → freshness update (all
        inside the build lock; the reap precedes the reconcile so FTS/registry
        never retain reaped content between builds)."""
        src = (SCRIPTS_ROOT / "indexer.py").read_text(encoding="utf-8")
        bookkeeping_pos = src.index("write_build_bookkeeping(index_dir, new_meta)")
        snapshot_pos = src.index("export_meta_snapshot(index_dir)", bookkeeping_pos)
        save_meta_pos = src.index(
            "_save_meta(index_dir, _meta_snapshot if _meta_snapshot is not None else new_meta)",
            snapshot_pos,
        )
        reap_pos = src.index("_reap_stranded_lance_rows(\n            lance_db_path", save_meta_pos)
        reconcile_pos = src.index("_sync_chunk_derived_state(", reap_pos)
        update_pos = src.index("update_freshness_from_build(", reconcile_pos)
        self.assertGreater(update_pos, reconcile_pos)
        loader_pos = src.index("def _get_index_state_store()")
        self.assertGreater(loader_pos, 0)

    def test_setup_optimize_after_build_wires_state_store_pass(self):
        src = (SCRIPTS_ROOT / "setup_index.py").read_text(encoding="utf-8")
        lance_pos = src.index("optimize_index_tables(index_dir)")
        store_pos = src.index("optimize_state_stores(", lance_pos)
        self.assertGreater(store_pos, lance_pos)


if __name__ == "__main__":
    unittest.main()

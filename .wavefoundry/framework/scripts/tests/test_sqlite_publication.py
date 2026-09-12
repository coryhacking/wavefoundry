"""Native transaction/publication controls for unified semantic storage."""
import errno
import json
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import index_state_store as iss
import sqlite_runtime as runtime
import sqlite_vector_store as vectors


def row(key="a", text="original_symbol", path="src/a.py"):
    return {"id": key, "path": path, "text": text, "kind": "code", "lines": [2, 7],
            "vector": [1.0] + [0.0] * 383, "chunk_hash": text}


class SQLitePublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.index_dir = Path(self.tmp.name)
        self.store = iss.IndexStateStore(self.index_dir)
        self.spill_limit = patch.object(vectors.PreparedUpdates, "MEMORY_LIMIT_BYTES", 0)
        self.spill_limit.start()
        self.addCleanup(self.spill_limit.stop)
        iss.apply_chunk_deltas(self.index_dir, "code", add_rows=[row()])

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_prepared_spool_ignores_global_temp_and_cleans_success_and_failure(self):
        before = vectors.payload_rows(self.index_dir, "code", include_vector=True)
        for fail in (False, True):
            with self.subTest(fail=fail):
                # An unusable system temp directory must not affect this spool.
                with patch.object(tempfile, "tempdir", str(self.index_dir / "missing-temp")):
                    try:
                        with vectors.PreparedUpdates(self.index_dir) as prepared:
                            prepared.add("code", rows=[row("new")])
                            spool = prepared.path.parent
                            self.assertEqual(spool.parent.resolve(), self.index_dir.resolve())
                            if fail:
                                raise ValueError("injected embedding failure")
                    except ValueError:
                        self.assertTrue(fail)
                self.assertFalse(spool.exists())
                self.assertEqual(vectors.payload_rows(self.index_dir, "code", include_vector=True), before)

    def test_failed_spool_initialization_removes_only_its_owned_directory(self):
        neighbor = self.index_dir / "unrelated"
        neighbor.mkdir()
        with patch.object(runtime, "connect", side_effect=runtime.RuntimeUnavailable("injected")):
            with self.assertRaises(runtime.RuntimeUnavailable) as caught:
                with vectors.PreparedUpdates(self.index_dir) as prepared:
                    prepared.add("code", rows=[row("new")])
        self.assertIn("injected", str(caught.exception))
        self.assertEqual(list(self.index_dir.glob("wavefoundry-sqlite-prepared-*")), [])
        self.assertTrue(neighbor.is_dir())
        self.assertEqual(vectors.layer_counts(self.index_dir)["code"], 1)

    def test_spool_low_space_refuses_creation_on_owned_filesystem(self):
        with patch.object(vectors.shutil, "disk_usage", return_value=SimpleNamespace(free=0)) as usage:
            with self.assertRaises(OSError) as caught:
                with vectors.PreparedUpdates(self.index_dir) as prepared:
                    prepared.add("code", rows=[row("new")])
        self.assertEqual(caught.exception.errno, errno.ENOSPC)
        usage.assert_called_once_with(self.index_dir)
        self.assertEqual(list(self.index_dir.glob("wavefoundry-sqlite-prepared-*")), [])

    def test_spool_growth_low_space_rolls_back_and_preserves_published_rows(self):
        before = vectors.payload_rows(self.index_dir, "code", include_vector=True)
        with vectors.PreparedUpdates(self.index_dir) as prepared:
            prepared.add("code", rows=[row("keep")])
            # The first bounded batch fits; the next check loses its headroom.
            # Earlier inserts in this add must roll back with the refused batch.
            with patch.object(vectors.shutil, "disk_usage", side_effect=[
                    SimpleNamespace(free=128 * 1024 * 1024),
                    SimpleNamespace(free=64 * 1024 * 1024)]):
                with self.assertRaises(OSError) as caught:
                    prepared.add("code", replace=True,
                                 rows=(row(f"discard-{n}") for n in range(251)))
            self.assertEqual(caught.exception.errno, errno.ENOSPC)
            conn = runtime.connect(prepared.path, read_only=True)
            try:
                operations = conn.execute("SELECT payload FROM operations").fetchall()
                self.assertEqual([json.loads(payload)["id"] for payload, in operations], ["keep"])
            finally:
                conn.close()
        self.assertEqual(vectors.payload_rows(self.index_dir, "code", include_vector=True), before)

    def test_publication_reserves_growth_while_spool_coexists(self):
        before = vectors.payload_rows(self.index_dir, "code", include_vector=True)
        with vectors.PreparedUpdates(self.index_dir) as prepared:
            prepared.add("code", replace=True, rows=[row("new")])
            with patch.object(vectors.shutil, "disk_usage",
                              return_value=SimpleNamespace(free=64 * 1024 * 1024)):
                with self.assertRaises(OSError) as caught:
                    with self.store._conn:
                        prepared.apply(self.store)
            self.assertEqual(caught.exception.errno, errno.ENOSPC)
        self.assertEqual(vectors.payload_rows(self.index_dir, "code", include_vector=True), before)

    def test_prepared_rollback_restores_vector_text_fts_registry_and_bookkeeping(self):
        before = vectors.payload_rows(self.index_dir,"code",include_vector=True)
        with vectors.PreparedUpdates(self.index_dir) as prepared:
            prepared.add("code", ids=["a"], rows=[row("b","replacement_symbol")])
            conn = self.store._conn
            conn.execute("BEGIN IMMEDIATE")
            try:
                prepared.apply(self.store)
                iss.write_build_bookkeeping_locked(conn,{"file_meta":{"src/a.py":{"hash":"replacement"}}})
                raise RuntimeError("injected failure before commit")
            except RuntimeError:
                conn.execute("ROLLBACK")
        self.assertEqual(vectors.payload_rows(self.index_dir,"code",include_vector=True),before)
        self.assertEqual([r['id'] for r in iss.fts_search(self.index_dir,"code","original_symbol",limit=5)],["a"])
        self.assertEqual(iss.fts_search(self.index_dir,"code","replacement_symbol",limit=5),[])
        self.assertEqual(iss.registry_chunk_count(self.index_dir,"code"),1)
        self.assertEqual(self.store._conn.execute("SELECT COUNT(*) FROM build_file_meta").fetchone(),(0,))

    def test_concurrent_reader_retains_one_snapshot_and_new_reader_gets_complete_delta(self):
        reader = runtime.connect(self.store.path,read_only=True)
        try:
            reader.execute("BEGIN")
            self.assertEqual(reader.execute("SELECT text FROM chunks_code").fetchone()[0],"original_symbol")
            with self.store._conn:
                iss._apply_chunk_deltas_locked(self.store,"code",delete_ids=["a"],add_rows=[row("b","replacement_symbol")])
            self.assertEqual(reader.execute("SELECT text FROM chunks_code").fetchone()[0],"original_symbol")
            self.assertEqual(reader.execute("SELECT COUNT(*) FROM fts_code WHERE fts_code MATCH 'original_symbol'").fetchone(),(1,))
            reader.execute("COMMIT")
            self.assertEqual(reader.execute("SELECT text FROM chunks_code").fetchone()[0],"replacement_symbol")
        finally:
            reader.close()

    def test_full_replace_zero_rows_clears_one_layer_only(self):
        iss.apply_chunk_deltas(self.index_dir,"docs",add_rows=[row("d")])
        with vectors.PreparedUpdates(self.index_dir) as prepared:
            prepared.add("code",replace=True)
            with self.store._conn:
                prepared.apply(self.store)
        self.assertEqual(vectors.layer_counts(self.index_dir),{"docs":1,"code":0})
        self.assertEqual(iss.fts_search(self.index_dir,"code","original_symbol",limit=2),[])

    def test_prepared_operation_order_survives_batch_boundaries(self):
        for batch_size in (1, 2, 250):
            with self.subTest(batch_size=batch_size):
                with vectors.PreparedUpdates(self.index_dir) as prepared:
                    prepared.add("code", rows=[row("b", "discard_symbol")])
                    prepared.add("code", paths=["src/a.py"])
                    prepared.add("code", rows=[row("c", "also_discard_symbol")])
                    prepared.add("code", replace=True)
                    prepared.add("code", rows=[row("d", "retained_symbol")])
                    with self.store._conn:
                        prepared.apply(self.store, batch_size=batch_size)
                self.assertEqual([r["id"] for r in vectors.payload_rows(self.index_dir, "code")], ["d"])
                self.assertEqual(iss.registry_chunk_count(self.index_dir, "code"), 1)
                self.assertEqual(iss.fts_search(self.index_dir, "code", "discard_symbol", limit=5), [])

    def test_unknown_schema_and_corruption_are_preserved(self):
        with self.store._conn:
            self.store._conn.execute("UPDATE meta SET value='999' WHERE key='store_schema_version'")
        with self.assertRaises(runtime.StorageRecoveryRequired):
            iss.IndexStateStore(self.index_dir)
        self.assertEqual(self.store._conn.execute("SELECT COUNT(*) FROM vectors_code").fetchone(),(1,))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/vectors.FILENAME
            path.write_bytes(b"unrecognized corrupt canonical index")
            before = path.read_bytes()
            with self.assertRaises(runtime.Error):
                iss.IndexStateStore(Path(temp))
            self.assertEqual(path.read_bytes(),before)

    def test_orphan_vector_is_detected_and_full_replacement_repairs_only_its_layer(self):
        conn = self.store._conn
        conn.execute("PRAGMA foreign_keys=OFF")
        try:
            conn.execute("INSERT INTO vectors_code VALUES(999,?)", (vectors.pack_vector(row()['vector']),))
        finally:
            conn.execute("PRAGMA foreign_keys=ON")
        with conn:
            verdict = vectors.vector_integrity(conn, "code")
        self.assertEqual(verdict, {"canonical": 1, "vectors": 2,
                                   "missing_vectors": 0, "orphan_vectors": 1})
        iss.apply_chunk_deltas(self.index_dir, "docs", add_rows=[row("d")])
        with vectors.PreparedUpdates(self.index_dir) as prepared:
            prepared.add("code", replace=True, rows=[row("replacement")])
            with conn:
                prepared.apply(self.store)
                self.assertEqual(vectors.vector_integrity(conn, "code")["orphan_vectors"], 0)
        self.assertEqual(vectors.layer_counts(self.index_dir), {"docs": 1, "code": 1})

    def test_read_only_and_foreign_key_refusal(self):
        reader = runtime.connect(self.store.path,read_only=True)
        try:
            with self.assertRaises(runtime.Error):
                reader.execute("DELETE FROM chunks_code")
        finally:
            reader.close()
        with self.assertRaises(runtime.Error):
            self.store._conn.execute("INSERT INTO vectors_code VALUES(999,?)",(vectors.pack_vector(row()['vector']),))

    def test_build_fence_uses_actual_affected_row_count_and_full_durability(self):
        attempt = iss.begin_build_epoch(self.index_dir,"test")
        self.assertFalse(iss.finalize_build_epoch(self.index_dir,"not-the-attempt"))
        self.assertEqual(iss.read_build_state(self.index_dir)['status'],"building")
        conn = iss._full_durable_connection(self.index_dir)
        try:
            self.assertEqual(conn.execute("PRAGMA synchronous").fetchone(),(2,))
        finally:
            conn.close()
        self.assertTrue(iss.finalize_build_epoch(self.index_dir,attempt))
        self.assertFalse(iss.finalize_build_epoch(self.index_dir,attempt))

    def test_payload_has_one_text_copy_and_external_fts(self):
        payload = json.loads(self.store._conn.execute("SELECT payload FROM chunks_code").fetchone()[0])
        self.assertNotIn("text",payload)
        self.assertNotIn("vector",payload)
        schema = self.store._conn.execute("SELECT sql FROM sqlite_schema WHERE name='fts_code'").fetchone()[0]
        self.assertIn("content='chunks_code'",schema)
        result = iss.fts_search(self.index_dir,"code","original_symbol",limit=1)[0]
        self.assertEqual(result['lines'],[2,7])


if __name__ == "__main__":
    unittest.main()

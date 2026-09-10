"""Native negative controls for guarded, bounded SQLite publication work."""
import struct
import tempfile
import unittest
from pathlib import Path

import index_state_store as iss
import sqlite_runtime as runtime
import sqlite_vector_store as vectors


def row(key='a', text='alpha beta'):
    return {'id': key, 'path': 'src/a.py', 'text': text, 'kind': 'code',
            'lines': [1, 2], 'vector': [1.0] + [0.0] * 383, 'chunk_hash': text}


class PublicationOptimizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.index_dir = Path(self.temp.name)
        self.store = iss.IndexStateStore(self.index_dir)
        iss.apply_chunk_deltas(self.index_dir, 'code', add_rows=[row()])

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_corrupt_prepared_blobs_still_refuse_atomic_publication(self):
        before = vectors.payload_rows(self.index_dir, 'code', include_vector=True)
        bad = {
            'nan': struct.pack('<384f', float('nan'), *([0.0] * 383)),
            'infinity': struct.pack('<384f', float('inf'), *([0.0] * 383)),
            'zero': bytes(384 * 4),
            'wrong_dimensions': bytes(383 * 4),
        }
        for name, blob in bad.items():
            with self.subTest(name=name), vectors.PreparedUpdates(self.index_dir) as prepared:
                prepared.add('code', ids=['a'], rows=[row('b')])
                spool = runtime.connect(prepared.path)
                try:
                    with spool:
                        spool.execute("UPDATE operations SET vector=? WHERE action='row'", (blob,))
                finally:
                    spool.close()
                conn = self.store._conn
                conn.execute('BEGIN IMMEDIATE')
                try:
                    with self.assertRaises(ValueError):
                        prepared.apply(self.store)
                finally:
                    conn.execute('ROLLBACK')
                self.assertEqual(vectors.payload_rows(self.index_dir, 'code', include_vector=True), before)
                self.assertEqual(iss.registry_chunk_count(self.index_dir, 'code'), 1)
                self.assertEqual([r['id'] for r in iss.fts_search(self.index_dir, 'code', 'alpha')], ['a'])
        packed = struct.pack('<384f', 0.25, -0.75, *([0.0] * 382))
        self.assertEqual(vectors.pack_vector(memoryview(packed)), packed)

    def test_bounded_digest_deduplicates_overlapping_ids_and_paths(self):
        rows = [row(str(i), f'alpha beta {i}') for i in range(4)]
        iss.apply_chunk_deltas(self.index_dir, 'code', delete_ids=['a'], add_rows=rows)
        conn = self.store._conn
        expected = 0
        for value in rows:
            expected ^= iss._fts_payload_row_digest(*iss._fts_row_tuple(value))
        ids = ['0', '0', '2'] + [f'absent-{i}' for i in range(iss._FTS_DIGEST_SELECT_BATCH + 1)]
        self.assertEqual(iss._fts_affected_rows_digest(conn, 'fts_code', ids, ['src/a.py', 'src/a.py']), expected)
        self.assertEqual(iss._fts_table_digest(conn, 'fts_code'), expected)

    def test_writer_probe_preserves_connection_transaction_and_reader_contract(self):
        conn = self.store._conn
        with self.assertRaises(RuntimeError):
            iss.fts_state_verdict(self.index_dir, 'code', _writer_conn=conn)
        conn.execute('BEGIN IMMEDIATE')
        conn.execute("INSERT INTO meta(key,value) VALUES('probe-uncommitted','yes')")
        self.assertTrue(iss.fts_state_verdict(self.index_dir, 'code', _writer_conn=conn)['ok'])
        self.assertFalse(conn.get_autocommit())
        conn.execute('ROLLBACK')
        self.assertIsNone(conn.execute("SELECT value FROM meta WHERE key='probe-uncommitted'").fetchone())
        reader = iss.open_read_only(self.index_dir)
        try:
            reader.execute('BEGIN')
            self.assertTrue(reader.readonly('main'))
            self.assertTrue(iss._fts_postings_match(reader, 'code'))
            with self.assertRaises(RuntimeError):
                iss.fts_state_verdict(self.index_dir, 'code', _writer_conn=reader)
        finally:
            reader.close()

    def test_same_count_position_substitution_fails_both_native_probe_paths(self):
        conn = self.store._conn
        cols = vectors.FTS_COLUMNS
        old = conn.execute(f'SELECT id,{cols} FROM chunks_code').fetchone()
        changed = (*old[:-1], 'beta alpha')
        marks = ','.join('?' for _ in old)
        with conn:
            conn.execute(f"INSERT INTO fts_code(fts_code,rowid,{cols}) VALUES('delete',{marks})", old)
            conn.execute(f'INSERT INTO fts_code(rowid,{cols}) VALUES({marks})', changed)
        self.assertEqual(conn.execute('SELECT count(*) FROM fts_code_docsize').fetchone(), (1,))
        self.assertEqual(iss._fts_table_digest(conn, 'fts_code'), iss._fts_payload_row_digest(*old[1:]))
        self.assertFalse(iss.fts_state_verdict(self.index_dir, 'code')['ok'])
        conn.execute('BEGIN IMMEDIATE')
        try:
            verdict = iss.fts_state_verdict(self.index_dir, 'code', _writer_conn=conn)
            self.assertFalse(verdict['ok'])
            self.assertEqual(verdict['reason'], 'digest_mismatch')
            self.assertFalse(conn.get_autocommit())
        finally:
            conn.execute('ROLLBACK')


if __name__ == '__main__':
    unittest.main()

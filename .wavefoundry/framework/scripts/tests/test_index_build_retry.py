"""Real SQLite publication and reader regressions for bounded source-drift retry."""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import unittest
from unittest.mock import patch

import test_indexer as fixtures


class SourceDriftPublicationTests(unittest.TestCase):
    # Reuse the native SQLite + deterministic 384D embedder fixture, without
    # inheriting unrelated tests or replacing either source-validation guard.
    setUp = fixtures.TargetedPublicationContractTests.setUp
    _rows = fixtures.TargetedPublicationContractTests._rows
    _change_one = fixtures.TargetedPublicationContractTests._change_one

    def _payload(self):
        rows = self._rows('one.py')
        rows.pop('secret_scan_cache')  # optional scanner runs before recovery capture
        return rows

    def _run_drift(self, *, repeated=False, external_commit=False, full=False, preserve_stat=False):
        prepared_objects = []
        graph_objects = []
        apply = self.bi.vector_store.PreparedUpdates.apply
        graph = self.bi._build_graph_artifacts

        def apply_then_edit(prepared, store):
            result = apply(prepared, store)
            prepared_objects.append(prepared)
            if repeated or len(prepared_objects) == 1:
                source = self.root / 'one.py'
                if preserve_stat:
                    before = source.stat()
                    source.write_text(source.read_text().replace('12345', '54321'))
                    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
                else:
                    number = 700000 + len(prepared_objects)
                    source.write_text(
                        f'def one():\n    """Newest documentation {number}."""\n    return {number}\n')
            return result

        def prepare_graph(**kwargs):
            result = graph(**kwargs)
            graph_objects.append(result.get('publication'))
            if external_commit:
                writer = self.iss.IndexStateStore(self.index_dir)
                try:
                    with writer._conn:
                        writer._conn.execute(
                            "INSERT INTO meta(key,value) VALUES('external-race',?) "
                            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                            (str(len(graph_objects)),))
                finally:
                    writer.close()
            return result

        logs = io.StringIO()
        with patch.object(self.bi.vector_store.PreparedUpdates, 'apply', apply_then_edit), \
                patch.object(self.bi, '_build_graph_artifacts', side_effect=prepare_graph), \
                contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
            result = self.bi.build_index(self.root, content='all', full=full)
        self.assertEqual(2, len(prepared_objects), (result, logs.getvalue()))
        self.assertIsNot(prepared_objects[0], prepared_objects[1])
        self.assertEqual(2, len(graph_objects))
        self.assertTrue(all(graph_objects))
        self.assertIsNot(graph_objects[0], graph_objects[1])
        self.assertIn('one.py', logs.getvalue())
        self.assertIn('retrying once', logs.getvalue())
        self.assertIn('readers:', logs.getvalue())
        return result, logs.getvalue()

    def test_transient_drift_reprepares_all_participants_and_publishes_latest(self):
        old_token = self.iss.build_epoch_token(self.index_dir)
        self._change_one()
        result, logs = self._run_drift()
        self.assertFalse(result.get('failed'), (result, logs))
        token = self.iss.build_epoch_token(self.index_dir)
        self.assertEqual(old_token[1] + 1, token[1])
        rows = fixtures._read_index_chunks(self.index_dir, 'code')
        self.assertTrue(any('700001' in row['text'] for row in rows))
        self.assertFalse(any('12345' in row['text'] for row in rows))
        self.assertEqual(self.bi._sha256(self.root / 'one.py'),
                         fixtures._read_meta_store(self.index_dir)['file_meta']['one.py']['hash'])
        self.assertEqual('ready', self.iss.lexical_statistics(self.index_dir)['status'])
        self.assertIsNotNone(self.gi.read_published_graph_snapshot(self.root))

    def test_same_stat_content_drift_still_requires_fresh_preparation(self):
        self._change_one()
        result, logs = self._run_drift(preserve_stat=True)
        self.assertFalse(result.get('failed'), (result, logs))
        rows = fixtures._read_index_chunks(self.index_dir, 'code')
        self.assertTrue(any('54321' in row['text'] for row in rows))
        self.assertFalse(any('12345' in row['text'] for row in rows))

    def test_repeated_drift_restores_payload_and_serving_with_distinct_token(self):
        before = self._payload()
        old_token = self.iss.build_epoch_token(self.index_dir)
        lexical = self.iss.lexical_statistics(self.index_dir)
        hits = self.iss.fts_search(self.index_dir, 'code', 'one')
        self.assertTrue(hits)
        self._change_one()
        result, logs = self._run_drift(repeated=True)
        self.assertTrue(result.get('failed'), result)
        self.assertIn('refused after two attempts', logs)
        self.assertIn('previous completed snapshot', result['reader_state'])
        token = self.iss.build_epoch_token(self.index_dir)
        self.assertIsNotNone(token)
        self.assertNotEqual(old_token, token)
        self.assertEqual(old_token[1], token[1])
        self.assertEqual(before, self._payload())
        self.assertEqual(lexical, self.iss.lexical_statistics(self.index_dir))
        self.assertEqual(hits, self.iss.fts_search(self.index_dir, 'code', 'one'))
        from server_tools_support import load_server
        server = load_server()
        health = server.index_health_response(server.WaveIndex(self.root))
        self.assertEqual('ok', health['status'])
        data = health['data']
        self.assertEqual('stale', data['project']['readiness'])
        self.assertIn('one.py', data['project']['stale_paths'])
        self.assertTrue(data['graph']['project']['present'])
        for layer in ('docs', 'code'):
            self.assertTrue(data['state_store']['chunk_index'][layer]['covered'])
            self.assertTrue(data['state_store']['fts'][layer]['ok'])
            self.assertEqual('complete', data['state_store']['fts'][layer]['epoch'][1])
        self.assertIsNotNone(self.gi.read_published_graph_snapshot(self.root))

    def test_recovery_error_emits_refusal_and_actual_reader_state_without_retry(self):
        for restore_first in (False, True):
            with self.subTest(restore_first=restore_first):
                self._change_one()
                apply = self.bi.vector_store.PreparedUpdates.apply
                restore = self.iss.BuildEpochRecovery.restore_after_rollback
                calls = []
                def drift(prepared, store):
                    apply(prepared, store)
                    calls.append(1)
                    (self.root / 'one.py').write_text('def one(): return 777777\n')
                def uncertain(recovery, **kwargs):
                    if restore_first:
                        self.assertTrue(restore(recovery, **kwargs))
                    raise OSError('recovery I/O uncertainty')
                logs = io.StringIO()
                with patch.object(self.bi.vector_store.PreparedUpdates, 'apply', drift), \
                        patch.object(self.iss.BuildEpochRecovery, 'restore_after_rollback', uncertain), \
                        contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
                    result = self.bi.build_index(self.root, content='all')
                self.assertTrue(result.get('failed'))
                self.assertEqual([1], calls)
                self.assertIn('one.py', logs.getvalue())
                self.assertIn('refused without retry', logs.getvalue())
                self.assertIn('recovery I/O uncertainty', logs.getvalue())
                state = ('complete snapshot available; recovery outcome uncertain'
                         if restore_first else 'fail-closed')
                self.assertIn('readers: ' + state, logs.getvalue())
                self.assertEqual(state, result['reader_state'])
                # Heal before the next independent uncertainty ordering.
                self.assertFalse(self.bi.build_index(self.root, content='all').get('failed'))

    def test_no_previous_epoch_stays_fail_closed_after_two_attempts(self):
        shutil.rmtree(self.index_dir)
        result, logs = self._run_drift(repeated=True, full=True)
        self.assertTrue(result.get('failed'), result)
        self.assertEqual('fail-closed', result['reader_state'])
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        self.assertNotEqual('ready', self.iss.lexical_statistics(self.index_dir)['status'])
        self.assertIn('refused after two attempts', logs)

    def test_external_commit_disqualifies_restoration(self):
        self._change_one()
        result, _ = self._run_drift(repeated=True, external_commit=True)
        self.assertTrue(result.get('failed'), result)
        self.assertEqual('fail-closed', result['reader_state'])
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        self.assertNotEqual('ready', self.iss.lexical_statistics(self.index_dir)['status'])

    def test_graph_only_markdown_edit_reprepares_graph_and_preserves_semantics(self):
        source = self.root / 'note.md'
        source.write_text('# Original graph note\n\nSee `one.py`.\n')
        self.assertFalse(self.bi.build_index(self.root, content='all').get('failed'))
        before = fixtures._read_index_chunks(self.index_dir, 'docs')
        source.write_text('# Pending graph note\n\nSee `two.py`.\n')
        original = self.gi.GraphPublication.apply
        publications = []
        def edit_then_apply(publication, conn):
            publications.append(publication)
            if len(publications) == 1:
                source.write_text('# Latest graph note after race\n\nSee `one.py`.\n')
            return original(publication, conn)
        with patch.object(self.gi.GraphPublication, 'apply', edit_then_apply):
            result = self.bi.build_index(self.root, content='graph', full=True)
        self.assertFalse(result.get('failed'), result)
        self.assertEqual(2, len(publications), result)
        self.assertIsNot(publications[0], publications[1])
        self.assertEqual(before, fixtures._read_index_chunks(self.index_dir, 'docs'))
        snapshot = self.gi.read_published_graph_snapshot(self.root)
        self.assertIsNotNone(snapshot)
        conn = self.iss.open_read_only(self.index_dir)
        try:
            stored_hash = conn.execute(
                "SELECT source_hash FROM graph_file_state WHERE path='note.md'").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(self.bi._sha256(source), stored_hash)

    def test_real_build_defers_due_monitor_then_flushes_after_publication(self):
        from test_index_source_guard import SourceGuardTests
        fixture = SourceGuardTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        original = self.bi.vector_store.PreparedUpdates.apply
        with contextlib.ExitStack() as stack:
            def apply_while_monitor_due(prepared, store):
                handler = stack.enter_context(fixture.monitor())
                fixture.wait_until(lambda: handler._ce_projection_status.get('reason') == 'index_source_busy'
                                   or fixture.wave_md.read_bytes() != fixture.before)
                self.assertEqual(fixture.before, fixture.wave_md.read_bytes())
                self.assertTrue(fixture.ce.read_wave_snapshot(fixture.root, fixture.wave)['pending'])
                return original(prepared, store)
            with patch.object(self.bi.vector_store.PreparedUpdates, 'apply', apply_while_monitor_due):
                result = self.bi.build_index(fixture.root, full=True, content='all')
            self.assertFalse(result.get('failed'), result)
            self.assertIsNotNone(self.iss.build_epoch_token(fixture.root / '.wavefoundry/index'))
            fixture.wait_until(lambda: not fixture.ce.read_wave_snapshot(fixture.root, fixture.wave)['pending'])
            self.assertNotEqual(fixture.before, fixture.wave_md.read_bytes())

    def test_postcommit_reconcile_failure_does_not_restore_or_retry(self):
        self._change_one()
        with patch.object(self.bi, '_sync_chunk_derived_state', return_value={
                'code': {'error': 'injected postcommit reconcile failure'}}), \
                patch.object(self.bi, '_build_graph_artifacts',
                             wraps=self.bi._build_graph_artifacts) as graph:
            result = self.bi.build_index(self.root, content='all')
        self.assertTrue(result.get('failed'), result)
        self.assertIn('injected postcommit', result['failure'])
        self.assertEqual(1, graph.call_count)
        self.assertIsNone(self.iss.build_epoch_token(self.index_dir))
        # Prove this is the committed-content branch, rather than a precommit
        # injection accidentally testing the easier rollback branch.
        self.assertTrue(any('12345' in row['text'] for row in
                            fixtures._read_index_chunks(self.index_dir, 'code')))


if __name__ == '__main__':
    unittest.main()

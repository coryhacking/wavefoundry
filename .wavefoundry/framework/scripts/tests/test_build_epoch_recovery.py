"""Real-connection controls for verified precommit snapshot recovery."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import index_state_store as iss


class BuildEpochRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.index = Path(self.temp.name) / '.wavefoundry/index'
        self.index.mkdir(parents=True)

    def store(self):
        store = iss.IndexStateStore(self.index)
        self.addCleanup(store.close)
        return store

    def complete(self):
        store = self.store()
        store.set_meta({'recovery_control': 'previous'})
        attempt = iss.begin_build_epoch(self.index, 'all:prior')
        self.assertTrue(iss.finalize_build_epoch(self.index, attempt))
        return store, iss.read_build_state(self.index)

    def rollback(self, store):
        store._conn.execute('BEGIN IMMEDIATE')
        store._conn.execute("UPDATE meta SET value='unpublished' WHERE key='recovery_control'")
        store._conn.execute('ROLLBACK')

    def test_restores_payload_times_generation_and_rebinds_statistics_without_aba(self):
        store, before = self.complete()
        old_token = iss.build_epoch_token(self.index)
        old_cache = json.loads(store.get_meta(iss.META_LEXICAL_STATISTICS))
        recovery = iss.begin_recoverable_build_epoch(store, 'docs:attempt')
        self.assertIsNone(iss.build_epoch_token(self.index))
        self.rollback(store)
        self.assertTrue(recovery.restore_after_rollback(rollback_confirmed=True, commit_attempted=False))
        after = iss.read_build_state(self.index)
        for key in ('scope', 'generation', 'started_at', 'completed_at'):
            self.assertEqual(after[key], before[key])
        self.assertNotEqual(after['attempt_id'], old_token[0])
        self.assertNotEqual(after['attempt_id'], recovery.attempt_id)
        self.assertEqual(store.get_meta('recovery_control'), 'previous')
        cache = json.loads(store.get_meta(iss.META_LEXICAL_STATISTICS))
        self.assertEqual(dict(cache, attempt_id=old_cache['attempt_id']), old_cache)
        self.assertEqual(cache['attempt_id'], after['attempt_id'])
        self.assertNotEqual(iss.lexical_statistics(self.index).get('reason'), 'statistics_stale')
        self.assertFalse(recovery.restore_after_rollback(rollback_confirmed=True, commit_attempted=False))

    def test_two_refusals_keep_original_content_generation(self):
        store, before = self.complete()
        attempts = {before['attempt_id']}
        for _ in range(2):
            recovery = iss.begin_recoverable_build_epoch(store, 'docs')
            self.rollback(store)
            self.assertTrue(recovery.restore_after_rollback(rollback_confirmed=True, commit_attempted=False))
            current = iss.read_build_state(self.index)
            self.assertEqual(current['generation'], before['generation'])
            self.assertEqual(current['completed_at'], before['completed_at'])
            self.assertNotIn(current['attempt_id'], attempts)
            attempts.add(current['attempt_id'])

    def test_no_prior_complete_and_unconfirmed_rollback_stay_closed(self):
        store = self.store()
        recovery = iss.begin_recoverable_build_epoch(store, 'docs')
        self.rollback(store)
        self.assertFalse(recovery.restore_after_rollback(rollback_confirmed=True, commit_attempted=False))
        self.assertIsNone(iss.build_epoch_token(self.index))
        self.assertTrue(iss.finalize_build_epoch(self.index, recovery.attempt_id))
        recovery = iss.begin_recoverable_build_epoch(store, 'docs')
        self.assertFalse(recovery.restore_after_rollback(rollback_confirmed=False, commit_attempted=False))
        self.assertIsNone(iss.build_epoch_token(self.index))

    def test_external_commit_even_to_optional_resident_disqualifies(self):
        store, _ = self.complete()
        other = self.store()
        recovery = iss.begin_recoverable_build_epoch(store, 'docs')
        other.set_meta({'external_control': 'committed'})
        self.rollback(store)
        self.assertFalse(recovery.restore_after_rollback(rollback_confirmed=True, commit_attempted=False))
        self.assertEqual(store.get_meta('external_control'), 'committed')
        self.assertIsNone(iss.build_epoch_token(self.index))

    def test_own_commit_cannot_be_hidden_by_false_caller_flags(self):
        store, _ = self.complete()
        recovery = iss.begin_recoverable_build_epoch(store, 'docs')
        store.set_meta({'recovery_control': 'committed-new'})
        self.rollback(store)
        self.assertFalse(recovery.restore_after_rollback(rollback_confirmed=True, commit_attempted=False))
        self.assertEqual(store.get_meta('recovery_control'), 'committed-new')
        self.assertIsNone(iss.build_epoch_token(self.index))

    def test_uncertain_commit_flag_and_live_transaction_are_ineligible(self):
        store, _ = self.complete()
        recovery = iss.begin_recoverable_build_epoch(store, 'docs')
        self.rollback(store)
        self.assertFalse(recovery.restore_after_rollback(rollback_confirmed=True, commit_attempted=True))
        store._conn.execute('BEGIN IMMEDIATE')
        self.assertFalse(recovery.restore_after_rollback(rollback_confirmed=True, commit_attempted=False))
        store._conn.execute('ROLLBACK')
        self.assertIsNone(iss.build_epoch_token(self.index))

    def test_superseded_attempt_cannot_be_restored(self):
        store, _ = self.complete()
        recovery = iss.begin_recoverable_build_epoch(store, 'docs')
        newer = iss.begin_build_epoch(self.index, 'code:newer')
        self.rollback(store)
        self.assertFalse(recovery.restore_after_rollback(rollback_confirmed=True, commit_attempted=False))
        self.assertEqual(iss.read_build_state(self.index)['attempt_id'], newer)

    def test_upgrade_authorization_is_not_bypassed(self):
        store, _ = self.complete()
        import publication_control
        with patch.object(publication_control, 'read_upgrade_checkpoint', return_value={}), patch.object(
                publication_control, 'publication_checkpoint_reason', return_value='foreign_upgrade'):
            with self.assertRaisesRegex(RuntimeError, 'foreign_upgrade'):
                iss.begin_recoverable_build_epoch(store, 'docs')
        self.assertIsNotNone(iss.build_epoch_token(self.index))

    def test_sidecar_retirement_joins_publication_rollback(self):
        store, _ = self.complete()
        store._conn.execute("INSERT INTO secret_scan_cache(path,content_hash,rules_fingerprint,scanned_at) "
                            "VALUES('retired.md','content','rules',1)")
        recovery = iss.begin_recoverable_build_epoch(store, 'docs')
        with self.assertRaisesRegex(RuntimeError, 'writer transaction'):
            iss.remove_sidecar_paths_locked(store._conn, secret_scan_paths=['retired.md'])
        store._conn.execute('BEGIN IMMEDIATE')
        removed = iss.remove_sidecar_paths_locked(store._conn, secret_scan_paths=['retired.md'])
        self.assertEqual(removed['secret_scan_cache'], 1)
        store._conn.execute('ROLLBACK')
        self.assertTrue(recovery.restore_after_rollback(rollback_confirmed=True, commit_attempted=False))
        self.assertEqual(store._conn.execute('SELECT path FROM secret_scan_cache').fetchall(), [('retired.md',)])

    def test_failed_commit_observed_even_when_native_hook_rolls_it_back(self):
        store, _ = self.complete()
        recovery = iss.begin_recoverable_build_epoch(store, 'docs')
        veto_id = object()
        store._conn.set_commit_hook(lambda: True, id=veto_id)
        try:
            with self.assertRaises(Exception):
                store.set_meta({'recovery_control': 'vetoed'})
        finally:
            store._conn.set_commit_hook(None, id=veto_id)
        self.assertTrue(store._conn.get_autocommit())
        self.assertFalse(recovery.restore_after_rollback(rollback_confirmed=True, commit_attempted=False))
        self.assertEqual(store.get_meta('recovery_control'), 'previous')


if __name__ == '__main__':
    unittest.main()

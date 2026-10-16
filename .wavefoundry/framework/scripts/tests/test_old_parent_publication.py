"""The historical installing parent can publish without its ordinary index call."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import index_state_store as store
import memory_backfill as backfill
import upgrade_extensions as hooks
import upgrade_lib


class OldParentPublicationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.index = self.root / '.wavefoundry/index'
        self.index.mkdir(parents=True)
        self.parent = types.ModuleType('historical_publication_parent')
        self.parent.__file__ = str(SCRIPTS / 'upgrade_wavefoundry.py')
        self.enterContext(patch.dict(sys.modules, {self.parent.__name__: self.parent}))
        source = SCRIPTS / 'tests/fixtures/upgrade_old_runner/upgrade_runner_v1_22_0.py.txt'
        exec(compile(source.read_bytes(), str(source), 'exec'), self.parent.__dict__)
        self.ctx = self.parent.UpgradeContext(self.root, '1.22.0', '1.31.0', None, True)
        self.assertFalse(hasattr(self.ctx, 'index_published'))
        upgrade_lib.write_upgrade_lock(self.root, '1.22.0', '1.31.0')
        self.run_id = backfill.ensure_run(self.root, 'upgrade')
        self.assertEqual(backfill.sync_inventory(self.root, self.run_id)['state'], 'ready_for_index')
        upgrade_lib.update_upgrade_lock(self.root, memory_backfill_run_id=self.run_id, current_phase='index_update')
        self.receipt_path = self.index / 'upgrade-index-staging-receipt.json'

    def stage(self):
        attempt = store.begin_build_epoch(self.index, 'all')
        generation = store.read_build_state(self.index)['generation'] + 1
        self.assertTrue(backfill.authorize_index_finalize(self.root, self.run_id, attempt, generation))
        self.receipt_path.write_text(json.dumps({'index_dir': str(self.index.resolve()),
            'attempt_id': attempt, 'expected_generation': generation,
            'memory_backfill_run_id': self.run_id}))
        return attempt, generation

    def recover_historical_parent(self):
        original = self.enterContext(patch.object(self.parent, 'phase_index_update', side_effect=AssertionError('ordinary index phase must be bypassed')))
        hooks._observe_parent_index_outcome(self.ctx)
        with contextlib.redirect_stdout(io.StringIO()):
            self.parent.phase_index_update_parent_owned(self.root, self.run_id)
        original.assert_not_called()
        self.assertFalse(hasattr(self.ctx, 'index_published'))
        self.assertFalse(self.receipt_path.exists())

    def invoke_hook(self):
        # Installed-source import selection is the seam; publication and memory
        # authority stay real, using this root's actual stores and checkpoint.
        with patch.object(hooks, '_installed_memory_backfill', return_value=backfill), contextlib.redirect_stdout(io.StringIO()):
            hooks.post_index_update(self.ctx)

    def assert_failed(self):
        with self.assertRaises(SystemExit) as caught:
            self.invoke_hook()
        self.assertEqual(caught.exception.code, 1)
        self.assertTrue(upgrade_lib.read_upgrade_lock(self.root)['index_publication_failed'])

    def test_actual_historical_early_recovery_passes_incoming_hook(self):
        self.stage()
        self.recover_historical_parent()
        self.assertEqual(backfill.run_state(self.root, self.run_id), 'indexed')
        self.invoke_hook()
        self.assertNotIn('index_publication_failed', upgrade_lib.read_upgrade_lock(self.root))

    def test_reconciles_exact_authorized_attempt_after_cas_split(self):
        self.stage()
        with patch.object(backfill, 'record_publication_success', return_value=False):
            self.recover_historical_parent()
        self.assertEqual(backfill.run_state(self.root, self.run_id), 'publishing_index')
        self.invoke_hook()
        self.assertEqual(backfill.run_state(self.root, self.run_id), 'indexed')

    def test_explicit_current_result_remains_authoritative(self):
        self.stage()
        self.recover_historical_parent()
        self.ctx.index_published = False
        self.assert_failed()
        self.ctx.index_published = True
        self.invoke_hook()

    def test_absent_unknown_wrong_run_and_unreadable_proof_fail(self):
        self.stage()
        self.recover_historical_parent()
        for run_id in ('', 'unknown-run', backfill.ensure_run(self.root, 'manual')):
            with self.subTest(run_id=run_id):
                upgrade_lib.update_upgrade_lock(self.root, memory_backfill_run_id=run_id)
                self.assert_failed()
        upgrade_lib.update_upgrade_lock(self.root, memory_backfill_run_id=self.run_id)
        with patch.object(backfill, 'reconcile_index_publication', side_effect=OSError('unreadable')):
            self.assert_failed()

    def test_wrong_root_checkpoint_does_not_authorize_indexed_run(self):
        self.stage()
        self.recover_historical_parent()
        checkpoint = upgrade_lib.read_upgrade_lock(self.root)
        checkpoint['root'] = str(self.root / 'other')
        upgrade_lib.upgrade_lock_path(self.root).write_text(json.dumps(checkpoint))
        self.assert_failed()

    def mismatched_publication(self, column, value):
        self.stage()
        with patch.object(backfill, 'record_publication_success', return_value=False):
            self.recover_historical_parent()
        conn = backfill._connect(self.root)
        try:
            conn.execute(f'UPDATE memory_backfill_runs SET {column}=? WHERE run_id=?', (value, self.run_id))
            conn.commit()
        finally:
            conn.close()
        self.assert_failed()

    def test_mismatched_attempt_fails_closed(self):
        self.mismatched_publication('publication_attempt_id', 'unrelated-build')

    def test_mismatched_generation_fails_closed(self):
        self.mismatched_publication('publication_generation', 99999)

    def test_stale_inventory_digest_fails_closed(self):
        self.mismatched_publication('publication_inventory_digest', 'stale-inventory')

    def test_new_closed_wave_invalidates_recorded_publication(self):
        import record_paths
        import vocabulary_profile
        self.stage()
        self.recover_historical_parent()
        wave = record_paths.load_record_roots(self.root).waves / '00001 new-history'
        wave.mkdir(parents=True)
        (wave / vocabulary_profile.RECORD_FILENAME).write_text('# Historical wave\n\nStatus: closed\n')
        self.assertTrue(backfill.inventory_closed_waves(self.root))
        self.assert_failed()


if __name__ == '__main__':
    unittest.main()

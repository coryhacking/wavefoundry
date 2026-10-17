"""Supported old runners pass through advisory memory inventory into plain indexing.

The text fixture is the released v1.31.0 runner (0e9f1db9). Its layout literals
remain text so a distribution can rename them along with the current sources.
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, Mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import memory_backfill as backfill
import upgrade_extensions as hooks
import upgrade_lib
import upgrade_wavefoundry
import review_policy_upgrade
import sqlite_storage_migration
import venv_bootstrap
import vocabulary_profile
from record_layout_support import waves_dir


class OldParentPublicationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        (self.root / '.wavefoundry/index').mkdir(parents=True)
        waves = waves_dir(self.root)
        waves.mkdir(parents=True)
        wave = waves / '1abc closed'
        wave.mkdir()
        (wave / vocabulary_profile.RECORD_FILENAME).write_text('# Wave\n\nStatus: closed\n')
        self.manual = backfill.ensure_run(self.root, 'manual')

    def parent(self, archived):
        parent = types.ModuleType('supported_upgrade_parent_' + str(id(self)))
        source = (SCRIPTS / 'tests/fixtures/upgrade_old_runner/upgrade_runner_v1_31_0.py.txt'
                  if archived else SCRIPTS / 'upgrade_wavefoundry.py')
        parent.__file__ = str(source)
        self.enterContext(patch.dict(sys.modules, {parent.__name__: parent}))
        exec(compile(source.read_bytes(), str(source), 'exec'), parent.__dict__)
        # The archived runner resolves its sibling root from __file__; make that
        # root the installed scripts, exactly as extraction would on a target.
        parent.SCRIPTS_DIR = SCRIPTS
        return parent

    def drive(self, *, archived=True, inventory_failure=False, corrupt=False,
              index_result=True, hook_exit=None):
        parent = self.parent(archived)
        self.last_parent = parent
        if corrupt:
            (self.root / '.wavefoundry/index/memory-state.sqlite').write_bytes(b'not sqlite')
        original_loader = hooks._installed_memory_backfill
        inventory_calls = []
        def load(root):
            module = original_loader(root)
            original_inventory = module._inventory
            def observed_inventory(root):
                inventory_calls.append(root)
                if inventory_failure:
                    raise OSError('PRIVATE_PATH_MUST_NOT_LEAK')
                return original_inventory(root)
            self.enterContext(patch.object(module, '_inventory', side_effect=observed_inventory))
            return module
        visited = []
        def run_hook(name, ctx, ext):
            if name in {'post_docs_gate', 'pre_index_update', 'post_index_update'}:
                visited.append(name)
                if name == 'pre_index_update' and hook_exit is not None:
                    raise SystemExit(hook_exit)
                getattr(hooks, name)(ctx)
        phase = Mock()
        def observed_phase(root):
            phase(root)
            return index_result
        self.enterContext(patch.object(parent, 'phase_index_update', observed_phase))
        self.enterContext(patch.object(hooks, '_installed_memory_backfill', side_effect=load))
        self.enterContext(patch.object(hooks, 'enforce_index_guard_handoff'))
        self.enterContext(patch.object(hooks, 'pre_extract'))
        self.enterContext(patch.object(sqlite_storage_migration, 'prepare_upgrade'))
        self.enterContext(patch.object(parent, 'phase_preflight', return_value=('1.30.0', '1.31.0', None)))
        self.enterContext(patch.object(parent, '_load_extension_module', return_value=None))
        self.enterContext(patch.object(parent, '_run_hook', side_effect=run_hook))
        for name in ('phase_surface_rendering', 'phase_docs_gate', 'materialize_secrets_policy',
                     'materialize_lifecycle_policy', '_emit_primary_summary_via_delegate_or_fallback'):
            self.enterContext(patch.object(parent, name))
        self.enterContext(patch.object(parent, 'phase_pruning', return_value=0))
        self.enterContext(patch.object(parent, 'phase_review_evidence_sidecar_cleanup', return_value={}))
        self.enterContext(patch.object(parent, '_snapshot_pre_extract_chunker_versions', return_value={}))
        self.enterContext(patch.object(parent, '_snapshot_pre_extract_versions', return_value={}))
        self.enterContext(patch.object(parent, '_stamp_manifest_revision', return_value=False))
        self.enterContext(patch.object(review_policy_upgrade, 'plan_review_policy_upgrade', return_value={}))
        self.enterContext(patch.object(review_policy_upgrade, 'apply_review_policy_upgrade', return_value={}))
        self.enterContext(patch.object(venv_bootstrap, 'ensure_python_resolves', return_value='ok'))
        self.enterContext(patch.dict(os.environ, {'WAVEFOUNDRY_SKIP_PYTHON_HEAL': '1'}))
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            if hook_exit is not None or archived and not index_result:
                with self.assertRaises(SystemExit) as caught:
                    parent.main(['--root', str(self.root), '--yes'])
                result = caught.exception.code
            else:
                result = parent.main(['--root', str(self.root), '--yes'])
        return result, visited, inventory_calls, phase, output.getvalue()

    def test_archived_main_and_new_hook_inventory_once_and_do_not_touch_manual_run(self):
        result, visited, inventory, phase, output = self.drive()
        self.assertEqual(result, 0, output)
        self.assertEqual(visited, ['post_docs_gate', 'pre_index_update', 'post_index_update'])
        self.assertEqual(len(inventory), 1)
        phase.assert_called_once_with(self.root)
        run = backfill.latest_run_id(self.root, 'upgrade')
        summary = backfill.run_summary(self.root, run)
        self.assertEqual(summary['state'], 'indexed')
        self.assertEqual(summary['candidates_drafted'], 0)
        self.assertEqual(summary['remaining_waves'], 1)
        conn = backfill._connect(self.root)
        try:
            self.assertEqual(conn.execute('SELECT state FROM memory_backfill_runs WHERE run_id=?', (self.manual,)).fetchone()[0], 'inventory_pending')
        finally:
            conn.close()
        self.assertNotIn('requires bounded extraction', output)

    def test_new_main_has_no_memory_gate_fields(self):
        result, visited, inventory, phase, output = self.drive(archived=False)
        self.assertEqual(result, 0, output)
        self.assertEqual(len(inventory), 1)
        phase.assert_called_once_with(self.root)
        lock = upgrade_lib.read_upgrade_lock(self.root)
        self.assertFalse(any(key.startswith('memory_backfill_') for key in lock))
        self.assertNotEqual((lock.get('action_required') or {}).get('kind'), 'historical_memory')
        self.assertEqual(lock['historical_memory_report']['closed_waves_without_memory'], 1)
        parent = self.last_parent
        with contextlib.ExitStack() as controls:
            controls.enter_context(patch.object(parent, '_find_zip', return_value=None))
            for name in ('_ensure_lifecycle_policy_backstop', '_ensure_rendered_permissions_backstop',
                         '_regenerate_codebase_map_on_upgrade', '_record_setup_baseline',
                         '_warn_if_background_code_incomplete', '_warn_if_migration_errors',
                         '_remove_deprecated_framework_index', '_print_operator_summary'):
                controls.enter_context(patch.object(parent, name))
            controls.enter_context(contextlib.redirect_stdout(io.StringIO()))
            controls.enter_context(contextlib.redirect_stderr(io.StringIO()))
            self.assertEqual(parent.main(['--root', str(self.root), '--cleanup']), 0)
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))
        self.assertEqual(len(inventory), 1)

    def test_archived_main_unreadable_inventory_is_advisory(self):
        result, visited, inventory, phase, output = self.drive(inventory_failure=True)
        self.assertEqual(result, 0, output)
        self.assertEqual(len(inventory), 1)
        phase.assert_called_once_with(self.root)
        self.assertIn('post_index_update', visited)
        self.assertNotIn('PRIVATE_PATH_MUST_NOT_LEAK', output)
        self.assertEqual(upgrade_lib.read_upgrade_lock(self.root)['historical_memory_report']['status'], 'unavailable')

    def test_archived_main_corrupt_store_is_advisory(self):
        result, visited, inventory, phase, output = self.drive(corrupt=True)
        self.assertEqual(result, 0, output)
        self.assertIn('post_index_update', visited)
        phase.assert_called_once_with(self.root)
        self.assertEqual(upgrade_lib.read_upgrade_lock(self.root)['historical_memory_report']['status'], 'unavailable')

    def test_new_main_unreadable_inventory_is_advisory(self):
        result, visited, inventory, phase, output = self.drive(archived=False, inventory_failure=True)
        self.assertEqual(result, 0, output)
        self.assertEqual(len(inventory), 1)
        phase.assert_called_once_with(self.root)
        self.assertIn('post_index_update', visited)
        self.assertNotIn('PRIVATE_PATH_MUST_NOT_LEAK', output)
        self.assertEqual(upgrade_lib.read_upgrade_lock(self.root)['historical_memory_report']['status'], 'unavailable')

    def test_new_main_corrupt_store_is_advisory(self):
        result, visited, inventory, phase, output = self.drive(archived=False, corrupt=True)
        self.assertEqual(result, 0, output)
        phase.assert_called_once_with(self.root)
        self.assertIn('post_index_update', visited)
        self.assertEqual(upgrade_lib.read_upgrade_lock(self.root)['historical_memory_report']['status'], 'unavailable')

    def test_archived_system_exit_preserves_real_failure(self):
        result, visited, inventory, phase, output = self.drive(hook_exit=2)
        self.assertEqual(result, 2)
        self.assertEqual(upgrade_lib.read_upgrade_lock(self.root)['failed_phase'], 'index_update')
        phase.assert_not_called()
        self.assertIn('Upgrade failed', output)

    def test_archived_index_failure_is_ordinary_recoverable_failure(self):
        result, visited, inventory, phase, output = self.drive(index_result=False)
        self.assertEqual(result, 1, output)
        self.assertIn('post_index_update', visited)
        lock = upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(lock['failed_phase'], 'index_update')
        import sqlite_storage_migration
        self.assertEqual(sqlite_storage_migration._checkpoint_resume_flag(lock), '--update-index')

    def test_legacy_memory_shapes_recover_through_plain_update_then_cleanup(self):
        parent = self.parent(False)
        shapes = [
            {"action_required": {"kind": "historical_memory", "state": "awaiting_memory_validation"}},
            {"failed_phase": "awaiting_memory_validation"},
            {"failed_phase": "historical_memory_backfill"},
            {"current_phase": "awaiting_memory_publication"},
            {"current_phase": "memory_resume_preflight"},
            {"current_phase": "awaiting_memory_validation", "failed_phase": "index_update"},
        ]
        for shape in shapes:
            with self.subTest(shape=shape), contextlib.ExitStack() as controls:
                upgrade_lib.write_upgrade_lock(self.root, "1.30.0", "1.31.0")
                upgrade_lib.update_upgrade_lock(self.root, memory_backfill_run_id="legacy", memory_backfill_pending=1, **shape)
                controls.enter_context(patch.object(parent, "_find_zip", return_value=None))
                controls.enter_context(patch.object(parent, "_load_extension_module", return_value=None))
                controls.enter_context(patch.object(parent, "phase_review_evidence_sidecar_cleanup", return_value={}))
                controls.enter_context(patch.object(parent, "phase_index_update", return_value=True))
                for name in ("_ensure_lifecycle_policy_backstop", "_ensure_rendered_permissions_backstop", "_regenerate_codebase_map_on_upgrade", "_record_setup_baseline", "_warn_if_background_code_incomplete", "_warn_if_migration_errors", "_remove_deprecated_framework_index", "_print_operator_summary"):
                    controls.enter_context(patch.object(parent, name))
                controls.enter_context(contextlib.redirect_stdout(io.StringIO()))
                controls.enter_context(contextlib.redirect_stderr(io.StringIO()))
                self.assertEqual(parent.main(["--root", str(self.root), "--resume-after-memory"]), 0)
                lock = upgrade_lib.read_upgrade_lock(self.root)
                self.assertFalse(any(key.startswith("memory_backfill_") for key in lock))
                self.assertIsNone(lock.get("action_required"))
                self.assertIsNone(lock.get("failed_phase"))
                self.assertEqual(lock["current_phase"], "index_complete")
                self.assertTrue(lock["index_rebuilt_at"])
                self.assertEqual(parent.main(["--root", str(self.root), "--cleanup"]), 0)
                self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))

"""Recovery guidance pins on real setup, publication and registered MCP consumers."""
from __future__ import annotations
import asyncio
import contextlib
import io
import importlib
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import sqlite_storage_migration as migration
import setup_reconciliation as setup
import upgrade_extensions as extensions
import upgrade_wavefoundry as upgrade
import upgrade_bundle
import publication_control
from server_tools_support import load_server, load_thin_runner, _make_repo


class ResumeGuidanceTests(unittest.TestCase):
    def setUp(self):
        global migration
        migration = importlib.import_module('sqlite_storage_migration')
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "operator's repo"
        self.root.mkdir()

    def assert_guidance(self, text, flag='--resume-after-memory'):
        self.assertIn(str(self.root), text.replace("'\"'\"'", "'").replace("''", "'"))
        for term in (flag, '--yes', '--confirm-hosts-stopped', 'Operator-run', 'external terminal', 'every Wavefoundry host is stopped', 'agents must not execute'):
            self.assertIn(term, text)

    def test_fixed_flags_order_and_platform_quoting(self):
        for platform in ('posix', 'nt'):
            with self.subTest(platform=platform), patch.object(migration, 'os', SimpleNamespace(**{**vars(os), 'name': platform})):
                result = migration.resume_guidance(self.root, resume_flag='--resume-after-memory')
                expected = [sys.executable, str(self.root / '.wavefoundry/framework/scripts/upgrade_wavefoundry.py'), '--root', str(self.root), '--resume-after-memory', '--yes', '--confirm-hosts-stopped']
                self.assertEqual(result['command_argv'], expected)
                self.assertNotIn('--pack', expected)
                self.assertTrue(result['operator_run'])
                self.assertTrue(result['requires_hosts_stopped'])
                self.assertFalse(result['agent_execution_allowed'])
                self.assert_guidance(result['guidance'])
                if platform == 'nt':
                    self.assertEqual(result['command'], '& ' + ' '.join("'" + arg.replace("'", "''") + "'" for arg in expected))
                else:
                    self.assertEqual(shlex.split(result['command']), expected)
        with self.assertRaises(ValueError):
            migration.resume_guidance(self.root, resume_flag='--unapproved')

    def test_foreign_checkpoint_refusal_uses_only_allowlisted_phase(self):
        cases = [({'failed_phase': 'docs_gate'}, '--resume-after-gate'),
                 ({'failed_phase': 'post_docs_gate'}, '--resume-after-gate'),
                 ({'current_phase': 'awaiting_memory_validation'}, '--resume-after-memory'),
                 ({'current_phase': 'awaiting_memory_publication'}, '--resume-after-memory'),
                 ({'failed_phase': 'index_update', 'current_phase': 'memory_resume_preflight'}, '--resume-after-memory'),
                 ({'failed_phase': 'awaiting_memory_validation', 'current_phase': 'docs_gate_complete'}, '--resume-after-gate'),
                 ({'failed_phase': 'index_update'}, '--update-index'),
                 ({'current_phase': 'index_rebuild'}, '--update-index'),
                 ({'current_phase': 'index_complete'}, '--cleanup'),
                 ({'failed_phase': 'cleanup'}, '--cleanup'),
                 ({'current_phase': 'unknown'}, None),
                 ({'current_phase': ['--cleanup'], 'failed_phase': {'flag': '--cleanup'}}, None),
                 ({'failed_phase': '--cleanup --pack evil', 'current_phase': '--resume-after-memory'}, None)]
        for checkpoint, flag in cases:
            with self.subTest(checkpoint=checkpoint):
                with patch.object(migration, 'read_receipt', return_value=None) as receipt, patch.object(setup.upgrade_lib, 'read_upgrade_lock', return_value=checkpoint) as lock:
                    with self.assertRaises(migration.MigrationRequired) as refused:
                        setup.session(self.root, [])._inspect()
                receipt.assert_called_once_with(self.root / '.wavefoundry/index')
                lock.assert_called_once_with(self.root)
                self.assertIn('storage_setup_foreign_upgrade', str(refused.exception))
                if flag:
                    self.assert_guidance(str(refused.exception), flag)
                else:
                    self.assertEqual(str(refused.exception), 'storage_setup_foreign_upgrade: finish the recorded upgrade before wf setup; checkpoint retained')

    def test_foreign_receipt_and_mixed_version_guard(self):
        checkpoint = {'current_phase': 'awaiting_memory_validation'}
        receipt = {'state': 'complete', 'entry_path': 'upgrade'}
        for old in ('missing', 'old_restart'):
            with self.subTest(old=old), contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(migration, 'read_receipt', return_value=receipt))
                stack.enter_context(patch.object(setup.upgrade_lib, 'read_upgrade_lock', return_value=checkpoint))
                if old == 'missing':
                    helper = stack.enter_context(patch.object(migration, 'resume_guidance', None))
                else:
                    def old_restart(root, pack_path, rebuild_storage=False):
                        return {'command': 'legacy'}
                    restart = stack.enter_context(patch.object(migration, 'restart_command', side_effect=old_restart))
                with self.assertRaisesRegex(migration.MigrationRequired, 'storage_setup_foreign_upgrade') as caught:
                    setup.session(self.root, [])._inspect()
                self.assertNotIn('Operator-run', str(caught.exception))
                if old == 'old_restart':
                    restart.assert_called_once_with(self.root, None, resume_flag='--resume-after-memory')

    def test_typed_action_and_pause_share_one_command(self):
        ctx = SimpleNamespace(root=self.root, from_version='current')
        with patch.object(extensions, '_update_upgrade_state') as write, contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as stopped:
                extensions._pause_for_memory_action(ctx, state='awaiting_memory_validation', run_id='run', message='memory_validate then resume_after_memory')
        self.assertEqual(stopped.exception.code, 4)
        write.assert_called_once()
        action = write.call_args.kwargs['action_required']
        expected = migration.resume_guidance(self.root, resume_flag='--resume-after-memory')
        for key, value in expected.items():
            self.assertEqual(action[key], value)
        self.assert_guidance(output.getvalue())
        with contextlib.redirect_stdout(io.StringIO()) as rendered:
            upgrade._report_action_required_pause(action, self.root)
        self.assert_guidance(rendered.getvalue())

    def test_bundle_nextstep_and_publication_renderers_have_root(self):
        self.assert_guidance(upgrade_bundle._recovery(self.root, {}, 'awaiting_memory_validation')['instruction'])
        handlers = importlib.import_module('wf_server.upgrade_handlers')
        self.assert_guidance(handlers._upgrade_next_step('resume_after_gate', self.root)[0])
        for pending in (0, 1, None):
            text = publication_control._checkpoint_recovery_tail({'current_phase': 'awaiting_memory_validation', 'memory_backfill_pending': pending}, self.root)
            self.assert_guidance(text)
            if pending == 0:
                self.assertIn('recover in order', text)
            else:
                self.assertIn('memory_validate', text)
        self.assertNotIn('--resume', publication_control._checkpoint_recovery_tail({'current_phase': '--evil'}, self.root))
    def test_old_protocol_post_docs_message_and_publication_boundary(self):
        checkpoint = self.root / '.wavefoundry/upgrade-in-progress.json'
        checkpoint.parent.mkdir()
        checkpoint.write_text('{}')
        summary = {'state': 'awaiting_validation', 'remaining_waves': 1, 'candidates_pending': 0, 'failures': 0, 'last_failure': None}
        backfill = SimpleNamespace(ensure_run=unittest.mock.Mock(return_value='run'), sync_inventory=unittest.mock.Mock(return_value=summary))
        ctx = SimpleNamespace(root=self.root, from_version='current', runner_protocol=1)
        with patch.object(extensions, '_installed_memory_backfill', return_value=backfill) as loaded, contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as stopped:
                extensions.post_docs_gate(ctx)
        self.assertEqual(stopped.exception.code, 4)
        loaded.assert_called_once_with(self.root)
        backfill.ensure_run.assert_called_once_with(self.root, 'upgrade')
        backfill.sync_inventory.assert_called_once_with(self.root, 'run')
        self.assert_guidance(output.getvalue())
        self.assert_guidance(publication_control.publication_checkpoint_reason(self.root, 'index_build'))

    def test_real_memory_handler_and_typed_mcp_pause_render_cli(self):
        server = load_server()
        _make_repo(self.root)
        response = server.memory_backfill_response(self.root, mode='create', entry_path='upgrade')
        self.assertEqual(response['status'], 'ok')
        self.assert_guidance(response['usage'])
        backfill = server._load_script('memory_backfill')
        run_id = backfill.ensure_run(self.root, 'upgrade')
        import upgrade_lib
        upgrade_lib.write_upgrade_lock(self.root, 'old', 'new')
        for state in ('awaiting_memory_validation', 'awaiting_memory_publication'):
            action = {'kind': 'historical_memory', 'resume_phase': 'resume_after_memory', 'run_id': run_id, 'state': state, 'token': 'fixture-token', **migration.resume_guidance(self.root, resume_flag='--resume-after-memory')}
            upgrade_lib.update_upgrade_lock(self.root, memory_backfill_run_id=run_id, current_phase=state, action_required=action)
            with patch.object(server, '_mcp_subprocess_run', return_value=__import__('subprocess').CompletedProcess([], 4, 'memory pause', '')) as spawn:
                response = server.wf_upgrade_response(self.root)
            spawn.assert_called_once()
            self.assertEqual(response['status'], 'ok')
            self.assert_guidance(response['next_step'])
            self.assertEqual(response['data']['action_required']['command_argv'], action['command_argv'])

    def test_extension_validation_publication_and_postindex_messages(self):
        checkpoint = self.root / '.wavefoundry/upgrade-in-progress.json'
        checkpoint.parent.mkdir()
        checkpoint.write_text(json.dumps({'memory_backfill_run_id': 'run'}))
        ctx = SimpleNamespace(root=self.root, from_version='current')
        for state in ('awaiting_validation', 'ready_for_index'):
            summary = {'state': state, 'candidates_drafted': 1}
            backfill = SimpleNamespace(reconcile_index_publication=unittest.mock.Mock(return_value=summary))
            with self.subTest(state=state), patch.object(extensions, 'enforce_index_guard_handoff') as guard, patch.object(extensions, '_bridge_index_publisher_grant') as grant, patch.object(extensions, '_installed_memory_backfill', return_value=backfill) as loaded, contextlib.redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(SystemExit) as stopped:
                    extensions.pre_index_update(ctx)
            self.assertEqual(stopped.exception.code, 4)
            guard.assert_called_once_with(ctx)
            grant.assert_called_once()
            loaded.assert_called_once_with(self.root)
            backfill.reconcile_index_publication.assert_called_once_with(self.root, 'run')
            self.assert_guidance(output.getvalue())
            action = json.loads(checkpoint.read_text())['action_required']
            self.assertEqual(action['command_argv'], migration.resume_guidance(self.root, resume_flag='--resume-after-memory')['command_argv'])
            self.assertFalse(action['agent_execution_allowed'])
        ctx.index_published = True  # The index succeeded; candidate publication still needs its owner.
        with patch.object(extensions, '_installed_memory_backfill', return_value=backfill) as loaded:
            with self.assertRaises(RuntimeError) as stopped:
                extensions.post_index_update(ctx)
        loaded.assert_called_once_with(self.root)
        self.assert_guidance(str(stopped.exception))



class RegisteredGapGuidanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = _make_repo(Path(temporary.name).resolve() / "operator's repo")
        self.runner = load_thin_runner()
        self.mcp = self.runner.build_server(self.root)

    def call(self, name):
        result = self.mcp._tool_manager._tools[name].fn()
        return asyncio.run(result) if hasattr(result, '__await__') else result

    def test_actual_gap_marker_at_both_top_level_boundaries(self):
        marker = self.root / '.wavefoundry/logs/context-efficiency.gap'
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_bytes(b'')
        for name in ('wf_upgrade', 'wf_reload_mcp'):
            with self.subTest(name=name), patch.object(self.runner, 'perform_mcp_reload') as reload, patch.object(self.server, 'wf_upgrade_response') as child:
                result = self.call(name)
            reload.assert_not_called()  # Projection refusal precedes a live reload.
            child.assert_not_called()  # Projection refusal precedes upgrade spawning.
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['data']['projection']['detail']['authority_status'], 'accounting_gap')
            text = result['usage']
            self.assertIn('./.wavefoundry/bin/wf clear-accounting-gap', text)
            self.assertIn(shlex.quote(str(self.root)), text)
            for term in ('discards no waves, docs or memories', 'unsealed, non-closed', 'accounting_gap', 'totals stay flagged incomplete', 'not backfilled'):
                self.assertIn(term, text)
            self.assertTrue(marker.exists())

    def test_non_gap_failure_keeps_prior_text_and_windows_is_only_rendered(self):
        projection = {'ok': False, 'detail': {'authority_status': 'unavailable'}}
        with patch.object(self.server, 'project_pending_context_efficiency', return_value=projection) as project:
            upgrade_response, reload_response = self.call('wf_upgrade'), self.call('wf_reload_mcp')
        self.assertEqual(project.call_count, 2)
        self.assertEqual(upgrade_response['usage'], 'Resolve the projection failure, then retry wf_upgrade.')
        self.assertEqual(reload_response['usage'], 'Resolve the projection failure, then call wf_reload_mcp() again.')
        with patch.object(migration, 'os', SimpleNamespace(**{**vars(os), 'name': 'nt'})):
            text = migration.accounting_gap_guidance(self.root)
        self.assertIn(r'.\.wavefoundry\bin\wf.cmd clear-accounting-gap', text)
        self.assertIn("'" + str(self.root).replace("'", "''") + "'", text)


if __name__ == '__main__':
    unittest.main()

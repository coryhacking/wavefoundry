"""Field upgrade failures exercised through runner/handler public consumers."""
from __future__ import annotations
import ast
import contextlib
import io
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import sqlite_storage_migration as migration
import upgrade_wavefoundry as upgrade
import upgrade_lib
import lifecycle_lock
import review_policy_upgrade
from server_tools_support import load_server, load_thin_runner, _make_repo


class PendingUpgradeTests(unittest.TestCase):
    """Public default routes must stop before discovery and retained-state writes."""

    def setUp(self):
        global migration
        migration = importlib.import_module('sqlite_storage_migration')
        self.tmp = tempfile.TemporaryDirectory(prefix='wf pending ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.pack = self.root / 'wavefoundry-1.0.0.retained.zip'
        import zipfile
        with zipfile.ZipFile(self.pack, 'w') as archive:
            archive.writestr('.wavefoundry/framework/VERSION', '1.0.0+retained\n')
        self.newer = self.root / 'wavefoundry-99.0.0.newer.zip'
        self.newer.write_bytes(self.pack.read_bytes())
        upgrade_lib.write_upgrade_lock(self.root, '0.9.0', '1.0.0+retained', self.pack)
        upgrade_lib.update_upgrade_lock(self.root, pid=999999999, current_phase='awaiting_memory_validation',
            failed_phase='awaiting_memory_validation', memory_backfill_run_id='retained-run',
            action_required={'kind': 'historical_memory', 'state': 'awaiting_memory_validation',
                             'resume_phase': 'resume_after_memory', 'token': 'retained-token', 'run_id': 'retained-run'})
        self.checkpoint = upgrade_lib.upgrade_lock_path(self.root)
        self.log = self.root / '.wavefoundry/logs/upgrade.log'
        self.log.parent.mkdir(parents=True)
        self.log.write_bytes(b'RETAINED LOG')

    def invoke(self, *args):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        results = []
        for mode in ((), ('--dry-run',)):
            out, err = io.StringIO(), io.StringIO()
            with patch.object(upgrade, '_find_zip', side_effect=AssertionError('pack discovery reached')), \
                    patch.object(upgrade, '_find_latest_release_zip', side_effect=AssertionError('latest discovery reached')), \
                    patch.object(migration, 'restore_checkpoint', side_effect=AssertionError('checkpoint restoration reached')), \
                    patch.object(upgrade, '_load_extension_module', side_effect=AssertionError('incoming hook load reached')), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = upgrade.main(['--root', str(self.root), '--yes', *mode, *args])
            after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
            self.assertEqual(after, before)
            output = out.getvalue() + err.getvalue()
            self.assertNotIn('would be cleared', output)
            results.append((code, output))
        self.assertEqual(results[0][0], results[1][0], results)
        return results[1]

    def test_live_owner_and_legacy_stale_have_no_new_disposal_authority(self):
        upgrade_lib.update_upgrade_lock(self.root, pid=os.getpid())
        self.assertEqual(self.invoke()[0], 5)
        self.checkpoint.write_text(json.dumps({'pid': 999999999, 'started_at': 'now',
            'to_version': '1.0.0+retained', 'current_phase': 'unknown'}))
        code, output = self.invoke()
        self.assertEqual(code, 3, output)
        self.assertIn('upgrade_checkpoint_ambiguous', output)

    def test_setup_owned_checkpoint_is_refused_by_both_routes(self):
        upgrade_lib.update_upgrade_lock(self.root, entry_path='setup')
        code, output = self.invoke()
        self.assertEqual(code, 3, output)
        self.assertIn('storage_setup_resume_required', output)

    def test_default_memory_pause_precedes_newer_pack_and_stale_cleanup(self):
        for args in ((), ('--pack', str(self.newer)), ('--pack', str(self.pack))):
            with self.subTest(args=args):
                code, output = self.invoke(*args)
                self.assertEqual(code, 5, output)
                self.assertIn('--resume-after-memory', output)
                self.assertIn('retained-run', output)
                self.assertIn('1.0.0+retained', output)

    def test_contract_state_matrix_reports_existing_phase(self):
        for current, failed, flag in (
                ('awaiting_memory_publication', None, '--resume-after-memory'),
                ('memory_resume_preflight', 'index_update', '--resume-after-memory'),
                ('docs_gate', 'docs_gate', '--resume-after-gate'),
                ('docs_gate_complete', 'post_docs_gate', '--resume-after-gate'),
                ('docs_gate_complete', 'awaiting_memory_validation', '--resume-after-gate'),
                ('index_update', 'index_publication_failed', '--update-index'),
                ('index_complete', None, '--cleanup'),
                ('cleanup', 'dashboard_restart', '--cleanup'),
                ('cleanup', 'retired_model_cleanup', '--cleanup')):
            with self.subTest(current=current, failed=failed):
                upgrade_lib.update_upgrade_lock(self.root, current_phase=current, failed_phase=failed, action_required=None)
                code, output = self.invoke()
                self.assertEqual(code, 5, output)
                self.assertIn(flag, output)

    def test_invalid_unknown_unreadable_and_pack_change_refuse_read_only(self):
        valid = self.checkpoint.read_bytes()
        for value in (b'{', b'[]', b'null', b'{}', json.dumps({'started_at': 'now', 'to_version': '1', 'current_phase': 'unknown'}).encode()):
            with self.subTest(value=value):
                self.checkpoint.write_bytes(value)
                code, output = self.invoke()
                self.assertEqual(code, 3, output)
                self.assertIn('preserve', output.lower())
        self.checkpoint.write_bytes(valid)
        with patch.object(upgrade_lib, 'read_upgrade_lock', return_value={}), \
                patch.object(upgrade_lib, 'upgrade_lock_unreadable_cause', return_value='Permission denied'):
            code, output = self.invoke()
        self.assertEqual(code, 3)
        self.assertIn('Restore access', output)
        self.pack.write_bytes(b'changed archive')
        code, output = self.invoke()
        self.assertEqual(code, 3, output)
        self.assertIn('original package', output)

    def test_real_cli_and_registered_mcp_default_path_report_pending(self):
        server = load_server()
        from mcp.server.fastmcp import FastMCP
        from types import SimpleNamespace
        mcp = FastMCP('pending-upgrade-fixture')
        server.register_mcp_surface(mcp, lambda: SimpleNamespace(root=self.root))
        registered = mcp._tool_manager._tools['wf_upgrade'].fn
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', WAVEFOUNDRY_DISABLE_BYTECODE_CACHE='1')
        env.pop('PYTHONPYCACHEPREFIX', None)
        before = self.checkpoint.read_bytes()
        def child(cmd, **kwargs):
            if '--dry-run' in cmd:
                self.assertIn('--confirm-hosts-stopped', cmd)
            return subprocess.run([sys.executable, '-B', str(SCRIPTS / 'upgrade_wavefoundry.py'), *cmd[2:]],
                                  cwd=self.root, env=env, capture_output=True, text=True, timeout=20)
        with patch.object(server, '_mcp_subprocess_run', side_effect=child), \
                patch.object(server, 'project_pending_context_efficiency', return_value={'ok': True}), \
                patch('wf_server.upgrade_handlers._reload_live_runner') as reload:
            for response in (registered(), server.wf_upgrade_response(self.root, mode='dry_run', phase='cleanup', confirm_hosts_stopped=True)):
                self.assertEqual(response['status'], 'action_required', response)
                self.assertEqual(response['data']['code'], 'upgrade_pending')
                self.assertEqual(response['data']['state'], 'awaiting_memory_validation')
                self.assertEqual(response['data']['action_required']['run_id'], 'retained-run')
                self.assertIn('--resume-after-memory', response['next_step'])
        self.assertEqual(self.checkpoint.read_bytes(), before)
        self.assertEqual(self.log.read_bytes(), b'RETAINED LOG')
        reload.assert_not_called()

    def test_preview_refuses_copied_identity_without_reaching_hooks(self):
        self.durable()
        value = json.loads(self.checkpoint.read_bytes())
        value['index_guard_handoff']['root_identity']['inode'] = -1
        self.checkpoint.write_text(json.dumps(value))
        code, output = self.invoke()
        self.assertEqual(code, 3, output)
        self.assertIn('index_guard', output)
        server = load_server()
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        env.pop('PYTHONPYCACHEPREFIX', None)
        def child(cmd, **kwargs):
            return subprocess.run([sys.executable, '-B', str(SCRIPTS / 'upgrade_wavefoundry.py'), *cmd[2:]],
                                  cwd=self.root, env=env, capture_output=True, text=True, timeout=20)
        before = self.checkpoint.read_bytes()
        with patch.object(server, '_mcp_subprocess_run', side_effect=child), \
                patch('wf_server.upgrade_handlers._reload_live_runner') as reload:
            for mode in ('apply', 'dry_run'):
                response = server.wf_upgrade_response(self.root, mode=mode)
                self.assertEqual(response['status'], 'error', response)
                self.assertEqual(response['data']['exit_code'], 3)
                self.assertIn('index_guard', response['data']['output'])
                self.assertNotIn('would be cleared', response['data']['output'])
                self.assertEqual(self.checkpoint.read_bytes(), before)
        reload.assert_not_called()

    def test_explicit_verified_manifest_retry_previews_selected_pack_only(self):
        framework = self.root / '.wavefoundry/framework'
        framework.mkdir(parents=True, exist_ok=True)
        (framework / 'MANIFEST').write_text('VERSION\n')
        upgrade._save_old_manifest_snapshot(self.root, '1.0.0+retained')
        upgrade_lib.update_upgrade_lock(self.root, current_phase='extract', failed_phase='extract', action_required=None)
        before = self.checkpoint.read_bytes()
        with patch.object(upgrade, '_find_zip', side_effect=AssertionError('ambient discovery reached')), \
                patch.object(migration, 'restore_checkpoint', side_effect=AssertionError('restore reached')), \
                patch.object(upgrade, '_detect_dashboard', return_value=(False, None, None)), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            code = upgrade.main(['--root', str(self.root), '--dry-run', '--pack', str(self.pack), '--confirm-hosts-stopped'])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn(f'Zip to apply:       {self.pack.name}', out.getvalue())
        self.assertEqual(self.checkpoint.read_bytes(), before)

    def test_dry_run_phase_flags_do_not_execute_recovery(self):
        with patch.object(upgrade, 'phase_cleanup', side_effect=AssertionError('cleanup reached')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code = upgrade.main(['--root', str(self.root), '--dry-run', '--cleanup'])
        self.assertEqual(code, 5, out.getvalue())
        self.assertIn('--resume-after-memory', out.getvalue())

    def durable(self):
        import upgrade_extensions as extensions
        retained = self.root / extensions._INDEX_GUARD_PACK_REL
        retained.parent.mkdir(parents=True)
        retained.write_bytes(self.pack.read_bytes())
        identity = self.root.stat()
        digest = extensions._pack_sha256(retained)
        record = {'version': 1, 'required': True, 'prior_runtime_present': True,
                  'prior_capability': False, 'prior_coordinator_capable': False,
                  'root': str(self.root), 'root_identity': {'device': identity.st_dev, 'inode': identity.st_ino},
                  'target_version': '1.0.0+retained', 'token': 'guard-token',
                  'pack_sha256': digest, 'pack_path': str(retained)}
        record['durable_pack'] = {'version': 1, 'path': extensions._INDEX_GUARD_PACK_REL,
            'root': record['root'], 'root_identity': record['root_identity'],
            'token': record['token'], 'target_version': record['target_version'],
            'sha256': digest, 'identity': extensions._guard_file_identity(retained.stat())}
        upgrade_lib.update_upgrade_lock(self.root, zip_path=str(retained), index_guard_handoff=record)
        return retained, record

    def test_durable_pack_identity_digest_and_terminal_absence_are_canonical(self):
        retained, record = self.durable()
        self.assertEqual(self.invoke()[0], 5)
        original = self.checkpoint.read_bytes()
        for field, value in (('token', 'foreign'), ('target_version', '99.0.0'),
                             ('root_identity', {'device': -1, 'inode': -1}), ('sha256', '0' * 64)):
            with self.subTest(field=field):
                changed = json.loads(original)
                changed['index_guard_handoff']['durable_pack'][field] = value
                self.checkpoint.write_text(json.dumps(changed))
                code, output = self.invoke()
                self.assertEqual(code, 3, output)
                self.assertIn('index_guard', output)
        self.checkpoint.write_bytes(original)
        retained.write_bytes(b'changed durable archive')
        self.assertEqual(self.invoke()[0], 3)
        retained.unlink()
        self.assertEqual(self.invoke()[0], 3)
        record['hosts_stopped_confirmed'] = True
        record['terminal_cleanup'] = {'version': 1, 'state': 'fatal_obligations_complete',
            'proof': record['durable_pack'], 'storage_cleanup_complete': True,
            'dashboard_restart_complete': True, 'fatal_cleanup_complete': True}
        upgrade_lib.update_upgrade_lock(self.root, index_guard_handoff=record, current_phase='cleanup',
            failed_phase=None, action_required=None, index_publication_failed=False,
            dashboard_restart_pending=False, memory_backfill_state='indexed')
        code, output = self.invoke()
        self.assertEqual(code, 5, output)
        self.assertIn('--cleanup', output)
        self.assertIn('terminal_cleanup', output)

    def test_memory_identity_mismatch_and_unknown_action_refuse(self):
        action = upgrade_lib.read_upgrade_lock(self.root)['action_required']
        for change in ({'run_id': 'foreign'}, {'token': ''}, {'resume_phase': 'cleanup'},
                       {'state': 'unknown'}, {'kind': 'unknown'}):
            with self.subTest(change=change):
                upgrade_lib.update_upgrade_lock(self.root, action_required={**action, **change})
                code, output = self.invoke()
                self.assertEqual(code, 3, output)


    def test_fresh_default_still_reaches_preflight_and_read_only_modes_discover(self):
        self.checkpoint.unlink()
        with patch.object(upgrade, 'phase_preflight', side_effect=SystemExit(77)) as preflight, \
                patch.object(migration, 'restore_checkpoint', return_value=None), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                upgrade.main(['--root', str(self.root), '--yes'])
        self.assertEqual(stopped.exception.code, 77)
        preflight.assert_called_once()
        with patch.object(upgrade, '_find_latest_release_zip', return_value=self.newer) as finder, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(upgrade.main(['--root', str(self.root), '--detect-zip']), 0)
        finder.assert_called_once()


class EarlyUpgradeLogTests(unittest.TestCase):
    def setUp(self):
        global migration
        migration = importlib.import_module('sqlite_storage_migration')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.log = self.root / '.wavefoundry/logs/upgrade.log'
        self.addCleanup(upgrade._close_log)

    def drive(self, policy_failure=None, **overrides):
        def preflight(*args, **kwargs):
            upgrade._log('PREFLIGHT-PRESERVED')
            return '1.0.0', '2.0.0', None
        defaults = {'phase_preflight': preflight, '_matching_model_bundle': lambda *a: None,
                    '_load_extension_module': lambda *a: None, '_run_hook': lambda *a: None,
                    '_save_old_manifest_snapshot': lambda *a: False,
                    '_snapshot_pre_extract_chunker_versions': lambda *a: (_ for _ in ()).throw(RuntimeError('after old open'))}
        defaults.update(overrides)
        with contextlib.ExitStack() as stack:
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            stack.enter_context(patch.object(migration, 'read_receipt', return_value=None))
            restore = stack.enter_context(patch.object(migration, 'restore_checkpoint'))
            policy = stack.enter_context(patch.object(review_policy_upgrade, 'plan_review_policy_upgrade', return_value=None, side_effect=policy_failure))
            extraction = stack.enter_context(patch('upgrade_extensions.pre_extract'))
            preparation = stack.enter_context(patch.object(migration, 'prepare_upgrade'))
            stack.enter_context(patch.object(upgrade_lib, 'read_upgrade_lock', return_value=None))
            mocks = {}
            for name, value in defaults.items():
                mock = stack.enter_context(patch.object(upgrade, name, side_effect=value))
                mocks[name] = mock
            try:
                return upgrade.main(['--root', str(self.root), '--yes'])
            finally:
                restore.assert_called_once_with(self.root)
                if isinstance(sys.exc_info()[1], __import__('contained_files').ContainedFileRefused):
                    mocks['phase_preflight'].assert_not_called()  # Log refusal precedes preflight.
                else:
                    mocks['phase_preflight'].assert_called_once()
                # These run after the selected preflight/pack/hook/policy/manifest failure.
                if mocks['_snapshot_pre_extract_chunker_versions'].called:
                    extraction.assert_called_once()
                    preparation.assert_called_once()
                else:
                    extraction.assert_not_called()
                    preparation.assert_not_called()
                if mocks['_run_hook'].called:
                    policy.assert_called_once() if policy.called else policy.assert_not_called()
                else:
                    policy.assert_not_called()

    def test_preflight_error_is_logged_and_handle_cleared(self):
        def fails(*a, **k):
            upgrade._err('EARLY-PREFLIGHT-REASON')
            raise SystemExit(1)
        with self.assertRaises(SystemExit):
            self.drive(phase_preflight=fails)
        self.assertIn('EARLY-PREFLIGHT-REASON', self.log.read_text())
        self.assertIsNone(upgrade._log_file)

    def test_no_late_truncate_and_all_early_exits_clear_handle(self):
        with self.assertRaisesRegex(RuntimeError, 'after old open'):
            self.drive()
        self.assertIn('PREFLIGHT-PRESERVED', self.log.read_text())
        self.assertIsNone(upgrade._log_file)
        for kind in ('pack', 'policy', 'manifest', 'hook'):
            with self.subTest(kind=kind):
                fail = lambda *a, **k: (_ for _ in ()).throw(ValueError(kind + '-reason'))
                if kind == 'pack':
                    args = {'phase_preflight': lambda *a, **k: ('1', '2', Path('fixture.zip')), '_stage_pack_for_consumption': fail}
                    self.assertEqual(self.drive(**args), 3)
                elif kind == 'policy':
                    self.assertEqual(self.drive(policy_failure=fail), 1)
                elif kind == 'manifest':
                    self.assertEqual(self.drive(_save_old_manifest_snapshot=fail), 1)
                else:
                    with self.assertRaises(ValueError):
                        self.drive(_run_hook=fail)
                self.assertIsNone(upgrade._log_file)

    def test_lock_refusal_does_not_open_or_write_existing_log(self):
        self.log.parent.mkdir(parents=True)
        self.log.write_bytes(b'LIVE-RUN-BYTES')
        transaction = contextlib.nullcontext()
        current_lifecycle = __import__('lifecycle_lock')
        with patch.object(current_lifecycle, 'lifecycle_publication_transaction', return_value=transaction), \
                patch.object(type(transaction), '__enter__', side_effect=current_lifecycle.LifecycleLockBusy('busy')), \
                patch.object(upgrade, '_open_log') as opened, \
                patch.object(migration, 'read_receipt', return_value=None), \
                patch.object(migration, 'restore_checkpoint') as restore, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(upgrade.main(['--root', str(self.root), '--yes']), 3)
        opened.assert_not_called()  # Inert by design: the refused run owns no log.
        restore.assert_called_once()
        self.assertEqual(self.log.read_bytes(), b'LIVE-RUN-BYTES')

    def test_log_open_exception_releases_lifecycle_transaction(self):
        from contained_files import ContainedFileRefused
        with patch.object(upgrade, '_open_log', side_effect=ContainedFileRefused('fixture refusal')) as opened:
            with self.assertRaisesRegex(ContainedFileRefused, 'fixture refusal'):
                self.drive()
        opened.assert_called_once_with(self.root, mode='w')
        with __import__('lifecycle_lock').lifecycle_publication_transaction(self.root):
            pass
        self.assertIsNone(upgrade._log_file)

    def test_fresh_and_resume_log_refuse_planted_final_link(self):
        if os.name == 'nt':
            self.skipTest('POSIX link creation; Windows reparse branch tested directly')
        self.log.parent.mkdir(parents=True)
        target = self.root / 'kept'
        target.write_text('unchanged')
        self.log.symlink_to(target)
        for mode in ('w', 'a'):
            with self.subTest(mode=mode), contextlib.redirect_stdout(io.StringIO()):
                upgrade._open_log(self.root, mode)
                self.assertIsNone(upgrade._log_file)
                self.assertEqual(target.read_text(), 'unchanged')


class UpgradeOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))

    def test_full_middle_sentinel_diagnostics_and_final_error_survive(self):
        summary = {'index_update': 'publication failed', 'dependency_provisioning_failed': True,
                   'retired_model_cleanup_status': 'failed'}
        full = 'HEAD\n' + 'a'*40000 + '\nWAVE_UPGRADE_SUMMARY_JSON:' + json.dumps(summary) + '\n' + 'b'*40000 + '\nERROR: FINAL-FAILURE\n'
        with patch.object(self.server, '_mcp_subprocess_run', return_value=subprocess.CompletedProcess([], 1, full, '')) as spawn:
            response = self.server.wf_upgrade_response(self.root)
        spawn.assert_called_once()
        data = response['data']
        self.assertIn('HEAD', data['output'])
        self.assertIn('elided', data['output'])
        self.assertIn('FINAL-FAILURE', data['output'])
        self.assertIn('FINAL-FAILURE', data['error_tail'])
        self.assertLessEqual(len(data['error_tail']), 4000)
        self.assertEqual(data['output_total_chars'], len(full))
        self.assertEqual(data['summary']['index_update'], summary['index_update'])
        self.assertTrue({'index_publication_failed', 'dependency_provisioning_failed', 'retired_model_cleanup_failed'} <= {d['code'] for d in response['diagnostics']})
        self.assertLessEqual(len(data['output']), self.server.UPGRADE_OUTPUT_CAP_CHARS)
        with patch.object(self.server, '_mcp_subprocess_run', return_value=subprocess.CompletedProcess([], 0, 'ok', '')) as success:
            self.assertNotIn('error_tail', self.server.wf_upgrade_response(self.root)['data'])
        success.assert_called_once()

    def test_every_envelope_compaction_preserves_tail_and_error_tail(self):
        for oversized in ({'summary': {'body': 's'*99000}}, {'mcp_reload': 'r'*180000}, {'future': 'f'*180000}, {'summary': {'body': '\x01'*180000}}):
            with self.subTest(keys=list(oversized)):
                envelope = {'status': 'error', 'data': {'output': 'HEAD'+('x'*150000)+'ERROR: LAST-REASON',
                    'output_total_chars': 150027, 'error_tail': 'ERROR: LAST-REASON', **oversized}, 'diagnostics': []}
                handlers = importlib.import_module('wf_server.upgrade_handlers')
                response = handlers._bounded_upgrade_response_envelope(envelope)
                self.assertIn('LAST-REASON', response['data']['output'])
                self.assertEqual(response['data']['error_tail'], 'ERROR: LAST-REASON')
                self.assertLessEqual(len(json.dumps(response, ensure_ascii=False)), self.server.UPGRADE_RESPONSE_CAP_CHARS)

    def test_shared_docs_bound_is_unchanged(self):
        text = 'HEAD' + 'x'*60000 + 'TAIL'
        result, truncated = self.server._bounded_subprocess_output(text, cap_chars=60000)
        self.assertTrue(truncated)
        self.assertTrue(result.startswith(text[:60000]))
        self.assertNotIn('TAIL', result)

    def test_large_scrubbed_display_preserves_head_tail_and_raw_recovery_marker(self):
        token = "publisher-known-token-0123456789"
        full = ("\x1b[31mHEAD\x00\r\n" + token + "\n" + "x" * 90000 +
                "\n--resume-after-gate\nFINAL\x85\n")
        with patch.object(self.server, '_mcp_subprocess_run', return_value=subprocess.CompletedProcess([], 7, full, '')), \
                patch.dict(os.environ, {"WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN": token}):
            response = self.server.wf_upgrade_response(self.root)
        data = response['data']
        self.assertEqual(response['status'], 'error')
        self.assertEqual(data['exit_code'], 7)
        self.assertTrue(data['output_truncated'])
        self.assertIn('elided', data['output'])
        self.assertIn('HEAD', data['output'])
        self.assertIn('FINAL', data['output'])
        self.assertIn('[REDACTED]', data['output'])
        for forbidden in (token, '\x1b', '\x00', '\r', '\x85'):
            self.assertNotIn(forbidden, data['output'])
        self.assertIn("wf_upgrade(phase='resume_after_gate')", response['next_step'])


class UpgradeHelperReloadTests(unittest.TestCase):
    def test_reload_refreshes_helpers_and_consumers_preserving_candidate_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = _make_repo(Path(temporary).resolve())
            load_server()
            runner = load_thin_runner()
            try:
                runner.build_server(root)
                # Bind the currently called owners after server loading, rather
                # than an earlier imported module that a reload may have evicted.
                old_tee = importlib.import_module('child_tee')
                old_guidance = importlib.import_module('sqlite_storage_migration')
                runtime = importlib.import_module('runtime_lock')
                old_exception = old_guidance.MigrationRequired
                old_context = old_guidance._candidate_build
                old_runtime_exception = runtime.RuntimeLockError
                old_holds = runtime._PROCESS_RECORD_HOLDS
                old_guard = runtime.process_hold_guard()
                index = root / '.wavefoundry/index'
                index.mkdir(parents=True, exist_ok=True)
                migration_id = 'a' * 32
                work = index / (old_guidance.KIND_WORK_PREFIX + migration_id)
                staging = old_guidance._staging_index_dir(work)
                staging.mkdir(parents=True)
                old_guidance.staged_database_path(staging).write_bytes(b'owned candidate')
                receipt = {'receipt_version': old_guidance.RECEIPT_VERSION_CURRENT,
                    'kind': old_guidance.KIND_SCHEMA8, 'state': 'staged',
                    'migration_id': migration_id, 'index_dir': str(index),
                    'root_identity': old_guidance._identity(root),
                    'staging_pid': os.getpid(), 'work_dir': work.name,
                    'work_identity': old_guidance._identity(work)}
                old_guidance._write(index, receipt)
                candidate_scope = old_guidance._candidate_build_scope(index, receipt, staging)
                candidate_scope.__enter__()
                old_binding = old_context.get()
                self.assertTrue(old_guidance.is_unpublished_candidate(staging))
                hold_path = root / 'registered-hold-control'
                with old_guard:
                    runtime.register_process_hold(hold_path, {'owner': 'reload-control'})
                self.addCleanup(runtime.release_process_hold, hold_path)
                stale_clean = lambda value, token='': 'ERROR: STALE-SANITIZER ' + value
                stale_resume = lambda *args, **kwargs: {'command_argv': ['STALE-RESUME'], 'guidance': 'STALE-RESUME'}
                try:
                    with patch.object(old_tee, 'clean_output', stale_clean), \
                        patch.object(old_guidance, 'resume_guidance', stale_resume):
                        self._assert_reloaded_consumers(runner, root, old_tee, old_guidance,
                            stale_clean, stale_resume, old_exception, old_context,
                            old_binding, staging, runtime, old_runtime_exception,
                            old_holds, old_guard, hold_path)
                finally:
                    try:
                        candidate_scope.__exit__(None, None, None)
                    except ValueError as exc:
                        self.fail('reload replaced the active candidate ContextVar: ' + str(exc))
                    finally:
                        self.assertIsNone(old_context.get())
                self.assertFalse(old_guidance.is_unpublished_candidate(staging))
            finally:
                runner._get_handler().close()

    def _assert_reloaded_consumers(self, runner, root, old_tee, old_guidance,
            stale_clean, stale_resume, old_exception, old_context, old_binding,
            staging, runtime, old_runtime_exception, old_holds, old_guard, hold_path):
        response = runner.perform_mcp_reload()
        self.assertEqual(response['status'], 'ok', response)
        fresh_tee = importlib.import_module('child_tee')
        fresh_guidance = importlib.import_module('sqlite_storage_migration')
        token = '0123456789abcdef' * 4
        decorated = token[:31] + '\x1b[0m' + token[31:]
        value = fresh_tee.clean_output(decorated, token)
        handlers = importlib.import_module('wf_server.upgrade_handlers')
        with patch.dict(os.environ, {'WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN': token}):
            error_tail = handlers._upgrade_error_tail('ERROR: ' + decorated)
        self.assertEqual(error_tail, 'ERROR: [REDACTED]')
        self.assertNotIn('STALE-SANITIZER', error_tail)
        self.assertEqual(value, '[REDACTED]')
        self.assertNotIn('STALE-SANITIZER', value)
        command = fresh_guidance.resume_guidance(root, resume_flag='--resume-after-memory')
        next_step, _ = handlers._upgrade_next_step('resume_after_gate', root)
        self.assertIn('--resume-after-memory', next_step)
        self.assertIn(str(root), next_step)
        self.assertNotIn('STALE-RESUME', next_step)
        self.assertIn(command['command'], next_step)
        argv = command['command_argv']
        self.assertIn('--resume-after-memory', argv)
        self.assertEqual(argv[argv.index('--root') + 1], str(root))
        self.assertNotIn('STALE-RESUME', argv)
        self.assertTrue(command['operator_run'])
        self.assertFalse(command['agent_execution_allowed'])
        self.assertIsNot(fresh_tee, old_tee)
        self.assertIs(fresh_guidance, old_guidance)
        self.assertIs(fresh_guidance.MigrationRequired, old_exception)
        self.assertIs(fresh_guidance._candidate_build, old_context)
        self.assertIs(fresh_guidance._candidate_build.get(), old_binding)
        self.assertTrue(fresh_guidance.is_unpublished_candidate(staging))
        fresh_runtime = importlib.import_module('runtime_lock')
        self.assertIs(fresh_runtime, runtime)
        self.assertIs(fresh_runtime.RuntimeLockError, old_runtime_exception)
        self.assertIs(fresh_runtime._PROCESS_RECORD_HOLDS, old_holds)
        self.assertIs(fresh_runtime.process_hold_guard(), old_guard)
        self.assertEqual(fresh_runtime.process_hold(hold_path), {'owner': 'reload-control'})
        self.assertIsNot(fresh_tee.clean_output, stale_clean)
        self.assertIsNot(fresh_guidance.resume_guidance, stale_resume)


class PhaseChildTests(unittest.TestCase):
    def setUp(self):
        global migration
        migration = importlib.import_module('sqlite_storage_migration')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.scripts = self.root / 'scripts'
        self.scripts.mkdir()
        for name in ('setup_index.py', 'sqlite_storage_migration.py', 'docs_gardener.py', 'docs_lint.py', 'render_platform_surfaces.py', 'prune_framework.py'):
            (self.scripts / name).write_text("import sys;print('stdout failure reason');print('stderr failure reason',file=sys.stderr);sys.exit(1)\n")

    def test_docs_gate_tails_before_exit_with_target_env_and_cwd(self):
        upgrade._open_log(self.root)
        try:
            with patch.object(upgrade, 'SCRIPTS_DIR', self.scripts), patch.object(upgrade, '_preferred_python', return_value=sys.executable), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit):
                    upgrade.phase_docs_gate(self.root)
            self.assertIn('stdout failure reason', err.getvalue())
            self.assertIn('stderr failure reason', err.getvalue())
            self.assertIn('stderr failure reason', (self.root / '.wavefoundry/logs/upgrade.log').read_text())
            self.assertTrue(list((self.root / '.wavefoundry/logs').glob('upgrade-child-*.log')))
        finally:
            upgrade._close_log()

    def test_split_publisher_token_is_absent_from_all_upgrade_destinations(self):
        token = '0123456789abcdef' * 4
        source = "import os,time,sys; t=os.environ['WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN']; os.write(1,b'x'*4090+t[:31].encode()+b'\\x1b['); time.sleep(.03); os.write(1,b'31m'+t[31:].encode()+b'\\r\\x00\\n'); print('ERROR: '+t[:31]+'\\x00'+t[31:],file=sys.stderr); print('ERROR: '+t[:31]+'\\x85'+t[31:],file=sys.stderr); os.write(2,('ERROR: '+t[:31]+'\\x1b]0;').encode()); time.sleep(.03); os.write(2,('title\\x1b\\\\'+t[31:]+'\\n').encode()); sys.exit(1)"
        (self.scripts / 'docs_gardener.py').write_text(source)
        with patch.object(upgrade, 'SCRIPTS_DIR', self.scripts), patch.object(upgrade, '_preferred_python', return_value=sys.executable), patch.dict(os.environ, {'WAVEFOUNDRY_UPGRADE_PUBLISHER_TOKEN': token}), contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            upgrade._open_log(self.root)
            with self.assertRaises(SystemExit):
                upgrade.phase_docs_gate(self.root)
            upgrade._close_log()
            full = out.getvalue() + err.getvalue()
            server = load_server()
            with patch.object(server, '_mcp_subprocess_run', return_value=subprocess.CompletedProcess([], 1, full, '')) as spawn:
                response = server.wf_upgrade_response(self.root)
            spawn.assert_called_once()
        destinations = [out.getvalue(), err.getvalue(), response['data']['output'], response['data']['error_tail'], (self.root / '.wavefoundry/logs/upgrade.log').read_text()]
        destinations += [path.read_text() for path in (self.root / '.wavefoundry/logs').glob('upgrade-child-*.log')]
        for value in destinations:
            self.assertNotIn(token, value)
            self.assertNotIn(token[:8], value)
            for control in ('\x1b', '\r', '\x00', '\x85', '[31m', 'title'):
                self.assertNotIn(control, value)
        self.assertIn('[REDACTED]', response['data']['error_tail'])

    def test_real_index_update_rebuild_and_graph_children_surface_both_streams(self):
        for function in (upgrade.phase_index_update, upgrade.phase_index_rebuild):
            with self.subTest(function=function.__name__), contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(upgrade, 'SCRIPTS_DIR', self.scripts))
                stack.enter_context(patch.object(upgrade, '_preferred_python', return_value=sys.executable))
                guard = stack.enter_context(patch.object(upgrade, '_enforce_index_guard_before_children'))
                dependencies = stack.enter_context(patch.object(upgrade, '_provision_upgrade_dependencies', return_value=True))
                grant = stack.enter_context(patch.object(upgrade, '_index_child_publisher_grant', return_value='fixture-secret'))
                receipt = stack.enter_context(patch.object(migration, 'read_receipt', return_value=None))
                detected = stack.enter_context(patch.object(migration, 'detect', return_value={'migration_required': False}))
                publication = stack.enter_context(patch.object(migration, 'begin_upgrade_publication'))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                err = stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                upgrade._open_log(self.root)
                self.assertFalse(function(self.root))
                upgrade._close_log()
                self.assertIn('stdout failure reason', err.getvalue())
                self.assertIn('stderr failure reason', err.getvalue())
                content = (self.root / '.wavefoundry/logs/upgrade.log').read_text()
                self.assertIn('Graph index', content)
                self.assertIn('continuing', content)
                self.assertIn('[stderr] stderr failure reason', content)
                dependencies.assert_called_once_with(self.root)
                grant.assert_called_once_with(self.root)
                self.assertEqual(guard.call_count, 3)
                if function is upgrade.phase_index_update:
                    self.assertEqual(receipt.call_args_list, [unittest.mock.call(self.root / '.wavefoundry/index')] * 2)
                    detected.assert_called_once_with(self.root / '.wavefoundry/index')
                    publication.assert_called_once_with(self.root)
                else:
                    # Rebuild owns no storage-migration detect/publication path.
                    receipt.assert_not_called(); detected.assert_not_called(); publication.assert_not_called()

    def test_real_prewarm_and_verify_fail_before_migration_or_cleanup(self):
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(upgrade, 'SCRIPTS_DIR', self.scripts))
            stack.enter_context(patch.object(upgrade, '_preferred_python', return_value=sys.executable))
            guard = stack.enter_context(patch.object(upgrade, '_enforce_index_guard_before_children'))
            dependencies = stack.enter_context(patch.object(upgrade, '_provision_upgrade_dependencies', return_value=True))
            install = stack.enter_context(patch.object(upgrade, '_run_dependency_install', return_value=True))
            receipt = stack.enter_context(patch.object(migration, 'read_receipt', return_value={'state': 'quiesced', 'strategy': 'rebuild'}))
            detected = stack.enter_context(patch.object(migration, 'detect', return_value={'migration_required': True, 'legacy': []}))
            conversion = stack.enter_context(patch.object(migration, 'migrate_legacy'))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            with self.assertRaises(migration.MigrationRequired) as failed:
                upgrade.phase_index_update(self.root)
            self.assertIn('stdout failure reason', str(failed.exception))
            self.assertIn('stderr failure reason', str(failed.exception))
            conversion.assert_not_called()  # Prewarm refusal precedes live conversion.
            guard.assert_called_once_with(self.root)
            dependencies.assert_called_once_with(self.root)
            install.assert_called_once()
            detected.assert_called_once_with(self.root / '.wavefoundry/index')
            receipt.assert_called_once_with(self.root / '.wavefoundry/index')
            receipt.return_value = {'state': 'published'}
            with self.assertRaisesRegex(RuntimeError, 'stderr failure reason'):
                upgrade._verify_storage_publication(self.root)
            self.assertEqual(receipt.call_count, 2)
        self.assertTrue(list((self.root / '.wavefoundry/logs').glob('upgrade-child-*-prewarm-*.log')))
        self.assertTrue(list((self.root / '.wavefoundry/logs').glob('upgrade-child-*-storage-verify-*.log')))

    def test_second_docs_gate_child_and_surface_failure_use_real_tee(self):
        (self.scripts / 'docs_gardener.py').write_text("print('gardener success')\n")
        with patch.object(upgrade, 'SCRIPTS_DIR', self.scripts), patch.object(upgrade, '_preferred_python', return_value=sys.executable), contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit):
                upgrade.phase_docs_gate(self.root)
            self.assertIn('docs-lint', err.getvalue())
            self.assertIn('stderr failure reason', err.getvalue())
            with patch.object(upgrade.venv_bootstrap, 'ensure_python_resolves') as resolves:
                with self.assertRaises(SystemExit) as stopped:
                    upgrade.phase_surface_rendering(self.root)
            resolves.assert_called_once_with(strict=False)
            self.assertEqual(stopped.exception.code, 2)
            self.assertIn('stdout failure reason', err.getvalue())
            upgrade._ensure_rendered_permissions_backstop(self.root)
            self.assertIn('Permissions render backstop exited', out.getvalue())
            self.assertIn('[stderr] stderr failure reason', out.getvalue())

    def test_real_pruning_failure_preserves_snapshot_and_stderr(self):
        framework = self.root / '.wavefoundry/framework'
        framework.mkdir(parents=True)
        (framework / 'MANIFEST').write_text('seeds/kept.md\n')
        upgrade._save_old_manifest_snapshot(self.root, 'fixture-version')
        with patch.object(upgrade, 'SCRIPTS_DIR', self.scripts), patch.object(upgrade, '_preferred_python', return_value=sys.executable), contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            self.assertIsNone(upgrade.phase_pruning(self.root))
        self.assertIn('[stderr] stderr failure reason', out.getvalue())
        self.assertIn('non-fatal', out.getvalue())
        self.assertIsNotNone(upgrade._read_old_manifest_snapshot(self.root))

    def test_phase_callsite_census_uses_tee_and_metadata_stays_excluded(self):
        tree = ast.parse((SCRIPTS / 'upgrade_wavefoundry.py').read_text())
        expected = {'phase_docs_gate': 1, '_verify_storage_publication': 1, 'phase_index_update': 3,
                    'phase_index_rebuild': 2, 'phase_surface_rendering': 1, '_ensure_rendered_permissions_backstop': 1, 'phase_pruning': 1}
        for function in tree.body:
            if isinstance(function, ast.FunctionDef) and function.name in expected:
                calls = [n for n in ast.walk(function) if isinstance(n, ast.Call)]
                self.assertEqual(sum(ast.unparse(n.func) == '_run_upgrade_child' for n in calls), expected[function.name])
                self.assertFalse(any(ast.unparse(n.func) == 'subprocess_util.isolated_run' for n in calls))

    def test_lazy_module_and_pack_inventory(self):
        import builtins
        actual = builtins.__import__
        def absent(name, *args, **kwargs):
            if name == 'child_tee':
                raise ImportError('partially extracted fixture')
            return actual(name, *args, **kwargs)
        namespace = {'__file__': str(SCRIPTS / 'upgrade_wavefoundry.py'), '__name__': 'lazy_upgrade_fixture'}
        with patch('builtins.__import__', side_effect=absent):
            exec(compile((SCRIPTS / 'upgrade_wavefoundry.py').read_text(), namespace['__file__'], 'exec'), namespace)
        self.assertTrue(callable(namespace['phase_index_update']))
        import mcp_tool_extensions, build_pack, setup_readiness
        self.assertIn('child_tee', mcp_tool_extensions.FRAMEWORK_SCRIPT_MODULE_NAMES)
        self.assertNotIn('child_tee.py', setup_readiness.SOURCE_FILES)
        self.assertFalse(build_pack.should_exclude('scripts/child_tee.py', 'child_tee.py'))
        entries = build_pack.collect_files(SCRIPTS.parent)
        self.assertTrue(any(path == SCRIPTS / 'child_tee.py' and arc.endswith('/scripts/child_tee.py') for path, arc in entries))
        with tempfile.TemporaryDirectory() as temporary:
            manifest = build_pack.write_manifest(Path(temporary), entries)
            self.assertIn('scripts/child_tee.py', manifest.read_text().splitlines())


if __name__ == '__main__':
    unittest.main()

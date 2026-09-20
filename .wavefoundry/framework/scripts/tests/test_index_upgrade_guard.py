"""First protected-release upgrade handoff through real hooks and phase entries."""
from __future__ import annotations

import contextlib
import copy
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
import sys
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import upgrade_extensions as hooks
import upgrade_lib
import upgrade_wavefoundry as runner
import sqlite_storage_migration as migration


def _legacy_wrapper_fixture():
    """The ppjy exit-3 branch, isolated from subprocesses and host shutdown.

    Keep its storage-only labeling and final bounder lookup: either correcting
    this fixture or calling the new wrapper would erase the reported defect.
    """
    bounded_inputs = []

    def bounded(response):
        bounded_inputs.append(copy.deepcopy(response))
        return response

    namespace = {'migration': migration, '_bounded_upgrade_response_envelope': bounded}
    exec(compile('''
def wf_upgrade_response(root, invocation, mode="apply", exit_code=3, after_read=None):
    if exit_code == 3 and mode == "apply":
        storage_action = migration.read_restart_action(root, 3, invocation)
        if isinstance(storage_action, dict):
            storage_action = dict(storage_action)
            hosts = storage_action.get("old_hosts", [])
            storage_action["old_hosts"] = hosts[:50]
            storage_action["old_hosts_total"] = len(hosts)
            storage_action["old_hosts_omitted"] = max(0, len(hosts) - 50)
            storage_action["receipt_path"] = str(root / ".wavefoundry/index/sqlite-migration.json")
            response = {"status": "ok", "data": {
                "exit_code": 3, "state": "restart_required", "restart_required": True,
                "code": "storage_restart_required", "action_required": storage_action,
                "failed_phase": None}, "diagnostics": [], "next_tools": ["wf_upgrade_status"]}
            response["next_step"] = "Preserve the migration receipt and selected package."
            if after_read:
                after_read(response)
            return _bounded_upgrade_response_envelope(response)
    return _bounded_upgrade_response_envelope({"status": "error", "isError": True,
        "data": {"exit_code": exit_code}, "diagnostics": [{"message": "pre-flight check failed"}]})
''', '<ppjy-upgrade-exit-3-fixture>', 'exec'), namespace)
    return namespace, bounded_inputs


class IndexUpgradeGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.scripts = self.root / '.wavefoundry/framework/scripts'
        self.scripts.mkdir(parents=True)
        self.package = self.root / 'release.zip'
        self.package.write_bytes(b'original-package-bytes')
        self.ctx = runner.UpgradeContext(self.root, '1.24.0+old', '1.24.0+new', self.package, True)
        upgrade_lib.write_upgrade_lock(self.root, self.ctx.from_version, self.ctx.to_version, self.package)
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.pop(migration.CONFIRM_ENV, None)
        self.hosts = patch.object(migration, 'discover_hosts', return_value=([], ['discovery is best effort']))
        self.hosts.start()
        self.addCleanup(self.hosts.stop)

    def capture(self, ctx=None):
        with patch.object(hooks, '_protect_existing_root_bootstrap'), patch.object(hooks, '_preserve_original_manifest'), patch.object(hooks, '_snapshot_graph_builder_doc_claim'), patch.object(hooks, '_cut_over_runtime_locks'):
            hooks.pre_extract(ctx or self.ctx)

    def record(self):
        return upgrade_lib.read_upgrade_lock(self.root)['index_guard_handoff']

    def refuse(self, callback):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as caught:
                callback()
        self.assertEqual(caught.exception.code, 3)
        return json.loads(output.getvalue().splitlines()[-1])

    def confirm(self):
        os.environ[migration.CONFIRM_ENV] = '1'

    def test_incoming_identity_helper_before_extraction_preserves_drifted_handoff(self):
        import zipfile
        source = Path(hooks.__file__).parent
        with zipfile.ZipFile(self.package, 'w') as archive:
            for name in ('upgrade_extensions.py', 'storage_identity.py'):
                archive.write(source / name, '.wavefoundry/framework/scripts/' + name)
        self.capture()
        record = self.record()
        record['root_identity']['device'] += 17
        upgrade_lib.update_upgrade_lock(self.root, index_guard_handoff=record)
        before = upgrade_lib.upgrade_lock_path(self.root).read_bytes()
        incoming = runner._load_extension_module(self.package)
        self.assertIsNotNone(incoming)
        self.assertFalse((self.scripts / 'storage_identity.py').exists())
        def dispatch():
            with contextlib.ExitStack() as stack:
                for name in ('_protect_existing_root_bootstrap', '_preserve_original_manifest',
                             '_snapshot_graph_builder_doc_claim', '_cut_over_runtime_locks'):
                    stack.enter_context(patch.object(incoming, name))
                runner._run_hook('pre_extract', self.ctx, incoming)
        # An unavailable installed helper must not disable the incoming hook.
        with patch.dict(sys.modules, {'storage_identity': None}):
            dispatch()
        self.assertEqual(upgrade_lib.upgrade_lock_path(self.root).read_bytes(), before)
        bad = copy.deepcopy(record)
        bad['root_identity']['inode'] += 1
        upgrade_lib.update_upgrade_lock(self.root, index_guard_handoff=bad)
        rejected = upgrade_lib.upgrade_lock_path(self.root).read_bytes()
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as refused:
            dispatch()
        self.assertEqual(refused.exception.code, 3)
        self.assertEqual(upgrade_lib.upgrade_lock_path(self.root).read_bytes(), rejected)

    def test_changed_archive_never_executes_incoming_identity_helper(self):
        import zipfile
        source = Path(hooks.__file__).parent
        marker = self.root / 'unvalidated-helper-executed'
        def package(changed=False):
            with zipfile.ZipFile(self.package, 'w') as archive:
                archive.write(source / 'upgrade_extensions.py', '.wavefoundry/framework/scripts/upgrade_extensions.py')
                helper = (source / 'storage_identity.py').read_text()
                if changed:
                    helper += f'\nPath({str(marker)!r}).write_text("executed")\n'
                archive.writestr('.wavefoundry/framework/scripts/storage_identity.py', helper)
        for after_outer_hash in (False, True):
            with self.subTest(after_outer_hash=after_outer_hash):
                package()
                upgrade_lib.upgrade_lock_path(self.root).unlink(missing_ok=True)
                upgrade_lib.write_upgrade_lock(self.root, self.ctx.from_version, self.ctx.to_version, self.package)
                self.capture()
                before = upgrade_lib.upgrade_lock_path(self.root).read_bytes()
                incoming = runner._load_extension_module(self.package)
                self.assertIsNotNone(incoming)
                digest = incoming._pack_sha256
                def hash_then_replace(path):
                    result = digest(path)
                    package(changed=True)
                    return result
                if not after_outer_hash:
                    package(changed=True)
                with contextlib.ExitStack() as stack:
                    for name in ('_protect_existing_root_bootstrap', '_preserve_original_manifest',
                                 '_snapshot_graph_builder_doc_claim', '_cut_over_runtime_locks'):
                        stack.enter_context(patch.object(incoming, name))
                    if after_outer_hash:
                        stack.enter_context(patch.object(incoming, '_pack_sha256', side_effect=hash_then_replace))
                    with contextlib.redirect_stderr(io.StringIO()) as output, self.assertRaises(SystemExit) as refused:
                        runner._run_hook('pre_extract', self.ctx, incoming)
                self.assertEqual(refused.exception.code, 3)
                self.assertIn('index_guard_package_changed', output.getvalue())
                self.assertFalse(marker.exists(), 'unvalidated helper executed before refusal')
                self.assertEqual(before, upgrade_lib.upgrade_lock_path(self.root).read_bytes())

    def test_same_schema_old_host_requires_new_coordinator_and_confirmation(self):
        old = SimpleNamespace(root=self.root, from_version=self.ctx.from_version, to_version=self.ctx.to_version, zip_path=self.package)
        self.capture(old)
        self.scripts.joinpath('index_compatibility.py').write_text('INDEX_GUARD_CAPABILITY = 1\n')
        self.confirm()
        result = self.refuse(lambda: hooks.pre_index_update(old))
        self.assertEqual(result['reason'], 'index_guard_fresh_coordinator_required')
        self.assertIn('--confirm-hosts-stopped', result['command_argv'])
        self.assertIn(str(self.package), result['command_argv'])
        os.environ.pop(migration.CONFIRM_ENV)
        self.assertEqual(self.refuse(lambda: hooks.pre_index_update(self.ctx))['reason'], 'index_guard_hosts_confirmation_required')
        self.confirm()
        hooks.pre_index_update(self.ctx)
        self.assertTrue(self.record()['hosts_stopped_confirmed'])
        self.assertFalse((self.root / '.wavefoundry/index/sqlite-migration.json').exists())

    def test_known_live_host_refuses_even_with_confirmation(self):
        self.capture()
        self.confirm()
        host = {'pid': os.getpid(), 'kind': 'mcp', 'association': 'fixture positively associated host'}
        with patch.object(migration, 'discover_hosts', return_value=([host], [])):
            result = self.refuse(lambda: hooks.pre_index_rebuild(self.ctx))
        self.assertIn('storage_old_host_alive', result['reason'])
        # Retained old host stays a blocker even if later discovery misses it.
        self.assertIn('storage_old_host_alive', self.refuse(lambda: hooks.pre_index_update(self.ctx))['reason'])

    def test_retry_before_and_after_extraction_preserves_original_decision(self):
        self.capture()
        original = self.record()
        self.capture()
        self.assertEqual(self.record(), original)
        self.scripts.joinpath('index_compatibility.py').write_text('INDEX_GUARD_CAPABILITY = 1\n')
        # The full retry sees installed target version, but retains old obligation.
        upgrade_lib.write_upgrade_lock(self.root, self.ctx.to_version, self.ctx.to_version, self.package)
        self.capture()
        self.assertEqual(self.record(), original)
        with patch.object(upgrade_lib, 'is_lock_stale', return_value=True), patch.object(migration, 'restore_checkpoint', return_value=None):
            runner._clear_stale_upgrade_lock_for_preflight(self.root, upgrade_lib)
        self.assertEqual(self.record(), original)
        with contextlib.redirect_stderr(io.StringIO()):
            runner._finalize_failed_upgrade(self.root, False, 'extract')
        self.assertEqual(self.record(), original)

    def test_altered_checkpoint_or_package_refuses_without_replacing_authority(self):
        self.capture()
        original = self.record()
        for field, bad in [('root', str(self.root.parent)), ('target_version', 'wrong'), ('required', 'false'), ('required', False), ('root_identity', {})]:
            with self.subTest(field=field):
                changed = dict(original, **{field: bad})
                upgrade_lib.update_upgrade_lock(self.root, index_guard_handoff=changed)
                with self.assertRaisesRegex(ValueError, 'index_guard_checkpoint_invalid'):
                    hooks.pre_index_update(self.ctx)
        upgrade_lib.update_upgrade_lock(self.root, index_guard_handoff=original)
        self.package.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'index_guard_package_changed'):
            upgrade_lib.write_upgrade_lock(self.root, self.ctx.from_version, self.ctx.to_version, self.package)
        self.assertEqual(self.record(), original)
        with self.assertRaisesRegex(ValueError, 'index_guard_package_changed'):
            hooks.pre_index_update(self.ctx)

    def test_byte_identical_relocated_package_is_accepted(self):
        self.capture()
        moved = self.root / 'relocated.zip'
        self.package.rename(moved)
        upgrade_lib.write_upgrade_lock(self.root, self.ctx.from_version, self.ctx.to_version, moved)
        self.ctx.zip_path = moved
        self.capture()
        self.confirm()
        hooks.pre_index_update(self.ctx)

    def test_old_runner_retains_verified_original_archive_locator(self):
        private_copy = self.root / 'private-copy.zip'
        private_copy.write_bytes(self.package.read_bytes())
        upgrade_lib.write_upgrade_lock(self.root, self.ctx.from_version, self.ctx.to_version, private_copy)
        old_type = type('OldContext', (), {'__module__': '_fixture_old_upgrade'})
        old = old_type()
        old.root, old.from_version, old.to_version, old.zip_path = self.root, self.ctx.from_version, self.ctx.to_version, private_copy
        with patch.dict(sys.modules, {'_fixture_old_upgrade': SimpleNamespace(_find_zip=lambda root: self.package)}):
            self.capture(old)
            action = self.refuse(lambda: hooks.pre_index_update(old))
        self.assertEqual(self.record()['pack_path'], str(self.package))
        self.assertIn(str(self.package), action['command_argv'])
        self.assertNotIn(str(private_copy), action['command_argv'])

    def test_fresh_install_and_previously_protected_controls(self):
        for fresh in (True, False):
            with self.subTest(fresh=fresh):
                upgrade_lib.remove_upgrade_lock(self.root)
                self.ctx.from_version = None if fresh else '1.24.0+protected'
                self.scripts.joinpath('index_compatibility.py').write_text('INDEX_GUARD_CAPABILITY = 1\n')
                upgrade_lib.write_upgrade_lock(self.root, self.ctx.from_version, self.ctx.to_version, self.package)
                self.capture()
                self.assertFalse(self.record()['required'])
                hooks.pre_index_update(self.ctx)

    def test_installed_marker_does_not_bless_already_loaded_old_context(self):
        self.scripts.joinpath('index_compatibility.py').write_text('INDEX_GUARD_CAPABILITY = 1\n')
        old = SimpleNamespace(root=self.root, from_version=self.ctx.from_version, to_version=self.ctx.to_version, zip_path=self.package)
        self.capture(old)
        self.assertTrue(self.record()['required'])
        self.refuse(lambda: hooks.pre_index_update(old))

    def test_each_actual_phase_refuses_before_child_or_store_access(self):
        self.capture()
        for phase in (lambda: runner.phase_index_update(self.root), lambda: runner.phase_index_rebuild(self.root), lambda: runner.phase_index_update_parent_owned(self.root, 'memory-fixture')):
            with self.subTest(phase=phase):
                with patch.object(migration, 'detect', side_effect=AssertionError('storage reached before guard')), patch.object(runner.subprocess_util, 'isolated_run', side_effect=AssertionError('child reached before guard')):
                    self.refuse(phase)

    def test_post_extract_preserves_storage_action_and_dispatch_order(self):
        self.capture()
        self.scripts.joinpath('sqlite_storage_migration.py').write_text('from sqlite_storage_migration import *\nfrom sqlite_storage_migration import _hosts_gone\ndef prepare_upgrade(ctx):\n    ctx.storage_visited = True\n')
        storage_action = {'kind': 'storage_migration', 'state': 'restart_required'}
        upgrade_lib.update_upgrade_lock(self.root, action_required=storage_action)
        self.refuse(lambda: hooks.post_extract(self.ctx))
        self.assertTrue(self.ctx.storage_visited)
        self.assertEqual(upgrade_lib.read_upgrade_lock(self.root)['action_required'], storage_action)
        self.confirm()
        with patch.object(hooks, '_run_convergence_migration'):
            hooks.post_extract(self.ctx)
        self.assertTrue(self.record()['hosts_stopped_confirmed'])

    def test_storage_pause_precedes_independent_guard_and_retains_capture(self):
        self.capture()
        self.scripts.joinpath('sqlite_storage_migration.py').write_text('def prepare_upgrade(ctx):\n    raise SystemExit(3)\n')
        with self.assertRaises(SystemExit):
            hooks.post_extract(self.ctx)
        self.assertTrue(self.record()['required'])
        self.assertNotIn('action', self.record())

    def test_old_context_uses_installed_migration_helper_not_cached_discovery(self):
        old = SimpleNamespace(root=self.root, from_version=self.ctx.from_version, to_version=self.ctx.to_version, zip_path=self.package)
        self.capture(old)
        self.scripts.joinpath('sqlite_storage_migration.py').write_text(
            'from sqlite_storage_migration import *\n'
            'from sqlite_storage_migration import _hosts_gone\n'
            'def discover_hosts(root):\n    return [], ["fresh installed discovery"]\n')
        with patch.object(migration, 'discover_hosts', side_effect=AssertionError('cached discovery used')):
            action = self.refuse(lambda: hooks.pre_index_update(old))
        self.assertEqual(action['discovery_limits'], ['fresh installed discovery'])

    def test_structured_action_reader_binds_invocation_and_checkpoint(self):
        self.capture()
        with patch.dict(os.environ, {migration.INVOCATION_ENV: 'this-invocation'}):
            self.refuse(lambda: hooks.pre_index_update(self.ctx))
        action = hooks.read_index_guard_action(self.root, 3, 'this-invocation')
        self.assertEqual(action['code'], 'index_guard_restart_required')
        self.assertIsNone(hooks.read_index_guard_action(self.root, 3, 'other-invocation'))
        self.assertIsNone(hooks.read_index_guard_action(self.root, 1, 'this-invocation'))
        record = self.record()
        record['action']['token'] = 'unrelated-pause'
        upgrade_lib.update_upgrade_lock(self.root, index_guard_handoff=record)
        self.assertIsNone(hooks.read_index_guard_action(self.root, 3, 'this-invocation'))

    def test_linked_source_refused_before_read(self):
        external = self.root / 'outside.py'
        external.write_text('INDEX_GUARD_CAPABILITY = 1\n')
        self.scripts.joinpath('index_compatibility.py').symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'linked recovery/source path'):
            self.capture()

    def test_missing_snapshot_legacy_checkpoint_is_conservatively_fenced(self):
        self.scripts.joinpath('index_compatibility.py').write_text('INDEX_GUARD_CAPABILITY = 1\n')
        self.refuse(lambda: hooks.pre_index_update(self.ctx))
        self.assertTrue(self.record()['required'])

    def guard_pause(self, invocation='invocation-one', root=None):
        root = root or self.root
        ctx = self.ctx
        if root != self.root:
            (root / '.wavefoundry/framework/scripts').mkdir(parents=True)
            package = root / 'release.zip'
            package.write_bytes(b'second-package')
            ctx = runner.UpgradeContext(root, '1.24.0+old', '1.24.0+new', package, True)
            upgrade_lib.write_upgrade_lock(root, ctx.from_version, ctx.to_version, package)
        self.capture(ctx)
        with patch.dict(os.environ, {migration.INVOCATION_ENV: invocation}):
            return self.refuse(lambda: hooks.pre_index_update(ctx))

    def test_legacy_wrapper_corrects_outer_status_and_retains_exact_continuation(self):
        action = self.guard_pause()
        namespace, bounded_inputs = _legacy_wrapper_fixture()
        result = namespace['wf_upgrade_response'](self.root, 'invocation-one')
        self.assertEqual(result['status'], 'action_required')
        self.assertFalse(result.get('isError'))
        self.assertEqual(result['data']['code'], 'index_guard_restart_required')
        self.assertIsNone(result['data']['failed_phase'])
        returned = result['data']['action_required']
        self.assertEqual(returned['command_argv'], action['command_argv'])
        self.assertEqual(returned['invocation_token'], 'invocation-one')
        self.assertNotIn('receipt_path', returned)
        self.assertNotIn('_index_guard_envelope_proof', json.dumps(result))
        self.assertIn('upgrade checkpoint', result['next_step'])
        self.assertIn('non-MCP shell', result['next_step'])
        self.assertNotIn('migration receipt', result['next_step'])
        self.assertEqual(bounded_inputs, [result], 'normalization must precede the original bounder')
        self.assertFalse((self.root / '.wavefoundry/index/sqlite-migration.json').exists())

    def test_legacy_wrapper_preserves_host_inventory_cap_and_root_locator_spelling(self):
        # Confirmation is absent, so production never probes these fixture PIDs.
        hosts = [{'pid': 10000 + i, 'kind': 'mcp', 'association': f'fixture-{i}'} for i in range(60)]
        with patch.object(migration, 'discover_hosts', return_value=(hosts, ['best effort'])):
            action = self.guard_pause()
        # Exercise an alias portably without requiring Windows symlink rights.
        alias_child = self.root / 'alias-child'
        alias_child.mkdir()
        alias = alias_child / '..'
        namespace, _ = _legacy_wrapper_fixture()
        result = namespace['wf_upgrade_response'](alias, 'invocation-one')
        self.assertEqual(result['status'], 'action_required')
        returned = result['data']['action_required']
        self.assertEqual(returned['old_hosts'], action['old_hosts'][:50])
        self.assertEqual(returned['old_hosts_total'], 60)
        self.assertEqual(returned['old_hosts_omitted'], 10)
        self.assertEqual(returned['command_argv'], action['command_argv'])
        self.assertNotIn('receipt_path', returned)

    def test_legacy_wrapper_control_detects_missing_reader_or_final_normalization(self):
        self.guard_pause()
        namespace, _ = _legacy_wrapper_fixture()
        # The original consumer report is the independent reference: an old
        # wrapper with no incoming reader adaptation produces the outer error.
        with patch.object(hooks, 'legacy_index_guard_restart_action', return_value=None):
            missing_reader = namespace['wf_upgrade_response'](self.root, 'invocation-one')
        self.assertEqual(missing_reader['status'], 'error')
        self.assertTrue(missing_reader['isError'])
        # Reader-only repair avoids the error but still gives false storage
        # guidance. This focused mutation guards the second required seam.
        with patch.object(hooks, '_normalize_legacy_index_guard_envelope', lambda response: response):
            reader_only = namespace['wf_upgrade_response'](self.root, 'invocation-one')
        self.assertEqual(reader_only['status'], 'ok')
        self.assertEqual(reader_only['data']['code'], 'storage_restart_required')
        self.assertIn('receipt_path', reader_only['data']['action_required'])
        repaired = namespace['wf_upgrade_response'](self.root, 'invocation-one')
        self.assertEqual(repaired['status'], 'action_required')
        self.assertEqual(repaired['data']['code'], 'index_guard_restart_required')
        self.assertNotIn('receipt_path', repaired['data']['action_required'])

    def test_legacy_wrapper_does_not_bless_unbound_exit_or_dry_run(self):
        self.guard_pause()
        namespace, _ = _legacy_wrapper_fixture()
        for invocation, mode, exit_code in [('stale', 'apply', 3), ('', 'apply', 3),
                                             (None, 'apply', 3), ('invocation-one', 'dry_run', 3),
                                             ('invocation-one', 'apply', 1)]:
            with self.subTest(invocation=invocation, mode=mode, exit_code=exit_code):
                result = namespace['wf_upgrade_response'](self.root, invocation, mode, exit_code)
                self.assertEqual(result['status'], 'error')
                self.assertTrue(result['isError'])
                self.assertNotIn('action_required', result['data'])
        upgrade_lib.remove_upgrade_lock(self.root)
        result = namespace['wf_upgrade_response'](self.root, 'invocation-one')
        self.assertEqual(result['status'], 'error')

    def test_legacy_wrapper_refuses_foreign_or_malformed_checkpoint(self):
        self.guard_pause()
        original = self.record()
        namespace, _ = _legacy_wrapper_fixture()
        for field, value in [('root', str(self.root.parent)), ('root_identity', {}),
                             ('target_version', 'foreign'), ('action', 'malformed')]:
            with self.subTest(field=field):
                upgrade_lib.update_upgrade_lock(self.root, index_guard_handoff={**original, field: value})
                result = namespace['wf_upgrade_response'](self.root, 'invocation-one')
                self.assertEqual(result['status'], 'error')
                self.assertNotIn('action_required', result['data'])

    def test_legacy_adapter_interleaves_roots_without_pending_response_state(self):
        first = self.guard_pause('first')
        second_root = self.root / 'second-project'
        second = self.guard_pause('second', second_root)
        namespace, bounded_inputs = _legacy_wrapper_fixture()
        barrier = threading.Barrier(2)

        def call(root, invocation):
            return namespace['wf_upgrade_response'](
                root, invocation, after_read=lambda response: barrier.wait(timeout=10))

        with ThreadPoolExecutor(max_workers=2) as executor:
            one = executor.submit(call, self.root, 'first')
            two = executor.submit(call, second_root, 'second')
            results = [one.result(timeout=15), two.result(timeout=15)]
        for result, action in zip(results, (first, second)):
            self.assertEqual(result['status'], 'action_required')
            self.assertEqual(result['data']['action_required']['command_argv'], action['command_argv'])
            self.assertEqual(result['data']['action_required']['invocation_token'], action['invocation_token'])
        adapter = namespace['_bounded_upgrade_response_envelope']
        namespace['wf_upgrade_response'](self.root, 'first')
        self.assertIs(namespace['_bounded_upgrade_response_envelope'], adapter)
        # An ordinary storage action has no capability and is not relabeled.
        storage = {'status': 'ok', 'data': {'code': 'storage_restart_required',
                   'action_required': {'kind': 'storage_migration', 'receipt_path': 'real-receipt'}}}
        unrelated_error = {'status': 'error', 'isError': True, 'data': {'exit_code': 3}}
        for response in (storage, unrelated_error):
            original = copy.deepcopy(response)
            self.assertEqual(adapter(response), original)
        self.assertEqual(len(bounded_inputs), 5)

    def test_legacy_adapter_rejects_changed_action_and_strips_internal_proof(self):
        self.guard_pause()
        namespace, bounded_inputs = _legacy_wrapper_fixture()

        def corrupt(response):
            response['data']['action_required']['command_argv'] = ['unsafe', 'replacement']

        result = namespace['wf_upgrade_response'](self.root, 'invocation-one', after_read=corrupt)
        self.assertEqual(result['status'], 'error')
        self.assertTrue(result['isError'])
        self.assertEqual(result['data']['code'], 'index_guard_envelope_unproven')
        self.assertNotIn('_index_guard_envelope_proof', json.dumps(result))
        self.assertEqual(bounded_inputs, [result])

    def test_legacy_adapter_only_installs_at_supported_old_wrapper_seam(self):
        self.guard_pause()
        self.assertIsNone(migration.read_restart_action(self.root, 3, 'invocation-one'))
        for alteration in ('capability', 'missing-bounder', 'foreign-wrapper'):
            with self.subTest(alteration=alteration):
                namespace, _ = _legacy_wrapper_fixture()
                wrapper = namespace['wf_upgrade_response']
                bounder = namespace['_bounded_upgrade_response_envelope']
                if alteration == 'capability':
                    namespace['INDEX_GUARD_RESPONSE_VERSION'] = 1
                elif alteration == 'missing-bounder':
                    namespace['_bounded_upgrade_response_envelope'] = None
                else:
                    namespace['wf_upgrade_response'] = lambda: None
                # Probe the adapter from the fixture's actual caller frame.
                observed = []

                def intercept(root, exit_code, invocation):
                    observed.append(hooks.legacy_index_guard_restart_action(
                        root, exit_code, invocation, sys._getframe(1)))
                    return None

                # A direct function replacement keeps Mock's frame out of the
                # supported-seam check under test.
                with patch.object(migration, 'read_restart_action', intercept):
                    if alteration == 'missing-bounder':
                        with self.assertRaises(TypeError):
                            wrapper(self.root, 'invocation-one')
                    else:
                        self.assertEqual(wrapper(self.root, 'invocation-one')['status'], 'error')
                self.assertEqual(observed, [None])
                if alteration != 'missing-bounder':
                    self.assertIs(namespace['_bounded_upgrade_response_envelope'], bounder)


if __name__ == '__main__':
    unittest.main()

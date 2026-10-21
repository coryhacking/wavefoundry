"""Synthetic capability and cross-run device controls; no native OS qualification."""
import contextlib
import copy
import errno
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import embedded_model_bundle as embedded
import contained_files
import upgrade_extensions as hooks
import upgrade_lib
import upgrade_wavefoundry as runner
import test_index_upgrade_guard as existing
from nt_metadata_support import MISSING_TAG, nt_stat

TAGS = [(0x9000001A, False), (0x80000013, False), (0xA000000C, True),
        (0xA0000003, True), (0x20001234, True), (MISSING_TAG, True),
        (None, True), ('bad', True), (-1, True), (0, True), (True, True),
        (0x100000000, True)]


def tag_at(target, tag):
    actual = Path.lstat
    def lstat(path, *args, **kwargs):
        entry = actual(path, *args, **kwargs)
        return nt_stat(entry, tag) if path == target else entry
    return patch.object(Path, 'lstat', lstat)


class EmbeddedOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        source = self.root / 'source.zip'
        source.write_bytes(b'owned combined archive')
        self.proof = embedded.retain(self.root, source)
        self.path = Path(self.proof['path'])

    def test_source_tags_classify_surrogates_without_refusing_cloud_metadata(self):
        source = self.root / 'source.zip'
        for tag, refused in TAGS:
            with self.subTest(tag=repr(tag)), tag_at(source, tag):
                if refused:
                    with self.assertRaises(OSError):
                        embedded.retain(self.root, source)
                else:
                    proof = embedded.retain(self.root, source)
                    self.assertEqual(embedded.validate_retained(self.root, proof).read_bytes(), source.read_bytes())
                    self.assertTrue(embedded.cleanup(self.root, proof))

    def test_retained_parent_and_final_tags_preserve_resume_and_cleanup_guards(self):
        for index in range(3):
            for tag, refused in TAGS:
                proof = embedded.retain(self.root, self.root / 'source.zip')
                path = Path(proof['path'])
                target = (path.parent.parent, path.parent, path)[index]
                with self.subTest(component=index, tag=repr(tag)), tag_at(target, tag):
                    if refused:
                        with self.assertRaises((OSError, ValueError)):
                            embedded.validate_retained(self.root, proof)
                        self.assertFalse(embedded.cleanup(self.root, proof))
                        self.assertTrue(path.exists())
                    else:
                        self.assertEqual(embedded.validate_retained(self.root, proof), path)
                        self.assertTrue(embedded.cleanup(self.root, proof))
                if path.exists():
                    self.assertTrue(embedded.cleanup(self.root, proof))

    def test_capability_limited_cleanup_succeeds_without_retention(self):
        reasons = []
        real_stat = os.stat
        def no_descriptor_stat(*args, **kwargs):
            if kwargs.get('dir_fd') is not None:
                raise NotImplementedError('descriptor-relative stat unavailable')
            return real_stat(*args, **kwargs)
        with patch.object(contained_files, '_dir_fd_supported', return_value=False), patch.object(os, 'stat', side_effect=no_descriptor_stat):
            self.assertTrue(embedded.cleanup(self.root, self.proof, on_retain=reasons.append))
        self.assertFalse(self.path.exists())
        self.assertEqual(reasons, [])

    def test_legacy_device_drift_validates_and_cleans_using_fresh_device(self):
        self.proof['identity'][0] += 999
        self.assertEqual(embedded.validate_retained(self.root, self.proof), self.path)
        with patch.object(contained_files, 'unlink_contained', wraps=contained_files.unlink_contained) as unlink:
            self.assertTrue(embedded.cleanup(self.root, self.proof))
        self.assertEqual(unlink.call_args.kwargs['expected_identity'][0], self.root.stat().st_dev)

    def test_bad_proof_fields_and_io_errors_retain_with_reason(self):
        for field in ('inode', 'size', 'mtime', 'unknown', 'hash'):
            proof = copy.deepcopy(self.proof)
            if field == 'hash': proof['sha256'] = '0' * 64
            elif field == 'unknown': proof['identity'][1] = 0
            else: proof['identity'][{'inode': 1, 'size': 2, 'mtime': 3}[field]] += 1
            reasons = []
            with self.subTest(field=field):
                self.assertFalse(embedded.cleanup(self.root, proof, on_retain=reasons.append))
                self.assertTrue(reasons)
                self.assertTrue(self.path.exists())
        reasons = []
        with patch.object(contained_files, 'unlink_contained', side_effect=PermissionError(errno.EACCES, 'denied')):
            self.assertFalse(embedded.cleanup(self.root, self.proof, on_retain=reasons.append))
        self.assertTrue(reasons)
        self.assertTrue(self.path.exists())

    def test_fallback_unsafe_parent_and_changed_final_entry_are_retained(self):
        real = self.path.parent.with_name('retained-directory')
        self.path.parent.rename(real)
        self.path.parent.symlink_to(real, target_is_directory=True)
        reasons = []
        with patch.object(contained_files, '_dir_fd_supported', return_value=False):
            self.assertFalse(embedded.cleanup(self.root, self.proof, on_retain=reasons.append))
        self.assertTrue(reasons)
        self.assertTrue((real / self.path.name).exists())

    def test_same_open_device_change_is_refused(self):
        original = os.fstat
        calls = 0
        def changed(fd):
            nonlocal calls
            entry = original(fd)
            if stat.S_ISREG(entry.st_mode):
                calls += 1
                if calls > 1:
                    values = {name: getattr(entry, name) for name in dir(entry) if name.startswith('st_')}
                    values['st_dev'] += 99
                    return SimpleNamespace(**values)
            return entry
        with patch.object(os, 'fstat', side_effect=changed), self.assertRaises(ValueError):
            embedded.validate_retained(self.root, self.proof)
        self.assertTrue(self.path.exists())

    def test_fallback_final_replacement_preserves_competing_entry(self):
        saved = self.path.with_suffix('.saved')
        def replace_at_unlink(stage):
            if stage == 'unlink':
                self.path.rename(saved)
                self.path.write_bytes(b'competing archive')
        reasons = []
        with patch.object(contained_files, '_dir_fd_supported', return_value=False), patch.object(contained_files, '_checkpoint', side_effect=replace_at_unlink):
            self.assertFalse(embedded.cleanup(self.root, self.proof, on_retain=reasons.append))
        self.assertEqual(self.path.read_bytes(), b'competing archive')
        self.assertTrue(saved.exists())
        self.assertTrue(reasons)

    def test_fallback_reparse_parent_and_final_entry_are_retained(self):
        actual = Path.lstat
        for target in (self.path.parent, self.path):
            def reparse(path, *, target=target):
                entry = actual(path)
                if path == target:
                    values = {name: getattr(entry, name) for name in dir(entry) if name.startswith('st_')}
                    values['st_file_attributes'] = stat.FILE_ATTRIBUTE_REPARSE_POINT
                    return SimpleNamespace(**values)
                return entry
            reasons = []
            with self.subTest(target=target.name), patch.object(contained_files, '_dir_fd_supported', return_value=False), patch.object(Path, 'lstat', reparse):
                self.assertFalse(embedded.cleanup(self.root, self.proof, on_retain=reasons.append))
            self.assertTrue(self.path.exists())
            self.assertTrue(reasons)


class GuardOwnershipTests(unittest.TestCase):
    setUp = existing.IndexUpgradeGuardTests.setUp
    capture = existing.IndexUpgradeGuardTests.capture
    record = existing.IndexUpgradeGuardTests.record
    refuse = existing.IndexUpgradeGuardTests.refuse
    prepare = existing.DurableIndexGuardContinuationTests.prepare
    handoff = existing.DurableIndexGuardContinuationTests.handoff
    terminal = existing.DurableIndexGuardContinuationTests.terminal

    def read_failure(self, target, *, replace=False, corrupt=False):
        original = hooks._read_guard_pack
        def read(root, path, helper):
            if path == target:
                if replace:
                    path.rename(path.with_suffix('.saved'))
                    path.write_bytes(self.package.read_bytes())
                    return original(root, path, helper)
                if corrupt:
                    _, opened, resolved = original(root, path, helper)
                    return b'wrong publication bytes', opened, resolved
                raise PermissionError(errno.EACCES, 'simulated target read-back sharing failure')
            return original(root, path, helper)
        return patch.object(hooks, '_read_guard_pack', side_effect=read)

    def test_legacy_temp_alias_is_removed_by_terminal_cleanup_consumer(self):
        pack_parent = self.enterContext(tempfile.TemporaryDirectory())
        with patch.object(tempfile, 'gettempdir', return_value=pack_parent):
            self.prepare(staged=True)
        staged = Path(upgrade_lib.read_upgrade_lock(self.root)['zip_path'])
        self.addCleanup(staged.unlink, missing_ok=True)
        alias = self.root / 'legacy-temp-alias'
        try:
            alias.symlink_to(staged.parent, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('Directory symlink privileges unavailable; native alias behavior unqualified')
        legacy = alias / staged.name
        proof = {'path': str(legacy), 'identity': runner._pack_entry_identity(staged)}
        self.ctx.zip_path = legacy
        upgrade_lib.update_upgrade_lock(self.root, zip_path=str(legacy), verified_pack_identity=proof)
        self.handoff()
        terminal = self.terminal()
        with patch.object(tempfile, 'gettempdir', return_value=str(staged.parent)):
            hooks.finalize_index_guard_terminal_cleanup(self.root, terminal, runner._cleanup_verified_pack)
        self.assertFalse(staged.exists())
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))
        self.assertTrue(self.package.exists())

    def test_readback_error_rolls_back_then_normal_retry_and_terminal_cleanup_work(self):
        self.prepare()
        target = self.root / hooks._INDEX_GUARD_PACK_REL
        with self.read_failure(target):
            action = self.handoff()
        self.assertEqual(action['reason'], 'index_guard_durable_pack_publication_unavailable')
        self.assertFalse(target.exists())
        self.assertNotIn('durable_pack', self.record())
        self.assertEqual(list(target.parent.iterdir()), [])
        self.handoff()
        self.assertEqual(hooks.validate_index_guard_durable_pack(self.root, upgrade_lib.read_upgrade_lock(self.root)), target)
        hooks.finalize_index_guard_terminal_cleanup(self.root, self.terminal(), lambda *args: None)
        self.assertFalse(target.exists())
        self.assertTrue(self.package.exists())

    def test_rollback_refusal_persists_bound_ownership_for_normal_retry(self):
        self.prepare()
        target = self.root / hooks._INDEX_GUARD_PACK_REL
        with self.read_failure(target), patch.object(contained_files, 'unlink_contained', side_effect=PermissionError('sharing refusal')):
            action = self.handoff()
        self.assertEqual(action['reason'], 'index_guard_durable_pack_retained_validation_unavailable')
        self.assertIn('--update-index', action['command_argv'])
        lock = upgrade_lib.read_upgrade_lock(self.root)
        self.assertEqual(lock['zip_path'], str(target))
        self.assertEqual(lock['index_guard_handoff']['durable_pack']['identity'], hooks._guard_file_identity(target.stat()))
        self.assertEqual(target.stat().st_nlink, 1)
        self.assertEqual(hooks.validate_index_guard_durable_pack(self.root, lock), target)
        self.handoff()
        hooks.finalize_index_guard_terminal_cleanup(self.root, self.terminal(), lambda *args: None)
        self.assertFalse(target.exists())
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))
        self.assertTrue(self.package.exists())

    def test_successful_same_hash_replacement_is_never_adopted_or_removed(self):
        self.prepare()
        target = self.root / hooks._INDEX_GUARD_PACK_REL
        with self.read_failure(target, replace=True), self.assertRaisesRegex(ValueError, 'recovery_required'):
            self.handoff()
        self.assertEqual(target.read_bytes(), self.package.read_bytes())
        self.assertTrue(target.with_suffix('.saved').exists())
        self.assertNotIn('durable_pack', self.record())

    def test_hash_mismatch_is_hard_refusal_and_rolls_back_owned_target(self):
        self.prepare()
        target = self.root / hooks._INDEX_GUARD_PACK_REL
        with self.read_failure(target, corrupt=True), self.assertRaisesRegex(ValueError, 'publication changed'):
            self.handoff()
        self.assertFalse(target.exists())
        self.assertNotIn('durable_pack', self.record())
        self.assertTrue(self.package.exists())

    def test_retention_checkpoint_failure_is_explicit_and_never_adopts_on_retry(self):
        self.prepare()
        target = self.root / hooks._INDEX_GUARD_PACK_REL
        checkpoint = upgrade_lib.upgrade_lock_path(self.root).read_bytes()
        with self.read_failure(target), patch.object(contained_files, 'unlink_contained', side_effect=PermissionError('denied')), \
                patch.object(upgrade_lib, 'update_upgrade_lock', return_value=False), \
                self.assertRaisesRegex(ValueError, 'checkpoint_write_failed'):
            self.handoff()
        self.assertEqual(upgrade_lib.upgrade_lock_path(self.root).read_bytes(), checkpoint)
        self.assertTrue(target.exists())
        self.assertTrue(self.package.exists())
        with self.assertRaisesRegex(ValueError, 'occupied'):
            self.handoff()

    def test_private_unlink_and_rollback_failure_are_explicit_without_false_proof(self):
        self.prepare()
        target = self.root / hooks._INDEX_GUARD_PACK_REL
        unlink = os.unlink
        def deny_private(path, *args, **kwargs):
            if Path(path).name.startswith('.' + target.name):
                raise PermissionError('private name still shared')
            return unlink(path, *args, **kwargs)
        with patch.object(hooks.os, 'unlink', side_effect=deny_private), \
                patch.object(contained_files, 'unlink_contained', side_effect=PermissionError('rollback refused')), \
                self.assertRaisesRegex(ValueError, 'recovery_required'):
            self.handoff()
        self.assertEqual(target.stat().st_nlink, 2)
        self.assertNotIn('durable_pack', self.record())
        self.assertTrue(self.package.exists())

    def test_unavailable_fresh_proof_is_explicit_after_rollback_refusal(self):
        self.prepare()
        target = self.root / hooks._INDEX_GUARD_PACK_REL
        checkpoint = upgrade_lib.upgrade_lock_path(self.root).read_bytes()
        original = Path.lstat
        failed = False
        def fail_read(root, path, helper):
            nonlocal failed
            if path == target:
                failed = True
                raise PermissionError('read-back refused')
            return read(root, path, helper)
        def lstat(path, *args, **kwargs):
            if failed and path == target:
                raise PermissionError('fresh identity unavailable')
            return original(path, *args, **kwargs)
        read = hooks._read_guard_pack
        with patch.object(hooks, '_read_guard_pack', side_effect=fail_read), \
                patch.object(Path, 'lstat', lstat), \
                patch.object(contained_files, 'unlink_contained', side_effect=PermissionError('rollback refused')), \
                self.assertRaisesRegex(ValueError, 'recovery_required'):
            self.handoff()
        self.assertEqual(upgrade_lib.upgrade_lock_path(self.root).read_bytes(), checkpoint)
        self.assertTrue(self.package.exists())
        self.assertNotIn('durable_pack', self.record())

    def test_consumed_source_tags_use_same_name_surrogate_rule(self):
        self.prepare()
        lock = upgrade_lib.read_upgrade_lock(self.root)
        target = self.root / hooks._INDEX_GUARD_PACK_REL
        for tag, refused in TAGS:
            record = copy.deepcopy(lock['index_guard_handoff'])
            with self.subTest(tag=repr(tag)), tag_at(self.package, tag):
                if refused:
                    with self.assertRaises(ValueError):
                        hooks._retain_index_guard_pack(self.ctx, lock, record)
                    self.assertFalse(target.exists())
                else:
                    fields = hooks._retain_index_guard_pack(self.ctx, lock, record)
                    candidate = {**lock, **fields, 'index_guard_handoff': record}
                    self.assertEqual(hooks.validate_index_guard_durable_pack(self.root, candidate), target)
                    contained_files.unlink_contained(self.root, target, expected_identity=(target.stat().st_dev, target.stat().st_ino))

    def test_link_capability_errors_pause_without_clobber_or_temporary_leak(self):
        self.prepare()
        for error in (NotImplementedError('unsupported'), OSError(errno.ENOTSUP, 'unsupported')):
            with self.subTest(error=type(error).__name__), patch.object(hooks.os, 'link', side_effect=error):
                action = self.handoff()
            self.assertIn('publication_unavailable', action['reason'])
            self.assertNotIn('durable_pack', self.record())
            self.assertFalse((self.root / hooks._INDEX_GUARD_PACK_REL).exists())
            self.assertTrue(self.package.exists())
            self.assertEqual(list((self.root / hooks._INDEX_GUARD_PACK_REL).parent.iterdir()), [])

    def test_device_drift_passes_resume_and_terminal_uses_current_identity(self):
        self.prepare()
        self.handoff()
        lock = upgrade_lib.read_upgrade_lock(self.root)
        record = lock['index_guard_handoff']
        record['root_identity']['device'] += 77
        record['durable_pack']['root_identity']['device'] += 77
        record['durable_pack']['identity'][0] += 77
        upgrade_lib.update_upgrade_lock(self.root, index_guard_handoff=record)
        path = hooks.validate_index_guard_durable_pack(self.root, lock)
        hooks._validate_index_guard_handoff(self.root, lock, record)
        current_identity = path.stat().st_dev, path.stat().st_ino
        terminal = self.terminal()
        with patch.object(contained_files, 'unlink_contained', wraps=contained_files.unlink_contained) as unlink:
            hooks.finalize_index_guard_terminal_cleanup(self.root, terminal, lambda *args: None)
        self.assertEqual(unlink.call_args.kwargs['expected_identity'], current_identity)
        self.assertFalse(path.exists())
        self.assertIsNone(upgrade_lib.read_upgrade_lock(self.root))

    def test_unknown_root_inode_and_file_identity_are_never_wildcards(self):
        self.prepare()
        early = upgrade_lib.read_upgrade_lock(self.root)
        early['index_guard_handoff']['root_identity']['inode'] = 0
        with self.assertRaises(ValueError):
            hooks._validate_index_guard_handoff(self.root, early, early['index_guard_handoff'])
        self.handoff()
        original = upgrade_lib.read_upgrade_lock(self.root)
        for fault in ('root', 'file'):
            lock = copy.deepcopy(original)
            if fault == 'root':
                lock['index_guard_handoff']['root_identity']['inode'] = 0
                lock['index_guard_handoff']['durable_pack']['root_identity']['inode'] = 0
            else:
                lock['index_guard_handoff']['durable_pack']['identity'][1] = 0
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                hooks.validate_index_guard_durable_pack(self.root, lock)

    def test_terminal_validator_refuses_changed_inode_size_and_time(self):
        self.prepare()
        self.handoff()
        original = self.terminal()
        for slot in (1, 2, 3, 4):
            lock = copy.deepcopy(original)
            proof = lock['index_guard_handoff']['durable_pack']
            proof['identity'][slot] += 1
            lock['index_guard_handoff']['terminal_cleanup']['proof'] = copy.deepcopy(proof)
            with self.subTest(slot=slot), self.assertRaises(ValueError):
                hooks.validate_index_guard_terminal_cleanup(self.root, lock)

    def test_terminal_binding_rejects_wrong_coordinates_even_after_archive_unlink(self):
        self.prepare()
        self.handoff()
        original = self.terminal()
        path = hooks.validate_index_guard_durable_pack(self.root, original)
        path.unlink()
        for field, value in (('root', '/foreign'), ('token', 'wrong'), ('path', '../wrong'), ('sha256', '0' * 64), ('identity', [0] * 5)):
            lock = copy.deepcopy(original)
            proof = lock['index_guard_handoff']['durable_pack']
            proof[field] = value
            lock['index_guard_handoff']['terminal_cleanup']['proof'] = copy.deepcopy(proof)
            with self.subTest(field=field), self.assertRaises(ValueError):
                hooks.validate_index_guard_terminal_cleanup(self.root, lock)


class IncomingManifestMetadataTests(unittest.TestCase):
    def test_old_runner_pre_extract_uses_local_rule_without_installed_helper(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        framework = root / '.wavefoundry/framework'
        framework.mkdir(parents=True)
        manifest = framework / 'MANIFEST'
        manifest.write_text('seeds/old.prompt.md\n')
        version = framework / 'VERSION'
        version.write_text('1.0.0')
        package = root / 'incoming.zip'
        with zipfile.ZipFile(package, 'w') as archive:
            archive.write(Path(hooks.__file__), '.wavefoundry/framework/scripts/upgrade_extensions.py')
        incoming = runner._load_extension_module(package)
        self.assertIsNotNone(incoming)
        self.assertFalse(Path(incoming.__file__).is_absolute(), 'incoming old-runner path must be exercised')
        ctx = SimpleNamespace(root=root, from_version='1.0.0', to_version='2.0.0',
                              zip_path=package, dry_run=False)
        upgrade_lib.write_upgrade_lock(root, ctx.from_version, ctx.to_version, package)
        with contextlib.ExitStack() as stack:
            for name in ('_preview_council_role_links', '_capture_index_guard_handoff',
                         '_protect_existing_root_bootstrap', '_snapshot_graph_builder_doc_claim', '_cut_over_runtime_locks'):
                stack.enter_context(patch.object(incoming, name))
            stack.enter_context(patch.dict(sys.modules, {'contained_files': None}))
            incoming.pre_extract(ctx)
            snapshot = root / '.wavefoundry/upgrade-manifest-old.json'
            before = snapshot.read_bytes()
            self.assertEqual(json.loads(before)['manifest'], manifest.read_text())
            for target in (framework.parent, framework, manifest, version, snapshot):
                for tag, refused in TAGS:
                    with self.subTest(component=target.name, tag=repr(tag)), tag_at(target, tag):
                        if refused:
                            with self.assertRaisesRegex(ValueError, 'recovery paths'):
                                incoming.pre_extract(ctx)
                        else:
                            incoming.pre_extract(ctx)
                    self.assertEqual(snapshot.read_bytes(), before)


class SharedGuardHandleTests(unittest.TestCase):
    """Windows API/resource simulation; not a native sharing qualification."""

    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.path = self.root / 'owned'
        self.path.write_bytes(b'owned')
        self.fd = os.open(self.path, os.O_WRONLY)
        self.addCleanup(self.close_if_open, self.fd)

    @staticmethod
    def close_if_open(fd):
        try:
            os.close(fd)
        except OSError:
            pass

    def windows(self, *, conversion_error=None, identity_mismatch=False, invalid_handle=False):
        import ctypes
        kernel = SimpleNamespace(ReOpenFile=MagicMock(return_value=ctypes.c_void_p(-1).value if invalid_handle else 2 ** 35),
                                 CloseHandle=MagicMock(return_value=True))
        def convert(handle, flags):
            if conversion_error:
                raise conversion_error
            if identity_mismatch:
                other = self.root / 'foreign'
                other.write_bytes(b'foreign')
                result = os.open(other, os.O_WRONLY)
            else:
                result = os.dup(self.fd)
            self.addCleanup(self.close_if_open, result)
            return result
        crt = SimpleNamespace(get_osfhandle=MagicMock(return_value=2 ** 34), open_osfhandle=MagicMock(side_effect=convert))
        facade = SimpleNamespace(name='nt', O_WRONLY=os.O_WRONLY, O_BINARY=0x8000, O_NOINHERIT=0x80,
                                 fstat=os.fstat, set_inheritable=os.set_inheritable, close=os.close)
        stack = contextlib.ExitStack()
        stack.enter_context(patch.object(hooks, 'os', facade))
        stack.enter_context(patch.object(ctypes, 'WinDLL', return_value=kernel, create=True))
        stack.enter_context(patch.object(ctypes, 'get_last_error', return_value=32, create=True))
        stack.enter_context(patch.dict(sys.modules, {'msvcrt': crt}))
        return stack, kernel, crt

    def test_posix_noop_preserves_the_owned_descriptor(self):
        with patch.object(hooks, 'os', SimpleNamespace(name='posix')):
            self.assertEqual(hooks._guard_delete_shared_fd(self.fd), self.fd)
        self.assertEqual(os.fstat(self.fd).st_ino, self.path.stat().st_ino)

    def test_windows_same_file_transfer_requests_delete_sharing_and_closes_original(self):
        stack, kernel, crt = self.windows()
        with stack:
            shared = hooks._guard_delete_shared_fd(self.fd)
        kernel.ReOpenFile.assert_called_once_with(2 ** 34, 0x40000000, 7, 0)
        crt.open_osfhandle.assert_called_once_with(2 ** 35, os.O_WRONLY | 0x8000 | 0x80)
        kernel.CloseHandle.assert_not_called()
        self.assertFalse(os.get_inheritable(shared))
        self.assertEqual(os.fstat(shared).st_ino, self.path.stat().st_ino)
        with self.assertRaises(OSError):
            os.fstat(self.fd)

    def test_conversion_failure_closes_raw_handle_and_keeps_original(self):
        stack, kernel, _ = self.windows(conversion_error=OSError('CRT conversion failed'))
        with stack, self.assertRaisesRegex(OSError, 'CRT conversion'):
            hooks._guard_delete_shared_fd(self.fd)
        kernel.CloseHandle.assert_called_once_with(2 ** 35)
        self.assertEqual(os.fstat(self.fd).st_ino, self.path.stat().st_ino)

    def test_identity_mismatch_closes_converted_fd_not_raw_handle(self):
        stack, kernel, _ = self.windows(identity_mismatch=True)
        with stack, self.assertRaisesRegex(ValueError, 'shared handle identity changed'):
            hooks._guard_delete_shared_fd(self.fd)
        kernel.CloseHandle.assert_not_called()
        self.assertEqual(os.fstat(self.fd).st_ino, self.path.stat().st_ino)

    def test_invalid_handle_keeps_original_and_never_converts(self):
        stack, kernel, crt = self.windows(invalid_handle=True)
        with stack, self.assertRaises(OSError):
            hooks._guard_delete_shared_fd(self.fd)
        kernel.CloseHandle.assert_not_called()
        crt.open_osfhandle.assert_not_called()
        self.assertEqual(os.fstat(self.fd).st_ino, self.path.stat().st_ino)


if __name__ == '__main__':
    unittest.main()

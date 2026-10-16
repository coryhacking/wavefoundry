"""Synthetic capability and cross-run device controls; no native OS qualification."""
import contextlib
import copy
import errno
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import embedded_model_bundle as embedded
import contained_files
import upgrade_extensions as hooks
import upgrade_lib
import test_index_upgrade_guard as existing


class EmbeddedOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        source = self.root / 'source.zip'
        source.write_bytes(b'owned combined archive')
        self.proof = embedded.retain(self.root, source)
        self.path = Path(self.proof['path'])

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


if __name__ == '__main__':
    unittest.main()

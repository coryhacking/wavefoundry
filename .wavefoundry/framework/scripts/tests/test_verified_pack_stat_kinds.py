"""21alh: handle and path stats may disagree on ctime alone (Windows, Python 3.12).

The platform cannot be forced, so each test patches the stat boundary: the
open-handle side (``os.fstat``) or the path side (``os.stat``) of a regular
file reports a shifted field while every other field stays real.
"""
import contextlib
import copy
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contained_files
import upgrade_lib
import upgrade_protocol
import upgrade_wavefoundry as runner
import upgrade_extensions as hooks
import test_index_upgrade_guard as guard_tests  # module import: no re-collected tests

_REAL_FSTAT = os.fstat
_REAL_STAT = os.stat


class _Shifted:
    """A real stat result with one integer field moved; attribute access only."""

    def __init__(self, real, field, delta):
        self._real, self._field, self._delta = real, field, delta

    def __getattr__(self, name):
        value = getattr(self._real, name)
        return value + self._delta if name == self._field else value


def shifted_fstat(field='st_ctime_ns', delta=1000):
    def fstat(fd):
        real = _REAL_FSTAT(fd)
        return _Shifted(real, field, delta) if stat.S_ISREG(real.st_mode) else real
    return patch.object(os, 'fstat', fstat)


def shifted_pack_path_stat(field='st_ctime_ns', delta=1000):
    def stat_(path, *args, **kwargs):
        real = _REAL_STAT(path, *args, **kwargs)
        if stat.S_ISREG(real.st_mode) and os.path.basename(os.fspath(path)).startswith('wf-verified-pack-'):
            return _Shifted(real, field, delta)
        return real
    return patch.object(os, 'stat', stat_)


class VerifiedPackStatKindTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.parent = self.root / 'owned-pack-parent'
        self.parent.mkdir()
        self.enterContext(patch.object(tempfile, 'tempdir', str(self.parent)))
        self.source = self.root / 'selected.zip'
        self.source.write_bytes(b'private verified payload')

    def stage(self):
        with patch.object(upgrade_protocol, 'validate_feature_pack', return_value={}):
            staged = runner._stage_pack_for_consumption(self.source)
        self.addCleanup(staged.unlink, missing_ok=True)
        return staged, copy.deepcopy(runner._VERIFIED_PACK_IDENTITIES[str(staged)])

    def cleanup(self, staged, proof):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = runner._cleanup_verified_pack(staged, proof)
        return result, output.getvalue()

    def test_ctime_only_handle_difference_stages_and_cleans_up(self):
        with shifted_fstat():
            staged, proof = self.stage()
            self.assertEqual(staged.read_bytes(), self.source.read_bytes())
            result, output = self.cleanup(staged, proof)
        self.assertTrue(result, output)
        self.assertFalse(staged.exists())

    def test_ctime_only_handle_difference_cleans_up_a_normally_staged_pack(self):
        staged, proof = self.stage()
        with shifted_fstat():
            result, output = self.cleanup(staged, proof)
        self.assertTrue(result, output)
        self.assertFalse(staged.exists())

    def test_real_handle_changes_still_refuse_staging_and_retain_cleanup(self):
        for field in ('st_ino', 'st_size', 'st_mtime_ns'):
            with self.subTest(field=field):
                with shifted_fstat(field), patch.object(upgrade_protocol, 'validate_feature_pack', return_value={}), \
                        self.assertRaisesRegex(ValueError, 'verified private pack changed before validation'):
                    runner._stage_pack_for_consumption(self.source)
                staged, proof = self.stage()
                with shifted_fstat(field):
                    result, output = self.cleanup(staged, proof)
                self.assertFalse(result)
                self.assertTrue(staged.exists())
                self.assertIn('fresh opened file identity changed', output)

    def test_same_kind_path_ctime_difference_still_retains(self):
        staged, proof = self.stage()
        with shifted_pack_path_stat():
            result, output = self.cleanup(staged, proof)
        self.assertFalse(result)
        self.assertTrue(staged.exists())
        self.assertIn('verified file identity changed', output)

    def test_same_kind_ctime_change_across_validation_is_refused(self):
        # The path stats taken before and after validation are the same kind,
        # so a ctime change between them still refuses (delivery finding S1).
        validated = []

        def after_validation(real_call):
            def call(path, *args, **kwargs):
                real = real_call(path, *args, **kwargs)
                if validated and stat.S_ISREG(real.st_mode) and os.path.basename(os.fspath(path)).startswith('wf-verified-pack-'):
                    return _Shifted(real, 'st_ctime_ns', 1000)
                return real
            return call
        with patch.object(os, 'stat', after_validation(_REAL_STAT)), \
                patch.object(os, 'lstat', after_validation(os.lstat)), \
                patch.object(upgrade_protocol, 'validate_feature_pack', side_effect=lambda path: validated.append(path)), \
                self.assertRaisesRegex(ValueError, 'verified private pack identity could not be established'):
            runner._stage_pack_for_consumption(self.source)
        self.assertEqual(len(validated), 1)

    def test_five_field_proof_recorded_by_1_35_0_is_accepted(self):
        staged, proof = self.stage()
        # 1.35.0 recorded the path-derived lstat identity with all five fields.
        entry = staged.lstat()
        recorded = {'path': str(staged), 'parent': proof['parent'],
                    'identity': [entry.st_dev, entry.st_ino, entry.st_size, entry.st_mtime_ns, entry.st_ctime_ns]}
        self.assertEqual(recorded['identity'], proof['identity'])
        with shifted_fstat():
            result, output = self.cleanup(staged, recorded)
        self.assertTrue(result, output)
        self.assertFalse(staged.exists())


class DurableGuardPackStatKindTests(unittest.TestCase):
    setUp = guard_tests.DurableIndexGuardContinuationTests.setUp
    capture = guard_tests.DurableIndexGuardContinuationTests.capture
    record = guard_tests.DurableIndexGuardContinuationTests.record
    refuse = guard_tests.DurableIndexGuardContinuationTests.refuse
    prepare = guard_tests.DurableIndexGuardContinuationTests.prepare
    handoff = guard_tests.DurableIndexGuardContinuationTests.handoff

    def test_ctime_only_difference_retains_reads_and_validates_the_durable_pack(self):
        # Drives _read_guard_pack's lstat/opened checks (source read and
        # publication read-back) and validation's proof against the path stat.
        self.prepare()
        with shifted_fstat():
            action = self.handoff()
            self.assertIn('--update-index', action['command_argv'])
            lock = upgrade_lib.read_upgrade_lock(self.root)
            path = hooks.validate_index_guard_durable_pack(self.root, lock)
        self.assertEqual(path.read_bytes(), self.package.read_bytes())

    def test_ctime_only_difference_keeps_the_publication_recheck_proof(self):
        self.prepare()
        target = self.root / hooks._INDEX_GUARD_PACK_REL
        lock = upgrade_lib.read_upgrade_lock(self.root)
        record = copy.deepcopy(lock['index_guard_handoff'])
        read = hooks._read_guard_pack

        def fail_read_back(root, path, helper):
            if path == target:
                raise PermissionError('read-back refused')
            return read(root, path, helper)
        with shifted_fstat(), patch.object(hooks, '_read_guard_pack', side_effect=fail_read_back), \
                patch.object(contained_files, 'unlink_contained', side_effect=PermissionError('rollback refused')), \
                self.assertRaises(hooks._GuardPackReadbackUnavailable) as caught:
            hooks._retain_index_guard_pack(self.ctx, lock, record)
        self.assertEqual(caught.exception.retained_fields['zip_path'], str(target))
        self.assertEqual(record['durable_pack']['identity'][1], target.lstat().st_ino)

    def test_real_handle_changes_still_refuse_the_durable_pack_read(self):
        # Requirement 4 on the guard path: only ctime is ignored (finding E1).
        self.prepare()
        self.handoff()
        path = self.root / hooks._INDEX_GUARD_PACK_REL
        helper = hooks._guard_contained_helper()
        hooks._read_guard_pack(self.root, path, helper)
        lock = upgrade_lib.read_upgrade_lock(self.root)
        real_lstat = os.lstat
        for field in ('st_ino', 'st_size', 'st_mtime_ns'):
            # Handle side: the contained open refuses inode and size changes
            # itself (an OSError); mtime reaches the guard's own comparison.
            with self.subTest(side='handle', field=field), shifted_fstat(field), \
                    self.assertRaises((ValueError, OSError)):
                hooks._read_guard_pack(self.root, path, helper)
            # Path side: the handle-derived proof against the path stat.
            def lstat_(target, *args, _field=field, **kwargs):
                real = real_lstat(target, *args, **kwargs)
                if os.path.basename(os.fspath(target)) == path.name and stat.S_ISREG(real.st_mode):
                    return _Shifted(real, _field, 1000)
                return real
            with self.subTest(side='path', field=field), patch.object(os, 'lstat', lstat_), \
                    self.assertRaisesRegex(ValueError, 'index_guard_durable_pack_invalid'):
                hooks.validate_index_guard_durable_pack(self.root, lock)

    def test_real_path_change_refuses_the_publication_recheck(self):
        # The rollback re-check compares the target's path stat with the held
        # descriptor; an inode change there must still refuse (finding E1).
        self.prepare()
        target = self.root / hooks._INDEX_GUARD_PACK_REL
        lock = upgrade_lib.read_upgrade_lock(self.root)
        record = copy.deepcopy(lock['index_guard_handoff'])
        read = hooks._read_guard_pack
        real_lstat = os.lstat

        def fail_read_back(root, path, helper):
            if path == target:
                raise PermissionError('read-back refused')
            return read(root, path, helper)

        def lstat_(path, *args, **kwargs):
            real = real_lstat(path, *args, **kwargs)
            if os.path.basename(os.fspath(path)) == target.name and stat.S_ISREG(real.st_mode):
                return _Shifted(real, 'st_ino', 1000)
            return real
        with patch.object(hooks, '_read_guard_pack', side_effect=fail_read_back), \
                patch.object(contained_files, 'unlink_contained', side_effect=PermissionError('rollback refused')), \
                patch.object(os, 'lstat', lstat_), \
                self.assertRaisesRegex(ValueError, 'index_guard_durable_pack_recovery_required'):
            hooks._retain_index_guard_pack(self.ctx, lock, record)

    def test_five_field_proof_recorded_by_1_35_0_is_accepted(self):
        self.prepare()
        self.handoff()
        lock = upgrade_lib.read_upgrade_lock(self.root)
        path = self.root / hooks._INDEX_GUARD_PACK_REL
        # 1.35.0 bound the proof from the held descriptor's five-field fstat.
        fd = os.open(path, os.O_RDONLY)
        try:
            held = os.fstat(fd)
        finally:
            os.close(fd)
        lock['index_guard_handoff']['durable_pack']['identity'] = [
            held.st_dev, held.st_ino, held.st_size, held.st_mtime_ns, held.st_ctime_ns]
        self.assertEqual(hooks.validate_index_guard_durable_pack(self.root, lock), path)


if __name__ == '__main__':
    unittest.main()

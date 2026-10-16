"""Verified temporary ownership survives sessions without broadening old proofs."""
import contextlib
import copy
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
import upgrade_wavefoundry as runner
import upgrade_protocol
import contained_files

class VerifiedPackOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.source = self.root / 'selected.zip'
        self.source.write_bytes(b'private verified payload')
        with patch.object(upgrade_protocol, 'validate_feature_pack', return_value={}):
            self.staged = runner._stage_pack_for_consumption(self.source)
        self.proof = copy.deepcopy(runner._VERIFIED_PACK_IDENTITIES[str(self.staged)])
        self.addCleanup(self.staged.unlink, missing_ok=True)

    def cleanup(self, path=None, proof=None):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            result=runner._cleanup_verified_pack(path or self.staged, proof or self.proof)
        return result, output.getvalue()

    def test_changed_temp_directory_and_device_drift_cleanup_owned_pack(self):
        self.proof['identity'][0] += 123
        if 'parent' in self.proof:
            self.proof['parent']['identity'][0] += 456
        with patch.object(tempfile, 'gettempdir', return_value=str(self.root / 'new-session')):
            result, output = self.cleanup()
        self.assertTrue(result)
        self.assertFalse(self.staged.exists())
        self.assertEqual(output, '')

    def test_capability_limited_cleanup_reuses_bounded_path_fallback(self):
        with patch.object(contained_files, '_dir_fd_supported', return_value=False):
            result, output = self.cleanup()
        self.assertTrue(result)
        self.assertFalse(self.staged.exists())
        self.assertEqual(output, '')

    def test_legacy_proof_stays_bounded_to_current_temp_and_rejects_changed_session(self):
        old = {'path': self.proof['path'], 'identity': list(self.proof['identity'])}
        with patch.object(tempfile, 'gettempdir', return_value=str(self.root / 'new-session')):
            result, output = self.cleanup(proof=old)
        self.assertFalse(result)
        self.assertTrue(self.staged.exists())
        self.assertIn('legacy', output)
        self.assertTrue(self.cleanup(proof=old)[0])

    def test_mutated_file_fields_and_unusable_identity_retain(self):
        for slot in range(1, 5):
            proof=copy.deepcopy(self.proof);proof['identity'][slot] += 1
            with self.subTest(slot=slot):
                self.assertFalse(self.cleanup(proof=proof)[0])
                self.assertTrue(self.staged.exists())
        for value in (0, None, True):
            proof=copy.deepcopy(self.proof);proof['identity'][1]=value
            with self.subTest(value=value): self.assertFalse(self.cleanup(proof=proof)[0])
        self.staged.write_bytes(b'changed private bytes')
        self.assertFalse(self.cleanup()[0])
        self.assertTrue(self.staged.exists())

    def test_forged_path_and_parent_cannot_grant_ownership(self):
        unowned=self.root / 'wf-verified-pack-unowned.zip';unowned.write_bytes(self.staged.read_bytes())
        proof=copy.deepcopy(self.proof);proof['path']=str(unowned);proof['identity']=runner._pack_entry_identity(unowned)
        self.assertFalse(self.cleanup(path=unowned, proof=proof)[0])
        self.assertTrue(unowned.exists())
        for bad in ({}, {'kind':'temporary','path':str(self.staged.parent),'identity':[0,0]}):
            proof=copy.deepcopy(self.proof);proof['parent']=bad
            self.assertFalse(self.cleanup(proof=proof)[0])
        self.assertTrue(self.staged.exists())

    def test_validated_absence_only_accepts_owned_coordinates(self):
        self.staged.unlink()
        self.assertTrue(self.cleanup()[0])
        proof=copy.deepcopy(self.proof);proof['parent']['identity'][1] += 1
        self.assertFalse(self.cleanup(proof=proof)[0])
        absent=self.root / 'wf-verified-pack-absent.zip'
        old={'path':str(absent),'identity':list(self.proof['identity'])}
        self.assertFalse(self.cleanup(path=absent, proof=old)[0])

    def test_parent_replacement_or_link_and_final_replacement_refuse(self):
        # Own one temporary parent, then change its identity beneath the proof.
        parent=self.root / 'private-tmp';parent.mkdir()
        with patch.object(tempfile, 'tempdir', str(parent)), patch.object(upgrade_protocol, 'validate_feature_pack', return_value={}):
            staged=runner._stage_pack_for_consumption(self.source)
        proof=copy.deepcopy(runner._VERIFIED_PACK_IDENTITIES[str(staged)])
        retained=parent.with_name('old-parent');parent.rename(retained);parent.mkdir()
        replacement=parent/staged.name;replacement.write_bytes(b'competing archive')
        self.assertFalse(self.cleanup(path=staged, proof=proof)[0])
        self.assertEqual(replacement.read_bytes(),b'competing archive')
        replacement.unlink();parent.rmdir();parent.symlink_to(retained, target_is_directory=True)
        self.assertFalse(self.cleanup(path=staged, proof=proof)[0])
        self.assertTrue((retained/staged.name).exists())

    def test_same_open_device_change_and_preunlink_replacement_refuse(self):
        real_fstat=os.fstat
        def changed(fd):
            entry=real_fstat(fd)
            if stat.S_ISREG(entry.st_mode):
                values={key:getattr(entry,key) for key in dir(entry) if key.startswith('st_')}
                values['st_dev'] += 99
                return SimpleNamespace(**values)
            return entry
        with patch.object(os,'fstat',side_effect=changed):
            self.assertFalse(self.cleanup()[0])
        self.assertTrue(self.staged.exists())

    def test_preunlink_final_replacement_preserves_both_entries(self):
        actual_stat=os.stat
        calls=0
        saved=self.staged.with_suffix('.saved')
        self.addCleanup(saved.unlink, missing_ok=True)
        def replace_before_final_stat(path, *args, **kwargs):
            nonlocal calls
            if path == self.staged.name and kwargs.get('dir_fd') is not None:
                calls += 1
                if calls == 2:
                    self.staged.rename(saved)
                    self.staged.write_bytes(b'competing entry')
            return actual_stat(path,*args,**kwargs)
        with patch.object(os,'stat',side_effect=replace_before_final_stat):
            self.assertFalse(self.cleanup()[0])
        self.assertEqual(self.staged.read_bytes(),b'competing entry')
        self.assertTrue(saved.exists())

    def test_staging_never_adopts_or_deletes_postvalidation_replacement(self):
        replaced=[]
        def replace(path):
            saved=path.with_suffix('.saved')
            path.rename(saved);path.write_bytes(b'operator replacement')
            replaced.extend((path,saved))
            self.addCleanup(path.unlink,missing_ok=True)
            self.addCleanup(saved.unlink,missing_ok=True)
        with patch.object(upgrade_protocol,'validate_feature_pack',side_effect=replace), self.assertRaises(ValueError):
            runner._stage_pack_for_consumption(self.source)
        self.assertEqual(replaced[0].read_bytes(),b'operator replacement')
        self.assertEqual(replaced[1].read_bytes(),self.source.read_bytes())

    def test_diagnostics_escape_controls_and_hide_absolute_roots(self):
        forged=self.root / 'wf-verified-pack-\ncontrol.zip'
        proof={'path':str(forged),'identity':[1,2,3,4,5]}
        _, output=self.cleanup(path=forged,proof=proof)
        self.assertNotIn(str(self.root),output)
        self.assertIn('\\n',output)
        self.assertLess(len(output),500)
        self.assertIn('parent',output)

if __name__=='__main__': unittest.main()

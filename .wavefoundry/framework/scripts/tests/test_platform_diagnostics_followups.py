"""Synthetic platform diagnostics; no native Windows qualification implied."""
from pathlib import Path
import errno
import os
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import workflow_include_prefixes as prefixes
import setup_index
import record_paths
import review_evidence
import contained_files


class InputDiagnosticsTests(unittest.TestCase):
    def test_bom_prefixes_and_malformed_mapping_remain_nonraising(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'docs/workflow-config.json'
            target.parent.mkdir()
            target.write_bytes(b'\xef\xbb\xbf{"indexing":{"project_include_prefixes":["product/"]}}')
            self.assertEqual(prefixes.read_project_include_prefixes(root),
                             {'docs': ('product',), 'code': ('product',)})
            for data in (b'\xef\xbb\xbf{', b'[]', b'null'):
                target.write_bytes(data)
                self.assertEqual(prefixes.read_project_include_prefixes(root), {'docs': (), 'code': ()})

    def test_shim_notice_names_only_command_scripts_and_preserves_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('uv.cmd', 'uv.bat'):
                (root / name).write_text('must never execute')
            with patch.dict(os.environ, {'PATH': str(root)}), patch.object(setup_index.subprocess, 'run',
                    side_effect=AssertionError('shim execution')):
                message = setup_index._uv_required_message(windows=True)
            self.assertIn('uv.bat, uv.cmd', message)
            self.assertIn('refused, not executed', message)
            self.assertIn('pinned, hash-verified uv bootstrap', message)
            self.assertNotIn(directory, message)


class PathErrorDiagnosticsTests(unittest.TestCase):
    def test_windows_missing_parent_long_path_and_invalid_name(self):
        for length, code, absent in [(40, 3, True), (400, 3, False), (400, 2, True)]:
            path = Path('/' + ('a/' * (length // 2)))
            error = FileNotFoundError(errno.ENOENT, 'not found')
            error.winerror = code
            with self.subTest(length=length, code=code), patch.object(record_paths.os, 'stat', side_effect=error):
                if absent:
                    self.assertFalse(record_paths.record_root_is_dir(path, record_paths.WAVES_ROOT))
                else:
                    with self.assertRaises(record_paths.RecordRootUnreadable) as caught:
                        record_paths.record_root_is_dir(path, record_paths.WAVES_ROOT)
                    self.assertIn('possible long-path', str(caught.exception))
            with self.subTest(authority=True, length=length, code=code), \
                    patch.object(review_evidence.os, 'lstat', side_effect=error):
                if absent:
                    self.assertIsNone(review_evidence._authority_member_lstat(path))
                else:
                    with self.assertRaises(OSError) as caught:
                        review_evidence._authority_member_lstat(path)
                    self.assertIn('possible long-path', str(caught.exception))
        error = OSError(errno.EINVAL, 'invalid')
        with patch.object(record_paths.os, 'stat', side_effect=error):
            with self.assertRaises(record_paths.RecordRootUnreadable) as caught:
                record_paths.record_root_is_dir(Path('bad'), record_paths.WAVES_ROOT)
            self.assertIn('possible reserved/invalid name', str(caught.exception))


class PermissionDiagnosticsTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'posix' and hasattr(os, 'fchmod'), 'POSIX descriptor permission control')
    def test_failed_chmod_requires_actual_temporary_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / 'data'
            target.write_bytes(b'old')
            target.chmod(0o600)
            old_umask = os.umask(0o077)
            try:
                with patch.object(contained_files.os, 'fchmod', side_effect=PermissionError(errno.EPERM, 'denied')):
                    self.assertTrue(contained_files.write_contained_bytes(root, target, b'new', mode=0o600))
                    before = target.read_bytes()
                    with self.assertRaises(OSError):
                        contained_files.write_contained_bytes(root, target, b'bad', mode=0o777)
            finally:
                os.umask(old_umask)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(list(root.glob('.*.tmp')), [])

    def test_windows_readonly_refuses_before_publication(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / 'data'
            target.write_bytes(b'original')
            original = contained_files.os.lstat
            def readonly(path, *args, **kwargs):
                info = original(path, *args, **kwargs)
                if Path(path) == target:
                    fields = {name: getattr(info, name) for name in dir(info) if name.startswith('st_')}
                    fields['st_file_attributes'] = 1
                    return SimpleNamespace(**fields)
                return info
            with patch.object(contained_files, '_windows', return_value=True), \
                    patch.object(contained_files.os, 'lstat', side_effect=readonly), \
                    patch.object(contained_files.os, 'replace', side_effect=AssertionError('publication reached')):
                with self.assertRaises(contained_files.ContainedFileRefused) as caught:
                    contained_files.write_contained_bytes(root, target, b'changed')
            self.assertIn('read-only', str(caught.exception))
            self.assertEqual(target.read_bytes(), b'original')
            self.assertEqual(list(root.glob('.*.tmp')), [])


if __name__ == '__main__':
    unittest.main()

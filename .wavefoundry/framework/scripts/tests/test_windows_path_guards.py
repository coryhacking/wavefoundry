"""20qrs: exact Windows metadata outcomes at each named refusal boundary."""
from pathlib import Path
import ast
import inspect
import os
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import bytecode_cache
import contained_files as cf
import lifecycle_lock
import record_paths
import vocabulary_profile
import render_agent_surfaces as render
import review_evidence
import runtime_lock
import upgrade_bridge_bootstrap as bridge
import upgrade_wavefoundry as upgrade
import upgrade_extensions
from wave_lint_lib import helpers
from nt_metadata_support import MISSING_TAG, nt_stat

CASES = [(0x9000001A, False), (0x80000013, False), (0xA000000C, True),
         (0xA0000003, True), (0x20001234, True), (MISSING_TAG, True),
         (None, True), ('bad', True), (-1, True), (0, True), (True, True),
         (0x100000000, True)]


class WindowsPathGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        roots = record_paths.load_record_roots(self.root)
        self.waves = roots.waves
        self.wave = self.waves / '1abcd test'
        self.wave.mkdir(parents=True)
        roots.plans.mkdir(parents=True, exist_ok=True)
        self.record = self.wave / vocabulary_profile.RECORD_FILENAME
        self.record.write_text('# Wave\n')
        self.ledger = self.wave / 'events.jsonl'
        self.ledger.write_text('')
        self.file = self.root / 'docs/a.md'
        self.file.write_text('ordinary')

    def oracle(self, target, tag):
        original = os.lstat
        def lstat(path, *args, **kwargs):
            info = original(path, *args, **kwargs)
            return nt_stat(info, tag) if Path(path) == target else info
        return patch.object(os, 'lstat', side_effect=lstat)

    def test_named_boundaries_match_exact_tag_outcomes(self):
        boundaries = [
            ('contained-read', self.file, lambda: self._read_refused()),
            ('contained-directory', self.wave, lambda: self._directory_refused()),
            ('lint', self.file, lambda: not helpers.doc_entry_is_regular(self.root, self.file)),
            ('render', self.file, lambda: render._is_link_or_reparse(self.file, os.lstat(self.file))),
            ('cache', self.file, lambda: bytecode_cache.is_linked(self.file)),
            ('authority-directory', self.wave, lambda: review_evidence._review_authority_path_error(self.record) is not None),
            ('authority-record', self.record, lambda: review_evidence._review_authority_path_error(self.record) is not None),
            ('authority-ledger', self.ledger, lambda: review_evidence._review_authority_path_error(self.record) is not None),
            ('record-component', self.wave, lambda: record_paths._has_symlink_component(self.root, list(self.wave.relative_to(self.root).parts))),
            ('record-exemption', self.wave, lambda: record_paths._refusal_exempt(self.wave)),
            ('record-subdirs', self.wave, lambda: self.wave not in record_paths._list_subdirs(self.waves)),
            ('record-container', self.record, lambda: self._container_refused()),
            ('sidecar-parent', self.waves, lambda: upgrade._retired_sidecar_path_error(self.root, self.record) is not None),
            ('sidecar-member', self.record, lambda: upgrade._retired_sidecar_path_error(self.root, self.record) is not None),
        ]
        for tag, expected in CASES:
            for name, target, probe in boundaries:
                with self.subTest(boundary=name, tag=repr(tag)), self.oracle(target, tag), \
                        patch.object(cf, '_dir_fd_supported', return_value=False):
                    self.assertEqual(probe(), expected)

    def _read_refused(self):
        try:
            cf.read_contained_bytes(self.root, self.file, max_bytes=1024, follow_links=False)
        except cf.ContainedFileRefused as exc:
            self.assertEqual(exc.cause, cf.CAUSE_NOT_REGULAR)
            return True
        return False

    def _directory_refused(self):
        try:
            fd = cf.open_contained_dir(self.root, self.wave.relative_to(self.root), refuse_reparse=True)
        except cf.ContainedFileRefused as exc:
            self.assertEqual(exc.cause, cf.CAUSE_LINK_COMPONENT)
            return True
        if fd is not None:
            os.close(fd)
        return False

    def _container_refused(self):
        with patch.object(record_paths, 'OPEN_CONTAINER_SCOPE', 'parent'), \
                patch.object(record_paths, 'NESTED', True):
            try:
                record_paths.open_container_scope(self.root, self.record, wave_dirs=[self.wave])
            except record_paths.RecordLayoutInvalid:
                return True
        return False

    def test_every_copy_and_lock_predicate_has_exact_outcomes(self):
        modules = (cf, runtime_lock, bridge, bytecode_cache, record_paths, review_evidence, lifecycle_lock, upgrade_extensions)
        for tag, expected in CASES:
            info = nt_stat(os.lstat(self.file), tag)
            entry = SimpleNamespace(is_symlink=lambda: False, stat=lambda **_: info)
            for module in modules:
                with self.subTest(copy=module.__name__, tag=repr(tag)):
                    self.assertEqual(module._is_link_metadata(info), expected)
            with self.subTest(copy='lifecycle_lock', tag=repr(tag)), \
                    patch.object(lifecycle_lock, 'os', SimpleNamespace(name='nt')):
                self.assertEqual(lifecycle_lock._is_link_entry(entry), expected)
        posix = os.lstat(self.file)
        for module in modules:
            self.assertFalse(module._is_link_metadata(posix))
            symlink = SimpleNamespace(st_mode=stat.S_IFLNK)
            self.assertTrue(module._is_link_metadata(symlink))
        def body(function):
            node = ast.parse(inspect.getsource(function)).body[0]
            node.body = [item for item in node.body if not isinstance(item, ast.Expr)]
            return ast.dump(node, include_attributes=False)
        bodies = {body(module._is_link_metadata) for module in modules}
        sidecar = ast.parse(inspect.getsource(upgrade._retired_sidecar_path_error)).body[0]
        nested = next(node for node in sidecar.body
                      if isinstance(node, ast.FunctionDef) and node.name == '_is_link_metadata')
        nested.body = [item for item in nested.body if not isinstance(item, ast.Expr)]
        bodies.add(ast.dump(nested, include_attributes=False))
        self.assertEqual(len(bodies), 1)

    def test_non_surrogate_keeps_size_and_regular_file_guards(self):
        with self.oracle(self.file, 0x9000001A), patch.object(cf, '_dir_fd_supported', return_value=False):
            with self.assertRaises(cf.ContainedFileRefused) as caught:
                cf.read_contained_bytes(self.root, self.file, max_bytes=1, follow_links=False)
            self.assertEqual(caught.exception.cause, cf.CAUSE_SIZE)
        with self.oracle(self.wave, 0x80000013), patch.object(cf, '_dir_fd_supported', return_value=False):
            with self.assertRaises(cf.ContainedFileRefused) as caught:
                cf.read_contained_bytes(self.root, self.wave, max_bytes=1024, follow_links=False)
            self.assertEqual(caught.exception.cause, cf.CAUSE_NOT_REGULAR)

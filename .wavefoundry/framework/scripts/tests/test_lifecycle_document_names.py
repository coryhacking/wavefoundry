"""Lifecycle-guide rename contracts; fixtures never copy project-authored docs."""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import render_agent_surfaces as ras
import review_policy
import vocabulary_profile
import record_paths
from wave_lint_lib.core_validators import check_review_policy_carriers

# Historical inputs are deliberately independent of the production table.
PAIRS = (
    ('docs/contributing/feature-workflow.md', 'docs/contributing/delivery-workflow.md'),
    ('docs/contributing/feature-wave-lifecycle-overview.md', 'docs/contributing/lifecycle-overview.md'),
)


class LifecycleDocumentMoveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'docs/contributing').mkdir(parents=True)

    def seed(self):
        for old, _new in PAIRS:
            path = self.root / old
            path.write_bytes(b'# Customized guide\r\n\r\nLocal prose.\r\n')
            path.chmod(0o640)

    def test_exact_bytes_modes_and_repeat(self):
        self.seed()
        originals = [(self.root / old).read_bytes() for old, _ in PAIRS]
        modes = [stat.S_IMODE((self.root / old).stat().st_mode) for old, _ in PAIRS]
        result = ras.migrate_lifecycle_document_renames(self.root)
        self.assertEqual(result.written, tuple(path for pair in PAIRS for path in pair))
        for index, (old, new) in enumerate(PAIRS):
            self.assertFalse((self.root / old).exists())
            self.assertEqual((self.root / new).read_bytes(), originals[index])
            if os.name != 'nt':
                self.assertEqual(stat.S_IMODE((self.root / new).stat().st_mode), modes[index])
        self.assertEqual(ras.migrate_lifecycle_document_renames(self.root).written, ())

    def test_second_pair_conflict_preserves_first_pair_too(self):
        self.seed()
        destination = self.root / PAIRS[1][1]
        destination.write_bytes(b'Independent destination\n')
        before = {p: p.read_bytes() for p in (self.root / 'docs/contributing').iterdir()}
        with self.assertRaisesRegex(RuntimeError, 'both exist'):
            ras.migrate_lifecycle_document_renames(self.root)
        self.assertEqual({p: p.read_bytes() for p in (self.root / 'docs/contributing').iterdir()}, before)

    def test_unsafe_source_and_destination_preserve_files(self):
        for polarity in ('source', 'destination', 'parent', 'directory'):
            with self.subTest(polarity=polarity), tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
                root = Path(tmp)
                directory = root / 'docs/contributing'
                directory.mkdir(parents=True)
                sentinel = Path(outside) / 'sentinel.md'
                sentinel.write_bytes(b'Outside remains untouched\n')
                old, new = (root / p for p in PAIRS[1])
                first = root / PAIRS[0][0]
                first.write_bytes(b'First must remain\n')
                if polarity == 'source':
                    old.symlink_to(sentinel)
                elif polarity == 'destination':
                    old.write_bytes(b'Old\n')
                    new.symlink_to(sentinel)
                elif polarity == 'directory':
                    old.mkdir()
                else:
                    first.unlink()
                    directory.rmdir()
                    directory.symlink_to(outside, target_is_directory=True)
                    old.write_bytes(b'Outside source\n')
                before = {p.name: p.read_bytes() for p in Path(outside).iterdir() if p.is_file()}
                with self.assertRaises(RuntimeError):
                    ras.migrate_lifecycle_document_renames(root)
                self.assertEqual({p.name: p.read_bytes() for p in Path(outside).iterdir() if p.is_file()}, before)
                if polarity != 'parent':
                    self.assertEqual(first.read_bytes(), b'First must remain\n')
                    self.assertFalse((root / PAIRS[0][1]).exists())

    def test_destination_race_is_exclusive(self):
        self.seed()
        publish = ras._write_review_carrier_text
        destination = self.root / PAIRS[0][1]
        def race(path, content, **kwargs):
            destination.write_bytes(b'Concurrent destination\n')
            return publish(path, content, **kwargs)
        with patch.object(ras, '_write_review_carrier_text', side_effect=race):
            with self.assertRaises(RuntimeError):
                ras.migrate_lifecycle_document_renames(self.root)
        self.assertEqual(destination.read_bytes(), b'Concurrent destination\n')
        self.assertEqual((self.root / PAIRS[0][0]).read_bytes(), b'# Customized guide\r\n\r\nLocal prose.\r\n')

    def test_unlink_failure_removes_only_new_copy(self):
        self.seed()
        unlink = Path.unlink
        old = self.root / PAIRS[0][0]
        def refuse(path, *args, **kwargs):
            if path == old.resolve():
                raise PermissionError('fixture refusal')
            return unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', refuse):
            with self.assertRaisesRegex(RuntimeError, 'preserved'):
                ras.migrate_lifecycle_document_renames(self.root)
        self.assertTrue(old.is_file())
        self.assertFalse((self.root / PAIRS[0][1]).exists())

    def test_links_reported_without_rewriting_history(self):
        self.seed()
        history = self.root / record_paths.WAVES_ROOT / 'history.md'
        history.parent.mkdir(parents=True)
        target = Path(os.path.relpath(self.root / PAIRS[0][0], history.parent)).as_posix()
        original = f'[Old guide]({target})\n'.encode()
        history.write_bytes(original)
        result = ras.migrate_lifecycle_document_renames(self.root)
        self.assertIn(f'{history.relative_to(self.root).as_posix()}:1', result.link_report)
        self.assertEqual(history.read_bytes(), original)

    def test_real_render_reconciles_policy_and_validation_follows_new_path(self):
        self.seed()
        prompts = self.root / 'docs/prompts'
        prompts.mkdir()
        (prompts / 'prompt-surface-manifest.json').write_text('{}\n')
        with contextlib.redirect_stderr(io.StringIO()):
            ras.render_agent_surfaces(self.root)
        prepare = self.root / vocabulary_profile.prompt_doc('prepare-wave')
        self.assertIn(review_policy.REVIEW_POLICY_SURFACE_MARKER_BEGIN, prepare.read_text())
        path = self.root / PAIRS[1][1]
        text = path.read_text()
        self.assertIn('Local prose.', text)
        self.assertIn(review_policy.REVIEW_POLICY_SURFACE_MARKER_BEGIN, text)
        self.assertFalse((self.root / PAIRS[1][0]).exists())
        self.assertEqual(check_review_policy_carriers(self.root), [])
        path.write_text('# Broken guide\n\nNo required anchors.\n')
        failures = check_review_policy_carriers(self.root)
        self.assertIn(f'{PAIRS[1][1]}: registered review-policy obligation is missing: policy', failures)
        self.assertIn(f'{PAIRS[1][1]}: registered review-policy obligation is missing: phase', failures)

    def test_sparse_render_does_not_create_optional_guides(self):
        with contextlib.redirect_stderr(io.StringIO()):
            ras.render_agent_surfaces(self.root)
        for pair in PAIRS:
            for rel in pair:
                self.assertFalse((self.root / rel).exists())


if __name__ == '__main__':
    unittest.main()

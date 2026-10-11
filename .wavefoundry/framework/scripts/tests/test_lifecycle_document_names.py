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
import review_evidence
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
        publish = ras._write_move_target
        destination = self.root / PAIRS[0][1]
        def race(path, content, **kwargs):
            destination.write_bytes(b'Concurrent destination\n')
            return publish(path, content, **kwargs)
        with patch.object(ras, '_write_move_target', side_effect=race) as publication:
            with self.assertRaises(RuntimeError):
                ras.migrate_lifecycle_document_renames(self.root)
        publication.assert_called_once()
        self.assertEqual(publication.call_args.args[0], destination.resolve())
        self.assertEqual(destination.read_bytes(), b'Concurrent destination\n')
        self.assertEqual((self.root / PAIRS[0][0]).read_bytes(), b'# Customized guide\r\n\r\nLocal prose.\r\n')

    def test_unlink_failure_removes_only_new_copy(self):
        self.seed()
        unlink = ras.contained_files.unlink_contained
        old = self.root / PAIRS[0][0]
        def refuse(root, path, *args, **kwargs):
            if path == old.resolve():
                raise PermissionError('fixture refusal')
            return unlink(root, path, *args, **kwargs)
        with patch.object(ras.contained_files, 'unlink_contained', side_effect=refuse) as removal:
            with self.assertRaisesRegex(RuntimeError, 'preserved'):
                ras.migrate_lifecycle_document_renames(self.root)
        self.assertEqual(removal.call_count, 2, 'source refusal must reach the real rollback')
        self.assertEqual(removal.call_args_list[0].args[1], old.resolve())
        self.assertEqual(removal.call_args_list[1].args[1], (self.root / PAIRS[0][1]).resolve())
        self.assertTrue(old.is_file())
        self.assertEqual(old.read_bytes(), b'# Customized guide\r\n\r\nLocal prose.\r\n')
        self.assertFalse((self.root / PAIRS[0][1]).exists())

    def test_history_is_not_read_or_rewritten(self):
        self.seed()
        history = self.root / record_paths.WAVES_ROOT / 'history.md'
        history.parent.mkdir(parents=True)
        target = Path(os.path.relpath(self.root / PAIRS[0][0], history.parent)).as_posix()
        original = f'[Old guide]({target})\n'.encode()
        history.write_bytes(original)
        result = ras.migrate_lifecycle_document_renames(self.root)
        self.assertEqual(result.link_report, ())
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


class BoundedDocumentRepairTests(unittest.TestCase):
    setUp = LifecycleDocumentMoveTests.setUp
    seed = LifecycleDocumentMoveTests.seed
    def peer(self, content):
        path = self.root / 'docs/consumer.md'
        path.write_bytes(content)
        path.chmod(0o640)
        return path

    def test_empty_pair_plan_never_traverses(self):
        self.peer(b'\xff')
        with patch.object(ras.os, 'scandir', side_effect=AssertionError('must not traverse')), \
                patch.object(ras, '_read_move_source_identity', side_effect=AssertionError('must not read')):
            self.assertEqual(ras._council_role_link_plan(self.root, []), ([], []))
            self.assertEqual(ras.migrate_role_and_lifecycle_documents(self.root).written, ())

    def test_lifecycle_preview_apply_self_links_suffixes_modes_and_history(self):
        old, new = PAIRS[0]
        source = self.root / old
        original = b'# Custom\r\n[self](feature-workflow.md#part)\r\n'
        source.write_bytes(original); source.chmod(0o640)
        peer = self.peer(b'[label](contributing/feature-workflow.md?q=1#part "title")\r\n'
                         b'`[literal](contributing/feature-workflow.md)`\r\n')
        before = peer.read_bytes()
        preview = ras.migrate_lifecycle_document_renames(self.root, apply=False)
        self.assertEqual(preview.written, ())
        self.assertIn('docs/consumer.md:1: would repair lifecycle document link', preview.link_report)
        self.assertEqual(source.read_bytes(), original); self.assertEqual(peer.read_bytes(), before)
        result = ras.migrate_lifecycle_document_renames(self.root)
        self.assertIsInstance(result.written, tuple); self.assertIsInstance(result.link_report, tuple)
        self.assertEqual((self.root / new).read_bytes(), original.replace(b'feature-workflow.md', b'delivery-workflow.md'))
        self.assertEqual(peer.read_bytes(), before.replace(b'contributing/feature-workflow.md?q', b'contributing/delivery-workflow.md?q'))
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE((self.root / new).stat().st_mode), 0o640)
            self.assertEqual(stat.S_IMODE(peer.stat().st_mode), 0o640)

    def test_failed_planned_write_preserves_source_then_retry(self):
        old, new = PAIRS[0]
        source = self.root / old; source.write_bytes(b'# Original\r\n'); source.chmod(0o640)
        peer = self.peer(b'[old](contributing/feature-workflow.md)\r\n')
        write = ras._write_review_carrier_text
        with patch.object(ras, '_write_review_carrier_text', side_effect=PermissionError('scratch write failure')):
            with self.assertRaisesRegex(RuntimeError, 'legacy sources preserved'):
                ras.migrate_lifecycle_document_renames(self.root)
        self.assertTrue(source.exists(), 'failed edits must retain legacy retry authority')
        self.assertEqual(source.read_bytes(), b'# Original\r\n'); self.assertFalse((self.root / new).exists())
        ras.migrate_lifecycle_document_renames(self.root)
        self.assertFalse(source.exists()); self.assertEqual((self.root / new).read_bytes(), b'# Original\r\n')
        self.assertIn(b'delivery-workflow.md', peer.read_bytes())
        self.assertEqual(ras.migrate_lifecycle_document_renames(self.root).written, ())

    def test_new_only_region_is_exact_retry_authority(self):
        old, new = PAIRS[1]
        target = self.root / new
        begin, end = review_policy.REVIEW_POLICY_SURFACE_MARKER_BEGIN, review_policy.REVIEW_POLICY_SURFACE_MARKER_END
        region = begin + '\r\n' + review_policy.REVIEW_POLICY_SURFACE_BLOCKS[new].replace('\n', '\r\n') + '\r\n' + end
        for text, eligible in [(region, True), (region + region, False), (end + begin, False),
                               (begin + '\nwrong\n' + end, False), ('# Lifecycle overview\n', False)]:
            with self.subTest(eligible=eligible, text=text[:30]):
                target.write_text(text, encoding='utf-8', newline='')
                peer = self.peer(b'[old](contributing/feature-wave-lifecycle-overview.md)\n')
                result = ras.migrate_lifecycle_document_renames(self.root)
                self.assertEqual(b'lifecycle-overview.md)' in peer.read_bytes() and b'feature-wave' not in peer.read_bytes(), eligible)
                if not eligible:
                    self.assertTrue(any('manually repair' in item for item in result.link_report))

    def test_unmarked_delivery_target_never_authorizes_repair(self):
        (self.root / PAIRS[0][1]).write_text('# Delivery workflow\n')
        peer = self.peer(b'[old](contributing/feature-workflow.md)\n')
        result = ras.migrate_lifecycle_document_renames(self.root)
        self.assertIn(b'feature-workflow.md', peer.read_bytes())
        self.assertTrue(any('unconfirmed' in item and 'manually repair' in item for item in result.link_report))

    def test_skip_unrelated_refused_undecodable_and_oversize_docs(self):
        self.seed()
        peer = self.peer(b'[old](contributing/feature-workflow.md)\n')
        bad = self.root / 'docs/bad.md'; bad.write_bytes(b'\xff')
        oversized = self.root / 'docs/large.md'; oversized.write_bytes(b'x' * 70)
        refusal = None
        with patch.object(ras, '_MIGRATION_MAX_DOC_BYTES', 64):
            try:
                result = ras.migrate_lifecycle_document_renames(self.root)
            except (OSError, RuntimeError) as exc:
                refusal = exc
        self.assertIsNone(refusal, 'unrelated refused documents must report and continue')
        self.assertIn(b'delivery-workflow.md', peer.read_bytes())
        self.assertEqual(bad.read_bytes(), b'\xff'); self.assertEqual(oversized.read_bytes(), b'x' * 70)
        self.assertTrue(any('bad.md' in line and 'skipped' in line and 'retry' in line for line in result.link_report))
        self.assertTrue(any('large.md' in line and 'per-file byte limit' in line for line in result.link_report))

    def test_all_aggregate_bounds_refuse_before_moves_or_edits(self):
        for limit, value, kind in [('_MIGRATION_MAX_ENTRIES', 1, 'entry-count'),
                                   ('_MIGRATION_MAX_DOCS', 1, 'document-count'),
                                   ('_MIGRATION_MAX_TOTAL_BYTES', 8, 'aggregate-byte')]:
            with self.subTest(kind=kind):
                self.seed(); peer = self.peer(b'[old](contributing/feature-workflow.md)\n')
                before = peer.read_bytes()
                with patch.object(ras, limit, value):
                    with self.assertRaisesRegex(RuntimeError, kind):
                        ras.migrate_role_and_lifecycle_documents(self.root)
                self.assertEqual(peer.read_bytes(), before)
                self.assertTrue((self.root / PAIRS[0][0]).is_file())
                self.assertFalse((self.root / PAIRS[0][1]).exists())

    def test_combined_real_render_uses_one_walk_and_reports_skips(self):
        self.seed()
        old, new = ras.COUNCIL_ROLE_RENAMES[0]
        role = self.root / old; role.parent.mkdir(parents=True); role.write_text(f'Role: {review_evidence.LEGACY_COUNCIL_ACTORS[0]}\n')
        self.peer(f'[role]({Path(old).relative_to("docs").as_posix()})\n[lifecycle](contributing/feature-workflow.md)\n'.encode())
        bad = self.root / 'docs/bad.md'; bad.write_bytes(b'\xff')
        error = io.StringIO()
        with patch.object(ras, '_migration_current_docs', wraps=ras._migration_current_docs) as walk, contextlib.redirect_stderr(error):
            result = ras.render_agent_surfaces(self.root)
        walk.assert_called_once()
        self.assertIsInstance(result, list)
        self.assertFalse(role.exists()); self.assertTrue((self.root / new).is_file())
        self.assertIn('bad.md', error.getvalue()); self.assertIn('retry', error.getvalue())
        self.assertEqual(bad.read_bytes(), b'\xff')

    def test_non_markdown_entries_count_and_linked_dirs_are_not_descended(self):
        self.seed(); unrelated = self.root / 'docs/generated'; unrelated.mkdir()
        for index in range(6): (unrelated / str(index)).write_bytes(b'')
        with patch.object(ras, '_MIGRATION_MAX_ENTRIES', 5):
            with self.assertRaisesRegex(RuntimeError, 'entry-count'):
                ras.migrate_lifecycle_document_renames(self.root)
        if os.name != 'nt':
            link = self.root / 'docs/linked'; link.symlink_to(unrelated, target_is_directory=True)
            with patch.object(ras.os, 'scandir', wraps=os.scandir) as scan:
                result = ras.migrate_lifecycle_document_renames(self.root)
            self.assertEqual(scan.call_count, 3, 'docs, contributing and the real directory only; no linked descent')
            self.assertTrue(link.is_symlink()); self.assertTrue(any('linked' in line and 'skipped' in line for line in result.link_report))

    def test_partial_edit_retry_moves_fresh_source_bytes_and_mode(self):
        old, new = PAIRS[0]; source = self.root / old
        source.write_bytes(b'# Local\r\n[self](feature-workflow.md)\r\n'); source.chmod(0o440)
        first = self.peer(b'[one](contributing/feature-workflow.md)\r\n')
        second = self.root / 'docs/second.md'; second.write_bytes(b'[two](contributing/feature-workflow.md)\r\n')
        write = ras._write_review_carrier_text
        fired = []
        def fail_once(path, *args, **kwargs):
            if path == second and not fired:
                fired.append(True); raise PermissionError('scratch interruption')
            return write(path, *args, **kwargs)
        with patch.object(ras, '_write_review_carrier_text', side_effect=fail_once):
            with self.assertRaisesRegex(RuntimeError, 'legacy sources preserved'):
                ras.migrate_lifecycle_document_renames(self.root)
        self.assertEqual(fired, [True]); self.assertTrue(source.exists()); self.assertFalse((self.root / new).exists())
        ras.migrate_lifecycle_document_renames(self.root)
        self.assertEqual((self.root / new).read_bytes(), b'# Local\r\n[self](delivery-workflow.md)\r\n')
        self.assertIn(b'delivery-workflow.md', first.read_bytes()); self.assertIn(b'delivery-workflow.md', second.read_bytes())
        if os.name != 'nt': self.assertEqual(stat.S_IMODE((self.root / new).stat().st_mode), 0o440)

    def test_required_source_refusal_blocks_before_independent_edits(self):
        self.seed(); peer = self.peer(b'[old](contributing/feature-workflow.md)\n'); before = peer.read_bytes()
        read = ras._read_move_source_identity
        def denied(root, rel, **kwargs):
            if rel == PAIRS[1][0]: raise PermissionError('scratch denied source')
            return read(root, rel, **kwargs)
        with patch.object(ras, '_read_move_source_identity', side_effect=denied):
            with self.assertRaisesRegex(RuntimeError, 'could not be read'):
                ras.migrate_role_and_lifecycle_documents(self.root)
        self.assertEqual(peer.read_bytes(), before); self.assertTrue((self.root / PAIRS[0][0]).is_file())
        inspect = os.lstat
        def denied_metadata(path, *args, **kwargs):
            if Path(path) == self.root / PAIRS[1][0]: raise PermissionError('scratch inaccessible candidate')
            return inspect(path, *args, **kwargs)
        with patch.object(ras.os, 'lstat', side_effect=denied_metadata):
            with self.assertRaisesRegex(RuntimeError, 'cannot be inspected.*PermissionError'):
                ras.migrate_role_and_lifecycle_documents(self.root)
        self.assertEqual(peer.read_bytes(), before); self.assertTrue((self.root / PAIRS[0][0]).is_file())

    def test_document_caps_exact_boundary_counts_each_read_once(self):
        old, new = PAIRS[0]; source = self.root / old; source.write_bytes(b'# Local\n')
        peer = self.peer(b'[old](contributing/feature-workflow.md)\n')
        expected = len(source.read_bytes()) + len(peer.read_bytes())
        read = ras._read_move_source_identity
        with patch.object(ras, '_MIGRATION_MAX_ENTRIES', 3), patch.object(ras, '_MIGRATION_MAX_DOCS', 2), \
                patch.object(ras, '_MIGRATION_MAX_TOTAL_BYTES', expected), \
                patch.object(ras, '_read_move_source_identity', wraps=read) as reads:
            edits, reports = ras._council_role_link_plan(self.root, [(old, new)], move_destinations=())
        self.assertEqual(len(edits), 1); self.assertEqual(reads.call_count, 2)
        self.assertEqual(sum(call.kwargs['max_bytes'] for call in reads.call_args_list), expected + min(len(source.read_bytes()), len(peer.read_bytes())))

    def test_failed_reads_charge_attempted_io_and_stop_before_more_work(self):
        old, new = PAIRS[0]; (self.root / old).write_bytes(b'# Local\n')
        self.peer(b'one'); (self.root / 'docs/second.md').write_bytes(b'two')
        consumed = []
        def failed_after_read(root, rel, *, max_bytes):
            consumed.append(max_bytes + 1)
            raise ras.contained_files.ContainedFileRefused(ras.contained_files.CAUSE_SIZE)
        with patch.object(ras, '_MIGRATION_MAX_TOTAL_BYTES', 16), \
                patch.object(ras, '_read_move_source_identity', side_effect=failed_after_read):
            with self.assertRaisesRegex(RuntimeError, 'aggregate-byte'):
                ras._council_role_link_plan(self.root, [(old, new)], move_destinations=())
        self.assertEqual(consumed, [17], 'one crossing sentinel refuses; later files are not read')
        self.assertTrue((self.root / old).exists()); self.assertFalse((self.root / new).exists())

    def test_late_file_growth_cannot_be_an_unaccounted_skip(self):
        old, new = PAIRS[0]; (self.root / old).write_bytes(b'# Local\n')
        peer = self.peer(b'one')
        read = ras._read_move_source_identity
        def grows(root, rel, **kwargs):
            if rel == 'docs/consumer.md': peer.write_bytes(b'x' * 40)
            return read(root, rel, **kwargs)
        with patch.object(ras, '_MIGRATION_MAX_TOTAL_BYTES', 16), \
                patch.object(ras, '_read_move_source_identity', side_effect=grows):
            with self.assertRaisesRegex(RuntimeError, 'aggregate-byte'):
                ras._council_role_link_plan(self.root, [(old, new)], move_destinations=())
        self.assertEqual(peer.read_bytes(), b'x' * 40); self.assertTrue((self.root / old).exists())

    def test_unrelated_target_with_copied_region_is_not_a_registered_carrier(self):
        registered = PAIRS[1][1]
        unrelated = 'docs/other.md'
        text = (review_policy.REVIEW_POLICY_SURFACE_MARKER_BEGIN + '\n' +
                review_policy.REVIEW_POLICY_SURFACE_BLOCKS[registered] + '\n' + review_policy.REVIEW_POLICY_SURFACE_MARKER_END)
        (self.root / unrelated).write_text(text)
        peer = self.peer(b'[old](contributing/feature-wave-lifecycle-overview.md)\n')
        with patch.object(ras, 'LIFECYCLE_DOCUMENT_RENAMES', ((PAIRS[1][0], unrelated),)):
            result = ras.migrate_lifecycle_document_renames(self.root)
        self.assertIn(b'feature-wave-lifecycle-overview.md', peer.read_bytes())
        self.assertTrue(any('unconfirmed' in line for line in result.link_report))


if __name__ == '__main__':
    unittest.main()

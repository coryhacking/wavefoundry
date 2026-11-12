"""Statistics observations do not change scan or index scope."""
from __future__ import annotations

import contextlib
from datetime import datetime, timezone
import errno
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import indexer
import record_paths
import vocabulary_profile as vp
import scanner_skips
import scan_secrets
import run_secrets_scan
from wave_lint_lib import secrets_validators as scanner
from wave_lint_lib import cli
from wave_lint_lib import betterleaks_worker


class WalkerObservationTests(unittest.TestCase):
    def test_real_walk_observes_bounded_exclusions_without_entering_evidence(self):
        for waves_root in (record_paths.WAVES_ROOT, 'records/live'):
            with self.subTest(waves_root=waves_root), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                wave = root / waves_root / 'abc scope'
                (wave / 'evidence').mkdir(parents=True)
                (wave / vp.RECORD_FILENAME).write_text('# Wave\n')
                (wave / 'evidence' / 'hidden.py').write_text('x = 1\n')
                (root / 'keep.py').write_text('x = 1\n')
                (root / 'binary.bin').write_bytes(b'\0blob')
                (root / 'ignored').mkdir()
                (root / 'ignored' / 'hidden.py').write_text('x = 2\n')
                (root / '.gitignore').write_text('ignored/\n')
                for i in range(13):
                    (root / f'large{i:02}.json').write_text(' ' * 101)
                observed = {}
                real_walk = os.walk
                visited = []
                def tracked_walk(*a, **kw):
                    for row in real_walk(*a, **kw):
                        visited.append(Path(row[0]))
                        yield row
                with patch.multiple(record_paths, WAVES_ROOT=waves_root), patch.object(
                        indexer, '_resolve_max_file_bytes', return_value=100), patch.object(
                        indexer.os, 'walk', tracked_walk), contextlib.redirect_stderr(io.StringIO()):
                    plain = indexer.walk_repo(root)
                    actual = indexer.walk_repo(root, observations=observed)
                self.assertEqual(actual, plain)
                self.assertIn(root / 'keep.py', actual)
                self.assertNotIn(wave / 'evidence', visited)
                self.assertNotIn(root / 'ignored', visited)
                self.assertEqual(observed['evidence_excluded_directories'], {
                    'count': 1, 'paths': [f'{waves_root}/abc scope/evidence'], 'omitted': 0, 'unit': 'directories'})
                self.assertEqual(observed['oversized_files']['count'], 13)
                self.assertEqual(observed['oversized_files']['paths'], [f'large{i:02}.json' for i in range(10)])
                self.assertEqual(observed['oversized_files']['omitted'], 3)
                self.assertEqual(observed['binary_files']['count'], 1)
                self.assertEqual(observed['policy_excluded_directories']['paths'], ['ignored'])

    def test_denied_file_and_directory_are_not_policy_exclusions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            denied = root / 'denied.py'
            denied.write_text('x=1')
            actual_stat = indexer.os.stat
            def stat(path, *args, **kwargs):
                if Path(path) == denied:
                    raise PermissionError(errno.EACCES, 'denied', str(path))
                return actual_stat(path, *args, **kwargs)
            original_walk = os.walk
            def walk(*args, **kwargs):
                kwargs['onerror'](PermissionError(errno.EACCES, 'denied', str(root / 'private')))
                yield from original_walk(*args, **kwargs)
            observations, directories, files = {}, set(), set()
            with patch.object(indexer.os, 'stat', stat), patch.object(indexer.os, 'walk', walk), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(indexer.walk_repo(root, unreadable_dirs=directories,
                    unreadable_files=files, observations=observations), [])
            self.assertEqual(directories, {'private'})
            self.assertEqual(files, {'denied.py'})
            self.assertEqual(observations['unreadable_files']['paths'], ['denied.py'])
            self.assertEqual(observations['unreadable_directories']['unit'], 'directories')


class ScanHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(betterleaks_worker.close_worker)
        self.root = Path(self.tmp.name)
        self.rules = self.root / scanner.SCAN_RULES_FRAMEWORK_PATH
        self.rules.parent.mkdir(parents=True)
        self.rules.write_text('[[rules]]\nid="synthetic"\nregex="FIXTURE_MARKER"\n')
        self.file = self.root / 'sample.py'
        self.file.write_text('x = 1\n')

    def scan(self, **kwargs):
        with patch.object(scanner, 'get_scan_files', return_value=[self.file]), contextlib.redirect_stderr(io.StringIO()):
            return scanner.check_hardcoded_secrets(self.root, **kwargs)

    def test_full_then_incremental_then_no_work_preserves_distinct_times(self):
        first = datetime(2026, 1, 1, tzinfo=timezone.utc)
        second = datetime(2026, 1, 2, tzinfo=timezone.utc)
        self.assertEqual(self.scan(scan_all=True, as_of=first), [])
        self.assertEqual(self.scan(files=[self.file], as_of=second), [])
        history = scanner_skips.scan_history(self.root)
        self.assertTrue(history['available'])
        self.assertTrue(history['machine_local'])
        self.assertEqual(history['last_full']['scanned_at'], first.isoformat())
        self.assertEqual(history['latest_run']['scanned_at'], second.isoformat())
        self.assertEqual(history['latest_run']['scope'], 'incremental')
        before = scanner_skips._scan_history_path(self.root).read_bytes()
        self.assertEqual(self.scan(files=[]), [])
        self.assertEqual(self.scan(files=[self.file], publish=False), [])
        self.assertEqual(scanner_skips._scan_history_path(self.root).read_bytes(), before)
        self.assertNotIn('rules_hash', json.dumps(history))
        self.assertNotIn('sample.py', json.dumps(history))
        self.rules.write_text(self.rules.read_text() + '\n# changed rules\n')
        self.assertFalse(scanner_skips.scan_history(self.root)['latest_run']['rules_current'])

    def test_history_uses_the_retained_scanner_identity(self):
        from types import SimpleNamespace
        retained = SimpleNamespace(SCANNER_VERSION="17", _compute_rules_hash=lambda root: "a" * 64)
        with patch.object(indexer, "_secrets_scanner_mod", retained):
            scanner_skips.publish_scan_history(self.root, scope="full", requested_files=1,
                                              complete=True, scanned_at="2026-01-01T00:00:00+00:00")
            history = scanner_skips.scan_history(self.root)
        self.assertEqual(history["latest_run"]["scanner_version"], "17")
        self.assertTrue(history["latest_run"]["rules_current"])

    def test_missing_scanner_runtime_refuses_observation(self):
        with patch.object(indexer, "_get_secrets_scanner", return_value=None):
            self.assertEqual(self.scan(scan_all=True), ["[scan-incomplete] Scanner identity unavailable."])
            with self.assertRaisesRegex(ValueError, "scanner identity unavailable"):
                scanner_skips.publish_scan_history(self.root, scope="full", requested_files=1,
                                                  complete=True, scanned_at="2026-01-01T00:00:00+00:00")
        self.assertFalse(scanner_skips._scan_history_path(self.root).exists())

    def test_read_only_scan_creates_no_history_lock_or_any_other_file(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(self.scan(scan_all=True, publish=False), [])
        self.assertEqual(before, {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})
        self.assertFalse(scanner_skips.scan_history(self.root)["available"])

    def test_incomplete_full_replaces_prior_complete_full(self):
        self.assertEqual(self.scan(scan_all=True), [])
        with patch.object(scanner, 'MAX_FILE_BYTES', 1):
            failures = self.scan(scan_all=True)
        self.assertTrue(any('[scan-incomplete]' in x for x in failures))
        self.assertFalse(scanner_skips.scan_history(self.root)['last_full']['complete'])

    def test_history_missing_malformed_and_atomic_failure(self):
        self.assertEqual(scanner_skips.scan_history(self.root)['reason'], 'scan_history_missing')
        self.scan(scan_all=True)
        path = scanner_skips._scan_history_path(self.root)
        before = path.read_bytes()
        with patch.object(scanner_skips.os, 'replace', side_effect=OSError('PRIVATE_ERROR')):
            failures = self.scan()
        self.assertTrue(any('run history could not be persisted' in f for f in failures))
        self.assertNotIn('PRIVATE_ERROR', str(failures))
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue(scanner_skips.scan_history(self.root)['available'])
        path.write_text('{}')
        self.assertEqual(scanner_skips.scan_history(self.root)['reason'], 'scan_history_unreadable_or_invalid')
        self.assertTrue(any('run history could not be persisted' in f for f in self.scan()))
        self.assertEqual(path.read_text(), '{}')

    def test_history_reader_rejects_invalid_metadata_and_bounds_input(self):
        self.scan(scan_all=True)
        path = scanner_skips._scan_history_path(self.root)
        original = json.loads(path.read_text())
        for key, value in (("scope", "other"), ("complete", "yes"), ("requested_files", -1),
                           ("scanner_version", "PRIVATE"), ("rules_hash", "PRIVATE"),
                           ("scanned_at", "PRIVATE")):
            with self.subTest(key=key):
                state = json.loads(json.dumps(original))
                state["latest_run"][key] = value
                path.write_text(json.dumps(state))
                result = scanner_skips.scan_history(self.root)
                self.assertFalse(result["available"])
                self.assertNotIn("PRIVATE", json.dumps(result))
        for raw in ('[' * 2000, ' ' * 65537):
            path.write_text(raw)
            self.assertFalse(scanner_skips.scan_history(self.root)["available"])

    def test_per_edit_docs_lint_calls_owner_only_executed_scan_updates_latest(self):
        self.scan(scan_all=True, as_of=datetime(2026, 1, 1, tzinfo=timezone.utc))
        full = scanner_skips.scan_history(self.root)['last_full']
        with patch.object(cli, '_get_changed_files', return_value=[self.file]), patch.object(
                scanner, 'get_scan_files', return_value=[self.file]), contextlib.redirect_stderr(io.StringIO()):
            cli._run_incremental_checks(self.root)
        history = scanner_skips.scan_history(self.root)
        self.assertEqual(history['last_full'], full)
        self.assertEqual(history['latest_run']['scope'], 'incremental')
        before = scanner_skips._scan_history_path(self.root).read_bytes()
        with patch.object(cli, '_get_changed_files', return_value=[]), patch.object(
                scanner, 'get_scan_files', return_value=[]), contextlib.redirect_stderr(io.StringIO()):
            cli._run_incremental_checks(self.root)
        self.assertEqual(scanner_skips._scan_history_path(self.root).read_bytes(), before)

    def test_cli_full_and_indexer_incremental_share_history_owner(self):
        with patch.object(scanner, 'get_scan_files', return_value=[self.file]), patch.object(
                scan_secrets, '_load_state_store', return_value=None), patch.object(
                run_secrets_scan, '_auto_max_workers', return_value=1), patch.object(
                sys, 'argv', ['scan', '--root', str(self.root), '--mode', 'full']), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run_secrets_scan.main(), 0)
        self.assertEqual(scanner_skips.scan_history(self.root)['last_full']['scope'], 'full')
        # Establish adapter state; the real owner still controls history publication.
        scan_dir = self.root / '.wavefoundry/index/scan'
        scan_secrets._save_scan_state(scan_dir, {'rules_hash': scan_secrets._compute_rules_hash(self.root),
                                               'scanner_version': scan_secrets.SCANNER_VERSION})
        (self.root / 'docs').mkdir(exist_ok=True)
        (self.root / 'docs/scan-findings.json').write_text('[]')
        with patch.object(scan_secrets, '_load_state_store', return_value=None), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            result = scan_secrets.update_secrets_scan(root=self.root, scan_dir=scan_dir,
                changed={'sample.py'}, removed=set())
        self.assertTrue(result['complete'])
        self.assertEqual(scanner_skips.scan_history(self.root)['latest_run']['scope'], 'incremental')
        before = scanner_skips._scan_history_path(self.root).read_bytes()
        with patch.object(scan_secrets, '_load_state_store', return_value=None), contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(scan_secrets.update_secrets_scan(root=self.root, scan_dir=scan_dir,
                changed=set(), removed=set())['up_to_date'])
        self.assertEqual(scanner_skips._scan_history_path(self.root).read_bytes(), before)


if __name__ == '__main__':
    unittest.main()

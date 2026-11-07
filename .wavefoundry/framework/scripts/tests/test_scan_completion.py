"""Scanner coverage must survive adapters, caching, and later incremental work."""
from __future__ import annotations
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_secrets_scan
import scan_secrets
import scanner_skips
from wave_lint_lib import secrets_validators as scanner
from wave_lint_lib import betterleaks_worker as worker
from wave_lint_lib import betterleaks_engine as engine


class ScanCompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(worker.close_worker)
        self.root = Path(self.tmp.name)
        self.rules = self.root / scanner.SCAN_RULES_FRAMEWORK_PATH
        self.rules.parent.mkdir(parents=True)
        self.rules.write_text('[[rules]]\nid="synthetic"\nregex="SYNTHETIC_TOKEN"\n')
        self.file = self.root / 'candidate.txt'
        self.file.write_text('ordinary content\n')

    def scan(self, files=None, **kwargs):
        with contextlib.redirect_stderr(io.StringIO()):
            return scanner.check_hardcoded_secrets(self.root, files=[self.file] if files is None else files, **kwargs)

    def upstream(self):
        self.rules.write_text('wavefoundryProfile="betterleaks-v2-8f376ff9"\n[[rules]]\nid="synthetic"\nregex="SYNTHETIC_TOKEN"\n')

    def test_warm_cache_failure_retries_unchanged_content_in_both_producers(self):
        import index_state_store as store
        for route in ('cli', 'index'):
            for resolution in ('retry', 'legacy_cache', 'positive', 'binary', 'exclude', 'remove'):
                with self.subTest(route=route, resolution=resolution), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    rules = root / scanner.SCAN_RULES_FRAMEWORK_PATH
                    rules.parent.mkdir(parents=True)
                    rules.write_text('[[rules]]\nid="synthetic"\nregex="SYNTHETIC_TOKEN"\n')
                    candidate = root / 'candidate.txt'
                    candidate.write_text('SYNTHETIC_TOKEN' if resolution == 'positive' else 'ordinary content')
                    index_dir = root / '.wavefoundry/index'
                    def run(full=False):
                        output = io.StringIO()
                        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                            if route == 'cli':
                                with patch.object(sys, 'argv', ['scan', '--root', str(root), '--mode', 'full' if full else 'incremental']):
                                    code = run_secrets_scan.main()
                                result = json.loads(output.getvalue().splitlines()[-1])
                                self.assertEqual(code, 0 if result['complete'] else 2)
                                return result
                            return scan_secrets.update_secrets_scan(root=root, scan_dir=index_dir/'scan',
                                changed=set(), removed=set(), full=full)
                    with patch.object(scanner, 'get_scan_files', return_value=[candidate]), patch.object(
                            scan_secrets, '_load_state_store', return_value=store), patch.object(
                            scan_secrets, '_auto_max_workers', return_value=1):
                        self.assertTrue(run(full=True)['complete'])
                        fingerprint = scan_secrets._compute_rules_hash(root)
                        pending, skipped, _ = store.secret_scan_filter(index_dir, root, ['candidate.txt'], fingerprint)
                        self.assertEqual((pending, skipped), ([], 1))
                        with patch.object(scanner, 'MAX_FILE_BYTES', 3):
                            self.assertFalse(run(full=True)['complete'])
                        # The existing cache row must be evicted, not merely omitted
                        # from the latest batch of successful cache writes.
                        pending, skipped, _ = store.secret_scan_filter(index_dir, root, ['candidate.txt'], fingerprint)
                        self.assertEqual((pending, skipped), (['candidate.txt'], 0))
                        if resolution == 'legacy_cache':
                            store.secret_scan_record(index_dir, root, scanned_rel_paths=['candidate.txt'],
                                rules_fingerprint=fingerprint, findings_by_file={})
                        elif resolution == 'binary':
                            candidate.write_bytes(b'\0binary')
                        elif resolution == 'exclude':
                            rules.write_text('[allowlist]\npaths=["candidate.txt"]\n[[rules]]\nid="synthetic"\nregex="SYNTHETIC_TOKEN"\n')
                        elif resolution == 'remove':
                            candidate.unlink()
                        with patch.object(scanner, 'scan_file_raw', wraps=scanner.scan_file_raw) as raw:
                            result = run()
                        self.assertTrue(result['complete'], result)
                        if resolution in ('retry', 'legacy_cache', 'positive'):
                            self.assertGreater(raw.call_count, 0)
                            self.assertEqual(result['files_skipped'], 0)
                        if resolution == 'positive':
                            findings = json.loads((root/'docs/scan-findings.json').read_text())
                            self.assertTrue(any(row['file'] == 'candidate.txt' for row in findings))
                        self.assertEqual(scanner_skips.incomplete_paths(root), set())
                        if resolution == 'binary':
                            self.assertEqual(result['policy_excluded_files'], 1)

    def test_eligible_size_failure_persists_through_unrelated_run_and_complete_retry(self):
        with patch.object(scanner, 'MAX_FILE_BYTES', 3):
            failures = self.scan()
        self.assertTrue(any('[scan-incomplete]' in x for x in failures))
        self.assertEqual(scanner.unpublished_scanner_skips(), ['candidate.txt'])
        self.assertFalse(scanner_skips.scanner_completion(self.root)['complete'])
        self.assertTrue(self.scan(files=[]))
        self.assertEqual(self.scan(), [])
        self.assertTrue(scanner_skips.scanner_completion(self.root)['complete'])

    def test_record_only_does_not_hide_incomplete_work(self):
        with patch.object(scanner, 'MAX_FILE_BYTES', 3):
            self.assertTrue(self.scan(record_only=True))

    def test_policy_exclusion_and_confirmed_removal_resolve_prior_failure(self):
        for resolution in ('allowlist', 'remove', 'runtime'):
            with self.subTest(resolution=resolution):
                self.file.write_text('ordinary content')
                with patch.object(scanner, 'MAX_FILE_BYTES', 3):
                    self.scan()
                self.assertFalse(scanner_skips.scanner_completion(self.root)['complete'])
                self.rules.write_text('[[rules]]\nid="synthetic"\nregex="SYNTHETIC_TOKEN"\n')
                if resolution == 'allowlist':
                    self.rules.write_text('[allowlist]\npaths=["candidate.txt"]\n[[rules]]\nid="synthetic"\nregex="SYNTHETIC_TOKEN"\n')
                    self.assertEqual(self.scan(files=[]), [])
                elif resolution == 'remove':
                    self.file.unlink()
                    self.assertEqual(self.scan(files=[]), [])
                else:
                    with patch.object(scanner, 'is_scanner_excluded_path', return_value=True):
                        self.assertEqual(self.scan(files=[]), [])
                self.assertTrue(scanner_skips.scanner_completion(self.root)['complete'])
                self.rules.write_text('[[rules]]\nid="synthetic"\nregex="SYNTHETIC_TOKEN"\n')

    def test_binary_policy_omissions_are_visible_but_not_failures(self):
        self.file.write_bytes(b'\0binary content')
        self.assertEqual(self.scan(), [])
        coverage = scanner_skips.scanner_completion(self.root)
        self.assertTrue(coverage['complete'])
        self.assertEqual(coverage['policy_excluded_files'], 1)

    def test_unreadable_input_and_malformed_history_cannot_appear_clean(self):
        original = Path.open
        def denied(path, *args, **kwargs):
            if path == self.file:
                raise PermissionError('sensitive text not reported')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', denied):
            self.assertTrue(self.scan())
        self.assertEqual(scanner_skips.scanner_completion(self.root)['incomplete'][0]['detail'], 'read_failed')
        ledger = self.root / scanner_skips.LEDGER_REL
        ledger.write_text('{')
        self.assertTrue(self.scan(files=[]))
        coverage = scanner_skips.scanner_completion(self.root)
        self.assertFalse(coverage['complete'])
        self.assertIn('coverage_error', coverage)

    def test_full_fragment_keeps_long_line_tail_under_real_worker_bounds(self):
        self.upstream()
        self.file.write_text('x' * (scanner.MAX_LINE_BYTES + 5) + ' SYNTHETIC_TOKEN')
        failures = self.scan()
        self.assertTrue(any('[secrets]' in item for item in failures), failures)
        self.assertTrue(scanner_skips.scanner_completion(self.root, failures)['complete'])
        self.assertNotIn('candidate.txt', scanner.unpublished_scanner_skips())

    def test_worker_timeout_and_incomplete_result_preserve_existing_finding(self):
        self.upstream()
        self.file.write_text('SYNTHETIC_TOKEN')
        self.scan()
        ledger = self.root / scanner.SCAN_FINDINGS_PATH
        original = ledger.read_bytes()
        actual = worker.worker_request
        for behavior in ('timeout', 'incomplete'):
            def failed(operation, payload):
                if operation == 'scan':
                    if behavior == 'timeout':
                        raise worker.WorkerError('worker_timeout')
                    result = actual(operation, payload)
                    result['complete'] = False
                    return result
                return actual(operation, payload)
            with self.subTest(behavior=behavior), patch.object(worker, 'worker_request', side_effect=failed):
                failures = self.scan(scan_all=True)
            self.assertTrue(any('[scan-incomplete]' in item for item in failures))
            self.assertEqual(ledger.read_bytes(), original)
            self.assertFalse(scanner_skips.scanner_completion(self.root)['complete'])
            self.assertIn('candidate.txt', scanner.unpublished_scanner_skips())

    def test_engine_byte_line_and_match_caps_propagate_through_real_adapter(self):
        self.upstream()
        self.file.write_text('SYNTHETIC_TOKEN\nSYNTHETIC_TOKEN\n')
        actual = worker.worker_request
        for bound, value in (('MAX_CONTENT_BYTES', 2), ('MAX_LINES', 1), ('MAX_MATCHES', 1)):
            def limited(operation, payload):
                if operation != 'scan':
                    return actual(operation, payload)
                with patch.object(engine, bound, value):
                    return engine.BetterleaksEngine(payload['config']).scan(payload['content'], payload['path'])
            with self.subTest(bound=bound), patch.object(worker, 'worker_request', side_effect=limited):
                failures = self.scan()
            self.assertTrue(any('[scan-incomplete]' in item for item in failures), (bound, failures))
            self.assertFalse(scanner_skips.scanner_completion(self.root)['complete'])

    def test_both_cache_producers_exclude_incomplete_files_and_cli_exits_two(self):
        store = Mock()
        store.secret_scan_filter.side_effect = lambda _index, _root, paths, _hash: (paths, 0, {})
        for route in ('cli', 'index'):
            store.reset_mock()
            with self.subTest(route=route), patch.object(scanner, 'MAX_FILE_BYTES', 3), patch.object(scan_secrets, '_load_state_store', return_value=store), patch.object(scanner, 'get_scan_files', return_value=[self.file]), contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
                if route == 'cli':
                    with patch.object(sys, 'argv', ['scan', '--root', str(self.root), '--mode', 'full']):
                        self.assertEqual(run_secrets_scan.main(), 2)
                    self.assertFalse(json.loads(out.getvalue().splitlines()[-1])['complete'])
                else:
                    result = scan_secrets.update_secrets_scan(root=self.root, scan_dir=self.root/'.wavefoundry/index/scan', changed={'candidate.txt'}, removed=set(), full=True)
                    self.assertFalse(result['complete'])
            for call in store.secret_scan_record.call_args_list:
                self.assertNotIn('candidate.txt', call.kwargs['scanned_rel_paths'])

    def test_idle_incremental_result_does_not_hide_outstanding_failure(self):
        with patch.object(scanner, 'MAX_FILE_BYTES', 3):
            self.scan()
        state = {'rules_hash': scan_secrets._compute_rules_hash(self.root), 'scanner_version':scan_secrets.SCANNER_VERSION}
        (self.root / scanner.SCAN_FINDINGS_PATH).parent.mkdir(parents=True, exist_ok=True)
        (self.root / scanner.SCAN_FINDINGS_PATH).write_text('[]')
        with patch.object(scan_secrets, '_load_scan_state', return_value=state), patch.object(scan_secrets, '_load_state_store', return_value=None), patch.object(scanner, 'MAX_FILE_BYTES', 3):
            result=scan_secrets.update_secrets_scan(root=self.root, scan_dir=self.root/'.wavefoundry/index/scan',changed=set(),removed=set())
        self.assertFalse(result['complete'])
        self.assertFalse(result['up_to_date'])
        self.assertGreater(result['failures'], 0)

    def test_completion_rows_are_bounded_without_losing_count(self):
        rows={}
        for n in range(55):
            name=f'file-{n}.txt';(self.root/name).write_text('ordinary')
            rows[name]={'complete':False,'skips':[{'file':name,'reason':'file too large','detail':'bound'}]}
        scanner_skips.update_scanner_skips(self.root, rows)
        result=scanner_skips.scanner_completion(self.root)
        self.assertEqual(result['incomplete_files'],55)
        self.assertEqual(len(result['incomplete']),50)
        self.assertEqual(result['incomplete_omitted'],5)

if __name__ == '__main__':
    unittest.main()

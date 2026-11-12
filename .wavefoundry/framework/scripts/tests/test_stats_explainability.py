"""Explainable report contracts through the shared public collector."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_project_stats import write, wave, change, tree_bytes
import project_stats as stats
import record_paths
import context_efficiency as ce
import dashboard_lib
import vocabulary_profile as vp


class ExplainableStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_human_cli_keeps_bounded_skipped_paths_and_omitted_count(self):
        import wf_cli
        write(self.root, 'keep.py', 'x = 1\n')
        for n in range(12):
            path = self.root / f'benchmark-{n:02}.json'
            with path.open('wb') as handle:
                handle.truncate(5_000_001)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(wf_cli.main(['stats', '--root', str(self.root), '--section', 'code']), 0)
        rendered = out.getvalue()
        for n in range(10):
            self.assertIn(f'- benchmark-{n:02}.json', rendered)
        self.assertNotIn('benchmark-10.json', rendered)
        self.assertNotIn('benchmark-11.json', rendered)
        self.assertIn('Count: 12', rendered)
        self.assertIn('Omitted: 2', rendered)

    def test_checkpoint_details_opt_in_reconcile_and_never_change_default(self):
        for n, status in enumerate(('healthy', 'healthy', 'accounting_gap')):
            path = wave(self.root, f'234a{n} token')
            checkpoint = ce.empty_checkpoint()
            checkpoint['measurement_status'] = status
            checkpoint['pending'] = n == 1
            totals = dict(checkpoint['totals'])
            totals.update(content_source_credit=100 * (n + 1), workflow_prompt_credit=10,
                          derived_artifact_credit=5, request_debit=3, response_debit=7,
                          estimated_tokens_saved=100 * (n + 1) + 5, calls=1)
            checkpoint['stages'] = {'plan': totals}
            path.write_text(path.read_text() + '\n' + ce.render_checkpoint_block(checkpoint))
        wave(self.root, '234a3 missing')
        before = tree_bytes(self.root)
        default = stats.collect_project_stats(self.root, ['token_savings'])
        detailed = stats.collect_project_stats(self.root, ['token_savings'], include_wave_details=True)
        aggregate = default['sections']['token_savings']
        detail = detailed['sections']['token_savings']
        self.assertNotIn('wave_details', aggregate)
        self.assertEqual(len(detail['wave_details']), 4)
        self.assertEqual(detail['estimated_totals'], aggregate['estimated_totals'])
        healthy = [row for row in detail['wave_details'] if row['included']]
        self.assertEqual(len(healthy), 2)
        for key, value in detail['estimated_totals'].items():
            self.assertEqual(value, sum(row['estimated_totals'][key] for row in healthy), key)
        self.assertTrue(healthy[1]['pending'])
        self.assertEqual(detail['wave_details'][-1]['measurement_status'], 'missing')
        rendered = stats.format_report(default)
        self.assertIn('Estimated tokens saved: 310. No paired evaluations recorded', rendered)
        self.assertIn('not total model consumption', rendered)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(stats.main(['--root', str(self.root), '--section', 'token_savings', '--include-wave-details', '--json']), 0)
        self.assertEqual(json.loads(out.getvalue()), detailed)
        self.assertEqual(before, tree_bytes(self.root))

    def test_hundreds_of_healthy_checkpoints_have_no_default_detail_rows(self):
        state = ce.empty_checkpoint()
        state['measurement_status'] = 'healthy'
        rows = [{'wave_id': f'{n:05d}', 'path': f'{record_paths.WAVES_ROOT}/{n}/{vp.RECORD_FILENAME}'} for n in range(350)]
        with patch.object(Path, 'read_text', return_value='fixture'), patch.object(ce, 'parse_checkpoint_block', return_value=state):
            output = stats._token_savings(self.root, rows)
        self.assertEqual(output['records_with_marker'], 350)
        self.assertNotIn('wave_details', output)
        self.assertEqual(output['excluded_records'], [])
        with patch.object(stats, '_token_savings', side_effect=AssertionError('unrequested checkpoint read')):
            self.assertEqual(stats.collect_project_stats(self.root, [], include_wave_details=True)['sections'], {})
        for invalid in ('true', 1, None, []):
            with self.assertRaises(ValueError):
                stats.collect_project_stats(self.root, [], include_wave_details=invalid)

    def test_active_and_paused_rows_use_admitted_identity_and_literal_marks(self):
        for ident, status in (('234aa active', 'implementing'), ('234ab parked', 'paused')):
            name = ident[:5] + '-enh member'
            wave(self.root, ident, status, [name, ident[:5] + '-bug missing'])
            path = change(self.root, name, ident, '\n## Acceptance Criteria\n\n- [ ] AC-1: open\n\n## Tasks\n\n- [~] intentionally deferred\n')
            path.write_text(path.read_text().replace(f'{vp.BACKREF_LABEL}: `{ident}`', f'{vp.BACKREF_LABEL}: `stale`').replace('`planned`', '`completed`'))
        value = stats.collect_project_stats(self.root, ['lifecycle'])['sections']['lifecycle']
        self.assertEqual(len(value['open_work_by_wave']), 2)
        for row in value['open_work_by_wave']:
            self.assertEqual(row['criteria']['open'], 1)
            self.assertEqual(row['criteria']['done'], 0)
            self.assertEqual(row['tasks']['deferred'], 1)
            self.assertEqual(row['coverage']['missing_admitted_documents'], 1)
        with patch.object(vp, 'CONTAINER_NAME_PLURAL', 'Sets'), patch.object(vp, 'ITEM_NAME_PLURAL', 'Works'):
            named = stats._lifecycle([], {'wave': [], 'plan': []})['completion_rule']
        self.assertIn('Sets count as done', named)
        self.assertNotIn('wave', named.lower())
        for status in dashboard_lib._lint_constants().DONE_CHANGE_STATUSES:
            self.assertIn(status, value['completion_rule'])

    def test_all_memory_states_are_present_and_proposals_are_not_records(self):
        import memory_records
        for n, status in enumerate(('active', 'candidate', 'rejected', 'stale')):
            body = memory_records.render_memory_record(memory_id=f'234a{n}-mem sample', kind='failed_attempt', summary='Fixture lesson', evidence=['fixture'], targets=['a.py'], status=status, date='2026-01-01')
            write(self.root, f'docs/agents/memory/234a{n}-mem sample.md', body)
        memory_records.archive_memory_record(self.root, '234a3-mem sample', reason='fixture')
        write(self.root, '.wavefoundry/index/proposals.json', '{"candidates":27}')
        value = stats.collect_project_stats(self.root, ['memories'])['sections']['memories']
        self.assertEqual(value['by_status'], {'active': 1, 'candidate': 1, 'rejected': 1, 'archived': 1})
        self.assertEqual(value['candidate_records_awaiting_validation'], 1)
        text = stats.format_report({'sections': {'memories': value}})
        for status in ('Active', 'Candidate', 'Rejected', 'Archived'):
            self.assertIn(status, text)
        self.assertIn('malformed/unreadable', text)

    def test_health_survives_invalid_findings_without_exposing_details(self):
        import scanner_skips
        write(self.root, 'docs/scan-findings.json', 'PRIVATE_FINDING')
        write(self.root, 'docs/scan-rules.toml', '[allowlist]\npaths = ["a", "b"]\n')
        history = {'available': True, 'machine_local': True, 'latest_run': {'scope': 'incremental'}, 'last_full': {'scope': 'full'}}
        with patch.object(scanner_skips, 'scan_history', return_value=history):
            value = stats.collect_project_stats(self.root, ['secrets'])['sections']['secrets']
        self.assertFalse(value['available'])
        self.assertEqual(value['scan_health']['history'], history)
        self.assertEqual(value['scan_health']['project_allowlist']['path_entries'], 2)
        self.assertFalse(value['scan_health']['outstanding']['available'])
        self.assertNotIn('PRIVATE_FINDING', json.dumps(value))

    def test_project_allowlist_counts_global_and_rule_tables_not_values(self):
        write(self.root, 'docs/scan-rules.toml', '[allowlist]\npaths=["PRIVATE_A"]\n[[rules]]\nid="demo"\nregex="x"\n[[rules.allowlists]]\npaths=["PRIVATE_B","PRIVATE_C"]\n[[rules.allowlists]]\npaths=["PRIVATE_D"]\n')
        result = stats._scan_health(self.root)['project_allowlist']
        self.assertEqual(result['path_entries'], 4)
        self.assertNotIn('PRIVATE_', json.dumps(result))
        write(self.root, 'docs/scan-rules.toml', '[[allowlists]]\npaths=["unsupported"]\n')
        self.assertFalse(stats._scan_health(self.root)['project_allowlist']['available'])

    def test_real_walk_reports_bounded_size_and_evidence_directory_exclusions(self):
        write(self.root, 'docs/workflow-config.json', '{"indexing":{"max_file_bytes":100}}')
        write(self.root, 'main.py', 'value = 1\n')
        for n in range(12):
            write(self.root, f'large{n:02}.json', 'x' * 101)
        wave(self.root, '234aa sample')
        write(self.root, f'{record_paths.WAVES_ROOT}/234aa sample/evidence/nested/result.json', '{}')
        code = stats.collect_project_stats(self.root, ['code'])['sections']['code']
        skipped = code['skip_reasons']['oversized_files']
        self.assertEqual(skipped['count'], 12)
        self.assertEqual(skipped['paths'], [f'large{n:02}.json' for n in range(10)])
        self.assertEqual(skipped['omitted'], 2)
        evidence = code['skip_reasons']['evidence_excluded_directories']
        self.assertEqual(evidence['count'], 1)
        self.assertEqual(evidence['unit'], 'directories')
        self.assertEqual(evidence['paths'], [f'{record_paths.WAVES_ROOT}/234aa sample/evidence'])
        self.assertNotIn('nested/result', json.dumps(code))


if __name__ == '__main__':
    unittest.main()

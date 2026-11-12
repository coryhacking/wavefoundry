"""Effective composition preserves legacy counts while qualifying syntax precision."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_project_stats import write, wave, tree_bytes
import project_stats as stats
import record_paths
import indexer


class StatisticsRolesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def roles(self, rows):
        write(self.root, 'docs/repo-profile.json', json.dumps({'statistics': {'path_roles': rows}}))

    def code(self, **kwargs):
        return stats.collect_project_stats(self.root, ['code'], **kwargs)['sections']['code']

    def test_roles_longest_literal_match_keep_categories_and_legacy(self):
        self.roles([{'path': 'src/', 'role': 'shipped'}, {'path': 'src/support/', 'role': 'tooling'},
                    {'path': 'checks/', 'role': 'test'}, {'path': 'results/', 'role': 'evidence'},
                    {'path': 'generated/', 'role': 'generated'}])
        write(self.root, 'src/main.swift', 'let x = 1\n')
        write(self.root, 'src/support/build.py', 'x = 1\n')
        write(self.root, 'checks/Nonstandard.swift', 'let x = 2\n')
        write(self.root, 'results/run.json', '{}\n')
        write(self.root, 'generated/data.json', '{}\n')
        write(self.root, 'misc.py', 'y = 2\n')
        value = self.code()
        self.assertTrue(value['available'], value)
        self.assertEqual(value['roles']['shipped']['both']['files'], 1)
        self.assertEqual(value['roles']['tooling']['both']['files'], 1)
        self.assertEqual(value['roles']['test']['both']['files'], 1)
        self.assertEqual(value['roles']['evidence']['both']['files'], 1)
        self.assertEqual(value['roles']['generated']['both']['files'], 1)
        self.assertEqual(value['languages']['swift']['test']['code_lines'], 0)
        self.assertEqual(value['languages']['swift']['effective_test']['code_lines'], 1)
        self.assertEqual(value['languages']['swift']['effective_non_test']['code_lines'], 1)
        self.assertEqual(value['languages']['json']['category'], 'data')
        self.assertEqual(value['roles']['test']['configured_files'], 1)
        self.assertEqual(value['roles']['non_test']['inferred_files'], 2)  # misc and profile
        self.assertEqual(sum(row['both']['files'] for row in value['roles'].values()), sum(row['both']['files'] for row in value['categories'].values()))
        rendered = stats.format_report({'sections': {'code': value}})
        self.assertIn('Non-test code lines', rendered)
        self.assertNotIn('| Production', rendered)
        self.assertIn('not packaged binaries', rendered)

    def test_invalid_roles_are_isolated_from_other_sections(self):
        invalid = [[{'path': '/tmp/private', 'role': 'shipped'}], [{'path': '../escape/', 'role': 'test'}],
                   [{'path': 'C:\\private', 'role': 'test'}], [{'path': 'x/', 'role': []}],
                   [{'path': 'src/', 'role': 'shipped'}, {'path': 'src/', 'role': 'test'}],
                   [{'path': '.', 'role': 'test'}], [{'path': 'x', 'role': 'other'}]]
        write(self.root, 'main.py', 'x\n')
        for rows in invalid:
            with self.subTest(rows=rows):
                self.roles(rows)
                sections = stats.collect_project_stats(self.root, ['code', 'todo', 'memories'])['sections']
                self.assertEqual(sections['code'].get('reason'), 'statistics_configuration_invalid')
                self.assertTrue(sections['todo']['available'])
                self.assertTrue(sections['memories']['available'])
        self.roles([{'path': './src/', 'role': 'shipped'}, {'path': 'src/', 'role': 'shipped'}])
        self.assertEqual(stats._path_roles(self.root), [('src/', 'shipped')])

    def test_real_rust_spans_union_attributes_and_following_live_item(self):
        if indexer._get_graph_indexer()._ts_get_parser('rust') is None:
            self.skipTest('existing Rust parser unavailable')
        text = ('fn live() {}\n'
                '#[ cfg ( test ) ]\n'
                'mod tests {\n'
                '    #[test]\n'
                '    fn nested() {}\n'
                '}\n'
                'fn after() {}\n'
                '#[test]\n'
                'fn standalone() {}\n'
                'const TEXT: &str = "#[test] fn fake() {}";\n'
                '// #[cfg(test)]\n')
        write(self.root, 'src/lib.rs', text)
        self.roles([{'path': 'src/', 'role': 'shipped'}])
        value = self.code()
        rust = value['languages']['rust']
        self.assertEqual(rust['both']['code_lines'], 10)
        self.assertEqual(rust['production']['code_lines'], 10)
        self.assertEqual(rust['test']['code_lines'], 0)
        self.assertEqual(rust['effective_test']['code_lines'], 7)
        self.assertEqual(rust['effective_non_test']['code_lines'], 3)
        self.assertEqual(rust['effective_test']['files'], 1)
        self.assertEqual(rust['effective_non_test']['files'], 1)
        self.assertEqual(rust['both']['files'], 1)
        self.assertEqual(rust['mixed_test_files'], 1)
        self.assertEqual(value['roles']['shipped']['effective_test']['code_lines'], 7)
        self.assertEqual(value['inline_analysis']['status'], 'supported_syntax')
        self.assertIn('hidden test semantics', value['inline_analysis']['note'])
        write(self.root, 'tests/unit.rs', text)
        whole = self.code()['languages']['rust']
        self.assertEqual(whole['test']['code_lines'], 10)
        self.assertEqual(whole['effective_test']['code_lines'], 17)

    def test_partial_rust_falls_back_without_claiming_exact_zero_inline_tests(self):
        write(self.root, 'src/lib.rs', '#[cfg(any(test, feature="x"))]\nmod tests { fn test() {} }\n')
        value = self.code()
        self.assertEqual(value['inline_analysis']['status'], 'partial')
        self.assertEqual(value['inline_analysis']['fallback_files'][0]['reason'], 'unsupported_conditional')
        write(self.root, 'src/lib.rs', '#[cfg(test)]\nmod tests {\n')
        self.assertEqual(self.code()['inline_analysis']['fallback_files'][0]['reason'], 'parse_error')
        write(self.root, 'src/lib.rs', 'fn live() {}\n')
        with patch.object(indexer._get_graph_indexer(), '_ts_parse', return_value=None):
            value = self.code()
        self.assertEqual(value['inline_analysis']['status'], 'partial')
        self.assertIn('path-only fallback', value['inline_analysis']['note'])
        self.assertEqual(value['languages']['rust']['effective_non_test']['code_lines'], 1)

    def test_explicit_evidence_does_not_restore_pruned_contents(self):
        wave(self.root, '234aa sample')
        write(self.root, f'{record_paths.WAVES_ROOT}/234aa sample/evidence/result.json', '{}')
        write(self.root, 'results/evidence/run.json', '{}')
        write(self.root, 'other/evidence/run.json', '{}')
        self.roles([{'path': f'{record_paths.WAVES_ROOT}/234aa sample/evidence/', 'role': 'evidence'}, {'path': 'results/', 'role': 'evidence'}])
        value = self.code()
        self.assertEqual(value['roles']['evidence']['both']['files'], 1)
        self.assertEqual(value['skip_reasons']['evidence_excluded_directories']['count'], 1)
        self.assertEqual(value['roles']['evidence']['configured_files'], 1)
        self.assertNotIn('evidence', self.code()['languages'])

    def test_directory_reconciliation_one_pass_and_cli_parity(self):
        import indexer
        write(self.root, 'main.py', 'x\n')
        write(self.root, 'src/mod.py', 'a\nb\n')
        write(self.root, 'tests/test_a.py', 'x\n')
        before = tree_bytes(self.root)
        with patch.object(indexer, 'walk_repo', wraps=indexer.walk_repo) as walker:
            payload = stats.collect_project_stats(self.root, ['code', 'todo'], group_by='directory')
        self.assertEqual(walker.call_count, 1)
        value = payload['sections']['code']
        self.assertEqual([row['directory'] for row in value['directories']], ['.', 'src', 'tests'])
        self.assertEqual(sum(row['both']['files'] for row in value['directories']), value['categories']['code']['both']['files'])
        self.assertEqual(sum(row['effective_test']['code_lines'] for row in value['directories']), value['categories']['code']['effective_test']['code_lines'])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            stats.main(['--root', str(self.root), '--section', 'code', '--section', 'todo', '--group-by', 'directory', '--json'])
        self.assertEqual(json.loads(out.getvalue()), payload)
        self.assertEqual(before, tree_bytes(self.root))
        with patch.object(stats, '_files', side_effect=AssertionError('not requested')), patch.object(stats, '_path_roles', side_effect=AssertionError('not requested')):
            self.assertEqual(stats.collect_project_stats(self.root, [], group_by='directory')['sections'], {})
        self.assertNotIn('directories', self.code())
        for invalid in ('nested', '', 3, []):
            with self.assertRaises(ValueError):
                stats.collect_project_stats(self.root, [], group_by=invalid)


if __name__ == '__main__':
    unittest.main()

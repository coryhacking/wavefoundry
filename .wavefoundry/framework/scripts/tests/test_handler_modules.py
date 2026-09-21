"""Compatibility contracts for the nineteen extracted handler responses (1y0h2).

The roster below is the admitted public contract, not discovered from the
implementation. Existing golden/registry suites remain the surface authority.
"""
from __future__ import annotations

import ast
import builtins
import copy
import importlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import symtable
import sys
import tempfile
import unittest
from unittest.mock import patch

from server_tools_support import load_server

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parents[2]
FAMILIES = {
    'codenav_handlers': ('code_list_files', 'code_read', 'code_keyword', 'code_lexical',
        'code_constants', 'code_pattern', 'code_outline', 'code_definition',
        'code_references', 'code_dependencies', 'code_hover', 'code_commit_provenance'),
    'graph_handlers': ('code_impact', 'code_callgraph', 'code_callhierarchy',
        'code_graph_path', 'code_graph_community', 'code_risk_score', 'wf_graph_report'),
}


def _unresolved(source, module, server):
    """Use Python's scope analysis, including nested functions/comprehensions."""
    failures = set()
    def walk(table):
        for symbol in table.get_symbols():
            if symbol.is_referenced() and symbol.is_global():
                name = symbol.get_name()
                if name not in vars(module) and name not in vars(builtins):
                    failures.add(name)
        for child in table.get_children():
            walk(child)
    walk(symtable.symtable(source, '<handler-contract>', 'exec'))
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'server_impl':
            if not hasattr(server, node.attr):
                failures.add('server_impl.' + node.attr)
    return failures


class HandlerStructureTests(unittest.TestCase):
    def test_locations_import_boundaries_and_name_resolution(self):
        server = load_server()
        server_defs = {n.name for n in ast.parse((SCRIPTS / 'server_impl.py').read_text()).body
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for name, tools in FAMILIES.items():
            with self.subTest(module=name):
                module = importlib.import_module(name)
                source = (SCRIPTS / (name + '.py')).read_text()
                tree = ast.parse(source)
                local_defs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
                for tool in tools:
                    response = tool + '_response'
                    self.assertNotIn(response, server_defs)
                    self.assertIn(response, local_defs)
                    self.assertIs(getattr(server, response), getattr(module, response))
                imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
                imported = {alias.name.split('.')[0] for n in imports if isinstance(n, ast.Import) for alias in n.names}
                imported.update(n.module.split('.')[0] for n in imports if isinstance(n, ast.ImportFrom) and n.module)
                self.assertNotIn('server_impl', imported)
                self.assertFalse((set(FAMILIES) - {name}) & imported)
                self.assertEqual(_unresolved(source, module, server), set())
                bad = source + '\ndef _contract_mutant():\n    return never_defined_handler_global\n'
                self.assertIn('never_defined_handler_global', _unresolved(bad, module, server))
                self.assertIn('server_impl.never_defined_helper', _unresolved(
                    source + '\ndef _contract_mutant():\n    import server_impl\n    return server_impl.never_defined_helper()\n', module, server))


class HandlerResponseTests(unittest.TestCase):
    def setUp(self):
        self.server = load_server()
        self.nav = importlib.import_module('codenav_handlers')
        self.graph = importlib.import_module('graph_handlers')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        (self.root.parent / "outside.py").write_text("OUTSIDE_SENTINEL = 1\n")
        # A missing index may request repair; this fixture deliberately models
        # an offline/unavailable builder and never downloads models. Some
        # handlers do not reach repair (inert-by-design on those paths).
        repair = patch.object(self.server, 'index_build_response',
                              side_effect=RuntimeError('fixture builder unavailable'))
        self.repair = repair.start()
        self.addCleanup(repair.stop)
        (self.root / '.gitignore').write_text('git_hidden.py\n')
        (self.root / '.aiignore').write_text('ai_hidden.py\n')
        for name in ('visible.py', 'git_hidden.py', 'ai_hidden.py'):
            (self.root / name).write_text('ANSWER = 42\ndef public_symbol():\n    return ANSWER  # needle\n')

    def test_ignore_rules_and_late_bound_shared_walker(self):
        listed = self.nav.code_list_files_response(self.root)
        self.assertEqual(listed['status'], 'ok')
        self.assertIn('visible.py', listed['data']['paths'])
        for hidden in ('git_hidden.py', 'ai_hidden.py'):
            self.assertNotIn(hidden, listed['data']['paths'])
        found = self.nav.code_keyword_response(self.root, query='needle')
        self.assertEqual(found['status'], 'ok')
        self.assertEqual({row['path'] for row in found['data']['results']}, {'visible.py'})
        with patch.object(self.server, '_walk_repo_for_navigation', return_value=[]) as walker:
            empty = self.nav.code_list_files_response(self.root)
            walker.assert_called_once_with(self.root)
        self.assertEqual(empty['data']['paths'], [])

    def test_all_navigation_responses_without_transport(self):
        calls = {
            'code_list_files': {}, 'code_read': {'path': 'visible.py'},
            'code_keyword': {'query': 'needle'}, 'code_lexical': {'query': 'public_symbol'},
            'code_constants': {'symbols': ['ANSWER']}, 'code_pattern': {'pattern': 'public_symbol'},
            'code_outline': {'path': 'visible.py'}, 'code_definition': {'symbol_or_path_position': 'public_symbol'},
            'code_references': {'symbol_or_path_position': 'ANSWER'}, 'code_dependencies': {'path': 'visible.py'},
            'code_hover': {'path': 'visible.py', 'line': 2}, 'code_commit_provenance': {'path': 'visible.py'},
        }
        self.assertEqual(set(calls), set(FAMILIES['codenav_handlers']))
        for name, kwargs in calls.items():
            with self.subTest(tool=name):
                result = getattr(self.nav, name + '_response')(self.root, **kwargs)
                self.assertIn(result['status'], {'ok', 'error'})
                # No index and no Git repository are deliberate reachable boundaries.
                if name not in {'code_lexical', 'code_commit_provenance'}:
                    self.assertEqual(result['status'], 'ok', result)
                else:
                    self.assertTrue(result.get('diagnostics'), result)
        def assert_root_boundary():
            result = self.nav.code_read_response(self.root, '../outside.py')
            self.assertEqual(result['status'], 'error', result)
            self.assertNotIn('OUTSIDE_SENTINEL', str(result))
        assert_root_boundary()
        # A real sibling file makes bypass observable; a missing file would
        # return an unrelated error and let this mutation pass.
        with patch.object(self.server, '_resolve_repo_path',
                          side_effect=lambda root, path: (root / path).resolve()) as resolver:
            with self.assertRaises(AssertionError):
                assert_root_boundary()
            resolver.assert_called_once()

    def test_all_graph_responses_on_reachable_empty_index(self):
        calls = {
            'code_impact': {'path': 'visible.py'}, 'code_callgraph': {'symbol': 'public_symbol'},
            'code_callhierarchy': {'symbol': 'public_symbol'},
            'code_graph_path': {'from_symbol': 'public_symbol', 'to_symbol': 'ANSWER'},
            'code_graph_community': {}, 'code_risk_score': {}, 'wf_graph_report': {},
        }
        self.assertEqual(set(calls), set(FAMILIES['graph_handlers']))
        for name, kwargs in calls.items():
            with self.subTest(tool=name):
                result = getattr(self.graph, name + '_response')(self.root, **kwargs)
                self.assertIn(result['status'], {'ok', 'error'}, result)
                self.assertTrue(result.get('data') or result.get('diagnostics'), result)
                self.assertNotIn('NameError', str(result))


class HandlerPackagingAndEvaluatorTests(unittest.TestCase):
    def test_generated_manifest_contains_both_modules(self):
        import build_pack
        with tempfile.TemporaryDirectory() as temp:
            framework = Path(temp)
            (framework / 'scripts').mkdir()
            for name in FAMILIES:
                shutil.copy2(SCRIPTS / (name + '.py'), framework / 'scripts' / (name + '.py'))
            manifest = build_pack.write_manifest(framework, build_pack.collect_files(framework))
            entries = manifest.read_text().splitlines()
        for name in FAMILIES:
            self.assertIn('scripts/' + name + '.py', entries)

    def test_evaluator_real_server_attributes_and_missing_alias_control(self):
        import retrieval_eval
        server = load_server()
        tree = ast.parse(inspect.getsource(retrieval_eval))
        reads = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
                 and isinstance(n.value, ast.Name) and n.value.id == 'server'}
        def missing():
            return reads - set(vars(server))
        self.assertTrue({'code_outline_response', 'code_constants_response', 'code_lexical_response'} <= reads)
        self.assertEqual(missing(), set())
        for name in ('code_outline_response', 'code_constants_response', 'code_lexical_response'):
            value = vars(server).pop(name)
            try:
                self.assertIn(name, missing())
            finally:
                setattr(server, name, value)

    def test_codenav_edit_moves_production_identity(self):
        import retrieval_eval as evaluator
        with tempfile.TemporaryDirectory() as temp:
            scripts = Path(temp)
            # Copy the moved file independently of the identity allowlist, so
            # omitting it is detected by digest invariance, not fixture setup.
            for name in {*evaluator.PRODUCTION_RETRIEVAL_MODULES, 'codenav_handlers.py'}:
                shutil.copy2(SCRIPTS / name, scripts / name)
            before = evaluator._production_identity(scripts)
            with (scripts / 'codenav_handlers.py').open('a') as handle:
                handle.write('\n# isolated production-identity mutation\n')
            after = evaluator._production_identity(scripts)
            self.assertNotEqual(before['digest'], after['digest'])

    def test_golden_symbol_and_content_anchors_resolve_and_stale_path_fails(self):
        import retrieval_eval as evaluator
        server = load_server()
        corpus = evaluator.load_fixture_corpus(ROOT / 'docs/evals/retrieval-quality-golden.json', root=ROOT)
        resolved = evaluator.resolve_symbol_anchors(corpus, server, ROOT)
        symbols, contents = [], []
        for fixture in corpus['fixtures']:
            for entry in fixture['relevance']:
                anchor = entry.get('anchor', {})
                if anchor.get('type') == 'symbol':
                    symbols.append(entry)
                    self.assertIn(entry['path'] + '::' + anchor['value'], resolved)
                elif anchor.get('type') == 'content':
                    contents.append(entry)
                    self.assertIn(anchor['value'], (ROOT / entry['path']).read_text())
        self.assertTrue(symbols)
        self.assertTrue(contents)
        # A valid file with the wrong content must fail the same content oracle.
        bad_content = copy.deepcopy(contents[0])
        bad_content['path'] = '.wavefoundry/framework/scripts/mcp_tool_registry.py'
        with self.assertRaises(AssertionError):
            self.assertIn(bad_content['anchor']['value'], (ROOT / bad_content['path']).read_text())
        mutant = copy.deepcopy(corpus)
        target = next(e for f in mutant['fixtures'] for e in f['relevance']
                      if e.get('anchor', {}).get('value') == 'code_lexical_response')
        target['path'] = '.wavefoundry/framework/scripts/server_impl.py'
        with self.assertRaises(evaluator.EvaluationInvalid) as caught:
            evaluator.resolve_symbol_anchors(mutant, server, ROOT)
        self.assertEqual(caught.exception.code, 'unresolved_symbol_anchor')


_RELOAD = r'''
import inspect,json,sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()/'tests'))
from server_tools_support import _make_repo,load_server,load_thin_runner
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    root=_make_repo(Path(tmp))
    load_server()
    runner=load_thin_runner()
    runner.build_server(root)
    try:
        old=runner.server_impl.wf_graph_report_response
        source=Path('graph_handlers.py')
        source.write_text(source.read_text()+'\ndef wf_graph_report_response(root, **kwargs):\n    return {"status":"ok","data":{"handler_reload_probe":True}}\n')
        result=runner.perform_mcp_reload()
        assert result['status']=='ok',result
        fresh=runner.server_impl.wf_graph_report_response
        assert fresh is not old
        assert fresh(root)['data']['handler_reload_probe'] is True
        served=runner.server_impl._TOOL_REGISTRY.get('wf_graph_report').callable()
        assert served['data']['handler_reload_probe'] is True,served
        print(json.dumps({'fresh':True,'served_modified_handler':True}))
    finally:
        runner._get_handler().close()
'''


class HandlerReloadTests(unittest.TestCase):
    def test_actual_reload_serves_modified_scratch_graph_handler(self):
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp) / 'scripts'
            shutil.copytree(SCRIPTS, scratch, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            result = subprocess.run([sys.executable, '-B', '-c', _RELOAD], cwd=scratch,
                env=dict(os.environ, PYTHONPATH=str(scratch), PYTHONDONTWRITEBYTECODE='1'),
                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr[-4000:])
        self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1]),
                         {'fresh': True, 'served_modified_handler': True})


if __name__ == '__main__':
    unittest.main()

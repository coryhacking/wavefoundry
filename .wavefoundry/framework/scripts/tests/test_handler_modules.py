"""Compatibility contracts for extracted handler responses (1y0h2, 1ymzk).

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
from framework_files import source_path  # wf_server-aware source locations (wave 1yzd0)
# Explicit aliases preserve the retired gate response names and private optimize name.
FAMILIES = {'memory_handlers': {'memory_add': 'memory_add_response',
                     'memory_propose': 'memory_propose_response',
                     'memory_backfill': 'memory_backfill_response',
                     'memory_validate': 'memory_validate_response',
                     'memory_search': 'memory_search_response',
                     'memory_brief': 'memory_brief_response',
                     'memory_reconcile': 'memory_reconcile_response',
                     'memory_purge': 'memory_purge_response',
                     'memory_consolidate': 'memory_consolidate_response',
                     'wf_memory_eval': 'wf_memory_eval_response'},
 'techdocs_handlers': {'wf_techdocs_audit': 'wf_techdocs_audit_response',
                       'wf_techdocs_baseline': 'wf_techdocs_baseline_response'},
 'codenav_handlers': {'code_list_files': 'code_list_files_response',
                      'code_read': 'code_read_response',
                      'code_keyword': 'code_keyword_response',
                      'code_lexical': 'code_lexical_response',
                      'code_constants': 'code_constants_response',
                      'code_pattern': 'code_pattern_response',
                      'code_outline': 'code_outline_response',
                      'code_definition': 'code_definition_response',
                      'code_references': 'code_references_response',
                      'code_dependencies': 'code_dependencies_response',
                      'code_hover': 'code_hover_response',
                      'code_commit_provenance': 'code_commit_provenance_response'},
 'graph_handlers': {'code_impact': 'code_impact_response',
                    'code_callgraph': 'code_callgraph_response',
                    'code_callhierarchy': 'code_callhierarchy_response',
                    'code_graph_path': 'code_graph_path_response',
                    'code_graph_community': 'code_graph_community_response',
                    'code_risk_score': 'code_risk_score_response',
                    'wf_graph_report': 'wf_graph_report_response'},
 'context_efficiency_handlers': {'wf_context_efficiency_eval': 'wf_context_efficiency_eval_response'},
 'docs_handlers': {'wf_validate_docs': 'wf_validate_docs_response',
                   'wf_garden_docs': 'wf_garden_docs_response',
                   'wf_sync_surfaces': 'wf_sync_surfaces_response',
                   'wf_scan_secrets': 'wf_scan_secrets_response'},
 'dashboard_handlers': {'wf_start_dashboard': 'wf_start_dashboard_response',
                        'wf_stop_dashboard': 'wf_stop_dashboard_response',
                        'wf_restart_dashboard': 'wf_restart_dashboard_response',
                        'wf_open_dashboard': 'wf_open_dashboard_response'},
 'edit_gate_handlers': {'wf_open_gate': 'wave_open_gate_response',
                        'wf_close_gate': 'wf_close_wave_gate_response',
                        'wf_gate_status': 'wf_gate_status_response',
                        'wf_get_handoff': 'wf_get_handoff_response',
                        'wf_set_handoff': 'wf_set_handoff_response'},
 'upgrade_handlers': {'wf_upgrade': 'wf_upgrade_response',
                      'wf_upgrade_status': 'wf_upgrade_status_response',
                      'wf_audit_install': 'wf_audit_install_response'},
 'index_handlers': {'index_build': 'index_build_response',
                    'index_build_status': 'index_build_status_response',
                    'index_health': 'index_health_response',
                    'index_optimize': '_index_optimize_response'}}




# Literal classified sets captured from the admitted pre-move inventory.
SPLIT_THREE_ROSTERS = {'context_efficiency_handlers': ['_read_ce_projection_config',
                                 '_pending_ce_generations',
                                 '_maybe_project_context_efficiency',
                                 '_project_context_efficiency_wave',
                                 '_flush_context_efficiency',
                                 'project_pending_context_efficiency',
                                 'project_pending_context_efficiency_root',
                                 '_context_efficiency_state',
                                 'wf_context_efficiency_eval_response',
                                 '_state_sources_review_evidence',
                                 '_state_sources_get_change',
                                 '_state_sources_live_waves',
                                 '_state_sources_list_plans',
                                 '_state_sources_map',
                                 '_state_sources_memory_validate',
                                 '_state_sources_memory_propose',
                                 '_state_sources_memory_views',
                                 '_CE_PROJECTION_MIN_QUIET_SECONDS',
                                 '_CE_PROJECTION_DEFAULT_QUIET_SECONDS',
                                 '_CE_PROJECTION_MAX_QUIET_SECONDS',
                                 '_CE_PROJECTION_POLL_SECONDS',
                                 '_STATE_SOURCE_EXTRACTORS'],
 'docs_handlers': ['wf_validate_docs_response',
                   'wf_garden_docs_response',
                   'run_garden',
                   'wf_sync_surfaces_response',
                   'run_sync_surfaces',
                   'wf_scan_secrets_response',
                   '_subprocess_timeout_summary'],
 'dashboard_handlers': ['wf_start_dashboard_response',
                        'wf_open_dashboard_response',
                        '_dashboard_cmdline_pids',
                        '_dashboard_pid_is_live',
                        '_dashboard_url_reachable',
                        '_dashboard_already_serving',
                        '_dashboard_process_metadata',
                        '_remove_dashboard_metadata',
                        '_terminate_dashboard_pid',
                        'wf_stop_dashboard_response',
                        'wf_restart_dashboard_response',
                        'DASHBOARD_START_WAIT_SECONDS'],
 'edit_gate_handlers': ['wave_open_gate_response',
                        'wf_close_wave_gate_response',
                        'wf_gate_status_response',
                        '_force_gates_closed',
                        'wf_get_handoff_response',
                        'wf_set_handoff_response',
                        '_update_handoff_wave_ref',
                        '_read_guard_overrides',
                        '_write_guard_overrides',
                        '_VALID_GATES',
                        '_EDIT_GOVERNANCE_GATE_MAP'],
 'upgrade_handlers': ['wf_upgrade_response',
                      '_bounded_upgrade_response_envelope',
                      'wf_audit_install_response',
                      '_bounded_upgrade_summary',
                      '_parse_bridge_release_required',
                      '_upgrade_next_step',
                      'wf_upgrade_status_response',
                      '_load_upgrade_lib',
                      '_upgrade_summary_sentinel',
                      '_parse_upgrade_summary',
                      '_install_artifact_display',
                      '_install_audit_row_brief',
                      '_project_retired_model_cleanup_fields',
                      '_cutover_restart_required',
                      'UPGRADE_OUTPUT_CAP_CHARS',
                      'UPGRADE_SUMMARY_CAP_CHARS',
                      'UPGRADE_SUMMARY_VALUE_CAP_CHARS',
                      'UPGRADE_SUMMARY_MAX_ITEMS_PER_COLLECTION',
                      'UPGRADE_RESPONSE_CAP_CHARS',
                      'UPGRADE_BRIDGE_ARGV_CAP_CHARS',
                      'UPGRADE_SUMMARY_KEY_CAP_CHARS',
                      'UPGRADE_SUMMARY_METADATA_CAP_CHARS',
                      'UPGRADE_SUMMARY_TERMINAL_KEYS',
                      'RETIRED_MODEL_CLEANUP_KEYS',
                      '_RETIRED_MODEL_CLEANUP_ITEM_RE',
                      '_CUTOVER_RESTART_INSTRUCTION'],
 'index_handlers': ['_index_layer_readiness',
                    '_index_readiness_overview',
                    '_audit_build_summary',
                    '_audit_index_snapshot',
                    '_background_build_status',
                    '_background_build_progress',
                    '_index_dir_for_layer',
                    '_epoch_token',
                    '_epoch_state',
                    '_index_freshness_verdict',
                    '_index_rebuilding_response',
                    '_index_runtime_failure_response',
                    '_read_index_rebuild_stats',
                    '_index_is_up_to_date',
                    '_index_build_state_path',
                    '_clear_index_build_state',
                    '_index_build_log_path',
                    '_project_background_build_log_path',
                    '_index_build_stats_path',
                    '_graph_health_summary',
                    '_chunk_index_coverage',
                    '_read_index_build_stats_file',
                    '_write_index_build_stats_file',
                    '_refresh_index_build_stats_from_finished_log',
                    '_refresh_index_build_stats_from_finished_logs',
                    '_index_build_active',
                    '_check_index_writer_current',
                    'run_index_rebuild',
                    '_index_chunk_matching_address',
                    '_background_refresh_state_path',
                    '_indexable_refresh_path',
                    '_load_background_refresh_state',
                    '_lock_is_fresh',
                    '_background_refresh_active',
                    '_index_builder_cmdline_targets_root',
                    '_register_background_build_pid',
                    '_reap_background_build_pids',
                    '_register_dashboard_child_pid',
                    '_reap_dashboard_child_pids',
                    '_start_background_index_refresh',
                    '_trigger_background_index_refresh_for_paths',
                    '_index_dir_size',
                    '_close_optimize_enabled',
                    '_index_table_bloat_ratios',
                    '_sqlite_maintenance_failure',
                    '_maybe_optimize_index_on_close',
                    'index_health_response',
                    '_index_optimize_response',
                    'index_build_response',
                    '_index_build_lock_info',
                    'index_build_status_response',
                    '_index_build_status_response_inner',
                    '_graph_refresh_then_recheck',
                    'BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS',
                    'CLOSE_OPTIMIZE_BLOAT_RATIO',
                    '_BACKGROUND_BUILD_PIDS',
                    '_DASHBOARD_CHILD_PIDS',
                    '_FRESHNESS_CACHE',
                    '_FRESHNESS_TTL_SECONDS',
                    '_FRESHNESS_CURRENT',
                    '_FRESHNESS_STALE',
                    '_FRESHNESS_UNKNOWN',
                    '_FTS_DAMAGE_REASONS',
                    '_INDEX_BUILD_VERIFY_POLL_INTERVAL_SECONDS',
                    'BACKGROUND_INDEX_LOCK_STALE_SECONDS']}

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
        server_defs = {n.name for n in ast.parse(source_path("server_impl.py").read_text()).body
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for name, tools in FAMILIES.items():
            with self.subTest(module=name):
                module = importlib.import_module(name)
                source = source_path(name).read_text()
                tree = ast.parse(source)
                local_defs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
                for tool, response in tools.items():
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


    def test_memory_partition_and_reexport_identities(self):
        server = load_server()
        memory = importlib.import_module('memory_handlers')
        server_tree = ast.parse(source_path("server_impl.py").read_text())
        memory_tree = ast.parse(source_path("memory_handlers.py").read_text())
        staying = {'_auto_populate_memory_for_wave', '_memory_validation_diagnostics'}
        def definitions(tree):
            return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        self.assertTrue(staying <= definitions(server_tree))
        self.assertFalse(staying & definitions(memory_tree))
        # Literal roster comes from the independently approved inventory.
        moved = ('MEMORY_BRIEF_CAP', 'MEMORY_SEARCH_CAP', 'MEMORY_QUERY_CHECK_CAP', 'MEMORY_QUERY_MIN_LOGIT', 'MEMORY_PROPOSE_CAP', 'MEMORY_CONSOLIDATE_GROUP_CAP', 'MEMORY_CONSOLIDATE_MEMBER_CAP', 'MEMORY_SUMMARY_EXCERPT_CHARS', 'MEMORY_BRIEF_CONTEXTS', '_memory_mod', '_memory_fence', '_memory_finalize', '_LIFECYCLE_ID_TOKEN_RE', '_lifecycle_id_tokens', '_MEMORY_RECORDS_CACHE', '_MEMORY_BETWEENNESS_CACHE', '_MEMORY_KEY_BYPASS', '_memory_cache_key', '_memory_records_cached', '_memory_betweenness_by_file', '_memory_view', '_memory_ranked', 'MEMORY_ADVISORY_CAP', '_memory_advisories_for_path', '_memory_advisories_for_wave', '_credit_exploration_avoided_surface', 'memory_add_response', '_memory_add_response_locked', '_draft_view', 'memory_propose_response', '_memory_propose_response_locked', 'memory_backfill_response', '_memory_backfill_batch_locked', '_memory_file_target_exists', 'memory_validate_response', '_memory_query_records', 'memory_search_response', 'memory_brief_response', 'memory_reconcile_response', '_memory_reconcile_response_locked', 'memory_purge_response', 'memory_consolidate_response', 'wf_memory_eval_response')
        for name in moved:
            with self.subTest(name=name):
                self.assertIs(getattr(server, name), getattr(memory, name))
                self.assertNotIn(name, definitions(server_tree))
        assignments = {target.id for node in server_tree.body
                       if isinstance(node, (ast.Assign, ast.AnnAssign))
                       for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
                       if isinstance(target, ast.Name)}
        self.assertFalse(set(moved) & assignments)


    def test_split_three_complete_partitions_and_identity(self):
        server = load_server()
        root_tree = ast.parse(source_path("server_impl.py").read_text())
        def owned(tree):
            result = set()
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    result.add(node.name)
                elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                    for target in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                        result.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
            return result
        root_owned = owned(root_tree)
        for owner, names in SPLIT_THREE_ROSTERS.items():
            module = importlib.import_module(owner)
            tree = ast.parse(source_path(owner).read_text())
            self.assertTrue(set(names) <= owned(tree), owner)
            self.assertFalse(set(names) & root_owned, owner)
            for name in names:
                self.assertIs(getattr(server, name), getattr(module, name), (owner, name))
            # Include function-local imports; sibling handler imports are forbidden.
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse({a.name for a in node.names} & (set(FAMILIES) - {owner}))
                elif isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module, set(FAMILIES) - {owner})
        self.assertTrue({'register_mcp_surface', 'ImplHandler', '_maybe_refresh_if_stale',
                         '_read_monitor_config', '_wrap_upgrade_publication_guard',
                         '_indexer_module', '_run_post_write_lint', 'wf_audit_response'} <= root_owned)


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

    def test_docs_responses_reach_subprocess_and_manifest_without_transport(self):
        # Boundary doubles replace external processes; real responses parse their
        # outputs and real manifest files, including a known refusal path.
        docs = importlib.import_module('docs_handlers')
        def render(argv, **kwargs):
            self.assertIn('render_platform_surfaces.py', argv[1])
            Path(argv[argv.index('--manifest') + 1]).write_text(
                json.dumps({'written': ['docs/changed.md']}))
            return subprocess.CompletedProcess(argv, 0, 'rendered', '')
        with patch.object(self.server, '_mcp_subprocess_run', side_effect=render) as run, \
             patch.object(self.server, '_attach_lint_to_response', side_effect=lambda result, *args: result):
            result = docs.wf_sync_surfaces_response(self.root, mode='run')
        run.assert_called_once()
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['data']['written'], ['docs/changed.md'])
        with patch.object(self.server, '_mcp_subprocess_run', return_value=
                          subprocess.CompletedProcess([], 0, json.dumps({'failures': ['sentinel finding']}), '')) as run:
            result = docs.wf_scan_secrets_response(self.root, mode='full')
        run.assert_called_once()
        self.assertIn('run_secrets_scan.py', run.call_args.args[0][1])
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['data']['failures'], ['sentinel finding'])



class HandlerPackagingAndEvaluatorTests(unittest.TestCase):
    def test_generated_manifest_contains_all_handler_modules(self):
        import build_pack
        with tempfile.TemporaryDirectory() as temp:
            framework = Path(temp)
            (framework / 'scripts' / 'wf_server').mkdir(parents=True)
            shutil.copy2(SCRIPTS / 'wf_server' / '__init__.py', framework / 'scripts' / 'wf_server' / '__init__.py')
            for name in FAMILIES:
                # Wave 1yzd0: the flat alias and the package implementation both ship.
                shutil.copy2(SCRIPTS / (name + '.py'), framework / 'scripts' / (name + '.py'))
                shutil.copy2(source_path(name), framework / 'scripts' / 'wf_server' / (name + '.py'))
            manifest = build_pack.write_manifest(framework, build_pack.collect_files(framework))
            entries = manifest.read_text().splitlines()
        self.assertIn('scripts/wf_server/__init__.py', entries)
        for name in FAMILIES:
            self.assertIn('scripts/' + name + '.py', entries)
            self.assertIn('scripts/wf_server/' + name + '.py', entries)

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

    def test_memory_is_outside_measured_retrieval_closure(self):
        import retrieval_eval as evaluator
        self.assertNotIn('memory_handlers.py', evaluator.PRODUCTION_RETRIEVAL_MODULES)
        self.assertNotIn('techdocs_handlers.py', evaluator.PRODUCTION_RETRIEVAL_MODULES)
        functions = {}
        for module in ('server_impl', *FAMILIES):
            tree = ast.parse(source_path(module).read_text())
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    functions[node.name] = node
                elif isinstance(node, ast.ClassDef) and node.name == 'WaveIndex':
                    functions.update({'WaveIndex.' + child.name: child for child in node.body
                                      if isinstance(child, ast.FunctionDef)})
        roots = {'code_ask_response', 'code_search_response', 'docs_search_response',
                 'code_lexical_response'}
        self.assertTrue(roots <= functions.keys())
        reached, pending = set(), list(roots)
        while pending:
            name = pending.pop()
            if name in reached:
                continue
            reached.add(name)
            for call in ast.walk(functions[name]):
                if not isinstance(call, ast.Call):
                    continue
                target = call.func
                edge = None
                if isinstance(target, ast.Name):
                    edge = target.id
                elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                    if target.value.id == 'server_impl':
                        edge = target.attr
                    elif target.value.id in {'self', 'index'}:
                        edge = 'WaveIndex.' + target.attr
                if edge in functions and edge not in reached:
                    pending.append(edge)
        memory_tree = ast.parse(source_path("memory_handlers.py").read_text())
        memory_names = {node.name for node in memory_tree.body if isinstance(node, ast.FunctionDef)}
        self.assertTrue({'WaveIndex.search_docs', 'WaveIndex.search_code', '_response'} <= reached)
        self.assertFalse(memory_names & reached)
        evaluator_reads = {node.attr for node in ast.walk(ast.parse(inspect.getsource(evaluator)))
                           if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                           and node.value.id == 'server'}
        self.assertTrue({'WaveIndex', 'code_ask_response'} <= evaluator_reads)
        self.assertFalse(memory_names & evaluator_reads)
        corpus = json.loads((ROOT / 'docs/evals/retrieval-quality-golden.json').read_text())
        anchors = [entry['anchor'] for fixture in corpus['fixtures']
                   for entry in fixture['relevance'] if entry.get('anchor')]
        self.assertTrue(anchors)
        self.assertFalse([anchor for anchor in anchors
                          if any(name in anchor.get('value', '') for name in memory_names)])

    def test_codenav_edit_moves_production_identity(self):
        import retrieval_eval as evaluator
        with tempfile.TemporaryDirectory() as temp:
            scripts = Path(temp)
            # Copy the moved file independently of the identity allowlist, so
            # omitting it is detected by digest invariance, not fixture setup.
            # Wave 1yzd0: copy the package with its initializer so the identity
            # reads the implementing files, and mutate the implementation.
            (scripts / 'wf_server').mkdir()
            shutil.copy2(SCRIPTS / 'wf_server' / '__init__.py', scripts / 'wf_server' / '__init__.py')
            for name in {*evaluator.PRODUCTION_RETRIEVAL_MODULES, 'codenav_handlers.py'}:
                shutil.copy2(source_path(name), source_path(name, scripts))
            before = evaluator._production_identity(scripts)
            with source_path('codenav_handlers.py', scripts).open('a') as handle:
                handle.write('\n# isolated production-identity mutation\n')
            after = evaluator._production_identity(scripts)
            self.assertNotEqual(before['digest'], after['digest'])

    def test_golden_symbol_and_content_anchors_resolve_and_stale_path_fails(self):
        import retrieval_eval as evaluator
        server = load_server()
        corpus = evaluator.load_fixture_corpus(ROOT / 'docs/evals/retrieval-quality-golden.json', root=ROOT)
        # Wave 1yzd0: resolve the golden paths the way the evaluator does.
        resolution = evaluator.implementing_relevance_paths(ROOT, corpus)
        resolved = evaluator.resolve_symbol_anchors(corpus, server, ROOT, resolution)
        symbols, contents = [], []
        for fixture in corpus['fixtures']:
            for entry in fixture['relevance']:
                anchor = entry.get('anchor', {})
                if anchor.get('type') == 'symbol':
                    symbols.append(entry)
                    self.assertIn(entry['path'] + '::' + anchor['value'], resolved)
                elif anchor.get('type') == 'content':
                    contents.append(entry)
                    self.assertIn(anchor['value'], (ROOT / resolution.get(entry['path'], entry['path'])).read_text())
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
            evaluator.resolve_symbol_anchors(mutant, server, ROOT, evaluator.implementing_relevance_paths(ROOT, mutant))
        self.assertEqual(caught.exception.code, 'unresolved_symbol_anchor')


_RELOAD = r'''
import inspect,json,sys
from pathlib import Path
module_name, response_name, tool_name = sys.argv[1:]
sys.path.insert(0, str(Path.cwd()/'tests'))
from server_tools_support import _make_repo,load_server,load_thin_runner
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    root=_make_repo(Path(tmp))
    load_server()
    runner=load_thin_runner()
    runner.build_server(root)
    try:
        old=getattr(runner.server_impl, response_name)
        source=Path('wf_server')/(module_name+'.py')  # edit the implementation, never the alias
        source.write_text(source.read_text()+'\ndef '+response_name+'(root, *args, **kwargs):\n    return {"status":"ok","data":{"handler_reload_probe":True}}\n')
        result=runner.perform_mcp_reload()
        assert result['status']=='ok',result
        fresh=getattr(runner.server_impl, response_name)
        assert fresh is not old
        assert fresh(root)['data']['handler_reload_probe'] is True
        tool_args = {'wf_open_gate': {'gate': 'framework_edit_allowed'}, 'code_read': {'path': 'README.md'},
                     'wf_context_efficiency_eval': {'wave_id': 'probe', 'phase_id': 'implementation', 'mode': 'register'}}.get(tool_name, {})
        served=runner.server_impl._TOOL_REGISTRY.get(tool_name).callable(**tool_args)
        assert served['data']['handler_reload_probe'] is True,served
        print(json.dumps({'fresh':True,'served_modified_handler':True}))
    finally:
        runner._get_handler().close()
'''


class HandlerReloadTests(unittest.TestCase):
    def test_actual_reload_serves_modified_scratch_handlers(self):
        cases = (
            # Wave 1yzd0: every moved handler module, including code navigation.
            ('codenav_handlers', 'code_read_response', 'code_read'),
            ('graph_handlers', 'wf_graph_report_response', 'wf_graph_report'),
            ('memory_handlers', 'memory_brief_response', 'memory_brief'),
            ('techdocs_handlers', 'wf_techdocs_audit_response', 'wf_techdocs_audit'),
            ('index_handlers', 'index_build_response', 'index_build'),
            ('upgrade_handlers', 'wf_upgrade_response', 'wf_upgrade'),
            ('edit_gate_handlers', 'wave_open_gate_response', 'wf_open_gate'),
            ('dashboard_handlers', 'wf_start_dashboard_response', 'wf_start_dashboard'),
            ('docs_handlers', 'wf_validate_docs_response', 'wf_validate_docs'),
            ('context_efficiency_handlers', 'wf_context_efficiency_eval_response', 'wf_context_efficiency_eval'),
        )
        for module, response, tool in cases:
            with self.subTest(module=module), tempfile.TemporaryDirectory() as temp:
                scratch = Path(temp) / 'scripts'
                shutil.copytree(SCRIPTS, scratch, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
                result = subprocess.run([sys.executable, '-B', '-c', _RELOAD, module, response, tool], cwd=scratch,
                    env=dict(os.environ, PYTHONPATH=str(scratch), PYTHONDONTWRITEBYTECODE='1'),
                    capture_output=True, text=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stderr[-4000:])
                self.assertEqual(json.loads(result.stdout.strip().splitlines()[-1]),
                                 {'fresh': True, 'served_modified_handler': True})


if __name__ == '__main__':
    unittest.main()

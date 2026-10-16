"""Repeated adoption and receipt-bound cleanup, using public runner seams."""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import upgrade_wavefoundry as upgrade
import upgrade_extensions as extensions
import sqlite_storage_migration as migration
import upgrade_lib


class RerunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        framework = self.root / '.wavefoundry/framework'
        framework.mkdir(parents=True)
        (framework / 'VERSION').write_text('1.31.0+fixture\n')

    def test_same_build_cli_refuses_before_any_adoption_or_memory_work(self):
        with patch.object(upgrade, '_find_zip', return_value=None), \
                patch.object(upgrade, 'phase_surface_rendering', side_effect=AssertionError('render reached')), \
                patch.object(upgrade, 'phase_docs_gate', side_effect=AssertionError('docs gate reached')), \
                patch.object(upgrade, 'phase_index_update', side_effect=AssertionError('index reached')), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as error:
            with self.assertRaises(SystemExit) as stopped:
                upgrade.main(['--root', str(self.root), '--yes'])
        self.assertEqual(stopped.exception.code, 3)
        self.assertIn('already_installed_build', error.getvalue())
        self.assertFalse(upgrade_lib.upgrade_lock_path(self.root).exists())
        self.assertFalse((self.root / 'docs').exists())

    def test_equal_semver_different_build_reaches_plan(self):
        with patch.object(upgrade, '_read_installed_revision', return_value='1.31.0+earlier'), \
                patch.object(upgrade, '_find_zip', return_value=None), \
                patch.object(upgrade, '_print_change_plan') as plan:
            before, after, archive = upgrade.phase_preflight(self.root, True)
        self.assertEqual((before, after, archive), ('1.31.0+earlier', '1.31.0+fixture', None))
        plan.assert_called_once()

    def test_revision_fallback_and_stale_manifest_precedence(self):
        manifest = self.root / 'docs/prompts/prompt-surface-manifest.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text('{}')
        self.assertEqual(upgrade._read_installed_revision(self.root), '1.31.0+fixture')
        with patch.object(upgrade, '_find_zip', return_value=None), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                upgrade.phase_preflight(self.root, True)
        self.assertEqual(stopped.exception.code, 3)
        manifest.write_text(json.dumps({'framework_revision': '1.31.0+earlier'}))
        with patch.object(upgrade, '_find_zip', return_value=None), patch.object(upgrade, '_print_change_plan'):
            self.assertEqual(upgrade.phase_preflight(self.root, True)[:2],
                             ('1.31.0+earlier', '1.31.0+fixture'))

    def test_at_target_tree_survives_main_extraction_branch(self):
        import zipfile
        archive = self.root / 'fixture.zip'
        sentinel = self.root / '.wavefoundry/framework/keep.py'
        sentinel.write_bytes(b'project-preserved-byte-sentinel')
        with zipfile.ZipFile(archive, 'w') as pack:
            pack.writestr('.wavefoundry/framework/keep.py', 'destructive replacement')
        before = sentinel.read_bytes()
        # Exercise the actual main extraction branch after its preflight result;
        # stop at the next phase rather than start an index or model operation.
        with contextlib.ExitStack() as stack:
            for name, value in {
                'phase_preflight': ('1.31.0+earlier', '1.31.0+fixture', archive),
                '_stage_pack_for_consumption': archive,
                '_load_extension_module': None,
                '_run_hook': None,
                '_snapshot_pre_extract_chunker_versions': {},
                '_snapshot_pre_extract_versions': {},
                '_detect_version_transitions': [],
                '_warn_if_no_version_baseline': False,
            }.items():
                stack.enter_context(patch.object(upgrade, name, return_value=value))
            extract = stack.enter_context(patch.object(upgrade, '_extract_feature_members',
                                                       side_effect=AssertionError('destructive extraction')))
            stack.enter_context(patch.object(upgrade, 'phase_surface_rendering', side_effect=RuntimeError('fixture stop after extract')))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
            with self.assertRaisesRegex(RuntimeError, 'fixture stop after extract'):
                upgrade.main(['--root', str(self.root), '--yes'])
        extract.assert_not_called()
        self.assertEqual(sentinel.read_bytes(), before)

    def test_validated_retained_continuation_is_not_repeated_adoption(self):
        # main derives this flag only after its retained-state decision; the
        # process-resume suite exercises that validation with real checkpoints.
        with patch.object(upgrade, '_find_zip', return_value=None), \
                patch.object(upgrade, '_print_change_plan') as plan:
            result = upgrade.phase_preflight(self.root, True, retained_recovery=True)
        self.assertEqual(result[:2], ('1.31.0+fixture', '1.31.0+fixture'))
        plan.assert_called_once()

    def test_same_label_changed_pack_contents_also_refuse(self):
        import zipfile
        import upgrade_protocol
        pack = self.root / 'collision.zip'
        with zipfile.ZipFile(pack, 'w') as archive:
            archive.writestr('.wavefoundry/framework/VERSION', '1.31.0+fixture\n')
            archive.writestr('.wavefoundry/framework/scripts/new.py', 'CHANGED = True\n')
        with patch.object(upgrade_protocol, 'validate_feature_pack', return_value={}), \
                patch.object(upgrade_protocol, 'runner_compatibility', return_value='compatible'), \
                patch.object(upgrade, '_print_change_plan', side_effect=AssertionError('adoption reached')), \
                contextlib.redirect_stderr(io.StringIO()) as error:
            with self.assertRaises(SystemExit) as refused:
                upgrade.phase_preflight(self.root, True, explicit_pack=pack)
        self.assertEqual(refused.exception.code, 3)
        self.assertIn('distinct build identity', error.getvalue())
        self.assertFalse((self.root / '.wavefoundry/framework/scripts/new.py').exists())

    def test_absent_legacy_rebuild_refuses_before_preflight(self):
        with patch.object(upgrade, 'phase_preflight', side_effect=AssertionError('adoption reached')), \
                contextlib.redirect_stderr(io.StringIO()) as error:
            result = upgrade.main(['--root', str(self.root), '--rebuild-storage', '--yes'])
        self.assertEqual(result, 3)
        self.assertIn('storage_rebuild_not_applicable', error.getvalue())
        self.assertFalse(upgrade_lib.upgrade_lock_path(self.root).exists())

    def test_explicit_index_repairs_bypass_equal_build_adoption(self):
        for flag, phase in (('--update-index', 'phase_index_update'), ('--rebuild-index', 'phase_index_rebuild')):
            with self.subTest(flag=flag), contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(upgrade, 'phase_preflight', side_effect=AssertionError('adoption reached')))
                stack.enter_context(patch.object(upgrade, '_load_extension_module', return_value=None))
                stack.enter_context(patch.object(upgrade, '_run_hook'))
                stack.enter_context(patch.object(upgrade, '_ensure_lifecycle_policy_backstop'))
                stack.enter_context(patch.object(upgrade, '_ensure_rendered_permissions_backstop'))
                invoked = stack.enter_context(patch.object(upgrade, phase, return_value=True))
                self.assertEqual(upgrade.main(['--root', str(self.root), flag]), 0)
                invoked.assert_called_once_with(self.root)

    def test_registered_mcp_reports_same_build_non_success(self):
        from server_tools_support import load_server
        from mcp.server.fastmcp import FastMCP
        server = load_server()
        mcp = FastMCP('same-build-test')
        server.register_mcp_surface(mcp, lambda: types.SimpleNamespace(root=self.root))
        def child(cmd, **kwargs):
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', WAVEFOUNDRY_DISABLE_BYTECODE_CACHE='1')
            env.pop('PYTHONPYCACHEPREFIX', None)
            code = f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); import upgrade_wavefoundry as u; u._find_zip=lambda root: None; sys.exit(u.main(sys.argv[1:]))"
            return subprocess.run([sys.executable, '-B', '-c', code, *cmd[2:]],
                                  cwd=self.root, env=env, capture_output=True, text=True, timeout=20)
        with patch.object(server, '_mcp_subprocess_run', side_effect=child), \
                patch.object(server, 'project_pending_context_efficiency', return_value={'ok': True}):
            response = mcp._tool_manager._tools['wf_upgrade'].fn()
        self.assertEqual(response['status'], 'error', response)
        self.assertEqual(response['data']['exit_code'], 3)
        self.assertIn('already_installed_build', response['data']['output'])


class DateStabilityTests(unittest.TestCase):
    def test_next_day_registered_render_preserves_existing_doc_bytes(self):
        import render_agent_surfaces as renderer
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with patch.object(renderer.time, 'strftime', return_value='2026-10-15'):
                renderer.render_agent_surfaces(root)
            before = {p.relative_to(root): p.read_bytes() for p in (root / 'docs').rglob('*.md')}
            self.assertTrue(before)
            with patch.object(renderer.time, 'strftime', return_value='2026-10-16'):
                renderer.render_agent_surfaces(root)
            self.assertEqual(before, {p.relative_to(root): p.read_bytes() for p in (root / 'docs').rglob('*.md')})

    def test_docs_gate_gardens_only_changed_docs_and_retains_real_edits(self):
        import docs_gardener
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            doc = root / 'docs/guide.md'
            doc.parent.mkdir()
            initial = '# Guide\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-10-15\n\nText.\n'
            doc.write_text(initial)
            changed = []
            def child(argv, **kwargs):
                if Path(argv[1]).name == 'docs_gardener.py':
                    with patch.dict(os.environ, {'PROJECT_ROOT': str(root)}), \
                            patch.object(docs_gardener, 'collect_changed_markdown_paths', return_value=changed):
                        code = docs_gardener.main(['--date', '2026-10-16'])
                else:
                    code = 0  # Metadata writer fixture; lint has separate gate coverage.
                return types.SimpleNamespace(returncode=code)
            with patch.object(upgrade, '_run_upgrade_child', side_effect=child):
                upgrade.phase_docs_gate(root)
                self.assertEqual(doc.read_text(), initial)
                doc.write_text(initial + 'Substantive addition.\n')
                changed.append(doc)
                upgrade.phase_docs_gate(root)
            self.assertIn('Last verified: 2026-10-16', doc.read_text())
            self.assertIn('Substantive addition.', doc.read_text())


class IncomingOutcomeTests(unittest.TestCase):
    def test_old_parent_actual_result_is_observed_and_original_restored(self):
        for result in (False, True):
            with self.subTest(result=result), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                parent = types.ModuleType('old_upgrade_fixture')
                context = type('OldContext', (), {'__module__': parent.__name__})()
                context.root = root
                original = parent.phase_index_update = lambda *_: result
                with patch.dict(sys.modules, {parent.__name__: parent}), \
                        patch.object(extensions, 'enforce_index_guard_handoff'), \
                        patch.object(extensions, '_bridge_index_publisher_grant'), \
                        patch.object(extensions, '_read_json_object', return_value={}), \
                        patch.object(extensions, '_update_upgrade_state') as update:
                    extensions.pre_index_update(context)
                    self.assertEqual(parent.phase_index_update(root), result)
                    self.assertIs(parent.phase_index_update, original)
                    if result:
                        extensions.post_index_update(context)
                    else:
                        with self.assertRaises(SystemExit) as refused:
                            extensions.post_index_update(context)
                        self.assertEqual(refused.exception.code, 1)
                        update.assert_called_once_with(root, index_publication_failed=True)

    def test_parent_exception_restores_original_and_unknown_outcome_cannot_seal(self):
        parent = types.ModuleType('old_upgrade_fixture')
        context = type('OldContext', (), {'__module__': parent.__name__})()
        context.root = Path('/unused-fixture-root')
        def failed(*_):
            raise ValueError('index failed')
        parent.phase_index_update = failed
        with patch.dict(sys.modules, {parent.__name__: parent}):
            extensions._observe_parent_index_outcome(context)
            with self.assertRaises(ValueError):
                parent.phase_index_update(context.root)
            self.assertIs(parent.phase_index_update, failed)
        with patch.object(extensions, '_update_upgrade_state'), \
                patch.object(extensions, '_installed_memory_backfill', side_effect=AssertionError('seal reached')):
            with self.assertRaises(SystemExit):
                extensions.post_index_update(context)


class GraphOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.index = self.root / '.wavefoundry/index'
        self.graph = self.index / migration.GRAPH_OUTPUT_DIRNAME
        self.graph.mkdir(parents=True)
        self.file = self.graph / 'project-graph.json'
        self.file.write_bytes(b'old graph')
        self.receipt = {'retired_graph_ownership': migration._capture_retired_graph(self.index)}

    def test_capture_removes_only_unchanged_owned_entries(self):
        plan = migration._plan_captured_graph(self.index, self.receipt)
        if os.unlink not in os.supports_dir_fd or not hasattr(os, 'O_NOFOLLOW'):
            self.assertEqual(plan['state'], migration.RETAINED_UNOWNED_CONTENTS)
            self.assertEqual(migration._apply_retired_graph_directory(self.root, self.index, plan), 0)
            self.assertTrue(self.graph.exists())
            return
        self.assertEqual(plan['state'], 'removable')
        self.assertEqual(migration._apply_retired_graph_directory(self.root, self.index, plan), 9)
        self.assertFalse(self.graph.exists())

    def test_missing_evidence_and_replacement_preserve_whole_directory(self):
        self.assertEqual(migration._plan_captured_graph(self.index, {})['state'], migration.RETAINED_UNOWNED_CONTENTS)
        self.file.write_bytes(b'changed graph')
        plan = migration._plan_captured_graph(self.index, self.receipt)
        self.assertEqual(plan['state'], migration.RETAINED_UNOWNED_CONTENTS)
        self.assertEqual(migration._apply_retired_graph_directory(self.root, self.index, plan), 0)
        self.assertEqual(self.file.read_bytes(), b'changed graph')

    def test_deletion_time_swap_is_refused(self):
        plan = migration._plan_captured_graph(self.index, self.receipt)
        self.file.write_bytes(b'changed after plan')
        with self.assertRaises(migration.MigrationRequired):
            migration._apply_retired_graph_directory(self.root, self.index, plan)
        self.assertEqual(self.file.read_bytes(), b'changed after plan')

    def test_new_allowlisted_entry_is_not_adopted_on_retry(self):
        added = self.graph / 'project-graph-clusters.json'
        added.write_bytes(b'new')
        self.assertEqual(migration._plan_captured_graph(self.index, self.receipt)['state'], migration.RETAINED_UNOWNED_CONTENTS)
        added.unlink()
        self.assertEqual(migration._plan_captured_graph(self.index, self.receipt)['state'], 'removable')

    def test_replaced_empty_directory_is_not_owned(self):
        self.graph.rename(self.index / 'preserved-original')
        self.graph.mkdir()
        self.assertEqual(migration._plan_captured_graph(self.index, self.receipt)['state'],
                         migration.RETAINED_UNOWNED_CONTENTS)

    def test_publication_and_host_refusals_precede_graph_deletion(self):
        receipt = {**self.receipt, 'state': 'verified'}
        for boundary in ('verify_migration', '_hosts_gone'):
            with self.subTest(boundary=boundary), contextlib.ExitStack() as controls:
                controls.enter_context(patch.object(migration, 'read_receipt', return_value=receipt))
                controls.enter_context(patch.object(migration, 'verify_migration', return_value=receipt))
                controls.enter_context(patch.object(migration, boundary, side_effect=migration.MigrationRequired('unproven')))
                controls.enter_context(patch.object(migration, '_plan_captured_graph', side_effect=AssertionError('cleanup reached')))
                with self.assertRaisesRegex(migration.MigrationRequired, 'unproven'):
                    migration.cleanup_legacy(self.root)
                self.assertEqual(self.file.read_bytes(), b'old graph')


if __name__ == '__main__':
    unittest.main()

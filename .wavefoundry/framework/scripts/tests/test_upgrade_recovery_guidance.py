"""Recovery guidance pins on real setup, publication and registered MCP consumers."""
from __future__ import annotations
import asyncio
import contextlib
import io
import importlib
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import sqlite_storage_migration as migration
import setup_reconciliation as setup
import upgrade_extensions as extensions
import upgrade_wavefoundry as upgrade
import upgrade_bundle
import publication_control
from server_tools_support import load_server, load_thin_runner, _make_repo


class ResumeGuidanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "operator's repo"
        self.root.mkdir()

    def test_storage_and_guard_cli_quoting_is_unchanged(self):
        for platform in ('posix', 'nt'):
            with self.subTest(platform=platform), patch.object(migration, 'os', SimpleNamespace(**{**vars(os), 'name': platform})):
                result = migration.resume_guidance(self.root, resume_flag='--cleanup')
                expected = [sys.executable, str(self.root / '.wavefoundry/framework/scripts/upgrade_wavefoundry.py'), '--root', str(self.root), '--cleanup', '--yes', '--confirm-hosts-stopped']
                self.assertEqual(result['command_argv'], expected)
                self.assertTrue(result['operator_run'])
                self.assertTrue(result['requires_hosts_stopped'])
                self.assertFalse(result['agent_execution_allowed'])
                self.assertIn('external terminal', result['guidance'])
                if platform == 'nt':
                    self.assertEqual(result['command'], '& ' + ' '.join("'" + arg.replace("'", "''") + "'" for arg in expected))
                else:
                    self.assertEqual(shlex.split(result['command']), expected)
        with self.assertRaises(ValueError):
            migration.resume_guidance(self.root, resume_flag='--unapproved')

    def test_legacy_pause_shapes_route_index_but_never_storage_or_guard_actions(self):
        cases = [
            ({'action_required': {'kind': 'historical_memory'}}, '--update-index'),
            ({'failed_phase': 'awaiting_memory_validation'}, '--update-index'),
            ({'failed_phase': 'historical_memory_backfill'}, '--update-index'),
            ({'current_phase': 'awaiting_memory_publication'}, '--update-index'),
            ({'current_phase': 'memory_resume_preflight'}, '--update-index'),
            ({'current_phase': 'awaiting_memory_validation', 'failed_phase': 'index_update'}, '--update-index'),
            ({'failed_phase': 'awaiting_memory_validation', 'current_phase': 'docs_gate_complete'}, '--resume-after-gate'),
            ({'current_phase': 'awaiting_memory_validation', 'memory_backfill_run_id': 'alone'}, None),
            ({'current_phase': 'storage_restart_required', 'failed_phase': 'awaiting_memory_validation'}, None),
            ({'action_required': {'kind': 'storage_migration'}, 'current_phase': 'memory_resume_preflight'}, None),
            ({'action_required': {'kind': 'index_guard_handoff'}, 'current_phase': 'memory_resume_preflight'}, None),
        ]
        for checkpoint, flag in cases:
            with self.subTest(checkpoint=checkpoint):
                self.assertEqual(migration._checkpoint_resume_flag(checkpoint), flag)
                if migration.legacy_memory_pause(checkpoint):
                    report = migration.resume_guidance(self.root, checkpoint)
                    self.assertIn('--update-index', report['command_argv'])
                    self.assertNotIn('--confirm-hosts-stopped', report['command_argv'])
                    self.assertFalse(report['requires_hosts_stopped'])
                    self.assertNotIn('external terminal', report['guidance'])

    def test_alias_guidance_and_read_only_consumers_name_only_index_then_cleanup(self):
        result = migration.resume_guidance(self.root, resume_flag='--resume-after-memory')
        self.assertIn('--update-index', result['command_argv'])
        self.assertNotIn('--resume-after-memory', result['command_argv'])
        self.assertTrue(result['agent_execution_allowed'])
        messages = [upgrade_bundle._recovery(self.root, {}, 'awaiting_memory_validation')['instruction'],
                    publication_control._checkpoint_recovery_tail({'failed_phase': 'awaiting_memory_validation'}, self.root)]
        handlers = importlib.import_module('wf_server.upgrade_handlers')
        messages.append(handlers._upgrade_next_step('resume_after_memory', self.root)[0])
        for text in messages:
            self.assertIn('cleanup', text)
            self.assertNotIn('memory_validate', text)
            self.assertNotIn('external terminal', text)

    def test_memory_publishers_are_refused_under_every_retained_checkpoint(self):
        path = self.root / '.wavefoundry/upgrade-in-progress.json'
        path.parent.mkdir()
        for phase in ('awaiting_memory_validation', 'awaiting_memory_publication', 'index_update'):
            path.write_text(json.dumps({'current_phase': phase}))
            for name in ('memory_backfill', 'memory_validate'):
                self.assertIn('upgrade_in_progress', publication_control.publication_block_reason(self.root, name))

    def test_preindex_does_not_read_memory_and_postindex_uses_actual_result(self):
        checkpoint = self.root / '.wavefoundry/upgrade-in-progress.json'
        checkpoint.parent.mkdir()
        checkpoint.write_text(json.dumps({'memory_backfill_run_id': 'old-run'}))
        ctx = SimpleNamespace(root=self.root)
        with patch.object(extensions, 'enforce_index_guard_handoff') as guard, patch.object(extensions, '_bridge_index_publisher_grant') as grant, patch.object(extensions, '_installed_memory_backfill', side_effect=AssertionError('memory authority must not be read')):
            extensions.pre_index_update(ctx)
            guard.assert_called_once_with(ctx)
            grant.assert_called_once()
            ctx.index_published = True
            extensions.post_index_update(ctx)
            ctx.index_published = False
            with self.assertRaises(SystemExit) as failed:
                extensions.post_index_update(ctx)
            self.assertEqual(failed.exception.code, 1)
        self.assertTrue(json.loads(checkpoint.read_text())['index_publication_failed'])


class RegisteredGapGuidanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = _make_repo(Path(temporary.name).resolve() / "operator's repo")
        self.runner = load_thin_runner()
        self.mcp = self.runner.build_server(self.root)

    def call(self, name):
        result = self.mcp._tool_manager._tools[name].fn()
        return asyncio.run(result) if hasattr(result, '__await__') else result

    def test_actual_gap_marker_at_both_top_level_boundaries(self):
        marker = self.root / '.wavefoundry/logs/context-efficiency.gap'
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_bytes(b'')
        for name in ('wf_upgrade', 'wf_reload_mcp'):
            with self.subTest(name=name), patch.object(self.runner, 'perform_mcp_reload') as reload, patch.object(self.server, 'wf_upgrade_response') as child:
                result = self.call(name)
            reload.assert_not_called()  # Projection refusal precedes a live reload.
            child.assert_not_called()  # Projection refusal precedes upgrade spawning.
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['data']['projection']['detail']['authority_status'], 'accounting_gap')
            text = result['usage']
            self.assertIn('./.wavefoundry/bin/wf clear-accounting-gap', text)
            self.assertIn(shlex.quote(str(self.root)), text)
            for term in ('discards no waves, docs or memories', 'unsealed, non-closed', 'accounting_gap', 'totals stay flagged incomplete', 'not backfilled'):
                self.assertIn(term, text)
            self.assertTrue(marker.exists())

    def test_non_gap_failure_keeps_prior_text_and_windows_is_only_rendered(self):
        projection = {'ok': False, 'detail': {'authority_status': 'unavailable'}}
        with patch.object(self.server, 'project_pending_context_efficiency', return_value=projection) as project:
            upgrade_response, reload_response = self.call('wf_upgrade'), self.call('wf_reload_mcp')
        self.assertEqual(project.call_count, 2)
        self.assertEqual(upgrade_response['usage'], 'Resolve the projection failure, then retry wf_upgrade.')
        self.assertEqual(reload_response['usage'], 'Resolve the projection failure, then call wf_reload_mcp() again.')
        with patch.object(migration, 'os', SimpleNamespace(**{**vars(os), 'name': 'nt'})):
            text = migration.accounting_gap_guidance(self.root)
        self.assertIn(r'.\.wavefoundry\bin\wf.cmd clear-accounting-gap', text)
        self.assertIn("'" + str(self.root).replace("'", "''") + "'", text)


if __name__ == '__main__':
    unittest.main()

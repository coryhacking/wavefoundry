"""Public review attribution: optional on first write, immutable on replay."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server_tools_support import _make_repo, integrity_checks, load_server, load_thin_runner


class ReviewOperatorIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        made = self.srv.wf_create_wave_response(self.root, 'operator-test', mode='create')
        self.assertEqual(made['status'], 'ok', made)
        self.wave_id = made['data']['wave_id']
        self.wave_md = self.root / made['data']['path']
        self.ledger = self.wave_md.parent / 'events.jsonl'
        self.map = self.root / 'docs/contributors.json'
        self.map.write_text(json.dumps({
            'alice': {'name': 'Alice', 'emails': ['alice@example.test']},
            'bob': {'name': 'Bob', 'emails': ['bob@example.test']},
        }))

    def call(self, event='approval', mode='create', context='same', **extra):
        args = dict(mode=mode, fresh_context=True, independent=True,
                    integrity_checks=integrity_checks())
        if event == 'approval':
            args.update(signoff_key='qa-reviewer', approval_phase='delivery',
                        evidence={'observed': 'passed', 'artifact_or_test_id': 'test:operator'})
        elif event == 'run':
            args.update(run_kind='initial_delivery', cycle=0)
        elif event == 'finding':
            args.update(finding_id='identity-finding-' + context, run_kind='initial_delivery', cycle=0,
                        source_lanes=['qa-reviewer'], judgment={
                            'validation_status': 'conforming', 'scope_relation': 'admitted',
                            'introduced_or_worsened_by_wave': False, 'contract_relevance': 'none',
                            'supported_reachability': False, 'attacker_reachability': False,
                            'authority_domain': 'none', 'authority_delta': 'none',
                            'observable_impact': 'none', 'containment': 'preventive',
                        }, evidence={
                            'proposition': 'behavior conforms', 'failure_condition': 'counterexample',
                            'public_path': 'wf_review_event', 'command_or_fixture': 'operator fixture',
                            'expected': 'conforming', 'observed': 'conforming',
                            'artifact_or_test_id': 'test:operator',
                            'known_bad_detection_method': 'changed semantic content control',
                            'limitations': 'local fixture', 'safety_and_authorization': 'temporary repository',
                            'disposition_rationale': 'no issue reproduced',
                        })
        args.update(extra)
        return self.srv.wf_review_event_response(
            self.root, self.wave_id, event, 'qa-reviewer', context, **args)

    def contexts(self, response):
        return [r['verification_context'] for r in response['data']['appended_records']
                if 'verification_context' in r]

    def test_preview_and_create_propagate_explicit_identity_for_all_events(self):
        for event in ('approval', 'finding', 'run'):
            with self.subTest(event=event):
                before = self.ledger.read_bytes()
                preview = self.call(event, mode='dry_run', context=event, operator_handle='alice')
                self.assertEqual(preview['status'], 'dry_run', preview)
                self.assertEqual(self.ledger.read_bytes(), before)
                actual = self.call(event, context=event, operator_handle='alice')
                self.assertEqual(actual['status'], 'ok', actual)
                self.assertEqual(preview['data']['appended_records'], actual['data']['appended_records'])
                self.assertTrue(self.contexts(actual))
                for context in self.contexts(actual):
                    self.assertEqual(context['operator'], {'handle': 'alice', 'source': 'explicit'})
        self.assertIn('current executed approval by alice, not receipt-bound, follows every affected repair',
                      self.wave_md.read_text())

    def test_git_identity_and_unresolved_git_states_reach_public_write(self):
        import subprocess
        module = sys.modules['operator_identity']
        for event in ('approval', 'finding', 'run'):
            with self.subTest(event=event), patch.object(module.subprocess, 'run', return_value=
                    subprocess.CompletedProcess([], 0, ' ALICE@EXAMPLE.TEST\n', '')):
                result = self.call(event, context='git-' + event)
            self.assertEqual(result['status'], 'ok', result)
            self.assertTrue(self.contexts(result))
            for context in self.contexts(result):
                self.assertEqual(context['operator'], {'handle': 'alice', 'source': 'git_email'})
        for label, code, email in [('unset', 1, ''), ('unmapped', 0, 'nobody@example.test'),
                                   ('ambiguous', 0, 'alice@example.test')]:
            if label == 'ambiguous':
                data = json.loads(self.map.read_text())
                data['bob']['emails'].append('alice@example.test')
                self.map.write_text(json.dumps(data))
            with patch.object(module.subprocess, 'run', return_value=
                              subprocess.CompletedProcess([], code, email, '')):
                result = self.call(context=label)
            self.assertEqual(result['status'], 'ok', result)
            self.assertNotIn('operator', self.contexts(result)[0])
            self.assertEqual([d['code'] for d in result['diagnostics']], ['operator_identity_unresolved'])

    def test_replay_keeps_original_or_absent_identity_without_lookup(self):
        for event in ('approval', 'finding', 'run'):
            for original in ({'handle': 'alice', 'source': 'git_email'}, None):
                with self.subTest(event=event, original=original):
                    context_id = event + str(original)
                    with patch.object(self.srv, 'resolve_operator', return_value=(original, 'no_contributors_file')):
                        first = self.call(event, context=context_id)
                    self.assertEqual(first['status'], 'ok', first)
                    before = self.ledger.read_bytes()
                    with patch.object(self.srv, 'resolve_operator', side_effect=AssertionError('replay lookup')):
                        replay = self.call(event, context=context_id, operator_handle='bob')
                    self.assertEqual(replay['status'], 'ok', replay)
                    self.assertTrue(replay['data']['replayed'])
                    self.assertEqual(replay['data']['appended_records'], first['data']['appended_records'])
                    self.assertEqual(self.ledger.read_bytes(), before)

    def test_missing_map_is_silent_and_invalid_map_does_not_block(self):
        for name, content in [('missing', None), ('json', '{'), ('blank', json.dumps({' ': {'name': 'A', 'emails': ['a@b']}}))]:
            with self.subTest(name=name):
                if content is None:
                    self.map.unlink(missing_ok=True)
                else:
                    self.map.write_text(content)
                result = self.call(context=name, operator_handle='alice')
                self.assertEqual(result['status'], 'ok', result)
                self.assertNotIn('operator', self.contexts(result)[0])
                diagnostics = [d for d in result['diagnostics'] if d['code'] == 'operator_identity_unresolved']
                self.assertEqual(len(diagnostics), 0 if name == 'missing' else 1)
                if diagnostics:
                    self.assertTrue(diagnostics[0]['advisory'])

    def test_unknown_explicit_handle_warns_in_preview_and_create(self):
        for mode in ('dry_run', 'create'):
            result = self.call(mode=mode, operator_handle='unknown')
            self.assertEqual(result['status'], 'dry_run' if mode == 'dry_run' else 'ok', result)
            self.assertNotIn('operator', self.contexts(result)[0])
            self.assertEqual([d['code'] for d in result['diagnostics']], ['operator_identity_unresolved'])

    def test_list_does_not_resolve_identity(self):
        with patch.object(self.srv, 'resolve_operator', side_effect=AssertionError('list lookup')):
            result = self.srv.wf_review_event_response(
                self.root, self.wave_id, 'list', '', '', operator_handle='alice')
        self.assertEqual(result['status'], 'ok', result)

    def test_registered_schema_forwards_optional_handle_and_reload_refreshes_resolver(self):
        runner = load_thin_runner()
        mcp = runner.build_server(self.root)
        tool = mcp._tool_manager._tools['wf_review_event']
        schema = tool.parameters
        self.assertIn('operator_handle', schema['properties'])
        self.assertNotIn('operator_handle', schema.get('required', []))
        prop = schema['properties']['operator_handle']
        self.assertTrue(prop.get('type') == 'string' or {'type': 'string'} in prop.get('anyOf', []))
        result = tool.fn(wave_id=self.wave_id, event='run', actor='qa-reviewer',
                         context_id='registered', run_kind='initial_delivery', operator_handle='alice')
        self.assertEqual(result['status'], 'dry_run', result)
        self.assertEqual(self.contexts(result)[0]['operator']['handle'], 'alice')
        stale_module = sys.modules['operator_identity']
        with patch.object(stale_module, 'resolve_operator', return_value=(None, 'stale implementation')):
            reloaded = runner.perform_mcp_reload()
        self.assertEqual(reloaded['status'], 'ok', reloaded)
        self.assertIsNot(sys.modules['operator_identity'], stale_module)
        fresh_tool = mcp._tool_manager._tools['wf_review_event']
        result = fresh_tool.fn(wave_id=self.wave_id, event='run', actor='qa-reviewer',
                               context_id='fresh', run_kind='initial_delivery', operator_handle='alice')
        self.assertEqual(result['status'], 'dry_run', result)
        self.assertEqual(self.contexts(result)[0]['operator']['handle'], 'alice')


if __name__ == '__main__':
    unittest.main()

"""Readiness telemetry uses real policy producers; its diagnostics never gate."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from server_tools_support import _make_repo, integrity_checks, load_server, load_thin_runner
import test_server_tools_lifecycle as fixtures
import record_paths
import review_evidence
import vocabulary_profile


class ReadinessSignalTests(unittest.TestCase):
    _write_config = fixtures.WaveCouncilPolicyTests._write_config
    _prepared_wave_with_change = fixtures.WaveCouncilPolicyTests._prepared_wave_with_change
    _record_readiness_approval = fixtures.WaveCouncilPolicyTests._record_readiness_approval
    _run_prepare = fixtures.WaveCouncilPolicyTests._run_prepare
    LINT_OK = fixtures.WaveCouncilPolicyTests.LINT_OK
    GARDEN_OK = fixtures.WaveCouncilPolicyTests.GARDEN_OK

    def setUp(self):
        self.srv = load_server()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = _make_repo(Path(self.temp.name))
        self._write_config()

    def _records(self, wave_md):
        records, errors = review_evidence.read_review_event_ledger(wave_md)
        self.assertEqual(errors, ())
        return records

    def _publish(self, wave_md):
        text = wave_md.read_text()
        support = self.srv.lifecycle_gate_support
        changes = support._extract_change_ids_from_wave_text(text)
        brief = support._build_prepare_council_brief(wave_md.parent.name, text, changes)
        state, errors = support._prepare_policy_state(self.root, wave_md, text, changes, brief)
        self.assertEqual(errors, ())
        self.srv._publish_prepare_policy_state(self.root, wave_md, text, state)
        return state

    def _wave_with_receipts(self, count):
        if count == 0:
            result = self.srv.wf_create_wave_response(self.root, 'empty-receipts', mode='create')
            self.assertEqual(result['status'], 'ok', result)
            wave_id = result['data']['wave_id']
            wave_md = vocabulary_profile.record_file(record_paths.load_record_roots(self.root).waves / wave_id)
            self.assertFalse(any(r['record_type'] == 'review_policy_receipt' for r in self._records(wave_md)))
            return wave_id, wave_md, None
        wave_id, wave_md, change = self._prepared_wave_with_change('receipt-count')
        for number in range(1, count):
            change.write_text(change.read_text().replace('1. x', f'1. x revision-{number}', 1))
            self._publish(wave_md)
        self.assertEqual(sum(r['record_type'] == 'review_policy_receipt' for r in self._records(wave_md)), count)
        return wave_id, wave_md, change

    @staticmethod
    def _diagnostics(result, code):
        return [d for d in result.get('diagnostics', []) if d['code'] == code]

    def test_receipt_counts_zero_one_five_six_are_from_canonical_ledger(self):
        # Each subcase has a distinct root: no hand-authored receipt records.
        for count in (0, 1, 5, 6):
            with self.subTest(count=count), tempfile.TemporaryDirectory() as temp:
                self.root = _make_repo(Path(temp))
                self._write_config()
                wave_id, wave_md, _ = self._wave_with_receipts(count)
                ledger_before = review_evidence.review_event_path(wave_md).read_bytes()
                result = self._run_prepare(wave_id=wave_id, mode='dry_run')
                self.assertEqual(result['data']['readiness_receipts'], count)
                high = self._diagnostics(result, 'readiness_receipt_publications_high')
                self.assertEqual(len(high), int(count == 6))
                if high:
                    self.assertIs(high[0]['advisory'], True)
                    self.assertIn('publication', high[0]['message'].lower())
                    self.assertNotIn('budget exhausted', high[0]['message'].lower())
                self.assertEqual(review_evidence.review_event_path(wave_md).read_bytes(), ledger_before)

    def test_receipts_after_first_initial_delivery_do_not_count(self):
        wave_id, wave_md, change = self._wave_with_receipts(5)
        result = self.srv.wf_review_event_response(
            self.root, wave_id=wave_id, event='run', mode='create',
            actor='code-reviewer', context_id='delivery-count-boundary',
            run_kind='initial_delivery', cycle=0)
        self.assertEqual(result['status'], 'ok', result)
        for number in range(2):
            change.write_text(change.read_text().replace('1. x', f'1. x delivery-{number}', 1))
            self._publish(wave_md)
        self.assertEqual(sum(r['record_type'] == 'review_policy_receipt' for r in self._records(wave_md)), 7)
        result = self._run_prepare(wave_id=wave_id, mode='dry_run')
        self.assertEqual(result['data']['readiness_receipts'], 5)
        self.assertFalse(self._diagnostics(result, 'readiness_receipt_publications_high'))

    def test_count_observes_receipt_published_by_this_prepare(self):
        wave_id, wave_md, change = self._wave_with_receipts(5)
        change.write_text(change.read_text().replace('1. x', '1. x changed before prepare', 1))
        result = self._run_prepare(wave_id=wave_id, mode='ready')
        self.assertEqual(sum(r['record_type'] == 'review_policy_receipt' for r in self._records(wave_md)), 6)
        self.assertEqual(result['data']['readiness_receipts'], 6)
        self.assertTrue(self._diagnostics(result, 'readiness_receipt_publications_high'))

    def test_early_errors_and_unavailable_ledger_report_null_not_zero(self):
        cases = [('unknown-wave', 'dry_run'), ('unknown-wave', 'not-a-mode')]
        for wave_id, mode in cases:
            with self.subTest(mode=mode):
                result = self.srv.wf_prepare_wave_response(self.root, wave_id, mode=mode)
                self.assertEqual(result['status'], 'error')
                self.assertIn('readiness_receipts', result['data'])
                self.assertIsNone(result['data']['readiness_receipts'])
        result = self.srv._ensure_no_extra_args('wf_prepare_wave', {'unsupported': True})
        self.assertEqual(result['status'], 'error')
        self.assertTrue(self._diagnostics(result, 'unknown_arguments'))
        self.assertIn('readiness_receipts', result['data'])
        self.assertIsNone(result['data']['readiness_receipts'])
        wave_id, wave_md, _ = self._wave_with_receipts(1)
        ledger = review_evidence.review_event_path(wave_md)
        ledger.write_text('{invalid-ledger\n')
        result = self._run_prepare(wave_id=wave_id, mode='dry_run')
        self.assertEqual(result['status'], 'error')
        self.assertIsNone(result['data']['readiness_receipts'])
        self.assertFalse(self._diagnostics(result, 'readiness_lane_approvals_missing'))
        with patch.object(self.srv, '_find_wave_md_detailed', side_effect=self.srv.record_paths.RecordLayoutInvalid(['fixture layout refused'])) as resolve:
            result = self.srv.wf_prepare_wave_response(self.root, wave_id)
            resolve.assert_called_once()
        self.assertEqual(result['status'], 'error')
        self.assertIsNone(result['data']['readiness_receipts'])

    def test_outer_lock_refusals_keep_null_count_and_original_error(self):
        calls = []
        tool = SimpleNamespace(fn=lambda **kwargs: calls.append(kwargs))
        mcp = SimpleNamespace(_tool_manager=SimpleNamespace(_tools={'wf_prepare_wave': tool}))
        self.srv._wrap_lifecycle_mutation_lock(mcp, lambda: SimpleNamespace(root=self.root))
        with patch.object(self.srv, '_lifecycle_mutation_lock', side_effect=self.srv.LifecycleMutationBusy('fixture-lock')) as acquire:
            result = tool.fn(wave_id='unknown', mode='ready')
            acquire.assert_called_once()
        self.assertEqual(calls, [])
        self.assertEqual(result['status'], 'error')
        self.assertIsNone(result['data']['readiness_receipts'])
        self.assertTrue(self._diagnostics(result, 'lifecycle_mutation_locked'))

    def test_other_outer_refusals_include_unknown_count(self):
        def unavailable():
            raise OSError('fixture root unavailable')

        for case, expected in (('root', 'lifecycle_lock_unavailable'),
                               ('upgrade', 'upgrade_in_progress'),
                               ('publication', 'project_publication_busy')):
            with self.subTest(case=case):
                called = []
                def handler(**kwargs):
                    called.append(kwargs)
                    raise self.srv.ProjectPublicationUnavailable('fixture publication')
                tool = SimpleNamespace(fn=handler)
                mcp = SimpleNamespace(_tool_manager=SimpleNamespace(_tools={'wf_prepare_wave': tool}))
                if case == 'root':
                    self.srv._wrap_lifecycle_mutation_lock(mcp, unavailable)
                    result = tool.fn(mode='ready')
                else:
                    self.srv._wrap_upgrade_publication_guard(mcp, lambda: SimpleNamespace(root=self.root))
                    reason = 'upgrade_in_progress: fixture' if case == 'upgrade' else None
                    with patch.object(self.srv.publication_control, 'publication_block_reason', return_value=reason):
                        result = tool.fn(mode='ready')
                self.assertEqual(bool(called), case == 'publication')
                self.assertEqual(result['status'], 'error')
                self.assertTrue(self._diagnostics(result, expected))
                self.assertIn('readiness_receipts', result['data'])
                self.assertIsNone(result['data']['readiness_receipts'])

    def test_no_ledger_schema_or_projection_change_for_read_only_prepare(self):
        wave_id, wave_md, _ = self._wave_with_receipts(1)
        review = review_evidence
        self.assertEqual(review.RUN_KINDS, {'readiness', 'initial_delivery', 'repair_start', 'reverification', 'convergence_checkpoint'})
        records = self._records(wave_md)
        before = review.render_review_evidence_projection(wave_md.read_text(), records)
        self._run_prepare(wave_id=wave_id, mode='dry_run')
        self.assertEqual(self._records(wave_md), records)
        self.assertEqual(review.render_review_evidence_projection(wave_md.read_text(), records), before)

    def test_lane_advice_matches_activation_union_and_current_receipt(self):
        self._write_config(transition_policy='applies-from-next-prepare')
        config_path = self.root / 'docs/workflow-config.json'
        config = json.loads(config_path.read_text())
        config['required_review_lanes'] = ['security-reviewer']
        config_path.write_text(json.dumps(config))
        wave_id, wave_md, change = self._wave_with_receipts(1)
        roster = ('- Requested review lanes: code-reviewer\n- Required review lanes: none\n\n'
                  '| Role | Lane | Scope |\n|------|------|-------|\n'
                  '| code-reviewer | review | scope |\n\n')
        wave_md.write_text(re.sub(r'(?ms)(^## Participants[ \t]*\n).*?(?=^## )',
                                 lambda m: m[1] + '\n' + roster, wave_md.read_text(), count=1))
        self._publish(wave_md)
        self.assertEqual(self._record_readiness_approval(wave_id, 'code-reviewer', 'old-code')['status'], 'ok')
        change.write_text(change.read_text().replace('1. x', '1. x revised lane contract', 1))
        self._publish(wave_md)
        # Publication materializes project lanes into the wave roster. Remove
        # that duplicate so this fixture independently exercises project union.
        text = wave_md.read_text()
        text = re.sub(r'(?m)^- Required review lanes:.*$',
                      '- Required review lanes: code-reviewer, qa-reviewer', text)
        wave_md.write_text(self.srv._project_current_review_status(self.root, wave_md, text))

        def check(expected):
            prepared = self._run_prepare(wave_id=wave_id, mode='dry_run')
            advice = self._diagnostics(prepared, 'readiness_lane_approvals_missing')
            self.assertEqual(len(advice), bool(expected), prepared)
            if expected:
                self.assertEqual(set(advice[0]['missing_lanes']), set(expected))
                self.assertIs(advice[0]['advisory'], True)
            activated = self.srv.wf_implement_wave_response(self.root, wave_id=wave_id, mode='dry_run')
            gates = self._diagnostics(activated, 'prepare_review_incomplete')
            self.assertEqual(len(gates), bool(expected), activated)
            if expected:
                actual = [row['lane'] for row in gates[0]['lane_results']]
                self.assertEqual(set(actual), set(expected))
                self.assertEqual(gates[0]['lane_results'], advice[0]['lane_results'])
                for row in gates[0]['lane_results']:
                    self.assertFalse(row['approval_current'])
                    self.assertEqual(row['approval_phase'], 'readiness')
                    self.assertIn(row['approval_state'], {'absent', 'stale'})
                    self.assertTrue(row['why'])
                    self.assertTrue(row['next_action'])
            return prepared

        check(['code-reviewer', 'qa-reviewer', 'security-reviewer'])  # stale wave lane + absent project lane
        for lane in ('code-reviewer', 'qa-reviewer', 'security-reviewer', 'wave-council-readiness'):
            recorded = self._record_readiness_approval(wave_id, lane, 'current-' + lane)
            self.assertEqual(recorded['status'], 'ok', recorded)
            if lane == 'code-reviewer':
                check(['qa-reviewer', 'security-reviewer'])
        check([])

    def test_advisory_attachment_preserves_success_and_error_outcomes(self):
        wave_id, _, _ = self._wave_with_receipts(6)
        for status in ('ok', 'error'):
            with self.subTest(status=status):
                response = {'status': status, 'data': {'sentinel': 7}, 'diagnostics': []}
                result = self.srv._attach_prepare_readiness_advisories(self.root, wave_id, response)
                self.assertIs(result, response)
                self.assertEqual(result['status'], status)
                self.assertEqual(result['data']['sentinel'], 7)
                self.assertTrue(self._diagnostics(result, 'readiness_receipt_publications_high'))

    def _readiness_review(self, wave_id, *, registered=False):
        handler = self.srv.wf_review_wave_response
        if registered:
            handler = load_thin_runner().build_server(self.root)._tool_manager._tools['wf_review_wave'].fn
        with patch.object(self.srv, 'run_validate', return_value=self.LINT_OK):
            return (handler(wave_id=wave_id, phase='prepare') if registered else
                    handler(self.root, wave_id=wave_id, phase='prepare'))

    def _decision_finding(self, wave_id, finding_id, *, security=False, phase='readiness', evidence_text='fixture observation'):
        judgment = {
            'validation_status': 'real', 'scope_relation': 'admitted',
            'introduced_or_worsened_by_wave': security,
            'contract_relevance': 'required_ac' if security else 'none',
            'supported_reachability': security, 'attacker_reachability': False,
            'authority_domain': 'confidentiality' if security else 'none',
            'authority_delta': 'material' if security else 'none',
            'observable_impact': 'material' if security else 'low', 'containment': 'preventive',
            'fix_risk': 'comparable', 'optional_value': 'positive', 'repair_scope_bounded': True,
            'repair_safety': 'safe', 'benefit_vs_fix_risk': 'greater', 'rejection_basis': 'none',
        }
        evidence = {key: evidence_text for key in review_evidence.REVIEW_FINDING_REQUIRED_EVIDENCE_FIELDS}
        evidence.update(artifact_or_test_id='test:readiness-decision', known_bad_detection_method='injected contrary judgment')
        lane = 'security-reviewer' if security else 'code-reviewer'
        result = self.srv.wf_review_event_response(
            self.root, wave_id=wave_id, event='finding', mode='create',
            actor=lane, context_id='ctx-' + finding_id, finding_id=finding_id,
            run_kind='readiness' if phase == 'readiness' else 'initial_delivery', cycle=0,
            source_lanes=[lane], blocking_required_lanes=[lane] if security else [],
            approval_recheck_lanes=[lane],
            judgment=judgment, evidence=evidence, fresh_context=True, independent=True,
            integrity_checks=integrity_checks())
        self.assertEqual(result['status'], 'ok', result)
        return result

    def test_registered_decision_packet_and_write_continuation_preserve_canonical_authority(self):
        config_path = self.root / 'docs/workflow-config.json'
        config = json.loads(config_path.read_text())
        config['required_review_lanes'] = ['security-reviewer', 'code-reviewer']
        config_path.write_text(json.dumps(config))
        wave_id, wave_md, _ = self._wave_with_receipts(1)
        for lane in ('council-readiness', 'security-reviewer', 'code-reviewer', 'qa-reviewer'):
            self.assertEqual(self._record_readiness_approval(wave_id, lane, 'before-' + lane)['status'], 'ok')
        advisory = self._decision_finding(wave_id, 'editorial-note')
        self.assertIn('readiness_decision_packet', advisory['data']['review_actions'])
        self.assertEqual(self.srv.wf_implement_wave_response(self.root, wave_id=wave_id, mode='dry_run')['status'], 'dry_run')
        blocker = self._decision_finding(wave_id, 'security-ac', security=True)
        continuation = blocker['data']['review_actions']['readiness_decision_packet']
        ledger = review_evidence.review_event_path(wave_md)
        before = ledger.read_bytes(), wave_md.read_bytes()
        gate_before = self.srv.wf_implement_wave_response(self.root, wave_id=wave_id, mode='dry_run')
        reviewed = self._readiness_review(wave_id, registered=True)
        packet = reviewed['data']['review_actions']['readiness_decision_packet']
        self.assertEqual(packet, continuation)
        facts = {row['finding_id']: row for row in packet['finding_facts']}
        self.assertEqual((facts['editorial-note']['disposition'], facts['editorial-note']['blocking']), ('maybe_later', False))
        self.assertEqual((facts['security-ac']['disposition'], facts['security-ac']['blocking']), ('do_now', True))
        self.assertEqual(facts['security-ac']['unresolved_required_lanes'], ('security-reviewer',))
        self.assertEqual(facts['security-ac']['judgment_reasons']['contract_relevance'], 'required_ac')
        self.assertTrue(facts['security-ac']['affected_signoff_keys'])
        self.assertIn('focused_rereview', reviewed['data']['review_actions'])
        self.assertEqual(packet['navigation']['focused_rereview'], 'review_actions.focused_rereview')
        waiver = packet['operator_options'][-1]
        self.assertEqual(waiver['required_fields'], ['waiver_id', 'waiver_scope', 'waiver_reason', 'waiver_risk'])
        self.assertFalse(waiver['grants_approval'])
        self.assertFalse(waiver['automatic_security_waiver'])
        self.assertFalse(packet['operator_stop_inferred'])
        self.assertEqual((ledger.read_bytes(), wave_md.read_bytes()), before)
        self.assertEqual(self.srv.wf_implement_wave_response(self.root, wave_id=wave_id, mode='dry_run')['status'], gate_before['status'])
        self.assertEqual(gate_before['status'], 'error')
        security_approval = next(row for row in packet['approval_facts'] if row['signoff_key'] == 'security-reviewer')
        self.assertEqual(security_approval['approval_state'], 'withheld')
        self.assertEqual(security_approval['blocking_finding_ids'], ('security-ac',))

    def test_decision_packet_missing_run_approvals_and_empty_actions_do_not_imply_ready(self):
        wave_id, _, _ = self._wave_with_receipts(1)
        initial = self._readiness_review(wave_id)
        actions = initial['data']['review_actions']
        packet = actions['readiness_decision_packet']
        self.assertFalse(packet['required_run_present'])
        self.assertFalse(actions['next_actions'])
        self.assertTrue(packet['approval_facts'])
        self.assertTrue(all(row['approval_state'] == 'absent' for row in packet['approval_facts']))
        self.assertFalse(packet['empty_actions_imply_ready'])
        self.assertFalse(packet['operator_stop_inferred'])
        self.assertEqual(initial['status'], 'error')
        run = self.srv.wf_review_event_response(self.root, wave_id=wave_id, event='run', mode='create',
            actor='council-chair', context_id='run-packet', run_kind='readiness', cycle=0)
        self.assertEqual(run['status'], 'ok', run)
        after = run['data']['review_actions']['readiness_decision_packet']
        self.assertTrue(after['required_run_present'])
        self.assertTrue(any(not row['approval_current'] for row in after['approval_facts']))

    def test_decision_packet_phase_unavailable_and_delivery_compatibility(self):
        wave_id, wave_md, change = self._wave_with_receipts(1)
        delivery = self._decision_finding(wave_id, 'delivery-only', security=True, phase='delivery')
        self.assertNotIn('readiness_decision_packet', delivery['data']['review_actions'])
        result = self._readiness_review(wave_id)
        fact = result['data']['review_actions']['readiness_decision_packet']['finding_facts'][0]
        self.assertEqual(fact['origin_phase'], 'delivery')
        self.assertEqual(fact['affected_signoff_keys'], ())
        self.assertTrue(all('delivery-only' not in row['blocking_finding_ids'] for row in
                            result['data']['review_actions']['readiness_decision_packet']['approval_facts']))
        change.write_text(change.read_text().replace('1. x', '1. x changed contract', 1))
        stale = self._readiness_review(wave_id)['data']['review_actions']['readiness_decision_packet']
        self.assertFalse(stale['available'])
        self.assertEqual(stale['reason'], 'review_policy_receipt_stale')
        self.assertIsNone(stale['total_findings'])
        self.assertEqual(stale['finding_facts'], [])
        # negative-fixture: deliberately unreadable typed authority must not manufacture an empty ready packet.
        review_evidence.review_event_path(wave_md).write_text('{invalid-ledger\n')
        invalid = self._readiness_review(wave_id)['data']['review_actions']['readiness_decision_packet']
        self.assertFalse(invalid['available'])
        self.assertEqual(invalid['reason'], 'invalid_typed_authority')

    def test_decision_packet_bounds_rows_bytes_and_excludes_oversized_evidence(self):
        wave_id, wave_md, _ = self._wave_with_receipts(1)
        secret = 'MALICIOUS-PHI-DO-NOT-COPY-' * 3000
        self._decision_finding(wave_id, 'safe-reference', evidence_text=secret)
        packet = self._readiness_review(wave_id)['data']['review_actions']['readiness_decision_packet']
        self.assertNotIn(secret[:100], json.dumps(packet))
        self.assertNotIn('judgment_template', json.dumps(packet))
        self.assertLessEqual(len(json.dumps(packet).encode()), packet['byte_cap'])
        # A small aggregate budget on the real public path forces omission;
        # the optional note must not silently make missing approvals disappear.
        with patch.object(self.srv, 'READINESS_DECISION_BYTE_CAP', 1900):
            limited = self._readiness_review(wave_id)['data']['review_actions']['readiness_decision_packet']
        self.assertTrue(limited['truncated'])
        self.assertGreater(limited['omitted_findings'] + limited['omitted_approvals'], 0)
        self.assertLessEqual(len(json.dumps(limited).encode()), 1900)
        with patch.object(self.srv, 'READINESS_DECISION_ROW_CAP', 1):
            limited = self._readiness_review(wave_id)['data']['review_actions']['readiness_decision_packet']
        self.assertEqual(len(limited['finding_facts']) + len(limited['approval_facts']), 1)
        self.assertEqual(limited['total_findings'], 1)
        self.assertTrue(limited['omitted_approvals'])
        oversized_id = 'reference-' + 'x' * 200
        self._decision_finding(wave_id, oversized_id)
        limited = self._readiness_review(wave_id)['data']['review_actions']['readiness_decision_packet']
        self.assertEqual(limited['total_findings'], 2)
        self.assertEqual(limited['omitted_findings'], 1)
        self.assertNotIn(oversized_id, json.dumps(limited))


class ReadinessProtocolPins(unittest.TestCase):
    """Presence only: scenario evaluations establish agent behavior separately."""
    ROOT = Path(__file__).resolve().parents[4]
    SURFACES = (
        '.wavefoundry/framework/seeds/215-council-chair.prompt.md',
        'docs/agents/specialists/council-chair.md',
        '.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md',
        'docs/contributing/review-and-evals.md',
        '.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md',
        vocabulary_profile.prompt_doc('prepare-wave'),  # the profile's path (change 2134q)
        '.wavefoundry/framework/seeds/007-review-system-overview.md',
    )
    RULES = (
        'After the first full readiness review, focused review is the default.',
        'one bounded repair pass',
        'wf_prepare_wave(mode="ready")',
        'one focused verification round',
        'unchanged context needed to detect contradictions and regressions',
        'Every required lane and the council re-record required readiness approvals against the current receipt after publication',
        'At the end of focused verification, escalate every remaining blocker to the operator',
        'No further automatic repair/review round begins.',
        'this protocol never waives required-lane authority.',
    )
    SHAPE_RULES = (
        'the rule deriving that set; the derived set governs',
        'An acceptance criterion names the observable outcome and kind of oracle.',
        'A readiness repair narrows or deletes a claim it cannot verify rather than elaborating it.',
    )

    @staticmethod
    def _missing(text, rules):
        return {rule for rule in rules if rule not in text}

    def test_essential_protocol_rules_and_deleted_rule_controls(self):
        groups = [(self.SURFACES, self.RULES), ((
            '.wavefoundry/framework/seeds/170-plan-change.prompt.md',
            vocabulary_profile.prompt_doc('plan-change')), self.SHAPE_RULES), ((
            '.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md',
            'docs/contributing/review-and-evals.md'), (
                'would ship wrong behavior',
                'cannot be implemented correctly because a substantive decision is unresolved',
                'required acceptance criterion that cannot pass or cannot fail',
                'Preferences without these consequences remain untyped notes',
            ))]
        for paths, rules in groups:
            for path in paths:
                with self.subTest(path=path):
                    text = (self.ROOT / path).read_text()
                    self.assertEqual(self._missing(text, rules), set())
                    for rule in rules:
                        # Delete a load-bearing rule while retaining the rest of
                        # the document. Each control must name exactly its loss.
                        self.assertEqual(self._missing(text.replace(rule, ''), rules), {rule})


if __name__ == '__main__':
    unittest.main()

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

from server_tools_support import _make_repo, load_server
import test_server_tools_lifecycle as fixtures
import review_evidence


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
            wave_md = self.root / 'docs/waves' / wave_id / 'wave.md'
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
                actual = re.search(r'approval: (.*?)\. Run', gates[0]['message']).group(1).split(', ')
                self.assertEqual(set(actual), set(expected))
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


class ReadinessProtocolPins(unittest.TestCase):
    """Presence only: scenario evaluations establish agent behavior separately."""
    ROOT = Path(__file__).resolve().parents[4]
    SURFACES = (
        '.wavefoundry/framework/seeds/215-wave-council.prompt.md',
        'docs/agents/specialists/wave-council.md',
        '.wavefoundry/framework/seeds/209-agent-harness-core.prompt.md',
        'docs/contributing/review-and-evals.md',
        '.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md',
        'docs/prompts/prepare-wave.prompt.md',
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
            '.wavefoundry/framework/seeds/170-plan-feature.prompt.md',
            'docs/prompts/plan-feature.prompt.md'), self.SHAPE_RULES), ((
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

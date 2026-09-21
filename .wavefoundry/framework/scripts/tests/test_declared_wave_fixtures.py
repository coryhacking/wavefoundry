"""Producer-backed fixture validity and a bounded, per-token declaration census."""
from __future__ import annotations

import io
import json
from pathlib import Path
import re
import tempfile
import tokenize
import unittest
from unittest.mock import patch

import review_evidence
from server_tools_support import (
    _make_repo, load_server, declared_wave_doc_gates, make_declared_wave,
    review_policy_config,
)

DECLARATION = 'review-evidence-source: ' + 'events.jsonl'
CLASSIFICATION = re.compile(r'^# (negative-fixture|component-fixture|producer-fixture|declaration-check):\s*(\S.*)$')


def declaration_sites(source):
    """Inspect literal tokens only; computed declarations require human review."""
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    comments = {t.start[0]: t.string for t in tokens if t.type == tokenize.COMMENT}
    string_types = {tokenize.STRING, getattr(tokenize, 'FSTRING_MIDDLE', tokenize.STRING)}
    sites = []
    for token in tokens:
        if token.type not in string_types or DECLARATION not in token.string:
            continue
        adjacent = (comments.get(token.start[0] - 1, ''),
                    comments.get(token.end[0], ''))
        valid = any(CLASSIFICATION.fullmatch(comment) for comment in adjacent)
        sites.append((token.start[0], valid))
    return sites


def fixture_doc_stubs():
    """Explicit caller choice, shared by fixture tests and migrated test setups."""
    return {
        'run_validate': lambda *a, **k: {'passed': True, 'errors': [], 'warnings': [], 'output': ''},
        'run_garden': lambda *a, **k: {'passed': True, 'files_updated': 0, 'updated': [], 'output': ''},
        '_run_post_write_lint': lambda *a, **k: {'mode': 'stubbed'},
        '_trigger_background_index_refresh_for_paths': lambda *a, **k: None,
    }


class DeclaredWaveFixtureTests(unittest.TestCase):
    def setUp(self):
        self.srv = load_server()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = _make_repo(Path(self.temp.name))
        path = self.root / 'docs/workflow-config.json'
        config = json.loads(path.read_text())
        config['wave_review'] = review_policy_config()
        path.write_text(json.dumps(config))
        self.stubs = fixture_doc_stubs()
        with declared_wave_doc_gates(self.srv, self.stubs):
            made = self.srv._change_create_response(self.root, 'enh', 'fixture-child', mode='create')
        self.assertEqual(made['status'], 'ok', made)
        self.change_id = made['data']['change_id']

    def build(self, **kwargs):
        return make_declared_wave(self.srv, self.root, 'fixture',
                                  doc_gate_stubs=self.stubs, **kwargs)

    def prepare(self, wave_id):
        with declared_wave_doc_gates(self.srv, self.stubs):
            return self.srv.wf_prepare_wave_response(self.root, wave_id, mode='ready')

    def test_valid_fixture_and_independent_readiness_oracle(self):
        wave_id, path = self.build(change_ids=[self.change_id], ready=True,
                                  readiness_run=True, approvals=('wave-council-readiness',))
        valid = review_evidence.validate_external_review_evidence(path)
        self.assertTrue(valid.ok, valid.errors)
        with declared_wave_doc_gates(self.srv, self.stubs):
            dry = self.srv.wf_prepare_wave_response(self.root, wave_id, mode='dry_run')
        self.assertFalse({'review_evidence_invalid', 'review_policy_reprepare_required'} &
                         {d['code'] for d in dry['diagnostics']})
        ready = self.prepare(wave_id)
        self.assertEqual(ready['status'], 'ok', ready)
        self.assertEqual([d for d in ready['diagnostics'] if not d.get('advisory')], [])

    def test_missing_readiness_run_is_caught_by_final_prepare_not_just_parser(self):
        wave_id, path = self.build(change_ids=[self.change_id], ready=True,
                                  readiness_run=False, approvals=('wave-council-readiness',))
        self.assertTrue(review_evidence.validate_external_review_evidence(path).ok)
        result = self.prepare(wave_id)
        self.assertEqual(result['status'], 'error')
        self.assertIn('review_evidence_invalid', [d['code'] for d in result['diagnostics']])
        self.assertIn('`readiness` Review Run Record', ' '.join(d['message'] for d in result['diagnostics']))

    def test_real_producers_run_in_order_and_stubs_restore(self):
        names = ('wf_create_wave_response', 'wf_add_change_response', 'wf_prepare_wave_response', 'wf_review_event_response')
        calls = []
        originals = {name: getattr(self.srv, name) for name in self.stubs}
        from contextlib import ExitStack
        with ExitStack() as stack:
            for name in names:
                real = getattr(self.srv, name)
                def record(*args, _real=real, _name=name, **kwargs):
                    calls.append((_name, kwargs.get('event')))
                    if _name != names[0]:
                        wave_md = self.root / 'docs/waves' / args[1] / 'wave.md'
                        self.assertRegex(wave_md.read_text(), r'(?m)^Status: planned$')
                    return _real(*args, **kwargs)
                stack.enter_context(patch.object(self.srv, name, side_effect=record))
            _, path = self.build(status='implementing', change_ids=[self.change_id],
                                 ready=True, readiness_run=True,
                                 approvals=('wave-council-readiness',))
        self.assertRegex(path.read_text(), r'(?m)^Status: implementing$')
        self.assertEqual(calls, [(names[0], None), (names[1], None), (names[2], None),
                                 (names[3], 'run'), (names[3], 'approval')])
        for name, original in originals.items():
            self.assertIs(getattr(self.srv, name), original)

    def test_refusals_fail_at_the_producer_and_restore_all_stubs(self):
        for name in ('wf_create_wave_response', 'wf_add_change_response',
                     'wf_prepare_wave_response', 'wf_review_event_response'):
            with self.subTest(producer=name):
                with declared_wave_doc_gates(self.srv, self.stubs):
                    made = self.srv._change_create_response(self.root, 'enh', name.replace('_', '-'), mode='create')
                self.change_id = made['data']['change_id']
                originals = {key: getattr(self.srv, key) for key in self.stubs}
                refusal = {'status': 'error', 'data': {}, 'diagnostics': [
                    {'code': 'fixture_refusal', 'message': 'specific failure explanation'}]}
                with patch.object(self.srv, name, return_value=refusal):
                    with self.assertRaisesRegex(AssertionError, 'specific failure explanation'):
                        self.build(change_ids=[self.change_id], ready=True, readiness_run=True)
                for key, original in originals.items():
                    self.assertIs(getattr(self.srv, key), original)

    def test_missing_receipt_cannot_hide_behind_expected_initial_refusal(self):
        refusal = {'status': 'error', 'data': {}, 'diagnostics': [
            {'code': 'missing_wave_council_signoff', 'message': 'expected initial refusal'}]}
        with patch.object(self.srv, 'wf_prepare_wave_response', return_value=refusal):
            with self.assertRaisesRegex(AssertionError, 'did not publish a receipt'):
                self.build(change_ids=[self.change_id], ready=True)

    def test_explicit_stubs_and_admitted_change_are_required(self):
        with self.assertRaisesRegex(ValueError, 'admitted change'):
            self.build(ready=True)
        for key in self.stubs:
            with self.subTest(key=key):
                stubs = dict(self.stubs)
                del stubs[key]
                with self.assertRaisesRegex(ValueError, 'doc_gate_stubs'):
                    make_declared_wave(self.srv, self.root, 'bad', doc_gate_stubs=stubs)

    def test_invalid_helper_inputs_fail_before_producer_entry(self):
        with patch.object(self.srv, 'wf_create_wave_response') as create:
            for kwargs, message in (
                ({'approvals': ('wave-council-readiness',)}, 'approvals require ready=True'),
                ({'status': 'unsupported'}, 'unsupported synthetic wave status'),
                ({'status': 'ready'}, 'unsupported synthetic wave status'),
            ):
                with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, message):
                    self.build(**kwargs)
                create.assert_not_called()
        originals = {key: getattr(self.srv, key) for key in self.stubs}
        for key in self.stubs:
            with self.subTest(noncallable=key):
                stubs = dict(self.stubs)
                stubs[key] = None
                with self.assertRaisesRegex(ValueError, 'callable stubs'):
                    with declared_wave_doc_gates(self.srv, stubs):
                        self.fail('noncallable stub reached the producer context')
                for name, original in originals.items():
                    self.assertIs(getattr(self.srv, name), original)

    def test_invalid_prepare_envelopes_reject_after_real_receipt_publication(self):
        real_prepare = self.srv.wf_prepare_wave_response
        for case in ('unexpected-blocker', 'unsupported-status', 'error-without-blocker'):
            with self.subTest(case=case):
                original_seams = {key: getattr(self.srv, key) for key in self.stubs}
                observed_receipts = []
                with declared_wave_doc_gates(self.srv, self.stubs):
                    change = self.srv._change_create_response(self.root, 'enh', case, mode='create')
                self.assertEqual(change['status'], 'ok', change)

                def prepare_then_corrupt(*args, **kwargs):
                    result = real_prepare(*args, **kwargs)
                    wave_md = self.root / 'docs/waves' / args[1] / 'wave.md'
                    records, errors = self.srv.read_review_event_ledger(wave_md)
                    self.assertFalse(errors, errors)
                    receipts = [r for r in records if r.get('record_type') == 'review_policy_receipt']
                    self.assertTrue(receipts, 'the real Prepare must publish a receipt first')
                    observed_receipts.extend(receipts)
                    if case == 'unexpected-blocker':
                        result['diagnostics'].append({
                            'code': 'fixture_unexpected_blocker',
                            'message': 'unexpected blocker after real receipt publication',
                        })
                    elif case == 'unsupported-status':
                        result['status'] = 'unsupported'
                    else:
                        result['status'] = 'error'
                        result['diagnostics'] = []
                    return result

                with patch.object(self.srv, 'wf_prepare_wave_response', side_effect=prepare_then_corrupt):
                    with self.assertRaisesRegex(AssertionError, 'prepare receipt refused:') as refused:
                        make_declared_wave(
                            self.srv, self.root, case, change_ids=(change['data']['change_id'],),
                            ready=True, doc_gate_stubs=self.stubs,
                        )
                self.assertTrue(observed_receipts)
                if case == 'unexpected-blocker':
                    self.assertIn('unexpected blocker after real receipt publication', str(refused.exception))
                for name, original in original_seams.items():
                    self.assertIs(getattr(self.srv, name), original)

    def test_synthetic_status_changes_only_the_status_line(self):
        original = self.srv.wf_create_wave_response
        generated = []
        def capture(*args, **kwargs):
            result = original(*args, **kwargs)
            generated.append((self.root / result['data']['path']).read_text())
            return result
        with patch.object(self.srv, 'wf_create_wave_response', side_effect=capture):
            _, path = self.build(status='implementing')
        self.assertEqual(path.read_text(), generated[0].replace('Status: planned', 'Status: implementing', 1))

    def test_policy_block_is_complete_fresh_and_does_not_change_repo_defaults(self):
        first = review_policy_config()
        self.assertEqual(first, {'enabled': True, 'delivery_mode': 'targeted'})
        first['enabled'] = False
        self.assertTrue(review_policy_config()['enabled'])
        self.assertEqual(review_policy_config(delivery_mode='universal')['delivery_mode'], 'universal')
        with tempfile.TemporaryDirectory() as temp:
            root = _make_repo(Path(temp))
            self.assertNotIn('wave_review', json.loads((root / 'docs/workflow-config.json').read_text()))


class DeclarationCensusTests(unittest.TestCase):
    def test_every_retained_literal_has_its_own_reasoned_classification(self):
        found = set()
        failures = []
        for path in Path(__file__).parent.rglob('*.py'):
            sites = declaration_sites(path.read_text())
            if sites:
                found.add(path.name)
            failures.extend(f'{path.name}:{line}' for line, valid in sites if not valid)
        self.assertTrue({'test_review_evidence.py', 'test_docs_lint.py'} <= found, found)
        self.assertEqual(failures, [])

    def test_unrelated_helper_or_comment_cannot_exempt_a_site(self):
        raw = 'value = ' + repr(DECLARATION) + '\n'
        for source in (raw, 'make_declared_wave(srv, root, "other")\n' + raw,
                       '# negative-fixture: reason\n\n' + raw,
                       '# negative-fixture:\n' + raw,
                       '# unrelated: reason\n' + raw):
            with self.subTest(source=source):
                self.assertEqual([valid for _, valid in declaration_sites(source)], [False])

    def test_classifications_and_multiline_and_fstring_literal_segments(self):
        for kind in ('negative-fixture', 'component-fixture', 'producer-fixture', 'declaration-check'):
            for literal in (repr(DECLARATION), '"""prefix\n' + DECLARATION + '\n"""',
                            'f"' + DECLARATION + ' {name}"'):
                source = f'# {kind}: the represented contract is the test subject\nvalue = {literal}\n'
                self.assertEqual([valid for _, valid in declaration_sites(source)], [True])
        source = '# component-fixture: only the first literal\na=' + repr(DECLARATION) + '\nb=' + repr(DECLARATION)
        self.assertEqual([valid for _, valid in declaration_sites(source)], [True, False])

"""Config gate contract tests using real lifecycle producers and bounded subprocesses."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import ExitStack
from server_tools_support import load_server
import vocabulary_profile
from test_lifecycle_golden import (_make_repo, _build_one, _write_config, _WAVE_REVIEW_CONFIG,
    seed_state, _stub_validate, _stub_garden)


class PhaseGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        self.config = copy.deepcopy(_WAVE_REVIEW_CONFIG)
        self.config['sensors'] = [{'name': 'release-check', 'dimension': 'correctness',
            'command': [sys.executable, '-c', 'print("release passed")']}]
        _write_config(self.root, self.config)
        self.wave_md, self.wave = _build_one(self.srv, self.root, 'sensor-fixture', status='active')
        # Wave 1zoju (1zodx): the change document's header carries its status
        # from the start, so a later status change moves no receipt input.
        doc = self.change_doc()
        title, rest = doc.read_text().split('\n', 1)
        doc.write_text(f'{title}\n\n{vocabulary_profile.MEMBER_STATUS_LABEL}: `planned`\n{rest}')
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in [('run_validate', _stub_validate), ('run_garden', _stub_garden),
                ('_run_post_write_lint', lambda *a, **k: {'mode': 'stubbed'})]:
            self.stack.enter_context(patch.object(self.srv, name, value))

    def declare(self, phase='close', script=None):
        self.config['phase_gates'] = {phase: {'required_sensors': ['release-check']}}
        if script is not None:
            self.config['sensors'][0]['command'] = [sys.executable, '-c', script]
        _write_config(self.root, self.config)
        seed_state(self.srv, self.root, self.wave, ('wave-council-readiness', 'code-reviewer'))

    def clean_close(self, script=None, command=None):
        """The delivery-approved close fixture, reusing the landed recipe.

        Wave 1yd98 needs this for every execution-path case: the precondition
        withholds sensors on a blocked close, so a failing, timing-out or
        unlaunchable sensor can only be observed on a close with no blocking
        diagnostic.
        """
        from test_lifecycle_gates import LifecycleGateBehaviorTests
        # The command is set before `declare`, not after: writing the config
        # rotates the review-policy receipt, so a later write would lapse the
        # approvals `declare` and `delivery_approvals` have just recorded.
        if command is not None:
            self.config['sensors'][0]['command'] = command
        self.declare(script=script)
        gates = self.srv.lifecycle_gates
        ctx = gates.GateContext(self.root, self.wave_md, self.wave_md.read_text(),
                                'create', _stub_validate(self.root), 'close')
        helper = LifecycleGateBehaviorTests()
        helper.srv = self.srv
        helper.delivery_approvals(ctx)
        text = self.wave_md.read_text()
        label = vocabulary_profile.MEMBER_STATUS_LABEL
        self.wave_md.write_text(text.replace(f'{label}: `planned`', f'{label}: `complete`'))
        self.match_doc_status('complete')

    def match_doc_status(self, status):
        """Wave 1zoju (1zodx): close refuses status drift, so the change
        document's header carries the same status as its wave record."""
        label = vocabulary_profile.MEMBER_STATUS_LABEL
        doc = self.change_doc()
        doc.write_text(doc.read_text().replace(f'{label}: `planned`', f'{label}: `{status}`', 1))

    def change_doc(self):
        return next(p for p in self.wave_md.parent.glob('*.md') if p.name != self.wave_md.name)

    def codes(self, response):
        return [d['code'] for d in response.get('diagnostics', [])]

    def test_absent_digest_is_pre_change_capture(self):
        import review_policy
        kwargs = dict(wave_review={'enabled': True, 'delivery_mode': 'targeted'},
            project_lanes=['code-reviewer'], review_policies={},
            changes=[('abcde-ref fixture', 'ref', b'# Fixture\n\n## Requirements\nKeep policy stable.\n')],
            requested_lanes=[])
        expected = 'edd395ae2a8fcd8cc1d983e1b73334e381721f1ad1bb0b2f306eb8476e7325fd'
        for optional in ({}, {'phase_gates': None}, {'phase_gates': {}}):
            self.assertEqual(review_policy.policy_input_digest(**kwargs, **optional), expected)

    def test_schema_errors_lint_and_prepare_without_lint_subprocess(self):
        from wave_lint_lib.core_validators import check_workflow_config
        cases = [({'close': {'required_lanes': 'security-reviewer'}}, 'phase_gates.close.required_lanes'),
            ({'review': {}}, 'phase_gates.review'),
            ({'prepare': {'mystery': []}}, 'phase_gates.prepare.mystery'),
            ({'close': {'required_sensors': ['absent']}}, 'phase_gates.close.required_sensors'),
            ({'close': {'required_sensors': 'release-check'}}, 'phase_gates.close.required_sensors')]
        for gates, path in cases:
            with self.subTest(path=path):
                self.config['phase_gates'] = gates
                _write_config(self.root, self.config)
                self.assertTrue(any(path in e for e in check_workflow_config(self.root)))
                response = self.srv.wf_prepare_wave_response(self.root, self.wave, mode='ready')
                self.assertEqual(response['status'], 'error', response)
                self.assertIn(path, json.dumps(response))
                self.assertEqual(response['data']['configured_gates'], [])
        self.config['phase_gates'] = {'close': {'required_sensors': ['release-check']}}
        for sensors, path in [({'retrieval_posture': {}}, 'sensors'),
                ([{'name': 'release-check', 'command': 'echo unsafe'}], 'command')]:
            self.config['sensors'] = sensors
            _write_config(self.root, self.config)
            self.assertTrue(any(path in e for e in check_workflow_config(self.root)))
            response = self.srv.wf_prepare_wave_response(self.root, self.wave, mode='ready')
            self.assertEqual(response['status'], 'error', response)
        self.config['wave_review'] = {'enabled': 'bad'}
        self.config['phase_gates'] = {'review': {}}
        _write_config(self.root, self.config)
        errors = check_workflow_config(self.root)
        self.assertTrue(any('wave_review' in e for e in errors))
        self.assertTrue(any('phase_gates.review' in e for e in errors))

    def test_dict_sensors_without_required_gate_remains_tolerated(self):
        import review_policy
        for gates in (None, {}, {'close': {}}):
            config = {'sensors': {'retrieval_posture': {}}}
            if gates is not None:
                config['phase_gates'] = gates
            self.assertEqual(review_policy.normalize_phase_gates(config)[1], ())

    def test_blocked_close_withholds_the_sensor(self):
        """1yd98 AC-1: four cases, with the positive control sharing one bound spy."""
        import sensor_runner
        sentinel = self.root / 'sensor-ran.txt'
        script = f'from pathlib import Path; Path({str(sentinel)!r}).write_text("ran")'

        # Case 1: a close carrying blocking diagnostics withholds the sensor.
        self.declare(script=script)
        with patch.object(sensor_runner, 'run_sensor', wraps=sensor_runner.run_sensor) as run:
            blocked = self.srv.wf_close_wave_response(self.root, self.wave, mode='create')
            self.assertEqual(run.call_count, 0)
            self.assertFalse(sentinel.exists())
            self.assertIn('missing_operator_signoff', self.codes(blocked))
            rows = blocked['data']['configured_gates']
            self.assertEqual([row['outcome'] for row in rows], ['would_run'])
            advisories = [d for d in blocked['diagnostics'] if d['code'] == 'phase_sensor_not_executed']
            self.assertEqual(len(advisories), 1)
            self.assertTrue(advisories[0]['advisory'])
            self.assertIn('blocking diagnostics', advisories[0]['message'])
            self.assertNotIn('read-only', advisories[0]['message'])

            # Positive control, same fixture and same sensor with the blockers
            # removed: the sentinel must appear, so its absence above is
            # meaningful rather than absent for an unrelated reason.  The spy is
            # the same bound name in the same function, which is what the landed
            # patch census accepts.
            self.clean_close(script=script)
            clean = self.srv.wf_close_wave_response(self.root, self.wave, mode='create')
            run.assert_called_once()
            self.assertTrue(sentinel.exists())
            self.assertEqual(clean['data']['configured_gates'][0]['outcome'], 'passed')

    def test_blocked_read_only_close_still_names_read_only(self):
        """1yd98 AC-1 case 3: read-only takes precedence over blocked."""
        self.declare()
        response = self.srv.wf_close_wave_response(self.root, self.wave, mode='dry_run')
        advisory = next(d for d in response['diagnostics'] if d['code'] == 'phase_sensor_not_executed')
        self.assertIn('read-only', advisory['message'])
        self.assertNotIn('blocking diagnostics', advisory['message'])

    def test_blocker_raised_inside_the_hard_gate_loop_withholds_the_sensor(self):
        """1yd98 AC-1 case 4: the keyword is computed after the loop, not before.

        The only blocking diagnostic here is produced by `close_checkbox_gate`,
        which runs inside the narrowed loop.  A keyword computed before the loop
        reads not-blocked, the sensor executes, and this case is the sole
        detector of that shape.
        """
        import sensor_runner
        sentinel = self.root / 'inloop-sensor-ran.txt'
        self.clean_close(script=f'from pathlib import Path; Path({str(sentinel)!r}).write_text("ran")')
        doc = self.change_doc()
        doc.write_text(doc.read_text().replace('- [x] AC-1:', '- [ ] AC-1:'), encoding='utf-8')
        # inert-by-design: this path must never reach the runner; the sentinel is
        # the primary oracle and the spy's absence assertion is its corroboration.
        with patch.object(sensor_runner, 'run_sensor', wraps=sensor_runner.run_sensor) as run:
            response = self.srv.wf_close_wave_response(self.root, self.wave, mode='create')
            run.assert_not_called()
        self.assertFalse(sentinel.exists())
        blocking = [d['code'] for d in response['diagnostics'] if d.get('advisory') is not True]
        self.assertEqual(blocking, ['silent_unchecked_items_at_close'])
        self.assertEqual(response['data']['configured_gates'][0]['outcome'], 'would_run')

    def test_advisory_only_close_still_executes_its_sensors(self):
        """1yd98 AC-2: an advisory diagnostic must not satisfy the precondition."""
        import sensor_runner
        self.clean_close()
        warned = dict(_stub_validate(self.root), warnings=['fixture advisory'])
        with patch.object(self.srv, 'run_validate', lambda *a, **k: warned), \
             patch.object(sensor_runner, 'run_sensor', wraps=sensor_runner.run_sensor) as run:
            response = self.srv.wf_close_wave_response(self.root, self.wave, mode='create')
            run.assert_called_once()
        self.assertEqual(response['data']['configured_gates'][0]['outcome'], 'passed')

    def test_misdeclared_sensor_on_a_blocked_close_still_classifies_invalid(self):
        """1yd98 AC-3: both misdeclaration forms survive the precondition."""
        import sensor_runner
        for label, mutate in (
            ('unknown name', lambda: self.config['phase_gates'].__setitem__(
                'close', {'required_sensors': ['absent-sensor']})),
            ('non-list command', lambda: self.config['sensors'][0].__setitem__(
                'command', 'echo not permitted')),
        ):
            with self.subTest(form=label):
                self.setUp()
                self.declare()
                mutate()
                _write_config(self.root, self.config)
                # inert-by-design: a misdeclared sensor is refused before any spawn.
                with patch.object(sensor_runner, 'run_sensor') as run:
                    response = self.srv.wf_close_wave_response(self.root, self.wave, mode='create')
                    run.assert_not_called()
                self.assertIn('phase_sensor_invalid', self.codes(response))
                invalid = next(d for d in response['diagnostics'] if d['code'] == 'phase_sensor_invalid')
                self.assertIsNot(invalid.get('advisory'), True)
                self.assertEqual(response['data']['configured_gates'][0]['outcome'], 'invalid')

    def test_close_passes_with_real_delivery_approvals(self):
        from test_lifecycle_gates import LifecycleGateBehaviorTests
        self.declare()
        gates = self.srv.lifecycle_gates
        ctx = gates.GateContext(self.root, self.wave_md, self.wave_md.read_text(), 'create', _stub_validate(self.root), 'close')
        helper = LifecycleGateBehaviorTests()
        helper.srv = self.srv
        helper.delivery_approvals(ctx)
        # The producer admits a planned change; this fixture represents completed delivery.
        text = self.wave_md.read_text()
        label = vocabulary_profile.MEMBER_STATUS_LABEL
        self.wave_md.write_text(text.replace(f'{label}: `planned`', f'{label}: `complete`'))
        self.match_doc_status('complete')
        with patch.object(self.srv, '_auto_populate_memory_for_wave', return_value={}) as memory, \
             patch.object(self.srv, '_maybe_optimize_index_on_close', return_value={}) as optimize:
            response = self.srv.wf_close_wave_response(self.root, self.wave, mode='create')
            memory.assert_called_once()
            optimize.assert_called_once()
        self.assertNotEqual(response['status'], 'error', response)
        self.assertEqual(response['data']['configured_gates'][0]['outcome'], 'passed')
        self.assertIn('Status: closed', self.wave_md.read_text())

    def test_close_timeout_and_invalid_command_fail_closed(self):
        import sensor_runner
        # 1yd98 AC-4: the timeout half is rehomed onto the clean fixture, because
        # the precondition withholds sensors on a blocked close.  The invalid half
        # below classifies before the mutating branch and needs no rehoming.
        self.clean_close(script='import time; time.sleep(2)')
        with patch.object(self.srv.lifecycle_gate_support, 'subprocess_ops_timeout_seconds', return_value=0.03) as timeout:
            response = self.srv.wf_close_wave_response(self.root, self.wave, mode='create')
            timeout.assert_called_once()
        diag = next(d for d in response['diagnostics'] if d['code'] == 'phase_sensor_failed')
        self.assertIsNone(diag['exit_code'])
        self.assertIn('0.03', diag['output_summary'])
        self.config['sensors'][0]['command'] = 'echo not permitted'
        _write_config(self.root, self.config)
        # inert-by-design: read-only or invalid input must never execute the runner.
        with patch.object(sensor_runner, 'run_sensor') as run:
            response = self.srv.wf_close_wave_response(self.root, self.wave, mode='create')
            run.assert_not_called()
        self.assertIn('phase_sensor_invalid', self.codes(response))
        self.assertEqual(response['data']['configured_gates'][0]['outcome'], 'invalid')
        self.assertIsNone(response['data']['configured_gates'][0]['duration_ms'])

    def test_prepare_ready_executes_and_read_only_modes_do_not_spawn(self):
        import sensor_runner
        self.declare('prepare')
        with patch.object(sensor_runner, 'run_sensor', wraps=sensor_runner.run_sensor) as run:
            response = self.srv.wf_prepare_wave_response(self.root, self.wave, mode='ready')
            run.assert_called_once()
        self.assertEqual(response['data']['configured_gates'][0]['outcome'], 'passed')
        for mode in ('dry_run', 'evaluate'):
            with self.subTest(mode=mode), patch.object(sensor_runner, 'run_sensor') as run:
                response = self.srv.wf_prepare_wave_response(self.root, self.wave, mode=mode)
                run.assert_not_called()
            self.assertEqual(response['data']['configured_gates'], [{
                'phase': 'prepare', 'gate': 'release-check',
                'source': 'phase_gates.prepare.required_sensors', 'outcome': 'would_run', 'duration_ms': None}])
            self.assertTrue(next(d for d in response['diagnostics'] if d['code'] == 'phase_sensor_not_executed')['advisory'])
        self.config['phase_gates'] = {'close': {'required_sensors': ['release-check']}}
        _write_config(self.root, self.config)
        # inert-by-design: read-only or invalid input must never execute the runner.
        with patch.object(sensor_runner, 'run_sensor') as run:
            response = self.srv.wf_close_wave_response(self.root, self.wave, mode='dry_run')
            run.assert_not_called()
        self.assertEqual(response['data']['configured_gates'][0]['outcome'], 'would_run')

    def test_sensor_runner_rows_timeout_and_default(self):
        import sensor_runner
        self.config['subprocess_ops'] = {'sensor_timeout_seconds': 0.03}
        self.config['sensors'][0]['command'] = [sys.executable, '-c', 'import time; time.sleep(2)']
        _write_config(self.root, self.config)
        # Inject subsecond effective bound because the public config reader validates integral seconds.
        with patch.object(self.srv, 'subprocess_ops_timeout_seconds', return_value=0.03) as timeout:
            response = self.srv.wf_run_sensors_response(self.root)
            timeout.assert_called_once()
        row = response['data']['results'][0]
        self.assertFalse(row['passed'])
        self.assertIsNone(row['exit_code'])
        self.assertIn('0.03', row['output_summary'])
        self.assertGreaterEqual(row['duration_ms'], 0)
        self.config.pop('subprocess_ops')
        self.config['sensors'][0]['command'] = [sys.executable, '-c', 'print("ok")']
        _write_config(self.root, self.config)
        with patch.object(sensor_runner, 'run_sensor', wraps=sensor_runner.run_sensor) as run:
            response = self.srv.wf_run_sensors_response(self.root)
            run.assert_called_once()
            self.assertEqual(run.call_args.kwargs['timeout_seconds'], 120)
        self.assertTrue(response['data']['results'][0]['passed'])
        self.assertIn('duration_ms', response['data']['results'][0])

    def test_policy_edits_stale_both_prepare_and_review(self):
        for mutation in ('phase', 'command'):
            with self.subTest(mutation=mutation):
                self.declare('close')
                if mutation == 'phase':
                    self.config['phase_gates']['prepare'] = {'required_sensors': ['release-check']}
                else:
                    self.config['sensors'][0]['command'][-1] = 'print("different")'
                _write_config(self.root, self.config)
                prepare = self.srv.wf_prepare_wave_response(self.root, self.wave, mode='dry_run')
                self.assertIn('review_policy_receipt_stale', self.codes(prepare))
                stale = next(d for d in prepare['diagnostics'] if d['code'] == 'review_policy_receipt_stale')
                self.assertTrue(stale['advisory'])
                review = self.srv.wf_review_wave_response(self.root, self.wave, phase='prepare')
                self.assertIn('review_policy_receipt_stale', self.codes(review))
                self.assertEqual(review['data']['configured_gates'], [])

    def test_launch_failure_reports_failed_and_never_closes(self):
        """1yd98 AC-4: rehomed onto the clean fixture, and counts calls and rows.

        The per-sensor call and row counts are what catch an implementation that
        leaves the hard-gate loop iterating the whole tuple and adds the explicit
        call after it, which would spawn every declared sensor twice.
        """
        import sensor_runner
        self.clean_close(command=[str(self.root / 'no-such-executable')])
        with patch.object(sensor_runner, 'run_sensor', wraps=sensor_runner.run_sensor) as run:
            response = self.srv.wf_close_wave_response(self.root, self.wave, mode='apply')
            run.assert_called_once()
        self.assertIn('phase_sensor_failed', self.codes(response))
        rows = response['data']['configured_gates']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['outcome'], 'failed')
        # AC-4 asks for `passed` or `failed` reported with `duration_ms`; the
        # failing path carries it too, so assert it here and not only on success.
        self.assertIsNotNone(rows[0]['duration_ms'])
        self.assertGreaterEqual(rows[0]['duration_ms'], 0)
        self.assertIn('Status: active', self.wave_md.read_text())

    def test_clean_close_executes_exactly_once_per_declared_sensor(self):
        """1yd98 AC-4 and AC-6: the execution path survives, on `create` and `apply`."""
        import sensor_runner
        for mode in ('create', 'apply'):
            with self.subTest(mode=mode):
                self.setUp()
                self.clean_close()
                with patch.object(sensor_runner, 'run_sensor', wraps=sensor_runner.run_sensor) as run:
                    response = self.srv.wf_close_wave_response(self.root, self.wave, mode=mode)
                    run.assert_called_once()
                rows = response['data']['configured_gates']
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['outcome'], 'passed')
                self.assertGreaterEqual(rows[0]['duration_ms'], 0)
                self.assertIn('Status: closed', self.wave_md.read_text())

    def test_apply_alias_withholds_the_sensor_on_a_blocked_close(self):
        """1yd98 AC-6: the alias behaves identically on the blocked path."""
        import sensor_runner
        self.declare()
        # inert-by-design: the alias must withhold the sensor exactly as create does.
        with patch.object(sensor_runner, 'run_sensor', wraps=sensor_runner.run_sensor) as run:
            response = self.srv.wf_close_wave_response(self.root, self.wave, mode='apply')
            run.assert_not_called()
        self.assertEqual(response['data']['configured_gates'][0]['outcome'], 'would_run')

    def test_prepare_failure_retains_receipt_but_refuses_readiness(self):
        import sensor_runner
        self.declare('prepare', script='raise SystemExit(8)')
        with patch.object(sensor_runner, 'run_sensor', wraps=sensor_runner.run_sensor) as run:
            response = self.srv.wf_prepare_wave_response(self.root, self.wave, mode='ready')
            run.assert_called_once()
        self.assertEqual(response['status'], 'error')
        self.assertIn('phase_sensor_failed', self.codes(response))
        authority = self.srv.resolve_review_authority(self.root, self.wave_md, wave_text=self.wave_md.read_text())
        self.assertIsNotNone(self.srv.current_policy_receipt(authority.records))

    def test_layout_error_envelopes_and_review_never_spawn(self):
        import record_paths
        import sensor_runner
        self.declare()
        # inert-by-design: layout refusal must return before sensor execution.
        with patch.object(record_paths, 'WAVES_ROOT', '../outside'), \
             patch.object(sensor_runner, 'run_sensor') as run:
            for method in (self.srv.wf_prepare_wave_response, self.srv.wf_review_wave_response, self.srv.wf_close_wave_response):
                response = method(self.root, self.wave)
                self.assertEqual(response['status'], 'error')
                self.assertEqual(response['data']['configured_gates'], [])
            run.assert_not_called()

    def test_timeout_config_finite_positive_or_caller_default(self):
        support = self.srv.lifecycle_gate_support
        for value in (float('inf'), float('-inf'), float('nan'), 0, -1, True, '2'):
            self.config['subprocess_ops'] = {'sensor_timeout_seconds': value}
            _write_config(self.root, self.config)
            self.assertEqual(support.subprocess_ops_timeout_seconds(self.root, 'sensor', default=120), 120)
        self.config['subprocess_ops'] = {'sensor_timeout_seconds': 0.125}
        _write_config(self.root, self.config)
        self.assertEqual(support.subprocess_ops_timeout_seconds(self.root, 'sensor', default=120), 0.125)

    def test_early_errors_have_empty_provenance(self):
        for method, kwargs in [(self.srv.wf_prepare_wave_response, {'mode': 'nonsense'}),
                (self.srv.wf_prepare_wave_response, {'mode': 'dry_run'}),
                (self.srv.wf_review_wave_response, {}),
                (self.srv.wf_close_wave_response, {'mode': 'dry_run'})]:
            response = method(self.root, 'zzzzz absent', **kwargs)
            self.assertEqual(response['status'], 'error')
            self.assertEqual(response['data']['configured_gates'], [])


class PhaseLaneTests(unittest.TestCase):
    """Wave 1zlu1 (change 1zlu4): `phase_gates.<phase>.required_lanes`."""

    @classmethod
    def setUpClass(cls):
        cls.srv = load_server()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = _make_repo(Path(self.tmp.name))
        self.config = copy.deepcopy(_WAVE_REVIEW_CONFIG)
        _write_config(self.root, self.config)
        self.wave_md = self.wave = None
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for name, value in [('run_validate', _stub_validate), ('run_garden', _stub_garden),
                ('_run_post_write_lint', lambda *a, **k: {'mode': 'stubbed'})]:
            self.stack.enter_context(patch.object(self.srv, name, value))

    def configure(self, phase_gates=None, **extra):
        self.config = copy.deepcopy(_WAVE_REVIEW_CONFIG)
        if phase_gates is not None:
            self.config['phase_gates'] = phase_gates
        self.config.update(extra)
        _write_config(self.root, self.config)
        if self.wave is None:
            # The record's review-status projection is rendered from the
            # config, so the wave is built after the first configuration.
            self.wave_md, self.wave = _build_one(self.srv, self.root, 'lane-fixture', status='active')

    def ready(self, approvals=('wave-council-readiness', 'code-reviewer')):
        seed_state(self.srv, self.root, self.wave, approvals)
        return self.srv.wf_prepare_wave_response(self.root, self.wave, mode='ready')

    def approve(self, key, phase='delivery'):
        from test_lifecycle_golden import _approval_evidence, _APPROVAL_INTEGRITY
        response = self.srv.wf_review_event_response(
            self.root, self.wave, 'approval', key, f'lane-{key}-{phase}', mode='create',
            signoff_key=key, approval_phase=phase, fresh_context=True, independent=True,
            evidence=_approval_evidence(key), integrity_checks=dict(_APPROVAL_INTEGRITY))
        self.assertNotEqual(response['status'], 'error', response)

    def delivery(self):
        from test_lifecycle_gates import LifecycleGateBehaviorTests
        gates = self.srv.lifecycle_gates
        ctx = gates.GateContext(self.root, self.wave_md, self.wave_md.read_text(), 'create',
                                _stub_validate(self.root), 'close')
        helper = LifecycleGateBehaviorTests()
        helper.srv = self.srv
        helper.delivery_approvals(ctx)

    def close_missing(self):
        response = self.srv.wf_close_wave_response(self.root, self.wave, mode='dry_run')
        return [d for d in response['diagnostics'] if d['code'] == 'missing_required_lane']

    def codes(self, response):
        return [d['code'] for d in response.get('diagnostics') or []]

    def line(self, label):
        import re
        match = re.search(rf'(?m)^- Required {label} lanes: (.*)$', self.wave_md.read_text())
        return match.group(1) if match else None

    def phase_finding(self, lanes, recheck_lanes, *, finding_id, run_kind):
        from test_lifecycle_golden import _APPROVAL_INTEGRITY

        judgment = dict(
            validation_status='real', scope_relation='admitted', introduced_or_worsened_by_wave=True,
            contract_relevance='required_ac', supported_reachability=True, attacker_reachability=False,
            authority_domain='none', authority_delta='none', observable_impact='material', containment='none',
            fix_risk='lower', optional_value='none', repair_scope_bounded=True, repair_safety='safe',
            benefit_vs_fix_risk='greater', rejection_basis='none', disposition='do_now',
            repair_execution_state='pending')
        evidence = {key: 'generic phase-isolation fixture' for key in (
            'proposition', 'failure_condition', 'public_path', 'command_or_fixture', 'expected', 'observed',
            'artifact_or_test_id', 'known_bad_detection_method', 'limitations', 'safety_and_authorization',
            'disposition_rationale')}
        result = self.srv.wf_review_event_response(
            self.root, self.wave, 'finding', 'qa-reviewer', 'phase-isolation-finding', mode='create',
            finding_id=finding_id, run_kind=run_kind, cycle=0, judgment=judgment,
            evidence=evidence, source_lanes=lanes, blocking_required_lanes=lanes,
            approval_recheck_lanes=list(recheck_lanes),
            integrity_checks=dict(_APPROVAL_INTEGRITY))
        self.assertNotEqual(result['status'], 'error', result)

    def test_delivery_findings_allow_real_readiness_admission_but_block_close(self):
        """207lx: canonical producers, paired consumers, and unchanged ledger bytes."""
        import review_evidence as evidence_module

        lanes = ['code-reviewer', 'qa-reviewer', 'architecture-reviewer',
                 'security-reviewer', 'custom-reviewer']
        ready_keys = lanes + [evidence_module.COUNCIL_READINESS_SIGNOFF_KEY]
        delivery_keys = lanes + [evidence_module.COUNCIL_DELIVERY_SIGNOFF_KEY]
        self.configure({'prepare': {'required_lanes': ['custom-reviewer']}},
                       required_review_lanes=lanes[:-1])
        self.assertNotEqual(self.ready(approvals=tuple(ready_keys))['status'], 'error')
        self.phase_finding(lanes, list(dict.fromkeys(ready_keys + delivery_keys)),
                           finding_id='delivery-fix', run_kind='initial_delivery')
        ledger = self.wave_md.parent / 'events.jsonl'
        before = ledger.read_bytes()
        records = [json.loads(line) for line in before.splitlines()]
        for phase, keys, expected in (('readiness', ready_keys, 'approved'),
                                      ('delivery', delivery_keys, 'withheld')):
            projection = evidence_module.review_authority_projection(records, keys, approval_phase=phase)
            self.assertEqual({row['state'] for row in projection['status_rows']}, {expected})
        authority = evidence_module.resolve_review_authority(self.root, self.wave_md)
        gates = self.srv.lifecycle_gates
        ctx = gates.GateContext(self.root, self.wave_md, self.wave_md.read_text(), 'ready',
                               _stub_validate(self.root), 'prepare')
        gate = gates.review_lanes_gate(ctx, authority=authority, required_lanes=lanes)
        self.assertEqual(gate.diagnostics, [])
        _authority, pending = self.srv._prepare_lane_review_state(
            self.root, self.wave_md, self.wave_md.read_text())
        self.assertEqual(pending, [])
        admission = self.srv.wf_implement_wave_response(self.root, self.wave, mode='dry_run')
        self.assertNotEqual(admission['status'], 'error', admission)
        close = self.srv.wf_close_wave_response(self.root, self.wave, mode='dry_run')
        self.assertEqual(close['status'], 'error', close)
        self.assertIn('missing_required_lane', self.codes(close))
        self.assertEqual(ledger.read_bytes(), before)

    def test_readiness_finding_keeps_recorded_approval_withheld_in_every_consumer(self):
        import review_evidence as evidence_module

        self.configure(required_review_lanes=['code-reviewer'])
        self.assertNotEqual(self.ready(approvals=(
            evidence_module.COUNCIL_READINESS_SIGNOFF_KEY, 'code-reviewer'))['status'], 'error')
        self.phase_finding(['code-reviewer'], ['code-reviewer'],
                           finding_id='plan-fix', run_kind='readiness')
        ledger = self.wave_md.parent / 'events.jsonl'
        before = ledger.read_bytes()
        review = self.srv.wf_review_wave_response(self.root, self.wave, phase='prepare')
        admission = self.srv.wf_implement_wave_response(self.root, self.wave, mode='dry_run')
        prepare = self.srv.wf_prepare_wave_response(self.root, self.wave, mode='dry_run')
        self.assertEqual(admission['status'], 'error', admission)
        consumers = {
            'review': review['data']['lane_results'],
            'implementation': next(d['lane_results'] for d in admission['diagnostics']
                                   if d['code'] == 'prepare_review_incomplete'),
            'prepare advisory': next(d['lane_results'] for d in prepare['diagnostics']
                                     if d['code'] == 'readiness_lane_approvals_missing'),
        }
        for consumer, rows in consumers.items():
            with self.subTest(consumer=consumer):
                row = next(row for row in rows if row['lane'] == 'code-reviewer')
                self.assertTrue(row['approval_recorded'])
                self.assertFalse(row['approval_current'])
                self.assertEqual(row['approval_state'], 'withheld')
                self.assertEqual(tuple(row['blocking_finding_ids']), ('plan-fix',))
                self.assertTrue(row['has_unresolved_blocking_findings'])
                self.assertIn('plan-fix', row['why'])
                self.assertIn('independent reverification', row['next_action'])
                self.assertNotEqual(row['next_action'], 'record approval evidence for code-reviewer')
        self.assertEqual(ledger.read_bytes(), before)

    # AC-1 --------------------------------------------------------------
    def test_required_lanes_validation(self):
        import review_policy
        from wave_lint_lib.core_validators import check_workflow_config
        ok = {'phase_gates': {'prepare': {'required_lanes': ['design-review']},
                              'close': {'required_lanes': ['release-review'], 'required_sensors': []}}}
        normalized, errors = review_policy.normalize_phase_gates(ok)
        self.assertEqual(errors, ())
        self.assertEqual(normalized['prepare']['required_lanes'], ['design-review'])
        self.assertEqual(normalized['close']['required_lanes'], ['release-review'])
        cases = [({'close': {'required_lanes': 'release-review'}}, 'phase_gates.close.required_lanes must be a list'),
                 ({'close': {'required_lanes': ['']}}, 'phase_gates.close.required_lanes[0] must be a non-empty lane name'),
                 ({'prepare': {'required_lanes': [5]}}, 'phase_gates.prepare.required_lanes[0] must be a non-empty lane name'),
                 ({'close': {'required_lanes': ['a', 'a']}}, "phase_gates.close.required_lanes[1]: duplicate lane 'a'"),
                 ({'close': {'required_lanes': [' x', 'x']}}, "phase_gates.close.required_lanes[1]: duplicate lane 'x'"),
                 ({'close': {'mystery': []}}, 'phase_gates.close.mystery: unknown field'),
                 ({'review': {'required_lanes': ['a']}}, 'phase_gates.review: unknown phase')]
        for gates, message in cases:
            with self.subTest(message=message):
                self.assertIn(message, review_policy.normalize_phase_gates({'phase_gates': gates})[1])
                self.configure(gates)
                self.assertIn(f'docs/workflow-config.json: {message}', check_workflow_config(self.root))

    # AC-2 --------------------------------------------------------------
    def test_delivery_only_lane(self):
        self.configure({'close': {'required_lanes': ['release-review']}})
        response = self.ready()
        self.assertNotEqual(response['status'], 'error', response)
        self.assertEqual(response['data']['delivery_only_lanes'], ['release-review'])
        self.assertEqual(response['data']['pending_readiness_lanes'], [])
        self.assertEqual(self.line('review'), 'code-reviewer')
        self.assertEqual(self.line('delivery'), 'code-reviewer, release-review')
        _authority, missing = self.srv._prepare_lane_review_state(self.root, self.wave_md, self.wave_md.read_text())
        self.assertEqual(missing, [])
        review = self.srv.wf_review_wave_response(self.root, self.wave, phase='implementation')
        self.assertIn('release-review', review['data']['required_lanes'])
        self.delivery()
        self.assertIn('release-review', self.close_missing()[0]['message'])
        self.approve('release-review')
        self.assertEqual(self.close_missing(), [])

    def test_delivery_only_roster_is_not_reported_empty_at_review(self):
        """Delivery review F2: with no base lanes and one delivery-only lane,
        the implementation-phase advisory reads the delivery roster."""
        self.configure({'close': {'required_lanes': ['release-review']}}, required_review_lanes=[])
        response = self.ready(approvals=('wave-council-readiness',))
        self.assertNotEqual(response['status'], 'error', response)
        self.assertEqual(self.line('delivery'), 'release-review')
        review = self.srv.wf_review_wave_response(self.root, self.wave, phase='implementation')
        self.assertIn('release-review', review['data']['required_lanes'])
        self.assertNotIn('required_review_lanes_empty', self.codes(review))
        prepare_review = self.srv.wf_review_wave_response(self.root, self.wave, phase='prepare')
        self.assertIn('required_review_lanes_empty', self.codes(prepare_review))
        # Reverification nit 2: the readiness advisory names the delivery lanes.
        message = next(d['message'] for d in prepare_review['diagnostics']
                       if d['code'] == 'required_review_lanes_empty')
        self.assertIn('No readiness review lanes are required', message)
        self.assertIn('release-review', message)

    def test_readiness_only_lane(self):
        self.configure({'prepare': {'required_lanes': ['design-review']}})
        response = self.ready()
        self.assertNotEqual(response['status'], 'error', response)
        self.assertEqual(response['data']['pending_readiness_lanes'], ['design-review'])
        self.assertEqual(self.line('review'), 'code-reviewer, design-review')
        self.assertEqual(self.line('delivery'), 'code-reviewer')
        review = self.srv.wf_review_wave_response(self.root, self.wave, phase='implementation')
        self.assertNotIn('design-review', review['data']['required_lanes'])
        prepare_review = self.srv.wf_review_wave_response(self.root, self.wave, phase='prepare')
        self.assertIn('design-review', prepare_review['data']['required_lanes'])
        keys = self.srv._guided_review_signoff_keys(self.root, self.wave_md, self.wave_md.read_text(),
                                                    approval_phase='delivery')
        self.assertNotIn('design-review', keys)
        self.delivery()
        self.assertEqual(self.close_missing(), [])

    # AC-3 --------------------------------------------------------------
    def test_every_site_reads_the_pure_helper(self):
        self.configure()
        import review_policy
        import review_evidence
        self.ready()
        text = self.wave_md.read_text()

        def sentinel(config, phase):
            return [f'architecture-sentinel-{phase}']

        with patch.object(review_policy, 'project_lanes_for_phase', sentinel):
            change_ids = self.srv._extract_change_ids_from_wave_text(text)
            brief = self.srv._build_prepare_council_brief(self.wave, text, change_ids, typed=True)
            state, errors = self.srv._prepare_policy_state(self.root, self.wave_md, text, change_ids, brief)
            self.assertEqual(errors, ())
            self.assertIn('architecture-sentinel-prepare', state['required_lanes'])
            self.assertNotIn('architecture-sentinel-close', state['required_lanes'])
            self.assertIn('architecture-sentinel-close', state['delivery_lanes'])
            _authority, missing = self.srv._prepare_lane_review_state(self.root, self.wave_md, text)
            self.assertIn('architecture-sentinel-prepare', missing)
            readiness = self.srv._guided_review_signoff_keys(self.root, self.wave_md, text, approval_phase='readiness')
            delivery = self.srv._guided_review_signoff_keys(self.root, self.wave_md, text, approval_phase='delivery')
            self.assertIn('architecture-sentinel-prepare', readiness)
            self.assertNotIn('architecture-sentinel-close', readiness)
            self.assertIn('architecture-sentinel-close', delivery)
            self.assertNotIn('architecture-sentinel-prepare', delivery)
            for phase, expected in (('prepare', 'prepare'), ('implementation', 'close')):
                review = self.srv.wf_review_wave_response(self.root, self.wave, phase=phase)
                self.assertIn(f'architecture-sentinel-{expected}', review['data']['required_lanes'], phase)
            shared = self.srv.lifecycle_gates._evaluate_shared_delivery_state(
                self.root, self.wave_md, text, _stub_validate(self.root))
            self.assertIn('architecture-sentinel-close', shared['required_lanes'])
            self.assertNotIn('architecture-sentinel-prepare', shared['required_lanes'])
            coverage = self.srv._audit_harness_coverage(self.root)
            self.assertTrue(coverage['dimensions']['architecture']['covered'])
            keys = review_evidence.required_review_status_keys(self.root, text)
            self.assertIn('architecture-sentinel-prepare', keys)
            self.assertIn('architecture-sentinel-close', keys)
        override = review_evidence.required_review_status_keys(
            self.root, text, config_override={'required_review_lanes': ['override-lane']})
        self.assertIn('override-lane', override)
        file_keys = review_evidence.required_review_status_keys(self.root, '')
        self.assertIn('code-reviewer', file_keys)
        self.assertNotIn('code-reviewer', review_evidence.required_review_status_keys(
            self.root, '', config_override={'required_review_lanes': ['override-lane']}))

    # AC-4 --------------------------------------------------------------
    def test_delivery_line_written_only_when_rosters_differ(self):
        self.configure()
        replace = self.srv._replace_required_review_lanes
        text = '## Participants\n\n- Required review lanes: a\n- Required delivery lanes: a, b\n\n## Next\n'
        self.assertNotIn('Required delivery lanes', replace(text, ['a'], ['a']))
        self.assertIn('- Required review lanes: a\n- Required delivery lanes: a, c\n', replace(text, ['a'], ['a', 'c']))
        self.assertEqual(replace(text, ['a']), text.replace('- Required review lanes: a', '- Required review lanes: a'))
        self.ready()
        self.assertIsNone(self.line('delivery'))

    def test_existing_delivery_line_is_removed_when_rosters_become_equal(self):
        self.configure({'close': {'required_lanes': ['release-review']}})
        self.ready()
        self.assertIsNotNone(self.line('delivery'))
        self.configure()
        self.srv.wf_prepare_wave_response(self.root, self.wave, mode='ready')
        self.assertIsNone(self.line('delivery'))

    def _stale(self):
        return [d for d in self.srv.lifecycle_gate_support._review_policy_receipt_diagnostics(
            self.root, self.wave_md, self.wave_md.read_text()) if d['code'] == 'review_policy_receipt_stale']

    def test_roster_staleness_per_line(self):
        self.configure({'close': {'required_lanes': ['release-review']}})
        self.ready()
        self.assertEqual(self._stale(), [])
        original = self.wave_md.read_text()
        edits = {
            'hand-edited delivery line': original.replace(
                '- Required delivery lanes: code-reviewer, release-review', '- Required delivery lanes: code-reviewer'),
            'stale readiness line': original.replace(
                '- Required review lanes: code-reviewer', '- Required review lanes: code-reviewer, extra'),
            'deleted delivery line': original.replace(
                '- Required delivery lanes: code-reviewer, release-review\n', ''),
        }
        for label, edited in edits.items():
            with self.subTest(case=label):
                self.assertNotEqual(edited, original)
                self.wave_md.write_text(edited)
                self.assertTrue(self._stale(), label)
        self.wave_md.write_text(original)

    # AC-5 --------------------------------------------------------------
    def test_digest_unchanged_without_phase_gates(self):
        self.configure()
        import review_policy
        self.assertEqual(review_policy.REVIEW_POLICY_EVALUATOR_VERSION, 7)
        text = self.wave_md.read_text()
        change_ids = self.srv._extract_change_ids_from_wave_text(text)
        brief = self.srv._build_prepare_council_brief(self.wave, text, change_ids, typed=True)
        state, _errors = self.srv._prepare_policy_state(self.root, self.wave_md, text, change_ids, brief)
        changes = []
        for change_id in change_ids:
            body = (self.wave_md.parent / f'{change_id}.md').read_bytes()
            changes.append((change_id, change_id.split('-', 1)[0].rsplit('-', 1)[-1], body))
        # The pre-change computation: the base lane list, no phase_gates key.
        expected = review_policy.policy_input_digest(
            wave_review=state['policy'], project_lanes=['code-reviewer'], review_policies={},
            changes=changes, requested_lanes=review_policy.extract_requested_review_lanes(text))
        self.assertEqual(state['policy_input_digest'], expected)
        self.assertEqual(state['delivery_lanes'], state['required_lanes'])
        self.assertEqual(state['delivery_only_lanes'], [])
        self.configure({'close': {'required_lanes': ['release-review']}})
        moved, _ = self.srv._prepare_policy_state(self.root, self.wave_md, text, change_ids, brief)
        self.assertNotEqual(moved['policy_input_digest'], expected)

    # AC-6 --------------------------------------------------------------
    def test_non_list_required_review_lanes_is_a_config_error(self):
        import review_policy
        import review_evidence
        from wave_lint_lib.core_validators import check_workflow_config
        for value in ('code-reviewer', {'lane': 'code-reviewer'}):
            with self.subTest(value=value):
                self.configure(required_review_lanes=value)
                self.assertIn('docs/workflow-config.json: required_review_lanes must be a list',
                              check_workflow_config(self.root))
                with self.assertRaises(review_policy.ProjectLanesConfigError):
                    self.srv._read_project_required_review_lanes(self.root)
                with self.assertRaises(review_policy.ProjectLanesConfigError):
                    review_policy.project_lanes_for_phase(self.config, 'close')
                prepare = self.srv.wf_prepare_wave_response(self.root, self.wave, mode='ready')
                self.assertEqual(prepare['status'], 'error', prepare)
                self.assertIn('required_review_lanes must be a list', json.dumps(prepare))
                review = self.srv.wf_review_wave_response(self.root, self.wave, phase='implementation')
                self.assertIn('required_review_lanes_invalid', self.codes(review))
                close = self.srv.wf_close_wave_response(self.root, self.wave, mode='dry_run')
                self.assertIn('required_review_lanes_invalid', self.codes(close))
                coverage = self.srv._audit_harness_coverage(self.root)
                self.assertIn('required_review_lanes must be a list', coverage['config_error'])
                self.assertIsInstance(self.srv.wf_audit_response(self.root), dict)
        self.configure()
        del self.config['required_review_lanes']
        _write_config(self.root, self.config)
        self.assertEqual(self.srv._read_project_required_review_lanes(self.root), [])
        keys = review_evidence.required_review_status_keys(
            self.root, '', config_override={'required_review_lanes': [5, 'kept-lane']})
        self.assertIn('kept-lane', keys)
        self.assertNotIn('5', keys)


if __name__ == '__main__':
    unittest.main()

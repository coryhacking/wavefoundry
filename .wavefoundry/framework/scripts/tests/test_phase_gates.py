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
        self.wave_md.write_text(text.replace('Change Status: `planned`', 'Change Status: `complete`'))

    def change_doc(self):
        return next(p for p in self.wave_md.parent.glob('*.md') if p.name != 'wave.md')

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
        cases = [({'close': {'required_lanes': ['security-reviewer']}}, 'phase_gates.close.required_lanes'),
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
        self.wave_md.write_text(text.replace('Change Status: `planned`', 'Change Status: `complete`'))
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

if __name__ == '__main__':
    unittest.main()

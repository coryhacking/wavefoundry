"""Setup stamp writers and fresh-process convergence (wave 1yzcz, change 1yzcy).

The end-to-end cases run the fixture's own ``wf setup --check`` in a fresh
process against ``setup_ready_fixture``, so no readiness internals are patched on
the checked path.
"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / 'tests'))

import setup_readiness as readiness  # noqa: E402
import setup_ready_fixture  # noqa: E402


class _FixtureCase(unittest.TestCase):
    claude = False

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = setup_ready_fixture.build(self.root, claude=self.claude)
        self.stamp = self.root / '.wavefoundry/index/setup-state.json'

    def in_fixture_environment(self):
        """The fixture environment for in-process writers: clean of every recorded variable."""
        return patch.dict(os.environ, self.env, clear=True)

    def check(self):
        return setup_ready_fixture.check(self.root, self.env)


class FreshProcessConvergenceTests(_FixtureCase):
    def test_fixture_is_ready_and_check_never_writes_the_stamp(self):
        result = self.check()
        self.assertEqual(result['status'], 'ready', result)
        self.assertFalse(self.stamp.exists())

    def test_real_setup_order_converges_with_a_fresh_check(self):
        import setup_index

        with self.in_fixture_environment():
            with patch.object(setup_index.provider_policy, 'available_onnx_providers',
                              return_value=('CPUExecutionProvider',)), redirect_stdout(io.StringIO()):
                setup_index.report_embedding_provider_decision()
            self.assertIn(readiness.SETUP_SELECTED_ENV, os.environ)
            readiness.write_setup_stamp(self.root)
        recorded = json.loads(self.stamp.read_text())['environment']['variables']
        self.assertIsNotNone(recorded[readiness.SETUP_SELECTED_ENV])
        result = self.check()
        self.assertEqual(result['status'], 'ready', result)

    def test_adopted_baseline_reports_a_later_framework_change(self):
        with self.in_fixture_environment():
            self.assertTrue(readiness.adopt_setup_stamp(
                self.root, {'status': 'ready'}, readiness.capture_loaded_identity()))
        self.assertEqual(json.loads(self.stamp.read_text())['provenance'], 'adopted')
        self.assertEqual(self.check()['status'], 'ready')
        source = self.root / '.wavefoundry/framework/scripts/setup_index.py'
        source.write_text(source.read_text() + '\n# pulled framework update\n')
        result = self.check()
        self.assertEqual(result['status'], 'action_required', result)
        self.assertIn('setup_inputs_changed', [r['code'] for r in result['reasons']])


class ServerStartupAdoptionTests(_FixtureCase):
    def setUp(self):
        super().setUp()
        from server_tools_support import load_server, load_thin_runner

        load_server()
        self.runner = load_thin_runner()
        self.events = []

    def _main(self, argv, assessment):
        stamp = self.stamp

        class FakeMcp:
            def run(inner, *, transport):
                # The real transport never returns, so adoption must precede it.
                self.events.append(('run', stamp.exists()))

        def fake_build(root):
            self.events.append('build')
            return FakeMcp()

        err = io.StringIO()
        with self.in_fixture_environment(), \
                patch.object(self.runner, '_assess_startup', return_value=assessment), \
                patch.object(self.runner, '_configure_stdio_for_mcp_transport'), \
                patch.object(self.runner, '_isolate_native_stdout_from_protocol'), \
                patch.object(self.runner, 'build_server', side_effect=fake_build), \
                redirect_stderr(err), redirect_stdout(io.StringIO()):
            result = self.runner.main(argv)
        return result, err.getvalue()

    def test_ready_startup_adopts_a_missing_stamp(self):
        result, _ = self._main(['--root', str(self.root)], {'status': 'ready', 'startup_blocked': False})
        self.assertEqual(result, 0)
        self.assertEqual(self.events, ['build', ('run', True)])
        self.assertEqual(json.loads(self.stamp.read_text())['provenance'], 'adopted')
        self.assertEqual(self.check()['status'], 'ready')

    def test_readable_stamp_is_never_rewritten(self):
        with self.in_fixture_environment():
            readiness.write_setup_stamp(self.root)
        before = self.stamp.read_bytes()
        self._main(['--root', str(self.root)], {'status': 'ready', 'startup_blocked': False})
        self.assertEqual(self.stamp.read_bytes(), before)

    def test_not_ready_startup_writes_nothing(self):
        self._main(['--root', str(self.root)], {'status': 'action_required', 'startup_blocked': False})
        self.assertFalse(self.stamp.exists())

    def test_dry_run_writes_nothing(self):
        with patch.object(self.runner, '_get_handler', return_value=object()):
            result, _ = self._main(['--root', str(self.root), '--dry-run'],
                                   {'status': 'ready', 'startup_blocked': False})
        self.assertEqual(result, 0)
        self.assertFalse(self.stamp.exists())

    def test_source_change_since_assessment_writes_nothing_and_starts(self):
        stale = {'schema_version': 1, 'errors': [],
                 'sources': dict(self.runner._SETUP_LOADED_IDENTITY['sources'], **{'server.py': '0' * 64})}
        with patch.object(self.runner, '_SETUP_LOADED_IDENTITY', stale):
            result, err = self._main(['--root', str(self.root)], {'status': 'ready', 'startup_blocked': False})
        self.assertEqual(result, 0)
        self.assertEqual(self.events, ['build', ('run', False)])
        self.assertFalse(self.stamp.exists())
        self.assertIn('setup baseline not recorded', err)

    def test_create_only_race_keeps_the_existing_stamp(self):
        original = readiness.write_setup_stamp

        def racing_write(root, **kwargs):
            # Another writer publishes between the absence check and our publish.
            original(root)
            return original(root, **kwargs)

        with patch.object(readiness, 'write_setup_stamp', side_effect=racing_write):
            result, err = self._main(['--root', str(self.root)], {'status': 'ready', 'startup_blocked': False})
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(self.stamp.read_text())['provenance'], 'setup')
        self.assertIn('setup baseline not recorded', err)


if __name__ == '__main__':
    unittest.main()

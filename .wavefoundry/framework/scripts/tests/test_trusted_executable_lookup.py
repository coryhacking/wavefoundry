"""20qxn: trust the target boundary without treating HOME or / as a repository."""
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import setup_index as setup
import tensorwell_client as tensorwell


class TrustedExecutableLookupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.home = self.base / 'home'
        self.root = self.home / 'repo'
        self.root.mkdir(parents=True)
        self.bin = self.home / '.local/bin'
        self.bin.mkdir(parents=True)
        self.uv = self.plant(self.bin, 'uv.exe' if os.name == 'nt' else 'uv')
        self.controller = self.plant(self.bin, 'tensorwell')

    def plant(self, directory, name):
        path = directory / name
        path.write_text('fixture bytes; never executed')
        path.chmod(0o755)
        return path

    def test_home_root_and_unrelated_cwd_find_outside_executables(self):
        unrelated = self.base / 'unrelated'
        unrelated.mkdir()
        for cwd in (self.home, Path(self.home.anchor), unrelated):
            with contextlib.chdir(cwd), patch.dict(os.environ, {'PATH': str(self.bin)}):
                with self.subTest(cwd=str(cwd), lookup='uv'):
                    self.assertEqual(setup._trusted_path_uv(self.root), self.uv)
                with self.subTest(cwd=str(cwd), lookup='tensorwell'):
                    self.assertEqual(tensorwell._controller(self.root), self.controller.resolve())

    def test_absolute_repo_entries_and_relative_or_empty_entries_stay_refused(self):
        self.plant(self.root, self.uv.name)
        self.plant(self.root, 'tensorwell')
        for entry in (str(self.root), '.', '', 'relative/bin'):
            with self.subTest(entry=repr(entry)), contextlib.chdir(self.root), patch.dict(os.environ, {'PATH': entry}):
                self.assertIsNone(setup._trusted_path_uv(self.root))
                self.assertIsNone(tensorwell._controller(self.root))

    def test_candidate_and_directory_symlinks_into_repo_stay_refused(self):
        if os.name == 'nt':
            self.skipTest('Native Windows symlink privileges unqualified')
        planted_uv = self.plant(self.root, self.uv.name)
        planted_controller = self.plant(self.root, 'tensorwell')
        self.uv.unlink()
        self.controller.unlink()
        self.uv.symlink_to(planted_uv)
        self.controller.symlink_to(planted_controller)
        alias = self.home / 'alias-bin'
        alias.symlink_to(self.root, target_is_directory=True)
        for directory in (self.bin, alias):
            with self.subTest(directory=str(directory)), contextlib.chdir(self.home), patch.dict(os.environ, {'PATH': str(directory)}):
                self.assertIsNone(setup._trusted_path_uv(self.root))
                self.assertIsNone(tensorwell._controller(self.root))

    def test_unknown_target_keeps_conservative_cwd_exclusion(self):
        with contextlib.chdir(self.home), patch.dict(os.environ, {'PATH': str(self.bin)}):
            self.assertIsNone(setup._trusted_path_uv(None))
        with contextlib.chdir(self.root), patch.dict(os.environ, {'PATH': str(self.bin)}):
            self.assertEqual(setup._trusted_path_uv(None), self.uv)

    def test_skipped_diagnostics_are_bounded_escaped_and_explain_refusal(self):
        entries = ['', '.', 'relative\n\x1b[31mbin', str(self.root)] + ['relative-' + 'x' * 1000] * 30
        skipped = []
        with contextlib.chdir(self.root), patch.dict(os.environ, {'PATH': os.pathsep.join(entries)}):
            self.assertIsNone(setup._trusted_path_uv(self.root, skipped=skipped))
        self.assertEqual(len(skipped), 5)
        self.assertTrue(any('relative' in entry for entry in skipped))
        self.assertTrue(any('repository' in entry for entry in skipped))
        self.assertLess(len(' '.join(skipped)), 1100)
        self.assertNotIn('\x1b', ''.join(skipped))
        self.assertNotIn('\n', ''.join(skipped))
        message = setup._uv_required_message(windows=False, skipped=skipped)
        self.assertIn('Skipped PATH entries', message)
        self.assertIn('relative PATH entry', message)
        self.assertIn('hash-verified uv bootstrap', message)

    def test_real_no_uv_refusal_includes_lookup_diagnostics_without_installer(self):
        error = io.StringIO()
        with contextlib.chdir(self.root), patch.dict(os.environ, {'PATH': '.'}), \
                patch.object(setup, '_uv_bin', return_value=None), \
                patch.object(setup, '_bootstrap_uv', return_value=None), \
                patch.object(setup, '_run_install_step', side_effect=AssertionError('installer ran')), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error), \
                self.assertRaises(SystemExit) as caught:
            setup._install_deps(['fixture-dependency'], self.base / 'venv/bin/python', self.root)
        self.assertEqual(caught.exception.code, 2)
        self.assertIn('Skipped PATH entries', error.getvalue())
        self.assertIn('relative PATH entry', error.getvalue())


    def test_startup_no_uv_returns_the_same_bounded_lookup_reasons(self):
        python = self.base / 'venv/bin/python'
        python.parent.mkdir(parents=True)
        python.write_text('fixture interpreter; never executed')
        with contextlib.chdir(self.root), patch.dict(os.environ, {'PATH': '.'}), \
                patch.object(setup.venv_bootstrap, 'tool_venv_python', return_value=python), \
                patch.object(setup, '_uv_bin', return_value=None), \
                patch.object(setup, '_run_install_step', side_effect=AssertionError('startup installer ran')):
            outcome = setup.install_requirement_specs(['fixture-dependency'], root=self.root)
        self.assertEqual(outcome['status'], 'no_uv')
        self.assertIn('relative PATH entry', outcome['message'])
        self.assertIn('package-age guard', outcome['message'])

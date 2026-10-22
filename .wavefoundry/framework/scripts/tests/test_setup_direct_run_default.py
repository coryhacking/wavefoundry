"""Change 21cw5: a direct run of setup without ``--root`` targets the
repository that holds the script, as ``wf setup`` does."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import setup_wavefoundry  # noqa: E402
import upgrade_lib  # noqa: E402


def _can_symlink() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        try:
            os.symlink(tmp, os.path.join(tmp, "probe"), target_is_directory=True)
        except (OSError, NotImplementedError):
            return False
    return True


class DirectRunDefaultTests(unittest.TestCase):
    def test_no_root_defaults_to_the_script_repository(self) -> None:
        script = os.path.join("/repo", ".wavefoundry", "framework", "scripts", "setup_wavefoundry.py")
        args, root = setup_wavefoundry._direct_run_default(["--full"], script)
        self.assertEqual(args, ["--full"])
        self.assertEqual(root, Path(os.path.abspath("/repo")))

    def test_explicit_root_in_either_spelling_wins(self) -> None:
        for argv in (["--root", "/other"], ["--root=/other"], ["--full", "--root", "/a", "--root=/b"]):
            with self.subTest(argv=argv):
                args, root = setup_wavefoundry._direct_run_default(argv, "/repo/.wavefoundry/framework/scripts/s.py")
                self.assertIsNone(root)
                self.assertEqual(args, argv)

    def test_relative_model_bundle_is_made_absolute_before_the_change(self) -> None:
        here = os.getcwd()
        args, _ = setup_wavefoundry._direct_run_default(
            ["--model-bundle", "models.zip", "--model-bundle-model-set-version", "3"], "/r/.wavefoundry/framework/scripts/s.py")
        self.assertEqual(args, ["--model-bundle", os.path.join(here, "models.zip"), "--model-bundle-model-set-version", "3"])
        args, _ = setup_wavefoundry._direct_run_default(["--model-bundle=sub/models.zip"], "/r/.wavefoundry/framework/scripts/s.py")
        self.assertEqual(args, ["--model-bundle=" + os.path.join(here, "sub", "models.zip")])

    @unittest.skipUnless(_can_symlink(), "this platform cannot create directory links")
    def test_linked_framework_folder_targets_the_repository_holding_the_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shared = Path(tmp, "shared-framework")
            (shared / "scripts").mkdir(parents=True)
            repo = Path(tmp, "repo")
            (repo / ".wavefoundry").mkdir(parents=True)
            os.symlink(shared, repo / ".wavefoundry" / "framework", target_is_directory=True)
            script = repo / ".wavefoundry" / "framework" / "scripts" / "setup_wavefoundry.py"
            _, root = setup_wavefoundry._direct_run_default([], str(script))
            self.assertEqual(root, repo)
            self.assertNotEqual(root, Path(os.path.realpath(script)).parents[3])

    def test_in_process_main_callers_keep_the_current_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                self.assertEqual(setup_wavefoundry._resolve_setup_root([]), Path(tmp).resolve())
            finally:
                os.chdir(previous)


class EnterDirectRunRootTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous = os.getcwd()
        self.addCleanup(os.chdir, self.previous)

    def test_unusable_script_location_is_refused_naming_root(self) -> None:
        cases = (os.path.join(os.sep, "s.py"),  # too shallow to hold a repository
                 os.path.join(tempfile.gettempdir(), "missing-21cw5", ".wavefoundry", "framework", "scripts", "s.py"))
        for script in cases:
            with self.subTest(script=script):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    self.assertIsNone(setup_wavefoundry._enter_direct_run_root([], script))
                self.assertIn("Pass --root", stderr.getvalue())
                self.assertEqual(os.getcwd(), self.previous)

    def test_relative_model_bundle_environment_is_made_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp, "repo")
            (repo / ".wavefoundry" / "framework" / "scripts").mkdir(parents=True)
            here = os.getcwd()
            try:
                with mock.patch.dict(os.environ, {"WAVEFOUNDRY_MODEL_BUNDLE": "models.zip"}):
                    args = setup_wavefoundry._enter_direct_run_root(
                        ["--full"], str(repo / ".wavefoundry" / "framework" / "scripts" / "s.py"))
                    self.assertEqual(os.environ["WAVEFOUNDRY_MODEL_BUNDLE"], os.path.join(here, "models.zip"))
                self.assertEqual(args, ["--full"])
                self.assertEqual(Path(os.getcwd()).resolve(), repo.resolve())
            finally:
                os.chdir(self.previous)  # Windows cannot remove the current folder


class DirectRunSubprocessTests(unittest.TestCase):
    """Run a copy of the scripts as ``__main__`` from outside its repository.

    Runs that pass the root check use a scratch repository holding a foreign
    upgrade lock, so setup stops at reconciliation before any write.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="setup-direct-run-")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        scripts = self.repo / ".wavefoundry" / "framework" / "scripts"
        shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
        self.script = scripts / "setup_wavefoundry.py"
        self.outside = self.tmp / "elsewhere"
        self.outside.mkdir()

    def run_setup(self, *args: str, cwd: Path) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPYCACHEPREFIX"}
        return subprocess.run([sys.executable, str(self.script), *args], cwd=cwd, env=env,
                              capture_output=True, text=True, timeout=300)

    def lock(self) -> None:
        upgrade_lib.write_upgrade_lock(self.repo, "old", "new", runner_protocol=2)

    def assert_reached_reconciliation(self, result: subprocess.CompletedProcess) -> None:
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertNotIn("is not a Wavefoundry repository root", output)
        self.assertIn("storage_setup_foreign_upgrade", output)

    def test_run_from_another_folder_targets_the_script_repository(self) -> None:
        self.lock()
        self.assert_reached_reconciliation(self.run_setup(cwd=self.outside))

    def test_run_from_a_subfolder_targets_the_repository_root(self) -> None:
        sub = self.repo / "docs" / "deep"
        sub.mkdir(parents=True)
        self.lock()
        self.assert_reached_reconciliation(self.run_setup(cwd=sub))

    def test_explicit_root_without_the_framework_is_still_refused(self) -> None:
        for args in (("--root", str(self.outside)), (f"--root={self.outside}",)):
            with self.subTest(args=args):
                result = self.run_setup(*args, cwd=self.repo)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("is not a Wavefoundry repository root", result.stderr)

    def test_check_from_another_folder_assesses_the_script_repository(self) -> None:
        result = self.run_setup("--check", "--json", cwd=self.outside)
        report = json.loads(result.stdout)
        argvs = [action.get("argv", []) for action in report.get("actions", [])]
        roots = [argv[argv.index("--root") + 1] for argv in argvs if "--root" in argv]
        self.assertTrue(roots, report)
        self.assertTrue(all(Path(root).resolve() == self.repo for root in roots), roots)


if __name__ == "__main__":
    unittest.main()

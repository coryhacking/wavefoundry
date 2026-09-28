"""Wave 1z2m8: list-form sensors resolve Windows .cmd tools through PATHEXT."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import sensor_runner  # noqa: E402
import subprocess_util  # noqa: E402


def _completed(argv):
    return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")


class SensorCommandResolutionTests(unittest.TestCase):
    def _run(self, command, *, windows, which, shell=False):
        calls = []

        def _run_with_tree_kill(cmd, **_kwargs):
            calls.append(cmd)
            return _completed(cmd)

        sensor = {"name": "tests", "command": command}
        # inert-by-design: _IS_WINDOWS is a platform flag value, not a callable stub.
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(sensor_runner, "_IS_WINDOWS", windows), \
             patch.object(sensor_runner.shutil, "which", side_effect=which) as which_mock, \
             patch.object(subprocess_util, "run_with_tree_kill", side_effect=_run_with_tree_kill):
            result = sensor_runner.run_sensor(Path(tmp), sensor, timeout_seconds=5, shell=shell)
        return result, calls, which_mock, sensor

    def test_windows_resolves_a_bare_name_to_its_cmd_wrapper(self):
        resolved = r"C:\Program Files\nodejs\npm.CMD"
        result, calls, _which, sensor = self._run(
            ["npm", "test"], windows=True, which=lambda name: resolved)
        self.assertTrue(result["passed"], result["output_summary"])
        self.assertEqual(calls, [[resolved, "test"]])
        self.assertEqual(sensor["command"], ["npm", "test"])  # config is never mutated

    def test_an_unresolvable_name_runs_unchanged(self):
        _result, calls, _which, _sensor = self._run(
            ["nosuchtool", "x"], windows=True, which=lambda name: None)
        self.assertEqual(calls, [["nosuchtool", "x"]])

    def test_a_path_is_never_resolved(self):
        for command in (["./gradlew", "check"], [r".\gradlew.bat", "check"]):
            with self.subTest(command=command):
                _result, calls, which_mock, _sensor = self._run(
                    command, windows=True, which=lambda name: "ignored")
                self.assertEqual(calls, [command])
                which_mock.assert_not_called()

    def test_posix_and_shell_commands_are_unchanged(self):
        _result, calls, which_mock, _sensor = self._run(
            ["npm", "test"], windows=False, which=lambda name: "ignored")
        self.assertEqual(calls, [["npm", "test"]])
        which_mock.assert_not_called()
        _result, calls, which_mock, _sensor = self._run(
            "npm test", windows=True, which=lambda name: "ignored", shell=True)
        self.assertEqual(calls, ["npm test"])
        which_mock.assert_not_called()


class SensorTimeoutTests(unittest.TestCase):
    def test_a_timed_out_sensor_reports_the_timeout(self):
        # Wave 1z822: the timeout path runs through run_with_tree_kill for real.
        sensor = {"name": "slow", "command": [sys.executable, "-c", "import time; time.sleep(30)"]}
        with tempfile.TemporaryDirectory() as tmp:
            result = sensor_runner.run_sensor(Path(tmp), sensor, timeout_seconds=0.5)
        self.assertFalse(result["passed"])
        self.assertEqual(result["output_summary"], "Sensor timed out after 0.5s.")
        self.assertLess(result["duration_ms"], 15000)


if __name__ == "__main__":
    unittest.main()

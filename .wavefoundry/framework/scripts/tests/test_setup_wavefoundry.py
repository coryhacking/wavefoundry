from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SETUP_WF_PATH = SCRIPTS_ROOT / "setup_wavefoundry.py"


def load_setup_wavefoundry():
    spec = importlib.util.spec_from_file_location("setup_wavefoundry", SETUP_WF_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["setup_wavefoundry"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_completed_process(returncode: int):
    """Build a minimal CompletedProcess-like object for subprocess.run mocking."""
    class _CP:
        def __init__(self, rc: int):
            self.returncode = rc
    return _CP(returncode)


class SetupWavefoundryTests(unittest.TestCase):
    def setUp(self):
        self.mod = load_setup_wavefoundry()

    # --- Step 1: setup_index delegation ----------------------------------

    def test_step_1_delegates_args_to_setup_index_main(self):
        delegated: list[list[str] | None] = []

        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                delegated.append(argv)
                return 0

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=0), \
             patch.object(self.mod, "_run_mcp_server_dry_run", return_value=0):
            result = self.mod.main(["--root", "/tmp/repo", "--full"])

        self.assertEqual(result, 0)
        self.assertEqual(delegated, [["--root", "/tmp/repo", "--full"]])

    def test_step_1_failure_aborts_before_step_2_and_3(self):
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 5

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces") as render_mock, \
             patch.object(self.mod, "_run_mcp_server_dry_run") as dry_run_mock:
            result = self.mod.main([])

        self.assertEqual(result, 5)
        render_mock.assert_not_called()
        dry_run_mock.assert_not_called()

    # --- Step 2: render_platform_surfaces orchestration ------------------

    def test_step_2_runs_render_platform_surfaces_after_setup_index_succeeds(self):
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 0

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=0) as render_mock, \
             patch.object(self.mod, "_run_mcp_server_dry_run", return_value=0):
            result = self.mod.main([])

        self.assertEqual(result, 0)
        render_mock.assert_called_once_with()

    def test_step_2_failure_aborts_before_step_3(self):
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 0

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=3), \
             patch.object(self.mod, "_run_mcp_server_dry_run") as dry_run_mock:
            result = self.mod.main([])

        self.assertEqual(result, 3)
        dry_run_mock.assert_not_called()

    # --- Step 3: MCP server dry-run smoke test ---------------------------

    def test_step_3_runs_mcp_server_dry_run_after_render_succeeds(self):
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 0

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=0), \
             patch.object(self.mod, "_run_mcp_server_dry_run", return_value=0) as dry_run_mock:
            result = self.mod.main([])

        self.assertEqual(result, 0)
        dry_run_mock.assert_called_once_with()

    def test_step_3_failure_returns_non_zero(self):
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 0

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=0), \
             patch.object(self.mod, "_run_mcp_server_dry_run", return_value=7):
            result = self.mod.main([])

        self.assertEqual(result, 7)

    # --- Helper subprocess invocations -----------------------------------

    def test_run_render_invokes_render_script_via_python(self):
        captured: list[list[str]] = []

        def fake_run(cmd, check=False):
            captured.append(list(cmd))
            return _make_completed_process(0)

        with patch.object(self.mod.subprocess, "run", side_effect=fake_run):
            rc = self.mod._run_render_platform_surfaces()

        self.assertEqual(rc, 0)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], sys.executable)
        self.assertTrue(captured[0][1].endswith("render_platform_surfaces.py"))

    def test_run_mcp_dry_run_invokes_server_with_dry_run_flag(self):
        captured: list[list[str]] = []

        def fake_run(cmd, check=False):
            captured.append(list(cmd))
            return _make_completed_process(0)

        with patch.object(self.mod.subprocess, "run", side_effect=fake_run):
            rc = self.mod._run_mcp_server_dry_run()

        self.assertEqual(rc, 0)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], sys.executable)
        self.assertTrue(captured[0][1].endswith("server.py"))
        self.assertIn("--dry-run", captured[0])


if __name__ == "__main__":
    unittest.main()

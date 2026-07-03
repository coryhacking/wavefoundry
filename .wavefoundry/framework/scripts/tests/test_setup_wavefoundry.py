from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
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
        # Wave 1p7pm: setup `main` calls venv_bootstrap.ensure_python_resolves() after Step 1, which
        # is SIDE-EFFECTING (creates ~/.local/bin/python3 + may append to the shell rc). These tests
        # mock Step 1 to succeed, so they would reach that heal against the REAL machine — patch it to
        # a no-op so the suite never mutates the operator's box. (The real heal is exercised, safely
        # isolated into a tempdir, only in test_venv_bootstrap.py.)
        import venv_bootstrap
        heal = patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok")
        self.ensure_python_resolves_mock = heal.start()
        self.addCleanup(heal.stop)

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

    # --- Step 1b: `python` resolution heal (wave 1p7pm) ------------------

    def test_step_1b_calls_ensure_python_resolves_strict_after_venv(self):
        """Setup heals `python` resolution after Step 1 (the venv exists), strictly. The heal mock is
        installed in setUp; this asserts the WIRING stays in place (without mutating the real machine)."""
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 0

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=0), \
             patch.object(self.mod, "_run_mcp_server_dry_run", return_value=0):
            result = self.mod.main([])

        self.assertEqual(result, 0)
        self.ensure_python_resolves_mock.assert_called_once_with(strict=True)

    def test_step_1b_skipped_when_step_1_fails(self):
        """If Step 1 (venv build) fails, the heal must NOT run — there's no venv to heal against."""
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 9

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces"), \
             patch.object(self.mod, "_run_mcp_server_dry_run"):
            result = self.mod.main([])

        self.assertEqual(result, 9)
        self.ensure_python_resolves_mock.assert_not_called()

    def test_step_1b_failure_aborts_before_step_2_and_3(self):
        """A missing or too-old command-line `python3` is a hard setup prerequisite failure."""
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 0

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces") as render_mock, \
             patch.object(self.mod, "_run_mcp_server_dry_run") as dry_run_mock:
            self.ensure_python_resolves_mock.side_effect = SystemExit(2)
            with self.assertRaises(SystemExit):
                self.mod.main([])

        self.ensure_python_resolves_mock.assert_called_once_with(strict=True)
        render_mock.assert_not_called()
        dry_run_mock.assert_not_called()

    def test_setup_does_not_print_gui_fallback_guidance(self):
        """Setup must stop on the `python3 --version` prerequisite, not advertise a bypass stanza."""
        import tempfile

        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 0

        # A real (writable) root: Step 0 provisions the lifecycle policy here
        # instead of failing on the old nonexistent placeholder path.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)

        out = io.StringIO()
        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=0), \
             patch.object(self.mod, "_run_mcp_server_dry_run", return_value=0), \
             redirect_stdout(out):
            result = self.mod.main(["--root", tmp.name])

        self.assertEqual(result, 0)
        text = out.getvalue()
        self.assertNotIn("GUI-host note", text)
        self.assertNotIn("absolute-path form", text)
        self.assertNotIn("/.wavefoundry/venv/", text)

    # --- Helper subprocess invocations -----------------------------------

    def test_run_render_invokes_render_script_via_python(self):
        captured: list[list[str]] = []

        # Wave 1p8gu: spawns route through subprocess_util.isolated_run, which adds stdin/creationflags
        # kwargs — accept **kwargs so the fake tolerates the isolation kwargs.
        def fake_run(cmd, check=False, **kwargs):
            captured.append(list(cmd))
            return _make_completed_process(0)

        with patch.object(self.mod.subprocess, "run", side_effect=fake_run):
            rc = self.mod._run_render_platform_surfaces()

        self.assertEqual(rc, 0)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], sys.executable)
        self.assertTrue(captured[0][1].endswith("render_platform_surfaces.py"))

    def test_run_mcp_dry_run_invokes_server_with_generated_mcp_python_shape(self):
        captured: list[list[str]] = []

        def fake_run(cmd, check=False, **kwargs):
            captured.append(list(cmd))
            return _make_completed_process(0)

        with patch.object(self.mod.subprocess, "run", side_effect=fake_run):
            rc = self.mod._run_mcp_server_dry_run()

        self.assertEqual(rc, 0)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], "python3")
        self.assertTrue(captured[0][1].endswith("server.py"))
        self.assertIn("--dry-run", captured[0])

    def test_success_message_requires_fresh_agent_session(self):
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 0

        out = io.StringIO()
        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=0), \
             patch.object(self.mod, "_run_mcp_server_dry_run", return_value=0), \
             redirect_stdout(out):
            result = self.mod.main([])

        self.assertEqual(result, 0)
        text = out.getvalue()
        self.assertIn("fully quit and reopen your AI agent", text)
        self.assertIn("start a fresh conversation", text)
        self.assertIn("Do not resume an old session", text)


if __name__ == "__main__":
    unittest.main()


class GpuDoctorCheckTests(unittest.TestCase):
    """1p6et: `setup_wavefoundry --check` prints the GPU/provider diagnostic and skips setup;
    provider_policy.diagnostic_report() runs the bounded model-loading provider probe when one is
    supplied (not pure introspection — wave 1p9lj docstring correction) and reflects the probes."""

    def setUp(self):
        self.mod = load_setup_wavefoundry()

    def test_check_gpu_flag_short_circuits_setup(self):
        # `--check-gpu` routes to _run_gpu_check and runs NONE of the 3 setup steps. (_run_gpu_check
        # is mocked here so the test doesn't load a model; its probe behaviour is covered by
        # test_diagnostic_report_with_probe_selects_probed_provider + the live smoke.)
        flags = {"gpu": False}
        steps: list[str] = []

        def fake_gpu_check():
            flags["gpu"] = True
            return 0

        with patch.object(self.mod, "_run_gpu_check", side_effect=fake_gpu_check), \
             patch.object(self.mod, "_load_setup_index", side_effect=lambda: steps.append("setup_index")), \
             patch.object(self.mod, "_run_render_platform_surfaces", side_effect=lambda: (steps.append("render"), 0)[1]), \
             patch.object(self.mod, "_run_mcp_server_dry_run", side_effect=lambda: (steps.append("dryrun"), 0)[1]):
            rc = self.mod.main(["--check-gpu"])
        self.assertEqual(rc, 0)
        self.assertTrue(flags["gpu"])
        self.assertEqual(steps, [])  # no setup step ran — short-circuited

    def test_diagnostic_report_with_probe_selects_probed_provider(self):
        # 1p6et accuracy fix: with a probe, a probe-required provider (CoreML on Apple Silicon) is
        # CONFIRMED and selected — matching runtime — rather than falling back to CPU (the no-probe view).
        import os
        pp = self.mod._load_provider_policy()

        def fake_probe(provider, **_kw):
            return pp.ProviderProbeResult(provider, True, "probe ok")

        # Clear any setup-cached / requested provider env (can leak from other test files in the
        # shared run_tests process — select_embedding_providers short-circuits to a cached provider
        # before probing) so this test deterministically exercises the probe path.
        with patch.dict(os.environ, clear=False):
            os.environ.pop(pp.SETUP_SELECTED_ENV, None)
            os.environ.pop(pp.REQUESTED_PROVIDER_ENV, None)
            with patch.object(pp, "nvidia_gpu_present", return_value=False), \
                 patch.object(pp, "apple_silicon_present", return_value=True), \
                 patch.object(pp, "available_onnx_providers", return_value=("CoreMLExecutionProvider", "CPUExecutionProvider")), \
                 patch.object(pp, "detect_cuda12_abi_gap", return_value=None):
                report = pp.diagnostic_report(provider_probe=fake_probe)
        self.assertEqual(report["selected_provider"], "CoreMLExecutionProvider")

    def test_diagnostic_report_shape_and_reflects_probes(self):
        pp = self.mod._load_provider_policy()
        fake = pp.ProviderDecision(
            selected_provider="CUDAExecutionProvider",
            providers=("CUDAExecutionProvider", "CPUExecutionProvider"),
            available_providers=("CUDAExecutionProvider", "CPUExecutionProvider"),
            reason="cuda available",
            remediation=None,
        )
        with patch.object(pp, "nvidia_gpu_present", return_value=True), \
             patch.object(pp, "apple_silicon_present", return_value=False), \
             patch.object(pp, "available_onnx_providers", return_value=("CUDAExecutionProvider", "CPUExecutionProvider")), \
             patch.object(pp, "select_embedding_providers", return_value=fake), \
             patch.object(pp, "detect_cuda12_abi_gap", return_value=None):
            report = pp.diagnostic_report()
        self.assertTrue(report["nvidia_gpu_present"])
        self.assertFalse(report["apple_silicon_present"])
        self.assertIn("CUDAExecutionProvider", report["available_onnx_providers"])
        self.assertEqual(report["selected_provider"], "CUDAExecutionProvider")
        self.assertIsNone(report["cuda12_abi_gap"])
        self.assertIn("platform", report)
        text = pp.format_diagnostic_report(report)
        self.assertIn("would select", text)
        self.assertIn("CUDAExecutionProvider", text)

    def test_diagnostic_report_filters_remote_azure_provider(self):
        # 1p6et follow-up: AzureExecutionProvider is a remote/inert EP Wavefoundry never selects;
        # it must not appear in the diagnostic's available_onnx_providers (local backends only).
        pp = self.mod._load_provider_policy()
        with patch.object(pp, "nvidia_gpu_present", return_value=False), \
             patch.object(pp, "apple_silicon_present", return_value=True), \
             patch.object(pp, "available_onnx_providers",
                          return_value=("CoreMLExecutionProvider", "AzureExecutionProvider", "CPUExecutionProvider")), \
             patch.object(pp, "detect_cuda12_abi_gap", return_value=None):
            report = pp.diagnostic_report()
        self.assertNotIn("AzureExecutionProvider", report["available_onnx_providers"])
        self.assertIn("CoreMLExecutionProvider", report["available_onnx_providers"])
        self.assertIn("CPUExecutionProvider", report["available_onnx_providers"])


class LifecyclePolicyStepZeroTests(unittest.TestCase):
    """Wave 1p9q0 — setup Step 0 auto-provisions the lifecycle-ID policy on
    fresh repos and never touches an existing (configured) policy block."""

    def setUp(self):
        import tempfile
        self.mod = load_setup_wavefoundry()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "proj"
        (self.root / "docs").mkdir(parents=True)
        # Anchor: provisioning requires the extracted framework dir (repo-root guard).
        (self.root / ".wavefoundry" / "framework").mkdir(parents=True)
        self.cfg = self.root / "docs" / "workflow-config.json"
        self.addCleanup(self._tmp.cleanup)

    def test_absent_policy_block_is_provisioned_v2(self):
        import json
        self.cfg.write_text("{}", encoding="utf-8")
        rc = self.mod._provision_lifecycle_policy_if_absent(self.root)
        self.assertEqual(rc, 0)
        pol = json.loads(self.cfg.read_text(encoding="utf-8"))["lifecycle_id_policy"]
        self.assertEqual(pol["scheme_version"], "v2")

    def test_missing_config_file_is_provisioned_v2(self):
        import json
        rc = self.mod._provision_lifecycle_policy_if_absent(self.root)
        self.assertEqual(rc, 0)
        pol = json.loads(self.cfg.read_text(encoding="utf-8"))["lifecycle_id_policy"]
        self.assertEqual(pol["scheme_version"], "v2")

    def test_existing_policy_block_left_untouched(self):
        import json
        original = json.dumps({"lifecycle_id_policy": {
            "epoch_utc": "2021-03-04T00:00:00Z", "hour_offset": 0}})
        self.cfg.write_text(original, encoding="utf-8")
        rc = self.mod._provision_lifecycle_policy_if_absent(self.root)
        self.assertEqual(rc, 0)
        # Byte-identical: configured repos migrate via the upgrade pipeline, not setup.
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), original)

    def test_corrupt_config_aborts_setup_before_step_one(self):
        self.cfg.write_text("{corrupt", encoding="utf-8")
        err = io.StringIO()
        import contextlib
        with contextlib.redirect_stderr(err):
            rc = self.mod._provision_lifecycle_policy_if_absent(self.root)
        self.assertEqual(rc, 1)
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), "{corrupt")
        # And through main(): step 0 failure aborts before setup_index runs.
        with patch.object(self.mod, "_load_setup_index") as load_mock, \
             contextlib.redirect_stderr(io.StringIO()), \
             redirect_stdout(io.StringIO()):
            main_rc = self.mod.main(["--root", str(self.root)])
        self.assertEqual(main_rc, 1)
        load_mock.assert_not_called()

    def test_non_repo_root_is_skipped_not_provisioned(self):
        import shutil
        shutil.rmtree(self.root / ".wavefoundry")
        rc = self.mod._provision_lifecycle_policy_if_absent(self.root)
        self.assertEqual(rc, 0)
        self.assertFalse(self.cfg.exists(),
                         "must not provision a directory that is not a repo root")

    def test_resolve_setup_root_parses_both_flag_forms(self):
        self.assertEqual(self.mod._resolve_setup_root(["--root", str(self.root)]),
                         self.root.resolve())
        self.assertEqual(self.mod._resolve_setup_root([f"--root={self.root}"]),
                         self.root.resolve())

    def test_main_runs_step_zero_before_setup_index(self):
        import json
        self.cfg.write_text("{}", encoding="utf-8")
        order: list[str] = []

        class FakeSetupIndex:
            @staticmethod
            def main(argv):
                order.append("setup_index")
                return 0

        real = self.mod._provision_lifecycle_policy_if_absent

        def traced(root):
            order.append("provision")
            return real(root)

        with patch.object(self.mod, "_provision_lifecycle_policy_if_absent", traced), \
             patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=0), \
             patch.object(self.mod, "_run_mcp_server_dry_run", return_value=0), \
             redirect_stdout(io.StringIO()):
            rc = self.mod.main(["--root", str(self.root)])
        self.assertEqual(rc, 0)
        self.assertEqual(order, ["provision", "setup_index"])
        pol = json.loads(self.cfg.read_text(encoding="utf-8"))["lifecycle_id_policy"]
        self.assertEqual(pol["scheme_version"], "v2")

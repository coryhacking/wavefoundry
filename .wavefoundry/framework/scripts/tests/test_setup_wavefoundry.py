from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
SETUP_WF_PATH = SCRIPTS_ROOT / "setup_wavefoundry.py"
REVIEW_PROTOCOL_SEEDS = (
    "209-agent-harness-core.prompt.md",
    "221-code-reviewer.prompt.md",
    "239-qa-reviewer.prompt.md",
)


def _stage_review_protocol_seeds(root: Path) -> Path:
    target_seeds = root / ".wavefoundry" / "framework" / "seeds"
    target_seeds.mkdir(parents=True, exist_ok=True)
    for name in REVIEW_PROTOCOL_SEEDS:
        target_seeds.joinpath(name).write_bytes(
            (SCRIPTS_ROOT.parent / "seeds" / name).read_bytes()
        )
    shutil.copytree(
        SCRIPTS_ROOT.parent / "install" / "lifecycle-prompts",
        root
        / ".wavefoundry"
        / "framework"
        / "install"
        / "lifecycle-prompts",
        dirs_exist_ok=True,
    )
    return target_seeds


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
        import memory_backfill
        gate = patch.object(
            memory_backfill,
            "sync_inventory",
            return_value={
                "run_id": "test-run",
                "state": "ready_for_index",
                "eligible_waves": 0,
            },
        )
        gate.start()
        self.addCleanup(gate.stop)
        mark = patch.object(memory_backfill, "mark_indexed", return_value=None)
        mark.start()
        self.addCleanup(mark.stop)
        # Wave 1p7pm: setup `main` calls venv_bootstrap.ensure_python_resolves() after Step 1, which
        # is SIDE-EFFECTING (creates ~/.local/bin/python3 + may append to the shell rc). These tests
        # mock Step 1 to succeed, so they would reach that heal against the REAL machine — patch it to
        # a no-op so the suite never mutates the operator's box. (The real heal is exercised, safely
        # isolated into a tempdir, only in test_venv_bootstrap.py.)
        import venv_bootstrap
        heal = patch.object(venv_bootstrap, "ensure_python_resolves", return_value="ok")
        self.ensure_python_resolves_mock = heal.start()
        self.addCleanup(heal.stop)

    # --- Step 2: setup_index delegation ----------------------------------

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
        self.assertEqual(
            delegated,
            [
                ["--root", "/tmp/repo", "--full", "--deps-only"],
                ["--root", "/tmp/repo", "--full"],
            ],
        )

    def test_step_2_failure_aborts_before_step_3(self):
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 5

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=0) as render_mock, \
             patch.object(self.mod, "_run_mcp_server_dry_run") as dry_run_mock:
            result = self.mod.main([])

        self.assertEqual(result, 5)
        render_mock.assert_called_once_with(Path.cwd().resolve())
        dry_run_mock.assert_not_called()

    # --- Step 1: render_platform_surfaces orchestration ------------------

    def test_step_1_runs_render_platform_surfaces_before_setup_index(self):
        events: list[str] = []
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                events.append("index")
                return 0

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex), \
             patch.object(self.mod, "_run_render_platform_surfaces", side_effect=lambda root: (events.append("render"), 0)[1]) as render_mock, \
             patch.object(self.mod, "_run_mcp_server_dry_run", return_value=0):
            result = self.mod.main([])

        self.assertEqual(result, 0)
        render_mock.assert_called_once_with(Path.cwd().resolve())
        self.assertEqual(events, ["render", "index", "index"])

    def test_step_1_failure_aborts_before_index_and_step_3(self):
        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                return 0

        with patch.object(self.mod, "_load_setup_index", return_value=FakeSetupIndex) as index_mock, \
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=3), \
             patch.object(self.mod, "_run_mcp_server_dry_run") as dry_run_mock:
            result = self.mod.main([])

        self.assertEqual(result, 3)
        index_mock.assert_not_called()
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
        dry_run_mock.assert_called_once_with(Path.cwd().resolve())

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

    # --- Step 2b: `python` resolution heal (wave 1p7pm) ------------------

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
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=0), \
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
             patch.object(self.mod, "_run_render_platform_surfaces", return_value=0) as render_mock, \
             patch.object(self.mod, "_run_mcp_server_dry_run") as dry_run_mock:
            self.ensure_python_resolves_mock.side_effect = SystemExit(2)
            with self.assertRaises(SystemExit):
                self.mod.main([])

        self.ensure_python_resolves_mock.assert_called_once_with(strict=True)
        render_mock.assert_called_once_with(Path.cwd().resolve())
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
            root = (Path.cwd() / "public-setup-target").resolve()
            rc = self.mod._run_render_platform_surfaces(root)

        self.assertEqual(rc, 0)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], sys.executable)
        self.assertTrue(captured[0][1].endswith("render_platform_surfaces.py"))
        self.assertEqual(captured[0][2:], ["--repo-root", str(root)])

    def test_run_mcp_dry_run_invokes_server_with_generated_mcp_python_shape(self):
        captured: list[list[str]] = []

        def fake_run(cmd, check=False, **kwargs):
            captured.append(list(cmd))
            return _make_completed_process(0)

        with patch.object(self.mod.subprocess, "run", side_effect=fake_run):
            root = (Path.cwd() / "external-target").resolve()
            rc = self.mod._run_mcp_server_dry_run(root)

        self.assertEqual(rc, 0)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][0], "python3")
        self.assertTrue(captured[0][1].endswith("server.py"))
        self.assertIn("--root", captured[0])
        self.assertEqual(captured[0][captured[0].index("--root") + 1], str(root))
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


class PublicSetupReviewProtocolIntegrationTests(unittest.TestCase):
    """Fresh public setup reconciles review carriers in the requested target."""

    def test_setup_refuses_claude_ancestor_escape_before_indexing_or_external_write(self):
        mod = load_setup_wavefoundry()
        index_called = False

        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                nonlocal index_called
                index_called = True
                return 0

        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir)
            root = (outer / "repo").resolve()
            outside = outer / "outside"
            (root / ".wavefoundry" / "framework").mkdir(parents=True)
            outside.mkdir()
            try:
                (root / ".claude").symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")

            import memory_backfill
            with patch.object(mod, "_load_setup_index", return_value=FakeSetupIndex), \
                 patch.object(mod, "_run_mcp_server_dry_run", return_value=0), \
                 patch.object(mod.venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.object(memory_backfill, "sync_inventory", return_value={
                     "run_id": "test-run", "state": "ready_for_index", "eligible_waves": 0,
                 }), \
                 patch.object(memory_backfill, "mark_indexed", return_value=None), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertNotEqual(mod.main(["--root", str(root)]), 0)

            self.assertFalse(index_called)
            self.assertEqual(list(outside.rglob("*")), [])

    def test_setup_refuses_parent_symlink_escape_before_indexing(self):
        mod = load_setup_wavefoundry()
        index_called = False

        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                nonlocal index_called
                index_called = True
                return 0

        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir)
            root = (outer / "repo").resolve()
            outside = outer / "outside"
            (root / ".wavefoundry" / "framework").mkdir(parents=True)
            (root / "docs").mkdir()
            outside.mkdir()
            sentinel = outside / "qa-reviewer.md"
            sentinel.write_text("external sentinel\n", encoding="utf-8")
            (root / "docs" / "agents").symlink_to(outside, target_is_directory=True)

            with patch.object(mod, "_load_setup_index", return_value=FakeSetupIndex), \
                 patch.object(mod, "_run_mcp_server_dry_run", return_value=0), \
                 patch.object(mod.venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertNotEqual(mod.main(["--root", str(root)]), 0)

            self.assertFalse(index_called)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "external sentinel\n")

    def test_setup_refuses_dangling_native_wrapper_parent_before_indexing(self):
        mod = load_setup_wavefoundry()
        index_called = False

        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                nonlocal index_called
                index_called = True
                return 0

        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir)
            root = (outer / "repo").resolve()
            outside = outer / "outside"
            (root / ".wavefoundry" / "framework").mkdir(parents=True)
            (root / "docs" / "agents").mkdir(parents=True)
            (root / "docs" / "agents" / "guru.md").write_text("# Guru\n", encoding="utf-8")
            wrapper = root / ".codex" / "skills" / "auto-guru"
            wrapper.parent.mkdir(parents=True)
            outside.mkdir()
            wrapper.symlink_to(outside, target_is_directory=True)

            with patch.object(mod, "_load_setup_index", return_value=FakeSetupIndex), \
                 patch.object(mod, "_run_mcp_server_dry_run", return_value=0), \
                 patch.object(mod.venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertNotEqual(mod.main(["--root", str(root)]), 0)

            self.assertFalse(index_called)
            self.assertFalse((outside / "SKILL.md").exists())

    def test_setup_root_adds_missing_protocol_preserves_extensions_and_is_idempotent(self):
        mod = load_setup_wavefoundry()
        import render_agent_surfaces as ras
        observed: list[bool] = []
        historical_snapshot: bytes | None = None

        class FakeSetupIndex:
            @staticmethod
            def main(argv=None):
                observed.append((root / "docs" / "agents" / "qa-reviewer.md").is_file())
                self.assertEqual(historical.read_bytes(), historical_snapshot)
                return 0

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            (root / ".wavefoundry" / "framework").mkdir(parents=True)
            target_seeds = _stage_review_protocol_seeds(root)
            config = root / "docs" / "workflow-config.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps({"lifecycle_id_policy": {"scheme_version": "v2"}}),
                encoding="utf-8",
            )
            historical = root / "docs" / "waves" / "abcde historical" / "wave.md"
            historical.parent.mkdir(parents=True)
            historical.write_bytes(
                b"# Historical target wave\n\nproject-authored bytes: do not parse or rewrite\n"
            )
            historical_snapshot = historical.read_bytes()
            historical_events = historical.parent / "events.jsonl"
            historical_events.write_bytes(b'{"historical":true,"opaque":"keep"}\n')
            historical_events_snapshot = historical_events.read_bytes()
            prompt_root = root / "docs" / "prompts"
            target = root / "docs" / "agents" / "code-reviewer.md"
            target.parent.mkdir(parents=True)
            prefix = "# Project Code Reviewer\n\nproject-prefix\n\n"
            suffix = "\n\n## Project extension\n\n- preserve this exactly\n"
            target.write_text(
                prefix + suffix,
                encoding="utf-8",
            )
            original = target.read_bytes()

            with patch.object(mod, "_load_setup_index", return_value=FakeSetupIndex), \
                 patch.object(mod, "_run_mcp_server_dry_run", return_value=0), \
                 patch.object(mod.venv_bootstrap, "ensure_python_resolves", return_value="ok"), \
                 patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}, clear=False), \
                 redirect_stdout(io.StringIO()):
                self.assertEqual(mod.main(["--root", str(root)]), 0)
                first = target.read_bytes()
                self.assertEqual(mod.main(["--root", str(root)]), 0)

            text = first.decode("utf-8")
            self.assertTrue(first.startswith(original), "project-authored bytes must remain an exact prefix")
            self.assertEqual(
                observed,
                [True, True, True, True],
                "dependency and index passes must both see rendered carriers",
            )
            self.assertTrue(text.startswith(prefix))
            self.assertIn(suffix.strip(), text)
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, text)
            self.assertIn("four-way actionability gate", text)
            self.assertIn("Independent-reference verification", text)
            self.assertIn("`independent: false`", text)
            canonical_text = target_seeds.joinpath(
                "209-agent-harness-core.prompt.md"
            ).read_text(encoding="utf-8")
            self.assertIn(
                "Independent-reference verification",
                canonical_text,
            )
            self.assertIn(
                "Implementer-authored evidence remains `independent: false`",
                canonical_text,
            )
            for name in REVIEW_PROTOCOL_SEEDS:
                self.assertEqual(
                    target_seeds.joinpath(name).read_bytes(),
                    (SCRIPTS_ROOT.parent / "seeds" / name).read_bytes(),
                )
            for rel in (
                "docs/agents/qa-reviewer.md",
                "docs/prompts/review-wave.prompt.md",
                "docs/prompts/create-wave.prompt.md",
                "docs/contributing/review-and-evals.md",
            ):
                created = root / rel
                self.assertTrue(created.is_file(), rel)
                created_text = created.read_text(encoding="utf-8")
                self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, created_text)
                self.assertNotIn("waveframework:", created_text)
                self.assertNotIn("wavefoundry:context-efficiency", created_text)
            self.assertIn(
                "zero unintended skips",
                (root / "docs" / "agents" / "qa-reviewer.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "assertion that would falsify",
                (root / "docs" / "agents" / "qa-reviewer.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(target.read_bytes(), first)
            self.assertEqual(historical.read_bytes(), historical_snapshot)
            self.assertEqual(historical_events.read_bytes(), historical_events_snapshot)
            create_text = (
                root / "docs" / "prompts" / "create-wave.prompt.md"
            ).read_text(encoding="utf-8")
            self.assertIn("review-evidence-source: events.jsonl", create_text)
            self.assertEqual(
                create_text.count(ras.CONTEXT_EFFICIENCY_CARRIER_MARKER_BEGIN), 1
            )
            self.assertEqual(
                create_text.count(ras.CONTEXT_EFFICIENCY_CARRIER_MARKER_END), 1
            )
            self.assertIn(ras._context_efficiency_carrier_block(), create_text)
            self.assertNotIn("review-evidence-protocol: 1", create_text)
            self.assertNotIn("```jsonl", create_text)
            for prompt_name in (
                "create-wave.prompt.md",
                "prepare-wave.prompt.md",
                "implement-wave.prompt.md",
                "review-wave.prompt.md",
                "close-wave.prompt.md",
            ):
                self.assertTrue(prompt_root.joinpath(prompt_name).is_file())
                self.assertGreater(
                    prompt_root.joinpath(prompt_name).stat().st_size,
                    500,
                )
            self.assertIn(
                "wave_memory_validate",
                prompt_root.joinpath("review-wave.prompt.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                "wave_memory_validate",
                prompt_root.joinpath("close-wave.prompt.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                ".wavefoundry/logs/",
                (root / ".gitignore").read_text(encoding="utf-8"),
            )
            self.assertFalse(
                (
                    root
                    / ".wavefoundry"
                    / "locks"
                    / "producers"
                ).exists()
            )
            self.assertFalse(
                (root / ".wavefoundry" / "logs" / "context-efficiency.sqlite").exists()
            )
            self.assertFalse(
                (root / "docs" / "agents" / "guru.md").exists(),
                "review reconciliation must run before the Guru-availability guard",
            )

    def test_public_setup_known_bad_unwired_renderer_is_detected_at_index_boundary(self):
        """The public-path fixture fails against the old renderer-unwired setup ordering."""

        mod = load_setup_wavefoundry()
        observed: list[bool] = []

        class DetectMissingCarrierSetupIndex:
            @staticmethod
            def main(argv=None):
                present = (root / "docs" / "agents" / "qa-reviewer.md").is_file()
                observed.append(present)
                return 0 if present else 29

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            (root / ".wavefoundry" / "framework").mkdir(parents=True)
            (root / "docs").mkdir()
            (root / "docs" / "workflow-config.json").write_text("{}\n", encoding="utf-8")
            with patch.object(mod, "_run_render_platform_surfaces", return_value=0), \
                 patch.object(mod, "_load_setup_index", return_value=DetectMissingCarrierSetupIndex), \
                 patch.object(mod, "_run_mcp_server_dry_run", return_value=0), \
                 redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                result = mod.main(["--root", str(root)])

        self.assertEqual(result, 29)
        self.assertEqual(observed, [False])


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
             patch.object(self.mod, "_run_render_platform_surfaces", side_effect=lambda _root: (steps.append("render"), 0)[1]), \
             patch.object(self.mod, "_run_mcp_server_dry_run", side_effect=lambda _root: (steps.append("dryrun"), 0)[1]):
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
                order.append(
                    "setup_deps"
                    if "--deps-only" in (argv or [])
                    else "setup_index"
                )
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
        self.assertEqual(order, ["provision", "setup_deps", "setup_index"])
        pol = json.loads(self.cfg.read_text(encoding="utf-8"))["lifecycle_id_policy"]
        self.assertEqual(pol["scheme_version"], "v2")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
WF_CLI_PATH = SCRIPTS_ROOT / "wf_cli.py"
REPO_ROOT = SCRIPTS_ROOT.parents[2]  # scripts -> framework -> .wavefoundry -> repo root


def load_wf_cli():
    spec = importlib.util.spec_from_file_location("wf_cli", WF_CLI_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wf_cli"] = mod
    spec.loader.exec_module(mod)
    return mod


class WfCliDispatchTests(unittest.TestCase):
    """Wave 1p7tz AC-1: each subcommand routes to the correct entry module with argv pass-through;
    every subcommand re-execs into the venv first EXCEPT `setup` (which stays pre-symlink-safe)."""

    def setUp(self):
        self.mod = load_wf_cli()
        self._orig_argv = list(sys.argv)
        # Never activate the venv in the test process; assert the call instead.
        p = patch.object(self.mod.venv_bootstrap, "activate_tool_venv")
        self.reexec_mock = p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        sys.argv = self._orig_argv

    def _fake_module(self, recorder: dict, *, takes_argv: bool) -> ModuleType:
        m = ModuleType("fake_target")
        if takes_argv:
            def main(argv=None):  # noqa: ANN001
                recorder["argv"] = list(argv) if argv is not None else None
                recorder["sys_argv"] = list(sys.argv)
                return 0
        else:
            def main():
                recorder["argv"] = "NO_ARGV_PARAM"
                recorder["sys_argv"] = list(sys.argv)
                return 0
        m.main = main
        return m

    def _run(self, argv: list[str], recorder: dict, *, takes_argv: bool = True) -> int:
        fake = self._fake_module(recorder, takes_argv=takes_argv)
        with patch("importlib.import_module", return_value=fake):
            return self.mod.main(argv)

    # --- routing + argv pass-through (one per subcommand) ---

    def test_each_subcommand_routes_to_its_module(self):
        expected = {
            "docs-lint": "docs_lint",
            "docs-gardener": "docs_gardener",
            "gate": "wave_gate",
            "dashboard": "dashboard_server",
            "update-indexes": "setup_index",
            "lifecycle-id": "lifecycle_id",
            "upgrade": "upgrade_wavefoundry",
            "setup": "setup_wavefoundry",
            "codebase-map": "gen_codebase_map",
            "render-surfaces": "render_platform_surfaces",
            "secrets-scan": "run_secrets_scan",
            "gpu-doctor": "gpu_doctor",
        }
        for sub, module_name in expected.items():
            with self.subTest(sub=sub):
                with patch("importlib.import_module") as imp:
                    imp.return_value = self._fake_module({}, takes_argv=True)
                    self.mod.main([sub])
                    imp.assert_called_once_with(module_name)

    def test_argv_passthrough_for_argv_main(self):
        rec: dict = {}
        rc = self._run(["gate", "open", "seed_edit_allowed"], rec, takes_argv=True)
        self.assertEqual(rc, 0)
        self.assertEqual(rec["argv"], ["open", "seed_edit_allowed"])
        # sys.argv[0] is the target's own script name; the rest is the forwarded args.
        self.assertEqual(rec["sys_argv"], ["wave_gate.py", "open", "seed_edit_allowed"])

    def test_sys_argv_set_for_no_argv_main(self):
        # docs_lint's main (wave_lint_lib.cli.main) takes NO argv param and reads sys.argv.
        rec: dict = {}
        rc = self._run(["docs-lint", "--date", "2026-06-25"], rec, takes_argv=False)
        self.assertEqual(rc, 0)
        self.assertEqual(rec["argv"], "NO_ARGV_PARAM")  # called with no args
        self.assertEqual(rec["sys_argv"], ["docs_lint.py", "--date", "2026-06-25"])  # sys.argv set

    def test_dashboard_prefix_args_prepended(self):
        # The retired `wave-dashboard` wrapper self-detached + opened the browser → wf dashboard keeps it.
        rec: dict = {}
        self._run(["dashboard"], rec, takes_argv=True)
        self.assertEqual(rec["argv"][:2], ["--daemon", "--open"])

    def test_dashboard_explicit_args_are_forwarded_without_default_open(self):
        rec: dict = {}
        self._run(["dashboard", "--root", "."], rec, takes_argv=True)
        self.assertEqual(rec["argv"], ["--root", "."])

    def test_update_indexes_prefix_args_prepended(self):
        rec: dict = {}
        self._run(["update-indexes"], rec, takes_argv=True)
        self.assertEqual(rec["argv"], ["--background-code", "--verbose"])

    # --- the bootstrap rule: every subcommand re-execs EXCEPT setup ---

    def test_non_setup_subcommand_activates_venv(self):
        for sub in ("docs-lint", "docs-gardener", "gate", "dashboard", "update-indexes",
                    "lifecycle-id", "upgrade", "codebase-map", "render-surfaces",
                    "secrets-scan", "gpu-doctor"):
            with self.subTest(sub=sub):
                self.reexec_mock.reset_mock()
                self._run([sub], {}, takes_argv=True)
                self.reexec_mock.assert_called_once()

    def test_setup_does_not_force_venv_activation(self):
        # `wf setup` must stay on the system interpreter pre-symlink — the dispatcher must NOT call
        # activate for the setup path (setup_wavefoundry's own import-time bootstrap no-ops pre-venv).
        self._run(["setup", "--full"], {}, takes_argv=True)
        self.reexec_mock.assert_not_called()

    # --- help + errors ---

    def test_help_lists_subcommands(self):
        out = MagicMock()
        with patch("sys.stdout", new=__import__("io").StringIO()) as buf:
            rc = self.mod.main(["--help"])
        text = buf.getvalue()
        self.assertEqual(rc, 0)
        for sub in ("docs-lint", "docs-gardener", "gate", "dashboard", "update-indexes",
                    "lifecycle-id", "upgrade", "setup", "codebase-map", "render-surfaces",
                    "secrets-scan", "gpu-doctor"):
            self.assertIn(sub, text)

    def test_unknown_subcommand_errors(self):
        with self.assertRaises(SystemExit) as cm:
            self.mod.main(["bogus"])
        self.assertEqual(cm.exception.code, 2)  # argparse error exit

    def test_prune_framework_is_not_a_subcommand(self):
        # prune_framework.py is intentionally manual-only (run directly, not via wf): its
        # main() -> None used to crash the dispatcher's int() coercion, and it needs the
        # pre-upgrade MANIFEST only the operator has. Lock the removal so it is not re-added.
        self.assertNotIn("prune-framework", self.mod._SUBCOMMANDS)
        with self.assertRaises(SystemExit) as cm:
            self.mod.main(["prune-framework"])
        self.assertEqual(cm.exception.code, 2)  # unknown subcommand -> argparse error

    def test_none_returning_main_coerces_to_exit_zero(self):
        # Regression: a target whose main() returns None (the "exit 0" convention, e.g. the
        # manual prune_framework.py shape) must NOT crash the dispatcher on int(None). The
        # dispatcher coerces None -> 0.
        m = ModuleType("fake_none_main")

        def main():  # no argv param, returns None
            return None

        m.main = main
        with patch("importlib.import_module", return_value=m):
            rc = self.mod.main(["codebase-map"])
        self.assertEqual(rc, 0)


class GpuDoctorSubcommandTests(unittest.TestCase):
    """Wave 1p8gz: `wf gpu-doctor` surfaces the same diagnostics as wave_gpu_doctor by REUSING the
    shared provider_policy backing logic — no duplicated GPU/provider detection."""

    def setUp(self):
        scripts_dir = str(Path(__file__).resolve().parents[1])
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

    def test_registered_in_subcommands(self):
        mod = load_wf_cli()
        self.assertIn("gpu-doctor", mod._SUBCOMMANDS)
        self.assertEqual(mod._SUBCOMMANDS["gpu-doctor"]["module"], "gpu_doctor")
        self.assertEqual(mod._SUBCOMMANDS["gpu-doctor"]["script"], "gpu_doctor.py")

    def test_main_reuses_provider_policy_backing_logic(self):
        # The CLI must call the SAME provider_policy.diagnostic_report / format_diagnostic_report the
        # wave_gpu_doctor MCP tool uses — proving no duplicated detection.
        import gpu_doctor
        import provider_policy

        with patch.object(provider_policy, "diagnostic_report", return_value={"fake": "report"}) as dr, \
             patch.object(provider_policy, "format_diagnostic_report", return_value="DIAG") as fmt, \
             patch("sys.stdout", new=__import__("io").StringIO()) as buf:
            rc = gpu_doctor.main([])
        self.assertEqual(rc, 0)
        dr.assert_called_once()
        fmt.assert_called_once_with({"fake": "report"})
        self.assertIn("DIAG", buf.getvalue())

    def test_gpu_doctor_does_not_duplicate_detection(self):
        # Anti-duplication: gpu_doctor.py must not re-implement provider/GPU detection. It may only
        # delegate — so its source contains the delegation calls, not detection primitives.
        src = (Path(__file__).resolve().parents[1] / "gpu_doctor.py").read_text(encoding="utf-8")
        self.assertIn("provider_policy.diagnostic_report", src)
        self.assertIn("provider_policy.format_diagnostic_report", src)
        # No re-implemented detection: must not define its own provider/GPU probing functions.
        self.assertNotIn("def nvidia_gpu_present", src)
        self.assertNotIn("def available_onnx_providers", src)

    def test_self_bootstraps_into_tool_venv(self):
        # AC-2: like every other subcommand, gpu_doctor activates the shared tool venv in-process.
        src = (Path(__file__).resolve().parents[1] / "gpu_doctor.py").read_text(encoding="utf-8")
        self.assertIn("venv_bootstrap.activate_tool_venv()", src)


def _load_reconcile_scan():
    spec = importlib.util.spec_from_file_location(
        "reconcile_scan", SCRIPTS_ROOT / "reconcile_scan.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["reconcile_scan"] = mod
    spec.loader.exec_module(mod)
    return mod


class NoLiveReferenceToRetiredWrapperTests(unittest.TestCase):
    """Wave 1p7tz AC-4 / 1p8et: no live doc/config names a retired `.wavefoundry/bin/<wrapper>` path.

    The proven scan (patterns + exclusions) now lives in the SHIPPED ``reconcile_scan`` helper (wave
    1p8et) — this guard asserts THROUGH that helper (no duplicated regex), so the test and the
    downstream upgrade-time scan are the single source. The framework pack tree
    (`.wavefoundry/framework/`) is part of the helper's baked-in exclusion set, so the helper's own
    source naming the retired names is not flagged."""

    def setUp(self):
        # The helper imports the one map from render_platform_surfaces; SCRIPTS_ROOT must be importable.
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))
        self.scan = _load_reconcile_scan()

    def test_no_live_file_references_a_retired_wrapper(self):
        # The literal `.wavefoundry/bin/<wrapper>` references and the dynamic/variable bin-join forms
        # are both surfaced by the shared helper. The self-host's own framework pack tree is excluded
        # by the helper, so a green scan over the repo means no LIVE consumer-authored reference exists.
        findings = self.scan.scan_repo(REPO_ROOT)
        offenders = [f"{f.file}:{f.line} (.wavefoundry/bin/{f.retired_surface})" for f in findings]
        self.assertEqual(
            offenders,
            [],
            "live docs/config/scripts must not name a retired bin wrapper (use `wf <subcommand>`):\n"
            + "\n".join(offenders),
        )

    def test_reintroduced_reference_is_caught(self):
        """The guard catches a reintroduced retired-surface reference (proves it is not vacuous)."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs").mkdir()
            offending = root / "docs" / "runbook.md"
            offending.write_text(
                "Run `.wavefoundry/bin/docs-lint` to lint.\n", encoding="utf-8"
            )
            findings = self.scan.scan_repo(root)
            self.assertTrue(findings, "a reintroduced retired-surface reference must be caught")
            self.assertEqual(findings[0].retired_surface, "docs-lint")
            self.assertEqual(findings[0].suggested, "wf docs-lint")


class NoRawCoveredScriptInvocationInOperatorDocsTests(unittest.TestCase):
    r"""Wave 1p88t AC-5: operator/agent-facing guidance must NOT show a runnable raw
    ``python3 .wavefoundry/framework/scripts/<script>.py`` command for a script that HAS a ``wf``
    subcommand — agents/operators copy-paste those and they are fragile across Windows/POSIX. Use
    the ``wf <subcommand>`` form instead.

    COVERED scripts are derived from ``wf_cli._SUBCOMMANDS`` (auto-syncing): a script gains coverage
    the moment it gets a ``wf`` subcommand, and ``prune_framework.py`` (intentionally manual-only,
    removed from the wf surface) is automatically allowlisted.

    SCOPE — operator runbook + operator-facing top-level docs + live seeds. EXCLUDED, with rationale:
      - ``docs/architecture/**`` : design/explanation narration (entry-point ASCII diagrams, data/
        control-flow descriptions, mechanism examples) legitimately names the underlying invocations.
      - ``docs/plans/**``, ``docs/waves/**``, ``docs/reports/**`` : planning + history.
      - ``CHANGELOG.md`` : release history.
      - tests, generated indexes, vcs/build dirs.
    Only a runnable COMMAND invocation (a ``python3``/``python``/``py`` prefix) is flagged; a bare
    prose mention of a script name (``\`docs_lint.py\```) is fine.
    """

    COVERED = sorted({spec["script"] for spec in load_wf_cli()._SUBCOMMANDS.values()})

    PATTERN = re.compile(
        r"(?:python3?|py)\s+\.wavefoundry/framework/scripts/("
        + "|".join(re.escape(s) for s in COVERED) + r")"
    )

    EXCLUDED_DIRS = (
        ".git", "__pycache__", "node_modules", ".wavefoundry/index",
        "docs/architecture", "docs/plans", "docs/waves", "docs/reports",
    )
    EXCLUDED_FILES = ("CHANGELOG.md",)
    SCAN_SUFFIXES = (".md", ".mdc")

    def _iter_operator_docs(self):
        for path in REPO_ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in self.SCAN_SUFFIXES:
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            if any(part in rel for part in self.EXCLUDED_DIRS):
                continue
            if rel in self.EXCLUDED_FILES or "/tests/" in rel:
                continue
            yield path, rel

    def test_operator_docs_prefer_wf_over_raw_covered_script(self):
        offenders = []
        for path, rel in self._iter_operator_docs():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for m in self.PATTERN.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                offenders.append(f"{rel}:{line} — python3 .../{m.group(1)} (use `wf <subcommand>`)")
        self.assertEqual(
            offenders,
            [],
            "operator/agent-facing docs must prefer `wf <subcommand>` over a runnable raw "
            "`python3 .wavefoundry/framework/scripts/<covered>.py` command:\n" + "\n".join(sorted(offenders)),
        )

    def test_prune_framework_is_allowlisted_because_manual_only(self):
        # prune_framework.py is intentionally manual-only (removed from wf), so it must NOT be in the
        # covered set — a raw `python3 ... prune_framework.py` in the upgrade seed is allowed.
        self.assertNotIn("prune_framework.py", self.COVERED)


if __name__ == "__main__":
    unittest.main()

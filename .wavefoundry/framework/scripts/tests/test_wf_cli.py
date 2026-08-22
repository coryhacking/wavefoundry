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
            "techdocs-baseline": "techdocs_baseline",
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
                    "secrets-scan", "gpu-doctor", "techdocs-baseline"):
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
                    "secrets-scan", "gpu-doctor", "techdocs-baseline"):
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
    """Wave 1p8gz: `wf gpu-doctor` surfaces the same diagnostics as wf_gpu_doctor by REUSING the
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
        # wf_gpu_doctor MCP tool uses — proving no duplicated detection.
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


class TechdocsAuditSubcommandTests(unittest.TestCase):
    """Wave 1vqqi: `wf techdocs-audit` is a thin entry over techdocs_audit_lib.audit_techdocs.

    The dispatch test drives the real module through wf_cli with only the venv
    activation mocked, and every mode is checked for writes with a digest over
    git-tracked-shaped state: the entry must never write, and the MCP path's cost
    telemetry (which is gitignored and not a repository write) is out of scope here.
    """

    def setUp(self):
        scripts_dir = str(Path(__file__).resolve().parents[1])
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        self.mod = load_wf_cli()
        self._orig_argv = list(sys.argv)
        p = patch.object(self.mod.venv_bootstrap, "activate_tool_venv")
        self.reexec_mock = p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        sys.argv = self._orig_argv

    @staticmethod
    def _tree(temp_dir: str, *, with_mkdocs: bool = True) -> Path:
        root = (Path(temp_dir) / "Example_Project").resolve()
        meta = "Owner: Engineering\nStatus: active\nLast verified: 2026-08-18\n"
        for rel, title in (
            ("docs/index.md", "Home"),
            ("docs/ARCHITECTURE.md", "Architecture"),
            ("docs/references/project-overview.md", "Project overview"),
            ("docs/prompts/index.md", "Commands"),
        ):
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {title}\n\n{meta}\n", encoding="utf-8")
        (root / "catalog-info.yaml").write_text("kind: Component\n", encoding="utf-8")
        if with_mkdocs:
            block = "\n".join(
                "  " + line for line in
                ["/*", "!/index.md", "!/ARCHITECTURE.md", "!/architecture/", "!/architecture/**",
                 "!/references/", "!/references/**", "!/prompts/", "/prompts/*", "!/prompts/index.md"]
            )
            (root / "mkdocs.yml").write_text(
                "site_name: Example\ndocs_dir: docs\nnav:\n  - Home: index.md\n"
                "  - Project overview: references/project-overview.md\n"
                "  - Architecture: ARCHITECTURE.md\n  - Workflow: prompts/index.md\n"
                "exclude_docs: |\n" + block + "\n",
                encoding="utf-8",
            )
        return root

    @staticmethod
    def _digest(root: Path) -> dict:
        import hashlib
        out = {}
        for path in sorted(root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                out[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return out

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        import io
        import contextlib

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = self.mod.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_registered_in_subcommands(self):
        self.assertIn("techdocs-audit", self.mod._SUBCOMMANDS)
        self.assertEqual(self.mod._SUBCOMMANDS["techdocs-audit"]["module"], "techdocs_audit")
        self.assertEqual(self.mod._SUBCOMMANDS["techdocs-audit"]["script"], "techdocs_audit.py")

    def test_no_findings_but_ungit_tree_degrades_rather_than_claiming_clean(self):
        """A run that could not compute something never reports clean, and exit 1 covers it.

        Outside a git work tree the audience invariant cannot be evaluated at all, so the
        verdict is `degraded` even though no finding fired. That is the whole point of the
        degraded verdict: silence about an unevaluated check would read as a clean site.
        """
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._tree(temp_dir)
            before = self._digest(root)
            rc, out, err = self._run(["techdocs-audit", "--root", str(root), "--json"])
            self.assertEqual(rc, 1, err)
            self.reexec_mock.assert_called()
            envelope = json.loads(out)
            self.assertEqual(envelope["summary"]["verdict"], "degraded")
            self.assertIn("git_unavailable", envelope["degraded"])
            self.assertEqual(envelope["publication"]["survivor_count"], 4)
            self.assertEqual(envelope["findings"], [])
            self.assertEqual(self._digest(root), before)

    def test_clean_verdict_and_exit_zero_when_every_check_is_informative(self):
        """The clean verdict is reachable: a git tree with an uncommitted authoring edit,
        which is exactly the state the workflow's Step 3 runs in."""
        import json
        import shutil
        import subprocess
        import tempfile

        if shutil.which("git") is None:  # pragma: no cover
            self.skipTest("git unavailable")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._tree(temp_dir)
            subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
            for args in (("config", "user.email", "t@example.invalid"), ("config", "user.name", "T")):
                subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "base"], check=True, capture_output=True)
            for rel in ("docs/references/project-overview.md", "docs/ARCHITECTURE.md"):
                path = root / rel
                path.write_text(path.read_text(encoding="utf-8") + "\n## Added by the authoring pass\n",
                                encoding="utf-8")
            before = self._digest(root)
            rc, out, err = self._run(["techdocs-audit", "--root", str(root), "--json"])
            self.assertEqual(rc, 0, err)
            envelope = json.loads(out)
            self.assertEqual(envelope["summary"]["verdict"], "clean")
            self.assertEqual(envelope["degraded"], [])
            self.assertTrue(envelope["audience"]["docs/ARCHITECTURE.md"]["checked"])
            self.assertEqual(self._digest(root), before)

    def test_findings_exit_one_and_text_mode_names_each(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._tree(temp_dir)
            (root / "docs" / "references" / "links.md").write_text(
                "# Links\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-08-18\n\n"
                "[gone](./missing.md)\n", encoding="utf-8")
            before = self._digest(root)
            rc, out, err = self._run(["techdocs-audit", "--root", str(root)])
            self.assertEqual(rc, 1)
            self.assertIn("techdocs-audit: medium techdocs_link_missing", out)
            self.assertIn("techdocs-audit: findings;", out)
            self.assertEqual(self._digest(root), before)

    def test_not_applicable_exits_zero_because_it_is_a_legitimate_state(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._tree(temp_dir, with_mkdocs=False)
            before = self._digest(root)
            rc, out, err = self._run(["techdocs-audit", "--root", str(root), "--json"])
            self.assertEqual(rc, 0)
            envelope = json.loads(out)
            self.assertEqual(envelope["summary"]["verdict"], "not_applicable")
            self.assertIn("mkdocs_absent", envelope["degraded"])
            self.assertIn("techdocs-audit: NOTE degraded: mkdocs_absent", err)
            self.assertEqual(self._digest(root), before)
            # Contrast with the sibling verb, where exit 1 means precondition-unmet:
            # here 1 is an informative result and 0 covers this legitimate state.

    def test_not_applicable_does_not_suppress_an_exit_one_when_findings_exist(self):
        """DEL-5: `not_applicable` is a forced verdict that wins over findings.

        Keying the exit code on the verdict made this combination exit 0 while
        both documented exit-1 conditions held, so a CI consumer chaining on
        exit status read a partial trio and an unauthored landing page as a pass.
        """
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._tree(temp_dir, with_mkdocs=False)
            # The markdown member's marker is an HTML comment; the YAML members
            # use a `#` comment. A generated landing page beside a project-owned
            # catalog file is a mixed trio, which is what reports here.
            marker = ("<!-- wavefoundry: generated missing-only Backstage/TechDocs "
                      "baseline; project-owned, edit freely. -->\n")
            (root / "docs" / "index.md").write_text(
                marker + "# Home\n\nOwner: Engineering\nStatus: active\n"
                "Last verified: 2026-08-18\n", encoding="utf-8")
            before = self._digest(root)
            rc, out, err = self._run(["techdocs-audit", "--root", str(root), "--json"])
            envelope = json.loads(out)
            self.assertEqual(envelope["summary"]["verdict"], "not_applicable")
            self.assertTrue(envelope["findings"], "the trio checks must still report")
            self.assertEqual(rc, 1, err)
            self.assertEqual(self._digest(root), before)

    def test_an_unresolvable_root_exits_two_rather_than_raising(self):
        """Root resolution sat outside main()'s try, so this raised.

        `expanduser()` raises RuntimeError for an unknown user, and the entry
        promises an exit code. Moving the resolution inside the try shipped with
        no test at all, so the mutation survived.
        """
        rc, out, err = self._run(["techdocs-audit", "--root", "~nosuchuser1234/x"])
        self.assertEqual(rc, 2, out)
        self.assertNotIn("Traceback", err)

    def test_could_not_run_exits_two(self):
        """AC-5 pins 0 / 1 / 2; only 0 and 1 had an assertion for this subcommand."""
        import tempfile
        from unittest import mock

        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._tree(temp_dir)
            before = self._digest(root)
            with mock.patch("techdocs_audit_lib.run_techdocs_audit",
                            side_effect=OSError("unreadable tree")):
                rc, out, err = self._run(["techdocs-audit", "--root", str(root)])
            self.assertEqual(rc, 2, out)
            self.assertIn("ERROR the audit could not run", err)
            self.assertEqual(self._digest(root), before)

    def test_timeout_is_a_degraded_json_report_and_exit_one(self):
        """AC-10: the CLI surfaces the bounded runner's timeout envelope."""
        import json
        import tempfile
        from unittest import mock

        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._tree(temp_dir)
            before = self._digest(root)
            import techdocs_audit_lib

            timeout_report = techdocs_audit_lib._timeout_report(root)
            with mock.patch("techdocs_audit_lib.run_techdocs_audit",
                            return_value=timeout_report) as run:
                rc, out, err = self._run(
                    ["techdocs-audit", "--root", str(root), "--json"])

            self.assertEqual(rc, 1, err)
            envelope = json.loads(out)
            self.assertEqual(envelope["degraded"], ["audit_timeout"])
            self.assertEqual(envelope["summary"]["verdict"], "degraded")
            self.assertIn("NOTE degraded: audit_timeout", err)
            run.assert_called_once_with(root, compare_to=None)
            self.assertEqual(self._digest(root), before)

    def test_help_lists_the_subcommand_with_a_description(self):
        import io
        import contextlib

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.mod.main(["--help"])
        rendered = out.getvalue()
        self.assertIn("techdocs-audit", rendered)

        # AC-5 requires it to APPEAR in help, which a bare name does not satisfy.
        # Asserted over every subcommand rather than just this one, so the next
        # verb added without a description fails here too.
        parser = self.mod._build_parser()
        sub_action = next(a for a in parser._subparsers._group_actions
                          if getattr(a, "_choices_actions", None))
        undescribed = sorted(c.dest for c in sub_action._choices_actions if not c.help)
        self.assertEqual(undescribed, [])


class TechdocsBaselineSubcommandTests(unittest.TestCase):
    """Wave 1vj4e (1vj4d): `wf techdocs-baseline` is a thin entry over
    render_agent_surfaces.render_techdocs_baseline; the faithful dispatch test drives the real
    module through wf_cli with only the venv activation mocked."""

    def setUp(self):
        scripts_dir = str(Path(__file__).resolve().parents[1])
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        self.mod = load_wf_cli()
        self._orig_argv = list(sys.argv)
        p = patch.object(self.mod.venv_bootstrap, "activate_tool_venv")
        self.reexec_mock = p.start()
        self.addCleanup(p.stop)

    def tearDown(self):
        sys.argv = self._orig_argv

    @staticmethod
    def _target(temp_dir: str, *, targets: bool = True) -> Path:
        import render_agent_surfaces as ras

        root = (Path(temp_dir) / "Example_Project").resolve()
        (root / "docs" / "references").mkdir(parents=True)
        (root / "docs" / "prompts").mkdir(parents=True)
        if targets:
            for target in ras.TECHDOCS_PRECONDITION_TARGETS:
                (root / target).write_text("# t\n", encoding="utf-8")
        return root

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        import io
        import contextlib

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = self.mod.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_registered_in_subcommands(self):
        self.assertIn("techdocs-baseline", self.mod._SUBCOMMANDS)
        self.assertEqual(self.mod._SUBCOMMANDS["techdocs-baseline"]["module"], "techdocs_baseline")
        self.assertEqual(self.mod._SUBCOMMANDS["techdocs-baseline"]["script"], "techdocs_baseline.py")

    def test_faithful_dispatch_generates_the_trio_and_prints_the_json_envelope(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._target(temp_dir)
            rc, out, err = self._run(["techdocs-baseline", "--root", str(root), "--json"])
            self.assertEqual(rc, 0, err)
            # The dispatcher activates the venv in-process (the entry module also does at import).
            self.reexec_mock.assert_called()
            for rel in ("catalog-info.yaml", "mkdocs.yml", "docs/index.md"):
                self.assertTrue((root / rel).is_file(), rel)
            envelope = json.loads(out)
            self.assertEqual(
                sorted(envelope),
                ["generated_paths", "missing_targets", "partial", "preserved_paths", "refusal", "written_paths"],
            )
            self.assertEqual(envelope["written_paths"], ["catalog-info.yaml", "mkdocs.yml", "docs/index.md"])
            self.assertEqual(envelope["generated_paths"], envelope["written_paths"])
            self.assertEqual(envelope["preserved_paths"], [])
            self.assertEqual(envelope["missing_targets"], [])
            self.assertIsNone(envelope["partial"])
            self.assertIsNone(envelope["refusal"])
            self.assertEqual(err, "")
            self.assertIn("name: example-project-docs", (root / "catalog-info.yaml").read_text(encoding="utf-8"))

            # Text mode on a rerun: preserved lines on stdout, nothing on stderr, exit 0.
            rc, out, err = self._run(["techdocs-baseline", "--root", str(root)])
            self.assertEqual(rc, 0)
            self.assertEqual(
                out.splitlines(),
                [f"techdocs-baseline: preserved {rel}" for rel in ("catalog-info.yaml", "mkdocs.yml", "docs/index.md")],
            )
            self.assertEqual(err, "")

            # Mixed trio: exit 0, one WARNING on stderr, `partial` is the record.
            (root / "mkdocs.yml").write_text("site_name: Mine\n", encoding="utf-8")
            rc, out, err = self._run(["techdocs-baseline", "--root", str(root), "--json"])
            self.assertEqual(rc, 0)
            self.assertEqual(err.count("techdocs-baseline: WARNING Backstage/TechDocs baseline is partial"), 1)
            envelope = json.loads(out)
            self.assertEqual(envelope["partial"]["code"], "backstage_techdocs_partial")
            self.assertEqual(envelope["partial"]["preserved_paths"], ["mkdocs.yml"])
            self.assertEqual(envelope["written_paths"], [])

    def test_post_preflight_failure_reports_what_was_written(self):
        """A failure after preflight must not claim 'nothing written' (delivery finding DEL-2).

        Two shapes share exit 2: the preflight refusal, where the tree really is untouched,
        and a write failure on a later member, where earlier members are on disk. The ERROR
        line and the envelope have to tell them apart.
        """

        import json
        import tempfile

        import render_agent_surfaces as ras

        real = ras._write_review_carrier_text

        def flaky(path, content, *, exclusive=False):
            if path.name == "mkdocs.yml":
                raise PermissionError(13, "Permission denied", str(path))
            return real(path, content, exclusive=exclusive)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._target(temp_dir)
            with patch.object(ras, "_write_review_carrier_text", side_effect=flaky):
                rc, out, err = self._run(["techdocs-baseline", "--root", str(root), "--json"])
            self.assertEqual(rc, 2)
            self.assertTrue((root / "catalog-info.yaml").is_file())
            self.assertFalse((root / "mkdocs.yml").exists())
            envelope = json.loads(out)
            self.assertEqual(envelope["written_paths"], ["catalog-info.yaml"])
            self.assertEqual(envelope["generated_paths"], ["catalog-info.yaml"])
            self.assertIn("Permission denied", envelope["refusal"])
            self.assertIn("wrote catalog-info.yaml before failing", envelope["refusal"])
            self.assertEqual(err.count("techdocs-baseline: ERROR"), 1)
            self.assertNotIn("(nothing written)", err)

            # Control: the preflight refusal on an untouched tree still says nothing was written.
            other = self._target(temp_dir + "/second")
            (other / "docs" / "index.md").mkdir()
            rc, out, err = self._run(["techdocs-baseline", "--root", str(other), "--json"])
            self.assertEqual(rc, 2)
            self.assertIn("(nothing written)", err)
            self.assertEqual(json.loads(out)["written_paths"], [])
            self.assertFalse((other / "catalog-info.yaml").exists())

    def test_precondition_and_refusal_exit_codes(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._target(temp_dir, targets=False)
            rc, out, err = self._run(["techdocs-baseline", "--root", str(root), "--json"])
            self.assertEqual(rc, 1)
            self.assertEqual(err.count("techdocs-baseline: ERROR precondition unmet"), 1)
            for target in ("docs/references/project-overview.md", "docs/ARCHITECTURE.md", "docs/prompts/index.md"):
                self.assertIn(target, err)
            envelope = json.loads(out)
            self.assertEqual(len(envelope["missing_targets"]), 3)
            self.assertEqual(envelope["written_paths"], [])
            for rel in ("catalog-info.yaml", "mkdocs.yml", "docs/index.md"):
                self.assertFalse((root / rel).exists(), rel)
            # Text mode: the one stderr line, empty stdout.
            rc, out, err = self._run(["techdocs-baseline", "--root", str(root)])
            self.assertEqual(rc, 1)
            self.assertEqual(out, "")
            self.assertEqual(len(err.splitlines()), 1)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = self._target(temp_dir)
            (root / "docs" / "index.md").mkdir()
            rc, out, err = self._run(["techdocs-baseline", "--root", str(root), "--json"])
            self.assertEqual(rc, 2)
            self.assertIn("techdocs-baseline: ERROR", err)
            envelope = json.loads(out)
            self.assertIn("not a regular file", envelope["refusal"])
            self.assertEqual(envelope["written_paths"], [])
            self.assertFalse((root / "catalog-info.yaml").exists())
            self.assertFalse((root / "mkdocs.yml").exists())

    def test_thin_entry_delegates_and_self_bootstraps(self):
        src = (Path(__file__).resolve().parents[1] / "techdocs_baseline.py").read_text(encoding="utf-8")
        self.assertIn("venv_bootstrap.activate_tool_venv()", src)
        self.assertIn("render_techdocs_baseline", src)
        # No re-implemented behavior: the entry never opens or writes the trio itself.
        for forbidden in ("os.open(", "TECHDOCS_BASELINES", "{{entity_name}}", "def techdocs_entity_name"):
            self.assertNotIn(forbidden, src)


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
        # The literal `.wavefoundry/bin/<wrapper>` references, the dynamic/variable bin-join forms,
        # and (wave 1t72b / 1t6p8) renamed-MCP-tool references are all surfaced by the shared helper.
        # The guard asserts the EDITABLE channel only: host permission/allow-rule findings route to
        # the operator-flag channel by design (an agent must not self-edit those files), so they are
        # surfaced at upgrade time rather than gating the framework suite on operator-owned files.
        reconciliation, _host_flags, _prov_flags = self.scan.scan_repo_channels(REPO_ROOT)
        offenders = [f"{f.file}:{f.line} ({f.matched} -> {f.suggested})" for f in reconciliation]
        self.assertEqual(
            offenders,
            [],
            "live editable docs/config/scripts must not name a retired or renamed surface:\n"
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


class RetiredContentReferenceScanTests(unittest.TestCase):
    """1v4mv: the scan covers two retired surfaces beyond the bin wrappers.

    These need their own pattern family. The pre-existing families each match a
    NAME inside a fixed literal shape (``.wavefoundry/bin/<name>``,
    ``mcp__wavefoundry__<tool>``), so a retired SUBSYSTEM cannot be expressed by
    adding an entry to the shared map — that would only search for
    ``.wavefoundry/bin/journal``.
    """

    def setUp(self):
        import tempfile

        self.scan = _load_reconcile_scan()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _write(self, rel: str, body: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def test_journal_instruction_shapes_are_reported(self):
        """AC-2, using the four shapes the field report named."""
        self._write(
            "docs/agents/reviewer.md",
            "Stop and journal when:\n"
            "- something\n"
            "## Associated journal\n"
            "Memory responsibility: journal the outcome\n"
            "At close, distill journals.\n"
            "See docs/agents/journals/reviewer.md for history.\n",
        )
        findings = self.scan.scan_repo(self.root)
        matched = " | ".join(f.matched for f in findings)
        self.assertIn("Stop and journal when:", matched)
        self.assertIn("Associated journal", matched)
        self.assertIn("Memory responsibility: journal", matched)
        self.assertIn("distill journals", matched)
        self.assertIn("docs/agents/journals/reviewer.md", matched)
        for finding in findings:
            self.assertIn("docs/agents/memory/", finding.suggested)

    def test_stale_prompt_extension_reference_is_reported(self):
        """AC-3: resolution-based, so the twin must exist for a hit to fire."""
        self._write("docs/prompts/close-wave.prompt.md", "# Close wave\n")
        self._write("docs/agents/guide.md", "See docs/prompts/close-wave.md for closure.\n")
        findings = [
            f for f in self.scan.scan_repo(self.root)
            if f.retired_surface == "prompt .md extension"
        ]
        self.assertEqual(len(findings), 1, findings)
        self.assertEqual(findings[0].matched, "docs/prompts/close-wave.md")
        self.assertIn("docs/prompts/close-wave.prompt.md", findings[0].suggested)

    def test_prompt_reference_without_a_prompt_md_twin_is_not_reported(self):
        """AC-6 for this surface: a genuinely-.md prompt doc is not stale.
        Textual matching alone would flag it; resolution is what makes the
        pattern safe to run over a whole tree."""
        self._write("docs/prompts/index.md", "# Index\n")
        self._write("docs/agents/guide.md", "See docs/prompts/index.md for the catalog.\n")
        self.assertEqual(
            [f for f in self.scan.scan_repo(self.root)
             if f.retired_surface == "prompt .md extension"],
            [],
        )

    def test_every_stale_reference_on_one_line_is_reported(self):
        """AC-4: per-line-first reporting would under-count, which is the
        failure mode being fixed — one downstream line broke three at once."""
        self._write("docs/prompts/a.prompt.md", "a\n")
        self._write("docs/prompts/b.prompt.md", "b\n")
        self._write("docs/prompts/c.prompt.md", "c\n")
        self._write(
            "docs/agents/guide.md",
            "Read docs/prompts/a.md, docs/prompts/b.md and docs/prompts/c.md.\n",
        )
        findings = [
            f for f in self.scan.scan_repo(self.root)
            if f.retired_surface == "prompt .md extension"
        ]
        self.assertEqual(len(findings), 3, findings)
        self.assertEqual({f.line for f in findings}, {1})
        self.assertEqual(
            sorted(f.matched for f in findings),
            ["docs/prompts/a.md", "docs/prompts/b.md", "docs/prompts/c.md"],
        )

    def test_scan_mutates_nothing(self):
        """AC-5: the report-only contract, asserted by comparing bytes."""
        path = self._write(
            "docs/agents/reviewer.md", "Stop and journal when:\n- something\n"
        )
        before = path.read_bytes()
        self.assertTrue(self.scan.scan_repo(self.root), "fixture must produce findings")
        self.assertEqual(path.read_bytes(), before)

    def test_clean_repository_reports_nothing(self):
        """AC-6: a scan that cries wolf on clean repos gets ignored."""
        self._write("docs/agents/reviewer.md", "Record a memory candidate when:\n- something\n")
        self._write("docs/prompts/close-wave.prompt.md", "# Close wave\n")
        self.assertEqual(self.scan.scan_repo(self.root), [])

    def test_live_migrate_journals_alias_is_not_reported(self):
        """Found by running the scan against this repository: `Distill journals`
        is ALSO the documented legacy alias of the LIVE `Migrate journals`
        command, so flagging it would tell operators to delete a working alias.
        The exemption is line-scoped and must not silence a bare instruction."""
        self._write(
            "docs/prompts/index.md",
            "| **Migrate journals** | one-time retirement "
            "(legacy alias: **Distill journals**) | seed-210 |\n"
            "At close, distill journals.\n",
        )
        findings = self.scan.scan_repo(self.root)
        self.assertEqual([f.line for f in findings], [2], findings)

    def test_wave_archives_are_not_reported(self):
        """AC-8: historical records legitimately narrate the retired system."""
        self._write("docs/waves/1abcd wave/wave.md", "Stop and journal when:\n")
        self._write("docs/agents/memory/1abcd-mem note.md", "Associated journal\n")
        self.assertEqual(self.scan.scan_repo(self.root), [])


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


class HistoricalRecordDispositionTests(unittest.TestCase):
    """1v7a1: a finding that is correct AS WRITTEN can be settled once.

    The scan had one disposition, unresolved, so the only way to silence a
    sentence recording that something was retired was to rewrite that sentence.
    The framework's own seeded policy forbids exactly that: seed-160 and
    seed-220 both state "retiring a file removes the file, not the historical
    record of it". Field-reported downstream on 1.16.2.
    """

    def setUp(self):
        import tempfile

        self.scan = _load_reconcile_scan()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _write(self, rel: str, body: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    def _mixed_file(self) -> Path:
        """One file, one historical record AND one live instruction."""
        return self._write(
            "docs/agents/session-handoff.md",
            "All 17 files under docs/agents/journals/ were pristine scaffolds.\n"
            "Stop and journal when: something notable happens.\n",
        )

    def _disposition(self, ref) -> None:
        import json as _json

        path = self.root / self.scan.DISPOSITIONS_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _json.dumps([
                {
                    "key": self.scan.disposition_key(ref),
                    "status": self.scan.HISTORICAL_RECORD,
                    "file": ref.file,
                    "matched": ref.matched,
                }
            ], indent=2) + "\n",
            encoding="utf-8",
        )

    def _historical_ref(self):
        return next(
            r for r in self.scan.scan_repo(self.root)
            if "journals/" in r.matched
        )

    def test_dispositioned_finding_stops_reporting(self):
        """AC-1, asserted through the reported channel rather than the store."""
        self._mixed_file()
        self._disposition(self._historical_ref())
        reconciliation, _host, _prov = self.scan.scan_repo_channels(self.root)
        self.assertFalse(
            [r for r in reconciliation if "journals/" in r.matched], reconciliation
        )

    def test_sibling_finding_in_the_same_file_still_reports(self):
        """AC-2: per finding, not per file. File-level suppression would silence
        real findings, which is worse than the recurrence it fixes."""
        self._mixed_file()
        self._disposition(self._historical_ref())
        reconciliation, _host, _prov = self.scan.scan_repo_channels(self.root)
        self.assertTrue(
            [r for r in reconciliation if "Stop and journal when" in r.matched],
            reconciliation,
        )

    def test_disposition_persists_across_runs(self):
        """AC-3: the recurrence is upgrade-time, so an in-process marking fixes
        nothing. Re-read from disk on a fresh scan."""
        self._mixed_file()
        self._disposition(self._historical_ref())
        for _ in range(2):
            reconciliation, _h, _p = self.scan.scan_repo_channels(self.root)
            self.assertFalse([r for r in reconciliation if "journals/" in r.matched])

    def test_disposition_does_not_survive_a_text_change(self):
        """AC-4, the hard one. A disposition that outlives its finding is a
        blanket suppression wearing a per-finding label."""
        path = self._mixed_file()
        self._disposition(self._historical_ref())
        path.write_text(
            "All 4 files under docs/agents/journals/older/ were pristine scaffolds.\n",
            encoding="utf-8",
        )
        reconciliation, _h, _p = self.scan.scan_repo_channels(self.root)
        self.assertTrue(
            [r for r in reconciliation if "journals/" in r.matched],
            "changed text must report as a NEW finding",
        )

    def test_line_movement_does_not_resurrect_a_disposition(self):
        """The other half of AC-4's balance: editing prose ELSEWHERE in the file
        moves the line but not the judgment, so a settled finding stays settled."""
        path = self._mixed_file()
        self._disposition(self._historical_ref())
        path.write_text(
            "A new leading paragraph.\n\n" + path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        reconciliation, _h, _p = self.scan.scan_repo_channels(self.root)
        self.assertFalse([r for r in reconciliation if "journals/" in r.matched])

    def test_unmarked_repository_is_unaffected(self):
        """AC-5: repositories that never disposition anything behave as before."""
        self._mixed_file()
        reconciliation, _h, _p = self.scan.scan_repo_channels(self.root)
        self.assertEqual(len(reconciliation), 2, reconciliation)

    def test_scan_repo_still_returns_dispositioned_findings(self):
        """Suppression is at the reported-channel boundary only, so an audit can
        still see what was dispositioned away rather than it vanishing."""
        self._mixed_file()
        self._disposition(self._historical_ref())
        self.assertTrue(
            [r for r in self.scan.scan_repo(self.root) if "journals/" in r.matched]
        )

    def test_malformed_store_fails_open(self):
        """A corrupt store must not suppress anything. Fail-closed would turn a
        broken file into an invisible gap, which is the failure this channel
        exists to prevent."""
        self._mixed_file()
        path = self.root / self.scan.DISPOSITIONS_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")
        reconciliation, _h, _p = self.scan.scan_repo_channels(self.root)
        self.assertEqual(len(reconciliation), 2, reconciliation)

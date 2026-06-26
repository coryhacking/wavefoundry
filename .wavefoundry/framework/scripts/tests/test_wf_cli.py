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

    def test_update_indexes_prefix_args_prepended(self):
        rec: dict = {}
        self._run(["update-indexes"], rec, takes_argv=True)
        self.assertEqual(rec["argv"], ["--background-code", "--verbose"])

    # --- the bootstrap rule: every subcommand re-execs EXCEPT setup ---

    def test_non_setup_subcommand_activates_venv(self):
        for sub in ("docs-lint", "docs-gardener", "gate", "dashboard", "update-indexes",
                    "lifecycle-id", "upgrade"):
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
                    "lifecycle-id", "upgrade", "setup"):
            self.assertIn(sub, text)

    def test_unknown_subcommand_errors(self):
        with self.assertRaises(SystemExit) as cm:
            self.mod.main(["bogus"])
        self.assertEqual(cm.exception.code, 2)  # argparse error exit


class NoLiveReferenceToRetiredWrapperTests(unittest.TestCase):
    """Wave 1p7tz AC-4: no live doc/config names a retired `.wavefoundry/bin/<wrapper>` path.

    Scope of "live": the operator-instruction surface — root agent/config files, `docs/` (excluding
    `docs/waves/` historical wave records), framework seeds + framework docs, and editor/host configs.
    EXCLUDED (history, like wave records): `docs/waves/`, `CHANGELOG.md` (release history records what
    a past release shipped), and the test files themselves (which reference the names to assert they
    are gone)."""

    RETIRED = ("docs-lint", "docs-gardener", "wave-gate", "update-indexes", "lifecycle-id",
               "wave-dashboard", "upgrade-wavefoundry", "setup-wavefoundry", "mcp-server")

    # `.wavefoundry/bin/<wrapper>` where <wrapper> is one of the retired names (word-boundary after).
    PATTERN = re.compile(
        r"\.wavefoundry/bin/(" + "|".join(re.escape(w) for w in RETIRED) + r")(?![\w-])"
    )

    _RETIRED_ALT = "|".join(re.escape(w) for w in RETIRED)

    # Dynamic path-join construction: `... / "bin" / "<wrapper>"` (e.g. the pre-1p7tz
    # `REPO_ROOT / ".wavefoundry" / "bin" / "docs-lint"`). A literal-string scan misses these — this
    # flags a quoted `"bin"` segment immediately joined to a quoted retired-wrapper-name segment.
    DYNAMIC_PATTERN = re.compile(r"""["']bin["']\s*/\s*["'](""" + _RETIRED_ALT + r""")["']""")

    # Variable bin-dir join: `<bin-ish var> / "<wrapper>"` (e.g. `bin_dir / "docs-lint"`) — the
    # demonstrated false-negative of the `"bin" / ...` form. Keyed on a variable whose name contains
    # `bin` joined to a quoted RETIRED name. Because `wf` and the `_RETIRED_BIN_WRAPPERS` tuple entries
    # are NOT in RETIRED, `bin_dir / "wf"` and the renderer's own deletion list never match. Guard-
    # hardening only — no live offender exists today.
    VAR_BINDIR_PATTERN = re.compile(
        r"""\b\w*bin\w*\s*/\s*["'](""" + _RETIRED_ALT + r""")["']"""
    )

    EXCLUDED_DIRS = (".git", "docs/waves", "__pycache__", ".wavefoundry/index", "node_modules")
    EXCLUDED_FILES = ("CHANGELOG.md",)
    SCAN_SUFFIXES = (".md", ".mdc", ".json", ".py")

    def _iter_live_files(self):
        for path in REPO_ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in self.SCAN_SUFFIXES:
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            if any(part in rel for part in self.EXCLUDED_DIRS):
                continue
            if rel in self.EXCLUDED_FILES:
                continue
            # The test files themselves name the retired wrappers to assert they are gone.
            if "/tests/" in rel and path.name.startswith("test_"):
                continue
            yield path, rel

    def test_no_live_file_references_a_retired_wrapper(self):
        offenders = []
        for path, rel in self._iter_live_files():
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for m in self.PATTERN.finditer(text):
                offenders.append(f"{rel}: .wavefoundry/bin/{m.group(1)}")
        self.assertEqual(
            offenders,
            [],
            "live docs/config must not name a retired bin wrapper (use `wf <subcommand>`):\n"
            + "\n".join(offenders),
        )

    def test_no_dynamic_bin_wrapper_construction_in_scripts(self):
        """Wave 1p7tz: catch DYNAMIC bin-wrapper path-joins in the framework `.py` scripts that the
        literal-string scan misses — both `... / "bin" / "<wrapper>"` (the pre-fix hook-body
        `REPO_ROOT / ".wavefoundry" / "bin" / "docs-lint"` form) AND a variable bin-dir join
        `<bin-ish var> / "<wrapper>"` (e.g. `bin_dir / "docs-lint"` — the demonstrated false-negative).
        Scopes to scripts (not docs); excludes the test files. Won't false-positive on
        `_RETIRED_BIN_WRAPPERS` (bare strings, no `/` adjacency) or `bin_dir / "wf"` (`wf` is not a
        RETIRED name). Limitation: it keys on the literal RETIRED names, so a fully indirected
        `bin_dir / some_name_var` is not caught — guard-hardening, not a proof of absence."""
        scripts_dir = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
        offenders = []
        for path in sorted(scripts_dir.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for pat, label in ((self.DYNAMIC_PATTERN, '"bin" /'), (self.VAR_BINDIR_PATTERN, "<bin-var> /")):
                for m in pat.finditer(text):
                    line = text.count("\n", 0, m.start()) + 1
                    offenders.append(f"{path.name}:{line} — {label} \"{m.group(1)}\"")
        self.assertEqual(
            offenders,
            [],
            "framework scripts must not construct a retired bin-wrapper path "
            "(invoke the script under sys.executable / _preferred_python instead):\n"
            + "\n".join(sorted(set(offenders))),
        )


if __name__ == "__main__":
    unittest.main()

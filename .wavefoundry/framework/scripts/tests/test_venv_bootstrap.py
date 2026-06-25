from __future__ import annotations

import ast
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch


SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
VENV_BOOTSTRAP_PATH = SCRIPTS_ROOT / "venv_bootstrap.py"


def load_venv_bootstrap():
    spec = importlib.util.spec_from_file_location("venv_bootstrap", VENV_BOOTSTRAP_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["venv_bootstrap"] = mod
    spec.loader.exec_module(mod)
    return mod


vb = load_venv_bootstrap()


class LayoutTests(unittest.TestCase):
    # The Windows *branch selection* is tested via the pure relpath helper: a
    # concrete WindowsPath cannot be instantiated on a POSIX runner, so real nt
    # path behavior is covered by 1p7pm AC-6 (operator smoke), not here.
    def test_relpath_windows(self):
        self.assertEqual(vb._venv_python_relpath("nt"), ("Scripts", "python.exe"))

    def test_relpath_posix(self):
        self.assertEqual(vb._venv_python_relpath("posix"), ("bin", "python"))

    def test_tool_venv_python_honors_env(self):
        with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": "/custom/venv"}):
            # Real os.name on the test box is posix.
            self.assertEqual(vb.tool_venv_python(), Path("/custom/venv/bin/python"))

    def test_tool_venv_base_expands_user(self):
        env = {k: v for k, v in os.environ.items() if k != "WAVEFOUNDRY_TOOL_VENV"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                vb.tool_venv_base(), Path("~/.wavefoundry/venv").expanduser()
            )


class RunningInsideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.venv = Path(self.tmp.name) / "venv"
        self.py = self.venv / "bin" / "python"

    def test_true_when_prefix_is_venv(self):
        with patch.object(vb.sys, "prefix", str(self.venv)):
            self.assertTrue(vb._running_inside_venv(self.py))

    def test_false_when_prefix_elsewhere(self):
        with patch.object(vb.sys, "prefix", str(Path(self.tmp.name) / "other")):
            self.assertFalse(vb._running_inside_venv(self.py))


class ReexecTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.venv = Path(self.tmp.name) / "venv"
        (self.venv / "bin").mkdir(parents=True)
        self.py = self.venv / "bin" / "python"
        self.py.write_text("")  # make it exist
        self.absent = Path(self.tmp.name) / "absent" / "bin" / "python"

    def test_noop_when_venv_absent(self):
        # Tier 1 (fresh bootstrap): no venv yet ⇒ run on the current interpreter,
        # never re-exec, never block setup from creating the venv.
        with patch.object(vb, "tool_venv_python", return_value=self.absent), patch.object(
            vb.os, "execv"
        ) as execv, patch.object(vb.subprocess, "run") as run:
            vb.reexec_into_tool_venv()
        execv.assert_not_called()
        run.assert_not_called()

    def test_noop_when_already_inside_venv(self):
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "_running_inside_venv", return_value=True
        ), patch.object(vb.os, "execv") as execv, patch.object(
            vb.subprocess, "run"
        ) as run:
            vb.reexec_into_tool_venv()
        execv.assert_not_called()
        run.assert_not_called()

    def test_posix_reexecs_via_execv(self):
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "_running_inside_venv", return_value=False
        ), patch.object(vb.os, "name", "posix"), patch.object(
            vb.os, "execv"
        ) as execv, patch.object(vb.subprocess, "run") as run:
            vb.reexec_into_tool_venv()
        execv.assert_called_once()
        self.assertEqual(execv.call_args.args[0], str(self.py))
        run.assert_not_called()

    def test_windows_reexecs_via_subprocess_never_execv(self):
        # AC-3: os.execv on Windows orphans the host stdio pipe — must use subprocess
        # and preserve the child's exit code. (tool_venv_python + _running_inside_venv
        # are mocked so no concrete WindowsPath is instantiated on this POSIX runner.)
        result = MagicMock(returncode=7)
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "_running_inside_venv", return_value=False
        ), patch.object(vb.os, "name", "nt"), patch.object(
            vb.os, "execv"
        ) as execv, patch.object(vb.subprocess, "run", return_value=result) as run:
            with self.assertRaises(SystemExit) as ctx:
                vb.reexec_into_tool_venv()
        self.assertEqual(ctx.exception.code, 7)
        run.assert_called_once()
        execv.assert_not_called()

    def test_emits_no_stdout(self):
        # AC-2: a stdout byte before the MCP JSON-RPC handshake corrupts it.
        buf = io.StringIO()
        with redirect_stdout(buf), patch.object(
            vb, "tool_venv_python", return_value=self.absent
        ):
            vb.reexec_into_tool_venv()
        self.assertEqual(buf.getvalue(), "")


class StdlibOnlyTests(unittest.TestCase):
    def test_imports_are_stdlib_only(self):
        allowed = {"__future__", "os", "shutil", "subprocess", "sys", "pathlib"}
        tree = ast.parse(VENV_BOOTSTRAP_PATH.read_text(encoding="utf-8"))
        mods: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    mods.add(n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module.split(".")[0])
        self.assertTrue(
            mods <= allowed, f"venv_bootstrap has non-stdlib imports: {mods - allowed}"
        )


class FreshBootstrapTests(unittest.TestCase):
    # AC-5 (P0/P1): on a fresh box (no venv) the bootstrap must no-op so it never
    # blocks setup from creating the venv. (Full end-to-end is 1p7pm AC-6 smoke.)
    def test_noop_then_venv_path_creatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv_base = Path(tmp) / "venv"  # does not exist yet
            with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_base)}):
                self.assertFalse(vb.tool_venv_python().exists())
                with patch.object(vb.os, "execv") as execv, patch.object(
                    vb.subprocess, "run"
                ) as run:
                    vb.reexec_into_tool_venv()  # must not raise
                execv.assert_not_called()  # no re-exec ⇒ setup proceeds on system python
                run.assert_not_called()
                # The venv dir is resolvable, so setup can build it there.
                self.assertEqual(vb.tool_venv_python().parent.parent, venv_base)


class SingleResolverScanTests(unittest.TestCase):
    # AC-6 (goal B): WAVEFOUNDRY_TOOL_VENV — the venv-resolution entry point — must be
    # read in exactly one place (venv_bootstrap). Anything else duplicates the resolver.
    ALLOWED = {"venv_bootstrap.py"}
    # Wave 1p7pn closed goal B: render_platform_surfaces no longer emits TOOL_VENV into any rendered
    # bin/hook/git-hook body (1p7pm retired the bin forwarders + rendered-hook resolver; 1p7pn routed
    # the git-hook bodies onto the shared bootstrap). The allowlist is now EMPTY — only venv_bootstrap
    # reads the env var.
    PENDING_RETIRED_BY_1P7PM_1P7PN: set[str] = set()

    def test_tool_venv_env_read_in_exactly_one_place(self):
        offenders = []
        for py in sorted(SCRIPTS_ROOT.glob("*.py")):
            if py.name in self.ALLOWED or py.name in self.PENDING_RETIRED_BY_1P7PM_1P7PN:
                continue
            if "WAVEFOUNDRY_TOOL_VENV" in py.read_text(encoding="utf-8"):
                offenders.append(py.name)
        self.assertEqual(
            offenders,
            [],
            f"WAVEFOUNDRY_TOOL_VENV must be read only in venv_bootstrap; offenders: {offenders}",
        )

    def test_pending_retirement_allowlist_is_empty(self):
        """Goal B guard: the temporary 1p7pm/1p7pn allowlist must stay empty — no file other than
        venv_bootstrap may re-derive the tool-venv path. A non-empty set is a regression."""
        self.assertEqual(self.PENDING_RETIRED_BY_1P7PM_1P7PN, set())

    @staticmethod
    def _docstring_constant_ids(tree: ast.AST) -> set[int]:
        """ids of the Constant nodes that are module/class/function docstrings (to exclude from a scan)."""
        ids: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = getattr(node, "body", None)
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    ids.add(id(body[0].value))
        return ids

    def test_no_venv_python_layout_branch_outside_bootstrap(self):
        """1p7pl Req-7 (strengthened): the ``Scripts\\python.exe``-vs-``bin/python`` venv-PYTHON layout
        decision must live ONLY in venv_bootstrap. A non-allowlisted top-level script with a
        ``python.exe`` venv-binary literal in CODE (not a docstring) is re-deriving the venv layout —
        a goal-B violation. ``python.exe`` is the precise marker (the codebase-map ``"Scripts"`` labels
        and setup_index's ``uv.exe`` uv-binary branch are NOT venv-python layout, so they don't trip)."""
        offenders = []
        for py in sorted(SCRIPTS_ROOT.glob("*.py")):
            if py.name in self.ALLOWED:
                continue
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            doc_ids = self._docstring_constant_ids(tree)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                        and id(node) not in doc_ids and "python.exe" in node.value:
                    offenders.append(py.name)
                    break
        self.assertEqual(
            offenders,
            [],
            f"venv-python layout (Scripts/python.exe) must live only in venv_bootstrap; offenders: {offenders}",
        )


class ReexecAdoptionScanTests(unittest.TestCase):
    """1p7pl AC-4 / Risks: every direct-launch entry script must self-bootstrap into the tool venv by
    calling ``venv_bootstrap.reexec_into_tool_venv()`` (so a bare ``python <entry>.py`` runs on the venv
    interpreter). A standing scan catches an entry that forgets the first-line import (the footgun the
    1p7pl plan called out)."""

    ENTRY_SCRIPTS = (
        "server.py",
        "setup_wavefoundry.py",
        "setup_index.py",
        "indexer.py",
        "dashboard_server.py",
        "docs_lint.py",
        "docs_gardener.py",
        "wave_gate.py",
        "lifecycle_id.py",
        "run_tests.py",
    )

    def test_every_direct_launch_entry_reexecs_into_tool_venv(self):
        missing = []
        for name in self.ENTRY_SCRIPTS:
            path = SCRIPTS_ROOT / name
            self.assertTrue(path.is_file(), f"entry script {name} not found")
            src = path.read_text(encoding="utf-8")
            if "reexec_into_tool_venv()" not in src:
                missing.append(name)
        self.assertEqual(
            missing,
            [],
            f"these direct-launch entries do not self-bootstrap into the tool venv: {missing}",
        )


class EnsurePythonResolvesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.localbin = Path(self.tmp.name) / ".local" / "bin"
        # Never touch the real ~/.local/bin or shell rc during tests.
        p1 = patch.object(vb, "_user_local_bin", return_value=self.localbin)
        p1.start()
        self.addCleanup(p1.stop)
        p2 = patch.object(vb, "_ensure_dir_on_path", return_value=False)
        p2.start()
        self.addCleanup(p2.stop)
        # Wave 1p7pm: these tests exercise the REAL heal — make sure the global opt-out env var is
        # NOT set so they don't all short-circuit to "skipped".
        p3 = patch.dict(os.environ, {}, clear=False)
        p3.start()
        self.addCleanup(p3.stop)
        os.environ.pop("WAVEFOUNDRY_SKIP_PYTHON_HEAL", None)

    @staticmethod
    def _which(map_):
        return lambda name: map_.get(name)

    def test_env_opt_out_makes_heal_a_complete_noop(self):
        """WAVEFOUNDRY_SKIP_PYTHON_HEAL=1 returns "skipped" without touching the filesystem (the
        subprocess-safe path used by render/setup/upgrade tests so the suite never mutates the box)."""
        with patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}), patch.object(
            vb.shutil, "which"
        ) as which_mock:
            self.assertEqual(vb.ensure_python_resolves(strict=True), "skipped")
        which_mock.assert_not_called()  # short-circuits before any resolution work
        self.assertFalse((self.localbin / "python").exists())

    def test_noop_when_python_already_ge_311(self):
        with patch.object(vb.shutil, "which", side_effect=self._which({"python": "/usr/bin/python"})), patch.object(
            vb, "_interpreter_version", return_value=(3, 11)
        ):
            self.assertEqual(vb.ensure_python_resolves(), "ok")
        self.assertFalse((self.localbin / "python").exists())

    def test_warns_and_does_not_clobber_python2(self):
        with patch.object(vb.shutil, "which", side_effect=self._which({"python": "/usr/bin/python"})), patch.object(
            vb, "_interpreter_version", return_value=(2, 7)
        ):
            self.assertEqual(vb.ensure_python_resolves(), "warn_existing_unusable")
        self.assertFalse((self.localbin / "python").exists())  # never clobbered

    def test_creates_symlink_when_absent_posix(self):
        py3 = Path(self.tmp.name) / "python3"
        py3.write_text("")
        with patch.object(vb.os, "name", "posix"), patch.object(
            vb.shutil, "which", side_effect=self._which({"python3": str(py3)})
        ), patch.object(vb, "_interpreter_version", return_value=(3, 12)):
            self.assertEqual(vb.ensure_python_resolves(), "created")
        link = self.localbin / "python"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), py3.resolve())

    def test_reheals_dangling_symlink(self):
        self.localbin.mkdir(parents=True)
        (self.localbin / "python").symlink_to(Path(self.tmp.name) / "old_python3")  # dangling
        py3 = Path(self.tmp.name) / "python3"
        py3.write_text("")
        with patch.object(vb.os, "name", "posix"), patch.object(
            vb.shutil, "which", side_effect=self._which({"python3": str(py3)})
        ), patch.object(vb, "_interpreter_version", return_value=(3, 12)):
            self.assertEqual(vb.ensure_python_resolves(), "created")
        self.assertEqual((self.localbin / "python").resolve(), py3.resolve())

    def test_windows_absent_python_warns_then_strict_raises(self):
        with patch.object(vb.os, "name", "nt"), patch.object(vb.shutil, "which", return_value=None):
            self.assertEqual(vb.ensure_python_resolves(strict=False), "warn_no_python")
            with self.assertRaises(SystemExit):
                vb.ensure_python_resolves(strict=True)

    def test_strict_raises_when_no_python_posix(self):
        with patch.object(vb.os, "name", "posix"), patch.object(vb.shutil, "which", return_value=None):
            with self.assertRaises(SystemExit):
                vb.ensure_python_resolves(strict=True)


class GuiFallbackStanzaTests(unittest.TestCase):
    """Wave 1p7pm AC-4/AC-5: the GUI-host fallback stanza uses the ABSOLUTE tool-venv Python + the
    ABSOLUTE server.py path — no relative `python`, no PATH dependency (GUI hosts don't inherit the
    shell PATH where setup symlinked `python`)."""

    def test_stanza_uses_absolute_venv_python_and_server_path(self):
        fake_venv_python = Path("/fake/tool-venv/bin/python")
        with patch.object(vb, "tool_venv_python", return_value=fake_venv_python):
            stanza = vb.gui_fallback_mcp_stanza("/some/repo")
        # Command is the ABSOLUTE venv python — never the relative `python` token.
        self.assertEqual(stanza["command"], str(fake_venv_python))
        self.assertNotEqual(stanza["command"], "python")
        self.assertTrue(Path(stanza["command"]).is_absolute())
        # args: absolute server.py + --root <abs repo>.
        self.assertEqual(len(stanza["args"]), 3)
        server_arg = stanza["args"][0]
        self.assertTrue(server_arg.endswith(".wavefoundry/framework/scripts/server.py"))
        self.assertTrue(Path(server_arg).is_absolute())
        self.assertEqual(stanza["args"][1], "--root")
        self.assertTrue(Path(stanza["args"][2]).is_absolute())
        # No relative `python` token anywhere — the whole point of the no-PATH fallback.
        import json
        self.assertNotIn('"python"', json.dumps(stanza))


if __name__ == "__main__":
    unittest.main()

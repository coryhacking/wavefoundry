from __future__ import annotations

import ast
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
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


class ActivateTests(unittest.TestCase):
    """Wave 1p802: ``activate_tool_venv`` activates the venv IN-PROCESS via ``site.addsitedir`` — no
    re-exec, no child, no ``os.execv``/``subprocess`` relay. A SINGLE host-spawned process on every OS."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.venv = Path(self.tmp.name) / "venv"
        (self.venv / "bin").mkdir(parents=True)
        self.py = self.venv / "bin" / "python"
        self.py.write_text("")  # make it exist
        self.absent = Path(self.tmp.name) / "absent" / "bin" / "python"
        self._orig_path = list(sys.path)
        self.addCleanup(lambda: setattr(sys, "path", self._orig_path))

    def _make_site_packages(self, *, pyvenv_version: str | None) -> Path:
        # Build a fake venv whose site-packages matches the RUNNING interpreter's lib layout.
        sp = vb._venv_site_packages(self.venv)
        sp.mkdir(parents=True, exist_ok=True)
        if pyvenv_version is not None:
            (self.venv / "pyvenv.cfg").write_text(f"version = {pyvenv_version}\n", encoding="utf-8")
        return sp

    def test_activate_adds_site_packages_to_sys_path(self):
        # AC-1: site-packages is prepended to sys.path.
        running = f"{sys.version_info[0]}.{sys.version_info[1]}.0"
        sp = self._make_site_packages(pyvenv_version=running)
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "tool_venv_base", return_value=self.venv
        ), patch.object(vb, "_running_inside_venv", return_value=False):
            vb.activate_tool_venv()
        self.assertIn(str(sp), sys.path)
        self.assertEqual(sys.path.index(str(sp)), 0, "venv site-packages must be prepended (win over system)")

    def test_activate_makes_a_real_module_importable_and_processes_a_pth(self):
        # AC-1 (strengthened): a REAL importable module in site-packages is importable after activation
        # (proves site.addsitedir worked), and a `.pth` in site-packages is PROCESSED (its extra dir
        # lands on sys.path — that is the thing addsitedir does over a bare sys.path.insert).
        running = f"{sys.version_info[0]}.{sys.version_info[1]}.0"
        sp = self._make_site_packages(pyvenv_version=running)
        # A real single-file module to import.
        unique = f"wf_activate_probe_{os.getpid()}"
        (sp / f"{unique}.py").write_text("MARKER = 7\n", encoding="utf-8")
        # A .pth that adds an extra directory — addsitedir processes .pth lines.
        extra = self.venv / "pth-extra"
        extra.mkdir()
        (sp / "wf_extra.pth").write_text(str(extra) + "\n", encoding="utf-8")
        self.addCleanup(lambda: sys.modules.pop(unique, None))
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "tool_venv_base", return_value=self.venv
        ), patch.object(vb, "_running_inside_venv", return_value=False):
            vb.activate_tool_venv()
        mod = __import__(unique)  # would ImportError if addsitedir didn't make sp live
        self.assertEqual(mod.MARKER, 7)
        self.assertIn(str(extra), sys.path, "the .pth's extra dir must be processed onto sys.path")

    def test_missing_site_packages_dir_exits(self):
        # The site-packages dir absent (pyvenv.cfg present, version matches) → stderr + SystemExit(2).
        running = f"{sys.version_info[0]}.{sys.version_info[1]}.0"
        (self.venv / "pyvenv.cfg").write_text(f"version = {running}\n", encoding="utf-8")
        # Deliberately do NOT create the site-packages dir.
        sp = vb._venv_site_packages(self.venv)
        self.assertFalse(sp.is_dir())
        before = list(sys.path)
        buf = io.StringIO()
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "tool_venv_base", return_value=self.venv
        ), patch.object(vb, "_running_inside_venv", return_value=False), redirect_stderr(buf):
            with self.assertRaises(SystemExit) as ctx:
                vb.activate_tool_venv()
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("site-packages", buf.getvalue())
        self.assertIn("wf setup", buf.getvalue())
        self.assertEqual(sys.path, before)

    def test_fail_open_when_pyvenv_cfg_absent(self):
        # Conscious edge: no pyvenv.cfg ⇒ _venv_python_version returns None ⇒ activation PROCEEDS
        # (don't block a valid venv over an unreadable version line). No SystemExit.
        sp = self._make_site_packages(pyvenv_version=None)  # site-packages exists, NO pyvenv.cfg
        self.assertFalse((self.venv / "pyvenv.cfg").exists())
        self.assertIsNone(vb._venv_python_version(self.venv))
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "tool_venv_base", return_value=self.venv
        ), patch.object(vb, "_running_inside_venv", return_value=False):
            vb.activate_tool_venv()  # must not raise / exit
        self.assertIn(str(sp), sys.path)

    def test_fail_open_when_pyvenv_cfg_malformed(self):
        # A malformed version line ⇒ None ⇒ activation proceeds (fail-open).
        sp = self._make_site_packages(pyvenv_version=None)
        (self.venv / "pyvenv.cfg").write_text("version = not.a.version\nother = x\n", encoding="utf-8")
        self.assertIsNone(vb._venv_python_version(self.venv))
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "tool_venv_base", return_value=self.venv
        ), patch.object(vb, "_running_inside_venv", return_value=False):
            vb.activate_tool_venv()
        self.assertIn(str(sp), sys.path)

    def test_noop_when_venv_absent(self):
        # Tier 1 (fresh bootstrap): no venv yet ⇒ no activation, never block setup creating it.
        before = list(sys.path)
        with patch.object(vb, "tool_venv_python", return_value=self.absent):
            vb.activate_tool_venv()
        self.assertEqual(sys.path, before)

    def test_noop_when_already_inside_venv(self):
        before = list(sys.path)
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "tool_venv_base", return_value=self.venv
        ), patch.object(vb, "_running_inside_venv", return_value=True):
            vb.activate_tool_venv()
        self.assertEqual(sys.path, before)

    def test_version_guard_mismatch_exits_and_does_not_activate(self):
        # AC-2: a venv built for a different Python (major, minor) → clear stderr + SystemExit(2),
        # and the (ABI-incompatible) site-packages is NOT added to sys.path.
        other = f"{sys.version_info[0]}.{sys.version_info[1] + 1}.0"  # one minor ahead
        sp = self._make_site_packages(pyvenv_version=other)
        before = list(sys.path)
        buf = io.StringIO()
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "tool_venv_base", return_value=self.venv
        ), patch.object(vb, "_running_inside_venv", return_value=False), \
             redirect_stderr(buf):
            with self.assertRaises(SystemExit) as ctx:
                vb.activate_tool_venv()
        self.assertEqual(ctx.exception.code, 2)
        msg = buf.getvalue()
        self.assertIn("wf setup", msg)
        self.assertIn("built for Python", msg)
        self.assertNotIn(str(sp), sys.path)  # no activation
        self.assertEqual(sys.path, before)

    def test_version_guard_mismatch_can_noop_for_setup_repair(self):
        # P1 repair path: setup is the command users run to rebuild a stale venv, so it must be able
        # to bypass the mismatch guard WITHOUT activating incompatible packages.
        other = f"{sys.version_info[0]}.{sys.version_info[1] + 1}.0"
        sp = self._make_site_packages(pyvenv_version=other)
        before = list(sys.path)
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "tool_venv_base", return_value=self.venv
        ), patch.object(vb, "_running_inside_venv", return_value=False):
            vb.activate_tool_venv(allow_version_mismatch=True)
        self.assertNotIn(str(sp), sys.path)
        self.assertEqual(sys.path, before)

    def test_version_guard_match_activates(self):
        running = f"{sys.version_info[0]}.{sys.version_info[1]}.7"  # same major.minor, diff patch
        sp = self._make_site_packages(pyvenv_version=running)
        with patch.object(vb, "tool_venv_python", return_value=self.py), patch.object(
            vb, "tool_venv_base", return_value=self.venv
        ), patch.object(vb, "_running_inside_venv", return_value=False):
            vb.activate_tool_venv()
        self.assertIn(str(sp), sys.path)

    def test_no_reexec_or_execv_in_module(self):
        # AC-3: no re-exec mechanism remains in the live code of venv_bootstrap.
        src = VENV_BOOTSTRAP_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src)
        offenders = []
        for node in ast.walk(tree):
            # os.execv / subprocess.run([...sys.argv...]) re-exec calls in live code (not docstrings).
            if isinstance(node, ast.Attribute) and node.attr == "execv":
                offenders.append(f"os.execv at line {node.lineno}")
            if isinstance(node, ast.Name) and node.id == "reexec_into_tool_venv":
                offenders.append(f"reexec_into_tool_venv ref at line {node.lineno}")
        self.assertEqual(offenders, [], f"re-exec mechanism must be gone: {offenders}")

    def test_emits_no_stdout(self):
        # A stdout byte before the MCP JSON-RPC handshake corrupts it — neither the absent-venv early
        # return NOR the activate path may write to stdout.
        # (1) absent-venv early return.
        buf = io.StringIO()
        with redirect_stdout(buf), patch.object(vb, "tool_venv_python", return_value=self.absent):
            vb.activate_tool_venv()
        self.assertEqual(buf.getvalue(), "")
        # (2) the activate path (venv present, version matches).
        running = f"{sys.version_info[0]}.{sys.version_info[1]}.0"
        self._make_site_packages(pyvenv_version=running)
        buf2 = io.StringIO()
        with redirect_stdout(buf2), patch.object(vb, "tool_venv_python", return_value=self.py), \
             patch.object(vb, "tool_venv_base", return_value=self.venv), \
             patch.object(vb, "_running_inside_venv", return_value=False):
            vb.activate_tool_venv()
        self.assertEqual(buf2.getvalue(), "")


def _system_base_interpreter() -> "str | None":
    """The base (system) interpreter the REAL tool venv was built from.

    Reads ``pyvenv.cfg``'s ``executable =`` (the base python the venv was created from — by
    construction NOT a venv python: running it gives the system ``sys.prefix``, not the venv's, so it
    exercises activation). Confirms it exists and that running it reports a ``sys.prefix`` distinct
    from the venv base (a binary-path comparison is unreliable — on Homebrew the venv python symlinks
    to the same file). Returns None when it can't be resolved distinctly so the de-risk test self-skips
    on a box without a separate system python."""
    import subprocess

    venv_base = vb.tool_venv_base()
    if not vb.tool_venv_python().exists():
        return None
    cfg = venv_base / "pyvenv.cfg"
    try:
        text = cfg.read_text(encoding="utf-8")
    except OSError:
        return None
    base = None
    for raw in text.splitlines():
        key, sep, value = raw.partition("=")
        if sep and key.strip().lower() == "executable":
            base = value.strip()
            break
    if not base or not Path(base).exists():
        return None
    try:
        proc = subprocess.run([base, "-c", "import sys; print(sys.prefix)"],
                              capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    try:
        base_prefix = Path(proc.stdout.strip()).resolve()
        if base_prefix == venv_base.resolve():
            return None  # running it IS the venv (not distinct) — can't exercise activation
    except OSError:
        return None
    return base


class ActivateInProcessDeRiskTests(unittest.TestCase):
    """Wave 1p802 AC-4/AC-5 de-risk: a heavy venv-only dep imports IN-PROCESS under the SYSTEM
    interpreter after ``activate_tool_venv`` (proves ``site.addsitedir`` makes the compiled deps
    importable without a re-exec). Self-skips when a distinct system interpreter can't be found."""

    def test_heavy_dep_imports_under_system_interpreter(self):
        import subprocess

        base = _system_base_interpreter()
        if base is None:
            self.skipTest("no distinct system base interpreter resolvable from the venv pyvenv.cfg")
        # Pick a venv-only package present in this tool venv.
        sp = vb._venv_site_packages(vb.tool_venv_base())
        candidates = ["mcp", "fastembed", "onnxruntime", "lancedb", "numpy"]
        pkg = next((c for c in candidates if (sp / c).exists() or (sp / f"{c}.py").exists()), None)
        if pkg is None:
            self.skipTest("no known venv-only package found in the tool venv site-packages")
        code = (
            "import sys; sys.path.insert(0, %r); "
            "import venv_bootstrap; venv_bootstrap.activate_tool_venv(); "
            "import %s; print('OK')" % (str(SCRIPTS_ROOT), pkg)
        )
        result = subprocess.run(
            [base, "-c", code], capture_output=True, text=True, timeout=120, check=False,
        )
        self.assertEqual(
            result.returncode, 0,
            f"system-interpreter in-process import of {pkg} failed:\nstdout={result.stdout}\nstderr={result.stderr}",
        )
        self.assertIn("OK", result.stdout)


class StdlibOnlyTests(unittest.TestCase):
    def test_imports_are_stdlib_only(self):
        # `site` is imported inside activate_tool_venv (lazy) — stdlib, allowed.
        allowed = {"__future__", "os", "shutil", "subprocess", "sys", "pathlib", "site"}
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
    # blocks setup from creating the venv. (Full end-to-end is 1p802 AC-5 Windows smoke.)
    def test_noop_then_venv_path_creatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv_base = Path(tmp) / "venv"  # does not exist yet
            with patch.dict(os.environ, {"WAVEFOUNDRY_TOOL_VENV": str(venv_base)}):
                self.assertFalse(vb.tool_venv_python().exists())
                before = list(sys.path)
                vb.activate_tool_venv()  # must not raise, must not activate
                self.assertEqual(sys.path, before)
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


class ActivateAdoptionScanTests(unittest.TestCase):
    """1p7pl AC-4 / 1p802 AC-3: every direct-launch entry script must self-bootstrap into the tool venv
    by calling ``venv_bootstrap.activate_tool_venv()`` (in-process activation — no re-exec). A standing
    scan catches an entry that forgets the first-line call."""

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
        "wf_cli.py",
    )

    def test_every_direct_launch_entry_activates_tool_venv(self):
        missing = []
        for name in self.ENTRY_SCRIPTS:
            path = SCRIPTS_ROOT / name
            self.assertTrue(path.is_file(), f"entry script {name} not found")
            src = path.read_text(encoding="utf-8")
            if "activate_tool_venv(" not in src:
                missing.append(name)
        self.assertEqual(
            missing,
            [],
            f"these direct-launch entries do not self-activate the tool venv: {missing}",
        )

    def test_no_reexec_into_tool_venv_call_in_any_entry(self):
        # 1p802 AC-3: the re-exec is gone — no entry script CALLS reexec_into_tool_venv().
        offenders = []
        for name in self.ENTRY_SCRIPTS:
            src = (SCRIPTS_ROOT / name).read_text(encoding="utf-8")
            if "reexec_into_tool_venv()" in src:
                offenders.append(name)
        self.assertEqual(offenders, [], f"these entries still call the removed re-exec: {offenders}")


class EnsurePythonResolvesTests(unittest.TestCase):
    """Wave 1p88t: ``ensure_python_resolves`` is DETECT + GUIDE only — it verifies `python3` resolves
    to Python 3.11+ and fails closed (strict) / warns (non-strict) with platform-aware guidance
    otherwise. It NEVER creates a shim/symlink, copies into a Python install, or edits PATH (operator
    decision; amends ADR 1p7pb). Every test asserts no filesystem mutation under a temp HOME."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # Point HOME at a temp dir so any accidental ~/.local/bin write would be caught here and never
        # touch the real home.
        self.home = Path(self.tmp.name)
        ph = patch.object(vb.Path, "home", return_value=self.home)
        ph.start()
        self.addCleanup(ph.stop)
        pe = patch.dict(os.environ, {}, clear=False)
        pe.start()
        self.addCleanup(pe.stop)
        os.environ.pop("WAVEFOUNDRY_SKIP_PYTHON_HEAL", None)

    @staticmethod
    def _which(map_):
        return lambda name: map_.get(name)

    def _assert_nothing_created(self):
        # Detect+guide must never write a shim/symlink/copy anywhere under (temp) home.
        localbin = self.home / ".local" / "bin"
        self.assertFalse((localbin / "python3").exists())
        self.assertFalse((localbin / "python3.cmd").exists())

    def test_env_opt_out_is_a_complete_noop(self):
        with patch.dict(os.environ, {"WAVEFOUNDRY_SKIP_PYTHON_HEAL": "1"}), patch.object(
            vb.shutil, "which"
        ) as which_mock:
            self.assertEqual(vb.ensure_python_resolves(strict=True), "skipped")
        which_mock.assert_not_called()  # short-circuits before any resolution work
        self._assert_nothing_created()

    def test_ok_when_python3_already_ge_311(self):
        with patch.object(vb.shutil, "which", side_effect=self._which({"python3": "/usr/bin/python3"})), patch.object(
            vb, "_interpreter_version", return_value=(3, 11)
        ):
            self.assertEqual(vb.ensure_python_resolves(strict=True), "ok")
        self._assert_nothing_created()

    def test_python3_below_311_warns_then_strict_raises(self):
        with patch.object(vb.shutil, "which", side_effect=self._which({"python3": "/usr/bin/python3"})), patch.object(
            vb, "_interpreter_version", return_value=(2, 7)
        ):
            self.assertEqual(vb.ensure_python_resolves(strict=False), "warn_existing_unusable")
            with self.assertRaises(SystemExit):
                vb.ensure_python_resolves(strict=True)
        self._assert_nothing_created()  # never clobbers the unusable python3 either

    def test_python3_absent_with_python_present_does_NOT_create_anything_posix(self):
        # Only `python` exists (no `python3`). Detect+guide does NOT symlink/create a python3 — it
        # fails closed (strict) / warns (non-strict) and tells the operator to make python3 resolve.
        with patch.object(vb.os, "name", "posix"), patch.object(
            vb.shutil, "which", side_effect=self._which({"python": "/usr/bin/python"})
        ):
            self.assertEqual(vb.ensure_python_resolves(strict=False), "warn_unresolved")
            with self.assertRaises(SystemExit):
                vb.ensure_python_resolves(strict=True)
        self._assert_nothing_created()

    def test_python3_absent_with_python_present_does_NOT_create_anything_windows(self):
        with patch.object(vb.os, "name", "nt"), patch.object(
            vb.shutil, "which", side_effect=self._which({"python": r"C:\Python312\python.exe"})
        ):
            self.assertEqual(vb.ensure_python_resolves(strict=False), "warn_unresolved")
            with self.assertRaises(SystemExit):
                vb.ensure_python_resolves(strict=True)
        self._assert_nothing_created()

    def test_no_python_at_all_warns_then_strict_raises(self):
        with patch.object(vb.shutil, "which", return_value=None):
            self.assertEqual(vb.ensure_python_resolves(strict=False), "warn_unresolved")
            with self.assertRaises(SystemExit):
                vb.ensure_python_resolves(strict=True)
        self._assert_nothing_created()

    def test_guidance_is_platform_aware_and_states_no_mutation(self):
        import io
        from contextlib import redirect_stderr

        for osname, needle in (("posix", "symlink"), ("nt", "Scoop")):
            buf = io.StringIO()
            with patch.object(vb.os, "name", osname), patch.object(
                vb.shutil, "which", return_value=None
            ), redirect_stderr(buf):
                vb.ensure_python_resolves(strict=False)
            text = buf.getvalue()
            self.assertIn(needle, text)
            self.assertIn("does not modify your Python", text)


class GuiFallbackStanzaTests(unittest.TestCase):
    """Wave 1p7pm AC-4/AC-5: the GUI-host fallback stanza uses the ABSOLUTE tool-venv Python + the
    ABSOLUTE server.py path — no relative `python3`, no PATH dependency (GUI hosts don't inherit the
    shell PATH where setup ensured `python3`)."""

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

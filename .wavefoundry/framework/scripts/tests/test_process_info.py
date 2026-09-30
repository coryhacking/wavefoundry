"""process_info: psutil-backed process information (ADR 1z9df, wave 1zc7n)."""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import process_info  # noqa: E402
from server_tools_support import fake_psutil  # noqa: E402


def _absent_pid() -> int:
    pid = 999_999
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return pid
        except OSError:
            pass
        pid += 1


class _Reset(unittest.TestCase):
    def setUp(self):
        saved = process_info._PSUTIL
        self.addCleanup(setattr, process_info, "_PSUTIL", saved)


class ContractOnHostTests(_Reset):
    def test_pid_state_across_process_states(self):
        self.assertEqual(process_info.pid_state(os.getpid()), process_info.ALIVE)
        self.assertEqual(process_info.pid_state(0), process_info.DEAD)
        self.assertEqual(process_info.pid_state(-3), process_info.DEAD)
        self.assertEqual(process_info.pid_state(_absent_pid()), process_info.DEAD)
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        child.wait()
        self.assertEqual(process_info.pid_state(child.pid), process_info.DEAD)

    @unittest.skipIf(os.name == "nt", "POSIX zombie")
    def test_zombie_child_is_zombie_and_its_state_is_separate(self):
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        self.addCleanup(child.wait)
        deadline = time.time() + 10
        while process_info.is_zombie(child.pid) is not True and time.time() < deadline:
            time.sleep(0.05)
        self.assertIs(process_info.is_zombie(child.pid), True)
        self.assertEqual(process_info.pid_state(child.pid), process_info.ALIVE)
        self.assertIs(process_info.is_zombie(os.getpid()), False)
        self.assertIs(process_info.is_zombie(_absent_pid()), False)

    def test_cmdline_cwd_and_create_time_of_a_live_child(self):
        child = subprocess.Popen(
            [sys.executable, "-c", "import time; print('ready', flush=True); time.sleep(30)",
             "--root", "/tmp/a b"],
            cwd=str(SCRIPTS), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True,
        )
        self.addCleanup(lambda: (child.kill(), child.wait()))
        # macOS framework Python re-execs itself at startup; read the command
        # line once the interpreter is running, as a real caller would.
        self.assertEqual(child.stdout.readline().strip(), "ready")
        line = process_info.cmdline(child.pid)
        if os.name != "nt":
            ps = subprocess.run(["ps", "-o", "args=", "-p", str(child.pid)],
                                capture_output=True, text=True, timeout=10).stdout.strip()
            self.assertEqual(line, ps)
        # Review DEL-CR-WINDOWS-QUOTING: rendering is platform-specific; Windows
        # quotes the spaced argument (subprocess.list2cmdline).
        tail = ["--root", "/tmp/a b"]
        rendered = subprocess.list2cmdline(tail) if os.name == "nt" else " ".join(tail)
        self.assertIn(rendered, line)
        self.assertEqual(process_info.cwd(child.pid).resolve(), SCRIPTS.resolve())
        created = process_info.create_time(child.pid)
        self.assertLess(abs(created - time.time()), 60)
        for fn in (process_info.cmdline, process_info.cwd, process_info.create_time):
            self.assertIsNone(fn(0))
            self.assertIsNone(fn(_absent_pid()))

    def test_available_reports_the_loaded_version(self):
        ok, detail = process_info.available()
        self.assertTrue(ok)
        self.assertEqual(detail, __import__("psutil").__version__)


class WindowsBranchTests(_Reset):
    def test_windows_rendering_and_access_denied_after_existence(self):
        fake = fake_psutil(exists=True, cmdline=["C:\\Program Files\\py.exe", "-c", "a b"])
        with patch.object(process_info, "_load", return_value=fake), \
                patch.object(process_info.os, "name", "nt"):
            self.assertEqual(process_info.cmdline(4321), subprocess.list2cmdline(fake.Process(1).cmdline()))
            self.assertIs(process_info.is_zombie(4321), False)
        denied = fake_psutil(exists=True, process_error="AccessDenied")
        with patch.object(process_info, "_load", return_value=denied), \
                patch.object(process_info.os, "name", "nt"):
            self.assertEqual(process_info.pid_state(4321), process_info.ALIVE)
            self.assertIsNone(process_info.cmdline(4321))
            self.assertIsNone(process_info.cwd(4321))


class BrokenOrMissingPsutilTests(_Reset):
    def _fresh(self):
        process_info._PSUTIL = None

    def test_any_import_failure_is_unavailable_and_names_wf_setup(self):
        self._fresh()
        with patch.object(process_info.importlib, "import_module", side_effect=OSError("blocked dll")):
            with self.assertRaises(process_info.ProcessInfoUnavailable) as raised:
                process_info.pid_state(os.getpid())
            self.assertIn("wf setup", str(raised.exception))
            self.assertEqual(process_info.available()[0], False)

    def test_below_the_floor_is_unavailable(self):
        self._fresh()
        with patch.object(process_info.importlib, "import_module", return_value=fake_psutil(version="5.9.8")):
            with self.assertRaises(process_info.ProcessInfoUnavailable) as raised:
                process_info.pid_state(os.getpid())
            self.assertIn("older than the required", str(raised.exception))

    def test_a_later_successful_import_is_picked_up(self):
        self._fresh()
        with patch.object(process_info.importlib, "import_module", side_effect=ImportError("missing")):
            self.assertFalse(process_info.available()[0])
        with patch.object(process_info.importlib, "import_module", return_value=fake_psutil()) as imp, \
                patch.object(process_info.importlib, "invalidate_caches") as invalidate:
            self.assertTrue(process_info.available()[0])
            invalidate.assert_called()
            imp.assert_called_with("psutil")

    def test_raising_calls_never_escape(self):
        for exc in (OSError("boom"), SystemError("bad build"), RuntimeError("x")):
            broken = fake_psutil(exists=True, process_error=exc)
            broken.pid_exists = lambda pid, _e=exc: (_ for _ in ()).throw(_e)
            with self.subTest(exc=type(exc).__name__), patch.object(process_info, "_load", return_value=broken):
                self.assertEqual(process_info.pid_state(4321), process_info.UNKNOWN)
                self.assertIsNone(process_info.is_zombie(4321))
                self.assertIsNone(process_info.cmdline(4321))
                self.assertIsNone(process_info.cwd(4321))
                self.assertIsNone(process_info.create_time(4321))


# Files that run before dependencies are installed or inside an older upgrade
# runner (ADR 1z9df). None may import psutil anywhere or process_info at module
# level (a function-local process_info import after ensure_deps is a review rule).
_STDLIB_ONLY = (
    "venv_bootstrap.py", "setup_requirements.py", "setup_readiness.py", "setup_index.py",
    "setup_wavefoundry.py", "setup_reconciliation.py", "upgrade_lib.py", "dashboard_lib.py",
    "sqlite_storage_migration.py",
)


class StdlibOnlyGuardTests(unittest.TestCase):
    def _files(self):
        import upgrade_protocol

        names = set(_STDLIB_ONLY)
        names.update(upgrade_protocol.MANDATORY_FEATURE_MODULES)
        return sorted(names)

    def test_no_psutil_anywhere_and_no_module_level_process_info(self):
        from framework_files import source_path

        files = self._files()
        self.assertGreater(len(files), len(_STDLIB_ONLY))
        for name in files:
            path = source_path(name)
            self.assertTrue(path.exists(), name)
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                for mod in names:
                    with self.subTest(file=name, module=mod, line=node.lineno):
                        self.assertNotEqual(mod.split(".")[0], "psutil")
            for node in tree.body:
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    mods = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                    self.assertNotIn("process_info", mods, f"{name}: module-level import process_info")

    def test_the_guard_detects_a_function_local_psutil_import(self):
        tree = ast.parse("def f():\n    import psutil\n")
        found = [n for n in ast.walk(tree) if isinstance(n, ast.Import) and n.names[0].name == "psutil"]
        self.assertTrue(found)


if __name__ == "__main__":
    unittest.main()

"""Tests for the shared subprocess-isolation helper (wave 1p8gu / 1p8gv).

These exercise the cross-OS guarantees by faking ``subprocess.run`` / ``subprocess.Popen`` and
monkeypatching ``os.name`` — the real Windows console behavior cannot be reproduced on POSIX, so the
guarantees are verified at the kwargs boundary (what the helper passes to subprocess).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import subprocess_util


class NoWindowCreationflagsTests(unittest.TestCase):
    def test_zero_on_posix(self):
        with patch.object(subprocess_util.os, "name", "posix"):
            self.assertEqual(subprocess_util.no_window_creationflags(), 0)
            self.assertEqual(subprocess_util.detached_background_creationflags(), 0)

    def test_no_window_flag_on_windows(self):
        with patch.object(subprocess_util.os, "name", "nt"), \
             patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True):
            self.assertEqual(subprocess_util.no_window_creationflags(), 0x08000000)

    def test_detached_background_flags_on_windows(self):
        with patch.object(subprocess_util.os, "name", "nt"), \
             patch.object(subprocess, "DETACHED_PROCESS", 0x08, create=True), \
             patch.object(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, create=True), \
             patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True):
            flags = subprocess_util.detached_background_creationflags()
            self.assertEqual(flags, 0x08 | 0x200 | 0x08000000)


class IsolatedRunTests(unittest.TestCase):
    def _capture_run(self):
        captured: dict[str, object] = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        return captured, fake_run

    def test_defaults_stdin_to_devnull(self):
        captured, fake = self._capture_run()
        with patch.object(subprocess, "run", side_effect=fake):
            subprocess_util.isolated_run(["x"])
        self.assertIs(captured["stdin"], subprocess.DEVNULL)

    def test_input_kwarg_leaves_stdin_alone(self):
        # input= uses a PIPE (not the inherited stream); the helper must not also set stdin=DEVNULL,
        # which would conflict with input=.
        captured, fake = self._capture_run()
        with patch.object(subprocess, "run", side_effect=fake):
            subprocess_util.isolated_run(["x"], input="payload", text=True)
        self.assertNotIn("stdin", captured)
        self.assertEqual(captured["input"], "payload")

    def test_caller_stdin_wins(self):
        captured, fake = self._capture_run()
        with patch.object(subprocess, "run", side_effect=fake):
            subprocess_util.isolated_run(["x"], stdin=subprocess.PIPE)
        self.assertIs(captured["stdin"], subprocess.PIPE)

    def test_no_window_flag_applied_on_windows(self):
        captured, fake = self._capture_run()
        with patch.object(subprocess_util.os, "name", "nt"), \
             patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch.object(subprocess, "run", side_effect=fake):
            subprocess_util.isolated_run(["x"])
        self.assertEqual(captured["creationflags"], 0x08000000)

    def test_no_creationflags_on_posix(self):
        captured, fake = self._capture_run()
        with patch.object(subprocess_util.os, "name", "posix"), \
             patch.object(subprocess, "run", side_effect=fake):
            subprocess_util.isolated_run(["x"])
        self.assertNotIn("creationflags", captured)

    def test_existing_creationflags_preserved_and_ored(self):
        captured, fake = self._capture_run()
        with patch.object(subprocess_util.os, "name", "nt"), \
             patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch.object(subprocess, "run", side_effect=fake):
            subprocess_util.isolated_run(["x"], creationflags=0x01)
        self.assertEqual(captured["creationflags"], 0x01 | 0x08000000)

    def test_utf8_capture_encoding_applied_for_text_spawn(self):
        # Wave 1p8gv: a captured text spawn must decode as UTF-8 with errors=replace so cp1252
        # consoles do not mangle child output.
        captured, fake = self._capture_run()
        with patch.object(subprocess, "run", side_effect=fake):
            subprocess_util.isolated_run(["x"], capture_output=True, text=True)
        self.assertEqual(captured["encoding"], "utf-8")
        self.assertEqual(captured["errors"], "replace")

    def test_utf8_capture_not_applied_for_binary_spawn(self):
        captured, fake = self._capture_run()
        with patch.object(subprocess, "run", side_effect=fake):
            subprocess_util.isolated_run(["x"], capture_output=True)  # no text=True
        self.assertNotIn("encoding", captured)
        self.assertNotIn("errors", captured)

    def test_caller_encoding_wins(self):
        captured, fake = self._capture_run()
        with patch.object(subprocess, "run", side_effect=fake):
            subprocess_util.isolated_run(["x"], text=True, encoding="latin-1")
        self.assertEqual(captured["encoding"], "latin-1")


class IsolatedPopenTests(unittest.TestCase):
    def _capture_popen(self):
        captured: dict[str, object] = {}

        class FakeProc:
            pid = 1234

        def fake_popen(cmd, **kwargs):
            captured.update(kwargs)
            return FakeProc()

        return captured, fake_popen

    def test_defaults_stdin_devnull_and_start_new_session_on_posix(self):
        captured, fake = self._capture_popen()
        with patch.object(subprocess_util.os, "name", "posix"), \
             patch.object(subprocess, "Popen", side_effect=fake):
            subprocess_util.isolated_popen(["x"], stdout=99, stderr=99)
        self.assertIs(captured["stdin"], subprocess.DEVNULL)
        self.assertTrue(captured["start_new_session"])
        # Caller's log-file stdout/stderr preserved.
        self.assertEqual(captured["stdout"], 99)
        self.assertEqual(captured["stderr"], 99)

    def test_detached_flags_on_windows_when_no_caller_creationflags(self):
        captured, fake = self._capture_popen()
        with patch.object(subprocess_util.os, "name", "nt"), \
             patch.object(subprocess, "DETACHED_PROCESS", 0x08, create=True), \
             patch.object(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, create=True), \
             patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch.object(subprocess, "Popen", side_effect=fake):
            subprocess_util.isolated_popen(["x"])
        self.assertEqual(captured["creationflags"], 0x08 | 0x200 | 0x08000000)
        self.assertIs(captured["stdin"], subprocess.DEVNULL)

    def test_caller_creationflags_get_no_window_ored_not_detached(self):
        # A foreground Popen that pinned its own creationflags keeps them + the no-window bit, but is
        # NOT force-detached (honors the caller's foreground intent).
        captured, fake = self._capture_popen()
        with patch.object(subprocess_util.os, "name", "nt"), \
             patch.object(subprocess, "DETACHED_PROCESS", 0x08, create=True), \
             patch.object(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, create=True), \
             patch.object(subprocess, "CREATE_NO_WINDOW", 0x08000000, create=True), \
             patch.object(subprocess, "Popen", side_effect=fake):
            subprocess_util.isolated_popen(["x"], creationflags=0x01)
        self.assertEqual(captured["creationflags"], 0x01 | 0x08000000)
        self.assertNotIn("start_new_session", captured)


class Utf8ChildEnvTests(unittest.TestCase):
    """Wave 1p8gv (review F1): the spawned CHILD must encode its OWN stdout as UTF-8 — the field defect
    was an index child that ``print``ed ``→`` (U+2192) and crashed with UnicodeEncodeError on a cp1252
    console, which the parent only saw as a non-zero exit."""

    _NON_ASCII_PRINT = "import sys\nsys.stdout.write('\\u2192 done\\n')\n"  # prints '→ done'

    def test_sets_utf8_env_vars(self):
        env = subprocess_util.utf8_child_env({})
        self.assertEqual(env["PYTHONUTF8"], "1")
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8")

    def test_overrides_inherited_cp1252_pythonioencoding(self):
        # An inherited cp1252 PYTHONIOENCODING is deliberately overridden — UTF-8 is the guarantee.
        env = subprocess_util.utf8_child_env({"PYTHONIOENCODING": "cp1252"})
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8")

    def _run_child(self, env):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "child.py"
            script.write_text(self._NON_ASCII_PRINT, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(script)], env=env, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
            )

    def test_cp1252_child_crashes_then_utf8_child_env_fixes_it(self):
        # Baseline: a child forced to a cp1252 stdout (the Windows-console default, simulated via
        # PYTHONIOENCODING) CRASHES printing '→' — rc != 0, the silent index-failure mode.
        cp1252_env = dict(os.environ)
        cp1252_env["PYTHONIOENCODING"] = "cp1252"
        cp1252_env.pop("PYTHONUTF8", None)
        crashed = self._run_child(cp1252_env)
        self.assertNotEqual(crashed.returncode, 0, "cp1252 child should crash on '→' (baseline)")
        self.assertIn("UnicodeEncodeError", crashed.stderr)

        # Fix: utf8_child_env forces UTF-8 child stdio → rc == 0 and the glyph is written.
        fixed = self._run_child(subprocess_util.utf8_child_env(cp1252_env))
        self.assertEqual(fixed.returncode, 0, f"utf8_child_env child must not crash (stderr={fixed.stderr!r})")
        self.assertIn("→ done", fixed.stdout)


class WindowlessPythonwTests(unittest.TestCase):
    """Wave 1p8pe: windowless_pythonw() returns the tool-venv pythonw.exe on Windows when present, else
    None — the graceful-fallback contract every spawn-site conversion relies on. The real Windows
    console behavior can't run on POSIX, so we simulate os.name == 'nt' + a present/absent pythonw."""

    def test_returns_none_on_posix(self):
        with patch.object(subprocess_util.os, "name", "posix"):
            self.assertIsNone(subprocess_util.windowless_pythonw())

    def _fake_nt_os(self):
        # Patch ONLY subprocess_util's `os` reference so the helper's `os.name != "nt"` gate sees
        # Windows, while the REAL global os (and pathlib's Path) stays POSIX — otherwise patching the
        # shared os.name to "nt" makes pathlib try to instantiate WindowsPath and crash on macOS/Linux.
        import types as _types
        fake_os = _types.SimpleNamespace(name="nt")
        return patch.object(subprocess_util, "os", fake_os)

    def test_returns_pythonw_path_on_windows_when_present(self):
        # Simulate Windows: os.name == 'nt' and a candidate pythonw.exe exists on disk.
        with tempfile.TemporaryDirectory() as td:
            scripts = Path(td) / "Scripts"
            scripts.mkdir()
            pythonw = scripts / "pythonw.exe"
            pythonw.write_text("", encoding="utf-8")  # any file — the helper only checks is_file()
            import venv_bootstrap
            with self._fake_nt_os(), \
                 patch.object(venv_bootstrap, "tool_venv_base", return_value=Path(td)):
                result = subprocess_util.windowless_pythonw()
            self.assertEqual(result, str(pythonw))

    def test_returns_none_on_windows_when_no_pythonw(self):
        # Windows but no pythonw anywhere: tool venv base points at an empty dir, and the real
        # sys.executable's directory (the test interpreter's) has no pythonw.exe sibling — so all
        # candidates miss and the helper returns None (the graceful-fallback contract).
        with tempfile.TemporaryDirectory() as td:
            import venv_bootstrap
            with self._fake_nt_os(), \
                 patch.object(venv_bootstrap, "tool_venv_base", return_value=Path(td) / "empty"):
                self.assertIsNone(subprocess_util.windowless_pythonw())


class PreferredPythonResolverTests(unittest.TestCase):
    """Wave 1p8pe AC-1: server_impl._preferred_python and upgrade_wavefoundry._preferred_python prefer
    the windowless pythonw on Windows when present, and gracefully fall back to the venv python /
    sys.executable when windowless_pythonw() returns None (POSIX / no pythonw)."""

    def _load(self, name: str):
        import importlib
        return importlib.import_module(name)

    def test_returns_pythonw_when_windowless_available(self):
        for modname in ("server_impl", "upgrade_wavefoundry"):
            with self.subTest(module=modname):
                mod = self._load(modname)
                with patch.object(mod.subprocess_util, "windowless_pythonw",
                                  return_value="/venv/Scripts/pythonw.exe"):
                    self.assertEqual(mod._preferred_python(), "/venv/Scripts/pythonw.exe")

    def test_falls_back_to_venv_python_when_no_windowless(self):
        # windowless_pythonw() None (POSIX / no pythonw) → the venv python when it exists.
        for modname in ("server_impl", "upgrade_wavefoundry"):
            with self.subTest(module=modname):
                mod = self._load(modname)
                fake_vp = Path("/fake/venv/bin/python")

                class _VP:
                    def exists(self_inner):
                        return True

                    def __str__(self_inner):
                        return str(fake_vp)

                with patch.object(mod.subprocess_util, "windowless_pythonw", return_value=None), \
                     patch.object(mod.venv_bootstrap, "tool_venv_python", return_value=_VP()):
                    self.assertEqual(mod._preferred_python(), str(fake_vp))

    def test_falls_back_to_sys_executable_when_no_venv(self):
        for modname in ("server_impl", "upgrade_wavefoundry"):
            with self.subTest(module=modname):
                mod = self._load(modname)

                class _VP:
                    def exists(self_inner):
                        return False

                    def __str__(self_inner):
                        return "/never/used"

                with patch.object(mod.subprocess_util, "windowless_pythonw", return_value=None), \
                     patch.object(mod.venv_bootstrap, "tool_venv_python", return_value=_VP()):
                    self.assertEqual(mod._preferred_python(), mod.sys.executable)


if __name__ == "__main__":
    unittest.main()

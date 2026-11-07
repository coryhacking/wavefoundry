"""Recovery commands remain usable before setup and across command interpreters."""
from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import setup_commands as commands


class SetupCommandTests(unittest.TestCase):
    def test_posix_selected_root_roundtrips_metacharacters_without_execution(self):
        root = "/tmp/project with 'quotes';$(not-a-command)"
        recovery = commands.setup_recovery(root, "--full", windows=False)
        self.assertEqual(shlex.split(recovery["recovery_usage"]), recovery["recovery_argv"])
        self.assertEqual(recovery["recovery_argv"],
                         [root + "/.wavefoundry/bin/wf", "setup", "--root", root, "--full"])
        self.assertEqual(recovery["recovery_shell"], "posix")

    def test_windows_supplies_argv_independent_of_powershell_display(self):
        root = "C:\\Other repo\\O'Brien & tools"
        recovery = commands.setup_recovery(root, "--check", windows=True)
        self.assertEqual(recovery["recovery_argv"],
                         [root + "\\.wavefoundry\\bin\\wf.cmd", "setup", "--root", root, "--check"])
        self.assertEqual(recovery["recovery_shell"], "powershell")
        self.assertIn("O''Brien", recovery["recovery_usage"])
        self.assertTrue(recovery["recovery_usage"].startswith("& '"))
        self.assertTrue(callable(os.stat))
        self.assertIsNotNone(os.environ)

    def test_unknown_root_never_uses_working_directory(self):
        result = commands.setup_recovery(None)
        self.assertEqual(result["recovery_argv"], [])
        self.assertIsNone(result["recovery_shell"])
        self.assertNotIn(os.getcwd(), result["recovery_usage"])

    def test_helper_has_python39_syntax_and_no_tomllib_dependency(self):
        ast.parse((SCRIPTS / "setup_commands.py").read_text(), feature_version=(3, 9))
        code = '''import builtins, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name in ('tomllib', 'setup_readiness'):
        raise ImportError('not available on the bootstrap interpreter')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
sys.path.insert(0, sys.argv[1])
import setup_commands
print(setup_commands.setup_command('/chosen/root'))
'''
        result = subprocess.run([sys.executable, "-B", "-S", "-c", code, str(SCRIPTS)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/chosen/root/.wavefoundry/bin/wf", result.stdout)

    def _bootstrap(self, helper_failure=False):
        import render_platform_surfaces as renderer
        with tempfile.TemporaryDirectory() as directory:
            hook = Path(directory) / ".claude/hooks/test.py"
            hook.parent.mkdir(parents=True)
            # Supply only the bootstrap contract, with all optional libraries absent.
            preamble = '''import sys, types, builtins
sys.path.insert(0, %r)
sys.modules['venv_bootstrap'] = types.SimpleNamespace(
    activate_tool_venv=lambda **kwargs: None, activation_deferred=lambda: 'version_mismatch')
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name in %r:
        raise ImportError('unavailable bootstrap dependency')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
''' % (str(SCRIPTS), ('tomllib', 'setup_readiness', 'setup_commands') if helper_failure
                    else ('tomllib', 'setup_readiness'))
            hook.write_text(preamble + renderer.HOOK_BOOTSTRAP + "\n")
            return subprocess.run([sys.executable, "-B", "-S", str(hook)],
                                  capture_output=True, text=True, timeout=30)

    def test_actual_session_start_output_does_not_print_changed_or_cut_paths(self):
        import render_platform_surfaces as renderer
        from unittest.mock import patch
        namespace = {"__name__": "session_start_probe", "__file__": "/checkout/.claude/hooks/wf-session-start.py"}
        exec(compile(renderer.claude_session_start_source(), "session-hook", "exec"), namespace)
        for root in ("/tmp/bad\nforged\x1b[31m", "/tmp/" + "a" * 400, "/tmp/O'Brien"):
            for status in ("action_required", "indeterminate"):
                with self.subTest(root=root, status=status), patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": root}):
                    action = commands.setup_recovery(root)
                    lines = namespace["render"]({"status": status,
                        "reasons": [{"code": "dependencies_missing", "message": "missing"}],
                        "actions": [{"kind": "setup", "argv": action["recovery_argv"]}]}, commands.format_command)
                    self.assertTrue(all(len(line) <= 240 and line.isprintable() for line in lines), lines)
                    if "\n" in root or len(root) > 240:
                        self.assertNotIn(".wavefoundry/bin/wf", "\n".join(lines))
                    else:
                        self.assertIn("O", "\n".join(lines))

    def test_actual_hook_warns_without_tomllib_and_without_printing_to_stdout(self):
        result = self._bootstrap()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr.count("hook running without the tool venv"), 1)
        self.assertIn("/.wavefoundry/bin/wf", result.stderr)

    def test_actual_hook_keeps_static_warning_if_command_formatting_fails(self):
        result = self._bootstrap(helper_failure=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr.count("hook running without the tool venv"), 1)
        self.assertIn("local Wavefoundry setup launcher", result.stderr)


# Wave 22r99 (change 22r98): PowerShell ends a single-quoted string at any of five
# characters, so each one is doubled. Escapes keep the source unambiguous.
FIVE_QUOTES = ("\u0027", "\u2018", "\u2019", "\u201a", "\u201b")


class PowerShellQuoteTests(unittest.TestCase):
    def test_each_single_quote_character_is_doubled_with_an_exact_string(self):
        for quote in FIVE_QUOTES:
            with self.subTest(codepoint=f"U+{ord(quote):04X}"):
                self.assertEqual(commands.format_command(["C:\\Users\\O" + quote + "Brien\\wf.cmd"], windows=True),
                                 "& 'C:\\Users\\O" + quote + quote + "Brien\\wf.cmd'")

    def test_all_five_in_one_argument_and_posix_output_is_unchanged(self):
        argument = "a\u0027b\u2018c\u2019d\u201ae\u201bf"
        self.assertEqual(commands.format_command([argument, "plain"], windows=True),
                         "& 'a\u0027\u0027b\u2018\u2018c\u2019\u2019d\u201a\u201ae\u201b\u201bf' 'plain'")
        self.assertEqual(commands.format_command([argument, "plain"], windows=False),
                         shlex.join([argument, "plain"]))

    def test_setup_recovery_quotes_a_typographic_apostrophe_in_the_root(self):
        root = "C:\\Users\\O\u2019Brien\\repo"
        usage = commands.setup_recovery(root, windows=True)["recovery_usage"]
        self.assertEqual(usage, "& 'C:\\Users\\O\u2019\u2019Brien\\repo\\.wavefoundry\\bin\\wf.cmd' 'setup' "
                                "'--root' 'C:\\Users\\O\u2019\u2019Brien\\repo'")


if __name__ == "__main__":
    unittest.main()

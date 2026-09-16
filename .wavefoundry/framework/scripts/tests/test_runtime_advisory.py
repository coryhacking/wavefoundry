"""Runtime policy and executable-boundary stream/count regression controls."""
from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import runtime_advisory
import wf_cli


class RuntimePolicyTests(unittest.TestCase):
    def test_policy_uses_executing_version_not_executable_or_path(self):
        for version in ((3, 10, 9), (3, 11, 8), (3, 12, 1), (3, 13, 0), (3, 14, 0), (4, 0, 0)):
            for executable in ("/old/python3.11", "/new/python3.13"):
                with self.subTest(version=version, executable=executable), \
                     patch.object(sys, "version_info", version), \
                     patch.object(sys, "executable", executable), \
                     patch.dict(os.environ, {"PATH": "/unrelated/python3.14"}), \
                     patch("subprocess.run", side_effect=AssertionError("runtime policy must not probe")), \
                     contextlib.redirect_stdout(io.StringIO()) as out, \
                     contextlib.redirect_stderr(io.StringIO()) as err:
                    advisory = runtime_advisory.python_runtime_advisory()
                    if version[:2] in ((3, 11), (3, 12)):
                        self.assertEqual(advisory["code"], "python_runtime_deprecated")
                        self.assertEqual(advisory["severity"], "warning")
                        self.assertEqual(advisory["actual_version"], ".".join(map(str, version)))
                        self.assertEqual(advisory["recommended_minimum"], "3.13")
                        self.assertEqual(advisory["executable"], executable)
                        self.assertIn("Setup does not install Python", advisory["guidance"])
                        self.assertIn(executable, runtime_advisory.format_advisory(advisory))
                    else:
                        self.assertIsNone(advisory)
                    self.assertEqual(out.getvalue(), "")
                    self.assertEqual(err.getvalue(), "")

    def test_imports_and_reload_are_silent(self):
        with patch.object(sys, "version_info", (3, 11, 9)), \
             contextlib.redirect_stdout(io.StringIO()) as out, \
             contextlib.redirect_stderr(io.StringIO()) as err:
            for _ in range(2):
                importlib.reload(runtime_advisory)
                importlib.reload(wf_cli)
                runtime_advisory.python_runtime_advisory()
            self.assertEqual(out.getvalue(), "")
            self.assertEqual(err.getvalue(), "")

    def test_cli_dispatch_and_help_warn_once_each_without_changing_payload_or_exit(self):
        for version in ((3, 11, 9), (3, 12, 2), (3, 13, 0)):
            for argv in (["--help"], ["setup"], ["setup", "--check", "--json"], ["docs-lint"]):
                with self.subTest(version=version, argv=argv):
                    def dispatch(command, rest):
                        # Child policy reads, like health/monitor calls, never emit.
                        for _ in range(3):
                            runtime_advisory.python_runtime_advisory()
                        print('{"child":true}')
                        return 7
                    with patch.object(sys, "version_info", version), \
                         patch.object(wf_cli, "_dispatch", side_effect=dispatch), \
                         patch.object(wf_cli.venv_bootstrap, "activate_tool_venv"):
                        for _ in range(2):
                            with contextlib.redirect_stdout(io.StringIO()) as out, \
                                 contextlib.redirect_stderr(io.StringIO()) as err:
                                code = wf_cli.main(argv)
                            self.assertEqual(err.getvalue().count("is deprecated for Wavefoundry"), int(version[1] < 13))
                            self.assertNotIn("deprecated", out.getvalue())
                            self.assertEqual(code, 0 if argv == ["--help"] else 7)
                            if code == 7:
                                self.assertEqual(json.loads(out.getvalue()), {"child": True})


class McpExecutableAdvisoryTests(unittest.TestCase):
    """Run the real runner; replace heavyweight construction with a JSON transport stub."""

    def invoke(self, version, *args, imported=False):
        driver = r'''
import importlib, json, pathlib, runpy, sys, types
scripts, root, version, imported = sys.argv[1:5]
sys.argv = [str(pathlib.Path(scripts) / 'server.py'), '--root', root, *sys.argv[5:]]
sys.path.insert(0, scripts)
sys.dont_write_bytecode = True
sys.version_info = tuple(map(int, version.split('.')))
import setup_readiness, venv_bootstrap
setup_readiness.capture_loaded_identity = lambda: {}
def assess(*args, **kwargs):
    import runtime_advisory
    return {'status': 'action_required', 'startup_blocked': False, 'actions': [],
            'reasons': [{'code': 'independent', 'message': 'independent readiness issue'}],
            'advisories': [runtime_advisory.python_runtime_advisory()]}
setup_readiness.assess_setup = assess
venv_bootstrap.activate_tool_venv = lambda: None
venv_bootstrap.tool_venv_python = lambda: pathlib.Path(sys.executable)
sys.modules['server_impl'] = types.ModuleType('server_impl')
def trace(frame, event, arg):
    if event == 'call' and frame.f_code.co_name == 'main' and frame.f_code.co_filename.endswith('/server.py'):
        def build(root):
            frame.f_globals['_handler'] = object()
            class Transport:
                def run(self, **kwargs):
                    # Repeated assessments and imported/reloaded runner facades must stay silent.
                    for _ in range(2):
                        frame.f_globals['_assess_startup'](root)
                    import server
                    importlib.reload(server)
                    print(json.dumps({'jsonrpc': '2.0', 'id': 1, 'result': 'ok'}), flush=True)
            return Transport()
        frame.f_globals['build_server'] = build
        sys.settrace(None)
    return trace
sys.settrace(trace)
runpy.run_path(sys.argv[0], run_name='imported_runner' if imported == 'yes' else '__main__')
'''
        with tempfile.TemporaryDirectory() as root:
            return subprocess.run(
                [sys.executable, "-I", "-S", "-B", "-c", driver, str(SCRIPTS), root,
                 ".".join(map(str, version)), "yes" if imported else "no", *args],
                capture_output=True, text=True, timeout=15, stdin=subprocess.DEVNULL,
            )

    def test_real_executable_owns_one_notice_and_keeps_json_stdout(self):
        for version in ((3, 11, 9), (3, 12, 1), (3, 13, 0)):
            with self.subTest(version=version):
                completed = self.invoke(version)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(completed.stdout), {"jsonrpc": "2.0", "id": 1, "result": "ok"})
                self.assertEqual(completed.stderr.count("is deprecated for Wavefoundry"), int(version[1] < 13))
                self.assertIn("independent readiness issue", completed.stderr)

    def test_help_dry_run_and_imports_do_not_emit_advisory(self):
        for args, imported in ((["--help"], False), (["--dry-run"], False), ([], True)):
            with self.subTest(args=args, imported=imported):
                completed = self.invoke((3, 11, 9), *args, imported=imported)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertNotIn("deprecated", completed.stderr)
                self.assertNotIn("deprecated", completed.stdout)

    def test_setup_child_verification_does_not_repeat_cli_notice(self):
        import setup_wavefoundry

        def child(argv, **kwargs):
            self.assertEqual(argv[-1], "--dry-run")
            completed = self.invoke((3, 11, 9), "--dry-run")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            # The real setup helper inherits the child's stderr.
            print(completed.stderr, end="", file=sys.stderr)
            return completed

        def setup_main(argv=None):
            runtime_advisory.python_runtime_advisory()
            return setup_wavefoundry._run_mcp_server_dry_run(SCRIPTS.parents[2])

        with patch.object(sys, "version_info", (3, 11, 9)), \
             patch.object(setup_wavefoundry, "main", side_effect=setup_main), \
             patch.object(setup_wavefoundry.subprocess_util, "isolated_run", side_effect=child) as spawn, \
             contextlib.redirect_stdout(io.StringIO()) as out, \
             contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(wf_cli.main(["setup"]), 0)
        spawn.assert_called_once()
        self.assertEqual(err.getvalue().count("is deprecated for Wavefoundry"), 1)
        self.assertIn("mcp-server --dry-run: OK", err.getvalue())
        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

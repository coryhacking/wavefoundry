"""Native execution checks; skipped elsewhere, never counted as Windows qualification."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "nt", "requires native Windows process semantics")
class NativePythonDiagnosticTests(unittest.TestCase):
    def test_missing_python_preserves_seeded_checkout_and_fails_launcher(self):
        import render_platform_surfaces

        system32 = Path(os.environ["SystemRoot"]) / "System32"
        powershell = system32 / "WindowsPowerShell/v1.0/powershell.exe"
        with tempfile.TemporaryDirectory(prefix="wf seeded checkout ") as tmp:
            root = Path(tmp)
            scripts = root / ".wavefoundry/framework/scripts"
            scripts.mkdir(parents=True)
            shutil.copyfile(SCRIPTS / "diagnose_python.ps1", scripts / "diagnose_python.ps1")
            (scripts / "wf_cli.py").write_text("raise AssertionError('must not enter setup')\n")
            (root / ".mcp.json").write_text('{"command":"python3"}')
            (root / ".wavefoundry/install-log.md").write_text("- [x] Installation complete\n")
            (root / ".wavefoundry/index").mkdir()
            (root / ".wavefoundry/index/retained").write_bytes(b"existing index")
            render_platform_surfaces.render_bin_launchers(root)
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            env = dict(os.environ, PATH=str(system32))
            self.assertIsNone(shutil.which("python3", path=env["PATH"]), "fixture requires no system32 python3")
            diagnostic = subprocess.run(
                [str(powershell), "-NoProfile", "-File", str(scripts / "diagnose_python.ps1"), "-Json"],
                cwd=root, env=env, capture_output=True, text=True, timeout=45,
            )
            self.assertEqual(diagnostic.returncode, 2, diagnostic.stderr)
            report = json.loads(diagnostic.stdout)
            self.assertFalse(report["interpreter_ready"])
            self.assertEqual(report["probes"][0]["state"], "missing")
            self.assertEqual(report["probes"][0]["command"], "python3")
            self.assertTrue(any("ask IT" in line for line in report["next_steps"]))
            launcher = subprocess.run(
                [str(system32 / "cmd.exe"), "/d", "/c", str(root / ".wavefoundry/bin/wf.cmd"), "setup"],
                cwd=root, env=env, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(launcher.returncode, 2, launcher.stderr)
            self.assertIn("diagnose_python.ps1", launcher.stderr)
            self.assertIn("python3", launcher.stderr)
            self.assertEqual(before, {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_ROOT.parents[2]
SCRIPT_PATH = PROJECT_ROOT / "framework" / "scripts" / "render_platform_surfaces.py"


class RenderPlatformSurfacesScriptTests(unittest.TestCase):
    def test_renders_python_hook_entrypoints_and_configs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir).resolve()
            (repo_root / ".wavefoundry" / "framework" / "scripts").mkdir(parents=True)
            (repo_root / ".claude").mkdir()
            (repo_root / ".claude" / "hooks").mkdir()
            (repo_root / ".cursor" / "rules").mkdir(parents=True)
            (repo_root / ".cursor" / "hooks").mkdir()
            (repo_root / ".github").mkdir()
            (repo_root / ".github" / "hooks").mkdir(parents=True)
            (repo_root / ".github" / "workflows").mkdir(parents=True)
            (repo_root / ".git" / "hooks").mkdir(parents=True)
            (repo_root / ".junie").mkdir()
            (repo_root / ".github" / "copilot-instructions.md").write_text("", encoding="utf-8")
            (repo_root / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
            (repo_root / ".git" / "hooks" / "pre-push").write_text("#!/bin/sh\n", encoding="utf-8")
            (repo_root / ".junie" / "guidelines.md").write_text("", encoding="utf-8")
            (repo_root / ".claude" / "hooks" / "pre-edit.sh").write_text("# legacy\n", encoding="utf-8")
            (repo_root / ".claude" / "hooks" / "pycache-cleanup.py").write_text("# legacy\n", encoding="utf-8")
            (repo_root / ".cursor" / "hooks" / "reformat.py").write_text("# legacy\n", encoding="utf-8")
            (repo_root / ".github" / "hooks" / "pre-tool-use.sh").write_text("# legacy\n", encoding="utf-8")

            result = subprocess.run(
                ["python3", str(SCRIPT_PATH), "--repo-root", str(repo_root)],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            # Wave 1p590: hook commands are PROJECT-RELATIVE (never machine-absolute) so a clone works.
            if os.name == "nt":
                expected_claude_command = "cmd.exe /c .claude\\hooks\\pre-edit.cmd"
                expected_cursor_command = "cmd.exe /c .cursor\\hooks\\after-file-edit.cmd"
                expected_copilot_command = "cmd.exe /c .github\\hooks\\pre-tool-use.cmd"
            else:
                expected_claude_command = ".claude/hooks/pre-edit"
                expected_cursor_command = ".cursor/hooks/after-file-edit"
                expected_copilot_command = ".github/hooks/pre-tool-use"

            claude_settings = json.loads((repo_root / ".claude" / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(
                claude_settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"],
                expected_claude_command,
            )

            cursor_hooks = json.loads((repo_root / ".cursor" / "hooks.json").read_text(encoding="utf-8"))
            self.assertEqual(
                cursor_hooks["hooks"]["afterFileEdit"][0]["command"],
                expected_cursor_command,
            )

            copilot_hooks = json.loads((repo_root / ".github" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
            self.assertEqual(
                copilot_hooks["hooks"]["preToolUse"][0]["bash"],
                expected_copilot_command,
            )
            # Wave 1p590: Junie MCP uses the project-relative .wavefoundry/bin/mcp-server wrapper
            # (parity with root .mcp.json), not an absolute venv-Python path.
            junie_mcp = json.loads((repo_root / ".junie" / "mcp" / "mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(
                junie_mcp["mcpServers"]["wavefoundry"]["command"],
                ".wavefoundry/bin/mcp-server",
            )
            self.assertEqual(
                junie_mcp["mcpServers"]["wavefoundry"]["args"],
                [],
            )

            self.assertTrue((repo_root / ".claude" / "hooks" / "pre-edit").exists())
            self.assertTrue((repo_root / ".claude" / "hooks" / "pre-edit.py").exists())
            self.assertTrue((repo_root / ".claude" / "hooks" / "pre-edit.cmd").exists())
            self.assertTrue((repo_root / ".cursor" / "hooks" / "framework-plan-warn.py").exists())
            self.assertTrue((repo_root / ".cursor" / "hooks" / "framework-plan-warn").exists())
            self.assertFalse((repo_root / ".wavefoundry" / "bin" / "register-codex-mcp").exists())
            self.assertTrue((repo_root / ".cursor" / "hooks" / "framework-plan-warn.cmd").exists())
            self.assertTrue((repo_root / ".github" / "hooks" / "post-tool-use.py").exists())
            self.assertTrue((repo_root / ".github" / "hooks" / "post-tool-use").exists())
            self.assertTrue((repo_root / ".github" / "hooks" / "post-tool-use.cmd").exists())
            self.assertFalse((repo_root / ".claude" / "hooks" / "pre-edit.sh").exists())
            self.assertFalse((repo_root / ".claude" / "hooks" / "pycache-cleanup.py").exists())
            self.assertFalse((repo_root / ".cursor" / "hooks" / "reformat.py").exists())
            self.assertFalse((repo_root / ".github" / "hooks" / "pre-tool-use.sh").exists())
            self.assertTrue((repo_root / ".github" / "workflows" / "ci.yml").exists())
            self.assertTrue((repo_root / ".git" / "hooks" / "pre-push").exists())
            self.assertIn(
                "def read_payload_text()",
                (repo_root / ".claude" / "hooks" / "pre-edit.py").read_text(encoding="utf-8"),
            )
            self.assertIn(
                ".wavefoundry/guard-overrides.json",
                (repo_root / ".claude" / "hooks" / "pre-edit.py").read_text(encoding="utf-8"),
            )
            post_edit = (repo_root / ".claude" / "hooks" / "post-edit.py").read_text(encoding="utf-8")
            # 1p4ww: the reindex hook is a single bare project spawn (framework seeds/README
            # fold into the project docs index) — no separate framework-index reindex.
            self.assertIn("maybe_trigger_reindex", post_edit)
            self.assertNotIn("--index-dir", post_edit)
            self.assertNotIn("should_reindex_framework", post_edit)
            self.assertIn("python_exec = _venv_python_path()", post_edit)
            # Wave 1p35d (1p35n, AC-9): the rendered hook helper source must no longer
            # contain the dead `maybe_cleanup_pycache` helper or its `shutil` dependency.
            # The previous third hook was never actually wired in any host's settings,
            # but the helper code shipped in every rendered hook regardless. Verify it's
            # gone across every rendered hook file, not just one.
            rendered_hooks = [
                repo_root / ".claude" / "hooks" / "pre-edit.py",
                repo_root / ".claude" / "hooks" / "post-edit.py",
                repo_root / ".cursor" / "hooks" / "after-file-edit.py",
                repo_root / ".cursor" / "hooks" / "docs-lint.py",
                repo_root / ".cursor" / "hooks" / "framework-plan-warn.py",
                repo_root / ".cursor" / "hooks" / "seed-warn.py",
                repo_root / ".github" / "hooks" / "pre-tool-use.py",
                repo_root / ".github" / "hooks" / "post-tool-use.py",
            ]
            for path in rendered_hooks:
                if not path.exists():
                    continue
                body = path.read_text(encoding="utf-8")
                self.assertNotIn("maybe_cleanup_pycache", body, f"{path.name} still ships the retired pycache helper")
                self.assertNotIn("import shutil", body, f"{path.name} still imports shutil (only the pycache helper used it)")
            self.assertIn("[python_exec, str(indexer), \"--root\", str(REPO_ROOT)]", post_edit)
            cursor_after = (repo_root / ".cursor" / "hooks" / "after-file-edit.py").read_text(encoding="utf-8")
            self.assertIn("python_exec = _venv_python_path()", cursor_after)
            self.assertIn("[python_exec, str(gate)]", cursor_after)
            claude_sim = (repo_root / ".claude" / "hooks" / "simulate-hooks.py").read_text(encoding="utf-8")
            self.assertIn("python_exec = _venv_python_path()", claude_sim)
            self.assertIn("[python_exec, str(target)]", claude_sim)
            self.assertIn(
                ".wavefoundry/guard-overrides.json",
                (repo_root / ".claude" / "skills" / "upgrade-wave.md").read_text(encoding="utf-8"),
            )
            aiignore_text = (repo_root / ".aiignore").read_text(encoding="utf-8")
            self.assertIn(".wavefoundry/index/", aiignore_text)
            self.assertIn(".wavefoundry/framework/index/", aiignore_text)
            self.assertIn(".wavefoundry/*.lock", aiignore_text)
            self.assertIn(".wavefoundry/framework/*.lock", aiignore_text)
            self.assertNotIn(".wavefoundry/framework/seeds/*.prompt.md", aiignore_text)

            # bin launchers created by render_bin_launchers (called unconditionally from main)
            bin_lint = repo_root / ".wavefoundry" / "bin" / "docs-lint"
            bin_gardener = repo_root / ".wavefoundry" / "bin" / "docs-gardener"
            bin_dashboard = repo_root / ".wavefoundry" / "bin" / "wave-dashboard"
            bin_update_indexes = repo_root / ".wavefoundry" / "bin" / "update-indexes"
            bin_setup = repo_root / ".wavefoundry" / "bin" / "setup-wavefoundry"
            bin_upgrade = repo_root / ".wavefoundry" / "bin" / "upgrade-wavefoundry"
            self.assertTrue(bin_lint.exists(), ".wavefoundry/bin/docs-lint should be created")
            self.assertTrue(bin_gardener.exists(), ".wavefoundry/bin/docs-gardener should be created")
            self.assertTrue(bin_dashboard.exists(), ".wavefoundry/bin/wave-dashboard should be created")
            self.assertTrue(bin_update_indexes.exists(), ".wavefoundry/bin/update-indexes should be created")
            self.assertFalse((repo_root / ".wavefoundry" / "bin" / "wave_dashboard").exists(), "stale wave_dashboard should be removed")
            self.assertFalse((repo_root / ".wavefoundry" / "bin" / "register-codex-mcp").exists(), "register-codex-mcp should be removed")
            self.assertTrue(bin_setup.exists(), ".wavefoundry/bin/setup-wavefoundry should be created")
            self.assertTrue(bin_upgrade.exists(), ".wavefoundry/bin/upgrade-wavefoundry should be created")
            if os.name != "nt":
                self.assertTrue(os.access(bin_lint, os.X_OK), "docs-lint should be executable")
                self.assertTrue(os.access(bin_gardener, os.X_OK), "docs-gardener should be executable")
                self.assertTrue(os.access(bin_dashboard, os.X_OK), "wave-dashboard should be executable")
                self.assertTrue(os.access(bin_update_indexes, os.X_OK), "update-indexes should be executable")
                self.assertTrue(os.access(bin_setup, os.X_OK), "setup-wavefoundry should be executable")
                self.assertTrue(os.access(bin_upgrade, os.X_OK), "upgrade-wavefoundry should be executable")
            self.assertIn(
                ".wavefoundry/framework/scripts/docs_lint.py",
                bin_lint.read_text(encoding="utf-8"),
            )
            self.assertIn(
                ".wavefoundry/framework/scripts/docs_gardener.py",
                bin_gardener.read_text(encoding="utf-8"),
            )
            dashboard_src = bin_dashboard.read_text(encoding="utf-8")
            self.assertIn("nohup", dashboard_src)
            self.assertIn("--open", dashboard_src)
            self.assertIn(".wavefoundry/logs/dashboard.log", dashboard_src)
            self.assertIn("Wave dashboard started", dashboard_src)
            update_indexes_src = bin_update_indexes.read_text(encoding="utf-8")
            self.assertIn(".wavefoundry/framework/scripts/setup_index.py", update_indexes_src)
            self.assertIn("--background-code", update_indexes_src)
            self.assertIn("--verbose", update_indexes_src)


class RenderBinLaunchersTests(unittest.TestCase):
    """Unit tests for render_bin_launchers."""

    def _load_rps(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("rps", SCRIPT_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_creates_bin_launchers(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_bin_launchers(root)
            bin_lint = root / ".wavefoundry" / "bin" / "docs-lint"
            bin_gardener = root / ".wavefoundry" / "bin" / "docs-gardener"
            bin_dashboard = root / ".wavefoundry" / "bin" / "wave-dashboard"
            bin_update_indexes = root / ".wavefoundry" / "bin" / "update-indexes"
            bin_setup = root / ".wavefoundry" / "bin" / "setup-wavefoundry"
            bin_upgrade = root / ".wavefoundry" / "bin" / "upgrade-wavefoundry"
            bin_mcp_server = root / ".wavefoundry" / "bin" / "mcp-server"
            bin_wave_gate = root / ".wavefoundry" / "bin" / "wave-gate"
            self.assertTrue(bin_lint.exists())
            self.assertTrue(bin_gardener.exists())
            self.assertTrue(bin_dashboard.exists())
            self.assertTrue(bin_update_indexes.exists())
            self.assertFalse((root / ".wavefoundry" / "bin" / "wave_dashboard").exists())
            self.assertFalse((root / ".wavefoundry" / "bin" / "register-codex-mcp").exists())
            self.assertTrue(bin_setup.exists())
            self.assertTrue(bin_upgrade.exists())
            self.assertTrue(bin_mcp_server.exists(), ".wavefoundry/bin/mcp-server should be created (wave 130et)")
            self.assertTrue(bin_wave_gate.exists(), ".wavefoundry/bin/wave-gate should be created (wave 130et / 130f9)")
            self.assertFalse((root / ".wavefoundry" / "bin" / "upgrade-wavefoundry.bat").exists())
            lint_src = bin_lint.read_text(encoding="utf-8")
            gardener_src = bin_gardener.read_text(encoding="utf-8")
            dashboard_src = bin_dashboard.read_text(encoding="utf-8")
            update_indexes_src = bin_update_indexes.read_text(encoding="utf-8")
            setup_src = bin_setup.read_text(encoding="utf-8")
            upgrade_src = bin_upgrade.read_text(encoding="utf-8")
            mcp_server_src_text = bin_mcp_server.read_text(encoding="utf-8")
            wave_gate_src_text = bin_wave_gate.read_text(encoding="utf-8")
        _venv_var = "WAVEFOUNDRY_VENV"
        self.assertIn("docs_lint.py", lint_src)
        self.assertIn(_venv_var, lint_src)
        self.assertIn("docs_gardener.py", gardener_src)
        self.assertIn(_venv_var, gardener_src)
        self.assertIn("nohup", dashboard_src)
        self.assertIn(".wavefoundry/logs/dashboard.log", dashboard_src)
        self.assertIn(_venv_var, dashboard_src)
        self.assertIn("setup_index.py", update_indexes_src)
        self.assertIn("--background-code", update_indexes_src)
        self.assertIn("--verbose", update_indexes_src)
        self.assertIn(_venv_var, update_indexes_src)
        self.assertIn("setup_wavefoundry.py", setup_src)
        self.assertIn(_venv_var, setup_src)
        self.assertIn("upgrade_wavefoundry.py", upgrade_src)
        self.assertIn(_venv_var, upgrade_src)
        self.assertIn("server.py", mcp_server_src_text)
        self.assertIn("--root .", mcp_server_src_text)
        self.assertIn(_venv_var, mcp_server_src_text)
        self.assertIn("wave_gate.py", wave_gate_src_text)
        self.assertIn(_venv_var, wave_gate_src_text)
        self.assertIn("#!/usr/bin/env bash", lint_src)
        self.assertIn("#!/usr/bin/env bash", gardener_src)
        self.assertIn("#!/usr/bin/env bash", dashboard_src)
        self.assertIn("#!/usr/bin/env bash", setup_src)
        self.assertIn("#!/usr/bin/env bash", upgrade_src)
        self.assertIn("#!/usr/bin/env bash", mcp_server_src_text)
        self.assertIn("#!/usr/bin/env bash", wave_gate_src_text)

    def test_bin_launchers_are_executable(self):
        if os.name == "nt":
            self.skipTest("executable bit not applicable on Windows")
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_bin_launchers(root)
            bin_lint = root / ".wavefoundry" / "bin" / "docs-lint"
            bin_gardener = root / ".wavefoundry" / "bin" / "docs-gardener"
            bin_dashboard = root / ".wavefoundry" / "bin" / "wave-dashboard"
            bin_update_indexes = root / ".wavefoundry" / "bin" / "update-indexes"
            bin_setup = root / ".wavefoundry" / "bin" / "setup-wavefoundry"
            bin_upgrade = root / ".wavefoundry" / "bin" / "upgrade-wavefoundry"
            bin_mcp_server = root / ".wavefoundry" / "bin" / "mcp-server"
            bin_wave_gate = root / ".wavefoundry" / "bin" / "wave-gate"
            self.assertTrue(os.access(bin_lint, os.X_OK))
            self.assertTrue(os.access(bin_gardener, os.X_OK))
            self.assertTrue(os.access(bin_dashboard, os.X_OK))
            self.assertTrue(os.access(bin_update_indexes, os.X_OK))
            self.assertTrue(os.access(bin_setup, os.X_OK))
            self.assertTrue(os.access(bin_upgrade, os.X_OK))
            self.assertTrue(os.access(bin_mcp_server, os.X_OK))
            self.assertTrue(os.access(bin_wave_gate, os.X_OK))

    def test_render_bin_launchers_is_idempotent(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_bin_launchers(root)
            first_lint = (root / ".wavefoundry" / "bin" / "docs-lint").read_text(encoding="utf-8")
            rps.render_bin_launchers(root)
            second_lint = (root / ".wavefoundry" / "bin" / "docs-lint").read_text(encoding="utf-8")
        self.assertEqual(first_lint, second_lint)

    def test_render_bin_launchers_removes_stale_windows_upgrade_wrapper(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stale = root / ".wavefoundry" / "bin" / "upgrade-wavefoundry.bat"
            stale.parent.mkdir(parents=True, exist_ok=True)
            stale.write_text("stale\n", encoding="utf-8")
            rps.render_bin_launchers(root)
            self.assertFalse(stale.exists())


class MergeMcpServerTests(unittest.TestCase):
    """Unit tests for _merge_mcp_server, render_cursor_mcp_json, render_mcp_json, render_junie_mcp_json."""

    def _load_rps(self):
        import importlib.util, sys
        spec = importlib.util.spec_from_file_location("rps", SCRIPT_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_render_cursor_mcp_json_creates_stanza(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_cursor_mcp_json(root)
            data = json.loads((root / ".cursor" / "mcp.json").read_text(encoding="utf-8"))
        wf = data["mcpServers"]["wavefoundry"]
        self.assertEqual(wf["type"], "stdio")
        # Wave 1p590: portable wrapper, not an absolute venv-Python path.
        self.assertEqual(wf["command"], ".wavefoundry/bin/mcp-server")
        self.assertEqual(wf["args"], [])
        self.assertEqual(wf["cwd"], "${workspaceFolder}")

    def test_render_cursor_mcp_json_preserves_existing_servers(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_dir = root / ".cursor"
            cursor_dir.mkdir()
            (cursor_dir / "mcp.json").write_text(
                json.dumps({"mcpServers": {"other-tool": {"command": "node", "args": ["other.js"]}}}),
                encoding="utf-8",
            )
            rps.render_cursor_mcp_json(root)
            data = json.loads((cursor_dir / "mcp.json").read_text(encoding="utf-8"))
        # Pre-existing entry preserved
        self.assertIn("other-tool", data["mcpServers"])
        self.assertEqual(data["mcpServers"]["other-tool"]["command"], "node")
        # Wavefoundry entry written (wave 1p590: portable wrapper, not absolute venv Python)
        self.assertEqual(data["mcpServers"]["wavefoundry"]["command"], ".wavefoundry/bin/mcp-server")

    def test_render_mcp_json_uses_mcp_server_wrapper(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_mcp_json(root)
            data = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
        wf = data["mcpServers"]["wavefoundry"]
        self.assertEqual(wf["command"], ".wavefoundry/bin/mcp-server")
        self.assertEqual(wf["args"], [])

    def test_render_mcp_json_preserves_existing_servers(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".mcp.json").write_text(
                json.dumps({"mcpServers": {"my-other-server": {"command": "npx", "args": ["-y", "my-pkg"]}}}),
                encoding="utf-8",
            )
            rps.render_mcp_json(root)
            data = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
        self.assertIn("my-other-server", data["mcpServers"])
        self.assertIn("wavefoundry", data["mcpServers"])

    def test_render_junie_mcp_json_uses_portable_wrapper(self):
        # Wave 1p590: Junie MCP uses the project-relative .wavefoundry/bin/mcp-server wrapper
        # (which self-resolves repo root + venv), so no absolute command and no --root arg.
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_junie_mcp_json(root)
            data = json.loads((root / ".junie" / "mcp" / "mcp.json").read_text(encoding="utf-8"))
        wf = data["mcpServers"]["wavefoundry"]
        self.assertEqual(wf["command"], ".wavefoundry/bin/mcp-server")
        self.assertEqual(wf["args"], [])

    def test_merge_mcp_server_is_idempotent(self):
        rps = self._load_rps()
        stanza = {"command": "python3", "args": ["server.py", "--root", "."]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / ".mcp.json"
            rps._merge_mcp_server(target, stanza)
            first = target.read_text(encoding="utf-8")
            rps._merge_mcp_server(target, stanza)
            second = target.read_text(encoding="utf-8")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

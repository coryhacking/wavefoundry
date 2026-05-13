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
            repo_root = Path(temp_dir)
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

            if os.name == "nt":
                expected_claude_command = r"cmd.exe /c .claude\hooks\pre-edit.cmd"
                expected_cursor_command = r"cmd.exe /c .cursor\hooks\after-file-edit.cmd"
                expected_copilot_command = r"cmd.exe /c .github\hooks\pre-tool-use.cmd"
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
            junie_mcp = json.loads((repo_root / ".junie" / "mcp" / "mcp.json").read_text(encoding="utf-8"))
            self.assertEqual(
                junie_mcp["mcpServers"]["wavefoundry"]["command"],
                "python3",
            )
            self.assertEqual(
                junie_mcp["mcpServers"]["wavefoundry"]["args"],
                [".wavefoundry/framework/scripts/server.py", "--root", "."],
            )

            self.assertTrue((repo_root / ".claude" / "hooks" / "pre-edit").exists())
            self.assertTrue((repo_root / ".claude" / "hooks" / "pre-edit.py").exists())
            self.assertTrue((repo_root / ".claude" / "hooks" / "pre-edit.cmd").exists())
            self.assertTrue((repo_root / ".cursor" / "hooks" / "framework-plan-warn.py").exists())
            self.assertTrue((repo_root / ".cursor" / "hooks" / "framework-plan-warn").exists())
            self.assertTrue((repo_root / ".wavefoundry" / "bin" / "register-codex-mcp").exists())
            self.assertTrue((repo_root / ".cursor" / "hooks" / "framework-plan-warn.cmd").exists())
            self.assertTrue((repo_root / ".github" / "hooks" / "post-tool-use.py").exists())
            self.assertTrue((repo_root / ".github" / "hooks" / "post-tool-use").exists())
            self.assertTrue((repo_root / ".github" / "hooks" / "post-tool-use.cmd").exists())
            self.assertFalse((repo_root / ".claude" / "hooks" / "pre-edit.sh").exists())
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
            self.assertIn("--index-dir", post_edit)
            self.assertIn(".wavefoundry/framework/index", post_edit)
            self.assertIn("--include-prefix", post_edit)
            self.assertIn(".wavefoundry/framework", post_edit)
            self.assertIn("--no-ignore-files", post_edit)
            self.assertIn(
                ".wavefoundry/guard-overrides.json",
                (repo_root / ".claude" / "skills" / "upgrade-wave.md").read_text(encoding="utf-8"),
            )
            aiignore_text = (repo_root / ".aiignore").read_text(encoding="utf-8")
            self.assertIn(".wavefoundry/index/", aiignore_text)
            self.assertIn(".wavefoundry/framework/index/", aiignore_text)
            self.assertNotIn(".wavefoundry/framework/seeds/*.prompt.md", aiignore_text)

            # bin launchers created by render_bin_launchers (called unconditionally from main)
            bin_lint = repo_root / ".wavefoundry" / "bin" / "docs-lint"
            bin_gardener = repo_root / ".wavefoundry" / "bin" / "docs-gardener"
            bin_codex = repo_root / ".wavefoundry" / "bin" / "register-codex-mcp"
            self.assertTrue(bin_lint.exists(), ".wavefoundry/bin/docs-lint should be created")
            self.assertTrue(bin_gardener.exists(), ".wavefoundry/bin/docs-gardener should be created")
            self.assertTrue(bin_codex.exists(), ".wavefoundry/bin/register-codex-mcp should be created")
            if os.name != "nt":
                self.assertTrue(os.access(bin_lint, os.X_OK), "docs-lint should be executable")
                self.assertTrue(os.access(bin_gardener, os.X_OK), "docs-gardener should be executable")
                self.assertTrue(os.access(bin_codex, os.X_OK), "register-codex-mcp should be executable")
            self.assertIn(
                ".wavefoundry/framework/scripts/docs_lint.py",
                bin_lint.read_text(encoding="utf-8"),
            )
            self.assertIn(
                ".wavefoundry/framework/scripts/docs_gardener.py",
                bin_gardener.read_text(encoding="utf-8"),
            )
            codex_src = bin_codex.read_text(encoding="utf-8")
            self.assertIn("codex mcp add", codex_src)
            self.assertIn("repo_suffix()", codex_src)
            self.assertIn('SERVER_NAME="wavefoundry-$(repo_suffix "$REPO_ROOT")"', codex_src)
            self.assertIn(".wavefoundry/framework/scripts/server.py", codex_src)


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
            bin_codex = root / ".wavefoundry" / "bin" / "register-codex-mcp"
            self.assertTrue(bin_lint.exists())
            self.assertTrue(bin_gardener.exists())
            self.assertTrue(bin_codex.exists())
            lint_src = bin_lint.read_text(encoding="utf-8")
            gardener_src = bin_gardener.read_text(encoding="utf-8")
            codex_src = bin_codex.read_text(encoding="utf-8")
        self.assertIn("docs_lint.py", lint_src)
        self.assertIn("docs_gardener.py", gardener_src)
        self.assertIn("codex mcp add", codex_src)
        self.assertIn("repo_suffix()", codex_src)
        self.assertIn('SERVER_NAME="wavefoundry-$(repo_suffix "$REPO_ROOT")"', codex_src)
        self.assertIn("#!/usr/bin/env bash", lint_src)
        self.assertIn("#!/usr/bin/env bash", gardener_src)
        self.assertIn("#!/usr/bin/env bash", codex_src)

    def test_bin_launchers_are_executable(self):
        if os.name == "nt":
            self.skipTest("executable bit not applicable on Windows")
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_bin_launchers(root)
            bin_lint = root / ".wavefoundry" / "bin" / "docs-lint"
            bin_gardener = root / ".wavefoundry" / "bin" / "docs-gardener"
            bin_codex = root / ".wavefoundry" / "bin" / "register-codex-mcp"
            self.assertTrue(os.access(bin_lint, os.X_OK))
            self.assertTrue(os.access(bin_gardener, os.X_OK))
            self.assertTrue(os.access(bin_codex, os.X_OK))

    def test_render_bin_launchers_is_idempotent(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_bin_launchers(root)
            first_lint = (root / ".wavefoundry" / "bin" / "docs-lint").read_text(encoding="utf-8")
            rps.render_bin_launchers(root)
            second_lint = (root / ".wavefoundry" / "bin" / "docs-lint").read_text(encoding="utf-8")
        self.assertEqual(first_lint, second_lint)


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
        self.assertEqual(wf["command"], "python3")
        self.assertEqual(
            wf["args"],
            [".wavefoundry/framework/scripts/server.py", "--root", "${workspaceFolder}"],
        )
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
        # Wavefoundry entry written
        self.assertEqual(data["mcpServers"]["wavefoundry"]["command"], "python3")

    def test_render_mcp_json_includes_root_arg(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_mcp_json(root)
            data = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))
        self.assertIn("--root", data["mcpServers"]["wavefoundry"]["args"])
        self.assertIn(".", data["mcpServers"]["wavefoundry"]["args"])

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

    def test_render_junie_mcp_json_includes_root_arg(self):
        rps = self._load_rps()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rps.render_junie_mcp_json(root)
            data = json.loads((root / ".junie" / "mcp" / "mcp.json").read_text(encoding="utf-8"))
        self.assertIn("--root", data["mcpServers"]["wavefoundry"]["args"])

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

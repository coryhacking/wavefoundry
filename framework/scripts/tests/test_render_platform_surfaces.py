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

            self.assertTrue((repo_root / ".claude" / "hooks" / "pre-edit").exists())
            self.assertTrue((repo_root / ".claude" / "hooks" / "pre-edit.py").exists())
            self.assertTrue((repo_root / ".claude" / "hooks" / "pre-edit.cmd").exists())
            self.assertTrue((repo_root / ".cursor" / "hooks" / "framework-plan-warn.py").exists())
            self.assertTrue((repo_root / ".cursor" / "hooks" / "framework-plan-warn").exists())
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
            self.assertIn(
                ".wavefoundry/guard-overrides.json",
                (repo_root / ".claude" / "skills" / "upgrade-wave.md").read_text(encoding="utf-8"),
            )
            self.assertIn(
                ".wavefoundry/framework/seeds/*.prompt.md",
                (repo_root / ".aiignore").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_ROOT.parents[2]
RENDER_SCRIPT = PROJECT_ROOT / "framework" / "scripts" / "render_agent_surfaces.py"
GURU_STUB = "# Guru\n\nRole: guru\n"


class RenderAgentSurfacesTests(unittest.TestCase):
    def test_skips_when_guru_role_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            result = subprocess.run(
                ["python3", str(RENDER_SCRIPT), "--repo-root", str(repo_root)],
                cwd=PROJECT_ROOT / "framework" / "scripts",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("skip", result.stderr.lower())
            self.assertFalse((repo_root / ".cursor" / "rules" / "auto-guru.mdc").exists())

    def test_renders_tier2_and_tier3_when_guru_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "docs" / "agents").mkdir(parents=True)
            (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
            (repo_root / ".cursor" / "rules").mkdir(parents=True)
            (repo_root / ".cursor" / "rules" / "project-context.mdc").write_text(
                "# Cursor\n\n## Key Guardrails\n\n- stage gate\n",
                encoding="utf-8",
            )
            (repo_root / ".claude" / "agents").mkdir(parents=True)
            (repo_root / ".junie").mkdir()
            (repo_root / ".junie" / "guidelines.md").write_text(
                "# Junie\n\n## Key Rules\n\n- other\n",
                encoding="utf-8",
            )
            (repo_root / "CLAUDE.md").write_text(
                "# Claude\n\n## Startup Order\n\n1. AGENTS.md\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(RENDER_SCRIPT), "--repo-root", str(repo_root)],
                cwd=PROJECT_ROOT / "framework" / "scripts",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

            cursor_rule = repo_root / ".cursor" / "rules" / "auto-guru.mdc"
            self.assertTrue(cursor_rule.is_file())
            self.assertIn("alwaysApply: true", cursor_rule.read_text(encoding="utf-8"))

            claude_agent = repo_root / ".claude" / "agents" / "guru.md"
            self.assertTrue(claude_agent.is_file())
            self.assertIn("PROACTIVELY", claude_agent.read_text(encoding="utf-8"))

            codex_skill = repo_root / ".codex" / "skills" / "auto-guru" / "SKILL.md"
            self.assertTrue(codex_skill.is_file())

            junie = (repo_root / ".junie" / "guidelines.md").read_text(encoding="utf-8")
            self.assertIn("waveframework:auto-guru begin", junie)
            self.assertIn("code_ask", junie)

            claude = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("waveframework:auto-guru begin", claude)
            self.assertIn("guru", claude)


if __name__ == "__main__":
    unittest.main()

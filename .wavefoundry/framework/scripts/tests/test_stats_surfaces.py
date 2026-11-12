"""Project statistics uses one payload across the registered tool, CLI and skill."""
from __future__ import annotations

import asyncio
import contextlib
import io
import json
import sys
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_tool_surface_golden import _BootedSurface


class StatisticsSurfaceTests(_BootedSurface):
    def test_directory_option_reaches_registered_tool_and_cli(self):
        import project_stats
        import wf_cli
        (self.root / "main.py").write_text("value = 1\n")
        expected = project_stats.collect_project_stats(self.root, ["code"], group_by="directory")
        tool = self.mcp._tool_manager._tools["wf_stats"]
        result = asyncio.run(tool.run({"sections": ["code"], "group_by": "directory"}))
        if hasattr(result, "structured_content"):
            result = result.structured_content
        self.assertEqual(result["data"], expected)
        output = io.StringIO()
        with patch.object(wf_cli.venv_bootstrap, "activate_tool_venv"), patch.object(sys, "argv", list(sys.argv)), contextlib.redirect_stdout(output):
            self.assertEqual(wf_cli.main(["stats", "--root", str(self.root), "--section", "code", "--group-by", "directory", "--json"]), 0)
        self.assertEqual(json.loads(output.getvalue()), expected)
        self.assertEqual(self.impl.wf_stats_response(self.root, [], group_by="nested")["status"], "error")

    def test_token_detail_option_reaches_registered_tool_and_cli(self):
        import project_stats
        import wf_cli
        expected = project_stats.collect_project_stats(self.root, ["token_savings"], include_wave_details=True)
        tool = self.mcp._tool_manager._tools["wf_stats"]
        result = asyncio.run(tool.run({"sections": ["token_savings"], "include_wave_details": True}))
        if hasattr(result, "structured_content"):
            result = result.structured_content
        self.assertEqual(result["data"], expected)
        self.assertEqual(result["data"]["sections"]["token_savings"]["wave_details"], [])
        out = io.StringIO()
        with patch.object(wf_cli.venv_bootstrap, "activate_tool_venv"), patch.object(sys, "argv", list(sys.argv)), contextlib.redirect_stdout(out):
            self.assertEqual(wf_cli.main(["stats", "--root", str(self.root), "--section", "token_savings", "--include-wave-details", "--json"]), 0)
        self.assertEqual(json.loads(out.getvalue()), expected)
        self.assertEqual(self.impl.wf_stats_response(self.root, [], include_wave_details="true")["status"], "error")

    def test_registered_tool_and_cli_share_payload_and_reject_unknown_sections(self):
        import wf_cli
        import project_stats

        payload = project_stats.collect_project_stats(self.root, sections=["secrets"])
        tool = self.mcp._tool_manager._tools["wf_stats"]
        self.assertEqual(self.roster.TOOL_TIERS["wf_stats"], "read")
        result = asyncio.run(tool.run({"sections": ["secrets"]}))
        # FastMCP's run returns the underlying envelope on this shipped SDK.
        if hasattr(result, "structured_content"):
            result = result.structured_content
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"], payload)
        with patch.object(wf_cli.venv_bootstrap, "activate_tool_venv"), patch.object(sys, "argv", list(sys.argv)):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = wf_cli.main(["stats", "--root", str(self.root), "--section", "secrets", "--json"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.getvalue()), payload)
        invalid = asyncio.run(tool.run({"sections": ["not-a-section"]}))
        if hasattr(invalid, "structured_content"):
            invalid = invalid.structured_content
        self.assertEqual(invalid["status"], "error")
        self.assertEqual(invalid["diagnostics"][0]["code"], "invalid_arguments")



    def test_index_degradation_preserves_malformed_state(self):
        index = self.root / ".wavefoundry/index"
        index.mkdir(parents=True)
        state = index / "index-build.json"
        state.write_bytes(b"not JSON")
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = self.impl.wf_stats_response(self.root, sections=["index", "secrets"])
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["data"]["sections"]["index"]["available"])
        self.assertTrue(result["data"]["sections"]["secrets"]["available"])
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_actual_cli_entry_does_not_write_fixture(self):
        script = Path(__file__).resolve().parents[1] / "wf_cli.py"
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        env = dict(os.environ)
        env.pop("PYTHONPYCACHEPREFIX", None)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        # Exercise the real CLI bootstrap, not the test runner's injected
        # sitecustomize (which imports before the CLI can disable bytecode).
        env.pop("PYTHONPATH", None)
        completed = subprocess.run([sys.executable, str(script), "stats", "--root", str(self.root), "--section", "secrets", "--json"], capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["sections"]["secrets"]["available"])
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_sensitive_finding_fields_never_reach_tool_or_cli(self):
        import wf_cli

        path = self.root / "docs/scan-findings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        private = "PRIVATE-FINDING-SENTINEL"
        path.write_text(json.dumps([{
            "rule_id": "fixture", "status": "false-positive",
            "matched_text": private, "file": private, "line_hash": private,
            "confirmations": [{"git_user_email": private}], "override_reason": private,
        }]))
        tool = self.mcp._tool_manager._tools["wf_stats"]
        for contents in (path.read_text(), private):
            path.write_text(contents)
            result = asyncio.run(tool.run({"sections": ["secrets"]}))
            if hasattr(result, "structured_content"):
                result = result.structured_content
            self.assertEqual(result["status"], "ok")
            self.assertNotIn(private, json.dumps(result))
            for flags in ([], ["--json"]):
                output = io.StringIO()
                with patch.object(wf_cli.venv_bootstrap, "activate_tool_venv"), patch.object(sys, "argv", list(sys.argv)), contextlib.redirect_stdout(output):
                    self.assertEqual(wf_cli.main(["stats", "--root", str(self.root), "--section", "secrets", *flags]), 0)
                self.assertNotIn(private, output.getvalue())


class StatisticsSkillTests(unittest.TestCase):
    def test_skill_renders_without_prompt_and_preserves_presentation_limits(self):
        import render_agent_surfaces as ras
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for host, _ in ras.SKILL_HOSTS:
                (root / host).mkdir()
            ras.render_skills(root)
            self.assertFalse((root / "docs/prompts").exists())
            for _, skills in ras.SKILL_HOSTS:
                text = (root / skills / "wf-stats/SKILL.md").read_text()
                for required in ("wf_stats", "stats --json", "summary", "section headings", "tables", "estimate", "incomplete", "Do not recount", "done, deferred, open and total", "Changes assigned to waves", "Plans not assigned", "Implementation tasks", "Source-code TODO markers", "including tests", "not-this-scope", "Lifecycle", "Markdown", "all eight sections", "Documents and roles", "Memories", "Index", "stage and record coverage", "modification time is not scan time", "not box-drawing", "test-share ratio", "files, total lines", "effective non-test/test", "include_wave_details", "No paired evaluations recorded", "machine-local", "candidates awaiting validation"):
                    self.assertIn(required, text)
            self.assertIsNone(next(s for s in ras.SKILL_REGISTRY if s.name == "wf-stats").requires_doc)


if __name__ == "__main__":
    unittest.main()

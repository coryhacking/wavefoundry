from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TESTS_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_ROOT.parents[2]
SCRIPTS_ROOT = PROJECT_ROOT / "framework" / "scripts"
RENDER_SCRIPT = SCRIPTS_ROOT / "render_agent_surfaces.py"
GURU_STUB = "# Guru\n\nRole: guru\n"

sys.path.insert(0, str(SCRIPTS_ROOT))
import render_agent_surfaces as ras  # noqa: E402


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

            codex_mcp_config = repo_root / ".codex" / "config.toml"
            self.assertTrue(codex_mcp_config.is_file())
            self.assertIn("[mcp_servers.wavefoundry]", codex_mcp_config.read_text(encoding="utf-8"))

            junie = (repo_root / ".junie" / "guidelines.md").read_text(encoding="utf-8")
            self.assertIn("waveframework:auto-guru begin", junie)
            self.assertIn("code_ask", junie)

            claude = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("waveframework:auto-guru begin", claude)
            self.assertIn("guru", claude)


class AutoGuruRoutingAnchorRegressionTests(unittest.TestCase):
    """Wave 1p3dk / 1p3hf (intent-based-auto-guru-routing) regression guard.

    The literal failure-mode example ``tell me about the way authentication works``
    is the load-bearing anchor for the auto-Guru routing examples table in
    `seed-050` and the rendered `AGENTS.md`. This test asserts the anchor's
    presence in both surfaces so a future seed edit, render, or refactor that
    accidentally drops the example fails loudly.

    The brittleness is intentional: this single phrase is the demonstrable
    failure case that motivated the table's existence. Any change that needs
    to rephrase the anchor should rephrase it in the same change as updating
    this test — the coupling enforces the documentation discipline.
    """

    # The phrase is the semantic anchor; casing is operator-driven (the original
    # user message was lowercase; rendered docs use sentence case). The test is
    # case-insensitive — the load-bearing element is the phrase, not the casing.
    FAILURE_MODE_ANCHOR = "tell me about the way authentication works"

    def _repo_root(self) -> Path:
        # TESTS_ROOT = .../.wavefoundry/framework/scripts/tests
        # parents[2] = .wavefoundry; .parent = repo root
        return TESTS_ROOT.parents[2].parent

    def _assertAnchorIn(self, text: str, surface_label: str, hint: str) -> None:
        """Case-insensitive contains check. Brittleness is intentional on the
        phrase itself; casing variation is acceptable."""
        self.assertIn(
            self.FAILURE_MODE_ANCHOR.lower(), text.lower(),
            f"{surface_label} must contain the failure-mode anchor "
            f"'{self.FAILURE_MODE_ANCHOR}' (case-insensitive) — {hint}",
        )

    def test_anchor_present_in_seed_050(self) -> None:
        seed_path = self._repo_root() / ".wavefoundry" / "framework" / "seeds" / "050-agent-entry-surface-bootstrap.prompt.md"
        self.assertTrue(seed_path.is_file(), f"missing {seed_path}")
        self._assertAnchorIn(
            seed_path.read_text(encoding="utf-8"),
            "seed-050",
            "see wave 1p3dk / 1p3hf rationale",
        )

    def test_anchor_present_in_seed_211(self) -> None:
        seed_path = self._repo_root() / ".wavefoundry" / "framework" / "seeds" / "211-guru.prompt.md"
        self.assertTrue(seed_path.is_file(), f"missing {seed_path}")
        self._assertAnchorIn(
            seed_path.read_text(encoding="utf-8"),
            "seed-211 (Guru role doc)",
            "mirror seed-050's failure-mode anchor per the AC-5 mirroring contract",
        )

    def test_anchor_present_in_rendered_agents_md(self) -> None:
        agents_md = self._repo_root() / "AGENTS.md"
        self.assertTrue(agents_md.is_file(), f"missing {agents_md}")
        self._assertAnchorIn(
            agents_md.read_text(encoding="utf-8"),
            "AGENTS.md",
            "the lead agent reads this surface before routing decisions",
        )

    def test_anchor_in_examples_table_context(self) -> None:
        """The anchor must appear inside an examples table marked as
        anchoring-not-rule. Guards against the table being dropped while the
        anchor survives in unrelated prose."""
        agents_md = self._repo_root() / "AGENTS.md"
        text = agents_md.read_text(encoding="utf-8")
        lines = text.splitlines()
        anchor_lower = self.FAILURE_MODE_ANCHOR.lower()
        anchor_line_idx = next(
            (i for i, line in enumerate(lines) if anchor_lower in line.lower()),
            -1,
        )
        self.assertGreaterEqual(anchor_line_idx, 0, "anchor missing entirely")
        window = "\n".join(lines[max(0, anchor_line_idx - 20):anchor_line_idx + 20])
        self.assertIn("Route to Guru?", window,
            "anchor must appear within the examples-table context (Route to Guru? column header expected nearby)")
        self.assertIn("anchoring", window.lower(),
            "table must be framed as 'anchoring examples for an intent rule, not the rule itself' — "
            "guards against the table becoming a keyword-match list")


class AgentSurfaceNewlineTests(unittest.TestCase):
    """Wave 1p9ix (F14) — render_agent_surfaces.write_text must write embedded
    line terminators VERBATIM (newline="") so the freshly generated agent surfaces
    are byte-identical LF on every host, matching render_platform_surfaces.write_text.
    """

    # The four freshly generated agent surfaces write_text produces.
    _GENERATED_SURFACES = (
        (".cursor", "rules", "auto-guru.mdc"),
        (".claude", "agents", "guru.md"),
        (".codex", "skills", "auto-guru", "SKILL.md"),
        (".codex", "config.toml"),
    )

    def _make_repo(self, repo_root: Path) -> None:
        (repo_root / "docs" / "agents").mkdir(parents=True)
        (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
        (repo_root / ".cursor" / "rules").mkdir(parents=True)
        (repo_root / ".claude" / "agents").mkdir(parents=True)

    def test_write_text_uses_newline_empty_and_writes_verbatim(self) -> None:
        # Durable, host-independent guard: capture the newline kwarg passed to
        # Path.open. The old `path.write_text(content, encoding="utf-8")` never
        # passes newline="" (it uses the default newline=None, which translates
        # every "\n" -> os.linesep on native Windows), so this fails on a revert
        # on ANY host, not only on Windows.
        real_open = Path.open
        captured: dict[str, object] = {}

        def spy_open(self, *args, **kwargs):  # noqa: ANN001
            captured["newline"] = kwargs.get("newline", "<absent>")
            return real_open(self, *args, **kwargs)

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "surface.txt"
            with patch.object(Path, "open", spy_open):
                ras.write_text(target, "line-1\nline-2\nline-3\n")
            self.assertEqual(
                captured.get("newline"), "",
                "write_text must open with newline='' so embedded \\n are written verbatim",
            )
            raw = target.read_bytes()
            self.assertNotIn(b"\r\n", raw, "written bytes must be LF-only")
            self.assertEqual(target.read_text(encoding="utf-8"), "line-1\nline-2\nline-3\n")

    def test_rendered_agent_surfaces_are_lf_only(self) -> None:
        # Render the four generated surfaces and assert their bytes contain no
        # \r\n (LF-only) regardless of os.linesep on the rendering host.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._make_repo(repo_root)
            written = ras.render_agent_surfaces(repo_root)
            self.assertTrue(written, "render should produce surfaces when guru.md is present")
            for parts in self._GENERATED_SURFACES:
                surface = repo_root.joinpath(*parts)
                self.assertTrue(surface.is_file(), f"missing generated surface {surface}")
                raw = surface.read_bytes()
                self.assertNotIn(
                    b"\r\n", raw,
                    f"{'/'.join(parts)} must be written LF-only (no CRLF)",
                )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import re
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
PLATFORM_RENDER_SCRIPT = SCRIPTS_ROOT / "render_platform_surfaces.py"
GURU_STUB = "# Guru\n\nRole: guru\n"

sys.path.insert(0, str(SCRIPTS_ROOT))
import render_agent_surfaces as ras  # noqa: E402


class ReviewProtocolCarrierRegistryTests(unittest.TestCase):
    def test_independent_reference_contract_is_bounded_and_preserves_independence(self) -> None:
        seeds_root = PROJECT_ROOT / "framework" / "seeds"
        core = (seeds_root / "209-agent-harness-core.prompt.md").read_text(encoding="utf-8")
        code = (seeds_root / "221-code-reviewer.prompt.md").read_text(encoding="utf-8")
        qa = (seeds_root / "239-qa-reviewer.prompt.md").read_text(encoding="utf-8")

        for literal in (
            "one highest-risk differential or invariant probe",
            "normative specification",
            "materially independent implementation",
            "prior-version behavior contract",
            "authoritative schema/model",
            "metamorphic invariant",
            "fixed seed or durable fixture",
            "reject invalid generated inputs before comparison",
            "same hypothesis list is not an independent reference",
            "Implementer-authored evidence remains `independent: false`",
            "If no credible independent reference exists",
            "not reviewer adherence",
        ):
            self.assertIn(literal, core)
        self.assertIn("Name the reference, the exact promised property", code)
        self.assertIn("name the assertion that would falsify it", qa)
        self.assertIn("Executable review never broadens task authority", core)
        self.assertNotIn("oracle_id", core + code + qa)
        self.assertNotIn("oracle_property", core + code + qa)

    def test_independent_reference_carrier_is_role_scoped_and_carries_the_proof_ceiling(self) -> None:
        code = ras._carrier_protocol_block(
            ras.ReviewProtocolCarrier(
                "221-code-reviewer.prompt.md", "docs/agents/code-reviewer.md"
            )
        )
        qa = ras._carrier_protocol_block(
            ras.ReviewProtocolCarrier(
                "239-qa-reviewer.prompt.md", "docs/agents/qa-reviewer.md"
            )
        )
        security = ras._carrier_protocol_block(
            ras.ReviewProtocolCarrier(
                "229-security-reviewer.prompt.md", "docs/agents/security-reviewer.md"
            )
        )

        for role_block in (code, qa):
            self.assertIn("same-hypothesis helper", role_block)
            self.assertIn("`independent: false`", role_block)
            self.assertIn("Carrier-presence tests prove propagation", role_block)
        self.assertIn("assertion that would falsify", qa)
        self.assertNotIn("Independent-reference verification", security)

        repo_root = TESTS_ROOT.parents[3]
        for rel in ("docs/agents/code-reviewer.md", "docs/agents/qa-reviewer.md"):
            rendered = (repo_root / rel).read_text(encoding="utf-8")
            self.assertIn(ras.INDEPENDENT_REFERENCE_CARRIER_BLOCK, rendered)

    def test_dual_implementation_reference_scenario_carries_bounded_falsification_contract(self) -> None:
        # AC-3 scenario fixture: a deterministic fallback parser has a materially
        # independent grammar-backed implementation. The carrier must ask for the exact
        # compared property and common-mode limit, while keeping the probe finite.
        scenario = {
            "mechanism": "fallback parser",
            "reference": "materially independent grammar-backed parser",
            "promised_property": "stable public initializer identity",
            "highest_risk_input": "valid declaration-prefix boundary",
        }
        self.assertNotEqual(scenario["mechanism"], scenario["reference"])
        code = ras._carrier_protocol_block(
            ras.ReviewProtocolCarrier(
                "221-code-reviewer.prompt.md", "docs/agents/code-reviewer.md"
            )
        )
        qa = ras._carrier_protocol_block(
            ras.ReviewProtocolCarrier(
                "239-qa-reviewer.prompt.md", "docs/agents/qa-reviewer.md"
            )
        )
        code_flat = " ".join(code.split())
        self.assertIn("one highest-risk probe bounded, reproducible", code_flat)
        self.assertIn("exact promised property", code_flat)
        self.assertIn("common-mode", code_flat)
        self.assertIn("assertion that would falsify", qa)
        self.assertIn("limited to valid inputs", " ".join(qa.split()))

    def test_no_reference_or_unsafe_probe_scenario_narrows_claim_without_broadening_authority(self) -> None:
        # AC-3 scenario fixture: no credible reference exists and the tempting comparison
        # would require an unauthorized external mutation. The canonical rule must record
        # the limitation/narrow the claim, not invent a reference or broaden task authority.
        scenario = {
            "credible_reference": None,
            "candidate_probe": "unauthorized external mutation",
            "authorized": False,
            "expected_disposition": "record narrow limitation",
        }
        self.assertIsNone(scenario["credible_reference"])
        self.assertFalse(scenario["authorized"])
        core = (
            PROJECT_ROOT / "framework" / "seeds" / "209-agent-harness-core.prompt.md"
        ).read_text(encoding="utf-8")
        self.assertIn("If no credible independent reference exists", core)
        self.assertIn("record that narrow limitation", core)
        self.assertIn("Executable review never broadens task authority", core)
        self.assertIn("not proof of universal correctness", core)

    def test_manifest_is_derived_from_unique_registry_destinations(self) -> None:
        expected = tuple(row.destination for row in ras.REVIEW_PROTOCOL_CARRIER_REGISTRY)
        self.assertEqual(ras.REVIEW_PROTOCOL_CARRIER_MANIFEST, expected)
        self.assertEqual(len(expected), len(set(expected)))
        self.assertIn("docs/agents/qa-reviewer.md", expected)
        self.assertIn("docs/prompts/agents/review-wave.prompt.md", expected)
        self.assertIn("docs/contributing/review-and-evals.md", expected)
        seeds_root = PROJECT_ROOT / "framework" / "seeds"
        missing_sources = [
            row.source_seed
            for row in ras.REVIEW_PROTOCOL_CARRIER_REGISTRY
            if not (seeds_root / row.source_seed).is_file()
        ]
        self.assertEqual(missing_sources, [])

    def test_self_host_ownership_contracts_cover_every_registry_destination(self) -> None:
        repo_root = TESTS_ROOT.parents[3]
        ownership = (repo_root / "docs" / "contributing" / "review-and-evals.md").read_text(
            encoding="utf-8"
        )
        change = next((repo_root / "docs" / "waves").glob("1skt1*/1siu0*.md")).read_text(
            encoding="utf-8"
        )
        for carrier in ras.REVIEW_PROTOCOL_CARRIER_REGISTRY:
            self.assertIn(carrier.destination, ownership, carrier.destination)
            self.assertIn(carrier.destination, change, carrier.destination)

    def test_reconciles_before_guru_guard_preserves_extensions_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            target = repo_root / "docs" / "agents" / "code-reviewer.md"
            target.parent.mkdir(parents=True)
            operator_extension = "## Project extension\n\n- keep this byte-for-byte\n"
            target.write_text("# Code Reviewer\n\n" + operator_extension, encoding="utf-8")

            written = ras.render_agent_surfaces(repo_root)
            self.assertIn("docs/agents/code-reviewer.md", written)
            self.assertIn("docs/agents/qa-reviewer.md", written)
            self.assertIn("docs/prompts/review-wave.prompt.md", written)
            self.assertIn("docs/prompts/create-wave.prompt.md", written)
            first = target.read_bytes()
            text = first.decode("utf-8")
            self.assertIn(operator_extension, text)
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, text)
            self.assertIn("four-way actionability gate", text)
            self.assertIn("Independent-reference verification", text)
            qa_text = (repo_root / "docs" / "agents" / "qa-reviewer.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("assertion that would falsify", qa_text)
            self.assertIn("`independent: false`", qa_text)
            self.assertFalse((repo_root / "docs" / "agents" / "guru.md").exists())
            create_wave = (repo_root / "docs" / "prompts" / "create-wave.prompt.md").read_text(encoding="utf-8")
            for literal in (
                "review-evidence-source: events.jsonl",
                "exactly empty file",
                "No review findings recorded.",
                "docs/waves/review-evidence-adoptions.json",
            ):
                self.assertIn(literal, create_wave)
            self.assertNotIn("review-evidence-protocol: 1", create_wave)
            self.assertNotIn("waveframework:finding-synthesis", create_wave)
            self.assertNotIn("```jsonl", create_wave)

            self.assertEqual(ras.render_agent_surfaces(repo_root), [])
            self.assertEqual(target.read_bytes(), first)

    def test_stale_owned_region_refreshes_without_touching_surrounding_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            target = repo_root / "docs" / "prompts" / "review-wave.prompt.md"
            target.parent.mkdir(parents=True)
            prefix = "# Review Wave\n\nproject-prefix\n\n"
            suffix = "\n\nproject-suffix\n"
            target.write_text(
                prefix
                + ras.REVIEW_PROTOCOL_MARKER_BEGIN
                + "\nstale\n"
                + ras.REVIEW_PROTOCOL_MARKER_END
                + suffix,
                encoding="utf-8",
            )

            ras.reconcile_review_protocol_surfaces(repo_root)
            text = target.read_text(encoding="utf-8")
            self.assertTrue(text.startswith(prefix))
            self.assertTrue(text.endswith(suffix))
            self.assertNotIn("\nstale\n", text)
            self.assertIn("public or registered", text)

    def test_malformed_owned_markers_fail_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            target = repo_root / "docs" / "agents" / "qa-reviewer.md"
            target.parent.mkdir(parents=True)
            original = "# QA\n\n" + ras.REVIEW_PROTOCOL_MARKER_BEGIN + "\ntruncated\n"
            target.write_text(original, encoding="utf-8")

            written = ras.reconcile_review_protocol_surfaces(repo_root)
            self.assertNotIn("docs/agents/qa-reviewer.md", written)
            self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_parent_symlink_escape_is_refused_without_touching_external_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir)
            repo_root = outer / "repo"
            outside = outer / "outside"
            (repo_root / "docs").mkdir(parents=True)
            outside.mkdir()
            sentinel = outside / "qa-reviewer.md"
            sentinel.write_text("external sentinel\n", encoding="utf-8")
            (repo_root / "docs" / "agents").symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(RuntimeError, "escapes the repository root"):
                ras.reconcile_review_protocol_surfaces(repo_root)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "external sentinel\n")

    def test_only_registered_enabled_native_role_wrappers_are_reconciled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            registered = repo_root / ".claude" / "agents" / "code-reviewer.md"
            unregistered = repo_root / ".claude" / "agents" / "project-custom.md"
            codex = repo_root / ".codex" / "skills" / "agent-role-code-reviewer" / "SKILL.md"
            for path in (registered, unregistered, codex):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# {path.stem}\n\nproject extension\n", encoding="utf-8")

            manifest = ras.review_protocol_carrier_manifest(repo_root)
            self.assertIn(".claude/agents/code-reviewer.md", manifest)
            self.assertIn(".codex/skills/agent-role-code-reviewer/SKILL.md", manifest)
            self.assertNotIn(".claude/agents/project-custom.md", manifest)

            written = ras.reconcile_review_protocol_surfaces(repo_root)
            self.assertIn(".claude/agents/code-reviewer.md", written)
            self.assertIn(".codex/skills/agent-role-code-reviewer/SKILL.md", written)
            self.assertNotIn(".claude/agents/project-custom.md", written)
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, registered.read_text(encoding="utf-8"))
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, codex.read_text(encoding="utf-8"))
            self.assertIn("Independent-reference verification", registered.read_text(encoding="utf-8"))
            self.assertIn("Independent-reference verification", codex.read_text(encoding="utf-8"))
            self.assertNotIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, unregistered.read_text(encoding="utf-8"))

    def test_self_host_enabled_manifest_has_exactly_one_owned_region(self) -> None:
        repo_root = TESTS_ROOT.parents[3]
        manifest = ras.review_protocol_carrier_manifest(repo_root)
        self.assertIn(".claude/agents/guru.md", manifest)
        self.assertIn(".codex/skills/auto-guru/SKILL.md", manifest)
        for rel in manifest:
            path = repo_root / rel
            if not path.is_file():
                # Conditional repo-local/native carriers are enabled by presence.
                continue
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count(ras.REVIEW_PROTOCOL_MARKER_BEGIN), 1, rel)
            self.assertEqual(text.count(ras.REVIEW_PROTOCOL_MARKER_END), 1, rel)


class RenderAgentSurfacesTests(unittest.TestCase):
    def test_public_agent_render_refuses_dangling_native_wrapper_symlink_escapes(self) -> None:
        for shape in ("final", "parent"):
            with self.subTest(shape=shape), tempfile.TemporaryDirectory() as temp_dir:
                outer = Path(temp_dir)
                repo_root = outer / "repo"
                outside = outer / "outside"
                (repo_root / "docs" / "agents").mkdir(parents=True)
                (repo_root / "docs" / "agents" / "guru.md").write_text(
                    GURU_STUB, encoding="utf-8"
                )
                skill = repo_root / ".codex" / "skills" / "auto-guru" / "SKILL.md"
                skill.parent.mkdir(parents=True)
                if shape == "final":
                    outside.mkdir()
                    skill.symlink_to(outside / "created.md")
                    escaped = outside / "created.md"
                else:
                    skill.parent.rmdir()
                    outside.mkdir()
                    skill.parent.symlink_to(outside, target_is_directory=True)
                    escaped = outside / "SKILL.md"

                result = subprocess.run(
                    ["python3", str(RENDER_SCRIPT), "--repo-root", str(repo_root)],
                    cwd=SCRIPTS_ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("escapes the repository root", result.stderr)
                self.assertFalse(escaped.exists())

    def test_public_platform_render_refuses_final_carrier_symlink_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outer = Path(temp_dir)
            repo_root = outer / "repo"
            outside = outer / "outside.md"
            target = repo_root / "docs" / "agents" / "qa-reviewer.md"
            target.parent.mkdir(parents=True)
            outside.write_text("external sentinel\n", encoding="utf-8")
            target.symlink_to(outside)

            result = subprocess.run(
                ["python3", str(PLATFORM_RENDER_SCRIPT), "--repo-root", str(repo_root)],
                cwd=SCRIPTS_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("escapes the repository root", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(outside.read_text(encoding="utf-8"), "external sentinel\n")

    def test_missing_guru_stays_disabled_while_required_review_carriers_are_created(self) -> None:
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
            self.assertTrue((repo_root / "docs" / "agents" / "qa-reviewer.md").is_file())
            self.assertTrue((repo_root / "docs" / "prompts" / "review-wave.prompt.md").is_file())
            self.assertFalse((repo_root / "docs" / "agents" / "guru.md").exists())
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
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, claude_agent.read_text(encoding="utf-8"))

            codex_skill = repo_root / ".codex" / "skills" / "auto-guru" / "SKILL.md"
            self.assertTrue(codex_skill.is_file())
            self.assertIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, codex_skill.read_text(encoding="utf-8"))

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


class CodexConfigOverwriteSafetyTests(unittest.TestCase):
    """Wave 1p9pe (1p9p7-bug renderer-overwrite-safety): the `.codex/config.toml`
    write must upsert only the framework-managed marker region and preserve all
    operator-authored TOML byte-for-byte. Pre-fix, `write_text(codex_mcp_config,
    CODEX_MCP_CONFIG_TOML)` clobbered the file on every render — this deleted a
    committed operator `wave_close` approval guardrail twice (waves 1p9j0/1p9qm).
    """

    OPERATOR_BLOCK = (
        "[mcp_servers.wavefoundry.tools.wave_close]\n"
        'approval_mode = "approve"\n'
    )

    # This repo's exact pre-migration on-disk shape (AC-7): the unmarked
    # framework table at lines 1-3 plus the restored operator block at 5-6.
    THIS_REPO_PREMIGRATION_SHAPE = (
        "[mcp_servers.wavefoundry]\n"
        'command = "python3"\n'
        'args = [".wavefoundry/framework/scripts/server.py"]\n'
        "\n"
        "[mcp_servers.wavefoundry.tools.wave_close]\n"
        'approval_mode = "approve"\n'
    )

    def _make_repo(self, repo_root: Path) -> None:
        (repo_root / "docs" / "agents").mkdir(parents=True)
        (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")

    def _config_path(self, repo_root: Path) -> Path:
        return repo_root / ".codex" / "config.toml"

    def _parse(self, text: str) -> dict:
        import tomllib

        return tomllib.loads(text)

    def test_create_if_missing_renders_marked_framework_region(self) -> None:
        # AC-3: a fresh repo with no .codex/config.toml gets the file created
        # containing the framework-managed region, and it parses as TOML.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._make_repo(repo_root)
            ras.render_agent_surfaces(repo_root)
            text = self._config_path(repo_root).read_text(encoding="utf-8")
            self.assertIn(ras.CODEX_CONFIG_MARKER_BEGIN, text)
            self.assertIn(ras.CODEX_CONFIG_MARKER_END, text)
            parsed = self._parse(text)
            self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")
            self.assertEqual(
                parsed["mcp_servers"]["wavefoundry"]["args"],
                [".wavefoundry/framework/scripts/server.py"],
            )

    def test_rerender_preserves_operator_block_byte_for_byte(self) -> None:
        # AC-1: an operator-added block outside the marker region survives a
        # re-render byte-for-byte while the framework region stays current.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._make_repo(repo_root)
            ras.render_agent_surfaces(repo_root)
            config = self._config_path(repo_root)
            seeded = config.read_text(encoding="utf-8") + "\n" + self.OPERATOR_BLOCK
            config.write_text(seeded, encoding="utf-8")

            ras.render_agent_surfaces(repo_root)

            text = config.read_text(encoding="utf-8")
            self.assertIn(self.OPERATOR_BLOCK, text, "operator block must survive re-render")
            self.assertIn(ras.CODEX_CONFIG_MARKER_BEGIN, text)
            parsed = self._parse(text)
            self.assertEqual(
                parsed["mcp_servers"]["wavefoundry"]["tools"]["wave_close"]["approval_mode"],
                "approve",
            )
            self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")

    def test_double_render_is_idempotent(self) -> None:
        # AC-2: two consecutive renders produce identical bytes — with and
        # without operator content present.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._make_repo(repo_root)
            config = self._config_path(repo_root)

            ras.render_agent_surfaces(repo_root)
            first = config.read_bytes()
            ras.render_agent_surfaces(repo_root)
            self.assertEqual(first, config.read_bytes(), "fresh double-render must be byte-identical")

            config.write_text(
                config.read_text(encoding="utf-8") + "\n" + self.OPERATOR_BLOCK,
                encoding="utf-8",
            )
            ras.render_agent_surfaces(repo_root)
            second = config.read_bytes()
            ras.render_agent_surfaces(repo_root)
            self.assertEqual(second, config.read_bytes(), "double-render with operator content must be byte-identical")

    def test_stale_framework_region_is_refreshed(self) -> None:
        # Requirement 1: the framework-managed command/args are kept CURRENT —
        # a stale marked region is rewritten to the canonical template.
        stale = (
            f"{ras.CODEX_CONFIG_MARKER_BEGIN}\n"
            "[mcp_servers.wavefoundry]\n"
            'command = "python-old"\n'
            'args = ["old/server.py"]\n'
            f"{ras.CODEX_CONFIG_MARKER_END}\n"
            "\n" + self.OPERATOR_BLOCK
        )
        result = ras.upsert_codex_mcp_config(stale)
        self.assertNotIn("python-old", result)
        self.assertIn('command = "python3"', result)
        self.assertIn(self.OPERATOR_BLOCK, result)

    def test_absorbs_unmarked_framework_table_this_repos_shape(self) -> None:
        # AC-7: migration absorption + TOML validity, seeded with this repo's
        # exact pre-migration on-disk shape. The first marked render must
        # absorb the unmarked framework table into the managed region (never
        # duplicate it) and the result must parse as valid TOML.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._make_repo(repo_root)
            config = self._config_path(repo_root)
            config.parent.mkdir(parents=True)
            config.write_text(self.THIS_REPO_PREMIGRATION_SHAPE, encoding="utf-8")

            ras.render_agent_surfaces(repo_root)

            text = config.read_text(encoding="utf-8")
            header_lines = [
                line for line in text.splitlines() if line.strip() == "[mcp_servers.wavefoundry]"
            ]
            self.assertEqual(
                len(header_lines), 1,
                "the unmarked framework table must be ABSORBED, not duplicated",
            )
            self.assertIn(ras.CODEX_CONFIG_MARKER_BEGIN, text)
            self.assertIn(self.OPERATOR_BLOCK, text, "operator block must survive migration byte-for-byte")
            parsed = self._parse(text)  # tomllib round-trip: raises on duplicate tables
            self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")
            self.assertEqual(
                parsed["mcp_servers"]["wavefoundry"]["tools"]["wave_close"]["approval_mode"],
                "approve",
            )

            # The migration is one-time: the next render is byte-identical.
            migrated = config.read_bytes()
            ras.render_agent_surfaces(repo_root)
            self.assertEqual(migrated, config.read_bytes())

    def test_unrelated_operator_server_table_survives(self) -> None:
        # Requirement 1: unrelated [mcp_servers.*] tables are operator content.
        operator_table = '[mcp_servers.other]\ncommand = "deno"\n'
        result = ras.upsert_codex_mcp_config(
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
            "\n" + operator_table
        )
        self.assertIn(operator_table, result)
        parsed = self._parse(result)
        self.assertEqual(parsed["mcp_servers"]["other"]["command"], "deno")
        self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")

    def test_operator_key_inside_framework_table_survives_migration(self) -> None:
        # An operator-added key trailing the framework command/args stays in
        # the [mcp_servers.wavefoundry] table (markers are TOML comments).
        result = ras.upsert_codex_mcp_config(
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
            "startup_timeout_ms = 20000\n"
        )
        parsed = self._parse(result)
        self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["startup_timeout_ms"], 20000)
        self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")

    def test_unparseable_merge_leaves_existing_untouched(self) -> None:
        # Fail-safe: if absorption would produce invalid TOML (here: a shape
        # the absorber cannot merge without duplicating `command`), the
        # existing operator config is returned unchanged rather than corrupted.
        odd_shape = (
            "[mcp_servers.wavefoundry]\n"
            "# operator comment blocks absorption of the lines below\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
        )
        self.assertEqual(ras.upsert_codex_mcp_config(odd_shape), odd_shape)


class CodexConfigUpsertHardeningTests(unittest.TestCase):
    """Wave 1p9pe review-fix lane: `upsert_codex_mcp_config` hardening.

    Convergent findings from the red-team/code/architecture/security review
    streams: (a) single-exit tomllib validation — every mutating branch's
    candidate is parse-validated, and any failure returns the existing content
    unchanged; (b) the unmarked-table migration accepts TOML-equivalent header
    spellings (quoted keys, whitespace) so they migrate instead of duplicating;
    (c) a bracket-count desync from an unbalanced bracket inside a string
    fail-safes instead of silently absorbing operator content to EOF (the one
    corruption tomllib validation cannot catch, because the result parses);
    (d) fail-safe is loud — stderr warning naming the file — and the path is
    NOT reported in `written`.
    """

    OPERATOR_BLOCK = (
        "[mcp_servers.wavefoundry.tools.wave_close]\n"
        'approval_mode = "approve"\n'
    )

    def _parse(self, text: str) -> dict:
        import tomllib

        return tomllib.loads(text)

    def _upsert(self, existing: str) -> tuple[str, list[str]]:
        reasons: list[str] = []
        result = ras.upsert_codex_mcp_config(existing, on_fail_safe=reasons.append)
        return result, reasons

    def test_quoted_header_spelling_migrates_not_duplicates(self) -> None:
        # Pre-fix the quoted spelling missed the exact-match header scan and
        # fell to the append branch, WRITING a duplicate-table file tomllib
        # rejects. It must migrate exactly like the plain spelling.
        existing = (
            '[mcp_servers."wavefoundry"]\n'
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
            "\n" + self.OPERATOR_BLOCK
        )
        result, reasons = self._upsert(existing)
        self.assertEqual(reasons, [], "quoted header must migrate, not fail-safe")
        headers = [
            line for line in result.splitlines()
            if line.strip().startswith("[") and "wavefoundry]" in line.replace('"', "").replace(" ", "")
        ]
        self.assertEqual(
            [h for h in headers if "tools" not in h],
            ["[mcp_servers.wavefoundry]"],
            "exactly one (canonical) framework table header after migration",
        )
        self.assertIn(ras.CODEX_CONFIG_MARKER_BEGIN, result)
        self.assertIn(self.OPERATOR_BLOCK, result)
        parsed = self._parse(result)  # raises on a duplicate table
        self.assertEqual(parsed["mcp_servers"]["wavefoundry"]["command"], "python3")

    def test_whitespace_header_variant_migrates(self) -> None:
        existing = (
            "[ mcp_servers.wavefoundry ]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
        )
        result, reasons = self._upsert(existing)
        self.assertEqual(reasons, [])
        self.assertIn(ras.CODEX_CONFIG_MARKER_BEGIN, result)
        self.assertNotIn("[ mcp_servers.wavefoundry ]", result)
        self._parse(result)

    def test_dotted_key_form_fails_safe_not_corrupt(self) -> None:
        # Dotted-key assignments define the table without a header line; the
        # append branch would re-declare it (invalid TOML). Must fail-safe.
        existing = (
            'mcp_servers.wavefoundry.command = "python3"\n'
            'mcp_servers.wavefoundry.args = ["x"]\n'
        )
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "dotted-key config must be left untouched")
        self.assertEqual(len(reasons), 1)
        self._parse(result)  # still the operator's valid file

    def test_marker_text_inside_operator_string_fails_safe(self) -> None:
        # Marker text embedded in an operator string value must not select the
        # region-replace branch (pre-fix the substring check sliced through
        # the string). The valid file is left untouched.
        existing = (
            "[mcp_servers.other]\n"
            f'note = "{ras.CODEX_CONFIG_MARKER_BEGIN} and {ras.CODEX_CONFIG_MARKER_END}"\n'
            'command = "deno"\n'
        )
        self._parse(existing)  # precondition: the operator file is valid
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "file with marker text in a string must be untouched")
        self.assertEqual(len(reasons), 1)

    def test_unbalanced_bracket_in_string_operator_subtable_survives(self) -> None:
        # The one silent-loss shape: an unbalanced "[" inside a string desyncs
        # the bracket counter, and pre-fix the absorber ate everything to EOF
        # — dropping the operator subtable while producing VALID TOML (so the
        # tomllib guard alone cannot catch it). Must fail-safe instead.
        existing = (
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py", "--flag["]\n'
            "\n" + self.OPERATOR_BLOCK
        )
        self._parse(existing)  # precondition: valid operator file
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "desynced absorption must fail-safe, not eat to EOF")
        self.assertIn(self.OPERATOR_BLOCK, result, "operator subtable must survive")
        self.assertEqual(len(reasons), 1)
        self.assertIn("bracket", reasons[0])

    def test_oversized_value_continuation_fails_safe(self) -> None:
        # The continuation-line cap: a value run longer than the small
        # constant is treated as a desync even if brackets eventually balance.
        filler = "".join(f'"pad-{i}",\n' for i in range(ras._CODEX_ABSORB_MAX_VALUE_LINES + 2))
        existing = (
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            "args = [\n" + filler + "]\n"
        )
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing)
        self.assertEqual(len(reasons), 1)
        self.assertIn("continuation", reasons[0])

    def test_marked_region_replace_ignores_marker_text_in_string(self) -> None:
        # A real marked region plus an operator string that ALSO contains
        # marker text: the line-anchored match must replace only the real
        # region and preserve the operator string byte-for-byte.
        fresh = ras.upsert_codex_mcp_config(None)
        operator_tail = (
            "\n[mcp_servers.other]\n"
            f'note = "{ras.CODEX_CONFIG_MARKER_END}"\n'
        )
        existing = fresh + operator_tail
        result, reasons = self._upsert(existing)
        self.assertEqual(reasons, [])
        self.assertEqual(result, existing, "re-render must be idempotent and keep the string")
        self._parse(result)

    def test_fail_safe_render_warns_and_omits_written(self) -> None:
        # End-to-end (fix d): a fail-safe merge during render_agent_surfaces
        # emits a stderr warning naming the file and does NOT report the path
        # in the returned written list; the file bytes are untouched.
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "docs" / "agents").mkdir(parents=True)
            (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
            config = repo_root / ".codex" / "config.toml"
            config.parent.mkdir(parents=True)
            fail_safe_shape = (
                'mcp_servers.wavefoundry.command = "python3"\n'
                'mcp_servers.wavefoundry.args = ["x"]\n'
            )
            config.write_text(fail_safe_shape, encoding="utf-8")

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                written = ras.render_agent_surfaces(repo_root)

            self.assertNotIn(
                ".codex/config.toml", written,
                "a fail-safe (unchanged) file must not be reported as written",
            )
            warning = stderr.getvalue()
            self.assertIn("config.toml", warning, "fail-safe must warn loudly on stderr")
            self.assertIn("fail-safe", warning)
            self.assertEqual(
                config.read_text(encoding="utf-8"), fail_safe_shape,
                "the operator file must be byte-for-byte untouched",
            )

    def test_successful_render_still_reports_config_written(self) -> None:
        # Guard the inverse: the normal path still reports the path.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "docs" / "agents").mkdir(parents=True)
            (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
            written = ras.render_agent_surfaces(repo_root)
            self.assertIn(".codex/config.toml", written)


class CodexConfigCouncilFixNowTests(unittest.TestCase):
    """Wave 1p9pe delivery-council fix-now lane: `upsert_codex_mcp_config`.

    (1) Security seat S-NEW-1: a triple-quoted (multiline) operator string
    whose body reproduces BOTH marker comment lines as whole physical lines
    matched the line-anchored region regex; the replace branch sliced the
    string, silently dropped operator content, and the sliced result still
    parsed — the tomllib guard was blind. Empirically proven pre-fix.
    (2) QA seat: the marker-replace branch's own tomllib exit was untested.
    (3) Rotating seat: semantic tomllib-equivalence exit guard — after
    normalizing framework-owned differences, existing and candidate parsed
    docs must be EQUAL, structurally closing valid-TOML content-loss shapes
    (e.g. a balanced-bracket absorption desync) the parse check cannot flag.
    (4) Rotating seat: CRLF-rewritten marker regions now match (region
    refresh) instead of perpetually fail-safing with a stale block.
    """

    OPERATOR_BLOCK = (
        "[mcp_servers.wavefoundry.tools.wave_close]\n"
        'approval_mode = "approve"\n'
    )

    def _upsert(self, existing: str) -> tuple[str, list[str]]:
        reasons: list[str] = []
        result = ras.upsert_codex_mcp_config(existing, on_fail_safe=reasons.append)
        return result, reasons

    def _parse(self, text: str) -> dict:
        import tomllib

        return tomllib.loads(text)

    def test_multiline_string_reproducing_both_marker_lines_fails_safe(self) -> None:
        # S-NEW-1 probe B: triple-quoted operator string containing both
        # marker lines as whole physical lines + a real unmarked framework
        # table below. Pre-fix: the region replace sliced the string, dropped
        # the operator's blob content (including `command = "evil"`), and the
        # result STILL PARSED. Must fail-safe with the string-embedding reason.
        existing = (
            "[mcp_servers.other]\n"
            'blob = """\n'
            f"{ras.CODEX_CONFIG_MARKER_BEGIN}\n"
            'command = "evil"\n'
            f"{ras.CODEX_CONFIG_MARKER_END}\n"
            '"""\n'
            "\n"
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
        )
        self._parse(existing)  # precondition: the operator file is valid TOML
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "string-embedded marker lines must fail-safe untouched")
        self.assertEqual(len(reasons), 1)
        self.assertIn("multiline operator string", reasons[0])

    def test_single_line_marker_string_with_real_region_still_upserts(self) -> None:
        # No-false-positive guard: this repo's on-disk shape (marked region +
        # operator tools subtable) plus an operator SINGLE-LINE string that
        # mentions one marker line. Single-line strings cannot line-anchor the
        # region regex, so the normal replace path must run: the stale region
        # is refreshed and every operator byte outside it survives.
        operator_tail = (
            "\n" + self.OPERATOR_BLOCK
            + "\n[mcp_servers.other]\n"
            f'note = "{ras.CODEX_CONFIG_MARKER_END}"\n'
        )
        existing = (
            f"{ras.CODEX_CONFIG_MARKER_BEGIN}\n"
            "[mcp_servers.wavefoundry]\n"
            'command = "python-old"\n'
            'args = ["old/server.py"]\n'
            f"{ras.CODEX_CONFIG_MARKER_END}\n"
            + operator_tail
        )
        result, reasons = self._upsert(existing)
        self.assertEqual(reasons, [], "single-line marker mention must not fail-safe")
        self.assertNotIn("python-old", result, "stale framework region must be refreshed")
        self.assertIn('command = "python3"', result)
        self.assertIn(operator_tail, result, "operator content incl. the marker string survives")
        self._parse(result)

    def test_region_replace_duplicate_operator_table_hits_tomllib_exit(self) -> None:
        # QA seat: the marker-REPLACE branch flowing into the tomllib single
        # exit was untested. A well-formed marked region plus an operator-owned
        # duplicate [mcp_servers.wavefoundry] table outside it: the existing
        # content already does not parse (duplicate table), so the parsed-
        # baseline guards are skipped and the region replace runs; the
        # candidate is still duplicate-table TOML, so the tomllib exit must
        # fail-safe with the existing content unchanged. No marker text in any
        # string value — this shape exercises the parse exit specifically.
        existing = (
            f"{ras.CODEX_CONFIG_MARKER_BEGIN}\n"
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = [".wavefoundry/framework/scripts/server.py"]\n'
            f"{ras.CODEX_CONFIG_MARKER_END}\n"
            "\n"
            "[mcp_servers.wavefoundry]\n"
            "startup_timeout_ms = 20000\n"
        )
        with self.assertRaises(Exception):
            self._parse(existing)  # precondition: duplicate table, unparseable
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "unparseable replace result must leave existing untouched")
        self.assertEqual(len(reasons), 1)
        self.assertIn("parse", reasons[0])

    def test_balanced_bracket_desync_caught_by_semantic_equivalence_guard(self) -> None:
        # Rotating seat: brackets inside string values can desync the
        # absorption counter and RETURN TO ZERO, evading both the depth
        # fail-safe and the continuation cap — pre-fix the absorber ate the
        # operator table to EOF and the result parsed cleanly. Only the
        # semantic-equivalence exit guard catches this shape.
        existing = (
            "[mcp_servers.wavefoundry]\n"
            'command = "python3"\n'
            'args = ["x", "--open[["]\n'
            "\n"
            "[mcp_servers.other]\n"
            'key = "]]close"\n'
        )
        self._parse(existing)  # precondition: valid operator file
        result, reasons = self._upsert(existing)
        self.assertEqual(result, existing, "balanced-bracket desync must fail-safe, not eat to EOF")
        self.assertIn("[mcp_servers.other]", result, "operator table must survive")
        self.assertEqual(len(reasons), 1)
        self.assertIn("operator-owned parsed content", reasons[0])

    def test_normalized_doc_equivalence_tolerances(self) -> None:
        # Unit coverage of the equivalence helper: framework-owned differences
        # (command/args refresh; wavefoundry-table creation) are tolerated;
        # any operator-owned difference is not.
        norm = ras._codex_normalized_doc
        base = {"mcp_servers": {"wavefoundry": {"command": "python-old", "args": ["old"]}}}
        refreshed = {"mcp_servers": {"wavefoundry": {"command": "python3", "args": ["new"]}}}
        self.assertEqual(norm(base), norm(refreshed), "command/args refresh must be equivalent")

        self.assertEqual(
            norm({}), norm(refreshed),
            "creating the wavefoundry table (and mcp_servers parent) must be equivalent",
        )
        with_other = {"mcp_servers": {"other": {"command": "deno"}}}
        with_other_and_fw = {
            "mcp_servers": {"other": {"command": "deno"}, "wavefoundry": {"command": "python3"}}
        }
        self.assertEqual(norm(with_other), norm(with_other_and_fw))

        operator_changed = {"mcp_servers": {"other": {"command": "node"}, "wavefoundry": {"command": "python3"}}}
        self.assertNotEqual(
            norm(with_other_and_fw), norm(operator_changed),
            "an operator key change must NOT be equivalent",
        )

        with_subtable = {
            "mcp_servers": {"wavefoundry": {"command": "python3", "tools": {"wave_close": {"approval_mode": "approve"}}}}
        }
        dropped_subtable = {"mcp_servers": {"wavefoundry": {"command": "python3"}}}
        self.assertNotEqual(
            norm(with_subtable), norm(dropped_subtable),
            "dropping an operator subtable must NOT be equivalent",
        )

    def test_crlf_marker_region_is_replaced_not_fail_safed(self) -> None:
        # Rotating seat: a CRLF-rewritten config (editor/tooling re-encoded)
        # must still match its marker region — region refreshed, operator CRLF
        # content outside the region preserved byte-for-byte — instead of
        # perpetually fail-safing with a stale framework block.
        stale_region = (
            f"{ras.CODEX_CONFIG_MARKER_BEGIN}\n"
            "[mcp_servers.wavefoundry]\n"
            'command = "python-old"\n'
            'args = ["old/server.py"]\n'
            f"{ras.CODEX_CONFIG_MARKER_END}\n"
        )
        operator_tail = '\n[mcp_servers.other]\ncommand = "deno"\n'
        existing = (stale_region + operator_tail).replace("\n", "\r\n")
        result, reasons = self._upsert(existing)
        self.assertEqual(reasons, [], "CRLF marker region must be matched, not fail-safed")
        self.assertNotIn("python-old", result, "stale framework region must be refreshed")
        self.assertIn(
            operator_tail.replace("\n", "\r\n"), result,
            "operator CRLF content outside the region survives byte-for-byte",
        )
        self._parse(result)


class GuruWrapperToolAllowlistTests(unittest.TestCase):
    """Subagent MCP tool access — the rendered guru wrapper's frontmatter
    `tools:` allowlist must grant the read-only Wavefoundry retrieval tools its
    own body instructs it to use. An explicit allowlist is not additive in
    Claude Code, so omitting the MCP tools makes the wrapper self-contradictory
    (body says "call code_ask", frontmatter forbids it). Guards:
      1. the enumerated read-only retrieval grant (incl. ToolSearch for hosts
         that defer MCP schemas),
      2. no write-capable / lifecycle-mutating wave_* tool ever granted,
      3. frontmatter grants cover every MCP tool the wrapper body names.
    """

    # The read-only retrieval set the wrapper must grant. Exact tool names are
    # the fail-safe frontmatter form: honored -> precise read-only grant;
    # ignored by a host -> status quo (never a mutator exposure).
    _REQUIRED_GRANTS = {
        "ToolSearch",
        "mcp__wavefoundry__code_ask",
        "mcp__wavefoundry__code_search",
        "mcp__wavefoundry__code_keyword",
        "mcp__wavefoundry__code_read",
        "mcp__wavefoundry__code_outline",
        "mcp__wavefoundry__code_definition",
        "mcp__wavefoundry__code_references",
        "mcp__wavefoundry__code_callhierarchy",
        "mcp__wavefoundry__code_dependencies",
        "mcp__wavefoundry__code_impact",
        "mcp__wavefoundry__code_list_files",
        "mcp__wavefoundry__code_constants",
        "mcp__wavefoundry__code_pattern",
        "mcp__wavefoundry__code_callgraph",
        "mcp__wavefoundry__code_graph_path",
        "mcp__wavefoundry__code_graph_community",
        "mcp__wavefoundry__docs_search",
        "mcp__wavefoundry__seed_get",
    }

    def _rendered_guru(self) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "docs" / "agents").mkdir(parents=True)
            (repo_root / "docs" / "agents" / "guru.md").write_text(GURU_STUB, encoding="utf-8")
            (repo_root / ".claude" / "agents").mkdir(parents=True)
            ras.render_agent_surfaces(repo_root)
            return (repo_root / ".claude" / "agents" / "guru.md").read_text(encoding="utf-8")

    @staticmethod
    def _tools_entries(rendered: str) -> list[str]:
        for line in rendered.splitlines():
            if line.startswith("tools:"):
                return [entry.strip() for entry in line[len("tools:"):].split(",") if entry.strip()]
        return []

    def test_required_readonly_grants_present(self) -> None:
        entries = set(self._tools_entries(self._rendered_guru()))
        missing = self._REQUIRED_GRANTS - entries
        self.assertFalse(
            missing,
            f"guru wrapper tools: allowlist is missing required read-only grants: {sorted(missing)}",
        )
        # The pre-fix baseline tools stay granted.
        for base in ("Read", "Grep", "Glob", "Bash"):
            self.assertIn(base, entries)

    def test_no_mutating_wave_tool_granted(self) -> None:
        entries = self._tools_entries(self._rendered_guru())
        offenders = [e for e in entries if e.startswith("mcp__wavefoundry__wave_")]
        self.assertEqual(
            offenders, [],
            "guru wrapper must never grant wave_* lifecycle/mutating tools",
        )
        # And never a bare server-level grant, which would include the mutators.
        self.assertNotIn("mcp__wavefoundry", entries)
        self.assertNotIn("mcp__wavefoundry__*", entries)

    def test_body_instructions_covered_by_grants(self) -> None:
        rendered = self._rendered_guru()
        entries = set(self._tools_entries(rendered))
        body = rendered.split("---", 2)[2] if rendered.count("---") >= 2 else rendered
        body_named = set(re.findall(r"`((?:code|docs)_[a-z_]+|seed_get|wave_[a-z_]+)`", body))
        body_named |= set(re.findall(r"`mcp__wavefoundry__([a-z_]+)`", body))
        self.assertTrue(body_named, "wrapper body should name its MCP tools")
        uncovered = {
            name for name in body_named
            if f"mcp__wavefoundry__{name}" not in entries
        }
        self.assertFalse(
            uncovered,
            "wrapper body instructs tools its frontmatter does not grant "
            f"(the self-contradiction this change fixes): {sorted(uncovered)}",
        )


class FreshCarrierAgentFrontmatterTests(unittest.TestCase):
    """Regression: fresh docs/agents/** carriers must satisfy the pack's own docs-lint.

    A 1.13.0 upgrade halted at the docs gate because newly-rendered specialist
    carriers lacked the `Role:`/`Category:` frontmatter the agent-metadata validator
    requires. These tests render carriers into a temp root that EXPOSES the real
    seeds (so rendering takes the seed-verbatim path, not the frontmatter-less
    title-minimum branch that would make the test vacuous) and assert the agent
    validators pass over the whole rendered `docs/agents/**` set.
    """

    def _render_fresh_root(self, repo_root: Path) -> None:
        import shutil

        seeds_dst = repo_root / ".wavefoundry" / "framework" / "seeds"
        seeds_dst.parent.mkdir(parents=True)
        shutil.copytree(PROJECT_ROOT / "framework" / "seeds", seeds_dst)
        ras.reconcile_review_protocol_surfaces(repo_root)

    def test_fresh_carriers_pass_the_pack_agent_metadata_validators(self) -> None:
        from wave_lint_lib.wave_validators import (
            _check_agent_category_metadata,
            _check_agent_role_metadata,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            self._render_fresh_root(repo_root)

            # The exact checks that blocked the upgrade — over the whole rendered set.
            self.assertEqual(_check_agent_role_metadata(repo_root), [])
            self.assertEqual(_check_agent_category_metadata(repo_root), [])

            specialists = repo_root / "docs" / "agents" / "specialists"

            # Requirement 1 (seed frontmatter): a single-destination specialist renders
            # seed-verbatim (proving the seeds dir was actually consulted) with Role/Category.
            red_team = (specialists / "red-team.md").read_text(encoding="utf-8")
            self.assertIn("# Agent Body — Red Team", red_team)  # seed body, not title-minimum
            self.assertIn("Role: red-team", red_team)
            self.assertIn("Category: specialist", red_team)

            # Requirement 2 (renderer fallback): seed 236 carries NO seed frontmatter, so
            # its specialist render gets Role/Category from the fallback — and its exempt
            # docs/prompts render must NOT be polluted with them.
            archetype = (specialists / "archetype-council.md").read_text(encoding="utf-8")
            self.assertIn("Role: archetype-council", archetype)
            self.assertIn("Category: specialist", archetype)
            prompt = (repo_root / "docs" / "prompts" / "archetype-council.prompt.md").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("Role: archetype-council", prompt)
            self.assertNotIn("Category: specialist", prompt)

            # Non-specialist derivation: a review-category carrier must get Category: review,
            # not specialist — this is why the fallback reuses _expected_agent_category.
            qa = (repo_root / "docs" / "agents" / "qa-reviewer.md").read_text(encoding="utf-8")
            self.assertIn("Role: qa-reviewer", qa)
            self.assertIn("Category: review", qa)

    def test_fallback_is_fresh_only_and_does_not_clobber_existing_frontmatter(self) -> None:
        # An existing (update-path) specialist doc with project-authored frontmatter must
        # be preserved verbatim outside the owned region — the fallback runs fresh-only.
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            target = repo_root / "docs" / "agents" / "specialists" / "red-team.md"
            target.parent.mkdir(parents=True)
            existing = "# Red Team\n\nRole: red-team\nCategory: specialist\n\n## Project note\n\n- keep me\n"
            target.write_text(existing, encoding="utf-8")

            ras.reconcile_review_protocol_surfaces(repo_root)

            text = target.read_text(encoding="utf-8")
            self.assertIn("## Project note", text)
            self.assertIn("- keep me", text)
            # Exactly one Role:/Category: each — no duplicate injection on the update path.
            self.assertEqual(text.count("Role: red-team"), 1)
            self.assertEqual(text.count("Category: specialist"), 1)


if __name__ == "__main__":
    unittest.main()

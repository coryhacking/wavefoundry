from __future__ import annotations

import re
import unittest
from pathlib import Path

# tests/ -> scripts/ -> framework/ -> .wavefoundry/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]

# Shipped framework template -> canonical project copy. Each pair must stay BYTE-IDENTICAL:
# the framework copy is what build_pack carries in the distribution zip and the install/upgrade
# seeds provision into target projects; the project copy is the canonical the self-host uses.
# (1p4dc for install-log-format; 1p455 for scan-findings-format. 1p591 consolidated the shipped
# templates: install-log-format under .wavefoundry/framework/install/ with the other install assets,
# scan-findings-format under .wavefoundry/framework/docs/ — see docs/references/install-assets.md.)
SHIPPED_TEMPLATE_PAIRS = {
    "install-log-format.md": (
        ".wavefoundry/framework/install/install-log-format.md",
        "docs/references/install-log-format.md",
    ),
    "scan-findings-format.md": (
        ".wavefoundry/framework/docs/scan-findings-format.md",
        "docs/references/scan-findings-format.md",
    ),
}


class ShippedReferenceDocParityTests(unittest.TestCase):
    """Wave 1p591: every reference doc shipped as a framework template must stay BYTE-IDENTICAL to
    its canonical project copy. If the two drift, every installed/upgraded target receives a stale
    schema. This guards the shipped-template <-> provisioned-canonical invariant documented in
    ``docs/references/install-assets.md`` — it is NOT accidental duplication."""

    def test_shipped_templates_are_byte_identical_to_canonical(self) -> None:
        for name, (shipped_rel, canonical_rel) in SHIPPED_TEMPLATE_PAIRS.items():
            with self.subTest(doc=name):
                shipped = REPO_ROOT / shipped_rel
                canonical = REPO_ROOT / canonical_rel
                self.assertTrue(shipped.is_file(), f"missing shipped template: {shipped_rel}")
                self.assertTrue(canonical.is_file(), f"missing canonical copy: {canonical_rel}")
                self.assertEqual(
                    shipped.read_bytes(),
                    canonical.read_bytes(),
                    f"{name}: the shipped framework template ({shipped_rel}) has drifted from the "
                    f"canonical copy ({canonical_rel}) — they must stay byte-identical so installed "
                    f"targets receive the current schema (see docs/references/install-assets.md).",
                )

    def test_all_provisioned_format_schemas_are_guarded(self) -> None:
        """Every canonical ``*-format.md`` under ``docs/references/`` is a provisioned schema and must
        have a parity pair — a new one without a guard would silently drift from its shipped template."""
        guarded = set(SHIPPED_TEMPLATE_PAIRS)
        for canonical in sorted((REPO_ROOT / "docs" / "references").glob("*-format.md")):
            with self.subTest(doc=canonical.name):
                self.assertIn(
                    canonical.name, guarded,
                    f"{canonical.name} is a provisioned *-format schema but has no parity pair in "
                    f"SHIPPED_TEMPLATE_PAIRS — add one so its shipped template cannot drift.",
                )


class ScanFindingsFormatReferenceSafetyTests(unittest.TestCase):
    """Wave 1p8o5 #3 / AC-3: seed-213 references `docs/references/scan-findings-format.md`. A consumer
    mirroring the seed must NOT hit a docs-lint broken-link error for that reference. Two independent
    guarantees keep it safe — this guard pins both so a future edit cannot silently break either:

      (a) Self-resolving in the link validator: every repo reference to the doc uses INLINE-CODE form
          (`` `...scan-findings-format.md` ``), which `wave_lint_lib.link_validators.check_markdown_links`
          strips before checking — it only flags `[text](href)` markdown links. So the reference can
          never trigger a broken-link error even if the file is somehow absent.
      (b) Availability: the doc IS provisioned/refreshed into a consumer's `docs/references/` — the
          install seed (012) provisions it from the shipped template and the upgrade seed (160)
          refreshes it from the same template (the byte-parity pair is guarded above)."""

    SEED_213 = ".wavefoundry/framework/seeds/213-security-reviewer.prompt.md"
    SEED_012 = ".wavefoundry/framework/seeds/012-install-wavefoundry-phase-2.prompt.md"
    SEED_160 = ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md"
    SHIPPED_TEMPLATE = ".wavefoundry/framework/docs/scan-findings-format.md"
    CANONICAL = "docs/references/scan-findings-format.md"

    # A markdown link whose href contains scan-findings-format.md — the form the link validator WOULD
    # flag if the target were missing. The reference must NEVER appear in this form.
    _MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\[\]]*\]\([^)]*scan-findings-format\.md[^)]*\)")

    def _read(self, rel: str) -> str:
        path = REPO_ROOT / rel
        self.assertTrue(path.is_file(), f"missing: {rel}")
        return path.read_text(encoding="utf-8")

    def test_seed_213_references_the_doc(self) -> None:
        # Sanity: the reference this guard protects actually exists in seed-213.
        self.assertIn("scan-findings-format.md", self._read(self.SEED_213))

    def test_no_markdown_link_form_anywhere_in_seeds_or_docs(self) -> None:
        # (a) No surface (seed, prompt, doc) may reference the doc as a `[text](href)` markdown link,
        # which the link validator would flag if the file were absent in a consumer. Inline-code only.
        offenders: list[str] = []
        for base in ("docs", ".wavefoundry/framework/seeds", ".wavefoundry/framework/docs"):
            for path in sorted((REPO_ROOT / base).rglob("*.md")):
                rel = path.relative_to(REPO_ROOT).as_posix()
                # Skip the wave/plan history that records this very change's prose.
                if rel.startswith("docs/waves/") or rel.startswith("docs/plans/"):
                    continue
                if self._MARKDOWN_LINK_RE.search(path.read_text(encoding="utf-8")):
                    offenders.append(rel)
        self.assertEqual(
            offenders, [],
            "scan-findings-format.md must be referenced as inline code, never a `[text](href)` "
            "markdown link the docs-lint link validator would flag in a consumer: " + ", ".join(offenders),
        )

    def test_link_validator_does_not_flag_inline_code_reference(self) -> None:
        # (a) Prove the safety mechanism directly: a doc that references the (absent) target via
        # inline code yields ZERO broken-link failures; the same reference as a markdown link DOES fail.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "link_validators", REPO_ROOT / ".wavefoundry" / "framework" / "scripts" / "wave_lint_lib" / "link_validators.py"
        )
        # link_validators imports `.helpers` relatively — load the package context first.
        import sys
        scripts_dir = REPO_ROOT / ".wavefoundry" / "framework" / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from wave_lint_lib import link_validators  # noqa: E402

        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "docs" / "references").mkdir(parents=True)
            # NOTE: scan-findings-format.md intentionally absent in this temp repo.
            inline_doc = root / "docs" / "uses-inline.md"
            inline_doc.write_text(
                "See `docs/references/scan-findings-format.md` for the ledger format.\n",
                encoding="utf-8",
            )
            self.assertEqual(
                link_validators.check_markdown_links(root, inline_doc), [],
                "an inline-code reference must never be link-checked (it is self-resolving)",
            )
            link_doc = root / "docs" / "uses-link.md"
            link_doc.write_text(
                "See [the format](references/scan-findings-format.md).\n", encoding="utf-8"
            )
            self.assertTrue(
                link_validators.check_markdown_links(root, link_doc),
                "control: a markdown link to the absent target MUST flag — proves the guard is real",
            )

    def test_doc_is_provisioned_by_install_and_upgrade_seeds(self) -> None:
        # (b) Availability: the install seed provisions and the upgrade seed refreshes the canonical
        # from the shipped template, so a consumer's docs/references/ carries the file.
        install = self._read(self.SEED_012)
        self.assertIn("docs/references/scan-findings-format.md", install)
        self.assertIn(".wavefoundry/framework/docs/scan-findings-format.md", install)
        upgrade = self._read(self.SEED_160)
        self.assertIn("docs/references/scan-findings-format.md", upgrade)
        self.assertIn(".wavefoundry/framework/docs/scan-findings-format.md", upgrade)
        # And the shipped template (what build_pack carries) exists.
        self.assertTrue((REPO_ROOT / self.SHIPPED_TEMPLATE).is_file())


class UpgradeMcpFirstGuidanceTests(unittest.TestCase):
    """Wave 1p7ww: the upgrade seed AND the rendered prompt must lead with the MCP-first
    `wave_upgrade()` directive while still carrying the labeled no-MCP `wf upgrade` fallback, and
    surface the minor-bump reconciliation callout. Both surfaces are parallel-maintained (the
    docs/prompts copy is the self-hosted surface, not a mechanical render of the seed), so this
    cross-checks they stay in parity on these directives."""

    SEED = ".wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md"
    PROMPT = "docs/prompts/upgrade-wavefoundry.prompt.md"

    def _read(self, rel: str) -> str:
        path = REPO_ROOT / rel
        self.assertTrue(path.is_file(), f"missing: {rel}")
        return path.read_text(encoding="utf-8")

    def test_seed_leads_with_mcp_first_directive(self) -> None:
        text = self._read(self.SEED)
        self.assertIn("MCP-first", text)
        self.assertIn("wave_upgrade()", text)
        self.assertIn("wave_upgrade_status", text)
        # The manual sequence is kept, labeled as the no-MCP CLI fallback (not deleted).
        self.assertIn("no-MCP", text)
        self.assertIn("wf upgrade", text)
        # Wave 1p8kz: the reconciliation callout runs on EVERY upgrade (no longer minor+-gated).
        self.assertIn("Reconciliation on every upgrade", text)

    def test_prompt_leads_with_mcp_first_directive(self) -> None:
        text = self._read(self.PROMPT)
        self.assertIn("MCP-first", text)
        self.assertIn("wave_upgrade()", text)
        self.assertIn("wave_upgrade_status", text)
        self.assertIn("no-MCP", text)
        self.assertIn("wf upgrade", text)
        # Wave 1p8et: the recommend-only prose callout became the actionable "Reconciliation scan".
        self.assertIn("Reconciliation scan", text)

    def test_mcp_first_directive_leads_the_procedure(self) -> None:
        # AC-1: the MCP-first directive must LEAD the manual/CLI-fallback procedure in both surfaces.
        # Anchor on each surface's own "this is the fallback" label so the check is about the directive
        # heading the procedure, not about an incidental earlier `wf upgrade` mention in an overview.
        cases = {
            # In the seed, the relabeled procedure header marks where the fallback begins.
            self.SEED: "Execution flow (no-MCP CLI fallback",
            # In the prompt, the MCP-first lead sits at the top of "## Upgrade Steps", before the
            # versioning-contract / agent-safe-discovery procedure content.
            self.PROMPT: "**Versioning contract:**",
        }
        for rel, fallback_anchor in cases.items():
            with self.subTest(doc=rel):
                text = self._read(rel)
                mcp_pos = text.find("MCP-first")
                fallback_pos = text.find(fallback_anchor)
                self.assertGreater(mcp_pos, -1, f"{rel}: missing the MCP-first directive")
                self.assertGreater(fallback_pos, -1, f"{rel}: missing the fallback anchor {fallback_anchor!r}")
                self.assertLess(
                    mcp_pos, fallback_pos,
                    f"{rel}: the MCP-first directive must lead the manual/CLI-fallback procedure",
                )

    def test_tool_lists_and_spec_name_wave_upgrade_tools(self) -> None:
        # AC-2: AGENTS.md available-tools list + the spec name both upgrade tools.
        agents = self._read("AGENTS.md")
        self.assertIn("`wave_upgrade`", agents)
        self.assertIn("`wave_upgrade_status`", agents)
        spec = self._read("docs/specs/mcp-tool-surface.md")
        self.assertIn("wave_upgrade_status()", spec)


class McpPythonLaunchGuidanceTests(unittest.TestCase):
    """Native Windows field reports showed agents copying a venv Python path into MCP config.

    The shipped guidance must keep MCP launch on the PATH `python3` command and Wavefoundry's
    `server.py`; the server handles tool-venv activation itself.
    """

    def _read(self, rel: str) -> str:
        path = REPO_ROOT / rel
        self.assertTrue(path.is_file(), f"missing: {rel}")
        return path.read_text(encoding="utf-8")

    def test_install_prompt_uses_path_python_not_tool_venv_python(self) -> None:
        text = self._read("docs/prompts/install-wavefoundry.prompt.md")
        self.assertIn('"command": "python3"', text)
        self.assertIn('command = "python3"', text)
        self.assertIn("<repo>/.wavefoundry/framework/scripts/server.py", text)
        self.assertIn("Do not point MCP config at `.wavefoundry/venv/Scripts/python.exe`", text)
        self.assertNotIn('"command": "/Users/coryhacking/.wavefoundry/venv/bin/python"', text)
        self.assertNotIn('command = "/Users/coryhacking/.wavefoundry/venv/bin/python"', text)

    def test_agent_guide_copy_ready_entry_uses_path_python(self) -> None:
        text = self._read("AGENTS.md")
        self.assertIn('"command": "python3"', text)
        self.assertIn("<repo>/.wavefoundry/framework/scripts/server.py", text)
        self.assertIn("do not point MCP config at `.wavefoundry/venv/Scripts/python.exe`", text)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TESTS_ROOT.parent
PROJECT_ROOT = SCRIPTS_ROOT.parents[3]
FIXTURE_ROOT = TESTS_ROOT / "fixtures" / "docs_lint" / "base"
DOCS_LINT_SCRIPT = SCRIPTS_ROOT / "docs_lint.py"


class DocsLintFixtureTests(unittest.TestCase):
    VALID_WAVE_ID = "00057 routine-behavior-contract"
    BASELINE_WAVE_ID = "00000 wave-zero-plans-and-specs"
    VALID_CHANGE_ID = "00058-bug fixture-core"
    FOLLOW_UP_CHANGE_ID = "00059-enh fixture-follow-up"
    WAVE_DOC_PATH = Path("docs/waves/waves/change-2026-03/wave.md")
    PERSONA_DOC_PATH = Path("docs/agents/personas/wave-coordinator.md")

    def copy_fixture(self) -> Path:
        temp_dir = Path(tempfile.mkdtemp(prefix="wave-docs-lint-fixture-"))
        shutil.copytree(FIXTURE_ROOT, temp_dir, dirs_exist_ok=True)
        return temp_dir

    def run_docs_lint(self, root: Path) -> subprocess.CompletedProcess[str]:
        return self.run_docs_lint_with_args(root)

    def run_docs_lint_with_args(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PROJECT_ROOT"] = str(root)
        env["PYTHONPATH"] = str(SCRIPTS_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [os.environ.get("PYTHON", "python3"), str(DOCS_LINT_SCRIPT), *args],
            cwd=PROJECT_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_base_fixture_passes(self) -> None:
        root = self.copy_fixture()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)

    def test_closed_wave_id_requires_date_slug_and_wave_suffix(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8").replace(
                f"wave-id: `{self.VALID_WAVE_ID}`",
                "wave-id: `0100 routine-behavior-contract`",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing stable `wave-id` declaration", result.stderr)

    def test_legacy_baseline_wave_id_is_allowed(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        journal_doc = root / "docs/agents/journals/wave-coordinator.md"
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8").replace(
                f"wave-id: `{self.VALID_WAVE_ID}`",
                f"wave-id: `{self.BASELINE_WAVE_ID}`",
            ),
            encoding="utf-8",
        )
        journal_doc.write_text(
            journal_doc.read_text(encoding="utf-8").replace(
                f"wave-id: `{self.VALID_WAVE_ID}`",
                f"wave-id: `{self.BASELINE_WAVE_ID}`",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)

    def test_wave_id_with_alternative_valid_slug_passes(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        journal_doc = root / "docs/agents/journals/wave-coordinator.md"
        persona_doc = root / self.PERSONA_DOC_PATH
        for doc in (wave_doc, journal_doc, persona_doc):
            doc.write_text(
                doc.read_text(encoding="utf-8").replace(
                    f"wave-id: `{self.VALID_WAVE_ID}`",
                    "wave-id: `0006a docs-lint-hardening`",
                ),
                encoding="utf-8",
            )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)

    def test_legacy_baseline_wave_id_in_journal_and_persona_passes(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        journal_doc = root / "docs/agents/journals/wave-coordinator.md"
        persona_doc = root / self.PERSONA_DOC_PATH
        for doc in (wave_doc, journal_doc, persona_doc):
            doc.write_text(
                doc.read_text(encoding="utf-8").replace(
                f"wave-id: `{self.VALID_WAVE_ID}`",
                f"wave-id: `{self.BASELINE_WAVE_ID}`",
                ),
                encoding="utf-8",
            )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)

    def test_wave_id_rejects_non_crockford_prefix_characters(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8").replace(
                f"wave-id: `{self.VALID_WAVE_ID}`",
                "wave-id: `0O10 routine-behavior-contract wave`",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing stable `wave-id` declaration", result.stderr)

    def test_closed_wave_id_rejects_missing_wave_suffix(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8").replace(
                f"wave-id: `{self.VALID_WAVE_ID}`",
                "wave-id: `2026-03-20 routine-behavior-contract`",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing stable `wave-id` declaration", result.stderr)

    def test_invalid_wave_change_id_fails(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8").replace(
                f"Change ID: `{self.VALID_CHANGE_ID}`",
                "Change ID: `bad fixture id`",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("wave artifact has unstable Change ID `bad fixture id`", result.stderr)

    def test_ac_priority_row_count_mismatch_fails(self) -> None:
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.write_text(
            change_doc.read_text(encoding="utf-8").replace(
                "## Acceptance Criteria\n\n- [x] AC-1: Fixture criterion satisfied.\n",
                "## Acceptance Criteria\n\n- [x] AC-1: Fixture criterion satisfied.\n- [ ] AC-2: Second criterion missing a priority row.\n",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("AC Priority table must have one row per Acceptance Criteria bullet", result.stderr)
        self.assertIn("unknown ACs are not allowed", result.stderr)

    def test_plain_bullet_ac_syntax_fails(self) -> None:
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.write_text(
            change_doc.read_text(encoding="utf-8").replace(
                "## Acceptance Criteria\n\n- [x] AC-1: Fixture criterion satisfied.\n",
                "## Acceptance Criteria\n\n- AC-1: Fixture criterion satisfied.\n",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("uses plain bullet format", result.stderr)
        self.assertIn("checkbox syntax", result.stderr)

    def test_checkbox_ac_syntax_passes(self) -> None:
        root = self.copy_fixture()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0)

    def test_plain_bullet_task_syntax_fails(self) -> None:
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.write_text(
            change_doc.read_text(encoding="utf-8")
            + "\n## Tasks\n\n- Inspect parser behavior.\n- Keep fixtures readable.\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("`## Tasks` uses plain bullet format", result.stderr)
        self.assertIn("checkbox syntax", result.stderr)

    def test_tilde_ac_with_inline_italic_note_passes(self) -> None:
        """Wave 1p31b (1p32k): a `[~]` AC at required priority with an inline italic
        status note must lint clean."""
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.write_text(
            change_doc.read_text(encoding="utf-8").replace(
                "- [x] AC-1: Fixture criterion satisfied.",
                "- [~] AC-1: Mermaid diagram removed entirely per operator direction. *Original draft used a five-subgraph composite; operator subsequently directed removal in favor of prose description. See Decision Log entry on 2026-06-03.*",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")

    def test_tilde_ac_with_long_inline_prose_passes(self) -> None:
        """Wave 1p31b (1p32k): the inline-note requirement is satisfied by 40+ chars of
        prose after the AC label, even without italic markup."""
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.write_text(
            change_doc.read_text(encoding="utf-8").replace(
                "- [x] AC-1: Fixture criterion satisfied.",
                "- [~] AC-1: Mermaid diagram intentionally removed per operator direction on 2026-06-03 — see Decision Log.",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")

    def test_silent_tilde_required_ac_fails(self) -> None:
        """Wave 1p31b (1p32k): a `[~]` AC at required priority with no inline note
        (or only a trivial label) must produce a lint error naming the AC."""
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.write_text(
            change_doc.read_text(encoding="utf-8").replace(
                "- [x] AC-1: Fixture criterion satisfied.",
                "- [~] AC-1: deferred",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("lacks an inline status note", result.stderr)
        self.assertIn("AC-1", result.stderr)

    def test_tilde_on_nonrequired_priority_passes_without_note(self) -> None:
        """Wave 1p31b (1p32k): `[~]` on important / nice-to-have / not-this-scope
        priorities does not require the inline note (mechanical enforcement applies
        only to required-priority ACs)."""
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.write_text(
            change_doc.read_text(encoding="utf-8")
            .replace(
                "- [x] AC-1: Fixture criterion satisfied.",
                "- [~] AC-1: deferred",
            )
            .replace(
                "| AC-1 | required |",
                "| AC-1 | important |",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")

    def test_tilde_task_without_inline_note_passes(self) -> None:
        """Wave 1p31b (1p32k): tasks accept `[~]` without requiring an inline note
        — asymmetric with the AC rule per Req-12. Task `[~]` is for implementation
        hints that were streamlined out; the AC system carries the audit trail."""
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.write_text(
            change_doc.read_text(encoding="utf-8")
            + "\n## Tasks\n\n- [x] Inspect parser behavior.\n- [~] Run the 5,000-row bench fixture\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, msg=f"stderr: {result.stderr}")

    def test_workflow_config_accepts_new_wave_implement_key(self) -> None:
        """Wave 1p337 (1p336) AC-6: docs-lint required-keys check passes with the new
        `wave_implement` key set and the legacy `wave_execution` key absent."""
        root = self.copy_fixture()
        config = root / "docs/workflow-config.json"
        data = json.loads(config.read_text(encoding="utf-8"))
        # Rename wave_execution → wave_implement (the new canonical name).
        data["wave_implement"] = data.pop("wave_execution")
        config.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, msg=f"new-key path should lint clean — stderr: {result.stderr}")

    def test_workflow_config_accepts_legacy_wave_execution_key(self) -> None:
        """Wave 1p337 (1p336) AC-7: docs-lint required-keys check passes with the
        legacy `wave_execution` key set and the new `wave_implement` key absent
        (no-silent-break promise for existing consumer configs)."""
        root = self.copy_fixture()
        # Base fixture already uses the legacy key; no edit needed — just verify pass.
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, msg=f"legacy-key path must remain clean — stderr: {result.stderr}")

    def test_workflow_config_fails_when_neither_alias_present(self) -> None:
        """Wave 1p337 (1p336) AC-8: docs-lint required-keys check fails when neither
        `wave_implement` nor `wave_execution` is set; error message names both
        acceptable keys so the operator sees the migration path inline."""
        root = self.copy_fixture()
        config = root / "docs/workflow-config.json"
        data = json.loads(config.read_text(encoding="utf-8"))
        del data["wave_execution"]  # remove both possible aliases
        config.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        # Error message must name both the new and legacy keys.
        self.assertIn("wave_implement", result.stderr)
        self.assertIn("wave_execution", result.stderr)
        self.assertIn("legacy", result.stderr.lower())

    def test_workflow_config_accepts_new_wave_review_key(self) -> None:
        """Wave 1p337 (1p33f) AC-3: docs-lint required-keys check passes with the new
        `wave_review` key set and the legacy `wave_council_policy` key absent."""
        root = self.copy_fixture()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, msg=f"new-key path should lint clean — stderr: {result.stderr}")

    def test_workflow_config_accepts_legacy_wave_council_policy_key(self) -> None:
        """Wave 1p337 (1p33f) AC-4: docs-lint required-keys check passes with the
        legacy `wave_council_policy` key set and the new `wave_review` key absent
        (alias-tuple back-compat for the council-policy rename)."""
        root = self.copy_fixture()
        config = root / "docs/workflow-config.json"
        data = json.loads(config.read_text(encoding="utf-8"))
        data["wave_council_policy"] = data.pop("wave_review")
        config.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, msg=f"legacy-key path must remain clean — stderr: {result.stderr}")

    def test_workflow_config_fails_when_neither_council_alias_present(self) -> None:
        """Wave 1p337 (1p33f) AC-5: docs-lint required-keys check fails when neither
        `wave_review` nor `wave_council_policy` is set; error message names both
        acceptable keys so the operator sees the migration path inline."""
        root = self.copy_fixture()
        config = root / "docs/workflow-config.json"
        data = json.loads(config.read_text(encoding="utf-8"))
        del data["wave_review"]
        config.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("wave_review", result.stderr)
        self.assertIn("wave_council_policy", result.stderr)
        self.assertIn("legacy", result.stderr.lower())

    def test_ac_priority_placeholder_priority_fails(self) -> None:
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.write_text(
            change_doc.read_text(encoding="utf-8").replace(
                "| AC-1 | required |",
                "| AC-1 | required / important / nice-to-have / not-this-scope |",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("uncategorized", result.stderr)
        self.assertIn("unknown ACs are not allowed", result.stderr)

    def test_activated_wave_requires_sibling_change_docs(self) -> None:
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.unlink()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            f"wave-owned change `{self.VALID_CHANGE_ID}` must exist at "
            "`docs/waves/waves/change-2026-03/00058-bug fixture-core.md`",
            result.stderr,
        )
        self.assertIn("Prepare wave", result.stderr)

    def test_missing_persona_journal_reference_fails(self) -> None:
        root = self.copy_fixture()
        persona_doc = root / self.PERSONA_DOC_PATH
        persona_doc.write_text(
            persona_doc.read_text(encoding="utf-8").replace(
                "- Journal: `docs/agents/journals/wave-coordinator.md`",
                "- Journal: `docs/agents/journals/missing.md`",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("persona doc references missing journal", result.stderr)

    def test_journal_requires_operating_memory_sections(self) -> None:
        root = self.copy_fixture()
        journal_doc = root / "docs/agents/journals/wave-coordinator.md"
        journal_doc.write_text(
            journal_doc.read_text(encoding="utf-8").replace(
                "## Operating Identity\n\n"
                "- Role memory for a wave coordinator agent responsible for preserving delivery gates, reviewer routing, and wave sequencing after context loss.\n\n",
                "",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required section `## Operating Identity`", result.stderr)

    def test_journal_rejects_sensitive_or_low_salience_noise(self) -> None:
        root = self.copy_fixture()
        journal_doc = root / "docs/agents/journals/wave-coordinator.md"
        journal_doc.write_text(
            journal_doc.read_text(encoding="utf-8").replace(
                "- No active capture beyond the fixture wave reference above.",
                "- password: fixture-value\n- routine progress update",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("sensitive data, raw transcript content, or low-salience routine noise", result.stderr)

    def test_agent_role_metadata_required_for_dashboard_visible_docs(self) -> None:
        root = self.copy_fixture()
        agent_doc = root / "docs/agents/code-reviewer.md"
        agent_doc.write_text(
            "# Code Reviewer\n\nOwner: Engineering\nCategory: review\n\n## Operating Identity\n\nReviews code quality.\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/agents/code-reviewer.md: missing required `Role:` metadata", result.stderr)

    def test_agent_category_metadata_required_for_all_agent_docs(self) -> None:
        root = self.copy_fixture()
        persona_doc = root / "docs/agents/personas/wave-coordinator.md"
        persona_doc.write_text(
            persona_doc.read_text(encoding="utf-8").replace("Category: persona\n", ""),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/agents/personas/wave-coordinator.md: missing required `Category:` metadata", result.stderr)

    def test_factor_agent_role_metadata_required_for_canonical_docs(self) -> None:
        root = self.copy_fixture()
        factor_doc = root / "docs/agents/factor-03-config.md"
        factor_doc.write_text(
            "# Factor 03 — Config Review Agent\n\nOwner: Engineering\nStatus: active\nCategory: factor\nLast verified: 2026-05-20\n\n## What This Factor Covers\n\nConfiguration values.\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/agents/factor-03-config.md: missing required `Role:` metadata", result.stderr)

    def test_role_metadata_required_for_arbitrary_specialist_doc(self) -> None:
        """Wave 1p35d (1p35l): the Role: rule covers every agent doc, not just the canonical allow-list."""
        root = self.copy_fixture()
        specialist_dir = root / "docs/agents/specialists"
        specialist_dir.mkdir(parents=True, exist_ok=True)
        synthetic = specialist_dir / "synthetic-specialist.md"
        synthetic.write_text(
            "# Synthetic Specialist\n\nOwner: Engineering\nStatus: active\nCategory: specialist\nLast verified: 2026-06-04\n\n## Operating Identity\n\nFixture role doc with no Role: field.\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "docs/agents/specialists/synthetic-specialist.md: missing required `Role:` metadata",
            result.stderr,
        )
        self.assertIn("invisible agent", result.stderr)

    def test_three_councils_have_role_field_in_self_host(self) -> None:
        """Wave 1p35d (1p35l, AC-11): the three universal-specialist council docs must
        carry `Role:` in the self-host. These are the canonical surfaces the dashboard
        must always be able to classify; their post-1p33i shape is the regression target."""
        # PROJECT_ROOT at module scope is the parent of the scripts tree (cwd for the
        # lint subprocess); the actual self-host repo root is one level deeper.
        self_host_root = SCRIPTS_ROOT.parents[1].parent  # .wavefoundry/framework → repo root
        import re as _re
        for slug in ("red-team", "wave-council", "archetype-council"):
            path = self_host_root / "docs" / "agents" / "specialists" / f"{slug}.md"
            self.assertTrue(path.is_file(), f"missing council doc: {path}")
            text = path.read_text(encoding="utf-8")
            self.assertIsNotNone(
                _re.search(rf"^Role:\s+{slug}\s*$", text, _re.MULTILINE),
                f"{path.relative_to(self_host_root)} must declare `Role: {slug}`",
            )

    def test_journal_docs_are_exempt_from_role_metadata_rule(self) -> None:
        root = self.copy_fixture()
        agent_doc = root / "docs/agents/code-reviewer.md"
        agent_doc.write_text(
            "# Code Reviewer\n\nOwner: Engineering\nStatus: active\nRole: code-reviewer\nCategory: review\nLast verified: 2026-05-20\n\n## Operating Identity\n\nReviews code quality.\n",
            encoding="utf-8",
        )
        journal_doc = root / "docs/agents/journals/wave-coordinator.md"
        journal_doc.write_text(
            journal_doc.read_text(encoding="utf-8").replace("Role: wave-coordinator\n\n", ""),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)

    def test_persona_requires_operating_salience(self) -> None:
        root = self.copy_fixture()
        persona_doc = root / self.PERSONA_DOC_PATH
        persona_doc.write_text(
            persona_doc.read_text(encoding="utf-8").replace(
                "## Salience triggers\n\n"
                "- Critical/high: operator directives, compaction-sensitive blockers, review routing drift, and regression-prone wave-contract changes.\n"
                "- Medium: follow-up review or migration watchpoints that affect later wave execution.\n\n",
                "",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required section `## Salience triggers`", result.stderr)

    def test_closed_wave_requires_completed_at(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8")
            .replace("Status: active", "Status: completed")
            .replace("## Wave Summary", "**Current state:** completed.\n\n## Wave Summary"),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("closed wave must record `Completed at`", result.stderr)

    def test_closed_wave_requires_required_reviewer_lane_evidence(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8")
            .replace("Status: active", "Status: completed")
            .replace(
                "## Wave Summary",
                "Completed at: 2026-03-21T00:00:00Z\n\n"
                "## Readiness checkpoints\n\n"
                "- Required reviewer lanes: `code-reviewer`, `qa-reviewer`\n\n"
                "## Review checkpoints\n\n"
                "- Code review: complete\n\n"
                "**Current state:** completed.\n\n"
                "## Wave Summary",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "missing review checkpoint evidence for required reviewer lane `qa-reviewer`",
            result.stderr,
        )

    def test_missing_journal_semantic_section_fails(self) -> None:
        root = self.copy_fixture()
        journal_doc = root / "docs/agents/journals/wave-coordinator.md"
        journal_doc.write_text(
            journal_doc.read_text(encoding="utf-8").replace(
                "\n## Governance\n\n"
                "- Allowed memory: role behavior, validated wave hazards, and evidence linked to stable artifacts.\n"
                "- Disallowed memory: sensitive operator data, credentials, raw transcripts, or routine progress noise.\n",
                "\n",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required section `## Governance`", result.stderr)

    def test_missing_persona_workflows_fails(self) -> None:
        root = self.copy_fixture()
        persona_doc = root / self.PERSONA_DOC_PATH
        persona_doc.write_text(
            persona_doc.read_text(encoding="utf-8").replace(
                "\n## Workflows\n\n- Plan admission, sequence follow-up review, and coordinate low-noise validation work.\n\n",
                "\n",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required section `## Workflows`", result.stderr)

    def test_journal_reference_to_unknown_change_fails(self) -> None:
        root = self.copy_fixture()
        journal_doc = root / "docs/agents/journals/wave-coordinator.md"
        journal_doc.write_text(
            journal_doc.read_text(encoding="utf-8").replace(
                f"Change ID: `{self.VALID_CHANGE_ID}`",
                "Change ID: `0005a-enh missing-change`",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("journal doc references unknown Change ID `0005a-enh missing-change`", result.stderr)

    def test_manifest_and_workflow_seed_source_mismatch_fails(self) -> None:
        root = self.copy_fixture()
        manifest_doc = root / "docs/prompts/prompt-surface-manifest.json"
        manifest_doc.write_text(
            '{\n  "schema_version": 2,\n  "framework_revision": "2099-01-01a",\n  "seed_framework_source": "agent-workflows/legacy-framework",\n  "generated_artifacts": [\n    "docs/prompts/prompt-surface-manifest.json"\n  ]\n}\n',
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("prompt_generation.seed_framework_source` does not match", result.stderr)

    def test_stale_legacy_prompt_marker_fails(self) -> None:
        root = self.copy_fixture()
        wave_prompt = root / "docs/prompts/install-wavefoundry.prompt.md"
        wave_prompt.write_text(
            wave_prompt.read_text(encoding="utf-8") + "\nLegacy helper: spec-change-lifecycle\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WARNING: migration-edge drift detected; stale legacy marker remains in docs/prompts/install-wavefoundry.prompt.md: spec-change-lifecycle", result.stderr)

    def test_unsatisfied_change_dependency_fails(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8").replace(
                "Change Status: `complete`",
                "Change Status: `planned`",
                1,
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            f"change `{self.FOLLOW_UP_CHANGE_ID}` is `ready` but dependency `{self.VALID_CHANGE_ID}` is still `planned`",
            result.stderr,
        )

    def test_invalid_change_status_progression_fails(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8").replace(
                "Previous Change Status: `planned`\nChange Status: `complete`",
                "Previous Change Status: `complete`\nChange Status: `active`",
                1,
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"change `{self.VALID_CHANGE_ID}` has invalid status progression `complete` -> `active`", result.stderr)

    def test_missing_change_status_fails(self) -> None:
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8").replace(
                "Change Status: `complete`\n",
                "",
                1,
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"change `{self.VALID_CHANGE_ID}` is missing `Change Status`", result.stderr)

    def _write_plan_fixture(self, root: Path, basename: str, body: str) -> Path:
        plans_dir = root / "docs/plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        plan_path = plans_dir / f"{basename}.md"
        plan_path.write_text(body, encoding="utf-8")
        return plan_path

    def test_plan_filename_matches_change_id_passes(self) -> None:
        root = self.copy_fixture()
        change_id = "1a2x8-bug staging-plan-fixture"
        self._write_plan_fixture(
            root,
            change_id,
            f"# Staging plan fixture\n\n"
            f"Owner: Engineering\nStatus: planning\nLast verified: 2026-04-18\n\n"
            f"## Change ID\n\nChange ID: `{change_id}`\n\n"
            f"## Rationale\n\nFixture.\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)

    def test_plan_filename_wave_overview_matches_wave_id_passes(self) -> None:
        root = self.copy_fixture()
        wave_id = "1a2yy staging-overview-fixture"
        self._write_plan_fixture(
            root,
            wave_id,
            f"# Overview plan\n\n"
            f"Owner: Engineering\nStatus: planning\nLast verified: 2026-04-18\n\n"
            f"## Change ID\n\nWave: `{wave_id}`\n\n"
            f"## Rationale\n\nFixture.\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)

    def test_plan_filename_slug_only_fails(self) -> None:
        root = self.copy_fixture()
        change_id = "1a2x8-bug staging-plan-fixture"
        self._write_plan_fixture(
            root,
            "staging-plan-fixture",
            f"# Staging plan fixture\n\n"
            f"Owner: Engineering\nStatus: planning\nLast verified: 2026-04-18\n\n"
            f"## Change ID\n\nChange ID: `{change_id}`\n\n"
            f"## Rationale\n\nFixture.\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            f"plan filename must match `Change ID` — rename to `docs/plans/{change_id}.md`",
            result.stderr,
        )

    def test_plan_missing_identifier_fails(self) -> None:
        root = self.copy_fixture()
        self._write_plan_fixture(
            root,
            "some-orphan-plan",
            "# Orphan plan\n\n"
            "Owner: Engineering\nStatus: planning\nLast verified: 2026-04-18\n\n"
            "## Rationale\n\nFixture.\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "plan is missing a `Change ID:` or `Wave:` identifier line",
            result.stderr,
        )

    def test_checkbox_task_syntax_passes(self) -> None:
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.write_text(
            change_doc.read_text(encoding="utf-8")
            + "\n## Tasks\n\n- [ ] Inspect parser behavior.\n- [ ] Keep fixtures readable.\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)

    def test_missing_manifest_generated_artifact_registration_fails(self) -> None:
        root = self.copy_fixture()
        manifest_doc = root / "docs/prompts/prompt-surface-manifest.json"
        manifest_doc.write_text(
            '{\n'
            '  "schema_version": 2,\n'
            '  "framework_revision": "2099-01-01a",\n'
            '  "seed_framework_source": ".wavefoundry/framework",\n'
            '  "generated_artifacts": [\n'
            '    "docs/prompts/prompt-surface-manifest.json",\n'
            '    "docs/agents/session-handoff.md",\n'
            '    "docs/waves/",\n'
            '    "docs/agents/journals/"\n'
            '  ],\n'
            '  "public_prompt_surface": [\n'
            '    {\n'
            '      "doc": "docs/prompts/install-wavefoundry.prompt.md",\n'
            '      "shortcut": "Init wave framework"\n'
            '    }\n'
            '  ]\n'
            '}\n',
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("`generated_artifacts` is missing `docs/agents/personas/`", result.stderr)

    def test_stale_wrapper_target_is_error(self) -> None:
        root = self.copy_fixture()
        wrapper = root / "docs-lint"
        wrapper.write_text("#!/bin/sh\npython3 agent-workflows/legacy-framework/scripts/docs-lint.py\n", encoding="utf-8")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("root wrapper must be removed", result.stderr)

    def test_migration_audit_report_is_written_only_when_requested(self) -> None:
        root = self.copy_fixture()
        wave_prompt = root / "docs/prompts/install-wavefoundry.prompt.md"
        wave_prompt.write_text(
            wave_prompt.read_text(encoding="utf-8") + "\nLegacy helper: spec-change-lifecycle\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint_with_args(root, "--write-migration-audit")
            audit_path = root / "docs/reports/wave-migration-audit.md"
            audit_text = audit_path.read_text(encoding="utf-8")
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("migration-audit: updated docs/reports/wave-migration-audit.md", result.stderr)
        self.assertIn("## Warnings", audit_text)
        self.assertIn("spec-change-lifecycle", audit_text)

    def test_archived_legacy_wave_docs_are_ignored_for_migration_drift(self) -> None:
        root = self.copy_fixture()
        archived_doc = root / "docs/waves/00000 wave-zero-plans-and-specs/legacy-change.md"
        archived_doc.parent.mkdir(parents=True, exist_ok=True)
        archived_doc.write_text(
            "# Legacy Change\n\nOwner: Engineering\nStatus: closed\nLast verified: 2026-03-24\n\nLegacy helper: agent-workflows/legacy-framework\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("legacy-change.md", result.stderr)

    def test_pycache_directories_do_not_fail_docs_lint(self) -> None:
        """Wave 1p35d (1p35n, AC-1, AC-7): `__pycache__` is in `LINT_EXCLUDED_TRANSIENT_DIRS`.
        `.gitignore` is the source of truth; lint does not duplicate that check.
        The MCP server creates pycache on every Python import — flagging it here
        produced a recurring blocker the operator decided to retire."""
        root = self.copy_fixture()
        pycache_dir = root / ".wavefoundry/framework/scripts/__pycache__"
        pycache_dir.mkdir(parents=True, exist_ok=True)
        (pycache_dir / "fixture.pyc").write_bytes(b"fixture")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("__pycache__", result.stderr)
        self.assertNotIn("python bytecode cache", result.stderr)

    def test_lint_still_flags_other_genuinely_forbidden_artifacts(self) -> None:
        """Wave 1p35d (1p35n, AC-2, AC-8): the pycache exclusion is targeted, not blanket.
        Other 'should not exist' checks must still fire. Uses a forbidden root wrapper
        as the proof (`check_forbidden_root_wrappers` is unrelated to pycache and still active)."""
        root = self.copy_fixture()
        # Drop a retired root wrapper to trigger check_forbidden_root_wrappers
        (root / "package-wave-framework").write_text("legacy wrapper\n", encoding="utf-8")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("retired root wrapper", result.stderr)

    def test_persona_scope_section_is_forbidden(self) -> None:
        """## Scope is forbidden in persona docs — adding it should fail."""
        root = self.copy_fixture()
        persona_doc = root / self.PERSONA_DOC_PATH
        persona_doc.write_text(
            persona_doc.read_text(encoding="utf-8") + "\n## Scope\n\n- Forbidden scope section.\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("persona docs must not contain `## Scope`", result.stderr)

    def test_change_doc_with_wave_id_prose_not_flagged_as_wave_record(self) -> None:
        """A change doc that mentions wave-id in prose must not be misclassified as a wave record."""
        root = self.copy_fixture()
        change_doc = root / "docs/waves/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.write_text(
            change_doc.read_text(encoding="utf-8")
            + "\n## Notes\n\n"
            "This change fixes a detector that previously used `wave-id:` string presence as a heuristic.\n"
            "Any doc containing the string wave-id: followed by a backtick-value would be misclassified.\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)

    def test_wave_md_still_checked_as_wave_record(self) -> None:
        """A wave.md with no valid wave-id must still trigger wave-record validation."""
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8").replace(
                f"wave-id: `{self.VALID_WAVE_ID}`",
                "wave-id: `invalid-format no-wave-id-here`",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing stable `wave-id` declaration", result.stderr)


class CheckPycacheTests(unittest.TestCase):
    """Wave 1p35d (1p35n): `check_pycache` is a documented no-op. Membership of
    `__pycache__` in `LINT_EXCLUDED_TRANSIENT_DIRS` is the contract; lint defers
    to `.gitignore` as the source of truth and never flags pycache directly."""

    def setUp(self) -> None:
        import sys

        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib.core_validators import check_pycache, LINT_EXCLUDED_TRANSIENT_DIRS

        self._check_pycache = check_pycache
        self._exclusion_set = LINT_EXCLUDED_TRANSIENT_DIRS
        self._root = Path(tempfile.mkdtemp(prefix="wave-check-pycache-"))

    def tearDown(self) -> None:
        shutil.rmtree(self._root)

    def _scripts_pycache(self) -> Path:
        d = self._root / ".wavefoundry" / "framework" / "scripts" / "__pycache__"
        d.mkdir(parents=True, exist_ok=True)
        (d / "fixture.pyc").write_bytes(b"x")
        return d

    def test_pycache_in_named_exclusion_set(self) -> None:
        """The exclusion is discoverable via a named module constant, not buried inline (AC-2)."""
        self.assertIn("__pycache__", self._exclusion_set)

    def test_universal_python_transients_in_exclusion_set(self) -> None:
        """Wave 1p35d (1p35p enterprise-deployment hardening): the exclusion
        list covers every Python-ecosystem cache that gets generated by routine
        tool invocations and would otherwise produce the same recurring blocker
        pattern that retired `check_pycache`. See
        `docs/references/docs-lint-exclusions.md` for the operator-visible
        rationale per pattern."""
        for pattern in (".pytest_cache", ".mypy_cache", ".ruff_cache",
                        ".tox", ".coverage"):
            self.assertIn(
                pattern, self._exclusion_set,
                f"{pattern} must be in LINT_EXCLUDED_TRANSIENT_DIRS "
                "(see docs/references/docs-lint-exclusions.md)",
            )

    def test_exclusion_doc_exists_and_lists_each_pattern(self) -> None:
        """The operator-visible doc at docs/references/docs-lint-exclusions.md
        must enumerate every pattern in the exclusion set. Drift between the
        Python constant and the operator-facing doc is exactly what the doc
        exists to prevent — enterprise security review reads the doc, not
        the source."""
        # Resolve repo root from the test file location.
        repo_root = SCRIPTS_ROOT.parents[1].parent
        doc_path = repo_root / "docs" / "references" / "docs-lint-exclusions.md"
        self.assertTrue(doc_path.is_file(), f"missing {doc_path}")
        doc_text = doc_path.read_text(encoding="utf-8")
        for pattern in self._exclusion_set:
            self.assertIn(
                pattern, doc_text,
                f"{pattern} is in LINT_EXCLUDED_TRANSIENT_DIRS but not in "
                "docs/references/docs-lint-exclusions.md — security audit drift",
            )

    def test_no_failures_when_pycache_absent(self) -> None:
        self.assertEqual(self._check_pycache(self._root), [])

    def test_no_failures_when_pycache_present_on_disk(self) -> None:
        """Wave 1p35d (1p35n, AC-1): on-disk pycache is no longer flagged."""
        self._scripts_pycache()
        self.assertEqual(self._check_pycache(self._root), [])

    def test_no_failures_when_pycache_tracked_in_git(self) -> None:
        """Per operator decision the check is fully retired — even tracked pycache
        is no longer surfaced through this lint surface. Code review and `.gitignore`
        are the controls for preventing bytecode in git from now on."""
        self._scripts_pycache()
        # No git setup needed — the function never consults git anymore.
        self.assertEqual(self._check_pycache(self._root), [])


class CheckPromptFileExtensionsTests(unittest.TestCase):
    """Unit tests for ``check_prompt_file_extensions``."""

    def setUp(self) -> None:
        import sys

        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib.core_validators import check_prompt_file_extensions

        self._check = check_prompt_file_extensions
        self._root = Path(tempfile.mkdtemp(prefix="wave-prompt-ext-"))

    def tearDown(self) -> None:
        shutil.rmtree(self._root)

    def _prompts_dir(self) -> Path:
        d = self._root / "docs" / "prompts"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_no_prompts_dir_passes(self) -> None:
        self.assertEqual(self._check(self._root), [])

    def test_prompt_md_file_fails(self) -> None:
        d = self._prompts_dir()
        (d / "close-wave.md").write_text("# Close Wave\n", encoding="utf-8")
        errors = self._check(self._root)
        self.assertEqual(len(errors), 1)
        self.assertIn("close-wave.md", errors[0])
        self.assertIn(".prompt.md", errors[0])

    def test_prompt_md_file_in_agents_subdir_fails(self) -> None:
        d = self._prompts_dir() / "agents"
        d.mkdir(parents=True, exist_ok=True)
        (d / "close-wave.md").write_text("# Close Wave\n", encoding="utf-8")
        errors = self._check(self._root)
        self.assertEqual(len(errors), 1)
        self.assertIn("close-wave.md", errors[0])

    def test_prompt_md_extension_passes(self) -> None:
        d = self._prompts_dir()
        (d / "close-wave.prompt.md").write_text("# Close Wave\n", encoding="utf-8")
        self.assertEqual(self._check(self._root), [])

    def test_index_md_exempt(self) -> None:
        d = self._prompts_dir()
        (d / "index.md").write_text("# Index\n", encoding="utf-8")
        self.assertEqual(self._check(self._root), [])

    def test_readme_md_exempt(self) -> None:
        d = self._prompts_dir() / "agents"
        d.mkdir(parents=True, exist_ok=True)
        (d / "README.md").write_text("# Agents\n", encoding="utf-8")
        self.assertEqual(self._check(self._root), [])

    def test_multiple_violations_reported(self) -> None:
        d = self._prompts_dir()
        (d / "close-wave.md").write_text("# Close\n", encoding="utf-8")
        (d / "review-wave.md").write_text("# Review\n", encoding="utf-8")
        errors = self._check(self._root)
        self.assertEqual(len(errors), 2)


class CheckForbiddenRootWrappersTests(unittest.TestCase):
    """Unit tests for ``check_forbidden_root_wrappers``."""

    def setUp(self) -> None:
        import sys

        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib.core_validators import check_forbidden_root_wrappers
        from wave_lint_lib.constants import FORBIDDEN_ROOT_WRAPPERS_RETIRED, FORBIDDEN_ROOT_WRAPPERS_RELOCATED

        self._check = check_forbidden_root_wrappers
        self._forbidden = FORBIDDEN_ROOT_WRAPPERS_RETIRED + FORBIDDEN_ROOT_WRAPPERS_RELOCATED
        self._root = Path(tempfile.mkdtemp(prefix="wave-forbidden-root-"))

    def tearDown(self) -> None:
        shutil.rmtree(self._root)

    def test_no_forbidden_files_passes(self) -> None:
        self.assertEqual(self._check(self._root), [])

    def test_each_forbidden_wrapper_fails(self) -> None:
        for name in self._forbidden:
            (self._root / name).write_text("#!/bin/sh\n", encoding="utf-8")
            errors = self._check(self._root)
            self.assertEqual(len(errors), 1, f"expected 1 error for {name}, got {errors}")
            self.assertIn(name, errors[0])
            self.assertIn("must be removed", errors[0])
            (self._root / name).unlink()

    def test_retired_wrapper_message_says_no_replacement(self) -> None:
        from wave_lint_lib.constants import FORBIDDEN_ROOT_WRAPPERS_RETIRED
        name = FORBIDDEN_ROOT_WRAPPERS_RETIRED[0]
        (self._root / name).write_text("#!/bin/sh\n", encoding="utf-8")
        errors = self._check(self._root)
        self.assertEqual(len(errors), 1)
        self.assertIn("no replacement", errors[0])
        self.assertNotIn(".wavefoundry/bin", errors[0])

    def test_relocated_wrapper_message_says_bin(self) -> None:
        from wave_lint_lib.constants import FORBIDDEN_ROOT_WRAPPERS_RELOCATED
        name = FORBIDDEN_ROOT_WRAPPERS_RELOCATED[0]
        (self._root / name).write_text("#!/bin/sh\n", encoding="utf-8")
        errors = self._check(self._root)
        self.assertEqual(len(errors), 1)
        self.assertIn(".wavefoundry/bin", errors[0])

    def test_multiple_forbidden_files_reports_all(self) -> None:
        for name in self._forbidden:
            (self._root / name).write_text("#!/bin/sh\n", encoding="utf-8")
        errors = self._check(self._root)
        self.assertEqual(len(errors), len(self._forbidden))

    def test_allowed_root_file_not_flagged(self) -> None:
        (self._root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        self.assertEqual(self._check(self._root), [])


class LinkValidatorUnitTests(unittest.TestCase):
    """Unit tests for check_markdown_links — exercises the function directly."""

    def setUp(self) -> None:
        import sys
        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib.link_validators import check_markdown_links
        self._check = check_markdown_links
        self._tmp = Path(tempfile.mkdtemp(prefix="link-validator-unit-"))
        # Create a minimal docs/ structure so iter helpers work.
        (self._tmp / "docs").mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self._tmp)

    def _write(self, rel: str, content: str) -> Path:
        path = self._tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_valid_relative_link_passes(self) -> None:
        target = self._write("docs/other.md", "# Other\n")
        doc = self._write("docs/source.md", "[Other](other.md)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(result, [])

    def test_broken_relative_link_fails(self) -> None:
        doc = self._write("docs/source.md", "[Missing](missing.md)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(len(result), 1)
        self.assertIn("broken link", result[0])
        self.assertIn("missing.md", result[0])

    def test_url_is_skipped(self) -> None:
        doc = self._write("docs/source.md", "[Ext](https://example.com/page)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(result, [])

    def test_pure_anchor_is_skipped(self) -> None:
        doc = self._write("docs/source.md", "[Section](#my-section)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(result, [])

    def test_anchor_fragment_stripped_before_resolution(self) -> None:
        self._write("docs/other.md", "# Other\n")
        doc = self._write("docs/source.md", "[Other](other.md#heading)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(result, [])

    def test_link_inside_code_fence_is_skipped(self) -> None:
        content = "```markdown\n[Missing](no-such-file.md)\n```\n"
        doc = self._write("docs/source.md", content)
        result = self._check(self._tmp, doc)
        self.assertEqual(result, [])

    def test_link_inside_inline_code_is_skipped(self) -> None:
        content = "Use `[Missing](no-such-file.md)` as an example.\n"
        doc = self._write("docs/source.md", content)
        result = self._check(self._tmp, doc)
        self.assertEqual(result, [])

    def test_url_encoded_path_resolves_correctly(self) -> None:
        subdir = self._tmp / "docs" / "sub dir"
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / "target.md").write_text("# Target\n", encoding="utf-8")
        doc = self._write("docs/source.md", "[Target](sub%20dir/target.md)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(result, [])

    def test_directory_trailing_slash_is_skipped(self) -> None:
        doc = self._write("docs/source.md", "[Dir](some/dir/)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(result, [])

    def test_image_link_is_not_checked(self) -> None:
        doc = self._write("docs/source.md", "![Alt](missing-image.png)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(result, [])

    def test_reports_prefix_is_skipped(self) -> None:
        doc = self._write("docs/reports/reindex-2026-01-01.md", "[Old](missing.md)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(result, [])

    def test_duplicate_broken_link_reported_once(self) -> None:
        doc = self._write("docs/source.md", "[A](missing.md)\n[B](missing.md)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(len(result), 1)


class LinkValidatorIntegrationTests(DocsLintFixtureTests):
    """Integration tests that run the full docs-lint pipeline to verify link checking."""

    def test_broken_link_in_docs_fails_lint(self) -> None:
        root = self.copy_fixture()
        doc = root / "docs/README.md"
        doc.write_text(
            doc.read_text(encoding="utf-8") + "\n[Broken](no-such-file.md)\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("broken link", result.stderr)
        self.assertIn("no-such-file.md", result.stderr)

    def test_valid_link_in_docs_passes_lint(self) -> None:
        root = self.copy_fixture()
        # Link from README.md to references/project-context-memory.md (exists in fixture).
        target_rel = "references/project-context-memory.md"
        target = root / "docs" / target_rel
        doc = root / "docs/README.md"
        # Only add the link if the target actually exists in this fixture.
        if target.exists():
            doc.write_text(
                doc.read_text(encoding="utf-8") + f"\n[Memory]({target_rel})\n",
                encoding="utf-8",
            )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)


class PrepareCouncilVerdictLintTests(DocsLintFixtureTests):
    """AC-7: check_prepare_council_verdict — at least one passing and one failing test."""

    ACTIVE_WAVE = Path("docs/waves/waves/change-2026-03/wave.md")

    def _patch_wave_status(self, root: Path, status: str) -> None:
        wave_md = root / self.ACTIVE_WAVE
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "Status: active",
                f"Status: {status}",
            ),
            encoding="utf-8",
        )

    def _add_council_verdict(self, root: Path) -> None:
        wave_md = root / self.ACTIVE_WAVE
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + "\n## Review Checkpoints\n\n- **Prepare-phase Wave Council [prepare-council] — 2026-05-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat: none; strongest-challenge: red-team identified the remaining unknowns; strongest-alternative: keep the verdict structured and machine-readable)\n",
            encoding="utf-8",
        )

    def test_active_wave_with_council_verdict_passes(self) -> None:
        root = self.copy_fixture()
        try:
            self._add_council_verdict(root)
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)
        self.assertNotIn("prepare-council", result.stderr)

    def test_active_wave_without_council_verdict_warns(self) -> None:
        root = self.copy_fixture()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prepare-council", result.stderr)
        self.assertIn("WARNING", result.stderr)

    def test_implementing_wave_without_council_verdict_errors(self) -> None:
        root = self.copy_fixture()
        try:
            self._patch_wave_status(root, "implementing")
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("prepare-council", result.stderr)
        self.assertIn("ERROR", result.stderr)

    def test_implementing_wave_with_council_verdict_passes(self) -> None:
        root = self.copy_fixture()
        try:
            self._patch_wave_status(root, "implementing")
            self._add_council_verdict(root)
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TESTS_ROOT.parent
PROJECT_ROOT = SCRIPTS_ROOT.parents[3]
FIXTURE_ROOT = TESTS_ROOT / "fixtures" / "docs_lint" / "base"
DOCS_LINT_SCRIPT = SCRIPTS_ROOT / "docs_lint.py"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import context_efficiency as ce
from wave_lint_lib.wave_validators import check_wave_docs


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

    def test_context_efficiency_checkpoint_shape_is_linted(self) -> None:
        root = self.copy_fixture()
        try:
            wave_md = root / self.WAVE_DOC_PATH
            original = wave_md.read_text(encoding="utf-8")
            valid = ce.replace_checkpoint_block(
                original,
                ce.empty_checkpoint(self.VALID_WAVE_ID),
            )
            wave_md.write_text(valid, encoding="utf-8")
            self.assertFalse(
                [
                    error
                    for error in check_wave_docs(root, only={wave_md})
                    if "Context Efficiency checkpoint" in error
                ]
            )

            state_prefix = "<!-- wave:context-efficiency-state "
            state_start = valid.index(state_prefix)
            state_end = valid.index(" -->", state_start)
            state_comment = valid[state_start : state_end + 4]
            cases = {
                "duplicate": valid + "\n" + ce.render_checkpoint_block(
                    ce.empty_checkpoint(self.VALID_WAVE_ID)
                ),
                "unmatched": valid.replace(
                    ce.CONTEXT_EFFICIENCY_MARKER_END, "", 1
                ),
                "malformed_json": valid.replace(
                    state_comment, f"{state_prefix}{{ -->"
                ),
                "wrong_schema": valid.replace(
                    f'"schema_version":{ce.STORE_SCHEMA_VERSION}',
                    '"schema_version":999',
                ),
                "invalid_shape": valid.replace(
                    '"stages":{}', '"stages":[]'
                ),
                "altered_table": valid.replace(
                    "| — | 0 | 0 |",
                    "| — | 9 | 0 |",
                    1,
                ),
            }
            for name, text in cases.items():
                with self.subTest(case=name):
                    wave_md.write_text(text, encoding="utf-8")
                    failures = check_wave_docs(root, only={wave_md})
                    self.assertTrue(
                        any(
                            "Context Efficiency checkpoint" in error
                            for error in failures
                        ),
                        failures,
                    )
        finally:
            shutil.rmtree(root)

    def test_external_review_event_ledger_missing_fails_closed(self) -> None:
        root = self.copy_fixture()
        ledger = root / self.WAVE_DOC_PATH.parent / "events.jsonl"
        ledger.unlink()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("canonical review event ledger is missing", result.stderr)

    def test_external_review_event_ledger_malformed_fails_closed(self) -> None:
        root = self.copy_fixture()
        ledger = root / self.WAVE_DOC_PATH.parent / "events.jsonl"
        ledger.write_text('{"record_type":"review_run"}', encoding="utf-8")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("final LF", result.stderr)

    def test_external_review_projection_drift_is_reported(self) -> None:
        root = self.copy_fixture()
        wave_md = root / self.WAVE_DOC_PATH
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "| — | — | — | — | — |",
                "| _Stale projection._ | — | — | — | — |",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("review evidence projection is stale", result.stderr)

    def test_legacy_review_projection_markers_are_validation_equivalent(self) -> None:
        root = self.copy_fixture()
        wave_md = root / self.WAVE_DOC_PATH
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            .replace(
                "<!-- wave:finding-synthesis begin -->",
                "<!-- waveframework:finding-synthesis begin -->",
            )
            .replace(
                "<!-- wave:finding-synthesis end -->",
                "<!-- waveframework:finding-synthesis end -->",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_inline_review_evidence_is_not_a_runtime_fallback(self) -> None:
        root = self.copy_fixture()
        wave_md = root / self.WAVE_DOC_PATH
        text = wave_md.read_text(encoding="utf-8").replace(
            "review-evidence-source: events.jsonl",
            "review-evidence-protocol: 1",
        )
        wave_md.write_text(text, encoding="utf-8")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must declare `review-evidence-source: events.jsonl`", result.stderr)

    def test_external_review_adoption_prefix_mismatch_fails_closed(self) -> None:
        root = self.copy_fixture()
        adoption = root / "docs" / "waves" / "review-evidence-adoptions.json"
        adoption.write_text(
            json.dumps(
                {
                    "protocol_version": 1,
                    "waves": {
                        self.WAVE_DOC_PATH.parent.name: {
                            "version": 1,
                            "source": "events.jsonl",
                            "record_count": 0,
                            "prefix_sha256": "0" * 64,
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("adopted prefix hash does not match", result.stderr)

    def test_verification_stamp_valid_forms_pass(self) -> None:
        # 1ro43 AC-11: the stamp is optional and accepted when well-formed
        # (full or abbreviated hex) — no registration or whitelist needed.
        root = self.copy_fixture()
        doc = root / "docs" / "stamped.md"
        doc.write_text(
            "# Stamped\n\nOwner: Engineering\nStatus: active\n"
            "Last verified: 2026-07-13\nVerified against: abc1234\n\nBody.\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_verification_stamp_malformed_sha_fails(self) -> None:
        # 1ro43 AC-11: a malformed stamp silently degrades drift to the
        # content anchor while LOOKING stamped — docs-lint must flag it.
        root = self.copy_fixture()
        doc = root / "docs" / "stamped.md"
        for bad in ("not-a-sha", "12345", "<commit-sha>"):
            doc.write_text(
                "# Stamped\n\nOwner: Engineering\nStatus: active\n"
                f"Last verified: 2026-07-13\nVerified against: {bad}\n\nBody.\n",
                encoding="utf-8",
            )
            result = self.run_docs_lint(root)
            if result.returncode != 1:
                shutil.rmtree(root)
                self.fail(f"malformed stamp {bad!r} passed lint")
            self.assertIn("malformed `Verified against` stamp", result.stderr)
        shutil.rmtree(root)

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

    def test_workflow_config_passes_with_canonical_keys(self) -> None:
        """Wave 1p5b4: the base fixture uses the canonical `wave_implement` + `wave_review`
        keys (legacy aliases retired) and lints clean."""
        root = self.copy_fixture()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, msg=f"canonical base should lint clean — stderr: {result.stderr}")

    def test_workflow_config_fails_when_wave_implement_missing(self) -> None:
        """Wave 1p5b4: docs-lint requires the canonical `wave_implement` key; legacy
        `wave_execution` is no longer accepted."""
        root = self.copy_fixture()
        config = root / "docs/workflow-config.json"
        data = json.loads(config.read_text(encoding="utf-8"))
        del data["wave_implement"]
        config.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("wave_implement", result.stderr)

    def test_workflow_config_fails_when_wave_review_missing(self) -> None:
        """Wave 1p5b4: docs-lint requires the canonical `wave_review` key; legacy
        `wave_council_policy` is no longer accepted."""
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

    def test_journal_governance_may_forbid_transcript_without_tripping(self) -> None:
        # Wave 1p9bn: a line that FORBIDS raw transcripts (a Governance/disallowed rule) must NOT trip the
        # disallowed-content pattern — a journal must be able to describe its own rule.
        root = self.copy_fixture()
        journal_doc = root / "docs/agents/journals/wave-coordinator.md"
        journal_doc.write_text(
            journal_doc.read_text(encoding="utf-8").replace(
                "- No active capture beyond the fixture wave reference above.",
                "- Do not include raw transcript content, secrets, or routine progress noise.",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_journal_still_rejects_a_real_transcript_line(self) -> None:
        # The negation exemption must NOT weaken the true positive: a non-forbidding transcript line fails.
        root = self.copy_fixture()
        journal_doc = root / "docs/agents/journals/wave-coordinator.md"
        journal_doc.write_text(
            journal_doc.read_text(encoding="utf-8").replace(
                "- No active capture beyond the fixture wave reference above.",
                "- Full transcript of the session pasted below for reference.",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("raw transcript content", result.stderr)

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

    # ------------------------------------------------------------------
    # Wave 1p79x / 1p7ac — factor-surface declared-but-missing gate.
    # 1p7ac re-keys the canonical-doc requirement off the operational
    # active-lane set (workflow-config.json factor_review_policy.applicable_factors),
    # not the repo-profile.json factor_review applicability assessment. The
    # assessment-vs-lane drift surfaces as a non-blocking WARNING.
    # ------------------------------------------------------------------

    def _write_repo_profile(self, root: Path, factor_review: dict) -> None:
        profile = {
            "schema_version": "1.0",
            "factor_review": factor_review,
        }
        profile_path = root / "docs" / "repo-profile.json"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")

    def _set_applicable_factors(self, root: Path, applicable_factors: list[str]) -> None:
        """Set the operational active-lane set in the fixture's workflow-config.json."""
        config_path = root / "docs" / "workflow-config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        policy = config.get("factor_review_policy")
        if not isinstance(policy, dict):
            policy = {}
            config["factor_review_policy"] = policy
        policy["applicable_factors"] = applicable_factors
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    def _write_factor_canonical(self, root: Path, slug: str) -> None:
        doc = root / "docs" / "agents" / f"{slug}.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(
            f"# {slug}\n\nOwner: Engineering\nStatus: active\n"
            f"Role: {slug}\nCategory: factor\nLast verified: 2026-06-22\n\n"
            "## What This Factor Covers\n\nGeneric factor coverage for the fixture.\n",
            encoding="utf-8",
        )

    def _write_factor_wrapper(self, root: Path, slug: str, *, frontmatter: bool = True) -> None:
        wrapper = root / ".claude" / "agents" / f"{slug}.md"
        wrapper.parent.mkdir(parents=True, exist_ok=True)
        if frontmatter:
            body = (
                f"---\nname: {slug}\ndescription: PROACTIVELY use for factor review.\n"
                f"tools: Read, Grep, Glob, Bash\nmodel: sonnet\n---\n\n"
                f"# {slug} (Wrapper)\n\nCanonical factor doc: `docs/agents/{slug}.md`.\n"
            )
        else:
            body = (
                f"# {slug} (Wrapper)\n\nCanonical factor doc: `docs/agents/{slug}.md`.\n"
                "No frontmatter — cannot load as a subagent.\n"
            )
        wrapper.write_text(body, encoding="utf-8")

    def test_factor_surface_lane_active_missing_canonical_fails(self) -> None:
        """Lane-active: a factor in applicable_factors with no canonical doc -> ERROR."""
        root = self.copy_fixture()
        self._set_applicable_factors(root, ["07"])
        self._write_repo_profile(
            root,
            {"07": {"name": "Port binding", "status": "applicable", "rationale": "binds loopback ports"}},
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("factor `07` is an active review lane", result.stderr)
        self.assertIn("seed-050", result.stderr)

    def test_factor_surface_lane_active_correct_canonical_only_passes(self) -> None:
        """Self-host shape: an active-lane canonical with NO wrapper passes."""
        root = self.copy_fixture()
        self._set_applicable_factors(root, ["07"])
        self._write_repo_profile(
            root,
            {"07": {"name": "Port binding", "status": "applicable", "rationale": "binds loopback ports"}},
        )
        self._write_factor_canonical(root, "factor-07-port-binding")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_factor_surface_lane_active_correct_canonical_with_wrapper_passes(self) -> None:
        root = self.copy_fixture()
        self._set_applicable_factors(root, ["07"])
        self._write_repo_profile(
            root,
            {"07": {"name": "Port binding", "status": "applicable", "rationale": "binds loopback ports"}},
        )
        self._write_factor_canonical(root, "factor-07-port-binding")
        self._write_factor_wrapper(root, "factor-07-port-binding", frontmatter=True)
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_factor_surface_retired_lane_repo_profile_applicable_passes(self) -> None:
        """Retired lane (empty applicable_factors) with 2+ repo-profile factors still
        `applicable` -> PASS without falsifying the assessment, surfacing ONE consolidated
        non-blocking WARNING (wave 1p9bp) rather than N per-factor lines."""
        root = self.copy_fixture()
        self._set_applicable_factors(root, [])
        self._write_repo_profile(
            root,
            {
                "07": {"name": "Port binding", "status": "applicable", "rationale": "binds loopback ports"},
                "12": {"name": "Admin processes", "status": "applicable", "rationale": "CLI admin"},
            },
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # No canonical docs required; assessed factors are non-blocking warnings.
        self.assertNotIn("ERROR:", result.stderr)
        self.assertIn("WARNING:", result.stderr)
        # Consolidated advisory: one line, names both factors + a single actionable next step.
        self.assertIn("is empty while docs/repo-profile.json marks 2 factors applicable", result.stderr)
        self.assertIn("`07`", result.stderr)
        self.assertIn("`12`", result.stderr)
        self.assertIn("Upgrade Wavefoundry", result.stderr)
        # The per-factor "no active review lane" phrasing is NOT used when consolidated.
        self.assertNotIn("no active review lane", result.stderr)

    def test_factor_surface_single_inactive_factor_stays_per_factor(self) -> None:
        """Boundary (wave 1p9bp): with an empty lane set but only ONE applicable factor,
        the single per-factor warning is already a single actionable instruction, so it is
        NOT consolidated (the consolidation only triggers at 2+ inactive-applicable factors)."""
        root = self.copy_fixture()
        self._set_applicable_factors(root, [])
        self._write_repo_profile(
            root,
            {"07": {"name": "Port binding", "status": "applicable", "rationale": "binds loopback ports"}},
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("ERROR:", result.stderr)
        self.assertIn("factor `07`", result.stderr)
        self.assertIn("no active review lane", result.stderr)
        self.assertNotIn("marks 2 factors applicable", result.stderr)

    def test_factor_surface_assessment_only_factor_warns_not_errors(self) -> None:
        """Assessment-only: a factor `applicable` in repo-profile but NOT in
        applicable_factors -> WARNING, not ERROR (does not block the gate)."""
        root = self.copy_fixture()
        # Active lane is 03 (with its doc); 07 is assessed applicable but not a lane.
        self._set_applicable_factors(root, ["03"])
        self._write_repo_profile(
            root,
            {
                "03": {"name": "Config", "status": "applicable", "rationale": "config"},
                "07": {"name": "Port binding", "status": "applicable", "rationale": "binds loopback ports"},
            },
        )
        self._write_factor_canonical(root, "factor-03-config")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        # The drift is visible but unblocked: passes, and 07 surfaces as a WARNING only.
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("ERROR:", result.stderr)
        self.assertIn("WARNING:", result.stderr)
        self.assertIn("factor `07`", result.stderr)
        self.assertIn("no active review lane", result.stderr)

    def test_factor_surface_self_host_shape_passes(self) -> None:
        """Self-host shape: applicable_factors 03/05/12/13 with their canonical docs -> PASS,
        no residual drift WARNING."""
        root = self.copy_fixture()
        self._set_applicable_factors(root, ["03", "05", "12", "13"])
        self._write_repo_profile(
            root,
            {
                "03": {"name": "Config", "status": "applicable", "rationale": "config"},
                "05": {"name": "Build / release / run", "status": "applicable", "rationale": "build"},
                "07": {"name": "Port binding", "status": "partial", "rationale": "optional dashboard"},
                "12": {"name": "Admin processes", "status": "applicable", "rationale": "CLI admin"},
                "13": {"name": "API first", "status": "applicable", "rationale": "MCP surface"},
            },
        )
        self._write_factor_canonical(root, "factor-03-config")
        self._write_factor_canonical(root, "factor-05-build-release-run")
        self._write_factor_canonical(root, "factor-12-admin-processes")
        self._write_factor_canonical(root, "factor-13-api-first")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # No residual factor assessment-vs-lane drift WARNING for the self-host shape.
        self.assertNotIn("no active review lane", result.stderr)

    def test_factor_surface_orphan_wrapper_fails_regardless_of_lane_set(self) -> None:
        """A wrapper with no matching canonical source is an orphan wrapper, even with an
        empty (retired) lane set."""
        root = self.copy_fixture()
        self._set_applicable_factors(root, [])
        # Wrapper exists but no canonical docs/agents/factor-07-port-binding.md.
        self._write_factor_wrapper(root, "factor-07-port-binding", frontmatter=True)
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("orphan wrapper", result.stderr)

    def test_factor_surface_wrapper_missing_frontmatter_fails(self) -> None:
        root = self.copy_fixture()
        self._set_applicable_factors(root, ["07"])
        self._write_factor_canonical(root, "factor-07-port-binding")
        self._write_factor_wrapper(root, "factor-07-port-binding", frontmatter=False)
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("missing YAML frontmatter", result.stderr)

    def test_factor_surface_no_active_lanes_no_repo_profile_is_noop(self) -> None:
        """No applicable_factors + no repo-profile -> the existence/drift halves are a no-op
        (base fixture stays green); a clean canonical+wrapper pair still passes."""
        root = self.copy_fixture()
        self._set_applicable_factors(root, [])
        self._write_factor_canonical(root, "factor-07-port-binding")
        self._write_factor_wrapper(root, "factor-07-port-binding", frontmatter=True)
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
            '      "shortcut": "Init Wavefoundry"\n'
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
        `.wavefoundry/framework/docs/lint-exclusions.md` for the operator-visible
        rationale per pattern."""
        for pattern in (".pytest_cache", ".mypy_cache", ".ruff_cache",
                        ".tox", ".coverage"):
            self.assertIn(
                pattern, self._exclusion_set,
                f"{pattern} must be in LINT_EXCLUDED_TRANSIENT_DIRS "
                "(see .wavefoundry/framework/docs/lint-exclusions.md)",
            )

    def test_exclusion_doc_exists_and_lists_each_pattern(self) -> None:
        """The operator-visible doc at .wavefoundry/framework/docs/lint-exclusions.md
        must enumerate every pattern in the exclusion set. Drift between the
        Python constant and the operator-facing doc is exactly what the doc
        exists to prevent — enterprise security review reads the doc, not
        the source."""
        # Resolve repo root from the test file location.
        repo_root = SCRIPTS_ROOT.parents[1].parent
        doc_path = repo_root / ".wavefoundry" / "framework" / "docs" / "lint-exclusions.md"
        self.assertTrue(doc_path.is_file(), f"missing {doc_path}")
        doc_text = doc_path.read_text(encoding="utf-8")
        for pattern in self._exclusion_set:
            self.assertIn(
                pattern, doc_text,
                f"{pattern} is in LINT_EXCLUDED_TRANSIENT_DIRS but not in "
                ".wavefoundry/framework/docs/lint-exclusions.md — security audit drift",
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

    def test_link_check_does_not_call_path_resolve(self) -> None:
        """Wave 1p9cf: the per-link hot loop must NOT call Path.resolve() (realpath, per-component
        syscalls) — that was the O(links) blowup behind the field >30s timeout."""
        import unittest.mock as mock
        self._write("docs/other.md", "# Other\n")
        body = "\n".join(f"- [ref{i}](other.md) and [miss{i}](missing-{i}.md)" for i in range(50))
        doc = self._write("docs/source.md", body + "\n")
        with mock.patch("pathlib.Path.resolve", side_effect=AssertionError("Path.resolve must not be called")) as m:
            result = self._check(self._tmp, doc)
        self.assertEqual(m.call_count, 0, "check_markdown_links must not call Path.resolve() per link")
        # Behavior intact: the 50 distinct missing targets are still flagged; the resolvable one is not.
        self.assertEqual(len(result), 50, result)
        self.assertTrue(all("broken link" in r for r in result))

    def test_root_escaping_link_is_skipped_not_flagged(self) -> None:
        """Wave 1p9cf: a link that normalizes outside the repo root is skipped (not flagged broken) —
        preserving the prior `relative_to(root)` escape behavior with lexical normpath containment."""
        doc = self._write("docs/source.md", "[escape](../../../../etc/hosts)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(result, [], "a root-escaping link must be skipped, not reported as broken")

    def test_dotdot_within_root_still_resolves(self) -> None:
        """A `..` link that stays inside the repo is resolved normally (normpath collapses it)."""
        self._write("docs/guide/intro.md", "# Intro\n")
        self._write("docs/ref.md", "# Ref\n")
        doc = self._write("docs/guide/source.md", "[up](../ref.md) and [gone](../missing.md)\n")
        result = self._check(self._tmp, doc)
        self.assertEqual(len(result), 1, result)
        self.assertIn("missing.md", result[0])

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
        # 1p9pk: the roster⇄evidence consistency check requires every rostered seat to have
        # recorded evidence outside the verdict line, so the consistent fixture records a
        # per-seat evidence bullet for each non-tolerance seat.
        wave_md = root / self.ACTIVE_WAVE
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8")
            + "\n## Review Checkpoints\n\n- **Prepare-phase Wave Council [prepare-council] — 2026-05-21: PASS** (moderator: wave-council; primer-depth: standard; seats: red-team, architecture-reviewer, security-reviewer, qa-reviewer, reality-checker; rotating-seat: none; strongest-challenge: red-team identified the remaining unknowns; strongest-alternative: keep the verdict structured and machine-readable)\n"
            + "\n## Prepare Review Evidence\n\n- architecture-reviewer: approved 2026-05-21 — boundaries coherent.\n- security-reviewer: approved 2026-05-21 — no trust boundary crossed.\n- qa-reviewer: approved 2026-05-21 — ACs testable.\n- reality-checker: approved 2026-05-21 — cited sites verified.\n",
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


class PrepareCouncilRosterEvidenceTests(unittest.TestCase):
    """1p9pk AC-3/AC-4: roster⇄evidence consistency check for prepare-council verdict lines.

    Pinned matching rule: literal role-token (or ``<stem> seat`` prose form) match; corpus =
    ## Prepare Review Evidence + ## Review Evidence + ## Review Checkpoints MINUS every
    structured verdict line (review-fix hardening: excluding only the matched line's own text
    let two pasted thin PASS lines mutually certify each other); ## Participants / ## Changes
    excluded by construction; tolerance set {red-team, wave-council}.
    """

    FROZEN_FIXTURE = TESTS_ROOT / "fixtures" / "prepare_council" / "1p9pe-wave-pre-corrective.md"

    def setUp(self) -> None:
        from wave_lint_lib.wave_validators import check_prepare_council_roster_evidence

        self._check = check_prepare_council_roster_evidence
        self._root = Path(tempfile.mkdtemp(prefix="wave-roster-evidence-"))

    def tearDown(self) -> None:
        shutil.rmtree(self._root)

    def _write_wave(self, text: str, folder: str = "zzzzz roster-fixture") -> Path:
        wave_dir = self._root / "docs" / "waves" / folder
        wave_dir.mkdir(parents=True, exist_ok=True)
        wave_md = wave_dir / "wave.md"
        wave_md.write_text(text, encoding="utf-8")
        return wave_md

    @staticmethod
    def _verdict(seats: str, rotating: str = "none") -> str:
        return (
            "- **Prepare-phase Wave Council [prepare-council] — 2026-07-01: PASS** "
            f"(moderator: wave-council; primer-depth: standard; seats: {seats}; "
            f"rotating-seat: {rotating}; strongest-challenge: the usual; "
            "strongest-alternative: none stronger)"
        )

    @staticmethod
    def _wave_text(checkpoints: str, prepare_evidence: str = "", review_evidence: str = "", status: str = "implementing") -> str:
        # Participants deliberately names the seats: a Role-column mention is a responsibility
        # assignment, not review evidence, and must never corroborate a roster claim.
        return (
            "# Wave Record\n\n"
            "Owner: Engineering\n"
            f"Status: {status}\n"
            "Last verified: 2026-07-01\n\n"
            "wave-id: `zzzzz roster-fixture`\n\n"
            "## Participants\n\n"
            "| Role | Responsibility |\n"
            "|------|----------------|\n"
            "| architecture-reviewer | Boundaries. |\n"
            "| qa-reviewer | ACs. |\n"
            "| performance-reviewer | Hot paths. |\n"
            "| docs-contract-reviewer | Contracts. |\n\n"
            "## Review Checkpoints\n\n"
            f"{checkpoints}\n\n"
            "## Review Evidence\n\n"
            f"{review_evidence}\n\n"
            "## Prepare Review Evidence\n\n"
            f"{prepare_evidence}\n"
        )

    # --- AC-3: the frozen pre-corrective 1p9pe snapshot ---

    def test_frozen_pre_corrective_1p9pe_snapshot_trips(self) -> None:
        """AC-3: the frozen pre-corrective wave record (captured from git history at the plan
        commit) trips the check — its thin PASS roster names architecture-reviewer with no
        recorded evidence anywhere in the record. (Status patched to implementing: the frozen
        snapshot predates activation, and the check binds when the wave opens.)"""
        frozen = self.FROZEN_FIXTURE.read_text(encoding="utf-8")
        self.assertIn("Status: planned", frozen)  # provenance: pre-activation snapshot
        self._write_wave(frozen.replace("Status: planned", "Status: implementing"))
        errors, warnings = self._check(self._root)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("architecture-reviewer", warnings[0])
        # Seats with evidence in the record (corrective checkpoint prose, Prepare Review
        # Evidence) are NOT flagged.
        self.assertNotIn("qa-reviewer", warnings[0])
        self.assertNotIn("reality-checker", warnings[0])
        self.assertNotIn("security-reviewer", warnings[0])

    def test_truly_pre_corrective_shape_flags_all_three(self) -> None:
        """AC-3: with the corrective re-review bullets removed (the record as it stood when the
        thin PASS was the only prepare-council entry), all three unevidenced roster seats are
        flagged: architecture-reviewer, qa-reviewer, reality-checker. security-reviewer is
        evidenced by ## Prepare Review Evidence and is not flagged."""
        frozen = self.FROZEN_FIXTURE.read_text(encoding="utf-8")
        reduced_lines = []
        in_checkpoints = False
        for line in frozen.splitlines():
            if line.startswith("## "):
                in_checkpoints = line.strip() == "## Review Checkpoints"
            if in_checkpoints and line.startswith("- ") and "PASS**" not in line:
                continue  # drop the corrective READY-WITH-NOTES bullets
            if in_checkpoints and line.startswith("  - "):
                continue  # drop their sub-bullets
            reduced_lines.append(line)
        reduced = "\n".join(reduced_lines).replace("Status: planned", "Status: implementing")
        self._write_wave(reduced)
        errors, warnings = self._check(self._root)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)
        for seat in ("architecture-reviewer", "qa-reviewer", "reality-checker"):
            self.assertIn(seat, warnings[0])
        self.assertNotIn("security-reviewer", warnings[0])

    # --- AC-4: consistent records and tolerance cases ---

    def test_consistent_record_passes(self) -> None:
        checkpoints = self._verdict("red-team, architecture-reviewer, qa-reviewer")
        evidence = (
            "- architecture-reviewer: approved 2026-07-01 — boundaries hold.\n"
            "- qa-reviewer: approved 2026-07-01 — ACs testable.\n"
        )
        self._write_wave(self._wave_text(checkpoints, prepare_evidence=evidence))
        self.assertEqual(self._check(self._root), ([], []))

    def test_red_team_tolerated_without_dedicated_evidence(self) -> None:
        """red-team is the adversarial primer; its output folds into strongest-challenge."""
        checkpoints = self._verdict("red-team, qa-reviewer")
        self._write_wave(self._wave_text(checkpoints, prepare_evidence="- qa-reviewer: approved — checked.\n"))
        self.assertEqual(self._check(self._root), ([], []))

    def test_wave_council_tolerated_without_dedicated_evidence(self) -> None:
        """wave-council is the moderator; synthesis is the verdict line itself."""
        checkpoints = self._verdict("wave-council, qa-reviewer")
        self._write_wave(self._wave_text(checkpoints, prepare_evidence="- qa-reviewer: approved — checked.\n"))
        self.assertEqual(self._check(self._root), ([], []))

    def test_seat_named_only_in_own_verdict_line_does_not_self_certify(self) -> None:
        """AC-4/pinned rule: the matched verdict line's own text is excluded from the corpus —
        a strongest-challenge mention inside the same line is not evidence."""
        checkpoints = (
            "- **Prepare-phase Wave Council [prepare-council] — 2026-07-01: PASS** "
            "(moderator: wave-council; primer-depth: standard; seats: red-team, performance-reviewer; "
            "rotating-seat: none; strongest-challenge: performance-reviewer raised the hot-path concern; "
            "strongest-alternative: none stronger)"
        )
        self._write_wave(self._wave_text(checkpoints))
        errors, warnings = self._check(self._root)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("performance-reviewer", warnings[0])

    def test_two_pasted_thin_pass_lines_do_not_mutually_certify(self) -> None:
        """Review-fix hardening (security S6-i + red-team primer): with only the matched
        verdict line excluded, two near-identical thin PASS lines corroborated each other's
        rosters (each line's seat tokens satisfied the other's check → 0 warnings). ALL
        structured verdict lines are excluded from the corpus, so both rosters now flag."""
        first = self._verdict("red-team, architecture-reviewer, qa-reviewer")
        second = first.replace("2026-07-01", "2026-07-02")
        self.assertNotEqual(first, second)  # near-identical, not byte-identical
        self._write_wave(self._wave_text(first + "\n" + second))
        errors, warnings = self._check(self._root)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 2, warnings)
        for warning in warnings:
            self.assertIn("architecture-reviewer", warning)
            self.assertIn("qa-reviewer", warning)

    def test_seat_evidenced_in_other_checkpoint_bullet_passes(self) -> None:
        """AC-4: a literal role-token mention in a checkpoint bullet other than the verdict
        line corroborates the seat."""
        checkpoints = (
            self._verdict("red-team, performance-reviewer")
            + "\n- performance-reviewer follow-up: hot-path cost reviewed, no findings."
        )
        self._write_wave(self._wave_text(checkpoints))
        self.assertEqual(self._check(self._root), ([], []))

    def test_seat_evidenced_by_stem_seat_prose_passes(self) -> None:
        """Live-corpus convention: checkpoint prose records per-seat findings as
        '<Stem> seat ...' ('Architecture seat flagged ...'); that corroborates the seat."""
        checkpoints = (
            self._verdict("red-team, architecture-reviewer")
            + "\n- Readiness narrative: Architecture seat flagged the layering decision as deferred."
        )
        self._write_wave(self._wave_text(checkpoints))
        self.assertEqual(self._check(self._root), ([], []))

    def test_participants_table_does_not_corroborate(self) -> None:
        """AC-3 exclusion: the base wave text's Participants table names every seat; a roster
        seat with no evidence outside it is still flagged."""
        checkpoints = self._verdict("red-team, docs-contract-reviewer")
        self._write_wave(self._wave_text(checkpoints))
        errors, warnings = self._check(self._root)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("docs-contract-reviewer", warnings[0])

    def test_unevidenced_rotating_seat_is_flagged(self) -> None:
        checkpoints = self._verdict("red-team, qa-reviewer", rotating="docs-contract-reviewer")
        self._write_wave(self._wave_text(checkpoints, prepare_evidence="- qa-reviewer: approved — checked.\n"))
        errors, warnings = self._check(self._root)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("docs-contract-reviewer", warnings[0])

    def test_verbatim_template_paste_is_flagged(self) -> None:
        """A verdict line pasted from the wave_prepare template (placeholder wording intact)
        still exposes its example seat tokens as unevidenced roster claims."""
        checkpoints = self._verdict(
            "<replace with the seats actually run, each at most once, e.g. red-team, "
            "architecture-reviewer, security-reviewer, qa-reviewer, reality-checker>"
        )
        self._write_wave(self._wave_text(checkpoints))
        errors, warnings = self._check(self._root)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)
        for seat in ("architecture-reviewer", "security-reviewer", "qa-reviewer"):
            self.assertIn(seat, warnings[0])

    # --- Scope: statuses outside active/implementing are not checked ---

    def test_planned_and_closed_waves_are_skipped(self) -> None:
        checkpoints = self._verdict("red-team, architecture-reviewer, qa-reviewer")
        for status, folder in (("planned", "zzzzz planned-fixture"), ("closed", "zzzzz closed-fixture")):
            self._write_wave(self._wave_text(checkpoints, status=status), folder=folder)
        self.assertEqual(self._check(self._root), ([], []))

    def test_active_wave_is_checked(self) -> None:
        checkpoints = self._verdict("red-team, architecture-reviewer")
        self._write_wave(self._wave_text(checkpoints, status="active"))
        errors, warnings = self._check(self._root)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("architecture-reviewer", warnings[0])

    def test_freeform_prepare_council_mention_without_structured_verdict_is_not_checked(self) -> None:
        """Only structured PASS/PASS WITH NOTES/BLOCKED verdict lines carry a machine-checkable
        roster; corrective or narrative bullets that mention prepare-council are not parsed."""
        checkpoints = (
            "- Corrective prepare-council re-review — 2026-07-01: READY-WITH-NOTES "
            "(seats actually run: reality-checker only; roster of the earlier pass was thin)"
        )
        self._write_wave(self._wave_text(checkpoints))
        self.assertEqual(self._check(self._root), ([], []))


class PrepareCouncilVerdictRegexParityTests(unittest.TestCase):
    """Wave 1p9pe delivery-council fix-now lane: `_PREPARE_COUNCIL_VERDICT_LINE_RE`
    in wave_validators deliberately mirrors `_PREPARE_COUNCIL_VERDICT_RE` in
    server_impl (the wave_prepare parser). The two patterns are intentionally
    identical; this parity pin fails loudly if either side is edited without
    the other, so the lint validator and the prepare gate never diverge on
    which verdict lines they consider structured."""

    def test_verdict_line_patterns_are_identical(self) -> None:
        # Import order matters: server_impl evicts wave_lint_lib modules from
        # sys.modules at import time (its reload hygiene), so load it first.
        import server_impl

        from wave_lint_lib import wave_validators

        self.assertEqual(
            wave_validators._PREPARE_COUNCIL_VERDICT_LINE_RE.pattern,
            server_impl._PREPARE_COUNCIL_VERDICT_RE.pattern,
            "prepare-council verdict-line regexes must stay literally identical "
            "between the lint validator and the wave_prepare parser",
        )
        self.assertEqual(
            wave_validators._PREPARE_COUNCIL_VERDICT_LINE_RE.flags,
            server_impl._PREPARE_COUNCIL_VERDICT_RE.flags,
            "verdict-line regex flags must match (both IGNORECASE)",
        )


class CouncilSeedVerificationContractTests(unittest.TestCase):
    """1p9pk AC-5: the council-review seed carries the code-grounded verification and
    roster-honesty contracts; the moderator and review-hub seeds point at them."""

    SEEDS_DIR = SCRIPTS_ROOT.parent / "seeds"

    def test_seed_237_requires_code_grounded_verification(self) -> None:
        text = (self.SEEDS_DIR / "237-council-review.prompt.md").read_text(encoding="utf-8")
        self.assertIn("Verify code-grounded", text)
        self.assertIn("sites and symbols must resolve", text)
        self.assertIn("censuses must be complete", text)

    def test_seed_237_carries_roster_honesty_contract(self) -> None:
        text = (self.SEEDS_DIR / "237-council-review.prompt.md").read_text(encoding="utf-8")
        self.assertIn("Roster honesty", text)
        self.assertIn("seats *actually run*, each at most once", text)
        self.assertIn("does not self-certify", text)

    def test_seed_215_cross_references_recording_contract(self) -> None:
        text = (self.SEEDS_DIR / "215-wave-council.prompt.md").read_text(encoding="utf-8")
        self.assertIn("`prepare-council` recording contract in `237-council-review.prompt.md`", text)

    def test_seed_007_points_at_roster_evidence_consistency(self) -> None:
        text = (self.SEEDS_DIR / "007-review-system-overview.md").read_text(encoding="utf-8")
        self.assertIn("roster⇄evidence consistency", text)
        self.assertIn("per-seat findings (or an explicit no-findings note)", text)


class ChangeIdDeferralForPlannedWavesTests(unittest.TestCase):
    """Wave 1p3dk / 1p3do AC-3: a freshly-created `Status: planned` wave with
    an empty `## Changes` section does NOT emit the `missing stable Change ID
    declaration` error. The deferral disables the moment Status moves past
    planned OR the first Change ID appears."""

    def _wave_doc(self, status: str, changes_body: str) -> str:
        """Build a minimal wave doc with the requested status and Changes body."""
        return (
            "# Wave Record\n\n"
            "Owner: Engineering\n"
            f"Status: {status}\n"
            "Last verified: 2026-06-05\n\n"
            "wave-id: `1p3dk test-deferral`\n"
            "Title: Test Deferral\n\n"
            "## Objective\n\n"
            "Test the deferral behavior.\n\n"
            "## Changes\n\n"
            f"{changes_body}"
            "## Wave Summary\n\n"
            "Test wave for deferral logic.\n\n"
            "## Journal Watchpoints\n\n"
            "- Test watchpoint.\n\n"
            "## Review Evidence\n\n"
            "- operator-signoff: pending\n\n"
            "## Dependencies\n\n"
            "- None.\n"
        )

    def _check(self, doc_text: str) -> list[str]:
        """Invoke the wave validator directly against a synthesized wave doc."""
        import sys
        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib.wave_validators import check_wave_docs

        with tempfile.TemporaryDirectory(prefix="wave-deferral-") as tmp:
            root = Path(tmp)
            wave_dir = root / "docs" / "waves" / "1p3dk test-deferral"
            wave_dir.mkdir(parents=True)
            (wave_dir / "wave.md").write_text(doc_text, encoding="utf-8")
            return check_wave_docs(root)

    def test_planned_wave_with_empty_changes_passes(self):
        """AC-3 happy path: deferral fires when both conditions hold."""
        failures = self._check(self._wave_doc("planned", ""))
        change_id_errors = [
            f for f in failures
            if "missing stable `Change ID` declaration" in f
        ]
        self.assertEqual(
            change_id_errors, [],
            f"Change-ID error should be deferred for planned wave with empty "
            f"Changes; got {change_id_errors}",
        )

    def test_planned_wave_with_admitted_change_passes(self):
        """Sanity: a planned wave with a real Change ID also passes (no
        deferral needed because the rule is satisfied)."""
        body = (
            "Change ID: `1p3dm-enh sample`\n"
            "Change Status: `planned`\n\n"
        )
        failures = self._check(self._wave_doc("planned", body))
        change_id_errors = [
            f for f in failures
            if "missing stable `Change ID` declaration" in f
        ]
        self.assertEqual(change_id_errors, [])

    def test_active_wave_with_empty_changes_fails(self):
        """AC-3 negative: deferral does NOT apply once status moves past
        `planned`. An active wave without changes is still a lint failure."""
        failures = self._check(self._wave_doc("active", ""))
        change_id_errors = [
            f for f in failures
            if "missing stable `Change ID` declaration" in f
        ]
        self.assertNotEqual(
            change_id_errors, [],
            "Change-ID error must fire for non-planned waves with empty Changes",
        )

    def test_closed_wave_with_empty_changes_fails(self):
        """AC-3 negative: closed waves never benefit from the deferral."""
        failures = self._check(self._wave_doc("closed", ""))
        change_id_errors = [
            f for f in failures
            if "missing stable `Change ID` declaration" in f
        ]
        self.assertNotEqual(change_id_errors, [])

    def test_deferral_is_case_insensitive_on_status(self):
        """Status comparison must be case-insensitive (matches existing
        validator helper that casefolds the status value)."""
        failures = self._check(self._wave_doc("PLANNED", ""))
        change_id_errors = [
            f for f in failures
            if "missing stable `Change ID` declaration" in f
        ]
        self.assertEqual(change_id_errors, [])


class SeedPrefixUniquenessTests(unittest.TestCase):
    """Wave 1p3dk / 1p3dm (field feedback 2026-06-04): the framework
    seed-prefix convention is converted from a soft naming standard to an
    enforced unique key. Two seeds sharing the same `NNN-` prefix is now a
    docs-lint failure with both filenames named explicitly."""

    def setUp(self) -> None:
        import sys

        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib.core_validators import check_seed_prefix_uniqueness

        self._check = check_seed_prefix_uniqueness
        self._root = Path(tempfile.mkdtemp(prefix="wave-check-seed-prefix-"))
        self._seeds_dir = self._root / ".wavefoundry" / "framework" / "seeds"
        self._seeds_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self._root)

    def _plant(self, name: str, body: str = "# stub\n") -> Path:
        path = self._seeds_dir / name
        path.write_text(body, encoding="utf-8")
        return path

    def test_no_failures_when_seeds_dir_missing(self) -> None:
        """No `.wavefoundry/framework/seeds/` dir → no work, no failures.
        Important for consumer projects that vendor the framework differently."""
        empty_root = Path(tempfile.mkdtemp(prefix="wave-check-seed-prefix-empty-"))
        try:
            self.assertEqual(self._check(empty_root), [])
        finally:
            shutil.rmtree(empty_root)

    def test_no_failures_when_all_prefixes_unique(self) -> None:
        """AC-4: clean state passes — empty failure list."""
        self._plant("100-foo.prompt.md")
        self._plant("200-bar.prompt.md")
        self._plant("237-council-review.prompt.md")
        self.assertEqual(self._check(self._root), [])

    def test_collision_fails_with_both_filenames(self) -> None:
        """AC-5: error names both colliding filenames so the operator can
        immediately identify the offending pair without re-grepping."""
        self._plant("230-author-spec.prompt.md")
        self._plant("230-council-review.prompt.md")
        failures = self._check(self._root)
        self.assertEqual(len(failures), 1)
        self.assertIn("230-", failures[0])
        self.assertIn("230-author-spec.prompt.md", failures[0])
        self.assertIn("230-council-review.prompt.md", failures[0])
        self.assertIn("seed prefix collision", failures[0])

    def test_three_way_collision_reports_all_names(self) -> None:
        """Triple-collision case: all three names appear in the single error."""
        self._plant("050-alpha.prompt.md")
        self._plant("050-beta.prompt.md")
        self._plant("050-gamma.prompt.md")
        failures = self._check(self._root)
        self.assertEqual(len(failures), 1)
        for name in ("050-alpha", "050-beta", "050-gamma"):
            self.assertIn(name, failures[0])

    def test_non_prefixed_files_ignored(self) -> None:
        """Files without an `NNN-` prefix (e.g., README.md) are not flagged
        and do not crash the check."""
        self._plant("README.md")
        self._plant("notes.md")
        self._plant("100-foo.prompt.md")
        self.assertEqual(self._check(self._root), [])

    def test_repo_self_hosting_state_is_clean(self) -> None:
        """Regression guard against the 1p3dm rename: this repo's own
        `.wavefoundry/framework/seeds/` must not regress to a collision state."""
        repo_root = SCRIPTS_ROOT.parents[1].parent
        self.assertEqual(self._check(repo_root), [])


class SeedPrefixUniquenessCliIntegrationTests(unittest.TestCase):
    """End-to-end via docs-lint subprocess on the live repo. AC-6:
    `check_seed_prefix_uniqueness` is auto-invoked in the docs-lint pipeline
    (no special flag required)."""

    def test_cli_imports_the_check(self) -> None:
        """The CLI module imports the new check from core_validators —
        a structural regression guard."""
        import sys
        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib.cli import main  # noqa: F401 — import smoke test
        import wave_lint_lib.cli as cli_module
        self.assertTrue(
            hasattr(cli_module, "check_seed_prefix_uniqueness"),
            "wave_lint_lib.cli must import check_seed_prefix_uniqueness so the "
            "docs-lint pipeline auto-runs the prefix check (1p3dm AC-6)",
        )


class IncrementalDocsLintTests(DocsLintFixtureTests):
    """Wave 1p9c1: incremental (`--changed`) post-edit docs-lint self-detects the git working-tree
    changed set (reusing secrets' `_get_changed_files`) and runs only the per-file validators on
    changed docs, skipping the corpus-wide checks; a changed config file falls back to the full lint;
    an empty/non-git changed set is a safe `ok` no-op. The authoritative full lint (no `--changed`) is
    unchanged."""

    def _cli(self):
        import sys
        sys.path.insert(0, str(SCRIPTS_ROOT))
        import wave_lint_lib.cli as cli
        return cli

    def _full_args(self):
        import argparse
        return argparse.Namespace(
            scan_all=False,
            write_migration_audit=False,
            migration_audit_path="docs/reports/wave-migration-audit.md",
            changed=True,
        )

    def test_incremental_skips_corpus_checks_that_full_reports(self) -> None:
        """AC-1: with a clean changed doc, incremental does NOT run a corpus-wide check (here: the
        required-files check), while the full lint DOES report the missing required file."""
        import unittest.mock as mock
        root = self.copy_fixture()
        cli = self._cli()
        try:
            # Introduce a corpus-wide defect: remove a required file.
            (root / "docs/README.md").unlink()
            clean_changed = [root / "docs/agents/journals/wave-coordinator.md"]
            with mock.patch.object(cli, "_get_changed_files", return_value=clean_changed):
                inc_failures, inc_warnings = cli._run_incremental_checks(root)
            full_failures, _fw, _fi = cli._run_full_checks(root, self._full_args())
        finally:
            shutil.rmtree(root)
        # Incremental: the corpus-wide required-files error is NOT reported (check skipped)…
        self.assertFalse(
            any("missing required" in f for f in inc_failures),
            f"incremental must skip the corpus required-files check; got {inc_failures}",
        )
        # …and a clean changed journal yields no per-file failures either.
        self.assertEqual(inc_failures, [], inc_failures)
        # Full lint DOES report the missing required file.
        self.assertTrue(
            any("missing required" in f for f in full_failures),
            f"full lint must still report the missing required file; got {full_failures}",
        )

    def test_incremental_catches_per_file_defect_in_changed_doc(self) -> None:
        """AC-2: incremental still catches a per-file defect in a changed doc — a journal missing a
        required section reports the same error the full lint would."""
        import unittest.mock as mock
        root = self.copy_fixture()
        cli = self._cli()
        journal = root / "docs/agents/journals/wave-coordinator.md"
        try:
            text = journal.read_text(encoding="utf-8")
            self.assertIn("## Governance", text, "fixture precondition: journal has ## Governance")
            # Rename the heading to something that does NOT contain the "## Governance" substring so the
            # required-section check actually fires.
            journal.write_text(text.replace("## Governance", "## Ruleset"), encoding="utf-8")
            with mock.patch.object(cli, "_get_changed_files", return_value=[journal]):
                inc_failures, _ = cli._run_incremental_checks(root)
        finally:
            shutil.rmtree(root)
        self.assertTrue(
            any("missing required section `## Governance`" in f for f in inc_failures),
            f"incremental must catch the journal's missing ## Governance; got {inc_failures}",
        )

    def test_incremental_config_change_falls_back_to_full(self) -> None:
        """AC-3: a changed config/corpus file returns None (signal to run the full lint)."""
        import unittest.mock as mock
        root = self.copy_fixture()
        cli = self._cli()
        try:
            changed = [root / "docs/workflow-config.json"]
            with mock.patch.object(cli, "_get_changed_files", return_value=changed):
                result = cli._run_incremental_checks(root)
        finally:
            shutil.rmtree(root)
        self.assertIsNone(result, "a changed config file must signal the full-lint fallback (None)")

    def test_incremental_empty_and_non_doc_changed_set_is_noop(self) -> None:
        """AC-4: an empty changed set, or one with no docs/config files, is a safe ok no-op."""
        import unittest.mock as mock
        root = self.copy_fixture()
        cli = self._cli()
        try:
            with mock.patch.object(cli, "_get_changed_files", return_value=[]):
                empty_result = cli._run_incremental_checks(root)
            code_only = [root / "src/example.py"]
            with mock.patch.object(cli, "_get_changed_files", return_value=code_only):
                code_result = cli._run_incremental_checks(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(empty_result, ([], []), "empty changed set must be an ok no-op")
        self.assertEqual(code_result, ([], []), "a non-doc/non-config changed set must be an ok no-op")

    def test_incremental_canonical_event_change_revalidates_owning_wave(self) -> None:
        """A changed canonical ledger is not a generic non-doc no-op."""
        import unittest.mock as mock
        root = self.copy_fixture()
        cli = self._cli()
        try:
            source_wave = next((root / "docs" / "waves").rglob("wave.md"))
            wave_dir = root / "docs" / "waves" / "00abc incremental-event-fixture"
            wave_dir.mkdir()
            (wave_dir / "wave.md").write_text(
                source_wave.read_text(encoding="utf-8").replace(
                    "00057 routine-behavior-contract", "00abc incremental-event-fixture"
                ),
                encoding="utf-8",
            )
            events = wave_dir / "events.jsonl"
            events.write_bytes(b"{not-json}\n")
            with mock.patch.object(cli, "_get_changed_files", return_value=[events]):
                failures, _ = cli._run_incremental_checks(root)
        finally:
            shutil.rmtree(root)
        self.assertTrue(
            any("events.jsonl" in failure and "invalid JSON" in failure for failure in failures),
            failures,
        )

    def test_changed_flag_on_non_git_tree_is_ok_noop_end_to_end(self) -> None:
        """AC-4 (end-to-end): `docs_lint.py --changed` on a non-git fixture (git reports nothing) exits
        0 without falling through to a whole-tree scan — and (review-fix, 1p9pe follow-up hardening)
        the summary line says `skipped`, not `ok`, so an advisory no-op is distinguishable from
        checked-and-clean."""
        root = self.copy_fixture()
        try:
            result = self.run_docs_lint_with_args(root, "--changed")
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: skipped (no git changed-set available)", result.stdout)
        self.assertNotIn("docs-lint: ok", result.stdout)


class RelativeToRootCrossPlatformTests(unittest.TestCase):
    """Wave 1p9cf: `relative_to_root` must return forward-slash (POSIX) relative paths on ALL platforms so
    the validators' `rel.startswith("docs/…/")` forward-slash comparisons fire on Windows/WSL2 and lint
    messages honor the keep-`/` directive."""

    def _fn(self):
        import sys
        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib.helpers import relative_to_root
        return relative_to_root

    def test_posix_nested_path_uses_forward_slashes(self) -> None:
        relative_to_root = self._fn()
        root = Path("/repo")
        rel = relative_to_root(root, Path("/repo/docs/reports/x.md"))
        self.assertEqual(rel, "docs/reports/x.md")
        self.assertNotIn("\\", rel)
        self.assertTrue(rel.startswith("docs/reports/"), "the skip-prefix comparison must match")

    def test_windows_path_normalizes_to_forward_slashes(self) -> None:
        """Deterministically exercise the Windows flavour on any host by driving the REAL
        `relative_to_root` with `PureWindowsPath` inputs (a pure path needs no filesystem, so this runs on
        POSIX CI). This hits production's `.relative_to(...).as_posix()` code path and FAILS against a
        `str()` revert — which would return backslashes that silently break the `docs/…/` skip-prefix
        comparisons on Windows/WSL2. (Wave 1p9bm pre-close review: the prior version hand-rolled the
        transformation and never called the function, so a revert went undetected — a vacuous guard.)"""
        from pathlib import PureWindowsPath
        relative_to_root = self._fn()
        rel = relative_to_root(PureWindowsPath(r"C:\repo"), PureWindowsPath(r"C:\repo\docs\reports\x.md"))
        self.assertEqual(rel, "docs/reports/x.md")
        self.assertNotIn("\\", rel)
        self.assertTrue(rel.startswith("docs/reports/"), "the skip-prefix comparison must match on Windows")
        # Regression guard: the pre-1p9cf `str()` behavior would produce backslashes here that break the skip.
        old = str(PureWindowsPath(r"C:\repo\docs\reports\x.md").relative_to(PureWindowsPath(r"C:\repo")))
        self.assertFalse(old.startswith("docs/reports/"), "str() backslashes break the skip — must not regress to str()")


class PerfCacheAndTimingsTests(DocsLintFixtureTests):
    """Wave 1p9c6: a transparent `helpers.read_text` cache (keyed on `(path, st_mtime_ns, st_size)`)
    dedupes the redundant per-run reads, and an opt-in `--timings` flag emits per-phase wall-clock
    without changing the pass/fail or exit contract."""

    def _helpers(self):
        import sys
        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib import helpers
        return helpers

    def test_read_cache_returns_cached_content_when_stat_identity_unchanged(self) -> None:
        """AC-1: a repeated read of a file whose (mtime_ns, size) is unchanged returns the cached content
        without re-reading — proven by mutating the bytes to a same-length value, restoring the mtime, and
        observing the ORIGINAL content still returned."""
        import os
        helpers = self._helpers()
        tmp = Path(tempfile.mkdtemp(prefix="wave-readcache-"))
        try:
            f = tmp / "doc.md"
            f.write_text("AAAA", encoding="utf-8")
            helpers.read_text_cache_clear()
            first = helpers.read_text(f)
            st = f.stat()
            # Overwrite with a DIFFERENT same-length value, then restore the mtime so the (mtime_ns, size)
            # key is unchanged → the cache must serve the original content (i.e. it did not re-read).
            f.write_text("BBBB", encoding="utf-8")
            os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns))
            self.assertEqual(f.stat().st_size, st.st_size, "precondition: same size")
            second = helpers.read_text(f)
        finally:
            helpers.read_text_cache_clear()
            shutil.rmtree(tmp)
        self.assertEqual(first, "AAAA")
        self.assertEqual(second, "AAAA", "cache must serve the original content when stat identity is unchanged")

    def test_read_cache_invalidates_when_stat_identity_changes(self) -> None:
        """AC-2: a file whose (mtime_ns, size) changed is re-read (no stale content)."""
        helpers = self._helpers()
        tmp = Path(tempfile.mkdtemp(prefix="wave-readcache-"))
        try:
            f = tmp / "doc.md"
            f.write_text("AAAA", encoding="utf-8")
            helpers.read_text_cache_clear()
            self.assertEqual(helpers.read_text(f), "AAAA")
            # Different length → size changes → key changes → re-read.
            f.write_text("BBBBB", encoding="utf-8")
            self.assertEqual(helpers.read_text(f), "BBBBB", "cache must re-read when (mtime_ns, size) changed")
        finally:
            helpers.read_text_cache_clear()
            shutil.rmtree(tmp)

    def test_timings_emits_per_phase_and_total_and_preserves_contract(self) -> None:
        """AC-4: `--timings` prints TIMING per phase + total to stderr, keeps `docs-lint: ok` and exit 0;
        absent the flag there are no TIMING lines."""
        root = self.copy_fixture()
        try:
            timed = self.run_docs_lint_with_args(root, "--timings")
            plain = self.run_docs_lint_with_args(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(timed.returncode, 0, timed.stdout + timed.stderr)
        self.assertIn("docs-lint: ok", timed.stdout)
        self.assertIn("TIMING: total ", timed.stderr)
        self.assertIn("TIMING: corpus ", timed.stderr)
        self.assertIn("TIMING: metadata ", timed.stderr)
        self.assertIn("TIMING: links ", timed.stderr)
        # Without the flag: identical pass + no timing lines.
        self.assertEqual(plain.returncode, 0, plain.stdout + plain.stderr)
        self.assertIn("docs-lint: ok", plain.stdout)
        self.assertNotIn("TIMING:", plain.stderr)

    def test_timings_is_inert_in_incremental_mode(self) -> None:
        """AC-5: `--changed --timings` on a non-git fixture is an exit-0 no-op with NO timing lines
        (the incremental hot path stays quiet). The summary line reports `skipped` on a non-git
        fixture (review-fix, 1p9pe follow-up hardening)."""
        root = self.copy_fixture()
        try:
            result = self.run_docs_lint_with_args(root, "--changed", "--timings")
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: skipped (no git changed-set available)", result.stdout)
        self.assertNotIn("TIMING:", result.stderr)


class DocsLintFileSizeGuardTests(DocsLintFixtureTests):
    """Wave 1p9cj: an oversized `docs/**` doc has its content validators skipped with a loud
    non-blocking WARNING (never a silent skip, never a blocking ERROR), matching the secrets/indexing
    file-size caps. Configurable via `docs_lint.max_file_bytes`, default 5 MB."""

    def _set_cap(self, root: Path, cap: int) -> None:
        config_path = root / "docs" / "workflow-config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        dl = config.get("docs_lint")
        if not isinstance(dl, dict):
            dl = {}
            config["docs_lint"] = dl
        dl["max_file_bytes"] = cap
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

    def _write_oversized_broken_doc(self, root: Path, rel: str, filler_bytes: int) -> None:
        # A doc with NO metadata (would normally fail check_metadata) + padding to exceed the cap.
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Big\n\n" + ("x " * (filler_bytes // 2)) + "\n", encoding="utf-8")

    def test_oversized_doc_warns_and_is_skipped_not_failed(self) -> None:
        """AC-1/AC-2: an oversized doc that would otherwise fail a per-file check produces a size WARNING
        (not an ERROR) and docs-lint still exits 0 — its content validators were skipped."""
        root = self.copy_fixture()
        try:
            self._set_cap(root, 2048)  # 2 KB
            self._write_oversized_broken_doc(root, "docs/huge-generated.md", 8192)  # ~8 KB, no metadata
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)
        self.assertIn("exceeds the docs-lint file-size cap", result.stderr)
        self.assertIn("docs/huge-generated.md", result.stderr)
        # It must be a WARNING, and NOT flagged for its missing metadata (validators were skipped).
        self.assertIn("WARNING:", result.stderr)
        self.assertNotIn("docs/huge-generated.md: missing or invalid", result.stderr)

    def test_under_cap_doc_is_still_validated(self) -> None:
        """Control: the SAME broken doc UNDER the cap is validated normally (its metadata error fires) —
        proving the guard only skips genuinely oversized docs."""
        root = self.copy_fixture()
        try:
            self._set_cap(root, 5 * 1024 * 1024)  # 5 MB — the small doc is well under
            self._write_oversized_broken_doc(root, "docs/small-broken.md", 200)  # ~200 B, no metadata
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("docs/small-broken.md: missing or invalid", result.stderr)
        self.assertNotIn("exceeds the docs-lint file-size cap", result.stderr)

    def test_default_cap_produces_no_size_warnings(self) -> None:
        """AC-4: with no override, the base fixture (all small docs) emits zero size warnings."""
        root = self.copy_fixture()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("exceeds the docs-lint file-size cap", result.stderr)

    def test_cap_reader_override_and_fail_safe(self) -> None:
        """AC-3: the config override is read; a malformed/missing value falls back to the 5 MB default."""
        import sys
        sys.path.insert(0, str(SCRIPTS_ROOT))
        import wave_lint_lib.cli as cli
        from wave_lint_lib.constants import DOCS_LINT_MAX_FILE_BYTES_DEFAULT
        root = self.copy_fixture()
        try:
            self._set_cap(root, 123456)
            self.assertEqual(cli._docs_lint_max_file_bytes(root), 123456)
            # Malformed (string / bool / zero) → fallback.
            for bad in ("nope", True, 0, -5):
                config_path = root / "docs" / "workflow-config.json"
                config = json.loads(config_path.read_text(encoding="utf-8"))
                config["docs_lint"] = {"max_file_bytes": bad}
                config_path.write_text(json.dumps(config), encoding="utf-8")
                self.assertEqual(cli._docs_lint_max_file_bytes(root), DOCS_LINT_MAX_FILE_BYTES_DEFAULT,
                                 f"bad value {bad!r} must fall back to default")
        finally:
            shutil.rmtree(root)

    def test_incremental_mode_skips_oversized_changed_doc(self) -> None:
        """Wave 1p9bm pre-close review: the file-size guard's INCREMENTAL arm (`_run_incremental_checks`,
        previously untested — the full-lint arm alone was covered). An oversized *changed* doc is skipped
        with a size WARNING and no per-file ERROR, mirroring the tested full-lint path; a dropped guard
        would otherwise pull the doc through the validators silently."""
        import sys, unittest.mock as mock
        sys.path.insert(0, str(SCRIPTS_ROOT))
        import wave_lint_lib.cli as cli
        root = self.copy_fixture()
        try:
            self._set_cap(root, 2048)  # 2 KB
            # An oversized journal that WOULD fail its structural checks (no required sections) if not skipped.
            journal = root / "docs/agents/journals/huge-generated.md"
            self._write_oversized_broken_doc(root, "docs/agents/journals/huge-generated.md", 8192)  # ~8 KB
            with mock.patch.object(cli, "_get_changed_files", return_value=[journal]):
                result = cli._run_incremental_checks(root)
        finally:
            shutil.rmtree(root)
        self.assertIsNotNone(result, "no config file in the changed set → incremental, not full-lint fallback")
        failures, warnings = result
        self.assertTrue(any("exceeds the docs-lint file-size cap" in w for w in warnings),
                        f"expected a size WARNING; got {warnings}")
        self.assertTrue(any("huge-generated.md" in w for w in warnings), warnings)
        self.assertFalse(any("huge-generated.md" in f for f in failures),
                         f"the oversized changed doc's content validators must be skipped; got {failures}")


class LifecycleIdPolicyValidatorTests(unittest.TestCase):
    """Wave 1p9q0 — `_check_lifecycle_id_policy` v2 rules mirror the loader so
    docs-lint catches a hand-edited malformed v2 block before a mint does."""

    @classmethod
    def setUpClass(cls):
        # Order-independent import (delivery review): don't rely on another
        # class's setUp having inserted SCRIPTS_ROOT into sys.path.
        import sys
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))

    def _check(self, policy):
        from wave_lint_lib.core_validators import _check_lifecycle_id_policy
        return _check_lifecycle_id_policy({"lifecycle_id_policy": policy})

    def test_valid_v1_block_passes(self):
        self.assertEqual(self._check({"epoch_utc": "2020-02-02T02:02:00Z",
                                      "hour_offset": 0, "prefix_width": 5}), [])

    def test_valid_v2_block_passes(self):
        self.assertEqual(self._check({"epoch_utc": "2026-07-03T00:00:00Z",
                                      "scheme_version": "v2", "offset": 100000,
                                      "node_bits": 0, "prefix_width": 5,
                                      "project_seed": "2026-07-03T…|proj"}), [])

    def test_unknown_scheme_version_fails(self):
        failures = self._check({"epoch_utc": "2026-07-03T00:00:00Z", "scheme_version": "v3"})
        self.assertTrue(any("scheme_version" in f for f in failures), failures)

    def test_v2_missing_offset_fails(self):
        failures = self._check({"epoch_utc": "2026-07-03T00:00:00Z", "scheme_version": "v2"})
        self.assertTrue(any("offset" in f for f in failures), failures)

    def test_v2_below_band_offset_fails(self):
        failures = self._check({"epoch_utc": "2026-07-03T00:00:00Z",
                                "scheme_version": "v2", "offset": 100})
        self.assertTrue(any("36^3" in f for f in failures), failures)

    def test_v2_missing_epoch_fails(self):
        failures = self._check({"scheme_version": "v2", "offset": 100000})
        self.assertTrue(any("epoch_utc is required" in f for f in failures), failures)

    def test_v2_nonzero_node_bits_fails(self):
        failures = self._check({"epoch_utc": "2026-07-03T00:00:00Z",
                                "scheme_version": "v2", "offset": 100000, "node_bits": 4})
        self.assertTrue(any("node_bits" in f for f in failures), failures)

    def test_prefix_width_five_still_pins(self):
        failures = self._check({"epoch_utc": "2020-02-02T02:02:00Z", "prefix_width": 6})
        self.assertTrue(any("prefix_width" in f for f in failures), failures)


class LifecyclePrefixWidthPatternTests(unittest.TestCase):
    """Wave 1p9q0 AC-6a — the central prefix pattern (feeding the wave-id /
    change-id / plan-overview / wave-reference validators) accepts 6-char IDs."""

    @classmethod
    def setUpClass(cls):
        import sys
        if str(SCRIPTS_ROOT) not in sys.path:
            sys.path.insert(0, str(SCRIPTS_ROOT))

    def test_wave_id_pattern_accepts_five_and_six_char_prefixes(self):
        from wave_lint_lib.constants import WAVE_ID_PATTERN
        self.assertIsNotNone(WAVE_ID_PATTERN.search("wave-id: `1p9pk my-wave`"))
        self.assertIsNotNone(WAVE_ID_PATTERN.search("wave-id: `100001 future-wave`"))

    def test_change_id_pattern_accepts_five_and_six_char_prefixes(self):
        from wave_lint_lib.constants import CHANGE_ID_PATTERN
        self.assertIsNotNone(CHANGE_ID_PATTERN.search("Change ID: `1p9pt-enh sample-slug`"))
        self.assertIsNotNone(CHANGE_ID_PATTERN.search("Change ID: `100001-bug future-slug`"))

    def test_sec_id_pattern_accepts_five_and_six_char_prefixes(self):
        from wave_lint_lib.secrets_validators import _SEC_ID_RE
        self.assertIsNotNone(_SEC_ID_RE.match("1p9pk-sec"))
        self.assertIsNotNone(_SEC_ID_RE.match("100001-sec"))
        self.assertIsNone(_SEC_ID_RE.match("1234-sec"))


if __name__ == "__main__":
    unittest.main()


class MemoryRecordLintTests(DocsLintFixtureTests):
    """1p8gy AC-1: memory record schema validation — required fields, known
    kinds/statuses, evidence/target refs, supersession integrity, forbidden
    content. Per-kind fixtures per the readiness-council guidance."""

    ALL_KINDS = (
        "failed_attempt", "successful_pattern", "review_finding",
        "operator_preference", "environment_gotcha", "fragile_file",
        "decision", "dependency_gotcha",
    )

    @staticmethod
    def _record(memory_id: str, kind: str, *, status: str = "active",
                confidence: str = "0.8", extra: str = "",
                evidence: str = "- `1abcd-bug some-change` — learned during review",
                targets: str = "- `src/module.py`") -> str:
        return (
            f"# Lesson {memory_id}\n\n"
            f"Owner: Engineering\nStatus: {status}\nLast verified: 2026-07-13\n\n"
            f"Memory ID: `{memory_id}`\nKind: `{kind}`\nConfidence: {confidence}\n"
            f"Created: 2026-07-13\nUpdated: 2026-07-13\n{extra}\n"
            f"## Summary\n\nA durable lesson body.\n\n"
            f"## Evidence\n\n{evidence}\n\n"
            f"## Targets\n\n{targets}\n"
        )

    def _write_record(self, root: Path, memory_id: str, content: str) -> None:
        mem_dir = root / "docs" / "agents" / "memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        (mem_dir / f"{memory_id}.md").write_text(content, encoding="utf-8")

    def test_wellformed_records_of_every_kind_pass(self):
        root = self.copy_fixture()
        for i, kind in enumerate(self.ALL_KINDS):
            mid = f"mem-{kind.replace('_', '-')}"
            self._write_record(root, mid, self._record(mid, kind))
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_schema_violations_fail_loudly(self):
        cases = [
            ("unknown kind", self._record("mem-a", "vibes"), "unknown memory kind"),
            ("bad status", self._record("mem-a", "decision", status="maybe"),
             "memory `Status` must be one of"),
            ("bad confidence", self._record("mem-a", "decision", confidence="9"),
             "`Confidence` must be a number in [0.0, 1.0]"),
            ("id/filename mismatch", self._record("mem-b", "decision"),
             "must match the filename stem"),
            ("refless evidence", self._record("mem-a", "decision",
                                              evidence="- learned it somewhere"),
             "must carry backticked refs"),
            ("superseded without link",
             self._record("mem-a", "decision", status="superseded"),
             "must carry a backticked `Superseded by:`"),
            ("secret content", self._record(
                "mem-a", "environment_gotcha",
                evidence="- `x.py` — set api_key: sk-live-1234 to reproduce"),
             "secrets, raw transcript content, or personal facts"),
        ]
        for label, content, expected in cases:
            root = self.copy_fixture()
            self._write_record(root, "mem-a", content)
            result = self.run_docs_lint(root)
            shutil.rmtree(root)
            self.assertEqual(result.returncode, 1, f"{label}: lint passed unexpectedly")
            self.assertIn(expected, result.stderr, label)

    def test_superseded_with_link_passes(self):
        root = self.copy_fixture()
        self._write_record(root, "mem-old", self._record(
            "mem-old", "decision", status="superseded",
            extra="Superseded by: `mem-new`\n"))
        self._write_record(root, "mem-new", self._record("mem-new", "decision"))
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class MemoryRecordSchemaCompletenessTests(MemoryRecordLintTests):
    """Delivery-review P1: lint must REQUIRE every schema field — a
    status-less (or otherwise incomplete) record must fail, not pass."""

    def test_missing_status_line_fails(self):
        root = self.copy_fixture()
        # A record with no `Status:` line at all.
        content = (
            "# Lesson\n\nOwner: Engineering\nLast verified: 2026-07-13\n\n"
            "Memory ID: `mem-nostatus`\nKind: `decision`\nConfidence: 0.8\n"
            "Created: 2026-07-13\nUpdated: 2026-07-13\n\n"
            "## Summary\n\nBody.\n\n## Evidence\n\n- `1x`\n\n## Targets\n\n- `src/a.py`\n"
        )
        self._write_record(root, "mem-nostatus", content)
        result = self.run_docs_lint(root)
        shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing `Status:` line", result.stderr)

    def test_empty_summary_fails(self):
        root = self.copy_fixture()
        content = (
            "# Lesson\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-07-13\n\n"
            "Memory ID: `mem-empty`\nKind: `decision`\nConfidence: 0.8\n"
            "Created: 2026-07-13\nUpdated: 2026-07-13\n\n"
            "## Summary\n\n## Evidence\n\n- `1x`\n\n## Targets\n\n- `src/a.py`\n"
        )
        self._write_record(root, "mem-empty", content)
        result = self.run_docs_lint(root)
        shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("`## Summary` must not be empty", result.stderr)


class MemoryRecordValueParityLintTests(MemoryRecordLintTests):
    """Adversarial-pass: lint value grammars — `*` bullets fail, float
    confidence passes, impossible dates fail (calendar-validated)."""

    def test_star_bullets_fail(self):
        root = self.copy_fixture()
        self._write_record(root, "mem-star", self._record(
            "mem-star", "decision", evidence="* `1abcd-bug some-change` star bullet"))
        result = self.run_docs_lint(root)
        shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("must include at least one bullet", result.stderr)

    def test_impossible_date_fails(self):
        root = self.copy_fixture()
        content = (
            "# T\n\nOwner: Engineering\nStatus: active\nLast verified: 2026-07-13\n\n"
            "Memory ID: `mem-baddate`\nKind: `decision`\nConfidence: 0.8\n"
            "Created: 2020-13-40\nUpdated: 2026-07-13\n\n"
            "## Summary\n\nBody.\n\n## Evidence\n\n- `1x`\n\n## Targets\n\n- `src/a.py`\n"
        )
        self._write_record(root, "mem-baddate", content)
        result = self.run_docs_lint(root)
        shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a valid calendar date", result.stderr)

    def test_float_confidence_passes(self):
        root = self.copy_fixture()
        content = self._record("mem-sci", "decision").replace("Confidence: 0.8", "Confidence: 1e-1")
        self._write_record(root, "mem-sci", content)
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

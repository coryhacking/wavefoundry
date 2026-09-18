from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


TESTS_ROOT = Path(__file__).resolve().parent
SCRIPTS_ROOT = TESTS_ROOT.parent
PROJECT_ROOT = SCRIPTS_ROOT.parents[3]
FIXTURE_ROOT = TESTS_ROOT / "fixtures" / "docs_lint" / "base"
DOCS_LINT_SCRIPT = SCRIPTS_ROOT / "docs_lint.py"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import context_efficiency as ce
from wave_lint_lib.wave_validators import check_orphan_wave_ledgers
from review_evidence import (
    read_review_event_ledger,
    render_review_status_projection,
    REVIEW_STATUS_MARKER_BEGIN,
    REVIEW_STATUS_MARKER_END,
    review_status_signoff_keys,
)
from wave_lint_lib.wave_validators import check_wave_docs


class DocsLintFixtureTests(unittest.TestCase):
    VALID_WAVE_ID = "00057 routine-behavior-contract"
    BASELINE_WAVE_ID = "00000 wave-zero-plans-and-specs"
    VALID_CHANGE_ID = "00058-bug fixture-core"
    FOLLOW_UP_CHANGE_ID = "00059-enh fixture-follow-up"
    WAVE_DOC_PATH = Path("docs/waves/change-2026-03/wave.md")
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

    def test_external_review_status_projection_drift_is_reported(self) -> None:
        root = self.copy_fixture()
        wave_md = root / self.WAVE_DOC_PATH
        records, errors = read_review_event_ledger(wave_md)
        self.assertEqual(errors, ())
        keys = review_status_signoff_keys(
            records,
            (
                "wave-council-readiness",
                "wave-council-delivery",
                "operator-signoff",
            ),
        )
        source_text = wave_md.read_text(encoding="utf-8")
        current = render_review_status_projection(
            source_text,
            records,
            keys,
        )
        wave_md.write_text(
            current.replace(
                "| wave-council-readiness |",
                "| wave-council-readiness | stale |",
                1,
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("review evidence projection is stale", result.stderr)

    def test_external_review_status_projection_missing_is_reported(self) -> None:
        root = self.copy_fixture()
        wave_md = root / self.WAVE_DOC_PATH
        text = wave_md.read_text(encoding="utf-8")
        start = text.index(REVIEW_STATUS_MARKER_BEGIN)
        end = text.index(REVIEW_STATUS_MARKER_END, start) + len(
            REVIEW_STATUS_MARKER_END
        )
        wave_md.write_text(text[:start] + text[end:], encoding="utf-8")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("review evidence projection is stale", result.stderr)

    def test_closed_external_wave_keeps_historical_review_status_projection(self) -> None:
        """1tmb0: new approval rules apply prospectively, not to closed archives."""
        root = self.copy_fixture()
        wave_md = root / self.WAVE_DOC_PATH
        text = wave_md.read_text(encoding="utf-8")
        text = text.replace("Status: active", "Status: closed", 1).replace(
            "| wave-council-readiness | pending |",
            "| wave-council-readiness | historical |",
            1,
        )
        wave_md.write_text(text, encoding="utf-8")
        try:
            failures = check_wave_docs(root, only={wave_md})
        finally:
            shutil.rmtree(root)
        self.assertFalse(
            [item for item in failures if "review evidence projection is stale" in item],
            failures,
        )

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

    def test_one_thirteen_shaped_inline_wave_fails_actionably_without_ledger(self) -> None:
        # Wave 1to78 (AC-4): a 1.13-shaped inline-marker wave — inline jsonl
        # fence inside the owned block, no source declaration, no sibling
        # ledger — still fails closed with the actionable manual-migration
        # message after the inline reader's deletion. It never silently
        # reclassifies as legacy prose.
        root = self.copy_fixture()
        wave_md = root / self.WAVE_DOC_PATH
        text = (
            wave_md.read_text(encoding="utf-8")
            .replace(
                "review-evidence-source: events.jsonl",
                "review-evidence-protocol: 1",
            )
            .replace(
                "</summary>\n</details>",
                "</summary>\n\n```jsonl\n```\n</details>",
            )
        )
        self.assertIn("```jsonl", text)  # the inline fence is really present
        wave_md.write_text(text, encoding="utf-8")
        (wave_md.parent / "events.jsonl").unlink()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "must declare `review-evidence-source: events.jsonl`", result.stderr
        )
        self.assertIn("migrate manually", result.stderr)
        self.assertIn("sibling `events.jsonl` ledger", result.stderr)

    def test_orphan_ledger_control_matrix(self) -> None:
        # Wave 1to78 (AC-7): the content-driven orphan-ledger guard, run
        # against a synthetic docs/waves tree covering every named control.
        # P1/P2 are the executed known-bad positives; N1-N5 must all pass.
        # Delivery repair DF1 narrowed N3: enumeration is content-driven, so
        # only a non-wave-shaped folder WITHOUT a non-empty ledger passes
        # (the renamed-directory positive lives in
        # test_orphan_ledger_renamed_directory_is_still_detected).
        root = Path(tempfile.mkdtemp(prefix="wave-orphan-matrix-"))
        try:
            waves = root / "docs" / "waves"
            declared = "review-evidence-source: events.jsonl\n"
            record = '{"record_type": "review_run"}\n'
            # P1: non-empty ledger + wave.md with neither declaration nor marker
            p1 = waves / "1zzp1 orphan-undeclared"
            p1.mkdir(parents=True)
            (p1 / "events.jsonl").write_text(record, encoding="utf-8")
            (p1 / "wave.md").write_text(
                "# Wave Record\n\n## Review Evidence\n\n- operator-signoff: approved\n",
                encoding="utf-8",
            )
            # P2: non-empty ledger in an id-shaped dir, wave.md missing (the
            # tamper variant the rglob("*.md") walk cannot see)
            p2 = waves / "1zzp2 orphan-missing-md"
            p2.mkdir(parents=True)
            (p2 / "events.jsonl").write_text(record, encoding="utf-8")
            # N1: empty ledger passes (fresh scaffold)
            n1 = waves / "1zzn1 empty-ledger"
            n1.mkdir(parents=True)
            (n1 / "events.jsonl").write_bytes(b"")
            # N2: declared wave passes
            n2 = waves / "1zzn2 declared-wave"
            n2.mkdir(parents=True)
            (n2 / "events.jsonl").write_text(record, encoding="utf-8")
            (n2 / "wave.md").write_text(
                f"# Wave Record\n\n{declared}\n## Review Evidence\n", encoding="utf-8"
            )
            # N3: non-wave-shaped folder WITHOUT a non-empty ledger passes
            # (empty-ledger and no-ledger variants)
            n3 = waves / "notes"
            n3.mkdir(parents=True)
            (n3 / "events.jsonl").write_bytes(b"")
            n3b = waves / "assets"
            n3b.mkdir(parents=True)
            (n3b / "README.txt").write_text("not a ledger\n", encoding="utf-8")
            # N4: root-level docs/waves/events.jsonl passes
            (waves / "events.jsonl").write_text(record, encoding="utf-8")
            # N5: legacy inline-marker wave does not ADDITIONALLY trip the
            # orphan check (it fails full validation elsewhere)
            n5 = waves / "1zzn5 inline-marker"
            n5.mkdir(parents=True)
            (n5 / "events.jsonl").write_text(record, encoding="utf-8")
            (n5 / "wave.md").write_text(
                "# Wave Record\n\nreview-evidence-protocol: 1\n\n## Review Evidence\n",
                encoding="utf-8",
            )

            failures = check_orphan_wave_ledgers(root)
            self.assertEqual(len(failures), 2, failures)
            p1_failure = next(f for f in failures if "1zzp1" in f)
            p2_failure = next(f for f in failures if "1zzp2" in f)
            for failure in (p1_failure, p2_failure):
                self.assertIn("orphaned review ledger", failure)
                self.assertIn("non-empty `events.jsonl`", failure)
                self.assertIn(
                    "restore `wave.md` or its declaration line from history", failure
                )
            # P2 fails IDENTICALLY to P1 apart from the folder name.
            self.assertEqual(
                p1_failure.replace("1zzp1 orphan-undeclared", "X"),
                p2_failure.replace("1zzp2 orphan-missing-md", "X"),
            )
        finally:
            shutil.rmtree(root)

    def test_orphan_ledger_detected_through_public_docs_lint(self) -> None:
        # Wave 1to78 (AC-7): the P2 tamper variant end-to-end: an id-shaped
        # wave folder whose wave.md was deleted while its non-empty ledger
        # survives fails the real docs-lint subprocess; the empty-ledger
        # sibling control (N1) does not.
        root = self.copy_fixture()
        try:
            orphan = root / "docs" / "waves" / "1zzzz orphan-probe"
            orphan.mkdir(parents=True)
            (orphan / "events.jsonl").write_text(
                '{"record_type": "review_run"}\n', encoding="utf-8"
            )
            scaffold = root / "docs" / "waves" / "1zzzy fresh-scaffold"
            scaffold.mkdir(parents=True)
            (scaffold / "events.jsonl").write_bytes(b"")
            result = self.run_docs_lint(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn("orphaned review ledger", result.stderr)
            self.assertIn("1zzzz orphan-probe", result.stderr)
            self.assertNotIn("1zzzy fresh-scaffold", result.stderr)
        finally:
            shutil.rmtree(root)

    def test_orphan_ledger_renamed_directory_is_still_detected(self) -> None:
        # Wave 1to78 delivery repair (DF1, P3 control): the guard is
        # CONTENT-driven, not name-shape-driven. A direct child directory of
        # docs/waves/ holding a non-empty events.jsonl is a candidate even
        # when its name is not id-shaped (renamed-directory tamper variant:
        # underscore/7-char-prefix/uppercase name), whether wave.md is absent
        # or present-but-undeclared.
        root = Path(tempfile.mkdtemp(prefix="wave-orphan-renamed-"))
        try:
            waves = root / "docs" / "waves"
            record = '{"record_type": "review_run"}\n'
            # P3a: renamed dir (uppercase + underscore + 7-char leading
            # token), non-empty ledger, wave.md absent.
            p3a = waves / "1ZZP3AX_renamed-orphan"
            p3a.mkdir(parents=True)
            (p3a / "events.jsonl").write_text(record, encoding="utf-8")
            # P3b: renamed dir, non-empty ledger, wave.md present but
            # carrying neither declaration nor legacy marker.
            p3b = waves / "1ZZP3BX_renamed-undeclared"
            p3b.mkdir(parents=True)
            (p3b / "events.jsonl").write_text(record, encoding="utf-8")
            (p3b / "wave.md").write_text(
                "# Wave Record\n\n## Review Evidence\n\n- operator-signoff: approved\n",
                encoding="utf-8",
            )
            failures = check_orphan_wave_ledgers(root)
            self.assertEqual(len(failures), 2, failures)
            p3a_failure = next(f for f in failures if "1ZZP3AX" in f)
            p3b_failure = next(f for f in failures if "1ZZP3BX" in f)
            for failure in (p3a_failure, p3b_failure):
                self.assertIn("orphaned review ledger", failure)
                self.assertIn("non-empty `events.jsonl`", failure)
                self.assertIn(
                    "restore `wave.md` or its declaration line from history", failure
                )
                # The message notes that the folder name is not id-shaped.
                self.assertIn("not id-shaped", failure)
        finally:
            shutil.rmtree(root)

    def test_retired_adoption_sidecar_is_never_consulted(self) -> None:
        # Wave 1tomw (AC-2/AC-7): events.jsonl is the sole authority. A stray
        # adoption-shaped sidecar — even one whose receipt would contradict
        # the ledger — changes nothing, because no lint path reads it.
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
                            "record_count": 7,
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
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
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
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
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

    AC_REPO_STATE_DOC = "docs/waves/change-2026-03/00058-bug fixture-core.md"

    def _replace_acs(self, root, acs: str, priorities: str) -> None:
        change_doc = root / self.AC_REPO_STATE_DOC
        text = change_doc.read_text(encoding="utf-8")
        text = text.replace(
            "## Acceptance Criteria\n\n- [x] AC-1: Fixture criterion satisfied.\n",
            f"## Acceptance Criteria\n\n{acs}",
        )
        text = text.replace("| AC-1 | required |\n", priorities)
        change_doc.write_text(text, encoding="utf-8")

    def test_ac_asserting_repository_state_warns_across_named_families(self) -> None:
        # Wave 1wur7 (1wuui AC-2): the three phrasing families named in
        # Requirement 3 -- the bare suite clause, the runner-command form, and a
        # repo-wide clause compounded into an otherwise change-scoped AC.
        root = self.copy_fixture()
        self._replace_acs(
            root,
            "- [x] AC-1: Fixture criterion satisfied and the full framework test suite passes.\n"
            "- [x] AC-2: The reproducer lands and python3 .wavefoundry/framework/scripts/run_tests.py passes.\n"
            "- [x] AC-3: The new validator has fixtures beside the existing AC checks, and all tests are green.\n",
            "| AC-1 | required |\n| AC-2 | required |\n| AC-3 | required |\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0)
        for label in ("AC-1", "AC-2", "AC-3"):
            self.assertIn(f"{label} asserts repository-wide state", result.stderr)
            self.assertRegex(result.stderr, r"(?m)^WARNING: .*asserts repository-wide state")
        self.assertIn("an outcome THIS CHANGE controls", result.stderr)

    def test_wrapped_ac_bullet_is_inspected_whole(self) -> None:
        # Delivery review DOCS-DEL-2: only a bullet's FIRST physical line was
        # inspected, so a wrapped bullet evaded the rule -- and long compound
        # criteria, where a repo-wide clause actually hides, are the ones that wrap.
        root = self.copy_fixture()
        self._replace_acs(
            root,
            "- [x] AC-1: The reproducer lands and the fixtures cover it, and\n"
            "  the full framework test suite passes.\n",
            "| AC-1 | required |\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0)
        self.assertIn("AC-1 asserts repository-wide state", result.stderr)
        self.assertRegex(result.stderr, r"(?m)^WARNING: .*asserts repository-wide state")

    def test_loose_list_continuation_paragraph_is_inspected_whole(self) -> None:
        # Round-5 architecture reverification: a blank line ended the fold, so a
        # loose-list continuation paragraph (blank line, then indented text, which
        # markdown renders as the same item) was never inspected -- the wrapped
        # bullet hole in a different costume.
        root = self.copy_fixture()
        self._replace_acs(
            root,
            "- [x] AC-1: The reproducer lands and the fixtures cover it.\n"
            "\n"
            "  In addition, the full framework test suite passes.\n",
            "| AC-1 | required |\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0)
        self.assertIn("AC-1 asserts repository-wide state", result.stderr)
        self.assertRegex(result.stderr, r"(?m)^WARNING: .*asserts repository-wide state")

    def test_backticked_runner_command_still_fires(self) -> None:
        # CODE-DEL-7 / QA-DEL-7 / ARCH-DEL-10: backticking a command is this
        # repository's house style, and exempting it silenced the exact
        # runner-command family the rule names. Quoting exempts only when the
        # PREDICATE is quoted with the clause.
        root = self.copy_fixture()
        self._replace_acs(
            root,
            "- [x] AC-1: `python3 .wavefoundry/framework/scripts/run_tests.py` passes.\n",
            "| AC-1 | required |\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0)
        self.assertIn("AC-1 asserts repository-wide state", result.stderr)
        self.assertRegex(result.stderr, r"(?m)^WARNING: .*asserts repository-wide state")

    def test_change_local_acs_naming_a_specific_target_do_not_fire(self) -> None:
        # CODE-DEL-6 / REL-DEL-4 / ARCH-DEL-10: a blocking rule about assertion
        # shape must not reject an assertion that is already change-local.
        root = self.copy_fixture()
        self._replace_acs(
            root,
            "- [x] AC-1: All tests in `test_chunker.py` pass.\n"
            "- [x] AC-2: The full test suite for the new module passes.\n"
            "- [x] AC-3: Every test we touch passes.\n",
            "| AC-1 | required |\n| AC-2 | required |\n| AC-3 | required |\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_an_unrelated_negation_word_does_not_disable_the_rule(self) -> None:
        # CODE-DEL-5 / REL-DEL-5 / QA-DEL-7: the carve-out was tested line-wide,
        # so any bullet containing an ordinary "flag" or an unrelated "never"
        # clause silently exempted itself. It now has to sit immediately before
        # the phrase it governs.
        root = self.copy_fixture()
        self._replace_acs(
            root,
            "- [x] AC-1: The --all flag is honored and the full test suite passes.\n"
            "- [x] AC-2: The sensor never fires on closed waves, and all framework tests pass.\n"
            "- [x] AC-3: The whole-repository test suite passes.\n",
            "| AC-1 | required |\n| AC-2 | required |\n| AC-3 | required |\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0)
        for label in ("AC-1", "AC-2", "AC-3"):
            self.assertIn(f"{label} asserts repository-wide state", result.stderr)
            self.assertRegex(result.stderr, r"(?m)^WARNING: .*asserts repository-wide state")

    def test_quoting_alone_and_negating_alone_each_exempt_a_bullet(self) -> None:
        # QA-DEL-7: the original negative fixture carried BOTH signals at once,
        # so either mechanism could be deleted and the test stayed green. Each is
        # now exercised on its own.
        root = self.copy_fixture()
        self._replace_acs(
            root,
            "- [x] AC-1: The seed shows the banned shape `the full test suite passes` verbatim.\n"
            "- [x] AC-2: The guidance says to write a change-scoped clause rather than "
            "the full framework test suite passing.\n",
            "| AC-1 | required |\n| AC-2 | required |\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_change_scoped_and_quoting_acs_do_not_fire(self) -> None:
        # Wave 1wur7 (1wuui AC-2): the replacement shape passes, and a bullet that
        # quotes, negates, or specifies the clause is talking ABOUT it, not
        # asserting it. The carve-out is scoped to the individual AC bullet.
        root = self.copy_fixture()
        self._replace_acs(
            root,
            "- [x] AC-1: The change's own suites and every test it adds pass; the documents this "
            "change authors or edits validate; and no failure elsewhere is attributable to this change.\n"
            "- [x] AC-2: The validator flags an AC that says `the full framework test suite passes`.\n"
            "- [x] AC-3: Every test class in `test_server_tools.py` is classified, and the runner "
            "gains a `--file` flag.\n",
            "| AC-1 | required |\n| AC-2 | required |\n| AC-3 | required |\n",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ac_repository_state_rule_does_not_reach_a_closed_wave(self) -> None:
        # Wave 1wur7 (1wuui Requirement 4, AC-5): scoping is the wave record's
        # Status via `_wave_requires_wave_owned_change_docs`, so closed-wave
        # records and parked `docs/plans/` drafts are never reached and this
        # change fails no document it promised not to touch.
        root = self.copy_fixture()
        self._replace_acs(
            root,
            "- [x] AC-1: Fixture criterion satisfied and the full framework test suite passes.\n",
            "| AC-1 | required |\n",
        )
        wave_doc = root / self.WAVE_DOC_PATH
        wave_text = wave_doc.read_text(encoding="utf-8")
        self.assertIn("Status: active", wave_text)
        wave_doc.write_text(wave_text.replace("Status: active", "Status: closed", 1), encoding="utf-8")
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertNotIn("asserts repository-wide state", result.stderr)

    def test_checkbox_ac_syntax_passes(self) -> None:
        root = self.copy_fixture()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0)

    def test_plain_bullet_task_syntax_fails(self) -> None:
        root = self.copy_fixture()
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
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
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
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
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
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
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
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
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
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
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
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
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
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
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.unlink()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            f"wave-owned change `{self.VALID_CHANGE_ID}` must exist at "
            "`docs/waves/change-2026-03/00058-bug fixture-core.md`",
            result.stderr,
        )
        self.assertIn("Prepare wave", result.stderr)

    def test_implementing_wave_requires_sibling_change_docs(self) -> None:
        """1v0lx AC-3 red-first (end-to-end half): the existence check must
        fire at `Status: implementing`, the status every OPEN wave actually
        holds. Before 1v0lx the gate covered {active, ready} plus the
        `Activated at:` fallback only, so a missing admitted doc sailed
        through the exact status where implementation happens (probe: rc=0
        with zero failures on this fixture against the pre-fix code)."""
        root = self.copy_fixture()
        wave_md = root / self.WAVE_DOC_PATH
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "Status: active", "Status: implementing", 1
            ),
            encoding="utf-8",
        )
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
        change_doc.unlink()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(
            f"wave-owned change `{self.VALID_CHANGE_ID}` must exist at ",
            result.stderr,
        )

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

    def test_rejected_transition_names_what_is_reachable_from_the_current_status(self) -> None:
        """AC-3: the message states the reachable set for THIS status, not the global one."""
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
        self.assertIn("; allowed from `complete`: `complete`", result.stderr)
        # `complete` is terminal, so the reachable set is strictly narrower than
        # the global vocabulary. Printing the global set here would be wrong.
        self.assertNotIn("; allowed from `complete`: `active`", result.stderr)

    def test_malformed_change_status_names_the_accepted_vocabulary(self) -> None:
        """AC-1: the shape failure from the field report now carries the value set."""
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8").replace(
                "Change Status: `complete`",
                "Change Status: `implemented - awaiting delivery review`",
                1,
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid `Change Status` declaration", result.stderr)
        self.assertIn("; allowed: `active`, `blocked`, `complete`", result.stderr)
        self.assertIn("`planned`, `ready`, `retry`, `review`, `superseded`", result.stderr)

    def test_publishing_the_vocabulary_did_not_turn_it_into_a_gate(self) -> None:
        """AC-2: `implemented` is used 1000 times and is in no constant. It must still pass.

        This is the no-new-gate oracle: the change publishes the vocabulary as
        guidance, so a well-formed value outside it keeps linting exactly as it
        did before.
        """
        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        original = wave_doc.read_text(encoding="utf-8")
        self.assertIn("Change Status: `complete`", original)
        wave_doc.write_text(
            original.replace("Change Status: `complete`", "Change Status: `implemented`", 1),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        # The claim under test is narrow and must be stated narrowly: publishing
        # the vocabulary did not add a declaration-time gate. `implemented` is
        # well formed and unknown, and the declaration check still accepts it.
        self.assertNotIn("invalid `Change Status` declaration", result.stderr)
        # Any OTHER failure this fixture produces is pre-existing behavior that
        # this change did not touch: the fixture carries a `Previous Change
        # Status`, so the transition rule applies, and a dependent change
        # requires a terminal dependency. Asserting their absence here would be
        # asserting something this change never claimed. What must hold is that
        # each such message is one the tree already emitted, now merely carrying
        # its value set.
        for line in result.stderr.splitlines():
            if "Change Status" in line and "declaration" in line:
                self.fail(f"declaration-time gate appeared: {line}")

    def test_blocked_dependency_names_which_statuses_would_unblock_it(self) -> None:
        """Delivery review: the terminal set is bound at the check but was not printed.

        Same defect shape as the transition site, found by auditing every
        enum-governed failure rather than only the sites the plan happened to
        name.
        """
        from wave_lint_lib import wave_validators

        root = self.copy_fixture()
        wave_doc = root / self.WAVE_DOC_PATH
        wave_doc.write_text(
            wave_doc.read_text(encoding="utf-8").replace(
                "Change Status: `complete`", "Change Status: `planned`", 1
            ),
            encoding="utf-8",
        )
        try:
            failures = "\n".join(wave_validators.check_wave_docs(root))
        finally:
            shutil.rmtree(root)
        self.assertIn(
            f"change `{self.FOLLOW_UP_CHANGE_ID}` is `ready` but dependency "
            f"`{self.VALID_CHANGE_ID}` is still `planned`. "
            "The dependency must reach a terminal status; allowed:",
            failures,
        )
        for status in wave_validators.TERMINAL_CHANGE_STATUSES:
            self.assertIn(f"`{status}`", failures)

    def test_watchpoint_marker_message_lists_every_marker_that_satisfies_it(self) -> None:
        """Delivery review: the message hand-listed 3 of 6 markers.

        `retry`, `defer`, and `move` also satisfy the check but were never
        named, which is the hand-written drift this change exists to remove.
        """
        from wave_lint_lib import wave_validators
        from wave_lint_lib.constants import WAVE_WATCHPOINT_MARKERS, allowed_values_suffix

        self.assertEqual(len(WAVE_WATCHPOINT_MARKERS), 6)
        rendered = allowed_values_suffix(WAVE_WATCHPOINT_MARKERS)
        for marker in WAVE_WATCHPOINT_MARKERS:
            self.assertIn(f"`{marker}`", rendered)
        source = Path(wave_validators.__file__).read_text(encoding="utf-8")
        self.assertIn(
            "blocking language for non-terminal changes\"\n"
            "                f\"{allowed_values_suffix(WAVE_WATCHPOINT_MARKERS)}",
            source,
            "the watchpoint message must derive its marker list from the constant",
        )

    def test_the_printed_set_is_read_from_the_constant_not_hand_written(self) -> None:
        """AC-4: vary the CONSTANT, not the fixture, and the message must follow.

        A hand-written list in the message would pass every other test in this
        class while silently drifting from the rule it claims to describe. The
        patch target is the ``wave_validators`` binding rather than the
        ``constants`` module: ``wave_validators`` does ``from .constants import
        (...)`` at import time, so patching ``constants`` would leave the bound
        name untouched and this test would pass without exercising anything.
        The unpatched assertion below is the negative control that proves it.
        """
        from unittest import mock

        from wave_lint_lib import wave_validators

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
            baseline = "\n".join(wave_validators.check_wave_docs(root))
            self.assertIn("; allowed from `complete`:", baseline)
            self.assertNotIn("`teleported`", baseline)

            widened = {
                status: (set(targets) | {"teleported"} if status == "complete" else targets)
                for status, targets in wave_validators.ALLOWED_CHANGE_STATUS_TRANSITIONS.items()
            }
            with mock.patch.object(
                wave_validators, "ALLOWED_CHANGE_STATUS_TRANSITIONS", widened
            ):
                mutated = "\n".join(wave_validators.check_wave_docs(root))
        finally:
            shutil.rmtree(root)
        self.assertIn("`teleported`", mutated)

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
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
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
        change_doc = root / "docs/waves/change-2026-03/00058-bug fixture-core.md"
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

    ACTIVE_WAVE = Path("docs/waves/change-2026-03/wave.md")

    def _make_legacy(self, root: Path) -> None:
        wave_md = root / self.ACTIVE_WAVE
        wave_md.write_text(
            wave_md.read_text(encoding="utf-8").replace(
                "review-evidence-source: events.jsonl\n", ""
            ),
            encoding="utf-8",
        )
        wave_md.with_name("events.jsonl").unlink(missing_ok=True)

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

    def _declare_with_typed_readiness(self, root: Path) -> None:
        """Add a schema-valid typed readiness approval with no prose verdict."""
        import review_evidence

        wave_md = root / self.ACTIVE_WAVE
        text = wave_md.read_text(encoding="utf-8")
        if "review-evidence-source: events.jsonl" not in text:
            text = text.replace(
                "Last verified:",
                "review-evidence-source: events.jsonl\nLast verified:",
                1,
            )
        wave_md.write_text(text, encoding="utf-8")
        approval = {
            "record_type": "executable_evidence",
            "evidence_record_id": "approval-wave-council-readiness",
            "claim_id": "approval:wave-council-readiness",
            "claim_kind": "approval",
            "required_for_approval": True,
            "phase": "readiness",
            "proposition": "readiness council independently approved the plan",
            "counterexample_or_failure_condition": "the plan still has a blocking finding",
            "execution_status": "executed",
            "public_path": "wf_review_event",
            "command_or_fixture": "PrepareCouncilVerdictLintTests typed readiness",
            "expected": "a current typed readiness approval",
            "observed": "the typed approval was recorded",
            "artifact_or_test_id": "test:typed-readiness-no-prose",
            "adjacent_controls": ["legacy missing-verdict fixture"],
            "test_ran_without_unintended_skip": True,
            "public_path_reached": True,
            "boundary_values_realistic": True,
            "assertions_non_vacuous": True,
            "known_bad_detected": True,
            "known_bad_detection_method": "remove typed approval control",
            "limitations": "temporary local fixture",
            "safety_and_authorization": "local temporary fixture only",
            "probe_class": "local_safe",
            "authorization_status": "not_required",
            "safe_boundary": False,
            "unexecuted_remainder_prohibited": False,
            "universal_claim": False,
            "verification_context": {
                "actor": "wave-council",
                "context_id": "ctx-typed-readiness-no-prose",
                "fresh_context": True,
                "independent": True,
            },
        }
        review_evidence.review_event_path(wave_md).write_bytes(
            review_evidence.canonical_review_events_bytes((approval,))
        )

    def test_active_wave_with_council_verdict_passes(self) -> None:
        root = self.copy_fixture()
        try:
            self._make_legacy(root)
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
            self._make_legacy(root)
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prepare-council", result.stderr)
        self.assertIn("WARNING", result.stderr)

    def test_implementing_wave_without_council_verdict_errors(self) -> None:
        root = self.copy_fixture()
        try:
            self._make_legacy(root)
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
            self._make_legacy(root)
            self._patch_wave_status(root, "implementing")
            self._add_council_verdict(root)
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("docs-lint: ok", result.stdout)

    def test_declared_implementing_wave_with_typed_readiness_needs_no_prose_verdict(self) -> None:
        """1tsyx AC-2 red-first at the only pre-change hard-error status."""
        from wave_lint_lib.wave_validators import check_prepare_council_verdict

        root = self.copy_fixture()
        try:
            self._patch_wave_status(root, "implementing")
            self._declare_with_typed_readiness(root)
            wave_md = root / self.ACTIVE_WAVE
            wave_text = wave_md.read_text(encoding="utf-8")
            self.assertNotIn("prepare-council", wave_text.casefold())
            records, ledger_errors = read_review_event_ledger(wave_md)
            self.assertFalse(ledger_errors, ledger_errors)
            self.assertEqual(
                [record.get("claim_id") for record in records],
                ["approval:wave-council-readiness"],
            )
            errors, warnings = check_prepare_council_verdict(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_narrative_or_malformed_declaration_cannot_bypass_legacy_verdict_gate(self) -> None:
        from wave_lint_lib.wave_validators import check_prepare_council_verdict

        root = self.copy_fixture()
        try:
            self._make_legacy(root)
            self._patch_wave_status(root, "implementing")
            wave_md = root / self.ACTIVE_WAVE
            base = wave_md.read_text(encoding="utf-8")

            wave_md.write_text(
                base
                + "\n## Notes\n\nThe token `review-evidence-source: events.jsonl` is discussed here only.\n",
                encoding="utf-8",
            )
            narrative_errors, narrative_warnings = check_prepare_council_verdict(root)

            wave_md.write_text(
                base.replace(
                    "Last verified:",
                    "review-evidence-source events.jsonl\nLast verified:",
                    1,
                ),
                encoding="utf-8",
            )
            malformed_errors, malformed_warnings = check_prepare_council_verdict(root)
        finally:
            shutil.rmtree(root)

        for errors, warnings in (
            (narrative_errors, narrative_warnings),
            (malformed_errors, malformed_warnings),
        ):
            self.assertEqual(len(errors), 1, errors)
            self.assertIn("prepare-council", errors[0])
            self.assertEqual(warnings, [])


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
        """A verdict line pasted from the wf_prepare_wave template (placeholder wording intact)
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
    server_impl (the wf_prepare_wave parser). The two patterns are intentionally
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
            "between the lint validator and the wf_prepare_wave parser",
        )
        self.assertEqual(
            wave_validators._PREPARE_COUNCIL_VERDICT_LINE_RE.flags,
            server_impl._PREPARE_COUNCIL_VERDICT_RE.flags,
            "verdict-line regex flags must match (both IGNORECASE)",
        )


# Wave 1wur7, round 5. Four rounds of repairs each shipped a mechanism whose
# deletion the suite could not detect, because every pin was written by reading the
# mechanism's current contents. This matrix is the structural answer: one probe per
# alternation member and per tuning constant, chosen so that ONLY that member can
# change the outcome, and it lives here as literal data with no reference to the
# module. Each row was generated and then VERIFIED by deleting its member in a
# scratch copy and confirming the outcome flips; a row that did not flip was not
# kept, and the two members that could not be made to flip were removed from the
# validator as dead code rather than papered over with an unfalsifiable pin.
#
# Some probes read oddly ("the all test suite passes"). They are chosen for
# discrimination, not for prose; readability here would cost the property.
AC_RULE_MATRIX = (
    # The two path-shaped referents. The coverage floor below caught their absence
    # on its first run, which is the point of having it.
    ('The full test suite in tests/ passes.', True),
    ('All tests under .wavefoundry/ pass.', True),
    ('the full test suite passes.', True),
    ('the whole test suite passes.', True),
    ('the entire test suite passes.', True),
    ('the complete test suite passes.', True),
    ('the all test suite passes.', True),
    ('the every test suite passes.', True),
    ('All tests in the repository pass.', True),
    ('All tests in the repo pass.', True),
    ('All tests in the tree pass.', True),
    ('All tests in the project pass.', True),
    ('All tests in the codebase pass.', True),
    ('All tests in the framework pass.', True),
    ('All tests in the suite pass.', True),
    ('All tests in the ci pass.', True),
    ('Every test class passes.', False),
    ('Every test classes passes.', False),
    ('Every test file passes.', False),
    ('Every test files passes.', False),
    ('Every test module passes.', False),
    ('Every test modules passes.', False),
    ('Every test case passes.', False),
    ('Every test cases passes.', False),
    ('Every test method passes.', False),
    ('Every test methods passes.', False),
    ('Every test function passes.', False),
    ('Every test functions passes.', False),
    ('Every test name passes.', False),
    ('Every test names passes.', False),
    ('Every test id passes.', False),
    ('Every test ids passes.', False),
    ('Every test fixture passes.', False),
    ('Every test fixtures passes.', False),
    ('Every test runner passes.', False),
    ('Every test runners passes.', False),
    ('Every test data passes.', False),
    ('Every test helper passes.', False),
    ('Every test helpers passes.', False),
    ('Every test path passes.', False),
    ('Every test paths passes.', False),
    ('The full test suite for the new module passes.', False),
    ('The full test suites for the new module passes.', False),
    ('All existing tests pass.', True),
    ('All pre-existing tests pass.', True),
    ('All preexisting tests pass.', True),
    ('All repository tests pass.', True),
    ('All repo tests pass.', True),
    ('All project tests pass.', True),
    ('All codebase tests pass.', True),
    ('All remaining tests pass.', True),
    ('All other tests pass.', True),
    ('All current tests pass.', True),
    ('All known tests pass.', True),
    ('All passing tests pass.', True),
    ('All failing tests pass.', True),
    ('the full test suite green.', True),
    ('the full test suite clean.', True),
    ('the full test suite succeeds.', True),
    ('the full test suite succeeded.', True),
    ('the full test suite agrees.', True),
    # Round-5 architecture reverification: a carve-out marker inside a code span
    # is quoted, not applied; the assertion after it must still fire.
    ("- [ ] AC-1: `must not` full test suite passes.", True),
    # Round-5 code reverification (M15b): the straight and curly double-quote
    # span branches had no probe, so dropping either survived the suite. A clause
    # quoted WITH its predicate is talking about the sentence, not asserting it.
    ('The banned sentence is "the full test suite passes".', False),
    ('The banned sentence is \u201cthe full test suite passes\u201d.', False),
    # Round-5 code and qa reverification: every possessor and preposition of the
    # narrowing lookahead, the two compound scope words, and the runner's
    # positional-file lookahead had no row, so each survived deletion.
    ('Every test it adds passes.', False),
    ('All tests they add pass.', False),
    ('All tests this change adds pass.', False),
    ('All tests the change adds pass.', False),
    ('All tests the wave adds pass.', False),
    ('Every test added passes.', False),
    ('Every test introduced passes.', False),
    ('Every test we touch passes.', False),
    ('All tests covering the parser pass.', False),
    ('All tests touching the parser pass.', False),
    ('All tests from the parser module pass.', False),
    ('run_tests.py test_chunker.py passes.', False),
    ('the repository-wide test suite passes.', True),
    ('the repo-wide test suite passes.', True),
    ('the whole-repository test suite passes.', True),
    # Round-5 qa reverification: every carve-out marker, the passed/passing
    # predicate forms, the `tests suite` noun form, the two-word gap cap in both
    # directions, and the three windows at their exact boundaries.
    ('The rule must not say the full test suite passes.', False),
    ('The rule may not say the full test suite passes.', False),
    ('The rule never says the full test suite passes.', False),
    ('The rule no longer says the full test suite passes.', False),
    ('Write local criteria rather than the full test suite passes.', False),
    ('Write local criteria instead of the full test suite passes.', False),
    ('The seed outlaws the full test suite passes.', False),
    ('The seed forbids the full test suite passes.', False),
    ('The sensor does not exempt the full test suite passes.', False),
    ('A bullet asserting the full test suite passes is rejected.', False),
    ('A bullet that asserts the full test suite passes is rejected.', False),
    ('The full test suite passed.', True),
    ('The full test suite is passing.', True),
    ('The full tests suite passes.', True),
    ('All remaining existing tests pass.', True),
    ('All other remaining existing tests pass.', False),
    # health-predicate window: the predicate ends exactly 120 / 121 chars past the phrase
    ('the full test suite xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx passes.', True),
    ('the full test suite xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx passes.', False),
    # runner window: the predicate ends exactly 24 / 25 chars past run_tests.py
    ('run_tests.py xxxxxxxxxxxxxxxx passes.', True),
    ('run_tests.py xxxxxxxxxxxxxxxxx passes.', False),
    # carve-out tail: 16 chars between the marker and the phrase exempts, 17 does not
    ('The rule must not xxxxxxxxxx the full test suite passes.', False),
    ('The rule must not xxxxxxxxxxx the full test suite passes.', True),
    # Round-5 qa reverification (final): the old endpos cut and the explicit end bound
    # agree at +1 and diverge at +2, where `pass` sat exactly at the cut; these two
    # rows are what makes reverting the explicit bound fail.
    ('the full test suite xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx passes.', False),
    ('run_tests.py xxxxxxxxxxxxxxxxxx passes.', False),
)


class SensorPolarityRegistryTests(unittest.TestCase):
    """Wave 1wuju (1wujs AC-1, AC-2): polarity is decided by the registry alone.

    Standalone (not a DocsLintFixtureTests subclass) so the fixture suite is not
    re-run under this class; the fixture helpers are borrowed by composition.
    """

    BULLET = "- [x] AC-1: All acceptance criteria are met and the full framework test suite passes.\n"

    def setUp(self) -> None:
        self.helper = DocsLintFixtureTests()

    def run_docs_lint(self, root: Path):
        return self.helper.run_docs_lint(root)

    def _wave_root(self) -> Path:
        root = self.helper.copy_fixture()
        self.helper._replace_acs(root, self.BULLET, "| AC-1 | required |\n")
        return root

    def test_polarity_is_decided_only_by_the_registry_entry(self) -> None:
        from unittest.mock import patch
        from wave_lint_lib import wave_validators
        from wave_lint_lib.constants import SENSOR_POLARITY_REGISTRY
        root = self._wave_root()
        try:
            for polarity, expect_failure in (("advisory", False), ("blocking", True)):
                with self.subTest(polarity=polarity):
                    entry = {"ac_asserts_repository_state": {"polarity": polarity, "introduced_wave": "1wur7"}}
                    warnings: list[str] = []
                    with patch.dict(SENSOR_POLARITY_REGISTRY, entry, clear=True):
                        failures = wave_validators.check_wave_docs(root, warnings=warnings)
                    hits_f = [f for f in failures if "asserts repository-wide state" in f]
                    hits_w = [w for w in warnings if "asserts repository-wide state" in w]
                    self.assertEqual(expect_failure, bool(hits_f), (polarity, failures))
                    self.assertEqual(not expect_failure, bool(hits_w), (polarity, warnings))
                    if hits_w:
                        self.assertIn("advisory sensor `ac_asserts_repository_state`", hits_w[0])
                        self.assertIn("introduced in wave `1wur7`", hits_w[0])
        finally:
            shutil.rmtree(root)

    def test_the_ac_locality_sensor_is_registered_advisory(self) -> None:
        # The first registrant; removing the registration makes the sensor blocking
        # again, which the public lint path shows as a failing exit.
        from wave_lint_lib.constants import SENSOR_POLARITY_REGISTRY
        self.assertEqual("advisory", SENSOR_POLARITY_REGISTRY["ac_asserts_repository_state"]["polarity"])
        self.assertEqual("1wur7", SENSOR_POLARITY_REGISTRY["ac_asserts_repository_state"]["introduced_wave"])
        root = self._wave_root()
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stderr, r"(?m)^WARNING: .*AC-1 asserts repository-wide state")
        self.assertNotRegex(result.stderr, r"(?m)^ERROR: .*asserts repository-wide state")

    def test_an_advisory_finding_without_a_sink_is_not_a_failure(self) -> None:
        # Direct callers that pass no sink get blocking findings only; advisory
        # findings are never promoted to failures by the absence of a sink.
        from wave_lint_lib import wave_validators
        root = self._wave_root()
        try:
            failures = wave_validators.check_wave_docs(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual([], [f for f in failures if "asserts repository-wide state" in f])

    def test_an_unregistered_sensor_stays_a_failure(self) -> None:
        # Delivery review QA-DEL-1: the pre-registry default is blocking; a sensor
        # with no registry entry is never routed to the warnings sink.
        from wave_lint_lib import wave_validators
        failures: list[str] = []
        warnings: list[str] = []
        wave_validators._route_sensor_findings("not_registered", ["x.md: finding"], failures, warnings)
        self.assertEqual(["x.md: finding"], failures)
        self.assertEqual([], warnings)

    def test_an_unknown_polarity_fails_loudly(self) -> None:
        # Delivery review ARCH-DEL-2: a misspelled polarity must not silently become
        # blocking (or advisory); the router validates against SENSOR_POLARITIES.
        from unittest.mock import patch
        from wave_lint_lib import wave_validators
        from wave_lint_lib.constants import SENSOR_POLARITIES, SENSOR_POLARITY_REGISTRY
        self.assertEqual(("advisory", "blocking"), SENSOR_POLARITIES)
        entry = {"typo_sensor": {"polarity": "advisry", "introduced_wave": "1wuju"}}
        with patch.dict(SENSOR_POLARITY_REGISTRY, entry, clear=True):
            with self.assertRaises(ValueError) as caught:
                wave_validators._route_sensor_findings("typo_sensor", ["x.md: finding"], [], [])
        self.assertIn("advisry", str(caught.exception))
        self.assertIn("typo_sensor", str(caught.exception))


class ReviewCycleChurnControlPinTests(unittest.TestCase):
    """Wave 1wuju (1wujr AC-1 to AC-3): every load-bearing sentence of the review-cycle
    controls is pinned on the seed that owns it and on the surfaces this repository reads."""

    SEEDS_DIR = SCRIPTS_ROOT.parent / "seeds"
    DOCS_DIR = SCRIPTS_ROOT.parent.parent.parent / "docs"

    def _seed(self, name: str) -> str:
        return (self.SEEDS_DIR / name).read_text(encoding="utf-8")

    def _doc(self, *parts: str) -> str:
        return self.DOCS_DIR.joinpath(*parts).read_text(encoding="utf-8")

    def test_seed_209_owns_the_round_protocol_and_the_landing_rule(self) -> None:
        seed = self._seed("209-agent-harness-core.prompt.md")
        self.assertIn("| `tree_fingerprint` | Content fingerprint of the reviewed paths at brief time: `git hash-object`", seed)
        self.assertIn("| `time_budget` | Wall-clock budget for the seat or lane", seed)
        self.assertIn("| `sweep_rule` | For delivery lanes: targeted tests per mutant, whole-file runs only for survivors", seed)
        self.assertIn("**Frozen tree per round (wave 1wuju):** while any lane runs against a briefing packet, no edit lands under `files_in_scope`.", seed)
        self.assertIn("`frozen_boundary` freezes the finding SET at convergence and `policy_input_digest` hashes change-document bodies; neither freezes code.", seed)
        self.assertIn("records a process finding, `tree_moved_under_review`, rather than re-sweeping silently", seed)
        self.assertIn("**External blocker escalation (wave 1wuju):**", seed)
        self.assertIn("presents the exact fix and a yes/no decision to the operator in the same message that reports the block", seed)
        self.assertIn("Repairs are batched once per round (wave 1wuju)", seed)
        self.assertIn("**Landing rule for guards (wave 1wuju).** A guard, validator member, carve-out, or tuning constant is landed only when a named test fails with it deleted or loosened", seed)
        self.assertIn("the lane's mutation table is the prose projection of `known_bad_detection_method: focused-mutation`", seed)
        self.assertIn("A census is re-derived whenever its predicate moves and is quoted only with the predicate that produced it", seed)
        # Delivery review QA-DEL-1: the four clauses Requirements 1 and 2 name that
        # the first pins left deletable.
        self.assertIn("(working-tree content, so modified and untracked files count)", seed)
        self.assertIn("The coordinator collects every lane's findings, repairs once per round, re-snapshots once, and issues a new packet with a new `tree_fingerprint`.", seed)
        self.assertIn("a pin that passes for an unrelated reason is not a pin. The implementer records the mutant and the failing test in the change document's Progress Log before requesting review.", seed)
        # Delivery review DOCS-DEL-2: the report-at-budget tail of the packet row.
        self.assertIn("| `time_budget` | Wall-clock budget for the seat or lane; report at the budget with what is in hand and list what was not run (wave 1wuju) |", seed)

    def test_seeds_180_and_190_carry_the_implementer_and_close_hooks(self) -> None:
        seed180 = self._seed("180-implement-feature.prompt.md")
        self.assertIn("Landing rule for guards (seed-209, wave 1wuju): a guard, validator member, carve-out, or tuning constant is landed only when a named test fails with it deleted or loosened", seed180)
        self.assertIn("record the mutant and the failing test in the change document's Progress Log before requesting review. A pin that passes for an unrelated reason is not a pin.", seed180)
        self.assertIn("presents the exact fix and a yes/no decision to the operator in the same message that reports the block (seed-209, wave 1wuju)", seed180)
        seed190 = self._seed("190-finalize-feature.prompt.md")
        self.assertIn("Do not finalize with an unreconciled `tree_moved_under_review` finding", seed190)

    def test_lane_seeds_require_the_mutation_table(self) -> None:
        for name in ("214-architecture-reviewer.prompt.md", "221-code-reviewer.prompt.md", "239-qa-reviewer.prompt.md"):
            with self.subTest(seed=name):
                seed = self._seed(name)
                self.assertIn("**mutation table** for every mechanism the wave landed in your scope (mechanism, mutation applied, failing test or NOT CAUGHT)", seed)
                self.assertIn("`known_bad_detection_method: focused-mutation` fields, not a second evidence shape", seed)
                self.assertIn("Follow the packet's `sweep_rule` (targeted tests per mutant, whole-file runs only for survivors) and `time_budget`", seed)
                self.assertIn("and `time_budget`; report at the budget and list what was not run (wave 1wuju).", seed)

    def test_prompt_surfaces_and_role_docs_are_reconciled(self) -> None:
        implement = self._doc("prompts", "implement-wave.prompt.md")
        self.assertIn("**Landing rule for guards** (seed 180/209, wave `1wuju`)", implement)
        self.assertIn("**External blockers** (seed 209): when a gate is blocked by an artifact this wave does not own", implement)
        review = self._doc("prompts", "review-wave.prompt.md")
        self.assertIn("Brief every lane with the seed-209 packet fields `tree_fingerprint` (`git hash-object` over the reviewed paths), `time_budget`, and `sweep_rule`", review)
        self.assertIn("**Frozen tree per round:** no edit lands under the reviewed paths while a lane runs", review)
        # Delivery review DOCS-DEL-2: the clauses the round-1 repair added.
        self.assertIn("Neither `frozen_boundary` nor `policy_input_digest` freezes code; a repair landed while a lane is still running invalidates that lane's evidence for the paths it touched. Each lane reports at its `time_budget` with what is in hand and lists what was not run.", review)
        close = self._doc("prompts", "close-wave.prompt.md")
        self.assertIn("Do not finalize with an unreconciled `tree_moved_under_review` finding", close)
        for role in ("architecture-reviewer.md", "qa-reviewer.md"):
            with self.subTest(role=role):
                self.assertIn("- a mutation table for every mechanism the wave landed in your scope (mechanism, mutation, failing test or NOT CAUGHT)", self._doc("agents", role))
        for role in ("architecture-reviewer.md", "qa-reviewer.md", "code-reviewer.md"):
            with self.subTest(role=role, clause="report-at-budget"):
                self.assertIn("; report at the budget and list what was not run (seed 209, wave `1wuju`)", self._doc("agents", role))
        self.assertIn("which named test fails with it deleted or loosened? Report it in a mutation table", self._doc("agents", "code-reviewer.md"))
        self.assertIn("## Landing Rule for Guards (wave 1wuju)", self._doc("architecture", "testing-architecture.md"))
        self.assertIn("A census is re-derived whenever\nits predicate moves and is quoted only with the predicate that produced it; a\nfigure carried forward from an earlier predicate is a stale claim, not evidence.", self._doc("architecture", "testing-architecture.md"))
        self.assertIn("**Review-cycle churn controls in the seeds.**", (self.DOCS_DIR.parent / "CHANGELOG.md").read_text(encoding="utf-8"))


class AdvisoryFirstRulePinTests(unittest.TestCase):
    """Wave 1wuju (1wujs AC-3, AC-5): the advisory-first rule and the polarity of the
    first registrant are stated on every surface a planner, closer, or releaser reads."""

    SEEDS_DIR = SCRIPTS_ROOT.parent / "seeds"
    DOCS_DIR = SCRIPTS_ROOT.parent.parent.parent / "docs"

    def test_seed_170_states_the_advisory_first_rule_and_the_registered_polarity(self) -> None:
        seed = (self.SEEDS_DIR / "170-plan-feature.prompt.md").read_text(encoding="utf-8")
        self.assertIn("**New docs-lint sensors ship advisory.**", seed)
        self.assertIn("The sensor is registered `advisory` in the docs-lint\nsensor polarity registry", seed)
        self.assertIn("a flip to\n`blocking` is a separate recorded change made on field data", seed)
        self.assertNotIn("enforces this as a blocking\nerror", seed)

    def test_seed_190_treats_advisory_findings_as_review_notes(self) -> None:
        seed = (self.SEEDS_DIR / "190-finalize-feature.prompt.md").read_text(encoding="utf-8")
        self.assertIn("are review notes at close, never a closure blocker", seed)

    def test_prompt_surfaces_and_contributing_docs_are_reconciled(self) -> None:
        plan = (self.DOCS_DIR / "prompts" / "plan-feature.prompt.md").read_text(encoding="utf-8")
        self.assertIn("runs an advisory sensor on change documents", plan)
        self.assertIn("new docs-lint sensors ship advisory the same way", plan)
        # Delivery review DOCS-DEL-2: the two seed-170 clauses the round-1 repair added.
        self.assertIn("(the release checklist lists every sensor still advisory so the flip is decided, not forgotten)", plan)
        self.assertIn("The diagnostic supplies the replacement sentence: write \"the change's own suites", plan)
        close = (self.DOCS_DIR / "prompts" / "close-wave.prompt.md").read_text(encoding="utf-8")
        self.assertIn("are review notes at close, never a closure blocker", close)
        workflow = (self.DOCS_DIR / "contributing" / "change-workflow.md").read_text(encoding="utf-8")
        self.assertIn("an advisory sensor (a `WARNING:` line that never\nfails validation", workflow)
        spec = (self.DOCS_DIR / "specs" / "mcp-tool-surface.md").read_text(encoding="utf-8")
        self.assertIn("Advisory findings never block Prepare, Review, or Close", spec)

    def test_the_release_checklist_lists_advisory_sensors(self) -> None:
        package = (self.DOCS_DIR / "prompts" / "package-wavefoundry.prompt.md").read_text(encoding="utf-8")
        self.assertIn("list every sensor still registered `advisory`", package)
        self.assertIn("never a release-day edit", package)


class AcRuleDiscriminationMatrixTests(unittest.TestCase):
    """Every alternation member of the AC-shape rule has a case that pins it."""

    def test_every_matrix_row_behaves_as_recorded(self) -> None:
        from wave_lint_lib import wave_validators

        for body, should_fire in AC_RULE_MATRIX:
            with self.subTest(body=body):
                got = wave_validators._ac_repo_state_match(f"- [ ] AC-1: {body}")
                self.assertEqual(should_fire, bool(got), body)

    def test_the_matrix_covers_every_alternation_member(self) -> None:
        """A coverage floor, so a member added later without a probe is caught.

        This reads the module deliberately -- it is the one assertion whose job is
        to notice that the module grew past the matrix.
        """
        from wave_lint_lib import wave_validators

        corpus = " ".join(body for body, _ in AC_RULE_MATRIX).lower()
        # Every word-list alternation the rule is built from (round-5 code and qa
        # reverification: the floor once read only two of them, so a member added
        # to any other constant without a row went unnoticed).
        for constant in ("_AC_REPO_SCOPE", "_AC_SCOPE_GAP_WORD", "_AC_TEST_CORPUS_NOUN",
                         "_AC_REPO_REFERENT", "_AC_NARROWER_NOUN", "_AC_NOT_REPO_WIDE",
                         "_AC_HEALTH_PREDICATE_RE", "_AC_REPO_STATE_CARVE_OUT_RE"):
            pattern = getattr(wave_validators, constant)
            pattern = getattr(pattern, "pattern", pattern)
            members = [m for m in re.findall(r"[a-z][a-z-]+", pattern.lower())
                       if m not in {"the", "or", "and"}]
            uncovered = sorted({m for m in members if m not in corpus})
            self.assertEqual([], uncovered,
                             f"{constant} members with no probe in AC_RULE_MATRIX")
        # The quoted-span exemption has three delimiter branches; each needs a row
        # whose outcome depends on it (round-5 code reverification, M15b).
        raw = " ".join(body for body, _ in AC_RULE_MATRIX)
        for delimiter in ("`", '"', "\u201c"):
            self.assertIn(delimiter, raw,
                          f"no AC_RULE_MATRIX row exercises the {delimiter!r} span branch")


class CouncilSeedVerificationContractTests(unittest.TestCase):
    """1p9pk AC-5: the council-review seed carries the code-grounded verification and
    roster-honesty contracts; the moderator and review-hub seeds point at them."""

    SEEDS_DIR = SCRIPTS_ROOT.parent / "seeds"

    def test_seed_237_requires_code_grounded_verification(self) -> None:
        text = (self.SEEDS_DIR / "237-council-review.prompt.md").read_text(encoding="utf-8")
        self.assertIn("Verify code-grounded", text)
        self.assertIn("sites and symbols must resolve", text)
        self.assertIn("censuses must be complete", text)

    def test_seed_237_code_grounded_rule_is_pinned_exactly(self) -> None:
        """1tmb4 AC-6 (seed site): exact-value pin over the full rule line.

        The 1p9pk test above asserts substring presence only; a reworded rule
        that keeps the substrings would pass it.  This pin fails on ANY change
        to the rule text, so 1tmb4's additions provably cannot weaken the
        review-side rule.  Wording here intentionally differs from the server
        brief ('the artifact's' vs 'each plan's'); one pin cannot cover both.
        """
        text = (self.SEEDS_DIR / "237-council-review.prompt.md").read_text(encoding="utf-8")
        pinned = (
            "- **Verify code-grounded:** check the artifact's load-bearing claims "
            "against the actual tree, not against the artifact's own prose — cited "
            '`file:line` sites and symbols must resolve, "X already does Y" claims '
            'must hold in the code, and "no other caller/site" censuses must be '
            "complete. Do not approve an artifact whose claims were checked only "
            "against its own text. (A readiness review answerable purely from plan "
            "prose is how nonexistent symbols, wrong caller censuses, and no-op "
            "mechanisms pass review.)"
        )
        self.assertIn(pinned, text)
        # Finding 1tmb4-ac8-live-copy-sweep-claim-unexecuted: the live
        # self-hosted copy of this rule sits OUTSIDE any renderer-owned
        # marker region, so no re-render reaches it.  Pin it here so a seed
        # 237 edit cannot silently strand the operative copy.
        live_copy = (
            SCRIPTS_ROOT.parent.parent.parent
            / "docs" / "prompts" / "council-review.prompt.md"
        )
        if live_copy.exists():  # absent in target repos
            self.assertIn(pinned, live_copy.read_text(encoding="utf-8"), "live council-review copy")

    # 1v1c4: the 1uu9y resolvable-anchor AUTHORING paragraph has no renderer
    # sync (it sits outside BOTH renderer-owned marker regions of the live
    # prompt copy: wavefoundry:review-policy and wave:executable-review-
    # evidence), so these exact-value pins are its sync mechanism, per the
    # 1tmb4 precedent above.  The 1v1c4 carrier census found the seed copies
    # equally unpinned (the clause pin in test_server_tools covers only the
    # runtime brief), so the class is retired here once: seed 237 + live copy
    # in one pin, seed 209's audience variant in the other.

    CITATION_PARAGRAPH_237 = (
        "When a council seat writes a finding that cites code, cite a "
        "**resolvable anchor** — a function, class, method, constant, test "
        "name, or a distinguishing expression — rather than a bare "
        "`file:line`. The reason is not tidiness, it is resolvability: "
        "`code_definition(symbol)` and `code_read` return today's text for a "
        "symbol anchor, while a line anchor can only be checked and drifts "
        "hardest when a sibling wave concurrently edits the target. A line "
        "number is still correct for a module-level constant block, data "
        "file, specific line in a generated artifact, prose in a "
        "hand-authored markdown document, or deliberately historical "
        "citation; name that case inline so a reviewer can distinguish a "
        "deliberate line anchor from a lapsed one. Deliberately historical "
        "citations, including line numbers already written into a change "
        "document's `## Progress Log` or `## Decision Log` rows, record what "
        "was verified at the time and are never rewritten to symbols."
    )

    def test_1uu9y_citation_paragraph_pinned_in_seed_237_and_live_copy(self) -> None:
        """1v1c4 AC-1: byte-exact pin naming seed 237 as canonical."""
        seed_text = (self.SEEDS_DIR / "237-council-review.prompt.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            self.CITATION_PARAGRAPH_237,
            seed_text,
            "seed 237 lost the 1uu9y citation-authoring paragraph; the seed "
            "is canonical, so update the pin AND the live copy together",
        )
        live_copy = (
            SCRIPTS_ROOT.parent.parent.parent
            / "docs" / "prompts" / "council-review.prompt.md"
        )
        if live_copy.exists():  # absent in target repos
            self.assertIn(
                self.CITATION_PARAGRAPH_237,
                live_copy.read_text(encoding="utf-8"),
                "live council-review copy drifted from seed 237's "
                "citation-authoring paragraph; no re-render reaches it, so "
                "align it with the seed by hand",
            )

    def test_ac_locality_rule_pinned_in_seed_170_and_reconciled_prompt(self) -> None:
        """Wave 1wur7 (1wuui AC-1): the AC-locality rule and its replacement shape.

        Delivery review DOCS-DEL-3 / QA-DEL-1 found this pin missing while AC-1
        was marked complete and named it: the entire section could be deleted and
        every test stayed green. The load-bearing sentences are pinned here, plus
        the reconciled sentence in the project-owned prompt doc, because no
        renderer owns either file and nothing else would notice the drift.
        """
        seed = (self.SEEDS_DIR / "170-plan-feature.prompt.md").read_text(encoding="utf-8")
        self.assertIn(
            "### Acceptance criteria assert what the change controls", seed,
            "seed 170 AC-locality section header")
        self.assertIn(
            "An acceptance criterion states an outcome **this change owns** and that a\n"
            "reviewer can verify from **this change's own evidence**.", seed,
            "seed 170 AC-locality head sentence")
        self.assertIn(
            "is a **gate**\nconcern, not an acceptance criterion, and must not be written as one.", seed,
            "seed 170 gate-versus-criterion rule")
        self.assertIn(
            "- [ ] AC-6: All acceptance criteria are met and the full framework test suite passes.",
            seed, "seed 170 banned-shape example")
        self.assertIn(
            "The change's own suites and every test it adds pass; the documents", seed,
            "seed 170 replacement shape")
        self.assertIn(
            "not \"documentation validation passes\"", seed,
            "seed 170 qualifier against the unqualified docs-validation clause")
        self.assertIn(
            "This rule is also mechanically enforced", seed,
            "seed 170 must name the sensor an author will hit (DOCS-DEL-12)")
        self.assertIn(
            "name the gate that will\nenforce it in this repository", seed,
            "seed 170 must not promise a close gate that a pack-vendored repo lacks "
            "(ARCH-DEL-4)")
        prompt = (SCRIPTS_ROOT.parent.parent.parent / "docs" / "prompts"
                  / "plan-feature.prompt.md").read_text(encoding="utf-8")
        self.assertIn(
            "An acceptance criterion asserts an outcome **this change controls**", prompt,
            "docs/prompts/plan-feature.prompt.md reconciled AC-locality rule")
        self.assertIn(
            "the state of files this change never touches", prompt,
            "the prompt keeps the seed's fourth example (DOCS-DEL-12)")

    def test_possessive_apostrophes_do_not_form_a_swallowing_span(self) -> None:
        """Reverification mutant D2: re-adding the straight-apostrophe branch to
        `_AC_CODE_SPAN_RE` restored the defect while all 1058 tests stayed green.
        That is the untested-mechanism pattern this wave exists to eliminate, so
        the removal is pinned directly."""
        from wave_lint_lib import wave_validators

        self.assertNotIn("'", wave_validators._AC_CODE_SPAN_RE.pattern,
                         "a straight-apostrophe span branch lets two ordinary "
                         "possessives bracket and swallow the clause")
        bracketed = ("- [ ] AC-4: the repository's full test suite passes and the "
                     "wave's evidence records it.")
        self.assertEqual("full test suite",
                         wave_validators._ac_repo_state_match(bracketed))

    def test_repository_wide_shapes_with_intervening_modifiers_fire(self) -> None:
        """Reverification measured 70 unambiguous repository-wide criteria the
        first matcher missed because it required the quantifier and the corpus
        noun to be adjacent. These are the live-corpus forms."""
        from wave_lint_lib import wave_validators

        for body in (
            "All existing tests pass.",
            "All 944 tests pass.",
            "All pre-existing framework tests pass.",
            "The full repository test suite passes.",
            "Full framework tests run bytecode-free and docs validation passes.",
            "All tests in CI pass.",
            "Every test in tests/ passes.",
            "The full suite is green with no new skips.",
        ):
            with self.subTest(body=body):
                self.assertIsNotNone(
                    wave_validators._ac_repo_state_match(f"- [ ] AC-1: {body}"), body)

    def test_change_local_modifiers_inside_the_scope_gap_do_not_fire(self) -> None:
        """Reverification D1: widening the quantifier-to-noun gap to recover 78
        real detections also admitted a false-positive class on change-local
        shapes. A blocking rule must not reject `All new tests pass`."""
        from wave_lint_lib import wave_validators

        for body, should_fire in (
            ("All new tests pass.", False),
            ("All added tests pass.", False),
            ("All three new tests pass.", False),
            ("Every new regression test passes.", False),
            ("All updated tests pass.", False),
            ("All modified tests pass.", False),
            ("All newly written tests pass.", False),
            # A bare total is a repository-wide assertion and must still fire.
            ("All 944 tests pass.", True),
            ("All existing tests pass.", True),
        ):
            with self.subTest(body=body):
                got = wave_validators._ac_repo_state_match(f"- [ ] AC-1: {body}")
                self.assertEqual(should_fire, bool(got), body)
        # A loop that reads the alternation from the module under test cannot
        # detect a deletion: removing an alternative removes the subtest that would
        # have covered it. The discriminating cases live in AC_RULE_MATRIX below,
        # as literal data.

    def test_repository_wide_path_referents_are_reachable(self) -> None:
        """Reverification D4: `tests/` and `.wavefoundry/` were followed by a word
        boundary, which can never match after a slash, so both alternatives were
        dead code behind a pin that passed for an unrelated reason."""
        from wave_lint_lib import wave_validators

        self.assertIsNotNone(wave_validators._ac_repo_state_match(
            "- [ ] AC-1: All tests under .wavefoundry/ pass."))
        # Reverification: the shape above matches through the widened scope gap
        # (quantifier `All`, gap `tests under`, noun `tests`) and never touches the
        # referent, so it would survive deleting `tests/` -- the same passes-for-an-
        # unrelated-reason mechanism this wave exists to eliminate. This one is
        # discriminating: remove `tests/` from the referent and it goes silent.
        self.assertIsNotNone(wave_validators._ac_repo_state_match(
            "- [ ] AC-2: The full test suite in tests/ passes."))
        # The referent is what makes these repository-wide rather than narrowed;
        # a genuinely specific target in the same position stays silent.
        self.assertIsNone(wave_validators._ac_repo_state_match(
            "- [ ] AC-3: All tests under `tests/fixtures/retrieval_eval/` pass."))

    def test_a_change_whose_subject_is_the_runner_is_not_flagged(self) -> None:
        """Reverification found the bare `run_tests.py` token flagged bullets whose
        subject is the runner itself, including a real closed-wave criterion about
        its caching behaviour. A focused invocation is change-local."""
        from wave_lint_lib import wave_validators

        self.assertIsNone(wave_validators._ac_repo_state_match(
            "- [ ] AC-1: `run_tests.py --file test_chunker.py` passes."))
        self.assertIsNone(wave_validators._ac_repo_state_match(
            "- [ ] AC-2: `run_tests.py` gains `--no-cache`, and the focused chunker "
            "file passes."))
        # Reverification D3: the two guards must be pinned SEPARATELY. Removing the
        # focused-invocation lookahead was undetectable by the whole suite, because
        # the predicate window alone suppressed both fixtures above. This shape puts
        # the predicate inside the window, so only the lookahead can silence it.
        self.assertIsNone(wave_validators._ac_repo_state_match(
            "- [ ] AC-4: `run_tests.py --file test_x.py` pass"))
        # Reverification N1: the runner pattern carries TWO lookaheads and only
        # their conjunction was pinned, so either could be deleted alone with the
        # suite green. This shape is suppressed only by the bare `--file` guard.
        self.assertIsNone(wave_validators._ac_repo_state_match(
            "- [ ] AC-5: `run_tests.py --file` passes."))
        self.assertIsNone(wave_validators._ac_repo_state_match(
            "- [ ] AC-6: run_tests.py --file passes."))
        self.assertEqual("run_tests.py", wave_validators._ac_repo_state_match(
            "- [ ] AC-3: `python3 .wavefoundry/framework/scripts/run_tests.py` passes."))

    def test_health_predicate_window_keeps_an_incidental_mention_silent(self) -> None:
        """QA-DEL-8: the window that rejects an aside had no test, so widening it
        (the direction that produces false positives on live change docs) was
        invisible to the suite."""
        from wave_lint_lib import wave_validators

        # Modelled on a real closed-wave bullet: the suite is mentioned as an
        # incidental aside, and the nearest health predicate belongs to a
        # different clause far away.
        aside = ("- [ ] AC-12: Performance benchmark deferred; no field reports of a regression "
                 "at production graph sizes (full test suite at 2200 tests still runs in ~65s), "
                 "and the deferral is tracked for opportunistic verification at the next field "
                 "validation window rather than blocking this wave, so the reproducer fixture "
                 "passes.")
        self.assertIsNone(wave_validators._ac_repo_state_match(aside))
        self.assertLessEqual(wave_validators._AC_HEALTH_PREDICATE_WINDOW, 200)
        widened = wave_validators._AC_HEALTH_PREDICATE_WINDOW
        try:
            wave_validators._AC_HEALTH_PREDICATE_WINDOW = 100000
            self.assertEqual("full test suite", wave_validators._ac_repo_state_match(aside),
                             "a widened window must be observable as a false positive")
        finally:
            wave_validators._AC_HEALTH_PREDICATE_WINDOW = widened

    def test_1urlb_citation_variant_pinned_in_seed_170(self) -> None:
        """1v1dh: the author-phase citation variant, head sentence exact plus
        load-bearing clauses (the resolvability reason and the carve-out
        table), unconditional per the family's failure-not-skip rule."""
        text = (self.SEEDS_DIR / "170-plan-feature.prompt.md").read_text(
            encoding="utf-8"
        )
        head = (
            "When a change document cites code, cite a **resolvable anchor** "
            "— a function, class, method, constant, test name, or a "
            "distinguishing expression — rather than a bare `file:line`."
        )
        self.assertIn(head, text, "seed 170 citation-variant head sentence")
        self.assertIn(
            "A symbol anchor can be *resolved*", text,
            "seed 170 resolvability reason",
        )
        self.assertIn(
            "**A line number is still correct in these cases**", text,
            "seed 170 carve-out header",
        )
        self.assertIn(
            "| A module-level constant block | No containing symbol |", text,
            "seed 170 carve-out table first case",
        )

    def test_1urlb_citation_variant_pinned_in_seed_180(self) -> None:
        """1v1dh: the implement-phase citation bullet, head exact plus the
        anchor vocabulary (as seed 180 words it), the name-the-case-inline
        obligation, and the history-falsification clause."""
        text = (self.SEEDS_DIR / "180-implement-feature.prompt.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "**Cite by symbol, so the citation survives the cycle.**", text,
            "seed 180 bullet head",
        )
        self.assertIn(
            "cite a **resolvable anchor** — a function, class, method, "
            "constant, test name, or distinguishing expression — rather than "
            "a bare `file:line`.",
            text,
            "seed 180 anchor vocabulary (wording differs from seed 170 by "
            "one article; pinned as the seed reads)",
        )
        self.assertIn(
            "**Name the case inline when you rely on it.**", text,
            "seed 180 name-the-case obligation",
        )
        self.assertIn(
            "repairing them to symbols falsifies the history", text,
            "seed 180 history-falsification clause",
        )

    def test_1uu9y_citation_paragraph_pinned_in_seed_209(self) -> None:
        """1v1c4 AC-2 census closure: seed 209's audience variant, same pin."""
        variant = (
            "When `artifact_or_test_id` or review-evidence prose cites code, "
            "cite a **resolvable anchor** — a function, class, method, "
            "constant, test name, or a distinguishing expression — rather "
            "than a bare `file:line`."
        )
        immutable_tail = (
            "An appended evidence record is immutable: deliberately "
            "historical anchors record what was verified at the time and are "
            "never rewritten to symbols."
        )
        seed_text = (self.SEEDS_DIR / "209-agent-harness-core.prompt.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(variant, seed_text, "seed 209 authoring-rule head")
        self.assertIn(immutable_tail, seed_text, "seed 209 immutability tail")
        shared_middle = (
            "A line number is still correct for a module-level constant "
            "block, data file, specific line in a generated artifact, prose "
            "in a hand-authored markdown document, or deliberately "
            "historical citation; name that case inline so a reviewer can "
            "distinguish a deliberate line anchor from a lapsed one."
        )
        self.assertIn(shared_middle, seed_text, "seed 209 shared carve-outs")
        self.assertIn(shared_middle, self.CITATION_PARAGRAPH_237)

    def test_code_grounded_tenet_stated_once_in_seed_209(self) -> None:
        """1tmb4 AC-1: one canonical definition sentence, in seed 209 only.

        Forbids duplicating the DEFINITION sentence; phase seeds carry their
        own phase obligations (AC-2), which this test must not forbid.
        """
        canonical = (
            "Code-grounded verification is a tenet of creating, reviewing, and "
            "implementing: a load-bearing claim about existing code is verified "
            "against the actual tree, executed where executable, before it is "
            "asserted, approved, or built upon."
        )
        seed_209 = (self.SEEDS_DIR / "209-agent-harness-core.prompt.md").read_text(encoding="utf-8")
        self.assertEqual(seed_209.count(canonical), 1, "canonical statement missing or duplicated in 209")
        for name in (
            "170-plan-feature.prompt.md",
            "180-implement-feature.prompt.md",
            "211-guru.prompt.md",
            "237-council-review.prompt.md",
            "215-wave-council.prompt.md",
        ):
            text = (self.SEEDS_DIR / name).read_text(encoding="utf-8")
            self.assertNotIn(canonical, text, f"{name} duplicates the canonical definition sentence")

    def test_authoring_seed_carries_code_grounded_obligation(self) -> None:
        """1tmb4 AC-2/AC-3: seed 170 states the authoring obligation, names the
        three high-risk claim shapes, and carries the fix-absent AC rule."""
        text = (self.SEEDS_DIR / "170-plan-feature.prompt.md").read_text(encoding="utf-8")
        self.assertIn("Code-grounded authoring", text)
        self.assertIn("X already does Y", text)
        self.assertIn("no other caller/site", text)
        self.assertIn("an implementation with the fix absent cannot satisfy it", text)
        # 1tmb4 AC-3 (delivery finding 1tmb4-ac3-consistency-pin-one-sided):
        # the pairing pin covers BOTH sides of the fix-absent rule.  The
        # authoring side is asserted above; the review side lives in seed
        # 209's canonical tenet section and is pinned here so drift on
        # either side breaks the suite.
        seed_209 = (self.SEEDS_DIR / "209-agent-harness-core.prompt.md").read_text(encoding="utf-8")
        self.assertIn(
            "- **Reviewing** (seed-237, seed-215): the per-seat contract already "
            "requires this; do not approve an artifact whose claims were checked "
            "only against its own text.",
            seed_209,
        )
        # The review side AC-3 actually anchors on is the reviewer KNOWN-BAD
        # rule (209:126-region), which 170's new sentence names as its
        # counterpart.  Pin its load-bearing sentence so a material weakening
        # (e.g. "would fail" -> "should plausibly fail") breaks the suite.
        self.assertIn(
            "Before accepting a claimed check in either phase, confirm that it "
            "ran with zero unintended skips, reached the claimed public path or "
            "faithful boundary for its phase, used realistic boundary return "
            "shapes, made non-vacuous assertions, and would fail against the "
            "known-bad behavior",
            seed_209,
        )

    def test_implement_seed_carries_premise_exercise_obligation(self) -> None:
        """1tmb4 AC-4: seed 180 requires exercising a plan premise before
        building on it, with the stop-and-report path."""
        text = (self.SEEDS_DIR / "180-implement-feature.prompt.md").read_text(encoding="utf-8")
        self.assertIn("A plan is evidence, not proof.", text)
        self.assertIn("stop and report", text)

    def test_exploration_order_sites_carry_reading_vs_executing(self) -> None:
        """1tmb4 AC-5 (delivery finding 1tmb4-ac5-test-not-signature-keyed):
        every surface carrying the exploration order also carries the
        reading-versus-executing distinction.

        Detection is keyed on the ORDER'S STRUCTURAL SIGNATURE, not a file
        list, so a copied or paraphrased exploration order in any seed (or
        the live guru.md) is caught even though this test never names it.
        Signature forms, each verified to discriminate exactly on the real
        tree (matches 180, 211, guru.md; matches none of the ~26 role seeds
        whose tool-posture leads mention tools without restating the order):
        a numbered `code_*` list, the Tool Selection Quick Rules heading, or
        a run of `- Use `code_...`` bullets.  Mention-counting (e.g. four of
        five tool names present) was measured and rejected: it trips 26
        point-do-not-restate posture leads."""
        distinction = "Reading code is not executing it"

        def carries_exploration_order(text: str) -> bool:
            # Marker classes cover Markdown-equivalent forms (finding
            # 1tmb4-ac5-signature-misses-markdown-equivalent-markers): '*'
            # and '+' bullets render like '-', and 'N)' numbering like 'N.'.
            numbered = len(re.findall(r"(?m)^\s*\d+[.)]\s+`code_", text)) >= 3
            heading = "Tool Selection Quick Rules" in text
            use_bullets = len(re.findall(r"(?m)^[-*+] Use `code_", text)) >= 3
            return numbered or heading or use_bullets

        targets = sorted(self.SEEDS_DIR.glob("*.prompt.md"))
        live_guru = SCRIPTS_ROOT.parent.parent.parent / "docs" / "agents" / "guru.md"
        if live_guru.exists():  # absent in target repos without the Guru surface
            targets.append(live_guru)
        carriers = []
        for path in targets:
            text = path.read_text(encoding="utf-8")
            if carries_exploration_order(text):
                carriers.append(path.name)
                self.assertIn(
                    distinction,
                    text,
                    f"{path} carries the exploration order without the "
                    "reading-versus-executing distinction",
                )
        # Non-vacuity guard: the known carriers must trip the signature, so
        # a signature regression cannot silently empty the scan domain.
        for known in ("180-implement-feature.prompt.md", "211-guru.prompt.md"):
            self.assertIn(known, carriers)

    def test_seed_237_carries_roster_honesty_contract(self) -> None:
        text = (self.SEEDS_DIR / "237-council-review.prompt.md").read_text(encoding="utf-8")
        self.assertIn("Roster honesty", text)
        self.assertIn("seats *actually run*, each at most once", text)
        self.assertIn("does not self-certify", text)

    def test_seed_215_cross_references_recording_contract(self) -> None:
        text = (self.SEEDS_DIR / "215-wave-council.prompt.md").read_text(encoding="utf-8")
        self.assertIn("typed `wave-council-readiness` approval", text)
        self.assertIn("legacy waves retain the structured verdict contract", text)

    def test_seed_007_points_at_roster_evidence_consistency(self) -> None:
        text = (self.SEEDS_DIR / "007-review-system-overview.md").read_text(encoding="utf-8")
        self.assertIn("typed approval event in `events.jsonl`", text)
        self.assertIn("not machine authority", text)
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


class WaveOwnedChangeDocGateTests(unittest.TestCase):
    """1v0lx Requirement 3: both conjuncts of the existence-check gate, so a
    re-derivation can neither miss `implementing` again nor delete the
    seed-driven `Activated at:` fallback on a dead-code theory."""

    @staticmethod
    def _wave_text(status: str, activated: str | None = None) -> str:
        lines = ["# Wave Record", "", "Owner: Engineering", f"Status: {status}"]
        if activated is not None:
            lines.append(f"Activated at: {activated}")
        return "\n".join(lines) + "\n"

    def test_status_set_and_activation_fallback(self) -> None:
        from wave_lint_lib.wave_validators import (
            _wave_requires_wave_owned_change_docs,
        )

        cases = [
            ("active", None, True),
            ("ready", None, True),
            ("implementing", None, True),
            ("implementing", "2026-08-11T00:00:00Z", True),
            ("planned", None, False),
            ("planned", "2026-08-11T00:00:00Z", True),
            ("planned", "not activated", False),
            ("completed", None, False),
            ("closed", None, False),
            ("closed", "2026-08-11T00:00:00Z", False),
        ]
        for status, activated, expected in cases:
            with self.subTest(status=status, activated=activated):
                self.assertIs(
                    _wave_requires_wave_owned_change_docs(
                        self._wave_text(status, activated)
                    ),
                    expected,
                )


class ReviewPolicyCarrierParityTests(unittest.TestCase):
    """1v1c5: docs-lint fails when a rendered review-policy region differs from
    its registered block source, composed via the RENDERER'S OWN helper (the
    1us4q no-parallel-parser lesson). Dispositions pinned here as named
    behavior: missing file skipped; exists-with-neither-marker skipped (the
    base fixture holds that state); malformed markers FAIL; drift in either
    direction FAILS."""

    FIXTURE_CARRIER = "docs/references/project-overview.md"

    @staticmethod
    def _modules():
        import render_agent_surfaces as ras
        import review_policy
        from wave_lint_lib.core_validators import (
            check_review_policy_carrier_parity,
        )
        return review_policy, ras, check_review_policy_carrier_parity

    def _carrier(self):
        review_policy, _, _ = self._modules()
        return next(
            row
            for row in review_policy.REVIEW_POLICY_CARRIER_REGISTRY
            if row.destination == self.FIXTURE_CARRIER and row.owner == "renderer"
        )

    def _root_with_rendered_region(self):
        review_policy, ras, _check = self._modules()
        carrier = self._carrier()
        block = review_policy.REVIEW_POLICY_SURFACE_BLOCKS[carrier.destination]
        root = Path(tempfile.mkdtemp(prefix="parity-fixture-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        path = root / carrier.destination
        path.parent.mkdir(parents=True, exist_ok=True)
        base = "# Fixture carrier\n\nProject prose stays untouched.\n"
        rendered = ras._upsert_review_policy_region(base, block)
        self.assertIsNotNone(rendered)
        path.write_text(rendered, encoding="utf-8")
        return root, carrier, block, path

    def test_matching_region_passes(self) -> None:
        _, _, check = self._modules()
        root, _carrier, _block, _path = self._root_with_rendered_region()
        self.assertEqual(check(root), [])

    def test_hand_edit_inside_region_fails(self) -> None:
        """AC-4: the drift direction likelier in a self-hosting repo."""
        _, _, check = self._modules()
        root, carrier, block, path = self._root_with_rendered_region()
        text = path.read_text(encoding="utf-8")
        tampered = text.replace(block, block + "\nhand-edited addition", 1)
        self.assertNotEqual(tampered, text)
        path.write_text(tampered, encoding="utf-8")
        failures = check(root)
        self.assertEqual(len(failures), 1, failures)
        self.assertIn(carrier.destination, failures[0])
        self.assertIn("reconcile_review_policy_surfaces", failures[0])

    def test_block_edit_without_rerender_fails(self) -> None:
        """AC-1: the direction that motivated the change (1us4q shipped it)."""
        review_policy, _, check = self._modules()
        root, carrier, block, _path = self._root_with_rendered_region()
        with patch.dict(
            review_policy.REVIEW_POLICY_SURFACE_BLOCKS,
            {carrier.destination: block + "\n\nNew registered obligation."},
        ):
            failures = check(root)
        self.assertEqual(len(failures), 1, failures)
        self.assertIn(carrier.destination, failures[0])
        self.assertIn("reconcile_review_policy_surfaces", failures[0])
        self.assertEqual(check(root), [], "patch.dict must restore parity")

    def test_regionless_existing_carrier_is_skipped(self) -> None:
        """Requirement 2: presence/adoption stays the existing checks'
        business; a naive exists-implies-region rule would fail the base
        fixture, which holds this exact state today."""
        _, _, check = self._modules()
        root, _carrier, _block, path = self._root_with_rendered_region()
        path.write_text("# Fixture carrier\n\nNo markers at all.\n", encoding="utf-8")
        self.assertEqual(check(root), [])

    def test_protocol_family_half_paired_markers_fail(self) -> None:
        """1v4mt AC-1: the SECOND rendered marker family gets the same
        disposition as the first.

        Field-observed (downstream, 1.13.0 to 1.16.1): a broken begin marker
        left four reviewer role docs half-paired through a full upgrade cycle,
        silently receiving no review-protocol updates, while docs-lint reported
        ok and the docs gate PASSED every run. The renderer's warn-and-skip is
        correct for a reconciler; a gate must not share it.

        The exact reported shape is used: end marker present, begin removed.
        """
        import render_agent_surfaces as ras
        from wave_lint_lib.core_validators import (
            check_review_protocol_carrier_parity,
        )

        root = Path(tempfile.mkdtemp(prefix="protocol-parity-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        carrier = next(iter(ras.review_protocol_carriers(root)))
        path = root / carrier.destination
        path.parent.mkdir(parents=True, exist_ok=True)
        block = ras._carrier_protocol_block(carrier)
        rendered = ras._upsert_review_protocol_region(
            "# Fixture role doc\n\nRole prose stays untouched.\n", block
        )
        self.assertIsNotNone(rendered)
        path.write_text(rendered, encoding="utf-8")
        self.assertEqual(check_review_protocol_carrier_parity(root), [],
                         "a well-formed region must pass (AC-3)")

        half_paired = rendered.replace(ras.REVIEW_PROTOCOL_MARKER_BEGIN, "", 1)
        self.assertIn(ras.REVIEW_PROTOCOL_MARKER_END, half_paired)
        self.assertNotIn(ras.REVIEW_PROTOCOL_MARKER_BEGIN, half_paired)
        path.write_text(half_paired, encoding="utf-8")

        failures = check_review_protocol_carrier_parity(root)
        self.assertEqual(len(failures), 1, failures)
        self.assertIn(carrier.destination, failures[0], "AC-2: name the file")
        self.assertIn("marker", failures[0].lower(), "AC-2: name the condition")

    def test_protocol_family_registered_on_full_and_incremental_paths(self) -> None:
        """1v4mt AC-1, registration half: an unregistered gate is the exact
        defect class here, so assert the half-paired carrier fails through
        `cli._run_full_checks` and through the incremental hook."""
        import argparse
        import unittest.mock as mock

        import render_agent_surfaces as ras
        import wave_lint_lib.cli as cli

        root = Path(tempfile.mkdtemp(prefix="protocol-registration-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        shutil.copytree(FIXTURE_ROOT, root, dirs_exist_ok=True)
        carrier = next(iter(ras.review_protocol_carriers(root)))
        path = root / carrier.destination
        path.parent.mkdir(parents=True, exist_ok=True)
        rendered = ras._upsert_review_protocol_region(
            "# Fixture role doc\n\nRole prose.\n", ras._carrier_protocol_block(carrier)
        )
        path.write_text(
            rendered.replace(ras.REVIEW_PROTOCOL_MARKER_BEGIN, "", 1), encoding="utf-8"
        )
        args = argparse.Namespace(
            scan_all=False,
            write_migration_audit=False,
            migration_audit_path="docs/reports/wave-migration-audit.md",
            changed=False,
        )
        full_failures, _warnings, _infos = cli._run_full_checks(root, args)
        self.assertTrue(
            any(
                "reconcile_review_protocol_surfaces" in item for item in full_failures
            ),
            full_failures,
        )
        with mock.patch.object(cli, "_get_changed_files", return_value=[path]):
            incremental = cli._run_incremental_checks(root)
        self.assertIsNotNone(incremental)
        inc_failures, _inc_warnings = incremental
        self.assertTrue(
            any("reconcile_review_protocol_surfaces" in item for item in inc_failures),
            inc_failures,
        )

    def test_protocol_family_live_corpus_passes(self) -> None:
        """1v4mt AC-3: the new gate must not fire on this repository's 21
        rendered role docs. Guarded against vacuity the same way the
        review-policy corpus test is: assert a probe carrier really carries a
        region, or an empty carrier set would pass trivially."""
        import render_agent_surfaces as ras
        from wave_lint_lib.core_validators import (
            check_review_protocol_carrier_parity,
        )

        repo_root = SCRIPTS_ROOT.parents[1].parent
        if not (repo_root / "docs" / "agents").is_dir():
            self.skipTest("self-hosted docs corpus absent (target repo)")
        carriers = [
            carrier
            for carrier in ras.review_protocol_carriers(repo_root)
            if (repo_root / carrier.destination).is_file()
        ]
        self.assertGreaterEqual(len(carriers), 10, "corpus scan would be thin")
        probe = repo_root / "docs" / "agents" / "code-reviewer.md"
        self.assertIn(
            ras.REVIEW_PROTOCOL_MARKER_BEGIN,
            probe.read_text(encoding="utf-8"),
            "corpus probe carrier lost its rendered region; the scan below "
            "would be vacuous",
        )
        self.assertEqual(check_review_protocol_carrier_parity(repo_root), [])

    def test_protocol_family_regionless_carrier_is_skipped(self) -> None:
        """1v4mt AC-3, negative direction: an unadopted carrier must not fail,
        or the new gate blocks every repository that has not rendered one."""
        import render_agent_surfaces as ras
        from wave_lint_lib.core_validators import (
            check_review_protocol_carrier_parity,
        )

        root = Path(tempfile.mkdtemp(prefix="protocol-parity-none-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        carrier = next(iter(ras.review_protocol_carriers(root)))
        path = root / carrier.destination
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Fixture role doc\n\nNo markers at all.\n", encoding="utf-8")
        self.assertEqual(check_review_protocol_carrier_parity(root), [])

    def test_malformed_markers_fail_instead_of_warn_and_skip(self) -> None:
        """The reconciler warns-and-skips on malformed markers; a gate must
        not."""
        review_policy, _, check = self._modules()
        root, _carrier, _block, path = self._root_with_rendered_region()
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text + "\n" + review_policy.REVIEW_POLICY_SURFACE_MARKER_BEGIN + "\n",
            encoding="utf-8",
        )
        failures = check(root)
        self.assertEqual(len(failures), 1, failures)
        self.assertIn("malformed", failures[0])

    def test_missing_file_is_skipped(self) -> None:
        _, _, check = self._modules()
        root = Path(tempfile.mkdtemp(prefix="parity-empty-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        self.assertEqual(check(root), [])

    def test_live_corpus_passes_rooted_at_this_repo(self) -> None:
        """AC-3: rooted at the repository root constant that resolves to THIS
        repo, not the scripts-tree parent (the 1uwpf PROJECT_ROOT vacuity;
        module-scope PROJECT_ROOT above resolves OUTSIDE the repo)."""
        review_policy, _, check = self._modules()
        repo_root = SCRIPTS_ROOT.parents[1].parent
        if not (repo_root / "docs" / "prompts").is_dir():
            self.skipTest("self-hosted docs corpus absent (target repo)")
        self.assertTrue(
            (repo_root / ".wavefoundry").is_dir(),
            f"corpus root must be the self-hosted repo, got {repo_root}",
        )
        probe = repo_root / "docs" / "prompts" / "council-review.prompt.md"
        self.assertIn(
            review_policy.REVIEW_POLICY_SURFACE_MARKER_BEGIN,
            probe.read_text(encoding="utf-8"),
            "corpus probe carrier lost its rendered region; the scan below "
            "would be vacuous",
        )
        self.assertEqual(check(repo_root), [])

    def test_registered_on_full_and_incremental_paths(self) -> None:
        """AC-3 registration half: a drifted fixture fails cli._run_full_checks
        end to end, and the incremental path catches the same drift when the
        carrier file is in the changed set (rendered-side coverage per
        Requirement 3; a review_policy.py edit never fires the docs hook)."""
        import argparse
        import unittest.mock as mock

        import wave_lint_lib.cli as cli

        review_policy, ras, _check = self._modules()
        carrier = self._carrier()
        block = review_policy.REVIEW_POLICY_SURFACE_BLOCKS[carrier.destination]
        root = Path(tempfile.mkdtemp(prefix="parity-registration-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        shutil.copytree(FIXTURE_ROOT, root, dirs_exist_ok=True)
        path = root / carrier.destination
        rendered = ras._upsert_review_policy_region(
            path.read_text(encoding="utf-8"), block
        )
        self.assertIsNotNone(rendered)
        path.write_text(
            rendered.replace(block, block + "\nhand-edited drift", 1),
            encoding="utf-8",
        )
        args = argparse.Namespace(
            scan_all=False,
            write_migration_audit=False,
            migration_audit_path="docs/reports/wave-migration-audit.md",
            changed=False,
        )
        full_failures, _warnings, _infos = cli._run_full_checks(root, args)
        self.assertTrue(
            any("reconcile_review_policy_surfaces" in item for item in full_failures),
            full_failures,
        )
        with mock.patch.object(cli, "_get_changed_files", return_value=[path]):
            incremental = cli._run_incremental_checks(root)
        self.assertIsNotNone(incremental)
        inc_failures, _inc_warnings = incremental
        self.assertTrue(
            any("reconcile_review_policy_surfaces" in item for item in inc_failures),
            inc_failures,
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

    def test_incremental_changed_wave_record_routes_an_advisory_finding_to_warnings(self) -> None:
        """Wave 1wuju (1wujs Requirement 1; delivery review ARCH-DEL-2 / QA-DEL-1): the
        incremental changed-docs site passes the warnings sink, so on the post-edit hook
        path an advisory sensor's finding is a WARNING and never a failure. The AC
        sensors run from the wave-record branch, so the changed path is `wave.md`."""
        import unittest.mock as mock
        root = self.copy_fixture()
        cli = self._cli()
        try:
            self._replace_acs(
                root,
                "- [x] AC-1: Fixture criterion satisfied and the full framework test suite passes.\n",
                "| AC-1 | required |\n",
            )
            changed = [(root / self.AC_REPO_STATE_DOC).parent / "wave.md"]
            with mock.patch.object(cli, "_get_changed_files", return_value=changed):
                failures, warnings = cli._run_incremental_checks(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual([], [f for f in failures if "asserts repository-wide state" in f], failures)
        self.assertTrue(any("AC-1 asserts repository-wide state" in w for w in warnings), warnings)

    def test_incremental_changed_ledger_revalidates_the_owning_wave_through_the_sink(self) -> None:
        """Same wave and findings, the changed-event-wave site: an `events.jsonl`-only
        change revalidates the owning wave's documents through the same sink."""
        import unittest.mock as mock
        root = self.copy_fixture()
        cli = self._cli()
        try:
            self._replace_acs(
                root,
                "- [x] AC-1: Fixture criterion satisfied and the full framework test suite passes.\n",
                "| AC-1 | required |\n",
            )
            source_dir = (root / self.AC_REPO_STATE_DOC).parent
            wave_dir = root / "docs" / "waves" / "00abd advisory-event-fixture"
            shutil.copytree(source_dir, wave_dir)
            wave_md = wave_dir / "wave.md"
            wave_md.write_text(
                wave_md.read_text(encoding="utf-8").replace(
                    "00057 routine-behavior-contract", "00abd advisory-event-fixture"
                ),
                encoding="utf-8",
            )
            changed = [wave_dir / "events.jsonl"]
            with mock.patch.object(cli, "_get_changed_files", return_value=changed):
                failures, warnings = cli._run_incremental_checks(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual([], [f for f in failures if "asserts repository-wide state" in f], failures)
        self.assertTrue(any("AC-1 asserts repository-wide state" in w for w in warnings), warnings)

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
             "memory `Status` is invalid (got 'maybe')"),
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

    def test_archived_body_passes_but_legacy_pointer_fails_with_migration_guidance(self):
        root = self.copy_fixture()
        memory_root = root / "docs" / "agents" / "memory"
        archive = memory_root / "archive" / "mem-old.md"
        pointer = memory_root / "pointers" / "mem-old.md"
        archive.parent.mkdir(parents=True, exist_ok=True)
        pointer.parent.mkdir(parents=True, exist_ok=True)
        metadata = (
            "Archived: 2026-07-13\n"
            "Archive reason: Replaced tactical guidance.\n"
            "Archive path: `docs/agents/memory/archive/mem-old.md`\n"
        )
        archive.write_text(
            self._record(
                "mem-old",
                "failed_attempt",
                status="archived",
                extra=metadata,
            ),
            encoding="utf-8",
        )
        pointer.write_text(
            self._record(
                "mem-old",
                "failed_attempt",
                status="archived",
                extra=metadata + "Pointer to: `mem-old`\n",
            )
            + "\n## Keywords\n\n- `mem-old`\n- `src/module.py`\n",
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("legacy memory pointer residue is retired", result.stderr)
        self.assertIn("docs/agents/memory-archive.md", result.stderr)

    def test_non_markdown_legacy_pointer_residue_also_fails(self):
        root = self.copy_fixture()
        legacy_root = root / "docs" / "agents" / "memory" / "pointers"
        legacy_root.mkdir(parents=True, exist_ok=True)
        (legacy_root / "operator-notes.txt").write_text(
            "must not be ignored\n", encoding="utf-8"
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("legacy memory pointer residue is retired", result.stderr)

    def test_archived_status_outside_reserved_paths_fails(self):
        root = self.copy_fixture()
        self._write_record(
            root,
            "mem-old",
            self._record(
                "mem-old",
                "failed_attempt",
                status="archived",
                extra=(
                    "Archived: 2026-07-13\nArchive reason: Retired.\n"
                    "Archive path: `docs/agents/memory/archive/mem-old.md`\n"
                ),
            ),
        )
        result = self.run_docs_lint(root)
        shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("archived records must live under", result.stderr)

    def test_pending_archive_body_names_the_reconcile_recovery(self):
        root = self.copy_fixture()
        archive = (
            root / "docs" / "agents" / "memory" / "archive" / "mem-pending.md"
        )
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_text(
            self._record(
                "mem-pending",
                "failed_attempt",
                status="rejected",
            ),
            encoding="utf-8",
        )
        try:
            result = self.run_docs_lint(root)
        finally:
            shutil.rmtree(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("pending memory archive detected", result.stderr)
        self.assertIn(
            "memory_reconcile(memory_id='mem-pending', status='archived', "
            "archive_reason='<reason>')",
            result.stderr,
        )

    def test_evidence_derived_validation_contract(self):
        valid_cases = (
            ("mem-pending", "candidate", "Source event: `finding:x`\nValidation: pending\n"),
            (
                "mem-promote", "active",
                "Source event: `finding:y`\nValidation: promote\n"
                "Validated by: agent\nAction delta: Run the regression.\n"
                "Validation rationale: Evidence and target agree.\n"
                "Evidence verified: true\nCurrent target verified: true\n"
                "Canonical overlap: supplements\n",
            ),
            (
                "mem-promoted-superseded", "superseded",
                "Superseded by: `mem-replacement`\n"
                "Source event: `finding:z`\nValidation: promote\n"
                "Validated by: agent\nAction delta: Run the regression.\n"
                "Validation rationale: Evidence and target agree.\n"
                "Evidence verified: true\nCurrent target verified: true\n"
                "Canonical overlap: supplements\n",
            ),
        )
        for memory_id, status, extra in valid_cases:
            root = self.copy_fixture()
            self._write_record(
                root, memory_id,
                self._record(memory_id, "decision", status=status, extra=extra),
            )
            result = self.run_docs_lint(root)
            shutil.rmtree(root)
            self.assertEqual(result.returncode, 0, result.stderr)

        invalid_cases = (
            (
                "source without validation",
                self._record(
                    "mem-a", "decision",
                    extra="Source event: `finding:x`\n",
                ),
                "require `Validation:",
            ),
            (
                "promote status mismatch",
                self._record(
                    "mem-a", "decision", status="candidate",
                    extra=(
                        "Source event: `finding:x`\nValidation: promote\n"
                        "Validated by: agent\nAction delta: Act.\n"
                        "Validation rationale: Grounded.\nEvidence verified: true\n"
                        "Current target verified: true\nCanonical overlap: none\n"
                    ),
                ),
                "requires `Status: active`",
            ),
            (
                "final judgment missing fields",
                self._record(
                    "mem-a", "decision", status="rejected",
                    extra="Source event: `finding:x`\nValidation: reject\n",
                ),
                "finalized validation requires",
            ),
        )
        for label, content, expected in invalid_cases:
            root = self.copy_fixture()
            self._write_record(root, "mem-a", content)
            result = self.run_docs_lint(root)
            shutil.rmtree(root)
            self.assertEqual(result.returncode, 1, label)
            self.assertIn(expected, result.stderr, label)


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


class DesignTokenSeedGrammarTests(unittest.TestCase):
    """Wave 1viyu: seed-040 normalization guidance must match the enforced dot-path grammar."""

    SEED_040 = SCRIPTS_ROOT.parent / "seeds" / "040-docs-structure-bootstrap.prompt.md"

    def test_seed_normalization_examples_match_the_validator(self):
        from wave_lint_lib.design_system_validators import _DOT_PATH_RE

        valid = ("font.size", "kpi.card", "in.review", "color.primary.500", "spacing.4")
        invalid = ("fontSize", "kpi-card", "in-review", "size.2xl", "size.4xl")

        for token in valid:
            with self.subTest(token=token, expected="valid"):
                self.assertIsNotNone(_DOT_PATH_RE.fullmatch(token))
        for token in invalid:
            with self.subTest(token=token, expected="invalid"):
                self.assertIsNone(_DOT_PATH_RE.fullmatch(token))

    def test_seed_states_the_enforced_normalizations_and_digit_leading_negative(self):
        text = self.SEED_040.read_text(encoding="utf-8")
        for source, normalized in (
            ("fontSize", "font.size"),
            ("kpi-card", "kpi.card"),
            ("in-review", "in.review"),
        ):
            with self.subTest(source=source):
                self.assertIn(source, text)
                self.assertIn(normalized, text)
        self.assertIn("spacing.4", text)
        self.assertIn("size.2xl", text)
        self.assertIn("size.4xl", text)
        self.assertIn("normalizedFrom", text)
        self.assertIn("design_system_validators._DOT_PATH_RE", text)


class EvaluatorEditBaselinePolicyPinTests(unittest.TestCase):
    """Wave 1wybs (1wybq AC-1 to AC-3): an evaluator-only edit records no close-time
    baseline; the contributing, architecture, and CHANGELOG surfaces state one policy."""

    DOCS_DIR = SCRIPTS_ROOT.parent.parent.parent / "docs"

    def test_the_contributing_document_states_the_rule(self) -> None:
        text = (self.DOCS_DIR / "contributing" / "review-and-evals.md").read_text(encoding="utf-8")
        self.assertIn("**An evaluator-only edit records no close-time baseline.**", text)
        self.assertIn("In this repository that pair is a `cross_generation` comparison", text)
        self.assertIn("is the expected signal, not a defect", text)
        # Delivery review (ARCH-DEL-1's receipt): the drift attribution is disclosed.
        self.assertIn("**A `cross_generation` comparison attributes corpus drift to the change.**", text)
        # Delivery review ARCH-RV1-2: the pointer names the receipt binding the current identities.
        self.assertIn("The current\nreference receipt is `docs/reports/retrieval-quality-post-1wybs.json`", text)
        self.assertNotIn("reference receipt is `docs/reports/retrieval-quality-post-1wuju.json`", text)
        self.assertIn("when the diff\nreaches no retrieval tool, the receipt records drift, not a regression", text)
        self.assertNotIn("record a fresh baseline before the gate judges anything", text)
        self.assertNotIn("records its own single-run baseline the same way", text)

    def test_the_architecture_document_agrees(self) -> None:
        text = (self.DOCS_DIR / "architecture" / "testing-architecture.md").read_text(encoding="utf-8")
        self.assertIn("An evaluator-only edit records no close-time baseline (wave `1wybq`)", text)
        self.assertIn("the reference only until the next evaluator edit", text)
        self.assertIn("standing baseline `docs/reports/retrieval-quality-post-1wybs.json`", text)
        self.assertIn("--baseline docs/reports/retrieval-quality-post-1wybs.json", text)
        self.assertIn("attributes corpus drift to the change under the\nzero-tolerance regression rule", text)

    def test_the_1_22_0_changelog_states_one_policy(self) -> None:
        changelog = (self.DOCS_DIR.parent / "CHANGELOG.md").read_text(encoding="utf-8")
        release = changelog.split("## [1.22.0]", 1)[1].split("\n## [", 1)[0]
        self.assertIn("**An evaluator-only edit records no close-time baseline.**", release)
        self.assertIn("A cross-generation comparison attributes corpus drift", release)
        self.assertNotIn("record a fresh baseline", release)


class SerializationPointsTokenGrammarPinTests(unittest.TestCase):
    """Wave 1wybs (1wxe6 AC-1, AC-2): every scaffold surface states the token grammar
    of both declaration forms, anchored beside an existing phrase of the same guidance,
    and the templates' fenced examples are untouched."""

    FRAMEWORK_DIR = SCRIPTS_ROOT.parent
    DOCS_DIR = SCRIPTS_ROOT.parent.parent.parent / "docs"
    FRAGMENTS = (
        "is never a token in either form",
        "a `*` disqualifies the token",
        # Delivery review CODE-DEL-1: the explicit-block clause states the parser's predicate.
        "kept only when its last segment carries an extension or the span ends in `/`",
        "a `*` span is accepted as a phantom",
        # Delivery review CODE-RV1-1: a phantom recruits through the trigger table, not nothing.
        "recruits a lane only through a trigger token it happens to carry",
        "declare the directory that holds globbed files",
    )
    FRAMEWORK_CARRIERS = (
        ("seeds/170-plan-feature.prompt.md", "Prose declares NOTHING in either form"),
        ("seeds/040-docs-structure-bootstrap.prompt.md", "one stray English word makes the whole bullet prose, in either form"),
        ("seeds/160-upgrade-wavefoundry.prompt.md", "State both declaration forms, because prose declares nothing"),
        ("seeds/160-upgrade-wavefoundry.prompt.md", "names both declaration forms"),
        ("install/plan-template.md", "Prepare selects automatic review lanes from declared paths, not from narrative prose."),
        ("install/lifecycle-prompts/prepare-wave.prompt.md", "and a wrapped bullet is prose entirely."),
    )

    def test_every_carrier_states_the_token_grammar(self) -> None:
        carriers = [
            (rel, anchor, (self.FRAMEWORK_DIR / rel).read_text(encoding="utf-8"))
            for rel, anchor in self.FRAMEWORK_CARRIERS
        ]
        carriers.append((
            "docs/plans/plan-template.md",
            "Prepare uses declared paths",
            (self.DOCS_DIR / "plans" / "plan-template.md").read_text(encoding="utf-8"),
        ))
        for rel, anchor, text in carriers:
            with self.subTest(carrier=rel):
                self.assertIn(anchor, text)
                for fragment in self.FRAGMENTS:
                    self.assertIn(fragment, text)

    def test_seed_160_states_it_at_all_three_sites(self) -> None:
        # The repair instruction, the plan-template checklist item, and (delivery
        # review ARCH-DEL-3) the Prepare-prompt checklist item.
        seed = (self.FRAMEWORK_DIR / "seeds" / "160-upgrade-wavefoundry.prompt.md").read_text(encoding="utf-8")
        self.assertEqual(3, seed.count("is never a token in either form"))
        # Delivery review DOCS-RV1-1: the predicate clause is counted at every site too.
        self.assertEqual(3, seed.count("kept only when its last segment carries an extension or the span ends in `/`"))
        self.assertEqual(3, seed.count("recruits a lane only through a trigger token it happens to carry"))

    def test_the_1_22_0_changelog_announces_the_wave(self) -> None:
        # Delivery review DOCS-DEL-4: both 1wybs CHANGELOG bullets are pinned.
        changelog = (self.DOCS_DIR.parent / "CHANGELOG.md").read_text(encoding="utf-8")
        release = changelog.split("## [1.22.0]", 1)[1].split("\n## [", 1)[0]
        self.assertIn("**Serialization Points scaffolds state the token grammar of both declaration forms.**", release)
        self.assertIn("kept only when\n  its last segment carries an extension or the span ends in `/`", release)
        self.assertIn("**Verdict-gap and install-audit hardening**", release)
        self.assertIn("repr-doubled", release)

    def test_the_fenced_examples_are_untouched(self) -> None:
        shipped = (self.FRAMEWORK_DIR / "install" / "plan-template.md").read_text(encoding="utf-8")
        self.assertIn("```\n- `src/app/handler.py`, `docs/specs/`\n```", shipped)
        self.assertIn("```\n**Review targets (repo-relative paths):**\n\n- `docs/waves/1abc some slug/wave.md`\n```", shipped)
        project = (self.DOCS_DIR / "plans" / "plan-template.md").read_text(encoding="utf-8")
        self.assertIn("```\n**Review targets (repo-relative paths):**\n\n- `docs/waves/1abc some slug/wave.md`\n```", project)


class FreshPlanTemplateTests(unittest.TestCase):
    def test_shipped_template_has_required_headings_and_declares_nothing(self):
        import render_agent_surfaces as ras
        from review_policy import serialization_point_paths

        path = SCRIPTS_ROOT.parent / "install" / "plan-template.md"
        text = path.read_text(encoding="utf-8")
        for heading in ras.PLAN_TEMPLATE_REQUIRED_HEADINGS:
            self.assertIn(f"## {heading}", text)
        self.assertEqual(serialization_point_paths(text), ())

        unfenced = text.replace(
            "```\n- `src/app/handler.py`, `docs/specs/`\n```",
            "- `src/app/handler.py`, `docs/specs/`",
            1,
        )
        self.assertTrue(serialization_point_paths(unfenced))
        missing_heading = text.replace("## Agent Execution Graph", "", 1)
        with self.assertRaises(AssertionError):
            self.assertIn("## Agent Execution Graph", missing_heading)

    def test_materialized_template_passes_full_docs_lint(self):
        import render_agent_surfaces as ras

        root = Path(tempfile.mkdtemp(prefix="wave-plan-template-fixture-"))
        try:
            shutil.copytree(FIXTURE_ROOT, root, dirs_exist_ok=True)
            target = root / "docs/plans/plan-template.md"
            target.unlink(missing_ok=True)
            self.assertEqual(
                ras.reconcile_scaffold_baselines(root),
                ["docs/plans/plan-template.md"],
            )
            env = os.environ.copy()
            env["PROJECT_ROOT"] = str(root)
            env["PYTHONPATH"] = str(SCRIPTS_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
            result = subprocess.run(
                [os.environ.get("PYTHON", "python3"), str(DOCS_LINT_SCRIPT)],
                cwd=PROJECT_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        finally:
            shutil.rmtree(root)


class ScaffoldDeclaresNothingTests(unittest.TestCase):
    """A scaffold that declares review targets silently removes coverage.

    Field report from a 1.15.5 upgrade: a target repository's
    `docs/plans/plan-template.md` carried an UNFENCED example under the
    `**Review targets (repo-relative paths):**` marker, so the scaffold itself
    declared `path/to/file.swift` and `docs/specs/`. Every plan created from it
    was born in declared mode, losing `qa-reviewer` and `architecture-reviewer`
    and gaining `docs-contract-reviewer` from a path nobody chose.

    This repository is not affected, and that is the point: we are clean only
    because wave `1uo1x` pinned it with a test in OUR suite. A target
    repository does not run our suite; it gets prose instruction in seed 160,
    which the downstream repository followed and still shipped a declaring
    template. These tests make the property mechanical.
    """

    DOWNSTREAM_SHAPE = (
        "## Serialization Points\n\n"
        "**Review targets (repo-relative paths):**\n\n"
        "- `path/to/file.swift`\n"
        "- `docs/specs/`\n\n"
        "## Affected Architecture Docs\n"
    )

    def test_the_reported_downstream_shape_declares_targets(self):
        """The red premise: this shape really does declare, on shipped code.

        Pinned separately from the rule so a later parser change that stops
        extracting cannot make the rule vacuously green.
        """

        from review_policy import serialization_point_paths

        self.assertEqual(
            serialization_point_paths(self.DOWNSTREAM_SHAPE),
            ("path/to/file.swift", "docs/specs/"),
        )

    def test_a_declaring_scaffold_fails_on_the_blocking_channel(self):
        from wave_lint_lib.core_validators import check_scaffold_declares_nothing

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "plans").mkdir(parents=True)
            (root / "docs" / "plans" / "plan-template.md").write_text(
                "# [Change Title]\n\n" + self.DOWNSTREAM_SHAPE, encoding="utf-8"
            )
            failures = check_scaffold_declares_nothing(root)
        self.assertTrue(failures, "a declaring scaffold must fail")
        joined = " ".join(failures)
        self.assertIn("plan-template.md", joined)
        self.assertIn("path/to/file.swift", joined, "name the found target")
        self.assertIn("fence", joined.lower(), "state the remedy")

    def test_the_shipped_scaffolds_pass(self):
        """Confirms the wave-1uo1x fix rather than contradicting it.

        Without this, a rule that failed everything would satisfy the red test.
        """

        from wave_lint_lib.core_validators import check_scaffold_declares_nothing

        root = Path(__file__).resolve().parents[4]
        self.assertEqual(check_scaffold_declares_nothing(root), [])

    def test_an_authored_change_doc_never_blocks(self):
        """Blocking set equals repairable set.

        The upgrade repairs scaffolds only, so nothing else may block: a
        change doc the upgrade cannot rewrite must never halt the docs gate.
        Uses this wave's own change doc, which declares ten real targets.
        """

        from wave_lint_lib.core_validators import check_scaffold_declares_nothing

        root = Path(__file__).resolve().parents[4]
        declaring = sorted(
            (root / "docs" / "waves").glob("1ur6o */1ur6p-bug *.md")
        )
        self.assertTrue(declaring, "fixture must find this wave's change doc")
        failures = check_scaffold_declares_nothing(root)
        for path in declaring:
            self.assertNotIn(
                path.name, " ".join(failures),
                "an authored change doc must never block",
            )

    def test_the_rule_delegates_to_the_shipped_parser(self):
        """A second extractor would drift and pass what the evaluator declares.

        Patches the name the RULE resolves. Patching `review_policy` instead
        would be observationally identical to a re-implementation, since
        neither changes the output.
        """

        from wave_lint_lib import core_validators

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "plans").mkdir(parents=True)
            (root / "docs" / "plans" / "plan-template.md").write_text(
                "# T\n\n## Serialization Points\n\n- nothing here\n", encoding="utf-8"
            )
            self.assertEqual(
                core_validators.check_scaffold_declares_nothing(root), []
            )
            with patch.object(
                core_validators,
                "serialization_point_paths",
                return_value=("sentinel/injected.py",),
            ):
                failures = core_validators.check_scaffold_declares_nothing(root)
        self.assertTrue(
            failures and "sentinel/injected.py" in " ".join(failures),
            "the rule must follow the patched parser, not its own extractor",
        )

    def test_the_rule_is_registered_on_both_lint_paths(self):
        """AC-6c: a corpus-only registration is invisible to the post-edit hook.

        `_run_incremental_checks` runs an explicit per-file subset with
        `only=changed_docs` and deliberately excludes corpus checks, so a rule
        registered only in the corpus block never fires at the moment an author
        pastes a declaring block into the template — which is where the defect
        is cheapest to fix. Both registrations are pinned, and the `only=`
        filter is pinned with them: an unrelated changed doc must NOT drag the
        template into an incremental run.
        """

        import unittest.mock as mock

        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib import cli as lint_cli

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "plans").mkdir(parents=True)
            template = root / "docs" / "plans" / "plan-template.md"
            template.write_text(
                "# [Change Title]\n\n" + self.DOWNSTREAM_SHAPE, encoding="utf-8"
            )
            unrelated = root / "docs" / "plans" / "other.md"
            unrelated.write_text("# Other\n", encoding="utf-8")

            # Incremental, template changed -> fires.
            with mock.patch.object(
                lint_cli, "_get_changed_files", return_value=[template]
            ):
                hit, _ = lint_cli._run_incremental_checks(root)
            self.assertTrue(
                any("scaffold declares review targets" in f for f in hit),
                f"incremental must fire when the template changes; got {hit}",
            )

            # Incremental, template NOT changed -> silent (the only= filter).
            with mock.patch.object(
                lint_cli, "_get_changed_files", return_value=[unrelated]
            ):
                miss, _ = lint_cli._run_incremental_checks(root)
            self.assertFalse(
                any("scaffold declares review targets" in f for f in miss),
                f"an unrelated changed doc must not drag in the template; got {miss}",
            )

    def test_a_declaring_scaffold_blocks_the_real_cli(self):
        """The severity decision, pinned end to end rather than by inspection.

        `cli.py` has a real two-channel split: `failures` block and exit
        non-zero, `warnings` print and exit 0. A warning-channel implementation
        would satisfy a loose reading of "fails docs-lint" while leaving the
        property unenforced, and an unrepaired declaring template must halt the
        upgrade's docs gate rather than pass it.
        """

        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib.core_validators import check_scaffold_declares_nothing

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "plans").mkdir(parents=True)
            (root / "docs" / "plans" / "plan-template.md").write_text(
                "# [Change Title]\n\n" + self.DOWNSTREAM_SHAPE, encoding="utf-8"
            )
            failures = check_scaffold_declares_nothing(root)
        self.assertTrue(failures)
        # Drive the real emitter. An earlier version of this test asserted the
        # string started with "ERROR:", which a delivery lane proved cannot
        # distinguish the channels: feeding the identical list to the warnings
        # channel also exits 0. The channel is the contract, not the prefix.
        import argparse

        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib import cli as lint_cli

        self.assertEqual(
            lint_cli._emit(failures, [], [], root, argparse.Namespace(changed=False, write_migration_audit=False, migration_audit_path="docs/reports/wave-migration-audit.md", scan_all=False), False), 1,
            "a declaring scaffold must exit non-zero on the failures channel",
        )
        self.assertEqual(
            lint_cli._emit([], failures, [], root, argparse.Namespace(changed=False, write_migration_audit=False, migration_audit_path="docs/reports/wave-migration-audit.md", scan_all=False), False), 0,
            "control: the same strings on the warnings channel do NOT block, "
            "which is why a prefix assertion proves nothing",
        )
        self.assertFalse(
            any(f.startswith("ERROR:") for f in failures),
            "the validator must not self-prefix; cli._emit adds ERROR:",
        )

    def test_the_corpus_path_reports_a_declaring_scaffold(self):
        """The full lint is the authoritative gate the upgrade actually runs.

        `phase_docs_gate` subprocesses `docs_lint.py` with no `--changed`, so
        the corpus registration is what decides whether a contaminated
        repository halts. Pinned by driving `_run_full_checks`, the same entry
        the CLI uses, rather than the validator in isolation.
        """

        import argparse

        sys.path.insert(0, str(SCRIPTS_ROOT))
        from wave_lint_lib import cli as lint_cli

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "plans").mkdir(parents=True)
            (root / "docs" / "plans" / "plan-template.md").write_text(
                "# [Change Title]\n\n" + self.DOWNSTREAM_SHAPE, encoding="utf-8"
            )
            args = argparse.Namespace(
                scan_all=False,
                write_migration_audit=False,
                migration_audit_path="docs/reports/wave-migration-audit.md",
                changed=False,
            )
            failures, _warnings, _info = lint_cli._run_full_checks(root, args)
        self.assertTrue(
            any("scaffold declares review targets" in f for f in failures),
            f"the corpus path must report a declaring scaffold; got {failures}",
        )


class RecordLayoutLintTests(unittest.TestCase):
    """Wave 1y0gz / 1y042: docs-lint validates the record layout CONSTANTS.

    The layout is the ``record_paths`` module constants (``WAVES_ROOT``,
    ``PLANS_ROOT``, ``NESTED``, ``MAX_DEPTH``); nothing is read from
    configuration. The default layout is covered by the unchanged base corpus
    above (``test_base_fixture_passes``); these cases patch the constants
    through ``tests/record_layout_support.py`` (``apply_layout`` for direct
    validator calls, ``run_script_with_layout`` for subprocess runs), relocate
    the roots, exercise every invalid class fail-closed, and pin that a
    relocated corpus is linted and gardened exactly like the shipped one.
    Reuses the fixture helpers by reference (not subclassing) so the base
    corpus is not re-run under this class.
    """

    copy_fixture = DocsLintFixtureTests.copy_fixture
    run_docs_lint = DocsLintFixtureTests.run_docs_lint
    run_docs_lint_with_args = DocsLintFixtureTests.run_docs_lint_with_args

    RELOCATED_WAVES = "project/records/waves"
    RELOCATED_PLANS = "project/records/plans"
    RELOCATED_LAYOUT = {"waves_root": RELOCATED_WAVES, "plans_root": RELOCATED_PLANS}
    FIXTURE_WAVE_DIR = "change-2026-03"

    # -- helpers -----------------------------------------------------------

    def _run_lint_with_layout(
        self, root: Path, layout: dict[str, object], *args: str
    ) -> subprocess.CompletedProcess[str]:
        """The docs-lint CLI as a child process whose constants are ``layout``."""
        from record_layout_support import run_script_with_layout

        env = os.environ.copy()
        env["PROJECT_ROOT"] = str(root)
        env["PYTHONPATH"] = str(SCRIPTS_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        return run_script_with_layout(DOCS_LINT_SCRIPT, list(args), layout=layout, cwd=PROJECT_ROOT, env=env)

    def _apply(self, **layout: object) -> None:
        from record_layout_support import apply_layout

        apply_layout(self, **layout)

    def _relocate_waves(self, root: Path, waves_rel: str) -> Path:
        """Move the fixture waves root to ``waves_rel`` and regenerate the manifest
        through the real producer (``docs_gardener.default_manifest_payload``,
        which ``wf_garden_docs`` reconciles before lint) so the fixture matches a
        gardened relocated repository rather than a hand-edited one. The
        constants must already be patched to the relocated layout."""
        import docs_gardener

        target = root.joinpath(*waves_rel.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(root / "docs" / "waves"), str(target))
        manifest = root / "docs" / "prompts" / "prompt-surface-manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["generated_artifacts"] = docs_gardener.default_manifest_payload("2026-03-21", root)[
            "generated_artifacts"
        ]
        manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return target

    def _relocated_fixture(self) -> Path:
        root = self.copy_fixture()
        self._apply(**self.RELOCATED_LAYOUT)
        self._relocate_waves(root, self.RELOCATED_WAVES)
        return root

    @staticmethod
    def _error_lines(result: subprocess.CompletedProcess[str]) -> list[str]:
        return [line for line in result.stderr.splitlines() if line.startswith("ERROR: ")]

    @staticmethod
    def _break_wave_md(wave_md: Path) -> None:
        """A known-bad wave record: one broken relative link and no ``Last verified:``."""
        text = wave_md.read_text(encoding="utf-8")
        lines = [line for line in text.splitlines() if not line.startswith("Last verified:")]
        lines.append("")
        lines.append("See [the missing target](./definitely-missing-target.md).")
        wave_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # (a) default layout: the resolver hands the validators byte-identical paths.
    def test_default_layout_paths_are_byte_identical(self) -> None:
        from wave_lint_lib.helpers import resolve_record_roots
        from wave_lint_lib.wave_validators import check_wave_roots

        root = self.copy_fixture()
        try:
            roots = resolve_record_roots(root)
            self.assertIsNotNone(roots)
            self.assertEqual(roots.waves, root / "docs" / "waves")
            self.assertEqual(roots.plans, root / "docs" / "plans")
            self.assertEqual(roots.waves_prefix, "docs/waves/")
            self.assertEqual(check_wave_roots(root), [])
            shutil.rmtree(root / "docs" / "waves")
            self.assertIn(
                "docs/waves: missing required Wavefoundry generated artifact",
                check_wave_roots(root),
            )
        finally:
            shutil.rmtree(root)

    # (b) relocated roots: the full lint passes and the validators FIND the wave there.
    def test_relocated_roots_pass_and_wave_validators_find_the_wave(self) -> None:
        from wave_lint_lib.helpers import resolve_record_roots
        from wave_lint_lib.wave_validators import check_wave_docs, check_wave_roots

        root = self._relocated_fixture()
        try:
            result = self._run_lint_with_layout(root, self.RELOCATED_LAYOUT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("docs-lint: ok", result.stdout)

            roots = resolve_record_roots(root)
            self.assertEqual(roots.waves, root / "project" / "records" / "waves")
            self.assertEqual(check_wave_roots(root), [])

            wave_md = root / "project" / "records" / "waves" / self.FIXTURE_WAVE_DIR / "wave.md"
            self.assertTrue(wave_md.is_file())
            wave_md.write_text(
                wave_md.read_text(encoding="utf-8").replace("Change Status: `ready`", "Change Status: `bogus`"),
                encoding="utf-8",
            )
            failures = check_wave_docs(root)
            self.assertTrue(
                any(f.startswith(f"project/records/waves/{self.FIXTURE_WAVE_DIR}/wave.md") for f in failures),
                failures,
            )
            result = self._run_lint_with_layout(root, self.RELOCATED_LAYOUT)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(
                any(
                    f"project/records/waves/{self.FIXTURE_WAVE_DIR}/wave.md" in line
                    for line in self._error_lines(result)
                ),
                result.stderr,
            )

            shutil.rmtree(root / "project" / "records" / "waves")
            self.assertIn(
                "project/records/waves: missing required Wavefoundry generated artifact",
                check_wave_roots(root),
            )
        finally:
            shutil.rmtree(root)

    # (b') the relocated corpus is linted like the shipped one: a known-bad wave
    # record fails with the SAME two per-file errors (metadata + links) it fails
    # with under docs/waves. Pins finding `lint-corpus-docs-only`.
    def test_relocated_known_bad_wave_md_reports_the_same_errors(self) -> None:
        wave_rel = f"{self.FIXTURE_WAVE_DIR}/wave.md"

        default_root = self.copy_fixture()
        try:
            self._break_wave_md(default_root / "docs" / "waves" / self.FIXTURE_WAVE_DIR / "wave.md")
            default_result = self.run_docs_lint(default_root)
        finally:
            shutil.rmtree(default_root)
        self.assertEqual(default_result.returncode, 1, default_result.stdout + default_result.stderr)
        default_errors = sorted(
            line.replace(f"docs/waves/{wave_rel}", "<waves>/wave.md")
            for line in self._error_lines(default_result)
            if f"docs/waves/{wave_rel}" in line
        )
        self.assertEqual(len(default_errors), 2, default_errors)
        self.assertTrue(any("definitely-missing-target.md" in line for line in default_errors), default_errors)
        self.assertTrue(any("Last verified" in line for line in default_errors), default_errors)

        relocated_root = self._relocated_fixture()
        try:
            self._break_wave_md(relocated_root / "project" / "records" / "waves" / self.FIXTURE_WAVE_DIR / "wave.md")
            relocated_result = self._run_lint_with_layout(relocated_root, self.RELOCATED_LAYOUT)
        finally:
            shutil.rmtree(relocated_root)
        self.assertEqual(relocated_result.returncode, 1, relocated_result.stdout + relocated_result.stderr)
        relocated_errors = sorted(
            line.replace(f"project/records/waves/{wave_rel}", "<waves>/wave.md")
            for line in self._error_lines(relocated_result)
            if f"project/records/waves/{wave_rel}" in line
        )
        self.assertEqual(relocated_errors, default_errors)

    # (b'') the incremental (`--changed`) path lints a changed doc under the relocated root.
    def test_changed_detects_bogus_change_status_under_relocated_root(self) -> None:
        import unittest.mock as mock
        import wave_lint_lib.cli as cli

        root = self._relocated_fixture()
        try:
            wave_md = root / "project" / "records" / "waves" / self.FIXTURE_WAVE_DIR / "wave.md"
            wave_md.write_text(
                wave_md.read_text(encoding="utf-8").replace("Change Status: `ready`", "Change Status: `bogus`"),
                encoding="utf-8",
            )
            with mock.patch.object(cli, "_get_changed_files", return_value=[wave_md]):
                failures, _warnings = cli._run_incremental_checks(root)
        finally:
            shutil.rmtree(root)
        self.assertTrue(
            any(
                f.startswith(f"project/records/waves/{self.FIXTURE_WAVE_DIR}/wave.md") and "bogus" in f
                for f in failures
            ),
            failures,
        )

    # (c) every invalid class is a lint FAILURE and nothing scans a guessed root.
    def test_invalid_layout_classes_fail_closed(self) -> None:
        cases: dict[str, dict[str, object]] = {
            "absolute": {"waves_root": "/tmp/waves"},
            "dotdot": {"waves_root": "docs/../waves"},
            "equal": {"waves_root": "docs/records", "plans_root": "docs/records"},
            "nested": {"waves_root": "docs/records", "plans_root": "docs/records/plans"},
            "file_as_root": {"waves_root": "docs/records-file"},
            "max_depth_out_of_range": {"max_depth": 0},
        }
        for name, layout in cases.items():
            with self.subTest(case=name):
                root = self.copy_fixture()
                try:
                    if name == "file_as_root":
                        (root / "docs" / "records-file").write_text("not a directory\n", encoding="utf-8")
                    result = self._run_lint_with_layout(root, layout)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    errors = self._error_lines(result)
                    self.assertTrue(
                        any(line.startswith("ERROR: record_layout_invalid:") for line in errors),
                        result.stderr,
                    )
                    # Fail-closed: no validator probed the default root instead.
                    self.assertFalse(
                        any("docs/waves" in line and "missing required" in line for line in errors),
                        result.stderr,
                    )
                    self.assertEqual(
                        len([line for line in errors if line.startswith("ERROR: record_layout_invalid:")]),
                        len(set(line for line in errors if line.startswith("ERROR: record_layout_invalid:"))),
                        "record_layout_invalid diagnostics must not be duplicated across validators",
                    )
                finally:
                    shutil.rmtree(root)

    @unittest.skipIf(os.name == "nt", "symlink escape is a POSIX case")
    def test_escaping_symlink_root_fails_closed(self) -> None:
        root = self.copy_fixture()
        outside = Path(tempfile.mkdtemp(prefix="wave-docs-lint-outside-"))
        try:
            # The constant's path must EXIST to pass through the symlink: `records` -> outside the
            # repository, and the wave records really live there.
            shutil.move(str(root / "docs" / "waves"), str(outside / "waves"))
            (root / "records").symlink_to(outside, target_is_directory=True)
            self.assertTrue((root / "records" / "waves").is_dir())
            result = self._run_lint_with_layout(root, {"waves_root": "records/waves"})
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertTrue(
                any("record_layout_invalid:" in line and "outside the repository" in line for line in self._error_lines(result)),
                result.stderr,
            )
        finally:
            shutil.rmtree(root)
            shutil.rmtree(outside)

    def test_direct_validator_calls_fail_closed_on_invalid_layout(self) -> None:
        from wave_lint_lib.core_validators import check_required_files
        from wave_lint_lib.docs_constants_validators import check_wave_scaffolding_integrity
        from wave_lint_lib.link_validators import check_markdown_links
        from wave_lint_lib.wave_validators import (
            check_closed_wave_requirements,
            check_orphan_wave_ledgers,
            check_plan_filenames,
            check_prepare_council_roster_evidence,
            check_prepare_council_verdict,
            check_wave_docs,
            check_wave_roots,
        )

        root = self.copy_fixture()
        try:
            self._apply(waves_root="docs/records", plans_root="docs/records")
            shutil.rmtree(root / "docs" / "waves")  # a guessed default root would now report "missing"
            single = [
                check_required_files,
                check_wave_roots,
                check_wave_docs,
                check_closed_wave_requirements,
                check_plan_filenames,
                check_orphan_wave_ledgers,
                check_wave_scaffolding_integrity,
            ]
            for fn in single:
                with self.subTest(validator=fn.__name__):
                    failures = fn(root)
                    self.assertTrue(all(f.startswith("record_layout_invalid:") for f in failures), failures)
                    self.assertTrue(failures, fn.__name__)
            for fn in (check_prepare_council_verdict, check_prepare_council_roster_evidence):
                with self.subTest(validator=fn.__name__):
                    errors, _warnings = fn(root)
                    self.assertTrue(errors and all(e.startswith("record_layout_invalid:") for e in errors), errors)
            link_failures = check_markdown_links(root, root / "docs" / "README.md")
            self.assertTrue(
                link_failures and all(f.startswith("record_layout_invalid:") for f in link_failures),
                link_failures,
            )
        finally:
            shutil.rmtree(root)

    # (d') a sub-wave folder NESTED INSIDE a discovered wave folder (finding
    # `cycle2-adjacent-gaps` 4b): discovery never descends past a `wave.md`, so the
    # per-document walk must not either -- `_collect_wave_state` sees only the outer wave.
    def test_nested_sub_wave_inside_a_wave_folder_is_not_a_lint_record(self) -> None:
        import record_paths
        from wave_lint_lib.helpers import resolve_record_roots
        from wave_lint_lib.wave_validators import _collect_wave_state, _wave_record_docs

        root = self.copy_fixture()
        try:
            waves = root / "docs" / "waves"
            original = (waves / self.FIXTURE_WAVE_DIR / "wave.md").read_text(encoding="utf-8")
            self.assertIn("wave-id: `00057 routine-behavior-contract`", original)
            outer = waves / "1aaaa demo"
            (outer / "evidence").mkdir(parents=True)
            (outer / "wave.md").write_text(
                original.replace("wave-id: `00057 routine-behavior-contract`", "wave-id: `1aaaa demo`"),
                encoding="utf-8",
            )
            (outer / "evidence" / "notes.md").write_text("# Evidence\n\nwave-id: `1aaaa demo`\n", encoding="utf-8")
            inner = outer / "evidence" / "1bbbb sub"
            inner.mkdir()
            (inner / "wave.md").write_text(
                original.replace("wave-id: `00057 routine-behavior-contract`", "wave-id: `1bbbb sub`"),
                encoding="utf-8",
            )
            (inner / "detail.md").write_text("# Detail\n\nwave-id: `1bbbb sub`\n", encoding="utf-8")

            self._apply(nested=True, max_depth=4)
            roots = resolve_record_roots(root)
            discovered = record_paths.discover_wave_dirs(root, roots)
            self.assertEqual(discovered, [outer, waves / self.FIXTURE_WAVE_DIR])

            docs = _wave_record_docs(root, roots)
            self.assertIn(outer / "wave.md", docs)
            self.assertIn(outer / "evidence" / "notes.md", docs)  # evidence sub-docs are still linted
            self.assertFalse([d for d in docs if inner in d.parents or d.parent == inner], docs)

            wave_state, _records = _collect_wave_state(root)
            self.assertEqual(set(wave_state), {"00057 routine-behavior-contract", "1aaaa demo"})
        finally:
            shutil.rmtree(root)

    # (e) the incremental (`--changed`) path fails closed BEFORE scanning: an invalid
    # layout on a git-initialised fixture with a changed wave record reports the
    # `record_layout_invalid:` line and nothing else (finding `cycle2-adjacent-gaps` 4d).
    def test_changed_fails_closed_on_invalid_layout_before_scanning(self) -> None:
        root = self.copy_fixture()
        try:
            git_env = {
                **os.environ,
                "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
            }
            for cmd in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "commit", "-q", "-m", "fixture"]):
                subprocess.run(cmd, cwd=root, env=git_env, check=True, capture_output=True, text=True)
            wave_md = root / "docs" / "waves" / self.FIXTURE_WAVE_DIR / "wave.md"
            wave_md.write_text(
                wave_md.read_text(encoding="utf-8").replace("Change Status: `ready`", "Change Status: `bogus`"),
                encoding="utf-8",
            )
            result = self._run_lint_with_layout(root, {"waves_root": "../x"}, "--changed")
        finally:
            shutil.rmtree(root)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        errors = self._error_lines(result)
        self.assertTrue(errors, result.stdout + result.stderr)
        self.assertTrue(all(line.startswith("ERROR: record_layout_invalid:") for line in errors), errors)
        # Exactly ONE diagnostic: the incremental path returned before any per-file validator ran
        # (each of those would fail closed on its own and re-report the same line).
        self.assertEqual(len(errors), 1, errors)
        self.assertNotIn("bogus", result.stderr)  # the changed record was never scanned
        self.assertNotIn("docs-lint: ok", result.stdout)

    # (d) the validators' own walk is the discovery walk (finding `lint-validators-own-walk`):
    # under NESTED=True, MAX_DEPTH=1 a wave at depth 3 and one under `.archive/` are
    # outside the layout, so lint must see exactly the set `discover_wave_dirs` sees.
    def test_nested_divergence_lint_walk_matches_discovery(self) -> None:
        import record_paths
        from wave_lint_lib.helpers import resolve_record_roots
        from wave_lint_lib.wave_validators import (
            _collect_wave_state,
            _wave_record_docs,
            check_closed_wave_requirements,
            check_prepare_council_verdict,
        )

        root = self.copy_fixture()
        try:
            waves = root / "docs" / "waves"
            source = waves / self.FIXTURE_WAVE_DIR / "wave.md"
            original = source.read_text(encoding="utf-8")
            self.assertIn("wave-id: `00057 routine-behavior-contract`", original)

            def plant(rel_dir: str, wave_id: str, status: str = "active") -> Path:
                target = waves.joinpath(*rel_dir.split("/"))
                target.mkdir(parents=True)
                # A legacy (prose-gated) record: no ledger declaration, so the verdict
                # validator reports it whenever the walk reaches it.
                text = (
                    original.replace("wave-id: `00057 routine-behavior-contract`", f"wave-id: `{wave_id}`")
                    .replace("Status: active", f"Status: {status}", 1)
                    .replace("review-evidence-source: events.jsonl\n", "")
                )
                (target / "wave.md").write_text(text, encoding="utf-8")
                return target

            # Depth 3 (two containers without a wave.md above it) and a dot-prefixed archive;
            # `implementing` without a prepare-council verdict so the council validator
            # would report each one it walks.
            plant("deep/deeper/00061 deep-wave", "00061 deep-wave", status="implementing")
            plant(".archive/00062 archived-wave", "00062 archived-wave", status="implementing")

            self._apply(nested=True, max_depth=1)
            roots = resolve_record_roots(root)
            discovered = record_paths.discover_wave_dirs(root, roots)
            self.assertEqual(discovered, [waves / self.FIXTURE_WAVE_DIR])

            wave_state, _records = _collect_wave_state(root)
            self.assertEqual(set(wave_state), {"00057 routine-behavior-contract"})
            self.assertEqual(
                sorted({p.parent for p in _wave_record_docs(root, roots)}), discovered
            )
            council_errors, _council_warnings = check_prepare_council_verdict(root)
            self.assertFalse(
                any("00061" in e or "00062" in e or ".archive" in e or "deeper" in e for e in council_errors),
                council_errors,
            )
            self.assertFalse(
                any("deeper" in f or ".archive" in f for f in check_closed_wave_requirements(root)),
            )

            # Raising the bound brings the deep wave (not the archive) into lint's view too.
            self._apply(nested=True, max_depth=3)
            roots = resolve_record_roots(root)
            discovered = record_paths.discover_wave_dirs(root, roots)
            self.assertEqual(
                discovered, [waves / self.FIXTURE_WAVE_DIR, waves / "deep" / "deeper" / "00061 deep-wave"]
            )
            wave_state, _records = _collect_wave_state(root)
            self.assertEqual(set(wave_state), {"00057 routine-behavior-contract", "00061 deep-wave"})
            council_errors, _council_warnings = check_prepare_council_verdict(root)
            self.assertTrue(any("00061 deep-wave" in e for e in council_errors), council_errors)
            self.assertFalse(any(".archive" in e for e in council_errors), council_errors)
        finally:
            shutil.rmtree(root)

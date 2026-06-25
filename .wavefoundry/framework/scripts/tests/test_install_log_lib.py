"""Tests for install_log_lib.py (the install-log row parser + state queries).

Wave 1p35d (1p35h).
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import install_log_lib  # noqa: E402


SAMPLE_LOG = """\
# Wavefoundry Install Log

Owner: operator
Status: in-progress

## Phase 1 — Harness (no MCP required)

- [ ] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json
- [x] 1.2 — Bootstrap harness (setup_wavefoundry.py) — artifact: .mcp.json
- [ ] 1.3 — STOP: restart agent (instruction)

## Phase 2 — Project discovery (MCP required)

- [ ] 2.1 — Audit Phase 1 outputs (verify) — expects: wave_install_audit(phase=1) returns next_step
- [~] 2.2 — Capture legacy baseline wave if applicable (seed-110) — artifact: docs/waves/00000 wave-zero-plans-and-specs/wave.md
- [ ] 2.3 — Bootstrap evidence base (seed-030) — artifact: docs/repo-profile.json
"""


class RowParsingTests(unittest.TestCase):
    """Unit tests for ``parse_row``."""

    def test_seed_driven_row_parsed(self):
        row = install_log_lib.parse_row(
            "- [ ] 1.1 — Set lifecycle epoch in workflow-config (seed-020) — artifact: docs/workflow-config.json",
            phase=1,
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.state, " ")
        self.assertEqual(row.number, "1.1")
        self.assertEqual(row.kind, "seed")
        self.assertEqual(row.source, "seed-020")
        self.assertEqual(row.target, "docs/workflow-config.json")
        self.assertEqual(row.phase, 1)
        self.assertTrue(row.is_pending)
        self.assertFalse(row.is_done)
        self.assertTrue(row.needs_artifact_check)

    def test_script_driven_row_parsed(self):
        row = install_log_lib.parse_row(
            "- [x] 1.2 — Bootstrap harness (setup_wavefoundry.py) — artifact: .mcp.json",
            phase=1,
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.kind, "script")
        self.assertEqual(row.source, "setup_wavefoundry.py")
        self.assertEqual(row.target, ".mcp.json")
        self.assertTrue(row.is_done)
        self.assertTrue(row.needs_artifact_check)

    def test_verify_row_parsed_no_artifact_check(self):
        row = install_log_lib.parse_row(
            "- [ ] 2.1 — Audit Phase 1 outputs (verify) — expects: wave_install_audit(phase=1) returns next_step",
            phase=2,
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.kind, "verify")
        self.assertEqual(row.target, "wave_install_audit(phase=1) returns next_step")
        self.assertFalse(row.needs_artifact_check)

    def test_instruction_row_parsed_no_target(self):
        row = install_log_lib.parse_row(
            "- [ ] 1.3 — STOP: restart agent (instruction)",
            phase=1,
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.kind, "instruction")
        self.assertIsNone(row.target)
        self.assertFalse(row.needs_artifact_check)

    def test_not_applicable_state_parsed_as_terminal(self):
        row = install_log_lib.parse_row(
            "- [~] 2.2 — Capture legacy baseline wave (seed-110) — artifact: docs/waves/00000/wave.md",
            phase=2,
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.state, "~")
        self.assertTrue(row.is_not_applicable)
        self.assertTrue(row.is_terminal)
        self.assertFalse(row.is_pending)

    def test_non_row_line_returns_none(self):
        for prose in (
            "",
            "# Heading",
            "Some prose paragraph.",
            "- not a checkbox",
            "- [x] but no number or seed",
        ):
            with self.subTest(prose=prose):
                self.assertIsNone(install_log_lib.parse_row(prose, phase=1))

    def test_decimal_sub_extension_number_parsed(self):
        row = install_log_lib.parse_row(
            "- [ ] 1.3.5 — Inserted step (seed-025) — artifact: docs/foo.json",
            phase=1,
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.number, "1.3.5")


class LogParsingTests(unittest.TestCase):
    """Tests for ``parse_log`` (multi-row + phase detection)."""

    def test_log_parsed_with_phase_assignment(self):
        rows = install_log_lib.parse_log(SAMPLE_LOG)
        self.assertEqual(len(rows), 6)
        # First 3 rows are Phase 1.
        self.assertEqual(rows[0].number, "1.1")
        self.assertEqual(rows[0].phase, 1)
        self.assertEqual(rows[1].number, "1.2")
        self.assertEqual(rows[1].phase, 1)
        self.assertEqual(rows[2].number, "1.3")
        self.assertEqual(rows[2].phase, 1)
        # Last 3 are Phase 2.
        self.assertEqual(rows[3].number, "2.1")
        self.assertEqual(rows[3].phase, 2)
        self.assertEqual(rows[4].number, "2.2")
        self.assertEqual(rows[4].phase, 2)
        self.assertEqual(rows[5].number, "2.3")
        self.assertEqual(rows[5].phase, 2)

    def test_prose_between_rows_passes_through(self):
        log = (
            "## Phase 1 — Harness\n\n"
            "Some explanatory prose here.\n\n"
            "- [ ] 1.1 — Step A (seed-001) — artifact: foo.json\n\n"
            "More prose.\n\n"
            "- [x] 1.2 — Step B (seed-002) — artifact: bar.json\n"
        )
        rows = install_log_lib.parse_log(log)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].number, "1.1")
        self.assertEqual(rows[1].number, "1.2")


class StateQueryTests(unittest.TestCase):
    """Tests for the helper queries (filter, first-unchecked, missing-artifact, complete)."""

    def setUp(self):
        self.rows = install_log_lib.parse_log(SAMPLE_LOG)
        self._tmp = tempfile.mkdtemp()
        self.root = Path(self._tmp)

    def tearDown(self):
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_filter_phase_none_returns_all(self):
        self.assertEqual(len(install_log_lib.filter_phase(self.rows, None)), 6)

    def test_filter_phase_1_returns_three(self):
        phase_1 = install_log_lib.filter_phase(self.rows, 1)
        self.assertEqual(len(phase_1), 3)
        self.assertTrue(all(r.phase == 1 for r in phase_1))

    def test_filter_phase_2_returns_three(self):
        phase_2 = install_log_lib.filter_phase(self.rows, 2)
        self.assertEqual(len(phase_2), 3)
        self.assertTrue(all(r.phase == 2 for r in phase_2))

    def test_first_unchecked_returns_first_pending(self):
        next_row = install_log_lib.first_unchecked_row(self.rows)
        self.assertIsNotNone(next_row)
        self.assertEqual(next_row.number, "1.1")

    def test_first_unchecked_skips_x_and_tilde(self):
        # Rows: [ ] 1.1, [x] 1.2, [ ] 1.3, [ ] 2.1, [~] 2.2, [ ] 2.3
        # If we mark 1.1 as done, next becomes 1.3 (skips 1.2 which is already x).
        rows_after = [
            install_log_lib.Row(
                state="x" if r.number == "1.1" else r.state,
                number=r.number, slug=r.slug, kind=r.kind, source=r.source,
                target=r.target, phase=r.phase,
            )
            for r in self.rows
        ]
        next_row = install_log_lib.first_unchecked_row(rows_after)
        self.assertEqual(next_row.number, "1.3")

    def test_first_unchecked_returns_none_when_all_terminal(self):
        all_done = [
            install_log_lib.Row(
                state="x", number=r.number, slug=r.slug, kind=r.kind,
                source=r.source, target=r.target, phase=r.phase,
            )
            for r in self.rows
        ]
        self.assertIsNone(install_log_lib.first_unchecked_row(all_done))

    def test_checked_rows_missing_artifact_when_file_absent(self):
        # 1.2 is [x] in the sample but the artifact doesn't exist in self.root.
        missing = install_log_lib.checked_rows_missing_artifact(self.rows, self.root)
        self.assertEqual(len(missing), 1)
        row, path = missing[0]
        self.assertEqual(row.number, "1.2")
        self.assertEqual(path.name, ".mcp.json")  # wave 1p7tz: bin/mcp-server retired → .mcp.json

    def test_checked_rows_missing_artifact_empty_when_file_present(self):
        # Create the artifact 1.2 expects.
        artifact = self.root / ".mcp.json"
        artifact.write_text("{}\n")
        missing = install_log_lib.checked_rows_missing_artifact(self.rows, self.root)
        self.assertEqual(missing, [])

    def test_checked_rows_skips_verify_and_instruction(self):
        # Mark 1.3 (instruction) and 2.1 (verify) as [x]; both have no on-disk artifact.
        rows = []
        for r in self.rows:
            new_state = r.state
            if r.number in ("1.3", "2.1"):
                new_state = "x"
            rows.append(install_log_lib.Row(
                state=new_state, number=r.number, slug=r.slug, kind=r.kind,
                source=r.source, target=r.target, phase=r.phase,
            ))
        # 1.2 still flags because it has an artifact path. 1.3 and 2.1 should be skipped.
        missing = install_log_lib.checked_rows_missing_artifact(rows, self.root)
        flagged_numbers = {r.number for r, _ in missing}
        self.assertEqual(flagged_numbers, {"1.2"})

    def test_is_complete_true_only_when_no_pending(self):
        self.assertFalse(install_log_lib.is_complete(self.rows))
        all_terminal = [
            install_log_lib.Row(
                state="x", number=r.number, slug=r.slug, kind=r.kind,
                source=r.source, target=r.target, phase=r.phase,
            )
            for r in self.rows
        ]
        self.assertTrue(install_log_lib.is_complete(all_terminal))


class ReadLogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self.root = Path(self._tmp)

    def tearDown(self):
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_read_install_log_returns_none_when_missing(self):
        self.assertIsNone(install_log_lib.read_install_log(self.root))

    def test_read_install_log_returns_content_when_present(self):
        log_path = self.root / ".wavefoundry" / "install-log.md"
        log_path.parent.mkdir(parents=True)
        log_path.write_text("hello world\n")
        self.assertEqual(install_log_lib.read_install_log(self.root), "hello world\n")


if __name__ == "__main__":
    unittest.main()

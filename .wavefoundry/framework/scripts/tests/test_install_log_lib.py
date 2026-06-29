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
                source=r.source, target=r.target, phase=r.phase, field=r.field,
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
                source=r.source, target=r.target, phase=r.phase, field=r.field,
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


# ---------------------------------------------------------------------------
# Wave 1p8gw — description-as-path defect + template↔parser parity
# ---------------------------------------------------------------------------

TEMPLATE_PATH = (
    SCRIPTS_DIR / ".." / "install" / "install-log.template.md"
).resolve()


class DescriptionAsPathTests(unittest.TestCase):
    """Wave 1p8gw: a seed/script row whose ``artifact:`` value is a prose verification CLAUSE (not a
    single path token) must parse into the row's description, NOT be classified as a stat-able path —
    the field defect that made wave_install_audit verify against bogus 'paths' on a native-Windows
    install."""

    # The real drifted template row 1.2 (compound verification artifact with backticks + " AND ").
    COMPOUND_ROW = (
        "- [x] 1.2 — Bootstrap harness: venv + deps (setup_wavefoundry.py) — artifact: "
        "the committed `.mcp.json` names `command: \"python\"` + `args: [...]` AND "
        "`python3 .wavefoundry/framework/scripts/server.py --dry-run` exits 0"
    )

    def test_compound_artifact_is_not_classified_as_path(self):
        row = install_log_lib.parse_row(self.COMPOUND_ROW, phase=1)
        self.assertIsNotNone(row)
        self.assertEqual(row.kind, "script")
        self.assertEqual(row.field, "artifact")
        # The value parses into `target` (raw) but artifact_path is None (it is prose, not a path)…
        self.assertIsNotNone(row.target)
        self.assertIsNone(row.artifact_path, "compound verification artifact must not be a path")
        # …and is surfaced as a description instead.
        self.assertIsNotNone(row.description)
        self.assertFalse(row.needs_artifact_check, "a prose artifact must never be stat-checked")

    def test_compound_artifact_not_flagged_missing(self):
        # The whole point: a [x] compound-verification row must NOT be reported as a missing artifact.
        with tempfile.TemporaryDirectory() as tmp:
            rows = [install_log_lib.parse_row(self.COMPOUND_ROW, phase=1)]
            missing = install_log_lib.checked_rows_missing_artifact(rows, Path(tmp))
            self.assertEqual(missing, [], "compound verification artifact wrongly stat'd as a path")

    def test_real_path_artifact_still_classified_as_path(self):
        row = install_log_lib.parse_row(
            "- [x] 2.3 — Bootstrap evidence base (seed-030) — artifact: docs/repo-profile.json",
            phase=2,
        )
        self.assertEqual(row.artifact_path, "docs/repo-profile.json")
        self.assertIsNone(row.description)
        self.assertTrue(row.needs_artifact_check)

    def test_path_with_space_in_directory_still_classified_as_path(self):
        # A legitimate path with a space in a directory name must NOT be demoted to a description.
        row = install_log_lib.parse_row(
            "- [~] 2.2 — Capture legacy baseline (seed-110) — artifact: "
            "docs/waves/00000 wave-zero-plans-and-specs/wave.md",
            phase=2,
        )
        self.assertEqual(row.artifact_path, "docs/waves/00000 wave-zero-plans-and-specs/wave.md")
        self.assertIsNone(row.description)

    def test_expects_value_is_a_description_not_a_path(self):
        row = install_log_lib.parse_row(
            "- [ ] 2.1 — Audit Phase 1 (verify) — expects: wave_install_audit(phase=1) returns next_step",
            phase=2,
        )
        self.assertEqual(row.field, "expects")
        self.assertIsNone(row.artifact_path)
        self.assertIsNotNone(row.description)
        self.assertFalse(row.needs_artifact_check)


class TemplateParserParityTests(unittest.TestCase):
    """Wave 1p8gw: the shipped install-log template and ``parse_log`` must agree — every artifact row
    in the template parses into the correct field (path vs description), and a stat-able artifact_path
    never accidentally absorbs prose. Template/parser drift fails this test."""

    @classmethod
    def setUpClass(cls):
        cls.rows = install_log_lib.parse_log(TEMPLATE_PATH.read_text(encoding="utf-8"))

    def test_template_is_parseable(self):
        self.assertTrue(self.rows, "no rows parsed from the install-log template")
        # Every parsed row has a recognized kind.
        for r in self.rows:
            self.assertIn(r.kind, ("seed", "script", "verify", "instruction"))

    def test_every_artifact_row_classifies_consistently(self):
        for r in self.rows:
            if r.field == "artifact":
                # artifact_path XOR description: a value is a path OR a prose clause, never both/neither.
                self.assertTrue(
                    (r.artifact_path is None) != (r.description is None),
                    f"row {r.number}: artifact value '{r.target}' classified ambiguously",
                )
            if r.field == "expects":
                self.assertIsNone(r.artifact_path, f"row {r.number}: expects value treated as a path")
                self.assertIsNotNone(r.description)

    def test_check2_validates_a_minimum_of_real_paths_on_shipped_template(self):
        # POSITIVE parity (review F1): the shipped template backtick-wraps EVERY path. After stripping
        # backticks the parser MUST recover at least 10 stat-able rows — so a regression that disables
        # CHECK 2 (the "any backtick ⇒ prose" bug → 0 stat-able rows) FAILS this test instead of
        # passing vacuously.
        statable = [r for r in self.rows if r.artifact_path is not None]
        self.assertGreaterEqual(
            len(statable), 10,
            f"only {len(statable)} stat-able rows recovered from the shipped template — CHECK 2 is "
            "effectively disabled (backtick-stripping/classifier regressed)",
        )

    def test_known_rows_classify_exactly_as_expected_on_shipped_template(self):
        # POSITIVE, ANCHORED assertions on real shipped rows — these pin the exact path values.
        by_num = {r.number: r for r in self.rows}
        # Row 2.3: a clean backtick-wrapped path -> PATH (the canonical recovery case).
        self.assertEqual(by_num["2.3"].artifact_path, "docs/repo-profile.json")
        self.assertEqual(by_num["2.6"].artifact_path, "docs/ARCHITECTURE.md")
        # Row 2.2: path with a space in a dir name + a trailing conditional aside -> still PATH.
        self.assertEqual(
            by_num["2.2"].artifact_path, "docs/waves/00000 wave-zero-plans-and-specs/wave.md"
        )
        # Multi-seed source tags must PARSE (previously dropped) and their paths recover.
        self.assertIn("2.2", by_num, "row 2.2 (seed-110 / conditional) was dropped by the row regex")
        self.assertIn("2.8", by_num, "row 2.8 (seed-080 + seed-090) was dropped by the row regex")
        self.assertEqual(by_num["2.8"].artifact_path, "docs/contributing/build-and-verification.md")
        # Compound verification clauses stay DESC (never stat'd).
        self.assertIsNone(by_num["1.2"].artifact_path)
        self.assertIsNotNone(by_num["1.2"].description)
        self.assertIsNone(by_num["2.13"].artifact_path)  # "drift entries in `…`" — leading prose
        self.assertIsNotNone(by_num["2.13"].description)

    def test_no_stat_able_path_contains_prose_markers(self):
        # The load-bearing guarantee: nothing wave_install_audit will stat carries prose-clause markers
        # — i.e. no description is mis-read as a path. (Backticks are stripped, so they are NOT a marker
        # here; the markers are sentence conjunctions/verbs.)
        for r in self.rows:
            p = r.artifact_path
            if p is not None:
                for marker in install_log_lib._PROSE_CLAUSE_MARKERS:
                    self.assertNotIn(
                        marker, f" {p} ",
                        f"row {r.number}: stat-able artifact_path '{p}' contains prose marker {marker!r}",
                    )


class CheckTwoIsNotVacuousTests(unittest.TestCase):
    """Wave 1p8gw (review F1): prove wave_install_audit CHECK 2 actually validates — a [x] row whose
    backtick-wrapped artifact path is ABSENT must be flagged missing (the disabled-CHECK-2 defect let
    an operator mark every step [x] with zero files on disk and still get a clean audit)."""

    def test_missing_backtick_wrapped_artifact_is_flagged(self):
        log = (
            "## Phase 2 — Project discovery\n"
            "- [x] 2.3 — Bootstrap evidence base (seed-030) — artifact: `docs/repo-profile.json`\n"
        )
        rows = install_log_lib.parse_log(log)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].artifact_path, "docs/repo-profile.json")
        with tempfile.TemporaryDirectory() as tmp:
            missing = install_log_lib.checked_rows_missing_artifact(rows, Path(tmp))
            self.assertEqual([r.number for r, _ in missing], ["2.3"],
                             "a [x] row with a missing backtick-wrapped path must be flagged by CHECK 2")

    def test_present_backtick_wrapped_artifact_is_not_flagged(self):
        log = (
            "## Phase 2 — Project discovery\n"
            "- [x] 2.3 — Bootstrap evidence base (seed-030) — artifact: `docs/repo-profile.json`\n"
        )
        rows = install_log_lib.parse_log(log)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "docs").mkdir()
            (Path(tmp) / "docs" / "repo-profile.json").write_text("{}\n", encoding="utf-8")
            self.assertEqual(install_log_lib.checked_rows_missing_artifact(rows, Path(tmp)), [])


if __name__ == "__main__":
    unittest.main()

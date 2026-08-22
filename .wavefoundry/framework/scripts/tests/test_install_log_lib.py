"""Tests for install_log_lib.py (the install-log row parser + state queries).

Wave 1p35d (1p35h).
"""

from __future__ import annotations

import ast
import re
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

- [ ] 2.1 — Audit Phase 1 outputs (verify) — expects: wf_audit_install(phase=1) returns next_step
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
            "- [ ] 2.1 — Audit Phase 1 outputs (verify) — expects: wf_audit_install(phase=1) returns next_step",
            phase=2,
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.kind, "verify")
        self.assertEqual(row.target, "wf_audit_install(phase=1) returns next_step")
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

    def _write_bytes(self, raw: bytes):
        log_path = self.root / ".wavefoundry" / "install-log.md"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_bytes(raw)
        return log_path

    def test_read_install_log_does_not_raise_on_utf16_bom_log(self):
        # Wave 1p9hj: a PowerShell Set-Content/Out-File default write produces UTF-16 with a BOM.
        # read_install_log must decode with errors="replace" (not raise UnicodeDecodeError) so the
        # audit's is_unparseable safety net can run and surface an actionable error.
        content = "## Phase 1\n\n- [x] 1.1 — Epoch (seed-020) — artifact: docs/workflow-config.json\n"
        self._write_bytes(content.encode("utf-16"))  # includes BOM \xff\xfe
        result = install_log_lib.read_install_log(self.root)
        self.assertIsInstance(result, str)
        # The garbled decode yields zero parseable rows and is classified unparseable.
        self.assertEqual(install_log_lib.parse_log(result), [])
        self.assertTrue(install_log_lib.is_unparseable(result, []))

    def test_read_install_log_does_not_raise_on_cp1252_log(self):
        # Wave 1p9hj: a bare ANSI (cp1252) write of an em-dash produces raw byte 0x97 — a lone
        # continuation byte that is invalid UTF-8. read_install_log must decode it with
        # errors="replace" (not raise UnicodeDecodeError). Per AC-4 the log then either parses (ASCII
        # markers survived) or is classified unparseable — never a crash and never vacuous success.
        raw = b"## Phase 1\n\n- [ ] 1.1 \x97 Epoch (seed-020) \x97 artifact: docs/workflow-config.json\n"
        self._write_bytes(raw)
        result = install_log_lib.read_install_log(self.root)
        self.assertIsInstance(result, str)
        rows = install_log_lib.parse_log(result)
        self.assertTrue(
            rows or install_log_lib.is_unparseable(result, rows),
            "cp1252 log must either parse to rows or be flagged unparseable, never crash/vacuous-succeed",
        )


# ---------------------------------------------------------------------------
# Wave 1p8gw — description-as-path defect + template↔parser parity
# ---------------------------------------------------------------------------

TEMPLATE_PATH = (
    SCRIPTS_DIR / ".." / "install" / "install-log.template.md"
).resolve()
FRAMEWORK_ROOT = SCRIPTS_DIR.parent
REPO_ROOT = Path(__file__).resolve().parents[4]
SEEDS_DIR = FRAMEWORK_ROOT / "seeds"
SEED_012_PATH = SEEDS_DIR / "012-install-wavefoundry-phase-2.prompt.md"

# Wave 1vj4e (1vmpz): decimal-extension rows such as `2.13.5` are legal (install-log-format.md
# forbids renumbering), so both regexes accept `2.N(.M)*` and the mention test asserts the FULL
# token resolved; before the widening the heading regex missed `### 2.13.5` and the mention regex
# silently resolved "step 2.13.5" to `2.13`.
_SEED_STEP_HEADING_RE = re.compile(
    r"^###\s+(2\.\d+(?:\.\d+)*)([a-z]?)\s+—\s+(.+?)\s*$",
    re.MULTILINE,
)
_STEP_MENTION_RE = re.compile(
    r"\b(?:Phase\s+2\s+)?steps?\s+(2\.\d+(?:\.\d+)*[a-z]?)\b",
    re.IGNORECASE,
)


def _seed_012_sections() -> dict[str, tuple[str, str]]:
    text = SEED_012_PATH.read_text(encoding="utf-8")
    matches = list(_SEED_STEP_HEADING_RE.finditer(text))
    sections: dict[str, tuple[str, str]] = {}
    for index, match in enumerate(matches):
        step = match.group(1) + match.group(2)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        if step in sections:
            raise AssertionError(f"duplicate seed-012 heading for step {step}")
        sections[step] = (match.group(3), text[match.start():end])
    return sections


def _seed_numbers(text: str) -> tuple[str, ...]:
    if "seed" not in text.lower():
        return ()
    return tuple(re.findall(r"\b\d{3}\b", text))


class DescriptionAsPathTests(unittest.TestCase):
    """Wave 1p8gw: a seed/script row whose ``artifact:`` value is a prose verification CLAUSE (not a
    single path token) must parse into the row's description, NOT be classified as a stat-able path —
    the field defect that made wf_audit_install verify against bogus 'paths' on a native-Windows
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
            "- [ ] 2.1 — Audit Phase 1 (verify) — expects: wf_audit_install(phase=1) returns next_step",
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
        # The load-bearing guarantee: nothing wf_audit_install will stat carries prose-clause markers
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


class FreshInstallContractParityTests(unittest.TestCase):
    """Wave 1viyu: the shipped checklist, phase-2 seed, and referenced carriers stay executable."""

    @classmethod
    def setUpClass(cls):
        cls.template_text = TEMPLATE_PATH.read_text(encoding="utf-8")
        cls.template_rows = [
            row for row in install_log_lib.parse_log(cls.template_text)
            if row.phase == 2
        ]
        cls.seed_text = SEED_012_PATH.read_text(encoding="utf-8")
        cls.seed_sections = _seed_012_sections()

    def test_every_template_seed_reference_resolves(self):
        for row in self.template_rows:
            if row.kind != "seed":
                continue
            refs = re.findall(r"seed-(\d{3})", row.source)
            self.assertTrue(refs, f"row {row.number}: seed row has no seed reference")
            for number in refs:
                with self.subTest(row=row.number, seed=number):
                    matches = sorted(SEEDS_DIR.glob(f"{number}-*.md"))
                    self.assertEqual(
                        len(matches),
                        1,
                        f"row {row.number}: seed-{number} must resolve to exactly one shipped seed",
                    )

    def test_numbered_template_rows_and_seed_headings_are_one_to_one(self):
        template_by_number = {row.number: row for row in self.template_rows}
        expected_numbers = {
            *(f"2.{number}" for number in range(1, 12)),
            "2.13",
            "2.13.5",
            "2.14",
            "2.15",
        }
        self.assertEqual(
            len(template_by_number),
            len(self.template_rows),
            "duplicate template row number",
        )
        self.assertEqual(set(template_by_number), expected_numbers)
        numbered_sections = {
            step: section
            for step, section in self.seed_sections.items()
            if not step[-1].isalpha()
        }
        self.assertEqual(set(template_by_number), set(numbered_sections))

        for number, row in template_by_number.items():
            title, section = numbered_sections[number]
            with self.subTest(step=number):
                if row.kind == "seed":
                    self.assertEqual(_seed_numbers(title), _seed_numbers(row.source))
                elif row.kind == "verify":
                    self.assertIn("wf_audit_install", section)
                elif row.kind == "instruction":
                    self.assertIn(number, {"2.14", "2.15"})

    def test_final_tail_is_parser_visible_and_has_exact_actions(self):
        by_number = {row.number: row for row in self.template_rows}
        self.assertNotIn("2.12", by_number, "the retired seed-130 row must stay absent")

        expected_words = {
            "2.14": ("remove", "bootstrap"),
            "2.15": ("prepare", "summary"),
        }
        template_lines = {
            match.group(1): match.group(0)
            for match in re.finditer(
                r"^\s*-\s+\[[ x~]\]\s+(2\.1[45])\b.*$",
                self.template_text,
                re.MULTILINE,
            )
        }
        for number, words in expected_words.items():
            with self.subTest(step=number):
                row = by_number[number]
                self.assertEqual(row.kind, "instruction")
                self.assertIsNone(row.target)
                self.assertTrue(template_lines[number].rstrip().endswith("(instruction)"))
                template_action = row.slug.lower()
                seed_title = self.seed_sections[number][0].lower()
                for word in words:
                    self.assertIn(word, template_action)
                    self.assertIn(word, seed_title)
        self.assertNotIn("deliver", by_number["2.15"].slug.lower())

        bad_suffix = template_lines["2.15"] + " — covers: workflow, commands"
        self.assertIsNone(
            install_log_lib.parse_row(bad_suffix, phase=2),
            "control: an instruction-row suffix must make the row parser-invisible",
        )

    def test_seed_orders_prepare_mark_final_audit_then_delivery(self):
        _, final_section = self.seed_sections["2.15"]
        lowered = final_section.lower()
        prepare_pos = lowered.find("prepare")
        mark_pos = lowered.find("mark", prepare_pos + 1)
        audit_pos = lowered.find("wf_audit_install", mark_pos + 1)
        complete_pos = lowered.find("complete", audit_pos + 1)
        deliver_pos = lowered.find("deliver", complete_pos + 1)
        positions = [prepare_pos, mark_pos, audit_pos, complete_pos, deliver_pos]
        self.assertTrue(all(position >= 0 for position in positions), positions)
        self.assertEqual(positions, sorted(positions))

    def test_framework_path_literals_in_install_seeds_resolve(self):
        for seed_name in (
            "010-install-wavefoundry.prompt.md",
            "011-install-wavefoundry-phase-1.prompt.md",
            "012-install-wavefoundry-phase-2.prompt.md",
        ):
            text = (SEEDS_DIR / seed_name).read_text(encoding="utf-8")
            paths = sorted(set(re.findall(r"`(\.wavefoundry/framework/[^`]+)`", text)))
            self.assertTrue(paths, f"{seed_name}: expected at least one framework path fixture")
            for rel in paths:
                with self.subTest(seed=seed_name, path=rel):
                    self.assertTrue((REPO_ROOT / rel).exists(), f"unresolved framework path: {rel}")

    def test_phase_2_step_mentions_resolve_to_seed_012(self):
        known_steps = set(self.seed_sections)
        candidates = sorted(SEEDS_DIR.glob("*.md")) + sorted((FRAMEWORK_ROOT / "install").glob("*.md"))
        for path in candidates:
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for match in _STEP_MENTION_RE.finditer(line):
                    step = match.group(1)
                    with self.subTest(path=path.name, line=line_number, step=step):
                        # The token must be the FULL dotted number: a mention like
                        # "step 2.13.5" must not resolve to `2.13`.
                        self.assertFalse(
                            re.match(r"\.\d", line[match.end(1):]),
                            f"step mention truncated at {step!r}: {line.strip()!r}",
                        )
                        self.assertIn(step, known_steps)
                        _, section = self.seed_sections[step]
                        if "wf_audit_install" in line:
                            self.assertIn("wf_audit_install", section)

    def test_row_2_13_5_is_a_stat_checked_seed_row_with_the_catalog_artifact(self):
        """Wave 1vj4e (1vmpz AC-4): the Refresh TechDocs row is a `(seed-178)` seed row (an
        instruction row could not carry a stat-checked artifact), its artifact is the root
        `catalog-info.yaml`, CHECK 2 flags a `[x]` row without the file and skips `[~]`."""
        row = {r.number: r for r in self.template_rows}["2.13.5"]
        self.assertEqual(row.kind, "seed")
        self.assertEqual(row.source, "seed-178")
        self.assertEqual(row.artifact_path, "catalog-info.yaml")
        self.assertIn("Refresh TechDocs", row.slug)
        self.assertEqual(sorted(SEEDS_DIR.glob("178-*.md")), [SEEDS_DIR / "178-refresh-techdocs.prompt.md"])
        title, section = self.seed_sections["2.13.5"]
        self.assertIn("seed-178", title)
        self.assertIn("[~]", section)
        self.assertIn("wf techdocs-baseline", section)
        self.assertNotIn("techdocs_baseline.py", section)
        line = "- [x] 2.13.5 — Generate the Backstage catalog and TechDocs baseline via Refresh TechDocs (seed-178) — artifact: `catalog-info.yaml`"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            checked = install_log_lib.parse_log("## Phase 2\n" + line + "\n")
            self.assertEqual(
                [(r.number, r.artifact_path) for r, _expected in install_log_lib.checked_rows_missing_artifact(checked, root)],
                [("2.13.5", "catalog-info.yaml")],
            )
            (root / "catalog-info.yaml").write_text("kind: Component\n", encoding="utf-8")
            self.assertEqual(install_log_lib.checked_rows_missing_artifact(checked, root), [])
            (root / "catalog-info.yaml").unlink()
            declined = install_log_lib.parse_log("## Phase 2\n" + line.replace("[x]", "[~]") + "\n")
            self.assertEqual(install_log_lib.checked_rows_missing_artifact(declined, root), [])

    def test_row_2_13_5_boundary_through_the_install_audit(self):
        """`[ ]` 2.13.5 is the next step; `[~]` hands over to 2.14; `[x]` without the file is
        `checked_but_missing` (through `wf_audit_install_response`, `run_validate` mocked)."""
        import sys as _sys
        from unittest.mock import patch as _patch

        _sys.path.insert(0, str(SCRIPTS_DIR))
        import server_impl

        clean = {"passed": True, "errors": [], "warnings": [], "output": "docs-lint: ok"}
        # The tail of the shipped template (rows 2.13.5, 2.14, 2.15 verbatim); earlier rows are
        # omitted so no other artifact check interferes with the boundary under test.
        tail = [
            line for line in self.template_text.splitlines()
            if line.startswith("- [ ] 2.13.5 ") or line.startswith("- [ ] 2.14 ") or line.startswith("- [ ] 2.15 ")
        ]
        self.assertEqual(len(tail), 3, tail)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".wavefoundry").mkdir()

            def write_log(state_2_13_5: str) -> None:
                lines = ["## Phase 2"]
                for raw in tail:
                    if raw.startswith("- [ ] 2.13.5 "):
                        raw = raw.replace("[ ]", f"[{state_2_13_5}]", 1)
                    lines.append(raw)
                (root / ".wavefoundry" / "install-log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

            with _patch.object(server_impl, "run_validate", return_value=clean):
                write_log(" ")
                result = server_impl.wf_audit_install_response(root)
                self.assertEqual(result["data"]["status"], "next_step", result)
                self.assertEqual(result["data"]["row"]["number"], "2.13.5")

                write_log("~")
                result = server_impl.wf_audit_install_response(root)
                self.assertEqual(result["data"]["status"], "next_step", result)
                self.assertEqual(result["data"]["row"]["number"], "2.14")

                write_log("x")
                result = server_impl.wf_audit_install_response(root)
                self.assertEqual(result["data"]["status"], "checked_but_missing", result)
                self.assertEqual(result["data"]["row"]["number"], "2.13.5")

                (root / "catalog-info.yaml").write_text("kind: Component\n", encoding="utf-8")
                result = server_impl.wf_audit_install_response(root)
                self.assertEqual(result["data"]["status"], "next_step", result)
                self.assertEqual(result["data"]["row"]["number"], "2.14")

    def test_setup_docstring_names_live_log_not_phantom_root_log(self):
        setup_path = SCRIPTS_DIR / "setup_wavefoundry.py"
        module = ast.parse(setup_path.read_text(encoding="utf-8"))
        docstring = ast.get_docstring(module) or ""
        self.assertIn(".wavefoundry/install-log.md", docstring)
        self.assertIn("install-log.template.md", docstring)
        self.assertNotIn("wavefoundry-install-log.md", docstring)


class InstallPendingLintClassifierTests(unittest.TestCase):
    def test_pending_seed_defers_only_absent_marker_paths_and_strips_prefixes(self):
        rows = install_log_lib.parse_log(
            "## Phase 2\n- [ ] 2.2 — Bootstrap evidence (seed-030) — artifact: docs/repo-profile.json\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            existing = root / "docs/existing.md"
            existing.parent.mkdir(parents=True)
            existing.write_text("present\n", encoding="utf-8")
            pending = "ERROR: ERROR: docs/missing.md: missing required Wavefoundry file"
            present = "docs/existing.md: missing required Wavefoundry file"
            # Wave 1viyu (CODE-DEL-3): the load-bearing direction of prefix
            # stripping. Every real `run_validate` line carries `ERROR: `; without
            # stripping, `partition(": ")` yields the candidate path "ERROR", which
            # never exists, so a stale absence about a PRESENT file would be
            # deferred. This case must classify as blocking.
            present_prefixed = "ERROR: ERROR: docs/existing.md: missing required Wavefoundry file"
            ordinary = "docs/config.md: invalid policy value"
            blocking, expected = install_log_lib.classify_lint_errors(
                [pending, present, present_prefixed, ordinary], rows, root
            )
        self.assertEqual(expected, [pending])
        self.assertEqual(blocking, [present, present_prefixed, ordinary])

    def test_only_seed_rows_pending_defers_absences(self):
        """Wave 1viyu (CODE-DEL-3): rule (i) is SEED-row pending, not any-row pending.

        A log whose only pending rows are verify/instruction rows (the final tail after
        every seed row is terminal) must classify an absence-class error as blocking,
        because nothing left to run will create the file.
        """
        rows = install_log_lib.parse_log(
            "## Phase 2\n"
            "- [x] 2.2 — Bootstrap evidence (seed-030) — artifact: docs/repo-profile.json\n"
            "- [ ] 2.14 — Final install completeness gate (verify) — expects: complete\n"
            "- [ ] 2.15 — Deliver operator summary (instruction)\n"
        )
        error = "ERROR: docs/missing.md: missing required Wavefoundry file"
        with tempfile.TemporaryDirectory() as temp_dir:
            blocking, expected = install_log_lib.classify_lint_errors(
                [error], rows, Path(temp_dir)
            )
        self.assertEqual(blocking, [error])
        self.assertEqual(expected, [])

    def test_no_pending_seed_makes_every_lint_error_blocking(self):
        rows = install_log_lib.parse_log(
            "## Phase 2\n- [x] 2.2 — Bootstrap evidence (seed-030) — artifact: docs/repo-profile.json\n"
        )
        error = "docs/missing.md: missing required Wavefoundry generated artifact"
        with tempfile.TemporaryDirectory() as temp_dir:
            blocking, expected = install_log_lib.classify_lint_errors(
                [error], rows, Path(temp_dir)
            )
        self.assertEqual(blocking, [error])
        self.assertEqual(expected, [])


class CheckTwoIsNotVacuousTests(unittest.TestCase):
    """Wave 1p8gw (review F1): prove wf_audit_install CHECK 2 actually validates — a [x] row whose
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


_MOJIBAKE_EMDASH = "â€”"  # UTF-8 em dash (E2 80 94) misread as cp1252 -> "â€”"


class EncodingRobustParseTests(unittest.TestCase):
    """Wave 1p9bh: rows parse regardless of separator encoding; empty parse is never 'complete'."""

    def test_row_parses_across_separator_encodings(self):
        for sep in ("—", "–", "-", _MOJIBAKE_EMDASH):
            line = f"- [x] 1.1 {sep} Set lifecycle epoch (seed-020) {sep} artifact: docs/workflow-config.json"
            row = install_log_lib.parse_row(line, phase=1)
            self.assertIsNotNone(row, f"separator {sep!r} failed to parse")
            self.assertEqual(row.state, "x")
            self.assertEqual(row.number, "1.1")
            self.assertEqual(row.source, "seed-020")
            self.assertEqual(row.target, "docs/workflow-config.json")

    def test_parse_log_of_mojibake_log_is_not_empty(self):
        # The whole point of the fix: a mojibake'd log now PARSES rather than yielding zero rows.
        log = (
            "## Phase 1 — Harness\n\n"
            f"- [x] 1.1 {_MOJIBAKE_EMDASH} Epoch (seed-020) {_MOJIBAKE_EMDASH} artifact: docs/workflow-config.json\n"
            f"- [ ] 1.2 {_MOJIBAKE_EMDASH} Bootstrap (setup_wavefoundry.py) {_MOJIBAKE_EMDASH} artifact: .mcp.json\n"
        )
        rows = install_log_lib.parse_log(log)
        self.assertEqual(len(rows), 2)
        self.assertFalse(install_log_lib.is_complete(rows))  # 1.2 still pending

    def test_is_complete_empty_is_false(self):
        self.assertFalse(install_log_lib.is_complete([]))  # vacuous-truth guard
        done = install_log_lib.parse_row("- [x] 1.1 — Epoch (seed-020) — artifact: docs/workflow-config.json", 1)
        pend = install_log_lib.parse_row("- [ ] 1.2 — Boot (setup_wavefoundry.py) — artifact: .mcp.json", 1)
        self.assertTrue(install_log_lib.is_complete([done]))
        self.assertFalse(install_log_lib.is_complete([done, pend]))

    def test_is_unparseable_flags_present_but_zero_rows(self):
        # A log with checkbox-shaped content the parser still can't turn into rows -> unparseable.
        corrupt = "## Phase 1\n\n- [ ] this line has no number and no source\n"
        self.assertEqual(install_log_lib.parse_log(corrupt), [])
        self.assertTrue(install_log_lib.is_unparseable(corrupt, []))
        # A clean/parseable log is NOT unparseable.
        clean = "## Phase 1\n\n- [x] 1.1 — Epoch (seed-020) — artifact: docs/workflow-config.json\n"
        self.assertFalse(install_log_lib.is_unparseable(clean, install_log_lib.parse_log(clean)))
        # No log / blank text is NOT unparseable (that's "no log", handled elsewhere).
        self.assertFalse(install_log_lib.is_unparseable(None, []))
        self.assertFalse(install_log_lib.is_unparseable("   \n", []))

    def test_is_unparseable_flags_non_utf8_decode_with_no_markers(self):
        # Wave 1p9hj: a UTF-16 log decoded with errors="replace" loses its ASCII markers (NUL bytes
        # break the "## Phase"/checkbox patterns) and gains U+FFFD from the BOM. is_unparseable must
        # still classify it via the replacement-char / NUL signal, independent of the marker patterns.
        utf16_decoded = (
            "## Phase 1\n\n- [x] 1.1 — Epoch — artifact: docs/workflow-config.json\n"
            .encode("utf-16").decode("utf-8", errors="replace")
        )
        self.assertEqual(install_log_lib.parse_log(utf16_decoded), [])
        self.assertTrue(install_log_lib.is_unparseable(utf16_decoded, []))
        # A pure replacement-char blob (e.g. raw cp1252 with no ASCII markers) is also flagged.
        self.assertTrue(install_log_lib.is_unparseable("�� garbage �", []))
        # A clean UTF-8 log with a real em-dash but a genuine phase heading still parses (not flagged).
        clean_emdash = "## Phase 1\n\n- [x] 1.1 — Epoch (seed-020) — artifact: docs/workflow-config.json\n"
        self.assertFalse(
            install_log_lib.is_unparseable(clean_emdash, install_log_lib.parse_log(clean_emdash))
        )

    def test_write_install_log_roundtrips_utf8_emdash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content = "## Phase 1\n\n- [ ] 1.1 — Epoch (seed-020) — artifact: docs/workflow-config.json\n"
            path = install_log_lib.write_install_log(root, content)
            self.assertTrue(path.exists())
            self.assertIn("—", path.read_text(encoding="utf-8"))  # em dash survived
            self.assertEqual(len(install_log_lib.parse_log(install_log_lib.read_install_log(root))), 1)


if __name__ == "__main__":
    unittest.main()

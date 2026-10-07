"""Unit tests for the shared change-document checklist parser (wave 1zime, 1zimq)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import change_doc_checklist as cdc  # noqa: E402
import vocabulary_profile as _vocab  # noqa: E402
import tempfile  # noqa: E402


class ChecklistItemPatternTests(unittest.TestCase):
    def _items(self, text):
        return [(m.group("marker"), m.group("mark"), m.group("text"))
                for m in cdc.CHECKLIST_ITEM_RE.finditer(text)]

    def test_every_commonmark_marker_is_an_item(self):
        for marker in ("-", "*", "+", "1.", "1)", "12.", "123456789)"):
            with self.subTest(marker=marker):
                self.assertEqual(self._items(f"{marker} [ ] step\n"), [(marker, " ", "step")])

    def test_marks_and_indentation(self):
        text = "  - [x] a\n\t* [X] b\n    1. [~] c\n- [ ] d"
        self.assertEqual([i[1] for i in self._items(text)], ["x", "X", "~", " "])

    def test_non_items_are_not_matched(self):
        # Wave 1zls7 (1zltr): `- [?] other mark` is now an item (an open
        # unusual mark); `[]` and multi-character marks stay non-items.
        for line in ("- step", "-[ ] glued", "1234567890. [ ] ten digits", "a. [ ] letter",
                     "text - [ ] mid-line", "- [] empty", "- [ab] two", "- [  ] two spaces",
                     "- [ x] two", "text > - [ ] mid-line quote"):
            with self.subTest(line=line):
                self.assertEqual(self._items(line + "\n"), [])

    def test_crlf_text_excludes_carriage_return(self):
        self.assertEqual(self._items("* [ ] step\r\n- [x] done\r\n"),
                         [("*", " ", "step"), ("-", "x", "done")])

    def test_is_canonical_marker(self):
        self.assertTrue(cdc.is_canonical_marker("-"))
        for marker in ("*", "+", "1.", "1)"):
            self.assertFalse(cdc.is_canonical_marker(marker))


class LeadingAcIdTests(unittest.TestCase):
    def test_leading_forms(self):
        for text in ("AC-1: x", "AC-1 (required): x", "**AC-1**: x", "`AC-1` x", "  AC-1: x"):
            with self.subTest(text=text):
                self.assertEqual(cdc.leading_ac_id(text), "AC-1")
        self.assertEqual(cdc.leading_ac_id("AC-12b-x: y"), "AC-12b-x")

    def test_no_leading_id(self):
        for text in ("Covers AC-1", "Covers the remainder; see AC-2", "", "ac-1: lower",
                     "**AC-1: unclosed", "`AC-1 unclosed"):
            with self.subTest(text=text):
                self.assertIsNone(cdc.leading_ac_id(text))


class SectionBodiesTests(unittest.TestCase):
    def test_every_exact_section(self):
        text = ("# T\n\n## Tasks\n\n- [ ] a\n\n## Other\n\n- [ ] x\n\n"
                "## Tasks  \n- [ ] b\n### Sub\n- [ ] c\n")
        bodies = cdc.section_bodies(text, "Tasks")
        self.assertEqual(len(bodies), 2)
        self.assertIn("- [ ] a", bodies[0])
        self.assertNotIn("- [ ] x", bodies[0])
        self.assertIn("- [ ] b", bodies[1])
        self.assertIn("- [ ] c", bodies[1], "an H3 does not end an H2 section")

    def test_near_miss_headings_are_absent(self):
        for heading in ("## Task", "## Tasks (remaining)", "### Tasks", "##Tasks",
                        "##  Tasks", "Prose naming `## Tasks` inline", " ## Tasks"):
            with self.subTest(heading=heading):
                self.assertEqual(cdc.section_bodies(f"# T\n\n{heading}\n\n- [ ] a\n", "Tasks"), [])
                self.assertFalse(cdc.has_section(f"# T\n\n{heading}\n", "Tasks"))

    def test_empty_and_final_sections(self):
        self.assertEqual(cdc.section_bodies("## Tasks\n\n## AC Priority\n", "Tasks"), [""])
        self.assertEqual(cdc.section_bodies("## Tasks", "Tasks"), [""])
        self.assertTrue(cdc.has_section("## Tasks\n", "Tasks"))

    def test_crlf_matches_lf(self):
        lf = "# T\n\n## Acceptance Criteria\n\n* [ ] AC-1: x\n\n## Tasks\n\n1. [ ] s\n"
        crlf = lf.replace("\n", "\r\n")
        for heading in ("Acceptance Criteria", "Tasks"):
            lf_items = [m.group("text") for b in cdc.section_bodies(lf, heading)
                        for m in cdc.CHECKLIST_ITEM_RE.finditer(b)]
            crlf_items = [m.group("text") for b in cdc.section_bodies(crlf, heading)
                          for m in cdc.CHECKLIST_ITEM_RE.finditer(b)]
            self.assertEqual(lf_items, crlf_items)
            self.assertTrue(lf_items)

    def test_section_items_helper(self):
        text = "## Tasks\n- [ ] a\n## Tasks\n* [x] b\n"
        self.assertEqual([(m.group("marker"), m.group("text")) for m in cdc.section_items(text, "Tasks")],
                         [("-", "a"), ("*", "b")])



class BlockquoteAndMarkTests(unittest.TestCase):
    """Wave 1zls7 (1zltr) Requirements 1 and 2."""

    def _items(self, text):
        return [(m.group("marker"), m.group("mark"), m.group("text"))
                for m in cdc.CHECKLIST_ITEM_RE.finditer(text)]

    def test_blockquoted_items_are_items(self):
        for line in ("> - [ ] x", ">> - [ ] x", "> > - [x] x", "  >- [ ] x", ">\t* [ ] x"):
            with self.subTest(line=line):
                items = self._items(line + "\n")
                self.assertEqual(len(items), 1, line)
                self.assertEqual(items[0][2], "x")

    def test_any_single_character_mark_is_an_item(self):
        for mark in ("-", "/", "?", "o", "!", "\t"):
            with self.subTest(mark=mark):
                self.assertEqual(self._items(f"- [{mark}] step\n"), [("-", mark, "step")])

    def test_only_x_and_tilde_close(self):
        for mark in ("x", "X", "~"):
            self.assertFalse(cdc.is_open_mark(mark))
            self.assertTrue(cdc.is_canonical_mark(mark))
        for mark in (" ", "-", "/", "?"):
            self.assertTrue(cdc.is_open_mark(mark))
        self.assertTrue(cdc.is_canonical_mark(" "))
        for mark in ("-", "/", "o"):
            self.assertFalse(cdc.is_canonical_mark(mark))

    def test_crlf_blockquote_and_unusual_mark(self):
        self.assertEqual(self._items("> - [-] step\r\n> - [x] done\r\n"),
                         [("-", "-", "step"), ("-", "x", "done")])


class FenceTests(unittest.TestCase):
    """Wave 1zls7 (1zltr) Requirement 3."""

    def _flags(self, text):
        return cdc.fenced_line_flags(text.split("\n"))

    def test_closed_backtick_and_tilde_fences(self):
        self.assertEqual(self._flags("a\n```\n## x\n```\nb"), [False, True, True, True, False])
        self.assertEqual(self._flags("a\n~~~~ md\n## x\n~~~~\nb"), [False, True, True, True, False])

    def test_closer_must_match_character_and_length(self):
        # A shorter closer or the other character does not close; the longer one does.
        self.assertEqual(self._flags("````\n```\n~~~~\n`````\nb"), [True, True, True, True, False])
        # A closer with trailing text does not close: the fence is unterminated.
        self.assertEqual(self._flags("```\nx\n``` not\nb"), [False] * 4)

    def test_unterminated_fence_is_not_a_fence(self):
        self.assertEqual(self._flags("```\n## Tasks\n- [ ] x"), [False, False, False])

    def test_backtick_info_with_backtick_is_not_an_opener(self):
        self.assertEqual(self._flags("```a`b\nx\n```\ny"), [False, False, False, False])

    def test_indent_up_to_three_spaces(self):
        self.assertEqual(self._flags("   ```\nx\n   ```"), [True, True, True])
        self.assertEqual(self._flags("    ```\nx\n    ```"), [False, False, False])

    def test_quoted_fence_closes_inside_the_quote(self):
        self.assertEqual(self._flags("> ```\n> ## x\n> ```\nb"), [True, True, True, False])

    def test_quoted_fence_ends_at_the_first_unquoted_line(self):
        # Red-team R7: the quote ends before a closer, so the fence never
        # opened and the later unquoted closer-like line hides nothing.
        text = "> ```\n> - [ ] quoted\n## Tasks\n- [ ] open\n```"
        self.assertEqual(self._flags(text), [False] * 5)
        self.assertTrue(cdc.has_section(text, "Tasks"))
        self.assertEqual([m.group("text") for m in cdc.section_items(text, "Tasks")], ["open"])

    def test_crlf_fence(self):
        self.assertEqual(self._flags("```\r\n## x\r\n```\r\nb"), [True, True, True, False])

    def test_fenced_heading_does_not_end_a_section(self):
        text = "## Tasks\n- [x] a\n```sh\n## not a heading\n- [ ] example\n```\n- [ ] after\n## Other\n- [ ] o\n"
        self.assertEqual(len(cdc.section_bodies(text, "Tasks")), 1)
        self.assertEqual([(m.group("mark"), m.group("text")) for m in cdc.section_items(text, "Tasks")],
                         [("x", "a"), (" ", "after")])
        self.assertFalse(cdc.has_section("```\n## Tasks\n```\n", "Tasks"))
        self.assertEqual(cdc.near_miss_headings("```\n## Tasks (x)\n```\n", "Tasks"), [])

    def test_unterminated_fence_hides_no_heading_or_item(self):
        text = "## Tasks\n- [x] a\n```\n- [ ] x\n## AC Priority\n"
        self.assertEqual([(m.group("mark"), m.group("text")) for m in cdc.section_items(text, "Tasks")],
                         [("x", "a"), (" ", "x")])
        self.assertTrue(cdc.has_section(text, "AC Priority"))

    def test_unfenced_text_and_section_text(self):
        text = "## Tasks\n- [ ] a\n```\n- [ ] b\n```\n"
        self.assertNotIn("- [ ] b", cdc.section_text(text, "Tasks"))
        self.assertIn("- [ ] a", cdc.section_text(text, "Tasks"))


def _reference_fenced_line_flags(lines: list[str]) -> list[bool]:
    """The pre-1zxnt algorithm, verbatim (wave 1zyb2, change 1zxnt AC-1)."""
    flags = [False] * len(lines)
    index = 0
    while index < len(lines):
        depth, rest = cdc.split_blockquote(lines[index])
        opener = cdc._fence_opener(rest)
        if opener is None:
            index += 1
            continue
        char, length = opener
        close = None
        for probe in range(index + 1, len(lines)):
            probe_depth, probe_rest = cdc.split_blockquote(lines[probe])
            if probe_depth < depth:
                break
            if probe_depth == depth and cdc._closes_fence(probe_rest, char, length):
                close = probe
                break
        if close is None:
            index += 1
            continue
        for flagged in range(index, close + 1):
            flags[flagged] = True
        index = close + 1
    return flags


class FenceScanDifferentialTests(unittest.TestCase):
    """Wave 1zyb2 (1zxnt) AC-1: the linear scan returns exactly what the old scan returned."""

    def _assert_same(self, lines):
        self.assertEqual(cdc.fenced_line_flags(lines), _reference_fenced_line_flags(lines), lines)

    def test_seeded_random_inputs_match_the_reference(self):
        import random

        rng = random.Random(1729)
        bodies = []
        for char in "`~":
            for length in (3, 4, 5):
                fence = char * length
                bodies += [fence, fence + "python", fence + " md", fence + "  "]
        bodies += ["```a`b", "plain text", "", "## Heading", "- [ ] item", "    ```", "``` not"]
        for _ in range(400):
            lines = []
            for _ in range(rng.randint(0, 40)):
                depth = rng.choice((0, 0, 0, 1, 1, 2, 3))
                prefix = "".join(rng.choice(("> ", ">")) for _ in range(depth))
                lines.append(prefix + rng.choice(bodies))
            self._assert_same(lines)

    def test_hand_written_cases_match_the_reference(self):
        cases = [
            "a\n```\nx\n```\nb",
            "> ```\n> > ~~~\n> > x\n> > ~~~\n> ```",
            "> ```\n> x\nplain\n```",
            "> ```\nplain\n> ```\n> x\n> ```",
            "````\nx\n```\ny\n```",
            "```\n~~~\n```\n~~~",
            "",
            "```",
            "```python\n```python\n```python",
        ]
        for text in cases:
            with self.subTest(text=text):
                self._assert_same(text.split("\n"))
        self._assert_same([])

    def test_an_opener_after_a_depth_drop_is_scanned_afresh(self):
        lines = ["> ```", "> x", "plain", "> ```", "> y", "> ```"]
        self.assertEqual(cdc.fenced_line_flags(lines), [False, False, False, True, True, True])
        self._assert_same(lines)

    def test_an_unterminated_fence_then_a_terminated_one_of_another_length(self):
        lines = ["````", "```", "x", "```"]
        self.assertEqual(cdc.fenced_line_flags(lines), [False, True, True, True])
        self._assert_same(lines)


class FenceScanScalingTests(unittest.TestCase):
    """Wave 1zyb2 (1zxnt) AC-2: a ratio bound, not a wall-time bound."""

    @staticmethod
    def _best_of_three(lines):
        import gc
        import time

        best = None
        gc.disable()
        try:
            for _ in range(3):
                start = time.perf_counter()
                result = cdc.fenced_line_flags(lines)
                elapsed = time.perf_counter() - start
                best = elapsed if best is None else min(best, elapsed)
        finally:
            gc.enable()
        return best, result

    def _assert_linear(self, line):
        small, small_result = self._best_of_three([line] * 2000)
        large, large_result = self._best_of_three([line] * 8000)
        self.assertEqual(small_result, [False] * 2000)
        self.assertEqual(large_result, [False] * 8000)
        ratio = large / max(small, 1e-9)
        self.assertLess(ratio, 8, f"t(8000)/t(2000) = {ratio:.2f} for {line!r} (linear 4, quadratic 16)")

    def test_unclosed_info_string_openers_scale_linearly(self):
        self._assert_linear("```python")

    def test_unclosed_quoted_tilde_openers_scale_linearly(self):
        self._assert_linear("> ~~~x")


class NearMissHeadingTests(unittest.TestCase):
    """Wave 1zls7 (1zltr) Requirement 4a (red-team R5)."""

    def test_case_whitespace_and_indent_are_near_misses(self):
        for heading, name in (("##  Tasks", "Tasks"), ("## tasks", "Tasks"),
                              ("## Acceptance criteria", "Acceptance Criteria"),
                              ("## Acceptance  Criteria", "Acceptance Criteria"),
                              ("   ## Tasks", "Tasks"), ("##\tTasks", "Tasks"),
                              ("## Tasks (remaining)", "Tasks")):
            with self.subTest(heading=heading):
                text = f"# T\n\n{heading}\n\n- [ ] open\n"
                self.assertEqual(cdc.near_miss_headings(text, name), [heading.rstrip()])
                self.assertFalse(cdc.has_section(text, name))
                self.assertEqual(
                    [m.group("text") for m in cdc.section_items(text, name, include_near_miss=True)],
                    ["open"])

    def test_not_near_misses(self):
        for heading in ("## Tasks", "### Tasks", "##Tasks", "    ## Tasks", "## Task", "> ## Tasks"):
            with self.subTest(heading=heading):
                self.assertEqual(cdc.near_miss_headings(f"{heading}\n", "Tasks"), [])


def _write_wave(root: Path, change_doc: str, *, change_block: str | None = None) -> tuple[Path, str]:
    wave_dir = root / "wave"
    wave_dir.mkdir(parents=True, exist_ok=True)
    # Record markers come from the loaded vocabulary profile, so the fixture
    # holds under a second profile too.
    block = change_block if change_block is not None else (
        f"{_vocab.MEMBER_ID_LABEL}: `1abcd-bug sample`\n{_vocab.MEMBER_STATUS_LABEL}: `implementing`\n"
    )
    wave_text = f"{_vocab.RECORD_TITLE}\n\n{_vocab.MEMBER_HEADING}\n\n{block}\n## Participants\n\n- x\n"
    (wave_dir / _vocab.RECORD_FILENAME).write_text(wave_text, encoding="utf-8")
    (wave_dir / "1abcd-bug sample.md").write_text(change_doc, encoding="utf-8")
    return wave_dir / _vocab.RECORD_FILENAME, wave_text


_PRIORITY = ("## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n"
             "| AC-1 | required | r |\n| AC-2 | required | r |\n")


def _doc(ac_body: str = "- [x] AC-1: a\n", tasks_body: str = "- [x] t\n", priority: str = _PRIORITY) -> str:
    return (f"# Sample\n\n## Acceptance Criteria\n\n{ac_body}\n## Tasks\n\n{tasks_body}\n"
            f"{priority}\n## Progress Log\n\nx\n")


class CloseGateShapeTests(unittest.TestCase):
    """Wave 1zls7 (1zltr) AC-1, AC-2, AC-4 and Requirement 7b."""

    def setUp(self):
        import lifecycle_gate_support
        self.gates = lifecycle_gate_support
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def _collect(self, doc, **kwargs):
        wave_md, wave_text = _write_wave(self.root, doc, **kwargs)
        return [(f["item_type"], f["item_id"], f["item_text"])
                for f in self.gates._collect_silent_unchecked_items_for_close(wave_md, wave_text)]

    def test_blockquoted_task_is_open(self):
        self.assertEqual(self._collect(_doc(tasks_body="- [x] t\n> - [ ] write the test\n")),
                         [("task", "", "write the test")])

    def test_dash_mark_task_is_open_and_shows_its_mark(self):
        self.assertEqual(self._collect(_doc(tasks_body="- [x] t\n- [-] step\n")),
                         [("task", "", "[-] step")])

    def test_slash_mark_required_criterion_is_open(self):
        self.assertEqual(self._collect(_doc(ac_body="- [x] AC-1: a\n- [/] AC-2: half done\n")),
                         [("AC", "AC-2", "[/] AC-2: half done")])

    def test_task_after_a_fence_holding_a_heading_is_open(self):
        tasks = "- [x] t\n```sh\n$ cat notes\n## Not a heading\n```\n- [ ] after the fence\n"
        self.assertEqual(self._collect(_doc(tasks_body=tasks)),
                         [("task", "", "after the fence")])

    def test_fenced_example_item_is_not_reported(self):
        tasks = "- [x] t\n```md\n- [ ] example\n```\n"
        self.assertEqual(self._collect(_doc(tasks_body=tasks)), [])

    def test_unterminated_fence_hides_nothing(self):
        tasks = "- [x] t\n```\n- [ ] x\n"
        self.assertEqual(self._collect(_doc(tasks_body=tasks)), [("task", "", "x")])

    def test_quoted_fence_does_not_run_on(self):
        # Red-team R7: the unquoted item ends the quoted fence before the later
        # quoted closer, so the fence never closes and hides nothing.
        for closer in ("```", "> ```"):
            with self.subTest(closer=closer):
                tasks = f"- [x] t\n> ```\n> note\n- [ ] after the quote\n{closer}\n"
                self.assertEqual(self._collect(_doc(tasks_body=tasks)), [("task", "", "after the quote")])

    def test_near_miss_heading_items_are_open(self):
        doc = _doc().replace("## Tasks\n", "## Tasks\n\n- [x] t\n\n##  tasks\n", 1)
        doc = doc.replace("\n- [x] t\n\n## AC Priority", "\n- [ ] hidden\n\n## AC Priority", 1)
        self.assertIn(("task", "", "hidden"), self._collect(doc))

    def test_fenced_priority_row_does_not_exempt(self):
        priority = ("## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n"
                    "| AC-1 | required | r |\n```\n| AC-2 | not-this-scope | example |\n```\n")
        found = self._collect(_doc(ac_body="- [x] AC-1: a\n- [ ] AC-2: open\n", priority=priority))
        self.assertEqual(found, [("AC", "AC-2", "AC-2: open")])

    def test_indented_change_block_cannot_escape(self):
        # Requirement 7b (red-team R4).
        block = (f"  {_vocab.MEMBER_ID_LABEL}: `1abcd-bug sample`\n"
                 f"  {_vocab.MEMBER_STATUS_LABEL}: `implementing`\n")
        self.assertEqual(self._collect(_doc(ac_body="- [ ] AC-1: open\n"), change_block=block),
                         [("AC", "AC-1", "AC-1: open")])

    def test_column_zero_id_outside_the_lint_shape_is_still_checked(self):
        # Delivery review N2a: a column-0 id the lint record parser does not
        # accept cannot escape the gate. Wave 1zxo0 (1zxns): it fails the
        # allow-list, so it blocks as a `change id` finding (empty change id,
        # reason class) and no path is built from it.
        block = (f"{_vocab.MEMBER_ID_LABEL}: `1abcd-bug sample`\n{_vocab.MEMBER_STATUS_LABEL}: `implementing`\n\n"
                 f"{_vocab.MEMBER_ID_LABEL}: `odd sample`\n{_vocab.MEMBER_STATUS_LABEL}: `implementing`\n")
        wave_md, wave_text = _write_wave(self.root, _doc(), change_block=block)
        (wave_md.parent / "odd sample.md").write_text(_doc(ac_body="- [ ] AC-1: open\n"), encoding="utf-8")
        from wave_lint_lib.wave_validators import _parse_work_records
        self.assertNotIn("odd sample", [r.record_id for r in _parse_work_records(wave_text, "")])
        found = [(f["change_id"], f["item_id"])
                 for f in self.gates._collect_silent_unchecked_items_for_close(wave_md, wave_text)]
        self.assertEqual(found, [("", "shape")])

    def test_valid_document_findings_are_unchanged(self):
        # AC-4: canonical marks, `-` markers, no fences: the findings the
        # pre-change gate produced for the same document (recorded 2026-10-02).
        doc = _doc(ac_body="- [x] AC-1: a\n- [ ] AC-2: open\n- [~] AC-3: dropped *operator*\n",
                   tasks_body="- [X] done\n- [ ] remaining\n  continued\n- [~] skipped\n")
        self.assertEqual(self._collect(doc),
                         [("AC", "AC-2", "AC-2: open"), ("task", "", "remaining")])


class LintAndPrepareMarkTests(unittest.TestCase):
    """Wave 1zls7 (1zltr) AC-3 and AC-4."""

    def setUp(self):
        import lifecycle_gate_support
        from wave_lint_lib import wave_validators
        self.gates = lifecycle_gate_support
        self.lint = wave_validators

    def _lint(self, doc):
        return [f for rule in (self.lint._check_ac_priority_alignment, self.lint._check_checkbox_ac_syntax,
                               self.lint._check_checkbox_task_syntax, self.lint._check_checklist_list_markers,
                               self.lint._check_tilde_required_ac_has_inline_note)
                for f in rule(doc, "x.md")]

    def test_unusual_marks_are_reported_by_lint_and_prepare(self):
        doc = _doc(ac_body="- [x] AC-1: a\n- [/] AC-2: half\n", tasks_body="- [x] t\n- [-] step\n")
        failures = self._lint(doc)
        self.assertEqual(len(failures), 2, failures)
        joined = "\n".join(failures)
        for expected in ("x.md: `## Acceptance Criteria` checklist item `AC-2: half` uses the mark `[/]`",
                         "x.md: `## Tasks` checklist item `step` uses the mark `[-]`",
                         "use `[ ]`, `[x]` or `[~]`"):
            self.assertIn(expected, joined)
        self.assertNotIn("plain bullet format", joined)
        self.assertEqual(self.gates._noncanonical_checklist_items(doc), ["- [/] AC-2: half", "- [-] step"])

    def test_valid_document_lints_clean(self):
        doc = _doc(ac_body="- [x] AC-1: a\n- [ ] AC-2: open\n", tasks_body="- [X] done\n- [~] skipped\n")
        self.assertEqual(self._lint(doc), [])
        self.assertEqual(self.gates._noncanonical_checklist_items(doc), [])

    def test_fenced_example_items_are_not_linted(self):
        tasks = "- [x] t\n```md\n- plain example\n* [-] star example\n## Fake\n```\n"
        self.assertEqual(self._lint(_doc(ac_body="- [x] AC-1: a\n- [x] AC-2: b\n", tasks_body=tasks)), [])

    def test_fenced_criteria_do_not_count_toward_the_priority_table(self):
        ac = "- [x] AC-1: a\n- [x] AC-2: b\n```md\n- [ ] AC-3: example\n```\n"
        self.assertEqual(self._lint(_doc(ac_body=ac)), [])

    def test_blockquoted_criterion_counts_toward_the_priority_table(self):
        ac = "- [x] AC-1: a\n> - [x] AC-2: b\n> - [x] AC-3: c\n"
        failures = self._lint(_doc(ac_body=ac))
        self.assertTrue(any("found 3 AC bullets and 2 AC priority rows" in f for f in failures), failures)

    def test_blockquoted_required_tilde_needs_its_note(self):
        failures = self._lint(_doc(ac_body="- [x] AC-1: a\n> - [~] AC-2: no\n"))
        self.assertTrue(any("`[~]` required AC `AC-2`" in f for f in failures), failures)

    def test_every_criteria_section_counts_toward_the_priority_table(self):
        """Wave 1zls7 (1zodv, AC-5): the census shape. A document carrying a
        second, template-leftover ``## Acceptance Criteria`` section is read
        as the close gate reads it, every section with the heading, so the
        alignment count covers both (HEAD read only the last section)."""
        priority = ("## AC Priority\n\n| AC | Priority | Rationale |\n| --- | --- | --- |\n"
                    "| AC-1 | required | r |\n| AC-2 | required | r |\n| AC-3 | required | r |\n")
        doc = _doc(ac_body="- [x] AC-1: a\n- [x] AC-2: b\n- [x] AC-3: c\n", priority=priority)
        doc = doc.replace("## AC Priority", "## Acceptance Criteria\n\n- [x] AC-1: [Testable outcome]\n"
                          "- [x] AC-2: ...\n\n## AC Priority", 1)
        failures = self.lint._check_ac_priority_alignment(doc, "x.md")
        self.assertEqual(failures, [
            "x.md: AC Priority table must have one row per Acceptance Criteria bullet "
            "(found 5 AC bullets and 3 AC priority rows); unknown ACs are not allowed"])
        # The close gate reads the same two sections: an open item in the
        # first one blocks close.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        wave_md, wave_text = _write_wave(Path(tmp.name), doc.replace("- [x] AC-3: c", "- [ ] AC-3: c", 1))
        found = [(f["item_type"], f["item_id"])
                 for f in self.gates._collect_silent_unchecked_items_for_close(wave_md, wave_text)]
        self.assertEqual(found, [("AC", "AC-3")])


if __name__ == "__main__":
    unittest.main()

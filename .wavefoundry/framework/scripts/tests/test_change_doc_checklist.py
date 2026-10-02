"""Unit tests for the shared change-document checklist parser (wave 1zime, 1zimq)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import change_doc_checklist as cdc  # noqa: E402


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
        for line in ("- step", "-[ ] glued", "1234567890. [ ] ten digits", "a. [ ] letter",
                     "- [?] other mark", "text - [ ] mid-line"):
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


if __name__ == "__main__":
    unittest.main()

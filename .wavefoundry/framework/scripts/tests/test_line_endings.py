"""Wave 244in (change 244fj) AC-8 and AC-2: the shared line-ending rule.

Existing lines keep their own ending byte for byte; inserted or replaced lines
take the file's majority ending (ties go to CRLF); a file with no terminated
line gives LF.  The expected values are written out literally, not computed
through the helper.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import line_endings as le  # noqa: E402


class ToLfTests(unittest.TestCase):
    def test_crlf_pairs_become_lf_and_a_lone_cr_is_content(self):
        self.assertEqual(le.to_lf("a\r\nb\rc\n\r\n"), "a\nb\rc\n\n")
        self.assertEqual(le.to_lf("x\r\r\n"), "x\r\n")


class MajorityTests(unittest.TestCase):
    def test_majority_cases(self):
        cases = {
            "a\nb\n": "\n",
            "a\r\nb\r\n": "\r\n",
            "a\r\nb\n": "\r\n",  # a tie goes to CRLF
            "a\r\nb\nc\n": "\n",  # mixed, LF majority
            "a\r\nb\r\nc\n": "\r\n",  # mixed, CRLF majority
            "": "\n",  # no terminated line
            "no ending": "\n",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(le.majority(text), expected)


class MergeTests(unittest.TestCase):
    def test_unchanged_text_round_trips_byte_for_byte(self):
        for original in ("a\nb\n", "a\r\nb\r\n", "a\r\nb\nc\r\n", "a\r\nb", "", "x"):
            with self.subTest(original=original):
                self.assertEqual(le.merge(original, le.to_lf(original)), original)

    def test_replaced_line_takes_the_majority_and_others_keep_theirs(self):
        self.assertEqual(le.merge("a\r\nb\nc\r\n", "a\nB\nc\n"), "a\r\nB\r\nc\r\n")
        self.assertEqual(le.merge("a\nb\r\nc\n", "a\nB\nc\n"), "a\nB\nc\n")

    def test_inserted_lines_take_the_majority(self):
        self.assertEqual(le.merge("a\r\nb\r\nc\n", "a\nnew\nb\nc\n"), "a\r\nnew\r\nb\r\nc\n")
        self.assertEqual(le.merge("a\nb\nc\r\n", "a\nb\nnew\nc\n"), "a\nb\nnew\nc\r\n")

    def test_deleted_lines_leave_the_others_untouched(self):
        self.assertEqual(le.merge("a\r\nb\nc\r\n", "a\nc\n"), "a\r\nc\r\n")

    def test_missing_final_ending(self):
        # An unterminated last line stays unterminated.
        self.assertEqual(le.merge("a\r\nb", "a\nB"), "a\r\nB")
        # An unterminated line that gains a successor takes the majority ending.
        self.assertEqual(le.merge("a\r\nb", "a\nb\nc"), "a\r\nb\r\nc")
        self.assertEqual(le.merge("a\r\nb", "a\nb\nc\n"), "a\r\nb\r\nc\r\n")

    def test_empty_file_gives_lf(self):
        self.assertEqual(le.merge("", "a\nb\n"), "a\nb\n")
        self.assertEqual(le.merge("x", "x\ny\n"), "x\ny\n")

    def test_double_cr_input_round_trips_without_new_corruption(self):
        original = "x\r\r\ny\r\n"
        self.assertEqual(le.merge(original, le.to_lf(original)), original)
        edited = le.merge(original, "x\r\nY\n")
        self.assertEqual(edited, "x\r\r\nY\r\n")
        self.assertEqual(edited.count("\r\r\n"), 1)
        # A new line never gains a second carriage return.
        self.assertNotIn("\r\r\n", le.merge("a\r\n", "a\nb\n"))

    def test_encode_does_not_translate(self):
        self.assertEqual(le.encode("a\r\nb\n"), b"a\r\nb\n")


class MixedFileRuleTests(unittest.TestCase):
    """AC-2 at the helper: the coordinator's mixed-file rule."""

    def test_one_stray_crlf_line_in_200_lf_lines(self):
        lines = [f"line {index}\n" for index in range(200)]
        lines.insert(100, "stray\r\n")
        original = "".join(lines)
        new_lf = le.to_lf(original).replace("line 5\n", "line five\n")
        merged = le.merge(original, new_lf)
        changed = [
            (before, after)
            for before, after in zip(original.splitlines(keepends=True), merged.splitlines(keepends=True))
            if before != after
        ]
        self.assertEqual(changed, [("line 5\n", "line five\n")])
        self.assertIn("stray\r\n", merged)
        self.assertEqual(len(merged.splitlines()), 201)

    def test_crlf_majority_gives_an_inserted_line_crlf(self):
        self.assertEqual(le.merge("a\r\nb\r\nc\n", "a\nb\nc\nd\n"), "a\r\nb\r\nc\nd\r\n")

    def test_tie_gives_crlf(self):
        self.assertEqual(le.merge("a\r\nb\n", "a\nb\nc\n"), "a\r\nb\nc\r\n")

    def test_no_terminated_line_gives_lf(self):
        self.assertEqual(le.merge("a", "a\nb\n"), "a\nb\n")


class StdlibOnlyTests(unittest.TestCase):
    """``upgrade_extensions.py`` execs this module from a pack without
    ``sys.modules`` registration, so it must import only the standard library."""

    def test_imports_are_stdlib_only_and_exec_without_registration(self):
        import ast
        import types

        source = (SCRIPTS / "line_endings.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertLessEqual(imported, {"__future__", "difflib", "pathlib"})
        module = types.ModuleType("_incoming_line_endings_probe")
        exec(compile(source, "line_endings.py", "exec"), module.__dict__)
        self.assertNotIn("_incoming_line_endings_probe", sys.modules)
        self.assertEqual(module.merge("a\r\n", "a\nb\n"), "a\r\nb\r\n")


if __name__ == "__main__":
    unittest.main()

"""Pinned Go-oracle comparisons and adversarial limits for offline Expr."""
from __future__ import annotations

import gzip
import json
import sys
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wave_lint_lib import expr_filter as expr

FIXTURES = Path(__file__).parent / "fixtures" / "betterleaks"


class TestExprOracle(unittest.TestCase):
    def test_upstream_global_filter_and_prefilter_oracle(self):
        # Pure upstream expectations stay separate from Wavefoundry's explicit
        # whole-value placeholder correction in the shipped global filter.
        config = tomllib.loads((FIXTURES / "upstream.toml").read_text())
        programs = {kind: expr.compile_filter(config[kind], prefilter=kind == "prefilter")
                    for kind in ("filter", "prefilter")}
        rows = [json.loads(line) for line in (FIXTURES / "global-oracle.jsonl").read_text().splitlines()]
        self.assertEqual(118, len(rows))
        self.assertEqual(68, sum(row["kind"] == "filter" for row in rows))
        for row in rows:
            with self.subTest(kind=row["kind"], group=row["group"], value=row["input"]):
                self.assertEqual("", row["error"])
                finding = {"secret": row["input"]} if row["kind"] == "filter" else {}
                attributes = {"path": row["input"]} if row["kind"] == "prefilter" else {}
                result = expr.evaluate_filter(programs[row["kind"]], finding, attributes)
                self.assertEqual(row["actual_skip"], result)
                self.assertEqual(row["expected_skip"], result)

    def test_all_upstream_programs_against_go(self):
        corpus = json.loads(gzip.decompress((FIXTURES / "expr-oracle.json.gz").read_bytes()))
        self.assertEqual(len(corpus["cases"]), 1720)
        self.assertEqual(len(corpus["sources"]), 51)
        programs = {key: expr.compile_filter(row["source"], prefilter=row["prefilter"]) for key, row in corpus["sources"].items()}
        for row in corpus["cases"]:
            with self.subTest(case=row["id"]):
                attributes = dict(row["attributes"])
                if row["expected_error"]:
                    with self.assertRaises(expr.EvaluationError):
                        expr.evaluate_filter(programs[row["source"]], row["finding"], attributes)
                else:
                    result = expr.evaluate_filter(programs[row["source"]], row["finding"], attributes)
                    self.assertEqual(result, row["expected_skip"])
                    self.assertEqual(attributes, row["expected_attributes"])

    def test_utf8_slicing_and_len_have_different_units(self):
        finding = {"secret": "é", "fragment_raw": "éABC"}
        self.assertTrue(expr.evaluate_filter(expr.compile_filter('len(finding["secret"]) == 1'), finding, {}))
        self.assertTrue(expr.evaluate_filter(expr.compile_filter('finding["fragment_raw"][2:4] == "AB"'), finding, {}))
        self.assertTrue(expr.evaluate_filter(expr.compile_filter('finding["fragment_raw"][0:1] == fromBase64("ww==")'), finding, {}))
        self.assertTrue(expr.evaluate_filter(expr.compile_filter('"abc"[8:10] == ""'), {}, {}))

    def test_short_circuit_and_scoped_predicate(self):
        self.assertTrue(expr.evaluate_filter(expr.compile_filter('true || fromBase64("!") == ""'), {}, {}))
        self.assertFalse(expr.evaluate_filter(expr.compile_filter('false && fromBase64("!") == ""'), {}, {}))
        source = 'let suffix = "!"; join(map(split("a,b", ","), { let value = # + suffix; value }), "/") == "a!/b!"'
        self.assertTrue(expr.evaluate_filter(expr.compile_filter(source), {}, {}))

    def test_base64_errors_are_not_false(self):
        with self.assertRaises(expr.EvaluationError):
            expr.evaluate_filter(expr.compile_filter('fromBase64("Y Q==") == "a"'), {}, {})
        self.assertTrue(expr.evaluate_filter(expr.compile_filter('fromBase64("YQ==\\n") == "a"'), {}, {}))

    def test_confidence_is_mutated(self):
        attrs = {}
        self.assertTrue(expr.evaluate_filter(expr.compile_filter('let level = setConfidence("high"); level == "high"'), {}, attrs))
        self.assertEqual(attrs, {"confidence": "high"})


class TestRegexProfile(unittest.TestCase):
    def test_go_oracle_capture_values_and_utf8_byte_spans(self):
        rows = [json.loads(line) for line in (FIXTURES / "regex-controls.jsonl").read_text().splitlines()]
        self.assertEqual(11, len(rows))
        for row in rows:
            with self.subTest(case=row["name"]):
                self.assertEqual("", row["error"])
                pattern = expr.compile_regex(row["pattern"])
                matches = list(pattern.finditer(row["input"]))
                captures = [[match.group(i) or "" for i in range(pattern.groups + 1)] for match in matches]
                spans = [[-1 if offset < 0 else len(row["input"][:offset].encode("utf-8"))
                          for i in range(pattern.groups + 1) for offset in match.span(i)]
                         for match in matches]
                self.assertEqual(row["captures"] or [], captures)
                self.assertEqual(row["spans"] or [], spans)

    def test_go_controls(self):
        cases = [
            (r"[[:alnum:]]+", "éA0", ["A0"]),
            (r"\w+", "é_A0", ["_A0"]),
            (r"\d+", "١1", ["1"]),
            (r"\s+", "\u00a0 \t", [" \t"]),
            ("token$", "token\n", []),
            ("(?m)token$", "token\n", ["token"]),
            ("(a(?i)b|c)", "C", ["C"]),
            ("((?i)a)b", "Ab AB", ["Ab"]),
            ("(?i)(a(?-i)b|c)", "AB Ab C c", ["Ab", "c"]),
            (r"\btoken\b", "étokené", ["token"]),
            (r"[\s\S]+", "a\n🔐", ["a\n🔐"]),
        ]
        for pattern, text, expected in cases:
            with self.subTest(pattern=pattern):
                self.assertEqual([m.group() for m in expr.compile_regex(pattern).finditer(text)], expected)

    def test_unicode_simple_fold_does_not_enable_turkish_i(self):
        self.assertEqual(expr.compile_regex("(?i)[a-z]+").findall("İıKKsſ"), ["KKsſ"])
        self.assertEqual(expr.compile_regex("(?i)k|s|i").findall("Kſİıi"), ["K", "ſ", "i"])
        # Go regexp oracle: fold before complementing a shorthand inside [].
        self.assertEqual(expr.compile_regex(r"(?i)[\W]+").findall("éKKsſİı!"), ["é", "İı!"])
        self.assertEqual(expr.compile_regex(r"(?i)[\Wk]+").findall("éKKsſİı!"), ["éKK", "İı!"])

    def test_captures_and_end_anchor(self):
        match = expr.compile_regex(r"(?P<one>a)?(?P<two>b)\z").search("b")
        self.assertEqual(match.groups(), (None, "b"))
        self.assertIsNone(expr.compile_regex(r"b\z").search("b\n"))


class TestExprLimits(unittest.TestCase):
    def test_source_tokens_and_nesting_are_bounded(self):
        for source in ('"' + 'x' * 32768 + '"', 'false || ' * 5000 + 'true', '(' * 70 + 'true' + ')' * 70):
            with self.subTest(length=len(source)), self.assertRaises(expr.CompileError):
                expr.compile_filter(source)

    def test_unknown_programs_are_rejected_before_input(self):
        for source in ('http.get("https://invalid")', 'env.get("HOME")', 'finding["unknown"] == ""', 'finding.unknown == ""', '# == "x"', 'setConfidence()', 'let finding = "x"; true', 'true garbage', 'matchesAny("x" ["x"])', 'false && matchesAny("x", ["["])'):
            with self.subTest(source=source), self.assertRaises(expr.CompileError):
                expr.compile_filter(source)
        with self.assertRaises(expr.CompileError):
            expr.compile_filter('entropy("abc") > 1', prefilter=True)

    def test_budget_exhaustion_is_an_error(self):
        program = expr.compile_filter('let x = "a"; x == "a"')
        with patch.object(expr, "MAX_OPERATIONS", 2), self.assertRaises(expr.EvaluationError):
            expr.evaluate_filter(program, {}, {})
        with self.assertRaises(expr.EvaluationError):
            expr.evaluate_filter(expr.compile_filter('repeat("x", 1000001) == ""'), {}, {})
        with patch.object(expr, "MAX_VALUE_BYTES", 8), self.assertRaises(expr.EvaluationError):
            expr.evaluate_filter(expr.compile_filter('join(["abcdefgh", "abcdefgh"]) == ""'), {}, {})

    def test_result_must_be_boolean(self):
        with self.assertRaises(expr.EvaluationError):
            expr.evaluate_filter(expr.compile_filter('"truthy"'), {}, {})


if __name__ == "__main__":
    unittest.main()

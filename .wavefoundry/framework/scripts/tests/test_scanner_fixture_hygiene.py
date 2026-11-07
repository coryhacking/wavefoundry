"""Keep example-value hygiene separate from detection and filter behavior."""
from pathlib import Path
import random
import re
import string
import sys
import tomllib
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from wave_lint_lib import cel_filter, expr_filter
from wave_lint_lib.betterleaks_engine import BetterleaksEngine


class ExampleValueRepresentationTests(unittest.TestCase):
    def configurations(self):
        fixtures = SCRIPTS / "tests" / "fixtures" / "betterleaks"
        return (SCRIPTS.parent / "scan-rules.toml",
                fixtures / "upstream.toml", fixtures / "baseline.toml")

    def test_examples_preserve_filter_semantics_and_positive_detection(self):
        prefix = "AI" + "za"
        rng = random.Random(2202)
        positive = prefix + "".join(rng.choice(string.ascii_letters + string.digits + "_-")
                                  for _ in range(35))
        for path in self.configurations():
            with self.subTest(configuration=path.name):
                config = tomllib.loads(path.read_text())
                rule = next(r for r in config["rules"] if r["id"] == "gcp-api-key")
                candidate = rule["filter"]
                original = candidate.replace("[A]Iza", prefix)
                examples = re.findall(prefix + r"[\w-]{35}", original)
                self.assertEqual(len(examples), 16)
                self.assertNotRegex(candidate, prefix + r"[\w-]{35}")
                if path.name == "baseline.toml":
                    def evaluate(source, secret):
                        return cel_filter.eval_filter(source, secret, secret, "example.py")
                else:
                    def evaluate(source, secret):
                        return expr_filter.evaluate_filter(
                            expr_filter.compile_filter(source),
                            {"secret": secret, "match": secret, "line": secret},
                            {"path": "example.py"})
                for value in examples + [positive]:
                    self.assertEqual(evaluate(candidate, value), evaluate(original, value))
                self.assertTrue(all(evaluate(candidate, value) for value in examples))
                self.assertFalse(evaluate(candidate, positive))
                if path.name != "baseline.toml":
                    engine = BetterleaksEngine({"rules": [rule]})
                    for value in examples:
                        result = engine.scan('key = "' + value + '"', "example.py")
                        self.assertTrue(result["complete"])
                        self.assertEqual(result["findings"], [])
                    result = engine.scan('key = "' + positive + '"', "example.py")
                    self.assertTrue(result["complete"])
                    self.assertEqual([f["rule_id"] for f in result["findings"]], ["gcp-api-key"])


if __name__ == "__main__":
    unittest.main()

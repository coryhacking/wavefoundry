"""Tests for the hermetic memory-retrieval eval baseline (wave 1sufo / change 1sufm).

The harness itself is the deliverable; these tests run it against its own
synthetic corpus and assert the policy invariants hold and the recorded baseline
is the one the deferred fusion change must beat. Measurement-only: no product
ranking code is touched by this change.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_SCRIPTS / "tests" / "eval"))
import run_memory_eval as evalh  # noqa: E402


class MemoryEvalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "repo"
        (self.root / "docs" / "agents").mkdir(parents=True)

    def test_fixture_covers_all_five_categories(self):
        report = evalh.run(self.root)
        cats = {c["category"] for c in report["cases"]}
        self.assertEqual(
            cats, {"exact_target", "paraphrase", "no_index", "decay", "supersession"})

    def test_all_policy_invariants_pass(self):
        report = evalh.run(self.root)
        ov = report["overall"]
        self.assertEqual(ov["invariants_total"], 5)
        self.assertEqual(ov["invariants_passed"], ov["invariants_total"],
                         [c for c in report["cases"] if not c["invariant_pass"]])

    def test_recall_and_mrr_reported_per_case(self):
        report = evalh.run(self.root)
        for c in report["cases"]:
            self.assertIn("recall_at_k", c)
            self.assertIn("mrr", c)
            self.assertGreaterEqual(c["recall_at_k"], 0.0)

    def test_recorded_baseline_beats_semantic_and_lexical_only(self):
        # The recorded baseline the fusion change (1sufn) must beat: the fixed
        # policy keeps the high-trust record on top of the paraphrase case,
        # where pure-semantic (pre-1svuj) and strict lexical both miss it.
        report = evalh.run(self.root)
        comp = report["comparison"]
        self.assertEqual(comp["baseline"]["recall_at_1"], 1.0)
        self.assertEqual(comp["semantic_only"]["recall_at_1"], 0.0)
        self.assertEqual(comp["lexical_only"]["recall_at_1"], 0.0)

    def test_hermetic_reproducible(self):
        # Two independent runs over freshly-built corpora yield the same report.
        first = evalh.run(self.root)
        with tempfile.TemporaryDirectory() as tmp2:
            root2 = Path(tmp2) / "repo"
            (root2 / "docs" / "agents").mkdir(parents=True)
            second = evalh.run(root2)
        self.assertEqual(first["overall"], second["overall"])
        self.assertEqual(first["comparison"], second["comparison"])


if __name__ == "__main__":
    unittest.main()

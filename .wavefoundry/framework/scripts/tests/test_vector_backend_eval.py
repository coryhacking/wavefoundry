"""Adversarial checks for the development-only vector comparison oracle."""
import unittest
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import numpy as np
    import vector_backend_eval as subject
except ImportError:
    np = subject = None


@unittest.skipIf(np is None, "optional evaluation dependency numpy unavailable")
class VectorOracleTests(unittest.TestCase):
    @unittest.skipIf(sys.platform == "win32", "resource probe currently supports POSIX hosts")
    def test_resource_probe_refuses_truncated_metadata_even_if_stored_subset_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()
            vectors = np.ones((2, 2), dtype=np.float32)
            np.save(source / "vectors.npy", vectors)
            (source / "rows.jsonl").write_text(json.dumps({"rid": 0, "payload": "{}"}) + "\n")
            store = Mock()
            store.snapshot.return_value = {0: ("{}", vectors[0].tobytes())}
            work = Path(directory) / "work"
            args = SimpleNamespace(backend="sqlite-scalar", resource_source=str(source), work_dir=str(work))
            with patch.object(subject, "Store", return_value=store):
                with self.assertRaisesRegex(AssertionError, "row/vector count mismatch"):
                    subject.run_build_resources(args)
            self.assertEqual("error", json.loads((work / "result.json").read_text())["status"])

    def test_exact_modes_bypass_an_inexact_index_and_flat_avoids_building_it(self):
        # An intentionally wrong ANN neighbor must not contaminate an exact lane.
        for backend in ("lance", "lance-exact", "lance-flat"):
            with self.subTest(backend=backend):
                store = subject.Store.__new__(subject.Store)
                store.backend = backend
                query = Mock()
                query.metric.return_value = query
                query.limit.return_value = query
                query.refine_factor.return_value = query
                query.where.return_value = query
                exact = Mock()
                exact.where.return_value = exact
                query.bypass_vector_index.return_value = exact
                query.to_list.return_value = [{"rid": 1, "_distance": 1.0, "payload": "{}"}]
                exact.to_list.return_value = [{"rid": 0, "_distance": 0.0, "payload": "{}"}]
                store.table = Mock()
                store.table.search.return_value = query
                store.table.count_rows.return_value = 1000
                found = store.search(dict(vector=np.array([1., 0.]), k=1, sql="kind = 'code'"))
                check = subject.assess_rows(found, [(0, 0.)], eligible_indices=[0], expected_count=1)
                self.assertEqual(backend != "lance", check["ok"])
                store.maintain()
                self.assertEqual(backend != "lance-flat", store.table.create_index.called)

    def test_cosine_is_not_dot_product_and_filters_precede_top_k(self):
        vectors = [[100, 100], [1, 0], [0, 1], [-1, 0]]
        self.assertEqual([(2, 1.0), (3, 2.0)],
                         subject.exact_reference(vectors, [1, 0], [2, 3], 2))
        self.assertEqual(1, subject.exact_reference(vectors, [1, 0], range(4), 1)[0][0])

    def test_boundary_tie_permits_other_physical_row_but_not_missing_closer_row(self):
        oracle = [(0, 0.0), (1, 0.5), (2, 0.5), (3, 0.9)]
        def assess(rows):
            return subject.assess_rows(rows, oracle, eligible_indices=range(4), expected_count=2)
        self.assertTrue(assess([(0, 0), (2, .5)])["ok"])
        for mutant in ([(1, .5), (2, .5)], [(0, 0), (3, .9)],
                       [(0, 0), (0, 0)], [(0, 0)], [(0, 0), (2, float('nan'))]):
            with self.subTest(mutant=mutant):
                self.assertFalse(assess(mutant)["ok"])

    def test_eligible_membership_and_distance_are_independent_checks(self):
        result = subject.assess_rows([(8, 0)], [(8, 0)], eligible_indices=[9], expected_count=1)
        self.assertIn("filter_violation", result["errors"])
        result = subject.assess_rows([(9, .2)], [(9, .5)], eligible_indices=[9], expected_count=1)
        self.assertIn("distance_mismatch", result["errors"])

    def test_undefined_cosine_is_rejected(self):
        with self.assertRaises(ValueError):
            subject.exact_reference([[0, 0]], [1, 0], [0], 1)
        for vectors, query in (([[float('nan'), 1]], [1, 0]), ([[1, 0]], [float('inf'), 0])):
            with self.subTest(vectors=vectors, query=query), self.assertRaises(ValueError):
                subject.exact_reference(vectors, query, [0], 1)

    def test_empty_matches_do_not_become_unfiltered_search(self):
        self.assertEqual([], subject.exact_reference([[1, 0]], [1, 0], [], 10))
        self.assertFalse(subject.assess_rows([(0, 0)], [], eligible_indices=[], expected_count=0)["ok"])


if __name__ == "__main__":
    unittest.main()

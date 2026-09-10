"""Proof controls for the development-only public vector experiment."""
import unittest

from vector_public_eval import VerifiedTable


class MaterializationProofTests(unittest.TestCase):
    def test_empty_success_is_distinct_from_suppressed_failure(self):
        class Query:
            def limit(self, count):
                return self

            def to_list(self):
                return []

        class Table:
            def search(self, vector):
                return Query()

        proof = {}
        self.assertEqual(VerifiedTable(Table(), proof).search([1.0]).limit(3).to_list(), [])
        self.assertTrue(proof.get('materialized'))

        class BrokenQuery(Query):
            def to_list(self):
                raise RuntimeError('injected backend failure')

        class BrokenTable(Table):
            def search(self, vector):
                return BrokenQuery()

        proof = {}
        try:
            VerifiedTable(BrokenTable(), proof).search([1.0]).limit(3).to_list()
        except RuntimeError:
            pass  # The production caller intentionally suppresses this error.
        self.assertIsNot(proof.get('materialized'), True)

    def test_exact_proof_requires_executed_bypass(self):
        class Query:
            bypassed = False

            def bypass_vector_index(self):
                self.bypassed = True
                return self

            def to_list(self):
                if not self.bypassed:
                    raise AssertionError('ANN accidentally selected')
                return [{'id': 'exact'}]

        class Table:
            def search(self, vector):
                return Query()

        proof = {}
        self.assertEqual(VerifiedTable(Table(), proof, exact=True).search([1.0]).to_list(), [{'id': 'exact'}])
        self.assertTrue(proof['bypass_applied'])
        self.assertTrue(proof['materialized'])


if __name__ == '__main__':
    unittest.main()

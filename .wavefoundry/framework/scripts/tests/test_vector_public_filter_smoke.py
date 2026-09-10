"""Lightweight oracle controls; real storage smoke is explicitly CLI-only."""
import copy
import unittest

from vector_public_filter_smoke import assert_response, fixtures


class PublicFilterOracleTests(unittest.TestCase):
    def test_duplicate_ids_and_closer_distractors_are_real_fixture_conditions(self):
        rows, cases = fixtures()
        alpha = next(c for c in cases if c['name'] == 'selective-prefilter-and-duplicate-ids')
        selected = [r for r in rows if r['path'] in alpha['expected_paths']]
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]['id'], selected[1]['id'])
        self.assertGreater(sum(r['vector'][0] > selected[0]['vector'][0] for r in rows), 30)

    def test_oracle_rejects_prefilter_loss_wrong_score_and_dropped_duplicate(self):
        rows, cases = fixtures()
        case = cases[0]
        selected = [r for path in case['expected_paths'] for r in rows if r['path'] == path]
        response = {'status': 'ok', 'data': {'search_mode': 'semantic', 'fallback_reason': None,
                    'reranked': True, 'results': [dict(r, excerpt=r['text'], score=r['vector'][0]) for r in selected]}}
        assert_response(case, response, rows)
        for mutation in ('lost_filtered_rows', 'score', 'duplicate', 'nan', 'inf', 'negative_inf', 'string', 'bool'):
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(response)
                if mutation == 'lost_filtered_rows': bad['data']['results'] = []
                if mutation == 'score': bad['data']['results'][0]['score'] = 0.
                if mutation == 'duplicate': bad['data']['results'].pop()
                invalid_scores = {'nan': float('nan'), 'inf': float('inf'),
                                  'negative_inf': float('-inf'), 'string': '0.5', 'bool': True}
                if mutation in invalid_scores: bad['data']['results'][0]['score'] = invalid_scores[mutation]
                with self.assertRaises(AssertionError): assert_response(case, bad, rows)


if __name__ == '__main__':
    unittest.main()

"""Adversarial receipt controls for the development-only vector comparator."""
import copy
from pathlib import Path
import unittest

from vector_public_compare import TOOLS, compare, digest


def seal(attempt):
    report = attempt['report']
    report['run_id'] = digest({k: v for k, v in report.items() if k not in ('run_id', 'verdict')})


def fixture_pair(lane='latest-exact'):
    corpus = {'schema': 'fixture-v1', 'fixtures': [{'id': 'one', 'query': 'Find the public search entry',
               'applicable_tools': list(TOOLS)}]}
    cases = []
    for tool in TOOLS:
        cases.append({'fixture_id': 'one', 'tool': tool, 'applicable': True,
                      'repetitions': [{'repetition': i, 'elapsed_ms': 10.1,
                          'recall_at_10': 1., 'ndcg_at_10': 1., 'mrr_at_10': 1.,
                          'abstention_correct': None, 'question_type_correct': tool == 'code_ask',
                          'fallback_reason': None,
                          'search_mode': None if tool == 'code_lexical' else ('semantic' if tool == 'docs_search' else 'hybrid')}
                         for i in (1, 2, 3)]})
    report = {'schema': 'report-v1', 'fixture_schema': 'fixture-v1',
              'fixture_digest': digest(corpus), 'fixture_count': 1,
              'production_identity': {'digest': 'source', 'end_digest_verified': True},
              'evaluator_identity': {'digest': 'evaluator'},
              'index_identity': {'repository_root': str(Path('/tmp/vector-compare-fixture').resolve())},
              'generation': {'start': 1, 'end': 1, 'start_attempt_id': 'a', 'end_attempt_id': 'a',
                             'start_status': 'complete', 'end_status': 'complete',
                             'start_token': [1, 'a', 'complete'], 'end_token': [1, 'a', 'complete']},
              'corpus': {'non_empty': True, 'current_lance_fts_counts': {'docs': 100, 'code': 100},
                         'health': {'semantic_ready': True, 'readiness_overview': 'ready'}},
              'environment': {'offline': True, 'retrieval_toggles': {}, 'models': {'docs': 'unchanged'},
                              'python': '3.13.5', 'platform': 'test-platform', 'machine': 'arm64', 'processor': '',
                              'indexed_model_versions': {'docs': 'unchanged'}, 'execution_providers': ['CPUExecutionProvider'],
                              'reranker_provider': 'cpu', 'production_tuning': {'refine': 2},
                              'packages': {'lancedb': '0.33.0', 'fastembed': '0.8.0'}},
              'anchor_resolution': {}, 'cases': cases,
              'performance': {'protocol': {'warmups_per_tool': 1, 'measured_repetitions_per_applicable_pair': 3},
                              'warmups': {t: {'fixture_id': 'one'} for t in TOOLS}},
              'degraded_mode_probe': {'passed': True, 'disposable_store': True},
              'invalidation_reasons': [], 'verdict': 'baseline'}
    baseline = {'kind': 'experimental_public_path_overlay', 'production_certification': False,
                'status': 'completed', 'lane': 'baseline', 'root': '/tmp/vector-compare-fixture',
                'driver_sha256': 'd' * 64, 'packages': {'lancedb': '0.33.0', 'numpy': '2.5.1'}, 'report': report}
    candidate = copy.deepcopy(baseline)
    candidate['lane'] = lane
    candidate['packages']['lancedb'] = candidate['report']['environment']['packages']['lancedb'] = '0.38.0'
    if lane == 'sqlite-scalar':
        candidate['packages']['sqlite-vec'] = '0.1.9'
        candidate['sqlite_counts'] = {'docs': 100, 'code': 100}
    seal(baseline)
    seal(candidate)

    def calls(backend):
        result = []
        for category, tools in [('warmup', TOOLS), ('degraded', ('docs_search', 'code_search', 'code_ask')),
                                ('measured', [t for t in TOOLS for _ in range(3)])]:
            for tool in tools:
                semantic = category != 'degraded' and tool != 'code_lexical'
                events = [{'phase': 'lexical_fetch', 'ms': 1.}]
                if semantic:
                    events.append({'phase': 'dense_hydrated', 'backend': backend, 'table': 'docs', 'layer': 'project',
                                   'limit': 30, 'returned': 20, 'ms': 2.,
                                   'proof': {'materialized': True, 'bypass_applied': backend == 'latest-exact'}})
                    events.extend([{'phase': '_embed_query', 'ms': 1.},
                                   {'phase': '_agent_rerank' if tool == 'code_ask' else '_rerank', 'ms': 1.}])
                result.append({'tool': tool, 'query': corpus['fixtures'][0]['query'],
                               'root': '/tmp/vector-degraded-fixture' if category == 'degraded' else baseline['root'],
                               'status': 'ok', 'events': events, 'total_ms': 10., 'reranked': semantic,
                               'search_mode': 'lexical_fallback' if category == 'degraded' else
                                  (None if tool == 'code_lexical' else ('semantic' if tool == 'docs_search' else 'hybrid'))})
        return result
    return baseline, candidate, calls('baseline'), calls(lane), corpus


class PublicComparisonTests(unittest.TestCase):
    def test_equivalent_quality_and_explicit_package_delta_pass(self):
        result = compare(*fixture_pair())
        self.assertTrue(result['quality_non_regression'])
        self.assertEqual(len(result['candidate_measured_calls']), 12)
        self.assertEqual(result['timings']['code_ask']['candidate_uninstrumented_mean_ms'], 5.)
        self.assertFalse(result['production_certification'])

    def test_one_repetition_regression_cannot_hide_in_aggregates(self):
        args = fixture_pair()
        args[1]['report']['cases'][0]['repetitions'][1]['ndcg_at_10'] = .9
        seal(args[1])
        result = compare(*args)
        self.assertFalse(result['quality_non_regression'])
        self.assertEqual(result['regressions'][0]['repetition'], 2)

    def test_invalid_receipt_and_identity_changes_are_rejected(self):
        for mutation in ('unfinished', 'models', 'packages', 'generation', 'digest'):
            with self.subTest(mutation=mutation):
                args = fixture_pair()
                candidate = args[1]
                if mutation == 'unfinished': candidate['status'] = 'invalid'
                if mutation == 'models': candidate['report']['environment']['models']['docs'] = 'different'
                if mutation == 'packages': candidate['packages']['numpy'] = 'different'
                if mutation == 'generation': candidate['report']['generation']['end'] = 2
                if mutation == 'digest': candidate['report']['fixture_digest'] = 'wrong'
                seal(candidate)
                with self.assertRaises(ValueError): compare(*args)

    def test_missing_trace_proof_bypass_rerank_and_sequence_are_rejected(self):
        for mutation in ('proof', 'bypass', 'rerank', 'query', 'missing_call', 'wrong_backend', 'overlap'):
            with self.subTest(mutation=mutation):
                args = fixture_pair()
                call = args[3][7]
                dense = call['events'][1]
                if mutation == 'proof': dense['proof']['materialized'] = False
                if mutation == 'bypass': dense['proof']['bypass_applied'] = False
                if mutation == 'rerank': call['reranked'] = False
                if mutation == 'query': call['query'] = 'unrelated query'
                if mutation == 'missing_call': args[3].pop()
                if mutation == 'wrong_backend': dense['backend'] = 'baseline'
                if mutation == 'overlap': dense['ms'] = 11.
                with self.assertRaises(ValueError): compare(*args)

    def test_sqlite_requires_expected_extension_and_corpus_counts(self):
        args = fixture_pair('sqlite-scalar')
        self.assertTrue(compare(*args)['quality_non_regression'])
        args[1]['sqlite_counts']['docs'] -= 1
        with self.assertRaisesRegex(ValueError, 'count mismatch'): compare(*args)

    def test_semantic_calls_require_observed_embedding_and_matching_rerank_phase(self):
        for tool in ('docs_search', 'code_search', 'code_ask'):
            rerank = '_agent_rerank' if tool == 'code_ask' else '_rerank'
            for removed in ('_embed_query', rerank):
                for category in ('warmup', 'measured'):
                    with self.subTest(tool=tool, removed=removed, category=category):
                        args = fixture_pair()
                        candidates = args[3][:4] if category == 'warmup' else args[3][7:]
                        call = next(c for c in candidates if c['tool'] == tool)
                        call['events'] = [e for e in call['events'] if e['phase'] != removed]
                        # The other tool's rerank phase cannot stand in for the missing one.
                        if removed == rerank:
                            call['events'].append({'phase': '_rerank' if rerank == '_agent_rerank' else '_agent_rerank', 'ms': 1.})
                        with self.assertRaisesRegex(ValueError, 'phase proof'): compare(*args)

    def test_total_slowdown_is_descriptive_not_an_invented_gate(self):
        args = fixture_pair()
        for call in args[3]: call['total_ms'] *= 10
        result = compare(*args)
        self.assertTrue(result['quality_non_regression'])
        self.assertEqual(result['timings']['code_ask']['median_delta_percent'], 900.)


if __name__ == '__main__':
    unittest.main()

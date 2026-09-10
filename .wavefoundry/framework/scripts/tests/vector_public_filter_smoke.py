"""Opt-in, development-only public predicate smoke with real storage engines.

Models/loading are explicit fixtures, not a production readiness claim. Nothing
in retrieval_eval or its health/epoch checks is modified. The tiny exact corpus
checks filtering before top-k; it is not an ANN quality or timing benchmark.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys
import tempfile

from vector_public_eval import ScalarStore, VerifiedTable


def fixtures():
    # Forty closer distractors exceed production's minimum candidate window.
    declarations = [(f'noise-{i:02}', 'doc', 'noise', .001 * (i + 1), f'noise-{i}') for i in range(40)]
    declarations += [
        ('alpha', 'doc', 'alpha', .50, 'duplicate-public-id'),
        ('beta', 'seed', 'beta', .60, 'beta'),
        ('quote', 'doc', "owner's", .70, 'quote'),
        ('underscore', 'doc', 'under_score', .80, 'underscore'),
        ('wildcard-under', 'doc', 'underXscore', .90, 'wildcard-under'),
        ('percent', 'doc', 'percent%tag', 1.00, 'percent'),
        ('wildcard-percent', 'doc', 'percentZZtag', 1.10, 'wildcard-percent'),
        ('uppercase', 'doc', 'Alpha', 1.20, 'uppercase'),
        ('alpha-second', 'doc', 'alpha,shared', 1.30, 'duplicate-public-id'),
        ('shared-seed', 'seed', 'shared', 1.40, 'shared-seed'),
    ]
    rows = []
    for i, (name, kind, tags, angle, identity) in enumerate(declarations):
        rows.append({'id': identity, 'path': f'docs/{name}.md', 'kind': kind, 'language': '',
                     'tags': tags, 'lines': [i + 1, i + 1], 'section': name, 'text': f'Fixture {name}',
                     'chunk_hash': hashlib.sha256(name.encode()).hexdigest(),
                     'vector': [math.cos(angle), math.sin(angle)] + [0.] * 382})
    def case(name, expected, *, tags=None, kind='', limit=7):
        return {'name': name, 'tags': tags, 'kind': kind, 'limit': limit,
                'expected_paths': [f'docs/{item}.md' for item in expected]}
    cases = [
        case('selective-prefilter-and-duplicate-ids', ['alpha', 'alpha-second'], tags=['alpha']),
        case('or-tags', ['alpha', 'beta', 'alpha-second'], tags=['alpha', 'beta']),
        case('quoted-tag', ['quote'], tags=["owner's"]),
        case('underscore-is-like-wildcard', ['underscore', 'wildcard-under'], tags=['under_score']),
        case('percent-is-like-wildcard', ['percent', 'wildcard-percent'], tags=['percent%tag']),
        case('case-sensitive-tag', ['uppercase'], tags=['Alpha']),
        case('normalized-kind-and-tag', ['beta'], tags=['beta'], kind=' SEED '),
        case('kind-and-tag-empty-intersection', [], tags=['beta'], kind=' DOC '),
        case('empty-tag-match', [], tags=['absent']),
        case('kind-only', ['beta', 'shared-seed'], kind='seed'),
        case('top-one-after-filter', ['alpha'], tags=['alpha'], limit=1),
        case('public-lower-limit-clamp', ['alpha'], tags=['alpha'], limit=0),
        case('public-upper-limit-clamp', [f'noise-{i:02}' for i in range(20)], limit=100),
    ]
    return rows, cases


def assert_response(case, response, rows):
    if response.get('status') != 'ok':
        raise AssertionError(f"{case['name']}: public status is not ok")
    data = response.get('data') or {}
    if data.get('search_mode') != 'semantic' or data.get('fallback_reason') is not None or data.get('reranked') is not True:
        raise AssertionError(f"{case['name']}: unexpected fallback or skipped identity reranker")
    results = data['results']
    if [r['path'] for r in results] != case['expected_paths']:
        raise AssertionError(f"{case['name']}: expected {case['expected_paths']}, got {[r['path'] for r in results]}")
    by_path = {r['path']: r for r in rows}
    for result in results:
        source = by_path[result['path']]
        for key in ('kind', 'lines', 'section'):
            if result[key] != source[key]:
                raise AssertionError(f"{case['name']}: payload mismatch for {key}")
        score = result['score']
        if type(score) not in (int, float) or not math.isfinite(score):
            raise AssertionError(f"{case['name']}: cosine score must be a finite number")
        if result['excerpt'] != source['text'] or abs(score - source['vector'][0]) > 1e-5:
            raise AssertionError(f"{case['name']}: excerpt or cosine score mismatch")


def run(lane, scripts, work):
    import numpy as np
    import lancedb
    sys.path.insert(0, str(scripts))
    import server_impl as server
    expected_version = '0.33.0' if lane == 'baseline' else '0.38.0'
    if lancedb.__version__ != expected_version:
        raise RuntimeError(f'Expected LanceDB {expected_version}, got {lancedb.__version__}')
    if lane == 'sqlite-scalar' and importlib.metadata.version('sqlite-vec') != '0.1.9':
        raise RuntimeError('Expected sqlite-vec 0.1.9')
    rows, cases = fixtures()
    connection = lancedb.connect(work / 'lance')
    table = connection.create_table('docs', rows)
    scalar = ScalarStore(work / 'vectors.sqlite', {'docs': table}) if lane == 'sqlite-scalar' else None
    # Instance-only fixture seams; no global production method or epoch mutation.
    index = object.__new__(server.WaveIndex)
    index.root = work
    index._proj_docs_lance_table = table
    index._start_background_model_downloads_after_startup = lambda: None
    index._ensure_loaded = lambda: None
    index._indexer_constant = lambda name: 'synthetic-unit-vector-model'
    index._embed_query = lambda query, model: np.asarray([1.] + [0.] * 383, dtype=np.float32)
    index._get_reranker = lambda: 'explicit-identity-reranker'
    rerank_calls = []
    def identity_rerank(query, candidates, top_n):
        rerank_calls.append({'candidate_count': len(candidates), 'limit': top_n})
        return candidates[:top_n]
    index._rerank = identity_rerank
    original_dense = index._lance_search
    dense_calls = []
    def dense(actual_table, vector, limit, where=None, layer='project'):
        entry = {'where': where, 'limit': limit, 'backend': lane}
        if scalar is not None:
            result = scalar.search('docs', vector, limit, where)
            entry['sqlite_completed'] = True
        else:
            proof = {}
            result = original_dense(VerifiedTable(actual_table, proof, lane == 'latest-exact'), vector, limit, where, layer)
            if proof.get('materialized') is not True:
                raise RuntimeError('Storage failure was suppressed by production dense handler')
            entry['proof'] = proof
        entry['returned'] = len(result)
        dense_calls.append(entry)
        return result
    index._lance_search = dense
    results = []
    try:
        for case in cases:
            count, reranks = len(dense_calls), len(rerank_calls)
            response = server.docs_search_response(index, 'fixed predicate contract query',
                                                   kind=case['kind'], limit=case['limit'], tags=case['tags'],
                                                   epoch_state=None)
            assert_response(case, response, rows)
            if len(dense_calls) != count + 1 or len(rerank_calls) != reranks + 1:
                raise AssertionError('Expected exactly one real dense search and identity rerank')
            results.append({'case': case['name'], 'passed': True, 'dense': dense_calls[-1],
                            'rerank': rerank_calls[-1], 'paths': [r['path'] for r in response['data']['results']]})
        before = len(dense_calls)
        invalid = server.docs_search_response(index, 'query', kind='invalid-kind', epoch_state=None)
        if invalid['status'] != 'error' or len(dense_calls) != before:
            raise AssertionError('Invalid public kind reached storage')
        return {'kind': 'synthetic_public_filter_contract_smoke', 'lane': lane, 'passed': True,
                'production_certification': False, 'lancedb': lancedb.__version__,
                'sqlite_vec': importlib.metadata.version('sqlite-vec') if scalar is not None else None,
                'rows': len(rows), 'cases': results, 'invalid_kind_rejected_before_storage': True,
                'fixture_sha256': hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
                'limitations': ['Loading, embedding and reranking are explicit instance-only fixtures.',
                                'No completed epoch is forged; this does not exercise canonical evaluator readiness.',
                                'Tiny corpus has no ANN index; this proves predicates/public contracts, not ANN quality.',
                                'No timing or integration/recovery certification.']}
    finally:
        if scalar is not None:
            scalar.db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lane', choices=('baseline', 'latest-ann', 'latest-exact', 'sqlite-scalar'), required=True)
    parser.add_argument('--scripts', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--shared-site', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    os.environ['HF_HUB_OFFLINE'] = os.environ['TRANSFORMERS_OFFLINE'] = '1'
    if args.shared_site:
        sys.path.append(str(args.shared_site))
    with args.out.open('x') as out:
        result = {'lane': args.lane, 'passed': False, 'production_certification': False}
        try:
            with tempfile.TemporaryDirectory(prefix='wf-public-filter-') as temp:
                result = run(args.lane, args.scripts, Path(temp))
        except Exception as exc:
            result['error'] = repr(exc)
            raise
        finally:
            json.dump(result, out, indent=2)
            out.write('\n')
    print(f'{args.lane}: 13 filtered/public-limit cases and invalid-kind rejection passed')


if __name__ == '__main__':
    main()

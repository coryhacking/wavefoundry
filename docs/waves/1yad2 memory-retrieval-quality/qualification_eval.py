"""Explicit local qualification, never an MCP startup or automatic adoption path.

Run with the framework's provisioned Python. Only the named output artifact and
an owned scratch snapshot are written; the live index and memories are read-only.
"""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sqlite3
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.wavefoundry/framework/scripts'))
os.environ['WAVEFOUNDRY_EMBED_PROVIDER'] = 'cpu'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import memory_eval as ev
import server_impl as srv
import sqlite_vector_store as store

VARIANTS = ('production', 'rrf', 'score_fusion', 'rrf_qualified', 'score_fusion_qualified')
STOP = set('a an the and or to of in on for with is are be we do how what why can should must it our i this that at from by when as not'.split())


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def verify_sources(corpus):
    mem = srv._memory_mod()
    live_records = mem.load_memory_records(ROOT, statuses=None)
    live_paths = {Path(r['path']).relative_to(ROOT).as_posix() for r in live_records}
    if live_paths != {r['path'] for r in corpus['records']}:
        raise ValueError('frozen memory source census changed')
    live_register = mem.load_archive_register_entries(ROOT)
    if {r['memory_id'] for r in live_register} != {r['memory_id'] for r in corpus['archive_register']}:
        raise ValueError('frozen archive identity census changed')
    for item in corpus['source_manifest']:
        path = ROOT / item['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('frozen memory source changed: ' + item['path'])


def snapshot(directory):
    """Backup WAL-consistently, excluding this evaluation's own indexed prose."""
    path = directory / store.FILENAME
    with closing(sqlite3.connect((ROOT / '.wavefoundry/index' / store.FILENAME).as_uri() + '?mode=ro', uri=True)) as source:
        with closing(sqlite3.connect(path)) as target:
            source.backup(target)
            state = target.execute('SELECT status FROM build_state WHERE id=1').fetchone()
            if state != ('complete',):
                raise RuntimeError('snapshot_build_epoch_not_complete')
            ids = [r[0] for r in target.execute('SELECT id FROM chunks_docs WHERE path LIKE ?', ('docs/waves/1yad2 %',))]
            target.executemany('DELETE FROM vectors_docs WHERE chunk_id=?', [(i,) for i in ids])
            target.executemany('DELETE FROM chunks_docs WHERE id=?', [(i,) for i in ids])
            target.commit()
    return {'excluded_evaluation_chunks': len(ids), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def eligible(case):
    mem = srv._memory_mod()
    statuses = [case['status']] if case.get('status') else (None if case.get('include_history') else list(mem.DEFAULT_SURFACED_STATUSES))
    records = mem.load_memory_records(ROOT, statuses=statuses)
    if not case.get('include_history') and not case.get('status'):
        records.extend(mem.load_archive_register_entries(ROOT))
    if case.get('target') or case.get('symbol'):
        records = [r for r in records if mem.match_targets(r, path=case.get('target', ''), symbol=case.get('symbol', ''))]
    return records


def baseline(index, case):
    return srv.memory_search_response(ROOT, query=case['query'], target=case.get('target', ''), symbol=case.get('symbol', ''), status=case.get('status', ''), include_history=case.get('include_history', False), limit=20, index=index)


def candidates(index, case):
    started = time.perf_counter()
    records = eligible(case)
    by_id = {r['memory_id']: r for r in records}
    mem = srv._memory_mod()
    body_paths = {str(Path(r['path']).relative_to(ROOT).as_posix()): r['memory_id'] for r in records if r.get('record_type') != 'archive_register_entry'}
    loaded = time.perf_counter()
    vector = index._embed_query(case['query'], index._indexer_constant('DOCS_MODEL'))
    embedded = time.perf_counter()
    dense = store.dense_path_scores(index.index_dir, 'docs', vector, body_paths, 20)
    scored = time.perf_counter()
    dense_scores = {body_paths[p]: v for p, v in dense['scores'].items()}
    lexical_scores = ev.lexical_bm25_scores(records, case['query'])
    terms = set(ev._tokens(case['query'])) - STOP
    injection = {r['memory_id'] for r in records if len(terms & set(ev._tokens(ev._record_text(r)))) >= 2}
    rankings = ev.fusion_rankings(dense_scores, lexical_scores, injection_eligible=injection)
    fused = time.perf_counter()
    # Shared source ablation retains shipped authority ordering.
    union = list(dict.fromkeys(rankings['semantic'] + rankings['lexical']))
    rankings['source_policy'] = [r['memory_id'] for r, _ in srv._memory_ranked(ROOT, [by_id[i] for i in union], relevance_rank_by_id={mid: n for n, mid in enumerate(rankings['semantic'])})][:20]
    return records, rankings, {'dense_scores': dense_scores, 'lexical_scores': lexical_scores,
        'candidate_ids': union, 'eligible_chunks': dense['eligible_chunks'], 'covered_paths': dense['covered_paths'], 'requested_paths': dense['requested_paths'],
        'coverage_complete': dense['complete'], 'eligible_records': len(by_id),
        'stage_ms': {'load': (loaded-started)*1000, 'embedding': (embedded-loaded)*1000, 'dense': (scored-embedded)*1000, 'lexical_fusion': (fused-scored)*1000}}


def qualify(index, query, order, records):
    by_id = {r['memory_id']: r for r in records}
    texts = ['\n'.join(str(by_id[mid].get(key) or '') for key in ('title', 'action_delta', 'summary')) for mid in order[:20]]
    reranker = index._get_reranker()
    if reranker is None:
        raise RuntimeError('relevance_model_unavailable')
    values = list(map(float, reranker.rerank(query, texts))) if texts else []
    if len(values) != len(texts) or not all(math.isfinite(v) for v in values):
        raise ValueError('invalid_relevance_scores')
    return [mid for mid, score in zip(order[:20], values) if score >= -4.0], dict(zip(order[:20], values))


def experimental(index, case, variant):
    records, rankings, evidence = candidates(index, case)
    name = variant.removesuffix('_qualified')
    order = rankings[name]
    if variant.endswith('_qualified'):
        started = time.perf_counter()
        order, logits = qualify(index, case['query'], order, records)
        evidence['logits'] = logits
        evidence['stage_ms']['qualification'] = (time.perf_counter()-started)*1000
    selected = {r['memory_id']: r for r in records}
    ranked = srv._memory_ranked(ROOT, [selected[i] for i in order])
    views = {r['memory_id']: srv._memory_view(r, decay) for r, decay in ranked}
    # Same public record metadata and output cap; list order is experimental.
    response = srv._response('ok', {'records': [views[i] for i in order], 'count': len(order)}, diagnostics=[], next_tools=['memory_brief'], usage='memory_brief()')
    return response, evidence, rankings


def distribution(values):
    vals = sorted(values)
    if not vals:
        return {'count': 0, 'p50_ms': None, 'p95_ms': None, 'p99_ms': None}
    return {'count': len(vals), **{f'p{p}_ms': vals[max(0, math.ceil(p/100*len(vals))-1)] for p in (50,95,99)}}


class ProbeIndex(srv.WaveIndex):
    """Observe swallowed semantic failures without changing the public path."""
    semantic_failed = False

    def search_docs(self, *args, **kwargs):
        try:
            return super().search_docs(*args, **kwargs)
        except Exception:
            self.semantic_failed = True
            raise


def measure(index, case, variant):
    started = time.perf_counter()
    index.semantic_failed = False
    try:
        index._ensure_loaded()
        if index._docs_vector_layer is None:
            raise RuntimeError('docs_semantic_layer_unavailable')
        if variant == 'production':
            if index._get_reranker() is None:
                raise RuntimeError('production_reranker_unavailable')
            response = baseline(index, case)
            if index.semantic_failed:
                raise RuntimeError('production_semantic_failure')
            evidence, controls = {}, {}
        else:
            response, evidence, controls = experimental(index, case, variant)
        available = evidence.get('coverage_complete', True)
        if not available:
            response = baseline(None, case)
            evidence['fallback'] = 'public_lexical'
            evidence['unavailable'] = 'incomplete_semantic_coverage'
    except Exception as exc:
        # The fallback remains useful, but is never a qualified experiment.
        response = baseline(None, case)
        evidence, controls, available = {'unavailable': type(exc).__name__, 'fallback': 'public_lexical'}, {}, False
    return response, evidence, controls, available, (time.perf_counter()-started)*1000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', choices=('development','holdout'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--warm-calls', type=int, default=100)
    args = parser.parse_args()
    corpus = json.loads((HERE/'evidence/qualification-corpus.json').read_text())
    queries = json.loads((HERE/'evidence/qualification-queries.json').read_text())
    manifest = json.loads((HERE/'evidence/qualification-parameters.json').read_text())
    validation = ev.validate_qualification_manifest(corpus, queries, manifest)
    if not validation['valid']:
        raise ValueError(validation['reasons'])
    verify_sources(corpus)
    cases = queries['cases'] if args.split == 'holdout' else [dict(c, relevant_ids=c.get('expected', c.get('relevant_ids', [])), irrelevant_ids=[]) for c in queries['development_cases']]
    report = {'split': args.split, 'manifest_fingerprint': fingerprint(manifest), 'manifest_validation': validation,
        'runtime': {'python': sys.version, 'platform': platform.platform(), 'packages': {n: importlib.metadata.version(n) for n in ('apsw','sqlite-vec','onnxruntime','numpy','fastembed')}},
        'cases': [], 'timings': {}, 'limitations': ['One local macOS ARM64 CPU environment; no native Windows/Linux qualification.',
        'Positive unlabelled records remain unjudged; recall is against the independently enumerated relevant set.',
        'Evaluation-only runner; no automatic adoption or product ranking changes.',
        'Index snapshot excludes this wave evaluation prose to prevent benchmark leakage.',
        'Cold means first call on a fresh WaveIndex, including model initialization; OS file caches are not evicted.']}
    try:
        with tempfile.TemporaryDirectory(prefix='wf-memory-qualification-') as tmp:
            index_dir = Path(tmp)
            report['index_snapshot'] = snapshot(index_dir)
            for variant in VARIANTS:
                index = ProbeIndex(ROOT)
                index.index_dir = index_dir
                cold = measure(index, cases[0], variant)
                report.setdefault('cold', {})[variant] = {'ms': cold[4], 'available': cold[3]}
                times, failed = [], 0
                for n in range(max(len(cases), args.warm_calls)):
                    case = cases[n % len(cases)]
                    response, evidence, controls, available, elapsed = measure(index, case, variant)
                    if n < len(cases):
                        row = report['cases'][n] if len(report['cases']) > n else dict(case, rankings={}, availability={}, evidence={})
                        if len(report['cases']) <= n: report['cases'].append(row)
                        row['rankings'][variant] = [r['memory_id'] for r in response['data']['records']]
                        row['availability'][variant] = available
                        row['evidence'][variant] = evidence
                        if variant == 'rrf': row['controls'] = controls
                    if available: times.append(elapsed)
                    else: failed += 1
                report['timings'][variant] = dict(distribution(times), unavailable_calls=failed)
                report.setdefault('models', {})[variant] = {'embedding': index._indexer_constant('DOCS_MODEL'), 'reranker': index._indexer_constant('RERANKER_MODEL'), 'requested_provider': 'cpu',
                    'reranker_provider': getattr(index._reranker, 'provider', None)}
                write_json(args.output, report)
                print(variant, report['timings'][variant], flush=True)
        verify_sources(corpus)
    except Exception as exc:
        report['unavailable'] = type(exc).__name__ + ': ' + str(exc)
        write_json(args.output, report)
        raise
    report['metrics'] = {name: ev.quality_metrics(report['cases'], name) for name in VARIANTS}
    write_json(args.output, report)


if __name__ == '__main__':
    main()

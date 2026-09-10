"""Development-only comparison of explicitly labeled public vector experiments.

This is not the canonical evaluator's baseline approval and never certifies adoption.
The canonical fixture loader is reused for normalization only; comparisons and trace
checks below are independent of the experiment driver.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

TOOLS = ('code_ask', 'code_search', 'docs_search', 'code_lexical')
METRICS = ('recall_at_10', 'ndcg_at_10', 'mrr_at_10')
FLAGS = ('abstention_correct', 'question_type_correct')
PHASES = ('_embed_query', 'dense_hydrated', 'lexical_fetch', '_rerank', '_agent_rerank')
LANES = ('baseline', 'latest-ann', 'latest-exact', 'sqlite-scalar')
ENV_KEYS = ('python', 'platform', 'machine', 'processor', 'models', 'indexed_model_versions',
            'execution_providers', 'reranker_provider', 'packages', 'offline',
            'retrieval_toggles', 'production_tuning')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode()
    return hashlib.sha256(data).hexdigest()


def number(value, label):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            f'{label}: expected finite nonnegative number')
    return float(value)


def distribution(samples):
    require(bool(samples), 'empty timing sample set')
    ordered = sorted(samples)
    return {'count': len(ordered), 'median_ms': statistics.median(ordered),
            'p95_ms': ordered[math.ceil(.95 * len(ordered)) - 1],
            'p95_method': 'nearest_rank', 'p95_is_maximum': math.ceil(.95 * len(ordered)) == len(ordered)}


def validate_attempt(attempt, calls, corpus):
    """Validate against load_fixture_corpus's normalized corpus, not raw JSON.

    The public evaluator hashes normalized defaults/fields. The CLI calls the
    canonical loader before reaching this boundary; direct callers must too.
    """
    lane = attempt.get('lane')
    require(lane in LANES, 'unknown experiment lane')
    require(attempt.get('status') == 'completed' and not attempt.get('error'), 'attempt did not complete')
    require(attempt.get('production_certification') is False and
            attempt.get('kind') == 'experimental_public_path_overlay', 'missing experimental identity')
    require(isinstance(attempt.get('driver_sha256'), str) and len(attempt['driver_sha256']) == 64,
            'missing driver identity')
    report = attempt['report']
    require(report.get('invalidation_reasons') == [], 'invalid evaluator report')
    require(report.get('verdict') in ('baseline', 'pass', 'operator_review_required', 'fail'), 'unknown report verdict')
    require(report.get('fixture_digest') == digest(corpus), 'fixture digest mismatch')
    require(report.get('fixture_count') == len(corpus['fixtures']), 'fixture count mismatch')
    run_payload = {k: v for k, v in report.items() if k not in ('run_id', 'verdict')}
    require(report.get('run_id') == digest(run_payload), 'report run ID mismatch')
    require(report['production_identity'].get('end_digest_verified') is True, 'production end digest not verified')
    generation = report['generation']
    require(generation.get('start_status') == generation.get('end_status') == 'complete', 'incomplete generation')
    require(generation.get('start_token') == generation.get('end_token') and bool(generation.get('start_token')),
            'generation drift')
    require(generation.get('start') == generation.get('end') and
            generation.get('start_attempt_id') == generation.get('end_attempt_id'), 'generation metadata drift')
    health = report['corpus']['health']
    require(health.get('semantic_ready') is True and health.get('readiness_overview') == 'ready', 'unready corpus')
    require(report['corpus'].get('non_empty') is True, 'empty corpus')
    env = report['environment']
    require(all(key in env for key in ENV_KEYS), 'incomplete runtime identity')
    require(bool(env['models']) and bool(env['indexed_model_versions']) and bool(env['execution_providers']),
            'unknown model/provider identity')
    require(env.get('offline') is True, 'offline requirement not proven')
    require(not any(env['retrieval_toggles'].values()), 'retrieval toggle active')
    expected_version = '0.33.0' if lane == 'baseline' else '0.38.0'
    require(attempt['packages'].get('lancedb') == env['packages'].get('lancedb') == expected_version,
            'unexpected Lance version')
    if lane == 'sqlite-scalar':
        require(attempt['packages'].get('sqlite-vec') == '0.1.9', 'unexpected sqlite-vec version')
        require(attempt.get('sqlite_counts') == report['corpus']['current_lance_fts_counts'],
                'SQLite corpus count mismatch')
    fixture_by_id = {f['id']: f for f in corpus['fixtures']}
    require(len(fixture_by_id) == len(corpus['fixtures']), 'duplicate fixture identity')
    protocol = report['performance']['protocol']
    require(protocol['warmups_per_tool'] == 1 and protocol['measured_repetitions_per_applicable_pair'] == 3,
            'unexpected public evaluation repetition protocol')
    expected_cases = [(f['id'], tool, tool in f['applicable_tools']) for f in corpus['fixtures'] for tool in TOOLS]
    require([(c['fixture_id'], c['tool'], c['applicable']) for c in report['cases']] == expected_cases,
            'missing, reordered, or duplicate fixture/tool case')
    sequence = []
    for tool in TOOLS:
        fixture = next(f for f in corpus['fixtures'] if tool in f['applicable_tools'])
        require(report['performance']['warmups'][tool]['fixture_id'] == fixture['id'], 'wrong warmup fixture')
        sequence.append(('warmup', fixture, tool, None))
    sequence.extend(('degraded', corpus['fixtures'][0], tool, None)
                    for tool in ('docs_search', 'code_search', 'code_ask'))
    for case in report['cases']:
        if not case['applicable']:
            require(bool(case.get('exclusion_reason')), 'unexplained case exclusion')
            continue
        reps = case['repetitions']
        require([r['repetition'] for r in reps] == [1, 2, 3], 'missing/reordered repetitions')
        for rep in reps:
            for metric in METRICS:
                require(number(rep.get(metric), metric) <= 1, 'quality metric outside [0,1]')
            for flag in FLAGS:
                require(rep.get(flag) is None or type(rep[flag]) is bool, 'invalid correctness flag')
            sequence.append(('measured', fixture_by_id[case['fixture_id']], case['tool'], rep))
    require(len(sequence) == len(calls), 'trace call count mismatch')
    require(report['degraded_mode_probe'].get('passed') is True and
            report['degraded_mode_probe'].get('disposable_store') is True, 'missing degraded probe')
    root = str(Path(attempt['root']).resolve())
    require(root == report['index_identity']['repository_root'], 'attempt/report root mismatch')
    measured = []
    for (phase, fixture, tool, rep), call in zip(sequence, calls):
        require(call.get('tool') == tool and call.get('query') == fixture['query'], 'trace query/tool sequence mismatch')
        require(call.get('status') == 'ok', 'trace call failed')
        call_root = str(Path(call['root']).resolve())
        require((call_root != root) if phase == 'degraded' else (call_root == root), 'unexpected trace root')
        events = call['events']
        require(isinstance(events, list), 'missing events')
        totals = {name: 0.0 for name in PHASES}
        dense = []
        for event in events:
            require(event.get('phase') in PHASES and not event.get('error'), 'unknown/failed trace event')
            totals[event['phase']] += number(event.get('ms'), 'phase timing')
            if event['phase'] != 'dense_hydrated':
                continue
            dense.append(event)
            require(event.get('backend') == lane, 'unexpected backend execution')
            require(event.get('table') in ('docs', 'code') and event.get('layer') == 'project', 'unknown dense table/layer')
            require(type(event.get('limit')) is int and 0 < event['limit'] <= 240, 'invalid candidate limit')
            require(type(event.get('returned')) is int and 0 <= event['returned'] <= event['limit'], 'invalid returned count')
            if lane != 'sqlite-scalar':
                require(event.get('proof', {}).get('materialized') is True, 'missing substrate materialization proof')
                if lane == 'latest-exact':
                    require(event['proof'].get('bypass_applied') is True, 'missing exact bypass proof')
        if phase == 'degraded':
            require(not dense and call.get('search_mode') == 'lexical_fallback' and call.get('reranked') is False,
                    'degraded probe served semantic backend')
            continue
        if tool == 'code_lexical':
            require(not dense, 'lexical-only query unexpectedly used vectors')
        else:
            require(bool(dense), 'semantic query lacks actual substrate invocation')
            observed_phases = {event['phase'] for event in events}
            require('_embed_query' in observed_phases, 'semantic query lacks embedding phase proof')
            rerank_phase = '_agent_rerank' if tool == 'code_ask' else '_rerank'
            require(rerank_phase in observed_phases, 'semantic query lacks reranking phase proof')
            require(call.get('reranked') is True, 'semantic query skipped reranking')
            require(call.get('search_mode') == ('semantic' if tool == 'docs_search' else 'hybrid'),
                    'semantic query degraded')
        total = number(call.get('total_ms'), 'public timing')
        remainder = total - sum(totals.values())
        require(remainder >= -0.001, 'phase accounting overlaps/exceeds public total')
        if phase == 'measured':
            require(rep.get('fallback_reason') is None, 'measured query fallback')
            require(rep.get('search_mode') == call.get('search_mode'), 'report/trace search mode mismatch')
            measured.append({'fixture_id': fixture['id'], 'tool': tool, 'repetition': rep['repetition'],
                             'total_ms': total, 'canonical_elapsed_ms': number(rep['elapsed_ms'], 'canonical timing'),
                             'phase_ms': totals, 'uninstrumented_ms': max(0.0, remainder),
                             'dense_calls': len(dense), 'dense_rows': sum(e['returned'] for e in dense),
                             'dense_ms': [e['ms'] for e in dense]})
    return measured


def compare(base, candidate, base_calls, candidate_calls, corpus):
    base_times = validate_attempt(base, base_calls, corpus)
    candidate_times = validate_attempt(candidate, candidate_calls, corpus)
    require(base['lane'] == 'baseline' and candidate['lane'] != 'baseline', 'comparison requires baseline and candidate')
    require(base['driver_sha256'] == candidate['driver_sha256'], 'driver identity differs')
    a, b = base['report'], candidate['report']
    for key in ('schema', 'fixture_schema', 'fixture_digest', 'fixture_count', 'production_identity',
                'evaluator_identity', 'index_identity', 'generation', 'corpus', 'anchor_resolution'):
        require(key in a and key in b and a[key] == b[key], f'identity differs: {key}')
    require(a['performance']['protocol'] == b['performance']['protocol'], 'timing protocol differs')
    for key in set(a['environment']) | set(b['environment']):
        if key == 'packages':
            continue
        require(key in a['environment'] and key in b['environment'] and
                a['environment'][key] == b['environment'][key], f'environment differs: {key}')
    package_deltas = {}
    for location, ap, bp in (('environment', a['environment']['packages'], b['environment']['packages']),
                             ('attempt', base['packages'], candidate['packages'])):
        for key in set(ap) | set(bp):
            if ap.get(key) == bp.get(key):
                continue
            allowed = key == 'lancedb' or (location == 'attempt' and key == 'sqlite-vec' and
                                           candidate['lane'] == 'sqlite-scalar' and key not in ap)
            require(allowed, f'unapproved package delta: {location}.{key}')
            package_deltas[f'{location}.{key}'] = [ap.get(key), bp.get(key)]
    regressions = []
    for old, new in zip(a['cases'], b['cases']):
        if not old['applicable']:
            require(old == new, 'case exclusion changed')
            continue
        for before, after in zip(old['repetitions'], new['repetitions']):
            identity = {'fixture_id': old['fixture_id'], 'tool': old['tool'], 'repetition': before['repetition']}
            for metric in METRICS:
                if after[metric] < before[metric]:
                    regressions.append(dict(identity, metric=metric, baseline=before[metric], candidate=after[metric]))
            for flag in FLAGS:
                require((before[flag] is None) == (after[flag] is None), f'correctness applicability changed: {flag}')
                if before[flag] is True and after[flag] is not True:
                    regressions.append(dict(identity, metric=flag, baseline=True, candidate=after[flag]))
    timings = {}
    for tool in TOOLS:
        old = [r for r in base_times if r['tool'] == tool]
        new = [r for r in candidate_times if r['tool'] == tool]
        before, after = distribution([r['total_ms'] for r in old]), distribution([r['total_ms'] for r in new])
        timings[tool] = {'baseline': before, 'candidate': after,
                         'median_delta_ms': after['median_ms'] - before['median_ms'],
                         'p95_delta_ms': after['p95_ms'] - before['p95_ms'],
                         'median_delta_percent': 100 * (after['median_ms'] / before['median_ms'] - 1) if before['median_ms'] else None,
                         'p95_delta_percent': 100 * (after['p95_ms'] / before['p95_ms'] - 1) if before['p95_ms'] else None,
                         'candidate_phase_mean_ms': {p: statistics.mean(r['phase_ms'][p] for r in new) for p in PHASES},
                         'baseline_phase_mean_ms': {p: statistics.mean(r['phase_ms'][p] for r in old) for p in PHASES},
                         'candidate_phase_total_ms': {p: sum(r['phase_ms'][p] for r in new) for p in PHASES},
                         'baseline_phase_total_ms': {p: sum(r['phase_ms'][p] for r in old) for p in PHASES},
                         'candidate_uninstrumented_mean_ms': statistics.mean(r['uninstrumented_ms'] for r in new),
                         'baseline_uninstrumented_mean_ms': statistics.mean(r['uninstrumented_ms'] for r in old),
                         'baseline_dense_calls': sum(r['dense_calls'] for r in old),
                         'candidate_dense_calls': sum(r['dense_calls'] for r in new)}
    quality_failures = {'baseline': a.get('quality_gate_evaluation', {}).get('violations', []),
                        'candidate': b.get('quality_gate_evaluation', {}).get('violations', [])}
    return {'kind': 'experimental_public_vector_comparison', 'production_certification': False,
            'baseline_lane': base['lane'], 'candidate_lane': candidate['lane'],
            'quality_non_regression': not regressions, 'regressions': regressions,
            'standalone_quality_gate_failures': quality_failures, 'package_deltas': package_deltas,
            'total_latency_gate': 'descriptive_only_no_percentage_threshold', 'timings': timings,
            'baseline_measured_calls': base_times, 'candidate_measured_calls': candidate_times,
            'limits': ['Stage 1 vector-slice 100 ms gate is evaluated separately on its fixed repeated slices.',
                       'Public fixture metrics do not replace vector-oracle overlap or filtered public smoke.',
                       'Trace instrumentation is partial; uninstrumented remainder is explicit.',
                       'This comparison does not certify platform support, integration, migration, or adoption.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from retrieval_eval import load_fixture_corpus
    corpus = load_fixture_corpus(args.fixtures)
    def load(directory):
        return (json.loads((directory / 'result.json').read_text()),
                [json.loads(line) for line in (directory / 'calls.jsonl').read_text().splitlines()])
    a, ac = load(args.baseline)
    b, bc = load(args.candidate)
    result = compare(a, b, ac, bc, corpus)
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'quality_non_regression': result['quality_non_regression'],
                      'regression_count': len(result['regressions']), 'out': str(args.out)}))


if __name__ == '__main__':
    main()

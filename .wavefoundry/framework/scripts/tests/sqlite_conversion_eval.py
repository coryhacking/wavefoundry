#!/usr/bin/env python3
"""Paired frozen-corpus evaluation of the real SQLite conversion and Lance baseline.

Run manually, never by run_tests.py. All mutations stay beneath a newly created
output directory; historical corpus/drivers/receipts and the live index are read-only.
The six-run protocol preserves the canonical evaluator's three repetitions: nine
measurements per applicable fixture/tool pair per lane, across three full passes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace

BASELINE_HASHES = {
    'server_impl.py': 'a5054d39b4ab8dfb0c262ef5acd39718032b764c4eb2d24e4dc5e54ec339bf22',
    'accel_embedder.py': 'f546e85714362fd3d0650231d00a8f44a071c3044bdb6357ec2c2675e8fa6925',
    'retrieval_eval.py': 'f40ec2d734e657a2d7608ab46de73f54a1c824ab657f412598b57d41364006e4',
}
ORDER = ('baseline', 'sqlite', 'sqlite', 'baseline', 'baseline', 'sqlite')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, default=str) + '\n')


def prepare(args):
    args.output.mkdir(parents=True, exist_ok=False)
    scripts = args.source / '.wavefoundry/framework/scripts'
    frozen = args.corpus / '.wavefoundry/framework/scripts'
    for lane in ('baseline', 'sqlite'):
        shutil.copytree(args.corpus, args.output / (lane + '-root'),
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
        shutil.copytree(frozen if lane == 'baseline' else scripts,
                        args.output / (lane + '-scripts'),
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(scripts.parent / 'model-set-verification-manifest.json', args.output / 'model-set-verification-manifest.json')
    baseline = args.output / 'baseline-scripts'
    # Reconstruct only the independently recorded CPU batch-logging correction.
    server = subprocess.check_output(['git', 'show', 'HEAD:.wavefoundry/framework/scripts/server_impl.py'], cwd=args.source)
    server = server.replace(
        b'({reranker.provider}, static {accel_embedder.RERANK_STATIC_BATCH}x{accel_embedder.STATIC_SEQ})',
        b'({reranker.provider}, batch {reranker.batch_size}x{accel_embedder.STATIC_SEQ})')
    (baseline / 'server_impl.py').write_bytes(server)
    shutil.copy2(scripts / 'accel_embedder.py', baseline / 'accel_embedder.py')
    for name, expected in BASELINE_HASHES.items():
        if digest(baseline / name) != expected:
            raise RuntimeError(f'Corrected baseline hash mismatch: {name}')
    fixtures = json.loads((args.corpus / 'docs/evals/retrieval-quality-golden.json').read_text())['fixtures']
    if len(fixtures) != 35 or sum(len(case['applicable_tools']) for case in fixtures) != 55:
        raise RuntimeError('Frozen corpus must contain 35 fixtures / 55 applicable tool/query pairs')
    manifest = {
        'source': str(args.source), 'corpus': str(args.corpus), 'output': str(args.output),
        'fixture_count': 35, 'applicable_pairs': 55, 'order': ORDER,
        'canonical_repetitions': 3, 'measurements_per_pair_per_lane': 9,
        'model_cache': str(args.cache), 'downloads': 'forbidden; offline environment',
        'machine_cache': 'OS caches uncontrolled; warm latency only, process startup separately',
        'source_hashes': {lane: {str(path.relative_to(args.output / (lane + '-scripts'))): digest(path)
            for path in sorted((args.output / (lane + '-scripts')).rglob('*.py'))}
            for lane in ('baseline', 'sqlite')},
        'driver_sha256': digest(__file__),
    }
    save(args.output / 'manifest.json', manifest)


def freeze(args):
    """Refresh only disposable current-runtime code before any measured run."""
    if list(args.output.glob("run-*")):
        raise RuntimeError("Cannot change runtime snapshots after measured runs start")
    scripts = args.source / ".wavefoundry/framework/scripts"
    destination = args.output / "sqlite-scripts"
    shutil.copytree(scripts, destination, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manifest_path = args.output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["source_hashes"]["sqlite"] = {str(path.relative_to(destination)): digest(path)
        for path in sorted(destination.rglob("*.py"))}
    model_manifest = scripts.parent / "model-set-verification-manifest.json"
    shutil.copy2(model_manifest, args.output / model_manifest.name)
    manifest["model_manifest_sha256"] = digest(model_manifest)
    manifest["driver_sha256"] = digest(__file__)
    manifest["frozen_at"] = time.time()
    save(manifest_path, manifest)


def initialize(args):
    scripts = args.output / (args.lane + '-scripts')
    manifest = json.loads((args.output / "manifest.json").read_text())
    for relative, expected in manifest["source_hashes"][args.lane].items():
        if digest(scripts / relative) != expected:
            raise RuntimeError(f"Runtime snapshot changed: {args.lane}/{relative}")
    if "model_manifest_sha256" in manifest and digest(args.output / "model-set-verification-manifest.json") != manifest["model_manifest_sha256"]:
        raise RuntimeError("Model verification manifest changed")
    sys.path.insert(0, str(scripts))
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['WAVEFOUNDRY_EMBED_PROVIDER'] = 'cpu'
    import accel_embedder
    accel_embedder._ONNX_CACHE = args.cache
    return args.output / (args.lane + '-root')


def migration(args):
    root = initialize(args)
    import sqlite_storage_migration as migration
    ctx = SimpleNamespace(root=root, dry_run=False, storage_migration_protocol=1,
                          from_version='1.22.0', to_version='sqlite-conversion-evaluation',
                          zip_path=None, storage_old_hosts=[])
    os.environ[migration.CONFIRM_ENV] = '1'
    migration.prepare_upgrade(ctx)
    save(args.output / 'migration-transfer.json', migration.migrate_legacy(root, hosts_stopped=True))


def publish(args):
    """Phase-4-only corpus publication, never a claim of a complete upgrade."""
    from unittest.mock import patch
    root = initialize(args)
    import indexer
    import index_state_store as state
    import sqlite_vector_store as vectors
    import sqlite_storage_migration as migration
    import upgrade_wavefoundry as upgrade
    index_dir = root / '.wavefoundry/index'

    def authority():
        conn = state.open_read_only(index_dir)
        result = {}
        try:
            for layer in ('docs', 'code'):
                checksum = hashlib.sha256()
                count = 0
                for chunk_id, payload, embedding in conn.execute(
                    f'SELECT c.chunk_id,c.payload,v.embedding FROM chunks_{layer} c '
                    f'JOIN vectors_{layer} v ON c.id=v.chunk_id ORDER BY c.chunk_id'):
                    for item in (chunk_id.encode(), payload.encode(), bytes(embedding)):
                        checksum.update(len(item).to_bytes(8, 'big'))
                        checksum.update(item)
                    count += 1
                result[layer] = {'rows': count, 'sha256': checksum.hexdigest()}
        finally:
            conn.close()
        return result

    before = authority()
    # Repair derived digests from an earlier disposable transfer snapshot.
    # Canonical payload and embeddings remain byte-identical, verified below.
    for layer in ('docs', 'code'):
        state.rebuild_chunk_index(index_dir, layer, vectors.payload_rows(index_dir, layer))
    original_run = upgrade.subprocess_util.isolated_run
    result = {}
    child_results = []

    def phase_child(command, **kwargs):
        if Path(command[1]).name == 'setup_index.py':
            with patch.dict(os.environ, kwargs['env']), patch.object(
                indexer, '_predicted_precision_class', return_value='full'
            ), patch.object(indexer, '_get_embedder', side_effect=AssertionError(
                'Frozen corpus must not generate embeddings during publication'
            )):
                child_build = indexer.build_index(root, content='graph' if '--graph-only' in command else 'all')
                result['graph' if '--graph-only' in command else 'semantic'] = child_build
            save(args.output / 'migration-build.json', result)
            status = int(bool(child_build.get('failed') or child_build.get('error')))
            child_results.append({'command': command, 'returncode': status, 'actual_build': child_build})
            return subprocess.CompletedProcess(command, status)
        # Graph and fresh-process verification use actual snapshotted scripts.
        child_result = original_run(command, **kwargs)
        child_results.append({"command": command, "returncode": child_result.returncode})
        return child_result

    with patch.object(upgrade.subprocess_util, 'isolated_run', side_effect=phase_child):
        published = upgrade.phase_index_update(root)
    after = authority()
    save(args.output / 'migration-publication-controls.json', {
        'scope': 'Phase 4 only; not a complete upgrade test',
        'shim': 'Publication-only full-precision prediction; embedder construction forbidden',
        'publisher_grant': 'Minted by actual phase_index_update',
        'before': before, 'after': after, 'identical': before == after,
        'published': published, 'child_results': child_results,
    })
    if not published or before != after or any(child["returncode"] for child in child_results):
        raise RuntimeError('Frozen-corpus publication failed or changed canonical vectors/payload')
    save(args.output / 'migration-verification.json', migration.verify_migration(root))
    save(args.output / 'migration-cleanup.json', migration.cleanup_legacy(root))


def run(args):
    root = initialize(args)
    import retrieval_eval as evaluation
    import server_impl as server
    folder = args.output / f'run-{args.pass_number}-{args.lane}'
    folder.mkdir(exist_ok=False)
    trace = []
    phases = []
    query_vectors = {}
    dense_requests = {}
    original_factory = evaluation._new_evaluation_index
    def factory(module, root):
        index = original_factory(module, root)
        dense_name = "_vector_search" if args.lane == "sqlite" else "_lance_search"
        for name in ("_embed_query", dense_name, "_rerank", "_agent_rerank"):
            original_method = getattr(index, name)
            def timed(*values, _name=name, _method=original_method, **options):
                start = time.perf_counter()
                try:
                    value = _method(*values, **options)
                    if _name == "_embed_query":
                        key = json.dumps([str(item) for item in values], ensure_ascii=False)
                        query_vectors.setdefault(key, [float(item) for item in value])
                    return value
                finally:
                    phases.append({"phase": "dense_hydrated" if _name == dense_name else _name,
                                   "ms": (time.perf_counter()-start)*1000})
                    if _name == dense_name and args.lane == "sqlite" and values[0] is not None:
                        request = {"layer": values[0], "vector": [float(item) for item in values[1]],
                                   "limit": values[2], "predicate": options.get("where", values[3] if len(values) > 3 else None)}
                        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
                        dense_requests.setdefault(key, request)
            setattr(index, name, timed)
        return index
    evaluation._new_evaluation_index = factory
    original_fts = server._fts_probed_fetch
    def fts(*values, **options):
        start = time.perf_counter()
        try:
            return original_fts(*values, **options)
        finally:
            phases.append({"phase": "lexical_fetch", "ms": (time.perf_counter()-start)*1000})
    server._fts_probed_fetch = fts
    original = evaluation._call_public_path
    def measured(module, index, root, tool, query, epoch):
        offset = len(phases)
        start = time.perf_counter()
        result = original(module, index, root, tool, query, epoch)
        row = {'tool': tool, 'query': query, 'ms': (time.perf_counter() - start) * 1000,
               'status': result.get('status'), 'search_mode': (result.get('data') or {}).get('search_mode'),
               'events': phases[offset:]}
        trace.append(row)
        with (folder / 'calls.jsonl').open('a') as stream:
            stream.write(json.dumps(row) + '\n')
        return result
    evaluation._call_public_path = measured
    started = time.time()
    try:
        report = evaluation.run_evaluation(root, root / 'docs/evals/retrieval-quality-golden.json')
        save(folder / 'report.json', report)
    finally:
        save(folder / 'query-vectors.json', query_vectors)
        save(folder / 'dense-requests.json', dense_requests)
        save(folder / 'execution.json', {'lane': args.lane, 'pass': args.pass_number,
             'started_at': started, 'ended_at': time.time(), 'calls': len(trace),
             'driver_sha256': digest(__file__),
             'loaded_sources': {module.__name__: {'path': module.__file__, 'sha256': digest(module.__file__)}
                                for module in (server, evaluation)},
             'cold_start': 'fresh process; OS and model file caches may be warm'})


def probe(args):
    root = initialize(args)
    import server_impl as server
    measurements = []
    for phase in ("process_cold", "same_epoch_warm"):
        start = time.perf_counter()
        result = server._fts_degraded_serve(root, ("docs", "code"), "framework", 5)
        measurements.append({"phase": phase, "ms": (time.perf_counter()-start)*1000,
                             "available": result.get("available"),
                             "failure_reason": result.get("failure_reason"),
                             "result_count": len(result.get("results", []))})
        if not result.get("available"):
            save(args.output / "sqlite-integrity-startup.json", measurements)
            raise RuntimeError(str(result))
    save(args.output / "sqlite-integrity-startup.json", measurements)


def compare(args):
    reports = {lane: [] for lane in ("baseline", "sqlite")}
    for number, lane in enumerate(ORDER, 1):
        reports[lane].append(json.loads((args.output / f"run-{number}-{lane}/report.json").read_text()))
    violations = []
    keys = ("recall_at_10", "ndcg_at_10", "mrr_at_10", "abstention_correct", "question_type_correct")
    for lane, runs in reports.items():
        for number, report in enumerate(runs):
            if report.get("invalidation_reasons"):
                violations.append({"kind": "invalid_run", "lane": lane, "pass": number,
                                   "reasons": report["invalidation_reasons"]})
    for baseline in reports["baseline"]:
        reference = {(case["fixture_id"], case["tool"]): case for case in baseline["cases"] if case["applicable"]}
        for current in reports["sqlite"]:
            candidates = {(case["fixture_id"], case["tool"]): case for case in current["cases"] if case["applicable"]}
            if set(candidates) != set(reference):
                raise RuntimeError("Compared applicable fixture/tool sets differ")
            for identity, case in candidates.items():
                for metric in keys:
                    old, new = reference[identity].get(metric), case.get(metric)
                    if old is not None and (new is None or new < old):
                        violations.append({"kind": "quality_loss", "pair": identity, "metric": metric,
                                           "baseline": old, "sqlite": new})
    save(args.output / "comparison.json", {"passed": not violations, "violations": violations,
         "comparison": "Every SQLite pass against every baseline pass; no averaging hides a loss",
         "latency": {lane: [report["performance"] for report in runs] for lane, runs in reports.items()}})
    if violations:
        raise RuntimeError(f"Comparison has {len(violations)} violations")


def scale(args):
    """Bounded native-adapter capacity screen using the golden FP32 queries.

    Replication preserves payloads, text, metadata and vectors, changing only
    chunk IDs. This tests scan/storage capacity, not larger-corpus relevance.
    Each layer stops at its first p95 >=100ms. Global resource limits stop all
    work; unmeasured sizes are never represented as qualified.
    """
    import math
    import resource
    import statistics
    import platform
    from importlib.metadata import version
    started = time.monotonic()
    folder = args.output / ('scale-max-caps' if args.mode == 'scale-caps' else 'scale')
    folder.mkdir(exist_ok=False)
    scripts = folder / 'scripts'
    shutil.copytree(args.source / '.wavefoundry/framework/scripts', scripts,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    sys.path.insert(0, str(scripts))
    import sqlite_runtime as runtime
    import sqlite_vector_store as vectors
    database = folder / 'index'
    database.mkdir()
    runtime.backup(args.output / 'sqlite-root/.wavefoundry/index' / vectors.FILENAME,
                   database / vectors.FILENAME)
    requests = list(json.loads((args.output / 'run-2-sqlite/dense-requests.json').read_text()).values())
    report = {
        'scope': 'Native exact cosine adapter; replicated corpus; no new relevance claim',
        'runtime': {'sqlite': runtime.apsw.sqlitelibversion(), 'sqlite_source_id': runtime.apsw.sqlite3_sourceid(),
                    'apsw': runtime.apsw.apswversion(), 'sqlite_vec': version('sqlite-vec'),
                    'python': sys.version, 'platform': platform.platform(), 'machine': platform.machine()},
        'source_hashes': {str(p.relative_to(scripts)): digest(p) for p in sorted(scripts.rglob('*.py'))},
        'query_source_sha256': digest(args.output / 'run-2-sqlite/dense-requests.json'),
        'driver_sha256': digest(__file__), 'dimensions': 384, 'representation': 'float32',
        'metric': 'cosine', 'index': 'SQL scalar exact scan; native metadata B-tree prefilters',
        'limits': {'seconds': 1800, 'rss_bytes': 4 * 1024**3, 'temporary_bytes': 8 * 1024**3,
                   'vector_p95_ms': 100}, 'stages': [], 'qualified_per_layer': {},
        'cache': 'OS caches uncontrolled; each request warmed once per stage; fresh native read connection per call',
    }

    def resources():
        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss = usage.ru_maxrss
        if sys.platform != 'darwin':
            rss *= 1024
        return {'peak_rss_bytes': rss, 'temporary_bytes': sum(p.stat().st_size for p in database.iterdir() if p.is_file()),
                'elapsed_seconds': time.monotonic() - started,
                'cpu_user_seconds': usage.ru_utime, 'cpu_system_seconds': usage.ru_stime}

    def enforce():
        observed = resources()
        report['resources'] = observed
        save(folder / 'result.json', report)
        if observed['peak_rss_bytes'] >= 4 * 1024**3 or observed['temporary_bytes'] >= 8 * 1024**3 or observed['elapsed_seconds'] >= 1800:
            report['stopped'] = 'resource_cap'
            save(folder / 'result.json', report)
            raise RuntimeError('Capacity screen reached a declared resource cap')

    def summarize(values):
        ordered = sorted(values)
        return {'n': len(ordered), 'p50_ms': statistics.median(ordered),
                'p95_ms': ordered[math.ceil(.95 * len(ordered)) - 1],
                'p99_ms': ordered[math.ceil(.99 * len(ordered)) - 1], 'maximum_ms': max(ordered)}

    conn = runtime.connect(database / vectors.FILENAME)
    try:
        report['pragmas'] = {name: conn.execute('PRAGMA ' + name).fetchone()[0]
                             for name in ('page_size', 'cache_size', 'mmap_size', 'journal_mode', 'synchronous', 'wal_autocheckpoint')}
        for layer in ('docs', 'code'):
            original = vectors.payload_rows(database, layer, include_vector=True)
            initial = len(original)
            current = initial
            selected = [dict(r, limit=240) if args.mode == 'scale-caps' else r
                        for r in requests if r['layer'] == layer]
            if not selected or not initial:
                raise RuntimeError('Golden native requests/corpus missing for ' + layer)
            # Both a normal category and a highly selective real file path.
            column = 'kind' if layer == 'docs' else 'language'
            category = str(original[0].get(column) or '')
            path = str(original[0]['path'])
            predicates = [f"{column} = '{category.replace(chr(39), chr(39)*2)}'",
                          f"path = '{path.replace(chr(39), chr(39)*2)}'"]
            workloads = [('global', dict(r, predicate=None)) for r in selected]
            for predicate in predicates:
                workloads.extend(('filtered', dict(r, predicate=predicate)) for r in selected[:10])
            targets = ({vectors.QUALIFIED_MAX_ROWS[layer]} if args.mode == 'scale-caps'
                       else {initial, 2 * initial, 50_000, 250_000, 500_000})
            for target in sorted(targets):
                if target < initial:
                    continue
                while current < target:
                    enforce()
                    stop = min(current + 250, target)
                    batch = [dict(original[number % initial], id=f"scale-{layer}-{number}")
                             for number in range(current, stop)]
                    with conn:
                        vectors.write_rows(conn, layer, batch)
                    current = stop
                conn.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchone()
                enforce()
                measurements = {'global': [], 'filtered': []}
                filters = {}
                for predicate in predicates:
                    expression, parameters = vectors._predicate(predicate)
                    filters[predicate] = conn.execute(f'SELECT count(*) FROM chunks_{layer} c WHERE {expression}', parameters).fetchone()[0]
                for _group, request in workloads:
                    vectors.dense_rows(database, layer, request['vector'], request['limit'], request['predicate'])
                for repetition in range(3):
                    for group, request in workloads:
                        start = time.perf_counter()
                        rows = vectors.dense_rows(database, layer, request['vector'], request['limit'], request['predicate'])
                        milliseconds = (time.perf_counter() - start) * 1000
                        if len(rows) > request['limit']:
                            raise RuntimeError('Native candidate cap violated')
                        measurements[group].append(milliseconds)
                    enforce()
                stage = {'layer': layer, 'rows': current, 'initial_rows': initial,
                         'candidate_caps': sorted({r['limit'] for _, r in workloads}),
                         'filter_cardinality': filters, 'metrics': {k: summarize(v) for k, v in measurements.items()},
                         'resources': resources(), 'samples_ms': measurements}
                report['stages'].append(stage)
                if any(value['p95_ms'] >= 100 for value in stage['metrics'].values()):
                    stage['qualified'] = False
                    stage['stop_reason'] = 'first_vector_p95_budget_breach'
                    save(folder / 'result.json', report)
                    break
                stage['qualified'] = True
                report['qualified_per_layer'][layer] = current
                save(folder / 'result.json', report)
            del original
        report['stopped'] = 'completed_bounded_screen'
        report['resources'] = resources()
        save(folder / 'result.json', report)
    finally:
        conn.close()


def memory_worker(args):
    """Measure one fresh registered-tool worker, including real loaded models."""
    import asyncio
    import resource
    from unittest.mock import patch
    root = initialize(args)
    import server_impl as server
    from mcp.server.fastmcp import FastMCP
    folder = args.output / ('memory-' + args.lane)
    folder.mkdir(exist_ok=False)
    fixtures = json.loads((root / 'docs/evals/retrieval-quality-golden.json').read_text())['fixtures']
    requests = []
    for tool in ('code_ask', 'code_search', 'docs_search'):
        fixture = next(row for row in fixtures if tool in row['applicable_tools'])
        requests.append((tool, {'question' if tool == 'code_ask' else 'query': fixture['query']}))

    def peak():
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(value if sys.platform == 'darwin' else value * 1024)

    report = {'lane': args.lane, 'driver_sha256': digest(__file__),
              'server_sha256': digest(server.__file__), 'requests': requests,
              'rss_scope': 'Fresh process peak RSS, includes imports, actual models, native stores and allocator high-water mark',
              'background': 'Staleness/projection monitors and model-download prewarm disabled; real registered retrieval unchanged',
              'cache': 'offline existing model cache; uncontrolled warm OS filesystem cache',
              'after_import_peak_rss_bytes': peak(), 'calls': []}
    with patch.object(server.ImplHandler, '_start_staleness_monitor'), patch.object(
        server.ImplHandler, '_start_ce_projection_monitor'
    ), patch.object(server.WaveIndex, '_start_background_model_downloads'), patch.object(
        server.WaveIndex, '_start_background_model_downloads_after_startup'
    ):
        handler = server.build_handler(root)
        try:
            mcp = FastMCP('sqlite-conversion-memory-worker')
            server.register_mcp_surface(mcp, lambda: handler)
            report['after_registration_peak_rss_bytes'] = peak()
            for repetition in range(2):
                for tool, arguments in requests:
                    start = time.perf_counter()
                    response = asyncio.run(mcp._tool_manager.call_tool(
                        tool, arguments, context=mcp.get_context(), convert_result=False))
                    record = {'tool': tool, 'repetition': repetition + 1,
                              'elapsed_ms': (time.perf_counter() - start) * 1000,
                              'peak_rss_bytes': peak(), 'status': response.get('status'),
                              'search_mode': (response.get('data') or {}).get('search_mode')}
                    report['calls'].append(record)
                    if response.get('status') != 'ok':
                        raise RuntimeError('Registered memory worker query failed: ' + json.dumps(response, default=str))
            report['loaded_embedders'] = list(handler.index._embedders)
            report['reranker_loaded'] = handler.index._reranker is not None
            report['peak_rss_bytes'] = peak()
        finally:
            handler.close()
            save(folder / 'result.json', report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'freeze', 'migrate', 'publish', 'probe', 'run', 'compare', 'scale', 'scale-caps', 'memory'))
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument('--corpus', type=Path, default=Path('/tmp/wf-vector-eval-1xhbo-public'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, default=Path('/tmp/1xj6n-static-cache'))
    parser.add_argument('--lane', choices=('baseline', 'sqlite'), default='sqlite')
    parser.add_argument('--pass-number', type=int, default=1)
    args = parser.parse_args()
    for key in ('source', 'corpus', 'output', 'cache'):
        setattr(args, key, getattr(args, key).resolve())
    if args.output == args.source or args.output == args.corpus or args.output in args.corpus.parents:
        parser.error('Output must be an isolated evaluation directory')
    {'prepare': prepare, 'freeze': freeze, 'migrate': migration, 'publish': publish, 'probe': probe, 'run': run, 'compare': compare, 'scale': scale, 'scale-caps': scale, 'memory': memory_worker}[args.mode](args)


if __name__ == '__main__':
    main()

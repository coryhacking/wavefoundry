"""Isolated actual-producer bridge experiment; no shipped runtime conversion.

GraphIndexSession and the community builder still write disposable staging
artifacts. Only one copied schema-7 file is the prototype publication authority.
Its production build_state is deliberately unchanged: this is not a full indexer
epoch/rebuild implementation. Run with the tool Python and -B.
"""
from __future__ import annotations

import argparse
import calendar
import collections
import contextlib
import fcntl
import gc
import hashlib
import json
import os
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import graph_eval as base

# Identical actual producer configuration for A and C; no untracked process pool.
os.environ['WAVEFOUNDRY_GRAPH_PARALLEL_BACKEND'] = 'threads'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import graph_indexer as gi
import graph_cluster as cluster
import indexer
import index_state_store as iss
import sqlite_vector_store as vs
import chunker

EXTRA_SCHEMA = '''
CREATE TABLE IF NOT EXISTS graph_extraction_files(path TEXT PRIMARY KEY,source_hash TEXT NOT NULL,record BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS graph_extraction_blobs(key TEXT PRIMARY KEY,value BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS graph_extraction_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS graph_community_artifact(id INTEGER PRIMARY KEY CHECK(id=1),payload BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS graph_publication(id INTEGER PRIMARY KEY CHECK(id=1),generation INTEGER NOT NULL,fingerprint TEXT NOT NULL,semantic_epoch TEXT NOT NULL);
'''
GRAPH_TABLES = ('graph_edges', 'graph_nodes', 'graph_keys', 'graph_meta')
EXTRA_TABLES = ('graph_extraction_files', 'graph_extraction_blobs', 'graph_extraction_meta')
FIXTURE = ('lifecycle_fixture/caller.py', 'lifecycle_fixture/provider.py', 'lifecycle_fixture/guide.md')
MAPPING_KINDS = sorted(gi.DECLARATION_NODE_KINDS | {'method', 'interface', 'constructor', 'enum', 'record'})


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(compact(value).encode()).hexdigest()


def stable(value):
    """Normalize only documented artifact timing/presence wrapper fields.

    Every node/edge and community member attribute stays byte-for-byte semantic
    data. The producer returns no presence wrapper; artifact readers add True.
    A degraded False wrapper is never equivalent to a successful producer.
    """
    if not isinstance(value, dict):
        raise TypeError('expected artifact dictionary')
    if 'present' in value and value['present'] is not True:
        raise AssertionError('artifact reader is degraded')
    normalized = {k: v for k, v in value.items() if k not in
                  ('generated_at', 'graph_mtime', 'cluster_mtime', 'present', 'merge_stats')}
    if 'cluster_schema_version' in value and isinstance(value.get('betweenness'), dict):
        normalized['betweenness'] = {k: v for k, v in value['betweenness'].items() if k != 'elapsed_ms'}
    return normalized


def elapsed(start):
    return (time.perf_counter() - start) * 1000


def normalization_controls():
    nested = {'generated_at': 'semantic', 'present': False, 'elapsed_ms': 7,
              'graph_mtime': 8, 'cluster_mtime': 9, 'merge_stats': {'count': 3}}
    artifact = {'present': True, 'generated_at': 'transient',
                'nodes': [nested], 'edges': [dict(nested)]}
    normalized = stable(artifact)
    assert normalized['nodes'] == artifact['nodes'] and normalized['edges'] == artifact['edges']
    try:
        stable({'present': False, 'nodes': []})
    except AssertionError:
        pass
    else:
        raise AssertionError('degraded artifact accepted')
    return {'nested_semantic_attributes_retained': True, 'degraded_present_false_rejected': True}


@contextlib.contextmanager
def native_deadline(connection):
    end = time.monotonic() + 5
    connection.set_progress_handler(lambda: time.monotonic() > end, 1000)
    try:
        with base.query_deadline():
            yield
    finally:
        connection.set_progress_handler(None)


def index_path(stage):
    return stage / '.wavefoundry/index'


def graph_dir(stage):
    return index_path(stage) / 'graph'


def reset_dir(root, path):
    path = base.owned(root, path)
    if path == root:
        raise ValueError('refuse root cleanup')
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def frozen_manifest(root):
    receipt_path = base.owned(root, root / 'lifecycle-source-manifest.json')
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        for p, h in receipt['files'].items():
            if base.sha(base.owned(root, root / p)) != h:
                raise ValueError('frozen copied cohort changed: ' + p)
        return receipt['files']
    c = base.connect(root / '.wavefoundry/index/index-state.sqlite', read_only=True)
    try:
        rows = list(c.execute('SELECT path,hash FROM build_file_meta ORDER BY path'))
    finally:
        c.close()
    files = indexer._filter_project_index_excludes(
        [root / p for p, _ in rows], root, None,
        project_include_prefixes=indexer._merged_project_include_prefixes_for_graph(root, None))
    selected = {str(p.relative_to(root)) for p in files}
    manifest = {p: base.sha(base.owned(root, root / p)) for p, h in rows if p in selected}
    native = sqlite3.connect(f'file:{root}/.wavefoundry/index/graph/project-graph-state.sqlite?mode=ro', uri=True)
    try:
        graph_sources = dict(native.execute('SELECT path,source_hash FROM files'))
    finally:
        native.close()
    for p, h in graph_sources.items():
        if manifest.get(p) != h:
            raise ValueError('persisted graph source mismatch: ' + p)
    mismatches = [{'path': p, 'index_hash': h, 'copied_hash': manifest[p],
                   'in_graph_extraction_store': p in graph_sources}
                  for p, h in rows if p in selected and h != manifest[p]]
    base.dump(receipt_path, {'files': manifest, 'sha256': digest(manifest),
                            'graph_source_hashes_verified': len(graph_sources),
                            'semantic_metadata_mismatches': mismatches,
                            'basis': 'Frozen metadata path census and actual copied bytes; no whole semantic freshness claim'})
    return manifest


def clone_sources(root, stage, manifest):
    reset_dir(root, stage)
    for rel in sorted(set(manifest) | {'.gitattributes', '.gitignore', 'docs/workflow-config.json'}):
        src = base.owned(root, root / rel)
        if not src.is_file():
            continue
        dst = base.owned(root, stage / rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def producer(root, stage, manifest, changed=None):
    """Actual extraction, global resolution, state commit and community work."""
    base.owned(root, stage)
    names = sorted(p for p in set(manifest) | set(FIXTURE) if (stage / p).is_file())
    meta = {p: {'hash': base.sha(stage / p)} for p in names}
    state_path = graph_dir(stage) / 'project-graph-state.sqlite'
    known = set()
    if state_path.exists():
        native = sqlite3.connect(f'file:{state_path}?mode=ro', uri=True)
        try:
            known = {r[0] for r in native.execute('SELECT path FROM files')}
        finally:
            native.close()
    start = time.perf_counter()
    payload = gi.update_graph_index(
        root=stage, index_dir=index_path(stage), layer='project',
        files=[stage / p for p in names], current_file_meta=meta,
        changed=set(names) if changed is None else set(changed), removed=known - set(names),
        walker_version=indexer.WALKER_VERSION, chunker_version=chunker.CHUNKER_VERSION)
    extraction_ms = elapsed(start)
    stats = payload.pop('merge_stats', {})
    start = time.perf_counter()
    communities = cluster.update_graph_clusters(
        root=stage, index_dir=index_path(stage), layer='project', graph_payload=payload)
    return payload, communities, {'source_extract_resolve_persist_ms': extraction_ms,
                                 'community_compute_persist_ms': elapsed(start), 'merge': stats}


def prepared_graph(root, stage, payload, communities):
    """Serialize graph SQL and fetch actual compressed extraction rows BEFORE lock."""
    start = time.perf_counter()
    path = base.owned(root, stage / 'prepared-graph.sqlite')
    base.make_db(root, path, payload)
    native = sqlite3.connect(f'file:{graph_dir(stage)}/project-graph-state.sqlite?mode=ro', uri=True)
    try:
        records = {name: list(native.execute('SELECT * FROM ' + name))
                   for name in ('files', 'blobs', 'meta')}
    finally:
        native.close()
    # Filesystem stat bindings only apply to disposable producer artifacts.
    records['meta'] = [r for r in records['meta'] if r[0] not in
                       ('payload_size', 'payload_mtime_ns', 'payload_stat_state')]
    fingerprint = payload['input_fingerprint']
    assert dict(records['meta'])['payload_fingerprint'] == fingerprint
    assert gi._decode_state_record(dict(records['blobs'])['merge_state'])['payload_fingerprint'] == fingerprint
    assert communities['input_fingerprint'] == fingerprint
    return {'path': path, 'records': records, 'community': gi._encode_state_record(communities),
            'fingerprint': fingerprint, 'preparation_ms': elapsed(start)}


def shared_path(root, name='shared'):
    return base.owned(root, root / 'lifecycle' / name / 'index-state.sqlite')


def initialize_shared(root, path):
    path = base.owned(root, path)
    reset_dir(root, path.parent)
    base.backup(root / '.wavefoundry/index/index-state.sqlite', path)
    c = base.connect(path)
    c.execute(base.SCHEMA + EXTRA_SCHEMA)
    c.close()


def publish(root, path, prepared, generation, semantic=None, action='commit', observer=None):
    """Only this transaction changes the published prototype, including real deltas."""
    store = iss.IndexStateStore(base.owned(root, path).parent)
    c = store._conn
    c.execute('ATTACH DATABASE ? AS prepared_graph', (str(base.owned(root, prepared['path'])),))
    epoch = compact(list(c.execute('SELECT * FROM build_state')))
    start = time.perf_counter()
    c.execute('BEGIN IMMEDIATE')
    try:
        for name in GRAPH_TABLES:
            c.execute('DELETE FROM ' + name)
        for name in reversed(GRAPH_TABLES):
            c.execute(f'INSERT INTO {name} SELECT * FROM prepared_graph.{name}')
        for src, dst in zip(('files', 'blobs', 'meta'), EXTRA_TABLES):
            c.execute('DELETE FROM ' + dst)
            rows = prepared['records'][src]
            if rows:
                c.executemany('INSERT INTO ' + dst + ' VALUES(' + ','.join('?' * len(rows[0])) + ')', rows)
        c.execute('INSERT OR REPLACE INTO graph_community_artifact VALUES(1,?)', (prepared['community'],))
        if semantic is not None:
            semantic.apply(store)
        c.execute('INSERT OR REPLACE INTO graph_publication VALUES(1,?,?,?)',
                  (generation, prepared['fingerprint'], epoch))
        assert compact(list(c.execute('SELECT * FROM build_state'))) == epoch
        if observer:
            observer('before_commit')
        if action == 'crash':
            os._exit(77)
        c.execute('ROLLBACK' if action == 'rollback' else 'COMMIT')
        lock_ms = elapsed(start)
        if observer:
            observer('after_commit')
    except BaseException:
        if not c.get_autocommit():
            c.execute('ROLLBACK')
        raise
    finally:
        c.execute('DETACH DATABASE prepared_graph')
        store.close()
    return lock_ms


def shared_payload(c):
    header = json.loads(c.execute("SELECT value FROM graph_meta WHERE key='header'").fetchone()[0])
    header['nodes'] = [json.loads(r[0]) for r in c.execute('SELECT payload FROM graph_nodes ORDER BY ordinal')]
    header['edges'] = [json.loads(r[0]) for r in c.execute('SELECT payload FROM graph_edges ORDER BY ordinal')]
    return header


def restore_stage(root, path, stage):
    """Prove restart needs only shared publication rows, never prior stage files."""
    start = time.perf_counter()
    reset_dir(root, graph_dir(stage))
    c = base.connect(base.owned(root, path), read_only=True)
    c.execute('BEGIN')
    try:
        payload = shared_payload(c)
        community = gi._decode_state_record(c.execute('SELECT payload FROM graph_community_artifact').fetchone()[0])
        native = gi.GraphStateStore(graph_dir(stage) / 'project-graph-state.sqlite',
                                    layer='project', walker_version=indexer.WALKER_VERSION,
                                    chunker_version=chunker.CHUNKER_VERSION)
        try:
            with native._conn:
                for src, dst in zip(EXTRA_TABLES, ('files', 'blobs', 'meta')):
                    native._conn.execute('DELETE FROM ' + dst)
                    rows = list(c.execute('SELECT * FROM ' + src))
                    if rows:
                        native._conn.executemany('INSERT INTO ' + dst + ' VALUES(' + ','.join('?' * len(rows[0])) + ')', rows)
            gi._write_json(graph_dir(stage) / 'project-graph.json', payload)
            gi._write_json(graph_dir(stage) / 'project-graph-clusters.json', community)
            stat = (graph_dir(stage) / 'project-graph.json').stat()
            native.set_meta({'payload_stat_state': 'bound', 'payload_size': str(stat.st_size),
                             'payload_mtime_ns': str(stat.st_mtime_ns)})
        finally:
            native.close()
    finally:
        c.execute('COMMIT')
        c.close()
    return elapsed(start)


def semantic_digest(c):
    """All canonical payloads, actual vector bytes, registry and production epoch."""
    h = hashlib.sha256()
    for table, order in [('chunks_code', 'id'), ('chunks_docs', 'id'),
                         ('vectors_code', 'chunk_id'), ('vectors_docs', 'chunk_id'),
                         ('chunk_registry', 'table_name,chunk_id'), ('build_state', 'id')]:
        h.update(table.encode())
        for row in c.execute(f'SELECT * FROM {table} ORDER BY {order}'):
            for value in row:
                data = bytes(value) if isinstance(value, bytes) else compact(value).encode()
                h.update(str(len(data)).encode() + b':' + data)
    return h.hexdigest()


def mapping(c):
    """Declaration-start containment in actual chunks; no invented symbol ranges."""
    query = '''SELECT k.name,ch.chunk_id,
      CASE WHEN ef.source_hash=bf.hash THEN 'matching_source_hash' ELSE 'stale_or_unproven_source' END
      FROM graph_nodes n JOIN graph_keys k ON k.id=n.id
      JOIN chunks_code ch ON ch.path=json_extract(n.payload,'$.source_file')
      LEFT JOIN graph_extraction_files ef ON ef.path=ch.path
      LEFT JOIN build_file_meta bf ON bf.path=ch.path
      WHERE json_extract(n.payload,'$.kind') IN (SELECT value FROM json_each(?))
      AND CAST(substr(json_extract(n.payload,'$.source_location'),1,
      instr(json_extract(n.payload,'$.source_location'),':')-1) AS INTEGER)
      BETWEEN ch.start_line AND ch.end_line'''
    with native_deadline(c):
        rows = list(c.execute(query, (compact(MAPPING_KINDS),)))
    nodes = collections.Counter(n for n, _, _ in rows)
    chunks = collections.Counter(ch for _, ch, _ in rows)
    total = c.execute("SELECT count(*) FROM graph_nodes WHERE json_extract(payload,'$.kind') IN (SELECT value FROM json_each(?))", (compact(MAPPING_KINDS),)).fetchone()[0]
    return {'rule': 'declaration start lies within source chunk range; all overlaps retained',
            'included_kinds': MAPPING_KINDS,
            'pairs': len(rows), 'mapped_symbols': len(nodes), 'unmapped_symbols': total - len(nodes),
            'symbols_with_multiple_chunks': sum(v > 1 for v in nodes.values()),
            'chunks_with_multiple_symbols': sum(v > 1 for v in chunks.values()),
            'source_status': dict(collections.Counter(s for _, _, s in rows)), 'pairs_digest': digest(rows)}


def rebuild(root, variant, run):
    manifest = frozen_manifest(root)
    stage = root / 'lifecycle' / ('stage-' + variant)
    clone_sources(root, stage, manifest)
    path = shared_path(root)
    if variant == 'C':
        initialize_shared(root, path)
    start = time.perf_counter()
    payload, communities, result = producer(root, stage, manifest)
    if variant == 'C':
        prep = prepared_graph(root, stage, payload, communities)
        result['prepare_sql_ms'] = prep['preparation_ms']
        result['writer_lock_ms'] = publish(root, path, prep, run + 1)
    result['source_rebuild_to_publication_ms'] = elapsed(start)
    result.update(variant=variant, run=run, scope='frozen-source graph-only rebuild; no semantic embedding',
                  source_files=len(manifest), source_manifest_sha256=digest(manifest),
                  source_provenance=json.loads((root / 'lifecycle-source-manifest.json').read_text())['semantic_metadata_mismatches'],
                  nodes=len(payload['nodes']), edges=len(payload['edges']),
                  graph_digest=digest(stable(payload)), community_digest=digest(stable(communities)),
                  graph_fingerprint=payload['input_fingerprint'], cluster_algorithm=communities['cluster_algorithm'])
    c = base.connect(path if variant == 'C' else root / '.wavefoundry/index/index-state.sqlite', read_only=True)
    result['semantic_digest'] = semantic_digest(c)
    if variant == 'C':
        assert digest(stable(shared_payload(c))) == result['graph_digest']
        result['mapping'] = mapping(c)
    c.close()
    semantic_bytes = sum(p.stat().st_size for p in (root / '.wavefoundry/index').glob('index-state.sqlite*'))
    result['publication_bytes'] = (sum(p.stat().st_size for p in path.parent.glob('index-state.sqlite*'))
                                   if variant == 'C' else base.directory_bytes(graph_dir(stage)) + semantic_bytes)
    result['publication_bytes_scope'] = 'semantic database plus authoritative graph/state/community, including WAL/SHM; source copy excluded'
    result['stage_bytes'] = base.directory_bytes(stage)
    return result


def fixture_write(root, stage, state):
    caller, provider, guide = [base.owned(root, stage / p) for p in FIXTURE]
    caller.parent.mkdir(parents=True, exist_ok=True)
    if not caller.exists():
        caller.write_text('from lifecycle_fixture.provider import lifecycle_target\n\ndef lifecycle_caller():\n    return lifecycle_target()\n')
    if not guide.exists():
        guide.write_text('# Lifecycle fixture\n\n`lifecycle_target` is invoked by `lifecycle_caller`.\n')
    if state == 'removed':
        if provider.exists():
            provider.unlink()
    elif state == 'renamed':
        provider.write_text('def lifecycle_renamed():\n    return "lifecyclerenamedtoken"\n')
    else:
        provider.write_text('def lifecycle_target():\n    return "lifecycleboundtoken"\n')


def assert_fixture(payload, state):
    declarations = {n['id'] for n in payload['nodes'] if n.get('source_file') == FIXTURE[1]}
    target = FIXTURE[1] + '::lifecycle_target'
    renamed = FIXTURE[1] + '::lifecycle_renamed'
    if state == 'removed':
        assert not declarations, ('orphan provider declarations', declarations)
    elif state == 'renamed':
        assert renamed in declarations and target not in declarations, declarations
    else:
        assert target in declarations and renamed not in declarations, declarations
    edges = [e for e in payload['edges'] if e['source'].endswith('caller.py::lifecycle_caller') and e['relation'] == 'calls']
    assert len(edges) == 1, edges
    expected = ('lifecycle_fixture/provider.py::lifecycle_target' if state == 'bound'
                else 'external::lifecycle_fixture.provider.lifecycle_target')
    assert edges[0]['target'] == expected, (state, edges)
    return edges[0]


def deltas(root):
    manifest = frozen_manifest(root)
    stages = {v: root / 'lifecycle' / ('stage-' + v) for v in ('A', 'C')}
    path = shared_path(root)
    # Rebuild commands leave identical baseline producer states; C is restored
    # from its authoritative SQL rows even on the first mutation.
    outputs = []
    for i in range(10):
        state = ('bound', 'renamed', 'removed', 'bound', 'renamed')[i % 5]
        pair = []
        for variant in ('A', 'C'):
            stage = stages[variant]
            caller = stage / FIXTURE[0]
            old_caller = (base.sha(caller), caller.stat().st_mtime_ns) if caller.exists() else None
            fixture_write(root, stage, state)
            if old_caller is not None:
                assert old_caller == (base.sha(caller), caller.stat().st_mtime_ns)
            start = time.perf_counter()
            restored_ms = restore_stage(root, path, stage) if variant == 'C' else 0
            payload, community, result = producer(root, stage, manifest,
                                                  changed=FIXTURE if i == 0 else [FIXTURE[1]])
            edge = assert_fixture(payload, state)
            if variant == 'C':
                prep = prepared_graph(root, stage, payload, community)
                result['writer_lock_ms'] = publish(root, path, prep, 10 + i)
                result['prepare_sql_ms'] = prep['preparation_ms']
            result.update(variant=variant, run=i, state=state, stage_restore_ms=restored_ms,
                          source_change_to_publication_ms=elapsed(start), fixture_edge=edge,
                          caller_hash_and_mtime_unchanged=old_caller is not None,
                          graph_digest=digest(stable(payload)), community_digest=digest(stable(community)))
            pair.append(result)
            del payload, community
            gc.collect()
        assert pair[0]['graph_digest'] == pair[1]['graph_digest'], 'A/C delta graph mismatch'
        assert pair[0]['community_digest'] == pair[1]['community_digest'], 'A/C delta community mismatch'
        outputs.extend(pair)
        base.dump(root / 'lifecycle-deltas-progress.json', outputs)
    c = base.connect(path, read_only=True)
    semantic = semantic_digest(c)
    c.close()
    # Independent fresh producer rebuild of the final changed source cohort.
    stage = root / 'lifecycle' / 'stage-oracle'
    clone_sources(root, stage, manifest)
    fixture_write(root, stage, state)
    payload, _, _ = producer(root, stage, manifest)
    # Existing clustering can preserve previous IDs; graph identity is the
    # guaranteed differential invariant for incremental versus from-scratch.
    assert digest(stable(payload)) == outputs[-1]['graph_digest'], 'incremental/full graph mismatch'
    return {'status': 'pass', 'samples': outputs, 'semantic_digest': semantic,
            'incremental_full_graph_parity': True, 'reconstructed_from_shared_each_delta': True,
            'scope': 'graph-only source mutation, production global epoch unchanged'}


def reset_deltas(root):
    """Recover both producers from one committed graph after an interrupted trial."""
    manifest = frozen_manifest(root)
    path = shared_path(root)
    results = []
    expected = json.loads((root / 'lifecycle-rebuild-A-2.json').read_text())
    for variant in ('A', 'C'):
        stage = root / 'lifecycle' / ('stage-' + variant)
        restore_stage(root, path, stage)
        fixture_dir = base.owned(root, stage / 'lifecycle_fixture')
        if fixture_dir.exists():
            shutil.rmtree(fixture_dir)
        payload, communities, phases = producer(root, stage, manifest, changed=[])
        assert digest(stable(payload)) == expected['graph_digest'], 'reset did not restore baseline graph'
        results.append({'variant': variant, 'graph_digest': digest(stable(payload)),
                        'community_digest': digest(stable(communities)), 'phases': phases})
        if variant == 'C':
            publish(root, path, prepared_graph(root, stage, payload, communities), 9)
    assert results[0]['community_digest'] == results[1]['community_digest']
    return {'status': 'pass', 'restored_common_baseline': results,
            'reason': 'owned-child RSS monitor observation gap stopped initial delta trial'}


def semantic_spool(root, stage):
    """Real small-file producer using copied offline CPU FP32 model cache."""
    cache = base.owned(root, root / '.wavefoundry/index/evaluation-model-cache/fastembed')
    for entry in cache.rglob('*'):
        if entry.is_symlink():
            base.owned(root, entry)
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      HF_HUB_DISABLE_TELEMETRY='1', FASTEMBED_CACHE_PATH=str(cache))
    from fastembed import TextEmbedding
    started = time.perf_counter()
    embedder = TextEmbedding(model_name=indexer.CODE_MODEL, cache_dir=str(cache),
                             local_files_only=True, providers=['CPUExecutionProvider'], threads=2)
    chunks = [c.to_dict() for c in chunker.chunk_file((stage / FIXTURE[1]).read_text(), FIXTURE[1])]
    vectors = indexer._embed_chunks_for_incremental('lifecycle-fixture', chunks, embedder)
    rows = indexer._make_vector_rows(chunks, vectors)
    spool = vs.PreparedUpdates(index_path(stage))
    spool.add('code', paths=[FIXTURE[1]], rows=rows)
    return spool, {'model': indexer.CODE_MODEL, 'provider': 'CPUExecutionProvider',
                   'precision': 'actual FP32 offline fixture embeddings; explicit provider selection',
                   'chunks': len(chunks), 'vectors_shape': list(vectors.shape),
                   'vectors_sha256': hashlib.sha256(vectors.tobytes()).hexdigest(),
                   'prepare_embed_spool_ms': elapsed(started)}


def participant_view(c):
    publication = list(c.execute('SELECT * FROM graph_publication'))
    records = list(c.execute('SELECT path,source_hash FROM graph_extraction_files WHERE path LIKE ?', ('lifecycle_fixture/%',)))
    nodes = list(c.execute("SELECT payload FROM graph_nodes WHERE json_extract(payload,'$.source_file') LIKE 'lifecycle_fixture/%' ORDER BY ordinal"))
    edges = list(c.execute("SELECT payload FROM graph_edges WHERE json_extract(payload,'$.source') LIKE 'lifecycle_fixture/%' ORDER BY ordinal"))
    chunks = list(c.execute('SELECT chunk_id,text,payload FROM chunks_code WHERE path=? ORDER BY id', (FIXTURE[1],)))
    vectors = [(r[0], hashlib.sha256(bytes(r[1])).hexdigest()) for r in c.execute(
        'SELECT ch.chunk_id,v.embedding FROM chunks_code ch JOIN vectors_code v ON v.chunk_id=ch.id WHERE ch.path=? ORDER BY ch.id', (FIXTURE[1],))]
    fts = c.execute("SELECT count(*) FROM fts_code WHERE fts_code MATCH 'lifecycleboundtoken'").fetchone()[0]
    fts_renamed = c.execute("SELECT count(*) FROM fts_code WHERE fts_code MATCH 'lifecyclerenamedtoken'").fetchone()[0]
    community = hashlib.sha256(bytes(c.execute('SELECT payload FROM graph_community_artifact').fetchone()[0])).hexdigest()
    return {'publication': publication, 'records': records, 'nodes': nodes, 'edges': edges,
            'chunks': chunks, 'vectors': vectors, 'fts': fts, 'fts_renamed': fts_renamed,
            'community': community}


def recovery(root, manifest=None):
    path = shared_path(root)
    stage = root / 'lifecycle' / 'stage-C'
    manifest = frozen_manifest(root) if manifest is None else manifest
    restore_stage(root, path, stage)
    initial_embedding = None
    if manifest:
        # Establish a real prior semantic generation for the full-corpus proof,
        # including safe repetition after a later maintenance observation fails.
        fixture_write(root, stage, 'renamed')
        initial_payload, initial_communities, _ = producer(root, stage, manifest, changed=[FIXTURE[1]])
        assert_fixture(initial_payload, 'renamed')
        initial_spool, initial_embedding = semantic_spool(root, stage)
        try:
            publish(root, path, prepared_graph(root, stage, initial_payload, initial_communities),
                    90, semantic=initial_spool)
        finally:
            initial_spool.__exit__(None, None, None)
    fixture_write(root, stage, 'bound')
    payload, communities, phases = producer(root, stage, manifest, changed=[FIXTURE[1]])
    assert_fixture(payload, 'bound')
    prep = prepared_graph(root, stage, payload, communities)
    spool, embedding = semantic_spool(root, stage)
    reader = base.connect(path, read_only=True)
    old = participant_view(reader)
    try:
        publish(root, path, prep, 100, semantic=spool, action='rollback')
        assert participant_view(reader) == old
        # A spawned crash target drains the very same ACTUAL embedding spool.
        command = [sys.executable, '-B', str(Path(__file__).resolve()), 'crash', '--root', str(root),
                   '--spool', str(spool.path)]
        child = subprocess.run(command, timeout=30,
                               env=dict(os.environ, WAVEFOUNDRY_LIFECYCLE_CRASH_PARENT=str(os.getpid())))
        assert child.returncode == 77, child.returncode
        assert participant_view(reader) == old
        reader.execute('BEGIN')
        assert participant_view(reader) == old
        seen = []
        def observer(phase):
            assert participant_view(reader) == old
            seen.append(phase)
        lock_ms = publish(root, path, prep, 100, semantic=spool, observer=observer)
        reader.execute('COMMIT')
        new = participant_view(reader)
        assert new != old and new['fts'] >= 1 and new['vectors'] and new['records'] != old['records']
        assert new['vectors'] != old['vectors'] and new['fts_renamed'] == 0
        assert new['nodes'] != old['nodes'] and new['edges'] != old['edges']
        assert new['community'] != old['community']
        blob = bytes(reader.execute('SELECT v.embedding FROM vectors_code v JOIN chunks_code ch ON ch.id=v.chunk_id WHERE ch.path=? ORDER BY ch.id LIMIT 1', (FIXTURE[1],)).fetchone()[0])
        actual_vector = struct.unpack('<384f', blob)
        original_open = vs._open
        query_end = time.monotonic() + 5
        def bounded_open(directory):
            connection = original_open(directory)
            connection.set_progress_handler(lambda: time.monotonic() > query_end, 1000)
            return connection
        vs._open = bounded_open
        try:
            with base.query_deadline():
                neighbors = vs.dense_rows(path.parent, 'code', actual_vector, 10)
        finally:
            vs._open = original_open
        assert any(r['path'] == FIXTURE[1] for r in neighbors), 'fresh real vector not retrieved'
        restored_ms = restore_stage(root, path, stage)
        p2, c2, idle = producer(root, stage, manifest, changed=[])
        assert idle['merge']['mode'] == 'zero-change', idle
        assert digest(stable(p2)) == digest(stable(payload))
        assert digest(stable(c2)) == digest(stable(communities))
        query = base.SqlGraph(path)
        try:
            with native_deadline(query.c):
                reached = query.traverse('lifecycle_fixture/caller.py::lifecycle_caller', relations=['calls'], max_hops=1)
            assert 'lifecycle_fixture/provider.py::lifecycle_target' in reached[0]
            assert any(edge['target'] == 'lifecycle_fixture/provider.py::lifecycle_target'
                       and edge['relation'] == 'calls' for edge in reached[1]), 'recovered traversal is empty'
        finally:
            query.close()
    finally:
        reader.close()
        spool.__exit__(None, None, None)
    c = base.connect(path)
    assert c.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
    c.execute("INSERT INTO fts_code(fts_code,rank) VALUES('integrity-check',1)")
    checkpoints = list(c.execute('PRAGMA wal_checkpoint(PASSIVE)'))
    before = {p: c.execute('PRAGMA ' + p).fetchone()[0] for p in ('page_count', 'freelist_count')}
    c.execute('BEGIN IMMEDIATE')
    c.execute('DELETE FROM graph_edges')
    c.execute('COMMIT')
    freed = c.execute('PRAGMA freelist_count').fetchone()[0]
    c.close()
    publish(root, path, prep, 101)
    c = base.connect(path)
    after = {p: c.execute('PRAGMA ' + p).fetchone()[0] for p in ('page_count', 'freelist_count')}
    c.close()
    reuse_proven = (freed > before['freelist_count'] and after['freelist_count'] < freed
                    and after['page_count'] <= before['page_count'])
    return {'status': 'pass', 'embedding': embedding, 'actual_participants': list(new),
            'initial_semantic_embedding': initial_embedding,
            'replaced_existing_semantic_rows': bool(old['vectors']),
            'semantic_operation': 'replacement' if old['vectors'] else 'insertion into previously graph-only fixture',
            'rollback': True, 'crash_exit': child.returncode, 'reader_old_snapshot_phases': seen,
            'writer_lock_ms': lock_ms, 'restart_restore_ms': restored_ms,
            'restart_zero_change_merge': True, 'published_query_digest': digest(base.canonical(reached)),
            'quick_check': 'ok', 'fts_integrity': 'ok', 'checkpoint': checkpoints,
            'native_vector_self_retrieval': {'fixture_in_top10': True, 'minimum_distance': min(r['_distance'] for r in neighbors)},
            'page_reuse': {'before': before, 'after_delete_free': freed, 'after_reinsert': after,
                           'reuse_without_growth_asserted': False, 'reuse_observed': reuse_proven,
                           'status': 'observation-only', 'page_growth': after['page_count'] - before['page_count'],
                           'freed_capacity_consumed': freed > before['freelist_count'] and after['freelist_count'] < freed,
                           'no_growth_gate': 'pass' if after['page_count'] <= before['page_count'] else 'failed'},
            'production_epoch_advanced': False,
            'limits': 'Real tiny code semantic delta plus graph producers; no whole semantic rebuild, build-layer bookkeeping, production epoch/cache API migration, or platform qualification.'}


def fixture_probe(root):
    stage = root / 'lifecycle' / 'stage-C'
    clone_sources(root, stage, {})
    fixture_write(root, stage, 'renamed')
    payload, communities, phases = producer(root, stage, {})
    assert_fixture(payload, 'renamed')
    path = shared_path(root)
    initialize_shared(root, path)
    prep = prepared_graph(root, stage, payload, communities)
    initial_spool, initial_embedding = semantic_spool(root, stage)
    try:
        publish(root, path, prep, 1, semantic=initial_spool)
    finally:
        initial_spool.__exit__(None, None, None)
    result = recovery(root, {})
    result['initial_semantic_embedding'] = initial_embedding
    assert initial_embedding['vectors_sha256'] != result['embedding']['vectors_sha256']
    result['scope'] = 'tiny real source producer and embedding fixture beside complete copied semantic corpus'
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['rebuild', 'deltas', 'reset-deltas', 'recovery', 'fixture', 'crash'])
    ap.add_argument('--root', required=True)
    ap.add_argument('--variant', choices=['A', 'C'], default='A')
    ap.add_argument('--run', type=int, default=0)
    ap.add_argument('--spool')
    args = ap.parse_args()
    root = base.owned(args.root)
    if args.command == 'crash':
        # Only parent-held benchmark process spawns this child; no independent
        # worker/configuration begins and the parent's watchdog counts this PID.
        if not args.spool or os.environ.get('WAVEFOUNDRY_LIFECYCLE_CRASH_PARENT') != str(os.getppid()):
            raise ValueError('owned prepared spool required')
        stage = root / 'lifecycle' / 'stage-C'
        payload = gi._read_json(graph_dir(stage) / 'project-graph.json', {})
        communities = gi._read_json(graph_dir(stage) / 'project-graph-clusters.json', {})
        prep = prepared_graph(root, stage, payload, communities)
        spool = vs.PreparedUpdates.__new__(vs.PreparedUpdates)
        spool.path = base.owned(root, Path(args.spool))
        spool.index_dir = index_path(stage)
        publish(root, shared_path(root), prep, 100, semantic=spool, action='crash')
        return
    lock = (root / '.benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    config = json.loads((root / 'snapshot.json').read_text())
    started_at = calendar.timegm(time.strptime(config['created_at'], '%Y-%m-%dT%H:%M:%SZ'))
    remaining = started_at + 4 * 3600 - time.time()
    if remaining <= 0:
        raise RuntimeError('four-hour original evaluation envelope exhausted')
    stop, watch = base.guard(root, min(1800, remaining))
    temporary = base.owned(root, root / 'lifecycle' / 'temporary')
    temporary.mkdir(parents=True, exist_ok=True)
    os.environ['TMPDIR'] = str(temporary)
    tempfile.tempdir = str(temporary)
    name = 'lifecycle-' + args.command + (f'-{args.variant}-{args.run}' if args.command == 'rebuild' else '')
    cpu_started = time.process_time()
    try:
        result = (rebuild(root, args.variant, args.run) if args.command == 'rebuild'
                  else deltas(root) if args.command == 'deltas'
                  else reset_deltas(root) if args.command == 'reset-deltas'
                  else fixture_probe(root) if args.command == 'fixture' else recovery(root))
        result['worker_cpu_ms'] = (time.process_time() - cpu_started) * 1000
        result['normalization_controls'] = normalization_controls()
        result['watchdog'] = watch
        result['runtime_source_hashes'] = {p: base.sha(base.SCRIPTS / p) for p in
            ('graph_indexer.py', 'graph_cluster.py', 'indexer.py', 'sqlite_vector_store.py', 'index_state_store.py')}
        result['producer_backend'] = 'actual default auto-scaled threads; no ProcessPool'
        result['artifact_comparison_normalization'] = [
            'top-level generated_at/graph_mtime/cluster_mtime/merge_stats only',
            'top-level present must be True when emitted by artifact reader; producer may omit',
            'community artifact betweenness.elapsed_ms only',
            'all node/edge/community semantic attributes retained']
        result['harness_sha256'] = base.sha(Path(__file__).resolve())
        base.dump(root / (name + '.json'), result)
        print(compact(result)[:6000])
    except BaseException as exc:
        base.dump(root / (name + '-failure.json'), {'error': repr(exc), 'watchdog': watch})
        raise
    finally:
        stop.set()


if __name__ == '__main__':
    main()

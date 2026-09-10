"""Disposable paired storage-publication measurements for wave 1xjmm.

Run each lane in a separate interpreter with its frozen scripts directory.
This observes the actual build epoch with deterministic changed-file chunks and embeddings, not model inference or event-to-searchable time.
It never modifies the supplied source corpus. Full public quality and model
latency remain the separate sqlite_conversion_eval measurement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def distribution(values):
    return {"samples": values, "n": len(values),
            "p50_ms": percentile(values, .5), "p95_ms": percentile(values, .95),
            "p95_method": "nearest rank; no p99 inference"}


def file_bytes(path):
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def run(args):
    """Observe the real build epoch, never reproduce its publication algorithm."""
    import struct
    import ast
    from unittest.mock import patch
    sys.path.insert(0, str(args.runtime.resolve()))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import indexer
    state = indexer._get_index_state_store()
    import numpy as np
    import apsw
    import platform
    import importlib.metadata

    target = args.work.resolve()
    source = args.source.resolve()
    if target == source or target in source.parents:
        raise RuntimeError("Disposable work tree must differ from source")
    # Preserve the full indexed filesystem. Exclude only transient ownership
    # records and backup the semantic SQLite main/WAL through its native API.
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(
        "index-state.sqlite", "index-state.sqlite-wal", "index-state.sqlite-shm",
        "index-build.lock", "upgrade-in-progress.json", "sqlite-migration.json",
        "__pycache__", "*.pyc"))
    index_dir = target / ".wavefoundry/index"
    source_index = source / ".wavefoundry/index"
    old = apsw.Connection(str(source_index / "index-state.sqlite"), flags=apsw.SQLITE_OPEN_READONLY)
    new = apsw.Connection(str(index_dir / "index-state.sqlite"))
    try:
        with new.backup("main", old, "main") as backup:
            while not backup.done:
                backup.step(256)
    finally:
        new.close()
        old.close()
    if args.lane == "sqlite":
        import sqlite_vector_store as vectors
    else:
        vectors = None

    path = "docs/benchmark-prepared-update.md"
    source_file = target / path
    source_file.parent.mkdir(parents=True, exist_ok=True)
    vector = np.zeros(384, dtype=np.float32)
    vector[0] = 1
    vector_bytes = struct.pack("<384f", *vector)
    metadata = state.export_meta_snapshot(index_dir)
    if not metadata:
        raise RuntimeError("Published frozen source metadata required")

    def all_rows(layer):
        if vectors is not None:
            return vectors.payload_rows(index_dir, layer, include_vector=True)
        table = indexer._get_lance_db(index_dir).open_table(layer)
        return table.search().limit(table.count_rows()).to_list()

    def target_rows():
        if vectors is not None:
            return vectors.payload_rows(index_dir, "docs", "path = '" + path + "'", include_vector=True)
        return indexer._get_lance_db(index_dir).open_table("docs").search().where(
            "path = '" + path + "'").limit(100_000).to_list()

    def row_digest(rows):
        checksum = hashlib.sha256()
        for row in sorted(rows, key=lambda r: str(r["id"])):
            payload = {key: value for key, value in row.items() if key != "vector"}
            encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
            blob = struct.pack("<384f", *row["vector"])
            for value in (encoded, blob):
                checksum.update(len(value).to_bytes(8, "big"))
                checksum.update(value)
        return checksum.hexdigest()

    def unaffected():
        result = {}
        for layer in ("docs", "code"):
            rows = [row for row in all_rows(layer) if row["path"] != path]
            result[layer] = {"rows": len(rows), "unique_ids": len({row['id'] for row in rows}),
                             "sha256": row_digest(rows)}
        return result

    initial_identity = unaffected()
    logical_metadata = {key: metadata.get(key) for key in ('model_versions', 'chunker_versions', 'walker_version', 'content')}
    logical_metadata['file_hashes'] = {name: values.get('hash') for name, values in metadata['file_meta'].items()}
    metadata_identity = hashlib.sha256(json.dumps(logical_metadata, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    template = min(all_rows("docs"), key=lambda row: str(row["id"]))
    template.pop("vector", None)
    template.pop("chunk_hash", None)
    active = {"rows": [], "expected": [], "timer": None, "token": None,
              "starts": 0, "finishes": 0, "chunk_calls": 0, "embedded": 0}
    original_chunks = indexer._chunks_for_file
    original_begin = state.begin_build_epoch
    original_finalize = state.finalize_build_epoch
    original_store = state.IndexStateStore
    publication_site = None
    if vectors is not None:
        tree = ast.parse(Path(indexer.__file__).read_text())
        build = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_build_index_locked')
        sites = [node.lineno for node in ast.walk(build) if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == 'store' for target in node.targets)
                 and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute)
                 and node.value.func.attr == 'IndexStateStore'
                 and isinstance(node.value.func.value, ast.Name) and node.value.func.value.id == '_state_store']
        if len(sites) != 1:
            raise RuntimeError('Actual semantic publication callsite is no longer unique; review boundary')
        publication_site = sites[0]

    class ObservedStore(original_store):
        def __init__(self, *values, **options):
            caller = sys._getframe(1)
            if (vectors is not None and caller.f_code is indexer._build_index_locked.__code__
                    and caller.f_lineno == publication_site):
                if active.get('semantic_start') is not None:
                    raise RuntimeError('Actual semantic publication started more than once')
                active['semantic_start'] = time.perf_counter()
            super().__init__(*values, **options)

    legacy_write = getattr(indexer, '_lance_incremental_write', None)
    def observed_legacy_write(*values, **options):
        if active.get('semantic_start') is not None:
            raise RuntimeError('Unexpected multiple prepared legacy layer writes')
        active['semantic_start'] = time.perf_counter()
        return legacy_write(*values, **options)

    def chunks(relative, text):
        if relative != path:
            return original_chunks(relative, text)
        if text != source_file.read_text():
            raise RuntimeError("Prepared chunk source differs from actual filesystem")
        active["chunk_calls"] += 1
        return [dict(row) for row in active["rows"]], []

    class PreparedEmbedder:
        def embed(self, texts, **kwargs):
            values = list(texts)
            active["embedded"] += len(values)
            for _ in values:
                yield vector.copy()

    def begin(*values, **options):
        active["starts"] += 1
        if active["starts"] != 1:
            raise RuntimeError("Expected one actual build epoch per file update")
        active["timer"] = time.perf_counter()
        token = original_begin(*values, **options)
        active["token"] = token
        return token

    def finalize(*values, **options):
        result = original_finalize(*values, **options)
        if result:
            active["finishes"] += 1
            finished = time.perf_counter()
            active["publication_ms"] = (finished - active["timer"]) * 1000
            if active.get('semantic_start') is None:
                raise RuntimeError('Semantic publication observation was not reached')
            active['semantic_publication_ms'] = (finished - active['semantic_start']) * 1000
        return result

    report = {
        "lane": args.lane, "scope": "Actual indexer.build_index with separately observed full-epoch and semantic-publication intervals",
        "source": str(source), "runtime": str(args.runtime.resolve()),
        "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_hashes": {name: hashlib.sha256((args.runtime / name).read_bytes()).hexdigest()
                          for name in ("indexer.py", "index_state_store.py")},
        "dimensions": 384, "representation": "float32", "repetitions": args.repetitions,
        "preparation": "Deterministic changed-file chunks and finite384D embeddings replace chunk/model inference only; actual filesystem hashes, source/model guards, vector integrity, reconciliation, provenance and final CAS remain production code",
        "timer": "Common actual epoch boundary; includes fences, normal vector packing/preparation, mandatory residents and finalization. Scan/chunk generation before begin and independent oracles after finalize are excluded.",
        "semantic_timer": ("Actual publication-store constructor after graph, including attempt/source/model validation, vector integrity, reconciliation, provenance and successful final CAS" if vectors is not None else "Actual _lance_incremental_write entry through final CAS; includes legacy in-function delta preparation and deterministic embedding conversion"),
        "semantic_publication_source_line": publication_site,
        "initial_unaffected_identity": initial_identity, "initial_logical_metadata_sha256": metadata_identity,
        "batches": {}, "status": "running",
        "runtime_identity": {"python": platform.python_version(), "platform": platform.platform(),
            "machine": platform.machine(), "sqlite": apsw.sqlitelibversion() if vectors is not None else __import__('sqlite3').sqlite_version,
            "packages": {name: importlib.metadata.version(name) for name in
                         (("apsw", "sqlite-vec") if vectors is not None else ("lancedb",))}},
    }
    previous_ids, previous_token = set(), None

    def perform(count, iteration):
        nonlocal previous_ids, previous_token
        token = f"publication_{count}_{iteration}"
        rows = [{**template, "id": f"prepared-{count}-{iteration}-{number}", "path": path,
                 "kind": "doc", "language": "", "section": "prepared publication",
                 "text": token + f" chunk {number} " + "prepared publication measurement " * 12,
                 "lines": [number + 1, number + 1]}
                for number in range(count)]
        source_file.write_text("\n".join(row["text"] for row in rows) + "\n")
        expected = []
        for row in rows:
            value = dict(row)
            hash_fields = {key: (str(value.get(key) or "") if key != "tags" else value.get(key) or [])
                           for key in ("kind", "language", "section", "text", "tags")}
            value["chunk_hash"] = hashlib.sha256(json.dumps(hash_fields, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if isinstance(value.get("tags"), list):
                value["tags"] = " ".join(str(tag) for tag in value["tags"])
            value["vector"] = vector.tolist()
            expected.append(value)
        active.update(rows=rows, expected=expected, timer=None, token=None, starts=0,
                      finishes=0, chunk_calls=0, embedded=0, publication_ms=None, semantic_start=None, semantic_publication_ms=None)
        wall_start = time.perf_counter()
        result = indexer.build_index(target, content="docs")
        full_build_ms = (time.perf_counter() - wall_start) * 1000
        if result.get("error") or result.get("failed") or active["starts"] != 1 or active["finishes"] != 1:
            raise RuntimeError("Actual publication failed or missed epoch instrumentation: " + json.dumps(result, default=str))
        if active["chunk_calls"] != 1 or active["embedded"] != count:
            raise RuntimeError(f"Prepared-row invocation mismatch: chunk_calls={active['chunk_calls']}, embedded={active['embedded']}, expected={count}")
        # All oracles run outside the publication timer and use independently
        # keyed rows, not aggregate counts or the production reconciliation result.
        observed = target_rows()
        keyed = {row["id"]: row for row in observed}
        expected_keyed = {row["id"]: row for row in expected}
        if len(keyed) != len(observed) or keyed != expected_keyed:
            raise RuntimeError("Exact keyed payload/vector oracle failed")
        if any(struct.pack("<384f", *row["vector"]) != vector_bytes for row in observed):
            raise RuntimeError("FP32 vector-byte oracle failed")
        conn = state.open_read_only(index_dir)
        try:
            registry = dict(conn.execute("SELECT chunk_id,chunk_hash FROM chunk_registry WHERE table_name='docs' AND path=?", (path,)))
            expected_registry = {row["id"]: row["chunk_hash"] for row in expected}
            if registry != expected_registry:
                raise RuntimeError("Exact keyed registry oracle failed")
            current_hash = hashlib.sha256(source_file.read_bytes()).hexdigest()
            layer_hash = conn.execute("SELECT hash FROM layer_path_state WHERE layer='docs' AND path=?", (path,)).fetchone()
            if layer_hash != (current_hash,):
                raise RuntimeError("Layer source hash failed to publish")
            if vectors is not None:
                for layer in ("docs", "code"):
                    population = vectors.vector_integrity(conn, layer)
                    if population["missing_vectors"] or population["orphan_vectors"]:
                        raise RuntimeError("Native vector integrity oracle failed")
        finally:
            conn.close()
        committed = state.export_meta_snapshot(index_dir)
        file_meta = committed["file_meta"][path]
        if file_meta["hash"] != current_hash or file_meta["chunks_emitted"] != count:
            raise RuntimeError("Canonical file bookkeeping oracle failed")
        if committed["model_versions"] != metadata["model_versions"]:
            raise RuntimeError("Model provenance changed during prepared update")
        epoch = state.read_build_state(index_dir)
        if epoch["status"] != "complete" or epoch["attempt_id"] != active["token"]:
            raise RuntimeError("Actual final provenance token was not published")
        if not state.fts_search(index_dir, "docs", token, limit=5):
            raise RuntimeError("Committed content is not searchable")
        if previous_token and state.fts_search(index_dir, "docs", previous_token, limit=1):
            raise RuntimeError("Obsolete FTS tokens remain searchable")
        if previous_ids & set(keyed):
            raise RuntimeError("Obsolete keyed rows remain")
        if unaffected() != initial_identity:
            raise RuntimeError("Unchanged corpus payload/vector identity drifted")
        previous_ids, previous_token = set(keyed), token
        record = {"publication_ms": active["publication_ms"], "semantic_publication_ms": active["semantic_publication_ms"], "full_build_ms": full_build_ms,
                  "attempt_id": active["token"], "generation": epoch["generation"],
                  "keyed_rows_sha256": row_digest(observed), "exact_oracles_passed": True,
                  "chunks": count, "embedded_vectors": active["embedded"]}
        print(json.dumps({"lane": args.lane, "batch": count, "iteration": iteration, **record}), flush=True)
        return record

    from contextlib import ExitStack
    try:
        with ExitStack() as observers, patch.object(indexer, '_chunks_for_file', chunks), patch.object(
            indexer, '_get_embedder', return_value=PreparedEmbedder()
        ), patch.object(indexer, '_predicted_precision_class', return_value='full'), patch.object(
            state, 'begin_build_epoch', begin
        ), patch.object(state, 'finalize_build_epoch', finalize):
            observers.enter_context(patch.object(state, 'IndexStateStore', ObservedStore))
            if legacy_write is not None:
                observers.enter_context(patch.object(indexer, '_lance_incremental_write', observed_legacy_write))
            report['unmeasured_priming'] = perform(3, 'prime')
            for count in args.counts:
                records = [perform(count, iteration) for iteration in range(args.repetitions)]
                timings = [row['semantic_publication_ms'] for row in records]
                full_epoch = [row['publication_ms'] for row in records]
                report['batches'][str(count)] = {
                    'records': records, 'full_epoch_including_fences': distribution(full_epoch),
                    'semantic_publication': distribution(timings),
                    'under_1000ms_p95': percentile(timings, .95) < 1000,
                    'actual_production_boundary': True,
                }
                (target / 'result.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
        report['status'] = 'measured'
        report['publication_budget_passed'] = all(row['under_1000ms_p95'] for row in report['batches'].values())
    finally:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        report['process_peak_rss_bytes'] = rss if sys.platform == 'darwin' else rss * 1024
        report['rss_scope'] = 'Whole measurement worker including clone and exact full-corpus oracles; not query RSS'
        (target / 'result.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(json.dumps({'lane': args.lane, 'status': report['status'], 'result': str(target / 'result.json')}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=("baseline", "sqlite"), required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--counts", type=lambda value: [int(part) for part in value.split(",")], default=[10, 50, 250, 1000])
    parser.add_argument("--repetitions", type=int, default=5)
    run(parser.parse_args())

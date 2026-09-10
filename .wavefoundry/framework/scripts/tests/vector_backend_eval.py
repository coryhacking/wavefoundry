"""Development-only, isolated vector-store comparison; never opens a live index.

Queries use stored vectors plus deterministic noise, not user relevance judgments.
First-query timings follow build and roundtrip reads; these are NOT cold. All timed results hydrate the
same JSON payload. No adapter or schema here is a proposed production integration.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sqlite3
import statistics
import subprocess
import sys
import time

import numpy as np

TOLERANCE = 1e-5


def exact_reference(vectors, query, eligible_indices, k):
    """Independent float64 cosine oracle: ordered (physical rid, distance)."""
    indices = np.asarray(list(eligible_indices), dtype=np.int64)
    if k < 0:
        raise ValueError("k must be nonnegative")
    if not len(indices) or not k:
        return []
    matrix = np.asarray(vectors, dtype=np.float64)[indices]
    q = np.asarray(query, dtype=np.float64)
    if not np.isfinite(matrix).all() or not np.isfinite(q).all():
        raise ValueError("cosine oracle requires finite vectors and query")
    denominator = np.linalg.norm(matrix, axis=1) * np.linalg.norm(q)
    if np.any(denominator == 0):
        raise ValueError("zero vector has undefined cosine")
    distances = 1 - (matrix @ q) / denominator
    order = np.lexsort((indices, distances))[:k]
    return [(int(indices[i]), float(distances[i])) for i in order]


def assess_rows(results, reference, *, eligible_indices, expected_count, tolerance=TOLERANCE):
    """Validate complete oracle membership/scores; reference must include all eligible rows.

    Results may be (rid, distance) tuples or dictionaries with those keys. Boundary
    ties are accepted, but missing any strictly closer row is a failure.
    """
    actual = [(int(r['rid']), float(r['distance'])) if isinstance(r, dict)
              else (int(r[0]), float(r[1])) for r in results]
    oracle = dict(reference)
    eligible = set(eligible_indices)
    errors = []
    ids = [rid for rid, _ in actual]
    if len(actual) != expected_count:
        errors.append("result_count")
    if len(set(ids)) != len(ids):
        errors.append("duplicate_physical_rid")
    if not set(ids) <= eligible:
        errors.append("filter_violation")
    for rid, distance in actual:
        if rid not in oracle or not math.isfinite(distance) or abs(distance - oracle.get(rid, 0)) > tolerance:
            errors.append("distance_mismatch")
            break
    expected = sorted(reference, key=lambda r: (r[1], r[0]))[:expected_count]
    if expected:
        boundary = expected[-1][1]
        required = {rid for rid, distance in reference if distance < boundary - tolerance}
        allowed = {rid for rid, distance in reference if distance <= boundary + tolerance}
        if not required <= set(ids) or not set(ids) <= allowed:
            errors.append("nearest_set_mismatch")
    overlap = len(set(ids) & {r[0] for r in expected}) / len(expected) if expected else 1.0
    return {"ok": not errors, "errors": errors, "exact_overlap": overlap,
            "contract_ok": not any(e != "nearest_set_mismatch" for e in errors),
            "nearest_set_ok": "nearest_set_mismatch" not in errors}


def load_corpus(source, scale=1):
    rng = np.random.default_rng(1827)
    if source == "synthetic":
        vectors = rng.normal(size=(512, 384)).astype(np.float32)
        vectors[1] = vectors[0]  # exact tie, different physical rows
        payloads = [{"id": f"chunk-{i // 2}", "path": f"src/{i % 37}.py",
                     "kind": "code" if i % 2 else "doc", "language": "python" if i % 3 else "rust",
                     "tags": "alpha beta" if i % 5 else "owner's gamma", "text": f"fixture text {i}",
                     "lines": list(range(i % 7)), "section": "", "chunk_hash": f"hash-{i}"}
                    for i in range(512)]
    else:
        import pyarrow as pa
        with pa.memory_map(str(source), "r") as stream:
            table = pa.ipc.open_file(stream).read_all()
        records = table.to_pylist()
        vectors = np.asarray([r.pop("vector") for r in records], dtype=np.float32)
        payloads = records
    if scale not in (1, 2):
        raise ValueError("scale must be 1 or 2")
    if scale == 2:
        copies = [dict(p, id=str(p.get("id", "")) + "::growth") for p in payloads]
        payloads += copies
        vectors = np.concatenate([vectors, vectors])
    rows = []
    for rid, p in enumerate(payloads):
        p = dict(p)
        for field in ("path", "kind", "language", "tags"):
            value = p.get(field) or ""
            p[field] = " ".join(map(str, value)) if isinstance(value, list) else str(value)
        rows.append({"rid": rid, **{f: p[f] for f in ("path", "kind", "language", "tags")},
                     "payload": json.dumps(p, sort_keys=True, separators=(",", ":"))})
    if vectors.ndim != 2 or len(rows) != len(vectors) or not np.isfinite(vectors).all():
        raise ValueError("invalid corpus vectors")
    return rows, vectors


def query_slices(rows, vectors):
    """SQL/reference predicates are separately expressed; all fixtures are fixed."""
    quote = lambda s: "'" + s.replace("'", "''") + "'"
    kind, language = rows[0]["kind"], rows[0]["language"]
    cases = [
        ("unfiltered", "", lambda r: True, False, 40),
        ("kind", f"kind = {quote(kind)}", lambda r: r["kind"] == kind, False, 40),
        ("language", f"language = {quote(language)}", lambda r: r["language"] == language, False, 40),
        ("combined", f"kind = {quote(kind)} AND language = {quote(language)}", lambda r: r["kind"] == kind and r["language"] == language, False, 40),
        ("or_tags", "(tags LIKE '%alpha%' OR tags LIKE '%gamma%')", lambda r: "alpha" in r["tags"] or "gamma" in r["tags"], True, 40),
        ("quote", "tags LIKE '%owner''s%'", lambda r: "owner's" in r["tags"], True, 40),
        ("empty", "kind = '__absent_kind__'", lambda r: r["kind"] == "__absent_kind__", False, 40),
        ("large_k", "", lambda r: True, False, 240),
        ("tie", "", lambda r: True, False, 1),
    ]
    rng = np.random.default_rng(957)
    out = []
    for name, sql, predicate, complex_filter, k in cases:
        q = vectors[0].copy() if name == "tie" else (vectors[17 % len(vectors)] + rng.normal(0, .005, vectors.shape[1])).astype(np.float32)
        out.append(dict(name=name, sql=sql, complex=complex_filter, k=k, vector=q,
                        eligible=[r["rid"] for r in rows if predicate(r)]))
    return out


class Store:
    def __init__(self, backend, path, dimensions, *, existing=False):
        self.backend, self.path, self.dimensions = backend, Path(path), dimensions
        if backend.startswith("lance"):
            import lancedb
            self.db = lancedb.connect(str(path))
            self.table = self.db.open_table("vectors") if existing else None
        else:
            self.db = self.connect()
            if existing:
                return
            self.db.execute("PRAGMA journal_mode=WAL")
            if backend == "sqlite":
                self.db.execute(f"CREATE VIRTUAL TABLE vectors USING vec0(rid INTEGER PRIMARY KEY, vector FLOAT[{dimensions}] distance_metric=cosine, kind TEXT, language TEXT, +tags TEXT, +path TEXT, +payload TEXT)")
            else:
                self.db.execute("CREATE TABLE vectors(rid INTEGER PRIMARY KEY, vector BLOB, kind TEXT, language TEXT, tags TEXT, path TEXT, payload TEXT)")

    def connect(self):
        import sqlite_vec
        conn = sqlite3.connect(self.path, timeout=.05)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return conn

    def add(self, rows, vectors):
        if self.backend.startswith("lance"):
            data = [dict(r, vector=v.tolist()) for r, v in zip(rows, vectors)]
            if self.table is None:
                self.table = self.db.create_table("vectors", data=data)
            else:
                self.table.add(data)
        else:
            self.db.executemany("INSERT INTO vectors(rid,vector,kind,language,tags,path,payload) VALUES(?,?,?,?,?,?,?)",
                                [(r["rid"], np.asarray(v, dtype=np.float32).tobytes(), r["kind"], r["language"], r["tags"], r["path"], r["payload"]) for r, v in zip(rows, vectors)])
            self.db.commit()

    def delete(self, rid):
        if self.backend.startswith("lance"):
            self.table.delete(f"rid = {int(rid)}")
        else:
            self.db.execute("DELETE FROM vectors WHERE rid=?", (rid,))
            self.db.commit()

    def maintain(self):
        if self.backend.startswith("lance"):
            from datetime import timedelta
            self.table.optimize(cleanup_older_than=timedelta(0))
            if self.backend != "lance-flat" and self.table.count_rows() >= 1000:
                self.table.create_index(metric="cosine", index_type="IVF_HNSW_SQ", replace=True)
        else:
            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.db.execute("VACUUM")

    def search(self, case):
        q = case["vector"]
        if self.backend.startswith("lance"):
            query = self.table.search(q.tolist()).metric("cosine").limit(case["k"]).refine_factor(2)
            if self.backend in ("lance-exact", "lance-flat"):
                query = query.bypass_vector_index()
            if case["sql"]:
                query = query.where(case["sql"], prefilter=True)
            raw = query.to_list()
            return [{"rid": int(r["rid"]), "distance": float(r["_distance"]),
                     "score": 1 - float(r["_distance"]), "payload": json.loads(r["payload"])} for r in raw]
        blob = np.asarray(q, dtype=np.float32).tobytes()
        if self.backend == "sqlite" and not case["complex"]:
            sql = "SELECT rid,distance,payload FROM vectors WHERE vector MATCH ? AND k = ?"
            if case["sql"]:
                sql += " AND " + case["sql"]
            sql += " ORDER BY distance"
            args = (blob, case["k"])
        else:
            sql = "SELECT rid,vec_distance_cosine(vector, ?) AS distance,payload FROM vectors"
            if case["sql"]:
                sql += " WHERE " + case["sql"]
            sql += " ORDER BY distance, rid LIMIT ?"
            args = (blob, case["k"])
        return [{"rid": int(rid), "distance": float(distance), "score": 1-float(distance),
                 "payload": json.loads(payload)} for rid, distance, payload in self.db.execute(sql, args).fetchall()]

    def snapshot(self):
        if self.backend.startswith("lance"):
            return {r["rid"]: (r["payload"], np.asarray(r["vector"], dtype=np.float32).tobytes()) for r in self.table.to_arrow().to_pylist()}
        return {rid: (payload, vector) for rid, payload, vector in self.db.execute("SELECT rid,payload,vector FROM vectors").fetchall()}

    def reopen(self):
        if self.backend.startswith("lance"):
            import lancedb
            self.db = lancedb.connect(str(self.path))
            self.table = self.db.open_table("vectors")
        else:
            self.db.close()
            self.db = self.connect()


def _sqlite_probe_mutation(conn, mode):
    """Mutate a disposable store inside the caller's uncommitted transaction."""
    if mode not in ("insert", "replace", "delete"):
        raise ValueError("unknown probe mutation")
    row = list(conn.execute("SELECT rid,vector,kind,language,tags,path,payload FROM vectors WHERE rid=0").fetchone())
    if mode == "delete":
        conn.execute("DELETE FROM vectors WHERE rid=0")
        return
    if mode == "replace":
        conn.execute("DELETE FROM vectors WHERE rid=0")
    else:
        row[0] = conn.execute("SELECT max(rid)+1 FROM vectors").fetchone()[0]
    vector = np.frombuffer(row[1], dtype=np.float32).copy()
    vector[0] += np.float32(.125)
    row[1] = vector.tobytes()
    payload = json.loads(row[6])
    payload["probe_uncommitted"] = mode
    row[6] = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    conn.execute("INSERT INTO vectors(rid,vector,kind,language,tags,path,payload) VALUES(?,?,?,?,?,?,?)", row)


def sqlite_failure_probes(store):
    """Exercise insert/replace/delete rollback, reader isolation, busy and exit."""
    expected = store.snapshot()
    mutations = {}
    for mode in ("insert", "replace", "delete"):
        store.db.execute("BEGIN IMMEDIATE")
        _sqlite_probe_mutation(store.db, mode)
        assert store.snapshot() != expected, f"{mode} probe did not change private state"
        reader = store.connect()
        observed = {rid: (payload, vector) for rid, payload, vector in reader.execute("SELECT rid,payload,vector FROM vectors")}
        assert observed == expected, f"reader saw uncommitted {mode}"
        reader.close()
        store.db.rollback()
        assert store.snapshot() == expected, f"{mode} rollback changed rows"
        script = (
            "import sqlite3,sqlite_vec,os,sys; sys.path.insert(0,sys.argv[3]); "
            "from vector_backend_eval import _sqlite_probe_mutation; "
            "c=sqlite3.connect(sys.argv[1]); c.enable_load_extension(True); sqlite_vec.load(c); "
            "c.enable_load_extension(False); c.execute('BEGIN IMMEDIATE'); "
            "_sqlite_probe_mutation(c,sys.argv[2]); os._exit(0)"
        )
        subprocess.run([sys.executable, "-B", "-c", script, str(store.path), mode, str(Path(__file__).resolve().parent)], check=True, timeout=15)
        store.reopen()
        assert store.snapshot() == expected, f"{mode} process exit changed committed state"
        mutations[mode] = {"rollback": "passed", "reader_snapshot": "passed", "process_exit_before_commit": "passed"}
    reader = store.connect()
    store.db.execute("BEGIN IMMEDIATE")
    started = time.perf_counter()
    try:
        reader.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as exc:
        if "locked" not in str(exc).lower():
            raise
    else:
        raise AssertionError("second writer unexpectedly admitted")
    wait_ms = (time.perf_counter() - started) * 1000
    store.db.rollback()
    reader.execute("BEGIN IMMEDIATE")
    reader.rollback()
    reader.close()
    assert store.snapshot() == expected, "contention changed rows"
    return {"rollback": "passed", "reader_during_write": "passed", "busy_timeout_ms": wait_ms,
            "writer_after_release": "passed", "process_exit_before_commit": "passed", "mutations": mutations,
            "scope": "isolated insert, same-rid replacement with changed vector/payload, delete; no integration publication claim"}


def elapsed(call):
    start = time.perf_counter()
    value = call()
    return value, (time.perf_counter()-start)*1000


def sizes(path):
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file())


def run(args):
    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=False)
    result = {"backend": args.backend, "source": args.source, "scale": args.scale,
              "status": "running", "timing_scope": "hydrated payload; first-query-after-build (after snapshot/oracle); OS cache not flushed",
              "cold_startup": {"status": "not_run", "reason": "requires separate fresh-process probe; first-query-after-build is not cold"},
              "resource_scope": "whole harness including retained input corpus, Arrow conversion, float64 oracle and roundtrip snapshots; not backend-only RSS",
              "relevance_scope": "stored vector plus noise; public relevance evaluation separate"}
    try:
        rows, vectors = load_corpus(args.source, args.scale)
        result.update(rows=len(rows), dimensions=vectors.shape[1],
                      vector_hash=hashlib.sha256(vectors.tobytes()).hexdigest(),
                      payload_hash=hashlib.sha256("".join(r["payload"] for r in rows).encode()).hexdigest(),
                      versions={name: importlib.metadata.version(name) for name in ("numpy", "pyarrow", "lancedb" if args.backend.startswith("lance") else "sqlite-vec")},
                      python=sys.version, sqlite=sqlite3.sqlite_version)
        store, result["open_ms"] = elapsed(lambda: Store(args.backend, work / ("lance" if args.backend.startswith("lance") else "vectors.db"), vectors.shape[1]))
        _, result["storage_build_ms"] = elapsed(lambda: store.add(rows, vectors))
        _, result["initial_maintenance_ms"] = elapsed(store.maintain)
        expected = {r["rid"]: (r["payload"], v.tobytes()) for r, v in zip(rows, vectors)}
        assert store.snapshot() == expected, "vector/payload roundtrip mismatch"
        result["roundtrip"] = "passed"
        result["queries"] = []
        for case in query_slices(rows, vectors):
            reference = exact_reference(vectors, case["vector"], case["eligible"], len(case["eligible"]))
            first, cold_ms = elapsed(lambda: store.search(case))
            checks = assess_rows(first, reference, eligible_indices=case["eligible"], expected_count=min(case["k"], len(case["eligible"])))
            timings = []
            for iteration in range(9):
                found, ms = elapsed(lambda: store.search(case))
                current = assess_rows(found, reference, eligible_indices=case["eligible"], expected_count=min(case["k"], len(case["eligible"])))
                if current != checks:
                    checks = dict(ok=False, errors=["unstable_results", *current["errors"]], exact_overlap=current["exact_overlap"],
                                  contract_ok=False, nearest_set_ok=current["nearest_set_ok"])
                assert all(r["payload"] == json.loads(rows[r["rid"]]["payload"]) for r in found), "hydrated payload mismatch"
                if iteration >= 2:
                    timings.append(ms)
            result["queries"].append(dict(name=case["name"], eligible=len(case["eligible"]), k=case["k"], first_query_after_build_ms=cold_ms,
                                          median_ms=statistics.median(timings), p95_ms=sorted(timings)[math.ceil(.95*len(timings))-1], samples_ms=timings, **checks))
        result["churn"] = []
        for cycle in range(10):
            extra = dict(rows[0], rid=len(rows))
            _, update_ms = elapsed(lambda: store.add([extra], vectors[:1]))
            _, delete_ms = elapsed(lambda: store.delete(len(rows)))
            _, maintenance_ms = elapsed(store.maintain)
            store.reopen()
            assert store.snapshot() == expected, "maintenance/reopen changed live rows"
            result["churn"].append(dict(cycle=cycle, update_ms=update_ms, delete_ms=delete_ms, maintenance_ms=maintenance_ms, bytes=sizes(work)))
        result["failure_probes"] = sqlite_failure_probes(store) if not args.backend.startswith("lance") else {"status": "not_run", "reason": "transaction/process probes require separate Lance-specific harness"}
        result["post_maintenance_bytes"] = sizes(work)
        try:
            import resource
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            result["peak_rss_bytes"] = rss if sys.platform == "darwin" else rss*1024
        except ImportError:
            result["peak_rss_bytes"] = None
        result["status"] = "passed" if all(q["ok"] for q in result["queries"]) else "correctness_failed"
    except Exception as exc:
        result.update(status="error", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        (work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def run_build_resources(args):
    """Stream identical prepared batches; capture build peak before oracle snapshots."""
    import resource
    import threading

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=False)
    source = Path(args.resource_source)
    vectors = np.load(source / "vectors.npy", mmap_mode="r")
    result = {"backend": args.backend, "status": "running", "rows": len(vectors),
              "batch_size": 512, "resource_scope": "fresh build process, numpy mmap input and 512-row metadata batches; peak captured before verification snapshots; no embedder/reranker",
              "disk_scope": "logical visible work-directory files sampled every 10ms; lower bound excluding unlinked/out-of-tree temporary files and shorter peaks; prepared input excluded; final_store_bytes is before connection close and may include WAL",
              "prepared_input_bytes": sizes(source)}
    stop = threading.Event()
    samples = []

    def sample():
        total = 0
        for path in work.rglob("*"):
            try:
                if path.is_file():
                    total += path.stat().st_size
            except FileNotFoundError:
                pass  # Reclamation may remove a file between enumeration and stat.
        samples.append(total)

    def monitor():
        while not stop.wait(.01):
            sample()

    watcher = threading.Thread(target=monitor, daemon=True)
    watcher.start()
    try:
        store = Store(args.backend, work / ("lance" if args.backend.startswith("lance") else "vectors.db"), vectors.shape[1])
        started = time.perf_counter()
        batch, offset = [], 0
        with (source / "rows.jsonl").open() as stream:
            for line in stream:
                batch.append(json.loads(line))
                if len(batch) == 512:
                    store.add(batch, vectors[offset:offset+len(batch)])
                    offset += len(batch)
                    batch = []
            if batch:
                store.add(batch, vectors[offset:offset+len(batch)])
                offset += len(batch)
        assert offset == len(vectors), "prepared row/vector count mismatch"
        result["streamed_build_ms"] = (time.perf_counter()-started)*1000
        _, result["maintenance_ms"] = elapsed(store.maintain)
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["build_peak_rss_bytes"] = rss if sys.platform == "darwin" else rss*1024
        stop.set()
        watcher.join()
        sample()
        result.update(sampled_peak_store_bytes=max(samples), disk_samples=len(samples), final_store_bytes=sizes(work))
        # Capture above first: these full keyed comparisons are verification, not build memory.
        with (source / "rows.jsonl").open() as stream:
            expected = {r["rid"]: (r["payload"], vectors[i].tobytes())
                        for i, line in enumerate(stream) for r in [json.loads(line)]}
        assert store.snapshot() == expected, "streamed build roundtrip mismatch"
        store.reopen()
        assert store.snapshot() == expected, "streamed build reopen mismatch"
        result["status"] = "passed"
    except Exception as exc:
        result.update(status="error", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        stop.set()
        watcher.join()
        (work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("lance", "lance-exact", "lance-flat", "sqlite", "sqlite-scalar"), required=True)
    parser.add_argument("--source", default="synthetic")
    parser.add_argument("--scale", type=int, choices=(1, 2), default=1)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--resource-source", help="prepared vectors.npy and rows.jsonl directory for isolated build resources")
    args = parser.parse_args()
    result = run_build_resources(args) if args.resource_source else run(args)
    print(json.dumps({"status": result["status"], "rows": result["rows"]}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

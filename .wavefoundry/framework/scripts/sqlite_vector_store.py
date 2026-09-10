"""Canonical text, external-content FTS and exact FP32 vectors in one SQLite file.

Mutations take the indexer's transaction. Readers use one snapshot for candidate
selection and payload hydration, without materializing an Arrow table.
"""
from __future__ import annotations

import errno
import itertools
import json
import math
import re
import struct
import shutil
import tempfile
import threading
from pathlib import Path

import sqlite_runtime as runtime

DIMENSIONS = 384
FILENAME = "index-state.sqlite"
SCHEMA_VERSION = "7"
LAYERS = ("docs", "code")
FTS_COLUMNS = "chunk_id,path,kind,language,tags,start_line,end_line,text"
# Local native qualification, not an architectural maximum or a promise for
# other hardware. Existing indexes continue correct exact search above this
# envelope; migration and health consume this single evidence-bound contract.
QUALIFIED_MAX_ROWS = {"docs": 55_990, "code": 50_000}
QUALIFIED_CANDIDATE_CAPS = {"docs": 50, "code": 240}
CAPACITY_QUALIFICATION_SCOPE = "macOS ARM64; 384-dimensional float32 exact cosine; local wave 1xjmm measurements"


def capacity_qualification(counts: dict[str, int]) -> dict:
    """Describe the measured envelope without restricting correct index growth."""
    normalized = {layer: int(counts.get(layer, 0)) for layer in LAYERS}
    exceeded = [layer for layer in LAYERS if normalized[layer] < 0 or normalized[layer] > QUALIFIED_MAX_ROWS[layer]]
    return {"qualified": not exceeded, "counts": normalized,
            "qualified_max_rows": dict(QUALIFIED_MAX_ROWS), "exceeded_layers": exceeded,
            "qualification_scope": CAPACITY_QUALIFICATION_SCOPE,
            "candidate_caps": dict(QUALIFIED_CANDIDATE_CAPS)}


def _layer(layer):
    if layer not in LAYERS:
        raise ValueError(f"Unknown semantic layer: {layer!r}")
    return layer


def create_schema(conn) -> None:
    """Create storage tables inside the caller's transaction, never migrate implicitly."""
    for layer in LAYERS:
        conn.execute(f"""CREATE TABLE IF NOT EXISTS chunks_{layer} (
            id INTEGER PRIMARY KEY, chunk_id TEXT NOT NULL UNIQUE,
            path TEXT NOT NULL, kind TEXT NOT NULL, language TEXT NOT NULL,
            tags TEXT NOT NULL, start_line INTEGER, end_line INTEGER,
            text TEXT NOT NULL, payload TEXT NOT NULL, text_present INTEGER NOT NULL)""")
        conn.execute(f"CREATE INDEX IF NOT EXISTS chunks_{layer}_path ON chunks_{layer}(path)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS chunks_{layer}_kind ON chunks_{layer}(kind)")
        conn.execute(f"CREATE INDEX IF NOT EXISTS chunks_{layer}_language ON chunks_{layer}(language)")
        conn.execute(f"""CREATE TABLE IF NOT EXISTS vectors_{layer} (
            chunk_id INTEGER PRIMARY KEY REFERENCES chunks_{layer}(id) ON DELETE CASCADE,
            embedding BLOB NOT NULL CHECK(length(embedding)={DIMENSIONS * 4}))""")
        conn.execute(f"""CREATE VIRTUAL TABLE IF NOT EXISTS fts_{layer} USING fts5(
            chunk_id UNINDEXED,path UNINDEXED,kind UNINDEXED,language UNINDEXED,
            tags UNINDEXED,start_line UNINDEXED,end_line UNINDEXED,text,
            content='chunks_{layer}',content_rowid='id',
            tokenize="unicode61 tokenchars '_'")""")
        new = ",".join("new." + name for name in FTS_COLUMNS.split(","))
        old = ",".join("old." + name for name in FTS_COLUMNS.split(","))
        conn.execute(f"""CREATE TRIGGER IF NOT EXISTS chunks_{layer}_insert AFTER INSERT ON chunks_{layer}
            BEGIN INSERT INTO fts_{layer}(rowid,{FTS_COLUMNS}) VALUES(new.id,{new}); END""")
        conn.execute(f"""CREATE TRIGGER IF NOT EXISTS chunks_{layer}_delete AFTER DELETE ON chunks_{layer}
            BEGIN INSERT INTO fts_{layer}(fts_{layer},rowid,{FTS_COLUMNS}) VALUES('delete',old.id,{old}); END""")
        conn.execute(f"""CREATE TRIGGER IF NOT EXISTS chunks_{layer}_update AFTER UPDATE ON chunks_{layer}
            BEGIN INSERT INTO fts_{layer}(fts_{layer},rowid,{FTS_COLUMNS}) VALUES('delete',old.id,{old});
            INSERT INTO fts_{layer}(rowid,{FTS_COLUMNS}) VALUES(new.id,{new}); END""")


def pack_vector(vector) -> bytes:
    if isinstance(vector, (bytes, bytearray, memoryview)):
        data = bytes(vector)
        if len(data) != DIMENSIONS * 4:
            raise ValueError(f"Expected {DIMENSIONS} FP32 dimensions")
        import numpy as np
        values = np.frombuffer(data, dtype="<f4")
        if not np.isfinite(values).all() or not values.any():
            raise ValueError("Cosine vectors must be finite and nonzero")
        return data
    else:
        values = tuple(float(x) for x in vector)
        if len(values) != DIMENSIONS:
            raise ValueError(f"Expected {DIMENSIONS} FP32 dimensions")
        data = struct.pack(f"<{DIMENSIONS}f", *values)
    if not all(math.isfinite(v) for v in values) or not any(values):
        raise ValueError("Cosine vectors must be finite and nonzero")
    return data


def write_rows(conn, layer: str, rows, *, require_vector: bool = True) -> None:
    """Upsert public payloads and vectors without committing the caller's transaction."""
    layer = _layer(layer)
    if conn.get_autocommit():
        raise RuntimeError("write_rows requires an indexing transaction")
    for row in rows:
        vector = pack_vector(row["vector"]) if "vector" in row else None
        if require_vector and vector is None:
            raise ValueError("Canonical semantic chunk requires its embedding")
        payload = {k: v for k, v in row.items() if k not in ("vector", "text", "_distance")}
        tags = row.get("tags") or ""
        if isinstance(tags, (tuple, list)):
            tags = " ".join(str(tag) for tag in tags)
        lines = row.get("lines") or [row.get("start_line", 0), row.get("end_line", 0)]
        params = (str(row.get("id") or ""), str(row.get("path") or ""),
                  str(row.get("kind") or ""), str(row.get("language") or ""), str(tags),
                  lines[0], lines[1], str(row.get("text") or ""),
                  json.dumps(payload, separators=(",", ":"), ensure_ascii=False), int("text" in row))
        result = conn.execute(f"""INSERT INTO chunks_{layer}
            (chunk_id,path,kind,language,tags,start_line,end_line,text,payload,text_present)
            VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(chunk_id) DO UPDATE SET
            path=excluded.path,kind=excluded.kind,language=excluded.language,tags=excluded.tags,
            start_line=excluded.start_line,end_line=excluded.end_line,text=excluded.text,
            payload=excluded.payload,text_present=excluded.text_present RETURNING id""", params).fetchall()
        if vector is not None:
            conn.execute(f"INSERT INTO vectors_{layer}(chunk_id,embedding) VALUES (?,?) "
                         "ON CONFLICT(chunk_id) DO UPDATE SET embedding=excluded.embedding",
                         (result[0][0], vector))


def delete_rows(conn, layer: str, *, ids=(), paths=()) -> None:
    layer = _layer(layer)
    if conn.get_autocommit():
        raise RuntimeError("delete_rows requires an indexing transaction")
    conn.executemany(f"DELETE FROM chunks_{layer} WHERE chunk_id=?", ((str(x),) for x in ids))
    conn.executemany(f"DELETE FROM chunks_{layer} WHERE path=?", ((str(x),) for x in paths))


_TOKEN = re.compile(r"\s*(?:('(?:''|[^'])*')|([A-Za-z_][A-Za-z_0-9]*)|([(),=]))")
_COLUMNS = {"id": "c.chunk_id", "path": "c.path", "kind": "c.kind",
            "language": "c.language", "tags": "c.tags"}


def _predicate(predicate):
    """Bind literals in the existing internal filter grammar; reject arbitrary SQL."""
    if not predicate:
        return "1", []
    out, values, offset = [], [], 0
    while offset < len(predicate):
        if not predicate[offset:].strip():
            break
        match = _TOKEN.match(predicate, offset)
        if match is None:
            raise ValueError("Unsupported vector filter syntax")
        literal, word, punctuation = match.groups()
        offset = match.end()
        if literal is not None:
            values.append(literal[1:-1].replace("''", "'")); out.append("?")
        elif word in _COLUMNS:
            out.append(_COLUMNS[word])
        elif word and word.upper() in {"AND", "OR", "LIKE", "IN"}:
            out.append(word.upper())
        elif punctuation:
            out.append(punctuation)
        else:
            raise ValueError("Unsupported vector filter column or operator")
    return " ".join(out), values


def _open(index_dir):
    conn = runtime.connect(Path(index_dir) / FILENAME, read_only=True)
    try:
        version = conn.execute("SELECT value FROM meta WHERE key='store_schema_version'").fetchone()
        if version != (SCHEMA_VERSION,):
            raise runtime.StorageRecoveryRequired("Semantic index migration required; run wf setup.")
        return conn
    except BaseException:
        conn.close()
        raise


def _payload(row, *, include_vector=False, distance=False):
    payload = json.loads(row[0])
    if row[2]:
        payload["text"] = row[1]
    if include_vector:
        payload["vector"] = list(struct.unpack(f"<{DIMENSIONS}f", row[3]))
    if distance:
        payload["_distance"] = row[3]
    return payload


def dense_rows(index_dir: Path, layer: str, vector, limit: int,
               predicate: str | None = None) -> list[dict]:
    layer = _layer(layer)
    if limit <= 0:
        return []
    query = pack_vector(vector)
    where, params = _predicate(predicate)
    conn = _open(index_dir)
    try:
        with conn:
            rows = conn.execute(f"SELECT c.payload,c.text,c.text_present,"
                f"vec_distance_cosine(v.embedding,?) AS distance FROM chunks_{layer} c "
                f"JOIN vectors_{layer} v ON v.chunk_id=c.id WHERE {where} "
                "ORDER BY distance,c.id LIMIT ?", [query, *params, int(limit)]).fetchall()
            return [_payload(row, distance=True) for row in rows]
    finally:
        conn.close()


def payload_rows(index_dir: Path, layer: str, predicate: str | None = None,
                 limit: int | None = None, include_vector: bool = False) -> list[dict]:
    layer = _layer(layer)
    where, params = _predicate(predicate)
    conn = _open(index_dir)
    try:
        with conn:
            rows = conn.execute(f"SELECT c.payload,c.text,c.text_present"
                + (",v.embedding" if include_vector else "")
                + f" FROM chunks_{layer} c JOIN vectors_{layer} v ON v.chunk_id=c.id WHERE {where}"
                + " ORDER BY c.id" + (" LIMIT ?" if limit is not None else ""),
                [*params, int(limit)] if limit is not None else params).fetchall()
            return [_payload(row, include_vector=include_vector) for row in rows]
    finally:
        conn.close()


def layer_counts(index_dir: Path) -> dict[str, int]:
    conn = _open(index_dir)
    try:
        with conn:
            return {layer: conn.execute(f"SELECT COUNT(*) FROM chunks_{layer} c JOIN "
                    f"vectors_{layer} v ON c.id=v.chunk_id").fetchone()[0] for layer in LAYERS}
    finally:
        conn.close()


def vector_integrity(conn, layer: str) -> dict[str, int]:
    """Count both sides of the canonical/vector relationship in one snapshot.

    Foreign keys protect ordinary writers, but health/recovery must also expose
    pre-existing orphan rows rather than hiding them behind a serving JOIN.
    """
    layer = _layer(layer)
    canonical = conn.execute(f"SELECT COUNT(*) FROM chunks_{layer}").fetchone()[0]
    vectors = conn.execute(f"SELECT COUNT(*) FROM vectors_{layer}").fetchone()[0]
    missing = conn.execute(f"SELECT COUNT(*) FROM chunks_{layer} c LEFT JOIN vectors_{layer} v "
                           "ON c.id=v.chunk_id WHERE v.chunk_id IS NULL").fetchone()[0]
    orphaned = conn.execute(f"SELECT COUNT(*) FROM vectors_{layer} v LEFT JOIN chunks_{layer} c "
                            "ON c.id=v.chunk_id WHERE c.id IS NULL").fetchone()[0]
    return {"canonical": canonical, "vectors": vectors,
            "missing_vectors": missing, "orphan_vectors": orphaned}


def layer_available(index_dir: Path, layer: str) -> bool:
    _layer(layer)
    if not (Path(index_dir) / FILENAME).is_file():
        return False
    conn = _open(index_dir)
    try:
        if conn.execute(f"SELECT 1 FROM vectors_{layer} v JOIN chunks_{layer} c "
                        "ON c.id=v.chunk_id LIMIT 1").fetchone():
            return True
        if conn.execute(f"SELECT 1 FROM chunks_{layer} LIMIT 1").fetchone():
            return False
        row = conn.execute("SELECT value FROM build_layer_meta WHERE key='content'").fetchone()
        return bool(row and layer in json.loads(row[0]))
    finally:
        conn.close()


def storage_space(index_dir: Path) -> dict[str, int]:
    conn = _open(index_dir)
    try:
        return {key: conn.execute(f"PRAGMA {key}").fetchone()[0]
                for key in ("page_count", "freelist_count", "page_size")}
    finally:
        conn.close()


class PreparedUpdates:
    """Bounded, disposable embedding spool; never a serving or recovery authority.

Workers prepare independently of the shared index writer. Only publication
opens its write transaction. A failed process leaves no published half-delta.
"""

    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._require_space(0)
        self._directory = tempfile.TemporaryDirectory(
            prefix="wavefoundry-sqlite-prepared-", dir=self.index_dir)
        self.path = Path(self._directory.name) / "prepared.sqlite"
        self._mutex = threading.Lock()
        try:
            conn = runtime.connect(self.path)
            try:
                conn.execute("CREATE TABLE operations(seq INTEGER PRIMARY KEY,layer TEXT,"
                             "action TEXT,payload TEXT,vector BLOB)")
            finally:
                conn.close()
        except BaseException:
            self._directory.cleanup()
            raise

    def _require_space(self, growth_bytes):
        # A conservative headroom estimate, not a quota reservation. Keep room
        # for the database and its WAL together; actual I/O errors still roll
        # back the caller's transaction. Check the owned filesystem, never TMPDIR.
        required = 64 * 1024 * 1024 + 2 * growth_bytes
        free = shutil.disk_usage(self.index_dir).free
        if free < required:
            raise OSError(errno.ENOSPC,
                          f"Prepared index needs {required} free bytes; {free} available. "
                          "Free space on the index filesystem and retry indexing.",
                          str(self.index_dir))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self._directory.cleanup()

    def add(self, layer, *, rows=(), ids=(), paths=(), replace=False):
        _layer(layer)

        def operations():
            if replace:
                yield (layer, 'replace', None, None)
            for value in ids:
                yield (layer, 'id', str(value), None)
            for value in paths:
                yield (layer, 'path', str(value), None)
            for row in rows:
                yield (layer, 'row', json.dumps(
                    {k: v for k, v in row.items() if k != 'vector'},
                    separators=(',', ':')), pack_vector(row['vector']))

        with self._mutex:
            conn = runtime.connect(self.path)
            try:
                with conn:
                    pending = iter(operations())
                    growth = 0
                    while batch := list(itertools.islice(pending, 250)):
                        # Include a page per operation for SQLite overhead. The
                        # accumulator also covers dirty pages not yet flushed.
                        growth += sum(4096 + len((payload or '').encode('utf-8'))
                                      + len(vector or b'') for _, _, payload, vector in batch)
                        self._require_space(growth)
                        conn.executemany(
                            "INSERT INTO operations(layer,action,payload,vector) VALUES(?,?,?,?)",
                            batch)
            finally:
                conn.close()

    def apply(self, store, *, batch_size=250):
        """Drain into the caller's BEGIN IMMEDIATE; all resident updates share it."""
        import index_state_store as iss
        if store._conn.get_autocommit():
            raise RuntimeError("Prepared publication requires a writer transaction")
        # The spool remains present while canonical rows and their WAL grow.
        self._require_space(sum(p.stat().st_size for p in self.path.parent.iterdir()
                                if p.is_file()))
        conn = runtime.connect(self.path, read_only=True)
        try:
            cursor = iter(conn.execute("SELECT layer,action,payload,vector FROM operations ORDER BY seq"))
            if batch_size < 1:
                raise ValueError("Publication batch_size must be positive")
            while batch := list(itertools.islice(cursor, batch_size)):
                # Preserve operation order, including add-then-delete and later
                # replaces. Only adjacent operations of the same type coalesce.
                for (layer, action), operations in itertools.groupby(
                        batch, key=lambda operation: operation[:2]):
                    rows, ids, paths = [], [], []
                    for target, action, payload, vector in operations:
                        if action == 'replace':
                            store._conn.execute(f"DELETE FROM chunks_{layer}")
                            # Explicit full replacement also retires corrupt
                            # orphan vectors that no canonical row can own.
                            store._conn.execute(f"DELETE FROM vectors_{layer}")
                            store._conn.execute("DELETE FROM chunk_registry WHERE table_name=?", (layer,))
                            iss._write_fts_digest_meta(store._conn, layer, 0)
                        elif action == 'row':
                            row = json.loads(payload)
                            row['vector'] = vector
                            rows.append(row)
                        elif action == 'id':
                            ids.append(payload)
                        elif action == 'path':
                            paths.append(payload)
                    if rows or ids or paths:
                        iss._apply_chunk_deltas_locked(store, layer, delete_ids=ids,
                                                      delete_paths=paths, add_rows=rows)
        finally:
            conn.close()

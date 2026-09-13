"""Monotonic index writer compatibility. No connection or migration ownership.

The source snapshot is captured on the first producer import, not its first
operation. Later imports and publications verify bytes, including replacements
which preserve size/mtime. Restarting is the only way to adopt a new contract.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
from pathlib import Path
import re
import sys
from types import ModuleType

from sqlite_runtime import StorageRecoveryRequired

INDEX_GUARD_CAPABILITY = 1
_ACTIVE_WRITERS = ContextVar("index_compatibility_writers", default=frozenset())
_SOURCE_NAMES = ("indexer", "chunker", "graph_indexer", "graph_store",
                 "sqlite_vector_store", "index_state_store", "model_bundle")
_SOURCE_ROOT = Path(__file__).resolve().parent
_SOURCE_BYTES = {name: (_SOURCE_ROOT / (name + ".py")).read_bytes() for name in _SOURCE_NAMES}
_SOURCE_HASHES = {name: hashlib.sha256(value).hexdigest() for name, value in _SOURCE_BYTES.items()}


class IndexCompatibilityError(StorageRecoveryRequired):
    """A preserved index requires a current host, never destructive repair."""
    def __init__(self, code, component, persisted=None, supported=None):
        self.code = code
        self.component = component
        self.persisted = persisted
        self.supported = supported
        super().__init__(f"{code}: {component}: persisted={persisted!r}, supported={supported!r}. "
                         "Index preserved. Reload/restart the affected Wavefoundry host, then "
                         "resume the ordinary setup/upgrade or index command; do not delete the index.")


def ensure_runtime_current():
    """Verify installed producer bytes against this runtime's immutable capture."""
    for name, expected in _SOURCE_HASHES.items():
        try:
            actual = hashlib.sha256((_SOURCE_ROOT / (name + ".py")).read_bytes()).hexdigest()
        except OSError:
            actual = None
        if actual != expected:
            raise IndexCompatibilityError("index_runtime_stale", name, actual, expected)


_COMPILED_SOURCES = {}

def register_loaded_source():
    """Bind the executing module code, including replacement during import."""
    frame = sys._getframe(1)
    name = Path(frame.f_code.co_filename).stem
    if name not in _SOURCE_BYTES:
        raise IndexCompatibilityError("index_runtime_stale", name, "unknown producer", "captured source")
    key = (name, frame.f_code.co_filename, sys.flags.optimize)
    if key not in _COMPILED_SOURCES:
        expected_code = compile(_SOURCE_BYTES[name], frame.f_code.co_filename, "exec",
                                dont_inherit=True, optimize=sys.flags.optimize)
        if frame.f_code != expected_code:
            raise IndexCompatibilityError("index_runtime_stale", name, "executing code", "installed source capture")
        # Retain the already executing code object, not a duplicate compiled tree.
        _COMPILED_SOURCES[key] = frame.f_code
    if frame.f_code != _COMPILED_SOURCES[key]:
        raise IndexCompatibilityError("index_runtime_stale", name, "executing code", "installed source capture")
    ensure_runtime_current()


def _read_literals():
    wanted = {"STATE_STORE_SCHEMA_VERSION", "GRAPH_STORE_SCHEMA_VERSION", "GRAPH_SCHEMA_VERSION",
              "GRAPH_BUILDER_VERSION", "WALKER_VERSION", "CHUNKER_VERSION",
              "LEXICAL_STATISTICS_VERSION", "FTS_TOKENIZER"}
    values = {}
    for module, source in _SOURCE_BYTES.items():
        for node in ast.parse(source).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in wanted:
                        values[module, target.id] = ast.literal_eval(node.value)
    return values


_LITERALS = _read_literals()


def _literal(module, name):
    return _LITERALS[module, name]


SUPPORTED = {
    "store_schema_version": _literal("index_state_store", "STATE_STORE_SCHEMA_VERSION"),
    "graph:store_schema_version": _literal("graph_indexer", "GRAPH_STORE_SCHEMA_VERSION"),
    "graph:schema_version": _literal("graph_indexer", "GRAPH_SCHEMA_VERSION"),
    "graph:builder_version": _literal("graph_indexer", "GRAPH_BUILDER_VERSION"),
    "graph:walker_version": _literal("indexer", "WALKER_VERSION"),
    "graph:chunker_version": _literal("chunker", "CHUNKER_VERSION"),
    "walker_version": _literal("indexer", "WALKER_VERSION"),
    "chunker_version": _literal("chunker", "CHUNKER_VERSION"),
    "lexical_statistics.version": _literal("index_state_store", "LEXICAL_STATISTICS_VERSION"),
}


def _revision(value, component, supported):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        return int(value)
    raise IndexCompatibilityError("index_compatibility_unproven", component, value, supported)


def check_ordered(component, persisted, supported):
    """Reject malformed and newer ordered revisions; never coerce identities."""
    want = _revision(supported, component, supported)
    have = _revision(persisted, component, supported)
    if have > want:
        raise IndexCompatibilityError("index_version_newer", component, persisted, supported)


def _mapping(raw, component):
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        value = None
    if not isinstance(value, dict):
        raise IndexCompatibilityError("index_compatibility_unproven", component, raw, "object")
    return value


def check_connection(conn, expected=None, *, verify_source=True):
    """Read bounded metadata in the caller's snapshot, without repairing it.

    A pre-schema empty database is initializable. Missing legacy semantic
    provenance is accepted only before any complete build; a partial mapping
    or malformed recorded field is never a legacy absence. All existing
    participants are inspected, including unselected layers sharing metadata.
    """
    if id(conn) in _ACTIVE_WRITERS.get():
        return
    if verify_source:
        ensure_runtime_current()
    supported = dict(SUPPORTED)
    # Owners may already be loaded (including explicit supported-version test
    # controls). Never import a producer from storage or reload it here.
    for module, pairs in (("graph_indexer", (("GRAPH_STORE_SCHEMA_VERSION", "graph:store_schema_version"), ("GRAPH_SCHEMA_VERSION", "graph:schema_version"), ("GRAPH_BUILDER_VERSION", "graph:builder_version"))),
                          ("indexer", (("WALKER_VERSION", "walker_version"), ("WALKER_VERSION", "graph:walker_version"))),
                          ("chunker", (("CHUNKER_VERSION", "chunker_version"), ("CHUNKER_VERSION", "graph:chunker_version")))):
        loaded = sys.modules.get(module)
        for declaration, key in pairs:
            if isinstance(loaded, ModuleType) and declaration in vars(loaded):
                supported[key] = vars(loaded)[declaration]
    if expected:
        supported.update(expected)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_schema WHERE type='table'")}
    if "meta" not in tables:
        if tables:
            raise IndexCompatibilityError("index_compatibility_unproven", "store_schema_version", None, supported["store_schema_version"])
        return
    meta = dict(conn.execute("SELECT key,value FROM meta WHERE key='store_schema_version' OR key LIKE 'graph:%' OR key='lexical_statistics'"))
    if "store_schema_version" in meta:
        check_ordered("store_schema_version", meta["store_schema_version"], supported["store_schema_version"])
    elif tables != {"meta"}:
        raise IndexCompatibilityError("index_compatibility_unproven", "store_schema_version", None, supported["store_schema_version"])
    graph_keys = [k for k in supported if k.startswith("graph:")]
    graph_present = any(k.startswith("graph:") for k in meta)
    graph_rows = any(t in tables and conn.execute(f"SELECT 1 FROM {t} LIMIT 1").fetchone()
                     for t in tables if t.startswith("graph_"))
    for key in graph_keys:
        if key in meta:
            check_ordered(key, meta[key], supported[key])
        elif graph_present or graph_rows:
            raise IndexCompatibilityError("index_compatibility_unproven", key, None, supported[key])
    if "lexical_statistics" in meta:
        stats = _mapping(meta["lexical_statistics"], "lexical_statistics")
        check_ordered("lexical_statistics.version", stats.get("version"), supported["lexical_statistics.version"])
        if "tokenizer" in stats and stats["tokenizer"] != _literal("index_state_store", "FTS_TOKENIZER"):
            raise IndexCompatibilityError("index_compatibility_unproven", "lexical_statistics.tokenizer", stats["tokenizer"], _literal("index_state_store", "FTS_TOKENIZER"))
    if "build_layer_meta" not in tables:
        return
    layer = dict(conn.execute("SELECT key,value FROM build_layer_meta WHERE key IN ('walker_version','chunker_version','chunker_versions','model_versions')"))
    complete = False
    if "build_state" in tables:
        state = conn.execute("SELECT status,generation FROM build_state WHERE id=1").fetchone()
        complete = bool(state and (state[0] == "complete" or state[1] > 0))
    if "walker_version" in layer:
        check_ordered("walker_version", layer["walker_version"], supported["walker_version"])
    versions = _mapping(layer["chunker_versions"], "chunker_versions") if "chunker_versions" in layer else {}
    if "chunker_version" in layer:
        check_ordered("chunker_version", layer["chunker_version"], supported["chunker_version"])
    models = _mapping(layer["model_versions"], "model_versions") if "model_versions" in layer else {}
    for name in ("docs", "code"):
        value = versions.get(name, layer.get("chunker_version"))
        if value is not None:
            check_ordered(f"chunker_versions.{name}", value, supported["chunker_version"])
        populated = ("chunks_" + name) in tables and conn.execute(f"SELECT 1 FROM chunks_{name} LIMIT 1").fetchone()
        embedded = ("vectors_" + name) in tables and conn.execute(f"SELECT 1 FROM vectors_{name} LIMIT 1").fetchone()
        if populated and complete:
            required = [("walker_version", layer.get("walker_version")), (f"chunker_versions.{name}", value)]
            if embedded:
                required.append((f"model_versions.{name}", models.get(name)))
            for key, val in required:
                if val is None or (key.startswith("model_versions") and (not isinstance(val, str) or not val)):
                    raise IndexCompatibilityError("index_compatibility_unproven", key, val, "published identity")


def _autocommit(conn):
    return conn.get_autocommit() if hasattr(conn, "get_autocommit") else not conn.in_transaction


@contextmanager
def writer_transaction(conn, *, expected=None):
    """Own BEGIN IMMEDIATE, or join the caller's transaction without committing.

    Existing deferred readers are safe: the metadata SELECT pins their snapshot,
    and SQLite refuses its write upgrade if a competing writer committed since.
    """
    owner = _autocommit(conn)
    if owner:
        conn.execute("BEGIN IMMEDIATE")
    token = None
    try:
        check_connection(conn, expected)
        token = _ACTIVE_WRITERS.set(_ACTIVE_WRITERS.get() | {id(conn)})
        yield conn
        if owner:
            ensure_runtime_current()
        if owner:
            conn.execute("COMMIT")
    except BaseException:
        if owner and not _autocommit(conn):
            conn.execute("ROLLBACK")
        raise
    finally:
        if token is not None:
            _ACTIVE_WRITERS.reset(token)

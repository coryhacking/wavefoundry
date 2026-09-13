"""Generation-bound resident graph and community views (wave ``1xny6``, lane L5).

Every consumer that used to read ``project-graph.json`` or
``project-graph-clusters.json`` reads HERE instead. The retired files were two
independently-stat'd artifacts: a reader could see a graph written by one build
beside communities written by the next, and a same-mtime rewrite could pin
stale content indefinitely. Both failure modes are structural, and both are
closed the same way -- by reading graph rows AND community rows inside ONE
pinned SQLite read transaction whose build generation is read in that same
transaction.

Acquisition contract
--------------------

1. ``index_state_store.open_read_only`` gives a read-only connection (the
   helper's open-and-close-per-operation contract is honored: the connection
   is closed before :func:`acquire` returns, so a pinned reader can never
   starve WAL autocheckpoint between builds).
2. ``BEGIN`` + the first read pins ONE SQLite read snapshot. Everything after
   -- the build-state row, the graph meta, the graph rows, the community rows
   -- is read from that single snapshot, so the ``(attempt_id, generation)``
   the snapshot is stamped with IS the generation the rows belong to. A
   publication committing mid-read is invisible to this transaction; it cannot
   produce a graph/community pair from two generations.
3. The transaction ends and the connection closes before any caller work runs.
   What the caller holds is an immutable in-memory object, not a database
   handle, so a view is never swapped beneath an in-flight response: replacing
   the process cache rebinds the NEXT acquisition, never this one.

Content sharing across generations
----------------------------------

An unchanged graph input must not cost a rehydration on every build. When the
newly pinned generation carries the same ``graph_fingerprint`` as the cached
snapshot, the cached payload object (and anything derived from it, such as the
constructed ``GraphQueryIndex``) is REUSED under the new generation, with
explicit provenance: ``graph_content_generation`` records the generation the
content was actually loaded at, and ``shared_graph_content`` says the reuse
happened. Communities share independently on ``community_fingerprint``, so a
graph-unchanged / clusters-recomputed build shares half and reloads half.

Retry bound
-----------

A store caught mid-publication (``status != 'complete'``) is retried EXACTLY
once. After that the established typed not-ready state is returned; this module
never loops waiting for a publication to land.

This module never writes graph content. Its one write is the codebase-map
receipt -- a derived-output receipt (see :func:`write_map_receipt`) that never
advances any generation and is allowed to fail without failing its caller.
"""
from __future__ import annotations

import contextlib
import contextvars
import hashlib
import os
import threading
from pathlib import Path
from typing import Any

import index_paths

LAYERS = ("project",)

# Logical components of the shared database, for the path-identity fields that
# used to name the retired files. A consumer that prints `graph_path` is
# telling an operator where the graph LIVES; after this wave that is a
# component of one database, not a deleted filename.
GRAPH_COMPONENT = "graph"
COMMUNITY_COMPONENT = "communities"

# Acquisition outcomes. `absent` means the store is readable and its build
# epoch is complete but no graph generation has been published, or no store
# exists. `not_ready` preserves the established unreadable/in-flight contract;
# its diagnostic distinguishes publication retry from runtime/storage/migration
# recovery. Existing consumers must still refuse unreadable snapshots.
READY = "ready"
ABSENT = "absent"
NOT_READY = "not_ready"

# One initial acquisition plus ONE re-acquisition. Never a loop.
_MAX_ACQUISITIONS = 2

# Kill switch (diagnosis): restores acquire-per-call behavior when truthy.
_CACHE_DISABLE_ENV = "WAVEFOUNDRY_DISABLE_GRAPH_SNAPSHOT_CACHE"

_CACHE_LOCK = threading.Lock()
_CACHE: "dict[tuple[str, str], GraphSnapshot]" = {}
# One acquisition at a time per (root, layer). Concurrent tool calls against a
# cold cache would otherwise each hydrate the whole graph and each build their
# own adjacency structures -- the double-build the resident cache exists to
# avoid. Whoever loses the race re-reads the generation (cheap) and then shares
# the winner's content, so it ends up holding the SAME payload and the SAME
# constructed index rather than a duplicate of them.
_ACQUIRE_LOCKS: "dict[tuple[str, str], threading.Lock]" = {}


def _acquire_lock_for(key) -> threading.Lock:
    with _CACHE_LOCK:
        lock = _ACQUIRE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _ACQUIRE_LOCKS[key] = lock
        return lock

# The per-response pin. `acquire` consults it first, so every read inside a
# `pinned(...)` block returns the SAME object even across modules.
_PIN: "contextvars.ContextVar[dict | None]" = contextvars.ContextVar(
    "wavefoundry_graph_snapshot_pin", default=None
)


def index_dir_for(root) -> Path:
    return Path(root) / ".wavefoundry" / "index"


def component_path(component: str) -> str:
    """Repo-relative identity of one logical component of the shared database.

    Replaces the retired ``.wavefoundry/index/graph/*.json`` strings in every
    persisted ``graph_path`` / ``cluster_path`` field. It reads the runtime
    filename from :mod:`index_paths`, so lane L6's one-line rename flip moves
    these strings with it instead of leaving a second literal behind.
    """
    return f".wavefoundry/index/{index_paths.RUNTIME_DATABASE_FILENAME}#{component}"


class GraphSnapshot:
    """One immutable graph + community view, bound to one build generation."""

    __slots__ = (
        "state", "layer", "generation", "attempt_id", "graph_fingerprint",
        "community_fingerprint", "builder_version", "graph", "clusters",
        "graph_content_generation", "community_content_generation",
        "shared_graph_content", "shared_community_content",
        "derived_graph", "derived_clusters", "_derive_lock", "diagnostic",
    )

    def __init__(self, *, state: str, layer: str, generation: int = 0,
                 diagnostic: "dict[str, Any] | None" = None,
                 attempt_id: str = "", graph_fingerprint: str = "",
                 community_fingerprint: str = "",
                 builder_version: str = "",
                 graph: "dict[str, Any] | None" = None,
                 clusters: "dict[str, Any] | None" = None,
                 graph_content_generation: int = 0,
                 community_content_generation: int = 0,
                 shared_graph_content: bool = False,
                 shared_community_content: bool = False,
                 derived_graph: "dict | None" = None,
                 derived_clusters: "dict | None" = None) -> None:
        self.state = state
        self.diagnostic = dict(diagnostic) if diagnostic else None
        self.layer = layer
        self.generation = generation
        self.attempt_id = attempt_id
        self.graph_fingerprint = graph_fingerprint
        self.community_fingerprint = community_fingerprint
        # The builder that produced the published rows, read from the SAME
        # pinned snapshot as the rows -- so the version a staleness check acts
        # on and the graph it would serve can never disagree.
        self.builder_version = builder_version
        self.graph = graph
        self.clusters = clusters
        self.graph_content_generation = graph_content_generation
        self.community_content_generation = community_content_generation
        self.shared_graph_content = shared_graph_content
        self.shared_community_content = shared_community_content
        # Derived-object slots travel with the CONTENT they were derived from,
        # so a generation bump over an unchanged graph does not rebuild the
        # adjacency structures.
        self.derived_graph = derived_graph if derived_graph is not None else {}
        self.derived_clusters = derived_clusters if derived_clusters is not None else {}
        self._derive_lock = threading.Lock()

    # -- state predicates ---------------------------------------------------

    @property
    def ready(self) -> bool:
        return self.state == READY

    @property
    def present(self) -> bool:
        return self.state == READY and bool(self.graph)

    @property
    def clusters_present(self) -> bool:
        return self.state == READY and bool(self.clusters)

    def provenance(self) -> "dict[str, Any]":
        """Explicit answer to 'which generation is this content actually from?'"""
        return {
            "generation": self.generation,
            "attempt_id": self.attempt_id,
            "graph_content_generation": self.graph_content_generation,
            "community_content_generation": self.community_content_generation,
            "shared_graph_content": self.shared_graph_content,
            "shared_community_content": self.shared_community_content,
            "graph_fingerprint": self.graph_fingerprint,
            "community_fingerprint": self.community_fingerprint,
            "builder_version": self.builder_version,
        }

    def derive(self, slot: str, factory, *, of: str = "graph"):
        """Memoize one derived object against this snapshot's CONTENT.

        ``of='graph'`` binds the result to ``graph_fingerprint`` and
        ``of='clusters'`` to ``community_fingerprint``, so a snapshot that
        shared its content carries the derived object forward for free.
        """
        store = self.derived_graph if of == "graph" else self.derived_clusters
        hit = store.get(slot)
        if hit is not None:
            return hit
        with self._derive_lock:
            hit = store.get(slot)
            if hit is not None:
                return hit
            value = factory()
            store[slot] = value
            return value


def _not_ready(layer: str) -> GraphSnapshot:
    return GraphSnapshot(state=NOT_READY, layer=layer, diagnostic={
        "code": "graph_publication_in_flight",
        "message": "Graph publication is not complete. Retry after the active build finishes.",
        "recovery_tools": ["index_build_status"],
        "recovery_usage": "index_build_status()",
    })



def _read_failure(layer: str, exc: Exception) -> GraphSnapshot:
    """Keep actionable causes as data; never retain an exception traceback."""
    import sqlite_storage_migration
    code = getattr(exc, "code", "")
    detail = str(exc)
    recovery_tools, recovery_usage = ["index_health"], "index_health()"
    if isinstance(exc, sqlite_storage_migration.MigrationRequired):
        code = detail.split(":", 1)[0] or "storage_migration_required"
        recovery = "Preserve the index and migration receipt; inspect wf_upgrade_status(), then resume Upgrade Wavefoundry."
        recovery_tools, recovery_usage = ["wf_upgrade_status"], "wf_upgrade_status()"
    elif code == "storage_runtime_unavailable":
        recovery = "Run wf setup --root . in the repository to repair the native runtime, then restart the host."
    elif code in {"index_runtime_stale", "index_version_newer", "index_compatibility_unproven"}:
        recovery = "Restart the affected Wavefoundry host; preserve the newer index instead of rebuilding it."
        recovery_usage = "Restart the affected Wavefoundry host, then call index_health()."
    elif code == "storage_recovery_required":
        recovery = "Preserve the index; resolve the storage/filesystem refusal before retrying."
    else:
        code = "graph_read_failed"
        recovery = "Preserve the index and investigate the read failure before retrying."
    return GraphSnapshot(state=NOT_READY, layer=layer, diagnostic={
        "code": code, "message": f"{detail} {recovery}",
        "recovery_tools": recovery_tools, "recovery_usage": recovery_usage,
    })


def _cache_disabled() -> bool:
    return os.environ.get(_CACHE_DISABLE_ENV, "").strip().lower() in (
        "1", "true", "yes", "on")


def _key(root, layer: str) -> "tuple[str, str]":
    try:
        resolved = str(Path(root).resolve())
    except OSError:
        resolved = str(root)
    return (resolved, layer)


def _graph_indexer():
    import graph_indexer

    return graph_indexer


def _graph_cluster():
    import graph_cluster

    return graph_cluster


def _index_state_store():
    import index_state_store

    return index_state_store


def _community_fingerprint(conn, layer: str) -> str:
    """Content fingerprint of the published communities.

    ``graph_analysis``'s ``computed_at`` moves on every recompute and stands
    still when the fingerprint-gated skip reuses the previous generation's
    rows, so this changes exactly when the community content changes -- which
    is what makes cross-generation community sharing safe.
    """
    gc = _graph_cluster()
    row = conn.execute(
        "SELECT input_fingerprint, method, computed_at FROM graph_analysis "
        "WHERE kind = ? AND layer = ?",
        (gc.CLUSTER_ANALYSIS_KIND, layer),
    ).fetchone()
    if row is None:
        return ""
    digest = hashlib.sha256(
        f"{row[0]}\x1f{row[1]}\x1f{row[2]}".encode("utf-8")
    ).hexdigest()
    return digest


def _read_pinned(index_dir: Path, layer: str, cached: "GraphSnapshot | None",
                 *, settle: bool = True):
    """One pinned read. ``None`` means 'transient, retry once'.

    Everything below the ``BEGIN`` comes from a single SQLite read snapshot,
    which is what makes the returned generation and the returned rows the same
    generation by construction rather than by comparison.
    """
    iss = _index_state_store()
    try:
        import sqlite_storage_migration
        conn = iss.open_read_only(index_dir)
        if conn is None:
            sqlite_storage_migration.require_ready(index_dir)
    except Exception as exc:  # noqa: BLE001 - retain cause without crashing a reader
        return _read_failure(layer, exc)
    if conn is None:
        if iss.state_store_path(index_dir).exists():
            return _read_failure(layer, RuntimeError("Existing index could not be read or has an incompatible schema."))
        return GraphSnapshot(state=ABSENT, layer=layer)
    try:
        sqlite_storage_migration.require_ready(index_dir)
        conn.execute("BEGIN")
        try:
            # Validate every graph/storage participant before reconstructing
            # rows, in the same snapshot that supplies their generation.
            import index_compatibility
            index_compatibility.check_connection(conn)
            row = conn.execute(
                "SELECT attempt_id, status, generation FROM build_state WHERE id = 1"
            ).fetchone()
            if row is None:
                # No build epoch at all. A standalone graph publication (a
                # direct `update_graph_index` caller, the quality evaluator) is
                # a legitimate producer that never mints one, and its rows are
                # just as committed. Bind to generation 0 rather than refusing:
                # refusing here would report a real published graph as absent.
                attempt_id, status, generation = "", "absent", 0
            else:
                attempt_id, status, generation = str(row[0]), str(row[1]), int(row[2])
            # Schema initialization may install the never-started sentinel;
            # it has the same meaning as no epoch row for standalone producers.
            standalone = status == "uninitialized" and not attempt_id and generation == 0
            if status not in ("complete", "absent") and not standalone:
                # Participant rows can commit before the final epoch CAS. They
                # are durable but not yet authorized by the old generation.
                # Retry once, then return a typed state; never serve those rows
                # with the previous generation merely because they committed.
                return None if settle else _not_ready(layer)
            gi = _graph_indexer()
            cut = len(gi.GRAPH_META_PREFIX)
            meta = {
                str(k)[cut:]: str(v)
                for k, v in conn.execute(
                    "SELECT key, value FROM meta WHERE key LIKE ?",
                    (gi.GRAPH_META_PREFIX + "%",),
                )
            }
            builder_version = str(meta.get("builder_version") or "")
            graph_fingerprint = gi.graph_published_fingerprint(meta)
            if not graph_fingerprint:
                return GraphSnapshot(state=ABSENT, layer=layer,
                                     generation=generation, attempt_id=attempt_id,
                                     builder_version=builder_version)
            community_fingerprint = _community_fingerprint(conn, layer)

            share_graph = (
                cached is not None and cached.ready
                and cached.graph is not None
                and cached.graph_fingerprint == graph_fingerprint
            )
            share_clusters = (
                cached is not None and cached.ready
                and cached.clusters is not None
                and bool(community_fingerprint)
                and cached.community_fingerprint == community_fingerprint
            )
            if share_graph:
                graph = cached.graph
                graph_content_generation = cached.graph_content_generation
                derived_graph = cached.derived_graph
            else:
                graph = gi.read_graph_payload_rows(conn, layer)
                if graph is None:
                    return GraphSnapshot(state=ABSENT, layer=layer,
                                         generation=generation,
                                         attempt_id=attempt_id,
                                         builder_version=builder_version)
                graph = _finish_graph_payload(graph, layer)
                graph_content_generation = generation
                derived_graph = None
            if share_clusters:
                clusters = cached.clusters
                community_content_generation = cached.community_content_generation
                derived_clusters = cached.derived_clusters
            else:
                clusters = _graph_cluster().read_published_clusters(conn, layer)
                clusters = _finish_cluster_payload(clusters, layer) if clusters else None
                community_content_generation = generation
                derived_clusters = None
        finally:
            with contextlib.suppress(Exception):
                conn.execute("ROLLBACK")
    except Exception as exc:  # noqa: BLE001 - retain read failure and close below
        return _read_failure(layer, exc)
    finally:
        with contextlib.suppress(Exception):
            conn.close()
    return GraphSnapshot(
        state=READY, layer=layer, generation=generation, attempt_id=attempt_id,
        graph_fingerprint=graph_fingerprint,
        community_fingerprint=community_fingerprint,
        builder_version=builder_version,
        graph=graph, clusters=clusters,
        graph_content_generation=graph_content_generation,
        community_content_generation=community_content_generation,
        shared_graph_content=share_graph,
        shared_community_content=share_clusters,
        derived_graph=derived_graph, derived_clusters=derived_clusters,
    )


def _finish_graph_payload(payload: "dict[str, Any]", layer: str) -> "dict[str, Any]":
    """Fill the shape ``read_graph_payload`` guaranteed, minus the dead path."""
    gi = _graph_indexer()
    payload.setdefault("layer", layer)
    payload.setdefault("schema_version", gi.GRAPH_SCHEMA_VERSION)
    payload.setdefault("nodes", [])
    payload.setdefault("edges", [])
    payload.setdefault("counts", {
        "files": 0,
        "nodes": len(payload.get("nodes") or []),
        "edges": len(payload.get("edges") or []),
    })
    payload["present"] = True
    payload["graph_path"] = component_path(GRAPH_COMPONENT)
    return payload


def _finish_cluster_payload(payload: "dict[str, Any]", layer: str) -> "dict[str, Any]":
    gc = _graph_cluster()
    payload.setdefault("layer", layer)
    payload.setdefault("cluster_schema_version", gc.CLUSTER_SCHEMA_VERSION)
    payload.setdefault("communities", [])
    payload["community_count"] = len(payload.get("communities") or [])
    payload["present"] = True
    payload["cluster_path"] = component_path(COMMUNITY_COMPONENT)
    payload["graph_path"] = component_path(GRAPH_COMPONENT)
    return payload


def acquire(root, layer: str = "project") -> GraphSnapshot:
    """The generation-bound snapshot for ``(root, layer)``.

    Inside a :func:`pinned` block this returns the pinned object without
    touching the database, so every read in one response observes exactly one
    generation.
    """
    if layer not in LAYERS:
        raise ValueError(f"Unsupported graph layer: {layer}")
    key = _key(root, layer)
    pins = _PIN.get()
    if pins is not None:
        pinned_snapshot = pins.get(key)
        if pinned_snapshot is not None:
            return pinned_snapshot
    return _acquire_fresh(root, layer)


def _acquire_fresh(root, layer: str = "project") -> GraphSnapshot:
    """Acquire ignoring any active pin. Only :func:`repin` and :func:`acquire`
    may call this — every other caller must go through the pin so one response
    cannot straddle two generations."""
    key = _key(root, layer)
    index_dir = index_dir_for(root)
    with _acquire_lock_for(key):
        with _CACHE_LOCK:
            cached = None if _cache_disabled() else _CACHE.get(key)

        snapshot = None
        for attempt in range(_MAX_ACQUISITIONS):
            snapshot = _read_pinned(index_dir, layer, cached,
                                    settle=attempt < _MAX_ACQUISITIONS - 1)
            if snapshot is not None:
                break
        if snapshot is None:
            # Belt and braces: the loop's last pass never asks to settle, so it
            # cannot return None. Fail closed rather than loop if that changes.
            return _not_ready(layer)

        if not _cache_disabled():
            with _CACHE_LOCK:
                current = _CACHE.get(key)
                if snapshot.ready:
                    # A concurrent acquisition that landed a NEWER generation
                    # wins: the cache must never move backwards.
                    if current is None or not current.ready or current.generation <= snapshot.generation:
                        _CACHE[key] = snapshot
                else:
                    _CACHE.pop(key, None)
        return snapshot


def repin(root, layer: str = "project") -> "GraphSnapshot | None":
    """Rebind an ACTIVE pin to a freshly published generation.

    The refresh-then-recheck path deliberately builds and then re-reads. Inside
    a pin that recheck would otherwise be answered from the pre-build snapshot
    and report the tool's own successful refresh as "still missing". Rebinding
    is the narrow, explicit exception to "never swap a view beneath an
    in-flight response": the response ASKED for the newer generation, and every
    read after this point in that response sees the one snapshot it rebound to.

    Always returns the freshly acquired snapshot, whether or not a pin is
    active -- a caller that has just rebuilt must never be handed the
    pre-build view, and inside a pin plain :func:`acquire` would hand it back
    exactly that.
    """
    invalidate(root, layer)
    snapshot = _acquire_fresh(root, layer)
    pins = _PIN.get()
    key = _key(root, layer)
    if pins is not None and key in pins:
        # Mutate the dict the active `pinned()` frame owns, so the rebinding is
        # visible to the rest of that frame without a new ContextVar set.
        pins[key] = snapshot
    return snapshot


@contextlib.contextmanager
def pinned(root, layer: str = "project"):
    """Bind ONE snapshot for the duration of a response.

    Nested pins for the same key reuse the outer binding, so a helper that
    pins internally cannot silently re-acquire underneath its caller.
    """
    key = _key(root, layer)
    existing = _PIN.get()
    if existing is not None and key in existing:
        yield existing[key]
        return
    snapshot = acquire(root, layer)
    pins = dict(existing or {})
    pins[key] = snapshot
    token = _PIN.set(pins)
    try:
        yield snapshot
    finally:
        _PIN.reset(token)


def invalidate(root, layer: str = "project") -> None:
    """Drop the cached snapshot for ``(root, layer)``. Idempotent."""
    with _CACHE_LOCK:
        _CACHE.pop(_key(root, layer), None)


def clear_cache() -> None:
    with _CACHE_LOCK:
        _CACHE.clear()


# --------------------------------------------------------------------------- #
# Codebase-map receipt: a DERIVED-OUTPUT receipt, not index publication.
# --------------------------------------------------------------------------- #
def read_map_receipt(root, layer: str = "project") -> "dict[str, Any] | None":
    """The last rendered-input receipt, or ``None`` when there is none."""
    iss = _index_state_store()
    try:
        conn = iss.open_read_only(index_dir_for(root))
    except Exception:  # noqa: BLE001
        return None
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT input_fingerprint, graph_input_fingerprint, "
            "community_input_fingerprint, graph_generation, rendered_at "
            "FROM codebase_map_receipt WHERE layer = ?",
            (layer,),
        ).fetchone()
    except Exception:  # noqa: BLE001 - a pre-schema-8 store has no such table
        return None
    finally:
        with contextlib.suppress(Exception):
            conn.close()
    if row is None:
        return None
    return {
        "input_fingerprint": str(row[0] or ""),
        "graph_input_fingerprint": str(row[1] or ""),
        "community_input_fingerprint": str(row[2] or ""),
        "graph_generation": int(row[3] or 0),
        "rendered_at": float(row[4] or 0.0),
    }


def write_map_receipt(root, *, layer: str = "project", input_fingerprint: str,
                      graph_input_fingerprint: str = "",
                      community_input_fingerprint: str = "",
                      graph_generation: int = 0,
                      rendered_at: "float | None" = None) -> bool:
    """Record a SUCCESSFUL render. Returns False when it could not be written.

    Busy-tolerant by contract, not by luck. A full rebuild's publication holds
    the write lock for roughly 6.7 seconds -- longer than the runtime's 5
    second busy timeout -- and the map CLI deliberately takes no build lock, so
    a contended receipt write is an ORDINARY outcome. It must leave the
    rendered output valid, must not fail the render and must not advance any
    generation; the next run simply re-renders and retries the receipt.

    The conditional ``DO UPDATE`` is the stale-render guard: a render that
    started against an older generation cannot certify a newer one that already
    landed. That refusal also returns ``False`` — "not written" covers both a
    contended write and a refused stale one, and the caller treats both the
    same way: leave the output, advance nothing, retry next run.
    """
    import time as _time

    index_dir = index_dir_for(root)
    # Never CREATE the database from the map path: a repository with no index
    # must stay a repository with no index.
    if not index_paths.runtime_database_path(index_dir).exists():
        return False
    iss = _index_state_store()
    store = None
    try:
        store = iss.IndexStateStore(index_dir)
        conn = store._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                "INSERT INTO codebase_map_receipt (layer, input_fingerprint, "
                "graph_input_fingerprint, community_input_fingerprint, "
                "graph_generation, rendered_at) VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(layer) DO UPDATE SET "
                "input_fingerprint=excluded.input_fingerprint, "
                "graph_input_fingerprint=excluded.graph_input_fingerprint, "
                "community_input_fingerprint=excluded.community_input_fingerprint, "
                "graph_generation=excluded.graph_generation, "
                "rendered_at=excluded.rendered_at "
                "WHERE excluded.graph_generation >= codebase_map_receipt.graph_generation",
                (layer, input_fingerprint, graph_input_fingerprint,
                 community_input_fingerprint, int(graph_generation),
                 float(rendered_at if rendered_at is not None else _time.time())),
            )
            # A refused stale update changes no row. Report that honestly: the
            # caller must not be told it certified a render it did not.
            certified = bool(conn.changes())
            conn.execute("COMMIT")
        except BaseException:
            with contextlib.suppress(Exception):
                conn.execute("ROLLBACK")
            raise
    except Exception:  # noqa: BLE001 - busy/locked/absent are ordinary here
        return False
    finally:
        if store is not None:
            with contextlib.suppress(Exception):
                store.close()
    return certified

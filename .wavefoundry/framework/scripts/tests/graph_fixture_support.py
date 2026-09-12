"""Publish graph + community fixtures through the CANONICAL producers.

Wave ``1xny6`` lane L5. Before this wave a graph fixture was two JSON files
written by hand; after it, a graph is rows committed with a build generation,
and every reader resolves it through ``graph_snapshot``. A test that hand-wrote
SQL would be asserting against its own encoding rather than the product's, so
this helper drives the real ones:

* ``graph_indexer._node_row`` / ``_edge_row`` encode the rows,
* ``graph_indexer.GraphPublication`` applies them,
* ``graph_cluster.prepare_cluster_publication`` diffs the community rows,
* ``index_state_store.begin_build_epoch`` / ``finalize_build_epoch`` own the
  generation — the same CAS that production publication uses.

Everything lands in ONE ``BEGIN IMMEDIATE`` transaction, exactly as the build
coordinator publishes it, so a fixture can never produce a state the product
could not.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import graph_cluster  # noqa: E402
import graph_indexer  # noqa: E402
import graph_snapshot  # noqa: E402
import index_state_store  # noqa: E402


def index_dir_for(root: Path) -> Path:
    return Path(root) / ".wavefoundry" / "index"


def graph_payload(nodes, edges, *, layer: str = "project",
                  builder_version: str | None = None,
                  input_fingerprint: str = "",
                  generated_at: str = "2026-01-01T00:00:00Z",
                  **extra) -> dict:
    """The payload shape the merge produces, for fixtures to publish."""
    payload = {
        "schema_version": graph_indexer.GRAPH_SCHEMA_VERSION,
        "builder_version": (builder_version if builder_version is not None
                            else graph_indexer.GRAPH_BUILDER_VERSION),
        "layer": layer,
        "generated_at": generated_at,
        "input_fingerprint": input_fingerprint or _default_fingerprint(nodes, edges),
        "counts": {"files": len({str(n.get("source_file") or "") for n in nodes}),
                   "nodes": len(nodes), "edges": len(edges)},
        "nodes": list(nodes),
        "edges": list(edges),
    }
    payload.update(extra)
    return payload


def cluster_payload(communities, *, layer: str = "project",
                    input_fingerprint: str = "",
                    cluster_builder_version: str | None = None,
                    graph_builder_version: str | None = None,
                    betweenness: dict | None = None, **extra) -> dict:
    payload = {
        "cluster_schema_version": graph_cluster.CLUSTER_SCHEMA_VERSION,
        "cluster_builder_version": (
            cluster_builder_version if cluster_builder_version is not None
            else graph_cluster.CLUSTER_BUILDER_VERSION),
        "graph_builder_version": (
            graph_builder_version if graph_builder_version is not None
            else graph_indexer.GRAPH_BUILDER_VERSION),
        "cluster_algorithm": "fixture",
        "layer": layer,
        "input_fingerprint": input_fingerprint,
        "community_count": len(communities),
        "communities": [dict(c) for c in communities],
        "betweenness": betweenness or {"method": "fixture", "ranking": [],
                                       "node_count": 0, "edge_count": 0,
                                       "elapsed_ms": 0},
    }
    payload.update(extra)
    return payload


def _default_fingerprint(nodes, edges) -> str:
    import hashlib

    blob = json.dumps([nodes, edges], sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:32]


def publish_graph(root, *, nodes=(), edges=(), communities=None,
                  layer: str = "project", builder_version: str | None = None,
                  graph: dict | None = None, clusters: dict | None = None,
                  scope: str = "graph") -> dict:
    """Commit ONE published generation carrying ``nodes``/``edges``/communities.

    Returns ``{"graph": payload, "clusters": payload|None, "generation": int}``.
    ``communities=None`` publishes no community rows (the legitimate
    graph-without-clusters state); ``communities=[]`` publishes an empty set.

    Deliberately does NOT clear the resident cache: production publication does
    not either, so a fixture that cleared it would hide exactly the
    cross-generation reuse and stale-cache behavior these tests exist to pin.
    """
    root = Path(root)
    index_dir = index_dir_for(root)
    index_dir.mkdir(parents=True, exist_ok=True)
    payload = graph if graph is not None else graph_payload(
        list(nodes), list(edges), layer=layer, builder_version=builder_version)
    # A published generation ALWAYS carries a fingerprint -- that is what
    # `graph_published_fingerprint` reads to decide a generation exists at all.
    # A caller-supplied payload without one would publish rows nothing can see.
    if not str(payload.get("input_fingerprint") or ""):
        payload = dict(payload)
        payload["input_fingerprint"] = _default_fingerprint(
            payload.get("nodes") or [], payload.get("edges") or [])
    cpayload = clusters
    if cpayload is None and communities is not None:
        cpayload = cluster_payload(
            communities, layer=layer,
            input_fingerprint=str(payload.get("input_fingerprint") or ""),
            graph_builder_version=str(payload.get("builder_version") or ""))

    attempt = index_state_store.begin_build_epoch(index_dir, scope)
    store = index_state_store.IndexStateStore(index_dir)
    try:
        conn = store._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            publication = _graph_publication(conn, payload, layer)
            # The graph publication carries `reset=True` (a fixture states the
            # WHOLE graph, the way a full rebuild does). The community diff is
            # therefore prepared AFTER the reset DELETEs land in this
            # transaction: prepared before them it would diff against rows the
            # reset is about to drop and re-insert only the CHANGED ones,
            # silently losing every unchanged community.
            publication.apply(conn)
            if cpayload is not None:
                graph_cluster.prepare_cluster_publication(
                    conn, layer=layer, payload=cpayload).apply(conn)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        store.close()
    assert index_state_store.finalize_build_epoch(index_dir, attempt), (
        "fixture publication lost the attempt CAS")
    state = index_state_store.read_build_state(index_dir)
    return {"graph": payload, "clusters": cpayload,
            "generation": int(state["generation"])}


def _graph_publication(conn, payload: dict, layer: str):
    """Encode one payload into a ``GraphPublication`` via the real row encoders."""
    node_rows: dict[str, list[tuple]] = {}
    for node in payload.get("nodes") or []:
        owner = str(node.get("source_file") or "")
        node_rows.setdefault(owner, []).append(graph_indexer._node_row(node, layer))
    edge_rows: dict[str, list[tuple]] = {}
    occurrence: dict[tuple, int] = {}
    for edge in payload.get("edges") or []:
        owner = str(edge.get("source_file") or "")
        if not owner:
            source = str(edge.get("source") or "")
            owner = source.split("::", 1)[0]
        key = (owner, str(edge.get("source") or ""), str(edge.get("target") or ""),
               str(edge.get("relation") or ""), str(edge.get("confidence") or ""),
               str(edge.get("evidence") or ""))
        n = occurrence.get(key, 0)
        occurrence[key] = n + 1
        edge_rows.setdefault(owner, []).append(
            graph_indexer._edge_row(edge, owner, n))

    header = {k: v for k, v in payload.items() if k not in ("nodes", "edges")}
    meta = {
        "schema_version": str(payload.get("schema_version") or ""),
        "builder_version": str(payload.get("builder_version") or ""),
        "payload_fingerprint": str(payload.get("input_fingerprint") or ""),
        "graph_rows_state": "published",
        "payload_header": json.dumps(header, separators=(",", ":"), sort_keys=True),
    }
    return graph_indexer.GraphPublication(
        layer=layer,
        reset=True,
        node_rows=node_rows,
        edge_rows=edge_rows,
        meta=meta,
        payload_fingerprint=str(payload.get("input_fingerprint") or ""),
    )


def bump_generation(root, *, scope: str = "graph", layer: str = "project") -> int:
    """Advance the published generation WITHOUT changing graph content.

    The cross-generation content-sharing path is only observable through a
    generation that moved over identical content, so tests need a way to make
    exactly that happen.
    """
    index_dir = index_dir_for(Path(root))
    attempt = index_state_store.begin_build_epoch(index_dir, scope)
    assert index_state_store.finalize_build_epoch(index_dir, attempt)
    return int(index_state_store.read_build_state(index_dir)["generation"])


_GRAPH_VIEW_KEYS = ("present", "graph_path", "generation", "graph_generation")
_CLUSTER_VIEW_KEYS = ("present", "cluster_path", "graph_path", "generation",
                      "community_generation", "community_count")


def _strip_view_keys(payload: dict, keys) -> dict:
    return {k: v for k, v in payload.items() if k not in keys}


def publish_graph_payload(root, payload: dict, *, layer: str = "project",
                          builder_version: str | None = None) -> dict:
    """Publish a new graph generation, PRESERVING the published communities.

    Fixtures that used to drop two independent JSON files now state one half at
    a time; a publication states the whole generation, so the other half is
    carried forward rather than silently dropped.

    The builder version defaults to the RUNTIME constant, overriding whatever
    placeholder the fixture payload carried. That placeholder used to be inert:
    the staleness probe read a separate state file, so an artifact claiming
    builder "1" never triggered anything. Now the published payload IS what the
    probe reads, so leaving the placeholder would make every fixture look like
    a pre-upgrade graph and fire a real rebuild against the test repository.
    Tests that WANT the stale path pass ``builder_version`` explicitly.
    """
    snapshot = graph_snapshot.acquire(root, layer)
    clusters = (_strip_view_keys(snapshot.clusters, _CLUSTER_VIEW_KEYS)
                if snapshot.clusters_present else None)
    graph = _strip_view_keys(payload, _GRAPH_VIEW_KEYS)
    # A merged payload always carries these; a fixture literal often did not,
    # and health now reports `generated_at` rather than an artifact mtime.
    graph.setdefault("generated_at", "2026-01-01T00:00:00Z")
    graph.setdefault("schema_version", graph_indexer.GRAPH_SCHEMA_VERSION)
    graph.setdefault("counts", {
        "files": len({str(n.get("source_file") or "")
                      for n in (graph.get("nodes") or [])}),
        "nodes": len(graph.get("nodes") or []),
        "edges": len(graph.get("edges") or []),
    })
    graph["builder_version"] = (
        graph_indexer.GRAPH_BUILDER_VERSION if builder_version is None
        else str(builder_version))
    return publish_graph(root, graph=graph, clusters=clusters, layer=layer)


def publish_cluster_payload(root, payload: dict, *, layer: str = "project") -> dict:
    """Publish a new community generation, PRESERVING the published graph."""
    snapshot = graph_snapshot.acquire(root, layer)
    graph = (_strip_view_keys(snapshot.graph, _GRAPH_VIEW_KEYS)
             if snapshot.present else graph_payload([], [], layer=layer))
    return publish_graph(root, graph=graph,
                         clusters=_strip_view_keys(payload, _CLUSTER_VIEW_KEYS),
                         layer=layer)


def unpublish_graph(root, *, layer: str = "project") -> None:
    """Leave the store with NO published graph generation.

    The pre-1xny6 way to express this was deleting the graph folder. Rows
    outlive that folder, so absence is now stated where it actually lives:
    the graph rows and the ``graph:`` meta that marks them published are
    dropped together, in one transaction, exactly as a scoped reset does.
    """
    import graph_store

    root = Path(root)
    index_dir = index_dir_for(root)
    store = index_state_store.IndexStateStore(index_dir)
    try:
        conn = store._conn
        conn.execute("BEGIN IMMEDIATE")
        try:
            for table in graph_store.GRAPH_TABLES:
                conn.execute(f"DELETE FROM {table}")
            conn.execute("DELETE FROM meta WHERE key LIKE ?",
                         (graph_indexer.GRAPH_META_PREFIX + "%",))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    finally:
        store.close()
    graph_snapshot.invalidate(root, layer)

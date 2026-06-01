"""Read-only graph query helpers over persisted project/framework graph artifacts."""

from __future__ import annotations

import importlib.util
import math
import sys
from collections import deque
from pathlib import Path
from typing import Any, Iterable, Literal

Layer = Literal["project", "framework", "union"]
Direction = Literal["callers", "callees", "both"]
ReportSection = Literal["fan_in", "fan_out", "orphan_docs", "chokepoints", "file_hubs", "cross_layer", "betweenness"]

_BETWEENNESS_NODE_LIMIT = 10_000

_DEFAULT_IMPACT_RELATIONS = ("imports", "calls")
_DEFAULT_CALL_RELATIONS = ("calls",)
_DOC_KINDS = frozenset({"doc", "seed"})
_CHOKEPOINT_FAN_OUT = 20

_GRAPH_INDEXER_MOD = None


def _get_graph_indexer():
    global _GRAPH_INDEXER_MOD
    if _GRAPH_INDEXER_MOD is None:
        path = Path(__file__).resolve().parent / "graph_indexer.py"
        spec = importlib.util.spec_from_file_location("graph_query_graph_indexer", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load graph_indexer from {path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        _GRAPH_INDEXER_MOD = mod
    return _GRAPH_INDEXER_MOD


def load_graph(root: Path, *, layer: str = "project") -> dict[str, Any]:
    """Load one graph layer. Returns payload with nodes/edges; ``present=False`` when missing."""
    if layer not in ("project", "framework"):
        raise ValueError(f"Unsupported graph layer: {layer}")
    payload = _get_graph_indexer().read_graph_payload(root, layer)
    return payload


def _networkx_unavailable_message() -> str:
    return (
        "networkx is required for union graph queries. "
        "Install via: python3 .wavefoundry/framework/scripts/setup_index.py"
    )


def load_union(root: Path) -> dict[str, Any]:
    """Compose project + framework graphs at query time; no file is written."""
    project = load_graph(root, layer="project")
    framework = load_graph(root, layer="framework")
    if not project.get("present") and not framework.get("present"):
        return {
            "layer": "union",
            "present": False,
            "nodes": [],
            "edges": [],
            "counts": {"files": 0, "nodes": 0, "edges": 0},
            "diagnostic": "graph_not_ready",
        }
    try:
        import networkx as nx
    except ImportError:
        return {
            "layer": "union",
            "present": False,
            "nodes": [],
            "edges": [],
            "counts": {"files": 0, "nodes": 0, "edges": 0},
            "diagnostic": "networkx_unavailable",
            "message": _networkx_unavailable_message(),
        }

    g_project = nx.DiGraph()
    g_framework = nx.DiGraph()
    for node in project.get("nodes") or []:
        if isinstance(node, dict) and node.get("id"):
            attrs = dict(node)
            attrs["layer"] = "project"
            g_project.add_node(node["id"], **attrs)
    for node in framework.get("nodes") or []:
        if isinstance(node, dict) and node.get("id"):
            attrs = dict(node)
            attrs["layer"] = "framework"
            g_framework.add_node(node["id"], **attrs)
    for edge in project.get("edges") or []:
        if isinstance(edge, dict) and edge.get("source") and edge.get("target"):
            g_project.add_edge(edge["source"], edge["target"], **edge)
    for edge in framework.get("edges") or []:
        if isinstance(edge, dict) and edge.get("source") and edge.get("target"):
            g_framework.add_edge(edge["source"], edge["target"], **edge)

    composed = nx.compose(g_project, g_framework)
    nodes = [dict(composed.nodes[nid]) | {"id": nid} for nid in composed.nodes]
    edges = [
        {"source": u, "target": v, **data}
        for u, v, data in composed.edges(data=True)
    ]
    project_files = int((project.get("counts") or {}).get("files") or 0)
    framework_files = int((framework.get("counts") or {}).get("files") or 0)
    return {
        "layer": "union",
        "present": True,
        "nodes": nodes,
        "edges": edges,
        "counts": {
            "files": project_files + framework_files,
            "nodes": len(nodes),
            "edges": len(edges),
        },
    }


def collapse_generated_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a payload where each generated file is collapsed to one file-node (wave 130rj — 130su).

    Aggregation rules:
    - Each generated source file gets ONE representative node (id == source_file).
      If a module-level node already exists for that file (id matching source_file),
      it is repurposed; otherwise a synthetic file-node is created.
    - All non-module nodes carrying ``generated: true`` are dropped.
    - Edges where BOTH endpoints belong to the same generated file are dropped.
    - Edges where ONE endpoint is inside a generated file have that endpoint
      rewritten to the file-node id (the source_file path).
    - Edges where both endpoints are in DIFFERENT generated files have both
      rewritten. Duplicate rewritten edges (same src/tgt/relation/confidence)
      are deduplicated.
    - Edge metadata that referenced specific lines/snippets inside the
      collapsed file (``line``/``snippet`` fields on outgoing edges) is dropped
      because the internal symbol it pointed at is no longer present.

    Non-generated nodes and edges between non-generated endpoints are passed
    through unchanged.

    The collapsed file-node carries:
    - ``id``: source_file path (e.g. ``src/ELParser.java``)
    - ``label``: file basename
    - ``kind``: ``"module"``
    - ``source_file``: source_file
    - ``source_location``: ``"1:0"``
    - ``generated``: ``True``
    - ``collapsed_node_count``: count of non-module nodes that were rolled up
    """
    nodes_in = list(payload.get("nodes") or [])
    edges_in = list(payload.get("edges") or [])

    # Group generated symbol-nodes by source_file. Module-level generated nodes
    # (id == source_file) are tracked separately so we can repurpose them as the
    # file-node rather than creating a duplicate.
    generated_symbol_ids_by_file: dict[str, set[str]] = {}
    generated_module_node_by_file: dict[str, dict[str, Any]] = {}
    for node in nodes_in:
        if not isinstance(node, dict):
            continue
        if not node.get("generated"):
            continue
        src_file = str(node.get("source_file") or "")
        nid = str(node.get("id") or "")
        if not src_file or not nid:
            continue
        if nid == src_file:
            # Module-level node for the generated file — keep as file-node base.
            generated_module_node_by_file[src_file] = node
        else:
            generated_symbol_ids_by_file.setdefault(src_file, set()).add(nid)

    # Collapsed-out node ids that should disappear from the result.
    collapsed_node_ids: set[str] = set()
    for sym_ids in generated_symbol_ids_by_file.values():
        collapsed_node_ids |= sym_ids

    # Build replacement file-nodes (id == source_file). If an existing module
    # node was already there, repurpose it; otherwise synthesize a fresh one.
    file_nodes: dict[str, dict[str, Any]] = {}
    all_generated_files: set[str] = set(generated_symbol_ids_by_file.keys()) | set(generated_module_node_by_file.keys())
    for src_file in all_generated_files:
        symbol_count = len(generated_symbol_ids_by_file.get(src_file, set()))
        existing = generated_module_node_by_file.get(src_file)
        if existing is not None:
            file_node = dict(existing)
        else:
            label = src_file.rsplit("/", 1)[-1]
            file_node = {
                "id": src_file,
                "label": label,
                "kind": "module",
                "source_file": src_file,
                "source_location": "1:0",
            }
            # Inherit layer if present on any of the collapsed nodes.
            for node in nodes_in:
                if (
                    isinstance(node, dict)
                    and node.get("source_file") == src_file
                    and node.get("layer")
                ):
                    file_node["layer"] = node["layer"]
                    break
        file_node["generated"] = True
        file_node["collapsed_node_count"] = symbol_count
        file_nodes[src_file] = file_node

    # Build the output node list: keep non-collapsed nodes; replace module
    # generated nodes with the file-node; drop generated symbol nodes.
    out_nodes: list[dict[str, Any]] = []
    for node in nodes_in:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("id") or "")
        if nid in collapsed_node_ids:
            continue  # generated symbol node — dropped
        if nid in generated_module_node_by_file:
            continue  # will be re-added from file_nodes below
        out_nodes.append(node)
    for file_node in file_nodes.values():
        out_nodes.append(file_node)

    def _rewrite_endpoint(node_id: str) -> str:
        """Map a node id to its post-collapse equivalent."""
        if node_id in collapsed_node_ids:
            # Symbol node inside a generated file → rewrite to file-node id (source_file).
            # Find the source_file via the original nodes list.
            for node in nodes_in:
                if isinstance(node, dict) and node.get("id") == node_id:
                    return str(node.get("source_file") or node_id)
            return node_id
        return node_id

    # Edge processing:
    # - Drop edges where both endpoints map to the same file-node (internal).
    # - Rewrite endpoints; dedupe by (src, tgt, relation, confidence).
    # - Drop line/snippet on edges where an endpoint was rewritten (the line
    #   pointed at an internal symbol that no longer exists).
    seen_edge_keys: set[tuple[str, str, str, str]] = set()
    out_edges: list[dict[str, Any]] = []
    for edge in edges_in:
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("source") or "")
        tgt = str(edge.get("target") or "")
        if not src or not tgt:
            continue
        new_src = _rewrite_endpoint(src)
        new_tgt = _rewrite_endpoint(tgt)
        # If both endpoints belong to the same collapsed file, drop the edge.
        if new_src == new_tgt and new_src in file_nodes:
            continue
        rewritten = new_src != src or new_tgt != tgt
        relation = str(edge.get("relation") or "")
        confidence = str(edge.get("confidence") or "")
        key = (new_src, new_tgt, relation, confidence)
        if key in seen_edge_keys:
            continue
        seen_edge_keys.add(key)
        new_edge = dict(edge)
        new_edge["source"] = new_src
        new_edge["target"] = new_tgt
        if rewritten:
            new_edge.pop("line", None)
            new_edge.pop("snippet", None)
        out_edges.append(new_edge)

    # Build the output payload, preserving layer/present markers.
    out_payload = dict(payload)
    out_payload["nodes"] = out_nodes
    out_payload["edges"] = out_edges
    return out_payload


# Swift-first language enablement for collapse_class_module_view (wave 13129 — 1312h).
# Extension to other languages is operator-validation-driven; do not pre-emptively
# enable Java/Kotlin/C# without operator reports — those languages have edge cases
# (Java inner classes, Kotlin companion objects, C# multi-class-per-file convention)
# that warrant their own validation cycles.
_CLASS_MODULE_COLLAPSE_LANGUAGES: dict[str, set[str]] = {
    # Map extension → {kinds that count as the top-level "class" for collapse}.
    # Swift: class / struct / actor / enum / protocol all qualify as the single
    # top-level type when the file basename matches.
    ".swift": {"class", "struct", "actor", "enum", "protocol"},
}


def collapse_class_module_view(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a payload where each file+top-level-class pair is collapsed (wave 13129 — 1312h).

    For Swift (initial scope): when a file like ``Foo.swift`` contains a top-level
    type ``class Foo`` / ``struct Foo`` / ``actor Foo`` / etc. (basename match),
    the file node and the class node aggregate into a single node:

    - Id remains the file path (file node's id wins; class node id is rewritten).
    - Label takes the class name.
    - ``kind`` stays ``"module"`` for backward compat (queries against file paths
      still work).
    - ``collapsed_pair: True`` discriminator.
    - Incoming/outgoing edges from both nodes merge with dedup on
      ``(src, tgt, relation, confidence)``.

    Files without a matching top-level class are unaffected. Classes without a
    matching file (e.g., multi-class files where no class name matches the
    basename) are unaffected. Non-Swift files are unaffected (other languages
    extend the dispatch table when operator-validated).

    Per-symbol navigation tools (code_callhierarchy, code_impact, code_callgraph,
    code_graph_path) deliberately do NOT consume this view — they need the
    unmodified per-symbol graph.
    """
    nodes_in = list(payload.get("nodes") or [])
    edges_in = list(payload.get("edges") or [])

    # Index nodes by id for quick lookup.
    nodes_by_id: dict[str, dict[str, Any]] = {}
    for node in nodes_in:
        if isinstance(node, dict):
            nid = str(node.get("id") or "")
            if nid:
                nodes_by_id[nid] = node

    # Identify class/module pairs: for each file node (kind=module, id matches a
    # source_file path), check if a matching top-level type node exists at
    # ``<file>::<basename>`` with a kind in the language's set.
    collapse_pairs: dict[str, str] = {}  # class_node_id → file_node_id
    pair_label_by_file: dict[str, str] = {}
    for node in nodes_in:
        if not isinstance(node, dict):
            continue
        if node.get("kind") != "module":
            continue
        file_id = str(node.get("id") or "")
        if not file_id:
            continue
        # Extract extension.
        ext_idx = file_id.rfind(".")
        slash_idx = file_id.rfind("/")
        if ext_idx <= slash_idx:
            continue
        ext = file_id[ext_idx:]
        if ext not in _CLASS_MODULE_COLLAPSE_LANGUAGES:
            continue
        allowed_kinds = _CLASS_MODULE_COLLAPSE_LANGUAGES[ext]
        basename = file_id[slash_idx + 1:ext_idx]
        if not basename:
            continue
        candidate_id = f"{file_id}::{basename}"
        candidate = nodes_by_id.get(candidate_id)
        if candidate is None:
            continue
        if candidate.get("kind") not in allowed_kinds:
            continue
        collapse_pairs[candidate_id] = file_id
        pair_label_by_file[file_id] = basename

    if not collapse_pairs:
        # No pairs → return unchanged payload (cheap no-op).
        return dict(payload)

    # Build the output node list: drop the class nodes, repurpose file nodes.
    out_nodes: list[dict[str, Any]] = []
    for node in nodes_in:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("id") or "")
        if nid in collapse_pairs:
            # Class node — drop; the file node carries the merged identity.
            continue
        if nid in pair_label_by_file:
            # File node — repurpose with class label + collapsed_pair marker.
            merged = dict(node)
            merged["label"] = pair_label_by_file[nid]
            merged["collapsed_pair"] = True
            out_nodes.append(merged)
        else:
            out_nodes.append(node)

    # Edge rewriting: any edge endpoint that was the class node id becomes the file id.
    seen_edge_keys: set[tuple[str, str, str, str]] = set()
    out_edges: list[dict[str, Any]] = []
    for edge in edges_in:
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("source") or "")
        tgt = str(edge.get("target") or "")
        if not src or not tgt:
            continue
        new_src = collapse_pairs.get(src, src)
        new_tgt = collapse_pairs.get(tgt, tgt)
        # Drop edges that collapse to self-loops on the merged node.
        if new_src == new_tgt and new_src in pair_label_by_file:
            continue
        relation = str(edge.get("relation") or "")
        confidence = str(edge.get("confidence") or "")
        key = (new_src, new_tgt, relation, confidence)
        if key in seen_edge_keys:
            continue
        seen_edge_keys.add(key)
        new_edge = dict(edge)
        new_edge["source"] = new_src
        new_edge["target"] = new_tgt
        out_edges.append(new_edge)

    out_payload = dict(payload)
    out_payload["nodes"] = out_nodes
    out_payload["edges"] = out_edges
    return out_payload


class GraphQueryIndex:
    """In-memory adjacency index over a loaded graph payload."""

    __slots__ = ("layer", "present", "builder_version", "nodes", "edges", "_out", "_in", "_node_by_id")

    def __init__(self, payload: dict[str, Any]):
        self.layer = str(payload.get("layer") or "project")
        self.present = bool(payload.get("present"))
        # Wave 13129 (1312l delivery review): expose builder_version so
        # query-time consumers can short-circuit redundant work on graphs
        # the indexer already cleaned up (e.g., the code_callhierarchy
        # receiver-type filter is no-op on v13+ graphs).
        self.builder_version = str(payload.get("builder_version") or "")
        self.nodes: list[dict[str, Any]] = list(payload.get("nodes") or [])
        self.edges: list[dict[str, Any]] = list(payload.get("edges") or [])
        self._node_by_id: dict[str, dict[str, Any]] = {}
        self._out: dict[str, list[dict[str, Any]]] = {}
        self._in: dict[str, list[dict[str, Any]]] = {}
        for node in self.nodes:
            nid = node.get("id")
            if isinstance(nid, str) and nid:
                self._node_by_id[nid] = node
        for edge in self.edges:
            src = edge.get("source")
            tgt = edge.get("target")
            if not isinstance(src, str) or not isinstance(tgt, str):
                continue
            self._out.setdefault(src, []).append(edge)
            self._in.setdefault(tgt, []).append(edge)

    @classmethod
    def from_root(cls, root: Path, *, layer: str = "project") -> GraphQueryIndex:
        if layer == "union":
            return cls(load_union(root))
        return cls(load_graph(root, layer=layer))

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        return self._node_by_id.get(node_id)

    def resolve_symbol(self, symbol: str) -> str | None:
        """Resolve a symbol string to a graph node id."""
        symbol = symbol.strip()
        if not symbol:
            return None
        if symbol in self._node_by_id:
            return symbol
        # Suffix match on qualified names
        matches = [nid for nid in self._node_by_id if nid.endswith(f"::{symbol}") or nid == symbol]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            # Prefer shortest id (most specific path prefix)
            return sorted(matches, key=len)[0]
        # Bare symbol name
        by_label = [
            nid for nid, node in self._node_by_id.items()
            if node.get("label") == symbol or nid.split("::")[-1] == symbol
        ]
        if len(by_label) == 1:
            return by_label[0]
        return None

    def traverse(
        self,
        start_id: str,
        *,
        relations: Iterable[str] | None = None,
        max_hops: int = 1,
        direction: Direction = "callees",
    ) -> tuple[set[str], list[dict[str, Any]], bool]:
        """BFS traversal; returns (visited node ids, traversed edges, has_cycles).

        Edges are deduplicated by (source, target, relation). ``has_cycles`` is
        True when a back-edge to an already-visited node is encountered; the
        back-edge is still included in ``traversed`` so callers can inspect it.
        """
        rel_set = set(relations) if relations is not None else None
        visited: set[str] = {start_id}
        traversed: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        has_cycles = False
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= max_hops:
                continue
            edge_lists: list[list[dict[str, Any]]] = []
            if direction in ("callees", "both"):
                edge_lists.append(self._out.get(current, []))
            if direction in ("callers", "both"):
                edge_lists.append(self._in.get(current, []))
            for edges in edge_lists:
                for edge in edges:
                    rel = edge.get("relation")
                    if rel_set is not None and rel not in rel_set:
                        continue
                    neighbor = edge["target"] if edge.get("source") == current else edge.get("source")
                    if not isinstance(neighbor, str):
                        continue
                    edge_key = (str(edge.get("source", "")), str(edge.get("target", "")), str(rel))
                    if edge_key in seen_edges:
                        continue
                    seen_edges.add(edge_key)
                    if neighbor in visited:
                        has_cycles = True
                    else:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1))
                    traversed.append(edge)
        return visited, traversed, has_cycles

    def one_hop_neighbors(
        self,
        node_ids: Iterable[str],
        *,
        relations: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        rel_set = set(relations) if relations is not None else None
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        for start in node_ids:
            if start not in self._node_by_id:
                continue
            nodes[start] = self._node_by_id[start]
            for edge in self._out.get(start, []) + self._in.get(start, []):
                rel = edge.get("relation")
                if rel_set is not None and rel not in rel_set:
                    continue
                src = edge.get("source")
                tgt = edge.get("target")
                if not isinstance(src, str) or not isinstance(tgt, str):
                    continue
                key = (src, tgt, str(rel))
                if key in seen_edges:
                    continue
                seen_edges.add(key)
                edges.append(edge)
                for nid in (src, tgt):
                    if nid in self._node_by_id:
                        nodes[nid] = self._node_by_id[nid]
        return {
            "present": True,
            "layer": self.layer,
            "nodes": list(nodes.values()),
            "edges": edges,
            "note": "1-hop structural neighbors; on by default, suppress with graph=false",
        }

    def shortest_path(
        self,
        from_symbol: str,
        to_symbol: str,
        *,
        relations: Iterable[str] | None = None,
        max_hops: int = 10,
        direction: str = "forward",
    ) -> dict[str, Any]:
        """BFS shortest path between two symbols.

        Returns ``{found, path_nodes, path_edges, hop_count}`` always — empty lists
        and ``hop_count: 0`` when no path is found. Uses BFS (unweighted edges).

        ``direction`` controls which edges BFS may walk:
        - ``"forward"`` (default): outgoing edges only — answers "does from reach to?"
        - ``"backward"``: incoming edges only — answers "is from reached by to?"
        - ``"either"``: outgoing or incoming; each ``path_edges`` entry carries an
          extra ``traversal_direction`` field (``"forward"`` or ``"backward"``) so
          the chain is unambiguous. Answers "are from and to coupled at all?"
        """
        direction_value = (direction or "forward").strip().lower()
        if direction_value not in ("forward", "backward", "either"):
            raise ValueError(
                f"direction must be 'forward', 'backward', or 'either'; got {direction!r}"
            )

        from_id = self.resolve_symbol(from_symbol)
        to_id = self.resolve_symbol(to_symbol)

        empty: dict[str, Any] = {"found": False, "path_nodes": [], "path_edges": [], "hop_count": 0}
        if from_id is None or to_id is None:
            return empty

        if from_id == to_id:
            n = self._node_by_id.get(from_id, {})
            return {
                "found": True,
                "path_nodes": [{"node_id": from_id, "label": n.get("label", from_id), "kind": n.get("kind"), "source_file": n.get("source_file")}],
                "path_edges": [],
                "hop_count": 0,
            }

        rel_set = set(relations) if relations is not None else None
        annotate_direction = direction_value == "either"
        # State: (current_id, path_node_ids, path_edges)
        queue: deque[tuple[str, list[str], list[dict[str, Any]]]] = deque([(from_id, [from_id], [])])
        visited: set[str] = {from_id}

        while queue:
            current, path_ids, path_edges = queue.popleft()
            if len(path_edges) >= max_hops:
                continue
            # Candidate edges to walk from current node, in deterministic order
            candidates: list[tuple[dict[str, Any], str, str]] = []  # (edge, neighbor, traversal_dir)
            if direction_value in ("forward", "either"):
                for edge in self._out.get(current, []):
                    rel = edge.get("relation")
                    if rel_set is not None and rel not in rel_set:
                        continue
                    neighbor = edge.get("target")
                    if isinstance(neighbor, str):
                        candidates.append((edge, neighbor, "forward"))
            if direction_value in ("backward", "either"):
                for edge in self._in.get(current, []):
                    rel = edge.get("relation")
                    if rel_set is not None and rel not in rel_set:
                        continue
                    neighbor = edge.get("source")
                    if isinstance(neighbor, str):
                        candidates.append((edge, neighbor, "backward"))
            # Tie-break by neighbor-id length (shortest first) for deterministic output
            candidates.sort(key=lambda c: (len(c[1]), c[1]))
            for edge, neighbor, trav_dir in candidates:
                if neighbor in visited:
                    continue
                new_edge = dict(edge)
                if annotate_direction:
                    new_edge["traversal_direction"] = trav_dir
                new_ids = path_ids + [neighbor]
                new_edges = path_edges + [new_edge]
                if neighbor == to_id:
                    path_nodes = []
                    for nid in new_ids:
                        n = self._node_by_id.get(nid, {})
                        path_nodes.append({"node_id": nid, "label": n.get("label", nid), "kind": n.get("kind"), "source_file": n.get("source_file")})
                    return {"found": True, "path_nodes": path_nodes, "path_edges": new_edges, "hop_count": len(new_edges)}
                visited.add(neighbor)
                queue.append((neighbor, new_ids, new_edges))

        return empty

    def graph_impact(
        self,
        symbol: str,
        *,
        max_hops: int = 3,
        relations: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        node_id = self.resolve_symbol(symbol)
        if node_id is None:
            return {"symbol": symbol, "resolved": False, "affected": [], "edges": []}
        rels = tuple(relations) if relations is not None else _DEFAULT_IMPACT_RELATIONS
        # Per-node hop distance (wave 130rj — Aceiss field feedback §2.4):
        # the existing traverse() doesn't expose per-node depth, so do our
        # own BFS to record the minimum hop count to each visited node.
        # Edges are deduplicated by (source, target, relation) for parity
        # with traverse().
        rel_set = set(rels)
        node_depth: dict[str, int] = {node_id: 0}
        traversed: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        has_cycles = False
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= max_hops:
                continue
            for edge in self._in.get(current, []):
                rel = edge.get("relation")
                if rel not in rel_set:
                    continue
                src = edge.get("source")
                if not isinstance(src, str):
                    continue
                edge_key = (str(edge.get("source", "")), str(edge.get("target", "")), str(rel))
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                if src in node_depth:
                    has_cycles = True
                else:
                    node_depth[src] = depth + 1
                    queue.append((src, depth + 1))
                traversed.append(edge)
        affected: list[dict[str, Any]] = []
        seen_files: set[str] = set()
        for nid in sorted(node_depth):
            if nid == node_id:
                continue
            node = self._node_by_id.get(nid, {})
            source_file = node.get("source_file") or (nid.split("::")[0] if "::" in nid else nid)
            entry = {
                "node_id": nid,
                "label": node.get("label", nid),
                "kind": node.get("kind"),
                "source_file": source_file,
                "hop": node_depth[nid],
            }
            affected.append(entry)
            if isinstance(source_file, str):
                seen_files.add(source_file)
        return {
            "symbol": symbol,
            "resolved": True,
            "node_id": node_id,
            "affected": affected,
            "affected_files": sorted(seen_files),
            "edges": traversed,
            "has_cycles": has_cycles,
            "max_hops": max_hops,
            "relations": list(rels),
        }

    def callgraph(
        self,
        symbol: str,
        *,
        depth: int = 1,
        direction: Direction = "both",
    ) -> dict[str, Any]:
        node_id = self.resolve_symbol(symbol)
        if node_id is None:
            return {"symbol": symbol, "resolved": False, "nodes": [], "edges": []}
        visited, traversed, has_cycles = self.traverse(
            node_id,
            relations=_DEFAULT_CALL_RELATIONS,
            max_hops=depth,
            direction=direction,
        )
        nodes = [self._node_by_id[nid] for nid in sorted(visited) if nid in self._node_by_id]
        return {
            "symbol": symbol,
            "resolved": True,
            "node_id": node_id,
            "depth": depth,
            "direction": direction,
            "nodes": nodes,
            "edges": traversed,
            "has_cycles": has_cycles,
        }

    def report(
        self,
        *,
        limit: int = 20,
        sections: Iterable[str] | None = None,
        chokepoint_threshold: int = _CHOKEPOINT_FAN_OUT,
    ) -> dict[str, Any]:
        wanted = set(sections) if sections is not None else {
            "fan_in", "fan_out", "orphan_docs", "chokepoints", "file_hubs", "cross_layer",
        }
        fan_in_counts: dict[str, int] = {}
        fan_out_counts: dict[str, int] = {}
        for edge in self.edges:
            if edge.get("relation") != "calls":
                continue
            src = edge.get("source")
            tgt = edge.get("target")
            if isinstance(tgt, str):
                fan_in_counts[tgt] = fan_in_counts.get(tgt, 0) + 1
            if isinstance(src, str):
                fan_out_counts[src] = fan_out_counts.get(src, 0) + 1

        def _ranked(counts: dict[str, int]) -> list[dict[str, Any]]:
            rows = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
            return [
                {
                    "node_id": nid,
                    "count": count,
                    "label": (self._node_by_id.get(nid) or {}).get("label", nid),
                    "kind": (self._node_by_id.get(nid) or {}).get("kind"),
                }
                for nid, count in rows
            ]

        result: dict[str, Any] = {"layer": self.layer, "present": self.present}
        if "fan_in" in wanted:
            result["fan_in"] = _ranked(fan_in_counts)
        if "fan_out" in wanted:
            result["fan_out"] = _ranked(fan_out_counts)
        if "orphan_docs" in wanted:
            # Wave 13129 (1316t): track candidate total so an empty list can be
            # distinguished from "no doc nodes existed at all".
            doc_node_count = 0
            orphans: list[dict[str, Any]] = []
            for node in self.nodes:
                kind = node.get("kind")
                if kind not in _DOC_KINDS:
                    continue
                doc_node_count += 1
                nid = node.get("id")
                if not isinstance(nid, str):
                    continue
                has_any = bool(self._out.get(nid) or self._in.get(nid))
                has_doc_code = any(
                    e.get("relation") == "doc_references_code"
                    for e in self._out.get(nid, [])
                )
                if not has_any or not has_doc_code:
                    orphans.append({
                        "node_id": nid,
                        "label": node.get("label", nid),
                        "kind": kind,
                        "zero_edges": not has_any,
                        "missing_doc_references_code": not has_doc_code,
                    })
            result["orphan_docs"] = orphans[:limit]
            result["orphan_docs_candidates_total"] = doc_node_count
        if "chokepoints" in wanted:
            # Wave 13129 (1312d): chokepoints excludes kind:"module" entries.
            # File-level hubs go to the new `file_hubs` section instead.
            # Wave 13129 (1316t): candidates_total counts function/method/class
            # nodes with any fan_out > 0 (before threshold). Lets operators
            # distinguish "no candidates" from "candidates below threshold".
            chokepoint_candidates_total = sum(
                1 for nid, count in fan_out_counts.items()
                if count > 0
                and (self._node_by_id.get(nid) or {}).get("kind") != "module"
            )
            chokepoints = [
                {
                    "node_id": nid,
                    "fan_out": count,
                    "label": (self._node_by_id.get(nid) or {}).get("label", nid),
                }
                for nid, count in sorted(fan_out_counts.items(), key=lambda item: (-item[1], item[0]))
                if count >= chokepoint_threshold
                and (self._node_by_id.get(nid) or {}).get("kind") != "module"
            ][:limit]
            result["chokepoints"] = chokepoints
            result["chokepoints_candidates_total"] = chokepoint_candidates_total
            result["chokepoints_threshold"] = chokepoint_threshold
        if "file_hubs" in wanted:
            # Wave 13129 (1312d): file-level fan_out hubs — kind:"module" entries
            # that previously appeared in chokepoints alongside function-level
            # hotspots. Split into its own section so operators reading
            # chokepoints get a pure function/method/class ranking and operators
            # reading file_hubs get the file-level orientation independently.
            # Wave 13129 (1316t): candidates_total + threshold to distinguish
            # "no candidates" from "candidates below threshold".
            file_hubs_candidates_total = sum(
                1 for nid, count in fan_out_counts.items()
                if count > 0
                and (self._node_by_id.get(nid) or {}).get("kind") == "module"
            )
            file_hubs = [
                {
                    "node_id": nid,
                    "fan_out": count,
                    "label": (self._node_by_id.get(nid) or {}).get("label", nid),
                    "kind": "module",
                }
                for nid, count in sorted(fan_out_counts.items(), key=lambda item: (-item[1], item[0]))
                if count >= chokepoint_threshold
                and (self._node_by_id.get(nid) or {}).get("kind") == "module"
            ][:limit]
            result["file_hubs"] = file_hubs
            result["file_hubs_candidates_total"] = file_hubs_candidates_total
            result["file_hubs_threshold"] = chokepoint_threshold
        if "betweenness" in wanted:
            node_count = len(self.nodes)
            if node_count > _BETWEENNESS_NODE_LIMIT:
                result["betweenness"] = {
                    "diagnostic": "graph_too_large_for_betweenness",
                    "node_count": node_count,
                    "limit": _BETWEENNESS_NODE_LIMIT,
                }
            else:
                try:
                    import igraph as ig  # type: ignore[import]
                    node_list = list(self._node_by_id.keys())
                    node_index = {nid: i for i, nid in enumerate(node_list)}
                    edges_ig = [
                        (node_index[e["source"]], node_index[e["target"]])
                        for e in self.edges
                        if e.get("relation") == "calls"
                        and e.get("source") in node_index
                        and e.get("target") in node_index
                    ]
                    g = ig.Graph(n=len(node_list), edges=edges_ig, directed=True)
                    scores = g.betweenness(directed=True)
                    ranked = sorted(enumerate(scores), key=lambda x: -x[1])[:limit]
                    result["betweenness"] = [
                        {
                            "node_id": node_list[i],
                            "score": round(score, 4),
                            "label": (self._node_by_id.get(node_list[i]) or {}).get("label", node_list[i]),
                            "kind": (self._node_by_id.get(node_list[i]) or {}).get("kind"),
                        }
                        for i, score in ranked
                        if score > 0 and math.isfinite(score)
                    ][:limit]
                except ImportError:
                    result["betweenness"] = {"diagnostic": "igraph_unavailable"}
        if "cross_layer" in wanted and self.layer == "union":
            cross: list[dict[str, Any]] = []
            for edge in self.edges:
                src = edge.get("source")
                tgt = edge.get("target")
                if not isinstance(src, str) or not isinstance(tgt, str):
                    continue
                src_layer = (self._node_by_id.get(src) or {}).get("layer")
                tgt_layer = (self._node_by_id.get(tgt) or {}).get("layer")
                if src_layer and tgt_layer and src_layer != tgt_layer:
                    cross.append(edge)
            result["cross_layer"] = {
                "count": len(cross),
                "edges": cross[:limit],
            }
            # Wave 13129 (1316t): candidates_total = total cross-layer edges
            # found (same as the existing `count` field, surfaced as the
            # explicit diagnostic field for parity with other sections).
            result["cross_layer_candidates_total"] = len(cross)
        return result


def graph_not_ready_diagnostic(layer: str) -> dict[str, Any]:
    return {
        "code": "graph_not_ready",
        "message": f"Graph layer '{layer}' is not built yet. Run setup_index with graph indexing enabled.",
    }

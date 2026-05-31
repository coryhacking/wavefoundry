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
ReportSection = Literal["fan_in", "fan_out", "orphan_docs", "chokepoints", "cross_layer", "betweenness"]

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


class GraphQueryIndex:
    """In-memory adjacency index over a loaded graph payload."""

    __slots__ = ("layer", "present", "nodes", "edges", "_out", "_in", "_node_by_id")

    def __init__(self, payload: dict[str, Any]):
        self.layer = str(payload.get("layer") or "project")
        self.present = bool(payload.get("present"))
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
        visited, traversed, has_cycles = self.traverse(
            node_id,
            relations=rels,
            max_hops=max_hops,
            direction="callers",
        )
        visited.discard(node_id)
        affected: list[dict[str, Any]] = []
        seen_files: set[str] = set()
        for nid in sorted(visited):
            node = self._node_by_id.get(nid, {})
            source_file = node.get("source_file") or (nid.split("::")[0] if "::" in nid else nid)
            entry = {
                "node_id": nid,
                "label": node.get("label", nid),
                "kind": node.get("kind"),
                "source_file": source_file,
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
            "fan_in", "fan_out", "orphan_docs", "chokepoints", "cross_layer",
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
            orphans: list[dict[str, Any]] = []
            for node in self.nodes:
                kind = node.get("kind")
                if kind not in _DOC_KINDS:
                    continue
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
        if "chokepoints" in wanted:
            chokepoints = [
                {
                    "node_id": nid,
                    "fan_out": count,
                    "label": (self._node_by_id.get(nid) or {}).get("label", nid),
                }
                for nid, count in sorted(fan_out_counts.items(), key=lambda item: (-item[1], item[0]))
                if count >= chokepoint_threshold
            ][:limit]
            result["chokepoints"] = chokepoints
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
        return result


def graph_not_ready_diagnostic(layer: str) -> dict[str, Any]:
    return {
        "code": "graph_not_ready",
        "message": f"Graph layer '{layer}' is not built yet. Run setup_index with graph indexing enabled.",
    }

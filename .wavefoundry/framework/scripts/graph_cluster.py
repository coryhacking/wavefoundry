#!/usr/bin/env python3
"""Topology-based community clustering for Wavefoundry graph indexes."""
from __future__ import annotations

import importlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CLUSTER_SCHEMA_VERSION = "1"
CLUSTER_BUILDER_VERSION = "7"

# Document node kinds. These are pre-assigned to a single fixed "Documentation"
# community (like Tests/Configuration) before Leiden runs, so docs stay visible
# in the community overview without distorting the code communities.
_DOC_NODE_KINDS = {"doc", "seed"}
GRAPH_SCHEMA_VERSION = "1"
GRAPH_BUILDER_VERSION = "1"

MIN_COMMUNITY_SIZE = 12

_TEST_DIR_NAMES = {"test", "tests", "__tests__"}
_BENCH_DIR_NAMES = {"benchmarks", "benchmark"}
# Shallow-only: only match when within the first 2 path segments from root, to avoid
# misclassifying deep application directories named "scripts" as auxiliary scripts.
_SCRIPTS_SHALLOW_NAMES = {"scripts", "bin", "tools"}
# Any-depth: these names are specific enough to be considered scripts dirs anywhere.
_SCRIPTS_ANY_DEPTH_NAMES = {"cli", "tasks", "cmd", "hack"}
_GENERATED_DIR_NAMES = {"generated", "__generated__", "gen", "migrations", "stubs"}
_GENERATED_FILE_SUFFIXES = ("_pb2.py", "_pb2_grpc.py", "_generated.py", ".pb.go", ".generated.ts", ".generated.js")
_CICD_DIR_NAMES = {".github", ".gitlab", ".circleci", ".buildkite", "ci", ".drone"}
_CICD_FILENAMES = {"Dockerfile", "Jenkinsfile", ".travis.yml", ".drone.yml", "docker-compose.yml", "docker-compose.yaml"}
_CICD_PREFIXES = ("Dockerfile.", "docker-compose.")
_CONFIG_DIR_NAMES = {"config", "conf", "settings", "configuration"}
_CONFIG_FILE_SUFFIXES = (".config.js", ".config.ts", ".config.mjs", ".config.cjs", ".config.json")
_CONFIG_FILENAMES = {
    "pyproject.toml", "setup.cfg", "setup.py", "Cargo.toml", "go.mod", "go.sum",
    "composer.json", "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "tsconfig.json", "jsconfig.json",
    ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml",
    ".prettierrc", ".prettierrc.js", ".prettierrc.json",
    ".babelrc", ".babelrc.js", ".babelrc.json",
    "mypy.ini", "tox.ini", ".flake8", ".pylintrc", "pytest.ini",
    ".editorconfig", ".stylelintrc",
}

GRAPH_DIRNAME = "graph"
GRAPH_FILENAMES = {
    "project": "project-graph.json",
    "framework": "framework-graph.json",
}
CLUSTER_FILENAMES = {
    "project": "project-graph-clusters.json",
    "framework": "framework-graph-clusters.json",
}

_RELATION_WEIGHTS = {
    "calls": 3,
    "imports": 2,
    "defines": 1,
    "doc_references_code": 1,
}


def _graph_index_dir(root: Path, layer: str) -> Path:
    if layer not in GRAPH_FILENAMES:
        raise ValueError(f"Unsupported graph layer: {layer}")
    if layer == "framework":
        return root / ".wavefoundry" / "framework" / "index"
    return root / ".wavefoundry" / "index"


def graph_path(root: Path, layer: str) -> Path:
    return _graph_index_dir(root, layer) / GRAPH_DIRNAME / GRAPH_FILENAMES[layer]


def cluster_path(root: Path, layer: str) -> Path:
    return _graph_index_dir(root, layer) / GRAPH_DIRNAME / CLUSTER_FILENAMES[layer]


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_node_id(node_id: str) -> str:
    return str(node_id).replace("\\", "/")


def _node_label(node: dict[str, Any]) -> str:
    label = str(node.get("label") or "").strip()
    if label:
      return label
    node_id = str(node.get("id") or "").strip()
    if "::" in node_id:
        return node_id.rsplit("::", 1)[-1].split(".", 1)[-1]
    return Path(node_id).stem or node_id or "community"


def _community_seed(node_ids: set[str], nodes_by_id: dict[str, dict[str, Any]], adjacency: dict[str, dict[str, int]]) -> str:
    def sort_key(node_id: str) -> tuple[int, int, str, str]:
        degree = sum(adjacency.get(node_id, {}).values())
        node = nodes_by_id.get(node_id, {})
        label = _node_label(node)
        source_file = str(node.get("source_file") or "")
        return (-degree, len(source_file), label.casefold(), node_id)

    return min(node_ids, key=sort_key)


def _community_label(seed_node_id: str, nodes_by_id: dict[str, dict[str, Any]]) -> str:
    node = nodes_by_id.get(seed_node_id, {})
    label = _node_label(node)
    source_file = str(node.get("source_file") or "").strip()
    if source_file and source_file != seed_node_id:
        stem = Path(source_file).stem
        if stem and stem.casefold() not in {"index", "main"}:
            return stem
    return label or "community"


def _is_test_source_file(source_file: str) -> bool:
    if not source_file:
        return False
    parts = source_file.replace("\\", "/").split("/")
    filename = parts[-1]
    if filename.startswith("test_") or filename.endswith("_test.py"):
        return True
    return any(part in _TEST_DIR_NAMES for part in parts[:-1])


def _is_bench_source_file(source_file: str) -> bool:
    if not source_file:
        return False
    parts = source_file.replace("\\", "/").split("/")
    filename = parts[-1]
    if filename.startswith("bench_") or filename.endswith("_bench.py"):
        return True
    return any(part in _BENCH_DIR_NAMES for part in parts[:-1])


def _is_scripts_source_file(source_file: str) -> bool:
    if not source_file:
        return False
    parts = source_file.replace("\\", "/").split("/")
    dir_parts = parts[:-1]
    for i, part in enumerate(dir_parts):
        if part in _SCRIPTS_ANY_DEPTH_NAMES:
            return True
        if part in _SCRIPTS_SHALLOW_NAMES and i <= 1:
            return True
    return False


def _is_generated_source_file(source_file: str) -> bool:
    if not source_file:
        return False
    parts = source_file.replace("\\", "/").split("/")
    filename = parts[-1]
    if any(filename.endswith(suffix) for suffix in _GENERATED_FILE_SUFFIXES):
        return True
    return any(part in _GENERATED_DIR_NAMES for part in parts[:-1])


def _is_cicd_source_file(source_file: str) -> bool:
    if not source_file:
        return False
    parts = source_file.replace("\\", "/").split("/")
    filename = parts[-1]
    if filename in _CICD_FILENAMES:
        return True
    if any(filename.startswith(prefix) for prefix in _CICD_PREFIXES):
        return True
    return any(part in _CICD_DIR_NAMES for part in parts[:-1])


def _is_config_source_file(source_file: str) -> bool:
    if not source_file:
        return False
    parts = source_file.replace("\\", "/").split("/")
    filename = parts[-1]
    if filename in _CONFIG_FILENAMES:
        return True
    if any(filename.endswith(suffix) for suffix in _CONFIG_FILE_SUFFIXES):
        return True
    return any(part in _CONFIG_DIR_NAMES for part in parts[:-1])


def _extract_fixed_communities(
    nodes_by_id: dict[str, dict[str, Any]],
    adjacency: dict[str, dict[str, int]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, int]]]:
    """Separate test and benchmark nodes into fixed pre-assigned communities.

    Returns the fixed community records, and a reduced nodes_by_id and adjacency
    containing only production nodes for Leiden/label-prop to operate on.
    """
    # Ordered fixed categories. "Documentation" is kind-based (doc/seed nodes)
    # and checked first; the rest are source_file-path based.
    fixed_order = [
        "Documentation", "Tests", "Benchmarks", "CI/CD",
        "Generated", "Scripts", "Configuration",
    ]
    buckets: dict[str, set[str]] = {label: set() for label in fixed_order}
    # Checked in priority order — a file belongs to the first matching category.
    classifiers = [
        ("Tests", _is_test_source_file),
        ("Benchmarks", _is_bench_source_file),
        ("CI/CD", _is_cicd_source_file),
        ("Generated", _is_generated_source_file),
        ("Scripts", _is_scripts_source_file),
        ("Configuration", _is_config_source_file),
    ]
    for node_id, node in nodes_by_id.items():
        if str(node.get("kind") or "") in _DOC_NODE_KINDS:
            buckets["Documentation"].add(node_id)
            continue
        source_file = str(node.get("source_file") or "")
        for label, fn in classifiers:
            if fn(source_file):
                buckets[label].add(node_id)
                break
    fixed_node_ids: set[str] = set().union(*buckets.values())
    reduced_nodes = {nid: node for nid, node in nodes_by_id.items() if nid not in fixed_node_ids}
    reduced_adjacency: dict[str, dict[str, int]] = {
        nid: {nbr: w for nbr, w in neighbors.items() if nbr not in fixed_node_ids}
        for nid, neighbors in adjacency.items()
        if nid not in fixed_node_ids
    }
    fixed_communities: list[dict[str, Any]] = []
    for label in fixed_order:
        node_ids = buckets[label]
        if not node_ids:
            continue
        seed_node_id = _community_seed(node_ids, nodes_by_id, adjacency)
        internal_edges = 0
        boundary_nodes: set[str] = set()
        for node_id in node_ids:
            for neighbor in adjacency.get(node_id, {}):
                if neighbor in node_ids:
                    if node_id < neighbor:
                        internal_edges += 1
                else:
                    boundary_nodes.add(node_id)
        fixed_communities.append({
            "label": label,
            "seed_node_id": seed_node_id,
            "node_ids": sorted(node_ids),
            "node_count": len(node_ids),
            "edge_count": internal_edges,
            "boundary_node_count": len(boundary_nodes),
            "_fixed": True,
        })
    return fixed_communities, reduced_nodes, reduced_adjacency


def _run_clustering(
    adjacency: dict[str, dict[str, int]],
    nodes_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    if not nodes_by_id:
        return [], "empty"
    leiden_result = _build_leiden_clusters(adjacency, nodes_by_id)
    if leiden_result is not None:
        return leiden_result
    return _label_propagation(adjacency, nodes_by_id)


def _load_leiden_backend() -> tuple[Any, Any] | None:
    try:
        igraph = importlib.import_module("igraph")
        leidenalg = importlib.import_module("leidenalg")
    except Exception:
        return None
    if not hasattr(igraph, "Graph") or not hasattr(leidenalg, "find_partition"):
        return None
    return igraph, leidenalg


def _project_undirected_projection(graph_payload: dict[str, Any]) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, Any]], dict[str, int]]:
    nodes_by_id: dict[str, dict[str, Any]] = {}
    adjacency: dict[str, dict[str, int]] = defaultdict(dict)
    node_degrees: dict[str, int] = defaultdict(int)
    for raw_node in graph_payload.get("nodes", []) or []:
        if not isinstance(raw_node, dict):
            continue
        node_id = _normalize_node_id(str(raw_node.get("id") or ""))
        if not node_id or raw_node.get("kind") == "external" or node_id.startswith("external::"):
            continue
        node = dict(raw_node)
        node["id"] = node_id
        nodes_by_id[node_id] = node
        adjacency.setdefault(node_id, {})
    for raw_edge in graph_payload.get("edges", []) or []:
        if not isinstance(raw_edge, dict):
            continue
        source = _normalize_node_id(str(raw_edge.get("source") or ""))
        target = _normalize_node_id(str(raw_edge.get("target") or ""))
        if not source or not target or source == target:
            continue
        if source not in nodes_by_id or target not in nodes_by_id:
            continue
        weight = _RELATION_WEIGHTS.get(str(raw_edge.get("relation") or ""), 1)
        left, right = sorted((source, target))
        adjacency[left][right] = adjacency[left].get(right, 0) + weight
        adjacency[right][left] = adjacency[right].get(left, 0) + weight
        node_degrees[left] += weight
        node_degrees[right] += weight
    return adjacency, nodes_by_id, node_degrees


def _build_leiden_clusters(
    adjacency: dict[str, dict[str, int]],
    nodes_by_id: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], str] | None:
    backend = _load_leiden_backend()
    if backend is None:
        return None
    igraph, leidenalg = backend
    ordered_nodes = sorted(nodes_by_id)
    if not ordered_nodes:
        return [], "leiden"
    index_by_id = {node_id: index for index, node_id in enumerate(ordered_nodes)}
    edge_pairs: list[tuple[int, int]] = []
    edge_weights: list[int] = []
    for left in ordered_nodes:
        for right, weight in adjacency.get(left, {}).items():
            if left >= right:
                continue
            edge_pairs.append((index_by_id[left], index_by_id[right]))
            edge_weights.append(int(weight))
    graph = igraph.Graph(n=len(ordered_nodes), edges=edge_pairs, directed=False)
    if edge_weights:
        try:
            graph.es["weight"] = edge_weights
        except Exception:
            pass
    partition = None
    try:
        partition = leidenalg.find_partition(
            graph,
            leidenalg.RBConfigurationVertexPartition,
            weights="weight",
            seed=0,
        )
    except TypeError:
        try:
            partition = leidenalg.find_partition(
                graph,
                leidenalg.RBConfigurationVertexPartition,
                weights="weight",
            )
        except TypeError:
            partition = leidenalg.find_partition(graph, leidenalg.RBConfigurationVertexPartition)
    except Exception:
        return None
    membership = list(getattr(partition, "membership", []))
    if len(membership) != len(ordered_nodes):
        return None
    communities: dict[int, set[str]] = defaultdict(set)
    for node_id, cluster_index in zip(ordered_nodes, membership):
        communities[int(cluster_index)].add(node_id)
    cluster_records: list[dict[str, Any]] = []
    for _, node_ids in sorted(
        communities.items(),
        key=lambda item: (-len(item[1]), _community_seed(item[1], nodes_by_id, adjacency)),
    ):
        seed_node_id = _community_seed(node_ids, nodes_by_id, adjacency)
        label = _community_label(seed_node_id, nodes_by_id)
        internal_edges = 0
        boundary_nodes = set()
        for node_id in node_ids:
            for neighbor in adjacency.get(node_id, {}):
                if neighbor in node_ids:
                    if node_id < neighbor:
                        internal_edges += 1
                else:
                    boundary_nodes.add(node_id)
        cluster_records.append({
            "seed_node_id": seed_node_id,
            "label": label,
            "node_ids": sorted(node_ids),
            "node_count": len(node_ids),
            "edge_count": internal_edges,
            "boundary_node_count": len(boundary_nodes),
            "_seed_sort": seed_node_id,
        })
    return cluster_records, "leiden"


def _label_propagation(adjacency: dict[str, dict[str, int]], nodes_by_id: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    labels = {node_id: node_id for node_id in nodes_by_id}
    order = sorted(
        nodes_by_id,
        key=lambda node_id: (
            -sum(adjacency.get(node_id, {}).values()),
            str(nodes_by_id[node_id].get("kind") or ""),
            _node_label(nodes_by_id[node_id]).casefold(),
            node_id,
        ),
    )
    for _ in range(24):
        changed = False
        for node_id in order:
            weights: dict[str, int] = defaultdict(int)
            for neighbor, weight in adjacency.get(node_id, {}).items():
                weights[labels.get(neighbor, neighbor)] += weight
            if not weights:
                continue
            best_weight = max(weights.values())
            best_labels = sorted(label for label, weight in weights.items() if weight == best_weight)
            chosen = labels[node_id] if labels[node_id] in best_labels else best_labels[0]
            if labels[node_id] != chosen:
                labels[node_id] = chosen
                changed = True
        if not changed:
            break
    communities: dict[str, set[str]] = defaultdict(set)
    for node_id, label in labels.items():
        communities[label].add(node_id)
    cluster_records: list[dict[str, Any]] = []
    for _, node_ids in sorted(
        communities.items(),
        key=lambda item: (-len(item[1]), _community_seed(item[1], nodes_by_id, adjacency)),
    ):
        seed_node_id = _community_seed(node_ids, nodes_by_id, adjacency)
        label = _community_label(seed_node_id, nodes_by_id)
        internal_edges = 0
        boundary_nodes = set()
        for node_id in node_ids:
            for neighbor in adjacency.get(node_id, {}):
                if neighbor in node_ids:
                    if node_id < neighbor:
                        internal_edges += 1
                else:
                    boundary_nodes.add(node_id)
        cluster_records.append({
            "seed_node_id": seed_node_id,
            "label": label,
            "node_ids": sorted(node_ids),
            "node_count": len(node_ids),
            "edge_count": internal_edges,
            "boundary_node_count": len(boundary_nodes),
            "_seed_sort": seed_node_id,
        })
    return cluster_records, "label-propagation"


def _read_existing_clusters(path: Path) -> dict[str, Any]:
    data = _read_json(path, {})
    return data if isinstance(data, dict) else {}


def _next_cluster_id(existing_ids: set[str], layer: str) -> str:
    next_index = 0
    for community_id in existing_ids:
        if not community_id.startswith(f"{layer}:c"):
            continue
        suffix = community_id.rsplit("c", 1)[-1]
        if suffix.isdigit():
            next_index = max(next_index, int(suffix) + 1)
    return f"{layer}:c{next_index}"


def _remap_clusters(
    *,
    layer: str,
    new_clusters: list[dict[str, Any]],
    previous: dict[str, Any],
) -> list[dict[str, Any]]:
    previous_clusters = previous.get("communities") if isinstance(previous.get("communities"), list) else []
    previous_by_id: dict[str, set[str]] = {}
    previous_label_by_id: dict[str, str] = {}
    for community in previous_clusters:
        if not isinstance(community, dict):
            continue
        community_id = str(community.get("community_id") or "").strip()
        if not community_id:
            continue
        node_ids = {str(node_id) for node_id in (community.get("node_ids") or []) if str(node_id)}
        previous_by_id[community_id] = node_ids
        previous_label_by_id[community_id] = str(community.get("label") or "").strip()

    used_previous: set[str] = set()
    existing_ids = set(previous_by_id)
    next_cluster_id = _next_cluster_id(existing_ids, layer)
    next_cluster_index = int(next_cluster_id.rsplit("c", 1)[-1]) if next_cluster_id.rsplit("c", 1)[-1].isdigit() else 0

    def allocate_id() -> str:
        nonlocal next_cluster_index
        community_id = f"{layer}:c{next_cluster_index}"
        next_cluster_index += 1
        return community_id

    remapped: list[dict[str, Any]] = []
    for cluster in new_clusters:
        node_ids = set(cluster.get("node_ids") or [])
        best_id = None
        best_overlap = 0
        best_score = 0.0
        for community_id, prev_nodes in previous_by_id.items():
            if community_id in used_previous:
                continue
            overlap = len(node_ids.intersection(prev_nodes))
            if not overlap:
                continue
            score = overlap / max(len(node_ids), len(prev_nodes), 1)
            if overlap > best_overlap or (overlap == best_overlap and score > best_score) or (
                overlap == best_overlap and score == best_score and community_id < (best_id or community_id)
            ):
                best_id = community_id
                best_overlap = overlap
                best_score = score
        reuse_threshold = max(2, min(len(node_ids), len(previous_by_id.get(best_id, set()))) // 2) if best_id else 0
        if best_id and best_overlap >= reuse_threshold:
            community_id = best_id
            used_previous.add(best_id)
            label = previous_label_by_id.get(best_id) or str(cluster.get("label") or "").strip()
        else:
            community_id = allocate_id()
            label = str(cluster.get("label") or "").strip()
        entry: dict[str, Any] = {
            "community_id": community_id,
            "label": label or community_id,
            "seed_node_id": cluster.get("seed_node_id") or "",
            "node_ids": sorted(node_ids),
            "node_count": len(node_ids),
            "edge_count": int(cluster.get("edge_count") or 0),
            "boundary_node_count": int(cluster.get("boundary_node_count") or 0),
        }
        if cluster.get("_fixed"):
            entry["_fixed"] = True
        remapped.append(entry)
    return remapped


def read_cluster_payload(root: Path, layer: str) -> dict[str, Any]:
    path = cluster_path(root, layer)
    data = _read_json(path, {})
    if isinstance(data, dict) and data:
        data.setdefault("layer", layer)
        data.setdefault("cluster_schema_version", CLUSTER_SCHEMA_VERSION)
        data.setdefault("communities", [])
        data.setdefault("community_count", len(data.get("communities") or []))
        try:
            data["cluster_mtime"] = path.stat().st_mtime_ns
        except OSError:
            data["cluster_mtime"] = 0
        data["present"] = True
        data["cluster_path"] = str(path.relative_to(root)).replace("\\", "/")
        return data
    return {
        "layer": layer,
        "cluster_schema_version": CLUSTER_SCHEMA_VERSION,
        "cluster_mtime": 0,
        "present": False,
        "cluster_path": str(path.relative_to(root)).replace("\\", "/"),
        "communities": [],
        "community_count": 0,
    }


def _merge_same_stem_communities(
    communities: list[dict[str, Any]],
    nodes_by_id: dict[str, dict[str, Any]],
    adjacency: dict[str, dict[str, int]],
) -> list[dict[str, Any]]:
    """Merge communities whose seed nodes share the same directory and filename stem (e.g. dashboard.js + dashboard.css)."""
    from collections import defaultdict

    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    no_key: list[int] = []
    for i, c in enumerate(communities):
        seed_id = str(c.get("seed_node_id") or "")
        node = nodes_by_id.get(seed_id, {})
        source_file = str(node.get("source_file") or "")
        if source_file:
            p = Path(source_file)
            groups[(str(p.parent), p.stem)].append(i)
        else:
            no_key.append(i)

    result: list[dict[str, Any]] = []
    for indices in groups.values():
        if len(indices) == 1:
            result.append(communities[indices[0]])
            continue
        merged_ids: set[str] = set()
        for i in indices:
            merged_ids.update(communities[i].get("node_ids") or [])
        seed_node_id = _community_seed(merged_ids, nodes_by_id, adjacency)
        label = _community_label(seed_node_id, nodes_by_id)
        internal_edges = 0
        boundary_nodes: set[str] = set()
        for node_id in merged_ids:
            for neighbor in adjacency.get(node_id, {}):
                if neighbor in merged_ids:
                    if node_id < neighbor:
                        internal_edges += 1
                else:
                    boundary_nodes.add(node_id)
        primary = max(indices, key=lambda i: communities[i].get("node_count", 0))
        result.append({
            "community_id": communities[primary]["community_id"],
            "label": label,
            "seed_node_id": seed_node_id,
            "node_ids": sorted(merged_ids),
            "node_count": len(merged_ids),
            "edge_count": internal_edges,
            "boundary_node_count": len(boundary_nodes),
        })
    for i in no_key:
        result.append(communities[i])
    result.sort(key=lambda c: (-c.get("node_count", 0), str(c.get("seed_node_id") or "")))
    return result


def _merge_small_communities(
    communities: list[dict[str, Any]],
    nodes_by_id: dict[str, dict[str, Any]],
    adjacency: dict[str, dict[str, int]],
    min_size: int = MIN_COMMUNITY_SIZE,
) -> list[dict[str, Any]]:
    """Absorb non-fixed communities below min_size into their most-connected neighbor."""
    if len(communities) <= 1:
        return communities
    fixed = [c for c in communities if c.get("_fixed")]
    production = [c for c in communities if not c.get("_fixed")]
    changed = True
    while changed and len(production) > 1:
        changed = False
        small = None
        for c in production:
            if c.get("node_count", 0) < min_size:
                if small is None or c.get("node_count", 0) < small.get("node_count", 0):
                    small = c
        if small is None:
            break
        small_nodes = set(small.get("node_ids") or [])
        node_to_comm = {}
        for c in production:
            for nid in (c.get("node_ids") or []):
                node_to_comm[nid] = c
        neighbor_weights: dict[int, int] = defaultdict(int)
        neighbor_by_obj_id: dict[int, dict] = {}
        for nid in small_nodes:
            for nbr, weight in adjacency.get(nid, {}).items():
                if nbr in small_nodes:
                    continue
                nbr_comm = node_to_comm.get(nbr)
                if nbr_comm is None or nbr_comm is small:
                    continue
                key = id(nbr_comm)
                neighbor_weights[key] += weight
                neighbor_by_obj_id[key] = nbr_comm
        if not neighbor_weights:
            # No cross-community edges — fall back to the largest production community.
            candidates = [c for c in production if c is not small]
            if not candidates:
                break
            target_fallback = max(candidates, key=lambda c: c.get("node_count", 0))
            neighbor_weights[id(target_fallback)] = 0
            neighbor_by_obj_id[id(target_fallback)] = target_fallback
        best_key = max(neighbor_weights, key=lambda k: neighbor_weights[k])
        target = neighbor_by_obj_id[best_key]
        merged_ids = set(target.get("node_ids") or []) | small_nodes
        seed_node_id = _community_seed(merged_ids, nodes_by_id, adjacency)
        label = _community_label(seed_node_id, nodes_by_id)
        internal_edges = 0
        boundary_nodes: set[str] = set()
        for nid in merged_ids:
            for nbr in adjacency.get(nid, {}):
                if nbr in merged_ids:
                    if nid < nbr:
                        internal_edges += 1
                else:
                    boundary_nodes.add(nid)
        merged = {
            **target,
            "label": label,
            "seed_node_id": seed_node_id,
            "node_ids": sorted(merged_ids),
            "node_count": len(merged_ids),
            "edge_count": internal_edges,
            "boundary_node_count": len(boundary_nodes),
        }
        production = [merged if c is target else c for c in production if c is not small]
        changed = True
    production.sort(key=lambda c: (-c.get("node_count", 0), str(c.get("seed_node_id") or "")))
    return production + fixed


def _disambiguate_labels(communities: list[dict[str, Any]], nodes_by_id: dict[str, dict[str, Any]]) -> None:
    """Qualify duplicate community labels with the seed node's parent directory, then numeric suffix."""
    from collections import Counter
    labels = [str(c.get("label") or "") for c in communities]
    duplicates = {lbl for lbl, n in Counter(labels).items() if n > 1}
    if not duplicates:
        return
    for c in communities:
        lbl = str(c.get("label") or "")
        if lbl not in duplicates:
            continue
        seed_id = str(c.get("seed_node_id") or "")
        node = nodes_by_id.get(seed_id, {})
        source_file = str(node.get("source_file") or "")
        parent = Path(source_file).parent.name if source_file else ""
        if parent and parent not in {".", ""}:
            c["label"] = f"{parent}/{lbl}"
    # Second pass: numeric suffix for any remaining duplicates
    seen: dict[str, int] = {}
    remaining = {lbl for lbl, n in Counter(str(c.get("label") or "") for c in communities).items() if n > 1}
    if remaining:
        for c in communities:
            lbl = str(c.get("label") or "")
            if lbl in remaining:
                n = seen.get(lbl, 1)
                seen[lbl] = n + 1
                c["label"] = f"{lbl} {n}"


def update_graph_clusters(
    *,
    root: Path,
    index_dir: Path,
    layer: str,
    graph_payload: dict[str, Any] | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    if layer not in GRAPH_FILENAMES:
        raise ValueError(f"Unsupported graph layer: {layer}")
    graph = graph_payload
    if graph is None:
        graph = _read_json(index_dir / GRAPH_DIRNAME / GRAPH_FILENAMES[layer], {})
    if not isinstance(graph, dict) or not graph:
        stale_path = cluster_path(root, layer)
        try:
            stale_path.unlink()
        except OSError:
            pass
        return read_cluster_payload(root, layer)

    if verbose:
        print(f"build_index: graph clustering inputs ready for {layer} layer", flush=True)
    adjacency, nodes_by_id, _ = _project_undirected_projection(graph)
    fixed_communities, prod_nodes, prod_adjacency = _extract_fixed_communities(nodes_by_id, adjacency)
    prod_communities, algorithm = _run_clustering(prod_adjacency, prod_nodes)
    if verbose and algorithm == "label-propagation":
        print(
            f"build_index: Leiden backend unavailable for {layer} layer — "
            "falling back to label-propagation clustering",
            flush=True,
        )
    communities = prod_communities + fixed_communities
    previous = _read_existing_clusters(cluster_path(root, layer))
    remapped = _remap_clusters(layer=layer, new_clusters=communities, previous=previous)
    remapped = _merge_same_stem_communities(remapped, nodes_by_id, adjacency)
    remapped = _merge_small_communities(remapped, nodes_by_id, adjacency)
    _disambiguate_labels(remapped, nodes_by_id)
    for c in remapped:
        if c.pop("_fixed", None):
            c["kind"] = "fixed"
    payload = {
        "cluster_schema_version": CLUSTER_SCHEMA_VERSION,
        "cluster_builder_version": CLUSTER_BUILDER_VERSION,
        "cluster_algorithm": algorithm,
        "layer": layer,
        "graph_schema_version": str(graph.get("schema_version") or GRAPH_SCHEMA_VERSION),
        "graph_builder_version": str(graph.get("builder_version") or GRAPH_BUILDER_VERSION),
        "graph_path": str(graph_path(root, layer).relative_to(root)).replace("\\", "/"),
        "graph_mtime": int(graph.get("graph_mtime") or 0),
        "projection": "derived-undirected",
        "projection_rules": {
            "source_target": "min(source,target) -> max(source,target)",
            "reciprocal_edges": "weights accumulate on the same undirected pair",
            "external_nodes": "excluded",
        },
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "community_count": len(remapped),
        "communities": remapped,
    }
    _write_json(cluster_path(root, layer), payload)
    if verbose:
        print(
            f"build_index: graph clustering wrote {layer} cluster artifact — "
            f"{payload['community_count']} communities via {algorithm}",
            flush=True,
        )
    return read_cluster_payload(root, layer)

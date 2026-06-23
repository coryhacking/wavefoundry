"""Read-only graph query helpers over the persisted project graph artifact."""

from __future__ import annotations

import fnmatch
import heapq
import importlib.util
import itertools
import math
import sys
from collections import deque
from pathlib import Path
from typing import Any, Callable, Iterable, Literal

Layer = Literal["project"]
Direction = Literal["callers", "callees", "both"]
ReportSection = Literal["fan_in", "fan_out", "orphan_docs", "chokepoints", "file_hubs", "betweenness"]

_BETWEENNESS_NODE_LIMIT = 10_000

_DEFAULT_IMPACT_RELATIONS = ("imports", "calls")
_DEFAULT_CALL_RELATIONS = ("calls",)
# Wave 1p4ls: relations OPT-IN for default 1-hop traversal — excluded when a caller passes no
# explicit `relations` so a hot constant (read by hundreds of functions) does not balloon every
# default neighbor query (incl. 1p4hu's graph-signal expansion). A caller that WANTS constant
# reads passes them explicitly (e.g. relations=("reads",)). Deliberately NOT in the impact/call
# defaults above either, so constant reads never pollute blast-radius or call-graph analysis.
_NEIGHBOR_OPT_IN_RELATIONS = frozenset({"reads"})
_DOC_KINDS = frozenset({"doc", "seed"})
_CHOKEPOINT_FAN_OUT = 20


def _scope_matches(scope: str, source_file: str) -> bool:
    """True when ``source_file`` falls under ``scope`` (wave 1p41o).

    ``scope`` is a repo-relative file path, a directory prefix, or a glob
    (containing ``*``/``?``/``[]``). Path separators are normalized so callers
    can pass either style.
    """
    scope = (scope or "").strip().replace("\\", "/")
    sf = (source_file or "").replace("\\", "/")
    if not scope or not sf:
        return False
    if any(ch in scope for ch in "*?["):
        return fnmatch.fnmatch(sf, scope)
    return sf == scope or sf.startswith(scope.rstrip("/") + "/")


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


# Wave 131bt (131e2): per-process cache for stale-graph version checks.
# Maps (root, layer) → (payload_mtime, verified_builder_version) so the
# version check on the state file fires at most once per file change.
import threading as _threading
_VERSION_CHECK_LOCK = _threading.Lock()
_VERSION_CHECK_CACHE: dict[tuple[str, str], tuple[float, str]] = {}

# Wave 1p2q3 (1p2w5): in-process coordination of concurrent auto-rebuild
# attempts. When a `GRAPH_BUILDER_VERSION` bump invalidates the on-disk graph,
# every `load_graph` call detects the mismatch independently. Without
# coordination, concurrent MCP tool calls each fire their own synchronous
# `build_index`, all but one of which race for the index-build flock and lose
# — emitting `graph_auto_rebuild_failed` even though a rebuild is actively
# succeeding in a sibling call. This map records in-flight rebuilds keyed on
# `(root, layer)`; concurrent callers see the marker and defer with a
# `graph_auto_rebuild_in_progress` diagnostic. Each entry stores the wall-
# clock start time so a crashed rebuild does not pin the marker indefinitely
# (see _INFLIGHT_REBUILD_STALE_SECONDS).
_VERSION_REBUILD_INFLIGHT_LOCK = _threading.Lock()
_VERSION_REBUILD_INFLIGHT: dict[tuple[str, str], float] = {}
_INFLIGHT_REBUILD_STALE_SECONDS = 120.0

# Wave 1p2q3 (131hh): post-rebuild callback registry. server_impl wires this at
# MCP startup to dispatch `notifications/resources/updated` for wavefoundry://
# graph/* URIs whenever the auto-rebuild path completes. graph_query stays
# independent of FastMCP — the callback is opt-in and best-effort.
_POST_REBUILD_CALLBACK = None


def set_post_rebuild_callback(fn) -> None:
    """Register a callback invoked after a successful auto-rebuild.

    The callback receives keyword arguments ``root: Path`` and ``layer: str``.
    Exceptions raised by the callback are swallowed (notifications are
    best-effort and must not break query results).
    """
    global _POST_REBUILD_CALLBACK
    _POST_REBUILD_CALLBACK = fn


def _graph_payload_path(root: Path, layer: str = "project") -> Path:
    # Wave 1p4ww: single project graph — the framework graph layer was removed.
    return root / ".wavefoundry" / "index" / "graph" / "project-graph.json"


def _graph_state_path(root: Path, layer: str = "project") -> Path:
    return _graph_payload_path(root).with_name("project-graph-state.json")


def _graph_index_dir(root: Path, layer: str = "project") -> Path:
    return root / ".wavefoundry" / "index"


def _ensure_graph_builder_current(root: Path, layer: str) -> dict[str, Any] | None:
    """Check the on-disk graph's ``builder_version`` against runtime.

    Returns:
        - None when the graph is current (no diagnostic to surface), already
          checked this mtime, or no graph exists yet.
        - A structured diagnostic dict when an auto-rebuild fired (success or
          failure). The caller attaches it to the payload.

    Synchronously rebuilds the graph when the version mismatches. Once-per-
    upgrade cost; subsequent queries hit the in-process mtime cache and skip
    the state file read entirely.
    """
    if layer != "project":
        return None
    indexer = _get_graph_indexer()
    runtime_version = str(getattr(indexer, "GRAPH_BUILDER_VERSION", "") or "")
    if not runtime_version:
        return None
    payload_path = _graph_payload_path(root, layer)
    if not payload_path.exists():
        # No graph index yet — nothing to rebuild. The query layer surfaces
        # graph_not_ready_diagnostic separately.
        return None
    try:
        payload_mtime = payload_path.stat().st_mtime
    except OSError:
        return None
    cache_key = (str(root.resolve()), layer)
    with _VERSION_CHECK_LOCK:
        cached = _VERSION_CHECK_CACHE.get(cache_key)
        if cached is not None and cached[0] == payload_mtime and cached[1] == runtime_version:
            return None  # Already verified this exact graph state.
    state_path = _graph_state_path(root, layer)
    if not state_path.exists():
        # No state file — can't determine builder_version. Mark as verified
        # to avoid re-checking on every query.
        with _VERSION_CHECK_LOCK:
            _VERSION_CHECK_CACHE[cache_key] = (payload_mtime, runtime_version)
        return None
    import json
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        with _VERSION_CHECK_LOCK:
            _VERSION_CHECK_CACHE[cache_key] = (payload_mtime, runtime_version)
        return None
    state_version = str(state.get("builder_version") or "")
    if state_version == runtime_version:
        with _VERSION_CHECK_LOCK:
            _VERSION_CHECK_CACHE[cache_key] = (payload_mtime, runtime_version)
        return None
    # --- Mismatch: synchronously rebuild. ---
    import time
    import importlib.util
    indexer_script_path = Path(__file__).resolve().parent / "indexer.py"
    if not indexer_script_path.exists():
        return {
            "code": "graph_auto_rebuild_skipped",
            "message": f"Graph builder version mismatch ({state_version} → {runtime_version}) but indexer.py not found. Run wave_index_build(content='graph') manually.",
            "from_builder_version": state_version,
            "to_builder_version": runtime_version,
            "recovery_tools": ["wave_index_build"],
            "recovery_usage": "wave_index_build(content='graph', mode='rebuild')",
        }
    # Wave 1p2q3 (1p2w5): coordinate concurrent auto-rebuild attempts. If a
    # rebuild is already in-flight for this (root, layer), defer rather than
    # race for the index-build flock. The stale-inflight safety net allows a
    # fresh attempt after _INFLIGHT_REBUILD_STALE_SECONDS in case a prior
    # rebuild crashed without releasing the marker.
    import time as _time
    inflight_started: float | None = None
    with _VERSION_REBUILD_INFLIGHT_LOCK:
        inflight_started = _VERSION_REBUILD_INFLIGHT.get(cache_key)
        now_ts = _time.time()
        if inflight_started is not None:
            age = now_ts - inflight_started
            if age < _INFLIGHT_REBUILD_STALE_SECONDS:
                return {
                    "code": "graph_auto_rebuild_in_progress",
                    "message": (
                        f"Graph builder version mismatch ({state_version} → {runtime_version}); "
                        f"a rebuild for this layer is already in progress (started {age:.1f}s ago). "
                        "Skipping duplicate auto-rebuild attempt. Re-run the tool once the rebuild completes."
                    ),
                    "from_builder_version": state_version,
                    "to_builder_version": runtime_version,
                    "rebuild_started_at_age_seconds": round(age, 1),
                    "recovery_tools": ["wave_index_build_status"],
                    "recovery_usage": "wave_index_build_status()",
                }
            # Stale in-flight marker; fall through and claim it ourselves.
        _VERSION_REBUILD_INFLIGHT[cache_key] = now_ts
    start = time.monotonic()
    try:
        spec = importlib.util.spec_from_file_location("indexer_for_graph_query_rebuild", indexer_script_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load indexer from {indexer_script_path}")
        indexer_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(indexer_mod)
        index_dir = _graph_index_dir(root, layer)
        indexer_mod.build_index(
            root,
            full=True,
            content="graph",
            index_dir=index_dir,
            verbose=False,
        )
        duration_ms = int((time.monotonic() - start) * 1000)
    except Exception as exc:
        return {
            "code": "graph_auto_rebuild_failed",
            "message": f"Stale graph builder version mismatch ({state_version} → {runtime_version}) detected but automatic rebuild failed: {exc}. Run wave_index_build(content='graph') manually.",
            "from_builder_version": state_version,
            "to_builder_version": runtime_version,
            "recovery_tools": ["wave_index_build"],
            "recovery_usage": "wave_index_build(content='graph', mode='rebuild')",
        }
    finally:
        # Release the in-flight marker on every exit path (success, failure,
        # or unhandled exception). Idempotent: pop returns None if no entry.
        with _VERSION_REBUILD_INFLIGHT_LOCK:
            _VERSION_REBUILD_INFLIGHT.pop(cache_key, None)
    # Cache the post-rebuild state (mtime has changed) so subsequent queries
    # don't re-check.
    try:
        new_mtime = payload_path.stat().st_mtime
    except OSError:
        new_mtime = payload_mtime
    with _VERSION_CHECK_LOCK:
        _VERSION_CHECK_CACHE[cache_key] = (new_mtime, runtime_version)
    # Wave 1p2q3 (131hh): notify MCP clients that wavefoundry://graph/* resource
    # contents may have changed. Best-effort — callback registry stays empty
    # when graph_query is used outside the MCP server.
    if _POST_REBUILD_CALLBACK is not None:
        try:
            _POST_REBUILD_CALLBACK(root=root, layer=layer)
        except Exception:
            pass
    return {
        "code": "graph_auto_rebuilt",
        "message": f"Graph rebuilt automatically: builder_version {state_version} → {runtime_version} ({duration_ms} ms).",
        "from_builder_version": state_version,
        "to_builder_version": runtime_version,
        "rebuild_duration_ms": duration_ms,
    }


def load_graph(root: Path, *, layer: str = "project") -> dict[str, Any]:
    """Load one graph layer. Returns payload with nodes/edges; ``present=False`` when missing.

    Wave 131bt (131e2): when the on-disk graph's ``builder_version`` differs
    from the runtime ``GRAPH_BUILDER_VERSION``, a full rebuild fires
    synchronously before the payload is loaded. The resulting diagnostic is
    attached to the payload as ``auto_rebuild_diagnostic`` for the consumer
    tool to surface.
    """
    # Wave 1p4ww: single project graph — only the project layer exists.
    if layer != "project":
        raise ValueError(f"Unsupported graph layer: {layer}")
    rebuild_diag = _ensure_graph_builder_current(root, layer)
    payload = _get_graph_indexer().read_graph_payload(root, layer)
    if rebuild_diag is not None:
        payload["auto_rebuild_diagnostic"] = rebuild_diag
    return payload


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


# Wave 131bt (1319m): directory-aggregation language detection.
#
# Maps file extension → detection config. Three detection modes:
#   - "declaration_match": files in a directory must all share the same
#     ``package`` or ``namespace`` declaration (regex-matched in source).
#   - "init_file": directory must contain an ``__init__.py`` file.
#   - "convention": all files in the directory with this extension collapse
#     (no declaration verification).
#
# Kind preserves the language-native term ("package" vs "namespace") so
# operators reading the graph see familiar vocabulary.
import re as _re

_DIRECTORY_AGG_LANGUAGES: dict[str, dict[str, Any]] = {
    # Strict / language-enforced.
    ".go":     {"mode": "declaration_match", "pattern": _re.compile(r"^\s*package\s+([A-Za-z_]\w*)", _re.MULTILINE), "kind": "package"},
    ".py":     {"mode": "init_file", "kind": "package"},
    # Convention-based / build-system-enforced.
    ".java":   {"mode": "declaration_match", "pattern": _re.compile(r"^\s*package\s+([A-Za-z_][\w.]*)\s*;", _re.MULTILINE), "kind": "package"},
    ".kt":     {"mode": "declaration_match", "pattern": _re.compile(r"^\s*package\s+([A-Za-z_][\w.]*)", _re.MULTILINE), "kind": "package"},
    ".scala":  {"mode": "declaration_match", "pattern": _re.compile(r"^\s*package\s+([A-Za-z_][\w.]*)", _re.MULTILINE), "kind": "package"},
    ".cs":     {"mode": "declaration_match", "pattern": _re.compile(r"^\s*namespace\s+([A-Za-z_][\w.]*)", _re.MULTILINE), "kind": "namespace"},
    ".php":    {"mode": "declaration_match", "pattern": _re.compile(r"^\s*namespace\s+([A-Za-z_][\w\\]*)\s*;", _re.MULTILINE), "kind": "namespace"},
    # Swift uses build-target convention; no in-source declaration.
    ".swift":  {"mode": "convention", "kind": "package"},
}

# Excluded from directory aggregation: Rust (mod tree, not directory-bound),
# Ruby (module is namespace declaration, not directory-bound), JS/TS (no
# package concept beyond ES modules).
_DIRECTORY_AGG_EXCLUDED_EXTS: frozenset[str] = frozenset({
    ".rs", ".rb", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
})


def collapse_package_to_directory_view(
    payload: dict[str, Any], *, root: Path | None = None
) -> dict[str, Any]:
    """Aggregate files in a directory into a single package/namespace node (wave 131bt — 1319m).

    For supported languages, files in the same directory that share the same
    package/namespace declaration (Go/Java/Kotlin/C#/Scala/PHP), are within a
    Python package directory (``__init__.py`` present), or follow Swift's
    build-target convention (all ``.swift`` files in a directory), are merged
    into one package/namespace node. Edges from outside the package retarget
    to the package node; intra-package edges between merged files collapse.

    Per-symbol navigation tools deliberately do NOT consume this view —
    they need the unmodified per-file graph.

    Languages outside the eight-language scope (Rust ``mod`` tree, Ruby
    namespace declarations, JS/TS ES modules) are unchanged by this view.
    """
    nodes_in = list(payload.get("nodes") or [])
    edges_in = list(payload.get("edges") or [])

    # Phase 1: group file nodes by directory + detect language groupings.
    # file_node_id → (dir_path, ext, declared_unit)
    file_groups: dict[str, tuple[str, str, str]] = {}
    nodes_by_id: dict[str, dict[str, Any]] = {}
    for node in nodes_in:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("id") or "")
        if not nid:
            continue
        nodes_by_id[nid] = node
        # Only file/module nodes are candidates.
        if node.get("kind") != "module":
            continue
        if "::" in nid:
            continue  # symbol id, not a file path
        # Extract directory and extension from the node id (which is the path).
        slash_idx = nid.rfind("/")
        if slash_idx < 0:
            continue
        ext_idx = nid.rfind(".")
        if ext_idx <= slash_idx:
            continue
        ext = nid[ext_idx:]
        if ext in _DIRECTORY_AGG_EXCLUDED_EXTS:
            continue
        if ext not in _DIRECTORY_AGG_LANGUAGES:
            continue
        dir_path = nid[:slash_idx]
        if not dir_path:
            continue
        file_groups[nid] = (dir_path, ext, "")  # declared_unit filled in phase 2

    if not file_groups:
        return dict(payload)

    # Phase 2: per (dir, ext) group, determine the grouping unit.
    # Group by (dir, ext); read source files for declaration_match languages.
    by_dir_ext: dict[tuple[str, str], list[str]] = {}
    for nid, (dir_path, ext, _) in file_groups.items():
        by_dir_ext.setdefault((dir_path, ext), []).append(nid)

    # Per-(dir, ext) → resolved grouping unit (or empty when collapse should
    # skip — e.g., mixed-package directory, single-file, etc.)
    resolved_unit: dict[tuple[str, str], str] = {}
    for (dir_path, ext), file_ids in by_dir_ext.items():
        # Single-file directories are not collapsed (per AC-13 design).
        if len(file_ids) < 2:
            continue
        cfg = _DIRECTORY_AGG_LANGUAGES[ext]
        mode = cfg["mode"]
        if mode == "convention":
            # Swift: all files in this directory are one package; unit name is
            # the directory's basename.
            unit = dir_path.rsplit("/", 1)[-1] or dir_path
            resolved_unit[(dir_path, ext)] = unit
        elif mode == "init_file":
            # Python: require an __init__.py in the directory.
            init_id = f"{dir_path}/__init__.py"
            if init_id in nodes_by_id:
                unit = dir_path.rsplit("/", 1)[-1] or dir_path
                resolved_unit[(dir_path, ext)] = unit
        elif mode == "declaration_match":
            # Read each file's source (via filesystem) to extract the
            # declaration; require all files to agree.
            if root is None:
                continue  # No root to read sources; skip this group.
            pattern = cfg["pattern"]
            units: set[str] = set()
            agreement = True
            for fid in file_ids:
                fpath = root / fid
                if not fpath.is_file():
                    agreement = False
                    break
                try:
                    text = fpath.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    agreement = False
                    break
                m = pattern.search(text)
                if not m:
                    agreement = False
                    break
                units.add(m.group(1))
            if agreement and len(units) == 1:
                resolved_unit[(dir_path, ext)] = next(iter(units))

    if not resolved_unit:
        return dict(payload)

    # Phase 3: build collapse mapping (file_id → package_id) and new package nodes.
    collapse_map: dict[str, str] = {}
    package_nodes: list[dict[str, Any]] = []
    package_files_per_pkg: dict[str, list[str]] = {}
    package_unit_per_pkg: dict[str, str] = {}
    package_kind_per_pkg: dict[str, str] = {}

    for (dir_path, ext), unit in resolved_unit.items():
        cfg = _DIRECTORY_AGG_LANGUAGES[ext]
        # Package node id: <directory>/<__package__>:<unit>
        # Use a stable scheme that operators can recognize.
        pkg_id = f"{dir_path}/__package__::{unit}"
        package_unit_per_pkg[pkg_id] = unit
        package_kind_per_pkg[pkg_id] = cfg["kind"]
        # Find file ids belonging to this group.
        for fid in by_dir_ext.get((dir_path, ext), []):
            collapse_map[fid] = pkg_id
            package_files_per_pkg.setdefault(pkg_id, []).append(fid)

    for pkg_id, file_ids in package_files_per_pkg.items():
        package_nodes.append({
            "id": pkg_id,
            "label": package_unit_per_pkg[pkg_id],
            "kind": package_kind_per_pkg[pkg_id],
            "source_file": pkg_id,
            "source_location": "1:0",
            "collapse_origin_files": sorted(file_ids),
            "collapse_unit": package_unit_per_pkg[pkg_id],
            "collapse_lang": pkg_id.rsplit(".", 0)[0],  # placeholder, refined below
        })

    # Phase 4: build output nodes (drop collapsed file nodes; keep their child
    # symbols; add package nodes).
    out_nodes: list[dict[str, Any]] = []
    for node in nodes_in:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("id") or "")
        if nid in collapse_map:
            # File node absorbed into package — drop.
            continue
        out_nodes.append(node)
    out_nodes.extend(package_nodes)

    # Phase 5: rewrite edges. Cross-package edges retarget to the package node;
    # intra-package edges between absorbed files collapse (deduped).
    seen_edge_keys: set[tuple[str, str, str, str]] = set()
    out_edges: list[dict[str, Any]] = []
    for edge in edges_in:
        if not isinstance(edge, dict):
            continue
        src = str(edge.get("source") or "")
        tgt = str(edge.get("target") or "")
        if not src or not tgt:
            continue
        new_src = collapse_map.get(src, src)
        new_tgt = collapse_map.get(tgt, tgt)
        # Drop intra-package self-loops (file_a → file_b both collapse to pkg).
        if new_src == new_tgt and new_src.endswith("__package__::" + new_src.rsplit("::", 1)[-1]):
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


# Wave 1p2q3 (1p2q4): weighted-cost path search constants.
#
# `shortest_path` is now a Dijkstra-equivalent lowest-cost search rather than a
# shortest-hop BFS. Edge cost encodes semantic weight: deterministic-attribution
# call edges cost 1, heuristic call edges cost 2, structural (imports/defines)
# edges cost 100.
#
# Invariant: ``structural_cost > max_hops × calls/EXTRACTED_cost`` to preserve
# calls preference within the search horizon. With ``max_hops=10`` (default) and
# ``calls/EXTRACTED_cost=2``, the structural-cost floor is 20; 100 leaves
# comfortable margin (any call chain up to ~50 EXTRACTED hops beats a single
# structural hop). If ``max_hops`` ever defaults above ~50, revisit
# ``_PATH_COST_STRUCTURAL``.
_CONFIDENCE_RANK = {
    "RECEIVER_RESOLVED": 0,
    "CONSTRUCTION_RESOLVED": 0,
    "EXTRACTED": 1,
}
_PATH_COST_CALLS_HIGH = 1
_PATH_COST_CALLS_EXTRACTED = 2
_PATH_COST_STRUCTURAL = 100


def _path_edge_cost(edge: dict[str, Any]) -> int:
    """Return the path-search cost of an edge based on relation + confidence."""
    relation = str(edge.get("relation") or "")
    confidence = str(edge.get("confidence") or "")
    if relation == "calls":
        if confidence in ("RECEIVER_RESOLVED", "CONSTRUCTION_RESOLVED"):
            return _PATH_COST_CALLS_HIGH
        return _PATH_COST_CALLS_EXTRACTED
    return _PATH_COST_STRUCTURAL


# Wave 1p5l4 (field feedback): blast-radius / risk weighting by edge
# confidence. EXTRACTED edges are heuristic name-based fallback that cannot
# disambiguate receiver type, so a ubiquitous accessor name (getKey/getValue/
# toString) collects spurious in-edges from unrelated symbols (e.g.
# Map.Entry.getKey()) and over-counts blast radius. Down-weight EXTRACTED so
# confidence-resolved structure dominates the rank — but do NOT zero it
# (wave 1p41l showed EXTRACTED is sometimes the only cross-file signal). The
# factor is a single tunable constant; deterministic-attribution edges keep
# full weight.
_EXTRACTED_EDGE_WEIGHT = 0.25


def _edge_confidence_weight(edge: dict[str, Any]) -> float:
    """Return the blast-radius weight of an edge by its attribution confidence.

    RECEIVER_RESOLVED / CONSTRUCTION_RESOLVED (type-resolved at the graph
    builder) count in full; EXTRACTED (and any unknown confidence) is
    down-weighted to ``_EXTRACTED_EDGE_WEIGHT``.
    """
    confidence = str(edge.get("confidence") or "")
    if confidence in ("RECEIVER_RESOLVED", "CONSTRUCTION_RESOLVED"):
        return 1.0
    return _EXTRACTED_EDGE_WEIGHT


# Wave 1p7df (transitive confidence propagation): blast-radius weight is the
# confidence of the *path* back to the changed symbol, not just the immediate
# entering edge. `graph_impact` previously set a node's weight to the max
# entering-edge weight (immediate hop only), so a node reached via
# `resolved <- EXTRACTED` reset to full weight and the EXTRACTED discount leaked
# away two hops out — over-counting multi-hop blast radius on EXTRACTED-heavy
# graphs (the Java consumer's residual after 1p5l4/p5l8). We combine edge
# weights along the best path instead.
#
# "min" (weakest-link) is the default: a 1-edge path's min(1.0, w) == w, so it
# *exactly preserves* the prior single-hop weight while extending transitively;
# any EXTRACTED hop caps the path at `_EXTRACTED_EDGE_WEIGHT`. "product"
# (compounding) further distinguishes one EXTRACTED hop from several. The choice
# is value-gated on the real consumer graphs (change 1p7df AC-5).
_PATH_CONFIDENCE_COMBINE = "min"


def _combine_path_confidence(base: float, edge_weight: float) -> float:
    """Combine a path's running confidence with the next edge's weight."""
    if _PATH_CONFIDENCE_COMBINE == "product":
        return base * edge_weight
    return min(base, edge_weight)


class GraphQueryIndex:
    """In-memory adjacency index over a loaded graph payload."""

    __slots__ = (
        "layer", "present", "builder_version", "nodes", "edges",
        "_out", "_in", "_node_by_id",
        # Wave 131bt (131e2): when load_graph fired a synchronous rebuild
        # for a stale GRAPH_BUILDER_VERSION, the diagnostic propagates here
        # so consumer tools can echo it into their MCP response.
        "auto_rebuild_diagnostic",
    )

    def __init__(self, payload: dict[str, Any]):
        self.layer = str(payload.get("layer") or "project")
        self.present = bool(payload.get("present"))
        # Wave 13129 (1312l delivery review): expose builder_version so
        # query-time consumers can short-circuit redundant work on graphs
        # the indexer already cleaned up (e.g., the code_callhierarchy
        # receiver-type filter is no-op on v13+ graphs).
        self.builder_version = str(payload.get("builder_version") or "")
        # Wave 131bt (131e2): payload-level diagnostic from the auto-rebuild
        # path; None when the graph was already current.
        raw_diag = payload.get("auto_rebuild_diagnostic")
        self.auto_rebuild_diagnostic = raw_diag if isinstance(raw_diag, dict) else None
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
        # Wave 1p4ww: single project graph — framework/union layers removed.
        return cls(load_graph(root, layer="project"))

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        return self._node_by_id.get(node_id)

    def resolve_symbol(self, symbol: str) -> str | None:
        """Resolve a symbol string to a graph node id."""
        symbol = symbol.strip()
        if not symbol:
            return None
        if symbol in self._node_by_id:
            return symbol
        # Merged class/module alias: when the query is `<file_id>::<class_name>` and
        # the file id resolves to a collapsed_pair merged node whose label matches
        # the suffix, treat the query as an alias for the file id. The class/module
        # merge (1316l/13190) consumes the class node into the file id, so callers
        # querying the natural qualified form would otherwise see graph_symbol_not_found.
        if "::" in symbol:
            file_part, _, class_name = symbol.rpartition("::")
            file_node = self._node_by_id.get(file_part)
            if (
                file_node is not None
                and file_node.get("collapsed_pair")
                and file_node.get("label") == class_name
            ):
                return file_part
        # Suffix match on qualified names
        matches = [nid for nid in self._node_by_id if nid.endswith(f"::{symbol}") or nid == symbol]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            # Wave 1p4ls: kind-aware — prefer callables so a constant node sharing a simple name
            # does NOT shadow a previously-resolving function/method lookup. Then shortest id.
            pool = self._prefer_callable_ids(matches)
            return sorted(pool, key=len)[0]
        # Bare symbol name
        by_label = [
            nid for nid, node in self._node_by_id.items()
            if node.get("label") == symbol or nid.split("::")[-1] == symbol
        ]
        if len(by_label) == 1:
            return by_label[0]
        if len(by_label) > 1:
            # Wave 1p4ls: kind-aware tiebreak — if exactly ONE callable matches (the rest being
            # constants/other), bind it; multiple callables stay ambiguous (conservative → None).
            callables = self._prefer_callable_ids(by_label, only_callables=True)
            if len(callables) == 1:
                return callables[0]
        return None

    def _prefer_callable_ids(self, ids: list[str], *, only_callables: bool = False) -> list[str]:
        """Wave 1p4ls: of a multi-match set, the callable (function/method) node ids — or, when no
        callable is present and ``only_callables`` is False, the original set unchanged."""
        callables = [
            nid for nid in ids
            if (self._node_by_id.get(nid) or {}).get("kind") in ("function", "method")
        ]
        if only_callables:
            return callables
        return callables if callables else ids

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
        max_neighbors: int | None = None,
        direction: str = "both",
    ) -> dict[str, Any]:
        """1-hop neighbors of each seed. ``direction`` selects edge orientation relative to the
        seed: ``"both"`` (default — out + in, back-compatible), ``"in"``/``"callers"`` (edges
        pointing AT the seed — its callers / readers / importers, i.e. "what uses X"), or
        ``"out"``/``"callees"`` (edges FROM the seed — what it calls / reads / imports). Wave 1p4hu
        delivery follow-up: the structural signal passes ``direction="in"`` for "what calls/reads/
        uses X" phrasing so it stops answering a callers question with the seed's callees."""
        rel_set = set(relations) if relations is not None else None
        _want_out = direction in ("both", "out", "callees")
        _want_in = direction in ("both", "in", "callers")
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()
        truncated = False
        for start in node_ids:
            if start not in self._node_by_id:
                continue
            nodes[start] = self._node_by_id[start]
            _seed_edges = (self._out.get(start, []) if _want_out else []) + (self._in.get(start, []) if _want_in else [])
            for edge in _seed_edges:
                rel = edge.get("relation")
                if rel_set is None:
                    # Wave 1p4ls: default traversal excludes opt-in relations (e.g. "reads") so a
                    # hot constant does not balloon the neighbor set; explicit relations override.
                    if rel in _NEIGHBOR_OPT_IN_RELATIONS:
                        continue
                elif rel not in rel_set:
                    continue
                src = edge.get("source")
                tgt = edge.get("target")
                if not isinstance(src, str) or not isinstance(tgt, str):
                    continue
                key = (src, tgt, str(rel))
                if key in seen_edges:
                    continue
                # Wave 1p4ls: optional neighbor-size bound — a degree cap for hot nodes.
                if max_neighbors is not None and len(nodes) >= max_neighbors:
                    truncated = True
                    continue
                seen_edges.add(key)
                edges.append(edge)
                for nid in (src, tgt):
                    if nid in self._node_by_id:
                        nodes[nid] = self._node_by_id[nid]
        result = {
            "present": True,
            "layer": self.layer,
            "nodes": list(nodes.values()),
            "edges": edges,
            "note": "1-hop structural neighbors; on by default, suppress with graph=false",
        }
        if truncated:
            result["truncated"] = True
        return result

    def shortest_path(
        self,
        from_symbol: str,
        to_symbol: str,
        *,
        relations: Iterable[str] | None = None,
        max_hops: int = 10,
        direction: str = "forward",
        min_confidence: str = "EXTRACTED",
    ) -> dict[str, Any]:
        """Lowest-cost path between two symbols.

        Returns ``{found, path_nodes, path_edges, hop_count}`` always — empty lists
        and ``hop_count: 0`` when no path is found.

        Wave 1p2q3 (1p2q4): replaced shortest-hop BFS with weighted-cost Dijkstra-
        equivalent search. Per-edge cost reflects semantic weight: deterministic-
        attribution call edges cost 1, heuristic call edges cost 2, structural
        (imports/defines) edges cost 100. The cost function ensures real call
        chains beat shorter structural shortcuts (e.g. two functions sharing an
        ``external::any`` import). The invariant ``structural_cost > max_hops ×
        calls/EXTRACTED_cost`` must hold so calls preference holds across the
        search horizon.

        Also enforces ``external::*`` nodes as non-transitive: they are valid
        path endpoints (``from_id``/``to_id``) but not intermediate bridges.

        ``direction`` controls which edges the search may walk:
        - ``"forward"`` (default): outgoing edges only — answers "does from reach to?"
        - ``"backward"``: incoming edges only — answers "is from reached by to?"
        - ``"either"``: outgoing or incoming; each ``path_edges`` entry carries an
          extra ``traversal_direction`` field (``"forward"`` or ``"backward"``).

        ``min_confidence`` filters candidate edges below the named confidence
        rank. Accepts ``"EXTRACTED"`` (default — no filter), ``"RECEIVER_RESOLVED"``,
        or ``"CONSTRUCTION_RESOLVED"`` (peer to RECEIVER_RESOLVED). Orthogonal to
        the weighted-cost selection.
        """
        direction_value = (direction or "forward").strip().lower()
        if direction_value not in ("forward", "backward", "either"):
            raise ValueError(
                f"direction must be 'forward', 'backward', or 'either'; got {direction!r}"
            )
        min_conf_value = (min_confidence or "EXTRACTED").strip().upper()
        if min_conf_value not in _CONFIDENCE_RANK and min_conf_value != "EXTRACTED":
            raise ValueError(
                f"min_confidence must be one of EXTRACTED, RECEIVER_RESOLVED, CONSTRUCTION_RESOLVED; got {min_confidence!r}"
            )
        min_conf_rank = _CONFIDENCE_RANK.get(min_conf_value, 1)

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

        # Priority queue: (cumulative_cost, sequence_number, current_id, path_node_ids, path_edges)
        # Sequence number breaks ties deterministically so heapq doesn't compare lists.
        counter = itertools.count()
        heap: list[tuple[int, int, str, list[str], list[dict[str, Any]]]] = [
            (0, next(counter), from_id, [from_id], [])
        ]
        # Best-known cost to each node; pop-and-skip when a stale entry resurfaces.
        best_cost: dict[str, int] = {from_id: 0}

        while heap:
            current_cost, _seq, current, path_ids, path_edges = heapq.heappop(heap)
            if current_cost > best_cost.get(current, current_cost):
                continue
            if current == to_id:
                path_nodes = []
                for nid in path_ids:
                    n = self._node_by_id.get(nid, {})
                    path_nodes.append({"node_id": nid, "label": n.get("label", nid), "kind": n.get("kind"), "source_file": n.get("source_file")})
                return {"found": True, "path_nodes": path_nodes, "path_edges": path_edges, "hop_count": len(path_edges)}
            if len(path_edges) >= max_hops:
                continue
            # Wave 1p2q3 (1p2q4): external::* nodes are non-transitive — valid as
            # endpoint but never as intermediate bridge. Routing through an
            # unresolved identifier connects unrelated symbols (e.g. shared
            # exception variable `external::e`).
            if (
                current.startswith("external::")
                and current != from_id
                and current != to_id
            ):
                continue
            # Candidate edges to walk from current node
            candidates: list[tuple[dict[str, Any], str, str]] = []
            if direction_value in ("forward", "either"):
                for edge in self._out.get(current, []):
                    rel = edge.get("relation")
                    if rel_set is not None and rel not in rel_set:
                        continue
                    conf = str(edge.get("confidence") or "")
                    if _CONFIDENCE_RANK.get(conf, 2) > min_conf_rank:
                        continue
                    neighbor = edge.get("target")
                    if isinstance(neighbor, str):
                        candidates.append((edge, neighbor, "forward"))
            if direction_value in ("backward", "either"):
                for edge in self._in.get(current, []):
                    rel = edge.get("relation")
                    if rel_set is not None and rel not in rel_set:
                        continue
                    conf = str(edge.get("confidence") or "")
                    if _CONFIDENCE_RANK.get(conf, 2) > min_conf_rank:
                        continue
                    neighbor = edge.get("source")
                    if isinstance(neighbor, str):
                        candidates.append((edge, neighbor, "backward"))
            for edge, neighbor, trav_dir in candidates:
                edge_cost = _path_edge_cost(edge)
                new_cost = current_cost + edge_cost
                if new_cost >= best_cost.get(neighbor, new_cost + 1):
                    continue
                best_cost[neighbor] = new_cost
                new_edge = dict(edge)
                if annotate_direction:
                    new_edge["traversal_direction"] = trav_dir
                new_ids = path_ids + [neighbor]
                new_edges = path_edges + [new_edge]
                heapq.heappush(heap, (new_cost, next(counter), neighbor, new_ids, new_edges))

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
        # Per-node hop distance (wave 130rj — field feedback §2.4):
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
        # Wave 1p7df: per-affected-node blast-radius weight = the confidence of
        # the BEST path back to the changed symbol, propagated transitively.
        # The seed has weight 1.0; each node's weight is the max over its paths
        # of the combined edge weights along that path (see
        # `_combine_path_confidence`). Because the reverse-BFS records min-hop
        # depth, an edge (source -> target) always has the target closer to the
        # seed; processing edges in ascending target-depth order finalizes a
        # target's weight before its source is relaxed. This replaces the prior
        # max-entering-edge weight (immediate hop only), which let the EXTRACTED
        # discount leak away beyond the first hop. Also tally the traversal's
        # confidence mix so consumers can discount a mostly-EXTRACTED blast
        # radius without a second call.
        path_weight: dict[str, float] = {node_id: 1.0}
        confidence_counts = {"receiver_resolved": 0, "construction_resolved": 0, "extracted": 0}
        for edge in sorted(
            traversed,
            key=lambda e: node_depth.get(str(e.get("target", "")), 0),
        ):
            src = edge.get("source")
            tgt = str(edge.get("target", ""))
            # Relax only forward (toward the seed): the source must be strictly
            # deeper than the target, which skips cycle back-edges.
            if (
                isinstance(src, str)
                and node_depth.get(src, 0) > node_depth.get(tgt, -1)
                and tgt in path_weight
            ):
                cand = _combine_path_confidence(
                    path_weight[tgt], _edge_confidence_weight(edge)
                )
                if cand > path_weight.get(src, 0.0):
                    path_weight[src] = cand
            conf = str(edge.get("confidence") or "")
            if conf == "RECEIVER_RESOLVED":
                confidence_counts["receiver_resolved"] += 1
            elif conf == "CONSTRUCTION_RESOLVED":
                confidence_counts["construction_resolved"] += 1
            else:
                confidence_counts["extracted"] += 1
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
                "confidence_weight": path_weight.get(nid, _EXTRACTED_EDGE_WEIGHT),
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
            "confidence_counts": confidence_counts,
            "has_cycles": has_cycles,
            "max_hops": max_hops,
            "relations": list(rels),
        }

    def risk_score(
        self,
        scope: str,
        *,
        max_hops: int = 3,
        top: int = 20,
        candidate_cap: int = 200,
        is_test_path: Callable[[str], bool] | None = None,
    ) -> dict[str, Any]:
        """Rank symbols defined in ``scope`` by how risky they are to *change*.

        Composite v2 (wave 1p5l4): ``risk = weighted_affected_file_count *
        log1p(weighted_fan_in)`` — blast radius (distinct files reachable
        upstream, i.e. who breaks if this symbol changes) times log-dampened
        call-degree (to avoid hub domination), both **weighted by edge
        attribution confidence**. ``EXTRACTED`` (heuristic name-based) edges
        count at ``_EXTRACTED_EDGE_WEIGHT`` while ``RECEIVER_RESOLVED`` /
        ``CONSTRUCTION_RESOLVED`` count in full, so a ubiquitous accessor name
        (``getKey``/``getValue``) can't top the rank purely on a name collision
        with an unrelated symbol (v1, wave 1p41o, weighted every edge equally).
        Each result also carries the raw ``affected_file_count``/``fan_in`` and
        an ``extracted_edge_fraction`` so a high-but-mostly-EXTRACTED score is
        visibly discountable. ``fan_out`` (what the symbol itself calls — near-
        orthogonal to change-risk) is surfaced as an *independent* component,
        NOT multiplied into ``risk``. The response carries ``score_formula`` and
        ``score_components`` so the score is transparent, re-weightable, and
        extensible. ``risk`` is a *relative rank within the queried scope*, not a
        cross-module-comparable absolute magnitude.

        ``scope`` is a repo-relative file path, directory prefix, or glob
        (``*``/``?``/``[]``). Candidate symbols are the ``function``/``method``
        definitions whose ``source_file`` matches. The candidate set is bounded
        by ``candidate_cap`` (default 200) — ``graph_impact`` runs a reverse-BFS
        per candidate — and over the cap the call returns ``over_candidate_cap``
        rather than scoring a misleading subset. ``is_test_path``, when given,
        filters test-file nodes out of the blast radius (mirrors ``code_impact``).
        """
        fan_in_counts: dict[str, int] = {}
        fan_out_counts: dict[str, int] = {}
        # Wave 1p5l4: confidence-weighted fan_in — EXTRACTED in-edges count
        # fractionally so a name-collision accessor (whose in-edges are mostly
        # heuristic) doesn't earn a hub's call-degree.
        weighted_fan_in_counts: dict[str, float] = {}
        for edge in self.edges:
            if edge.get("relation") != "calls":
                continue
            tgt = edge.get("target")
            src = edge.get("source")
            if isinstance(tgt, str):
                fan_in_counts[tgt] = fan_in_counts.get(tgt, 0) + 1
                weighted_fan_in_counts[tgt] = (
                    weighted_fan_in_counts.get(tgt, 0.0) + _edge_confidence_weight(edge)
                )
            if isinstance(src, str):
                fan_out_counts[src] = fan_out_counts.get(src, 0) + 1

        candidates = [
            node for node in self.nodes
            if node.get("kind") in ("function", "method")
            and node.get("source_file")
            and _scope_matches(scope, str(node.get("source_file") or ""))
        ]
        candidate_count = len(candidates)
        base = {
            "scope": scope,
            # Wave 1p5l4: rank on confidence-weighted blast radius × call-degree
            # so EXTRACTED name-collision edges can't promote a trivial accessor.
            "score_formula": "risk = weighted_affected_file_count * log1p(weighted_fan_in)",
            "score_components": [
                "weighted_affected_file_count", "weighted_fan_in", "fan_out",
                "affected_file_count", "fan_in", "extracted_edge_fraction",
                "transitive_extracted_fraction",
            ],
            "extracted_edge_weight": _EXTRACTED_EDGE_WEIGHT,
            "candidate_count": candidate_count,
            "candidate_cap": candidate_cap,
            "top": top,
            "max_hops": max_hops,
        }
        if candidate_count > candidate_cap:
            # Over the cap: do NOT score an arbitrary subset (that would hide the
            # riskiest symbols). Signal the caller to narrow scope instead.
            return {**base, "over_candidate_cap": True, "results": []}

        results: list[dict[str, Any]] = []
        for node in candidates:
            nid = str(node.get("id"))
            impact = self.graph_impact(nid, max_hops=max_hops)
            affected = impact.get("affected") or []
            if is_test_path is not None:
                affected = [
                    a for a in affected
                    if not is_test_path(str(a.get("source_file") or ""))
                ]
            # Wave 1p5l4: weighted blast radius — each affected file contributes
            # the MAX confidence weight among its affected nodes (a file reached
            # by even one type-resolved edge counts in full; one reached only via
            # EXTRACTED name-collision edges is down-weighted). Raw count kept for
            # transparency.
            file_weights: dict[str, float] = {}
            for a in affected:
                sf = str(a.get("source_file") or "")
                if not sf:
                    continue
                w = float(a.get("confidence_weight", _EXTRACTED_EDGE_WEIGHT))
                if w > file_weights.get(sf, 0.0):
                    file_weights[sf] = w
            affected_file_count = len(file_weights)
            weighted_affected_file_count = sum(file_weights.values())
            fan_in = fan_in_counts.get(nid, 0)
            weighted_fan_in = weighted_fan_in_counts.get(nid, 0.0)
            fan_out = fan_out_counts.get(nid, 0)
            conf = impact.get("confidence_counts") or {}
            total_edges = (
                int(conf.get("receiver_resolved", 0))
                + int(conf.get("construction_resolved", 0))
                + int(conf.get("extracted", 0))
            )
            extracted_edge_fraction = (
                int(conf.get("extracted", 0)) / total_edges if total_edges else 0.0
            )
            # Wave 1p7df: of the affected nodes, the fraction whose best path back
            # to this symbol traversed >=1 EXTRACTED edge (propagated
            # confidence_weight < 1.0) — exposes how much of the blast radius is
            # reachable only via low-confidence transitive paths, distinct from
            # extracted_edge_fraction (the raw edge-mix).
            transitive_extracted_fraction = (
                sum(
                    1 for a in affected
                    if float(a.get("confidence_weight", _EXTRACTED_EDGE_WEIGHT)) < 1.0
                ) / len(affected)
                if affected else 0.0
            )
            worst_hop = max((int(a.get("hop", 0)) for a in affected), default=0)
            risk = weighted_affected_file_count * math.log1p(weighted_fan_in)
            results.append({
                "node_id": nid,
                "label": node.get("label", nid),
                "source_file": node.get("source_file"),
                "kind": node.get("kind"),
                "risk": risk,
                "weighted_affected_file_count": round(weighted_affected_file_count, 3),
                "weighted_fan_in": round(weighted_fan_in, 3),
                "affected_file_count": affected_file_count,
                "fan_in": fan_in,
                "fan_out": fan_out,
                "extracted_edge_fraction": round(extracted_edge_fraction, 3),
                "transitive_extracted_fraction": round(transitive_extracted_fraction, 3),
                "hop": worst_hop,
            })
        results.sort(key=lambda r: (-r["risk"], -r["weighted_fan_in"], r["node_id"]))
        return {**base, "over_candidate_cap": False, "results": results[:top]}

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
            "fan_in", "fan_out", "orphan_docs", "chokepoints", "file_hubs",
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
        # Wave 1p4ww: the ``cross_layer`` section required the union layer
        # (project×framework boundary edges), which no longer exists.
        return result


def graph_not_ready_diagnostic(layer: str) -> dict[str, Any]:
    return {
        "code": "graph_not_ready",
        "message": f"Graph layer '{layer}' is not built yet. Run setup_index with graph indexing enabled.",
    }

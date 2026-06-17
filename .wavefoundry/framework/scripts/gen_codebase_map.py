#!/usr/bin/env python3
"""Generate a graceful-scaling codebase map of the destination project.

Wave 1p5tl (1p5x8 large-codebase-map). This is a **read-only consumer** of the
artifacts the framework already builds offline:

* the persisted graph artifact (``.wavefoundry/index/graph/project-graph.json``)
* the persisted cluster artifact
  (``.wavefoundry/index/graph/project-graph-clusters.json``) produced by
  ``graph_cluster.update_graph_clusters`` — flat Leiden/label-prop communities
  with ``community_id`` / ``label`` / ``seed_node_id`` / ``node_ids`` /
  ``node_count`` / ``boundary_node_count``.

It never re-parses source, never needs a live server, and never bumps
``GRAPH_BUILDER_VERSION`` (it records ``CLUSTER_BUILDER_VERSION`` for staleness).

The map is the **index to the index**: it orients the agent and routes to the
``code_*`` tools for depth. The top tier is **bounded regardless of repo size** —
it is derived by collapsing the (potentially hundreds of) flat communities to
their representative **package/directory**, NOT by listing the raw community
list. A small repo yields a compact, near-flat map; a monorepo yields a bounded,
paged top tier with leveled per-area drill-down + a ``code_*`` drill-in handoff.

Two concerns are deliberately separated so ``1p5xc`` (per-area ``AGENTS.md``
scaffolding) can reuse the structured model:

* ``compute_areas(root, layer)`` -> :class:`CodebaseMapModel` — the structured,
  deterministic area model (id / name / representative path / key files /
  drill-in handle). **This is the function 1p5xc imports.**
* ``render_markdown(model)`` -> str — renders the docs-lint-clean markdown.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

# --------------------------------------------------------------------------- #
# Tunables (the load-bearing scaling knobs).
# --------------------------------------------------------------------------- #
MAP_SCHEMA_VERSION = "1"
# The bounded top tier. A monorepo with hundreds of communities still yields a
# top-level map an agent can read in one screen; overflow is summarized + routed
# to `code_graph_report` rather than dumped.
MAX_TOP_AREAS = 24
# A repo at or below this many areas is "small" — rendered near-flat (no paging
# note, no "more areas" overflow line).
NEAR_FLAT_AREA_THRESHOLD = 8
# Wave 1p61w (javaagent field test): a community whose node set is more than this
# fraction generated code (per-node `generated` tag — set from `.gitattributes
# linguist-generated`, header signatures, generated dir/suffix names) is NOT an
# orientation target and is excluded from the primary area tier. 0.4 matches the
# `generated_node_fraction` threshold `wave_graph_report(exclude_generated=…)` uses.
GENERATED_AREA_FRACTION = 0.4
# Wave 1p64t (javaagent 1b): a community more than this fraction VENDORED (matched by
# an explicit `docs/repo-profile.json` `vendored_paths` glob or a `.gitattributes`
# `linguist-vendored` marker — never a name heuristic) is third-party, not product,
# and is excluded from the primary area tier (mirrors the generated axis).
VENDORED_AREA_FRACTION = 0.4
# Wave 1p64u (javaagent 2): a directory whose files are absorbed into a larger
# community (so it never becomes that community's dominant dir) is surfaced as its
# own area only when it clears this distinct-source-file floor — so the map gains
# buried product modules without fragmenting into one area per stray file.
MODULE_FLOOR_MIN_FILES = 3
# Wave 1p65l #5: non-descriptive structural / version directory leaves. When an area
# name derives to one of these (or a `vN` version segment), it carries no orientation
# value, so we walk up to the nearest distinctive ancestor and qualify it
# (`…/github/cards/v1` → `github-cards (v1)`). Ecosystem-neutral + extensible — a
# single constant, not JS-specific; covers common structural segments across stacks.
_STRUCTURAL_LEAF_NAMES = frozenset({
    "shared", "common", "core", "util", "utils", "helper", "helpers", "lib", "libs",
    "src", "index", "components", "internal", "base", "impl", "app", "main", "pkg",
    "cmd", "mod", "dist", "build",
})
_VERSION_SEG_RE = re.compile(r"^v\d+$", re.IGNORECASE)
# Per-area drill-down caps (keep each area compact; depth is via the tools).
MAX_KEY_FILES_PER_AREA = 6
MAX_KEY_SYMBOLS_PER_AREA = 5
# Symbol kinds that make sense as "entry-point" anchors (exclude file/module
# container nodes and data-only constants).
_ENTRY_SYMBOL_KINDS = frozenset(
    {"function", "method", "class", "interface", "struct", "trait", "enum"}
)
# Symbol kinds the graph emits that DO carry an accurate descriptive tag (req 7a):
# don't blanket-label every non-class node `(function)`. When a node's kind is not
# in this set it is rendered with NO kind tag rather than a wrong one.
_KNOWN_SYMBOL_KINDS = frozenset(
    {
        "function",
        "method",
        "class",
        "interface",
        "struct",
        "trait",
        "enum",
        "type",
        "typealias",
        "property",
        "const",
        "constant",
        "variable",
        "field",
        "enum-member",
        "enum_member",
        "module",
        "namespace",
    }
)
# Non-code source extensions (markup / styleguide / static assets). Nodes on these
# files must not form or contaminate code areas (req 7d).
_NON_CODE_FILE_EXTS = (
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".svg",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".md",
    ".mdx",
    ".markdown",
    ".rst",
    ".txt",
)
# Fixed cluster categories (Tests/Docs/Config/...) carry no navigational value as
# top-level product "areas"; they are noise in an orientation map.
_FIXED_COMMUNITY_LABELS = frozenset(
    {"Documentation", "Tests", "Benchmarks", "CI/CD", "Generated", "Scripts", "Configuration"}
)
# File extensions whose nodes are config/data, not real code symbols. A node on
# one of these files (or its keys) is never an "entry point" — JSON keys parse to
# `class`/`module` graph nodes but carry no behavior.
_CONFIG_FILE_EXTS = (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env")
# An area is rendered as **config** (files-only, no entry points, demoted below
# code areas) when at least this share of its member nodes live in config files.
CONFIG_AREA_NODE_SHARE = 0.6
# Oversized-area subdivision. When a single representative directory would
# collapse to one area larger than ``OVERSIZED_AREA_NODE_CAP`` nodes OR more than
# ``OVERSIZED_AREA_GRAPH_SHARE`` of the whole graph, its contributing communities
# are kept as SEPARATE sub-areas (labeled by sub-path + community) instead of
# being fused into one undifferentiated blob.
OVERSIZED_AREA_NODE_CAP = 400
OVERSIZED_AREA_GRAPH_SHARE = 0.25
# A private helper (leading-underscore label) is only surfaced as an entry point
# when it has at least this much cross-file fan-in (callers in other files).
PRIVATE_ENTRY_MIN_CROSS_FILE_FANIN = 2

DEFAULT_LAYER = "project"
OUTPUT_REL_PATH = "docs/references/codebase-map.md"

# Option A (req 6): the map refreshes a marker-delimited structural block in
# docs/repo-index.md. The human/agent narrative OUTSIDE these markers is never
# touched. The marker is seed-rooted (see seed 030-inventory-and-map) so any
# consuming project carries it.
REPO_INDEX_REL_PATH = "docs/repo-index.md"
REPO_INDEX_MARKER_BEGIN = "<!-- waveframework:repo-index-modules begin -->"
REPO_INDEX_MARKER_END = "<!-- waveframework:repo-index-modules end -->"

# Vendor-neutral per-area context file (1p5xc). The canonical name many agents
# read (the agents.md convention); never Claude-specific.
AREA_CONTEXT_FILENAME = "AGENTS.md"


# --------------------------------------------------------------------------- #
# Reusable area model (consumed by 1p5xc).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CodebaseArea:
    """One bounded top-level area of the codebase.

    ``1p5xc`` consumes this list to scaffold per-area ``AGENTS.md`` stubs and to
    link them from the map. Stable, deterministic, derived purely from the
    persisted artifacts.
    """

    area_id: str  # stable slug derived from representative_path (NOT community_id)
    name: str  # human label (cluster label, deduped)
    representative_path: str  # the directory this area collapses to
    responsibility: str  # one-line responsibility (from cluster label)
    key_files: tuple[str, ...]  # ranked in-scope source files
    key_symbols: tuple[dict[str, str], ...]  # ranked entry-point symbols (id/label/kind)
    hub_node_id: str  # STABLE drill-in handle for code_graph_community (never community_id)
    community_ids: tuple[str, ...]  # contributing community_ids (convenience; renumbering)
    node_count: int
    boundary_node_count: int
    is_config: bool = False  # config-only area: files-only, no entry points, demoted


@dataclass(frozen=True)
class CodebaseMapModel:
    """The full structured map model — the contract 1p5xc imports."""

    present: bool
    reason: str  # "" when present; an explanation when degraded/empty
    layer: str
    areas: tuple[CodebaseArea, ...]
    total_area_count: int  # may exceed len(areas) when the top tier is capped
    truncated: bool  # True when total_area_count > len(areas)
    grouping: str  # "package-directory" | "directory-fallback" | "none"
    cluster_builder_version: str
    cluster_schema_version: str
    graph_builder_version: str
    file_count: int
    symbol_count: int
    extra: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Offline artifact loading.
# --------------------------------------------------------------------------- #
def _load_sibling(module_name: str):
    path = Path(__file__).resolve().parent / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _graph_paths(root: Path, layer: str) -> tuple[Path, Path]:
    """Resolve graph + cluster artifact paths, reusing graph_cluster's helpers."""
    gc = _load_sibling("graph_cluster")
    return gc.graph_path(root, layer), gc.cluster_path(root, layer)


def _norm(node_id: str) -> str:
    return str(node_id).replace("\\", "/")


# --------------------------------------------------------------------------- #
# Ranking from graph signals (degree).
# --------------------------------------------------------------------------- #
def _degree_index(edges: list[dict[str, Any]]) -> dict[str, int]:
    degree: dict[str, int] = defaultdict(int)
    for edge in edges or []:
        if not isinstance(edge, dict):
            continue
        src = _norm(str(edge.get("source") or ""))
        tgt = _norm(str(edge.get("target") or ""))
        if not src or not tgt:
            continue
        degree[src] += 1
        degree[tgt] += 1
    return degree


def _cross_file_fanin_index(
    edges: list[dict[str, Any]], nodes_by_id: dict[str, dict[str, Any]]
) -> dict[str, int]:
    """Count, per target symbol, the number of DISTINCT caller files outside its own.

    This is the importance signal the orientation map ranks entry points by: a
    symbol called from many *other* files is a real entry point / chokepoint,
    whereas a ubiquitous leaf helper called all over its own module (high raw
    degree) is not. Self-file edges and edges touching unknown nodes are ignored.
    """
    callers: dict[str, set[str]] = defaultdict(set)
    for edge in edges or []:
        if not isinstance(edge, dict):
            continue
        src = _norm(str(edge.get("source") or ""))
        tgt = _norm(str(edge.get("target") or ""))
        if not src or not tgt:
            continue
        sn = nodes_by_id.get(src)
        tn = nodes_by_id.get(tgt)
        if sn is None or tn is None:
            continue
        s_sf = _norm(str(sn.get("source_file") or ""))
        t_sf = _norm(str(tn.get("source_file") or ""))
        if not s_sf or not t_sf or s_sf == t_sf:
            continue
        callers[tgt].add(s_sf)
    return {nid: len(files) for nid, files in callers.items()}


def _is_config_source(source_file: str) -> bool:
    return _norm(str(source_file or "")).lower().endswith(_CONFIG_FILE_EXTS)


def _is_non_code_source(source_file: str) -> bool:
    """Markup / styleguide / asset / prose files — not real code (req 7d)."""
    return _norm(str(source_file or "")).lower().endswith(_NON_CODE_FILE_EXTS)


def _glob_match(path: str, pattern: str) -> bool:
    """Match a normalized POSIX ``path`` against a `.gitignore`-style glob.

    ``**`` matches across directory separators; we lean on ``fnmatch`` (whose ``*``
    already crosses ``/``) by collapsing ``**`` to ``*``. Sufficient for the
    vendored-path patterns repos write (``**/instrumentation/el/**``, ``**/*.cjs``).
    """
    import fnmatch

    pat = (pattern or "").strip()
    if not pat:
        return False
    norm = _norm(str(path or ""))
    collapsed = pat.replace("**/", "*/").replace("**", "*")
    return fnmatch.fnmatch(norm, collapsed) or fnmatch.fnmatch(norm, collapsed.lstrip("*/"))


def _load_vendored_patterns(root: Path | None) -> list[str]:
    """Explicit vendored-path globs for the map (wave 1p64t), fail-safe.

    Two operator-controlled signals, no name heuristics:
      * ``docs/repo-profile.json`` ``vendored_paths``: a list of globs.
      * ``.gitattributes`` lines marked ``linguist-vendored`` (=true / bare): the
        leading token is the pattern (ecosystem-standard, pairs with linguist-generated).
    Missing/garbage files are a safe no-op (empty list → nothing is vendored).
    """
    if root is None:
        return []
    patterns: list[str] = []
    profile = Path(root) / "docs" / "repo-profile.json"
    try:
        if profile.is_file():
            data = json.loads(profile.read_text(encoding="utf-8"))
            vp = data.get("vendored_paths") if isinstance(data, dict) else None
            if isinstance(vp, list):
                patterns.extend(str(p).strip() for p in vp if str(p).strip())
    except (OSError, ValueError):
        pass
    gitattributes = Path(root) / ".gitattributes"
    try:
        if gitattributes.is_file():
            for raw in gitattributes.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "linguist-vendored" not in line or "linguist-vendored=false" in line:
                    continue
                pat = line.split()[0].strip()
                if pat:
                    patterns.append(pat)
    except OSError:
        pass
    return patterns


def _kind_tag(node: dict[str, Any]) -> str:
    """The accurate symbol-kind tag to display, or "" when undeterminable (req 7a).

    Never default to ``function``: only emit a tag for a kind the graph actually
    reports AND that is a recognized symbol kind. Otherwise return "" so the
    renderer omits the tag rather than mislabeling (TS type members, object
    props, theme tokens, route segments were all shown as ``(function)``).
    """
    raw = str(node.get("kind") or "").strip().lower()
    if not raw or raw not in _KNOWN_SYMBOL_KINDS:
        return ""
    # Normalize a couple of synonymous spellings for a stable display.
    return {
        "constant": "const",
        "enum_member": "enum-member",
        "typealias": "type",
    }.get(raw, raw)


def _is_doc_spec_config_label(label: str, node_ids: list[str]) -> bool:
    """True when a cluster label derives from doc/spec/config files (Solaris fix).

    A community whose members predominantly live in doc/spec/config sources yields
    a wrong-category label (`repo-index`, `current-state`, `manual-override-
    contract`). We reject such labels for Tier-1 naming.
    """
    if not node_ids:
        return False
    # The label is suspect when the area is mostly doc/spec/config sources.
    # (node access is via the closure caller; here we only get ids, so this is a
    # conservative string heuristic plus the caller's config detection.)
    lab = str(label or "").strip().lower()
    suspicious_tokens = (
        "readme",
        "index",
        "current-state",
        "manifest",
        "contract",
        "changelog",
        "license",
        "notes",
        "overview",
        "spec",
    )
    return any(tok in lab for tok in suspicious_tokens)


def _read_area_context_label(root: Path | None, rep_path: str) -> tuple[str, str]:
    """Tier-2 (req 4): read ``rep_path/AGENTS.md`` for an authoritative label.

    Returns ``(title, first_content_line)`` where ``title`` is the first
    ``# heading`` and ``first_content_line`` is the first non-empty, non-heading,
    non-metadata, non-HTML-comment line. Either may be "" when absent. The map
    re-reads this on every generation — durable knowledge lives in AGENTS.md, not
    in the generated map, so a regen can never lose it.
    """
    if root is None:
        return "", ""
    rep = (rep_path or "").strip("/")
    rel = AREA_CONTEXT_FILENAME if (not rep or rep == "(root)") else f"{rep}/{AREA_CONTEXT_FILENAME}"
    path = Path(root) / rel
    if not path.is_file():
        return "", ""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return "", ""
    title = ""
    first_line = ""
    metadata_prefixes = ("owner:", "status:", "last verified:", "wave:", "change ")
    in_comment = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if line.startswith("<!--"):
            if "-->" not in line:
                in_comment = True
            continue
        if line.startswith("#"):
            if not title:
                title = line.lstrip("#").strip()
                # An "— area context" suffix from the stub is noise; trim it.
                for sep in (" — ", " - ", " – "):
                    if sep in title:
                        title = title.split(sep, 1)[0].strip()
                        break
            continue
        low = line.lower()
        if any(low.startswith(p) for p in metadata_prefixes):
            continue
        if not first_line:
            first_line = line
            break
    return title, first_line


def _representative_dir(source_file: str) -> str:
    """The directory a file collapses to for the bounded top tier.

    This is the offline, source-free equivalent of package-to-directory collapse:
    the immediate parent directory of the file. Top-level files (no parent) map to
    a synthetic ``(root)`` bucket. Mirrors the intent of
    ``graph_query.collapse_package_to_directory_view`` without re-reading sources.
    """
    sf = _norm(source_file).strip("/")
    if not sf:
        return ""
    parent = sf.rsplit("/", 1)[0] if "/" in sf else ""
    return parent or "(root)"


def _slugify(text: str) -> str:
    out = []
    prev_dash = False
    for ch in str(text).lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-") or "area"


def _module2(dir_path: str) -> str:
    """The module prefix of a DIRECTORY path — its first two segments (wave 1p65m #2,
    generator-side coherence). `libs/utils/src` → `libs/utils`; `backend/apis` →
    `backend/apis`; empty/`(root)` → `(root)`. Used to keep an area's key-files/hub
    within the area's own module so cross-package strays a grab-bag community absorbed
    (e.g. backend `ldap.ts` in a `libs/utils` area) are not presented as its key files."""
    parts = [p for p in _norm(str(dir_path or "")).strip("/").split("/") if p and p != "(root)"]
    return "/".join(parts[:2]) if parts else "(root)"


def _qualify_structural_name(name: str, rep_path: str) -> str:
    """Wave 1p65l #5: qualify a non-descriptive structural/version leaf area name by
    walking up to the nearest distinctive ancestor directory segment. Ecosystem-
    neutral + deterministic: `…/github/cards/v1` → `github-cards (v1)`;
    `…/sailpoint/idn/shared` → `idn shared`. Descriptive leaves (e.g. `data-grid`)
    and non-structural names (cluster symbols) are returned unchanged.
    """
    is_version = bool(_VERSION_SEG_RE.match(name or ""))
    if not is_version and str(name or "").casefold() not in _STRUCTURAL_LEAF_NAMES:
        return name
    segs = [s for s in str(rep_path or "").strip("/").split("/") if s and s != "(root)"]
    # Distinctive ancestors (exclude the leaf), nearest-first.
    ancestors = [
        s for s in reversed(segs[:-1])
        if s.casefold() not in _STRUCTURAL_LEAF_NAMES and not _VERSION_SEG_RE.match(s)
    ]
    if not ancestors:
        return name
    if is_version:
        chosen = list(reversed(ancestors[:2]))  # outer→inner path order
        return f"{'-'.join(chosen)} ({name})"
    return f"{ancestors[0]} {name}"


def _area_module_key(area: "CodebaseArea") -> str:
    """Top-level module / source-root key for the per-module area floor (1p61w).

    The first path segment of the representative directory — coarse on purpose, so
    the floor guarantees breadth across top-level modules without one slot per leaf.
    """
    rep = (area.representative_path or "").strip("/")
    if not rep or rep == "(root)":
        return "(root)"
    return rep.split("/", 1)[0]


def _select_with_module_floor(areas: list["CodebaseArea"], cap: int) -> list["CodebaseArea"]:
    """Cap the area list while guaranteeing each top-level module at least one slot.

    Wave 1p61w (javaagent 2): pure size-ranked truncation let a large vendored /
    generated subtree consume the whole cap and drop small product modules to
    incidental key-files. Here the best-ranked area of each distinct module is
    reserved first (in rank order), then any remaining slots fill by overall rank.
    Input is already rank-sorted, so the output preserves rank order and is
    deterministic.
    """
    if len(areas) <= cap:
        return list(areas)
    seen: set[str] = set()
    guaranteed: list[int] = []
    for i, a in enumerate(areas):
        k = _area_module_key(a)
        if k not in seen:
            seen.add(k)
            guaranteed.append(i)
    chosen: set[int] = set(guaranteed[:cap])
    for i in range(len(areas)):
        if len(chosen) >= cap:
            break
        chosen.add(i)
    return [areas[i] for i in sorted(chosen)]


def _disambiguate_area_names(areas: list["CodebaseArea"]) -> list["CodebaseArea"]:
    """Strip ordinal noise and disambiguate colliding area titles (1p61w / javaagent 3).

    Cluster-label disambiguation appends trailing ordinals (``Foo 1`` / ``Foo 2``);
    those are dropped. Titles that then collide across distinct representative paths
    (5×``parser``, 4×``javax``) are re-titled to their last two path segments
    (``el/apache/parser`` vs ``el/javax``) so the area list isn't a wall of
    near-duplicates. Slug uniqueness is handled separately by ``_make_slug``.
    """
    cleaned: list["CodebaseArea"] = []
    for a in areas:
        new_name = re.sub(r"\s+\d+$", "", a.name).strip() or a.name
        cleaned.append(replace(a, name=new_name) if new_name != a.name else a)
    from collections import Counter

    name_counts = Counter(a.name for a in cleaned)
    out: list["CodebaseArea"] = []
    for a in cleaned:
        if name_counts[a.name] > 1:
            rep = (a.representative_path or "").strip("/")
            segs = [s for s in rep.split("/") if s]
            disamb = "/".join(segs[-2:]) if len(segs) >= 2 else (rep or a.name)
            out.append(replace(a, name=disamb) if disamb and disamb != a.name else a)
        else:
            out.append(a)
    # Final pass (1p64u / javaagent 3): subdivisions of ONE oversized directory
    # share a representative path, so the path-based pass leaves them colliding
    # (4×`el/javax`). Append a third distinguisher — the area's top entry-point
    # symbol if it has one, else its node count — so each title is unique and the
    # reader can tell `el/javax — ELContext` from `el/javax — 267 nodes`.
    final_counts = Counter(a.name for a in out)
    if any(v > 1 for v in final_counts.values()):
        result: list["CodebaseArea"] = []
        for a in out:
            if final_counts[a.name] > 1:
                anchor = a.key_symbols[0]["label"] if a.key_symbols else f"{a.node_count} nodes"
                result.append(replace(a, name=f"{a.name} — {anchor}"))
            else:
                result.append(a)
        out = result
    return out


# --------------------------------------------------------------------------- #
# Core: compute the structured area model (reused by 1p5xc).
# --------------------------------------------------------------------------- #
def compute_areas(root: Path, layer: str = DEFAULT_LAYER) -> CodebaseMapModel:
    """Compute the bounded, hierarchical area model from persisted artifacts.

    Deterministic for a fixed graph + cluster artifact. Fail-safe: on a
    missing/empty/partial graph this returns a model with ``present=False`` and a
    ``reason`` rather than raising. When the graph exists but the cluster artifact
    is missing, it degrades to directory-only grouping (``grouping="directory-fallback"``).
    """
    root = Path(root)
    graph_file, cluster_file = _graph_paths(root, layer)
    graph = _read_json(graph_file)
    cluster = _read_json(cluster_file)

    empty = CodebaseMapModel(
        present=False,
        reason="",
        layer=layer,
        areas=(),
        total_area_count=0,
        truncated=False,
        grouping="none",
        cluster_builder_version="",
        cluster_schema_version="",
        graph_builder_version="",
        file_count=0,
        symbol_count=0,
    )

    if not isinstance(graph, dict) or not graph.get("nodes"):
        return CodebaseMapModel(**{**empty.__dict__, "reason": "no persisted graph artifact"})

    nodes_raw = graph.get("nodes") or []
    edges_raw = graph.get("edges") or []
    graph_builder_version = str(graph.get("builder_version") or "")

    # Build node lookup. The graph already inherits index file-scoping — nodes
    # only exist for indexed/in-scope files, so we never see gitignored/secret
    # paths here. We do not re-scope.
    nodes_by_id: dict[str, dict[str, Any]] = {}
    for raw in nodes_raw:
        if not isinstance(raw, dict):
            continue
        nid = _norm(str(raw.get("id") or ""))
        if not nid or raw.get("kind") == "external" or nid.startswith("external::"):
            continue
        # req 7d: exclude non-code (markup/styleguide/asset/prose) nodes entirely
        # so they neither form their own areas nor pollute code communities.
        if _is_non_code_source(raw.get("source_file")):
            continue
        node = dict(raw)
        node["id"] = nid
        nodes_by_id[nid] = node

    if not nodes_by_id:
        return CodebaseMapModel(**{**empty.__dict__, "reason": "graph has no in-scope nodes"})

    degree = _degree_index(edges_raw)
    file_count = len({
        _norm(str(n.get("source_file") or ""))
        for n in nodes_by_id.values()
        if n.get("source_file")
    })
    symbol_count = sum(1 for n in nodes_by_id.values() if "::" in str(n.get("id") or ""))

    # Resolve cluster membership: node_id -> (community_id, label).
    communities = []
    cluster_builder_version = ""
    cluster_schema_version = ""
    if isinstance(cluster, dict) and cluster.get("communities"):
        communities = [c for c in cluster.get("communities") or [] if isinstance(c, dict)]
        cluster_builder_version = str(cluster.get("cluster_builder_version") or "")
        cluster_schema_version = str(cluster.get("cluster_schema_version") or "")

    grouping = "package-directory" if communities else "directory-fallback"

    # ---- Phase 1: assemble per-community context, skipping fixed categories. ----
    # community_id -> {label, node_ids}
    community_ctx: list[dict[str, Any]] = []
    # Wave 1p61w/1p64t: generated- and vendored-dominated communities are excluded
    # from the area tier, tracked for honest omitted-count footers (never silent).
    generated_omitted: list[str] = []
    vendored_omitted: list[str] = []
    _vendored_patterns = _load_vendored_patterns(root)

    def _generated_fraction(node_ids: list[str]) -> float:
        if not node_ids:
            return 0.0
        gen = sum(1 for nid in node_ids if bool(nodes_by_id.get(nid, {}).get("generated")))
        return gen / len(node_ids)

    def _vendored_fraction(node_ids: list[str]) -> float:
        if not node_ids or not _vendored_patterns:
            return 0.0
        ven = 0
        for nid in node_ids:
            sf = str(nodes_by_id.get(nid, {}).get("source_file") or "")
            if sf and any(_glob_match(sf, pat) for pat in _vendored_patterns):
                ven += 1
        return ven / len(node_ids)

    def _is_type_only_community(node_ids: list[str]) -> bool:
        """Wave 1p65l #4: a community whose symbol nodes are predominantly type-shape
        kinds (type/interface/property/enum) — a pure type-declaration grouping.
        Detected by node KIND (accurate post-1p61v), NOT by `.types` filename, so it
        is language-generic. Multiple such communities in one package collapse into a
        single "types" area instead of one area per type file."""
        kinds = [str(nodes_by_id[n].get("kind") or "") for n in node_ids if "::" in n]
        if not kinds:
            return False
        type_kinds = {"type", "typealias", "interface", "property", "enum", "enum-member", "enum_member"}
        return sum(1 for k in kinds if k in type_kinds) >= 0.8 * len(kinds)

    def _is_vendored_or_generated(nid: str) -> bool:
        """Wave 1p65l #1: a node is vendored (explicit `vendored_paths`/`linguist-
        vendored` signal) or `generated`-tagged. Such a node must never be surfaced
        as a key file, key entry point, or drill-in hub of a product area — even
        when it is a minority absorbed into a product-dominated community (so the
        area-level fraction gate doesn't catch it). Generic: same explicit signals
        the vendored axis + the graph's `generated` tag already use."""
        node = nodes_by_id.get(nid, {})
        if bool(node.get("generated")):
            return True
        sf = str(node.get("source_file") or "")
        return bool(sf and _vendored_patterns and any(_glob_match(sf, p) for p in _vendored_patterns))

    if communities:
        for c in communities:
            label = str(c.get("label") or "").strip()
            if label in _FIXED_COMMUNITY_LABELS or c.get("kind") == "fixed":
                continue
            node_ids = [_norm(str(n)) for n in (c.get("node_ids") or []) if _norm(str(n)) in nodes_by_id]
            if not node_ids:
                continue
            # Wave 1p61w (javaagent 1a): drop generated-dominated communities (e.g. a
            # 99%-generated JavaCC parser that otherwise renders as a prominent area).
            # Prefer the persisted per-community `generated_node_fraction` (Aceiss §6.5);
            # fall back to recomputing from per-node `generated` tags.
            gen_fraction = c.get("generated_node_fraction")
            if gen_fraction is None:
                gen_fraction = _generated_fraction(node_ids)
            if float(gen_fraction) > GENERATED_AREA_FRACTION:
                generated_omitted.append(label or "area")
                continue
            # Wave 1p64t (javaagent 1b): drop vendored-dominated communities (e.g. a
            # bundled third-party EL implementation) — third-party, not product.
            if _vendored_fraction(node_ids) > VENDORED_AREA_FRACTION:
                vendored_omitted.append(label or "area")
                continue
            community_ctx.append({
                "community_id": str(c.get("community_id") or ""),
                "label": label or "area",
                "node_ids": node_ids,
            })
    else:
        # Directory-fallback: synthesize one pseudo-community per directory so the
        # same collapse pipeline runs. Label = directory basename.
        by_dir: dict[str, list[str]] = defaultdict(list)
        for nid, node in nodes_by_id.items():
            sf = str(node.get("source_file") or "")
            if not sf:
                continue
            by_dir[_representative_dir(sf)].append(nid)
        for d, ids in by_dir.items():
            label = (d.rsplit("/", 1)[-1] if "/" in d else d) or "area"
            if _generated_fraction(ids) > GENERATED_AREA_FRACTION:
                generated_omitted.append(label)
                continue
            if _vendored_fraction(ids) > VENDORED_AREA_FRACTION:
                vendored_omitted.append(label)
                continue
            community_ctx.append({
                "community_id": "",
                "label": label,
                "node_ids": ids,
            })

    if not community_ctx:
        return CodebaseMapModel(
            present=False,
            reason="no navigable (non-fixed) communities or directories",
            layer=layer,
            areas=(),
            total_area_count=0,
            truncated=False,
            grouping="none",
            cluster_builder_version=cluster_builder_version,
            cluster_schema_version=cluster_schema_version,
            graph_builder_version=graph_builder_version,
            file_count=file_count,
            symbol_count=symbol_count,
        )

    # Cross-file fan-in: the importance signal for entry-point ranking (callers
    # in OTHER files). Computed once over the whole graph.
    cross_file_fanin = _cross_file_fanin_index(edges_raw, nodes_by_id)

    def _dominant_code_token(node_ids: list[str]) -> str:
        """Tier-1 (b): the most common alphabetic token shared across the area's
        *code* symbol/file names (length >= 3, not generic), or "" when none."""
        from collections import Counter

        generic_tokens = {
            "the", "and", "for", "with", "from", "this", "that", "def", "var",
            "get", "set", "new", "src", "lib", "app", "mod", "test", "tests",
            "util", "utils", "init", "main", "py", "ts", "js", "tsx", "jsx",
        }
        counts: Counter[str] = Counter()
        for nid in node_ids:
            node = nodes_by_id[nid]
            if _is_config_source(node.get("source_file")) or _is_non_code_source(
                node.get("source_file")
            ):
                continue
            label = str(node.get("label") or "")
            stem = _norm(str(node.get("source_file") or "")).rsplit("/", 1)[-1]
            stem = stem.rsplit(".", 1)[0]
            for raw in (label, stem):
                cur = ""
                for ch in raw:
                    if ch.isalnum():
                        cur += ch.lower()
                    else:
                        if len(cur) >= 3 and cur not in generic_tokens and not cur.isdigit():
                            counts[cur] += 1
                        cur = ""
                if len(cur) >= 3 and cur not in generic_tokens and not cur.isdigit():
                    counts[cur] += 1
        if not counts:
            return ""
        token, freq = max(counts.items(), key=lambda kv: (kv[1], -len(kv[0]), kv[0]))
        # Only meaningful when shared by more than one member.
        return token if freq >= 2 else ""

    def _central_code_symbol_label(node_ids: list[str]) -> str:
        """Tier-1 (c): the highest-degree real code symbol's label, or ""."""
        best: tuple[int, str] | None = None
        for nid in node_ids:
            if "::" not in nid:
                continue
            node = nodes_by_id[nid]
            if _is_config_source(node.get("source_file")) or _is_non_code_source(
                node.get("source_file")
            ):
                continue
            if str(node.get("kind") or "") not in _ENTRY_SYMBOL_KINDS:
                continue
            cand = (degree.get(nid, 0), str(node.get("label") or ""))
            if best is None or (cand[0], cand[1]) > (best[0], best[1]):
                best = cand
        return best[1] if best else ""

    def _dominant_dir(node_ids: list[str]) -> str:
        dir_counts: dict[str, int] = defaultdict(int)
        for nid in node_ids:
            d = _representative_dir(str(nodes_by_id[nid].get("source_file") or ""))
            if d:
                dir_counts[d] += 1
        if not dir_counts:
            return ""
        return min(dir_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]

    # ---- Phase 2: collapse communities to their representative directory. ----
    # This is the bounded TOP tier. Each directory bucket accumulates the
    # contributing communities (each kept as a separate "part" so an oversized
    # bucket can be SUBDIVIDED back into per-community sub-areas rather than fused
    # into one undifferentiated blob).
    area_buckets: dict[str, dict[str, Any]] = {}
    for ctx in community_ctx:
        rep_dir = _dominant_dir(ctx["node_ids"])
        if not rep_dir:
            continue
        bucket = area_buckets.setdefault(rep_dir, {
            "representative_path": rep_dir,
            "parts": [],  # one entry per contributing community
            "node_ids": set(),
        })
        bucket["parts"].append(ctx)
        bucket["node_ids"].update(ctx["node_ids"])

    # ---- Phase 2.5: surface BURIED significant directories (wave 1p64u). ----
    # A product module whose files are absorbed into a larger cross-directory
    # community (joined only by, e.g., a shared `toJson` call) never becomes that
    # community's dominant directory, so it has no area — it shows only as an
    # incidental key-file. Synthesize a directory area for any in-scope dir that
    # clears the file floor and is not already a bucket. Additive (does not disturb
    # the community buckets); the cap + per-module floor bound the result. Excludes
    # config/non-code/generated/vendored sources so it never resurrects that noise.
    existing_rep_dirs = set(area_buckets.keys())
    files_by_dir: dict[str, set[str]] = defaultdict(set)
    nodes_by_dir: dict[str, list[str]] = defaultdict(list)
    for nid, node in nodes_by_id.items():
        sf = _norm(str(node.get("source_file") or ""))
        if not sf or _is_config_source(sf) or _is_non_code_source(sf):
            continue
        if bool(node.get("generated")):
            continue
        if _vendored_patterns and any(_glob_match(sf, p) for p in _vendored_patterns):
            continue
        d = _representative_dir(sf)
        if not d or d == "(root)" or d in existing_rep_dirs:
            continue
        files_by_dir[d].add(sf)
        nodes_by_dir[d].append(nid)
    for d in sorted(files_by_dir):
        if len(files_by_dir[d]) < MODULE_FLOOR_MIN_FILES:
            continue
        ids = nodes_by_dir[d]
        bucket = area_buckets.setdefault(d, {
            "representative_path": d, "parts": [], "node_ids": set(),
        })
        bucket["parts"].append({
            "community_id": "",
            "label": (d.rsplit("/", 1)[-1] if "/" in d else d) or "area",
            "node_ids": ids,
        })
        bucket["node_ids"].update(ids)

    # ---- Phase 3: rank + finalize areas (with subdivision + config demotion). ----
    used_slugs: dict[str, int] = {}

    def _make_slug(name: str, rep_dir: str) -> str:
        slug = _slugify(name) or _slugify(rep_dir)
        if slug in used_slugs:
            used_slugs[slug] += 1
            slug = f"{slug}-{used_slugs[slug]}"
        else:
            used_slugs[slug] = 1
        return slug

    def _finalize(node_ids: list[str], labels, community_ids, rep_path: str) -> CodebaseArea | None:
        node_ids = sorted(set(node_ids))
        if not node_ids:
            return None

        # Config detection: an area is config-only when its members predominantly
        # live in config files (JSON keys parse to fake `class` nodes — never code).
        config_members = sum(1 for n in node_ids if _is_config_source(nodes_by_id[n].get("source_file")))
        is_config = config_members >= max(1, round(CONFIG_AREA_NODE_SHARE * len(node_ids)))

        # Tier-1 auto label (req 4): NEVER a doc/spec/config node as the
        # representative (Solaris fix). Prefer, in order: a meaningful directory
        # segment (skipping generic roots), then the dominant shared code token,
        # then the most-central code symbol — disambiguated by path, never a bare
        # `N` suffix (the slugger handles uniqueness).
        labels_sorted = sorted(labels, key=lambda lt: (-lt[0], lt[1].casefold()))
        cluster_label = labels_sorted[0][1] if labels_sorted else ""
        seg = rep_path.rsplit("/", 1)[-1] if "/" in rep_path else rep_path
        if seg == "(root)":
            seg = ""
        generic = {"", "scripts", "src", "lib", "app", "source", "code", "pkg", "internal", "lib"}
        # The cluster label is usable only when it is not a doc/spec/config-derived
        # name (those are the wrong-category Solaris labels) and not generic.
        cluster_label_ok = bool(
            cluster_label
            and cluster_label.casefold() not in generic
            and not _is_doc_spec_config_label(cluster_label, node_ids)
        )
        if seg and seg.casefold() not in generic:
            name = seg
        elif is_config:
            # Wave 1p65l #3-name: a config area must NEVER borrow a doc-prose cluster
            # label that strayed into the community ("Agent Entry Guide"); when it has
            # no meaningful directory segment, use a neutral, language-agnostic label.
            name = "configuration"
        elif cluster_label_ok:
            name = cluster_label
        else:
            token = _dominant_code_token(node_ids)
            central = _central_code_symbol_label(node_ids)
            name = token or (cluster_label if cluster_label_ok else "") or central or seg or rep_path
        # Wave 1p65l #5: qualify a non-descriptive structural/version leaf name
        # (`v1`, `shared`, …) by walking up to a distinctive ancestor — deterministic,
        # so it also stabilizes names across rebuilds. No-op for descriptive names.
        name = _qualify_structural_name(name, rep_path)

        # Entry points (code areas only): rank by cross-file fan-in (desc),
        # tiebreak degree, then id. Exclude config-derived nodes; prefer real code
        # kinds; drop trivial private helpers UNLESS they have meaningful
        # cross-file fan-in.
        key_symbols: tuple[dict[str, str], ...] = ()
        if not is_config:
            candidates = []
            for n in node_ids:
                if "::" not in n:
                    continue
                node = nodes_by_id[n]
                if str(node.get("kind") or "") not in _ENTRY_SYMBOL_KINDS:
                    continue
                if _is_config_source(node.get("source_file")):
                    continue
                if _is_vendored_or_generated(n):  # 1p65l #1: never a vendored/generated entry point
                    continue
                label = str(node.get("label") or n)
                fanin = cross_file_fanin.get(n, 0)
                # Dunder/constructor noise (`__init__`, `__call__`, …) carries no
                # orientation value — skip unless nothing else qualifies.
                is_dunder = label.startswith("__") and label.endswith("__")
                # Trivial private helper: leading-underscore label with no
                # meaningful cross-file fan-in — filter out.
                if (
                    label.startswith("_")
                    and not is_dunder
                    and fanin < PRIVATE_ENTRY_MIN_CROSS_FILE_FANIN
                ):
                    continue
                candidates.append((n, label, is_dunder))
            candidates.sort(
                key=lambda c: (c[2], -cross_file_fanin.get(c[0], 0), -degree.get(c[0], 0), c[0])
            )
            # Dedupe by display label (keep the highest-ranked occurrence).
            seen_labels: set[str] = set()
            picked: list[str] = []
            for n, label, _ in candidates:
                if label in seen_labels:
                    continue
                seen_labels.add(label)
                picked.append(n)
                if len(picked) >= MAX_KEY_SYMBOLS_PER_AREA:
                    break
            key_symbols = tuple(
                {
                    "id": n,
                    "label": str(nodes_by_id[n].get("label") or n),
                    # req 7a: accurate kind tag or "" (never blanket `function`).
                    "kind": _kind_tag(nodes_by_id[n]),
                }
                for n in picked
            )

        # Key files: in-scope source files ranked by summed member degree.
        # Wave 1p65l #1: a vendored/generated file is never a "key file" of a product
        # area, even as an absorbed minority (the area-fraction gate misses it).
        # Wave 1p65m #2 (generator-side cohesion): restrict to files within the area's
        # OWN module (first-two-segment prefix of its representative dir) so a
        # cross-directory grab-bag community can't present another package's strays
        # (e.g. backend `ldap.ts` in a `libs/utils` area) as key files. Fail-safe:
        # falls back to the unrestricted set if the module filter would empty it.
        area_module = _module2(rep_path)

        def _score_files(restrict_module: bool) -> dict[str, int]:
            fs: dict[str, int] = defaultdict(int)
            for n in node_ids:
                if _is_vendored_or_generated(n):
                    continue
                sf = _norm(str(nodes_by_id[n].get("source_file") or ""))
                if not sf:
                    continue
                if (
                    restrict_module
                    and area_module != "(root)"
                    and _module2(_representative_dir(sf)) != area_module
                ):
                    continue
                fs[sf] += degree.get(n, 0) + 1
            return fs

        file_score = _score_files(restrict_module=True) or _score_files(restrict_module=False)
        key_files = tuple(
            f for f, _ in sorted(file_score.items(), key=lambda kv: (-kv[1], kv[0]))[:MAX_KEY_FILES_PER_AREA]
        )

        # Hub = STABLE drill-in handle (never a community_id). req 7c: the hub MUST
        # be a member of the area's representative package AND live in a key-file,
        # so drilling in never lands outside the area. Rank candidates by degree.
        key_file_set = set(key_files)

        def _hub_rank(n: str) -> tuple[int, str]:
            return (-degree.get(n, 0), n)

        in_rep_and_keyfiles = [
            n
            for n in node_ids
            if _norm(str(nodes_by_id[n].get("source_file") or "")) in key_file_set
            and _representative_dir(str(nodes_by_id[n].get("source_file") or "")) == rep_path
        ]
        in_keyfiles = [
            n
            for n in node_ids
            if _norm(str(nodes_by_id[n].get("source_file") or "")) in key_file_set
        ]
        in_rep = [
            n
            for n in node_ids
            if _representative_dir(str(nodes_by_id[n].get("source_file") or "")) == rep_path
        ]
        hub_pool = in_rep_and_keyfiles or in_keyfiles or in_rep or node_ids
        # Wave 1p61w (teton Issue 3): a drill-in hub must be actionable first-party
        # source — never a `.json`/data node (`…json::map`) or other non-code asset.
        # Prefer code candidates; fall back to the full pool only if none remain.
        # Wave 1p65l #1: also exclude vendored/generated from the hub — `otel.cjs`
        # (a `.cjs` code-ext bundle) otherwise won the drill-in hub, routing an agent
        # into a vendored dependency. Fall back to the full pool only if nothing else.
        _code_hub_pool = [
            n for n in hub_pool
            if not _is_non_code_source(nodes_by_id[n].get("source_file"))
            and not _is_config_source(nodes_by_id[n].get("source_file"))
            and not _is_vendored_or_generated(n)
        ]
        # Wave 1p65m #2: the drill-in hub should be within the area's OWN module, not
        # a cross-package stray the community absorbed. Fail-safe: fall back through
        # the code pool then the full pool if the module filter would empty it.
        _module_hub_pool = [
            n for n in _code_hub_pool
            if area_module == "(root)"
            or _module2(_representative_dir(str(nodes_by_id[n].get("source_file") or ""))) == area_module
        ]
        hub_node_id = min(_module_hub_pool or _code_hub_pool or hub_pool, key=_hub_rank)

        # Tier-2 authoritative labels (req 4): when the area's
        # ``representative_path/AGENTS.md`` exists, its first ``# heading`` becomes
        # the label and its first content line the responsibility, overriding the
        # auto-label. The map re-reads AGENTS.md every generation (knowledge lives
        # in AGENTS.md, never stored in the map — so a regen can never lose it).
        title, first_line = _read_area_context_label(root, rep_path)
        if title and not is_config:
            name = title
        # Responsibility (wave 1p60q): the AGENTS.md first content line is
        # authoritative; otherwise mirror the chosen ``name``. Do NOT fall back
        # to the graph ``cluster_label`` — when ``name`` is directory-derived, an
        # unrelated high-fan-in cluster symbol (`logger`, `BackendApi`) disagrees
        # with the directory name (`packages`, `lambdas`) and reads as a broken /
        # inconsistent area (teton p60n field re-test: name ≠ Responsibility in
        # 14/24 areas). The name/Responsibility derivations must never contradict.
        #
        # Wave 1p64u (teton p64p): a CONFIG area must NOT adopt an AGENTS.md prose
        # instruction that merely landed in the same community ("If the user's
        # request matches a phrase below…") as its responsibility — describe the
        # config files instead. (The AGENTS.md title is likewise not the config
        # area's name.)
        if is_config:
            responsibility = "configuration / manifest files"
        else:
            responsibility = first_line or name

        return CodebaseArea(
            area_id=_make_slug(name, rep_path),
            name=name,
            representative_path=rep_path,
            responsibility=responsibility,
            key_files=key_files,
            key_symbols=key_symbols,
            hub_node_id=hub_node_id,
            community_ids=tuple(sorted(community_ids)),
            node_count=len(node_ids),
            boundary_node_count=0,
            is_config=is_config,
        )

    # Subdivide an area that dominates the map. Two triggers, both requiring the
    # bucket to be substantial in absolute terms (so a tiny repo never subdivides
    # its largest area): more than the absolute node cap, OR more than a share of
    # the whole graph while still clearing a meaningful floor.
    graph_share_threshold = OVERSIZED_AREA_GRAPH_SHARE * len(nodes_by_id)

    def _is_oversized(total_nodes: int) -> bool:
        if total_nodes > OVERSIZED_AREA_NODE_CAP:
            return True
        # Relative trigger: a large graph whose dominant area is a big share of it,
        # but still gated by an absolute floor so small repos are unaffected.
        return total_nodes > graph_share_threshold and total_nodes >= OVERSIZED_AREA_NODE_CAP

    raw_areas: list[CodebaseArea] = []
    # Deterministic bucket order (largest first, path tiebreak) so slug suffixes
    # are stable across runs.
    bucket_order = sorted(
        area_buckets.items(), key=lambda kv: (-len(kv[1]["node_ids"]), kv[0])
    )
    for rep_dir, bucket in bucket_order:
        parts = bucket["parts"]
        total_nodes = len(bucket["node_ids"])
        # Subdivide an oversized directory bucket into its contributing
        # communities (each a navigable sub-area), but only when there is real
        # structure to split (more than one community).
        if _is_oversized(total_nodes) and len(parts) > 1:
            # Wave 1p65l #4: collapse the type-only sub-communities into ONE "types"
            # sub-area (by KIND, generic) instead of one area per type file; emit the
            # rest per-community as before.
            type_only_parts = [c for c in parts if _is_type_only_community(c["node_ids"])]
            other_parts = [c for c in parts if c not in type_only_parts]
            for ctx in sorted(other_parts, key=lambda c: (-len(c["node_ids"]), c["label"].casefold())):
                area = _finalize(
                    ctx["node_ids"],
                    [(len(ctx["node_ids"]), ctx["label"])],
                    [ctx["community_id"]] if ctx["community_id"] else [],
                    rep_dir,
                )
                if area is not None:
                    raw_areas.append(area)
            if type_only_parts:
                merged_ids = sorted({n for c in type_only_parts for n in c["node_ids"]})
                merged_cids = [c["community_id"] for c in type_only_parts if c["community_id"]]
                area = _finalize(merged_ids, [(len(merged_ids), "types")], merged_cids, rep_dir)
                if area is not None:
                    raw_areas.append(area)
        else:
            labels = [(len(c["node_ids"]), c["label"]) for c in parts]
            community_ids = [c["community_id"] for c in parts if c["community_id"]]
            area = _finalize(sorted(bucket["node_ids"]), labels, community_ids, rep_dir)
            if area is not None:
                raw_areas.append(area)

    # Rank areas: code areas before config areas, then by size, then path.
    raw_areas.sort(key=lambda a: (a.is_config, -a.node_count, a.representative_path))
    total = len(raw_areas)
    # Wave 1p61w (javaagent 2): per-module area floor — guarantee each distinct
    # top-level module/source-root at least one slot before remaining slots fill by
    # rank, so a large vendored/generated subtree can't consume the whole cap and
    # starve small product modules (e.g. instrumentation/<module>).
    capped = _select_with_module_floor(raw_areas, MAX_TOP_AREAS)
    # Wave 1p61w (javaagent 3): disambiguate colliding area titles + drop ordinal
    # noise so the area list doesn't read as a wall of near-duplicates.
    capped = _disambiguate_area_names(capped)

    return CodebaseMapModel(
        present=bool(capped),
        reason="" if capped else "no areas after collapse",
        layer=layer,
        areas=tuple(capped),
        total_area_count=total,
        truncated=total > len(capped),
        grouping=grouping if capped else "none",
        cluster_builder_version=cluster_builder_version,
        cluster_schema_version=cluster_schema_version,
        graph_builder_version=graph_builder_version,
        file_count=file_count,
        symbol_count=symbol_count,
        extra={
            "generated_areas_omitted": len(generated_omitted),
            "generated_omitted_sample": sorted(set(generated_omitted))[:3],
            "vendored_areas_omitted": len(vendored_omitted),
            "vendored_omitted_sample": sorted(set(vendored_omitted))[:3],
        },
    )


# --------------------------------------------------------------------------- #
# Rendering (separate concern from computation).
# --------------------------------------------------------------------------- #
def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _area_context_rel_path(area: CodebaseArea) -> str:
    """The conventional per-area ``AGENTS.md`` *authoring* location for an area.

    Vendor-neutral: the area's representative path (the ``(root)`` bucket maps to
    the repository root). This is where the scaffold writes a stub and what the
    "author one" hint points at — NOT necessarily where an authored file is read
    from. Reading/linking uses :func:`_resolve_area_context_rel_path`, which walks
    UP to the nearest existing ancestor ``AGENTS.md`` (1p66d).
    """
    rep = (area.representative_path or "").strip("/")
    if not rep or rep == "(root)":
        return AREA_CONTEXT_FILENAME
    return f"{rep}/{AREA_CONTEXT_FILENAME}"


def _resolve_area_context_rel_path(root: Path | None, area: CodebaseArea) -> str | None:
    """The repo-root-relative path of the ``AGENTS.md`` that an area should LINK to.

    Walks UP from the area's representative-path directory toward the repo root and
    returns the **nearest existing** ``AGENTS.md`` (1p66d). Conventional per-area
    files live at project roots (e.g. ``libs/ui/AGENTS.md``) while an area's
    representative path is a deep subdirectory (``libs/ui/src/components/buttons``),
    and a single project spawns several areas at different deep paths — so resolving
    only the exact representative path misses the file. Walking up also makes the
    link robust to representative-path churn across rebuilds.

    Bound (Requirement 4): for a non-root area the repo-root ``AGENTS.md`` is NOT a
    fallback — the global operating guide is surfaced by the synthetic ``(root)``
    area and ``wavefoundry://agents``, and linking it from every unrelated area is
    noise. The walk therefore stops above the top-level segment and never reaches
    the repo root for a non-root area.

    Deterministic: nearest-ancestor-first over a path-segment walk; independent of
    any dict/set iteration order. Returns ``None`` when no ancestor has one.
    """
    if root is None:
        return None
    root = Path(root)
    rep = (area.representative_path or "").strip("/")
    if not rep or rep == "(root)":
        cand = root / AREA_CONTEXT_FILENAME
        return AREA_CONTEXT_FILENAME if cand.is_file() else None
    segs = [s for s in rep.split("/") if s]
    # Nearest-first: rep dir, then each ancestor down to the top-level segment.
    # ``segs[:0]`` (the repo root) is intentionally excluded for non-root areas.
    for i in range(len(segs), 0, -1):
        rel = "/".join(segs[:i]) + "/" + AREA_CONTEXT_FILENAME
        if (root / rel).is_file():
            return rel
    return None


def _area_context_exists(root: Path | None, area: CodebaseArea) -> bool:
    return _resolve_area_context_rel_path(root, area) is not None


def _area_context_link_href(rel_path: str) -> str:
    """The per-area ``AGENTS.md`` href RELATIVE TO THE RENDERED MAP FILE.

    The map lives at ``OUTPUT_REL_PATH`` (``docs/references/codebase-map.md``);
    docs-lint resolves markdown links against the file's own directory, so a
    repo-root-relative href (e.g. ``libs/ui/AGENTS.md``) would be a broken link.
    This returns the href relative to the map's directory. ``rel_path`` is the
    resolved repo-root-relative path from :func:`_resolve_area_context_rel_path`.
    """
    map_dir = PurePosixPath(OUTPUT_REL_PATH).parent
    target = PurePosixPath(rel_path)
    return os.path.relpath(target.as_posix(), map_dir.as_posix())


def render_markdown(
    model: CodebaseMapModel,
    *,
    last_verified: str | None = None,
    root: Path | None = None,
) -> str:
    """Render the docs-lint-clean codebase map markdown from the area model.

    Header carries Owner / Status / Last verified (docs-lint requires these).
    All tool handles and ids are wrapped in inline code so the link checker
    ignores them. No timestamps that churn beyond the docs-lint-required
    ``Last verified`` date.

    When ``root`` is supplied, each area is linked to the nearest ancestor
    ``AGENTS.md`` (1p66d — resolved by walking up from the representative path),
    so an agent routed to the area can pick up its local conventions/gotchas on
    demand even when the file lives at the conventional project root.
    """
    lv = last_verified or _today()
    lines: list[str] = []
    lines.append("# Codebase Map")
    lines.append("")
    lines.append("Owner: Engineering")
    lines.append("Status: generated")
    lines.append(f"Last verified: {lv}")
    lines.append("")
    lines.append(
        "<!-- GENERATED by .wavefoundry/framework/scripts/gen_codebase_map.py — "
        "do not edit by hand; regenerated with the index build. -->"
    )
    lines.append("")
    lines.append(
        "This is a generated, read-only orientation map of this project's own "
        "codebase, built offline from the persisted graph + community-cluster "
        "artifacts the index already produces. It is the **index to the index**: "
        "it routes you to the right area, then hands off to the `code_*` tools "
        "for depth. It carries no per-function detail by design."
    )
    lines.append("")

    if not model.present:
        reason = model.reason or "the index/cluster artifacts are not yet available"
        lines.append("## Status")
        lines.append("")
        lines.append(
            f"No map could be generated: {reason}. Build the index "
            "(`python3 .wavefoundry/framework/scripts/setup_index.py --root . --include-code`) "
            "and regenerate "
            "(`python3 .wavefoundry/framework/scripts/gen_codebase_map.py --root .`)."
        )
        lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    # Provenance / staleness.
    lines.append("## How to read this")
    lines.append("")
    lines.append(
        "- Each **area** is a domain of the codebase, collapsed from the graph's "
        "communities to a representative package/directory so the top tier stays "
        "bounded at any repo size."
    )
    lines.append(
        "- **Drill in** by passing an area's `hub_node_id` (a stable cross-rebuild "
        "anchor) to `code_graph_community`, or open its key files with "
        "`code_outline`. Use `hub_node_id`, never a `community_id` (those renumber "
        "on re-cluster)."
    )
    lines.append(
        "- The map is regenerated with the index build; it tracks index freshness "
        "rather than per-commit parity."
    )
    lines.append("")

    grouping_note = (
        "graph communities collapsed to packages/directories"
        if model.grouping == "package-directory"
        else "directory grouping (no cluster artifact available — degraded mode)"
    )
    lines.append(
        f"_Grouping: {grouping_note}. Areas shown: {len(model.areas)} of "
        f"{model.total_area_count}. Cluster builder version: "
        f"`{model.cluster_builder_version or 'n/a'}`. Files in scope: "
        f"{model.file_count}; symbols: {model.symbol_count}._"
    )
    lines.append("")
    # Wave 1p61w (javaagent 1a): never silently drop — surface the count of
    # generated-dominated communities excluded from the area tier so coverage stays
    # honest (they remain searchable via the `code_*` tools).
    _gen_omitted = int((model.extra or {}).get("generated_areas_omitted") or 0)
    if _gen_omitted:
        _sample = [s for s in (model.extra or {}).get("generated_omitted_sample") or [] if s]
        _eg = f" (e.g. {', '.join('`' + s + '`' for s in _sample)})" if _sample else ""
        lines.append(
            f"_{_gen_omitted} generated-dominated "
            f"{'community' if _gen_omitted == 1 else 'communities'} omitted from areas"
            f"{_eg} — still searchable via the `code_*` tools._"
        )
        lines.append("")
    # Wave 1p64t (javaagent 1b): same honest footer for vendored / third-party.
    _ven_omitted = int((model.extra or {}).get("vendored_areas_omitted") or 0)
    if _ven_omitted:
        _vsample = [s for s in (model.extra or {}).get("vendored_omitted_sample") or [] if s]
        _veg = f" (e.g. {', '.join('`' + s + '`' for s in _vsample)})" if _vsample else ""
        lines.append(
            f"_{_ven_omitted} vendored / third-party "
            f"{'community' if _ven_omitted == 1 else 'communities'} omitted from areas"
            f"{_veg} — still searchable via the `code_*` tools._"
        )
        lines.append("")

    lines.append("## Areas")
    lines.append("")

    for area in model.areas:
        heading = f"{area.name} (config)" if area.is_config else area.name
        lines.append(f"### {heading}")
        lines.append("")
        lines.append(f"- Path: `{area.representative_path}`")
        # Wave 1p662: stable, URI-safe area key for the `wavefoundry://area/{id}`
        # MCP resource (a representative path with slashes can't be a single-segment
        # URI template parameter; the area_id slug can).
        lines.append(f"- Area id: `{area.area_id}` (MCP: `wavefoundry://area/{area.area_id}`)")
        lines.append(f"- Responsibility: {area.responsibility}")
        lines.append(f"- Size: {area.node_count} graph nodes")
        if area.is_config:
            # Config-only area: files only — NO entry points (JSON keys are not
            # code symbols), and clearly tagged as configuration/data.
            lines.append(
                "- Kind: configuration/data (no code entry points; this area is "
                "config/manifest files)."
            )
        elif area.key_symbols:
            anchors = ", ".join(
                f"`{s['label']}`" + (f" ({s['kind']})" if s["kind"] else "")
                for s in area.key_symbols
            )
            lines.append(f"- Key entry points (by cross-file fan-in): {anchors}")
        if area.key_files:
            files = ", ".join(f"`{f}`" for f in area.key_files)
            lines.append(f"- Key files: {files}")
        # Per-area AGENTS.md link ONLY when a file actually exists on disk
        # (1p5xc map-link bug fix: never link a non-existent file → docs-lint
        # broken-link failure). Resolution walks UP to the nearest ancestor
        # AGENTS.md (1p66d) so conventionally project-root-placed files are found.
        ctx_rel = _resolve_area_context_rel_path(root, area)
        if ctx_rel:
            ctx_href = _area_context_link_href(ctx_rel)  # map-relative href (resolves)
            lines.append(
                f"- Area context: [{ctx_rel}]({ctx_href}) — conventions/gotchas; "
                "consult before working in this area."
            )
        lines.append(
            f"- Drill in: `code_graph_community(hub_node_id=\"{area.hub_node_id}\")` "
            f"or `code_outline` on the key files above."
        )
        lines.append("")

    if model.truncated:
        remaining = model.total_area_count - len(model.areas)
        lines.append("## More areas")
        lines.append("")
        lines.append(
            f"{remaining} additional smaller area(s) are not shown here to keep the "
            "top tier readable. Enumerate the full community structure with "
            "`code_graph_report(sections=[\"communities\"], limit=100)` and drill in "
            "with `code_graph_community`."
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------- #
# Per-area AGENTS.md stub scaffolding (1p5xc).
#
# Opt-in (a CLI flag, NOT run on every index build). Idempotent: NEVER overwrites
# an existing AGENTS.md, NEVER auto-authors conventions. A stub is just the slot:
# area name + key files + a "fill in conventions/gotchas here" placeholder + a
# pointer back to the codebase map. Humans author the actual content.
# --------------------------------------------------------------------------- #
def _render_area_stub(area: CodebaseArea, *, last_verified: str | None = None) -> str:
    lv = last_verified or _today()
    lines: list[str] = []
    lines.append(f"# {area.name} — area context")
    lines.append("")
    lines.append("Owner: Engineering")
    lines.append("Status: stub")
    lines.append(f"Last verified: {lv}")
    lines.append("")
    lines.append(
        "<!-- Scaffolded stub by .wavefoundry/framework/scripts/gen_codebase_map.py "
        "(1p5xc). This is a placeholder slot — fill in real conventions below. The "
        "framework never auto-authors this content and never overwrites it. -->"
    )
    lines.append("")
    lines.append(
        "Vendor-neutral per-area context for this part of the codebase. Any agent "
        "should consult this file before working in this area."
    )
    lines.append("")
    lines.append(f"- Path: `{area.representative_path}`")
    if area.key_files:
        files = ", ".join(f"`{f}`" for f in area.key_files)
        lines.append(f"- Key files: {files}")
    lines.append(
        "- Codebase map: [docs/references/codebase-map.md]"
        "(../docs/references/codebase-map.md) — orient here, then drill in with "
        "the `code_*` tools."
    )
    lines.append("")
    lines.append("## Conventions and gotchas")
    lines.append("")
    lines.append(
        "_Fill in conventions, gotchas, and local intent for this area here "
        "(libraries it depends on, invariants to preserve, sharp edges). "
        "Human-authored — the framework will not overwrite this section._"
    )
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def scaffold_area_contexts(
    root: Path,
    layer: str = DEFAULT_LAYER,
    *,
    last_verified: str | None = None,
    model: CodebaseMapModel | None = None,
) -> list[str]:
    """Scaffold stub ``AGENTS.md`` files for the major areas (1p5xc).

    Major areas only = the bounded top tier returned by ``compute_areas`` (which
    is already capped at ``MAX_TOP_AREAS``; naturally few/none in a small repo).

    Idempotent + safe:
      * never overwrites an existing ``AGENTS.md`` (human or framework authored);
      * only ever writes a stub, never authored conventions;
      * returns the list of relative paths actually created (empty when all
        present, or when no areas).
    """
    root = Path(root)
    if model is None:
        model = compute_areas(root, layer)
    created: list[str] = []
    if not model.present:
        return created
    for area in model.areas:
        rel = _area_context_rel_path(area)
        dest = root / rel
        if dest.is_file():
            continue  # NEVER overwrite
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_render_area_stub(area, last_verified=last_verified), encoding="utf-8")
        created.append(rel)
    return created


# --------------------------------------------------------------------------- #
# Generate + write (fail-safe entry points).
# --------------------------------------------------------------------------- #
def output_path(root: Path) -> Path:
    return Path(root) / OUTPUT_REL_PATH


_LAST_VERIFIED_RE = "Last verified:"


def _strip_date_line(text: str) -> str:
    """Drop the volatile ``Last verified:`` line so content can be compared
    independently of the date (idempotence — req 6, change-only writes)."""
    return "\n".join(
        ln for ln in text.splitlines() if not ln.startswith(_LAST_VERIFIED_RE)
    )


def _existing_last_verified(text: str) -> str | None:
    for ln in text.splitlines():
        if ln.startswith(_LAST_VERIFIED_RE):
            return ln[len(_LAST_VERIFIED_RE):].strip() or None
    return None


def _fingerprint_inputs(root: Path, layer: str, model: CodebaseMapModel) -> str:
    """A cheap content fingerprint over the generator's inputs (req 6).

    Covers the graph + cluster artifacts AND each area's ``AGENTS.md`` (a Tier-2
    input — renaming an area must trigger an update). Used to skip the render
    entirely when nothing relevant changed. Fail-safe: any error yields a unique
    sentinel so the guard simply doesn't skip.
    """
    import hashlib

    h = hashlib.sha256()
    try:
        graph_file, cluster_file = _graph_paths(Path(root), layer)
        for p in (graph_file, cluster_file):
            try:
                st = p.stat()
                h.update(f"{p.name}:{st.st_size}:{int(st.st_mtime_ns)}".encode())
            except OSError:
                h.update(f"{p.name}:absent".encode())
        # Per-area AGENTS.md content (Tier-2 carry-forward input). Hash the
        # actually-linked file (nearest ancestor, 1p66d) so an edit to a
        # project-root AGENTS.md re-renders the areas that link it.
        for area in model.areas:
            ctx_rel = _resolve_area_context_rel_path(Path(root), area)
            if ctx_rel is None:
                h.update(b"\0")
                continue
            try:
                h.update((Path(root) / ctx_rel).read_bytes())
            except OSError:
                h.update(b"\0")
        return h.hexdigest()
    except Exception:
        import os as _os

        return _os.urandom(16).hex()


def _fingerprint_path(root: Path) -> Path:
    return Path(root) / ".wavefoundry" / "index" / "graph" / ".codebase-map.fingerprint"


def generate_codebase_map(
    root: Path,
    layer: str = DEFAULT_LAYER,
    *,
    last_verified: str | None = None,
    force: bool = False,
) -> str:
    """Compute + render + write the map. Returns the rendered markdown.

    Change-only / idempotent (req 6): a regeneration with unchanged inputs writes
    nothing — no file write, no ``Last verified`` bump, no git churn.

      (a) **Skip the render** when the input fingerprint (graph + cluster +
          per-area ``AGENTS.md``) is unchanged since the last generation.
      (b) **Skip the write** when the rendered content (ignoring the volatile
          ``Last verified`` date line) matches the existing file — preserving the
          existing date.

    ``force=True`` bypasses both guards (used by tests / explicit refreshes).
    """
    model = compute_areas(root, layer)
    out = output_path(root)
    fp_path = _fingerprint_path(root)
    fingerprint = _fingerprint_inputs(Path(root), layer, model)

    # (a) Input fingerprint unchanged AND the map already exists → true no-op.
    if not force and out.is_file():
        try:
            prior_fp = fp_path.read_text(encoding="utf-8").strip()
        except OSError:
            prior_fp = ""
        if prior_fp and prior_fp == fingerprint:
            try:
                _refresh_repo_index_modules(root, model)
            except Exception:
                pass
            return out.read_text(encoding="utf-8")

    # Preserve the existing date when the structural content is unchanged.
    existing_text = ""
    if out.is_file():
        try:
            existing_text = out.read_text(encoding="utf-8")
        except OSError:
            existing_text = ""

    render_lv = last_verified
    if render_lv is None and existing_text:
        # Render with the existing date first; only bump it if content changed.
        render_lv = _existing_last_verified(existing_text)
    markdown = render_markdown(model, last_verified=render_lv, root=root)

    # (b) Content (modulo date) unchanged → skip the write, preserve the date.
    if not force and existing_text and _strip_date_line(existing_text) == _strip_date_line(markdown):
        # Still record the (unchanged) fingerprint so the cheap guard short-
        # circuits next time, and refresh the repo-index block (its own guard).
        try:
            fp_path.parent.mkdir(parents=True, exist_ok=True)
            fp_path.write_text(fingerprint, encoding="utf-8")
        except OSError:
            pass
        try:
            _refresh_repo_index_modules(root, model)
        except Exception:
            pass
        return existing_text

    # Content changed (or first generation): bump the date when not pinned.
    if last_verified is None:
        markdown = render_markdown(model, last_verified=_today(), root=root)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markdown, encoding="utf-8")
    try:
        fp_path.parent.mkdir(parents=True, exist_ok=True)
        fp_path.write_text(fingerprint, encoding="utf-8")
    except OSError:
        pass
    try:
        _refresh_repo_index_modules(root, model)
    except Exception:
        pass
    return markdown


# --------------------------------------------------------------------------- #
# Option A (req 6): refresh the marker-delimited structural block in
# docs/repo-index.md from the area model. The human/agent narrative OUTSIDE the
# markers is never touched. Idempotent + fail-safe: only rewritten when the
# structural content actually changes; a missing file or missing markers is a
# safe no-op (never creates/corrupts the narrative).
# --------------------------------------------------------------------------- #
def _render_repo_index_modules(model: CodebaseMapModel) -> str:
    """The structural module table for the repo-index marker block."""
    lines: list[str] = []
    lines.append("")
    lines.append(
        "<!-- Generated from the codebase map "
        "(.wavefoundry/framework/scripts/gen_codebase_map.py). The narrative "
        "outside these markers is human/agent-authored and never touched. -->"
    )
    lines.append("")
    if not model.present or not model.areas:
        lines.append("_No structural areas available yet (build the index)._")
        lines.append("")
        return "\n".join(lines)
    lines.append("| Area | Path | Kind | Size (nodes) |")
    lines.append("| ---- | ---- | ---- | ------------ |")
    for area in model.areas:
        kind = "config" if area.is_config else "code"
        name = area.name.replace("|", "\\|")
        lines.append(
            f"| {name} | `{area.representative_path}` | {kind} | {area.node_count} |"
        )
    lines.append("")
    return "\n".join(lines)


def _refresh_repo_index_modules(root: Path, model: CodebaseMapModel) -> bool:
    """Refresh the marker block in docs/repo-index.md. Returns True if written.

    Fail-safe: only operates when the file exists AND both markers are present;
    rewrites only when the structural block content actually changes.
    """
    path = Path(root) / REPO_INDEX_REL_PATH
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    begin = text.find(REPO_INDEX_MARKER_BEGIN)
    end = text.find(REPO_INDEX_MARKER_END)
    if begin == -1 or end == -1 or end < begin:
        return False
    inner_start = begin + len(REPO_INDEX_MARKER_BEGIN)
    new_inner = _render_repo_index_modules(model)
    if text[inner_start:end] == new_inner:
        return False  # change-only: no structural change → no write
    new_text = text[:inner_start] + new_inner + text[end:]
    try:
        path.write_text(new_text, encoding="utf-8")
    except OSError:
        return False
    return True


def generate_safe(
    root: Path, layer: str = DEFAULT_LAYER, *, verbose: bool = False, force: bool = False
) -> bool:
    """Fail-safe wrapper for the index-build lifecycle.

    A generator error must NEVER fail the index build, so all exceptions are
    swallowed (logged when ``verbose``). Returns True on success. Change-only by
    default (see ``generate_codebase_map``): an unchanged codebase is a no-op.
    """
    try:
        generate_codebase_map(root, layer, force=force)
        if verbose:
            print(
                f"build_index: codebase map regenerated → {OUTPUT_REL_PATH}",
                flush=True,
            )
        return True
    except Exception as exc:  # noqa: BLE001 — fail-safe by contract
        if verbose:
            print(
                f"build_index: codebase map generation skipped ({exc})",
                file=sys.stderr,
                flush=True,
            )
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the project codebase map")
    parser.add_argument("--root", default=".", help="Repository root (default: current directory)")
    parser.add_argument("--layer", default=DEFAULT_LAYER, help="Graph layer (default: project)")
    parser.add_argument(
        "--print", action="store_true", help="Print the rendered map to stdout instead of writing"
    )
    parser.add_argument(
        "--scaffold-area-contexts",
        action="store_true",
        help=(
            "Opt-in: scaffold a stub AGENTS.md for each major area (idempotent; "
            "never overwrites or auto-authors). Not run on the index build."
        ),
    )
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if args.scaffold_area_contexts:
        created = scaffold_area_contexts(root, args.layer)
        if created:
            for rel in created:
                print(f"scaffolded area context → {rel}")
        else:
            print("no area contexts scaffolded (all present or no areas)")
        return 0
    if args.print:
        model = compute_areas(root, args.layer)
        sys.stdout.write(render_markdown(model, root=root))
        return 0
    generate_codebase_map(root, args.layer)
    print(f"codebase map written → {output_path(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

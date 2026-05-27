#!/usr/bin/env python3
"""Wavefoundry MCP server implementation — reloadable via server.py runner."""
from __future__ import annotations

import argparse
import ast
import contextlib
import datetime
import functools
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

sys.dont_write_bytecode = True

FASTEMBED_CACHE_DEFAULT = Path.home() / ".wavefoundry" / "cache" / "fastembed"
if not os.environ.get("FASTEMBED_CACHE_PATH"):
    os.environ["FASTEMBED_CACHE_PATH"] = str(FASTEMBED_CACHE_DEFAULT)

DASHBOARD_START_WAIT_SECONDS = 5.0


def _wf_log(message: str) -> None:
    """Operator diagnostics — stderr only; stdio MCP transport owns stdout."""
    print(message, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Root discovery (mirrors lifecycle_id.py pattern)
# ---------------------------------------------------------------------------

def _discover_root(override: Optional[str] = None) -> Path:
    """Walk up from CWD to find the repo root anchored by ``workflow-config.json``.

    Intentional differences from the copies in other scripts:
    - Accepts an explicit ``override`` path (used when ``--root`` is passed on
      the CLI or via MCP tool arguments).
    - Checks both ``PROJECT_ROOT`` and ``REPO_ROOT`` env vars.
    - Never returns ``None`` — falls back to CWD when no anchor is found.

    Cross-reference: ``indexer._discover_root``, ``lifecycle_id.discover_repo_root``,
    ``render_platform_surfaces.discover_repo_root``, ``docs_gardener.project_root``.
    A future consolidation task should unify these into a shared utility.
    """
    if override:
        return Path(override).expanduser().resolve()
    for env_key in ("PROJECT_ROOT", "REPO_ROOT"):
        raw = os.environ.get(env_key)
        if raw:
            candidate = Path(raw).expanduser().resolve()
            if (candidate / "docs" / "workflow-config.json").is_file():
                return candidate
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / "docs" / "workflow-config.json").is_file():
            return candidate
    return cwd


def _tool_venv_base() -> Path:
    """Return the configured shared Wavefoundry tool-venv base path."""
    return Path(os.environ.get("WAVEFOUNDRY_TOOL_VENV", "~/.wavefoundry/venv")).expanduser()


def _preferred_python() -> str:
    """Return the shared tool-venv Python when present, else the current interpreter."""
    venv_python = _tool_venv_base() / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(venv_python) if venv_python.exists() else sys.executable


# ---------------------------------------------------------------------------
# Index loader
# ---------------------------------------------------------------------------

class IndexNotReadyError(Exception):
    pass


class SemanticModelUnavailableOfflineError(IndexNotReadyError):
    pass


TRUSTED_FRAMEWORK = "trusted_framework"
TRUSTED_PROJECT_METADATA = "trusted_project_metadata"
UNTRUSTED_PROJECT_CONTENT = "untrusted_project_content"
VALID_CHANGE_KINDS = {"bug", "feat", "enh", "change", "doc", "debt", "ref", "task", "maint", "ops"}
MCP_TOOL_PREFIXES = ("wave_", "docs_", "code_", "seed_")
DOCS_SEARCH_KINDS = frozenset({"doc", "seed", "architecture", "prompt", "doc-summary"})
VECTOR_TOP_K = 30  # candidates fetched per index before reranking (navigational/instructional/default)
VECTOR_TOP_K_EXPLANATORY = 50  # candidates per index for explanatory/flow questions (dynamic-vector-top-k)

# LanceDB vector index constants (must match indexer.py)
# Tables live directly in the index directory: index_dir/docs.lance/, index_dir/code.lance/
LANCEDB_NPROBES = 20        # ANN search probes (recall vs latency)
LANCEDB_REFINE_FACTOR = 10  # reranking candidates multiplier

# RRF source-weight bias applied when question_type == "navigational" (question-type-aware-retrieval)
RRF_NAVIGATIONAL_CODE_WEIGHT = 1.5
RRF_NAVIGATIONAL_DOCS_WEIGHT = 1.0

# Path segments that identify scaffolding/wiring layers across framework families.
# Citations from these layers confirm a connection exists but do not contain business logic.
# Cloud IaC: CDK, Terraform — Node/TS: Express, NestJS — JVM: Spring — generic infra labels.
INFRASTRUCTURE_PATH_SEGMENTS: frozenset = frozenset({
    "constructs", "stacks", "api-gateways",          # CDK
    "infra", "infrastructure", "cdk",                 # CDK / generic IaC
    "modules", "resources", "providers",              # Terraform
    "config", "beans",                                # Spring
    "routes", "wiring",                               # Express / NestJS
    "scaffolding",                                    # generic
})

# Demotion weights for narrative/feedback sources in code_ask explanatory queries.
# Applied to post-rerank cross-encoder scores; see _demote_doc_results.
# Calibrated 2026-05-18 against live query data (change 12q5v).
_DEMOTION_WAVES = 0.75  # docs/waves/ — historical change docs
_DEMOTION_PLANS = 0.60  # docs/plans/ — pre-admission drafts
_DEMOTION_SEEDS = 0.60  # kind=seed or .wavefoundry/framework/seeds/ — framework guidance
_DEMOTION_JRNLS = 0.50  # journals/reports/feedback — observational notes
# Post-normalization score boost for symbol-injected code chunks (12q63).
_SYMBOL_INJECTION_BOOST = 0.40
# Definition-file boosting: vocabulary-triggered keyword augmentation for schema languages.
# Each rule fires when any vocabulary term appears in the lowercased query.
# Injected candidates receive score=0.0 so the reranker evaluates them on content merit only.
# Add new rules (GraphQL, protobuf, OpenAPI) by appending to this list — no logic changes required.
DEFINITION_BOOST_RULES: list[dict] = [
    {
        "vocabulary": frozenset({
            "sql", "stored procedure", "proc", "migration", "schema",
            "insert", "query", "database", "db", "routine",
            "table", "column",
        }),
        "extensions": [".sql"],
        "label": "sql",
    },
]
DEFINITION_BOOST_CANDIDATES = 5   # maximum candidates injected per rule per query
MAX_SYMBOLS_EXTRACTED = 5         # maximum symbol names extracted from first-hop citations
MAX_SECOND_HOP_CANDIDATES = 10    # maximum total candidates injected via second hop

# Tree-sitter node types used during symbol extraction
_TS_CALL_TYPES = frozenset({
    "call", "call_expression", "method_invocation",
    "invocation_expression", "function_call",
})
_TS_IDENTIFIER_TYPES = frozenset({
    "identifier", "name", "simple_name", "property_identifier",
    "type_identifier",  # TypeScript class/interface/type names
})
_TS_MEMBER_TYPES = frozenset({
    "attribute", "member_expression",
    "member_access_expression", "field_access",
})
# Node types used by code_outline to identify class/struct definitions
_TS_OUTLINE_CLASS_TYPES = frozenset({
    "class_declaration", "class_definition", "class_specifier",
    "interface_declaration", "interface_definition",
    "struct_item", "struct_specifier", "struct_declaration",
    "impl_item", "trait_item", "trait_definition",
    "object_declaration", "type_declaration",
})
# Node types used by code_outline to identify function/method definitions
_TS_OUTLINE_FUNC_TYPES = frozenset({
    "function_declaration", "function_definition", "function_item",
    "function_expression", "arrow_function",
    "method_declaration", "method_definition", "method_item",
    "constructor_declaration", "constructor_definition",
    # SQL: confirmed via tree-sitter-sql grammar parse tree inspection
    "create_function",
})
# Languages mapped to the tree-sitter lang key used by the chunker
_TS_SYMBOL_LANG_MAP: dict[str, str] = {
    "javascript": "javascript",
    "typescript": "typescript",
    "java": "java",
    "csharp": "csharp",
    "go": "go",
    "rust": "rust",
    "c": "c",
    "cpp": "cpp",
    "kotlin": "kotlin",
    "bash": "bash",
    "sql": "sql",
}
# Common built-in names filtered out of symbol extraction results
_SYMBOL_BLOCKLIST = frozenset({
    "get", "set", "run", "init", "main", "self", "this", "true", "false",
    "null", "new", "return", "create", "update", "delete", "list", "find",
    "print", "none", "super", "async", "await", "with", "open", "next",
    "type", "repr", "hash", "iter", "copy", "bool", "dict", "join",
})

# Regex patterns for symbol extraction fallback
_RE_CALL = re.compile(r'\b([A-Za-z_][A-Za-z0-9_]{3,})\s*\(')
_RE_SQL_EXEC = re.compile(
    r'\b(?:EXEC|EXECUTE|CALL)\s+([A-Za-z_][A-Za-z0-9_.]{3,})\b', re.IGNORECASE
)
_RE_IMPORT = re.compile(r'\bimport\s+([A-Za-z_][A-Za-z0-9_]{3,})')

_PROMPT_MISS = object()
"""Sentinel used by ``McpRepoCache.get_prompt_text_cached`` to cache a None
result (i.e. prompt not found) without storing Python ``None``, which cannot
be distinguished from a cache miss. Compared with ``is``, so it must be a
module-level singleton. If ``server.py`` is ever re-executed in the same
process, a new object will be created and old cache entries will be treated as
misses — acceptable because the cache is process-scoped."""
BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS = 15.0
# How long a .build.lock directory is trusted before being considered stale.
# Both this value and indexer.LOCK_STALE_SECONDS encode "max time a build can run
# before its lock is declared stale." Change them together if that assumption changes.
BACKGROUND_INDEX_LOCK_STALE_SECONDS = 60 * 60


def _index_layer_readiness(layer: dict[str, Any]) -> str:
    """Per-layer index state for operators (missing / stale / current / idle)."""
    has_sources = bool(layer.get("has_sources"))
    meta_present = bool(layer.get("meta_present"))
    docs_present = bool(layer.get("docs_present"))
    stale_paths = layer.get("stale_paths") or []
    if has_sources and (not meta_present or not docs_present):
        return "missing"
    if stale_paths:
        return "stale"
    if meta_present and docs_present:
        return "current"
    return "idle"


def _index_readiness_overview(
    missing_layers: list[str],
    stale_layers: list[str],
    compatible_chunks: bool,
    has_any_index: bool,
) -> str:
    """Aggregate readiness: incomplete, needs_update, degraded, absent, or ready."""
    if missing_layers:
        return "incomplete"
    if stale_layers:
        return "needs_update"
    if has_any_index and not compatible_chunks:
        return "degraded"
    if not has_any_index:
        return "absent"
    return "ready"


@contextlib.contextmanager
def _offline_model_env():
    """Module-level context manager: sets HF_HUB_OFFLINE=1 and restores on exit."""
    prior = os.environ.get("HF_HUB_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    try:
        yield
    finally:
        if prior is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = prior


def _ensure_model_cached(model_name: str, model_type: str) -> None:
    """Download model files to cache without loading into server working memory.

    The instantiated model object is immediately discarded — this function's
    sole purpose is to populate the on-disk cache so subsequent _get_embedder()
    or _get_reranker() calls succeed offline.
    """
    import os

    if model_type == "reranker":
        try:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
        except ImportError:
            _wf_log(f"[wavefoundry] fastembed.rerank not available; skipping {model_name}")
            return

        # Check if already cached (offline probe)
        try:
            with _offline_model_env():
                try:
                    TextCrossEncoder(model_name=model_name, local_files_only=True)
                except TypeError:
                    TextCrossEncoder(model_name=model_name)
            _wf_log(f"[wavefoundry] Reranker already cached: {model_name}")
            return
        except Exception:
            pass

        # Not cached — download (object is discarded after)
        try:
            TextCrossEncoder(model_name=model_name, local_files_only=False)
        except TypeError:
            TextCrossEncoder(model_name=model_name)
        _wf_log(f"[wavefoundry] Model cached: {model_name}")

    else:  # embedding
        from fastembed import TextEmbedding

        # Check if already cached (offline probe)
        try:
            with _offline_model_env():
                try:
                    TextEmbedding(model_name=model_name, local_files_only=True)
                except TypeError:
                    TextEmbedding(model_name=model_name)
            _wf_log(f"[wavefoundry] Embedding model already cached: {model_name}")
            return
        except Exception:
            pass

        # Not cached — download (object discarded)
        try:
            TextEmbedding(model_name=model_name, local_files_only=False)
        except TypeError:
            TextEmbedding(model_name=model_name)
        _wf_log(f"[wavefoundry] Model cached: {model_name}")


class WaveIndex:
    """Loaded in-memory index for semantic search."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.index_dir = root / ".wavefoundry" / "index"
        self.framework_index_dir = root / ".wavefoundry" / "framework" / "index"
        self._docs_lance_table = None   # LanceDB Table object for docs, None if not loaded
        self._code_lance_table = None   # LanceDB Table object for code, None if not loaded
        self._reranker = None
        self._model_downloads_started: bool = False
        self._meta: dict = {}
        self._loaded = False
        self._loaded_meta_signature: dict[str, tuple[int, int] | None] = {}
        self._lance_available: set[tuple[str, str]] = set()

    def _open_lance_table(self, layer: str, kind: str):
        """Open a LanceDB table fresh on every call — never returns a stale handle."""
        available = getattr(self, "_lance_available", None)
        if available is not None and (layer, kind) not in available:
            return None
        index_dir = getattr(self, "index_dir", None) if layer == "project" else getattr(self, "framework_index_dir", None)
        if index_dir is None:
            return object() if available and (layer, kind) in available else None
        table_path = index_dir / f"{kind}.lance"
        if not table_path.is_dir():
            return object() if available and (layer, kind) in available else None
        try:
            import lancedb
            db = lancedb.connect(str(index_dir))
            return db.open_table(kind)
        except Exception:
            return None

    @staticmethod
    def _fts_query(query: str) -> str:
        stripped = query.strip()
        if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in ('"', "'", "`"):
            inner = stripped[1:-1]
        else:
            inner = stripped
        if inner and re.search(r"\w", inner) and re.fullmatch(r"[\w._]+", inner):
            return f'"{inner}"'
        return query

    def _lance_fts_search(self, table, query: str, top_n: int, where: Optional[str] = None, layer: str = "project") -> list[dict]:
        fts_q = self._fts_query(query)
        try:
            q = table.search(fts_q, query_type="fts").limit(top_n)
            if where:
                q = q.where(where, prefilter=True)
            results = q.to_list()
        except Exception:
            return []
        out = []
        for r in results:
            d = dict(r)
            score = d.pop("_score", None)
            d.pop("vector", None)
            d["path"] = self._qualify_index_path(d.get("path", ""), layer)
            d["score"] = float(score) if score is not None else 0.0
            out.append(d)
        return out

    def _indexer_module(self):
        return _load_script("indexer")

    def _layer_current_hashes(self, layer: str) -> dict[str, str]:
        idx = self._indexer_module()
        # Framework index builds use ``--no-ignore-files`` (see ``run_index_rebuild``); match
        # that walk so ``meta.json`` ``file_hashes`` keys align with health checks.
        files = idx.walk_repo(self.root, respect_ignore=layer == "project")
        index_dir = self.index_dir if layer == "project" else self.framework_index_dir
        files = [path for path in files if not idx._is_relative_to(path, index_dir)]
        if layer == "project":
            files = idx._filter_project_index_excludes(files, self.root, ())
        else:
            files = idx._filter_by_prefixes(files, self.root, (".wavefoundry/framework/",))
            files = idx._filter_framework_pack_artifacts(files, self.root)
        return idx._build_file_hashes(files, self.root)

    def _layer_health(self, layer: str) -> dict[str, Any]:
        """Compute health metadata for one index layer (``'project'`` or ``'framework'``).

        Walks the repo and hashes every indexed file, then compares the result
        against the hashes stored in ``meta.json``.  Paths where the digest
        differs (or that are present in one set but not the other) are reported
        as ``stale_paths``.  This is an O(total-indexed-bytes) operation — call
        it only via the explicit ``wave_index_health`` MCP tool, never on the
        search hot path.
        """
        index_dir = self.index_dir if layer == "project" else self.framework_index_dir
        meta_path = index_dir / "meta.json"
        docs_lance_path = index_dir / "docs.lance"
        meta = self._meta.get(layer) if self._loaded else {}
        if not isinstance(meta, dict):
            meta = {}
        current_hashes = self._layer_current_hashes(layer)
        # Indexer writes file_meta (hash + mtime + size + inode per file); health checker
        # extracts just the hash for comparison.  Fall back to legacy file_hashes key.
        raw_file_meta = meta.get("file_meta", {})
        if isinstance(raw_file_meta, dict) and raw_file_meta:
            old_hashes = {
                path: entry["hash"]
                for path, entry in raw_file_meta.items()
                if isinstance(entry, dict) and "hash" in entry
            }
        else:
            raw_file_hashes = meta.get("file_hashes", {})
            old_hashes = raw_file_hashes if isinstance(raw_file_hashes, dict) else {}
        modified_paths = sorted(
            path for path, digest in current_hashes.items()
            if path in old_hashes and old_hashes[path] != digest
        )
        added_paths = sorted(
            path for path in current_hashes
            if path not in old_hashes
        )
        removed_paths = sorted(
            path for path in old_hashes
            if path not in current_hashes
        )
        stale_paths = sorted(set(modified_paths) | set(added_paths) | set(removed_paths))
        docs_present = docs_lance_path.is_dir()
        meta_present = meta_path.exists()
        raw_chunker_versions = meta.get("chunker_versions", {})
        indexed_chunker_versions: dict[str, str] = (
            raw_chunker_versions if isinstance(raw_chunker_versions, dict) else {}
        )
        current_chunker_version: str = _read_chunker_version()
        return {
            "layer": layer,
            "index_dir": str(index_dir),
            "meta_present": meta_present,
            "docs_present": docs_present,
            "has_sources": bool(current_hashes),
            "stale_paths": stale_paths,
            "stale_paths_count": len(stale_paths),
            "modified_paths_count": len(modified_paths),
            "added_paths_count": len(added_paths),
            "removed_paths_count": len(removed_paths),
            "current_hash_count": len(current_hashes),
            "indexed_chunker_versions": indexed_chunker_versions,
            "current_chunker_version": current_chunker_version,
        }

    def docs_health(self) -> dict[str, Any]:
        self._ensure_loaded()
        project = self._layer_health("project")
        framework = self._layer_health("framework")
        project["readiness"] = _index_layer_readiness(project)
        framework["readiness"] = _index_layer_readiness(framework)
        compatible_chunks = (
            getattr(self, "_docs_lance_table", None) is not None
            or getattr(self, "_code_lance_table", None) is not None
        )
        has_any_index = project["meta_present"] or framework["meta_present"]
        stale_layers = [layer["layer"] for layer in (project, framework) if layer["stale_paths"]]
        missing_layers = [
            layer["layer"]
            for layer in (project, framework)
            if layer["has_sources"] and (not layer["meta_present"] or not layer["docs_present"])
        ]
        readiness_overview = _index_readiness_overview(
            missing_layers, stale_layers, compatible_chunks, has_any_index
        )
        # Detect chunker version mismatch: index was built with an older CHUNKER_VERSION.
        # Fires even when file hashes are current (e.g. after a pack upgrade before rebuild).
        chunker_version_mismatch_layers: list[str] = []
        for layer_health in (project, framework):
            current_cv = layer_health.get("current_chunker_version", "")
            indexed_cvs = layer_health.get("indexed_chunker_versions", {})
            if not current_cv or not layer_health.get("meta_present"):
                continue
            if isinstance(indexed_cvs, dict) and any(
                v != current_cv for v in indexed_cvs.values() if v
            ):
                chunker_version_mismatch_layers.append(layer_health["layer"])
        return {
            "project": project,
            "framework": framework,
            "has_any_index": has_any_index,
            "stale_layers": stale_layers,
            "missing_layers": missing_layers,
            "compatible_chunks": compatible_chunks,
            "readiness_overview": readiness_overview,
            "semantic_ready": has_any_index and not stale_layers and compatible_chunks,
            "chunker_version_mismatch_layers": chunker_version_mismatch_layers,
        }

    @contextlib.contextmanager
    def _offline_model_env(self):
        with _offline_model_env():
            yield

    def _live_docs_chunks(self) -> list[dict[str, Any]]:
        """Walk the repo and chunk all doc files on the fly (no index required).

        Used as a lexical-fallback data source when the semantic index is
        unavailable or not yet built.  Does a full filesystem walk on every
        call — not suitable for the search hot path in large repos.  Results
        are not cached here; callers should cache if repeated fallback queries
        are expected.
        """
        idx = self._indexer_module()
        files = idx.walk_repo(self.root, respect_ignore=True)
        files = [path for path in files if not idx._is_relative_to(path, self.index_dir)]
        files = [path for path in files if not idx._is_relative_to(path, self.framework_index_dir)]

        chunks: list[dict[str, Any]] = []
        seen_paths: set[str] = set()
        for path in files:
            rel = str(path.relative_to(self.root)).replace("\\", "/")
            if rel.startswith(".wavefoundry/framework/"):
                if not rel.endswith(".md") and not rel.endswith(".json"):
                    continue
            elif not rel.startswith("docs/"):
                continue
            if rel in seen_paths:
                continue
            seen_paths.add(rel)
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            doc_chunks, _ = idx._chunks_for_file(rel, content)
            chunks.extend(doc_chunks)
        return chunks

    def _lexical_score(self, query: str, chunk: dict[str, Any]) -> float:
        terms = re.findall(r"[a-z0-9]+", query.lower())
        if not terms:
            return 0.0
        haystack = " ".join(
            str(chunk.get(field) or "")
            for field in ("path", "section", "text", "kind")
        ).lower()
        score = 0.0
        unique_terms = set(terms)
        for term in unique_terms:
            count = haystack.count(term)
            if count:
                score += 1.0 + min(count, 5) * 0.25
                if str(chunk.get("path") or "").lower().endswith(f"{term}.md"):
                    score += 0.5
        return score

    def _doc_matches_kind(self, chunk: dict[str, Any], kind: Optional[str]) -> bool:
        if not kind:
            return True
        chunk_kind = str(chunk.get("kind") or "")
        normalized_path = str(chunk.get("path") or "").replace("\\", "/")
        if kind == "seed":
            return chunk_kind == "seed"
        if kind == "prompt":
            return chunk_kind == "prompt"
        if kind == "doc-summary":
            return chunk_kind == "doc-summary"
        if chunk_kind != "doc":
            return False
        if kind == "doc":
            return True
        if kind == "architecture":
            return normalized_path == "docs/ARCHITECTURE.md" or normalized_path.startswith("docs/architecture/")
        return chunk_kind == kind

    def search_docs_lexical(self, query: str, kind: Optional[str] = None, top_n: int = 5) -> list[dict]:
        chunks = self._live_docs_chunks()
        if kind:
            chunks = [chunk for chunk in chunks if self._doc_matches_kind(chunk, kind)]
        ranked = []
        for chunk in chunks:
            score = self._lexical_score(query, chunk)
            if score <= 0:
                continue
            ranked.append({**chunk, "score": score})
        ranked.sort(key=lambda chunk: (-float(chunk["score"]), str(chunk.get("path") or ""), str(chunk.get("section") or "")))
        return ranked[:top_n]

    def _index_meta_signature(self, index_dir: Path) -> tuple[int, int] | None:
        meta_path = index_dir / "meta.json"
        try:
            st = meta_path.stat()
        except OSError:
            return None
        return (int(getattr(st, "st_mtime_ns", 0) or 0), int(getattr(st, "st_size", 0) or 0))

    def _ensure_loaded(self) -> None:
        if self._loaded:
            # Invalidate if either index has been rebuilt since we last loaded.
            project_signature = self._index_meta_signature(self.index_dir)
            framework_signature = self._index_meta_signature(self.framework_index_dir)
            if (project_signature != self._loaded_meta_signature.get("project")
                    or framework_signature != self._loaded_meta_signature.get("framework")):
                self._loaded = False
        if self._loaded:
            return

        if not (self.index_dir / "meta.json").exists() and not (self.framework_index_dir / "meta.json").exists():
            raise IndexNotReadyError(
                f"Index not found at {self.index_dir} or {self.framework_index_dir}. "
                "Run: python3 .wavefoundry/framework/scripts/setup_wavefoundry.py"
            )

        def _load_lance_table(index_dir: Path, table_name: str):
            """Return an open LanceDB Table, or None if the table directory is absent."""
            table_path = index_dir / f"{table_name}.lance"
            if not table_path.is_dir():
                return None
            try:
                import lancedb
                db = lancedb.connect(str(index_dir))
                return db.open_table(table_name)
            except ImportError:
                print(
                    "[wavefoundry] LanceDB index found but lancedb is not installed — "
                    "run: python3 .wavefoundry/framework/scripts/setup_wavefoundry.py",
                    file=sys.stderr,
                )
                return None
            except Exception:
                return None

        proj_docs_table = _load_lance_table(self.index_dir, "docs")
        proj_code_table = _load_lance_table(self.index_dir, "code")
        fw_docs_table = _load_lance_table(self.framework_index_dir, "docs")
        fw_code_table = _load_lance_table(self.framework_index_dir, "code")

        if not any(t is not None for t in (proj_docs_table, proj_code_table, fw_docs_table, fw_code_table)):
            raise IndexNotReadyError(
                "[wavefoundry] No index found. "
                "Run: python3 .wavefoundry/framework/scripts/setup_wavefoundry.py"
            )

        self._docs_lance_table = proj_docs_table or fw_docs_table
        self._code_lance_table = proj_code_table or fw_code_table
        self._proj_docs_lance_table = proj_docs_table
        self._proj_code_lance_table = proj_code_table
        self._fw_docs_lance_table = fw_docs_table
        self._fw_code_lance_table = fw_code_table
        self._lance_available = set()
        for layer_id, idx_dir in (("project", self.index_dir), ("framework", self.framework_index_dir)):
            for kind in ("docs", "code"):
                if (idx_dir / f"{kind}.lance").is_dir():
                    self._lance_available.add((layer_id, kind))

        def _load_meta_only(index_dir: Path) -> dict:
            meta_path = index_dir / "meta.json"
            if meta_path.exists():
                try:
                    return json.loads(meta_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    return {}
            return {}

        self._meta = {
            "project": _load_meta_only(self.index_dir),
            "framework": _load_meta_only(self.framework_index_dir),
        }
        self._loaded_meta_signature = {
            "project": self._index_meta_signature(self.index_dir),
            "framework": self._index_meta_signature(self.framework_index_dir),
        }
        self._loaded = True

    # ------------------------------------------------------------------
    # Embedding model
    #
    # Current model: BAAI/bge-base-en-v1.5  (768-d float32)
    # Defined in:    indexer.py  DOCS_MODEL / CODE_MODEL constants
    # Upgrade doc:   docs/architecture/embedding-model.md
    #
    # To upgrade the model:
    #   1. Change DOCS_MODEL / CODE_MODEL in indexer.py
    #   2. Update _EXPECTED_DOCS_MODEL / _EXPECTED_EMBEDDING_DIM in
    #      SemanticEmbeddingRegressionTests (test_server_tools.py)
    #   3. Delete .wavefoundry/index/ and rebuild:
        #        python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root . --include-code
    #   4. Run tests — all SemanticEmbeddingRegressionTests must pass
    #
    # Skip/fallback contract:
    #   - fastembed not installed          → IndexNotReadyError
    #   - model not locally cached         → SemanticModelUnavailableOfflineError
    #   - Both are caught by docs_search   → lexical fallback, mode="lexical" in response
    # ------------------------------------------------------------------
    def _get_embedder(self, model_name: str):
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise IndexNotReadyError(
                "fastembed is not installed. Run: python3 .wavefoundry/framework/scripts/setup_wavefoundry.py"
            )
        try:
            with self._offline_model_env():
                return TextEmbedding(model_name=model_name, local_files_only=True)
        except TypeError:
            try:
                with self._offline_model_env():
                    return TextEmbedding(model_name=model_name)
            except Exception as exc:  # pragma: no cover - fallback path
                raise SemanticModelUnavailableOfflineError(
                    f"Semantic query model '{model_name}' is unavailable offline. "
                    "Run: python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root ."
                ) from exc
        except Exception as exc:
            raise SemanticModelUnavailableOfflineError(
                f"Semantic query model '{model_name}' is unavailable offline. "
                "Run: python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root ."
            ) from exc

    def _embed_query(self, text: str, model_name: str) -> "np.ndarray":
        import numpy as np
        embedder = self._get_embedder(model_name)
        try:
            with self._offline_model_env():
                return next(iter(embedder.embed([text])))
        except Exception as exc:
            raise SemanticModelUnavailableOfflineError(
                f"Semantic query model '{model_name}' is unavailable offline. "
                "Run: python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root ."
            ) from exc

    def _get_reranker(self):
        if self._reranker is not None:
            return self._reranker
        try:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
        except ImportError:
            return None
        try:
            RERANKER_MODEL = self._indexer_constant("RERANKER_MODEL")
            with self._offline_model_env():
                reranker = TextCrossEncoder(model_name=RERANKER_MODEL, local_files_only=True)
            self._reranker = reranker
            return self._reranker
        except TypeError:
            try:
                RERANKER_MODEL = self._indexer_constant("RERANKER_MODEL")
                with self._offline_model_env():
                    reranker = TextCrossEncoder(model_name=RERANKER_MODEL)
                self._reranker = reranker
                return self._reranker
            except Exception:
                return None
        except Exception:
            return None

    def _start_background_model_downloads(self) -> None:
        import os
        import threading

        if os.environ.get("HF_HUB_OFFLINE") == "1":
            _wf_log("[wavefoundry] HF_HUB_OFFLINE set; skipping background model download")
            return

        if self._model_downloads_started:
            return
        self._model_downloads_started = True

        def _download_worker() -> None:
            try:
                docs_model = self._indexer_constant("DOCS_MODEL")
                code_model = self._indexer_constant("CODE_MODEL")
                reranker_model = self._indexer_constant("RERANKER_MODEL")
            except Exception as exc:
                _wf_log(f"[wavefoundry] Background model download: could not read model constants: {exc}")
                return

            # Deduplicate
            embedding_models = list(dict.fromkeys([docs_model, code_model]))
            all_models = [("embedding", m) for m in embedding_models] + [("reranker", reranker_model)]

            for model_type, model_name in all_models:
                try:
                    _ensure_model_cached(model_name, model_type)
                except Exception as exc:
                    _wf_log(f"[wavefoundry] Background download failed for {model_name}: {exc}")

        thread = threading.Thread(target=_download_worker, daemon=True, name="wavefoundry-model-download")
        thread.start()

    def _rerank(self, query: str, candidates: list[dict], top_n: int) -> list[dict]:
        reranker = self._get_reranker()
        if not reranker or not candidates:
            return candidates[:top_n]
        try:
            texts = [c.get("text", "") for c in candidates]
            scores = list(reranker.rerank(query, texts))
            min_s = min(scores)
            max_s = max(scores)
            for s, c in zip(scores, candidates):
                c["score"] = 1.0 if max_s == min_s else float((s - min_s) / (max_s - min_s))
            for c in candidates:
                if c.get("_sym_injected") and c.get("kind") == "code":
                    c["score"] = min(c["score"] + _SYMBOL_INJECTION_BOOST, 1.0)
            return sorted(candidates, key=lambda x: x.get("score", 0.0), reverse=True)[:top_n]
        except Exception:
            return candidates[:top_n]

    def _rrf_merge(self, ranked_lists: list[list[dict]], top_n: int, k: int = 60, weights: Optional[list[float]] = None) -> list[dict]:
        """Reciprocal Rank Fusion across ranked_lists.

        ``weights`` is an optional per-list multiplier applied to each RRF term.
        When omitted all lists are weighted equally (weight=1.0).
        """
        scores: dict[str, float] = {}
        chunks_by_id: dict[str, dict] = {}
        for i, ranked in enumerate(ranked_lists):
            if not ranked:
                continue
            w = weights[i] if weights and i < len(weights) else 1.0
            for rank, chunk in enumerate(ranked):
                chunk_id = str(chunk.get("id") or str(chunk.get("path", "")) + str(chunk.get("lines", "")))
                scores[chunk_id] = scores.get(chunk_id, 0.0) + w / (k + rank)
                chunks_by_id[chunk_id] = chunk
        sorted_ids = sorted(scores, key=lambda cid: scores[cid], reverse=True)
        return [chunks_by_id[cid] for cid in sorted_ids[:top_n]]

    def _indexer_constant(self, name: str) -> str:
        mod = _load_script("indexer")
        return getattr(mod, name)

    def _qualify_index_path(self, path: str, layer: str) -> str:
        normalized = str(path or "").replace("\\", "/")
        if layer == "framework" and normalized and not normalized.startswith(".wavefoundry/framework/"):
            return f".wavefoundry/framework/{normalized.lstrip('/')}"
        return normalized

    def _lance_search(self, table, query_vec: "np.ndarray", top_n: int, where: Optional[str] = None, layer: str = "project") -> list[dict]:
        """Search a LanceDB table with cosine metric.

        Returns a list of chunk dicts with a ``score`` field (1 - distance, higher = more similar).
        """
        try:
            q = table.search(query_vec.tolist()).metric("cosine").limit(top_n)
            if where:
                q = q.where(where, prefilter=True)
            results = q.to_list()
        except Exception:
            return []
        out = []
        for r in results:
            d = dict(r)
            score = d.pop("_distance", None)
            d.pop("vector", None)
            d["path"] = self._qualify_index_path(d.get("path", ""), layer)
            if score is not None:
                # LanceDB cosine distance = 1 - cosine_similarity; convert to similarity
                d["score"] = float(1.0 - score)
            else:
                d["score"] = 0.0
            out.append(d)
        return out

    def search_docs(self, query: str, kind: Optional[str] = None, top_n: int = 7, tags: Optional[list] = None) -> tuple[list[dict], bool]:
        self._ensure_loaded()
        DOCS_MODEL = self._indexer_constant("DOCS_MODEL")
        qvec = self._embed_query(query, DOCS_MODEL)

        where_parts = []
        if kind:
            safe_kind = kind.replace("'", "''")
            where_parts.append(f"kind = '{safe_kind}'")
        if tags:
            tag_clauses = [f"tags LIKE '%{t.replace(chr(39), chr(39)*2)}%'" for t in tags]
            where_parts.append(f"({' OR '.join(tag_clauses)})")
        where = " AND ".join(where_parts) if where_parts else None
        tables = [t for t in [
            getattr(self, "_proj_docs_lance_table", None),
            getattr(self, "_fw_docs_lance_table", None),
        ] if t is not None]
        if not tables:
            return [], False
        fetch_n = max(top_n, VECTOR_TOP_K)
        all_candidates: list[dict] = []
        if getattr(self, "_proj_docs_lance_table", None) is not None:
            all_candidates.extend(self._lance_search(self._proj_docs_lance_table, qvec, fetch_n, where=where, layer="project"))
        if getattr(self, "_fw_docs_lance_table", None) is not None:
            all_candidates.extend(self._lance_search(self._fw_docs_lance_table, qvec, fetch_n, where=where, layer="framework"))
        all_candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        candidates = all_candidates[:fetch_n]
        reranker = self._get_reranker()
        if reranker is not None:
            results = self._rerank(query, candidates, top_n)
            return results, True
        return candidates[:top_n], False

    def search_code(self, query: str, language: Optional[str] = None, top_n: int = 7, kind: Optional[str] = None, max_per_file: Optional[int] = None, tags: Optional[list] = None) -> tuple[list[dict], bool]:
        self._ensure_loaded()
        CODE_MODEL = self._indexer_constant("CODE_MODEL")
        qvec = self._embed_query(query, CODE_MODEL)

        where_parts = []
        if kind:
            safe_kind = kind.replace("'", "''")
            where_parts.append(f"kind = '{safe_kind}'")
        if tags:
            tag_clauses = [f"tags LIKE '%{t.replace(chr(39), chr(39)*2)}%'" for t in tags]
            where_parts.append(f"({' OR '.join(tag_clauses)})")
        where = " AND ".join(where_parts) if where_parts else None
        fetch_n_base = top_n * 4 if language or max_per_file is not None else top_n
        fetch_n = max(fetch_n_base, VECTOR_TOP_K)

        def _code_dense(layer: str) -> list[dict]:
            table = self._open_lance_table(layer, "code")
            if table is None:
                return []
            return self._lance_search(table, qvec, fetch_n, where=where, layer=layer)

        def _code_fts(layer: str) -> list[dict]:
            table = self._open_lance_table(layer, "code")
            if table is None:
                return []
            return self._lance_fts_search(table, query, fetch_n, where=where, layer=layer)

        if getattr(self, "_lance_available", None):
            dense_lists: list[list[dict]] = []
            fts_lists: list[list[dict]] = []
            for layer in ("project", "framework"):
                if (layer, "code") in self._lance_available:
                    dense = sorted(_code_dense(layer), key=lambda x: x.get("score", 0.0), reverse=True)
                    fts = sorted(_code_fts(layer), key=lambda x: x.get("score", 0.0), reverse=True)
                    if dense:
                        dense_lists.append(dense)
                    if fts:
                        fts_lists.append(fts)
            if not dense_lists and not fts_lists:
                return [], False
            dense_merged = self._rrf_merge(dense_lists, fetch_n) if dense_lists else []
            fts_merged = self._rrf_merge(fts_lists, fetch_n) if fts_lists else []
            results = self._rrf_merge([dense_merged, fts_merged], fetch_n)
        else:
            tables = [t for t in [
                getattr(self, "_proj_code_lance_table", None),
                getattr(self, "_fw_code_lance_table", None),
            ] if t is not None]
            if not tables:
                return [], False
            all_candidates: list[dict] = []
            if getattr(self, "_proj_code_lance_table", None) is not None:
                all_candidates.extend(self._lance_search(self._proj_code_lance_table, qvec, fetch_n, where=where, layer="project"))
            if getattr(self, "_fw_code_lance_table", None) is not None:
                all_candidates.extend(self._lance_search(self._fw_code_lance_table, qvec, fetch_n, where=where, layer="framework"))
            all_candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            results = all_candidates[:fetch_n]
        if language:
            results = [r for r in results if r.get("language") == language]
        if max_per_file is not None:
            seen: dict[str, int] = {}
            filtered = []
            for r in results:
                p = str(r.get("path") or "")
                count = seen.get(p, 0)
                if count < max_per_file:
                    seen[p] = count + 1
                    filtered.append(r)
            results = filtered
        reranker = self._get_reranker()
        if reranker is not None:
            results = self._rerank(query, results, top_n)
            return results, True
        return results[:top_n], False

    def search_combined(self, query: str, top_n: int = 7, question_type: str = "") -> tuple[list[dict], bool, int, int, list[str], list[str], str]:
        """Combined semantic search across docs and code indexes.

        Returns ``(results, reranked, vector_ms, rerank_ms, definition_boosted, second_hop_symbols, symbol_extraction_method)``.

        - ``question_type`` influences retrieval weighting and post-rerank ordering:
          - ``"navigational"``: code-index candidates receive a ``RRF_NAVIGATIONAL_CODE_WEIGHT``
            multiplier in RRF scoring; docs-index receives ``RRF_NAVIGATIONAL_DOCS_WEIGHT``.
          - ``"explanatory"``: after reranking, citations from ``INFRASTRUCTURE_PATH_SEGMENTS``
            (scaffolding/wiring layers) are stable-partitioned to the end of the result list.
            A second retrieval hop extracts symbol names from the top reranked citations and
            injects their definition files as additional candidates before a second rerank.
          - All other values (including ``""``) leave weighting and ordering unchanged.
        - ``vector_ms``: wall time for the vector fetch phase (both indexes), in milliseconds.
        - ``rerank_ms``: wall time for reranker inference or RRF merge, in milliseconds.
        - ``definition_boosted``: list of rule labels that fired (e.g. ``["sql"]``); empty when no rule fired.
        - ``second_hop_symbols``: list of symbol names that triggered second-hop retrieval; empty when
          the second hop was skipped or produced no candidates.
        - ``symbol_extraction_method``: extraction method used for the second-hop symbol pass —
          ``"ast"`` (Python stdlib AST or tree-sitter produced symbols), ``"regex"`` (AST unavailable
          or produced no symbols), or ``"none"`` (second hop not attempted, or all citations were
          infra-filtered before extraction).
        """
        self._ensure_loaded()
        DOCS_MODEL = self._indexer_constant("DOCS_MODEL")
        CODE_MODEL = self._indexer_constant("CODE_MODEL")

        # --- Artifact-anchored exact-first pass ---
        # For questions classified as artifact_anchored, try a keyword lookup on the
        # concrete artifact token before the broad semantic pass. If the exact pass
        # returns at least one code result, rerank and return immediately. If it finds
        # nothing, fall through to the broad semantic pass as explanatory.
        if question_type == "artifact_anchored":
            artifact_token = _extract_artifact_cue(query)
            if artifact_token:
                try:
                    kw_resp = code_keyword_response(self.root, artifact_token)
                    if kw_resp.get("status") == "ok":
                        kw_candidates = [
                            {
                                "path": r.get("path", ""),
                                "text": r.get("snippet", ""),
                                "score": 0.0,
                                "kind": "code",
                                "lines": [r.get("line", 1), r.get("line", 1)],
                            }
                            for r in kw_resp["data"]["results"]
                            if r.get("path")
                        ]
                        if kw_candidates:
                            t_exact = time.monotonic()
                            reranker = self._get_reranker()
                            if reranker is not None:
                                try:
                                    results = self._rerank(query, kw_candidates, top_n)
                                    results = _partition_tests(results)
                                    return results, True, 0, round((time.monotonic() - t_exact) * 1000), ["artifact_anchored"], [], "none"
                                except Exception:
                                    pass
                            return _partition_tests(kw_candidates[:top_n]), False, 0, 0, ["artifact_anchored"], [], "none"
                except Exception:
                    pass
            # Exact pass found no code results — treat remainder as explanatory
            question_type = "explanatory"

        # --- Vector fetch phase (timed) ---
        t_vector = time.monotonic()
        top_k = VECTOR_TOP_K_EXPLANATORY if question_type == "explanatory" else VECTOR_TOP_K
        docs_qvec = self._embed_query(query, DOCS_MODEL)
        code_qvec = self._embed_query(query, CODE_MODEL)
        docs_candidates = []
        if getattr(self, "_proj_docs_lance_table", None) is not None:
            docs_candidates.extend(self._lance_search(self._proj_docs_lance_table, docs_qvec, top_k, layer="project"))
        if getattr(self, "_fw_docs_lance_table", None) is not None:
            docs_candidates.extend(self._lance_search(self._fw_docs_lance_table, docs_qvec, top_k, layer="framework"))
        docs_candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        code_candidates = []
        if getattr(self, "_proj_code_lance_table", None) is not None:
            code_candidates.extend(self._lance_search(self._proj_code_lance_table, code_qvec, top_k, layer="project"))
        if getattr(self, "_fw_code_lance_table", None) is not None:
            code_candidates.extend(self._lance_search(self._fw_code_lance_table, code_qvec, top_k, layer="framework"))
        code_candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        vector_ms = round((time.monotonic() - t_vector) * 1000)

        all_candidates = docs_candidates + code_candidates

        # --- Definition-file boosting: vocabulary-triggered keyword augmentation ---
        q_lower = query.lower()
        definition_boosted: list[str] = []
        for rule in DEFINITION_BOOST_RULES:
            if not any(term in q_lower for term in rule["vocabulary"]):
                continue
            # Most specific matching term: longest vocabulary term > 3 chars present in query
            matching_terms = [t for t in rule["vocabulary"] if len(t) > 3 and t in q_lower]
            search_term = max(matching_terms, key=len) if matching_terms else query
            injected = 0
            for ext in rule["extensions"]:
                if injected >= DEFINITION_BOOST_CANDIDATES:
                    break
                try:
                    kw_resp = code_keyword_response(self.root, search_term, glob=f"*{ext}")
                    if kw_resp.get("status") == "ok":
                        for r in kw_resp["data"]["results"]:
                            if injected >= DEFINITION_BOOST_CANDIDATES:
                                break
                            all_candidates.append({
                                "path": r.get("path", ""),
                                "text": r.get("snippet", ""),
                                "score": 0.0,
                                "kind": "code",
                                "lines": [r.get("line", 1), r.get("line", 1)],
                            })
                            injected += 1
                except Exception:
                    pass
            if injected > 0:
                definition_boosted.append(rule["label"])

        # --- Symbol-first injection (explanatory only, 12q63) ---
        if question_type == "explanatory":
            sym = _extract_question_symbol(query)
            if sym:
                existing_keys = {
                    (r.get("path", ""), (r.get("lines") or [0])[0])
                    for r in all_candidates
                }
                try:
                    kw_resp = code_keyword_response(self.root, sym)
                    if kw_resp.get("status") == "ok":
                        sym_injected = 0
                        for r in kw_resp["data"]["results"][:2]:
                            key = (r.get("path", ""), r.get("line", 0))
                            if key not in existing_keys:
                                all_candidates.append({
                                    "path": r.get("path", ""),
                                    "text": r.get("snippet", ""),
                                    "score": 0.0,
                                    "kind": "code",
                                    "lines": [r.get("line", 1), r.get("line", 1)],
                                    "_sym_injected": True,
                                })
                                existing_keys.add(key)
                                sym_injected += 1
                        if sym_injected > 0:
                            definition_boosted.append(f"symbol:{sym}")
                except Exception:
                    pass

        # --- Rerank / RRF phase (timed) ---
        t_rerank = time.monotonic()
        reranker = self._get_reranker()
        second_hop_symbols: list[str] = []
        symbol_extraction_method: str = "none"
        if reranker is not None:
            try:
                results = self._rerank(query, all_candidates, top_n)
                rerank_ms = round((time.monotonic() - t_rerank) * 1000)

                # --- Second-hop symbol expansion (explanatory questions only) ---
                if question_type == "explanatory":
                    symbols, symbol_extraction_method = _extract_symbols_from_citations(results)
                    if symbols:
                        # Track which (path, start_line) pairs are already in the pool
                        first_hop_keys = {
                            (r.get("path", ""), (r.get("lines") or [0])[0])
                            for r in all_candidates
                        }
                        second_hop_candidates: list[dict] = []
                        for sym in symbols:
                            if len(second_hop_candidates) >= MAX_SECOND_HOP_CANDIDATES:
                                break
                            try:
                                kw_resp = code_keyword_response(self.root, sym)
                                if kw_resp.get("status") == "ok":
                                    for r in kw_resp["data"]["results"]:
                                        if len(second_hop_candidates) >= MAX_SECOND_HOP_CANDIDATES:
                                            break
                                        key = (r.get("path", ""), r.get("line", 0))
                                        if key not in first_hop_keys:
                                            second_hop_candidates.append({
                                                "path": r.get("path", ""),
                                                "text": r.get("snippet", ""),
                                                "score": 0.0,
                                                "kind": "code",
                                                "lines": [r.get("line", 1), r.get("line", 1)],
                                            })
                                            first_hop_keys.add(key)
                            except Exception:
                                pass
                        if second_hop_candidates:
                            second_hop_symbols = symbols
                            results = self._rerank(
                                query, results + second_hop_candidates, top_n
                            )

                # Stable partition: push scaffolding-layer citations to end
                if question_type == "explanatory":
                    results = _partition_infra(results)
                for r in results:
                    r.pop("_sym_injected", None)
                rerank_ms = round((time.monotonic() - t_rerank) * 1000)
                return results, True, vector_ms, rerank_ms, definition_boosted, second_hop_symbols, symbol_extraction_method
            except Exception:
                pass

        # RRF fallback — apply navigational weight bias when appropriate
        # (second hop is skipped in RRF path — unpredictable ordering without reranker)
        rrf_weights = (
            [RRF_NAVIGATIONAL_DOCS_WEIGHT, RRF_NAVIGATIONAL_CODE_WEIGHT]
            if question_type == "navigational"
            else None
        )
        results = self._rrf_merge([docs_candidates, code_candidates], top_n, weights=rrf_weights)
        rerank_ms = round((time.monotonic() - t_rerank) * 1000)
        if question_type == "explanatory":
            results = _partition_infra(results)
        for r in results:
            r.pop("_sym_injected", None)
        return results, False, vector_ms, rerank_ms, definition_boosted, second_hop_symbols, symbol_extraction_method

    def get_seed(self, name: str) -> Optional[dict]:
        self._ensure_loaded()
        name_lower = name.lower().strip()
        # Query Lance docs table for seed chunks; fall back to empty if table absent.
        for table in filter(None, [
            getattr(self, "_proj_docs_lance_table", None),
            getattr(self, "_fw_docs_lance_table", None),
        ]):
            try:
                rows = table.search().where("kind = 'seed'", prefilter=True).to_list()
            except Exception:
                rows = []
            for row in rows:
                chunk = {k: v for k, v in row.items() if k != "vector"}
                path = chunk.get("path", "")
                section = chunk.get("section") or ""
                if name_lower in path.lower() or name_lower in section.lower():
                    chunk["path"] = self._qualify_index_path(path, "framework" if table is getattr(self, "_fw_docs_lance_table", None) else "project")
                    return chunk
        return None

    def is_stale(self) -> bool:
        """Return True if the index may be out of date (no meta or missing files)."""
        return not (self.index_dir / "meta.json").exists() and not (self.framework_index_dir / "meta.json").exists()


# ---------------------------------------------------------------------------
# Wave inspection helpers
# ---------------------------------------------------------------------------

def _read_workflow_config(root: Path) -> dict:
    cfg = root / "docs" / "workflow-config.json"
    if cfg.is_file():
        try:
            return json.loads(cfg.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _read_project_required_review_lanes(root: Path) -> list[str]:
    """Return project-declared required review lanes from workflow-config.json."""
    cfg = _read_workflow_config(root)
    raw = cfg.get("required_review_lanes", [])
    if not isinstance(raw, list):
        return []
    return [str(lane).strip() for lane in raw if isinstance(lane, str) and str(lane).strip()]


def _read_wave_council_policy(root: Path) -> dict[str, Any]:
    """Return normalized Wave Council policy from workflow-config.json."""
    cfg = _read_workflow_config(root)
    raw = cfg.get("wave_council_policy", {})
    if not isinstance(raw, dict) or not bool(raw.get("enabled")):
        return {}

    phases_raw = raw.get("phases", {})
    if not isinstance(phases_raw, dict):
        phases_raw = {}

    phase_defaults = {
        "prepare": "wave-council-readiness",
        "review": "wave-council-delivery",
    }
    phases: dict[str, dict[str, str]] = {}
    for phase, default_key in phase_defaults.items():
        phase_raw = phases_raw.get(phase, {})
        if not isinstance(phase_raw, dict):
            phase_raw = {}
        signoff_key = str(phase_raw.get("signoff_key", default_key)).strip()
        moderator_role = str(phase_raw.get("moderator_role", "council-moderator")).strip()
        if signoff_key:
            phases[phase] = {
                "signoff_key": signoff_key,
                "moderator_role": moderator_role or "council-moderator",
            }

    return {
        "enabled": True,
        "required_for_all_waves": bool(raw.get("required_for_all_waves", True)),
        "evidence_section": str(raw.get("evidence_section", "## Review Evidence")).strip() or "## Review Evidence",
        "transition_policy": str(raw.get("transition_policy", "")).strip(),
        "phases": phases,
    }


def _required_wave_council_signoffs(root: Path, lifecycle_phase: str, wave_text: Optional[str] = None) -> list[str]:
    policy = _read_wave_council_policy(root)
    if not policy:
        return []
    phase_map = {
        "prepare": ["prepare"],
        "review": ["review"],
        "close": ["prepare", "review"],
    }
    required: list[str] = []
    for phase in phase_map.get(lifecycle_phase, []):
        signoff_key = policy.get("phases", {}).get(phase, {}).get("signoff_key")
        if signoff_key and signoff_key not in required:
            required.append(signoff_key)
    if not required:
        return required

    transition_policy = str(policy.get("transition_policy", "")).strip().lower()
    if transition_policy != "applies-from-next-prepare" or lifecycle_phase == "prepare" or not wave_text:
        return required

    prepare_key = policy.get("phases", {}).get("prepare", {}).get("signoff_key")
    review_key = policy.get("phases", {}).get("review", {}).get("signoff_key")
    has_prepare_signoff = bool(prepare_key and _lane_has_signoff(wave_text, prepare_key))
    has_review_signoff = bool(review_key and _lane_has_signoff(wave_text, review_key))

    if lifecycle_phase == "review":
        return required
    if lifecycle_phase == "close":
        if has_prepare_signoff:
            return required
        if has_review_signoff and review_key:
            return [review_key]
        return [key for key in required if key != prepare_key]
    return required


def _read_project_sensors(root: Path) -> list[dict]:
    """Return registered sensor definitions from workflow-config.json."""
    cfg = _read_workflow_config(root)
    raw = cfg.get("sensors", [])
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        command = item.get("command")
        if not name or not command:
            continue
        out.append({
            "name": name,
            "command": command if isinstance(command, list) else str(command),
            "dimension": str(item.get("dimension", "maintainability")),
            "description": str(item.get("description", "")),
        })
    return out


def _normalize_prefix_list(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    normalized: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        token = item.strip().replace("\\", "/").strip("/")
        if token and token not in normalized:
            normalized.append(token)
    return tuple(normalized)


def _workflow_project_include_prefixes(root: Path) -> dict[str, tuple[str, ...]]:
    data = _read_workflow_config(root)
    if not isinstance(data, dict):
        return {"docs": (), "code": ()}
    indexing = data.get("indexing", {})
    if not isinstance(indexing, dict):
        return {"docs": (), "code": ()}

    configured = indexing.get("project_include_prefixes", {})
    if isinstance(configured, list):
        prefixes = _normalize_prefix_list(configured)
        return {"docs": prefixes, "code": prefixes}

    docs_prefixes: tuple[str, ...] = ()
    code_prefixes: tuple[str, ...] = ()
    if isinstance(configured, dict):
        docs_prefixes = _normalize_prefix_list(configured.get("docs"))
        code_prefixes = _normalize_prefix_list(configured.get("code"))

    if not code_prefixes and bool(indexing.get("include_framework_code_for_code_search", False)):
        code_prefixes = (".wavefoundry/framework/scripts",)
    return {"docs": docs_prefixes, "code": code_prefixes}


_WAVE_ID_PATTERN = re.compile(r"^wave-id:\s+`([^`]+)`", re.MULTILINE)
_STATUS_PATTERN = re.compile(r"^Status:\s+(\S+)", re.MULTILINE)
_CHANGE_ID_PATTERN = re.compile(r"^Change ID:\s+`([^`]+)`", re.MULTILINE)
_CHANGE_STATUS_PATTERN = re.compile(r"^(?:Change|Item) Status:\s+`([^`]+)`", re.MULTILINE)
_TITLE_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _parse_wave_record(wave_md: Path) -> dict:
    text = wave_md.read_text(encoding="utf-8")
    wave_id_m = _WAVE_ID_PATTERN.search(text)
    status_m = _STATUS_PATTERN.search(text)
    change_ids = _CHANGE_ID_PATTERN.findall(text)
    change_statuses = _CHANGE_STATUS_PATTERN.findall(text)
    return {
        "wave_id": wave_id_m.group(1) if wave_id_m else wave_md.parent.name,
        "status": status_m.group(1) if status_m else "unknown",
        "changes": [
            {"id": cid, "status": cst}
            for cid, cst in zip(change_ids, change_statuses)
        ],
        "path": str(wave_md),
    }


def list_waves(root: Path) -> list[dict]:
    waves_root = root / "docs" / "waves"
    if not waves_root.exists():
        return []
    result = []
    for wave_dir in sorted(waves_root.iterdir()):
        if not wave_dir.is_dir():
            continue
        wave_md = wave_dir / "wave.md"
        if wave_md.exists():
            result.append(_parse_wave_record(wave_md))
    return result


def _parse_plan_record(root: Path, plan_md: Path) -> dict:
    text = plan_md.read_text(encoding="utf-8")
    change_id_m = _CHANGE_ID_PATTERN.search(text)
    change_status_m = _CHANGE_STATUS_PATTERN.search(text)
    status_m = _STATUS_PATTERN.search(text)
    title_m = _TITLE_PATTERN.search(text)
    return {
        "id": change_id_m.group(1) if change_id_m else plan_md.stem,
        "status": (
            change_status_m.group(1)
            if change_status_m
            else status_m.group(1) if status_m else "unknown"
        ),
        "title": title_m.group(1).strip() if title_m else plan_md.stem,
        "path": str(plan_md.relative_to(root)).replace("\\", "/"),
    }


def list_plans(root: Path) -> list[dict]:
    plans_root = root / "docs" / "plans"
    if not plans_root.exists():
        return []
    result = []
    for plan_md in sorted(plans_root.glob("*.md")):
        if plan_md.name == "plan-template.md":
            continue
        result.append(_parse_plan_record(root, plan_md))
    return result


def _dir_fingerprint(
    directory: Path,
    glob: str,
    *,
    skip: Optional[set[str]] = None,
    recursive: bool = False,
) -> tuple[int, int]:
    """Return a ``(file_count, max_mtime_ns)`` fingerprint for a directory.

    Used to detect whether a watched directory has changed since the last cache
    population. Returns ``(0, 0)`` when the directory does not exist.

    Args:
        directory: The directory to scan.
        glob: Glob pattern passed to ``Path.rglob`` (recursive) or ``Path.glob``.
        skip: Optional set of filenames to exclude from the scan.
        recursive: When True, uses ``rglob``; otherwise uses ``glob``.
    """
    if not directory.exists():
        return (0, 0)
    best_ns = 0
    count = 0
    scanner = directory.rglob(glob) if recursive else directory.glob(glob)
    for p in scanner:
        if skip and p.name in skip:
            continue
        try:
            st = p.stat()
        except OSError:
            continue
        count += 1
        best_ns = max(best_ns, int(st.st_mtime_ns))
    return (count, best_ns)


class McpRepoCache:
    """Per-process cache for wave/plan summaries and prompt lookups.

    Invalidated automatically when the underlying directory fingerprint
    (file count + max mtime) changes. Call ``invalidate()`` explicitly after
    any mutating operation to force an immediate refresh on the next access.
    """

    def __init__(self, root: Path, *, index: Optional[WaveIndex] = None) -> None:
        self.root = root.resolve()
        self._index = index
        self._waves: Optional[list[dict]] = None
        self._waves_key: Optional[tuple[int, int]] = None
        self._plans: Optional[list[dict]] = None
        self._plans_key: Optional[tuple[int, int]] = None
        self._prompt_cache: dict[str, Any] = {}
        self._prompt_key: Optional[tuple[int, int]] = None

    def invalidate(self) -> None:
        """Clear all cached data and mark the semantic index for reload."""
        self._waves = None
        self._waves_key = None
        self._plans = None
        self._plans_key = None
        self._prompt_cache = {}
        self._prompt_key = None
        if self._index is not None:
            self._index._loaded = False

    def _wave_fingerprint(self) -> tuple[int, int]:
        return _dir_fingerprint(
            self.root / "docs" / "waves", "wave.md", recursive=True
        )

    def _plans_fingerprint(self) -> tuple[int, int]:
        return _dir_fingerprint(
            self.root / "docs" / "plans", "*.md", skip={"plan-template.md"}
        )

    def _prompts_fingerprint(self) -> tuple[int, int]:
        return _dir_fingerprint(self.root / "docs" / "prompts", "*.md")

    def get_prompt_text_cached(self, shortcut: str) -> Optional[str]:
        """Return prompt body like ``get_prompt``, using an mtime-keyed per-process cache."""
        key = self._prompts_fingerprint()
        if self._prompt_key != key:
            self._prompt_cache = {}
            self._prompt_key = key
        norm = shortcut.strip().lower()
        if norm in self._prompt_cache:
            hit = self._prompt_cache[norm]
            return None if hit is _PROMPT_MISS else str(hit)
        text = get_prompt(self.root, shortcut)
        self._prompt_cache[norm] = _PROMPT_MISS if text is None else text
        return text

    def list_waves_cached(self) -> list[dict]:
        key = self._wave_fingerprint()
        if self._waves is not None and self._waves_key == key:
            return self._waves
        waves = list_waves(self.root)
        self._waves = waves
        self._waves_key = key
        return waves

    def list_plans_cached(self) -> list[dict]:
        key = self._plans_fingerprint()
        if self._plans is not None and self._plans_key == key:
            return self._plans
        plans = list_plans(self.root)
        self._plans = plans
        self._plans_key = key
        return plans


def first_party_tool_names_violating_prefix(tool_names: Iterable[str]) -> list[str]:
    """Return tool names that do not start with an approved MCP surface prefix."""
    violations: list[str] = []
    for name in sorted(tool_names):
        if not any(name.startswith(prefix) for prefix in MCP_TOOL_PREFIXES):
            violations.append(name)
    return violations


def resolve_path_under_root(repo_root: Path, user_path: str) -> tuple[Optional[Path], Optional[dict[str, Any]]]:
    """Resolve a user-supplied path to an absolute path confined under repo_root.

    Intended for future file navigation tools. Returns ``(path, None)`` on success or
    ``(None, diagnostic)`` when the path escapes allowed roots or cannot be resolved.
    """
    root = repo_root.resolve()
    raw = Path(user_path.strip()).expanduser()
    try:
        candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    except (OSError, RuntimeError) as exc:
        return None, _diagnostic(
            "path_resolution_failed",
            str(exc),
            recovery_tools=["wave_validate", "wave_current"],
            recovery_usage="wave_validate()",
        )
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, _diagnostic(
            "path_outside_allowed_roots",
            f"Path {user_path!r} resolves outside the configured repository root.",
            recovery_tools=["wave_current", "wave_validate"],
            recovery_usage="wave_current()",
        )
    return candidate, None


def current_wave(root: Path, cache: Optional[McpRepoCache] = None) -> Optional[dict]:
    waves = cache.list_waves_cached() if cache else list_waves(root)
    for wave in waves:
        if wave["status"] in ("active", "implementing", "planned"):
            return wave
    return None


def _find_other_active_wave(
    root: Path,
    target_wave_path: Path,
    cache: Optional[McpRepoCache] = None,
) -> Optional[dict]:
    """Return the first active wave whose path is not ``target_wave_path``.

    Used by the single-active-wave guard in ``wave_prepare``. Returns ``None``
    when no other wave is active (the target may itself be active and still
    allow self-prepare).
    """
    waves = cache.list_waves_cached() if cache else list_waves(root)
    target_resolved = target_wave_path.resolve()
    for wave in waves:
        if wave["status"] not in ("active", "implementing"):
            continue
        wave_md_path = Path(wave["path"])
        if not wave_md_path.is_absolute():
            wave_md_path = root / wave_md_path
        if wave_md_path.resolve() == target_resolved:
            continue
        return wave
    return None


def get_change(root: Path, change_id_prefix: str) -> Optional[str]:
    prefix = change_id_prefix.strip().lower()
    search_dirs = [
        root / "docs" / "plans",
        root / "docs" / "waves",
    ]
    for base in search_dirs:
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            if prefix in p.stem.lower():
                return p.read_text(encoding="utf-8")
    return None


def get_prompt(root: Path, shortcut: str) -> Optional[str]:
    shortcut_lower = shortcut.lower().strip()
    prompts_dir = root / "docs" / "prompts"
    if not prompts_dir.exists():
        return None
    # Slug-match the shortcut against prompt filenames and content
    slug = re.sub(r"[^\w]+", "-", shortcut_lower).strip("-")
    for p in prompts_dir.glob("*.md"):
        if slug in p.stem.lower():
            return p.read_text(encoding="utf-8")
    # Fallback: search file content for shortcut phrase
    for p in prompts_dir.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        if shortcut_lower in text.lower():
            return text
    return None


def _diagnostic(
    code: str,
    message: str,
    *,
    recovery_tools: list[str] | None = None,
    recovery_usage: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if recovery_tools:
        payload["recovery_tools"] = recovery_tools
    if recovery_usage:
        payload["recovery_usage"] = recovery_usage
    return payload


def _response(
    status: str,
    data: dict[str, Any] | None = None,
    *,
    diagnostics: list[dict[str, Any]] | None = None,
    next_tools: list[str] | None = None,
    usage: str = "",
) -> dict[str, Any]:
    """Build the standard MCP response envelope.

    Accepted ``status`` values:
    - ``"ok"``       — operation succeeded.
    - ``"error"``    — operation failed; ``isError: True`` is also set so that
                       MCP protocol-level clients see the correct error signal.
    - ``"dry_run"``  — mutating tool was called with ``mode='dry_run'``; no
                       writes were performed.  Callers should treat this like
                       ``"ok"`` but not assume side effects occurred.
    """
    envelope: dict[str, Any] = {
        "status": status,
        "data": data or {},
        "diagnostics": diagnostics or [],
        "next_tools": next_tools or [],
        "usage": usage,
    }
    if status == "error":
        envelope["isError"] = True
    return envelope


def _registered_mcp_tool_names(mcp: Any) -> set[str]:
    """Return registered first-party tool names from FastMCP (API varies by version)."""
    tm = getattr(mcp, "_tool_manager", None)
    tools = getattr(tm, "_tools", None) if tm is not None else None
    if tools:
        return set(tools.keys())
    legacy = getattr(mcp, "_tools", None)
    if legacy:
        return set(legacy.keys())
    return set()


def _ensure_no_extra_args(tool_name: str, kwargs: dict[str, Any]) -> Optional[dict[str, Any]]:
    """If MCP passed unsupported keyword arguments, return a structured error envelope.

    FastMCP generates a schema entry named ``kwargs`` from ``**kwargs`` in the function
    signature and may forward it back to the handler as a named argument.  Strip that
    self-referential key before checking for genuine extras.
    """
    real_extras = {k: v for k, v in kwargs.items() if k != "kwargs"}
    if not real_extras:
        return None
    kwargs = real_extras
    return _response(
        "error",
        {"tool": tool_name, "rejected_arguments": sorted(kwargs.keys())},
        diagnostics=[
            _diagnostic(
                "unknown_arguments",
                f"{tool_name} received unsupported arguments: {', '.join(sorted(kwargs.keys()))}.",
                recovery_tools=["wave_help"],
                recovery_usage="wave_help()",
            )
        ],
        next_tools=["wave_help"],
        usage=f"wave_help()  # see supported parameters for {tool_name}",
    )


def _slug_fragment(text: str) -> str:
    return re.sub(r"[^\w]+", "-", text.strip().lower()).strip("-")


def _codex_slug_fragment(text: str) -> str:
    return re.sub(r"[^0-9a-z]+", "-", text.strip().lower()).strip("-")


def _project_slug(root: Path) -> str:
    slug = _codex_slug_fragment(root.name)
    return slug or "project"


def server_identity(root: Path, *, server_runner_version: str | None = None) -> dict[str, Any]:
    resolved_root = root.resolve()
    data: dict[str, Any] = {
        "repo_root": str(resolved_root),
        "repo_name": resolved_root.name,
        "project_slug": _project_slug(resolved_root),
    }
    rv = server_runner_version if server_runner_version is not None else _runner_version
    if rv:
        data.update(version_payload(root, server_runner_version=rv))
    return data


def _trust_label(path: str, *, kind: str = "") -> str:
    normalized = path.replace("\\", "/")
    if kind == "seed" or normalized.startswith(".wavefoundry/framework/"):
        return TRUSTED_FRAMEWORK
    if (
        normalized == "docs/workflow-config.json"
        or normalized.startswith("docs/waves/")
        or normalized.startswith("docs/plans/")
    ):
        return TRUSTED_PROJECT_METADATA
    return UNTRUSTED_PROJECT_CONTENT


def _result_id(prefix: str, chunk: dict[str, Any]) -> str:
    raw_id = str(chunk.get("id") or "").strip()
    if raw_id:
        return raw_id if raw_id.startswith(f"{prefix}:") else f"{prefix}:{raw_id}"
    path = str(chunk.get("path") or "").replace("\\", "/")
    section = str(chunk.get("section") or "").strip()
    if section:
        return f"{prefix}:{path}#{_slug_fragment(section)}"
    lines = chunk.get("lines")
    if isinstance(lines, list) and len(lines) >= 2:
        return f"{prefix}:{path}:L{lines[0]}-L{lines[1]}"
    return f"{prefix}:{path}"


def _search_result(prefix: str, chunk: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "result_id": _result_id(prefix, chunk),
        "path": chunk.get("path"),
        "kind": chunk.get("kind"),
        "section": chunk.get("section"),
        "lines": chunk.get("lines"),
        "excerpt": str(chunk.get("text") or "")[:600],
        "trust_label": _trust_label(str(chunk.get("path") or ""), kind=str(chunk.get("kind") or "")),
    }
    if "language" in chunk:
        payload["language"] = chunk.get("language")
    if "score" in chunk:
        payload["score"] = float(chunk["score"])
    return payload


def _help_catalog() -> dict[str, Any]:
    return {
        "contract_version": 2,
        "core_tools": [
            "wave_help",
            "wave_server_info",
            "wave_mcp_reload",
            "wave_map",
            "wave_current",
            "wave_create_wave",
            "wave_add_change",
            "wave_prepare",
            "docs_search",
            "code_search",
            "seed_get",
            "wave_validate",
            "wave_garden",
            "wave_sync_surfaces",
            "wave_index_health",
            "wave_index_build",
            "wave_audit",
            "wave_dashboard_start",
            "wave_dashboard_stop",
            "wave_dashboard_restart",
        ],
        "compatibility_tools": [
            "wave_new_feature",
            "wave_new_bug",
            "wave_new_enhancement",
            "wave_new_refactor",
            "wave_new_change",
            "wave_new_documentation",
            "wave_new_tech_debt",
            "wave_new_task",
            "wave_new_maintenance",
            "wave_new_operations",
        ],
        "prefixes": {
            "wave_": "wave lifecycle, change planning, and framework operations",
            "docs_": "semantic documentation search",
            "code_": "semantic code search and future code navigation",
            "seed_": "canonical framework seed retrieval",
        },
        "workflows": {
            "server_identity": {
                "recommended_chain": ["wave_server_info", "wave_current"],
                "rationale": "Start by confirming which repository this MCP server is attached to, then inspect the active wave in that repository.",
                "fallback_tools": ["wave_help"],
                "next_step": "Call wave_server_info immediately after connect.",
                "usage": "wave_server_info()",
            },
            "plan_feature": {
                "recommended_chain": ["wave_new_feature", "wave_get_change", "wave_validate"],
                "rationale": "Create the change doc with the kind-specific tool, inspect it, then validate docs state.",
                "fallback_tools": ["wave_new_bug", "wave_new_enhancement", "wave_new_maintenance"],
                "next_step": "Create the change document with the appropriate wave_new_<kind> tool first.",
                "usage": "wave_new_feature(slug='my-feature')",
            },
            "inspect_wave": {
                "recommended_chain": ["wave_audit", "wave_current", "wave_list_waves", "wave_get_change"],
                "rationale": (
                    "Start with wave_audit for a combined wave + lint + index health snapshot. "
                    "Follow up with wave_current or wave_get_change for detail."
                ),
                "fallback_tools": ["wave_list_plans"],
                "next_step": "Run wave_audit for a full readiness snapshot.",
                "usage": "wave_audit()",
            },
            "start_wave": {
                "recommended_chain": ["wave_create_wave", "wave_add_change", "wave_prepare"],
                "rationale": (
                    "Create the wave, admit planned changes, then run transactional prepare checks. "
                    "Before wave_prepare will pass, a journal artifact under docs/agents/journals/ "
                    "must contain a line in the exact form: wave-id: `<wave-id>` "
                    "(the key alone on its own line, wave ID in backticks, no trailing content after the closing backtick)."
                ),
                "fallback_tools": ["wave_help"],
                "next_step": "Create the wave in dry_run first.",
                "usage": "wave_create_wave(slug='mcp-lifecycle', mode='dry_run')",
            },
            "search_docs": {
                "recommended_chain": ["docs_search", "wave_map", "seed_get", "wave_get_prompt"],
                "rationale": "Search docs first, resolve anchors with wave_map, then open seeds or prompts when needed.",
                "fallback_tools": ["wave_help"],
                "next_step": "Run semantic docs search.",
                "usage": "docs_search(query='prepare wave', kind='prompt')",
            },
            "resolve_anchor": {
                "recommended_chain": ["wave_map", "wave_validate"],
                "rationale": "Turn a search result_id into a normalized path, trust label, and excerpt before reading more.",
                "fallback_tools": ["docs_search"],
                "next_step": "Call wave_map with the address from search results.",
                "usage": "wave_map(address='doc:docs/README.md#section')",
            },
            "search_code": {
                "recommended_chain": ["code_search", "wave_help"],
                "rationale": (
                    "Search indexed code chunks when code embeddings exist; fall back to guidance when they do not. "
                    "The language filter accepts category names (java, web, systems, script, data, sparksql, dotnet), "
                    "canonical language names (python, typescript, go, rust, ...), or raw extensions (tsx, .tsx). "
                    "Raw extensions normalize to their canonical name: tsx/.tsx → typescript, js/.js → javascript. "
                    ".tsx and .ts files are both indexed as language='typescript' — passing tsx or typescript is equivalent. "
                    "Use language='web' to include TypeScript, JavaScript, HTML, CSS, and SCSS in one filter. "
                    "Category searches return language_resolved listing the expanded language set."
                ),
                "fallback_tools": ["code_keyword"],
                "next_step": "Run semantic code search. Omit language to search all languages, or use a category for broad filtering.",
                "usage": "code_search(query='handle authentication errors', language='web')",
            },
            "reload_mcp": {
                "recommended_chain": ["wave_mcp_reload", "wave_server_info"],
                "rationale": (
                    "After a framework upgrade, reload MCP tool logic in-process and confirm "
                    "server_impl_version matches framework_version on disk."
                ),
                "fallback_tools": ["wave_help"],
                "next_step": "Call wave_mcp_reload after wave_upgrade cleanup or when impl_matches_disk is false.",
                "usage": "wave_mcp_reload()",
            },
            "maintain_framework": {
                "recommended_chain": ["wave_validate", "wave_garden", "wave_sync_surfaces"],
                "rationale": "Land on validation first, then run focused maintenance tools.",
                "fallback_tools": ["wave_current"],
                "next_step": "Validate the repo first, then run garden and sync with mode='run'.",
                "usage": "wave_garden(mode='run')",
            },
            "refresh_semantic_index": {
                "recommended_chain": ["wave_index_health", "wave_index_build"],
                "rationale": (
                    "Check layer health first. wave_index_build(mode='update') runs an incremental index "
                    "update (hash-based). Use wave_index_build(mode='rebuild') for a full rebuild of the "
                    "selected content."
                ),
                "fallback_tools": ["wave_help"],
                "next_step": "Call wave_index_health if you need stale/missing diagnostics before reindexing.",
                "usage": "wave_index_build(content='docs', mode='update')",
            },
        },
    }


@functools.lru_cache(maxsize=1)
def _cached_help_catalog_json() -> str:
    return json.dumps(_help_catalog(), sort_keys=True)


def _snapshot_help_catalog() -> dict[str, Any]:
    """Return a deep copy of the discovery catalogue (cached per process)."""
    return json.loads(_cached_help_catalog_json())


def wave_help_response(goal: str = "") -> dict[str, Any]:
    catalog = _snapshot_help_catalog()
    normalized = _slug_fragment(goal).replace("-", "_")
    if not normalized:
        return _response(
            "ok",
            catalog,
            next_tools=["wave_current"],
            usage="wave_help(goal='plan_feature')",
        )
    workflow = catalog["workflows"].get(normalized)
    if workflow is None:
        return _response(
            "ok",
            catalog,
            diagnostics=[
                _diagnostic(
                    "unknown_goal",
                    f"Unsupported workflow goal '{goal}'.",
                    recovery_tools=["wave_help"],
                    recovery_usage="wave_help()",
                )
            ],
            next_tools=["wave_help"],
            usage="wave_help()",
        )
    return _response(
        "ok",
        {"goal": normalized, **workflow},
        next_tools=list(workflow["recommended_chain"]),
        usage=str(workflow["usage"]),
    )




# ---------------------------------------------------------------------------
# Framework operation helpers (direct import)
# ---------------------------------------------------------------------------

_chunker_version_cache: str = ""


def _read_chunker_version() -> str:
    """Read CHUNKER_VERSION from chunker.py without importing the full module.

    Importing chunker.py requires tree-sitter and fastembed which are not
    always available (e.g. during unit tests). Reading the constant directly
    from source avoids that dependency.
    """
    global _chunker_version_cache
    if _chunker_version_cache:
        return _chunker_version_cache
    chunker_path = Path(__file__).resolve().parent / "chunker.py"
    try:
        source = chunker_path.read_text(encoding="utf-8")
        m = re.search(r'^CHUNKER_VERSION\s*=\s*["\']([^"\']+)["\']', source, re.MULTILINE)
        if m:
            _chunker_version_cache = m.group(1)
    except OSError:
        pass
    return _chunker_version_cache


def _background_build_status(root: Path) -> str:
    """Return 'running', 'completed', or 'none' for the background code build.

    Uses a PID file written by _spawn_background_code_build to detect whether
    the process is still alive. 'completed' means the PID file exists but the
    process has already exited (build finished or crashed).
    """
    pid_path = root / ".wavefoundry" / "index" / "background-build.pid"
    if not pid_path.exists():
        return "none"
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        return "running"
    except (ValueError, OSError):
        return "completed"


def _background_build_progress(root: Path) -> str:
    """Return the latest non-empty line from the background build log, if any."""
    log_path = _project_background_build_log_path(root)
    if not log_path.exists():
        return ""
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    for line in reversed(log_text.splitlines()):
        text = line.strip()
        if text:
            return text
    return ""


def _infer_tags(path: str) -> list[str]:
    """Return classification tags for a file path. Delegates to _tag_utils — single source of truth."""
    return _load_script("_tag_utils").infer_tags(path)


_script_cache: dict[str, Any] = {}
"""Module-level cache for scripts loaded via _load_script.

Keyed by a namespaced string (e.g. ``_wavefoundry_indexer``) so the cache
entries do not collide with public ``sys.modules`` names. Each module is
executed at most once per process — subsequent calls return the cached object.
If hot-reload is needed during development, call ``_script_cache.clear()``.
"""


def _load_script(name: str) -> Any:
    """Load a sibling script as a module, executing it at most once per process.

    Uses a private ``_script_cache`` dict keyed by a namespaced name so that
    the loaded module does not pollute public ``sys.modules`` and is not
    re-executed on repeated calls.
    """
    import importlib.util

    cache_key = f"_wavefoundry_{name}"
    if cache_key in _script_cache:
        return _script_cache[cache_key]
    spec = importlib.util.spec_from_file_location(
        cache_key, Path(__file__).resolve().parent / f"{name}.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _script_cache[cache_key] = mod
    return mod


def run_validate(root: Path) -> dict:
    """Run docs_lint and return structured pass/fail.

    ``PROJECT_ROOT`` is forwarded explicitly so the subprocess lints the
    correct tree even when the caller's environment already has ``PROJECT_ROOT``
    set to a different path (e.g. in multi-project MCP setups).
    """
    import subprocess
    script = Path(__file__).resolve().parent / "docs_lint.py"
    result = subprocess.run(
        [_preferred_python(), str(script)],
        capture_output=True, text=True,
        cwd=str(root),
        env={**os.environ, "PROJECT_ROOT": str(root)},
    )
    lines = (result.stdout + result.stderr).strip().splitlines()
    errors = [l for l in lines if l.startswith("ERROR:")]
    warnings = [l for l in lines if l.startswith("WARNING:")]
    passed = result.returncode == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "output": result.stdout + result.stderr,
    }


def run_garden(root: Path) -> dict:
    """Run docs_gardener and return structured summary."""
    import subprocess
    script = Path(__file__).resolve().parent / "docs_gardener.py"
    result = subprocess.run(
        [_preferred_python(), str(script)],
        capture_output=True, text=True,
        cwd=str(root),
        env={**os.environ, "PROJECT_ROOT": str(root)},
    )
    output = result.stdout + result.stderr
    updated = [l for l in output.splitlines() if "wrote" in l.lower()]
    return {
        "passed": result.returncode == 0,
        "files_updated": len(updated),
        "updated": updated,
        "output": output,
    }


def run_sync_surfaces(root: Path) -> dict:
    """Run render_platform_surfaces and return structured summary."""
    import subprocess
    script = Path(__file__).resolve().parent / "render_platform_surfaces.py"
    result = subprocess.run(
        [_preferred_python(), str(script)],
        capture_output=True, text=True,
        cwd=str(root),
        env={**os.environ, "PROJECT_ROOT": str(root)},
    )
    output = result.stdout + result.stderr
    written = [l for l in output.splitlines() if "wrote" in l.lower() or "rendered" in l.lower()]
    return {
        "passed": result.returncode == 0,
        "files_written": written,
        "output": output,
    }


def _index_dir_for_layer(root: Path, layer: str) -> Path:
    if layer == "project":
        return root / ".wavefoundry" / "index"
    if layer == "framework":
        return root / ".wavefoundry" / "framework" / "index"
    raise ValueError(f"Unsupported layer '{layer}'.")


def _read_index_rebuild_stats(root: Path, layer: str) -> dict[str, Any]:
    index_dir = _index_dir_for_layer(root, layer)
    meta_path = index_dir / "meta.json"

    meta: dict[str, Any] = {}
    doc_chunks = 0
    code_chunks = 0

    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}

    # Try Lance tables for chunk counts; fall back to 0 if unavailable.
    try:
        import lancedb
        db = lancedb.connect(str(index_dir))
        if (index_dir / "docs.lance").is_dir():
            doc_chunks = db.open_table("docs").count_rows()
        if (index_dir / "code.lance").is_dir():
            code_chunks = db.open_table("code").count_rows()
    except Exception:
        pass

    return {
        "files_total": len(meta.get("file_meta") or meta.get("file_hashes") or {}),
        "doc_chunks": doc_chunks,
        "code_chunks": code_chunks,
        "available_content": list(meta.get("content", [])),
        "built_at": meta.get("built_at", ""),
    }


def _index_is_up_to_date(root: Path, layer: str, content: str = "docs") -> bool:
    """Return True if the index has no stale or missing files.

    Runs the indexer with --dry-run (hash check only, no embedding/writes) and
    checks whether it reports the index as current. Used by run_index_rebuild
    to short-circuit spawning a background process when there is nothing to do.
    """
    import subprocess
    scripts_dir = Path(__file__).resolve().parent
    index_dir = _index_dir_for_layer(root, layer)
    if not (index_dir / "meta.json").exists():
        return False
    include_prefixes = _workflow_project_include_prefixes(root) if layer == "project" else {"docs": (), "code": ()}
    if layer == "project" and content == "all":
        # setup_index.py doesn't support --dry-run; check docs layer as a proxy
        check_content = "docs"
    else:
        check_content = content if content != "all" else "docs"
    cmd = [
        _preferred_python(), str(scripts_dir / "indexer.py"),
        "--root", str(root), "--content", check_content, "--dry-run",
    ]
    if layer == "framework":
        cmd.extend([
            "--index-dir", str(index_dir),
            "--include-prefix", ".wavefoundry/framework",
            "--no-ignore-files",
        ])
    elif layer == "project" and check_content in {"docs", "code"}:
        for prefix in (include_prefixes["docs"] if check_content == "docs" else include_prefixes["code"]):
            cmd.extend(["--project-include-prefix", prefix])
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(root),
            env={**os.environ, "PROJECT_ROOT": str(root)},
            timeout=30,
        )
        return result.returncode == 0 and "build_index: index is up to date" in (result.stdout + result.stderr)
    except Exception:
        return False


def _index_build_state_path(root: Path, layer: str) -> Path:
    if layer == "framework":
        return root / ".wavefoundry" / "framework" / "index" / "index-build.json"
    return root / ".wavefoundry" / "index" / "index-build.json"


def _clear_index_build_state(root: Path, layer: str) -> None:
    try:
        _index_build_state_path(root, layer).unlink()
    except OSError:
        pass


def _index_build_log_path(root: Path, layer: str) -> Path:
    if layer == "framework":
        return root / ".wavefoundry" / "logs" / "framework-index-build.log"
    return root / ".wavefoundry" / "logs" / "project-index-build.log"


def _project_background_build_log_path(root: Path) -> Path:
    return root / ".wavefoundry" / "logs" / "project-background-build.log"


def _index_build_stats_path(root: Path, layer: str) -> Path:
    if layer == "framework":
        return root / ".wavefoundry" / "framework" / "index" / "index-build-stats.json"
    return root / ".wavefoundry" / "index" / "index-build-stats.json"


def _read_index_build_stats_file(root: Path, layer: str) -> Optional[dict[str, Any]]:
    """Return persisted build stats from a previous completed build, or None."""
    try:
        path = _index_build_stats_path(root, layer)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_index_build_stats_file(root: Path, layer: str, stats: dict[str, Any]) -> None:
    """Persist build stats — never raises."""
    try:
        path = _index_build_stats_path(root, layer)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(stats), encoding="utf-8")
    except Exception:
        pass


def _parse_finished_build_stats_from_log(
    root: Path,
    layer: str,
    log_path: Path,
    *,
    state_path: Optional[Path] = None,
    fallback_stats: Optional[dict[str, Any]] = None,
) -> Optional[tuple[dict[str, Any], float]]:
    """Return parsed build stats plus the log mtime, or None if the log is not terminal."""
    if not isinstance(root, Path):
        return None
    try:
        active = _index_build_active(root, layer)
    except Exception:
        active = False
    if active or not log_path.exists():
        return None

    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not log_text:
        return None
    if not (
        re.search(r"done\s*[—-]+\s*\d+\s+files? indexed,\s*\d+\s+doc chunks?,\s*\d+\s+code chunks?", log_text)
        or re.search(r"index is up to date", log_text)
    ):
        return None

    files_indexed: Optional[int] = None
    doc_chunks: Optional[int] = None
    code_chunks: Optional[int] = None
    m = re.search(r"done\s*[—-]+\s*(\d+)\s+files? indexed,\s*(\d+)\s+doc chunks?,\s*(\d+)\s+code chunks?", log_text)
    if m:
        files_indexed, doc_chunks, code_chunks = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if files_indexed is None:
        return None

    prev_state: dict[str, Any] = {}
    if state_path is not None:
        try:
            if state_path.exists():
                prev_state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            prev_state = {}
    if not prev_state and isinstance(fallback_stats, dict):
        prev_state = dict(fallback_stats)

    started_at = prev_state.get("started_at")
    try:
        finished_ts = log_path.stat().st_mtime
    except OSError:
        finished_ts = None
    elapsed = (
        int(float(finished_ts) - float(started_at))
        if finished_ts is not None and isinstance(started_at, (int, float))
        else prev_state.get("elapsed_seconds") if isinstance(prev_state.get("elapsed_seconds"), int) else None
    )
    stats = {
        "elapsed_seconds": elapsed,
        "files_indexed": files_indexed,
        "doc_chunks": doc_chunks,
        "code_chunks": code_chunks,
        "built_at": (
            datetime.datetime.utcfromtimestamp(finished_ts).isoformat() + "Z"
            if finished_ts is not None else prev_state.get("built_at")
        ),
        "content": prev_state.get("content"),
        "mode": "rebuild" if prev_state.get("full") else prev_state.get("mode", "update"),
    }
    return stats, float(finished_ts or 0.0)


def _refresh_index_build_stats_from_finished_log(
    root: Path,
    layer: str,
    *,
    log_path: Optional[Path] = None,
    state_path: Optional[Path] = None,
    fallback_stats: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Persist build stats from a finished build log, if available."""
    candidate_log = log_path or _index_build_log_path(root, layer)
    parsed = _parse_finished_build_stats_from_log(
        root,
        layer,
        candidate_log,
        state_path=state_path or _index_build_state_path(root, layer),
        fallback_stats=fallback_stats,
    )
    if parsed is None:
        return None
    stats, _ = parsed
    _write_index_build_stats_file(root, layer, stats)
    return stats


def _refresh_index_build_stats_from_finished_logs(root: Path, layer: str) -> Optional[dict[str, Any]]:
    """Persist build stats from the freshest finished build log for a layer."""
    if not isinstance(root, Path):
        return None
    try:
        active = _index_build_active(root, layer)
    except Exception:
        active = False
    if active:
        return None

    fallback_stats = _read_index_build_stats_file(root, layer) or {}
    candidates: list[tuple[Path, Optional[Path]]] = []
    if layer == "project":
        candidates.append((_project_background_build_log_path(root), None))
    candidates.append((_index_build_log_path(root, layer), _index_build_state_path(root, layer)))

    best_stats: Optional[dict[str, Any]] = None
    best_ts = -1.0
    for candidate_log, candidate_state in candidates:
        parsed = _parse_finished_build_stats_from_log(
            root,
            layer,
            candidate_log,
            state_path=candidate_state,
            fallback_stats=fallback_stats,
        )
        if parsed is None:
            continue
        stats, finished_ts = parsed
        if finished_ts >= best_ts:
            best_ts = finished_ts
            best_stats = stats

    if best_stats is None:
        return None
    _write_index_build_stats_file(root, layer, best_stats)
    return best_stats


def _index_build_active(root: Path, layer: str) -> bool:
    """Return True if a wave_index_build-spawned process is currently running."""
    state_path = _index_build_state_path(root, layer)
    if not state_path.exists():
        return False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    pid = state.get("pid")
    if isinstance(pid, int) and _pid_is_running(pid):
        return True
    # Brief throttle covers the Popen → indexer lock-acquire window (~1-2s cold start).
    # Reuses BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS (15s) — same race condition.
    started_at = state.get("started_at")
    if isinstance(started_at, (int, float)):
        import time
        if (time.time() - float(started_at)) < BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS:
            return True
    return False


def run_index_rebuild(
    root: Path,
    *,
    content: str = "docs",
    full: bool = False,
    layer: str = "project",
) -> dict:
    """Spawn indexer.py as a background process and return immediately with pre-build stats.

    The indexer runs detached; stdout/stderr are written to ``index-build.log`` in the
    index directory. Exposed as MCP ``wave_index_build`` with ``mode='update'|'rebuild'``.
    """
    import subprocess
    import time
    if content not in {"docs", "code", "all"}:
        raise ValueError(f"Unsupported content '{content}'.")
    if layer not in {"project", "framework"}:
        raise ValueError(f"Unsupported layer '{layer}'.")
    if layer == "framework" and content != "docs":
        raise ValueError("Framework index rebuild only supports content 'docs'.")

    if _index_build_active(root, layer):
        log_path = _index_build_log_path(root, layer)
        pre_stats = _read_index_rebuild_stats(root, layer)
        _index_label = {"docs": "docs/seed", "code": "code", "all": "docs/seed + code"}.get(content, content)
        return {
            "passed": True,
            "already_running": True,
            "notice": (
                f"An index build for the {layer} layer is already in progress. "
                f"Watch progress: {log_path}"
            ),
            "content": content,
            "full": full,
            "mode": "rebuild" if full else "update",
            "index_scope": "full_rebuild" if full else "incremental_update",
            "layer": layer,
            "stats": pre_stats,
            "log": str(log_path),
        }

    scripts_dir = Path(__file__).resolve().parent
    include_prefixes = _workflow_project_include_prefixes(root) if layer == "project" else {"docs": (), "code": ()}
    python_exec = _preferred_python()

    if layer == "project" and content == "all":
        script = scripts_dir / "setup_index.py"
        cmd = [python_exec, str(script), "--root", str(root), "--include-code", "--verbose"]
    else:
        script = scripts_dir / "indexer.py"
        cmd = [python_exec, str(script), "--root", str(root), "--content", content, "--verbose"]
    if layer == "framework":
        cmd.extend([
            "--index-dir", ".wavefoundry/framework/index",
            "--include-prefix", ".wavefoundry/framework",
            "--no-ignore-files",
        ])
    elif layer == "project" and content in {"docs", "code"}:
        configured_prefixes = include_prefixes["docs"] if content == "docs" else include_prefixes["code"]
        for prefix in configured_prefixes:
            cmd.extend(["--project-include-prefix", prefix])
    if full:
        cmd.append("--full")

    pre_stats = _read_index_rebuild_stats(root, layer)
    _index_label = {"docs": "docs/seed", "code": "code", "all": "docs/seed + code"}.get(content, content)
    _file_count = pre_stats.get("files_total", "?")

    if not full and _index_is_up_to_date(root, layer, content):
        return {
            "passed": True,
            "already_running": False,
            "up_to_date": True,
            "notice": f"Index is up to date — no rebuild needed.",
            "content": content,
            "full": False,
            "mode": "update",
            "index_scope": "incremental_update",
            "layer": layer,
            "stats": pre_stats,
        }

    # Persist stats from the previous completed build before overwriting the log.
    state_path = _index_build_state_path(root, layer)
    log_path = _index_build_log_path(root, layer)
    prev_log_text = ""
    if log_path.exists():
        try:
            prev_log_text = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    if prev_log_text:
        _m = re.search(
            r"done\s*[—-]+\s*(\d+)\s+files? indexed,\s*(\d+)\s+doc chunks?,\s*(\d+)\s+code chunks?",
            prev_log_text,
        )
        if _m:
            _prev_state: dict[str, Any] = {}
            try:
                _prev_state = json.loads(_index_build_state_path(root, layer).read_text(encoding="utf-8"))
            except Exception:
                pass
            _prev_started = _prev_state.get("started_at")
            _finished_ts: Optional[float] = None
            try:
                _finished_ts = log_path.stat().st_mtime
            except OSError:
                pass
            _elapsed = (
                int(_finished_ts - float(_prev_started))
                if _finished_ts is not None and isinstance(_prev_started, (int, float))
                else None
            )
            _write_index_build_stats_file(root, layer, {
                "elapsed_seconds": _elapsed,
                "files_indexed": int(_m.group(1)),
                "doc_chunks": int(_m.group(2)),
                "code_chunks": int(_m.group(3)),
                "built_at": (
                    datetime.datetime.utcfromtimestamp(_finished_ts).isoformat() + "Z"
                    if _finished_ts is not None else None
                ),
                "content": _prev_state.get("content", content),
                "mode": "rebuild" if _prev_state.get("full") else "update",
            })

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "w", encoding="utf-8")  # noqa: SIM115
    try:
        kwargs: dict[str, Any] = {
            "stdout": log_file,
            "stderr": log_file,
            "stdin": subprocess.DEVNULL,
            "cwd": str(root),
            "env": {
                **os.environ,
                "PROJECT_ROOT": str(root),
                "WAVEFOUNDRY_INDEX_BUILD_STATE_PATH": str(state_path),
            },
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(cmd, **kwargs)
    finally:
        log_file.close()
    state_path.write_text(
        json.dumps({"pid": proc.pid, "started_at": time.time(), "content": content, "layer": layer, "full": full}),
        encoding="utf-8",
    )

    _build_stats = _read_index_build_stats_file(root, layer)
    _timing_hint = ""
    if _build_stats and isinstance(_build_stats.get("elapsed_seconds"), int):
        _mins = round(_build_stats["elapsed_seconds"] / 60)
        _prev_files = _build_stats.get("files_indexed", "?")
        _timing_hint = f" Last build took ~{_mins} minute{'s' if _mins != 1 else ''} for {_prev_files} files — expect similar."

    if full:
        notice = (
            f"Rebuilding {_index_label} index ({layer} layer) — {_file_count} source files. "
            f"The index is being built locally and may take 5–10 minutes depending on repository size."
            f"{_timing_hint} "
            f"Watch progress: {log_path}"
        )
    else:
        notice = (
            f"Updating {_index_label} index ({layer} layer) — scanning for changes. "
            f"The index is being built locally and may take 5–10 minutes depending on repository size."
            f"{_timing_hint} "
            f"Watch progress: {log_path}"
        )

    mode_label = "rebuild" if full else "update"
    return {
        "passed": True,
        "already_running": False,
        "notice": notice,
        "content": content,
        "full": full,
        "mode": mode_label,
        "index_scope": "full_rebuild" if full else "incremental_update",
        "layer": layer,
        "stats": pre_stats,
        "log": str(log_path),
        "pid": proc.pid,
    }


def docs_search_response(index: WaveIndex, query: str, kind: str = "", limit: int = 7, tags: Optional[list] = None) -> dict[str, Any]:
    k = (kind or "").strip().lower()
    n = max(1, min(int(limit), 20))  # clamp to [1, 20]
    if k and k not in DOCS_SEARCH_KINDS:
        allowed = ", ".join(sorted(DOCS_SEARCH_KINDS))
        return _response(
            "error",
            {"query": query, "kind": kind, "results": []},
            diagnostics=[
                _diagnostic(
                    "invalid_arguments",
                    f"Unsupported docs_search kind {kind!r}. Allowed: {allowed}, or omit kind.",
                    recovery_tools=["wave_help"],
                    recovery_usage="wave_help(goal='search_docs')",
                )
            ],
            next_tools=["wave_help"],
            usage=f"docs_search(query={query!r}, kind='doc')",
        )
    diagnostics: list[dict[str, Any]] = []
    search_mode = "semantic"
    results: list[dict[str, Any]] = []
    fallback_reason = ""
    reranked = False
    try:
        # Attempt semantic search; exception handlers below switch to lexical fallback.
        results, reranked = index.search_docs(query, kind=k or None, top_n=n, tags=tags or None)
    except SemanticModelUnavailableOfflineError as exc:
        search_mode = "lexical_fallback"
        fallback_reason = "semantic_model_unavailable_offline"
        diagnostics.append(
            _diagnostic(
                "semantic_model_unavailable_offline",
                str(exc),
                recovery_tools=["wave_help"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root .",
            )
        )
        results = index.search_docs_lexical(query, kind=k or None, top_n=n)
    except IndexNotReadyError as exc:
        search_mode = "lexical_fallback"
        fallback_reason = "index_not_ready"
        diagnostics.append(
            _diagnostic(
                "index_not_ready",
                str(exc),
                recovery_tools=["wave_help"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root .",
            )
        )
        try:
            results = index.search_docs_lexical(query, kind=k or None, top_n=n)
        except Exception:
            results = []
    if not results:
        if search_mode == "lexical_fallback":
            diagnostics.append(
                _diagnostic(
                    "no_results",
                    f"No document results found for query '{query}' in lexical fallback mode.",
                    recovery_tools=["wave_help"],
                    recovery_usage="wave_help(goal='search_docs')",
                )
            )
        else:
            diagnostics.append(
                _diagnostic(
                    "no_results",
                    f"No document results found for query '{query}'.",
                    recovery_tools=["wave_help"],
                    recovery_usage="wave_help(goal='search_docs')",
                )
            )
        _mode = "lexical" if search_mode != "semantic" else "semantic"
        return _response(
            "ok",
            {"query": query, "kind": k, "mode": _mode, "search_mode": search_mode, "reranked": reranked, "results": []},
            diagnostics=diagnostics,
            next_tools=["wave_help"],
            usage=f"docs_search(query={query!r})",
        )
    _mode = "lexical" if search_mode != "semantic" else "semantic"
    return _response(
        "ok",
        {
            "query": query,
            "kind": k,
            "mode": _mode,
            "search_mode": search_mode,
            "reranked": reranked,
            "results": [_search_result("doc", result) for result in results],
        },
        diagnostics=diagnostics,
        next_tools=["seed_get", "wave_get_prompt"],
        usage=f"seed_get(name={results[0]['path']!r})" if results[0].get("kind") == "seed" else "",
    )


def code_search_response(index: WaveIndex, query: str, language: str = "", limit: int = 7, kind: Optional[str] = None, max_per_file: Optional[int] = None, tags: Optional[list] = None) -> dict[str, Any]:
    n = max(1, min(int(limit), 20))  # clamp to [1, 20]

    # Resolve language input → either a category (set of langs) or a single canonical name.
    category_langs: Optional[frozenset] = None
    if language:
        if language in _LANG_CATEGORIES:
            # Category match — expand to set of canonical language names.
            category_langs = _LANG_CATEGORIES[language]
        else:
            # Try extension normalization (e.g. "tsx" or ".tsx" → "typescript").
            norm = language.lstrip(".")
            as_ext = f".{norm}"
            if as_ext in _EXT_TO_LANG:
                language = _EXT_TO_LANG[as_ext]

    # Build response metadata fields.
    if category_langs is not None:
        lang_resolved: Optional[list[str]] = sorted(category_langs)
        lang_exts: Optional[list[str]] = sorted({
            ext for lang in category_langs for ext in _LANG_TO_EXTS.get(lang, [])
        })
    else:
        lang_resolved = None
        lang_exts = _LANG_TO_EXTS.get(language) if language else None

    def _data(results: list, reranked: bool = False) -> dict:
        d: dict[str, Any] = {"query": query, "language": language or None, "reranked": reranked, "results": results}
        if lang_resolved is not None:
            d["language_resolved"] = lang_resolved
        d["language_extensions"] = lang_exts
        return d

    reranked = False
    try:
        if category_langs is not None:
            # Fetch unfiltered results then post-filter to the category set.
            raw, reranked = index.search_code(query, language=None, top_n=n * len(category_langs), kind=kind, max_per_file=max_per_file, tags=tags or None)
            results = [r for r in raw if r.get("language") in category_langs][:n]
        else:
            results, reranked = index.search_code(query, language=language or None, top_n=n, kind=kind, max_per_file=max_per_file, tags=tags or None)
    except SemanticModelUnavailableOfflineError as exc:
        return _response(
            "error",
            _data([]),
            diagnostics=[
                _diagnostic(
                    "semantic_model_unavailable_offline",
                    str(exc),
                    recovery_tools=["wave_help"],
                    recovery_usage="python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root . --include-code",
                )
            ],
            next_tools=["wave_help"],
            usage="wave_help(goal='search_code')",
        )
    except IndexNotReadyError as exc:
        return _response(
            "error",
            _data([]),
            diagnostics=[
                _diagnostic(
                    "index_not_ready",
                    str(exc),
                    recovery_tools=["wave_help"],
                    recovery_usage="python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root . --include-code",
                )
            ],
            next_tools=["wave_help"],
            usage="wave_help(goal='search_code')",
        )
    if not results:
        return _response(
            "ok",
            _data([], reranked=reranked),
            diagnostics=[
                _diagnostic(
                    "no_results",
                    f"No code results found for query '{query}'.",
                    recovery_tools=["wave_help"],
                    recovery_usage="wave_help(goal='search_code')",
                )
            ],
            next_tools=["wave_help"],
            usage=f"code_search(query={query!r})",
        )
    return _response(
        "ok",
        _data([_search_result("code", result) for result in results], reranked=reranked),
        next_tools=["wave_help"],
        usage=f"code_search(query={query!r}, language={language!r})" if language else "",
    )


def seed_get_response(index: WaveIndex, name: str) -> dict[str, Any]:
    try:
        chunk = index.get_seed(name)
    except IndexNotReadyError as exc:
        return _response(
            "error",
            {"name": name},
            diagnostics=[
                _diagnostic(
                    "index_not_ready",
                    str(exc),
                    recovery_tools=["wave_help"],
                    recovery_usage="python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root .",
                )
            ],
            next_tools=["wave_help"],
            usage="wave_help(goal='search_docs')",
        )
    if chunk is None:
        return _response(
            "ok",
            {"name": name, "seed": None},
            diagnostics=[
                _diagnostic(
                    "seed_not_found",
                    f"No seed found matching '{name}'.",
                    recovery_tools=["docs_search"],
                    recovery_usage=f"docs_search(query={name!r}, kind='seed')",
                )
            ],
            next_tools=["docs_search"],
            usage=f"docs_search(query={name!r}, kind='seed')",
        )
    return _response(
        "ok",
        {
            "name": name,
            "seed": {
                "result_id": _result_id("seed", chunk),
                "path": chunk["path"],
                "trust_label": TRUSTED_FRAMEWORK,
                "content": chunk["text"],
            },
        },
        next_tools=["wave_help"],
        usage=f"docs_search(query={name!r}, kind='seed')",
    )


def _detect_wave_status_drift(root: Path, wave: dict) -> list[dict[str, Any]]:
    """Compare wave.md change statuses against actual change doc files.

    Returns a list of drift entries: ``{"change_id": ..., "wave_md_status": ..., "file_status": ...}``
    for any change whose status differs between wave.md and its change doc file.
    """
    drifts: list[dict[str, Any]] = []
    wave_md_path = Path(wave["path"])
    wave_dir = wave_md_path.parent
    for change in wave.get("changes", []):
        cid = change["id"]
        wave_md_status = change["status"]
        # Search for the change doc in the wave folder
        for p in sorted(wave_dir.rglob("*.md")):
            if p.name == "wave.md":
                continue
            if cid.lower() in p.stem.lower():
                try:
                    text = p.read_text(encoding="utf-8")
                except OSError:
                    continue
                m = _CHANGE_STATUS_PATTERN.search(text)
                if m:
                    file_status = m.group(1)
                    if file_status.strip().lower() != wave_md_status.strip().lower():
                        drifts.append({
                            "change_id": cid,
                            "wave_md_status": wave_md_status,
                            "file_status": file_status,
                        })
                break
    return drifts


_WAVE_CURRENT_NEXT_ACTION = {
    "active": "implement_wave",
    "implementing": "close_wave",
    "planned": "prepare_wave",
    "paused": "resume_wave",
}


def _wave_current_sort_key(wave: dict) -> tuple[int, str]:
    """Sort key: active/implementing (0), planned (1), paused (2), other (3); then by wave_id."""
    priority = {"active": 0, "implementing": 0, "planned": 1, "paused": 2}
    return (priority.get(wave["status"], 3), wave.get("wave_id", ""))


def wave_current_response(root: Path, cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    all_waves = cache.list_waves_cached() if cache else list_waves(root)
    open_waves = [w for w in all_waves if w["status"] != "closed"]
    open_waves.sort(key=_wave_current_sort_key)
    entries = [
        {**w, "next_action": _WAVE_CURRENT_NEXT_ACTION.get(w["status"], "prepare_wave")}
        for w in open_waves
    ]
    if not entries:
        return _response(
            "ok",
            {"waves": []},
            diagnostics=[
                _diagnostic(
                    "no_active_wave",
                    "No active, planned, or paused wave found.",
                    recovery_tools=["wave_list_waves"],
                    recovery_usage="wave_list_waves()",
                )
            ],
            next_tools=["wave_list_waves", "wave_list_plans"],
            usage="wave_list_waves()",
        )
    # Drift detection only runs against the active wave (if present) — that's the only
    # wave where in-flight Change Status drift is meaningful.
    diagnostics: list[dict[str, Any]] = []
    active_entry = entries[0] if entries[0]["status"] in ("active", "implementing") else None
    if active_entry is not None:
        try:
            drifts = _detect_wave_status_drift(root, active_entry)
            if drifts:
                drift_summary = "; ".join(f"{d['change_id']}: wave.md={d['wave_md_status']!r} vs file={d['file_status']!r}" for d in drifts)
                diagnostics.append(
                    _diagnostic(
                        "change_status_drift",
                        f"Change status drift detected — wave.md and change doc files disagree for: {drift_summary}. Update wave.md Change Status fields to match the actual change docs.",
                        recovery_tools=["wave_get_change", "wave_validate"],
                        recovery_usage=f"wave_get_change(change_id={drifts[0]['change_id']!r})",
                    )
                )
        except Exception:
            pass  # Drift detection is advisory; never let it block the response
    first_entry = entries[0]
    usage = f"wave_get_change(change_id={first_entry['changes'][0]['id']!r})" if first_entry.get("changes") else ""
    return _response(
        "ok",
        {"waves": entries},
        diagnostics=diagnostics,
        next_tools=["wave_get_change"],
        usage=usage,
    )


def wave_list_waves_response(root: Path, limit: int = 50, cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    n = max(1, min(int(limit), 200))  # clamp to [1, 200]
    all_waves = cache.list_waves_cached() if cache else list_waves(root)
    has_more = len(all_waves) > n
    waves = all_waves[:n]
    return _response(
        "ok",
        {"waves": waves, "total": len(all_waves), "has_more": has_more},
        diagnostics=[] if waves else [_diagnostic("no_waves", "No waves found.")],
        next_tools=["wave_current"] if waves else ["wave_list_plans"],
        usage="wave_current()" if waves else "wave_list_plans()",
    )


def wave_list_plans_response(root: Path, limit: int = 50, cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    n = max(1, min(int(limit), 200))  # clamp to [1, 200]
    all_plans = cache.list_plans_cached() if cache else list_plans(root)
    has_more = len(all_plans) > n
    plans = all_plans[:n]
    return _response(
        "ok",
        {"plans": plans, "total": len(all_plans), "has_more": has_more},
        diagnostics=[] if plans else [_diagnostic("no_plans", "No plan docs found.")],
        next_tools=["wave_new_feature", "wave_current"] if plans else ["wave_help"],
        usage="wave_help(goal='plan_feature')",
    )


def wave_get_change_response(root: Path, change_id: str = "", wave_id: str = "") -> dict[str, Any]:
    """Look up a single change doc by ID, or return all changes for a wave.

    When ``wave_id`` is provided and ``change_id`` is omitted (or empty), returns all
    admitted change docs for that wave in ``data.changes``, each with ``id``, ``status``,
    ``path``, and ``content``.  Content per change is capped at 300 lines to avoid
    overly large responses for waves with many large change docs.
    """
    wave_id_s = (wave_id or "").strip()
    change_id_s = (change_id or "").strip()

    # Bulk mode: wave_id provided, no specific change_id
    if wave_id_s and not change_id_s:
        wave_md = _find_wave_md(root, wave_id_s)
        if wave_md is None:
            return _response(
                "ok",
                {"wave_id": wave_id_s, "changes": []},
                diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id_s}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")],
                next_tools=["wave_list_waves"],
                usage="wave_list_waves()",
            )
        wave_text = wave_md.read_text(encoding="utf-8")
        admitted_ids = _extract_change_ids_from_wave_text(wave_text)
        changes: list[dict[str, Any]] = []
        wave_dir = wave_md.parent
        _MAX_CONTENT_LINES = 300
        for cid in admitted_ids:
            # Prefer wave folder; fall back to docs/plans
            doc_path: Optional[Path] = None
            for p in sorted(wave_dir.rglob("*.md")):
                if p.name != "wave.md" and cid.lower() in p.stem.lower():
                    doc_path = p
                    break
            if doc_path is None:
                doc_path_candidate = root / "docs" / "plans" / f"{cid}.md"
                if doc_path_candidate.exists():
                    doc_path = doc_path_candidate
            if doc_path is not None and doc_path.exists():
                try:
                    content_lines = doc_path.read_text(encoding="utf-8").splitlines()
                except OSError:
                    content_lines = []
                truncated = len(content_lines) > _MAX_CONTENT_LINES
                content = "\n".join(content_lines[:_MAX_CONTENT_LINES])
                if truncated:
                    content += f"\n\n[... truncated at {_MAX_CONTENT_LINES} lines. Use code_read(path=...) for the full file.]"
                # Extract change status from doc
                doc_status_m = _CHANGE_STATUS_PATTERN.search(content)
                doc_status = doc_status_m.group(1) if doc_status_m else "unknown"
                changes.append({
                    "id": cid,
                    "status": doc_status,
                    "path": _repo_rel(root, doc_path),
                    "content": content,
                })
            else:
                changes.append({"id": cid, "status": "unknown", "path": None, "content": None})
        return _response(
            "ok",
            {"wave_id": wave_id_s, "count": len(changes), "changes": changes},
            next_tools=["wave_validate", "wave_current"],
            usage="wave_validate()",
        )

    # Single lookup mode (original behavior)
    text = get_change(root, change_id_s)
    if text is None:
        return _response(
            "ok",
            {"change_id": change_id_s, "change": None},
            diagnostics=[
                _diagnostic(
                    "change_not_found",
                    f"No change doc found matching '{change_id_s}'.",
                    recovery_tools=["wave_list_plans", "wave_current"],
                    recovery_usage="wave_list_plans()",
                )
            ],
            next_tools=["wave_list_plans", "wave_current"],
            usage="wave_list_plans()",
        )
    return _response(
        "ok",
        {
            "change_id": change_id_s,
            "change": {
                "content": text,
                "trust_label": TRUSTED_PROJECT_METADATA,
            },
        },
        next_tools=["wave_validate"],
        usage="wave_validate()",
    )


def wave_get_prompt_response(root: Path, shortcut: str, cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    text = cache.get_prompt_text_cached(shortcut) if cache else get_prompt(root, shortcut)
    if text is None:
        return _response(
            "ok",
            {"shortcut": shortcut, "prompt": None},
            diagnostics=[
                _diagnostic(
                    "prompt_not_found",
                    f"No prompt found matching '{shortcut}'.",
                    recovery_tools=["docs_search"],
                    recovery_usage=f"docs_search(query={shortcut!r}, kind='prompt')",
                )
            ],
            next_tools=["docs_search"],
            usage=f"docs_search(query={shortcut!r}, kind='prompt')",
        )
    return _response(
        "ok",
        {
            "shortcut": shortcut,
            "prompt": {
                "content": text,
                "trust_label": UNTRUSTED_PROJECT_CONTENT,
            },
        },
        next_tools=["wave_validate"],
        usage="wave_validate()",
    )


def _parse_wave_address(address: str) -> Optional[dict[str, Any]]:
    """Parse ``doc:``, ``code:``, or ``seed:`` anchor strings from search tools and the spec."""
    s = (address or "").strip()
    if not s:
        return None
    m = re.match(r"^(doc|code|seed):(.+)$", s, flags=re.DOTALL)
    if not m:
        return None
    scheme, rest = m.group(1), m.group(2)
    rest = rest.strip().replace("\\", "/")
    if scheme == "code":
        m2 = re.match(r"^(.+):L(\d+)-L(\d+)$", rest)
        if m2:
            return {
                "scheme": "code",
                "path": m2.group(1).strip().replace("\\", "/"),
                "section": None,
                "line_start": int(m2.group(2)),
                "line_end": int(m2.group(3)),
            }
        return {
            "scheme": "code",
            "path": rest,
            "section": None,
            "line_start": None,
            "line_end": None,
        }
    if "#" in rest:
        path_part, sec = rest.split("#", 1)
        return {
            "scheme": scheme,
            "path": path_part.strip().replace("\\", "/"),
            "section": sec.strip(),
            "line_start": None,
            "line_end": None,
        }
    return {
        "scheme": scheme,
        "path": rest,
        "section": None,
        "line_start": None,
        "line_end": None,
    }


def _read_map_excerpt(
    path: Path,
    line_start: Optional[int],
    line_end: Optional[int],
    max_chars: int = 1600,
) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if line_start is not None and line_end is not None:
        lines = text.splitlines()
        s_idx = max(1, line_start) - 1
        e_idx = min(len(lines), line_end)
        chunk = "\n".join(lines[s_idx:e_idx])
        return chunk[:max_chars]
    return text[:max_chars]


def _index_chunk_matching_address(index: WaveIndex, address: str, parsed: dict[str, Any]) -> Optional[dict[str, Any]]:
    try:
        index._ensure_loaded()
    except (IndexNotReadyError, OSError, ValueError, Exception):
        return None
    scheme = parsed["scheme"]
    want = address.strip()
    path = (parsed.get("path") or "").replace("\\", "/").replace("'", "''")
    # Determine which Lance table(s) to scan and which prefix(es) to match.
    if scheme == "code":
        table_prefixes = [(getattr(index, "_code_lance_table", None), "code")]
    elif scheme == "seed":
        table_prefixes = [
            (getattr(index, "_docs_lance_table", None), "seed"),
            (getattr(index, "_docs_lance_table", None), "doc"),
        ]
    else:
        table_prefixes = [(getattr(index, "_docs_lance_table", None), "doc")]
    seen_tables: set[int] = set()
    for table, prefix in table_prefixes:
        if table is None:
            continue
        table_id = id(table)
        if table_id in seen_tables:
            continue
        seen_tables.add(table_id)
        try:
            where = f"path = '{path}'" if path else None
            q = table.search()
            if where:
                q = q.where(where, prefilter=True)
            rows = q.to_list()
        except Exception:
            rows = []
        for row in rows:
            ch = {k: v for k, v in row.items() if k != "vector"}
            if _result_id(prefix, ch) == want:
                return ch
    return None


def wave_map_response(root: Path, address: str, index: WaveIndex) -> dict[str, Any]:
    """Resolve a stable anchor string to paths, trust metadata, and optional excerpts."""
    addr = (address or "").strip()
    if not addr:
        return _response(
            "error",
            {"address": address},
            diagnostics=[
                _diagnostic(
                    "invalid_address",
                    "wave_map requires a non-empty anchor (e.g. doc:docs/README.md#intro).",
                    recovery_tools=["docs_search", "wave_help"],
                    recovery_usage="docs_search(query='topic')",
                )
            ],
            next_tools=["docs_search", "wave_help"],
            usage="wave_map(address='doc:docs/README.md')",
        )
    parsed = _parse_wave_address(addr)
    if parsed is None:
        return _response(
            "error",
            {"address": addr},
            diagnostics=[
                _diagnostic(
                    "invalid_address",
                    "Anchor must start with doc:, code:, or seed: and use repo-relative paths.",
                    recovery_tools=["wave_help"],
                    recovery_usage="wave_help(goal='search_docs')",
                )
            ],
            next_tools=["wave_help"],
            usage="wave_map(address='doc:docs/plans/1234-feat x.md')",
        )
    resolved, err = resolve_path_under_root(root, parsed["path"])
    if err is not None:
        return _response(
            "error",
            {"address": addr, "parsed": parsed},
            diagnostics=[err],
            next_tools=["wave_validate", "wave_current"],
            usage="wave_validate()",
        )
    assert resolved is not None
    root_r = root.resolve()
    rel = str(resolved.relative_to(root_r)).replace("\\", "/")
    chunk = _index_chunk_matching_address(index, addr, parsed)
    kind_for_trust = "seed" if parsed["scheme"] == "seed" else (str(chunk.get("kind") or "") if chunk else "")
    trust = _trust_label(rel, kind=kind_for_trust)
    excerpt = ""
    if chunk:
        excerpt = str(chunk.get("text") or "")[:1600]
    if not excerpt:
        excerpt = _read_map_excerpt(resolved, parsed.get("line_start"), parsed.get("line_end"))
    data: dict[str, Any] = {
        "address": addr,
        "scheme": parsed["scheme"],
        "path": rel,
        "section": parsed.get("section"),
        "line_start": parsed.get("line_start"),
        "line_end": parsed.get("line_end"),
        "file_exists": resolved.is_file(),
        "trust_label": trust,
        "index_match": chunk is not None,
        "excerpt": excerpt,
    }
    next_tools = ["wave_validate", "docs_search"]
    if parsed["scheme"] in ("doc", "seed") and chunk and chunk.get("kind") == "seed":
        next_tools = ["seed_get", "wave_validate"]
    return _response(
        "ok",
        data,
        next_tools=next_tools,
        usage="wave_validate()",
    )


def _find_wave_md(root: Path, wave_id_or_prefix: str) -> Optional[Path]:
    token = (wave_id_or_prefix or "").strip().lower()
    if not token:
        return None
    waves_root = root / "docs" / "waves"
    if not waves_root.exists():
        return None
    matches: list[Path] = []
    for wave_md in waves_root.glob("*/wave.md"):
        try:
            parsed = _parse_wave_record(wave_md)
            wave_id = str(parsed.get("wave_id") or wave_md.parent.name).lower()
        except OSError:
            continue
        if token in wave_id:
            matches.append(wave_md)
    if len(matches) != 1:
        return None
    return matches[0]


def _extract_change_ids_from_wave_text(text: str) -> list[str]:
    return _CHANGE_ID_PATTERN.findall(text)


def _resolve_change_doc_matches(root: Path, change_id_prefix: str) -> list[dict[str, Any]]:
    token = (change_id_prefix or "").strip().lower()
    if not token:
        return []
    matches: list[dict[str, Any]] = []
    search_dirs = [root / "docs" / "plans", root / "docs" / "waves"]
    for base in search_dirs:
        if not base.exists():
            continue
        for p in base.rglob("*.md"):
            if token not in p.stem.lower():
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except OSError:
                continue
            change_match = _CHANGE_ID_PATTERN.search(text)
            canonical_change_id = change_match.group(1) if change_match else p.stem
            matches.append(
                {
                    "path": str(p.relative_to(root)).replace("\\", "/"),
                    "change_id": canonical_change_id,
                    "content": text,
                }
            )
    return matches


_REVIEW_EVIDENCE_MARKERS = ("## Review Evidence", "## Review Signoff Evidence")
_PREPARE_REVIEW_EVIDENCE_MARKER = "## Prepare Review Evidence"
_SIGNOFF_TOKENS = ("sign-off", "signoff", "approved", "passed", "acceptance", "complete")


def _combined_review_evidence(wave_text: str) -> str:
    """Return raw text (preserves case) of all Review Evidence / Signoff sections."""
    parts: list[str] = []
    for marker in _REVIEW_EVIDENCE_MARKERS:
        idx = wave_text.find(marker)
        if idx == -1:
            continue
        start = idx + len(marker)
        nl = wave_text.find("\n", start)
        if nl != -1:
            start = nl + 1
        tail = wave_text[start:]
        m_end = re.search(r"\n(?=## )", tail)
        body = tail[: m_end.start()] if m_end else tail
        parts.append(body)
    return "\n".join(parts)


def _prepare_review_evidence(wave_text: str) -> str:
    """Return raw text of the ## Prepare Review Evidence section (prepare-phase signoffs)."""
    marker = _PREPARE_REVIEW_EVIDENCE_MARKER
    idx = wave_text.find(marker)
    if idx == -1:
        return ""
    start = idx + len(marker)
    nl = wave_text.find("\n", start)
    if nl != -1:
        start = nl + 1
    tail = wave_text[start:]
    m_end = re.search(r"\n(?=## )", tail)
    return tail[: m_end.start()] if m_end else tail


def _lane_has_signoff_in_evidence(evidence_text: str, lane: str) -> bool:
    """True if some line in the evidence block names the lane and records signoff on that line."""
    lane_l = lane.strip().lower()
    if not lane_l or not evidence_text.strip():
        return False
    for raw in evidence_text.splitlines():
        line = raw.strip().lower()
        if not line or line.startswith("#"):
            continue
        # Skip placeholder lines — e.g. "operator-signoff: <approved when ...>"
        if "<" in line:
            continue
        if lane_l not in line:
            continue
        if any(tok in line for tok in _SIGNOFF_TOKENS):
            return True
    return False


def _lanes_missing_signoff(wave_text: str) -> list[str]:
    """Required review roles from Participants that lack a per-line signoff in Review Evidence."""
    evidence = _combined_review_evidence(wave_text)
    missing: list[str] = []
    for lane in _extract_required_review_lanes(wave_text):
        if not _lane_has_signoff_in_evidence(evidence, lane):
            missing.append(lane)
    return missing


def _review_evidence_has_any_signoff_line(wave_text: str) -> bool:
    """When there are no participant review lanes, still require some recorded signoff in evidence."""
    evidence = _combined_review_evidence(wave_text)
    if not evidence.strip():
        return False
    el = evidence.lower()
    for raw in el.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "<" in line:
            continue
        if any(tok in line for tok in _SIGNOFF_TOKENS):
            return True
    return False


def _update_handoff_wave_ref(existing: str, wave_id: Optional[str]) -> str:
    """Surgically update the Active wave reference and Last verified in session-handoff.md.

    Only the ``**Active wave:**`` line and the ``Last verified:`` metadata field are
    updated.  All other content is preserved unchanged.  If the file is empty or the
    ``**Active wave:**`` pattern is absent, a minimal valid scaffold is written instead.

    Args:
        existing: Current file content (empty string when the file does not exist).
        wave_id: Wave ID to mark as active, or None to clear (renders as ``*(none)*``).
    """
    active_ref = f"`{wave_id}`" if wave_id else "*(none)*"
    today = datetime.date.today().isoformat()

    if not existing.strip():
        status = "active" if wave_id else "idle"
        return (
            "# Session Handoff\n\n"
            "Owner: wave-coordinator\n"
            f"Status: {status}\n"
            f"Last verified: {today}\n\n"
            "## Current Session\n\n"
            f"**Active wave:** {active_ref}\n"
        )

    lines = existing.splitlines(keepends=True)
    found_active = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("**Active wave:**"):
            out.append(f"**Active wave:** {active_ref}\n")
            found_active = True
        elif stripped.startswith("Last verified:"):
            out.append(f"Last verified: {today}\n")
        else:
            out.append(line)

    if not found_active:
        # Active wave line absent — insert it under ## Current Session if that section
        # exists, preserving all other content.  Only fall back to a minimal scaffold
        # if the file has no Current Session section at all.
        result = "".join(out)
        if "## Current Session" in result:
            result = re.sub(
                r"(## Current Session\s*\n+)",
                rf"\1**Active wave:** {active_ref}\n",
                result,
                count=1,
            )
            return result
        # No Current Session section — append one.
        if not result.endswith("\n"):
            result += "\n"
        result += f"\n## Current Session\n\n**Active wave:** {active_ref}\n"
        return result

    return "".join(out)


def _resolve_unique_change_doc(root: Path, change_id: str) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    matches = _resolve_change_doc_matches(root, change_id)
    if not matches:
        return None, _diagnostic("change_not_found", f"No change doc found matching '{change_id}'.", recovery_tools=["wave_list_plans"], recovery_usage="wave_list_plans()")
    if len(matches) > 1:
        return None, _diagnostic("ambiguous_change_id", f"Multiple change docs match '{change_id}'. Use a more specific ID.", recovery_tools=["wave_list_plans"], recovery_usage="wave_list_plans()")
    return matches[0], None


def _wave_change_doc_path(root: Path, wave_md: Path, change_id: str) -> Path:
    return wave_md.parent / f"{change_id}.md"


def _plan_change_doc_path(root: Path, change_id: str) -> Path:
    return root / "docs" / "plans" / f"{change_id}.md"


def _repo_rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def _background_refresh_state_path(root: Path, layer: str) -> Path:
    if layer == "framework":
        return root / ".wavefoundry" / "framework" / "index" / "background-refresh.json"
    return root / ".wavefoundry" / "index" / "background-refresh.json"


def _indexable_refresh_path(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    if not normalized:
        return False
    if normalized.startswith(".wavefoundry/index/") or normalized.startswith(".wavefoundry/framework/index/"):
        return False
    skip_suffixes = {
        ".pyc", ".npy", ".png", ".jpg", ".jpeg", ".gif", ".svg",
        ".ico", ".woff", ".woff2", ".ttf", ".eot", ".zip",
    }
    return Path(normalized).suffix.lower() not in skip_suffixes


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _load_background_refresh_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {}
    try:
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _lock_is_fresh(lock_path: Path) -> bool:
    """Return True if ``lock_path`` exists and its mtime is within the stale threshold."""
    import time as _time

    if not lock_path.exists():
        return False
    try:
        age = _time.time() - lock_path.stat().st_mtime
    except OSError:
        return False
    return age < BACKGROUND_INDEX_LOCK_STALE_SECONDS


def _table_lock_paths(index_dir: Path) -> list[Path]:
    """Return the per-table ``.lock`` file paths for the given index directory."""
    return [index_dir / f"{kind}.lance" / ".lock" for kind in ("docs", "code")]


def _cleanup_stale_table_locks(index_dir: Path) -> list[dict[str, Any]]:
    """Remove dead Lance table lock markers and return cleanup details."""
    import time as _time

    cleaned: list[dict[str, Any]] = []
    for lock_path in _table_lock_paths(index_dir):
        if not lock_path.exists():
            continue
        pid: Optional[int] = None
        try:
            raw_pid = lock_path.read_text(encoding="utf-8").strip()
            pid = int(raw_pid) if raw_pid else None
        except (OSError, ValueError):
            pid = None
        try:
            age = _time.time() - lock_path.stat().st_mtime
        except OSError:
            continue
        pid_dead = pid is None or not _pid_is_running(pid)
        if not pid_dead:
            continue
        try:
            lock_path.unlink()
            removed = True
        except OSError:
            removed = False
        cleaned.append({
            "path": str(lock_path),
            "pid": pid,
            "age_seconds": int(age),
            "reason": "pid_dead",
            "removed": removed,
        })
    return cleaned


def _background_refresh_active(state_path: Path) -> bool:
    # Primary guard: if any per-table .lock file exists and is fresh, a build is actively
    # running — regardless of what the state file says.
    index_dir = state_path.parent
    _cleanup_stale_table_locks(index_dir)
    if any(_lock_is_fresh(p) for p in _table_lock_paths(index_dir)):
        return True

    state = _load_background_refresh_state(state_path)
    pid = state.get("pid")
    started_at = state.get("started_at")
    if isinstance(pid, int) and _pid_is_running(pid):
        return True
    # Short throttle covers the brief window between Popen() and the indexer acquiring
    # its build lock (~1-2 seconds on a cold start).
    if isinstance(started_at, (int, float)):
        import time
        if (time.time() - float(started_at)) < BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS:
            return True
    return False


def _start_background_index_refresh(root: Path, layer: str) -> bool:
    if layer not in {"project", "framework"}:
        return False
    state_path = _background_refresh_state_path(root, layer)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if _background_refresh_active(state_path):
        return False
    indexer = root / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
    if not indexer.exists():
        return False
    import subprocess
    cmd = [_preferred_python(), str(indexer), "--root", str(root)]
    if layer == "framework":
        cmd.extend([
            "--content",
            "docs",
            "--index-dir",
            str(root / ".wavefoundry" / "framework" / "index"),
            "--include-prefix",
            ".wavefoundry/framework",
            "--no-ignore-files",
        ])
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(root),
        start_new_session=True,
    )
    import time
    state_path.write_text(
        json.dumps({"pid": proc.pid, "started_at": time.time(), "layer": layer}),
        encoding="utf-8",
    )
    return True


def _trigger_background_index_refresh_for_paths(root: Path, paths: Iterable[str | Path]) -> dict[str, bool]:
    normalized_paths: list[str] = []
    for path in paths:
        if isinstance(path, Path):
            normalized = _repo_rel(root, path)
        else:
            normalized = str(path).replace("\\", "/")
            while normalized.startswith("./"):
                normalized = normalized[2:]
        if normalized:
            normalized_paths.append(normalized)
    project_needed = any(_indexable_refresh_path(path) and path.startswith("docs/") for path in normalized_paths)
    framework_needed = any(_indexable_refresh_path(path) and path.startswith(".wavefoundry/framework/") for path in normalized_paths)
    return {
        "project": _start_background_index_refresh(root, "project") if project_needed else False,
        "framework": _start_background_index_refresh(root, "framework") if framework_needed else False,
    }


def _change_location_state(root: Path, wave_md: Path, change_id: str) -> dict[str, Any]:
    staged = _plan_change_doc_path(root, change_id)
    wave_path = _wave_change_doc_path(root, wave_md, change_id)
    return {
        "staged_path": staged,
        "wave_path": wave_path,
        "staged_exists": staged.exists(),
        "wave_exists": wave_path.exists(),
    }


def _move_change_doc(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)


_MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def _broken_relative_links_after_relocation(doc_text: str) -> list[str]:
    """Return relative markdown link targets that used ``../waves/`` anchoring.

    When a change doc is relocated from ``docs/plans/`` to a wave folder the
    relative path depth changes.  Links written as ``../waves/<something>`` were
    valid from ``docs/plans/`` but become invalid from the wave folder (which is
    already *inside* ``docs/waves/``).  This helper returns each such link target
    so callers can surface them to the agent as ``broken_links``.
    """
    broken: list[str] = []
    for _text, href in _MARKDOWN_LINK_PATTERN.findall(doc_text):
        if href.startswith("../waves/"):
            broken.append(href)
    return broken


def _change_block_pattern(change_id: str) -> re.Pattern[str]:
    return re.compile(
        rf"\n?Change ID:\s+`{re.escape(change_id)}`\n(?:Previous Change Status:\s+`[^`]+`\n)?Change Status:\s+`[^`]+`\n?",
        re.MULTILINE,
    )


def _missing_required_change_sections(change_text: str) -> list[str]:
    required_headers = [
        "## Rationale",
        "## Requirements",
        "## Scope",
        "## Acceptance Criteria",
        "## Tasks",
        "## AC Priority",
    ]
    return [hdr for hdr in required_headers if hdr not in change_text]


def _extract_required_review_lanes(wave_text: str) -> list[str]:
    lanes: list[str] = []
    in_participants = False
    for raw in wave_text.splitlines():
        line = raw.strip()
        if line.startswith("## Participants"):
            in_participants = True
            continue
        if in_participants and line.startswith("## "):
            break
        if not in_participants:
            continue
        if not line.startswith("|") or line.startswith("|------"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        role, lane = cells[0], cells[1]
        if role.lower() == "role":
            continue
        if "review" not in lane.lower():
            continue
        lanes.append(role)
    # preserve order, dedupe
    out: list[str] = []
    for lane in lanes:
        if lane not in out:
            out.append(lane)
    return out


def _lane_has_signoff(wave_text: str, lane: str) -> bool:
    """Whether ``lane`` has an explicit signoff on the same line in Review Evidence (not global heuristics)."""
    return _lane_has_signoff_in_evidence(_combined_review_evidence(wave_text), lane)


def create_wave(root: Path, slug: str, mode: str = "dry_run") -> dict[str, Any]:
    slug_s = (slug or "").strip()
    mode_s = "create" if mode == "apply" else mode
    if not slug_s:
        raise ValueError("Wave slug must be a non-empty string.")
    if mode_s not in {"dry_run", "create"}:
        raise ValueError(f"Unsupported mode '{mode}'.")
    wave_id = _lifecycle_module().build_id("wave", slug_s, legacy=False)
    wave_dir = root / "docs" / "waves" / wave_id
    wave_md = wave_dir / "wave.md"
    rel_path = str(wave_md.relative_to(root)).replace("\\", "/")
    exists = wave_md.exists()
    if mode_s == "dry_run":
        return {"wave_id": wave_id, "path": rel_path, "mode": mode_s, "created": False, "exists": exists}
    if exists:
        return {"wave_id": wave_id, "path": rel_path, "mode": mode_s, "created": False, "exists": True}
    wave_dir.mkdir(parents=True, exist_ok=True)
    today_iso = datetime.date.today().isoformat()
    wave_md.write_text(
        (
            "# Wave Record\n\n"
            "Owner: Engineering\n"
            "Status: planned\n"
            f"Last verified: {today_iso}\n\n"
            f"wave-id: `{wave_id}`\n"
            f"Title: {slug_s.replace('-', ' ').title()}\n\n"
            "## Changes\n\n"
            "## Wave Summary\n\n"
            "<Describe the purpose and scope of this wave in 1–3 sentences.>\n\n"
            "## Journal Watchpoints\n\n"
            "- <Add any coordination notes, sequencing constraints, or guard requirements here.>\n\n"
            "## Review Evidence\n\n"
            "- operator-signoff: <approved when operator confirms closure>\n\n"
            "## Dependencies\n\n"
            "- No external wave dependencies.\n"
        ),
        encoding="utf-8",
    )
    return {"wave_id": wave_id, "path": rel_path, "mode": mode_s, "created": True, "exists": False}


def wave_create_wave_response(root: Path, slug: str, mode: str = "dry_run", cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    try:
        result = create_wave(root, slug, mode)
    except ValueError as exc:
        return _response(
            "error",
            {"slug": slug, "mode": mode},
            diagnostics=[_diagnostic("invalid_arguments", str(exc), recovery_tools=["wave_help"], recovery_usage="wave_help()")],
            next_tools=["wave_help"],
            usage="wave_help()",
        )
    if cache and result.get("created"):
        cache.invalidate()
    if result.get("created"):
        _trigger_background_index_refresh_for_paths(root, [result["path"]])
    diagnostics: list[dict[str, Any]] = []
    if result["exists"] and not result["created"]:
        diagnostics.append(_diagnostic("already_exists", f"Wave already exists at {result['path']}.", recovery_tools=["wave_current"]))
    return _response(
        "dry_run" if result["mode"] == "dry_run" else "ok",
        result,
        diagnostics=diagnostics,
        next_tools=["wave_list_waves", "wave_current"],
        usage="wave_current()",
    )


def _insert_change_block_into_changes_section(text: str, change_id: str) -> str:
    """Append a ``Change ID:`` block inside the ``## Changes`` section.

    The block is inserted after any existing change blocks in the section, before
    the next ``## `` heading (or end-of-file). When ``## Changes`` is missing
    (e.g., on operator-edited waves), the section is created just before the
    first existing ``## `` heading, or appended to the end of the file if none
    exist. Admission order is preserved by tail-appending within the section.
    """
    block = f"Change ID: `{change_id}`\nChange Status: `planned`\n"
    changes_match = re.search(r"^## Changes[ \t]*\n", text, re.MULTILINE)
    if changes_match is None:
        next_heading = re.search(r"^## ", text, re.MULTILINE)
        section = "## Changes\n\n" + block + "\n"
        if next_heading is None:
            if text and not text.endswith("\n"):
                text += "\n"
            return text + "\n" + section
        return text[:next_heading.start()] + section + text[next_heading.start():]
    section_start = changes_match.end()
    next_heading = re.search(r"^## ", text[section_start:], re.MULTILINE)
    section_end = section_start + next_heading.start() if next_heading else len(text)
    section_body = text[section_start:section_end]
    body_stripped = section_body.rstrip()
    if body_stripped:
        new_section = body_stripped + "\n\n" + block + "\n"
    else:
        new_section = "\n" + block + "\n"
    return text[:section_start] + new_section + text[section_end:]


def wave_add_change_response(
    root: Path,
    wave_id: str,
    change_id: str,
    mode: str = "dry_run",
    cache: Optional[McpRepoCache] = None,
) -> dict[str, Any]:
    mode_s = "create" if (mode or "").strip().lower() == "apply" else (mode or "").strip().lower()
    if mode_s not in {"dry_run", "create"}:
        return _response("error", {"wave_id": wave_id, "change_id": change_id, "mode": mode}, diagnostics=[_diagnostic("invalid_arguments", f"Unsupported mode '{mode}'.")], next_tools=["wave_help"], usage="wave_help()")
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id, "change_id": change_id, "mode": mode_s}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
    change_matches = _resolve_change_doc_matches(root, change_id)
    if not change_matches:
        return _response("error", {"wave_id": wave_id, "change_id": change_id, "mode": mode_s}, diagnostics=[_diagnostic("change_not_found", f"No change doc found matching '{change_id}'.", recovery_tools=["wave_list_plans"], recovery_usage="wave_list_plans()")], next_tools=["wave_list_plans"], usage="wave_list_plans()")
    if len(change_matches) > 1:
        return _response(
            "error",
            {"wave_id": wave_id, "change_id": change_id, "mode": mode_s},
            diagnostics=[
                _diagnostic(
                    "ambiguous_change_id",
                    f"Multiple change docs match '{change_id}'. Use a more specific ID.",
                    recovery_tools=["wave_list_plans"],
                    recovery_usage="wave_list_plans()",
                )
            ],
            next_tools=["wave_list_plans"],
            usage="wave_list_plans()",
        )
    canonical_change_id = str(change_matches[0]["change_id"])
    source_path = root / str(change_matches[0]["path"])
    target_path = _wave_change_doc_path(root, wave_md, canonical_change_id)
    text = wave_md.read_text(encoding="utf-8")
    existing = _extract_change_ids_from_wave_text(text)
    location = _change_location_state(root, wave_md, canonical_change_id)
    if source_path.parent.name != wave_md.parent.name and "docs/waves/" in str(change_matches[0]["path"]).replace("\\", "/") and source_path != target_path:
        return _response(
            "error",
            {"wave_id": wave_id, "change_id": canonical_change_id, "mode": mode_s},
            diagnostics=[
                _diagnostic(
                    "change_already_in_other_wave",
                    f"Change '{canonical_change_id}' already lives in another wave folder at {_repo_rel(root, source_path)}.",
                    recovery_tools=["wave_current", "wave_get_change"],
                    recovery_usage=f"wave_get_change(change_id={canonical_change_id!r})",
                )
            ],
            next_tools=["wave_current", "wave_get_change"],
            usage=f"wave_get_change(change_id={canonical_change_id!r})",
        )
    if canonical_change_id in existing:
        diagnostics = [_diagnostic("already_admitted", f"Change '{canonical_change_id}' is already admitted.")]
        if location["staged_exists"] and location["wave_exists"]:
            diagnostics.append(
                _diagnostic(
                    "duplicate_change_doc_locations",
                    f"Change '{canonical_change_id}' exists in both {_repo_rel(root, location['staged_path'])} and {_repo_rel(root, location['wave_path'])}.",
                    recovery_tools=["wave_prepare", "wave_get_change"],
                    recovery_usage=f"wave_prepare(wave_id={wave_md.parent.name!r}, mode='create')",
                )
            )
            return _response("error", {"wave_id": wave_id, "change_id": canonical_change_id, "mode": mode_s, "updated": False}, diagnostics=diagnostics, next_tools=["wave_prepare", "wave_get_change"], usage=f"wave_prepare(wave_id={wave_md.parent.name!r}, mode='create')")
        return _response(
            "ok",
            {
                "wave_id": wave_id,
                "change_id": canonical_change_id,
                "mode": mode_s,
                "updated": False,
                "relocated": location["wave_exists"],
                "path": _repo_rel(root, location["wave_path"]) if location["wave_exists"] else _repo_rel(root, source_path),
            },
            diagnostics=diagnostics,
            next_tools=["wave_current"],
            usage="wave_current()",
        )
    relocated = source_path == target_path
    if mode_s == "create":
        if target_path.exists() and source_path != target_path:
            return _response(
                "error",
                {"wave_id": wave_id, "change_id": canonical_change_id, "mode": mode_s},
                diagnostics=[
                    _diagnostic(
                        "duplicate_change_doc_locations",
                        f"Target wave doc already exists at {_repo_rel(root, target_path)} while source remains at {_repo_rel(root, source_path)}.",
                        recovery_tools=["wave_prepare", "wave_get_change"],
                        recovery_usage=f"wave_prepare(wave_id={wave_md.parent.name!r}, mode='create')",
                    )
                ],
                next_tools=["wave_prepare", "wave_get_change"],
                usage=f"wave_prepare(wave_id={wave_md.parent.name!r}, mode='create')",
            )
        if source_path != target_path:
            try:
                _move_change_doc(source_path, target_path)
            except OSError as exc:
                return _response(
                    "error",
                    {"wave_id": wave_id, "change_id": canonical_change_id, "mode": mode_s},
                    diagnostics=[
                        _diagnostic(
                            "change_relocation_failed",
                            f"Failed to relocate change doc to {_repo_rel(root, target_path)}: {exc}",
                            recovery_tools=["wave_get_change"],
                            recovery_usage=f"wave_get_change(change_id={canonical_change_id!r})",
                        )
                    ],
                    next_tools=["wave_get_change"],
                    usage=f"wave_get_change(change_id={canonical_change_id!r})",
                )
            relocated = True
        text = _insert_change_block_into_changes_section(text, canonical_change_id)
        wave_md.write_text(text, encoding="utf-8")
        if cache:
            cache.invalidate()
        _trigger_background_index_refresh_for_paths(root, [wave_md, target_path])
    # Detect broken relative links regardless of mode (dry-run reads source, create reads target).
    _doc_check_path = target_path if (mode_s == "create" and target_path.exists()) else source_path
    broken_links: list[str] = []
    if _doc_check_path.exists():
        _doc_text = _doc_check_path.read_text(encoding="utf-8")
        broken_links = _broken_relative_links_after_relocation(_doc_text)
    return _response(
        "dry_run" if mode_s == "dry_run" else "ok",
        {
            "wave_id": wave_id,
            "change_id": canonical_change_id,
            "mode": mode_s,
            "updated": mode_s == "create",
            "relocated": relocated,
            "source_path": _repo_rel(root, source_path),
            "target_path": _repo_rel(root, target_path),
            "broken_links": broken_links,
        },
        next_tools=["wave_current", "wave_add_change", "wave_get_change"],
        usage=f"wave_get_change(change_id={canonical_change_id!r})",
    )


def wave_remove_change_response(
    root: Path,
    wave_id: str,
    change_id: str,
    mode: str = "dry_run",
    cache: Optional[McpRepoCache] = None,
) -> dict[str, Any]:
    mode_s = "create" if (mode or "").strip().lower() == "apply" else (mode or "").strip().lower()
    if mode_s not in {"dry_run", "create"}:
        return _response("error", {"wave_id": wave_id, "change_id": change_id, "mode": mode}, diagnostics=[_diagnostic("invalid_arguments", f"Unsupported mode '{mode}'.")], next_tools=["wave_help"], usage="wave_help()")
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id, "change_id": change_id, "mode": mode_s}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
    text = wave_md.read_text(encoding="utf-8")
    target = _change_block_pattern(change_id)
    if not target.search(text):
        return _response("ok", {"wave_id": wave_id, "change_id": change_id, "mode": mode_s, "updated": False}, diagnostics=[_diagnostic("not_admitted", f"Change '{change_id}' is not admitted to wave.")], next_tools=["wave_current"], usage="wave_current()")
    location = _change_location_state(root, wave_md, change_id)
    if location["staged_exists"] and location["wave_exists"]:
        return _response(
            "error",
            {"wave_id": wave_id, "change_id": change_id, "mode": mode_s, "updated": False},
            diagnostics=[
                _diagnostic(
                    "duplicate_change_doc_locations",
                    f"Change '{change_id}' exists in both {_repo_rel(root, location['staged_path'])} and {_repo_rel(root, location['wave_path'])}.",
                    recovery_tools=["wave_prepare", "wave_get_change"],
                    recovery_usage=f"wave_prepare(wave_id={wave_md.parent.name!r}, mode='create')",
                )
            ],
            next_tools=["wave_prepare", "wave_get_change"],
            usage=f"wave_prepare(wave_id={wave_md.parent.name!r}, mode='create')",
        )
    if mode_s == "create":
        text = target.sub("\n", text, count=1)
        if location["wave_exists"]:
            try:
                _move_change_doc(location["wave_path"], location["staged_path"])
            except OSError as exc:
                return _response(
                    "error",
                    {"wave_id": wave_id, "change_id": change_id, "mode": mode_s, "updated": False},
                    diagnostics=[
                        _diagnostic(
                            "change_relocation_failed",
                            f"Failed to move change doc back to {_repo_rel(root, location['staged_path'])}: {exc}",
                            recovery_tools=["wave_get_change"],
                            recovery_usage=f"wave_get_change(change_id={change_id!r})",
                        )
                    ],
                    next_tools=["wave_get_change"],
                    usage=f"wave_get_change(change_id={change_id!r})",
                )
        wave_md.write_text(text, encoding="utf-8")
        if cache:
            cache.invalidate()
        _trigger_background_index_refresh_for_paths(root, [wave_md, location["staged_path"]])
    return _response(
        "dry_run" if mode_s == "dry_run" else "ok",
        {
            "wave_id": wave_id,
            "change_id": change_id,
            "mode": mode_s,
            "updated": mode_s == "create",
            "source_path": _repo_rel(root, location["wave_path"]),
            "target_path": _repo_rel(root, location["staged_path"]),
        },
        next_tools=["wave_current"],
        usage="wave_current()",
    )

def _lifecycle_module() -> Any:
    """Return the cached ``lifecycle_id`` module.

    Thin wrapper around ``_load_script`` so that tests can mock this single
    call site instead of patching the lower-level loader.
    """
    return _load_script("lifecycle_id")


def new_change(root: Path, kind: str, slug: str) -> dict:
    """Generate a lifecycle ID and scaffold a change doc. Returns path and ID."""
    change_id = _lifecycle_module().build_id(kind, slug, legacy=False)
    plans_dir = root / "docs" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    template_path = plans_dir / "plan-template.md"
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template = _default_template()

    import time
    today = time.strftime("%Y-%m-%d")
    content = template
    content = re.sub(r"`<id-prefix>-<kind> <slug>`.*", f"`{change_id}`", content)
    content = re.sub(r"Change ID:.*", f"Change ID: `{change_id}`", content)
    content = re.sub(r"Last verified:.*", f"Last verified: {today}", content)

    out_path = plans_dir / f"{change_id}.md"
    out_path.write_text(content, encoding="utf-8")
    return {"id": change_id, "path": str(out_path.relative_to(root)).replace("\\", "/")}


def change_create(root: Path, kind: str, slug: str, mode: str = "create") -> dict[str, Any]:
    if kind not in VALID_CHANGE_KINDS:
        raise ValueError(f"Unsupported change kind '{kind}'.")
    norm_mode = "create" if mode == "apply" else mode
    if norm_mode not in {"dry_run", "create"}:
        raise ValueError(f"Unsupported mode '{mode}'.")
    mode = norm_mode

    change_id = _lifecycle_module().build_id(kind, slug, legacy=False)
    plans_dir = root / "docs" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)
    rel_path = str((plans_dir / f"{change_id}.md").relative_to(root)).replace("\\", "/")
    out_path = root / rel_path
    exists = out_path.exists()

    if mode == "dry_run":
        return {
            "id": change_id,
            "path": rel_path,
            "mode": mode,
            "created": False,
            "exists": exists,
        }
    if exists:
        return {
            "id": change_id,
            "path": rel_path,
            "mode": mode,
            "created": False,
            "exists": True,
        }
    created = new_change(root, kind, slug)
    return {
        **created,
        "mode": mode,
        "created": True,
        "exists": False,
    }


def _change_create_response(
    root: Path,
    kind: str,
    slug: str,
    mode: str = "dry_run",
    cache: Optional[McpRepoCache] = None,
) -> dict[str, Any]:
    kind_s = (kind or "").strip().lower()
    slug_s = (slug or "").strip()
    mode_s = (mode or "").strip().lower()
    if mode_s == "apply":
        mode_s = "create"
    if not slug_s:
        return _response(
            "error",
            {"kind": kind_s, "slug": slug, "mode": mode_s},
            diagnostics=[
                _diagnostic(
                    "invalid_arguments",
                    "Change slug must be a non-empty string.",
                    recovery_tools=["wave_help"],
                    recovery_usage="wave_help(goal='plan_feature')",
                )
            ],
            next_tools=["wave_help"],
            usage="wave_help(goal='plan_feature')",
        )
    try:
        result = change_create(root, kind_s, slug_s, mode=mode_s)
    except ValueError as exc:
        return _response(
            "error",
            {"kind": kind_s, "slug": slug_s, "mode": mode_s},
            diagnostics=[
                _diagnostic(
                    "invalid_arguments",
                    str(exc),
                    recovery_tools=["wave_help"],
                    recovery_usage="wave_help(goal='plan_feature')",
                )
            ],
            next_tools=["wave_help"],
            usage="wave_help(goal='plan_feature')",
        )

    diagnostics: list[dict[str, Any]] = []
    status = "dry_run" if mode_s == "dry_run" else "ok"
    if result["exists"] and not result["created"]:
        diagnostics.append(
            _diagnostic(
                "already_exists",
                f"Change doc already exists at {result['path']}.",
                recovery_tools=["wave_get_change", "wave_validate"],
                recovery_usage=f"wave_get_change(change_id={result['id']!r})",
            )
        )
    if cache and result.get("created"):
        cache.invalidate()
    if result.get("created"):
        _trigger_background_index_refresh_for_paths(root, [result["path"]])
    return _response(
        status,
        {
            "change_id": result["id"],
            "path": result["path"],
            "kind": kind_s,
            "slug": slug_s,
            "mode": mode_s,
            "created": result["created"],
            "exists": result["exists"],
        },
        diagnostics=diagnostics,
        next_tools=["wave_get_change", "wave_validate"],
        usage=f"wave_get_change(change_id={result['id']!r})",
    )


_VALID_GATES = {"seed_edit_allowed", "framework_edit_allowed", "design_system_edit_allowed"}


def _read_guard_overrides(root: Path) -> dict[str, Any]:
    """Read .wavefoundry/guard-overrides.json; return empty dict on missing/malformed."""
    path = root / ".wavefoundry" / "guard-overrides.json"
    if not path.exists():
        return {}
    try:
        import json as _json
        return _json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_guard_overrides(root: Path, data: dict[str, Any]) -> None:
    """Write data to .wavefoundry/guard-overrides.json."""
    import json as _json
    path = root / ".wavefoundry" / "guard-overrides.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _force_gates_closed(root: Path, mode: str) -> list[dict[str, Any]]:
    """Close all edit gates and return a diagnostic listing which were open.

    In dry-run mode the gate file is not written; the diagnostic is still returned
    so callers can report what would have been closed.

    Args:
        root: Repository root.
        mode: ``"create"`` to write the gate file; any other value is a dry-run.
    """
    overrides = _read_guard_overrides(root)
    open_gates = [g for g in _VALID_GATES if overrides.get(g, {}).get("enabled", False)]
    if not open_gates:
        return []
    if mode == "create":
        for gate in _VALID_GATES:
            overrides.setdefault(gate, {})["enabled"] = False
        _write_guard_overrides(root, overrides)
    return [
        _diagnostic(
            "gates_forced_closed",
            f"The following edit gate(s) were open and have been {'closed' if mode == 'create' else 'detected (dry-run — not closed)' }: {', '.join(sorted(open_gates))}. "
            "Use wave_gate_open / wave_gate_close to manage gates explicitly.",
            recovery_tools=["wave_gate_close"],
            recovery_usage="wave_gate_close(gate='seed_edit_allowed')",
        )
    ]


def wave_open_gate_response(root: Path, gate: str) -> dict[str, Any]:
    """Open an edit gate, enabling the corresponding guard in guard-overrides.json."""
    gate_s = (gate or "").strip()
    if gate_s not in _VALID_GATES:
        return _response(
            "error",
            {"gate": gate_s, "valid_gates": sorted(_VALID_GATES)},
            diagnostics=[_diagnostic("invalid_arguments", f"Unknown gate '{gate_s}'. Valid gates: {sorted(_VALID_GATES)}.")],
            next_tools=["wave_gate_open"],
            usage=f"wave_gate_open(gate='seed_edit_allowed')",
        )
    overrides = _read_guard_overrides(root)
    if overrides.get(gate_s, {}).get("enabled", False):
        return _response(
            "error",
            {"gate": gate_s, "enabled": True},
            diagnostics=[_diagnostic(
                "gate_already_open",
                f"Gate '{gate_s}' is already open. Close it with wave_gate_close before opening again.",
                recovery_tools=["wave_gate_close"],
                recovery_usage=f"wave_gate_close(gate={gate_s!r})",
            )],
            next_tools=["wave_gate_close"],
            usage=f"wave_gate_close(gate={gate_s!r})",
        )
    overrides.setdefault(gate_s, {})["enabled"] = True
    _write_guard_overrides(root, overrides)
    return _response(
        "ok",
        {"gate": gate_s, "enabled": True},
        next_tools=["wave_gate_close"],
        usage=f"wave_gate_close(gate={gate_s!r})",
    )


def wave_close_gate_response(root: Path, gate: str) -> dict[str, Any]:
    """Close an edit gate, disabling the corresponding guard in guard-overrides.json."""
    gate_s = (gate or "").strip()
    if gate_s not in _VALID_GATES:
        return _response(
            "error",
            {"gate": gate_s, "valid_gates": sorted(_VALID_GATES)},
            diagnostics=[_diagnostic("invalid_arguments", f"Unknown gate '{gate_s}'. Valid gates: {sorted(_VALID_GATES)}.")],
            next_tools=["wave_gate_close"],
            usage=f"wave_gate_close(gate='seed_edit_allowed')",
        )
    overrides = _read_guard_overrides(root)
    already_closed = not overrides.get(gate_s, {}).get("enabled", False)
    overrides.setdefault(gate_s, {})["enabled"] = False
    _write_guard_overrides(root, overrides)
    diagnostics: list[dict[str, Any]] = []
    if already_closed:
        diagnostics.append(_diagnostic(
            "gate_already_closed",
            f"Gate '{gate_s}' was already closed — no change made.",
        ))
    return _response(
        "ok",
        {"gate": gate_s, "enabled": False},
        diagnostics=diagnostics if diagnostics else None,
        next_tools=["wave_gate_open"],
        usage=f"wave_gate_open(gate={gate_s!r})",
    )


def wave_gate_status_response(root: Path) -> dict[str, Any]:
    """Return the current enabled/disabled state of all edit gates."""
    overrides = _read_guard_overrides(root)
    gates = {gate: overrides.get(gate, {}).get("enabled", False) for gate in sorted(_VALID_GATES)}
    return _response(
        "ok",
        {"gates": gates},
        next_tools=["wave_gate_open", "wave_gate_close"],
    )


def wave_get_handoff_response(root: Path) -> dict[str, Any]:
    """Read docs/agents/session-handoff.md and return its content and mtime."""
    handoff_path = root / "docs" / "agents" / "session-handoff.md"
    if not handoff_path.exists():
        return _response(
            "ok",
            {"path": "docs/agents/session-handoff.md", "content": None, "mtime": None},
            diagnostics=[
                _diagnostic(
                    "handoff_not_found",
                    "docs/agents/session-handoff.md does not exist. Use wave_set_handoff to create it.",
                    recovery_tools=["wave_current"],
                    recovery_usage="wave_current()",
                )
            ],
            next_tools=["wave_set_handoff", "wave_current"],
            usage="wave_set_handoff(content='# Session Handoff\\n\\n...')",
        )
    try:
        content = handoff_path.read_text(encoding="utf-8")
        mtime = handoff_path.stat().st_mtime
    except OSError as exc:
        return _response("error", {"path": "docs/agents/session-handoff.md"}, diagnostics=[_diagnostic("read_error", str(exc))], next_tools=["wave_current"], usage="wave_current()")
    return _response(
        "ok",
        {"path": "docs/agents/session-handoff.md", "content": content, "mtime": mtime},
        next_tools=["wave_set_handoff", "wave_current"],
        usage="wave_current()",
    )


def wave_set_handoff_response(root: Path, content: str, cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    """Write content to docs/agents/session-handoff.md, creating the file if absent."""
    handoff_path = root / "docs" / "agents" / "session-handoff.md"
    try:
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        return _response("error", {"path": "docs/agents/session-handoff.md"}, diagnostics=[_diagnostic("write_error", str(exc))], next_tools=["wave_current"], usage="wave_current()")
    _trigger_background_index_refresh_for_paths(root, ["docs/agents/session-handoff.md"])
    return _response(
        "ok",
        {"path": "docs/agents/session-handoff.md", "written": True, "size": len(content)},
        next_tools=["wave_get_handoff", "wave_current"],
        usage="wave_get_handoff()",
    )


def wave_index_health_response(index: WaveIndex) -> dict[str, Any]:
    """Return structured health status for each index layer (project + framework).

    Runs file-hash comparison against meta.json for each layer and reports
    missing, stale, or ready state.  Intended as an explicit diagnostic tool;
    does not run on the search hot path.
    """
    try:
        health = index.docs_health()
    except Exception as exc:
        return _response(
            "error",
            {"layers": {}},
            diagnostics=[
                _diagnostic(
                    "index_health_error",
                    f"Could not compute index health: {exc}",
                    recovery_tools=["wave_help"],
                    recovery_usage="python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root .",
                )
            ],
            next_tools=["wave_help"],
            usage="wave_index_health()",
        )

    diagnostics: list[dict[str, Any]] = []
    for layer in health.get("missing_layers", []):
        diagnostics.append(
            _diagnostic(
                "index_missing",
                f"Index layer missing: {layer}. Run: python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root .",
                recovery_tools=["wave_help"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root .",
            )
        )
    for layer in health.get("stale_layers", []):
        diagnostics.append(
            _diagnostic(
                "index_stale",
                f"Index layer stale: {layer}. Run: python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root . --full",
                recovery_tools=["wave_help"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root . --full",
            )
        )
    overview = health.get("readiness_overview")
    if overview == "degraded":
        diagnostics.append(
            _diagnostic(
                "index_degraded",
                "Index metadata is present but merged semantic chunks did not load; search may fall back to lexical retrieval.",
                recovery_tools=["wave_help", "wave_index_build"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root .",
            )
        )
    elif overview == "absent":
        diagnostics.append(
            _diagnostic(
                "index_absent",
                "No index metadata found under project or framework index dirs (nothing to search semantically yet).",
                recovery_tools=["wave_help"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root .",
            )
        )
    for layer in health.get("chunker_version_mismatch_layers", []):
        diagnostics.append(
            _diagnostic(
                "chunker_version_mismatch",
                f"Index layer '{layer}' was built with an older chunker version. "
                "A full rebuild is required: python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root . --full",
                recovery_tools=["wave_index_build"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_wavefoundry.py --root . --full",
            )
        )
    background_build_status = _background_build_status(index.root)
    if background_build_status == "running":
        diagnostics.append(
            _diagnostic(
                "background_code_build_running",
                "A background code index build is in progress. "
                f"Watch progress: {index.root / '.wavefoundry' / 'logs' / 'project-background-build.log'}",
                recovery_tools=[],
                recovery_usage="wave_index_health()",
            )
        )

    _refresh_index_build_stats_from_finished_logs(index.root, "project")
    # Always return "ok" when health data was successfully computed — agents
    # read ``readiness_overview`` and ``diagnostics`` to decide whether to
    # reindex.  Reserve ``status: "error"`` for the except branch above (i.e.
    # when the health check itself crashed, not when the index is merely absent
    # or stale).
    project_stats = _read_index_build_stats_file(index.root, "project")
    if project_stats is not None:
        health["previous_build_stats"] = project_stats

    semantic_ready = health.get("semantic_ready")
    return _response(
        "ok",
        health,
        diagnostics=diagnostics,
        next_tools=["docs_search"] if semantic_ready else ["wave_index_build"],
        usage="docs_search(query='...')" if semantic_ready else "wave_index_build(content='docs', mode='update')",
    )


def wave_audit_response(
    root: Path,
    wave_id: str = "",
    index: Optional[WaveIndex] = None,
    cache: Optional[McpRepoCache] = None,
) -> dict[str, Any]:
    """Aggregate read-only audit: wave state + docs validation + index health.

    Returns a single ``data`` payload with three sub-objects (``wave``,
    ``validation``, ``index``) and a top-level ``ready`` boolean that is
    ``True`` only when all three sub-checks pass:
    - wave is active or planned
    - docs-lint reports zero failures
    - ``semantic_ready`` is ``True`` in the index health report

    Safe to call at any time; does not trigger writes or reindexes.
    """
    # --- Wave sub-check ---
    wave_data: dict[str, Any] = {}
    wave_ok = False
    if wave_id:
        waves = cache.list_waves_cached() if cache else list_waves(root)
        wid = wave_id.strip().lower()
        matched = next(
            (w for w in waves if w["wave_id"].lower().startswith(wid) or wid in w["wave_id"].lower()),
            None,
        )
        if matched:
            next_action = _WAVE_CURRENT_NEXT_ACTION.get(matched["status"], "prepare_wave")
            wave_data = {**matched, "next_action": next_action}
            wave_ok = matched["status"] in ("active", "implementing", "planned")
        else:
            wave_data = {"id": wave_id, "status": "not_found"}
    else:
        wave = current_wave(root, cache=cache)
        if wave:
            next_action = _WAVE_CURRENT_NEXT_ACTION.get(wave["status"], "prepare_wave")
            wave_data = {**wave, "next_action": next_action}
            wave_ok = True
        # wave_data stays {}; wave_ok stays False when no active wave

    # --- Validation sub-check ---
    try:
        val_result = run_validate(root)
        lint_ok = val_result["passed"]
    except Exception as exc:  # pragma: no cover
        val_result = {"passed": False, "errors": [str(exc)], "warnings": []}
        lint_ok = False

    # --- Index health sub-check ---
    index_data: dict[str, Any] = {}
    index_ok = False
    if index is not None:
        try:
            index_data = index.docs_health()
            index_ok = bool(index_data.get("semantic_ready"))
        except Exception as exc:  # pragma: no cover
            index_data = {"error": str(exc), "semantic_ready": False}
    else:
        index_data = {"semantic_ready": False}

    # --- ready ---
    ready = wave_ok and lint_ok and index_ok

    # --- diagnostics ---
    diagnostics: list[dict[str, Any]] = []
    if not wave_ok:
        diagnostics.append(
            _diagnostic(
                "no_active_wave",
                (
                    f"Wave not found: {wave_id}"
                    if wave_id
                    else "No active or planned wave found."
                ),
                recovery_tools=["wave_list_waves"],
                recovery_usage="wave_list_waves()",
            )
        )
    if not lint_ok:
        for err in val_result.get("errors", []):
            diagnostics.append(_diagnostic("docs_lint_error", err, recovery_tools=["wave_validate"]))
    if not index_ok:
        overview = index_data.get("readiness_overview", "absent")
        diagnostics.append(
            _diagnostic(
                "index_not_ready",
                (
                    f"Semantic index is not ready (readiness_overview: {overview!r}). "
                    "Call wave_index_build to recover."
                ),
                recovery_tools=["wave_index_build"],
                recovery_usage="wave_index_build(content='docs', mode='update')",
            )
        )

    # --- next_tools ---
    next_tools: list[str] = []
    if not lint_ok:
        next_tools.append("wave_validate")
    if not index_ok:
        next_tools.append("wave_index_build")
    if not wave_ok:
        next_tools.append("wave_current")
    if not next_tools:
        next_tools = ["wave_current"]

    # --- Harness sub-checks ---
    commit_governance = _audit_commit_governance(root)
    harnessability = _audit_harnessability(root)
    harness_coverage = _audit_harness_coverage(root)
    harness_coherence = _audit_harness_coherence(root)

    # Advisory diagnostics for harness checks
    if commit_governance.get("available") and commit_governance.get("unassociated_count", 0) > 0:
        n = commit_governance["unassociated_count"]
        diagnostics.append(_diagnostic(
            "unassociated_commits",
            f"{n} recent commit(s) could not be associated with a wave or change ID.",
            recovery_tools=["wave_current"],
            recovery_usage="wave_current()",
        ))
    if harness_coverage.get("covered_count", 3) < 3:
        uncovered = [k for k, v in harness_coverage.get("dimensions", {}).items() if not v["covered"]]
        diagnostics.append(_diagnostic(
            "harness_coverage_gap",
            f"Harness coverage {harness_coverage['coverage_ratio']}: uncovered dimensions: {', '.join(uncovered)}.",
            recovery_tools=["wave_audit"],
            recovery_usage="wave_audit()",
        ))
    if harness_coherence.get("findings_count", 0) > 0:
        diagnostics.append(_diagnostic(
            "harness_coherence_issue",
            f"{harness_coherence['findings_count']} harness coherence finding(s) detected in seed surface.",
            recovery_tools=["wave_audit"],
            recovery_usage="wave_audit()",
        ))

    return _response(
        "ok",
        {
            "ready": ready,
            "wave": wave_data,
            "validation": val_result,
            "index": index_data,
            "commit_governance": commit_governance,
            "harnessability": harnessability,
            "harness_coverage": harness_coverage,
            "harness_coherence": harness_coherence,
        },
        diagnostics=diagnostics,
        next_tools=next_tools,
        usage=next_tools[0] + "()" if next_tools else "wave_current()",
    )


def wave_validate_response(root: Path) -> dict[str, Any]:
    result = run_validate(root)
    status = "ok" if result["passed"] else "error"
    diagnostics = [
        _diagnostic("docs_lint_error", error, recovery_tools=["wave_validate"])
        for error in result["errors"]
    ] + [
        _diagnostic("docs_lint_warning", warning, recovery_tools=["wave_validate"])
        for warning in result["warnings"]
    ]
    return _response(
        status,
        result,
        diagnostics=diagnostics,
        next_tools=["wave_garden"] if result["passed"] else ["wave_help"],
        usage="wave_garden()" if result["passed"] else "wave_help(goal='maintain_framework')",
    )


def wave_garden_response(root: Path, mode: str = "dry_run", cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    if (mode or "").strip().lower() == "dry_run":
        return _response(
            "ok",
            {"mode": "dry_run", "skipped": True},
            diagnostics=[_diagnostic(
                "dry_run",
                "Pass mode='run' to execute the docs gardener.",
                recovery_tools=[],
                recovery_usage="wave_garden(mode='run')",
            )],
            next_tools=["wave_garden"],
            usage="wave_garden(mode='run')",
        )
    result = run_garden(root)
    status = "ok" if result["passed"] else "error"
    diagnostics = [] if result["passed"] else [
        _diagnostic(
            "docs_gardener_failed",
            result["output"].strip() or "docs_gardener failed",
            recovery_tools=["wave_validate"],
            recovery_usage="wave_validate()",
        )
    ]
    if cache and result["passed"]:
        cache.invalidate()
    if result["passed"] and result.get("files_updated", 0):
        _trigger_background_index_refresh_for_paths(root, ["docs/"])
    return _response(
        status,
        result,
        diagnostics=diagnostics,
        next_tools=["wave_validate", "wave_sync_surfaces"] if result["passed"] else ["wave_validate"],
        usage="wave_sync_surfaces()" if result["passed"] else "wave_validate()",
    )


def wave_sync_surfaces_response(root: Path, mode: str = "dry_run", cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    if (mode or "").strip().lower() == "dry_run":
        return _response(
            "ok",
            {"mode": "dry_run", "skipped": True},
            diagnostics=[_diagnostic(
                "dry_run",
                "Pass mode='run' to execute render_platform_surfaces.",
                recovery_tools=[],
                recovery_usage="wave_sync_surfaces(mode='run')",
            )],
            next_tools=["wave_sync_surfaces"],
            usage="wave_sync_surfaces(mode='run')",
        )
    result = run_sync_surfaces(root)
    status = "ok" if result["passed"] else "error"
    diagnostics = [] if result["passed"] else [
        _diagnostic(
            "render_platform_surfaces_failed",
            result["output"].strip() or "render_platform_surfaces failed",
            recovery_tools=["wave_validate"],
            recovery_usage="wave_validate()",
        )
    ]
    if cache and result["passed"]:
        cache.invalidate()
    return _response(
        status,
        result,
        diagnostics=diagnostics,
        next_tools=["wave_validate"],
        usage="wave_validate()",
    )


def wave_index_build_response(
    root: Path,
    *,
    content: str = "docs",
    mode: str = "update",
    layer: str = "project",
    cache: Optional[McpRepoCache] = None,
) -> dict[str, Any]:
    content_s = (content or "").strip().lower()
    layer_s = (layer or "").strip().lower()
    mode_s = (mode or "").strip().lower()
    if mode_s not in {"update", "rebuild"}:
        return _response(
            "error",
            {"content": content, "mode": mode, "layer": layer},
            diagnostics=[
                _diagnostic(
                    "invalid_arguments",
                    f"Unsupported mode {mode!r}. Use 'update' (incremental) or 'rebuild' (full).",
                    recovery_tools=["wave_help"],
                    recovery_usage="wave_help(goal='refresh_semantic_index')",
                )
            ],
            next_tools=["wave_help"],
            usage="wave_help(goal='refresh_semantic_index')",
        )
    full = mode_s == "rebuild"
    try:
        result = run_index_rebuild(root, content=content_s, full=full, layer=layer_s)
    except ValueError as exc:
        return _response(
            "error",
            {"content": content, "mode": mode_s, "layer": layer},
            diagnostics=[
                _diagnostic(
                    "invalid_arguments",
                    str(exc),
                    recovery_tools=["wave_help"],
                    recovery_usage="wave_help(goal='maintain_framework')",
                )
            ],
            next_tools=["wave_help"],
            usage="wave_help(goal='maintain_framework')",
        )
    # Only invalidate the cache when a rebuild was actually spawned — not for
    # up-to-date or already-running short-circuits.
    if cache and not result.get("up_to_date") and not result.get("already_running"):
        cache.invalidate()
    diagnostics = []
    if result.get("already_running"):
        diagnostics.append(_diagnostic(
            "index_build_already_running",
            result["notice"],
            recovery_tools=["wave_index_health"],
            recovery_usage="wave_index_health()",
        ))
    return _response(
        "ok",
        result,
        diagnostics=diagnostics,
        next_tools=["wave_index_health"],
        usage="wave_index_health()",
    )


def wave_index_build_status_response(root: Path, layer: str = "project") -> dict[str, Any]:
    import time as _time
    layer_s = (layer or "").strip().lower()
    if layer_s not in {"project", "framework"}:
        return _response("error", {"layer": layer}, diagnostics=[_diagnostic("invalid_arguments", f"Unsupported layer '{layer}'. Use 'project' or 'framework'.")])
    state_path = _index_build_state_path(root, layer_s)
    log_path = _index_build_log_path(root, layer_s)
    index_dir = state_path.parent
    stale_locks_cleaned = _cleanup_stale_table_locks(index_dir)
    background_status = _background_build_status(root) if layer_s == "project" else "none"

    if not state_path.exists():
        if background_status == "running":
            pid_path = root / ".wavefoundry" / "index" / "background-build.pid"
            background_pid: Optional[int] = None
            background_started_at: Optional[float] = None
            try:
                background_pid = int(pid_path.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                background_pid = None
            try:
                background_started_at = pid_path.stat().st_mtime
            except OSError:
                background_started_at = None
            now = _time.time()
            background_elapsed = (
                int(now - float(background_started_at))
                if isinstance(background_started_at, (int, float))
                else None
            )
            running_data: dict[str, Any] = {
                "layer": layer_s,
                "state": "running",
                "source": "background",
                "pid": background_pid,
                "started_at": background_started_at,
                "elapsed_seconds": background_elapsed,
                "progress": _background_build_progress(root),
            }
            _running_prev = _read_index_build_stats_file(root, layer_s)
            if _running_prev is not None:
                running_data["previous_stats"] = _running_prev
            if stale_locks_cleaned:
                running_data["stale_locks_cleaned"] = stale_locks_cleaned
            return _response(
                "ok",
                running_data,
                next_tools=["wave_index_build_status"],
                usage="wave_index_build_status()",
            )
        idle_data: dict[str, Any] = {"layer": layer_s, "state": "idle"}
        if stale_locks_cleaned:
            idle_data["stale_locks_cleaned"] = stale_locks_cleaned
        return _response("ok", idle_data, next_tools=["wave_index_build"], usage="wave_index_build()")

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _clear_index_build_state(root, layer_s)
        idle_data = {"layer": layer_s, "state": "idle"}
        if stale_locks_cleaned:
            idle_data["stale_locks_cleaned"] = stale_locks_cleaned
        return _response("ok", idle_data, next_tools=["wave_index_build"], usage="wave_index_build()")

    pid = state.get("pid")
    started_at = state.get("started_at")
    now = _time.time()
    elapsed = int(now - float(started_at)) if isinstance(started_at, (int, float)) else None

    # Read log once — used for last_line (progress) and done-marker detection.
    # Check log for completion marker before trusting _pid_is_running — the OS can
    # recycle a PID to an unrelated process after the indexer exits, causing a false positive.
    log_text = ""
    last_line = ""
    if log_path.exists():
        try:
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            last_line = next((l.strip() for l in reversed(log_text.splitlines()) if l.strip()), "")
        except OSError:
            pass
    # Either the "done — N files indexed" completion line or the "index is up to date"
    # early-exit message counts as a terminal state. Without the second pattern, a zombie
    # process (defunct on macOS) keeps reporting state="running" indefinitely because
    # os.kill(pid, 0) succeeds on zombies until the parent reaps them.
    log_done = bool(re.search(r"done\s*[—-]+\s*\d+\s+files? indexed", log_text)) or bool(
        re.search(r"index is up to date", log_text)
    )

    if layer_s == "project" and background_status == "running":
        pid_path = root / ".wavefoundry" / "index" / "background-build.pid"
        background_pid: Optional[int] = None
        background_started_at: Optional[float] = None
        try:
            background_pid = int(pid_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            background_pid = None
        try:
            background_started_at = pid_path.stat().st_mtime
        except OSError:
            background_started_at = None
        background_elapsed = (
            int(now - float(background_started_at))
            if isinstance(background_started_at, (int, float))
            else None
        )
        running_data: dict[str, Any] = {
            "layer": layer_s,
            "state": "running",
            "source": "background",
            "pid": background_pid,
            "started_at": background_started_at,
            "elapsed_seconds": background_elapsed,
            "progress": _background_build_progress(root),
        }
        _running_prev = _read_index_build_stats_file(root, layer_s)
        if _running_prev is not None:
            running_data["previous_stats"] = _running_prev
        if stale_locks_cleaned:
            running_data["stale_locks_cleaned"] = stale_locks_cleaned
        return _response(
            "ok",
            running_data,
            next_tools=["wave_index_build_status"],
            usage="wave_index_build_status()",
        )

    if not log_done and isinstance(pid, int) and _pid_is_running(pid):
        running_data: dict[str, Any] = {
            "layer": layer_s,
            "state": "running",
            "source": "foreground",
            "mode": "rebuild" if state.get("full") else state.get("mode", "update"),
            "pid": pid,
            "started_at": started_at,
            "elapsed_seconds": elapsed,
            "progress": last_line,
        }
        _running_prev = _read_index_build_stats_file(root, layer_s)
        if _running_prev is not None:
            running_data["previous_stats"] = _running_prev
        if stale_locks_cleaned:
            running_data["stale_locks_cleaned"] = stale_locks_cleaned
        return _response(
            "ok",
            running_data,
            next_tools=["wave_index_build_status"],
            usage="wave_index_build_status()",
        )

    # Process not running (or log confirms done) — build finished (or crashed). Parse summary from log.
    _refresh_index_build_stats_from_finished_log(root, layer_s)
    _clear_index_build_state(root, layer_s)
    finished_at = None
    if log_path.exists():
        try:
            finished_at = int(log_path.stat().st_mtime)
        except OSError:
            pass
    finished_elapsed = int(float(finished_at) - float(started_at)) if finished_at and isinstance(started_at, (int, float)) else elapsed

    files_indexed: Optional[int] = None
    doc_chunks: Optional[int] = None
    code_chunks: Optional[int] = None
    if log_text:
        m = re.search(r"done\s*[—-]+\s*(\d+)\s+files? indexed,\s*(\d+)\s+doc chunks?,\s*(\d+)\s+code chunks?", log_text)
        if m:
            files_indexed, doc_chunks, code_chunks = int(m.group(1)), int(m.group(2)), int(m.group(3))

    previous_stats = _read_index_build_stats_file(root, layer_s)
    summary: dict[str, Any] = {"layer": layer_s, "state": "finished", "started_at": started_at, "finished_at": finished_at, "elapsed_seconds": finished_elapsed}
    if files_indexed is not None:
        summary.update({"files_indexed": files_indexed, "doc_chunks": doc_chunks, "code_chunks": code_chunks})
    else:
        summary["last_log_line"] = last_line
    if previous_stats is not None:
        summary["previous_stats"] = previous_stats
    if stale_locks_cleaned:
        summary["stale_locks_cleaned"] = stale_locks_cleaned
    return _response("ok", summary, next_tools=["wave_index_health"], usage="wave_index_health()")


def wave_dashboard_start_response(root: Path, port: int | None = None) -> dict[str, Any]:
    """Start the local dashboard server (with browser open) or return its URL if already running."""
    import subprocess
    import time as _time
    import dashboard_lib

    meta_path = root / ".wavefoundry" / "dashboard-server.json"

    def running_meta() -> dict[str, Any] | None:
        if not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            pid = meta.get("pid")
            url = meta.get("url", "")
            if isinstance(pid, int) and _pid_is_running(pid) and url:
                return {"pid": pid, "url": url}
        except (OSError, json.JSONDecodeError):
            pass
        return None

    def already_running(meta: dict[str, Any], *, starting: bool = False) -> dict[str, Any]:
        data: dict[str, Any] = {
            "already_running": True,
            "pid": meta.get("pid"),
            "url": meta.get("url"),
        }
        if starting:
            data["starting"] = True
        return _response(
            "ok",
            data,
            next_tools=["wave_dashboard_open"],
            usage=str(meta.get("url") or "wave_dashboard_open()"),
        )

    def wait_for_running(timeout: float = DASHBOARD_START_WAIT_SECONDS) -> dict[str, Any] | None:
        deadline = _time.monotonic() + timeout
        while _time.monotonic() < deadline:
            meta = running_meta()
            if meta is not None:
                return meta
            _time.sleep(0.25)
        return None

    meta = running_meta()
    if meta is not None:
        return already_running(meta)

    try:
        start_lock = dashboard_lib.dashboard_start_lock(root)
        start_lock.__enter__()
    except dashboard_lib.DashboardLockBusy:
        meta = wait_for_running()
        if meta is not None:
            return already_running(meta, starting=True)
        return _response(
            "ok",
            {"already_running": True, "starting": True, "pid": None, "url": None},
            diagnostics=[_diagnostic(
                "dashboard_start_in_progress",
                "Another dashboard start is already in progress for this repository.",
            )],
            next_tools=["wave_dashboard_open"],
            usage="wave_dashboard_open()",
        )

    try:
        meta = running_meta()
        if meta is not None:
            return already_running(meta)

        scripts_dir = Path(__file__).resolve().parent
        cmd = [_preferred_python(), str(scripts_dir / "dashboard_server.py"), "--root", str(root)]
        if port is not None:
            cmd.extend(["--port", str(port)])
        if dashboard_lib.dashboard_browser_open_enabled():
            cmd.append("--open")
        spawn_kwargs: dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
            "cwd": str(root),
        }
        if os.name == "nt":
            spawn_kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            spawn_kwargs["start_new_session"] = True

        try:
            proc = subprocess.Popen(cmd, **spawn_kwargs)
        except OSError as exc:
            return _response(
                "error",
                {},
                diagnostics=[_diagnostic("spawn_failed", str(exc))],
            )

        # Poll up to 5s for the server to write its metadata (host, port, URL).
        url = ""
        deadline = _time.monotonic() + 5.0
        while _time.monotonic() < deadline:
            _time.sleep(0.25)
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    if meta.get("pid") == proc.pid and meta.get("url"):
                        url = meta["url"]
                        break
                except (OSError, json.JSONDecodeError):
                    pass

        if not url:
            return _response(
                "ok",
                {"started": True, "pid": proc.pid, "url": None},
                diagnostics=[_diagnostic(
                    "url_not_ready",
                    "Dashboard spawned but URL not yet available — it may still be binding.",
                )],
            )

        return _response("ok", {"started": True, "pid": proc.pid, "url": url}, usage=url)
    finally:
        start_lock.__exit__(None, None, None)


def wave_dashboard_open_response(root: Path) -> dict[str, Any]:
    """Open the browser to the running dashboard, or start the dashboard (with browser open) if not running."""
    import webbrowser
    import dashboard_lib

    meta_path = dashboard_lib.dashboard_metadata_path(root)
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            pid = meta.get("pid")
            url = meta.get("url", "")
            if isinstance(pid, int) and _pid_is_running(pid) and url:
                opened = False
                if dashboard_lib.dashboard_browser_open_enabled():
                    webbrowser.open(url)
                    opened = True
                return _response(
                    "ok",
                    {"opened": opened, "url": url, "browser_suppressed": not opened},
                    usage=url,
                )
        except (OSError, json.JSONDecodeError):
            pass

    # Dashboard not running — delegate to start (which spawns with --open).
    return wave_dashboard_start_response(root)


def _dashboard_process_metadata(root: Path) -> tuple[Path, dict[str, Any]]:
    import dashboard_lib

    meta_path = dashboard_lib.dashboard_metadata_path(root)
    return meta_path, dashboard_lib.read_dashboard_metadata(root)


def _remove_dashboard_metadata(meta_path: Path) -> bool:
    try:
        meta_path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def _terminate_dashboard_pid(pid: int) -> bool:
    import subprocess
    import time as _time

    if pid <= 0:
        return True

    if os.name == "nt":
        try:
            completed = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except OSError:
            return False
        return completed.returncode == 0 or not _pid_is_running(pid)

    import signal

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except OSError:
        return False

    deadline = _time.monotonic() + 5.0
    while _time.monotonic() < deadline:
        if not _pid_is_running(pid):
            return True
        try:
            ended_pid, _ = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            ended_pid = 0
        except OSError:
            ended_pid = 0
        if ended_pid == pid:
            return True
        _time.sleep(0.1)

    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return True
    except OSError:
        return False

    deadline = _time.monotonic() + 2.0
    while _time.monotonic() < deadline:
        if not _pid_is_running(pid):
            return True
        try:
            ended_pid, _ = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            ended_pid = 0
        except OSError:
            ended_pid = 0
        if ended_pid == pid:
            return True
        _time.sleep(0.1)

    return not _pid_is_running(pid)


def wave_dashboard_stop_response(root: Path) -> dict[str, Any]:
    meta_path, meta = _dashboard_process_metadata(root)
    pid = meta.get("pid")
    url = meta.get("url", "")

    summary: dict[str, Any] = {
        "pid": pid if isinstance(pid, int) else None,
        "url": url if isinstance(url, str) else "",
    }
    if not isinstance(pid, int):
        summary.update({"already_stopped": True, "metadata_removed": _remove_dashboard_metadata(meta_path)})
        return _response("ok", summary, usage="wave_dashboard_stop()")

    if not _pid_is_running(pid):
        summary.update({"already_stopped": True, "metadata_removed": _remove_dashboard_metadata(meta_path)})
        return _response("ok", summary, usage="wave_dashboard_stop()")

    if not _terminate_dashboard_pid(pid):
        return _response(
            "error",
            summary,
            diagnostics=[_diagnostic("stop_failed", f"Dashboard process {pid} for this repository did not exit cleanly.")],
            usage="wave_dashboard_stop()",
        )

    summary.update({"stopped": True, "metadata_removed": _remove_dashboard_metadata(meta_path)})
    return _response("ok", summary, usage="wave_dashboard_stop()")


def wave_dashboard_restart_response(root: Path) -> dict[str, Any]:
    # R7 (revised): Allow restart during upgrade. The restarted dashboard
    # detects the upgrade lock at startup and enters upgrade_paused
    # automatically, then resumes when the lock is removed. Blocking the
    # restart was redundant and prevented legitimate recovery via restart.

    # Capture the current port before stopping so the restarted server reuses
    # the same port — the browser tab stays valid without a refresh.
    restart_port: int | None = None
    try:
        _, pre_meta = _dashboard_process_metadata(root)
        recorded_port = pre_meta.get("port")
        if isinstance(recorded_port, int) and recorded_port > 0:
            restart_port = recorded_port
    except Exception:  # noqa: BLE001
        pass

    stop_env = wave_dashboard_stop_response(root)
    if stop_env.get("status") != "ok":
        return stop_env
    start_env = wave_dashboard_start_response(root, port=restart_port)
    if start_env.get("status") != "ok":
        return start_env
    data = dict(stop_env.get("data", {}))
    data.update(start_env.get("data", {}))
    data["restarted"] = True
    return _response(
        "ok",
        data,
        diagnostics=list(stop_env.get("diagnostics", [])) + list(start_env.get("diagnostics", [])),
        next_tools=list(start_env.get("next_tools", [])),
        usage=start_env.get("usage", ""),
    )


def _load_upgrade_lib() -> Any:
    """Import upgrade_lib from the scripts directory, ensuring it is on sys.path."""
    _scripts_dir = str(Path(__file__).resolve().parent)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    try:
        import upgrade_lib as _ulib  # noqa: PLC0415
        return _ulib
    except ImportError:
        return None


def wave_upgrade_response(
    root: Path,
    phase: str = "preflight_to_docs_gate",
    mode: str = "apply",
) -> dict[str, Any]:
    """Invoke upgrade_wavefoundry.py for the requested phase (12r0b).

    mode values:
      "dry_run" — print the full upgrade plan + hook inventory (seed diffs,
          extension module source, convention hook scripts) without modifying
          anything on disk. Use this before the real upgrade to review what
          will change and inspect any hook code. The phase parameter is
          ignored in dry_run mode.
      "apply" (default) — execute the requested phase for real.

    phase values (apply mode only):
      "preflight_to_docs_gate" — phases 0–3 (default): pre-flight, surface
          rendering, pruning, docs gate. Non-interactive (--yes).
      "update_index" — phase 4 (default): incremental docs index update
          (blocking) + code index (background). Re-embeds only files that
          changed; auto-escalates to full rebuild when chunker or embedding
          model version changed. Use for normal post-editing-pass runs.
      "rebuild_index" — phase 4 (full): re-embeds every file from scratch.
          Use when update_index is insufficient (e.g. index corruption, or
          a chunker bump that the auto-escalation did not catch).
      "cleanup" — phase 5: remove upgrade lock + print operator summary.
    """
    valid_modes = ("apply", "dry_run")
    if mode not in valid_modes:
        return _response(
            "error",
            {"mode": mode, "valid_modes": list(valid_modes)},
            diagnostics=[_diagnostic("invalid_mode", f"Unknown mode {mode!r}. Valid: {valid_modes}")],
        )

    valid_phases = ("preflight_to_docs_gate", "update_index", "rebuild_index", "cleanup")
    if mode == "apply" and phase not in valid_phases:
        return _response(
            "error",
            {"phase": phase, "valid_phases": list(valid_phases)},
            diagnostics=[_diagnostic("invalid_phase", f"Unknown phase {phase!r}. Valid: {valid_phases}")],
        )

    upgrade_script = Path(__file__).resolve().parent / "upgrade_wavefoundry.py"
    if not upgrade_script.exists():
        return _response(
            "error",
            {},
            diagnostics=[_diagnostic("script_not_found", f"upgrade_wavefoundry.py not found at {upgrade_script}")],
        )

    if mode == "dry_run":
        cmd = [_preferred_python(), str(upgrade_script), "--root", str(root), "--dry-run"]
    else:
        # Pre-create the log file so log_path in the response is always valid,
        # even if the upgrade fails before the script opens it.  The upgrade
        # script manages truncation (mode="w") and appending (mode="a") itself.
        _log_path = root / ".wavefoundry" / "logs" / "upgrade.log"
        try:
            _log_path.parent.mkdir(parents=True, exist_ok=True)
            _log_path.touch(exist_ok=True)
        except OSError:
            pass

        # All apply-mode phases run non-interactively (no TTY in MCP).
        cmd = [_preferred_python(), str(upgrade_script), "--root", str(root), "--yes"]
        if phase == "update_index":
            cmd.append("--update-index")
        elif phase == "rebuild_index":
            cmd.append("--rebuild-index")
        elif phase == "cleanup":
            cmd.append("--cleanup")
        # phase == "preflight_to_docs_gate": --yes only (default run)

    import subprocess as _subprocess
    try:
        result = _subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return _response(
            "error",
            {"phase": phase},
            diagnostics=[_diagnostic("spawn_failed", str(exc))],
        )

    output = (result.stdout or "") + (result.stderr or "")
    # log_path is deterministic and always present for apply-mode phases;
    # dry_run is read-only so it writes no log file.
    log_path = (
        str(root / ".wavefoundry" / "logs" / "upgrade.log")
        if mode == "apply"
        else None
    )
    data = {
        "phase": phase,
        "exit_code": result.returncode,
        "output": output.strip(),
        "log_path": log_path,
    }

    if result.returncode != 0:
        exit_meanings = {1: "docs gate failed", 2: "surface rendering failed", 3: "pre-flight check failed"}
        reason = exit_meanings.get(result.returncode, f"exited {result.returncode}")
        return _response(
            "error",
            data,
            diagnostics=[_diagnostic("upgrade_failed", f"Upgrade phase '{phase}' failed: {reason}")],
        )

    resp = _response("ok", data, usage=f"wave_upgrade(phase='{phase}')")
    if phase == "cleanup" and mode == "apply":
        try:
            import server as _srv
            reload_resp = _srv.perform_mcp_reload()
            if reload_resp.get("status") == "ok":
                resp.setdefault("data", {})["mcp_reload"] = reload_resp.get("data", {})
            else:
                resp.setdefault("diagnostics", []).extend(reload_resp.get("diagnostics", []))
        except Exception as exc:
            resp.setdefault("diagnostics", []).append(
                _diagnostic("mcp_reload_skipped", f"In-process MCP reload skipped: {exc}")
            )
    return resp


def wave_upgrade_status_response(root: Path) -> dict[str, Any]:
    """Return the current upgrade lock state (R5 — 12r08)."""
    _ulib = _load_upgrade_lib()
    if _ulib is not None:
        lock = _ulib.read_upgrade_lock(root)
    else:
        lock = None

    if lock is None:
        data: dict[str, Any] = {
            "in_progress": False,
            "started_at": None,
            "from_version": None,
            "to_version": None,
            "pid": None,
        }
    else:
        data = {
            "in_progress": True,
            "started_at": lock.get("started_at"),
            "from_version": lock.get("from_version"),
            "to_version": lock.get("to_version"),
            "pid": lock.get("pid"),
        }
    return _response("ok", data, usage="wave_upgrade_status()")


def wave_run_sensors_response(root: Path) -> dict[str, Any]:
    """Run registered project sensors and return structured pass/fail results.

    Sensors are defined in ``docs/workflow-config.json`` under the ``sensors`` key.
    Each sensor entry must have ``name`` and ``command`` fields; ``dimension`` and
    ``description`` are optional.  Commands are run in a subprocess with ``cwd=root``.
    Results include per-sensor pass/fail, exit code, and stdout/stderr summary.
    """
    import subprocess as _sp
    sensors = _read_project_sensors(root)
    if not sensors:
        return _response(
            "ok",
            {"sensors_run": 0, "results": [], "all_passed": True, "notice": "No sensors registered in workflow-config.json."},
            next_tools=["wave_audit"],
            usage="wave_audit()",
        )
    results = []
    all_passed = True
    for sensor in sensors:
        cmd = sensor["command"]
        try:
            proc = _sp.run(
                cmd if isinstance(cmd, list) else cmd,
                shell=not isinstance(cmd, list),
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            passed = proc.returncode == 0
            output = (proc.stdout + proc.stderr).strip()
            summary_lines = output.splitlines()
            results.append({
                "name": sensor["name"],
                "dimension": sensor["dimension"],
                "passed": passed,
                "exit_code": proc.returncode,
                "output_summary": "\n".join(summary_lines[:20]) if summary_lines else "",
            })
            if not passed:
                all_passed = False
        except _sp.TimeoutExpired:
            results.append({"name": sensor["name"], "dimension": sensor["dimension"], "passed": False, "exit_code": None, "output_summary": "Sensor timed out after 120s."})
            all_passed = False
        except Exception as exc:
            results.append({"name": sensor["name"], "dimension": sensor["dimension"], "passed": False, "exit_code": None, "output_summary": f"Sensor failed to run: {exc}"})
            all_passed = False

    diagnostics = []
    if not all_passed:
        failed = [r["name"] for r in results if not r["passed"]]
        diagnostics.append(_diagnostic(
            "sensor_failed",
            f"Sensor(s) failed: {', '.join(failed)}. Address failures before declaring done.",
            recovery_tools=["wave_run_sensors"],
            recovery_usage="wave_run_sensors()",
        ))
    return _response(
        "ok" if all_passed else "error",
        {"sensors_run": len(results), "results": results, "all_passed": all_passed},
        diagnostics=diagnostics,
        next_tools=["wave_audit"] if all_passed else ["wave_run_sensors"],
        usage="wave_audit()" if all_passed else "wave_run_sensors()",
    )


# ---------------------------------------------------------------------------
# Audit helpers: commit governance, harnessability, harness coverage, coherence
# ---------------------------------------------------------------------------

def _audit_commit_governance(root: Path) -> dict[str, Any]:
    """Scan recent git commits and classify as governed or unassociated."""
    import subprocess as _sp
    cfg = _read_workflow_config(root)
    governance_cfg = cfg.get("commit_governance", {})
    window_days = int(governance_cfg.get("window_days", 30)) if isinstance(governance_cfg, dict) else 30
    exclusion_patterns = governance_cfg.get("exclusion_patterns", []) if isinstance(governance_cfg, dict) else []
    if not isinstance(exclusion_patterns, list):
        exclusion_patterns = []

    try:
        result = _sp.run(
            ["git", "log", f"--since={window_days} days ago", "--pretty=format:%h %s"],
            cwd=str(root), capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return {"available": False, "reason": "git log failed"}
        lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
    except Exception:
        return {"available": False, "reason": "git unavailable"}

    # Collect known wave/change ID prefixes from docs/waves/
    known_ids: set[str] = set()
    waves_dir = root / "docs" / "waves"
    if waves_dir.is_dir():
        for entry in waves_dir.iterdir():
            if entry.is_dir():
                # wave-id prefix like "12ecs"
                parts = entry.name.split(" ", 1)
                if parts:
                    known_ids.add(parts[0].lower())
                for f in entry.iterdir():
                    if f.suffix == ".md" and "-" in f.stem:
                        # change-id like "12ecs-feat"
                        cid = f.stem.split(" ")[0].lower()
                        known_ids.add(cid)

    governed, unassociated, excluded = [], [], []
    for line in lines:
        parts = line.split(" ", 1)
        sha = parts[0]
        msg = parts[1] if len(parts) > 1 else ""
        msg_lower = msg.lower()
        # Check exclusion patterns first
        if any(msg_lower.startswith(pat.lower()) or pat.lower() in msg_lower for pat in exclusion_patterns):
            excluded.append({"sha": sha, "message": msg})
            continue
        # Check association with known wave/change IDs
        associated = any(kid in msg_lower for kid in known_ids)
        if associated:
            governed.append({"sha": sha, "message": msg})
        else:
            unassociated.append({"sha": sha, "message": msg})

    return {
        "available": True,
        "window_days": window_days,
        "governed": governed,
        "unassociated": unassociated,
        "excluded": excluded,
        "governed_count": len(governed),
        "unassociated_count": len(unassociated),
    }


def _audit_harnessability(root: Path) -> dict[str, Any]:
    """Assess codebase harnessability across three proxy dimensions."""
    # --- Type coverage ---
    type_score = "unknown"
    type_evidence = ""
    typed_configs = []
    for cfg_file in ["tsconfig.json", "mypy.ini", "pyrightconfig.json", ".pyrightconfig.json"]:
        if (root / cfg_file).exists():
            typed_configs.append(cfg_file)
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(encoding="utf-8")
            if "strict" in text or "disallow_untyped" in text or "mypy" in text:
                typed_configs.append("pyproject.toml (typed)")
        except OSError:
            pass
    if typed_configs:
        type_score = "high" if len(typed_configs) >= 2 else "medium"
        type_evidence = f"Type config found: {', '.join(typed_configs)}"
    else:
        type_score = "low"
        type_evidence = "No type configuration files detected"

    # --- Module boundary clarity ---
    boundary_score = "unknown"
    boundary_evidence = ""
    arch_dir = root / "docs" / "architecture"
    boundary_docs = []
    for name in ["domain-map.md", "layering-rules.md", "current-state.md"]:
        if (arch_dir / name).exists():
            boundary_docs.append(name)
    if len(boundary_docs) >= 2:
        boundary_score = "high"
    elif boundary_docs:
        boundary_score = "medium"
    else:
        boundary_score = "low"
    boundary_evidence = f"Architecture docs found: {', '.join(boundary_docs)}" if boundary_docs else "No architecture boundary docs found"

    # --- Debt density proxy ---
    debt_score = "unknown"
    debt_evidence = ""
    try:
        result = __import__("subprocess").run(
            ["git", "grep", "-c", "-E", "TODO|FIXME|HACK|XXX"],
            cwd=str(root), capture_output=True, text=True, timeout=10,
        )
        todo_count = sum(int(l.split(":")[-1]) for l in result.stdout.splitlines() if ":" in l and l.split(":")[-1].isdigit())
        if todo_count == 0:
            debt_score = "high"
        elif todo_count < 20:
            debt_score = "medium"
        else:
            debt_score = "low"
        debt_evidence = f"{todo_count} TODO/FIXME/HACK markers found"
    except Exception:
        debt_score = "unknown"
        debt_evidence = "Could not scan for debt markers"

    scores = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
    dims = [type_score, boundary_score, debt_score]
    known = [s for s in dims if s != "unknown"]
    if known:
        avg = sum(scores[s] for s in known) / len(known)
        overall = "high" if avg >= 2.5 else "medium" if avg >= 1.5 else "low"
    else:
        overall = "unknown"

    return {
        "overall": overall,
        "dimensions": {
            "type_coverage": {"score": type_score, "evidence": type_evidence},
            "boundary_clarity": {"score": boundary_score, "evidence": boundary_evidence},
            "debt_density": {"score": debt_score, "evidence": debt_evidence},
        },
    }


def _audit_harness_coverage(root: Path) -> dict[str, Any]:
    """Report which harness dimensions have at least one sensor configured."""
    cfg = _read_workflow_config(root)
    sensors = _read_project_sensors(root)
    required_lanes = _read_project_required_review_lanes(root)
    lanes_lower = [l.lower() for l in required_lanes]

    maintainability_covered = len(sensors) > 0
    architecture_covered = any("architecture" in l for l in lanes_lower)
    behaviour_covered = (
        any(l in ("security", "security-review", "performance", "performance-review") for l in lanes_lower)
        or bool(cfg.get("test_runner"))
    )

    dimensions = {
        "maintainability": {"covered": maintainability_covered, "signal": "computational sensors" if maintainability_covered else None},
        "architecture": {"covered": architecture_covered, "signal": "architecture-review lane" if architecture_covered else None},
        "behaviour": {"covered": behaviour_covered, "signal": "security/performance lanes or test_runner" if behaviour_covered else None},
    }
    covered_count = sum(1 for d in dimensions.values() if d["covered"])
    return {
        "coverage_ratio": f"{covered_count}/3",
        "covered_count": covered_count,
        "dimensions": dimensions,
    }


def _audit_harness_coherence(root: Path) -> dict[str, Any]:
    """Scan seed surface for stale tool references and known contradiction patterns."""
    seed_dirs = [
        root / ".wavefoundry" / "framework" / "seeds",
        root / "docs" / "prompts",
    ]
    # Collect live MCP tool names from this server module
    live_tools: set[str] = set()
    try:
        import re as _re
        src = Path(__file__).read_text(encoding="utf-8")
        live_tools = set(_re.findall(r'def (wave_\w+|docs_search|code_\w+|seed_get)\(', src))
    except Exception:
        pass

    findings = []
    scanned_files = 0

    for seed_dir in seed_dirs:
        if not seed_dir.is_dir():
            continue
        for f in sorted(seed_dir.glob("*.md")):
            try:
                text = f.read_text(encoding="utf-8")
            except OSError:
                continue
            scanned_files += 1
            rel = str(f.relative_to(root))

            # Check for stale tool references (tool names mentioned but not in live set)
            import re as _re2
            mentioned = set(_re2.findall(r'\b(wave_\w+|docs_search|code_\w+|seed_get)\b', text))
            for tool in sorted(mentioned):
                # Strip trailing punctuation artefacts and check
                clean = tool.rstrip("_")
                if clean not in live_tools and clean + "_response" not in live_tools:
                    # Exclude common false positives (e.g. wave_new_* family covered by pattern)
                    if not any(clean.startswith(p) for p in ("wave_new_", "wave_list_", "wave_get_", "wave_set_")):
                        findings.append({"file": rel, "type": "stale_tool_reference", "detail": f"Tool '{clean}' mentioned but not found in live MCP surface"})

            # Check for bypass patterns (skip + gate/lane in same sentence)
            lines = text.splitlines()
            for i, line in enumerate(lines):
                ll = line.lower()
                if ("skip" in ll or "bypass" in ll or "omit" in ll) and ("gate" in ll or "required_review" in ll or "operator-signoff" in ll):
                    findings.append({"file": rel, "type": "bypass_pattern", "detail": f"Line {i+1}: possible gate/lane bypass instruction"})

    return {
        "scanned_files": scanned_files,
        "findings": findings[:50],  # cap at 50 to avoid overwhelming response
        "findings_count": len(findings),
    }


def _select_prepare_council_rotating_seat(wave_text: str) -> tuple[str | None, str]:
    """Select the rotating Wave Council seat for the prepare-phase review.

    Heuristic (first match wins; documented explicitly per 12sp5 AC-2):
    1. docs-contract-reviewer  — wave objective/watchpoints reference seeds, prompts, docs, or templates
    2. security-reviewer       — wave objective/watchpoints reference auth, security, trust, vulnerability,
                                  permission, credential, or secret
    3. architecture-reviewer   — wave objective/watchpoints reference architecture, boundary, structural,
                                  refactor, or layering
    4. code-reviewer           — wave objective/watchpoints reference server_impl, MCP, api, endpoint,
                                  or tool surface
    5. (no rotating seat)      — no clear domain signal; red-team only
    """
    probe = wave_text.casefold()
    if any(kw in probe for kw in ("seed", "prompt", "template", "doc authoring", "seed prompt")):
        return "docs-contract-reviewer", "Wave references seed/prompt authoring or documentation changes"
    if any(kw in probe for kw in ("auth", "security", "trust boundary", "vulnerability", "credential", "permission", "secret")):
        return "security-reviewer", "Wave references authentication, security, or trust boundary changes"
    if any(kw in probe for kw in ("architecture", "boundary", "structural", "refactor", "layering")):
        return "architecture-reviewer", "Wave references architectural or structural changes"
    if any(kw in probe for kw in ("server_impl", "mcp tool", "mcp surface", "api endpoint", "tool registration")):
        return "code-reviewer", "Wave references MCP tool or API surface changes"
    return None, "No clear domain signal; red-team fixed seat only"


def _prepare_council_verdict_present(wave_text: str) -> bool:
    """True if ## Review Checkpoints contains a prepare-council verdict line."""
    _heading_pat = re.compile(r"^(#{1,6} .+)$", re.MULTILINE)
    headings = list(_heading_pat.finditer(wave_text))
    for i, m in enumerate(headings):
        if m.group(1).strip() == "## Review Checkpoints":
            end = headings[i + 1].start() if i + 1 < len(headings) else len(wave_text)
            checkpoints = wave_text[m.end():end]
            return "prepare-council" in checkpoints.casefold()
    return False


def _build_prepare_council_brief(wave_id: str, wave_text: str, change_ids: list[str]) -> dict[str, Any]:
    """Build the council review brief returned by wave_prepare when no verdict is recorded."""
    rotating_seat, rotating_seat_reason = _select_prepare_council_rotating_seat(wave_text)
    seats = ["red-team (fixed)"]
    if rotating_seat:
        seats.append(f"{rotating_seat} (rotating)")
    return {
        "wave_id": wave_id,
        "change_count": len(change_ids),
        "fixed_seat": "red-team",
        "rotating_seat": rotating_seat,
        "rotating_seat_reason": rotating_seat_reason,
        "council_seats": seats,
        "instructions": (
            "Run each council seat in isolation against the admitted change docs and wave record. "
            "Have council-moderator synthesize findings. "
            "Record the verdict in ## Review Checkpoints with a 'prepare-council' marker "
            "(e.g. '- **Prepare-phase Wave Council — <date>: PASS** (red-team fixed seat; "
            f"{rotating_seat + ' rotating seat' if rotating_seat else 'red-team only'})') "
            "before calling wave_prepare(mode='create')."
        ),
        "verdict_format": (
            f"- **Prepare-phase Wave Council — <date>: PASS** "
            f"(red-team fixed seat{'; ' + rotating_seat + ' rotating seat' if rotating_seat else ''})"
        ),
    }


def wave_prepare_response(root: Path, wave_id: str, mode: str = "dry_run", cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    mode_s = "create" if (mode or "").strip().lower() == "apply" else (mode or "").strip().lower()
    if mode_s not in {"dry_run", "create"}:
        return _response("error", {"wave_id": wave_id, "mode": mode}, diagnostics=[_diagnostic("invalid_arguments", f"Unsupported mode '{mode}'.")], next_tools=["wave_help"], usage="wave_help()")
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id, "mode": mode_s}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
    text = wave_md.read_text(encoding="utf-8")
    change_ids = _extract_change_ids_from_wave_text(text)
    diagnostics: list[dict[str, Any]] = []
    _ac_advisories: list[dict[str, Any]] = []
    repairs_needed = 0
    repaired = 0
    updated = False
    if not change_ids:
        diagnostics.append(_diagnostic("no_admitted_changes", "Wave has no admitted changes."))
    for admitted_change in change_ids:
        location = _change_location_state(root, wave_md, admitted_change)
        change_path: Optional[Path] = None
        if location["staged_exists"] and location["wave_exists"]:
            diagnostics.append(
                _diagnostic(
                    "duplicate_change_doc_locations",
                    f"Admitted change '{admitted_change}' exists in both {_repo_rel(root, location['staged_path'])} and {_repo_rel(root, location['wave_path'])}.",
                    recovery_tools=["wave_get_change"],
                    recovery_usage=f"wave_get_change(change_id={admitted_change!r})",
                )
            )
            continue
        if location["wave_exists"]:
            change_path = location["wave_path"]
        elif location["staged_exists"]:
            repairs_needed += 1
            if mode_s == "create":
                try:
                    _move_change_doc(location["staged_path"], location["wave_path"])
                except OSError as exc:
                    diagnostics.append(
                        _diagnostic(
                            "change_relocation_failed",
                            f"Failed to relocate admitted change '{admitted_change}' during prepare: {exc}",
                            recovery_tools=["wave_get_change"],
                            recovery_usage=f"wave_get_change(change_id={admitted_change!r})",
                        )
                    )
                    continue
                repaired += 1
                updated = True
                change_path = location["wave_path"]
            else:
                diagnostics.append(
                    _diagnostic(
                        "change_doc_not_relocated",
                        f"Admitted change '{admitted_change}' is still staged at {_repo_rel(root, location['staged_path'])}; prepare must relocate it to {_repo_rel(root, location['wave_path'])}.",
                        recovery_tools=["wave_prepare"],
                        recovery_usage=f"wave_prepare(wave_id={wave_md.parent.name!r}, mode='create')",
                    )
                )
                continue
        else:
            diagnostics.append(
                _diagnostic(
                    "change_not_found",
                    f"Admitted change '{admitted_change}' was not found in {_repo_rel(root, location['staged_path'])} or {_repo_rel(root, location['wave_path'])}.",
                    recovery_tools=["wave_get_change", "wave_list_plans"],
                    recovery_usage=f"wave_get_change(change_id={admitted_change!r})",
                )
            )
            continue
        try:
            change_text = change_path.read_text(encoding="utf-8")
        except OSError as exc:
            diagnostics.append(
                _diagnostic(
                    "change_doc_unreadable",
                    f"Could not read admitted change '{admitted_change}' at {_repo_rel(root, change_path)}: {exc}",
                    recovery_tools=["wave_get_change"],
                    recovery_usage=f"wave_get_change(change_id={admitted_change!r})",
                )
            )
            continue
        missing_headers = _missing_required_change_sections(change_text)
        if missing_headers:
            diagnostics.append(
                _diagnostic(
                    "change_doc_missing_sections",
                    f"Admitted change '{admitted_change}' is missing sections: {', '.join(missing_headers)}.",
                    recovery_tools=["wave_get_change"],
                    recovery_usage=f"wave_get_change(change_id={admitted_change!r})",
                )
            )
        # AC priority advisory (non-blocking): warn if every AC row still has unpopulated placeholder text
        _AC_PLACEHOLDER = "required / important / nice-to-have / not-this-scope"
        if "## AC Priority" in change_text:
            ac_section_start = change_text.find("## AC Priority")
            ac_section = change_text[ac_section_start:]
            ac_rows = [line for line in ac_section.splitlines() if line.strip().startswith("| AC-")]
            if ac_rows and all(_AC_PLACEHOLDER in row for row in ac_rows):
                _ac_advisories.append(
                    _diagnostic(
                        "ac_priority_unpopulated",
                        f"Change '{admitted_change}' AC priority table still contains only placeholder text. Fill in priority values (required / important / nice-to-have / not-this-scope) for each AC row before closing the wave.",
                        recovery_tools=["wave_get_change"],
                        recovery_usage=f"wave_get_change(change_id={admitted_change!r})",
                    )
                )
    # Garden and lint only run on create — dry-run must stay read-only.
    required_council_signoffs = _required_wave_council_signoffs(root, "prepare")
    if required_council_signoffs:
        missing_council = [
            signoff_key
            for signoff_key in required_council_signoffs
            if not _lane_has_signoff_in_evidence(_combined_review_evidence(text), signoff_key)
        ]
        if missing_council:
            diagnostics.append(
                _diagnostic(
                    "missing_wave_council_signoff",
                    (
                        "Required Wave Council signoff missing for prepare: "
                        f"{', '.join(missing_council)}. Record the signoff line(s) in `## Review Evidence` before the wave can become active."
                    ),
                    recovery_tools=["wave_current"],
                    recovery_usage="wave_current()",
                )
            )
    garden_passed = True
    lint_passed = True
    if mode_s == "create":
        garden_result = run_garden(root)
        garden_passed = garden_result["passed"]
        if not garden_passed:
            diagnostics.append(_diagnostic("docs_gardener_failed", "docs_gardener failed during prepare.", recovery_tools=["wave_garden", "wave_validate"], recovery_usage="wave_garden(mode='run')"))
    lint_result = run_validate(root)
    lint_passed = lint_result["passed"]
    if not lint_passed:
        diagnostics.extend(_diagnostic("docs_lint_error", err, recovery_tools=["wave_validate"]) for err in lint_result["errors"])
    # Single-active-wave guard: block prepare when another wave is already active.
    # Keyed on "is any other wave active?" — self-transitions (active→active or paused→active
    # on the target wave) are not blocked by this check.
    other_active = _find_other_active_wave(root, wave_md, cache=cache)
    guard_data: dict[str, Any] = {}
    if other_active is not None:
        guard_data = {
            "active_wave_id": other_active["wave_id"],
            "active_wave_path": _repo_rel(root, Path(other_active["path"])),
        }
        diagnostics.append(
            _diagnostic(
                "another_wave_active",
                f"Wave {other_active['wave_id']!r} is already active. Pause it before preparing {wave_id!r}.",
                recovery_tools=["wave_pause", "wave_current"],
                recovery_usage=f"wave_pause(wave_id={other_active['wave_id']!r}, mode='create')",
            )
        )
    if diagnostics:
        error_data = {"wave_id": wave_id, "mode": mode_s, "change_count": len(change_ids), "lint_passed": lint_passed, "garden_passed": garden_passed, "repairs_needed": repairs_needed, "repaired": repaired}
        error_data["required_council_signoffs"] = required_council_signoffs
        error_data.update(guard_data)
        next_tools_list = ["wave_pause", "wave_current"] if other_active is not None else ["wave_validate", "wave_current"]
        usage_hint = f"wave_pause(wave_id={other_active['wave_id']!r}, mode='create')" if other_active is not None else "wave_validate()"
        return _response("error", error_data, diagnostics=diagnostics, next_tools=next_tools_list, usage=usage_hint)
    # Prepare-phase Wave Council review — final step of wave_prepare (12sp5).
    # Always generate the council brief; block create-mode completion until verdict is recorded.
    council_brief = _build_prepare_council_brief(wave_id, text, change_ids)
    verdict_present = _prepare_council_verdict_present(text)
    if not verdict_present:
        council_usage = (
            "Run the prepare-phase Wave Council review now (seats and scope in council_brief), "
            "record the verdict in ## Review Checkpoints with a 'prepare-council' marker, "
            "then call wave_prepare(mode='create') to complete prepare."
        )
        if mode_s == "create":
            return _response(
                "ready_for_council_review",
                {"wave_id": wave_id, "mode": mode_s, "council_brief": council_brief},
                diagnostics=[_diagnostic(
                    "prepare_council_verdict_missing",
                    "Technical checks passed. Ready to run prepare-phase Wave Council review. "
                    "Run each council seat in isolation against the admitted change docs, "
                    "record the verdict in ## Review Checkpoints with a 'prepare-council' marker, "
                    "then call wave_prepare(mode='create') again to complete prepare.",
                    recovery_tools=["wave_prepare"],
                    recovery_usage="wave_prepare(mode='create')",
                )],
                next_tools=["wave_prepare"],
                usage=council_usage,
            )
        # dry_run: include brief as advisory, don't block
        _ac_advisories.append(_diagnostic(
            "prepare_council_verdict_missing",
            "Technical checks passed. Ready to run prepare-phase Wave Council review. "
            "Run the council review and record the verdict before calling wave_prepare(mode='create').",
            recovery_tools=["wave_prepare"],
            recovery_usage="wave_prepare(mode='create')",
        ))
    if mode_s == "create":
        status_match = _STATUS_PATTERN.search(text)
        if status_match and status_match.group(1) != "active":
            text = text[:status_match.start(1)] + "active" + text[status_match.end(1):]
            wave_md.write_text(text, encoding="utf-8")
            updated = True
        if cache and updated:
            cache.invalidate()
        _trigger_background_index_refresh_for_paths(
            root,
            [wave_md, *(_wave_change_doc_path(root, wave_md, change_id) for change_id in change_ids)],
        )
    resp_data = {"wave_id": wave_id, "mode": mode_s, "change_count": len(change_ids), "lint_passed": lint_passed, "garden_passed": garden_passed, "updated": updated, "repairs_needed": repairs_needed, "repaired": repaired, "required_council_signoffs": required_council_signoffs, "council_brief": council_brief, "council_verdict_present": verdict_present}
    return _response("dry_run" if mode_s == "dry_run" else "ok", resp_data, diagnostics=_ac_advisories if _ac_advisories else None, next_tools=["wave_current"], usage="wave_current()")


def wave_pause_response(root: Path, wave_id: str, mode: str = "dry_run", cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    mode_s = "create" if (mode or "").strip().lower() == "apply" else (mode or "").strip().lower()
    if mode_s not in {"dry_run", "create"}:
        return _response("error", {"wave_id": wave_id, "mode": mode}, diagnostics=[_diagnostic("invalid_arguments", f"Unsupported mode '{mode}'.")], next_tools=["wave_help"], usage="wave_help()")
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id, "mode": mode_s}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
    handoff = root / "docs" / "agents" / "session-handoff.md"
    rel = str(handoff.relative_to(root)).replace("\\", "/")
    # Compute the wave-status transition. Only active → paused writes; other states are no-ops.
    wave_text = wave_md.read_text(encoding="utf-8")
    status_match = _STATUS_PATTERN.search(wave_text)
    current_status = status_match.group(1) if status_match else ""
    if current_status in ("active", "implementing"):
        status_transition = {"from": current_status, "to": "paused"}
    elif current_status == "paused":
        status_transition = {"from": "paused", "to": "paused"}
    else:
        status_transition = {"from": current_status, "to": current_status}
    diagnostics: list[dict[str, Any]] = []
    if current_status not in ("active", "implementing", "paused"):
        diagnostics.append(
            _diagnostic(
                "pause_on_non_active_wave",
                f"Wave '{wave_id}' is not active (status: {current_status!r}). Handoff entry was written but wave status was not changed.",
                recovery_tools=["wave_current"],
                recovery_usage="wave_current()",
            )
        )
    diagnostics.extend(_force_gates_closed(root, mode_s))
    if mode_s == "create":
        # Transition wave status first, then write the handoff entry.
        if status_transition["from"] in ("active", "implementing") and status_transition["to"] == "paused":
            new_text = wave_text[:status_match.start(1)] + "paused" + wave_text[status_match.end(1):]
            wave_md.write_text(new_text, encoding="utf-8")
        handoff.parent.mkdir(parents=True, exist_ok=True)
        prior = handoff.read_text(encoding="utf-8") if handoff.exists() else ""
        handoff.write_text(_update_handoff_wave_ref(prior, wave_id), encoding="utf-8")
        if cache:
            cache.invalidate()
        _trigger_background_index_refresh_for_paths(root, [handoff, wave_md])
    return _response(
        "dry_run" if mode_s == "dry_run" else "ok",
        {
            "wave_id": wave_id,
            "mode": mode_s,
            "path": rel,
            "written": mode_s == "create",
            "status_transition": status_transition,
        },
        diagnostics=diagnostics if diagnostics else None,
        next_tools=["wave_current"],
        usage="wave_current()",
    )


def _operator_signoff_present(wave_text: str) -> bool:
    """True if Review Evidence contains an operator-signoff line."""
    return _lane_has_signoff_in_evidence(_combined_review_evidence(wave_text), "operator-signoff")


_SEVERITY_ORDER = ["none", "low", "medium", "high", "critical"]


def _max_severity_from_evidence(wave_text: str) -> str:
    """Scan Review Evidence signoff lines for severity annotations; return highest found."""
    evidence = _combined_review_evidence(wave_text)
    max_rank = 0
    for raw in evidence.splitlines():
        line = raw.strip().lower()
        if not line or line.startswith("#") or "<" in line:
            continue
        for sev in _SEVERITY_ORDER:
            if sev in line and line.index(sev) > 0:
                rank = _SEVERITY_ORDER.index(sev)
                if rank > max_rank:
                    max_rank = rank
    return _SEVERITY_ORDER[max_rank]


def wave_review_response(root: Path, wave_id: str, phase: str = "implementation") -> dict[str, Any]:
    phase_s = (phase or "implementation").strip().lower()
    if phase_s not in ("prepare", "implementation"):
        return _response("error", {"wave_id": wave_id, "phase": phase_s}, diagnostics=[_diagnostic("invalid_arguments", f"Invalid phase '{phase_s}'. Valid values: 'prepare', 'implementation'.")], next_tools=["wave_help"], usage="wave_help()")
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
    _trigger_background_index_refresh_for_paths(root, [wave_md])
    lint_result = run_validate(root)
    wave_text = wave_md.read_text(encoding="utf-8")
    # Merge lanes from wave.md Participants table and project-declared required_review_lanes
    wave_lanes = _extract_required_review_lanes(wave_text)
    project_lanes = _read_project_required_review_lanes(root)
    extra_lanes = [l for l in project_lanes if l not in wave_lanes]
    required_lanes = (["operator"] + wave_lanes + extra_lanes) if phase_s == "implementation" else wave_lanes + extra_lanes

    if phase_s == "prepare":
        # Prepare-phase: check signoffs in ## Prepare Review Evidence (no operator signoff required)
        evidence = _prepare_review_evidence(wave_text)
        lane_results = [{"lane": lane, "recorded_signoff": _lane_has_signoff_in_evidence(evidence, lane)} for lane in required_lanes]
        diagnostics = [] if lint_result["passed"] else [_diagnostic("docs_lint_error", err, recovery_tools=["wave_validate"]) for err in lint_result["errors"]]
        missing = [entry["lane"] for entry in lane_results if not entry["recorded_signoff"]]
        if missing:
            diagnostics.append(_diagnostic(
                "missing_required_lane",
                f"Prepare-phase review lanes without recorded signoff in `## Prepare Review Evidence`: {', '.join(missing)}. "
                "Record each lane signoff in the `## Prepare Review Evidence` section of wave.md before running wave_implement.",
                recovery_tools=["wave_current"],
                recovery_usage="wave_current()",
            ))
        status = "ok" if lint_result["passed"] and not missing else "error"
        return _response(
            status,
            {"wave_id": wave_id, "phase": phase_s, "required_lanes": required_lanes, "lane_results": lane_results, "lint_passed": lint_result["passed"]},
            diagnostics=diagnostics,
            next_tools=["wave_implement", "wave_current"],
            usage=f"wave_implement(wave_id={wave_id!r}, mode='dry_run')",
        )

    # Implementation phase (default): current behavior — check ## Review Evidence
    operator_signed = _operator_signoff_present(wave_text)
    lane_results = [{"lane": "operator", "recorded_signoff": operator_signed}] + [{"lane": lane, "recorded_signoff": _lane_has_signoff(wave_text, lane)} for lane in required_lanes[1:]]
    required_council_signoffs = _required_wave_council_signoffs(root, "review", wave_text=wave_text)
    council_results = [
        {"signoff_key": signoff_key, "recorded_signoff": _lane_has_signoff(wave_text, signoff_key)}
        for signoff_key in required_council_signoffs
    ]
    diagnostics = [] if lint_result["passed"] else [_diagnostic("docs_lint_error", err, recovery_tools=["wave_validate"]) for err in lint_result["errors"]]
    missing = [entry["lane"] for entry in lane_results if not entry["recorded_signoff"]]
    if "operator" in missing:
        diagnostics.append(_diagnostic(
            "missing_operator_signoff",
            "Operator review approval is required before closing this wave. "
            "Add `operator-signoff: approved` to `## Review Evidence` in wave.md. "
            "Approval is given by the operator asking to close the wave, or by the agent explicitly asking for approval.",
            recovery_tools=["wave_current"],
            recovery_usage="wave_current()",
        ))
    other_missing = [m for m in missing if m != "operator"]
    if other_missing:
        diagnostics.append(_diagnostic(
            "missing_required_lane",
            f"Required review lanes without recorded signoff: {', '.join(other_missing)}.",
            recovery_tools=["wave_current"],
            recovery_usage="wave_current()",
        ))
    missing_council = [entry["signoff_key"] for entry in council_results if not entry["recorded_signoff"]]
    if missing_council:
        diagnostics.append(_diagnostic(
            "missing_wave_council_signoff",
            (
                "Required Wave Council signoff missing for review: "
                f"{', '.join(missing_council)}. Record the signoff line(s) in `## Review Evidence` before closing the wave."
            ),
            recovery_tools=["wave_current"],
            recovery_usage="wave_current()",
        ))
    max_severity = _max_severity_from_evidence(wave_text)
    if max_severity in ("critical", "high"):
        diagnostics.append(_diagnostic(
            "high_severity_finding",
            f"Sensor findings include {max_severity}-severity issues — prioritise operator review of these before closing.",
            recovery_tools=["wave_current"],
            recovery_usage="wave_current()",
        ))
    status = "ok" if lint_result["passed"] and not missing and not missing_council else "error"
    return _response(
        status,
        {"wave_id": wave_id, "phase": phase_s, "required_lanes": required_lanes, "lane_results": lane_results, "required_council_signoffs": required_council_signoffs, "council_results": council_results, "lint_passed": lint_result["passed"], "max_severity": max_severity},
        diagnostics=diagnostics,
        next_tools=["wave_validate", "wave_current"],
        usage="wave_validate()",
    )


def wave_implement_response(root: Path, wave_id: str, mode: str = "dry_run", cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    """Gate and context builder for starting wave implementation (12sqb).

    Checks:
    1. Wave is active (not already implementing, not planned/paused/closed).
    2. Automated prepare-phase Wave Council verdict is recorded (12sp5).
    3. All required prepare-phase lane reviews are recorded in ## Prepare Review Evidence.

    On create: transitions wave status to 'implementing'.
    Returns ordered change list, Journal Watchpoints, and serialization points.
    """
    mode_s = "create" if (mode or "").strip().lower() == "apply" else (mode or "").strip().lower()
    _VALID_MODES = ["dry_run", "create"]
    if mode_s not in _VALID_MODES:
        return _response("error", {"wave_id": wave_id, "mode": mode, "valid_modes": _VALID_MODES}, diagnostics=[_diagnostic("invalid_arguments", f"Unsupported mode '{mode}'. Valid modes: {_VALID_MODES}.")], next_tools=["wave_help"], usage="wave_help()")
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")

    wave_text = wave_md.read_text(encoding="utf-8")
    status_match = _STATUS_PATTERN.search(wave_text)
    current_status = (status_match.group(1) if status_match else "").lower()

    if current_status == "implementing":
        return _response("ok", {"wave_id": wave_id, "mode": mode_s, "status": "implementing", "already_implementing": True}, next_tools=["wave_current", "wave_review"], usage="wave_current()")
    if current_status != "active":
        return _response(
            "error",
            {"wave_id": wave_id, "mode": mode_s, "status": current_status},
            diagnostics=[_diagnostic("wave_not_active", f"wave_implement requires an active wave; '{wave_id}' has status '{current_status}'.", recovery_tools=["wave_prepare", "wave_current"], recovery_usage=f"wave_prepare(wave_id={wave_id!r}, mode='dry_run')")],
            next_tools=["wave_prepare", "wave_current"],
            usage=f"wave_prepare(wave_id={wave_id!r}, mode='dry_run')",
        )

    diagnostics: list[dict[str, Any]] = []

    # Gate 1: council verdict
    if not _prepare_council_verdict_present(wave_text):
        diagnostics.append(_diagnostic(
            "prepare_council_verdict_missing",
            "No prepare-phase Wave Council verdict found in `## Review Checkpoints`. "
            "Run the council review (red-team fixed seat + rotating seat) and record the verdict "
            "with a 'prepare-council' marker before calling wave_implement.",
            recovery_tools=["wave_prepare", "wave_current"],
            recovery_usage=f"wave_prepare(wave_id={wave_id!r}, mode='dry_run')",
        ))

    # Gate 2: prepare-phase lane review
    wave_lanes = _extract_required_review_lanes(wave_text)
    project_lanes = _read_project_required_review_lanes(root)
    required_lanes = wave_lanes + [l for l in project_lanes if l not in wave_lanes]
    if required_lanes:
        evidence = _prepare_review_evidence(wave_text)
        missing_lanes = [lane for lane in required_lanes if not _lane_has_signoff_in_evidence(evidence, lane)]
        if missing_lanes:
            diagnostics.append(_diagnostic(
                "prepare_review_incomplete",
                f"Prepare-phase lane review incomplete — missing signoffs in `## Prepare Review Evidence`: {', '.join(missing_lanes)}. "
                "Run wave_review(phase='prepare') and record each lane signoff before calling wave_implement.",
                recovery_tools=["wave_review", "wave_current"],
                recovery_usage=f"wave_review(wave_id={wave_id!r}, phase='prepare')",
            ))
    else:
        missing_lanes = []

    if diagnostics:
        return _response("error", {"wave_id": wave_id, "mode": mode_s}, diagnostics=diagnostics, next_tools=["wave_review", "wave_current"], usage=f"wave_review(wave_id={wave_id!r}, phase='prepare')")

    # All gates passed — build implementation context
    change_ids = _extract_change_ids_from_wave_text(wave_text)

    # Ordered changes: extract status + dependencies from each change doc
    ordered_changes: list[dict[str, Any]] = []
    for cid in change_ids:
        change_path = wave_md.parent / f"{cid}.md"
        if not change_path.exists():
            ordered_changes.append({"change_id": cid, "status": "unknown", "depends_on": []})
            continue
        ct = change_path.read_text(encoding="utf-8")
        status_m = _CHANGE_STATUS_PATTERN.search(ct)
        cs = status_m.group(1) if status_m else "unknown"
        deps_m = re.findall(r"Depends On:\s*`([^`]+)`", ct)
        ordered_changes.append({"change_id": cid, "status": cs, "depends_on": deps_m})

    # Journal Watchpoints section
    watchpoints_text = ""
    wp_idx = wave_text.find("## Journal Watchpoints")
    if wp_idx != -1:
        tail = wave_text[wp_idx + len("## Journal Watchpoints"):]
        nl = tail.find("\n")
        if nl != -1:
            tail = tail[nl + 1:]
        m_end = re.search(r"\n(?=## )", tail)
        watchpoints_text = (tail[: m_end.start()] if m_end else tail).strip()

    # Serialization points: changes that other changes depend on
    all_deps: set[str] = set()
    for c in ordered_changes:
        all_deps.update(c["depends_on"])
    serialization_points = [cid for cid in change_ids if cid in all_deps]

    if mode_s == "create":
        new_text = wave_text[:status_match.start(1)] + "implementing" + wave_text[status_match.end(1):]
        wave_md.write_text(new_text, encoding="utf-8")
        if cache:
            cache.invalidate()

    resp_data = {
        "wave_id": wave_id,
        "mode": mode_s,
        "status_transition": {"from": "active", "to": "implementing"} if mode_s == "create" else {"from": "active", "to": "active (dry_run)"},
        "ordered_changes": ordered_changes,
        "journal_watchpoints": watchpoints_text,
        "serialization_points": serialization_points,
    }
    return _response(
        "dry_run" if mode_s == "dry_run" else "ok",
        resp_data,
        next_tools=["wave_current", "wave_review"],
        usage="wave_current()",
    )


def _generate_wave_close_summary(wave_id: str, wave_text: str, wave_md: Path) -> str:
    """Synthesize a wave close summary from structured fields in the wave record and change docs.

    Format: one or more prose paragraphs followed by optional per-change bullet points.
    Reads completed ACs ([x] lines), progress log entries, and decision log entries from
    each admitted change doc. Does not require operator input.
    """
    # Extract wave title
    title_m = re.search(r"^Title:\s*(.+)$", wave_text, re.MULTILINE)
    wave_title = title_m.group(1).strip() if title_m else wave_id

    change_ids = _extract_change_ids_from_wave_text(wave_text)

    def _section_body(text: str, heading: str) -> str:
        idx = text.find(heading)
        if idx == -1:
            return ""
        tail = text[idx + len(heading):]
        nl = tail.find("\n")
        if nl != -1:
            tail = tail[nl + 1:]
        m = re.search(r"\n(?=## )", tail)
        return (tail[: m.start()] if m else tail).strip()

    change_summaries: list[dict] = []
    for cid in change_ids:
        change_path = wave_md.parent / f"{cid}.md"
        if not change_path.exists():
            change_summaries.append({"id": cid, "title": cid, "completed_acs": [], "decisions": [], "progress": []})
            continue
        ct = change_path.read_text(encoding="utf-8")
        # Title from H1
        h1_m = re.search(r"^#\s+(.+)$", ct, re.MULTILINE)
        title = h1_m.group(1).strip() if h1_m else cid
        # Completed ACs: [x] lines in Acceptance Criteria
        ac_body = _section_body(ct, "## Acceptance Criteria")
        completed_acs = [line.strip()[5:].strip() for line in ac_body.splitlines() if re.match(r"\s*-\s*\[x\]", line, re.IGNORECASE)]
        # Progress log: data rows (skip header)
        progress_body = _section_body(ct, "## Progress Log")
        progress_entries = []
        for row in progress_body.splitlines():
            cells = [c.strip() for c in row.strip("|").split("|")]
            if len(cells) >= 2 and cells[0] and cells[0].lower() not in ("date", "---", ""):
                progress_entries.append(cells[1] if len(cells) > 1 else "")
        # Decision log: data rows
        decision_body = _section_body(ct, "## Decision Log")
        decision_entries = []
        for row in decision_body.splitlines():
            cells = [c.strip() for c in row.strip("|").split("|")]
            if len(cells) >= 2 and cells[0] and cells[0].lower() not in ("date", "---", ""):
                decision_entries.append(cells[1] if len(cells) > 1 else "")
        change_summaries.append({"id": cid, "title": title, "completed_acs": completed_acs, "decisions": decision_entries, "progress": progress_entries})

    # Compose prose paragraph
    if change_summaries:
        titles = [cs["title"] for cs in change_summaries]
        if len(titles) == 1:
            delivered = f"one change: {titles[0]}"
        elif len(titles) == 2:
            delivered = f"two changes: {titles[0]} and {titles[1]}"
        else:
            delivered = f"{len(titles)} changes: {', '.join(titles[:-1])}, and {titles[-1]}"
        para = f"Wave `{wave_id}` ({wave_title}) delivered {delivered}."
    else:
        para = f"Wave `{wave_id}` ({wave_title}) closed with no admitted changes."

    # Notable pivots from progress logs
    pivots: list[str] = []
    for cs in change_summaries:
        for entry in cs["progress"]:
            lower = entry.lower()
            if any(kw in lower for kw in ("renamed", "removed", "consolidated", "added", "scope", "pivot", "revert", "expanded")):
                pivots.append(f"{cs['title']}: {entry}")
    if pivots:
        para += " Notable adjustments during implementation: " + "; ".join(pivots[:3]) + ("." if not pivots[0].endswith(".") else "")

    lines = [para, ""]

    # Per-change bullet points if there are decisions or completed ACs worth surfacing
    any_detail = any(cs["decisions"] or cs["completed_acs"] for cs in change_summaries)
    if any_detail and change_summaries:
        lines.append("**Changes delivered:**")
        lines.append("")
        for cs in change_summaries:
            ac_count = len(cs["completed_acs"])
            decisions = cs["decisions"]
            bullet = f"- **{cs['title']}** (`{cs['id']}`)"
            if ac_count:
                bullet += f" — {ac_count} AC{'s' if ac_count != 1 else ''} completed"
            if decisions:
                bullet += (". Key decisions: " if ac_count else " — ") + "; ".join(decisions[:2])
            lines.append(bullet)

    return "\n".join(lines)


def _replace_wave_summary_section(text: str, summary: str) -> str:
    """Replace the content of ## Wave Summary with the generated summary."""
    marker = "## Wave Summary"
    idx = text.find(marker)
    if idx == -1:
        return text
    # Find end of section (next ## heading or end of file)
    tail_start = idx + len(marker)
    nl = text.find("\n", tail_start)
    if nl != -1:
        body_start = nl + 1
    else:
        body_start = tail_start
    tail = text[body_start:]
    m_end = re.search(r"\n(?=## )", tail)
    body_end = body_start + (m_end.start() + 1 if m_end else len(tail))
    return text[:body_start] + "\n" + summary + "\n" + text[body_end:]


def wave_close_response(root: Path, wave_id: str, mode: str = "dry_run", cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    mode_s = "create" if (mode or "").strip().lower() == "apply" else (mode or "").strip().lower()
    _WAVE_CLOSE_VALID_MODES = ["dry_run", "create"]
    if mode_s not in {"dry_run", "create"}:
        return _response("error", {"wave_id": wave_id, "mode": mode, "valid_modes": _WAVE_CLOSE_VALID_MODES}, diagnostics=[_diagnostic("invalid_arguments", f"Unsupported mode '{mode}'. Valid modes: {_WAVE_CLOSE_VALID_MODES}.")], next_tools=["wave_help"], usage="wave_help()")
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
    # Garden only runs on create — dry-run must stay read-only.
    garden_passed = True
    if mode_s == "create":
        garden_result = run_garden(root)
        garden_passed = garden_result["passed"]
    lint_result = run_validate(root)
    text = wave_md.read_text(encoding="utf-8")
    statuses = [status.lower() for status in _CHANGE_STATUS_PATTERN.findall(text)]
    open_statuses = {"stub", "planned", "ready", "active"}
    unresolved = [s for s in statuses if s in open_statuses]
    diagnostics: list[dict[str, Any]] = []
    if not garden_passed:
        diagnostics.append(_diagnostic("docs_gardener_failed", "docs_gardener failed during close.", recovery_tools=["wave_garden", "wave_validate"], recovery_usage="wave_garden(mode='run')"))
    if unresolved:
        diagnostics.append(_diagnostic("open_changes_remaining", f"Wave has unresolved change statuses: {', '.join(sorted(set(unresolved)))}.", recovery_tools=["wave_current"], recovery_usage="wave_current()"))
    if not _operator_signoff_present(text):
        diagnostics.append(
            _diagnostic(
                "missing_operator_signoff",
                (
                    "Operator review approval is required before closing this wave. "
                    "Add `operator-signoff: approved` to `## Review Evidence` in wave.md. "
                    "Approval is given by the operator asking to close the wave, or by the agent explicitly asking for approval."
                ),
                recovery_tools=["wave_review"],
                recovery_usage=f"wave_review(wave_id={wave_id!r})",
            )
        )
    # Merge lanes from wave.md Participants table and project-declared required_review_lanes
    wave_lanes = _extract_required_review_lanes(text)
    project_lanes = _read_project_required_review_lanes(root)
    required_lanes = list({*wave_lanes, *project_lanes})  # deduped, order doesn't matter here
    required_council_signoffs = _required_wave_council_signoffs(root, "close", wave_text=text)
    evidence_present = bool(_combined_review_evidence(text).strip())
    if required_lanes:
        if not evidence_present:
            diagnostics.append(
                _diagnostic(
                    "missing_signoff_evidence",
                    "Wave record needs a ## Review Evidence (or ## Review Signoff Evidence) section with per-lane signoffs.",
                    recovery_tools=["wave_review"],
                    recovery_usage=f"wave_review(wave_id={wave_id!r})",
                )
            )
        else:
            missing_lane = [l for l in required_lanes if not _lane_has_signoff_in_evidence(_combined_review_evidence(text), l)]
            if missing_lane:
                diagnostics.append(
                    _diagnostic(
                        "missing_required_lane",
                        f"Required review lanes without a signoff line in Review Evidence: {', '.join(missing_lane)}.",
                        recovery_tools=["wave_review"],
                        recovery_usage=f"wave_review(wave_id={wave_id!r})",
                    )
                )
    else:
        if not _review_evidence_has_any_signoff_line(text):
            diagnostics.append(
                _diagnostic(
                    "missing_signoff_evidence",
                    "Wave record needs ## Review Evidence (or ## Review Signoff Evidence) with at least one signoff line.",
                    recovery_tools=["wave_review"],
                    recovery_usage=f"wave_review(wave_id={wave_id!r})",
                )
            )
    if required_council_signoffs:
        missing_council = [
            signoff_key
            for signoff_key in required_council_signoffs
            if not _lane_has_signoff_in_evidence(_combined_review_evidence(text), signoff_key)
        ]
        if missing_council:
            diagnostics.append(
                _diagnostic(
                    "missing_wave_council_signoff",
                    (
                        "Required Wave Council signoff missing for close: "
                        f"{', '.join(missing_council)}. Record the signoff line(s) in `## Review Evidence` before attempting closure."
                    ),
                    recovery_tools=["wave_review"],
                    recovery_usage=f"wave_review(wave_id={wave_id!r})",
                )
            )
    if not lint_result["passed"]:
        diagnostics.extend([_diagnostic("docs_lint_error", err, recovery_tools=["wave_validate"]) for err in lint_result["errors"]])
    # Gate close runs unconditionally so open gates are always reported (and closed in
    # create mode) even when other diagnostics cause an early return.
    gate_diagnostics = _force_gates_closed(root, mode_s)
    if diagnostics:
        return _response("error", {"wave_id": wave_id, "mode": mode_s, "lint_passed": lint_result["passed"], "garden_passed": garden_passed, "required_council_signoffs": required_council_signoffs}, diagnostics=diagnostics + gate_diagnostics, next_tools=["wave_validate", "wave_current"], usage="wave_validate()")
    # Generate the wave summary from structured change doc fields (12sq4).
    wave_summary = _generate_wave_close_summary(wave_id, text, wave_md)
    updated = False
    handoff_rel = ""
    if mode_s == "create":
        status_match = _STATUS_PATTERN.search(text)
        if status_match and status_match.group(1) != "closed":
            import time
            # Summary write precedes status checkpoint (per 12sq4 AC risk note).
            text = _replace_wave_summary_section(text, wave_summary)
            text = text[:status_match.start(1)] + "closed" + text[status_match.end(1):]
            if "Completed At:" not in text:
                text = text.replace("## Wave Summary", f"Completed At: {time.strftime('%Y-%m-%d')}\n\n## Wave Summary", 1)
            wave_md.write_text(text, encoding="utf-8")
            updated = True
            handoff = root / "docs" / "agents" / "session-handoff.md"
            handoff.parent.mkdir(parents=True, exist_ok=True)
            prior = handoff.read_text(encoding="utf-8") if handoff.exists() else ""
            handoff.write_text(_update_handoff_wave_ref(prior, None), encoding="utf-8")
            handoff_rel = str(handoff.relative_to(root)).replace("\\", "/")
            if cache:
                cache.invalidate()
            refresh_paths: list[str | Path] = [wave_md]
            if handoff_rel:
                refresh_paths.append(handoff)
            _trigger_background_index_refresh_for_paths(root, refresh_paths)
    return _response(
        "dry_run" if mode_s == "dry_run" else "ok",
        {"wave_id": wave_id, "mode": mode_s, "updated": updated, "handoff_path": handoff_rel, "wave_summary": wave_summary},
        diagnostics=gate_diagnostics if gate_diagnostics else None,
        next_tools=["wave_current"],
        usage="wave_current()",
    )


def wave_reopen_response(root: Path, wave_id: str) -> dict[str, Any]:
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
    text = wave_md.read_text(encoding="utf-8")
    status_match = _STATUS_PATTERN.search(text)
    current_status = status_match.group(1).lower() if status_match else ""
    if current_status not in ("closed", "paused"):
        return _response("error", {"wave_id": wave_id, "current_status": current_status}, diagnostics=[_diagnostic("wave_not_closed", f"Wave '{wave_id}' has status '{current_status}' — only closed or paused waves can be reopened.", recovery_tools=["wave_current"], recovery_usage="wave_current()")], next_tools=["wave_current"], usage="wave_current()")
    # Set status back to active
    text = text[:status_match.start(1)] + "active" + text[status_match.end(1):]
    # Remove any "Completed At: ..." line stamped by wave_close
    text = re.sub(r"^Completed At:.*\n?", "", text, flags=re.MULTILINE)
    wave_md.write_text(text, encoding="utf-8")
    _trigger_background_index_refresh_for_paths(root, [wave_md])
    return _response("ok", {"wave_id": wave_id, "status": "active", "updated": True}, next_tools=["wave_current", "wave_review"], usage="wave_current()")


def _default_template() -> str:
    return """# [Change Title]

Change ID: `<id>`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: <date>
Wave: TBD

## Rationale

## Requirements

## Scope

**Problem statement:**

**In scope:**

**Out of scope:**

## Acceptance Criteria

- [ ] AC-1:
- [ ] AC-2:

## Tasks

- [ ]
- [ ]

## Affected Architecture Docs

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|----|----------|-----------|

## Progress Log

| Date | Update | Evidence |
|------|--------|---------|

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|-------------|

## Risks

| Risk | Mitigation |
|------|-----------|

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
"""


# ---------------------------------------------------------------------------
# Code navigation helpers (exact search, file listing, ranged reads, symbol nav)
# ---------------------------------------------------------------------------

def _resolve_repo_path(root: Path, user_path: str) -> Optional[Path]:
    """Resolve *user_path* to an absolute path that is guaranteed to be inside *root*.

    Returns ``None`` if the path escapes the root (path traversal attempt) or if
    it is absolute (only repo-relative paths are accepted).  The returned path is
    not guaranteed to exist — callers must check.
    """
    # Reject absolute paths immediately
    if user_path.startswith("/") or (len(user_path) > 1 and user_path[1] == ":"):
        return None
    try:
        resolved = (root / user_path).resolve()
        root_resolved = root.resolve()
        resolved.relative_to(root_resolved)  # raises ValueError if outside root
        return resolved
    except (ValueError, OSError):
        return None


def _indexer_module():
    """Import the indexer module from the framework scripts directory."""
    import importlib.util
    indexer_path = Path(__file__).parent / "indexer.py"
    spec = importlib.util.spec_from_file_location("indexer", indexer_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load indexer from {indexer_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    return mod


def _walk_repo_for_navigation(root: Path) -> list[Path]:
    """Return navigable files respecting indexer ignore/exclusion rules."""
    try:
        indexer = _indexer_module()
        return indexer.walk_repo(root)
    except Exception:
        # Fallback: simple glob without ignore support
        result = []
        for p in sorted(root.rglob("*")):
            if p.is_file() and ".git" not in p.parts:
                result.append(p)
        return result


def code_list_files_response(root: Path, glob: str = "") -> dict[str, Any]:
    """List repository files with optional glob filter."""
    try:
        all_files = _walk_repo_for_navigation(root)
    except Exception as exc:
        return _response("error", {"glob": glob}, diagnostics=[_diagnostic("navigation_error", f"File listing failed: {exc}")], next_tools=["wave_help"], usage="wave_help()")

    root_r = root.resolve()
    if glob:
        import fnmatch
        paths = [
            str(p.resolve().relative_to(root_r)).replace("\\", "/")
            for p in all_files
            if fnmatch.fnmatch(str(p.resolve().relative_to(root_r)).replace("\\", "/"), glob)
            or fnmatch.fnmatch(p.name, glob)
        ]
    else:
        paths = [str(p.resolve().relative_to(root_r)).replace("\\", "/") for p in all_files]

    return _response("ok", {"glob": glob, "count": len(paths), "paths": paths}, next_tools=["code_read", "code_keyword"], usage="code_read(path='...', start_line=1, end_line=50)")


def code_read_response(root: Path, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> dict[str, Any]:
    """Read a file with optional line range, returning line-numbered content."""
    resolved = _resolve_repo_path(root, path)
    if resolved is None:
        return _response("error", {"path": path}, diagnostics=[_diagnostic("path_outside_root", f"Path '{path}' is outside the repository root or uses an absolute path. Use a repo-relative path.", recovery_tools=["code_list_files"], recovery_usage="code_list_files()")], next_tools=["code_list_files"], usage="code_list_files()")
    if not resolved.exists():
        return _response("error", {"path": path}, diagnostics=[_diagnostic("file_not_found", f"File '{path}' does not exist.", recovery_tools=["code_list_files"], recovery_usage="code_list_files()")], next_tools=["code_list_files"], usage="code_list_files()")
    if not resolved.is_file():
        return _response("error", {"path": path}, diagnostics=[_diagnostic("not_a_file", f"'{path}' is a directory, not a file.", recovery_tools=["code_list_files"], recovery_usage=f"code_list_files(glob='{path}/**')")], next_tools=["code_list_files"], usage="code_list_files()")
    try:
        raw = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return _response("error", {"path": path}, diagnostics=[_diagnostic("read_error", f"Could not read '{path}': {exc}")], next_tools=["code_list_files"], usage="code_list_files()")

    lines = raw.splitlines()
    total = len(lines)
    lo = max(1, start_line) if start_line is not None else 1
    hi = min(total, end_line) if end_line is not None else total
    if lo > hi:
        return _response("error", {"path": path, "start_line": start_line, "end_line": end_line}, diagnostics=[_diagnostic("invalid_range", f"start_line ({lo}) is greater than end_line ({hi}) for file with {total} lines.")], next_tools=["code_read"], usage=f"code_read(path={path!r})")
    selected = lines[lo - 1:hi]
    numbered = "\n".join(f"{i + lo:5d}\t{line}" for i, line in enumerate(selected))
    return _response("ok", {"path": path, "start_line": lo, "end_line": hi, "total_lines": total, "content": numbered}, next_tools=["code_keyword", "code_definition"], usage=f"code_keyword(query='...', glob='*.py')")


def code_keyword_response(
    root: Path,
    query: str = "",
    glob: str = "",
    queries: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Search repository files for an exact keyword/substring, returning path/line/snippet results.

    Pass either *query* (single string) or *queries* (list of strings); supplying both is an error.
    When *queries* is used each result includes ``matched_query`` showing which entry produced it.
    """
    has_query = bool(query.strip())
    has_queries = queries is not None

    if has_query and has_queries:
        return _response(
            "error", {"query": query, "queries": queries},
            diagnostics=[_diagnostic("invalid_arguments", "Provide either 'query' or 'queries', not both.")],
            next_tools=["code_keyword"], usage="code_keyword(query='FOO')",
        )

    if not has_query and not has_queries:
        return _response(
            "error", {"query": query},
            diagnostics=[_diagnostic("invalid_arguments", "Search query must be a non-empty string.")],
            next_tools=["code_list_files"], usage="code_list_files()",
        )

    # --- multi-query path ---
    if has_queries:
        assert queries is not None  # for type checker
        if not queries:
            return _response("ok", {"queries": queries, "glob": glob, "count": 0, "results": []},
                             next_tools=["code_read"], usage="code_read(path='...', start_line=N, end_line=N+20)")
        try:
            all_files = _walk_repo_for_navigation(root)
        except Exception as exc:
            return _response("error", {"queries": queries},
                             diagnostics=[_diagnostic("navigation_error", f"File walk failed: {exc}")],
                             next_tools=["wave_help"], usage="wave_help()")
        root_r = root.resolve()
        if glob:
            import fnmatch
            all_files = [
                p for p in all_files
                if fnmatch.fnmatch(str(p.resolve().relative_to(root_r)).replace("\\", "/"), glob)
                or fnmatch.fnmatch(p.name, glob)
            ]
        seen: set[tuple[str, int]] = set()
        merged: list[dict[str, Any]] = []
        for q in queries:
            for p in all_files:
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
                for lineno, line in enumerate(text.splitlines(), 1):
                    if q in line:
                        key = (rel, lineno)
                        if key not in seen:
                            seen.add(key)
                            merged.append({"path": rel, "line": lineno, "snippet": line.rstrip(), "matched_query": q})
        return _response("ok", {"queries": queries, "glob": glob, "count": len(merged), "results": merged},
                         next_tools=["code_read"], usage="code_read(path='...', start_line=N, end_line=N+20)")

    # --- single-query path (original behaviour) ---
    try:
        all_files = _walk_repo_for_navigation(root)
    except Exception as exc:
        return _response("error", {"query": query}, diagnostics=[_diagnostic("navigation_error", f"File walk failed: {exc}")], next_tools=["wave_help"], usage="wave_help()")

    root_r = root.resolve()
    if glob:
        import fnmatch
        all_files = [
            p for p in all_files
            if fnmatch.fnmatch(str(p.resolve().relative_to(root_r)).replace("\\", "/"), glob)
            or fnmatch.fnmatch(p.name, glob)
        ]

    results: list[dict[str, Any]] = []
    for p in all_files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for lineno, line in enumerate(text.splitlines(), 1):
            if query in line:
                results.append({"path": rel, "line": lineno, "snippet": line.rstrip()})

    return _response("ok", {"query": query, "glob": glob, "count": len(results), "results": results},
                     next_tools=["code_read"], usage="code_read(path='...', start_line=N, end_line=N+20)")


def _bracket_depth(text: str) -> int:
    """Net open-bracket depth of ``text``, treating quoted strings as opaque.

    Used by ``code_constants_response`` to detect multiline values.
    Triple-quoted and single-quoted strings are skipped entirely so bracket
    characters inside strings do not affect the depth count.
    """
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        # Triple-quoted string — skip to closing triple-quote
        if text[i:i + 3] in ('"""', "'''"):
            q = text[i:i + 3]
            i += 3
            while i < n and text[i:i + 3] != q:
                i += 1
            i += 3
        # Single-quoted string — skip to closing quote
        elif text[i] in ('"', "'"):
            q = text[i]
            i += 1
            while i < n and text[i] != q:
                if text[i] == '\\':
                    i += 1  # skip escaped character
                i += 1
            i += 1  # skip closing quote
        elif text[i] in '([{':
            depth += 1
            i += 1
        elif text[i] in ')]}':
            depth -= 1
            i += 1
        else:
            i += 1
    return depth


_CONSTANTS_MAX_CONTINUATION = 50


def code_constants_response(root: Path, symbols: list[str], glob: str = "") -> dict[str, Any]:
    """Look up module-level constant assignments by name, returning parsed values.

    For each symbol, scans files for an assignment of the form::

        NAME = <value>
        NAME: TYPE = <value>

    at column 0 (no leading indent). Collects multiline values (frozenset, list,
    dict literals) by tracking bracket depth until depth returns to zero or
    ``_CONSTANTS_MAX_CONTINUATION`` continuation lines are consumed.

    Returns results in input ``symbols`` order. Symbols not found are included
    with ``value: null``. When a symbol appears in multiple files all matches are
    returned (one entry per match).
    """
    if not symbols:
        return _response(
            "error", {"symbols": symbols},
            diagnostics=[_diagnostic("invalid_arguments", "symbols list must be non-empty.")],
            next_tools=["code_keyword"], usage="code_keyword(query='CONSTANT_NAME')",
        )
    try:
        all_files = _walk_repo_for_navigation(root)
    except Exception as exc:
        return _response(
            "error", {"symbols": symbols},
            diagnostics=[_diagnostic("navigation_error", f"File walk failed: {exc}")],
            next_tools=["wave_help"], usage="wave_help()",
        )

    root_r = root.resolve()
    if glob:
        import fnmatch
        all_files = [
            p for p in all_files
            if fnmatch.fnmatch(str(p.resolve().relative_to(root_r)).replace("\\", "/"), glob)
            or fnmatch.fnmatch(p.name, glob)
        ]

    symbol_set = set(symbols)
    # matches[sym] accumulates all file matches for that symbol
    matches: dict[str, list[dict[str, Any]]] = {s: [] for s in symbol_set}

    import re as _re
    for p in all_files:
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")

        i = 0
        while i < len(lines):
            line = lines[i]
            # Only consider unindented lines (module-level assignments)
            if line and not line[0].isspace():
                for sym in symbol_set:
                    if not line.startswith(sym):
                        continue
                    # NAME must be followed by whitespace, ':', or '='
                    after = line[len(sym):]
                    if not after or after[0] not in (' ', ':', '=', '\t'):
                        continue
                    m = _re.match(
                        r'^' + _re.escape(sym) + r'\s*(?::[^=]*)?\s*=\s*(.*)',
                        line,
                    )
                    if not m:
                        continue
                    val_start = m.group(1).rstrip()
                    lineno = i + 1
                    depth = _bracket_depth(val_start)
                    if depth == 0:
                        matches[sym].append({
                            "name": sym, "value": val_start,
                            "file": rel, "line": lineno, "kind": "scalar",
                        })
                    else:
                        val_lines = [val_start]
                        j = i + 1
                        count = 0
                        while j < len(lines) and depth != 0 and count < _CONSTANTS_MAX_CONTINUATION:
                            cont = lines[j].rstrip()
                            depth += _bracket_depth(cont)
                            val_lines.append(cont)
                            j += 1
                            count += 1
                        kind = "multiline" if depth == 0 else "multiline-truncated"
                        matches[sym].append({
                            "name": sym, "value": "\n".join(val_lines),
                            "file": rel, "line": lineno, "kind": kind,
                        })
            i += 1

    # Assemble results in input order; emit all matches per symbol, or null if none
    results: list[dict[str, Any]] = []
    for sym in symbols:
        sym_matches = matches.get(sym, [])
        if sym_matches:
            results.extend(sym_matches)
        else:
            results.append({"name": sym, "value": None, "file": None, "line": None, "kind": None})

    matched_count = sum(1 for r in results if r["value"] is not None)
    return _response(
        "ok",
        {"symbols": symbols, "matched": matched_count, "results": results},
        next_tools=["code_read"],
        usage="code_read(path='...', start_line=N, end_line=N+5)",
    )


# ---------------------------------------------------------------------------
# code_pattern helpers
# ---------------------------------------------------------------------------

_PATTERN_MAX_FILE_BYTES = 1 * 1024 * 1024  # 1 MB — ReDoS guard: skip files larger than this


def code_pattern_response(
    root: Path,
    pattern: str,
    glob: str = "",
    max_results: int = 50,
    ignore_case: bool = False,
) -> dict[str, Any]:
    """Regex pattern search across repository files.

    Skips files larger than ``_PATTERN_MAX_FILE_BYTES`` (1 MB) as a ReDoS
    mitigation — per-line ``re.search()`` is unbounded within a single line,
    so large generated files are excluded to prevent latency spikes from
    pathological patterns. Callers using pathological patterns against
    small files bear that risk themselves.
    """
    flags = re.IGNORECASE if ignore_case else 0
    try:
        compiled = re.compile(pattern, flags)
    except re.error as exc:
        return _response(
            "error", {"pattern": pattern},
            diagnostics=[_diagnostic("invalid_pattern", f"Invalid regex: {exc}")],
            next_tools=["code_keyword"], usage="code_keyword(query='literal text')",
        )

    try:
        all_files = _walk_repo_for_navigation(root)
    except Exception as exc:
        return _response(
            "error", {"pattern": pattern},
            diagnostics=[_diagnostic("navigation_error", f"File walk failed: {exc}")],
            next_tools=["wave_help"], usage="wave_help()",
        )

    root_r = root.resolve()
    if glob:
        import fnmatch
        all_files = [
            p for p in all_files
            if fnmatch.fnmatch(str(p.resolve().relative_to(root_r)).replace("\\", "/"), glob)
            or fnmatch.fnmatch(p.name, glob)
        ]

    matches: list[dict[str, Any]] = []
    total = 0
    truncated = False

    for p in all_files:
        try:
            if p.stat().st_size > _PATTERN_MAX_FILE_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for lineno, line in enumerate(text.splitlines(), 1):
            if compiled.search(line):
                total += 1
                if len(matches) < max_results:
                    matches.append({"file": rel, "line": lineno, "text": line.rstrip()})
                else:
                    truncated = True

    return _response(
        "ok",
        {"pattern": pattern, "glob": glob, "matches": matches,
         "truncated": truncated, "total_matches_found": total},
        next_tools=["code_read"], usage="code_read(path='...', start_line=N, end_line=N+5)",
    )


# ---------------------------------------------------------------------------
# code_outline helpers
# ---------------------------------------------------------------------------

_OUTLINE_REGEX = re.compile(
    r'^(?:pub\s+)?(?:async\s+)?'
    r'(def|class|function|func|fn|sub|procedure)\s+'
    r'([A-Za-z_][A-Za-z0-9_]*)',
    re.IGNORECASE,
)


def _outline_ts_name(node: Any) -> str:
    """Extract the identifier name from a tree-sitter definition node."""
    for child in node.children:
        if child.type in _TS_IDENTIFIER_TYPES:
            return child.text.decode("utf-8", errors="replace").strip()
    return ""


def _outline_python(source: str, rel: str) -> dict[str, Any]:
    """Python AST-based outline extraction."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return _response("error", {"path": rel},
                         diagnostics=[_diagnostic("unparseable", f"Python SyntaxError: {exc}")],
                         next_tools=[], usage="")

    def _end(node: ast.AST) -> int:
        return getattr(node, "end_lineno", getattr(node, "lineno", 0))

    def _docstring(node: ast.AST) -> Optional[str]:
        body = getattr(node, "body", [])
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            return body[0].value.value.strip().splitlines()[0][:200]
        return None

    symbols: list[dict[str, Any]] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append({"name": node.name, "kind": "function",
                            "start_line": node.lineno, "end_line": _end(node),
                            "docstring": _docstring(node)})
        elif isinstance(node, ast.ClassDef):
            symbols.append({"name": node.name, "kind": "class",
                            "start_line": node.lineno, "end_line": _end(node),
                            "docstring": _docstring(node)})
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append({"name": child.name, "kind": "method",
                                    "start_line": child.lineno, "end_line": _end(child),
                                    "docstring": _docstring(child)})
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == t.id.upper() and t.id.replace("_", "").isalpha():
                    symbols.append({"name": t.id, "kind": "constant",
                                    "start_line": node.lineno, "end_line": _end(node),
                                    "docstring": None})
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                n = node.target.id
                if n == n.upper() and n.replace("_", "").isalpha():
                    symbols.append({"name": n, "kind": "constant",
                                    "start_line": node.lineno, "end_line": _end(node),
                                    "docstring": None})

    return _response("ok", {"file": rel, "parser_used": "python_ast", "symbols": symbols},
                     next_tools=["code_read"], usage=f"code_read(path='{rel}', start_line=N, end_line=N+20)")


def _outline_treesitter(source: str, rel: str, lang: str) -> Optional[dict[str, Any]]:
    """Tree-sitter outline. Returns None on any failure so caller can fall through to regex."""
    try:
        chunker = _get_chunker_module()
        tree = chunker._ts_parse(_TS_SYMBOL_LANG_MAP[lang], source)
        if tree is None:
            return None
    except Exception:
        return None

    def _entry(node: Any, kind: str) -> Optional[dict[str, Any]]:
        name = _outline_ts_name(node)
        if not name:
            return None
        return {"name": name, "kind": kind,
                "start_line": node.start_point[0] + 1,
                "end_line": node.end_point[0] + 1,
                "docstring": None}

    symbols: list[dict[str, Any]] = []
    for node in tree.root_node.children:
        # Unwrap export_statement (TypeScript/JavaScript top-level exports)
        inner = node
        if node.type == "export_statement":
            for child in node.children:
                if child.type not in ("export", "default", "type"):
                    inner = child
                    break
        # Also unwrap SQL statement wrapper (e.g. statement → create_function)
        elif node.type == "statement":
            for child in node.children:
                if child.type not in (";",):
                    inner = child
                    break
        if inner.type in _TS_OUTLINE_CLASS_TYPES:
            e = _entry(inner, "class")
            if e:
                symbols.append(e)
            # Walk one level into the class body for methods
            for child in inner.children:
                if child.type in _TS_OUTLINE_FUNC_TYPES:
                    m = _entry(child, "method")
                    if m:
                        symbols.append(m)
                elif hasattr(child, "children"):
                    for gc in child.children:
                        if gc.type in _TS_OUTLINE_FUNC_TYPES:
                            m = _entry(gc, "method")
                            if m:
                                symbols.append(m)
        elif inner.type in _TS_OUTLINE_FUNC_TYPES:
            e = _entry(inner, "function")
            if e:
                symbols.append(e)
        elif inner.type == "lexical_declaration":
            # Arrow function exports: export const fn = async (props) => {}
            for declarator in inner.children:
                if declarator.type == "variable_declarator":
                    value = next(
                        (c for c in declarator.children if c.type == "arrow_function"), None
                    )
                    if value:
                        name_node = next(
                            (c for c in declarator.children if c.type == "identifier"), None
                        )
                        if name_node:
                            symbols.append({
                                "name": name_node.text.decode("utf-8", errors="replace").strip(),
                                "kind": "function",
                                "start_line": inner.start_point[0] + 1,
                                "end_line": inner.end_point[0] + 1,
                                "docstring": None,
                            })

    return _response("ok", {"file": rel, "parser_used": "tree_sitter", "symbols": symbols},
                     next_tools=["code_read"], usage=f"code_read(path='{rel}', start_line=N, end_line=N+20)")


def _outline_regex_tier(source: str, rel: str) -> dict[str, Any]:
    """Regex-based outline for unsupported file types. end_line and docstring are always null."""
    symbols: list[dict[str, Any]] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        m = _OUTLINE_REGEX.match(line)
        if m:
            kw = m.group(1).lower()
            kind = "class" if kw == "class" else "function"
            symbols.append({"name": m.group(2), "kind": kind,
                            "start_line": lineno, "end_line": None,
                            "docstring": None})
    return _response("ok", {"file": rel, "parser_used": "regex", "symbols": symbols},
                     next_tools=["code_read"], usage=f"code_read(path='{rel}', start_line=N, end_line=N+20)")


def code_outline_response(root: Path, path: str) -> dict[str, Any]:
    """Return a structural symbol map of a source file using a tiered parser.

    Tier 1 — Python AST (for ``.py``).
    Tier 2 — tree-sitter for the 11 languages in ``_TS_SYMBOL_LANG_MAP``.
    Tier 3 — regex fallback for all other file types.
    """
    resolved = _resolve_repo_path(root, path)
    if resolved is None:
        return _response("error", {"path": path},
                         diagnostics=[_diagnostic("path_rejected", f"Path '{path}' is outside the project root or invalid.")],
                         next_tools=["code_list_files"], usage="code_list_files()")
    if not resolved.exists():
        return _response("error", {"path": path},
                         diagnostics=[_diagnostic("file_not_found", f"File '{path}' does not exist.")],
                         next_tools=["code_list_files"], usage="code_list_files()")
    if not resolved.is_file():
        return _response("error", {"path": path},
                         diagnostics=[_diagnostic("not_a_file", f"'{path}' is a directory.")],
                         next_tools=["code_list_files"], usage=f"code_list_files(glob='{path}/**')")

    root_r = root.resolve()
    rel = str(resolved.relative_to(root_r)).replace("\\", "/")
    lang = _EXT_TO_LANG.get(resolved.suffix.lower(), "")

    try:
        source = resolved.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError) as exc:
        return _response("error", {"path": path},
                         diagnostics=[_diagnostic("unparseable", f"Cannot read '{path}': {exc}")],
                         next_tools=[], usage="")

    if lang == "python":
        return _outline_python(source, rel)
    if lang in _TS_SYMBOL_LANG_MAP:
        result = _outline_treesitter(source, rel, lang)
        if result is not None:
            return result
    return _outline_regex_tier(source, rel)


# ---------------------------------------------------------------------------
# code_hover — symbol enclosing a given line number
# ---------------------------------------------------------------------------


def _innermost_symbol(symbols: list[dict[str, Any]], line: int) -> Optional[dict[str, Any]]:
    """Return the innermost (smallest range) symbol that encloses *line*, or None."""
    best: Optional[dict[str, Any]] = None
    best_range: Optional[int] = None
    for sym in symbols:
        sl = sym.get("start_line")
        el = sym.get("end_line")
        if sl is None or el is None:
            continue
        if sl <= line <= el:
            rng = el - sl
            if best_range is None or rng < best_range:
                best = sym
                best_range = rng
    return best


def _hover_python(source: str, line: int) -> Optional[dict[str, Any]]:
    """Find the symbol enclosing *line* in a Python source file."""
    try:
        outline_resp = _outline_python(source, "<hover>")
        if outline_resp.get("status") != "ok":
            return None
        symbols = outline_resp["data"]["symbols"]
        sym = _innermost_symbol(symbols, line)
        if sym is None:
            return None
        # Re-parse to extract signature
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return {**sym, "signature": None}
        target_name = sym["name"]
        target_line = sym["start_line"]
        matched_node = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == target_name and node.lineno == target_line:
                    matched_node = node
                    break
        if matched_node is None:
            return {**sym, "signature": None}
        if isinstance(matched_node, ast.ClassDef):
            return {**sym, "signature": None}
        # Build signature for function/async function
        fn = matched_node
        args = fn.args
        params: list[str] = []
        # Build positional args with annotations and defaults
        all_args = []
        if args.posonlyargs:
            all_args.extend(args.posonlyargs)
        all_args.extend(args.args)
        # Defaults are right-aligned in all_args
        n_defaults = len(args.defaults)
        n_all = len(all_args)
        for i, arg in enumerate(all_args):
            s = arg.arg
            if arg.annotation is not None:
                try:
                    s += ": " + ast.unparse(arg.annotation)
                except AttributeError:
                    pass
            default_idx = i - (n_all - n_defaults)
            if default_idx >= 0:
                try:
                    s += " = " + ast.unparse(args.defaults[default_idx])
                except AttributeError:
                    pass
            params.append(s)
        if args.vararg:
            s = "*" + args.vararg.arg
            if args.vararg.annotation is not None:
                try:
                    s += ": " + ast.unparse(args.vararg.annotation)
                except AttributeError:
                    pass
            params.append(s)
        if args.kwonlyargs:
            if not args.vararg:
                params.append("*")
            for i, arg in enumerate(args.kwonlyargs):
                s = arg.arg
                if arg.annotation is not None:
                    try:
                        s += ": " + ast.unparse(arg.annotation)
                    except AttributeError:
                        pass
                if args.kw_defaults[i] is not None:
                    try:
                        s += " = " + ast.unparse(args.kw_defaults[i])
                    except AttributeError:
                        pass
                params.append(s)
        if args.kwarg:
            s = "**" + args.kwarg.arg
            if args.kwarg.annotation is not None:
                try:
                    s += ": " + ast.unparse(args.kwarg.annotation)
                except AttributeError:
                    pass
            params.append(s)
        sig = "(" + ", ".join(params) + ")"
        if fn.returns is not None:
            try:
                sig += " -> " + ast.unparse(fn.returns)
            except AttributeError:
                pass
        return {**sym, "signature": sig}
    except Exception:
        return None


def _hover_treesitter(source: str, line: int, lang: str) -> Optional[dict[str, Any]]:
    """Find the symbol enclosing *line* in a tree-sitter-supported source file."""
    try:
        outline_resp = _outline_treesitter(source, "<hover>", lang)
        if outline_resp is None or outline_resp.get("status") != "ok":
            return None
        symbols = outline_resp["data"]["symbols"]
        sym = _innermost_symbol(symbols, line)
        if sym is None:
            return None
        # Re-parse to extract raw parameter text
        try:
            chunker = _get_chunker_module()
            tree = chunker._ts_parse(_TS_SYMBOL_LANG_MAP[lang], source)
            if tree is None:
                return {**sym, "signature": None}
        except Exception:
            return {**sym, "signature": None}
        target_start = sym["start_line"]
        signature: Optional[str] = None

        def _walk_for_func(node: Any) -> Optional[Any]:
            if node.start_point[0] + 1 == target_start and node.type in _TS_OUTLINE_FUNC_TYPES:
                return node
            for child in node.children:
                found = _walk_for_func(child)
                if found is not None:
                    return found
            return None

        func_node = _walk_for_func(tree.root_node)
        if func_node is not None:
            for child in func_node.children:
                if child.type == "parameters" or child.type == "formal_parameters":
                    signature = child.text.decode("utf-8", errors="replace").strip()
                    break
        return {**sym, "signature": signature}
    except Exception:
        return None


def _hover_regex(source: str, line: int) -> Optional[dict[str, Any]]:
    """Find the nearest preceding symbol to *line* using regex outline."""
    try:
        outline_resp = _outline_regex_tier(source, "<hover>")
        symbols = outline_resp["data"]["symbols"]
        best = None
        for sym in symbols:
            sl = sym.get("start_line")
            if sl is not None and sl <= line:
                best = sym
        if best is None:
            return None
        return {**best, "signature": None}
    except Exception:
        return None


def code_hover_response(root: Path, path: str, line: int) -> dict[str, Any]:
    """Return the symbol enclosing a given 1-based line number."""
    resolved = _resolve_repo_path(root, path)
    if resolved is None:
        return _response("error", {"path": path, "line": line},
                         diagnostics=[_diagnostic("path_rejected", f"Path '{path}' is outside the project root or invalid.")],
                         next_tools=["code_list_files"], usage="code_list_files()")
    if not resolved.exists():
        return _response("error", {"path": path, "line": line},
                         diagnostics=[_diagnostic("file_not_found", f"File '{path}' does not exist.")],
                         next_tools=["code_list_files"], usage="code_list_files()")

    root_r = root.resolve()
    rel = str(resolved.relative_to(root_r)).replace("\\", "/")

    try:
        source = resolved.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError) as exc:
        return _response("ok", {"file": rel, "line": line, "symbol": None, "parser_used": "none"},
                         diagnostics=[_diagnostic("unparseable", f"Cannot read '{path}': {exc}")])

    lang = _EXT_TO_LANG.get(resolved.suffix.lower(), "")
    symbol: Optional[dict[str, Any]] = None
    parser_used = "regex"

    try:
        if lang == "python":
            parser_used = "python_ast"
            symbol = _hover_python(source, line)
        elif lang in _TS_SYMBOL_LANG_MAP:
            parser_used = "tree_sitter"
            symbol = _hover_treesitter(source, line, lang)
            if symbol is None:
                parser_used = "regex"
                symbol = _hover_regex(source, line)
        else:
            symbol = _hover_regex(source, line)
    except Exception:
        symbol = None

    return _response("ok", {"file": rel, "line": line, "symbol": symbol, "parser_used": parser_used})


# ---------------------------------------------------------------------------
# Symbol navigation helpers
# ---------------------------------------------------------------------------


_EXT_TO_LANG: dict[str, str] = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".mjs": "javascript", ".cjs": "javascript",
    ".go": "go", ".rs": "rust", ".java": "java", ".rb": "ruby",
    ".cs": "csharp", ".cpp": "cpp", ".hpp": "cpp", ".c": "c", ".h": "c",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".fish": "fish",
    ".kt": "kotlin", ".kts": "kotlin", ".groovy": "groovy", ".scala": "scala",
    ".css": "css", ".scss": "scss",
    ".sql": "sql", ".psql": "sql", ".pgsql": "sql", ".ddl": "sql", ".dml": "sql", ".tsql": "sql", ".hql": "sql", ".xml": "xml",
    ".html": "html", ".htm": "html",
    ".swift": "swift",
    ".json": "json", ".jsonc": "json",
    ".toml": "toml", ".yaml": "yaml", ".yml": "yaml",
}

# Reverse map: language name → sorted list of extensions (without leading dot).
_LANG_TO_EXTS: dict[str, list[str]] = {}
for _ext, _lang in _EXT_TO_LANG.items():
    _LANG_TO_EXTS.setdefault(_lang, []).append(_ext.lstrip("."))
_LANG_TO_EXTS = {k: sorted(v) for k, v in _LANG_TO_EXTS.items()}

# Category map: category name → frozenset of canonical language names.
# Categories are intent-based groupings; a language may appear in multiple categories.
# "java" covers the JVM family; "sparksql" is an alias for sql (SparkSQL is SQL syntax).
_LANG_CATEGORIES: dict[str, frozenset] = {
    "java":     frozenset({"java", "kotlin", "scala", "groovy"}),
    "web":      frozenset({"typescript", "javascript", "html", "css", "scss"}),
    "systems":  frozenset({"c", "cpp", "rust", "go"}),
    "data":     frozenset({"sql"}),
    "sparksql": frozenset({"sql"}),
    "dotnet":   frozenset({"csharp"}),
    "script":   frozenset({"python", "ruby", "shell", "fish"}),
}

_TREE_SITTER_DEFINITION_LANGS = {"javascript", "typescript", "java", "csharp", "sql"}
_TREE_SITTER_REFERENCE_LANGS = {"javascript", "typescript", "java", "csharp", "sql"}
_CHUNKER_MOD = None

_SUPPORTED_DEFINITION_LANGS = {
    "python", "javascript", "typescript", "go", "rust", "java", "csharp", "kotlin", "swift", "sql",
    "css", "scss",
}
_SUPPORTED_REFERENCE_LANGS = set(_LANG_TO_EXTS)

_DOC_REFERENCE_EXTS = {".md", ".markdown", ".mdx", ".rst", ".txt", ".adoc", ".asciidoc"}
_TEST_REFERENCE_PATH_RE = re.compile(r"(^|/)(tests?|__tests__)(/|$)|(^|/)(test|spec)[^/]*\.(py|js|jsx|ts|tsx|java|cs|go|rs|kt|swift)$|(\.test|\.spec)\.[^.]+$", re.IGNORECASE)

_TS_CALL_PARENT_TYPES: dict[str, set[str]] = {
    "javascript": {"call_expression", "new_expression"},
    "typescript": {"call_expression", "new_expression"},
    "java": {"method_invocation", "object_creation_expression"},
    "csharp": {"invocation_expression", "object_creation_expression"},
    "sql": {"function_call", "call", "call_expression", "routine_invocation"},
}

_TS_IMPORT_PARENT_TYPES: dict[str, set[str]] = {
    "javascript": {"import_statement", "import_clause", "import_specifier", "named_imports", "namespace_import"},
    "typescript": {"import_statement", "import_clause", "import_specifier", "named_imports", "namespace_import"},
    "java": {"import_declaration"},
    "csharp": {"using_directive"},
    "sql": {"with_clause"},
}

_IDENTIFIER_SYMBOL_RE = re.compile(r"^[A-Za-z_]\w*$")


def _sql_symbol_variants(symbol: str) -> set[str]:
    symbol_s = symbol.strip()
    variants = {symbol_s}
    if "." in symbol_s:
        variants.add(symbol_s.rsplit(".", 1)[-1])
    return variants


def _sql_symbol_matches(candidate: str, symbol: str) -> bool:
    candidate_s = candidate.strip()
    symbol_s = symbol.strip()
    if candidate_s == symbol_s:
        return True
    candidate_base = candidate_s.rsplit(".", 1)[-1]
    symbol_base = symbol_s.rsplit(".", 1)[-1]
    if candidate_base != symbol_base:
        return False
    candidate_qualified = "." in candidate_s
    symbol_qualified = "." in symbol_s
    return candidate_qualified != symbol_qualified


def _sql_schema_retry_symbol(symbol: str) -> Optional[str]:
    symbol_s = symbol.strip()
    if "." not in symbol_s:
        return None
    retry = symbol_s.rsplit(".", 1)[-1].strip()
    return retry if retry and retry != symbol_s else None


def _sql_schema_doc_mention_refs(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Return doc/mention hits for a schema-qualified SQL symbol using the bare name."""
    retry_symbol = _sql_schema_retry_symbol(symbol)
    if retry_symbol is None:
        return []
    refs: list[dict[str, Any]] = []
    for ref in _non_python_references(root, retry_symbol):
        if ref.get("reference_kind") in {"docs", "mention"}:
            ref["sql_query_symbol"] = retry_symbol
            refs.append(ref)
    return refs

# Regex-based structural definition patterns for languages where we have a
# reliable top-level symbol shape but no AST/LSP navigation in the MCP layer.
_DEFINITION_PATTERNS: dict[str, list[tuple[str, re.Pattern]]] = {
    "javascript": [
        ("function", re.compile(r"^(?:export\s+)?(?:default\s+)?function\s+(\w+)")),
        ("class", re.compile(r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)")),
        ("variable", re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=")),
    ],
    "typescript": [
        ("function", re.compile(r"^(?:export\s+)?(?:default\s+)?function\s+(\w+)")),
        ("class", re.compile(r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)")),
        ("interface", re.compile(r"^(?:export\s+)?interface\s+(\w+)")),
        ("type", re.compile(r"^(?:export\s+)?type\s+(\w+)")),
        ("enum", re.compile(r"^(?:export\s+)?enum\s+(\w+)")),
        ("variable", re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=")),
    ],
    "go": [
        ("function", re.compile(r"^func\s+(?:\([^)]*\)\s*)?(\w+)\s*\(")),
        ("type", re.compile(r"^type\s+(\w+)")),
        ("variable", re.compile(r"^var\s+(\w+)")),
        ("const", re.compile(r"^const\s+(\w+)")),
    ],
    "rust": [
        ("function", re.compile(r"^(?:pub\s+)?fn\s+(\w+)")),
        ("struct", re.compile(r"^(?:pub\s+)?struct\s+(\w+)")),
        ("enum", re.compile(r"^(?:pub\s+)?enum\s+(\w+)")),
        ("trait", re.compile(r"^(?:pub\s+)?trait\s+(\w+)")),
        ("type", re.compile(r"^(?:pub\s+)?type\s+(\w+)")),
        ("const", re.compile(r"^(?:pub\s+)?const\s+(\w+)")),
    ],
    "java": [
        ("class", re.compile(r"^(?:public|protected|private)?\s*(?:abstract\s+|final\s+)?class\s+(\w+)")),
        ("interface", re.compile(r"^(?:public|protected|private)?\s*interface\s+(\w+)")),
        ("enum", re.compile(r"^(?:public|protected|private)?\s*enum\s+(\w+)")),
        ("method", re.compile(r"^(?:public|protected|private)\s+(?:static\s+)?[\w<>\[\], ?]+\s+(\w+)\s*\(")),
    ],
    "csharp": [
        ("class", re.compile(r"^(?:public|internal|protected|private)?\s*(?:abstract\s+|sealed\s+)?(?:partial\s+)?class\s+(\w+)")),
        ("interface", re.compile(r"^(?:public|internal|protected|private)?\s*interface\s+(\w+)")),
        ("enum", re.compile(r"^(?:public|internal|protected|private)?\s*enum\s+(\w+)")),
        ("struct", re.compile(r"^(?:public|internal|protected|private)?\s*struct\s+(\w+)")),
        ("record", re.compile(r"^(?:public|internal|protected|private)?\s*record\s+(\w+)")),
        ("method", re.compile(r"^(?:public|protected|private|internal)\s+(?:static\s+)?[\w<>\[\], ?.]+\s+(\w+)\s*\(")),
    ],
    "kotlin": [
        ("function", re.compile(r"^(?:public|private|internal|protected)?\s*fun\s+(\w+)")),
        ("class", re.compile(r"^(?:data\s+)?class\s+(\w+)")),
        ("object", re.compile(r"^object\s+(\w+)")),
        ("interface", re.compile(r"^interface\s+(\w+)")),
        ("enum", re.compile(r"^enum\s+class\s+(\w+)")),
    ],
    "swift": [
        ("function", re.compile(r"^(?:public|internal|private|open)?\s*func\s+(\w+)")),
        ("class", re.compile(r"^(?:public|internal|private|open)?\s*class\s+(\w+)")),
        ("struct", re.compile(r"^(?:public|internal|private|open)?\s*struct\s+(\w+)")),
        ("enum", re.compile(r"^(?:public|internal|private|open)?\s*enum\s+(\w+)")),
        ("protocol", re.compile(r"^(?:public|internal|private|open)?\s*protocol\s+(\w+)")),
    ],
}


# CSS/SCSS definition patterns.  Class and ID selectors can appear anywhere in
# a selector string (e.g. `html[data-theme="dark"] .classname { ... }`), so
# these use finditer on rule-opening lines rather than match() at line start.
_CSS_CLASS_RE    = re.compile(r"(?<![.\w#])\.(-?[a-zA-Z_][a-zA-Z0-9_-]*)")
_CSS_ID_RE       = re.compile(r"(?<![.\w])#([a-zA-Z_][a-zA-Z0-9_-]*)")
_CSS_PROP_RE     = re.compile(r"^--([\w-]+)\s*:")
_CSS_KEYFRAME_RE = re.compile(r"^@keyframes\s+([\w-]+)")
_CSS_MIXIN_RE    = re.compile(r"^@(?:mixin|function)\s+([\w-]+)")  # SCSS


def _detect_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    return _EXT_TO_LANG.get(ext, "unknown")


def _get_chunker_module():
    """Load chunker.py lazily for tree-sitter-backed navigation."""
    global _CHUNKER_MOD
    if _CHUNKER_MOD is not None:
        return _CHUNKER_MOD
    chunker_path = Path(__file__).resolve().parent / "chunker.py"
    script_dir = str(chunker_path.parent)
    added = False
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
        added = True
    try:
        spec = importlib.util.spec_from_file_location("wf_server_chunker", chunker_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load chunker module from {chunker_path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["wf_server_chunker"] = mod
        spec.loader.exec_module(mod)
        _CHUNKER_MOD = mod
        return mod
    finally:
        if added:
            with contextlib.suppress(ValueError):
                sys.path.remove(script_dir)


def _symbol_search_pattern(symbol: str) -> re.Pattern:
    if _IDENTIFIER_SYMBOL_RE.match(symbol):
        return re.compile(r"\b" + re.escape(symbol) + r"\b")
    return re.compile(re.escape(symbol))


def _definition_match_kind(name: str, symbol: str) -> str:
    return "exact" if name == symbol else "partial"


def _definition_sort_key(defn: dict[str, Any], symbol: str) -> tuple[int, int, int, int, str, int]:
    match_rank = 0 if str(defn.get("name", "")) == symbol else 1
    method_rank = {"ast": 0, "treesitter": 1, "regex": 2, "keyword_fallback": 3}.get(str(defn.get("method", "")), 4)
    language_rank = 0 if str(defn.get("language", "")) == "python" else 1
    kind_rank = {"class": 0, "interface": 1, "enum": 2, "struct": 3, "record": 4, "method": 5, "function": 6, "variable": 7, "symbol": 8}.get(str(defn.get("kind", "symbol")), 9)
    return (
        match_rank,
        method_rank,
        language_rank,
        kind_rank,
        str(defn.get("path", "")),
        int(defn.get("line", 0) or 0),
    )


def _python_definitions(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Find function/class definitions matching *symbol* in Python files via AST."""
    import ast as _ast
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    for p in _walk_repo_for_navigation(root):
        if p.suffix.lower() != ".py":
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
            tree = _ast.parse(source, filename=str(p))
        except (SyntaxError, OSError):
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for node in _ast.walk(tree):
            name = None
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                name = node.name
            if name and (name == symbol or symbol in name):
                results.append({
                    "path": rel,
                    "line": node.lineno,
                    "kind": type(node).__name__.lower().replace("asyncfunctiondef", "async_function").replace("functiondef", "function").replace("classdef", "class"),
                    "name": name,
                    "language": "python",
                    "method": "ast",
                    "match_kind": _definition_match_kind(name, symbol),
                })
    return results


def _python_reference_call_sites(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Find structural Python call sites for *symbol* via AST."""
    import ast as _ast
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    for p in _walk_repo_for_navigation(root):
        if p.suffix.lower() != ".py":
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
            tree = _ast.parse(source, filename=str(p))
        except (SyntaxError, OSError):
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        lines = source.splitlines()
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            func = node.func
            matched = False
            if isinstance(func, _ast.Name):
                matched = func.id == symbol
            elif isinstance(func, _ast.Attribute):
                matched = func.attr == symbol
            if not matched:
                continue
            line = getattr(node, "lineno", 0)
            if line <= 0 or line > len(lines):
                continue
            results.append({
                "path": rel,
                "line": line,
                "snippet": lines[line - 1].rstrip(),
                "language": "python",
                "method": "ast",
                "reference_kind": "call_sites",
            })
    return results


def _python_references(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Find references to *symbol* in Python files via AST call-site detection plus text fallback."""
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    pattern = _symbol_search_pattern(symbol)
    call_sites_by_path: dict[str, set[int]] = {}
    for ref in _python_reference_call_sites(root, symbol):
        ref["reference_kind"] = "call_sites"
        ref["method"] = "ast"
        results.append(ref)
        call_sites_by_path.setdefault(ref["path"], set()).add(ref["line"])
    for p in _walk_repo_for_navigation(root):
        if p.suffix.lower() != ".py":
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        call_site_lines = call_sites_by_path.get(rel, set())
        for lineno, line in enumerate(source.splitlines(), 1):
            if pattern.search(line):
                if lineno in call_site_lines:
                    continue
                results.append({
                    "path": rel,
                    "line": lineno,
                    "snippet": line.rstrip(),
                    "language": "python",
                    "method": "text",
                    "reference_kind": _text_reference_kind(rel, line, symbol),
                })
    return results


def _treesitter_definition_results(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Find definitions in tree-sitter-backed languages using chunker parse helpers."""
    chunker = _get_chunker_module()
    by_language = {
        "javascript": chunker.chunk_js_ts_treesitter,
        "typescript": chunker.chunk_js_ts_treesitter,
        "java": chunker.chunk_java_treesitter,
        "csharp": chunker.chunk_csharp_treesitter,
        "sql": chunker.chunk_sql,
    }
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    for p in _walk_repo_for_navigation(root):
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        lang = _detect_language(rel)
        if lang not in _TREE_SITTER_DEFINITION_LANGS:
            continue
        chunk_fn = by_language.get(lang)
        if chunk_fn is None:
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
            chunks = chunk_fn(source, rel)
        except Exception:
            continue
        if not chunks:
            continue
        for chunk in chunks:
            if getattr(chunk, "kind", None) != "code":
                continue
            chunk_id = getattr(chunk, "id", "")
            if not chunk_id.startswith(f"{rel}::"):
                continue
            local_id = chunk_id.split("::", 1)[1]
            section = getattr(chunk, "section", "")
            line = getattr(chunk, "lines", (1, 1))[0]
            match_name = local_id
            kind = "symbol"
            if local_id.endswith(".__decl__"):
                match_name = local_id[: -len(".__decl__")]
                if lang in {"java", "csharp"}:
                    kind = "class"
                elif lang == "sql":
                    kind = "object"
                else:
                    kind = "class"
            elif "." in local_id:
                match_name = local_id.split(".")[-1]
                kind = "method"
            else:
                kind = "object" if lang == "sql" else "function"
            if (lang == "sql" and _sql_symbol_matches(match_name, symbol)) or match_name == symbol or symbol in match_name:
                results.append({
                    "path": rel,
                    "line": line,
                    "kind": kind,
                    "name": match_name,
                    "language": lang,
                    "method": "treesitter",
                    "section": section,
                    "match_kind": _definition_match_kind(match_name, symbol),
                })
    return results


_TS_IDENTIFIER_NODE_TYPES: dict[str, set[str]] = {
    "javascript": {"identifier", "property_identifier"},
    "typescript": {"identifier", "property_identifier", "type_identifier"},
    "java": {"identifier"},
    "csharp": {"identifier"},
    "sql": {"identifier", "bare_identifier", "quoted_identifier", "object_reference", "column_reference"},
}

_TS_DEFINITION_PARENT_TYPES: dict[str, set[str]] = {
    "javascript": {
        "function_declaration", "generator_function_declaration", "class_declaration",
        "method_definition", "variable_declarator",
    },
    "typescript": {
        "function_declaration", "generator_function_declaration", "class_declaration",
        "method_definition", "variable_declarator", "interface_declaration",
        "type_alias_declaration", "enum_declaration",
    },
    "java": {
        "class_declaration", "interface_declaration", "enum_declaration",
        "annotation_type_declaration", "method_declaration", "constructor_declaration",
    },
    "csharp": {
        "class_declaration", "interface_declaration", "struct_declaration",
        "enum_declaration", "record_declaration", "method_declaration",
        "constructor_declaration", "operator_declaration",
    },
}


def _treesitter_references(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Find identifier references in tree-sitter-backed languages."""
    chunker = _get_chunker_module()
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    for p in _walk_repo_for_navigation(root):
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        lang = _detect_language(rel)
        if lang not in _TREE_SITTER_REFERENCE_LANGS:
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
            tree = chunker._ts_parse(lang, source)
        except Exception:
            continue
        if tree is None:
            continue
        source_lines = source.splitlines()
        id_types = _TS_IDENTIFIER_NODE_TYPES.get(lang, {"identifier"})
        def_parents = _TS_DEFINITION_PARENT_TYPES.get(lang, set())
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if getattr(node, "type", "") in id_types:
                text = source_lines[node.start_point[0]][node.start_point[1]:node.end_point[1]]
                if (lang == "sql" and _sql_symbol_matches(text, symbol)) or text == symbol:
                    line = node.start_point[0] + 1
                    snippet = source_lines[node.start_point[0]].rstrip()
                    parent = getattr(node, "parent", None)
                    method = "treesitter_reference"
                    if parent is not None and getattr(parent, "type", "") in def_parents:
                        method = "treesitter_definition_reference"
                    results.append({
                        "path": rel,
                        "line": line,
                        "snippet": snippet,
                        "language": lang,
                        "method": method,
                        "reference_kind": _tree_sitter_reference_kind(lang, node, symbol, source_lines),
                    })
            children = list(getattr(node, "children", []) or [])
            stack.extend(reversed(children))
    return results


def _regex_definitions(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Find structural definitions in supported non-Python languages via regex."""
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    for p in _walk_repo_for_navigation(root):
        lang = _detect_language(str(p))
        patterns = _DEFINITION_PATTERNS.get(lang)
        if not patterns:
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for lineno, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            for kind, pattern in patterns:
                match = pattern.match(stripped)
                if not match:
                    continue
                name = match.group(1)
                if name == symbol or symbol in name:
                    results.append({
                        "path": rel,
                        "line": lineno,
                        "kind": kind,
                        "name": name,
                        "language": lang,
                        "method": "regex",
                        "match_kind": _definition_match_kind(name, symbol),
                    })
                break
    return results


def _css_definitions(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Find CSS/SCSS class, ID, custom-property, keyframe, and mixin definitions."""
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    structural_patterns = (
        ("custom-property", _CSS_PROP_RE),
        ("keyframes",       _CSS_KEYFRAME_RE),
        ("mixin",           _CSS_MIXIN_RE),
    )
    for p in _walk_repo_for_navigation(root):
        lang = _detect_language(str(p))
        if lang not in {"css", "scss"}:
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for lineno, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("/*"):
                continue
            # Custom property / @keyframes / @mixin — anchored at line start
            matched_structural = False
            for kind, pat in structural_patterns:
                m = pat.match(stripped)
                if m:
                    matched_structural = True
                    name = m.group(1)
                    if name == symbol or symbol in name:
                        results.append({
                            "path": rel, "line": lineno, "kind": kind, "name": name,
                            "language": lang, "method": "regex",
                            "match_kind": _definition_match_kind(name, symbol),
                        })
                    break
            if matched_structural:
                continue
            # Class and ID selectors — only on lines that open a rule block
            if "{" not in stripped:
                continue
            for kind, pat in (("class", _CSS_CLASS_RE), ("id", _CSS_ID_RE)):
                for m in pat.finditer(stripped):
                    name = m.group(1)
                    if name == symbol or symbol in name:
                        results.append({
                            "path": rel, "line": lineno, "kind": kind, "name": name,
                            "language": lang, "method": "regex",
                            "match_kind": _definition_match_kind(name, symbol),
                        })
                        break
    return results


def _non_python_references(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Find references to *symbol* across non-Python files via text search."""
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    pattern = _symbol_search_pattern(symbol)
    sql_variants = _sql_symbol_variants(symbol) if "." in symbol else {symbol}
    for p in _walk_repo_for_navigation(root):
        lang = _detect_language(str(p))
        if lang == "python":
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for lineno, line in enumerate(source.splitlines(), 1):
            if lang == "sql" and sql_variants:
                matched = any(
                    re.search(rf"(?<!\w){re.escape(variant)}(?!\w)", line)
                    for variant in sql_variants
                )
            else:
                matched = bool(pattern.search(line))
            if matched:
                results.append({
                    "path": rel,
                    "line": lineno,
                    "snippet": line.rstrip(),
                    "language": lang,
                    "method": "text",
                    "reference_kind": _text_reference_kind(rel, line, symbol),
                })
    return results


_KEYWORD_FALLBACK_RESULT_CAP = 50


def _keyword_fallback_definitions(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Broad keyword fallback for unsupported or unmatched languages."""
    results = []
    root_r = root.resolve()
    pattern = _symbol_search_pattern(symbol)
    for p in _walk_repo_for_navigation(root):
        if len(results) >= _KEYWORD_FALLBACK_RESULT_CAP:
            break
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for lineno, line in enumerate(source.splitlines(), 1):
            if pattern.search(line):
                results.append({
                    "path": rel,
                    "line": lineno,
                    "snippet": line.rstrip(),
                    "language": _detect_language(rel),
                    "method": "keyword_fallback",
                    "match_kind": "exact" if pattern.search(line) and re.search(rf"\b{re.escape(symbol)}\b", line) else "partial",
                })
                if len(results) >= _KEYWORD_FALLBACK_RESULT_CAP:
                    break
    return results


def _dedupe_navigation_results(results: list[dict[str, Any]], key_fields: tuple[str, ...]) -> list[dict[str, Any]]:
    """Deduplicate navigation hits while preserving the earliest/strongest entry order."""
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for item in results:
        key = tuple(item.get(field) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _reference_counts(refs: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"call_sites": 0, "other": 0, "docs": 0, "tests": 0}
    for ref in refs:
        counts[_reference_bucket(str(ref.get("reference_bucket", ref.get("reference_kind", "other"))))] += 1
    return counts


def _is_test_reference_path(rel_path: str) -> bool:
    rel = rel_path.replace("\\", "/").lower()
    return bool(_TEST_REFERENCE_PATH_RE.search(rel))


def _is_doc_reference_path(rel_path: str) -> bool:
    rel = rel_path.replace("\\", "/").lower()
    return rel.startswith("docs/") or "/docs/" in rel or Path(rel).suffix.lower() in _DOC_REFERENCE_EXTS


def _text_reference_kind(path: str, line: str, symbol: str) -> str:
    if _is_test_reference_path(path):
        return "tests"
    if _is_doc_reference_path(path):
        return "docs"
    stripped = line.strip()
    if not stripped:
        return "mention"
    if stripped.startswith(("import ", "from ", "export ", "using ", "package ")):
        return "import"
    if re.match(rf"^(?:def|class|func|function|const|let|var|type|interface|enum|record|struct)\s+{re.escape(symbol)}\b", stripped):
        return "definition"
    if re.match(rf"^(?:public|private|protected|internal|static|final|abstract|sealed|export)\b", stripped) and symbol in stripped:
        return "definition"
    if re.search(rf"\b{re.escape(symbol)}\s*\(", line):
        return "call_sites"
    if re.search(rf"\b{re.escape(symbol)}\b", line):
        return "mention"
    return "mention"


def _tree_sitter_reference_kind(lang: str, node: Any, symbol: str, source_lines: list[str]) -> str:
    if lang == "sql":
        return _sql_tree_sitter_reference_kind(node, symbol, source_lines)
    path = getattr(node, "parent", None)
    ancestor = path
    depth = 0
    while ancestor is not None and depth < 4:
        if getattr(ancestor, "type", "") in _TS_CALL_PARENT_TYPES.get(lang, set()):
            return "call_sites"
        ancestor = getattr(ancestor, "parent", None)
        depth += 1
    ancestor = path
    depth = 0
    while ancestor is not None and depth < 4:
        if getattr(ancestor, "type", "") in _TS_IMPORT_PARENT_TYPES.get(lang, set()):
            return "import"
        ancestor = getattr(ancestor, "parent", None)
        depth += 1
    if path is not None and getattr(path, "type", "") in _TS_DEFINITION_PARENT_TYPES.get(lang, set()):
        return "definition"
    line_idx = getattr(node, "start_point", (0, 0))[0]
    if 0 <= line_idx < len(source_lines):
        return _text_reference_kind("", source_lines[line_idx], symbol)
    return "mention"


def _sql_tree_sitter_reference_kind(node: Any, symbol: str, source_lines: list[str]) -> str:
    ancestor = getattr(node, "parent", None)
    depth = 0
    while ancestor is not None and depth < 4:
        ancestor_type = getattr(ancestor, "type", "").lower()
        if any(token in ancestor_type for token in ("call", "function", "routine")):
            return "call_sites"
        if any(token in ancestor_type for token in ("create", "alter", "drop", "declare", "definition", "table", "view", "procedure", "index", "schema", "trigger", "type")):
            return "definition"
        ancestor = getattr(ancestor, "parent", None)
        depth += 1
    line_idx = getattr(node, "start_point", (0, 0))[0]
    if 0 <= line_idx < len(source_lines):
        line = source_lines[line_idx]
        stripped = line.strip()
        if re.match(rf"^(?:CREATE|ALTER|DROP)\b.*\b{re.escape(symbol)}\b", stripped, re.IGNORECASE):
            return "definition"
        if re.search(rf"\b{re.escape(symbol)}\s*\(", line):
            return "call_sites"
        if re.search(rf"\b{re.escape(symbol)}\b", line):
            return "mention"
    return "mention"


def _reference_bucket(kind: str) -> str:
    if kind == "call_sites":
        return "call_sites"
    if kind == "tests":
        return "tests"
    if kind == "docs":
        return "docs"
    return "other"

def _reference_sort_key(ref: dict[str, Any]) -> tuple[int, int, int, str, int, str]:
    kind_rank = {
        "call_sites": 0,
        "definition": 1,
        "import": 2,
        "mention": 3,
        "other": 4,
        "docs": 5,
        "tests": 6,
    }.get(str(ref.get("reference_kind", "other")), 4)
    language_rank = 0 if ref.get("language") == "python" else 1
    method_rank = 0 if str(ref.get("method", "")).startswith("treesitter") else 1
    return (
        kind_rank,
        language_rank,
        method_rank,
        str(ref.get("path", "")),
        int(ref.get("line", 0) or 0),
        str(ref.get("snippet", "")),
    )


def _reference_detail_counts(refs: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"call_sites": 0, "definition": 0, "import": 0, "mention": 0, "docs": 0, "tests": 0, "other": 0}
    for ref in refs:
        kind = str(ref.get("reference_kind", "other"))
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _apply_reference_filters(
    refs: list[dict[str, Any]],
    *,
    exclude_tests: bool = False,
    exclude_docs: bool = False,
    call_sites_only: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int], dict[str, int], dict[str, int]]:
    """Normalize reference kinds, sort by signal, and apply optional filters."""
    all_counts = {"call_sites": 0, "other": 0, "docs": 0, "tests": 0}
    filtered_counts = {"call_sites": 0, "other": 0, "docs": 0, "tests": 0}
    detail_all_counts = {"call_sites": 0, "definition": 0, "import": 0, "mention": 0, "docs": 0, "tests": 0, "other": 0}
    detail_filtered_counts = {"call_sites": 0, "definition": 0, "import": 0, "mention": 0, "docs": 0, "tests": 0, "other": 0}
    filtered: list[dict[str, Any]] = []
    for ref in refs:
        detail_kind = str(ref.get("reference_kind", "other"))
        broad_kind = _reference_bucket(detail_kind)
        ref["reference_kind"] = detail_kind
        ref["reference_bucket"] = broad_kind
        all_counts[broad_kind] += 1
        detail_all_counts[detail_kind] = detail_all_counts.get(detail_kind, 0) + 1
        if call_sites_only and broad_kind != "call_sites":
            continue
        if exclude_tests and broad_kind == "tests":
            continue
        if exclude_docs and broad_kind == "docs":
            continue
        filtered_counts[broad_kind] += 1
        detail_filtered_counts[detail_kind] = detail_filtered_counts.get(detail_kind, 0) + 1
        filtered.append(ref)
    filtered.sort(key=_reference_sort_key)
    return filtered, filtered_counts, all_counts, detail_filtered_counts, detail_all_counts


def code_definition_response(root: Path, symbol_or_path_position: str) -> dict[str, Any]:
    """Find definition(s) for a symbol across Python AST and supported non-Python regex matchers."""
    symbol = symbol_or_path_position.strip()
    retry_symbol = _sql_schema_retry_symbol(symbol)
    if not symbol:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("invalid_arguments", "Symbol must be a non-empty string.")], next_tools=["code_keyword"], usage="code_keyword(query='MyClass')")
    try:
        python_definitions = _python_definitions(root, symbol)
        treesitter_definitions = _treesitter_definition_results(root, symbol)
        regex_definitions = _regex_definitions(root, symbol)
        css_definitions = _css_definitions(root, symbol)
    except Exception as exc:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Definition search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
    definitions = _dedupe_navigation_results(
        python_definitions + treesitter_definitions + regex_definitions + css_definitions,
        ("path", "line", "language", "name"),
    )
    note = None
    if not definitions and retry_symbol is not None:
        try:
            python_definitions = _python_definitions(root, retry_symbol)
            treesitter_definitions = _treesitter_definition_results(root, retry_symbol)
            regex_definitions = _regex_definitions(root, retry_symbol)
            css_definitions = _css_definitions(root, retry_symbol)
        except Exception as exc:
            return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Definition search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
        definitions = _dedupe_navigation_results(
            python_definitions + treesitter_definitions + regex_definitions + css_definitions,
            ("path", "line", "language", "name"),
        )
        if definitions:
            note = f"Retried lookup with schema-stripped SQL symbol '{retry_symbol}'."
    definitions.sort(key=lambda d: _definition_sort_key(d, symbol))
    if definitions:
        languages = sorted({d.get("language") for d in definitions if d.get("language")})
        definition_methods = {d.get("method") for d in definitions}
        method = "multi_language"
        if definition_methods == {"ast"}:
            return _response(
                "ok",
                {"symbol": symbol, "language": "python", "definitions": definitions, "supported_languages": sorted(_SUPPORTED_DEFINITION_LANGS), "method": "ast", **({"note": note} if note else {})},
                next_tools=["code_read"],
                usage=f"code_read(path={definitions[0]['path']!r}, start_line={definitions[0]['line']}, end_line={definitions[0]['line'] + 20})",
            )
        if definition_methods == {"treesitter"}:
            method = "treesitter"
        elif definition_methods == {"regex"}:
            method = "regex"
        return _response(
            "ok",
                {
                    "symbol": symbol,
                    "definitions": definitions,
                    "supported_languages": sorted(_SUPPORTED_DEFINITION_LANGS),
                    "method": method,
                    "languages": languages,
                    **({"note": note} if note else {}),
                },
                next_tools=["code_read"],
                usage=f"code_read(path={definitions[0]['path']!r}, start_line={definitions[0]['line']}, end_line={definitions[0]['line'] + 20})",
            )
    fallback_symbol = retry_symbol or symbol
    # No structural definitions found — run keyword fallback across all files.
    try:
        fallback = _keyword_fallback_definitions(root, fallback_symbol)
    except Exception as exc:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Fallback search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
    if not fallback:
        return _response(
            "ok",
            {"symbol": symbol, "definitions": [], "method": "keyword_fallback"},
            diagnostics=[_diagnostic("not_found", f"No definition found for '{symbol}' in any language.", recovery_tools=["code_keyword"], recovery_usage=f"code_keyword(query={symbol!r})")],
            next_tools=["code_keyword"],
            usage=f"code_keyword(query={symbol!r})",
        )
    return _response(
        "ok",
        {"symbol": symbol, "definitions": fallback, "method": "keyword_fallback", "note": note or (f"Retried lookup with schema-stripped SQL symbol '{retry_symbol}'." if retry_symbol else "No structural definition matcher found a result. Returning broad keyword matches across the repo.")},
        next_tools=["code_read"],
        usage=f"code_read(path={fallback[0]['path']!r}, start_line={fallback[0]['line']}, end_line={fallback[0]['line'] + 20})",
    )


def code_references_response(
    root: Path,
    symbol_or_path_position: str,
    *,
    exclude_tests: bool = False,
    exclude_docs: bool = False,
    call_sites_only: bool = False,
    limit: Optional[int] = None,
) -> dict[str, Any]:
    """Find references to a symbol across known code languages with structural call-site detection where available."""
    symbol = symbol_or_path_position.strip()
    retry_symbol = _sql_schema_retry_symbol(symbol)
    if not symbol:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("invalid_arguments", "Symbol must be a non-empty string.")], next_tools=["code_keyword"], usage="code_keyword(query='my_func')")
    if limit is not None and limit < 0:
        return _response("error", {"symbol": symbol, "limit": limit}, diagnostics=[_diagnostic("invalid_arguments", "limit must be a non-negative integer or omitted.")], next_tools=["code_help"], usage="code_help()")
    try:
        python_refs = _python_references(root, symbol)
        treesitter_refs = _treesitter_references(root, symbol)
        other_refs = _non_python_references(root, symbol)
    except Exception as exc:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Reference search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
    refs = _dedupe_navigation_results(
        python_refs + treesitter_refs + other_refs,
        ("path", "line", "language", "snippet"),
    )
    note = None
    sql_doc_refs = _sql_schema_doc_mention_refs(root, symbol)
    if sql_doc_refs:
        refs = _dedupe_navigation_results(
            refs + sql_doc_refs,
            ("path", "line", "language", "snippet"),
        )
        note = f"Included docs and mention matches from schema-stripped SQL symbol '{_sql_schema_retry_symbol(symbol)}'."
    if refs:
        refs, filtered_counts, all_counts, detail_filtered_counts, detail_all_counts = _apply_reference_filters(
            refs,
            exclude_tests=exclude_tests,
            exclude_docs=exclude_docs,
            call_sites_only=call_sites_only,
        )
        matched_count = len(refs)
        matched_counts = dict(filtered_counts)
        if limit is not None and limit > 0:
            refs = refs[:limit]
        returned_counts = _reference_counts(refs)
        detail_returned_counts = _reference_detail_counts(refs)
        languages = sorted({r.get("language") for r in refs if r.get("language")})
        ref_methods = {r.get("method") for r in refs}
        method = "multi_language"
        broad_buckets = {
            "call_sites": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "call_sites"],
            "other": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "other"],
            "docs": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "docs"],
            "tests": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "tests"],
        }
        detail_buckets = {
            "call_sites": [r for r in refs if r["reference_kind"] == "call_sites"],
            "definition": [r for r in refs if r["reference_kind"] == "definition"],
            "import": [r for r in refs if r["reference_kind"] == "import"],
            "mention": [r for r in refs if r["reference_kind"] == "mention"],
            "docs": [r for r in refs if r["reference_kind"] == "docs"],
            "tests": [r for r in refs if r["reference_kind"] == "tests"],
            "other": [r for r in refs if r["reference_kind"] == "other"],
        }
        if languages == ["python"] and ref_methods.issubset({"ast", "text"}):
            return _response(
                "ok",
                {
                    "symbol": symbol,
                    "language": "python",
                    "count": len(refs),
                    "matched_count": matched_count,
                    "total_count": sum(all_counts.values()),
                    "counts": returned_counts,
                    "matched_counts": matched_counts,
                    "all_counts": all_counts,
                    "detail_counts": detail_returned_counts,
                    "detail_matched_counts": detail_filtered_counts,
                    "detail_all_counts": detail_all_counts,
                    "references": refs,
                    "buckets": broad_buckets,
                    "detail_buckets": detail_buckets,
                    "method": "ast",
                    "supported_languages": sorted(_SUPPORTED_REFERENCE_LANGS),
                    "exclude_tests": exclude_tests,
                    "exclude_docs": exclude_docs,
                    "call_sites_only": call_sites_only,
                    "limit": limit,
                },
                next_tools=["code_read"],
                usage=f"code_read(path='...', start_line=N, end_line=N+20)",
            )
        if all(str(m).startswith("treesitter") for m in ref_methods):
            method = "treesitter"
        elif ref_methods == {"text"}:
            method = "text"
        return _response(
            "ok",
            {
                "symbol": symbol,
                "count": len(refs),
                "matched_count": matched_count,
                "total_count": sum(all_counts.values()),
                "counts": returned_counts,
                "matched_counts": matched_counts,
                "all_counts": all_counts,
                "detail_counts": detail_returned_counts,
                "detail_matched_counts": detail_filtered_counts,
                "detail_all_counts": detail_all_counts,
                "references": refs,
                "buckets": broad_buckets,
                "detail_buckets": detail_buckets,
                "method": method,
                "supported_languages": sorted(_SUPPORTED_REFERENCE_LANGS),
                "languages": languages,
                **({"note": note} if note else {}),
                "exclude_tests": exclude_tests,
                "exclude_docs": exclude_docs,
                "call_sites_only": call_sites_only,
                "limit": limit,
            },
            next_tools=["code_read"],
            usage=f"code_read(path='...', start_line=N, end_line=N+20)",
        )
    if retry_symbol is not None:
        try:
            python_refs = _python_references(root, retry_symbol)
            treesitter_refs = _treesitter_references(root, retry_symbol)
            other_refs = _non_python_references(root, retry_symbol)
        except Exception as exc:
            return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Reference search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
        refs = _dedupe_navigation_results(
            python_refs + treesitter_refs + other_refs,
            ("path", "line", "language", "snippet"),
        )
        sql_doc_refs = _sql_schema_doc_mention_refs(root, symbol)
        if sql_doc_refs:
            refs = _dedupe_navigation_results(
                refs + sql_doc_refs,
                ("path", "line", "language", "snippet"),
            )
            note = f"Included docs and mention matches from schema-stripped SQL symbol '{retry_symbol}'."
        if refs:
            if note is None:
                note = f"Retried lookup with schema-stripped SQL symbol '{retry_symbol}'."
            refs, filtered_counts, all_counts, detail_filtered_counts, detail_all_counts = _apply_reference_filters(
                refs,
                exclude_tests=exclude_tests,
                exclude_docs=exclude_docs,
                call_sites_only=call_sites_only,
            )
            matched_count = len(refs)
            matched_counts = dict(filtered_counts)
            if limit is not None and limit > 0:
                refs = refs[:limit]
            returned_counts = _reference_counts(refs)
            detail_returned_counts = _reference_detail_counts(refs)
            languages = sorted({r.get("language") for r in refs if r.get("language")})
            ref_methods = {r.get("method") for r in refs}
            method = "multi_language"
            broad_buckets = {
                "call_sites": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "call_sites"],
                "other": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "other"],
                "docs": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "docs"],
                "tests": [r for r in refs if _reference_bucket(str(r["reference_kind"])) == "tests"],
            }
            detail_buckets = {
                "call_sites": [r for r in refs if r["reference_kind"] == "call_sites"],
                "definition": [r for r in refs if r["reference_kind"] == "definition"],
                "import": [r for r in refs if r["reference_kind"] == "import"],
                "mention": [r for r in refs if r["reference_kind"] == "mention"],
                "docs": [r for r in refs if r["reference_kind"] == "docs"],
                "tests": [r for r in refs if r["reference_kind"] == "tests"],
                "other": [r for r in refs if r["reference_kind"] == "other"],
            }
            if languages == ["python"] and ref_methods.issubset({"ast", "text"}):
                return _response(
                    "ok",
                    {
                        "symbol": symbol,
                        "language": "python",
                        "count": len(refs),
                        "matched_count": matched_count,
                        "total_count": sum(all_counts.values()),
                        "counts": returned_counts,
                        "matched_counts": matched_counts,
                        "all_counts": all_counts,
                        "detail_counts": detail_returned_counts,
                        "detail_matched_counts": detail_filtered_counts,
                        "detail_all_counts": detail_all_counts,
                        "references": refs,
                        "buckets": broad_buckets,
                        "detail_buckets": detail_buckets,
                        "method": "ast",
                        "supported_languages": sorted(_SUPPORTED_REFERENCE_LANGS),
                        "exclude_tests": exclude_tests,
                        "exclude_docs": exclude_docs,
                        "call_sites_only": call_sites_only,
                        "limit": limit,
                        **({"note": note} if note else {}),
                    },
                    next_tools=["code_read"],
                    usage=f"code_read(path='...', start_line=N, end_line=N+20)",
                )
            if all(str(m).startswith("treesitter") for m in ref_methods):
                method = "treesitter"
            elif ref_methods == {"text"}:
                method = "text"
            return _response(
                "ok",
                {
                    "symbol": symbol,
                    "count": len(refs),
                    "matched_count": matched_count,
                    "total_count": sum(all_counts.values()),
                    "counts": returned_counts,
                    "matched_counts": matched_counts,
                    "all_counts": all_counts,
                    "detail_counts": detail_returned_counts,
                    "detail_matched_counts": detail_filtered_counts,
                    "detail_all_counts": detail_all_counts,
                    "references": refs,
                    "buckets": broad_buckets,
                    "detail_buckets": detail_buckets,
                    "method": method,
                    "supported_languages": sorted(_SUPPORTED_REFERENCE_LANGS),
                    "languages": languages,
                    **({"note": note} if note else {}),
                    "exclude_tests": exclude_tests,
                    "exclude_docs": exclude_docs,
                    "call_sites_only": call_sites_only,
                    "limit": limit,
                },
                next_tools=["code_read"],
                usage=f"code_read(path='...', start_line=N, end_line=N+20)",
            )
    fallback_symbol = retry_symbol or symbol
    # No known-language references — run broad keyword fallback across all files.
    try:
        fallback = _keyword_fallback_definitions(root, fallback_symbol)
    except Exception as exc:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Fallback search failed: {exc}")], next_tools=["code_keyword"], usage=f"code_keyword(query={symbol!r})")
    if not fallback:
        return _response(
            "ok",
            {"symbol": symbol, "references": [], "count": 0, "method": "keyword_fallback"},
            diagnostics=[_diagnostic("not_found", f"No references found for '{symbol}'.", recovery_tools=["code_keyword"], recovery_usage=f"code_keyword(query={symbol!r})")],
            next_tools=["code_keyword"],
            usage=f"code_keyword(query={symbol!r})",
        )
    fallback_total = len(fallback)
    fallback, fallback_counts, fallback_all_counts, fallback_detail_counts, fallback_detail_all_counts = _apply_reference_filters(
        fallback,
        exclude_tests=exclude_tests,
        exclude_docs=exclude_docs,
        call_sites_only=call_sites_only,
    )
    fallback_matched_count = len(fallback)
    fallback_matched_counts = dict(fallback_counts)
    if limit is not None and limit > 0:
        fallback = fallback[:limit]
    fallback_returned_counts = _reference_counts(fallback)
    fallback_detail_returned_counts = _reference_detail_counts(fallback)
    fallback_buckets = {
        "call_sites": [r for r in fallback if _reference_bucket(str(r["reference_kind"])) == "call_sites"],
        "other": [r for r in fallback if _reference_bucket(str(r["reference_kind"])) == "other"],
        "docs": [r for r in fallback if _reference_bucket(str(r["reference_kind"])) == "docs"],
        "tests": [r for r in fallback if _reference_bucket(str(r["reference_kind"])) == "tests"],
    }
    fallback_detail_buckets = {
        "call_sites": [r for r in fallback if r["reference_kind"] == "call_sites"],
        "definition": [r for r in fallback if r["reference_kind"] == "definition"],
        "import": [r for r in fallback if r["reference_kind"] == "import"],
        "mention": [r for r in fallback if r["reference_kind"] == "mention"],
        "docs": [r for r in fallback if r["reference_kind"] == "docs"],
        "tests": [r for r in fallback if r["reference_kind"] == "tests"],
        "other": [r for r in fallback if r["reference_kind"] == "other"],
    }
    return _response(
        "ok",
        {
            "symbol": symbol,
            "references": fallback,
            "count": len(fallback),
            "matched_count": fallback_matched_count,
            "total_count": fallback_total,
            "counts": fallback_returned_counts,
            "matched_counts": fallback_matched_counts,
            "all_counts": fallback_all_counts,
            "detail_counts": fallback_detail_returned_counts,
            "detail_matched_counts": fallback_detail_counts,
            "detail_all_counts": fallback_detail_all_counts,
            "buckets": fallback_buckets,
            "detail_buckets": fallback_detail_buckets,
            "method": "keyword_fallback",
            "exclude_tests": exclude_tests,
            "exclude_docs": exclude_docs,
            "call_sites_only": call_sites_only,
            "limit": limit,
            "note": "No known-language reference search found a result. Returning broad keyword matches across the repo.",
        },
        next_tools=["code_read"],
        usage=f"code_read(path='...', start_line=N, end_line=N+20)",
    )


# ---------------------------------------------------------------------------
# code_callhierarchy — call graph for a symbol (depth 1)
# ---------------------------------------------------------------------------

MAX_CALLHIERARCHY_OUTGOING = 30
MAX_CALLHIERARCHY_INCOMING = 50


def _extract_outgoing_calls(root: Path, symbol: str, definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract function calls made within the body of *symbol*."""
    calls: dict[str, dict[str, Any]] = {}
    for defn in definitions:
        defn_path = defn.get("path", "")
        start_line = defn.get("line", 1)
        end_line = defn.get("end_line") or defn.get("line", start_line)
        if not defn_path:
            continue
        abs_path = _resolve_repo_path(root, defn_path)
        if abs_path is None:
            continue
        try:
            source = abs_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        lines = source.splitlines()
        body_lines = lines[max(0, start_line - 1): end_line]
        body = "\n".join(body_lines)
        found: set[str] = set()
        for m in _RE_CALL.finditer(body):
            found.add(m.group(1))
        for m in _RE_SQL_EXEC.finditer(body):
            found.add(m.group(1))
        for name in found:
            if name in _SYMBOL_BLOCKLIST:
                continue
            if name == symbol:
                continue
            if name not in calls:
                calls[name] = {"name": name, "file": defn_path, "line": None}
        if len(calls) >= MAX_CALLHIERARCHY_OUTGOING:
            break
    return list(calls.values())[:MAX_CALLHIERARCHY_OUTGOING]


def code_callhierarchy_response(
    root: Path,
    symbol: str,
    file: Optional[str] = None,
    direction: str = "both",
) -> dict[str, Any]:
    """Return the call hierarchy for a symbol: outgoing calls and/or incoming callers."""
    if direction not in {"both", "outgoing", "incoming"}:
        return _response(
            "error", {"symbol": symbol, "direction": direction},
            diagnostics=[_diagnostic("invalid_arguments", f"direction must be 'both', 'outgoing', or 'incoming'; got '{direction}'.")],
            next_tools=[], usage="",
        )
    if not symbol or not symbol.strip():
        return _response(
            "error", {"symbol": symbol},
            diagnostics=[_diagnostic("invalid_arguments", "symbol must be a non-empty string.")],
            next_tools=[], usage="",
        )
    symbol = symbol.strip()

    # Get definitions
    def_resp = code_definition_response(root, symbol)
    definitions: list[dict[str, Any]] = []
    parser_used = "regex"
    if def_resp.get("status") == "ok":
        definitions = def_resp["data"].get("definitions", [])
        parser_used = def_resp["data"].get("method", "regex")

    if file:
        definitions = [d for d in definitions if d.get("path", "") == file] or definitions

    data: dict[str, Any] = {
        "symbol": symbol,
        "definition_file": definitions[0]["path"] if definitions else None,
        "parser_used": parser_used,
    }

    if direction in {"both", "outgoing"}:
        outgoing = _extract_outgoing_calls(root, symbol, definitions)
        data["outgoing"] = outgoing

    if direction in {"both", "incoming"}:
        ref_resp = code_references_response(
            root, symbol, call_sites_only=True, limit=MAX_CALLHIERARCHY_INCOMING
        )
        incoming: list[dict[str, Any]] = []
        if ref_resp.get("status") == "ok":
            refs = ref_resp["data"].get("references", [])
            for ref in refs:
                incoming.append({
                    "name": symbol,
                    "file": ref.get("path", ""),
                    "line": ref.get("line"),
                    "snippet": ref.get("snippet", ""),
                })
        data["incoming"] = incoming

    return _response("ok", data, next_tools=["code_read"], usage="code_read(...)")


# ---------------------------------------------------------------------------
# code_dependencies — on-demand import graph extraction
# ---------------------------------------------------------------------------

def _parse_python_imports(source: str) -> list[dict[str, Any]]:
    import ast as _ast
    try:
        tree = _ast.parse(source)
    except SyntaxError:
        return []
    imports = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Import):
            for alias in node.names:
                imports.append({"module": alias.name, "resolved": False})
        elif isinstance(node, _ast.ImportFrom):
            module = node.module or ""
            level = node.level or 0
            name = ("." * level) + module if level else module
            imports.append({"module": name, "resolved": False})
    return imports


_JS_TS_IMPORT_RE = re.compile(r"""(?:import|export)\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]""")
_JS_TS_REQUIRE_RE = re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)""")
_GO_IMPORT_BLOCK_RE = re.compile(r"import\s*\(([^)]+)\)", re.DOTALL)
_GO_IMPORT_INLINE_RE = re.compile(r'import\s+"([^"]+)"')
_GO_IMPORT_STR_RE = re.compile(r'"([^"]+)"')
_RUST_USE_RE = re.compile(r"^(?:pub\s+)?use\s+([\w:]+)", re.MULTILINE)


def _parse_js_ts_imports(source: str) -> list[dict[str, Any]]:
    imports = []
    for m in _JS_TS_IMPORT_RE.finditer(source):
        imports.append({"module": m.group(1), "resolved": False})
    for m in _JS_TS_REQUIRE_RE.finditer(source):
        imports.append({"module": m.group(1), "resolved": False})
    return imports


def _parse_go_imports(source: str) -> list[dict[str, Any]]:
    imports = []
    for block in _GO_IMPORT_BLOCK_RE.finditer(source):
        for m in _GO_IMPORT_STR_RE.finditer(block.group(1)):
            imports.append({"module": m.group(1), "resolved": False})
    for m in _GO_IMPORT_INLINE_RE.finditer(source):
        imports.append({"module": m.group(1), "resolved": False})
    return imports


def _parse_rust_imports(source: str) -> list[dict[str, Any]]:
    imports = []
    for m in _RUST_USE_RE.finditer(source):
        imports.append({"module": m.group(1), "resolved": False})
    return imports


_IMPORT_PARSERS: dict[str, Any] = {
    "python": (_parse_python_imports, "ast"),
    "javascript": (_parse_js_ts_imports, "regex"),
    "typescript": (_parse_js_ts_imports, "regex"),
    "go": (_parse_go_imports, "regex"),
    "rust": (_parse_rust_imports, "regex"),
}

_JS_TS_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}


def code_dependencies_response(root: Path, path: str) -> dict[str, Any]:
    """Return imported modules/files for a given repo-relative path, parsed on demand."""
    rel = path.strip().replace("\\", "/")
    if not rel:
        return _response("error", {"path": rel}, diagnostics=[_diagnostic("invalid_arguments", "path must be a non-empty repo-relative file path.")], next_tools=["code_list_files"], usage="code_list_files()")
    abs_path = _resolve_repo_path(root, rel)
    if abs_path is None:
        return _response("error", {"path": rel}, diagnostics=[_diagnostic("invalid_arguments", "path escapes the repository root or is absolute.")], next_tools=["code_list_files"], usage="code_list_files()")
    try:
        source = abs_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return _response("error", {"path": rel}, diagnostics=[_diagnostic("file_not_found", f"File not found: {rel}")], next_tools=["code_list_files"], usage="code_list_files()")
    except OSError as exc:
        return _response("error", {"path": rel}, diagnostics=[_diagnostic("read_error", str(exc))], next_tools=[], usage="")

    suffix = Path(rel).suffix.lower()
    if suffix == ".py":
        lang = "python"
    elif suffix in _JS_TS_SUFFIXES:
        lang = _EXT_TO_LANG.get(suffix, "javascript")
    else:
        lang = _EXT_TO_LANG.get(suffix, "")

    parser_entry = _IMPORT_PARSERS.get(lang)
    if not parser_entry:
        return _response("ok", {"path": rel, "imports": [], "method": "unsupported"}, next_tools=[], usage="")

    parser_fn, method = parser_entry
    imports = parser_fn(source)
    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped = []
    for entry in imports:
        mod = entry["module"]
        if mod not in seen:
            seen.add(mod)
            deduped.append(entry)

    return _response(
        "ok",
        {"path": rel, "imports": deduped, "method": method},
        next_tools=["code_read"],
        usage=f"code_read(path={rel!r})",
    )


# ---------------------------------------------------------------------------
# code_impact — reverse dependency / impact analysis
# ---------------------------------------------------------------------------


def _match_import_to_target(import_entry: dict[str, Any], target_rel: str, importing_file_rel: str) -> bool:
    """Return True if *import_entry* appears to import *target_rel*."""
    module = import_entry.get("module", "")
    if not module:
        return False

    target_path = Path(target_rel)
    target_stem = target_rel
    for ext in (".py", ".ts", ".js", ".tsx", ".jsx"):
        if target_stem.endswith(ext):
            target_stem = target_stem[: -len(ext)]
            break

    # Heuristic 1: module path normalization
    # Strip leading dots (relative Python imports) then normalize
    stripped = module.lstrip(".")
    normalized = stripped.replace(".", "/")
    if (
        normalized == target_stem
        or target_rel.endswith("/" + normalized + ".py")
        or target_rel.endswith("/" + normalized + ".ts")
        or target_rel.endswith("/" + normalized + ".js")
        or target_rel.endswith("/" + normalized + ".tsx")
        or target_rel.endswith("/" + normalized + ".jsx")
        or target_stem.endswith("/" + normalized)
        or normalized == target_stem.split("/")[-1]
    ):
        return True

    # Heuristic 2: filename stem match (≥ 4 chars)
    module_parts = normalized.replace("/", ".").split(".")
    module_last = module_parts[-1] if module_parts else ""
    target_file_stem = target_path.stem
    if len(module_last) >= 4 and module_last == target_file_stem:
        return True

    # Heuristic 3: relative path resolution for JS/TS ./.. imports
    if module.startswith(("./", "../")):
        importing_dir = Path(importing_file_rel).parent
        try:
            resolved_base = (importing_dir / module).as_posix()
            # Normalize to remove .. components
            resolved_parts = []
            for part in resolved_base.split("/"):
                if part == "..":
                    if resolved_parts:
                        resolved_parts.pop()
                else:
                    resolved_parts.append(part)
            resolved_str = "/".join(resolved_parts)
            # Ensure no escaping
            if resolved_str.startswith(".."):
                pass  # escaped repo, skip
            else:
                candidates = [
                    resolved_str,
                    resolved_str + ".ts",
                    resolved_str + ".tsx",
                    resolved_str + ".js",
                    resolved_str + ".jsx",
                    resolved_str + "/index.ts",
                    resolved_str + "/index.js",
                ]
                if target_rel in candidates:
                    return True
        except Exception:
            pass

    return False


def code_impact_response(root: Path, path: str, max_results: int = 50) -> dict[str, Any]:
    """Find all files that import a given file (reverse dependency analysis)."""
    resolved = _resolve_repo_path(root, path)
    if resolved is None:
        return _response(
            "error", {"path": path},
            diagnostics=[_diagnostic("path_rejected", f"Path '{path}' is outside the project root or invalid.")],
            next_tools=["code_list_files"], usage="code_list_files()",
        )
    if not resolved.exists():
        return _response(
            "error", {"path": path},
            diagnostics=[_diagnostic("file_not_found", f"File '{path}' does not exist.")],
            next_tools=["code_list_files"], usage="code_list_files()",
        )

    root_r = root.resolve()
    target_rel = str(resolved.relative_to(root_r)).replace("\\", "/")

    importers: list[dict[str, Any]] = []
    total = 0
    limit_hit = max_results + 1

    for p in _walk_repo_for_navigation(root):
        file_rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        if file_rel == target_rel:
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue

        suffix = p.suffix.lower()
        if suffix == ".py":
            lang = "python"
        elif suffix in _JS_TS_SUFFIXES:
            lang = _EXT_TO_LANG.get(suffix, "javascript")
        else:
            lang = _EXT_TO_LANG.get(suffix, "")

        parser_entry = _IMPORT_PARSERS.get(lang)
        if not parser_entry:
            continue

        parser_fn, _ = parser_entry
        try:
            imports = parser_fn(source)
        except Exception:
            continue

        for imp in imports:
            if _match_import_to_target(imp, target_rel, file_rel):
                total += 1
                if len(importers) < max_results:
                    importers.append({
                        "file": file_rel,
                        "import_statement": imp.get("module", ""),
                        "kind": imp.get("kind", "import"),
                    })
                if total >= limit_hit:
                    break
        if total >= limit_hit:
            break

    return _response(
        "ok",
        {
            "path": target_rel,
            "importers": importers,
            "truncated": total > max_results,
            "total_found": total,
            "method": "heuristic",
        },
        next_tools=["code_read"],
        usage=f"code_read(path='{target_rel}')",
    )


# ---------------------------------------------------------------------------
# code_ask — mechanical retrieval routing for codebase Q&A
# ---------------------------------------------------------------------------

def _partition_infra(results: list[dict]) -> list[dict]:
    """Stable index-based partition: move scaffolding-layer results to the end.

    Uses enumerate to avoid false drops from dict equality comparison when two
    results share identical content (same path, text, score).
    """
    infra_idx = {
        i for i, r in enumerate(results)
        if any(seg in Path(r.get("path", "")).parts for seg in INFRASTRUCTURE_PATH_SEGMENTS)
    }
    non_infra = [r for i, r in enumerate(results) if i not in infra_idx]
    infra = [r for i, r in enumerate(results) if i in infra_idx]
    return non_infra + infra


# Test-file detection: directory segments and filename patterns across ecosystems.
# Directory check uses exact segment matching (not substring) to avoid false positives
# such as src/contest/ matching "test". Filename regex covers Python, Go, Java, C#,
# JS/TS, Swift, Kotlin, Ruby, and PHP conventions.
_TEST_DIR_SEGMENTS = frozenset(["tests", "test", "__tests__", "spec", "specs"])
_TEST_FILENAME_RE = re.compile(
    r"^test_"                                               # Python: test_foo.py
    r"|_test\.[a-z]+$"                                      # Go/Python: foo_test.go
    r"|(?:Tests?|TestCase|TestSuite|Specs?)\.[a-zA-Z]+$"    # Java/C#/Swift/Kotlin: FooTest.java
    r"|\.(?:test|spec)\.[a-z]+$"                            # JS/TS: foo.test.js, foo.spec.ts
)


def _is_test_path(path: str) -> bool:
    """Return True when path belongs to a test file across common ecosystems."""
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    name = parts[-1] if parts else ""
    return (
        any(p.lower() in _TEST_DIR_SEGMENTS for p in parts[:-1])
        or bool(_TEST_FILENAME_RE.search(name))
    )


def _partition_tests(results: list[dict]) -> list[dict]:
    """Stable index-based partition: move test-file citations to the end.

    Applied after reranking in the artifact-anchored exact-first path so
    implementation owner files rank ahead of test fixtures.
    Uses enumerate to avoid false drops from dict equality comparison when two
    results share identical content.
    """
    test_idx = {i for i, r in enumerate(results) if _is_test_path(r.get("path", ""))}
    non_test = [r for i, r in enumerate(results) if i not in test_idx]
    test = [r for i, r in enumerate(results) if i in test_idx]
    return non_test + test


def _doc_demotion_weight(path: str, kind: str) -> float:
    """Return the demotion multiplier for a result based on its path and kind."""
    normalized = (path or "").replace("\\", "/")
    if normalized.startswith("docs/waves/"):
        return _DEMOTION_WAVES
    if normalized.startswith("docs/plans/"):
        return _DEMOTION_PLANS
    if kind == "seed" or normalized.startswith(".wavefoundry/framework/seeds/"):
        return _DEMOTION_SEEDS
    parts = Path(normalized).parts
    name = Path(normalized).name.lower()
    if any(seg in parts for seg in ("journals", "reports")) or "feedback" in name or "journal" in name:
        return _DEMOTION_JRNLS
    return 1.0


def _demote_doc_results(results: list[dict], question_type: str) -> tuple[list[dict], int]:
    """Apply weighted score demotion to narrative/feedback sources for explanatory queries."""
    if question_type != "explanatory":
        return results, 0

    demotion_count = 0
    for r in results:
        weight = _doc_demotion_weight(r.get("path", ""), str(r.get("kind") or "").strip().lower())
        if weight < 1.0:
            r["score"] = (r.get("score") or 0.0) * weight
            demotion_count += 1

    if demotion_count:
        results.sort(key=lambda x: x.get("score") or 0.0, reverse=True)

    return results, demotion_count


def _extract_question_symbol(question: str) -> Optional[str]:
    """Extract the primary code symbol from a question for symbol-first injection."""
    m = re.search(r'`([^`]+)`', question)
    if m:
        sym = m.group(1).strip()
        if sym:
            return sym
    m = re.search(r'\b(\w+(?:(?:\.|::|->)\w+)+)\b', question)
    if m:
        qualified = m.group(1)
        sym = re.split(r'\.|::|->', qualified)[-1]
        if sym:
            return sym
    m = re.search(r'@(\w+)', question)
    if m:
        return '@' + m.group(1)
    m = re.search(r'\b(_\w+)\b', question)
    if m:
        return m.group(1)
    m = re.search(r'\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b', question)
    if m:
        return m.group(1)
    m = re.search(r'\b([a-z][a-z0-9]+(?:_[a-z0-9]+)+)\b', question)
    if m:
        return m.group(1)
    m = re.search(r'\b([a-z][a-z0-9]*(?:[A-Z][a-zA-Z0-9]*)+)\b', question)
    if m:
        return m.group(1)
    m = re.search(r'\b([A-Z][a-zA-Z0-9]{3,})\b', question)
    if m:
        return m.group(1)
    return None


def _extract_symbols_ts(tree: Any) -> list[str]:
    """Walk a tree-sitter parse tree and extract called function/method names."""
    symbols: list[str] = []

    def walk(node: Any) -> None:
        if node.type in _TS_CALL_TYPES:
            for child in node.children:
                if child.type in _TS_IDENTIFIER_TYPES:
                    text = child.text.decode("utf-8", errors="replace").strip()
                    if text:
                        symbols.append(text)
                    break
                elif child.type in _TS_MEMBER_TYPES:
                    for attr_child in reversed(child.children):
                        if attr_child.type in _TS_IDENTIFIER_TYPES:
                            text = attr_child.text.decode("utf-8", errors="replace").strip()
                            if text:
                                symbols.append(text)
                            break
                    break
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return symbols


def _extract_symbols_python(text: str) -> list[str]:
    """Use stdlib ast to extract called and imported names from Python source."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    symbols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                symbols.append(func.id)
            elif isinstance(func, ast.Attribute):
                symbols.append(func.attr)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                symbols.append(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                symbols.append(alias.asname or alias.name)
    return symbols


def _extract_symbols_regex(text: str) -> list[str]:
    """Regex-based symbol extraction for unsupported languages or parse failures."""
    symbols = list(_RE_CALL.findall(text))
    symbols += _RE_SQL_EXEC.findall(text)
    symbols += _RE_IMPORT.findall(text)
    return symbols


def _extract_symbols_from_citations(
    citations: list[dict],
    max_symbols: int = MAX_SYMBOLS_EXTRACTED,
) -> tuple[list[str], str]:
    """Extract referenced symbol names from the top non-infra citation texts.

    Strategy:
    - Python chunks: stdlib ``ast.parse`` for accurate call/import extraction.
    - JS/TS/Java/C# chunks: tree-sitter via the chunker module (lazy-loaded);
      falls back to regex if unavailable or parse fails.
    - All other languages: regex.

    Filters infra-path citations before extraction (they import many symbols
    and would bias second-hop expansion toward wiring/routing files).
    Deduplicates, enforces min length ≥ 4, removes blocklisted names, caps at
    ``max_symbols``.

    Returns ``(symbols, symbol_extraction_method)`` where ``symbol_extraction_method``
    is one of:

    - ``"ast"`` — Python stdlib AST or tree-sitter produced at least one symbol.
    - ``"regex"`` — regex was the effective extractor for all processed citations
      and no TS-eligible language was present (regex is the expected path).
    - ``"regex_fallback"`` — a TS-eligible language was present but tree-sitter
      was unavailable or failed; regex ran as a degradation fallback.
    - ``"none"`` — no citations survived the infra filter; no extraction was attempted.

    ``"regex_fallback"`` signals silent tree-sitter grammar degradation: callers can
    detect missing grammars at query time and alert operators.
    ``"none"`` distinguishes the empty-top-citations case from ``"regex"``/``"regex_fallback"``
    (where regex actually ran).
    """
    non_infra = [
        r for r in citations
        if not any(
            seg in Path(r.get("path", "")).parts
            for seg in INFRASTRUCTURE_PATH_SEGMENTS
        )
    ]
    top = non_infra[:3]

    if not top:
        return [], "none"

    raw: list[str] = []
    chunker: Any = None  # None = not yet attempted; False = failed to load
    ast_succeeded = False
    ts_eligible_seen = False  # True if any citation was a TS-eligible language

    for r in top:
        text = r.get("text", "")
        if not text:
            continue
        lang = r.get("language", "")

        if lang == "python":
            extracted = _extract_symbols_python(text)
            if extracted:
                ast_succeeded = True
            else:
                extracted = _extract_symbols_regex(text)
            raw.extend(extracted)
        elif lang in _TS_SYMBOL_LANG_MAP:
            ts_eligible_seen = True
            # Try tree-sitter primary
            if chunker is None:
                try:
                    chunker = _get_chunker_module()
                except Exception:
                    chunker = False
            extracted = []
            if chunker:
                try:
                    tree = chunker._ts_parse(_TS_SYMBOL_LANG_MAP[lang], text)
                    if tree is not None:
                        extracted = _extract_symbols_ts(tree)
                        if extracted:
                            ast_succeeded = True
                except Exception:
                    pass
            if not extracted:
                extracted = _extract_symbols_regex(text)
            raw.extend(extracted)
        else:
            raw.extend(_extract_symbols_regex(text))

    # Post-filter: deduplicate, min length, blocklist, cap
    seen: set[str] = set()
    result: list[str] = []
    for sym in raw:
        sym = sym.strip()
        if (
            len(sym) >= 4
            and sym.lower() not in _SYMBOL_BLOCKLIST
            and sym.lower() not in seen
        ):
            seen.add(sym.lower())
            result.append(sym)
            if len(result) >= max_symbols:
                break

    if ast_succeeded:
        method = "ast"
    elif ts_eligible_seen:
        method = "regex_fallback"  # TS-eligible language present but grammar unavailable/degraded
    else:
        method = "regex"           # no TS-eligible language — regex is the expected extractor
    return result, method


# Artifact-anchored question detection: implementation verbs + concrete artifact cue.
# A question qualifies as artifact_anchored when it contains both a verb from
# _ARTIFACT_VERBS and a token matched by _ARTIFACT_CUE_RE. Detection uses named
# constants so the scope is auditable and extensible without reimplementing the classifier.
_ARTIFACT_VERBS = frozenset([
    "generated", "generate", "generates",
    "derived", "derive", "derives",
    "stamped", "stamp", "stamps",
    "computed", "compute", "computes",
    "encoded", "encode", "encodes",
    "written", "writes", "write",
])
_ARTIFACT_CUE_RE = re.compile(
    r"\+[a-z0-9]{4,5}"                             # version suffix like +2vr8
    r"|\w+\.(?:py|toml|json|md|yaml|yml|js|ts)\b"  # dotted filename like lifecycle_id.py
    r"|[A-Z][a-z]+[A-Z]\w+"                        # CamelCase identifier like BuildPrefix
    r"|[a-z]{3,}_[a-z]{2,}\w*"                     # snake_case identifier like build_prefix
)


def _extract_artifact_cue(question: str) -> str:
    """Return the first concrete artifact cue token in question, or empty string."""
    m = _ARTIFACT_CUE_RE.search(question)
    return m.group(0) if m else ""


def _classify_question(question: str) -> str:
    """Heuristic question classifier: navigational | explanatory | instructional | artifact_anchored."""
    q = question.lower()
    navigational_signals = ["where is", "where are", "where can i find", "which file", "what file", "find the", "find where", "locate the", "path to"]
    instructional_signals = ["how do i", "how to", "steps to", "how can i", "how should i", "how would i"]
    for sig in instructional_signals:
        if sig in q:
            return "instructional"
    for sig in navigational_signals:
        if sig in q:
            return "navigational"
    if any(verb in q for verb in _ARTIFACT_VERBS) and _extract_artifact_cue(question):
        return "artifact_anchored"
    return "explanatory"


def _heuristic_confidence(citations: list[dict]) -> str:
    if len(citations) >= 2:
        return "high"
    if len(citations) == 1:
        return "medium"
    return "low"


def code_ask_response(index: "WaveIndex", root: Path, question: str) -> dict[str, Any]:
    """Mechanical routing: broad retrieval pass → targeted pass → assemble structured response."""
    t_start = time.monotonic()

    question = question.strip()
    if not question:
        return _response("error", {"question": question}, diagnostics=[_diagnostic("invalid_arguments", "question must be a non-empty string.")], next_tools=[], usage="")

    question_type = _classify_question(question)
    gaps: list[str] = []
    citations: list[dict] = []

    # Check index freshness
    try:
        health = index._layer_health("project")
        chunker_versions = health.get("indexed_chunker_versions", {})
        current_cv = health.get("current_chunker_version", "")
        is_stale = bool(chunker_versions) and any(v != current_cv for v in chunker_versions.values())
    except Exception:
        is_stale = False
    index_freshness = "stale" if is_stale else "current"

    # Broad pass: combined semantic search with reranking
    combined_reranked = False
    vector_ms = 0
    rerank_ms = 0
    infrastructure_demoted = False
    definition_boosted: list[str] = []
    second_hop_symbols: list[str] = []
    symbol_extraction_method: str = "none"
    try:
        combined_results, combined_reranked, vector_ms, rerank_ms, definition_boosted, second_hop_symbols, symbol_extraction_method = index.search_combined(
            question, top_n=7, question_type=question_type
        )
        # Detect whether the scaffolding-layer partition fired (explanatory questions only)
        if question_type == "explanatory" and combined_reranked and combined_results:
            infra_paths = {
                r.get("path", "") for r in combined_results
                if any(seg in Path(r.get("path", "")).parts for seg in INFRASTRUCTURE_PATH_SEGMENTS)
            }
            infrastructure_demoted = bool(infra_paths)
    except Exception:
        combined_results = []
        gaps.append("search index unavailable")

    def _to_citation(r: dict) -> dict:
        path = r.get("path", "")
        lines = r.get("lines") or []
        line_range = f":{lines[0]}-{lines[1]}" if len(lines) == 2 else ""
        return {
            "ref": f"{path}{line_range}",
            "path": path,
            "lines": lines,
            "excerpt": (r.get("text") or "")[:300],
            "score": r.get("score"),
            "kind": r.get("kind"),
        }

    broad_hits = combined_results
    broad_hits, demotion_count = _demote_doc_results(broad_hits, question_type)
    partition_applied = bool(demotion_count)
    citations = []
    for final_rank, r in enumerate(broad_hits, start=1):
        citation = _to_citation(r)
        citation["final_rank"] = final_rank
        citations.append(citation)

    # Targeted pass: keyword and structural lookup when broad pass is thin
    if len(citations) < 2:
        try:
            kw_resp = code_keyword_response(root, question.split()[0] if question.split() else question)
            if kw_resp.get("status") != "ok":
                gaps.append("keyword search failed")
            else:
                kw_results = kw_resp.get("data", {}).get("results", [])[:3]
                for r in kw_results:
                    citations.append({
                        "ref": f"{r.get('path', '')}:{r.get('line', '')}",
                        "path": r.get("path", ""),
                        "lines": [r.get("line"), r.get("line")],
                        "excerpt": r.get("snippet", ""),
                        "score": None,
                        "kind": "keyword",
                    })
        except Exception:
            gaps.append("keyword search unavailable")

    if not citations:
        gaps.append(f"no indexed evidence found for: {question!r}")

    for final_rank, citation in enumerate(citations, start=1):
        citation["final_rank"] = final_rank

    confidence = _heuristic_confidence(citations)

    # Assemble answer text from top citations
    if citations:
        top = citations[0]
        answer = f"Based on indexed sources: see {top['ref']}."
        if len(citations) > 1:
            answer += f" Additional evidence in {', '.join(c['ref'] for c in citations[1:3])}."
    else:
        answer = f"No indexed evidence found for this question. The topic may not be covered in the current index or may use different terminology."

    total_ms = round((time.monotonic() - t_start) * 1000)
    _wf_log(f"[wavefoundry] code_ask timing: total={total_ms}ms vector={vector_ms}ms rerank={rerank_ms}ms")

    data: dict[str, Any] = {
        "question": question,
        "question_type": question_type,
        "answer": answer,
        "citations": citations,
        "confidence": confidence,
        "gaps": gaps,
        "index_freshness": index_freshness,
        "reranked": combined_reranked,
        "partition_applied": partition_applied,
        "demotion_count": demotion_count,
        "total_ms": total_ms,
        "vector_ms": vector_ms,
        "rerank_ms": rerank_ms,
    }
    if infrastructure_demoted:
        data["infrastructure_demoted"] = True
    if definition_boosted:
        data["definition_boosted"] = definition_boosted
    if second_hop_symbols:
        data["second_hop_symbols"] = second_hop_symbols
    if symbol_extraction_method != "none":
        data["symbol_extraction_method"] = symbol_extraction_method

    if question_type == "explanatory" and citations and citations[0].get("kind") in ("doc", "doc-summary"):
        data["validation_required"] = True

    next_tools = ["code_read", "docs_search"]
    if citations:
        top_path = citations[0].get("path", "")
        if top_path:
            try:
                with (root / top_path).open() as _f:
                    line_count = sum(1 for _ in _f)
                if line_count > 300:
                    next_tools = ["code_outline", "code_read"]
            except Exception:
                pass

    return _response(
        "ok",
        data,
        next_tools=next_tools,
        usage=f"code_read(path={citations[0]['path']!r}, start_line={citations[0]['lines'][0] if citations[0]['lines'] else 1})" if citations else "code_search(query=...)",
    )


# ---------------------------------------------------------------------------
# Implementation version (refreshed on importlib.reload)
# ---------------------------------------------------------------------------

SERVER_RUNNER_VERSION = "1"  # re-exported alias; canonical runner version lives in server.py


def _read_framework_pack_version(*, scripts_dir: Path | None = None) -> str:
    scripts_dir = scripts_dir or Path(__file__).resolve().parent
    version_path = scripts_dir.parent / "VERSION"
    try:
        return version_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _read_framework_version_at_root(root: Path) -> str:
    version_path = root.resolve() / ".wavefoundry" / "framework" / "VERSION"
    try:
        return version_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


SERVER_IMPL_VERSION = _read_framework_pack_version()

_runner_version: str = ""


def set_server_runner_version(v: str) -> None:
    global _runner_version
    _runner_version = v


def version_payload(root: Path, *, server_runner_version: str) -> dict[str, Any]:
    framework_version = _read_framework_version_at_root(root)
    impl_version = SERVER_IMPL_VERSION
    impl_matches_disk: bool | None = None
    if framework_version and impl_version:
        impl_matches_disk = framework_version == impl_version
    return {
        "framework_version": framework_version,
        "server_runner_version": server_runner_version,
        "server_impl_version": impl_version,
        "impl_matches_disk": impl_matches_disk,
    }


class ImplHandler:
    """Owns per-process MCP business state (index, cache, root)."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.index = WaveIndex(self.root)
        self.index._start_background_model_downloads()
        self.cache = McpRepoCache(self.root, index=self.index)

    def close(self) -> None:
        self.cache.invalidate()
        self.index._loaded = False
        self.index._docs_lance_table = None
        self.index._code_lance_table = None
        self.index._reranker = None
        self.index._model_downloads_started = False
        self.index._loaded_meta_signature = {}
        self.index._lance_available = set()


def build_handler(root: Path) -> ImplHandler:
    return ImplHandler(root)


def wave_server_info_response(root: Path, *, server_runner_version: str | None = None) -> dict[str, Any]:
    return _response(
        "ok",
        server_identity(root, server_runner_version=server_runner_version),
        next_tools=["wave_current", "wave_help"],
        usage="wave_server_info()",
    )

def register_mcp_surface(mcp: Any, get_handler: Any) -> None:
    """Register tools and resources; resolve state via get_handler() for hot reload."""
    # Tool annotation constants — passed to @mcp.tool(annotations={...}).
    # All handlers also accept **kwargs so FastMCP's auto-generated "kwargs"
    # schema parameter is captured and rejected via _ensure_no_extra_args rather
    # than causing an unexpected-argument error at the Python call boundary.
    _READONLY_TOOL = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
    _MUTATING_TOOL = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}
    _DESTRUCTIVE_TOOL = {"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}

    # --- Search and retrieval ---

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_help(goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Return a structured MCP workflow catalogue or a goal-specific recommended chain.

        Args:
            goal: Optional workflow goal, e.g. "plan_feature" or "inspect_wave".
        """
        bad = _ensure_no_extra_args("wave_help", kwargs)
        if bad is not None:
            return bad
        return wave_help_response(goal)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_server_info(**kwargs: Any) -> dict[str, Any]:
        """Return the repository root and implementation version info for this MCP server.

        Use immediately after connect when you need to confirm which checkout this server is attached to.
        """
        bad = _ensure_no_extra_args("wave_server_info", kwargs)
        if bad is not None:
            return bad
        return wave_server_info_response(get_handler().root)

    @mcp.tool(annotations=_READONLY_TOOL)
    def docs_search(
        query: str,
        kind: Literal["", "doc", "seed", "architecture", "prompt", "doc-summary"] = "",
        tags: list = [],
        limit: int = 7,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Semantic search over docs, architecture, prompts, seed chunks, and framework seeds at .wavefoundry/framework/seeds/.

        Prefer when: searching by concept, intent, or natural language across project and framework documentation.
        Use code_keyword instead when the exact text is known.
        Degrades to lexical fallback when the semantic model or index is unavailable.

        Tags pre-filter the search space before cosine ranking. Use to scope results to a specific doc category.
        Tag vocabulary: wave, agent, lifecycle, reference, journal, prompt, seed, framework, test, config.
        Multiple tags use OR semantics (a chunk matching any requested tag is included).
        kind and tags compose with AND semantics (a chunk must satisfy both when both are provided).
        Examples: tags=["wave"] for wave records, tags=["agent"] for agent prompts and journals,
                  tags=["lifecycle"] for install/onboarding docs, tags=["journal"] for agent journals only.

        Args:
            query: Natural language search query.
            kind: Optional filter — one of: doc, seed, architecture, prompt, doc-summary.
            tags: Optional list of classification tags to pre-filter results. See tag vocabulary above.
            limit: Maximum results to return (1–20, default 7).
        """
        bad = _ensure_no_extra_args("docs_search", kwargs)
        if bad is not None:
            return bad
        return docs_search_response(get_handler().index, query, kind, limit=limit, tags=tags or None)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_search(query: str, language: str = "", kind: str = "", max_per_file: int = 0, tags: list = [], limit: int = 7, **kwargs: Any) -> dict[str, Any]:
        """Semantic search over indexed source code chunks. Requires a built code index (wave_index_build content='code').

        Prefer when: searching for code by concept, behavior, or intent (e.g. "React component with loading state").
        Use code_keyword instead when the exact token, symbol, or string is known — always available, deterministic.
        Use docs_search instead when the answer is in a spec, architecture doc, or prompt rather than source code.
        When the code index is absent: returns status='error' with a diagnostic — does not crash.

        Orientation pass (Guru): use kind="code-summary" with max_per_file=1 for a fast file-level survey before targeted retrieval.

        Tags pre-filter the search space before cosine ranking. Use to scope results to a specific file category.
        Tag vocabulary: test, config, framework, seed. Multiple tags use OR semantics.
        language, kind, and tags all compose with AND semantics when provided together.
        Example: tags=["test"] to scope to test files only, tags=["config"] for config/infra files.

        Choosing a language filter:
        - No filter: query spans the whole codebase. Best when you don't know which language has the answer.
        - Category: use when the answer could be in any language of a family, or the codebase mixes them.
          Categories: java (java/kotlin/scala/groovy), web (typescript/javascript/html/css/scss),
          systems (c/cpp/rust/go), script (python/ruby/shell/fish), data (sql), sparksql (sql alias), dotnet (csharp).
          Category responses include language_resolved (expanded language list) and language_extensions.
        - Canonical name or extension: use when you know the exact language. e.g. "python", "typescript", "tsx", ".tsx".
          Note: .tsx and .ts files are both indexed as language="typescript" — tsx/.tsx normalizes to typescript.
          Use "web" (category) if you want TypeScript + JavaScript + HTML + CSS + SCSS together.

        Args:
            query: Natural language description of the code behavior or concept to find.
            language: Optional — category name, canonical language name, or raw extension (with or without dot).
            kind: Optional — filter to a specific chunk kind. Use "code-summary" for file-level orientation chunks only.
            max_per_file: Optional — cap results per file path (0 = no cap). Use 1 for orientation pass diversity.
            tags: Optional list of classification tags to pre-filter results. See tag vocabulary above.
            limit: Maximum results to return (1–20, default 7).
        """
        bad = _ensure_no_extra_args("code_search", kwargs)
        if bad is not None:
            return bad
        return code_search_response(get_handler().index, query, language, limit=limit, kind=kind or None, max_per_file=max_per_file or None, tags=tags or None)

    @mcp.tool(annotations=_READONLY_TOOL)
    def seed_get(name: str, **kwargs: Any) -> dict[str, Any]:
        """Retrieve a framework seed prompt by name or partial slug.

        Prefer when: you know the seed name or number. Use docs_search instead when searching for seed content by concept.

        Args:
            name: Seed name or partial slug, e.g. "plan-feature" or "020-run-contract".
        """
        bad = _ensure_no_extra_args("seed_get", kwargs)
        if bad is not None:
            return bad
        return seed_get_response(get_handler().index, name)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_dependencies(path: str, **kwargs: Any) -> dict[str, Any]:
        """Return the list of imported modules/files for a repo-relative source file, parsed on demand.

        Prefer when: you need to understand what a file imports without reading the full source.
        Supports Python (AST), JavaScript/TypeScript, Go, and Rust (regex). Returns method="unsupported" for other languages.

        Args:
            path: Repo-relative file path, e.g. "src/billing.py" or "src/App.tsx".
        """
        bad = _ensure_no_extra_args("code_dependencies", kwargs)
        if bad is not None:
            return bad
        return code_dependencies_response(get_handler().root, path)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_hover(path: str, line: int, **kwargs: Any) -> dict[str, Any]:
        """Return the symbol (function, class, or method) enclosing a given line number.

        Prefer when: you need the signature and docstring for the symbol at a specific
        line without reading 50 lines of context. Faster than code_outline when you
        already know the line number.

        Response fields:
        - file: repo-relative path
        - line: requested line number (1-based)
        - symbol: {name, kind, signature, docstring, start_line, end_line} or null if no symbol encloses the line
        - parser_used: "python_ast" | "tree_sitter" | "regex"

        Args:
            path: Repo-relative file path, e.g. "src/server.py".
            line: 1-based line number to look up.
        """
        bad = _ensure_no_extra_args("code_hover", kwargs)
        if bad is not None:
            return bad
        return code_hover_response(get_handler().root, path, line)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_impact(path: str, max_results: int = 50, **kwargs: Any) -> dict[str, Any]:
        """Find all files that import a given file (reverse dependency / impact analysis).

        Prefer when: assessing the blast radius of a change, planning a file deletion,
        or tracing who depends on a module. Complements code_dependencies (which shows
        what a file imports) with the reverse direction.

        Matching is heuristic (not compiler-resolved): three strategies are tried —
        module-path normalization, filename-stem match (≥4 chars), and relative
        ./..  path resolution for JS/TS imports. Results include method="heuristic"
        to signal approximate matching.

        Response fields:
        - path: repo-relative path of the target file
        - importers: list of {file, import_statement, kind} — files that import the target
        - truncated: true when more than max_results importers were found
        - total_found: total importer count before truncation
        - method: "heuristic"

        Args:
            path: Repo-relative path of the file to find importers for, e.g. "src/auth/user.py".
            max_results: Maximum importers to return (default 50).
        """
        bad = _ensure_no_extra_args("code_impact", kwargs)
        if bad is not None:
            return bad
        return code_impact_response(get_handler().root, path, max_results)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_ask(question: str, **kwargs: Any) -> dict[str, Any]:
        """Ask a natural-language question about the codebase and receive a grounded, cited answer.

        Prefer when: the question spans multiple files or layers ("how does X work end-to-end?",
        "what calls Y?", "where is Z implemented?"). Use code_search or docs_search directly when
        you want raw result lists to browse rather than a pre-assembled answer.

        Performs mechanical retrieval routing: broad semantic pass (code_search + docs_search) followed by
        targeted keyword pass. Returns a structured response with citations, confidence, and gaps.
        No LLM synthesis occurs in this tool — the calling agent synthesizes from the returned citations.

        Response fields:
        - answer: Navigation pointer ("Based on indexed sources: see X") — ignore this field; synthesize
          directly from citations.
        - citations: List of {ref, path, lines, excerpt, score, kind}. kind="keyword" means the semantic
          pass was thin and keyword fallback fired — results are still relevant but ranked by term overlap,
          not vector similarity.
        - reranked: true means cross-encoder reranking ran and ranking is high-quality; false means RRF
          fallback fired (index or model unavailable) and ranking is slightly lower quality.
        - confidence: "high" (2+ citations), "medium" (1 citation), "low" (no evidence). Retrieval signal
          only — not an answer-quality signal. Evaluate citations by path and content, not confidence alone;
          high confidence with wrong-layer citations (e.g. infrastructure scaffolding for an explanatory
          question) still requires follow-up reads of the actual handler or repository layer.
        - gaps: Retrieval gaps or index unavailability notices
        - question_type: "navigational" | "explanatory" | "instructional". Influences retrieval pool
          weighting and candidate window size. "explanatory" triggers two enhancements when the
          cross-encoder reranker is available: (1) a wider candidate window (VECTOR_TOP_K_EXPLANATORY=60
          per index vs 30 for other types), and (2) two-hop symbol expansion — symbol names are extracted
          from the top reranked citations and a second keyword retrieval pass fetches their definitions,
          reaching call-chain layers the original query vocabulary cannot reach. Navigational questions
          bias toward code results via RRF weight adjustment.
        - second_hop_symbols: list of symbol names that triggered second-hop retrieval for explanatory
          questions. Only present when non-empty. When present: the citations already include candidates
          surfaced by following these symbols one layer deeper; use this list to understand which call
          chain references were automatically expanded rather than re-chasing them manually. Absent when
          question_type != "explanatory", reranked=false, or no extractable symbols were found in the
          top citations.
        - symbol_extraction_method: extraction method used for the two-hop symbol pass. Present when
          the second-hop gate fired and at least one citation survived the infra filter. Values: "ast"
          — Python stdlib AST or tree-sitter produced at least one symbol; "regex" — AST was
          unavailable or produced no symbols (regex was the effective extractor). Use this field to
          detect silent grammar degradation: "regex" on a TypeScript-heavy codebase indicates the
          tree-sitter grammar failed to load or produced no symbols.
        - validation_required: present and true when question_type=="explanatory" and the top
          citation is a doc or doc-summary (spec, architecture, or reference doc). When present,
          code_read in next_tools is a REQUIRED continuation — not optional. A spec citation is
          the starting point, not the answer; read the implementation file named in the spec's
          source metadata before synthesizing.
        - index_freshness: "current" | "stale"
        - vector_ms: milliseconds spent on vector retrieval across all indexes.
        - rerank_ms: milliseconds spent on cross-encoder reranking (0 when reranked=false).
        - total_ms: wall-clock milliseconds for the full code_ask call.

        Args:
            question: Natural-language question about the codebase, e.g. "where does billing handle failed payments?"
        """
        bad = _ensure_no_extra_args("code_ask", kwargs)
        if bad is not None:
            return bad
        return code_ask_response(get_handler().index, get_handler().root, question)

    # --- Wave inspection ---

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_current(**kwargs: Any) -> dict[str, Any]:
        """Return the active wave ID, lifecycle status, and admitted changes.

        Prefer when: you need current working context (what wave am I on, what changes are admitted).
        Use wave_list_waves instead when discovering or browsing across all waves.
        """
        bad = _ensure_no_extra_args("wave_current", kwargs)
        if bad is not None:
            return bad
        return wave_current_response(get_handler().root, get_handler().cache)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_list_waves(limit: int = 50, **kwargs: Any) -> dict[str, Any]:
        """List all waves with their ID, status, and change count.

        Args:
            limit: Maximum waves to return (1–200, default 50). Check ``has_more`` for truncation.
        """
        bad = _ensure_no_extra_args("wave_list_waves", kwargs)
        if bad is not None:
            return bad
        return wave_list_waves_response(get_handler().root, limit=limit, cache=get_handler().cache)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_list_plans(limit: int = 50, **kwargs: Any) -> dict[str, Any]:
        """List pending plan/change docs in docs/plans that have not yet been admitted to a wave.

        Use this to answer "what changes are planned but not in a wave?" before reaching for ls or grep.

        Args:
            limit: Maximum plans to return (1–200, default 50). Check ``has_more`` for truncation.
        """
        bad = _ensure_no_extra_args("wave_list_plans", kwargs)
        if bad is not None:
            return bad
        return wave_list_plans_response(get_handler().root, limit=limit, cache=get_handler().cache)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_get_change(change_id: str = "", wave_id: str = "", **kwargs: Any) -> dict[str, Any]:
        """Return a change doc by ID, or all change docs for a wave in bulk.

        **Single lookup (default):** provide ``change_id`` to return one change doc.

        **Bulk mode:** provide ``wave_id`` without ``change_id`` to return all admitted
        change docs for that wave in ``data.changes``, each with ``id``, ``status``,
        ``path``, and ``content``. Content is capped at 300 lines per doc.

        Args:
            change_id: Change ID or prefix for single lookup, e.g. "12926" or "12926-feat".
                       Omit or leave empty to use bulk mode with wave_id.
            wave_id: Wave ID or prefix for bulk mode, e.g. "12ahv". Returns all
                     admitted changes for this wave when change_id is not provided.
        """
        bad = _ensure_no_extra_args("wave_get_change", kwargs)
        if bad is not None:
            return bad
        return wave_get_change_response(get_handler().root, change_id=change_id, wave_id=wave_id)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_get_prompt(shortcut: str, **kwargs: Any) -> dict[str, Any]:
        """Return the full rendered prompt for a Wave Framework shortcut phrase.

        Args:
            shortcut: Shortcut phrase, e.g. "Prepare wave" or "Plan feature".
        """
        bad = _ensure_no_extra_args("wave_get_prompt", kwargs)
        if bad is not None:
            return bad
        return wave_get_prompt_response(get_handler().root, shortcut, get_handler().cache)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_get_handoff(**kwargs: Any) -> dict[str, Any]:
        """Read the session handoff document (docs/agents/session-handoff.md).

        Returns the document content and last-modified timestamp.
        Returns a structured not-found response when the file is absent.
        """
        bad = _ensure_no_extra_args("wave_get_handoff", kwargs)
        if bad is not None:
            return bad
        return wave_get_handoff_response(get_handler().root)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_set_handoff(content: str, **kwargs: Any) -> dict[str, Any]:
        """Write the session handoff document (docs/agents/session-handoff.md).

        Creates or overwrites docs/agents/session-handoff.md with the provided content.
        Triggers a background docs-index refresh after writing.

        Args:
            content: Full markdown content to write as the new handoff document.
        """
        bad = _ensure_no_extra_args("wave_set_handoff", kwargs)
        if bad is not None:
            return bad
        return wave_set_handoff_response(get_handler().root, content, cache=get_handler().cache)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_gate_open(gate: str, **kwargs: Any) -> dict[str, Any]:
        """Open an edit gate in .wavefoundry/guard-overrides.json.

        Sets the named guard to enabled so framework or seed edits are permitted.
        Returns an error if the gate is already open — close it first to avoid
        silent double-opens (which indicate a bug or forgotten close).

        Every open must be paired with a matching wave_gate_close call.
        wave_pause and wave_close automatically close all open gates.

        Args:
            gate: Gate to open. One of: ``seed_edit_allowed``, ``framework_edit_allowed``,
                  ``design_system_edit_allowed``.
        """
        bad = _ensure_no_extra_args("wave_gate_open", kwargs)
        if bad is not None:
            return bad
        return wave_open_gate_response(get_handler().root, gate)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_gate_close(gate: str, **kwargs: Any) -> dict[str, Any]:
        """Close an edit gate in .wavefoundry/guard-overrides.json.

        Sets the named guard to disabled. Returns an advisory diagnostic (not an
        error) if the gate was already closed — double-close is harmless.

        Args:
            gate: Gate to close. One of: ``seed_edit_allowed``, ``framework_edit_allowed``,
                  ``design_system_edit_allowed``.
        """
        bad = _ensure_no_extra_args("wave_gate_close", kwargs)
        if bad is not None:
            return bad
        return wave_close_gate_response(get_handler().root, gate)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_gate_status(**kwargs: Any) -> dict[str, Any]:
        """Return the current enabled/disabled state of all edit gates.

        Use to inspect which gates exist and whether each is currently open or closed.
        A gate with enabled=true is open; enabled=false is closed.

        No arguments required.
        """
        bad = _ensure_no_extra_args("wave_gate_status", kwargs)
        if bad is not None:
            return bad
        return wave_gate_status_response(get_handler().root)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_map(address: str, **kwargs: Any) -> dict[str, Any]:
        """Resolve a doc:/code:/seed: anchor to repo path, trust label, excerpt, and index match flag.

        Prefer when: navigating from a search result anchor to the actual file, or verifying that a reference is indexed.
        Anchors appear in result_id fields returned by docs_search and code_search.

        Args:
            address: Stable anchor from search results, e.g. doc:docs/README.md#intro or code:src/a.py:L10-L20.
        """
        bad = _ensure_no_extra_args("wave_map", kwargs)
        if bad is not None:
            return bad
        return wave_map_response(get_handler().root, address, get_handler().index)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_create_wave(slug: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Create a wave record under docs/waves using a lifecycle wave ID.

        Args:
            slug: Kebab-case wave topic slug.
            mode: Either "dry_run" or "create".
        """
        bad = _ensure_no_extra_args("wave_create_wave", kwargs)
        if bad is not None:
            return bad
        return wave_create_wave_response(get_handler().root, slug, mode=mode, cache=get_handler().cache)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_add_change(wave_id: str, change_id: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Admit a change into a wave's Changes section.

        Args:
            wave_id: Wave ID or unique prefix.
            change_id: Change ID or unique prefix.
            mode: Either "dry_run" or "create".
        """
        bad = _ensure_no_extra_args("wave_add_change", kwargs)
        if bad is not None:
            return bad
        return wave_add_change_response(get_handler().root, wave_id, change_id, mode=mode, cache=get_handler().cache)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_remove_change(wave_id: str, change_id: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Remove an admitted change from a wave's Changes section.

        Args:
            wave_id: Wave ID or unique prefix.
            change_id: Change ID or unique prefix to remove.
            mode: Either "dry_run" or "create".
        """
        bad = _ensure_no_extra_args("wave_remove_change", kwargs)
        if bad is not None:
            return bad
        return wave_remove_change_response(get_handler().root, wave_id, change_id, mode=mode, cache=get_handler().cache)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_prepare(wave_id: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Transactional prepare check: validates docs and confirms wave has admitted changes.

        Call after all changes are admitted and docs validation passes — this is the required stage gate before implementation begins.

        Args:
            wave_id: Wave ID or unique prefix.
            mode: Either "dry_run" (validate only) or "create" (write Prepared checkpoint).
        """
        bad = _ensure_no_extra_args("wave_prepare", kwargs)
        if bad is not None:
            return bad
        return wave_prepare_response(get_handler().root, wave_id, mode=mode, cache=get_handler().cache)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_pause(wave_id: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Write or preview a session handoff entry for an active wave.

        Call at session end when work is incomplete and must resume in a later session.
        Captures current state so the next session can pick up without re-discovering context.

        Args:
            wave_id: Wave ID or unique prefix.
            mode: Either "dry_run" (preview only) or "create" (write handoff entry).
        """
        bad = _ensure_no_extra_args("wave_pause", kwargs)
        if bad is not None:
            return bad
        return wave_pause_response(get_handler().root, wave_id, mode=mode, cache=get_handler().cache)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_review(wave_id: str, phase: str = "implementation", **kwargs: Any) -> dict[str, Any]:
        """Run review readiness checks for a wave and return structured lane summary.

        Args:
            wave_id: Wave ID or unique prefix.
            phase: Review phase. "prepare" checks ## Prepare Review Evidence for prepare-phase
                lane signoffs (run before wave_implement). "implementation" (default) checks
                ## Review Evidence for implementation-phase signoffs (run before wave_close).
        """
        bad = _ensure_no_extra_args("wave_review", kwargs)
        if bad is not None:
            return bad
        return wave_review_response(get_handler().root, wave_id, phase=phase)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_implement(wave_id: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Gate and context builder for starting wave implementation.

        Verifies that both the prepare-phase Wave Council verdict and the prepare-phase
        lane review are complete before implementation begins. On create mode, transitions
        the wave status to 'implementing' and returns the ordered change list, Journal
        Watchpoints, and serialization points.

        Args:
            wave_id: Wave ID or unique prefix.
            mode: Either "dry_run" (validate readiness only, no writes) or "create"
                (alias "apply") to transition wave status to implementing.
        """
        bad = _ensure_no_extra_args("wave_implement", kwargs)
        if bad is not None:
            return bad
        return wave_implement_response(get_handler().root, wave_id, mode=mode, cache=get_handler().cache)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_reopen(wave_id: str, **kwargs: Any) -> dict[str, Any]:
        """Reopen a closed wave, restoring it to active status.

        Only works on waves with status 'closed'. Removes any Completed At stamp
        and sets Status back to active.

        Args:
            wave_id: Wave ID or unique prefix.
        """
        bad = _ensure_no_extra_args("wave_reopen", kwargs)
        if bad is not None:
            return bad
        return wave_reopen_response(get_handler().root, wave_id)

    @mcp.tool(annotations=_DESTRUCTIVE_TOOL)
    def wave_close(wave_id: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Dry-run or close a wave after validation passes.

        Args:
            wave_id: Wave ID or unique prefix.
            mode: Valid values are "dry_run" (validate only, no writes) or "create"
                (alias "apply") to write the Closed status checkpoint. Passing any
                other value returns an error with a "valid_modes" field in the response
                data listing the accepted values.
        """
        bad = _ensure_no_extra_args("wave_close", kwargs)
        if bad is not None:
            return bad
        return wave_close_response(get_handler().root, wave_id, mode=mode, cache=get_handler().cache)

    # --- Change creation ---

    def _new_change_response(kind: str, slug: str) -> dict[str, Any]:
        return _change_create_response(get_handler().root, kind, slug, mode="create", cache=get_handler().cache)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_new_feature(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded feature change doc (kind=feat). Returns the ID and path.

        Use for: net-new capability with user-visible behavior that did not exist before.

        Args:
            slug: Kebab-case slug, e.g. "my-new-feature".
        """
        bad = _ensure_no_extra_args("wave_new_feature", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("feat", slug)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_new_bug(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded bug change doc (kind=bug). Returns the ID and path.

        Use for: fixing a defect in existing behavior (something that worked and is now broken, or never worked as intended).

        Args:
            slug: Kebab-case slug, e.g. "login-redirect-broken".
        """
        bad = _ensure_no_extra_args("wave_new_bug", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("bug", slug)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_new_enhancement(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded enhancement change doc (kind=enh). Returns the ID and path.

        Use for: improving or extending existing functionality (making something that works better or more capable).

        Args:
            slug: Kebab-case slug, e.g. "improve-search-ranking".
        """
        bad = _ensure_no_extra_args("wave_new_enhancement", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("enh", slug)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_new_refactor(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded refactor change doc (kind=ref). Returns the ID and path.

        Use for: code structure changes with no user-visible behavior change (rename, extract, reorganize).

        Args:
            slug: Kebab-case slug, e.g. "extract-auth-module".
        """
        bad = _ensure_no_extra_args("wave_new_refactor", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("ref", slug)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_new_change(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded general change doc (kind=change). Returns the ID and path.

        Use for: changes that don't fit a more specific kind. Prefer feat, bug, enh, ref, doc, debt, task, maint, or ops first.

        Args:
            slug: Kebab-case slug, e.g. "update-release-process".
        """
        bad = _ensure_no_extra_args("wave_new_change", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("change", slug)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_new_documentation(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded documentation change doc (kind=doc). Returns the ID and path.

        Use for: docs-only changes — new or updated docs, specs, seeds, or prompts with no code changes.

        Args:
            slug: Kebab-case slug, e.g. "document-install-flow".
        """
        bad = _ensure_no_extra_args("wave_new_documentation", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("doc", slug)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_new_tech_debt(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded technical debt change doc (kind=debt). Returns the ID and path.

        Use for: cleanup of known technical debt — removing workarounds, paying down accumulated shortcuts.

        Args:
            slug: Kebab-case slug, e.g. "reduce-indexer-coupling".
        """
        bad = _ensure_no_extra_args("wave_new_tech_debt", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("debt", slug)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_new_task(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded task change doc (kind=task). Returns the ID and path.

        Use for: one-off tasks with no ongoing code artifact (e.g. fixture refresh, data migration, one-time audit).

        Args:
            slug: Kebab-case slug, e.g. "refresh-fixtures".
        """
        bad = _ensure_no_extra_args("wave_new_task", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("task", slug)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_new_maintenance(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded maintenance change doc (kind=maint). Returns the ID and path.

        Use for: routine upkeep with no new behavior — rotating generated surfaces, version bumps, dependency updates.

        Args:
            slug: Kebab-case slug, e.g. "rotate-generated-surfaces".
        """
        bad = _ensure_no_extra_args("wave_new_maintenance", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("maint", slug)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_new_operations(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded operations change doc (kind=ops). Returns the ID and path.

        Use for: operational or process changes — release checklists, runbooks, deployment procedures.

        Args:
            slug: Kebab-case slug, e.g. "update-release-checklist".
        """
        bad = _ensure_no_extra_args("wave_new_operations", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("ops", slug)

    # --- Framework operations ---

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_index_health(**kwargs: Any) -> dict[str, Any]:
        """Check the semantic index health for each layer (project + framework).

        Returns per-layer ``readiness`` (``missing`` / ``stale`` / ``current`` / ``idle``),
        aggregate ``readiness_overview`` (``incomplete`` / ``needs_update`` / ``degraded`` /
        ``absent`` / ``ready``), ``compatible_chunks``, ``stale_layers``, ``missing_layers``,
        and ``semantic_ready``. Use this to diagnose index issues explicitly rather than
        inferring them from degraded docs_search results.

        If ``readiness_overview`` is not ``ready``, call ``wave_index_build`` to rebuild
        the missing or stale layer (e.g. ``wave_index_build(content='docs', mode='update')``).
        """
        bad = _ensure_no_extra_args("wave_index_health", kwargs)
        if bad is not None:
            return bad
        return wave_index_health_response(get_handler().index)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_audit(wave_id: str = "", **kwargs: Any) -> dict[str, Any]:
        """Aggregate read-only audit: wave state + docs validation + index health.

        Returns ``data.ready`` (``true`` only when wave is active/planned, docs-lint
        passes, and ``semantic_ready`` is ``true``), plus three sub-objects:
        ``wave`` (current wave record), ``validation`` (lint pass/fail + errors),
        and ``index`` (semantic index health summary).

        Use this as the preferred landing tool after any mutation or uncertainty.
        When any sub-check fails, ``next_tools`` lists the specific recovery tool
        to call (``wave_validate``, ``wave_index_build``, or ``wave_current``).

        Args:
            wave_id: Optional wave ID prefix to audit a specific wave. Defaults to
                the currently active or planned wave.
        """
        bad = _ensure_no_extra_args("wave_audit", kwargs)
        if bad is not None:
            return bad
        return wave_audit_response(get_handler().root, wave_id=wave_id, index=get_handler().index, cache=get_handler().cache)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_index_build(content: str = "docs", mode: str = "update", layer: str = "project", **kwargs: Any) -> dict[str, Any]:
        """Run a synchronous semantic index **build** for the current repo root.

        Use ``mode='update'`` (default) for an incremental hash-based refresh of changed files.
        Use ``mode='rebuild'`` to force a full rebuild of the selected ``content`` for ``layer``.
        Successful responses include ``mode``, ``index_scope``, and runtime ``stats``.

        Args:
            content: One of `docs`, `code`, or `all`.
            mode: `update` (incremental) or `rebuild` (full).
            layer: `project` for the repo-local index or `framework` for packaged framework docs/seeds.
        """
        bad = _ensure_no_extra_args("wave_index_build", kwargs)
        if bad is not None:
            return bad
        return wave_index_build_response(get_handler().root, content=content, mode=mode, layer=layer, cache=get_handler().cache)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_index_build_status(layer: str = "project", **kwargs: Any) -> dict[str, Any]:
        """Check the status of a background index build.

        Returns state: 'running' (with pid, elapsed, progress), 'finished' (with
        elapsed time and file/chunk summary), or 'idle' (no build has been run).
        Safe to call at any time — read-only, no side effects. Suitable for /loop polling.

        Args:
            layer: `project` (default) or `framework`.
        """
        bad = _ensure_no_extra_args("wave_index_build_status", kwargs)
        if bad is not None:
            return bad
        return wave_index_build_status_response(get_handler().root, layer=layer)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_dashboard_start(**kwargs: Any) -> dict[str, Any]:
        """Start the local dashboard server and open it in the browser.

        If the dashboard is already running, returns its URL immediately without
        spawning a second process. Otherwise spawns the server in the background,
        waits up to 5 seconds for it to bind, and returns the URL.

        The dashboard provides a live web UI for wave status, index health, git
        activity, and (when ``auto_index`` is enabled) automatic index rebuilds.

        When the dashboard is already running, the response includes
        ``next_tools: ["wave_dashboard_open"]`` — call that tool to open the
        browser without restarting the server.
        """
        bad = _ensure_no_extra_args("wave_dashboard_start", kwargs)
        if bad is not None:
            return bad
        return wave_dashboard_start_response(get_handler().root)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_dashboard_open(**kwargs: Any) -> dict[str, Any]:
        """Open the browser to the local dashboard.

        If the dashboard is already running, opens the browser to its URL and
        returns ``{"opened": True, "url": <url>}``.

        If the dashboard is not running, starts it (equivalent to
        ``wave_dashboard_start``) and returns the start response — the server
        spawns with ``--open`` so the browser opens at startup.

        Use this tool when the user says "open the dashboard", "show me the
        dashboard in the browser", or when ``wave_dashboard_start`` returns
        ``already_running: True`` and you want to open the browser.
        """
        bad = _ensure_no_extra_args("wave_dashboard_open", kwargs)
        if bad is not None:
            return bad
        return wave_dashboard_open_response(get_handler().root)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_dashboard_stop(**kwargs: Any) -> dict[str, Any]:
        """Stop the local dashboard server for this repository.

        The command targets the dashboard process recorded for the current
        repository only, so dashboards in other repositories are unaffected.
        If the dashboard is already stopped, the command reports that state and
        clears stale repo-local metadata when present.
        """
        bad = _ensure_no_extra_args("wave_dashboard_stop", kwargs)
        if bad is not None:
            return bad
        return wave_dashboard_stop_response(get_handler().root)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_dashboard_restart(**kwargs: Any) -> dict[str, Any]:
        """Restart the local dashboard server for this repository.

        The command stops the current repository dashboard, then starts a new
        one with the same repo root and browser-open behavior.
        """
        bad = _ensure_no_extra_args("wave_dashboard_restart", kwargs)
        if bad is not None:
            return bad
        return wave_dashboard_restart_response(get_handler().root)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_upgrade(phase: str = "preflight_to_docs_gate", **kwargs: Any) -> dict[str, Any]:
        """Run the automated Wavefoundry framework upgrade script.

        Invokes ``upgrade_wavefoundry.py`` for the requested phase. Always runs
        non-interactively (equivalent to ``upgrade-wavefoundry --yes``).

        Args:
            phase: Which upgrade phase to run.

              - ``"preflight_to_docs_gate"`` *(default)* — phases 0–3: pre-flight
                checks, zip adoption, surface rendering, pruning, docs gate.
                Run this first. The agent's editing pass (drift detection, journal
                reconciliation, spec gap remediation) follows after this completes.
              - ``"update_index"`` — phase 4 *(default post-editing choice)*:
                incremental docs index update (blocking) then code (background).
                Re-embeds only files that changed since the last run.
                Auto-escalates to a full rebuild when chunker or embedding model
                version changed. Use this for normal post-editing-pass runs.
              - ``"rebuild_index"`` — phase 4 (full): re-embeds every file from
                scratch. Use when ``update_index`` is insufficient — e.g. index
                corruption or a manual forced refresh.
              - ``"cleanup"`` — phase 5: remove the upgrade lock file and print the
                operator summary. Call after ``update_index`` or ``rebuild_index``.

        Response fields:
          - ``exit_code``: 0 = success, 1 = docs gate failed, 2 = surface rendering
            failed, 3 = pre-flight check failed (downgrade detected, lock conflict).
          - ``output``: combined stdout + stderr from the upgrade script.
          - ``phase``: echoes the phase that was run.

        Upgrade sequence::

            wave_upgrade()                          # phases 0–3
            # … agent editing pass …
            wave_upgrade(phase="update_index")      # phase 4 — incremental (default)
            wave_upgrade(phase="cleanup")           # phase 5

        Use ``wave_upgrade_status`` to check lock state at any time.
        """
        bad = _ensure_no_extra_args("wave_upgrade", kwargs)
        if bad is not None:
            return bad
        return wave_upgrade_response(get_handler().root, phase=phase)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_upgrade_status(**kwargs: Any) -> dict[str, Any]:
        """Return the current upgrade lock state.

        Reads ``.wavefoundry/upgrade-in-progress.json`` and reports whether a
        framework upgrade is currently in progress.

        Response fields:
          - ``in_progress`` (bool): True if the upgrade lock file exists and the
            recorded PID is still running.
          - ``started_at`` (str | null): ISO-8601 timestamp when the upgrade started.
          - ``from_version`` (str | null): Framework revision being upgraded from.
          - ``to_version`` (str | null): Pack version being upgraded to.
          - ``pid`` (int | null): PID of the upgrade process.

        Use before calling ``wave_dashboard_restart`` to confirm whether a restart
        is safe, or to confirm the lock was removed after ``upgrade-wavefoundry --cleanup``.
        """
        bad = _ensure_no_extra_args("wave_upgrade_status", kwargs)
        if bad is not None:
            return bad
        return wave_upgrade_status_response(get_handler().root)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_validate(**kwargs: Any) -> dict[str, Any]:
        """Run docs_lint against the project. Returns structured pass/fail with errors.

        Use for targeted lint-only checks. Prefer wave_audit for a combined wave state + lint + index health snapshot.
        """
        bad = _ensure_no_extra_args("wave_validate", kwargs)
        if bad is not None:
            return bad
        return wave_validate_response(get_handler().root)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_run_sensors(**kwargs: Any) -> dict[str, Any]:
        """Run all computational sensors declared in workflow-config.json and return structured results.

        Sensors are defined as: {"name": "...", "command": [...], "dimension": "maintainability|architecture|behaviour", "description": "..."}.
        Each sensor runs as a subprocess; pass/fail is determined by exit code.
        Returns per-sensor results and an overall all_passed flag.
        Use wave_audit to declare sensors in workflow-config.json if none are configured.
        """
        bad = _ensure_no_extra_args("wave_run_sensors", kwargs)
        if bad is not None:
            return bad
        return wave_run_sensors_response(get_handler().root)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_garden(mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Run docs_gardener to update Last verified dates. Returns summary.

        Args:
            mode: Either "dry_run" (preview, no writes) or "run" (execute gardener).
        """
        bad = _ensure_no_extra_args("wave_garden", kwargs)
        if bad is not None:
            return bad
        return wave_garden_response(get_handler().root, mode=mode, cache=get_handler().cache)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_sync_surfaces(mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Run render_platform_surfaces to regenerate .claude/, .cursor/ hook configs.

        Args:
            mode: Either "dry_run" (preview, no writes) or "run" (execute renderer).
        """
        bad = _ensure_no_extra_args("wave_sync_surfaces", kwargs)
        if bad is not None:
            return bad
        return wave_sync_surfaces_response(get_handler().root, mode=mode, cache=get_handler().cache)

    # --- Code navigation tools ---

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_list_files(glob: str = "", **kwargs: Any) -> dict[str, Any]:
        """List repository-relative file paths, optionally filtered by a glob pattern.

        Respects the same ignore/exclusion rules as the semantic index (gitignore,
        aiignore, hardcoded excludes for .git, caches, binaries, generated indexes).

        Args:
            glob: Optional glob pattern to filter results, e.g. "**/*.py" or "*.md".
                  Matches against full repo-relative paths and file names.
        """
        bad = _ensure_no_extra_args("code_list_files", kwargs)
        if bad is not None:
            return bad
        return code_list_files_response(get_handler().root, glob=glob)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_read(path: str, start_line: Optional[int] = None, end_line: Optional[int] = None, **kwargs: Any) -> dict[str, Any]:
        """Read a file at a repo-relative path, returning line-numbered content.

        Rejects absolute paths and paths that escape the repository root.
        Use code_list_files to discover valid paths.

        Args:
            path: Repo-relative path to the file, e.g. "src/main.py".
            start_line: First line to include (1-indexed, inclusive). Defaults to 1.
            end_line: Last line to include (1-indexed, inclusive). Defaults to end of file.
        """
        bad = _ensure_no_extra_args("code_read", kwargs)
        if bad is not None:
            return bad
        return code_read_response(get_handler().root, path, start_line=start_line, end_line=end_line)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_keyword(
        query: str = "",
        glob: str = "",
        queries: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Search repository files for an exact keyword or substring.

        Prefer code_definition first when the goal is to find where a specific symbol, CSS class, or
        custom property is *declared* — it returns a precise definition location without scanning all occurrences.
        Use code_keyword when you need all occurrences of a token, or when code_definition returns no results.
        Use docs_search or code_search instead when searching by concept or intent rather than exact text.
        Use code_pattern when you need regex (non-literal) matching.
        Returns deterministic path/line/snippet results for each match.
        Respects the same ignore/exclusion rules as the semantic index.

        Pass either ``query`` (single string) or ``queries`` (list of strings) — not both. When
        ``queries`` is supplied, results from all entries are merged and deduplicated by (path, line);
        each result includes ``matched_query`` identifying which query string produced it. The ``glob``
        parameter applies uniformly across all queries in a batch.

        Args:
            query: Exact text to search for (substring match). Omit when using ``queries``.
            glob: Optional glob to restrict the search, e.g. "**/*.py" or "*.md".
            queries: List of exact strings to search for in a single call. Omit when using ``query``.
        """
        bad = _ensure_no_extra_args("code_keyword", kwargs)
        if bad is not None:
            return bad
        return code_keyword_response(get_handler().root, query, glob=glob, queries=queries)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_constants(symbols: list[str], glob: str = "", **kwargs: Any) -> dict[str, Any]:
        """Look up current values of named module-level constants in one call.

        Prefer when: you need the current value of one or more named constants
        (e.g. VECTOR_TOP_K, MAX_SYMBOLS_EXTRACTED) without manually parsing
        grep output. Returns structured name/value/file/line/kind per match.
        Use code_keyword when searching for arbitrary substrings rather than
        constant assignments specifically.

        Scans for unindented assignments of the form ``NAME = <value>`` or
        ``NAME: TYPE = <value>``. Multiline values (frozenset, list, dict
        literals) are collected until the bracket depth closes. A value that
        does not close within 50 continuation lines is returned with
        kind="multiline-truncated".

        Symbols not found in the codebase are included in the result with
        value=null so callers can verify every lookup was attempted. When a
        symbol appears in multiple files, all matches are returned — use the
        glob parameter to scope to a specific file.

        Response fields per result entry:
        - name: the requested symbol name
        - value: right-hand-side of the assignment as a raw string, or null if not found
        - file: repo-relative path, or null if not found
        - line: 1-based line number, or null if not found
        - kind: "scalar" | "multiline" | "multiline-truncated" | null

        Args:
            symbols: List of constant names to look up, e.g. ["VECTOR_TOP_K", "RRF_K"].
            glob: Optional glob to restrict search, e.g. "**/server.py" or "**/*.py".
        """
        bad = _ensure_no_extra_args("code_constants", kwargs)
        if bad is not None:
            return bad
        return code_constants_response(get_handler().root, symbols, glob=glob)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_pattern(
        pattern: str,
        glob: str = "",
        max_results: int = 50,
        ignore_case: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Search repository files using a Python regex pattern.

        Prefer when: you need structured pattern matching (e.g. ``def .*search``,
        ``TODO:.*urgent``) rather than exact substring matching. Use code_keyword
        for literal exact-text matches — it is faster and simpler. Use code_search
        when searching by concept or intent rather than a specific pattern.

        Invalid patterns return a structured error (not an exception trace). Files
        larger than 1 MB are skipped to guard against ReDoS latency.

        Response fields:
        - matches: list of {file, line, text} — file is repo-relative, line is 1-based
        - truncated: true when the result cap was reached before all files were scanned
        - total_matches_found: actual match count found (may exceed max_results when truncated)

        Args:
            pattern: Python ``re``-compatible regex string.
            glob: Optional glob to restrict search, e.g. "**/*.py" or "src/**".
            max_results: Maximum number of matches to return (default 50).
            ignore_case: Apply re.IGNORECASE when True.
        """
        bad = _ensure_no_extra_args("code_pattern", kwargs)
        if bad is not None:
            return bad
        return code_pattern_response(get_handler().root, pattern, glob=glob,
                                     max_results=max_results, ignore_case=ignore_case)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_outline(path: str, **kwargs: Any) -> dict[str, Any]:
        """Return a structural symbol map of a source file.

        Prefer when: you need to understand the shape of an unfamiliar file —
        what functions, classes, methods, and constants it defines — without
        reading the full implementation. Use code_read once you know which
        symbol to inspect. Use code_definition when you know the symbol name
        but not which file contains it.

        Parsing is tiered for maximum accuracy:
        - Python (.py): stdlib AST — functions, classes, methods, module-level constants
        - JS/TS/Java/C#/Go/Rust/C/C++/Kotlin/Bash/SQL: tree-sitter-backed
        - All other file types: regex fallback (end_line and docstring are null)

        Response fields:
        - file: repo-relative path
        - parser_used: "python_ast" | "tree_sitter" | "regex"
        - symbols: list of {name, kind, start_line, end_line, docstring}
          - kind: "function" | "class" | "method" | "constant"
          - end_line: null for regex tier
          - docstring: first docstring line, or null

        Args:
            path: Repo-relative path to the file, e.g. "src/server.py".
        """
        bad = _ensure_no_extra_args("code_outline", kwargs)
        if bad is not None:
            return bad
        return code_outline_response(get_handler().root, path)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_definition(symbol_or_path_position: str, **kwargs: Any) -> dict[str, Any]:
        """Find definition(s) for a symbol name across Python and supported non-Python languages.

        Prefer when: looking up where a function, class, interface, enum, or similar symbol is defined.
        Python uses AST-based lookup. Java, C#, JavaScript, and TypeScript use tree-sitter-backed navigation
        when parser support is available. Other supported non-Python languages use structural regex matchers.
        If no structural definition is found, the response includes a broad code_keyword-style fallback.

        Supported languages:
        - Python: AST-based function/class/async-function definitions
        - JavaScript/TypeScript/Java/C#: tree-sitter-backed structural definitions when available
        - Go/Rust/Kotlin/Swift: regex-based structural definitions
        - CSS/SCSS: class selectors, ID selectors, custom properties (--var), @keyframes, @mixin/@function

        Args:
            symbol_or_path_position: Symbol name to look up (e.g. "MyClass", "process_wave",
                                     "agent-dialog-header", "--brand-color", "fade-in").
                                     Exact or partial match against supported symbol names.
        """
        bad = _ensure_no_extra_args("code_definition", kwargs)
        if bad is not None:
            return bad
        return code_definition_response(get_handler().root, symbol_or_path_position)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_references(
        symbol_or_path_position: str,
        exclude_tests: bool = False,
        exclude_docs: bool = False,
        call_sites_only: bool = False,
        limit: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Find references to a symbol across known code languages via text matching.

        Prefer when: tracing call sites for a known symbol more directly than broad code_keyword.
        Python uses AST-backed call-site detection plus text fallback for broader mentions. Java, C#, JavaScript,
        and TypeScript use tree-sitter-backed identifier traversal when parser support is available. Other known
        code languages use language-aware text matching.
        If no known-language references are found, the response includes a broad keyword fallback.
        Optional filters can suppress test/doc hits or restrict the response to call sites only.
        Optional limit caps returned hits after ordering and filtering while preserving matched counts.

        Supported languages: all canonical code-search languages recognized by the navigation layer.

        Args:
            symbol_or_path_position: Symbol name to find references for (e.g. "wave_close_response").
                                     Text-based search in known code files.
            exclude_tests: When true, omit references classified as tests.
            exclude_docs: When true, omit references classified as docs.
            call_sites_only: When true, omit all non-call-site references.
            limit: Optional cap on the number of hits returned. Use 0 to keep all hits.
        """
        bad = _ensure_no_extra_args("code_references", kwargs)
        if bad is not None:
            return bad
        return code_references_response(
            root,
            symbol_or_path_position,
            exclude_tests=exclude_tests,
            exclude_docs=exclude_docs,
            call_sites_only=call_sites_only,
            limit=limit if limit and limit > 0 else None,
        )

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_callhierarchy(
        symbol: str,
        file: str = "",
        direction: str = "both",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Return the call hierarchy for a symbol: what it calls (outgoing) and what calls it (incoming).

        Prefer when: tracing execution paths, understanding a function's callers and callees,
        or planning a refactor that affects a specific symbol. Depth is always 1 — direct callers
        and callees only. Chain calls for transitive analysis.

        Response fields:
        - symbol: the queried symbol name
        - definition_file: path of the file where the symbol is defined (null if not found)
        - outgoing: list of {name, file, line} — symbols called by this symbol (when direction includes "outgoing")
        - incoming: list of {name, file, line, snippet} — symbols that call this symbol (when direction includes "incoming")
        - parser_used: method used for definition lookup

        Args:
            symbol: Symbol name to query (e.g. "process_payment", "UserService").
            file: Optional repo-relative file path to disambiguate when the symbol appears in multiple files.
            direction: "both" (default), "outgoing" (callee direction only), or "incoming" (caller direction only).
        """
        bad = _ensure_no_extra_args("code_callhierarchy", kwargs)
        if bad is not None:
            return bad
        return code_callhierarchy_response(get_handler().root, symbol, file or None, direction)

    # --- Read-only MCP Resources ---
    # These expose stable context as MCP resources rather than tool calls.
    # Agents should prefer resources for read-only context discovery and
    # fall back to the equivalent tools when they need structured envelopes.

    def _read_doc_or_not_found(path: Path, label: str) -> str:
        """Read a markdown doc and return its text, or a clear not-found message."""
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f"# Not Found\n\n`{label}` does not exist at `{_repo_rel(get_handler().root, path)}`.\n"

    @mcp.resource(
        "wavefoundry://overview",
        name="project_overview",
        description="Project overview and orientation doc (docs/references/project-overview.md).",
        mime_type="text/markdown",
    )
    def resource_project_overview() -> str:
        """Return the project overview document."""
        _root = get_handler().root
        candidates = [
            _root / "docs" / "references" / "project-overview.md",
            _root / "docs" / "README.md",
            _root / "README.md",
        ]
        for c in candidates:
            if c.exists():
                return c.read_text(encoding="utf-8")
        return "# Not Found\n\nNo project overview document found in docs/references/project-overview.md or docs/README.md.\n"

    @mcp.resource(
        "wavefoundry://prompts",
        name="prompt_index",
        description="Public agent command catalogue (docs/prompts/index.md).",
        mime_type="text/markdown",
    )
    def resource_prompt_index() -> str:
        """Return the prompt/command index."""
        return _read_doc_or_not_found(get_handler().root / "docs" / "prompts" / "index.md", "docs/prompts/index.md")

    @mcp.resource(
        "wavefoundry://architecture/current-state",
        name="architecture_current_state",
        description="Architecture current-state summary (docs/architecture/current-state.md).",
        mime_type="text/markdown",
    )
    def resource_architecture_current_state() -> str:
        """Return the architecture current-state document."""
        return _read_doc_or_not_found(get_handler().root / "docs" / "architecture" / "current-state.md", "docs/architecture/current-state.md")

    @mcp.resource(
        "wavefoundry://wave/current",
        name="current_wave",
        description="Current active wave record. Equivalent to calling wave_current() but returned as markdown text.",
        mime_type="text/markdown",
    )
    def resource_current_wave() -> str:
        """Return the current active wave.md as markdown text."""
        wave_info = current_wave(get_handler().root, cache=get_handler().cache)
        if wave_info is None:
            return "# No Active Wave\n\nNo active wave found. Use `wave_create_wave` to start one.\n"
        wave_path = get_handler().root / wave_info["path"]
        if wave_path.exists():
            return wave_path.read_text(encoding="utf-8")
        return f"# Wave Not Found\n\nWave record path `{wave_info['path']}` does not exist on disk.\n"

    @mcp.resource(
        "wavefoundry://session-handoff",
        name="session_handoff",
        description="Current session handoff state (docs/agents/session-handoff.md).",
        mime_type="text/markdown",
    )
    def resource_session_handoff() -> str:
        """Return the session handoff document."""
        return _read_doc_or_not_found(get_handler().root / "docs" / "agents" / "session-handoff.md", "docs/agents/session-handoff.md")

    # --- Read-only MCP Resource Templates ---
    # Parameterized reads for change docs, waves, prompts, seeds, and architecture docs.

    @mcp.resource(
        "wavefoundry://change/{change_id}",
        name="change_doc",
        description="Read a change doc by ID or prefix. Returns the raw markdown content.",
        mime_type="text/markdown",
    )
    def resource_change(change_id: str) -> str:
        """Return the change doc matching the given ID or prefix."""
        text = get_change(get_handler().root, change_id)
        if text is None:
            return f"# Not Found\n\nNo change doc found matching `{change_id}`. Use `wave_get_change(change_id=...)` for structured lookup.\n"
        return text

    @mcp.resource(
        "wavefoundry://wave/{wave_id}",
        name="wave_doc",
        description="Read a wave record (wave.md) by ID or prefix. Returns the raw markdown content.",
        mime_type="text/markdown",
    )
    def resource_wave(wave_id: str) -> str:
        """Return the wave.md for the given wave ID or prefix."""
        wave_md = _find_wave_md(get_handler().root, wave_id)
        if wave_md is None:
            return f"# Not Found\n\nNo wave found matching `{wave_id}`. Use `wave_list_waves()` to see available waves.\n"
        return wave_md.read_text(encoding="utf-8")

    @mcp.resource(
        "wavefoundry://prompt/{slug}",
        name="prompt_doc",
        description="Read a prompt doc by slug or shortcut. Returns the raw markdown content.",
        mime_type="text/markdown",
    )
    def resource_prompt(slug: str) -> str:
        """Return the prompt document matching the given slug."""
        text = get_prompt(get_handler().root, slug)
        if text is None:
            return f"# Not Found\n\nNo prompt found matching `{slug}`. Use `wave_get_prompt(shortcut=...)` for structured lookup.\n"
        return text

    @mcp.resource(
        "wavefoundry://seed/{slug}",
        name="seed_doc",
        description="Read a seed doc by slug or name. Returns the raw markdown content.",
        mime_type="text/markdown",
    )
    def resource_seed(slug: str) -> str:
        """Return the seed document matching the given slug."""
        try:
            chunk = get_handler().index.get_seed(slug)
        except Exception:
            chunk = None
        if chunk is None:
            # Fall back to filesystem scan of framework seeds
            seeds_dir = get_handler().root / ".wavefoundry" / "framework" / "seeds"
            if seeds_dir.exists():
                slug_lower = slug.lower().strip()
                for p in sorted(seeds_dir.glob("*.md")):
                    if slug_lower in p.stem.lower():
                        return p.read_text(encoding="utf-8")
            return f"# Not Found\n\nNo seed found matching `{slug}`. Use `seed_get(name=...)` for structured lookup.\n"
        # chunk has a "path" and likely "text" or we read from path
        seed_path = get_handler().root / chunk["path"] if not str(chunk.get("path", "")).startswith("/") else Path(chunk["path"])
        if seed_path.exists():
            return seed_path.read_text(encoding="utf-8")
        return chunk.get("text", f"# Not Found\n\nSeed `{slug}` index entry exists but file not readable.\n")

    @mcp.resource(
        "wavefoundry://architecture/{slug}",
        name="architecture_doc",
        description="Read an architecture doc by slug (e.g. 'domain-map', 'data-and-control-flow'). Returns the raw markdown content.",
        mime_type="text/markdown",
    )
    def resource_architecture(slug: str) -> str:
        """Return the architecture document matching the given slug."""
        arch_dir = get_handler().root / "docs" / "architecture"
        if arch_dir.exists():
            slug_lower = slug.lower().strip()
            for p in sorted(arch_dir.glob("*.md")):
                if slug_lower in p.stem.lower():
                    return p.read_text(encoding="utf-8")
        return f"# Not Found\n\nNo architecture doc found matching `{slug}` in docs/architecture/.\n"

    tool_names = _registered_mcp_tool_names(mcp)
    violations = first_party_tool_names_violating_prefix(tool_names)
    if violations:
        raise RuntimeError(
            "MCP tool name prefix contract violated for: " + ", ".join(violations)
        )



# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wavefoundry MCP server (stdio transport)")
    parser.add_argument("--root", default=None, help="Repository root (default: auto-discover)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = _discover_root(args.root)
    mcp = build_server(get_handler().root)
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

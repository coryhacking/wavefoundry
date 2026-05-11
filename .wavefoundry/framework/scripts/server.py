#!/usr/bin/env python3
"""Wavefoundry MCP server — semantic index, wave inspection, and framework operations."""
from __future__ import annotations

import argparse
import contextlib
import datetime
import functools
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Literal, Optional

sys.dont_write_bytecode = True

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


class WaveIndex:
    """Loaded in-memory index for semantic search."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.index_dir = root / ".wavefoundry" / "index"
        self.framework_index_dir = root / ".wavefoundry" / "framework" / "index"
        self._docs_vecs: Optional["np.ndarray"] = None
        self._code_vecs: Optional["np.ndarray"] = None
        self._docs_chunks: list[dict] = []
        self._all_docs_chunks: list[dict] = []
        self._code_chunks: list[dict] = []
        self._docs_embedder = None
        self._code_embedder = None
        self._meta: dict = {}
        self._loaded = False
        self._loaded_built_at: dict[str, str] = {}  # layer -> built_at stamp when last loaded
        self._docs_tag_index: dict[str, list[int]] = {}
        self._code_tag_index: dict[str, list[int]] = {}
        self._docs_kind_index: dict[str, list[int]] = {}
        self._code_kind_index: dict[str, list[int]] = {}

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
        docs_json_path = index_dir / "docs.json"
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
        docs_present = docs_json_path.exists()
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
        compatible_chunks = bool(self._docs_chunks)
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
        prior = os.environ.get("HF_HUB_OFFLINE")
        os.environ["HF_HUB_OFFLINE"] = "1"
        try:
            yield
        finally:
            if prior is None:
                os.environ.pop("HF_HUB_OFFLINE", None)
            else:
                os.environ["HF_HUB_OFFLINE"] = prior

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

    def _index_built_at(self, index_dir: Path) -> str:
        meta_path = index_dir / "meta.json"
        try:
            return json.loads(meta_path.read_text(encoding="utf-8")).get("built_at", "")
        except (OSError, json.JSONDecodeError):
            return ""

    def _ensure_loaded(self) -> None:
        if self._loaded:
            # Invalidate if either index has been rebuilt since we last loaded.
            project_built_at = self._index_built_at(self.index_dir)
            framework_built_at = self._index_built_at(self.framework_index_dir)
            if (project_built_at != self._loaded_built_at.get("project", "")
                    or framework_built_at != self._loaded_built_at.get("framework", "")):
                self._loaded = False
        if self._loaded:
            return
        try:
            import numpy as np
        except ImportError:
            raise IndexNotReadyError(
                "numpy is not installed. Run: python3 .wavefoundry/framework/scripts/setup_index.py"
            )

        if not (self.index_dir / "meta.json").exists() and not (self.framework_index_dir / "meta.json").exists():
            raise IndexNotReadyError(
                f"Index not found at {self.index_dir} or {self.framework_index_dir}. "
                "Run: python3 .wavefoundry/framework/scripts/setup_index.py"
            )

        def _load(index_dir: Path, npy_name: str, json_name: str, path_prefix: str = "") -> tuple:
            npy_path = index_dir / npy_name
            json_path = index_dir / json_name
            try:
                vecs = np.load(str(npy_path)) if npy_path.exists() else None
            except Exception:
                vecs = None
            try:
                chunks = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else []
            except (json.JSONDecodeError, OSError):
                chunks = []
            if path_prefix:
                prefix = path_prefix.rstrip("/") + "/"
                chunks = [
                    {
                        **chunk,
                        "path": chunk.get("path", "")
                        if chunk.get("path", "").startswith(prefix)
                        else prefix + chunk.get("path", "").lstrip("/"),
                    }
                    for chunk in chunks
                ]
            return vecs, chunks

        def _load_meta(index_dir: Path) -> dict:
            meta_path = index_dir / "meta.json"
            if meta_path.exists():
                try:
                    return json.loads(meta_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    return {}
            return {}

        def _compatible_layer(
            vecs: Optional["np.ndarray"],
            chunks: list[dict],
            meta: dict,
            content_name: str,
            expected_model: str,
        ) -> tuple[Optional["np.ndarray"], list[dict]]:
            if vecs is None or not chunks:
                return None, []
            model_versions = meta.get("model_versions", {})
            if model_versions.get(content_name) != expected_model:
                return None, []
            if getattr(vecs, "ndim", 0) != 2 or vecs.shape[0] != len(chunks):
                return None, []
            return vecs, chunks

        def _merge_layers(layers: list[tuple[Optional["np.ndarray"], list[dict]]]) -> tuple[Optional["np.ndarray"], list[dict]]:
            valid_vecs = []
            valid_chunks: list[dict] = []
            dim = None
            for vecs, chunks in layers:
                if vecs is None or not chunks:
                    continue
                if dim is None:
                    dim = vecs.shape[1]
                elif vecs.shape[1] != dim:
                    continue
                valid_vecs.append(vecs)
                valid_chunks.extend(chunks)
            if not valid_vecs:
                return None, []
            if len(valid_vecs) == 1:
                return valid_vecs[0], valid_chunks
            return np.concatenate(valid_vecs, axis=0), valid_chunks

        project_docs_vecs, project_docs_chunks = _load(self.index_dir, "docs.npy", "docs.json")
        project_code_vecs, project_code_chunks = _load(self.index_dir, "code.npy", "code.json")
        project_meta = _load_meta(self.index_dir)
        framework_docs_vecs, framework_docs_chunks = _load(
            self.framework_index_dir,
            "docs.npy",
            "docs.json",
            ".wavefoundry/framework",
        )
        framework_code_vecs, framework_code_chunks = _load(
            self.framework_index_dir,
            "code.npy",
            "code.json",
            ".wavefoundry/framework",
        )
        framework_meta = _load_meta(self.framework_index_dir)

        DOCS_MODEL = self._indexer_constant("DOCS_MODEL")
        CODE_MODEL = self._indexer_constant("CODE_MODEL")
        project_docs_layer = _compatible_layer(
            project_docs_vecs, project_docs_chunks, project_meta, "docs", DOCS_MODEL
        )
        framework_docs_layer = _compatible_layer(
            framework_docs_vecs, framework_docs_chunks, framework_meta, "docs", DOCS_MODEL
        )
        project_code_layer = _compatible_layer(
            project_code_vecs, project_code_chunks, project_meta, "code", CODE_MODEL
        )
        framework_code_layer = _compatible_layer(
            framework_code_vecs, framework_code_chunks, framework_meta, "code", CODE_MODEL
        )

        self._docs_vecs, self._docs_chunks = _merge_layers([project_docs_layer, framework_docs_layer])
        self._code_vecs, self._code_chunks = _merge_layers([project_code_layer, framework_code_layer])
        self._all_docs_chunks = project_docs_chunks + framework_docs_chunks
        self._meta = {
            "project": project_meta,
            "framework": framework_meta,
        }
        self._loaded_built_at = {
            "project": project_meta.get("built_at", ""),
            "framework": framework_meta.get("built_at", ""),
        }
        docs_tag_index: dict[str, list[int]] = {}
        docs_kind_index: dict[str, list[int]] = {}
        for i, chunk in enumerate(self._docs_chunks):
            for tag in _infer_tags(chunk.get("path", "")):
                docs_tag_index.setdefault(tag, []).append(i)
            chunk_kind = str(chunk.get("kind") or "")
            docs_kind_index.setdefault(chunk_kind, []).append(i)
            if chunk_kind == "doc":
                p = str(chunk.get("path") or "").replace("\\", "/")
                if p == "docs/ARCHITECTURE.md" or p.startswith("docs/architecture/"):
                    docs_kind_index.setdefault("architecture", []).append(i)
        self._docs_tag_index = docs_tag_index
        self._docs_kind_index = docs_kind_index
        code_tag_index: dict[str, list[int]] = {}
        code_kind_index: dict[str, list[int]] = {}
        for i, chunk in enumerate(self._code_chunks):
            for tag in _infer_tags(chunk.get("path", "")):
                code_tag_index.setdefault(tag, []).append(i)
            chunk_kind = str(chunk.get("kind") or "")
            code_kind_index.setdefault(chunk_kind, []).append(i)
        self._code_tag_index = code_tag_index
        self._code_kind_index = code_kind_index
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
    #        python3 .wavefoundry/framework/scripts/setup_index.py --root . --include-code
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
                "fastembed is not installed. Run: python3 .wavefoundry/framework/scripts/setup_index.py"
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
                    "Run: python3 .wavefoundry/framework/scripts/setup_index.py --root ."
                ) from exc
        except Exception as exc:
            raise SemanticModelUnavailableOfflineError(
                f"Semantic query model '{model_name}' is unavailable offline. "
                "Run: python3 .wavefoundry/framework/scripts/setup_index.py --root ."
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
                "Run: python3 .wavefoundry/framework/scripts/setup_index.py --root ."
            ) from exc

    def _indexer_constant(self, name: str) -> str:
        mod = _load_script("indexer")
        return getattr(mod, name)

    def _cosine_search(
        self,
        query_vec: "np.ndarray",
        matrix: "np.ndarray",
        chunks: list[dict],
        top_n: int,
    ) -> list[dict]:
        import numpy as np
        if matrix is None or len(chunks) == 0:
            return []
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-10, norms)
        normed = matrix / norms
        q_norm = query_vec / (np.linalg.norm(query_vec) + 1e-10)
        scores = normed @ q_norm
        top_idx = np.argsort(scores)[::-1][:top_n]
        return [
            {**chunks[i], "score": float(scores[i])}
            for i in top_idx
            if scores[i] > 0
        ]

    def search_docs(self, query: str, kind: Optional[str] = None, top_n: int = 5, tags: Optional[list] = None) -> list[dict]:
        self._ensure_loaded()
        DOCS_MODEL = self._indexer_constant("DOCS_MODEL")
        qvec = self._embed_query(query, DOCS_MODEL)
        vecs, chunks = self._docs_vecs, self._docs_chunks
        if tags or kind:
            indices: set[int] = set(range(len(self._docs_chunks)))
            if tags:
                indices &= set().union(*(self._docs_tag_index.get(t, []) for t in tags))
            if kind:
                indices &= set(self._docs_kind_index.get(kind, []))
            sorted_indices = sorted(indices)
            if not sorted_indices:
                return []
            vecs = vecs[sorted_indices]
            chunks = [chunks[i] for i in sorted_indices]
        return self._cosine_search(qvec, vecs, chunks, top_n)

    def search_code(self, query: str, language: Optional[str] = None, top_n: int = 5, kind: Optional[str] = None, max_per_file: Optional[int] = None, tags: Optional[list] = None) -> list[dict]:
        self._ensure_loaded()
        CODE_MODEL = self._indexer_constant("CODE_MODEL")
        qvec = self._embed_query(query, CODE_MODEL)
        vecs, chunks = self._code_vecs, self._code_chunks
        if tags or kind:
            indices: set[int] = set(range(len(self._code_chunks)))
            if tags:
                indices &= set().union(*(self._code_tag_index.get(t, []) for t in tags))
            if kind:
                indices &= set(self._code_kind_index.get(kind, []))
            sorted_indices = sorted(indices)
            if not sorted_indices:
                return []
            vecs = vecs[sorted_indices]
            chunks = [chunks[i] for i in sorted_indices]
        n = top_n * 4 if language or max_per_file is not None else top_n
        results = self._cosine_search(qvec, vecs, chunks, n)
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
        return results[:top_n]

    def get_seed(self, name: str) -> Optional[dict]:
        self._ensure_loaded()
        name_lower = name.lower().strip()
        for chunk in self._all_docs_chunks:
            if chunk.get("kind") != "seed":
                continue
            path = chunk.get("path", "")
            section = chunk.get("section") or ""
            if name_lower in path.lower() or name_lower in section.lower():
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
_CHANGE_STATUS_PATTERN = re.compile(r"^Change Status:\s+`([^`]+)`", re.MULTILINE)
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
        if wave["status"] in ("active", "planned"):
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
        if wave["status"] != "active":
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
                "fallback_tools": ["code_keyword_search"],
                "next_step": "Run semantic code search. Omit language to search all languages, or use a category for broad filtering.",
                "usage": "code_search(query='handle authentication errors', language='web')",
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
        [sys.executable, str(script)],
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
        [sys.executable, str(script)],
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
        [sys.executable, str(script)],
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
    docs_path = index_dir / "docs.json"
    code_path = index_dir / "code.json"

    meta: dict[str, Any] = {}
    docs_chunks: list[Any] = []
    code_chunks: list[Any] = []

    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    if docs_path.is_file():
        try:
            docs_chunks = json.loads(docs_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            docs_chunks = []
    if code_path.is_file():
        try:
            code_chunks = json.loads(code_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            code_chunks = []

    return {
        "files_total": len(meta.get("file_meta") or meta.get("file_hashes") or {}),
        "doc_chunks": len(docs_chunks),
        "code_chunks": len(code_chunks),
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
        sys.executable, str(scripts_dir / "indexer.py"),
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


def _index_build_log_path(root: Path, layer: str) -> Path:
    if layer == "framework":
        return root / ".wavefoundry" / "framework" / "index" / "index-build.log"
    return root / ".wavefoundry" / "index" / "index-build.log"


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

    if layer == "project" and content == "all":
        script = scripts_dir / "setup_index.py"
        cmd = [sys.executable, str(script), "--root", str(root), "--include-code", "--verbose"]
    else:
        script = scripts_dir / "indexer.py"
        cmd = [sys.executable, str(script), "--root", str(root), "--content", content, "--verbose"]
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
            "env": {**os.environ, "PROJECT_ROOT": str(root)},
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(cmd, **kwargs)
    finally:
        log_file.close()

    state_path = _index_build_state_path(root, layer)
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


def docs_search_response(index: WaveIndex, query: str, kind: str = "", limit: int = 5, tags: Optional[list] = None) -> dict[str, Any]:
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
    try:
        # Attempt semantic search; exception handlers below switch to lexical fallback.
        results = index.search_docs(query, kind=k or None, top_n=n, tags=tags or None)
    except SemanticModelUnavailableOfflineError as exc:
        search_mode = "lexical_fallback"
        fallback_reason = "semantic_model_unavailable_offline"
        diagnostics.append(
            _diagnostic(
                "semantic_model_unavailable_offline",
                str(exc),
                recovery_tools=["wave_help"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_index.py --root .",
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
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_index.py --root .",
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
            {"query": query, "kind": k, "mode": _mode, "search_mode": search_mode, "results": []},
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
            "results": [_search_result("doc", result) for result in results],
        },
        diagnostics=diagnostics,
        next_tools=["seed_get", "wave_get_prompt"],
        usage=f"seed_get(name={results[0]['path']!r})" if results[0].get("kind") == "seed" else "",
    )


def code_search_response(index: WaveIndex, query: str, language: str = "", limit: int = 5, kind: Optional[str] = None, max_per_file: Optional[int] = None, tags: Optional[list] = None) -> dict[str, Any]:
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

    def _data(results: list) -> dict:
        d: dict[str, Any] = {"query": query, "language": language or None, "results": results}
        if lang_resolved is not None:
            d["language_resolved"] = lang_resolved
        d["language_extensions"] = lang_exts
        return d

    try:
        if category_langs is not None:
            # Fetch unfiltered results then post-filter to the category set.
            raw = index.search_code(query, language=None, top_n=n * len(category_langs), kind=kind, max_per_file=max_per_file, tags=tags or None)
            results = [r for r in raw if r.get("language") in category_langs][:n]
        else:
            results = index.search_code(query, language=language or None, top_n=n, kind=kind, max_per_file=max_per_file, tags=tags or None)
    except SemanticModelUnavailableOfflineError as exc:
        return _response(
            "error",
            _data([]),
            diagnostics=[
                _diagnostic(
                    "semantic_model_unavailable_offline",
                    str(exc),
                    recovery_tools=["wave_help"],
                    recovery_usage="python3 .wavefoundry/framework/scripts/setup_index.py --root . --include-code",
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
                    recovery_usage="python3 .wavefoundry/framework/scripts/setup_index.py --root . --include-code",
                )
            ],
            next_tools=["wave_help"],
            usage="wave_help(goal='search_code')",
        )
    if not results:
        return _response(
            "ok",
            _data([]),
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
        _data([_search_result("code", result) for result in results]),
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
                    recovery_usage="python3 .wavefoundry/framework/scripts/setup_index.py --root .",
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
    "planned": "prepare_wave",
    "paused": "resume_wave",
}


def _wave_current_sort_key(wave: dict) -> tuple[int, str]:
    """Sort key: active (0), planned (1), paused (2), other (3); then by wave_id."""
    priority = {"active": 0, "planned": 1, "paused": 2}
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
    active_entry = entries[0] if entries[0]["status"] == "active" else None
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
    if scheme == "code":
        seq: list[tuple[str, list[dict]]] = [("code", index._code_chunks)]
    elif scheme == "seed":
        seq = [("seed", index._docs_chunks), ("doc", index._docs_chunks)]
    else:
        seq = [("doc", index._docs_chunks)]
    for prefix, chunks in seq:
        for ch in chunks:
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


def _index_lock_dir_for_state_path(state_path: Path) -> Path:
    """Return the .build.lock directory that corresponds to a background-refresh state file."""
    return state_path.parent / ".build.lock"


def _background_refresh_active(state_path: Path) -> bool:
    # Primary guard: if the indexer's file-system build lock exists and is not stale, a
    # build is actively running — regardless of what the state file says.  This handles
    # the case where the state file's PID has already exited (process finished) but a
    # newly-spawned indexer from a subsequent trigger is currently holding the lock.
    lock_dir = _index_lock_dir_for_state_path(state_path)
    if lock_dir.exists():
        try:
            import time as _time
            age = _time.time() - lock_dir.stat().st_mtime
        except OSError:
            age = 0
        if age < BACKGROUND_INDEX_LOCK_STALE_SECONDS:
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
    cmd = [sys.executable, str(indexer), "--root", str(root)]
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
        next_tools=["wave_current", "wave_get_change"],
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


_VALID_GATES = {"seed_edit_allowed", "framework_edit_allowed"}


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
            "Use wave_open_gate / wave_close_gate to manage gates explicitly.",
            recovery_tools=["wave_close_gate"],
            recovery_usage="wave_close_gate(gate='seed_edit_allowed')",
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
            next_tools=["wave_open_gate"],
            usage=f"wave_open_gate(gate='seed_edit_allowed')",
        )
    overrides = _read_guard_overrides(root)
    if overrides.get(gate_s, {}).get("enabled", False):
        return _response(
            "error",
            {"gate": gate_s, "enabled": True},
            diagnostics=[_diagnostic(
                "gate_already_open",
                f"Gate '{gate_s}' is already open. Close it with wave_close_gate before opening again.",
                recovery_tools=["wave_close_gate"],
                recovery_usage=f"wave_close_gate(gate={gate_s!r})",
            )],
            next_tools=["wave_close_gate"],
            usage=f"wave_close_gate(gate={gate_s!r})",
        )
    overrides.setdefault(gate_s, {})["enabled"] = True
    _write_guard_overrides(root, overrides)
    return _response(
        "ok",
        {"gate": gate_s, "enabled": True},
        next_tools=["wave_close_gate"],
        usage=f"wave_close_gate(gate={gate_s!r})",
    )


def wave_close_gate_response(root: Path, gate: str) -> dict[str, Any]:
    """Close an edit gate, disabling the corresponding guard in guard-overrides.json."""
    gate_s = (gate or "").strip()
    if gate_s not in _VALID_GATES:
        return _response(
            "error",
            {"gate": gate_s, "valid_gates": sorted(_VALID_GATES)},
            diagnostics=[_diagnostic("invalid_arguments", f"Unknown gate '{gate_s}'. Valid gates: {sorted(_VALID_GATES)}.")],
            next_tools=["wave_close_gate"],
            usage=f"wave_close_gate(gate='seed_edit_allowed')",
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
        next_tools=["wave_open_gate"],
        usage=f"wave_open_gate(gate={gate_s!r})",
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
                    recovery_usage="python3 .wavefoundry/framework/scripts/setup_index.py --root .",
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
                f"Index layer missing: {layer}. Run: python3 .wavefoundry/framework/scripts/setup_index.py --root .",
                recovery_tools=["wave_help"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_index.py --root .",
            )
        )
    for layer in health.get("stale_layers", []):
        diagnostics.append(
            _diagnostic(
                "index_stale",
                f"Index layer stale: {layer}. Run: python3 .wavefoundry/framework/scripts/setup_index.py --root . --full",
                recovery_tools=["wave_help"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_index.py --root . --full",
            )
        )
    overview = health.get("readiness_overview")
    if overview == "degraded":
        diagnostics.append(
            _diagnostic(
                "index_degraded",
                "Index metadata is present but merged semantic chunks did not load; search may fall back to lexical retrieval.",
                recovery_tools=["wave_help", "wave_index_build"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_index.py --root .",
            )
        )
    elif overview == "absent":
        diagnostics.append(
            _diagnostic(
                "index_absent",
                "No index metadata found under project or framework index dirs (nothing to search semantically yet).",
                recovery_tools=["wave_help"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_index.py --root .",
            )
        )
    for layer in health.get("chunker_version_mismatch_layers", []):
        diagnostics.append(
            _diagnostic(
                "chunker_version_mismatch",
                f"Index layer '{layer}' was built with an older chunker version. "
                "A full rebuild is required: python3 .wavefoundry/framework/scripts/setup_index.py --root . --full",
                recovery_tools=["wave_index_build"],
                recovery_usage="python3 .wavefoundry/framework/scripts/setup_index.py --root . --full",
            )
        )
    background_build_status = _background_build_status(index.root)
    if background_build_status == "running":
        diagnostics.append(
            _diagnostic(
                "background_code_build_running",
                "A background code index build is in progress. "
                f"Watch progress: {index.root / '.wavefoundry' / 'index' / 'background-build.log'}",
                recovery_tools=[],
                recovery_usage="wave_index_health()",
            )
        )

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
            (w for w in waves if w["id"].lower().startswith(wid) or wid in w["id"].lower()),
            None,
        )
        if matched:
            next_action = "implement_wave" if matched["status"] == "active" else "prepare_wave"
            wave_data = {**matched, "next_action": next_action}
            wave_ok = matched["status"] in ("active", "planned")
        else:
            wave_data = {"id": wave_id, "status": "not_found"}
    else:
        wave = current_wave(root, cache=cache)
        if wave:
            next_action = "implement_wave" if wave["status"] == "active" else "prepare_wave"
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

    if not state_path.exists():
        return _response("ok", {"layer": layer_s, "state": "idle"}, next_tools=["wave_index_build"], usage="wave_index_build()")

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _response("ok", {"layer": layer_s, "state": "idle"}, next_tools=["wave_index_build"], usage="wave_index_build()")

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

    if not log_done and isinstance(pid, int) and _pid_is_running(pid):
        running_data: dict[str, Any] = {"layer": layer_s, "state": "running", "pid": pid, "started_at": started_at, "elapsed_seconds": elapsed, "progress": last_line}
        _running_prev = _read_index_build_stats_file(root, layer_s)
        if _running_prev is not None:
            running_data["previous_stats"] = _running_prev
        return _response(
            "ok",
            running_data,
            next_tools=["wave_index_build_status"],
            usage="wave_index_build_status()",
        )

    # Process not running (or log confirms done) — build finished (or crashed). Parse summary from log.
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
    return _response("ok", summary, next_tools=["wave_index_health"], usage="wave_index_health()")


def wave_dashboard_start_response(root: Path) -> dict[str, Any]:
    """Start the local dashboard server (with browser open) or return its URL if already running."""
    import subprocess
    import time as _time

    meta_path = root / ".wavefoundry" / "dashboard-server.json"

    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            pid = meta.get("pid")
            url = meta.get("url", "")
            if isinstance(pid, int) and _pid_is_running(pid) and url:
                return _response(
                    "ok",
                    {"already_running": True, "pid": pid, "url": url},
                    usage=url,
                )
        except (OSError, json.JSONDecodeError):
            pass

    scripts_dir = Path(__file__).resolve().parent
    cmd = [sys.executable, str(scripts_dir / "dashboard_server.py"), "--root", str(root), "--open"]
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
    return _response("dry_run" if mode_s == "dry_run" else "ok", {"wave_id": wave_id, "mode": mode_s, "change_count": len(change_ids), "lint_passed": lint_passed, "garden_passed": garden_passed, "updated": updated, "repairs_needed": repairs_needed, "repaired": repaired, "required_council_signoffs": required_council_signoffs}, diagnostics=_ac_advisories if _ac_advisories else None, next_tools=["wave_current"], usage="wave_current()")


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
    if current_status == "active":
        status_transition = {"from": "active", "to": "paused"}
    elif current_status == "paused":
        status_transition = {"from": "paused", "to": "paused"}
    else:
        status_transition = {"from": current_status, "to": current_status}
    diagnostics: list[dict[str, Any]] = []
    if current_status not in ("active", "paused"):
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
        if status_transition["from"] == "active" and status_transition["to"] == "paused":
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


def wave_review_response(root: Path, wave_id: str) -> dict[str, Any]:
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
    required_lanes = ["operator"] + wave_lanes + extra_lanes
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
        {"wave_id": wave_id, "required_lanes": required_lanes, "lane_results": lane_results, "required_council_signoffs": required_council_signoffs, "council_results": council_results, "lint_passed": lint_result["passed"], "max_severity": max_severity},
        diagnostics=diagnostics,
        next_tools=["wave_validate", "wave_current"],
        usage="wave_validate()",
    )


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
    updated = False
    handoff_rel = ""
    if mode_s == "create":
        status_match = _STATUS_PATTERN.search(text)
        if status_match and status_match.group(1) != "closed":
            import time
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
        {"wave_id": wave_id, "mode": mode_s, "updated": updated, "handoff_path": handoff_rel},
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
    if current_status != "closed":
        return _response("error", {"wave_id": wave_id, "current_status": current_status}, diagnostics=[_diagnostic("wave_not_closed", f"Wave '{wave_id}' has status '{current_status}' — only closed waves can be reopened.", recovery_tools=["wave_current"], recovery_usage="wave_current()")], next_tools=["wave_current"], usage="wave_current()")
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

## Tasks

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

    return _response("ok", {"glob": glob, "count": len(paths), "paths": paths}, next_tools=["code_read", "code_keyword_search"], usage="code_read(path='...', start_line=1, end_line=50)")


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
    return _response("ok", {"path": path, "start_line": lo, "end_line": hi, "total_lines": total, "content": numbered}, next_tools=["code_keyword_search", "code_definition"], usage=f"code_keyword_search(query='...', glob='*.py')")


def code_keyword_search_response(root: Path, query: str, glob: str = "") -> dict[str, Any]:
    """Search repository files for an exact keyword/substring, returning path/line/snippet results."""
    if not query.strip():
        return _response("error", {"query": query}, diagnostics=[_diagnostic("invalid_arguments", "Search query must be a non-empty string.")], next_tools=["code_list_files"], usage="code_list_files()")
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

    return _response("ok", {"query": query, "glob": glob, "count": len(results), "results": results}, next_tools=["code_read"], usage="code_read(path='...', start_line=N, end_line=N+20)")


# ---------------------------------------------------------------------------
# Symbol navigation helpers (milestone 2 — Python AST, unsupported for others)
# ---------------------------------------------------------------------------

_SUPPORTED_DEFINITION_LANGS = {"python"}
_SUPPORTED_REFERENCE_LANGS = {"python"}


_EXT_TO_LANG: dict[str, str] = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".mjs": "javascript", ".cjs": "javascript",
    ".go": "go", ".rs": "rust", ".java": "java", ".rb": "ruby",
    ".cs": "csharp", ".cpp": "cpp", ".hpp": "cpp", ".c": "c", ".h": "c",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".fish": "fish",
    ".kt": "kotlin", ".kts": "kotlin", ".groovy": "groovy", ".scala": "scala",
    ".css": "css", ".scss": "scss",
    ".sql": "sql", ".xml": "xml",
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


def _detect_language(path: str) -> str:
    ext = Path(path).suffix.lower()
    return _EXT_TO_LANG.get(ext, "unknown")


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
                })
    return results


def _python_references(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Find references to *symbol* in Python files via text search (lightweight)."""
    results: list[dict[str, Any]] = []
    root_r = root.resolve()
    for p in _walk_repo_for_navigation(root):
        if p.suffix.lower() != ".py":
            continue
        try:
            source = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = str(p.resolve().relative_to(root_r)).replace("\\", "/")
        for lineno, line in enumerate(source.splitlines(), 1):
            if symbol in line:
                results.append({"path": rel, "line": lineno, "snippet": line.rstrip()})
    return results


_KEYWORD_FALLBACK_RESULT_CAP = 50


def _keyword_fallback_definitions(root: Path, symbol: str) -> list[dict[str, Any]]:
    """Keyword fallback for non-Python definition lookup."""
    results = []
    root_r = root.resolve()
    pattern = re.compile(r"\b" + re.escape(symbol) + r"\b")
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
                results.append({"path": rel, "line": lineno, "snippet": line.rstrip(), "method": "keyword_fallback"})
                if len(results) >= _KEYWORD_FALLBACK_RESULT_CAP:
                    break
    return results


def code_definition_response(root: Path, symbol_or_path_position: str) -> dict[str, Any]:
    """Find definition(s) for a symbol. Uses Python AST for Python files; keyword fallback for all other languages."""
    symbol = symbol_or_path_position.strip()
    if not symbol:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("invalid_arguments", "Symbol must be a non-empty string.")], next_tools=["code_keyword_search"], usage="code_keyword_search(query='MyClass')")
    try:
        definitions = _python_definitions(root, symbol)
    except Exception as exc:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Definition search failed: {exc}")], next_tools=["code_keyword_search"], usage=f"code_keyword_search(query={symbol!r})")
    if definitions:
        return _response(
            "ok",
            {"symbol": symbol, "language": "python", "definitions": definitions, "supported_languages": list(_SUPPORTED_DEFINITION_LANGS), "method": "ast"},
            next_tools=["code_read"],
            usage=f"code_read(path={definitions[0]['path']!r}, start_line={definitions[0]['line']}, end_line={definitions[0]['line'] + 20})",
        )
    # No Python definitions found — run keyword fallback across all languages
    try:
        fallback = _keyword_fallback_definitions(root, symbol)
    except Exception as exc:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Fallback search failed: {exc}")], next_tools=["code_keyword_search"], usage=f"code_keyword_search(query={symbol!r})")
    if not fallback:
        return _response(
            "ok",
            {"symbol": symbol, "definitions": [], "method": "keyword_fallback"},
            diagnostics=[_diagnostic("not_found", f"No definition found for '{symbol}' in any language.", recovery_tools=["code_keyword_search"], recovery_usage=f"code_keyword_search(query={symbol!r})")],
            next_tools=["code_keyword_search"],
            usage=f"code_keyword_search(query={symbol!r})",
        )
    return _response(
        "ok",
        {"symbol": symbol, "definitions": fallback, "method": "keyword_fallback", "note": "AST-based lookup is Python-only. Results are keyword matches across all languages."},
        next_tools=["code_read"],
        usage=f"code_read(path={fallback[0]['path']!r}, start_line={fallback[0]['line']}, end_line={fallback[0]['line'] + 20})",
    )


def code_references_response(root: Path, symbol_or_path_position: str) -> dict[str, Any]:
    """Find references to a symbol. Uses Python text matching for Python files; keyword fallback for all other languages."""
    symbol = symbol_or_path_position.strip()
    if not symbol:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("invalid_arguments", "Symbol must be a non-empty string.")], next_tools=["code_keyword_search"], usage="code_keyword_search(query='my_func')")
    try:
        refs = _python_references(root, symbol)
    except Exception as exc:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Reference search failed: {exc}")], next_tools=["code_keyword_search"], usage=f"code_keyword_search(query={symbol!r})")
    if refs:
        return _response(
            "ok",
            {"symbol": symbol, "language": "python", "count": len(refs), "references": refs, "method": "ast", "supported_languages": list(_SUPPORTED_REFERENCE_LANGS)},
            next_tools=["code_read"],
            usage=f"code_read(path='...', start_line=N, end_line=N+20)",
        )
    # No Python references — run keyword fallback across all languages
    try:
        fallback = _keyword_fallback_definitions(root, symbol)
    except Exception as exc:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Fallback search failed: {exc}")], next_tools=["code_keyword_search"], usage=f"code_keyword_search(query={symbol!r})")
    if not fallback:
        return _response(
            "ok",
            {"symbol": symbol, "references": [], "count": 0, "method": "keyword_fallback"},
            diagnostics=[_diagnostic("not_found", f"No references found for '{symbol}'.", recovery_tools=["code_keyword_search"], recovery_usage=f"code_keyword_search(query={symbol!r})")],
            next_tools=["code_keyword_search"],
            usage=f"code_keyword_search(query={symbol!r})",
        )
    return _response(
        "ok",
        {"symbol": symbol, "references": fallback, "count": len(fallback), "method": "keyword_fallback", "note": "Python-only AST lookup found no results. Results are keyword matches across all languages."},
        next_tools=["code_read"],
        usage=f"code_read(path='...', start_line=N, end_line=N+20)",
    )


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
# code_ask — mechanical retrieval routing for codebase Q&A
# ---------------------------------------------------------------------------

def _classify_question(question: str) -> str:
    """Heuristic question classifier: navigational | explanatory | instructional."""
    q = question.lower()
    navigational_signals = ["where", "which file", "what file", "find", "locate", "path to"]
    instructional_signals = ["how do i", "how to", "steps to", "how can i", "how should i", "how would i"]
    for sig in instructional_signals:
        if sig in q:
            return "instructional"
    for sig in navigational_signals:
        if sig in q:
            return "navigational"
    return "explanatory"


def _heuristic_confidence(citations: list[dict]) -> str:
    if len(citations) >= 2:
        return "high"
    if len(citations) == 1:
        return "medium"
    return "low"


def code_ask_response(index: "WaveIndex", root: Path, question: str) -> dict[str, Any]:
    """Mechanical routing: broad retrieval pass → targeted pass → assemble structured response."""
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

    # Broad pass: semantic search over code and docs
    try:
        code_results = index.search_code(question, top_n=5, max_per_file=2)
    except Exception:
        code_results = []
        gaps.append("code index unavailable")

    try:
        doc_results = index.search_docs(question, top_n=3)
    except Exception:
        doc_results = []
        gaps.append("docs index unavailable")

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

    broad_hits = code_results + doc_results
    citations = [_to_citation(r) for r in broad_hits]

    # Targeted pass: keyword and structural lookup when broad pass is thin
    if len(citations) < 2:
        try:
            kw_resp = code_keyword_search_response(root, question.split()[0] if question.split() else question)
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

    confidence = _heuristic_confidence(citations)

    # Assemble answer text from top citations
    if citations:
        top = citations[0]
        answer = f"Based on indexed sources: see {top['ref']}."
        if len(citations) > 1:
            answer += f" Additional evidence in {', '.join(c['ref'] for c in citations[1:3])}."
    else:
        answer = f"No indexed evidence found for this question. The topic may not be covered in the current index or may use different terminology."

    return _response(
        "ok",
        {
            "question": question,
            "question_type": question_type,
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "gaps": gaps,
            "index_freshness": index_freshness,
        },
        next_tools=["code_read", "docs_search"],
        usage=f"code_read(path={citations[0]['path']!r}, start_line={citations[0]['lines'][0] if citations[0]['lines'] else 1})" if citations else "code_search(query=...)",
    )


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

def build_server(root: Path):
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("wavefoundry_mcp")
    index = WaveIndex(root)
    cache = McpRepoCache(root, index=index)

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
    def docs_search(
        query: str,
        kind: Literal["", "doc", "seed", "architecture", "prompt", "doc-summary"] = "",
        tags: list = [],
        limit: int = 5,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Semantic search over docs, architecture, prompts, seed chunks, and framework seeds at .wavefoundry/framework/seeds/.

        Prefer when: searching by concept, intent, or natural language across project and framework documentation.
        Use code_keyword_search instead when the exact text is known.
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
            limit: Maximum results to return (1–20, default 5).
        """
        bad = _ensure_no_extra_args("docs_search", kwargs)
        if bad is not None:
            return bad
        return docs_search_response(index, query, kind, limit=limit, tags=tags or None)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_search(query: str, language: str = "", kind: str = "", max_per_file: int = 0, tags: list = [], limit: int = 5, **kwargs: Any) -> dict[str, Any]:
        """Semantic search over indexed source code chunks. Requires a built code index (wave_index_build content='code').

        Prefer when: searching for code by concept, behavior, or intent (e.g. "React component with loading state").
        Use code_keyword_search instead when the exact token, symbol, or string is known — always available, deterministic.
        Use docs_search instead when the answer is in a spec, architecture doc, or prompt rather than source code.
        When the code index is absent: returns status='error' with a diagnostic — does not crash.

        Orientation pass (CIA): use kind="code-summary" with max_per_file=1 for a fast file-level survey before targeted retrieval.

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
            limit: Maximum results to return (1–20, default 5).
        """
        bad = _ensure_no_extra_args("code_search", kwargs)
        if bad is not None:
            return bad
        return code_search_response(index, query, language, limit=limit, kind=kind or None, max_per_file=max_per_file or None, tags=tags or None)

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
        return seed_get_response(index, name)

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
        return code_dependencies_response(root, path)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_ask(question: str, **kwargs: Any) -> dict[str, Any]:
        """Ask a natural-language question about the codebase and receive a grounded, cited answer.

        Performs mechanical retrieval routing: broad semantic pass (code_search + docs_search) followed by
        targeted keyword pass. Returns a structured response with citations, confidence, and gaps.
        No LLM synthesis occurs in this tool — the calling agent synthesizes from the returned citations.

        Response fields:
        - answer: Short answer with primary citation reference(s)
        - citations: List of {ref, path, lines, excerpt, score, kind}
        - confidence: "high" (2+ citations), "medium" (1 citation), "low" (no evidence)
        - gaps: Retrieval gaps or index unavailability notices
        - question_type: "navigational" | "explanatory" | "instructional"
        - index_freshness: "current" | "stale"

        Args:
            question: Natural-language question about the codebase, e.g. "where does billing handle failed payments?"
        """
        bad = _ensure_no_extra_args("code_ask", kwargs)
        if bad is not None:
            return bad
        return code_ask_response(index, root, question)

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
        return wave_current_response(root, cache)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_list_waves(limit: int = 50, **kwargs: Any) -> dict[str, Any]:
        """List all waves with their ID, status, and change count.

        Args:
            limit: Maximum waves to return (1–200, default 50). Check ``has_more`` for truncation.
        """
        bad = _ensure_no_extra_args("wave_list_waves", kwargs)
        if bad is not None:
            return bad
        return wave_list_waves_response(root, limit=limit, cache=cache)

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
        return wave_list_plans_response(root, limit=limit, cache=cache)

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
        return wave_get_change_response(root, change_id=change_id, wave_id=wave_id)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_get_prompt(shortcut: str, **kwargs: Any) -> dict[str, Any]:
        """Return the full rendered prompt for a Wave Framework shortcut phrase.

        Args:
            shortcut: Shortcut phrase, e.g. "Prepare wave" or "Plan feature".
        """
        bad = _ensure_no_extra_args("wave_get_prompt", kwargs)
        if bad is not None:
            return bad
        return wave_get_prompt_response(root, shortcut, cache)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_get_handoff(**kwargs: Any) -> dict[str, Any]:
        """Read the session handoff document (docs/agents/session-handoff.md).

        Returns the document content and last-modified timestamp.
        Returns a structured not-found response when the file is absent.
        """
        bad = _ensure_no_extra_args("wave_get_handoff", kwargs)
        if bad is not None:
            return bad
        return wave_get_handoff_response(root)

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
        return wave_set_handoff_response(root, content, cache=cache)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_open_gate(gate: str, **kwargs: Any) -> dict[str, Any]:
        """Open an edit gate in .wavefoundry/guard-overrides.json.

        Sets the named guard to enabled so framework or seed edits are permitted.
        Returns an error if the gate is already open — close it first to avoid
        silent double-opens (which indicate a bug or forgotten close).

        Every open must be paired with a matching wave_close_gate call.
        wave_pause and wave_close automatically close all open gates.

        Args:
            gate: Gate to open. One of: ``seed_edit_allowed``, ``framework_edit_allowed``.
        """
        bad = _ensure_no_extra_args("wave_open_gate", kwargs)
        if bad is not None:
            return bad
        return wave_open_gate_response(root, gate)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_close_gate(gate: str, **kwargs: Any) -> dict[str, Any]:
        """Close an edit gate in .wavefoundry/guard-overrides.json.

        Sets the named guard to disabled. Returns an advisory diagnostic (not an
        error) if the gate was already closed — double-close is harmless.

        Args:
            gate: Gate to close. One of: ``seed_edit_allowed``, ``framework_edit_allowed``.
        """
        bad = _ensure_no_extra_args("wave_close_gate", kwargs)
        if bad is not None:
            return bad
        return wave_close_gate_response(root, gate)

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
        return wave_map_response(root, address, index)

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
        return wave_create_wave_response(root, slug, mode=mode, cache=cache)

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
        return wave_add_change_response(root, wave_id, change_id, mode=mode, cache=cache)

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
        return wave_remove_change_response(root, wave_id, change_id, mode=mode, cache=cache)

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
        return wave_prepare_response(root, wave_id, mode=mode, cache=cache)

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
        return wave_pause_response(root, wave_id, mode=mode, cache=cache)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_review(wave_id: str, **kwargs: Any) -> dict[str, Any]:
        """Run review readiness checks for a wave and return structured lane summary.

        Args:
            wave_id: Wave ID or unique prefix.
        """
        bad = _ensure_no_extra_args("wave_review", kwargs)
        if bad is not None:
            return bad
        return wave_review_response(root, wave_id)

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
        return wave_reopen_response(root, wave_id)

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
        return wave_close_response(root, wave_id, mode=mode, cache=cache)

    # --- Change creation ---

    def _new_change_response(kind: str, slug: str) -> dict[str, Any]:
        return _change_create_response(root, kind, slug, mode="create", cache=cache)

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
        return wave_index_health_response(index)

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
        return wave_audit_response(root, wave_id=wave_id, index=index, cache=cache)

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
        return wave_index_build_response(root, content=content, mode=mode, layer=layer, cache=cache)

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
        return wave_index_build_status_response(root, layer=layer)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_dashboard_start(**kwargs: Any) -> dict[str, Any]:
        """Start the local dashboard server and open it in the browser.

        If the dashboard is already running, returns its URL immediately without
        spawning a second process. Otherwise spawns the server in the background,
        waits up to 5 seconds for it to bind, and returns the URL.

        The dashboard provides a live web UI for wave status, index health, git
        activity, and (when ``auto_index`` is enabled) automatic index rebuilds.
        """
        bad = _ensure_no_extra_args("wave_dashboard_start", kwargs)
        if bad is not None:
            return bad
        return wave_dashboard_start_response(root)

    @mcp.tool(annotations=_READONLY_TOOL)
    def wave_validate(**kwargs: Any) -> dict[str, Any]:
        """Run docs_lint against the project. Returns structured pass/fail with errors.

        Use for targeted lint-only checks. Prefer wave_audit for a combined wave state + lint + index health snapshot.
        """
        bad = _ensure_no_extra_args("wave_validate", kwargs)
        if bad is not None:
            return bad
        return wave_validate_response(root)

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
        return wave_run_sensors_response(root)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_garden(mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Run docs_gardener to update Last verified dates. Returns summary.

        Args:
            mode: Either "dry_run" (preview, no writes) or "run" (execute gardener).
        """
        bad = _ensure_no_extra_args("wave_garden", kwargs)
        if bad is not None:
            return bad
        return wave_garden_response(root, mode=mode, cache=cache)

    @mcp.tool(annotations=_MUTATING_TOOL)
    def wave_sync_surfaces(mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Run render_platform_surfaces to regenerate .claude/, .cursor/ hook configs.

        Args:
            mode: Either "dry_run" (preview, no writes) or "run" (execute renderer).
        """
        bad = _ensure_no_extra_args("wave_sync_surfaces", kwargs)
        if bad is not None:
            return bad
        return wave_sync_surfaces_response(root, mode=mode, cache=cache)

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
        return code_list_files_response(root, glob=glob)

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
        return code_read_response(root, path, start_line=start_line, end_line=end_line)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_keyword_search(query: str, glob: str = "", **kwargs: Any) -> dict[str, Any]:
        """Search repository files for an exact keyword or substring.

        Prefer when: the exact token, symbol name, or string pattern is known. Always available — no index required.
        Use docs_search or code_search instead when searching by concept or intent rather than exact text.
        Returns deterministic path/line/snippet results for each match.
        Respects the same ignore/exclusion rules as the semantic index.

        Args:
            query: Exact text to search for (substring match).
            glob: Optional glob to restrict the search, e.g. "**/*.py" or "*.md".
        """
        bad = _ensure_no_extra_args("code_keyword_search", kwargs)
        if bad is not None:
            return bad
        return code_keyword_search_response(root, query, glob=glob)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_definition(symbol_or_path_position: str, **kwargs: Any) -> dict[str, Any]:
        """Find definition(s) for a symbol name by searching all Python files via AST.

        Prefer when: looking up where a Python function or class is defined by name.
        For non-Python symbols, use code_keyword_search directly — this tool searches only .py files.
        If no Python definition is found, the response includes a code_keyword_search fallback recommendation.

        Supported languages: Python (AST-based, finds function/class/async-function definitions).

        Args:
            symbol_or_path_position: Symbol name to look up (e.g. "MyClass", "process_wave").
                                     Exact or partial match against Python AST node names.
        """
        bad = _ensure_no_extra_args("code_definition", kwargs)
        if bad is not None:
            return bad
        return code_definition_response(root, symbol_or_path_position)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_references(symbol_or_path_position: str, **kwargs: Any) -> dict[str, Any]:
        """Find references to a symbol by searching all Python .py files via text matching.

        Prefer when: tracing all call sites for a known Python symbol — more targeted than code_keyword_search.
        For non-Python symbols, use code_keyword_search directly — this tool searches only .py files.

        Supported languages: Python (text-based matching in .py files).

        Args:
            symbol_or_path_position: Symbol name to find references for (e.g. "wave_close_response").
                                     Text-based search in Python files.
        """
        bad = _ensure_no_extra_args("code_references", kwargs)
        if bad is not None:
            return bad
        return code_references_response(root, symbol_or_path_position)

    # --- Read-only MCP Resources ---
    # These expose stable context as MCP resources rather than tool calls.
    # Agents should prefer resources for read-only context discovery and
    # fall back to the equivalent tools when they need structured envelopes.

    def _read_doc_or_not_found(path: Path, label: str) -> str:
        """Read a markdown doc and return its text, or a clear not-found message."""
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f"# Not Found\n\n`{label}` does not exist at `{_repo_rel(root, path)}`.\n"

    @mcp.resource(
        "wavefoundry://overview",
        name="project_overview",
        description="Project overview and orientation doc (docs/references/project-overview.md).",
        mime_type="text/markdown",
    )
    def resource_project_overview() -> str:
        """Return the project overview document."""
        candidates = [
            root / "docs" / "references" / "project-overview.md",
            root / "docs" / "README.md",
            root / "README.md",
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
        return _read_doc_or_not_found(root / "docs" / "prompts" / "index.md", "docs/prompts/index.md")

    @mcp.resource(
        "wavefoundry://architecture/current-state",
        name="architecture_current_state",
        description="Architecture current-state summary (docs/architecture/current-state.md).",
        mime_type="text/markdown",
    )
    def resource_architecture_current_state() -> str:
        """Return the architecture current-state document."""
        return _read_doc_or_not_found(root / "docs" / "architecture" / "current-state.md", "docs/architecture/current-state.md")

    @mcp.resource(
        "wavefoundry://wave/current",
        name="current_wave",
        description="Current active wave record. Equivalent to calling wave_current() but returned as markdown text.",
        mime_type="text/markdown",
    )
    def resource_current_wave() -> str:
        """Return the current active wave.md as markdown text."""
        wave_info = current_wave(root, cache=cache)
        if wave_info is None:
            return "# No Active Wave\n\nNo active wave found. Use `wave_create_wave` to start one.\n"
        wave_path = root / wave_info["path"]
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
        return _read_doc_or_not_found(root / "docs" / "agents" / "session-handoff.md", "docs/agents/session-handoff.md")

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
        text = get_change(root, change_id)
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
        wave_md = _find_wave_md(root, wave_id)
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
        text = get_prompt(root, slug)
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
            chunk = index.get_seed(slug)
        except Exception:
            chunk = None
        if chunk is None:
            # Fall back to filesystem scan of framework seeds
            seeds_dir = root / ".wavefoundry" / "framework" / "seeds"
            if seeds_dir.exists():
                slug_lower = slug.lower().strip()
                for p in sorted(seeds_dir.glob("*.md")):
                    if slug_lower in p.stem.lower():
                        return p.read_text(encoding="utf-8")
            return f"# Not Found\n\nNo seed found matching `{slug}`. Use `seed_get(name=...)` for structured lookup.\n"
        # chunk has a "path" and likely "text" or we read from path
        seed_path = root / chunk["path"] if not str(chunk.get("path", "")).startswith("/") else Path(chunk["path"])
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
        arch_dir = root / "docs" / "architecture"
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

    return mcp


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
    mcp = build_server(root)
    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

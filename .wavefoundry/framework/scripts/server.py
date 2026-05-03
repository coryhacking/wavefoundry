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
DOCS_SEARCH_KINDS = frozenset({"doc", "seed", "architecture", "prompt"})
_PROMPT_MISS = object()
"""Sentinel used by ``McpRepoCache.get_prompt_text_cached`` to cache a None
result (i.e. prompt not found) without storing Python ``None``, which cannot
be distinguished from a cache miss. Compared with ``is``, so it must be a
module-level singleton. If ``server.py`` is ever re-executed in the same
process, a new object will be created and old cache entries will be treated as
misses — acceptable because the cache is process-scoped."""
BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS = 15.0


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
        old_hashes = meta.get("file_hashes", {}) if isinstance(meta.get("file_hashes", {}), dict) else {}
        stale_paths = sorted(
            {
                path for path, digest in current_hashes.items()
                if old_hashes.get(path) != digest
            } | (set(old_hashes.keys()) - set(current_hashes.keys()))
        )
        docs_present = docs_json_path.exists()
        meta_present = meta_path.exists()
        return {
            "layer": layer,
            "index_dir": str(index_dir),
            "meta_present": meta_present,
            "docs_present": docs_present,
            "has_sources": bool(current_hashes),
            "stale_paths": stale_paths,
            "current_hash_count": len(current_hashes),
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
        return {
            "project": project,
            "framework": framework,
            "has_any_index": has_any_index,
            "stale_layers": stale_layers,
            "missing_layers": missing_layers,
            "compatible_chunks": compatible_chunks,
            "readiness_overview": readiness_overview,
            "semantic_ready": has_any_index and not stale_layers and compatible_chunks,
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
        if chunk_kind != "doc":
            return False
        if kind == "doc":
            return True
        if kind == "prompt":
            return normalized_path.startswith("docs/prompts/")
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

    def _ensure_loaded(self) -> None:
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

    def search_docs(self, query: str, kind: Optional[str] = None, top_n: int = 5) -> list[dict]:
        self._ensure_loaded()
        DOCS_MODEL = self._indexer_constant("DOCS_MODEL")
        qvec = self._embed_query(query, DOCS_MODEL)
        results = self._cosine_search(qvec, self._docs_vecs, self._docs_chunks, top_n * 2)
        if kind:
            results = [r for r in results if self._doc_matches_kind(r, kind)]
        return results[:top_n]

    def search_code(self, query: str, language: Optional[str] = None, top_n: int = 5) -> list[dict]:
        self._ensure_loaded()
        CODE_MODEL = self._indexer_constant("CODE_MODEL")
        qvec = self._embed_query(query, CODE_MODEL)
        results = self._cosine_search(qvec, self._code_vecs, self._code_chunks, top_n * 2)
        if language:
            results = [r for r in results if r.get("language") == language]
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
        "files_total": len(meta.get("file_hashes", {})),
        "doc_chunks": len(docs_chunks),
        "code_chunks": len(code_chunks),
        "available_content": list(meta.get("content", [])),
        "built_at": meta.get("built_at", ""),
    }


def _extract_rebuild_runtime_stats(output: str) -> dict[str, Any]:
    stats: dict[str, Any] = {}
    if "build_index: index is up to date" in output:
        stats["files_indexed"] = 0
        stats["up_to_date"] = True
        return stats

    done_matches = list(re.finditer(
        r"build_index: done — (?P<files>\d+) files indexed, "
        r"(?P<doc_chunks>\d+) doc chunks, (?P<code_chunks>\d+) code chunks",
        output,
    ))
    if done_matches:
        last_done = done_matches[-1]
        stats["files_indexed"] = int(last_done.group("files"))
        stats["doc_chunks"] = int(last_done.group("doc_chunks"))
        stats["code_chunks"] = int(last_done.group("code_chunks"))
        stats["up_to_date"] = False
        if len(done_matches) > 1:
            stats["pass_stats"] = [
                {
                    "files_indexed": int(match.group("files")),
                    "doc_chunks": int(match.group("doc_chunks")),
                    "code_chunks": int(match.group("code_chunks")),
                }
                for match in done_matches
            ]

    incremental_matches = list(re.finditer(
        r"build_index: incremental \w+ rebuild — (?P<changed>\d+) changed, (?P<removed>\d+) removed",
        output,
    ))
    if incremental_matches:
        last_incremental = incremental_matches[-1]
        stats["changed_files"] = int(last_incremental.group("changed"))
        stats["removed_files"] = int(last_incremental.group("removed"))

    full_matches = list(re.finditer(r"build_index: full \w+ rebuild — (?P<files>\d+) files", output))
    if full_matches:
        stats["rebuild_scope"] = "full"
        stats.setdefault("files_indexed", int(full_matches[-1].group("files")))
    elif incremental_matches:
        stats["rebuild_scope"] = "incremental"

    return stats


def run_index_rebuild(
    root: Path,
    *,
    content: str = "docs",
    full: bool = False,
    layer: str = "project",
) -> dict:
    """Run indexer.py (or setup_index.py for project ``content=all``) synchronously.

    When ``full`` is false (the default), the indexer performs an **incremental update**
    (hash-based: changed files only). When ``full`` is true, it forces a **full rebuild**
    of the selected content for that layer. Exposed as MCP ``wave_index_build`` with ``mode='update'|'rebuild'``.
    """
    import subprocess
    if content not in {"docs", "code", "all"}:
        raise ValueError(f"Unsupported content '{content}'.")
    if layer not in {"project", "framework"}:
        raise ValueError(f"Unsupported layer '{layer}'.")
    if layer == "framework" and content != "docs":
        raise ValueError("Framework index rebuild only supports content 'docs'.")
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
    result = subprocess.run(
        cmd,
        capture_output=True, text=True,
        cwd=str(root),
        env={**os.environ, "PROJECT_ROOT": str(root)},
    )
    output = result.stdout + result.stderr
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    stats: dict[str, Any] = {}
    if result.returncode == 0:
        stats = _read_index_rebuild_stats(root, layer)
        stats.update(_extract_rebuild_runtime_stats(output))
        if stats.get("pass_stats") and not stats.get("up_to_date"):
            stats["files_indexed"] = stats.get("files_total", stats.get("files_indexed", 0))
    mode_label = "rebuild" if full else "update"
    return {
        "passed": result.returncode == 0,
        "content": content,
        "full": full,
        "mode": mode_label,
        "index_scope": "full_rebuild" if full else "incremental_update",
        "layer": layer,
        "stats": stats,
        "output": output,
        "summary": lines[-1] if lines else "",
    }


def docs_search_response(index: WaveIndex, query: str, kind: str = "", limit: int = 5) -> dict[str, Any]:
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
        results = index.search_docs(query, kind=k or None, top_n=n)
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


def code_search_response(index: WaveIndex, query: str, language: str = "", limit: int = 5) -> dict[str, Any]:
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
            raw = index.search_code(query, language=None, top_n=n * len(category_langs))
            results = [r for r in raw if r.get("language") in category_langs][:n]
        else:
            results = index.search_code(query, language=language or None, top_n=n)
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


def _background_refresh_active(state_path: Path) -> bool:
    state = _load_background_refresh_state(state_path)
    pid = state.get("pid")
    started_at = state.get("started_at")
    if isinstance(pid, int) and _pid_is_running(pid):
        return True
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

    # Always return "ok" when health data was successfully computed — agents
    # read ``readiness_overview`` and ``diagnostics`` to decide whether to
    # reindex.  Reserve ``status: "error"`` for the except branch above (i.e.
    # when the health check itself crashed, not when the index is merely absent
    # or stale).
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

    return _response(
        "ok",
        {
            "ready": ready,
            "wave": wave_data,
            "validation": val_result,
            "index": index_data,
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
    status = "ok" if result["passed"] else "error"
    recovery_usage = "python3 .wavefoundry/framework/scripts/setup_index.py --root ."
    if layer_s == "framework":
        recovery_usage = (
            "python3 .wavefoundry/framework/scripts/indexer.py --root . --content docs "
            "--index-dir .wavefoundry/framework/index --include-prefix .wavefoundry/framework "
            "--no-ignore-files"
        )
    elif content_s == "all":
        recovery_usage = "python3 .wavefoundry/framework/scripts/setup_index.py --root . --include-code"
    diagnostics = [] if result["passed"] else [
        _diagnostic(
            "index_rebuild_failed",
            result["output"].strip() or "index rebuild failed",
            recovery_tools=["wave_index_health", "wave_help"],
            recovery_usage=recovery_usage,
        )
    ]
    if cache and result["passed"]:
        cache.invalidate()
    return _response(
        status,
        result,
        diagnostics=diagnostics,
        next_tools=["wave_index_health", "docs_search"] if result["passed"] else ["wave_index_health", "wave_help"],
        usage="docs_search(query='...')" if result["passed"] else "python3 .wavefoundry/framework/scripts/setup_index.py --root .",
    )


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
    return _response("dry_run" if mode_s == "dry_run" else "ok", {"wave_id": wave_id, "mode": mode_s, "change_count": len(change_ids), "lint_passed": lint_passed, "garden_passed": garden_passed, "updated": updated, "repairs_needed": repairs_needed, "repaired": repaired}, diagnostics=_ac_advisories if _ac_advisories else None, next_tools=["wave_current"], usage="wave_current()")


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


def wave_review_response(root: Path, wave_id: str) -> dict[str, Any]:
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
    _trigger_background_index_refresh_for_paths(root, [wave_md])
    lint_result = run_validate(root)
    wave_text = wave_md.read_text(encoding="utf-8")
    required_lanes = _extract_required_review_lanes(wave_text)
    lane_results = [{"lane": lane, "recorded_signoff": _lane_has_signoff(wave_text, lane)} for lane in required_lanes]
    diagnostics = [] if lint_result["passed"] else [_diagnostic("docs_lint_error", err, recovery_tools=["wave_validate"]) for err in lint_result["errors"]]
    missing = [entry["lane"] for entry in lane_results if not entry["recorded_signoff"]]
    if missing:
        diagnostics.append(
            _diagnostic(
                "missing_lane_signoff",
                f"Required review lanes without recorded signoff: {', '.join(missing)}.",
                recovery_tools=["wave_current"],
                recovery_usage="wave_current()",
            )
        )
    status = "ok" if lint_result["passed"] and not missing else "error"
    return _response(
        status,
        {"wave_id": wave_id, "required_lanes": required_lanes, "lane_results": lane_results, "lint_passed": lint_result["passed"]},
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
    required_lanes = _extract_required_review_lanes(text)
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
            missing_lane = _lanes_missing_signoff(text)
            if missing_lane:
                diagnostics.append(
                    _diagnostic(
                        "missing_lane_signoff",
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
    if not lint_result["passed"]:
        diagnostics.extend([_diagnostic("docs_lint_error", err, recovery_tools=["wave_validate"]) for err in lint_result["errors"]])
    # Gate close runs unconditionally so open gates are always reported (and closed in
    # create mode) even when other diagnostics cause an early return.
    gate_diagnostics = _force_gates_closed(root, mode_s)
    if diagnostics:
        return _response("error", {"wave_id": wave_id, "mode": mode_s, "lint_passed": lint_result["passed"], "garden_passed": garden_passed}, diagnostics=diagnostics + gate_diagnostics, next_tools=["wave_validate", "wave_current"], usage="wave_validate()")
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


def code_definition_response(root: Path, symbol_or_path_position: str) -> dict[str, Any]:
    """Find definition(s) for a symbol (Python AST) or return unsupported for other languages."""
    symbol = symbol_or_path_position.strip()
    if not symbol:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("invalid_arguments", "Symbol must be a non-empty string.")], next_tools=["code_keyword_search"], usage="code_keyword_search(query='MyClass')")
    try:
        definitions = _python_definitions(root, symbol)
    except Exception as exc:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Definition search failed: {exc}")], next_tools=["code_keyword_search"], usage=f"code_keyword_search(query={symbol!r})")
    if not definitions:
        return _response(
            "ok",
            {"symbol": symbol, "language": "python", "definitions": [], "supported_languages": list(_SUPPORTED_DEFINITION_LANGS)},
            diagnostics=[_diagnostic("not_found", f"No Python definition found for '{symbol}'. Use code_keyword_search for text-based fallback.", recovery_tools=["code_keyword_search"], recovery_usage=f"code_keyword_search(query={symbol!r})")],
            next_tools=["code_keyword_search"],
            usage=f"code_keyword_search(query={symbol!r})",
        )
    return _response(
        "ok",
        {"symbol": symbol, "language": "python", "definitions": definitions, "supported_languages": list(_SUPPORTED_DEFINITION_LANGS), "note": "Non-Python languages are not supported. Use code_keyword_search for text-based lookup in those files."},
        next_tools=["code_read"],
        usage=f"code_read(path={definitions[0]['path']!r}, start_line={definitions[0]['line']}, end_line={definitions[0]['line'] + 20})",
    )


def code_references_response(root: Path, symbol_or_path_position: str) -> dict[str, Any]:
    """Find references to a symbol in Python files, or return unsupported for other languages."""
    symbol = symbol_or_path_position.strip()
    if not symbol:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("invalid_arguments", "Symbol must be a non-empty string.")], next_tools=["code_keyword_search"], usage="code_keyword_search(query='my_func')")
    try:
        refs = _python_references(root, symbol)
    except Exception as exc:
        return _response("error", {"symbol": symbol}, diagnostics=[_diagnostic("navigation_error", f"Reference search failed: {exc}")], next_tools=["code_keyword_search"], usage=f"code_keyword_search(query={symbol!r})")
    return _response(
        "ok",
        {"symbol": symbol, "language": "python", "count": len(refs), "references": refs, "supported_languages": list(_SUPPORTED_REFERENCE_LANGS), "note": "Reference search uses text matching for Python. Non-Python languages fall back to code_keyword_search."},
        next_tools=["code_read"],
        usage=f"code_read(path='...', start_line=N, end_line=N+20)" if refs else f"code_keyword_search(query={symbol!r})",
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
        kind: Literal["", "doc", "seed", "architecture", "prompt"] = "",
        limit: int = 5,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Semantic search over docs, architecture, prompts, seed chunks, and framework seeds at .wavefoundry/framework/seeds/.

        Prefer when: searching by concept, intent, or natural language across project and framework documentation.
        Use code_keyword_search instead when the exact text is known.
        Degrades to lexical fallback when the semantic model or index is unavailable.

        Args:
            query: Natural language search query.
            kind: Optional filter — one of: doc, seed, architecture, prompt.
            limit: Maximum results to return (1–20, default 5).
        """
        bad = _ensure_no_extra_args("docs_search", kwargs)
        if bad is not None:
            return bad
        return docs_search_response(index, query, kind, limit=limit)

    @mcp.tool(annotations=_READONLY_TOOL)
    def code_search(query: str, language: str = "", limit: int = 5, **kwargs: Any) -> dict[str, Any]:
        """Semantic search over indexed source code chunks. Requires a built code index (wave_index_build content='code').

        Prefer when: searching for code by concept, behavior, or intent (e.g. "React component with loading state").
        Use code_keyword_search instead when the exact token, symbol, or string is known — always available, deterministic.
        Use docs_search instead when the answer is in a spec, architecture doc, or prompt rather than source code.
        When the code index is absent: returns status='error' with a diagnostic — does not crash.

        Choosing a language filter:
        - No filter: query spans the whole codebase. Best when you don't know which language has the answer.
        - Category: use when the answer could be in any language of a family, or the codebase mixes them.
          Categories: java (java/kotlin/scala/groovy), web (typescript/javascript/html/css/scss),
          systems (c/cpp/rust/go), script (python/ruby/shell/fish), data (sql), sparksql (sql alias), dotnet (csharp).
          Category responses include language_resolved (expanded language list) and language_extensions.
        - Canonical name or extension: use when you know the exact language. e.g. "python", "typescript", "tsx", ".tsx".

        Args:
            query: Natural language description of the code behavior or concept to find.
            language: Optional — category name, canonical language name, or raw extension (with or without dot).
            limit: Maximum results to return (1–20, default 5).
        """
        bad = _ensure_no_extra_args("code_search", kwargs)
        if bad is not None:
            return bad
        return code_search_response(index, query, language, limit=limit)

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
    def wave_validate(**kwargs: Any) -> dict[str, Any]:
        """Run docs_lint against the project. Returns structured pass/fail with errors.

        Use for targeted lint-only checks. Prefer wave_audit for a combined wave state + lint + index health snapshot.
        """
        bad = _ensure_no_extra_args("wave_validate", kwargs)
        if bad is not None:
            return bad
        return wave_validate_response(root)

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

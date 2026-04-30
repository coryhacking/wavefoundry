#!/usr/bin/env python3
"""Wavefoundry MCP server — semantic index, wave inspection, and framework operations."""
from __future__ import annotations

import argparse
import functools
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

sys.dont_write_bytecode = True

# ---------------------------------------------------------------------------
# Root discovery (mirrors lifecycle_id.py pattern)
# ---------------------------------------------------------------------------

def _discover_root(override: Optional[str] = None) -> Path:
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


TRUSTED_FRAMEWORK = "trusted_framework"
TRUSTED_PROJECT_METADATA = "trusted_project_metadata"
UNTRUSTED_PROJECT_CONTENT = "untrusted_project_content"
VALID_CHANGE_KINDS = {"bug", "feat", "enh", "change", "doc", "debt", "ref", "task", "maint", "ops"}
MCP_TOOL_PREFIXES = ("wave_", "docs_", "code_", "seed_")
DOCS_SEARCH_KINDS = frozenset({"doc", "seed", "architecture", "prompt"})
_PROMPT_MISS = object()


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

    def _get_embedder(self, model_name: str):
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise IndexNotReadyError(
                "fastembed is not installed. Run: python3 .wavefoundry/framework/scripts/setup_index.py"
            )
        return TextEmbedding(model_name=model_name)

    def _embed_query(self, text: str, model_name: str) -> "np.ndarray":
        import numpy as np
        embedder = self._get_embedder(model_name)
        return next(iter(embedder.embed([text])))

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
            results = [r for r in results if r.get("kind") == kind]
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


class McpRepoCache:
    """Per-process cache for wave/plan summaries; invalidated when repo metadata changes."""

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
        self._waves = None
        self._waves_key = None
        self._plans = None
        self._plans_key = None
        self._prompt_cache = {}
        self._prompt_key = None
        if self._index is not None:
            self._index._loaded = False

    def _wave_fingerprint(self) -> tuple[int, int]:
        waves = self.root / "docs" / "waves"
        if not waves.exists():
            return (0, 0)
        best_ns = 0
        count = 0
        for p in waves.rglob("wave.md"):
            try:
                st = p.stat()
            except OSError:
                continue
            count += 1
            best_ns = max(best_ns, int(st.st_mtime_ns))
        return (count, best_ns)

    def _plans_fingerprint(self) -> tuple[int, int]:
        plans = self.root / "docs" / "plans"
        if not plans.exists():
            return (0, 0)
        best_ns = 0
        count = 0
        for p in plans.glob("*.md"):
            if p.name == "plan-template.md":
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            count += 1
            best_ns = max(best_ns, int(st.st_mtime_ns))
        return (count, best_ns)

    def _prompts_fingerprint(self) -> tuple[int, int]:
        prompts = self.root / "docs" / "prompts"
        if not prompts.exists():
            return (0, 0)
        best_ns = 0
        count = 0
        for p in prompts.glob("*.md"):
            try:
                st = p.stat()
            except OSError:
                continue
            count += 1
            best_ns = max(best_ns, int(st.st_mtime_ns))
        return (count, best_ns)

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
    return {
        "status": status,
        "data": data or {},
        "diagnostics": diagnostics or [],
        "next_tools": next_tools or [],
        "usage": usage,
    }


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
    """If MCP passed unsupported keyword arguments, return a structured error envelope."""
    if not kwargs:
        return None
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
            "wave_change_create",
            "wave_validate",
            "wave_garden",
            "wave_sync_surfaces",
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
                "recommended_chain": ["wave_change_create", "wave_get_change", "wave_validate"],
                "rationale": "Create or preview the change doc, inspect it, then validate docs state.",
                "fallback_tools": ["wave_new_feature"],
                "next_step": "Create or dry-run the change document first.",
                "usage": "wave_change_create(kind='feat', slug='my-feature', mode='dry_run')",
            },
            "inspect_wave": {
                "recommended_chain": ["wave_current", "wave_list_waves", "wave_get_change"],
                "rationale": "Inspect current wave state before opening specific change documents.",
                "fallback_tools": ["wave_list_plans"],
                "next_step": "Read current wave state first.",
                "usage": "wave_current()",
            },
            "start_wave": {
                "recommended_chain": ["wave_create_wave", "wave_add_change", "wave_prepare"],
                "rationale": "Create the wave, admit planned changes, then run transactional prepare checks.",
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
                "rationale": "Search indexed code chunks when code embeddings exist; fall back to guidance when they do not.",
                "fallback_tools": ["docs_search"],
                "next_step": "Run semantic code search.",
                "usage": "code_search(query='build semantic index', language='python')",
            },
            "maintain_framework": {
                "recommended_chain": ["wave_validate", "wave_garden", "wave_sync_surfaces"],
                "rationale": "Land on validation first, then run focused maintenance tools.",
                "fallback_tools": ["wave_current"],
                "next_step": "Validate the repo first.",
                "usage": "wave_validate()",
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

def _load_script(name: str):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / f"{name}.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_validate(root: Path) -> dict:
    """Run docs_lint and return structured pass/fail."""
    import subprocess
    script = Path(__file__).resolve().parent / "docs_lint.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True,
        cwd=str(root),
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


def docs_search_response(index: WaveIndex, query: str, kind: str = "") -> dict[str, Any]:
    k = (kind or "").strip().lower()
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
    try:
        results = index.search_docs(query, kind=k or None)
    except IndexNotReadyError as exc:
        return _response(
            "error",
            {"query": query, "kind": k or None, "results": []},
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
    if not results:
        return _response(
            "ok",
            {"query": query, "kind": k or None, "results": []},
            diagnostics=[
                _diagnostic(
                    "no_results",
                    f"No document results found for query '{query}'.",
                    recovery_tools=["wave_help"],
                    recovery_usage="wave_help(goal='search_docs')",
                )
            ],
            next_tools=["wave_help"],
            usage=f"docs_search(query={query!r})",
        )
    return _response(
        "ok",
        {
            "query": query,
            "kind": k or None,
            "results": [_search_result("doc", result) for result in results],
        },
        next_tools=["seed_get", "wave_get_prompt"],
        usage=f"seed_get(name={results[0]['path']!r})" if results[0].get("kind") == "seed" else "",
    )


def code_search_response(index: WaveIndex, query: str, language: str = "") -> dict[str, Any]:
    try:
        results = index.search_code(query, language=language or None)
    except IndexNotReadyError as exc:
        return _response(
            "error",
            {"query": query, "language": language or None, "results": []},
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
            {"query": query, "language": language or None, "results": []},
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
        {
            "query": query,
            "language": language or None,
            "results": [_search_result("code", result) for result in results],
        },
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


def wave_current_response(root: Path, cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    wave = current_wave(root, cache=cache)
    if wave is None:
        return _response(
            "ok",
            {"wave": None},
            diagnostics=[
                _diagnostic(
                    "no_active_wave",
                    "No active or planned wave found.",
                    recovery_tools=["wave_list_waves"],
                    recovery_usage="wave_list_waves()",
                )
            ],
            next_tools=["wave_list_waves", "wave_list_plans"],
            usage="wave_list_waves()",
        )
    next_action = "implement_wave" if wave["status"] == "active" else "prepare_wave"
    return _response(
        "ok",
        {"wave": {**wave, "next_action": next_action}},
        next_tools=["wave_get_change"],
        usage=f"wave_get_change(change_id={wave['changes'][0]['id']!r})" if wave["changes"] else "",
    )


def wave_list_waves_response(root: Path, cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    waves = cache.list_waves_cached() if cache else list_waves(root)
    return _response(
        "ok",
        {"waves": waves},
        diagnostics=[] if waves else [_diagnostic("no_waves", "No waves found.")],
        next_tools=["wave_current"] if waves else ["wave_list_plans"],
        usage="wave_current()" if waves else "wave_list_plans()",
    )


def wave_list_plans_response(root: Path, cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    plans = cache.list_plans_cached() if cache else list_plans(root)
    return _response(
        "ok",
        {"plans": plans},
        diagnostics=[] if plans else [_diagnostic("no_plans", "No plan docs found.")],
        next_tools=["wave_help"] if plans else ["wave_help"],
        usage="wave_help(goal='plan_feature')",
    )


def wave_get_change_response(root: Path, change_id: str) -> dict[str, Any]:
    text = get_change(root, change_id)
    if text is None:
        return _response(
            "ok",
            {"change_id": change_id, "change": None},
            diagnostics=[
                _diagnostic(
                    "change_not_found",
                    f"No change doc found matching '{change_id}'.",
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
            "change_id": change_id,
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


def _merge_pause_into_session_handoff(existing: str, wave_id: str) -> str:
    """Update or append ``## Current Session`` without discarding other handoff sections."""
    session_header = "## Current Session"
    new_body = (
        f"**Active wave:** `{wave_id}`\n"
        "**Last completed action:** wave_pause via MCP tool.\n"
    )
    if not existing.strip():
        return (
            "# Session Handoff\n\n"
            "Owner: wave-coordinator\n"
            "Status: active\n\n"
            f"{session_header}\n\n"
            f"{new_body}"
        )
    lines = existing.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    found = False
    while i < len(lines):
        line = lines[i]
        if line.strip() == session_header:
            found = True
            out.append(line if line.endswith("\n") else line + "\n")
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            if out and not out[-1].endswith("\n"):
                out[-1] += "\n"
            if not out[-1].endswith("\n\n"):
                out.append("\n")
            out.append(new_body)
            if not new_body.endswith("\n"):
                out.append("\n")
            continue
        out.append(lines[i])
        i += 1
    if not found:
        if out and not (out[-1].endswith("\n")):
            out[-1] += "\n"
        if out and not out[-1].endswith("\n\n"):
            out.append("\n")
        out.append(session_header)
        out.append("\n\n")
        out.append(new_body)
    return "".join(out)


def _resolve_unique_change_doc(root: Path, change_id: str) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]]]:
    matches = _resolve_change_doc_matches(root, change_id)
    if not matches:
        return None, _diagnostic("change_not_found", f"No change doc found matching '{change_id}'.", recovery_tools=["wave_list_plans"], recovery_usage="wave_list_plans()")
    if len(matches) > 1:
        return None, _diagnostic("ambiguous_change_id", f"Multiple change docs match '{change_id}'. Use a more specific ID.", recovery_tools=["wave_list_plans"], recovery_usage="wave_list_plans()")
    return matches[0], None


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
    wave_md.write_text(
        (
            "# Wave Record\n\n"
            "Owner: Engineering\n"
            "Status: planned\n"
            "Last verified: <date>\n\n"
            f"wave-id: `{wave_id}`\n"
            f"Title: {slug_s.replace('-', ' ').title()}\n\n"
            "## Changes\n\n"
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
    text = wave_md.read_text(encoding="utf-8")
    existing = _extract_change_ids_from_wave_text(text)
    if canonical_change_id in existing:
        return _response("ok", {"wave_id": wave_id, "change_id": canonical_change_id, "mode": mode_s, "updated": False}, diagnostics=[_diagnostic("already_admitted", f"Change '{canonical_change_id}' is already admitted.")], next_tools=["wave_current"], usage="wave_current()")
    insert = f"\nChange ID: `{canonical_change_id}`\nChange Status: `planned`\n"
    if mode_s == "create":
        if "## Dependencies" in text:
            text = text.replace("## Dependencies", insert + "\n## Dependencies", 1)
        else:
            text += "\n## Dependencies\n" + insert
        wave_md.write_text(text, encoding="utf-8")
        if cache:
            cache.invalidate()
    return _response("dry_run" if mode_s == "dry_run" else "ok", {"wave_id": wave_id, "change_id": canonical_change_id, "mode": mode_s, "updated": mode_s == "create"}, next_tools=["wave_current", "wave_get_change"], usage=f"wave_get_change(change_id={canonical_change_id!r})")


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
    target = re.compile(rf"\n?Change ID:\s+`{re.escape(change_id)}`\n(?:Previous Change Status:\s+`[^`]+`\n)?Change Status:\s+`[^`]+`\n?", re.MULTILINE)
    if not target.search(text):
        return _response("ok", {"wave_id": wave_id, "change_id": change_id, "mode": mode_s, "updated": False}, diagnostics=[_diagnostic("not_admitted", f"Change '{change_id}' is not admitted to wave.")], next_tools=["wave_current"], usage="wave_current()")
    if mode_s == "create":
        text = target.sub("\n", text, count=1)
        wave_md.write_text(text, encoding="utf-8")
        if cache:
            cache.invalidate()
    return _response("dry_run" if mode_s == "dry_run" else "ok", {"wave_id": wave_id, "change_id": change_id, "mode": mode_s, "updated": mode_s == "create"}, next_tools=["wave_current"], usage="wave_current()")

def _lifecycle_module():
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


def wave_change_create_response(
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


def wave_garden_response(root: Path, cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
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
    return _response(
        status,
        result,
        diagnostics=diagnostics,
        next_tools=["wave_validate", "wave_sync_surfaces"] if result["passed"] else ["wave_validate"],
        usage="wave_sync_surfaces()" if result["passed"] else "wave_validate()",
    )


def wave_sync_surfaces_response(root: Path, cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
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


def wave_prepare_response(root: Path, wave_id: str, mode: str = "dry_run", cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    mode_s = "create" if (mode or "").strip().lower() == "apply" else (mode or "").strip().lower()
    if mode_s not in {"dry_run", "create"}:
        return _response("error", {"wave_id": wave_id, "mode": mode}, diagnostics=[_diagnostic("invalid_arguments", f"Unsupported mode '{mode}'.")], next_tools=["wave_help"], usage="wave_help()")
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id, "mode": mode_s}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
    garden_result = run_garden(root)
    lint_result = run_validate(root)
    text = wave_md.read_text(encoding="utf-8")
    change_ids = _extract_change_ids_from_wave_text(text)
    diagnostics: list[dict[str, Any]] = []
    if not garden_result["passed"]:
        diagnostics.append(_diagnostic("docs_gardener_failed", "docs_gardener failed during prepare.", recovery_tools=["wave_garden", "wave_validate"], recovery_usage="wave_garden()"))
    if not change_ids:
        diagnostics.append(_diagnostic("no_admitted_changes", "Wave has no admitted changes."))
    for admitted_change in change_ids:
        change_doc, change_diag = _resolve_unique_change_doc(root, admitted_change)
        if change_diag is not None:
            diagnostics.append(change_diag)
            continue
        assert change_doc is not None
        missing_headers = _missing_required_change_sections(str(change_doc.get("content") or ""))
        if missing_headers:
            diagnostics.append(
                _diagnostic(
                    "change_doc_missing_sections",
                    f"Admitted change '{admitted_change}' is missing sections: {', '.join(missing_headers)}.",
                    recovery_tools=["wave_get_change"],
                    recovery_usage=f"wave_get_change(change_id={admitted_change!r})",
                )
            )
    if not lint_result["passed"]:
        diagnostics.extend(_diagnostic("docs_lint_error", err, recovery_tools=["wave_validate"]) for err in lint_result["errors"])
    if diagnostics:
        return _response("error", {"wave_id": wave_id, "mode": mode_s, "change_count": len(change_ids), "lint_passed": lint_result["passed"], "garden_passed": garden_result["passed"]}, diagnostics=diagnostics, next_tools=["wave_validate", "wave_current"], usage="wave_validate()")
    updated = False
    if mode_s == "create":
        status_match = _STATUS_PATTERN.search(text)
        if status_match and status_match.group(1) != "active":
            text = text[:status_match.start(1)] + "active" + text[status_match.end(1):]
            wave_md.write_text(text, encoding="utf-8")
            updated = True
            if cache:
                cache.invalidate()
    return _response("dry_run" if mode_s == "dry_run" else "ok", {"wave_id": wave_id, "mode": mode_s, "change_count": len(change_ids), "lint_passed": True, "garden_passed": True, "updated": updated}, next_tools=["wave_current"], usage="wave_current()")


def wave_pause_response(root: Path, wave_id: str, mode: str = "dry_run", cache: Optional[McpRepoCache] = None) -> dict[str, Any]:
    mode_s = "create" if (mode or "").strip().lower() == "apply" else (mode or "").strip().lower()
    if mode_s not in {"dry_run", "create"}:
        return _response("error", {"wave_id": wave_id, "mode": mode}, diagnostics=[_diagnostic("invalid_arguments", f"Unsupported mode '{mode}'.")], next_tools=["wave_help"], usage="wave_help()")
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id, "mode": mode_s}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
    handoff = root / "docs" / "agents" / "session-handoff.md"
    rel = str(handoff.relative_to(root)).replace("\\", "/")
    if mode_s == "create":
        handoff.parent.mkdir(parents=True, exist_ok=True)
        prior = handoff.read_text(encoding="utf-8") if handoff.exists() else ""
        handoff.write_text(_merge_pause_into_session_handoff(prior, wave_id), encoding="utf-8")
        if cache:
            cache.invalidate()
    return _response("dry_run" if mode_s == "dry_run" else "ok", {"wave_id": wave_id, "mode": mode_s, "path": rel, "written": mode_s == "create"}, next_tools=["wave_current"], usage="wave_current()")


def wave_review_response(root: Path, wave_id: str) -> dict[str, Any]:
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
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
    if mode_s not in {"dry_run", "create"}:
        return _response("error", {"wave_id": wave_id, "mode": mode}, diagnostics=[_diagnostic("invalid_arguments", f"Unsupported mode '{mode}'.")], next_tools=["wave_help"], usage="wave_help()")
    wave_md = _find_wave_md(root, wave_id)
    if wave_md is None:
        return _response("error", {"wave_id": wave_id}, diagnostics=[_diagnostic("wave_not_found", f"No wave found matching '{wave_id}'.", recovery_tools=["wave_list_waves"], recovery_usage="wave_list_waves()")], next_tools=["wave_list_waves"], usage="wave_list_waves()")
    garden_result = run_garden(root)
    lint_result = run_validate(root)
    text = wave_md.read_text(encoding="utf-8")
    statuses = [status.lower() for status in _CHANGE_STATUS_PATTERN.findall(text)]
    open_statuses = {"stub", "planned", "ready", "active"}
    unresolved = [s for s in statuses if s in open_statuses]
    diagnostics: list[dict[str, Any]] = []
    if not garden_result["passed"]:
        diagnostics.append(_diagnostic("docs_gardener_failed", "docs_gardener failed during close.", recovery_tools=["wave_garden", "wave_validate"], recovery_usage="wave_garden()"))
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
    if diagnostics:
        return _response("error", {"wave_id": wave_id, "mode": mode_s, "lint_passed": lint_result["passed"], "garden_passed": garden_result["passed"]}, diagnostics=diagnostics, next_tools=["wave_validate", "wave_current"], usage="wave_validate()")
    updated = False
    archive_rel = ""
    handoff_rel = ""
    if mode_s == "create":
        status_match = _STATUS_PATTERN.search(text)
        if status_match and status_match.group(1) != "closed":
            text = text[:status_match.start(1)] + "closed" + text[status_match.end(1):]
            if "Completed At:" not in text:
                import time
                text = text.replace("## Wave Summary", f"Completed At: {time.strftime('%Y-%m-%d')}\n\n## Wave Summary", 1)
            wave_md.write_text(text, encoding="utf-8")
            updated = True
            import time
            archive_dir = wave_md.parent / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_file = archive_dir / f"close-summary-{time.strftime('%Y%m%d')}.md"
            archive_file.write_text(
                (
                    f"# Wave Close Summary\n\n"
                    f"Wave: `{wave_id}`\n"
                    f"Closed At: {time.strftime('%Y-%m-%d')}\n\n"
                    f"## Change Statuses\n\n"
                    + "\n".join(f"- `{cid}`" for cid in _extract_change_ids_from_wave_text(text))
                    + "\n"
                ),
                encoding="utf-8",
            )
            archive_rel = str(archive_file.relative_to(root)).replace("\\", "/")
            handoff = root / "docs" / "agents" / "session-handoff.md"
            if handoff.exists():
                handoff.write_text(
                    "# Session Handoff\n\nOwner: wave-coordinator\nStatus: idle\n\n## Current Session\n\n**Active wave:** *(none)*\n",
                    encoding="utf-8",
                )
                handoff_rel = str(handoff.relative_to(root)).replace("\\", "/")
            if cache:
                cache.invalidate()
    return _response(
        "dry_run" if mode_s == "dry_run" else "ok",
        {"wave_id": wave_id, "mode": mode_s, "updated": updated, "archive_path": archive_rel, "handoff_path": handoff_rel},
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
# MCP server
# ---------------------------------------------------------------------------

def build_server(root: Path):
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("wavefoundry")
    index = WaveIndex(root)
    cache = McpRepoCache(root, index=index)

    # --- Search and retrieval ---

    @mcp.tool()
    def wave_help(goal: str = "", **kwargs: Any) -> dict[str, Any]:
        """Return a structured MCP workflow catalogue or a goal-specific recommended chain.

        Args:
            goal: Optional workflow goal, e.g. "plan_feature" or "inspect_wave".
        """
        bad = _ensure_no_extra_args("wave_help", kwargs)
        if bad is not None:
            return bad
        return wave_help_response(goal)

    @mcp.tool()
    def docs_search(query: str, kind: str = "", **kwargs: Any) -> dict[str, Any]:
        """Semantic search over docs, architecture, prompts, and seed chunks.

        Args:
            query: Natural language search query.
            kind: Optional filter — one of: doc, seed, architecture, prompt.
        """
        bad = _ensure_no_extra_args("docs_search", kwargs)
        if bad is not None:
            return bad
        return docs_search_response(index, query, kind)

    @mcp.tool()
    def code_search(query: str, language: str = "", **kwargs: Any) -> dict[str, Any]:
        """Semantic search over source code chunks.

        Args:
            query: Natural language or code description to search for.
            language: Optional filter — e.g. python, javascript, go.
        """
        bad = _ensure_no_extra_args("code_search", kwargs)
        if bad is not None:
            return bad
        return code_search_response(index, query, language)

    @mcp.tool()
    def seed_get(name: str, **kwargs: Any) -> dict[str, Any]:
        """Retrieve a framework seed prompt by name or partial slug.

        Args:
            name: Seed name or partial slug, e.g. "plan-feature" or "020-run-contract".
        """
        bad = _ensure_no_extra_args("seed_get", kwargs)
        if bad is not None:
            return bad
        return seed_get_response(index, name)

    # --- Wave inspection ---

    @mcp.tool()
    def wave_current(**kwargs: Any) -> dict[str, Any]:
        """Return the active wave ID, lifecycle status, and admitted changes."""
        bad = _ensure_no_extra_args("wave_current", kwargs)
        if bad is not None:
            return bad
        return wave_current_response(root, cache)

    @mcp.tool()
    def wave_list_waves(**kwargs: Any) -> dict[str, Any]:
        """List all waves with their ID, status, and change count."""
        bad = _ensure_no_extra_args("wave_list_waves", kwargs)
        if bad is not None:
            return bad
        return wave_list_waves_response(root, cache)

    @mcp.tool()
    def wave_list_plans(**kwargs: Any) -> dict[str, Any]:
        """List pending plan/change docs in docs/plans."""
        bad = _ensure_no_extra_args("wave_list_plans", kwargs)
        if bad is not None:
            return bad
        return wave_list_plans_response(root, cache)

    @mcp.tool()
    def wave_get_change(change_id: str, **kwargs: Any) -> dict[str, Any]:
        """Return the full text of a change doc by ID prefix.

        Args:
            change_id: Change ID or prefix, e.g. "12926" or "12926-feat".
        """
        bad = _ensure_no_extra_args("wave_get_change", kwargs)
        if bad is not None:
            return bad
        return wave_get_change_response(root, change_id)

    @mcp.tool()
    def wave_get_prompt(shortcut: str, **kwargs: Any) -> dict[str, Any]:
        """Return the full rendered prompt for a Wave Framework shortcut phrase.

        Args:
            shortcut: Shortcut phrase, e.g. "Prepare wave" or "Plan feature".
        """
        bad = _ensure_no_extra_args("wave_get_prompt", kwargs)
        if bad is not None:
            return bad
        return wave_get_prompt_response(root, shortcut, cache)

    @mcp.tool()
    def wave_map(address: str, **kwargs: Any) -> dict[str, Any]:
        """Resolve a doc:/code:/seed: anchor to repo path, trust label, excerpt, and index match flag.

        Args:
            address: Stable anchor from search results, e.g. doc:docs/README.md#intro or code:src/a.py:L10-L20.
        """
        bad = _ensure_no_extra_args("wave_map", kwargs)
        if bad is not None:
            return bad
        return wave_map_response(root, address, index)

    @mcp.tool()
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

    @mcp.tool()
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

    @mcp.tool()
    def wave_remove_change(wave_id: str, change_id: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Remove an admitted change from a wave's Changes section."""
        bad = _ensure_no_extra_args("wave_remove_change", kwargs)
        if bad is not None:
            return bad
        return wave_remove_change_response(root, wave_id, change_id, mode=mode, cache=cache)

    @mcp.tool()
    def wave_prepare(wave_id: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Transactional prepare check: validates docs and confirms wave has admitted changes."""
        bad = _ensure_no_extra_args("wave_prepare", kwargs)
        if bad is not None:
            return bad
        return wave_prepare_response(root, wave_id, mode=mode, cache=cache)

    @mcp.tool()
    def wave_pause(wave_id: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Write or preview a session handoff entry for an active wave."""
        bad = _ensure_no_extra_args("wave_pause", kwargs)
        if bad is not None:
            return bad
        return wave_pause_response(root, wave_id, mode=mode, cache=cache)

    @mcp.tool()
    def wave_review(wave_id: str, **kwargs: Any) -> dict[str, Any]:
        """Run review readiness checks for a wave and return structured lane summary."""
        bad = _ensure_no_extra_args("wave_review", kwargs)
        if bad is not None:
            return bad
        return wave_review_response(root, wave_id)

    @mcp.tool()
    def wave_close(wave_id: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Dry-run or close a wave after validation passes."""
        bad = _ensure_no_extra_args("wave_close", kwargs)
        if bad is not None:
            return bad
        return wave_close_response(root, wave_id, mode=mode, cache=cache)

    # --- Change creation ---

    def _new_change_response(kind: str, slug: str) -> dict[str, Any]:
        return wave_change_create_response(root, kind, slug, mode="create", cache=cache)

    @mcp.tool()
    def wave_change_create(kind: str, slug: str, mode: str = "dry_run", **kwargs: Any) -> dict[str, Any]:
        """Create or dry-run a scaffolded change doc using a lifecycle kind enum.

        Args:
            kind: One of bug, feat, enh, change, doc, debt, ref, task, maint, ops.
            slug: Kebab-case slug, e.g. "my-new-feature".
            mode: Either "dry_run" or "create".
        """
        bad = _ensure_no_extra_args("wave_change_create", kwargs)
        if bad is not None:
            return bad
        return wave_change_create_response(root, kind, slug, mode=mode, cache=cache)

    @mcp.tool()
    def wave_new_feature(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded feature change doc. Returns the ID and path.

        Args:
            slug: Kebab-case slug, e.g. "my-new-feature".
        """
        bad = _ensure_no_extra_args("wave_new_feature", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("feat", slug)

    @mcp.tool()
    def wave_new_bug(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded bug change doc. Returns the ID and path.

        Args:
            slug: Kebab-case slug, e.g. "login-redirect-broken".
        """
        bad = _ensure_no_extra_args("wave_new_bug", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("bug", slug)

    @mcp.tool()
    def wave_new_enhancement(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded enhancement change doc. Returns the ID and path.

        Args:
            slug: Kebab-case slug, e.g. "improve-search-ranking".
        """
        bad = _ensure_no_extra_args("wave_new_enhancement", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("enh", slug)

    @mcp.tool()
    def wave_new_refactor(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded refactor change doc. Returns the ID and path.

        Args:
            slug: Kebab-case slug, e.g. "extract-auth-module".
        """
        bad = _ensure_no_extra_args("wave_new_refactor", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("ref", slug)

    @mcp.tool()
    def wave_new_change(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded general change doc. Returns the ID and path.

        Args:
            slug: Kebab-case slug, e.g. "update-release-process".
        """
        bad = _ensure_no_extra_args("wave_new_change", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("change", slug)

    @mcp.tool()
    def wave_new_documentation(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded documentation change doc. Returns the ID and path.

        Args:
            slug: Kebab-case slug, e.g. "document-install-flow".
        """
        bad = _ensure_no_extra_args("wave_new_documentation", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("doc", slug)

    @mcp.tool()
    def wave_new_tech_debt(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded technical debt change doc. Returns the ID and path.

        Args:
            slug: Kebab-case slug, e.g. "reduce-indexer-coupling".
        """
        bad = _ensure_no_extra_args("wave_new_tech_debt", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("debt", slug)

    @mcp.tool()
    def wave_new_task(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded task change doc. Returns the ID and path.

        Args:
            slug: Kebab-case slug, e.g. "refresh-fixtures".
        """
        bad = _ensure_no_extra_args("wave_new_task", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("task", slug)

    @mcp.tool()
    def wave_new_maintenance(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded maintenance change doc. Returns the ID and path.

        Args:
            slug: Kebab-case slug, e.g. "rotate-generated-surfaces".
        """
        bad = _ensure_no_extra_args("wave_new_maintenance", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("maint", slug)

    @mcp.tool()
    def wave_new_operations(slug: str, **kwargs: Any) -> dict[str, Any]:
        """Create a scaffolded operations change doc. Returns the ID and path.

        Args:
            slug: Kebab-case slug, e.g. "update-release-checklist".
        """
        bad = _ensure_no_extra_args("wave_new_operations", kwargs)
        if bad is not None:
            return bad
        return _new_change_response("ops", slug)

    # --- Framework operations ---

    @mcp.tool()
    def wave_validate(**kwargs: Any) -> dict[str, Any]:
        """Run docs_lint against the project. Returns structured pass/fail with errors."""
        bad = _ensure_no_extra_args("wave_validate", kwargs)
        if bad is not None:
            return bad
        return wave_validate_response(root)

    @mcp.tool()
    def wave_garden(**kwargs: Any) -> dict[str, Any]:
        """Run docs_gardener to update Last verified dates. Returns summary."""
        bad = _ensure_no_extra_args("wave_garden", kwargs)
        if bad is not None:
            return bad
        return wave_garden_response(root, cache)

    @mcp.tool()
    def wave_sync_surfaces(**kwargs: Any) -> dict[str, Any]:
        """Run render_platform_surfaces to regenerate .claude/, .cursor/ hook configs."""
        bad = _ensure_no_extra_args("wave_sync_surfaces", kwargs)
        if bad is not None:
            return bad
        return wave_sync_surfaces_response(root, cache)

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

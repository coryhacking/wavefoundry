"""Index handlers: extracted response ownership."""
from __future__ import annotations

from lifecycle_gate_support import _diagnostic
from lifecycle_gate_support import _read_workflow_config
from lifecycle_gate_support import _repo_rel
from pathlib import Path
from public_contract import INDEX_FRESHNESS_STATES as _INDEX_FRESHNESS_STATES
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Mapping
from typing import Optional
import datetime
import json
import os
import publication_control
import re
import shlex
import time


BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS = 15.0


BACKGROUND_INDEX_LOCK_STALE_SECONDS = 60 * 60


_INDEX_BUILD_VERIFY_POLL_INTERVAL_SECONDS = 0.1


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


def _audit_build_summary(index_dir: Path) -> dict[str, Any]:
    """Bounded store read for the audit snapshot; {} on any failure.

    Operator review repair (1t59p cycle 1): this MUST stay on the
    read_build_summary path (layer scalars plus one COUNT). The per-file
    exporter materializes every per-file bookkeeping row, which is the
    O(indexed-files) cost this snapshot exists to avoid.
    """
    import server_impl

    try:
        iss = server_impl._load_script("index_state_store")
        return iss.read_build_summary(index_dir) or {}
    except Exception:
        return {}


def _audit_index_snapshot(root: Path, index_dir: Path) -> dict[str, Any]:
    """Bounded metadata-only index readiness for ``wf_audit`` (wave 1t59p).

    Reads ONLY the index control plane: the completed-build epoch (SQLite),
    SQLite layer/schema presence (never vector payloads), the bounded build
    summary (layer scalars plus one COUNT — never per-file rows), and the
    configured include-prefixes. It must never read vector payloads,
    load a model, hash the working tree, or materialize per-file store rows —
    those are the unbounded first-call costs this snapshot exists to avoid
    (the native-Windows field report). Freshness is therefore UNKNOWN here by
    construction; the explicit ``index_health`` tool owns full hash-walk
    verification.
    """
    import server_impl

    epoch_complete = server_impl._store_has_completed_build(index_dir)
    docs_present = server_impl._vector_layer_available(index_dir, "docs")
    code_present = server_impl._vector_layer_available(index_dir, "code")
    snapshot = _audit_build_summary(index_dir) if epoch_complete else {}
    try:
        code_prefixes = tuple(
            server_impl._load_script("indexer")._workflow_project_include_prefixes(root).get("code", ())
        )
    except Exception:
        code_prefixes = ()
    # Operator review repair (1t59p cycle 1): readiness derives from NO
    # per-file metadata — configuration is the scope authority. Prefixes
    # configured with no code vector layer is the 1p7is missing-layer signal
    # (e.g. an OOM-killed code embedding pass), read fail-closed.
    code_sources_in_scope = bool(code_prefixes)
    code_layer_missing = code_sources_in_scope and not code_present
    raw_chunker_versions = snapshot.get("chunker_versions", {})
    indexed_chunker_versions: dict[str, str] = (
        raw_chunker_versions if isinstance(raw_chunker_versions, dict) else {}
    )
    current_chunker_version = server_impl._read_chunker_version()
    chunker_version_mismatch = bool(
        current_chunker_version
        and epoch_complete
        and any(v != current_chunker_version for v in indexed_chunker_versions.values() if v)
    )
    missing_layers: list[str] = []
    if epoch_complete and not (docs_present or code_present):
        missing_layers.append("project")
    if code_layer_missing:
        missing_layers.append("code")
    metadata_ready = (
        epoch_complete and (docs_present or code_present) and not code_layer_missing
    )
    readiness_overview = _index_readiness_overview(
        missing_layers, [], docs_present or code_present, epoch_complete
    )
    return {
        "metadata_ready": metadata_ready,
        "epoch_complete": epoch_complete,
        "docs_present": docs_present,
        "code_present": code_present,
        "code_sources_in_scope": code_sources_in_scope,
        "code_layer_missing": code_layer_missing,
        "indexed_chunker_versions": indexed_chunker_versions,
        "current_chunker_version": current_chunker_version,
        "chunker_version_mismatch": chunker_version_mismatch,
        "readiness_overview": readiness_overview,
        # The honesty contract (1t59o AC-2): this snapshot never scanned the
        # working tree, so it must never be read as a freshness verdict.
        "freshness_checked": False,
        "freshness": "unknown",
        "freshness_verification_tool": "index_health",
    }


def _background_build_status(root: Path) -> str:
    """Return 'running', 'completed', or 'none' for the background code build.

    Uses a PID file written by _spawn_background_code_build to detect whether
    the process is still alive. 'completed' means the PID file exists but the
    process has already exited (build finished or crashed).
    """
    import server_impl

    pid_path = root / ".wavefoundry" / "index" / "background-build.pid"
    if not pid_path.exists():
        return "none"
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return "completed"
    # Wave 1p6d6: route through the guarded _pid_is_running (Windows-correct via tasklist)
    # instead of an inline os.kill that misjudges liveness on native Windows.
    return "running" if server_impl._pid_is_running(pid) else "completed"


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


def _index_dir_for_layer(root: Path, layer: str = "project") -> Path:
    # Wave 1p4ww: single project index — the framework layer is folded in.
    if layer == "project":
        return root / ".wavefoundry" / "index"
    raise ValueError(f"Unsupported layer '{layer}'.")


def _epoch_token(root: Path) -> "tuple[str, int] | None":
    """The reader epoch token (1sed6): ``(attempt_id, generation)`` of the
    COMPLETE build epoch, or None when the index is not servable (absent,
    uninitialized, mid-build, interrupted, unreadable). Cheap: one short
    read-only query, never held across the operation."""
    import server_impl

    try:
        iss = server_impl._load_script("index_state_store")
        return iss.build_epoch_token(root / ".wavefoundry" / "index")
    except Exception:
        return None


def _epoch_state(root: Path, *, propagate_runtime_errors: bool = False) -> "tuple[str, str, int] | None":
    """The ABA-proof consistency token (1sed6 review fix): the full build-state
    row ``(attempt_id, status, generation)`` in ANY state; None only when the
    store is absent/unreadable. Used for the pre/post seqlock compare at every
    tool — unlike the complete-only ``_epoch_token``, it distinguishes
    ``building A`` from ``building B``, so an operation that straddled a
    finalize + re-fence (both endpoints "not ready") is still discarded.

    Registered seqlock boundaries request typed runtime failures so an unusable
    runtime cannot be mistaken for a legitimately missing or building epoch.
    """
    import server_impl

    try:
        iss = server_impl._load_script("index_state_store")
        return iss.build_epoch_state_token(root / ".wavefoundry" / "index")
    except Exception as exc:
        if propagate_runtime_errors:
            import sqlite_runtime as runtime
            if isinstance(exc, (runtime.RuntimeUnavailable, runtime.StorageRecoveryRequired)):
                raise
        return None


_FRESHNESS_TTL_SECONDS = 5.0


_FRESHNESS_CACHE: "dict[str, tuple[float, object, dict]]" = {}


_FRESHNESS_CURRENT, _FRESHNESS_STALE, _FRESHNESS_UNKNOWN = _INDEX_FRESHNESS_STATES


def _index_freshness_verdict(root: Path) -> dict[str, Any]:
    """Cheap cached three-state freshness verdict (wave 1seav / 1sbxq).

    ``{"state": "current" | "stale" | "unknown", "reason": str}`` — replaces
    code_ask's per-call ``_layer_health`` O(corpus) hash walk. The cache has
    BOTH invalidation axes (P0 plan repair): a root-scoped seconds-scale TTL
    (the build generation only advances at finalization, so TTL bounds
    edit-detection latency between builds) AND the 1sed7 epoch state token
    (any build transition — publish, fence — refreshes immediately without
    waiting out the TTL). Exceptions and undeterminable states are "unknown",
    never silently "current" (the 1sbfj honesty rule).
    """
    import server_impl

    key = str(root)
    now = time.monotonic()
    tok = _epoch_state(root)
    cached = _FRESHNESS_CACHE.get(key)
    if cached is not None and now < cached[0] and cached[1] == tok:
        return cached[2]
    try:
        idx = server_impl._load_script("indexer")
        result = idx.project_layer_freshness(root)
        stale = result.get("stale")
        state = (
            _FRESHNESS_UNKNOWN if stale is None
            else (_FRESHNESS_STALE if stale else _FRESHNESS_CURRENT)
        )
        verdict = {"state": state, "reason": str(result.get("reason", ""))}
    except Exception as exc:  # noqa: BLE001 - honesty rule
        verdict = {"state": _FRESHNESS_UNKNOWN, "reason": f"freshness check failed: {exc}"}
    _FRESHNESS_CACHE[key] = (now + _FRESHNESS_TTL_SECONDS, tok, verdict)
    return verdict


def _index_rebuilding_response(tool: str, payload: dict) -> dict[str, Any]:
    """Structured not-ready/rebuilding result (1sed6 AC-4): the index has no
    complete epoch, or it changed while the operation ran — results (if any)
    were discarded rather than served as current."""
    import server_impl

    payload = dict(payload)
    # AC-3 (review fix): the search_mode/fallback_reason contract is carried
    # on EVERY response from the gated search tools, including refusals.
    payload.setdefault("search_mode", None)
    payload.setdefault("fallback_reason", server_impl._REASON_INDEX_NOT_READY)
    payload.setdefault("results", [])
    response = server_impl._response(
        "error", payload,
        diagnostics=[_diagnostic(
            server_impl._REASON_INDEX_NOT_READY,
            "The semantic index has no completed build epoch (building, interrupted, "
            "or not yet built) or it changed while this query ran — results were "
            "discarded rather than served from a mixed index state. Check "
            "index_build_status; retry after the build completes.",
            recovery_tools=["index_build_status", "index_build"],
            recovery_usage="index_build_status()",
        )],
        next_tools=["index_build_status"],
        usage="index_build_status()",
    )
    return server_impl._attach_retrieval_failure_context(tool, response)


def _index_runtime_failure_response(tool: str, root: Path, payload: dict, exc: Exception) -> dict[str, Any]:
    """Discard the complete operation when either epoch probe cannot use storage."""
    import server_impl

    payload = {**payload, "search_mode": None, "fallback_reason": server_impl._REASON_QUERY_FAILED,
               "results": []}
    code = getattr(exc, "code", server_impl._REASON_QUERY_FAILED)
    compatibility_failure = code in {
        "index_runtime_stale", "index_version_newer", "index_compatibility_unproven"}
    recovery = ("Restart the affected Wavefoundry host, then call index_health(). "
                "Preserve the index; do not rebuild it with this older runtime."
                if compatibility_failure else "index_health()")
    message = server_impl._bounded_failure_detail(root, exc)
    if not compatibility_failure:
        message = ("Semantic index runtime is unusable: " + message
                   + " Results were discarded; resolve the runtime or filesystem issue and retry.")
    response = server_impl._response(
        "error", payload,
        diagnostics=[_diagnostic(
            code, message,
            recovery_tools=["index_health"], recovery_usage=recovery,
        )],
        next_tools=["index_health"], usage=recovery,
    )
    return server_impl._attach_retrieval_failure_context(tool, response)


def _read_index_rebuild_stats(root: Path, layer: str) -> dict[str, Any]:
    import server_impl

    index_dir = _index_dir_for_layer(root, layer)

    meta: dict[str, Any] = {}
    doc_chunks = 0
    code_chunks = 0

    if True:
        try:
            meta = server_impl._store_build_meta(index_dir)
        except (OSError, json.JSONDecodeError):
            meta = {}

    try:
        counts = server_impl._load_script("sqlite_vector_store").layer_counts(index_dir)
        doc_chunks, code_chunks = counts.get("docs", 0), counts.get("code", 0)
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
    import server_impl

    import subprocess
    scripts_dir = Path(server_impl.__file__).resolve().parent
    index_dir = _index_dir_for_layer(root, layer)
    if not server_impl._store_has_completed_build(index_dir):
        return False
    if layer == "project" and content in {"all", "graph"}:
        # setup_index.py (all) and graph-only mode don't support --dry-run; treat as always stale
        return False
    else:
        check_content = content
    cmd = [
        server_impl._preferred_python(), str(scripts_dir / "indexer.py"),
        "--root", str(root), "--content", check_content, "--dry-run",
    ]
    # Project layer: indexer.py reads workflow-config include-prefixes itself.
    try:
        result = server_impl._mcp_subprocess_run(
            cmd, capture_output=True, cwd=str(root),
            env={**os.environ, "PROJECT_ROOT": str(root)},
            timeout=30,
        )
        return result.returncode == 0 and "build_index: index is up to date" in (result.stdout + result.stderr)
    except Exception:
        return False


def _index_build_state_path(root: Path, layer: str = "project") -> Path:
    return root / ".wavefoundry" / "index" / "index-build.json"


def _clear_index_build_state(root: Path, layer: str) -> None:
    try:
        _index_build_state_path(root, layer).unlink()
    except OSError:
        pass


def _index_build_log_path(root: Path, layer: str = "project") -> Path:
    return root / ".wavefoundry" / "logs" / "project-index-build.log"


def _project_background_build_log_path(root: Path) -> Path:
    return root / ".wavefoundry" / "logs" / "project-background-build.log"


def _index_build_stats_path(root: Path, layer: str = "project") -> Path:
    return root / ".wavefoundry" / "index" / "index-build-stats.json"


def _graph_health_summary(root: Path) -> dict[str, Any]:
    """Wave 13129 (1316n): summary of graph presence + last-built per layer.

    Operators reading index_health get this alongside semantic-layer
    readiness so the "did my rebuild touch graph?" question is answerable
    inline without inspecting timestamps manually.

    Returns dict with shape:
        {
            "project": {"present": bool, "last_built_at": str | None,
                        "node_count": int | None, "edge_count": int | None,
                        "generation": int, "component": str},
        }

    Wave 1p4ww: single project graph — the framework layer is folded in.
    Wave 1xny6: served from the generation-bound snapshot. ``last_built_at``
    is the payload's own ``generated_at`` rather than an artifact mtime, and
    ``component`` names the database component instead of a deleted filename —
    a read-only health call opens nothing under the retired graph folder.
    """
    import server_impl

    gs = server_impl._graph_snapshot_module()
    summary: dict[str, Any] = {}
    for layer in ("project",):
        try:
            snapshot = gs.acquire(root, layer)
        except Exception:
            snapshot = None
        component = gs.component_path(gs.GRAPH_COMPONENT)
        if snapshot is None or not snapshot.present:
            summary[layer] = {
                "present": False, "last_built_at": None,
                "node_count": None, "edge_count": None,
                "generation": 0 if snapshot is None else snapshot.generation,
                "state": "failed" if snapshot is None else snapshot.state,
                "diagnostic": None if snapshot is None else snapshot.diagnostic,
                "component": component,
            }
            continue
        payload = snapshot.graph or {}
        nodes = payload.get("nodes") or []
        edges = payload.get("edges") or []
        counts = payload.get("counts") or {}
        summary[layer] = {
            "present": True,
            "last_built_at": str(payload.get("generated_at") or "") or None,
            "node_count": len(nodes) if isinstance(nodes, list) else counts.get("nodes"),
            "edge_count": len(edges) if isinstance(edges, list) else counts.get("edges"),
            "generation": snapshot.generation,
            "graph_generation": snapshot.graph_content_generation,
            "component": component,
        }
    return summary


def _chunk_index_coverage(
    root: Path, tables: "tuple[str, ...]" = ("docs", "code"),
) -> dict[str, Any]:
    """Compare native vector and registry populations exactly without reading payloads.

    SQLite chunk IDs are unique. Even one missing vector is a real coverage
    defect; the legacy duplicate-row tolerance no longer applies.
    """
    import server_impl

    coverage: dict[str, Any] = {}
    index_dir = root / ".wavefoundry" / "index"
    try:
        iss = server_impl._load_script("index_state_store")
        vectors = server_impl._load_script("sqlite_vector_store")
        counts = vectors.layer_counts(index_dir)
        conn = iss.open_read_only(index_dir)
        if conn is None:
            return coverage
        try:
            populations = {table: vectors.vector_integrity(conn, table) for table in tables}
        finally:
            conn.close()
        for table_name in tables:
            population = populations[table_name]
            if not any(population.values()) and not vectors.layer_available(index_dir, table_name):
                continue
            vector_rows = int(counts.get(table_name, 0))
            registry_rows = iss.registry_chunk_count(index_dir, table_name)
            if registry_rows is None:
                continue
            covered = (vector_rows == registry_rows and not population["missing_vectors"]
                       and not population["orphan_vectors"])
            entry: dict[str, Any] = {
                "vector_rows": vector_rows,
                "registry_rows": int(registry_rows),
                "canonical_rows": population["canonical"],
                "raw_vector_rows": population["vectors"],
                "missing_vectors": population["missing_vectors"],
                "orphan_vectors": population["orphan_vectors"],
                "covered": covered,
            }
            # 1wngv: same-ID/distinct-content census recorded at the last
            # derived rebuild — non-zero means the registry/FTS layer holds
            # one row per colliding id, so derived-state coverage is not
            # complete for that content even when the counts above match.
            if hasattr(iss, "chunk_id_collision_counts"):
                _coll, _sample = iss.chunk_id_collision_counts(index_dir, table_name)
                if _coll:
                    entry["id_collisions"] = int(_coll)
                    if _sample:
                        entry["id_collision_sample"] = _sample[:5]
            coverage[table_name] = entry
    except Exception:  # noqa: BLE001 - advisory only
        pass
    return coverage


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


def _refresh_index_build_stats_from_finished_log(
    root: Path,
    layer: str,
    *,
    log_path: Optional[Path] = None,
    state_path: Optional[Path] = None,
    fallback_stats: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """Persist build stats from a finished build log, if available."""
    import server_impl

    candidate_log = log_path or _index_build_log_path(root, layer)
    parsed = server_impl._parse_finished_build_stats_from_log(
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
    import server_impl

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
        parsed = server_impl._parse_finished_build_stats_from_log(
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
    """Return True if a index_build-spawned process is currently running."""
    import server_impl

    state_path = _index_build_state_path(root, layer)
    if not state_path.exists():
        return False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    pid = state.get("pid")
    if isinstance(pid, int) and server_impl._pid_is_running(pid):
        return True
    # Brief throttle covers the Popen → indexer lock-acquire window (~1-2s cold start).
    # Reuses BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS (15s) — same race condition.
    started_at = state.get("started_at")
    if isinstance(started_at, (int, float)):
        import time
        if (time.time() - float(started_at)) < BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS:
            return True
    return False


def _check_index_writer_current(root: Path) -> None:
    """Preflight local work scheduling; publication rechecks in its transaction."""
    # Reject a stale coordinator before it schedules work, including map/FTS
    # entry points. The child still rechecks under its publication transaction.
    import index_compatibility
    index_compatibility.ensure_runtime_current()
    import index_state_store
    conn = index_state_store.open_read_only(root / ".wavefoundry" / "index")
    if conn is not None:
        try:
            index_compatibility.check_connection(conn)
        finally:
            conn.close()


def run_index_rebuild(
    root: Path,
    *,
    content: str = "docs",
    full: bool = False,
    rechunk: bool = False,
    layer: str = "project",
) -> dict:
    """Spawn indexer.py as a background process and return immediately with pre-build stats.

    The indexer runs detached; stdout/stderr are written to ``index-build.log`` in the
    index directory. Exposed as MCP ``index_build`` with ``mode='update'|'rebuild'``.
    """
    import server_impl

    import subprocess
    import time
    from public_contract import INDEX_BUILD_CONTENT_VALUES
    if content not in INDEX_BUILD_CONTENT_VALUES:
        raise ValueError(f"Unsupported content '{content}'.")
    # Wave 1p4ww: single project index — the framework layer is folded in.
    if layer != "project":
        raise ValueError(f"Unsupported layer '{layer}'.")

    _check_index_writer_current(root)

    # Wave 1p601: content="map" is a map-only refresh — run the ~0.09s codebase
    # map generator (change-only/idempotent) WITHOUT a full index rebuild. No
    # subprocess, fail-safe (never raises into the tool).
    if content == "map":
        regenerated = False
        try:
            gen = server_impl._load_script("gen_codebase_map")
            regenerated = bool(gen.generate_safe(root, force=True))
        except Exception:
            regenerated = False
        out_rel = "docs/references/codebase-map.md"
        return {
            "passed": True,
            "already_running": False,
            "up_to_date": False,
            "content": "map",
            "full": False,
            "mode": "map-refresh",
            "index_scope": "codebase_map_only",
            "layer": layer,
            "regenerated": regenerated,
            "notice": (
                f"Codebase map refreshed → {out_rel}."
                if regenerated
                else "Codebase map refresh skipped (no artifacts yet or generator unavailable)."
            ),
            "map_path": out_rel,
        }

    # Wave 1sc7c (1sek8): content="fts" — from-scratch rebuild of the DERIVED
    # chunk state (FTS5 lexical tables + chunk registry) from the
    # canonical SQLite chunks. Embedding-free and in-process (seconds):
    # the clean recovery for an under-covered/corrupt lexical layer without a
    # semantic build. Runs under the whole-index build lock.
    if content == "fts":
        idx_mod = server_impl._load_script("indexer")
        index_dir = root / ".wavefoundry" / "index"
        _fts_busy = {
            "passed": True,
            "already_running": True,
            "content": "fts",
            "mode": "derived-rebuild",
            "index_scope": "derived_chunk_state_only",
            "layer": layer,
            "notice": "Another build holds the index lock — retry when it finishes.",
        }
        if _index_build_active(root, layer):
            return _fts_busy
        _fts_t0 = time.monotonic()
        try:
            with idx_mod._index_build_lock(index_dir):
                tables = idx_mod.rebuild_derived_chunk_state(index_dir)
        except idx_mod.IndexBuildAlreadyRunning:
            return _fts_busy
        _fts_ms = round((time.monotonic() - _fts_t0) * 1000)
        # Independent-review N1: the restore-only refusal is a TOP-LEVEL
        # {"error": str} — it must fail this response, not slip past the
        # dict-only comprehensions as passed=True.
        if isinstance(tables.get("error"), str):
            return {
                "passed": False,
                "already_running": False,
                "content": "fts",
                "mode": "derived-rebuild",
                "index_scope": "derived_chunk_state_only",
                "layer": layer,
                "error": tables["error"],
                "duration_ms": _fts_ms,
                "notice": tables["error"],
            }
        rows = {k: v.get("rows_written") for k, v in tables.items() if isinstance(v, dict)}
        errors = {k: v.get("error") for k, v in tables.items()
                  if isinstance(v, dict) and v.get("error")}
        return {
            "passed": not errors,
            "already_running": False,
            "content": "fts",
            "full": True,
            "mode": "derived-rebuild",
            "index_scope": "derived_chunk_state_only",
            "layer": layer,
            "tables": tables,
            "duration_ms": _fts_ms,
            "notice": (
                "Derived chunk state (FTS5 + registry) rebuilt from SQLite chunks: "
                + ", ".join(f"{k}={v}" for k, v in rows.items())
                if rows and not errors else
                "FTS rebuild completed with issues — see tables."
            ),
        }

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
            "mode": "rebuild" if full else ("rechunk" if rechunk else "update"),
            "index_scope": "full_rebuild" if full else ("rechunk_reuse" if rechunk else "incremental_update"),
            "layer": layer,
            "stats": pre_stats,
            "log": str(log_path),
        }

    scripts_dir = Path(server_impl.__file__).resolve().parent
    python_exec = server_impl._preferred_python()

    if layer == "project" and content == "all":
        script = scripts_dir / "setup_index.py"
        cmd = [python_exec, str(script), "--root", str(root), "--include-code", "--verbose"]
    elif layer == "project" and content == "graph":
        script = scripts_dir / "setup_index.py"
        cmd = [python_exec, str(script), "--root", str(root), "--graph-only", "--verbose"]
    else:
        script = scripts_dir / "indexer.py"
        cmd = [python_exec, str(script), "--root", str(root), "--content", content, "--verbose"]
    # Project layer (docs/code): indexer.py reads workflow-config include-prefixes itself.
    if full:
        cmd.append("--full")
    # Wave 1p4n4 (mode='rechunk'): re-chunk all files + reuse embeddings by hash, no version change.
    # Meaningful only for chunked content (graph has no embeddings to reuse).
    if rechunk and content in {"docs", "code", "all"}:
        cmd.append("--rechunk")

    pre_stats = _read_index_rebuild_stats(root, layer)
    _index_label = {"docs": "docs/seed", "code": "code", "all": "docs/seed + code"}.get(content, content)
    _file_count = pre_stats.get("files_total", "?")

    # rechunk must NOT short-circuit on an up-to-date index — re-chunking unchanged files is the point.
    if not full and not rechunk and _index_is_up_to_date(root, layer, content):
        # Paths excluded by workflow configuration can outlive walk bookkeeping.
        # Reaping belongs exclusively to the indexer's zero-change maintenance
        # path (read-only plan, then fenced execution under the build lock).
        # This up-to-date response must never mutate storage itself.
        reaped_uptd: dict[str, int] = {"docs": 0, "code": 0, "total": 0}
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
            "stranded_rows_reaped": reaped_uptd.get("total", 0),
            "stranded_rows_reaped_by_table": reaped_uptd,
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

    state_path.parent.mkdir(parents=True, exist_ok=True)
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
                    "WAVEFOUNDRY_TIMESTAMP_LOGS": "1",
                },
            }
        if os.name == "nt":
            kwargs["creationflags"] = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | server_impl._windows_no_window_flag()
            )
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

    if content == "graph":
        notice = (
            f"Rebuilding graph index ({layer} layer) — extracting nodes/edges and re-clustering communities. "
            f"No semantic embedding; duration depends on corpus size and graph work. "
            f"Watch progress: {log_path}"
        )
    elif full:
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

    mode_label = "rebuild" if full else ("rechunk" if rechunk else "update")
    # Wave 1p2q3 (1p2w5): synchronous post-Popen verification window. The
    # subprocess can die in its first few hundred ms with "lock file busy"
    # written to the log; the prior code returned `passed: True` immediately
    # after Popen and the caller got no signal that the rebuild silently
    # failed. We poll briefly (≤1.5s, sampled every 100ms): a process that
    # survives the window has acquired its locks and is in `build_index`
    # proper. If the process exited inside the window with a non-zero exit
    # code, surface the failure to the caller.
    import time as _time
    _verify_deadline = _time.monotonic() + server_impl._INDEX_BUILD_VERIFY_TIMEOUT_SECONDS
    _early_exit_code: int | None = None
    while _time.monotonic() < _verify_deadline:
        _poll_result = proc.poll()
        # Real `subprocess.Popen.poll()` returns Optional[int]: None means
        # "still running", an int is the exit code. We type-check here both
        # to guard against test mocks that don't configure poll() and to
        # tolerate any future Popen wrapper returning richer objects.
        if isinstance(_poll_result, int):
            _early_exit_code = _poll_result
            break
        _time.sleep(_INDEX_BUILD_VERIFY_POLL_INTERVAL_SECONDS)
    if _early_exit_code is not None and _early_exit_code != 0:
        # Subprocess died inside the verification window. Read the log to
        # surface a useful diagnostic to the caller.
        log_tail = ""
        try:
            log_tail = log_path.read_text(encoding="utf-8", errors="replace")[-2048:]
        except OSError:
            pass
        lock_busy = (
            "Another index build is already running" in log_tail
            or "lock file busy" in log_tail
        )
        diagnostic_code = "build_skipped_lock_busy" if lock_busy else "index_build_subprocess_failed"
        # Look up the lock-holder PID so the caller can decide whether to
        # wait or to clean up after a known-dead holder.
        lock_owner_pid: int | None = None
        try:
            import importlib.util as _importlib_util
            _indexer_spec = _importlib_util.spec_from_file_location(
                "wavefoundry_indexer_for_lock_owner",
                Path(server_impl.__file__).resolve().parent / "indexer.py",
            )
            if _indexer_spec is not None and _indexer_spec.loader is not None:
                _indexer_mod = _importlib_util.module_from_spec(_indexer_spec)
                _indexer_spec.loader.exec_module(_indexer_mod)
                _lock_path = root / ".wavefoundry" / "index" / "index-build.lock"
                _meta = _indexer_mod.read_index_build_lock_metadata(_lock_path)
                if isinstance(_meta, dict) and isinstance(_meta.get("pid"), int):
                    lock_owner_pid = int(_meta["pid"])
        except Exception:
            pass
        return {
            "passed": False,
            "already_running": False,
            "build_failed_early": True,
            "exit_code": _early_exit_code,
            "lock_owner_pid": lock_owner_pid,
            "diagnostic_code": diagnostic_code,
            "notice": (
                f"Index rebuild subprocess (pid {proc.pid}) exited within {1.5}s with code "
                f"{_early_exit_code}"
                + (f" — lock held by pid {lock_owner_pid}." if lock_busy and lock_owner_pid else ".")
            ),
            "content": content,
            "full": full,
            "mode": mode_label,
            "index_scope": "full_rebuild" if full else ("rechunk_reuse" if rechunk else "incremental_update"),
            "layer": layer,
            "stats": pre_stats,
            "log": str(log_path),
            "log_tail": log_tail,
            "pid": proc.pid,
        }
    return {
        "passed": True,
        "already_running": False,
        "notice": notice,
        "content": content,
        "full": full,
        "mode": mode_label,
        "index_scope": "full_rebuild" if full else ("rechunk_reuse" if rechunk else "incremental_update"),
        "layer": layer,
        "stats": pre_stats,
        "log": str(log_path),
        "pid": proc.pid,
    }


def _index_chunk_matching_address(index: server_impl.WaveIndex, address: str, parsed: dict[str, Any]) -> Optional[dict[str, Any]]:
    import server_impl

    try:
        index._ensure_loaded()
    except (server_impl.IndexNotReadyError, OSError, ValueError, Exception):
        return None
    scheme = parsed["scheme"]
    want = address.strip()
    path = (parsed.get("path") or "").replace("\\", "/").replace("'", "''")
    # Determine which SQLite layer(s) to read and which prefix(es) to match.
    if scheme == "code":
        table_prefixes = [(getattr(index, "_code_vector_layer", None), "code")]
    elif scheme == "seed":
        table_prefixes = [
            (getattr(index, "_docs_vector_layer", None), "seed"),
            (getattr(index, "_docs_vector_layer", None), "doc"),
        ]
    else:
        table_prefixes = [(getattr(index, "_docs_vector_layer", None), "doc")]
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
            rows = server_impl._load_script("sqlite_vector_store").payload_rows(
                index.index_dir, table, predicate=where
            )
        except Exception:
            rows = []
        for row in rows:
            ch = {k: v for k, v in row.items() if k != "vector"}
            if server_impl._result_id(prefix, ch) == want:
                return ch
    return None


def _background_refresh_state_path(root: Path, layer: str = "project") -> Path:
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


def _background_refresh_active(state_path: Path) -> bool:
    # Reap server-owned children before consulting their durable PID record.
    # Otherwise a completed POSIX child remains os.kill-alive as a zombie and
    # this predicate prevents the monitor from ever reaching the launcher that
    # historically owned the reap sweep.
    import server_impl

    _reap_background_build_pids()
    index_dir = state_path.parent
    # The whole-index OS lock is the cross-process authority. It can be held
    # before a child has written its background state or acquired a per-table
    # lock, so consult it before using either weaker carrier to permit a spawn.
    try:
        root = index_dir.parent.parent
        if _index_build_lock_info(root).get("held") is True:
            return True
    except Exception:  # noqa: BLE001
        # The indexer's acquire-time lock remains the final single-flight
        # authority if this observational probe is unavailable.
        pass

    state = _load_background_refresh_state(state_path)
    pid = state.get("pid")
    started_at = state.get("started_at")
    if isinstance(pid, int) and server_impl._pid_is_running(pid):
        # The state file outlives both the child and MCP hot reload. Confirm
        # that an unregistered live/reused PID is actually an index builder;
        # the indexer's classifier is already zombie-, PID-reuse-, and
        # native-Windows-aware. Probe failure remains fail-safe ("live").
        if pid in _BACKGROUND_BUILD_PIDS:
            return True
        try:
            indexer_module = server_impl._load_script("indexer")
            owner = indexer_module.classify_index_build_lock_owner(
                {"pid": pid, "started_at": started_at}
            )
        except Exception:  # noqa: BLE001
            return True
        if owner == "live":
            try:
                cmdline = indexer_module._process_cmdline(pid)
            except Exception:  # noqa: BLE001
                return True
            if cmdline is None:
                return True
            if _index_builder_cmdline_targets_root(cmdline, root):
                return True
    # Short throttle covers the brief window between Popen() and the indexer acquiring
    # its build lock (~1-2 seconds on a cold start).
    if isinstance(started_at, (int, float)):
        import time
        if (time.time() - float(started_at)) < BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS:
            return True
    return False


def _index_builder_cmdline_targets_root(cmdline: str, root: Path) -> bool:
    """Whether a readable index-builder command explicitly targets ``root``.

    Persisted background PIDs can be recycled by another Wavefoundry indexer.
    The generic owner classifier proves the executable class; this second
    check binds that live process to the repository whose state file named it.
    """

    try:
        tokens = [
            token.strip("\"'")
            for token in shlex.split(cmdline, posix=os.name != "nt")
        ]
    except ValueError:
        return True  # unreadable quoting is a probe failure: preserve single-flight safety
    raw_root: str | None = None
    for index, token in enumerate(tokens):
        if token == "--root" and index + 1 < len(tokens):
            raw_root = tokens[index + 1]
            break
        if token.startswith("--root="):
            raw_root = token.partition("=")[2]
            break
    if not raw_root:
        return False
    if os.name == "nt":
        import ntpath

        return ntpath.normcase(ntpath.normpath(raw_root)) == ntpath.normcase(
            ntpath.normpath(str(root))
        )
    try:
        return Path(raw_root).resolve(strict=False) == root.resolve(strict=False)
    except OSError:
        return False


_BACKGROUND_BUILD_PIDS: set[int] = set()


def _register_background_build_pid(pid: int) -> None:
    if os.name == "nt" or not isinstance(pid, int) or pid <= 0:
        return
    _BACKGROUND_BUILD_PIDS.add(pid)


def _reap_background_build_pids() -> None:
    """Reap finished server-launched background builds so they don't linger as zombies.

    POSIX-only. Only ever waits on PIDs this server launched; a PID that is not our child (already
    reaped/reparented) raises ChildProcessError, treated as gone. Never blocks (WNOHANG); a
    still-running child stays registered for a later sweep."""
    if os.name == "nt":
        return
    for pid in list(_BACKGROUND_BUILD_PIDS):
        try:
            ended_pid, _ = os.waitpid(pid, os.WNOHANG)
        except (ChildProcessError, OSError):
            _BACKGROUND_BUILD_PIDS.discard(pid)  # not our child / already reaped / gone
            continue
        if ended_pid == pid:
            _BACKGROUND_BUILD_PIDS.discard(pid)  # reaped — no longer a zombie


_DASHBOARD_CHILD_PIDS: set[int] = set()


def _register_dashboard_child_pid(pid: int) -> None:
    if os.name == "nt" or not isinstance(pid, int) or pid <= 0:
        return
    _DASHBOARD_CHILD_PIDS.add(pid)


def _reap_dashboard_child_pids() -> None:
    """Reap finished server-launched dashboard children so they don't linger as zombies.

    POSIX-only, WNOHANG, and scoped to PIDs this server itself spawned (never a bare/recycled PID) —
    mirrors ``_reap_background_build_pids``. A still-running dashboard stays registered for a later
    sweep; a PID that is not (or no longer) our child raises ChildProcessError and is dropped."""
    if os.name == "nt":
        return
    for pid in list(_DASHBOARD_CHILD_PIDS):
        try:
            ended_pid, _ = os.waitpid(pid, os.WNOHANG)
        except (ChildProcessError, OSError):
            _DASHBOARD_CHILD_PIDS.discard(pid)  # not our child / already reaped / gone
            continue
        if ended_pid == pid:
            _DASHBOARD_CHILD_PIDS.discard(pid)  # reaped — no longer a zombie


def _start_background_index_refresh(root: Path, layer: str = "project") -> bool:
    # Wave 1p4ww: single project index — the framework layer is folded in.
    import server_impl

    if layer != "project":
        return False
    # Publication upgrades require a truly quiet repository. Check before
    # reaping, creating the state directory, or spawning the native indexer.
    if publication_control.native_publication_block_reason(
        root, "background_index_refresh"
    ) is not None:
        return False
    import sqlite_runtime as runtime
    try:
        _check_index_writer_current(root)
    except (runtime.RuntimeUnavailable, runtime.StorageRecoveryRequired) as exc:
        server_impl._wf_log(f"[wavefoundry] background index refresh refused: {exc}")
        return False
    # Wave 1p98u: reap any prior finished background builds before launching another, so server-owned
    # zombies don't accumulate across a session (each new refresh sweeps the previous ones).
    _reap_background_build_pids()
    # Wave 1rswx: sweep finished dashboard children on this frequently-hit path too, so a dashboard that
    # dies mid-session is reaped during ordinary editing — not left until the next explicit
    # wf_*_dashboard call or server exit (readiness amendment / AC-4).
    _reap_dashboard_child_pids()
    state_path = _background_refresh_state_path(root, layer)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    if _background_refresh_active(state_path):
        return False
    indexer = root / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
    if not indexer.exists():
        return False
    import subprocess
    cmd = [
        server_impl._preferred_python(), str(indexer), "--root", str(root),
        "--content", "all",
    ]
    # The project index contains both semantic layers. Passing ``all`` is
    # required: indexer.py otherwise defaults to docs-only even though it reads
    # both workflow-config include-prefix lists. This matches the Claude
    # turn-end flusher and keeps code embeddings current on monitor recovery.
    # Wave 1p6d6: detach the background reindex correctly per-OS — on Windows start_new_session
    # is a no-op, so without creationflags the child stays in the server's process group and dies
    # with it. Mirror the three sibling spawns (server_impl.py:3487, :6654, setup_index.py).
    detach_kwargs = {}
    if os.name == "nt":
        detach_kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | server_impl._windows_no_window_flag()
        )
    else:
        detach_kwargs["start_new_session"] = True
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,  # never inherit the JSON-RPC stdin (sibling-consistent; wave 1p88t)
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(root),
        close_fds=os.name != "nt",
        **detach_kwargs,
    )
    import time
    # Wave 1p98u: track this server-launched build so a later spawn reaps it once it exits (POSIX),
    # instead of leaving a defunct PID that makes the index-build lock read as "live".
    _register_background_build_pid(proc.pid)
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
    # Wave 1p4ww: framework seeds + README are folded into the project docs index, so a
    # change to either triggers the single project refresh (no separate framework layer).
    fold_prefixes = (".wavefoundry/framework/seeds/", ".wavefoundry/framework/README.md")
    project_needed = any(
        _indexable_refresh_path(path)
        and (path.startswith("docs/") or path.startswith(fold_prefixes))
        for path in normalized_paths
    )
    return {
        "project": _start_background_index_refresh(root, "project") if project_needed else False,
    }


def _index_dir_size(index_dir: Path) -> Optional[dict[str, Any]]:
    """Wave 1p9a9: total + top-level component on-disk size of the index dir. Read-only, best-effort;
    a missing dir or any stat error yields ``None`` (never raises). The per-component breakdown
    (``index.sqlite`` / ``memory-state.sqlite`` / …) makes storage growth diagnosable."""
    import server_impl

    try:
        if not index_dir.exists():
            return None
        components: dict[str, int] = {}
        total = 0
        for entry in sorted(index_dir.iterdir(), key=lambda e: e.name):
            sz = server_impl._path_size_bytes(entry)
            components[entry.name] = sz
            total += sz
    except OSError:
        return None
    return {"total_bytes": total, "total_human": server_impl._human_bytes(total), "components": components}


CLOSE_OPTIMIZE_BLOAT_RATIO = 1.0 / 0.6


def _close_optimize_enabled(root: Path) -> bool:
    """Kill-switch for the wave 1rycf close-time optimize. Reads
    ``docs/workflow-config.json`` ``indexing.close_optimize_enabled`` (default ``True``). Fail-safe:
    any read/parse error or missing key yields the default; never raises."""
    try:
        cfg = _read_workflow_config(root)
        indexing = cfg.get("indexing")
        if isinstance(indexing, dict) and "close_optimize_enabled" in indexing:
            return bool(indexing.get("close_optimize_enabled"))
    except Exception:  # noqa: BLE001 — a config read must never gate the close
        pass
    return True


def _index_table_bloat_ratios(root: Path) -> dict[str, float]:
    """Page bloat in the one shared database; no payload scans.

    Wave 1xny6 lane L6b retired the separate ``graph`` entry with the
    standalone graph state store it measured. Graph rows live in the shared
    database now, so the docs/code ratios already describe their pages, and
    procedure step 6 deletes the retired folder that file lived in -- a second
    arm here could only ever report on a file the upgrade removes.
    """
    import server_impl

    ratios: dict[str, float] = {}
    index_dir = root / ".wavefoundry" / "index"
    try:
        vectors = server_impl._load_script("sqlite_vector_store")
        space = vectors.storage_space(index_dir)
        pages, free = int(space["page_count"]), int(space["freelist_count"])
        if pages > 0 and free > 0:
            ratio = pages / max(1, pages - free)
            ratios.update({layer: ratio for layer in ("docs", "code")
                           if vectors.layer_available(index_dir, layer)})
    except Exception:
        pass
    return ratios


def _sqlite_maintenance_failure(results: dict[str, Any]) -> Optional[str]:
    """Keep nested maintenance failures visible in both operator response paths."""
    errors = []
    # A top-level error with store results means maintenance started but
    # publication failed. A bare error is the pre-maintenance epoch refusal.
    if "stores" in results and results.get("error"):
        errors.append(str(results["error"]))
    for name, res in results.get("stores", {}).items():
        if res.get("error") or res.get("integrity") not in (None, "ok"):
            errors.append(f"{name}: {res.get('error') or res.get('integrity')}")
    finalize = results.get("finalize")
    if isinstance(finalize, dict) and finalize.get("error"):
        errors.append(str(finalize["error"]))
    return "; ".join(errors) or None


def _maybe_optimize_index_on_close(root: Path) -> Optional[dict[str, Any]]:
    """Opportunistically maintain stores when either has at least 40 percent free pages.

    Skip when disabled, unnecessary, lock-busy, or maintenance fails. Never
    rebuild or re-embed during close; report any recovery requirement instead.
    """
    import server_impl

    try:
        if not _close_optimize_enabled(root):
            return None
        ratios = _index_table_bloat_ratios(root)
        bloated = sorted(t for t, r in ratios.items() if r >= CLOSE_OPTIMIZE_BLOAT_RATIO)
        if not bloated:
            return None
        index_dir = root / ".wavefoundry" / "index"
        idx = server_impl._load_script("indexer")
        already_running = getattr(idx, "IndexBuildAlreadyRunning", None)
        try:
            results = idx.optimize_index_tables(index_dir, tuple(t for t in bloated if t in ("docs", "code")))
        except Exception as exc:  # noqa: BLE001
            if already_running is not None and isinstance(exc, already_running):
                return {"ran": False, "skipped": "index_build_lock_held",
                        "bloated_tables": bloated,
                        "ratios": {t: round(ratios[t], 2) for t in bloated}}
            return {"ran": False, "skipped": "optimize_error", "error": str(exc),
                    "bloated_tables": bloated}
        if not results:
            return {"ran": False, "skipped": server_impl._REASON_INDEX_NOT_READY,
                    "error": "Maintenance did not run: no initialized shared index is available.",
                    "bloated_tables": bloated,
                    "recovery_tools": ["index_health"], "recovery_usage": "index_health()"}
        failure = _sqlite_maintenance_failure(results)
        if failure:
            return {"ran": False, "skipped": "optimize_error", "error": failure,
                    "bloated_tables": bloated, "stores": results.get("stores", {}),
                    "recovery_tools": ["index_health"], "recovery_usage": "index_health()"}
        if isinstance(results.get("error"), str):
            return {"ran": False, "skipped": server_impl._REASON_INDEX_NOT_READY, "error": results["error"],
                    "bloated_tables": bloated,
                    "recovery_tools": ["index_build"], "recovery_usage": "index_build(content='all')"}
        stores = results.pop("stores", {})
        results.pop("finalize", None)
        reclaimed_total = sum(int(value.get("reclaimed_bytes") or 0)
                              for value in stores.values() if isinstance(value, dict))
        deferred_rebuild: list[str] = []
        tables_out: dict[str, Any] = {}
        for t, res in (results or {}).items():
            if not isinstance(res, dict):
                continue
            before = int(res.get("bytes_before") or 0)
            after = int(res.get("bytes_after") or 0)
            reclaimed = max(0, before - after)
            reclaimed_total += reclaimed
            if res.get("needs_rebuild"):
                deferred_rebuild.append(t)
            tables_out[t] = {"tier": res.get("tier"), "reclaimed_bytes": reclaimed,
                             "reclaimed": server_impl._human_bytes(reclaimed)}
        return {
            "ran": True,
            "bloated_tables": bloated,
            "ratios": {t: round(ratios[t], 2) for t in bloated},
            "tables": tables_out,
            "stores": stores,
            "reclaimed_bytes": reclaimed_total,
            "reclaimed": server_impl._human_bytes(reclaimed_total),
            # Tier-3 rebuild is DEFERRED at close (never spawned inline) — surface it so a follow-up
            # index_optimize / index_build can pick it up.
            "needs_rebuild_deferred": sorted(deferred_rebuild),
        }
    except Exception:  # noqa: BLE001 — the close must never fail because of opportunistic reclaim
        return None


def index_health_response(
    index: server_impl.WaveIndex,
    *,
    background_monitors: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return structured health status for the project index layer.

    Runs file-hash comparison against the store's recorded build hashes and reports missing, stale, or
    ready state.  Wave 1p4ww folded the framework docs into this single project
    index.  Intended as an explicit diagnostic tool; not on the search hot path.
    """
    import server_impl

    setup_usage = "wf setup --root ."
    update_usage = "index_build(content='all', mode='update')"
    rebuild_usage = "index_build(content='all', mode='rebuild')"
    preserve_usage = (
        "Preserve index.sqlite, its WAL/SHM files, and any migration receipt. "
        "Diagnose the storage failure and use explicit recovery before retrying; "
        "do not delete or rebuild the only copy."
    )
    try:
        health = index.docs_health()
    except Exception as exc:
        code = getattr(exc, "code", "index_health_error")
        if code == "storage_runtime_unavailable":
            recovery_usage = setup_usage
            message = f"{exc} From the target repository, run {setup_usage}, then restart the MCP host."
        elif code in {"index_runtime_stale", "index_version_newer", "index_compatibility_unproven"}:
            recovery_usage = "Restart the affected Wavefoundry host, then call index_health(). Preserve the existing index."
            message = str(exc)
        elif code == "storage_recovery_required":
            recovery_usage = str(exc)
            message = str(exc)
        else:
            recovery_usage = "Resolve the reported error before retrying index_health(). " + preserve_usage
            message = str(exc)
        return server_impl._response(
            "error",
            {
                "layers": {},
                **(
                    {"background_monitors": dict(background_monitors)}
                    if background_monitors is not None
                    else {}
                ),
            },
            diagnostics=[
                _diagnostic(
                    code,
                    f"Could not compute index health: {message}",
                    recovery_tools=["wf_help"],
                    recovery_usage=recovery_usage,
                )
            ],
            next_tools=["wf_help"],
            usage=recovery_usage,
        )

    diagnostics: list[dict[str, Any]] = []
    for layer in health.get("missing_layers", []):
        diagnostics.append(
            _diagnostic(
                server_impl._REASON_INDEX_MISSING,
                f"Index layer missing: {layer}. From the target repository, run {setup_usage}.",
                recovery_tools=["wf_help"],
                recovery_usage=setup_usage,
            )
        )
    for layer in health.get("stale_layers", []):
        diagnostics.append(
            _diagnostic(
                "index_stale",
                f"Index layer stale: {layer}. Refresh: {rebuild_usage if health.get('chunker_version_mismatch_layers') else update_usage}",
                recovery_tools=["index_build"],
                recovery_usage=rebuild_usage if health.get("chunker_version_mismatch_layers") else update_usage,
            )
        )
    overview = health.get("readiness_overview")
    if overview == "degraded":
        diagnostics.append(
            _diagnostic(
                "index_degraded",
                "Index metadata is present but merged semantic chunks did not load; search may fall back to lexical retrieval.",
                recovery_tools=["wf_help"],
                recovery_usage=setup_usage,
            )
        )
    elif overview == "absent":
        diagnostics.append(
            _diagnostic(
                "index_absent",
                "No index metadata found under the project index dir (nothing to search semantically yet).",
                recovery_tools=["wf_help"],
                recovery_usage=setup_usage,
            )
        )
    if health.get("code_layer_missing"):
        diagnostics.append(
            _diagnostic(
                "code_layer_missing",
                "Code sources are in scope but the code SQLite vector layer is absent — likely an "
                "interrupted or OOM-killed code embedding pass. code_ask / code_search have no code layer "
                "until it is rebuilt: index_build(content='code').",
                recovery_tools=["index_build"],
                recovery_usage="index_build(content='code')",
            )
        )
    for layer in health.get("chunker_version_mismatch_layers", []):
        diagnostics.append(
            _diagnostic(
                "chunker_version_mismatch",
                f"Index layer '{layer}' was built with an older chunker version. "
                f"A full rebuild is required: {rebuild_usage}",
                recovery_tools=["index_build"],
                recovery_usage=rebuild_usage,
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
                recovery_usage="index_health()",
            )
        )

    # Wave 1p99o: surface the authoritative index-build lock status so a leftover lock file (present
    # by design, not held) is diagnosable at a glance and agents don't misread its presence as "a build
    # is running."
    health["size"] = _index_dir_size(index.root / ".wavefoundry" / "index")  # wave 1p9a9
    lock_info = _index_build_lock_info(index.root)
    health["lock"] = lock_info
    if (
        lock_info.get("present")
        and not lock_info.get("held")
        and lock_info.get("ended_at") is None
        and lock_info.get("started_at") is not None
    ):
        diagnostics.append(
            _diagnostic(
                "index_build_interrupted",
                "The last index build did NOT finish cleanly (interrupted or killed) — the index may be "
                "partial. Consider a rebuild: index_build(content='all', mode='rebuild'). The lock "
                "file is present but NOT held; do not delete it (it persists by design). Use "
                "index_build_status for the authoritative lock state.",
                recovery_tools=["index_build", "index_build_status"],
                recovery_usage="index_build(content='all', mode='rebuild')",
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

    # Wave 13129 (1316n): graph readiness reported separately from semantic
    # readiness. A consumer caught the silent "rebuild didn't touch graph" misread
    # because there was no breakout. Operators now see graph_present /
    # graph_last_built_at per layer alongside the existing fields.
    health["graph"] = _graph_health_summary(index.root)
    if background_monitors is not None:
        health["background_monitors"] = dict(background_monitors)

    # Wave 1rsh9 (1rq4h): index-state store presence + schema version + two-layer
    # integrity verdict (quick_check + freshness-fingerprint binding). Absence
    # is a normal not-yet-built state, never an error (AC-2/AC-6).
    health["state_store"] = server_impl._state_store_health_summary(index.root)
    try:
        vector_store = server_impl._load_script("sqlite_vector_store")
        counts = vector_store.layer_counts(index.root / ".wavefoundry" / "index")
        health["capacity"] = vector_store.capacity_qualification(counts)
        if not health["capacity"]["qualified"]:
            diagnostics.append(_diagnostic(
                "capacity_unqualified",
                "The local vector index exceeds the measured retrieval-latency envelope for "
                + ", ".join(health["capacity"]["exceeded_layers"])
                + ". Indexing and exact search continue normally; performance at this size "
                "needs qualification on this machine. No files or results are dropped.",
            ))
    except Exception:
        pass  # Store absence/corruption has its own health diagnostics.
    vector_defects = {
        layer: {key: details.get(key, 0) for key in ("missing_vectors", "orphan_vectors")}
        for layer, details in (health["state_store"].get("chunk_index") or {}).items()
        if details.get("missing_vectors") or details.get("orphan_vectors")
    }
    if vector_defects:
        diagnostics.append(_diagnostic(
            "vector_population_mismatch",
            "Canonical chunks and vectors differ: " + json.dumps(vector_defects, sort_keys=True)
            + ". Run an index update to reconcile the native vector population.",
            recovery_tools=["index_build"], recovery_usage="index_build(content='all', mode='update')",
        ))
    # Wave 1x6ti (1x551): the reap's persisted deferral / preservation record,
    # the same reader index_build_status uses, plus one diagnostic per
    # non-empty map (a deferral the operator must act on; a preserved subtree
    # served as of the last readable build).
    _reap_block = server_impl._reap_state_block(index.root)
    if _reap_block is not None:
        health["reap"] = _reap_block
        diagnostics.extend(server_impl._reap_state_diagnostics(_reap_block))
    # 1sbfj: coverage advisory — a structurally-sound store whose chunk
    # registry/FTS covers fewer rows than the canonical SQLite tables, so retrieval
    # is running partially blind (the field defect read as `integrity: ok`).
    # The next index build heals it (the reconcile backfills from canonical chunks,
    # including on zero-change builds).
    _uncovered = [
        f"{t} (registry {c.get('registry_rows')} of {c.get('vector_rows')} vector rows)"
        for t, c in (health["state_store"].get("chunk_index") or {}).items()
        if c.get("covered") is False and not c.get("missing_vectors") and not c.get("orphan_vectors")
    ]
    if _uncovered:
        diagnostics.append(
            _diagnostic(
                "chunk_index_undercovered",
                "The derived chunk index (FTS/registry) covers materially less than the "
                "Vector layers: " + "; ".join(sorted(_uncovered)) + ". Lexical (BM25) "
                "retrieval is running partially blind until it heals. Rebuild the derived "
                "lexical layer directly (embedding-free, seconds): "
                "index_build(content='fts') — or any ordinary build backfills it.",
                recovery_tools=["index_build", "index_build_status"],
                recovery_usage="index_build(content='fts')",
            )
        )
    # 1wngv (wave 1wpif): same-ID/distinct-content collisions detected by the
    # store-layer census at the last derived rebuild. This fires BEFORE the
    # coverage numbers can read as complete: one id maps to multiple
    # different chunks, and the registry/FTS layer keeps only one of them.
    _colliding = [
        f"{t} ({c.get('id_collisions')} colliding id(s))"
        for t, c in (health["state_store"].get("chunk_index") or {}).items()
        if c.get("id_collisions")
    ]
    if _colliding:
        diagnostics.append(
            _diagnostic(
                "chunk_id_collisions",
                "The derived chunk index recorded same-ID/distinct-content collisions at "
                "its last rebuild: " + "; ".join(sorted(_colliding)) + ". One id maps to "
                "multiple different chunks, so the registry/FTS layer keeps only one of "
                "them and derived-state coverage is NOT complete for the colliding "
                "content. A full rebuild under the current chunker clears chunker-emitted "
                "collisions: index_build(content='all', mode='rebuild').",
                recovery_tools=["index_build", "index_build_status"],
                recovery_usage="index_build(content='all', mode='rebuild')",
            )
        )
    # 1wpag (wave 1wpif): FTS liveness / parity / keyed-integrity verdict per
    # table (the epoch-cached result the serving chokepoint uses). Damage means
    # code_lexical returns typed query_failed and the hybrid tools carry
    # lexical_undercoverage until the next ordinary build heals the table.
    _fts_damaged = [
        f"{t} ({v.get('reason')}; fts_rows={v.get('fts_rows')}, registry_rows={v.get('registry_rows')})"
        for t, v in (health["state_store"].get("fts") or {}).items()
        if v.get("ok") is False and v.get("reason") in _FTS_DAMAGE_REASONS
    ]
    if _fts_damaged:
        diagnostics.append(
            _diagnostic(
                "fts_integrity_failed",
                "The derived FTS5 lexical state failed its liveness/parity/keyed-integrity "
                "probe: " + "; ".join(sorted(_fts_damaged)) + ". Lexical retrieval "
                "(code_lexical, the hybrid FTS half, the degraded fallbacks) reports typed "
                "query_failed / lexical_undercoverage instead of a healthy zero until the "
                "next ordinary build heals the table under the build lock (one heal per "
                "table per epoch): index_build(content='all', mode='update').",
                recovery_tools=["index_build", "index_build_status"],
                recovery_usage="index_build(content='all', mode='update')",
            )
        )

    if health["state_store"].get("integrity") == "structural-fail":
        # Retain concurrent findings (including FTS damage), but never suggest
        # competing writes while the canonical store needs explicit recovery.
        for diagnostic in diagnostics:
            diagnostic["message"] = (
                "Additional finding: " + diagnostic["code"].replace("_", " ")
                + ". Details remain in the health data. Canonical storage recovery "
                "takes precedence over other index maintenance."
            )
            diagnostic["recovery_tools"] = ["wf_help"]
            diagnostic["recovery_usage"] = preserve_usage
        diagnostics.insert(0, _diagnostic(
            "state_store_structural_fail",
            "The canonical index store failed its structural integrity check. " + preserve_usage,
            recovery_tools=["wf_help"], recovery_usage=preserve_usage,
        ))
        next_tools, usage = ["wf_help"], preserve_usage
    elif lock_info.get("held") or background_build_status == "running":
        next_tools, usage = ["index_build_status"], "index_build_status()"
    elif health.get("chunker_version_mismatch_layers"):
        next_tools, usage = ["index_build"], rebuild_usage
    elif health.get("missing_layers") or overview in {"absent", "incomplete", "degraded"}:
        next_tools, usage = ["wf_help"], setup_usage
    elif health.get("stale_layers") or not health.get("semantic_ready"):
        next_tools, usage = ["index_build"], update_usage
    else:
        next_tools, usage = ["docs_search"], "docs_search(query='...')"
    return server_impl._response("ok", health, diagnostics=diagnostics, next_tools=next_tools, usage=usage)


def _index_optimize_response(
    root: Path,
    content: str = "all",
    rebuild_if_needed: bool = True,
    cache: Optional[server_impl.McpRepoCache] = None,
) -> dict[str, Any]:
    """Maintain the shared SQLite index and graph store once under the build lock.

    Preserve per-layer statistics and per-store integrity results. Reclaim free
    pages incrementally without re-embedding or routinely rewriting the database.
    """
    import server_impl

    content_s = (content or "all").strip().lower()
    layer_map = {"docs": ("docs",), "code": ("code",), "all": ("docs", "code"), "": ("docs", "code")}
    tables = layer_map.get(content_s)
    if tables is None:
        return server_impl._response(
            "error",
            {"content": content, "operation": "optimize"},
            diagnostics=[_diagnostic(
                "invalid_arguments",
                f"index_optimize's content selects the vector layers — it must be 'docs', 'code', or "
                f"'all' (got {content!r}). The shared SQLite index is maintained once "
                f"alongside whichever vector selection runs.",
            )],
            next_tools=["index_health"],
            usage="index_optimize(content='all')",
        )
    index_dir = root / ".wavefoundry" / "index"
    idx = server_impl._load_script("indexer")
    already_running = getattr(idx, "IndexBuildAlreadyRunning", None)
    try:
        results = idx.optimize_index_tables(index_dir, tuple(tables))
    except Exception as exc:  # noqa: BLE001
        if already_running is not None and isinstance(exc, already_running):
            return server_impl._response(
                "error",
                {"content": content_s, "operation": "optimize"},
                diagnostics=[_diagnostic(
                    "build_skipped_lock_busy",
                    f"A build is already running ({exc}). Call index_build_status and read the "
                    f"`lock` object; retry index_optimize once `held` is false.",
                    recovery_tools=["index_build_status"],
                    recovery_usage="index_build_status()",
                )],
                next_tools=["index_build_status"],
                usage="index_build_status()",
            )
        return server_impl._response(
            "error",
            {"content": content_s, "operation": "optimize"},
            diagnostics=[_diagnostic("index_optimize_failed", f"Optimize failed: {exc}")],
            next_tools=["index_health"],
            usage="index_health()",
        )
    maintenance_failure = _sqlite_maintenance_failure(results)
    stores_out: dict[str, Any] = {}
    store_diagnostics: list[dict[str, Any]] = []
    stores_reclaimed = 0
    try:
        raw_stores = results.pop("stores", {})
        for name, res in raw_stores.items():
            s_before = int(res.get("size_before_bytes") or 0)
            s_after = int(res.get("size_after_bytes") or 0)
            s_reclaimed = int(res.get("reclaimed_bytes") or 0)
            stores_reclaimed += s_reclaimed
            stores_out[name] = {
                **res,
                "present": bool(res.get("present")),
                "integrity": res.get("integrity"),
                "size_before_bytes": s_before,
                "size_before": server_impl._human_bytes(s_before),
                "size_after_bytes": s_after,
                "size_after": server_impl._human_bytes(s_after),
                "reclaimed_bytes": s_reclaimed,
                "reclaimed": server_impl._human_bytes(s_reclaimed),
                "error": res.get("error"),
            }
            if res.get("present") and res.get("integrity") == "structural-fail":
                store_diagnostics.append(_diagnostic(
                    "state_store_structural_fail",
                    (f"SQLite store '{name}' failed its integrity check. "
                     "Preserve index.sqlite and any -wal/-shm companions before explicit "
                     "recovery; a pending migration must follow its retained receipt. "
                     "The shared semantic store is not automatically discarded."
                     if name == "index-state" else
                     f"SQLite store '{name}' failed its integrity check; rebuild the derived graph store."),
                    recovery_tools=["index_health"] if name == "index-state" else ["index_build"],
                    recovery_usage="index_health()" if name == "index-state" else "index_build(content='graph', mode='rebuild')",
                ))
    except Exception as exc:  # noqa: BLE001
        if already_running is not None and isinstance(exc, already_running):
            store_diagnostics.append(_diagnostic(
                "build_skipped_lock_busy",
                f"SQLite store maintenance skipped — a build is running ({exc}). Retry once "
                f"index_build_status reports lock.held false.",
                recovery_tools=["index_build_status"],
                recovery_usage="index_build_status()",
            ))
        else:
            store_diagnostics.append(_diagnostic(
                "state_store_maintenance_failed", f"SQLite store maintenance failed: {exc}",
            ))
    if maintenance_failure:
        return server_impl._response(
            "error",
            {"content": content_s, "operation": "optimize", "tables": {}, "stores": stores_out,
             "error": maintenance_failure, "total_reclaimed_bytes": stores_reclaimed,
             "total_reclaimed": server_impl._human_bytes(stores_reclaimed)},
            diagnostics=store_diagnostics + [_diagnostic(
                "state_store_maintenance_failed", maintenance_failure,
                recovery_tools=["index_health"], recovery_usage="index_health()",
            )],
            next_tools=["index_health"], usage="index_health()",
        )
    if not results:
        return server_impl._response(
            "ok",
            {"content": content_s, "operation": "optimize", "tables": {},
             "stores": stores_out,
             "total_reclaimed_bytes": stores_reclaimed,
             "total_reclaimed": server_impl._human_bytes(stores_reclaimed),
             "note": "No matching vector layers present to optimize."},
            diagnostics=store_diagnostics,
            next_tools=["index_health"],
            usage="index_health()",
        )
    # Independent-review N2: the restore-only refusal is a top-level
    # {"error": str}; iterating it as per-table dicts raised AttributeError.
    if isinstance(results.get("error"), str):
        return server_impl._response(
            "error",
            {"error": results["error"]},
            diagnostics=[_diagnostic(
                server_impl._REASON_INDEX_NOT_READY,
                results["error"],
                recovery_tools=["index_build"],
                recovery_usage="index_build(content='all')",
            )],
            next_tools=["index_build"],
            usage="index_build(content='all')",
        )
    # 1sed6: a dirty optimize deliberately leaves the epoch un-finalized —
    # surface that as a diagnostic instead of listing "finalize" as a table.
    results.pop("finalize", None)
    tables_out: dict[str, Any] = {}
    needs_rebuild: list[str] = []
    total_before = 0
    total_after = 0
    for t, res in results.items():
        if not isinstance(res, dict):
            continue
        before = int(res.get("bytes_before") or 0)
        after = int(res.get("bytes_after") or 0)
        total_before += before
        total_after += after
        reclaimed = max(0, before - after)
        tables_out[t] = {
            "tier": res.get("tier"),
            "rows": res.get("rows"),
            "needs_rebuild": bool(res.get("needs_rebuild")),
            "size_before_bytes": before,
            "size_before": server_impl._human_bytes(before),
            "size_after_bytes": after,
            "size_after": server_impl._human_bytes(after),
            "reclaimed_bytes": reclaimed,
            "reclaimed": server_impl._human_bytes(reclaimed),
            "error": res.get("error"),
        }
        if res.get("needs_rebuild"):
            needs_rebuild.append(t)
    if cache:
        cache.invalidate()
    diagnostics = list(store_diagnostics)
    rebuilt: list[str] = []
    if needs_rebuild and rebuild_if_needed:
        # Tier 3: a table was unreadable for a rewrite. The build lock is released now (optimize_index_tables
        # exited its `with`), so spawn a full re-embed rebuild for each — run_index_rebuild is
        # background + single-flight.
        for layer in needs_rebuild:
            try:
                run_index_rebuild(root, content=layer, full=True, rechunk=False, layer="project")
                rebuilt.append(layer)
            except Exception as exc:  # noqa: BLE001
                diagnostics.append(_diagnostic(
                    "index_rebuild_spawn_failed",
                    f"Table '{layer}' needs a rebuild but the rebuild spawn failed ({exc}). "
                    f"Run index_build(content='{layer}', mode='rebuild').",
                ))
        if rebuilt:
            diagnostics.append(_diagnostic(
                "index_optimize_rebuild_spawned",
                f"Tables {rebuilt} were unreadable (Tier 3) and a full rebuild was spawned in the "
                f"background. Poll index_build_status.",
                recovery_tools=["index_build_status"],
                recovery_usage="index_build_status()",
            ))
    elif needs_rebuild:
        diagnostics.append(_diagnostic(
            "index_optimize_needs_rebuild",
            f"Tables {needs_rebuild} were unreadable (Tier 3) and need a full rebuild. "
            f"Run index_build(content='{needs_rebuild[0]}', mode='rebuild').",
            recovery_tools=["index_build"],
            recovery_usage=f"index_build(content='{needs_rebuild[0]}', mode='rebuild')",
        ))
    total_reclaimed = max(0, total_before - total_after) + stores_reclaimed
    return server_impl._response(
        "ok",
        {
            "content": content_s,
            "operation": "optimize",
            "tables": tables_out,
            "stores": stores_out,
            "total_reclaimed_bytes": total_reclaimed,
            "total_reclaimed": server_impl._human_bytes(total_reclaimed),
            "needs_rebuild": needs_rebuild,
            "rebuild_spawned": rebuilt,
        },
        diagnostics=diagnostics,
        next_tools=["index_health"],
        usage="index_health()",
    )


def index_build_response(
    root: Path,
    *,
    content: str = "docs",
    mode: str = "update",
    layer: str = "project",
    cache: Optional[server_impl.McpRepoCache] = None,
) -> dict[str, Any]:
    import server_impl

    content_s = (content or "").strip().lower()
    layer_s = (layer or "").strip().lower()
    mode_s = (mode or "").strip().lower()
    if mode_s not in {"update", "rebuild", "rechunk"}:
        return server_impl._response(
            "error",
            {"content": content, "mode": mode, "layer": layer},
            diagnostics=[
                _diagnostic(
                    "invalid_arguments",
                    f"Unsupported mode {mode!r}. Use 'update' (incremental, changed files only), "
                    "'rechunk' (re-chunk every file but reuse embeddings by hash — only new/changed "
                    "chunks re-embed), or 'rebuild' (full re-embed from scratch). To reclaim on-disk "
                    "bloat without re-embedding, use index_optimize().",
                    recovery_tools=["index_optimize", "wf_help"],
                    recovery_usage="wf_help(goal='refresh_semantic_index')",
                )
            ],
            next_tools=["index_optimize", "wf_help"],
            usage="wf_help(goal='refresh_semantic_index')",
        )
    import sqlite_runtime as runtime
    full = mode_s == "rebuild"
    rechunk = mode_s == "rechunk"
    try:
        result = run_index_rebuild(root, content=content_s, full=full, rechunk=rechunk, layer=layer_s)
    except (runtime.RuntimeUnavailable, runtime.StorageRecoveryRequired) as exc:
        return _index_runtime_failure_response(
            "index_build", root, {"content": content, "mode": mode_s, "layer": layer}, exc)
    except ValueError as exc:
        return server_impl._response(
            "error",
            {"content": content, "mode": mode_s, "layer": layer},
            diagnostics=[
                _diagnostic(
                    "invalid_arguments",
                    str(exc),
                    recovery_tools=["wf_help"],
                    recovery_usage="wf_help(goal='maintain_framework')",
                )
            ],
            next_tools=["wf_help"],
            usage="wf_help(goal='maintain_framework')",
        )
    # Only invalidate the cache when a rebuild was actually spawned and the
    # subprocess survived the verification window — not for up-to-date,
    # already-running, or early-exit short-circuits.
    if (
        cache
        and not result.get("up_to_date")
        and not result.get("already_running")
        and not result.get("build_failed_early")
    ):
        cache.invalidate()
    diagnostics = []
    if result.get("already_running"):
        diagnostics.append(_diagnostic(
            "index_build_already_running",
            result["notice"],
            recovery_tools=["index_health"],
            recovery_usage="index_health()",
        ))
    # Wave 1p2q3 (1p2w5): synchronous Popen-verification surfaced a subprocess
    # early-exit. Emit a `build_skipped_lock_busy` (or
    # `index_build_subprocess_failed`) diagnostic carrying the lock-holder pid
    # so the caller sees a clear actionable recovery path instead of a
    # misleading success response.
    if result.get("build_failed_early"):
        _failure_code = str(result.get("diagnostic_code") or "index_build_subprocess_failed")
        _failure_message = str(result.get("notice") or "Index rebuild subprocess exited early.")
        if result.get("lock_owner_pid"):
            _failure_message = (
                f"{_failure_message} Recovery: call index_build_status and read the `lock` object — "
                f"if `held` is true a build is running, so wait; if it is not held (stale), the lock is "
                f"reclaimed automatically on the next build, so just retry index_build. Do not "
                f"delete the lock file — it persists by design and its presence does not mean a build is running."
            )
        diagnostics.append(_diagnostic(
            _failure_code,
            _failure_message,
            recovery_tools=["index_build_status", "index_build"],
            recovery_usage="index_build_status()",
        ))
    # Wave 13129 (1316n): surface graph state regardless of content. Operators
    # running content='code'|'docs'|'all' need to see the graph wasn't touched
    # (a consumer's misread on 1.2.1+315o). When content is not 'graph', append a
    # clarifying note pointing at content='graph' for graph refresh.
    graph_health = _graph_health_summary(root)
    target_layer = "project"
    layer_graph = graph_health.get(target_layer, {})
    if layer_graph.get("present"):
        result["graph_node_count"] = layer_graph.get("node_count")
        result["graph_edge_count"] = layer_graph.get("edge_count")
        result["graph_last_built_at"] = layer_graph.get("last_built_at")
    if content_s != "graph":
        result["graph_rebuilt"] = False
        existing_notice = str(result.get("notice") or "")
        graph_callout = (
            " | NOTE: The graph layer was NOT rebuilt by this call. "
            "Run index_build(content='graph') if graph-layer refresh is required."
        )
        if graph_callout not in existing_notice:
            result["notice"] = (existing_notice + graph_callout).strip(" |")
    else:
        # Wave 1p2q3 (1p2w5): graph_rebuilt reflects whether a rebuild actually
        # ran. A subprocess early-exit (lock-busy) means the rebuild never
        # happened despite the spawn; do not claim graph_rebuilt: true.
        result["graph_rebuilt"] = not (
            result.get("already_running")
            or result.get("up_to_date")
            or result.get("build_failed_early")
        )
        # Wave 1p2q3 (131hh): explicit graph rebuild — notify MCP clients that
        # cached wavefoundry://graph/* resources may be stale. Skip when the
        # request was already-running, up-to-date, or failed early (no rebuild
        # fired in any of those cases).
        if result["graph_rebuilt"]:
            server_impl._dispatch_graph_resources_updated(root=root, layer=target_layer)
    return server_impl._response(
        "ok" if not result.get("build_failed_early") else "error",
        result,
        diagnostics=diagnostics,
        next_tools=["index_health"],
        usage="index_health()",
    )


def _index_build_lock_info(root: Path) -> dict[str, Any]:
    """Authoritative index-build lock status (wave 1p99o).

    ``held`` is determined by **non-destructively testing the real OS lock**
    (``indexer._index_build_lock_held`` — POSIX ``fcntl`` ``F_GETLK`` / native Windows momentary
    ``msvcrt``), never from file presence. The lock FILE persists **by design** as a last-owner record,
    so ``present: true`` does not imply a build is running — read ``held``. ``ended_at`` (best-effort,
    written on a clean build exit) distinguishes a clean finish from an **interrupted** build (a hard
    kill can't write it). Plain terminology only — no "zombie"."""
    import server_impl

    index_dir = root / ".wavefoundry" / "index"
    lock_path = index_dir / "index-build.lock"
    info: dict[str, Any] = {
        "held": False,
        "present": False,
        "owner_pid": None,
        "owner_cmdline": None,
        "started_at": None,
        "ended_at": None,
        "note": "No index-build lock file is present; no build is running.",
    }
    try:
        idx = server_impl._indexer_module()
        present = lock_path.exists()
        info["present"] = present
        if not present:
            return info
        meta = idx.read_index_build_lock_metadata(lock_path)
        held, holder_pid = idx._index_build_lock_held(index_dir)
    except Exception:  # noqa: BLE001 — best-effort; status must never break
        return info
    meta = meta if isinstance(meta, dict) else {}
    started_at = meta.get("started_at") if isinstance(meta.get("started_at"), (int, float)) else None
    ended_at = meta.get("ended_at") if isinstance(meta.get("ended_at"), (int, float)) else None
    cmdline = meta.get("cmdline") if isinstance(meta.get("cmdline"), str) else None
    meta_pid = meta.get("pid") if isinstance(meta.get("pid"), int) else None
    info["started_at"] = started_at
    info["ended_at"] = ended_at
    info["owner_cmdline"] = cmdline
    # Prefer the kernel-reported holder PID when held (ground truth); else the last recorded owner.
    info["owner_pid"] = holder_pid if (held and holder_pid) else meta_pid
    info["held"] = bool(held)
    if held:
        info["note"] = f"A build is running (owner pid {info['owner_pid']})."
    elif held is None:
        info["note"] = (
            "The lock state could not be determined; treat it as not held — the acquire-time lock is "
            "the authority. The lock file's presence does not mean a build is running."
        )
    elif ended_at is not None:
        info["note"] = (
            "The last build finished cleanly; the lock is not held. The lock file persists as a "
            "last-owner record — its presence does not mean a build is running."
        )
    elif started_at is not None:
        info["note"] = (
            "The last build did NOT finish cleanly (interrupted or killed) — the index may be partial; "
            "consider a rebuild. The lock file persists by design; its presence does not mean a build "
            "is running."
        )
    else:
        info["note"] = (
            "A lock file is present but has no recorded owner; the lock is not held. Its presence does "
            "not mean a build is running."
        )
    return info


def index_build_status_response(root: Path, layer: str = "project") -> dict[str, Any]:
    """Wrapper (wave 1p99o): attach the authoritative ``lock`` object to every return path so callers
    ask the classifier, not the by-design-persistent lock file, whether a build is running.

    1sed6 review fix: also attach the store's build ``epoch`` on every return
    path, and never report ``idle`` over a non-complete epoch — a builder that
    died between fence and finalize is ``interrupted`` (readers are failed
    closed), which callers must see to know a rebuild is required.
    """
    import server_impl

    resp = _index_build_status_response_inner(root, layer=layer)
    data = resp.get("data")
    if isinstance(data, dict):
        # Read order matters (review F5): epoch state FIRST, lock second, and
        # a positive interrupted classification re-reads the state — so a
        # build finalizing (or starting) between the two reads cannot yield a
        # one-poll false "interrupted".
        def _read_epoch() -> dict[str, Any]:
            out: dict[str, Any] = {"status": "absent", "generation": None, "scope": ""}
            try:
                iss = server_impl._load_script("index_state_store")
                state = iss.read_build_state(root / ".wavefoundry" / "index")
                if state is not None:
                    out = {
                        "status": state.get("status"),
                        "generation": state.get("generation"),
                        "scope": state.get("scope", ""),
                    }
            except Exception:
                pass
            return out
        epoch = _read_epoch()
        lock_info = _index_build_lock_info(root)
        data["lock"] = lock_info
        held = bool(lock_info.get("held")) if isinstance(lock_info, dict) else False
        if epoch.get("status") == "building" and not held:
            epoch = _read_epoch()  # double-check: rule out a finalize between reads
        epoch["interrupted"] = epoch.get("status") == "building" and not held
        data["epoch"] = epoch
        if data.get("state") == "idle" and epoch["interrupted"]:
            data["state"] = "interrupted"
            resp.setdefault("diagnostics", []).append(_diagnostic(
                "index_build_interrupted",
                "The store records a `building` epoch but no build holds the lock — a prior "
                "builder died between fence and finalize. Readers are failed closed; run "
                "index_build to recover (an unchanged retry heals the epoch).",
                recovery_tools=["index_build"],
                recovery_usage="index_build(content='all')",
            ))
        # Wave 1x6ti (1x551): the reap's deferral / preservation record rides
        # EVERY state (finished, idle, running beside previous_stats, and
        # interrupted), read from the store and never from the log; omitted
        # when no record exists.
        reap_block = server_impl._reap_state_block(root)
        if reap_block is not None:
            data["reap"] = reap_block
    return resp


def _index_build_status_response_inner(root: Path, layer: str = "project") -> dict[str, Any]:
    import server_impl

    import time as _time
    layer_s = (layer or "").strip().lower()
    # Wave 1p4ww: single project index — the framework layer is folded in.
    if layer_s != "project":
        return server_impl._response("error", {"layer": layer}, diagnostics=[_diagnostic("invalid_arguments", f"Unsupported layer '{layer}'. Use 'project'.")])
    state_path = _index_build_state_path(root, layer_s)
    log_path = _index_build_log_path(root, layer_s)
    index_dir = state_path.parent
    stale_locks_cleaned: list[dict[str, Any]] = []
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
            return server_impl._response(
                "ok",
                running_data,
                next_tools=["index_build_status"],
                usage="index_build_status()",
            )
        idle_data: dict[str, Any] = {"layer": layer_s, "state": "idle"}
        if stale_locks_cleaned:
            idle_data["stale_locks_cleaned"] = stale_locks_cleaned
        return server_impl._response("ok", idle_data, next_tools=["index_build"], usage="index_build()")

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _clear_index_build_state(root, layer_s)
        idle_data = {"layer": layer_s, "state": "idle"}
        if stale_locks_cleaned:
            idle_data["stale_locks_cleaned"] = stale_locks_cleaned
        return server_impl._response("ok", idle_data, next_tools=["index_build"], usage="index_build()")

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
        return server_impl._response(
            "ok",
            running_data,
            next_tools=["index_build_status"],
            usage="index_build_status()",
        )

    if not log_done and isinstance(pid, int) and server_impl._pid_is_running(pid):
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
        return server_impl._response(
            "ok",
            running_data,
            next_tools=["index_build_status"],
            usage="index_build_status()",
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
    return server_impl._response("ok", summary, next_tools=["index_health"], usage="index_health()")


_FTS_DAMAGE_REASONS = frozenset({"probe_failed", "digest_mismatch", "digest_unavailable"})


def _graph_refresh_then_recheck(
    root: Path,
    recheck_fn: Callable[[], Any],
) -> Any:
    """Run an incremental graph update, then re-call ``recheck_fn`` and return its result.

    Wave 1304x / 1304r: shared helper used by every graph-using MCP tool when its
    initial graph query returns no result. Incremental refresh is ~4ms when nothing
    has changed (measured during wave 12xr3 close-review), so it's cheap to attempt
    inline. Returns ``None`` on any exception so callers fall through to their
    existing not-found / suggestions path without surfacing the refresh error;
    exceptions are logged to stderr via ``_wf_log`` so operators see real failures
    rather than silent degradation.

    Usage pattern:
        candidate = primary_query(...)
        if candidate is None or empty:
            candidate = _graph_refresh_then_recheck(root, lambda: primary_query(...))
            if candidate:
                # found after refresh — proceed
            else:
                # genuinely missing — emit suggestions / not-found
    """
    import server_impl

    try:
        index_build_response(root, content="graph", mode="update")
    except Exception as exc:
        server_impl._wf_log(f"[wavefoundry] graph refresh failed during recheck: {exc!r}")
        return None
    # Wave 1xny6: the refresh may have published a new generation. Drop the
    # cached snapshot AND rebind any pin held by the calling response — the
    # response asked for the newer generation, so serving it the pre-build one
    # would report its own successful refresh as "still missing".
    try:
        server_impl._load_graph_query().invalidate_query_index_cache(root)
    except Exception:
        pass
    try:
        server_impl._graph_snapshot_module().repin(root, "project")
    except Exception:
        pass
    try:
        return recheck_fn()
    except Exception as exc:
        server_impl._wf_log(f"[wavefoundry] recheck closure failed after graph refresh: {exc!r}")
        return None

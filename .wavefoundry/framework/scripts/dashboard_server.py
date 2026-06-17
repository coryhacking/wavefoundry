#!/usr/bin/env python3
"""Local dashboard server for Wave Framework repositories."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import queue
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import dashboard_lib


ASSET_ROOT = Path(__file__).resolve().parent.parent / "dashboard"

_GIT_INTERVAL = 60       # seconds between git stat rebuilds
_WATCH_INTERVAL = 3.0    # seconds between mtime polls
_SSE_HEARTBEAT = 15      # seconds between SSE keep-alive comments
# Wave 1p4ww: single project index — the framework layer is folded in.
_INDEX_LAYERS = ("project",)
# Wave 1p5xw: the on-demand staleness display is rate-limited so a busy repo can't
# trigger a full repo-walk on every snapshot rebuild (mtime change / git tick).
_DISPLAY_STALENESS_MIN_INTERVAL = 30.0
_INDEXER_MOD = None


def _get_indexer():
    global _INDEXER_MOD
    if _INDEXER_MOD is None:
        indexer_path = Path(__file__).resolve().parent / "indexer.py"
        spec = importlib.util.spec_from_file_location("dashboard_indexer", indexer_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load indexer module from {indexer_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _INDEXER_MOD = mod
    return _INDEXER_MOD


def _dashboard_log(message: str, *, context: str | None = None) -> None:
    prefix = f"{datetime.now(UTC).isoformat()} - "
    if context:
        prefix += f"{context} - "
    sys.stderr.write(f"[dashboard] {prefix}{message}\n")


# ── Index builder ─────────────────────────────────────────────────────────────

class IndexBuilder:
    """Debounced incremental index builder.

    Runs one subprocess at a time. File-change signals arm a debounce timer;
    a second signal during a running build sets a re-arm flag so the build
    is rescheduled after completion rather than spawning a second process.
    """

    def __init__(self, root: Path, delay: float, on_done: Any, on_started: Any | None = None) -> None:
        self._root = root
        self._delay = delay
        self._on_done = on_done
        self._on_started = on_started or (lambda: None)
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._running = False
        self._pending_after_build = False
        self._status = "idle"
        self._build_started_at: str | None = None
        self._build_finished_at: str | None = None
        self._pending_layers: set[str] = set()
        self._active_layers: set[str] = set()
        self._pending_reasons = {layer: set() for layer in _INDEX_LAYERS}
        self._active_reasons = {layer: set() for layer in _INDEX_LAYERS}
        self._layer_states = {
            layer: {
                "build_status": "idle",
                "build_started_at": None,
                "build_finished_at": None,
            }
            for layer in _INDEX_LAYERS
        }

    @staticmethod
    def _format_layers(layers: set[str]) -> str:
        ordered = [layer for layer in _INDEX_LAYERS if layer in layers]
        return ", ".join(ordered) if ordered else "project"

    @staticmethod
    def _normalize_reason(reason: str | None) -> str:
        text = (reason or "").strip()
        return text or "unspecified trigger"

    def _record_pending_reason(self, layer: str, reason: str) -> None:
        self._pending_reasons[layer].add(self._normalize_reason(reason))

    def _format_reason_summary(self, layers: set[str], reasons_by_layer: dict[str, set[str]]) -> str:
        parts: list[str] = []
        for layer in _INDEX_LAYERS:
            if layer not in layers:
                continue
            reasons = sorted(reasons_by_layer.get(layer) or [])
            parts.append(f"{layer}: {', '.join(reasons) if reasons else 'unspecified trigger'}")
        return "; ".join(parts) if parts else "project: unspecified trigger"

    def signal_change(self, layer: str = "project", reason: str = "change signal") -> None:
        if layer not in _INDEX_LAYERS:
            raise ValueError(f"Unsupported index layer: {layer}")
        with self._lock:
            self._pending_layers.add(layer)
            self._record_pending_reason(layer, reason)
            if self._running:
                self._pending_after_build = True
                _dashboard_log(
                    f"IndexBuilder: queued {layer} index update ({self._normalize_reason(reason)}) while build is running."
                )
                return
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._run_build)
            self._timer.daemon = True
            self._timer.start()
            _dashboard_log(
                f"IndexBuilder: scheduled {self._format_layers(self._pending_layers)} index update in {self._delay:.1f}s "
                f"({self._format_reason_summary(self._pending_layers, self._pending_reasons)})."
            )

    def signal_startup(
        self,
        delay: float = 1.0,
        layers: set[str] | None = None,
        reason: str = "startup stale check",
    ) -> None:
        """Arm a startup rebuild with a short fixed delay, bypassing the debounce."""
        requested_layers = set(layers or {"project"})
        invalid = requested_layers.difference(_INDEX_LAYERS)
        if invalid:
            raise ValueError(f"Unsupported index layers: {sorted(invalid)}")
        with self._lock:
            self._pending_layers.update(requested_layers)
            for layer in requested_layers:
                self._record_pending_reason(layer, reason)
            if self._running:
                _dashboard_log(
                    f"IndexBuilder: startup request ignored while build is running "
                    f"({self._format_reason_summary(requested_layers, self._pending_reasons)})."
                )
                return
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(delay, self._run_build)
            self._timer.daemon = True
            self._timer.start()
            _dashboard_log(
                f"IndexBuilder: scheduled startup {self._format_layers(requested_layers)} index update in {delay:.1f}s "
                f"({self._format_reason_summary(requested_layers, self._pending_reasons)})."
            )

    def get_status(self, layer: str = "project") -> dict[str, Any]:
        if layer not in _INDEX_LAYERS:
            raise ValueError(f"Unsupported index layer: {layer}")
        with self._lock:
            return dict(self._layer_states[layer])

    def _run_build(self) -> None:
        with self._lock:
            self._timer = None
            self._running = True
            self._status = "running"
            self._active_layers = set(self._pending_layers or {"project"})
            self._pending_layers.clear()
            active_reasons = {
                layer: set(self._pending_reasons[layer]) for layer in _INDEX_LAYERS
            }
            self._active_reasons = active_reasons
            self._pending_reasons = {layer: set() for layer in _INDEX_LAYERS}
            self._build_started_at = datetime.now(UTC).isoformat()
            self._build_finished_at = None
            for layer in self._active_layers:
                self._layer_states[layer]["build_status"] = "running"
                self._layer_states[layer]["build_started_at"] = self._build_started_at
                self._layer_states[layer]["build_finished_at"] = None
        _dashboard_log(
            f"IndexBuilder: starting {self._format_layers(self._active_layers)} index update "
            f"({self._format_reason_summary(self._active_layers, active_reasons)})."
        )

        self._on_started()

        exit_code = self._execute()

        with self._lock:
            self._running = False
            self._build_finished_at = datetime.now(UTC).isoformat()
            self._status = "done" if exit_code == 0 else "failed"
            completed_layers = set(self._active_layers)
            completed_reasons = {
                layer: set(self._active_reasons[layer]) for layer in _INDEX_LAYERS
            }
            for layer in self._active_layers:
                self._layer_states[layer]["build_status"] = self._status
                self._layer_states[layer]["build_finished_at"] = self._build_finished_at
            if exit_code != 0:
                _dashboard_log(
                    f"IndexBuilder: {self._format_layers(completed_layers)} index update failed (exit {exit_code}) "
                    f"({self._format_reason_summary(completed_layers, completed_reasons)})."
                )
            else:
                _dashboard_log(
                    f"IndexBuilder: completed {self._format_layers(completed_layers)} index update "
                    f"({self._format_reason_summary(completed_layers, completed_reasons)})."
                )
            rearm = self._pending_after_build
            self._pending_after_build = False
            self._active_layers = set()
            self._active_reasons = {layer: set() for layer in _INDEX_LAYERS}

        self._on_done()

        if rearm:
            with self._lock:
                t = threading.Timer(self._delay, self._run_build)
                t.daemon = True
                t.start()
                self._timer = t
                _dashboard_log(
                    f"IndexBuilder: rearmed {self._format_layers(self._pending_layers)} index update in {self._delay:.1f}s "
                    f"({self._format_reason_summary(self._pending_layers, self._pending_reasons)})."
                )

    def _execute(self) -> int:
        indexer_path = self._root / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
        venv_base = Path(os.environ.get("WAVEFOUNDRY_TOOL_VENV", "~/.wavefoundry/venv")).expanduser()
        venv_python = venv_base / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python_exec = str(venv_python) if venv_python.exists() else sys.executable
        with self._lock:
            active_layers = set(self._active_layers or {"project"})
        try:
            layer_cmds: list[tuple[str, list[str]]] = []
            if "project" in active_layers:
                # indexer.py reads workflow-config project include-prefixes itself.
                project_cmd = [python_exec, str(indexer_path), "--root", str(self._root), "--content", "all"]
                layer_cmds.append(("project", project_cmd))
            for layer, cmd in layer_cmds:
                state_path = self._index_state_path(layer)
                content = "all" if layer == "project" else "docs"
                log_path = self._index_log_path(layer, content)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                state_path.parent.mkdir(parents=True, exist_ok=True)
                started_at = time.time()
                try:
                    with open(log_path, "w", encoding="utf-8") as log_file:
                        proc = subprocess.Popen(
                            cmd,
                            start_new_session=True,
                            close_fds=True,
                            stdout=log_file,
                            stderr=log_file,
                            env={**os.environ, "WAVEFOUNDRY_TIMESTAMP_LOGS": "1"},
                        )
                        state_path.write_text(
                            json.dumps({"pid": proc.pid, "started_at": started_at, "content": "all" if layer == "project" else "docs", "layer": layer, "full": False, "mode": "update"}),
                            encoding="utf-8",
                        )
                        proc.communicate()
                finally:
                    try:
                        state_path.unlink(missing_ok=True)
                    except Exception:  # noqa: BLE001
                        pass
                if proc.returncode != 0:
                    try:
                        log_text = log_path.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        log_text = ""
                    if "Another index build is already running" in log_text or "lock file busy" in log_text:
                        _dashboard_log(
                            f"IndexBuilder: {layer} index update skipped because another build is already running."
                        )
                        continue
                    return proc.returncode
            return 0
        except FileNotFoundError:
            _dashboard_log("IndexBuilder: indexer executable not found")
            return -1
        except Exception as exc:  # noqa: BLE001
            _dashboard_log(f"IndexBuilder error: {exc}")
            return -1

    def _index_state_path(self, layer: str = "project") -> Path:
        return self._root / ".wavefoundry" / "index" / "index-build.json"

    def _index_log_path(self, layer: str = "project", content: str = "all") -> Path:
        return self._root / ".wavefoundry" / "logs" / f"project-index-build-{content}.log"


def _get_graph_query():
    global _GRAPH_QUERY_MOD
    if _GRAPH_QUERY_MOD is None:
        import importlib.util

        query_path = Path(__file__).resolve().parent / "graph_query.py"
        spec = importlib.util.spec_from_file_location("dashboard_graph_query", query_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load graph_query from {query_path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        _GRAPH_QUERY_MOD = mod
    return _GRAPH_QUERY_MOD


_GRAPH_QUERY_MOD = None


def _graph_neighbors_payload(root: Path, *, layer: str, symbol: str) -> dict[str, Any]:
    try:
        gq = _get_graph_query()
        index = gq.GraphQueryIndex.from_root(root, layer=layer)
        if not index.present:
            return {"present": False, "layer": layer, "symbol": symbol, "diagnostic": "graph_not_ready"}
        node_id = index.resolve_symbol(symbol)
        if not node_id:
            return {"present": False, "layer": layer, "symbol": symbol, "diagnostic": "symbol_not_found"}
        neighbors = index.one_hop_neighbors([node_id])
        neighbors["focus_node_id"] = node_id
        return neighbors
    except Exception as exc:  # noqa: BLE001
        return {"present": False, "layer": layer, "symbol": symbol, "diagnostic": "error", "message": str(exc)}


def _project_index_inputs_stale(root: Path, meta: dict[str, Any]) -> bool | None:
    # Canonical implementation now lives in indexer.project_index_inputs_stale
    # (moved in wave 1p5xu so the MCP in-session monitor and the dashboard share
    # one cheap stat-fast-path check). Behavior is unchanged.
    try:
        return _get_indexer().project_index_inputs_stale(root, meta)
    except Exception:  # noqa: BLE001
        return None


def _index_is_stale(root: Path, layer: str = "project") -> bool:
    """Return True if the selected index layer is missing or its inputs differ from meta.json.

    Staleness is derived from the index ``file_meta`` snapshot (and related meta fields),
    not from git history or working-tree dirtiness. Uncommitted or committed git changes
    that do not alter indexed input hashes must not mark the layer stale.
    """
    if layer not in _INDEX_LAYERS:
        raise ValueError(f"Unsupported index layer: {layer}")
    meta_path = root / ".wavefoundry" / "index" / "meta.json"
    if not meta_path.exists():
        return True
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if not meta.get("built_at", ""):
            return True
    except (OSError, json.JSONDecodeError, ValueError):
        return True

    project_file_meta_stale = _project_index_inputs_stale(root, meta)
    if project_file_meta_stale is not None:
        return project_file_meta_stale

    return False


# ── Snapshot store ────────────────────────────────────────────────────────────

class _SseClient:
    __slots__ = ("queue",)

    def __init__(self) -> None:
        self.queue: queue.Queue[str] = queue.Queue(maxsize=4)


class SnapshotStore:
    """In-memory dashboard model.

    Built once at startup, then updated in a background thread whenever watched
    files change. API handlers read the cached snapshot without touching disk.
    Git stats are rebuilt at most every _GIT_INTERVAL seconds; the timer resets
    whenever mtime polling detects a file change.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._lock = threading.RLock()
        self._snapshot: dict[str, Any] = {}
        self._ready = threading.Event()
        self._stop_event = threading.Event()  # set by stop() to terminate _watch_loop
        self._sse_lock = threading.Lock()
        self._sse_clients: list[_SseClient] = []
        self._last_mtimes: dict[str, float] = {}
        self._last_git_at: float = 0.0
        self._cached_git: dict[str, Any] = {}
        self._content_hash: str = ""
        self._upgrade_paused: bool = False  # R2: True while upgrade lock file is present

        cfg = dashboard_lib.read_dashboard_config(root)
        if cfg["auto_index"]:
            self._index_builder: IndexBuilder | None = IndexBuilder(
                root=root,
                delay=float(cfg["auto_index_delay_seconds"]),
                on_done=self._on_index_build_done,
                on_started=self._on_index_build_done,
            )
        else:
            self._index_builder = None
        # Check staleness once at startup so the first snapshot already has the state.
        self._index_stale: dict[str, bool | None] = {
            layer: _index_is_stale(root, layer) for layer in _INDEX_LAYERS
        }
        self._last_display_staleness_at: float = time.monotonic()

        # R2: Check for upgrade lock at startup — if present, enter upgrade_paused
        # immediately and skip the startup stale check / index build scheduling.
        if self._check_upgrade_lock():
            _dashboard_log(
                "Upgrade in progress (upgrade-in-progress.json detected) — "
                "indexing paused until upgrade completes."
            )
            self._upgrade_paused = True

        # Build the initial snapshot (including git) before serving requests.
        self._rebuild(force_git=True)
        self._ready.set()

        if not self._upgrade_paused:
            startup_layers = {
                layer for layer, stale in self._index_stale.items() if stale
            }
            if self._index_builder is not None and startup_layers:
                _dashboard_log(
                    f"Index is stale at startup — scheduling {IndexBuilder._format_layers(startup_layers)} update."
                )
                self._index_builder.signal_startup(layers=startup_layers, reason="startup stale check")

        t = threading.Thread(
            target=self._watch_loop, daemon=True, name="wf-dashboard-watcher"
        )
        t.start()

    def get(self) -> dict[str, Any]:
        self._ready.wait()
        with self._lock:
            return self._snapshot

    # ── private ───────────────────────────────────────────────────────────────

    def _watched_paths(self) -> list[Path]:
        r = self._root
        return [
            r / "docs" / "waves",
            r / "docs" / "plans",
            r / "docs" / "agents",
            r / ".claude" / "agents",
            r / "docs" / "workflow-config.json",
            r / "docs" / "agents" / "session-handoff.md",
            r / "docs" / "prompts" / "prompt-surface-manifest.json",
            r / ".wavefoundry" / "index" / "index-build.json",
            r / ".wavefoundry" / "index" / "background-build.pid",
            r / ".wavefoundry" / "index" / "index-build-stats.json",
            r / ".wavefoundry" / "index" / "graph" / "project-graph.json",
            r / ".wavefoundry" / "logs" / "project-index-build.log",
            r / ".wavefoundry" / "logs" / "project-index-build-docs.log",
            r / ".wavefoundry" / "logs" / "project-index-build-code.log",
            r / ".wavefoundry" / "logs" / "project-index-build-all.log",
            r / ".wavefoundry" / "logs" / "project-background-build.log",
        ]

    def _current_mtimes(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for p in self._watched_paths():
            try:
                out[str(p)] = p.stat().st_mtime
            except OSError:
                out[str(p)] = 0.0
        return out

    @staticmethod
    def _hash_snapshot(snap: dict[str, Any]) -> str:
        """Stable content hash of snapshot, excluding the generated_at timestamp."""
        filtered = {k: v for k, v in snap.items() if k != "generated_at"}
        return hashlib.md5(
            json.dumps(filtered, sort_keys=True, default=str).encode()
        ).hexdigest()

    def _rebuild(self, force_git: bool = False) -> bool:
        """Rebuild the snapshot. Returns True if content changed."""
        now = time.monotonic()
        do_git = force_git or (now - self._last_git_at >= _GIT_INTERVAL)
        snap = dashboard_lib.collect_dashboard_snapshot(self._root, skip_git=not do_git)
        if do_git:
            self._last_git_at = now
            self._cached_git = snap.get("git", {})
        else:
            snap["git"] = self._cached_git
        # Wave 1p4ww: single project index — the framework layer is folded in.
        proj = snap.setdefault("health", {}).setdefault("index", {}).setdefault("project", {})
        if self._index_builder is not None:
            proj_builder = self._index_builder.get_status("project")
            # Preserve live builder state, but clear stale failed snapshots when the
            # builder is idle so the dashboard does not keep showing a past failure.
            if proj_builder.get("build_status") == "running":
                proj.update(proj_builder)
            elif proj_builder.get("build_status") == "failed":
                proj.update(proj_builder)
            elif proj.get("build_status") == "failed":
                proj.pop("build_status", None)
        if self._index_builder is not None and proj.get("build_status") is None:
            proj["build_status"] = "idle"
        # Wave 1p5xw: the dashboard no longer runs a continuous staleness poll.
        # Compute index staleness on demand here (read-only, for display only) using
        # the shared cheap stat-fast-path check, so the UI reflects current state
        # without a background monitor. Skip while a build is running to avoid
        # flapping the indicator mid-build (the build-done callback resets it).
        building = self._index_builder is not None and self._index_builder._running
        now = time.monotonic()
        if not building and (now - self._last_display_staleness_at) >= _DISPLAY_STALENESS_MIN_INTERVAL:
            self._last_display_staleness_at = now
            for layer in _INDEX_LAYERS:
                self._index_stale[layer] = _index_is_stale(self._root, layer)
        if self._index_stale.get("project") is not None:
            proj["stale"] = self._index_stale["project"]
        # R2: surface upgrade_paused state in snapshot so the UI can show the right message.
        snap["upgrade_paused"] = self._upgrade_paused
        new_hash = self._hash_snapshot(snap)
        with self._lock:
            changed = new_hash != self._content_hash
            self._content_hash = new_hash
            self._snapshot = snap
        return changed

    def _check_upgrade_lock(self) -> bool:
        """Return True if a live upgrade lock file is present (R2)."""
        try:
            import upgrade_lib as _ulib
            lock = _ulib.read_upgrade_lock(self._root)
            if lock is None:
                return False
            # Wave 1p44o — DATA SAFETY: a post-mutation upgrade failure RETAINS the
            # lock with a failure marker so the half-replaced tree stays paused. The
            # upgrade process has already exited, so its PID is gone and the lock
            # would otherwise look "stale" below — auto-clearing it would resume the
            # watcher and force-reindex a gate-failed tree. Treat a failure-marked
            # lock as a live pause and do NOT clear it.
            if isinstance(lock, dict) and lock.get("failed_phase"):
                return True
            # Stale lock (crashed upgrade, PID gone) — auto-clear and treat as not locked.
            if _ulib.is_lock_stale(self._root):
                _dashboard_log(
                    "Stale upgrade lock detected (PID not running) — clearing it automatically."
                )
                _ulib.remove_upgrade_lock(self._root)
                return False
            return True
        except ImportError:
            # upgrade_lib not present in older installs — degrade gracefully.
            lock_path = self._root / ".wavefoundry" / "upgrade-in-progress.json"
            return lock_path.exists()

    def _notify_sse(self) -> None:
        with self._sse_lock:
            clients = list(self._sse_clients)
        for c in clients:
            try:
                c.queue.put_nowait("update")
            except queue.Full:
                pass

    def _notify_upgrade_sse(self, state: str) -> None:
        """Emit an upgrade_status SSE event with {"state": "paused" | "idle"} (R2)."""
        with self._sse_lock:
            clients = list(self._sse_clients)
        for c in clients:
            try:
                c.queue.put_nowait(f"upgrade_status:{state}")
            except queue.Full:
                pass

    def _on_index_build_done(self) -> None:
        if self._index_builder is not None:
            for layer in _INDEX_LAYERS:
                status = self._index_builder.get_status(layer)
                if status["build_status"] == "done":
                    self._index_stale[layer] = False
        self._rebuild(force_git=False)
        self._notify_sse()

    def stop(self) -> None:
        """Signal the watcher thread to exit and cancel any pending index builds.

        Safe to call from any thread. Primarily used in tests to prevent daemon threads
        and IndexBuilder timers from outliving a test's setUp/tearDown lifecycle.
        Blocks briefly until any in-progress build completes so callers can safely clean
        up temp directories without racing against ongoing subprocess writes.
        """
        self._stop_event.set()
        if self._index_builder is not None:
            with self._index_builder._lock:
                if self._index_builder._timer is not None:
                    self._index_builder._timer.cancel()
                    self._index_builder._timer = None
            # Wait up to 10s for any already-started build to finish before returning.
            deadline = time.monotonic() + 10.0
            while self._index_builder._running and time.monotonic() < deadline:
                time.sleep(0.05)

    def _watch_loop(self) -> None:
        self._last_mtimes = self._current_mtimes()
        while not self._stop_event.wait(timeout=_WATCH_INTERVAL):
            try:
                # R2: Poll upgrade lock on every watch cycle — cheap stat() call.
                lock_present = self._check_upgrade_lock()
                if lock_present and not self._upgrade_paused:
                    # Upgrade started after dashboard was already running — pause indexing.
                    _dashboard_log(
                        "Upgrade lock appeared — entering upgrade_paused; indexing suspended."
                    )
                    self._upgrade_paused = True
                    self._rebuild(force_git=False)
                    self._notify_sse()
                    self._notify_upgrade_sse("paused")
                elif not lock_present and self._upgrade_paused:
                    # Upgrade completed — resume and trigger post-upgrade reindex.
                    _dashboard_log(
                        "Upgrade lock removed — resuming; triggering post-upgrade reindex."
                    )
                    self._upgrade_paused = False
                    self._rebuild(force_git=True)
                    self._notify_sse()
                    self._notify_upgrade_sse("idle")
                    if self._index_builder is not None:
                        self._index_builder.signal_startup(
                            layers=set(_INDEX_LAYERS),
                            reason="post-upgrade reindex",
                        )
                    continue  # Skip staleness check this cycle; reindex already queued.

                if self._upgrade_paused:
                    # While paused, skip all mtime polling and staleness checks.
                    continue

                current = self._current_mtimes()
                changed_keys = {k for k in current if current[k] != self._last_mtimes.get(k)}
                self._last_mtimes = current
                if changed_keys:
                    # File changed — rebuild the dashboard snapshot.
                    if self._rebuild(force_git=True):
                        self._notify_sse()
                elif time.monotonic() - self._last_git_at >= _GIT_INTERVAL:
                    # Git timer expired — refresh git stats, notify only if they changed.
                    if self._rebuild(force_git=True):
                        self._notify_sse()
                # NOTE (wave 1p5xt / 1p5xw): the dashboard no longer runs a continuous
                # staleness monitor or trigger index builds on a periodic recheck.
                # Continuous index-freshness monitoring now lives in the MCP server
                # (1p5xu), which is the index's query consumer. The dashboard is a
                # read-only health UI: index staleness for display is computed on
                # demand when the snapshot is built (see _rebuild) and refreshed by the
                # one-shot startup check (#1) and post-upgrade reindex (#3) paths.
            except Exception as exc:  # noqa: BLE001
                _dashboard_log(f"watcher error: {exc}")

    def register_sse_client(self) -> _SseClient:
        client = _SseClient()
        with self._sse_lock:
            self._sse_clients.append(client)
        return client

    def unregister_sse_client(self, client: _SseClient) -> None:
        with self._sse_lock:
            try:
                self._sse_clients.remove(client)
            except ValueError:
                pass


# ── HTTP handler ──────────────────────────────────────────────────────────────

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", ""})


def _asset_path(name: str) -> Path:
    asset_root = ASSET_ROOT.resolve()
    candidate = (ASSET_ROOT / name).resolve()
    if not candidate.is_relative_to(asset_root):
        raise FileNotFoundError(name)
    return candidate


def _dashboard_title(snapshot: dict[str, Any] | None = None) -> str:
    project = (snapshot or {}).get("project", {})
    repo_name = str(project.get("repo_basename") or project.get("name") or "").strip()
    return f"{repo_name} - Wavefoundry" if repo_name else "Wavefoundry"


def _is_port_free(host: str, port: int) -> bool:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


_PEER_DISCONNECT_ERRORS = (ConnectionResetError, BrokenPipeError, ConnectionAbortedError)


class _QuietThreadingHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer that silences expected peer-disconnect errors."""

    def handle_error(self, request: Any, client_address: Any) -> None:
        import sys
        exc = sys.exc_info()[1]
        if isinstance(exc, _PEER_DISCONNECT_ERRORS):
            return  # browser closed or refreshed — not an error worth logging
        super().handle_error(request, client_address)


def choose_port(root: Path, host: str, override_port: int | None = None) -> int:
    config = dashboard_lib.read_dashboard_config(root)
    metadata = dashboard_lib.read_dashboard_metadata(root)
    if override_port is not None:
        return override_port

    candidates: list[int] = []
    recorded = metadata.get("port")
    if isinstance(recorded, int):
        candidates.append(recorded)
    preferred = config.get("preferred_port")
    if isinstance(preferred, int):
        candidates.append(preferred)

    start = int(config.get("port_range_start", 43127))
    end = int(config.get("port_range_end", 43147))
    candidates.extend(port for port in range(start, end + 1))

    seen: set[int] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if _is_port_free(host, candidate):
            return candidate
    raise RuntimeError(
        f"No free dashboard port available on {host} in configured range {start}-{end}."
    )


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "WavefoundryDashboard/1.0"

    @property
    def _store(self) -> SnapshotStore:
        return self.server.snapshot_store  # type: ignore[attr-defined]

    def _send_json(self, payload: Any, status: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_asset(self, rel_name: str, content_type: str) -> None:
        try:
            asset = _asset_path(rel_name)
            if rel_name == "dashboard.html":
                data = asset.read_text(encoding="utf-8").replace("__DASHBOARD_TITLE__", _dashboard_title(self._store.get()))
                data = data.encode("utf-8")
            else:
                data = asset.read_bytes()
        except (FileNotFoundError, OSError):
            self.send_error(HTTPStatus.NOT_FOUND, f"Asset not found: {rel_name}")
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _sse_write(self, event: str, data: dict[str, Any]) -> None:
        msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
        self.wfile.write(msg.encode("utf-8"))
        self.wfile.flush()

    def _handle_sse(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        client = self._store.register_sse_client()
        try:
            self._sse_write("connected", {})
            while True:
                try:
                    msg = client.queue.get(timeout=_SSE_HEARTBEAT)
                    # R2: upgrade_status events carry a state payload; all others are "update".
                    if isinstance(msg, str) and msg.startswith("upgrade_status:"):
                        state = msg.split(":", 1)[1]
                        self._sse_write("upgrade_status", {"state": state})
                    else:
                        self._sse_write("update", {})
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (OSError, BrokenPipeError):
            pass
        finally:
            self._store.unregister_sse_client(client)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", ""):
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/dashboard.html")
            self.end_headers()
            return
        if path == "/dashboard.html":
            return self._send_asset("dashboard.html", "text/html; charset=utf-8")
        _STATIC_TYPES = {
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }
        if path.startswith("/") and "." in path:
            suffix = path[path.rfind("."):]
            ct = _STATIC_TYPES.get(suffix)
            if ct:
                return self._send_asset(path.lstrip("/"), ct)
        if path == "/api/events":
            return self._handle_sse()
        if path == "/api/doc":
            return self._handle_doc()
        snapshot = self._store.get()
        if path == "/api/dashboard":
            return self._send_json(snapshot)
        if path == "/api/health":
            return self._send_json(snapshot.get("health", {}))
        if path == "/api/project":
            return self._send_json(snapshot.get("project", {}))
        if path == "/api/graph":
            # Wave 1p4ww: single project graph — framework/union layers removed.
            params = parse_qs(urlparse(self.path).query)
            layer = (params.get("layer") or ["project"])[0].strip().lower() or "project"
            if layer != "project":
                return self._send_json({"error": f"Unsupported graph layer: {layer}"}, status=HTTPStatus.BAD_REQUEST)
            return self._send_json(dashboard_lib.read_graph_payload(self._store._root, layer))
        if path == "/api/graph/neighbors":
            params = parse_qs(urlparse(self.path).query)
            layer = (params.get("layer") or ["project"])[0].strip().lower() or "project"
            symbol = unquote((params.get("symbol") or [""])[0]).strip()
            if layer != "project":
                return self._send_json({"error": f"Unsupported graph layer: {layer}"}, status=HTTPStatus.BAD_REQUEST)
            if not symbol:
                return self._send_json({"error": "Missing symbol parameter"}, status=HTTPStatus.BAD_REQUEST)
            return self._send_json(_graph_neighbors_payload(self._store._root, layer=layer, symbol=symbol))
        if path == "/api/diff":
            params = parse_qs(urlparse(self.path).query)
            rel_path = unquote((params.get("path") or [""])[0]).strip()
            if not rel_path:
                self.send_error(HTTPStatus.BAD_REQUEST, "Missing path parameter")
                return
            diff_text, status_code = dashboard_lib.get_file_diff(self._store._root, rel_path)
            if status_code == 400:
                self.send_error(HTTPStatus.BAD_REQUEST, "Path traversal denied")
                return
            data = diff_text.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _handle_doc(self) -> None:
        """Serve raw markdown for a wave or change document."""
        params = parse_qs(urlparse(self.path).query)
        doc_type  = (params.get("type") or [""])[0]
        doc_id    = unquote((params.get("id")   or [""])[0]).strip()
        wave_id   = unquote((params.get("wave") or [""])[0]).strip()
        doc_path  = unquote((params.get("path") or [""])[0]).strip()

        root      = self._store._root
        docs_root = (root / "docs").resolve()

        if doc_type == "wave" and doc_id:
            target = root / "docs" / "waves" / doc_id / "wave.md"
        elif doc_type == "change" and doc_id and doc_path:
            # Prefer the explicit path from the change record (works for both
            # wave-scoped and plan-scoped changes).
            target = root / doc_path
        elif doc_type == "change" and doc_id and wave_id:
            # Fallback: reconstruct path from wave_id (legacy callers).
            target = root / "docs" / "waves" / wave_id / f"{doc_id}.md"
        else:
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing or invalid type/id parameters")
            return

        # Security: resolved path must stay within docs/ and be a markdown file.
        try:
            target.resolve().relative_to(docs_root)
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN, "Path traversal denied")
            return
        if target.suffix.lower() != ".md":
            self.send_error(HTTPStatus.FORBIDDEN, "Only markdown files are served")
            return

        try:
            text = target.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND, "Document not found")
            return
        except OSError as exc:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
            return

        data = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: Any) -> None:
        _dashboard_log(fmt % args, context=self.address_string())


# ── Entry point ───────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the Wavefoundry local dashboard server.")
    parser.add_argument("--root", default=None, help="Repository root (default: auto-discover)")
    parser.add_argument("--host", default="", help="Override bind host (default: docs/workflow-config.json dashboard.host or 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Override the dashboard port")
    parser.add_argument("--open", action="store_true", help="Open the dashboard in the default browser after binding")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = dashboard_lib.discover_root(args.root)
    try:
        server_lock = dashboard_lib.dashboard_server_lock(root)
        server_lock.__enter__()
    except dashboard_lib.DashboardLockBusy:
        meta = dashboard_lib.read_dashboard_metadata(root)
        url = str(meta.get("url") or "")
        if url:
            print(url, flush=True)
        _dashboard_log("Dashboard already running for this repository.")
        return 0

    cfg = dashboard_lib.read_dashboard_config(root)
    host = args.host.strip() or cfg["host"]
    if host not in _LOOPBACK_HOSTS:
        _dashboard_log(
            f"WARNING: binding to non-loopback host '{host}'. "
            "The dashboard is designed for local-only access."
        )
    port = choose_port(root, host, args.port)

    httpd = _QuietThreadingHTTPServer((host, port), DashboardHandler)
    httpd.repo_root = root  # type: ignore[attr-defined]

    # Write metadata immediately after binding so MCP callers can detect the URL
    # without waiting for the (potentially slow) initial snapshot build.
    entrypoint = cfg["entrypoint"]
    url = f"http://{host}:{port}/{entrypoint}"
    dashboard_lib.write_dashboard_metadata(
        root,
        {
            "host": host,
            "port": port,
            "url": url,
            "entrypoint": entrypoint,
            "pid": os.getpid(),
            "started_at": datetime.now(UTC).isoformat(),
        },
    )
    print(url, flush=True)
    if args.open and dashboard_lib.dashboard_browser_open_enabled():
        webbrowser.open(url, new=2)

    httpd.snapshot_store = SnapshotStore(root)  # type: ignore[attr-defined]
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard server stopped.", file=sys.stderr)
    finally:
        httpd.server_close()
        server_lock.__exit__(None, None, None)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

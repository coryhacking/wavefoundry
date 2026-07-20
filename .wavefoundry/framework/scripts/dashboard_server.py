#!/usr/bin/env python3
"""Local dashboard server for Wave Framework repositories."""
from __future__ import annotations

import argparse
import concurrent.futures
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

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import venv_bootstrap  # the single venv resolver (wave 1p7pl)
import subprocess_util  # shared subprocess isolation (wave 1p8gu)
import cli_stdio  # shared UTF-8 stdio reconfigure (wave 1p8gv)

# Activate the shared tool venv IN-PROCESS before any heavy import (wave 1p7pl/1p802). No-op when
# already in the venv or when it does not exist yet (fresh bootstrap).
venv_bootstrap.activate_tool_venv()
# Wave 1p8gv: CLI entry — UTF-8 stdout/stderr so non-ASCII prints never raise on a cp1252 console.
cli_stdio.configure_utf8_stdio()

import dashboard_lib


ASSET_ROOT = Path(__file__).resolve().parent.parent / "dashboard"

_GIT_INTERVAL = 60       # seconds between git stat rebuilds
_WATCH_INTERVAL = 3.0    # seconds between mtime polls
_SSE_HEARTBEAT = 15      # seconds between SSE keep-alive comments
# Wave 1rtju: bound the watcher's snapshot collection so a slow/hung filesystem or git call cannot
# freeze the single watcher thread for the process lifetime. On timeout the loop keeps the last-good
# snapshot and surfaces a stall signal instead of publishing partial state. 30s is a generous bounded
# multiple of the 3s watch interval — far above a normal sub-second collection, so the healthy path is
# unchanged.
_COLLECT_TIMEOUT_SECONDS = 30.0
# Wave 1rtju: a watcher is considered stalled (surfaced on /api/dashboard + an SSE signal) when it has
# not completed a cycle within this window — a bounded multiple of the git-refresh interval, above one
# legitimately-slow collect-timeout cycle so a single slow cycle is not a false stall.
_WATCHER_STALL_SECONDS = 90.0
# Wave 1rtju: bound the recursive nested-tree mtime scan so it can never become an unbounded walk on a
# pathological docs tree (no-busy-loop AC-6). The watched doc trees are far smaller than this.
_NESTED_SCAN_MAX_ENTRIES = 20000
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


# Wave 1rtju (AC-5): the repo root for the always-on log sink, set once in main() after root discovery.
# When set, _dashboard_log persists to .wavefoundry/logs/dashboard.log so watcher/error lines survive
# the MCP-spawn DEVNULL stdout/stderr (server_impl.py) — previously only the --daemon path logged to a
# file, so a stall under the normal MCP launch was undiagnosable.
_LOG_ROOT: Path | None = None


def _dashboard_log(message: str, *, context: str | None = None, persist: bool = True) -> None:
    prefix = f"{datetime.now(UTC).isoformat()} - "
    if context:
        prefix += f"{context} - "
    line = f"[dashboard] {prefix}{message}\n"
    sys.stderr.write(line)
    # Wave 1rtju: also persist to dashboard.log so watcher/lifecycle diagnostics are captured even when
    # stderr is DEVNULL (the MCP-tool spawn path). `persist=False` keeps the per-request HTTP access-log
    # firehose (log_message) OFF the file so it can't grow unbounded — access lines still reach stderr
    # (and the --daemon child's stderr is already the file, so that path is unchanged either way). Skip
    # the direct write when we ARE the --daemon child whose stderr is ALREADY redirected to dashboard.log
    # (_daemonize) — that would double-write every line.
    if persist and _LOG_ROOT is not None and os.environ.get(_DAEMON_ENV_MARKER) != "1":
        try:
            log_path = _LOG_ROOT / ".wavefoundry" / "logs" / "dashboard.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError:
            pass


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
    """Return True if the selected index layer is missing or its inputs differ from the store snapshot.

    Staleness is derived from the index ``file_meta`` snapshot (and related meta fields),
    not from git history or working-tree dirtiness. Uncommitted or committed git changes
    that do not alter indexed input hashes must not mark the layer stale.
    """
    if layer not in _INDEX_LAYERS:
        raise ValueError(f"Unsupported index layer: {layer}")
    # 1sed6: readiness = the store's completed build epoch; state = the
    # store snapshot (meta.json retired).
    index_dir = root / ".wavefoundry" / "index"
    try:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "index_state_store",
            Path(__file__).resolve().parent / "index_state_store.py",
        )
        _iss = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_iss)
        if _iss.build_epoch_token(index_dir) is None:
            return True
        # Full per-file snapshot is REQUIRED here (bounded-read exception):
        # this IS the staleness compare against current file inputs, and it
        # runs on the daemon's periodic timer, never the HTTP request path.
        meta = _iss.export_meta_snapshot(index_dir) or {}
    except Exception:
        return True

    project_file_meta_stale = _project_index_inputs_stale(root, meta)
    if project_file_meta_stale is not None:
        return project_file_meta_stale

    return False


# ── SSE + snapshot store ───────────────────────────────────────────────────────


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
        self._last_mtimes: dict[str, float | str] = {}
        self._last_git_at: float = 0.0
        self._cached_git: dict[str, Any] = {}
        self._content_hash: str = ""
        self._upgrade_paused: bool = False  # R2: True while upgrade lock file is present
        # Wave 1rtju: bound the watcher's snapshot collection with a single-worker executor so a hung
        # FS/git call cannot freeze the watcher thread. A timed-out collection stays referenced in
        # _pending_collect so the next cycle does NOT resubmit (no piling up) until it finally returns.
        self._collect_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="wf-dashboard-collect"
        )
        self._pending_collect: concurrent.futures.Future | None = None
        # Wave 1rtju: watcher-liveness signals, surfaced on /api/dashboard + an SSE watcher_status event
        # so a "stale but still serving" watcher becomes visible instead of silent. Read at request time
        # (see watcher_health) so a blocked watcher's staleness is observable even mid-block.
        self._last_watch_cycle_at: float = time.monotonic()
        self._watcher_stalled: bool = False
        # Wave 1rtju: dedupe consecutive identical watcher-error log lines so a persistently-raising
        # collect/stat (e.g. a flaky mount) cannot append the same line to dashboard.log every 3s. Reset
        # on any clean cycle so a recurrence after recovery is logged again.
        self._last_watcher_error: str | None = None

        cfg = dashboard_lib.read_dashboard_config(root)
        # 1p7it: the dashboard does NOT trigger index builds — index updates are owned by the
        # MCP/hook background path (post-edit hook + the MCP server's background refresh +
        # index_build). The dashboard is a read-only viewer; build status it shows comes from
        # the shared index-build state (collect_health → index_build_status_response).
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

        # 1p7it: no startup index trigger — staleness is shown read-only; the MCP/hook path reindexes.

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

    def _watched_trees(self) -> list[Path]:
        """Directory trees whose NESTED files must trip the fast-change path (wave 1rtju, AC-3).

        The flat directory-mtime watch in ``_watched_paths`` only sees direct-child add/remove/rename;
        a directory's mtime does not change when a file nested inside an existing subdirectory is edited
        (the common ``docs/waves/<id>/<change>.md`` / ``wave.md`` editing pattern). These trees get a
        bounded recursive mtime signature so nested edits surface promptly instead of only on the 60s
        git fallback."""
        r = self._root
        return [
            r / "docs" / "waves",
            r / "docs" / "plans",
            r / "docs" / "agents",
            r / ".claude" / "agents",
        ]

    def _nested_signature(self, base: Path) -> str:
        """A bounded recursive signature (max-mtime + file-count) over a watched tree (wave 1rtju).

        Any nested-file EDIT bumps that file's mtime → raises max-mtime; an add/remove changes the file
        count. Both change the signature, tripping the fast-change path. The walk is bounded by
        ``_NESTED_SCAN_MAX_ENTRIES`` so it can never become an unbounded scan (no-busy-loop AC-6). Cheap
        relative to the existing unconditional 60s full git recollect."""
        if not base.is_dir():
            return ""
        max_mtime = 0.0
        count = 0
        for dirpath, _dirnames, filenames in os.walk(base):
            for fn in filenames:
                count += 1
                try:
                    m = os.stat(os.path.join(dirpath, fn)).st_mtime
                except OSError:
                    continue
                if m > max_mtime:
                    max_mtime = m
                if count >= _NESTED_SCAN_MAX_ENTRIES:
                    return f"{max_mtime:.6f}:{count}:capped"
        return f"{max_mtime:.6f}:{count}"

    def _current_mtimes(self) -> dict[str, float | str]:
        out: dict[str, float | str] = {}
        for p in self._watched_paths():
            try:
                out[str(p)] = p.stat().st_mtime
            except OSError:
                out[str(p)] = 0.0
        # Wave 1rtju (AC-3): add a bounded nested signature per watched tree so edits to files nested
        # inside them trip the fast-change diff (the flat dir stat above misses nested writes).
        for tree in self._watched_trees():
            out[f"tree::{tree}"] = self._nested_signature(tree)
        return out

    @staticmethod
    def _hash_snapshot(snap: dict[str, Any]) -> str:
        """Stable content hash of snapshot, excluding the generated_at timestamp."""
        filtered = {k: v for k, v in snap.items() if k != "generated_at"}
        return hashlib.md5(
            json.dumps(filtered, sort_keys=True, default=str).encode()
        ).hexdigest()

    def _collect_bounded(self, skip_git: bool) -> dict[str, Any] | None:
        """Run ``collect_dashboard_snapshot`` under a per-cycle timeout (wave 1rtju, AC-1).

        Returns the snapshot, or ``None`` if the collection did not finish within
        ``_COLLECT_TIMEOUT_SECONDS`` — in which case the still-running future is retained so the next
        cycle does not resubmit work on top of a hung call (bounded to one in-flight collection).
        Non-timeout exceptions raised inside the collection propagate to the caller (surfaced as a
        watcher error by ``_watch_loop``), preserving the prior direct-call error behavior."""
        if self._pending_collect is not None:
            if not self._pending_collect.done():
                return None  # previous collection still hung — do not pile up work
            self._pending_collect = None
        future = self._collect_executor.submit(
            dashboard_lib.collect_dashboard_snapshot, self._root, skip_git=skip_git
        )
        try:
            return future.result(timeout=_COLLECT_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            self._pending_collect = future
            return None

    def _rebuild(self, force_git: bool = False) -> bool | None:
        """Rebuild the snapshot. Returns True if content changed, False if unchanged, or None if the
        bounded collection timed out / is still hung (caller keeps the last-good snapshot; wave 1rtju)."""
        now = time.monotonic()
        do_git = force_git or (now - self._last_git_at >= _GIT_INTERVAL)
        snap = self._collect_bounded(skip_git=not do_git)
        if snap is None:
            # Collection timed out / still hung — keep the last-good snapshot and let the watch loop
            # surface the stall signal rather than publishing partial state (AC-1/AC-2 risk mitigation).
            return None
        if do_git:
            self._last_git_at = now
            self._cached_git = snap.get("git", {})
        else:
            snap["git"] = self._cached_git
        # Wave 1p4ww: single project index — the framework layer is folded in.
        proj = snap.setdefault("health", {}).setdefault("index", {}).setdefault("project", {})
        # 1p7it: the dashboard does not run builds — `collect_health` already merges the shared
        # index-build status (the hook/MCP background builds, via index_build_status_response)
        # into proj["build_status"], so the display reflects the real builds with no overlay.
        # Wave 1p5xw: the dashboard no longer runs a continuous staleness poll. Compute index
        # staleness on demand here (read-only, for display only). Skip while a build is running to
        # avoid flapping the indicator mid-build.
        building = proj.get("build_status") == "running"
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

    def _notify_watcher_sse(self, stalled: bool) -> None:
        """Emit a watcher_status SSE event with {"stalled": bool} (wave 1rtju, AC-2).

        Sent only on a stall-state transition so a wedged watcher becomes visible to the client (which
        can force a poll/reconnect) without spamming the stream."""
        with self._sse_lock:
            clients = list(self._sse_clients)
        for c in clients:
            try:
                c.queue.put_nowait(f"watcher_status:{'1' if stalled else '0'}")
            except queue.Full:
                pass

    def watcher_health(self) -> dict[str, Any]:
        """Read-time watcher-liveness view (wave 1rtju, AC-2).

        Computed on request (not written by the possibly-blocked watcher) so a wedged watcher's
        staleness is observable even while it is blocked: ``stalled`` is true when the watcher
        explicitly hit a collection timeout OR has not completed a cycle within ``_WATCHER_STALL_SECONDS``
        (covers a fully-frozen or dead watcher thread)."""
        age = time.monotonic() - self._last_watch_cycle_at
        stalled = self._watcher_stalled or (age > _WATCHER_STALL_SECONDS)
        return {
            "stalled": stalled,
            "last_cycle_age_seconds": round(age, 1),
            "interval_seconds": _WATCH_INTERVAL,
            "stall_threshold_seconds": _WATCHER_STALL_SECONDS,
        }

    def stop(self) -> None:
        """Signal the watcher thread to exit.

        Safe to call from any thread. Primarily used in tests to prevent the daemon watcher
        thread from outliving a test's setUp/tearDown lifecycle. The dashboard runs no index
        builds (1p7it: indexing is MCP/hook-owned), so there is nothing else to cancel.
        """
        self._stop_event.set()
        # Wave 1rtju: release the bounded-collection executor. Don't wait on a possibly-hung collection.
        try:
            self._collect_executor.shutdown(wait=False, cancel_futures=True)
        except Exception:  # noqa: BLE001
            pass

    def _note_cycle_alive(self) -> None:
        """Heartbeat: the watcher completed a loop iteration (feeds the time-based stall check in
        ``watcher_health``). Does NOT clear a collection stall — a no-op cycle with nothing to rebuild
        must not declare recovery while the last collection is still hung and the snapshot is stale."""
        self._last_watch_cycle_at = time.monotonic()

    def _note_cycle_recovered(self) -> None:
        """A rebuild completed successfully — record liveness AND clear any prior stall (emit once).
        Recovery is tied to an actual completed collection, not merely a live watcher thread (1rtju)."""
        self._last_watch_cycle_at = time.monotonic()
        if self._watcher_stalled:
            self._watcher_stalled = False
            _dashboard_log("watcher recovered — snapshot collection completed after a stall.")
            self._notify_watcher_sse(stalled=False)

    def _mark_cycle_stalled(self) -> None:
        """Flag a collection timeout and emit the stall signal once per stall episode (1rtju, AC-2)."""
        if not self._watcher_stalled:
            self._watcher_stalled = True
            _dashboard_log(
                f"watcher stall — snapshot collection exceeded {_COLLECT_TIMEOUT_SECONDS:.0f}s; "
                "keeping last-good snapshot and signalling staleness."
            )
            self._notify_watcher_sse(stalled=True)

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
                    self._note_cycle_alive()
                    continue
                elif not lock_present and self._upgrade_paused:
                    # Upgrade completed — resume display. (1p7it: no dashboard reindex trigger;
                    # the upgrade's own index phase + the MCP/hook path reindex.)
                    _dashboard_log("Upgrade lock removed — resuming dashboard.")
                    self._upgrade_paused = False
                    self._rebuild(force_git=True)
                    self._notify_sse()
                    self._notify_upgrade_sse("idle")
                    self._note_cycle_alive()
                    continue

                if self._upgrade_paused:
                    # While paused, skip all mtime polling and staleness checks — but the cycle itself
                    # completed, so the watcher thread is alive.
                    self._note_cycle_alive()
                    continue

                current = self._current_mtimes()
                changed_keys = {k for k in current if current[k] != self._last_mtimes.get(k)}
                # Wave 1rtju (AC-1/AC-2): a rebuild returns None when the bounded collection timed out /
                # is still hung — keep the last-good snapshot and surface the stall. A completed rebuild
                # (True/False) clears any prior stall; a no-op cycle only heartbeats liveness (it must NOT
                # declare recovery while a collection is still hung and the snapshot is stale).
                git_due = time.monotonic() - self._last_git_at >= _GIT_INTERVAL
                if changed_keys or git_due:
                    # File changed (incl. nested doc edits, AC-3) or git timer expired — rebuild.
                    changed = self._rebuild(force_git=True)
                    if changed is None:
                        # Stall: do NOT commit _last_mtimes — retry this same change set on the next 3s
                        # cycle (the bounded collect returns fast while the prior one is still hung) rather
                        # than consuming the delta and waiting up to the 60s git timer to notice the edit.
                        self._mark_cycle_stalled()
                    else:
                        self._last_mtimes = current
                        if changed:
                            self._notify_sse()
                        self._note_cycle_recovered()
                else:
                    # Nothing to do this cycle — the watcher thread is alive, but do not clear a stall.
                    self._last_mtimes = current
                    self._note_cycle_alive()
                # NOTE (wave 1p5xt / 1p5xw): the dashboard no longer runs a continuous
                # staleness monitor or trigger index builds on a periodic recheck.
                # Continuous index-freshness monitoring now lives in the MCP server
                # (1p5xu), which is the index's query consumer. The dashboard is a
                # read-only health UI: index staleness for display is computed on
                # demand when the snapshot is built (see _rebuild) and refreshed by the
                # one-shot startup check (#1) and post-upgrade reindex (#3) paths.
                self._last_watcher_error = None  # a clean cycle clears the error dedup
            except Exception as exc:  # noqa: BLE001
                # Wave 1rtju: dedupe consecutive identical errors so a persistent per-cycle failure does
                # not flood dashboard.log; the first occurrence and any change are still captured.
                msg = str(exc)
                if msg != self._last_watcher_error:
                    _dashboard_log(f"watcher error: {msg}")
                    self._last_watcher_error = msg

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

    # Wave 1p9hm: HTTPServer defaults allow_reuse_address=1 (SO_REUSEADDR). Disable it ONLY on Windows.
    # On Windows SO_REUSEADDR lets MULTIPLE sockets bind the same port SIMULTANEOUSLY, so two
    # near-simultaneous dashboard spawns could both bind the same port with nondeterministic routing;
    # disabling reuse closes the sub-millisecond TOCTOU window between the _is_port_free probe and the
    # real bind. On POSIX SO_REUSEADDR does NOT permit duplicate live binds — it only allows rebinding
    # a TIME_WAIT port, which is the BENEFICIAL default: choose_port prefers the last-recorded port, so
    # a quick stop→start would otherwise fail with "Address already in use" during TIME_WAIT. Keep the
    # POSIX default enabled to preserve fast restart; the duplicate-bind hazard is Windows-only.
    allow_reuse_address = os.name != "nt"

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
                    # R2: upgrade_status events carry a state payload; wave 1rtju: watcher_status carries
                    # a stalled flag; all others are "update".
                    if isinstance(msg, str) and msg.startswith("upgrade_status:"):
                        state = msg.split(":", 1)[1]
                        self._sse_write("upgrade_status", {"state": state})
                    elif isinstance(msg, str) and msg.startswith("watcher_status:"):
                        stalled = msg.split(":", 1)[1] == "1"
                        self._sse_write("watcher_status", {"stalled": stalled})
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
            # Wave 1rtju (AC-2): attach the read-time watcher-liveness view additively so a stalled
            # watcher is observable to clients. Computed per request (not stored) so it never churns the
            # snapshot content hash and reflects a wedged watcher even while it is blocked.
            return self._send_json({**snapshot, "watcher": self._store.watcher_health()})
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
        # Wave 1rtju: HTTP access lines go to stderr only (persist=False) — do NOT flood the always-on
        # dashboard.log, which is reserved for watcher/lifecycle diagnostics (AC-5).
        _dashboard_log(fmt % args, context=self.address_string(), persist=False)


# ── Entry point ───────────────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the Wavefoundry local dashboard server.")
    parser.add_argument("--root", default=None, help="Repository root (default: auto-discover)")
    parser.add_argument("--host", default="", help="Override bind host (default: docs/workflow-config.json dashboard.host or 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Override the dashboard port")
    parser.add_argument("--open", action="store_true", help="Open the dashboard in the default browser after binding")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Self-detach: re-spawn this server in the background (OS-correct detach), log to "
        ".wavefoundry/logs/dashboard.log, print a started message, and exit. Replaces the bash "
        "`nohup ... &` so the cross-OS `python dashboard_server.py --daemon` forwarder persists.",
    )
    return parser.parse_args(argv)


# Wave 1p7pn (1p7pb-adr, AC-3): self-detach the dashboard into the background, OS-correctly, replacing
# `bin/wave-dashboard`'s bash `nohup ... &` (bash-only, no native-Windows peer). The detached CHILD
# spawn uses `sys.executable` (an absolute path; never `python3`, absent on python.org-Windows). Wave
# 1p802: after in-process activation `sys.executable` is the SYSTEM interpreter — the re-spawned
# dashboard_server.py self-activates the venv first-line, so the child reaches the venv packages.
# Reuses the same detach flags as the MCP server's dashboard spawn.
_DAEMON_ENV_MARKER = "WAVEFOUNDRY_DASHBOARD_DAEMON_CHILD"


def _daemonize(root: Path, argv: list[str]) -> int:
    """Re-spawn this server detached (without `--daemon`), log to dashboard.log, and return 0.

    The child runs the normal foreground path; an env marker prevents an infinite re-spawn loop."""
    log_path = root / ".wavefoundry" / "logs" / "dashboard.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    child_args = [a for a in argv if a != "--daemon"]
    # Wave 1p8pe: prefer the console-free tool-venv pythonw.exe on Windows for this detached daemon
    # re-spawn (all output goes to dashboard.log, no console) so it never flashes a window; falls back
    # to sys.executable (POSIX returns None). The re-spawned child self-activates the venv first-line.
    interp = subprocess_util.windowless_pythonw() or sys.executable
    cmd = [interp, str(Path(__file__).resolve()), *child_args]
    child_env = {**os.environ, _DAEMON_ENV_MARKER: "1"}
    log_handle = open(log_path, "a", encoding="utf-8")
    try:
        # Wave 1p8gu: shared isolated Popen — keeps the log-file stdout/stderr + the daemon env while
        # supplying detached stdin + the detached/no-window Windows creationflags.
        proc = subprocess_util.isolated_popen(
            cmd,
            cwd=str(root),
            env=child_env,
            stdout=log_handle,
            stderr=log_handle,
        )
    finally:
        # The child inherits its own dup'd fd; close our handle so this process doesn't hold the log.
        log_handle.close()
    print(f"Wave dashboard started (pid {proc.pid}). Log: {log_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = dashboard_lib.discover_root(args.root)
    # Wave 1rtju (AC-5): route _dashboard_log to .wavefoundry/logs/dashboard.log for this root so
    # watcher/error lines are captured even under the MCP-spawn DEVNULL stderr. Set before the daemon
    # branch and before SnapshotStore startup so first-cycle logs are persisted.
    global _LOG_ROOT
    _LOG_ROOT = root

    # Wave 1p7pn: `--daemon` self-detaches (unless we ARE the detached child) so the cross-OS
    # `python dashboard_server.py --daemon` forwarder survives shell exit, then exits. The child
    # runs the normal foreground path below.
    if args.daemon and os.environ.get(_DAEMON_ENV_MARKER) != "1":
        full_argv = list(sys.argv[1:] if argv is None else argv)
        return _daemonize(root, full_argv)

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

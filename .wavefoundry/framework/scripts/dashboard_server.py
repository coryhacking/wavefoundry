#!/usr/bin/env python3
"""Local dashboard server for Wave Framework repositories."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
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
from urllib.parse import urlparse

import dashboard_lib


ASSET_ROOT = Path(__file__).resolve().parent.parent / "dashboard"

_GIT_INTERVAL = 60       # seconds between git stat rebuilds
_WATCH_INTERVAL = 3.0    # seconds between mtime polls
_SSE_HEARTBEAT = 15      # seconds between SSE keep-alive comments
_STALENESS_CHECK_INTERVAL = 60.0  # seconds between periodic git-based index staleness checks


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

    def signal_change(self) -> None:
        with self._lock:
            if self._running:
                self._pending_after_build = True
                return
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._delay, self._run_build)
            self._timer.daemon = True
            self._timer.start()

    def signal_startup(self, delay: float = 1.0) -> None:
        """Arm a startup rebuild with a short fixed delay, bypassing the debounce."""
        with self._lock:
            if self._running:
                return
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(delay, self._run_build)
            self._timer.daemon = True
            self._timer.start()

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "build_status": self._status,
                "build_started_at": self._build_started_at,
                "build_finished_at": self._build_finished_at,
            }

    def _run_build(self) -> None:
        with self._lock:
            self._timer = None
            self._running = True
            self._status = "running"
            self._build_started_at = datetime.now(UTC).isoformat()
            self._build_finished_at = None

        self._on_started()

        exit_code = self._execute()

        with self._lock:
            self._running = False
            self._build_finished_at = datetime.now(UTC).isoformat()
            self._status = "done" if exit_code == 0 else "failed"
            if exit_code != 0:
                sys.stderr.write(
                    f"[dashboard] IndexBuilder: index build failed (exit {exit_code})\n"
                )
            rearm = self._pending_after_build
            self._pending_after_build = False

        self._on_done()

        if rearm:
            with self._lock:
                t = threading.Timer(self._delay, self._run_build)
                t.daemon = True
                t.start()
                self._timer = t

    def _execute(self) -> int:
        indexer_path = self._root / ".wavefoundry" / "framework" / "scripts" / "indexer.py"
        cmd = [sys.executable, str(indexer_path), "--root", str(self._root), "--content", "all"]
        try:
            proc = subprocess.Popen(
                cmd,
                start_new_session=True,
                close_fds=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            _, stderr_data = proc.communicate()
            if proc.returncode != 0 and stderr_data:
                sys.stderr.write(
                    f"[dashboard] IndexBuilder stderr: {stderr_data.decode(errors='replace')[:400]}\n"
                )
            return proc.returncode
        except FileNotFoundError:
            sys.stderr.write("[dashboard] IndexBuilder: indexer executable not found\n")
            return -1
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[dashboard] IndexBuilder error: {exc}\n")
            return -1


def _index_is_stale(root: Path) -> bool:
    """Return True if the project index is missing or older than the current git state.

    A file is only considered stale if it was modified *after* the last index build —
    files that were dirty before the build are already indexed and do not count.
    """
    meta_path = root / ".wavefoundry" / "index" / "meta.json"
    if not meta_path.exists():
        return True
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        built_at = meta.get("built_at", "")
        if not built_at:
            return True
        built_at_ts = datetime.fromisoformat(built_at.replace("Z", "+00:00")).timestamp()
    except (OSError, json.JSONDecodeError, ValueError):
        return True

    git = ["git", "-C", str(root)]
    try:
        r = subprocess.run(
            git + ["log", f"--since={built_at}", "--oneline"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return True
    except Exception:  # noqa: BLE001
        pass
    try:
        r = subprocess.run(
            git + ["status", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            for line in r.stdout.splitlines():
                filename = line[3:].strip().split(" -> ")[-1]
                try:
                    if (root / filename).stat().st_mtime > built_at_ts:
                        return True
                except OSError:
                    pass
    except Exception:  # noqa: BLE001
        pass
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
        self._sse_lock = threading.Lock()
        self._sse_clients: list[_SseClient] = []
        self._last_mtimes: dict[str, float] = {}
        self._last_git_at: float = 0.0
        self._cached_git: dict[str, Any] = {}
        self._content_hash: str = ""
        self._last_staleness_check: float = 0.0

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
        self._index_stale: bool | None = _index_is_stale(root)

        # Build the initial snapshot (including git) before serving requests.
        self._rebuild(force_git=True)
        self._ready.set()

        if self._index_builder is not None and self._index_stale:
            sys.stderr.write("[dashboard] Index is stale — scheduling startup index update.\n")
            self._index_builder.signal_startup()

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
            r / "docs" / "workflow-config.json",
            r / "docs" / "agents" / "session-handoff.md",
            r / "docs" / "prompts" / "prompt-surface-manifest.json",
            r / ".wavefoundry" / "index" / "index-build-stats.json",
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
        proj = snap.setdefault("health", {}).setdefault("index", {}).setdefault("project", {})
        if self._index_builder is not None:
            proj.update(self._index_builder.get_status())
        if self._index_stale is not None:
            proj["stale"] = self._index_stale
        new_hash = self._hash_snapshot(snap)
        with self._lock:
            changed = new_hash != self._content_hash
            self._content_hash = new_hash
            self._snapshot = snap
        return changed

    def _notify_sse(self) -> None:
        with self._sse_lock:
            clients = list(self._sse_clients)
        for c in clients:
            try:
                c.queue.put_nowait("update")
            except queue.Full:
                pass

    def _on_index_build_done(self) -> None:
        if self._index_builder is not None:
            status = self._index_builder.get_status()
            if status["build_status"] == "done":
                self._index_stale = False
        self._rebuild(force_git=False)
        self._notify_sse()

    def _watch_loop(self) -> None:
        _stats_key = str(self._root / ".wavefoundry" / "index" / "index-build-stats.json")
        self._last_mtimes = self._current_mtimes()
        while True:
            time.sleep(_WATCH_INTERVAL)
            try:
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
                # Periodic git-based staleness check: catches source code edits that
                # fall outside the watched-path set (e.g. any file in the working tree).
                now = time.monotonic()
                if now - self._last_staleness_check >= _STALENESS_CHECK_INTERVAL and (
                    self._index_builder is None or not self._index_builder._running
                ):
                    self._last_staleness_check = now
                    stale = _index_is_stale(self._root)
                    if stale != self._index_stale:
                        self._index_stale = stale
                        self._rebuild(force_git=False)
                        self._notify_sse()
                        if stale and self._index_builder is not None:
                            self._index_builder.signal_change()
                    else:
                        self._index_stale = stale
            except Exception as exc:  # noqa: BLE001
                sys.stderr.write(f"[dashboard] watcher error: {exc}\n")

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
                    client.queue.get(timeout=_SSE_HEARTBEAT)
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
        snapshot = self._store.get()
        if path == "/api/dashboard":
            return self._send_json(snapshot)
        if path == "/api/health":
            return self._send_json(snapshot.get("health", {}))
        if path == "/api/project":
            return self._send_json(snapshot.get("project", {}))
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write(
            f"[dashboard] {self.address_string()} - {datetime.now(UTC).isoformat()} - {fmt % args}\n"
        )


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
    cfg = dashboard_lib.read_dashboard_config(root)
    host = args.host.strip() or cfg["host"]
    if host not in _LOOPBACK_HOSTS:
        sys.stderr.write(
            f"[dashboard] WARNING: binding to non-loopback host '{host}'. "
            "The dashboard is designed for local-only access.\n"
        )
    port = choose_port(root, host, args.port)

    httpd = _QuietThreadingHTTPServer((host, port), DashboardHandler)
    httpd.repo_root = root  # type: ignore[attr-defined]
    httpd.snapshot_store = SnapshotStore(root)  # type: ignore[attr-defined]

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
    if args.open:
        webbrowser.open(url, new=2)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard server stopped.", file=sys.stderr)
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

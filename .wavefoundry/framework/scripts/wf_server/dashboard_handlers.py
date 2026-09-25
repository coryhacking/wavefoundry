"""Dashboard handlers: extracted response ownership."""
from __future__ import annotations

from lifecycle_gate_support import _diagnostic
from pathlib import Path
from typing import Any
import json
import os


DASHBOARD_START_WAIT_SECONDS = 5.0


def wf_start_dashboard_response(root: Path, port: int | None = None) -> dict[str, Any]:
    """Start the local dashboard server (with browser open) or return its URL if already running."""
    from wf_server import server_impl
    import subprocess
    import time as _time
    import dashboard_lib

    # Wave 1rswx: reap finished dashboard children on entry so a prior crashed instance's zombie can't
    # linger and can't be misread by the reconcile/liveness checks below.
    server_impl._reap_dashboard_child_pids()

    meta_path = dashboard_lib.dashboard_metadata_path(root)  # 1p64x: the server lock file

    def running_meta() -> dict[str, Any] | None:
        if not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            pid = meta.get("pid")
            url = meta.get("url", "")
            # Wave 1p654: require the PID be a live dashboard for THIS root, not
            # merely os.kill-alive — a recycled/zombie PID must not read as running.
            if isinstance(pid, int) and _dashboard_pid_is_live(pid, root) and url:
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
        return server_impl._response(
            "ok",
            data,
            next_tools=["wf_open_dashboard"],
            usage=str(meta.get("url") or "wf_open_dashboard()"),
        )

    def wait_for_running(timeout: float = server_impl.DASHBOARD_START_WAIT_SECONDS) -> dict[str, Any] | None:
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
    # Wave 1p8pf: also early-out when a dashboard is serving under a drifted/non-matching PID (reachable
    # URL + a live dashboard process) so we never even acquire the start lock to spawn a duplicate.
    serving = _dashboard_already_serving(root, meta_path)
    if serving is not None:
        return already_running(serving)

    try:
        start_lock = dashboard_lib.dashboard_start_lock(root)
        start_lock.__enter__()
    except dashboard_lib.DashboardLockBusy:
        meta = wait_for_running()
        if meta is not None:
            return already_running(meta, starting=True)
        return server_impl._response(
            "ok",
            {"already_running": True, "starting": True, "pid": None, "url": None},
            diagnostics=[_diagnostic(
                "dashboard_start_in_progress",
                "Another dashboard start is already in progress for this repository.",
            )],
            next_tools=["wf_open_dashboard"],
            usage="wf_open_dashboard()",
        )

    try:
        meta = running_meta()
        if meta is not None:
            return already_running(meta)

        # Wave 1p8pf: reconcile-before-spawn — a dashboard may be serving under a DIFFERENT PID than
        # any we recorded (the field race: prior spawn wrote metadata under PID X, this start polls for
        # PID Y). Recognize it by URL-reachability + a live dashboard process and return that URL
        # instead of spawning a duplicate (which climbed ports). running_meta() above already adopted
        # the live-recorded-PID case; this catches the PID-drift case before we kill orphans/spawn.
        serving = _dashboard_already_serving(root, meta_path)
        if serving is not None:
            return already_running(serving)

        # Wave 1p654: no valid recorded instance — but orphaned dashboards for this
        # root may still be alive (drifted/removed metadata). Terminate them so we
        # converge to exactly one instance instead of spawning alongside (the cause
        # of orphan accumulation + port climb). A genuinely-live instance was
        # already adopted by running_meta()/_dashboard_already_serving above; this only
        # fires on real drift (a dead/unreachable recorded instance).
        orphan_diags: list[dict[str, Any]] = []
        _orphans = _dashboard_cmdline_pids(root) or []
        if _orphans:
            for _op in _orphans:
                _terminate_dashboard_pid(_op)
            orphan_diags.append(_diagnostic(
                "dashboard_orphan_detected",
                f"Terminated {len(_orphans)} orphaned dashboard process(es) for this repository before starting.",
            ))

        scripts_dir = server_impl.SCRIPTS_DIR
        cmd = [server_impl._preferred_python(), str(scripts_dir / "dashboard_server.py")]
        if port is not None:
            cmd.extend(["--port", str(port)])
        if dashboard_lib.dashboard_browser_open_enabled():
            cmd.append("--open")
        cmd.extend(["--root", str(root.resolve())])
        spawn_kwargs: dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
            "cwd": str(root),
        }
        if os.name == "nt":
            spawn_kwargs["creationflags"] = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | server_impl._windows_no_window_flag()
            )
        else:
            spawn_kwargs["start_new_session"] = True

        try:
            proc = subprocess.Popen(cmd, **spawn_kwargs)
        except OSError as exc:
            return server_impl._response(
                "error",
                {},
                diagnostics=[_diagnostic("spawn_failed", str(exc))],
            )

        # Wave 1rswx: track this server-launched dashboard so a later sweep (index-refresh or any
        # dashboard entry point) reaps it once it exits (POSIX), instead of leaving a defunct PID that
        # a bare os.kill liveness check would misread as a live kill target.
        server_impl._register_dashboard_child_pid(proc.pid)

        # A child PID/metadata write alone does not prove a serving dashboard.
        # Keep pending children registered; reap exited children before returning.
        deadline = _time.monotonic() + server_impl.DASHBOARD_START_WAIT_SECONDS
        while True:
            exited = proc.poll() is not None
            serving = _dashboard_already_serving(root, meta_path)
            if serving and _dashboard_url_reachable(serving["url"]):
                if exited:
                    proc.wait()
                    server_impl._DASHBOARD_CHILD_PIDS.discard(proc.pid)
                if serving["pid"] != proc.pid:
                    return already_running(serving)
                if not exited:
                    return server_impl._response(
                        "ok", {"started": True, **serving},
                        diagnostics=orphan_diags or None, usage=serving["url"],
                    )
            if exited:
                proc.wait()
                server_impl._DASHBOARD_CHILD_PIDS.discard(proc.pid)
                return server_impl._response(
                    "error", {"started": False, "starting": False, "pid": None, "url": None},
                    diagnostics=[*orphan_diags, _diagnostic(
                        "dashboard_child_exited", "Dashboard child exited before serving.",
                    )],
                )
            if _time.monotonic() >= deadline:
                return server_impl._response(
                    "ok", {"started": False, "starting": True, "pid": proc.pid, "url": None},
                    diagnostics=[*orphan_diags, _diagnostic(
                        "url_not_ready", "Dashboard child is still starting; serving is not confirmed.",
                    )],
                )
            _time.sleep(0.25)
    finally:
        start_lock.__exit__(None, None, None)


def wf_open_dashboard_response(root: Path) -> dict[str, Any]:
    """Open the browser to the running dashboard, or start the dashboard (with browser open) if not running."""
    from wf_server import server_impl
    import webbrowser
    import dashboard_lib

    # Wave 1rswx: reap finished dashboard children so a zombie recorded PID isn't reported as serving.
    server_impl._reap_dashboard_child_pids()

    meta_path = dashboard_lib.dashboard_metadata_path(root)
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            pid = meta.get("pid")
            url = meta.get("url", "")
            # Wave 1rswx: zombie-safe liveness (cmdline-verified) so a <defunct> recorded PID is not
            # reported as a live/serving dashboard (Req 7 / AC-5) — align with the start-path treatment.
            if isinstance(pid, int) and _dashboard_pid_is_live(pid, root) and url:
                opened = False
                if dashboard_lib.dashboard_browser_open_enabled():
                    webbrowser.open(url)
                    opened = True
                return server_impl._response(
                    "ok",
                    {"opened": opened, "url": url, "browser_suppressed": not opened},
                    usage=url,
                )
        except (OSError, json.JSONDecodeError):
            pass

    # Dashboard not running — delegate to start (which spawns with --open).
    return wf_start_dashboard_response(root)


def _dashboard_cmdline_pids(root: Path) -> list[int] | None:
    """Live dashboard PIDs for ``root`` by cmdline scan — delegates to the shared
    ``dashboard_lib.dashboard_cmdline_pids`` (1p654; relocated to the shared module
    in the 1p654 review follow-up so upgrade dashboard detection reuses it)."""
    import dashboard_lib

    return dashboard_lib.dashboard_cmdline_pids(root)


def _dashboard_pid_is_live(pid: int, root: Path) -> bool:
    """True only if ``pid`` is running AND is a dashboard for ``root`` (1p654).

    Hardens the bare ``_pid_is_running`` (a zombie or recycled PID passes
    ``os.kill(pid, 0)``) by requiring a cmdline match. When the scan is
    unavailable (``_dashboard_cmdline_pids`` returns None), falls back to the bare
    liveness check so unsupported platforms keep their current behavior.
    """
    from wf_server import server_impl
    if not server_impl._pid_is_running(pid):
        return False
    live = _dashboard_cmdline_pids(root)
    if live is None:
        return True
    return pid in live


def _dashboard_url_reachable(url: str, timeout: float = 1.0) -> bool:
    """True iff ``url`` answers an HTTP request (any status — a serving dashboard).

    Wave 1p8pf: the dashboard start path must recognize an already-serving dashboard by
    URL-reachability, not by matching the just-spawned PID. A reachable URL is proof the server
    is up regardless of which PID owns it; any HTTP response (incl. 4xx/5xx) counts as serving —
    only a connection failure / timeout means "not reachable". Never raises.
    """
    if not url:
        return False
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout):  # noqa: S310 — loopback dashboard URL
            return True
    except urllib.error.HTTPError:
        # The server answered with an HTTP error status — it IS serving.
        return True
    except Exception:
        # Connection refused / DNS / timeout / SSE-hang — treat as not (yet) reachable.
        return False


def _dashboard_already_serving(root: Path, meta_path: Path) -> dict[str, Any] | None:
    """Reconcile-before-spawn: return a serving dashboard's metadata, or None.

    Wave 1p8pf: a dashboard counts as already-serving when EITHER
      (a) the recorded metadata names a live dashboard PID for ``root`` with a URL
          (the wave-1p654 ``running_meta`` contract — the common reconcile case, incl. the field
          race once the just-spawned child's PID is the live recorded one), OR
      (b) the recorded URL is actually HTTP-reachable AND a live dashboard process exists for
          ``root`` (cmdline scan) — the dashboard is genuinely serving under a PID that differs from
          the recorded one (the field race: a prior spawn wrote metadata under a different PID). A
          reachable URL means killing+respawning would only churn a working server.
    A present-but-DEAD recorded PID whose URL is NOT reachable is a genuine drift — return None so the
    orphan reconciliation terminates the stale process and respawns (converge to one instance).
    Returns ``{"pid", "url"}`` when serving, else None. Never raises.
    """
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    pid = meta.get("pid")
    url = meta.get("url", "") or ""
    if not url:
        return None
    # (a) live recorded PID + URL.
    if isinstance(pid, int) and _dashboard_pid_is_live(pid, root):
        return {"pid": pid, "url": url}
    # (b) a genuinely-reachable URL backed by a live dashboard process for this root (any PID) — adopt
    # rather than churn. A NON-reachable URL falls through to the orphan reconciliation (drift).
    if _dashboard_url_reachable(url):
        live = _dashboard_cmdline_pids(root)
        if live:
            return {"pid": live[0], "url": url}
    return None


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
    from wf_server import server_impl
    import subprocess
    import time as _time

    if pid <= 0:
        return True

    if os.name == "nt":
        try:
            completed = server_impl._mcp_subprocess_run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=False,
                cwd=str(Path.cwd()),
                check=False,
            )
        except OSError:
            return False
        return completed.returncode == 0 or not server_impl._pid_is_running(pid)

    import signal

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    except OSError:
        return False

    deadline = _time.monotonic() + 5.0
    while _time.monotonic() < deadline:
        if not server_impl._pid_is_running(pid):
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
        if not server_impl._pid_is_running(pid):
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

    return not server_impl._pid_is_running(pid)


def wf_stop_dashboard_response(root: Path) -> dict[str, Any]:
    # Wave 1rswx: reap any of our finished dashboard children first, so a recorded PID that is now a
    # <defunct> zombie is cleared from the process table (and no longer passes os.kill(pid,0)) before we
    # classify targets — otherwise the zombie was added as a kill target and stop returned stop_failed.
    from wf_server import server_impl
    server_impl._reap_dashboard_child_pids()

    meta_path, meta = _dashboard_process_metadata(root)
    pid = meta.get("pid")
    url = meta.get("url", "")

    summary: dict[str, Any] = {
        "pid": pid if isinstance(pid, int) else None,
        "url": url if isinstance(url, str) else "",
    }

    # Wave 1p654: reconcile against ALL live dashboards for this root — not just the
    # recorded PID — so a drifted/removed metadata file can't leave an orphan alive.
    scanned = _dashboard_cmdline_pids(root)
    targets: set[int] = set(scanned or [])
    # Wave 1rswx: classify the recorded PID with the cmdline-verified, zombie-safe check (not a bare
    # os.kill liveness). A <defunct> recorded PID fails this test — so it is treated as already stopped
    # (metadata cleared below) instead of a live kill target that SIGTERM/SIGKILL can never reap. A
    # genuinely-live dashboard for this root is already in ``targets`` via the cmdline scan above.
    #
    # SECURITY CONTROL (1rswx AC-3): we never fall back to killing an os.kill-alive-but-unverified
    # recorded PID, because a zombie/recycled PID is indistinguishable from a scan-missed live dashboard
    # WITHOUT the cmdline check — SIGKILLing it could hit a PID recycled to an unrelated process. So when
    # the scan RUNS but misses a genuinely-live dashboard (e.g. a symlink path component repointed
    # mid-session so its --root no longer resolves-equal), that instance is NOT added to targets and is
    # never signalled. The scan-UNAVAILABLE (None) case still falls back to bare liveness inside
    # _dashboard_pid_is_live. (Wave 1rvfw handles the reporting for that unverified-alive case below.)
    if isinstance(pid, int) and pid > 0 and _dashboard_pid_is_live(pid, root):
        targets.add(pid)

    if not targets:
        # Wave 1rvfw: distinguish "genuinely stopped" from "alive but unverifiable". If the recorded PID
        # is still os.kill-alive but was NOT cmdline-verified (not in targets), do NOT claim
        # already_stopped and do NOT delete the metadata — that would be a false success plus state loss
        # while the process keeps serving. Report honestly (already_stopped=False, stopped=False, keep
        # metadata) with a distinct diagnostic and leave the kill decision untouched (the PID is never
        # signalled — the AC-3 control stands). A genuinely dead/reaped/absent PID — including a
        # 1rswx-reaped <defunct> zombie, which is no longer os.kill-alive — takes the clean
        # already_stopped + metadata-cleared path below.
        if isinstance(pid, int) and pid > 0 and server_impl._pid_is_running(pid):
            summary.update({"already_stopped": False, "stopped": False})
            return server_impl._response(
                "ok",
                summary,
                diagnostics=[_diagnostic(
                    "dashboard_pid_unverified",
                    f"Recorded dashboard PID {pid} is alive but could not be verified as a dashboard for "
                    "this repository (it may be a recycled PID now owned by an unrelated process, or a "
                    "live dashboard the process scan could not match for this root). It was NOT "
                    "terminated and the metadata was kept; investigate and stop it manually if it is a "
                    "stray dashboard.",
                )],
                usage="wf_stop_dashboard()",
            )
        summary.update({"already_stopped": True, "metadata_removed": _remove_dashboard_metadata(meta_path)})
        return server_impl._response("ok", summary, usage="wf_stop_dashboard()")

    failed = [p for p in sorted(targets) if not _terminate_dashboard_pid(p)]
    stopped = [p for p in sorted(targets) if p not in failed]
    if failed:
        return server_impl._response(
            "error",
            {**summary, "stopped_pids": stopped},
            diagnostics=[_diagnostic("stop_failed", f"Dashboard process(es) {failed} for this repository did not exit cleanly.")],
            usage="wf_stop_dashboard()",
        )

    orphan_count = len([p for p in stopped if p != pid])
    summary.update({"stopped": True, "stopped_pids": stopped, "metadata_removed": _remove_dashboard_metadata(meta_path)})
    if orphan_count:
        summary["orphans_terminated"] = orphan_count
    return server_impl._response("ok", summary, usage="wf_stop_dashboard()")


def wf_restart_dashboard_response(root: Path) -> dict[str, Any]:
    # R7 (revised): Allow restart during upgrade. The restarted dashboard
    # detects the upgrade lock at startup and enters upgrade_paused
    # automatically, then resumes when the lock is removed. Blocking the
    # restart was redundant and prevented legitimate recovery via restart.

    # Capture the current port before stopping so the restarted server reuses
    # the same port — the browser tab stays valid without a refresh.
    from wf_server import server_impl
    restart_port: int | None = None
    try:
        _, pre_meta = _dashboard_process_metadata(root)
        recorded_port = pre_meta.get("port")
        if isinstance(recorded_port, int) and recorded_port > 0:
            restart_port = recorded_port
    except Exception:  # noqa: BLE001
        pass

    stop_env = wf_stop_dashboard_response(root)
    stop_data = stop_env.get("data", {})
    if stop_env.get("status") != "ok" or not (
        stop_data.get("stopped") is True or stop_data.get("already_stopped") is True
    ):
        return {**stop_env, "data": {**stop_data, "restarted": False}}
    start_env = wf_start_dashboard_response(root, port=restart_port)
    data = dict(stop_env.get("data", {}))
    data.update(start_env.get("data", {}))
    data["restarted"] = start_env.get("status") == "ok" and data.get("started") is True
    return server_impl._response(
        start_env.get("status", "error"),
        data,
        diagnostics=list(stop_env.get("diagnostics", [])) + list(start_env.get("diagnostics", [])),
        next_tools=list(start_env.get("next_tools", [])),
        usage=start_env.get("usage", ""),
    )
